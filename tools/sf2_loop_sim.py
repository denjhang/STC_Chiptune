#!/usr/bin/env python3
"""PC 仿真 MCU SF2 ADPCM 解码 + loop 回绕

模拟 MCU 完整路径:
  公式编码器编码 -> MCU 硬编码表解码 -> addr > loop_end 回绕 -> >>5 衰减
"""

import struct, os, wave, json

WAV_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'adpcm_wav')
OUT_DIR = os.path.join(WAV_DIR, 'loop_test')
os.makedirs(OUT_DIR, exist_ok=True)

SF2_ROOT = 'D:/working/vscode-projects/Reference_Project/STC-MCU/sf2_extract'
TARGET_RATE = 17640

# 公式 jedi_table (编码器)
STEPS = [16,17,19,21,23,25,28,31,34,37,41,45,50,55,60,66,
         73,80,88,97,107,118,130,143,157,173,190,209,230,253,
         279,307,337,371,408,449,494,544,598,658,724,796,876,
         963,1060,1166,1282,1411,1552]

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
STEP_INC = [-16,-16,-16,-16,32,80,112,144]

# MCU 硬编码 jedi_table (解码器, 784 s16 flat)
JEDI_FLAT = []
for row in JEDI:
    JEDI_FLAT.extend(row)

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


def adpcm_encode(pcm, snap_nibble=-1):
    nibbles = []
    acc = 0
    step_idx = 0
    snap = None
    for i, s in enumerate(pcm):
        if s > 2047: s = 2047
        if s < -2048: s = -2048
        best = 0
        bd = abs(s - acc)
        row = step_idx // 16
        for n in range(16):
            d = JEDI[row][n]
            t = acc + d
            t &= 0xFFF
            if t & 0x800: t |= ~0xFFF
            if abs(s - t) < bd:
                bd = abs(s - t)
                best = n
        d = JEDI[row][best]
        acc += d
        acc &= 0xFFF
        if acc & 0x800: acc |= ~0xFFF
        step_idx += STEP_INC[best & 7]
        if step_idx < 0: step_idx = 0
        if step_idx > 768: step_idx = 768
        nibbles.append(best)
        if i == snap_nibble:
            snap = (acc & 0xFFF, step_idx)
    rom = bytearray()
    for i in range(0, len(nibbles), 2):
        hi = nibbles[i]
        lo = nibbles[i + 1] if i + 1 < len(nibbles) else 0
        rom.append((hi << 4) | lo)
    return rom, len(nibbles), snap


def mcu_decode(rom_bytes, start_nib, loop_start, loop_end, n_samples,
               loop_acc=0, loop_step=0):
    """模拟 MCU 解码: 硬编码表 + addr > loop_end 回绕 + acc/step 重置"""
    samples = []
    addr = start_nib
    acc = 0
    step = 0
    for i in range(n_samples):
        byte_val = rom_bytes[addr >> 1]
        if addr & 1:
            nib = byte_val & 0x0F
        else:
            nib = (byte_val >> 4) & 0x0F
        d = JEDI_FLAT[step + nib]
        acc += d
        acc &= 0xFFF
        if acc & 0x800: acc |= ~0xFFF
        samples.append(acc)
        step += STEP_INC[nib & 7]
        if step < 0: step = 0
        if step > 768: step = 768
        addr += 1
        if addr > loop_end:
            addr = loop_start
            acc = loop_acc & 0xFFF
            if acc & 0x800: acc |= ~0xFFF
            step = loop_step
    return samples


def main():
    dur = 3.0
    dur_samples = int(dur * TARGET_RATE)

    for wav_name, sf2_src, sf2_id, display in INSTRUMENTS:
        meta_path = os.path.join(SF2_ROOT, sf2_src, 'sf2_mapping.json')
        with open(meta_path) as f:
            data = json.load(f)
        meta = data['samples'][str(sf2_id)]
        ls = meta['loop_start']
        le = meta['loop_end']

        with wave.open(os.path.join(WAV_DIR, wav_name), 'r') as w:
            raw = w.readframes(w.getnframes())
        pcm16 = list(struct.unpack('<%dh' % (len(raw) // 2), raw))

        # 归一化到 12-bit
        peak = max(abs(s) for s in pcm16)
        scale = 2047.0 / peak if peak > 0 else 1.0
        normalized = [int(s * scale) for s in pcm16]

        rom, nib_count, snap = adpcm_encode(normalized, snap_nibble=ls)
        loop_acc = snap[0] if snap else 0
        loop_step = snap[1] if snap else 0
        if loop_acc & 0x800: loop_acc = loop_acc - 0x1000

        # MCU 解码 (含 loop + acc/step reset)
        decoded = mcu_decode(rom, 0, ls, le, dur_samples, loop_acc, loop_step)

        # >>5 衰减 + vol=31
        out_16 = [max(-32768, min(32767, s * 31 >> 5)) for s in decoded]

        out_path = os.path.join(OUT_DIR, f'mcu_{os.path.splitext(wav_name)[0]}.wav')
        with wave.open(out_path, 'w') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(TARGET_RATE)
            wf.writeframes(struct.pack('<%dh' % len(out_16), *out_16))

        # loop 接缝检测: 第一次回绕点
        wrap_idx = le + 1  # 播放 le 后 addr++ 变 le+1, 触发回绕到 ls
        # 但注意: start_nib=0, ls=1915, 所以 loop 在 decoded 中从 ls 开始
        # 第一次回绕发生在第 le+1 个采样之后, 即 decoded[le] 是 loop_end 的采样
        # decoded[le+1] 是回绕后 loop_start 的采样
        if le + 1 < len(decoded):
            print(f'{display:12s} ls={ls:5d} le={le:5d} '
                  f'wrap: [{le}]={decoded[le]} -> [{le+1}]={decoded[le+1]} '
                  f'diff={abs(decoded[le] - decoded[le+1])}')
        print(f'  -> {out_path}')

    print('\nDone.')


if __name__ == '__main__':
    main()
