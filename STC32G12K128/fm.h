/* fm.h - 轻量 2-Operator FM 合成 (STC32G C251)
 * 3 voice x 2 op, 6 种波形, 4 态 ADSR 包络
 * 参考: ArduinoUnoTinyFmKeyboard
 * UART: 0x51 复用
 *   [0x51][0x00][voice][note]         -> Note On
 *   [0x51][0x01][voice]              -> Note Off
 *   [0x51][0x10][voice][17 bytes]    -> Set Tone
 *   [0x51][0x11][voice][wave]        -> Set Wave (0-5)
 *   [0x51][0x20][voice][param][val]  -> Set Param
 */
#ifndef FM_H
#define FM_H

#include "types.h"

#define FM_VOICES   3
#define FM_OPS      (FM_VOICES * 2)  /* 6 operators */
#define FM_WAVELEN  64

void fm_init(void);
s16 fm_render(void);
void fm_note_on(u8 voice, u8 note);
void fm_note_off(u8 voice);
void fm_set_tone(u8 voice, u8 *dat);
void fm_set_wave(u8 voice, u8 wave);

#endif
