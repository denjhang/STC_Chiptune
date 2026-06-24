#!/usr/bin/env python3
"""纯Python自相关基频检测, 确认反馈移位不改音高.

检测各 fb_shift 的基频是否一致 (音高不变).
另外检查 emu 的 FB 各档位分布 (哪些乐器带反馈).
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fw_real_sim as F
from fw_real_sim import (fw_decode, fw_apply_patch, fw_key_on, fw_env_tick,
                         fw_calc_step, FW_SIN, INTERNAL_RATE)
from ym2413_wav_gen import (DEFAULT_INST, NAMES, render_emu2413, save_wav,
                            freq_to_fnum_blk)

def autocorr_freq(samples, sr, fmin=80, fmax=2000):
    """自相关法测基频. 取稳定段(attack后)分析."""
    n = len(samples)
    # 取 0.1~0.3s 段 (attack 后, 稳定)
    start = int(0.1*sr); end = min(int(0.3*sr), n)
    seg = samples[start:end]
    if len(seg) < 256: return -1
    lag_min = int(sr/fmax); lag_max = int(sr/fmin)
    best_lag, best_corr = -1, -1e18
    for lag in range(lag_min, lag_max+1):
        c = 0
        for i in range(len(seg)-lag):
            c += seg[i]*seg[i+lag]
        # 归一化 (用 lag=0 的自相关)
        if c > best_corr:
            best_corr = c; best_lag = lag
    if best_lag < 0: return -1
    return sr/best_lag

# ===== 1. 全 15 乐器的 FB 分布 =====
print("=== 全 15 乐器 FB (反馈) 分布 ===")
print(f"{'Inst':>3} {'Name':<14} {'FB':>3} {'mod_ws':>6} {'car_ws':>6}")
print("-" * 40)
for i in range(1, 16):
    p = fw_decode(DEFAULT_INST[i])
    mark = " <== 有反馈" if p['mod_fb'] > 0 else ""
    print(f"{i:>3} {NAMES[i]:<14} {p['mod_fb']:>3} {p['mod_ws']:>6} {p['car_ws']:>6}{mark}")

# ===== 2. harpsichord 各 fb_shift 基频 =====
dump = DEFAULT_INST[11]
FREQ = 440.0
DUR_KO, DUR_KF = 0.4, 0.0   # 短一点, 只要稳定段

def render_fw(fb_shift):
    p = fw_decode(dump)
    mod, car = fw_apply_patch(p)
    fn, bl = freq_to_fnum_blk(FREQ)
    if bl > 0: bl -= 1
    mod['step'] = fw_calc_step(fn, bl, mod['ml'])
    car['step'] = fw_calc_step(fn, bl, car['ml'])
    car['tl'] = max(0, min(31, (60-0)>>1))
    car['wave'] = list(FW_SIN[:32]) + [0]*32
    if p['mod_ws']: mod['wave'] = list(FW_SIN[:32]) + [0]*32
    fw_key_on(mod, car)
    out = []
    wc = 0
    n = int((DUR_KO+DUR_KF)*INTERNAL_RATE)
    for i in range(n):
        wc = (wc+1) & 0x0F
        mod['pos'] = (mod['pos'] + mod['step']) & 0xFFFFFFFF
        midx = (mod['pos'] >> 16) & 0x3F
        midx = (midx + (mod['fb_val'] & 0xFF)) & 0x3F
        mwave = mod['wave'][midx]
        if wc == 0: fw_env_tick(mod)
        mch = ((mwave * (mod['level']+1) * (mod['tl']+1)) >> 10)
        if mch > 127: mch = 127
        elif mch < -128: mch = -128
        if mod['fb'] > 0:
            mod['fb_val'] = max(-128, min(127, mch >> fb_shift))
        else: mod['fb_val'] = 0
        car['pos'] = (car['pos'] + car['step']) & 0xFFFFFFFF
        cidx = (car['pos'] >> 16) & 0x3F
        cidx = (cidx + (mch & 0xFF)) & 0x3F
        cwave = car['wave'][cidx]
        if wc == 0: fw_env_tick(car)
        cch = ((cwave * (car['level']+1) * (car['tl']+1)) >> 10)
        if cch > 127: cch = 127
        elif cch < -128: cch = -128
        total = max(-32768, min(32767, cch << 1))
        out.append(total)
    return out

print(f"\n=== harpsichord 各 fb_shift 基频检测 (音高不变性) ===")
print(f"期望: 所有 fb_shift 基频一致 (反馈只改音色, 不改音高)\n")
SR_DOWN = 22050   # INTERNAL_RATE 49716, 但下位机 ISR 是 22050
# 注意: fw 仿真用 INTERNAL_RATE=49716, 实际下位机 22050, 这里测相对一致性即可
sr = INTERNAL_RATE
freqs = {}
for N in [1, 2, 3, 4, 5]:
    out = render_fw(N)
    f = autocorr_freq(out, sr)
    freqs[N] = f
    print(f"  fb_shift={N}: 基频 ≈ {f:.1f} Hz")

# emu 基频 (reference)
emu = render_emu2413(11, FREQ, DUR_KO, DUR_KF, 0)
ef = autocorr_freq(emu, sr)
print(f"  emu 参考 : 基频 ≈ {ef:.1f} Hz")

# 判断一致性
fs = list(freqs.values())
fmin_, fmax_ = min(fs), max(fs)
print(f"\n各 fb_shift 基频范围: {fmin_:.1f}~{fmax_:.1f} Hz, 差 {fmax_-fmin_:.1f} Hz")
if fmax_ - fmin_ < 5:
    print("✓ 反馈移位不改变基频 (音高稳定), 可安全调反馈强度")
else:
    print("✗ 反馈移位导致基频偏移, 需谨慎")
