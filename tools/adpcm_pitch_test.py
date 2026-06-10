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

    ser = serial.Serial(PORT, BAUD, timeout=0.1)
    time.sleep(0.1)
    ser.reset_input_buffer()

    base_step = 0x0100
    scale = [0, 2, 4, 5, 7, 9, 11]

    for drum in range(6):
        print(f"=== {NAMES[drum]} ===")

        # 所有鼓: 6 通道轮转 0.025s
        ch_idx = 0
        for octave in range(1, 8):
            base_midi = 12 * octave + 12
            for semi in scale:
                midi = base_midi + semi
                if midi > 108: break
                note_names = {0:'C', 2:'D', 4:'E', 5:'F', 7:'G', 9:'A', 11:'B'}
                nn = f"{note_names.get(semi, '?')}{octave}"

                ratio = 2 ** ((midi - 60) / 12.0)
                step = int(base_step * ratio)
                step = max(1, min(step, 0xFFFF))

                ch = ch_idx % 6
                set_vol(ser, ch, 31)
                set_step16(ser, ch, step)
                note_on(ser, ch, drum)
                ch_idx += 1
                time.sleep(0.025)

                tag = 'interp' if step < 0x100 else 'direct'
                print(f"  ch{ch} {nn} step=0x{step:04X} [{tag}]")
        time.sleep(0.5)
        for c in range(6):
            note_off(ser, c)

    print("\n完成")
    for c in range(6):
        note_off(ser, c)
    ser.close()

if __name__ == "__main__":
    main()
