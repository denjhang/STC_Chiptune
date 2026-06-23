/* ym2413.c - Yamaha YM2413 (OPLL) FM 合成 (STC32G C251 s8 核心)
 *
 * 寄存器完整兼容 YM2413, FM 核心: 64 点 s8 波形 + eg_out 包络.
 * 严格对照 PC render_fm_v3_fw (ym2413_wav_gen.py):
 * - eg_out (0~127 dB域) 包络, 照搬 emu2413 calc_envelope
 * - rate_h/rate_l/eg_shift 状态转换时预算 (不在每采样 commit)
 * - LEVEL_GAIN[128] 采样 emu2413 eg_out→lookup_exp_table 输出
 * - LFO: PM (pm_table 加相位) + AM (am_table 加 eg_out)
 * - 19-bit pg_phase, >>9 得 pg_out, 映射到 64 点表
 * - mod 输出 >>6 (peak 4086), car 输出 >>7 (peak 2042)
 * - tll = TL*2 + KL 衰减, 直接加到 eg_out (dB 域)
 *
 * PC 验证: 14/15 音色 < 0.1dB (render_fm_v3_fw vs emu2413)
 */
#include "stc.h"
#include "ym2413.h"

/* ===== 64 点波形表 (s8, ±127, 与 PC V3 WAVE64 完全一致) ===== */
/* WS=0: 正弦 (正常 FM) */
static const s8 code ym_sin[64] = {
      0,  12,  25,  37,  49,  60,  71,  81,  90,  98, 106, 112, 117, 122, 125, 126,
    127, 126, 125, 122, 117, 112, 106,  98,  90,  81,  71,  60,  49,  37,  25,  12,
      0, -12, -25, -37, -49, -60, -71, -81, -90, -98,-106,-112,-117,-122,-125,-126,
   -127,-126,-125,-122,-117,-112,-106, -98, -90, -81, -71, -60, -49, -37, -25, -12,
};
/* WS=1: 半正弦 (emu2413: 负半周静音, 不是镜像) */
static const s8 code ym_halfsin[64] = {
      0,  12,  25,  37,  49,  60,  71,  81,  90,  98, 106, 112, 117, 122, 125, 126,
    127, 126, 125, 122, 117, 112, 106,  98,  90,  81,  71,  60,  49,  37,  25,  12,
      0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,
      0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,
};

/* ===== LEVEL_GAIN[128]: eg_out(0~127 dB域) → 线性增益 ===== */
/* 直接采样 emu2413 eg_out→lookup_exp_table 输出 (eg=0→2042, eg>=124→0) */
static const u16 code ym_level_gain[128] = {
     2042, 1956, 1873, 1794, 1717, 1645, 1575, 1508,
     1444, 1383, 1324, 1268, 1214, 1163, 1114, 1066,
     1021,  978,  936,  897,  858,  822,  787,  754,
      722,  691,  662,  634,  607,  581,  557,  533,
      510,  489,  468,  448,  429,  411,  393,  377,
      361,  345,  331,  317,  303,  290,  278,  266,
      255,  244,  234,  224,  214,  205,  196,  188,
      180,  172,  165,  158,  151,  145,  139,  133,
      127,  122,  117,  112,  107,  102,   98,   94,
       90,   86,   82,   79,   75,   72,   69,   66,
       63,   61,   58,   56,   53,   51,   49,   47,
       45,   43,   41,   39,   37,   36,   34,   33,
       31,   30,   29,   28,   26,   25,   24,   23,
       22,   21,   20,   19,   18,   18,   17,   16,
       15,   15,   14,   14,   13,   12,   12,   11,
       11,   10,   10,    9,    0,    0,    0,    0,
};

/* ===== eg_step_tables[4][8]: emu2413 包络步长模式 (attack/decay 共用) ===== */
static const u8 code ym_eg_step_tables[4][8] = {
    {0,1,0,1,0,1,0,1},
    {0,1,0,1,1,1,0,1},
    {0,1,1,1,0,1,1,1},
    {0,1,1,1,1,1,1,1},
};

/* ===== PM/AM LFO 表 (emu2413) ===== */
static const s8 code ym_pm_table[8][8] = {
    {0,0,0,0,0,0,0,0},
    {0,0,1,0,0,0,-1,0},
    {0,1,2,1,0,-1,-2,-1},
    {0,1,3,1,0,-1,-3,-1},
    {0,2,4,2,0,-2,-4,-2},
    {0,2,5,2,0,-2,-5,-2},
    {0,3,6,3,0,-3,-6,-3},
    {0,3,7,3,0,-3,-7,-3},
};
static const u8 code ym_am_table[210] = {
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
1,1,1,1,1,1,1,1,0,0,0,0,0,0,0
};

/* ===== ML 查表 (YM2413 multiple, ml=0 时 0.5) ===== */
/* 用定点: 实际 = ml_table[ML] / 2, ml=0 → 0.5, ml=1 → 1, ml=2 → 2 ... */
static const u8 code ym_ml_table[16] = {
    1, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 24, 24, 24
};

/* ===== 默认音色 dump (19 voices × 8 bytes) ===== */
/* dump 格式 (dumpToPatch):
 *   [0] mod: AM PM EG KR ML(4)
 *   [1] car: AM PM EG KR ML(4)
 *   [2] mod: KL(2) TL(6)
 *   [3] car: KL(2) WS(1) FB(3) WS_mod(1)  ← 注意 FB 在这里
 *   [4] mod: AR(4) DR(4)
 *   [5] car: AR(4) DR(4)
 *   [6] mod: SL(4) RR(4)
 *   [7] car: SL(4) RR(4)
 */
static const u8 code ym_default_inst[19*8] = {
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

/* ===== 音色参数 (解码后) ===== */
typedef struct {
    u8 mod_ml, car_ml;     /* frequency multiplier */
    u8 mod_tl;             /* modulator total level (0-63) */
    u8 mod_fb;             /* feedback (0-7) */
    u8 mod_ar, mod_dr;     /* attack/decay rate */
    u8 car_ar, car_dr;
    u8 mod_sl, mod_rr;     /* sustain level / release rate */
    u8 car_sl, car_rr;
    u8 mod_eg, car_eg;     /* EG type: 0=sustaining, 1=non-sustaining */
    u8 mod_ws, car_ws;     /* wave select */
    u8 mod_kr, car_kr;     /* key rate scaling */
    u8 mod_am, car_am;     /* AM LFO enable */
    u8 mod_pm, car_pm;     /* PM LFO enable */
    u8 mod_kl, car_kl;     /* key scale level */
} YM_VOICE_PATCH;

/* ===== Operator 状态 (s8 FM + eg_out 包络) ===== */
/* 严格对照 PC FwSlot */
typedef struct {
    u8 active;
    u8 ml;
    u8 fb;
    u8 AR, DR, SL, RR;     /* ADSR rate (0~15, 原始 YM2413 值) */
    u8 eg_type;
    u8 kr;
    u8 am, pm;             /* LFO enable */
    u8 sus_flag;
    const s8 code *wave;
    u32 pos;               /* 19-bit pg_phase (与 emu 一致) */
    s16 mo1, mo2;          /* feedback 历史 (mod 才用) */
    /* eg_out 包络 (0~127 dB域, 0=最响, 127=静音) */
    u8 eg_out;
    u8 eg_state;           /* DAMP=0,ATTACK=1,DECAY=2,SUSTAIN=3,RELEASE=4 */
    u8 rate_h;             /* 预算: eg_rate_h (0~15) */
    u8 rate_l;             /* 预算: eg_rate_l (0~3) */
    u8 eg_shift;           /* 预算: 13-rate_h */
    u8 tll;                /* total level + KL (加到 eg_out) */
} YM_OP;

/* ===== 通道 (9 旋律 + rhythm) ===== */
typedef struct {
    YM_OP mod, car;        /* 2 operators */
    YM_VOICE_PATCH *patch; /* 当前音色指针 */
    u8 key_on;             /* key-on 状态 */
    u8 sus_flag;           /* sustain (reg 0x2x bit5) */
    u8 vol;                /* volume (reg 0x3x 低4位 << 2, 0-60) */
} YM_CHANNEL;

/* ===== 全局状态 ===== */
#define YM_CHANNELS 9
static YM_CHANNEL xdata ym_ch[YM_CHANNELS];
static YM_VOICE_PATCH xdata ym_patch[19];   /* 0=用户, 1-15=内置, 16-18=rhythm */
static u8 xdata ym_reg[0x40];
static u8 xdata ym_ch_patch[YM_CHANNELS];   /* 当前每通道用的音色号 */
static u8 xdata ym_rhythm_mode;
/* 噪声发生器 (AY8910 原理: 17-bit LFSR, 用于鼓声 HH/SD/CYM) */
static u32 data ym_noise_seed;
static u8 data ym_noise_step;
static u8 data ym_noise_val;
static u8 data ym_test_flag;
/* 全局包络计数器 + LFO 相位 (所有 slot 共享, 与 emu2413 一致) */
static u32 data ym_eg_counter;
static u32 data ym_pm_phase;
static u16 data ym_am_phase;

/* EG 状态枚举 (与 PC FwSlot 一致) */
#define EG_DAMP    0
#define EG_ATTACK  1
#define EG_DECAY   2
#define EG_SUSTAIN 3
#define EG_RELEASE 4
#define EG_MUTE_VAL 127
#define EG_MAX_VAL  123

/* ===== 解码音色 dump (完全对照 EOPLL_dumpToPatch) ===== */
static void ym_decode_patch(const u8 *dump, YM_VOICE_PATCH *p) {
    p->mod_am = (dump[0] >> 7) & 1;
    p->car_am = (dump[1] >> 7) & 1;
    p->mod_pm = (dump[0] >> 6) & 1;
    p->car_pm = (dump[1] >> 6) & 1;
    p->mod_eg = (dump[0] >> 5) & 1;
    p->car_eg = (dump[1] >> 5) & 1;
    p->mod_kr = (dump[0] >> 4) & 1;
    p->car_kr = (dump[1] >> 4) & 1;
    p->mod_ml = dump[0] & 0x0F;
    p->car_ml = dump[1] & 0x0F;
    p->mod_kl = (dump[2] >> 6) & 3;
    p->car_kl = (dump[3] >> 6) & 3;
    p->mod_tl = dump[2] & 0x3F;
    p->mod_fb = dump[3] & 0x07;
    p->mod_ws = (dump[3] >> 3) & 1;
    p->car_ws = (dump[3] >> 4) & 1;
    p->mod_ar = (dump[4] >> 4) & 0x0F;
    p->mod_dr = dump[4] & 0x0F;
    p->car_ar = (dump[5] >> 4) & 0x0F;
    p->car_dr = dump[5] & 0x0F;
    p->mod_sl = (dump[6] >> 4) & 0x0F;
    p->mod_rr = dump[6] & 0x0F;
    p->car_sl = (dump[7] >> 4) & 0x0F;
    p->car_rr = dump[7] & 0x0F;
}

/* ===== 应用音色到通道 (存原始 YM2413 参数, 不做查表映射) ===== */
static void ym_apply_patch(u8 ch) {
    YM_VOICE_PATCH *p = ym_ch[ch].patch;
    YM_OP *mod = &ym_ch[ch].mod;
    YM_OP *car = &ym_ch[ch].car;
    mod->ml = ym_ml_table[p->mod_ml];
    car->ml = ym_ml_table[p->car_ml];
    mod->fb = p->mod_fb;
    mod->eg_type = p->mod_eg;
    mod->kr = p->mod_kr;
    mod->am = p->mod_am;
    mod->pm = p->mod_pm;
    mod->AR = p->mod_ar; mod->DR = p->mod_dr;
    mod->SL = p->mod_sl; mod->RR = p->mod_rr;
    mod->wave = p->mod_ws ? ym_halfsin : ym_sin;
    car->fb = 0;
    car->eg_type = p->car_eg;
    car->kr = p->car_kr;
    car->am = p->car_am;
    car->pm = p->car_pm;
    car->AR = p->car_ar; car->DR = p->car_dr;
    car->SL = p->car_sl; car->RR = p->car_rr;
    car->wave = p->car_ws ? ym_halfsin : ym_sin;
}

/* (ym_calc_step/ym_update_step 已删除: render 里现场算 pg_phase step) */

/* ===== rks 计算 (对照 PC _fw_calc_rks) ===== */
static u8 ym_calc_rks(u8 blk, u8 kr) {
    /* blk 已做 -1 修正 (见 ym_get_blk) */
    return kr ? (blk << 1) : (blk >> 1);
}

/* ===== 获取通道 blk (含 -1 八度修正) ===== */
static u8 ym_get_blk(u8 ch) {
    u8 blk = (ym_reg[0x20 + ch] >> 1) & 7;
    if (blk > 0) blk--;
    return blk;
}

/* ===== commit_rate: 状态转换时预算 rate_h/rate_l/eg_shift (对照 PC _fw_commit_rate) ===== */
static void ym_commit_rate(YM_OP *op, u8 state, u8 blk) {
    u8 p_rate, rks;
    if (state == EG_ATTACK)       p_rate = op->AR;
    else if (state == EG_DECAY)   p_rate = op->DR;
    else if (state == EG_SUSTAIN) p_rate = op->eg_type ? 0 : op->RR;
    else if (state == EG_RELEASE) p_rate = op->sus_flag ? 5 : (op->eg_type ? op->RR : 7);
    else if (state == EG_DAMP)    p_rate = 12;  /* DAMPER_RATE */
    else p_rate = 0;

    rks = ym_calc_rks(blk, op->kr);
    if (p_rate == 0) {
        op->rate_h = 0; op->rate_l = 0; op->eg_shift = 0;
        return;
    }
    op->rate_h = p_rate + (rks >> 2);
    if (op->rate_h > 15) op->rate_h = 15;
    op->rate_l = rks & 3;
    if (state == EG_ATTACK) {
        op->eg_shift = (0 < op->rate_h && op->rate_h < 12) ? (13 - op->rate_h) : 0;
    } else {
        op->eg_shift = (op->rate_h < 13) ? (13 - op->rate_h) : 0;
    }
}

/* ===== tll 计算 (对照 PC TLL_TABLE, 简化: 运行时算) ===== */
static u8 ym_calc_tll(u8 blk, u8 fnum_hi4, u8 tl, u8 kl) {
    u16 tll = tl << 1;  /* TL2EG */
    if (kl > 0) {
        static const u8 code kl_db2[16] = {
            0,18,24,28,30,32,34,35,36,38,38,39,40,41,41,42
        };
        s16 tmp = (s16)kl_db2[fnum_hi4] - 6 * (7 - blk);
        if (tmp > 0) tll += (u16)(tmp >> (3 - kl));
    }
    return (u8)tll;
}

/* ===== 更新通道 tll (fnum/blk/vol/patch 改变时) ===== */
static void ym_update_tll(u8 ch) {
    u8 blk = ym_get_blk(ch);
    u16 fnum = (u16)ym_reg[0x10 + ch] | ((u16)(ym_reg[0x20 + ch] & 1) << 8);
    u8 fnum_hi4 = (fnum >> 5) & 15;
    YM_VOICE_PATCH *p = ym_ch[ch].patch;
    ym_ch[ch].mod.tll = ym_calc_tll(blk, fnum_hi4, p->mod_tl, p->mod_kl);
    ym_ch[ch].car.tll = ym_calc_tll(blk, fnum_hi4, ym_ch[ch].vol, p->car_kl);
}

/* ===== key on/off (对照 PC render_fm_v3_fw 的 key on 逻辑) ===== */
static void ym_key_on(u8 ch) {
    YM_OP *mod = &ym_ch[ch].mod;
    YM_OP *car = &ym_ch[ch].car;
    u8 blk = ym_get_blk(ch);
    ym_ch[ch].key_on = 1;
    mod->pos = 0; car->pos = 0;
    mod->mo1 = 0; mod->mo2 = 0;
    /* DAMP 起始: eg_out=EG_MUTE, 快速升到 EG_MAX 触发 start_envelope */
    mod->eg_state = EG_DAMP; mod->eg_out = EG_MUTE_VAL;
    car->eg_state = EG_DAMP; car->eg_out = EG_MUTE_VAL;
    ym_commit_rate(mod, EG_DAMP, blk);
    ym_commit_rate(car, EG_DAMP, blk);
}

static void ym_key_off(u8 ch) {
    YM_OP *car = &ym_ch[ch].car;
    u8 blk = ym_get_blk(ch);
    ym_ch[ch].key_on = 0;
    /* 只有 carrier 响应 keyoff (type&1); mod 保持 (对照 PC) */
    car->eg_state = EG_RELEASE;
    ym_commit_rate(car, EG_RELEASE, blk);
}

/* ===== 更新 key 状态 (reg 0x20-0x28 或 0x0E 改变时) ===== */
static void ym_update_keys(void) {
    u8 ch;
    u8 r14 = ym_reg[0x0E];
    u8 rhythm = (r14 >> 5) & 1;
    for (ch = 0; ch < 9; ch++) {
        u8 new_key;
        if (rhythm && ch >= 6) {
            if (ch == 6) new_key = (r14 >> 4) & 1;
            else if (ch == 7) new_key = ((r14 & 0x09) != 0) ? 1 : 0;
            else new_key = ((r14 & 0x06) != 0) ? 1 : 0;
        } else {
            new_key = (ym_reg[0x20 + ch] >> 4) & 1;
        }
        if (new_key && !ym_ch[ch].key_on) {
            ym_key_on(ch);
        } else if (!new_key && ym_ch[ch].key_on) {
            ym_key_off(ch);
        }
    }
}

/* ===== 包络 tick (严格对照 PC _fw_env_tick, 照搬 emu calc_envelope) ===== */
static void ym_env_tick(YM_OP *op, u32 eg_counter, u8 blk) {
    u8 state = op->eg_state;
    u8 rh = op->rate_h;
    u8 rl = op->rate_l;
    u8 shift = op->eg_shift;
    u32 mask = ((u32)1 << shift) - 1;

    if (state == EG_ATTACK) {
        /* attack: eg_out 指数下降 */
        if (op->eg_out > 0 && rh > 0 && (eg_counter & mask & ~3ul) == 0) {
            u8 s = 0;
            u8 idx;
            if (rh == 12) { idx = (eg_counter & 0xc) >> 1; s = 4 - ym_eg_step_tables[rl][idx]; }
            else if (rh == 13) { idx = (eg_counter & 0xc) >> 1; s = 3 - ym_eg_step_tables[rl][idx]; }
            else if (rh == 14) { idx = (eg_counter & 0xc) >> 1; s = 2 - ym_eg_step_tables[rl][idx]; }
            else if (rh == 15) { s = 0; }
            else { idx = (u8)(eg_counter >> shift); s = ym_eg_step_tables[rl][idx & 7] ? 4 : 0; }
            if (s > 0) {
                op->eg_out -= (op->eg_out >> s) + 1;
            }
        }
    } else {
        /* DAMP/DECAY/SUSTAIN/RELEASE: eg_out 线性上升 */
        if (rh > 0 && (eg_counter & mask) == 0) {
            u8 step = 0;
            u8 idx;
            if (rh == 13) { idx = ((eg_counter & 0xc) >> 1) | (eg_counter & 1); step = ym_eg_step_tables[rl][idx]; }
            else if (rh == 14) { idx = (eg_counter & 0xc) >> 1; step = ym_eg_step_tables[rl][idx] + 1; }
            else if (rh == 15) { step = 2; }
            else { idx = (u8)(eg_counter >> shift); step = ym_eg_step_tables[rl][idx & 7]; }
            op->eg_out += step;
            if (op->eg_out > EG_MUTE_VAL) op->eg_out = EG_MUTE_VAL;
        }
    }

    /* 状态转移 */
    if (state == EG_DAMP) {
        if (op->eg_out >= EG_MAX_VAL) {
            u8 ar_rh = op->AR + (ym_calc_rks(blk, op->kr) >> 2);
            if (ar_rh >= 15) {
                op->eg_state = EG_DECAY; op->eg_out = 0;
                ym_commit_rate(op, EG_DECAY, blk);
            } else {
                op->eg_state = EG_ATTACK;
                ym_commit_rate(op, EG_ATTACK, blk);
            }
        }
    } else if (state == EG_ATTACK) {
        if (op->eg_out == 0) {
            op->eg_state = EG_DECAY;
            ym_commit_rate(op, EG_DECAY, blk);
        }
    } else if (state == EG_DECAY) {
        if ((op->eg_out >> 3) >= op->SL) {
            op->eg_state = EG_SUSTAIN;
            ym_commit_rate(op, EG_SUSTAIN, blk);
        }
    }
    /* SUSTAIN/RELEASE: 无自动转移 */
}

/* ===== 公开接口 ===== */
void ym2413_set_clock(u32 clock_hz) {
    /* YM2413 固定 3.579545MHz, 这个函数保留但当前不改变常数 */
    (void)clock_hz;
}

void ym2413_init(void) {
    u8 i, ch;
    /* 解码默认音色 */
    for (i = 0; i < 19; i++) {
        ym_decode_patch(&ym_default_inst[i * 8], &ym_patch[i]);
    }
    /* 初始化通道 */
    for (ch = 0; ch < YM_CHANNELS; ch++) {
        ym_ch[ch].patch = &ym_patch[0];
        ym_ch[ch].key_on = 0;
        ym_ch[ch].sus_flag = 0;
        ym_ch[ch].vol = 0;
        ym_ch_patch[ch] = 0;
        ym_ch[ch].mod.active = 0; ym_ch[ch].car.active = 0;
        ym_ch[ch].mod.pos = 0; ym_ch[ch].car.pos = 0;
        ym_ch[ch].mod.mo1 = 0; ym_ch[ch].mod.mo2 = 0;
        ym_ch[ch].mod.eg_state = EG_RELEASE; ym_ch[ch].car.eg_state = EG_RELEASE;
        ym_ch[ch].mod.eg_out = EG_MUTE_VAL; ym_ch[ch].car.eg_out = EG_MUTE_VAL;
        ym_ch[ch].mod.rate_h = 0; ym_ch[ch].car.rate_h = 0;
        ym_apply_patch(ch);
    }
    for (i = 0; i < 0x40; i++) ym_reg[i] = 0;
    ym_rhythm_mode = 0;
    ym_noise_seed = 1;
    ym_noise_step = 0;
    ym_noise_val = 0;
    ym_eg_counter = 0;
    ym_pm_phase = 0;
    ym_am_phase = 0;
    ym_test_flag = 0;
}

void ym2413_wr(u8 reg, u8 val) {
    u8 ch, i;
    if (reg >= 0x40) return;
    /* mirror registers */
    if ((reg >= 0x19 && reg <= 0x1F) || (reg >= 0x29 && reg <= 0x2F) || (reg >= 0x39 && reg <= 0x3F)) {
        reg -= 9;
    }
    ym_reg[reg] = val;

    switch (reg) {
    /* 用户音色 0x00-0x07 → ym_patch[0] */
    case 0x00: case 0x01: case 0x02: case 0x03:
    case 0x04: case 0x05: case 0x06: case 0x07: {
        u8 dump[8];
        for (i = 0; i < 8; i++) dump[i] = ym_reg[i];
        ym_decode_patch(dump, &ym_patch[0]);
        for (ch = 0; ch < 9; ch++) {
            if (ym_ch_patch[ch] == 0) {
                ym_apply_patch(ch);
                ym_update_tll(ch);
            }
        }
        break;
    }
    case 0x0E: {
        u8 new_rhythm = (val >> 5) & 1;
        if (new_rhythm != ym_rhythm_mode) {
            ym_rhythm_mode = new_rhythm;
            if (new_rhythm) {
                for (ch = 6; ch < 9; ch++) {
                    ym_ch_patch[ch] = 13 + ch;
                    ym_ch[ch].patch = &ym_patch[13 + ch];
                    ym_apply_patch(ch);
                    ym_update_tll(ch);
                }
            } else {
                for (ch = 6; ch < 9; ch++) {
                    u8 inst = (ym_reg[0x30 + ch] >> 4) & 0x0F;
                    ym_ch_patch[ch] = inst;
                    ym_ch[ch].patch = &ym_patch[inst];
                    ym_apply_patch(ch);
                    ym_update_tll(ch);
                }
            }
        }
        ym_update_keys();
        break;
    }
    case 0x0F:
        ym_test_flag = val;
        break;
    /* f-number low 0x10-0x18 */
    case 0x10: case 0x11: case 0x12: case 0x13: case 0x14:
    case 0x15: case 0x16: case 0x17: case 0x18:
        ch = reg - 0x10;
        ym_update_tll(ch);
        break;
    /* f-number high / block / sus / key-on 0x20-0x28 */
    case 0x20: case 0x21: case 0x22: case 0x23: case 0x24:
    case 0x25: case 0x26: case 0x27: case 0x28:
        ch = reg - 0x20;
        ym_ch[ch].sus_flag = (val >> 5) & 1;
        ym_ch[ch].car.sus_flag = (val >> 5) & 1;
        ym_ch[ch].mod.sus_flag = 0;
        ym_update_tll(ch);
        ym_update_keys();
        break;
    /* instrument + volume 0x30-0x38 */
    case 0x30: case 0x31: case 0x32: case 0x33: case 0x34:
    case 0x35: case 0x36: case 0x37: case 0x38:
        ch = reg - 0x30;
        {
            if (ym_rhythm_mode && ch >= 6) {
                /* rhythm mode: 鼓 volume (高4位) */
                u8 drum_vol = (val >> 4) & 0x0F;
                ym_ch[ch].vol = drum_vol << 2;
                ym_update_tll(ch);
            } else {
                u8 inst = (val >> 4) & 0x0F;
                if (inst != ym_ch_patch[ch]) {
                    ym_ch_patch[ch] = inst;
                    ym_ch[ch].patch = &ym_patch[inst];
                    ym_apply_patch(ch);
                }
                /* volume: reg 低4位, vol=0 最大 → 存 (15-reg_vol)<<2 给 tll 用 */
                ym_ch[ch].vol = (15 - (val & 0x0F)) << 2;
                ym_update_tll(ch);
            }
        }
        break;
    }
}

/* ===== 噪声推进 (AY8910 原理: 17-bit LFSR) ===== */
static void ym_update_noise(void) {
    /* 噪声频率较高, 每采样推进多次 */
    ym_noise_step++;
    if (ym_noise_step >= 4) {   /* 控制噪声频率 */
        ym_noise_step = 0;
        if (ym_noise_seed & 1)
            ym_noise_seed ^= 0x24000;   /* AY8910 反馈多项式 */
        ym_noise_seed >>= 1;
    }
    ym_noise_val = ym_noise_seed & 1;
}

/* ===== 单通道标准 FM 渲染 (严格对照 PC render_fm_v3_fw) ===== */
static s16 ym_render_fm(u8 ch) {
    YM_OP *mod = &ym_ch[ch].mod;
    YM_OP *car = &ym_ch[ch].car;
    u8 blk = ym_get_blk(ch);
    u16 fnum = (u16)ym_reg[0x10 + ch] | ((u16)(ym_reg[0x20 + ch] & 1) << 8);
    u8 lfo_am = ym_am_table[(ym_am_phase >> 6) % 210];
    s8 mod_pm = mod->pm ? ym_pm_table[(fnum >> 6) & 7][(ym_pm_phase >> 10) & 7] : 0;
    s8 car_pm = car->pm ? ym_pm_table[(fnum >> 6) & 7][(ym_pm_phase >> 10) & 7] : 0;
    u32 mod_step, car_step;
    u16 midx, cidx, midx64, cidx64;
    u8 mod_eff_eg, car_eff_eg, mod_am, car_am;
    s16 fb, mod_raw, mo1, car_raw, car_val;

    if (fnum == 0) return 0;

    /* pg_phase 增量 = (fnum*2+pm)*ml << blk >> 2 (19-bit 语义, 对照 PC) */
    mod_step = ((u32)((fnum & 0x1ff) * 2 + mod_pm) * mod->ml) << blk >> 2;
    car_step = ((u32)((fnum & 0x1ff) * 2 + car_pm) * car->ml) << blk >> 2;

    /* OP1 (modulator) */
    mod->pos = (mod->pos + mod_step) & 0x7FFFF;  /* 19-bit 回绕 (DP_WIDTH-1) */
    midx = (mod->pos >> 9) & 0x3FF;              /* 10-bit pg_out (DP_BASE_BITS=9) */
    midx64 = (midx * 64) >> 10;                  /* 映射到 64 点 (PG_BITS=10) */
    if (mod->fb > 0) {
        fb = (mod->mo2 + mod->mo1) >> (9 - mod->fb);
        mod_raw = mod->wave[(u8)(midx64 + (fb >> 4)) & 0x3F];
    } else {
        mod_raw = mod->wave[(u8)midx64 & 0x3F];
    }
    mod_am = mod->am ? lfo_am : 0;
    mod_eff_eg = mod->eg_out + mod->tll + mod_am;
    if (mod_eff_eg > EG_MUTE_VAL) mod_eff_eg = EG_MUTE_VAL;
    mo1 = ((s16)mod_raw * (s16)ym_level_gain[mod_eff_eg]) >> 6;  /* >>6: peak 4086 */
    mod->mo2 = mod->mo1;
    mod->mo1 = mo1;

    /* OP2 (carrier) */
    car->pos = (car->pos + car_step) & 0x7FFFF;
    cidx = (car->pos >> 9) & 0x3FF;
    cidx64 = (cidx * 64) >> 10;
    car_raw = car->wave[(u8)(cidx64 + (mo1 >> 4)) & 0x3F];  /* mod→car: >>4 缩放到 64 点 */
    car_am = car->am ? lfo_am : 0;
    car_eff_eg = car->eg_out + car->tll + car_am;
    if (car_eff_eg > EG_MUTE_VAL) car_eff_eg = EG_MUTE_VAL;
    car_val = ((s16)car_raw * (s16)ym_level_gain[car_eff_eg]) >> 7;  /* >>7: peak 2042 */
    return -car_val;
}

/* ===== FM 渲染 (对照 PC render_fm_v3_fw 主循环) ===== */
s16 ym2413_render(void) {
    u8 ch, blk;
    s32 total32 = 0;

    /* 全局计数器 + LFO 相位递增 (所有 channel 共享, 对照 PC) */
    ym_eg_counter++;
    ym_pm_phase++;
    ym_am_phase++;

    /* 噪声推进 (鼓声用) */
    if (ym_rhythm_mode) ym_update_noise();

    for (ch = 0; ch < 9; ch++) {
        YM_OP *mod = &ym_ch[ch].mod;
        YM_OP *car = &ym_ch[ch].car;

        /* 跳过静音通道: release 且 eg_out 到顶 */
        if (!ym_ch[ch].key_on && car->eg_state == EG_RELEASE && car->eg_out >= EG_MUTE_VAL) continue;
        /* DAMP/其他状态 eg_out=EG_MUTE 也跳过 (静音) */
        if (car->eg_out >= EG_MUTE_VAL && car->eg_state != EG_ATTACK && car->eg_state != EG_DECAY) continue;

        if (ym_rhythm_mode && ch >= 6) continue;  /* 鼓声暂未实现 */

        /* 包络 tick (对照 PC: mod 和 car 都 tick) */
        blk = ym_get_blk(ch);
        if (ym_ch[ch].key_on || mod->eg_state < EG_RELEASE) {
            ym_env_tick(mod, ym_eg_counter, blk);
        }
        ym_env_tick(car, ym_eg_counter, blk);

        /* 合成 */
        total32 += ym_render_fm(ch);
    }

    if (total32 > 32767) total32 = 32767;
    if (total32 < -32768) total32 = -32768;
    return (s16)total32;
}
