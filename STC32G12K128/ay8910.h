/* ay8910.h - AY8910 仿真核心 (STC32G C251 版) */
#ifndef AY8910_H
#define AY8910_H

#include "types.h"

#define AY_CHANS    3
#define AY_CLK      1789772UL
#define AY_GETA_BITS 24
#define AY_BASE_INCR   212779134UL

void ay_init(void);
void ay_wr(u8 reg, u8 val);
s16 ay_render(void);

#endif
