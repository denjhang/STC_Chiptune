/* adpcm.h - ADPCM 6ch (鼓声 + SF2 采样旋律乐器) (STC32G C251)
 * 6 通道 ADPCM 解码, jedi_table 查表, 12-bit acc
 *
 * 寄存器 (复用 WT 的 0xC0 前缀):
 *   0x15-0x1A: ch0-5 note on  (data: 0-5=鼓, 16-25=SF2旋律, 接下来发 midi note)
 *   0x1B-0x20: ch0-5 note off
 *   0x21-0x26: ch0-5 volume   (0-31)
 *   0x27-0x2C: ch0-5 step hi
 *   0x2D-0x32: ch0-5 step lo
 *   0x33: midi note (紧跟在 SF2 note on 之后)
 */
#ifndef PCM_H
#define PCM_H

#include "types.h"

#define PCM_CHANS    6

void pcm_init(void);
s16 pcm_render(void);
void pcm_wr(u8 addr, u8 dat);
u8  pcm_channel_mask(void);

#endif
