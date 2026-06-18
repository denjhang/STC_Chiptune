/*---------------------------------------------------------------------*/
/* Phase 5b: PWMB 438Hz + Timer0 ISR 17640Hz + USB CDC 双串口          */
/*---------------------------------------------------------------------*/

#include "stc.h"
#include "usb.h"
#include "uart.h"
#include "timer.h"
#include "ay8910.h"

unsigned long MAIN_Fosc = 24000000L;
#define SAMPLE_RATE 17640

#define PWMB_ENO1P    0x01

u8 led_val = 0xFE;
static u16 led_tick = 0;

static u16 test_cnt = 0;
static u8 test_active = 0;
static u8 ay_active = 0;
#define BOOT_NOTE_TICKS 35280  /* 2 秒 (17640 * 2) */

void pwmb_dac_init(void)  /* 改名: 不再是固定 440Hz, 而是 8-bit DAC */
{
    PWMB_ENO   = 0x00;
    PWMB_CCER1 = 0x00;
    PWMB_CCMR1 = 0x68;
    PWMB_CCER1 = 0x05;
    PWMB_ARRH  = 0x00;
    PWMB_ARRL  = 255;
    PWMB_CCR5H = 0x00;
    PWMB_CCR5L = 128;
    PWMB_PSCRH = 0x00;       /* PSC=0, 高频 PWM (24MHz/256 ≈ 94kHz) */
    PWMB_PSCRL = 0x00;
    PWMB_PS    = (PWMB_PS & ~0x03) | 0x02;  /* PS=2 -> P0.0 */
    PWMB_ENO   = PWMB_ENO1P;
    PWMB_BKR   = 0x80;
    PWMB_CR1   = 0x01;
}

void test_start(void)
{
    test_cnt = 0;
    test_active = 1;
    ay_active = 1;

    ay_wr(0, 0xB1); ay_wr(1, 0x01);
    ay_wr(2, 0x89); ay_wr(3, 0x02);
    ay_wr(4, 0xCB); ay_wr(5, 0x03);
    ay_wr(7, 0x00);
    ay_wr(11, 0x91); ay_wr(12, 0x0C);
    ay_wr(13, 0x04);
    ay_wr(8, 0x10);
    ay_wr(9, 0x10);
    ay_wr(10, 0x10);
}

/* Timer0: 1T 17640Hz (跟主线一样, ISR 混音 + 流水灯节拍 + test_tick) */
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
    s16 mix;
    u8 out;

    /* test_tick: 5 秒后停 AY */
    if (test_active)
    {
        if (++test_cnt >= BOOT_NOTE_TICKS)
        {
            test_active = 0;
            ay_active = 0;
            ay_wr(8, 0x00);
            ay_wr(9, 0x00);
            ay_wr(10, 0x00);
        }
    }

    /* AY 混音输出到 PWMB P0.0 (只在 ay_active 时) */
    if (ay_active)
    {
        mix = ay_render();
        if (mix > 127) mix = 127;
        if (mix < -128) mix = -128;
        out = 128 + (u8)mix;
        PWMB_CCR5L = out;
    }

    /* 流水灯节拍: 每 1 秒 (17640 次) */
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
    pwmb_dac_init();
    ay_init();
    test_start();        /* AY 开机 C4/E4/G4 和弦 */
    timer0_init();
    uart_init();
    usb_init();
    EA = 1;

    while (1)
    {
        uart_polling();
    }
}
