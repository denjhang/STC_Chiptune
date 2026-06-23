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
/* WS=1: 半正弦 (abssin, 负半周取绝对值, 产生八度叠加感) */
static const s8 code ym_halfsin[64] = {
     0,  3,  6,  9, 12, 15, 17, 20, 22, 24, 26, 28, 29, 30, 31, 31,
    31, 31, 31, 30, 29, 28, 26, 24, 22, 20, 17, 15, 12,  9,  6,  3,
     0,  3,  6,  9, 12, 15, 17, 20, 22, 24, 26, 28, 29, 30, 31, 31,
    31, 31, 31, 30, 29, 28, 26, 24, 22, 20, 17, 15, 12,  9,  6,  3
};
/* WS=2: 噪声 (64 点假随机 ±31, 代替 LFSR, 用于鼓声 HH/SD/CYM/TOM) */
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
/* DR 表: decay 31 步 (近似最大) */
static const u8 code ym_dr_tab[16] = {
    0, 255, 255, 175, 88, 44, 22, 11, 6, 3, 1, 1, 1, 1, 1, 1
};
/* RR 表: release 16 步 (sul≈15 近似), EG=1 时用 */
static const u8 code ym_rr_tab[16] = {
    0, 255, 255, 255, 170, 85, 42, 21, 11, 5, 3, 1, 1, 1, 1, 1
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
    u32 step;
    u32 pos;
    s8 fb_val;
    u8 env_state;
    u8 env_cnt;
    u8 env_step;
    u8 level;
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
#define YM_DRUM_CHANNELS 5
#define YM_TOTAL_CHANNELS (YM_CHANNELS + YM_DRUM_CHANNELS)
static YM_CHANNEL xdata ym_ch[YM_TOTAL_CHANNELS];
static YM_VOICE_PATCH xdata ym_patch[19];   /* 0=用户, 1-15=内置, 16-18=rhythm */
static u8 xdata ym_reg[0x40];
static u8 xdata ym_ch_patch[YM_TOTAL_CHANNELS];
static u8 xdata ym_rhythm_mode;
/* 噪声发生器 (AY8910 原理: 17-bit LFSR, 用于鼓声 HH/SD/CYM) */
static u32 data ym_noise_seed;
static u8 data ym_noise_step;
static u8 data ym_noise_val;
static u8 data ym_wait_cnt;
static u8 data ym_test_flag;

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
#define YM_STEP_CONST  (3579545.0f * 64.0f * 65536.0f / (72.0f * 262144.0f * 22050.0f))

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
    mod->wave = (p->mod_ws >= 2) ? ym_noise : (p->mod_ws ? ym_halfsin : ym_sin);
    mod->atk  = ym_ar_tab[p->mod_ar];
    mod->decy = ym_dr_tab[p->mod_dr];
    mod->sul  = (p->mod_sl >= 15) ? 0 : (31 - p->mod_sl * 2);
    mod->rel  = ym_rr_tab[p->mod_rr];
    car->fb = 0;
    car->eg_type = p->car_eg;
    car->wave = (p->car_ws >= 2) ? ym_noise : (p->car_ws ? ym_halfsin : ym_sin);
    car->atk  = ym_ar_tab[p->car_ar];
    car->decy = ym_dr_tab[p->car_dr];
    car->sul  = (p->car_sl >= 15) ? 0 : (31 - p->car_sl * 2);
    car->rel  = ym_rr_tab[p->car_rr];
}

/* ===== 鼓声专用参数设置 (rhythm mode 进入时调用) ===== */
/* ch9-13 = 5 个独立鼓声通道 (BD/SD/TOM/HH/CYM), 各自独立 2-op */
/* BD = ch9:  mod=halfsin+FB, car=sin (标准 FM), 100Hz */
/* SD = ch10: mod=noise(WS=2), car=sin, sine慢包络+noise快, FB=2 */
/* TOM= ch11: mod=sin, car=sin (只用 car 输出), 214Hz ml=5 */
/* HH = ch12: mod=noise(WS=2), car=unused, 755Hz */
/* CYM= ch13: mod=noise(WS=2), car=unused, 755Hz */
#define DRUM_BD   9
#define DRUM_SD   10
#define DRUM_TOM  11
#define DRUM_HH   12
#define DRUM_CYM  13

static void ym_setup_drums(void) {
    u8 ch;
    /* 噪声步进: 755Hz (16.16 定点) = 755 × 64 × 65536 / 49716 ≈ 63608 */
    u32 noise_step = 63608;

    /* 初始化 ch9-13: 都用 patch16/17/18 的 ADSR, 但 WS/频率特殊 */
    for (ch = DRUM_BD; ch <= DRUM_CYM; ch++) {
        ym_ch[ch].key_on = 0;
        ym_ch[ch].mod.pos = 0; ym_ch[ch].car.pos = 0;
        ym_ch[ch].mod.fb_val = 0;
        ym_ch[ch].mod.env_state = 0; ym_ch[ch].car.env_state = 0;
        ym_ch[ch].mod.level = 0; ym_ch[ch].car.level = 0;
    }

    /* BD (ch9): patch16, 标准 2-op FM */
    ym_ch[DRUM_BD].patch = &ym_patch[16];
    ym_apply_patch(DRUM_BD);

    /* SD (ch10): patch17, mod=noise, car=sin, FB=2 */
    ym_ch[DRUM_SD].patch = &ym_patch[17];
    ym_apply_patch(DRUM_SD);
    ym_ch[DRUM_SD].mod.wave = ym_noise;
    ym_ch[DRUM_SD].mod.fb = 2;
    ym_ch[DRUM_SD].mod.step = noise_step;  /* noise 755Hz */

    /* TOM (ch11): patch18 mod, sin 214Hz ml=5 */
    ym_ch[DRUM_TOM].patch = &ym_patch[18];
    ym_apply_patch(DRUM_TOM);
    /* TOM 只用 mod 输出 (car 不输出) */

    /* HH (ch12): noise 755Hz */
    ym_ch[DRUM_HH].patch = &ym_patch[17];
    ym_apply_patch(DRUM_HH);
    ym_ch[DRUM_HH].mod.wave = ym_noise;
    ym_ch[DRUM_HH].mod.step = noise_step;

    /* CYM (ch13): noise 755Hz */
    ym_ch[DRUM_CYM].patch = &ym_patch[18];
    ym_apply_patch(DRUM_CYM);
    ym_ch[DRUM_CYM].mod.wave = ym_noise;
    ym_ch[DRUM_CYM].mod.step = noise_step;
}

/* ===== 算 step (16.16 定点) ===== */
static u32 ym_calc_step(u16 fnum, u8 blk, u8 ml) {
    /* step = fnum × (1<<blk) × YM_STEP_CONST × ml / 2
     * ml 是查表后的值 (ym_ml_table), 实际 = ml/2 */
    float base = (float)fnum * (float)(1 << blk) * YM_STEP_CONST;
    u32 step = (u32)(base * (float)ml / 2.0f);
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
    mod->env_state = 4; car->env_state = 4;
    /* Release 速率 (行为对齐 YM2413):
     *   sus_flag=1 → 固定速率 5 (ym_rr_tab[5]) */
    if (mod->sus_flag) mod->env_step = ym_rr_tab[5]; else mod->env_step = mod->rel;
    if (car->sus_flag) car->env_step = ym_rr_tab[5]; else car->env_step = car->rel;
}

/* ===== 更新 key 状态 (reg 0x20-0x28 或 0x0E 改变时) ===== */
static void ym_update_keys(void) {
    u8 ch;
    u8 r14 = ym_reg[0x0E];
    u8 rhythm = (r14 >> 5) & 1;
    /* ch0-8: 旋律 (rhythm mode 时 ch6-8 不再用) */
    for (ch = 0; ch < 9; ch++) {
        u8 new_key;
        if (rhythm && ch >= 6) {
            new_key = 0;  /* rhythm mode: ch6-8 旋律静音 */
        } else {
            new_key = (ym_reg[0x20 + ch] >> 4) & 1;
        }
        if (new_key && !ym_ch[ch].key_on) {
            ym_key_on(ch);
        } else if (!new_key && ym_ch[ch].key_on) {
            ym_key_off(ch);
        }
    }
    /* rhythm mode: ch9-13 鼓声由 reg 0x0E 各 bit 触发 */
    if (rhythm) {
        u8 drum_key[5];
        drum_key[0] = (r14 >> 4) & 1;           /* BD  = bit4 */
        drum_key[1] = (r14 >> 3) & 1;           /* SD  = bit3 */
        drum_key[2] = (r14 >> 2) & 1;           /* TOM = bit2 */
        drum_key[3] = (r14 >> 1) & 1;           /* CYM = bit1 */
        drum_key[4] = r14 & 1;                   /* HH  = bit0 */
        for (ch = 0; ch < 5; ch++) {
            u8 dch = DRUM_BD + ch;
            if (drum_key[ch] && !ym_ch[dch].key_on) {
                ym_key_on(dch);
            }
        }
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
            /* Sustain 速率 (对齐 emu2413 get_parameter_rate):
             *   EG=1 (sustaining) → 保持 SL, step=0
             *   EG=0 (non-sustaining) → 继续降, step=RR */
            op->env_step = op->eg_type ? 0 : op->rel;
        }
        break;
    case 3: /* sustain: EG=1 step=0 不进这里(保持); EG=0 step=rel 继续降 */
        if (op->level > 0) op->level--;
        break;
    case 4: /* release: level→0 */
        if (op->level > 0) op->level--;
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
    for (ch = 0; ch < YM_TOTAL_CHANNELS; ch++) {
        ym_ch[ch].patch = &ym_patch[0];
        ym_ch[ch].key_on = 0;
        ym_ch[ch].sus_flag = 0;
        ym_ch[ch].vol = 0;
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
                /* 进 rhythm mode: 初始化 ch9-13 鼓声通道 */
                ym_setup_drums();
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

/* ===== 单通道标准 FM 渲染 (OP1→OP2) ===== */
static s16 ym_render_fm(u8 ch) {
    YM_OP *mod = &ym_ch[ch].mod;
    YM_OP *car = &ym_ch[ch].car;
    u8 idx;
    s8 wave_val, ch_out;

    if (!mod->step) return 0;

    /* OP1 (modulator) */
    mod->pos += mod->step;
    idx = (u8)(mod->pos >> 16) & 0x3F;
    idx += (u8)mod->fb_val;
    wave_val = mod->wave[idx & 0x3F];
    if (ym_wait_cnt == (ch & 0x0F)) ym_env_tick(mod);
    ch_out = (s8)(((s16)wave_val * (s16)(mod->level + 1) * (s16)(mod->tl + 1)) >> 10);
    if (mod->fb > 0) mod->fb_val = (s8)((s8)ch_out >> mod->fb);
    else mod->fb_val = 0;

    /* OP2 (carrier) */
    car->pos += car->step;
    idx = (u8)(car->pos >> 16) & 0x3F;
    idx += (u8)ch_out;
    wave_val = car->wave[idx & 0x3F];
    if (ym_wait_cnt == (ch & 0x0F)) ym_env_tick(car);
    ch_out = (s8)(((s16)wave_val * (s16)(car->level + 1) * (s16)(car->tl + 1)) >> 10);
    return ch_out;
}

/* ===== FM 渲染 (旋律 + 鼓声) ===== */
s16 ym2413_render(void) {
    u8 ch;
    s16 total = 0;

    ym_wait_cnt++;
    ym_wait_cnt &= 0x0F;

    for (ch = 0; ch < YM_TOTAL_CHANNELS; ch++) {
        /* 跳过静音通道 */
        if (!ym_ch[ch].key_on && ym_ch[ch].car.env_state == 0) continue;
        if (ym_ch[ch].car.env_state == 4 && ym_ch[ch].car.level == 0) {
            ym_ch[ch].car.env_state = 0;
            continue;
        }
        total += ym_render_fm(ch);
    }

    total <<= 1;
    if (total > 32767) total = 32767;
    if (total < -32768) total = -32768;
    return total;
}
