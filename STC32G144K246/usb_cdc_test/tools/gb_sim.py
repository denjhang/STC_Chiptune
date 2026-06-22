#!/usr/bin/env py -3
"""gb.c 的 Python 等价仿真器。
喂真实 GB VGM 进去, 看 gb_render() 输出什么, 定位"没声音"根因。

用法:
    py -3 gb_sim.py "vgm/gb/01 Spring in Your Step.vgz" [--max-samples 5000]
"""
import sys, os, gzip, struct, argparse

# ========== 常量 (与 gb.h / gb.c 一致) ==========
GB_CLOCK        = 4194304
SAMPLE_RATE     = 22050
GB_GETA_BITS    = 24
GB_BASE_INCR    = (GB_CLOCK << GB_GETA_BITS) // SAMPLE_RATE   # u32 累加步进
FRAME_CYCLES    = 8192

# 寄存器地址
NR10=0x00; NR11=0x01; NR12=0x02; NR13=0x03; NR14=0x04
NR21=0x06; NR22=0x07; NR23=0x08; NR24=0x09
NR30=0x0A; NR31=0x0B; NR32=0x0C; NR33=0x0D; NR34=0x0E
NR41=0x10; NR42=0x11; NR43=0x12; NR44=0x13
NR50=0x14; NR51=0x15; NR52=0x16
AUD3W0=0x20

WAVE_DUTY = [
    [-1,-1,-1,-1,-1,-1,-1, 1],
    [ 1,-1,-1,-1,-1,-1,-1, 1],
    [ 1,-1,-1,-1,-1, 1, 1, 1],
    [-1, 1, 1, 1, 1, 1, 1,-1],
]

class SOUND:
    __slots__ = ['reg','on','channel','length','length_mask','length_counting',
                 'length_enabled','cycles_left','duty','envelope_enabled',
                 'envelope_value','envelope_direction','envelope_time',
                 'envelope_count','signal','frequency','distance',
                 'sweep_enabled','sweep_neg_mode_used','sweep_shift',
                 'sweep_direction','sweep_time','sweep_count','level','offset',
                 'frequency_counter','duty_count','noise_short','noise_rng']
    def __init__(self, channel, length_mask):
        self.reg=[0,0,0,0,0]; self.on=0; self.channel=channel
        self.length=0; self.length_mask=length_mask; self.length_counting=0
        self.length_enabled=0; self.cycles_left=0; self.duty=0
        self.envelope_enabled=0; self.envelope_value=0; self.envelope_direction=0
        self.envelope_time=0; self.envelope_count=0; self.signal=0
        self.frequency=0; self.distance=0x800; self.sweep_enabled=0
        self.sweep_neg_mode_used=0; self.sweep_shift=0; self.sweep_direction=0
        self.sweep_time=0; self.sweep_count=0; self.level=0; self.offset=0
        self.frequency_counter=0; self.duty_count=0; self.noise_short=0; self.noise_rng=0

def mask32(x):  return x & 0xFFFFFFFF

# ========== 仿真核心 (逐行对齐 gb.c) ==========
class GB:
    def __init__(self):
        self.regs = [0]*0x30
        self.snd1 = SOUND(1, 0x3F)
        self.snd2 = SOUND(2, 0x3F)
        self.snd3 = SOUND(3, 0xFF)
        self.snd4 = SOUND(4, 0x3F)
        self.ctrl_on = 0
        self.vol_left = 0; self.vol_right = 0
        self.mode1_left=0; self.mode1_right=0
        self.mode2_left=0; self.mode2_right=0
        self.mode3_left=0; self.mode3_right=0
        self.mode4_left=0; self.mode4_right=0
        self.cycles = 0
        self.base_count = 0
        self.hp_y = 0
        self.hp_x = 0
        self.gb_init()

    def gb_init(self):
        self.regs = [0]*0x30
        for s in (self.snd1, self.snd2, self.snd3, self.snd4):
            for attr in s.__slots__:
                if attr == 'channel': continue
                if attr == 'length_mask': continue
                setattr(s, attr, 0 if attr != 'reg' else [0,0,0,0,0])
        self.snd1.channel=1; self.snd1.length_mask=0x3F
        self.snd2.channel=2; self.snd2.length_mask=0x3F
        self.snd3.channel=3; self.snd3.length_mask=0xFF
        self.snd4.channel=4; self.snd4.length_mask=0x3F
        # DMG 默认波形 RAM
        default_wave = [0xac,0xdd,0xda,0x48,0x36,0x02,0xcf,0x16,
                        0x2c,0x04,0xe5,0x2c,0xac,0xdd,0xda,0x48]
        for i,v in enumerate(default_wave):
            self.regs[AUD3W0+i] = v
        self.ctrl_on = 1
        self.cycles = 0
        self.base_count = 0
        self.hp_y = 0                # RC 高通滤波器状态
        self.hp_x = 0

    def dac_enabled(self, snd):
        if snd.channel != 3:
            return 1 if (snd.reg[2] & 0xF8) else 0
        return 1 if (snd.reg[0] & 0x80) else 0

    def tick_length(self, snd):
        if snd.length_enabled:
            snd.length = (snd.length + 1) & snd.length_mask
            if snd.length == 0:
                snd.on = 0
                snd.length_counting = 0

    def calculate_next_sweep(self, snd):
        snd.sweep_neg_mode_used = 1 if snd.sweep_direction < 0 else 0
        new_freq = snd.frequency + snd.sweep_direction * (snd.frequency >> snd.sweep_shift)
        if new_freq > 0x7FF: snd.on = 0
        return new_freq

    def apply_next_sweep(self, snd):
        new_freq = self.calculate_next_sweep(snd)
        if snd.on and snd.sweep_shift > 0:
            snd.frequency = new_freq & 0xFFFF
            snd.reg[3] = snd.frequency & 0xFF

    def tick_sweep(self, snd):
        snd.sweep_count = (snd.sweep_count - 1) & 0x07
        if snd.sweep_count == 0:
            snd.sweep_count = snd.sweep_time
            if snd.sweep_enabled and snd.sweep_time > 0:
                self.apply_next_sweep(snd)
                self.calculate_next_sweep(snd)

    def tick_envelope(self, snd):
        if snd.envelope_enabled:
            snd.envelope_count = (snd.envelope_count - 1) & 0x07
            if snd.envelope_count == 0:
                snd.envelope_count = snd.envelope_time
                if snd.envelope_count:
                    new_env = snd.envelope_value + snd.envelope_direction
                    if 0 <= new_env <= 15:
                        snd.envelope_value = new_env
                    else:
                        snd.envelope_enabled = 0

    def noise_period_cycles(self):
        divisor = [8,16,32,48,64,80,96,112]
        return divisor[self.snd4.reg[3] & 7] << (self.snd4.reg[3] >> 4)

    def update_square(self, snd, cycles):
        # 对齐 libvgm gb_update_square_channel: 双 distance + frequency_counter
        if not snd.on: return
        snd.cycles_left += cycles
        if snd.cycles_left <= 0: return
        cyc = snd.cycles_left >> 2
        snd.cycles_left &= 3
        distance = 0x800 - snd.frequency_counter
        if cyc >= distance:
            cyc -= distance
            distance = snd.distance      # 0x800 - frequency (预计算)
            counter = 1 + cyc // distance
            snd.duty_count = (snd.duty_count + counter) & 0x07
            snd.signal = WAVE_DUTY[snd.duty][snd.duty_count]
            snd.frequency_counter = snd.frequency + (cyc % distance)
        else:
            snd.frequency_counter += cyc

    def update_wave(self, snd, cycles):
        # 对齐优化版 gb.c: phaseacc 风格, period = 2 × distance
        if not snd.on: return
        period = snd.distance * 2
        if period == 0: return
        snd.cycles_left += cycles
        guard = 0
        while snd.cycles_left >= period and guard < 32:
            snd.cycles_left -= period; guard += 1
            snd.offset = (snd.offset + 1) & 0x1F
            b = self.regs[AUD3W0 + (snd.offset >> 1)]
            if not (snd.offset & 1): b >>= 4
            sig = (b & 0x0f) - 8
            if snd.level == 0: snd.signal = 0
            elif snd.level == 1: snd.signal = sig
            elif snd.level == 2: snd.signal = sig >> 1
            else: snd.signal = sig >> 2
        if guard >= 32: snd.cycles_left = 0

    def update_noise(self, snd, cycles):
        # 对齐优化版 gb.c: AY 风格 Galois LFSR, guard=8
        period = self.noise_period_cycles()
        if period == 0: return
        snd.cycles_left += cycles
        rng = snd.noise_rng
        guard = 0
        while snd.cycles_left >= period and guard < 8:
            snd.cycles_left -= period; guard += 1
            rng >>= 1
            if rng & 1: rng ^= 0x6000
            if snd.noise_short:
                rng = (rng & 0x007F) | ((rng & 1) << 6)
        snd.noise_rng = rng
        snd.signal = -1 if (rng & 1) else 1
        if guard >= 8: snd.cycles_left = 0

    def update_state(self, cycles):
        # 对齐优化版 gb.c: 位移代替除法, 不双倍调用 update
        if not self.ctrl_on: return
        old_cycles = self.cycles
        self.cycles = mask32(self.cycles + cycles)
        if (old_cycles >> 13) != (self.cycles >> 13):
            frame_step = (self.cycles >> 13) & 0x07
            if frame_step in (0,2,4,6):
                self.tick_length(self.snd1)
                self.tick_length(self.snd2)
                self.tick_length(self.snd3)
                self.tick_length(self.snd4)
                if frame_step in (2,6):
                    self.tick_sweep(self.snd1)
            elif frame_step == 7:
                self.tick_envelope(self.snd1)
                self.tick_envelope(self.snd2)
                self.tick_envelope(self.snd4)
        # 通道相位推进: 完整 cycles 一次 update (不拆分)
        self.update_square(self.snd1, cycles)
        self.update_square(self.snd2, cycles)
        self.update_wave(self.snd3, cycles)
        self.update_noise(self.snd4, cycles)

    def sound_w_internal(self, offset, val):
        old = self.regs[offset]
        if self.ctrl_on: self.regs[offset] = val
        s=None
        if offset in (NR10,NR11,NR12,NR13,NR14): s=self.snd1
        elif offset in (NR21,NR22,NR23,NR24): s=self.snd2
        elif offset in (NR30,NR31,NR32,NR33,NR34): s=self.snd3
        elif offset in (NR41,NR42,NR43,NR44): s=self.snd4

        if offset == NR10:
            self.snd1.reg[0]=val
            self.snd1.sweep_shift=val&0x7
            self.snd1.sweep_direction=-1 if (val&0x8) else 1
            self.snd1.sweep_time=(val&0x70)>>4
            if (old&0x08) and not (val&0x08) and self.snd1.sweep_neg_mode_used:
                self.snd1.on=0
        elif offset == NR11:
            self.snd1.reg[1]=val
            if self.ctrl_on: self.snd1.duty=(val&0xc0)>>6
            self.snd1.length=val&0x3f; self.snd1.length_counting=1
        elif offset == NR12:
            self.snd1.reg[2]=val
            self.snd1.envelope_value=val>>4
            self.snd1.envelope_direction=1 if (val&0x8) else -1
            self.snd1.envelope_time=val&0x07
            if not self.dac_enabled(self.snd1): self.snd1.on=0
        elif offset == NR13:
            self.snd1.reg[3]=val
            if not self.snd1.sweep_enabled:
                self.snd1.frequency=((self.snd1.reg[4]&0x7)<<8)|self.snd1.reg[3]
                self.snd1.distance=0x800-self.snd1.frequency
        elif offset == NR14:
            lwe=self.snd1.length_enabled
            self.snd1.reg[4]=val
            self.snd1.length_enabled=1 if (val&0x40) else 0
            self.snd1.frequency=((self.regs[NR14]&0x7)<<8)|self.snd1.reg[3]
            self.snd1.distance=0x800-self.snd1.frequency
            if not lwe and not (self.cycles & 0x1FFF) and self.snd1.length_counting:
                if self.snd1.length_enabled: self.tick_length(self.snd1)
            if val&0x80:
                self.snd1.on=1; self.snd1.envelope_enabled=1
                self.snd1.envelope_value=self.snd1.reg[2]>>4
                self.snd1.envelope_count=self.snd1.envelope_time
                self.snd1.sweep_count=self.snd1.sweep_time
                self.snd1.sweep_neg_mode_used=0; self.snd1.signal=0
                self.snd1.length_counting=1
                self.snd1.frequency=((self.snd1.reg[4]&0x7)<<8)|self.snd1.reg[3]
                self.snd1.distance=0x800-self.snd1.frequency
                self.snd1.cycles_left=0; self.snd1.duty_count=0
                self.snd1.frequency_counter=self.snd1.frequency
                self.snd1.sweep_enabled = (self.snd1.sweep_shift!=0) or (self.snd1.sweep_time!=0)
                if not self.dac_enabled(self.snd1): self.snd1.on=0
                if self.snd1.sweep_shift>0: self.calculate_next_sweep(self.snd1)
                if self.snd1.length==0 and self.snd1.length_enabled and not (self.cycles & 0x1FFF):
                    self.tick_length(self.snd1)
            else:
                if not self.snd1.sweep_enabled:
                    self.snd1.frequency=((self.snd1.reg[4]&0x7)<<8)|self.snd1.reg[3]
                    self.snd1.distance=0x800-self.snd1.frequency
        elif offset == NR21:
            self.snd2.reg[1]=val
            if self.ctrl_on: self.snd2.duty=(val&0xc0)>>6
            self.snd2.length=val&0x3f; self.snd2.length_counting=1
        elif offset == NR22:
            self.snd2.reg[2]=val
            self.snd2.envelope_value=val>>4
            self.snd2.envelope_direction=1 if (val&0x8) else -1
            self.snd2.envelope_time=val&0x07
            if not self.dac_enabled(self.snd2): self.snd2.on=0
        elif offset == NR23:
            self.snd2.reg[3]=val
            self.snd2.frequency=((self.snd2.reg[4]&0x7)<<8)|self.snd2.reg[3]
            self.snd2.distance=0x800-self.snd2.frequency
        elif offset == NR24:
            lwe=self.snd2.length_enabled
            self.snd2.reg[4]=val
            self.snd2.length_enabled=1 if (val&0x40) else 0
            self.snd2.frequency=((self.snd2.reg[4]&0x7)<<8)|self.snd2.reg[3]
            self.snd2.distance=0x800-self.snd2.frequency
            if not lwe and not (self.cycles & 0x1FFF) and self.snd2.length_counting:
                if self.snd2.length_enabled: self.tick_length(self.snd2)
            if val&0x80:
                self.snd2.on=1; self.snd2.envelope_enabled=1
                self.snd2.envelope_value=self.snd2.reg[2]>>4
                self.snd2.envelope_count=self.snd2.envelope_time
                self.snd2.frequency=((self.snd2.reg[4]&0x7)<<8)|self.snd2.reg[3]
                self.snd2.distance=0x800-self.snd2.frequency
                self.snd2.cycles_left=0; self.snd2.duty_count=0; self.snd2.signal=0
                self.snd2.frequency_counter=self.snd2.frequency
                self.snd2.length_counting=1
                if not self.dac_enabled(self.snd2): self.snd2.on=0
                if self.snd2.length==0 and self.snd2.length_enabled and not (self.cycles & 0x1FFF):
                    self.tick_length(self.snd2)
            else:
                self.snd2.frequency=((self.snd2.reg[4]&0x7)<<8)|self.snd2.reg[3]
                self.snd2.distance=0x800-self.snd2.frequency
        elif offset == NR30:
            self.snd3.reg[0]=val
            if not self.dac_enabled(self.snd3): self.snd3.on=0
        elif offset == NR31:
            self.snd3.reg[1]=val
            self.snd3.length=val&0xff; self.snd3.length_counting=1
        elif offset == NR32:
            self.snd3.reg[2]=val
            self.snd3.level=(val>>5)&0x3
        elif offset == NR33:
            self.snd3.reg[3]=val
            self.snd3.frequency=((self.snd3.reg[4]&0x7)<<8)|self.snd3.reg[3]
            self.snd3.distance=0x800-self.snd3.frequency
        elif offset == NR34:
            lwe=self.snd3.length_enabled
            self.snd3.reg[4]=val
            self.snd3.length_enabled=1 if (val&0x40) else 0
            self.snd3.frequency=((self.snd3.reg[4]&0x7)<<8)|self.snd3.reg[3]
            self.snd3.distance=0x800-self.snd3.frequency
            if not lwe and not (self.cycles & 0x1FFF) and self.snd3.length_counting:
                if self.snd3.length_enabled: self.tick_length(self.snd3)
            if val&0x80:
                self.snd3.on=1
                self.snd3.frequency=((self.snd3.reg[4]&0x7)<<8)|self.snd3.reg[3]
                self.snd3.distance=0x800-self.snd3.frequency
                self.snd3.cycles_left=-6
                self.snd3.offset=0
                self.snd3.signal=0
                self.snd3.length_counting=1
                if not self.dac_enabled(self.snd3): self.snd3.on=0
                if self.snd3.length==0 and self.snd3.length_enabled and not (self.cycles & 0x1FFF):
                    self.tick_length(self.snd3)
            else:
                self.snd3.frequency=((self.snd3.reg[4]&0x7)<<8)|self.snd3.reg[3]
                self.snd3.distance=0x800-self.snd3.frequency
        elif offset == NR41:
            self.snd4.reg[1]=val
            self.snd4.length=val&0x3f; self.snd4.length_counting=1
        elif offset == NR42:
            self.snd4.reg[2]=val
            self.snd4.envelope_value=val>>4
            self.snd4.envelope_direction=1 if (val&0x8) else -1
            self.snd4.envelope_time=val&0x07
            if not self.dac_enabled(self.snd4): self.snd4.on=0
        elif offset == NR43:
            self.snd4.reg[3]=val
            self.snd4.noise_short = 1 if (val&0x08) else 0
        elif offset == NR44:
            lwe=self.snd4.length_enabled
            self.snd4.reg[4]=val
            self.snd4.length_enabled=1 if (val&0x40) else 0
            if not lwe and not (self.cycles & 0x1FFF) and self.snd4.length_counting:
                if self.snd4.length_enabled: self.tick_length(self.snd4)
            if val&0x80:
                self.snd4.on=1; self.snd4.envelope_enabled=1
                self.snd4.envelope_value=self.snd4.reg[2]>>4
                self.snd4.envelope_count=self.snd4.envelope_time
                self.snd4.noise_rng=0x7FFF
                self.snd4.cycles_left=0; self.snd4.signal=-1
                self.snd4.length_counting=1
                if not self.dac_enabled(self.snd4): self.snd4.on=0
                if self.snd4.length==0 and self.snd4.length_enabled and not (self.cycles & 0x1FFF):
                    self.tick_length(self.snd4)
        elif offset == NR50:
            self.vol_left=val&0x7
            self.vol_right=(val&0x70)>>4
        elif offset == NR51:
            self.mode1_right=val&0x1;  self.mode1_left=(val&0x10)>>4
            self.mode2_right=(val&0x2)>>1; self.mode2_left=(val&0x20)>>5
            self.mode3_right=(val&0x4)>>2; self.mode3_left=(val&0x40)>>6
            self.mode4_right=(val&0x8)>>3; self.mode4_left=(val&0x80)>>7
        elif offset == NR52:
            if not (val&0x80):
                self.snd1.on=0; self.snd2.on=0; self.snd3.on=0; self.snd4.on=0
            else:
                if not self.ctrl_on:
                    self.cycles = mask32(self.cycles | (7 * FRAME_CYCLES))
            self.ctrl_on = 1 if (val&0x80) else 0
            self.regs[NR52] = val & 0x80

    def wr(self, reg, val):
        if AUD3W0 <= reg <= AUD3W0+0x0F:
            self.regs[reg]=val; return
        if not self.ctrl_on and reg not in (NR52,NR11,NR21,NR31,NR41):
            return
        self.sound_w_internal(reg, val)

    def render(self):
        self.base_count = mask32(self.base_count + GB_BASE_INCR)
        incr = self.base_count >> GB_GETA_BITS
        self.base_count &= (1 << GB_GETA_BITS) - 1
        if incr > 0: self.update_state(incr)

        left = 0
        right = 0
        if self.snd1.on:
            sample = self.snd1.signal * self.snd1.envelope_value
            if self.mode1_left:  left  += sample
            if self.mode1_right: right += sample
        if self.snd2.on:
            sample = self.snd2.signal * self.snd2.envelope_value
            if self.mode2_left:  left  += sample
            if self.mode2_right: right += sample
        if self.snd3.on:
            sample = self.snd3.signal
            if self.mode3_left:  left  += sample
            if self.mode3_right: right += sample
        if self.snd4.on:
            sample = self.snd4.signal * self.snd4.envelope_value
            if self.mode4_left:  left  += sample
            if self.mode4_right: right += sample
        # 对齐 gb.c: max(|left|,|right|) 保留符号, vol_avg, >>3 衰减
        if left < 0:
            mono = left if -left >= right else right
        else:
            mono = left if left >= right else right
        vol_avg = (self.vol_left + self.vol_right + 1) // 2
        mono *= vol_avg
        mono >>= 3
        if mono > 2047: mono = 2047
        if mono < -2048: mono = -2048
        return mono

# ========== VGM 解析 + 仿真驱动 ==========
def load_vgm(path):
    raw = open(path,'rb').read()
    if path.lower().endswith('.vgz') or raw[:4] != b'Vgm ':
        raw = gzip.decompress(raw)
    return raw

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('vgm')
    ap.add_argument('--max-samples', type=int, default=8000)
    ap.add_argument('--trace-cmds', type=int, default=40)
    ap.add_argument('--print-every', type=int, default=200)
    args = ap.parse_args()

    data = load_vgm(args.vgm)
    gb_clk = struct.unpack_from('<I', data, 0x80)[0]
    data_off = 0x34 + struct.unpack_from('<I', data, 0x34)[0]
    end = struct.unpack_from('<I', data, 0x04)[0] + 0x04 if False else len(data)
    eof_off = struct.unpack_from('<I', data, 0x04)[0]
    # Eofoff 是相对文件 0 的偏移
    print(f"GB clock: {gb_clk}  data_off: {data_off}  file_len: {len(data)}")
    print(f"GB_BASE_INCR = {GB_BASE_INCR} (0x{GB_BASE_INCR:X})")
    print(f"  → cycles per sample ~ {GB_BASE_INCR >> GB_GETA_BITS}")
    print()

    gb = GB()
    pos = data_off
    samples_rendered = 0
    samples_budget = 0.0
    cmds_done = 0
    trace = []

    # === 第一阶段: 打印前 N 条命令, 看 NR52 开电源后 cycles 状态 ===
    print(f"=== 前 {args.trace_cmds} 条命令仿真 (含 cycles 状态) ===")
    scan_pos = pos
    for _ in range(args.trace_cmds):
        if scan_pos >= len(data): break
        b = data[scan_pos]
        if b == 0x66:
            print(f"  @{scan_pos}: END"); break
        elif b == 0xB3:
            r, d = data[scan_pos+1], data[scan_pos+2]
            gb.wr(r, d)
            tag = ""
            if r == NR52:
                tag = f"  ← NR52 power {'on' if d&0x80 else 'off'}: cycles now = {gb.cycles} (0x{gb.cycles:X})"
            print(f"  @{scan_pos}: B3 reg={r:02X} data={d:02X}{tag}")
            scan_pos += 3
        elif b == 0x61:
            n = struct.unpack_from('<H', data, scan_pos+1)[0]
            print(f"  @{scan_pos}: WAIT {n}")
            scan_pos += 3
        elif b == 0x62: print(f"  @{scan_pos}: WAIT 735"); scan_pos += 1
        elif 0x70 <= b <= 0x8F:
            print(f"  @{scan_pos}: WAIT {b&0xF}"); scan_pos += 1
        else:
            print(f"  @{scan_pos}: cmd {b:02X}"); scan_pos += 1

    # === 第二阶段: 从头跑 N 个采样, 看 gb_render() 输出 ===
    # 驱动模型: 用 samples_to_wait 表示"还要等多少个 sample 才能处理下一条命令"
    # 每次迭代 = 1 个 sample. 若 samples_to_wait > 0, 则只 render 不消费命令.
    print(f"\n=== 渲染前 {args.max_samples} 个采样, 每 {args.print_every} 打印一次状态 ===")
    gb.gb_init()   # 重置
    pos = data_off
    samples_to_wait = 0   # 还要等多少 sample 才处理下一条命令
    nonzero_count = 0
    max_abs = 0
    sum_abs = 0
    last_cmds = []        # 本 sample 处理的命令 (用于追踪)

    while samples_rendered < args.max_samples:
        # 处理本 sample: 如果还在 wait, 跳过命令消费; 否则消费所有 0-wait 命令
        if samples_to_wait > 0:
            samples_to_wait -= 1
        else:
            this_sample_cmds = []
            while pos < len(data):
                b = data[pos]
                if b == 0x66:
                    pos = len(data); break
                elif b == 0xB3:
                    gb.wr(data[pos+1], data[pos+2])
                    this_sample_cmds.append(f'B3 r={data[pos+1]:02X} d={data[pos+2]:02X}')
                    pos += 3
                elif b == 0x61:
                    n = struct.unpack_from('<H', data, pos+1)[0]
                    pos += 3
                    if n > 0:
                        samples_to_wait = n - 1   # 本 sample 已用掉一个
                        break
                elif b == 0x62:
                    pos += 1; samples_to_wait = 735 - 1; break
                elif b == 0x63:
                    pos += 1; samples_to_wait = 882 - 1; break
                elif 0x70 <= b <= 0x8F:
                    n = (b & 0xF) + 1
                    pos += 1
                    if n > 0:
                        samples_to_wait = n - 1
                        break
                elif b == 0xD2: pos += 4
                else: pos += 1
            if this_sample_cmds:
                last_cmds = this_sample_cmds
        if pos >= len(data): break

        out = gb.render()
        samples_rendered += 1
        if out != 0:
            nonzero_count += 1
        a = abs(out); 
        if a > max_abs: max_abs = a
        sum_abs += a

        if samples_rendered % args.print_every == 0 or samples_rendered == 1:
            cmd_str = ' '.join(last_cmds[-2:]) if last_cmds else ''
            print(f"  sample {samples_rendered:5d}: render={out:6d} | "
                  f"s1(on={gb.snd1.on} sig={gb.snd1.signal:+d} env={gb.snd1.envelope_value:+d}) "
                  f"s2(on={gb.snd2.on} sig={gb.snd2.signal:+d}) "
                  f"s3(on={gb.snd3.on} sig={gb.snd3.signal:+d}) "
                  f"s4(on={gb.snd4.on}) | cycles={gb.cycles} step={(gb.cycles//FRAME_CYCLES)&7}"
                  + (f"  cmd:{cmd_str}" if cmd_str else ""))

    print(f"\n=== 统计 (前 {samples_rendered} 采样, 约 {samples_rendered/SAMPLE_RATE:.2f}s) ===")
    print(f"  非零输出采样数: {nonzero_count} / {samples_rendered}  ({100*nonzero_count/samples_rendered:.1f}%)")
    print(f"  最大幅度:       {max_abs}")
    print(f"  平均幅度:       {sum_abs/samples_rendered:.2f}")
    print(f"  cycles 累计:    {gb.cycles} (= {gb.cycles/FRAME_CYCLES:.1f} frame periods)")
    print(f"  最终各通道: snd1.on={gb.snd1.on} snd2.on={gb.snd2.on} snd3.on={gb.snd3.on} snd4.on={gb.snd4.on}")

if __name__ == '__main__':
    main()
