/* nes.h - NES APU 仿真核心 (STC32G C251 版) */
#ifndef NES_H
#define NES_H

/* 不 include stc.h, 由 nes.c 的 #include "stc.h" 提供 u8/u16/s16/s32 */

#define NES_GETA_BITS   24
#define NES_RATE        22050.0   /* 采样率, 用于 set_clock 计算 base_incr */

/* DMC 采样缓冲: 对应 NES CPU memory $C000-$FFFF (16KB) */
#define NES_DMC_BUF_SIZE 16384

/* PCM ring buffer: Deflemask DAC stream 用 (0x90-0x95 路径).
 * 8KB 缓冲 @ 22050 pop/s = 371ms, 吸收 USB CDC 突发.
 * 上位机虚拟水位流控: pushed - elapsed*22050, 高于 75% 暂停发送. */
#define NES_PCM_RING_SIZE 8192   /* 必须 2^N */

void nes_init(void);
void nes_wr(u8 reg, u8 val);
void nes_set_clock(u32 clock_hz);
s16  nes_render(void);

/* DMC 采样数据下发: vgm_player 从 0x67 type=0xC2 RAM write block 提取后
 * 通过 [0xB6][addr_lo][addr_hi][len][data...] 调用
 * cpu_addr 是 NES CPU 地址 ($C000+), 内部映射到 nes_dmc_buf[addr - 0xC000]
 */
void nes_dmc_load(u16 cpu_addr, u8 len, u8 *buf);

/* PCM ring buffer (Deflemask DAC stream 路径):
 * nes_pcm_push: 上位机 [0xB8][byte] 调用, push 一个 PCM 字节. ring 满则丢弃.
 * nes_render 内部每次调用 nes_pcm_pop_to_vol: 有数据则 pop 写 nes_dpcm.vol,
 *   无则保持 (zero-order hold).
 * 上位机已升采样到 22050Hz (每个 PCM 字节重复 22050/freq 次),
 *   所以下位机每次 render pop 一个字节即可, 无需知道 PCM 源频率. */
void nes_pcm_push(u8 byte);

#endif
