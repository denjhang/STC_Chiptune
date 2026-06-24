#!/usr/bin/env python3
"""验证 sus_hold 查表机制 (扫描时间常数缩放).

sus_hold[32] 表固定 (从 emu tau=221 反推), 扫描一个全局缩放因子 scale
(sus_hold_eff[n] = sus_hold[n] / scale), 找最贴合 emu 的.

机制: SUSTAIN 阶段 sus_cnt++, 达到 sus_hold[level] 则 level--
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fw_real_sim as F
from fw_real_sim import (fw_decode, fw_apply_patch, fw_key_on, fw_env_tick,
                         fw_calc_step, FW_ISR_RATE, FW_RR_TAB, save_fw_wav)
from ym2413_wav_gen import (DEFAULT_INST, render_emu2413, save_wav,
                            freq_to_fnum_blk, INTERNAL_RATE)

# sus_hold 基础表 (tau=221ms 反推)
SUS_HOLD_BASE = [0, 305, 305, 178, 126, 98, 80, 68, 59, 52, 46, 42, 38, 35, 33,
                 30, 28, 27, 25, 24, 23, 21, 20, 20, 19, 18, 17, 17, 16, 15, 15, 14]

dump = DEFAULT_INST[11]; FREQ = 440.0; DUR_KO, DUR_KF = 1.0, 1.0

def render(scale):
    """scale: sus_hold 缩放 (越大衰减越快)"""
    sus_hold = [max(1, int(h/scale)) for h in SUS_HOLD_BASE]
    p = fw_decode(dump); mod, car = fw_apply_patch(p)
    fn, bl = freq_to_fnum_blk(FREQ)
    if bl > 0: bl -= 1
    mod['step'] = fw_calc_step(fn, bl, mod['ml'])
    car['step'] = fw_calc_step(fn, bl, car['ml'])
    car['tl'] = max(0, min(31, (60-0)>>1))
    fw_key_on(mod, car)
    car_sus_cnt = 0
    n = int((DUR_KO+DUR_KF)*FW_ISR_RATE); nk = int(DUR_KO*FW_ISR_RATE)
    out = []; wc = 0
    for s in range(n):
        if s == nk: F.fw_key_off(mod, car)
        wc = (wc+1) & 0x0F
        # mod 正常
        if mod['step']:
            mod['pos'] = (mod['pos']+mod['step']) & 0xFFFF
            midx = ((mod['pos']>>8)+(mod['fb_val']&0xFF)) & 0x3F
            mw = mod['wave'][midx]
            if wc == 0: fw_env_tick(mod)
            mch = max(-128, min(127, (mw*(mod['level']+1)*(mod['tl']+1))>>10))
            mod['fb_val'] = max(-128, min(127, mch>>mod['fb'])) if mod['fb']>0 else 0
        else: mch = 0
        # car: sustain 用 sus_hold
        if car['step']:
            car['pos'] = (car['pos']+car['step']) & 0xFFFF
            cidx = ((car['pos']>>8)+(mch&0xFF)) & 0x3F
            cw = car['wave'][cidx]
            if wc == 0:
                if car['env_state'] == 3:  # sustain
                    if car['level'] > 0:
                        car_sus_cnt += 1
                        if car_sus_cnt >= sus_hold[car['level']]:
                            car_sus_cnt = 0; car['level'] -= 1
                            if car['level'] == 0: car['env_state'] = 0
                else:
                    fw_env_tick(car); car_sus_cnt = 0
            cch = max(-128, min(127, (cw*(car['level']+1)*(car['tl']+1))>>10))
        else: cch = 0
        if car['env_state'] == 4 and car['level'] == 0: car['env_state'] = 0
        out.append(max(-32768, min(32767, cch << 1)))
    return out

def curve(s, sr, ms=50):
    seg = int(sr*ms/1000)
    return [(i*1000/sr, (sum(x*x for x in s[i:i+seg])/max(len(s[i:i+seg]),1))**0.5) for i in range(0,len(s),seg) if s[i:i+seg]]

emu = render_emu2413(11, FREQ, DUR_KO, DUR_KF, 0)
ec = curve(emu, INTERNAL_RATE); ep = max(r for _,r in ec)
targets = {300:-8.2, 500:-13.6, 700:-19.1, 950:-25.9, 1000:-27.2}

print(f"=== sus_hold 缩放扫描 (tau=221ms 基础表) ===")
print(f"emu: @300{-8.2} @500{-13.6} @700{-19.1} @950{-25.9}\n")
print(f"{'scale':>7} {'@300':>6} {'@500':>6} {'@700':>6} {'@950':>6} {'@1000':>7} {'score':>7}")
print("-" * 52)
best=None; OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),'wav_sushold'); os.makedirs(OUT,exist_ok=True)
save_wav(os.path.join(OUT,'harp_emu.wav'), emu)
for scale in [0.5, 0.7, 1.0, 1.3, 1.5, 1.8, 2.0]:
    out = render(scale); c = curve(out, FW_ISR_RATE); pk = max(r for _,r in c)
    def db_at(ms):
        for t,r in c:
            if abs(t-ms)<30: return 20*math.log10(r/pk) if r>0 else -99
        return -99
    ds = {m:db_at(m) for m in targets}
    score = sum(abs(ds[m]-targets[m]) for m in targets)
    print(f"{scale:>7} {ds[300]:>+6.1f} {ds[500]:>+6.1f} {ds[700]:>+6.1f} {ds[950]:>+6.1f} {ds[1000]:>+7.1f} {score:>7.1f}")
    save_fw_wav(os.path.join(OUT, f'harp_sc{scale}.wav'), out)
    if best is None or score < best[0]: best=(score, scale)
print(f'\n最佳 scale={best[1]} (score={best[0]:.1f})')
