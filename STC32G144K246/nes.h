/* nes.h - NES APU 仿真核心 (STC32G C251 版) */
#ifndef NES_H
#define NES_H

#include "types.h"

#define NES_CLOCK       1789773UL
#define NES_GETA_BITS   24
#define NES_BASE_INCR   683021612UL

void nes_init(void);
void nes_wr(u8 reg, u8 val);
s16 nes_render(void);

#endif
