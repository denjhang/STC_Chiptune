#!/usr/bin/env python3
"""扫描 RR_TAB[4] 找 harpsichord keyoff 衰减 50ms 的正确值.

harpsichord: car_rr=4. keyoff 后 carrier release, 用 RR_TAB[4].
目标: keyoff 后到 -40dB 用时 ≈ 50ms (对齐 emu).

DR_TAB 用新反推值 (decay 阶段). 只扫 RR_TAB[4].
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fw_real_sim as F
from fw_real_sim import (fw_decode, fw_apply_patch, fw_key_on, fw_calc_step,
                         FW_ISR_RATE, FW_RR_TAB, FW_DR_TAB, save_fw_wav)
from ym2413_wav_gen import (DEFAULT_INST, render_emu2413, save_wav,
                            freq_to_fnum_blk, INTERNAL_RATE)

NEW_DR = [0, 255, 255, 255, 75, 38, 19, 9, 5, 2, 1, 1, 1, 1, 1, 1]
dump = DEFAULT_INST[11]
FREQ = 440.0
DUR_KO, DUR_KF = 1.0, 1.0

def render_fw(rr4):
    rr_tab = list(NEW_DR)  # DR 不影响这里, 但保持
    # 用新 DR, RR 只改 [4]
    F.FW_DR_TAB = list(NEW_DR)
    rr_new = [0, 255, 255, 255, rr4, 38, 19, 9, 5, 2, 1, 1, 1, 1, 1, 1]
    F.FW_RR_TAB = rr_new
    p = fw_decode(dump)
    mod, car = fw_apply_patch(p)
    fn, bl = freq_to_fnum_blk(FREQ)
    if bl > 0: bl -= 1
    mod['step'] = fw_calc_step(fn, bl, mod['ml'])
    car['step'] = fw_calc_step(fn, bl, car['ml'])
    car['tl'] = max(0, min(31, (60-0)>>1))
    fw_key_on(mod, car)
    n = int((DUR_KO+DUR_KF)*FW_ISR_RATE); nk = int(DUR_KO*FW_ISR_RATE)
    out = []; wc = 0
    for s in range(n):
        if s == nk: F.fw_key_off(mod, car)
        wc = (wc+1) & 0x0F
        total = 0
        if not (car['env_state'] == 4 and car['level'] == 0):
            total = F.fw_render_fm(mod, car, wc, 0)
        else:
            car['env_state'] = 0
        total = max(-32768, min(32767, total << 1))
        out.append(total)
    return out

def env_curve(samples, sr, seg_ms=50):
    seg = int(sr * seg_ms / 1000)
    return [(i*1000/sr, (sum(x*x for x in samples[i:i+seg])/max(len(samples[i:i+seg]),1))**0.5)
            for i in range(0, len(samples), seg) if samples[i:i+seg]]

def keyoff_to_db(curve, peak, target_db, keyoff_ms=1000):
    """keyoff 后降到 target_db 的时间"""
    target = peak * 10**(target_db/20)
    for t, r in curve:
        if t >= keyoff_ms and r <= target:
            return t - keyoff_ms
    return 9999

# emu 参考
emu = render_emu2413(11, FREQ, DUR_KO, DUR_KF, 0)
emu_c = env_curve(emu, INTERNAL_RATE, 50)
emu_peak = max(r for _, r in emu_c)
emu_ko = keyoff_to_db(emu_c, emu_peak, -40)
print(f"emu keyoff->-40dB: {emu_ko:.0f}ms (目标)\n")

# 扫描 RR_TAB[4]
print(f"{'rr4':>4} {'ko->-40dB ms':>13}")
print("-" * 20)
best = None
results = {}
for rr4 in [1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20]:
    out = render_fw(rr4)
    c = env_curve(out, FW_ISR_RATE, 50)
    pk = max(r for _, r in c)
    ko = keyoff_to_db(c, pk, -40)
    results[rr4] = ko
    print(f"{rr4:>4} {ko:>13.0f}")
    score = abs(ko - emu_ko)
    if best is None or score < best[0]:
        best = (score, rr4, ko)

print(f"\n最接近 emu({emu_ko:.0f}ms): RR_TAB[4]={best[1]} -> {best[2]:.0f}ms")

# 用最佳值输出 wav + 曲线
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wav_rr4")
os.makedirs(OUT, exist_ok=True)
out = render_fw(best[1])
save_fw_wav(os.path.join(OUT, f"harp_fw_rr4_{best[1]}.wav"), out)
save_wav(os.path.join(OUT, "harp_emu.wav"), emu)

# 详细曲线对比 (各自归一化)
fw_c = env_curve(out, FW_ISR_RATE, 50)
fw_peak = max(r for _, r in fw_c)
print(f"\n=== 包络曲线 (各自归一化 0dB峰值) RR_TAB[4]={best[1]} ===")
print(f"{'t_ms':>5} {'emu':>7} {'fw':>7}")
for (te, re), (_, rf) in zip(emu_c, fw_c):
    ed = 20*math.log10(re/emu_peak) if re > 0 else -99
    fd = 20*math.log10(rf/fw_peak) if rf > 0 else -99
    print(f"{te:>5.0f} {ed:>+7.1f} {fd:>+7.1f}")

print(f"\n输出: {OUT}/harp_fw_rr4_{best[1]}.wav + harp_emu.wav")
