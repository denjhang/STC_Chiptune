/* fm.c - 轻量 2-Operator FM 合成 (STC32G C251)
 * 参考: ArduinoUnoTinyFmKeyboard (ATmega328P, 20MHz, 24kHz PWM)
 * 适配: STC32G 35MHz, 17640Hz ISR, 8-bit PWM DAC
 *
 * 算法:
 *   每个 voice 有 op1 + op2:
 *     op1: sin_pos += sin_step; index = (sin_pos>>8 + fb_val) & 0x3F
 *          out = wave_tbl[index]; out = out * level * tl / 31 / 31
 *          fb_val = (out * signed_fb) >> 3   (反馈)
 *     op2: sin_pos += sin_step; index = (sin_pos>>8 + op1_out) & 0x3F
 *          out = wave_tbl[index]; out = out * level * tl / 31 / 31
 *     voice_out = op2_out
 *   总输出 = sum(voice_out) - 3 voices
 *
 * 步进计算: step = freq * 64 * 256 / 17640 (8.8 fixed point)
 */

#include "STC32G.H"
#include "fm.h"

/* ========== 波形表 (code 段, 64 entries, range -31~31) ========== */
static const s8 code fm_wave_sin[64] = {
     0,  3,  6,  9, 12, 15, 17, 20, 22, 24, 26, 28, 29, 30, 31, 31,
    31, 31, 31, 30, 29, 28, 26, 24, 22, 20, 17, 15, 12,  9,  6,  3,
     0, -3, -6, -9,-12,-15,-17,-20,-22,-24,-26,-28,-29,-30,-31,-31,
   -31,-31,-31,-30,-29,-28,-26,-24,-22,-20,-17,-15,-12, -9, -6, -3
};

static const s8 code fm_wave_tri[64] = {
     0, 1, 3, 5, 7, 9,11,13,15,17,19,21,23,25,27,29,
    31,30,28,26,24,22,20,18,16,14,12,10, 8, 6, 4, 2,
     0,-2,-4,-6,-8,-10,-12,-14,-16,-18,-20,-22,-24,-26,-28,-30,
   -31,-30,-28,-26,-24,-22,-20,-18,-16,-14,-12,-10, -8, -6, -4, -2
};

static const s8 code fm_wave_saw[64] = {
     0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9,10,11,12,13,14,
    15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,
   -31,-30,-29,-28,-27,-26,-25,-24,-23,-22,-21,-20,-19,-18,-17,-16,
   -15,-14,-13,-12,-11,-10, -9, -8, -7, -6, -5, -4, -3, -2, -1,  0
};

static const s8 code fm_wave_rect[64] = {
   -21,-21,-21,-21,-21,-21,-21,-21,-21,-21,-21,-21,-21,-21,-21,-21,
   -21,-21,-21,-21,-21,-21,-21,-21,-21,-21,-21,-21,-21,-21,-21,-21,
    21, 21, 21, 21, 21, 21, 21, 21, 21, 21, 21, 21, 21, 21, 21, 21,
    21, 21, 21, 21, 21, 21, 21, 21, 21, 21, 21, 21, 21, 21, 21, 21
};

static const s8 code fm_wave_clipsin[64] = {
     0,  3,  6,  8, 11, 14, 17, 19, 20, 20, 20, 20, 20, 20, 20, 20,
    20, 20, 20, 20, 20, 20, 20, 20, 20, 19, 17, 14, 11,  8,  6,  3,
     0, -3, -6, -8,-11,-14,-17,-19,-20,-20,-20,-20,-20,-20,-20,-20,
   -20,-20,-20,-20,-20,-20,-20,-20,-20,-19,-17,-14,-11, -8, -6, -3
};

static const s8 code fm_wave_abssin[64] = {
     0,  3,  6,  8, 11, 14, 17, 19, 21, 23, 25, 27, 28, 29, 30, 30,
    31, 30, 30, 29, 28, 27, 25, 23, 21, 19, 17, 14, 11,  8,  6,  3,
     0,  3,  6,  8, 11, 14, 17, 19, 21, 23, 25, 27, 28, 29, 30, 30,
    31, 30, 30, 29, 28, 27, 25, 23, 21, 19, 17, 14, 11,  8,  6,  3
};

/* 波形查表 (避免 code 指针数组问题) */
static s8 fm_read_wave(u8 wave_idx, u8 idx) {
    switch (wave_idx) {
    case 0: return fm_wave_tri[idx];
    case 1: return fm_wave_clipsin[idx];
    case 2: return fm_wave_rect[idx];
    case 3: return fm_wave_sin[idx];
    case 4: return fm_wave_saw[idx];
    case 5: return fm_wave_abssin[idx];
    default: return fm_wave_tri[idx];
    }
}

/* ========== 包络计数表 (attack/decay/sustain/release 速度) ========== */
static const u8 code fm_env_cnt[16] = {
    0, 1, 2, 3, 4, 5, 7, 10, 13, 20, 29, 43, 64, 86, 128, 255
};

/* ========== 频率表: MIDI note 24-127 -> 8.8 fixed step = freq*64*256/17640 ========== */
/* 原始公式: int(freq * SAMPLE_VAL(64) * 256 / PWM_KHZ(24) / 1000)
 * 适配: int(freq * 64 * 256 / 17640) */
static const u16 code fm_note_freq[92] = {
    /* C1  */ (u16)( 32.7 * 16384.0 / 17640.0 + 0.5),
    /* C#1 */ (u16)( 34.6 * 16384.0 / 17640.0 + 0.5),
    /* D1  */ (u16)( 36.7 * 16384.0 / 17640.0 + 0.5),
    /* D#1 */ (u16)( 38.9 * 16384.0 / 17640.0 + 0.5),
    /* E1  */ (u16)( 41.2 * 16384.0 / 17640.0 + 0.5),
    /* F1  */ (u16)( 43.7 * 16384.0 / 17640.0 + 0.5),
    /* F#1 */ (u16)( 46.2 * 16384.0 / 17640.0 + 0.5),
    /* G1  */ (u16)( 49.0 * 16384.0 / 17640.0 + 0.5),
    /* G#1 */ (u16)( 51.9 * 16384.0 / 17640.0 + 0.5),
    /* A1  */ (u16)( 55.0 * 16384.0 / 17640.0 + 0.5),
    /* A#1 */ (u16)( 58.3 * 16384.0 / 17640.0 + 0.5),
    /* B1  */ (u16)( 61.7 * 16384.0 / 17640.0 + 0.5),
    /* C2  */ (u16)( 65.4 * 16384.0 / 17640.0 + 0.5),
    /* C#2 */ (u16)( 69.3 * 16384.0 / 17640.0 + 0.5),
    /* D2  */ (u16)( 73.4 * 16384.0 / 17640.0 + 0.5),
    /* D#2 */ (u16)( 77.8 * 16384.0 / 17640.0 + 0.5),
    /* E2  */ (u16)( 82.4 * 16384.0 / 17640.0 + 0.5),
    /* F2  */ (u16)( 87.3 * 16384.0 / 17640.0 + 0.5),
    /* F#2 */ (u16)( 92.5 * 16384.0 / 17640.0 + 0.5),
    /* G2  */ (u16)( 98.0 * 16384.0 / 17640.0 + 0.5),
    /* G#2 */ (u16)(103.8 * 16384.0 / 17640.0 + 0.5),
    /* A2  */ (u16)(110.0 * 16384.0 / 17640.0 + 0.5),
    /* A#2 */ (u16)(116.5 * 16384.0 / 17640.0 + 0.5),
    /* B2  */ (u16)(123.5 * 16384.0 / 17640.0 + 0.5),
    /* C3  */ (u16)(130.8 * 16384.0 / 17640.0 + 0.5),
    /* C#3 */ (u16)(138.6 * 16384.0 / 17640.0 + 0.5),
    /* D3  */ (u16)(146.8 * 16384.0 / 17640.0 + 0.5),
    /* D#3 */ (u16)(155.6 * 16384.0 / 17640.0 + 0.5),
    /* E3  */ (u16)(164.8 * 16384.0 / 17640.0 + 0.5),
    /* F3  */ (u16)(174.6 * 16384.0 / 17640.0 + 0.5),
    /* F#3 */ (u16)(185.0 * 16384.0 / 17640.0 + 0.5),
    /* G3  */ (u16)(196.0 * 16384.0 / 17640.0 + 0.5),
    /* G#3 */ (u16)(207.7 * 16384.0 / 17640.0 + 0.5),
    /* A3  */ (u16)(220.0 * 16384.0 / 17640.0 + 0.5),
    /* A#3 */ (u16)(233.1 * 16384.0 / 17640.0 + 0.5),
    /* B3  */ (u16)(246.9 * 16384.0 / 17640.0 + 0.5),
    /* C4  */ (u16)(261.6 * 16384.0 / 17640.0 + 0.5),
    /* C#4 */ (u16)(277.2 * 16384.0 / 17640.0 + 0.5),
    /* D4  */ (u16)(293.7 * 16384.0 / 17640.0 + 0.5),
    /* D#4 */ (u16)(311.1 * 16384.0 / 17640.0 + 0.5),
    /* E4  */ (u16)(329.6 * 16384.0 / 17640.0 + 0.5),
    /* F4  */ (u16)(349.2 * 16384.0 / 17640.0 + 0.5),
    /* F#4 */ (u16)(370.0 * 16384.0 / 17640.0 + 0.5),
    /* G4  */ (u16)(392.0 * 16384.0 / 17640.0 + 0.5),
    /* G#4 */ (u16)(415.3 * 16384.0 / 17640.0 + 0.5),
    /* A4  */ (u16)(440.0 * 16384.0 / 17640.0 + 0.5),
    /* A#4 */ (u16)(466.2 * 16384.0 / 17640.0 + 0.5),
    /* B4  */ (u16)(493.9 * 16384.0 / 17640.0 + 0.5),
    /* C5  */ (u16)(523.3 * 16384.0 / 17640.0 + 0.5),
    /* C#5 */ (u16)(554.4 * 16384.0 / 17640.0 + 0.5),
    /* D5  */ (u16)(587.3 * 16384.0 / 17640.0 + 0.5),
    /* D#5 */ (u16)(622.3 * 16384.0 / 17640.0 + 0.5),
    /* E5  */ (u16)(659.3 * 16384.0 / 17640.0 + 0.5),
    /* F5  */ (u16)(698.5 * 16384.0 / 17640.0 + 0.5),
    /* F#5 */ (u16)(740.0 * 16384.0 / 17640.0 + 0.5),
    /* G5  */ (u16)(784.0 * 16384.0 / 17640.0 + 0.5),
    /* G#5 */ (u16)(830.6 * 16384.0 / 17640.0 + 0.5),
    /* A5  */ (u16)(880.0 * 16384.0 / 17640.0 + 0.5),
    /* A#5 */ (u16)(932.3 * 16384.0 / 17640.0 + 0.5),
    /* B5  */ (u16)(987.0 * 16384.0 / 17640.0 + 0.5),
    /* C6  */ (u16)(1046.5 * 16384.0 / 17640.0 + 0.5),
    /* C#6 */ (u16)(1108.7 * 16384.0 / 17640.0 + 0.5),
    /* D6  */ (u16)(1174.7 * 16384.0 / 17640.0 + 0.5),
    /* D#6 */ (u16)(1244.5 * 16384.0 / 17640.0 + 0.5),
    /* E6  */ (u16)(1318.5 * 16384.0 / 17640.0 + 0.5),
    /* F6  */ (u16)(1396.9 * 16384.0 / 17640.0 + 0.5),
    /* F#6 */ (u16)(1480.0 * 16384.0 / 17640.0 + 0.5),
    /* G6  */ (u16)(1568.0 * 16384.0 / 17640.0 + 0.5),
    /* G#6 */ (u16)(1661.2 * 16384.0 / 17640.0 + 0.5),
    /* A6  */ (u16)(1760.0 * 16384.0 / 17640.0 + 0.5),
    /* A#6 */ (u16)(1864.7 * 16384.0 / 17640.0 + 0.5),
    /* B6  */ (u16)(1975.5 * 16384.0 / 17640.0 + 0.5),
    /* C7  */ (u16)(4186.0 * 16384.0 / 17640.0 + 0.5),
    /* C#7 */ (u16)(4434.9 * 16384.0 / 17640.0 + 0.5),
    /* D7  */ (u16)(4698.6 * 16384.0 / 17640.0 + 0.5),
    /* D#7 */ (u16)(4978.0 * 16384.0 / 17640.0 + 0.5),
    /* E7  */ (u16)(5274.0 * 16384.0 / 17640.0 + 0.5),
    /* F7  */ (u16)(5587.7 * 16384.0 / 17640.0 + 0.5),
    /* F#7 */ (u16)(5919.9 * 16384.0 / 17640.0 + 0.5),
    /* G7  */ (u16)(6271.9 * 16384.0 / 17640.0 + 0.5),
    /* G#7 */ (u16)(6644.9 * 16384.0 / 17640.0 + 0.5),
    /* A7  */ (u16)(7040.0 * 16384.0 / 17640.0 + 0.5),
    /* A#7 */ (u16)(7458.6 * 16384.0 / 17640.0 + 0.5),
    /* B7  */ (u16)(7902.1 * 16384.0 / 17640.0 + 0.5),
    /* C8  */ (u16)(8372.0 * 16384.0 / 17640.0 + 0.5),
    /* C#8 */ (u16)(8869.8 * 16384.0 / 17640.0 + 0.5),
    /* D8  */ (u16)(9397.3 * 16384.0 / 17640.0 + 0.5),
    /* D#8 */ (u16)(9956.1 * 16384.0 / 17640.0 + 0.5),
    /* E8  */ (u16)(10548.1 * 16384.0 / 17640.0 + 0.5),
    /* F8  */ (u16)(11175.3 * 16384.0 / 17640.0 + 0.5),
    /* F#8 */ (u16)(11839.8 * 16384.0 / 17640.0 + 0.5),
    /* G8  */ (u16)(12543.9 * 16384.0 / 17640.0 + 0.5)
};

/* ========== Operator 状态 ========== */
typedef struct {
    u8  fb;          /* feedback level (0-7, op1 only) */
    s8  fb_val;      /* feedback accumulator (signed) */
    u8  atk;         /* attack rate (converted from envelope_cnt) */
    u8  decy;        /* decay rate */
    u8  sul;         /* sustain level (0-31) */
    u8  sus;         /* sustain rate */
    u8  rel;         /* release rate */
    u8  tl;          /* total level (0-31, inverted: 31=max) */
    u8  mul;         /* frequency multiplier (0-15) */
    u8  wave_idx;    /* wave table index (0-5) */
    u16 sin_pos;     /* 8.8 fixed-point phase */
    u16 sin_step;    /* phase increment per sample */
    u8  env_state;   /* 0=off, 1=atk, 2=decay, 3=sustain, 4=release */
    u8  env_cnt;     /* envelope counter */
    u8  env_step;    /* current envelope step size */
    u8  level;       /* current envelope level (0-31) */
} FmOp;

static FmOp fm_op[FM_OPS];

/* voice active: midino != 0 means playing */
static u8 fm_midino[FM_VOICES];

/* envelope tick counter: round-robin, 1 operator per 8 ticks */
static u8 fm_wait_cnt;

/* ========== 内部函数 ========== */

void fm_note_on(u8 voice, u8 note) {
    u8 opi;
    u16 f;

    if (voice >= FM_VOICES) return;
    if (note < 24) note = 24;
    if (note > 115) note = 115;
    note -= 24;

    f = fm_note_freq[note];

    /* OP1: modulator */
    opi = voice * 2;
    if (fm_op[opi].mul == 0) {
        fm_op[opi].sin_step = f >> 1;
    } else {
        fm_op[opi].sin_step = (u16)((u32)f * fm_op[opi].mul);
    }
    fm_op[opi].sin_pos = 0;
    fm_op[opi].env_state = 1;    /* attack */
    fm_op[opi].env_cnt = 250;
    fm_op[opi].level = 0;
    fm_op[opi].fb_val = 0;
    fm_op[opi].env_step = fm_op[opi].atk;

    /* OP2: carrier */
    opi = voice * 2 + 1;
    if (fm_op[opi].mul == 0) {
        fm_op[opi].sin_step = f >> 1;
    } else {
        fm_op[opi].sin_step = (u16)((u32)f * fm_op[opi].mul);
    }
    fm_op[opi].sin_pos = 0;
    fm_op[opi].env_state = 1;
    fm_op[opi].env_cnt = 250;
    fm_op[opi].level = 0;
    fm_op[opi].fb_val = 0;
    fm_op[opi].env_step = fm_op[opi].atk;

    fm_midino[voice] = note + 24;
}

void fm_note_off(u8 voice) {
    u8 opi;
    if (voice >= FM_VOICES) return;
    if (fm_midino[voice] == 0) return;

    opi = voice * 2;
    fm_op[opi].env_state = 4;    /* release */
    fm_op[opi].env_step = fm_op[opi].rel;

    opi = voice * 2 + 1;
    fm_op[opi].env_state = 4;
    fm_op[opi].env_step = fm_op[opi].rel;

    fm_midino[voice] = 0;
}

void fm_set_tone(u8 voice, u8 *dat) {
    u8 opi;
    if (voice >= FM_VOICES) return;

    /* OP1 (modulator) */
    opi = voice * 2;
    fm_op[opi].fb = dat[0] & 0x07;
    fm_op[opi].atk  = fm_env_cnt[dat[1] & 0x0F];
    fm_op[opi].decy = fm_env_cnt[dat[2] & 0x0F];
    fm_op[opi].sul  = (dat[3] == 15) ? 0 : (31 - dat[3] * 2);
    fm_op[opi].sus  = fm_env_cnt[dat[4] & 0x0F];
    fm_op[opi].rel  = fm_env_cnt[dat[5] & 0x0F];
    fm_op[opi].tl   = 31 - (dat[6] & 0x1F);
    fm_op[opi].mul  = dat[7] & 0x0F;
    fm_op[opi].wave_idx = dat[8] % 6;

    /* OP2 (carrier) */
    opi = voice * 2 + 1;
    fm_op[opi].fb = 0;
    fm_op[opi].atk  = fm_env_cnt[dat[9] & 0x0F];
    fm_op[opi].decy = fm_env_cnt[dat[10] & 0x0F];
    fm_op[opi].sul  = (dat[11] == 15) ? 0 : (31 - dat[11] * 2);
    fm_op[opi].sus  = fm_env_cnt[dat[12] & 0x0F];
    fm_op[opi].rel  = fm_env_cnt[dat[13] & 0x0F];
    fm_op[opi].tl   = 31 - (dat[14] & 0x1F);
    fm_op[opi].mul  = dat[15] & 0x0F;
    fm_op[opi].wave_idx = dat[16] % 6;
}

void fm_set_wave(u8 voice, u8 wave) {
    u8 opi;
    if (voice >= FM_VOICES) return;
    wave = wave % 6;
    opi = voice * 2;
    fm_op[opi].wave_idx = wave;
    opi = voice * 2 + 1;
    fm_op[opi].wave_idx = wave;
}

/* 包络更新 (简化版: 每次调用更新一个 operator) */
static void fm_env_tick(u8 opi) {
    u8 cnt, step, lvl, sul_val;

    cnt = fm_op[opi].env_cnt;
    step = fm_op[opi].env_step;
    if (cnt >= step) {
        fm_op[opi].env_cnt = cnt - step;
        return;
    }

    fm_op[opi].env_cnt = 250;
    lvl = fm_op[opi].level;

    switch (fm_op[opi].env_state) {
    case 1: /* attack */
        lvl++;
        if (lvl >= 31) {
            fm_op[opi].env_state = 2; /* decay */
            fm_op[opi].env_step = fm_op[opi].decy;
        }
        fm_op[opi].level = lvl;
        break;

    case 2: /* decay */
        if (lvl > 0) lvl--;
        fm_op[opi].level = lvl;
        sul_val = fm_op[opi].sul;
        if (lvl == sul_val) {
            fm_op[opi].env_state = 3; /* sustain */
            fm_op[opi].env_step = fm_op[opi].sus;
        }
        break;

    case 3: /* sustain */
        if (lvl > 0) lvl--;
        fm_op[opi].level = lvl;
        if (lvl == 0) {
            fm_op[opi].sin_step = 0; /* silence */
        }
        break;

    case 4: /* release */
        if (lvl > 0) lvl--;
        fm_op[opi].level = lvl;
        if (lvl == 0) {
            fm_op[opi].sin_step = 0;
        }
        break;

    default:
        break;
    }
}

/* ========== 公开函数 ========== */

void fm_init(void) {
    u8 i;
    for (i = 0; i < FM_OPS; i++) {
        fm_op[i].wave_idx = 0;   /* tri default */
        fm_op[i].atk  = fm_env_cnt[15];
        fm_op[i].decy = fm_env_cnt[9];
        fm_op[i].sul  = 31 - 9 * 2;
        fm_op[i].sus  = fm_env_cnt[2];
        fm_op[i].rel  = fm_env_cnt[5];
        fm_op[i].mul  = 1;
        fm_op[i].fb = 0;
        fm_op[i].fb_val = 0;
        fm_op[i].sin_pos = 0;
        fm_op[i].sin_step = 0;
        fm_op[i].env_state = 0;
        fm_op[i].env_cnt = 0;
        fm_op[i].env_step = 0;
        fm_op[i].level = 0;
    }
    /* OP1 (modulator): tl=0 (不直接输出), OP2 (carrier): tl=max */
    for (i = 0; i < FM_VOICES; i++) {
        fm_op[i * 2].tl = 0;          /* modulator: 静音 */
        fm_op[i * 2 + 1].tl = 31;    /* carrier: 最大音量 (tl inverted) */
        fm_midino[i] = 0;
    }
    for (i = 0; i < FM_VOICES; i++) {
        fm_midino[i] = 0;
    }
    fm_wait_cnt = 0;
}

/* FM 渲染 (每次 ISR 调用, 返回 s16 混合输出) */
s16 fm_render(void) {
    u8 v, opi;
    s16 total;
    s8 ch_out;
    s8 wave_val;
    u8 idx, lvl, tl, fb;
    s8 fb_val;
    u16 pos, step;

    fm_wait_cnt++;
    fm_wait_cnt &= 0x07;

    total = 0;

    for (v = 0; v < FM_VOICES; v++) {
        opi = v * 2;

        /* ---- OP1 (modulator) ---- */
        pos = fm_op[opi].sin_pos;
        step = fm_op[opi].sin_step;
        pos += step;
        fm_op[opi].sin_pos = pos;
        idx = (u8)(pos >> 8);
        fb_val = fm_op[opi].fb_val;
        idx += (u8)fb_val;
        idx &= 0x3F;

        wave_val = fm_read_wave(fm_op[opi].wave_idx, idx);

        /* 包络 tick (round-robin) */
        if (fm_wait_cnt == v) {
            fm_env_tick(opi);
        }

        lvl = fm_op[opi].level;
        tl = fm_op[opi].tl;
        /* out = wave_val * (lvl+1) * (tl+1) / 32 / 32 近似 */
        ch_out = (s8)(((s16)wave_val * (s16)(lvl + 1) * (s16)(tl + 1)) >> 10);

        /* feedback */
        fb = fm_op[opi].fb;
        if (fb > 0) {
            s8 sfb = (s8)ch_out;
            fm_op[opi].fb_val = (s8)(sfb >> fb);
        } else {
            fm_op[opi].fb_val = 0;
        }

        /* ---- OP2 (carrier) ---- */
        opi = v * 2 + 1;

        pos = fm_op[opi].sin_pos;
        step = fm_op[opi].sin_step;
        pos += step;
        fm_op[opi].sin_pos = pos;
        idx = (u8)(pos >> 8);
        idx += (u8)ch_out;    /* OP1 output modulates OP2 phase */
        idx &= 0x3F;

        wave_val = fm_read_wave(fm_op[opi].wave_idx, idx);

        if (fm_wait_cnt == v) {
            fm_env_tick(opi);
        }

        lvl = fm_op[opi].level;
        tl = fm_op[opi].tl;
        ch_out = (s8)(((s16)wave_val * (s16)(lvl + 1) * (s16)(tl + 1)) >> 10);

        total += ch_out;
    }

    return total;
}
