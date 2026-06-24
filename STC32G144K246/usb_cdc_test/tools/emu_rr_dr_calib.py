#!/usr/bin/env python3
"""精确反推 RR_TAB + 测 DR_TAB.

上次反推假设 31 步, 但 keyoff 时 level 已降. 这次:
1. 直接测 fw 各 RR 下 level 31->0 的实际步数和时间 (用仿真)
2. 对照 emu 同 RR 的 eg_out 全程时间
3. 反推精确 cnt
另外测 DR 表 (decay 阶段 eg_out 0->SL 对应值).
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fw_real_sim as F
from fw_real_sim import (fw_decode, fw_apply_patch, fw_key_on, fw_env_tick,
                         fw_calc_step, FW_ISR_RATE, FW_RR_TAB, FW_DR_TAB)
from ym2413_wav_gen import (DEFAULT_INST, dump_to_patch, freq_to_fnum_blk,
                            EmuChannel, calc_envelope, EG_MUTE, INTERNAL_RATE)

ISR = 22050

# ===== 测 emu 各 RR 的 eg_out 全程时间 (精确, 从 attack 完成到 126) =====
def emu_rr_time(rr_val):
    mp, cp = dump_to_patch(DEFAULT_INST[11])
    cp.RR = rr_val; cp.EG = 0; cp.SL = 0
    ch = EmuChannel(mp, cp)
    fn, bl = freq_to_fnum_blk(440.0)
    ch.set_note(fn, bl); ch.set_volume(0); ch.set_sus(0); ch.key_on()
    from ym2413_wav_gen import am_table, calc_phase
    eg = []
    for i in range(int(2.0*INTERNAL_RATE)):
        ch.pm_phase = (ch.pm_phase + 1) & 0xffffffff
        ch.am_phase += 1
        ch.lfo_am = am_table[(ch.am_phase >> 6) % len(am_table)]
        ch.eg_counter += 1
        calc_envelope(ch.car, ch.eg_counter)
        calc_phase(ch.car, ch.pm_phase)
        eg.append(ch.car.eg_out)
    eg_min = min(eg)
    t0 = next(i for i,e in enumerate(eg) if e <= eg_min+1)
    try:
        t1 = next(i for i in range(t0, len(eg)) if eg[i] >= 126)
    except StopIteration:
        t1 = len(eg)-1
    return (t1-t0)/INTERNAL_RATE*1000  # ms

# ===== 测 fw 各 RR 的 level 31->0 时间 (精确仿真) =====
def fw_rr_time(rr_tab_val):
    """用 RR=固定值, SL=0(不衰减), keyon 后直接进 sustain 降, 测 level 31->0."""
    F.FW_RR_TAB = [rr_tab_val]*16   # 全用这个值测
    p = fw_decode(DEFAULT_INST[11])
    p['car_rr'] = 4  # 占位, 实际用 FW_RR_TAB[4]
    mod, car = fw_apply_patch(p)
    car['tl'] = max(0, min(31, (60-0)>>1))
    # 强制: key_on 后 atk<=2 瞬间到顶 level=31, 进 decay, sul=31 立刻进 sustain
    # EG=0 sustain 用 rel=RR_TAB[rr]
    fw_key_on(mod, car)
    # 此时 car: level=31, env_state=2(decay), sul=31 -> 下个 tick 进 sustain
    n = int(2.0*FW_ISR_RATE); wc = 0
    t_start = -1; t_end = -1
    for i in range(n):
        wc = (wc+1) & 0x0F
        # 只 tick car env (跳过渲染, 只看 level)
        if wc == 0:
            fw_env_tick(car)
        if t_start < 0 and car['level'] < 31:
            t_start = i
        if car['level'] == 0:
            t_end = i; break
    if t_end < 0: return 9999
    return (t_end - t_start)/FW_ISR_RATE*1000

print(f"=== RR 精确反推 (emu 实测时间 + fw level 31->0 步数) ===\n")
# 先测 fw 各 RR_TAB 值下 level 31->0 的步数 (固定 cnt)
# fw: 每 tick (16采样) cnt 次才降 1 level. level 31->0 = 31 步.
# 但实际 cnt 控制的是 env_cnt, env_cnt 达到 cnt 才走 1 level 步.
# 所以 31 level 步 × cnt × 16 采样 = 总采样. 时间 = 31×cnt×16/ISR
print(f"fw level 31->0 理论时间 = 31 × cnt × 16 / {ISR} ms\n")
print(f"{'RR':>3} {'emu_ms':>8} {'emu需要的cnt':>12} {'现cnt':>6} {'新cnt':>6}")
print("-" * 45)
new_rr = [0]*16
for rr in range(16):
    if rr == 0:
        print(f"{rr:>3} {'∞':>8} {'0':>12} {FW_RR_TAB[rr]:>6} {0:>6}")
        new_rr[rr] = 0; continue
    emu_ms = emu_rr_time(rr)
    # emu_ms = 31 × cnt × 16 / ISR × 1000
    cnt_need = emu_ms * ISR / (31 * 16 * 1000)
    cnt_need = max(1, min(255, int(round(cnt_need))))
    old = FW_RR_TAB[rr]
    print(f"{rr:>3} {emu_ms:>8.1f} {cnt_need:>12} {old:>6} {cnt_need:>6}")
    new_rr[rr] = cnt_need

print(f"\n现 RR_TAB = {FW_RR_TAB}")
print(f"新 RR_TAB = {new_rr}")

# ===== 同法测 DR (decay 阶段) =====
print(f"\n=== DR 反推 (emu decay eg_out 0->SL对应值) ===")
def emu_dr_time(dr_val):
    mp, cp = dump_to_patch(DEFAULT_INST[11])
    cp.DR = dr_val; cp.EG = 1; cp.SL = 15  # sustaining, SL=15 衰减到接近静音
    ch = EmuChannel(mp, cp)
    fn, bl = freq_to_fnum_blk(440.0)
    ch.set_note(fn, bl); ch.set_volume(0); ch.set_sus(0); ch.key_on()
    from ym2413_wav_gen import am_table, calc_phase
    eg = []
    for i in range(int(2.0*INTERNAL_RATE)):
        ch.pm_phase = (ch.pm_phase + 1) & 0xffffffff
        ch.am_phase += 1
        ch.lfo_am = am_table[(ch.am_phase >> 6) % len(am_table)]
        ch.eg_counter += 1
        calc_envelope(ch.car, ch.eg_counter)
        calc_phase(ch.car, ch.pm_phase)
        eg.append(ch.car.eg_out)
    eg_min = min(eg)
    t0 = next(i for i,e in enumerate(eg) if e <= eg_min+1)
    # SL=15: decay 到 eg_out>>3==15 即 eg_out 120~127
    try:
        t1 = next(i for i in range(t0, len(eg)) if (eg[i]>>3) >= 15)
    except StopIteration:
        t1 = len(eg)-1
    return (t1-t0)/INTERNAL_RATE*1000

print(f"{'DR':>3} {'emu_ms':>8} {'新cnt':>6} {'现cnt':>6}")
print("-" * 30)
new_dr = [0]*16
for dr in range(16):
    if dr == 0:
        new_dr[dr]=0; print(f"{dr:>3} {'∞':>8} {0:>6} {FW_DR_TAB[dr]:>6}"); continue
    emu_ms = emu_dr_time(dr)
    # fw decay: level 31->sul 步数. sul=31-15*2=1, 步数=31-1=30
    # 但 DR 影响 decay 速度. 时间 = (31-sul) × cnt × 16 / ISR
    # sul 固定看 DR 速率: 用 sul=1 (SL=15), 步数=30
    cnt_need = emu_ms * ISR / (30 * 16 * 1000)
    cnt_need = max(1, min(255, int(round(cnt_need))))
    print(f"{dr:>3} {emu_ms:>8.1f} {cnt_need:>6} {FW_DR_TAB[dr]:>6}")
    new_dr[dr] = cnt_need
print(f"\n现 DR_TAB = {FW_DR_TAB}")
print(f"新 DR_TAB = {new_dr}")
