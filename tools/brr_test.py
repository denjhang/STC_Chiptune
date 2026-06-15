#!/usr/bin/env python3
"""BRR 编解码验证 (PC 仿真)

严格参考 GME Spc_Dsp.cpp (line 530-581) 和 OpenMPT SampleFormatBRR.cpp

BRR Decode (GME):
  shifts[0..15] = right_shift: 13,12,12,12,12,12,12,12,12,12,12,12,12,16,16,16
  shifts[16..31] = left_shift:  0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9,10,11,11,11,11
  s = int16(uint16(int16(nybbles) >> right_shift) << left_shift)
  filter (header & 0x0C):
    0x4: s += p1>>1 + (-p1)>>5
    0x8: s += p1 - (p2>>1) + (p2>>1)>>4 + (p1*-3)>>6
    0xC: s += p1 - (p2>>1) + (p1*-13)>>7 + ((p2>>1)*3)>>4
  CLAMP16(s); s *= 2;

BRR Decode (OpenMPT):
  sample = rshift_signed(lshift_signed(nib, range), 1)
  filter:
    1: sample += output[-1] * 15 / 16
    2: sample += output[-1] * 61 / 32 - output[-2] * 15 / 16
    3: sample += output[-1] * 115 / 64 - output[-2] * 13 / 16
  clamp; sample *= 2

两种实现内部精度不同但效果近似。
本实现采用 GME 版本 (bit-exact)。

BRR Encode:
  对于目标 decoded peak ≈ ±16383 (因为最终 *2 到 ±32766):
  每个 block 选择 scale 使 peak << 1 的 nibble 尽量接近 ±7
  nib = sample >> (shift+1)  (因为 decode 是 <<left >>right, 然后 *2)
  实际: decode = nib * (1 << left_shift) * 2 (忽略 right_shift 的截断)
  所以: nib = sample / (2 << left_shift) = sample >> (left_shift + 1)
  auto_scale: 选择 left_shift 使 peak >> (left_shift + 1) <= 7

测试乐器: Blow, Shakuhachi (ADPCM 无法完美循环的)
"""

import struct, os, wave, math

WAV_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'adpcm_wav')
OUT_DIR = os.path.join(WAV_DIR, 'brr_test')
os.makedirs(OUT_DIR, exist_ok=True)

TARGET_RATE = 17640

PROBLEM = [
    ('06_blow.wav',       'microgm',         207, 'Blow',     60),
    ('03_shakuhachi.wav', 'microgm',         211, 'Shakuhachi', 81),
]

# GME Spc_Dsp.cpp shifts table (bit-exact)
RIGHT_SHIFT = [13,12,12,12,12,12,12,12,12,12,12,12,12,16,16,16]
LEFT_SHIFT  = [ 0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9,10,11,11,11,11]


def brr_decode_block(block_data, prev1=0, prev2=0):
    """解码一个 BRR block (9 字节) -> 16 个采样

    严格按 GME Spc_Dsp.cpp 实现:
    - 每 4 个 nybble 一组, nybbles = byte0*256 + byte1
    - s = int16(uint16(int16(nybbles) >> right_shift) << left_shift)
    - p2 = prev2 >> 1 (GME 特有)
    - filter = header & 0x0C (注意是 bit3:2)
    - 输出 *= 2
    """
    header = block_data[0]
    scale = header >> 4
    filter_mode = header & 0x0C  # GME: bits 3:2
    rs = RIGHT_SHIFT[scale]
    ls = LEFT_SHIFT[scale]

    samples = []
    p1 = prev1
    p2_raw = prev2  # 存原始值, 用时 >>1

    for byte_pair in range(4):
        byte0 = block_data[1 + byte_pair * 2]
        byte1 = block_data[2 + byte_pair * 2]
        nybbles = (byte0 * 256 + byte1) & 0xFFFF

        for _ in range(4):
            # GME line 550: int s = int16_t(uint16_t((int16_t) nybbles >> right_shift) << left_shift)
            # C 中 uint16 左移自然截断到 16-bit，Python 需要 & 0xFFFF
            nybbles &= 0xFFFF
            raw = nybbles if nybbles < 0x8000 else nybbles - 0x10000  # int16
            s = ((raw >> rs) & 0xFFFF) << ls
            s &= 0xFFFF  # uint16 截断 (C 的 unsigned << 自然溢出)
            if s >= 0x8000:
                s -= 0x10000  # back to int16

            # GME: p2 = pos[brr_buf_size - 2] >> 1
            p2 = p2_raw >> 1

            if filter_mode >= 8:
                s += p1
                s -= p2
                if filter_mode == 8:
                    # s += p2>>4 + (p1*-3)>>6
                    s += p2 >> 4
                    s += (p1 * -3) >> 6
                else:  # filter_mode == 12
                    # s += (p1*-13)>>7 + (p2*3)>>4
                    s += (p1 * -13) >> 7
                    s += (p2 * 3) >> 4
            elif filter_mode >= 4:
                # s += p1>>1 + (-p1)>>5
                s += p1 >> 1
                s += (-p1) >> 5

            # CLAMP16
            if s > 32767: s = 32767
            if s < -32768: s = -32768

            # GME: s *= 2
            s = (s * 2)
            # 再次 clamp (overflow possible)
            if s > 32767: s = 32767
            if s < -32768: s = -32768

            samples.append(s)

            p2_raw = p1
            p1 = s
            nybbles <<= 4  # 移到下一个 nybble

    return samples, p1, p2_raw


def auto_scale(pcm_samples):
    """选择最佳 scale

    GME decode: s = (nib >> rs) << ls * 2
    对于 packed nybble (nib 在 bit15-12), nib=7 时 nybbles=0x7000:
      (0x7000 >> rs) << ls * 2
    = (7 << (16-rs)) >> rs << ls * 2  -- 不对

    简化: 对于 nybbles 高4位 = N (signed 4-bit in bit15-12):
      raw = 0xN000 (int16), >> rs 提取 N
      然后 << ls 放大, * 2 输出
      decode_out = N * (2 << ls)

    所以 capacity = 7 * (2 << LEFT_SHIFT[scale])
    对 scale=12: 7 * (2 << 11) = 7 * 4096 = 28672
    对 scale=11: 7 * (2 << 10) = 7 * 2048 = 14336

    选最小的 scale 使 capacity >= peak (nibble 用率最高)
    """
    peak = max(abs(s) for s in pcm_samples) if pcm_samples else 1
    if peak == 0:
        return 0

    best_sc = 12  # 默认最大
    for sc in range(13):
        ls = LEFT_SHIFT[sc]
        capacity = 7 * (2 << ls)
        if capacity >= peak:
            return sc  # 第一个满足的就是最优 (ls 最小)
    return 12


def brr_encode_block(pcm_samples, scale=0, filter_mode=0):
    """编码一个 block (16 个样本) -> 9 字节

    Encode: 对 decode 的逆过程
    decode 中: s (clamped, *2) ≈ sample
    所以 sample/2 ≈ nib << left_shift (忽略 filter)
    nib = (sample/2) >> left_shift = sample >> (left_shift + 1)
    """
    ls = LEFT_SHIFT[scale]
    rs = RIGHT_SHIFT[scale]
    result = bytearray(9)
    # header: [7:4]=scale, [3:2]=filter (GME 格式: filter = 0x0C * filter_mode)
    result[0] = (scale << 4) | (filter_mode << 2)

    for i in range(16):
        s = pcm_samples[i]
        # nib = s >> (ls + 1), 因为 decode 是 nib << ls 然后 *2
        total_shift = ls + 1
        nib = s >> total_shift
        nib = max(-8, min(7, nib))

        byte_idx = 1 + i // 2
        if i % 2 == 0:
            result[byte_idx] = (nib & 0x0F) << 4
        else:
            result[byte_idx] |= (nib & 0x0F)

    return bytes(result), scale


def brr_encode(pcm_samples, block_size=16, use_filter=True):
    """编码整个 PCM 为 BRR 块序列"""
    blocks = bytearray()
    n_blocks = (len(pcm_samples) + block_size - 1) // block_size

    for b in range(n_blocks):
        start = b * block_size
        end = min(start + block_size, len(pcm_samples))
        block_pcm = pcm_samples[start:end]
        while len(block_pcm) < block_size:
            block_pcm.append(0)

        scale = auto_scale(block_pcm)
        filter_mode = 2 if use_filter else 0  # filter=2 对应 0x8

        block_data, _ = brr_encode_block(block_pcm, scale, filter_mode)
        blocks.extend(block_data)

    return bytes(blocks)


def decode_verify(blocks, seg_original):
    """验证 encode->decode round-trip"""
    n_blocks = len(blocks) // 9
    decoded = []
    p1, p2 = 0, 0
    for b in range(n_blocks):
        bd = blocks[b*9:(b+1)*9]
        samp, p1, p2 = brr_decode_block(bd, p1, p2)
        decoded.extend(samp)

    n = min(len(decoded), len(seg_original))
    errors = [abs(decoded[i] - seg_original[i]) for i in range(n)]
    max_err = max(errors) if errors else 0
    rms = math.sqrt(sum(e*e for e in errors) / n) if n > 0 else 0
    return max_err, rms, decoded[:n]


def verify_loop_seam(blocks, loop_block, n_cycles=20):
    """验证 loop 接缝: 连续解码多个循环, 检查跳变"""
    n_blocks = len(blocks) // 9
    loop_nibbles = (n_blocks - loop_block) * 16
    decoded = []
    p1, p2 = 0, 0

    for cycle in range(n_cycles):
        b_start = loop_block if cycle > 0 else 0
        for b in range(b_start, n_blocks):
            bd = blocks[b*9:(b+1)*9]
            samp, p1, p2 = brr_decode_block(bd, p1, p2)
            decoded.extend(samp)

    seams = []
    for cycle in range(1, n_cycles):
        end_idx = cycle * loop_nibbles - 1
        start_idx = cycle * loop_nibbles
        if end_idx < len(decoded) and start_idx < len(decoded):
            seams.append(abs(decoded[start_idx] - decoded[end_idx]))

    return max(seams) if seams else 0, sum(seams)/len(seams) if seams else 0


def render_brr(blocks, loop_block, dur=4.0, pitch_ratio=256):
    """渲染 BRR 循环播放 (GME bit-exact decode)"""
    n_frames = int(dur * TARGET_RATE)
    out = []

    p1, p2 = 0, 0
    n_blocks = len(blocks) // 9
    current_block = 0
    sample_in_block = 0
    decoded_block = []

    def decode_current_block():
        nonlocal current_block, sample_in_block, decoded_block, p1, p2
        bs = current_block * 9
        bd = blocks[bs:bs+9]
        decoded_block, p1, p2 = brr_decode_block(bd, p1, p2)
        sample_in_block = 0

    decode_current_block()

    now_step = 0
    s_prev = 0
    s_cur = decoded_block[0] if decoded_block else 0

    for i in range(n_frames):
        now_step += pitch_ratio
        while now_step >= 256:
            s_prev = s_cur
            sample_in_block += 1
            if sample_in_block >= 16:
                current_block += 1
                if current_block >= n_blocks:
                    current_block = loop_block
                    p1, p2 = 0, 0  # 重置 filter 状态!
                decode_current_block()
            s_cur = decoded_block[sample_in_block]
            now_step -= 256

        frac = now_step
        if frac > 0 and pitch_ratio < 0x100:
            out_val = s_prev + (s_cur - s_prev) * frac / 256
        else:
            out_val = s_cur
        out.append(max(-32768, min(32767, int(out_val))))

    return out


def estimate_period(pcm):
    crosses = [i for i in range(1, len(pcm)) if pcm[i-1] < 0 and pcm[i] >= 0]
    if len(crosses) < 2:
        return 40
    gaps = [crosses[i+1] - crosses[i] for i in range(len(crosses)-1)]
    return int(sum(gaps) / len(gaps))


def find_zero_crossing(pcm, center, search_range=200):
    n = len(pcm)
    lo = max(1, center - search_range)
    hi = min(n, center + search_range)
    for i in range(lo, hi):
        if pcm[i-1] < 0 and pcm[i] >= 0:
            return i
    return center


def write_wav(path, samples, rate=TARGET_RATE):
    with wave.open(path, 'w') as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(rate)
        wf.writeframes(struct.pack('<%dh' % len(samples), *samples))


def main():
    for wav_name, sf2_src, sf2_id, display, orig_pitch in PROBLEM:
        with wave.open(os.path.join(WAV_DIR, wav_name), 'r') as w:
            raw = w.readframes(w.getnframes())
        pcm16 = list(struct.unpack('<%dh' % (len(raw) // 2), raw))
        n = len(pcm16)

        peak = max(abs(s) for s in pcm16)
        scale_f = 32767.0 / peak if peak > 0 else 1.0
        norm = [int(s * scale_f) for s in pcm16]

        period = estimate_period(norm)
        print(f'{display:12s} n={n} peak={peak} period={period}')

        # 搜索最佳 seg_start 和 loop_block (seam=0)
        mid = n // 2
        best_params = None
        for offset in range(-300, 301, 16):
            ss = mid + offset - ((mid + offset) % 16)
            if ss < 0: continue
            sl = (n - ss - 10) // 16 * 16
            if sl < 64: continue
            s = norm[ss:ss+sl]
            nb = len(s) // 16
            blocks = brr_encode(s, use_filter=True)
            for lb in [1, nb//4, nb//2, nb*3//4, nb-1]:
                ms, _ = verify_loop_seam(blocks, lb, n_cycles=5)
                if ms == 0:
                    # 选最长的段
                    if best_params is None or sl > best_params[0]:
                        best_params = (sl, ss, lb)

        if best_params:
            seg_len, seg_start, loop_block = best_params
        else:
            # fallback
            zc = find_zero_crossing(norm, mid)
            seg_start = zc - (zc % 16)
            seg_len = (n - seg_start - 10) // 16 * 16
            loop_block = max(1, (seg_len // 16) // 4)

        seg = norm[seg_start:seg_start + seg_len]
        n_blocks = len(seg) // 16

        print(f'  seg=[{seg_start}..{seg_start+seg_len-1}] blocks={n_blocks} loop_block={loop_block}')

        # 原始段参考 WAV
        write_wav(os.path.join(OUT_DIR, f'{display}_orig_seg.wav'), seg)

        # BRR 编码 (filter=2)
        blocks = brr_encode(seg, use_filter=True)
        print(f'  BRR: {len(blocks)}B ({len(blocks)//9} blocks)')

        # Round-trip 验证
        max_err, rms, decoded = decode_verify(blocks, seg)
        seg_peak = max(abs(s) for s in seg)
        dec_peak = max(abs(s) for s in decoded)
        print(f'  round-trip: max_err={max_err} rms={rms:.1f} input_peak={seg_peak} decode_peak={dec_peak}')

        # 解码段 WAV
        write_wav(os.path.join(OUT_DIR, f'{display}_decoded_seg.wav'), decoded)

        # Loop 接缝验证
        max_seam, avg_seam = verify_loop_seam(blocks, loop_block, n_cycles=20)
        print(f'  loop seam: max={max_seam} avg={avg_seam:.1f} (20 cycles)')

        # 渲染循环播放
        for midi in [60, 72]:
            note_name = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
            nn = f'{note_name[midi%12]}{midi//12-1}'
            out = render_brr(blocks, loop_block, dur=4.0)
            out_peak = max(abs(s) for s in out)
            out_rms = (sum(s*s for s in out)/len(out))**0.5
            p = os.path.join(OUT_DIR, f'{display}_{nn}.wav')
            write_wav(p, out)
            print(f'  {nn}: peak={out_peak} rms={out_rms:.0f}')

        print()


if __name__ == '__main__':
    main()
