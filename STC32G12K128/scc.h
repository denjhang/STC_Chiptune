/* scc.h - SCC (K051649) 仿真核心 (STC32G C251 版, 参考 RPFM) */
#ifndef SCC_H
#define SCC_H

#include "types.h"

#define SCC_CHANS    5
#define SCC_WAVELEN  32
#define SCC_FREQ_BITS 16
/* RPFM 公式: step = ((clock >> 1) << 17) / ((freq+1) * rate)
 * VGM SCC 时钟: 3579545 Hz (内部用 clock >> 1 = 1789772)
 * SCC 渲染率: 8820 Hz
 * SCC_STEP_BASE = (1789772 << 17) / 8820 = 26594592 */
#define SCC_STEP_BASE 26594592UL

void scc_init(void);
void scc_wr(u8 port, u8 dat);
u8 scc_render(void);

#endif
