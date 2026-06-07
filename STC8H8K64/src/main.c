/*
 * STC8H8K64U 开发板 Demo
 * Keil C51 + stc8h.h, 45.1584MHz (IRC 超频)
 *
 * PWMA PWM1 → P2.0: 8-bit DAC 载波 (~176kHz)
 * PWMA interrupt 26: 音频频率定时器, ISR 查表写 duty (参考 buzzer_hx)
 * Timer1:     UART1 波特率 230400
 * main loop:  LED 流水 + 音乐播放 + UART echo
 *
 * 波形: 方波/正弦, 每 8 音符切换
 */

#include "stc8h.h"
#include <intrins.H>

#define MAIN_Fosc       45158400L
#define Baudrate1       230400L
#define UART1_BUF_LENGTH 64

typedef unsigned char   u8;
typedef unsigned int    u16;
typedef unsigned long   u32;

/* ========== UART ========== */
u8  TX1_Cnt, RX1_Cnt;
bit B_TX1_Busy;
u8  xdata RX1_Buffer[UART1_BUF_LENGTH];

/* ========== 波形表 (32点, 0~255) ========== */
#define WAVE_SQUARE     0
#define WAVE_SINE       1

u8 code square_table[] = {
    255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,
      0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0
};
u8 code sine_table[] = {
    128,144,160,176,188,200,212,220,
    224,220,212,200,188,176,160,144,
    128,112, 96, 80, 68, 56, 44, 36,
     32, 36, 44, 56, 68, 80, 96,112
};

/* ========== 音阶 reload 表 (跟 buzzer_hx 一致, 22MHz 基准) ========== */
u16 code Musical_Scale[] = {
    42272,39898,37660,35546,33550,31668,29890,28212,26630,25134,23724,22392,
    21136,19950,18828,17772,16776,15834,14944,14106,13314,12568,11862,11196,
    10568,9974,9414,8886,8388,7920,7472,7054,6658,6284,5930,5598,
    0
};

/* 小星星: [音阶索引, 时基单位] */
u8 code twinkle[] = {
    12,250, 12,250, 16,250, 16,250, 18,250, 18,250, 16,250,
    14,250, 14,250, 13,250, 13,250, 11,250, 11,250, 12,250,
    16,250, 16,250, 15,250, 15,250, 14,250, 14,250, 13,250,
    16,250, 16,250, 15,250, 15,250, 14,250, 14,250, 13,250,
    12,250, 12,250, 16,250, 16,250, 18,250, 18,250, 16,250,
    14,250, 14,250, 13,250, 13,250, 11,250, 11,250, 12,250,
    0xff
};

/* ========== LED ========== */
u8  led_val = 0xFE;

/* ========== 波形/PWM 状态 ========== */
volatile u8 wave_type = WAVE_SINE;
u16 phase_acc = 0;
u16 phase_step = 0;
volatile u8 pwm_range = 0;
static u8 play_count = 0;
static u8 note_in_phrase = 0;

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
    PWMA_CCMR1 = 0x68;           /* PWM 模式1, 预装载 */
    PWMA_CCER1 = 0x05;           /* CH1+CH2 使能 */

    PWMA_ARRH  = 0x00;
    PWMA_ARRL  = 255;            /* period=256, 8-bit */
    PWMA_CCR1H = 0x00;
    PWMA_CCR1L = 128;            /* 50% 初始 */
    PWMA_PSCRH = 0x00;
    PWMA_PSCRL = 0x00;           /* prescaler=0, 载波 ~176kHz */

    PWMA_PS = (PWMA_PS & ~0x03) | 0x01;  /* P2.0 */
    PWMA_ENO = 0x01;
    PWMA_BKR = 0x80;
    PWMA_CR1 = 0x01;

    /* P_SW2 保持开启 */
}

/* ========== PWMA 定时器: 音频频率 (参考 buzzer_hx) ========== */
void pwma_timer_start(u16 reload) {
    if (reload == 0) {
        PWM1_CR1 = 0;
        PWM1_IER = 0;
        return;
    }
    PWM1_CNTRH = 0;
    PWM1_CNTRL = 0;
    PWM1_ARRH  = (u8)(reload >> 8);
    PWM1_ARRL  = (u8)(reload & 0xFF);
    PWM1_SR1   = 0x00;
    PWM1_IER   = 0x01;           /* 使能溢出中断 */
    PWM1_CR1   = 0x01;
}

/* ========== PWMA interrupt 26: 查表写 DAC ========== */
void PWM1_Interrupt(void) interrupt 26 {
    u16 acc;
    u8 idx, s;

    PWM1_SR1 = 0x00;

    acc = phase_acc + phase_step;
    phase_acc = acc;
    idx = (u8)(acc >> 11);        /* 高 5 位 → 0~31 */

    if (wave_type == WAVE_SQUARE)
        s = square_table[idx];
    else
        s = sine_table[idx];

    /* 音量调制 */
    if (pwm_range == 0)
        PWM1_CCR1L = 128;        /* 静音: 50% duty = 0V */
    else
        PWM1_CCR1L = (u8)(((u16)s * pwm_range) >> 8);
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

        /* 每 8 音符换波形 */
        if (note_in_phrase >= 8) {
            note_in_phrase = 0;
            wave_type = !wave_type;
        }

        if (freq_reload) {
            /* 45MHz 下 interrupt 26 频率翻倍 = 音高 +1 八度
               再降 2 八度 = 用 twinkle 索引对应 Musical_Scale 低 2 八度
               twinkle[11~18] → Musical_Scale[35~42] 但表只有 0~35
               所以: 用原始索引减 12 得到低八度, 再减 12 得到低 2 八度
               11-24 = 负数... 换思路: 直接乘 2 补偿 45MHz */
            freq_reload = Musical_Scale[note_idx];
            freq_reload *= 2;        /* 补偿 45MHz (22MHz 的 ~2x) */
            pwma_timer_start(freq_reload);
            pwm_range = 128;         /* 音量 */
            /* 计算相位步进: freq ≈ MAIN_Fosc/2/reload, 适配 45MHz */
            /* Musical_Scale 是 22MHz 基准, 45MHz 下实际频率翻倍 */
            /* phase_step = freq * 32 * 65536 / 采样率, 采样率=2*freq(reload) */
            /* 简化: step ∝ reload, reload 越小频率越高 */
        } else {
            PWM1_CCR1L = 128;       /* 静音 */
            pwma_timer_start(0);
        }

        /* 音符时长 + 慢衰减 */
        {
            u16 sleep = twinkle[play_count + 1];
            while (sleep--) {
                if (pwm_range && (sleep & 0x01))
                    pwm_range -= 1;
                delay(2);
            }
        }

        play_count += 2;
        note_in_phrase++;
    }

    /* 播放完毕 */
    pwma_timer_start(0);
    pwm_range = 0;
    PWM1_CCR1L = 128;
    play_count = 0;
    note_in_phrase = 0;
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
    UART1_config();
    EA = 1;
    PrintString1("STC8H PWM DAC Demo\r\n");

    while (1) {
        /* 播放小星星 (sine/square 交替) */
        play_music();

        /* LED 流水 */
        P0 = led_val;
        led_val = _crol_(led_val, 1);
        delay(50);

        /* UART echo */
        if ((TX1_Cnt != RX1_Cnt) && (!B_TX1_Busy)) {
            SBUF = RX1_Buffer[TX1_Cnt];
            B_TX1_Busy = 1;
            if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
        }
    }
}
