#!/usr/bin/env python3
"""验证: halfsin 负半周改静音(0) vs 镜像(现状), 对照 emu.

emu2413 halfsin (emu2413.c:383-387):
  前半周 (0~31)  = fullsin (有值)
  后半周 (32~63) = 0xfff (静音, 不是镜像!)

下位机现状 (fw_real_sim FW_HALFSIN):
  后半周 = 前半周镜像 (全正) -> carrier 永远正 -> 过反馈失真

本脚本: 把 FW_HALFSIN 后半周置 0, 看能否恢复负半周摆动 + 接近 emu.
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fw_real_sim as F
from ym2413_wav_gen import (DEFAULT_INST, NAMES, dump_to_patch, freq_to_fnum_blk,
                            EmuChannel, save_wav, INTERNAL_RATE)

INST = 11
FREQ = 440.0
DUR_KO, DUR_KF = 1.0, 1.0
N_PEEK = 48

# emu 参考
def render_emu():
    mp, cp = dump_to_patch(DEFAULT_INST[INST])
    ch = EmuChannel(mp, cp)
    fn, bl = freq_to_fnum_blk(FREQ)
    ch.set_note(fn, bl); ch.set_volume(0); ch.set_sus(0); ch.key_on()
    n = int((DUR_KO + DUR_KF) * INTERNAL_RATE); nk = int(DUR_KO * INTERNAL_RATE)
    o = []
    for i in range(n):
        if i == nk: ch.key_off()
        o.append(ch.render_one())
    return o

# fw 渲染 (用 monkey-patch 改 FW_HALFSIN)
def render_fw(half_mode):
    # half_mode: 'mirror'=现状, 'mute'=后半周置0
    orig = F.FW_HALFSIN
    if half_mode == 'mute':
        h = list(F.FW_SIN[:32]) + [0]*32   # 后半周静音
        F.FW_HALFSIN = h
    try:
        # 重新 apply_patch 让 wave 指向新表
        from fw_real_sim import render_fw_real
        out = render_fw_real(INST, FREQ, DUR_KO, DUR_KF, 0)
    finally:
        F.FW_HALFSIN = orig
    return out

def rms(s): return (sum(x*x for x in s)/max(len(s),1))**0.5
def neg_ratio(s):
    neg = sum(1 for x in s if x < 0)
    return neg / max(len(s), 1)

print(f"=== Inst {INST}: {NAMES[INST]} | halfsin 负半周: 镜像(现状) vs 静音(emu) ===\n")

emu = render_emu()
fw_mirror = render_fw('mirror')
fw_mute   = render_fw('mute')

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wav_harp_half")
os.makedirs(OUT, exist_ok=True)
save_wav(os.path.join(OUT, "harp_emu.wav"), emu)
save_wav(os.path.join(OUT, "harp_fw_mirror.wav"), fw_mirror)
save_wav(os.path.join(OUT, "harp_fw_mute.wav"), fw_mute)

print(f"{'版本':<16} {'RMS':>8} {'peak':>6} {'neg%':>6} {'dB_vs_emu':>9}")
print("-" * 52)
for name, s in [("emu 参考", emu), ("fw mirror(现)", fw_mirror), ("fw mute(emu)", fw_mute)]:
    r, ng, pk = rms(s), neg_ratio(s), max(abs(x) for x in s)
    d = 20*math.log10(r/rms(emu)) if r > 0 and rms(emu) > 0 else -99
    print(f"{name:<16} {r:8.1f} {pk:6d} {ng:6.3f} {d:+9.3f}")

print(f"\n--- 前{N_PEEK}采样 carrier 波形对比 (看负半周) ---")
print(f"{'s':>3} {'emu':>7} {'fw_mirror':>10} {'fw_mute':>9}")
for i in range(N_PEEK):
    print(f"{i:>3} {emu[i]:>7} {fw_mirror[i]:>10} {fw_mute[i]:>9}")

print(f"\n输出: {OUT}")
print(f"  harp_emu.wav / harp_fw_mirror.wav / harp_fw_mute.wav")
