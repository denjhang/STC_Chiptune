/* scc.c - SCC (K051649) 仿真核心 (STC32G C251 版, 对齐 RPFM) */
#include "stc.h"
#include "scc.h"

/* ISR 热路径: data */
static u32 data scc_cnt[SCC_CHANS];
static u32 data scc_step_val[SCC_CHANS];
static u8  data scc_vol[SCC_CHANS];
static u8  data scc_key[SCC_CHANS];
/* 非热路径: xdata */
static u16 xdata scc_freq[SCC_CHANS];
static s8  xdata scc_wav[SCC_CHANS][SCC_WAVELEN];  /* int8 带符号, 对齐 RPFM */
static u8  xdata scc_creg;
static u8  xdata scc_tst;

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
    u8 off, chi;

    if (port & 1) {
        switch (port >> 1) {
        case 0:
        case 4:
            off = scc_creg;
            if (scc_tst & 0x40) return;
            /* SCC (非 SCC+) 模式: offset 0x60-0x7F 同时写 ch3 + ch4 (硬件共享波表) */
            if (off >= 0x60) {
                scc_wav[3][off & 0x1f] = (s8)dat;
                scc_wav[4][off & 0x1f] = (s8)dat;
            } else {
                scc_wav[off >> 5][off & 0x1f] = (s8)dat;
            }
            break;
        case 1:
            off = scc_creg;
            chi = off >> 1;
            if (chi < SCC_CHANS) {
                if (off & 1)
                    scc_freq[chi] = (scc_freq[chi] & 0x00FF) | ((u16)(dat & 0x0F) << 8);
                else
                    scc_freq[chi] = (scc_freq[chi] & 0x0F00) | dat;
                /* 切频时重置相位低 16 位 (对齐 RPFM, 避免相位不连续咔哒声) */
                scc_cnt[chi] &= 0xFFFF0000u;
                if (scc_tst & 0x20) {
                    scc_cnt[chi] = 0xFFFFFFFFu;
                } else if (scc_freq[chi] < 9) {
                    scc_cnt[chi] |= 0x0000FFFFu;
                    scc_step_val[chi] = 0;
                } else {
                    /* 双精度等价 RPFM 的 64-bit 整数除法:
                     * ((clock/2 << 17) / ((freq+1) * rate))
                     * 分子 1789772*131072=2^37.77 在 double 52-bit 尾数内完全精确 */
                    scc_step_val[chi] = (u32)(
                        ((double)SCC_HALF_CLK * (double)(1UL << SCC_SHIFT)) /
                        ((double)(scc_freq[chi] + 1) * (double)SCC_RATE)
                    );
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

s16 scc_render(void) {
    s16 mix, tmp;
    s16 wav;
    s16 vol_s;
    u8 i, offs;

    mix = 0;
    for (i = 0; i < SCC_CHANS; i++) {
        if (scc_step_val[i] > 0) {
            scc_cnt[i] += scc_step_val[i];
            if (scc_key[i]) {
                offs = (u8)(scc_cnt[i] >> SCC_FREQ_BITS) & 0x1F;
                /* 全 signed 运算, 避免 s16*u16 被 C 提升为 unsigned 导致符号丢失 */
                wav = (s16)scc_wav[i][offs];
                vol_s = (s16)scc_vol[i];
                tmp = (wav * vol_s) >> 4;  /* vol 0-15 缩放 */
                mix += tmp;
            }
        }
    }
    return mix;
}
