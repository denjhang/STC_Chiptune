#!/usr/bin/env python3
"""SF2 采样乐器变频测试 (drum-path, 无ADSR无loop)

用法:
    python tools/sf2_pitch_test.py              # 依次播放 10 乐器 C4 扫频
    python tools/sf2_pitch_test.py piano 60     # 单乐器单音
    python tools/sf2_pitch_test.py piano         # 单乐器扫频
"""

import serial, sys, time

PORT = "COM12"
BAUD = 115200

NAMES = ['Piano', 'SlapBass', 'Shakuhachi', 'Oboe', 'Trumpet',
         'Blow', 'Oboe2', 'Strings', 'Harp', 'Guitar']


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
    hi = (step_val >> 8) & 0xFF
    lo = step_val & 0xFF
    pcm_send(ser, 0x27 + ch, hi)
    pcm_send(ser, 0x2D + ch, lo)


def note_on(ser, ch, data):
    pcm_send(ser, 0x15 + ch, data)


def note_off(ser, ch):
    pcm_send(ser, 0x1B + ch, 0)


def set_vol(ser, ch, vol):
    pcm_send(ser, 0x21 + ch, vol)


def play_sf2(ser, ch, inst_idx, step_val, dur=0.8):
    note_off(ser, ch)
    time.sleep(0.05)
    set_vol(ser, ch, 31)
    set_step16(ser, ch, step_val)
    time.sleep(0.02)
    note_on(ser, ch, 16 + inst_idx)
    time.sleep(dur)
    note_off(ser, ch)
    time.sleep(0.15)


def main():
    ser = serial.Serial(PORT, BAUD, timeout=0.1)
    time.sleep(0.1)
    ser.reset_input_buffer()

    base_step = 0x0100
    scale = [0, 2, 4, 5, 7, 9, 11]
    note_names = {0: 'C', 2: 'D', 4: 'E', 5: 'F', 7: 'G', 9: 'A', 11: 'B'}

    args = sys.argv[1:]

    if len(args) >= 1:
        name = args[0].lower()
        found = -1
        for i, n in enumerate(NAMES):
            if n.lower() == name:
                found = i
                break
        if found < 0:
            print(f"未知乐器: {name}")
            print(f"可用: {', '.join(NAMES)}")
            ser.close()
            return

        if len(args) >= 2:
            midi = int(args[1])
            ratio = 2 ** ((midi - 60) / 12.0)
            step = int(base_step * ratio)
            step = max(1, min(step, 0xFFFF))
            print(f"{NAMES[found]} MIDI {midi} step=0x{step:04X}")
            play_sf2(ser, 0, found, step, dur=2.0)
        else:
            print(f"=== {NAMES[found]} 扫频 ===")
            ch_idx = 0
            for octave in range(2, 7):
                base_midi = 12 * octave + 12
                for semi in scale:
                    midi = base_midi + semi
                    if midi > 108: break
                    nn = f"{note_names.get(semi, '?')}{octave}"
                    ratio = 2 ** ((midi - 60) / 12.0)
                    step = int(base_step * ratio)
                    step = max(1, min(step, 0xFFFF))
                    ch = ch_idx % 6
                    set_vol(ser, ch, 31)
                    set_step16(ser, ch, step)
                    note_on(ser, ch, 16 + found)
                    ch_idx += 1
                    time.sleep(0.05)
                    tag = 'interp' if step < 0x100 else 'direct'
                    print(f"  ch{ch} {nn} step=0x{step:04X} [{tag}]")
            time.sleep(0.5)
    else:
        for inst in range(10):
            print(f"=== {NAMES[inst]} C4 单音 ===")
            play_sf2(ser, 0, inst, base_step, dur=1.5)
            time.sleep(0.3)

    for c in range(6):
        note_off(ser, c)
    print("\n完成")
    ser.close()


if __name__ == "__main__":
    main()
