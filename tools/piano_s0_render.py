#!/usr/bin/env python3
"""Acoustic Grand Piano sample 0 (最高音) -> 17640Hz BRR 上位机试听

生成 4 个 WAV:
  1. xi_raw_44100.wav         — XI 原始 PCM (44100, 无重采样)
  2. pcm_resample_17640.wav   — 重采样到 17640Hz (无 crossfade)
  3. pcm_crossfade_17640.wav  — + PCM crossfade 修 loop seam
  4. brr_decode_17640.wav     — + BRR encode/decode (filter=0, SNES DSP)
"""

import struct, os, wave
from xi_brr_crossfade_test import (
    parse_xi_pcm, resample, crossfade_tail,
    auto_scale, brr_encode_block, brr_encode,
    brr_decode_block, brr_decode_all_samples,
    brr_fix_seam, verify_seam, render_loop,
)

XI_DIR = 'D:/working/vscode-projects/Reference_Project/STC-MCU/sootsound/0000_all_instruments/'
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'xi_out', 'piano_s0')
TARGET_RATE = 17640


def write_wav(path, samples, rate):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, 'w') as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(rate)
        wf.writeframes(struct.pack('<%dh' % len(samples), *samples))


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    name, samples = parse_xi_pcm(os.path.join(XI_DIR, '00_Acoustic_Grand_Piano.xi'))
    s = samples[0]

    pcm16 = s['pcm']
    center_rate = s['center_rate']
    n_orig = s['n_samples']
    loop_s_orig = s['loop_start']
    loop_e_orig = s['loop_end']
    native_midi = 24 + s['relnote'] + s['fine'] / 128.0
    vol = s['volume'] / 64.0

    print(f'Original: center={center_rate:.0f}Hz, n={n_orig}, '
          f'native_midi={native_midi:.2f}')
    print(f'  loop=[{loop_s_orig}-{loop_e_orig}], loop_len={loop_e_orig-loop_s_orig}')

    # 1. XI raw (44100 center_rate, no resample) - 用原始频率渲染
    out1 = render_loop(pcm16, loop_s_orig, loop_e_orig, 5.0, center_rate, 60,
                       native_midi, vol)
    write_wav(os.path.join(OUT_DIR, '1_xi_raw.wav'), out1, center_rate)
    print(f'  [1] xi_raw: {center_rate:.0f}Hz, {len(out1)} frames')

    # 2. 重采样到 17640 (无 crossfade)
    pcm17640 = resample(pcm16, center_rate, TARGET_RATE)
    n17640 = len(pcm17640)
    ratio = n17640 / n_orig
    loop_s = max(0, int(loop_s_orig * ratio))
    loop_e = min(n17640, int(loop_e_orig * ratio))
    print(f'Resample: {n_orig}@{center_rate:.0f} -> {n17640}@{TARGET_RATE}, '
          f'loop=[{loop_s}-{loop_e}] len={loop_e-loop_s}')

    out2 = render_loop(pcm17640, loop_s, loop_e, 5.0, TARGET_RATE, 60,
                       native_midi, vol)
    write_wav(os.path.join(OUT_DIR, '2_pcm_resample.wav'), out2, TARGET_RATE)
    print(f'  [2] pcm_resample_17640: {len(out2)} frames')

    # 3. PCM crossfade 修 seam
    new_loop_len = loop_e - loop_s
    pcm_fade = max(8, min(64, new_loop_len // 10))
    pcm_fixed = crossfade_tail(pcm17640, loop_s, loop_e, pcm_fade)

    out3 = render_loop(pcm_fixed, loop_s, loop_e, 5.0, TARGET_RATE, 60,
                       native_midi, vol)
    write_wav(os.path.join(OUT_DIR, '3_pcm_crossfade.wav'), out3, TARGET_RATE)
    print(f'  [3] pcm_crossfade_17640: pcm_fade={pcm_fade}, {len(out3)} frames')

    # 4. BRR encode + decode + crossfade 修 BRR seam
    loop_s_aligned = (loop_s + 15) // 16 * 16
    if loop_s_aligned >= n17640: loop_s_aligned = 0
    blocks, n_blocks = brr_encode(pcm_fixed, loop_s_aligned)
    loop_block = loop_s_aligned // 16

    brr_fade = 16
    blocks_fixed = brr_fix_seam(blocks, n_blocks, loop_block, brr_fade)
    max_seam, avg_seam = verify_seam(blocks_fixed, n_blocks, loop_block)

    decoded = brr_decode_all_samples(blocks_fixed, n_blocks)
    brr_loop_s = loop_block * 16
    brr_loop_e = n_blocks * 16

    out4 = render_loop(decoded, brr_loop_s, brr_loop_e, 5.0, TARGET_RATE, 60,
                       native_midi, vol)
    write_wav(os.path.join(OUT_DIR, '4_brr_decode.wav'), out4, TARGET_RATE)
    print(f'  [4] brr_decode_17640: n_blocks={n_blocks}, '
          f'seam_max={max_seam} avg={avg_seam:.1f}, {len(out4)} frames')

    print(f'\nBRR size: {len(blocks_fixed)} bytes = {len(blocks_fixed)/1024:.2f}KB')
    print(f'\nFiles in {OUT_DIR}:')
    for f in sorted(os.listdir(OUT_DIR)):
        print(f'  {f}')


if __name__ == '__main__':
    main()
