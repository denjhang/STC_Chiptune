#!/usr/bin/env python3
"""ADPCM 调试 - 逐通道触发并读取固件回传的 mask"""

import serial
import time

PORT = "COM12"
BAUD = 115200

NAMES = ['BD', 'SD', 'TC', 'HH', 'TM', 'RS']

def pcm_send(ser, addr, data):
    chk = 0xC0 ^ addr ^ data
    ser.write(bytes([0xC0, addr, data, chk]))
    time.sleep(0.01)
    resp = ser.read(10)
    return resp

def note_on(ser, ch, drum):
    return pcm_send(ser, 0x15 + ch, drum)

def set_vol(ser, ch, vol):
    pcm_send(ser, 0x21 + ch, vol)

def main():
    ser = serial.Serial(PORT, BAUD, timeout=0.5)
    time.sleep(0.1)
    ser.reset_input_buffer()

    for ch in range(6):
        set_vol(ser, ch, 31)
        time.sleep(0.01)

    print("逐通道触发，回传格式: ACK(0xAA) + 'A'+ch + mask + '\\n'")
    print()

    for ch in range(6):
        ser.reset_input_buffer()
        resp = note_on(ser, ch, ch)
        hex_str = ' '.join(f'{b:02X}' for b in resp)
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else f'[{b:02X}]' for b in resp)
        mask = resp[2] if len(resp) > 2 else -1
        active_chs = []
        if mask >= 0:
            for i in range(6):
                if mask & (1 << i):
                    active_chs.append(f'ch{i}')
        print(f"  ch{ch} -> {NAMES[ch]:2s}: [{hex_str}]  {ascii_str}  mask=0x{mask:02X} active={','.join(active_chs)}")
        time.sleep(0.5)

    ser.close()

if __name__ == "__main__":
    main()
