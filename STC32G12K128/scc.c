/* scc.c - SCC (K051649) 仿真核心 (STC32G C251 版)
 * 参考 RPFM emu/scc.c 优化版 */
#include "STC32G.H"
#include "scc.h"

static u32 scc_cnt[SCC_CHANS];
static u32 scc_step_val[SCC_CHANS];
static u8  scc_vol[SCC_CHANS];
static u8  scc_key[SCC_CHANS];
static u16 scc_freq[SCC_CHANS];
static u8  scc_wav[SCC_CHANS][SCC_WAVELEN];
static u8  scc_creg;
static u8  scc_tst;

void scc_init(void) {
    u8 i, j;
    for (i = 0; i < SCC_CHANS; i++) {
        scc_cnt[i] = 0;
        scc_freq[i] = 0;
        scc_step_val[i] = 0;
        scc_vol[i] = 0;
        scc_key[i] = 0;
        for (j = 0; j < SCC_WAVELEN; j++)
            scc_wav[i][j] = 0;
    }
    scc_creg = 0;
    scc_tst = 0;
}

void scc_wr(u8 port, u8 dat) {
    u8 off, chi, hi, lo;

    if (port & 1) {
        switch (port >> 1) {
        case 0:
        case 4:
            off = scc_creg;
            if (scc_tst & 0x40) return;
            scc_wav[off >> 5][off & 0x1f] = dat;
            break;
        case 1:
            off = scc_creg;
            chi = off >> 1;
            if (chi < SCC_CHANS) {
                if (off & 1) {
                    hi = dat & 0x0F;
                    lo = scc_freq[chi] & 0xFF;
                    scc_freq[chi] = ((u16)hi << 8) | lo;
                } else {
                    hi = scc_freq[chi] & 0x0F00;
                    scc_freq[chi] = hi | dat;
                }
                /* RPFM 步进: step = (1789772 << 17) / ((freq+1) * 8820) */
                {
                    u32 f = (u32)scc_freq[chi] + 1;
                    scc_step_val[chi] = (u32)(SCC_DIVIDEND / (f * SCC_RATE));
                }
            }
            break;
        case 2:
            chi = scc_creg & 0x07;
            if (chi < SCC_CHANS)
                scc_vol[chi] = dat & 0x0F;
            break;
        case 3:
            for (chi = 0; chi < SCC_CHANS; chi++)
                scc_key[chi] = (dat >> chi) & 1;
            break;
        case 5:
            scc_tst = dat;
            break;
        default:
            break;
        }
    } else {
        scc_creg = dat;
    }
}

u8 scc_render(void) {
    s16 mix;
    u8 i;
    u8 vol, offs, b;
    s16 tmp;

    mix = 0;
    for (i = 0; i < SCC_CHANS; i++) {
        if (scc_step_val[i] > 0) {
            scc_cnt[i] += scc_step_val[i];
            if (scc_key[i]) {
                /* RPFM: offs = (counter >> SCC_FREQ_BITS) & 0x1F */
                offs = (u8)(scc_cnt[i] >> SCC_FREQ_BITS) & 0x1F;
                vol = scc_vol[i];
                b = scc_wav[i][offs];
                /* 8-bit 波形转换为有符号，乘音量，右移 4 位 */
                if (b >= 128)
                    tmp = -(((s16)(256 - (u16)b) * (u16)vol) >> 4);
                else
                    tmp = ((s16)(u16)b * (u16)vol) >> 4;
                mix += tmp;
            }
        }
    }
    if (mix > 127) mix = 127;
    if (mix < -128) mix = -128;
    return 128 + (u8)mix;
}
