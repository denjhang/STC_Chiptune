/*
 * STC32G12K128 多音源合成器
 * Keil C251, 35MHz IRC
 *
 * PWMA PWM1 -> P2.0: 8-bit DAC 载波
 * Timer0 ISR: 17640Hz, AY+SN 每 tick, SCC/GB/NES/SAA 每 4 tick (4410Hz)
 * Timer1:     UART1 波特率 115200
 *
 * 协议: 与 VGM 标准命令字节一致, Python 直接透传
 *   [0x50][data]            -> SN76489 (2 字节)
 *   [0x51][subcmd][...]     -> FM 合成 (自定义, 2-19 字节)
 *   [0xA0][reg][data]       -> AY8910 (3 字节)
 *   [0xB0][addr][data][xor]  -> Gigatron (4 字节, XOR校验)
 *   [0xC0][addr][data][xor]  -> WT Wavetable (4 字节, XOR校验ACK)
 *   0xC0 寄存器:
 *     0x00-0x03: ch0-3 note on (MIDI note)
 *     0x04-0x07: ch0-3 note off
 *     0x08-0x0B: ch0-3 volume (0-31)
 *     0x10-0x12: ADSR
 *     0x13: wave select (0-5)
 *   [0xB3][reg][data]       -> GB DMG (3 字节)
 *   [0xB4][reg][data]       -> NES APU (3 字节)
 *   [0xBD][addr][data]      -> SAA1099 (3 字节)
 *   [0xD2][port][reg][data] -> SCC (4 字节)
 *   [0x52][variant]         -> SN76489 变体 (自定义, 2 字节)
 *
 * FM 寄存器 (0x51 后跟, OPLL 分页结构):
 *   0x00-0x09: 音色参数 (全局共用)
 *   [0x10-0x13][note]      -> Note On (voice 0-3)
 *   [0x20-0x23]            -> Note Off (voice 0-3)
 *   [0x30-0x33][vol]       -> Volume override (voice 0-3)
 */

#pragma LARGE
#pragma OPTIMIZE(8, SPEED)

#include "STC32G.H"
#include <intrins.h>
#include "types.h"

#define MAIN_Fosc       38000000L
#define Baudrate1       115200L
#define UART1_BUF_LENGTH 2048
#define SAMPLE_RATE     17640
#define SCC_RATE        17640

/* ========== 仿真核心 ========== */
#include "scc.h"
#include "ay8910.h"
#include "sn76489.h"
#include "fm.h"
#include "gigatron.h"
#include "wt.h"
#include "adpcm.h"
/* 暂不启用: #include "gb.h" #include "nes.h" #include "saa1099.h" */

/* ========== 芯片活跃标志 ========== */
bit scc_active;
bit ay_active;
bit sn_active;
bit fm_active;
bit gt_active;
bit wt_active;
bit pcm_active;
/* gb/nes/saa 暂不启用 */

/* ========== 16kHz tick ========== */
volatile u16 sample_tick;

/* ========== UART ========== */
u16 TX1_Cnt, RX1_Cnt;
bit B_TX1_Busy;
u8  RX1_Buffer[UART1_BUF_LENGTH];

/* ========== LED ========== */
u8  led_val = 0xFE;
u8  led_dir = 0;

/* ========== 任务调度 ========== */
#define TASK_DIVIDER    294
static u16 task_div;

/* ========== PWM1 P/P2.0 端口选择 ========== */
#define PWM1_1      0x01
#define ENO1P       0x01

/* ========== PWMA PWM1 -> P2.0, 8-bit DAC ========== */
void pwma_dac_init(void) {
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
    PWMA_PS = (PWMA_PS & ~0x03) | PWM1_1;
    PWMA_ENO = ENO1P;
    PWMA_BKR = 0x80;
    PWMA_CR1 = 0x01;
}

/* ========== Timer0: 17640Hz ========== */
void timer0_init(void) {
    u32 reload;
    AUXR |= 0x80;
    TMOD &= 0xF0;
    reload = 65536UL - MAIN_Fosc / SAMPLE_RATE;
    TH0 = (u8)(reload >> 8);
    TL0 = (u8)(reload & 0xFF);
    ET0 = 1;
    TR0 = 1;
}

/* ========== UART1 ========== */
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
 * VGM 命令 (0x50/0x52/0xA0/0xB3/0xB4/0xBD/0xD2): 直接透传, 不校验不回ACK
 * FM 命令 (0x51): [0x51][addr][data][xor] XOR校验, 通过回0xAA, 失败回0xFF
 */
#define ACK_OK   0xAA
#define ACK_ERR  0xFF

static void uart_send_ack(u8 ack) {
    while (B_TX1_Busy);
    SBUF = ack;
    B_TX1_Busy = 1;
}

void process_uart(void) {
    u8 b, p, r, d, chk, calc;

    while (TX1_Cnt != RX1_Cnt) {
        b = RX1_Buffer[TX1_Cnt];
        if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;

        if (b == 0x50) {
            /* SN76489: [0x50][data] */
            if (TX1_Cnt == RX1_Cnt) break;
            d = RX1_Buffer[TX1_Cnt];
            if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
            sn_active = 1;
            sn_wr(d);

        } else if (b == 0x52) {
            /* SN76489 变体: [0x52][variant] */
            if (TX1_Cnt == RX1_Cnt) break;
            d = RX1_Buffer[TX1_Cnt];
            if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
            sn_set_variant(d);

        } else if (b == 0x51) {
            /* FM: [0x51][addr][data][xor] 校验+ACK */
            if (TX1_Cnt == RX1_Cnt) break;
            r = RX1_Buffer[TX1_Cnt];
            if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
            if (TX1_Cnt == RX1_Cnt) break;
            d = RX1_Buffer[TX1_Cnt];
            if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
            if (TX1_Cnt == RX1_Cnt) break;
            chk = RX1_Buffer[TX1_Cnt];
            if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
            calc = 0x51 ^ r ^ d;
            if (chk != calc) { uart_send_ack(ACK_ERR); continue; }
            fm_active = 1;
            fm_wr(r, d);
            uart_send_ack(ACK_OK);

        } else if (b == 0xA0) {
            /* AY8910: [0xA0][reg][data] */
            if (TX1_Cnt == RX1_Cnt) break;
            r = RX1_Buffer[TX1_Cnt];
            if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
            if (TX1_Cnt == RX1_Cnt) break;
            d = RX1_Buffer[TX1_Cnt];
            if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
            ay_active = 1;
            ay_wr(r, d);

        } else if (b == 0xB3) {
            /* GB DMG: 暂不启用 */

        } else if (b == 0xB0) {
            /* Gigatron: [0xB0][addr][data][xor] 校验丢弃, 无ACK */
            if (TX1_Cnt == RX1_Cnt) break;
            r = RX1_Buffer[TX1_Cnt];
            if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
            if (TX1_Cnt == RX1_Cnt) break;
            d = RX1_Buffer[TX1_Cnt];
            if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
            if (TX1_Cnt == RX1_Cnt) break;
            chk = RX1_Buffer[TX1_Cnt];
            if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
            calc = 0xB0 ^ r ^ d;
            if (chk != calc) continue;
            gt_active = 1;
            gt_wr(r, d);

        } else if (b == 0xC0) {
            /* WT/PCM: [0xC0][addr][data][xor] 校验+ACK */
            if (TX1_Cnt == RX1_Cnt) break;
            r = RX1_Buffer[TX1_Cnt];
            if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
            if (TX1_Cnt == RX1_Cnt) break;
            d = RX1_Buffer[TX1_Cnt];
            if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
            if (TX1_Cnt == RX1_Cnt) break;
            chk = RX1_Buffer[TX1_Cnt];
            if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
            calc = 0xC0 ^ r ^ d;
            if (chk != calc) { uart_send_ack(ACK_ERR); continue; }
            if (r >= 0x15 && r <= 0x33) {
                pcm_active = 1;
                pcm_wr(r, d);
            } else {
                wt_active = 1;
                wt_wr(r, d);
            }
            uart_send_ack(ACK_OK);

        } else if (b == 0xB4) {
            /* NES APU: 暂不启用 */

        } else if (b == 0xBD) {
            /* SAA1099: 暂不启用 */

        } else if (b == 0xD2) {
            /* SCC: [0xD2][port][reg][data] */
            if (TX1_Cnt == RX1_Cnt) break;
            p = RX1_Buffer[TX1_Cnt];
            if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
            if (TX1_Cnt == RX1_Cnt) break;
            r = RX1_Buffer[TX1_Cnt];
            if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
            if (TX1_Cnt == RX1_Cnt) break;
            d = RX1_Buffer[TX1_Cnt];
            if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
            scc_active = 1;
            scc_wr((p & 0x7F) << 1, r);
            scc_wr(((p & 0x7F) << 1) | 1, d);

        } else {
            /* 忽略未知命令 */
        }
    }
}

/* ========== 开机音: AY C4 E4 G4 和弦 ========== */
#define BOOT_NOTE_TICKS 300
#define LED_EVERY    1

static u16 test_cnt;
static u8  led_tick;
static bit test_active;

void test_start(void) {
    test_cnt = 0;
    test_active = 1;
    ay_active = 1;

    ay_wr(0, 0xB1); ay_wr(1, 0x01);
    ay_wr(2, 0x89); ay_wr(3, 0x02);
    ay_wr(4, 0xCB); ay_wr(5, 0x03);
    ay_wr(7, 0x00);
    ay_wr(11, 0x91); ay_wr(12, 0x0C);
    ay_wr(13, 0x04);
    ay_wr(8, 0x10);
    ay_wr(9, 0x10);
    ay_wr(10, 0x10);
}

void test_tick(void) {
    if (!test_active) return;
    test_cnt++;
    if (test_cnt >= BOOT_NOTE_TICKS) {
        test_active = 0;
        ay_active = 0;
        ay_wr(8, 0x00);
        ay_wr(9, 0x00);
        ay_wr(10, 0x00);
    }
}

static bit led_music_mode;
static u16 led_silent_cnt;
#define LED_SILENT_WAIT 180

void led_tick_update(void) {
    u8 mask;
    led_tick++;
    if (led_music_mode) {
        led_silent_cnt++;
        if (led_silent_cnt >= LED_SILENT_WAIT) {
            led_music_mode = 0;
        }
    }
    if ((led_tick % LED_EVERY) == 0) {
        mask = 0;
        if (fm_active) mask |= fm_channel_mask();
        if (gt_active) mask |= gt_channel_mask();
        if (wt_active) mask |= wt_channel_mask() & 0x0F;
        if (pcm_active) mask |= pcm_channel_mask() << 2;
        if (ay_active) mask |= ay_channel_mask() << 3;
        if (sn_active) mask |= sn_channel_mask() << 4;

        if (mask) {
            P0 = ~mask;
            led_music_mode = 1;
            led_silent_cnt = 0;
        } else if (!led_music_mode) {
            P0 = led_val;
            if (led_dir) {
                led_val = _cror_(led_val, 1);
                if (led_val == 0xFE) led_dir = 0;
            } else {
                led_val = _crol_(led_val, 1);
                if (led_val == 0x7F) led_dir = 1;
            }
        }
    }
}

/* ========== Timer0 ISR: 17640Hz ========== */
static u8 scc_tick_div;
static u8 scc_out = 128;
static u8 gt_tick_div;
static s16 gt_out;
static s16 wt_out;

void timer0_isr(void) interrupt 1 {
    s16 mix;
    u8 out;

    if (scc_active) {
        scc_out = scc_render();
    }

    if (gt_active) {
        if (++gt_tick_div >= 2) {
            gt_tick_div = 0;
            gt_out = gt_render();
        }
    }

    if (wt_active) {
        wt_out = wt_render();
        if (!wt_channel_mask()) wt_active = 0;
    }

    /* gb/nes/saa 暂不启用 */

    mix = 0;
    if (scc_active) mix += ((s16)((u16)scc_out - 128)) * 3 / 8;
    if (ay_active) mix += ay_render() * 3 / 2;
    if (sn_active) mix += sn_render() * 3 / 4;
    if (fm_active) mix += fm_render() * 3 / 2;
    if (gt_active) mix += gt_out * 3 / 2;
    if (wt_active) mix += wt_out * 3 / 2;
    if (pcm_active) {
        mix += pcm_render() * 3 / 2;
        if (!pcm_channel_mask()) pcm_active = 0;
    }
    if (mix > 127) mix = 127;
    if (mix < -128) mix = -128;
    out = 128 + (u8)mix;
    PWMA_CCR1L = out;
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
    WTST = 0;
    EAXFR = 1;
    CKCON = 0;

    P0M0=0; P0M1=0;
    P1M0=0; P1M1=0;
    P2M0=0; P2M1=0;
    P3M0=0; P3M1=0;
    P4M0=0; P4M1=0;
    P5M0=0; P5M1=0;
    P6M0=0; P6M1=0;
    P7M0=0; P7M1=0;

    P0 = 0xFF;

    pwma_dac_init();
    UART1_config();
    scc_init();
    ay_init();
    sn_init();
    fm_init();
    gt_init();
    wt_init();
    pcm_init();
    /* gb/nes/saa 暂不启用 */
    test_start();
    led_tick = 0;
    timer0_init();
    EA = 1;
    PrintString1("STC32G Chiptune Synth\r\n");

    while (1);
}
