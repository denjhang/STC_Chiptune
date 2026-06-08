/* nes.h - NES APU 仿真核心 (无 DMC) */
#ifndef NES_H
#define NES_H

#include "types.h"

/* NES APU clock = 21477272/12 = 1789773 Hz (NTSC)
 * render @ SAMPLE_RATE (17640), 累加器采样率转换, 和 AY 一样直接渲染
 * NES_GETA_BITS=24, base_incr = 1789773 * 2^24 / 17640 = 1707554030
 * u32 放得下
 * 每 frame ~102 个 APU cycles
 */
#define NES_CLOCK       1789773UL
#define NES_GETA_BITS   24
#define NES_BASE_INCR   1707554030UL

void nes_init(void);
void nes_wr(u8 reg, u8 val);
s16 nes_render(void);

#endif
