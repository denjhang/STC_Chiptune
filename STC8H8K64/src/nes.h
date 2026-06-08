/* nes.h - NES APU 仿真核心 (无 DMC) */
#ifndef NES_H
#define NES_H

#include "types.h"

/* NES APU clock = 21477272/12 = 1789773 Hz (NTSC)
 * render @ 4410Hz (17640/4), 累加器采样率转换
 * NES_GETA_BITS=24, base_incr = 1789773 * 2^24 / 4410 = 683021612
 * 每 frame ~405 个 APU cycles
 */
#define NES_CLOCK       1789773UL
#define NES_GETA_BITS   24
#define NES_BASE_INCR   683021612UL

void nes_init(void);
void nes_wr(u8 reg, u8 val);
s16 nes_render(void);

#endif
