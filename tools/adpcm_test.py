#!/usr/bin/env python3
"""ADPCM 打击乐器测试 - 6 鼓: BD/SD/HH/TC/TM/RS"""

import serial
import time

PORT = "COM12"
BAUD = 115200

DRUM_NAMES = ['BD', 'SD', 'HH', 'TC', 'TM', 'RS']

def pcm_send(ser, addr, data):
    """发送 PCM 命令 [0xC0][addr][data][xor] 等待 ACK"""
    chk = 0xC0 ^ addr ^ data
    pkt = bytes([0xC0, addr, data, chk])
    ser.write(pkt)
    time.sleep(0.005)
    resp = ser.read(1)
    if resp and resp[0] == 0xAA:
        return True
    ack_val = resp[0] if resp else None
    print(f"  ACK: {ack_val:#04x}" if ack_val is not None else "  ACK: None")
    return False

def pcm_note_on(ser, ch, drum):
    """PCM note on: ch 0-5, drum 0-5 (BD/SD/HH/TC/TM/RS)"""
    pcm_send(ser, 0x15 | ch, drum)

def pcm_note_off(ser, ch):
    """PCM note off: ch 0-5"""
    pcm_send(ser, 0x1B | ch, 0)

def main():
    print(f"ADPCM 打击乐器测试 - {PORT} @ {BAUD}")
    print("6 鼓: BD(0) SD(1) HH(2) TC(3) TM(4) RS(5)")

    ser = serial.Serial(PORT, BAUD, timeout=0.1)
    time.sleep(0.1)
    ser.reset_input_buffer()

    # 逐个播放 6 个鼓
    print("\n--- 逐个播放 ---")
    for i in range(3):
        for drum in range(6):
            pcm_note_on(ser, drum % 6, drum)
            print(f"  ch{drum % 6} {DRUM_NAMES[drum]}")
            time.sleep(0.3)

    # 节奏模式: BD + SD 交替, HH 持续
    print("\n--- 节奏模式 ---")
    for i in range(8):
        if i % 2 == 0:
            pcm_note_on(ser, 0, 0)  # BD
            print("  BD")
        else:
            pcm_note_on(ser, 1, 1)  # SD
            print("  SD")
        pcm_note_on(ser, 2, 2)  # HH
        time.sleep(0.2)

    print("\n全部发送完成，等待结束...")
    time.sleep(2.0)

    for c in range(6):
        pcm_note_off(ser, c)

    print("测试完成")
    ser.close()

if __name__ == "__main__":
    main()
