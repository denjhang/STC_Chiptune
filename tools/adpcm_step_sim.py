#!/usr/bin/env python3
"""ADPCM 仿真 - fixed point step 变速渲染, 输出 WAV 验证音高"""

import struct, wave, re, sys
import os

# ========== 读取预处理后的 ROM (本项目的 fmopn_2608rom.h) ==========
def load_rom(path):
    data = []
    with open(path, 'r') as f:
        for line in f:
            for val in re.findall(r'0x([0-9A-Fa-f]{2})', line):
                data.append(int(val, 16))
    return bytes(data)

ROM = load_rom(os.path.join(os.path.dirname(__file__), '..', 'STC32G12K128', 'fmopn_2608rom.h'))

# ========== jedi_table (49 x 16 = 784 s16) ==========
STEPS = [
    16, 17, 19, 21, 23, 25, 28, 31, 34, 37, 41, 45, 50, 55, 60, 66,
    73, 80, 88, 97, 107, 118, 130, 143, 157, 173, 190, 209, 230, 253,
    279, 307, 337, 371, 408, 449, 494, 544, 598, 658, 724, 796, 876,
    963, 1060, 1166, 1282, 1411, 1552
]

def build_jedi():
    table = []
    for step in STEPS:
        row = []
        for nib in range(16):
            val = (2 * (nib & 7) + 1) * step // 8
            if nib & 8:
                val = -val
            row.append(val)
        table.append(row)
    return table

JEDI = build_jedi()

# ========== step_inc ==========
STEP_INC = [-16, -16, -16, -16, 32, 80, 112, 144]

# ========== 鼓参数 (预处理后的布局) ==========
NAMES = ['BD', 'SD', 'TC', 'HH', 'TM', 'RS']
DRUM_START = [0x0000, 0x01AB, 0x040D, 0x0F20, 0x108E, 0x12F0]
DRUM_LEN   = [854, 1219, 5670, 732, 1219, 244]
# 预设 step (8.8 fp): 0x100=原速17640Hz, 0x080=半速8820Hz
DRUM_STEP  = [0x100, 0x100, 0x080, 0x100, 0x080, 0x080]

# ========== ADPCM 解码器 ==========
class ADPCMChannel:
    def __init__(self, rom, start, length):
        self.rom = rom
        self.start = start
        self.length = length
        self.reset()

    def reset(self):
        self.addr = 0
        self.acc = 0
        self.step_idx = 0
        self.cache = 0
        self.now_step = 0
        self.active = True
        self.out = 0

    def decode_one(self):
        if not self.active:
            return 0
        # 读 nibble
        if self.addr & 1:
            nib = self.cache & 0x0F
        else:
            rom_idx = self.start + (self.addr >> 1)
            if rom_idx >= len(self.rom):
                self.active = False
                return 0
            self.cache = self.rom[rom_idx]
            nib = (self.cache >> 4) & 0x0F
        self.addr += 1

        if self.addr >= self.length:
            self.active = False
            return 0

        # jedi_table 查表
        row = self.step_idx >> 4
        delta = JEDI[row][nib]
        self.acc += delta
        self.acc &= 0xFFF

        # 12-bit 符号扩展到 s16
        if self.acc & 0x800:
            self.acc -= 0x1000

        # 更新 step
        self.step_idx += STEP_INC[nib & 7]
        if self.step_idx < 0: self.step_idx = 0
        if self.step_idx > 768: self.step_idx = 768

        self.out = self.acc
        return self.out

    def render_tick(self, step_val):
        """模拟一个输出 tick, step_val 是 8.8 fixed point 步长"""
        if not self.active:
            return 0
        self.now_step += step_val
        out = 0
        while self.now_step >= 0x100:
            step_cnt = self.now_step >> 8
            self.now_step &= 0xFF
            for _ in range(step_cnt):
                s = self.decode_one()
                if not self.active:
                    self.now_step = 0
                    break
                out = s
        return out

# ========== 渲染 WAV ==========
def render_wav(drum_idx, step_val, num_ticks, out_path, sample_rate=17640):
    ch = ADPCMChannel(ROM, DRUM_START[drum_idx], DRUM_LEN[drum_idx])
    # 如果 step_val 和默认不同，说明自定义 step
    samples = []
    for _ in range(num_ticks):
        s = ch.render_tick(step_val)
        # clamp to 16-bit
        s = max(-32768, min(32767, s))
        samples.append(s)
        if not ch.active:
            break

    with wave.open(out_path, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f'<{len(samples)}h', *samples))
    return samples

def main():
    drum_idx = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    drum_idx = drum_idx % 6
    out_dir = os.path.join(os.path.dirname(__file__), 'step_sim_wav')

    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    print(f"ADPCM step 仿真 - {NAMES[drum_idx]}")
    print(f"ROM: {len(ROM)} bytes, 鼓: start=0x{DRUM_START[drum_idx]:04X} len={DRUM_LEN[drum_idx]} nibbles")
    print(f"默认 step=0x{DRUM_STEP[drum_idx]:02X}")
    print()

    tests = [
        (0x40,  "quarter_speed"),
        (0x80,  "half_speed"),
        (0xFF,  "~normal_speed"),
        (0x100, "normal_speed"),
    ]

    for step_val, label in tests:
        out_path = os.path.join(out_dir, f"{NAMES[drum_idx]}_{label}.wav")
        num_ticks = int(17640 * 2)  # ~2 秒
        samples = render_wav(drum_idx, step_val, num_ticks, out_path)
        actual_dur = len(samples) / 17640
        print(f"  step=0x{step_val:02X}: {len(samples)} samples, {actual_dur:.3f}s -> {out_path}")

    print("\nDone! 用播放器打开 tools/step_sim_wav/ 下的 WAV 听音高差异")

if __name__ == "__main__":
    main()
