#ifndef SCC_H
#define SCC_H

#include <stdint.h>

#define SCC_CHANS   5
#define SCC_WAVELEN 32
#define SCC_FREQ_BITS 16

typedef struct {
    uint32_t counter;
    uint16_t frequency;
    uint8_t  volume;
    uint8_t  key;
    int8_t   waveram[SCC_WAVELEN];
} scc_channel_t;

typedef struct {
    scc_channel_t ch[SCC_CHANS];
    uint32_t rate;
    uint32_t clock_factor;  /* precomputed: (clock/2) << (FREQ_BITS+1) */
    uint8_t  mode_plus;
    uint8_t  test;
    uint8_t  cur_reg;
} scc_state_t;

void scc_init(scc_state_t *s, uint32_t clock_hz);
void scc_reset(scc_state_t *s);
void scc_write(scc_state_t *s, uint8_t port, uint8_t data);
int8_t scc_render(scc_state_t *s);

#endif
