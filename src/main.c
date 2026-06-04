#include "fw_hal.h"

#define MELODY_LEN 42

/*
 * Twinkle Twinkle Little Star - PWMA on P2.0
 * Fpwm = 11059200 / 24 / (period+1)
 * G4=392->1176, A4=440->1047, B4=494->933
 * E4=330->1396, D4=294->1567, C4=262->1759
 * No timer ISR - switch notes in main loop with LED blink
 */
static uint16_t __code melody[MELODY_LEN] = {
    1176,1176,1047,1047,933,933,1047,
    1176,1176,1396,1396,1567,1567,1759,
    1176,1176,1047,1047,1396,1396,1567,
    1176,1176,1047,1396,1567,1567,1759,1759,
    1176,1176,1047,1047,933,933,1047,
    1176,1176,1396,1396,1567,1567,1759,
};

static uint8_t __xdata note_idx;
static uint16_t __xdata period;

static void set_note(uint16_t per) {
    PWMA_ARRH = (uint8_t)(per >> 8);
    PWMA_ARRL = (uint8_t)(per);
    PWMA_CCR1H = (uint8_t)((per / 2) >> 8);
    PWMA_CCR1L = (uint8_t)(per / 2);
}

void main(void) {
    GPIO_P3_SetMode(GPIO_Pin_4, GPIO_Mode_Output_PP);
    GPIO_P2_SetMode(GPIO_Pin_0, GPIO_Mode_Output_PP);
    note_idx = 0;

    P_SW2 |= 0x80;

    /* PWMA init */
    PWMA_ENO = 0x00;
    PWMA_CCER1 = 0x00;
    PWMA_CCER2 = 0x00;
    PWMA_CCMR1 = 0x68;
    PWMA_CCER1 = 0x05;

    PWMA_PSCRH = 0;
    PWMA_PSCRL = 23;
    PWMA_PS = (PWMA_PS & ~0x03) | 0x01;

    period = melody[0];
    set_note(period);

    PWMA_ENO = 0x01;
    PWMA_BKR = 0x80;
    PWMA_CR1 = 0x01;

    EA = 1;

    while (1) {
        P34 = 0;
        { volatile uint32_t i; for (i = 0; i < 30000UL; i++); }
        P34 = 1;
        { volatile uint32_t i; for (i = 0; i < 30000UL; i++); }

        /* Switch note every LED blink (~1s) */
        note_idx++;
        if (note_idx >= MELODY_LEN) note_idx = 0;
        period = melody[note_idx];
        set_note(period);
    }
}
