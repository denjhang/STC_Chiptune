/*
 * STC8H8K64U 开发板综合 Demo
 * Keil C51 + stc8h.h, 22.1184MHz
 *
 * Timer0 ISR: 蜂鸣器方波（P1.6 toggle）
 * Timer2 ISR: 数码管动态扫描（1ms 切一位）
 * Timer1:     UART1 波特率
 * main loop:  LED 流水 + RGB 变色 + 音符切换 + UART echo
 */

#include "stc8h.h"
#include <intrins.H>

#define MAIN_Fosc       22118400L
#define Baudrate1       115200L
#define UART1_BUF_LENGTH 64

typedef unsigned char   u8;
typedef unsigned int    u16;
typedef unsigned long   u32;

/* ========== UART ========== */
u8  TX1_Cnt, RX1_Cnt;
bit B_TX1_Busy;
u8  xdata RX1_Buffer[UART1_BUF_LENGTH];

/* ========== 数码管 ========== */
u8 code table[] = {0xc0,0xf9,0xa4,0xb0,0x99,0x92,0x82,0xf8,0x80,0x90};
u8 digit_pos = 0;
u16 cur_freq = 262;

/* ========== 小星星 ========== */
u16 code twinkle_freq[] = {
    262,262,392,392,440,440,392, 0,
    349,349,330,330,294,294,262, 0,
    392,392,349,349,330,330,294, 0,
    392,392,349,349,330,330,294, 0,
    262,262,392,392,440,440,392, 0,
    349,349,330,330,294,294,262, 0
};
#define NOTE_LEN 32

/* ========== LED/RGB ========== */
u8  led_val = 0xFE;
u8  rgb_idx = 0;

/* ========== Timer0: 蜂鸣器方波 ========== */
void timer0_init(void) {
    AUXR |= 0x80;       /* Timer0 1T */
    TMOD &= 0xF0;       /* Timer0 16-bit auto */
    ET0 = 1;
}

void buzzer_set_freq(u16 freq) {
    u32 reload;
    if (freq == 0) { TR0 = 0; P16 = 0; return; }
    reload = MAIN_Fosc / 2 / freq;
    if (reload > 65535) reload = 65535;
    TH0 = (u8)(reload >> 8);
    TL0 = (u8)(reload & 0xFF);
    TR0 = 1;
}

void timer0_isr(void) interrupt 1 {
    P16 = !P16;
}

/* ========== Timer2: 数码管扫描 ========== */
void timer2_init(void) {
    u32 reload;
    /* 1ms per digit, 4 digits = 4ms full scan = 250Hz refresh
     * reload = 65536 - Fosc / 1T / 1000 = 65536 - 22118 = 43418 = 0xA97A
     */
    reload = MAIN_Fosc / 1000;
    reload = 65536UL - reload;
    AUXR &= ~(1<<4);     /* stop Timer2 */
    AUXR &= ~(1<<3);     /* Timer2 as Timer */
    AUXR |=  (1<<2);     /* Timer2 1T mode */
    T2H = (u8)(reload >> 8);
    T2L = (u8)(reload & 0xFF);
    IE2 |= (1<<2);       /* enable Timer2 interrupt */
    AUXR |=  (1<<4);     /* start Timer2 */
}

void timer2_isr(void) interrupt 12 {
    u8 d;
    /* 先关所有位选，消除鬼影 */
    P41 = 1; P42 = 1; P44 = 1; P45 = 1;

    switch (digit_pos) {
        case 0: d = cur_freq / 1000;           P2 = table[d]; P41 = 0; break;
        case 1: d = (cur_freq / 100) % 10;     P2 = table[d]; P42 = 0; break;
        case 2: d = (cur_freq / 10) % 10;      P2 = table[d]; P44 = 0; break;
        case 3: d = cur_freq % 10;             P2 = table[d]; P45 = 0; break;
    }
    digit_pos++;
    if (digit_pos >= 4) digit_pos = 0;
}

/* ========== UART ========== */
void UART1_config(void) {
    TR1 = 0;
    AUXR &= ~0x01;
    AUXR |=  (1<<6);
    TMOD &= ~(1<<6);
    TMOD &= ~0x30;
    TH1 = (u8)((65536UL - (MAIN_Fosc / 4) / Baudrate1) / 256);
    TL1 = (u8)((65536UL - (MAIN_Fosc / 4) / Baudrate1) % 256);
    ET1 = 0;
    INTCLKO &= ~0x02;
    TR1 = 1;
    SCON = (SCON & 0x3f) | 0x40;
    ES = 1;
    REN = 1;
    P_SW1 &= 0x3f;
    B_TX1_Busy = 0;
    TX1_Cnt = 0;
    RX1_Cnt = 0;
}

void PrintString1(u8 *puts) {
    for (; *puts != 0; puts++) {
        SBUF = *puts;
        B_TX1_Busy = 1;
        while (B_TX1_Busy);
    }
}

void UART1_int(void) interrupt 4 {
    if (RI) { RI = 0; RX1_Buffer[RX1_Cnt] = SBUF; if (++RX1_Cnt >= UART1_BUF_LENGTH) RX1_Cnt = 0; }
    if (TI) { TI = 0; B_TX1_Busy = 0; }
}

/* ========== 延时 ========== */
void delay(u16 i) {
    u16 j, k;
    for (j = 0; j < 500; j++)
        for (k = 0; k < i; k++);
}

/* ========== 主 ========== */
void main(void) {
    u8 note_idx = 0;
    u16 note_timer = 0;

    P0M0=0; P0M1=0;
    P1M0=0; P1M1=0;
    P2M0=0; P2M1=0;
    P3M0=0; P3M1=0;
    P4M0=0; P4M1=0;

    P0 = 0xFF;
    P35 = 0; P36 = 0; P37 = 0;
    P41 = 1; P42 = 1; P44 = 1; P45 = 1;
    P16 = 0;

    timer0_init();
    buzzer_set_freq(cur_freq);
    timer2_init();
    UART1_config();
    EA = 1;
    PrintString1("STC8H Board Demo\r\n");

    while (1) {
        /* LED 流水 */
        P0 = led_val;
        led_val = _crol_(led_val, 1);
        delay(100);

        /* RGB 变色 */
        P35 = rgb_idx & 0x01;
        P36 = (rgb_idx >> 1) & 0x01;
        P37 = (rgb_idx >> 2) & 0x01;
        rgb_idx++;
        if (rgb_idx >= 7) rgb_idx = 0;
        delay(100);

        /* 音符切换 ~300ms */
        note_timer++;
        if (note_timer >= 8) {
            note_timer = 0;
            note_idx++;
            if (note_idx >= NOTE_LEN) note_idx = 0;
            cur_freq = twinkle_freq[note_idx];
            buzzer_set_freq(cur_freq);
        }

        /* UART echo */
        if ((TX1_Cnt != RX1_Cnt) && (!B_TX1_Busy)) {
            SBUF = RX1_Buffer[TX1_Cnt];
            B_TX1_Busy = 1;
            if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
        }
    }
}
