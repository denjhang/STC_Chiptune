/*
 * STC32G12K128 LED Blink Test
 * Keil C251, SMALL memory model, 24MHz IRC
 * P6.0 LED blink - simplest possible test
 */

#pragma SMALL
#pragma OPTIMIZE(7, SPEED)
#pragma CODE

#include "STC32G.H"
#include <stdio.h>

typedef unsigned char  u8;
typedef unsigned int   u16;
typedef unsigned long  u32;

#define MAIN_Fosc  24000000UL

void delay_ms(u8 ms)
{
    u16 i;
    do {
        i = MAIN_Fosc / 6000;
        while (--i);
    } while (--ms);
}

void main(void)
{
    WTST = 0;     /* set wait state to 0 for max speed */
    EAXFR = 1;    /* enable extended SFR access (XFR) */
    CKCON = 0;    /* set XRAM access speed to fastest */

    P6M1 = 0x00;  /* P6 quasi-bidirectional mode */
    P6M0 = 0x00;

    P60 = 1;      /* LED off (active low on dev board) */

    while (1) {
        P60 = 0;           /* LED on */
        delay_ms(250);
        P60 = 1;           /* LED off */
        delay_ms(250);
    }
}
