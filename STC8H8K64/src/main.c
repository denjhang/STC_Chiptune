/*
 * STC8H8K64U SCC 合成器
 * Keil C51 + stc8h.h, 45.1584MHz
 *
 * PWMA PWM1 → P2.0: 8-bit DAC 载波 (~176kHz)
 * Timer0 ISR: 16kHz 采样率, scc_render() → PWM1_CCR1L
 * Timer1:     UART1 波特率 230400
 *
 * SCC 移植自 RPFM/rpfm/emu/scc.c
 */

#include "stc8h.h"
#include <intrins.H>

#define MAIN_Fosc       45158400L
#define Baudrate1       230400L
#define UART1_BUF_LENGTH 128
#define SAMPLE_RATE     16000
#define SCC_CHANS        5
#define SCC_WAVELEN      32

typedef unsigned char   u8;
typedef unsigned int    u16;
typedef unsigned long   u32;
typedef signed char     s8;
typedef signed int      s16;

/* ========== SCC 状态 (平坦 xdata) ========== */
static u32 xdata scc_cnt[SCC_CHANS];
static u16 xdata scc_freq[SCC_CHANS];
static u8  xdata scc_vol[SCC_CHANS];
static u8  xdata scc_key[SCC_CHANS];
static u16 xdata scc_step[SCC_CHANS];
static u8  xdata scc_wav[SCC_CHANS][SCC_WAVELEN];
static u8  xdata scc_creg;
static u8  xdata scc_tst;

/* ========== SCC 初始化 ========== */
void scc_init_func(void) {
    u8 i, j;
    for (i = 0; i < SCC_CHANS; i++) {
        scc_cnt[i] = 0;
        scc_freq[i] = 0;
        scc_vol[i] = 0;
        scc_key[i] = 0;
        for (j = 0; j < SCC_WAVELEN; j++)
            scc_wav[i][j] = 0;
    }
    scc_creg = 0;
    scc_tst = 0;
}

/* ========== SCC 写寄存器 ========== */
void scc_wr(u8 port, u8 dat) {
    u8 off, chi, hi, lo;

    if (port & 1) {
        switch (port >> 1) {
        case 0:
        case 4:
            off = scc_creg;
            if (scc_tst & 0x40) return;
            scc_wav[off >> 5][off & 0x1f] = dat;
            break;
        case 1:
            off = scc_creg;
            chi = off >> 1;
            if (chi < SCC_CHANS) {
                if (off & 1) {
                    hi = dat & 0x0F;
                    lo = scc_freq[chi] & 0xFF;
                    scc_freq[chi] = ((u16)hi << 8) | lo;
                } else {
                    hi = scc_freq[chi] & 0x0F00;
                    scc_freq[chi] = hi | dat;
                }
                scc_step[chi] = (u16)(11568768UL / ((u32)scc_freq[chi] + 1));
            }
            break;
        case 2:
            chi = scc_creg & 0x07;
            if (chi < SCC_CHANS)
                scc_vol[chi] = dat & 0x0F;
            break;
        case 3:
            for (chi = 0; chi < SCC_CHANS; chi++)
                scc_key[chi] = (dat >> chi) & 1;
            break;
        case 5:
            scc_tst = dat;
            break;
        default:
            break;
        }
    } else {
        scc_creg = dat;
    }
}

/* ========== SCC 渲染 ========== */
u8 scc_render(void) {
    s16 mix;
    u8 i;
    u16 step;
    u8 vol, offs, b;
    s16 tmp;

    mix = 0;
    for (i = 0; i < SCC_CHANS; i++) {
        step = scc_step[i];
        if (step > 0) {
            scc_cnt[i] += step;
            if (scc_key[i]) {
                offs = (u8)(scc_cnt[i] >> 12) & 0x1F;
                vol = scc_vol[i];
                b = scc_wav[i][offs];
                /* b 是 u8 (0~255), 但存的是 s8 波形 (-64~63)
                   取值 >= 128 时为负 */
                if (b >= 128)
                    tmp = -(((s16)(256 - (u16)b) * (u16)vol) >> 4);
                else
                    tmp = ((s16)(u16)b * (u16)vol) >> 4;
                mix += tmp;
            }
        }
    }
    if (mix > 127) mix = 127;
    if (mix < -128) mix = -128;
    return 128 + (u8)mix;
}

/* ========== UART ========== */
u8  TX1_Cnt, RX1_Cnt;
bit B_TX1_Busy;
u8  xdata RX1_Buffer[UART1_BUF_LENGTH];

/* ========== LED ========== */
u8  led_val = 0xFE;

volatile u16 vd;

void delay(u16 i) {
    u16 j, k;
    for (j = 0; j < 500; j++)
        for (k = 0; k < i; k++);
}

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

void timer0_isr(void) interrupt 1 {
    u8 out;
    out = scc_render();
    P_SW2 |= 0x80;
    PWM1_CCR1L = out;
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
    if (RI) {
        RI = 0;
        RX1_Buffer[RX1_Cnt] = SBUF;
        if (++RX1_Cnt >= UART1_BUF_LENGTH) RX1_Cnt = 0;
    }
    if (TI) { TI = 0; B_TX1_Busy = 0; }
}

/* ========== 前向声明 ========== */
void test_start(void);

/* ========== VGM/UART → SCC 协议 ========== */
/*
 * 协议:
 *
 * [0xD2] [port] [reg] [data]  — SCC (VGM 标准, 4 字节)
 *                                内部展开: scc_wr((port<<1), reg) + scc_wr((port<<1)|1, data)
 * [port]  [data]              — SCC 简写（无前缀, 2 字节）→ 直接 scc_wr(port, data)
 * [0xA0] [reg]  [data]       — AY8910 (预留, TODO)
 * [0xFF]  [ticks]            — Wait N main-loop ticks
 * [0xFE]                    — 关闭测试播放, 切 UART 控制
 * [0xFD]                    — 开启测试播放
 */

static u8  vgm_wait;       /* wait 计数器, >0 时暂停命令处理 */
static bit test_active;     /* 1=内置测试播放, 0=UART 控制 */

void process_uart(void) {
    u8 b, p, r, d;
    while (TX1_Cnt != RX1_Cnt) {
        if (vgm_wait > 0) {
            vgm_wait--;
            return;
        }
        b = RX1_Buffer[TX1_Cnt];
        if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;

        if (b == 0xD2) {
            /* VGM 0xD2: [0xD2][port][reg][data] → scc_wr(port<<1, reg) + scc_wr(port<<1|1, data) */
            if (TX1_Cnt != RX1_Cnt) {
                p = RX1_Buffer[TX1_Cnt];
                if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
            } else break;
            if (TX1_Cnt != RX1_Cnt) {
                r = RX1_Buffer[TX1_Cnt];
                if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
            } else break;
            if (TX1_Cnt != RX1_Cnt) {
                d = RX1_Buffer[TX1_Cnt];
                if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
            } else break;
            scc_wr((p & 0x7F) << 1, r);       /* latch register */
            scc_wr(((p & 0x7F) << 1) | 1, d);  /* write data */
        } else if (b == 0xA0) {
            /* AY8910 写入 (预留): [0xA0] [reg] [data] */
            /* TODO: ay8910_wr(p, d); */
            if (TX1_Cnt != RX1_Cnt) {
                if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
            }
            if (TX1_Cnt != RX1_Cnt) {
                if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
            }
        } else if (b == 0xFF) {
            /* Wait: [0xFF] [ticks] */
            if (TX1_Cnt != RX1_Cnt) {
                d = RX1_Buffer[TX1_Cnt];
                if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
                vgm_wait = d;
            }
        } else if (b == 0xFE) {
            test_active = 0;
            scc_key[0] = 0;  /* 关闭测试音 */
        } else if (b == 0xFD) {
            test_active = 1;
            test_start();
        } else {
            /* 简写格式: [port] [data] */
            if (TX1_Cnt != RX1_Cnt) {
                d = RX1_Buffer[TX1_Cnt];
                if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
                scc_wr(b, d);
            }
        }
    }
}

/* ========== 测试: 2 音交替 (C4/G4) — 非阻塞 ========== */
u16 code twn_freq[] = { 1000, 1587, 1000, 1587, 1000, 1587, 1000, 1587 };
#define TWN_LEN 8
#define NOTE_TICKS  4000   /* 每个 note 持续 4000 main loop ticks */
#define DECAY_EVERY 200    /* 每 200 ticks 衰减一次 */
#define LED_EVERY    100    /* 每 100 ticks 切 LED */

static u16 test_cnt;       /* 主循环 tick 计数 */
static u8  test_note;      /* 当前音符索引 */
static u8  test_dec_cnt;   /* 衰减子计数 */
static u8  led_tick;       /* LED 流水计数（UART 模式下也运行） */

void test_start(void) {
    u8 i;
    u8 code st[] = {
         0, 12, 25, 37, 49, 60, 71, 81,
        90, 98,105,111,115,118,120,127,
        127,120,118,115,111,105, 98, 90,
        81, 71, 60, 49, 37, 25, 12,  0
    };
    for (i = 0; i < 32; i++)
        scc_wav[0][i] = st[i];

    test_note = 0;
    test_cnt = 0;
    test_dec_cnt = 0;
    test_active = 1;

    /* 触发第一个音 */
    scc_freq[0] = twn_freq[0];
    scc_step[0] = (u16)(11568768UL / ((u32)twn_freq[0] + 1));
    scc_cnt[0] = 0;
    scc_vol[0] = 15;
    scc_key[0] = 1;
}

void test_tick(void) {
    if (!test_active) return;

    test_cnt++;
    test_dec_cnt++;

    /* 切换音符 */
    if (test_cnt >= NOTE_TICKS) {
        test_cnt = 0;
        test_dec_cnt = 0;
        test_note = (test_note + 1) % TWN_LEN;

        scc_freq[0] = twn_freq[test_note];
        scc_step[0] = (u16)(11568768UL / ((u32)twn_freq[test_note] + 1));
        scc_cnt[0] = 0;
        scc_vol[0] = 15;
        scc_key[0] = 1;
    }

    /* 音量衰减 */
    if (test_dec_cnt >= DECAY_EVERY) {
        test_dec_cnt = 0;
        if (scc_vol[0] > 0)
            scc_vol[0]--;
    }
}

void led_tick_update(void) {
    led_tick++;
    if ((led_tick % LED_EVERY) == 0) {
        P0 = led_val;
        led_val = _crol_(led_val, 1);
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
    timer0_init();
    UART1_config();
    scc_init_func();
    EA = 1;
    PrintString1("STC8H SCC Synth\r\n");

    test_start();
    led_tick = 0;

    while (1) {
        test_tick();
        led_tick_update();
        process_uart();
        delay(1);
    }
}
