#ifndef __CONFIG_H__
#define __CONFIG_H__

extern unsigned long MAIN_Fosc;

/* 单 CDC 模式: 只启用 EP2/EP4 (CDC1), 关闭 EP3/EP5 (CDC2) */

#define EP0_SIZE                64
#define EP1IN_SIZE              64
#define EP2IN_SIZE              64
#define EP3IN_SIZE              64
#define EP4IN_SIZE              64
#define EP5IN_SIZE              64
#define EP1OUT_SIZE             64
#define EP2OUT_SIZE             64
#define EP3OUT_SIZE             64
#define EP4OUT_SIZE             64
#define EP5OUT_SIZE             64

#define EN_EP2IN                        /* CDC1 中断 IN */
// #define EN_EP3IN                     /* CDC2 中断 IN (关闭) */
#define EN_EP4IN                        /* CDC1 Bulk IN */
// #define EN_EP5IN                     /* CDC2 Bulk IN (关闭) */
#define EN_EP4OUT                       /* CDC1 Bulk OUT */
// #define EN_EP5OUT                    /* CDC2 Bulk OUT (关闭) */

#endif
