#!/usr/bin/env python3
"""钢琴系 XI 所有 sample -> 4 个对比文件 (17640Hz, native_midi 播放)

每个 sample 生成 4 个 WAV (放各自子目录):
  1_xi_raw.wav         — XI 原始 PCM @ center_rate, native_midi 播放
  2_pcm_resample.wav   — 重采样到 17640Hz (无 crossfade)
  3_pcm_crossfade.wav  — + PCM crossfade 修 loop seam
  4_brr_decode.wav     — + BRR encode/decode (filter=0, SNES DSP)
"""

import struct, os, wave
from xi_brr_crossfade_test import (
    parse_xi_pcm, resample, crossfade_tail,
    brr_encode, brr_fix_seam, brr_decode_all_samples,
    verify_seam, render_loop,
)

XI_DIR = 'D:/working/vscode-projects/Reference_Project/STC-MCU/sootsound/0000_all_instruments/'
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'xi_out', 'piano_all')
TARGET_RATE = 17640

PIANO_FILES = [
    '00_Acoustic_Grand_Piano.xi',
    '01_Bright_Acoustic_Piano.xi',
    '02_Electric_Grand_Piano_L0.xi',
    '02_Electric_Grand_Piano_L1.xi',
    '03_Honky-Tonk_Piano_L0.xi',
    '03_Honky-Tonk_Piano_L1.xi',
    '04_Electric_Piano_1_L0.xi',
    '04_Electric_Piano_1_L1.xi',
    '05_Electric_Piano_2_L0.xi',
    '05_Electric_Piano_2_L1.xi',
    '06_Harpsichord.xi',
    '07_Clavinet.xi',
]


def write_wav(path, samples, rate):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, 'w') as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(rate)
        wf.writeframes(struct.pack('<%dh' % len(samples), *samples))


def process_sample(s):
    """处理单个 sample: 返回所有中间结果"""
    if not s['has_loop'] or s['n_samples'] < 50:
        return None
    pcm16 = s['pcm']
    center_rate = s['center_rate']
    n_orig = s['n_samples']
    loop_s_orig = s['loop_start']
    loop_e_orig = s['loop_end']

    # 1. XI raw (原 center_rate, 原始 loop)
    out1 = render_loop(pcm16, loop_s_orig, loop_e_orig, 5.0, center_rate,
                       24 + s['relnote'] + s['fine'] / 128.0,
                       24 + s['relnote'] + s['fine'] / 128.0,
                       s['volume'] / 64.0)

    # 2. 重采样到 17640
    pcm17640 = resample(pcm16, center_rate, TARGET_RATE)
    n17640 = len(pcm17640)
    ratio = n17640 / n_orig
    loop_s = max(0, int(loop_s_orig * ratio))
    loop_e = min(n17640, int(loop_e_orig * ratio))
    new_loop_len = loop_e - loop_s
    if new_loop_len < 16: return None

    native_midi = 24 + s['relnote'] + s['fine'] / 128.0
    vol = s['volume'] / 64.0

    out2 = render_loop(pcm17640, loop_s, loop_e, 5.0, TARGET_RATE,
                       native_midi, native_midi, vol)

    # 3. PCM crossfade
    pcm_fade = max(8, min(64, new_loop_len // 10))
    pcm_fixed = crossfade_tail(pcm17640, loop_s, loop_e, pcm_fade)

    out3 = render_loop(pcm_fixed, loop_s, loop_e, 5.0, TARGET_RATE,
                       native_midi, native_midi, vol)

    # 4. BRR encode + fix seam
    loop_s_aligned = (loop_s + 15) // 16 * 16
    if loop_s_aligned >= n17640: loop_s_aligned = 0
    blocks, n_blocks = brr_encode(pcm_fixed, loop_s_aligned)
    loop_block = loop_s_aligned // 16

    blocks_fixed = brr_fix_seam(blocks, n_blocks, loop_block, 16)
    max_seam, _ = verify_seam(blocks_fixed, n_blocks, loop_block)

    decoded = brr_decode_all_samples(blocks_fixed, n_blocks)
    brr_loop_s = loop_block * 16
    brr_loop_e = n_blocks * 16

    out4 = render_loop(decoded, brr_loop_s, brr_loop_e, 5.0, TARGET_RATE,
                       native_midi, native_midi, vol)

    return {
        'wav1': (out1, center_rate),
        'wav2': (out2, TARGET_RATE),
        'wav3': (out3, TARGET_RATE),
        'wav4': (out4, TARGET_RATE),
        'native_midi': native_midi,
        'center_rate': center_rate,
        'n_17640': n17640,
        'loop_s': loop_s, 'loop_e': loop_e,
        'seam': max_seam, 'blocks': blocks_fixed, 'n_blocks': n_blocks,
    }


def main():
    print(f'{"filename":<38s} {"s":>2s} {"center":>7s} {"MIDI":>5s} '
          f'{"n_s17640":>8s} {"loop":>6s} {"seam":>6s} {"bytes":>6s}')
    print('-' * 90)

    for xi_fn in PIANO_FILES:
        fp = os.path.join(XI_DIR, xi_fn)
        if not os.path.exists(fp):
            print(f'  SKIP (not found) {xi_fn}'); continue
        name, samples = parse_xi_pcm(fp)
        if not samples: continue
        short = xi_fn.replace('.xi', '')

        for si, s in enumerate(samples):
            r = process_sample(s)
            if r is None: continue

            sample_dir = os.path.join(OUT_DIR, f'{short}_s{si}')
            write_wav(os.path.join(sample_dir, '1_xi_raw.wav'),
                      *r['wav1'])
            write_wav(os.path.join(sample_dir, '2_pcm_resample.wav'),
                      *r['wav2'])
            write_wav(os.path.join(sample_dir, '3_pcm_crossfade.wav'),
                      *r['wav3'])
            write_wav(os.path.join(sample_dir, '4_brr_decode.wav'),
                      *r['wav4'])

            seam_str = 'OK0' if r['seam'] == 0 else f'{r["seam"]}'
            print(f'{short[:37]:<37s} {si:>2d} {r["center_rate"]:>6.0f} '
                  f'{r["native_midi"]:>5.1f} {r["n_17640"]:>8d} '
                  f'{r["loop_e"]-r["loop_s"]:>6d} {seam_str:>6s} '
                  f'{len(r["blocks"]):>6d}')

    print(f'\nFiles in {OUT_DIR}/<short>_s<idx>/')


if __name__ == '__main__':
    main()
