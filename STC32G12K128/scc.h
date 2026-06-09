/* scc.h - SCC (K051649) 仿真核心 (STC32G C251 版, 参考 RPFM) */
#ifndef SCC_H
#define SCC_H

#include "types.h"

#define SCC_CHANS    5
#define SCC_WAVELEN  32
#define SCC_FREQ_BITS 16
/* RPFM 公式: step = ((clock >> 1) << 17) / ((freq+1) * rate)
 * VGM SCC 时钟: 3579545 Hz (clock >> 1 = 1789772)
 * SCC 渲染率: 17640 Hz
 * 被除数 = 1789772 << 17 = 234588995584 (超出 u32, 用 double) */
#define SCC_CLK_HALF   1789772.0
#define SCC_RATE        17640.0
#define SCC_DIVIDEND    (SCC_CLK_HALF * 131072.0)  /* 234588995584.0 */

void scc_init(void);
void scc_wr(u8 port, u8 dat);
u8 scc_render(void);

#endif
