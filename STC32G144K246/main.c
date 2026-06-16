/*
 * STC32G144K246 USB HID + 72MHz HPLL (代码配置) + DAC1 12-bit
 *
 * - 主时钟: HPLL 输出 72MHz (代码切换 PLL, 必须在 USB 初始化之前)
 *   路径: 24M HIRC -> /5 -> 4.8M -> x60 -> 288M -> /2 -> 144M -> CLKDIV=2 -> 72M
 *   PLL 倍频编码猜测: HPLLCR 低4位 = (N - 52) / 2, 即 x60=0x04, x80=0x0e
 *   PLL 工作范围参考: 用户测试数据 (x58~x70 对应 139~168M PLL 输出)
 * - USB HID EP1 IN/OUT 64 字节回环 (USB 走独立 IRC48M, 不受主时钟影响)
 * - DAC1 P0.7 12-bit, PGA1 Buffer 模式
 * - Timer0 1000Hz 中断翻转 DAC (500Hz 方波试听)
 * - P2 流水灯
 *
 * 移植自 stc_hid-master 开源工程 (无 LIB 依赖)
 */

#include "stc.h"
#include "usb.h"
#include "usb_req_class.h"

#define MAIN_Fosc   72000000L

#define LED P2

void delay_ms(unsigned int ms)
{
    unsigned long i;
    do {
        i = MAIN_Fosc / 6000;
        while (--i);
    } while (--ms);
}

/* 主时钟切到 HPLL 72MHz. 必须在 USB 初始化之前调用, 否则 PLL 切换冲击 USB 模块 */
void clk_init_72m(void)
{
    /* 关键: 先设 WTST/CLKDIV, 再切 PLL, 否则 PLL 输出后 Flash 读不出来 -> 死机 */
    WTST = 3;                       /* FLASH 等待: 72MHz 用 WTST=3 */
    CLKDIV = 2;                     /* 144M / 2 = 72MHz */

    VRTRIM = CHIPID22;              /* 27MHz 频段的 VRTRIM 出厂校准值 */
    IRTRIM = CHIPID12;              /* 恢复 HIRC 到 24MHz, 覆盖 ISP 设置 */
    IRCBAND &= ~0x03;
    IRCBAND |= 0x01;                /* 选 27MHz 频段 */

    HPLLCR &= ~0x10;                /* PLL 时钟源 = HIRC */
    HPLLPDIV = 5;                   /* 24M / 5 = 4.8M PLL 输入 */
    HPLLCR &= ~0x0f;
    HPLLCR |= 0x04;                 /* PLL 倍频 x60: 4.8M * 60 = 288MHz */
    HPLLCR |= 0x80;                 /* 使能 PLL */
    delay_ms(10);                   /* 等 PLL 锁定 */

    CLKSEL &= ~0x03;                /* BASE_CLK 选 HIRC (准备给 HPLL) */
    CLKSEL &= ~0x0c;
    CLKSEL |= (1 << 2);             /* 主时钟源 = HPLL1 / 2 = 144MHz */
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

    /* 关键: PLL 切换必须在 USB 初始化之前, 否则冲击 USB 模块 (历史教训, 见 memory) */
    clk_init_72m();

    /* USB 走独立 IRC48M, 不受主时钟影响 */
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
