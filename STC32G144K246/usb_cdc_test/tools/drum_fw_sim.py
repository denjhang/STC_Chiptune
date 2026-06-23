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

# ============================================================
# 鼓声参数 (试听确定)
# ============================================================
DRUM_PARAMS = {
    # BD: 纯正弦 100Hz
    'bd':  {'ar':15, 'dr':8,  'sl':6, 'rr':13, 'freq':100, 'noise_mix':0.0},
    # TOM: 正弦 214Hz (fnum=200 blk=0 ml=5)
    'tom': {'ar':15, 'dr':8,  'sl':5, 'rr':9,  'freq':214, 'noise_mix':0.0},
    # SD: 正弦 + 20% 噪声
    'sd':  {'ar':13, 'dr':8,  'sl':6, 'rr':8,  'freq':0,   'noise_mix':0.2},
    # HH: 纯噪声, 快衰减
    'hh':  {'ar':12, 'dr':8,  'sl':10,'rr':7,  'freq':0,   'noise_mix':1.0},
    # CYM: 纯噪声, 慢衰减
    'cym': {'ar':10, 'dr':10, 'sl':5, 'rr':5,  'freq':0,   'noise_mix':1.0},
}

def render_drum_fw(drum_type, dur=0.8):
    """下位机式鼓声仿真. 鼓声无 keyoff (自然衰减)."""
    p = DRUM_PARAMS[drum_type]
    ar_cnt = FW_AR_TAB[p['ar']]
    dr_cnt = FW_DR_TAB[p['dr']]
    sl = 0 if p['sl'] >= 15 else (31 - p['sl'] * 2)
    rr_cnt = FW_RR_TAB[p['rr']]

    n = int(dur * INTERNAL_RATE)

    # 包络: AR 高 → 瞬间到顶 (atk<=2)
    atk = ar_cnt
    level = 0; env_cnt = 0
    if atk == 0:
        env_state = 0
    elif atk <= 2:
        level = 31; env_state = 2; env_step = dr_cnt
    else:
        env_state = 1; env_step = atk

    # 相位
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

    wait_cnt = 0
    out = []

    for s in range(n):
        wait_cnt = (wait_cnt + 1) & 0x0F
        if wait_cnt == 0 and env_step > 0:
            if env_cnt < env_step:
                env_cnt += 1
            else:
                env_cnt = 0
                if env_state == 1:  # attack
                    if level < 31: level += 1
                    if level >= 31: env_state = 2; env_step = dr_cnt
                elif env_state == 2:  # decay
                    if level > sl: level -= 1
                    else: env_state = 3; env_step = rr_cnt
                elif env_state == 3:  # sustain (EG=0 继续降)
                    if level > 0: level -= 1

        # 波形: 正弦 + 噪声混合
        sin_val = 0
        if has_sine:
            sin_pos = (sin_pos + sin_step) & 0xFFFFFFFF
            sin_val = FW_SIN[(sin_pos >> 16) & 0x3F]
        noise_val = 0
        if has_noise:
            noise_pos_q16 = (noise_pos_q16 + NOISE_STEP_Q16) & 0x3FFFFF
            noise_val = FW_NOISE[(noise_pos_q16 >> 16) & 0x3F]

        mix = p['noise_mix']
        wave_val = int(sin_val * (1 - mix) + noise_val * mix)

        # 输出
        if level == 0:
            ch_out = 0
        else:
            ch_out = (wave_val * (level + 1) * 32) >> 10
            if ch_out > 127: ch_out = 127
            elif ch_out < -128: ch_out = -128

        total = ch_out << 1
        if total > 32767: total = 32767
        elif total < -32768: total = -32768
        out.append(total)

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
