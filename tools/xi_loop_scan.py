#!/usr/bin/env python3
"""扫描所有 XI 乐器所有 sample 的 loop 质量 (17640Hz 重采样后)

输出 CSV: filename, sample_idx, center_rate, native_midi, loop_len_17640,
         seam_max_raw, seam_max_crossfade, has_loop, n_samp_17640
"""

import os, glob
from xi_brr_crossfade_test import (
    parse_xi_pcm, resample, crossfade_tail,
    brr_encode, brr_fix_seam, verify_seam,
)

XI_DIR = 'D:/working/vscode-projects/Reference_Project/STC-MCU/sootsound/0000_all_instruments/'
TARGET_RATE = 17640


def main():
    files = sorted(glob.glob(os.path.join(XI_DIR, '*.xi')))
    print(f'{"filename":<45s} {"s#":>3s} {"center":>7s} {"MIDI":>5s} '
          f'{"loop_len":>8s} {"seam_raw":>9s} {"seam_xfade":>11s} {"bytes":>6s}')
    print('-' * 100)

    seam_zero_count = 0
    total_count = 0

    for f in files:
        name, samples = parse_xi_pcm(f)
        if not name or not samples: continue
        fn = os.path.basename(f).replace('.xi', '')

        for si, s in enumerate(samples):
            if not s['has_loop'] or s['n_samples'] < 50: continue
            pcm16 = s['pcm']
            n_orig = s['n_samples']
            center_rate = s['center_rate']
            ratio = TARGET_RATE / center_rate
            n_resamp = int(n_orig * TARGET_RATE / center_rate)
            if n_resamp < 100: continue

            pcm_r = resample(pcm16, center_rate, TARGET_RATE)
            loop_s = max(0, int(s['loop_start'] * TARGET_RATE / center_rate))
            loop_e = min(len(pcm_r), int(s['loop_end'] * TARGET_RATE / center_rate))
            loop_len = loop_e - loop_s
            if loop_len < 16: continue

            native_midi = 24 + s['relnote'] + s['fine'] / 128.0
            vol = s['volume'] / 64.0

            # PCM crossfade
            fade = max(8, min(64, loop_len // 10))
            pcm_fixed = crossfade_tail(pcm_r, loop_s, loop_e, fade)

            # BRR encode
            loop_s_a = (loop_s + 15) // 16 * 16
            if loop_s_a >= len(pcm_r): loop_s_a = 0
            blocks, n_blocks = brr_encode(pcm_fixed, loop_s_a)
            loop_block = loop_s_a // 16

            # No BRR seam fix
            raw_seam, _ = verify_seam(blocks, n_blocks, loop_block, n_cycles=20)

            # With BRR seam fix
            blocks_fixed = brr_fix_seam(blocks, n_blocks, loop_block, 16)
            fixed_seam, _ = verify_seam(blocks_fixed, n_blocks, loop_block, n_cycles=20)

            seam_zero = (fixed_seam == 0)
            if seam_zero: seam_zero_count += 1
            total_count += 1

            marker = '*' if seam_zero else ' '
            print(f'{marker}{fn[:44]:<44s} {si:>3d} {center_rate:>6.0f} '
                  f'{native_midi:>5.1f} {loop_len:>8d} {raw_seam:>9d} '
                  f'{fixed_seam:>11d} {len(blocks_fixed):>6d}')

    print(f'\n完美循环 (seam=0): {seam_zero_count}/{total_count} '
          f'({100*seam_zero_count/total_count:.1f}%)')


if __name__ == '__main__':
    main()
