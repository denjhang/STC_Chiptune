#!/usr/bin/env python3
"""XI 乐器 -> BRR filter=0 循环测试

BRR block: 9 bytes = 1 header + 8 data = 16 samples (4-bit each)
filter=0: 无 IIR 滤波，纯 4-bit 量化，循环回绕无需状态 -> 天然无缝
header: [7:4]=scale, [3:2]=filter(=0), [1]=loop, [0]=end

每个乐器输出 5 秒 WAV: 原始 PCM vs BRR 解码
"""

import struct, os, wave

XI_DIR = 'D:/working/vscode-projects/Reference_Project/STC-MCU/sootsound/0000_all_instruments/'
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'xi_out', 'brr_test')
TARGET_RATE = 17640

# GME Spc_Dsp.cpp shifts table (bit-exact)
RIGHT_SHIFT = [13,12,12,12,12,12,12,12,12,12,12,12,13,16,16,16]
LEFT_SHIFT  = [ 0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9,10,11,11,11,11]

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


def auto_scale(pcm_samples):
    peak = max(abs(s) for s in pcm_samples) if pcm_samples else 1
    if peak == 0: return 0
    for sc in range(13):
        ls = LEFT_SHIFT[sc]
        if 7 * (2 << ls) >= peak:
            return sc
    return 12


def brr_encode_block(pcm_samples, scale=0, is_last=False):
    header = (scale << 4) | (0 << 2)
    if is_last: header |= 1
    result = bytearray(9)
    result[0] = header
    ls = LEFT_SHIFT[scale]
    for i in range(16):
        s = pcm_samples[i] if i < len(pcm_samples) else 0
        nib = s >> (ls + 1)
        nib = max(-8, min(7, nib))
        byte_idx = 1 + i // 2
        if i % 2 == 0:
            result[byte_idx] = (nib & 0x0F) << 4
        else:
            result[byte_idx] |= (nib & 0x0F)
    return bytes(result)


def brr_encode(pcm_samples, loop_start):
    """Encode PCM as BRR blocks with filter=0. Sets loop flag on loop_start block."""
    blocks = bytearray()
    n_blocks = (len(pcm_samples) + 15) // 16
    for b in range(n_blocks):
        start = b * 16
        end = min(start + 16, len(pcm_samples))
        block_pcm = pcm_samples[start:end]
        while len(block_pcm) < 16:
            block_pcm.append(0)
        is_last = (b == n_blocks - 1)
        is_loop_start = (b * 16 == loop_start)
        scale = auto_scale(block_pcm)
        header = (scale << 4) | (0 << 2)
        if is_loop_start: header |= 0x02  # loop flag
        if is_last: header |= 0x01      # end flag
        blk = bytearray(9)
        blk[0] = header
        ls = LEFT_SHIFT[scale]
        for i in range(16):
            s = block_pcm[i]
            nib = s >> (ls + 1)
            nib = max(-8, min(7, nib))
            byte_idx = 1 + i // 2
            if i % 2 == 0:
                blk[byte_idx] = (nib & 0x0F) << 4
            else:
                blk[byte_idx] |= (nib & 0x0F)
        blocks.extend(blk)
    return bytes(blocks), n_blocks


def brr_decode_all(blocks, n_blocks, loop_block, n_cycles=200):
    """Decode all blocks sequentially, looping from loop_block. Returns list of s16."""
    decoded = []
    for cycle in range(n_cycles):
        b_start = loop_block if cycle > 0 else 0
        for b in range(b_start, n_blocks):
            bd = blocks[b*9:(b+1)*9]
            header = bd[0]
            scale = header >> 4
            filter_mode = header & 0x0C
            rs = RIGHT_SHIFT[scale]
            ls = LEFT_SHIFT[scale]
            p1 = 0; p2_raw = 0
            for byte_pair in range(4):
                byte0 = bd[1 + byte_pair*2]
                byte1 = bd[2 + byte_pair*2]
                nybbles = (byte0 * 256 + byte1) & 0xFFFF
                for _ in range(4):
                    nybbles &= 0xFFFF
                    raw = nybbles if nybbles < 0x8000 else nybbles - 0x10000
                    s = ((raw >> rs) & 0xFFFF) << ls
                    s &= 0xFFFF
                    if s >= 0x8000: s -= 0x10000
                    # filter=0: no filter ops
                    if s > 32767: s = 32767
                    if s < -32768: s = -32768
                    s = s * 2
                    if s > 32767: s = 32767
                    if s < -32768: s = -32768
                    decoded.append(s)
                    p2_raw = p1; p1 = s
                    nybbles <<= 4
    return decoded


def brr_decode_sample(blocks, n_blocks, loop_block, ipos):
    """Decode sample at index ipos (across loop boundaries)."""
    n_per_block = 16
    total = (n_blocks - loop_block) * 16
    if total <= 0: total = n_blocks * 16
    pos = ipos
    if total > 0:
        pos = pos % total
    block_idx = loop_block + pos // n_per_block
    sample_in_block = pos % n_per_block

    bd = blocks[block_idx*9:(block_idx+1)*9]
    header = bd[0]
    scale = header >> 4
    rs = RIGHT_SHIFT[scale]
    ls = LEFT_SHIFT[scale]

    # Decode just one sample (need prev1/prev2 for filter, but filter=0 so they don't matter)
    nib_pos = sample_in_block
    byte_pair = nib_pos // 4
    nyb_in_pair = nib_pos % 4
    byte0 = bd[1 + byte_pair*2]
    byte1 = bd[2 + byte_pair*2]
    nybbles = (byte0 * 256 + byte1) & 0xFFFF
    nybbles = (nybbles << (nyb_in_pair * 4)) & 0xFFFF
    raw = nybbles if nybbles < 0x8000 else nybbles - 0x10000
    s = ((raw >> rs) & 0xFFFF) << ls
    s &= 0xFFFF
    if s >= 0x8000: s -= 0x10000
    s = s * 2
    if s > 32767: s = 32767
    if s < -32768: s = -32768
    return s


def render_brr_pcm(pcm, loop_start, dur, rate, midi_note, native_midi, vol):
    """Render raw 16-bit PCM at pitch, with envelope + loop (reference)."""
    n_frames = int(dur * rate)
    n_pcm = len(pcm)
    loop_len = n_pcm - loop_start if loop_start < n_pcm else n_pcm
    pitch_step = 2.0 ** ((midi_note - native_midi) / 12.0)
    note_off = int(dur * 0.8 * rate)
    out = []
    for i in range(n_frames):
        ipos = int(i * pitch_step)
        frac = (i * pitch_step) - ipos
        if loop_len > 0 and ipos >= n_pcm:
            ipos = loop_start + (ipos - loop_start) % loop_len
        if ipos >= n_pcm:
            ipos = n_pcm - 1
        p1 = ipos + 1
        if loop_len > 0 and p1 >= n_pcm:
            p1 = loop_start + (p1 - loop_start) % loop_len
        if p1 >= n_pcm:
            p1 = n_pcm - 1
        sample = pcm[ipos] * (1 - frac) + pcm[p1] * frac
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


def render_brr(blocks, n_blocks, loop_block, dur, rate, midi_note, native_midi, vol):
    n_frames = int(dur * rate)
    out = []
    pitch_step = 2.0 ** ((midi_note - native_midi) / 12.0)
    note_off = int(dur * 0.8 * rate)
    total_loop_samples = (n_blocks - loop_block) * 16
    if total_loop_samples <= 0:
        total_loop_samples = n_blocks * 16

    for i in range(n_frames):
        ipos = int(i * pitch_step)
        frac = (i * pitch_step) - ipos
        s0 = brr_decode_sample(blocks, n_blocks, loop_block, ipos)
        s1 = brr_decode_sample(blocks, n_blocks, loop_block, ipos + 1)
        sample = int(s0 * (1 - frac) + s1 * frac)

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


def render_seam(blocks, n_blocks, loop_block, dur, rate):
    """Pure loop, no envelope, 5 seconds"""
    decoded = brr_decode_all(blocks, n_blocks, loop_block, 1)
    n_fill = int(dur * rate)
    out = []
    pos = 0
    while len(out) < n_fill:
        out.append(decoded[pos % len(decoded)])
        pos += 1
    return out


def verify_seam(blocks, n_blocks, loop_block, n_cycles=50):
    """Check seam delta at loop boundary across n_cycles"""
    decoded = brr_decode_all(blocks, n_blocks, loop_block, n_cycles)
    loop_n = (n_blocks - loop_block) * 16
    if loop_n <= 0: return 9999, 9999
    seams = []
    for c in range(n_cycles):
        end_idx = c * loop_n - 1
        start_idx = c * loop_n
        if end_idx < len(decoded) and start_idx < len(decoded):
            seams.append(abs(decoded[start_idx] - decoded[end_idx]))
    return max(seams) if seams else 0, sum(seams)/len(seams) if seams else 0


# ADPCM tables (for size comparison only)
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
STEP_INC = [-16,-16,-16,-16,32,80,112,144]

def adpcm_encode_simple(pcm_samples):
    nibbles = []; acc = 0; step_idx = 0
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
    return bytes(result)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    print(f"{'Instrument':<40s} {'OrigKB':>6s} {'PCM16KB':>7s} {'ADPCMKB':>7s} {'BRRKB':>6s} {'Seam':>14s}")
    print('-' * 85)

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

        # BRR encode: attack + loop, loop block aligned to 16-sample boundary
        loop_s_aligned = (loop_s + 15) // 16 * 16
        loop_e_aligned = (loop_e + 15) // 16 * 16
        if loop_s_aligned >= n_17640:
            loop_s_aligned = 0
        if loop_e_aligned > n_17640:
            loop_e_aligned = n_17640

        blocks, n_blocks = brr_encode(pcm16_17640, loop_s_aligned)
        loop_block = loop_s_aligned // 16

        # Verify seam
        max_seam, avg_seam = verify_seam(blocks, n_blocks, loop_block)
        brr_kb = len(blocks) / 1024
        cn = pick.replace('.xi', '')
        native_midi = 24 + s['relnote'] + s['fine'] / 128.0
        vol = s['volume'] / 64.0
        loop_segs = loop_e_aligned - loop_s_aligned

        # Size comparison
        orig_kb = s['n_samples'] * 2 / 1024  # original 16-bit PCM
        pcm16_kb = n_17640 * 2 / 1024        # 17640Hz 16-bit PCM
        pcm12 = [max(-2048, min(2047, v >> 4)) for v in pcm16_17640]
        adpcm_bytes = adpcm_encode_simple(pcm12)
        adpcm_kb = len(adpcm_bytes) / 1024

        seam_ok = '*** PERFECT ***' if max_seam == 0 else f'seam={max_seam}'

        print(f'{cn:40s} {orig_kb:5.1f}  {pcm16_kb:6.1f}  {adpcm_kb:6.1f}  {brr_kb:5.1f}  {seam_ok}')

        # WAV 0: raw PCM at C4, 5s (reference)
        out_pcm = render_brr_pcm(pcm16_17640, loop_s_aligned, 5.0, TARGET_RATE, 60, native_midi, vol)
        wav0 = os.path.join(OUT_DIR, f'{cn}_pcm_C4.wav')
        with wave.open(wav0, 'w') as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(TARGET_RATE)
            wf.writeframes(struct.pack('<%dh' % len(out_pcm), *out_pcm))

        # WAV 1: BRR decoded at C4, 5s
        out_brr = render_brr(blocks, n_blocks, loop_block, 5.0, TARGET_RATE, 60, native_midi, vol)
        wav = os.path.join(OUT_DIR, f'{cn}_brr_C4.wav')
        with wave.open(wav, 'w') as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(TARGET_RATE)
            wf.writeframes(struct.pack('<%dh' % len(out_brr), *out_brr))

        # WAV 2: seam check, pure loop, 5s
        out_seam = render_seam(blocks, n_blocks, loop_block, 5.0, TARGET_RATE)
        wav2 = os.path.join(OUT_DIR, f'{cn}_seam.wav')
        with wave.open(wav2, 'w') as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(TARGET_RATE)
            wf.writeframes(struct.pack('<%dh' % len(out_seam), *out_seam))

    print(f'\nDone! WAV files in {OUT_DIR}')


if __name__ == '__main__':
    main()
