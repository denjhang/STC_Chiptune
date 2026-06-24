#!/usr/bin/env python3
"""核对仿真器 vs 下位机 step 计算, 找频率偏差根因.

下位机 (ym2413.c:234-242):
  8.8 定点: idx = pos>>8 & 0x3F, 一个周期 = 64×256 = 16384, pos 是 u16
  STEP_CONST = 3579545 × 64 × 256 / (72 × 262144 × 22050)
  step = fnum × (1<<blk) × STEP_CONST × ml / 2  (u16)
  频率 = step × ISR(22050) / 16384

仿真器 (fw_real_sim.py):
  注释说 16.16 定点, idx = pos>>16 & 0x3F, 但 pos 用 u32 (& 0xFFFFFFFF)
  FW_STEP_CONST = 3579545 × 64 × 65536 / (72 × 262144 × 22050)
  step = fnum × (1<<blk) × FW_STEP_CONST × ml / 2
  频率 = step × INTERNAL_RATE(49716) / (64 × 65536)  ??? 需确认

emu2413 参考:
  freq_to_fnum_blk(440) -> fnum/blk, 反算频率应 = 440
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fw_real_sim import fw_calc_step, FW_STEP_CONST, FW_ML_TABLE, INTERNAL_RATE
from ym2413_wav_gen import freq_to_fnum_blk, DEFAULT_INST, dump_to_patch

print(f"=== step 常数对比 ===")
FW_CONST = 3579545.0 * 64.0 * 65536.0 / (72.0 * 262144.0 * 22050.0)
HW_CONST = 3579545.0 * 64.0 * 256.0  / (72.0 * 262144.0 * 22050.0)
print(f"仿真器 FW_STEP_CONST (×65536) = {FW_STEP_CONST:.8f}")
print(f"重算 FW_CONST (×65536)        = {FW_CONST:.8f}")
print(f"下位机 HW_CONST (×256)        = {HW_CONST:.8f}")
print(f"两者比 FW/HW = {FW_CONST/HW_CONST:.1f} (应=256 if 都是×64/(72×262144×22050))")

# 72 × 262144 这个分母: 262144=2^18, 72×262144 = 18874368
# 但 emu 的 DP_WIDTH=2^19=524288, 不一样
print(f"\n72×262144 = {72*262144} (下位机分母, 奇怪)")
print(f"2^18 = {2**18}, 2^19 = {2**19}")

# ===== harpsichord 440Hz 实际频率对比 =====
print(f"\n=== harpsichord 440Hz 实际频率对比 ===")
dump = DEFAULT_INST[11]
mp, cp = dump_to_patch(dump)
fnum, blk = freq_to_fnum_blk(440.0)
print(f"freq_to_fnum_blk(440) = fnum={fnum}, blk={blk}")
print(f"emu 反算频率: 应 = 440 Hz")

# 下位机: blk-1 修正
blk_hw = blk - 1 if blk > 0 else blk
print(f"\n--- 下位机 (8.8 定点) ---")
print(f"  blk-1 修正: blk={blk_hw}")
# mod ml
mod_ml = FW_ML_TABLE[mp.ML]
car_ml = FW_ML_TABLE[cp.ML]
print(f"  mod ML={mp.ML} -> ml_table={mod_ml}, car ML={cp.ML} -> ml={car_ml}")
step_mod_hw = fnum * (1 << blk_hw) * HW_CONST * mod_ml / 2.0
step_car_hw = fnum * (1 << blk_hw) * HW_CONST * car_ml / 2.0
print(f"  step_mod = {step_mod_hw:.2f} (u16={int(step_mod_hw)&0xFFFF})")
print(f"  step_car = {step_car_hw:.2f} (u16={int(step_car_hw)&0xFFFF})")
# 一个周期 = 16384 (64×256), ISR=22050
freq_mod_hw = int(step_mod_hw) & 0xFFFF
freq_mod_hw = freq_mod_hw * 22050 / 16384
freq_car_hw = (int(step_car_hw) & 0xFFFF) * 22050 / 16384
print(f"  mod 实际频率 = step × 22050 / 16384 = {freq_mod_hw:.1f} Hz")
print(f"  car 实际频率 = {freq_car_hw:.1f} Hz")

# 仿真器
print(f"\n--- 仿真器 (fw_calc_step, 注释16.16) ---")
blk_sim = blk - 1 if blk > 0 else blk
step_mod_sim = fw_calc_step(fnum, blk_sim, mod_ml)
step_car_sim = fw_calc_step(fnum, blk_sim, car_ml)
print(f"  step_mod = {step_mod_sim} (0x{step_mod_sim&0xFFFFFFFF:08X})")
print(f"  step_car = {step_car_sim} (0x{step_car_sim&0xFFFFFFFF:08X})")
print(f"  INTERNAL_RATE = {INTERNAL_RATE}")
# 仿真器 render: pos = (pos + step) & 0xFFFFFFFF, idx = pos>>16 & 0x3F
# 一个周期 = 64 × 65536 = 4194304
freq_mod_sim = step_mod_sim * INTERNAL_RATE / (64 * 65536)
freq_car_sim = step_car_sim * INTERNAL_RATE / (64 * 65536)
print(f"  mod 实际频率 = step × {INTERNAL_RATE} / (64×65536) = {freq_mod_sim:.1f} Hz")
print(f"  car 实际频率 = {freq_car_sim:.1f} Hz")

print(f"\n=== 频率比 vs emu(440) ===")
print(f"  下位机 car: {freq_car_hw/440:.4f} × 440 = {freq_car_hw:.1f} Hz")
print(f"  仿真器 car: {freq_car_sim/440:.4f} × 440 = {freq_car_sim:.1f} Hz")
print(f"  听感'高八度+2半音' = 2 × 2^(2/12) = {2 * 2**(2/12):.4f} × 440 = {440*2*2**(2/12):.1f} Hz")
