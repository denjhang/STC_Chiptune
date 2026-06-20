/* nes.h - NES APU 仿真核心 (STC32G C251 版) */
#ifndef NES_H
#define NES_H

/* 不 include stc.h, 由 nes.c 的 #include "stc.h" 提供 u8/u16/s16/s32 */

#define NES_GETA_BITS   24
#define NES_RATE        17640.0   /* 采样率, 用于 set_clock 计算 base_incr */

void nes_init(void);
void nes_wr(u8 reg, u8 val);
void nes_set_clock(u32 clock_hz);  /* vgm_player 读 VGM header 0x84 传入 */
s16 nes_render(void);

#endif
