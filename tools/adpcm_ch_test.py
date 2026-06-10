#!/usr/bin/env python3
"""ADPCM 单通道逐个测试 - 确认每个通道每个鼓是否出声"""

import serial
import time
import sys

PORT = "COM12"
BAUD = 115200

def pcm_send(ser, addr, data):
    chk = 0xC0 ^ addr ^ data
    ser.write(bytes([0xC0, addr, data, chk]))
    time.sleep(0.002)
    resp = ser.read(1)
    return resp and resp[0] == 0xAA

def note_on(ser, ch, drum):
    return pcm_send(ser, 0x15 + ch, drum)

def note_off(ser, ch):
    pcm_send(ser, 0x1B + ch, 0)

def set_vol(ser, ch, vol):
    pcm_send(ser, 0x21 + ch, vol)

NAMES = ['BD', 'SD', 'TC', 'HH', 'TM', 'RS']

def main():
    print(f"ADPCM 单通道逐个测试 - {PORT} @ {BAUD}")
    print()

    ser = serial.Serial(PORT, BAUD, timeout=0.1)
    time.sleep(0.1)
    ser.reset_input_buffer()

    for ch in range(6):
        set_vol(ser, ch, 31)

    # 测试1: 每个 ch 播放对应 drum
    print("=== 测试1: chN -> drumN ===")
    for ch in range(6):
        ok = note_on(ser, ch, ch)
        print(f"  ch{ch} -> {NAMES[ch]}: ACK={'OK' if ok else 'FAIL'}")
        time.sleep(0.3)
        note_off(ser, ch)
        time.sleep(0.1)

    time.sleep(0.5)

    # 测试2: 全部 ch 都播放 BD(0)，看哪些 ch 能出声
    print("\n=== 测试2: 全部 ch 播放 BD ===")
    for ch in range(6):
        ok = note_on(ser, ch, 0)
        print(f"  ch{ch} -> BD: ACK={'OK' if ok else 'FAIL'}")
    time.sleep(1.0)
    for ch in range(6):
        note_off(ser, ch)
    time.sleep(0.2)

    # 测试3: 只用 ch0，逐个播放 6 种鼓
    print("\n=== 测试3: ch0 播放全部鼓 ===")
    for drum in range(6):
        ok = note_on(ser, 0, drum)
        print(f"  ch0 -> {NAMES[drum]}: ACK={'OK' if ok else 'FAIL'}")
        time.sleep(0.3)
        note_off(ser, 0)
        time.sleep(0.1)

    print("\n测试完成")
    ser.close()

if __name__ == "__main__":
    main()
