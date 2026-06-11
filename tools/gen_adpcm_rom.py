#!/usr/bin/env python3
"""生成采样乐器 ADPCM ROM C header
读取 tools/adpcm_wav/ 下的 10 个原始 WAV,
归一化 -> ADPCM 编码 -> 输出 C header + 元数据表

编码器和 MCU adpcm.c jedi_table 完全一致 (硬编码 JEDI_FLAT)
"""

import struct, os, wave, json

WAV_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'adpcm_wav')
SF2_ROOT = 'D:/working/vscode-projects/Reference_Project/STC-MCU/sf2_extract'
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'STC32G12K128')

INSTRUMENTS = [
    ('01_piano.wav',      'snes_unofficial', 35, 'Piano'),
    ('02_slapbass.wav',   'snes_unofficial', 34, 'SlapBass'),
    ('10_guitar.wav',     'snes_unofficial', 91, 'Guitar'),
    ('fixed/04_oboe_fixed.wav',  None, None, 'Oboe',     2425, 2852),
    ('fixed/09_harp_fixed.wav',  None, None, 'Harp',     3374, 6372),
]

# jedi_table: 直接复制自 adpcm.c 的硬编码表 (784 s16, 49 step * 16 nib)
# 确保编码器和解码器(C MCU)完全一致
JEDI_FLAT = [
     2,     6,    10,    14,    18,    22,    26,    30,    -2,    -6,   -10,   -14,   -18,   -22,   -26,   -30,
     2,     6,    10,    14,    19,    23,    27,    31,    -2,    -6,   -10,   -14,   -19,   -23,   -27,   -31,
     2,     7,    11,    16,    21,    26,    30,    35,    -2,    -7,   -11,   -16,   -21,   -26,   -30,  -35,
     2,     7,    13,    18,    23,    28,    34,    39,    -2,    -7,   -13,   -18,   -23,   -28,  -34,  -39,
     2,     8,    14,    20,    25,    31,    37, 43,    -2,    -8,   -14,   -20,   -25,  -31,   -37,  -43,
     3,     9,    15,    21,    28,    34, 40, 46,    -3,    -9,   -15,   -21,   -28,   -34,  -40,   -46,
     3,    10,    17,   24,    31,    38,   45,   52,    -3,   -10,   -17,   -24,   -31,   -38,  -45,  -52,
     3,    11,    19,    27,    34,    42,   50,    58,    -3,   -11,  -19,   -27,   -34,   -42,  -50,  -58,
     4,    12,    21,    29,    38,   46,   55,    63,    -4,   -12,  -21,   -29,   -38,   -46,  -55,  -63,
     4,    13,    23,    32,    41,    50,   60,    69,    -4,   -13,  -23,   -32,   -41,   -50,  -60,  -69,
     5,    15,    25,    35,   46,    56,   66,  76,    -5,   -15,   -25,   -35,   -46,  -56,  -66,  -76,
     5,    16,    28,    39,    50, 61, 73, 84,    -5,   -16,  -28,   -39,   -50,  -61,  -73,  -84,
     6,    18,    31,    43,    56,    68,    81, 93,    -6,   -18,  -31,   -43,   -56,  -68,  -81,  -93,
     6,    20,    34,    48,    61,    75,    89,   103, -6,   -20,  -34,  -48,   -61,  -75,  -89,  -103,
     7,    22,    37,    52,    67,    82,    97,   112, -7,  -22,  -37,  -52,  -67,  -82,  -97,  -112,
     8,    24,    41,    57,    74,    90,  107,  123, -8,   -24,  -41,  -57,  -74,  -90, -107,  -123,
     9,    27,    45,    63,    82,   100,  118,  136, -9,   -27,  -45,  -63,  -82,  -100, -118, -136,
    10,    30,    50,    70,    90,   110,   130,  150, -10,  -30,  -50,  -70,  -90,  -110,  -130, -150,
    11,    33,    55,    77,    99,   121,   143,  165, -11,  -33,  -55,  -77,  -99,  -121,  -143, -165,
    12,    36,    60,    84,   109,  133,  157, 181, -12,  -36,  -60,  -84,  -109,  -133,  -157,  -181,
    13,    40,    66,    93,   120, 147, 173, 200, -13,  -40,  -66,  -93,  -120,  -147,  -173, -200,
    14,    44,    73,   103,  132,  162, 191, 221, -14,  -44,  -73,  -103, -132, -162, -191, -221,
    16,    48,    81,   113,  146, 178,  211, 243, -16,  -48,  -81,  -113,  -146, -178, -211, -243,
    17,    53,    89,   125,  160, 196, 232, 268, -17,  -53,  -89,  -125, -160, -196, -232, -268,
    19,    58,    98,   137,  176,  215, 255, 294, -19,  -58,  -98,  -137,  -176, -215, -255, -294,
    21,    64,   108,   151, 194, 237, 281, 324, -21,  -64,  -108,  -151,  -194, -237, -281, -324,
    23,    71,   118,   166, 213, 261, 308, 356, -23,  -71,  -118,  -166,  -213, -261, -308, -356,
    26,    78,   130,   182, 235, 287, 339, 391, -26,  -78,  -130,  -182, -235, -287, -339, -391,
    28,    86,   143,   201, 258, 316, 373, 431, -28,  -86,  -143,  -201, -258, -316, -373, -431,
    31,    94,   158,   221, 284, 347, 411, 474, -31,  -94,  -158,  -221, -284, -347, -411, -474,
    34,   104,   174,   244, 313, 383, 453, 523, -34,  -104, -174,  -244, -313, -383, -453, -523,
    38,   115,   191,   268, 345, 422, 498, 575, -38,  -115, -191,  -268, -345, -422, -498, -575,
    42,   126,   210,   294, 379, 463, 547, 631, -42,  -126,  -210,  -294, -379, -463, -547, -631,
    46,   139,   231,   324, 417, 510, 602, 695, -46,  -139,  -231,  -324, -417, -510, -602, -695,
    51,   153,   255,   357, 459, 561, 663, 765, -51,  -153,  -255,  -357, -459, -561, -663, -765,
    56,   168,   280,   392, 505, 617, 729, 841, -56,  -168,  -280,  -392, -505,  -617, -729, -841,
    61,   185,   308,   432, 555, 679, 802, 926, -61,  -185,  -308,  -432, -555, -679, -802, -926,
    68,   204,   340,   476, 612, 748, 884,1020, -68,  -204,  -340,  -476, -612, -748, -884, -1020,
    74,   224,   373,   523, 672, 822, 971,1121, -74,  -224,  -373,  -523,  -672, -822, -971, -1121,
    82,   246,   411,   575, 740, 904,1069,1233, -82,  -246,  -411,  -575,  -740, -904, -1069, -1233,
    90,   271,   452,   633, 814, 995,1176,1357, -90,  -271,  -452,  -633,  -814,  -995, -1176, -1357,
    99,   298,   497,   696, 895,1094,1293,1492, -99,  -298,  -497,  -696,  -895, -1094, -1293, -1492,
   109,   328,   547,   766, 985,1204,1423,1642, -109, -328,  -547,  -766,  -985, -1204, -1423, -1642,
   120,   361,   601,   842,1083,1324,1564,1805, -120, -361,  -601,  -842, -1083, -1324, -1564, -1805,
   132,   397,   662,   927,1192,1457,1722,1987, -132, -397,  -662,  -927, -1192, -1457, -1722, -1987,
   145,   437,   728,  1020,1311,1603,1894,2186, -145, -437,  -728, -1020, -1311, -1603, -1894, -2186,
   160,   480,   801, 1121,1442,1762,2083,2403, -160, -480,  -801, -1121, -1442, -1762, -2083, -2403,
   176,   529,   881, 1234,1587,1940,2292,2645, -176, -529,  -881, -1234, -1587, -1940, -2292, -2645,
   194,   582,   970, 1358,1746,2134,2522,2910, -194, -582,  -970, -1358, -1746, -2134, -2522, -2910,
]
STEP_INC = [-16, -16, -16, -16, 32, 80, 112, 144]


def adpcm_encode(pcm_samples, snapshot_nibble=-1):
    nibbles = []; acc = 0; step_idx = 0
    for i, s in enumerate(pcm_samples):
        if s > 2047: s = 2047
        if s < -2048: s = -2048
        best_nib = 0; best_diff = abs(s - acc)
        for nib in range(16):
            delta = JEDI_FLAT[step_idx + nib]
            trial = acc + delta; trial &= 0xFFF
            if trial & 0x800: trial |= ~0xFFF
            diff = abs(s - trial)
            if diff < best_diff:
                best_diff = diff; best_nib = nib
        delta = JEDI_FLAT[step_idx + best_nib]
        acc += delta; acc &= 0xFFF
        if acc & 0x800: acc |= ~0xFFF
        step_idx += STEP_INC[best_nib & 7]
        if step_idx < 0: step_idx = 0
        if step_idx > 768: step_idx = 768
        nibbles.append(best_nib)
    result = bytearray()
    for i in range(0, len(nibbles), 2):
        hi = nibbles[i]; lo = nibbles[i + 1] if i + 1 < len(nibbles) else 0
        result.append((hi << 4) | lo)
    rom = bytes(result)
    # 用硬编码表解码到 snapshot_nibble 处, 记录解码器状态
    snap = None
    if snapshot_nibble >= 0:
        dacc = 0; dstep = 0
        for i in range(min(snapshot_nibble + 1, len(nibbles))):
            byte_val = rom[i >> 1]
            nib = (byte_val >> 4) & 0x0F if not (i & 1) else byte_val & 0x0F
            d = JEDI_FLAT[dstep + nib]
            dacc += d; dacc &= 0xFFF
            if dacc & 0x800: dacc |= ~0xFFF
            dstep += STEP_INC[nib & 7]
            if dstep < 0: dstep = 0
            if dstep > 768: dstep = 768
            if i == snapshot_nibble:
                snap = (dacc & 0xFFF, dstep)
    return rom, len(nibbles), snap


def load_metadata(sf2_source, sf2_id):
    path = os.path.join(SF2_ROOT, sf2_source, 'sf2_mapping.json')
    with open(path) as f:
        data = json.load(f)
    key = str(sf2_id)
    if key not in data['samples']:
        return None
    return data['samples'][key]


def main():
    all_data = bytearray()
    entries = []
    total_nib = 0

    for entry in INSTRUMENTS:
        if len(entry) == 6:
            # Fixed WAV: (wav_name, None, None, display, loop_s, loop_e)
            wav_name, sf2_src, sf2_id, display_name, loop_s, loop_e = entry
            is_fixed = True
            orig_pitch = 28 if 'oboe' in wav_name.lower() else 73  # hardcoded
        else:
            wav_name, sf2_src, sf2_id, display_name = entry
            is_fixed = False

        if not is_fixed:
            meta = load_metadata(sf2_src, sf2_id)
            orig_pitch = meta['orig_pitch']
            loop_s = meta['loop_start']
            loop_e = meta['loop_end']

        wav_path = os.path.join(WAV_DIR, wav_name)
        with wave.open(wav_path, 'r') as w:
            raw = w.readframes(w.getnframes())
        pcm16 = list(struct.unpack('<%dh' % (len(raw) // 2), raw))
        n_samples = len(pcm16)

        if loop_e > n_samples: loop_e = n_samples

        # 归一化到 12-bit
        peak = max(abs(s) for s in pcm16)
        scale = 2047.0 / peak if peak > 0 else 1.0
        normalized = [int(s * scale) for s in pcm16]

        adpcm_data, nib_count, loop_snap = adpcm_encode(normalized, snapshot_nibble=loop_s)
        offset = len(all_data)

        entries.append({
            'name': display_name,
            'offset': offset,
            'n_bytes': len(adpcm_data),
            'n_nibbles': nib_count,
            'orig_pitch': orig_pitch,
            'loop_start': loop_s,
            'loop_end': loop_e,
            'n_samples': n_samples,
            'loop_acc': loop_snap[0] if loop_snap else 0,
            'loop_step': loop_snap[1] if loop_snap else 0,
        })

        all_data.extend(adpcm_data)
        total_nib += nib_count

        print(f"  {display_name:12s} offset={offset:5d}  {len(adpcm_data):5d}B  {nib_count:6d}nib  op={orig_pitch:3d}  loop={loop_s}->{loop_e}")

    # 对齐到 16 字节
    while len(all_data) % 16:
        all_data.append(0)
    rom_size = len(all_data)

    print(f"\n  Total: {rom_size}B ({rom_size / 1024:.1f} KB), {total_nib} nibbles, {len(entries)} instruments")

    # 生成 C header
    header_path = os.path.join(OUT_DIR, 'sf2_rom.h')
    with open(header_path, 'w') as f:
        f.write('/*\n    SF2 Sample Instruments ADPCM ROM\n    10 instruments, normalized 12-bit, YM2608 ADPCM Type-A\n')
        f.write(f'    Total: {rom_size}B ({rom_size / 1024:.1f} KB)\n*/\n\n')

        # ROM 数据
        f.write(f'static const unsigned char code SF2_ROM[{rom_size}] = {{\n')
        addr = 0
        for i, entry in enumerate(entries):
            f.write(f'/* {i}: {entry["name"]}  {entry["n_bytes"]}B  op={entry["orig_pitch"]}  loop={entry["loop_start"]}->{entry["loop_end"]} */\n')
            end = entry['offset'] + entry['n_bytes']
            while addr < end:
                chunk = all_data[addr:min(addr + 16, end)]
                hex_line = ', '.join(f'0x{b:02X}' for b in chunk)
                f.write(hex_line + ',\n')
                addr += 16
        # padding
        while addr < rom_size:
            chunk = all_data[addr:min(addr + 16, rom_size)]
            hex_line = ', '.join(f'0x{b:02X}' for b in chunk)
            f.write(hex_line + ',\n')
            addr += 16
        f.write('};\n\n')

        # 乐器表
        f.write(f'#define SF2_INST_COUNT  {len(entries)}\n\n')

        f.write('/* 每乐器: offset(nibble addr), loop_start(nibble), loop_end(nibble), n_nibbles, orig_pitch */\n')
        f.write(f'static const u16 code sf2_start[SF2_INST_COUNT] = {{\n')
        for e in entries:
            nm = e["name"]
            f.write(f'    {e["offset"] * 2},    /* {nm} */\n')
        f.write('};\n\n')

        f.write(f'static const u16 code sf2_loop_start[SF2_INST_COUNT] = {{\n')
        for e in entries:
            nm = e["name"]
            f.write(f'    {e["loop_start"]},    /* {nm} */\n')
        f.write('};\n\n')

        f.write(f'static const u16 code sf2_loop_end[SF2_INST_COUNT] = {{\n')
        for e in entries:
            nm = e["name"]
            f.write(f'    {e["loop_end"]},    /* {nm} */\n')
        f.write('};\n\n')

        f.write(f'static const u16 code sf2_nib_count[SF2_INST_COUNT] = {{\n')
        for e in entries:
            f.write(f'    {e["n_nibbles"]},    /* {e["name"]} */\n')
        f.write('};\n\n')

        f.write(f'static const u8 code sf2_orig_pitch[SF2_INST_COUNT] = {{\n')
        for e in entries:
            f.write(f'    {e["orig_pitch"]},    /* {e["name"]} */\n')
        f.write('};\n\n')

        # loop 回绕时 acc/step 重置值 (12-bit signed, 0..768)
        f.write(f'static const s16 code sf2_loop_acc[SF2_INST_COUNT] = {{\n')
        for e in entries:
            a = e['loop_acc']
            if a & 0x800: a = a - 0x1000  # sign extend 12-bit
            f.write(f'    {a},    /* {e["name"]} */\n')
        f.write('};\n\n')

        f.write(f'static const u16 code sf2_loop_step[SF2_INST_COUNT] = {{\n')
        for e in entries:
            f.write(f'    {e["loop_step"]},    /* {e["name"]} */\n')
        f.write('};\n\n')

        # 乐器名称表 (调试用)
        f.write(f'static const u8 code sf2_names[SF2_INST_COUNT][8] = {{\n')
        for e in entries:
            name_bytes = e['name'].encode('ascii')[:8].ljust(8, b'\0')
            hex_name = ', '.join(f"0x{b:02X}" for b in name_bytes)
            f.write(f'    {{{hex_name}}},  /* {e["name"]} */\n')
        f.write('};\n\n')

    print(f"\n  Written: {header_path}")


if __name__ == '__main__':
    main()
