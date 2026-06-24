#!/usr/bin/env python3
"""harpsichord release 精调: sus_hold=0.44 固定, 扫描 RR_TAB[7].

emu release: @1050=-43.2 @1100=-99 (跨度50ms, 中速)
fw  当前: @1050=-99 (太快)
RR_TAB[7] 当前=9, 扫描更大值 (慢).
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fw_real_sim as F
from fw_real_sim import render_fw_real, FW_ISR_RATE, FW_RR_TAB, save_fw_wav
from ym2413_wav_gen import render_emu2413, INTERNAL_RATE, save_wav

ORIG_RR = list(FW_RR_TAB)
def curve(s, sr, ms=25):
    seg = int(sr*ms/1000)
    return [(i*1000/sr, (sum(x*x for x in s[i:i+seg])/max(len(s[i:i+seg]),1))**0.5) for i in range(0,len(s),seg) if s[i:i+seg]]

emu = render_emu2413(11, 440.0, 1.0, 1.0, 0)
ec = curve(emu, INTERNAL_RATE); ep = max(r for _,r in ec)

print(f"=== harpsichord release 精调 (sus_hold scale=0.44 已固化) ===")
print(f"emu release: @1025 @1050 @1075 @1100\n")
# emu release 段 dB
for ms in [1000, 1025, 1050, 1075, 1100, 1125]:
    for t,r in ec:
        if abs(t-ms)<15:
            print(f"  emu @{ms}ms = {20*math.log10(r/ep) if r>0 else -99:+.1f}")
            break

print(f"\n{'rr7':>4} {'@1025':>7} {'@1050':>7} {'@1075':>7} {'@1100':>7} {'score':>7}")
print("-" * 42)
# emu 目标
tgt = {1025:0, 1050:-43.2, 1075:0, 1100:-99}  # 1025/1075 近似
best=None
OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),'wav_harp_rel'); os.makedirs(OUT,exist_ok=True)
save_wav(os.path.join(OUT,'harp_emu.wav'), emu)
for rr7 in [9, 11, 13, 15, 18, 21, 25]:
    F.FW_RR_TAB = list(ORIG_RR); F.FW_RR_TAB[7] = rr7
    out = render_fw_real(11, 440.0, 1.0, 1.0, 0)
    c = curve(out, FW_ISR_RATE); pk = max(r for _,r in c)
    def db_at(ms):
        for t,r in c:
            if abs(t-ms)<15: return 20*math.log10(r/pk) if r>0 else -99
        return -99
    d1050 = db_at(1050)
    # score: @1050 接近 -43 最好
    score = abs(d1050 + 43.2)
    print(f"{rr7:>4} {db_at(1025):>+7.1f} {d1050:>+7.1f} {db_at(1075):>+7.1f} {db_at(1100):>+7.1f} {score:>7.1f}")
    save_fw_wav(os.path.join(OUT, f'harp_rr7_{rr7}.wav'), out)
    if best is None or score < best[0]: best=(score, rr7)
print(f'\n最佳 rr7={best[1]} (score={best[0]:.1f}, emu @1050=-43.2)')
