#!/usr/bin/env python3
"""BRR ROM decode 验证 - 用 C251 下位机完全一致的逻辑解码

从 brr_rom.h 提取 BRR 数据, 用两种方式解码:
  1. GME 标准解码 (brr_test.py 已验证)
  2. C251 下位机 brr_decode_one 逻辑 (此脚本)

对比两者输出, 如果不同则说明下位机有 bug。
最后渲染 WAV 供试听。
"""

import struct, wave, re, os, sys

# 从 brr_rom.h 提取数据
BRR_ROM_H = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          '..', 'STC32G12K128', 'brr_rom.h')
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'brr_wav')
os.makedirs(OUT_DIR, exist_ok=True)
TARGET_RATE = 17640

# GME shifts
RIGHT_SHIFT = [13,12,12,12,12,12,12,12,12,12,12,12,13,16,16,16]
LEFT_SHIFT  = [ 0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9,10,11,11,11,11]

INST_NAMES = [
    'ElecPiano', 'Violin', 'Strings', 'Harp', 'Accordion', 'Organ',
    'Fretless', 'JazzGtr', 'DistGtr', 'Celesta', 'Flute',
    'Recorder', 'Oboe', 'Clarinet',
]


def parse_brr_rom_h():
    """解析 brr_rom.h, 提取乐器数据和描述表"""
    with open(BRR_ROM_H, 'r', errors='replace') as f:
        text = f.read()

    # 提取每个 brr_rom_N[] 数组
    instruments = []
    for i in range(50):  # 最多 50 个
        pattern = rf'static const u8 code brr_rom_{i}\[\] = {{\s*\n'
        m = re.search(pattern, text)
        if not m:
            break
        # 提取到 };
        start = m.end()
        end = text.find('};', start)
        hex_str = text[start:end]
        data = bytes(int(b, 16) for b in re.findall(r'0x([0-9A-Fa-f]{2})', hex_str))
        instruments.append(data)

    # 提取 brr_inst[] 描述表
    inst_pattern = re.compile(
        r'\{\s*brr_rom_(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\s*\}.*?/\*\s*(\w+)\s*\*/')
    insts = []
    for m in inst_pattern.finditer(text):
        rom_idx = int(m.group(1))
        n_blocks = int(m.group(2))
        loop_block = int(m.group(3))
        native_midi = int(m.group(4))
        vol = int(m.group(5))
        name = m.group(6)
        insts.append({
            'rom_idx': rom_idx,
            'blocks': instruments[rom_idx],
            'n_blocks': n_blocks,
            'loop_block': loop_block,
            'native_midi': native_midi,
            'vol': vol,
            'name': name,
        })

    return insts


# ========== GME 标准解码 (参考 brr_test.py, filter=0) ==========
def gme_decode_block(block_data):
    header = block_data[0]
    scale = header >> 4
    rs = RIGHT_SHIFT[scale]
    ls = LEFT_SHIFT[scale]
    samples = []
    for byte_pair in range(4):
        byte0 = block_data[1 + byte_pair * 2]
        byte1 = block_data[2 + byte_pair * 2]
        nybbles = (byte0 * 256 + byte1) & 0xFFFF
        for _ in range(4):
            nybbles &= 0xFFFF
            raw = nybbles if nybbles < 0x8000 else nybbles - 0x10000
            s = ((raw >> rs) & 0xFFFF) << ls
            s &= 0xFFFF
            if s >= 0x8000:
                s -= 0x10000
            s *= 2
            if s > 32767: s = 32767
            if s < -32768: s = -32768
            samples.append(s)
            nybbles <<= 4
    return samples


# ========== C251 下位机 brr_decode_one 逻辑 ==========
def c251_decode_one(blocks_data, n_blocks, inst_idx, block_idx, sample_idx):
    """模拟修复后的 brr_decode_one (GME 方式: <<= sp*4)"""
    p_offset = block_idx * 9
    header = blocks_data[p_offset]
    scale = header >> 4
    if scale > 15: scale = 15
    rs = RIGHT_SHIFT[scale]
    ls = LEFT_SHIFT[scale]
    bp = sample_idx >> 2
    sp = sample_idx & 0x03
    b0 = blocks_data[p_offset + 1 + bp*2]
    b1 = blocks_data[p_offset + 2 + bp*2]
    nybbles = ((b0 << 8) | b1) & 0xFFFF

    # GME: 左移 sp*4 把目标 nybble 推到 bit15-12
    nybbles = (nybbles << (sp << 2)) & 0xFFFF
    raw = nybbles if nybbles < 0x8000 else nybbles - 0x10000
    raw >>= rs
    s = ((raw & 0xFFFF) << ls) & 0xFFFF
    s = s if s < 0x8000 else s - 0x10000
    s = (s * 2) & 0xFFFF
    s = s if s < 0x8000 else s - 0x10000
    if s > 32767: s = 32767
    if s < -32768: s = -32768
    return s


def decode_all_gme(blocks_data, n_blocks):
    samples = []
    for b in range(n_blocks):
        samples.extend(gme_decode_block(blocks_data[b*9:(b+1)*9]))
    return samples


def decode_all_c251(blocks_data, n_blocks):
    samples = []
    for b in range(n_blocks):
        for s in range(16):
            samples.append(c251_decode_one(blocks_data, n_blocks, 0, b, s))
    return samples


def render_loop_gme(blocks_data, n_blocks, loop_block, dur=3.0, pitch_step=0x0100):
    """用 GME 解码 + 8.8 step 模拟下位机 render"""
    n_frames = int(dur * TARGET_RATE)
    out = []
    # 预解码所有采样
    all_samples = decode_all_gme(blocks_data, n_blocks)
    total_samples = len(all_samples)

    s_cur = all_samples[0]
    s_prev = 0
    sample_pos = 0  # float sample position
    now_step = 0

    for _ in range(n_frames):
        now_step += pitch_step
        while now_step >= 0x0100:
            s_prev = s_cur
            sample_pos += 1
            # loop
            if sample_pos >= total_samples:
                sample_pos = loop_block * 16
            s_cur = all_samples[sample_pos]
            now_step -= 0x0100

        frac = now_step
        if frac > 0 and pitch_step < 0x0100:
            val = s_prev + (s_cur - s_prev) * frac / 256
        else:
            val = s_cur
        out.append(max(-32768, min(32767, int(val))))

    return out


def render_loop_c251(blocks_data, n_blocks, loop_block, dur=3.0, pitch_step=0x0100):
    """用 C251 decode_one + 8.8 step 模拟下位机 render"""
    n_frames = int(dur * TARGET_RATE)
    out = []

    block_idx = 0
    sample_in_block = 0
    s_cur = c251_decode_one(blocks_data, n_blocks, 0, block_idx, sample_in_block)
    s_prev = 0
    now_step = 0

    for _ in range(n_frames):
        now_step += pitch_step
        while now_step >= 0x0100:
            s_prev = s_cur
            sample_in_block += 1
            if sample_in_block >= 16:
                sample_in_block = 0
                block_idx += 1
                if block_idx >= n_blocks:
                    block_idx = loop_block
            s_cur = c251_decode_one(blocks_data, n_blocks, 0, block_idx, sample_in_block)
            now_step -= 0x0100

        frac = now_step
        if frac > 0 and pitch_step < 0x0100:
            val = s_prev + (s_cur - s_prev) * frac / 256
        else:
            val = s_cur
        out.append(max(-32768, min(32767, int(val))))

    return out


def write_wav(path, samples, rate=TARGET_RATE):
    with wave.open(path, 'w') as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(rate)
        wf.writeframes(struct.pack('<%dh' % len(samples), *samples))


def main():
    insts = parse_brr_rom_h()
    print(f"解析到 {len(insts)} 个乐器")

    # 只解码前 3 个做验证 (可改)
    test_count = min(14, len(insts))

    for i in range(test_count):
        inst = insts[i]
        name = inst['name']
        blocks = inst['blocks']
        n_blocks = inst['n_blocks']
        loop_block = inst['loop_block']
        native_midi = inst['native_midi']

        print(f"\n[{i}] {name}: {n_blocks} blocks, loop_block={loop_block}, native_midi={native_midi}")

        # GME 解码全部
        gme_all = decode_all_gme(blocks, n_blocks)

        # C251 解码全部
        c251_all = decode_all_c251(blocks, n_blocks)

        # 对比
        n = min(len(gme_all), len(c251_all))
        diffs = [abs(gme_all[j] - c251_all[j]) for j in range(n)]
        max_diff = max(diffs) if diffs else 0
        avg_diff = sum(diffs) / n if n > 0 else 0
        match = sum(1 for d in diffs if d == 0)

        print(f"  GME vs C251: max_diff={max_diff}, avg_diff={avg_diff:.2f}, "
              f"exact_match={match}/{n} ({100*match/n:.1f}%)")

        # 打印前 32 个采样对比
        print(f"  前32采样对比 (GME / C251 / diff):")
        for j in range(min(32, n)):
            print(f"    [{j:2d}] {gme_all[j]:6d} / {c251_all[j]:6d} / {diffs[j]:4d}")

        # 渲染 WAV (GME)
        gme_wav = render_loop_gme(blocks, n_blocks, loop_block, dur=3.0, pitch_step=0x0100)
        gme_peak = max(abs(s) for s in gme_wav)
        write_wav(os.path.join(OUT_DIR, f'{name}_gme_native.wav'), gme_wav)
        print(f"  GME  native: peak={gme_peak}")

        # 渲染 WAV (C251)
        c251_wav = render_loop_c251(blocks, n_blocks, loop_block, dur=3.0, pitch_step=0x0100)
        c251_peak = max(abs(s) for s in c251_wav)
        write_wav(os.path.join(OUT_DIR, f'{name}_c251_native.wav'), c251_wav)
        print(f"  C251 native: peak={c251_peak}")

        # 上行变频 (C251)
        midi = native_midi + 12  # 高一个八度
        semi = midi - native_midi
        step = int(round(0x0100 * (2.0 ** (semi / 12.0))))
        c251_up = render_loop_c251(blocks, n_blocks, loop_block, dur=3.0, pitch_step=step)
        write_wav(os.path.join(OUT_DIR, f'{name}_c251_up12.wav'), c251_up)
        print(f"  C251 +12semi: step=0x{step:04X}, peak={max(abs(s) for s in c251_up)}")

    print(f"\nWAV 输出: {OUT_DIR}/")
    print("试听 *_gme_native.wav (正常) vs *_c251_native.wav (下位机逻辑)")
    print("如果 C251 版本破音, 说明下位机 decode 有 bug")


if __name__ == '__main__':
    main()
