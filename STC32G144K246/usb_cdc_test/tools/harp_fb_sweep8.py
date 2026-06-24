#!/usr/bin/env python3
"""harpsichord FB=0~7 扫描 (mute halfsin, mod.tl 原状).

只改 patch 的 mod_fb 值 (PC 实验调参), 其他全保持原状.
输出: harp_fb0.wav ~ harp_fb7.wav + harp_emu.wav (共9个)

FB 语义 (下位机): fb_val = ch_out >> FB
  FB=0: >>0 不衰减 (最强反馈)
  FB=7: >>7 最弱反馈
  harpsichord 原 FB=1
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fw_real_sim as F
from fw_real_sim import (fw_decode, fw_apply_patch, fw_key_on, fw_env_tick,
                         fw_calc_step, FW_SIN, FW_HALFSIN, INTERNAL_RATE)
from ym2413_wav_gen import (DEFAULT_INST, NAMES, render_emu2413, save_wav,
                            freq_to_fnum_blk)

INST = 11
FREQ = 440.0
DUR_KO, DUR_KF = 1.0, 1.0

print(f"=== Inst {INST}: {NAMES[INST]} | FB 扫描 (mute halfsin) ===")
print(f"FW_HALFSIN 后半周: {FW_HALFSIN[32:40]}... (mute=0)")
print(f"mod.tl 映射: 31-(TL>>1) 原状 (TL={DEFAULT_INST[INST][2]&63} -> tl={31-((DEFAULT_INST[INST][2]&63)>>1)})")
print(f"原 patch mod_fb = {fw_decode(DEFAULT_INST[INST])['mod_fb']}")
print()

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wav_harp_fb_sweep")
os.makedirs(OUT, exist_ok=True)

def render_fw_with_fb(fb_override):
    """渲染 harpsichord, 强制 mod_fb = fb_override. 其他原状."""
    p = fw_decode(DEFAULT_INST[INST])
    p['mod_fb'] = fb_override   # <<< 唯一改动: 覆盖 FB
    mod, car = fw_apply_patch(p)
    fn, bl = freq_to_fnum_blk(FREQ)
    if bl > 0: bl -= 1
    mod['step'] = fw_calc_step(fn, bl, mod['ml'])
    car['step'] = fw_calc_step(fn, bl, car['ml'])
    car['tl'] = max(0, min(31, (60-0)>>1))   # volume=0 -> tl=30 (和 render_fw_real 一致)
    fw_key_on(mod, car)

    n = int((DUR_KO + DUR_KF) * INTERNAL_RATE)
    nk = int(DUR_KO * INTERNAL_RATE)
    out = []
    wc = 0
    for s in range(n):
        if s == nk:
            F.fw_key_off(mod, car)
        wc = (wc + 1) & 0x0F
        total = 0
        if not (car['env_state'] == 4 and car['level'] == 0):
            total = F.fw_render_fm(mod, car, wc, 0)
        else:
            car['env_state'] = 0
        total = total << 1
        if total > 32767: total = 32767
        elif total < -32768: total = -32768
        out.append(total)
    return out

# emu 原版
emu = render_emu2413(INST, FREQ, DUR_KO, DUR_KF, 0)
save_wav(os.path.join(OUT, "harp_emu.wav"), emu)
print(f"  harp_emu.wav        (emu2413 原版参考)")

# FB=0~7
for fb in range(8):
    out = render_fw_with_fb(fb)
    path = os.path.join(OUT, f"harp_fb{fb}.wav")
    save_wav(path, out)
    mark = " <- harpsichord 原值" if fb == 1 else ""
    print(f"  harp_fb{fb}.wav       (fb_val = ch_out >> {fb}){mark}")

print(f"\n输出目录: {OUT}")
print(f"对照听: harp_emu.wav (参考) vs harp_fb0~7.wav")
print(f"  fb0=最强反馈, fb7=最弱, fb1=原值")
