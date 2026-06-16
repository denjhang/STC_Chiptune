/* brr.h - BRR 4ch 旋律采样 (filter=0, SNES DSP 风格, STC32G C251)
 *
 * 4 通道 BRR 解码, filter=0 (无状态), 完美循环
 * 数据: 14 个 YRW801 XI 乐器 (brr_rom.h)
 *
 * 寄存器 (新前缀 0xD3, 4 字节, XOR校验):
 *   0x00-0x03: ch0-3 note on  (data = 0-13 乐器索引)
 *   0x04-0x07: ch0-3 note off
 *   0x08-0x0B: ch0-3 volume   (0-31)
 *   0x0C-0x0F: ch0-3 midi note (24-95, 紧跟 note on 之后)
 *   0x10-0x13: ch0-3 pitch step hi (可选覆盖, 0=用 native pitch)
 *   0x14-0x17: ch0-3 pitch step lo
 *   0x18: attack  (高4) + decay  (低4)
 *   0x19: sustain (高4) + sustain_level (低4)
 *   0x1A: release
 */
#ifndef BRR_H
#define BRR_H

#include "types.h"

#define BRR_CHANS    4

void brr_init(void);
s16 brr_render(void);
void brr_wr(u8 addr, u8 dat);
u8  brr_channel_mask(void);

#endif
