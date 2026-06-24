#!/usr/bin/env python3
"""harpsichord 精调: sus_hold scale 细扫 + release 观察.

当前 scale=0.4, sustain 略快 (diff -2~-3), release@1050 归零 (emu -43, 偏快).
细扫 scale 0.40~0.55, 找 keyon 段最优, 同时看 release.
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fw_real_sim as F
from fw_real_sim import render_fw_real, FW_SUS_HOLD, FW_ISR_RATE, save_fw_wav
from ym2413_wav_gen import render_emu2413, INTERNAL_RATE, save_wav

# 原始未缩放表 (tau=221ms), 固化的 scale=0.4 表是 BASE×0.4 的结果
BASE = [0, 305, 305, 178, 126, 98, 80, 68, 59, 52, 46, 42, 38, 35, 33,
        30, 28, 27, 25, 24, 23, 21, 20, 20, 19, 18, 17, 17, 16, 15, 15, 14]
def curve(s, sr, ms=50):
    seg = int(sr*ms/1000)
    return [(i*1000/sr, (sum(x*x for x in s[i:i+seg])/max(len(s[i:i+seg]),1))**0.5) for i in range(0,len(s),seg) if s[i:i+seg]]

emu = render_emu2413(11, 440.0, 1.0, 1.0, 0)
ec = curve(emu, INTERNAL_RATE); ep = max(r for _,r in ec)
# emu keyon 段目标
targets = {100:-2.7, 300:-8.2, 500:-13.7, 700:-19.2, 900:-24.7, 950:-26.1}

print(f"=== harpsichord sus_hold scale 精调 ===\n")
print(f"{'scale':>6} {'@100':>6} {'@300':>6} {'@500':>6} {'@700':>6} {'@900':>6} {'@950':>6} {'score':>7} {'rel@1050':>9}")
print("-" * 70)
best=None
for scale in [0.40, 0.42, 0.44, 0.46, 0.48, 0.50, 0.55]:
    F.FW_SUS_HOLD = [max(1, int(h*scale)) for h in BASE]
    out = render_fw_real(11, 440.0, 1.0, 1.0, 0)
    c = curve(out, FW_ISR_RATE); pk = max(r for _,r in c)
    def db_at(ms):
        for t,r in c:
            if abs(t-ms)<30: return 20*math.log10(r/pk) if r>0 else -99
        return -99
    ds = {m:db_at(m) for m in targets}
    # release @1050
    r1050 = db_at(1050)
    score = sum(abs(ds[m]-targets[m]) for m in targets)
    print(f"{scale:>6} {ds[100]:>+6.1f} {ds[300]:>+6.1f} {ds[500]:>+6.1f} {ds[700]:>+6.1f} {ds[900]:>+6.1f} {ds[950]:>+6.1f} {score:>7.1f} {r1050:>+9.1f}")
    if best is None or score < best[0]: best=(score, scale)

print(f'\n最佳 scale={best[1]} (score={best[0]:.1f})')
print(f'\nemu release: @1050=-43.2 @1100=-99')
print(f'注: release 速率由 RR_TAB[7]=9 控制 (固定速率7), 若偏快可调')
