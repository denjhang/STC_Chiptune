/* fm.h - 轻量 2-Operator FM 合成 (STC32G C251)
 * 4 voice x 2 op, 6 种波形, 4 态 ADSR 包络
 * UART: 0x51 寄存器模式 (同 AY: [0x51][addr][data])
 * 寄存器映射 (模仿 OPLL 分页结构):
 *   0x00-0x09: 音色参数 (全局共用)
 *   0x10-0x13: channel 0-3 note on (data=MIDI note)
 *   0x20-0x23: channel 0-3 note off
 *   0x30-0x33: channel 0-3 volume override (0-31)
 */
#ifndef FM_H
#define FM_H

#include "types.h"

#define FM_VOICES   6
#define FM_OPS      (FM_VOICES * 2)
#define FM_WAVELEN  64

void fm_init(void);
s16 fm_render(void);
void fm_wr(u8 addr, u8 dat);
u8 fm_channel_mask(void);

#endif
