/*
 * STC8H8K64U SCC + AY8910 合成器
 * Keil C51 + stc8h.h, 48MHz
 *
 * PWMA PWM1 → P2.0: 8-bit DAC 载波 (~176kHz)
 * Timer0 ISR: 11025Hz 采样率, scc_render() + ay_render() → PWM1_CCR1L
 * Timer1:     UART1 波特率 115200
 *
 * 协议: Python 控制节拍
 *   [0xD2][port][reg][data] → SCC (4 字节)
 *   [0xA0][reg][data]       → AY8910 (3 字节)
 *   其他: 忽略
 */

#include "stc8h.h"
#include <intrins.H>

#define MAIN_Fosc       48000000L
#define Baudrate1       115200L
#define UART1_BUF_LENGTH 2048
#define SAMPLE_RATE     11025
#define SCC_CHANS        5
#define SCC_WAVELEN      32
#define SCC_FREQ_BITS    16
#define SCC_CLOCK       3579545L

/* 预计算常量: step = (SCC_HALF_CLK / SAMPLE_RATE) << SCC_SHIFT / (freq+1)
 * = 81 * 131072 / (freq+1) = 10616832 / (freq+1) */
#define SCC_HALF_CLK    1789772UL
#define SCC_SHIFT       (SCC_FREQ_BITS + 1)  /* 17 */
#define SCC_STEP_BASE   (SCC_HALF_CLK / SAMPLE_RATE * (1UL << SCC_SHIFT))  /* 10616832 */

typedef unsigned char   u8;
typedef unsigned int    u16;
typedef unsigned long   u32;
typedef signed char     s8;
typedef signed int      s16;

/* ========== SCC 状态 ========== */
/* ISR 热路径: idata (快) */
static u32 idata scc_cnt[SCC_CHANS];
static u32 idata scc_step_val[SCC_CHANS];
static u8  idata scc_vol[SCC_CHANS];
static u8  idata scc_key[SCC_CHANS];
/* 非热路径: xdata (省 idata 空间) */
static u16 xdata scc_freq[SCC_CHANS];
static u8  xdata scc_wav[SCC_CHANS][SCC_WAVELEN];
static u8  xdata scc_creg;
static u8  xdata scc_tst;

/* ========== AY8910 状态 ========== */
#define AY_CHANS    3
#define AY_CLK      1789772UL
#define AY_GETA_BITS 24
/* base_incr = CLK * (1 << 24) / 8 / RATE = 1789772 * 16777216 / 8 / 11025 = 340446710 */
#define AY_BASE_INCR   340446710UL

static u8  xdata ay_reg[16];
static u16 xdata ay_count[AY_CHANS];
static u8  xdata ay_freq_lo[AY_CHANS];
static u8  xdata ay_freq_hi[AY_CHANS];
static u8  xdata ay_edge[AY_CHANS];
static u8  xdata ay_tmask[AY_CHANS];
static u8  xdata ay_nmask[AY_CHANS];
static u16 xdata ay_env_freq;
static u32 xdata ay_env_count;
static u8  xdata ay_env_step;
static u8  xdata ay_env_attack;
static u8  xdata ay_env_continue, ay_env_alternate, ay_env_hold, ay_env_pause;
static u32 xdata ay_noise_seed;
static u8  xdata ay_noise_scaler;
static u8  xdata ay_noise_count;
static u8  xdata ay_noise_freq;
static u8  xdata ay_volume[AY_CHANS];
static u32 xdata ay_base_count;

/* AY-3-8910 音量表 (16 steps) */
static u8 code ay_voltbl[32] = {
    0x00, 0x00, 0x03, 0x03, 0x04, 0x04, 0x06, 0x06,
    0x09, 0x09, 0x0D, 0x0D, 0x12, 0x12, 0x1D, 0x1D,
    0x22, 0x22, 0x37, 0x37, 0x4D, 0x4D, 0x62, 0x62,
    0x82, 0x82, 0xA6, 0xA6, 0xD0, 0xD0, 0xFF, 0xFF
};

s16 ay_render(void);

/* 寄存器写掩码 */
static u8 code ay_regmsk[16] = {
    0xff, 0x0f, 0xff, 0x0f, 0xff, 0x0f, 0x1f, 0x3f,
    0x1f, 0x1f, 0x1f, 0xff, 0xff, 0x0f, 0xff, 0xff
};

/* ========== 16kHz tick (Timer0 ISR) ========== */
volatile u16 sample_tick;

/* ========== SCC 初始化 ========== */
void scc_init_func(void) {
    u8 i, j;
    for (i = 0; i < SCC_CHANS; i++) {
        scc_cnt[i] = 0;
        scc_freq[i] = 0;
        scc_step_val[i] = 0;
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
                {
                    u32 f = (u32)scc_freq[chi] + 1;
                    if (f < 9) {
                        scc_step_val[chi] = 0;
                    } else {
                        scc_step_val[chi] = SCC_STEP_BASE / f;
                    }
                }
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
/*
 * counter += step[u32]; offs = (counter >> FREQ_BITS) & 0x1F
 * step 范围: freq=100->step~145000, freq=4095->step~3579
 */

s16 scc_and_ay_render(void) {
    s16 mix;
    u8 i;
    u8 vol, offs, b;
    s16 tmp;

    mix = 0;
    for (i = 0; i < SCC_CHANS; i++) {
        if (scc_step_val[i] > 0) {
            scc_cnt[i] += scc_step_val[i];
            if (scc_key[i]) {
                offs = (u8)(scc_cnt[i] >> SCC_FREQ_BITS) & 0x1F;
                vol = scc_vol[i];
                b = scc_wav[i][offs];
                if (b >= 128)
                    tmp = -(((s16)(256 - (u16)b) * (u16)vol) >> 4);
                else
                    tmp = ((s16)(u16)b * (u16)vol) >> 4;
                mix += tmp;
            }
        }
    }
    mix += ay_render();
    if (mix > 127) mix = 127;
    if (mix < -128) mix = -128;
    return 128 + (u8)mix;
}

/* ========== AY8910 初始化 ========== */
void ay_init(void) {
    u8 i;
    for (i = 0; i < 16; i++) ay_reg[i] = 0;
    for (i = 0; i < AY_CHANS; i++) {
        ay_count[i] = 0;
        ay_freq_lo[i] = 0;
        ay_freq_hi[i] = 0;
        ay_edge[i] = 0;
        ay_tmask[i] = 0;
        ay_nmask[i] = 0;
        ay_volume[i] = 0;
    }
    ay_env_freq = 0;
    ay_env_count = 0;
    ay_env_step = 0;
    ay_env_attack = 0;
    ay_env_continue = 0;
    ay_env_alternate = 0;
    ay_env_hold = 0;
    ay_env_pause = 0;
    ay_noise_seed = 1;
    ay_noise_scaler = 0;
    ay_noise_count = 0;
    ay_noise_freq = 0;
    ay_base_count = 0;
}

/* ========== AY8910 写寄存器 ========== */
void ay_wr(u8 reg, u8 val) {
    u8 c;
    u16 freq;

    if (reg > 15) return;
    val &= ay_regmsk[reg];
    ay_reg[reg] = val;

    switch (reg) {
    case 0: case 2: case 4:
    case 1: case 3: case 5:
        c = reg >> 1;
        freq = ((u16)ay_reg[c * 2 + 1] & 0x0F) << 8;
        freq |= ay_reg[c * 2];
        ay_freq_lo[c] = ay_reg[c * 2];
        ay_freq_hi[c] = ay_reg[c * 2 + 1] & 0x0F;
        break;
    case 6:
        ay_noise_freq = val & 31;
        break;
    case 7:
        ay_tmask[0] = (val & 1) ? 1 : 0;
        ay_tmask[1] = (val & 2) ? 1 : 0;
        ay_tmask[2] = (val & 4) ? 1 : 0;
        ay_nmask[0] = (val & 8) ? 1 : 0;
        ay_nmask[1] = (val & 16) ? 1 : 0;
        ay_nmask[2] = (val & 32) ? 1 : 0;
        break;
    case 8: case 9: case 10:
        ay_volume[reg - 8] = val;
        break;
    case 11: case 12:
        ay_env_freq = ((u16)ay_reg[12] << 8) + ay_reg[11];
        break;
    case 13:
        ay_env_continue = (val >> 3) & 1;
        ay_env_attack   = (val >> 2) & 1;
        ay_env_alternate= (val >> 1) & 1;
        ay_env_hold     = val & 1;
        ay_env_pause    = 0;
        ay_env_step     = ay_env_attack ? 0 : 0x0F;
        break;
    }
}

/* ========== AY8910 渲染 ========== */
s16 ay_render(void) {
    u8 i, incr, noise;
    u16 freq;
    u16 ch_out;
    s16 mix;
    u8 vol_idx, vol_val;

    ay_base_count += AY_BASE_INCR;
    incr = (u8)(ay_base_count >> AY_GETA_BITS);
    ay_base_count &= (1UL << AY_GETA_BITS) - 1;

    /* Envelope */
    if (incr > 0) {
        ay_env_count += incr;
        if (ay_env_freq > 0 && ay_env_count >= ay_env_freq) {
            if (!ay_env_pause) {
                ay_env_step--;
            }
            if (ay_env_step == 0xFF) {
                if (ay_env_hold) {
                    if (ay_env_alternate) ay_env_attack ^= 0x0F;
                    ay_env_pause = 1;
                    ay_env_step = 0;
                } else {
                    if (ay_env_alternate && ay_env_step & 0x10)
                        ay_env_attack ^= 0x0F;
                    ay_env_step = 0x0F;
                }
            }
            if (ay_env_freq >= incr)
                ay_env_count -= ay_env_freq;
            else
                ay_env_count = 0;
        }

        /* Noise */
        ay_noise_count += incr;
        if (ay_noise_freq > 0 && ay_noise_count >= ay_noise_freq) {
            ay_noise_scaler ^= 1;
            if (ay_noise_scaler) {
                if (ay_noise_seed & 1)
                    ay_noise_seed ^= 0x24000;
                ay_noise_seed >>= 1;
            }
            if (ay_noise_freq >= incr)
                ay_noise_count -= ay_noise_freq;
            else
                ay_noise_count = 0;
        }
    }
    noise = ay_noise_seed & 1;

    /* Tone channels */
    mix = 0;
    for (i = 0; i < AY_CHANS; i++) {
        if (incr > 0) {
            freq = ((u16)ay_freq_hi[i] << 8) | ay_freq_lo[i];
            ay_count[i] += incr;
            if (freq > 0 && ay_count[i] >= freq) {
                ay_edge[i] = !ay_edge[i];
                if (freq >= incr)
                    ay_count[i] -= freq;
                else
                    ay_count[i] = 0;
            }
        }

        ch_out = 0;
        if ((ay_tmask[i] || ay_edge[i]) && (ay_nmask[i] || noise)) {
            vol_idx = ay_volume[i] & 0x0F;
            if (ay_volume[i] & 0x10)
                vol_idx = ay_env_step ^ ay_env_attack;
            vol_val = ay_voltbl[vol_idx];
            ch_out = (u16)vol_val << 4;
        }
        /* AY 输出 0~0xFF0, 缩放到 SCC 的 -128~127 范围 */
        mix += (s16)((u16)ch_out >> 4) - 8;
    }
    return mix;
}

/* ========== UART ========== */
u8  TX1_Cnt, RX1_Cnt;
bit B_TX1_Busy;
u8  xdata RX1_Buffer[UART1_BUF_LENGTH];

/* ========== LED ========== */
u8  led_val = 0xFE;

/* ========== 任务调度: Timer0 ISR 软件分频 ========== */
/* 11025 / 60 ≈ 184, 每 184 次 Timer0 ISR 处理一次任务 */
#define TASK_DIVIDER    184
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

/* ========== UART → SCC ========== */
/*
 * Python 控制节拍, 固件只做 SCC 写入:
 *   [0xD2][port][reg][data] → SCC (4 字节, 波形/频率/音量/keyon)
 *   [0xA0][reg][data]       → AY8910 (预留)
 *   其他: 忽略
 */

void process_uart(void) {
    u8 b, p, r, d;

    while (TX1_Cnt != RX1_Cnt) {
        b = RX1_Buffer[TX1_Cnt];
        if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;

        if (b == 0xD2) {
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
            if (TX1_Cnt == RX1_Cnt) break;
            r = RX1_Buffer[TX1_Cnt];
            if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
            if (TX1_Cnt == RX1_Cnt) break;
            d = RX1_Buffer[TX1_Cnt];
            if (++TX1_Cnt >= UART1_BUF_LENGTH) TX1_Cnt = 0;
            ay_wr(r, d);

        } else {
            /* 忽略: wait, 未知命令等 */
        }
    }
}

/* ========== 开机音: C4 → G4 ========== */
#define BOOT_NOTE_TICKS 180
#define BOOT_DECAY_EVERY 12
#define LED_EVERY    8

static u16 test_cnt;
static u8  test_dec_cnt;
static u8  led_tick;
static bit test_active;

void test_start(void);
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

    test_cnt = 0;
    test_dec_cnt = 0;
    test_active = 1;

    /* C4: freq=1000
     * step = 1789772 / 1001 * 131072 / 16000 = 1785 * 131072 / 16000 = 14632 */
    scc_freq[0] = 1000;
    scc_step_val[0] = (1789772UL / 1001UL) * 131072UL / 16000UL;
    scc_cnt[0] = 0;
    scc_vol[0] = 15;
    scc_key[0] = 1;
}

void test_tick(void) {
    if (!test_active) return;

    test_cnt++;
    test_dec_cnt++;

    if (test_cnt == BOOT_NOTE_TICKS) {
        /* G4: freq=1587
         * step = 1789772 / 1588 * 131072 / 16000 = 1127 * 131072 / 16000 = 9236 */
        scc_freq[0] = 1587;
        scc_step_val[0] = (1789772UL / 1588UL) * 131072UL / 16000UL;
        scc_cnt[0] = 0;
        scc_vol[0] = 15;
    }

    if (test_cnt >= BOOT_NOTE_TICKS * 2) {
        test_active = 0;
        scc_key[0] = 0;
        scc_vol[0] = 0;
        return;
    }

    if (test_dec_cnt >= BOOT_DECAY_EVERY) {
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

/* ========== Timer0 ISR: 音频 + 软件分频任务 ========== */
void timer0_isr(void) interrupt 1 {
    u8 out;
    out = scc_and_ay_render();
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
    scc_init_func();
    ay_init();
    test_start();
    led_tick = 0;
    timer0_init();
    EA = 1;
    PrintString1("STC8H SCC Synth\r\n");

    while (1);
}
