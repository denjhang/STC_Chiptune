/* scc.h - SCC (K051649) 仿真核心 */
#ifndef SCC_H
#define SCC_H

#include "types.h"

#define SCC_CHANS       5
#define SCC_WAVELEN     32
#define SCC_FREQ_BITS   16
#define SCC_CLOCK       3579545L

/* 由 main.c 定义采样率 */
#ifndef SCC_RATE
#define SCC_RATE        4410
#endif

#define SCC_HALF_CLK    1789772UL
#define SCC_SHIFT       (SCC_FREQ_BITS + 1)
#define SCC_STEP_BASE   (SCC_HALF_CLK / SCC_RATE * (1UL << SCC_SHIFT))

void scc_init(void);
void scc_wr(u8 port, u8 dat);
u8 scc_render(void);

#endif
