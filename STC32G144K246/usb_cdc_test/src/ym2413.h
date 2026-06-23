/* ym2413.h - Yamaha YM2413 (OPLL) FM 音源芯片 (STC32G C251 版)
 *
 * YM2413 是雅马哈 2-operator FM 合成芯片 (OPLL), 9 通道旋律 + 5 鼓.
 * 移植自 libvgm emu2413.c (Mitsutaka Okazaki, Valley Bell).
 *
 * VGM 命令: 0x51 [reg][data] (地址/数据写, A1+D 方式) */
#ifndef YM2413_H
#define YM2413_H

void ym2413_init(void);
void ym2413_wr(u8 reg, u8 val);    /* 直接寄存器写 (reg 0x00-0x3F) */
void ym2413_set_clock(u32 clock_hz); /* 时钟设置 (标准 3579545 Hz) */
s16  ym2413_render(void);           /* 每采样调用, 返回 mono 输出 */

#endif
