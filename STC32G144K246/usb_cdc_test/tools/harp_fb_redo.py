#!/usr/bin/env python3
"""mute halfsin 下, 重新量化 emu vs fw 的反馈强度.

emu 反馈 (calc_slot_mod):
  fm = (output[1]+output[0]) >> (9-FB)    # FB=1 -> >>8
  output 来自 to_linear, 量级 ±32768
  -> 满幅 fm = (±65536)>>8 = ±256, 加到 pg_out (1024点表)

fw 反馈 (fw_render_fm):
  fb_val = ch_out >> FB                    # FB=1 -> >>1
  ch_out = (wave×(level+1)×(tl+1))>>10, 量级 ±30
  -> 满幅 fb_val = ±15, 加到 idx (64点表)

关键对比: 反馈量占周期比例
  emu: fm/PG_WIDTH = ±256/1024 = 25% (满幅)
  fw : fb_val/64   = ±15/64   = 23% (满幅)
比例接近! 但"满幅"前提不同:
  emu output 满幅要 eg_out=0 + tll=0 (mod TL=3 -> tll=6, 非零!)
  fw  ch_out 满幅要 level=31 + tl=30 (mod TL=3 -> tl=30, 几乎满!)

所以实际反馈强度:
  emu: mod 实际 output 受 (eg_out+tll) 衰减, 远小于满幅
  fw : mod 实际 ch_out 几乎满幅 (tl=30)

本脚本: 实测两者 mod 输出的归一化量级 + 反馈占周期比.
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fw_real_sim as F
from fw_real_sim import (fw_decode, fw_apply_patch, fw_key_on, fw_env_tick,
                         fw_calc_step, FW_SIN)
from ym2413_wav_gen import (DEFAULT_INST, NAMES, dump_to_patch, freq_to_fnum_blk,
                            EmuChannel, calc_envelope, calc_phase,
                            calc_slot_mod, calc_slot_car, PG_WIDTH, INTERNAL_RATE)

dump = DEFAULT_INST[11]
N = 200

# ============ emu: 抓 mod output + fm ============
mp, cp = dump_to_patch(dump)
ch = EmuChannel(mp, cp)
fn, bl = freq_to_fnum_blk(440.0)
ch.set_note(fn, bl); ch.set_volume(0); ch.set_sus(0); ch.key_on()
from ym2413_wav_gen import am_table
emu_mod_out = []
emu_fm = []
for i in range(N):
    ch.pm_phase = (ch.pm_phase + 1) & 0xffffffff
    ch.am_phase += 1
    ch.lfo_am = am_table[(ch.am_phase >> 6) % len(am_table)]
    ch.eg_counter += 1
    calc_envelope(ch.mod, ch.eg_counter); calc_phase(ch.mod, ch.pm_phase)
    calc_envelope(ch.car, ch.eg_counter); calc_phase(ch.car, ch.pm_phase)
    # calc_slot_mod 内部 fm (更新前)
    fm = ((ch.mod.output[1] + ch.mod.output[0]) >> (9 - ch.mod.patch.FB)
          if ch.mod.patch.FB > 0 else 0)
    mo = calc_slot_mod(ch.mod, ch.lfo_am)
    calc_slot_car(ch.car, mo, ch.lfo_am)
    emu_mod_out.append(mo)
    emu_fm.append(fm)

# ============ fw: 抓 mod ch_out + fb_val (mute halfsin) ============
p = fw_decode(dump)
mod, car = fw_apply_patch(p)
fn, bl = freq_to_fnum_blk(440.0)
if bl > 0: bl -= 1
mod['step'] = F.fw_calc_step(fn, bl, mod['ml'])
car['step'] = F.fw_calc_step(fn, bl, car['ml'])
car['tl'] = max(0, min(31, (60-0)>>1))
car['wave'] = list(FW_SIN[:32]) + [0]*32   # mute halfsin
fw_key_on(mod, car)
fw_chout = []
fw_fbval = []
wc = 0
for i in range(N):
    wc = (wc+1) & 0x0F
    # 复制 fw_render_fm 的 mod 部分, 抓 ch_out 和 fb_val
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
    # car 部分 (推进 car 相位, 不影响 mod 数据)
    car['pos'] = (car['pos'] + car['step']) & 0xFFFFFFFF
    cidx = (car['pos'] >> 16) & 0x3F
    cidx = (cidx + (mch & 0xFF)) & 0x3F
    cwave = car['wave'][cidx]
    if wc == 0: fw_env_tick(car)
    cch = ((cwave * (car['level']+1) * (car['tl']+1)) >> 10)
    if cch > 127: cch = 127
    elif cch < -128: cch = -128
    fw_chout.append(mch)
    fw_fbval.append(mod['fb_val'])

def stats(a): return (max(abs(x) for x in a), sum(abs(x) for x in a)/len(a))

ep, em = stats(emu_mod_out)
fp, fm_ = stats(fw_chout)
efp, efm = stats(emu_fm)
ffp, ffm = stats(fw_fbval)

print(f"=== harpsichord mod 输出 + 反馈量级 (前{N}采样) ===\n")
print(f"{'指标':<24} {'emu':>10} {'fw':>10} {'比':>8}")
print("-" * 56)
print(f"{'mod 输出 peak':<24} {ep:>10} {fp:>10} {ep/fp:>8.1f}")
print(f"{'mod 输出 mean|x|':<24} {em:>10.1f} {fm_:>10.1f} {em/fm_:>8.1f}")
print(f"{'反馈量(fm/fb_val) peak':<24} {efp:>10} {ffp:>10} {efp/max(ffp,1):>8.1f}")
print(f"{'反馈量 mean|x|':<24} {efm:>10.1f} {ffm:>10.1f} {efm/max(ffm,1):>8.1f}")

print(f"\n=== 反馈占周期比 (关键!) ===")
print(f"  emu: fm/PG_WIDTH = ±{efp}/{PG_WIDTH} = {efp/PG_WIDTH*100:.1f}% (peak)")
print(f"  fw : fb_val/64   = ±{ffp}/64 = {ffp/64*100:.1f}% (peak)")
print(f"  emu mean: {efm/PG_WIDTH*100:.2f}%")
print(f"  fw  mean: {ffm/64*100:.2f}%")

print(f"\n=== mod 衰减对比 (TL=3) ===")
print(f"  emu mod: TL=3 -> tll=TL2EG(3)=6 (EG单位, 满EG_MUTE=127)")
print(f"           实际 eg_out+sul 影响, mod output peak={ep} (满幅32768的 {ep/32768*100:.1f}%)")
print(f"  fw  mod: TL=3 -> tl=31-(3>>1)=30 (满31)")
print(f"           ch_out peak={fp} (满幅~30的 {fp/30*100:.0f}%)")

print(f"\n=== 结论 ===")
fw_ratio = ffm/64*100
emu_ratio = efm/PG_WIDTH*100
print(f"  fw 反馈占周期 {fw_ratio:.1f}% vs emu {emu_ratio:.2f}%")
print(f"  若 fw >> fw, 说明反馈过强 (过反馈)")
print(f"  修复方向: 增大反馈移位 (fb_val = ch_out >> N, N>1)")
