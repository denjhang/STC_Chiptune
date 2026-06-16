/*
 * STC32G144K246 最小测试
 * P2.0-P2.7 流水灯 + USB CDC 回环
 */

#include "STC32G.H"
#include "ai_usb.h"

#define MAIN_Fosc 64000000L

#define LED P2

void delay_ms(unsigned int ms) {
    unsigned int i;
    do {
        i = MAIN_Fosc / 6000;
        while (--i);
    } while (--ms);
}

void main(void) {
    unsigned char k, temp;

    WTST = 0;
    EAXFR = 1;
    CKCON = 0;

    P0M0 = 0; P0M1 = 0;
    P1M0 = 0; P1M1 = 0;
    P2M0 = 0; P2M1 = 0;
    P3M0 = 0; P3M1 = 0;
    P4M0 = 0; P4M1 = 0;
    P5M0 = 0; P5M1 = 0;
    P6M0 = 0; P6M1 = 0;
    P7M0 = 0; P7M1 = 0;

    usb_init();
    EA = 1;

    LED = 0xFE;
    delay_ms(500);

    while (1) {
        temp = 0x01;
        for (k = 0; k < 8; k++) {
            LED = ~temp;
            delay_ms(100);
            temp = temp << 1;
        }

        /* USB CDC 回环: 收到数据原样发回 */
        if (UsbOutBuffer[0]) {
            USB_SendData(UsbOutBuffer, UsbOutBuffer[0] + 1);
            usb_OUT_done();
        }
    }
}
