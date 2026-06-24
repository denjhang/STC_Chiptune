#!/usr/bin/env python3
"""逐采样对比 emu2413 vs fw_real 的 mod 输出/反馈量, 定位 harpsichord 过反馈.

emu: calc_slot_mod 用 (output[1]+output[0])>>(9-FB), FB=1 -> >>8
     to_linear 经指数表, 输出 int16 (±32768)
     mod 衰减: eg_out(0~127) + tll(TL2EG(TL)=TL<<1, TL=3->6, KL=2 还加 key-scale)
fw : fb_val = ch_out >> FB, ch_out=(wave×(level+1)×(tl+1))>>10, FB=1 -> >>1
     mod.tl = 31 - (mod_tl>>1) = 31 - 1 = 30 (几乎满!)
     输出范围 ±30 左右

关键怀疑: fw 的 mod.tl 映射 (31 - tl/2) 让 TL=3 几乎无衰减 (tl=30),
而 emu 的 TL=3 -> tll=6 (EG单位, 127 满) 衰减很大.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ym2413_wav_gen import (DEFAULT_INST, NAMES, dump_to_patch, freq_to_fnum_blk,
                            EmuChannel, PG_WIDTH, DP_BASE_BITS, EG_MUTE, TLL_TABLE)
from fw_real_sim import (fw_decode, fw_apply_patch, fw_key_on, fw_render_fm,
                         fw_calc_step)

INST = 11
FREQ = 440.0
N = 64   # 打印前 N 个采样

print(f"=== Inst {INST}: {NAMES[INST]} | {FREQ}Hz | 前{N}采样 ===")
dump = DEFAULT_INST[INST]
print(f"dump: {['0x%02X'%b for b in dump]}")

# ---------------- emu ----------------
mod_patch, car_patch = dump_to_patch(dump)
print(f"\n[emu] mod patch: ML={mod_patch.ML} TL={mod_patch.TL} KL={mod_patch.KL} "
      f"FB={mod_patch.FB} WS={mod_patch.WS} AR={mod_patch.AR} DR={mod_patch.DR} SL={mod_patch.SL} EG={mod_patch.EG}")
print(f"[emu] car patch: ML={car_patch.ML} TL={car_patch.TL} KL={car_patch.KL} "
      f"FB={car_patch.FB} WS={car_patch.WS} AR={car_patch.AR} DR={car_patch.DR} SL={car_patch.SL} EG={car_patch.EG}")
ch = EmuChannel(mod_patch, car_patch)
fnum, blk = freq_to_fnum_blk(FREQ)
ch.set_note(fnum, blk)
ch.set_volume(0)
ch.set_sus(0)
ch.key_on()
emu_mod_out = []
emu_car_out = []
emu_fm = []
for i in range(N):
    # 用 render_one (内部处理 pm_phase/env/反馈), 渲染后读 mod.output 抓数据
    co = ch.render_one()
    mo = ch.mod.output[0]
    # 反馈量: emu 用更新前的 output[1]+output[0], render_one 后 output[1]=上一拍, output[0]=当前
    # 这里取渲染后的组合近似 (仅供量级参考)
    fb = (ch.mod.output[1] + ch.mod.output[0]) >> (9 - ch.mod.patch.FB) if ch.mod.patch.FB > 0 else 0
    emu_mod_out.append(mo)
    emu_car_out.append(co)
    emu_fm.append(fb)

# ---------------- fw ----------------
p = fw_decode(dump)
mod, car = fw_apply_patch(p)
print(f"\n[fw]  mod: ml={mod['ml']} tl={mod['tl']} fb={mod['fb']} eg={mod['eg_type']} "
      f"atk={mod['atk']} decy={mod['decy']} sul={mod['sul']}")
print(f"[fw]  car: ml={car['ml']} tl={car['tl']} fb={car['fb']} eg={car['eg_type']} "
      f"atk={car['atk']} decy={car['decy']} sul={car['sul']}")
fnum2, blk2 = freq_to_fnum_blk(FREQ)
if blk2 > 0: blk2 -= 1
mod['step'] = fw_calc_step(fnum2, blk2, mod['ml'])
car['step'] = fw_calc_step(fnum2, blk2, car['ml'])
fw_vol = 60 - 0
car['tl'] = max(0, min(31, fw_vol >> 1))   # volume=0 -> tl=30
fw_key_on(mod, car)
fw_mod_out = []
fw_car_out = []
fw_fb = []
for i in range(N):
    wc = (i + 1) & 0x0F
    fb_before = mod['fb_val']
    co = fw_render_fm(mod, car, wc, 0)
    fw_mod_out.append(mod['fb_val'])   # fb_val 反映 mod 输出量级
    fw_car_out.append(co)
    fw_fb.append(mod['fb_val'])

# ---------------- 打印对比 ----------------
print(f"\n{'s':>3} | {'emu_mod':>8} {'emu_fb':>7} | {'fw_fbval':>9} | {'emu_car':>8} {'fw_car':>7}")
print("-" * 62)
import math
for i in range(min(N, 32)):
    print(f"{i:>3} | {emu_mod_out[i]:>8} {emu_fm[i]:>7} | {fw_mod_out[i]:>9} | {emu_car_out[i]:>8} {fw_car_out[i]:>7}")

print(f"\n--- 振幅统计 (前{N}采样) ---")
def stats(name, arr):
    if not arr: return
    pk = max(abs(x) for x in arr)
    rms = (sum(x*x for x in arr)/len(arr))**0.5
    print(f"  {name:<14} peak={pk:>7} rms={rms:>8.1f}")
stats("emu_mod_out", emu_mod_out)
stats("emu_car_out", emu_car_out)
stats("fw_fb_val",   fw_mod_out)
stats("fw_car_out",  fw_car_out)

print(f"\n=== 分析 ===")
print(f"emu mod 输出范围 ±32768, 经 (output[1]+output[0])>>8 反馈")
print(f"fw  mod fb_val = ch_out>>1, ch_out=(wave±31)×(lvl+1)×(tl+1)>>10")
print(f"    fw mod.tl={mod['tl']} (mod_tl=3 -> 31-1=30, 几乎无衰减)")
print(f"    emu mod TL=3 -> tll=TL2EG(3)=6 (EG单位, EG_MUTE=127), 衰减显著")
