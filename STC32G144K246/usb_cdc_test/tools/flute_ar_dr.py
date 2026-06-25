#!/usr/bin/env python3
"""测 emu flute AR/DR 形态, 确定指数查表方案.

flute: car ar=6 dr=4 sl=2 rr=7 eg=1 (sustaining)
- AR: attack, level 0->31 (上升), emu 指数 (前期慢后期快? 或反之)
- DR: decay, level 31->sul=27 (下降 4 步), 但 emu 衰减形态指数

测 emu carrier attack/decay 阶段 eg_out 曲线, 看形态.
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ym2413_wav_gen import (DEFAULT_INST, dump_to_patch, freq_to_fnum_blk,
                            EmuChannel, calc_envelope, calc_phase,
                            calc_slot_mod, calc_slot_car, INTERNAL_RATE)
import fw_real_sim as F
from fw_real_sim import (fw_decode, fw_apply_patch, fw_key_on, fw_env_tick,
                         fw_calc_step, FW_ISR_RATE)

dump = DEFAULT_INST[4]

# emu: 抓 carrier eg_out + 输出
mp, cp = dump_to_patch(dump)
ch = EmuChannel(mp, cp)
fn, bl = freq_to_fnum_blk(440.0)
ch.set_note(fn, bl); ch.set_volume(0); ch.set_sus(0); ch.key_on()
from ym2413_wav_gen import am_table
emu_eg = []; emu_out = []
for i in range(int(0.5*INTERNAL_RATE)):
    ch.pm_phase = (ch.pm_phase+1)&0xffffffff; ch.am_phase += 1
    ch.lfo_am = am_table[(ch.am_phase>>6)%len(am_table)]
    ch.eg_counter += 1
    calc_envelope(ch.car, ch.eg_counter); calc_phase(ch.car, ch.pm_phase)
    calc_envelope(ch.mod, ch.eg_counter); calc_phase(ch.mod, ch.pm_phase)
    mo = calc_slot_mod(ch.mod, ch.lfo_am)
    co = calc_slot_car(ch.car, mo, ch.lfo_am)
    emu_eg.append(ch.car.eg_out); emu_out.append(co)

# eg_out 曲线 (attack 127->0, decay 0->SL对应值)
print("=== emu flute carrier eg_out 曲线 (前 300ms) ===")
seg = int(0.01*INTERNAL_RATE)
for ms in range(0, 300, 10):
    i = int(ms/1000*INTERNAL_RATE)
    eg = emu_eg[i]
    # eg_out 0=最大, 127=静音. 输出 ∝ 2^(-eg/某常数)
    print(f"  {ms:>4}ms eg_out={eg:>3}")

# fw: 抓 carrier level
p = fw_decode(dump); mod, car = fw_apply_patch(p)
fn, bl = freq_to_fnum_blk(440.0)
if bl > 0: bl -= 1
mod['step'] = fw_calc_step(fn, bl, mod['ml']); car['step'] = fw_calc_step(fn, bl, car['ml'])
car['tl'] = max(0, min(31, (60-0)>>1)); fw_key_on(mod, car)
fw_lvl = []
wc = 0
for i in range(int(0.5*FW_ISR_RATE)):
    wc = (wc+1) & 0x0F
    F.fw_render_fm(mod, car, wc, 0)
    fw_lvl.append(car['level'])

print("\n=== fw flute carrier level 曲线 (前 300ms) ===")
for ms in range(0, 300, 10):
    i = int(ms/1000*FW_ISR_RATE)
    print(f"  {ms:>4}ms level={fw_lvl[i]:>2}")

# emu attack 时间 (eg_out 127-><5) 和 decay (->SL=2 对应 eg_out 16)
print("\n=== AR/DR 时间对比 ===")
# emu attack 完成
t_atk = next((i for i,e in enumerate(emu_eg) if e < 5), -1)
print(f"emu attack 完成: {t_atk/INTERNAL_RATE*1000:.0f}ms (eg_out 127->5)")
# emu decay 到 SL=2 (eg_out 0->16)
t_dec = next((i for i in range(t_atk, len(emu_eg)) if emu_eg[i] >= 16), -1)
print(f"emu decay 到 SL=2: {(t_dec-t_atk)/INTERNAL_RATE*1000:.0f}ms (eg_out 5->16)")
# fw attack 完成
t_atk_fw = next((i for i,l in enumerate(fw_lvl) if l >= 31), -1)
print(f"fw  attack 完成: {t_atk_fw/FW_ISR_RATE*1000:.0f}ms (level->31)")
# fw decay 到 sul
sul = 0 if 2 >= 15 else (31 - 2*2)
t_dec_fw = next((i for i in range(t_atk_fw, len(fw_lvl)) if fw_lvl[i] <= sul), -1)
print(f"fw  decay 到 sul={sul}: {(t_dec_fw-t_atk_fw)/FW_ISR_RATE*1000:.0f}ms (level 31->{sul})")
