/* sn76489.h - SN76489 仿真核心 */
#ifndef SN76489_H
#define SN76489_H

#include "types.h"

#define SN_CHANS    4
#define SN_CLK      3579545UL
#define SN_CLK_DIV  8

void sn_init(void);
void sn_wr(u8 dat);
s16 sn_render(void);

#endif
