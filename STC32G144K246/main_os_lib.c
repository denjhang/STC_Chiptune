/*
 * STC32G144K246 最小测试
 * P2流水灯 + 开源USB库 HID回环
 */

#include "STC32G.H"
#include "usb_os.h"

#define MAIN_Fosc 48000000L

#define LED P2

void delay_ms(unsigned int ms) {
    unsigned long i;
    do {
        i = MAIN_Fosc / 6000;
        while (--i);
    } while (--ms);
}

void main(void) {
    unsigned char k, temp;

    P_SW1 = 0x00;
    WTST = 0;
    EAXFR = 1;
    CKCON = 0;
    AUXR = 0x00;

    P0M1 = 0x00; P0M0 = 0x00;
    P1M1 = 0x00; P1M0 = 0x00;
    P2M1 = 0x00; P2M0 = 0x00;
    P3M1 = 0x00; P3M0 = 0x00;
    P4M1 = 0x00; P4M0 = 0x00;
    P5M1 = 0x00; P5M0 = 0x00;

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

        /* HID 回环: EP1 OUT -> EP1 IN */
        if (OutEpState & 0x01) {
            if (usb_bulk_intr_out(Ep1OutBuffer, 0x01)) {
                hid_send_report(Ep1OutBuffer, 64);
            }
        }
    }
}
