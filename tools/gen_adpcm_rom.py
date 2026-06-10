#!/usr/bin/env python3
"""生成采样乐器 ADPCM ROM C header
读取 tools/adpcm_wav/ 下的 10 个原始 WAV,
归一化 -> ADPCM 编码 -> 输出 C header + 元数据表

编码器和 adpcm_preprocess.py 鼓声编码完全一致 (公式 jedi_table)
"""

import struct, os, wave, json

WAV_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'adpcm_wav')
SF2_ROOT = 'D:/working/vscode-projects/Reference_Project/STC-MCU/sf2_extract'
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'STC32G12K128')

INSTRUMENTS = [
    ('01_piano.wav',      'snes_unofficial', 35, 'Piano'),
    ('02_slapbass.wav',   'snes_unofficial', 34, 'SlapBass'),
    ('03_shakuhachi.wav', 'microgm',         211, 'Shakuhachi'),
    ('04_oboe.wav',       'snes_unofficial', 102, 'Oboe'),
    ('05_trumpet.wav',    'snes_unofficial', 45, 'Trumpet'),
    ('06_blow.wav',       'microgm',         207, 'Blow'),
    ('07_oboe2.wav',      'snes_unofficial', 69, 'Oboe2'),
    ('08_strings.wav',    'snes_unofficial', 50, 'Strings'),
    ('09_harp.wav',       'snes_unofficial', 90, 'Harp'),
    ('10_guitar.wav',     'snes_unofficial', 91, 'Guitar'),
]

# jedi_table: 公式计算 (和 adpcm_preprocess.py 鼓声编码一致)
STEPS = [
    16, 17, 19, 21, 23, 25, 28, 31, 34, 37, 41, 45, 50, 55, 60, 66,
    73, 80, 88, 97, 107, 118, 130, 143, 157, 173, 190, 209, 230, 253,
    279, 307, 337, 371, 408, 449, 494, 544, 598, 658, 724, 796, 876,
    963, 1060, 1166, 1282, 1411, 1552
]

def build_jedi():
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

JEDI = build_jedi()
STEP_INC = [-16, -16, -16, -16, 32, 80, 112, 144]


def adpcm_encode(pcm_samples, snapshot_nibble=-1):
    nibbles = []; acc = 0; step_idx = 0
    snap = None
    for i, s in enumerate(pcm_samples):
        if s > 2047: s = 2047
        if s < -2048: s = -2048
        best_nib = 0; best_diff = abs(s - acc)
        row_idx = step_idx // 16
        for nib in range(16):
            delta = JEDI[row_idx][nib]
            trial = acc + delta; trial &= 0xFFF
            if trial & 0x800: trial |= ~0xFFF
            diff = abs(s - trial)
            if diff < best_diff:
                best_diff = diff; best_nib = nib
        delta = JEDI[row_idx][best_nib]
        acc += delta; acc &= 0xFFF
        if acc & 0x800: acc |= ~0xFFF
        step_idx += STEP_INC[best_nib & 7]
        if step_idx < 0: step_idx = 0
        if step_idx > 768: step_idx = 768
        nibbles.append(best_nib)
        if i == snapshot_nibble:
            snap = (acc & 0xFFF, step_idx)
    result = bytearray()
    for i in range(0, len(nibbles), 2):
        hi = nibbles[i]; lo = nibbles[i + 1] if i + 1 < len(nibbles) else 0
        result.append((hi << 4) | lo)
    return bytes(result), len(nibbles), snap


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

    for wav_name, sf2_src, sf2_id, display_name in INSTRUMENTS:
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
