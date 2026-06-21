/*---------------------------------------------------------------------*/
/* DAC1 12-bit + Timer0 ISR 22050Hz + USB 单 CDC + AY 开机音 */
/*---------------------------------------------------------------------*/

#include "stc.h"
#include "usb.h"
#include "timer.h"
#include "ay8910.h"
#include "sn76489.h"
#include "scc.h"
#include "nes.h"

char *USER_DEVICEDESC = 0;
char *USER_PRODUCTDESC = 0;
char *USER_STCISPCMD = "@STCISP#";

unsigned long MAIN_Fosc = 72000000L;  /* 72MHz HPLL */
#define SAMPLE_RATE 22050

u8 led_val = 0xFE;
static u16 led_tick = 0;

static u16 test_cnt = 0;
static u8 test_active = 0;
static u8 ay_active = 0;
static u8 sn_active = 0;
static u8 scc_active = 0;
static u8 nes_active = 0;
#define BOOT_NOTE_TICKS 44100  /* 2 秒 (22050 * 2) */

static u8 isp_match = 0;

/* ========== UART 命令缓冲 ========== */
#define UART1_BUF_LENGTH 2048
u8 xdata RX1_Buffer[UART1_BUF_LENGTH];
u8 xdata Uart3RxBuffer[UART1_BUF_LENGTH];  /* usb.c 引用, 别名到 RX1_Buffer */
volatile u16 RX1_Cnt = 0;
volatile u16 TX1_Cnt = 0;
u8 Uart3RxRptr = 0, Uart3RxWptr = 0;

void uart_set_parity(void) {}
void uart_set_baud(void) {}

void dac1_init(void)
{
    DAC1_DIV = 2;
    PGA1_CR1 = 0x43;  /* MSEL=Buffer(1), OSEL=P0.7(0), NSEL=P0.5(0), PSEL=DAC1O(3) */
    PGA1_CR2 = 0x04;  /* GSEL=1, OE=1, PWD=0 */
    P0n_HighZ(0x80);  /* P0.7 高阻 */
    P0n_HighZ(0x20);  /* P0.5 高阻 */
    DAC1_DAT = 2048;
    DAC1_CR = 0x41;
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
    u16 out;

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

    mix = 0;
    if (ay_active) mix += (s16)(ay_render() * 2);
    if (sn_active) mix += sn_render();
    if (scc_active) mix += (s16)(scc_render() / 2);
    if (nes_active) mix += nes_render();

    mix *= 8;
    if (mix > 2047) mix = 2047;
    if (mix < -2048) mix = -2048;
    out = 2048 + (u16)mix;
    DAC1_DAT = out;
    DAC1_CR = 0x41;

    if (++led_tick >= 22050)
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

void clk_init_72m(void)
{
    WTST = 3;
    CLKDIV = 2;
    VRTRIM = CHIPID22;
    IRTRIM = CHIPID12;
    IRCBAND &= ~0x03;
    IRCBAND |= 0x01;
    HPLLCR &= ~0x10;
    HPLLPDIV = 5;
    HPLLCR &= ~0x0f;
    HPLLCR |= 0x04;
    HPLLCR |= 0x80;
    {
        unsigned int d;
        for (d = 0; d < 60000; d++);
    }
    CLKSEL &= ~0x03;
    CLKSEL &= ~0x0c;
    CLKSEL |= (1 << 2);
}

void process_uart(void)
{
    u8 b, r, d, p;

    while (TX1_Cnt != RX1_Cnt)
    {
        b = RX1_Buffer[TX1_Cnt];
        if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;

        /* @STCISP# 续命优先, 否则 0x50='P' 会被 SN 分支截走 */
        if (isp_match > 0 && b == USER_STCISPCMD[isp_match])
        {
            if (++isp_match >= 8)
            {
                USBCON = 0x00;
                USBCLK = 0x00;
                IRC48MCR = 0x00;
                IAP_CONTR = 0x60;
                while (1);
            }
        }
        else if (isp_match == 0 && b == USER_STCISPCMD[0])
        {
            isp_match = 1;
        }
        else if (b == 0xA0)
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
            isp_match = 0;
        }
        else if (b == 0x50)
        {
            /* SN76489: [0x50][data] */
            if (TX1_Cnt == RX1_Cnt) break;
            d = RX1_Buffer[TX1_Cnt];
            if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
            sn_active = 1;
            sn_wr(d);
            isp_match = 0;
        }
        else if (b == 0xD2)
        {
            /* SCC: [0xD2][port][reg][data] */
            if (TX1_Cnt == RX1_Cnt) break;
            p = RX1_Buffer[TX1_Cnt];
            if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
            if (TX1_Cnt == RX1_Cnt) break;
            r = RX1_Buffer[TX1_Cnt];
            if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
            if (TX1_Cnt == RX1_Cnt) break;
            d = RX1_Buffer[TX1_Cnt];
            if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
            scc_active = 1;
            scc_wr((p & 0x7F) << 1, r);
            scc_wr(((p & 0x7F) << 1) | 1, d);
            isp_match = 0;
        }
        else if (b == 0xB4)
        {
            /* NES APU: [0xB4][reg][data] */
            if (TX1_Cnt == RX1_Cnt) break;
            r = RX1_Buffer[TX1_Cnt];
            if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
            if (TX1_Cnt == RX1_Cnt) break;
            d = RX1_Buffer[TX1_Cnt];
            if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
            nes_active = 1;
            nes_wr(r, d);
            isp_match = 0;
        }
        else if (b == 0xB5)
        {
            /* NES set clock: [0xB5][clk0][clk1][clk2][clk3] little-endian */
            u32 clk = 0;
            u8 k;
            for (k = 0; k < 4; k++) {
                if (TX1_Cnt == RX1_Cnt) break;
                clk |= ((u32)RX1_Buffer[TX1_Cnt]) << (k * 8);
                if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
            }
            if (k == 4) {
                nes_set_clock(clk);
            }
            isp_match = 0;
        }
        else if (b == 0xB6)
        {
            /* NES DMC 采样数据下发: [0xB6][addr_lo][addr_hi][len][data...]
             * cpu_addr 是 NES CPU 地址 ($C000+), MCU 内部映射到 nes_dmc_buf[addr - 0xC000]
             * len 最大 32 (避免一次过长), vgm_player 分片下发
             */
            u16 addr;
            u8 len, k;
            u8 tmp[32];
            if (TX1_Cnt == RX1_Cnt) break;
            addr = RX1_Buffer[TX1_Cnt];
            if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
            if (TX1_Cnt == RX1_Cnt) break;
            addr |= ((u16)RX1_Buffer[TX1_Cnt]) << 8;
            if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
            if (TX1_Cnt == RX1_Cnt) break;
            len = RX1_Buffer[TX1_Cnt];
            if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
            if (len > 32) len = 32;
            for (k = 0; k < len; k++) {
                if (TX1_Cnt == RX1_Cnt) break;
                tmp[k] = RX1_Buffer[TX1_Cnt];
                if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
            }
            nes_dmc_load(addr, k, tmp);
            isp_match = 0;
        }
        else if (b == 0xF0)
        {
            /* Reset all chips: 重新初始化所有音源, 清除残留状态
             * 用于 playlist 模式切歌时避免上一首的相位/步进/波表残留
             * 导致下一首第一音音高错误 */
            sn_init();
            ay_init();
            scc_init();
            nes_init();
            ay_active = 0;
            sn_active = 0;
            scc_active = 0;
            nes_active = 0;
            isp_match = 0;
        }
        else
        {
            isp_match = 0;
        }
    }
}

void main(void)
{
    sys_init();
    clk_init_72m();  /* PLL 72MHz, 必须在 usb_init 之前 */
    dac1_init();
    sn_init();
    ay_init();
    scc_init();
    nes_init();
    test_start();
    timer0_init();
    usb_init();
    EA = 1;

    while (1)
    {
        process_uart();  /* 解析 USB CDC 接收的 AY 命令 */
    }
}
