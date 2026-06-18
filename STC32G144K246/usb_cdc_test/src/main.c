/*---------------------------------------------------------------------*/
/* Phase 5c: PWMB 8-bit DAC + Timer0 ISR 17640Hz + USB 单 CDC + AY 开机音 */
/*---------------------------------------------------------------------*/

#include "stc.h"
#include "usb.h"
#include "timer.h"
#include "ay8910.h"
/* 暂时只做 AY, 其他音源稍后加 */

unsigned long MAIN_Fosc = 60000000L;  /* 60MHz (ISP 设) */
#define SAMPLE_RATE 17640

#define PWMB_ENO1P    0x01

u8 led_val = 0xFE;
static u16 led_tick = 0;

static u16 test_cnt = 0;
static u8 test_active = 0;
static u8 ay_active = 0;
#define BOOT_NOTE_TICKS 35280  /* 2 秒 (17640 * 2) */

/* ========== UART 命令缓冲 ========== */
#define UART1_BUF_LENGTH 2048
u8 xdata RX1_Buffer[UART1_BUF_LENGTH];
u8 xdata Uart3RxBuffer[UART1_BUF_LENGTH];  /* usb.c 引用, 别名到 RX1_Buffer */
volatile u16 RX1_Cnt = 0;
volatile u16 TX1_Cnt = 0;
u8 Uart3RxRptr = 0, Uart3RxWptr = 0;

void uart_set_parity(void) {}
void uart_set_baud(void) {}

void pwmb_dac_init(void)
{
    PWMB_ENO   = 0x00;
    PWMB_CCER1 = 0x00;
    PWMB_CCMR1 = 0x68;
    PWMB_CCER1 = 0x05;
    PWMB_ARRH  = 0x00;
    PWMB_ARRL  = 255;
    PWMB_CCR5H = 0x00;
    PWMB_CCR5L = 128;
    PWMB_PSCRH = 0x00;
    PWMB_PSCRL = 0x00;
    PWMB_PS    = (PWMB_PS & ~0x03) | 0x02;
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

    if (ay_active)
    {
        mix = ay_render();
        if (mix > 127) mix = 127;
        if (mix < -128) mix = -128;
        out = 128 + (u8)mix;
        PWMB_CCR5L = out;
    }

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
    P3M1 = 0x00;   P3M0 = 0x00;
    P4M1 = 0x00;   P4M0 = 0x00;
    P5M1 = 0x00;   P5M0 = 0x00;
    P6M1 = 0x00;   P6M0 = 0x00;
    P7M1 = 0x00;   P7M0 = 0x00;

    S3_S = 1;
    S2_S = 1;

    P2 = 0xFF;
}

void process_uart(void)
{
    u8 b, r, d;

    while (TX1_Cnt != RX1_Cnt)
    {
        b = RX1_Buffer[TX1_Cnt];
        if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;

        if (b == 0xA0)
        {
            /* AY8910: [0xA0][reg][data] */
            if (TX1_Cnt == RX1_Cnt) break;
            r = RX1_Buffer[TX1_Cnt];
            if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
            if (TX1_Cnt == RX1_Cnt) break;
            d = RX1_Buffer[TX1_Cnt];
            if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
            ay_active = 1;
            ay_wr(r, d);
        }
    }
}

void main(void)
{
    sys_init();
    pwmb_dac_init();
    ay_init();
    test_start();
    timer0_init();
    usb_init();
    EA = 1;

    while (1)
    {
        process_uart();  /* 解析 USB CDC 接收的 AY 命令 */
    }
}
