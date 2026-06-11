#!/usr/bin/env python3
"""WT 全音阶测试 - 4通道轮替，每八度切换波形"""

import serial
import time

PORT = "COM12"
BAUD = 115200

WT_WAVE_NAMES = [
    'sq12', 'sq25', 'pulse50', 'sq75',
    'sin', 'clipsin', 'abssin', 'halfsin',
    'qsin', 'altsin', 'althalfsin', 'tri',
    'saw', 'gb_dmg'
]

def wt_send(ser, addr, data):
    """发送 WT 命令 [0xC0][addr][data][xor] 等待 ACK"""
    chk = 0xC0 ^ addr ^ data
    pkt = bytes([0xC0, addr, data, chk])
    ser.write(pkt)
    time.sleep(0.002)
    resp = ser.read(1)
    if resp and resp[0] == 0xAA:
        return True
    return False

def wt_note_on(ser, ch, note):
    """WT note on: ch 0-3, note 24-127"""
    wt_send(ser, 0x00 | ch, note)

def wt_note_off(ser, ch):
    """WT note off: ch 0-3"""
    wt_send(ser, 0x04 | ch, 0)

def wt_set_wave(ser, wave_idx):
    """WT set wave: 0-5"""
    wt_send(ser, 0x13, wave_idx)

def wt_set_release(ser, rel_val):
    """WT set release: 0-15 (中等约 7)"""
    wt_send(ser, 0x12, rel_val)

def main():
    print(f"WT 全音阶测试 - {PORT} @ {BAUD}")
    print("C2上行到C6再下行回C2, 每个八度切换波形, 14种波形循环")

    ser = serial.Serial(PORT, BAUD, timeout=0.1)
    time.sleep(0.1)
    ser.reset_input_buffer()

    wt_set_release(ser, 7)

    low = 36   # C2
    high = 96  # C7
    wave = 0

    while True:
        notes = list(range(low, high + 1)) + list(range(high - 1, low - 1, -1))
        for note in notes:
            if note > low and (note - low) % 12 == 0:
                wave = (wave + 1) % 14
                wt_set_wave(ser, wave)
                print(f"\n--- {WT_WAVE_NAMES[wave]} ---")
            elif note == low:
                print(f"--- {WT_WAVE_NAMES[wave]} ---")

            wt_note_on(ser, 0, note)
            time.sleep(0.1)
            wt_note_off(ser, 0)

        print("\n--- 循环 ---")

    ser.close()

if __name__ == "__main__":
    main()
