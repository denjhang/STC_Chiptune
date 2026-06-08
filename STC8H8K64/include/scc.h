#ifndef SCC_H
#define SCC_H

#include "types.h"

#define SCC_CHANS    5
#define SCC_WAVELEN  32
#define SCC_FREQ_BITS 16
#define SCC_STEP_BASE 53084160UL

void scc_init(void);
void scc_wr(u8 port, u8 dat);
u8 scc_render(void);

#endif
