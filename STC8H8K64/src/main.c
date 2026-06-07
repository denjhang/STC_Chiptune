/*
 * STC8H8K64U 开发板综合 Demo
 * Keil C51 + stc8h.h, 22.1184MHz
 *
 * PWMB CH3 → P0.2: 8-bit DAC 载波 (~43kHz), PWM DAC 音量控制
 * PWMA: 音频频率定时器, interrupt 26 翻转 DAC duty 产生方波
 * Timer2 ISR: 数码管动态扫描 (1ms/位)
 * Timer1:     UART1 波特率
 * main loop:  LED 流水(剔除P0.2) + RGB 变色 + 音乐播放 + UART echo
 *
 * 参考: buzzer_hx-master
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

/* ========== 音乐音阶表 (reload值, 和 buzzer_hx 一致) ========== */
u16 code Musical_Scale[] = {
    42272,39898,37660,35546,33550,31668,29890,28212,26630,25134,23724,22392,
    21136,19950,18828,17772,16776,15834,14944,14106,13314,12568,11862,11196,
    10568,9974,9414,8886,8388,7920,7472,7054,6658,6284,5930,5598,
    0
};

/* 小星星: [音阶索引, 时基单位]
 * 每单位 = pwm_range -= 1 + delay(1) ≈ 几ms
 */
u8 code twinkle[] = {
    12,250, 12,250, 16,250, 16,250, 18,250, 18,250, 16,250,
    14,250, 14,250, 13,250, 13,250, 11,250, 11,250, 12,250,
    16,250, 16,250, 15,250, 15,250, 14,250, 14,250, 13,250,
    16,250, 16,250, 15,250, 15,250, 14,250, 14,250, 13,250,
    12,250, 12,250, 16,250, 16,250, 18,250, 18,250, 16,250,
    14,250, 14,250, 13,250, 13,250, 11,250, 11,250, 12,250,
    0xff
};

/* ========== LED/RGB ========== */
u8  led_val = 0xFE;
u8  rgb_idx = 0;

/* ========== PWM DAC 音频 ========== */
volatile u8 pwm_range = 0;       /* 0~255, DAC 音量 */
bit out_z = 0;                   /* 方波正/负半周 */
static u8 play_count = 0;

/* ========== volatile 延时 ========== */
volatile u16 vd;

/* ========== 延时 ========== */
void delay(u16 i) {
    u16 j, k;
    for (j = 0; j < 500; j++)
        for (k = 0; k < i; k++);
}

/* ========== PWMB (PWM2) CH7 → P0.2: 8-bit DAC 载波 ========== */
void pwmb_dac_init(void) {
    P_SW2 |= 0x80;
    PWMB_PS    = 0x20;           /* C5PS=10 → CH7 → P0.2 */
    PWMB_ENO   = 0x10;           /* ENO3 = 1 (bit4 = CH7/8 的低通道) */
    PWMB_CCER2 = 0x00;
    PWMB_CCMR3 = 0x60;           /* PWM 模式1 */
    PWMB_CCER2 = 0x01;           /* CC3E = 1 */
    PWM2_CCR3H = 0;
    PWM2_CCR3L = 0;             /* 初始静音 */
    PWM2_ARRH  = 0x01;          /* ARR = 256 → 8-bit DAC */
    PWM2_ARRL  = 0x00;
    PWMB_BKR   = 0x80;
    PWMB_CR1   = 0x01;
    P_SW2 &= ~0x80;
}

/* ========== PWMA (PWM1) 定时器: 音频频率 ========== */
void pwma_timer_start(u16 reload) {
    P_SW2 |= 0x80;
    if (reload == 0) {
        PWM1_CR1 = 0;
        PWM1_IER = 0;
        P_SW2 &= ~0x80;
        return;
    }
    PWM1_CNTRH = 0;
    PWM1_CNTRL = 0;
    PWM1_ARRH = (u8)(reload >> 8);
    PWM1_ARRL = (u8)(reload & 0xFF);
    PWM1_SR1 = 0x00;
    PWM1_IER = 0x01;             /* 使能溢出中断 */
    PWM1_CR1 = 0x01;
    P_SW2 &= ~0x80;
}

/* PWMA 溢出中断 → 翻转 DAC duty 产生方波 + 音量 */
void PWM1_Interrupt(void) interrupt 26 {
    P_SW2 |= 0x80;
    PWM1_SR1 = 0x00;
    if (out_z)
        PWM2_CCR3L = pwm_range;  /* 正半周: 输出音量 */
    else
        PWM2_CCR3L = 0;          /* 负半周: 输出 0 */
    out_z = !out_z;
    P_SW2 &= ~0x80;
}

/* ========== Timer2: 数码管扫描 ========== */
void timer2_init(void) {
    u32 reload;
    reload = MAIN_Fosc / 1000;
    reload = 65536UL - reload;
    AUXR &= ~(1<<4);
    AUXR &= ~(1<<3);
    AUXR |=  (1<<2);
    T2H = (u8)(reload >> 8);
    T2L = (u8)(reload & 0xFF);
    IE2 |= (1<<2);
    AUXR |=  (1<<4);
}

void timer2_isr(void) interrupt 12 {
    u8 d;
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

/* ========== 音乐播放 (参考 buzzer_hx) ========== */
void play_music(void) {
    u8 note_idx;
    u16 freq_reload;

    while (twinkle[play_count] != 0xff) {
        note_idx = twinkle[play_count];
        freq_reload = Musical_Scale[note_idx];

        if (freq_reload) {
            pwma_timer_start(freq_reload);
            pwm_range = 255;
            cur_freq = MAIN_Fosc / 2 / freq_reload;
        } else {
            P_SW2 |= 0x80;
            PWM2_CCR3L = 0;
            P_SW2 &= ~0x80;
            pwma_timer_start(0);
        }

        /* 音符时长 + 慢衰减 */
        {
            u16 sleep = twinkle[play_count + 1];
            while (sleep--) {
                if (pwm_range) pwm_range -= 1;
                delay(1);
            }
        }

        play_count += 2;
    }

    /* 播放完毕 */
    pwma_timer_start(0);
    pwm_range = 0;
    P_SW2 |= 0x80;
    PWM2_CCR3L = 0;
    P_SW2 &= ~0x80;
    play_count = 0;
}

/* ========== 主 ========== */
void main(void) {
    P0M0=0; P0M1=0;
    P1M0=0; P1M1=0;
    P2M0=0; P2M1=0;
    P3M0=0; P3M1=0;
    P4M0=0; P4M1=0;

    P0 = 0xFF;
    P35 = 1; P36 = 1; P37 = 1;  /* RGB 关闭 */
    P41 = 1; P42 = 1; P44 = 1; P45 = 1;

    pwmb_dac_init();
    timer2_init();
    UART1_config();
    EA = 1;
    PrintString1("STC8H PWM DAC Demo\r\n");

    while (1) {
        /* 播放小星星 */
        play_music();

        /* LED 流水 (P0.2 留给 PWM DAC, 掩码保护) */
        P0 = led_val & 0xFB;
        led_val = _crol_(led_val & 0xFB, 1) | 0x04;
        delay(50);

        /* RGB 关闭
        P35 = rgb_idx & 0x01;
        P36 = (rgb_idx >> 1) & 0x01;
        P37 = (rgb_idx >> 2) & 0x01;
        rgb_idx++;
        if (rgb_idx >= 7) rgb_idx = 0;
        */

        /* UART echo */
        if ((TX1_Cnt != RX1_Cnt) && (!B_TX1_Busy)) {
            SBUF = RX1_Buffer[TX1_Cnt];
            B_TX1_Busy = 1;
            if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
        }
    }
}
