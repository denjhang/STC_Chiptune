/* wt.h - Wavetable 4ch 合成器 (STC32G C251)
 * 4 通道, 64 字节波形表, ADSR 包络
 * 参考 fm.c 架构, 移植自 ArduinoUno_wavetable_synthesis
 *
 * 寄存器:
 *   0x00-0x03: ch0-3 note on  (data = MIDI note 24-127)
 *   0x04-0x07: ch0-3 note off
 *   0x08-0x0B: ch0-3 volume   (data = 0-31)
 *   0x10: ADSR atk|dec
 *   0x11: ADSR sul|sus
 *   0x12: ADSR rel
 *   0x13: wave select (0-5: tri/sin/saw/pulse/clipsin/abssin)
 */
#ifndef WT_H
#define WT_H

#include "types.h"

#define WT_CHANS    4

void wt_init(void);
s16 wt_render(void);
void wt_wr(u8 addr, u8 dat);
u8  wt_channel_mask(void);

#endif
