#!/usr/bin/env python3
"""AutoLoop + BRR 测试: 01_Bright_Acoustic_Piano s0/s2

每个 sample 生成 4 个 WAV:
  1_xi_orig_loop.wav     — XI 原始 loop 点 (基线)
  2_autoloop_pcm.wav     — AutoLoop 找的 loop (无 crossfade, 直接用)
  3_autoloop_xfade.wav   — AutoLoop + crossfade 修
  4_autoloop_brr.wav     — AutoLoop + BRR encode/decode
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
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'xi_out', 'piano_autoloop')
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


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    for xi_fn, si in TEST:
        fp = os.path.join(XI_DIR, xi_fn)
        name, samples = parse_xi_pcm(fp)
        s = samples[si]
        if not s['has_loop'] or s['n_samples'] < 50:
            print(f'  SKIP {xi_fn} s{si}'); continue

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

        print(f'\n=== {short} s{si} ===')
        print(f'  center={center_rate:.0f}Hz native_midi={native_midi:.1f} n_orig={n_orig}')
        print(f'  XI orig loop=[{orig_loop_s}-{orig_loop_e}] len={orig_loop_e-orig_loop_s} '
              f'({(orig_loop_e-orig_loop_s)/center_rate*1000:.1f}ms)')

        # 1. XI 原始 loop (center_rate, native_midi)
        out1 = render_loop(pcm16, orig_loop_s, orig_loop_e, 5.0, center_rate,
                           native_midi, native_midi, vol)
        write_wav(os.path.join(sample_dir, '1_xi_orig_loop.wav'), out1, center_rate)

        # 重采样到 17640
        pcm17640 = resample(pcm16, center_rate, TARGET_RATE)
        n17640 = len(pcm17640)
        ratio = n17640 / n_orig

        # 2. AutoLoop 找 loop (只搜最后 1/4, 避开 attack + 早期 decay)
        loops = find_best_loops(pcm17640, TARGET_RATE,
                                threshold_ratio=0.08,
                                min_loop_sec=0.05,
                                distance_sec=0.05,
                                quality_factor=2000.0,
                                max_candidates=2000,
                                loops_to_return=5,
                                search_start_ratio=0.5,
                                search_end_ratio=1.0)
        if not loops:
            print('  AutoLoop 未找到候选, 跳过')
            continue

        print(f'  AutoLoop 找到 {len(loops)} 个候选:')
        for k, (st, ed, q) in enumerate(loops):
            ll = ed - st
            print(f'    [{k}] start={st} end={ed} len={ll} '
                  f'({ll/TARGET_RATE*1000:.1f}ms) quality={q:.1f}')

        # 选最佳 loop
        best = loops[0]
        loop_s = best[0]
        loop_e = best[1]
        loop_len = loop_e - loop_s
        print(f'  选用最佳: start={loop_s} end={loop_e} '
              f'len={loop_len} ({loop_len/TARGET_RATE*1000:.1f}ms) q={best[2]:.1f}')

        # 2. AutoLoop 直接 render (无 crossfade)
        out2 = render_loop(pcm17640, loop_s, loop_e, 5.0, TARGET_RATE,
                           native_midi, native_midi, vol)
        write_wav(os.path.join(sample_dir, '2_autoloop_pcm.wav'), out2, TARGET_RATE)

        # 3. AutoLoop + crossfade
        fade_len = min(int(0.02 * TARGET_RATE), loop_len // 4)  # 20ms 或 loop 1/4
        pcm_fixed = crossfade_tail(pcm17640, loop_s, loop_e, fade_len)
        out3 = render_loop(pcm_fixed, loop_s, loop_e, 5.0, TARGET_RATE,
                           native_midi, native_midi, vol)
        write_wav(os.path.join(sample_dir, '3_autoloop_xfade.wav'), out3, TARGET_RATE)
        print(f'  PCM crossfade fade_len={fade_len} ({fade_len/TARGET_RATE*1000:.1f}ms)')

        # 4. AutoLoop + BRR encode + fix seam
        loop_s_aligned = (loop_s + 15) // 16 * 16
        if loop_s_aligned >= n17640: loop_s_aligned = 0
        blocks, n_blocks = brr_encode(pcm_fixed, loop_s_aligned)
        loop_block = loop_s_aligned // 16
        blocks_fixed = brr_fix_seam(blocks, n_blocks, loop_block, 16)
        max_seam, _ = verify_seam(blocks_fixed, n_blocks, loop_block)

        decoded = brr_decode_all_samples(blocks_fixed, n_blocks)
        brr_ls = loop_block * 16
        brr_le = n_blocks * 16
        out4 = render_loop(decoded, brr_ls, brr_le, 5.0, TARGET_RATE,
                           native_midi, native_midi, vol)
        write_wav(os.path.join(sample_dir, '4_autoloop_brr.wav'), out4, TARGET_RATE)
        print(f'  BRR: n_blocks={n_blocks} seam={max_seam} bytes={len(blocks_fixed)}')

    print(f'\nFiles in {OUT_DIR}/')


if __name__ == '__main__':
    main()
