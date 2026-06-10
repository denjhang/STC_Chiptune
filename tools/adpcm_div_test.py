#!/usr/bin/env python3
"""ADPCM 步进音高测试 - 同一个鼓用不同 step 播放，听音高变化"""

import serial
import time

PORT = "COM12"
BAUD = 115200

NAMES = ['BD', 'SD', 'TC', 'HH', 'TM', 'RS']

def pcm_send(ser, addr, data):
    chk = 0xC0 ^ addr ^ data
    ser.write(bytes([0xC0, addr, data, chk]))
    time.sleep(0.002)
    resp = ser.read(10)
    for b in resp:
        if b == 0xAA: return True
        if b == 0xFF: return False
    return False

def note_on(ser, ch, drum):
    pcm_send(ser, 0x15 + ch, drum)

def note_off(ser, ch):
    pcm_send(ser, 0x1B + ch, 0)

def set_vol(ser, ch, vol):
    pcm_send(ser, 0x21 + ch, vol)

def set_step(ser, ch, step):
    pcm_send(ser, 0x27 + ch, step)

def play(ser, ch, drum, step_val, label):
    set_step(ser, ch, step_val)
    time.sleep(0.05)
    note_on(ser, ch, drum)
    time.sleep(1.0)
    note_off(ser, ch)
    time.sleep(0.2)

def main():
    import sys
    drum_idx = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    drum_idx = drum_idx % 6

    print(f"ADPCM 步进音高测试 - {PORT} @ {BAUD}")
    print(f"测试鼓: {NAMES[drum_idx]}")
    print()
    print("8.8 fixed point step: 值越大解码越快, 音高越高")
    print("  0x40 (64):  1/4速, 低两个八度")
    print("  0x80 (128): 半速, 低一个八度")
    print("  0xFF (255): ~原速 (256)")
    print()

    ser = serial.Serial(PORT, BAUD, timeout=0.1)
    time.sleep(0.1)
    ser.reset_input_buffer()

    set_vol(ser, 0, 31)

    print(f"=== {NAMES[drum_idx]} 不同 step 对比 ===")
    for sv in [0x40, 0x80, 0xFF]:
        play(ser, 0, drum_idx, sv, f"step=0x{sv:02X}")
        print("  done")

    print()
    print("=== 循环对比: 原速 vs 半速 交替 ===")
    for i in range(4):
        play(ser, 0, drum_idx, 0xFF, "normal")
        print("  done")
        play(ser, 0, drum_idx, 0x80, "half")
        print("  done")

    print()
    print("测试完成")
    note_off(ser, 0)
    ser.close()

if __name__ == "__main__":
    main()
