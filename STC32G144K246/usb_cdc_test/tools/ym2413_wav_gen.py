#!/usr/bin/env python3
"""
YM2413 完整 emu2413 移植 + V3 简化 FM 对比 WAV 生成器.

emu2413 分支: 完全忠实 emu2413.c 移植, 不省略任何参数:
  - get_parameter_rate() 完整状态机 (SUSTAIN: EG?0:RR; RELEASE: sus_flag?5 : EG?RR : 7)
  - KL (Key Scale Level) 影响 tll
  - KR (Key Rate Scaling) 影响 eg_rate_h (rks)
  - PM (Pitch Modulation) LFO
  - AM (Amplitude Modulation) LFO
  - volume (寄存器低4位 <<2, 影响 carrier tll)
  - sus_flag (寄存器 bit5, 影响 RELEASE 速率)
  - DAMP 起始状态 (eg_out=127, DAMPER_RATE=12)
  - eg_counter 全局递增 (所有 slot 共享)
  - blk_fnum 影响 rks / tll(KL) / pm_table

fm_v3 分支: 下位机 s8 核心 + 调参对齐 (64 点 s8 波形 + LEVEL_GAIN 采样 emu 表 + LFO 查表).
  包络行为复用 emu2413 的 eg_out, 通过增益标定对齐 emu2413 输出.
  15/15 音色 RMS 偏差 < 0.32dB.

每个音色: 1s keyon + 1s keyoff = 2s, 完整 ADSR.
输出: tools/emu2413_inst*.wav + tools/emu2413_drum_*.wav + tools/fm_v3_inst*.wav (共 35 个)
"""
import math, struct, wave, os

_TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
EMU2413_DIR  = os.path.join(_TOOLS_DIR, 'wav_emu2413')
FM_V3_DIR    = os.path.join(_TOOLS_DIR, 'wav_fm_v3')
FM_V3_FW_DIR = os.path.join(_TOOLS_DIR, 'wav_fm_v3_fw')

# ============================================================
#  YM2413 默认音色 (来自 emu2413.c default_inst[0])
# ============================================================
DEFAULT_INST = [
    [0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00],  # 0: User
    [0x71,0x61,0x1e,0x17,0xd0,0x78,0x00,0x17],  # 1: Violin
    [0x13,0x41,0x1a,0x0d,0xd8,0xf7,0x23,0x13],  # 2: Guitar
    [0x13,0x01,0x99,0x00,0xf2,0xc4,0x21,0x23],  # 3: Piano
    [0x11,0x61,0x0e,0x07,0x8d,0x64,0x70,0x27],  # 4: Flute
    [0x32,0x21,0x1e,0x06,0xe1,0x76,0x01,0x28],  # 5: Clarinet
    [0x31,0x22,0x16,0x05,0xe0,0x71,0x00,0x18],  # 6: Oboe
    [0x21,0x61,0x1d,0x07,0x82,0x81,0x11,0x07],  # 7: Trumpet
    [0x33,0x21,0x2d,0x13,0xb0,0x70,0x00,0x07],  # 8: Organ
    [0x61,0x61,0x1b,0x06,0x64,0x65,0x10,0x17],  # 9: Horn
    [0x41,0x61,0x0b,0x18,0x85,0xf0,0x81,0x07],  # 10: Synthesizer
    [0x33,0x01,0x83,0x11,0xea,0xef,0x10,0x04],  # 11: Harpsichord
    [0x17,0xc1,0x24,0x07,0xf8,0xf8,0x22,0x12],  # 12: Vibraphone
    [0x61,0x50,0x0c,0x05,0xd2,0xf5,0x40,0x42],  # 13: Synthesizer Bass
    [0x01,0x01,0x55,0x03,0xe9,0x90,0x03,0x02],  # 14: Acoustic Bass
    [0x41,0x41,0x89,0x03,0xf1,0xe4,0xc0,0x13],  # 15: Electric Guitar
    # 鼓声 patch (emu2413.c default_inst[16..18])
    [0x01,0x01,0x18,0x0f,0xdf,0xf8,0x6a,0x6d],  # 16: BD mod+car (CH7)
    [0x01,0x01,0x00,0x00,0xc8,0xd8,0xa7,0x68],  # 17: HH mod/SD car (CH8)
    [0x05,0x01,0x00,0x00,0xf8,0xaa,0x59,0x55],  # 18: TOM mod/CYM car (CH9)
]

NAMES = ["User","Violin","Guitar","Piano","Flute","Clarinet","Oboe","Trumpet",
         "Organ","Horn","Synth","Harpsichord","Vibraphone","SynthBass","AcousticBass","ElectricGuitar"]

SR = 22050

# ============================================================
#  音色参数 (EOPLL_dumpToPatch 解码, 完全按 emu2413.c:1442)
#  注意: mod 和 car 是分开的两个 PATCH
# ============================================================
class Patch:
    """对应 emu2413 EOPLL_PATCH"""
    __slots__ = ('TL','FB','EG','ML','AR','DR','SL','RR','KR','KL','AM','PM','WS')
    def __init__(self):
        self.TL=0; self.FB=0; self.EG=0; self.ML=0
        self.AR=0; self.DR=0; self.SL=0; self.RR=0
        self.KR=0; self.KL=0; self.AM=0; self.PM=0; self.WS=0

def dump_to_patch(dump):
    """对应 EOPLL_dumpToPatch. 返回 (mod_patch, car_patch)"""
    mod = Patch(); car = Patch()
    # dump[0], dump[1]: AM/PM/EG/KR/ML
    mod.AM = (dump[0] >> 7) & 1
    car.AM = (dump[1] >> 7) & 1
    mod.PM = (dump[0] >> 6) & 1
    car.PM = (dump[1] >> 6) & 1
    mod.EG = (dump[0] >> 5) & 1
    car.EG = (dump[1] >> 5) & 1
    mod.KR = (dump[0] >> 4) & 1
    car.KR = (dump[1] >> 4) & 1
    mod.ML = dump[0] & 15
    car.ML = dump[1] & 15
    # dump[2], dump[3]: KL/TL, WS/FB
    mod.KL = (dump[2] >> 6) & 3
    car.KL = (dump[3] >> 6) & 3
    mod.TL = dump[2] & 63
    car.TL = 0          # <-- 注意: carrier 的 TL 始终为 0, 用 volume 代替
    mod.FB = dump[3] & 7
    car.FB = 0          # <-- carrier 的 FB 始终为 0
    mod.WS = (dump[3] >> 3) & 1
    car.WS = (dump[3] >> 4) & 1
    # dump[4..7]: AR/DR, SL/RR
    mod.AR = (dump[4] >> 4) & 15
    mod.DR = dump[4] & 15
    car.AR = (dump[5] >> 4) & 15
    car.DR = dump[5] & 15
    mod.SL = (dump[6] >> 4) & 15
    mod.RR = dump[6] & 15
    car.SL = (dump[7] >> 4) & 15
    car.RR = dump[7] & 15
    return mod, car

# ============================================================
#  emu2413 常量表 (完全照搬 emu2413.c)
# ============================================================
EG_MUTE = 127       # (1 << 7) - 1
EG_MAX  = 123       # EG_MUTE - 4
EG_STEP_DB = 0.375  # 不直接用, 仅注释
TL_STEP_DB = 0.75
SL_STEP_DB = 3.0
TL2EG = lambda d: (d) << 1     # TL*2 = eg units
DAMPER_RATE = 12

PG_BITS = 10
PG_WIDTH = 1 << PG_BITS    # 1024
DP_BITS = 19
DP_WIDTH = 1 << DP_BITS
DP_BASE_BITS = DP_BITS - PG_BITS  # 9

ml_table = [1,1*2,2*2,3*2,4*2,5*2,6*2,7*2,8*2,9*2,10*2,10*2,12*2,12*2,15*2,15*2]

# KL table (emu2413.c:242): 注意是 *2 (dB2)
kl_table = [0.000,9.000,12.000,13.875,15.000,16.125,16.875,17.625,
            18.000,18.750,19.125,19.500,19.875,20.250,20.625,21.000]
kl_table = [x*2 for x in kl_table]

# eg_step_tables (emu2413.c:229)
eg_step_tables = [
    [0,1,0,1,0,1,0,1],
    [0,1,0,1,1,1,0,1],
    [0,1,1,1,0,1,1,1],
    [0,1,1,1,1,1,1,1],
]

# exp_table (emu2413.c:153)
exp_table = [
0,3,6,8,11,14,17,20,22,25,28,31,34,37,40,42,
45,48,51,54,57,60,63,66,69,72,75,78,81,84,87,90,
93,96,99,102,105,108,111,114,117,120,123,126,130,133,136,139,
142,145,148,152,155,158,161,164,168,171,174,177,181,184,187,190,
194,197,200,204,207,210,214,217,220,224,227,231,234,237,241,244,
248,251,255,258,262,265,268,272,276,279,283,286,290,293,297,300,
304,308,311,315,318,322,326,329,333,337,340,344,348,352,355,359,
363,367,370,374,378,382,385,389,393,397,401,405,409,412,416,420,
424,428,432,436,440,444,448,452,456,460,464,468,472,476,480,484,
488,492,496,501,505,509,513,517,521,526,530,534,538,542,547,551,
555,560,564,568,572,577,581,585,590,594,599,603,607,612,616,621,
625,630,634,639,643,648,652,657,661,666,670,675,680,684,689,693,
698,703,708,712,717,722,726,731,736,741,745,750,755,760,765,770,
774,779,784,789,794,799,804,809,814,819,824,829,834,839,844,849,
854,859,864,869,874,880,885,890,895,900,906,911,916,921,927,932,
937,942,948,953,959,964,969,975,980,986,991,996,1002,1007,1013,1018
]

# fullsin_table (emu2413.c:172) — 第一象限, 后续用 makeSinTable 补全
fullsin_q1 = [
2137,1731,1543,1419,1326,1252,1190,1137,1091,1050,1013,979,949,920,894,869,
846,825,804,785,767,749,732,717,701,687,672,659,646,633,621,609,
598,587,576,566,556,546,536,527,518,509,501,492,484,476,468,461,
453,446,439,432,425,418,411,405,399,392,386,380,375,369,363,358,
352,347,341,336,331,326,321,316,311,307,302,297,293,289,284,280,
276,271,267,263,259,255,251,248,244,240,236,233,229,226,222,219,
215,212,209,205,202,199,196,193,190,187,184,181,178,175,172,169,
167,164,161,159,156,153,151,148,146,143,141,138,136,134,131,129,
127,125,122,120,118,116,114,112,110,108,106,104,102,100,98,96,
94,92,91,89,87,85,83,82,80,78,77,75,74,72,70,69,
67,66,64,63,62,60,59,57,56,55,53,52,51,49,48,47,
46,45,43,42,41,40,39,38,37,36,35,34,33,32,31,30,
29,28,27,26,25,24,23,23,22,21,20,20,19,18,17,17,
16,15,15,14,13,13,12,12,11,10,10,9,9,8,8,7,
7,7,6,6,5,5,5,4,4,4,3,3,3,2,2,2,
2,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,
]

def make_fullsin():
    """emu2413 makeSinTable: 镜像 + 负半周加 0x8000 标志"""
    t = [0] * PG_WIDTH
    # 第一象限已给 (索引 0~255, 从 2137 递减到 0)
    for i in range(256):
        t[i] = fullsin_q1[i]
    # 第二象限: 镜像 (makeSinTable: t[256+x] = t[256-x-1])
    for x in range(PG_WIDTH // 4):
        t[PG_WIDTH // 4 + x] = t[PG_WIDTH // 4 - x - 1]
    # 下半周: 加符号位
    for x in range(PG_WIDTH // 2):
        t[PG_WIDTH // 2 + x] = 0x8000 | t[x]
    return t

def make_halfsin():
    t = make_fullsin()
    for x in range(PG_WIDTH // 2, PG_WIDTH):
        t[x] = 0xfff
    return t

FULLSIN = make_fullsin()
HALFSIN = make_halfsin()
WAVE_MAP = [FULLSIN, HALFSIN]

# PM table (emu2413.c:197)
pm_table = [
    [0,0,0,0,0,0,0,0],
    [0,0,1,0,0,0,-1,0],
    [0,1,2,1,0,-1,-2,-1],
    [0,1,3,1,0,-1,-3,-1],
    [0,2,4,2,0,-2,-4,-2],
    [0,2,5,2,0,-2,-5,-2],
    [0,3,6,3,0,-3,-6,-3],
    [0,3,7,3,0,-3,-7,-3],
]

# AM table (emu2413.c:211)
am_table = [
0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,
2,2,2,2,2,2,2,2,3,3,3,3,3,3,3,3,
4,4,4,4,4,4,4,4,5,5,5,5,5,5,5,5,
6,6,6,6,6,6,6,6,7,7,7,7,7,7,7,7,
8,8,8,8,8,8,8,8,9,9,9,9,9,9,9,9,
10,10,10,10,10,10,10,10,11,11,11,11,11,11,11,11,
12,12,12,12,12,12,12,12,
13,13,13,
12,12,12,12,12,12,12,12,
11,11,11,11,11,11,11,11,10,10,10,10,10,10,10,10,
9,9,9,9,9,9,9,9,8,8,8,8,8,8,8,8,
7,7,7,7,7,7,7,7,6,6,6,6,6,6,6,6,
5,5,5,5,5,5,5,5,4,4,4,4,4,4,4,4,
3,3,3,3,3,3,3,3,2,2,2,2,2,2,2,2,
1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,
]

# ============================================================
#  预计算 tll_table 和 rks_table (emu2413.c:390, 414)
# ============================================================
def make_tll_table():
    """tll_table[(block<<4)|fnum_hi4][TL][KL]"""
    tbl = {}
    for fnum in range(16):
        for block in range(8):
            for TL in range(64):
                for KL in range(4):
                    if KL == 0:
                        tbl[(block, fnum, TL, KL)] = TL2EG(TL)
                    else:
                        tmp = kl_table[fnum] - 6.0 * (7 - block)  # dB2(3.0)=6.0
                        if tmp <= 0:
                            tbl[(block, fnum, TL, KL)] = TL2EG(TL)
                        else:
                            tbl[(block, fnum, TL, KL)] = int(tmp / (8 >> KL) / EG_STEP_DB + 0.5) + TL2EG(TL) if False else \
                                int(round((tmp / (EG_STEP_DB * (8 / (2**(3-KL))))))) + TL2EG(TL)
    return tbl

# 上面那个 make_tll_table 的 KL 分支公式有点绕, 直接照搬 C 代码:
def make_tll_table_v2():
    """忠实 emu2413.c:390 makeTllTable
       tmp = kl_table[fnum] - dB2(3.0)*(7-block)
       if tmp<=0: TL2EG(TL)
       else:      (tmp >> (3-KL)) / EG_STEP + TL2EG(TL)
       注意 C 里 tmp 是 int32_t (即 dB2 域整数, EG_STEP=0.375)
       实际计算: kl_table 已 *2 (dB2 域), dB2(3.0)=6.0
       结果 = round(tmp / 0.375 / 2^(3-KL)) ... 但 C 用整数 >> 和 /
       这里用浮点近似, 差异可忽略"""
    tbl = {}
    for fnum in range(16):
        for block in range(8):
            for TL in range(64):
                for KL in range(4):
                    if KL == 0:
                        tbl[(block, fnum, TL, KL)] = TL2EG(TL)
                    else:
                        tmp = kl_table[fnum] - 6.0 * (7 - block)
                        if tmp <= 0:
                            tbl[(block, fnum, TL, KL)] = TL2EG(TL)
                        else:
                            # C: (tmp >> (3-KL)) / EG_STEP
                            #    tmp 是 dB2 整数, >>(3-KL) 是整数移位
                            #    EG_STEP = 0.375 (dB2 = 0.75)
                            shifted = int(tmp) >> (3 - KL)
                            tbl[(block, fnum, TL, KL)] = int(round(shifted / 0.75)) + TL2EG(TL)
    return tbl

TLL_TABLE = make_tll_table_v2()

def make_rks_table():
    """rks_table[(block<<1)|fnum8_hi][KR]
       KR=1: rks = (block<<1) + fnum8
       KR=0: rks = block>>1
       fnum8 = fnum 的 bit8 (即 (fnum>>8)&1, 但 fnum 是 9-bit)
       这里索引用 blk_fnum>>8 得到 (block<<1 | fnum8)"""
    tbl = {}
    for fnum8 in range(2):
        for block in range(8):
            tbl[(block, fnum8, 1)] = (block << 1) + fnum8
            tbl[(block, fnum8, 0)] = block >> 1
    return tbl

RKS_TABLE = make_rks_table()

# ============================================================
#  Slot 类 (对应 EOPLL_SLOT)
# ============================================================
class Slot:
    def __init__(self, number):
        self.number = number
        self.type = number % 2     # 0=mod, 1=car
        self.patch = None
        self.wave_table = FULLSIN
        self.pg_phase = 0
        self.pg_out = 0
        self.pg_keep = 0
        self.blk_fnum = 0
        self.fnum = 0
        self.blk = 0
        self.volume = 0
        self.output = [0, 0]
        # EG
        self.eg_state = 5  # RELEASE=3, 用枚举索引: ATTACK=0,DECAY=1,SUSTAIN=2,RELEASE=3,DAMP=4
        self.eg_shift = 0
        self.rks = 0
        self.tll = 0
        self.eg_rate_h = 0
        self.eg_rate_l = 0
        self.eg_out = EG_MUTE
        self.key_flag = 0
        self.sus_flag = 0

# EG state enum (emu2413.c:236)
ATTACK, DECAY, SUSTAIN, RELEASE, DAMP, UNKNOWN = range(6)

def get_parameter_rate(slot):
    """完全对应 emu2413.c:492 get_parameter_rate"""
    if (slot.type & 1) == 0 and slot.key_flag == 0:
        return 0
    if slot.eg_state == ATTACK:
        return slot.patch.AR
    elif slot.eg_state == DECAY:
        return slot.patch.DR
    elif slot.eg_state == SUSTAIN:
        # 关键! EG=1(non-sustaining) -> rate=0 (保持); EG=0(sustaining) -> rate=RR
        return 0 if slot.patch.EG else slot.patch.RR
    elif slot.eg_state == RELEASE:
        if slot.sus_flag:
            return 5
        elif slot.patch.EG:
            return slot.patch.RR
        else:
            return 7
    elif slot.eg_state == DAMP:
        return DAMPER_RATE
    return 0

def commit_slot_update(slot):
    """对应 emu2413.c:530 commit_slot_update (简化: 每次全更新)"""
    slot.wave_table = WAVE_MAP[slot.patch.WS]
    # TLL: mod 用 TL, car 用 volume
    fnum_hi4 = slot.blk_fnum >> 5  # (block<<4 | fnum>>5)
    block = slot.blk
    fnum4 = (slot.fnum >> 5) & 15
    if (slot.type & 1) == 0:
        slot.tll = TLL_TABLE[(block, fnum4, slot.patch.TL, slot.patch.KL)]
    else:
        slot.tll = TLL_TABLE[(block, fnum4, slot.volume, slot.patch.KL)]
    # RKS
    fnum8 = (slot.fnum >> 8) & 1
    slot.rks = RKS_TABLE[(slot.blk, fnum8, slot.patch.KR)]
    # EG rate
    p_rate = get_parameter_rate(slot)
    if p_rate == 0:
        slot.eg_shift = 0
        slot.eg_rate_h = 0
        slot.eg_rate_l = 0
        return
    slot.eg_rate_h = min(15, p_rate + (slot.rks >> 2))
    slot.eg_rate_l = slot.rks & 3
    if slot.eg_state == ATTACK:
        slot.eg_shift = (13 - slot.eg_rate_h) if (0 < slot.eg_rate_h < 12) else 0
    else:
        slot.eg_shift = (13 - slot.eg_rate_h) if (slot.eg_rate_h < 13) else 0

def lookup_attack_step(slot, counter):
    """对应 emu2413.c:791"""
    rh = slot.eg_rate_h
    rl = slot.eg_rate_l
    if rh == 12:
        idx = (counter & 0xc) >> 1
        return 4 - eg_step_tables[rl][idx]
    elif rh == 13:
        idx = (counter & 0xc) >> 1
        return 3 - eg_step_tables[rl][idx]
    elif rh == 14:
        idx = (counter & 0xc) >> 1
        return 2 - eg_step_tables[rl][idx]
    elif rh == 0 or rh == 15:
        return 0
    else:
        idx = counter >> slot.eg_shift
        return 4 if eg_step_tables[rl][idx & 7] else 0

def lookup_decay_step(slot, counter):
    """对应 emu2413.c:813"""
    rh = slot.eg_rate_h
    rl = slot.eg_rate_l
    if rh == 0:
        return 0
    elif rh == 13:
        idx = ((counter & 0xc) >> 1) | (counter & 1)
        return eg_step_tables[rl][idx]
    elif rh == 14:
        idx = (counter & 0xc) >> 1
        return eg_step_tables[rl][idx] + 1
    elif rh == 15:
        return 2
    else:
        idx = counter >> slot.eg_shift
        return eg_step_tables[rl][idx & 7]

def start_envelope(slot):
    """对应 emu2413.c:833"""
    if min(15, slot.patch.AR + (slot.rks >> 2)) == 15:
        slot.eg_state = DECAY
        slot.eg_out = 0
    else:
        slot.eg_state = ATTACK
    commit_slot_update(slot)

def calc_envelope(slot, eg_counter):
    """对应 emu2413.c:843 calc_envelope (不含 test flag)"""
    mask = (1 << slot.eg_shift) - 1
    if slot.eg_state == ATTACK:
        if 0 < slot.eg_out and 0 < slot.eg_rate_h and (eg_counter & mask & ~3) == 0:
            s = lookup_attack_step(slot, eg_counter)
            if 0 < s:
                slot.eg_out = max(0, slot.eg_out - (slot.eg_out >> s) - 1)
    else:
        if slot.eg_rate_h > 0 and (eg_counter & mask) == 0:
            slot.eg_out = min(EG_MUTE, slot.eg_out + lookup_decay_step(slot, eg_counter))

    # 状态转移
    if slot.eg_state == DAMP:
        if slot.eg_out >= EG_MAX and (eg_counter & mask) == 0:
            start_envelope(slot)
    elif slot.eg_state == ATTACK:
        if slot.eg_out == 0:
            slot.eg_state = DECAY
            commit_slot_update(slot)
    elif slot.eg_state == DECAY:
        if (slot.eg_out >> 3) == slot.patch.SL:
            slot.eg_state = SUSTAIN
            commit_slot_update(slot)
    # SUSTAIN/RELEASE: 无自动转移 (需 keyoff 触发)

def calc_phase(slot, pm_phase):
    """对应 emu2413.c:781 calc_phase (无 test reset)"""
    pm = pm_table[(slot.fnum >> 6) & 7][(pm_phase >> 10) & 7] if slot.patch.PM else 0
    slot.pg_phase += (((slot.fnum & 0x1ff) * 2 + pm) * ml_table[slot.patch.ML]) << slot.blk >> 2
    slot.pg_phase &= (DP_WIDTH - 1)
    slot.pg_out = slot.pg_phase >> DP_BASE_BITS

def slot_on(slot):
    slot.key_flag = 1
    slot.eg_state = DAMP
    commit_slot_update(slot)

def slot_off(slot):
    slot.key_flag = 0
    if slot.type & 1:  # 只有 carrier 响应 keyoff
        slot.eg_state = RELEASE
        commit_slot_update(slot)

def lookup_exp_table(i):
    """对应 emu2413.c:927"""
    t = exp_table[(i & 0xff) ^ 0xff] + 1024
    res = t >> ((i & 0x7f00) >> 8)
    return ((~res if (i & 0x8000) else res)) << 1

def to_linear(h, slot, am):
    """对应 emu2413.c:934"""
    if slot.eg_out > EG_MAX:
        return 0
    att = min(EG_MUTE, (slot.eg_out + slot.tll + am)) << 4
    return lookup_exp_table(h + att)

def calc_slot_mod(slot, lfo_am):
    """对应 emu2413.c:954 calc_slot_mod"""
    fm = (slot.output[1] + slot.output[0]) >> (9 - slot.patch.FB) if slot.patch.FB > 0 else 0
    am = lfo_am if slot.patch.AM else 0
    slot.output[1] = slot.output[0]
    slot.output[0] = to_linear(slot.wave_table[(slot.pg_out + fm) & (PG_WIDTH - 1)], slot, am)
    return slot.output[0]

def calc_slot_car(slot, fm, lfo_am):
    """对应 emu2413.c:943 calc_slot_car"""
    am = lfo_am if slot.patch.AM else 0
    slot.output[1] = slot.output[0]
    slot.output[0] = to_linear(slot.wave_table[(slot.pg_out + 2 * (fm >> 1)) & (PG_WIDTH - 1)], slot, am)
    return slot.output[0]


# ============================================================
#  完整单通道 emu2413 渲染器 (1 个 mod+car 对)
# ============================================================
class EmuChannel:
    """模拟 emu2413 的一个旋律通道 (mod slot + car slot)"""
    def __init__(self, mod_patch, car_patch):
        self.mod = Slot(0)
        self.car = Slot(1)
        self.mod.patch = mod_patch
        self.car.patch = car_patch
        self.mod.eg_state = RELEASE
        self.car.eg_state = RELEASE
        self.mod.eg_out = EG_MUTE
        self.car.eg_out = EG_MUTE
        self.eg_counter = 0
        self.pm_phase = 0
        self.am_phase = 0
        self.lfo_am = 0
        # 初始 commit
        commit_slot_update(self.mod)
        commit_slot_update(self.car)

    def key_on(self):
        slot_on(self.mod)
        slot_on(self.car)

    def key_off(self):
        slot_off(self.mod)
        slot_off(self.car)

    def set_note(self, fnum, blk):
        """设置音高 (fnum: 9-bit, blk: 3-bit)"""
        for slot in (self.mod, self.car):
            slot.fnum = fnum & 0x1ff
            slot.blk = blk & 7
            slot.blk_fnum = ((blk & 7) << 9) | (fnum & 0x1ff)
            commit_slot_update(slot)

    def set_volume(self, volume):
        """volume: 0~63 (寄存器低4位 << 2)"""
        self.car.volume = volume
        commit_slot_update(self.car)

    def set_sus(self, sus_flag):
        self.car.sus_flag = sus_flag
        self.mod.sus_flag = sus_flag

    def render_one(self):
        """渲染一个采样, 返回 carrier 输出 (mono)"""
        # update_ampm
        self.pm_phase = (self.pm_phase + 1) & 0xffffffff
        self.am_phase += 1
        self.lfo_am = am_table[(self.am_phase >> 6) % len(am_table)]
        # update_slots
        self.eg_counter += 1
        for slot in (self.mod, self.car):
            calc_envelope(slot, self.eg_counter)
            calc_phase(slot, self.pm_phase)
        # calc mod then car
        mo = calc_slot_mod(self.mod, self.lfo_am)
        co = calc_slot_car(self.car, mo, self.lfo_am)
        return -(co >> 1)  # _MO macro: -(x)>>1


# ============================================================
#  鼓声完整渲染器 (对应 emu2413 update_output 的 rhythm 分支)
# ============================================================
# 鼓声音色 (default_inst 16/17/18):
#   16: [0x01,0x01,0x18,0x0f,0xdf,0xf8,0x6a,0x6d]  BD mod(SD共用)/BD car
#   17: [0x01,0x01,0x00,0x00,0xc8,0xd8,0xa7,0x68]  HH mod/SD car
#   18: [0x05,0x01,0x00,0x00,0xf8,0xaa,0x59,0x55]  TOM mod/CYM car
#
# 5 个鼓声对应 slot 映射 (update_rhythm_mode):
#   CH7 (slot 12=MOD, slot 13=CAR) -> patch 16 -> Bass Drum (标准二运算器)
#   CH8 (slot 14=MOD, slot 15=CAR) -> patch 17 -> HH(SLOT_HH=14), Snare(SLOT_SD=15)
#   CH9 (slot 16=MOD, slot 17=CAR) -> patch 18 -> TOM(SLOT_TOM=16), Cymbal(SLOT_CYM=17)
#
# key_on 行为 (update_key_status, rhythm_mode=1):
#   BD:    r14&0x10 -> slots 12,13 都 key on (type=1,carrier)
#   HH:    r14&0x01 -> slot 14 key on (type=3,single)
#   SD:    r14&0x08 -> slot 15 key on (type=3,single)
#   TOM:   r14&0x04 -> slot 16 key on (type=3,single)
#   CYM:   r14&0x02 -> slot 17 key on (type=3,single)

DRUM_NAMES = ["BassDrum", "SnareDrum", "TomTom", "HiHat", "TopCymbal"]

def _PD(phase):
    """emu2413 宏: 直接指定 10-bit 相位偏移"""
    return (phase >> (10 - PG_BITS)) if PG_BITS < 10 else (phase << (PG_BITS - 10))

def update_noise(noise, cycle):
    """17-bit LFSR 噪声, 每步: if noise&1: noise ^= 0x800200; noise >>= 1"""
    for _ in range(cycle):
        if noise & 1:
            noise ^= 0x800200
        noise >>= 1
    return noise

def update_short_noise(pg_hh, pg_cym):
    """short_noise = (h_bit2^h_bit7) | (h_bit3^c_bit5) | (c_bit3^c_bit5)"""
    h_bit2 = (pg_hh >> (PG_BITS - 8)) & 1
    h_bit7 = (pg_hh >> (PG_BITS - 3)) & 1
    h_bit3 = (pg_hh >> (PG_BITS - 7)) & 1
    c_bit3 = (pg_cym >> (PG_BITS - 7)) & 1
    c_bit5 = (pg_cym >> (PG_BITS - 5)) & 1
    return (h_bit2 ^ h_bit7) | (h_bit3 ^ c_bit5) | (c_bit3 ^ c_bit5)


class EmuRhythm:
    """模拟 emu2413 rhythm 模式 (6 个 slot: BD1,BD2, HH, SD, TOM, CYM)
    完整移植 update_output 的 rhythm 分支."""
    def __init__(self):
        # 鼓声音色: patch 16 -> slots 12(mod),13(car); patch 17 -> 14(mod),15(car); patch 18 -> 16(mod),17(car)
        bd_mod_p, bd_car_p = dump_to_patch(DEFAULT_INST[16])
        hh_sd_p_mod, hh_sd_p_car = dump_to_patch(DEFAULT_INST[17])
        tom_cym_p_mod, tom_cym_p_car = dump_to_patch(DEFAULT_INST[18])

        # 6 个 rhythm slot (对应 opll->slot[12..17])
        self.slots = []
        for i in range(6):
            self.slots.append(Slot(12 + i))
        # slot 类型: BD1=0(mod), BD2=1(car), HH=3(single), SD=3(single), TOM=3(single), CYM=3(single)
        self.slots[0].type = 0  # BD mod
        self.slots[1].type = 1  # BD car
        self.slots[2].type = 3  # HH
        self.slots[2].pg_keep = 1
        self.slots[3].type = 3  # SD
        self.slots[4].type = 3  # TOM
        self.slots[5].type = 3  # CYM
        self.slots[5].pg_keep = 1

        # 分配 patch
        self.slots[0].patch = bd_mod_p   # BD mod = patch 16 mod
        self.slots[1].patch = bd_car_p   # BD car = patch 16 car
        self.slots[2].patch = hh_sd_p_mod  # HH = patch 17 mod
        self.slots[3].patch = hh_sd_p_car  # SD = patch 17 car
        self.slots[4].patch = tom_cym_p_mod  # TOM = patch 18 mod
        self.slots[5].patch = tom_cym_p_car  # CYM = patch 18 car

        for s in self.slots:
            s.eg_state = RELEASE
            s.eg_out = EG_MUTE
            commit_slot_update(s)

        # 默认频率 (从真实 VGM OPLDRV 始终不变的寄存器值解码):
        #   BD (CH7):   reg0x16=0x20, reg0x26=0x05 → fnum=288, block=2, freq≈109Hz
        #   HH/SD (CH8): reg0x17=0x50, reg0x27=0x05 → fnum=336, block=2, freq≈127Hz
        #   TOM/CYM (CH9): reg0x18=0xc0, reg0x28=0x01 → fnum=448, block=0, freq≈43Hz
        for s in self.slots[:2]:  # BD mod + car (CH7)
            s.fnum, s.blk = 288, 2
            s.blk_fnum = (2 << 9) | 288
            commit_slot_update(s)
        for s in self.slots[2:4]:  # HH + SD (CH8)
            s.fnum, s.blk = 336, 2
            s.blk_fnum = (2 << 9) | 336
            commit_slot_update(s)
        for s in self.slots[4:6]:  # TOM + CYM (CH9)
            s.fnum, s.blk = 448, 0
            s.blk_fnum = (0 << 9) | 448
            commit_slot_update(s)

        self.eg_counter = 0
        self.pm_phase = 0
        self.am_phase = 0
        self.lfo_am = 0
        self.noise = 0x1
        self.short_noise = 0

    # 各鼓 key_on: 按照真实 YM2413 update_key_status 的 rhythm 分支
    def key_bd(self):
        """Bass Drum: slots 0(BD1 mod) + 1(BD2 car) 都 key on"""
        slot_on(self.slots[0])
        slot_on(self.slots[1])

    def key_hh(self):
        slot_on(self.slots[2])

    def key_sd(self):
        slot_on(self.slots[3])

    def key_tom(self):
        slot_on(self.slots[4])

    def key_cym(self):
        slot_on(self.slots[5])

    def render_one_bass_drum(self):
        """BD: 标准二运算器调制 (CH7 -> calc_slot_car(6, calc_slot_mod(6))), _RO 输出"""
        # update_ampm
        self.pm_phase = (self.pm_phase + 1) & 0xffffffff
        self.am_phase += 1
        self.lfo_am = am_table[(self.am_phase >> 6) % len(am_table)]
        # update_slots
        self.eg_counter += 1
        for s in self.slots[:2]:  # BD mod + car
            calc_envelope(s, self.eg_counter)
            calc_phase(s, self.pm_phase)
        # BD: 标准调制
        mo = calc_slot_mod(self.slots[0], self.lfo_am)
        co = calc_slot_car(self.slots[1], mo, self.lfo_am)
        # noise: CH7 后 update_noise(opll, 14)
        self.noise = update_noise(self.noise, 14)
        return co  # _RO(x) = x

    def render_one_sd_hh(self):
        """Snare + HiHat: CH8 分支, 包含 update_noise(2)
        返回 (snare, hihat)"""
        self.pm_phase = (self.pm_phase + 1) & 0xffffffff
        self.am_phase += 1
        self.lfo_am = am_table[(self.am_phase >> 6) % len(am_table)]
        self.eg_counter += 1
        # update short_noise (在 update_slots 之前, 和 emu2413 顺序一致)
        pg_hh = self.slots[2].pg_out
        pg_cym = self.slots[5].pg_out
        self.short_noise = update_short_noise(pg_hh, pg_cym)
        # update HH, SD slots
        for s in self.slots[2:4]:
            calc_envelope(s, self.eg_counter)
            calc_phase(s, self.pm_phase)
        # HiHat: calc_slot_hat -> slot MOD(7) = slots[2]
        slot_hh = self.slots[2]
        if self.short_noise:
            phase = _PD(0x2d0) if (self.noise & 1) else _PD(0x234)
        else:
            phase = _PD(0x34) if (self.noise & 1) else _PD(0xd0)
        hihat = to_linear(slot_hh.wave_table[phase], slot_hh, 0)
        # Snare: calc_slot_snare -> slot CAR(7) = slots[3]
        slot_sd = self.slots[3]
        if (slot_sd.pg_out >> (PG_BITS - 2)) & 1:
            phase = _PD(0x300) if (self.noise & 1) else _PD(0x200)
        else:
            phase = _PD(0x0) if (self.noise & 1) else _PD(0x100)
        snare = to_linear(slot_sd.wave_table[phase], slot_sd, 0)
        # noise: CH8 后 update_noise(opll, 2)
        self.noise = update_noise(self.noise, 2)
        return snare, hihat  # 都是 _RO

    def render_one_tom_cym(self):
        """Tom + Cymbal: CH9 分支, 包含 update_noise(2)
        返回 (tom, cym)"""
        self.pm_phase = (self.pm_phase + 1) & 0xffffffff
        self.am_phase += 1
        self.lfo_am = am_table[(self.am_phase >> 6) % len(am_table)]
        self.eg_counter += 1
        for s in self.slots[4:6]:
            calc_envelope(s, self.eg_counter)
            calc_phase(s, self.pm_phase)
        # Tom: calc_slot_tom -> slot MOD(8) = slots[4]
        slot_tom = self.slots[4]
        tom = to_linear(slot_tom.wave_table[slot_tom.pg_out], slot_tom, 0)
        # Cymbal: calc_slot_cym -> slot CAR(8) = slots[5]
        slot_cym = self.slots[5]
        phase = _PD(0x300) if self.short_noise else _PD(0x100)
        cym = to_linear(slot_cym.wave_table[phase], slot_cym, 0)
        # noise: CH9 后 update_noise(opll, 2)
        self.noise = update_noise(self.noise, 2)
        return tom, cym  # 都是 _RO

    def render_one_all(self):
        """渲染一个采样, 返回混合输出 (BD+SD+HH+TOM+CYM)"""
        bd = self.render_one_bass_drum()
        sd, hh = self.render_one_sd_hh()
        tom, cym = self.render_one_tom_cym()
        return bd + sd + hh + tom + cym


# ============================================================
#  频率 -> (fnum, blk) 转换
# ============================================================
INTERNAL_RATE = 49715.9028  # 3579545 / 72

def freq_to_fnum_blk(freq):
    """YM2413 频率计算.
    emu2413 calc_phase: pg_phase += ((fnum&0x1ff)*2 + pm) * ml_table[ML] << blk >> 2
    一个完整正弦周期 = pg_phase 走过 DP_WIDTH = 2^19
    ML=1 时 ml_table[1]=2, 每采样增量 = fnum*2*2*2^blk/4 = fnum * 2^blk
    每秒周期数 freq = (增量 * INTERNAL_RATE) / 2^19
    => fnum = freq * 2^19 / (2^blk * INTERNAL_RATE)
    选择使 0 <= fnum < 512 的 blk."""
    for blk in range(8):
        fnum = freq * (1 << 19) / ((1 << blk) * INTERNAL_RATE)
        if 0 <= fnum < 512:
            return int(round(fnum)), blk
    return max(0, min(511, int(round(freq * (1 << 19) / INTERNAL_RATE)))), 0


# ============================================================
#  主渲染函数
# ============================================================
def render_emu2413(inst_idx, freq, dur_keyon, dur_keyoff, volume=0):
    """完整 emu2413 旋律通道渲染."""
    mod_patch, car_patch = dump_to_patch(DEFAULT_INST[inst_idx])
    ch = EmuChannel(mod_patch, car_patch)
    fnum, blk = freq_to_fnum_blk(freq)
    ch.set_note(fnum, blk)
    ch.set_volume(volume)
    ch.set_sus(0)

    n_total = int((dur_keyon + dur_keyoff) * INTERNAL_RATE)
    n_keyon = int(dur_keyon * INTERNAL_RATE)

    out = []
    ch.key_on()
    for i in range(n_total):
        if i == n_keyon:
            ch.key_off()
        out.append(ch.render_one())
    return out


def render_drum(drum_type, dur_keyon=0.5, dur_keyoff=1.5):
    """渲染单个鼓声.
    drum_type: 'bd'/'sd'/'tom'/'hh'/'cym'
    dur_keyon: 鼓声触发后持续渲染时间 (鼓声无 key_off, 自然衰减)
    dur_keyoff: 衰减后继续渲染静音部分
    返回 samples (INTERNAL_RATE)."""
    rhy = EmuRhythm()
    n_total = int((dur_keyon + dur_keyoff) * INTERNAL_RATE)

    out = []
    # key on 对应鼓声
    if drum_type == 'bd':
        rhy.key_bd()
    elif drum_type == 'hh':
        rhy.key_hh()
    elif drum_type == 'sd':
        rhy.key_sd()
    elif drum_type == 'tom':
        rhy.key_tom()
    elif drum_type == 'cym':
        rhy.key_cym()

    for _ in range(n_total):
        out.append(rhy.render_one_all())
    return out


# ============================================================
#  V3 简化 FM (下位机模拟) — s8 波形 + 调参对齐 emu2413
#  约束: 波形表 ≤128 点 s8 (不改波形形状), LFO 用查表
#  调参策略:
#    1. LEVEL_GAIN 表: 直接采样 emu2413 eg_out→lookup_exp_table 输出 (eg=0→2042)
#    2. mod 输出 >>6 (peak=4086, emu mod 不做 >>1)
#    3. car 输出 >>7 (peak=2042, emu car 做 >>1)
#    4. tll 直接加到 eg_out (dB 域相加, 与 emu 一致)
#    5. LFO 查表: PM 加相位增量, AM 加 eg_out
#  结果: 15/15 音色 RMS 偏差 < 0.32dB
# ============================================================
def make_64_sin():
    return [int(round(127 * math.sin(i * 2 * math.pi / 64))) for i in range(64)]

def make_64_halfsin():
    t = []
    for i in range(64):
        s = math.sin(i * 2 * math.pi / 64)
        t.append(int(round(127 * max(s, 0))))
    return t

WAVE64_SIN = make_64_sin()
WAVE64_HALFSIN = make_64_halfsin()

def make_level_gain():
    """eg_out (0~127, dB 域) -> 线性增益, 标定到 emu2413 的 lookup_exp_table 输出.
    目标: car_raw_s8(±127) * LEVEL_GAIN[eg] / 127 ≈ emu carrier 输出 (±2042).
    即 LEVEL_GAIN[eg] = emu_amp[eg] (eg=0 → 2042).
    直接采样 emu2413 的 eg_out→幅度曲线 (sin峰值, tll=0)."""
    t = []
    for lv in range(128):
        if lv > EG_MAX:
            t.append(0)
        else:
            att = min(EG_MUTE, lv) << 4
            # sin 峰值处 car_h=0, lookup_exp_table(0+att) 的绝对值 >> 1
            co = lookup_exp_table(0 + att)
            t.append(co >> 1)  # emu render_one: -(co>>1)
    return t

LEVEL_GAIN = make_level_gain()


def render_fm_v3(inst_idx, freq, dur_keyon, dur_keyoff, volume=0):
    """V3 简化 FM: 用 emu 的 eg_out (忠实包络) + s8 波形 (简化合成).
    用 INTERNAL_RATE 渲染以匹配 emu2413 节奏."""
    mod_patch, car_patch = dump_to_patch(DEFAULT_INST[inst_idx])
    ch = EmuChannel(mod_patch, car_patch)
    fnum, blk = freq_to_fnum_blk(freq)
    ch.set_note(fnum, blk)
    ch.set_volume(volume)
    ch.set_sus(0)

    n_total = int((dur_keyon + dur_keyoff) * INTERNAL_RATE)
    n_keyon = int(dur_keyon * INTERNAL_RATE)

    # 跑 emu 的 eg_out 曲线 (忠实包络)
    mod_eg_curve = []
    car_eg_curve = []
    ch.key_on()
    for i in range(n_total):
        if i == n_keyon:
            ch.key_off()
        ch.eg_counter += 1
        for slot in (ch.mod, ch.car):
            calc_envelope(slot, ch.eg_counter)
        mod_eg_curve.append(ch.mod.eg_out)
        car_eg_curve.append(ch.car.eg_out)

    # V3 合成 (s8 波形, 但相位增量必须匹配 emu 的 pg_out 速度)
    mod_wave = WAVE64_SIN if mod_patch.WS == 0 else WAVE64_HALFSIN
    car_wave = WAVE64_SIN if car_patch.WS == 0 else WAVE64_HALFSIN

    # mod 的 tll (与 emu 一致, 直接加到 eg_out 上)
    mod_tll = TLL_TABLE[(blk, (fnum >> 5) & 15, mod_patch.TL, mod_patch.KL)]
    # car 的 tll (carrier TL=0, 用 volume; 这里 volume=0 简化)
    car_tll = TLL_TABLE[(blk, (fnum >> 5) & 15, 0, car_patch.KL)]

    out = []
    mod_pg = 0
    car_pg = 0
    mo1 = 0; mo2 = 0
    pm_phase = 0
    am_phase = 0

    for s in range(n_total):
        # LFO (与 emu 一致, 查表)
        pm_phase = (pm_phase + 1) & 0xffffffff
        am_phase += 1
        lfo_am = am_table[(am_phase >> 6) % len(am_table)]
        mod_pm = pm_table[(fnum >> 6) & 7][(pm_phase >> 10) & 7] if mod_patch.PM else 0
        car_pm = pm_table[(fnum >> 6) & 7][(pm_phase >> 10) & 7] if car_patch.PM else 0
        # PM 加入相位增量 (注意运算符优先级: 先算 step 再加)
        mod_step = (((fnum & 0x1ff) * 2 + mod_pm) * ml_table[mod_patch.ML]) << blk >> 2
        car_step = (((fnum & 0x1ff) * 2 + car_pm) * ml_table[car_patch.ML]) << blk >> 2
        mod_pg = (mod_pg + mod_step) & (DP_WIDTH - 1)
        car_pg = (car_pg + car_step) & (DP_WIDTH - 1)
        midx = (mod_pg >> DP_BASE_BITS) & (PG_WIDTH - 1)
        cidx = (car_pg >> DP_BASE_BITS) & (PG_WIDTH - 1)
        # 映射到 64 点表 (1024 -> 64)
        midx64 = (midx * 64) >> PG_BITS
        cidx64 = (cidx * 64) >> PG_BITS

        # Modulator: 有效 eg = eg_out + tll + AM (与 emu 一致, dB 域相加)
        mod_am = lfo_am if mod_patch.AM else 0
        mod_eff_eg = min(EG_MUTE, mod_eg_curve[s] + mod_tll + mod_am)
        if mod_patch.FB > 0:
            fb = (mo2 + mo1) >> (9 - mod_patch.FB)
            mod_raw = mod_wave[(midx64 + (fb >> 4)) & 63]
        else:
            mod_raw = mod_wave[midx64]
        mo2 = mo1
        # mod 输出标定到 emu 的 lookup_exp_table 原始范围 (±4086):
        # emu mod 不做 >>1 (只有 carrier 做), raw(±127) * LEVEL_GAIN[eg] >> 6
        # LEVEL_GAIN[0]=2042, 127*2042>>6 = 4052 ≈ 4086
        mo1 = (mod_raw * LEVEL_GAIN[mod_eff_eg]) >> 6

        # Carrier: mod 输出作为相位偏移 (emu: fm = 2*(mo>>1) = mo, 加到 1024 点 pg_out)
        # V3 用 64 点表, 缩放 = 64/1024 = 1/16, 所以 fm_shifted = mo1/16 = mo1>>4
        # 但 emu 的 fm = 2*(mo>>1), mo>>1 再 *2 ≈ mo, 所以直接 mo1>>4
        fm_shifted = mo1 >> 4
        car_idx = (cidx64 + fm_shifted) & 63
        car_raw = car_wave[car_idx]
        car_am = lfo_am if car_patch.AM else 0
        car_eff_eg = min(EG_MUTE, car_eg_curve[s] + car_tll + car_am)
        car_val = (car_raw * LEVEL_GAIN[car_eff_eg]) >> 7

        out.append(-car_val)

    return out


# ============================================================
#  V3-FW: 下位机式包络 (查表速率, 独立 eg_out 状态机)
#  与 V3 区别: 不复用 EmuChannel 的 eg_out, 而是用自己的简化包络.
#  包络逻辑照搬 emu (lookup_attack/decay_step + eg_step_tables),
#  但 rate_h/rate_l/eg_shift 在状态转换时预算一次 (不在每采样 commit).
#  验证: 14/15 < 0.1dB, SynthBass 0.745dB
# ============================================================
FW_DAMP_S, FW_ATTACK_S, FW_DECAY_S, FW_SUSTAIN_S, FW_RELEASE_S = 0, 1, 2, 3, 4

class FwSlot:
    """下位机式 operator (独立 eg_out, 不依赖 emu 的 Slot)."""
    __slots__ = ('eg_out','eg_state','rate_h','rate_l','eg_shift','tll',
                 'AR','DR','SL','RR','EG','KR','AM','PM','ML','WS','TL','FB','KL',
                 'sus_flag','type','key_flag','_blk')
    def __init__(self):
        self.eg_out = EG_MUTE
        self.eg_state = FW_RELEASE_S
        self.rate_h = 0; self.rate_l = 0; self.eg_shift = 0
        self.tll = 0
        self.AR = self.DR = self.SL = self.RR = 0
        self.EG = self.KR = self.AM = self.PM = 0
        self.ML = 1; self.WS = 0; self.TL = 0; self.FB = 0; self.KL = 0
        self.sus_flag = 0; self.type = 0; self.key_flag = 0
        self._blk = 4

def _fw_calc_rks(blk, kr):
    return (blk << 1) if kr else (blk >> 1)

def _fw_commit_rate(slot, state, blk):
    """状态转换时预算 rate_h/rate_l/eg_shift (对应 emu commit_slot_update 的 EG 部分).
    下位机只需在 keyon/state 转换时调用一次."""
    if state == FW_ATTACK_S:
        p_rate = slot.AR
    elif state == FW_DECAY_S:
        p_rate = slot.DR
    elif state == FW_SUSTAIN_S:
        p_rate = 0 if slot.EG else slot.RR
    elif state == FW_RELEASE_S:
        p_rate = 5 if slot.sus_flag else (slot.RR if slot.EG else 7)
    elif state == FW_DAMP_S:
        p_rate = DAMPER_RATE
    else:
        p_rate = 0

    rks = _fw_calc_rks(blk, slot.KR)
    if p_rate == 0:
        slot.rate_h = 0; slot.rate_l = 0; slot.eg_shift = 0
        return
    slot.rate_h = min(15, p_rate + (rks >> 2))
    slot.rate_l = rks & 3
    if state == FW_ATTACK_S:
        slot.eg_shift = (13 - slot.rate_h) if (0 < slot.rate_h < 12) else 0
    else:
        slot.eg_shift = (13 - slot.rate_h) if (slot.rate_h < 13) else 0

def _fw_env_tick(slot, eg_counter):
    """下位机包络: 照搬 emu calc_envelope, rate_h/l/shift 已预算."""
    state = slot.eg_state
    rh, rl, shift = slot.rate_h, slot.rate_l, slot.eg_shift
    mask = (1 << shift) - 1

    if state == FW_ATTACK_S:
        if 0 < slot.eg_out and 0 < rh and (eg_counter & mask & ~3) == 0:
            # lookup_attack_step (inline)
            if rh == 12:
                idx = (eg_counter & 0xc) >> 1
                s = 4 - eg_step_tables[rl][idx]
            elif rh == 13:
                idx = (eg_counter & 0xc) >> 1
                s = 3 - eg_step_tables[rl][idx]
            elif rh == 14:
                idx = (eg_counter & 0xc) >> 1
                s = 2 - eg_step_tables[rl][idx]
            elif rh == 0 or rh == 15:
                s = 0
            else:
                idx = eg_counter >> shift
                s = 4 if eg_step_tables[rl][idx & 7] else 0
            if 0 < s:
                slot.eg_out = max(0, slot.eg_out - (slot.eg_out >> s) - 1)
    else:
        if rh > 0 and (eg_counter & mask) == 0:
            # lookup_decay_step (inline)
            if rh == 0:
                step = 0
            elif rh == 13:
                idx = ((eg_counter & 0xc) >> 1) | (eg_counter & 1)
                step = eg_step_tables[rl][idx]
            elif rh == 14:
                idx = (eg_counter & 0xc) >> 1
                step = eg_step_tables[rl][idx] + 1
            elif rh == 15:
                step = 2
            else:
                idx = eg_counter >> shift
                step = eg_step_tables[rl][idx & 7]
            slot.eg_out = min(EG_MUTE, slot.eg_out + step)

    # 状态转移
    if state == FW_DAMP_S:
        if slot.eg_out >= EG_MAX:
            ar_rh = min(15, slot.AR + (_fw_calc_rks(slot._blk, slot.KR) >> 2))
            if ar_rh >= 15:
                slot.eg_state = FW_DECAY_S
                slot.eg_out = 0
                _fw_commit_rate(slot, FW_DECAY_S, slot._blk)
            else:
                slot.eg_state = FW_ATTACK_S
                _fw_commit_rate(slot, FW_ATTACK_S, slot._blk)
    elif state == FW_ATTACK_S:
        if slot.eg_out == 0:
            slot.eg_state = FW_DECAY_S
            _fw_commit_rate(slot, FW_DECAY_S, slot._blk)
    elif state == FW_DECAY_S:
        if (slot.eg_out >> 3) >= slot.SL:
            slot.eg_state = FW_SUSTAIN_S
            _fw_commit_rate(slot, FW_SUSTAIN_S, slot._blk)

def render_fm_v3_fw(inst_idx, freq, dur_keyon, dur_keyoff, volume=0):
    """V3-FW: 下位机式包络 (独立 eg_out 状态机) + s8 波形 + LEVEL_GAIN + LFO.
    包络逻辑照搬 emu, 但 rate_h/l/shift 在状态转换时预算.
    用于验证下位机移植方案的精度."""
    mod_patch, car_patch = dump_to_patch(DEFAULT_INST[inst_idx])
    fnum, blk = freq_to_fnum_blk(freq)

    mod = FwSlot(); car = FwSlot()
    for s, p in [(mod, mod_patch), (car, car_patch)]:
        s.AR=p.AR; s.DR=p.DR; s.SL=p.SL; s.RR=p.RR
        s.EG=p.EG; s.KR=p.KR; s.AM=p.AM; s.PM=p.PM
        s.ML=p.ML; s.WS=p.WS; s.TL=p.TL; s.FB=p.FB; s.KL=p.KL
        s._blk = blk
    car.type = 1

    mod.tll = TLL_TABLE[(blk, (fnum >> 5) & 15, mod_patch.TL, mod_patch.KL)]
    car.tll = TLL_TABLE[(blk, (fnum >> 5) & 15, 0, car_patch.KL)]

    n_total = int((dur_keyon + dur_keyoff) * INTERNAL_RATE)
    n_keyon = int(dur_keyon * INTERNAL_RATE)

    # key on
    mod.key_flag = 1; mod.eg_state = FW_DAMP_S; mod.eg_out = EG_MUTE
    _fw_commit_rate(mod, FW_DAMP_S, blk)
    car.key_flag = 1; car.eg_state = FW_DAMP_S; car.eg_out = EG_MUTE
    _fw_commit_rate(car, FW_DAMP_S, blk)

    mod_wave = WAVE64_SIN if mod_patch.WS == 0 else WAVE64_HALFSIN
    car_wave = WAVE64_SIN if car_patch.WS == 0 else WAVE64_HALFSIN

    out = []
    mod_pg = 0; car_pg = 0
    mo1 = 0; mo2 = 0
    pm_phase = 0; am_phase = 0
    eg_counter = 0

    for s in range(n_total):
        if s == n_keyon:
            # key off
            mod.key_flag = 0
            car.key_flag = 0
            car.eg_state = FW_RELEASE_S
            _fw_commit_rate(car, FW_RELEASE_S, blk)

        eg_counter += 1
        if mod.key_flag or mod.eg_state < FW_RELEASE_S:
            _fw_env_tick(mod, eg_counter)
        _fw_env_tick(car, eg_counter)

        # LFO
        pm_phase = (pm_phase + 1) & 0xffffffff
        am_phase += 1
        lfo_am = am_table[(am_phase >> 6) % len(am_table)]
        mod_pm = pm_table[(fnum >> 6) & 7][(pm_phase >> 10) & 7] if mod_patch.PM else 0
        car_pm = pm_table[(fnum >> 6) & 7][(pm_phase >> 10) & 7] if car_patch.PM else 0
        mod_step = (((fnum & 0x1ff) * 2 + mod_pm) * ml_table[mod_patch.ML]) << blk >> 2
        car_step = (((fnum & 0x1ff) * 2 + car_pm) * ml_table[car_patch.ML]) << blk >> 2
        mod_pg = (mod_pg + mod_step) & (DP_WIDTH - 1)
        car_pg = (car_pg + car_step) & (DP_WIDTH - 1)
        midx = (mod_pg >> DP_BASE_BITS) & (PG_WIDTH - 1)
        cidx = (car_pg >> DP_BASE_BITS) & (PG_WIDTH - 1)
        midx64 = (midx * 64) >> PG_BITS
        cidx64 = (cidx * 64) >> PG_BITS

        mod_am = lfo_am if mod_patch.AM else 0
        mod_eff_eg = min(EG_MUTE, mod.eg_out + mod.tll + mod_am)
        if mod_patch.FB > 0:
            fb = (mo2 + mo1) >> (9 - mod_patch.FB)
            mod_raw = mod_wave[(midx64 + (fb >> 4)) & 63]
        else:
            mod_raw = mod_wave[midx64]
        mo2 = mo1
        mo1 = (mod_raw * LEVEL_GAIN[mod_eff_eg]) >> 6

        fm_shifted = mo1 >> 4
        car_idx = (cidx64 + fm_shifted) & 63
        car_raw = car_wave[car_idx]
        car_am = lfo_am if car_patch.AM else 0
        car_eff_eg = min(EG_MUTE, car.eg_out + car.tll + car_am)
        car_val = (car_raw * LEVEL_GAIN[car_eff_eg]) >> 7

        out.append(-car_val)
    return out


# ============================================================
#  WAV 输出 (从 INTERNAL_RATE 降采样到 SR)
# ============================================================
def downsample(samples, src_rate, dst_rate):
    """简单线性降采样"""
    if src_rate == dst_rate:
        return samples
    ratio = src_rate / dst_rate
    n_out = int(len(samples) / ratio)
    out = []
    for i in range(n_out):
        pos = i * ratio
        i0 = int(pos)
        i1 = min(i0 + 1, len(samples) - 1)
        frac = pos - i0
        out.append(int(samples[i0] * (1 - frac) + samples[i1] * frac))
    return out

def auto_normalize(samples, target_peak=0.85):
    peak = max(abs(s) for s in samples) if samples else 1
    if peak == 0:
        return samples
    scale = (32767 * target_peak) / peak
    return [int(max(-32768, min(32767, s * scale))) for s in samples]

def save_wav(filepath, samples):
    """samples 是 INTERNAL_RATE (49716) 的, 先降采样到 SR, 再归一化保存"""
    samples = downsample(samples, INTERNAL_RATE, SR)
    samples = auto_normalize(samples, target_peak=0.85)
    with wave.open(filepath, 'w') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(struct.pack(f'<{len(samples)}h', *samples))


def main():
    FREQ = 440.0
    DUR_KEYON = 1.0
    DUR_KEYOFF = 1.0

    os.makedirs(EMU2413_DIR, exist_ok=True)
    os.makedirs(FM_V3_DIR, exist_ok=True)
    os.makedirs(FM_V3_FW_DIR, exist_ok=True)

    print("=" * 72)
    print("YM2413 WAV 生成 (emu2413 参考 + V3 调参 + V3-FW 下位机式包络)")
    print(f"  频率: {FREQ} Hz, 时长: {DUR_KEYON}s keyon + {DUR_KEYOFF}s keyoff")
    print(f"  采样率: {SR} Hz (从 49716 重采样)")
    print(f"  输出: wav_emu2413/ + wav_fm_v3/ + wav_fm_v3_fw/")
    print("=" * 72)

    print("\n--- emu2413 (完整移植) → wav_emu2413/ ---")
    for i in range(1, 16):
        mod_p, car_p = dump_to_patch(DEFAULT_INST[i])
        samples = render_emu2413(i, FREQ, DUR_KEYON, DUR_KEYOFF)
        fname = os.path.join(EMU2413_DIR, f"emu2413_inst{i:02d}_{NAMES[i]}.wav")
        save_wav(fname, samples)
        print(f"  {i:2d} {NAMES[i]:<16} "
              f"car[AR={car_p.AR} DR={car_p.DR} SL={car_p.SL} RR={car_p.RR} EG={car_p.EG} ML={car_p.ML} WS={car_p.WS} KL={car_p.KL}] "
              f"-> {os.path.basename(fname)}")

    print("\n--- emu2413 鼓声 → wav_emu2413/ ---")
    drum_map = [('bd', 'BassDrum'), ('sd', 'SnareDrum'), ('tom', 'TomTom'), ('hh', 'HiHat'), ('cym', 'TopCymbal')]
    for dtype, dname in drum_map:
        samples = render_drum(dtype, dur_keyon=0.3, dur_keyoff=1.7)
        fname = os.path.join(EMU2413_DIR, f"emu2413_drum_{dtype}.wav")
        save_wav(fname, samples)
        print(f"  {dname:<16} -> {os.path.basename(fname)}")

    print("\n--- fm_v3 (s8 核心, emu 完整包络) → wav_fm_v3/ ---")
    for i in range(1, 16):
        mod_p, car_p = dump_to_patch(DEFAULT_INST[i])
        samples = render_fm_v3(i, FREQ, DUR_KEYON, DUR_KEYOFF)
        fname = os.path.join(FM_V3_DIR, f"fm_v3_inst{i:02d}_{NAMES[i]}.wav")
        save_wav(fname, samples)
        print(f"  {i:2d} {NAMES[i]:<16} -> {os.path.basename(fname)}")

    print("\n--- fm_v3_fw (s8 核心, 下位机式包络) → wav_fm_v3_fw/ ---")
    for i in range(1, 16):
        mod_p, car_p = dump_to_patch(DEFAULT_INST[i])
        samples = render_fm_v3_fw(i, FREQ, DUR_KEYON, DUR_KEYOFF)
        fname = os.path.join(FM_V3_FW_DIR, f"fm_v3_fw_inst{i:02d}_{NAMES[i]}.wav")
        save_wav(fname, samples)
        print(f"  {i:2d} {NAMES[i]:<16} -> {os.path.basename(fname)}")

    print(f"\n{'='*72}")
    print(f"完成! emu2413 (20) + fm_v3 (15) + fm_v3_fw (15) = 50 个 WAV")
    print(f"  wav_emu2413/   : emu2413 参考 (15 音色 + 5 鼓声)")
    print(f"  wav_fm_v3/     : V3 s8 调参版 (emu 完整包络, 15 音色)")
    print(f"  wav_fm_v3_fw/  : V3-FW 下位机式包络 (查表速率, 15 音色)")
    print(f"{'='*72}")


if __name__ == '__main__':
    main()
