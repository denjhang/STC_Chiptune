#!/usr/bin/env python3
"""XI 乐器 -> 17640Hz 重采样 + crossfade + BRR filter=0 完美循环

流程:
1. 解析 XI, 重采样到 17640Hz
2. PCM 层 crossfade 修复 loop 接缝
3. BRR 编码
4. 解码得到真实 BRR 值
5. 在解码值上再次 crossfade 修 BRR 量化误差
6. 重新编码受影响的 block (filter=0, 无状态, 改哪修哪)
7. 验证 seam=0, 输出 WAV
"""

import struct, os, wave

XI_DIR = 'D:/working/vscode-projects/Reference_Project/STC-MCU/sootsound/0000_all_instruments/'
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'xi_out', 'brr_crossfade')
TARGET_RATE = 17640

RIGHT_SHIFT = [13,12,12,12,12,12,12,12,12,12,12,12,13,16,16,16]
LEFT_SHIFT  = [ 0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9,10,11,11,11,11]

PICKS = [
    '00_Acoustic_Grand_Piano.xi',
    '04_Electric_Piano_1_L0.xi',
    '28_Violin.xi',
    '30_Strings.xi',
    '2E_Harp.xi',
    '15_Accordion_L0.xi',
    '13_Church_Organ.xi',
    '23_Fretless_Bass.xi',
    '1A_Jazz_Guitar.xi',
    '1E_Distortion_Guitar.xi',
    '08_Celesta.xi',
    '49_Flute.xi',
    '4A_Recorder.xi',
    '44_Oboe.xi',
    '47_Clarinet.xi',
]


def parse_xi_pcm(filepath):
    with open(filepath, 'rb') as f:
        data = f.read()
    if data[:21] != b'Extended Instrument: ':
        return None, None
    name = data[21:43].split(b'\x00')[0].decode('ascii', errors='replace')
    num_samples = struct.unpack_from('<H', data, 296)[0]
    sh_off = 298; pcm_off = sh_off + num_samples * 40
    samples = []
    for s_idx in range(num_samples):
        so = sh_off + s_idx * 40
        slen = struct.unpack_from('<I', data, so)[0]
        lstart = struct.unpack_from('<I', data, so+4)[0]
        llen = struct.unpack_from('<I', data, so+8)[0]
        vol = data[so+12]; fine = struct.unpack_from('b', data, so+13)[0]
        flags = data[so+14]; relnote = struct.unpack_from('b', data, so+16)[0]
        is_16 = bool(flags & 0x10); loop_type = flags & 0x03
        n_samp = slen // 2 if is_16 else slen
        loop_s = lstart // 2 if is_16 else lstart
        loop_l = llen // 2 if is_16 else llen
        center_rate = 8363.0 * (2.0 ** ((relnote + fine / 128.0) / 12.0))
        pcm = []
        if is_16:
            acc = 0
            for i in range(n_samp):
                delta = struct.unpack_from('<h', data, pcm_off + i*2)[0]
                acc += delta
                pcm.append(max(-32768, min(32767, acc)))
        else:
            acc = 0
            for i in range(n_samp):
                delta = struct.unpack_from('b', data, pcm_off + i)[0]
                acc += delta
                pcm.append(max(-128, min(127, acc)) * 256)
        pcm_off += slen
        samples.append({'pcm': pcm, 'n_samples': n_samp, 'loop_start': loop_s,
                         'loop_end': loop_s + loop_l, 'has_loop': loop_type > 0,
                         'relnote': relnote, 'fine': fine, 'volume': vol, 'center_rate': center_rate})
    return name, samples


def resample(pcm, src_rate, dst_rate):
    src_len = len(pcm)
    if src_rate == dst_rate or src_len < 2:
        return pcm[:]
    dst_len = max(2, int(round(src_len * dst_rate / src_rate)))
    ratio = (src_len - 1) / (dst_len - 1)
    result = []
    for i in range(dst_len):
        pos = i * ratio; idx = int(pos); frac = pos - idx
        s = pcm[idx] * (1 - frac) + pcm[idx+1] * frac if idx+1 < src_len else pcm[-1]
        result.append(int(round(s)))
    return result


def crossfade_tail(pcm, loop_s, loop_e, fade_len):
    """只改 tail: loop_e 前 fade_len 个采样渐变到 loop_s 的值"""
    loop_len = loop_e - loop_s
    if loop_len <= 0 or fade_len <= 0:
        return pcm[:]
    fade_len = min(fade_len, loop_len // 2)
    result = pcm[:]
    target = result[loop_s]
    for i in range(fade_len):
        t = (i + 1) / fade_len
        idx = loop_e - fade_len + i
        result[idx] = int(result[idx] * (1 - t) + target * t)
    return result


# --- BRR ---

def auto_scale(pcm16):
    peak = max(abs(s) for s in pcm16) if pcm16 else 1
    if peak == 0: return 0
    for sc in range(13):
        if 7 * (2 << LEFT_SHIFT[sc]) >= peak:
            return sc
    return 12


def brr_encode_block(pcm16, scale, loop_flag=False, end_flag=False):
    """编码一个 BRR block (16 个 s16 采样 → 9 字节), filter=0"""
    header = (scale << 4)
    if loop_flag: header |= 0x02
    if end_flag: header |= 0x01
    blk = bytearray(9)
    blk[0] = header
    ls = LEFT_SHIFT[scale]
    for i in range(16):
        s = pcm16[i] if i < len(pcm16) else 0
        nib = s >> (ls + 1)
        nib = max(-8, min(7, nib))
        byte_idx = 1 + i // 2
        if i % 2 == 0:
            blk[byte_idx] = (nib & 0x0F) << 4
        else:
            blk[byte_idx] |= (nib & 0x0F)
    return bytes(blk)


def brr_encode(pcm, loop_start):
    """BRR encode all, loop_start aligned to 16"""
    blocks = bytearray()
    n_blocks = (len(pcm) + 15) // 16
    for b in range(n_blocks):
        start = b * 16
        chunk = pcm[start:start+16]
        while len(chunk) < 16:
            chunk = chunk + [0]
        scale = auto_scale(chunk)
        is_loop = (b * 16 == loop_start)
        is_end = (b == n_blocks - 1)
        blocks.extend(brr_encode_block(chunk, scale, is_loop, is_end))
    return bytes(blocks), n_blocks


def brr_decode_block(blk):
    """解码一个 BRR block, filter=0, 返回 16 个 s16"""
    scale = blk[0] >> 4
    rs = RIGHT_SHIFT[scale]
    ls = LEFT_SHIFT[scale]
    samples = []
    for bp in range(4):
        b0 = blk[1 + bp*2]
        b1 = blk[2 + bp*2]
        nyb = (b0 * 256 + b1) & 0xFFFF
        for _ in range(4):
            nyb &= 0xFFFF
            raw = nyb if nyb < 0x8000 else nyb - 0x10000
            s = ((raw >> rs) & 0xFFFF) << ls
            s &= 0xFFFF
            if s >= 0x8000: s -= 0x10000
            s *= 2
            s = max(-32768, min(32767, s))
            samples.append(s)
            nyb <<= 4
    return samples


def brr_decode_all_samples(blocks, n_blocks):
    """Decode all BRR blocks → list of s16"""
    decoded = []
    for b in range(n_blocks):
        decoded.extend(brr_decode_block(blocks[b*9:(b+1)*9]))
    return decoded


def brr_fix_seam(blocks, n_blocks, loop_block, fade_len=16):
    """在 BRR 解码值上做 crossfade 修复, 重编码受影响 block。
    filter=0 无状态, 改 block 不影响邻居。

    loop 回绕: block[loop_block] 的第 0 个采样 ← block[n_blocks-1] 的第 15 个采样
    修 tail: 最后 fade_len 个采样渐变到 loop_block 第 0 个采样的解码值
    """
    # 1. 解码所有 block
    decoded = brr_decode_all_samples(blocks, n_blocks)
    total = n_blocks * 16

    loop_start_sample = loop_block * 16
    loop_end_sample = n_blocks * 16  # loop 到这里回绕
    target = decoded[loop_start_sample]  # loop 起点的实际解码值

    fade_len = min(fade_len, (loop_end_sample - loop_start_sample) // 2)

    # 2. 修改 decoded 的 tail
    for i in range(fade_len):
        t = (i + 1) / fade_len
        idx = loop_end_sample - fade_len + i
        if idx < len(decoded):
            decoded[idx] = int(decoded[idx] * (1 - t) + target * t)

    # 3. 重编码受影响的 block (最后 ceil(fade_len/16) 个)
    first_affected_block = (loop_end_sample - fade_len) // 16
    result = bytearray(blocks)
    for b in range(first_affected_block, n_blocks):
        start = b * 16
        chunk = decoded[start:start+16]
        if len(chunk) < 16:
            chunk = chunk + [0] * (16 - len(chunk))
        scale = auto_scale(chunk)
        is_loop = (b == loop_block)
        is_end = (b == n_blocks - 1)
        new_blk = brr_encode_block(chunk, scale, is_loop, is_end)
        result[b*9:(b+1)*9] = new_blk

    return bytes(result)


def verify_seam(blocks, n_blocks, loop_block, n_cycles=50):
    decoded = brr_decode_all_samples(blocks, n_blocks)
    loop_n = (n_blocks - loop_block) * 16
    if loop_n <= 0: return 9999, 9999
    seams = []
    for c in range(n_cycles):
        # cycle c: [loop_block..n_blocks) 的第 c 次
        end_idx = loop_block * 16 + (c + 1) * loop_n - 1
        start_idx = loop_block * 16 + c * loop_n
        if end_idx < len(decoded) and start_idx < len(decoded):
            seams.append(abs(decoded[start_idx] - decoded[end_idx]))
    return max(seams) if seams else 0, sum(seams)/len(seams) if seams else 0


def render_loop(samples, loop_start_samp, loop_end_samp, dur, rate, midi_note, native_midi, vol):
    """Render loop playback. loop_start_samp/loop_end_samp = 采样索引."""
    n_frames = int(dur * rate)
    pitch_step = 2.0 ** ((midi_note - native_midi) / 12.0)
    note_off = int(dur * 0.8 * rate)
    loop_len = loop_end_samp - loop_start_samp
    if loop_len <= 0: loop_len = len(samples)
    n_s = len(samples)
    out = []
    for i in range(n_frames):
        ipos = int(i * pitch_step)
        frac = (i * pitch_step) - ipos
        if loop_len > 0 and ipos >= loop_end_samp:
            ipos = loop_start_samp + (ipos - loop_start_samp) % loop_len
        if ipos >= n_s: ipos = n_s - 1
        p1 = ipos + 1
        if loop_len > 0 and p1 >= loop_end_samp:
            p1 = loop_start_samp + (p1 - loop_start_samp) % loop_len
        if p1 >= n_s: p1 = n_s - 1
        sample = samples[ipos] + (samples[p1] - samples[ipos]) * frac
        t_sec = i / rate
        if t_sec < 0.005: e = t_sec / 0.005
        elif i < note_off: e = 1.0
        else:
            rel = (i - note_off) / max(1, n_frames - note_off)
            e = max(0, 1.0 - rel * rel)
        out.append(max(-32768, min(32767, int(sample * e * vol))))
    return out


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(os.path.join(OUT_DIR, 'pcm'), exist_ok=True)
    os.makedirs(os.path.join(OUT_DIR, 'brr'), exist_ok=True)

    print(f"{'Instrument':<35s} {'OrigKB':>6s} {'PCM16':>6s} {'BRR':>5s} {'Seam':>10s} {'Rate':>8s}")
    print('-' * 78)

    for pick in PICKS:
        filepath = os.path.join(XI_DIR, pick)
        if not os.path.exists(filepath):
            print(f'  SKIP {pick}'); continue

        name, samples = parse_xi_pcm(filepath)
        if not name or not samples: continue

        s = samples[0]
        if not s['has_loop'] or s['n_samples'] < 50:
            print(f'  SKIP {pick} (no loop)'); continue

        pcm16 = s['pcm']
        center_rate = s['center_rate']
        pcm17640 = resample(pcm16, center_rate, TARGET_RATE)
        n17640 = len(pcm17640)
        ratio = n17640 / len(pcm16)
        loop_s = max(0, int(s['loop_start'] * ratio))
        loop_e = min(n17640, int(s['loop_end'] * ratio))
        native_midi = 24 + s['relnote'] + s['fine'] / 128.0
        vol = s['volume'] / 64.0
        cn = pick.replace('.xi', '')

        # Step 1: PCM crossfade
        new_loop_len = loop_e - loop_s
        pcm_fade = max(8, min(64, new_loop_len // 10))
        pcm_fixed = crossfade_tail(pcm17640, loop_s, loop_e, pcm_fade)

        # Step 2: BRR encode
        loop_s_aligned = (loop_s + 15) // 16 * 16
        if loop_s_aligned >= n17640: loop_s_aligned = 0
        blocks, n_blocks = brr_encode(pcm_fixed, loop_s_aligned)
        loop_block = loop_s_aligned // 16

        # Step 3: BRR decode → crossfade → re-encode affected blocks
        brr_fade = 16  # BRR 层面 fade 16 采样 (1 个 block)
        blocks_fixed = brr_fix_seam(blocks, n_blocks, loop_block, brr_fade)

        # Step 4: Verify
        max_seam, avg_seam = verify_seam(blocks_fixed, n_blocks, loop_block)

        # Sizes
        orig_kb = s['n_samples'] * 2 / 1024
        pcm_kb = n17640 * 2 / 1024
        brr_kb = len(blocks_fixed) / 1024

        seam_str = f'{max_seam}' if max_seam > 0 else 'PERFECT'
        print(f'{cn:35s} {orig_kb:5.1f}  {pcm_kb:5.1f}  {brr_kb:4.1f}  {seam_str:>10s}  {center_rate:.0f}Hz')

        # WAV 1: crossfade PCM
        out_pcm = render_loop(pcm_fixed, loop_s, loop_e, 5.0, TARGET_RATE, 60,
                              native_midi, vol)
        wav1 = os.path.join(OUT_DIR, 'pcm', f'{cn}.wav')
        with wave.open(wav1, 'w') as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(TARGET_RATE)
            wf.writeframes(struct.pack('<%dh' % len(out_pcm), *out_pcm))

        # WAV 2: BRR decoded
        decoded = brr_decode_all_samples(blocks_fixed, n_blocks)
        brr_loop_s = loop_block * 16
        brr_loop_e = n_blocks * 16
        out_brr = render_loop(decoded, brr_loop_s, brr_loop_e, 5.0, TARGET_RATE, 60, native_midi, vol)
        wav2 = os.path.join(OUT_DIR, 'brr', f'{cn}.wav')
        with wave.open(wav2, 'w') as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(TARGET_RATE)
            wf.writeframes(struct.pack('<%dh' % len(out_brr), *out_brr))

    print(f'\nDone! pcm/ and brr/ in {OUT_DIR}')


if __name__ == '__main__':
    main()
