#!/usr/bin/env python3
"""周期复制法: 找基频周期, 取 K 个周期作为段, 复制 N 次

算法:
1. ACF 找末尾段基频 lag
2. 在 lag 附近精确搜索 (找使 |x[i]-x[i+T]| 之和最小的 T)
3. 从末尾取 K * T 个采样作为段
4. 段复制 N 次拼到末尾
5. BRR encode

测试 K (周期数) × N (复制次数):
  J_period_4x5  - 4 周期 × 5 次 = 20 周期
  J_period_4x10 - 4 周期 × 10 次
  J_period_8x5  - 8 周期 × 5 次 = 40 周期
  J_period_16x3 - 16 周期 × 3 次
"""

import struct, os, wave, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from xi_brr_crossfade_test import (
    parse_xi_pcm, resample,
    brr_encode, brr_fix_seam, brr_decode_all_samples,
    verify_seam, render_loop,
)

XI_DIR = 'D:/working/vscode-projects/Reference_Project/STC-MCU/sootsound/0000_all_instruments/'
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'xi_out', 'piano_periodcopy')
TARGET_RATE = 17640

TEST = [
    ('01_Bright_Acoustic_Piano.xi', 0),
    ('01_Bright_Acoustic_Piano.xi', 2),
]

CONFIGS = [
    ('J_period_4x5',   4, 5),
    ('J_period_4x10',  4, 10),
    ('J_period_8x5',   8, 5),
    ('J_period_16x3',  16, 3),
]


def write_wav(path, samples, rate):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, 'w') as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(rate)
        wf.writeframes(struct.pack('<%dh' % len(samples), *samples))


def detect_period(pcm, tail_ms=100):
    """ACF 找基频周期, 返回精确 T"""
    n = len(pcm)
    tail = pcm[max(0, n - int(tail_ms * TARGET_RATE / 1000)):]
    nt = len(tail)

    # 1. ACF 找粗略 lag
    best_lag = 0; best_corr = -1
    for lag in range(20, min(800, nt // 2)):
        c = 0
        for i in range(nt - lag):
            c += tail[i] * tail[i + lag]
        if c > best_corr:
            best_corr = c
            best_lag = lag

    # 2. 在 best_lag ±3 范围精确搜索 (最小绝对差)
    best_T = best_lag; best_diff = 1e18
    for T in range(max(10, best_lag - 3), best_lag + 4):
        diff = 0
        count = 0
        for i in range(nt - T):
            diff += abs(tail[i] - tail[i + T])
            count += 1
        if count > 0 and diff < best_diff:
            best_diff = diff
            best_T = T

    f0 = TARGET_RATE / best_T
    return best_T, f0


def rms_ratio(pcm, start, end):
    tail = pcm[start:end]
    win = max(50, len(tail) // 10)
    vals = []
    for i in range(0, len(tail) - win, win):
        vals.append((sum(x*x for x in tail[i:i+win]) / win) ** 0.5)
    if not vals: return 0
    return max(vals) / max(1, min(vals))


def make_periodcopy(pcm, T, K_periods, N_copies, label):
    """取末尾 K * T 个采样作为段, 复制 N 次拼末尾"""
    n = len(pcm)
    seg_len = K_periods * T
    # 16 对齐 (段长向下取 16 倍数, 通过微调 T 不行, 用 K 调)
    # 改成: 段长直接 16 对齐, 通过调整段长度
    seg_len_aligned = (seg_len // 16) * 16
    if seg_len_aligned < 16: seg_len_aligned = 16

    segment = pcm[n - seg_len_aligned:n]

    # 拼到末尾: 原 PCM + segment * (N-1)  (第 1 份是原末尾)
    extended = pcm[:] + segment * (N_copies - 1)
    loop_s = n - seg_len_aligned
    loop_e = loop_s + seg_len_aligned * N_copies

    # 16 对齐 loop_s
    loop_s_aligned = (loop_s + 15) // 16 * 16
    if loop_s_aligned >= len(extended): loop_s_aligned = 0

    blocks, n_blocks = brr_encode(extended, loop_s_aligned)
    loop_block = loop_s_aligned // 16
    blocks_fixed = brr_fix_seam(blocks, n_blocks, loop_block, 16)
    max_seam, _ = verify_seam(blocks_fixed, n_blocks, loop_block)
    r = rms_ratio(extended, loop_s, loop_e)

    print(f'    {label}: T={T} K={K_periods} N={N_copies} '
          f'seg={seg_len_aligned}({seg_len_aligned/TARGET_RATE*1000:.1f}ms) '
          f'loop=[{loop_s}-{loop_e}] len={loop_e-loop_s} '
          f'({(loop_e-loop_s)/TARGET_RATE*1000:.0f}ms) '
          f'seam={max_seam} rms={r:.3f} bytes={len(blocks_fixed)}')
    return blocks_fixed, n_blocks, loop_block


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    for xi_fn, si in TEST:
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

        T, f0 = detect_period(pcm17640)
        midi = round(69 + 12 * math.log2(f0 / 440)) if f0 > 0 else 0
        NOTES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
        note_name = f'{NOTES[midi%12]}{midi//12-1}' if 0 < midi < 128 else '?'
        print(f'  基频: T={T} samples, f0={f0:.1f}Hz (~{note_name})')

        for lbl, K, N in CONFIGS:
            b, nb, lb = make_periodcopy(pcm17640, T, K, N, lbl)
            decoded = brr_decode_all_samples(b, nb)
            out = render_loop(decoded, lb * 16, nb * 16, 5.0,
                              TARGET_RATE, native_midi, native_midi, vol)
            write_wav(os.path.join(sample_dir, lbl + '.wav'), out, TARGET_RATE)

    print(f'\nFiles in {OUT_DIR}/<short>_s<idx>/')


if __name__ == '__main__':
    main()
