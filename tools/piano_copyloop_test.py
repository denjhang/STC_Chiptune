#!/usr/bin/env python3
"""末尾复制 loop 方案测试: 01_Bright_Acoustic_Piano s0/s2

策略:
1. 取末尾 N ms 作为 loop 段
2. (可选) 在 loop 段首尾做 crossfade 修接缝
3. BRR encode + decode

测试 N = 50 / 100 / 150 / 200 ms 共 4 种长度
每种长度生成 1 个 BRR 试听 WAV
"""

import struct, os, wave, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from xi_brr_crossfade_test import (
    parse_xi_pcm, resample, crossfade_tail,
    brr_encode, brr_fix_seam, brr_decode_all_samples,
    verify_seam, render_loop,
)

XI_DIR = 'D:/working/vscode-projects/Reference_Project/STC-MCU/sootsound/0000_all_instruments/'
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'xi_out', 'piano_copyloop')
TARGET_RATE = 17640

TEST = [
    ('01_Bright_Acoustic_Piano.xi', 0),
    ('01_Bright_Acoustic_Piano.xi', 2),
]

# 末尾 loop 长度候选 (ms) — 越长越自然
TAIL_LENS_MS = [100, 200, 300, 500]


def write_wav(path, samples, rate):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, 'w') as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(rate)
        wf.writeframes(struct.pack('<%dh' % len(samples), *samples))


def make_copyloop(pcm, tail_ms, rate, do_crossfade=True):
    """取末尾 tail_ms 毫秒作为 loop, 可选 crossfade 修接缝

    音量突变保护:
    - 检查 loop 段起始 RMS 与 attack 末尾 RMS 的比值
    - 如果 loop 段开始音量明显小于 attack (突变), 在 loop_s 处加 fade-in
    """
    n = len(pcm)
    tail_n = int(tail_ms * rate / 1000)
    if tail_n > n - 100:
        tail_n = n - 100
    tail_n = (tail_n // 16) * 16
    loop_s = n - tail_n
    loop_e = n

    pcm_work = pcm[:]

    if do_crossfade:
        # 1. crossfade tail 末端到 loop_s 的值, 修接缝 (避免 loop 回绕咔哒)
        fade = min(int(0.02 * rate), tail_n // 4)
        pcm_work = crossfade_tail(pcm_work, loop_s, loop_e, fade)

        # 2. 音量突变保护: 在 loop_s 前后做 fade-in 过渡
        #    防止从 attack 段高电平突跳到 loop 段低电平
        attack_end = loop_s
        if attack_end > 0:
            rms_attack = (sum(x*x for x in pcm_work[max(0, attack_end-200):attack_end]) / 200) ** 0.5
            rms_loop_start = (sum(x*x for x in pcm_work[loop_s:loop_s+200]) / 200) ** 0.5
            if rms_attack > rms_loop_start * 1.5 and rms_loop_start > 0:
                # 突变: 在 loop_s 前 30ms 做衰减 fade-out 到 loop 段电平
                fade_protect = min(int(0.03 * rate), loop_s)
                ratio = rms_loop_start / rms_attack
                for i in range(fade_protect):
                    t = i / fade_protect
                    idx = loop_s - fade_protect + i
                    # 从 1.0 线性过渡到 ratio
                    scale = 1.0 * (1 - t) + ratio * t
                    pcm_work[idx] = int(pcm_work[idx] * scale)

    # BRR encode
    loop_s_aligned = (loop_s + 15) // 16 * 16
    if loop_s_aligned >= n: loop_s_aligned = 0
    blocks, n_blocks = brr_encode(pcm_work, loop_s_aligned)
    loop_block = loop_s_aligned // 16

    # BRR seam fix
    blocks_fixed = brr_fix_seam(blocks, n_blocks, loop_block, 16)
    max_seam, _ = verify_seam(blocks_fixed, n_blocks, loop_block)

    # RMS ratio (平稳度)
    tail = pcm_work[loop_s:loop_e]
    win = max(50, len(tail) // 10)
    rms_vals = []
    for i in range(0, len(tail) - win, win):
        chunk = tail[i:i+win]
        rms = (sum(x*x for x in chunk) / len(chunk)) ** 0.5
        rms_vals.append(rms)
    if rms_vals:
        rms_ratio = max(rms_vals) / max(1, min(rms_vals))
    else:
        rms_ratio = 0

    return {
        'pcm': pcm_work,
        'blocks': blocks_fixed,
        'n_blocks': n_blocks,
        'loop_s': loop_s, 'loop_e': loop_e,
        'loop_block': loop_block,
        'seam': max_seam,
        'rms_ratio': rms_ratio,
    }


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
        native_midi = 24 + s['relnote'] + s['fine'] / 128.0
        vol = s['volume'] / 64.0

        pcm17640 = resample(pcm16, center_rate, TARGET_RATE)
        n17640 = len(pcm17640)
        print(f'\n=== {short} s{si} ===')
        print(f'  center={center_rate:.0f}Hz native_midi={native_midi:.1f} '
              f'n17640={n17640} ({n17640/TARGET_RATE*1000:.0f}ms)')

        for tail_ms in TAIL_LENS_MS:
            r = make_copyloop(pcm17640, tail_ms, TARGET_RATE,
                              do_crossfade=True)

            decoded = brr_decode_all_samples(r['blocks'], r['n_blocks'])
            brr_ls = r['loop_block'] * 16
            brr_le = r['n_blocks'] * 16
            out = render_loop(decoded, brr_ls, brr_le, 5.0, TARGET_RATE,
                              native_midi, native_midi, vol)
            wav_path = os.path.join(sample_dir,
                                    f'copyloop_{tail_ms}ms.wav')
            write_wav(wav_path, out, TARGET_RATE)

            tail_n = r['loop_e'] - r['loop_s']
            print(f'  tail={tail_ms:>3d}ms (={tail_n} samples) '
                  f'seam={r["seam"]:>4d} rms_ratio={r["rms_ratio"]:.2f} '
                  f'brr_bytes={len(r["blocks"])}')


if __name__ == '__main__':
    main()
