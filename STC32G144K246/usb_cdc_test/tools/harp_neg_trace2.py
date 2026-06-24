#!/usr/bin/env python3
"""render_one 模式下抓 car 真实输出+内部状态, 找负值来源."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ym2413_wav_gen import (DEFAULT_INST, dump_to_patch, freq_to_fnum_blk,
                            EmuChannel, PG_WIDTH, HALFSIN, FULLSIN, to_linear)

dump = DEFAULT_INST[11]
mp, cp = dump_to_patch(dump)
ch = EmuChannel(mp, cp)
fn, bl = freq_to_fnum_blk(440.0)
ch.set_note(fn, bl); ch.set_volume(0); ch.set_sus(0); ch.key_on()

print(f"car.wave_table is HALFSIN: {ch.car.wave_table is HALFSIN}")
print(f"car.wave_table is FULLSIN: {ch.car.wave_table is FULLSIN}")
print(f"car.patch.WS = {ch.car.patch.WS}")
# 看 car wave_table 关键位置
wt = ch.car.wave_table
print(f"wave_table[0]={wt[0]} [256]={wt[256]} [511]={wt[511]} [512]={wt[512]} [768]={wt[768]} [1023]={wt[1023]}")
print(f"\n用 render_one 跑, 抓 car.output[0] (最终) 和 pg_out:")
print(f"{'s':>3} {'pg_out':>7} {'eg_out':>6} {'tll':>4} {'car_out':>8}")
neg_seen = []
for i in range(60):
    co = ch.render_one()
    if co < 0 and len(neg_seen) < 5:
        neg_seen.append((i, ch.car.pg_out, ch.car.eg_out, ch.car.tll, co))
    if i < 40 or (co < 0 and i < 60):
        print(f"{i:>3} {ch.car.pg_out:>7} {ch.car.eg_out:>6} {ch.car.tll:>4} {co:>8}")

print(f"\n--- 负值采样详情 ---")
for s, pg, eg, tll, co in neg_seen:
    # 重算: render_one 后 car.output[0] 已更新, 重新查这个 pg_out 对应的 raw wave
    idx = pg & (PG_WIDTH - 1)
    raw = wt[idx]
    print(f"  s={s} pg_out={pg} idx={idx} raw_wave={raw} eg_out={eg} tll={tll} "
          f"to_lin={to_linear(raw, ch.car, 0)} car_out={co}")
    if raw >= 0x8000:
        print(f"    ↑ raw 有符号位 0x8000! 这是 FULLSIN 负半周, 不是 HALFSIN!")
