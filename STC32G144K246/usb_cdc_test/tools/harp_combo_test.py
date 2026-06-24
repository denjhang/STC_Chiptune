#!/usr/bin/env python3
"""组合验证: halfsin后半周静音 + 看 carrier 索引分布, 能否复现 emu 脉冲形态.

emu carrier: HALFSIN, 后半周(idx>=512)=4095静音, 经 to_linear -> 0
  carrier idx = (pg_out + 2*(fm>>1)) & 1023
  fm = modulator 输出 (FULLSIN, 有正负)
  -> mod 调制让 carrier idx 在 0~1023 摆动, 落到 >=512 就静音 -> 脉冲

fw carrier: halfsin-mirror, 后半周(idx>=32)也是正值
  carrier idx = (mod_pos>>16 + ch_out) & 0x3F
  ch_out = modulator 输出
  -> 永远正值, 永远有输出 -> 直流偏置

验证方案: fw halfsin 后半周置0 (mute), 看 carrier idx 是否能落到 >=32
关键: mod 的 ch_out 量级 (±30) 加到 64 点 idx 上, 能否推过 32?
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fw_real_sim as F
from fw_real_sim import (fw_decode, fw_apply_patch, fw_key_on, fw_env_tick,
                         fw_calc_step, FW_SIN)
from ym2413_wav_gen import (DEFAULT_INST, dump_to_patch, freq_to_fnum_blk,
                            EmuChannel, calc_envelope, calc_phase,
                            calc_slot_mod, calc_slot_car, INTERNAL_RATE, save_wav)

dump = DEFAULT_INST[11]

# ============ 抓 emu carrier idx 分布 ============
mp, cp = dump_to_patch(dump)
ch = EmuChannel(mp, cp)
fn, bl = freq_to_fnum_blk(440.0)
ch.set_note(fn, bl); ch.set_volume(0); ch.set_sus(0); ch.key_on()
from ym2413_wav_gen import am_table
emu_idx = []
for i in range(200):
    ch.pm_phase = (ch.pm_phase + 1) & 0xffffffff
    ch.am_phase += 1
    ch.lfo_am = am_table[(ch.am_phase >> 6) % len(am_table)]
    ch.eg_counter += 1
    calc_envelope(ch.mod, ch.eg_counter); calc_phase(ch.mod, ch.pm_phase)
    calc_envelope(ch.car, ch.eg_counter); calc_phase(ch.car, ch.pm_phase)
    mo = calc_slot_mod(ch.mod, ch.lfo_am)
    # car idx (calc_slot_car 内部)
    car_idx = (ch.car.pg_out + 2*(mo>>1)) & 1023
    calc_slot_car(ch.car, mo, ch.lfo_am)
    emu_idx.append(car_idx)
emu_silent = sum(1 for x in emu_idx if x >= 512)
print(f"=== emu carrier idx 分布 (前200采样) ===")
print(f"  idx 范围: {min(emu_idx)}~{max(emu_idx)} (PG_WIDTH=1024)")
print(f"  落到静音区(>=512): {emu_silent}/200 = {emu_silent/2:.0f}%")
print(f"  -> emu carrier 有 {emu_silent/2:.0f}% 采样静音, 形成脉冲")

# ============ 抓 fw carrier idx 分布 (mute halfsin) ============
p = fw_decode(dump)
mod, car = fw_apply_patch(p)
fn2, bl2 = freq_to_fnum_blk(440.0)
if bl2 > 0: bl2 -= 1
mod['step'] = fw_calc_step(fn2, bl2, mod['ml'])
car['step'] = fw_calc_step(fn2, bl2, car['ml'])
car['tl'] = max(0, min(31, (60-0)>>1))
fw_key_on(mod, car)
# 用 mute halfsin
car['wave'] = list(FW_SIN[:32]) + [0]*32
fw_idx = []
fw_chout = []
wc = 0
for i in range(200):
    wc = (wc+1) & 0x0F
    # 复制 fw_render_fm 逻辑, 抓 idx
    if mod['step'] == 0: continue
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
    else: mod['fb_val'] = 0
    car['pos'] = (car['pos'] + car['step']) & 0xFFFFFFFF
    cidx = (car['pos'] >> 16) & 0x3F
    cidx = (cidx + (mch & 0xFF)) & 0x3F   # 注意: mch 是 s8, &0xFF 转无符号
    cwave = car['wave'][cidx]
    if wc == 0: fw_env_tick(car)
    cch = ((cwave * (car['level']+1) * (car['tl']+1)) >> 10)
    if cch > 127: cch = 127
    elif cch < -128: cch = -128
    fw_idx.append(cidx)
    fw_chout.append(cch)

fw_silent = sum(1 for x in fw_idx if x >= 32)
print(f"\n=== fw carrier idx 分布 (mute halfsin, 前200采样) ===")
print(f"  idx 范围: {min(fw_idx)}~{max(fw_idx)} (64点表)")
print(f"  落到静音区(>=32): {fw_silent}/200 = {fw_silent/2:.0f}%")
print(f"  mod ch_out(mch) 让 idx 偏移量: 看 cidx 是否能超过 32")
print(f"  carrier 原始 pos 索引 (无调制): {(car['pos']>>16)&0x3F}")

print(f"\n=== 关键诊断 ===")
# carrier 自身相位推进的 idx (无调制) 分布
car_base = []
for i in range(200):
    base_idx = int((i * (car['step'] & 0xFFFFFFFF)) >> 16) & 0x3F
    car_base.append(base_idx)
print(f"  carrier 自身 idx (无调制, 200步): 范围 {min(car_base)}~{max(car_base)}")
print(f"  mod mch 量级 (加到 idx): ±{max(abs(x) for x in [((mod['wave'][(mod['pos']>>16)&0x3F]*(mod['level']+1)*(mod['tl']+1))>>10) for _ in range(1)])}")
# 实际 mch 分布
print(f"  实际 mod mch: 需在循环里抓")
print(f"\n结论预判:")
print(f"  fw carrier 64点表, 自身相位 1周期=64点, 22050Hz下440Hz约50采样/周期")
print(f"  carrier idx 自然覆盖 0~63 (整周期), 后半周(32~63) mute 会产生静音段")
print(f"  但 mod 调制 mch(±30) 加到 idx 上会扭曲相位 -> 这才是过反馈/失真")
