/* sn76489.h - SN76489 仿真核心 */
#ifndef SN76489_H
#define SN76489_H

#include "types.h"

#define SN_CHANS    4
#define SN_CLK      3579545UL
#define SN_CLK_DIV  16

/* 变体选择 */
#define SN_VARIANT_SN76489    0   /* 原版 TI: taps=0x03, SRWidth=15 */
#define SN_VARIANT_SEGAVDP    1   /* Sega VDP: taps=0x09, SRWidth=16 */
#define SN_VARIANT_SN76489A   2   /* Rev.A: taps=0x0C, SRWidth=17 */

void sn_init(void);
void sn_set_variant(u8 variant);
void sn_wr(u8 dat);
s16 sn_render(void);

#endif
