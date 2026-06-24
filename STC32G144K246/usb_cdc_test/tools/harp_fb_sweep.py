#!/usr/bin/env python3
"""参数扫描: 调 mod.tl 映射 + 反馈移位, 看 carrier 能否对齐 emu.

可调参数 (只改数值/运算, 不动架构):
  TL_MODE: mod.tl 映射
    'inv'  = 31 - (tl_raw>>1)   [现状, TL=3->30 几乎无衰减]
    'direct' = tl_raw>>1        [TL=3->1 大衰减]
  FB_SHIFT: 反馈移位基底 (fb_val = ch_out >> (FB_SHIFT_BASE)), 作用于 fb 控制总移位
    现状: fb_val = ch_out >> FB        (FB=1 -> >>1)
    emu参考: emu 1024点表, >> (9-FB); fw 64点表
  这里把反馈改成: fb_val = ch_out >> (FB_SHIFT_BASE + (FB-1)*1)  让 FB=1 时移位更大

只渲染 harpsichord (inst 11), 不改源文件, 纯仿真试验.
"""
import os, sys, math, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ym2413_wav_gen import (DEFAULT_INST, NAMES, dump_to_patch, freq_to_fnum_blk,
                            EmuChannel, save_wav)
from fw_real_sim import (fw_decode, fw_apply_patch, fw_key_on, fw_calc_step,
                         FW_SIN, FW_HALFSIN, FW_AR_TAB, FW_DR_TAB, FW_RR_TAB,
                         FW_ML_TABLE, INTERNAL_RATE)

INST = 11
FREQ = 440.0
DUR_KO, DUR_KF = 1.0, 1.0

# ---------------- emu 参考 (固定) ----------------
def render_emu():
    mod_patch, car_patch = dump_to_patch(DEFAULT_INST[INST])
    ch = EmuChannel(mod_patch, car_patch)
    fnum, blk = freq_to_fnum_blk(FREQ)
    ch.set_note(fnum, blk); ch.set_volume(0); ch.set_sus(0); ch.key_on()
    n = int((DUR_KO + DUR_KF) * INTERNAL_RATE); nk = int(DUR_KO * INTERNAL_RATE)
    out = []
    for i in range(n):
        if i == nk: ch.key_off()
        out.append(ch.render_one())
    return out

# ---------------- fw 可调渲染 ----------------
def render_fw(TL_MODE, FB_BASE):
    """TL_MODE: 'inv'|'direct'; FB_BASE: 反馈总移位基底 (fb_val = ch_out >> FB_BASE 当 FB=1)"""
    p = fw_decode(DEFAULT_INST[INST])
    mod, car = fw_apply_patch(p)
    # --- 改 mod.tl 映射 ---
    if TL_MODE == 'inv':
        mod['tl'] = max(0, min(31, 31 - (p['mod_tl'] >> 1)))
    else:  # direct
        mod['tl'] = max(0, min(31, p['mod_tl'] >> 1))
    # carrier tl 不变 (volume 映射已修)
    fnum, blk = freq_to_fnum_blk(FREQ)
    if blk > 0: blk -= 1
    mod['step'] = fw_calc_step(fnum, blk, mod['ml'])
    car['step'] = fw_calc_step(fnum, blk, car['ml'])
    car['tl'] = max(0, min(31, (60 - 0) >> 1))  # volume=0 -> 30
    fw_key_on(mod, car)

    n = int((DUR_KO + DUR_KF) * INTERNAL_RATE); nk = int(DUR_KO * INTERNAL_RATE)
    out = []
    wc = 0
    # 反馈移位: FB=1 时用 FB_BASE (emu 对应 >>8 on 1024; fw 64点 + ch_out量级小)
    fb_shift = FB_BASE  # 简化: 直接用基底 (harpsichord FB=1)
    for s in range(n):
        if s == nk:
            from fw_real_sim import fw_key_off
            fw_key_off(mod, car)
        wc = (wc + 1) & 0x0F
        total = 0
        if not (car['env_state'] == 4 and car['level'] == 0):
            total = fw_render_fm_tunable(mod, car, wc, 0, fb_shift)
        else:
            car['env_state'] = 0
        total = total << 1
        if total > 32767: total = 32767
        elif total < -32768: total = -32768
        out.append(total)
    return out

def fw_render_fm_tunable(mod, car, wait_tick, ch, fb_shift):
    """可调反馈移位的 fw_render_fm (复制逻辑, 只改 fb 那一行)"""
    if mod['step'] == 0: return 0
    # OP1 mod
    mod['pos'] = (mod['pos'] + mod['step']) & 0xFFFFFFFF
    idx = (mod['pos'] >> 16) & 0x3F
    idx = (idx + (mod['fb_val'] & 0xFF)) & 0x3F
    wave_val = mod['wave'][idx]
    if wait_tick == (ch & 0x0F):
        from fw_real_sim import fw_env_tick
        fw_env_tick(mod)
    ch_out = ((wave_val * (mod['level'] + 1) * (mod['tl'] + 1)) >> 10)
    if ch_out > 127: ch_out = 127
    elif ch_out < -128: ch_out = -128
    if mod['fb'] > 0:
        fb_val = ch_out >> fb_shift            # <<< 唯一改动: 移位可调
        if fb_val > 127: fb_val = 127
        elif fb_val < -128: fb_val = -128
        mod['fb_val'] = fb_val
    else:
        mod['fb_val'] = 0
    # OP2 car
    car['pos'] = (car['pos'] + car['step']) & 0xFFFFFFFF
    idx = (car['pos'] >> 16) & 0x3F
    idx = (idx + (ch_out & 0xFF)) & 0x3F
    wave_val = car['wave'][idx]
    if wait_tick == (ch & 0x0F):
        from fw_real_sim import fw_env_tick
        fw_env_tick(car)
    ch_out = ((wave_val * (car['level'] + 1) * (car['tl'] + 1)) >> 10)
    if ch_out > 127: ch_out = 127
    elif ch_out < -128: ch_out = -128
    return ch_out

def rms(s): return (sum(x*x for x in s)/max(len(s),1))**0.5
def neg_ratio(s):
    """负采样占比, 衡量是否有负半周 (正常乐器应接近 0.5)"""
    neg = sum(1 for x in s if x < 0)
    return neg / max(len(s), 1)

# ---------------- 跑扫描 ----------------
print(f"=== Inst {INST}: {NAMES[INST]} | {FREQ}Hz | {DUR_KO}s+{DUR_KF}s ===\n")
emu = render_emu()
er, en = rms(emu), neg_ratio(emu)
print(f"[emu 参考] RMS={er:7.1f} peak={max(abs(x) for x in emu):6d} 负采样占比={en:.3f}")
print()

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wav_harp_sweep")
os.makedirs(OUT, exist_ok=True)
# 存 emu 参考
save_wav(os.path.join(OUT, "harp_emu.wav"), emu)

print(f"{'TL_MODE':<8} {'FB_BASE':>7} | {'RMS':>8} {'peak':>6} {'neg%':>6} | {'dB_vs_emu':>9}")
print("-" * 58)
best = None
for TL_MODE in ['inv', 'direct']:
    for FB_BASE in [1, 2, 3, 4, 5, 6]:
        try:
            fw = render_fw(TL_MODE, FB_BASE)
        except Exception as e:
            print(f"{TL_MODE:<8} {FB_BASE:>7} | ERR {e}"); continue
        r, ng = rms(fw), neg_ratio(fw)
        d = 20*math.log10(r/er) if er > 0 and r > 0 else -99
        flag = ""
        # 目标: neg% 接近 emu (>0.3) 且 dB 接近 0
        score = abs(d) + abs(ng - en) * 50
        if best is None or score < best[0]:
            best = (score, TL_MODE, FB_BASE, r, ng, d)
        print(f"{TL_MODE:<8} {FB_BASE:>7} | {r:8.1f} {max(abs(x) for x in fw):6d} {ng:6.3f} | {d:+9.3f}")
        # 存每一组
        save_wav(os.path.join(OUT, f"harp_{TL_MODE}_fb{FB_BASE}.wav"), fw)

print("-" * 58)
print(f"\n最接近 emu 的组合: TL_MODE={best[1]} FB_BASE={best[2]} "
      f"RMS={best[3]:.1f} neg%={best[4]:.3f} dB={best[5]:+.3f}")
print(f"\n输出目录: {OUT}")
print(f"  harp_emu.wav              - 参考")
print(f"  harp_<mode>_fb<n>.wav     - 各参数组合 (共 12 个)")
