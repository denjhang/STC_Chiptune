#!/usr/bin/env python3
"""验证仿真器 8.8 定点同步修复: 频率应≈438Hz (下位机一致), 不再 992Hz.

测 harpsichord carrier 实际频率 (自相关), 对照 emu(440).
输出 harpsichord 1s+1s 的 fw vs emu wav.
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fw_real_sim as F
from fw_real_sim import (render_fw_real, save_fw_wav, FW_ISR_RATE,
                         fw_decode, fw_apply_patch, fw_key_on, fw_env_tick,
                         fw_calc_step, FW_SIN, FW_HALFSIN)
from ym2413_wav_gen import (DEFAULT_INST, NAMES, render_emu2413, save_wav,
                            freq_to_fnum_blk)

def autocorr_freq(samples, sr, fmin=200, fmax=1200):
    """自相关测基频, 只取 0.05s 短段 (够测, 快)."""
    start = int(0.1*sr); end = min(int(0.15*sr), len(samples))
    seg = samples[start:end]
    if len(seg) < 256: return -1
    lag_min = max(1, int(sr/fmax)); lag_max = int(sr/fmin)
    best_lag, best_corr = -1, -1e18
    for lag in range(lag_min, lag_max+1):
        c = sum(seg[i]*seg[i+lag] for i in range(len(seg)-lag))
        if c > best_corr:
            best_corr = c; best_lag = lag
    return sr/best_lag if best_lag > 0 else -1

INST = 11
FREQ = 440.0
DUR_KO, DUR_KF = 1.0, 1.0

print(f"=== 仿真器 8.8 定点同步验证 ===")
print(f"FW_ISR_RATE = {FW_ISR_RATE}")
print(f"FW_STEP_CONST = {F.FW_STEP_CONST:.8f} (×256, 8.8)")
print(f"FW_HALFSIN 后半周 = {FW_HALFSIN[32:40]}... (mute=0)")
print()

# 仿真器渲染
fw = render_fw_real(INST, FREQ, DUR_KO, DUR_KF, 0)
# emu 渲染 (49716 采样率)
emu = render_emu2413(INST, FREQ, DUR_KO, DUR_KF, 0)

# 频率检测
fw_freq = autocorr_freq(fw, FW_ISR_RATE)
emu_freq = autocorr_freq(emu, 49716)

print(f"harpsichord 440Hz 实际输出频率:")
print(f"  仿真器 (fw, 22050Hz): {fw_freq:.1f} Hz  (期望≈438, 下位机一致)")
print(f"  emu2413 (49716Hz)   : {emu_freq:.1f} Hz  (期望≈440)")
print(f"  比例 fw/emu = {fw_freq/emu_freq:.4f}  (修复前是 2.255, 应接近 1.0)")

# 输出 wav
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wav_fw_sync")
os.makedirs(OUT, exist_ok=True)
save_fw_wav(os.path.join(OUT, "harp_fw.wav"), fw)        # 22050
save_wav(os.path.join(OUT, "harp_emu.wav"), emu)          # emu 标准保存
print(f"\n输出: {OUT}")
print(f"  harp_fw.wav  (仿真器, 22050Hz, 8.8定点)")
print(f"  harp_emu.wav (emu2413 参考)")
