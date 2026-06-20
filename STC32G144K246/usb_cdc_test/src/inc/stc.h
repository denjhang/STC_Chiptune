#ifndef __STC_H__
#define __STC_H__

#include <intrins.h>

#include "..\comm\stc32g.h"
#include "config.h"
#include "port.h"

typedef bit BOOL;
typedef unsigned char BYTE;
typedef unsigned int WORD;
typedef unsigned long DWORD;

typedef unsigned char u8;
typedef unsigned int u16;
typedef unsigned long u32;

typedef signed char s8;
typedef signed int s16;
typedef signed long s32;

typedef unsigned char uchar;
typedef unsigned int uint;
typedef unsigned int ushort;
typedef unsigned long ulong;

typedef unsigned char uint8_t;
typedef unsigned int uint16_t;
typedef unsigned long uint32_t;

/* GPIO 模式宏 */
#define P0n_HighZ(bitn)  P0M1 |=  (bitn), P0M0 &= ~(bitn)
#define P0n_push_pull(bitn) P0M0 |= (bitn), P0M1 &= ~(bitn)

#endif
