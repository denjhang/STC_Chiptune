#!/usr/bin/env python3
"""测 emu 各 RR 档位下 SUSTAIN(non-sus) 的衰减速度, 反推 sus_hold 按 RR 缩放.

emu: non-sus(EG=0) SUSTAIN 用 RR 速率, eg_out 线性递增 -> 输出指数衰减.
     RR 小=慢衰减(长 sustain), RR 大=快衰减.
fw : sus_hold 固定 tau, 不分 RR -> 慢 RR 乐器(vibraphone RR=2)被快衰减.

测 emu SUSTAIN(RR=n) 从 attack 后到 -20dB 的时间, 反推 sus_hold 缩放因子.
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ym2413_wav_gen import (DEFAULT_INST, dump_to_patch, freq_to_fnum_blk,
                            EmuChannel, calc_envelope, calc_phase,
                            calc_slot_mod, calc_slot_car, INTERNAL_RATE)

ISR = 22050

def measure_emu_sustain(rr_val):
    """carrier SL=0/EG=0/RR=n, 测 attack 后输出到 -20dB 的时间."""
    mp, cp = dump_to_patch(DEFAULT_INST[12])
    cp.RR = rr_val; cp.EG = 0; cp.SL = 0
    ch = EmuChannel(mp, cp)
    fn, bl = freq_to_fnum_blk(440.0)
    ch.set_note(fn, bl); ch.set_volume(0); ch.set_sus(0); ch.key_on()
    from ym2413_wav_gen import am_table
    outs = []
    for i in range(int(3.0*INTERNAL_RATE)):
        ch.pm_phase = (ch.pm_phase+1)&0xffffffff; ch.am_phase += 1
        ch.lfo_am = am_table[(ch.am_phase>>6)%len(am_table)]
        ch.eg_counter += 1
        calc_envelope(ch.mod, ch.eg_counter); calc_phase(ch.mod, ch.pm_phase)
        calc_envelope(ch.car, ch.eg_counter); calc_phase(ch.car, ch.pm_phase)
        mo = calc_slot_mod(ch.mod, ch.lfo_am)
        outs.append(calc_slot_car(ch.car, mo, ch.lfo_am))
    # attack 后峰值
    seg = int(0.02*INTERNAL_RATE)
    peak = max((sum(x*x for x in outs[i:i+seg])/seg)**0.5 for i in range(0, len(outs)-seg, seg//4))
    target20 = peak * 0.1  # -20dB
    # 找 attack 后(50ms起)到 -20dB
    start = int(0.05*INTERNAL_RATE)
    for i in range(start, len(outs)-seg, seg//2):
        r = (sum(x*x for x in outs[i:i+seg])/len(outs[i:i+seg]))**0.5
        if r <= target20:
            return (i - start)/INTERNAL_RATE*1000
    return 9999

print(f"=== emu SUSTAIN(RR=n) 衰减到 -20dB 时间 ===\n")
print(f"{'RR':>3} {'到-20dB ms':>11} {'相对RR=4':>9} {'sus_hold缩放':>12}")
print("-" * 42)
# harpsichord RR=4 是基准 (sus_hold scale=0.44 已对齐)
base = measure_emu_sustain(4)
for rr in range(1, 12):
    ms = measure_emu_sustain(rr)
    rel = ms/base if base else 0
    # sus_hold 缩放 = emu时间比 (RR=4 对应 scale=0.44)
    scale = 0.44 * rel if rel > 0 else 0.44
    print(f"{rr:>3} {ms:>11.0f} {rel:>9.2f} {scale:>12.3f}")

print(f"\n注: sus_hold 按 RR 缩放, scale = 0.44 × (emu时间[rr] / emu时间[4])")
print(f"vibraphone RR=2: 比 RR=4 慢, sus_hold 更大 (衰减更慢)")
