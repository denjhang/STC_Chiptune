/*
 * STC32G144K246 USB HID 单接口回环测试
 * 移植自 stc_hid-master 开源工程 (无 LIB 依赖)
 * - P2 流水灯
 * - EP1 OUT 收到数据 -> EP1 IN 回送
 */

#include "stc.h"
#include "usb.h"
#include "usb_req_class.h"

#define LED P2

void delay_ms(unsigned int ms)
{
    unsigned long i;
    do {
        i = FOSC / 6000;
        while (--i);
    } while (--ms);
}

void hid_send_ep1(BYTE *buf, BYTE len)
{
    BYTE i;

    if (DeviceState != DEVSTATE_CONFIGURED) return;
    if (Usb1InBusy) return;

    EUSB = 0;
    Usb1InBusy = 1;
    usb_write_reg(INDEX, 1);
    for (i = 0; i < len; i++)
    {
        usb_write_reg(FIFO1, buf[i]);
    }
    usb_write_reg(INCSR1, INIPRDY);
    EUSB = 1;
}

void main(void)
{
    BYTE k, temp;

    WTST = 0;
    EAXFR = 1;
    CKCON = 0;

    P0M1 = 0x00; P0M0 = 0x00;
    P1M1 = 0x00; P1M0 = 0x00;
    P2M1 = 0x00; P2M0 = 0x00;
    P3M1 = 0x00; P3M0 = 0x00;
    P4M1 = 0x00; P4M0 = 0x00;
    P5M1 = 0x00; P5M0 = 0x00;
    P6M1 = 0x00; P6M0 = 0x00;
    P7M1 = 0x00; P7M0 = 0x00;

    /* USB 引脚 P3.0/P3.1 准双向 (默认就是), 启用 IRC48M 给 USB */
    P3M1 &= ~0x03;
    P3M0 &= ~0x03;

    IRC48MCR = 0x80;
    while (!(IRC48MCR & 0x01));

    USBCLK = 0x00;
    USBCON = 0x90;

    usb_init();
    EA = 1;

    LED = 0xFE;
    delay_ms(500);

    while (1)
    {
        temp = 0x01;
        for (k = 0; k < 8; k++)
        {
            LED = ~temp;
            delay_ms(100);
            temp = temp << 1;
        }

        /* HID 回环: EP1 OUT -> EP1 IN */
        if (HidEp1OutReady)
        {
            HidEp1OutReady = 0;
            hid_send_ep1(HidEp1OutBuffer, 64);
        }
    }
}
