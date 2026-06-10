#!/usr/bin/env python3
"""SF2 乐器用鼓声编码器编码 -> PC 端解码播放 (无ADSR无loop)
和鼓声完全相同的编码/解码路径，验证音质"""

import struct, os, wave, json, math

WAV_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'adpcm_wav')
OUT_DIR = os.path.join(WAV_DIR, 'drum_test')
os.makedirs(OUT_DIR, exist_ok=True)

SF2_ROOT = 'D:/working/vscode-projects/Reference_Project/STC-MCU/sf2_extract'
TARGET_RATE = 17640

INSTRUMENTS = [
    ('01_piano.wav',      'snes_unofficial', 35, 'Piano'),
    ('02_slapbass.wav',   'snes_unofficial', 34, 'SlapBass'),
    ('03_shakuhachi.wav', 'microgm',         211, 'Shakuhachi'),
    ('04_oboe.wav',       'snes_unofficial', 102, 'Oboe'),
    ('05_trumpet.wav',    'snes_unofficial', 45, 'Trumpet'),
    ('06_blow.wav',       'microgm',         207, 'Blow'),
    ('07_oboe2.wav',      'snes_unofficial', 69, 'Oboe2'),
    ('08_strings.wav',    'snes_unofficial', 50, 'Strings'),
    ('09_harp.wav',       'snes_unofficial', 90, 'Harp'),
    ('10_guitar.wav',     'snes_unofficial', 91, 'Guitar'),
]

# ========== 和 adpcm_preprocess.py 完全一致 ==========
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
    nibbles = []
    acc = 0
    step_idx = 0
    for s in pcm_samples:
        if s > 2047: s = 2047
        if s < -2048: s = -2048
        best_nib = 0
        best_diff = abs(s - acc)
        row_idx = step_idx // 16
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
        hi = nibbles[i]
        lo = nibbles[i + 1] if i + 1 < len(nibbles) else 0
        result.append((hi << 4) | lo)
    return bytes(result), len(nibbles)


def adpcm_decode(data, start_byte, nib_count):
    acc = 0; step_idx = 0; samples = []
    for i in range(nib_count):
        addr = start_byte + (i >> 1)
        if addr >= len(data): break
        nib = (data[addr] >> 4) & 0x0F if not (i & 1) else data[addr] & 0x0F
        delta = JEDI[step_idx // 16][nib]
        acc += delta; acc &= 0xFFF
        if acc & 0x800: acc |= ~0xFFF
        samples.append(acc)
        step_idx += STEP_INC[nib & 7]
        if step_idx < 0: step_idx = 0
        if step_idx > 768: step_idx = 768
    return samples


def load_metadata(sf2_source, sf2_id):
    path = os.path.join(SF2_ROOT, sf2_source, 'sf2_mapping.json')
    with open(path) as f:
        data = json.load(f)
    key = str(sf2_id)
    if key not in data['samples']:
        return None
    return data['samples'][key]


def main():
    print(f"=== SF2 Drum-Path Test (no ADSR, no loop) ===\n")

    for wav_name, sf2_src, sf2_id, display in INSTRUMENTS:
        meta = load_metadata(sf2_src, sf2_id)
        if meta is None:
            continue

        # 读取原始 WAV
        wav_path = os.path.join(WAV_DIR, wav_name)
        with wave.open(wav_path, 'r') as w:
            raw = w.readframes(w.getnframes())
        pcm16 = list(struct.unpack('<%dh' % (len(raw) // 2), raw))
        n_samples = len(pcm16)

        # 归一化到 12-bit (和 adpcm_preprocess.py 对鼓声的做法一致: clamp to 12-bit)
        # 鼓声解码后已经是12-bit, clamp即可
        # 这里SF2是16-bit, 需要归一化
        peak = max(abs(s) for s in pcm16)
        scale = 2047.0 / peak if peak > 0 else 1.0
        normalized = [int(s * scale) for s in pcm16]

        # ADPCM 编码 (和鼓声完全一样的编码器)
        adpcm_data, nib_count = adpcm_encode(normalized)

        # ADPCM 解码 (和鼓声完全一样的解码器)
        decoded = adpcm_decode(adpcm_data, 0, nib_count)

        # SNR
        err = [normalized[i] - decoded[i] for i in range(min(len(normalized), len(decoded)))]
        mse = sum(e * e for e in err) / len(err) if err else 0
        sig = sum(s * s for s in normalized) / len(normalized) if normalized else 0
        snr = 10 * sig / mse if mse > 0 else 999

        # 输出 WAV: 解码后反归一化到 16-bit
        decoded_16 = [max(-32768, min(32767, int(s / scale))) for s in decoded]

        out_path = os.path.join(OUT_DIR, f'drum_{os.path.splitext(wav_name)[0]}.wav')
        with wave.open(out_path, 'w') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(TARGET_RATE)
            wf.writeframes(struct.pack('<%dh' % len(decoded_16), *decoded_16))

        print(f"  {display:12s} n={n_samples:5d} adpcm={len(adpcm_data):5d}B snr={snr:5.1f}dB -> {out_path}")

    # 同时输出原始 PCM 对照
    print("\n--- Original PCM reference ---")
    for wav_name, sf2_src, sf2_id, display in INSTRUMENTS:
        wav_path = os.path.join(WAV_DIR, wav_name)
        with wave.open(wav_path, 'r') as w:
            raw = w.readframes(w.getnframes())
        pcm16 = list(struct.unpack('<%dh' % (len(raw) // 2), raw))

        # 归一化到 16-bit 满幅
        peak = max(abs(s) for s in pcm16)
        norm = [max(-32768, min(32767, int(s * 32767.0 / peak))) for s in pcm16] if peak > 0 else pcm16

        out_path = os.path.join(OUT_DIR, f'pcm_{os.path.splitext(wav_name)[0]}.wav')
        with wave.open(out_path, 'w') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(TARGET_RATE)
            wf.writeframes(struct.pack('<%dh' % len(norm), *norm))

    print("\nDone. Listen to drum_xxx.wav vs pcm_xxx.wav")


if __name__ == '__main__':
    main()
