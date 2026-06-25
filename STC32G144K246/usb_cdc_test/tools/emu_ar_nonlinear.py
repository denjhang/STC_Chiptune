#!/usr/bin/env python3
"""研究 emu attack 非线性: eg_out = eg_out - (eg_out>>s) - 1, 反推 fw ar_hold 表.

emu attack: eg_out 127->0 (递减), 输出指数上升
  eg_out -= (eg_out >> s) + 1   (s 越大前期越快)
fw attack: level 0->31 (递增), 输出线性
  要拟合 emu: level 上升前期快(低level大步进), 后期慢(高level小步进)

方法: 抓 emu 各 AR 的 eg_out 曲线, 映射成 fw level 序列, 反推 ar_hold[level]
ar_hold[level] = 该 level 停留几个 tick (低level hold小=快升, 高level hold大=慢升)
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ym2413_wav_gen import (DEFAULT_INST, dump_to_patch, freq_to_fnum_blk,
                            EmuChannel, calc_envelope, calc_phase,
                            calc_slot_mod, calc_slot_car, EG_MUTE, INTERNAL_RATE)

def emu_attack_curve(ar_val):
    """抓 emu carrier AR=ar_val 的 eg_out 曲线 (127->0)"""
    mp, cp = dump_to_patch(DEFAULT_INST[1])  # violin 基础
    cp.AR = ar_val; cp.EG = 1; cp.SL = 15; cp.DR = 0
    ch = EmuChannel(mp, cp)
    fn, bl = freq_to_fnum_blk(440.0)
    ch.set_note(fn, bl); ch.set_volume(0); ch.set_sus(0); ch.key_on()
    from ym2413_wav_gen import am_table
    eg_seq = []
    for i in range(int(0.3*INTERNAL_RATE)):
        ch.pm_phase=(ch.pm_phase+1)&0xffffffff; ch.am_phase+=1
        ch.lfo_am=am_table[(ch.am_phase>>6)%len(am_table)]
        ch.eg_counter+=1
        calc_envelope(ch.car, ch.eg_counter); calc_phase(ch.car, ch.pm_phase)
        eg_seq.append(ch.car.eg_out)
    return eg_seq

# eg_out 127=静音, 0=最大. 输出比例 = 2^(-eg_out/某常数)
# emu to_linear: att=(eg_out+tll)<<4, 但 tll=0 时输出 = lookup_exp_table(eg_out<<4)
# 简化: 输出 ∝ 2^(-eg_out/某常数), eg_out=0 -> 1.0, eg_out=127 -> ~0
# fw level 输出 ∝ (level+1)/32. 要输出比例相同: level = 32×ratio - 1

print("=== emu attack eg_out 曲线 (AR=6, flute 用) ===")
eg = emu_attack_curve(6)
# 找 attack 完成
t_end = next((i for i,e in enumerate(eg) if e < 2), len(eg))
print(f"attack 完成于 {t_end/INTERNAL_RATE*1000:.0f}ms ({t_end} 采样)")
print(f"\nemu tick = 16采样, fw tick = 16采样@22050")
print(f"emu @49716, fw @22050, fw tick 慢 {INTERNAL_RATE/22050:.2f}x")

# 把 eg_out 曲线转成输出比例, 再映射 fw level
# 每 fw tick (16采样@22050 = 0.726ms) 对应 emu 的 0.726×49716/22050 = 1.64ms = ~81 采样
emu_per_fw = INTERNAL_RATE/22050  # 2.255
print(f"\nemu 采样/fw tick = {emu_per_fw*16:.0f}")

# 抓 fw tick 对应的 emu eg_out, 转输出比例 -> fw level
print(f"\n{'fw_tick':>6} {'emu_eg':>7} {'ratio':>7} {'fw_level':>9}")
level_seq = []
for ft in range(0, 50):
    emu_samp = int(ft * 16 * emu_per_fw)
    if emu_samp >= len(eg): break
    eg_out = eg[emu_samp]
    # 输出比例: eg_out=0 -> 1.0, 127 -> 0. 近似 ratio = 2^(-eg_out/64)
    ratio = 2**(-eg_out/64.0)
    fw_lvl = round(32 * ratio - 1)
    fw_lvl = max(0, min(31, fw_lvl))
    level_seq.append(fw_lvl)
    if ft < 20:
        print(f"{ft:>6} {eg_out:>7} {ratio:>7.3f} {fw_lvl:>9}")

# 看 level 序列形态 (前期快增, 后期慢增)
print(f"\nlevel 序列: {level_seq[:30]}")
# ar_hold[level]: level n -> n+1 停留几个 tick
# 从序列找: level 值 n 首次出现到 n+1 首次出现的 tick 差
ar_hold = [0]*32
for n in range(31):
    # 找 n 首次出现
    try:
        i0 = level_seq.index(n)
        i1 = level_seq.index(n+1, i0)
        ar_hold[n] = i1 - i0
    except ValueError:
        ar_hold[n] = 99  # 未出现
print(f"\nar_hold[0~15] (从 level 序列反推): {ar_hold[:16]}")
print(f"(低 level hold 小=快升, 高 level hold 大=慢升, 指数形态)")
