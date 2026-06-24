#!/usr/bin/env python3
"""查 emu harpsichord 实际用的 wave_table + halfsin 负半周真实行为."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ym2413_wav_gen import (DEFAULT_INST, dump_to_patch, FULLSIN, HALFSIN,
                            PG_WIDTH, EmuChannel)

dump = DEFAULT_INST[11]
mp, cp = dump_to_patch(dump)
print(f"harpsichord: mod_ws={mp.WS} car_ws={cp.WS}")
print(f"wave_table_map 顺序: [0]=FULLSIN [1]=HALFSIN")
print(f"  mod 用: {'HALFSIN' if mp.WS else 'FULLSIN'}")
print(f"  car 用: {'HALFSIN' if cp.WS else 'FULLSIN'}")

print(f"\n--- FULLSIN 表前64项 (看符号位/量级) ---")
print(f"  FULLSIN[0:16]   = {FULLSIN[0:16]}")
print(f"  FULLSIN[16:32]  = {FULLSIN[16:32]}")
print(f"  FULLSIN[32:48]  = {FULLSIN[32:48]}   <- 负半周?")
print(f"  FULLSIN[48:64]  = {FULLSIN[48:64]}")

print(f"\n--- HALFSIN 表前64项 ---")
print(f"  HALFSIN[0:16]   = {HALFSIN[0:16]}")
print(f"  HALFSIN[16:32]  = {HALFSIN[16:32]}")
print(f"  HALFSIN[32:48]  = {HALFSIN[32:48]}   <- 后半周")
print(f"  HALFSIN[48:64]  = {HALFSIN[48:64]}")

# 实例化 EmuChannel 看 car.wave_table 实际指向
ch = EmuChannel(mp, cp)
print(f"\nEmuChannel.car.wave_table is HALFSIN? {ch.car.wave_table is HALFSIN}")
print(f"EmuChannel.car.wave_table is FULLSIN? {ch.car.wave_table is FULLSIN}")
print(f"car.wave_table[0]={ch.car.wave_table[0]} car.wave_table[512]={ch.car.wave_table[512]} (后半周起)")

# 看 to_linear 对 HALFSIN 后半周 (0xfff) 的输出
from ym2413_wav_gen import to_linear, EG_MUTE
slot = ch.car
slot.eg_out = 0  # 最大音量
slot.tll = 0
print(f"\nto_linear(HALFSIN后半周=0xfff, eg_out=0, tll=0) = {to_linear(0xfff, slot, 0)}")
print(f"to_linear(FULLSIN负半周如0x8003, eg_out=0, tll=0) = {to_linear(0x8003, slot, 0)}")
