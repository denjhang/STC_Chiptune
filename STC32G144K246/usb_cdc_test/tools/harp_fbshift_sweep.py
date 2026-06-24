#!/usr/bin/env python3
"""只调反馈移位 (不动 mod.tl 映射), 扫描 N=2~5.

mod.tl 保持现状 31-(TL>>1) (不改, 避免影响所有乐器音色/音高).
mute halfsin (已验证修复).
fb_val = ch_out >> N, 扫 N.

目标: 反馈占周期 ~1.2% (对齐 emu), 且音高不变.
检查指标: 反馈占周期% + RMS + 基频(FFT).
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fw_real_sim as F
from fw_real_sim import (fw_decode, fw_apply_patch, fw_key_on, fw_env_tick,
                         fw_calc_step, FW_SIN, INTERNAL_RATE)
from ym2413_wav_gen import (DEFAULT_INST, NAMES, render_emu2413, save_wav,
                            freq_to_fnum_blk)

dump = DEFAULT_INST[11]
FREQ = 440.0
DUR_KO, DUR_KF = 1.0, 1.0

def render_fw(fb_shift):
    """fb_shift: 反馈移位数 (fb_val = ch_out >> fb_shift). mod.tl 不动."""
    p = fw_decode(dump)
    mod, car = fw_apply_patch(p)   # mod.tl = 31-(TL>>1) 保持现状
    fn, bl = freq_to_fnum_blk(FREQ)
    if bl > 0: bl -= 1
    mod['step'] = fw_calc_step(fn, bl, mod['ml'])
    car['step'] = fw_calc_step(fn, bl, car['ml'])
    car['tl'] = max(0, min(31, (60-0)>>1))
    # mute halfsin
    car['wave'] = list(FW_SIN[:32]) + [0]*32
    if p['mod_ws']:
        mod['wave'] = list(FW_SIN[:32]) + [0]*32
    fw_key_on(mod, car)
    out = []
    fbvals = []
    wc = 0
    n = int((DUR_KO+DUR_KF)*INTERNAL_RATE); nk = int(DUR_KO*INTERNAL_RATE)
    for i in range(n):
        if i == nk: F.fw_key_off(mod, car)
        wc = (wc+1) & 0x0F
        # mod (唯一改动: fb_val 用 fb_shift 而非 mod['fb'])
        mod['pos'] = (mod['pos'] + mod['step']) & 0xFFFFFFFF
        midx = (mod['pos'] >> 16) & 0x3F
        midx = (midx + (mod['fb_val'] & 0xFF)) & 0x3F
        mwave = mod['wave'][midx]
        if wc == 0: fw_env_tick(mod)
        mch = ((mwave * (mod['level']+1) * (mod['tl']+1)) >> 10)
        if mch > 127: mch = 127
        elif mch < -128: mch = -128
        if mod['fb'] > 0:
            mod['fb_val'] = max(-128, min(127, mch >> fb_shift))   # <<< 改这里
        else:
            mod['fb_val'] = 0
        # car
        car['pos'] = (car['pos'] + car['step']) & 0xFFFFFFFF
        cidx = (car['pos'] >> 16) & 0x3F
        cidx = (cidx + (mch & 0xFF)) & 0x3F
        cwave = car['wave'][cidx]
        if wc == 0: fw_env_tick(car)
        cch = ((cwave * (car['level']+1) * (car['tl']+1)) >> 10)
        if cch > 127: cch = 127
        elif cch < -128: cch = -128
        total = cch << 1
        if total > 32767: total = 32767
        elif total < -32768: total = -32768
        out.append(total)
        if i < 200: fbvals.append(mod['fb_val'])
    return out, fbvals

def rms(s): return (sum(x*x for x in s)/max(len(s),1))**0.5
def fft_peak_freq(samples, sr):
    """简易 FFT 找基频"""
    try:
        import numpy as np
        x = np.array(samples, dtype=float)
        if len(x) < 1024: return 0
        seg = x[:2048] * np.hanning(2048)
        sp = np.abs(np.fft.rfft(seg))
        freqs = np.fft.rfftfreq(2048, 1/sr)
        peak = np.argmax(sp[1:]) + 1
        return freqs[peak]
    except Exception:
        return -1

emu = render_emu2413(11, FREQ, DUR_KO, DUR_KF, 0)
emu_freq = fft_peak_freq(emu, 22050)

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wav_fbshift")
os.makedirs(OUT, exist_ok=True)
save_wav(os.path.join(OUT, "harp_emu.wav"), emu)

print(f"=== harpsichord 反馈移位扫描 (mod.tl 不动, mute halfsin) ===")
print(f"emu 基频 ≈ {emu_freq:.1f} Hz (440 的某次谐波)\n")
print(f"{'fb_shift':>8} {'反馈占周期%':>11} {'fw_RMS':>8} {'dB':>7} {'基频Hz':>8} {'音高对?':>7}")
print("-" * 60)
for N in [1, 2, 3, 4, 5]:
    out, fbvals = render_fw(N)
    fb_pk = max(abs(x) for x in fbvals)
    fb_ratio = fb_pk/64*100
    r = rms(out)
    d = 20*math.log10(r/rms(emu)) if r > 0 else -99
    f = fft_peak_freq(out, 22050)
    pitch_ok = "✓" if abs(f - emu_freq) < 5 else "✗"
    print(f"{N:>8} {fb_ratio:>10.1f}% {r:>8.1f} {d:>+7.2f} {f:>8.1f} {pitch_ok:>7}")
    save_wav(os.path.join(OUT, f"harp_fb{N}.wav"), out)

print(f"\n目标: 反馈占周期 ~1.2% (emu), 基频匹配 emu ({emu_freq:.1f}Hz)")
print(f"\n输出: {OUT}/harp_fb<N>.wav (N=1现状~5)")
