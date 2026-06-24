#!/usr/bin/env python3
"""干净对比 emu vs fw 的 carrier 输出量级 (抛开 render_one 的取负).

关键发现: render_one 返回 -(co>>1), emu 真正 carrier 输出 co 是大正值.
fw carrier 输出 = (wave×(level+1)×(tl+1))>>10 ≈ ±30.
两者差 100x, 是输出公式整体增益差异.

本脚本: 抓 emu 的 co (取负前) 和 fw 的 carrier 原始输出, 对比量级.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ym2413_wav_gen import (DEFAULT_INST, dump_to_patch, freq_to_fnum_blk,
                            EmuChannel, calc_envelope, calc_phase,
                            calc_slot_mod, calc_slot_car, INTERNAL_RATE)
from fw_real_sim import (fw_decode, fw_apply_patch, fw_key_on, fw_render_fm,
                         fw_calc_step)

dump = DEFAULT_INST[11]
mp, cp = dump_to_patch(dump)
ch = EmuChannel(mp, cp)
fn, bl = freq_to_fnum_blk(440.0)
ch.set_note(fn, bl); ch.set_volume(0); ch.set_sus(0); ch.key_on()

print("=== emu carrier 真实输出 co (calc_slot_car 返回, 取负前) ===")
print(f"{'s':>3} {'co(emu)':>8} {'|co|':>6}")
emu_cos = []
for i in range(40):
    ch.pm_phase = (ch.pm_phase + 1) & 0xffffffff
    ch.am_phase += 1
    from ym2413_wav_gen import am_table
    ch.lfo_am = am_table[(ch.am_phase >> 6) % len(am_table)]
    ch.eg_counter += 1
    calc_envelope(ch.mod, ch.eg_counter); calc_phase(ch.mod, ch.pm_phase)
    calc_envelope(ch.car, ch.eg_counter); calc_phase(ch.car, ch.pm_phase)
    mo = calc_slot_mod(ch.mod, ch.lfo_am)
    co = calc_slot_car(ch.car, mo, ch.lfo_am)
    emu_cos.append(co)
    if i < 24:
        print(f"{i:>3} {co:>8} {abs(co):>6}")

print(f"\nemu co peak={max(abs(x) for x in emu_cos)} mean|co|={sum(abs(x) for x in emu_cos)/len(emu_cos):.0f}")

# fw
p = fw_decode(dump)
mod, car = fw_apply_patch(p)
fn2, bl2 = freq_to_fnum_blk(440.0)
if bl2 > 0: bl2 -= 1
mod['step'] = fw_calc_step(fn2, bl2, mod['ml'])
car['step'] = fw_calc_step(fn2, bl2, car['ml'])
car['tl'] = max(0, min(31, (60-0)>>1))
fw_key_on(mod, car)
print(f"\n=== fw carrier 输出 (fw_render_fm 返回) ===")
print(f"{'s':>3} {'co(fw)':>8}")
fw_cos = []
wc = 0
for i in range(40):
    wc = (wc + 1) & 0x0F
    co = fw_render_fm(mod, car, wc, 0)
    fw_cos.append(co)
    if i < 24:
        print(f"{i:>3} {co:>8}")
print(f"\nfw co peak={max(abs(x) for x in fw_cos)} mean|co|={sum(abs(x) for x in fw_cos)/len(fw_cos):.0f}")

print(f"\n=== 量级比 ===")
import statistics
er = sum(abs(x) for x in emu_cos)/len(emu_cos)
fr = sum(abs(x) for x in fw_cos)/len(fw_cos)
print(f"emu mean|co| = {er:.0f}")
print(f"fw  mean|co| = {fr:.0f}")
print(f"增益比 emu/fw = {er/fr:.1f}x")
print(f"\nemu 输出公式: lookup_exp_table(h + (eg_out+tll)<<4), exp表满幅 ~32768")
print(f"fw  输出公式: (wave×(level+1)×(tl+1))>>10, wave±31 -> ~30")
print(f"\n结论: fw 输出动态范围太小 (±30 vs emu ±32768), 不是反馈问题,")
print(f"      是输出公式整体增益/动态范围不足. 但下位机 s8 输出本就有限,")
print(f"      关键是 fw 的 carrier 波形被 halfsin-mirror + 满tl 锁死在正值区间.")
