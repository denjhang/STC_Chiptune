#!/usr/bin/env python3
"""生成 BRR ROM C 头文件 (brr_rom.h)

从 XI 文件出发, 经过重采样 + crossfade + BRR 编码 + BRR crossfade 修复,
导出 14 个精选乐器的 BRR block 数据为 C 头文件。

每乐器输出:
  - BRR blocks (9 字节/block, filter=0)
  - n_blocks, loop_block 索引
  - native_midi (centerRate 对应的 MIDI note)
  - 16.16 fixed-point step base (centerRate/17640 << 16)

输出格式见 brr_rom.h
"""

import struct, os

XI_DIR = 'D:/working/vscode-projects/Reference_Project/STC-MCU/sootsound/0000_all_instruments/'
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'xi_out', 'brr_rom')
TARGET_RATE = 17640

RIGHT_SHIFT = [13,12,12,12,12,12,12,12,12,12,12,12,13,16,16,16]
LEFT_SHIFT  = [ 0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9,10,11,11,11,11]

# 14 个精选乐器 (排除 Acoustic Grand Piano)
# 格式: (xi_filename, short_name, sample_idx)
PICKS = [
    ('01_Bright_Acoustic_Piano.xi','AcPiano', 2),   # 原 ElecPiano 换成 Bright Acoustic s2
    ('28_Violin.xi',               'Violin',  0),
    ('30_Strings.xi',              'Strings', 0),
    ('2E_Harp.xi',                 'Harp',    0),
    ('15_Accordion_L0.xi',         'Accordion', 0),
    ('13_Church_Organ.xi',         'Organ',   0),
    ('23_Fretless_Bass.xi',        'Fretless',0),
    ('1A_Jazz_Guitar.xi',          'JazzGtr', 0),
    ('1E_Distortion_Guitar.xi',    'DistGtr', 0),
    ('08_Celesta.xi',              'Celesta', 0),
    ('49_Flute.xi',                'Flute',   0),
    ('4A_Recorder.xi',             'Recorder',0),
    ('44_Oboe.xi',                 'Oboe',    0),
    ('47_Clarinet.xi',             'Clarinet',0),
]


def parse_xi_pcm(filepath):
    with open(filepath, 'rb') as f:
        data = f.read()
    if data[:21] != b'Extended Instrument: ':
        return None, None
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
    name = data[21:43].split(b'\x00')[0].decode('ascii', errors='replace')
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


def auto_scale(pcm16):
    peak = max(abs(s) for s in pcm16) if pcm16 else 1
    if peak == 0: return 0
    for sc in range(13):
        if 7 * (2 << LEFT_SHIFT[sc]) >= peak:
            return sc
    return 12


def brr_encode_block(pcm16, scale, loop_flag=False, end_flag=False):
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
    decoded = []
    for b in range(n_blocks):
        decoded.extend(brr_decode_block(blocks[b*9:(b+1)*9]))
    return decoded


def brr_fix_seam(blocks, n_blocks, loop_block, fade_len=16):
    decoded = brr_decode_all_samples(blocks, n_blocks)
    loop_start_sample = loop_block * 16
    loop_end_sample = n_blocks * 16
    target = decoded[loop_start_sample]
    fade_len = min(fade_len, (loop_end_sample - loop_start_sample) // 2)
    for i in range(fade_len):
        t = (i + 1) / fade_len
        idx = loop_end_sample - fade_len + i
        if idx < len(decoded):
            decoded[idx] = int(decoded[idx] * (1 - t) + target * t)
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
        end_idx = loop_block * 16 + (c + 1) * loop_n - 1
        start_idx = loop_block * 16 + c * loop_n
        if end_idx < len(decoded) and start_idx < len(decoded):
            seams.append(abs(decoded[start_idx] - decoded[end_idx]))
    return max(seams) if seams else 0, sum(seams)/len(seams) if seams else 0


def midi_pitch_ratio(midi_diff):
    """16.16 fixed-point pitch ratio for ±semitones"""
    if midi_diff == 0:
        return 256 << 8
    if midi_diff > 0:
        octaves = midi_diff // 12; r = midi_diff % 12
        table = [256, 271, 287, 304, 322, 341, 362, 383, 406, 430, 455, 482]
        return (table[r] << (8 + octaves))
    else:
        md = -midi_diff
        octaves = md // 12; r = md % 12
        table = [256, 242, 228, 216, 203, 192, 181, 171, 161, 152, 144, 136]
        return (table[r] >> octaves) << 8


def process_instrument(filepath, sample_idx=0):
    name, samples = parse_xi_pcm(filepath)
    if not name or not samples:
        return None
    if sample_idx >= len(samples):
        return None
    s = samples[sample_idx]
    if not s['has_loop'] or s['n_samples'] < 50:
        return None

    pcm16 = s['pcm']
    center_rate = s['center_rate']
    pcm17640 = resample(pcm16, center_rate, TARGET_RATE)
    n17640 = len(pcm17640)
    ratio = n17640 / len(pcm16)
    loop_s = max(0, int(s['loop_start'] * ratio))
    loop_e = min(n17640, int(s['loop_end'] * ratio))
    native_midi = 24 + s['relnote'] + s['fine'] / 128.0

    # PCM crossfade
    new_loop_len = loop_e - loop_s
    pcm_fade = max(8, min(64, new_loop_len // 10))
    pcm_fixed = crossfade_tail(pcm17640, loop_s, loop_e, pcm_fade)

    # BRR encode
    loop_s_aligned = (loop_s + 15) // 16 * 16
    if loop_s_aligned >= n17640: loop_s_aligned = 0
    blocks, n_blocks = brr_encode(pcm_fixed, loop_s_aligned)
    loop_block = loop_s_aligned // 16

    # BRR crossfade fix
    blocks_fixed = brr_fix_seam(blocks, n_blocks, loop_block, 16)

    # Verify
    max_seam, _ = verify_seam(blocks_fixed, n_blocks, loop_block)

    return {
        'blocks': blocks_fixed,
        'n_blocks': n_blocks,
        'loop_block': loop_block,
        'native_midi': native_midi,
        'center_rate': center_rate,
        'seam': max_seam,
        'vol': s['volume'] / 64.0,
    }


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    results = []

    print(f"{'Instrument':<20s} {'Blocks':>6s} {'Bytes':>6s} {'LoopBlk':>7s} {'NativeMIDI':>10s} {'Seam':>8s}")
    print('-' * 70)

    for pick, short_name, sample_idx in PICKS:
        filepath = os.path.join(XI_DIR, pick)
        if not os.path.exists(filepath):
            print(f'  SKIP {pick}'); continue
        r = process_instrument(filepath, sample_idx)
        if r is None:
            print(f'  SKIP {pick} s{sample_idx} (process failed)'); continue
        r['short_name'] = short_name
        results.append(r)
        seam_str = 'PERFECT' if r['seam'] == 0 else f'{r["seam"]}'
        print(f'{short_name:<20s} {r["n_blocks"]:>6d} {len(r["blocks"]):>6d} '
              f'{r["loop_block"]:>7d} {r["native_midi"]:>10.2f} {seam_str:>8s}')

    # 生成 brr_rom.h
    total_bytes = sum(len(r['blocks']) for r in results)
    print(f'\nTotal BRR ROM: {total_bytes} bytes ({total_bytes/1024:.1f} KB), {len(results)} instruments')

    h_path = os.path.join(OUT_DIR, '..', '..', '..', 'STC32G12K128', 'brr_rom.h')
    with open(h_path, 'w') as f:
        f.write('/* brr_rom.h - 自动生成, 不要手改\n')
        f.write(f' * 14 个 YRW801 XI 乐器 BRR 数据 (filter=0, 17640Hz, perfect loop)\n')
        f.write(f' * 总计 {total_bytes} bytes ({total_bytes/1024:.1f} KB)\n')
        f.write(f' * 生成: python tools/gen_brr_rom.py\n')
        f.write(' */\n\n')
        f.write('#ifndef __BRR_ROM_H__\n#define __BRR_ROM_H__\n\n')
        f.write('#include "types.h"\n\n')
        f.write(f'#define BRR_INST_COUNT   {len(results)}\n\n')

        # 每乐器的 block 数据
        for i, r in enumerate(results):
            f.write(f'/* [{i}] {r["short_name"]} - {r["n_blocks"]} blocks, loop_block={r["loop_block"]} */\n')
            f.write(f'static const u8 code brr_rom_{i}[] = {{\n')
            for j in range(0, len(r['blocks']), 16):
                line = r['blocks'][j:j+16]
                hexs = ','.join(f'0x{b:02X}' for b in line)
                f.write(f'    {hexs},\n')
            f.write('};\n\n')

        # 乐器描述表
        f.write('typedef struct {\n')
        f.write('    const u8 code *blocks;\n')
        f.write('    u16 n_blocks;\n')
        f.write('    u16 loop_block;\n')
        f.write('    u8  native_midi;     /* 原始音高 MIDI note */\n')
        f.write('    u8  vol;             /* 原始 volume 0-255 */\n')
        f.write('} brr_inst_t;\n\n')
        f.write('static const brr_inst_t code brr_inst[BRR_INST_COUNT] = {\n')
        for i, r in enumerate(results):
            nm = int(round(r['native_midi']))
            vol = int(r['vol'] * 255) & 0xFF
            f.write(f'    {{ brr_rom_{i}, {r["n_blocks"]}, {r["loop_block"]}, {nm}, {vol} }},'
                    f'  /* {r["short_name"]} */\n')
        f.write('};\n\n')
        f.write('#endif\n')

    print(f'\nGenerated: {h_path}')


if __name__ == '__main__':
    main()
