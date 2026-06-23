/* ym2413.c - Yamaha YM2413 (OPLL) FM 合成芯片 (STC32G C251 精简版)
 * 移植自 libvgm emu2413.c (Mitsutaka Okazaki, Valley Bell).
 *
 * 9 通道 2-operator FM + 5 鼓 (rhythm mode).
 * C251 精简:
 *   - tll_table[128][64][4] (128KB!) → 运行时按 makeTllTable 公式算
 *   - rks_table[16][2] → 运行时按 makeRksTable 公式算
 *   - fullsin/halfsin: 只存 1/4 周期 (256 值), 运行时 makeSinTable 展开到 1024
 *   - 去掉 rate converter (sinc/blackman/浮点)
 *   - 去掉 malloc/pan/mask/debug
 *   - request_update/commit_slot_update → 直接更新 (同步)
 */
#include "stc.h"
#include "ym2413.h"

/* ===== 常量 (对齐 emu2413.c) ===== */
#define PG_BITS     10
#define PG_WIDTH    (1 << PG_BITS)       /* 1024 */
#define DP_BITS     19
#define DP_WIDTH    (1 << DP_BITS)
#define DP_BASE_BITS (DP_BITS - PG_BITS) /* 9 */
#define EG_BITS     7
#define EG_MUTE     ((1 << EG_BITS) - 1) /* 127 */
#define EG_MAX      (EG_MUTE - 4)        /* 123 */
#define TL_BITS     6
#define TL2EG(d)    ((d) << 1)
#define DAMPER_RATE 12
#define EG_STEP_X256 96   /* 0.375 * 256, 定点 EG_STEP */
#define TL_STEP_X256 192  /* 0.75 * 256 */

/* envelope states */
#define ATTACK   0
#define DECAY    1
#define SUSTAIN  2
#define RELEASE  3
#define DAMP     4

/* ===== 查找表 (code 段, 只存原始数据) ===== */
static const u16 code exp_table[256] = {
0,3,6,8,11,14,17,20,22,25,28,31,34,37,40,42,45,48,51,54,57,60,63,66,69,72,75,78,81,84,87,90,
93,96,99,102,105,108,111,114,117,120,123,126,130,133,136,139,142,145,148,152,155,158,161,164,168,171,174,177,181,184,187,190,
194,197,200,204,207,210,214,217,220,224,227,231,234,237,241,244,248,251,255,258,262,265,268,272,276,279,283,286,290,293,297,300,
304,308,311,315,318,322,326,329,333,337,340,344,348,352,355,359,363,367,370,374,378,382,385,389,393,397,401,405,409,412,416,420,
424,428,432,436,440,444,448,452,456,460,464,468,472,476,480,484,488,492,496,501,505,509,513,517,521,526,530,534,538,542,547,551,
555,560,564,568,572,577,581,585,590,594,599,603,607,612,616,621,625,630,634,639,643,648,652,657,661,666,670,675,680,684,689,693,
698,703,708,712,717,722,726,731,736,741,745,750,755,760,765,770,774,779,784,789,794,799,804,809,814,819,824,829,834,839,844,849,
854,859,864,869,874,880,885,890,895,900,906,911,916,921,927,932,937,942,948,953,959,964,969,975,980,986,991,996,1002,1007,1013,1018
};

/* 1/4 正弦表 (前 256 值), 运行时 makeSinTable 展开到 1024 */
static u16 xdata fullsin_table[PG_WIDTH];
static u16 xdata halfsin_table[PG_WIDTH];
static const u16 code sin_quarter[256] = {
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
2,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0
};

static const s8 code pm_table[8][8] = {
{0,0,0,0,0,0,0,0},{0,0,1,0,0,0,-1,0},{0,1,2,2,0,-2,-2,-1},
{0,1,3,3,0,-3,-3,-1},{0,2,4,4,0,-4,-4,-2},{0,2,5,5,0,-5,-5,-2},
{0,3,6,6,0,-6,-6,-3},{0,3,7,7,0,-7,-7,-3}
};

/* am_table: 210 samples, 实际是 13-bit 三角波 (0-8191), 但 emu2413 用 LFO_AM_DEPTH=64
 * am_table[x] = round(64 * (1 - cos(2*PI*x/8392)) / 2), 但这里直接搬源码的表 */
static const u8 code am_table[210] = {
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
0,0,1,1,1,1,1,1,1,2,2,2,2,3,3,3,4,4,4,5,5,6,6,7,7,8,8,9,9,10,10,11,
12,12,13,13,14,15,15,16,17,17,18,19,19,20,21,21,22,23,24,24,25,26,26,27,28,29,29,30,31,31,32,33,
34,34,35,36,36,37,38,39,39,40,41,41,42,43,43,44,45,45,46,47,47,48,48,49,50,50,50,51,51,52,52,53,
53,53,54,54,54,55,55,55,56,56,56,56,57,57,57,57,58,58,58,58,58,59,59,59,59,59,59,59,59,59,59,59,
59,59,59,59,59,59,59,59,59,59,59,59,59,59,59,59
};

static const u16 code ml_table[16] = {1,2,4,6,8,10,12,14,16,18,20,22,24,24,24,24};

static const u8 code eg_step_tables[4][8] = {
{0,1,0,1,0,1,0,1},{0,1,0,1,1,1,0,1},{0,1,1,1,0,1,1,1},{0,1,1,1,1,1,1,1}
};

/* kl_table[fnum低4位] = key level 衰减 (定点, ×2 表示 dB) */
static const s16 code kl_table[16] = {
0,18,24,28,30,32,34,35,36,37,38,39,40,40,41,42
};

/* 默认音色 dump (YM2413, 19 voices × 8 bytes) */
static const u8 code default_inst[19*8] = {
0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
0x71,0x61,0x1e,0x17,0xd0,0x78,0x00,0x17,
0x13,0x41,0x1a,0x0d,0xd8,0xf7,0x23,0x13,
0x13,0x01,0x99,0x00,0xf2,0xc4,0x21,0x23,
0x11,0x61,0x0e,0x07,0x8d,0x64,0x70,0x27,
0x32,0x21,0x1e,0x06,0xe1,0x76,0x01,0x28,
0x31,0x22,0x16,0x05,0xe0,0x71,0x00,0x18,
0x21,0x61,0x1d,0x07,0x82,0x81,0x11,0x07,
0x33,0x21,0x2d,0x13,0xb0,0x70,0x00,0x07,
0x61,0x61,0x1b,0x06,0x64,0x65,0x10,0x17,
0x41,0x61,0x0b,0x18,0x85,0xf0,0x81,0x07,
0x33,0x01,0x83,0x11,0xea,0xef,0x10,0x04,
0x17,0xc1,0x24,0x07,0xf8,0xf8,0x22,0x12,
0x61,0x50,0x0c,0x05,0xd2,0xf5,0x40,0x42,
0x01,0x01,0x55,0x03,0xe9,0x90,0x03,0x02,
0x41,0x41,0x89,0x03,0xf1,0xe4,0xc0,0x13,
0x01,0x01,0x18,0x0f,0xdf,0xf8,0x6a,0x6d,
0x01,0x01,0x00,0x00,0xc8,0xd8,0xa7,0x68,
0x05,0x01,0x00,0x00,0xf8,0xaa,0x59,0x55
};

/* ===== 结构 ===== */
typedef struct {
    u32 TL, FB, EG, ML, AR, DR, SL, RR, KR, KL, AM, PM, WS;
} YM_PATCH;

typedef struct {
    u8 type;           /* 0=mod,1=car */
    YM_PATCH *patch;
    s32 output[2];
    u16 *wave;
    u32 pg_phase;
    u32 pg_out;
    u8 pg_keep;
    u16 blk_fnum;
    u16 fnum;
    u8 blk;
    u8 eg_state;
    s32 eg_out;
    u8 key_flag;
    u8 sus_flag;
    u16 tll;
    u8 rks;
    u8 eg_rate_h;
    u8 eg_rate_l;
    u32 eg_shift;
    u8 volume;         /* carrier volume (from reg 0x30-0x38 low 4 bits << 2) */
} YM_SLOT;

typedef struct {
    u8 adr;
    u8 reg[0x40];
    u8 test_flag;
    u8 rhythm_mode;
    u32 eg_counter;
    u32 pm_phase;
    s32 am_phase;
    u8 lfo_am;
    u32 noise;
    u8 short_noise;
    u8 patch_number[9];
    YM_SLOT slot[18];
    YM_PATCH patch[38];   /* 19 voices × 2 (mod+car) */
    s16 ch_out[14];
    u32 step_accum;
    u32 step_incr;
} YM2413_STATE;

static YM2413_STATE xdata ym;

#define MOD(ch) (&ym.slot[2*(ch)])
#define CAR(ch) (&ym.slot[2*(ch)+1])

/* rhythm slot indices */
#define SLOT_BD1  12  /* ch6 mod */
#define SLOT_BD2  13  /* ch6 car */
#define SLOT_HH   14  /* ch7 mod */
#define SLOT_SD   15  /* ch7 car */
#define SLOT_TOM  16  /* ch8 mod */
#define SLOT_CYM  17  /* ch8 car */

/* ===== 表生成 (运行时, 替代 makeTllTable 的 128KB 预计算) ===== */
static void make_sin_table(void) {
    u16 i;
    /* 1/4 周期 → 1/2 周期 (镜像) */
    for (i = 0; i < 256; i++) {
        fullsin_table[255 - i] = sin_quarter[i];
    }
    for (i = 0; i < 256; i++) {
        fullsin_table[256 + i] = sin_quarter[i];
    }
    /* 1/2 周期 → 完整周期 (负半周, bit15=1) */
    for (i = 0; i < 512; i++) {
        fullsin_table[512 + i] = 0x8000 | fullsin_table[i];
    }
    /* halfsin: 前半同 fullsin, 后半 = 0xfff */
    for (i = 0; i < 512; i++) {
        halfsin_table[i] = fullsin_table[i];
    }
    for (i = 512; i < 1024; i++) {
        halfsin_table[i] = 0xFFF;
    }
}

/* 运行时算 tll (替代 tll_table[blk_fnum>>5][TL][KL]):
 *   KL==0: TL2EG(TL)
 *   KL>0:  tmp = kl_table[fnum低4] - 6*(7-blk)  (dB2(3.0)=6 定点)
 *          tmp<=0: TL2EG(TL)
 *          tmp>0:  (tmp >> (3-KL)) / EG_STEP + TL2EG(TL)
 *                 = (tmp >> (3-KL)) * 256 / 96 + TL2EG(TL)  (定点 EG_STEP=0.375) */
static u16 calc_tll(u8 blk, u8 fnum_hi4, u8 TL, u8 KL) {
    if (KL == 0) return TL2EG(TL);
    {
        s32 tmp = (s32)kl_table[fnum_hi4] - 6 * (7 - blk);
        if (tmp <= 0) return TL2EG(TL);
        tmp >>= (3 - KL);
        /* tmp / EG_STEP = tmp / 0.375 = tmp * 8 / 3 */
        return (u16)((tmp * 8 / 3) + TL2EG(TL));
    }
}

/* 运行时算 rks (替代 rks_table[blk_fnum>>8][KR]):
 *   KR==1: (blk<<1) + fnum_hi1
 *   KR==0: blk>>1 */
static u8 calc_rks(u8 blk, u8 fnum_hi1, u8 KR) {
    if (KR) return (blk << 1) + fnum_hi1;
    return blk >> 1;
}

/* ===== dumpToPatch (对齐 emu2413.c) ===== */
static void dump_to_patch(const u8 *dump, YM_PATCH *pm, YM_PATCH *pc) {
    pm->AM = (dump[0] >> 7) & 1; pm->PM = (dump[0] >> 6) & 1;
    pm->EG = (dump[0] >> 5) & 1; pm->KR = (dump[0] >> 4) & 1;
    pm->ML = dump[0] & 0x0F;
    pc->AM = (dump[1] >> 7) & 1; pc->PM = (dump[1] >> 6) & 1;
    pc->EG = (dump[1] >> 5) & 1; pc->KR = (dump[1] >> 4) & 1;
    pc->ML = dump[1] & 0x0F;
    pm->KL = (dump[2] >> 6) & 3; pm->TL = dump[2] & 0x3F;
    pc->KL = (dump[3] >> 6) & 3; pc->TL = 0;
    pm->FB = dump[3] & 7;
    pm->WS = (dump[3] >> 3) & 1; pc->WS = (dump[3] >> 4) & 1;
    pm->AR = (dump[4] >> 4) & 0x0F; pm->DR = dump[4] & 0x0F;
    pc->AR = (dump[5] >> 4) & 0x0F; pc->DR = dump[5] & 0x0F;
    pm->SL = (dump[6] >> 4) & 0x0F; pm->RR = dump[6] & 0x0F;
    pc->SL = (dump[7] >> 4) & 0x0F; pc->RR = dump[7] & 0x0F;
}

/* ===== slot 更新 (同步版, 替代 request_update+commit) ===== */
static u8 get_parameter_rate(YM_SLOT *slot) {
    if ((slot->type & 1) == 0 && slot->key_flag == 0) return 0;
    switch (slot->eg_state) {
    case ATTACK:  return slot->patch->AR;
    case DECAY:   return slot->patch->DR;
    case SUSTAIN: return slot->patch->EG ? 0 : slot->patch->RR;
    case RELEASE:
        if (slot->sus_flag) return 5;
        else if (slot->patch->EG) return slot->patch->RR;
        else return 7;
    case DAMP:    return DAMPER_RATE;
    default:      return 0;
    }
}

static void update_slot_all(YM_SLOT *slot) {
    u8 fnum_hi4 = (slot->blk_fnum >> 5) & 0x0F;
    u8 fnum_hi1 = (slot->blk_fnum >> 8) & 1;
    u8 p_rate;
    /* WS */
    slot->wave = (slot->patch->WS) ? halfsin_table : fullsin_table;
    /* TLL */
    if ((slot->type & 1) == 0) {
        slot->tll = calc_tll(slot->blk, fnum_hi4, slot->patch->TL, slot->patch->KL);
    } else {
        slot->tll = calc_tll(slot->blk, fnum_hi4, slot->volume, slot->patch->KL);
    }
    /* RKS */
    slot->rks = calc_rks(slot->blk, fnum_hi1, slot->patch->KR);
    /* EG rate */
    p_rate = get_parameter_rate(slot);
    if (p_rate == 0) {
        slot->eg_shift = 0; slot->eg_rate_h = 0; slot->eg_rate_l = 0;
        return;
    }
    slot->eg_rate_h = (p_rate + (slot->rks >> 2) > 15) ? 15 : (u8)(p_rate + (slot->rks >> 2));
    slot->eg_rate_l = slot->rks & 3;
    if (slot->eg_state == ATTACK) {
        slot->eg_shift = (slot->eg_rate_h > 0 && slot->eg_rate_h < 12) ? (13 - slot->eg_rate_h) : 0;
    } else {
        slot->eg_shift = (slot->eg_rate_h < 13) ? (13 - slot->eg_rate_h) : 0;
    }
}

static void update_slot_eg(YM_SLOT *slot) {
    u8 p_rate = get_parameter_rate(slot);
    if (p_rate == 0) {
        slot->eg_shift = 0; slot->eg_rate_h = 0; slot->eg_rate_l = 0;
        return;
    }
    slot->eg_rate_h = (p_rate + (slot->rks >> 2) > 15) ? 15 : (u8)(p_rate + (slot->rks >> 2));
    slot->eg_rate_l = slot->rks & 3;
    if (slot->eg_state == ATTACK) {
        slot->eg_shift = (slot->eg_rate_h > 0 && slot->eg_rate_h < 12) ? (13 - slot->eg_rate_h) : 0;
    } else {
        slot->eg_shift = (slot->eg_rate_h < 13) ? (13 - slot->eg_rate_h) : 0;
    }
}

/* ===== set helpers ===== */
static void set_patch(u8 ch, u8 num) {
    ym.patch_number[ch] = num;
    MOD(ch)->patch = &ym.patch[num * 2];
    CAR(ch)->patch = &ym.patch[num * 2 + 1];
    update_slot_all(MOD(ch));
    update_slot_all(CAR(ch));
}

static void set_fnumber(u8 ch, u16 fnum) {
    MOD(ch)->fnum = fnum; CAR(ch)->fnum = fnum;
    MOD(ch)->blk_fnum = (MOD(ch)->blk << 9) | fnum;
    CAR(ch)->blk_fnum = (CAR(ch)->blk << 9) | fnum;
    update_slot_all(MOD(ch));
    update_slot_all(CAR(ch));
}

static void set_block(u8 ch, u8 blk) {
    MOD(ch)->blk = blk; CAR(ch)->blk = blk;
    MOD(ch)->blk_fnum = (blk << 9) | MOD(ch)->fnum;
    CAR(ch)->blk_fnum = (blk << 9) | CAR(ch)->fnum;
    update_slot_all(MOD(ch));
    update_slot_all(CAR(ch));
}

static void set_sus_flag(u8 ch, u8 flag) {
    MOD(ch)->sus_flag = flag; CAR(ch)->sus_flag = flag;
}

static void set_volume(u8 ch, u8 vol) {
    CAR(ch)->volume = vol;
    update_slot_all(CAR(ch));
}

static void set_slot_volume(YM_SLOT *slot, u8 vol) {
    slot->volume = vol;
    update_slot_all(slot);
}

static void slotOn(u8 i) {
    ym.slot[i].key_flag = 1;
    ym.slot[i].eg_state = DAMP;
    update_slot_eg(&ym.slot[i]);
}

static void slotOff(u8 i) {
    ym.slot[i].key_flag = 0;
    if (ym.slot[i].type & 1) {
        ym.slot[i].eg_state = RELEASE;
        update_slot_eg(&ym.slot[i]);
    }
}

static void update_key_status(void) {
    u8 r14 = ym.reg[0x0e];
    u8 rhythm_mode = (r14 >> 5) & 1;
    u32 new_status = 0;
    u32 old_status = 0;
    u32 updated;
    u8 ch;
    /* 先记录旧状态 */
    for (ch = 0; ch < 9; ch++) {
        if (ym.slot[ch*2].key_flag) old_status |= 3UL << (ch*2);
    }
    for (ch = 0; ch < 9; ch++) {
        if (ym.reg[0x20+ch] & 0x10) new_status |= 3UL << (ch*2);
    }
    if (rhythm_mode) {
        if (r14 & 0x10) new_status |= 3UL << SLOT_BD1;
        if (r14 & 0x01) new_status |= 1UL << SLOT_HH;
        if (r14 & 0x08) new_status |= 1UL << SLOT_SD;
        if (r14 & 0x04) new_status |= 1UL << SLOT_TOM;
        if (r14 & 0x02) new_status |= 1UL << SLOT_CYM;
    }
    updated = new_status ^ old_status;
    if (updated) {
        for (ch = 0; ch < 18; ch++) {
            if (updated & (1 << ch)) {
                if (new_status & (1 << ch)) slotOn(ch);
                else slotOff(ch);
            }
        }
    }
}

static void update_rhythm_mode(void) {
    u8 new_rhythm = (ym.reg[0x0e] >> 5) & 1;
    if (ym.rhythm_mode != new_rhythm) {
        if (new_rhythm) {
            /* 进 rhythm mode: ch6/7/8 变成鼓 */
            set_patch(6, 16); set_patch(7, 17); set_patch(8, 18);
            /* BD: mod+car key off then on by update_key_status */
        } else {
            /* 退 rhythm mode */
        }
        ym.rhythm_mode = new_rhythm;
    }
}

/* ===== 核心: phase + envelope ===== */
static void calc_phase(YM_SLOT *slot) {
    s8 pm = slot->patch->PM ? pm_table[(slot->fnum >> 6) & 7][(ym.pm_phase >> 10) & 7] : 0;
    slot->pg_phase += (((slot->fnum & 0x1FF) * 2 + pm) * ml_table[slot->patch->ML]) << slot->blk >> 2;
    slot->pg_phase &= (DP_WIDTH - 1);
    slot->pg_out = slot->pg_phase >> DP_BASE_BITS;
}

static u8 lookup_attack_step(YM_SLOT *slot, u32 counter) {
    u32 index;
    switch (slot->eg_rate_h) {
    case 12: index = (counter & 0xc) >> 1; return 4 - eg_step_tables[slot->eg_rate_l][index];
    case 13: index = (counter & 0xc) >> 1; return 3 - eg_step_tables[slot->eg_rate_l][index];
    case 14: index = (counter & 0xc) >> 1; return 2 - eg_step_tables[slot->eg_rate_l][index];
    case 0: case 15: return 0;
    default: index = counter >> slot->eg_shift; return eg_step_tables[slot->eg_rate_l][index & 7] ? 4 : 0;
    }
}

static u8 lookup_decay_step(YM_SLOT *slot, u32 counter) {
    u32 index;
    switch (slot->eg_rate_h) {
    case 0: return 0;
    case 13: index = ((counter & 0xc) >> 1) | (counter & 1); return eg_step_tables[slot->eg_rate_l][index];
    case 14: index = ((counter & 0xc) >> 1); return eg_step_tables[slot->eg_rate_l][index] + 1;
    case 15: return 2;
    default: index = counter >> slot->eg_shift; return eg_step_tables[slot->eg_rate_l][index & 7];
    }
}

static void start_envelope(YM_SLOT *slot) {
    u8 ar = slot->patch->AR + (slot->rks >> 2);
    if (ar >= 15) {
        slot->eg_state = DECAY;
        slot->eg_out = 0;
    } else {
        slot->eg_state = ATTACK;
    }
    update_slot_eg(slot);
}

static void calc_envelope(YM_SLOT *slot, YM_SLOT *buddy, u32 eg_counter, u8 test) {
    u32 mask = (1UL << slot->eg_shift) - 1;
    u8 s;
    if (slot->eg_state == ATTACK) {
        if (slot->eg_out > 0 && slot->eg_rate_h > 0 && (eg_counter & mask & ~3UL) == 0) {
            s = lookup_attack_step(slot, eg_counter);
            if (s > 0) {
                slot->eg_out = slot->eg_out - (slot->eg_out >> s) - 1;
                if (slot->eg_out < 0) slot->eg_out = 0;
            }
        }
    } else {
        if (slot->eg_rate_h > 0 && (eg_counter & mask) == 0) {
            s = lookup_decay_step(slot, eg_counter);
            slot->eg_out += s;
            if (slot->eg_out > EG_MUTE) slot->eg_out = EG_MUTE;
        }
    }
    switch (slot->eg_state) {
    case DAMP:
        if (slot->eg_out >= (s32)EG_MAX && (eg_counter & mask) == 0) {
            start_envelope(slot);
            if (slot->type & 1) {
                if (!slot->pg_keep) slot->pg_phase = 0;
                if (buddy && !buddy->pg_keep) buddy->pg_phase = 0;
            }
        }
        break;
    case ATTACK:
        if (slot->eg_out == 0) { slot->eg_state = DECAY; update_slot_eg(slot); }
        break;
    case DECAY:
        if ((slot->eg_out >> 3) == (s32)slot->patch->SL) { slot->eg_state = SUSTAIN; update_slot_eg(slot); }
        break;
    }
    if (test) slot->eg_out = 0;
}

/* ===== output helpers ===== */
static s16 lookup_exp_table(u16 i) {
    s16 t = (s16)(exp_table[(i & 0xFF) ^ 0xFF] + 1024);
    s16 res = t >> ((i & 0x7F00) >> 8);
    return ((i & 0x8000) ? ~res : res) << 1;
}

static s16 to_linear(u16 h, YM_SLOT *slot, u8 am) {
    u16 att;
    if (slot->eg_out > (s32)EG_MAX) return 0;
    att = (slot->eg_out + slot->tll + am);
    if (att > EG_MUTE) att = EG_MUTE;
    att <<= 4;
    return lookup_exp_table(h + att);
}

static s16 calc_slot_car(u8 ch, s16 fm) {
    YM_SLOT *slot = CAR(ch);
    u8 am = slot->patch->AM ? ym.lfo_am : 0;
    slot->output[1] = slot->output[0];
    slot->output[0] = to_linear(slot->wave[(slot->pg_out + 2 * (fm >> 1)) & (PG_WIDTH - 1)], slot, am);
    return (s16)slot->output[0];
}

static s16 calc_slot_mod(u8 ch) {
    YM_SLOT *slot = MOD(ch);
    s16 fm = slot->patch->FB > 0 ? (s16)((slot->output[1] + slot->output[0]) >> (9 - slot->patch->FB)) : 0;
    u8 am = slot->patch->AM ? ym.lfo_am : 0;
    slot->output[1] = slot->output[0];
    slot->output[0] = to_linear(slot->wave[(slot->pg_out + fm) & (PG_WIDTH - 1)], slot, am);
    return (s16)slot->output[0];
}

/* rhythm slots */
#define _PD(phase) (phase)   /* PG_BITS=10, 无需移位 */
static s16 calc_slot_tom(void) {
    YM_SLOT *slot = MOD(8);
    return to_linear(slot->wave[slot->pg_out], slot, 0);
}
static s16 calc_slot_snare(void) {
    YM_SLOT *slot = CAR(7);
    u32 phase;
    if (slot->pg_out & (1 << (PG_BITS-2)))
        phase = (ym.noise & 1) ? 0x300 : 0x200;
    else
        phase = (ym.noise & 1) ? 0x000 : 0x100;
    return to_linear(slot->wave[phase], slot, 0);
}
static s16 calc_slot_cym(void) {
    YM_SLOT *slot = CAR(8);
    u32 phase = ym.short_noise ? 0x300 : 0x100;
    return to_linear(slot->wave[phase], slot, 0);
}
static s16 calc_slot_hat(void) {
    YM_SLOT *slot = MOD(7);
    u32 phase;
    if (ym.short_noise)
        phase = (ym.noise & 1) ? 0x2D0 : 0x234;
    else
        phase = (ym.noise & 1) ? 0x034 : 0x0D0;
    return to_linear(slot->wave[phase], slot, 0);
}

#define _MO(x) (-(x) >> 1)
#define _RO(x) (x)

static void update_noise(u8 cycles) {
    u8 i;
    for (i = 0; i < cycles; i++) {
        if (ym.noise & 1) ym.noise ^= 0x800200;
        ym.noise >>= 1;
    }
}

static void update_short_noise(void) {
    u32 pg_hh = ym.slot[SLOT_HH].pg_out;
    u32 pg_cym = ym.slot[SLOT_CYM].pg_out;
    u8 h_bit2 = (pg_hh >> (PG_BITS-8)) & 1;
    u8 h_bit7 = (pg_hh >> (PG_BITS-3)) & 1;
    u8 h_bit3 = (pg_hh >> (PG_BITS-7)) & 1;
    u8 c_bit3 = (pg_cym >> (PG_BITS-7)) & 1;
    u8 c_bit5 = (pg_cym >> (PG_BITS-5)) & 1;
    ym.short_noise = (h_bit2 ^ h_bit7) | (h_bit3 ^ c_bit5) | (c_bit3 ^ c_bit5);
}

static void update_ampm(void) {
    if (ym.test_flag & 2) { ym.pm_phase = 0; ym.am_phase = 0; }
    else {
        ym.pm_phase += (ym.test_flag & 8) ? 1024 : 1;
        ym.am_phase += (ym.test_flag & 8) ? 64 : 1;
    }
    ym.lfo_am = am_table[(ym.am_phase >> 6) % 210];
}

static void update_slots(void) {
    u8 i;
    ym.eg_counter++;
    for (i = 0; i < 18; i++) {
        YM_SLOT *slot = &ym.slot[i];
        YM_SLOT *buddy = (slot->type == 0) ? &ym.slot[i+1] : &ym.slot[i-1];
        calc_envelope(slot, buddy, ym.eg_counter, ym.test_flag & 1);
        calc_phase(slot);
    }
}

static void update_output(void) {
    u8 i;
    update_ampm();
    update_short_noise();
    update_slots();
    for (i = 0; i < 14; i++) ym.ch_out[i] = 0;
    /* CH1-6 */
    for (i = 0; i < 6; i++) {
        ym.ch_out[i] = _MO(calc_slot_car(i, calc_slot_mod(i)));
    }
    /* CH7 (ch6) */
    if (!ym.rhythm_mode) {
        ym.ch_out[6] = _MO(calc_slot_car(6, calc_slot_mod(6)));
    } else {
        ym.ch_out[9] = _RO(calc_slot_car(6, calc_slot_mod(6)));  /* BD */
    }
    update_noise(14);
    /* CH8 (ch7) */
    if (!ym.rhythm_mode) {
        ym.ch_out[7] = _MO(calc_slot_car(7, calc_slot_mod(7)));
    } else {
        ym.ch_out[10] = _RO(calc_slot_hat());   /* HH */
        ym.ch_out[11] = _RO(calc_slot_snare());  /* SD */
    }
    update_noise(2);
    /* CH9 (ch8) */
    if (!ym.rhythm_mode) {
        ym.ch_out[8] = _MO(calc_slot_car(8, calc_slot_mod(8)));
    } else {
        ym.ch_out[12] = _RO(calc_slot_tom());   /* TOM */
        ym.ch_out[13] = _RO(calc_slot_cym());    /* CYM */
    }
}

/* ===== 公开接口 ===== */
void ym2413_set_clock(u32 clock_hz) {
    u32 internal = clock_hz / 72;
    /* (internal << 24) / 22050, 用 double 避免 32 位溢出 */
    ym.step_incr = (u32)((double)internal * 16777216.0 / 22050.0);
}

void ym2413_init(void) {
    u8 i, j;
    make_sin_table();
    /* 清零状态 */
    for (i = 0; i < 0x40; i++) ym.reg[i] = 0;
    ym.adr = 0; ym.test_flag = 0; ym.rhythm_mode = 0;
    ym.eg_counter = 0; ym.pm_phase = 0; ym.am_phase = 0;
    ym.lfo_am = 0; ym.noise = 0; ym.short_noise = 0;
    ym.step_accum = 0;
    /* 解码默认音色 */
    for (i = 0; i < 19; i++) {
        dump_to_patch(&default_inst[i*8], &ym.patch[i*2], &ym.patch[i*2+1]);
    }
    /* 初始化 slot */
    for (i = 0; i < 18; i++) {
        ym.slot[i].type = i & 1;
        ym.slot[i].pg_keep = 0;
        ym.slot[i].wave = fullsin_table;
        ym.slot[i].pg_phase = 0; ym.slot[i].pg_out = 0;
        ym.slot[i].output[0] = 0; ym.slot[i].output[1] = 0;
        ym.slot[i].eg_state = RELEASE;
        ym.slot[i].eg_out = EG_MUTE;
        ym.slot[i].key_flag = 0; ym.slot[i].sus_flag = 0;
        ym.slot[i].blk_fnum = 0; ym.slot[i].fnum = 0; ym.slot[i].blk = 0;
        ym.slot[i].volume = 0; ym.slot[i].rks = 0;
        ym.slot[i].eg_shift = 0; ym.slot[i].eg_rate_h = 0; ym.slot[i].eg_rate_l = 0;
        ym.slot[i].tll = 0;
        ym.slot[i].patch = &ym.patch[0];  /* 默认 patch 0 */
    }
    for (i = 0; i < 9; i++) {
        ym.patch_number[i] = 0;
    }
    for (i = 0; i < 14; i++) ym.ch_out[i] = 0;
    ym2413_set_clock(3579545UL);
}

void ym2413_wr(u8 reg, u8 val) {
    u8 ch, i;
    /* A0=0: 地址锁存; A0=1: 数据写. 这里 val 已经是数据, reg 是地址. */
    /* (上位机 0x51 命令: [0x51][reg][data], reg 是 YM2413 寄存器号) */
    /* mirror registers */
    if ((reg >= 0x19 && reg <= 0x1F) || (reg >= 0x29 && reg <= 0x2F) || (reg >= 0x39 && reg <= 0x3F)) {
        reg -= 9;
    }
    if (reg >= 0x40) return;
    ym.reg[reg] = val;
    switch (reg) {
    /* 用户音色 reg 0x00-0x07 */
    case 0x00: ym.patch[0].AM=(val>>7)&1; ym.patch[0].PM=(val>>6)&1; ym.patch[0].EG=(val>>5)&1; ym.patch[0].KR=(val>>4)&1; ym.patch[0].ML=val&15;
        for(i=0;i<9;i++) if(ym.patch_number[i]==0) { update_slot_all(MOD(i)); } break;
    case 0x01: ym.patch[1].AM=(val>>7)&1; ym.patch[1].PM=(val>>6)&1; ym.patch[1].EG=(val>>5)&1; ym.patch[1].KR=(val>>4)&1; ym.patch[1].ML=val&15;
        for(i=0;i<9;i++) if(ym.patch_number[i]==0) { update_slot_all(CAR(i)); } break;
    case 0x02: ym.patch[0].KL=(val>>6)&3; ym.patch[0].TL=val&63;
        for(i=0;i<9;i++) if(ym.patch_number[i]==0) { update_slot_all(MOD(i)); } break;
    case 0x03: ym.patch[1].KL=(val>>6)&3; ym.patch[1].WS=(val>>4)&1; ym.patch[0].WS=(val>>3)&1; ym.patch[0].FB=val&7;
        for(i=0;i<9;i++) if(ym.patch_number[i]==0) { update_slot_all(MOD(i)); update_slot_all(CAR(i)); } break;
    case 0x04: ym.patch[0].AR=(val>>4)&15; ym.patch[0].DR=val&15;
        for(i=0;i<9;i++) if(ym.patch_number[i]==0) { update_slot_eg(MOD(i)); } break;
    case 0x05: ym.patch[1].AR=(val>>4)&15; ym.patch[1].DR=val&15;
        for(i=0;i<9;i++) if(ym.patch_number[i]==0) { update_slot_eg(CAR(i)); } break;
    case 0x06: ym.patch[0].SL=(val>>4)&15; ym.patch[0].RR=val&15;
        for(i=0;i<9;i++) if(ym.patch_number[i]==0) { update_slot_eg(MOD(i)); } break;
    case 0x07: ym.patch[1].SL=(val>>4)&15; ym.patch[1].RR=val&15;
        for(i=0;i<9;i++) if(ym.patch_number[i]==0) { update_slot_eg(CAR(i)); } break;
    /* rhythm/key control */
    case 0x0e: update_rhythm_mode(); update_key_status(); break;
    case 0x0f: ym.test_flag = val; break;
    /* f-number low */
    case 0x10: case 0x11: case 0x12: case 0x13: case 0x14: case 0x15: case 0x16: case 0x17: case 0x18:
        ch = reg - 0x10;
        set_fnumber(ch, val + ((ym.reg[0x20+ch] & 1) << 8));
        break;
    /* f-number high / block / sus / key-on */
    case 0x20: case 0x21: case 0x22: case 0x23: case 0x24: case 0x25: case 0x26: case 0x27: case 0x28:
        ch = reg - 0x20;
        set_fnumber(ch, ((val & 1) << 8) + ym.reg[0x10+ch]);
        set_block(ch, (val >> 1) & 7);
        set_sus_flag(ch, (val >> 5) & 1);
        update_key_status();
        break;
    /* instrument + volume */
    case 0x30: case 0x31: case 0x32: case 0x33: case 0x34: case 0x35: case 0x36: case 0x37: case 0x38:
        ch = reg - 0x30;
        if ((ym.reg[0x0e] & 32) && reg >= 0x36) {
            if (reg == 0x37) set_slot_volume(MOD(7), ((val>>4)&15)<<2);
            else if (reg == 0x38) set_slot_volume(MOD(8), ((val>>4)&15)<<2);
        } else {
            set_patch(ch, (val >> 4) & 15);
        }
        set_volume(ch, (val & 15) << 2);
        break;
    }
}

s16 ym2413_render(void) {
    s32 out = 0;
    u8 i;
    /* 内部采样率 49716Hz → 外部 22050Hz, 用 step_accum 控制调用频率 */
    ym.step_accum += ym.step_incr;
    while (ym.step_accum >= (1UL << 24)) {
        ym.step_accum -= (1UL << 24);
        update_output();
        /* mix 14 通道 */
        for (i = 0; i < 14; i++) out += ym.ch_out[i];
    }
    /* out 范围约 ±4096*9, 缩放 */
    out >>= 2;
    if (out > 32767) out = 32767;
    if (out < -32768) out = -32768;
    return (s16)out;
}
