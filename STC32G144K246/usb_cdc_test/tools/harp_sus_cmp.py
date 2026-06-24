#!/usr/bin/env python3
"""对比 SUSTAIN 衰减方案: cnt=11(线性快) vs 指数步进(level-=level>>k).

方案A: SUSTAIN 用 cnt=11 (RR_TAB[4] 单独给 SUSTAIN 用小值)
方案B: SUSTAIN 指数步进 level -= max(1, level>>3), cnt 固定
       (模拟 emu 指数衰减, 算"简单运算规则"改动)

看哪个 keyon 衰减形态更接近 emu.
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fw_real_sim as F
from fw_real_sim import (fw_decode, fw_apply_patch, fw_key_on, fw_env_tick,
                         fw_calc_step, FW_ISR_RATE, FW_RR_TAB, FW_DR_TAB, save_fw_wav)
from ym2413_wav_gen import (DEFAULT_INST, render_emu2413, save_wav,
                            freq_to_fnum_blk, INTERNAL_RATE)

dump = DEFAULT_INST[11]; FREQ = 440.0; DUR_KO, DUR_KF = 1.0, 1.0

def render(sus_mode):
    """sus_mode: 'cnt11' 线性cnt=11 | 'exp' 指数步进"""
    p = fw_decode(dump); mod, car = fw_apply_patch(p)
    fn, bl = freq_to_fnum_blk(FREQ)
    if bl > 0: bl -= 1
    mod['step'] = fw_calc_step(fn, bl, mod['ml'])
    car['step'] = fw_calc_step(fn, bl, car['ml'])
    car['tl'] = max(0, min(31, (60-0)>>1))
    if sus_mode == 'cnt11':
        car['rel'] = 11   # SUSTAIN 用 cnt=11 (快)
    fw_key_on(mod, car)
    n = int((DUR_KO+DUR_KF)*FW_ISR_RATE); nk = int(DUR_KO*FW_ISR_RATE)
    out = []; wc = 0
    # 指数模式需要 hack env_tick, 这里手动渲染
    exp_mode = (sus_mode == 'exp')
    for s in range(n):
        if s == nk: F.fw_key_off(mod, car)
        wc = (wc+1) & 0x0F
        # 手动 fw_render_fm 以便 exp 模式改 sustain 步进
        if mod['step']:
            mod['pos'] = (mod['pos']+mod['step']) & 0xFFFF
            idx = ((mod['pos']>>8) + (mod['fb_val']&0xFF)) & 0x3F
            mw = mod['wave'][idx]
            if wc == 0: fw_env_tick(mod)
            mch = max(-128, min(127, (mw*(mod['level']+1)*(mod['tl']+1))>>10))
            mod['fb_val'] = max(-128, min(127, mch>>mod['fb'])) if mod['fb']>0 else 0
        else: mch = 0
        if car['step']:
            car['pos'] = (car['pos']+car['step']) & 0xFFFF
            idx = ((car['pos']>>8) + (mch&0xFF)) & 0x3F
            cw = car['wave'][idx]
            # exp 模式: 手动 tick car (指数步进)
            if wc == 0:
                if exp_mode and car['env_state'] == 3:  # sustain 指数
                    if car['env_step'] > 0:
                        if car['env_cnt'] < car['env_step']:
                            car['env_cnt'] += 1
                        else:
                            car['env_cnt'] = 0
                            car['level'] = max(0, car['level'] - max(1, car['level']>>3))
                            if car['level'] == 0: car['env_state'] = 0
                else:
                    fw_env_tick(car)
            cch = max(-128, min(127, (cw*(car['level']+1)*(car['tl']+1))>>10))
        else: cch = 0
        if car['env_state'] == 4 and car['level'] == 0: car['env_state'] = 0
        total = max(-32768, min(32767, cch << 1))
        out.append(total)
    return out

def curve(s, sr, ms=50):
    seg = int(sr*ms/1000)
    return [(i*1000/sr, (sum(x*x for x in s[i:i+seg])/max(len(s[i:i+seg]),1))**0.5) for i in range(0,len(s),seg) if s[i:i+seg]]
def rms(s): return (sum(x*x for x in s)/max(len(s),1))**0.5

emu = render_emu2413(11, FREQ, DUR_KO, DUR_KF, 0)
fw_cnt = render('cnt11')
fw_exp = render('exp')

ec = curve(emu, INTERNAL_RATE); cc = curve(fw_cnt, FW_ISR_RATE); xc = curve(fw_exp, FW_ISR_RATE)
ep = max(r for _,r in ec); cp = max(r for _,r in cc); xp = max(r for _,r in xc)

print(f"=== SUSTAIN 衰减方案对比 (keyon 衰减形态) ===")
print(f"{'t_ms':>5} {'emu':>7} {'cnt11':>7} {'exp':>7}")
for (te,re),(_,rc),(_,rx) in zip(ec,cc,xc):
    ed = 20*math.log10(re/ep) if re>0 else -99
    cd = 20*math.log10(rc/cp) if rc>0 else -99
    xd = 20*math.log10(rx/xp) if rx>0 else -99
    flag = ''
    if 900 <= te <= 1000: flag = ' <- keyon尾'
    if 1000 <= te <= 1100: flag = ' <- release'
    print(f'{te:>5.0f} {ed:>+6.1f} {cd:>+6.1f} {xd:>+6.1f}{flag}')

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'wav_sus_cmp')
os.makedirs(OUT, exist_ok=True)
save_wav(os.path.join(OUT, 'harp_emu.wav'), emu)
save_fw_wav(os.path.join(OUT, 'harp_fw_cnt11.wav'), fw_cnt)
save_fw_wav(os.path.join(OUT, 'harp_fw_exp.wav'), fw_exp)
print(f'\n输出: {OUT}')
print(f'  emu / fw_cnt11(线性快) / fw_exp(指数步进)')
