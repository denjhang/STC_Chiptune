/* saa1099.c - SAA1099 仿真核心 (STC32G C251 版)
 * 6 方波 + 2 噪声 + 2 包络, 18-bit LFSR
 */
#include "STC32G.H"
#include <string.h>
#include "saa1099.h"

#define SAA_GETA_BITS 24
#define SAA_BASE_INCR  212779223UL

#define ENV_LOAD 0x80
#define ENV_STAY 0x40

static const u8 saa_env_tbl[8][32] = {
    {0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0xC0,
     0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0xC0},
    {0xF,0xF,0xF,0xF,0xF,0xF,0xF,0xF,0xF,0xF,0xF,0xF,0xF,0xF,0xF,0x8F,
     0xF,0xF,0xF,0xF,0xF,0xF,0xF,0xF,0xF,0xF,0xF,0xF,0xF,0xF,0xF,0x8F},
    {0xF,0xE,0xD,0xC,0xB,0xA,0x9,0x8,0x7,0x6,0x5,0x4,0x3,0x2,0x1,0xC0,
     0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0xC0},
    {0xF,0xE,0xD,0xC,0xB,0xA,0x9,0x8,0x7,0x6,0x5,0x4,0x3,0x2,0x1,0x80,
     0xF,0xE,0xD,0xC,0xB,0xA,0x9,0x8,0x7,0x6,0x5,0x4,0x3,0x2,0x1,0x80},
    {0x0,0x1,0x2,0x3,0x4,0x5,0x6,0x7,0x8,0x9,0xA,0xB,0xC,0xD,0xE,0xF,
     0xF,0xE,0xD,0xC,0xB,0xA,0x9,0x8,0x7,0x6,0x5,0x4,0x3,0x2,0x1,0xC0},
    {0x0,0x1,0x2,0x3,0x4,0x5,0x6,0x7,0x8,0x9,0xA,0xB,0xC,0xD,0xE,0xF,
     0xF,0xE,0xD,0xC,0xB,0xA,0x9,0x8,0x7,0x6,0x5,0x4,0x3,0x2,0x1,0x80},
    {0x0,0x1,0x2,0x3,0x4,0x5,0x6,0x7,0x8,0x9,0xA,0xB,0xC,0xD,0xE,0x8F,
     0xC0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0xC0},
    {0x0,0x1,0x2,0x3,0x4,0x5,0x6,0x7,0x8,0x9,0xA,0xB,0xC,0xD,0xE,0x8F,
     0x0,0x1,0x2,0x3,0x4,0x5,0x6,0x7,0x8,0x9,0xA,0xB,0xC,0xD,0xE,0x8F}
};

static const u8 saa_voltbl[16] = {
      0,  8, 17, 25, 34, 42, 51, 59,
     68, 76, 85, 93, 102, 110, 119, 127
};

static u8  saa_vol[6];
static u8  saa_freq[6];
static u8  saa_oct[6];
static u8  saa_tone_on;
static u8  saa_noise_on;
static u8  saa_state[6];
static s16 saa_fcount[6];
static s16 saa_flimit[6];

static u32 saa_nstate[2];
static u8  saa_nmode[2];
static s16 saa_ncnt[2];
static s16 saa_nlimit[2];

static u8  saa_env_en[2];
static u8  saa_env_rld[2];
static u8  saa_env_ext[2];
static u8  saa_env_step2[2];
static u8  saa_env_wave[2];
static u8  saa_env_pos[2];
static u8  saa_env_flags[2];
static u8  saa_env_vol[2];

static u8  saa_all_on;
static u8  saa_fg_rst;
static u8  saa_addr;
static u8  saa_regs[0x20];
static u32 saa_base_cnt;

static void saa_env_load(u8 gen) {
    u8 data_;
    data_ = saa_regs[0x18 | gen];
    saa_env_ext[gen] = (data_ >> 5) & 1;
    saa_env_wave[gen] = (data_ >> 1) & 7;
    saa_env_pos[gen] = 0;
    saa_env_rld[gen] = 0;
    if (!saa_env_en[gen]) {
        saa_env_flags[gen] = ENV_LOAD | ENV_STAY;
        saa_env_vol[gen] = 0x10;
    }
}

static void saa_env_step_fn(u8 gen) {
    u8 wdata;
    if (!saa_env_en[gen]) return;
    wdata = saa_env_tbl[saa_env_wave[gen]][saa_env_pos[gen]];
    saa_env_flags[gen] = wdata & 0xF0;
    saa_env_vol[gen] = wdata & 0x0F;
    if (!(saa_env_flags[gen] & ENV_STAY)) {
        saa_env_pos[gen] = (saa_env_pos[gen] + 1) & 0x1F;
    }
    if (saa_env_step2[gen]) {
        wdata = saa_env_tbl[saa_env_wave[gen]][saa_env_pos[gen]];
        saa_env_flags[gen] |= wdata & 0xF0;
        saa_env_vol[gen] &= ~0x01;
        if (!(saa_env_flags[gen] & ENV_STAY)) {
            saa_env_pos[gen] = (saa_env_pos[gen] + 1) & 0x1F;
        }
    }
}

void saa_init(void) {
    u8 i;
    for (i = 0; i < 6; i++) {
        saa_vol[i] = 0;
        saa_freq[i] = 0;
        saa_oct[i] = 0;
        saa_state[i] = 0;
        saa_fcount[i] = 0;
        saa_flimit[i] = 0x1FF;
    }
    for (i = 0; i < 2; i++) {
        saa_nstate[i] = 0xFFFFFFFF;
        saa_nmode[i] = 0;
        saa_ncnt[i] = 0;
        saa_nlimit[i] = 1;
        saa_env_en[i] = 0;
        saa_env_rld[i] = 0;
        saa_env_pos[i] = 0;
        saa_env_flags[i] = ENV_LOAD | ENV_STAY;
        saa_env_vol[i] = 0x10;
    }
    saa_all_on = 0;
    saa_fg_rst = 0;
    saa_addr = 0;
    saa_tone_on = 0;
    saa_noise_on = 0;
    saa_base_cnt = 0;
    memset(saa_regs, 0, sizeof(saa_regs));
}

void saa_write_addr(u8 addr) {
    saa_addr = addr & 0x1F;
    if (saa_addr == 0x18 || saa_addr == 0x19) {
        u8 gen = saa_addr & 1;
        if (saa_env_ext[gen]) {
            if ((saa_env_flags[gen] & ENV_LOAD) && saa_env_rld[gen])
                saa_env_load(gen);
            saa_env_step_fn(gen);
        }
    }
}

void saa_write_data(u8 data_) {
    u8 ch, gen, prev;
    saa_regs[saa_addr] = data_;

    if (saa_addr <= 5) {
        saa_vol[saa_addr] = ((data_ & 0x0F) + ((data_ >> 4) & 0x0F) + 1) >> 1;
    }
    else if (saa_addr >= 8 && saa_addr <= 0x0D) {
        ch = saa_addr & 7;
        saa_freq[ch] = data_;
        saa_flimit[ch] = data_ ^ 0x1FF;
    }
    else if (saa_addr >= 0x10 && saa_addr <= 0x12) {
        ch = (saa_addr & 3) << 1;
        saa_oct[ch] = data_ & 7;
        saa_oct[ch | 1] = (data_ >> 4) & 7;
    }
    else if (saa_addr == 0x14) {
        saa_tone_on = data_;
    }
    else if (saa_addr == 0x15) {
        saa_noise_on = data_;
    }
    else if (saa_addr == 0x16) {
        saa_nmode[0] = data_ & 3;
        saa_nmode[1] = (data_ >> 4) & 3;
        for (gen = 0; gen < 2; gen++) {
            if (saa_nmode[gen] == 3)
                saa_nlimit[gen] = 1;
            else
                saa_nlimit[gen] = 1 << saa_nmode[gen];
            saa_ncnt[gen] = 0;
        }
    }
    else if (saa_addr == 0x18 || saa_addr == 0x19) {
        gen = saa_addr & 1;
        prev = saa_env_en[gen];
        saa_env_en[gen] = (data_ >> 7) & 1;
        saa_env_step2[gen] = (data_ >> 4) & 1;
        saa_env_rld[gen] = 1;
        if (!saa_env_en[gen] || !prev) {
            saa_env_load(gen);
            saa_env_step_fn(gen);
        }
    }
    else if (saa_addr == 0x1C) {
        saa_all_on = data_ & 1;
        prev = saa_fg_rst;
        saa_fg_rst = (data_ >> 1) & 1;
        if (saa_fg_rst) {
            for (ch = 0; ch < 6; ch++) {
                saa_fcount[ch] = 0;
                saa_state[ch] = 0;
            }
        }
        else if (prev) {
            for (ch = 0; ch < 6; ch++)
                saa_state[ch] = 1;
        }
    }
}

s16 saa_render(void) {
    u8 ch, gen, incr;
    s16 mix, out;
    u8 vol, t_on, n_on, ns, ostate;
    u16 inc;

    saa_base_cnt += SAA_BASE_INCR;
    incr = (u8)(saa_base_cnt >> SAA_GETA_BITS);
    saa_base_cnt &= (1UL << SAA_GETA_BITS) - 1;

    mix = 0;
    if (!saa_all_on || incr == 0) return 0;

    if (!saa_fg_rst) {
        for (ch = 0; ch < 6; ch++) {
            saa_fcount[ch] -= (s16)((u16)incr << saa_oct[ch]);
            if (saa_fcount[ch] < 0) {
                saa_fcount[ch] += saa_flimit[ch];
                saa_state[ch] ^= 1;
            }
        }
    }

    for (gen = 0; gen < 2; gen++) {
        ch = gen * 3;
        if (saa_nmode[gen] == 3)
            inc = (saa_fcount[ch] < 0) ? 1 : 0;
        else
            inc = incr;
        saa_ncnt[gen] -= (s16)inc;
        if (saa_ncnt[gen] < 0) {
            saa_ncnt[gen] += saa_nlimit[gen];
            if ((!((saa_nstate[gen] >> 17) & 1)) != (!((saa_nstate[gen] >> 10) & 1)))
                saa_nstate[gen] = (saa_nstate[gen] << 1) | 1;
            else
                saa_nstate[gen] <<= 1;
        }
    }

    for (gen = 0; gen < 2; gen++) {
        ch = gen * 3 + 1;
        if (!saa_env_ext[gen] && saa_fcount[ch] < 0) {
            if ((saa_env_flags[gen] & ENV_LOAD) && saa_env_rld[gen])
                saa_env_load(gen);
            saa_env_step_fn(gen);
        }
    }

    for (ch = 0; ch < 6; ch++) {
        gen = ch / 3;
        t_on = (saa_tone_on >> ch) & 1;
        n_on = (saa_noise_on >> ch) & 1;
        ns = saa_nstate[gen] & 1;

        if (t_on && n_on) {
            ostate = saa_state[ch];
            if (saa_state[ch])
                ostate += ns;
        } else {
            ostate = t_on ? saa_state[ch] : 1;
            ostate &= n_on ? ns : 1;
            ostate <<= 1;
        }
        out = (s16)ostate - 1;

        if ((ch == 2 || ch == 5) && saa_env_en[gen]) {
            vol = (u8)((u16)saa_voltbl[saa_vol[ch] & 0x0E] * saa_env_vol[gen] >> 4);
        } else {
            vol = saa_voltbl[saa_vol[ch]];
        }
        mix += out * (s16)vol;
    }

    mix >>= 3;
    if (mix > 127) mix = 127;
    if (mix < -128) mix = -128;
    return mix;
}
