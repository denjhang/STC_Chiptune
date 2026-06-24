#!/usr/bin/env python3
"""测 emu 各 RR 档位下 release (keyoff后) 的实际时间, 反推 rel_hold 按 RR 缩放.

emu: keyoff 后 RELEASE 阶段, non-sus 用速率7, 但实际输出曲线因 eg_out 起点不同.
直接测: 构造 carrier SL=0/EG=0/RR=n, keyon 后等 level 稳定, keyoff, 测 release 时间.
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ym2413_wav_gen import (DEFAULT_INST, dump_to_patch, freq_to_fnum_blk,
                            EmuChannel, calc_envelope, calc_phase,
                            calc_slot_mod, calc_slot_car, EG_MUTE, INTERNAL_RATE)

ISR = 22050

def measure_emu_release(rr_val):
    """测 keyoff 后 carrier 输出从稳定到 -40dB 的时间 (各 RR)."""
    mp, cp = dump_to_patch(DEFAULT_INST[12])  # vibraphone 基础
    cp.RR = rr_val; cp.EG = 0; cp.SL = 1  # non-sus, 类似 vibraphone
    ch = EmuChannel(mp, cp)
    fn, bl = freq_to_fnum_blk(440.0)
    ch.set_note(fn, bl); ch.set_volume(0); ch.set_sus(0); ch.key_on()
    from ym2413_wav_gen import am_table
    outs = []
    keyoff_samp = int(0.5 * INTERNAL_RATE)  # 0.5s 后 keyoff
    for i in range(int(2.0*INTERNAL_RATE)):
        if i == keyoff_samp:
            ch.key_off()
        ch.pm_phase = (ch.pm_phase+1)&0xffffffff; ch.am_phase += 1
        ch.lfo_am = am_table[(ch.am_phase>>6)%len(am_table)]
        ch.eg_counter += 1
        calc_envelope(ch.mod, ch.eg_counter); calc_phase(ch.mod, ch.pm_phase)
        calc_envelope(ch.car, ch.eg_counter); calc_phase(ch.car, ch.pm_phase)
        mo = calc_slot_mod(ch.mod, ch.lfo_am)
        co = calc_slot_car(ch.car, mo, ch.lfo_am)
        outs.append(co)
    # keyoff 时刻的 RMS (峰值参考)
    ko = keyoff_samp
    seg = int(0.02*INTERNAL_RATE)
    peak_rms = (sum(x*x for x in outs[ko-seg:ko])/seg)**0.5
    # 找 keyoff 后降到 -40dB 的时间
    target = peak_rms * 0.01  # -40dB
    for i in range(ko, len(outs)-seg, seg//2):
        s = outs[i:i+seg]
        r = (sum(x*x for x in s)/len(s))**0.5
        if r <= target:
            return (i - ko)/INTERNAL_RATE*1000
    return 9999

print(f"=== emu 各 RR 档位 release 时间 (keyoff->-40dB) ===\n")
print(f"{'RR':>3} {'release_ms':>11} {'相对RR=7':>9}")
print("-" * 28)
base_ms = None
for rr in range(1, 12):
    ms = measure_emu_release(rr)
    if rr == 7: base_ms = ms
    rel = ms/base_ms if base_ms and ms < 9999 else 0
    print(f"{rr:>3} {ms:>11.0f} {rel:>9.2f}")
print(f"\n注: RR 小=慢 release (长尾巴), RR 大=快.")
print(f"vibraphone RR=2, 应该 release 很长.")
print(f"当前 fw rel_hold 固定 (sus_hold//10), 不分 RR -> RR=2 被快关.")
