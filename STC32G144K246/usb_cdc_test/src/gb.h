/* gb.h - GameBoy DMG APU 仿真核心 (STC32G C251 版)
 * 对齐 libvgm emu/cores/gb.c (Wilbert Pol, Anthony Kruize, BSD-3-Clause)
 * 4 通道: 2x方波(1带扫频) + 32步自定义波形 + 噪声(LFSR)
 */
#ifndef GB_H
#define GB_H

/* 不 include stc.h, 由 gb.c 的 #include "stc.h" 提供 u8/u16/s32 等 */

/* GB 主时钟 4.194304 MHz, 每 64 cycles 推进一个 GB-cycle 单位 (freq_counter 用)
 * 通过 24-bit 累加器把 GB-clock cycles 归一化到 22050Hz 采样率。
 * base_incr = 4194304 × 2^24 / 22050 = 3191326266 (用 UL, 超 LONG_MAX 但 u32 内) */
#define GB_CLOCK        4194304UL
#define GB_GETA_BITS    24
#define GB_BASE_INCR    3191326266UL

#define GB_DMG_MODE     0
#define GB_CGB_MODE     1

void gb_init(void);
void gb_wr(u8 reg, u8 val);
s16  gb_render(void);

#endif
