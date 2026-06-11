#!/usr/bin/env python3
"""SF2 乐器变频扫频: C1~C8 大调音阶"""

import serial, sys, time

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
    'Piano':     (7,  6,  10,  10,   7),
    'SlapBass':  (2,  9,  14,  14,   4),
    'Guitar':    (2,  5,   7,   7,   6),
    'Oboe':      (3,  5,   7,   7,   7),
    'Harp':      (2,  6,   7,   7,   6),
}

NOTES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']

def midi_name(n):
    return f"{NOTES[n%12]}{n//12-1}"

def send(ser, addr, data):
    xor = 0xC0 ^ addr ^ data
    ser.write(bytes([0xC0, addr, data, xor]))
    ser.read(1)

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

        print(f"\n{name} (orig={orig})")
        for n in range(24, 109):
            if n % 12 in (0, 2, 4, 5, 7, 9, 11):
                send(ser, 0x15, 16 + idx)
                time.sleep(0.001)
                send(ser, 0x33, n)
                time.sleep(0.3)

    print("\nDone!")
    ser.close()

if __name__ == '__main__':
    main()
