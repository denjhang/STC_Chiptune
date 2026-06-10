#!/usr/bin/env python3
"""
YM2608 ADPCM 鼓声预处理: 解码 -> 重采样到 17640Hz -> 重新编码 -> 输出 C header

原始采样率:
  BD/SD/HH/TC: 18518 Hz (freqbase/3)
  TM/RS:       9259 Hz (freqbase/6)

目标: 全部重采样到 17640Hz, 下位机用分频控制播放速度
"""

import struct, math

# ========== jedi_table (49 x 16 = 784) ==========
STEPS = [
    16, 17, 19, 21, 23, 25, 28, 31, 34, 37, 41, 45, 50, 55, 60, 66,
    73, 80, 88, 97, 107, 118, 130, 143, 157, 173, 190, 209, 230, 253,
    279, 307, 337, 371, 408, 449, 494, 544, 598, 658, 724, 796, 876,
    963, 1060, 1166, 1282, 1411, 1552
]

def build_jedi_table():
    table = []
    for step in STEPS:
        row = []
        for nib in range(16):
            val = (2 * (nib & 7) + 1) * step // 8
            if nib & 8:
                val = -val
            row.append(val)
        table.append(row)
    return table

JEDI = build_jedi_table()

STEP_INC = [-16, -16, -16, -16, 32, 80, 112, 144]

# ========== 原始 ROM (8KB) ==========
# 从 fmopn_2608rom.h 提取 — 运行时直接 parse header
def read_rom_from_header(path):
    """Parse fmopn_2608rom.h, extract ROM bytes"""
    rom = []
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            # match hex bytes
            parts = line.split(',')
            for p in parts:
                p = p.strip().strip(';')
                if not p:
                    continue
                try:
                    v = int(p, 16)
                    if 0 <= v <= 255:
                        rom.append(v)
                except ValueError:
                    continue
    return bytes(rom[:0x2000])

def read_rom_from_bin(path):
    with open(path, 'rb') as f:
        return f.read()

# ========== ADPCM 解码 ==========
def adpcm_decode(rom_data, start_byte, length_bytes):
    """Decode ADPCM from ROM, return list of s16 PCM samples"""
    acc = 0
    step_idx = 0
    total_nibbles = length_bytes * 2
    samples = []

    for i in range(total_nibbles):
        addr = start_byte + (i >> 1)
        if addr >= len(rom_data):
            break
        if i & 1:
            nib = rom_data[addr] & 0x0F
        else:
            nib = (rom_data[addr] >> 4) & 0x0F

        delta = JEDI[step_idx // 16][nib]
        acc += delta
        acc &= 0xFFF

        if acc & 0x800:
            acc |= ~0xFFF

        samples.append(acc)

        step_idx += STEP_INC[nib & 7]
        if step_idx < 0:
            step_idx = 0
        if step_idx > 48 * 16:
            step_idx = 48 * 16

    return samples

# ========== 重采样 (线性插值) ==========
def resample(samples, src_rate, dst_rate):
    """Resample using linear interpolation"""
    if src_rate == dst_rate:
        return samples

    src_len = len(samples)
    dst_len = int(round(src_len * dst_rate / src_rate))
    if dst_len < 1:
        dst_len = 1

    ratio = (src_len - 1) / (dst_len - 1) if dst_len > 1 else 0
    result = []
    for i in range(dst_len):
        pos = i * ratio
        idx = int(pos)
        frac = pos - idx
        if idx + 1 < src_len:
            s = samples[idx] * (1 - frac) + samples[idx + 1] * frac
        else:
            s = samples[-1]
        result.append(int(round(s)))
        # clamp to 12-bit
        if result[-1] > 2047:
            result[-1] = 2047
        if result[-1] < -2048:
            result[-1] = -2048
    return result

# ========== ADPCM 编码 ==========
def adpcm_encode(pcm_samples):
    """Encode PCM s16 samples to ADPCM nibbles, return bytes"""
    nibbles = []
    acc = 0
    step_idx = 0

    for s in pcm_samples:
        # clamp
        if s > 2047: s = 2047
        if s < -2048: s = -2048

        # find best nibble
        best_nib = 0
        best_diff = abs(s - acc)

        step = step_idx
        row_idx = step // 16
        for nib in range(16):
            delta = JEDI[row_idx][nib]
            trial = acc + delta
            trial &= 0xFFF
            if trial & 0x800:
                trial |= ~0xFFF
            diff = abs(s - trial)
            if diff < best_diff:
                best_diff = diff
                best_nib = nib

        # apply
        delta = JEDI[row_idx][best_nib]
        acc += delta
        acc &= 0xFFF
        if acc & 0x800:
            acc |= ~0xFFF

        step_idx += STEP_INC[best_nib & 7]
        if step_idx < 0:
            step_idx = 0
        if step_idx > 48 * 16:
            step_idx = 48 * 16

        nibbles.append(best_nib)

    # pack nibbles to bytes (MSB first)
    result = bytearray()
    for i in range(0, len(nibbles), 2):
        hi = nibbles[i]
        lo = nibbles[i + 1] if i + 1 < len(nibbles) else 0
        result.append((hi << 4) | lo)

    return bytes(result), len(nibbles)

# ========== 鼓参数 ==========
# 全部重采样到 17640Hz 或 8820Hz, ROM 空间充足 (128KB)
# div=1: 每 tick 解码 (17640Hz), div=2: 每 2 tick 解码 (8820Hz)
DRUM_INFO = [
    # name, start_byte, end_byte(inclusive), original_rate, target_rate, div
    # 地址来自 libvgm YM2608_ADPCM_ROM_addr[] (权威)
    ('BD', 0x0000, 0x01BF, 18518, 17640, 1),   # Bass Drum, 448B
    ('SD', 0x01C0, 0x043F, 18518, 17640, 1),   # Snare Drum, 640B
    ('TC', 0x0440, 0x1B7F, 18518, 8820,  2),   # Top Cymbal, 5952B
    ('HH', 0x1B80, 0x1CFF, 18518, 17640, 1),   # High Hat, 384B
    ('TM', 0x1D00, 0x1F7F, 9259,  8820,  2),   # Tom Tom, 640B
    ('RS', 0x1F80, 0x1FFF, 9259,  8820,  2),   # Rim Shot, 128B
]

TARGET_RATE = 17640

def main():
    rom_path = 'STC32G12K128/fmopn_2608rom.h'
    print(f"Reading ROM from {rom_path}...")
    rom = read_rom_from_header(rom_path)
    print(f"ROM size: {len(rom)} bytes")

    # Validate
    assert len(rom) == 0x2000, f"Expected 8192 bytes, got {len(rom)}"

    print(f"\nPreprocessing...")
    all_drums = []

    for name, start, end, src_rate, tgt_rate, div in DRUM_INFO:
        byte_len = end - start + 1
        nib_count = byte_len * 2
        print(f"\n{name}: {start:#06x}-{end:#06x} {byte_len}B ({nib_count} nib) @ {src_rate}Hz -> {tgt_rate}Hz (div={div})")

        # Decode
        pcm = adpcm_decode(rom, start, nib_count // 2)
        print(f"  Decoded: {len(pcm)} samples")

        # Resample
        resampled = resample(pcm, src_rate, tgt_rate)
        print(f"  Resampled: {len(resampled)} samples @ {tgt_rate}Hz")

        # Encode
        encoded, nibble_count = adpcm_encode(resampled)
        print(f"  Encoded: {len(encoded)} bytes ({nibble_count} nibbles)")

        all_drums.append((name, encoded, nibble_count, src_rate, tgt_rate, div))

    # Layout ROM: drums packed sequentially
    print("\n=== ROM Layout ===")
    rom_data = bytearray()
    offsets = []
    for name, encoded, nibble_count, src_rate, tgt_rate, div in all_drums:
        offset = len(rom_data)
        offsets.append(offset)
        rom_data.extend(encoded)
        print(f"  {name}: offset={offset:#06x} len={len(encoded)}B ({nibble_count} nibbles) div={div} orig={src_rate}Hz")

    # Pad to 0x2000
    total = len(rom_data)
    while len(rom_data) < 0x2000:
        rom_data.append(0)
    if total > 0x2000:
        rom_size = ((total + 15) >> 4) << 4  # align to 16
    else:
        rom_size = 0x2000
    print(f"  Total: {total} bytes (ROM array: {rom_size})")

    # Output header
    out_path = 'STC32G12K128/fmopn_2608rom.h'
    with open(out_path, 'w') as f:
        f.write('/*\n    YM2608 ADPCM ROM - preprocessed, all resampled to 17640Hz\n*/\n\n')
        f.write(f'static const unsigned char YM2608_ADPCM_ROM[{rom_size:#x}] = {{\n\n')

        # Write per-drum comments
        for name, encoded, nibble_count, src_rate, tgt_rate, div in all_drums:
            f.write(f'/* {name}: {len(encoded)}B, orig {src_rate}Hz -> {tgt_rate}Hz, div={div} */\n')

        # Write hex data
        addr = 0
        while addr < len(rom_data):
            chunk = rom_data[addr:addr + 16]
            hex_line = ', '.join(f'0x{b:02X}' for b in chunk)
            f.write(hex_line + ',\n')
            addr += 16

        f.write('};\n')

    print(f"\nWritten: {out_path}")

    # Print new addresses for adpcm.c
    print("\n=== Update adpcm.c ===")
    print("drum_start[6] = {")
    for i, (name, encoded, nibble_count, src_rate, tgt_rate, div) in enumerate(all_drums):
        print(f"    0x{offsets[i]:04X},  /* {name} */")
    print("};")
    print("\ndrum_len[6] = { // nibble counts")
    for i, (name, encoded, nibble_count, src_rate, tgt_rate, div) in enumerate(all_drums):
        print(f"    {nibble_count},    /* {name}: {len(encoded)}B */")
    print("};")
    print("\ndrum_div[6] = { // 1=every tick(17640Hz), 2=every 2 ticks(8820Hz)")
    for i, (name, encoded, nibble_count, src_rate, tgt_rate, div) in enumerate(all_drums):
        print(f"    {div},  /* {name}: {tgt_rate}Hz data, play={17640//div}Hz */")
    print("};")


if __name__ == '__main__':
    main()
