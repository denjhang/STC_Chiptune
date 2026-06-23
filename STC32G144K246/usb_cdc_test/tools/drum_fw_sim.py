#!/usr/bin/env python3
"""鼓声 PC 仿真 (下位机式): 最终参数固化版.
通过试听确定的参数, 等满意后改下位机.

鼓声方案 (下位机框架内, 寄存器兼容):
- BD:  纯正弦 100Hz, 单 op
- TOM: 正弦 214Hz (fnum=200 blk=0 ml=5)
- SD:  正弦 + 噪声混合 (noise_mix=0.2)
- HH:  纯噪声 (64点假噪声表, 755Hz 查表)
- CYM: 纯噪声 (64点假噪声表, 755Hz 查表, 慢衰减)

噪声: 64 点随机 ±31 表, 16.16 定点步进 (755Hz)
包络: 完整 ADSR (和旋律一样的 env_tick, AR/DR/SL/RR 查表)
"""
import sys, math, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fw_real_sim import (FW_SIN, FW_HALFSIN, fw_calc_step, FW_ML_TABLE,
                          FW_AR_TAB, FW_DR_TAB, FW_RR_TAB)
from ym2413_wav_gen import (render_drum, INTERNAL_RATE, save_wav,
                            DEFAULT_INST, dump_to_patch)

# ============================================================
# 假噪声表 (64 点随机 ±31, 固定种子)
# ============================================================
random.seed(42)
FW_NOISE = [random.randint(-31, 31) for _ in range(64)]

# 噪声步进: 755Hz (16.16 定点)
NOISE_STEP_Q16 = int(755 * 64 * 65536 / INTERNAL_RATE)

# 频率转换常数 (fw_calc_step 内部用)
FW_CONST = 3579545.0 * 64 * 65536 / (72 * 262144 * 22050)

def freq_to_fnum(freq_hz, blk=0, ml=1):
    """目标频率 → fnum (反推, 配合 fw_calc_step)"""
    return int(freq_hz * 2 * 64 * 65536 / ((1 << blk) * ml * FW_CONST * INTERNAL_RATE))

# 双包络辅助 (SD 用)
def _make_env(ar, dr, sl, rr):
    ar_cnt = FW_AR_TAB[ar]; dr_cnt = FW_DR_TAB[dr]
    sl_val = 0 if sl >= 15 else (31 - sl * 2)
    rr_cnt = FW_RR_TAB[rr]
    atk = ar_cnt
    if atk <= 2: level = 31; state = 2; step = dr_cnt
    else: level = 0; state = 1; step = atk
    return {'level': level, 'state': state, 'step': step, 'cnt': 0,
            'dr_cnt': dr_cnt, 'sl': sl_val, 'rr_cnt': rr_cnt}

def _tick_env(st):
    if st['step'] == 0: return
    if st['cnt'] < st['step']: st['cnt'] += 1; return
    st['cnt'] = 0
    if st['state'] == 1:
        if st['level'] < 31: st['level'] += 1
        if st['level'] >= 31: st['state'] = 2; st['step'] = st['dr_cnt']
    elif st['state'] == 2:
        if st['level'] > st['sl']: st['level'] -= 1
        else: st['state'] = 3; st['step'] = st['rr_cnt']
    elif st['state'] == 3:
        if st['level'] > 0: st['level'] -= 1

# ============================================================
# 鼓声参数 (试听确定)
# ============================================================
DRUM_PARAMS = {
    # BD: 纯正弦 100Hz
    'bd':  {'ar':15, 'dr':8,  'sl':6, 'rr':13, 'freq':100, 'noise_mix':0.0},
    # TOM: 正弦 214Hz (fnum=200 blk=0 ml=5)
    'tom': {'ar':15, 'dr':8,  'sl':5, 'rr':9,  'freq':214, 'noise_mix':0.0},
    # SD: FM调制 sine240Hz + noise25Hz(>>7) + FB=2, sine慢包络+noise快衰减
    'sd':  {'ar':13, 'dr':8,  'sl':6, 'rr':8,  'freq':240, 'noise_mix':1.0, 'noise_amp':4,
            'noise_hz':25, 'noise_shift':7, 'fb':2},
    # HH: 纯噪声, 快衰减
    'hh':  {'ar':12, 'dr':8,  'sl':10,'rr':7,  'freq':0,   'noise_mix':1.0},
    # CYM: 纯噪声, 慢衰减
    'cym': {'ar':10, 'dr':10, 'sl':5, 'rr':5,  'freq':0,   'noise_mix':1.0},
}

def render_drum_fw(drum_type, dur=0.8):
    """下位机式鼓声仿真. 鼓声无 keyoff (自然衰减)."""
    p = DRUM_PARAMS[drum_type]
    n = int(dur * INTERNAL_RATE)
    wait_cnt = 0
    out = []

    # SD 特殊: FM 调制 + FB + 两套包络
    if drum_type == 'sd':
        sin_step = fw_calc_step(freq_to_fnum(p['freq'], 0, 1), 0, 1)
        noise_step_q16 = int(p['noise_hz'] * 64 * 65536 / INTERNAL_RATE)
        noise_shift = p['noise_shift']
        fb = p['fb']
        sine_env = _make_env(p['ar'], p['dr'], p['sl'], p['rr'])      # sine 慢
        noise_env = _make_env(15, 8, 6, 13)                            # noise 快
        sin_pos = 0; noise_pos_q16 = 0; fb_val = 0
        for s in range(n):
            wait_cnt = (wait_cnt + 1) & 0x0F
            if wait_cnt == 0:
                _tick_env(sine_env); _tick_env(noise_env)
            noise_pos_q16 = (noise_pos_q16 + noise_step_q16) & 0x3FFFFF
            noise_val = FW_NOISE[(noise_pos_q16 >> 16) & 0x3F]
            noise_out = (noise_val * (noise_env['level'] + 1)) >> noise_shift if noise_env['level'] > 0 else 0
            sin_pos = (sin_pos + sin_step) & 0xFFFFFFFF
            idx = ((sin_pos >> 16) + noise_out + fb_val) & 0x3F
            sin_val = FW_SIN[idx]
            if sine_env['level'] > 0:
                co = max(-128, min(127, (sin_val * (sine_env['level'] + 1) * 32) >> 10))
                if fb > 0:
                    fb_val = max(-128, min(127, (sin_val * (sine_env['level'] + 1)) >> fb))
                else:
                    fb_val = 0
            else:
                co = 0; fb_val = 0
            out.append(max(-32768, min(32767, co << 1)))
        return out

    # 其他鼓声: 单包络
    ar_cnt = FW_AR_TAB[p['ar']]
    dr_cnt = FW_DR_TAB[p['dr']]
    sl = 0 if p['sl'] >= 15 else (31 - p['sl'] * 2)
    rr_cnt = FW_RR_TAB[p['rr']]

    atk = ar_cnt
    level = 0; env_cnt = 0
    if atk == 0:
        env_state = 0
    elif atk <= 2:
        level = 31; env_state = 2; env_step = dr_cnt
    else:
        env_state = 1; env_step = atk

    has_sine = p['freq'] > 0
    has_noise = p['noise_mix'] > 0
    if has_sine:
        ml = 5 if drum_type == 'tom' else 1
        fnum = freq_to_fnum(p['freq'], 0, ml)
        sin_step = fw_calc_step(fnum, 0, ml)
    else:
        sin_step = 0
    sin_pos = 0
    noise_pos_q16 = 0

    for s in range(n):
        wait_cnt = (wait_cnt + 1) & 0x0F
        if wait_cnt == 0 and env_step > 0:
            if env_cnt < env_step:
                env_cnt += 1
            else:
                env_cnt = 0
                if env_state == 1:
                    if level < 31: level += 1
                    if level >= 31: env_state = 2; env_step = dr_cnt
                elif env_state == 2:
                    if level > sl: level -= 1
                    else: env_state = 3; env_step = rr_cnt
                elif env_state == 3:
                    if level > 0: level -= 1

        if has_noise:
            noise_pos_q16 = (noise_pos_q16 + NOISE_STEP_Q16) & 0x3FFFFF
            wave_val = FW_NOISE[(noise_pos_q16 >> 16) & 0x3F]
        elif has_sine:
            sin_pos = (sin_pos + sin_step) & 0xFFFFFFFF
            wave_val = FW_SIN[(sin_pos >> 16) & 0x3F]
        else:
            wave_val = 0

        if level == 0:
            ch_out = 0
        else:
            ch_out = (wave_val * (level + 1) * 32) >> 10
            if ch_out > 127: ch_out = 127
            elif ch_out < -128: ch_out = -128

        out.append(max(-32768, min(32767, ch_out << 1)))

    return out


def main():
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'wav_drum_final')
    os.makedirs(out_dir, exist_ok=True)
    print('鼓声最终参数输出:')
    for dt in ['bd', 'tom', 'sd', 'hh', 'cym']:
        emu = render_drum(dt, 0.3, 0.5)
        fw = render_drum_fw(dt)
        save_wav(os.path.join(out_dir, f'{dt}_emu.wav'), emu)
        save_wav(os.path.join(out_dir, f'{dt}_fw.wav'), fw)
        p = DRUM_PARAMS[dt]
        print('  %s freq=%s noise=%.0f%% AR=%d DR=%d SL=%d RR=%d' % (
            dt.upper(), str(p['freq'])+'Hz' if p['freq'] else 'noise',
            p['noise_mix']*100, p['ar'], p['dr'], p['sl'], p['rr']))

if __name__ == '__main__':
    main()
