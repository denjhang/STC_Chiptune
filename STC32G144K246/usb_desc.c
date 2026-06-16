#include "stc.h"
#include "usb_desc.h"

char code DEVICEDESC[18] =
{
    0x12,                   //bLength(18);
    0x01,                   //bDescriptorType(Device);
    0x00,0x02,              //bcdUSB(2.00);
    0x00,                   //bDeviceClass(0)
    0x00,                   //bDeviceSubClass(0)
    0x00,                   //bDeviceProtocol(0)
    0x40,                   //bMaxPacketSize0(64);
    0xbf,0x34,              //idVendor(34bf)
    0x0a,0xff,              //idProduct(ff0a)
    0x00,0x01,              //bcdDevice(1.00);
    0x01,                   //iManufacturer(1);
    0x02,                   //iProduct(2);
    0x00,                   //iSerialNumber(0);
    0x01,                   //bNumConfigurations(1);
};

char code LANGIDDESC[4] =
{
    0x04,0x03,
    0x09,0x04,
};

char code MANUFACTDESC[8] =
{
    0x08,0x03,
    'S',0,
    'T',0,
    'C',0,
};

char code PRODUCTDESC[30] =
{
    0x1e,0x03,
    'S',0,
    'T',0,
    'C',0,
    ' ',0,
    'U',0,
    'S',0,
    'B',0,
    ' ',0,
    'H',0,
    'I',0,
    'D',0,
};

char code PACKET0[2] =
{
    0, 0,
};

char code PACKET1[2] =
{
    1, 0,
};

/* HID Report: 64字节 IN/OUT, Consumer Control */
char code HIDREPORTDESC[27] =
{
    0x05,0x0c,              //USAGE_PAGE(Consumer);
    0x09,0x01,              //USAGE(Consumer Control);
    0xa1,0x01,              //COLLECTION(Application);
    0x15,0x00,              //  LOGICAL_MINIMUM(0);
    0x25,0xff,              //  LOGICAL_MAXIMUM(255);
    0x75,0x08,              //  REPORT_SIZE(8);
    0x95,0x40,              //  REPORT_COUNT(64);
    0x09,0x01,              //  USAGE(Consumer Control);
    0xb1,0x02,              //  FEATURE(Data,Variable);
    0x09,0x01,              //  USAGE(Consumer Control);
    0x81,0x02,              //  INPUT(Data,Variable);
    0x09,0x01,              //  USAGE(Consumer Control);
    0x91,0x02,              //  OUTPUT(Data,Variable);
    0xc0,                   //END_COLLECTION;
};

/* 单 HID 接口: EP1 IN + EP1 OUT, 总共 41 字节 */
char code CONFIGDESC[41] =
{
    /* Configuration Descriptor */
    0x09,                   //bLength(9);
    0x02,                   //bDescriptorType(Configuration);
    0x29,0x00,              //wTotalLength(41);
    0x01,                   //bNumInterfaces(1);
    0x01,                   //bConfigurationValue(1);
    0x00,                   //iConfiguration(0);
    0x80,                   //bmAttributes(BUSPower);
    0x32,                   //MaxPower(100mA);

    /* HID Interface 0 */
    0x09,                   //bLength(9);
    0x04,                   //bDescriptorType(Interface);
    0x00,                   //bInterfaceNumber(0);
    0x00,                   //bAlternateSetting(0);
    0x02,                   //bNumEndpoints(2);
    0x03,                   //bInterfaceClass(HID);
    0x00,                   //bInterfaceSubClass(0);
    0x00,                   //bInterfaceProtocol(0);
    0x00,                   //iInterface(0);

    /* HID Descriptor */
    0x09,                   //bLength(9);
    0x21,                   //bDescriptorType(HID);
    0x11,0x01,              //bcdHID(1.11);
    0x00,                   //bCountryCode(0);
    0x01,                   //bNumDescriptors(1);
    0x22,                   //bDescriptorType(HID Report);
    0x1b,0x00,              //wDescriptorLength(27);

    /* EP1 IN (Interrupt) */
    0x07,                   //bLength(7);
    0x05,                   //bDescriptorType(Endpoint);
    0x81,                   //bEndpointAddress(EP1 IN);
    0x03,                   //bmAttributes(Interrupt);
    0x40,0x00,              //wMaxPacketSize(64);
    0x0a,                   //bInterval(10ms);

    /* EP1 OUT (Interrupt) */
    0x07,                   //bLength(7);
    0x05,                   //bDescriptorType(Endpoint);
    0x01,                   //bEndpointAddress(EP1 OUT);
    0x03,                   //bmAttributes(Interrupt);
    0x40,0x00,              //wMaxPacketSize(64);
    0x0a,                   //bInterval(10ms);
};
