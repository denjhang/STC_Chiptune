/* nes.h - NES APU 仿真核心 (STC32G C251 版) */
#ifndef NES_H
#define NES_H

/* 不 include stc.h, 由 nes.c 的 #include "stc.h" 提供 u8/u16/s16/s32 */

#define NES_GETA_BITS   24
#define NES_RATE        22050.0   /* 采样率, 用于 set_clock 计算 base_incr */

/* DMC 采样缓冲: 对应 NES CPU memory $C000-$FFFF (16KB) */
#define NES_DMC_BUF_SIZE 16384

void nes_init(void);
void nes_wr(u8 reg, u8 val);
void nes_set_clock(u32 clock_hz);
s16  nes_render(void);

/* DMC 采样数据下发: vgm_player 从 0x67 type=0xC2 RAM write block 提取后
 * 通过 [0xB6][addr_lo][addr_hi][len][data...] 调用
 * cpu_addr 是 NES CPU 地址 ($C000+), 内部映射到 nes_dmc_buf[addr - 0xC000]
 */
void nes_dmc_load(u16 cpu_addr, u8 len, u8 *buf);

#endif
