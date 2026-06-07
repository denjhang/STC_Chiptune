/*
 * STC8H8K64U 开发板 Demo
 * Keil C51 + stc8h.h, 45.1584MHz (IRC 超频)
 *
 * PWMA PWM1 → P2.0: 8-bit DAC 载波 (~176kHz)
 * Timer0 ISR: 16kHz 固定采样率, 16-bit 相位累加 + 64点 sine 表
 * Timer1:     UART1 波特率 230400
 * main loop:  LED 流水 + 音乐播放 + UART echo
 */

#include "stc8h.h"
#include <intrins.H>

#define MAIN_Fosc       45158400L
#define Baudrate1       230400L
#define UART1_BUF_LENGTH 64
#define SAMPLE_RATE     16000

typedef unsigned char   u8;
typedef unsigned int    u16;
typedef unsigned long   u32;

/* ========== UART ========== */
u8  TX1_Cnt, RX1_Cnt;
bit B_TX1_Busy;
u8  xdata RX1_Buffer[UART1_BUF_LENGTH];

/* ========== 波形表 (64点, 0~255) ========== */
#define WAVE_SQUARE     0
#define WAVE_SINE       1

u8 code square_table[] = {
    255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,
    255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,
      0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
      0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0
};
u8 code sine_table[] = {
    128, 140, 153, 165, 177, 188, 199, 209,
    218, 226, 234, 240, 245, 250, 253, 254,
    255, 254, 253, 250, 245, 240, 234, 226,
    218, 209, 199, 188, 177, 165, 153, 140,
    128, 116, 103,  91,  79,  68,  57,  47,
     38,  30,  22,  16,  11,   6,   3,   2,
      1,   2,   3,   6,  11,  16,  22,  30,
     38,  47,  57,  68,  79,  91, 103, 116
};

/* ========== 音阶频率表 (Hz) ========== */
u16 code note_freq[] = {
    262,262,392,392,440,440,392, 0,
    349,349,330,330,294,294,262, 0,
    392,392,349,349,330,330,294, 0,
    392,392,349,349,330,330,294, 0,
    262,262,392,392,440,440,392, 0,
    349,349,330,330,294,294,262, 0
};
#define NOTE_LEN 48

u8 code note_name[] = {0, 1,1,2,2,3,3,4, 0, 5,5,6,6,7,7,0, 1,1,2,2,3,3,4,4, 0, 5,5,6,6,7,7,0, 0xff};

u8 code twinkle[] = {
     0,250,  0,250,  1,250,  1,250,  2,250,  2,250,  1,250,
     3,250,  3,250,  4,250,  4,250,  5,250,  5,250,  0,250,
     1,250,  1,250,  2,250,  2,250,  4,250,  4,250,  5,250,
     1,250,  1,250,  2,250,  2,250,  4,250,  4,250,  5,250,
     0,250,  0,250,  1,250,  1,250,  2,250,  2,250,  1,250,
     3,250,  3,250,  4,250,  4,250,  5,250,  5,250,  0,250,
    0xff
};

/* ========== LED ========== */
u8  led_val = 0xFE;

/* ========== 采样/波形状态 ========== */
volatile u8 wave_type = WAVE_SINE;
u16 phase_acc = 0;
u16 phase_step = 0;
volatile u8 pwm_range = 128;
static u8 play_count = 0;
static u8 note_in_phrase = 0;

/*
 * 16-bit 相位累加, 高 6 位 → 64 点表索引
 * step = freq * 65536 / SAMPLE_RATE = freq * 65536 / 16000 = freq * 4
 * 降 1 八度: step = freq * 2
 */
u16 calc_step(u16 freq) {
    u32 tmp;
    tmp = (u32)freq * 2UL;
    if (tmp > 65535UL) tmp = 65535UL;
    return (u16)tmp;
}

/* ========== volatile 延时 ========== */
volatile u16 vd;

/* ========== 延时 ========== */
void delay(u16 i) {
    u16 j, k;
    for (j = 0; j < 500; j++)
        for (k = 0; k < i; k++);
}

/* ========== PWMA PWM1 → P2.0: 8-bit DAC 载波 ========== */
void pwma_dac_init(void) {
    P_SW2 |= 0x80;

    PWMA_ENO   = 0x00;
    PWMA_CCER1 = 0x00;
    PWMA_CCER2 = 0x00;
    PWMA_CCMR1 = 0x68;
    PWMA_CCER1 = 0x05;

    PWMA_ARRH  = 0x00;
    PWMA_ARRL  = 255;
    PWMA_CCR1H = 0x00;
    PWMA_CCR1L = 128;
    PWMA_PSCRH = 0x00;
    PWMA_PSCRL = 0x00;

    PWMA_PS = (PWMA_PS & ~0x03) | 0x01;
    PWMA_ENO = 0x01;
    PWMA_BKR = 0x80;
    PWMA_CR1 = 0x01;

    P_SW2 &= ~0x80;
}

/* ========== Timer0: 16kHz ========== */
void timer0_init(void) {
    u32 reload;
    reload = MAIN_Fosc / SAMPLE_RATE;
    reload = 65536UL - reload;
    AUXR |= 0x80;
    TMOD &= 0xF0;
    TH0 = (u8)(reload >> 8);
    TL0 = (u8)(reload & 0xFF);
    ET0 = 1;
    TR0 = 1;
}

/* Timer0 ISR: 16-bit 相位 + 64点查表 + 写 DAC */
void timer0_isr(void) interrupt 1 {
    u16 acc;
    u8 idx, s;

    acc = phase_acc + phase_step;
    phase_acc = acc;
    idx = (u8)(acc >> 10);        /* 高 6 位 → 0~63 */

    if (wave_type == WAVE_SQUARE)
        s = sine_table[idx];
    else
        s = square_table[idx];

    P_SW2 |= 0x80;
    if (pwm_range == 0)
        PWM1_CCR1L = 128;
    else
        PWM1_CCR1L = s;
    P_SW2 &= ~0x80;
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

/* ========== 音乐播放 ========== */
void play_music(void) {
    u8 ni;

    while (play_count < NOTE_LEN) {
        ni = twinkle[play_count];

        if (note_name[ni]) {
            phase_step = calc_step(note_freq[ni]);
            phase_acc = 0;
            pwm_range = 255;
        } else {
            phase_step = 0;
            phase_acc = 0;
            pwm_range = 0;
        }

        {
            u16 sleep = twinkle[play_count + 1];
            while (sleep--) {
                delay(2);
            }
        }

        play_count++;
        note_in_phrase++;
    }

    play_count = 0;
    note_in_phrase = 0;
    phase_step = 0;
    phase_acc = 0;
    pwm_range = 0;
    P_SW2 |= 0x80;
    PWM1_CCR1L = 128;
    P_SW2 &= ~0x80;
}

/* ========== 主 ========== */
void main(void) {
    P0M0=0; P0M1=0;
    P1M0=0; P1M1=0;
    P2M0=0; P2M1=0;
    P3M0=0; P3M1=0;
    P4M0=0; P4M1=0;

    P0 = 0xFF;
    P35 = 1; P36 = 1; P37 = 1;
    P41 = 1; P42 = 1; P44 = 1; P45 = 1;

    pwma_dac_init();
    timer0_init();
    UART1_config();
    EA = 1;
    PrintString1("STC8H PWM DAC Demo\r\n");

    while (1) {
        play_music();

        P0 = led_val;
        led_val = _crol_(led_val, 1);
        delay(50);

        if ((TX1_Cnt != RX1_Cnt) && (!B_TX1_Busy)) {
            SBUF = RX1_Buffer[TX1_Cnt];
            B_TX1_Busy = 1;
            if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
        }
    }
}
