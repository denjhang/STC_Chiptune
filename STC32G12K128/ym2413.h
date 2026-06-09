/* ym2413.h - YM2413 (OPLL) FM 合成 (STC32G C251, 查表法)
 * 9 通道 2-operator FM, 15 内置音色 + 1 用户音色
 * VGM 命令: [0x51][reg][data]
 * 参考: ArduinoUnoTinyFmKeyboard (ATmega328P 查表 FM)
 */
#ifndef YM2413_H
#define YM2413_H

#include "types.h"

#define YM_CHANS    9       /* 6 旋律 + 3 鼓 (ch6=BD, ch7=SD+TOM, ch8=HH+CY) */
#define YM_WAVELEN  64
#define YM_GETA_BITS 24
/* YM2413 clock = 3579545 Hz, internal = clock/72 = 49716 Hz
 * base_incr = 49716 * 2^24 / 17640 = 47284265 */
#define YM_BASE_INCR 47284265UL

void ym_init(void);
void ym_wr(u8 reg, u8 val);
s16 ym_render(void);

#endif
