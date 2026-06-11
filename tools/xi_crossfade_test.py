#!/usr/bin/env python3
"""XI 乐器 -> 17640Hz 重采样 + loop 点 crossfade 修复 -> PCM 循环测试

流程:
1. 解析 XI 原始 PCM
2. 线性插值重采样到 17640Hz
3. 按比例换算 loop_start / loop_end
4. 在 loop 边界做 crossfade (尾→头重叠混合)
5. 输出 WAV: 原始 PCM (无crossfade) vs crossfade 修复后
"""

import struct, os, wave

XI_DIR = 'D:/working/vscode-projects/Reference_Project/STC-MCU/sootsound/0000_all_instruments/'
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'xi_out', 'crossfade_test')
TARGET_RATE = 17640

PICKS = [
    '00_Acoustic_Grand_Piano.xi',
    '04_Electric_Piano_1_L0.xi',
    '28_Violin.xi',
    '30_Strings.xi',
    '2E_Harp.xi',
    '15_Accordion_L0.xi',
    '13_Church_Organ.xi',
    '23_Fretless_Bass.xi',
    '1A_Jazz_Guitar.xi',
    '1E_Distortion_Guitar.xi',
    '08_Celesta.xi',
    '49_Flute.xi',
    '4A_Recorder.xi',
    '44_Oboe.xi',
    '47_Clarinet.xi',
]


def parse_xi_pcm(filepath):
    with open(filepath, 'rb') as f:
        data = f.read()
    if data[:21] != b'Extended Instrument: ':
        return None, None
    name = data[21:43].split(b'\x00')[0].decode('ascii', errors='replace')
    num_samples = struct.unpack_from('<H', data, 296)[0]
    sh_off = 298; pcm_off = sh_off + num_samples * 40
    samples = []
    for s_idx in range(num_samples):
        so = sh_off + s_idx * 40
        slen = struct.unpack_from('<I', data, so)[0]
        lstart = struct.unpack_from('<I', data, so+4)[0]
        llen = struct.unpack_from('<I', data, so+8)[0]
        vol = data[so+12]; fine = struct.unpack_from('b', data, so+13)[0]
        flags = data[so+14]; relnote = struct.unpack_from('b', data, so+16)[0]
        is_16 = bool(flags & 0x10); loop_type = flags & 0x03
        n_samp = slen // 2 if is_16 else slen
        loop_s = lstart // 2 if is_16 else lstart
        loop_l = llen // 2 if is_16 else llen
        center_rate = 8363.0 * (2.0 ** ((relnote + fine / 128.0) / 12.0))
        pcm = []
        if is_16:
            acc = 0
            for i in range(n_samp):
                delta = struct.unpack_from('<h', data, pcm_off + i*2)[0]
                acc += delta
                pcm.append(max(-32768, min(32767, acc)))
        else:
            acc = 0
            for i in range(n_samp):
                delta = struct.unpack_from('b', data, pcm_off + i)[0]
                acc += delta
                pcm.append(max(-128, min(127, acc)) * 256)
        pcm_off += slen
        samples.append({'pcm': pcm, 'n_samples': n_samp, 'loop_start': loop_s,
                         'loop_end': loop_s + loop_l, 'has_loop': loop_type > 0,
                         'relnote': relnote, 'fine': fine, 'volume': vol, 'center_rate': center_rate})
    return name, samples


def resample(pcm, src_rate, dst_rate):
    src_len = len(pcm)
    if src_rate == dst_rate or src_len < 2:
        return pcm[:]
    dst_len = max(2, int(round(src_len * dst_rate / src_rate)))
    ratio = (src_len - 1) / (dst_len - 1)
    result = []
    for i in range(dst_len):
        pos = i * ratio; idx = int(pos); frac = pos - idx
        s = pcm[idx] * (1 - frac) + pcm[idx+1] * frac if idx+1 < src_len else pcm[-1]
        result.append(int(round(s)))
    return result


def crossfade_loop(pcm, loop_s, loop_e, fade_len):
    """在 loop 边界做 crossfade: 只改 tail，让 tail 末尾渐变到 loop_s 的值。
    循环时 loop_e-1 直接跳回 loop_s，两者值相等 = 无缝。
    head 不动，保持原始乐器行为。
    """
    n = len(pcm)
    loop_len = loop_e - loop_s
    if loop_len <= 0 or fade_len <= 0 or fade_len > loop_len:
        return pcm[:], 0, 0

    fade_len = min(fade_len, loop_len // 2)
    result = pcm[:]

    seam_before = abs(result[loop_e - 1] - result[loop_s])
    target = result[loop_s]  # tail 末尾目标是 loop_s 的值

    for i in range(fade_len):
        t = (i + 1) / fade_len  # 渐变: 0->1
        tail_idx = loop_e - fade_len + i
        result[tail_idx] = int(result[tail_idx] * (1 - t) + target * t)

    seam_after = abs(result[loop_e - 1] - result[loop_s])
    return result, seam_before, seam_after


def render_loop(pcm, loop_s, loop_e, dur, rate, midi_note, relnote, fine, vol):
    """Render 5s loop playback at given pitch"""
    native_midi = 24 + relnote + fine / 128.0
    pitch_step = 2.0 ** ((midi_note - native_midi) / 12.0)
    n_frames = int(dur * rate)
    n_pcm = len(pcm)
    loop_len = loop_e - loop_s
    note_off = int(dur * 0.8 * rate)
    out = []
    for i in range(n_frames):
        ipos = int(i * pitch_step)
        frac = (i * pitch_step) - ipos
        if loop_len > 0 and ipos >= loop_e:
            ipos = loop_s + (ipos - loop_s) % loop_len
        if ipos >= n_pcm:
            ipos = n_pcm - 1
        p1 = ipos + 1
        if loop_len > 0 and p1 >= loop_e:
            p1 = loop_s + (p1 - loop_s) % loop_len
        if p1 >= n_pcm:
            p1 = n_pcm - 1
        sample = pcm[ipos] + (pcm[p1] - pcm[ipos]) * frac
        t_sec = i / rate
        if t_sec < 0.005:
            e = t_sec / 0.005
        elif i < note_off:
            e = 1.0
        else:
            rel = (i - note_off) / max(1, n_frames - note_off)
            e = max(0, 1.0 - rel * rel)
        out.append(max(-32768, min(32767, int(sample * e * vol))))
    return out


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(os.path.join(OUT_DIR, 'raw'), exist_ok=True)
    os.makedirs(os.path.join(OUT_DIR, 'fixed'), exist_ok=True)

    print(f"{'Instrument':<35s} {'loop_s':>6s} {'loop_e':>6s} {'fade':>4s} {'seam_raw':>9s} {'seam_fix':>9s}")
    print('-' * 75)

    for pick in PICKS:
        filepath = os.path.join(XI_DIR, pick)
        if not os.path.exists(filepath):
            print(f'  SKIP {pick}'); continue

        name, samples = parse_xi_pcm(filepath)
        if not name or not samples: continue

        s = samples[0]
        if not s['has_loop'] or s['n_samples'] < 50:
            print(f'  SKIP {pick} (no loop)'); continue

        pcm16 = s['pcm']
        center_rate = s['center_rate']
        pcm16_17640 = resample(pcm16, center_rate, TARGET_RATE)
        n_17640 = len(pcm16_17640)
        ratio = n_17640 / len(pcm16)
        loop_s = max(0, int(s['loop_start'] * ratio))
        loop_e = min(n_17640, int(s['loop_end'] * ratio))
        native_midi = 24 + s['relnote'] + s['fine'] / 128.0
        vol = s['volume'] / 64.0
        cn = pick.replace('.xi', '')

        # Crossfade: fade_len 根据原始 loop 长度按比例缩放
        orig_loop_len = s['loop_end'] - s['loop_start']
        new_loop_len = loop_e - loop_s
        # crossfade = 新 loop 长度的 10%, 至少 8 采样, 至多 64
        fade_len = max(8, min(64, new_loop_len // 10))

        pcm_fixed, seam_before, seam_after = crossfade_loop(pcm16_17640, loop_s, loop_e, fade_len)

        seam_raw_str = f'{seam_before}' if seam_before > 0 else '0'
        seam_fix_str = f'{seam_after}' if seam_after > 0 else '0'
        print(f'{cn:35s} {loop_s:6d} {loop_e:6d} {fade_len:4d} {seam_raw_str:>9s} {seam_fix_str:>9s}')

        # WAV 1: raw (no crossfade)
        out_raw = render_loop(pcm16_17640, loop_s, loop_e, 5.0, TARGET_RATE, 60,
                              s['relnote'], s['fine'], vol)
        wav1 = os.path.join(OUT_DIR, 'raw', f'{cn}.wav')
        with wave.open(wav1, 'w') as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(TARGET_RATE)
            wf.writeframes(struct.pack('<%dh' % len(out_raw), *out_raw))

        # WAV 2: crossfade fixed
        out_fix = render_loop(pcm_fixed, loop_s, loop_e, 5.0, TARGET_RATE, 60,
                              s['relnote'], s['fine'], vol)
        wav2 = os.path.join(OUT_DIR, 'fixed', f'{cn}.wav')
        with wave.open(wav2, 'w') as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(TARGET_RATE)
            wf.writeframes(struct.pack('<%dh' % len(out_fix), *out_fix))

    print(f'\nDone! raw/ and fixed/ in {OUT_DIR}')


if __name__ == '__main__':
    main()
