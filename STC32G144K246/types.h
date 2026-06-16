/* types.h - STC32G C251 基本类型 */
#ifndef TYPES_H
#define TYPES_H

/* DEF.H (via ai_usb.h) defines u8/u16/u32/s8/s16/s32 */
/* Only define if DEF.H not yet included */
#ifndef __DEF_H__
typedef unsigned char  u8;
typedef unsigned int   u16;
typedef unsigned long  u32;
typedef signed char    s8;
typedef signed int     s16;
typedef signed long    s32;
#endif

#endif
