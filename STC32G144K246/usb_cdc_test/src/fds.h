/* fds.h - NES FDS (Famicom Disk System) 音源芯片 (STC32G C251 版)
 *
 * FDS 是任天堂 1986 年为 Famicom Disk System 自制的 FM 音源芯片.
 * 1 通道, 频率调制 (非雅马哈式正弦波 FM):
 *   - 64 步载波波形表 (自定义, 6-bit)
 *   - 64 步调制器波形表 (3-bit, 8 种斜率)
 *   - 调制器改变载波频率 → FM 合成
 *   - 2 个 ramp 包络 (音量 + 调制增益)
 *   - RC 低通滤波器 (cutoff 2000Hz)
 *
 * 移植自 libvgm np_nes_fds.c (NSFPlay 2.3, Valley Bell).
 * VGM 命令走 0xB4 (与 NES APU 共用), libvgm Cmd_NES_Reg 做 FDS remap. */
#ifndef FDS_H
#define FDS_H

/* 不 include stc.h, 由 fds.c 的 #include "stc.h" 提供 u8/u16/s16/s32 */

#define FDS_GETA_BITS   24
#define FDS_RATE        22050.0   /* 采样率, 用于 set_clock 计算 base_incr */

void fds_init(void);
void fds_wr(u8 reg, u8 val);      /* reg: $40-$8A 绝对地址低字节, 或 remap 后 0x80|n */
void fds_set_clock(u32 clock_hz);
s16  fds_render(void);

#endif
