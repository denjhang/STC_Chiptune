/*
 * STC8H8K64U SCC + AY8910 + SN76489 合成器
 * Keil C51 + stc8h.h, 48MHz
 *
 * PWMA PWM1 → P2.0: 8-bit DAC 载波
 * Timer0 ISR: 17640Hz, AY+SN 每 tick, SCC 每 5 tick (4410Hz)
 * Timer1:     UART1 波特率 115200
 *
 * 协议: Python 控制节拍
 *   [0xD2][port][reg][data] → SCC (4 字节)
 *   [0xA0][reg][data]       → AY8910 (3 字节)
 *   [0x50][data]            → SN76489 (2 字节)
 *   其他: 忽略
 */

#include "stc8h.h"
#include <intrins.H>
#include "types.h"

#define MAIN_Fosc       48000000L
#define Baudrate1       115200L
#define UART1_BUF_LENGTH 2048
#define SAMPLE_RATE     17640
#define SCC_RATE        4410

/* ========== 仿真核心 ========== */
#include "scc.h"
#include "ay8910.h"
#include "sn76489.h"
#include "gb.h"
#include "nes.h"

/* ========== 芯片活跃标志 (收到命令才 render) ========== */
bit scc_active;
bit ay_active;
bit sn_active;
bit gb_active;
bit nes_active;

/* ========== 16kHz tick (Timer0 ISR) ========== */
volatile u16 sample_tick;

/* ========== UART ========== */
u8  TX1_Cnt, RX1_Cnt;
bit B_TX1_Busy;
u8  xdata RX1_Buffer[UART1_BUF_LENGTH];

/* ========== LED ========== */
u8  led_val = 0xFE;

/* ========== 任务调度: Timer0 ISR 软件分频 ========== */
/* 11025 / 60 ≈ 184, 每 184 次 Timer0 ISR 处理一次任务 */
#define TASK_DIVIDER    294
static u16 task_div;

/* ========== PWMA PWM1 → P2.0 ========== */
void pwma_dac_init(void) {
    P_SW2 |= 0x80;
    PWMA_ENO   = 0x00;
    PWMA_CCER1 = 0x00;
    PWMA_CCER2 = 0x00;
    PWMA_CCMR1 = 0x68;
    PWMA_CCER1 = 0x05;
    PWMA_ARRH  = 0x00;
    PWMA_ARRL  = 255;
    PWM1_CCR1H = 0x00;
    PWM1_CCR1L = 128;
    PWMA_PSCRH = 0x00;
    PWMA_PSCRL = 0x00;
    PWMA_PS = (PWMA_PS & ~0x03) | 0x01;
    PWMA_ENO = 0x01;
    PWMA_BKR = 0x80;
    PWMA_CR1 = 0x01;
    /* P_SW2 保持开启，加速 PWM 访问 */
}

/* ========== Timer0: 11025Hz ========== */
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
    if (RI) {
        RI = 0;
        RX1_Buffer[RX1_Cnt] = SBUF;
        if (++RX1_Cnt >= UART1_BUF_LENGTH) RX1_Cnt = 0;
    }
    if (TI) { TI = 0; B_TX1_Busy = 0; }
}

/* ========== UART 命令协议 ========== */
/*
 *   [0xD2][port][reg][data] → SCC (4 字节)
 *   [0xA0][reg][data]       → AY8910 (3 字节)
 *   [0x50][data]            → SN76489 写寄存器 (2 字节)
 *   [0x51][variant]         → SN76489 变体选择 (2 字节)
 *     variant: 0=SN76489(15bit), 1=SegaVDP(16bit), 2=SN76489A(17bit)
 *   [0xB3][reg][data]       → GB DMG 寄存器写入 (3 字节)
 *   [0xB4][reg][data]       → NES APU 寄存器写入 (3 字节)
 *   其他: 忽略
 */

void process_uart(void) {
    u8 b, p, r, d;

    while (TX1_Cnt != RX1_Cnt) {
        b = RX1_Buffer[TX1_Cnt];
        if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;

        if (b == 0xD2) {
            scc_active = 1;
            if (TX1_Cnt == RX1_Cnt) break;
            p = RX1_Buffer[TX1_Cnt];
            if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
            if (TX1_Cnt == RX1_Cnt) break;
            r = RX1_Buffer[TX1_Cnt];
            if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
            if (TX1_Cnt == RX1_Cnt) break;
            d = RX1_Buffer[TX1_Cnt];
            if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
            scc_wr((p & 0x7F) << 1, r);
            scc_wr(((p & 0x7F) << 1) | 1, d);

        } else if (b == 0xA0) {
            /* AY8910: [0xA0][reg][data] */
            ay_active = 1;
            if (TX1_Cnt == RX1_Cnt) break;
            r = RX1_Buffer[TX1_Cnt];
            if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
            if (TX1_Cnt == RX1_Cnt) break;
            d = RX1_Buffer[TX1_Cnt];
            if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
            ay_wr(r, d);

        } else if (b == 0x50) {
            /* SN76489: [0x50][data] */
            sn_active = 1;
            if (TX1_Cnt == RX1_Cnt) break;
            d = RX1_Buffer[TX1_Cnt];
            if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
            sn_wr(d);

        } else if (b == 0x51) {
            /* SN76489 变体: [0x51][variant] */
            if (TX1_Cnt == RX1_Cnt) break;
            d = RX1_Buffer[TX1_Cnt];
            if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
            sn_set_variant(d);

        } else if (b == 0xB3) {
            /* GB DMG: [0xB3][reg][data] */
            gb_active = 1;
            if (TX1_Cnt == RX1_Cnt) break;
            r = RX1_Buffer[TX1_Cnt];
            if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
            if (TX1_Cnt == RX1_Cnt) break;
            d = RX1_Buffer[TX1_Cnt];
            if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
            gb_wr(r, d);

        } else if (b == 0xB4) {
            /* NES APU: [0xB4][reg][data] */
            nes_active = 1;
            if (TX1_Cnt == RX1_Cnt) break;
            r = RX1_Buffer[TX1_Cnt];
            if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
            if (TX1_Cnt == RX1_Cnt) break;
            d = RX1_Buffer[TX1_Cnt];
            if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
            nes_wr(r, d);

        } else {
            /* 忽略: wait, 未知命令等 */
        }
    }
}

/* ========== 开机音: AY C4 E4 G4 和弦 ========== */
#define BOOT_NOTE_TICKS 300
#define BOOT_DECAY_EVERY 15
#define LED_EVERY    8

static u16 test_cnt;
static u8  test_dec_cnt;
static u8  led_tick;
static bit test_active;

void test_start(void);
void test_start(void) {
    test_cnt = 0;
    test_dec_cnt = 0;
    test_active = 1;
    ay_active = 1;

    /* C4: freq=433 → R0=0xB1, R1=0x01 */
    ay_wr(0, 0xB1); ay_wr(1, 0x01);
    /* E4: freq=649 → R2=0x89, R3=0x02 */
    ay_wr(2, 0x89); ay_wr(3, 0x02);
    /* G4: freq=971 → R4=0xCB, R5=0x03 */
    ay_wr(4, 0xCB); ay_wr(5, 0x03);

    /* 混合器: 全部音调开启, 噪声关闭 */
    ay_wr(7, 0x00);

    /* 包络频率 */
    ay_wr(11, 0x91); ay_wr(12, 0x0C);
    /* 包络形状: decay once (continue=0, attack=1, alternate=0, hold=0 → 0x04) */
    ay_wr(13, 0x04);

    /* 3 通道启用包络 (bit4=1) */
    ay_wr(8, 0x10);
    ay_wr(9, 0x10);
    ay_wr(10, 0x10);
}

void test_tick(void) {
    if (!test_active) return;

    test_cnt++;

    if (test_cnt >= BOOT_NOTE_TICKS) {
        test_active = 0;
        ay_wr(8, 0x00);
        ay_wr(9, 0x00);
        ay_wr(10, 0x00);
        return;
    }
}

void led_tick_update(void) {
    led_tick++;
    if ((led_tick % LED_EVERY) == 0) {
        P0 = led_val;
        led_val = _crol_(led_val, 1);
    }
}

/* ========== Timer0 ISR: 音频 + 软件分频任务 ========== */
/* 17640Hz ISR, AY+SN 每 tick, SCC/GB/NES 每 4 tick (4410Hz) */
static u8 scc_tick_div;
static u8 gb_tick_div;
static u8 nes_tick_div;
static u8 scc_out = 128;
static s16 gb_out = 0;
static s16 nes_out = 0;

void timer0_isr(void) interrupt 1 {
    s16 mix;
    u8 out;

    if (scc_active && ++scc_tick_div >= 4) {
        scc_tick_div = 0;
        scc_out = scc_render();
    }

    if (gb_active && ++gb_tick_div >= 4) {
        gb_tick_div = 0;
        gb_out = gb_render();
    }

    if (nes_active && ++nes_tick_div >= 4) {
        nes_tick_div = 0;
        nes_out = nes_render();
    }

    mix = (s16)((u16)scc_out - 128);
    if (ay_active) mix += ay_render() << 1;
    if (sn_active) mix += sn_render() << 1;
    if (gb_active) mix += gb_out << 1;
    if (nes_active) mix += nes_out;

    if (mix > 127) mix = 127;
    if (mix < -128) mix = -128;
    out = 128 + (u8)mix;
    PWM1_CCR1L = out;
    sample_tick++;

    if (++task_div >= TASK_DIVIDER) {
        task_div = 0;
        process_uart();
        if (test_active) test_tick();
        led_tick_update();
    }
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
    scc_init();
    ay_init();
    sn_init();
    gb_init();
    nes_init();
    test_start();
    led_tick = 0;
    timer0_init();
    EA = 1;
    PrintString1("STC8H SCC Synth\r\n");

    while (1);
}
