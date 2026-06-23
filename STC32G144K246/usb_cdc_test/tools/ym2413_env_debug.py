#!/usr/bin/env python3
"""
YM2413 15 音色包络精确对比 + WAV 生成.
Phase 1: PC 上对齐全部 15 音色的 carrier 包络行为.
Phase 2: 生成短 WAV 供试听.

禁止改下位机. 全部在 PC 完成.
"""
import math, struct, wave

# ===== 默认音色 =====
DEFAULT_INST = [
    [0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00],
    [0x71,0x61,0x1e,0x17,0xd0,0x78,0x00,0x17],
    [0x13,0x41,0x1a,0x0d,0xd8,0xf7,0x23,0x13],
    [0x13,0x01,0x99,0x00,0xf2,0xc4,0x21,0x23],
    [0x11,0x61,0x0e,0x07,0x8d,0x64,0x70,0x27],
    [0x32,0x21,0x1e,0x06,0xe1,0x76,0x01,0x28],
    [0x31,0x22,0x16,0x05,0xe0,0x71,0x00,0x18],
    [0x21,0x61,0x1d,0x07,0x82,0x81,0x11,0x07],
    [0x33,0x21,0x2d,0x13,0xb0,0x70,0x00,0x07],
    [0x61,0x61,0x1b,0x06,0x64,0x65,0x10,0x17],
    [0x41,0x61,0x0b,0x18,0x85,0xf0,0x81,0x07],
    [0x33,0x01,0x83,0x11,0xea,0xef,0x10,0x04],
    [0x17,0xc1,0x24,0x07,0xf8,0xf8,0x22,0x12],
    [0x61,0x50,0x0c,0x05,0xd2,0xf5,0x40,0x42],
    [0x01,0x01,0x55,0x03,0xe9,0x90,0x03,0x02],
    [0x41,0x41,0x89,0x03,0xf1,0xe4,0xc0,0x13],
]
NAMES = ["User","Violin","Guitar","Piano","Flute","Clarinet","Oboe","Trumpet",
         "Organ","Horn","Synth","Harpsichord","Vibraphone","SynthBass","AcousticBass","ElectricGuitar"]

SR = 22050

def decode(d):
    return {'mod_ml':d[0]&15,'mod_eg':(d[0]>>5)&1,'car_ml':d[1]&15,'car_eg':(d[1]>>5)&1,
            'mod_tl':d[2]&63,'mod_fb':d[3]&7,'mod_ws':(d[3]>>3)&1,'car_ws':(d[3]>>4)&1,
            'mod_ar':(d[4]>>4)&15,'mod_dr':d[4]&15,'car_ar':(d[5]>>4)&15,'car_dr':d[5]&15,
            'mod_sl':(d[6]>>4)&15,'mod_rr':d[6]&15,'car_sl':(d[7]>>4)&15,'car_rr':d[7]&15}

ML_T = [0.5,1,2,3,4,5,6,7,8,9,10,11,12,12,12,12]

# ===== emu2413 精确包络 (eg_out: 0=最响, 127=mute) =====
EG_MUTE = 127
EG_STEP_TABLES = [
    [0,1,0,1,0,1,0,1],[0,1,0,1,1,1,0,1],[0,1,1,1,0,1,1,1],[0,1,1,1,1,1,1,1]
]

def eg_rate_h(p_rate, rks=0):
    return min(15, p_rate + (rks >> 2))

def eg_shift(rate_h, is_attack):
    if is_attack:
        return (13 - rate_h) if (0 < rate_h < 12) else 0
    return (13 - rate_h) if (rate_h < 13) else 0

def attack_step(rate_h, rate_l, counter, shift):
    if rate_h == 0 or rate_h == 15: return 0
    if 12 <= rate_h <= 14:
        idx = (counter & 0xc) >> 1
        return [4,3,2][rate_h-12] - EG_STEP_TABLES[rate_l][idx]
    idx = counter >> shift
    return 4 if EG_STEP_TABLES[rate_l][idx & 7] else 0

def decay_step(rate_h, rate_l, counter, shift):
    if rate_h == 0: return 0
    if rate_h == 15: return 2
    if rate_h == 14:
        idx = (counter & 0xc) >> 1
        return EG_STEP_TABLES[rate_l][idx] + 1
    if rate_h == 13:
        idx = ((counter & 0xc) >> 1) | (counter & 1)
        return EG_STEP_TABLES[rate_l][idx]
    idx = counter >> shift
    return EG_STEP_TABLES[rate_l][idx & 7]

def sim_emu_egout(ar, dr, sl, rr, eg_type, dur):
    """精确模拟 emu2413 carrier 包络. 返回 eg_out 曲线."""
    eg = EG_MUTE; state = 'damp'; counter = 0
    curve = []
    n = int(dur * SR)
    for _ in range(n):
        counter += 1
        if state == 'damp':
            if eg >= 123 and (counter & ((1<<eg_shift(eg_rate_h(ar),True))-1 if eg_shift(eg_rate_h(ar),True)>0 else 0)) == 0:
                # start_envelope
                if eg_rate_h(ar) >= 15:
                    eg = 0; state = 'decay'
                else:
                    state = 'attack'
            else:
                eg = EG_MUTE  # 保持 mute
        if state == 'attack':
            rh = eg_rate_h(ar); sh = eg_shift(rh, True)
            mask = (1<<sh)-1 if sh>0 else 0
            if eg > 0 and rh > 0 and (counter & mask & ~3) == 0:
                s = attack_step(rh, ar & 3, counter, sh)
                if s > 0:
                    eg = max(0, eg - (eg >> s) - 1)
            if eg == 0: state = 'decay'
        elif state == 'decay':
            rh = eg_rate_h(dr); sh = eg_shift(rh, False)
            mask = (1<<sh)-1 if sh>0 else 0
            if rh > 0 and (counter & mask) == 0:
                eg = min(EG_MUTE, eg + decay_step(rh, dr & 3, counter, sh))
            if (eg >> 3) >= sl: state = 'sustain'
        elif state == 'sustain':
            if eg_type:  # non-sustaining: 继续用 RR 衰减
                rh = eg_rate_h(rr); sh = eg_shift(rh, False)
                mask = (1<<sh)-1 if sh>0 else 0
                if rh > 0 and (counter & mask) == 0:
                    eg = min(EG_MUTE, eg + decay_step(rh, rr & 3, counter, sh))
        curve.append(eg)
    return curve

# ===== 极简版包络 V3 (128 级 level, 和 emu2413 一致) =====
# level 0-127, 和 eg_out 完全一致. 不需要映射转换.
# 用 emu2413 实测的步进值.
EG_STEP_TABLES = [[0,1,0,1,0,1,0,1],[0,1,0,1,1,1,0,1],[0,1,1,1,0,1,1,1],[0,1,1,1,1,1,1,1]]

def sim_simple_egout(ar, dr, sl, rr, eg_type, dur, ch=0):
    """极简版 V3: 128 级 level, 直接复用 emu2413 的 rate/shift/step 逻辑.
    和 sim_emu_egout 几乎一样, 但简化了 DAMP 初始化."""
    eg = 127; state = 'attack'; counter = 0
    curve = []
    n = int(dur * SR)

    # key on: 如果 AR+RKS >= 15, 跳过 attack
    if min(15, ar) >= 15:
        eg = 0; state = 'decay'

    for _ in range(n):
        counter += 1
        rh = min(15, ar) if state == 'attack' else (min(15, dr) if state == 'decay' else (min(15, rr) if state == 'sustain' else min(15, rr)))
        sh = (13-rh) if (0 < rh < 12 if state=='attack' else rh < 13) else 0
        if state == 'attack' and not (0 < rh < 12): sh = 0
        mask = (1 << sh) - 1 if sh > 0 else 0

        if state == 'attack':
            if eg > 0 and rh > 0 and (counter & mask & ~3) == 0:
                if 12 <= rh <= 14:
                    idx = (counter & 0xc) >> 1
                    s = [4,3,2][rh-12] - EG_STEP_TABLES[ar&3][idx]
                elif rh == 15:
                    s = 0
                else:
                    idx = counter >> sh
                    s = 4 if EG_STEP_TABLES[ar&3][idx&7] else 0
                if s > 0:
                    eg = max(0, eg - (eg >> s) - 1)
            if eg == 0: state = 'decay'
        elif state == 'decay':
            rh_d = min(15, dr); sh_d = (13-rh_d) if rh_d < 13 else 0
            mask_d = (1<<sh_d)-1 if sh_d>0 else 0
            if rh_d > 0 and (counter & mask_d) == 0:
                if rh_d == 15: s = 2
                elif rh_d == 14: s = EG_STEP_TABLES[dr&3][((counter&0xc)>>1)] + 1
                elif rh_d == 13: s = EG_STEP_TABLES[dr&3][(((counter&0xc)>>1)|(counter&1))]
                else: s = EG_STEP_TABLES[dr&3][((counter>>sh_d)&7)]
                eg = min(127, eg + s)
            if (eg >> 3) >= sl: state = 'sustain'
        elif state == 'sustain':
            if eg_type:
                rh_r = min(15, rr); sh_r = (13-rh_r) if rh_r < 13 else 0
                mask_r = (1<<sh_r)-1 if sh_r>0 else 0
                if rh_r > 0 and (counter & mask_r) == 0:
                    if rh_r == 15: s = 2
                    elif rh_r == 14: s = EG_STEP_TABLES[rr&3][((counter&0xc)>>1)] + 1
                    elif rh_r == 13: s = EG_STEP_TABLES[rr&3][(((counter&0xc)>>1)|(counter&1))]
                    else: s = EG_STEP_TABLES[rr&3][((counter>>sh_r)&7)]
                    eg = min(127, eg + s)

        curve.append(eg)
    return curve

def rms_db(curve, start, length):
    """eg_out 曲线转 dB RMS (越低=越响)"""
    chunk = curve[start:start+length]
    if not chunk: return -96
    avg = sum(chunk) / len(chunk)
    return -avg * 0.75  # 每 eg_out step ≈ 0.75dB

def main():
    dur = 0.3
    pts = 10
    step = int(dur * SR / pts)

    print("=" * 90)
    print("YM2413 15 音色 carrier 包络对比 (eg_out dB, 越接近 0=越响)")
    print("目标: 全部 15 音色 diff < 30dB")
    print("=" * 90)

    all_pass = True
    for i in range(1, 16):
        p = decode(DEFAULT_INST[i])
        emu = sim_emu_egout(p['car_ar'], p['car_dr'], p['car_sl'], p['car_rr'], p['car_eg'], dur)
        sim = sim_simple_egout(p['car_ar'], p['car_dr'], p['car_sl'], p['car_rr'], p['car_eg'], dur)

        emu_db = [int(rms_db(emu, j*step, step)) for j in range(pts)]
        sim_db = [int(rms_db(sim, j*step, step)) for j in range(pts)]
        diff = sum(abs(a-b) for a, b in zip(emu_db, sim_db))
        ok = '✓' if diff < 30 else '✗'
        if diff >= 30: all_pass = False

        print(f"\n{i:2d} {NAMES[i]:<14} AR={p['car_ar']} DR={p['car_dr']} SL={p['car_sl']} RR={p['car_rr']} EG={p['car_eg']}  diff={diff} {ok}")
        print(f"   {'time':>6}  " + "  ".join(f"{j*30:5d}ms" for j in range(pts)))
        print(f"   {'emu':>6}  " + "  ".join(f"{d:5d}" for d in emu_db))
        print(f"   {'simp':>6}  " + "  ".join(f"{d:5d}" for d in sim_db))

    print(f"\n{'='*60}")
    if all_pass:
        print("✓ 全部 15 音色过关! 可以生成 WAV 试听.")
    else:
        print("✗ 有音色未过关, 需继续调试 Python 模拟.")

    return all_pass

if __name__ == '__main__':
    main()
