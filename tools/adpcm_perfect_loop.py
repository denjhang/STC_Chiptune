#!/usr/bin/env python3
"""ADPCM 完美循环构造器

算法:
  1. 在采样中段找变化最小的区域 (差分绝对值之和最小)
  2. 限制段长度, 构造 palindrome (正向 + 反向)
  3. 迭代 ADPCM 感知 crossfade: 在 reverse 段末尾渐变到 forward 段开头
     (相同 PCM → 相同 ADPCM 状态 → 天然收敛)
  4. 迭代直到 ADPCM 解码器状态差为零
"""

import struct, os, wave, json

WAV_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'adpcm_wav')
OUT_DIR = os.path.join(WAV_DIR, 'perfect_loop')
os.makedirs(OUT_DIR, exist_ok=True)

SF2_ROOT = 'D:/working/vscode-projects/Reference_Project/STC-MCU/sf2_extract'
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
    ('09_harp.wav',       'snes_unofficial', 90, 'Harp',     73),
    ('03_shakuhachi.wav', 'microgm',         211, 'Shakuhachi', 81),
    ('04_oboe.wav',       'snes_unofficial', 102, 'Oboe',     28),
]


def adpcm_encode(pcm, snap_nibble=-1):
    nibbles = []; acc = 0; step_idx = 0
    for i, s in enumerate(pcm):
        if s > 2047: s = 2047
        if s < -2048: s = -2048
        best = 0; bd = abs(s - acc)
        row = step_idx // 16
        for n in range(16):
            d = JEDI[row][n]
            t = acc + d; t &= 0xFFF
            if t & 0x800: t |= ~0xFFF
            if abs(s - t) < bd: bd = abs(s - t); best = n
        d = JEDI[row][best]
        acc += d; acc &= 0xFFF
        if acc & 0x800: acc |= ~0xFFF
        step_idx += STEP_INC[best & 7]
        if step_idx < 0: step_idx = 0
        if step_idx > 768: step_idx = 768
        nibbles.append(best)
    rom = bytearray()
    for i in range(0, len(nibbles), 2):
        hi = nibbles[i]; lo = nibbles[i + 1] if i + 1 < len(nibbles) else 0
        rom.append((hi << 4) | lo)
    rom = bytes(rom)
    snap = None
    if snap_nibble >= 0:
        dacc = 0; dstep = 0
        for i in range(min(snap_nibble + 1, len(nibbles))):
            byte_val = rom[i >> 1]
            nib = (byte_val >> 4) & 0x0F if not (i & 1) else byte_val & 0x0F
            d = JEDI_FLAT[dstep + nib]
            dacc += d; dacc &= 0xFFF
            if dacc & 0x800: dacc |= ~0xFFF
            dstep += STEP_INC[nib & 7]
            if dstep < 0: dstep = 0
            if dstep > 768: dstep = 768
            if i == snap_nibble:
                snap = (dacc & 0xFFF, dstep)
    return rom, len(nibbles), snap


def get_decoder_states(rom, nib_count):
    """记录每个 nibble 处的 (acc, step)"""
    acc = 0; step = 0
    states = []
    for i in range(nib_count):
        byte_val = rom[i >> 1]
        nib = (byte_val >> 4) & 0x0F if not (i & 1) else byte_val & 0x0F
        d = JEDI_FLAT[step + nib]
        acc += d; acc &= 0xFFF
        if acc & 0x800: acc |= ~0xFFF
        step += STEP_INC[nib & 7]
        if step < 0: step = 0
        if step > 768: step = 768
        states.append((acc & 0xFFF, step))
    return states


def decode_one(rom, addr, acc, step, loop_start, loop_end, loop_acc, loop_step):
    byte_val = rom[addr >> 1]
    nib = (byte_val >> 4) & 0x0F if not (addr & 1) else byte_val & 0x0F
    d = JEDI_FLAT[step + nib]
    acc += d; acc &= 0xFFF
    if acc & 0x800: acc |= ~0xFFF
    sample = acc
    step += STEP_INC[nib & 7]
    if step < 0: step = 0
    if step > 768: step = 768
    addr += 1
    if addr > loop_end:
        addr = loop_start
        acc = loop_acc & 0xFFF
        if acc & 0x800: acc |= ~0xFFF
        step = loop_step
    return sample, addr, acc, step


def render_voice(rom, nib_count, loop_start, loop_end, loop_acc, loop_step,
                 midi_note, orig_pitch, dur=4.0):
    semi = midi_note - orig_pitch
    if semi == 0:
        pitch_ratio = 256
    elif semi > 0:
        oct = semi // 12
        r = semi % 12
        semi_table = [256, 271, 287, 304, 322, 341, 362, 383, 406, 430, 455, 482]
        pitch_ratio = semi_table[r] * (1 << oct)
    else:
        oct = (-semi) // 12
        r = (-semi) % 12
        semi_table = [256, 242, 228, 216, 203, 192, 181, 171, 161, 152, 144, 136]
        pitch_ratio = semi_table[r] >> oct

    n_frames = int(dur * TARGET_RATE)
    out = []
    addr = 0; acc = 0; step = 0
    s_prev = 0
    s_cur = decode_one(rom, 0, 0, 0, loop_start, loop_end, loop_acc, loop_step)[0]
    now_step = 0
    for i in range(n_frames):
        now_step += pitch_ratio
        while now_step >= 256:
            s_prev = s_cur
            s_cur, addr, acc, step = decode_one(
                rom, addr, acc, step, loop_start, loop_end, loop_acc, loop_step)
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
    """找差分绝对值之和最小的连续段"""
    n = len(norm)
    if search_start is None:
        search_start = n // 4
    if search_end is None:
        search_end = n - max(seg_len, n // 4)
    best_s = search_start
    best_cost = 999999999
    for s in range(search_start, search_end - seg_len + 1):
        cost = sum(abs(norm[i] - norm[i-1]) for i in range(s+1, s+seg_len))
        if cost < best_cost:
            best_cost = cost
            best_s = s
    return best_s


def build_perfect_loop(norm, seg_len, max_iter=30, tolerance=2):
    """
    1. 找变化最小的段
    2. 构造 palindrome
    3. 迭代 ADPCM crossfade 直到状态差 <= tolerance
    """
    n = len(norm)
    seg_start = find_smooth_segment(norm, seg_len)
    seg_end = seg_start + seg_len - 1

    # 构造 palindrome: fwd[seg_start..seg_end] + rev[seg_end-1..seg_start+1]
    fwd = norm[seg_start : seg_end + 1]
    rev = norm[seg_end - 1 : seg_start : -1]
    palindrome = fwd + rev

    # 拼接: attack + palindrome
    attack = norm[:seg_start]
    pcm = attack + palindrome
    ls = len(attack)
    le = len(pcm) - 1

    print(f'    seg=[{seg_start}..{seg_end}] fwd={len(fwd)} rev={len(rev)} ls={ls} le={le}')

    # 迭代 ADPCM 收敛
    cf_len = 0
    for iteration in range(max_iter):
        rom, nib_count, _ = adpcm_encode(pcm)
        states = get_decoder_states(rom, nib_count)

        if ls >= len(states) or le >= len(states):
            break

        t_acc, t_step = states[ls]
        e_acc, e_step = states[le]
        delta = abs(t_acc - e_acc) + abs(t_step - e_step) * 2

        if iteration % 3 == 0 or delta <= tolerance:
            print(f'    iter={iteration:2d} cf={cf_len:5d} delta={delta:4d} '
                  f'(acc:{t_acc:4d}/{e_acc:4d} step:{t_step:3d}/{e_step:3d})')

        if delta <= tolerance:
            break

        # 增大 crossfade: reverse 末尾 → forward 开头
        # crossfade 末尾 (alpha=1) 完全等于 forward 段开头
        # 编码相同 PCM → 相同 ADPCM 状态
        cf_len = max(cf_len * 2 + 32, 64)
        cf_len = min(cf_len, le - ls)
        patched = list(pcm)
        for i in range(cf_len):
            alpha = (i + 1) / cf_len
            rev_idx = le - cf_len + 1 + i
            fwd_idx = ls + i
            patched[rev_idx] = int((1 - alpha) * patched[rev_idx] + alpha * patched[fwd_idx])
        pcm = patched

    return pcm, ls, le


def main():
    for wav_name, sf2_src, sf2_id, display, orig_pitch in PROBLEM:
        with wave.open(os.path.join(WAV_DIR, wav_name), 'r') as w:
            raw = w.readframes(w.getnframes())
        pcm16 = list(struct.unpack('<%dh' % (len(raw) // 2), raw))
        peak = max(abs(s) for s in pcm16)
        scale = 2047.0 / peak
        norm = [int(s * scale) for s in pcm16]

        # 段长度: 短一些更容易收敛, 长一些音质更好
        # 用 800~1500 之间的值
        n = len(norm)
        seg_len = min(1500, max(800, n // 3))

        print(f'{display:12s} n={n} seg_len={seg_len}')

        pcm, ls, le = build_perfect_loop(norm, seg_len, max_iter=25, tolerance=2)

        # 最终编码渲染
        rom, nib_count, snap = adpcm_encode(pcm, snap_nibble=ls)
        loop_acc = snap[0] if snap else 0
        loop_step = snap[1] if snap else 0
        if loop_acc & 0x800: loop_acc = loop_acc - 0x1000

        states = get_decoder_states(rom, nib_count)
        final_delta = abs(states[ls][0] - states[le][0]) + abs(states[ls][1] - states[le][1]) * 2
        print(f'    FINAL delta={final_delta}')

        for midi in [60, 72]:
            note_name = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
            nn = f'{note_name[midi%12]}{midi//12-1}'
            out = render_voice(rom, nib_count, ls, le, loop_acc, loop_step,
                               midi, orig_pitch, dur=4.0)
            p = os.path.join(OUT_DIR, f'{display}_{nn}.wav')
            with wave.open(p, 'w') as wf:
                wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(TARGET_RATE)
                wf.writeframes(struct.pack('<%dh' % len(out), *out))
            print(f'    -> {p}')
        print()


if __name__ == '__main__':
    main()
