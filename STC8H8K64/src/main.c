#include "fw_hal.h"

#define MELODY_LEN 42
#define SINE_LEN   32

/*
 * Sine waveform - 8-bit PWM DAC with volume envelope
 * Carrier = 11059200 / 1 / 256 = 43.2kHz (ultrasonic)
 * 8-bit duty resolution avoids quantization noise at low volume
 * 32-point sine table, duty 0~255
 */

/* Sine table: 8-bit duty values 0~255, midpoint=128 */
static uint8_t __code sine_table[SINE_LEN] = {
    128,144,160,176,188,200,212,220,
    224,220,212,200,188,176,160,144,
    128,112, 96, 80, 68, 56, 44, 36,
     32, 36, 44, 56, 68, 80, 96,112
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

    /* PWMA: period=256, prescaler=0 -> carrier=43.2kHz (ultrasonic, 8-bit) */
    PWMA_ENO  = 0x00;
    PWMA_CCER1 = 0x00;
    PWMA_CCER2 = 0x00;
    PWMA_CCMR1 = 0x68;
    PWMA_CCER1 = 0x05;

    PWMA_ARRH = 0;
    PWMA_ARRL = 255;    /* period=256, 8-bit resolution */
    PWMA_CCR1H = 0;
    PWMA_CCR1L = 128;   /* 50% start */
    PWMA_PSCRH = 0;
    PWMA_PSCRL = 0;

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
            /* volume: 16..1 over 500 repeats */
            vol = 17 - (uint8_t)(r / 30);
            if (vol > 16) vol = 16;
            if (vol < 1) vol = 1;

            for (i = 0; i < SINE_LEN; i++) {
                /* 8-bit * 4-bit -> scale to 0~255, HW MUL */
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
