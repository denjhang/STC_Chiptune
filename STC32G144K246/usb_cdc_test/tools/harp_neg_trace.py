#!/usr/bin/env python3
"""追 emu harpsichord 负值的来源: 抓 carrier 的 pg_out/索引/原始wave/to_linear 各步."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ym2413_wav_gen import (DEFAULT_INST, dump_to_patch, freq_to_fnum_blk,
                            EmuChannel, calc_phase, calc_slot_mod, calc_slot_car,
                            to_linear, PG_WIDTH, HALFSIN)
from fw_real_sim import INTERNAL_RATE

dump = DEFAULT_INST[11]
mp, cp = dump_to_patch(dump)
ch = EmuChannel(mp, cp)
fn, bl = freq_to_fnum_blk(440.0)
ch.set_note(fn, bl); ch.set_volume(0); ch.set_sus(0); ch.key_on()

print(f"car wave_table = HALFSIN, PG_WIDTH={PG_WIDTH}, 后半周(index>=512)=4095静音")
print(f"car patch.FB={cp.FB} (carrier 无反馈)")
print(f"\n{'s':>3} {'car_pgout':>9} {'raw_wave':>8} {'eg_out':>6} {'tll':>4} {'to_lin':>7} {'car_out':>8}")
print("-" * 60)
for i in range(40):
    ch.pm_phase = (ch.pm_phase + 1) & 0xffffffff
    calc_phase(ch.mod, ch.pm_phase)
    calc_phase(ch.car, ch.pm_phase)
    mo = calc_slot_mod(ch.mod, ch.lfo_am)
    # 抓 car 计算前状态
    car = ch.car
    pg_out = car.pg_out
    # calc_slot_car 内部: fm=mo, idx=(pg_out + 2*(fm>>1))&1023
    fm = mo
    idx = (pg_out + 2 * (fm >> 1)) & (PG_WIDTH - 1)
    raw = car.wave_table[idx]
    eg = car.eg_out
    tll = car.tll
    co = calc_slot_car(car, mo, ch.lfo_am)
    print(f"{i:>3} {pg_out:>9} {raw:>8} {eg:>6} {tll:>4} {to_linear(raw,car,0):>7} {co:>8}")
