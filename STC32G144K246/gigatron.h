/* gigatron.h - Gigatron TTL 4ch 波形合成 (STC32G C251)
 * 4 通道, 共享 256 字节波形表 (可自定义), 8-bit 输出
 * UART: 0xB0 [addr][data] (同 AY 协议)
 * 寄存器:
 *   0x00-0x03: ch0-3 fnumL (频率低7位)
 *   0x04-0x07: ch0-3 fnumH (频率高7位, 写后 key *= 4)
 *   0x08-0x0B: ch0-3 wavX (波形 XOR 选择)
 *   0x0C-0x0F: ch0-3 wavA (波形幅度偏移)
 *   0x10-0x13: ch0-3 note off (key=0)
 *   0x14-0xFF: 波形表写入 (自定义波形)
 */
#ifndef GIGATRON_H
#define GIGATRON_H

#include "types.h"

#define GT_CHANS 4

void gt_init(void);
s16 gt_render(void);
void gt_wr(u8 addr, u8 dat);
u8 gt_channel_mask(void);

#endif
