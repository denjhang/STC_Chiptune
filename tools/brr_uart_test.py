#!/usr/bin/env python3
"""BRR 旋律乐器扫频: 从原音上行到2倍频再下行回来

复用 0xC0 前缀, BRR 地址 0x34-0x47 (映射 brr_wr 0x00-0x13)
"""

import math, serial, sys, time

PORT = 'COM12'
BAUD = 115200

BRR_BASE = 0x34  # MCU 0xC0 addr 偏移

# (inst_idx, name, native_midi)
INSTRUMENTS = [
    (0,  'ElecPiano', 56),
    (1,  'Violin',     45),
    (2,  'Strings',    42),
    (3,  'Harp',       34),
    (4,  'Accordion',  38),
    (5,  'Organ',      63),
    (6,  'Fretless',   46),
    (7,  'JazzGtr',    58),
    (8,  'DistGtr',    59),
    (9,  'Celesta',    30),
    (10, 'Flute',      42),
    (11, 'Recorder',   43),
    (12, 'Oboe',       40),
    (13, 'Clarinet',   51),
]

NOTES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
WHITE_KEYS = [0, 2, 4, 5, 7, 9, 11]

def midi_name(n):
    return f"{NOTES[n%12]}{n//12-1}"

def send(ser, addr, data):
    xor = 0xC0 ^ (BRR_BASE + addr) ^ data
    ser.write(bytes([0xC0, BRR_BASE + addr, data, xor]))
    ser.read(1)

def set_step(ser, ch, step):
    step = int(step)
    send(ser, 0x10 + ch, (step >> 8) & 0xFF)
    send(ser, 0x14 + ch, step & 0xFF)

def note_on(ser, ch, inst_idx, midi_note):
    send(ser, 0x00 + ch, inst_idx)
    send(ser, 0x0C + ch, midi_note)

def note_off(ser, ch):
    send(ser, 0x04 + ch, 0)

def set_vol(ser, ch, vol):
    send(ser, 0x08 + ch, vol & 0x1F)

def set_adsr(ser, atk=4, dec=5, sul=12, sus=5, rel=7):
    send(ser, 0x18, (atk << 4) | dec)
    send(ser, 0x19, (sus << 4) | sul)
    send(ser, 0x1A, rel)

def white_scale_notes(start, end):
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

    arg = sys.argv[1] if len(sys.argv) > 1 else 'all'
    inst_name = arg.lower() if not arg.isdigit() else arg

    for idx, name, native in INSTRUMENTS:
        if inst_name != 'all' and name.lower() != inst_name and str(idx) != inst_name:
            continue

        orig = native
        top = orig + 24
        up_notes = white_scale_notes(24, top)
        down_notes = white_scale_notes(top, 24)

        print(f"\n{name} (native={orig} {midi_name(orig)}, 24={midi_name(24)} -> {midi_name(top)})")

        set_adsr(ser, atk=4, dec=5, sul=12, sus=5, rel=7)
        set_vol(ser, 0, 24)

        for n in up_notes:
            semi = n - orig
            step = int(round(0x0100 * (2.0 ** (semi / 12.0))))
            print(f"  UP   {midi_name(n)} semi={semi:+3d} step=0x{step:04X}")
            note_on(ser, 0, idx, n)
            time.sleep(0.3)

        for n in down_notes:
            semi = n - orig
            step = int(round(0x0100 * (2.0 ** (semi / 12.0))))
            print(f"  DOWN {midi_name(n)} semi={semi:+3d} step=0x{step:04X}")
            note_on(ser, 0, idx, n)
            time.sleep(0.3)

        note_off(ser, 0)
        time.sleep(0.3)

    print("\nDone!")
    ser.close()


if __name__ == '__main__':
    main()
