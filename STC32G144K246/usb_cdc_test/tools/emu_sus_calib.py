#!/usr/bin/env python3
"""测 emu SUSTAIN 阶段 (non-sus, RR=4) 的衰减, 反推 fw SUSTAIN 该用的 cnt.

emu: non-sustaining(EG=0), SUSTAIN 阶段用 RR 速率, eg_out 持续递增.
     SL=0 -> decay 瞬间跳过, attack 后直接进 SUSTAIN.
     测 eg_out 从 ~0 到 各 dB 点 的时间.

fw : SUSTAIN 阶段 level 线性递减, 每步 cnt.
     线性衰减 vs emu 指数衰减 -> 用中段(-12dB附近)对齐.
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ym2413_wav_gen import (DEFAULT_INST, dump_to_patch, freq_to_fnum_blk,
                            EmuChannel, calc_envelope, calc_phase, EG_MUTE, INTERNAL_RATE)
from fw_real_sim import FW_ISR_RATE

ISR = FW_ISR_RATE

def emu_sustain_decay(rr_val):
    """carrier SL=0/EG=0/RR=n, 测 attack 后 eg_out 0->各点时间."""
    mp, cp = dump_to_patch(DEFAULT_INST[11])
    cp.RR = rr_val; cp.EG = 0; cp.SL = 0
    ch = EmuChannel(mp, cp)
    fn, bl = freq_to_fnum_blk(440.0)
    ch.set_note(fn, bl); ch.set_volume(0); ch.set_sus(0); ch.key_on()
    from ym2413_wav_gen import am_table
    eg = []
    for i in range(int(2.0*INTERNAL_RATE)):
        ch.pm_phase = (ch.pm_phase + 1) & 0xffffffff
        ch.am_phase += 1
        ch.lfo_am = am_table[(ch.am_phase >> 6) % len(am_table)]
        ch.eg_counter += 1
        calc_envelope(ch.car, ch.eg_counter)
        calc_phase(ch.car, ch.pm_phase)
        eg.append(ch.car.eg_out)
    eg_min = min(eg)
    t0 = next(i for i,e in enumerate(eg) if e <= eg_min+1)
    # eg_out 0=最大,127=静音. dB = -eg_out × (24/64) 近似 (emu eg 6dB/8步)
    # 找 eg_out 到 各阈值 的时间
    result = {}
    for thresh, label in [(16,'-12dB估'),(32,'-24dB估'),(64,'-48dB估'),(120,'近静音')]:
        try:
            t = next(i for i in range(t0,len(eg)) if eg[i]>=thresh)
            result[label] = (t-t0)/INTERNAL_RATE*1000
        except StopIteration:
            result[label] = 9999
    return result

print(f"=== emu SUSTAIN(RR=n) 衰减时间 + fw 反推 cnt ===\n")
# fw: SUSTAIN level 31->0 线性, 31步×cnt×16/ISR
# 对齐 emu -12dB(近似 level 24) 和 近静音(level 0)
print(f"fw SUSTAIN: level 线性 31->0, 时间 = 31步×cnt×16/{ISR}")
print(f"emu eg_out: 0=最大, 指数域线性\n")
print(f"{'RR':>3} {'emu -12dB':>10} {'emu 静音':>10} {'fw cnt(-12dB)':>13} {'fw cnt(静音)':>12}")
print("-" * 55)
for rr in [4, 5, 6, 7, 8]:
    r = emu_sustain_decay(rr)
    # fw level 对应 emu eg_out: level 31->0 映射 eg_out 0->127
    # -12dB ≈ level 降到 ~7.75 (31×0.5^0.5? 不对, 线性 level 的 dB)
    # fw 输出 ∝ level+1, -12dB = level+1 = 32×10^(-12/20)=8 -> level≈-24? 不对
    # 实际 fw 输出 = wave×(level+1)×(tl+1)>>10, 线性于 level. -12dB -> level = 31×0.25=7.75
    # level 31->8 = 23步
    cnt_12 = r['-12dB估'] * ISR / (23 * 16 * 1000) if r['-12dB估']<9999 else 255
    cnt_end = r['近静音'] * ISR / (31 * 16 * 1000) if r['近静音']<9999 else 255
    cnt_12 = max(1, min(255, round(cnt_12)))
    cnt_end = max(1, min(255, round(cnt_end)))
    print(f"{rr:>3} {r['-12dB估']:>10.0f} {r['近静音']:>10.0f} {cnt_12:>13} {cnt_end:>12}")

print(f"\n注: 线性衰减 cnt 取值在 -12dB 和 静音 之间不同 (线性 vs 指数差异)")
print(f"harpsichord RR=4: SUSTAIN 阶段 cnt 应在两者间取折中")
