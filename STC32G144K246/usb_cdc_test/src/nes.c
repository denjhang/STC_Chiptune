/* nes.c - NES APU 仿真核心 (STC32G C251 版)
 * 5 通道: 2x 方波(包络+扫频), 1x 三角波, 1x 噪声(包络), 1x DPCM
 */
#include "stc.h"
#include "nes.h"

static const u8 nes_vbl_len[32] = {
    10, 254, 20,  2, 40,  4, 80,  6, 160,  8, 60, 10, 14, 12, 26, 14,
    12,  16, 24, 18, 48, 20, 96, 22, 192, 24, 72, 26, 16, 28, 32, 30
};

static const u16 nes_freq_limit[8] = {
    0x3FF, 0x555, 0x666, 0x71C, 0x787, 0x7C1, 0x7E0, 0x7F2
};

static const u16 nes_noise_freq[16] = {
    4, 8, 16, 32, 64, 96, 128, 160, 202, 254, 380, 508, 762, 1016, 2034, 4068
};

/* DPCM 速率表 (NTSC): 每个 bit 占用的 CPU 周期数, 对应 reg0 低 4 位 */
static const u16 nes_dpcm_periods[16] = {
    428, 380, 340, 320, 286, 254, 226, 214, 190, 160, 142, 128, 106, 84, 72, 54
};

static const u8 nes_duty_lut[4] = { 0x40, 0x60, 0x78, 0x9F };

typedef struct {
    u8  regs[4];
    u16 freq;
    u16 phaseacc;
    u8  adder;
    u8  env_vol;
    u16 env_phase;
    u16 sweep_phase;
    u16 vbl_length;
    u8  enabled;
    s8  output;
} NES_SQUARE;

typedef struct {
    u8  regs[4];
    u16 phaseacc;
    u8  adder;
    u16 linear_length;
    u8  linear_reload;
    u8  counter_started;
    u8  write_latency;
    u16 vbl_length;
    u8  enabled;
    s8  output;
} NES_TRI;

typedef struct {
    u8  regs[4];
    u16 lfsr;
    u16 phaseacc;
    u8  env_vol;
    u16 env_phase;
    u16 vbl_length;
    u8  enabled;
    s8  output;
} NES_NOISE;

typedef struct {
    u8  regs[4];          /* $4010-4013 */
    u16 address;          /* 当前读地址 (NES CPU memory $C000+) */
    u16 length;           /* 剩余字节数 */
    u8  cur_byte;         /* 当前字节缓冲 */
    u16 bits_left;        /* 总剩余 bit 数 (length<<3 递减到 0, 对齐 libvgm bits_left) */
    u16 phaseacc;         /* 位周期累加 */
    u8  enabled;          /* 由 $4015 bit4 控制 */
    u8  active;           /* DMC 正在播 (内部状态) */
    s16 vol;              /* 7-bit DAC 累积 (0..127) */
    s8  output;
} NES_DPCM;

static NES_SQUARE xdata nes_squ[2];
static NES_TRI xdata nes_tri;
static NES_NOISE xdata nes_noi;
static NES_DPCM xdata nes_dpcm;
static u8  xdata nes_regs[0x18];

/* DMC 采样缓冲: 对应 NES CPU memory $C000-$FFFF (16KB) */
u8 xdata nes_dmc_buf[NES_DMC_BUF_SIZE];

/* PCM ring buffer: Deflemask DAC stream (0x90-0x95 路径).
 * 上位机 [0xB8][byte] push, nes_render 每次 pop 写 nes_dpcm.vol.
 * 8KB @ 22050 pop/s = 371ms 缓冲, 吸收 USB CDC 突发. */
u8 xdata nes_pcm_ring[NES_PCM_RING_SIZE];
volatile u16 data nes_pcm_head;   /* push 写位置 (主循环 process_uart) */
volatile u16 data nes_pcm_tail;   /* pop 读位置 (timer0 ISR nes_render) */

static u32 data nes_base_count;
static u32 data nes_base_incr;
static u16 data nes_frame_div;

void nes_set_clock(u32 clock_hz) {
    nes_base_incr = (u32)(((double)clock_hz * (double)(1UL << NES_GETA_BITS)) / NES_RATE);
}

void nes_init(void) {
    u8 i, j;
    u16 k;
    for (i = 0; i < 0x18; i++) nes_regs[i] = 0;
    nes_base_count = 0;
    nes_frame_div = 0;
    nes_set_clock(1789773UL);

    for (i = 0; i < 2; i++) {
        for (j = 0; j < 4; j++) nes_squ[i].regs[j] = 0;
        nes_squ[i].freq = 0;
        nes_squ[i].phaseacc = 0;
        nes_squ[i].adder = 0;
        nes_squ[i].env_vol = 0;
        nes_squ[i].env_phase = 0;
        nes_squ[i].sweep_phase = 0;
        nes_squ[i].vbl_length = 0;
        nes_squ[i].enabled = 0;
        nes_squ[i].output = 0;
    }

    for (j = 0; j < 4; j++) nes_tri.regs[j] = 0;
    nes_tri.phaseacc = 0;
    nes_tri.adder = 0;
    nes_tri.linear_length = 0;
    nes_tri.linear_reload = 0;
    nes_tri.counter_started = 0;
    nes_tri.write_latency = 0;
    nes_tri.vbl_length = 0;
    nes_tri.enabled = 0;
    nes_tri.output = 0;

    for (j = 0; j < 4; j++) nes_noi.regs[j] = 0;
    nes_noi.lfsr = 1;
    nes_noi.phaseacc = 0;
    nes_noi.env_vol = 0;
    nes_noi.env_phase = 0;
    nes_noi.vbl_length = 0;
    nes_noi.enabled = 0;
    nes_noi.output = 0;

    /* DMC 初始化 */
    for (j = 0; j < 4; j++) nes_dpcm.regs[j] = 0;
    nes_dpcm.address = 0;
    nes_dpcm.length = 0;
    nes_dpcm.cur_byte = 0;
    nes_dpcm.bits_left = 0;
    nes_dpcm.phaseacc = 0;
    nes_dpcm.enabled = 0;
    nes_dpcm.active = 0;
    nes_dpcm.vol = 0;
    nes_dpcm.output = 0;

    /* 清空 DMC 缓冲 */
    for (k = 0; k < NES_DMC_BUF_SIZE; k++) nes_dmc_buf[k] = 0;

    /* PCM ring buffer 初始化 (Deflemask DAC stream 路径) */
    nes_pcm_head = 0;
    nes_pcm_tail = 0;

    /* 自动 enable sq1/sq2/tri/noise (对齐 libvgm device_reset_nesapu line 901-902):
     * libvgm 在 reset 时自动发 $4015=0x0F, 某些 VGM (如 Kirby 16 Crane Fever)
     * 完全不写 $4015, 如果不默认 enable 会全通道无声. */
    nes_squ[0].enabled = 1;
    nes_squ[1].enabled = 1;
    nes_tri.enabled = 1;
    nes_noi.enabled = 1;
    /* DMC 不默认 enable (bit4), 由 $4015 或 $4015 trigger DMC 时开启 */
}

void nes_dmc_load(u16 cpu_addr, u8 len, u8 *buf) {
    /* 把 PC 下发的采样数据写到 nes_dmc_buf[cpu_addr - 0xC000] */
    u16 offset = cpu_addr - 0xC000;
    u8 i;
    for (i = 0; i < len; i++) {
        if (offset + i < NES_DMC_BUF_SIZE) {
            nes_dmc_buf[offset + i] = buf[i];
        }
    }
}

void nes_pcm_push(u8 byte) {
    /* PCM ring buffer push (主循环 process_uart 调用, 非中断上下文).
     * ring 满则丢弃 (保护节奏, PCM 连续流丢几字节听不出).
     * head/tail 用 mask 运算保证 2^N 回绕, 无需取模. */
    u16 next = (nes_pcm_head + 1) & (NES_PCM_RING_SIZE - 1);
    if (next == nes_pcm_tail) return;   /* 满, 丢弃 */
    nes_pcm_ring[nes_pcm_head] = byte;
    nes_pcm_head = next;
}

void nes_wr(u8 reg, u8 val) {
    u8 ch;

    if (reg > 0x17) return;
    nes_regs[reg] = val;

    switch (reg) {
    case 0x00: case 0x04:
        ch = (reg >> 2) & 1;
        nes_squ[ch].regs[0] = val;
        break;
    case 0x01: case 0x05:
        ch = (reg >> 2) & 1;
        nes_squ[ch].regs[1] = val;
        break;
    case 0x02: case 0x06:
        ch = (reg >> 2) & 1;
        nes_squ[ch].regs[2] = val;
        if (nes_squ[ch].enabled) {
            nes_squ[ch].freq = ((nes_squ[ch].regs[3] & 7) << 8) + val;
            nes_squ[ch].freq += 1;
        }
        break;
    case 0x03: case 0x07:
        ch = (reg >> 2) & 1;
        nes_squ[ch].regs[3] = val;
        /* NES 硬件: length counter 加载独立于 $4015 enable (见 $400F 注释) */
        nes_squ[ch].vbl_length = nes_vbl_len[val >> 3];
        nes_squ[ch].env_vol = 0;
        nes_squ[ch].freq = (((val & 7) << 8) + nes_squ[ch].regs[2]) + 1;
        break;

    case 0x08:
        nes_tri.regs[0] = val;
        break;
    case 0x09:
        nes_tri.regs[1] = val;
        break;
    case 0x0A:
        nes_tri.regs[2] = val;
        break;
    case 0x0B:
        nes_tri.regs[3] = val;
        nes_tri.write_latency = 3;
        /* NES 硬件: length counter 加载独立于 $4015 enable (见 $400F 注释) */
        nes_tri.vbl_length = nes_vbl_len[val >> 3];
        nes_tri.linear_length = (nes_tri.regs[0] & 0x7F) + 1;
        nes_tri.linear_reload = 1;
        break;

    case 0x0C:
        nes_noi.regs[0] = val;
        break;
    case 0x0D:
        nes_noi.regs[1] = val;
        break;
    case 0x0E:
        nes_noi.regs[2] = val;
        break;
    case 0x0F:
        nes_noi.regs[3] = val;
        /* NES 硬件: length counter 加载独立于 $4015 enable.
         * libvgm 加 if(enabled) 检查, 但某些 VGM (如 Kirby 15 Cloud Level)
         * 在 $4015 enable 之前就写 $400F trigger, 导致 vbl_length 永远 0 → 静音.
         * 移除 enabled 检查, trigger 总是加载 length (符合 NES 硬件文档). */
        nes_noi.vbl_length = nes_vbl_len[val >> 3];
        nes_noi.env_vol = 0;
        break;

    /* === DMC 寄存器 ($4010-4013) === */
    case 0x10:
        nes_dpcm.regs[0] = val;   /* IRQ/loop/rate */
        break;
    case 0x11:
        nes_dpcm.regs[1] = val & 0x7F;  /* 7-bit DAC direct load */
        nes_dpcm.vol = val & 0x7F;
        break;
    case 0x12:
        nes_dpcm.regs[2] = val;   /* sample addr: CPU = 0xC000 + val*64 */
        break;
    case 0x13:
        nes_dpcm.regs[3] = val;   /* sample len = val*16 + 1 */
        break;

    case 0x15:
        nes_squ[0].enabled = (val & 0x01) ? 1 : 0;
        if (!(val & 0x01)) nes_squ[0].vbl_length = 0;
        nes_squ[1].enabled = (val & 0x02) ? 1 : 0;
        if (!(val & 0x02)) nes_squ[1].vbl_length = 0;
        nes_tri.enabled = (val & 0x04) ? 1 : 0;
        if (!(val & 0x04)) { nes_tri.vbl_length = 0; nes_tri.linear_length = 0; nes_tri.counter_started = 0; }
        nes_noi.enabled = (val & 0x08) ? 1 : 0;
        if (!(val & 0x08)) nes_noi.vbl_length = 0;

        /* DMC 启停: bit4=1 启动一次 DMA, 仅在当前未活跃时触发.
         * 对齐 libvgm apu_dpcmreset (line 412-419):
         *   address = 0xC000 + (regs[2] << 6)
         *   length  = (regs[3] << 4) + 1
         *   bits_left = length << 3   (总 bit 数, 不是字节计数!)
         * apu_dpcm 每次 bits_left--, bit_pos = 7-(bits_left&7), 每 8 次读新字节 */
        if (val & 0x10) {
            if (!nes_dpcm.active) {
                nes_dpcm.address = 0xC000 + (nes_dpcm.regs[2] << 6);
                nes_dpcm.length = ((u16)nes_dpcm.regs[3] << 4) + 1;
                nes_dpcm.bits_left = nes_dpcm.length << 3;   /* 总 bit 数 (对齐 libvgm) */
                nes_dpcm.cur_byte = 0;
                nes_dpcm.phaseacc = 0;
                nes_dpcm.active = 1;
                nes_dpcm.enabled = 1;
            }
        } else {
            nes_dpcm.enabled = 0;
            nes_dpcm.active = 0;
        }
        break;

    case 0x17:
        break;
    }
}

static void nes_update_square(NES_SQUARE *chan, u16 cycles, u8 do_frame) {
    u16 freq;

    if (!chan->enabled) { chan->output = 0; return; }

    if (do_frame && !(chan->regs[0] & 0x20)) {
        if (chan->vbl_length > 0) chan->vbl_length--;
    }
    if (!chan->vbl_length) { chan->output = 0; return; }

    if (do_frame && !(chan->regs[0] & 0x10)) {
        if (chan->regs[0] & 0x20)
            chan->env_vol = (chan->env_vol + 1) & 15;
        else if (chan->env_vol < 15)
            chan->env_vol++;
    }

    freq = ((chan->regs[3] & 7) << 8) + chan->regs[2] + 1;

    /* Sweep: 两个方波都跑 (对齐 libvgm apu_square) */
    if ((chan->regs[1] & 0x80) && (chan->regs[1] & 7)) {
        u8 sweep_delay = ((chan->regs[1] >> 4) & 7) + 1;
        if (do_frame) {
            chan->sweep_phase++;
            if (chan->sweep_phase >= sweep_delay) {
                chan->sweep_phase = 0;
                if (chan->regs[1] & 8)
                    freq -= freq >> (chan->regs[1] & 7);
                else
                    freq += freq >> (chan->regs[1] & 7);
            }
        }
    }

    /* freq_limit 选择 (Delek 修复, 对齐 libvgm):
     * sweep 启用时用 regs[1]&7, 禁用时用 index 7 (最大限制, 几乎不限制)
     * 否则 sweep 关闭的方波会被 freq_limit[0]=8 卡死所有正常音 */
    {
        u8 freq_index = (chan->regs[1] & 0x80) ? (chan->regs[1] & 7) : 7;
        if (freq < 4 || freq > nes_freq_limit[freq_index]) {
            chan->output = 0;
            return;
        }
    }

    chan->phaseacc += cycles;
    while (chan->phaseacc >= freq) {
        chan->phaseacc -= freq;
        chan->adder = (chan->adder + 1) & 0x0F;
    }

    {
        u8 duty = nes_duty_lut[chan->regs[0] >> 6];
        u8 vol;
        if (chan->regs[0] & 0x10)
            vol = chan->regs[0] & 0x0F;
        else
            vol = 0x0F - chan->env_vol;

        if (duty & (1 << (7 - (chan->adder >> 1))))
            chan->output = vol;
        else
            chan->output = -vol;
    }
}

static void nes_update_tri(NES_TRI *chan, u16 cycles, u8 do_frame) {
    u16 freq;

    if (!chan->enabled) { chan->output = 0; return; }

    if (do_frame) {
        if (!chan->counter_started) {
            if (chan->write_latency > 0) chan->write_latency--;
            if (chan->write_latency == 0) chan->counter_started = 1;
        }

        if (chan->counter_started) {
            if (chan->linear_reload)
                chan->linear_length = (chan->regs[0] & 0x7F) + 1;
            else if (chan->linear_length > 0)
                chan->linear_length--;

            if (!(chan->regs[0] & 0x80))
                chan->linear_reload = 0;

            if (chan->vbl_length > 0 && !(chan->regs[0] & 0x80))
                chan->vbl_length--;
        }
    }

    if (!chan->linear_length || !chan->vbl_length) { chan->output = 0; return; }

    freq = ((chan->regs[3] & 7) << 8) + chan->regs[2] + 1;
    if (freq < 4) { chan->output = 0; return; }

    chan->phaseacc += cycles;
    while (chan->phaseacc >= freq) {
        chan->phaseacc -= freq;
        chan->adder = (chan->adder + 1) & 0x1F;

        chan->output = chan->adder & 0x0F;
        if (chan->adder & 8)
            chan->output ^= 0x07;
        else
            chan->output ^= 0x08;
        if (chan->adder & 0x10)
            chan->output ^= 0x0F;
        chan->output = (chan->output << 1) - 0x10;
    }
}

static void nes_update_noise(NES_NOISE *chan, u16 cycles, u8 do_frame) {
    u16 freq;
    u8 vol;

    if (!chan->enabled) { chan->output = 0; return; }

    if (do_frame) {
        if (!(chan->regs[0] & 0x20)) {
            if (chan->vbl_length > 0) chan->vbl_length--;
        }
        if (!(chan->regs[0] & 0x10)) {
            if (chan->regs[0] & 0x20)
                chan->env_vol = (chan->env_vol + 1) & 15;
            else if (chan->env_vol < 15)
                chan->env_vol++;
        }
    }

    if (!chan->vbl_length) { chan->output = 0; return; }

    freq = nes_noise_freq[chan->regs[2] & 0x0F];

    chan->phaseacc += cycles;
    while (chan->phaseacc >= freq) {
        chan->phaseacc -= freq;
        {
            u16 fb = ((chan->lfsr & 1) ^ ((chan->lfsr >> ((chan->regs[2] & 0x80) ? 6 : 1)) & 1));
            chan->lfsr = (chan->lfsr >> 1) | (fb << 14);
        }
    }

    if (chan->regs[0] & 0x10)
        vol = chan->regs[0] & 0x0F;
    else
        vol = 0x0F - chan->env_vol;

    chan->output = (chan->lfsr & 1) ? vol : -vol;
}

/* DMC 更新: 参考 libvgm nes_apu.c apu_dpcm
 * 每个 NES 周期减 phaseacc, <0 时消耗一个 bit:
 *   - bit_pos == 7 (新字节开头): 从 nes_dmc_buf 读一字节
 *   - bit=1 vol+=2, bit=0 vol-=2
 *   - vol 钳位 [0..127]
 *   - 字节读完 length--, ==0 时: 如果 loop 重启, 否则 active=0
 */
static void nes_update_dpcm(NES_DPCM xdata *chan, u16 cycles) {
    u16 period;

    if (!chan->active) { chan->output = (s8)(chan->vol - 64); return; }

    period = nes_dpcm_periods[chan->regs[0] & 0x0F];

    /* cycles 是本采样的 CPU 周期数, 减到 phaseacc.
     * 严格对齐 libvgm nes_apu.c apu_dpcm (line 423-484):
     *   - bits_left 先递减, bit_pos = 7 - (bits_left & 7), LSB first
     *   - bit_pos == 7 时读新字节 (不是 bit_pos == 0)
     *   - vol -= 2 的条件是 vol >= 2 (不是 vol > 0), 避免 vol 越界变负 */
    {
        s32 acc = (s32)chan->phaseacc - (s32)cycles;
        while (acc < 0) {              /* libvgm 用 < 0, 不是 <= 0 (避免多消耗一个 bit) */
            u8 bit_pos;
            acc += period;

            if (chan->length == 0) {
                chan->active = 0;
                chan->enabled = 0;
                if (chan->regs[0] & 0x40) {
                    /* loop: 重启 (对齐 apu_dpcmreset) */
                    chan->address = 0xC000 + (chan->regs[2] << 6);
                    chan->length = ((u16)chan->regs[3] << 4) + 1;
                    chan->bits_left = (u16)chan->length << 3;   /* 总 bit 数, 不是固定 8 */
                    chan->active = 1;
                    chan->enabled = 1;
                } else {
                    break;
                }
            }

            chan->bits_left--;                       /* 先递减 (对齐 libvgm) */
            bit_pos = 7 - (chan->bits_left & 7);     /* LSB first: bits_left 7→0 映射 bit_pos 0→7 */
            if (bit_pos == 7) {                       /* bit_pos==7 时读新字节 */
                u16 ofs = chan->address - 0xC000;
                if (ofs < NES_DMC_BUF_SIZE) {
                    chan->cur_byte = nes_dmc_buf[ofs];
                } else {
                    chan->cur_byte = 0;
                }
                chan->address++;
                /* NES 硬件: address 溢出 $FFFF 后回到 $8000 (对齐 libvgm line 472-473).
                 * u16 在 0xFFFF++ 后回绕到 0, 检测 0 并设为 $8000. */
                if (chan->address == 0) chan->address = 0x8000;
                chan->length--;
            }

            /* 处理当前 bit (LSB first, 对齐 libvgm line 477-482) */
            if (chan->cur_byte & (1 << bit_pos)) {
                if (chan->vol < 127) chan->vol += 2;
            } else {
                if (chan->vol >= 2) chan->vol -= 2;   /* >=2 避免 vol=1 时减成 -1 */
            }
        }
        chan->phaseacc = (u16)acc;
    }

    /* DMC 输出: 7-bit unsigned DAC, libvgm 转 signed (-64) */
    chan->output = (s8)(chan->vol - 64);
}

s16 nes_render(void) {
    u16 cycles;
    s16 mix;
    u8 do_frame = 0;

    nes_base_count += nes_base_incr;
    cycles = (u16)(nes_base_count >> NES_GETA_BITS);
    nes_base_count &= (1UL << NES_GETA_BITS) - 1;

    nes_frame_div++;
    if (nes_frame_div >= 92) {  /* 22050/240 ≈ 91.875, NES frame counter 240Hz */
        nes_frame_div = 0;
        do_frame = 1;
    }

    if (cycles > 0) {
        nes_update_square(&nes_squ[0], cycles, do_frame);
        nes_update_square(&nes_squ[1], cycles, do_frame);
        nes_update_tri(&nes_tri, cycles, do_frame);
        nes_update_noise(&nes_noi, cycles, do_frame);
        nes_update_dpcm(&nes_dpcm, cycles);
    }

    /* PCM ring buffer pop (Deflemask DAC stream 路径, timer0 ISR 22050Hz).
     * DMC 引擎未 active 时 ($4015 bit4=0, Deflemask DAC stream 就是这种状态),
     * 从 ring 取一字节写 nes_dpcm.vol. ring 空 则保持 (zero-order hold).
     * 上位机已升采样到 22050, 每次 render pop 一个字节即可.
     * 注意: head 可能被主循环改, 用局部快照避免竞态 (ISR 读取 tail 推进). */
    if (!nes_dpcm.active && nes_pcm_head != nes_pcm_tail) {
        nes_dpcm.vol = nes_pcm_ring[nes_pcm_tail];
        nes_pcm_tail = (nes_pcm_tail + 1) & (NES_PCM_RING_SIZE - 1);
    }

    mix = (s16)nes_squ[0].output + nes_squ[1].output;
    mix += (s16)(nes_tri.output * 3 >> 2);
    mix += (s16)(nes_noi.output * 3 >> 2);
    /* DMC 输出范围 ±64, 全幅 */
    mix += (s16)nes_dpcm.output;

    mix = mix * 1;
    return mix;
}
