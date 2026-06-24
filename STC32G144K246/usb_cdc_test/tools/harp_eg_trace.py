#!/usr/bin/env python3
"""逐采样对比 emu eg_out vs fw level, 看包络哪个阶段分叉.

emu: eg_out 0=最大, 127=静音; fw: level 0=静音, 31=最大 (反向!)
为对比, emu 输出 = 127 - eg_out (翻转成 fw 方向), fw = level
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fw_real_sim as F
from ym2413_wav_gen import (DEFAULT_INST, dump_to_patch, freq_to_fnum_blk,
                            EmuChannel, calc_envelope, calc_phase,
                            calc_slot_mod, calc_slot_car, EG_MUTE, INTERNAL_RATE)
from fw_real_sim import (fw_decode, fw_apply_patch, fw_key_on, fw_env_tick,
                         fw_calc_step, FW_ISR_RATE)

dump = DEFAULT_INST[11]
N_MS = 400   # 看 0~400ms (decay+sustain 起始)

# ===== emu: 抓 car.eg_out 序列 =====
mp, cp = dump_to_patch(dump)
ch = EmuChannel(mp, cp)
fn, bl = freq_to_fnum_blk(440.0)
ch.set_note(fn, bl); ch.set_volume(0); ch.set_sus(0); ch.key_on()
from ym2413_wav_gen import am_table
emu_eg = []
n = int(N_MS/1000 * INTERNAL_RATE)
for i in range(n):
    ch.pm_phase = (ch.pm_phase + 1) & 0xffffffff
    ch.am_phase += 1
    ch.lfo_am = am_table[(ch.am_phase >> 6) % len(am_table)]
    ch.eg_counter += 1
    calc_envelope(ch.mod, ch.eg_counter); calc_phase(ch.mod, ch.pm_phase)
    calc_envelope(ch.car, ch.eg_counter); calc_phase(ch.car, ch.pm_phase)
    mo = calc_slot_mod(ch.mod, ch.lfo_am)
    calc_slot_car(ch.car, mo, ch.lfo_am)
    emu_eg.append(ch.car.eg_out)

# ===== fw: 抓 car.level 序列 =====
p = fw_decode(dump)
mod, car = fw_apply_patch(p)
fn, bl = freq_to_fnum_blk(440.0)
if bl > 0: bl -= 1
mod['step'] = fw_calc_step(fn, bl, mod['ml'])
car['step'] = fw_calc_step(fn, bl, car['ml'])
car['tl'] = max(0, min(31, (60-0)>>1))
fw_key_on(mod, car)
fw_lvl = []
nfw = int(N_MS/1000 * FW_ISR_RATE)
wc = 0
for i in range(nfw):
    wc = (wc+1) & 0x0F
    F.fw_render_fm(mod, car, wc, 0)
    fw_lvl.append(car['level'])

# ===== 对比 (归一化时间, 每 20ms 一个点) =====
print(f"=== harpsichord carrier 包络 eg_out/level 对比 (0~{N_MS}ms) ===")
print(f"emu: eg_out 0=最大,127=静音 -> 翻转 (127-eg_out) 对齐 fw 方向")
print(f"fw : level 0=静音,31=最大\n")
print(f"{'t_ms':>5} {'emu(127-eg)':>11} {'emu_state':>10} {'fw_level':>9} {'fw_state':>9} {'差':>5}")
print("-" * 60)

state_name = {0:'ATTACK',1:'DECAY',2:'SUSTAIN',3:'RELEASE',4:'DAMP'}
fw_state_name = {0:'idle',1:'attack',2:'decay',3:'sustain',4:'release'}

for ms in range(0, N_MS, 20):
    ie = int(ms/1000 * INTERNAL_RATE)
    iw = int(ms/1000 * FW_ISR_RATE)
    if ie >= len(emu_eg) or iw >= len(fw_lvl): break
    eg = emu_eg[ie]
    lvl = fw_lvl[iw]
    emu_norm = 127 - eg  # 翻转: 大=输出大
    # emu state (近似, 从 eg_out 变化推断)
    # 实际 state 在 ch.car.eg_state
    es = ch.car.eg_state if ie == len(emu_eg)-1 else '?'
    fw_s = fw_state_name.get(car['env_state'], '?')
    diff = emu_norm - lvl
    print(f"{ms:>5} {emu_norm:>11} {str(es):>10} {lvl:>9} {fw_s:>9} {diff:>+5}")
