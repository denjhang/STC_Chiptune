/* sn76489.c - SN76489 仿真核心 (精简嵌入式版)
 * 3 方波 + 1 噪声, 10-bit period, 4-bit 音量 (2dB/step)
 * 15-bit LFSR (taps bit0,bit1, feedback bit14)
 * 时钟 /8 分频, period=0 等效 0x400
 * 使用累加器换算采样率 (同 AY 模型)
 */
#include <stc8h.h>
#include "sn76489.h"

#define SN_GETA_BITS 24
/* base_incr = CLK * (1<<24) / 2 / CLK_DIV / SAMPLE_RATE
 * = 3579545 * 16777216 / 2 / 8 / 17640 = 212779193 */
#define SN_BASE_INCR  212779193UL

static u16 xdata sn_reg[8];
static u8  xdata sn_last_reg;
static s16 xdata sn_vol[SN_CHANS];
static u16 xdata sn_period[SN_CHANS];
static u16 xdata sn_count[SN_CHANS];
static u8  xdata sn_output[SN_CHANS];
static u16 xdata sn_rng;
static u32 xdata sn_base_count;

/* 音量表: 2dB/step, 15=静音
 * 缩放到合适范围, vol[0]=255, vol[15]=0 */
static u8 code sn_voltbl[16] = {
    255, 202, 160, 127,
    101,  80,  64,  50,
     40,  32,  25,  20,
     16,  12,   9,   0
};

void sn_init(void) {
    u8 i;
    for (i = 0; i < 8; i++) sn_reg[i] = 0;
    sn_last_reg = 0;
    for (i = 0; i < SN_CHANS; i++) {
        sn_vol[i] = 0;
        sn_period[i] = 0;
        sn_count[i] = 0;
        sn_output[i] = 0;
    }
    sn_rng = 0x4000;
    sn_output[3] = 0;
    sn_base_count = 0;
}

void sn_wr(u8 dat) {
    u8 r, c, n;

    if (dat & 0x80) {
        r = (dat >> 4) & 0x07;
        sn_last_reg = r;
        sn_reg[r] = (sn_reg[r] & 0x3F0) | (dat & 0x0F);
    } else {
        r = sn_last_reg;
        sn_reg[r] = (sn_reg[r] & 0x00F) | ((dat & 0x3F) << 4);
    }

    c = r >> 1;
    switch (r) {
    case 0: case 2: case 4:
        if (sn_reg[r] != 0)
            sn_period[c] = sn_reg[r];
        else
            sn_period[c] = 0x400;
        if (r == 4 && (sn_reg[6] & 0x03) == 0x03)
            sn_period[3] = sn_period[2] << 1;
        break;
    case 1: case 3: case 5: case 7:
        sn_vol[c] = (s16)sn_voltbl[dat & 0x0F];
        break;
    case 6:
        n = sn_reg[6] & 0x03;
        if (n == 3)
            sn_period[3] = sn_period[2] << 1;
        else
            sn_period[3] = 2 << (4 + n);
        sn_rng = 0x4000;
        break;
    }
}

s16 sn_render(void) {
    u8 i, incr;
    s16 mix, out;

    /* 累加器换算采样率 (同 AY) */
    sn_base_count += SN_BASE_INCR;
    incr = (u8)(sn_base_count >> SN_GETA_BITS);
    sn_base_count &= (1UL << SN_GETA_BITS) - 1;

    mix = 0;
    if (incr > 0) {
        for (i = 0; i < 3; i++) {
            sn_count[i] += incr;
            if (sn_period[i] > 0 && sn_count[i] >= sn_period[i]) {
                sn_output[i] ^= 1;
                sn_count[i] -= sn_period[i];
            }
            out = sn_output[i] ? sn_vol[i] : -sn_vol[i];
            mix += out;
        }

        /* noise channel */
        sn_count[3] += incr;
        if (sn_period[3] > 0 && sn_count[3] >= sn_period[3]) {
            if (((sn_rng & 0x01) ? 1 : 0) != (((sn_rng & 0x02) ? 1 : 0) && ((sn_reg[6] & 0x04) != 0)))
            {
                sn_rng >>= 1;
                sn_rng |= 0x4000;
            } else {
                sn_rng >>= 1;
            }
            sn_output[3] = sn_rng & 1;
            sn_count[3] -= sn_period[3];
        }
        out = sn_output[3] ? sn_vol[3] : -sn_vol[3];
        mix += out;
    }

    /* 4 通道各 ±255 → max ±1020, 缩放到 ±128 范围 */
    mix >>= 2;
    return mix;
}
