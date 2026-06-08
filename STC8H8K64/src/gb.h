/* gb.h - Game Boy DMG 仿真核心 */
#ifndef GB_H
#define GB_H

#include "types.h"

/* GB clock = 4194304 Hz
 * render @ 4410Hz, 累加器基于原始 clock
 * GB_GETA_BITS=16, base_incr = 4194304 * 2^16 / 4410 = 62326579
 * 每帧 ~951 个 clock cycles, 传给 gb_update_state
 */
#define GB_CLOCK        4194304UL
#define GB_GETA_BITS    16
#define GB_BASE_INCR    62326579UL

void gb_init(void);
void gb_wr(u8 reg, u8 val);
s16 gb_render(void);

#endif
