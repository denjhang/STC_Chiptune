#include "stc.h"
#include "usb.h"
#include "usb_req_class.h"

BYTE bHidIdle;
volatile BOOL HidEp1OutReady;
BYTE xdata HidEp1OutBuffer[64];

static char code stcisp_cmd[] = "@STCISP#";

void usb_req_class()
{
    switch (Setup.bRequest)
    {
    case GET_REPORT:
        usb_get_report();
        break;
    case SET_REPORT:
        usb_set_report();
        break;
    case GET_IDLE:
        usb_get_idle();
        break;
    case SET_IDLE:
        usb_set_idle();
        break;
    case GET_PROTOCOL:
        usb_get_protocol();
        break;
    case SET_PROTOCOL:
        usb_set_protocol();
        break;
    default:
        usb_setup_stall();
        return;
    }
}

void usb_get_report()
{
    if ((DeviceState != DEVSTATE_CONFIGURED) ||
        (Setup.bmRequestType != (IN_DIRECT | CLASS_REQUEST | INTERFACE_RECIPIENT)))
    {
        usb_setup_stall();
        return;
    }

    Ep0State.pData = UsbBuffer;
    Ep0State.wSize = Setup.wLength;

    usb_setup_in();
}

void usb_set_report()
{
    if ((DeviceState != DEVSTATE_CONFIGURED) ||
        (Setup.bmRequestType != (OUT_DIRECT | CLASS_REQUEST | INTERFACE_RECIPIENT)))
    {
        usb_setup_stall();
        return;
    }

    Ep0State.pData = UsbBuffer;
    Ep0State.wSize = Setup.wLength;

    usb_setup_out();
}

void usb_get_idle()
{
    if ((DeviceState != DEVSTATE_CONFIGURED) ||
        (Setup.bmRequestType != (IN_DIRECT | CLASS_REQUEST | INTERFACE_RECIPIENT)))
    {
        usb_setup_stall();
        return;
    }

    Ep0State.pData = &bHidIdle;
    Ep0State.wSize = 1;

    usb_setup_in();
}

void usb_set_idle()
{
    if ((DeviceState != DEVSTATE_CONFIGURED) ||
        (Setup.bmRequestType != (OUT_DIRECT | CLASS_REQUEST | INTERFACE_RECIPIENT)))
    {
        usb_setup_stall();
        return;
    }

    bHidIdle = Setup.wValueH;

    usb_setup_status();
}

void usb_get_protocol()
{
    usb_setup_stall();
}

void usb_set_protocol()
{
    usb_setup_stall();
}

/* EP1 OUT 中断处理: 把数据搬到 HidEp1OutBuffer, 同时扫描 @STCISP# */
void usb_class_out_ep1()
{
    BYTE cnt;
    BYTE i;

    cnt = usb_bulk_intr_out(HidEp1OutBuffer, 1);
    if (cnt >= 8)
    {
        for (i = 0; i < 8; i++)
        {
            if (HidEp1OutBuffer[i] != (BYTE)stcisp_cmd[i]) break;
        }
        if (i == 8)
        {
            USBCON = 0x00;
            USBCLK = 0x00;
            IRC48MCR = 0x00;
            IAP_CONTR = 0x60;  /* 软件复位到 ISP 监控区 */
            while (1);
        }
    }
    if (cnt > 0)
    {
        HidEp1OutReady = 1;
    }
}

/* 保留空函数, usb.c 调用, 但 EP0 路径不扫描 @STCISP# (走 EP1 OUT) */
void usb_class_ep0_out_done()
{
}
