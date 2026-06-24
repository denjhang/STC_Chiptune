#!/usr/bin/env python3
"""验证修正A (mod.tl = tl_raw>>1 不反相) 能否对齐 emu 反馈强度.

mute halfsin + mod.tl=tl_raw>>1 下, 重新测反馈占周期比.
目标: fw 反馈占周期 ~1.2% (peak), 接近 emu.
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fw_real_sim as F
from fw_real_sim import (fw_decode, fw_apply_patch, fw_key_on, fw_env_tick,
                         fw_calc_step, FW_SIN, FW_HALFSIN)
from ym2413_wav_gen import (DEFAULT_INST, NAMES, dump_to_patch, freq_to_fnum_blk,
                            EmuChannel, calc_envelope, calc_phase,
                            calc_slot_mod, calc_slot_car, PG_WIDTH,
                            render_emu2413, save_wav)

dump = DEFAULT_INST[11]
N = 200
FREQ = 440.0
DUR_KO, DUR_KF = 1.0, 1.0

# ============ emu 参考 ============
mp, cp = dump_to_patch(dump)
ch = EmuChannel(mp, cp)
fn, bl = freq_to_fnum_blk(FREQ)
ch.set_note(fn, bl); ch.set_volume(0); ch.set_sus(0); ch.key_on()
from ym2413_wav_gen import am_table
emu_mod_out = []
for i in range(N):
    ch.pm_phase = (ch.pm_phase + 1) & 0xffffffff
    ch.am_phase += 1
    ch.lfo_am = am_table[(ch.am_phase >> 6) % len(am_table)]
    ch.eg_counter += 1
    calc_envelope(ch.mod, ch.eg_counter); calc_phase(ch.mod, ch.pm_phase)
    calc_envelope(ch.car, ch.eg_counter); calc_phase(ch.car, ch.pm_phase)
    mo = calc_slot_mod(ch.mod, ch.lfo_am)
    calc_slot_car(ch.car, mo, ch.lfo_am)
    emu_mod_out.append(mo)

# ============ fw 渲染函数 (可调 mod.tl 映射) ============
def render_fw(tl_mode, label):
    p = fw_decode(dump)
    mod, car = fw_apply_patch(p)
    # mod.tl 映射
    if tl_mode == 'inv':
        mod['tl'] = max(0, min(31, 31 - (p['mod_tl'] >> 1)))   # 现状
    elif tl_mode == 'direct':
        mod['tl'] = max(0, min(31, p['mod_tl'] >> 1))          # 修正A
    elif tl_mode == 'half':
        mod['tl'] = max(0, min(31, p['mod_tl']))               # TL直传 (TL=3->3)
    fn, bl = freq_to_fnum_blk(FREQ)
    if bl > 0: bl -= 1
    mod['step'] = fw_calc_step(fn, bl, mod['ml'])
    car['step'] = fw_calc_step(fn, bl, car['ml'])
    car['tl'] = max(0, min(31, (60-0)>>1))
    # mute halfsin (已修复)
    car['wave'] = list(FW_SIN[:32]) + [0]*32
    if p['mod_ws']:
        mod['wave'] = list(FW_SIN[:32]) + [0]*32
    fw_key_on(mod, car)
    # 抓 mod ch_out 序列
    chouts = []
    wc = 0
    out = []
    for i in range(int((DUR_KO+DUR_KF)*F.INTERNAL_RATE)):
        if i == int(DUR_KO*F.INTERNAL_RATE):
            F.fw_key_off(mod, car)
        wc = (wc+1) & 0x0F
        # mod
        mod['pos'] = (mod['pos'] + mod['step']) & 0xFFFFFFFF
        midx = (mod['pos'] >> 16) & 0x3F
        midx = (midx + (mod['fb_val'] & 0xFF)) & 0x3F
        mwave = mod['wave'][midx]
        if wc == 0: fw_env_tick(mod)
        mch = ((mwave * (mod['level']+1) * (mod['tl']+1)) >> 10)
        if mch > 127: mch = 127
        elif mch < -128: mch = -128
        if mod['fb'] > 0:
            mod['fb_val'] = max(-128, min(127, mch >> mod['fb']))
        else:
            mod['fb_val'] = 0
        # car
        car['pos'] = (car['pos'] + car['step']) & 0xFFFFFFFF
        cidx = (car['pos'] >> 16) & 0x3F
        cidx = (cidx + (mch & 0xFF)) & 0x3F
        cwave = car['wave'][cidx]
        if wc == 0: fw_env_tick(car)
        cch = ((cwave * (car['level']+1) * (car['tl']+1)) >> 10)
        if cch > 127: cch = 127
        elif cch < -128: cch = -128
        total = cch << 1
        if total > 32767: total = 32767
        elif total < -32768: total = -32768
        out.append(total)
        if i < N: chouts.append((mch, mod['fb_val']))
    return out, chouts

def rms(s): return (sum(x*x for x in s)/max(len(s),1))**0.5
def meanabs(a): return sum(abs(x) for x in a)/max(len(a),1)

# emu 全曲参考
emu_full = render_emu2413(11, FREQ, DUR_KO, DUR_KF, 0)

print(f"=== harpsichord mod.tl 映射扫描 (mute halfsin) ===\n")
print(f"{'映射':<10} {'mod.tl':>6} | {'mod_chout_pk':>12} {'反馈占周期%':>12} | {'fw_RMS':>8} {'dB_vs_emu':>9}")
print("-" * 72)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wav_fb_fix")
os.makedirs(OUT, exist_ok=True)
save_wav(os.path.join(OUT, "harp_emu.wav"), emu_full)

for mode, label in [('inv','31-(TL>>1)现'), ('direct','TL>>1 修正A'), ('half','TL直传')]:
    out, chouts = render_fw(mode, label)
    mch_pk = max(abs(c[0]) for c in chouts)
    fb_pk = max(abs(c[1]) for c in chouts)
    fb_ratio = fb_pk/64*100
    r = rms(out)
    d = 20*math.log10(r/rms(emu_full)) if r > 0 and rms(emu_full) > 0 else -99
    print(f"{label:<10} {dump[2]&63:>6} | {mch_pk:>12} {fb_ratio:>11.1f}% | {r:>8.1f} {d:>+9.2f}")
    save_wav(os.path.join(OUT, f"harp_{mode}.wav"), out)

# emu 反馈占周期参考
emu_fb_pk = 12  # 之前测的
print(f"\n{'emu参考':<10} {'tll=6':>6} | {'1644(5%)':>12} {emu_fb_pk/PG_WIDTH*100:>11.1f}% | {rms(emu_full):>8.1f} {0.0:>+9.2f}")
print(f"\n目标: fw 反馈占周期接近 emu 的 {emu_fb_pk/PG_WIDTH*100:.1f}%")
