/* nes.c - NES APU 仿真核心 (STC32G C251 版)
 * 4 通道: 2x 方波(包络+扫频), 1x 三角波, 1x 噪声(包络)
 */
#include "STC32G.H"
#include <string.h>
#include "nes.h"

static const u8 nes_vbl_len[32] = {
    10, 254, 20,  2, 40,  4, 80,  6, 160,  8, 60, 10, 14, 12, 26, 14,
    12,  16, 24, 18, 48, 20, 96, 22, 192, 24, 72, 26, 16, 28, 32, 30
};

static const u16 nes_freq_limit[8] = {
    0x3FF, 0x555, 0x666, 0x71C, 0x787, 0x7C1, 0x7E0, 0x7F2
};

static const u16 nes_noise_freq[16] = {
    4, 8, 16, 32, 64, 96, 128, 160, 202, 254, 380, 508, 762, 1016, 2034, 4068
};

static const u8 nes_duty_lut[4] = { 0x40, 0x60, 0x78, 0x9F };

typedef struct {
    u8  regs[4];
    u16 freq;
    u16 phaseacc;
    u8  adder;
    u8  env_vol;
    u16 env_phase;
    u16 sweep_phase;
    u16 vbl_length;
    u8  enabled;
    s8  output;
} NES_SQUARE;

typedef struct {
    u8  regs[4];
    u16 phaseacc;
    u8  adder;
    u16 linear_length;
    u8  linear_reload;
    u8  counter_started;
    u8  write_latency;
    u16 vbl_length;
    u8  enabled;
    s8  output;
} NES_TRI;

typedef struct {
    u8  regs[4];
    u16 lfsr;
    u16 phaseacc;
    u8  env_vol;
    u16 env_phase;
    u16 vbl_length;
    u8  enabled;
    s8  output;
} NES_NOISE;

static NES_SQUARE nes_squ[2];
static NES_TRI nes_tri;
static NES_NOISE nes_noi;
static u8  nes_regs[0x18];
static u32 nes_base_count;
static u16 nes_frame_div;

void nes_init(void) {
    u8 i, j;
    memset(nes_regs, 0, sizeof(nes_regs));
    nes_base_count = 0;
    nes_frame_div = 0;

    for (i = 0; i < 2; i++) {
        for (j = 0; j < 4; j++) nes_squ[i].regs[j] = 0;
        nes_squ[i].freq = 0;
        nes_squ[i].phaseacc = 0;
        nes_squ[i].adder = 0;
        nes_squ[i].env_vol = 0;
        nes_squ[i].env_phase = 0;
        nes_squ[i].sweep_phase = 0;
        nes_squ[i].vbl_length = 0;
        nes_squ[i].enabled = 0;
        nes_squ[i].output = 0;
    }

    for (j = 0; j < 4; j++) nes_tri.regs[j] = 0;
    nes_tri.phaseacc = 0;
    nes_tri.adder = 0;
    nes_tri.linear_length = 0;
    nes_tri.linear_reload = 0;
    nes_tri.counter_started = 0;
    nes_tri.write_latency = 0;
    nes_tri.vbl_length = 0;
    nes_tri.enabled = 0;
    nes_tri.output = 0;

    for (j = 0; j < 4; j++) nes_noi.regs[j] = 0;
    nes_noi.lfsr = 1;
    nes_noi.phaseacc = 0;
    nes_noi.env_vol = 0;
    nes_noi.env_phase = 0;
    nes_noi.vbl_length = 0;
    nes_noi.enabled = 0;
    nes_noi.output = 0;
}

void nes_wr(u8 reg, u8 val) {
    u8 ch;

    if (reg > 0x17) return;
    nes_regs[reg] = val;

    switch (reg) {
    case 0x00: case 0x04:
        ch = (reg >> 2) & 1;
        nes_squ[ch].regs[0] = val;
        break;
    case 0x01: case 0x05:
        ch = (reg >> 2) & 1;
        nes_squ[ch].regs[1] = val;
        break;
    case 0x02: case 0x06:
        ch = (reg >> 2) & 1;
        nes_squ[ch].regs[2] = val;
        if (nes_squ[ch].enabled) {
            nes_squ[ch].freq = ((nes_squ[ch].regs[3] & 7) << 8) + val;
            nes_squ[ch].freq += 1;
        }
        break;
    case 0x03: case 0x07:
        ch = (reg >> 2) & 1;
        nes_squ[ch].regs[3] = val;
        if (nes_squ[ch].enabled) {
            nes_squ[ch].vbl_length = nes_vbl_len[val >> 3];
            nes_squ[ch].env_vol = 0;
            nes_squ[ch].freq = (((val & 7) << 8) + nes_squ[ch].regs[2]) + 1;
        }
        break;

    case 0x08:
        nes_tri.regs[0] = val;
        break;
    case 0x09:
        nes_tri.regs[1] = val;
        break;
    case 0x0A:
        nes_tri.regs[2] = val;
        break;
    case 0x0B:
        nes_tri.regs[3] = val;
        nes_tri.write_latency = 3;
        if (nes_tri.enabled) {
            nes_tri.vbl_length = nes_vbl_len[val >> 3];
            nes_tri.linear_length = (nes_tri.regs[0] & 0x7F) + 1;
            nes_tri.linear_reload = 1;
        }
        break;

    case 0x0C:
        nes_noi.regs[0] = val;
        break;
    case 0x0D:
        nes_noi.regs[1] = val;
        break;
    case 0x0E:
        nes_noi.regs[2] = val;
        break;
    case 0x0F:
        nes_noi.regs[3] = val;
        if (nes_noi.enabled) {
            nes_noi.vbl_length = nes_vbl_len[val >> 3];
            nes_noi.env_vol = 0;
        }
        break;

    case 0x15:
        nes_squ[0].enabled = (val & 0x01) ? 1 : 0;
        if (!(val & 0x01)) nes_squ[0].vbl_length = 0;
        nes_squ[1].enabled = (val & 0x02) ? 1 : 0;
        if (!(val & 0x02)) nes_squ[1].vbl_length = 0;
        nes_tri.enabled = (val & 0x04) ? 1 : 0;
        if (!(val & 0x04)) { nes_tri.vbl_length = 0; nes_tri.linear_length = 0; nes_tri.counter_started = 0; }
        nes_noi.enabled = (val & 0x08) ? 1 : 0;
        if (!(val & 0x08)) nes_noi.vbl_length = 0;
        break;

    case 0x17:
        break;
    }
}

static void nes_update_square(NES_SQUARE *chan, u16 cycles, u8 do_frame) {
    u16 freq;

    if (!chan->enabled) { chan->output = 0; return; }

    if (do_frame && !(chan->regs[0] & 0x20)) {
        if (chan->vbl_length > 0) chan->vbl_length--;
    }
    if (!chan->vbl_length) { chan->output = 0; return; }

    if (do_frame && !(chan->regs[0] & 0x10)) {
        if (chan->regs[0] & 0x20)
            chan->env_vol = (chan->env_vol + 1) & 15;
        else if (chan->env_vol < 15)
            chan->env_vol++;
    }

    freq = ((chan->regs[3] & 7) << 8) + chan->regs[2] + 1;

    if (chan == &nes_squ[0] && (chan->regs[1] & 0x80) && (chan->regs[1] & 7)) {
        u8 sweep_delay = ((chan->regs[1] >> 4) & 7) + 1;
        if (do_frame) {
            chan->sweep_phase++;
            if (chan->sweep_phase >= sweep_delay) {
                chan->sweep_phase = 0;
                if (chan->regs[1] & 8)
                    freq -= freq >> (chan->regs[1] & 7);
                else
                    freq += freq >> (chan->regs[1] & 7);
            }
        }
    }

    if (freq < 4 || freq > nes_freq_limit[chan->regs[1] & 7]) {
        chan->output = 0;
        return;
    }

    chan->phaseacc += cycles;
    while (chan->phaseacc >= freq) {
        chan->phaseacc -= freq;
        chan->adder = (chan->adder + 1) & 0x0F;
    }

    {
        u8 duty = nes_duty_lut[chan->regs[0] >> 6];
        u8 vol;
        if (chan->regs[0] & 0x10)
            vol = chan->regs[0] & 0x0F;
        else
            vol = 0x0F - chan->env_vol;

        if (duty & (1 << (7 - (chan->adder >> 1))))
            chan->output = vol;
        else
            chan->output = -vol;
    }
}

static void nes_update_tri(NES_TRI *chan, u16 cycles, u8 do_frame) {
    u16 freq;

    if (!chan->enabled) { chan->output = 0; return; }

    if (do_frame) {
        if (!chan->counter_started) {
            if (chan->write_latency > 0) chan->write_latency--;
            if (chan->write_latency == 0) chan->counter_started = 1;
        }

        if (chan->counter_started) {
            if (chan->linear_reload)
                chan->linear_length = (chan->regs[0] & 0x7F) + 1;
            else if (chan->linear_length > 0)
                chan->linear_length--;

            if (!(chan->regs[0] & 0x80))
                chan->linear_reload = 0;

            if (chan->vbl_length > 0 && !(chan->regs[0] & 0x80))
                chan->vbl_length--;
        }
    }

    if (!chan->linear_length || !chan->vbl_length) { chan->output = 0; return; }

    freq = ((chan->regs[3] & 7) << 8) + chan->regs[2] + 1;
    if (freq < 4) { chan->output = 0; return; }

    chan->phaseacc += cycles;
    while (chan->phaseacc >= freq) {
        chan->phaseacc -= freq;
        chan->adder = (chan->adder + 1) & 0x1F;

        chan->output = chan->adder & 0x0F;
        if (chan->adder & 8)
            chan->output ^= 0x07;
        else
            chan->output ^= 0x08;
        if (chan->adder & 0x10)
            chan->output ^= 0x0F;
        chan->output = (chan->output << 1) - 0x10;
    }
}

static void nes_update_noise(NES_NOISE *chan, u16 cycles, u8 do_frame) {
    u16 freq;
    u8 vol;

    if (!chan->enabled) { chan->output = 0; return; }

    if (do_frame) {
        if (!(chan->regs[0] & 0x20)) {
            if (chan->vbl_length > 0) chan->vbl_length--;
        }
        if (!(chan->regs[0] & 0x10)) {
            if (chan->regs[0] & 0x20)
                chan->env_vol = (chan->env_vol + 1) & 15;
            else if (chan->env_vol < 15)
                chan->env_vol++;
        }
    }

    if (!chan->vbl_length) { chan->output = 0; return; }

    freq = nes_noise_freq[chan->regs[2] & 0x0F];

    chan->phaseacc += cycles;
    while (chan->phaseacc >= freq) {
        chan->phaseacc -= freq;
        {
            u16 fb = ((chan->lfsr & 1) ^ ((chan->lfsr >> ((chan->regs[2] & 0x80) ? 6 : 1)) & 1));
            chan->lfsr = (chan->lfsr >> 1) | (fb << 14);
        }
    }

    if (chan->regs[0] & 0x10)
        vol = chan->regs[0] & 0x0F;
    else
        vol = 0x0F - chan->env_vol;

    chan->output = (chan->lfsr & 1) ? vol : -vol;
}

s16 nes_render(void) {
    u16 cycles;
    s16 mix;
    u8 do_frame = 0;

    nes_base_count += NES_BASE_INCR;
    cycles = (u16)(nes_base_count >> NES_GETA_BITS);
    nes_base_count &= (1UL << NES_GETA_BITS) - 1;

    nes_frame_div++;
    if (nes_frame_div >= 74) {
        nes_frame_div = 0;
        do_frame = 1;
    }

    if (cycles > 0) {
        nes_update_square(&nes_squ[0], cycles, do_frame);
        nes_update_square(&nes_squ[1], cycles, do_frame);
        nes_update_tri(&nes_tri, cycles, do_frame);
        nes_update_noise(&nes_noi, cycles, do_frame);
    }

    mix = (s16)nes_squ[0].output + nes_squ[1].output;
    mix += (s16)(nes_tri.output * 3 >> 2);
    mix += (s16)(nes_noi.output * 3 >> 2);

    mix = mix * 4;
    return mix;
}
