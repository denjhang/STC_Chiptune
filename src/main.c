#include "fw_hal.h"

#define MELODY_LEN 42
#define SINE_LEN   32

/*
 * Sine waveform - high carrier PWM duty modulation
 * Carrier = 11059200 / 1 / 64 = 172.8kHz (ultrasonic, no noise)
 * 32-point sine table, duty 0~63
 * Audio freq = carrier_steps_per_sec / 32
 * Each main loop step: write duty + ~50us delay
 * 32 steps * 50us = 1.6ms per sine cycle = 625Hz base
 */

/* Sine table: duty values 0~63, midpoint=32 */
static uint8_t __code sine_table[SINE_LEN] = {
    32,36,40,44,47,50,53,55,
    56,55,53,50,47,44,40,36,
    32,28,24,20,17,14,11, 9,
     8, 9,11,14,17,20,24,28
};

/* Step delay per note (lower = higher pitch) */
static uint8_t __code note_delay[MELODY_LEN] = {
    60,60,53,53,47,47,53,
    60,60,42,42,37,37,33,
    60,60,53,53,42,42,37,
    60,60,53,42,37,37,33,33,
    60,60,53,53,47,47,53,
    60,60,42,42,37,37,33,
};

static uint8_t __xdata note_idx;

void main(void) {
    GPIO_P3_SetMode(GPIO_Pin_4, GPIO_Mode_Output_PP);
    GPIO_P2_SetMode(GPIO_Pin_0, GPIO_Mode_Output_PP);
    note_idx = 0;

    P_SW2 |= 0x80;

    /* PWMA: period=64, prescaler=0 -> carrier=172.8kHz (ultrasonic) */
    PWMA_ENO  = 0x00;
    PWMA_CCER1 = 0x00;
    PWMA_CCER2 = 0x00;
    PWMA_CCMR1 = 0x68;
    PWMA_CCER1 = 0x05;

    PWMA_ARRH = 0;
    PWMA_ARRL = 63;     /* period=64 */
    PWMA_CCR1H = 0;
    PWMA_CCR1L = 32;    /* 50% start */
    PWMA_PSCRH = 0;
    PWMA_PSCRL = 0;     /* no prescaler, max carrier */

    PWMA_PS = (PWMA_PS & ~0x03) | 0x01;  /* P2.0 */
    PWMA_ENO = 0x01;
    PWMA_BKR = 0x80;
    PWMA_CR1 = 0x01;

    EA = 1;

    while (1) {
        uint8_t i;
        uint8_t delay;
        uint16_t r;

        P34 = 0;

        delay = note_delay[note_idx];
        for (r = 0; r < 500; r++) {
            uint8_t vol;
            /* volume: 16..1 over 500 repeats, decay every ~8 repeats */
            vol = 17 - (uint8_t)(r / 30);
            if (vol > 16) vol = 16;
            if (vol < 1) vol = 1;

            for (i = 0; i < SINE_LEN; i++) {
                uint16_t tmp = (uint16_t)sine_table[i] * vol;
                PWMA_CCR1L = (uint8_t)(tmp >> 4);
                { volatile uint16_t d; for (d = 0; d < delay; d++); }
            }
        }

        P34 = 1;
        { volatile uint32_t w; for (w = 0; w < 15000UL; w++); }

        note_idx++;
        if (note_idx >= MELODY_LEN) note_idx = 0;
    }
}
