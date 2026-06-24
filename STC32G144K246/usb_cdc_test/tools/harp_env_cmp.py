#!/usr/bin/env python3
"""harpsichord 包络行为对比: fw vs emu, 逐段 RMS 看包络形状.

1s keyon + 1s keyoff, 每 20ms 算一段 RMS, 输出包络曲线.
无需输出 wav, 直接看数值差异.
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fw_real_sim as F
from fw_real_sim import (fw_decode, fw_apply_patch, fw_key_on, fw_env_tick,
                         fw_calc_step, FW_SIN, FW_HALFSIN, FW_ISR_RATE, save_fw_wav)
from ym2413_wav_gen import (DEFAULT_INST, NAMES, render_emu2413, save_wav,
                            freq_to_fnum_blk, INTERNAL_RATE)

dump = DEFAULT_INST[11]
INST = 11
FREQ = 440.0
DUR_KO, DUR_KF = 1.0, 1.0

def render_fw_fb(fb_override):
    p = fw_decode(dump)
    p['mod_fb'] = fb_override
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

def env_curve(samples, sr, seg_ms=20):
    """逐段 RMS, 返回 [(t_ms, rms), ...]"""
    seg = int(sr * seg_ms / 1000)
    curve = []
    for i in range(0, len(samples), seg):
        s = samples[i:i+seg]
        if not s: break
        r = (sum(x*x for x in s)/len(s))**0.5
        curve.append((i*1000/sr, r))
    return curve

# 渲染
emu = render_emu2413(INST, FREQ, DUR_KO, DUR_KF, 0)
fw  = render_fw_fb(3)   # fb3 (你说 fb2/3 差不多)

emu_c = env_curve(emu, INTERNAL_RATE, 20)
fw_c  = env_curve(fw, FW_ISR_RATE, 20)

print(f"=== harpsichord 包络曲线对比 (每20ms RMS) ===")
print(f"keyon 0~1000ms, keyoff 1000~2000ms\n")
print(f"{'t_ms':>6} {'emu_RMS':>9} {'fw_RMS':>9} {'emu_dB':>8} {'fw_dB':>8} {'差dB':>7}")
print("-" * 56)
# 归一化到各自最大值, 看 shape
emu_max = max(r for _, r in emu_c)
fw_max  = max(r for _, r in fw_c)
for (te, re), (tf, rf) in zip(emu_c, fw_c):
    ed = 20*math.log10(re/emu_max) if re > 0 and emu_max > 0 else -99
    fd = 20*math.log10(rf/fw_max) if rf > 0 and fw_max > 0 else -99
    diff = fd - ed
    bar_e = '#' * int(max(0, ed)/-3) if ed > -60 else ''
    print(f"{te:>6.0f} {re:>9.1f} {rf:>9.1f} {ed:>+8.2f} {fd:>+8.2f} {diff:>+7.2f}")

print(f"\n=== 包络特征点 ===")
def find_points(curve, label):
    rs = [r for _, r in curve]
    peak = max(rs)
    peak_t = curve[rs.index(peak)][0]
    # attack 时间 (到 peak)
    # decay 到 -6dB (peak/2)
    target6 = peak / 2
    t6 = next((t for t, r in curve if r <= target6 and t > peak_t), -1)
    # decay 到 -20dB (peak/10)
    target20 = peak / 10
    t20 = next((t for t, r in curve if r <= target20 and t > peak_t), -1)
    # sustain level @ 900ms (keyoff 前)
    sus = next((r for t, r in curve if 880 <= t <= 980), 0)
    print(f"  {label}: peak={peak:.0f}@{peak_t:.0f}ms, -6dB@{t6:.0f}ms, -20dB@{t20:.0f}ms, sustain@900ms={sus:.0f} ({20*math.log10(sus/peak) if sus>0 else -99:+.1f}dB)")
    return peak_t, t6, t20, sus

print()
find_points(emu_c, "emu")
find_points(fw_c,  "fw ")
print(f"\n峰值 emu={emu_max:.0f} fw={fw_max:.0f} (归一化看 shape, 绝对值无关)")
