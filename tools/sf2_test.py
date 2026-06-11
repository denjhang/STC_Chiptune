#!/usr/bin/env python3
"""SF2 采样旋律乐器测试: 通过 UART 发送 0xC0 命令播放乐器

用法:
    python tools/sf2_test.py              # 依次播放 5 个乐器 (原音高)
    python tools/sf2_test.py piano 60     # 指定乐器+音高 (变频)
    python tools/sf2_test.py all 60       # 所有乐器同时播放 C4
    python tools/sf2_test.py chord       # 和弦测试
"""

import math, serial, sys, time

PORT = 'COM12'
BAUD = 115200

# inst_idx = 0xC0 data - 16
# orig_pitch: 采样基准音高, 发此值 = 原速播放
INSTRUMENTS = [
    (0, 'Piano',    40),
    (1, 'SlapBass', 26),
    (2, 'Guitar',   40),
    (3, 'Oboe',     28),
    (4, 'Harp',     73),
]

ADSR_TEMPLATES = {
    #         atk  dec  sul  sus  rel
    'Piano':     (3,  4,   8,   5,   4),
    'SlapBass':  (2,  9,  14,  14,   4),
    'Guitar':    (2,  5,   7,  7,   6),
    'Oboe':      (3,  5,  7,  7,   7),
    'Harp':      (2,  6,  7,  7,   6),
}

DEFAULT_ADSR = (5, 6, 8, 8, 7)


def send_cmd(ser, addr, data):
    xor = 0xC0 ^ addr ^ data
    ser.write(bytes([0xC0, addr, data, xor]))
    ack = ser.read(1)
    return ack


def set_adsr(ser, template):
    atk, dec, sul, sus, rel = template
    send_cmd(ser, 0x10, (atk << 4) | dec)
    time.sleep(0.001)
    send_cmd(ser, 0x11, (sul << 4) | sus)
    time.sleep(0.001)
    send_cmd(ser, 0x12, rel)
    time.sleep(0.001)


def set_step(ser, ch, step):
    """通过 0x27/0x2D 直接写 step 高低字节"""
    step = int(step)
    step = max(0x0020, min(step, 0x0200))  # 最高2x速
    send_cmd(ser, 0x27 + ch, (step >> 8) & 0xFF)
    send_cmd(ser, 0x2D + ch, step & 0xFF)


def note_on_sf2(ser, ch, inst_idx, midi_note, orig_pitch):
    semi = midi_note - orig_pitch
    step = int(round(0x0100 * (2.0 ** (semi / 12.0))))
    send_cmd(ser, 0x15 + ch, 16 + inst_idx)
    set_step(ser, ch, step)
    send_cmd(ser, 0x33, midi_note)


def note_off(ser, ch):
    send_cmd(ser, 0x1B + ch, 0)


def set_volume(ser, ch, vol):
    send_cmd(ser, 0x21 + ch, vol & 0x1F)


def play_instrument(ser, inst_idx, name, midi_note, orig_pitch, duration=2.0):
    adsr = ADSR_TEMPLATES.get(name, DEFAULT_ADSR)
    semi = midi_note - orig_pitch
    step = int(round(0x0100 * (2.0 ** (semi / 12.0))))
    print(f"  {name} (inst={inst_idx}, note={midi_note}, semi={semi:+d}, step=0x{step:04X})")

    set_adsr(ser, adsr)
    set_volume(ser, 0, 28)

    note_on_sf2(ser, 0, inst_idx, midi_note, orig_pitch)
    time.sleep(duration)

    note_off(ser, 0)
    time.sleep(0.5)


def main():
    ser = serial.Serial(PORT, BAUD, timeout=0.5)
    time.sleep(0.1)
    ser.reset_input_buffer()

    print(f"=== SF2 采样乐器测试 ===")
    print(f"  串口: {PORT} @ {BAUD}")

    args = sys.argv[1:]

    if 'chord' in args:
        print("\n和弦测试: Piano + Guitar + Harp")
        set_adsr(ser, ADSR_TEMPLATES['Piano'])
        set_volume(ser, 0, 20)
        note_on_sf2(ser, 0, 0, 40, 40)
        time.sleep(0.05)
        set_adsr(ser, ADSR_TEMPLATES['Guitar'])
        set_volume(ser, 1, 22)
        note_on_sf2(ser, 1, 2, 60, 40)
        time.sleep(0.05)
        set_adsr(ser, ADSR_TEMPLATES['Harp'])
        set_volume(ser, 2, 18)
        note_on_sf2(ser, 2, 4, 72, 73)
        time.sleep(4.0)
        note_off(ser, 0)
        note_off(ser, 1)
        note_off(ser, 2)
        time.sleep(0.5)

    elif 'all' in args:
        print("\n所有乐器同时 @ C4")
        for i, (idx, name, op) in enumerate(INSTRUMENTS):
            if i >= 6:
                print(f"  跳过 {name} (超出 6 通道)")
                continue
            adsr = ADSR_TEMPLATES.get(name, DEFAULT_ADSR)
            set_volume(ser, i, 20)
            note_on_sf2(ser, i, idx, 60, op)
            time.sleep(0.05)
        time.sleep(4.0)
        for i in range(len(INSTRUMENTS)):
            note_off(ser, i)
        time.sleep(0.5)

    elif len(args) >= 1:
        name = args[0].lower()
        midi_note = None
        if len(args) >= 2:
            midi_note = int(args[1])

        found = False
        for idx, iname, op in INSTRUMENTS:
            if iname.lower() == name:
                if midi_note is None:
                    midi_note = op
                print(f"\n播放 {iname} @ MIDI {midi_note}")
                play_instrument(ser, idx, iname, midi_note, op)
                found = True
                break
        if not found:
            print(f"未知乐器: {name}")
            print(f"可用: {', '.join(n for _, n, _ in INSTRUMENTS)}")

    else:
        print("\n依次播放 5 个乐器 (原音高)\n")
        for idx, name, op in INSTRUMENTS:
            play_instrument(ser, idx, name, op, op, duration=2.5)

    print("\nDone!")
    ser.close()


if __name__ == '__main__':
    main()
