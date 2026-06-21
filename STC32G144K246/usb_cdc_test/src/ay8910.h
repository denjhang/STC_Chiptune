/* ay8910.h - AY8910 仿真核心 (STC32G C251 版) */
#ifndef AY8910_H
#define AY8910_H

/* 不 include stc.h/types.h, 由 ay8910.c 的 #include "stc.h" 提供 u8/u16/s16 */

#define AY_CHANS    3
#define AY_CLK      1789772UL
#define AY_GETA_BITS 24
#define AY_BASE_INCR   170223307UL

void ay_init(void);
void ay_wr(unsigned char reg, unsigned char val);
signed int ay_render(void);
unsigned char ay_channel_mask(void);

#endif
