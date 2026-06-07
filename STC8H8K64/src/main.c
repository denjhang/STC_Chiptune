/*
 * STC8H8K64U 开发板综合 Demo
 * Keil C51 + stc8h.h, 22.1184MHz
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

/* ========== LED/RGB 状态（全局，持续） ========== */
u8  led_val = 0xFE;
u8  rgb_idx = 0;
u16 led_timer = 0;
u16 rgb_timer = 0;

/* ========== volatile 防 Keil 优化空循环 ========== */
volatile u16 vdelay;

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

/* ========== 数码管扫描一位 ========== */
void digit_scan(void) {
    u8 d;
    switch (digit_pos) {
        case 0: d = cur_freq / 1000;       P2 = table[d]; P41 = 0; vdelay = 120; while(vdelay--); P41 = 1; break;
        case 1: d = (cur_freq / 100) % 10; P2 = table[d]; P42 = 0; vdelay = 120; while(vdelay--); P42 = 1; break;
        case 2: d = (cur_freq / 10) % 10;  P2 = table[d]; P44 = 0; vdelay = 120; while(vdelay--); P44 = 1; break;
        case 3: d = cur_freq % 10;         P2 = table[d]; P45 = 0; vdelay = 120; while(vdelay--); P45 = 1; break;
    }
    digit_pos++;
    if (digit_pos >= 4) digit_pos = 0;
}

/* ========== LED + RGB 更新 ========== */
void led_rgb_update(void) {
    led_timer++;
    if (led_timer >= 300) {
        led_timer = 0;
        P0 = led_val;
        led_val = _crol_(led_val, 1);
    }
    rgb_timer++;
    if (rgb_timer >= 600) {
        rgb_timer = 0;
        P35 = rgb_idx & 0x01;
        P36 = (rgb_idx >> 1) & 0x01;
        P37 = (rgb_idx >> 2) & 0x01;
        rgb_idx++;
        if (rgb_idx >= 7) rgb_idx = 0;
    }
}

/* ========== 蜂鸣器播放一个音符，同时扫描数码管+LED+RGB ========== */
void buzzer_beep(u16 freq, u16 dur_ms) {
    u16 i, j, d;
    u32 total;

    if (freq == 0) {
        total = (u32)dur_ms * 1000;
        while (total > 480) {
            digit_scan();
            digit_scan();
            digit_scan();
            digit_scan();
            led_rgb_update();
            total -= 480;
        }
        return;
    }

    d = MAIN_Fosc / 4 / freq;
    total = (u32)dur_ms * freq / 1000;

    for (i = 0; i < total; i++) {
        P16 = 1;
        for (j = 0; j < d; j++) {
            digit_scan();
            led_rgb_update();
        }
        P16 = 0;
        for (j = 0; j < d; j++) {
            digit_scan();
            led_rgb_update();
        }
    }
    P16 = 0;
}

/* ========== 主 ========== */
void main(void) {
    u8 note_idx = 0;

    P0M0=0; P0M1=0;
    P1M0=0; P1M1=0;
    P2M0=0; P2M1=0;
    P3M0=0; P3M1=0;
    P4M0=0; P4M1=0;

    P0 = 0xFF;
    P35 = 0; P36 = 0; P37 = 0;
    P16 = 0;

    UART1_config();
    EA = 1;
    PrintString1("STC8H Board Demo\r\n");

    while (1) {
        cur_freq = twinkle_freq[note_idx];
        buzzer_beep(cur_freq, 300);

        if ((TX1_Cnt != RX1_Cnt) && (!B_TX1_Busy)) {
            SBUF = RX1_Buffer[TX1_Cnt];
            B_TX1_Busy = 1;
            if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
        }

        note_idx++;
        if (note_idx >= NOTE_LEN) note_idx = 0;
    }
}
