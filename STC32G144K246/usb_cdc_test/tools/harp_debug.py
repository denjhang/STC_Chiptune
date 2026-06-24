#!/usr/bin/env python3
"""调试 harpsichord fw_real 静音原因: dump patch, key_on 后的状态, 前 20 采样."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fw_real_sim import (fw_decode, fw_apply_patch, fw_key_on, fw_env_tick,
                         fw_calc_step, FW_AR_TAB, FW_DR_TAB, FW_RR_TAB, FW_ML_TABLE)
from ym2413_wav_gen import DEFAULT_INST, NAMES, freq_to_fnum_blk, dump_to_patch

INST = 11
FREQ = 440.0
dump = DEFAULT_INST[INST]
print(f"=== Inst {INST}: {NAMES[INST]} ===")
print(f"raw dump: {['0x%02X'%b for b in dump]}")

p = fw_decode(dump)
print(f"\nfw_decode patch:")
for k, v in p.items():
    print(f"  {k:8} = {v}")

# emu 版解码对照
mod_patch, car_patch = dump_to_patch(dump)
print(f"\nemu dump_to_patch:")
print(f"  mod: {mod_patch}")
print(f"  car: {car_patch}")

# 下位机 apply_patch
mod, car = fw_apply_patch(p)
print(f"\nfw_apply_patch:")
print(f"  mod: ml={mod['ml']} tl={mod['tl']} fb={mod['fb']} eg={mod['eg_type']} "
      f"ws={mod['wave'][:3]}... ar={mod['atk']}(tab) decy={mod['decy']}(tab) sul={mod['sul']} rel={mod['rel']}(tab)")
print(f"  car: ml={car['ml']} tl={car['tl']} fb={car['fb']} eg={car['eg_type']} "
      f"ws={car['wave'][:3]}... ar={car['atk']}(tab) decy={car['decy']}(tab) sul={car['sul']} rel={car['rel']}(tab)")

# 算 step
fnum, blk = freq_to_fnum_blk(FREQ)
print(f"\nfreq_to_fnum_blk({FREQ}) = fnum={fnum}, blk={blk}")
if blk > 0: blk -= 1
print(f"  下位机 blk-1 修正: blk={blk}")
mod['step'] = fw_calc_step(fnum, blk, mod['ml'])
car['step'] = fw_calc_step(fnum, blk, car['ml'])
car['tl'] = 0  # volume=0
print(f"  mod step = 0x{mod['step']&0xFFFFFFFF:08X} ({mod['step']})")
print(f"  car step = 0x{car['step']&0xFFFFFFFF:08X} ({car['step']})")

# key_on 前后状态
print(f"\n--- key_on 前 ---")
print(f"  mod: env_state={mod['env_state']} level={mod['level']} env_step={mod['env_step']} pos={mod['pos']}")
print(f"  car: env_state={car['env_state']} level={car['level']} env_step={car['env_step']} pos={car['pos']}")
fw_key_on(mod, car)
print(f"\n--- key_on 后 ---")
print(f"  mod: env_state={mod['env_state']} level={mod['level']} env_step={mod['env_step']} "
      f"atk={mod['atk']} decy={mod['decy']} (atk<=2 瞬间到顶?)")
print(f"  car: env_state={car['env_state']} level={car['level']} env_step={car['env_step']} "
      f"atk={car['atk']} decy={car['decy']} (atk<=2 瞬间到顶?)")

# 手动跑 render_fm 前 20 采样, 看输出为什么是 0
print(f"\n--- 手动跑前 20 采样 ---")
from fw_real_sim import fw_render_fm, FW_SIN, FW_HALFSIN
total_out = []
for s in range(20):
    wait_cnt = (s + 1) & 0x0F
    ch_out = fw_render_fm(mod, car, wait_cnt, 0)
    total_out.append(ch_out)
    if s < 8:
        print(f"  s={s:2d} wait_cnt={wait_cnt} mod_pos=0x{mod['pos']&0xFFFFFFFF:08X} "
              f"mod_lvl={mod['level']} car_pos=0x{car['pos']&0xFFFFFFFF:08X} "
              f"car_lvl={car['level']} fb_val={mod['fb_val']} out={ch_out}")
print(f"  ...前20采样 out = {total_out}")
print(f"  全0? {all(x==0 for x in total_out)}")

# 单独测 carrier (无调制): 看 carrier 本身能否出声
print(f"\n--- carrier 单独无调制 (ch_out=0) 测试 ---")
mod2, car2 = fw_apply_patch(p)
car2['tl'] = 0  # volume=0 -> tl=0 (满输出), 和 render_fw_real 一致
fw_key_on(mod2, car2)
# 强制 mod 输出为 0 (无调制)
orig_mod_tl = mod2['tl']
mod2['tl'] = 0
mod2['level'] = 0  # mod level=0 -> (level+1)=1
print(f"  car2: tl={car2['tl']} (volume=0->tl=0) level={car2['level']} wave={'halfsin' if car2['wave'] is FW_HALFSIN else 'sin'}")
print(f"  注意 render_fw_real 设 car.tl = volume>>1 = 0, 不是 apply_patch 的 31")
outs = []
for s in range(20):
    ch_out = fw_render_fm(mod2, car2, (s+1)&0x0F, 0)
    outs.append(ch_out)
print(f"  carrier 输出: {outs[:8]}...")
print(f"  全0? {all(x==0 for x in outs)}")
print(f"  公式: wave(±31) × (level+1=32) × (tl+1=1) >> 10 = wave × 32 >> 10 = wave/32 ≈ 0!")
print(f"        ↑ tl=0 时 (tl+1)=1, 31×32×1>>10 = 0. 这就是静音原因!")
