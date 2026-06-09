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

/* ========== 合并波形表 (6 waves x 64 entries = 384 bytes, code 段) ========== */
/* wave_idx: 0=tri, 1=clipsin, 2=rect, 3=sin, 4=saw, 5=abssin */
/* 查表: fm_waves[(wave_idx << 6) | idx]  即 wave_idx*64+idx */
static const s8 code fm_waves[384] = {
    /* 0: tri */
     0, 1, 3, 5, 7, 9,11,13,15,17,19,21,23,25,27,29,
    31,30,28,26,24,22,20,18,16,14,12,10, 8, 6, 4, 2,
     0,-2,-4,-6,-8,-10,-12,-14,-16,-18,-20,-22,-24,-26,-28,-30,
   -31,-30,-28,-26,-24,-22,-20,-18,-16,-14,-12,-10, -8, -6, -4, -2,
    /* 1: clipsin */
     0,  3,  6,  8, 11, 14, 17, 19, 20, 20, 20, 20, 20, 20, 20, 20,
    20, 20, 20, 20, 20, 20, 20, 20, 20, 19, 17, 14, 11,  8,  6,  3,
     0, -3, -6, -8,-11,-14,-17,-19,-20,-20,-20,-20,-20,-20,-20,-20,
   -20,-20,-20,-20,-20,-20,-20,-20,-20,-19,-17,-14,-11, -8, -6, -3,
    /* 2: rect */
   -21,-21,-21,-21,-21,-21,-21,-21,-21,-21,-21,-21,-21,-21,-21,-21,
   -21,-21,-21,-21,-21,-21,-21,-21,-21,-21,-21,-21,-21,-21,-21,-21,
    21, 21, 21, 21, 21, 21, 21, 21, 21, 21, 21, 21, 21, 21, 21, 21,
    21, 21, 21, 21, 21, 21, 21, 21, 21, 21, 21, 21, 21, 21, 21, 21,
    /* 3: sin */
     0,  3,  6,  9, 12, 15, 17, 20, 22, 24, 26, 28, 29, 30, 31, 31,
    31, 31, 31, 30, 29, 28, 26, 24, 22, 20, 17, 15, 12,  9,  6,  3,
     0, -3, -6, -9,-12,-15,-17,-20,-22,-24,-26,-28,-29,-30,-31,-31,
   -31,-31,-31,-30,-29,-28,-26,-24,-22,-20,-17,-15,-12, -9, -6, -3,
    /* 4: saw */
     0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9,10,11,12,13,14,
    15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,
   -31,-30,-29,-28,-27,-26,-25,-24,-23,-22,-21,-20,-19,-18,-17,-16,
   -15,-14,-13,-12,-11,-10, -9, -8, -7, -6, -5, -4, -3, -2, -1,  0,
    /* 5: abssin */
     0,  3,  6,  8, 11, 14, 17, 19, 21, 23, 25, 27, 28, 29, 30, 30,
    31, 30, 30, 29, 28, 27, 25, 23, 21, 19, 17, 14, 11,  8,  6,  3,
     0,  3,  6,  8, 11, 14, 17, 19, 21, 23, 25, 27, 28, 29, 30, 30,
    31, 30, 30, 29, 28, 27, 25, 23, 21, 19, 17, 14, 11,  8,  6,  3
};

/* ========== 包络计数表 (attack/decay/sustain/release 速度) ========== */
static const u8 code fm_env_cnt[16] = {
    0, 1, 2, 3, 4, 5, 7, 10, 13, 20, 29, 43, 64, 86, 128, 255
};

/* ========== 频率表: MIDI note 24-127 -> 8.8 fixed step = freq*64*256/17640 ========== */
/* 原始公式: int(freq * SAMPLE_VAL(64) * 256 / PWM_KHZ(24) / 1000)
 * 适配: int(freq * 64 * 256 / 17640) */
static const u16 code fm_note_freq[104] = {
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
    /* C7  */ (u16)(2093.0 * 16384.0 / 17640.0 + 0.5),
    /* C#7 */ (u16)(2217.5 * 16384.0 / 17640.0 + 0.5),
    /* D7  */ (u16)(2349.3 * 16384.0 / 17640.0 + 0.5),
    /* D#7 */ (u16)(2489.0 * 16384.0 / 17640.0 + 0.5),
    /* E7  */ (u16)(2637.0 * 16384.0 / 17640.0 + 0.5),
    /* F7  */ (u16)(2793.8 * 16384.0 / 17640.0 + 0.5),
    /* F#7 */ (u16)(2960.0 * 16384.0 / 17640.0 + 0.5),
    /* G7  */ (u16)(3136.0 * 16384.0 / 17640.0 + 0.5),
    /* G#7 */ (u16)(3322.4 * 16384.0 / 17640.0 + 0.5),
    /* A7  */ (u16)(3520.0 * 16384.0 / 17640.0 + 0.5),
    /* A#7 */ (u16)(3729.3 * 16384.0 / 17640.0 + 0.5),
    /* B7  */ (u16)(3951.1 * 16384.0 / 17640.0 + 0.5),
    /* C8  */ (u16)(4186.0 * 16384.0 / 17640.0 + 0.5),
    /* C#8 */ (u16)(4434.9 * 16384.0 / 17640.0 + 0.5),
    /* D8  */ (u16)(4698.6 * 16384.0 / 17640.0 + 0.5),
    /* D#8 */ (u16)(4978.0 * 16384.0 / 17640.0 + 0.5),
    /* E8  */ (u16)(5274.0 * 16384.0 / 17640.0 + 0.5),
    /* F8  */ (u16)(5587.7 * 16384.0 / 17640.0 + 0.5),
    /* F#8 */ (u16)(5919.9 * 16384.0 / 17640.0 + 0.5),
    /* G8  */ (u16)(6271.9 * 16384.0 / 17640.0 + 0.5),
    /* G#8 */ (u16)(13289.8 * 16384.0 / 17640.0 + 0.5),
    /* A8  */ (u16)(14080.0 * 16384.0 / 17640.0 + 0.5),
    /* A#8 */ (u16)(14917.2 * 16384.0 / 17640.0 + 0.5),
    /* B8  */ (u16)(15804.3 * 16384.0 / 17640.0 + 0.5),
    /* C9  */ (u16)(16744.0 * 16384.0 / 17640.0 + 0.5),
    /* C#9 */ (u16)(17739.7 * 16384.0 / 17640.0 + 0.5),
    /* D9  */ (u16)(18794.5 * 16384.0 / 17640.0 + 0.5),
    /* D#9 */ (u16)(19912.2 * 16384.0 / 17640.0 + 0.5),
    /* E9  */ (u16)(21096.2 * 16384.0 / 17640.0 + 0.5),
    /* F9  */ (u16)(22350.6 * 16384.0 / 17640.0 + 0.5),
    /* F#9 */ (u16)(23679.6 * 16384.0 / 17640.0 + 0.5)
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

/* per-voice volume override (from reg 0x30-0x33, 0-15) */
static u8 fm_voice_vol[FM_VOICES];

/* envelope tick counter: round-robin, 1 operator per 8 ticks */
static u8 fm_wait_cnt;

/* 音色模板 (reg 0x00-0x09, 全局共用) */
static struct {
    u8 mod_mul, car_mul;
    u8 mod_tl,  car_tl;
    u8 mod_fb;  /* feedback, 低3位 */
    u8 mod_atk, mod_dec;
    u8 car_atk, car_dec;
    u8 mod_sul, mod_rel;
    u8 car_sul, car_rel;
    u8 mod_wave, car_wave;
} fm_tone;

/* 将音色模板应用到指定 voice 的 ops */
static void fm_apply_tone(u8 voice) {
    u8 opi;
    opi = voice * 2;
    fm_op[opi].mul = fm_tone.mod_mul;
    fm_op[opi].tl  = fm_tone.mod_tl;
    fm_op[opi].fb  = fm_tone.mod_fb;
    fm_op[opi].atk  = fm_env_cnt[fm_tone.mod_atk & 0x0F];
    fm_op[opi].decy = fm_env_cnt[fm_tone.mod_dec & 0x0F];
    fm_op[opi].sul  = (fm_tone.mod_sul == 15) ? 0 : (31 - fm_tone.mod_sul * 2);
    fm_op[opi].sus  = fm_env_cnt[fm_tone.mod_rel & 0x0F];
    fm_op[opi].rel  = fm_env_cnt[fm_tone.mod_rel & 0x0F];
    fm_op[opi].wave_idx = fm_tone.mod_wave % 6;

    opi = voice * 2 + 1;
    fm_op[opi].mul = fm_tone.car_mul;
    fm_op[opi].tl  = fm_tone.car_tl;
    fm_op[opi].fb  = 0;
    fm_op[opi].atk  = fm_env_cnt[fm_tone.car_atk & 0x0F];
    fm_op[opi].decy = fm_env_cnt[fm_tone.car_dec & 0x0F];
    fm_op[opi].sul  = (fm_tone.car_sul == 15) ? 0 : (31 - fm_tone.car_sul * 2);
    fm_op[opi].sus  = fm_env_cnt[fm_tone.car_rel & 0x0F];
    fm_op[opi].rel  = fm_env_cnt[fm_tone.car_rel & 0x0F];
    fm_op[opi].wave_idx = fm_tone.car_wave % 6;
}

/* ========== 内部函数 ========== */

/* 寄存器映射 (模仿 OPLL 分页结构):
 * 0x00-0x09: 音色参数 (全局, 所有 channel 共用)
 *   0x00: modulator MULTI (0-15)
 *   0x01: carrier MULTI (0-15)
 *   0x02: modulator TL (0-31, 调制深度)
 *   0x03: carrier TL (高5位) + FEEDBACK (低3位)
 *   0x04: modulator AR/DR (高4位=atk, 低4位=decy)
 *   0x05: carrier AR/DR
 *   0x06: modulator SL/RR (高4位=sul, 低4位=rel)
 *   0x07: carrier SL/RR
 *   0x08: modulator WAVE (低3位, 0-5)
 *   0x09: carrier WAVE (低3位, 0-5)
 * 0x10-0x13: channel 0-3 note on (data = MIDI note)
 * 0x20-0x23: channel 0-3 note off
 * 0x30-0x33: channel 0-3 volume override (0-15, 影响 carrier TL)
 */
void fm_wr(u8 addr, u8 dat) {
    u8 voice, opi, note;
    u16 f;

    switch (addr & 0xF0) {
    case 0x00:
        /* 音色参数 */
        switch (addr & 0x0F) {
        case 0x00: fm_tone.mod_mul = dat & 0x0F; break;
        case 0x01: fm_tone.car_mul = dat & 0x0F; break;
        case 0x02: fm_tone.mod_tl  = dat & 0x1F; break;
        case 0x03: fm_tone.car_tl  = dat >> 3; fm_tone.mod_fb = dat & 0x07; break;
        case 0x04: fm_tone.mod_atk = (dat >> 4) & 0x0F; fm_tone.mod_dec = dat & 0x0F; break;
        case 0x05: fm_tone.car_atk = (dat >> 4) & 0x0F; fm_tone.car_dec = dat & 0x0F; break;
        case 0x06: fm_tone.mod_sul = (dat >> 4) & 0x0F; fm_tone.mod_rel = dat & 0x0F; break;
        case 0x07: fm_tone.car_sul = (dat >> 4) & 0x0F; fm_tone.car_rel = dat & 0x0F; break;
        case 0x08: fm_tone.mod_wave = dat % 6; break;
        case 0x09: fm_tone.car_wave = dat % 6; break;
        }
        break;

    case 0x10:
        /* note on */
        voice = addr & 0x0F;
        if (voice >= FM_VOICES) return;
        note = dat;
        if (note < 24) note = 24;
        if (note > 127) note = 127;
        note -= 24;
        f = fm_note_freq[note];

        /* 先应用音色模板 */
        fm_apply_tone(voice);

        /* modulator */
        opi = voice * 2;
        fm_op[opi].sin_step = fm_op[opi].mul ?
            (u16)((u32)f * fm_op[opi].mul) : (f >> 1);
        fm_op[opi].sin_pos = 0;
        fm_op[opi].env_state = 1;
        fm_op[opi].env_cnt = 250;
        fm_op[opi].level = 0;
        fm_op[opi].fb_val = 0;
        fm_op[opi].env_step = fm_op[opi].atk;

        /* carrier */
        opi = voice * 2 + 1;
        fm_op[opi].sin_step = fm_op[opi].mul ?
            (u16)((u32)f * fm_op[opi].mul) : (f >> 1);
        fm_op[opi].sin_pos = 0;
        fm_op[opi].env_state = 1;
        fm_op[opi].env_cnt = 250;
        fm_op[opi].level = 0;
        fm_op[opi].fb_val = 0;
        fm_op[opi].env_step = fm_op[opi].atk;

        /* 应用 per-voice volume */
        fm_op[voice * 2 + 1].tl = fm_voice_vol[voice];

        fm_midino[voice] = note + 24;
        break;

    case 0x20:
        /* note off */
        voice = addr & 0x0F;
        if (voice >= FM_VOICES) return;
        if (fm_midino[voice] == 0) return;
        opi = voice * 2;
        fm_op[opi].env_state = 4;
        fm_op[opi].env_step = fm_op[opi].rel;
        opi = voice * 2 + 1;
        fm_op[opi].env_state = 4;
        fm_op[opi].env_step = fm_op[opi].rel;
        fm_midino[voice] = 0;
        break;

    case 0x30:
        /* per-voice volume override */
        voice = addr & 0x0F;
        if (voice >= FM_VOICES) return;
        fm_voice_vol[voice] = dat & 0x1F;
        break;
    }
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
    /* 音色模板默认值 */
    fm_tone.mod_mul = 1;  fm_tone.car_mul = 1;
    fm_tone.mod_tl  = 0;  fm_tone.car_tl  = 31;
    fm_tone.mod_fb  = 0;
    fm_tone.mod_atk = 15; fm_tone.mod_dec = 9;
    fm_tone.car_atk = 15; fm_tone.car_dec = 9;
    fm_tone.mod_sul = 9;  fm_tone.mod_rel = 5;
    fm_tone.car_sul = 9;  fm_tone.car_rel = 5;
    fm_tone.mod_wave = 0; fm_tone.car_wave = 3;

    for (i = 0; i < FM_OPS; i++) {
        fm_op[i].wave_idx = 0;
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
    for (i = 0; i < FM_VOICES; i++) {
        fm_op[i * 2].tl = 0;
        fm_op[i * 2 + 1].tl = 31;
        fm_midino[i] = 0;
        fm_voice_vol[i] = 31;
    }
    fm_wait_cnt = 0;
}

u8 fm_channel_mask(void) {
    u8 mask = 0, i;
    for (i = 0; i < FM_VOICES; i++) {
        if (fm_op[i * 2 + 1].sin_step) {
            if (i < 8) mask |= (1 << i);
            else mask |= (1 << (i & 7));  /* voice 8-15 复用 P0.0-7 */
        }
    }
    return mask;
}

/* FM 渲染 (每次 ISR 调用, 返回 s16 混合输出) */
s16 fm_render(void) {
    u8 v, opi;
    s16 total;
    s8 ch_out;
    s8 wave_val;
    u8 idx, lvl, tl, fb, wi;
    s8 fb_val;
    u16 pos, step;

    fm_wait_cnt++;
    fm_wait_cnt &= 0x0F;

    total = 0;

    for (v = 0; v < FM_VOICES; v++) {
        opi = v * 2;

        /* skip idle voice */
        if (fm_op[opi].sin_step == 0) continue;

        /* ---- OP1 (modulator) ---- */
        pos = fm_op[opi].sin_pos;
        step = fm_op[opi].sin_step;
        pos += step;
        fm_op[opi].sin_pos = pos;
        idx = (u8)(pos >> 8);
        fb_val = fm_op[opi].fb_val;
        idx += (u8)fb_val;
        idx &= 0x3F;

        wi = fm_op[opi].wave_idx;
        wave_val = fm_waves[(u16)(wi << 6) | idx];

        /* 包络 tick (round-robin) */
        if (fm_wait_cnt == v) {
            fm_env_tick(opi);
        }

        lvl = fm_op[opi].level;
        tl = fm_op[opi].tl;
        ch_out = (s8)(((s16)wave_val * (s16)(lvl + 1) * (s16)(tl + 1)) >> 10);

        /* feedback */
        fb = fm_op[opi].fb;
        if (fb > 0) {
            fm_op[opi].fb_val = (s8)((s8)ch_out >> fb);
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
        idx += (u8)ch_out;
        idx &= 0x3F;

        wi = fm_op[opi].wave_idx;
        wave_val = fm_waves[(u16)(wi << 6) | idx];

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
