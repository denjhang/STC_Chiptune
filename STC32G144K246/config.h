#ifndef __CONFIG_H__
#define __CONFIG_H__

#define FOSC                    48000000UL

/* 单 HID 接口: EP1 IN + EP1 OUT */
#define EN_EP1IN
#define EN_EP1OUT

#define EP0_SIZE                64

#ifdef EN_EP1IN
#define EP1IN_SIZE              64
#endif
#ifdef EN_EP1OUT
#define EP1OUT_SIZE             64
#endif

#endif
