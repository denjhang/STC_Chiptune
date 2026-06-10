#!/usr/bin/env python3
"""ADPCM 线性插值变频测试 - ymdeltat.c ElSemi 插值算法"""

import struct, wave, re, os, math

def load_rom(path):
    data = []
    with open(path, 'r') as f:
        for line in f:
            for val in re.findall(r'0x([0-9A-Fa-f]{2})', line):
                data.append(int(val, 16))
    return bytes(data)

ROM = load_rom(os.path.join(os.path.dirname(__file__), '..', 'STC32G12K128', 'fmopn_2608rom.h'))

STEPS_TBL = [16,17,19,21,23,25,28,31,34,37,41,45,50,55,60,66,73,80,88,97,107,118,130,143,157,173,190,209,230,253,279,307,337,371,408,449,494,544,598,658,724,796,876,963,1060,1166,1282,1411,1552]
STEP_INC = [-16,-16,-16,-16,32,80,112,144]

def build_jedi():
    table = []
    for step in STEPS_TBL:
        row = []
        for nib in range(16):
            val = (2 * (nib & 7) + 1) * step // 8
            if nib & 8: val = -val
            row.append(val)
        table.append(row)
    return table

JEDI = build_jedi()

class ADPCM:
    """ADPCM Type A decoder with linear interpolation (ymdeltat.c style)"""

    def __init__(self, rom, start, length):
        self.rom = rom
        self.start = start  # byte offset
        self.length = length  # nibble count
        self.addr = 0
        self.acc = 0
        self.step_idx = 0
        self.cache = 0
        self.active = True
        self.now_step = 0
        self.s_prev = 0
        self.s_cur = 0

    def decode(self):
        if not self.active:
            return 0
        if self.addr & 1:
            nib = self.cache & 0x0F
        else:
            ri = self.start + (self.addr >> 1)
            if ri >= len(self.rom):
                self.active = False
                return 0
            self.cache = self.rom[ri]
            nib = (self.cache >> 4) & 0x0F
        self.addr += 1
        if self.addr >= self.length:
            self.active = False
            return 0
        row = self.step_idx >> 4
        delta = JEDI[row][nib]
        self.acc += delta
        self.acc &= 0xFFF
        if self.acc & 0x800:
            self.acc -= 0x1000
        self.step_idx += STEP_INC[nib & 7]
        if self.step_idx < 0: self.step_idx = 0
        if self.step_idx > 768: self.step_idx = 768
        return self.acc

    def tick(self, step_val):
        """
        8.8 fixed point step + linear interpolation.
        照搬 ymdeltat.c ElSemi 插值:
          adpcml = prev_acc * ((1<<SHIFT) - now_step)
          adpcml += acc * now_step
          adpcml >>= SHIFT
        """
        if not self.active:
            return 0

        self.now_step += step_val

        if self.now_step >= 0x100:
            cnt = self.now_step >> 8
            self.now_step &= 0xFF

            # do..while: 至少解码 1 个采样
            while True:
                self.s_prev = self.s_cur
                s = self.decode()
                if not self.active:
                    self.now_step = 0
                    return self.s_prev
                self.s_cur = s
                cnt -= 1
                if cnt == 0:
                    break

        # 线性插值 (仅低速时有效果, 高速/原速直接输出)
        if self.now_step > 0 and step_val < 0x100:
            frac = self.now_step
            out = self.s_prev * (0x100 - frac) + self.s_cur * frac
            return out >> 8
        else:
            return self.s_cur


def render(drum_byte_start, drum_nibbles, step_val, max_ticks, out_path):
    ch = ADPCM(ROM, drum_byte_start, drum_nibbles)
    ch.s_cur = ch.decode()  # prime first sample
    samples = []
    for _ in range(max_ticks):
        s = ch.tick(step_val)
        s = max(-32768, min(32767, int(s)))
        samples.append(s)
        if not ch.active:
            break
    with wave.open(out_path, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(17640)
        wf.writeframes(struct.pack(f'<{len(samples)}h', *samples))
    return len(samples)


def main():
    # TC: byte_start=0x040D, nibbles=5670
    TC_START = 0x040D
    TC_LEN = 5670
    BASE_STEP = 0x0100  # C4 = original speed

    out_dir = os.path.join(os.path.dirname(__file__), 'pitch_sweep')
    os.makedirs(out_dir, exist_ok=True)

    print("ADPCM 线性插值变频测试 (ymdeltat.c ElSemi style)")
    print(f"TC: start=0x{TC_START:04X} len={TC_LEN} nibbles")
    print(f"8.8 fp, C4=0x{BASE_STEP:04X}")
    print()

    max_ticks = 17640 * 4  # ~4 seconds

    for midi in [24, 36, 48, 60, 72, 84, 96, 108]:
        note_name = f'C{(midi - 12) // 12}'
        ratio = 2 ** ((midi - 60) / 12.0)
        step = int(BASE_STEP * ratio)
        step = max(1, min(step, 0xFFFF))

        path = os.path.join(out_dir, f'TC_{note_name}_interp.wav')
        n = render(TC_START, TC_LEN, step, max_ticks, path)
        dur = n / 17640
        tag = 'interp' if step < 0x100 else 'direct'
        print(f"  {note_name} (MIDI {midi:3d}): step=0x{step:04X} [{tag}] -> {n} samples ({dur:.3f}s)")

    print(f"\nDone! -> tools/pitch_sweep/")


if __name__ == "__main__":
    main()
