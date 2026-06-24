#!/usr/bin/env python3
"""频率对齐后, 在正确仿真器上扫 FB=0~7 (反馈移位).

mute halfsin + mod.tl 原状 (31-(TL>>1)), 唯一变量 = patch 的 mod_fb.
输出 8 个 wav + emu 参考, 量化每个的反馈占周期.

FB 语义 (下位机): fb_val = ch_out >> FB
  FB=0: 最强反馈, FB=7: 最弱
  harpsichord 原值 FB=1
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fw_real_sim as F
from fw_real_sim import (fw_decode, fw_apply_patch, fw_key_on, fw_env_tick,
                         fw_calc_step, FW_SIN, FW_HALFSIN, FW_ISR_RATE, save_fw_wav)
from ym2413_wav_gen import (DEFAULT_INST, NAMES, render_emu2413, save_wav,
                            freq_to_fnum_blk, PG_WIDTH)

dump = DEFAULT_INST[11]
INST = 11
FREQ = 440.0
DUR_KO, DUR_KF = 1.0, 1.0
N_STATS = 200   # 统计反馈占周期的采样段

def render_fw_fb(fb_override):
    """渲染 harpsichord, 强制 mod_fb. 返回 (out, fbvals)."""
    p = fw_decode(dump)
    p['mod_fb'] = fb_override
    mod, car = fw_apply_patch(p)
    fn, bl = freq_to_fnum_blk(FREQ)
    if bl > 0: bl -= 1
    mod['step'] = fw_calc_step(fn, bl, mod['ml'])
    car['step'] = fw_calc_step(fn, bl, car['ml'])
    car['tl'] = max(0, min(31, (60-0)>>1))
    fw_key_on(mod, car)
    n = int((DUR_KO+DUR_KF)*FW_ISR_RATE); nk = int(DUR_KO*FW_ISR_RATE)
    out = []; fbvals = []; wc = 0
    for s in range(n):
        if s == nk: F.fw_key_off(mod, car)
        wc = (wc+1) & 0x0F
        total = 0
        if not (car['env_state'] == 4 and car['level'] == 0):
            total = F.fw_render_fm(mod, car, wc, 0)
        else:
            car['env_state'] = 0
        total = max(-32768, min(32767, total << 1))
        out.append(total)
        if s < N_STATS: fbvals.append(mod['fb_val'])
    return out, fbvals

# emu 反馈占周期参考 (已知 1.2% peak, 0.66% mean)
emu = render_emu2413(INST, FREQ, DUR_KO, DUR_KF, 0)

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wav_harp_fb_fixed")
os.makedirs(OUT, exist_ok=True)
save_wav(os.path.join(OUT, "harp_emu.wav"), emu)

def meanabs(a): return sum(abs(x) for x in a)/max(len(a),1)

print(f"=== harpsichord FB=0~7 扫描 (频率已对齐, mute halfsin) ===")
print(f"emu 反馈占周期: 1.2% peak, 0.66% mean (参考)\n")
print(f"{'FB':>3} {'反馈占周期peak%':>14} {'mean%':>7} {'fw_RMS':>8} | wav")
print("-" * 60)
for fb in range(8):
    out, fbvals = render_fw_fb(fb)
    fb_pk = max(abs(x) for x in fbvals)
    fb_mn = meanabs(fbvals)
    r = (sum(x*x for x in out)/len(out))**0.5
    pk_pct = fb_pk/64*100
    mn_pct = fb_mn/64*100
    mark = " <- 原值" if fb == 1 else ""
    save_fw_wav(os.path.join(OUT, f"harp_fb{fb}.wav"), out)
    print(f"{fb:>3} {pk_pct:>13.1f}% {mn_pct:>6.2f}% {r:>8.1f} | harp_fb{fb}.wav{mark}")

print(f"\n目标: 反馈占周期 mean 接近 emu 0.66%")
print(f"输出: {OUT}/harp_fb0~7.wav + harp_emu.wav")
