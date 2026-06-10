#!/usr/bin/env python3
"""ADPCM LED 测试 - 6 通道全部反复触发，确认每个通道 LED 都亮"""

import serial
import time

PORT = "COM12"
BAUD = 115200

def pcm_send(ser, addr, data):
    chk = 0xC0 ^ addr ^ data
    ser.write(bytes([0xC0, addr, data, chk]))
    time.sleep(0.01)
    # 读掉所有残留字节
    resp = ser.read(10)
    ack = None
    for b in resp:
        if b == 0xAA:
            ack = True
            break
        elif b == 0xFF:
            ack = False
            break
    return ack

def note_on(ser, ch, drum):
    pcm_send(ser, 0x15 + ch, drum)

def set_vol(ser, ch, vol):
    pcm_send(ser, 0x21 | ch, vol)

NAMES = ['BD', 'SD', 'TC', 'HH', 'TM', 'RS']

def main():
    print(f"ADPCM LED 测试 - {PORT} @ {BAUD}")
    print("6 通道全部反复触发，每个 LED 应持续亮起")
    print()

    ser = serial.Serial(PORT, BAUD, timeout=0.1)
    time.sleep(0.1)
    ser.reset_input_buffer()

    # 6 通道全部最大音量
    for ch in range(6):
        set_vol(ser, ch, 31)

    # 每通道触发对应鼓，反复 note on 保持 active
    # ch0=BD(0), ch1=SD(1), ch2=TC(2), ch3=HH(3), ch4=TM(4), ch5=RS(5)
    print("持续触发 6 通道... (Ctrl+C 停止)")
    print("P0.2=BD  P0.3=SD  P0.4=TC  P0.5=HH  P0.6=TM  P0.7=RS")
    try:
        cnt = 0
        while True:
            for drum in range(6):
                addr = 0x15 + drum
                ok = note_on(ser, drum, drum)
                if cnt == 0:
                    print(f"  ch{drum} addr=0x{addr:02X} drum={drum} ACK={'OK' if ok else 'FAIL'}")
            if cnt == 0:
                print("  (只打印第一轮)\n")
            cnt += 1
            time.sleep(0.05)
    except KeyboardInterrupt:
        pass

    print("\n停止")
    for ch in range(6):
        pcm_send(ser, 0x1B | ch, 0)
    ser.close()

if __name__ == "__main__":
    main()
