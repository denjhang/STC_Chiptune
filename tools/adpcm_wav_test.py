#!/usr/bin/env python3
"""ADPCM 编码/解码/渲染实验 v3: 归一化 + 正确 pitch/loop/音量

关键改进:
- 编码前将 16-bit PCM 按峰值归一化到 12-bit 范围, 避免 clamp 截断
- 解码后反归一化还原到 16-bit
- 从 sf2_mapping.json 读取正确的 orig_pitch + loop 点
- 同时输出 PCM 对照渲染
"""

import struct, os, wave, json

WAV_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'adpcm_wav')
OUT_DIR = os.path.join(WAV_DIR, 'rendered')
TARGET_RATE = 17640

INSTRUMENTS = [
    ('01_piano.wav',      'snes_unofficial', 35),
    ('02_slapbass.wav',   'snes_unofficial', 34),
    ('03_shakuhachi.wav', 'microgm',         211),
    ('04_oboe.wav',       'snes_unofficial', 102),
    ('05_trumpet.wav',    'snes_unofficial', 45),
    ('06_blow.wav',       'microgm',         207),
    ('07_oboe2.wav',      'snes_unofficial', 69),
    ('08_strings.wav',    'snes_unofficial', 50),
    ('09_harp.wav',       'snes_unofficial', 90),
    ('10_guitar.wav',     'snes_unofficial', 91),
]

SF2_ROOT = 'D:/working/vscode-projects/Reference_Project/STC-MCU/sf2_extract'

STEPS = [
    16, 17, 19, 21, 23, 25, 28, 31, 34, 37, 41, 45, 50, 55, 60, 66,
    73, 80, 88, 97, 107, 118, 130, 143, 157, 173, 190, 209, 230, 253,
    279, 307, 337, 371, 408, 449, 494, 544, 598, 658, 724, 796, 876,
    963, 1060, 1166, 1282, 1411, 1552
]

def build_jedi_table():
    table = []
    for step in STEPS:
        row = []
        for nib in range(16):
            val = (2 * (nib & 7) + 1) * step // 8
            if nib & 8: val = -val
            row.append(val)
        table.append(row)
    return table

JEDI = build_jedi_table()
STEP_INC = [-16, -16, -16, -16, 32, 80, 112, 144]


def adpcm_encode(pcm_samples):
    """Encode PCM (already in -2048..2047 range) -> ADPCM bytes"""
    nibbles = []
    acc = 0
    step_idx = 0
    for s in pcm_samples:
        if s > 2047: s = 2047
        if s < -2048: s = -2048
        row_idx = step_idx // 16
        best_nib = 0
        best_diff = abs(s - acc)
        for nib in range(16):
            delta = JEDI[row_idx][nib]
            trial = acc + delta; trial &= 0xFFF
            if trial & 0x800: trial |= ~0xFFF
            diff = abs(s - trial)
            if diff < best_diff:
                best_diff = diff; best_nib = nib
        delta = JEDI[row_idx][best_nib]
        acc += delta; acc &= 0xFFF
        if acc & 0x800: acc |= ~0xFFF
        step_idx += STEP_INC[best_nib & 7]
        if step_idx < 0: step_idx = 0
        if step_idx > 768: step_idx = 768
        nibbles.append(best_nib)
    result = bytearray()
    for i in range(0, len(nibbles), 2):
        hi = nibbles[i]; lo = nibbles[i + 1] if i + 1 < len(nibbles) else 0
        result.append((hi << 4) | lo)
    return bytes(result), len(nibbles)


def adpcm_decode(adpcm_bytes, nibble_count):
    """Decode ADPCM bytes -> 12-bit PCM samples"""
    acc = 0; step_idx = 0; samples = []
    for i in range(nibble_count):
        addr = i >> 1
        if addr >= len(adpcm_bytes): break
        nib = (adpcm_bytes[addr] >> 4) & 0x0F if not (i & 1) else adpcm_bytes[addr] & 0x0F
        delta = JEDI[step_idx // 16][nib]
        acc += delta; acc &= 0xFFF
        if acc & 0x800: acc |= ~0xFFF
        samples.append(acc)
        step_idx += STEP_INC[nib & 7]
        if step_idx < 0: step_idx = 0
        if step_idx > 768: step_idx = 768
    return samples


def render_voice(pcm, loop_s, loop_e, has_loop, orig_pitch, midi_note=60, dur=3.0):
    """Render C4 audition: pitch shift + loop + ADSR envelope
    pcm 应该是归一化到满幅的 float 或 int 数组
    """
    semi = midi_note - orig_pitch
    pitch_ratio = 2.0 ** (semi / 12.0)
    n_frames = int(dur * TARGET_RATE)
    out = []

    # 归一化到接近 16-bit 满幅
    peak = max(abs(s) for s in pcm)
    if peak == 0:
        peak = 1
    norm = 32000.0 / peak

    pos = 0.0
    note_off_time = dur * 0.7

    for i in range(n_frames):
        t = i / TARGET_RATE

        if has_loop and loop_e > loop_s and pos >= loop_e:
            loop_len = loop_e - loop_s
            pos = loop_s + (pos - loop_s) % loop_len

        idx = int(pos)
        frac = pos - idx
        if idx < 0 or idx >= len(pcm):
            break

        next_idx = idx + 1
        if has_loop and next_idx >= loop_e:
            next_idx = loop_s
        elif next_idx >= len(pcm):
            next_idx = idx

        s = pcm[idx] * (1 - frac) + pcm[next_idx] * frac
        s *= norm
        pos += pitch_ratio

        # ADSR envelope
        if t < 0.01:
            e = t / 0.01
        elif t < 0.15:
            e = 1.0 - 0.3 * ((t - 0.01) / 0.14)
        elif t < note_off_time:
            e = 0.7
        else:
            e = max(0, 0.7 * (1.0 - (t - note_off_time) / (dur - note_off_time)))

        out.append(max(-32768, min(32767, int(s * e))))

    return out


def load_metadata(sf2_source, sf2_id):
    path = os.path.join(SF2_ROOT, sf2_source, 'sf2_mapping.json')
    with open(path) as f:
        data = json.load(f)
    key = str(sf2_id)
    if key not in data['samples']:
        print(f"  WARNING: {sf2_source} #{sf2_id} not found!")
        return None
    return data['samples'][key]


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    print(f"=== ADPCM v3 (normalized): {len(INSTRUMENTS)} instruments ===\n")

    total_adpcm = 0

    for wav_name, sf2_src, sf2_id in INSTRUMENTS:
        meta = load_metadata(sf2_src, sf2_id)
        if meta is None:
            continue

        orig_pitch = meta['orig_pitch']
        loop_s = meta['loop_start']
        loop_e = meta['loop_end']
        has_loop = meta['has_loop']
        expected_n = meta['n_samples']

        # 读取 16-bit PCM WAV
        wav_path = os.path.join(WAV_DIR, wav_name)
        with wave.open(wav_path, 'r') as w:
            raw = w.readframes(w.getnframes())
        pcm16 = list(struct.unpack('<%dh' % (len(raw) // 2), raw))
        n_samples = len(pcm16)

        # clamp loop
        if loop_e > n_samples: loop_e = n_samples
        if loop_s >= loop_e: has_loop = False

        # 归一化: 16-bit peak -> 12-bit range (-2048..2047)
        peak = max(abs(s) for s in pcm16)
        scale = 2047.0 / peak if peak > 0 else 1.0
        normalized = [int(s * scale) for s in pcm16]

        # ADPCM encode (normalized 12-bit)
        adpcm_data, nib_count = adpcm_encode(normalized)
        adpcm_size = len(adpcm_data)
        total_adpcm += adpcm_size

        # ADPCM decode -> 12-bit
        decoded = adpcm_decode(adpcm_data, nib_count)

        # 反归一化: 12-bit -> 16-bit (float)
        decoded_16 = [s / scale for s in decoded]

        # SNR (normalized domain)
        err = [normalized[i] - decoded[i] for i in range(min(len(normalized), len(decoded)))]
        mse = sum(e * e for e in err) / len(err) if err else 0
        sig = sum(s * s for s in normalized) / len(normalized)
        snr = 10 * sig / mse if mse > 0 else 999

        base = os.path.splitext(wav_name)[0]

        # ADPCM 渲染
        adpcm_rendered = render_voice(decoded_16, loop_s, loop_e, has_loop, orig_pitch)
        adpcm_wav_path = os.path.join(OUT_DIR, f"adpcm_{base}.wav")
        with wave.open(adpcm_wav_path, 'w') as rw:
            rw.setnchannels(1); rw.setsampwidth(2); rw.setframerate(TARGET_RATE)
            rw.writeframes(struct.pack('<%dh' % len(adpcm_rendered), *adpcm_rendered))

        # PCM 对照渲染
        pcm_rendered = render_voice(pcm16, loop_s, loop_e, has_loop, orig_pitch)
        pcm_wav_path = os.path.join(OUT_DIR, f"pcm_{base}.wav")
        with wave.open(pcm_wav_path, 'w') as rw:
            rw.setnchannels(1); rw.setsampwidth(2); rw.setframerate(TARGET_RATE)
            rw.writeframes(struct.pack('<%dh' % len(pcm_rendered), *pcm_rendered))

        print(f"  {wav_name:20s}  n={n_samples:5d}  peak={peak:6d}  ADPCM={adpcm_size:5d}B  SNR={snr:.1f}dB")

    print(f"\n  ADPCM total: {total_adpcm}B ({total_adpcm / 1024:.1f} KB)")
    print(f"\n  adpcm_xxx.wav = ADPCM (normalized encode)")
    print(f"  pcm_xxx.wav   = original 16-bit PCM (reference)")


if __name__ == '__main__':
    main()
