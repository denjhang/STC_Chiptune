#!/usr/bin/env python3
"""render_fw_real: 严格 1:1 忠实下位机 da1cf8a 的 PC 仿真.
所有限制完全照搬, 不偷用 emu 精度.
用于看下位机真实输出 vs emu2413 的偏差."""
import sys, math, os, struct, wave
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ym2413_wav_gen import (DEFAULT_INST, NAMES, dump_to_patch, INTERNAL_RATE,
                            TLL_TABLE, ml_table, EG_MUTE, render_emu2413, save_wav)


def save_fw_wav(filepath, samples):
    """保存下位机仿真输出 (采样率 FW_ISR_RATE=22050, 不降采样, 只归一化).
    不能用 ym2413_wav_gen.save_wav (它假设输入是 49716)."""
    peak = max(abs(s) for s in samples) if samples else 1
    if peak == 0:
        norm = samples
    else:
        scale = (32767 * 0.85) / peak
        norm = [int(max(-32768, min(32767, s * scale))) for s in samples]
    with wave.open(filepath, 'w') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(FW_ISR_RATE)
        w.writeframes(struct.pack(f'<{len(norm)}h', *norm))

# ============================================================
# 下位机真实表 (1:1 照搬 da1cf8a ym2413.c)
# ============================================================
# 64 点 s8 波形, 振幅 ±31 (不是 ±127!)
FW_SIN = [
     0,  3,  6,  9, 12, 15, 17, 20, 22, 24, 26, 28, 29, 30, 31, 31,
    31, 31, 31, 30, 29, 28, 26, 24, 22, 20, 17, 15, 12,  9,  6,  3,
     0, -3, -6, -9,-12,-15,-17,-20,-22,-24,-26,-28,-29,-30,-31,-31,
   -31,-31,-31,-30,-29,-28,-26,-24,-22,-20,-17,-15,-12, -9, -6, -3
]
# halfsin: 负半周静音 (对齐 emu2413.c:383-387, halfsin后半周=0xfff→输出0)
# 注意: 旧版用镜像(取绝对值)是 bug, 导致 carrier 后半周输出正值→直流偏置→失真
FW_HALFSIN = [
     0,  3,  6,  9, 12, 15, 17, 20, 22, 24, 26, 28, 29, 30, 31, 31,
    31, 31, 31, 30, 29, 28, 26, 24, 22, 20, 17, 15, 12,  9,  6,  3,
     0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
     0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0
]
# env_cnt: 下位机旧 ADSR 速度表 (已废弃, 保留作参考)
FW_ENV_CNT = [0, 1, 2, 3, 4, 5, 7, 10, 13, 20, 29, 43, 64, 86, 128, 255]
# AR/DR/RR 三张表 (反推自 emu2413 速率, 2026-06-25 校准: 旧表 RR/DR 4~10 偏慢 2.2×)
FW_AR_TAB = [0, 116, 58, 29, 14, 7, 4, 2, 1, 1, 1, 1, 1, 1, 1, 1]
FW_DR_TAB = [0, 255, 255, 255, 75, 38, 19, 9, 5, 2, 1, 1, 1, 1, 1, 1]
FW_RR_TAB = [0, 255, 255, 255, 76, 38, 19, 9, 5, 2, 1, 1, 1, 1, 1, 1]
# SUSTAIN 指数衰减查表 (2026-06-25 新增): sus_hold[level] = 该 level 停留几个 round-robin tick
# 模拟 emu 指数输出衰减 (fw level 线性, 必须查表拟合指数). tau≈88ms (scale=0.4 实测对齐 emu)
# SUSTAIN 阶段: sus_cnt++; if (sus_cnt >= sus_hold[level]) { sus_cnt=0; level--; }
FW_SUS_HOLD = [1, 122, 122, 71, 50, 39, 32, 27, 23, 20, 18, 16, 15, 14, 13,
               12, 11, 10, 10, 9, 9, 8, 8, 8, 7, 7, 6, 6, 6, 6, 6, 5]
# ml_table: 下位机自己的 (和 emu 不同!)
FW_ML_TABLE = [1, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 24, 24, 24]
# step 常数 (8.8 定点, 1:1 照搬 ym2413.c:237, blk-1 修正)
# pos/step 都是 u16, idx = pos>>8 & 0x3F, 一个周期 = 64×256 = 16384
FW_STEP_CONST = 3579545.0 * 64.0 * 256.0 / (72.0 * 262144.0 * 22050.0)
# 下位机 ISR 采样率 (不是 emu 的 49716!)
FW_ISR_RATE = 22050

def fw_decode(dump):
    """1:1 照搬 ym_decode_patch (注意: 不解码 KR/AM/PM/KL, 下位机没用)"""
    return {
        'mod_ml': dump[0] & 0x0F, 'mod_eg': (dump[0] >> 5) & 1,
        'car_ml': dump[1] & 0x0F, 'car_eg': (dump[1] >> 5) & 1,
        'mod_tl': dump[2] & 0x3F, 'mod_fb': dump[3] & 0x07,
        'mod_ws': (dump[3] >> 3) & 1, 'car_ws': (dump[3] >> 4) & 1,
        'mod_ar': (dump[4] >> 4) & 0x0F, 'mod_dr': dump[4] & 0x0F,
        'car_ar': (dump[5] >> 4) & 0x0F, 'car_dr': dump[5] & 0x0F,
        'mod_sl': (dump[6] >> 4) & 0x0F, 'mod_rr': dump[6] & 0x0F,
        'car_sl': (dump[7] >> 4) & 0x0F, 'car_rr': dump[7] & 0x0F,
    }

def fw_apply_patch(p):
    """1:1 照搬 ym_apply_patch. 返回 (mod_op, car_op) 字典"""
    def make_op(ml_val, tl_raw, fb, eg, ws, ar, dr, sl, rr):
        return {
            'ml': FW_ML_TABLE[ml_val],
            'tl': max(0, min(31, 31 - (tl_raw >> 1))),  # mod_tl: 31 - tl/2
            'fb': fb, 'eg_type': eg,
            'wave': FW_HALFSIN if ws else FW_SIN,
            'atk': FW_AR_TAB[ar], 'decy': FW_DR_TAB[dr],
            'sul': 0 if sl >= 15 else (31 - sl * 2),
            'rel': FW_RR_TAB[rr],
            # 运行时状态
            'pos': 0, 'step': 0, 'fb_val': 0,
            'env_state': 0, 'env_cnt': 0, 'env_step': 0, 'level': 0,
            'sus_flag': 0, 'sus_cnt': 0,  # sus_cnt: SUSTAIN 指数查表计数器
        }
    mod = make_op(p['mod_ml'], p['mod_tl'], p['mod_fb'], p['mod_eg'], p['mod_ws'],
                  p['mod_ar'], p['mod_dr'], p['mod_sl'], p['mod_rr'])
    car = make_op(p['car_ml'], 0, 0, p['car_eg'], p['car_ws'],
                  p['car_ar'], p['car_dr'], p['car_sl'], p['car_rr'])
    return mod, car

def fw_calc_step(fnum, blk, ml):
    """1:1 照搬 ym_calc_step (float 算一次, 8.8 定点, 返回 u16)"""
    base = fnum * (1 << blk) * FW_STEP_CONST
    return int(base * ml / 2.0) & 0xFFFF

def fw_key_on(mod, car):
    """1:1 照搬 ym_key_on (和下位机 commit 1f45584/d84dee0 同步)
    env_cnt=0 立即开始; atk<=2 (AR>=7) 瞬间到顶"""
    mod['pos'] = 0; car['pos'] = 0
    mod['fb_val'] = 0
    for op in (mod, car):
        op['level'] = 0; op['env_cnt'] = 0
        if op['atk'] == 0:
            op['env_state'] = 0; op['level'] = 0
        elif op['atk'] <= 2:
            op['level'] = 31; op['env_state'] = 2; op['env_step'] = op['decy']
        else:
            op['env_state'] = 1; op['env_step'] = op['atk']

def fw_key_off(mod, car):
    """1:1 照搬 ym_key_off (RELEASE 速率对齐 emu get_parameter_rate line 505-512)
    sus_flag -> 5; EG=1 -> RR(rr); EG=0 -> 固定 7"""
    mod['env_state'] = 4; car['env_state'] = 4
    # RELEASE 速率: sus_flag?5 : (EG? RR : 7)
    mod['env_step'] = FW_RR_TAB[5] if mod['sus_flag'] else (mod['rel'] if mod['eg_type'] else FW_RR_TAB[7])
    car['env_step'] = FW_RR_TAB[5] if car['sus_flag'] else (car['rel'] if car['eg_type'] else FW_RR_TAB[7])

def fw_env_tick(op):
    """1:1 照搬 ym_env_tick (加法计数器, 和下位机 commit 1f45584 同步)"""
    step = op['env_step']
    if step == 0:
        return   # sustain EG=0 保持
    cnt = op['env_cnt']
    if cnt < step:
        op['env_cnt'] = cnt + 1
        return
    op['env_cnt'] = 0
    st = op['env_state']
    if st == 1:  # attack
        if op['level'] < 31: op['level'] += 1
        if op['level'] >= 31:
            op['env_state'] = 2; op['env_step'] = op['decy']
    elif st == 2:  # decay
        if op['level'] > op['sul']:
            op['level'] -= 1
        else:
            op['env_state'] = 3
            op['env_step'] = 0 if op['eg_type'] else 1  # EG=1保持; EG=0 进 sustain, env_step=1 让 sus_hold 接管速率
    elif st == 3:  # sustain (EG=0 non-sustaining: 指数查表衰减; EG=1 不会进这里因 env_step=0)
        if op['level'] > 0:
            op['sus_cnt'] += 1
            if op['sus_cnt'] >= FW_SUS_HOLD[op['level']]:
                op['sus_cnt'] = 0
                op['level'] -= 1
                if op['level'] == 0:
                    op['env_state'] = 0
    elif st == 4:  # release
        if op['level'] > 0: op['level'] -= 1

def fw_render_fm(mod, car, wait_tick, ch):
    """1:1 照搬 ym_render_fm (8.8 定点). 返回 s16 输出"""
    if mod['step'] == 0:
        return 0
    # OP1 (modulator) — pos/step u16, idx = pos>>8 & 0x3F
    mod['pos'] = (mod['pos'] + mod['step']) & 0xFFFF
    idx = (mod['pos'] >> 8) & 0x3F
    idx = (idx + (mod['fb_val'] & 0xFF)) & 0x3F
    wave_val = mod['wave'][idx]
    if wait_tick == (ch & 0x0F):
        fw_env_tick(mod)
    # 输出公式: (wave × (level+1) × (tl+1)) >> 10, 结果 s8
    ch_out = ((wave_val * (mod['level'] + 1) * (mod['tl'] + 1)) >> 10)
    # s8 截断
    if ch_out > 127: ch_out = 127
    elif ch_out < -128: ch_out = -128
    if mod['fb'] > 0:
        fb_val = ch_out >> mod['fb']
        if fb_val > 127: fb_val = 127
        elif fb_val < -128: fb_val = -128
        mod['fb_val'] = fb_val
    else:
        mod['fb_val'] = 0

    # OP2 (carrier)
    car['pos'] = (car['pos'] + car['step']) & 0xFFFF
    idx = (car['pos'] >> 8) & 0x3F
    idx = (idx + (ch_out & 0xFF)) & 0x3F
    wave_val = car['wave'][idx]
    if wait_tick == (ch & 0x0F):
        fw_env_tick(car)
    ch_out = ((wave_val * (car['level'] + 1) * (car['tl'] + 1)) >> 10)
    if ch_out > 127: ch_out = 127
    elif ch_out < -128: ch_out = -128
    return ch_out

def render_fw_real(inst_idx, freq, dur_keyon, dur_keyoff, volume=0):
    """严格 1:1 下位机仿真. freq 用 440Hz (会被 freq_to_fnum_blk 转成 fnum/blk).
    下位机实际从 VGM 寄存器读 fnum/blk, 这里模拟同样行为."""
    p = fw_decode(DEFAULT_INST[inst_idx])
    mod, car = fw_apply_patch(p)

    # 算 fnum/blk (用 PC 的 freq_to_fnum_blk, 和下位机 VGM 解析一致)
    from ym2413_wav_gen import freq_to_fnum_blk
    fnum, blk = freq_to_fnum_blk(freq)
    # 下位机 blk-1 修正
    if blk > 0: blk -= 1
    mod['step'] = fw_calc_step(fnum, blk, mod['ml'])
    car['step'] = fw_calc_step(fnum, blk, car['ml'])
    # carrier tl 映射: 和下位机 ym2413.c:500-502 一致
    #   下位机: vol = (15 - (reg_val & 0x0F)) << 2  (reg_val=0最大→vol=60, =15最小→vol=0)
    #           car.tl = vol >> 1  (vol=60→tl=30满, vol=0→tl=0静音)
    #   本函数 volume 参数语义和 emu2413 一致: 0=最大音量 (reg_vol=0), 60=最小
    #   故 下位机内部 vol = 60 - volume, car.tl = (60 - volume) >> 1
    fw_vol = 60 - volume
    if fw_vol < 0: fw_vol = 0
    if fw_vol > 60: fw_vol = 60
    car['tl'] = max(0, min(31, fw_vol >> 1))

    n_total = int((dur_keyon + dur_keyoff) * FW_ISR_RATE)
    n_keyon = int(dur_keyon * FW_ISR_RATE)

    fw_key_on(mod, car)

    out = []
    wait_cnt = 0
    for s in range(n_total):
        if s == n_keyon:
            fw_key_off(mod, car)
        wait_cnt = (wait_cnt + 1) & 0x0F
        # 1:1 照搬 ym2413_render 主循环
        total = 0
        # 只渲染这一个通道 (模拟单通道)
        # 跳过判断
        if not (not True and car['env_state'] == 0):
            if not (car['env_state'] == 4 and car['level'] == 0):
                ch_out = fw_render_fm(mod, car, wait_cnt, 0)
                total += ch_out
            elif car['env_state'] == 4 and car['level'] == 0:
                car['env_state'] = 0
        total = total << 1  # total <<= 1
        if total > 32767: total = 32767
        elif total < -32768: total = -32768
        out.append(total)
    return out

# ============================================================
# 验证: 下位机真实仿真 vs emu2413
# ============================================================
def main():
    FREQ = 440.0
    DUR_KO = 0.3
    DUR_KF = 0.3

    print(f"{'='*72}")
    print("下位机真实仿真 (render_fw_real) vs emu2413")
    print(f"{'='*72}")
    print(f"{'Inst':>3} {'Name':<14} {'emu_RMS':>9} {'fw_real':>9} {'diff_dB':>9}")
    print('-' * 60)

    for i in range(1, 16):
        emu = render_emu2413(i, FREQ, DUR_KO, DUR_KF)
        fw  = render_fw_real(i, FREQ, DUR_KO, DUR_KF)
        n = len(emu)
        def rms(s): return (sum(x*x for x in s)/len(s))**0.5 if s else 0
        er, fr = rms(emu), rms(fw)
        d = 20*math.log10(fr/er) if er > 0 and fr > 0 else -99
        print(f"{i:>3} {NAMES[i]:<14} {er:>9.1f} {fr:>9.1f} {d:>+9.3f}")

if __name__ == '__main__':
    main()
