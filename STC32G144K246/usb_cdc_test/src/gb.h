/* gb.h - GameBoy DMG APU 仿真核心 (STC32G C251 版, ISR 极致优化)
 * 对齐 libvgm emu/cores/gb.c (Wilbert Pol, Anthony Kruize, BSD-3-Clause)
 * 4 通道: 2x方波(1带扫频) + 32步自定义波形 + 噪声(AY风格简化)
 *
 * ISR 优化要点 (对齐 NES/AY/SN/SCC 模式, 详见 docs GB_INTEGRATION_STATUS.md §13):
 * - frame sequencer 除法 >>13 (FRAME_CYCLES=8192=2^13)
 * - noise 改 AY 风格 Galois LFSR (单次 if 代替 while 循环)
 * - 热路径变量 data 段直接寻址
 * - square distance 预计算, cycles_left 用 s16
 * - frame sequencer 跨 frame 单次 update (不双倍调用) */
#ifndef GB_H
#define GB_H

/* 不 include stc.h, 由 gb.c 的 #include "stc.h" 提供 u8/u16/s32 等 */

/* GB 主时钟 4.194304 MHz, 24-bit 累加器归一化到 22050Hz 采样率.
 * base_incr = 4194304 × 2^24 / 22050 = 3191326266 (超 LONG_MAX 但 u32 内) */
#define GB_CLOCK        4194304UL
#define GB_GETA_BITS    24
#define GB_BASE_INCR    3191326266UL

void gb_init(void);
void gb_wr(u8 reg, u8 val);
s16  gb_render(void);

#endif
