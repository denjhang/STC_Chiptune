/* gb.h - Game Boy DMG 仿真核心 (STC32G C251 版) */
#ifndef GB_H
#define GB_H

#include "types.h"

#define GB_CLOCK        4194304UL
#define GB_GETA_BITS    16
#define GB_BASE_INCR    973537UL

void gb_init(void);
void gb_wr(u8 reg, u8 val);
s16 gb_render(void);

#endif
