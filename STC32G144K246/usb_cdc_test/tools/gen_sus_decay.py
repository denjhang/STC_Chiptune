#!/usr/bin/env python3
"""从 emu SUSTAIN(RR=4) eg_out 曲线反推 sus_decay[32] 查表.

emu: SUSTAIN 阶段 eg_out 线性递增, 输出 ∝ 2^(-eg_out/某常数) 指数衰减.
fw : level 线性控制输出. 要让输出指数衰减, level 必须指数递减.

方法:
1. 抓 emu harpsichord SUSTAIN 阶段每个 tick 的 eg_out
2. 每个轮 round-robin tick (16采样) 对应 fw 一次 level 步进
3. 把 emu 输出比例 映射到 fw level (level = round(31 × 输出比例))
4. sus_decay[当前level] = 下一个level
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ym2413_wav_gen import (DEFAULT_INST, dump_to_patch, freq_to_fnum_blk,
                            EmuChannel, calc_envelope, calc_phase, calc_slot_mod,
                            calc_slot_car, to_linear, EG_MUTE, INTERNAL_RATE)

# 抓 emu harpsichord SUSTAIN 阶段 car 输出序列
mp, cp = dump_to_patch(DEFAULT_INST[11])
ch = EmuChannel(mp, cp)
fn, bl = freq_to_fnum_blk(440.0)
ch.set_note(fn, bl); ch.set_volume(0); ch.set_sus(0); ch.key_on()
from ym2413_wav_gen import am_table
outs = []
n = int(1.5*INTERNAL_RATE)  # 抓 1.5s (keyon 全程)
for i in range(n):
    ch.pm_phase = (ch.pm_phase+1)&0xffffffff
    ch.am_phase += 1
    ch.lfo_am = am_table[(ch.am_phase>>6)%len(am_table)]
    ch.eg_counter += 1
    calc_envelope(ch.mod, ch.eg_counter); calc_phase(ch.mod, ch.pm_phase)
    calc_envelope(ch.car, ch.eg_counter); calc_phase(ch.car, ch.pm_phase)
    mo = calc_slot_mod(ch.mod, ch.lfo_am)
    co = calc_slot_car(ch.car, mo, ch.lfo_am)
    outs.append(co)

# car 输出的包络: 取绝对值, 看衰减
# emu 输出有正负(halfsin+-(co>>1)), 取 |co| 的上包络
# 用短时 RMS 看衰减形态
seg = int(INTERNAL_RATE*0.01)  # 10ms
rms_seq = []
for i in range(0, len(outs)-seg, seg):
    s = outs[i:i+seg]
    rms_seq.append((sum(x*x for x in s)/len(s))**0.5)

peak = max(rms_seq)
print(f"emu harpsichord car 输出 RMS 衰减 (10ms段, 归一化):")
for i, r in enumerate(rms_seq[:60]):
    ms = i*10
    db = 20*math.log10(r/peak) if r>0 else -99
    if ms % 50 == 0:
        print(f"  {ms:>4}ms {db:>+6.1f}dB  ratio={r/peak:.3f}")

# 现在反推 sus_decay 表:
# fw level 0~31, 输出 ∝ level+1 (线性)
# emu 输出 ratio (0~1, 相对峰值)
# 要让 fw 在 SUSTAIN 阶段每个 tick 输出 = emu 对应时刻输出
# fw level = round((level_peak) × ratio)  -- 但 fw level 峰值=31
# sus_decay[n] = 下一个 level (比 n 小)
#
# emu 每 round-robin tick (16采样@49716 ≈ 0.32ms) 衰减一点
# 但 fw round-robin 是 16采样@22050 ≈ 0.73ms
# 速率不同! emu 49716/16 = 3107 tick/s, fw 22050/16 = 1378 tick/s
# fw tick 比 emu 慢 2.255x, 所以 fw 每个 tick 要衰减 emu 的 2.255 个 tick 的量

print(f"\n=== 反推 sus_decay[32] ===")
print(f"emu tick=16/{INTERNAL_RATE:.0f}={16/INTERNAL_RATE*1000:.2f}ms")
print(f"fw  tick=16/22050=0.73ms")
print(f"fw 慢 {INTERNAL_RATE/22050:.2f}x, 每个 fw tick 对应 {INTERNAL_RATE/22050:.2f} 个 emu tick")

# 简化: 直接从 emu RMS 曲线采样 fw 的 level 序列
# fw SUSTAIN 从 level=31 开始, 每个 fw tick 降一次
# fw tick 间隔 0.73ms, 对应 emu 的 0.73ms 时刻的 ratio
# level[i] = round(31 × ratio_at(i × 0.73ms))
emu_per_fw = INTERNAL_RATE/22050  # 2.255
# 用 outs (逐采样) 直接算, 每 16 emu采样 = 1 emu tick, fw tick = emu_per_fw 个 emu tick
# fw 第 i 个 tick 对应 emu 第 i×emu_per_fw×16 采样
level_seq = [31]
for i in range(1, 100):
    emu_samp = int(i * emu_per_fw * 16)
    if emu_samp >= len(outs): break
    # 取该时刻短时 RMS ratio
    s_start = max(0, emu_samp - 80)
    s = outs[s_start:emu_samp+80]
    r = (sum(x*x for x in s)/len(s))**0.5 if s else 0
    ratio = r / peak
    lvl = round(31 * ratio)
    level_seq.append(max(0, lvl))

print(f"\nfw level 序列 (前 {len(level_seq)} 步):")
print(f"  {level_seq}")

# 构造 sus_decay[32]: sus_decay[n] = level 序列中 n 的下一个值
# 但 level 序列可能有重复/跳跃, 需要规整
# 对每个 level 值 0~31, 找它在序列中首次出现后的下一个更小值
sus_decay = list(range(32))  # 默认不变
for n in range(32):
    # 在 level_seq 找 n, 取下一个
    for j in range(len(level_seq)-1):
        if level_seq[j] == n and level_seq[j+1] < n:
            sus_decay[n] = level_seq[j+1]
            break
    # 如果找不到(序列跳过 n), 用线性插值: 找比 n 小的最近定义
# 修正: 确保单调递减且到 0
for n in range(1, 32):
    if sus_decay[n] >= n:  # 没找到, 用上一级推导
        sus_decay[n] = max(0, sus_decay[n-1] - 1) if n > 0 else 0

print(f"\nsus_decay[32] = {sus_decay}")
print(f"(sus_decay[n] = level n 下一步应变成的值)")
# 保存供验证脚本用
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sus_decay_gen.txt'), 'w') as f:
    f.write(str(sus_decay))
