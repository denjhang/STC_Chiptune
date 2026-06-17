/*---------------------------------------------------------------------*/
/* Phase 5b: PWMB 438Hz + Timer0 ISR 17640Hz + USB CDC 双串口          */
/*---------------------------------------------------------------------*/

#include "stc.h"
#include "usb.h"
#include "uart.h"
#include "timer.h"

unsigned long MAIN_Fosc = 24000000L;
#define SAMPLE_RATE 17640

#define PWMB_ENO1P    0x01

u8 led_val = 0xFE;
static u16 led_tick = 0;

void pwmb_440hz_init(void)
{
    PWMB_ENO   = 0x00;
    PWMB_CCER1 = 0x00;
    PWMB_CCMR1 = 0x68;
    PWMB_CCER1 = 0x05;
    PWMB_ARRH  = 0x00;
    PWMB_ARRL  = 255;
    PWMB_CCR5H = 0x00;
    PWMB_CCR5L = 128;
    PWMB_PSCRH = (213 >> 8);
    PWMB_PSCRL = (213 & 0xFF);
    PWMB_PS    = (PWMB_PS & ~0x03) | 0x02;  /* PS=2 -> P0.0 */
    PWMB_ENO   = PWMB_ENO1P;
    PWMB_BKR   = 0x80;
    PWMB_CR1   = 0x01;
}

/* Timer0: 1T 17640Hz (跟主线一样, 但 ISR 只管流水灯) */
void timer0_init(void)
{
    u32 reload;
    AUXR |= 0x80;
    TMOD &= 0xF0;
    reload = 65536UL - MAIN_Fosc / SAMPLE_RATE;
    TH0 = (u8)(reload >> 8);
    TL0 = (u8)(reload & 0xFF);
    ET0 = 1;
    TR0 = 1;
}

void tm0_isr() interrupt 1
{
    if (++led_tick >= 17640)
    {
        led_tick = 0;
        P2 = led_val;
        led_val = (led_val << 1) | (led_val >> 7);
        if (led_val == 0x7F) led_val = 0xFE;
    }
}

void sys_init(void)
{
    WTST = 0;
    EAXFR = 1;
    CKCON = 0;

    P0M1 = 0x00;   P0M0 = 0x00;
    P1M1 = 0x00;   P1M0 = 0x00;
    P2M1 = 0x00;   P2M0 = 0x00;
    P3M1 = 0x00;   P3M0 = 0x00;   /* P3.0/P3.1 = USB D-/D+ */
    P4M1 = 0x00;   P4M0 = 0x00;
    P5M1 = 0x00;   P5M0 = 0x00;
    P6M1 = 0x00;   P6M0 = 0x00;
    P7M1 = 0x00;   P7M0 = 0x00;

    S3_S = 1;       /* UART3 (P5.0/P5.1) - CDC1 */
    S2_S = 1;       /* UART2 (P4.6/P4.7) - CDC2 */

    P2 = 0xFF;
}

void main(void)
{
    sys_init();
    pwmb_440hz_init();
    timer0_init();
    uart_init();
    usb_init();
    EA = 1;

    while (1)
    {
        uart_polling();
    }
}
