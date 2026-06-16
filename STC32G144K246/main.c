/*
 * STC32G144K246 USB HID + 64MHz HIRC (STC-ISP 配置) + DAC1 12-bit
 *
 * - 64MHz HIRC 主时钟 (STC-ISP 烧录时配置 IRCBAND/IRTRIM, 代码不动)
 * - USB HID EP1 IN/OUT 64 字节回环 (USB 走独立 IRC48M)
 * - DAC1 P0.7 12-bit, PGA1 Buffer 模式
 * - Timer0 1000Hz 中断翻转 DAC (500Hz 方波试听)
 * - P2 流水灯
 *
 * 移植自 stc_hid-master 开源工程 (无 LIB 依赖)
 */

#include "stc.h"
#include "usb.h"
#include "usb_req_class.h"

#define MAIN_Fosc   64000000L

#define LED P2

void delay_ms(unsigned int ms)
{
    unsigned long i;
    do {
        i = MAIN_Fosc / 6000;
        while (--i);
    } while (--ms);
}

/* DAC1: 12-bit, P0.7 (DAC1+OP1 Buffer 模式) */
void dac1_init(void)
{
    P0M0 |= 0x80; P0M1 &= ~0x80;  /* P0.7 推挽输出 */
    P0M0 |= 0x20; P0M1 &= ~0x20;  /* P0.5 高阻 (OP1反相输入) */

    PGA1_CR1 = 0x43;  /* MSEL=Buffer, OSEL=P0.7, NSEL=P0.5, PSEL=DAC1O */
    PGA1_CR2 = 0x04;  /* GSEL=1, OE=使能, PWD=电源开 */

    DAC1_CR = 0x41;   /* bit6=使能DAC1, bit0=触发输出 */
    DAC1_DIV = 2;     /* MCLK/(DIV*4) = 24M/8 = 3MHz 刷新率 */
    DAC1_DAT = 2048;  /* 中点 */
}

/* Timer0: 1000Hz 中断翻转 DAC (500Hz 方波) + P3.2 长按 1s 复位扫描 */
static bit dac_level;
static bit key_flag;
static unsigned int key_cnt;

void timer0_init(void)
{
    unsigned long reload;
    AUXR |= 0x80;       /* 1T 模式 */
    TMOD &= 0xF0;
    reload = 65536UL - MAIN_Fosc / 1000;  /* 1000Hz 翻转 */
    TH0 = (unsigned char)(reload >> 8);
    TL0 = (unsigned char)(reload & 0xFF);
    ET0 = 1;
    TR0 = 1;
}

/* P3.2 长按 ~1s 触发复位到 ISP 监控区 (双保险, USB 命令之外的物理入口) */
void key_reset_scan(void)
{
    if (!P32)
    {
        if (!key_flag)
        {
            key_cnt++;
            if (key_cnt >= 1000)
            {
                key_flag = 1;
                USBCON = 0x00;
                USBCLK = 0x00;
                IRC48MCR = 0x00;
                IAP_CONTR = 0x60;
                while (1);
            }
        }
    }
    else
    {
        key_cnt = 0;
        key_flag = 0;
    }
}

void timer0_isr(void) interrupt 1
{
    if (dac_level) {
        DAC1_DAT = 4095;
        DAC1_CR = 0x41;
        dac_level = 0;
    } else {
        DAC1_DAT = 0;
        DAC1_CR = 0x41;
        dac_level = 1;
    }
    /* P3.2 长按复位 - 接好按键到 GND 后启用 */
    /* key_reset_scan(); */
}

void hid_send_ep1(BYTE *buf, BYTE len)
{
    BYTE i;

    if (DeviceState != DEVSTATE_CONFIGURED) return;
    if (Usb1InBusy) return;

    EUSB = 0;
    Usb1InBusy = 1;
    usb_write_reg(INDEX, 1);
    for (i = 0; i < len; i++)
    {
        usb_write_reg(FIFO1, buf[i]);
    }
    usb_write_reg(INCSR1, INIPRDY);
    EUSB = 1;
}

void main(void)
{
    BYTE k, temp;

    WTST = 0;
    EAXFR = 1;
    CKCON = 0;

    P0M1 = 0x00; P0M0 = 0x00;
    P1M1 = 0x00; P1M0 = 0x00;
    P2M1 = 0x00; P2M0 = 0x00;
    P3M1 = 0x00; P3M0 = 0x00;
    P4M1 = 0x00; P4M0 = 0x00;
    P5M1 = 0x00; P5M0 = 0x00;
    P6M1 = 0x00; P6M0 = 0x00;
    P7M1 = 0x00; P7M0 = 0x00;

    /* USB 引脚 P3.0/P3.1 准双向 */
    P3M1 &= ~0x03;
    P3M0 &= ~0x03;

    /* 顺序照搬 stc_hid-master: IRC48M -> USBCLK/USBCON -> usb_init -> DAC -> Timer0 -> EA */
    IRC48MCR = 0x80;
    while (!(IRC48MCR & 0x01));

    USBCLK = 0x00;
    USBCON = 0x90;
    usb_init();

    dac1_init();
    timer0_init();

    EA = 1;             /* 总中断: Timer0 + USB */

    LED = 0xFE;
    delay_ms(500);

    while (1)
    {
        temp = 0x01;
        for (k = 0; k < 8; k++)
        {
            LED = ~temp;
            delay_ms(100);
            temp = temp << 1;
        }

        /* HID 回环: EP1 OUT -> EP1 IN */
        if (HidEp1OutReady)
        {
            HidEp1OutReady = 0;
            hid_send_ep1(HidEp1OutBuffer, 64);
        }
    }
}
