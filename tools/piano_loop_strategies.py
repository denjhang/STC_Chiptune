#!/usr/bin/env python3
"""Loop 策略对比测试: 01_Bright_Acoustic_Piano s0/s2

生成多种 loop 策略的 BRR 试听 WAV, 让用户对比选最佳:

策略列表:
  A_xi_orig         - XI 原始 loop (基线对照)
  B_tail_100ms      - 取末尾 100ms 直接做 loop (无任何修改)
  C_tail_300ms      - 取末尾 300ms 直接做 loop
  D_tail_500ms      - 取末尾 500ms 直接做 loop
  E_tail_500_xfade  - 取末尾 500ms + crossfade 修接缝
  F_autoloop        - AutoLoop 找最佳点 (尾 50% 搜索)
  G_tail_500_norm   - 取末尾 500ms + RMS 归一化 (强制音量恒定)
"""

import struct, os, wave, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from xi_brr_crossfade_test import (
    parse_xi_pcm, resample, crossfade_tail,
    brr_encode, brr_fix_seam, brr_decode_all_samples,
    verify_seam, render_loop,
)
from autoloop import find_best_loops

XI_DIR = 'D:/working/vscode-projects/Reference_Project/STC-MCU/sootsound/0000_all_instruments/'
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'xi_out', 'piano_strategies')
TARGET_RATE = 17640

TEST = [
    ('01_Bright_Acoustic_Piano.xi', 0),
    ('01_Bright_Acoustic_Piano.xi', 2),
]


def write_wav(path, samples, rate):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, 'w') as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(rate)
        wf.writeframes(struct.pack('<%dh' % len(samples), *samples))


def rms_chunk(pcm, start, length):
    chunk = pcm[start:start+length]
    if not chunk: return 0
    return (sum(x*x for x in chunk) / len(chunk)) ** 0.5


def rms_ratio(pcm, start, end):
    """loop 段内分 10 块, 返回 max_rms/min_rms (越接近 1 越平稳)"""
    tail = pcm[start:end]
    win = max(50, len(tail) // 10)
    rms_vals = []
    for i in range(0, len(tail) - win, win):
        rms_vals.append((sum(x*x for x in tail[i:i+win]) / win) ** 0.5)
    if not rms_vals: return 0
    return max(rms_vals) / max(1, min(rms_vals))


def normalize_loop_volume(pcm, loop_s, loop_e):
    """把 loop 段内每 50 个采样的 RMS 强制拉到平均值 (音量恒定)"""
    out = pcm[:]
    win = 50
    # 算 loop 段平均 RMS
    rms_vals = []
    for i in range(loop_s, loop_e - win, win):
        rms_vals.append(rms_chunk(out, i, win))
    if not rms_vals: return out
    target_rms = sum(rms_vals) / len(rms_vals)

    # 逐窗口缩放
    for i in range(loop_s, loop_e - win, win):
        local_rms = rms_chunk(out, i, win)
        if local_rms > 0:
            scale = target_rms / local_rms
            # 限制 scale 范围避免炸音
            scale = max(0.5, min(2.0, scale))
            # 平滑过渡 (避免相邻窗口突变)
            for j in range(win):
                idx = i + j
                if idx < loop_e:
                    out[idx] = max(-32768, min(32767, int(out[idx] * scale)))
    return out


def encode_brr(pcm, loop_s, loop_e, label):
    """通用 BRR encode + seam fix + 验证"""
    n = len(pcm)
    loop_s_aligned = (loop_s + 15) // 16 * 16
    if loop_s_aligned >= n: loop_s_aligned = 0
    blocks, n_blocks = brr_encode(pcm, loop_s_aligned)
    loop_block = loop_s_aligned // 16
    blocks_fixed = brr_fix_seam(blocks, n_blocks, loop_block, 16)
    max_seam, _ = verify_seam(blocks_fixed, n_blocks, loop_block)
    r_ratio = rms_ratio(pcm, loop_s, loop_e)
    print(f'    {label}: loop=[{loop_s}-{loop_e}] len={loop_e-loop_s} '
          f'({(loop_e-loop_s)/TARGET_RATE*1000:.0f}ms) '
          f'seam={max_seam} rms_ratio={r_ratio:.2f} bytes={len(blocks_fixed)}')
    return blocks_fixed, n_blocks, loop_block


def render_brr(blocks, n_blocks, loop_block, native_midi, vol, name, out_dir):
    decoded = brr_decode_all_samples(blocks, n_blocks)
    out = render_loop(decoded, loop_block * 16, n_blocks * 16, 5.0,
                      TARGET_RATE, native_midi, native_midi, vol)
    write_wav(os.path.join(out_dir, name + '.wav'), out, TARGET_RATE)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    for xi_fn, si in TEST:
        fp = os.path.join(XI_DIR, xi_fn)
        name, samples = parse_xi_pcm(fp)
        s = samples[si]
        if not s['has_loop'] or s['n_samples'] < 50: continue

        short = xi_fn.replace('.xi', '')
        sample_dir = os.path.join(OUT_DIR, f'{short}_s{si}')
        os.makedirs(sample_dir, exist_ok=True)

        pcm16 = s['pcm']
        center_rate = s['center_rate']
        n_orig = s['n_samples']
        orig_loop_s = s['loop_start']
        orig_loop_e = s['loop_end']
        native_midi = 24 + s['relnote'] + s['fine'] / 128.0
        vol = s['volume'] / 64.0

        pcm17640 = resample(pcm16, center_rate, TARGET_RATE)
        n17640 = len(pcm17640)

        print(f'\n=== {short} s{si} ===')
        print(f'  center={center_rate:.0f}Hz native_midi={native_midi:.1f} '
              f'n17640={n17640} ({n17640/TARGET_RATE*1000:.0f}ms)')

        # A. XI 原始 loop (center_rate 播放)
        ratio = n17640 / n_orig
        xi_loop_s = int(orig_loop_s * ratio)
        xi_loop_e = int(orig_loop_e * ratio)
        b, nb, lb = encode_brr(pcm17640, xi_loop_s, xi_loop_e, 'A_xi_orig')
        render_brr(b, nb, lb, native_midi, vol, 'A_xi_orig', sample_dir)

        # B/C/D. 取末尾 N ms (无修改)
        for tail_ms, lbl in [(100, 'B_tail_100ms'),
                              (300, 'C_tail_300ms'),
                              (500, 'D_tail_500ms')]:
            tail_n = (int(tail_ms * TARGET_RATE / 1000) // 16) * 16
            if tail_n > n17640 - 100:
                tail_n = (n17640 - 100) // 16 * 16
            loop_s = n17640 - tail_n
            b, nb, lb = encode_brr(pcm17640, loop_s, n17640, lbl)
            render_brr(b, nb, lb, native_midi, vol, lbl, sample_dir)

        # E. 取末尾 500ms + crossfade
        tail_n = (int(0.5 * TARGET_RATE) // 16) * 16
        if tail_n > n17640 - 100:
            tail_n = (n17640 - 100) // 16 * 16
        loop_s = n17640 - tail_n
        fade = min(int(0.05 * TARGET_RATE), tail_n // 4)
        pcm_xfade = crossfade_tail(pcm17640, loop_s, n17640, fade)
        b, nb, lb = encode_brr(pcm_xfade, loop_s, n17640, 'E_tail_500_xfade')
        render_brr(b, nb, lb, native_midi, vol, 'E_tail_500_xfade', sample_dir)

        # F. AutoLoop (尾 50%)
        loops = find_best_loops(pcm17640, TARGET_RATE,
                                threshold_ratio=0.08,
                                min_loop_sec=0.05,
                                distance_sec=0.05,
                                quality_factor=2000.0,
                                max_candidates=2000,
                                loops_to_return=5,
                                search_start_ratio=0.5,
                                search_end_ratio=1.0)
        if loops:
            best = loops[0]
            b, nb, lb = encode_brr(pcm17640, best[0], best[1],
                                   f'F_autoloop')
            render_brr(b, nb, lb, native_midi, vol, 'F_autoloop', sample_dir)

        # G. 取末尾 500ms + RMS 归一化
        tail_n = (int(0.5 * TARGET_RATE) // 16) * 16
        if tail_n > n17640 - 100:
            tail_n = (n17640 - 100) // 16 * 16
        loop_s = n17640 - tail_n
        pcm_norm = normalize_loop_volume(pcm17640, loop_s, n17640)
        b, nb, lb = encode_brr(pcm_norm, loop_s, n17640, 'G_tail_500_norm')
        render_brr(b, nb, lb, native_midi, vol, 'G_tail_500_norm', sample_dir)

    print(f'\nFiles in {OUT_DIR}/<short>_s<idx>/')


if __name__ == '__main__':
    main()
