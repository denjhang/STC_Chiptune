#!/usr/bin/env python3
"""Harpsichord (inst 11) 下位机仿真 vs emu2413 对照.

输出两个 WAV:
  wav_harp_test/harp_fw_real.wav   - 下位机 1:1 仿真 (render_fw_real)
  wav_harp_test/harp_emu2413.wav   - emu2413 参考 (render_emu2413)

两个都是: 1秒 keyon + 1秒 keyoff, 440Hz, volume=0 (最大音量).

用法: py -3 tools\harp_test.py
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fw_real_sim import render_fw_real
from ym2413_wav_gen import render_emu2413, save_wav, NAMES, DEFAULT_INST

INST = 11          # Harpsichord
FREQ = 440.0
DUR_KO = 1.0       # 1秒 keyon
DUR_KF = 1.0       # 1秒 keyoff
VOL  = 0           # 0 = 最大音量

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wav_harp_test")
os.makedirs(OUT_DIR, exist_ok=True)

def rms(s):
    return (sum(x*x for x in s)/max(len(s),1))**0.5

print(f"Inst {INST}: {NAMES[INST]}")
print(f"Patch: {['0x%02X'%b for b in DEFAULT_INST[INST]]}")
print(f"Freq={FREQ}Hz, {DUR_KO}s keyon + {DUR_KF}s keyoff, volume={VOL}")
print("-" * 60)

# 下位机仿真
fw = render_fw_real(INST, FREQ, DUR_KO, DUR_KF, VOL)
fw_path = os.path.join(OUT_DIR, "harp_fw_real.wav")
save_wav(fw_path, fw)
print(f"[fw_real] RMS={rms(fw):7.1f}  peak={max(abs(x) for x in fw):6d}  -> {fw_path}")

# emu2413 参考
emu = render_emu2413(INST, FREQ, DUR_KO, DUR_KF, VOL)
emu_path = os.path.join(OUT_DIR, "harp_emu2413.wav")
save_wav(emu_path, emu)
print(f"[emu2413] RMS={rms(emu):7.1f}  peak={max(abs(x) for x in emu):6d}  -> {emu_path}")

er, fr = rms(emu), rms(fw)
d = 20*math.log10(fr/er) if er > 0 and fr > 0 else -99
print("-" * 60)
print(f"RMS diff: {d:+.3f} dB (fw vs emu)")
print(f"\n输出目录: {OUT_DIR}")
