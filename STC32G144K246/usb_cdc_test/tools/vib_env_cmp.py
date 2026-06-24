#!/usr/bin/env python3
"""直接测 emu vibraphone 完整包络, 对照 fw, 看哪里过早关闭.

vibraphone: car eg=0(non-sus) sl=1 rr=2, mod eg=0 fb=7
emu: non-sus release 用速率7 (get_parameter_rate), 不随 RR
fw : rel_hold 固定 (sus_hold//10)
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fw_real_sim as F
from fw_real_sim import render_fw_real, FW_ISR_RATE, save_fw_wav, fw_decode
from ym2413_wav_gen import (DEFAULT_INST, NAMES, render_emu2413, save_wav,
                            INTERNAL_RATE)

FREQ = 440.0
DUR_KO, DUR_KF = 1.0, 1.0
INST = 12  # vibraphone

p = fw_decode(DEFAULT_INST[INST])
print(f"=== vibraphone 参数 ===")
print(f"  mod: ar={p['mod_ar']} dr={p['mod_dr']} sl={p['mod_sl']} rr={p['mod_rr']} eg={p['mod_eg']} fb={p['mod_fb']} tl={p['mod_tl']}")
print(f"  car: ar={p['car_ar']} dr={p['car_dr']} sl={p['car_sl']} rr={p['car_rr']} eg={p['car_eg']}")

emu = render_emu2413(INST, FREQ, DUR_KO, DUR_KF, 0)
fw = render_fw_real(INST, FREQ, DUR_KO, DUR_KF, 0)

def curve(s, sr, ms=50):
    seg = int(sr*ms/1000)
    return [(i*1000/sr, (sum(x*x for x in s[i:i+seg])/max(len(s[i:i+seg]),1))**0.5) for i in range(0,len(s),seg) if s[i:i+seg]]

ec = curve(emu, INTERNAL_RATE); fc = curve(fw, FW_ISR_RATE)
ep = max(r for _,r in ec); fp = max(r for _,r in fc)

print(f"\n=== 包络对比 (每50ms, 各自归一化) ===")
print(f"{'t_ms':>5} {'emu':>7} {'fw':>7}")
for (te,re),(_,rf) in zip(ec,fc):
    ed = 20*math.log10(re/ep) if re>0 else -99
    fd = 20*math.log10(rf/fp) if rf>0 else -99
    mark = ' <-keyoff' if te == 1000 else (' <-rel' if 1000 < te <= 1300 else '')
    print(f'{te:>5.0f} {ed:>+7.1f} {fd:>+7.1f}{mark}')

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'wav_vib')
os.makedirs(OUT, exist_ok=True)
save_wav(os.path.join(OUT, 'vib_emu.wav'), emu)
save_fw_wav(os.path.join(OUT, 'vib_fw.wav'), fw)
print(f'\nWAV: {OUT}/vib_emu.wav + vib_fw.wav')
