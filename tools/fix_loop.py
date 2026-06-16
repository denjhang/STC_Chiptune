#!/usr/bin/env python3
"""搜索更好的 loop_end 点 (匹配幅度+斜率) 并生成测试 WAV"""

import wave, struct, os, json

WAV_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'adpcm_wav')

PROBLEM_LIST = [
    ('04_oboe.wav',       'snes_unofficial', 102, 3533, 3959, 'Oboe'),
    ('06_blow.wav',       'microgm',         207, 1171, 5149, 'Blow'),
    ('09_harp.wav',       'snes_unofficial', 90, 1762, 6550, 'Harp'),
    ('03_shakuhachi.wav', 'microgm',         211, 2155, 3900, 'Shakuhachi'),
]


def find_loop_seam(pcm, orig_ls, orig_le, search_range=500):
    n = len(pcm)
    best_le = orig_le
    best_cost = 999999999

    slope_ls = pcm[orig_ls] - pcm[orig_ls - 1] if orig_ls > 0 else 0
    slope2_ls = (pcm[orig_ls + 1] - pcm[orig_ls - 1]
                 if orig_ls + 1 < n and orig_ls > 0 else 0)

    lo = max(1, orig_le - search_range)
    hi = min(n - 2, orig_le + search_range)

    for j in range(lo, hi):
        cost = 0
        val_j = pcm[j]
        cost += abs(val_j - pcm[orig_ls]) * 5
        slope_j = val_j - pcm[j - 1]
        cost += abs(slope_j - slope_ls) * 3
        slope2_j = pcm[j + 1] - pcm[j - 1] if j + 1 < n else slope_j
        cost += abs(slope2_j - slope2_ls) * 2
        if cost < best_cost:
            best_cost = cost
            best_le = j

    return best_le, best_cost


def main():
    for wav_name, src, sid, orig_ls, orig_le, display in PROBLEM_LIST:
        with wave.open(os.path.join(WAV_DIR, wav_name), 'r') as w:
            raw = w.readframes(w.getnframes())
        pcm = list(struct.unpack('<%dh' % (len(raw) // 2), raw))

        new_le, cost = find_loop_seam(pcm, orig_ls, orig_le)

        slope_ls = pcm[orig_ls] - pcm[orig_ls - 1] if orig_ls > 0 else 0
        slope_le_old = pcm[orig_le] - pcm[orig_le - 1]
        slope_le_new = pcm[new_le] - pcm[new_le - 1]

        print(f'{display:12s} orig_le={orig_le} -> new_le={new_le} (shift={new_le - orig_le:+d})')
        print(f'  val_diff: old={abs(pcm[orig_le] - pcm[orig_ls]):5d} new={abs(pcm[new_le] - pcm[orig_ls]):5d}')
        print(f'  slope diff: old={abs(slope_le_old - slope_ls):4d} new={abs(slope_le_new - slope_ls):4d}')

        synth = list(pcm[:orig_ls])
        for _ in range(150):
            synth.extend(pcm[orig_ls:new_le + 1])

        out_path = os.path.join(WAV_DIR, f'_fixed_{wav_name}')
        with wave.open(out_path, 'w') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(17640)
            wf.writeframes(struct.pack('<%dh' % len(synth), *synth))

        print(f'  -> _fixed_{wav_name} ({len(synth)} samples)')
        print()

    print('Done.')


if __name__ == '__main__':
    main()
