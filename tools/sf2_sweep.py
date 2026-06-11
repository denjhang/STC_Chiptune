#!/usr/bin/env python3
"""SF2 乐器变频扫频: 从原音上行到2倍频再下行回来

变频方式: Python 端计算 step = 0x0100 * 2^(semi/12),
通过 0x27/0x2D 直接写入 MCU step 寄存器, 0x33 只启动 ADSR。
"""

import math, serial, sys, time

PORT = 'COM12'
BAUD = 115200

INSTRUMENTS = [
    (0, 'Piano',    40),
    (1, 'SlapBass', 26),
    (2, 'Guitar',   40),
    (3, 'Oboe',     28),
    (4, 'Harp',     73),
]

ADSR_TEMPLATES = {
    'Piano':     (3,  4,  8,  5,  4),
    'SlapBass':  (2,  9,  14,  14,   4),
    'Guitar':    (2,  5,   7,  7,   6),
    'Oboe':      (3,  5,   7,  7,   7),
    'Harp':      (2,  6,   7,  7,   6),
}

NOTES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
WHITE_KEYS = [0, 2, 4, 5, 7, 9, 11]  # 大调音阶

def midi_name(n):
    return f"{NOTES[n%12]}{n//12-1}"

def send(ser, addr, data):
    xor = 0xC0 ^ addr ^ data
    ser.write(bytes([0xC0, addr, data, xor]))
    ser.read(1)

def set_step(ser, ch, step):
    step = int(step)
    step = max(0x0020, min(step, 0x0400))  # 最高4x速
    send(ser, 0x27 + ch, (step >> 8) & 0xFF)
    send(ser, 0x2D + ch, step & 0xFF)

def white_scale_notes(start, end, step_semi=2):
    """从 start 出发，按大调音阶（全全半全全全半）生成音符列表"""
    notes = []
    n = start
    direction = 1 if end >= start else -1
    while True:
        if n % 12 in WHITE_KEYS:
            notes.append(n)
        if direction > 0 and n >= end:
            break
        if direction < 0 and n <= end:
            break
        n += direction
    return notes

def main():
    ser = serial.Serial(PORT, BAUD, timeout=0.1)
    time.sleep(0.1)
    ser.reset_input_buffer()

    inst_name = sys.argv[1].lower() if len(sys.argv) > 1 else 'all'

    for idx, name, orig in INSTRUMENTS:
        if inst_name != 'all' and name.lower() != inst_name:
            continue

        adsr = ADSR_TEMPLATES[name]
        send(ser, 0x10, (adsr[0] << 4) | adsr[1])
        time.sleep(0.002)
        send(ser, 0x11, (adsr[2] << 4) | adsr[3])
        time.sleep(0.002)
        send(ser, 0x12, adsr[4])
        time.sleep(0.002)
        send(ser, 0x21, 28)

        top = orig + 24  # 原音到4倍频 (升2八度)

        # 上行: 24 -> top (大调音阶)
        up_notes = white_scale_notes(24, top)
        # 下行: top 回到 24 (大调音阶)
        down_notes = white_scale_notes(top, 24)

        print(f"\n{name} (orig={orig}, 24={midi_name(24)} -> {midi_name(top)})")

        for n in up_notes:
            semi = n - orig
            step = int(round(0x0100 * (2.0 ** (semi / 12.0))))
            print(f"  UP   {midi_name(n)} semi={semi:+3d} step=0x{step:04X}")
            send(ser, 0x15, 16 + idx)
            set_step(ser, 0, step)
            send(ser, 0x33, n)
            time.sleep(0.3)

        for n in down_notes:
            semi = n - orig
            step = int(round(0x0100 * (2.0 ** (semi / 12.0))))
            print(f"  DOWN {midi_name(n)} semi={semi:+3d} step=0x{step:04X}")
            send(ser, 0x15, 16 + idx)
            set_step(ser, 0, step)
            send(ser, 0x33, n)
            time.sleep(0.3)

    print("\nDone!")
    ser.close()

if __name__ == '__main__':
    main()
