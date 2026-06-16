/*
 * STC32G144K246 最小测试
 * HPLL 120MHz + P2流水灯 + USB CDC回环 + DAC1 P0.0 方波
 */

#include "STC32G.H"
#include "ai_usb.h"

#define MAIN_Fosc 120000000L

#define LED P2

void delay_ms(unsigned int ms) {
    unsigned long i;
    do {
        i = MAIN_Fosc / 6000;
        while (--i);
    } while (--ms);
}

/* HPLL 120MHz: HIRC 24MHz -> /4=6MHz -> x80=480MHz -> /2=240MHz -> CLKDIV/2=120MHz */
void clk_init(void) {
    WTST = 4;
    CLKDIV = 2;
    VRTRIM = CHIPID22;
    IRTRIM = CHIPID12;
    IRCBAND &= ~0x03;
    IRCBAND |= 0x01;       /* 27MHz 频段 */
    HPLLCR &= ~0x10;       /* HPLL 时钟源 = HIRC */
    HPLLPDIV = 4;          /* 24MHz / 4 = 6MHz */
    HPLLCR |= 0x0e;        /* HPLL = 6MHz * 80 = 480MHz */
    HPLLCR |= 0x80;        /* 使能 HPLL */
    delay_ms(10);
    CLKSEL &= ~0x03;       /* BASE_CLK = HIRC */
    CLKSEL &= ~0x0c;
    CLKSEL |= 1 << 2;      /* 系统时钟 = HPLL/2 */
}

/* DAC1: 12-bit, P0.7 (DAC1+OP1 Buffer 模式) */
void dac1_init(void) {
    P0M0 |= 0x80; P0M1 &= ~0x80;  /* P0.7 推挽输出 */
    P0M0 |= 0x20; P0M1 &= ~0x20;  /* P0.5 高阻 (OP1反相输入) */

    PGA1_CR1 = 0x43;  /* MSEL=Buffer, OSEL=P0.7, NSEL=P0.5, PSEL=DAC1O */
    PGA1_CR2 = 0x04;  /* GSEL=1, OE=使能, PWD=电源开 */

    DAC1_CR = 0x41;   /* bit6=使能DAC1, bit0=触发输出 */
    DAC1_DIV = 2;     /* MCLK/(DIV*4) ≈ 150KHz @120MHz */
    DAC1_DAT = 2048;  /* 中点 */
}

/* Timer0: 方波翻转 */
static bit dac_level;
void timer0_init(void) {
    unsigned long reload;
    AUXR |= 0x80;       /* 1T 模式 */
    TMOD &= 0xF0;
    reload = 65536UL - MAIN_Fosc / 1000;  /* 1000Hz 翻转 = 500Hz 方波 */
    TH0 = (unsigned char)(reload >> 8);
    TL0 = (unsigned char)(reload & 0xFF);
    ET0 = 1;
    TR0 = 1;
}

void timer0_isr(void) interrupt 1 {
    if (dac_level) {
        DAC1_DAT = 4095;
        DAC1_CR = 0x41;
        dac_level = 0;
    } else {
        DAC1_DAT = 0;
        DAC1_CR = 0x41;
        dac_level = 1;
    }
}

void main(void) {
    unsigned char k, temp;

    WTST = 0;
    EAXFR = 1;
    CKCON = 0;

    P0M0 = 0; P0M1 = 0;
    P1M0 = 0; P1M1 = 0;
    P2M0 = 0; P2M1 = 0;
    P3M0 = 0; P3M1 = 0;
    P4M0 = 0; P4M1 = 0;
    P5M0 = 0; P5M1 = 0;
    P6M0 = 0; P6M1 = 0;
    P7M0 = 0; P7M1 = 0;

    clk_init();
    usb_init();
    EA = 1;

    dac1_init();
    timer0_init();

    LED = 0xFE;
    delay_ms(500);

    while (1) {
        temp = 0x01;
        for (k = 0; k < 8; k++) {
            LED = ~temp;
            delay_ms(100);
            temp = temp << 1;
        }

        if (UsbOutBuffer[0]) {
            USB_SendData(UsbOutBuffer, UsbOutBuffer[0] + 1);
            usb_OUT_done();
        }
    }
}
