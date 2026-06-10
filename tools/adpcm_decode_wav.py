#!/usr/bin/env python3
"""将预处理后的 ROM 解码为 WAV, 在电脑上验证音色"""
import struct, math, wave

# ========== jedi_table ==========
STEPS = [
    16, 17, 19, 21, 23, 25, 28, 31, 34, 37, 41, 45, 50, 55, 60, 66,
    73, 80, 88, 97, 107, 118, 130, 143, 157, 173, 190, 209, 230, 253,
    279, 307, 337, 371, 408, 449, 494, 544, 598, 658, 724, 796, 876,
    963, 1060, 1166, 1282, 1411, 1552
]
STEP_INC = [-16, -16, -16, -16, 32, 80, 112, 144]

def build_jedi_table():
    table = []
    for step in STEPS:
        row = []
        for nib in range(16):
            val = (2 * (nib & 7) + 1) * step // 8
            if nib & 8: val = -val
            row.append(val)
        table.append(row)
    return table
JEDI = build_jedi_table()

def read_rom_header(path):
    rom = []
    with open(path, 'r') as f:
        for line in f:
            for p in line.split(','):
                p = p.strip().strip(';')
                if not p: continue
                try:
                    v = int(p, 16)
                    if 0 <= v <= 255: rom.append(v)
                except ValueError: continue
    return bytes(rom[:0x2000])

def adpcm_decode(rom, start_byte, nibble_count):
    acc = 0; step_idx = 0; samples = []
    for i in range(nibble_count):
        addr = start_byte + (i >> 1)
        if addr >= len(rom): break
        nib = (rom[addr] >> 4) & 0x0F if not (i & 1) else rom[addr] & 0x0F
        delta = JEDI[step_idx // 16][nib]
        acc += delta; acc &= 0xFFF
        if acc & 0x800: acc |= ~0xFFF
        samples.append(acc)
        step_idx += STEP_INC[nib & 7]
        if step_idx < 0: step_idx = 0
        if step_idx > 768: step_idx = 768
    return samples

# 预处理后的地址
DRUMS = [
    ('BD', 0x0000, 854,  17640),
    ('SD', 0x01AB, 1341, 17640),
    ('TC', 0x044A, 5853, 8820),   # Top Cymbal (was HH)
    ('HH', 0x0FB9, 1951, 17640),  # High Hat (was TC)
    ('TM', 0x1389, 1189, 8820),
    ('RS', 0x15DC, 244,  8820),
]

SAMPLE_RATE = 17640

def main():
    rom = read_rom_header('STC32G12K128/fmopn_2608rom.h')
    print(f"ROM: {len(rom)} bytes")

    # 每鼓单独 WAV
    for name, start, nib_count, drum_rate in DRUMS:
        pcm = adpcm_decode(rom, start, nib_count)
        # 转换到实际播放采样率: 如果 drum_rate < SAMPLE_RATE, 拉伸到 SAMPLE_RATE
        if drum_rate < SAMPLE_RATE:
            ratio = SAMPLE_RATE / drum_rate
            pcm_stretched = []
            for s in pcm:
                pcm_stretched.append(s)
                for _ in range(int(ratio) - 1):
                    pcm_stretched.append(s)
            pcm = pcm_stretched

        # s16 WAV
        out = 'tools/adpcm_' + name.lower() + '.wav'
        with wave.open(out, 'w') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(struct.pack(f'<{len(pcm)}h', *pcm))
        dur = len(pcm) / SAMPLE_RATE
        print(f"{name}: {len(pcm)} samples, {dur:.3f}s @ {SAMPLE_RATE}Hz -> {out}")

    # 合并节奏 WAV: BD SD HH 循环
    print("\nGenerating rhythm WAV...")
    all_samples = []
    beat = SAMPLE_RATE // 5  # 200ms per beat

    for bar in range(4):
        # beat 1: BD+HH
        bd = adpcm_decode(rom, 0x0000, 854)
        hh = adpcm_decode(rom, 0x044A, 5853)
        for i in range(max(len(bd), len(hh) * 2)):  # HH is div=2
            s = 0
            if i < len(bd): s += bd[i]
            if i // 2 < len(hh): s += hh[i // 2]
            all_samples.append(s)
        pad = beat * 2 - len(all_samples) % (beat * 2)
        if pad > 0: all_samples.extend([0] * pad)

        # beat 2: SD+HH
        sd = adpcm_decode(rom, 0x01AB, 1341)
        start_idx = len(all_samples)
        for i in range(max(len(sd), len(hh) * 2)):
            if start_idx + i >= len(all_samples) and i >= len(sd) and i // 2 >= len(hh):
                break
            s = 0
            if i < len(sd): s += sd[i]
            if i // 2 < len(hh): s += hh[i // 2]
            if start_idx + i < len(all_samples):
                all_samples[start_idx + i] += s
            else:
                all_samples.append(s)
        pad = beat * 2 - (len(all_samples) % (beat * 2))
        if pad > 0 and pad < beat * 2: all_samples.extend([0] * pad)

    # clamp
    all_samples = [max(-2048, min(2047, s)) for s in all_samples]

    with wave.open('tools/adpcm_rhythm.wav', 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(struct.pack(f'<{len(all_samples)}h', *all_samples))
    print(f"Rhythm: {len(all_samples)} samples, {len(all_samples)/SAMPLE_RATE:.2f}s -> tools/adpcm_rhythm.wav")

if __name__ == '__main__':
    main()
