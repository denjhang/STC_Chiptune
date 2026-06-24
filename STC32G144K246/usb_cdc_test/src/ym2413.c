/* ym2413.c - Yamaha YM2413 (OPLL) FM 合成 (STC32G C251 极简版)
 *
 * 寄存器完整兼容 YM2413, FM 核心参考 12k128 fm.c 极简设计:
 * - 64 点 s8 波形表 + 线性 FM (OP1 相位调制 OP2)
 * - ADSR 查表包络 (round-robin)
 * - 跳过静音通道
 * - 音高精确 (writeReg 算 u32 16.16 step, float 一次)
 *
 * 默认音色 dump → 极简参数映射:
 *   ML(4bit) → mod_mul/car_mul
 *   TL(6bit) → mod_tl (调制深度)
 *   AR(4bit)+DR(4bit) → atk/dec 查表
 *   SL(4bit)+RR(4bit) → sustain_level/release_rate
 *   用户音色从 reg 0x00-0x07 解码, 内置音色从 default_inst
 */
#include "stc.h"
#include "ym2413.h"

/* ===== 64 点波形表 (s8, -31..31) ===== */
/* WS=0: 正弦 (正常 FM) */
static const s8 code ym_sin[64] = {
     0,  3,  6,  9, 12, 15, 17, 20, 22, 24, 26, 28, 29, 30, 31, 31,
    31, 31, 31, 30, 29, 28, 26, 24, 22, 20, 17, 15, 12,  9,  6,  3,
     0, -3, -6, -9,-12,-15,-17,-20,-22,-24,-26,-28,-29,-30,-31,-31,
   -31,-31,-31,-30,-29,-28,-26,-24,-22,-20,-17,-15,-12, -9, -6, -3
};
/* WS=1: 半正弦 (后半周静音, 对齐 emu2413.c:383-387 halfsin=0xfff; 旧版镜像正值是 bug) */
static const s8 code ym_halfsin[64] = {
     0,  3,  6,  9, 12, 15, 17, 20, 22, 24, 26, 28, 29, 30, 31, 31,
    31, 31, 31, 30, 29, 28, 26, 24, 22, 20, 17, 15, 12,  9,  6,  3,
     0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
     0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0
};
/* 噪声表 (64 点假随机 ±31, 用于鼓声 HH/CYM) */
static const s8 code ym_noise[64] = {
     7, -4, 19, -28, 12, 23, -15,  6, -31,  8, -2, 27, -9, 14, -22,  3,
    18, -11, 25, -7, 30, -19,  5, -24, 10, -14, 21, -3, 16, -27,  1, 29,
    -8, 13, -21,  4, 26, -10, 20, -6, 15, -25, 11, -17, 24, -1,  9, -29,
     2, 22, -13, 28, -5, 17, -23,  0, 31, -18,  7, -12, 19, -26, 14, -20
};

/* ===== ADSR 速度查表 (AR/DR/RR 各一张, 对齐 emu2413 速率) ===== */
/* round-robin 每 16 采样 tick 一次, level 0~31 线性.
 * 反推: cnt = emu_全程ms × rate / (步数 × 16), 限 u8 (1~255). */
/* AR 表: attack 31 步, cnt=emu_atk_ms×rate/(31×16) */
static const u8 code ym_ar_tab[16] = {
    0, 116, 58, 29, 14, 7, 4, 2, 1, 1, 1, 1, 1, 1, 1, 1
};
/* DR 表: decay (2026-06-25 校准, 旧表 4~10 偏慢 2.2×) */
static const u8 code ym_dr_tab[16] = {
    0, 255, 255, 255, 75, 38, 19, 9, 5, 2, 1, 1, 1, 1, 1, 1
};
/* RR 表: release/sustain 速率 (2026-06-25 校准) */
static const u8 code ym_rr_tab[16] = {
    0, 255, 255, 255, 76, 38, 19, 9, 5, 2, 1, 1, 1, 1, 1, 1
};
/* SUSTAIN/RELEASE 指数衰减查表 (2026-06-25): 拟合 emu 指数输出衰减
 * sus_hold[level] = sustain 阶段该 level 停留 tick 数 (scale=0.44, tau≈97ms)
 * rel_hold[level] = release 阶段 (sus_hold//10, 整体~100ms)
 * 用法: sus_cnt++; if (sus_cnt >= hold[level]) { sus_cnt=0; level--; } */
static const u8 code ym_sus_hold[32] = {
    1, 134,134,78, 55, 43, 35, 29, 25, 22, 20, 18, 16, 15, 14, 13,
   12, 11, 11, 10, 10,  9,  8,  8,  8,  7,  7,  7,  7,  6,  6,  6
};
static const u8 code ym_rel_hold[32] = {
    1, 13, 13, 7, 5, 4, 3, 2, 2, 2, 2, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1
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

/* ===== 音色参数 (解码后, 极简 FM 用) ===== */
typedef struct {
    u8 mod_ml, car_ml;     /* frequency multiplier */
    u8 mod_tl;             /* modulator total level (调制深度, 0-63) */
    u8 mod_fb;             /* feedback (0-7) */
    u8 mod_ar, mod_dr;     /* attack/decay rate */
    u8 car_ar, car_dr;
    u8 mod_sl, mod_rr;     /* sustain level / release rate */
    u8 car_sl, car_rr;
    u8 mod_eg, car_eg;     /* EG type: 0=sustaining(保持SL), 1=non-sustaining(降到0) */
    u8 mod_ws, car_ws;     /* wave select: 0=sin, 1=half-sin(abssin) */
} YM_VOICE_PATCH;

/* ===== Operator 状态 (极简 FM) ===== */
typedef struct {
    u8 active;
    u8 ml;
    u8 tl;
    u8 atk, decy;
    u8 sul;
    u8 rel;
    u8 fb;
    u8 eg_type;
    u8 sus_flag;
    const s8 code *wave;   /* 波形表指针 (ym_sin 或 ym_halfsin) */
    u16 step;              /* 8.8 定点相位步进 (省 CPU, 参考 12K128 fm.c) */
    u16 pos;               /* 8.8 定点相位累加 */
    s8 fb_val;
    u8 env_state;
    u8 env_cnt;
    u8 env_step;
    u8 level;
    u8 sus_cnt;          /* SUSTAIN/RELEASE 指数查表计数器 (2026-06-25) */
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
static u8 data ym_wait_cnt;
static u8 data ym_test_flag;
static u8 data ym_prev_drum_bits;  /* reg 0x0E 鼓声 bit 上次值 (边沿检测) */

/* ===== 鼓声状态 (单 op, 简化路径) ===== */
/* BD/TOM/HH/CYM/SD 各 1 个单 op */
typedef struct {
    u8 active;
    u8 level;
    u8 env_cnt;
    u8 env_step;
    u8 vol;              /* 音量倍数 (2=标准, 4=2倍) */
    const s8 code *wave;
    u16 step;             /* 8.8 定点 */
    u16 pos;              /* 8.8 定点 */
} YM_DRUM;

static YM_DRUM xdata ym_drum[5];  /* 0=BD 1=TOM 2=HH 3=CYM 4=SD */
static void ym_drum_trigger(u8 idx);  /* 前向声明 */

/* base step 常数: step_q16 = fnum × (1<<blk) × C
 * YM2413 内部 PG_WIDTH=1024 (10-bit 相位), clock/72 采样率.
 * 我们用 64 点表 (s8), 但 phase accumulator 仍按 1024 精度,
 * 查表时 >> (10-6) = >> 4 取高 6 位索引.
 * 所以 step = fnum × 2^blk × clock × 65536 / (72 × 262144 × 22050)
 * (PG_WIDTH=1024 对应 2^10=1024, 但 YM2413 phase 是 19-bit,
 *  实际表推进 = phase >> 9. 我们用 16.16 定点存 phase, 表索引 = phase >> (16+4))
 *
 * 简化验证:
 *   freq_hz = fnum × 2^blk × clock / (72 × 2^18)
 *   表推进/采样 = freq_hz × 1024 / 22050  (1024 点表)
 *   但我们用 64 点表, 所以 = freq_hz × 64 / 22050
 *   存 16.16: step_q16 = freq_hz × 64 / 22050 × 65536
 *            = fnum × 2^blk × 3579545 / (72 × 262144) × 64 / 22050 × 65536
 */
/* YM_STEP_CONST 在 ym_calc_step 处定义 (8.8 定点) */

/* ===== 解码音色 dump ===== */
static void ym_decode_patch(const u8 *dump, YM_VOICE_PATCH *p) {
    p->mod_ml = dump[0] & 0x0F;
    p->mod_eg = (dump[0] >> 5) & 1;   /* bit5 = EG type */
    p->car_ml = dump[1] & 0x0F;
    p->car_eg = (dump[1] >> 5) & 1;
    p->mod_tl = dump[2] & 0x3F;
    p->mod_fb = dump[3] & 0x07;
    p->mod_ws = (dump[3] >> 3) & 1;   /* bit3 */
    p->car_ws = (dump[3] >> 4) & 1;   /* bit4 */
    p->mod_ar = (dump[4] >> 4) & 0x0F;
    p->mod_dr = dump[4] & 0x0F;
    p->car_ar = (dump[5] >> 4) & 0x0F;
    p->car_dr = dump[5] & 0x0F;
    p->mod_sl = (dump[6] >> 4) & 0x0F;
    p->mod_rr = dump[6] & 0x0F;
    p->car_sl = (dump[7] >> 4) & 0x0F;
    p->car_rr = dump[7] & 0x0F;
}

/* ===== 应用音色到通道 ===== */
static void ym_apply_patch(u8 ch) {
    YM_VOICE_PATCH *p = ym_ch[ch].patch;
    YM_OP *mod = &ym_ch[ch].mod;
    YM_OP *car = &ym_ch[ch].car;
    mod->ml = ym_ml_table[p->mod_ml];
    car->ml = ym_ml_table[p->car_ml];
    /* mod_tl: 0=最深调制, 63=无调制. 转 0-31: 31 - tl/2 */
    mod->tl = 31 - (p->mod_tl >> 1);
    if (mod->tl > 31) mod->tl = 31;
    mod->fb = p->mod_fb;
    mod->eg_type = p->mod_eg;
    mod->wave = p->mod_ws ? ym_halfsin : ym_sin;
    mod->atk  = ym_ar_tab[p->mod_ar];
    mod->decy = ym_dr_tab[p->mod_dr];
    mod->sul  = (p->mod_sl >= 15) ? 0 : (31 - p->mod_sl * 2);
    mod->rel  = ym_rr_tab[p->mod_rr];
    car->fb = 0;
    car->eg_type = p->car_eg;
    car->wave = p->car_ws ? ym_halfsin : ym_sin;
    car->atk  = ym_ar_tab[p->car_ar];
    car->decy = ym_dr_tab[p->car_dr];
    car->sul  = (p->car_sl >= 15) ? 0 : (31 - p->car_sl * 2);
    car->rel  = ym_rr_tab[p->car_rr];
}

/* ===== 算 step (8.8 定点, 参考 12K128 fm.c) ===== */
/* 64 点表, idx = pos >> 8 & 0x3F, 一个周期 = 64×256 = 16384 */
/* step = freq × 64 × 256 / 22050 */
#define YM_STEP_CONST  (3579545.0f * 64.0f * 256.0f / (72.0f * 262144.0f * 22050.0f))
static u16 ym_calc_step(u16 fnum, u8 blk, u8 ml) {
    float base = (float)fnum * (float)(1 << blk) * YM_STEP_CONST;
    u16 step = (u16)(base * (float)ml / 2.0f);
    return step;
}

/* ===== 重新算通道 step (fnum/blk/ml 改变时) ===== */
static void ym_update_step(u8 ch) {
    u16 fnum = (u16)ym_reg[0x10 + ch] | ((u16)(ym_reg[0x20 + ch] & 1) << 8);
    u8 blk = (ym_reg[0x20 + ch] >> 1) & 7;
    /* 实测音高整体高一个八度, blk 减 1 修正 (频率 ÷2 = 降一个八度) */
    if (blk > 0) blk--;
    ym_ch[ch].mod.step = ym_calc_step(fnum, blk, ym_ch[ch].mod.ml);
    ym_ch[ch].car.step = ym_calc_step(fnum, blk, ym_ch[ch].car.ml);
}

/* ===== key on/off (行为对齐 YM2413) ===== */
static void ym_key_on(u8 ch) {
    YM_OP *mod = &ym_ch[ch].mod;
    YM_OP *car = &ym_ch[ch].car;
    ym_ch[ch].key_on = 1;
    mod->pos = 0; car->pos = 0;
    mod->fb_val = 0;
    mod->sus_cnt = 0; car->sus_cnt = 0;   /* 重置指数查表计数器 */
    /* AR 值 (查表后) 含义: 0=不启动, 1~2=瞬间到顶(AR>=7), 3~255=线性 attack */
    /* env_cnt=0: 立即开始计時 */
    mod->level = 0; car->level = 0;
    if (mod->atk == 0) {
        mod->env_state = 0; mod->level = 0;
    } else if (mod->atk <= 2) {
        mod->level = 31; mod->env_state = 2; mod->env_step = mod->decy;
    } else {
        mod->env_state = 1; mod->env_cnt = 0; mod->env_step = mod->atk;
    }
    if (car->atk == 0) {
        car->env_state = 0; car->level = 0;
    } else if (car->atk <= 2) {
        car->level = 31; car->env_state = 2; car->env_step = car->decy;
    } else {
        car->env_state = 1; car->env_cnt = 0; car->env_step = car->atk;
    }
}

static void ym_key_off(u8 ch) {
    YM_OP *mod = &ym_ch[ch].mod;
    YM_OP *car = &ym_ch[ch].car;
    ym_ch[ch].key_on = 0;
    /* → release: env_step=1 让 rel_hold 指数查表接管 (2026-06-25) */
    mod->env_state = 4; mod->env_step = 1; mod->sus_cnt = 0;
    car->env_state = 4; car->env_step = 1; car->sus_cnt = 0;
}

/* ===== 更新 key 状态 (reg 0x20-0x28 或 0x0E 改变时) ===== */
static void ym_update_keys(void) {
    u8 ch;
    u8 r14 = ym_reg[0x0E];
    u8 rhythm = (r14 >> 5) & 1;
    for (ch = 0; ch < 9; ch++) {
        u8 new_key;
        if (rhythm && ch >= 6) {
            /* rhythm mode: ch6/7/8 由 reg 0x0E 控制 */
            if (ch == 6) new_key = (r14 >> 4) & 1;       /* BD */
            else if (ch == 7) new_key = ((r14 & 0x09) != 0) ? 1 : 0; /* HH(1) | SD(8) */
            else new_key = ((r14 & 0x06) != 0) ? 1 : 0;  /* TOM(4) | CYM(2) */
        } else {
            new_key = (ym_reg[0x20 + ch] >> 4) & 1;
        }
        if (new_key && !ym_ch[ch].key_on) {
            ym_key_on(ch);
        } else if (!new_key && ym_ch[ch].key_on) {
            ym_key_off(ch);
        }
    }
    /* rhythm mode: reg 0x0E 鼓声 bit 边沿触发 (0→1 时触发一次) */
    if (rhythm) {
        u8 drum_bits = r14 & 0x1F;  /* BD(bit4) SD(bit3) TOM(bit2) CYM(bit1) HH(bit0) */
        u8 new_bits = drum_bits & ~ym_prev_drum_bits;  /* 只触发 0→1 的 bit */
        ym_prev_drum_bits = drum_bits;
        if (new_bits & 0x10) ym_drum_trigger(0);  /* BD */
        if (new_bits & 0x08) ym_drum_trigger(4);  /* SD */
        if (new_bits & 0x04) ym_drum_trigger(1);  /* TOM */
        if (new_bits & 0x01) ym_drum_trigger(2);  /* HH */
        if (new_bits & 0x02) ym_drum_trigger(3);  /* CYM */
    }
}

/* ===== 包络 tick (行为对齐 YM2413) ===== */
static void ym_env_tick(YM_OP *op) {
    u8 cnt = op->env_cnt;
    u8 step = op->env_step;
    if (step == 0) return;   /* step=0: 永远保持 (sustain EG=0) */
    if (cnt < step) { op->env_cnt = cnt + 1; return; }
    op->env_cnt = 0;
    switch (op->env_state) {
    case 1: /* attack: level 0→31 */
        if (op->level < 31) op->level++;
        if (op->level >= 31) {
            op->env_state = 2;   /* → decay */
            op->env_step = op->decy;
        }
        break;
    case 2: /* decay: level 31→sul */
        if (op->level > op->sul) op->level--;
        else {
            op->env_state = 3;   /* → sustain */
            op->sus_cnt = 0;
            /* EG=1 sustaining: step=0 保持; EG=0 non-sus: step=1 让 sus_hold 接管 */
            op->env_step = op->eg_type ? 0 : 1;
        }
        break;
    case 3: /* sustain: EG=0 用 sus_hold 指数查表衰减 (EG=1 step=0 不进这里) */
        if (op->level > 0) {
            op->sus_cnt++;
            if (op->sus_cnt >= ym_sus_hold[op->level]) {
                op->sus_cnt = 0;
                op->level--;
                if (op->level == 0) op->env_state = 0;
            }
        }
        break;
    case 4: /* release: 用 rel_hold 指数查表衰减 (env_step=1 让计数器接管) */
        if (op->level > 0) {
            op->sus_cnt++;
            if (op->sus_cnt >= ym_rel_hold[op->level]) {
                op->sus_cnt = 0;
                op->level--;
                if (op->level == 0) op->env_state = 0;
            }
        }
        break;
    default: break;
    }
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
        ym_ch[ch].patch = &ym_patch[0];  /* 默认音色 0 */
        ym_ch[ch].key_on = 0;
        ym_ch[ch].sus_flag = 0;
        ym_ch[ch].vol = 60;
        ym_ch_patch[ch] = 0;
        ym_ch[ch].mod.active = 0; ym_ch[ch].car.active = 0;
        ym_ch[ch].mod.step = 0; ym_ch[ch].car.step = 0;
        ym_ch[ch].mod.pos = 0; ym_ch[ch].car.pos = 0;
        ym_ch[ch].mod.env_state = 0; ym_ch[ch].car.env_state = 0;
        ym_ch[ch].mod.level = 0; ym_ch[ch].car.level = 0;
        ym_apply_patch(ch);
    }
    for (i = 0; i < 0x40; i++) ym_reg[i] = 0;
    ym_rhythm_mode = 0;
    ym_noise_seed = 1;
    ym_noise_step = 0;
    ym_noise_val = 0;
    ym_wait_cnt = 0;
    ym_test_flag = 0;
    /* 鼓声参数初始化 (PC drum_fw_sim 试听确定) */
    /* BD=0: sin 100Hz, decay 快; TOM=1: sin 214Hz; HH=2: noise 755Hz; CYM=3: noise 755Hz 慢 */
    /* 鼓声 oneshot: 每采样 tick, env_step = 采样数/31步 */
    /* BD ~100ms TOM ~80ms HH ~29ms CYM ~150ms SD ~60ms */
    /* 鼓声 oneshot, step 按 22050Hz ISR 算: step = freq×64×65536/22050 */
    ym_drum[0].wave = ym_sin;     ym_drum[0].step = 0x004A;  ym_drum[0].env_step = 14;  ym_drum[0].vol = 16; /* BD */
    ym_drum[1].wave = ym_sin;     ym_drum[1].step = 0x009F;  ym_drum[1].env_step = 14;  ym_drum[1].vol = 8; /* TOM */
    ym_drum[2].wave = ym_noise;   ym_drum[2].step = 0x00F8;  ym_drum[2].env_step = 46;  ym_drum[2].vol = 2; /* HH */
    ym_drum[3].wave = ym_noise;   ym_drum[3].step = 0x00F8;  ym_drum[3].env_step = 255; ym_drum[3].vol = 2; /* CYM */
    ym_drum[4].wave = ym_noise;   ym_drum[4].step = 0x0012;  ym_drum[4].env_step = 28;  ym_drum[4].vol = 8; /* SD noise 25Hz */
    for (i = 0; i < 5; i++) { ym_drum[i].active = 0; ym_drum[i].level = 0; ym_drum[i].pos = 0; }
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
        /* 重组 dump 格式解码 */
        u8 dump[8];
        for (i = 0; i < 8; i++) dump[i] = ym_reg[i];
        ym_decode_patch(dump, &ym_patch[0]);
        /* 更新所有用 patch 0 的通道 */
        for (ch = 0; ch < 9; ch++) {
            if (ym_ch_patch[ch] == 0) {
                ym_apply_patch(ch);
                ym_update_step(ch);
            }
        }
        break;
    }
    case 0x0E: {
        u8 new_rhythm = (val >> 5) & 1;
        if (new_rhythm != ym_rhythm_mode) {
            ym_rhythm_mode = new_rhythm;
            if (new_rhythm) {
                /* 进 rhythm mode: ch6/7/8 用鼓音色 16/17/18 */
                for (ch = 6; ch < 9; ch++) {
                    ym_ch_patch[ch] = 13 + ch;   /* ch6→16(BD), ch7→17(HH/SD), ch8→18(TOM/CYM) */
                    ym_ch[ch].patch = &ym_patch[13 + ch];
                    ym_apply_patch(ch);
                    ym_update_step(ch);
                }
            } else {
                /* 退 rhythm mode: ch6/7/8 恢复用户音色 */
                for (ch = 6; ch < 9; ch++) {
                    u8 inst = (ym_reg[0x30 + ch] >> 4) & 0x0F;
                    ym_ch_patch[ch] = inst;
                    ym_ch[ch].patch = &ym_patch[inst];
                    ym_apply_patch(ch);
                    ym_update_step(ch);
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
        ym_update_step(ch);
        break;
    /* f-number high / block / sus / key-on 0x20-0x28 */
    case 0x20: case 0x21: case 0x22: case 0x23: case 0x24:
    case 0x25: case 0x26: case 0x27: case 0x28:
        ch = reg - 0x20;
        ym_ch[ch].sus_flag = (val >> 5) & 1;
        /* sus_flag 只影响 carrier (对齐 emu2413 set_sus_flag line 672:
         * modulator 的 sus_flag 永远不设, 因 type&1==0) */
        ym_ch[ch].car.sus_flag = (val >> 5) & 1;
        ym_ch[ch].mod.sus_flag = 0;
        ym_update_step(ch);
        ym_update_keys();
        break;
    /* instrument + volume 0x30-0x38 */
    case 0x30: case 0x31: case 0x32: case 0x33: case 0x34:
    case 0x35: case 0x36: case 0x37: case 0x38:
        ch = reg - 0x30;
        {
            if (ym_rhythm_mode && ch >= 6) {
                /* rhythm mode: ch6/7/8 的高4位是鼓 volume (不是 instrument)
                 * ch6=BD vol, ch7=SD vol(高4)/HH vol(低4), ch8=TOM vol(高4)/CYM vol(低4)
                 * 简化: 用高4位作为 carrier volume */
                u8 drum_vol = (val >> 4) & 0x0F;
                ym_ch[ch].car.tl = drum_vol << 1;
                if (ym_ch[ch].car.tl > 31) ym_ch[ch].car.tl = 31;
            } else {
                u8 inst = (val >> 4) & 0x0F;
                if (inst != ym_ch_patch[ch]) {
                    ym_ch_patch[ch] = inst;
                    ym_ch[ch].patch = &ym_patch[inst];
                    ym_apply_patch(ch);
                    ym_update_step(ch);
                }
                /* volume: reg 低4位, YM2413 vol=0 最大 → tl 大 (输出大) */
                ym_ch[ch].vol = (15 - (val & 0x0F)) << 2;
                ym_ch[ch].car.tl = ym_ch[ch].vol >> 1;
                if (ym_ch[ch].car.tl > 31) ym_ch[ch].car.tl = 31;
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

/* ===== 鼓声简化渲染 (单 op: 查表×level, 无 FM 调制) ===== */
/* BD=0 TOM=1 HH=2 CYM=3 SD=4 oneshot 单 op */
static void ym_drum_trigger(u8 idx) {
    YM_DRUM *d = &ym_drum[idx];
    d->active = 1;
    d->level = 31;
    d->env_cnt = 0;
}

/* SD 真 2-op 已废弃: 真 2-op (ch6 ym_render_fm) 听感最好但卡 ISR */
/* 简化 2-op 听感不如真 2-op, 暂用单 op noise */
/* 未来优化 ISR 后可恢复真 2-op SD */

static s16 ym_render_drum(u8 idx) {
    YM_DRUM *d = &ym_drum[idx];
    s8 wave_val;
    s16 out;

    if (!d->active) return 0;

    /* 包络: 每采样 tick (不走 round-robin, env_step 直接 = 采样数/步) */
    if (d->env_step > 0) {
        if (d->env_cnt < d->env_step) d->env_cnt++;
        else {
            d->env_cnt = 0;
            if (d->level > 0) d->level--;
            else { d->active = 0; return 0; }
        }
    }

    /* 单 op: 查表 × level × vol */
    d->pos += d->step;
    wave_val = d->wave[(u8)(d->pos >> 8) & 0x3F];
    out = ((s16)wave_val * (s16)((d->level + 1) * d->vol)) >> 6;
    if (out > 127) out = 127;
    if (out < -128) out = -128;
    return out;
}

/* ===== 单通道标准 FM 渲染 (OP1→OP2) ===== */
static s16 ym_render_fm(u8 ch) {
    YM_OP *mod = &ym_ch[ch].mod;
    YM_OP *car = &ym_ch[ch].car;
    u8 idx;
    s8 wave_val, ch_out;

    if (!mod->step) return 0;

    /* OP1 (modulator) */
    if (ym_wait_cnt == (ch & 0x0F)) ym_env_tick(mod);
    mod->pos += mod->step;
    if (mod->level == 0) {
        ch_out = 0;
        mod->fb_val = 0;
    } else {
        idx = (u8)(mod->pos >> 8) & 0x3F;
        idx += (u8)mod->fb_val;
        wave_val = mod->wave[idx & 0x3F];
        ch_out = (s8)(((s16)wave_val * (s16)(mod->level + 1) * (s16)(mod->tl + 1)) >> 10);
        /* FB+4 移位压低反馈 (对齐 emu 反馈强度, 2026-06-25) */
        if (mod->fb > 0) mod->fb_val = (s8)((s8)ch_out >> (mod->fb + 4));
        else mod->fb_val = 0;
    }

    /* OP2 (carrier) */
    if (ym_wait_cnt == (ch & 0x0F)) ym_env_tick(car);
    car->pos += car->step;
    if (car->level == 0) {
        return 0;
    }
    idx = (u8)(car->pos >> 8) & 0x3F;
    idx += (u8)ch_out;
    wave_val = car->wave[idx & 0x3F];
    ch_out = (s8)(((s16)wave_val * (s16)(car->level + 1) * (s16)(car->tl + 1)) >> 10);
    return ch_out;
}

/* ===== FM 渲染 (6旋律 + 鼓声简化) ===== */
s16 ym2413_render(void) {
    u8 ch;
    s16 total = 0;

    ym_wait_cnt++;
    ym_wait_cnt &= 0x0F;

    /* 只渲染 ch0-5 旋律 (6通道) */
    for (ch = 0; ch < 6; ch++) {
        /* 跳过无声通道 */
        if (ym_ch[ch].mod.step == 0) continue;
        if (!ym_ch[ch].key_on && ym_ch[ch].car.env_state == 0) continue;
        /* SD (ch6) 衰减完后自动 key_off */
        if (ch == 6 && ym_ch[ch].car.level == 0 && ym_ch[ch].mod.level == 0) {
            ym_ch[ch].key_on = 0;
            ym_ch[ch].car.env_state = 0;
            ym_ch[ch].mod.env_state = 0;
            continue;
        }
        if (ym_ch[ch].car.env_state == 4 && ym_ch[ch].car.level == 0) {
            ym_ch[ch].car.env_state = 0;
            continue;
        }
        total += ym_render_fm(ch);
    }

    /* 鼓声 (单 op 简化路径, 只有 active 时才有开销) */
    if (ym_rhythm_mode) {
        total += ym_render_drum(0);  /* BD */
        total += ym_render_drum(1);  /* TOM */
        total += ym_render_drum(2);  /* HH */
        total += ym_render_drum(3);  /* CYM */
        total += ym_render_drum(4);  /* SD */
    }

    total <<= 1;
    if (total > 32767) total = 32767;
    if (total < -32768) total = -32768;
    return total;
}
