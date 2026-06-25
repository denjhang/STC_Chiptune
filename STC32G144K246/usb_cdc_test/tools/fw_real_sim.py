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
# AR/DR/RR 三张表 (反推自 emu2413 速率, 2026-06-25 校准)
FW_AR_TAB = [0, 116, 58, 29, 14, 7, 4, 2, 1, 1, 1, 1, 1, 1, 1, 1]
# SUL 表: sl(0~15) -> sustain level. 注意: non-sus 乐器的 sul 是 sus_hold 起点
# sl=0 保持峰值(sul=31), sl 越大衰减越深. 比 emu 温和 (避免 non-sus 双重衰减)
FW_SUL_TAB = [31, 27, 23, 19, 15, 12, 9, 7, 5, 4, 3, 2, 1, 1, 0, 0]
FW_DR_TAB = [0, 255, 255, 255, 75, 38, 19, 9, 5, 2, 1, 1, 1, 1, 1, 1]
FW_RR_TAB = [0, 255, 255, 255, 76, 38, 19, 9, 5, 2, 1, 1, 1, 1, 1, 1]
# SUSTAIN 指数衰减基础表 (tau=221ms): sus_hold[level] = 该 level 停留 tick 数 (未缩放)
# 实际 sustain 用 sus_hold[level] × sus_scale_x16[rr] >> 4 (按 RR 缩放)
FW_SUS_HOLD = [0, 305, 305, 178, 126, 98, 80, 68, 59, 52, 46, 42, 38, 35, 33,
               30, 28, 27, 25, 24, 23, 21, 20, 20, 19, 18, 17, 17, 16, 15, 15, 14]
# sus_scale_x16[RR]: SUSTAIN 衰减缩放 (×16 定点), 按 RR 档位 (emu 实测反推)
# RR 小=慢衰减(长 sustain, vibraphone RR=2), RR 大=快衰减. RR=4 ≈ 0.44 (harpsichord 基准)
FW_SUS_SCALE_X16 = [0, 122, 27, 14, 7, 3, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
# RELEASE 指数衰减: rel_hold[level] (固定, 比 sustain 快 ~10×). 复用 sus_cnt.
FW_REL_HOLD = [max(1, h//10) for h in FW_SUS_HOLD]
# ml_table: 下位机自己的 (和 emu 不同!)
FW_ML_TABLE = [1, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 24, 24, 24]
# PM (vibrato) 表: pm_table[fnum>>6 & 7][pm_phase>>10 & 7] = fnum 偏移 (对齐 emu2413)
FW_PM_TABLE = [
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 1, 0, 0, 0,-1, 0],
    [0, 1, 2, 1, 0,-1,-2,-1],
    [0, 1, 3, 1, 0,-1,-3,-1],
    [0, 2, 4, 2, 0,-2,-4,-2],
    [0, 2, 5, 2, 0,-2,-5,-2],
    [0, 3, 6, 3, 0,-3,-6,-3],
    [0, 3, 7, 3, 0,-3,-7,-3],
]
# AM (tremolo) 表: am_table[am_phase>>6 % 210] = 0~13 振幅衰减 (对齐 emu2413)
FW_AM_TABLE = [0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1, 2,2,2,2,2,2,2,2, 3,3,3,3,3,3,3,3,
    4,4,4,4,4,4,4,4, 5,5,5,5,5,5,5,5, 6,6,6,6,6,6,6,6, 7,7,7,7,7,7,7,7,
    8,8,8,8,8,8,8,8, 9,9,9,9,9,9,9,9, 10,10,10,10,10,10,10,10, 11,11,11,11,11,11,11,11,
    12,12,12,12,12,12,12,12, 13,13,13, 12,12,12,12,12,12,12,12,
    11,11,11,11,11,11,11,11, 10,10,10,10,10,10,10,10, 9,9,9,9,9,9,9,9, 8,8,8,8,8,8,8,8,
    7,7,7,7,7,7,7,7, 6,6,6,6,6,6,6,6, 5,5,5,5,5,5,5,5, 4,4,4,4,4,4,4,4,
    3,3,3,3,3,3,3,3, 2,2,2,2,2,2,2,2, 1,1,1,1,1,1,1,1, 0,0,0,0,0,0,0]
# LFO 索引 (round-robin 每 16 采样推进一次, 不是每采样)
# am/pm 共用 am_table (210 项三角波), 每次推进 +1
# 频率: 22050/16/210 = 6.56Hz (vibrato/tremolo 标准 5~7Hz)
_fw_lfo_idx = 0
# step 常数 (8.8 定点, 1:1 照搬 ym2413.c:237, blk-1 修正)
# pos/step 都是 u16, idx = pos>>8 & 0x3F, 一个周期 = 64×256 = 16384
FW_STEP_CONST = 3579545.0 * 64.0 * 256.0 / (72.0 * 262144.0 * 22050.0)
# 下位机 ISR 采样率 (不是 emu 的 49716!)
FW_ISR_RATE = 22050

def fw_decode(dump):
    """1:1 照搬 ym_decode_patch (AM/PM 2026-06-25 新增解码)"""
    return {
        'mod_ml': dump[0] & 0x0F, 'mod_eg': (dump[0] >> 5) & 1,
        'mod_am': (dump[0] >> 7) & 1, 'mod_pm': (dump[0] >> 6) & 1,
        'car_ml': dump[1] & 0x0F, 'car_eg': (dump[1] >> 5) & 1,
        'car_am': (dump[1] >> 7) & 1, 'car_pm': (dump[1] >> 6) & 1,
        'mod_tl': dump[2] & 0x3F, 'mod_fb': dump[3] & 0x07,
        'mod_ws': (dump[3] >> 3) & 1, 'car_ws': (dump[3] >> 4) & 1,
        'mod_ar': (dump[4] >> 4) & 0x0F, 'mod_dr': dump[4] & 0x0F,
        'car_ar': (dump[5] >> 4) & 0x0F, 'car_dr': dump[5] & 0x0F,
        'mod_sl': (dump[6] >> 4) & 0x0F, 'mod_rr': dump[6] & 0x0F,
        'car_sl': (dump[7] >> 4) & 0x0F, 'car_rr': dump[7] & 0x0F,
    }

def fw_apply_patch(p):
    """1:1 照搬 ym_apply_patch. 返回 (mod_op, car_op) 字典"""
    def make_op(ml_val, tl_raw, fb, eg, ws, ar, dr, sl, rr, am=0, pm=0):
        return {
            'ml': FW_ML_TABLE[ml_val],
            'tl': max(0, min(31, 31 - (tl_raw >> 1))),  # mod_tl: 31 - tl/2
            'fb': fb, 'eg_type': eg,
            'am': am, 'pm': pm,  # LFO 标志 (AM=tremolo, PM=vibrato)
            'wave': FW_HALFSIN if ws else FW_SIN,
            'atk': FW_AR_TAB[ar], 'decy': FW_DR_TAB[dr],
            'sul': FW_SUL_TAB[sl] if sl < 16 else 0,
            'rel': FW_RR_TAB[rr],
            'sus_scale_x16': FW_SUS_SCALE_X16[rr],  # SUSTAIN 按 RR 缩放 (×16 定点)
            # 运行时状态
            'pos': 0, 'step': 0, 'fb_val': 0,
            'env_state': 0, 'env_cnt': 0, 'env_step': 0, 'level': 0,
            'sus_flag': 0, 'sus_cnt': 0,  # sus_cnt: SUSTAIN/RELEASE 指数查表计数器
            'fnum': 0,  # PM 查表用 (set_note 时存)
        }
    mod = make_op(p['mod_ml'], p['mod_tl'], p['mod_fb'], p['mod_eg'], p['mod_ws'],
                  p['mod_ar'], p['mod_dr'], p['mod_sl'], p['mod_rr'], p['mod_am'], p['mod_pm'])
    car = make_op(p['car_ml'], 0, 0, p['car_eg'], p['car_ws'],
                  p['car_ar'], p['car_dr'], p['car_sl'], p['car_rr'], p['car_am'], p['car_pm'])
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
    """keyoff -> RELEASE. release 用 FW_REL_HOLD 指数查表 (env_step=1 让计数器接管)"""
    mod['env_state'] = 4; car['env_state'] = 4
    mod['env_step'] = 1; mod['sus_cnt'] = 0
    car['env_step'] = 1; car['sus_cnt'] = 0

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
    if st == 1:  # attack (指数递增: level 增量 = (31-level)>>s + 1, 拟合 emu eg_out 指数)
        if op['level'] < 31:
            # s=2 固定 (attack 形态), atk 控制速率 (tick 间隔). 低 level 大步进, 高 level 小步进
            op['level'] += ((31 - op['level']) >> 2) + 1
            if op['level'] > 31: op['level'] = 31
        if op['level'] >= 31:
            op['env_state'] = 2; op['env_step'] = op['decy']
    elif st == 2:  # decay
        if op['level'] > op['sul']:
            op['level'] -= 1
        else:
            op['env_state'] = 3
            op['env_step'] = 0 if op['eg_type'] else 1  # EG=1保持; EG=0 进 sustain, env_step=1 让 sus_hold 接管速率
    elif st == 3:  # sustain (EG=0 non-sus: 指数查表按 RR 缩放衰减; EG=1 step=0 不进)
        if op['level'] > 0:
            op['sus_cnt'] += 1
            threshold = (FW_SUS_HOLD[op['level']] * op['sus_scale_x16']) >> 4
            if threshold < 1: threshold = 1
            if op['sus_cnt'] >= threshold:
                op['sus_cnt'] = 0
                op['level'] -= 1
                if op['level'] == 0:
                    op['env_state'] = 0
    elif st == 4:  # release (指数查表衰减, 拟合 emu release 形态)
        if op['level'] > 0:
            op['sus_cnt'] += 1
            if op['sus_cnt'] >= FW_REL_HOLD[op['level']]:
                op['sus_cnt'] = 0
                op['level'] -= 1
                if op['level'] == 0:
                    op['env_state'] = 0

def fw_lfo_tick():
    """LFO 推进 (round-robin 每 16 采样调一次, 不是每采样). 索引 +1."""
    global _fw_lfo_idx
    _fw_lfo_idx = (_fw_lfo_idx + 1) % len(FW_AM_TABLE)

def fw_pm_offset(op):
    """PM (vibrato): 操作 step (频率), 三角波让频率平滑 ±1.5% (1/4 半音).
    round-robin 更新 (每 16 采样变化一次, 不需每采样)."""
    if not op['pm']:
        return 0
    tri = FW_AM_TABLE[_fw_lfo_idx]  # 0~13 三角波
    delta_base = op['step'] >> 6    # step 的 1.5% (1/4 半音)
    return (delta_base * (tri - 6)) >> 3   # (tri-6) -6~+7, 映射 ±1.5%

def fw_am_factor(op):
    """AM (tremolo): 返回 0~13 (0=不衰减). round-robin 更新."""
    if not op['am']:
        return 0
    return FW_AM_TABLE[_fw_lfo_idx]

def fw_render_fm(mod, car, wait_tick, ch):
    """1:1 照搬 ym_render_fm (8.8 定点). 返回 s16 输出"""
    if mod['step'] == 0:
        return 0
    # OP1 (modulator) — pos/step u16, idx = pos>>8 & 0x3F
    mod['pos'] = (mod['pos'] + mod['step'] + fw_pm_offset(mod)) & 0xFFFF
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
        fb_val = ch_out >> (mod['fb'] + 4)   # FB+4 移位压低反馈 (对齐 emu 反馈强度, 2026-06-25)
        if fb_val > 127: fb_val = 127
        elif fb_val < -128: fb_val = -128
        mod['fb_val'] = fb_val
    else:
        mod['fb_val'] = 0

    # OP2 (carrier)
    car['pos'] = (car['pos'] + car['step'] + fw_pm_offset(car)) & 0xFFFF
    idx = (car['pos'] >> 8) & 0x3F
    idx = (idx + (ch_out & 0xFF)) & 0x3F
    wave_val = car['wave'][idx]
    if wait_tick == (ch & 0x0F):
        fw_env_tick(car)
    # AM (tremolo): am_factor 0~13 加到衰减 (level 对数域减). 简化: 输出 × am_scale
    am_f = fw_am_factor(car)
    eff_level = car['level'] - (am_f >> 1)  # am 0~13, level 减 0~6
    if eff_level < 0: eff_level = 0
    ch_out = ((wave_val * (eff_level + 1) * (car['tl'] + 1)) >> 10)
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
    mod['fnum'] = fnum; car['fnum'] = fnum  # PM 查表用
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
        if wait_cnt == 0:
            fw_lfo_tick()   # LFO round-robin 推进 (每 16 采样)
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
