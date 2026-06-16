#!/usr/bin/env python3
"""极端采样直接复制法: 选取一段, 复制 N 次拼接, 整体 BRR

策略:
  H_brute_100_x3   - 末尾 100ms 复制 3 次 (总长 300ms)
  H_brute_100_x5   - 末尾 100ms 复制 5 次 (总长 500ms)
  H_brute_200_x3   - 末尾 200ms 复制 3 次 (总长 600ms)
  I_autoloop_x3    - AutoLoop 找的段复制 3 次

loop_block = 原 PCM 末尾位置, loop_end = (原 PCM 末尾) + N*段长
"""

import struct, os, wave, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from xi_brr_crossfade_test import (
    parse_xi_pcm, resample,
    brr_encode, brr_fix_seam, brr_decode_all_samples,
    verify_seam, render_loop,
)
from autoloop import find_best_loops

XI_DIR = 'D:/working/vscode-projects/Reference_Project/STC-MCU/sootsound/0000_all_instruments/'
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'xi_out', 'piano_brutecopy')
TARGET_RATE = 17640

TEST = [
    ('01_Bright_Acoustic_Piano.xi', 0),
    ('01_Bright_Aroustic_Piano.xi', 2),
    ('01_Bright_Acoustic_Piano.xi', 2),
]

BRUTE_CONFIGS = [
    ('H_brute_100_x3', 100, 3),
    ('H_brute_100_x5', 100, 5),
    ('H_brute_200_x3', 200, 3),
]


def write_wav(path, samples, rate):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, 'w') as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(rate)
        wf.writeframes(struct.pack('<%dh' % len(samples), *samples))


def rms_ratio(pcm, start, end):
    tail = pcm[start:end]
    win = max(50, len(tail) // 10)
    vals = []
    for i in range(0, len(tail) - win, win):
        vals.append((sum(x*x for x in tail[i:i+win]) / win) ** 0.5)
    if not vals: return 0
    return max(vals) / max(1, min(vals))


def make_brutecopy(pcm, seg_len_samples, copies, label):
    """从末尾取 seg_len_samples, 复制 copies 次, 拼到末尾"""
    n = len(pcm)
    seg = (seg_len_samples // 16) * 16
    if seg > n - 100:
        seg = (n - 100) // 16 * 16
    # 取末尾 seg 个采样作为段
    segment = pcm[n - seg:n]

    # 拼接: 原 PCM + segment × (copies-1)  (第 1 份就是原末尾)
    extended = pcm[:] + segment * (copies - 1)
    # loop 段: [n-seg, n-seg + seg*copies] = copies 个相同段
    loop_s = n - seg
    loop_e = loop_s + seg * copies

    # 16 对齐
    loop_s_aligned = (loop_s + 15) // 16 * 16
    if loop_s_aligned >= len(extended): loop_s_aligned = 0

    # BRR encode (整段, 包括 attack + loop 段)
    blocks, n_blocks = brr_encode(extended, loop_s_aligned)
    loop_block = loop_s_aligned // 16
    blocks_fixed = brr_fix_seam(blocks, n_blocks, loop_block, 16)
    max_seam, _ = verify_seam(blocks_fixed, n_blocks, loop_block)
    r = rms_ratio(extended, loop_s, loop_e)

    print(f'    {label}: seg={seg} x{copies} loop=[{loop_s}-{loop_e}] '
          f'len={loop_e-loop_s} ({(loop_e-loop_s)/TARGET_RATE*1000:.0f}ms) '
          f'seam={max_seam} rms_ratio={r:.2f} bytes={len(blocks_fixed)}')
    return blocks_fixed, n_blocks, loop_block


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    for xi_fn, si in TEST:
        if 'Aroustic' in xi_fn: continue  # typo guard
        fp = os.path.join(XI_DIR, xi_fn)
        if not os.path.exists(fp): continue
        name, samples = parse_xi_pcm(fp)
        s = samples[si]
        if not s['has_loop'] or s['n_samples'] < 50: continue

        short = xi_fn.replace('.xi', '')
        sample_dir = os.path.join(OUT_DIR, f'{short}_s{si}')
        os.makedirs(sample_dir, exist_ok=True)

        pcm16 = s['pcm']
        center_rate = s['center_rate']
        native_midi = 24 + s['relnote'] + s['fine'] / 128.0
        vol = s['volume'] / 64.0

        pcm17640 = resample(pcm16, center_rate, TARGET_RATE)
        n17640 = len(pcm17640)
        print(f'\n=== {short} s{si} ===')
        print(f'  center={center_rate:.0f}Hz native_midi={native_midi:.1f} '
              f'n17640={n17640} ({n17640/TARGET_RATE*1000:.0f}ms)')

        # H 系列: 末尾段直接复制
        for lbl, seg_ms, copies in BRUTE_CONFIGS:
            seg_samples = int(seg_ms * TARGET_RATE / 1000)
            b, nb, lb = make_brutecopy(pcm17640, seg_samples, copies, lbl)
            decoded = brr_decode_all_samples(b, nb)
            out = render_loop(decoded, lb * 16, nb * 16, 5.0,
                              TARGET_RATE, native_midi, native_midi, vol)
            write_wav(os.path.join(sample_dir, lbl + '.wav'), out, TARGET_RATE)

        # I 系列: AutoLoop 找的段复制 3 次
        loops = find_best_loops(pcm17640, TARGET_RATE,
                                threshold_ratio=0.08,
                                min_loop_sec=0.05,
                                distance_sec=0.05,
                                quality_factor=2000.0,
                                max_candidates=2000,
                                loops_to_return=5,
                                search_start_ratio=0.5)
        if loops:
            best = loops[0]
            seg_len = best[1] - best[0]
            # 从原 pcm 取这段, 复制 3 次拼末尾
            segment = pcm17640[best[0]:best[1]]
            extended = pcm17640[:] + segment * 2  # 原末尾段已是第 1 份? 不一定
            # 上面 segment 来自中部, 不一定是末尾, 直接拼到末尾
            loop_s = len(pcm17640)  # 新 loop 起点在原末尾
            # 不对, 应该把 best 段作为整个新 loop, loop_s = n17640, loop_e = n17640 + seg_len * 3
            # 但 attack 段是原 pcm, 这就变成了 "原 attack + AutoLoop 段 × 3"
            extended = pcm17640[:] + segment * 3
            loop_s = len(pcm17640)
            loop_s_aligned = (loop_s + 15) // 16 * 16
            if loop_s_aligned >= len(extended): loop_s_aligned = 0
            blocks, n_blocks = brr_encode(extended, loop_s_aligned)
            loop_block = loop_s_aligned // 16
            blocks_fixed = brr_fix_seam(blocks, n_blocks, loop_block, 16)
            max_seam, _ = verify_seam(blocks_fixed, n_blocks, loop_block)
            loop_e = loop_s + seg_len * 3
            r = rms_ratio(extended, loop_s, loop_e)
            print(f'    I_autoloop_x3: seg={seg_len} x3 loop=[{loop_s}-{loop_e}] '
                  f'len={loop_e-loop_s} ({(loop_e-loop_s)/TARGET_RATE*1000:.0f}ms) '
                  f'seam={max_seam} rms_ratio={r:.2f} bytes={len(blocks_fixed)}')

            decoded = brr_decode_all_samples(blocks_fixed, n_blocks)
            out = render_loop(decoded, loop_block * 16, n_blocks * 16, 5.0,
                              TARGET_RATE, native_midi, native_midi, vol)
            write_wav(os.path.join(sample_dir, 'I_autoloop_x3.wav'),
                      out, TARGET_RATE)

    print(f'\nFiles in {OUT_DIR}/<short>_s<idx>/')


if __name__ == '__main__':
    main()
