#!/usr/bin/env python3
"""扫描 sus_hold 缩放, 找 sustain 衰减对齐 emu 的值.

完整 render_fw_real 流程 (用固化后的 env_tick), 临时覆盖 FW_SUS_HOLD.
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fw_real_sim as F
from fw_real_sim import (render_fw_real, FW_SUS_HOLD, FW_ISR_RATE, save_fw_wav)
from ym2413_wav_gen import (render_emu2413, save_wav, INTERNAL_RATE)

BASE = list(FW_SUS_HOLD)
def curve(s, sr, ms=50):
    seg = int(sr*ms/1000)
    return [(i*1000/sr, (sum(x*x for x in s[i:i+seg])/max(len(s[i:i+seg]),1))**0.5) for i in range(0,len(s),seg) if s[i:i+seg]]

emu = render_emu2413(11, 440.0, 1.0, 1.0, 0)
ec = curve(emu, INTERNAL_RATE); ep = max(r for _,r in ec)
targets = {200:-5.5, 400:-11.0, 600:-16.5, 800:-22.0, 950:-26.1}

print(f"=== sus_hold 缩放扫描 (完整 render_fw_real) ===")
print(f"emu: @200{-5.5} @400{-11} @600{-16.5} @800{-22} @950{-26.1}\n")
print(f"{'scale':>6} {'@200':>6} {'@400':>6} {'@600':>6} {'@800':>6} {'@950':>6} {'score':>7}")
print("-" * 48)
best=None; OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),'wav_sushold2'); os.makedirs(OUT,exist_ok=True)
save_wav(os.path.join(OUT,'harp_emu.wav'), emu)
for scale in [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0]:
    F.FW_SUS_HOLD = [max(1, int(h*scale)) for h in BASE]
    out = render_fw_real(11, 440.0, 1.0, 1.0, 0)
    c = curve(out, FW_ISR_RATE); pk = max(r for _,r in c)
    def db_at(ms):
        for t,r in c:
            if abs(t-ms)<30: return 20*math.log10(r/pk) if r>0 else -99
        return -99
    ds = {m:db_at(m) for m in targets}
    score = sum(abs(ds[m]-targets[m]) for m in targets)
    print(f"{scale:>6} {ds[200]:>+6.1f} {ds[400]:>+6.1f} {ds[600]:>+6.1f} {ds[800]:>+6.1f} {ds[950]:>+6.1f} {score:>7.1f}")
    save_fw_wav(os.path.join(OUT, f'harp_sc{scale}.wav'), out)
    if best is None or score < best[0]: best=(score, scale, list(F.FW_SUS_HOLD))
print(f'\n最佳 scale={best[1]} (score={best[0]:.1f})')
print(f'对应 sus_hold = {best[2]}')
