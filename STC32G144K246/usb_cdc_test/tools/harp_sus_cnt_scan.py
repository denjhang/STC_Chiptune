#!/usr/bin/env python3
"""SUSTAIN 阶段用独立 cnt (不改运算), 扫描找 harpsichord 对齐值.

env_tick 第140行: 进 SUSTAIN 时 env_step = SR_TAB[rr] (新表, 比 RR_TAB 快)
RELEASE 保持: 速率 7 (sus_flag?5:EG?RR:7)
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fw_real_sim as F
from fw_real_sim import (fw_decode, fw_apply_patch, fw_key_on, fw_env_tick,
                         fw_calc_step, FW_ISR_RATE, FW_RR_TAB, FW_DR_TAB, save_fw_wav)
from ym2413_wav_gen import (DEFAULT_INST, render_emu2413, save_wav,
                            freq_to_fnum_blk, INTERNAL_RATE)

dump = DEFAULT_INST[11]; FREQ = 440.0; DUR_KO, DUR_KF = 1.0, 1.0

def render(sus_cnt):
    """sus_cnt: SUSTAIN 阶段 env_step (覆盖 car 的 rel, 仅 sustain 用)"""
    p = fw_decode(dump); mod, car = fw_apply_patch(p)
    fn, bl = freq_to_fnum_blk(FREQ)
    if bl > 0: bl -= 1
    mod['step'] = fw_calc_step(fn, bl, mod['ml'])
    car['step'] = fw_calc_step(fn, bl, car['ml'])
    car['tl'] = max(0, min(31, (60-0)>>1))
    fw_key_on(mod, car)
    # hack: 给 car 加一个 sustain 专用 step (env_tick 用 env_step)
    car['sus_step'] = sus_cnt
    n = int((DUR_KO+DUR_KF)*FW_ISR_RATE); nk = int(DUR_KO*FW_ISR_RATE)
    out = []; wc = 0
    for s in range(n):
        if s == nk: F.fw_key_off(mod, car)
        wc = (wc+1) & 0x0F
        # 手动渲染 car, 在 decay->sustain 转换时用 sus_step
        if mod['step']:
            mod['pos'] = (mod['pos']+mod['step']) & 0xFFFF
            midx = ((mod['pos']>>8) + (mod['fb_val']&0xFF)) & 0x3F
            mw = mod['wave'][midx]
            if wc == 0: fw_env_tick(mod)
            mch = max(-128, min(127, (mw*(mod['level']+1)*(mod['tl']+1))>>10))
            mod['fb_val'] = max(-128, min(127, mch>>mod['fb'])) if mod['fb']>0 else 0
        else: mch = 0
        if car['step']:
            car['pos'] = (car['pos']+car['step']) & 0xFFFF
            cidx = ((car['pos']>>8) + (mch&0xFF)) & 0x3F
            cw = car['wave'][cidx]
            if wc == 0:
                # 改写的 env_tick: sustain 用 sus_step
                step = car['env_step']
                if step == 0: pass
                elif car['env_cnt'] < step: car['env_cnt'] += 1
                else:
                    car['env_cnt'] = 0; st = car['env_state']
                    if st == 1:
                        if car['level'] < 31: car['level'] += 1
                        if car['level'] >= 31: car['env_state']=2; car['env_step']=car['decy']
                    elif st == 2:
                        if car['level'] > car['sul']: car['level'] -= 1
                        else: car['env_state']=3; car['env_step'] = 0 if car['eg_type'] else car['sus_step']  # <<< sus_step
                    elif st == 3:
                        if car['level'] > 0: car['level'] -= 1
                    elif st == 4:
                        if car['level'] > 0: car['level'] -= 1
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
print(f"emu keyon衰减: @500ms=-13.7 @950ms=-26.1 @1000ms=-31.4\n")
print(f"{'sus_cnt':>8} {'@300':>6} {'@500':>6} {'@700':>6} {'@950':>6} {'@1000':>6} {'score':>7}")
print("-" * 50)
best=None; OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),'wav_suscnt'); os.makedirs(OUT,exist_ok=True)
save_wav(os.path.join(OUT,'harp_emu.wav'), emu)
targets = {300:-8.2, 500:-13.7, 700:-19.2, 950:-26.1, 1000:-31.4}
for sc in [5, 8, 10, 12, 15, 20, 25, 30]:
    out = render(sc); c = curve(out, FW_ISR_RATE); pk = max(r for _,r in c)
    def db_at(ms):
        for t,r in c:
            if abs(t-ms)<30: return 20*math.log10(r/pk) if r>0 else -99
        return -99
    ds = {m:db_at(m) for m in targets}
    score = sum(abs(ds[m]-targets[m]) for m in targets)
    print(f"{sc:>8} {ds[300]:>+6.1f} {ds[500]:>+6.1f} {ds[700]:>+6.1f} {ds[950]:>+6.1f} {ds[1000]:>+6.1f} {score:>7.1f}")
    save_fw_wav(os.path.join(OUT, f'harp_sus{sc}.wav'), out)
    if best is None or score < best[0]: best=(score, sc)
print(f'\n最佳 sus_cnt={best[1]} (score={best[0]:.1f})')
