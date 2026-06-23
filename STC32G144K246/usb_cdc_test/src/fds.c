/* fds.c - NES FDS 音源芯片仿真核心 (STC32G C251 版)
 * 移植自 libvgm np_nes_fds.c (NSFPlay 2.3, Valley Bell).
 *
 * 1 通道频率调制:
 *   调制器 (64 步 3-bit 波形) → 改变载波频率 → 载波 (64 步 6-bit 波形) 输出
 *   2 个 ramp 包络 (EVOL 音量 + EMOD 调制增益)
 *   RC 低通滤波 (cutoff 2000Hz)
 *
 * C251 适配:
 *   - 去掉 calloc/malloc → xdata 静态变量
 *   - 去掉 exp() → RC 常量预计算硬编码
 *   - bool → u8, INT32 → s32, UINT32 → u32
 *   - 不用 RATIO_CNTR, 用 nes.c 同款 base_count/base_incr 24-bit 定点
 */
#include "stc.h"
#include "fds.h"

/* RC 低通滤波器常量 (cutoff=2000Hz @ 22050Hz, RC_BITS=12):
 *   leak = exp(-2*pi*2000/22050) = 0.566787
 *   rc_k = leak * 4096 = 2322
 *   rc_l = 4096 - 2322 = 1774 */
#define RC_BITS     12
#define FDS_RC_K    2322
#define FDS_RC_L    1774

/* 调制器 BIAS 表: wave[TMOD] 值 0-7 映射到斜率 */
static const s8 code FDS_BIAS[8] = { 0, 1, 2, 4, 0, -4, -2, -1 };

/* 主音量表 (8-bit 近似, MASTER_VOL/MAX_OUT * 256 * 2/N):
 *   MASTER_VOL = 2.4 * 1223.0 = 2935.2
 *   MAX_OUT = 32.0 * 63.0 = 2016.0
 *   MASTER[0] = 2935.2/2016 * 256 * 2/2 = 372
 *   MASTER[1] = 2935.2/2016 * 256 * 2/3 = 248
 *   MASTER[2] = 2935.2/2016 * 256 * 2/4 = 186
 *   MASTER[3] = 2935.2/2016 * 256 * 2/5 = 149 */
static const s16 code FDS_MASTER[4] = { 372, 248, 186, 149 };

/* FDS 状态结构 (xdata, ~0.5KB) */
typedef struct {
    /* 两个波形表: [0]=调制器(3-bit), [1]=载波(6-bit) */
    s32 wave[2][64];
    u32 freq[2];        /* 12-bit 频率 */
    u32 phase[2];       /* 22-bit 相位 (6-bit 表位置 + 16-bit 累积器) */

    u8  wav_write;      /* $4089 bit7: 波形表写使能 */
    u8  wav_halt;       /* $4083 bit7: 载波停止 */
    u8  env_halt;       /* $4083 bit6: 包络停止 */
    u8  mod_halt;       /* $4087 bit7: 调制器停止 */
    u32 mod_pos;        /* 调制器累积位置 (7-bit) */
    u32 mod_write_pos;  /* OPT_4085_RESET 用 */

    /* 两个 ramp 包络: [0]=调制增益(EMOD), [1]=音量(EVOL) */
    u8  env_mode[2];    /* 0=下降, 1=上升 */
    u8  env_disable[2]; /* 1=禁用 (直接用 speed 作输出) */
    u32 env_timer[2];
    u32 env_speed[2];   /* 6-bit 速度 */
    u32 env_out[2];     /* 当前输出 (0-32) */
    u32 master_env_speed; /* $408A */

    u8  master_io;      /* $4023 bit1: I/O 使能 */
    u8  master_vol;     /* $4089 bit0-1: 主音量 (0-3) */

    s32 fout;           /* 当前输出 (波形值 × 音量) */
    s32 rc_accum;       /* RC 低通滤波器累积 */
} FDS_STATE;

static FDS_STATE xdata fds;
static u32 data fds_base_count;
static u32 data fds_base_incr;

void fds_set_clock(u32 clock_hz) {
    fds_base_incr = (u32)(((double)clock_hz * (double)(1UL << FDS_GETA_BITS)) / FDS_RATE);
}

void fds_init(void) {
    u8 i, j;
    /* 清零整个结构 */
    for (i = 0; i < 2; i++) {
        for (j = 0; j < 64; j++) fds.wave[i][j] = 0;
        fds.freq[i] = 0;
        fds.phase[i] = 0;
        fds.env_mode[i] = 0;
        fds.env_disable[i] = 0;
        fds.env_timer[i] = 0;
        fds.env_speed[i] = 0;
        fds.env_out[i] = 0;
    }
    fds.wav_write = 0;
    fds.wav_halt = 1;       /* 开机时 halt */
    fds.env_halt = 1;
    fds.mod_halt = 1;
    fds.mod_pos = 0;
    fds.mod_write_pos = 0;
    fds.master_io = 1;      /* 默认使能 (对齐 libvgm device_reset: $4023=0x83) */
    fds.master_vol = 0;
    /* FDS BIOS reset 自动写 $408A=0xE8 (master envelope speed).
     * 很多游戏 (如 Zelda) 不显式写 $408A, 依赖 BIOS 默认值.
     * 如果设 0, Tick 里 master_env_speed!=0 检查失败 → 包络永不跑. */
    fds.master_env_speed = 0xE8;
    fds.fout = 0;
    fds.rc_accum = 0;
    fds_base_count = 0;
    fds_set_clock(1789773UL);   /* NTSC 默认 */
}

/* FDS 核心 tick: 推进 clocks 个 NES 周期.
 * 移植自 np_nes_fds.c Tick() (line 250-374). */
static void fds_tick(u32 clocks) {
    s32 vol_out;

    /* 1. clock envelopes (2 个 ramp 包络) */
    if (!fds.env_halt && !fds.wav_halt && fds.master_env_speed != 0) {
        u8 i;
        for (i = 0; i < 2; i++) {
            if (!fds.env_disable[i]) {
                u32 period;
                fds.env_timer[i] += clocks;
                period = (fds.env_speed[i] + 1) * fds.master_env_speed;
                period <<= 3;   /* ×8 */
                while (fds.env_timer[i] >= period) {
                    if (fds.env_mode[i]) {
                        if (fds.env_out[i] < 32) fds.env_out[i]++;
                    } else {
                        if (fds.env_out[i] > 0) fds.env_out[i]--;
                    }
                    fds.env_timer[i] -= period;
                }
            }
        }
    }

    /* 2. clock modulator (调制器) */
    if (!fds.mod_halt) {
        u32 start_pos, end_pos, p;
        start_pos = fds.phase[0] >> 16;     /* TMOD */
        fds.phase[0] += clocks * fds.freq[0];
        end_pos = fds.phase[0] >> 16;
        fds.phase[0] &= 0x3FFFFF;           /* wrap 22-bit (6-bit 表 + 16-bit 累积) */

        /* 执行所有步进的调制器表读取 */
        for (p = start_pos; p < end_pos; p++) {
            s32 wv = fds.wave[0][p & 0x3F]; /* TMOD 波形 */
            if (wv == 4) {
                fds.mod_pos = 0;            /* 4 = 重置位置 */
            } else {
                fds.mod_pos += FDS_BIAS[wv];
                fds.mod_pos &= 0x7F;        /* 7-bit clamp */
            }
        }
    }

    /* 3. clock carrier (载波, 含调制) */
    if (!fds.wav_halt) {
        s32 mod, f;

        /* 复杂的调制计算 */
        mod = 0;
        if (fds.env_out[0] != 0) {          /* EMOD != 0 才调制 */
            s32 pos, temp, rem;

            /* mod_pos 转 7-bit signed */
            pos = (fds.mod_pos < 64) ? (s32)fds.mod_pos : (s32)fds.mod_pos - 128;

            /* pos × gain, 移掉 4-bit 但有特殊"舍入" */
            temp = pos * (s32)fds.env_out[0];
            rem = temp & 0x0F;
            temp >>= 4;
            if (rem > 0 && (temp & 0x80) == 0) {
                if (pos < 0) temp -= 1;
                else         temp += 2;
            }

            /* 范围回绕 */
            while (temp >= 192) temp -= 256;
            while (temp < -64) temp += 256;

            /* 结果 × 音高, 移掉 6-bit, 四舍五入 */
            temp = (s32)fds.freq[1] * temp;  /* TWAV freq */
            rem = temp & 0x3F;
            temp >>= 6;
            if (rem >= 32) temp += 1;

            mod = temp;
        }

        /* 推进载波相位 (频率 + 调制) */
        f = (s32)fds.freq[1] + mod;
        if (f < 0) f = 0;       /* 防止负频率 */
        fds.phase[1] += clocks * (u32)f;
        fds.phase[1] &= 0x3FFFFF;   /* wrap */
    }

    /* 4. 输出 (音量上限 32) */
    vol_out = (s32)fds.env_out[1];     /* EVOL */
    if (vol_out > 32) vol_out = 32;

    /* 最终输出: 载波波形 × 音量 */
    if (!fds.wav_write)
        fds.fout = fds.wave[1][(fds.phase[1] >> 16) & 0x3F] * vol_out;
}

s16 fds_render(void) {
    u32 clocks;
    s32 v, rc_out;

    /* 24-bit 定点累积器算 clocks (照 nes.c 模式) */
    fds_base_count += fds_base_incr;
    clocks = fds_base_count >> FDS_GETA_BITS;
    fds_base_count &= (1UL << FDS_GETA_BITS) - 1;

    fds_tick(clocks);

    /* 主音量增益: fout × MASTER[master_vol] >> 8 */
    v = fds.fout * FDS_MASTER[fds.master_vol] >> 8;

    /* RC 低通滤波 (1-pole) */
    rc_out = ((fds.rc_accum * FDS_RC_K) + (v * FDS_RC_L)) >> RC_BITS;
    fds.rc_accum = rc_out;
    v = rc_out;

    /* 缩放到和其他音源匹配的范围, 限制 s16 */
    if (v > 32767) v = 32767;
    if (v < -32768) v = -32768;
    return (s16)v;
}

void fds_wr(u8 reg, u8 val) {
    /* reg 经 main.c remap 后的值 (对齐 libvgm nesintf.c + Cmd_NES_Reg):
     *   0x23:     master I/O ($4023, VGM reg 0x3F → remap 0x23)
     *   0x40-0x7F: 载波波形表 ($4040-$407F, VGM reg 直接传)
     *   0x80-0x8A: FDS 寄存器 ($4080-$408A, 有两种来源:
     *              VGM reg 0x40-0x4A 直接传, 或 VGM reg 0x20-0x2A remap 0x80|(reg&0x1F))
     *   0x8B-0x9F: $408B-$409F 未用, 忽略 */

    /* $4023 master I/O enable */
    if (reg == 0x23) {
        fds.master_io = (val & 2) ? 1 : 0;
        return;
    }

    if (!fds.master_io) return;

    /* $4040-$407F 载波波形表写 */
    if (reg >= 0x40 && reg <= 0x7F) {
        if (fds.wav_write)
            fds.wave[1][reg - 0x40] = val & 0x3F;   /* TWAV, 6-bit */
        return;
    }

    /* $4080-$408A 寄存器 (reg 取低 8 位匹配) */
    switch (reg) {
    case 0x80:  /* $4080 volume envelope */
        fds.env_disable[1] = (val & 0x80) ? 1 : 0;   /* EVOL */
        fds.env_mode[1] = (val & 0x40) ? 1 : 0;
        fds.env_timer[1] = 0;
        fds.env_speed[1] = val & 0x3F;
        if (fds.env_disable[1])
            fds.env_out[1] = fds.env_speed[1];
        break;
    case 0x82:  /* $4082 wave frequency low */
        fds.freq[1] = (fds.freq[1] & 0xF00) | val;
        break;
    case 0x83:  /* $4083 wave frequency high / enables */
        fds.freq[1] = (fds.freq[1] & 0x0FF) | (((u32)(val & 0x0F)) << 8);
        fds.wav_halt = (val & 0x80) ? 1 : 0;
        fds.env_halt = (val & 0x40) ? 1 : 0;
        if (fds.wav_halt) fds.phase[1] = 0;
        if (fds.env_halt) {
            fds.env_timer[0] = 0;
            fds.env_timer[1] = 0;
        }
        break;
    case 0x84:  /* $4084 mod envelope */
        fds.env_disable[0] = (val & 0x80) ? 1 : 0;   /* EMOD */
        fds.env_mode[0] = (val & 0x40) ? 1 : 0;
        fds.env_timer[0] = 0;
        fds.env_speed[0] = val & 0x3F;
        if (fds.env_disable[0])
            fds.env_out[0] = fds.env_speed[0];
        break;
    case 0x85:  /* $4085 mod position */
        fds.mod_pos = val & 0x7F;
        break;
    case 0x86:  /* $4086 mod frequency low */
        fds.freq[0] = (fds.freq[0] & 0xF00) | val;
        break;
    case 0x87:  /* $4087 mod frequency high / enable */
        fds.freq[0] = (fds.freq[0] & 0x0FF) | (((u32)(val & 0x0F)) << 8);
        fds.mod_halt = (val & 0x80) ? 1 : 0;
        if (fds.mod_halt)
            fds.phase[0] = fds.phase[0] & 0x3F0000;   /* reset accumulator */
        break;
    case 0x88:  /* $4088 mod table write */
        if (fds.mod_halt) {
            /* 写当前位置 + 推进 2 步 (硬件行为) */
            u32 idx;
            idx = (fds.phase[0] >> 16) & 0x3F;
            fds.wave[0][idx] = val & 0x07;
            fds.phase[0] = (fds.phase[0] + 0x010000) & 0x3FFFFF;
            idx = (fds.phase[0] >> 16) & 0x3F;
            fds.wave[0][idx] = val & 0x07;
            fds.phase[0] = (fds.phase[0] + 0x010000) & 0x3FFFFF;
            fds.mod_write_pos = fds.phase[0] >> 16;
        }
        break;
    case 0x89:  /* $4089 wave write enable, master volume */
        fds.wav_write = (val & 0x80) ? 1 : 0;
        fds.master_vol = val & 0x03;
        break;
    case 0x8A:  /* $408A envelope speed */
        fds.master_env_speed = val;
        fds.env_timer[0] = 0;
        fds.env_timer[1] = 0;
        break;
    default:
        break;
    }
}
