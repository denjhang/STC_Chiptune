#!/usr/bin/env python3
"""ADPCM 鼓声变频测试 C1~C8"""

import serial, time, math

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

def set_step16(ser, ch, step_val):
    """设置 16-bit step: 0x27+ch 写高字节, 0x2D+ch 写低字节"""
    hi = (step_val >> 8) & 0xFF
    lo = step_val & 0xFF
    pcm_send(ser, 0x27 + ch, hi)
    pcm_send(ser, 0x2D + ch, lo)

def note_on(ser, ch, drum):
    pcm_send(ser, 0x15 + ch, drum)

def note_off(ser, ch):
    pcm_send(ser, 0x1B + ch, 0)

def set_vol(ser, ch, vol):
    pcm_send(ser, 0x21 + ch, vol)

def play(ser, ch, drum, step_val, label, dur=0.8):
    note_off(ser, ch)
    time.sleep(0.05)
    set_vol(ser, ch, 31)
    set_step16(ser, ch, step_val)
    time.sleep(0.02)
    note_on(ser, ch, drum)
    time.sleep(dur)
    note_off(ser, ch)
    time.sleep(0.15)

def main():
    import sys
    drum_idx = int(sys.argv[1]) if len(sys.argv) > 1 else -1

    ser = serial.Serial(PORT, BAUD, timeout=0.1)
    time.sleep(0.1)
    ser.reset_input_buffer()

    base_step = 0x0100
    dur = 0.4  # 快速

    if drum_idx >= 0:
        drums = [drum_idx]
    else:
        drums = range(6)

    for drum_idx in drums:
        print(f"=== {NAMES[drum_idx]} ===")
        for midi in [24, 36, 48, 60, 72, 84, 96, 108]:
            note_name = f'C{(midi - 12) // 12}'
            ratio = 2 ** ((midi - 60) / 12.0)
            step = int(base_step * ratio)
            step = max(1, min(step, 0xFFFF))

            note_off(ser, 0)
            time.sleep(0.02)
            set_vol(ser, 0, 31)
            set_step16(ser, 0, step)
            time.sleep(0.01)
            note_on(ser, 0, drum_idx)
            time.sleep(dur)
            note_off(ser, 0)
            time.sleep(0.05)
            tag = 'interp' if step < 0x100 else 'direct'
            print(f"  {note_name} step=0x{step:04X} [{tag}]")

    print("\n完成")
    note_off(ser, 0)
    ser.close()

if __name__ == "__main__":
    main()
