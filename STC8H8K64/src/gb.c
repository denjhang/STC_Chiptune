/* gb.c - Game Boy DMG 仿真核心 (精简嵌入式版)
 * 4 通道: 2x 方波(包络+扫频), 1x 波形(WaveRAM), 1x 噪声(包络)
 * DMG 模式, 仅写入寄存器, 无读取
 * 参考 libvgm gb.c (Wilbert Pol / Anthony Kruize)
 */
#include <stc8h.h>
#include <string.h>
#include "gb.h"

/* ========== 寄存器地址 ========== */
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

/* ========== 方波 duty 表 (code 段) ========== */
static s8 code gb_duty[4][8] = {
    { -1, -1, -1, -1, -1, -1, -1,  1},
    {  1, -1, -1, -1, -1, -1, -1,  1},
    {  1, -1, -1, -1, -1,  1,  1,  1},
    { -1,  1,  1,  1,  1,  1,  1, -1}
};

/* ========== 噪声分频表 ========== */
static u16 code gb_noise_div[8] = { 8, 16, 32, 48, 64, 80, 96, 112 };

/* ========== 通道状态 (xdata) ========== */
typedef struct {
    u8  on;             /* 通道启用 */
    u8  reg[5];         /* 最近写入的寄存器值 */
    u8  length;         /* 长度计数器 */
    u8  length_mask;    /* 长度掩码: ch1/2/4=0x3F, ch3=0xFF */
    u8  length_counting;
    u8  length_enabled;
    /* 方波/噪声共用 */
    s8  signal;         /* 当前信号 (-1 or 1) */
    s8  envelope_value;
    s8  envelope_dir;   /* +1 or -1 */
    u8  envelope_time;
    u8  envelope_count;
    u8  envelope_enabled;
    /* 方波 (ch1/ch2/ch3) */
    u16 frequency;      /* 11-bit 频率 */
    u16 freq_counter;   /* 频率计数器 */
    s16 cycles_left;    /* 剩余 cycle */
    u8  duty;           /* duty 序号 */
    u8  duty_count;     /* duty 位置 */
    /* ch1 扫频 */
    u8  sweep_shift;
    s8  sweep_dir;      /* +1 or -1 */
    u8  sweep_time;
    u8  sweep_count;
    u8  sweep_enabled;
    u8  sweep_neg_used;
    /* ch3 波形 */
    u8  level;          /* 输出级别 (0-3) */
    u8  offset;         /* WaveRAM 偏移 */
    u8  sample_reading;
    s8  current_sample;
    /* ch4 噪声 */
    u8  noise_short;    /* 0=15bit, 1=7bit */
    u16 noise_lfsr;
} GB_SND;

/* ========== 全局状态 ========== */
static GB_SND xdata gb_ch[4];         /* 4 通道 */
static u8 xdata gb_regs[0x30];        /* 寄存器镜像 */
static u8 xdata gb_ctrl_on;           /* NR52 bit7: 全局开关 */
static u8 xdata gb_vol_l, gb_vol_r;   /* NR50: 主音量 */
static u8 xdata gb_ch_l[4], gb_ch_r[4]; /* NR51: 通道左右分配 */
static u32 xdata gb_frame_cycles;     /* frame sequencer cycle 累积 */
static u32 xdata gb_base_count;       /* 采样率转换累加器 */
static u8 xdata gb_frame_step;        /* frame sequencer 步骤 (0-7) */

/* ========== 内部函数声明 ========== */
static void gb_tick_length(GB_SND *snd);
static void gb_tick_sweep(GB_SND *snd);
static void gb_tick_envelope(GB_SND *snd);
static u16  gb_noise_period(void);
static void gb_update_square(GB_SND *snd, u16 cycles);
static void gb_update_wave(GB_SND *snd, u16 cycles);
static void gb_update_noise(GB_SND *snd, u16 cycles);

/* ========== 初始化 ========== */
void gb_init(void) {
    u8 i, j;
    memset(gb_regs, 0, sizeof(gb_regs));
    gb_ctrl_on = 0;
    gb_vol_l = 7; gb_vol_r = 7;
    gb_frame_cycles = 0;
    gb_base_count = 0;
    gb_frame_step = 0;

    for (i = 0; i < 4; i++) {
        GB_SND xdata *s = &gb_ch[i];
        s->on = 0;
        for (j = 0; j < 5; j++) s->reg[j] = 0;
        s->length = 0;
        s->length_counting = 0;
        s->length_enabled = 0;
        s->signal = 0;
        s->envelope_value = 0;
        s->envelope_dir = 0;
        s->envelope_time = 0;
        s->envelope_count = 0;
        s->envelope_enabled = 0;
        s->frequency = 0;
        s->freq_counter = 0;
        s->cycles_left = 0;
        s->duty = 0;
        s->duty_count = 0;
        s->sweep_shift = 0;
        s->sweep_dir = 1;
        s->sweep_time = 0;
        s->sweep_count = 0;
        s->sweep_enabled = 0;
        s->sweep_neg_used = 0;
        s->level = 0;
        s->offset = 0;
        s->sample_reading = 0;
        s->current_sample = 0;
        s->noise_short = 0;
        s->noise_lfsr = 0x7FFF;
        gb_ch_l[i] = 1;
        gb_ch_r[i] = 1;
    }
    gb_ch[0].length_mask = 0x3F;
    gb_ch[1].length_mask = 0x3F;
    gb_ch[2].length_mask = 0xFF;
    gb_ch[3].length_mask = 0x3F;

    /* DMG 默认 WaveRAM */
    gb_regs[0x20] = 0xAC; gb_regs[0x21] = 0xDD;
    gb_regs[0x22] = 0xDA; gb_regs[0x23] = 0x48;
    gb_regs[0x24] = 0x36; gb_regs[0x25] = 0x02;
    gb_regs[0x26] = 0xCF; gb_regs[0x27] = 0x16;
    gb_regs[0x28] = 0x2C; gb_regs[0x29] = 0x04;
    gb_regs[0x2A] = 0xE5; gb_regs[0x2B] = 0x2C;
    gb_regs[0x2C] = 0xAC; gb_regs[0x2D] = 0xDD;
    gb_regs[0x2E] = 0xDA; gb_regs[0x2F] = 0x48;
}

/* ========== 寄存器写入 ========== */
void gb_wr(u8 reg, u8 val) {
    GB_SND xdata *s;
    u8 ch;

    if (reg <= 0x3F) {
        gb_regs[reg] = val;
    } else if (reg >= AUD3W0 && reg <= 0x2F) {
        gb_regs[reg] = val;
        return;
    } else {
        return;
    }

    /* DMG: power off 时只有 NR52 可写 (ch 长度寄存器也可写) */
    if (!gb_ctrl_on && reg != NR52 && reg != NR11 && reg != NR21 && reg != NR31 && reg != NR41)
        return;

    switch (reg) {
    /* ===== CH1: 方波 + 扫频 + 包络 ===== */
    case NR10:
        s = &gb_ch[0];
        s->reg[0] = val;
        s->sweep_shift = val & 0x07;
        s->sweep_dir = (val & 0x08) ? -1 : 1;
        s->sweep_time = (val & 0x70) >> 4;
        break;
    case NR11:
        s = &gb_ch[0];
        s->reg[1] = val;
        s->duty = (val & 0xC0) >> 6;
        s->length = val & 0x3F;
        s->length_counting = 1;
        break;
    case NR12:
        s = &gb_ch[0];
        s->reg[2] = val;
        s->envelope_value = val >> 4;
        s->envelope_dir = (val & 0x08) ? 1 : -1;
        s->envelope_time = val & 0x07;
        if (!(val & 0xF8)) s->on = 0;
        break;
    case NR13:
        s = &gb_ch[0];
        s->reg[3] = val;
        if (!s->sweep_enabled)
            s->frequency = ((s->reg[4] & 0x07) << 8) | val;
        break;
    case NR14:
        s = &gb_ch[0];
        s->reg[4] = val;
        s->length_enabled = (val & 0x40) ? 1 : 0;
        s->frequency = ((val & 0x07) << 8) | s->reg[3];
        if (val & 0x80) {
            s->on = 1;
            s->envelope_enabled = 1;
            s->envelope_value = s->reg[2] >> 4;
            s->envelope_count = s->envelope_time;
            s->sweep_count = s->sweep_time;
            s->sweep_neg_used = 0;
            s->signal = 0;
            s->length = s->reg[1] & 0x3F;
            s->length_counting = 1;
            s->frequency = ((val & 0x07) << 8) | s->reg[3];
            s->freq_counter = s->frequency;
            s->cycles_left = 0;
            s->duty_count = 0;
            s->sweep_enabled = (s->sweep_shift != 0) || (s->sweep_time != 0);
            if (!(s->reg[2] & 0xF8)) s->on = 0;
        }
        break;

    /* ===== CH2: 方波 + 包络 ===== */
    case NR21:
        s = &gb_ch[1];
        s->reg[1] = val;
        s->duty = (val & 0xC0) >> 6;
        s->length = val & 0x3F;
        s->length_counting = 1;
        break;
    case NR22:
        s = &gb_ch[1];
        s->reg[2] = val;
        s->envelope_value = val >> 4;
        s->envelope_dir = (val & 0x08) ? 1 : -1;
        s->envelope_time = val & 0x07;
        if (!(val & 0xF8)) s->on = 0;
        break;
    case NR23:
        s = &gb_ch[1];
        s->reg[3] = val;
        s->frequency = ((s->reg[4] & 0x07) << 8) | val;
        break;
    case NR24:
        s = &gb_ch[1];
        s->reg[4] = val;
        s->length_enabled = (val & 0x40) ? 1 : 0;
        s->frequency = ((val & 0x07) << 8) | s->reg[3];
        if (val & 0x80) {
            s->on = 1;
            s->envelope_enabled = 1;
            s->envelope_value = s->reg[2] >> 4;
            s->envelope_count = s->envelope_time;
            s->frequency = ((val & 0x07) << 8) | s->reg[3];
            s->freq_counter = s->frequency;
            s->cycles_left = 0;
            s->duty_count = 0;
            s->signal = 0;
            s->length = s->reg[1] & 0x3F;
            s->length_counting = 1;
            if (!(s->reg[2] & 0xF8)) s->on = 0;
        }
        break;

    /* ===== CH3: 波形 ===== */
    case NR30:
        s = &gb_ch[2];
        s->reg[0] = val;
        if (!(val & 0x80)) s->on = 0;
        break;
    case NR31:
        s = &gb_ch[2];
        s->reg[1] = val;
        s->length = val;
        s->length_counting = 1;
        break;
    case NR32:
        s = &gb_ch[2];
        s->reg[2] = val;
        s->level = (val & 0x60) >> 5;
        break;
    case NR33:
        s = &gb_ch[2];
        s->reg[3] = val;
        s->frequency = ((s->reg[4] & 0x07) << 8) | val;
        break;
    case NR34:
        s = &gb_ch[2];
        s->reg[4] = val;
        s->length_enabled = (val & 0x40) ? 1 : 0;
        s->frequency = ((val & 0x07) << 8) | s->reg[3];
        if (val & 0x80) {
            s->on = 1;
            s->offset = 0;
            s->duty = 1;
            s->duty_count = 0;
            s->length = s->reg[1];
            s->length_counting = 1;
            s->frequency = ((val & 0x07) << 8) | s->reg[3];
            s->freq_counter = s->frequency;
            s->cycles_left = -6;
            s->sample_reading = 0;
            if (!(s->reg[0] & 0x80)) s->on = 0;
        }
        break;

    /* ===== CH4: 噪声 ===== */
    case NR41:
        s = &gb_ch[3];
        s->reg[1] = val;
        s->length = val & 0x3F;
        s->length_counting = 1;
        break;
    case NR42:
        s = &gb_ch[3];
        s->reg[2] = val;
        s->envelope_value = val >> 4;
        s->envelope_dir = (val & 0x08) ? 1 : -1;
        s->envelope_time = val & 0x07;
        if (!(val & 0xF8)) s->on = 0;
        break;
    case NR43:
        s = &gb_ch[3];
        s->reg[3] = val;
        s->noise_short = (val & 0x08) ? 1 : 0;
        break;
    case NR44:
        s = &gb_ch[3];
        s->reg[4] = val;
        s->length_enabled = (val & 0x40) ? 1 : 0;
        if (val & 0x80) {
            s->on = 1;
            s->envelope_enabled = 1;
            s->envelope_value = s->reg[2] >> 4;
            s->envelope_count = s->envelope_time;
            s->freq_counter = 0;
            s->cycles_left = gb_noise_period();
            s->signal = -1;
            s->noise_lfsr = 0x7FFF;
            s->length = s->reg[1] & 0x3F;
            s->length_counting = 1;
            if (!(s->reg[2] & 0xF8)) s->on = 0;
        }
        break;

    /* ===== 控制寄存器 ===== */
    case NR50:
        gb_vol_l = val & 0x07;
        gb_vol_r = (val & 0x70) >> 4;
        break;
    case NR51:
        gb_ch_r[0] = (val & 0x01) ? 1 : 0;
        gb_ch_l[0] = (val & 0x10) ? 1 : 0;
        gb_ch_r[1] = (val & 0x02) ? 1 : 0;
        gb_ch_l[1] = (val & 0x20) ? 1 : 0;
        gb_ch_r[2] = (val & 0x04) ? 1 : 0;
        gb_ch_l[2] = (val & 0x40) ? 1 : 0;
        gb_ch_r[3] = (val & 0x08) ? 1 : 0;
        gb_ch_l[3] = (val & 0x80) ? 1 : 0;
        break;
    case NR52:
        if (!(val & 0x80)) {
            /* power off: 关闭所有通道 */
            for (ch = 0; ch < 4; ch++) gb_ch[ch].on = 0;
            gb_ctrl_on = 0;
        } else {
            gb_ctrl_on = 1;
        }
        break;
    }
}

/* ========== 内部: length tick ========== */
static void gb_tick_length(GB_SND *snd) {
    if (snd->length_enabled && snd->length_counting) {
        snd->length = (snd->length + 1) & snd->length_mask;
        if (snd->length == 0) {
            snd->on = 0;
            snd->length_counting = 0;
        }
    }
}

/* ========== 内部: sweep tick (ch1 only) ========== */
static void gb_tick_sweep(GB_SND *snd) {
    snd->sweep_count = (snd->sweep_count - 1) & 0x07;
    if (snd->sweep_count == 0) {
        snd->sweep_count = snd->sweep_time;
        if (snd->sweep_enabled && snd->sweep_time > 0) {
            u16 delta = snd->frequency >> snd->sweep_shift;
            u16 new_freq;
            snd->sweep_neg_used = (snd->sweep_dir < 0) ? 1 : 0;
            if (snd->sweep_dir > 0)
                new_freq = snd->frequency + delta;
            else
                new_freq = snd->frequency - delta;
            if (new_freq > 0x7FF) {
                snd->on = 0;
            } else if (snd->sweep_shift > 0) {
                snd->frequency = new_freq;
                snd->reg[3] = snd->frequency & 0xFF;
            }
            /* 二次 overflow 检测 */
            if (snd->sweep_dir > 0)
                new_freq = snd->frequency + (snd->frequency >> snd->sweep_shift);
            else
                new_freq = snd->frequency - (snd->frequency >> snd->sweep_shift);
            if (new_freq > 0x7FF) snd->on = 0;
        }
    }
}

/* ========== 内部: envelope tick ========== */
static void gb_tick_envelope(GB_SND *snd) {
    if (!snd->envelope_enabled) return;
    snd->envelope_count = (snd->envelope_count - 1) & 0x07;
    if (snd->envelope_count == 0) {
        snd->envelope_count = snd->envelope_time;
        if (snd->envelope_count) {
            s8 new_val = snd->envelope_value + snd->envelope_dir;
            if (new_val >= 0 && new_val <= 15)
                snd->envelope_value = new_val;
            else
                snd->envelope_enabled = 0;
        }
    }
}

/* ========== 内部: 噪声周期 ========== */
static u16 gb_noise_period(void) {
    return gb_noise_div[gb_ch[3].reg[3] & 0x07] << (gb_ch[3].reg[3] >> 4);
}

/* ========== 内部: 方波更新 ========== */
static void gb_update_square(GB_SND *snd, u16 cycles) {
    u16 distance;
    if (!snd->on) return;
    snd->cycles_left += cycles;
    if (snd->cycles_left <= 0) return;

    cycles = (u16)(snd->cycles_left >> 2);
    snd->cycles_left &= 3;
    distance = 0x800 - snd->freq_counter;
    if (cycles >= distance) {
        u16 counter;
        cycles -= distance;
        distance = 0x800 - snd->frequency;
        counter = 1 + cycles / distance;
        snd->duty_count = (snd->duty_count + counter) & 0x07;
        snd->signal = gb_duty[snd->duty][snd->duty_count];
        snd->freq_counter = snd->frequency + cycles % distance;
    } else {
        snd->freq_counter += cycles;
    }
}

/* ========== 内部: wave 更新 ========== */
static void gb_update_wave(GB_SND *snd, u16 cycles) {
    if (!snd->on) return;
    snd->cycles_left += cycles;
    while (snd->cycles_left >= 2) {
        snd->cycles_left -= 2;
        snd->freq_counter = (snd->freq_counter + 1) & 0x7FF;
        snd->sample_reading = 0;
        if (snd->freq_counter == 0x7FF)
            snd->offset = (snd->offset + 1) & 0x1F;
        if (snd->freq_counter == 0) {
            snd->sample_reading = 1;
            snd->offset = (snd->offset + 1) & 0x1F;
            snd->current_sample = gb_regs[AUD3W0 + (snd->offset >> 1)];
            if (!(snd->offset & 0x01))
                snd->current_sample >>= 4;
            snd->current_sample = (snd->current_sample & 0x0F) - 8;
            if (snd->level)
                snd->signal = snd->current_sample / (1 << (snd->level - 1));
            else
                snd->signal = 0;
            snd->freq_counter = snd->frequency;
        }
    }
}

/* ========== 内部: 噪声更新 ========== */
static void gb_update_noise(GB_SND *snd, u16 cycles) {
    u16 period = gb_noise_period();
    u16 fb;
    if (!snd->on) return;
    snd->cycles_left += cycles;
    while (snd->cycles_left >= period) {
        snd->cycles_left -= period;
        fb = ((snd->noise_lfsr >> 1) ^ snd->noise_lfsr) & 1;
        snd->noise_lfsr = (snd->noise_lfsr >> 1) | (fb << 14);
        if (snd->noise_short)
            snd->noise_lfsr = (snd->noise_lfsr & ~(u16)(1 << 6)) | (fb << 6);
        snd->signal = (snd->noise_lfsr & 1) ? -1 : 1;
    }
}

/* ========== frame sequencer ========== */
static void gb_frame_step_fn(u16 cycles) {
    u32 old_cyc = gb_frame_cycles;
    gb_frame_cycles += cycles;

    if ((old_cyc / FRAME_CYCLES) != (gb_frame_cycles / FRAME_CYCLES)) {
        gb_frame_step = (gb_frame_cycles / FRAME_CYCLES) & 0x07;
        switch (gb_frame_step) {
        case 0:
            gb_tick_length(&gb_ch[0]); gb_tick_length(&gb_ch[1]);
            gb_tick_length(&gb_ch[2]); gb_tick_length(&gb_ch[3]);
            break;
        case 2:
            gb_tick_sweep(&gb_ch[0]);
            gb_tick_length(&gb_ch[0]); gb_tick_length(&gb_ch[1]);
            gb_tick_length(&gb_ch[2]); gb_tick_length(&gb_ch[3]);
            break;
        case 4:
            gb_tick_length(&gb_ch[0]); gb_tick_length(&gb_ch[1]);
            gb_tick_length(&gb_ch[2]); gb_tick_length(&gb_ch[3]);
            break;
        case 6:
            gb_tick_sweep(&gb_ch[0]);
            gb_tick_length(&gb_ch[0]); gb_tick_length(&gb_ch[1]);
            gb_tick_length(&gb_ch[2]); gb_tick_length(&gb_ch[3]);
            break;
        case 7:
            gb_tick_envelope(&gb_ch[0]);
            gb_tick_envelope(&gb_ch[1]);
            gb_tick_envelope(&gb_ch[3]);
            break;
        }
    }

    gb_update_square(&gb_ch[0], cycles);
    gb_update_square(&gb_ch[1], cycles);
    gb_update_wave(&gb_ch[2], cycles);
    gb_update_noise(&gb_ch[3], cycles);
}

/* ========== 渲染: 每次 ISR 调用一次 (4410Hz) ========== */
s16 gb_render(void) {
    u16 incr;
    s16 mix_l, sample;

    gb_base_count += GB_BASE_INCR;
    incr = (u16)(gb_base_count >> GB_GETA_BITS);
    gb_base_count &= (1UL << GB_GETA_BITS) - 1;

    if (incr > 0) {
        gb_frame_step_fn(incr);
    }

    if (!gb_ctrl_on) return 0;

    /* 混音: 取左声道 (单声道输出) */
    mix_l = 0;
    if (gb_ch[0].on) {
        sample = (s16)gb_ch[0].signal * gb_ch[0].envelope_value;
        if (gb_ch_l[0]) mix_l += sample;
    }
    if (gb_ch[1].on) {
        sample = (s16)gb_ch[1].signal * gb_ch[1].envelope_value;
        if (gb_ch_l[1]) mix_l += sample;
    }
    if (gb_ch[2].on) {
        if (gb_ch_l[2]) mix_l += gb_ch[2].signal;
    }
    if (gb_ch[3].on) {
        sample = (s16)gb_ch[3].signal * gb_ch[3].envelope_value;
        if (gb_ch_l[3]) mix_l += sample;
    }

    /* 主音量: 0-7, 最大音量 = 7 * 15 * 4 = 420 */
    mix_l = (s16)((u32)mix_l * (gb_vol_l + 1) >> 3);

    /* 缩放到大致 -120..120 范围 (匹配 AY/SN 的 <<1) */
    return mix_l;
}
