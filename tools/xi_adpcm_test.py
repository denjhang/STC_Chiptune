#!/usr/bin/env python3
"""XI 乐器 -> 17640Hz ADPCM 循环测试 (naive vs state-reset)

两种循环方式各输出一个文件夹:
  - naive/: 不重置状态, ADPCM 状态连续流过循环边界
  - reset/: 循环边界强制重置 acc=0, step=0
每个 WAV 5 秒.
"""

import struct, os, wave

XI_DIR = 'D:/working/vscode-projects/Reference_Project/STC-MCU/sootsound/0000_all_instruments/'
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'xi_out', 'adpcm_test')
TARGET_RATE = 17640

STEPS = [
    16,17,19,21,23,25,28,31,34,37,41,45,50,55,60,66,
    73,80,88,97,107,118,130,143,157,173,190,209,230,253,
    279,307,337,371,408,449,494,544,598,658,724,796,876,
    963,1060,1166,1282,1411,1552
]

def build_jedi():
    t = []
    for step in STEPS:
        row = [(2 * (n & 7) + 1) * step // 8 for n in range(16)]
        for i in range(16):
            if row[i] & 8: row[i] = -row[i]
        t.append(row)
    return t

JEDI = build_jedi()
JEDI_FLAT = [v for row in JEDI for v in row]
STEP_INC = [-16,-16,-16,-16,32,80,112,144]

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
    '09_Music_Box.xi',
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
    sh_off = 298
    pcm_off = sh_off + num_samples * 40
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


def adpcm_encode(pcm_samples, init_acc=0, init_step=0):
    nibbles = []; acc = init_acc; step_idx = init_step
    for s in pcm_samples:
        if s > 2047: s = 2047
        if s < -2048: s = -2048
        best_nib = 0; best_diff = abs(s - acc)
        row_idx = step_idx // 16
        for nib in range(16):
            delta = JEDI[row_idx][nib]; trial = (acc + delta) & 0xFFF
            if trial & 0x800: trial |= ~0xFFF
            diff = abs(s - trial)
            if diff < best_diff: best_diff = diff; best_nib = nib
        delta = JEDI[row_idx][best_nib]; acc = (acc + delta) & 0xFFF
        if acc & 0x800: acc |= ~0xFFF
        step_idx += STEP_INC[best_nib & 7]
        if step_idx < 0: step_idx = 0
        if step_idx > 48*16: step_idx = 48*16
        nibbles.append(best_nib)
    result = bytearray()
    for i in range(0, len(nibbles), 2):
        result.append((nibbles[i] << 4) | (nibbles[i+1] if i+1 < len(nibbles) else 0))
    return bytes(result), nibbles, acc, step_idx


def adpcm_decode_stream(rom, start_byte, end_byte, init_acc=0, init_step=0):
    """Yield decoded samples one at a time, with loop at end_byte"""
    acc = init_acc; step_idx = init_step
    pos = start_byte * 2  # nibble position
    end = end_byte * 2
    while True:
        if pos >= end:
            return  # signal loop reset point
        addr = pos >> 1
        if pos & 1:
            nib = rom[addr] & 0x0F
        else:
            nib = (rom[addr] >> 4) & 0x0F
        delta = JEDI_FLAT[step_idx + nib]
        acc = (acc + delta) & 0xFFF
        if acc & 0x800: acc |= ~0xFFF
        step_idx += STEP_INC[nib & 7]
        if step_idx < 0: step_idx = 0
        if step_idx > 48*16: step_idx = 48*16
        yield acc
        pos += 1


def render_loop(naive_mode, rom, attack_end, loop_start_nib, loop_end_nib, dur, rate, pitch_step, vol):
    """Render ADPCM loop playback. naive_mode=True: no state reset; False: reset at loop boundary"""
    n_frames = int(dur * rate)
    out = []
    note_off = int(dur * 0.8 * rate)

    for i in range(n_frames):
        ipos = int(i * pitch_step)
        frac = (i * pitch_step) - ipos
        total_attack_nibs = attack_end * 2
        total_loop_nibs = (loop_end_nib - loop_start_nib) * 2

        if ipos < total_attack_nibs:
            # In attack - decode from (0,0)
            pass
        else:
            # In loop
            loop_pos = ipos - total_attack_nibs
            loop_pos = loop_pos % total_loop_nibs
            ipos = total_attack_nibs + loop_pos

        # Decode sample at ipos (approximate - full state tracking too slow for render)
        # For accurate output, pre-decode and index
        yield  # placeholder

    # Actually let's pre-decode everything and index
    # Decode attack once
    decoded_attack = []
    acc, step_idx = 0, 0
    for nib_i in range(attack_end * 2):
        addr = nib_i >> 1
        nib = rom[addr] >> 4 if not (nib_i & 1) else rom[addr] & 0x0F
        delta = JEDI_FLAT[step_idx + nib]
        acc = (acc + delta) & 0xFFF
        if acc & 0x800: acc |= ~0xFFF
        step_idx += STEP_INC[nib & 7]
        if step_idx < 0: step_idx = 0
        if step_idx > 48*16: step_idx = 48*16
        decoded_attack.append(acc)

    # Decode loop once
    decoded_loop, loop_end_acc, loop_end_step = [], 0, 0
    acc, step_idx = 0, 0
    for nib_i in range((loop_end_nib - loop_start_nib) * 2):
        addr = (loop_start_nib * 2 + nib_i) >> 1
        nib = rom[addr] >> 4 if not ((loop_start_nib * 2 + nib_i) & 1) else rom[addr] & 0x0F
        delta = JEDI_FLAT[step_idx + nib]
        acc = (acc + delta) & 0xFFF
        if acc & 0x800: acc |= ~0xFFF
        step_idx += STEP_INC[nib & 7]
        if step_idx < 0: step_idx = 0
        if step_idx > 48*16: step_idx = 48*16
        decoded_loop.append(acc)

    all_decoded = decoded_attack + decoded_loop
    n_attack = len(decoded_attack)
    n_loop = len(decoded_loop)

    for i in range(n_frames):
        ipos = int(i * pitch_step)
        frac = (i * pitch_step) - ipos

        if ipos < len(all_decoded):
            pass
        elif n_loop > 0:
            loop_pos = ipos - n_attack
            ipos = n_attack + (loop_pos % n_loop)
        else:
            continue

        p0 = ipos
        p1 = ipos + 1
        if p1 >= len(all_decoded):
            if n_loop > 0:
                p1 = n_attack  # wrap
            else:
                p1 = p0

        sample = all_decoded[p0] * (1 - frac) + all_decoded[p1] * frac
        sample *= 16  # 12-bit -> 16-bit

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


def render_seam_reset(rom, loop_start_byte, loop_end_byte, dur, rate):
    """Render loop segment with state reset at each boundary, 5s"""
    decoded_loop = []
    acc, step_idx = 0, 0
    for nib_i in range((loop_end_byte - loop_start_byte) * 2):
        addr = (loop_start_byte * 2 + nib_i) >> 1
        nib = rom[addr] >> 4 if not ((loop_start_byte * 2 + nib_i) & 1) else rom[addr] & 0x0F
        delta = JEDI_FLAT[step_idx + nib]
        acc = (acc + delta) & 0xFFF
        if acc & 0x800: acc |= ~0xFFF
        step_idx += STEP_INC[nib & 7]
        if step_idx < 0: step_idx = 0
        if step_idx > 48*16: step_idx = 48*16
        decoded_loop.append(acc)

    n_fill = int(dur * rate)
    out = []
    n_loop = len(decoded_loop)
    pos = 0
    while len(out) < n_fill:
        out.append(decoded_loop[pos % n_loop] * 16)
        pos += 1
    return out


def render_seam_naive(rom, attack_end_byte, loop_start_byte, loop_end_byte, dur, rate):
    """Render loop segment with continuous state (naive), 5s"""
    decoded_all = []
    acc, step_idx = 0, 0
    total_nibs = loop_end_byte * 2

    # Decode attack + one loop cycle to get state
    for nib_i in range(total_nibs):
        addr = nib_i >> 1
        nib = rom[addr] >> 4 if not (nib_i & 1) else rom[addr] & 0x0F
        delta = JEDI_FLAT[step_idx + nib]
        acc = (acc + delta) & 0xFFF
        if acc & 0x800: acc |= ~0xFFF
        step_idx += STEP_INC[nib & 7]
        if step_idx < 0: step_idx = 0
        if step_idx > 48*16: step_idx = 48*16
        decoded_all.append(acc)

    attack_n = attack_end_byte * 2
    loop_n = (loop_end_byte - loop_start_byte) * 2

    # Continue decoding in loop mode (state continues)
    n_fill = int(dur * rate)
    out = []
    pos = 0
    while len(out) < n_fill:
        if pos >= len(decoded_all):
            # In loop: keep decoding with continued state
            if (pos - len(decoded_all)) % loop_n == 0:
                # At loop start, state continues from end of last loop
                pass
            # Decode next sample from loop region
            loop_pos = (pos - attack_n) % loop_n
            nib_i = loop_start_byte * 2 + loop_pos
            addr = nib_i >> 1
            nib = rom[addr] >> 4 if not (nib_i & 1) else rom[addr] & 0x0F
            delta = JEDI_FLAT[step_idx + nib]
            acc = (acc + delta) & 0xFFF
            if acc & 0x800: acc |= ~0xFFF
            step_idx += STEP_INC[nib & 7]
            if step_idx < 0: step_idx = 0
            if step_idx > 48*16: step_idx = 48*16
            out.append(acc * 16)
        else:
            out.append(decoded_all[pos] * 16)
        pos += 1
    return out


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(os.path.join(OUT_DIR, 'naive'), exist_ok=True)
    os.makedirs(os.path.join(OUT_DIR, 'reset'), exist_ok=True)

    for pick in PICKS:
        filepath = os.path.join(XI_DIR, pick)
        if not os.path.exists(filepath):
            print(f'  SKIP {pick}')
            continue

        name, samples = parse_xi_pcm(filepath)
        if not name or not samples:
            continue

        s = samples[0]
        if not s['has_loop'] or s['n_samples'] < 50:
            print(f'  SKIP {pick} (no loop)')
            continue

        pcm16 = s['pcm']
        center_rate = s['center_rate']
        pcm16_17640 = resample(pcm16, center_rate, TARGET_RATE)
        n_17640 = len(pcm16_17640)
        ratio = n_17640 / len(pcm16)
        loop_s = max(0, int(s['loop_start'] * ratio))
        loop_e = min(n_17640, int(s['loop_end'] * ratio))
        pcm12 = [max(-2048, min(2047, v >> 4)) for v in pcm16_17640]
        native_midi = 24 + s['relnote'] + s['fine'] / 128.0
        vol = s['volume'] / 64.0
        pitch_step = 2.0 ** ((60 - native_midi) / 12.0)

        # Encode full PCM: attack[0..loop_s) + loop[loop_s..loop_e)
        # Byte-level: nib_pos -> byte = nib_pos // 2
        attack_nibs = loop_s
        loop_nibs = loop_e - loop_s
        rom, _, _, _ = adpcm_encode(pcm12)
        attack_end_byte = (loop_s + 1) // 2  # byte boundary after attack nibbles
        loop_start_byte = loop_s // 2
        loop_end_byte = (loop_e + 1) // 2

        cn = pick.replace('.xi', '')
        loop_segs = loop_e - loop_s
        adpcm_kb = len(rom) / 1024

        print(f'{cn:40s} {n_17640:5d}smp {adpcm_kb:5.1f}KB loop={loop_segs}smp')

        # Naive WAV
        out_naive = render_seam_naive(rom, attack_end_byte, loop_start_byte, loop_end_byte, 5.0, TARGET_RATE)
        wav = os.path.join(OUT_DIR, 'naive', f'{cn}.wav')
        with wave.open(wav, 'w') as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(TARGET_RATE)
            wf.writeframes(struct.pack('<%dh' % len(out_naive), *out_naive))

        # Reset WAV
        out_reset = render_seam_reset(rom, loop_start_byte, loop_end_byte, 5.0, TARGET_RATE)
        wav = os.path.join(OUT_DIR, 'reset', f'{cn}.wav')
        with wave.open(wav, 'w') as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(TARGET_RATE)
            wf.writeframes(struct.pack('<%dh' % len(out_reset), *out_reset))

    print(f'\nDone! naive/ and reset/ in {OUT_DIR}')


if __name__ == '__main__':
    main()
