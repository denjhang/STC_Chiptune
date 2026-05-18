#include "fw_hal.h"
#include "scc.h"
#include "uart.h"
#include "pwm_audio.h"

#define BAUD_RATE 115200UL

static scc_state_t __xdata scc;
static uint8_t __xdata rx_state;
static uint8_t __xdata rx_buf[2];

void uart1_isr(void) __interrupt(4) {
    if (RI) {
        RI = 0;
        rx_buf[rx_state++] = SBUF;
        if (rx_state >= 2) {
            scc_write(&scc, rx_buf[0], rx_buf[1]);
            rx_state = 0;
        }
    }
    if (TI) {
        TI = 0;
    }
}

void timer3_isr(void) __interrupt(19) {
    int8_t sample = scc_render(&scc);
    pwm_audio_set_sample(sample);
}

void main(void) {
    rx_state = 0;
    uart_init(BAUD_RATE);
    scc_init(&scc, __CONF_FOSC);
    pwm_audio_init(44100);
    EA = 1;

    while (1) {
    }
}
