#!/usr/bin/env python3
"""算 harpsichord 各包络阶段的实际时间, 对照 emu.

fw (round-robin 16采样/tick):
  AR: level 0->31, 每 tick (16采样) 走一步, cnt=AR_TAB[ar] 控制速度
      时间 = 31步 × AR_TAB[ar] × 16采样 / 22050
  DR: level 31->sul, 每步 cnt=DR_TAB[dr]
      时间 = (31-sul)步 × DR_TAB[dr] × 16 / 22050
  RR(keyoff): level ->0, cnt=RR_TAB[rr] 或 RR_TAB[5]
      时间 = level步 × RR × 16 / 22050
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fw_real_sim import (fw_decode, FW_AR_TAB, FW_DR_TAB, FW_RR_TAB)
from ym2413_wav_gen import DEFAULT_INST

dump = DEFAULT_INST[11]
p = fw_decode(dump)
ISR = 22050

def fw_stage_time(steps, cnt_tab_val, label):
    """round-robin: 每步 = cnt_tab_val × 16 采样 / ISR"""
    if cnt_tab_val == 0: return 0  # 瞬间
    return steps * cnt_tab_val * 16 / ISR * 1000  # ms

print(f"=== harpsichord 包络参数 ===")
print(f"mod: ar={p['mod_ar']} dr={p['mod_dr']} sl={p['mod_sl']} rr={p['mod_rr']} eg={p['mod_eg']}")
print(f"car: ar={p['car_ar']} dr={p['car_dr']} sl={p['car_sl']} rr={p['car_rr']} eg={p['car_eg']}")
print(f"\nAR_TAB={[0,116,58,29,14,7,4,2,1,1,1,1,1,1,1,1]}")
print(f"DR_TAB={[0,255,255,175,88,44,22,11,6,3,1,1,1,1,1,1]}")
print(f"RR_TAB={[0,255,255,255,170,85,42,21,11,5,3,1,1,1,1,1]}")

print(f"\n=== carrier 包络各阶段时间 (fw, round-robin 16采样/tick) ===")
# key_on: atk<=2 瞬间到顶 (AR>=7), 否则 attack
car_ar = p['car_ar']
car_atk = FW_AR_TAB[car_ar]
print(f"\ncar AR={car_ar} -> AR_TAB={car_atk}")
if car_atk <= 2:
    print(f"  atk<=2 -> 瞬间到顶 (attack≈0ms)")
    car_attack_ms = 0
else:
    car_attack_ms = fw_stage_time(31, car_atk, "AR")
    print(f"  attack: 31步 × {car_atk} × 16 / {ISR} = {car_attack_ms:.1f}ms")

car_dr = p['car_dr']
car_dec = FW_DR_TAB[car_dr]
car_sl = p['car_sl']
car_sul = 0 if car_sl >= 15 else (31 - car_sl * 2)
print(f"\ncar DR={car_dr} -> DR_TAB={car_dec}, SL={car_sl} -> sul={car_sul}")
car_decay_steps = 31 - car_sul
if car_sul >= 31:
    print(f"  sul=31 -> decay 不降! (31->31, 0步)")
    car_decay_ms = 0
else:
    car_decay_ms = fw_stage_time(car_decay_steps, car_dec, "DR")
    print(f"  decay: {car_decay_steps}步 × {car_dec} × 16 / {ISR} = {car_decay_ms:.1f}ms")

# sustain: EG=1 保持, EG=0 继续降
car_eg = p['car_eg']
print(f"\ncar EG={car_eg} ({'sustaining: 保持 sul' if car_eg else 'non-sustaining: 继续降'})")
if car_eg == 0:  # non-sustaining, 继续用 rel 降
    car_rel = FW_RR_TAB[p['car_rr']]
    print(f"  sustain 阶段继续降: RR_TAB[{p['car_rr']}]={car_rel}, 从 sul={car_sul} 到 0")
    car_sus_ms = fw_stage_time(car_sul, car_rel, "SUS")
    print(f"  sustain->0: {car_sul}步 × {car_rel} × 16 / {ISR} = {car_sus_ms:.1f}ms")

# release (keyoff): sus_flag? RR_TAB[5] : RR_TAB[rr]
print(f"\ncar keyoff release:")
car_rr5 = FW_RR_TAB[5]
car_rr = FW_RR_TAB[p['car_rr']]
print(f"  sus_flag=0 -> 用 RR_TAB[{p['car_rr']}]={car_rr}")
print(f"  从当前 level (假设=sul={car_sul}) 到 0: {car_sul}步 × {car_rr} × 16 / {ISR} = {fw_stage_time(car_sul, car_rr, 'REL'):.1f}ms")

print(f"\n=== emu 参考 (实测包络) ===")
print(f"  attack: ≈0ms (瞬间)")
print(f"  -6dB: 220ms")
print(f"  -20dB: 740ms")
print(f"  keyoff->0: ≈100ms")

print(f"\n=== 偏差总结 ===")
print(f"  fw car decay: sul={car_sul} (SL={car_sl}), {'不衰减!' if car_sul>=31 else f'{car_decay_ms:.0f}ms'}")
print(f"  emu -6dB@220ms 需要 decay 显著, fw sul={car_sul} 导致{'几乎不衰减' if car_sul>=31 else '衰减'}")
