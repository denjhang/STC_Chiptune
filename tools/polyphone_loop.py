#!/usr/bin/env python3
"""Polyphone 风格自动 loop 点搜索 + crossfade 烘焙

移植自 Polyphone (sampleutils.cpp) 的 loopStep1/loopStep2 算法:
  1. 找信号稳态区
  2. 只在过零点(负→正)选 loop start/end
  3. 多点质量评分: 值差(0.45) + 斜率差(0.33) + 二阶差(0.22)
  4. 综合评分: 200*quality + lengthScore, 越小越好
  5. Crossfade 烘焙进 PCM, 保证 ADPCM 无缝
"""

import struct, os, wave, json, math

WAV_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'adpcm_wav')
OUT_DIR = os.path.join(WAV_DIR, 'poly_loop')
os.makedirs(OUT_DIR, exist_ok=True)

SF2_ROOT = 'D:/working/vscode-projects/Reference_Project/STC-MCU/sf2_extract'
TARGET_RATE = 17640

# ADPCM 编解码 (和 sf2_preview.py 一致)
STEPS = [16,17,19,21,23,25,28,31,34,37,41,45,50,55,60,66,
         73,80,88,97,107,118,130,143,157,173,190,209,230,253,279,307,337,371,408,449,494,544,598,658,724,796,876,963,1060,1166,1282,1411,1552]

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

# 问题乐器
PROBLEM_LIST = [
    ('04_oboe.wav',       'snes_unofficial', 102, 'Oboe'),
    ('06_blow.wav',       'microgm',         207, 'Blow'),
    ('09_harp.wav',       'snes_unofficial', 90, 'Harp'),
    ('03_shakuhachi.wav', 'microgm',         211, 'Shakuhachi'),
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


# ===== Polyphone 算法移植 =====

def get_diff_for_loop_quality(data, pos1, pos2):
    """Polyphone: getDiffForLoopQuality — 值差+斜率差+二阶差"""
    diff0 = data[pos1] - data[pos2]
    diff1 = data[pos1 - 1] - data[pos2 - 1] - diff0
    diff2 = data[pos1 - 2] - data[pos2 - 2] - 2 * diff1 + diff0
    return 0.45 * abs(diff0) + 0.33 * abs(diff1) + 0.22 * abs(diff2)


def compute_loop_quality(data, loop_start, loop_end, check_number, bipolar, max_value):
    """Polyphone: computeLoopQuality"""
    length = len(data)
    if loop_start < 2 or loop_start >= loop_end or loop_end >= length:
        return 0

    n = 1
    result = get_diff_for_loop_quality(data, loop_start, loop_end)

    offset = 3
    for i in range(1, check_number):
        offset += int((math.pi / 2 + i - 1) * i)
        if loop_start > 3 + offset:
            result += get_diff_for_loop_quality(data, loop_start - offset - 1, loop_end - offset - 1)
            n += 1

    if bipolar:
        offset = 3
        for i in range(1, check_number):
            offset += int((math.pi / 2 + i - 1) * i)
            if loop_end + 3 + offset < length:
                result += get_diff_for_loop_quality(data, loop_start + offset - 1, loop_end + offset - 1)
                n += 1

    return result / (max_value * n)


def regime_permanent(data, sample_rate):
    """Polyphone: regimePermanent — 找振幅稳定区"""
    size = len(data)
    size_period = sample_rate // 10
    if size < size_period:
        return 0, size - 1

    nb_values = (size - size_period) // (sample_rate // 20)
    if nb_values == 0:
        return 0, size - 1

    averages = []
    for i in range(nb_values):
        val = 0
        for j in range(size_period):
            val += abs(data[(sample_rate // 20) * i + j])
        averages.append(val / size_period)

    med = sorted(averages)[nb_values // 2]
    pos_start = 0; pos_end = nb_values - 1
    count = 0
    # 从左找连续稳态
    while count < 10 and pos_start <= pos_end:
        if averages[pos_start] < 1.05 * med and averages[pos_start] > med / 1.05:
            count += 1
        else:
            count = 0
        pos_start += 1
    pos_start = pos_start + 2 - count
    # 从右找连续稳态
    count = 0
    while count < 10 and pos_end > 0:
        if averages[pos_end] < 1.05 * med and averages[pos_end] > med / 1.05:
            count += 1
        else:
            count = 0
        pos_end -= 1
    pos_end += count - 2

    pos_start = pos_start * (sample_rate // 20)
    pos_end = pos_end * (sample_rate // 20) + size_period
    return pos_start, pos_end


def loop_step1(data, sample_rate):
    """Polyphone: loopStep1 — 搜索最佳 loop 点对"""
    size = len(data)

    # 稳态区 (短采样跳过, 直接用全范围)
    pos_start, pos_end = regime_permanent(data, sample_rate)
    if pos_start >= pos_end or pos_end <= 0:
        pos_start = max(2, size // 10)
        pos_end = size - max(2, size // 10)

    # 限制搜索范围
    if size > 40000:
        pos_start = max(pos_start, 4000)
        pos_end = min(pos_end, size - 400)
    elif size > 4000:
        pos_start = max(pos_start, 400)
        pos_end = min(pos_end, size - 400)
    else:
        pos_start = max(pos_start, 2)
        pos_end = min(pos_end, size - 1)

    # 找所有过零点 (负→正)
    cross_positions = []
    for i in range(pos_start, pos_end):
        if data[i - 1] < 0 and data[i] >= 0:
            cross_positions.append(i)
    if len(cross_positions) < 2:
        return None, None, 0

    # loop start 最小位置 (搜索区 25% 处, 不超过 1 秒)
    min_loop_start = pos_start + 0.25 * (pos_end - pos_start)
    if min_loop_start > sample_rate:
        min_loop_start = sample_rate
    min_ls_idx = 0
    for i in range(len(cross_positions)):
        if cross_positions[i] > min_loop_start:
            min_ls_idx = i
            break

    # loop end 最小位置
    min_loop_end = pos_start + 0.25 * (pos_end - pos_start)
    min_le_idx = 0
    for i in range(len(cross_positions)):
        if cross_positions[i] > min_loop_end:
            min_le_idx = i
            break

    # 过零点密度
    position_density = len(cross_positions) / size * sample_rate

    # 信号最大值
    max_val = max(abs(s) for s in data)
    if max_val < 1:
        max_val = 1

    # 检查次数
    check_number = int(22 - position_density / 150)
    if check_number < 8:
        check_number = 8

    best_rank = 999999
    best_ls = 0; best_le = 0
    best_quality = 0

    for i in range(min_ls_idx, len(cross_positions) - 1):
        cur_ls = cross_positions[i]
        for j in range(len(cross_positions) - 1, max(min_le_idx, i + 1) - 1, -1):
            cur_le = cross_positions[j]
            length_score = max(3.0, (pos_end - pos_start) / (cur_le - cur_ls))
            if length_score > best_rank:
                continue

            quality = compute_loop_quality(data, cur_ls, cur_le, check_number, True, max_val)
            rank = 200.0 * quality + length_score
            if rank < best_rank:
                best_quality = quality
                best_rank = rank
                best_ls = cur_ls
                best_le = cur_le

    # crossfade 长度
    cf_len = int(best_quality * sample_rate / (5 + 0.75 * check_number))
    cf_len = cf_len * cf_len  # 平方
    cf_len = min(cf_len, best_ls - pos_start)

    return best_ls, best_le, cf_len


def loop_step2(data, loop_start, loop_end, cf_len):
    """Polyphone: loopStep2 — Crossfade 烘焙进 PCM"""
    data = list(data)
    if cf_len < 2:
        return data, loop_end

    # 交叉淡出: loop_end 前的 cf_len 个样本渐变到 loop_start 前对应位置
    for i in range(cf_len):
        alpha = i / (cf_len - 1)
        pos_end = loop_end - cf_len + i
        pos_start = loop_start - cf_len + i
        data[pos_end] = (1 - alpha) * data[pos_end] + alpha * data[pos_start]

    # 追加 8 个样本 (复制 loop_start 后的数据)
    for i in range(8):
        data.append(data[loop_start + i])

    return data, loop_end


def check_adpcm_seam(norm, ls, le):
    """检查 ADPCM 解码器在 loop 接缝处的状态差"""
    rom, nib_count, snap_ls = adpcm_encode(norm, snap_nibble=ls)
    ls_acc = snap_ls[0] if snap_ls else 0
    ls_step = snap_ls[1] if snap_ls else 0

    # 解码到 le 处
    acc = 0; step = 0; addr = 0
    for i in range(le + 1):
        byte_val = rom[addr >> 1]
        nib = (byte_val >> 4) & 0x0F if not (addr & 1) else byte_val & 0x0F
        d = JEDI_FLAT[step + nib]
        acc += d; acc &= 0xFFF
        if acc & 0x800: acc |= ~0xFFF
        step += STEP_INC[nib & 7]
        if step < 0: step = 0
        if step > 768: step = 768
        addr += 1

    pcm_diff = abs(norm[le] - norm[ls])
    acc_diff = abs(ls_acc - (acc & 0xFFF))
    step_diff = abs(ls_step - step)
    return pcm_diff, acc_diff, step_diff


def main():
    for wav_name, sf2_src, sf2_id, display in PROBLEM_LIST:
        meta_path = os.path.join(SF2_ROOT, sf2_src, 'sf2_mapping.json')
        with open(meta_path) as f:
            data = json.load(f)
        meta = data['samples'][str(sf2_id)]
        orig_ls = meta['loop_start']
        orig_le = meta['loop_end']
        orig_pitch = meta['orig_pitch']

        with wave.open(os.path.join(WAV_DIR, wav_name), 'r') as w:
            raw = w.readframes(w.getnframes())
        pcm16 = list(struct.unpack('<%dh' % (len(raw) // 2), raw))
        peak = max(abs(s) for s in pcm16)
        scale = 2047.0 / peak
        norm = [int(s * scale) for s in pcm16]

        # 原始 loop 接缝质量
        orig_pcm, orig_acc, orig_step = check_adpcm_seam(norm, orig_ls, orig_le)
        print(f'{display:12s} orig: ls={orig_ls} le={orig_le} '
              f'pcm_d={orig_pcm} acc_d={orig_acc} step_d={orig_step}')

        # Polyphone 搜索新 loop 点 (用 float 数据, 归一化到 -1..1)
        float_data = [s / 2047.0 for s in norm]
        new_ls, new_le, cf_len = loop_step1(float_data, TARGET_RATE)

        if new_ls is None:
            print(f'  FAILED to find loop points\n')
            continue

        print(f'  poly:  ls={new_ls} le={new_le} cf_len={cf_len}')

        # 应用 crossfade
        patched, new_le_end = loop_step2(norm, new_ls, new_le, cf_len)

        # crossfade 后的 ADPCM 接缝检查
        new_pcm, new_acc, new_step = check_adpcm_seam(patched, new_ls, new_le)
        print(f'  after: pcm_d={new_pcm} acc_d={new_acc} step_d={new_step}')

        # 编码 + 渲染预览
        rom, nib_count, snap = adpcm_encode(patched, snap_nibble=new_ls)
        loop_acc = snap[0] if snap else 0
        loop_step = snap[1] if snap else 0
        if loop_acc & 0x800: loop_acc = loop_acc - 0x1000

        for midi in [60, 72]:
            note_name = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
            nn = f'{note_name[midi%12]}{midi//12-1}'
            out = render_voice(rom, nib_count, new_ls, new_le, loop_acc, loop_step,
                               midi, orig_pitch, dur=4.0)
            out_path = os.path.join(OUT_DIR, f'{display}_{nn}_poly.wav')
            with wave.open(out_path, 'w') as wf:
                wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(TARGET_RATE)
                wf.writeframes(struct.pack('<%dh' % len(out), *out))
            print(f'  -> {out_path}')
        print()


if __name__ == '__main__':
    main()
