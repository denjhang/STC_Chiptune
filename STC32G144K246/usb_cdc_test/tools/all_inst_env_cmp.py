#!/usr/bin/env python3
"""全 15 乐器包络对比: 定位各乐器偏差.

每个乐器算:
- keyon 衰减 @500ms (dB, 归一化峰值)
- keyoff->-40dB 时间
对照 emu, 看哪些乐器偏差大.
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fw_real_sim as F
from fw_real_sim import render_fw_real, FW_ISR_RATE, fw_decode
from ym2413_wav_gen import (DEFAULT_INST, NAMES, render_emu2413, INTERNAL_RATE)

FREQ = 440.0
DUR_KO, DUR_KF = 1.0, 1.0

def curve(s, sr, ms=50):
    seg = int(sr*ms/1000)
    return [(i*1000/sr, (sum(x*x for x in s[i:i+seg])/max(len(s[i:i+seg]),1))**0.5) for i in range(0,len(s),seg) if s[i:i+seg]]

def db_at(curve_, peak, ms):
    for t,r in curve_:
        if abs(t-ms) < 30:
            return 20*math.log10(r/peak) if r>0 else -99
    return -99

def keyoff_to_db(curve_, peak, target_db, keyoff_ms=1000):
    target = peak * 10**(target_db/20)
    for t,r in curve_:
        if t >= keyoff_ms and r <= target:
            return t - keyoff_ms
    return 9999

print(f"=== 全 15 乐器包络对比 (440Hz, 1s+1s) ===\n")
print(f"{'#':>2} {'Name':<14} {'ar':>2}{'dr':>2}{'sl':>2}{'rr':>2}{'eg':>2} | {'emu@500':>8} {'fw@500':>8} {'diff':>6} | {'emu_ko':>7} {'fw_ko':>7}")
print("-" * 85)
results = []
for i in range(1, 16):
    p = fw_decode(DEFAULT_INST[i])
    emu = render_emu2413(i, FREQ, DUR_KO, DUR_KF, 0)
    fw = render_fw_real(i, FREQ, DUR_KO, DUR_KF, 0)
    ec = curve(emu, INTERNAL_RATE); fc = curve(fw, FW_ISR_RATE)
    ep = max(r for _,r in ec); fp = max(r for _,r in fc)
    e500 = db_at(ec, ep, 500); f500 = db_at(fc, fp, 500)
    eko = keyoff_to_db(ec, ep, -40); fko = keyoff_to_db(fc, fp, -40)
    diff500 = f500 - e500
    mark = " <==" if abs(diff500) > 4 or abs(fko-eko) > 100 else ""
    print(f"{i:>2} {NAMES[i]:<14} {p['car_ar']:>2}{p['car_dr']:>2}{p['car_sl']:>2}{p['car_rr']:>2}{p['car_eg']:>2} | "
          f"{e500:>+8.1f} {f500:>+8.1f} {diff500:>+6.1f} | {eko:>7.0f} {fko:>7.0f}{mark}")
    results.append((i, NAMES[i], diff500, fko-eko))

print(f"\n=== 偏差最大的乐器 ===")
by500 = sorted(results, key=lambda x: abs(x[2]), reverse=True)
print(f"按 keyon@500ms 偏差:")
for i, name, d500, dko in by500[:5]:
    print(f"  {i:>2} {name:<14} diff@500={d500:>+6.1f}dB")
