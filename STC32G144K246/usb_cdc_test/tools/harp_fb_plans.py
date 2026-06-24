#!/usr/bin/env python3
"""过反馈两方案对比, 各出 wav.

方案1 (FB移位): fb_val = ch_out >> (FB + 4)  [原 >>FB]
方案2 (mod tl): mod.tl = tl_raw >> 1         [原 31-(tl_raw>>1)]
方案3 (两方案合)
原版对照
都用已固化的 sus_hold/rel_hold (sustain/release 已对齐).
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fw_real_sim as F
from fw_real_sim import (fw_decode, fw_apply_patch, fw_key_on, fw_env_tick,
                         fw_calc_step, FW_ISR_RATE, FW_SIN, FW_SUS_HOLD,
                         FW_REL_HOLD, FW_AR_TAB, FW_DR_TAB, FW_RR_TAB,
                         FW_ML_TABLE, save_fw_wav)
from ym2413_wav_gen import (DEFAULT_INST, render_emu2413, save_wav,
                            freq_to_fnum_blk, INTERNAL_RATE)

dump = DEFAULT_INST[11]; FREQ = 440.0; DUR_KO, DUR_KF = 1.0, 1.0

def render(fb_shift_extra=0, mod_tl_direct=False):
    """fb_shift_extra: FB额外移位 (0=原>>FB, 4=方案1>>(FB+4))
       mod_tl_direct: True=方案2 (tl=tl_raw>>1), False=原(31-(tl_raw>>1))"""
    p = fw_decode(dump)
    # 手动 apply, 控制 mod tl
    def make_op(ml_val, tl_raw, fb, eg, ws, ar, dr, sl, rr, is_mod=False):
        if is_mod and mod_tl_direct:
            tl = max(0, min(31, tl_raw >> 1))
        else:
            tl = max(0, min(31, 31 - (tl_raw >> 1)))
        return {
            'ml': FW_ML_TABLE[ml_val], 'tl': tl, 'fb': fb, 'eg_type': eg,
            'wave': F.FW_HALFSIN if ws else FW_SIN,
            'atk': FW_AR_TAB[ar], 'decy': FW_DR_TAB[dr],
            'sul': 0 if sl >= 15 else (31 - sl * 2), 'rel': FW_RR_TAB[rr],
            'pos': 0, 'step': 0, 'fb_val': 0,
            'env_state': 0, 'env_cnt': 0, 'env_step': 0, 'level': 0,
            'sus_flag': 0, 'sus_cnt': 0,
        }
    mod = make_op(p['mod_ml'], p['mod_tl'], p['mod_fb'], p['mod_eg'], p['mod_ws'],
                  p['mod_ar'], p['mod_dr'], p['mod_sl'], p['mod_rr'], is_mod=True)
    car = make_op(p['car_ml'], 0, 0, p['car_eg'], p['car_ws'],
                  p['car_ar'], p['car_dr'], p['car_sl'], p['car_rr'])
    fn, bl = freq_to_fnum_blk(FREQ)
    if bl > 0: bl -= 1
    mod['step'] = fw_calc_step(fn, bl, mod['ml'])
    car['step'] = fw_calc_step(fn, bl, car['ml'])
    car['tl'] = max(0, min(31, (60-0)>>1))
    fw_key_on(mod, car)
    n = int((DUR_KO+DUR_KF)*FW_ISR_RATE); nk = int(DUR_KO*FW_ISR_RATE)
    out = []; wc = 0
    for s in range(n):
        if s == nk: F.fw_key_off(mod, car)
        wc = (wc+1) & 0x0F
        # 手动 render_fm, FB 用额外移位
        total = 0
        if not (car['env_state'] == 4 and car['level'] == 0):
            if mod['step']:
                mod['pos'] = (mod['pos']+mod['step']) & 0xFFFF
                midx = ((mod['pos']>>8)+(mod['fb_val']&0xFF)) & 0x3F
                mw = mod['wave'][midx]
                if wc == 0: fw_env_tick(mod)
                mch = max(-128, min(127, (mw*(mod['level']+1)*(mod['tl']+1))>>10))
                if mod['fb']>0:
                    mod['fb_val'] = max(-128, min(127, mch >> (mod['fb']+fb_shift_extra)))
                else: mod['fb_val'] = 0
            else: mch = 0
            if car['step']:
                car['pos'] = (car['pos']+car['step']) & 0xFFFF
                cidx = ((car['pos']>>8)+(mch&0xFF)) & 0x3F
                cw = car['wave'][cidx]
                if wc == 0: fw_env_tick(car)
                cch = max(-128, min(127, (cw*(car['level']+1)*(car['tl']+1))>>10))
            else: cch = 0
            total = cch
        else: car['env_state'] = 0
        out.append(max(-32768, min(32767, total << 1)))
    return out

def rms(s): return (sum(x*x for x in s)/max(len(s),1))**0.5

emu = render_emu2413(11, FREQ, DUR_KO, DUR_KF, 0)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'wav_fb_plans')
os.makedirs(OUT, exist_ok=True)
save_wav(os.path.join(OUT, 'harp_emu.wav'), emu)

versions = [
    ('orig',    0, False, '原版 (>>FB, tl=31-(tl>>1))'),
    ('plan1',   4, False, '方案1: FB+4 移位'),
    ('plan2',   0, True,  '方案2: mod tl = tl>>1'),
    ('plan12',  4, True,  '方案1+2 合'),
]
print(f"=== 过反馈两方案对比 (harpsichord) ===\n")
for name, fbs, mtl, desc in versions:
    out = render(fbs, mtl)
    save_fw_wav(os.path.join(OUT, f'harp_{name}.wav'), out)
    print(f"  harp_{name}.wav  ({desc})  RMS={rms(out):.1f}")

print(f"\n输出: {OUT}/")
print(f"  harp_emu.wav (参考)")
print(f"  harp_orig.wav / harp_plan1.wav / harp_plan2.wav / harp_plan12.wav")
print(f"\n注: 过反馈需试听判断 (非简单 RMS 检测), 对照 emu 听哪个最接近")
