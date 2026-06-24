#!/usr/bin/env python3
"""halfsin 后半周改静音(0) 的完整验证.

1. harpsichord (inst 11) 1s+1s: emu vs fw_mute 的 RMS/peak/波形对照
2. 全 15 乐器 RMS 对照: 看改动对 halfsin 音色(car_ws=1 或 mod_ws=1)的影响
3. 输出 WAV 可听对照

halfsin 影响: 解码 ws 位, ws=1 用 halfsin.
  mod_ws = (dump[3]>>3)&1, car_ws = (dump[3]>>4)&1
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fw_real_sim as F
from fw_real_sim import render_fw_real, fw_decode
from ym2413_wav_gen import (DEFAULT_INST, NAMES, render_emu2413, save_wav,
                            INTERNAL_RATE)

FREQ = 440.0
DUR_KO, DUR_KF = 1.0, 1.0

def rms(s): return (sum(x*x for x in s)/max(len(s),1))**0.5
def peak(s): return max(abs(x) for x in s) if s else 0

# 当前 FW_HALFSIN 已改成 mute (本脚本运行时)
print(f"FW_HALFSIN 后半周(32~63) = {F.FW_HALFSIN[32:48]}... (mute=0)")
print()

# ============ 1. harpsichord 详细对照 ============
INST = 11
print(f"=== [{INST}] {NAMES[INST]} | {FREQ}Hz | {DUR_KO}s+{DUR_KF}s ===")
emu = render_emu2413(INST, FREQ, DUR_KO, DUR_KF, 0)
fw  = render_fw_real(INST, FREQ, DUR_KO, DUR_KF, 0)
er, fr = rms(emu), rms(fw)
d = 20*math.log10(fr/er) if er > 0 and fr > 0 else -99
print(f"  emu: RMS={er:7.1f} peak={peak(emu):6d}")
print(f"  fw : RMS={fr:7.1f} peak={peak(fw):6d}  dB_vs_emu={d:+.2f}")

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wav_halfsin_fix")
os.makedirs(OUT, exist_ok=True)
save_wav(os.path.join(OUT, "harp_emu.wav"), emu)
save_wav(os.path.join(OUT, "harp_fw_mute.wav"), fw)

# 波形前 48 采样对照
print(f"\n  前48采样:")
print(f"  {'s':>3} {'emu':>7} {'fw':>5}")
for i in range(48):
    print(f"  {i:>3} {emu[i]:>7} {fw[i]:>5}")

# ============ 2. 全 15 乐器 RMS 对照 ============
print(f"\n=== 全 15 乐器 RMS 对照 (halfsin mute 后) ===")
# 标记哪些乐器用了 halfsin
print(f"{'Inst':>3} {'Name':<14} {'mod_ws':>6} {'car_ws':>6} {'emu_RMS':>8} {'fw_RMS':>8} {'dB':>7}")
print("-" * 64)
for i in range(1, 16):
    p = fw_decode(DEFAULT_INST[i])
    e = render_emu2413(i, FREQ, DUR_KO, DUR_KF, 0)
    fw_ = render_fw_real(i, FREQ, DUR_KO, DUR_KF, 0)
    er_, fr_ = rms(e), rms(fw_)
    d_ = 20*math.log10(fr_/er_) if er_ > 0 and fr_ > 0 else -99
    mark = " <== halfsin" if (p['mod_ws'] or p['car_ws']) else ""
    print(f"{i:>3} {NAMES[i]:<14} {p['mod_ws']:>6} {p['car_ws']:>6} "
          f"{er_:>8.1f} {fr_:>8.1f} {d_:>+7.2f}{mark}")

print(f"\n输出: {OUT}")
print(f"  harp_emu.wav (参考) / harp_fw_mute.wav (修复后)")
