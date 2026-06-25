#!/usr/bin/env python3
"""对比 emu vs fw 的 volume->输出 关系, 看是否需要对数映射.

emu: volume 0~63, tll = TLL_TABLE[..][volume][..], 输出经 exp 转换 (对数域)
fw : volume 0~63, car.tl = (60-volume)>>1 (线性反相)
测同一乐器各 volume 的输出 RMS, 看曲线形态.
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fw_real_sim as F
from fw_real_sim import render_fw_real, FW_ISR_RATE
from ym2413_wav_gen import render_emu2413, INTERNAL_RATE

def rms(s): return (sum(x*x for x in s)/max(len(s),1))**0.5

print("=== volume -> 输出 RMS 对比 (flute, 440Hz, 0.3s) ===\n")
print(f"{'vol':>4} {'emu_rms':>9} {'emu_dB':>8} {'fw_rms':>9} {'fw_dB':>8} {'fw映射':>8}")
print("-" * 52)
emu_ref = None; fw_ref = None
for vol in range(0, 64, 4):
    emu = render_emu2413(4, 440.0, 0.3, 0.0, vol)
    fw = render_fw_real(4, 440.0, 0.3, 0.0, vol)
    er = rms(emu); fr = rms(fw)
    if emu_ref is None: emu_ref = er; fw_ref = fr
    ed = 20*math.log10(er/emu_ref) if er > 0 and emu_ref > 0 else -99
    fd = 20*math.log10(fr/fw_ref) if fr > 0 and fw_ref > 0 else -99
    # fw 映射: vol -> tl
    fw_vol = 60 - vol
    tl = max(0, min(31, fw_vol >> 1))
    print(f"{vol:>4} {er:>9.0f} {ed:>+8.1f} {fr:>9.0f} {fd:>+8.1f} tl={tl:>2}")

print(f"\n=== 分析 ===")
print(f"若 emu_dB 均匀分布 (每级 ~-3dB) -> 对数映射 (音量旋钮特性)")
print(f"若 fw_dB 集中在低 vol 区 -> 线性映射, 需改对数")
