#!/usr/bin/env python3
"""过反馈解耦分析: FB运算 vs mod_tl运算 各自贡献多少.

harpsichord FB=1, mod_tl=3.
emu:
  FB: fm = (out0+out1) >> (9-FB), out 是 to_linear 输出(±32768), 作用于 pg_out(1024表)
  mod tl: tll = TL2EG(TL) = TL<<1 = 6 (EG单位, mod output 受 eg_out+tll 衰减)
fw:
  FB: fb_val = ch_out >> FB, ch_out=(wave×(level+1)×(tl+1))>>10 (±30), 作用于 idx(64表)
  mod tl: tl = 31-(tl_raw>>1) = 30 (满, mod 几乎不衰减)

分别测:
A. FB 移位等效: emu >>8 on 1024表 vs fw >>1 on 64表, 哪个反馈占周期大
B. mod 输出量级: emu 5% vs fw 93%, 差 18×
看两个因素分别贡献多少, 以及能否简单调参对齐.
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fw_real_sim as F
from fw_real_sim import (fw_decode, fw_apply_patch, fw_key_on, fw_env_tick,
                         fw_calc_step, FW_ISR_RATE, FW_SIN)
from ym2413_wav_gen import (DEFAULT_INST, dump_to_patch, freq_to_fnum_blk,
                            EmuChannel, calc_envelope, calc_phase,
                            calc_slot_mod, calc_slot_car, PG_WIDTH, INTERNAL_RATE)

dump = DEFAULT_INST[11]
N = 300

# ============ emu: 抓 mod output, fm, car idx 偏移 ============
mp, cp = dump_to_patch(dump)
ch = EmuChannel(mp, cp)
fn, bl = freq_to_fnum_blk(440.0)
ch.set_note(fn, bl); ch.set_volume(0); ch.set_sus(0); ch.key_on()
from ym2413_wav_gen import am_table
emu_mod_out = []; emu_fm = []
for i in range(N):
    ch.pm_phase = (ch.pm_phase+1)&0xffffffff; ch.am_phase += 1
    ch.lfo_am = am_table[(ch.am_phase>>6)%len(am_table)]
    ch.eg_counter += 1
    calc_envelope(ch.mod, ch.eg_counter); calc_phase(ch.mod, ch.pm_phase)
    calc_envelope(ch.car, ch.eg_counter); calc_phase(ch.car, ch.pm_phase)
    fm = (ch.mod.output[1]+ch.mod.output[0])>>(9-ch.mod.patch.FB) if ch.mod.patch.FB>0 else 0
    mo = calc_slot_mod(ch.mod, ch.lfo_am)
    calc_slot_car(ch.car, mo, ch.lfo_am)
    emu_mod_out.append(mo); emu_fm.append(fm)

# ============ fw: 抓 mod ch_out, fb_val ============
p = fw_decode(dump); mod, car = fw_apply_patch(p)
fn, bl = freq_to_fnum_blk(440.0)
if bl > 0: bl -= 1
mod['step'] = fw_calc_step(fn, bl, mod['ml']); car['step'] = fw_calc_step(fn, bl, car['ml'])
car['tl'] = max(0, min(31, (60-0)>>1))
fw_key_on(mod, car)
fw_chout = []; fw_fbval = []
wc = 0
for i in range(N):
    wc = (wc+1) & 0x0F
    mod['pos'] = (mod['pos']+mod['step']) & 0xFFFF
    midx = ((mod['pos']>>8)+(mod['fb_val']&0xFF)) & 0x3F
    mw = mod['wave'][midx]
    if wc == 0: fw_env_tick(mod)
    mch = max(-128, min(127, (mw*(mod['level']+1)*(mod['tl']+1))>>10))
    if mod['fb']>0: mod['fb_val'] = max(-128, min(127, mch>>mod['fb']))
    else: mod['fb_val'] = 0
    car['pos'] = (car['pos']+car['step']) & 0xFFFF
    cidx = ((car['pos']>>8)+(mch&0xFF)) & 0x3F
    cw = car['wave'][cidx]
    if wc == 0: fw_env_tick(car)
    fw_chout.append(mch); fw_fbval.append(mod['fb_val'])

def meanabs(a): return sum(abs(x) for x in a)/max(len(a),1)
def peak(a): return max(abs(x) for x in a)

print(f"=== 过反馈解耦分析 (harpsichord, FB=1, mod_tl=3) ===\n")

# 因素 A: FB 运算 (移位 + 表大小)
print(f"--- 因素 A: FB 运算 (反馈占周期比) ---")
emu_fb_ratio = meanabs(emu_fm) / PG_WIDTH * 100
fw_fb_ratio = meanabs(fw_fbval) / 64 * 100
print(f"  emu: fm={meanabs(emu_fm):.1f} / {PG_WIDTH} = {emu_fb_ratio:.2f}% (mean)")
print(f"  fw : fb_val={meanabs(fw_fbval):.1f} / 64 = {fw_fb_ratio:.2f}% (mean)")
print(f"  FB 运算差异: fw/emu = {fw_fb_ratio/emu_fb_ratio:.1f}x")
print(f"  emu: (out0+out1)>>(9-1)= out_sum>>8, out±32768 -> fm±256")
print(f"  fw : ch_out>>1, ch_out±30 -> fb_val±15")

# 因素 B: mod 输出量级 (mod tl 衰减)
print(f"\n--- 因素 B: mod 输出量级 (mod tl 衰减) ---")
emu_mod_pk = peak(emu_mod_out); fw_mod_pk = peak(fw_chout)
print(f"  emu: mod output peak={emu_mod_pk} (满幅32768的 {emu_mod_pk/32768*100:.1f}%)")
print(f"  fw : mod ch_out peak={fw_mod_pk} (满幅~30的 {fw_mod_pk/30*100:.0f}%)")
print(f"  emu mod TL=3 -> tll=TL2EG(3)=6 (EG单位), mod output 5% (重衰减)")
print(f"  fw  mod TL=3 -> tl=31-(3>>1)=30 (满), mod output 93% (几乎不衰减)")

# 综合反馈强度 = mod输出 × FB增益
print(f"\n--- 综合: 实际反馈调制量 ---")
# emu: fm 加到 pg_out(1024), 占周期 = fm/1024
# fw: fb_val 加到 idx(64), 占周期 = fb_val/64
# 但 fw 的 fb_val = ch_out>>1, ch_out 是 mod 输出
# 综合看 mod 输出 × FB 增益 的乘积
emu_prod = (emu_mod_pk/32768) * (1/256 * PG_WIDTH/PG_WIDTH)  # 归一化
fw_prod = (fw_mod_pk/30) * (1/2 * 64/64)
print(f"  emu: mod_ratio(5%) × FB增益(>>8) = {(emu_mod_pk/32768):.3f}")
print(f"  fw : mod_ratio(93%) × FB增益(>>1) = {(fw_mod_pk/30):.3f}")
print(f"  综合比 fw/emu = {(fw_mod_pk/30)/(emu_mod_pk/32768):.1f}x")

print(f"\n=== 能否简单调参对齐? ===")
print(f"要 fw 反馈强度 = emu:")
print(f"  方案1: 改 FB 移位基数. fw 现在 >>FB(FB=1>>1), 改 >>>(FB+4) 则 FB=1>>5")
fb_shift_need = 1
while (fw_mod_pk/30) / (2**fb_shift_need) * 64/64 > (emu_mod_pk/32768) * 1.1:
    fb_shift_need += 1
print(f"    需要 >>{fb_shift_need} (FB=1时) 让 fw 反馈 ≈ emu")
print(f"    即 fb_val = ch_out >> (FB + {fb_shift_need-1})")
print(f"  方案2: 改 mod tl 映射. fw 现在 31-(tl>>1), mod 几乎不衰减")
fw_tl_need = 30
while (fw_mod_pk * (fw_tl_need+1)/(30+1) / 30) > (emu_mod_pk/32768 * 1.1):
    fw_tl_need -= 1
    if fw_tl_need < 0: break
print(f"    mod tl 从 30 降到 {fw_tl_need} 让 mod 输出 ≈ emu 5%")
print(f"\n注: 两个方案都'简单调参', 但影响所有乐器. 需验证其他乐器不被破坏.")
