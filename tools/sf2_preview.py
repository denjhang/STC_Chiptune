#!/usr/bin/env python3
"""SF2 乐器预览: 有音高(pitch shift) + loop, 无ADSR

模拟 MCU 完整路径:
  公式编码 -> 硬编码表解码 -> addr > loop_end 回绕(重置acc/step)
  无包络, 线性插值变速, vol=31, >>5衰减
"""

import struct, os, wave, json

WAV_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'adpcm_wav')
OUT_DIR = os.path.join(WAV_DIR, 'sf2_preview')
os.makedirs(OUT_DIR, exist_ok=True)

SF2_ROOT = 'D:/working/vscode-projects/Reference_Project/STC-MCU/sf2_extract'
TARGET_RATE = 17640

STEPS = [16,17,19,21,23,25,28,31,34,37,41,45,50,55,60,66,
         73,80,88,97,107,118,130,143,157,173,190,209,230,253,279,307,337,371,408,449,494,544,598,658,724,796,876,963,1060,1166,1282,1411,1552]

def build_jedi():
    t = []
    for step in STEPS:
        row = []
        for nib in range(16):
            val = (2 * (nib & 7) + 1) * step // 8
            if nib & 8: val = -val
            row.append(val)
        t.append(row)
    return t

JEDI = build_jedi()
JEDI_FLAT = []
for row in JEDI: JEDI_FLAT.extend(row)
STEP_INC = [-16,-16,-16,-16,32,80,112,144]

INSTRUMENTS = [
    ('01_piano.wav',      'snes_unofficial', 35, 'Piano'),
    ('02_slapbass.wav',   'snes_unofficial', 34, 'SlapBass'),
    ('05_trumpet.wav',    'snes_unofficial', 45, 'Trumpet'),
    ('07_oboe2.wav',      'snes_unofficial', 69, 'Oboe2'),
    ('10_guitar.wav',     'snes_unofficial', 91, 'Guitar'),
]


def adpcm_encode(pcm, snap_nibble=-1):
    nibbles = []; acc = 0; step_idx = 0
    for i, s in enumerate(pcm):
        if s > 2047: s = 2047
        if s < -2048: s = -2048
        best = 0; bd = abs(s - acc)
        row = step_idx // 16
        for n in range(16):
            d = JEDI[row][n]
            t = acc + d; t &= 0xFFF
            if t & 0x800: t |= ~0xFFF
            if abs(s - t) < bd: bd = abs(s - t); best = n
        d = JEDI[row][best]
        acc += d; acc &= 0xFFF
        if acc & 0x800: acc |= ~0xFFF
        step_idx += STEP_INC[best & 7]
        if step_idx < 0: step_idx = 0
        if step_idx > 768: step_idx = 768
        nibbles.append(best)
    rom = bytearray()
    for i in range(0, len(nibbles), 2):
        hi = nibbles[i]; lo = nibbles[i + 1] if i + 1 < len(nibbles) else 0
        rom.append((hi << 4) | lo)
    rom = bytes(rom)
    snap = None
    if snap_nibble >= 0:
        dacc = 0; dstep = 0
        for i in range(min(snap_nibble + 1, len(nibbles))):
            byte_val = rom[i >> 1]
            nib = (byte_val >> 4) & 0x0F if not (i & 1) else byte_val & 0x0F
            d = JEDI_FLAT[dstep + nib]
            dacc += d; dacc &= 0xFFF
            if dacc & 0x800: dacc |= ~0xFFF
            dstep += STEP_INC[nib & 7]
            if dstep < 0: dstep = 0
            if dstep > 768: dstep = 768
            if i == snap_nibble:
                snap = (dacc & 0xFFF, dstep)
    return rom, len(nibbles), snap


def decode_one(rom, addr, acc, step, loop_start, loop_end, loop_acc, loop_step):
    """解码一个 nibble, 返回 (sample, new_addr, new_acc, new_step)"""
    byte_val = rom[addr >> 1]
    nib = (byte_val >> 4) & 0x0F if not (addr & 1) else byte_val & 0x0F
    d = JEDI_FLAT[step + nib]
    acc += d; acc &= 0xFFF
    if acc & 0x800: acc |= ~0xFFF
    sample = acc
    step += STEP_INC[nib & 7]
    if step < 0: step = 0
    if step > 768: step = 768
    addr += 1
    if addr > loop_end:
        addr = loop_start
        acc = loop_acc & 0xFFF
        if acc & 0x800: acc |= ~0xFFF
        step = loop_step
    return sample, addr, acc, step


def render_voice(rom, nib_count, loop_start, loop_end, loop_acc, loop_step,
                 midi_note, orig_pitch, dur=4.0):
    """8.8 fixed-point pitch shift + loop, 无ADSR, 直接从ROM逐nibble解码"""
    semi = midi_note - orig_pitch
    if semi == 0:
        pitch_ratio = 256  # 1.0 in 8.8
    elif semi > 0:
        oct = semi // 12
        r = semi % 12
        semi_table = [256, 271, 287, 304, 322, 341, 362, 383, 406, 430, 455, 482]
        pitch_ratio = semi_table[r] * (1 << oct)
    else:
        oct = (-semi) // 12
        r = (-semi) % 12
        semi_table = [256, 242, 228, 216, 203, 192, 181, 171, 161, 152, 144, 136]
        pitch_ratio = semi_table[r] >> oct

    n_frames = int(dur * TARGET_RATE)
    out = []

    # 解码器状态
    addr = 0; acc = 0; step = 0
    s_prev = 0
    s_cur = decode_one(rom, 0, 0, 0, loop_start, loop_end, loop_acc, loop_step)[0]

    now_step = 0

    for i in range(n_frames):
        now_step += pitch_ratio
        while now_step >= 256:
            s_prev = s_cur
            s_cur, addr, acc, step = decode_one(
                rom, addr, acc, step, loop_start, loop_end, loop_acc, loop_step)
            now_step -= 256

        frac = now_step
        if frac > 0 and pitch_ratio < 0x100:
            out_val = s_prev + (s_cur - s_prev) * frac / 256
        else:
            out_val = s_cur

        out_val = out_val * 31 >> 5
        out.append(max(-32768, min(32767, int(out_val))))

    return out


def main():
    for wav_name, sf2_src, sf2_id, display in INSTRUMENTS:
        meta_path = os.path.join(SF2_ROOT, sf2_src, 'sf2_mapping.json')
        with open(meta_path) as f:
            data = json.load(f)
        meta = data['samples'][str(sf2_id)]
        ls = meta['loop_start']
        le = meta['loop_end']
        orig_pitch = meta['orig_pitch']

        with wave.open(os.path.join(WAV_DIR, wav_name), 'r') as w:
            raw = w.readframes(w.getnframes())
        pcm16 = list(struct.unpack('<%dh' % (len(raw) // 2), raw))
        peak = max(abs(s) for s in pcm16)
        scale = 2047.0 / peak
        norm = [int(s * scale) for s in pcm16]

        rom, nib_count, snap = adpcm_encode(norm, snap_nibble=ls)
        loop_acc = snap[0] if snap else 0
        loop_step = snap[1] if snap else 0
        if loop_acc & 0x800: loop_acc = loop_acc - 0x1000

        print(f'{display:12s} op={orig_pitch} ls={ls} le={le} nib={nib_count} '
              f'loop_acc={loop_acc} loop_step={loop_step}')

        for midi in [60, 72]:
            note_name = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
            nn = f'{note_name[midi%12]}{midi//12-1}'
            print(f'  rendering {nn} ...')
            out = render_voice(rom, nib_count, ls, le, loop_acc, loop_step,
                               midi, orig_pitch, dur=3.0)
            out_path = os.path.join(OUT_DIR, f'{display}_{nn}.wav')
            with wave.open(out_path, 'w') as wf:
                wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(TARGET_RATE)
                wf.writeframes(struct.pack('<%dh' % len(out), *out))
            print(f'  -> {out_path}')

    print('\nDone.')


if __name__ == '__main__':
    main()
