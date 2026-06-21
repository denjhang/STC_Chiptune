/* gb.c - GameBoy DMG APU 仿真核心 (STC32G C251 版)
 * 对齐 libvgm emu/cores/gb.c (Wilbert Pol, Anthony Kruize, BSD-3-Clause)
 *
 * 4 通道:
 *   1. 方波 + 扫频 + 包络 (NR10-14)
 *   2. 方波 + 包络       (NR21-24)
 *   3. 自定义波形 (Wave RAM, NR30-34)
 *   4. 噪声 + 包络       (NR41-44)
 *
 * GB 频率公式: Hz = 131072 / (2048 - gb_freq),  gb = 2048 - 131072/Hz
 * Frame sequencer: clock/8192 = 512 Hz, 8 steps (length/sweep/envelope)
 *
 * 移植要点 (C251 C89 严格模式):
 * - 所有局部变量声明必须在 block 开头, 不能 mixed declarations
 * - 用 24-bit 累加器把 GB-clock cycles 归一化到采样率 (cycles_per_sample 非整数)
 * - 单声道 mono (libvgm 立体声 left/right 均值化)
 */
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

/* 方波 duty 表 (12.5%/25%/50%/75%) */
static const s8 wave_duty_table[4][8] = {
    { -1, -1, -1, -1, -1, -1, -1,  1 },
    {  1, -1, -1, -1, -1, -1, -1,  1 },
    {  1, -1, -1, -1, -1,  1,  1,  1 },
    { -1,  1,  1,  1,  1,  1,  1, -1 }
};

/* ========== 通道状态结构 ========== */
typedef struct {
    u8  reg[5];
    u8  on;
    u8  channel;
    u8  length;
    u8  length_mask;
    u8  length_counting;
    u8  length_enabled;
    s32 cycles_left;
    s8  duty;
    u8  envelope_enabled;
    s8  envelope_value;
    s8  envelope_direction;
    u8  envelope_time;
    u8  envelope_count;
    s8  signal;
    u16 frequency;
    u16 frequency_counter;
    u8  sweep_enabled;
    u8  sweep_neg_mode_used;
    u8  sweep_shift;
    s8  sweep_direction;
    u8  sweep_time;
    u8  sweep_count;
    u8  level;
    u8  offset;
    u32 duty_count;
    s8  current_sample;
    u8  sample_reading;
    u8  noise_short;
    u16 noise_lfsr;
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

static SOUND  gb_snd1, gb_snd2, gb_snd3, gb_snd4;
static SOUNDC gb_ctrl;
static u8     gb_regs[0x30];
static u32    gb_base_count;

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

static u32 gb_noise_period_cycles(void) {
    static const u32 divisor[8] = { 8, 16, 32, 48, 64, 80, 96, 112 };
    return divisor[gb_snd4.reg[3] & 7] << (gb_snd4.reg[3] >> 4);
}

/* ========== 通道更新 ========== */
static void gb_update_square(SOUND *snd, u32 cycles) {
    u16 distance;
    u32 counter;

    if (!snd->on) return;
    snd->cycles_left += (s32)cycles;
    if (snd->cycles_left <= 0) return;

    cycles = (u32)(snd->cycles_left >> 2);
    snd->cycles_left &= 3;
    distance = 0x800 - snd->frequency_counter;
    if (cycles >= distance) {
        cycles -= distance;
        distance = 0x800 - snd->frequency;
        counter = 1 + cycles / distance;
        snd->duty_count = (snd->duty_count + counter) & 0x07;
        snd->signal = wave_duty_table[snd->duty][snd->duty_count];
        snd->frequency_counter = snd->frequency + (u16)(cycles % distance);
    } else {
        snd->frequency_counter += (u16)cycles;
    }
}

static void gb_update_wave(SOUND *snd, u32 cycles) {
    /* NES 风格 phaseacc 累加 (对齐 nes_update_square):
     * cycles_left 当 phaseacc, 累加 cycles, 达到 period (4*(2048-frequency)) 就
     * 推进 offset 并读 sample. 循环次数 = cycles / period ≈ 5-10 次 (而非 95 次).
     * GB wave 原始: freq_counter 每 2 cycles +1, 走 (0x800-frequency) 步回绕,
     *   period_cycles = 2 * (0x800 - frequency) = 0x1000 - 2*frequency.
     * 但 DMG wave 的 period 实际是 2*(2048-frequency) GB cycles (每个 sample point 32 个).
     * 这里用 cycles_left 累加 GB cycles, 达到 period 就 offset+1 + 读 sample. */
    u8 b;
    u32 period;
    u16 guard;
    if (!snd->on) return;
    /* wave 通道: freq_counter 从 frequency 走到 0x7ff 再回 0, 一共 (0x800-frequency) 步,
     * 每步 2 GB cycles, 所以一个完整波形周期 = 2*(0x800-frequency) GB cycles.
     * 但 libvgm 原版 freq_counter 走法: 从 frequency 递增, 到 0x7ff 时 offset+1,
     * 到 0 时读 sample + 重载 frequency. 实际 sample point 间隔 = 2*(0x800-frequency).
     * 32 个 sample point = 完整波形. */
    if (snd->frequency >= 0x800) return;  /* 防御 */
    period = (u32)(0x800 - snd->frequency) * 2;  /* 一个 sample point 的 GB cycles */
    if (period == 0) return;
    snd->cycles_left += (s32)cycles;
    guard = 0;
    while (snd->cycles_left >= (s32)period && guard < 32) {
        snd->cycles_left -= (s32)period;
        guard++;
        snd->offset = (snd->offset + 1) & 0x1F;
        b = gb_regs[AUD3W0 + (snd->offset >> 1)];
        if (!(snd->offset & 0x01)) b >>= 4;
        snd->current_sample = (s8)((b & 0x0f) - 8);
        if (snd->level == 0) snd->signal = 0;
        else if (snd->level == 1) snd->signal = snd->current_sample;
        else if (snd->level == 2) snd->signal = (s8)(snd->current_sample >> 1);
        else snd->signal = (s8)(snd->current_sample >> 2);
    }
    if (guard >= 32) snd->cycles_left = 0;
}

static void gb_update_noise(SOUND *snd, u32 cycles) {
    /* noise 的 period 已是 GB cycles (8~32768), cycles_left 累加到 period 就移位.
     * period 最小 8, cycles 190, 循环最多 24 次, 可接受. guard 32 保底. */
    u32 period = gb_noise_period_cycles();
    u16 feedback;
    u16 guard;
    if (period == 0) return;
    snd->cycles_left += (s32)cycles;
    guard = 0;
    while (snd->cycles_left >= (s32)period && guard < 32) {
        snd->cycles_left -= (s32)period;
        guard++;
        feedback = ((snd->noise_lfsr >> 1) ^ snd->noise_lfsr) & 1;
        snd->noise_lfsr = (snd->noise_lfsr >> 1) | (feedback << 14);
        if (snd->noise_short) {
            snd->noise_lfsr = (snd->noise_lfsr & ~(1 << 6)) | (feedback << 6);
        }
        snd->signal = (snd->noise_lfsr & 1) ? -1 : 1;
    }
    if (guard >= 32) snd->cycles_left = 0;
}

static void gb_update_state(u32 cycles) {
    u32 old_cycles;
    u32 cycles_current_frame;
    u8 frame_step;

    if (!gb_ctrl.on) return;

    old_cycles = gb_ctrl.cycles;
    gb_ctrl.cycles += cycles;

    if ((old_cycles / FRAME_CYCLES) != (gb_ctrl.cycles / FRAME_CYCLES)) {
        cycles_current_frame = FRAME_CYCLES - (old_cycles & (FRAME_CYCLES - 1));
        gb_update_square(&gb_snd1, cycles_current_frame);
        gb_update_square(&gb_snd2, cycles_current_frame);
        gb_update_wave(&gb_snd3, cycles_current_frame);
        gb_update_noise(&gb_snd4, cycles_current_frame);
        cycles -= cycles_current_frame;

        frame_step = (u8)((gb_ctrl.cycles / FRAME_CYCLES) & 0x07);
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
        if (!gb_snd1.sweep_enabled)
            gb_snd1.frequency = ((u16)(gb_snd1.reg[4] & 0x7) << 8) | gb_snd1.reg[3];
        break;
    case NR14: {
        u8 length_was_enabled = gb_snd1.length_enabled;
        gb_snd1.reg[4] = val;
        gb_snd1.length_enabled = (val & 0x40) ? 1 : 0;
        gb_snd1.frequency = ((u16)(gb_regs[NR14] & 0x7) << 8) | gb_snd1.reg[3];

        if (!length_was_enabled && !(gb_ctrl.cycles & FRAME_CYCLES) && gb_snd1.length_counting) {
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
            gb_snd1.frequency_counter = gb_snd1.frequency;
            gb_snd1.cycles_left = 0;
            gb_snd1.duty_count = 0;
            gb_snd1.sweep_enabled = (gb_snd1.sweep_shift != 0) || (gb_snd1.sweep_time != 0);
            if (!gb_dac_enabled(&gb_snd1)) gb_snd1.on = 0;
            if (gb_snd1.sweep_shift > 0) gb_calculate_next_sweep(&gb_snd1);
            if (gb_snd1.length == 0 && gb_snd1.length_enabled && !(gb_ctrl.cycles & FRAME_CYCLES))
                gb_tick_length(&gb_snd1);
        } else {
            if (!gb_snd1.sweep_enabled)
                gb_snd1.frequency = ((u16)(gb_snd1.reg[4] & 0x7) << 8) | gb_snd1.reg[3];
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
        break;
    case NR24: {
        u8 length_was_enabled = gb_snd2.length_enabled;
        gb_snd2.reg[4] = val;
        gb_snd2.length_enabled = (val & 0x40) ? 1 : 0;
        if (!length_was_enabled && !(gb_ctrl.cycles & FRAME_CYCLES) && gb_snd2.length_counting) {
            if (gb_snd2.length_enabled) gb_tick_length(&gb_snd2);
        }
        if (val & 0x80) {
            gb_snd2.on = 1;
            gb_snd2.envelope_enabled = 1;
            gb_snd2.envelope_value = (s8)(gb_snd2.reg[2] >> 4);
            gb_snd2.envelope_count = gb_snd2.envelope_time;
            gb_snd2.frequency = ((u16)(gb_snd2.reg[4] & 0x7) << 8) | gb_snd2.reg[3];
            gb_snd2.frequency_counter = gb_snd2.frequency;
            gb_snd2.cycles_left = 0;
            gb_snd2.duty_count = 0;
            gb_snd2.signal = 0;
            gb_snd2.length_counting = 1;
            if (!gb_dac_enabled(&gb_snd2)) gb_snd2.on = 0;
            if (gb_snd2.length == 0 && gb_snd2.length_enabled && !(gb_ctrl.cycles & FRAME_CYCLES))
                gb_tick_length(&gb_snd2);
        } else {
            gb_snd2.frequency = ((u16)(gb_snd2.reg[4] & 0x7) << 8) | gb_snd2.reg[3];
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
        break;
    case NR34: {
        u8 length_was_enabled = gb_snd3.length_enabled;
        gb_snd3.reg[4] = val;
        gb_snd3.length_enabled = (val & 0x40) ? 1 : 0;
        if (!length_was_enabled && !(gb_ctrl.cycles & FRAME_CYCLES) && gb_snd3.length_counting) {
            if (gb_snd3.length_enabled) gb_tick_length(&gb_snd3);
        }
        if (val & 0x80) {
            gb_snd3.on = 1;
            gb_snd3.offset = 0;
            gb_snd3.duty = 1;
            gb_snd3.duty_count = 0;
            gb_snd3.length_counting = 1;
            gb_snd3.frequency = ((u16)(gb_snd3.reg[4] & 0x7) << 8) | gb_snd3.reg[3];
            gb_snd3.frequency_counter = gb_snd3.frequency;
            /* 启动时有一点延迟 */
            gb_snd3.cycles_left = -6;
            gb_snd3.sample_reading = 0;
            if (!gb_dac_enabled(&gb_snd3)) gb_snd3.on = 0;
            if (gb_snd3.length == 0 && gb_snd3.length_enabled && !(gb_ctrl.cycles & FRAME_CYCLES))
                gb_tick_length(&gb_snd3);
        } else {
            gb_snd3.frequency = ((u16)(gb_snd3.reg[4] & 0x7) << 8) | gb_snd3.reg[3];
        }
        break;
    }

    /* === MODE 4 (噪声 + 包络) === */
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
        if (!length_was_enabled && !(gb_ctrl.cycles & FRAME_CYCLES) && gb_snd4.length_counting) {
            if (gb_snd4.length_enabled) gb_tick_length(&gb_snd4);
        }
        if (val & 0x80) {
            gb_snd4.on = 1;
            gb_snd4.envelope_enabled = 1;
            gb_snd4.envelope_value = (s8)(gb_snd4.reg[2] >> 4);
            gb_snd4.envelope_count = gb_snd4.envelope_time;
            gb_snd4.frequency_counter = 0;
            gb_snd4.cycles_left = (s32)gb_noise_period_cycles();
            gb_snd4.signal = -1;
            gb_snd4.noise_lfsr = 0x7fff;
            gb_snd4.length_counting = 1;
            if (!gb_dac_enabled(&gb_snd4)) gb_snd4.on = 0;
            if (gb_snd4.length == 0 && gb_snd4.length_enabled && !(gb_ctrl.cycles & FRAME_CYCLES))
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
            /* Power off: 只关 on 标志, 不 memset 整个结构 (避免和 ISR 竞争)
             * 真正的复位在 gb_init() 0xF0 命令做 */
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
}

/* ========== 渲染 (一个采样) ========== */
/* Mono 合并策略 (对齐 libvgm emu/cores/gb.c gameboy_sound_update):
 *   libvgm 是立体声, 左/右各独立: sample *= vol_xxx; sample <<= 6;
 *   我们合成单声道, 用 (left + right) / 2 平均, 再乘平均主音量, 再 <<6.
 *   这样单使能 (只 left 或只 right) 时与 libvgm 单边完全一致;
 *   双使能时取均值, 避免幅度 2x 失真. */
s16 gb_render(void) {
    s32 left, right;
    s32 sample;
    s32 mono;
    s32 vol_avg;
    u32 incr;

    gb_base_count += GB_BASE_INCR;
    incr = gb_base_count >> GB_GETA_BITS;
    gb_base_count &= (1UL << GB_GETA_BITS) - 1;

    if (incr > 0) gb_update_state(incr);

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

    /* Mono 合并策略 (单声道系统, 不做立体声):
     * 真实 GB 左右扬声器物理分开, NR51 控制每个通道的声像 (left/right/both).
     * 我们只有一个 DAC, 合并成 mono.
     *
     * 取 |left| 和 |right| 中较大者 (保留符号), 不求和也不平均:
     *   - 单边使能 (只 left 或只 right): 全音量, 不被砍半
     *   - 双边使能: 也是全音量 (不 +6dB), 和单边音量一致
     *   - NR51 只影响"有没有声", 不影响"多大声"
     * 这样无论作曲家怎么编排声像, 听感音量都稳定.
     *
     * 量级: GB 最坏 ≈ ±67 (vol=7), >>2 (除 4) 后 ≈ ±16,
     * ISR 外层 mix *= 8 后 ≈ ±128, 在 DAC ±2048 内有充足余量.
     *
     * 若未来加第二个 DAC 做真立体声: 把 left/right 分别输出到 DAC1/DAC2,
     * 各自走 vol_left/vol_right 主音量, ISR 计算量翻倍 (需重新评估是否超时). */
    if (left < 0) { if (-left >= right) mono = left; else mono = right; }
    else          { if ( left >= right) mono = left; else mono = right; }
    vol_avg = ((s32)gb_ctrl.vol_left + gb_ctrl.vol_right + 1) / 2;
    mono *= vol_avg;
    mono >>= 2;

    if (mono > 2047)  mono = 2047;
    if (mono < -2048) mono = -2048;
    return (s16)mono;
}
