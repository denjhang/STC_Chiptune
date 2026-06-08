/* gb.h - Game Boy DMG 仿真核心 */
#ifndef GB_H
#define GB_H

#include "types.h"

/* GB clock = 4194304 Hz, tick = clock/64 = 65536 Hz
 * render @ 4410Hz, 累加器基于 tick rate (65536Hz)
 * GB_GETA_BITS=16, base_incr = 65536 * 2^16 / 4410 = 973537
 * 每帧 ~15 个 tick, 每个 tick = 64 clock cycles
 * 每次 tick 只传 64 cycles 给通道更新 (和 libvgm 一致)
 */
#define GB_CLOCK        4194304UL
#define GB_GETA_BITS    16
#define GB_BASE_INCR    973537UL

void gb_init(void);
void gb_wr(u8 reg, u8 val);
s16 gb_render(void);

#endif
