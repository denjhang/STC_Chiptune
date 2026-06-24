#!/usr/bin/env python3
"""扫描指数系数 k (level -= level>>k), 找最接近 emu SUSTAIN 衰减的值.

emu: 输出指数衰减 (eg_out 线性 + exp转换)
fw : level -= level>>k 模拟指数 (k 越小衰减越快)
  k=2: level/4 步进 (快)
  k=3: level/8 (中)
  k=4: level/16 (慢)
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fw_real_sim as F
from fw_real_sim import (fw_decode, fw_apply_patch, fw_key_on, fw_env_tick,
                         fw_calc_step, FW_ISR_RATE, FW_RR_TAB, save_fw_wav)
from ym2413_wav_gen import (DEFAULT_INST, render_emu2413, save_wav,
                            freq_to_fnum_blk, INTERNAL_RATE)

dump = DEFAULT_INST[11]; FREQ = 440.0; DUR_KO, DUR_KF = 1.0, 1.0

def render(k, sus_cnt=2):
    """k: 指数系数 (sustain 阶段 level -= max(1,level>>k), 每 sus_cnt×16 采样一步)"""
    p = fw_decode(dump); mod, car = fw_apply_patch(p)
    fn, bl = freq_to_fnum_blk(FREQ)
    if bl > 0: bl -= 1
    mod['step'] = fw_calc_step(fn, bl, mod['ml'])
    car['step'] = fw_calc_step(fn, bl, car['ml'])
    car['tl'] = max(0, min(31, (60-0)>>1))
    fw_key_on(mod, car)
    n = int((DUR_KO+DUR_KF)*FW_ISR_RATE); nk = int(DUR_KO*FW_ISR_RATE)
    out = []; wc = 0; sus_scnt = 0
    for s in range(n):
        if s == nk: F.fw_key_off(mod, car)
        wc = (wc+1) & 0x0F
        # mod 正常 tick
        if mod['step']:
            mod['pos'] = (mod['pos']+mod['step']) & 0xFFFF
            idx = ((mod['pos']>>8) + (mod['fb_val']&0xFF)) & 0x3F
            mw = mod['wave'][idx]
            if wc == 0: fw_env_tick(mod)
            mch = max(-128, min(127, (mw*(mod['level']+1)*(mod['tl']+1))>>10))
            mod['fb_val'] = max(-128, min(127, mch>>mod['fb'])) if mod['fb']>0 else 0
        else: mch = 0
        # car: sustain 阶段指数步进
        if car['step']:
            car['pos'] = (car['pos']+car['step']) & 0xFFFF
            idx = ((car['pos']>>8) + (mch&0xFF)) & 0x3F
            cw = car['wave'][idx]
            if wc == 0:
                if car['env_state'] == 3 and car['env_step'] > 0:  # sustain
                    sus_scnt += 1
                    if sus_scnt >= sus_cnt:
                        sus_scnt = 0
                        car['level'] = max(0, car['level'] - max(1, car['level']>>k))
                        if car['level'] == 0: car['env_state'] = 0
                else:
                    fw_env_tick(car)
                    sus_scnt = 0
            cch = max(-128, min(127, (cw*(car['level']+1)*(car['tl']+1))>>10))
        else: cch = 0
        if car['env_state'] == 4 and car['level'] == 0: car['env_state'] = 0
        out.append(max(-32768, min(32767, cch << 1)))
    return out

def curve(s, sr, ms=50):
    seg = int(sr*ms/1000)
    return [(i*1000/sr, (sum(x*x for x in s[i:i+seg])/max(len(s[i:i+seg]),1))**0.5) for i in range(0,len(s),seg) if s[i:i+seg]]

emu = render_emu2413(11, FREQ, DUR_KO, DUR_KF, 0)
ec = curve(emu, INTERNAL_RATE)
ep = max(r for _,r in ec)

# 目标: keyon 尾 (@950ms) 接近 emu -26dB
print(f"=== 指数系数 k 扫描 (sustain: level-=level>>k) ===")
print(f"emu @950ms = -26dB, @1000ms=-31dB (keyon尾目标)\n")
print(f"{'k':>3} {'@500ms':>8} {'@950ms':>8} {'@1000ms':>8} {'score':>7}")
print("-" * 40)
best = None
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'wav_expk')
os.makedirs(OUT, exist_ok=True)
for k in [2, 3, 4]:
    for sc in [1, 2]:
        out = render(k, sc)
        c = curve(out, FW_ISR_RATE)
        pk = max(r for _,r in c)
        def db_at(ms):
            for t,r in c:
                if abs(t-ms) < 30: return 20*math.log10(r/pk) if r>0 else -99
            return -99
        d500, d950, d1000 = db_at(500), db_at(950), db_at(1000)
        # score: 与 emu (-13.7, -26.1, -31.4) 的差
        score = abs(d500+13.7) + abs(d950+26.1) + abs(d1000+31.4)
        label = f'k{k}_sc{sc}'
        print(f'{label:>5} {d500:>+8.1f} {d950:>+8.1f} {d1000:>+8.1f} {score:>7.1f}')
        save_fw_wav(os.path.join(OUT, f'harp_{label}.wav'), out)
        if best is None or score < best[0]: best = (score, k, sc, label)

print(f'\n最佳: {best[3]} (score={best[0]:.1f})')
save_wav(os.path.join(OUT, 'harp_emu.wav'), emu)
print(f'输出: {OUT}')
