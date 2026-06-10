#!/usr/bin/env python3
"""钢琴采样变频测试: Grand Piano C3 -> 降采样17640 -> ADPCM编码 -> 变频C1~C8"""

import struct, wave, re, os, math

# ========== 降采样 ==========
def resample(samples, src_rate, dst_rate):
    if src_rate == dst_rate:
        return samples
    ratio = src_rate / dst_rate
    n = int(len(samples) / ratio)
    out = []
    for i in range(n):
        pos = i * ratio
        idx = int(pos)
        frac = pos - idx
        if idx + 1 < len(samples):
            s = samples[idx] * (1 - frac) + samples[idx + 1] * frac
        else:
            s = samples[idx] if idx < len(samples) else 0
        out.append(int(s))
    return out

# ========== ADPCM 编码 (Type A, jedi_table) ==========
STEPS_TBL = [16,17,19,21,23,25,28,31,34,37,41,45,50,55,60,66,73,80,88,97,107,118,130,143,157,173,190,209,230,253,279,307,337,371,408,449,494,544,598,658,724,796,876,963,1060,1166,1282,1411,1552]
STEP_INC_ENC = [-16,-16,-16,-16,32,80,112,144]

def adpcm_encode(pcm):
    nibbles = []
    acc = 0
    step_idx = 0

    def find_best_nibble(acc, step_idx, target):
        row = step_idx >> 4
        step = STEPS_TBL[row]
        best_nib = 0
        best_diff = 999999
        for nib in range(16):
            val = (2 * (nib & 7) + 1) * step // 8
            if nib & 8: val = -val
            test = (acc + val) & 0xFFF
            if test & 0x800: test -= 0x1000
            diff = abs(test - target)
            if diff < best_diff:
                best_diff = diff
                best_nib = nib
        return best_nib

    for s in pcm:
        # clamp to 12-bit
        target = max(-2048, min(2047, s))
        nib = find_best_nibble(acc, step_idx, target)
        nibbles.append(nib)

        row = step_idx >> 4
        step = STEPS_TBL[row]
        delta = (2 * (nib & 7) + 1) * step // 8
        if nib & 8: delta = -delta
        acc += delta
        acc &= 0xFFF

        step_idx += STEP_INC_ENC[nib & 7]
        if step_idx < 0: step_idx = 0
        if step_idx > 768: step_idx = 768

    # pack nibbles to bytes
    result = bytearray()
    for i in range(0, len(nibbles), 2):
        hi = nibbles[i]
        lo = nibbles[i + 1] if i + 1 < len(nibbles) else 0
        result.append((hi << 4) | lo)
    return bytes(result), len(nibbles)

# ========== ADPCM 解码 + 插值 ==========
JEDI = []
for step in STEPS_TBL:
    row = []
    for nib in range(16):
        val = (2 * (nib & 7) + 1) * step // 8
        if nib & 8: val = -val
        row.append(val)
    JEDI.append(row)
STEP_INC = [-16,-16,-16,-16,32,80,112,144]

class ADPCM:
    def __init__(self, rom, start, length, use_interp=False):
        self.rom = rom
        self.start = start
        self.length = length
        self.addr = 0
        self.acc = 0
        self.step_idx = 0
        self.cache = 0
        self.active = True
        self.now_step = 0
        self.s_prev = 0
        self.s_cur = 0
        self.use_interp = use_interp

    def decode(self):
        if not self.active: return 0
        if self.addr & 1:
            nib = self.cache & 0x0F
        else:
            ri = self.start + (self.addr >> 1)
            if ri >= len(self.rom): self.active = False; return 0
            self.cache = self.rom[ri]
            nib = (self.cache >> 4) & 0x0F
        self.addr += 1
        if self.addr >= self.length: self.active = False; return 0
        row = self.step_idx >> 4
        delta = JEDI[row][nib]
        self.acc += delta
        self.acc &= 0xFFF
        if self.acc & 0x800: self.acc -= 0x1000
        self.step_idx += STEP_INC[nib & 7]
        if self.step_idx < 0: self.step_idx = 0
        if self.step_idx > 768: self.step_idx = 768
        return self.acc

    def tick(self, step_val):
        if not self.active: return 0
        self.now_step += step_val
        if self.now_step >= 0x100:
            cnt = self.now_step >> 8
            self.now_step &= 0xFF
            while True:
                self.s_prev = self.s_cur
                s = self.decode()
                if not self.active: self.now_step = 0; return self.s_prev
                self.s_cur = s
                cnt -= 1
                if cnt == 0: break
        if self.use_interp and self.now_step > 0 and step_val < 0x100:
            frac = self.now_step
            out = self.s_prev * (0x100 - frac) + self.s_cur * frac
            return out >> 8
        else:
            return self.s_cur


def main():
    src_path = os.path.join(os.path.dirname(__file__), 'Grand Piano - C3.wav')
    out_dir = os.path.join(os.path.dirname(__file__), 'piano_sweep')
    os.makedirs(out_dir, exist_ok=True)

    # 读取原始 WAV
    with wave.open(src_path, 'r') as wf:
        pcm = list(struct.unpack(f'<{wf.getnframes()}h', wf.readframes(wf.getnframes())))
    print(f"原始: {len(pcm)} samples @ {32000}Hz, {len(pcm)/32000:.2f}s")

    # 降采样到 17640Hz
    pcm_17640 = resample(pcm, 32000, 17640)
    print(f"降采样: {len(pcm_17640)} samples @ 17640Hz, {len(pcm_17640)/17640:.2f}s")

    # ADPCM 编码
    rom_data, nib_count = adpcm_encode(pcm_17640)
    print(f"ADPCM: {len(rom_data)} bytes ({nib_count} nibbles)")

    # 先输出原始降采样参考
    ref_path = os.path.join(out_dir, 'piano_ref_17640.wav')
    with wave.open(ref_path, 'w') as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(17640)
        wf.writeframes(struct.pack(f'<{len(pcm_17640)}h', *pcm_17640))

    # C3=原速, step=0x0100
    BASE_STEP = 0x0100

    print()
    max_ticks = 17640 * 4

    for midi in [24, 36, 48, 60, 72, 84, 96, 108]:
        note_name = f'C{(midi - 12) // 12}'
        ratio = 2 ** ((midi - 60) / 12.0)
        step = int(BASE_STEP * ratio)
        step = max(1, min(step, 0xFFFF))

        # 有插值版
        ch = ADPCM(rom_data, 0, nib_count, use_interp=True)
        ch.s_cur = ch.decode()
        samples = []
        for _ in range(max_ticks):
            s = ch.tick(step)
            s = max(-32768, min(32767, int(s)))
            samples.append(s)
            if not ch.active: break

        path = os.path.join(out_dir, f'piano_{note_name}.wav')
        with wave.open(path, 'w') as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(17640)
            wf.writeframes(struct.pack(f'<{len(samples)}h', *samples))
        dur = len(samples) / 17640
        tag = 'interp' if step < 0x100 else 'direct'
        print(f"  {note_name} (MIDI {midi:3d}): step=0x{step:04X} [{tag}] -> {len(samples)} ({dur:.3f}s)")

    # 额外输出 C1 无插值版对比
    step_c1 = int(BASE_STEP * 2 ** ((24 - 60) / 12.0))
    ch = ADPCM(rom_data, 0, nib_count, use_interp=False)
    ch.s_cur = ch.decode()
    samples = []
    for _ in range(max_ticks):
        s = ch.tick(step_c1)
        s = max(-32768, min(32767, int(s)))
        samples.append(s)
        if not ch.active: break
    path = os.path.join(out_dir, 'piano_C1_no_interp.wav')
    with wave.open(path, 'w') as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(17640)
        wf.writeframes(struct.pack(f'<{len(samples)}h', *samples))
    print(f"  C1 no-interp: step=0x{step_c1:04X} -> {len(samples)} ({len(samples)/17640:.3f}s)")

    print(f"\nDone! -> tools/piano_sweep/")


if __name__ == "__main__":
    main()
