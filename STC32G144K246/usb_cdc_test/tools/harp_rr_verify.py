#!/usr/bin/env python3
"""验证新 RR_TAB 的包络效果 + 测 DR 表是否也偏慢.

1. 用新 RR_TAB 渲染 harpsichord, 对比包络曲线 vs emu
2. 同法测 emu DR 档位衰减时间, 反推 DR_TAB
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fw_real_sim as F
from fw_real_sim import (fw_decode, fw_apply_patch, fw_key_on, fw_calc_step,
                         FW_ISR_RATE, FW_AR_TAB, FW_DR_TAB, FW_RR_TAB, save_fw_wav)
from ym2413_wav_gen import (DEFAULT_INST, NAMES, render_emu2413, save_wav,
                            freq_to_fnum_blk, dump_to_patch, EmuChannel,
                            calc_envelope, calc_phase, calc_slot_mod, calc_slot_car,
                            INTERNAL_RATE)

# 新 RR_TAB + 新 DR_TAB (反推自 emu, 1/2/3 极慢档保留大值)
NEW_RR = [0, 255, 255, 255, 76, 38, 19, 9, 5, 2, 1, 1, 1, 1, 1, 1]
NEW_DR = [0, 255, 255, 255, 75, 38, 19, 9, 5, 2, 1, 1, 1, 1, 1, 1]

dump = DEFAULT_INST[11]
FREQ = 440.0
DUR_KO, DUR_KF = 1.0, 1.0

def render_fw(rr_tab, dr_tab=None):
    """用指定 RR_TAB/DR_TAB 渲染 harpsichord."""
    F.FW_RR_TAB = rr_tab
    if dr_tab is not None:
        F.FW_DR_TAB = dr_tab
    p = fw_decode(dump)
    mod, car = fw_apply_patch(p)   # apply_patch 会用新表
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
    curve = []
    for i in range(0, len(samples), seg):
        s = samples[i:i+seg]
        if not s: break
        curve.append((i*1000/sr, (sum(x*x for x in s)/len(s))**0.5))
    return curve

emu = render_emu2413(11, FREQ, DUR_KO, DUR_KF, 0)
fw_old = render_fw(list(FW_RR_TAB), list(FW_DR_TAB))
fw_new = render_fw(NEW_RR, NEW_DR)

emu_c = env_curve(emu, INTERNAL_RATE, 50)
fw_old_c = env_curve(fw_old, FW_ISR_RATE, 50)
fw_new_c = env_curve(fw_new, FW_ISR_RATE, 50)

emu_max = max(r for _, r in emu_c)
print(f"=== harpsichord 包络对比 (每50ms, 归一化 dB, 峰值=0dB) ===")
print(f"{'t_ms':>5} {'emu_dB':>7} {'fw旧RR':>7} {'fw新RR':>7}")
print("-" * 32)
for (te, re), (_, ro), (_, rn) in zip(emu_c, fw_old_c, fw_new_c):
    ed = 20*math.log10(re/emu_max) if re > 0 else -99
    od = 20*math.log10(ro/emu_max) if ro > 0 else -99
    nd = 20*math.log10(rn/emu_max) if rn > 0 else -99
    print(f"{te:>5.0f} {ed:>+7.1f} {od:>+7.1f} {nd:>+7.1f}")

# keyoff 后衰减时间
print(f"\n=== keyoff (1000ms) 后衰减到 -40dB 的时间 ===")
def time_to_db(curve, peak_max, target_db, start_ms=1000):
    target = peak_max * 10**(target_db/20)
    for t, r in curve:
        if t >= start_ms and r <= target:
            return t - start_ms
    return -1
emu_t = time_to_db(emu_c, emu_max, -40)
old_t = time_to_db(fw_old_c, emu_max, -40)
new_t = time_to_db(fw_new_c, emu_max, -40)
print(f"  emu:    {emu_t:.0f}ms")
print(f"  fw 旧:  {old_t:.0f}ms" if old_t > 0 else "  fw 旧:  >1000ms (太慢)")
print(f"  fw 新:  {new_t:.0f}ms" if new_t > 0 else "  fw 新:  >1000ms")

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wav_rr_fix")
os.makedirs(OUT, exist_ok=True)
save_wav(os.path.join(OUT, "harp_emu.wav"), emu)
save_fw_wav(os.path.join(OUT, "harp_fw_newRR.wav"), fw_new)
print(f"\n输出: {OUT} (harp_emu.wav / harp_fw_newRR.wav)")
