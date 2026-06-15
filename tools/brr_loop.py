#!/usr/bin/env python3
"""BRR 风格 loop 仿真

BRR 每个 block 有确定初始状态, loop 回绕时解码器重置到 block 初始状态.
类比: 把 ADPCM 波形分成 block, 每个 block 开头记录 (init_acc, init_step),
loop 回绕时从 block header 读取初始值.

核心思路: PCM 能完美循环 -> 只要每个 block 的大小 = 完整周期的整数倍,
          那么 block 开头的 PCM 值就相同, 编码器在相同 PCM + 相同初始状态 -> 相同输出.
"""

import struct, os, wave, json, math

WAV_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'adpcm_wav')
OUT_DIR = os.path.join(WAV_DIR, 'brr_style')
os.makedirs(OUT_DIR, exist_ok=True)
TARGET_RATE = 17640

STEPS = [16,17,19,21,23,25,28,31,34,37,41,45,50,55,60,66,
         73,80,88,97,107,118,130,143,157,173,190,209,230,253,
         279,307,337,371,408,449,494,544,598,658,724,796,876,
         963,1060,1166,1282,1411,1552]

def build_jedi():
    t = []
    for step in STEPS:
        row = []
        for nib in range(16):
            val = (2 * (nib & 7) + 1) * step // 8
            if nib & 8: val = -val
            row.append(val)
        t.append(row)
    return t

JEDI = build_jedi()
JEDI_FLAT = []
for row in JEDI: JEDI_FLAT.extend(row)
STEP_INC = [-16,-16,-16,-16,32,80,112,144]

PROBLEM = [
    ('06_blow.wav',       'microgm',         207, 'Blow',     60),
    ('03_shakuhachi.wav', 'microgm',         211, 'Shakuhachi', 81),
    ('09_harp.wav',       'snes_unofficial', 90, 'Harp',     73),
    ('04_oboe.wav',       'snes_unofficial', 102, 'Oboe',     28),
]


def estimate_period(norm):
    crosses = [i for i in range(1, len(norm)) if norm[i-1] < 0 and norm[i] >= 0]
    if len(crosses) < 2:
        return 40
    gaps = [crosses[i+1] - crosses[i] for i in range(len(crosses)-1)]
    return int(sum(gaps) / len(gaps))


def encode_with_init(pcm_samples, init_acc=0, init_step=0):
    """编码一段 PCM, 从指定初始状态开始"""
    nibbles = []; acc = init_acc; step = init_step
    for s in pcm_samples:
        if s > 2047: s = 2047
        if s < -2048: s = -2048
        best = 0; bd = abs(s - acc)
        row = step // 16
        for n in range(16):
            d = JEDI[row][n]
            t = acc + d; t &= 0xFFF
            if t & 0x800: t |= ~0xFFF
            if abs(s - t) < bd: bd = abs(s - t); best = n
        d = JEDI[row][best]
        acc += d; acc &= 0xFFF
        if acc & 0x800: acc |= ~0xFFF
        step += STEP_INC[best & 7]
        if step < 0: step = 0
        if step > 768: step = 768
        nibbles.append(best)
    rom = bytearray()
    for i in range(0, len(nibbles), 2):
        hi = nibbles[i]; lo = nibbles[i+1] if i+1 < len(nibbles) else 0
        rom.append((hi << 4) | lo)
    return bytes(rom), nibbles, acc, step


def decode_states(rom, nib_count):
    acc = 0; step = 0; addr = 0; states = []
    for i in range(nib_count):
        byte_val = rom[addr >> 1]
        nib = (byte_val >> 4) & 0x0F if not (addr & 1) else byte_val & 0x0F
        d = JEDI_FLAT[step + nib]
        acc += d; acc &= 0xFFF
        if acc & 0x800: acc |= ~0xFFF
        step += STEP_INC[nib & 7]
        if step < 0: step = 0
        if step > 768: step = 768
        states.append((acc & 0xFFF, step))
        addr += 1
    return states


def brr_encode(norm, block_size, ls_block_idx):
    """
    BRR 风格编码:
    1. 将 norm 分成 block_size 大小的 block
    2. 每个 block 连续编码 (前一个 block 的 end 状态 = 下一个的 init 状态)
    3. ls_block_idx 指定哪个 block 是 loop start
    4. 返回 (rom, nib_count, ls_nibble, le_nibble, block_headers)
       block_headers 记录每个 block 的 init (acc, step)
    """
    n_blocks = (len(norm) + block_size - 1) // block_size
    all_rom = bytearray()
    all_nibbles = []
    block_headers = []  # (nibble_offset, init_acc, init_step)

    acc = 0; step = 0
    nib_offset = 0
    for b in range(n_blocks):
        start = b * block_size
        end = min(start + block_size, len(norm))
        block_pcm = norm[start:end]

        block_headers.append((nib_offset, acc, step))
        rom, nibs, acc, step = encode_with_init(block_pcm, acc, step)
        all_rom.extend(rom)
        all_nibbles.extend(nibs)
        nib_offset += len(nibs)

    ls_nibble = block_headers[ls_block_idx][0]
    le_nibble = len(all_nibbles) - 1

    return bytes(all_rom), len(all_nibbles), ls_nibble, le_nibble, block_headers


def render_brr(rom, nib_count, ls, le, block_headers, ls_block_idx,
               init_acc, init_step, midi_note, orig_pitch, dur=4.0):
    """BRR 风格渲染: loop 回绕时从 block header 读取初始状态"""
    semi = midi_note - orig_pitch
    if semi == 0:
        pitch_ratio = 256
    elif semi > 0:
        oct = semi // 12; r = semi % 12
        semi_table = [256, 271, 287, 304, 322, 341, 362, 383, 406, 430, 455, 482]
        pitch_ratio = semi_table[r] * (1 << oct)
    else:
        oct = (-semi) // 12; r = (-semi) % 12
        semi_table = [256, 242, 228, 216, 203, 192, 181, 171, 161, 152, 144, 136]
        pitch_ratio = semi_table[r] >> oct

    n_frames = int(dur * TARGET_RATE)
    out = []
    addr = 0; acc = init_acc; step = init_step
    s_prev = 0

    # 初始解码一个样本
    byte_val = rom[addr >> 1]
    nib = (byte_val >> 4) & 0x0F if not (addr & 1) else byte_val & 0x0F
    d = JEDI_FLAT[step + nib]
    acc += d; acc &= 0xFFF
    if acc & 0x800: acc |= ~0xFFF
    step += STEP_INC[nib & 7]
    if step < 0: step = 0
    if step > 768: step = 768
    s_cur = acc
    addr += 1

    now_step = 0
    for i in range(n_frames):
        now_step += pitch_ratio
        while now_step >= 256:
            s_prev = s_cur
            byte_val = rom[addr >> 1]
            nib = (byte_val >> 4) & 0x0F if not (addr & 1) else byte_val & 0x0F
            d = JEDI_FLAT[step + nib]
            acc += d; acc &= 0xFFF
            if acc & 0x800: acc |= ~0xFFF
            step += STEP_INC[nib & 7]
            if step < 0: step = 0
            if step > 768: step = 768
            s_cur = acc
            addr += 1
            # BRR loop 回绕: 重置到 block header 的初始状态
            if addr > le:
                addr = ls
                acc = block_headers[ls_block_idx][1] & 0xFFF
                if acc & 0x800: acc |= ~0xFFF
                step = block_headers[ls_block_idx][2]
            now_step -= 256

        frac = now_step
        if frac > 0 and pitch_ratio < 0x100:
            out_val = s_prev + (s_cur - s_prev) * frac / 256
        else:
            out_val = s_cur
        out_val = int(out_val * 31) >> 5
        out.append(max(-32768, min(32767, int(out_val))))
    return out


def find_smooth_segment(norm, seg_len, search_start=None, search_end=None):
    n = len(norm)
    if search_start is None: search_start = n // 4
    if search_end is None: search_end = n - max(seg_len, n // 4)
    best_s = search_start; best_cost = 999999999
    for s in range(search_start, search_end - seg_len + 1):
        cost = sum(abs(norm[i] - norm[i-1]) for i in range(s+1, s+seg_len))
        if cost < best_cost:
            best_cost = cost; best_s = s
    return best_s


def main():
    for wav_name, sf2_src, sf2_id, display, orig_pitch in PROBLEM:
        with wave.open(os.path.join(WAV_DIR, wav_name), 'r') as w:
            raw = w.readframes(w.getnframes())
        pcm16 = list(struct.unpack('<%dh' % (len(raw)//2), raw))
        peak = max(abs(s) for s in pcm16)
        scale = 2047.0 / peak
        norm = [int(s * scale) for s in pcm16]
        n = len(norm)

        period = estimate_period(norm)
        # block_size = 整数个周期 (取较长段避免泛音)
        block_size = period * 4  # 4个周期一个block
        print(f'{display:12s} n={n} period={period} block={block_size}')

        # 取中段大部分, block_size 对齐
        mid = n // 2
        # 找最近的过零点
        crosses = [i for i in range(max(1,mid-200), min(n,mid+200))
                   if norm[i-1] < 0 and norm[i] >= 0]
        if not crosses:
            crosses = [i for i in range(1, n) if norm[i-1] < 0 and norm[i] >= 0]
        seg_start = crosses[len(crosses)//2]
        seg_start = seg_start - (seg_start % block_size)  # block对齐
        # 取尽可能长的段 (2/3 的采样)
        seg_len = (n * 2 // 3) - (n * 2 // 3) % block_size
        if seg_start + seg_len > n:
            seg_len = n - seg_start - (n - seg_start) % block_size

        seg = norm[seg_start:seg_start+seg_len]
        n_blocks = len(seg) // block_size
        ls_block_idx = 1  # 从第2个block开始loop

        print(f'  seg=[{seg_start}..{seg_start+seg_len-1}] blocks={n_blocks} ls_block={ls_block_idx}')

        # BRR 编码
        rom, nib_count, ls, le, headers = brr_encode(seg, block_size, ls_block_idx)

        # 验证: ls block 的 init 状态 vs 编码到 le 处的状态
        states = decode_states(rom, nib_count)
        ls_acc, ls_step = headers[ls_block_idx][1], headers[ls_block_idx][2]
        le_acc, le_step = states[le]
        delta = abs(ls_acc - le_acc) + abs(ls_step - le_step) * 2
        print(f'  ls_block init: acc={ls_acc} step={ls_step}')
        print(f'  le state:       acc={le_acc} step={le_step}')
        print(f'  delta={delta}')

        # 渲染
        for midi in [60, 72]:
            note_name = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
            nn = f'{note_name[midi%12]}{midi//12-1}'
            out = render_brr(rom, nib_count, ls, le, headers, ls_block_idx,
                             0, 0, midi, orig_pitch, dur=4.0)
            p = os.path.join(OUT_DIR, f'{display}_{nn}.wav')
            with wave.open(p, 'w') as wf:
                wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(TARGET_RATE)
                wf.writeframes(struct.pack('<%dh' % len(out), *out))
            print(f'  -> {p}')
        print()

if __name__ == '__main__':
    main()
