/* ay8910.c - AY8910 仿真核心 (STC32G C251 版)
 * 从 STC8H C51 版移植, 去掉 xdata/code 关键字
 */
#include "stc.h"
#include "ay8910.h"

static void *xmemset(void *s, int c, unsigned int n) {
    unsigned char *p = (unsigned char *)s;
    while (n--) *p++ = (unsigned char)c;
    return s;
}

#define memset xmemset

static u8  ay_reg[16];
static u16 ay_count[AY_CHANS];

static u8  ay_freq_lo[AY_CHANS];
static u8  ay_freq_hi[AY_CHANS];
static u8  ay_edge[AY_CHANS];
static u8  ay_tmask[AY_CHANS];
static u8  ay_nmask[AY_CHANS];
static u16 ay_env_freq;
static u32 ay_env_count;
static u8  ay_env_step;
static u8  ay_env_attack;
static u8  ay_env_continue, ay_env_alternate, ay_env_hold, ay_env_pause;
static u32 ay_noise_seed;
static u8  ay_noise_scaler;
static u8  ay_noise_count;
static u8  ay_noise_freq;
static u8  ay_volume[AY_CHANS];
static u32 ay_base_count;
static u32 ay_base_incr;     /* 运行时可变 (ay_set_clock), 支持 YM2149 /2 分频器 */

static const u8 ay_voltbl[32] = {
    0x00, 0x00, 0x03, 0x03, 0x04, 0x04, 0x06, 0x06,
    0x09, 0x09, 0x0D, 0x0D, 0x12, 0x12, 0x1D, 0x1D,
    0x22, 0x22, 0x37, 0x37, 0x4D, 0x4D, 0x62, 0x62,
    0x82, 0x82, 0xA6, 0xA6, 0xD0, 0xD0, 0xFF, 0xFF
};

static const u8 ay_regmsk[16] = {
    0xff, 0x0f, 0xff, 0x0f, 0xff, 0x0f, 0x1f, 0x3f,
    0x1f, 0x1f, 0x1f, 0xff, 0xff, 0x0f, 0xff, 0xff
};

void ay_init(void) {
    memset(ay_reg, 0, sizeof(ay_reg));
    memset(ay_count, 0, sizeof(ay_count));
    memset(ay_freq_lo, 0, sizeof(ay_freq_lo));
    memset(ay_freq_hi, 0, sizeof(ay_freq_hi));
    memset(ay_edge, 0, sizeof(ay_edge));
    memset(ay_tmask, 0, sizeof(ay_tmask));
    memset(ay_nmask, 0, sizeof(ay_nmask));
    memset(ay_volume, 0, sizeof(ay_volume));
    ay_env_freq = 0;
    ay_env_count = 0;
    ay_env_step = 0;
    ay_env_attack = 0;
    ay_env_continue = 0;
    ay_env_alternate = 0;
    ay_env_hold = 0;
    ay_env_pause = 0;
    ay_noise_seed = 1;
    ay_noise_scaler = 0;
    ay_noise_count = 0;
    ay_noise_freq = 0;
    ay_base_count = 0;
    ay_set_clock(AY_CLK);   /* 默认 NTSC 1789772 (对齐 libvgm) */
}

/* 运行时切换 AY 时钟 (对齐 nes_set_clock).
 * 支持 YM2149 的 /2 内置分频器 (chipFlags bit0=1): clock 传半频即可.
 * 比如 Gimmick 的 YM2149 clock=1789773, /2 分频器开启 → 传 894886.
 *
 * 注: 原 AY_BASE_INCR 常量 170223307 实际是按 21-bit 累加器算的 (虽然 AY_GETA_BITS=24),
 * 但和原有频率寄存器值配套工作正常, 不能改成"正确"的 24-bit 值否则音高全错.
 * 这里保留原常量做基准: AY_CLK (1789772) → 170223307, 其他时钟按比例缩放. */
#define AY_BASE_INCR_DEFAULT  170223307UL   /* AY_CLK=1789772 对应的已验证值 */

void ay_set_clock(u32 clock_hz) {
    /* 按比例缩放, 避免破坏原常量的 21-bit 工作点.
     * ay_base_incr = AY_BASE_INCR_DEFAULT × (clock_hz / AY_CLK) */
    ay_base_incr = (u32)(((double)clock_hz * (double)AY_BASE_INCR_DEFAULT) / (double)AY_CLK);
}

void ay_wr(u8 reg, u8 val) {
    u8 c;
    u16 freq;

    if (reg > 15) return;
    val &= ay_regmsk[reg];
    ay_reg[reg] = val;

    switch (reg) {
    case 0: case 2: case 4:
    case 1: case 3: case 5:
        c = reg >> 1;
        freq = ((u16)ay_reg[c * 2 + 1] & 0x0F) << 8;
        freq |= ay_reg[c * 2];
        ay_freq_lo[c] = ay_reg[c * 2];
        ay_freq_hi[c] = ay_reg[c * 2 + 1] & 0x0F;
        break;
    case 6:
        ay_noise_freq = val & 31;
        break;
    case 7:
        ay_tmask[0] = (val & 1) ? 1 : 0;
        ay_tmask[1] = (val & 2) ? 1 : 0;
        ay_tmask[2] = (val & 4) ? 1 : 0;
        ay_nmask[0] = (val & 8) ? 1 : 0;
        ay_nmask[1] = (val & 16) ? 1 : 0;
        ay_nmask[2] = (val & 32) ? 1 : 0;
        break;
    case 8: case 9: case 10:
        ay_volume[reg - 8] = val;
        break;
    case 11: case 12:
        ay_env_freq = ((u16)ay_reg[12] << 8) + ay_reg[11];
        break;
    case 13:
        /* 对齐 libvgm ay8910.c case AY_ESHAPE:
         * attack = 0x0F (attack bit=1) 或 0x00 (attack bit=0), 不是单 bit
         * env_volume = env_step ^ attack, 4-bit XOR 决定渐强/渐弱方向
         * env_step 总是从 0x0F 开始递减 */
        ay_env_continue = (val >> 3) & 1;
        ay_env_attack   = (val & 0x04) ? 0x0F : 0x00;
        ay_env_alternate= (val >> 1) & 1;
        ay_env_hold     = val & 1;
        ay_env_pause    = 0;
        ay_env_step     = 0x0F;
        break;
    }
}

s16 ay_render(void) {
    u8 incr, noise;
    u16 freq;
    u16 ch_out;
    s16 mix;
    u8 vol_idx, vol_val;

    ay_base_count += ay_base_incr;
    incr = (u8)(ay_base_count >> AY_GETA_BITS);
    ay_base_count &= (1UL << AY_GETA_BITS) - 1;

    if (incr > 0) {
        ay_env_count += incr;
        if (ay_env_freq > 0 && ay_env_count >= ay_env_freq) {
            if (!ay_env_pause) {
                ay_env_step--;
            }
            if (ay_env_step == 0xFF) {
                if (ay_env_hold) {
                    if (ay_env_alternate) ay_env_attack ^= 0x0F;
                    ay_env_pause = 1;
                    ay_env_step = 0;
                } else {
                    if (ay_env_alternate && ay_env_step & 0x10)
                        ay_env_attack ^= 0x0F;
                    ay_env_step = 0x0F;
                }
            }
            if (ay_env_freq >= incr)
                ay_env_count -= ay_env_freq;
            else
                ay_env_count = 0;
        }

        ay_noise_count += incr;
        if (ay_noise_freq > 0 && ay_noise_count >= ay_noise_freq) {
            ay_noise_scaler ^= 1;
            if (ay_noise_scaler) {
                if (ay_noise_seed & 1)
                    ay_noise_seed ^= 0x24000;
                ay_noise_seed >>= 1;
            }
            if (ay_noise_freq >= incr)
                ay_noise_count -= ay_noise_freq;
            else
                ay_noise_count = 0;
        }
    }
    noise = ay_noise_seed & 1;

    mix = 0;

    /* CH0 */
    if (incr > 0) {
        freq = ((u16)ay_freq_hi[0] << 8) | ay_freq_lo[0];
        ay_count[0] += incr;
        if (freq > 0 && ay_count[0] >= freq) {
            ay_edge[0] = !ay_edge[0];
            if (freq >= incr) ay_count[0] -= freq; else ay_count[0] = 0;
        }
    }
    ch_out = 0;
    if ((ay_tmask[0] || ay_edge[0]) && (ay_nmask[0] || noise)) {
        vol_idx = ay_volume[0] & 0x0F;
        if (ay_volume[0] & 0x10) vol_idx = ay_env_step ^ ay_env_attack;
        vol_val = ay_voltbl[vol_idx];
        ch_out = (u16)vol_val << 4;
    }
    mix += (s16)((u16)ch_out >> 4) - 8;

    /* CH1 */
    if (incr > 0) {
        freq = ((u16)ay_freq_hi[1] << 8) | ay_freq_lo[1];
        ay_count[1] += incr;
        if (freq > 0 && ay_count[1] >= freq) {
            ay_edge[1] = !ay_edge[1];
            if (freq >= incr) ay_count[1] -= freq; else ay_count[1] = 0;
        }
    }
    ch_out = 0;
    if ((ay_tmask[1] || ay_edge[1]) && (ay_nmask[1] || noise)) {
        vol_idx = ay_volume[1] & 0x0F;
        if (ay_volume[1] & 0x10) vol_idx = ay_env_step ^ ay_env_attack;
        vol_val = ay_voltbl[vol_idx];
        ch_out = (u16)vol_val << 4;
    }
    mix += (s16)((u16)ch_out >> 4) - 8;

    /* CH2 */
    if (incr > 0) {
        freq = ((u16)ay_freq_hi[2] << 8) | ay_freq_lo[2];
        ay_count[2] += incr;
        if (freq > 0 && ay_count[2] >= freq) {
            ay_edge[2] = !ay_edge[2];
            if (freq >= incr) ay_count[2] -= freq; else ay_count[2] = 0;
        }
    }
    ch_out = 0;
    if ((ay_tmask[2] || ay_edge[2]) && (ay_nmask[2] || noise)) {
        vol_idx = ay_volume[2] & 0x0F;
        if (ay_volume[2] & 0x10) vol_idx = ay_env_step ^ ay_env_attack;
        vol_val = ay_voltbl[vol_idx];
        ch_out = (u16)vol_val << 4;
    }
    mix += (s16)((u16)ch_out >> 4) - 8;

    return mix;
}

u8 ay_channel_mask(void) {
    u8 mask = 0, i;
    for (i = 0; i < AY_CHANS; i++) {
        if (ay_volume[i]) mask |= (1 << i);
    }
    /* noise: reg7 bit5=1 means noise enabled */
    if (ay_reg[7] & 0x20) mask |= 0x08;
    /* envelope: any channel using envelope mode */
    for (i = 0; i < AY_CHANS; i++) {
        if (ay_volume[i] & 0x10) { mask |= 0x10; break; }
    }
    return mask;
}
