/* fm.h - 轻量 2-Operator FM 合成 (STC32G C251)
 * 9 voice x 2 op, 6 种波形, 4 态 ADSR 包络
 * UART: 0x51 寄存器模式 (同 AY: [0x51][addr][data])
 *   0x00-0x11: voice 0-8 note (写 data 触发 note on, data=MIDI note)
 *   0x20-0x28: voice 0-8 note off (写任意值触发)
 *   0x30-0x38: voice 0-8 wave select (data 0-5)
 */
#ifndef FM_H
#define FM_H

#include "types.h"

#define FM_VOICES   4
#define FM_OPS      (FM_VOICES * 2)
#define FM_WAVELEN  64

void fm_init(void);
s16 fm_render(void);
void fm_wr(u8 addr, u8 dat);

#endif
