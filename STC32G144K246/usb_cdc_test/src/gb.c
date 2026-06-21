/* gb.c - GameBoy DMG APU 仿真核心 (STC32G C251 版, ISR 极致优化)
 * 对齐 libvgm emu/cores/gb.c (Wilbert Pol, Anthony Kruize, BSD-3-Clause)
 *
 * 4 通道:
 *   1. 方波 + 扫频 + 包络 (NR10-14)
 *   2. 方波 + 包络       (NR21-24)
 *   3. 自定义波形 (Wave RAM, NR30-34)
 *   4. 噪声 + 包络       (NR41-44, AY 风格简化 LFSR)
 *
 * GB 频率公式: Hz = 131072 / (2048 - gb_freq)
 * Frame sequencer: clock/8192 = 512 Hz, 8 steps (length/sweep/envelope)
 *
 * ISR 极致优化 (对齐 NES/AY/SN/SCC, 详见 docs GB_INTEGRATION_STATUS.md §13):
 * - frame sequencer: cycles/8192 改 cycles>>13 (8192=2^13, 避 u32 真除法)
 * - noise: AY 风格 Galois LFSR (单次 if 代替 while 循环, 听感接近 AY 噪声)
 * - square: distance 预计算, cycles_left 用 s16
 * - 热路径变量 data 段 (直接寻址 1 机器周期)
 * - frame sequencer 跨 frame 单次 update (不双倍调用)
 * - 结构体瘦身: cycles_left s32→s16, duty_count u32→u8, 移除调试字段 */
#include "stc.h"
#include "gb.h"

/* ========== 寄存器地址 (与 libvgm 一致) ========== */
#define NR10 0x00
#define NR11 0x01
#define NR12 0x02
#define NR13 0x03
#define NR14 0x04
#define NR21 0x06
#define NR22 0x07
#define NR23 0x08
#define NR24 0x09
#define NR30 0x0A
#define NR31 0x0B
#define NR32 0x0C
#define NR33 0x0D
#define NR34 0x0E
#define NR41 0x10
#define NR42 0x11
#define NR43 0x12
#define NR44 0x13
#define NR50 0x14
#define NR51 0x15
#define NR52 0x16
#define AUD3W0 0x20

#define FRAME_CYCLES 8192
#define FRAME_SHIFT  13          /* log2(8192), 用 >> 代替 / */
#define FRAME_MASK   0x1FFF      /* FRAME_CYCLES - 1, 用 & 代替 % */

/* 方波 duty 表 (12.5%/25%/50%/75%) */
static const s8 wave_duty_table[4][8] = {
    { -1, -1, -1, -1, -1, -1, -1,  1 },
    {  1, -1, -1, -1, -1, -1, -1,  1 },
    {  1, -1, -1, -1, -1,  1,  1,  1 },
    { -1,  1,  1,  1,  1,  1,  1, -1 }
};

/* noise period 查表 (对齐 NES nes_noise_freq 风格, 避免 render 里重复算)
 * NR43: bit0-2 = divisor index (0-7), bit4-7 = shift (0-15)
 * period = divisor[idx] << shift, divisor = {8,16,32,48,64,80,96,112} */
static const u16 noise_div[8] = { 8, 16, 32, 48, 64, 80, 96, 112 };

/* ========== 通道状态结构 (瘦身版) ========== */
typedef struct {
    u8  reg[5];              /* 寄存器原始值 */
    u8  on;                  /* 通道是否开启 */
    u8  channel;             /* 通道号 1/2/3/4 */
    u8  length;              /* 长度计数器 */
    u8  length_mask;         /* 长度掩码 (0x3F 或 0xFF) */
    u8  length_counting;     /* 长度计数是否激活 */
    u8  length_enabled;      /* NRx4 bit6 写入后是否启用长度 */
    s16 cycles_left;         /* 相位累加器 (s16 够用, 每采样 ~190) */
    u8  duty;                /* 方波 duty 索引 0-3 */
    u8  envelope_enabled;    /* 包络是否激活 */
    s8  envelope_value;      /* 当前音量 0-15 */
    s8  envelope_direction;  /* 1=渐强, -1=渐弱 */
    u8  envelope_time;       /* 包络周期 */
    u8  envelope_count;      /* 包络计数器 */
    s8  signal;              /* 当前波形输出值 */
    u16 frequency;           /* 11-bit 频率 */
    u16 distance;            /* 预计算: 0x800 - frequency (square/wave 用) */
    u8  sweep_enabled;       /* 扫频激活 (仅 CH1) */
    u8  sweep_neg_mode_used; /* 扫频负方向已使用 */
    u8  sweep_shift;         /* 扫频移位 */
    s8  sweep_direction;     /* +1/-1 */
    u8  sweep_time;          /* 扫频周期 */
    u8  sweep_count;         /* 扫频计数器 */
    u8  level;               /* CH3 输出电平 (NR32 bit5-6) */
    u8  offset;              /* CH3 波形偏移 (0-31) */
    u16 frequency_counter;   /* square 当前相位位置 (libvgm 原版字段, duty 推进用) */
    u8  duty_count;          /* duty 步进计数器 (&0x07) */
    u8  noise_short;         /* CH4 7-bit LFSR 模式 */
    u16 noise_rng;           /* CH4 噪声 LFSR 状态 (AY 风格 Galois) */
} SOUND;

typedef struct {
    u8 on;
    u8 vol_left;
    u8 vol_right;
    u8 mode1_left, mode1_right;
    u8 mode2_left, mode2_right;
    u8 mode3_left, mode3_right;
    u8 mode4_left, mode4_right;
    u32 cycles;
} SOUNDC;

/* 热路径标量放 data 段 (直接寻址, 1 机器周期), 对齐 SCC scc_cnt 等.
 * SOUND 结构体较大 (~40 字节 × 4 = 160B), 全放 data 会和 SCC/USB 挤爆, 故留 xdata.
 * data 段只给 render 每采样必访的标量: base_count + ctrl. */
static SOUND xdata gb_snd1, xdata gb_snd2, xdata gb_snd3, xdata gb_snd4;
static SOUNDC xdata gb_ctrl;
static u8     xdata gb_regs[0x30];
static u32    data gb_base_count;

/* RC 高通滤波器状态 (模拟 DMG 硬件隔直电容):
 * DMG 真机 CPU 输出经 1μF 电容 + 510Ω + 10KΩ 电位器到放大器, 截止 15.14Hz.
 * 这个硬件高通: 1) 隔直消除 duty 不对称的直流 (12.5% duty 的 -0.75×env)
 *              2) 衰减次声波. 是 gbsplay 比 libvgm 音质干净的根本原因.
 * 标准一阶 RC 高通差分方程: y[n] = α × (y[n-1] + x[n] - x[n-1])
 * α = RC/(RC+dt) = 0.99570436 (fc=15.14Hz, fs=22050Hz), Q16 定点 = 65254. */
static s32    data gb_hp_y;       /* 上一次输出 y[n-1] */
static s32    data gb_hp_x;       /* 上一次输入 x[n-1] */
#define GB_HP_ALPHA     65254     /* Q16 定点的 α 系数 */

static void *xmemset(void *s, int c, unsigned int n) {
    u8 *p = (u8 *)s;
    while (n--) *p++ = (u8)c;
    return s;
}
#define memset xmemset

/* ========== 辅助函数 ========== */
static u8 gb_dac_enabled(SOUND *snd) {
    if (snd->channel != 3) return snd->reg[2] & 0xF8 ? 1 : 0;
    return snd->reg[0] & 0x80 ? 1 : 0;
}

/* square distance 预计算更新 (切频时调) */
static void gb_update_distance(SOUND *snd) {
    snd->distance = 0x800 - snd->frequency;
}

static void gb_tick_length(SOUND *snd) {
    if (snd->length_enabled) {
        snd->length = (snd->length + 1) & snd->length_mask;
        if (snd->length == 0) {
            snd->on = 0;
            snd->length_counting = 0;
        }
    }
}

static s32 gb_calculate_next_sweep(SOUND *snd) {
    s32 new_frequency;
    snd->sweep_neg_mode_used = (snd->sweep_direction < 0);
    new_frequency = (s32)snd->frequency + snd->sweep_direction *
                    ((s32)snd->frequency >> snd->sweep_shift);
    if (new_frequency > 0x7FF) snd->on = 0;
    return new_frequency;
}

static void gb_apply_next_sweep(SOUND *snd) {
    s32 new_frequency = gb_calculate_next_sweep(snd);
    if (snd->on && snd->sweep_shift > 0) {
        snd->frequency = (u16)new_frequency;
        snd->reg[3] = snd->frequency & 0xFF;
        gb_update_distance(snd);
    }
}

static void gb_tick_sweep(SOUND *snd) {
    snd->sweep_count = (snd->sweep_count - 1) & 0x07;
    if (snd->sweep_count == 0) {
        snd->sweep_count = snd->sweep_time;
        if (snd->sweep_enabled && snd->sweep_time > 0) {
            gb_apply_next_sweep(snd);
            gb_calculate_next_sweep(snd);
        }
    }
}

static void gb_tick_envelope(SOUND *snd) {
    if (snd->envelope_enabled) {
        s8 new_env;
        snd->envelope_count = (snd->envelope_count - 1) & 0x07;
        if (snd->envelope_count == 0) {
            snd->envelope_count = snd->envelope_time;
            if (snd->envelope_count) {
                new_env = (s8)(snd->envelope_value + snd->envelope_direction);
                if (new_env >= 0 && new_env <= 15) {
                    snd->envelope_value = new_env;
                } else {
                    snd->envelope_enabled = 0;
                }
            }
        }
    }
}

static u16 gb_noise_period_cycles(SOUND *snd) {
    return noise_div[snd->reg[3] & 7] << (snd->reg[3] >> 4);
}

/* ========== 通道更新 (ISR 热路径, 极致优化) ========== */

/* square: 公式法, 无循环. 严格对齐 libvgm gb_update_square_channel (line 957-986).
 * 关键: 用 frequency_counter 记录当前相位位置, 不跨越时累加它, 跨越时重载.
 * distance 第一次用 0x800-frequency_counter (当前到边界), 跨越后换 0x800-frequency.
 * 之前为省一字段删了 frequency_counter, 导致相位推进错误 (duty_count 几乎不动,
 * 12.5% duty 通道永远停在 -1 步, 音质极差). */
static void gb_update_square(SOUND *snd, u16 cycles) {
    u16 distance;
    u16 cyc;
    u16 counter;

    if (!snd->on) return;
    snd->cycles_left += (s16)cycles;
    if (snd->cycles_left <= 0) return;

    cyc = (u16)(snd->cycles_left >> 2);
    snd->cycles_left &= 3;
    distance = 0x800 - snd->frequency_counter;
    if (cyc >= distance) {
        cyc -= distance;
        distance = snd->distance;              /* 0x800 - frequency (预计算) */
        counter = 1 + cyc / distance;
        snd->duty_count = (snd->duty_count + counter) & 0x07;
        snd->signal = wave_duty_table[snd->duty][snd->duty_count];
        snd->frequency_counter = snd->frequency + (cyc % distance);
    } else {
        snd->frequency_counter += cyc;
    }
}

/* wave: NES 风格 phaseacc (用户确认保持). cycles_left 累加到 period 才推进 offset.
 * period = 2 × distance = 2 × (0x800 - frequency). 循环 ~5-10 次, 体轻. */
static void gb_update_wave(SOUND *snd, u16 cycles) {
    u8 b;
    u32 period;
    u16 guard;
    if (!snd->on) return;
    period = (u32)snd->distance * 2;     /* distance = 0x800 - frequency */
    if (period == 0) return;
    snd->cycles_left += (s16)cycles;
    guard = 0;
    while (snd->cycles_left >= (s16)period && guard < 32) {
        snd->cycles_left -= (s16)period;
        guard++;
        snd->offset = (snd->offset + 1) & 0x1F;
        b = gb_regs[AUD3W0 + (snd->offset >> 1)];
        if (!(snd->offset & 0x01)) b >>= 4;
        snd->signal = (s8)(((b & 0x0f) - 8));   /* current_sample 内联 */
        if (snd->level == 0) snd->signal = 0;
        else if (snd->level == 2) snd->signal = (s8)(snd->signal >> 1);
        else if (snd->level == 3) snd->signal = (s8)(snd->signal >> 2);
        /* level == 1: 原值不变 */
    }
    if (guard >= 32) snd->cycles_left = 0;
}

/* noise: AY 风格 Galois LFSR (用户确认可简化).
 * 单次 if 判断代替 while 循环: cycles_left 累加, 每达到 period 做一次移位.
 * 最多累积不处理 (guard=8), 听感接近 AY8910 噪声. */
static void gb_update_noise(SOUND *snd, u16 cycles) {
    u16 period;
    u16 guard;
    u16 rng;
    if (!snd->on) return;
    period = gb_noise_period_cycles(snd);
    if (period == 0) return;
    snd->cycles_left += (s16)cycles;
    rng = snd->noise_rng;
    guard = 0;
    while (snd->cycles_left >= (s16)period && guard < 8) {
        snd->cycles_left -= (s16)period;
        guard++;
        /* Galois LFSR (15-bit, 对应 DMG): tap at bit 14, polynomial 0x4000 */
        rng >>= 1;
        if (rng & 1) rng ^= 0x6000;   /* 简化多项式, 听感接近白噪声 */
        if (snd->noise_short) {
            /* 7-bit 模式: 复位高位, 周期变短 (音调变高) */
            rng = (rng & 0x007F) | ((rng & 1) << 6);
        }
    }
    snd->noise_rng = rng;
    snd->signal = (rng & 1) ? -1 : 1;
    if (guard >= 8) snd->cycles_left = 0;
}

/* frame sequencer 调度 + 通道 update.
 * 优化: 跨 frame 时不再双倍调用 update (原版先 cycles_current_frame 再剩余 cycles).
 * 改成: 通道用完整 cycles 一次 update, frame 边界的 tick 仍按 step 触发.
 * 除法全改位移 (FRAME_CYCLES=8192=2^13). */
static void gb_update_state(u16 cycles) {
    u32 old_cycles;
    u32 new_cycles;
    u8 frame_step;

    if (!gb_ctrl.on) return;

    old_cycles = gb_ctrl.cycles;
    new_cycles = old_cycles + cycles;
    gb_ctrl.cycles = new_cycles;

    /* 跨 frame 边界检测: old>>13 != new>>13 (用位移代替除法) */
    if ((old_cycles >> FRAME_SHIFT) != (new_cycles >> FRAME_SHIFT)) {
        frame_step = (u8)((new_cycles >> FRAME_SHIFT) & 0x07);
        switch (frame_step) {
        case 0:
            gb_tick_length(&gb_snd1);
            gb_tick_length(&gb_snd2);
            gb_tick_length(&gb_snd3);
            gb_tick_length(&gb_snd4);
            break;
        case 2:
            gb_tick_sweep(&gb_snd1);
            gb_tick_length(&gb_snd1);
            gb_tick_length(&gb_snd2);
            gb_tick_length(&gb_snd3);
            gb_tick_length(&gb_snd4);
            break;
        case 4:
            gb_tick_length(&gb_snd1);
            gb_tick_length(&gb_snd2);
            gb_tick_length(&gb_snd3);
            gb_tick_length(&gb_snd4);
            break;
        case 6:
            gb_tick_sweep(&gb_snd1);
            gb_tick_length(&gb_snd1);
            gb_tick_length(&gb_snd2);
            gb_tick_length(&gb_snd3);
            gb_tick_length(&gb_snd4);
            break;
        case 7:
            gb_tick_envelope(&gb_snd1);
            gb_tick_envelope(&gb_snd2);
            gb_tick_envelope(&gb_snd4);
            break;
        }
    }

    /* 通道相位推进: 用完整 cycles 一次 update (不拆分 cycles_current_frame) */
    gb_update_square(&gb_snd1, cycles);
    gb_update_square(&gb_snd2, cycles);
    gb_update_wave(&gb_snd3, cycles);
    gb_update_noise(&gb_snd4, cycles);
}

/* ========== 寄存器写 ========== */
static void gb_sound_w_internal(u8 offset, u8 val) {
    u8 old_data = gb_regs[offset];
    if (gb_ctrl.on) gb_regs[offset] = val;

    switch (offset) {
    /* === MODE 1 (方波1 + 扫频 + 包络) === */
    case NR10:
        gb_snd1.reg[0] = val;
        gb_snd1.sweep_shift = val & 0x7;
        gb_snd1.sweep_direction = (val & 0x8) ? -1 : 1;
        gb_snd1.sweep_time = (val & 0x70) >> 4;
        if ((old_data & 0x08) && !(val & 0x08) && gb_snd1.sweep_neg_mode_used)
            gb_snd1.on = 0;
        break;
    case NR11:
        gb_snd1.reg[1] = val;
        if (gb_ctrl.on) gb_snd1.duty = (val & 0xc0) >> 6;
        gb_snd1.length = val & 0x3f;
        gb_snd1.length_counting = 1;
        break;
    case NR12:
        gb_snd1.reg[2] = val;
        gb_snd1.envelope_value = (s8)(val >> 4);
        gb_snd1.envelope_direction = (val & 0x8) ? 1 : -1;
        gb_snd1.envelope_time = val & 0x07;
        if (!gb_dac_enabled(&gb_snd1)) gb_snd1.on = 0;
        break;
    case NR13:
        gb_snd1.reg[3] = val;
        if (!gb_snd1.sweep_enabled) {
            gb_snd1.frequency = ((u16)(gb_snd1.reg[4] & 0x7) << 8) | gb_snd1.reg[3];
            gb_update_distance(&gb_snd1);
        }
        break;
    case NR14: {
        u8 length_was_enabled = gb_snd1.length_enabled;
        gb_snd1.reg[4] = val;
        gb_snd1.length_enabled = (val & 0x40) ? 1 : 0;
        gb_snd1.frequency = ((u16)(gb_regs[NR14] & 0x7) << 8) | gb_snd1.reg[3];
        gb_update_distance(&gb_snd1);

        if (!length_was_enabled && !(gb_ctrl.cycles & FRAME_MASK) && gb_snd1.length_counting) {
            if (gb_snd1.length_enabled) gb_tick_length(&gb_snd1);
        }

        if (val & 0x80) {
            gb_snd1.on = 1;
            gb_snd1.envelope_enabled = 1;
            gb_snd1.envelope_value = (s8)(gb_snd1.reg[2] >> 4);
            gb_snd1.envelope_count = gb_snd1.envelope_time;
            gb_snd1.sweep_count = gb_snd1.sweep_time;
            gb_snd1.sweep_neg_mode_used = 0;
            gb_snd1.signal = 0;
            gb_snd1.length_counting = 1;
            gb_snd1.frequency = ((u16)(gb_snd1.reg[4] & 0x7) << 8) | gb_snd1.reg[3];
            gb_update_distance(&gb_snd1);
            gb_snd1.cycles_left = 0;
            gb_snd1.duty_count = 0;
            gb_snd1.frequency_counter = gb_snd1.frequency;   /* libvgm: trigger 重置相位 */
            gb_snd1.sweep_enabled = (gb_snd1.sweep_shift != 0) || (gb_snd1.sweep_time != 0);
            if (!gb_dac_enabled(&gb_snd1)) gb_snd1.on = 0;
            if (gb_snd1.sweep_shift > 0) gb_calculate_next_sweep(&gb_snd1);
            if (gb_snd1.length == 0 && gb_snd1.length_enabled && !(gb_ctrl.cycles & FRAME_MASK))
                gb_tick_length(&gb_snd1);
        } else {
            if (!gb_snd1.sweep_enabled) {
                gb_snd1.frequency = ((u16)(gb_snd1.reg[4] & 0x7) << 8) | gb_snd1.reg[3];
                gb_update_distance(&gb_snd1);
            }
        }
        break;
    }

    /* === MODE 2 (方波2 + 包络) === */
    case NR21:
        gb_snd2.reg[1] = val;
        if (gb_ctrl.on) gb_snd2.duty = (val & 0xc0) >> 6;
        gb_snd2.length = val & 0x3f;
        gb_snd2.length_counting = 1;
        break;
    case NR22:
        gb_snd2.reg[2] = val;
        gb_snd2.envelope_value = (s8)(val >> 4);
        gb_snd2.envelope_direction = (val & 0x8) ? 1 : -1;
        gb_snd2.envelope_time = val & 0x07;
        if (!gb_dac_enabled(&gb_snd2)) gb_snd2.on = 0;
        break;
    case NR23:
        gb_snd2.reg[3] = val;
        gb_snd2.frequency = ((u16)(gb_snd2.reg[4] & 0x7) << 8) | gb_snd2.reg[3];
        gb_update_distance(&gb_snd2);
        break;
    case NR24: {
        u8 length_was_enabled = gb_snd2.length_enabled;
        gb_snd2.reg[4] = val;
        gb_snd2.length_enabled = (val & 0x40) ? 1 : 0;
        gb_snd2.frequency = ((u16)(gb_snd2.reg[4] & 0x7) << 8) | gb_snd2.reg[3];
        gb_update_distance(&gb_snd2);
        if (!length_was_enabled && !(gb_ctrl.cycles & FRAME_MASK) && gb_snd2.length_counting) {
            if (gb_snd2.length_enabled) gb_tick_length(&gb_snd2);
        }
        if (val & 0x80) {
            gb_snd2.on = 1;
            gb_snd2.envelope_enabled = 1;
            gb_snd2.envelope_value = (s8)(gb_snd2.reg[2] >> 4);
            gb_snd2.envelope_count = gb_snd2.envelope_time;
            gb_snd2.frequency = ((u16)(gb_snd2.reg[4] & 0x7) << 8) | gb_snd2.reg[3];
            gb_update_distance(&gb_snd2);
            gb_snd2.cycles_left = 0;
            gb_snd2.duty_count = 0;
            gb_snd2.frequency_counter = gb_snd2.frequency;   /* libvgm: trigger 重置相位 */
            gb_snd2.signal = 0;
            gb_snd2.length_counting = 1;
            if (!gb_dac_enabled(&gb_snd2)) gb_snd2.on = 0;
            if (gb_snd2.length == 0 && gb_snd2.length_enabled && !(gb_ctrl.cycles & FRAME_MASK))
                gb_tick_length(&gb_snd2);
        } else {
            gb_snd2.frequency = ((u16)(gb_snd2.reg[4] & 0x7) << 8) | gb_snd2.reg[3];
            gb_update_distance(&gb_snd2);
        }
        break;
    }

    /* === MODE 3 (自定义波形) === */
    case NR30:
        gb_snd3.reg[0] = val;
        if (!gb_dac_enabled(&gb_snd3)) gb_snd3.on = 0;
        break;
    case NR31:
        gb_snd3.reg[1] = val;
        gb_snd3.length = val;
        gb_snd3.length_counting = 1;
        break;
    case NR32:
        gb_snd3.reg[2] = val;
        gb_snd3.level = (val & 0x60) >> 5;
        break;
    case NR33:
        gb_snd3.reg[3] = val;
        gb_snd3.frequency = ((u16)(gb_snd3.reg[4] & 0x7) << 8) | gb_snd3.reg[3];
        gb_update_distance(&gb_snd3);
        break;
    case NR34: {
        u8 length_was_enabled = gb_snd3.length_enabled;
        gb_snd3.reg[4] = val;
        gb_snd3.length_enabled = (val & 0x40) ? 1 : 0;
        gb_snd3.frequency = ((u16)(gb_snd3.reg[4] & 0x7) << 8) | gb_snd3.reg[3];
        gb_update_distance(&gb_snd3);
        if (!length_was_enabled && !(gb_ctrl.cycles & FRAME_MASK) && gb_snd3.length_counting) {
            if (gb_snd3.length_enabled) gb_tick_length(&gb_snd3);
        }
        if (val & 0x80) {
            gb_snd3.on = 1;
            gb_snd3.offset = 0;
            gb_snd3.duty_count = 0;
            gb_snd3.length_counting = 1;
            gb_snd3.frequency = ((u16)(gb_snd3.reg[4] & 0x7) << 8) | gb_snd3.reg[3];
            gb_update_distance(&gb_snd3);
            gb_snd3.cycles_left = -6;   /* 启动延迟 (DMG 硬件行为) */
            gb_snd3.signal = 0;
            if (!gb_dac_enabled(&gb_snd3)) gb_snd3.on = 0;
            if (gb_snd3.length == 0 && gb_snd3.length_enabled && !(gb_ctrl.cycles & FRAME_MASK))
                gb_tick_length(&gb_snd3);
        } else {
            gb_snd3.frequency = ((u16)(gb_snd3.reg[4] & 0x7) << 8) | gb_snd3.reg[3];
            gb_update_distance(&gb_snd3);
        }
        break;
    }

    /* === MODE 4 (噪声 + 包络, AY 风格简化 LFSR) === */
    case NR41:
        gb_snd4.reg[1] = val;
        gb_snd4.length = val & 0x3f;
        gb_snd4.length_counting = 1;
        break;
    case NR42:
        gb_snd4.reg[2] = val;
        gb_snd4.envelope_value = (s8)(val >> 4);
        gb_snd4.envelope_direction = (val & 0x8) ? 1 : -1;
        gb_snd4.envelope_time = val & 0x07;
        if (!gb_dac_enabled(&gb_snd4)) gb_snd4.on = 0;
        break;
    case NR43:
        gb_snd4.reg[3] = val;
        gb_snd4.noise_short = (val & 0x8) ? 1 : 0;
        break;
    case NR44: {
        u8 length_was_enabled = gb_snd4.length_enabled;
        gb_snd4.reg[4] = val;
        gb_snd4.length_enabled = (val & 0x40) ? 1 : 0;
        if (!length_was_enabled && !(gb_ctrl.cycles & FRAME_MASK) && gb_snd4.length_counting) {
            if (gb_snd4.length_enabled) gb_tick_length(&gb_snd4);
        }
        if (val & 0x80) {
            gb_snd4.on = 1;
            gb_snd4.envelope_enabled = 1;
            gb_snd4.envelope_value = (s8)(gb_snd4.reg[2] >> 4);
            gb_snd4.envelope_count = gb_snd4.envelope_time;
            gb_snd4.cycles_left = 0;
            gb_snd4.signal = -1;
            gb_snd4.noise_rng = 0x7FFF;     /* DMG LFSR 初始值 */
            gb_snd4.length_counting = 1;
            if (!gb_dac_enabled(&gb_snd4)) gb_snd4.on = 0;
            if (gb_snd4.length == 0 && gb_snd4.length_enabled && !(gb_ctrl.cycles & FRAME_MASK))
                gb_tick_length(&gb_snd4);
        }
        break;
    }

    /* === CONTROL === */
    case NR50:
        gb_ctrl.vol_left = val & 0x7;
        gb_ctrl.vol_right = (val & 0x70) >> 4;
        break;
    case NR51:
        gb_ctrl.mode1_right = val & 0x1;
        gb_ctrl.mode1_left = (val & 0x10) >> 4;
        gb_ctrl.mode2_right = (val & 0x2) >> 1;
        gb_ctrl.mode2_left = (val & 0x20) >> 5;
        gb_ctrl.mode3_right = (val & 0x4) >> 2;
        gb_ctrl.mode3_left = (val & 0x40) >> 6;
        gb_ctrl.mode4_right = (val & 0x8) >> 3;
        gb_ctrl.mode4_left = (val & 0x80) >> 7;
        break;
    case NR52:
        if (!(val & 0x80)) {
            /* Power off: 只关 on 标志, 不 memset (避免和 ISR 竞争) */
            gb_snd1.on = 0;
            gb_snd2.on = 0;
            gb_snd3.on = 0;
            gb_snd4.on = 0;
        } else {
            if (!gb_ctrl.on) gb_ctrl.cycles |= (u32)(7 * FRAME_CYCLES);
        }
        gb_ctrl.on = (val & 0x80) ? 1 : 0;
        gb_regs[NR52] = val & 0x80;
        break;
    }
}

void gb_wr(u8 reg, u8 val) {
    /* AUD3W0 - AUD3WF: 波形 RAM */
    if (reg >= AUD3W0 && reg <= AUD3W0 + 0x0F) {
        gb_regs[reg] = val;
        return;
    }
    /* DMG 模式: 关闭时仅 NR52/NR11/NR21/NR31/NR41 可写 */
    if (!gb_ctrl.on && reg != NR52 && reg != NR11 && reg != NR21 && reg != NR31 && reg != NR41)
        return;
    gb_sound_w_internal(reg, val);
}

void gb_init(void) {
    memset(gb_regs, 0, sizeof(gb_regs));
    memset(&gb_snd1, 0, sizeof(SOUND));
    memset(&gb_snd2, 0, sizeof(SOUND));
    memset(&gb_snd3, 0, sizeof(SOUND));
    memset(&gb_snd4, 0, sizeof(SOUND));
    memset(&gb_ctrl, 0, sizeof(SOUNDC));

    gb_snd1.channel = 1; gb_snd1.length_mask = 0x3F;
    gb_snd2.channel = 2; gb_snd2.length_mask = 0x3F;
    gb_snd3.channel = 3; gb_snd3.length_mask = 0xFF;
    gb_snd4.channel = 4; gb_snd4.length_mask = 0x3F;

    /* DMG 默认波形 RAM (上电时由 BIOS 写入的标准值) */
    gb_regs[AUD3W0 + 0]  = 0xac;
    gb_regs[AUD3W0 + 1]  = 0xdd;
    gb_regs[AUD3W0 + 2]  = 0xda;
    gb_regs[AUD3W0 + 3]  = 0x48;
    gb_regs[AUD3W0 + 4]  = 0x36;
    gb_regs[AUD3W0 + 5]  = 0x02;
    gb_regs[AUD3W0 + 6]  = 0xcf;
    gb_regs[AUD3W0 + 7]  = 0x16;
    gb_regs[AUD3W0 + 8]  = 0x2c;
    gb_regs[AUD3W0 + 9]  = 0x04;
    gb_regs[AUD3W0 + 10] = 0xe5;
    gb_regs[AUD3W0 + 11] = 0x2c;
    gb_regs[AUD3W0 + 12] = 0xac;
    gb_regs[AUD3W0 + 13] = 0xdd;
    gb_regs[AUD3W0 + 14] = 0xda;
    gb_regs[AUD3W0 + 15] = 0x48;

    gb_ctrl.on = 1;
    gb_base_count = 0;
    gb_hp_y = 0;               /* RC 高通滤波器状态 */
    gb_hp_x = 0;
}

/* ========== 渲染 (一个采样, ISR 热路径) ========== */
s16 gb_render(void) {
    s32 left, right;
    s32 sample;
    s32 mono;
    s32 vol_avg;
    u32 incr;

    gb_base_count += GB_BASE_INCR;
    incr = gb_base_count >> GB_GETA_BITS;
    gb_base_count &= (1UL << GB_GETA_BITS) - 1;

    if (incr > 0) gb_update_state((u16)incr);

    /* Mono 合并: 取 max(|left|, |right|), NR51 只控制"有没有声"不控制"多大声" */
    left = 0;
    right = 0;

    if (gb_snd1.on) {
        sample = (s32)gb_snd1.signal * gb_snd1.envelope_value;
        if (gb_ctrl.mode1_left)  left  += sample;
        if (gb_ctrl.mode1_right) right += sample;
    }
    if (gb_snd2.on) {
        sample = (s32)gb_snd2.signal * gb_snd2.envelope_value;
        if (gb_ctrl.mode2_left)  left  += sample;
        if (gb_ctrl.mode2_right) right += sample;
    }
    if (gb_snd3.on) {
        sample = gb_snd3.signal;
        if (gb_ctrl.mode3_left)  left  += sample;
        if (gb_ctrl.mode3_right) right += sample;
    }
    if (gb_snd4.on) {
        sample = (s32)gb_snd4.signal * gb_snd4.envelope_value;
        if (gb_ctrl.mode4_left)  left  += sample;
        if (gb_ctrl.mode4_right) right += sample;
    }

    /* max(|left|, |right|) 保留符号, 不用 abs (避免库函数调用) */
    if (left < 0) { if (-left >= right) mono = left; else mono = right; }
    else          { if ( left >= right) mono = left; else mono = right; }

    /* 主音量 + 衰减 (对齐 NES 量级, ISR 外层 mix*=8 统一放大).
     * >>3 (除 8) 而非 >>2: Pokemon 等高密度曲目 4 通道全开时幅度接近上限,
     * >>2 会偶发破音, 减半到 >>3 留 6dB 余量. */
    vol_avg = ((s32)gb_ctrl.vol_left + gb_ctrl.vol_right + 1) >> 1;
    mono *= vol_avg;
    mono >>= 3;

    /* RC 高通滤波器 (模拟 DMG 硬件隔直电容, 对齐 gbsplay 思路):
     * 标准一阶 RC 高通: y[n] = α × (y[n-1] + x[n] - x[n-1])
     * 消除 duty 不对称直流 (12.5% duty 的 -0.75×env) + 衰减 <15Hz 次声波.
     * α=0.99570436 (fc=15.14Hz @ 22050Hz).
     * 信号放大到 Q16 再滤波 (否则小信号整数截断导致衰减失效). */
    {
        s32 in_q16 = mono << 16;
        s32 y_q16 = (GB_HP_ALPHA * (gb_hp_y + in_q16 - gb_hp_x)) >> 16;
        gb_hp_x = in_q16;
        gb_hp_y = y_q16;
        mono = y_q16 >> 16;     /* 还原到原始幅度 */
    }

    if (mono > 2047)  mono = 2047;
    if (mono < -2048) mono = -2048;
    return (s16)mono;
}
