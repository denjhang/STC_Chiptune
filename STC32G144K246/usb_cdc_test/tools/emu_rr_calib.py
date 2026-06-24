#!/usr/bin/env python3
"""测 emu 各 RR 档位 carrier 的真实衰减时间, 反推正确的 RR_TAB.

emu carrier (SL=0, EG=0): attack 后 eg_out≈0, sustain 阶段用 RR 速率
递增到 127. 测 eg_out 从 ~0 到 127 的全程时间 (各 RR 0~15).

fw 对应: level 从 31 降到 0, round-robin 16采样/tick,
  时间 = 31步 × RR_TAB[rr] × 16 / 22050
  => 正确 RR_TAB[rr] = emu全程ms × 22050 / (31 × 16 × 1000)
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ym2413_wav_gen import (DEFAULT_INST, dump_to_patch, freq_to_fnum_blk,
                            EmuChannel, calc_envelope, calc_phase,
                            calc_slot_mod, calc_slot_car, EG_MUTE, INTERNAL_RATE)
from fw_real_sim import FW_RR_TAB

ISR = 22050
FREQ = 440.0

def measure_emu_rr(rr_val):
    """构造一个 RR=rr_val 的 patch, 测 carrier attack 后 eg_out 0->127 时间."""
    # 用 harpsichord 基础改 RR
    mp, cp = dump_to_patch(DEFAULT_INST[11])
    cp.RR = rr_val
    cp.EG = 0  # non-sustaining, sustain 用 RR
    cp.SL = 0  # decay 瞬间跳过
    ch = EmuChannel(mp, cp)
    fn, bl = freq_to_fnum_blk(FREQ)
    ch.set_note(fn, bl); ch.set_volume(0); ch.set_sus(0); ch.key_on()
    from ym2413_wav_gen import am_table
    eg_seq = []
    n = int(2.0 * INTERNAL_RATE)  # 最多测 2s
    for i in range(n):
        ch.pm_phase = (ch.pm_phase + 1) & 0xffffffff
        ch.am_phase += 1
        ch.lfo_am = am_table[(ch.am_phase >> 6) % len(am_table)]
        ch.eg_counter += 1
        calc_envelope(ch.car, ch.eg_counter)
        eg_seq.append(ch.car.eg_out)
    # 找 attack 完成 (eg_out 第一次到最小) 和 eg_out 到 127 的时间
    eg_min = min(eg_seq)
    t_attack = next(i for i, e in enumerate(eg_seq) if e <= eg_min + 1)
    # 到 126 (近静音)
    try:
        t_end = next(i for i in range(t_attack, len(eg_seq)) if eg_seq[i] >= 126)
    except StopIteration:
        t_end = len(eg_seq) - 1
    ms_attack = t_attack / INTERNAL_RATE * 1000
    ms_decay = (t_end - t_attack) / INTERNAL_RATE * 1000
    return ms_attack, ms_decay

print(f"=== emu RR 档位衰减时间实测 + RR_TAB 反推 ===")
print(f"方法: carrier SL=0/EG=0/RR=n, 测 attack 后 eg_out 0->126 时间\n")
print(f"{'RR':>3} {'emu_decay_ms':>13} {'反推RR_TAB':>11} {'现RR_TAB':>9} {'倍数':>6}")
print("-" * 50)
new_rr = [0]*16
for rr in range(16):
    if rr == 0:
        print(f"{rr:>3} {'∞(step=0)':>13} {'0':>11} {FW_RR_TAB[rr]:>9}")
        new_rr[rr] = 0
        continue
    ma, md = measure_emu_rr(rr)
    # fw: 31步 × cnt × 16 / 22050 = md ms  =>  cnt = md × 22050 / (31×16×1000)
    if md >= 1900:  # 超时, 太慢
        cnt = 255
    else:
        cnt = md * ISR / (31 * 16 * 1000)
        cnt = max(1, min(255, int(round(cnt))))
    old = FW_RR_TAB[rr]
    ratio = old / cnt if cnt > 0 else 0
    mark = " <==" if abs(ratio - 1.0) > 0.3 else ""
    print(f"{rr:>3} {md:>13.1f} {cnt:>11} {old:>9} {ratio:>6.2f}{mark}")
    new_rr[rr] = cnt

print(f"\n现 RR_TAB = {FW_RR_TAB}")
print(f"新 RR_TAB = {new_rr}")
print(f"\nharpsichord RR=4: 现={FW_RR_TAB[4]}, 反推={new_rr[4]}")
