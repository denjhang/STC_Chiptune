/* sn76489.c - SN76489 仿真核心 (STC32G C251 版) */
#include "stc.h"
#include "sn76489.h"

#define SN_GETA_BITS 24
#define SN_BASE_INCR  212779193UL

static u16 sn_reg[8];
static u8  sn_last_reg;
static s16 sn_vol[SN_CHANS];
static u16 sn_period[SN_CHANS];
static u16 sn_count[SN_CHANS];
static u8  sn_output[SN_CHANS];
static u32 sn_rng;
static u32 sn_base_count;

static u8  sn_sr_width;
static u16 sn_taps;
static u32 sn_rng_init;

static const u8 sn_voltbl[16] = {
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
    sn_base_count = 0;
    sn_set_variant(SN_VARIANT_SEGAVDP);
}

void sn_set_variant(u8 variant) {
    switch (variant) {
    case SN_VARIANT_SN76489:
        sn_sr_width = 15;
        sn_taps = 0x0003;
        break;
    case SN_VARIANT_SEGAVDP:
    default:
        sn_sr_width = 16;
        sn_taps = 0x0009;
        break;
    case SN_VARIANT_SN76489A:
        sn_sr_width = 17;
        sn_taps = 0x000C;
        break;
    }
    sn_rng_init = 1UL << (sn_sr_width - 1);
    sn_rng = sn_rng_init;
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
            sn_period[3] = sn_period[2];
        break;
    case 1: case 3: case 5: case 7:
        sn_vol[c] = (s16)sn_voltbl[dat & 0x0F];
        break;
    case 6:
        n = sn_reg[6] & 0x03;
        if (n == 3)
            sn_period[3] = sn_period[2];
        else
            sn_period[3] = 0x10 << n;
        sn_rng = sn_rng_init;
        break;
    }
}

s16 sn_render(void) {
    u8 incr;
    s16 mix, out;

    sn_base_count += SN_BASE_INCR;
    incr = (u8)(sn_base_count >> SN_GETA_BITS);
    sn_base_count &= (1UL << SN_GETA_BITS) - 1;

    mix = 0;
    if (incr > 0) {
        /* CH0 */
        sn_count[0] += incr;
        if (sn_period[0] > 0 && sn_count[0] >= sn_period[0]) {
            sn_output[0] ^= 1;
            sn_count[0] -= sn_period[0];
        }
        out = sn_output[0] ? sn_vol[0] : -sn_vol[0];
        mix += out;

        /* CH1 */
        sn_count[1] += incr;
        if (sn_period[1] > 0 && sn_count[1] >= sn_period[1]) {
            sn_output[1] ^= 1;
            sn_count[1] -= sn_period[1];
        }
        out = sn_output[1] ? sn_vol[1] : -sn_vol[1];
        mix += out;

        /* CH2 */
        sn_count[2] += incr;
        if (sn_period[2] > 0 && sn_count[2] >= sn_period[2]) {
            sn_output[2] ^= 1;
            sn_count[2] -= sn_period[2];
        }
        out = sn_output[2] ? sn_vol[2] : -sn_vol[2];
        mix += out;

        /* Noise CH3 */
        sn_count[3] += incr;
        if (sn_period[3] > 0 && sn_count[3] >= sn_period[3]) {
            u8 fb;
            if (sn_reg[6] & 0x04) {
                u16 masked = sn_rng & sn_taps;
                fb = (masked != 0) && (masked != sn_taps);
            } else {
                fb = sn_rng & 1;
            }
            sn_rng >>= 1;
            if (fb)
                sn_rng |= sn_rng_init;
            sn_output[3] = sn_rng & 1;
            sn_count[3] -= sn_period[3];
        }
        out = sn_output[3] ? sn_vol[3] : -sn_vol[3];
        mix += out;
    }

    mix >>= 2;
    return mix;
}

u8 sn_channel_mask(void) {
    u8 mask = 0, i;
    for (i = 0; i < SN_CHANS; i++) {
        if (sn_vol[i]) mask |= (1 << i);
    }
    return mask;
}
