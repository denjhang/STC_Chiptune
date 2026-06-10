/* pcm.h - PCM 打击乐器 6ch ADPCM 解码 (STC32G C251)
 * 内置 YM2608 8KB ADPCM ROM (6 鼓: BD/SD/HH/TC/TM/RS)
 * 6 通道, 12-bit acc, jedi_table 查表解码
 *
 * 寄存器 (复用 WT 的 0xC0 前缀):
 *   0x15-0x1A: ch0-5 note on  (data = 任意, 触发播放)
 *   0x1B-0x20: ch0-5 note off (data = 任意, 停止播放)
 *   0x21-0x26: ch0-5 volume   (data = 0-31)
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
