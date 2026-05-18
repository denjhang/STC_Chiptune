// Copyright 2021-2022 IOsetting <iosetting@outlook.com>,
//                     Ivan Nalogin <egan.fryazino@gmail.com>,
//                     Alexey Evtyushkin <earvest@gmail.com>
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
#include <stdint.h>
#include <stdio.h>
#include <stdbool.h>
#include <windows.h>
#include <string.h>
#include <unistd.h>
#include "userial.h"

#ifdef __GNUC__
#define likely(x)       __builtin_expect(!!(x), 1)
#define unlikely(x)     __builtin_expect(!!(x), 0)
#else
#define likely(x)
#define unlikely(x)
#endif

static struct {
    HANDLE ttys;
    OVERLAPPED overlapped_read;
    OVERLAPPED overlapped_write;
} _w32;

int32_t com_ctor(userial_t * restrict const this, const char *path)
{
    char p[64];
    strncpy(p, path, sizeof(p) - 1);
    p[sizeof(p) - 1] = '\0';

    const HANDLE hSerial = CreateFile(p,
                                      GENERIC_READ | GENERIC_WRITE,
                                      0, NULL, OPEN_EXISTING,
                                      FILE_FLAG_OVERLAPPED, NULL);
    if (INVALID_HANDLE_VALUE != hSerial) {
        this->initiated = SERIAL_PORT_INIT_MAGIC;
        _w32.ttys = hSerial;
        (void)strncpy((char*)this->name, p, sizeof(this->name) - 1);
        this->name[sizeof(this->name) - 1] = '\0';
        return 0;
    }
    return -EBADF;
}

int32_t com_dtor(userial_t * restrict const this)
{
    if (likely(SERIAL_PORT_INIT_MAGIC == this->initiated)) {
        this->initiated = 0;
        const bool res = CloseHandle(_w32.ttys);
        return res ? 0 : -EBADF;
    }
    return -ENODEV;
}

int32_t com_speed_set(userial_t * restrict const this, uint32_t speed)
{
    if (unlikely(SERIAL_PORT_INIT_MAGIC != this->initiated)) return -ENODEV;
    DCB dcbSerialParams = {0};
    dcbSerialParams.DCBlength = sizeof(dcbSerialParams);
    if (!GetCommState(_w32.ttys, &dcbSerialParams)) return -EIO;
    if (dcbSerialParams.BaudRate != speed) {
        dcbSerialParams.BaudRate = speed;
        if (!SetCommState(_w32.ttys, &dcbSerialParams)) return -EIO;
    }
    this->speed = speed;
    return 0;
}

int32_t com_flush(userial_t * restrict const this)
{
    if (unlikely(SERIAL_PORT_INIT_MAGIC != this->initiated)) return -ENODEV;
    const bool res = PurgeComm(_w32.ttys, PURGE_RXCLEAR | PURGE_RXABORT);
    return (res ? 0 : -EIO);
}

int32_t com_setup(userial_t * restrict const this,
                  uint32_t speed, uint8_t databits, uint8_t stopbits,
                  userial_parity_t parity)
{
    if (unlikely(SERIAL_PORT_INIT_MAGIC != this->initiated)) return -ENODEV;

    if (!SetupComm(_w32.ttys, 4096, 4096)) return -EIO;

    _w32.overlapped_read.Internal = 0;
    _w32.overlapped_read.InternalHigh = 0;
    _w32.overlapped_read.Offset = 0;
    _w32.overlapped_read.OffsetHigh = 0;
    _w32.overlapped_write.Internal = 0;
    _w32.overlapped_write.InternalHigh = 0;
    _w32.overlapped_write.Offset = 0;
    _w32.overlapped_write.OffsetHigh = 0;

    _w32.overlapped_read.hEvent = CreateEvent(NULL, 1, 0, NULL);
    _w32.overlapped_write.hEvent = CreateEvent(NULL, 0, 0, NULL);

    DCB dcbSerialParams = {0};
    dcbSerialParams.DCBlength = sizeof(dcbSerialParams);
    if (!GetCommState(_w32.ttys, &dcbSerialParams)) return -EIO;

    dcbSerialParams.fBinary = 1;
    dcbSerialParams.fAbortOnError = 0;
    dcbSerialParams.wReserved = 0;
    dcbSerialParams.fDtrControl = DTR_CONTROL_DISABLE;
    dcbSerialParams.fRtsControl = RTS_CONTROL_DISABLE;
    dcbSerialParams.fParity = false;
    dcbSerialParams.fInX = 0;
    dcbSerialParams.fOutX = 0;
    dcbSerialParams.XonChar = 0x11;
    dcbSerialParams.XoffChar = 0x13;
    dcbSerialParams.ErrorChar = 0;
    dcbSerialParams.fErrorChar = 0;
    dcbSerialParams.fOutxCtsFlow = 0;
    dcbSerialParams.fOutxDsrFlow = 0;
    dcbSerialParams.XonLim = 0;
    dcbSerialParams.XoffLim = 0;
    dcbSerialParams.fNull = 0;

    dcbSerialParams.BaudRate = speed;
    dcbSerialParams.ByteSize = databits;
    dcbSerialParams.StopBits = (1 == stopbits) ? ONESTOPBIT : TWOSTOPBITS;

    switch (parity) {
        case USERIAL_PARITY_NONE: dcbSerialParams.Parity = NOPARITY; break;
        case USERIAL_PARITY_ODD:  dcbSerialParams.Parity = ODDPARITY; break;
        case USERIAL_PARITY_EVEN: dcbSerialParams.Parity = EVENPARITY; break;
        case USERIAL_PARITY_SPACE:dcbSerialParams.Parity = SPACEPARITY; break;
        case USERIAL_PARITY_MARK: dcbSerialParams.Parity = MARKPARITY; break;
    }

    if (!SetCommState(_w32.ttys, &dcbSerialParams)) return -EIO;

    COMMTIMEOUTS timeouts = {0};
    timeouts.ReadIntervalTimeout = MAXDWORD;
    timeouts.ReadTotalTimeoutConstant = 0;
    timeouts.ReadTotalTimeoutMultiplier = 0;
    timeouts.WriteTotalTimeoutConstant = 0;
    timeouts.WriteTotalTimeoutMultiplier = 0;
    if (!SetCommTimeouts(_w32.ttys, &timeouts)) return -EIO;

    if (!SetCommMask(_w32.ttys, EV_ERR)) return -EIO;
    if (!PurgeComm(_w32.ttys, PURGE_RXCLEAR | PURGE_RXABORT)) return -EIO;
    if (!EscapeCommFunction(_w32.ttys, SETRTS)) return -EIO;

    this->databits = databits;
    this->stopbits = stopbits;
    this->parity = parity;
    return 0;
}

int32_t com_rts(userial_t * restrict const this, bool level)
{
    if (unlikely(SERIAL_PORT_INIT_MAGIC != this->initiated)) return -ENODEV;
    const bool res = EscapeCommFunction(_w32.ttys, level ? SETRTS : CLRRTS);
    return (res ? 0 : -EIO);
}

int32_t com_dtr(userial_t * restrict const this, bool level)
{
    if (unlikely(SERIAL_PORT_INIT_MAGIC != this->initiated)) return -ENODEV;
    const bool res = EscapeCommFunction(_w32.ttys, level ? SETDTR : CLRDTR);
    return (res ? 0 : -EIO);
}

int32_t com_read(userial_t * restrict const this,
                 uint8_t * restrict const dst, const uint32_t dst_siz)
{
    if (unlikely(SERIAL_PORT_INIT_MAGIC != this->initiated)) return -ENODEV;
    DWORD flags;
    COMSTAT comstat;
    DWORD dwBytesRead = 0;

    if (!ResetEvent(_w32.overlapped_read.hEvent)) return -EIO;
    if (!ClearCommError(_w32.ttys, &flags, &comstat)) return -EIO;

    const bool read_ok = ReadFile(_w32.ttys, dst, dst_siz, &dwBytesRead, &_w32.overlapped_read);
    const DWORD error_id = GetLastError();
    if (unlikely((!read_ok) && (ERROR_SUCCESS != error_id) && (ERROR_IO_PENDING != error_id)))
        return -EIO;
    if (!GetOverlappedResult(_w32.ttys, &_w32.overlapped_read, &dwBytesRead, true))
        return -EIO;
    return dwBytesRead;
}

int32_t com_write(userial_t * restrict const this,
                  const uint8_t * restrict const src, const uint32_t src_siz)
{
    if (unlikely(SERIAL_PORT_INIT_MAGIC != this->initiated)) return -ENODEV;
    DWORD dwBytesWr = 0;
    const bool write_ok = WriteFile(_w32.ttys, src, src_siz, &dwBytesWr, &_w32.overlapped_write);
    const DWORD error_id = GetLastError();
    if (unlikely((!write_ok) && (error_id != ERROR_SUCCESS) && (error_id != ERROR_IO_PENDING)))
        return -EIO;
    if (!GetOverlappedResult(_w32.ttys, &_w32.overlapped_write, &dwBytesWr, true))
        return -EIO;
    return dwBytesWr;
}

userial_t serial = {
    .ctor = (userial_ctor_t)com_ctor,
    .dtor = (userial_dtor_t)com_dtor,
    .speed_set = (userial_speed_set_t)com_speed_set,
    .flush = (userial_flush_t)com_flush,
    .setup = (userial_setup_t)com_setup,
    .rts_set = (userial_rts_set_t)com_rts,
    .dtr_set = (userial_dtr_set_t)com_dtr,
    .read = (userial_read_t)com_read,
    .write = (userial_write_t)com_write,
    .initiated = 0,
};
