/* scc.h - SCC (K051649) 仿真核心 (STC32G C251 版, 对齐 RPFM) */
#ifndef SCC_H
#define SCC_H

/* 不 include stc.h, 由 scc.c 的 #include "stc.h" 提供 u8/u16/s16/s32 */

#define SCC_CHANS       5
#define SCC_WAVELEN     32
#define SCC_FREQ_BITS   16
#define SCC_CLOCK       3579545UL
#define SCC_HALF_CLK    1789772UL
#define SCC_RATE        22050
#define SCC_SHIFT       (SCC_FREQ_BITS + 1)

void scc_init(void);
void scc_wr(u8 port, u8 dat);
s16 scc_render(void);

#endif
