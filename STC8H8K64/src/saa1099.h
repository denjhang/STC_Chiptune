/* saa1099.h - SAA1099 仿真核心 */
#ifndef SAA1099_H
#define SAA1099_H

#include "types.h"

#define SAA_CHANS    6
#define SAA_CLK      7159091UL
#define SAA_CLK_DIV  128

void saa_init(void);
void saa_write_addr(u8 addr);
void saa_write_data(u8 dat);
s16 saa_render(void);

#endif
