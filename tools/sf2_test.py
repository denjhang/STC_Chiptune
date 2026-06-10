#!/usr/bin/env python3
"""SF2 采样旋律乐器测试: 通过 UART 发送 0xC0 命令播放 10 个乐器

用法:
    python tools/sf2_test.py              # 依次播放 10 个乐器 C4
    python tools/sf2_test.py piano 60     # 指定乐器+音高
    python tools/sf2_test.py all 60       # 所有乐器同时播放 C4
    python tools/sf2_test.py chord         # 和弦测试: piano+strings+harp
"""

import serial, sys, time

PORT = 'COM12'
BAUD = 115200

# 乐器名 -> inst_idx (0xC0 data = 16 + inst_idx)
INSTRUMENTS = [
    (0, 'Piano'),
    (1, 'SlapBass'),
    (2, 'Shakuhachi'),
    (3, 'Oboe'),
    (4, 'Trumpet'),
    (5, 'Blow'),
    (6, 'Oboe2'),
    (7, 'Strings'),
    (8, 'Harp'),
    (9, 'Guitar'),
]

# ADSR 参数 (hi nibble = index into env_cnt table, lo nibble = index)
# env_cnt = [0,1,2,3,4,5,7,10,13,20,29,43,64,86,128,255]
#          idx 0 1 2 3 4 5 6  7  8  9 10 11 12 13  14  15
#
# atk: 快=0(1tick) 慢=14(128tick)
# dec: 快=0(1tick) 慢=14(128tick)
# sul: 0=sustain=31, 7=sustain=17, 14=sustain=1, 15=sustain=0
# sus: 快=0(1tick) 慢=14(128tick)
# rel: 快=0(1tick) 慢=14(128tick)

ADSR_TEMPLATES = {
    #         atk  dec  sul  sus  rel
    'Piano':     (7,  6,  10,  10,   7),   # 中速起音, 中等衰减, 明显延音
    'SlapBass':  (2,  9,  14,  14,   4),   # 快起快衰, 短促
    'Shakuhachi':(3,  4,   7,   7,   9),   # 中快起, 适度延音
    'Oboe':      (3,  5,   7,   7,   7),   # 双簧管: 中速
    'Trumpet':   (4,  6,   5,   6,   7),   # 小号: 偏慢起音, 持续
    'Blow':      (2,  4,   7,   7,   9),   # 吹管: 中快
    'Oboe2':     (3,  5,   7,   7,   7),   # 双簧管2
    'Strings':   (9,  7,   3,   5,   9),   # 弦乐: 慢起音, 长延音
    'Harp':      (2,  6,   7,   7,   6),   # 竖琴: 快起, 清脆
    'Guitar':    (2,  5,   7,   7,   6),   # 吉他: 快起, 中等
}

DEFAULT_ADSR = (5, 6, 8, 8, 7)  # 默认: 中等


def send_cmd(ser, addr, data):
    """发送 [0xC0][addr][data][xor]"""
    xor = 0xC0 ^ addr ^ data
    ser.write(bytes([0xC0, addr, data, xor]))
    ack = ser.read(1)
    return ack


def set_adsr(ser, template):
    """设置 ADSR"""
    atk, dec, sul, sus, rel = template
    send_cmd(ser, 0x10, (atk << 4) | dec)   # atk|dec
    time.sleep(0.001)
    send_cmd(ser, 0x11, (sul << 4) | sus)   # sul|sus
    time.sleep(0.001)
    send_cmd(ser, 0x12, rel)                 # rel
    time.sleep(0.001)


def note_on_drum(ser, ch, drum_idx):
    """鼓声 note on"""
    send_cmd(ser, 0x15 + ch, drum_idx)


def note_on_sf2(ser, ch, inst_idx, midi_note):
    """SF2 旋律乐器 note on: 两步"""
    send_cmd(ser, 0x15 + ch, 16 + inst_idx)   # 选择乐器
    time.sleep(0.001)
    send_cmd(ser, 0x33, midi_note)             # midi note + 启动 ADSR


def note_off(ser, ch):
    """note off"""
    send_cmd(ser, 0x1B + ch, 0)


def set_volume(ser, ch, vol):
    """设置音量 0-31"""
    send_cmd(ser, 0x21 + ch, vol & 0x1F)


def play_instrument(ser, inst_idx, name, midi_note=60, duration=2.0):
    """播放单个乐器"""
    adsr = ADSR_TEMPLATES.get(name, DEFAULT_ADSR)
    print(f"  {name} (inst={inst_idx}, note={midi_note}, ADSR={adsr})")

    set_adsr(ser, adsr)
    set_volume(ser, 0, 28)

    note_on_sf2(ser, 0, inst_idx, midi_note)
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
    midi_note = 60  # C4

    if 'chord' in args:
        # 和弦: piano(0) + strings(7) + harp(8)
        print("\n和弦测试: Piano + Strings + Harp @ C4")
        set_adsr(ser, ADSR_TEMPLATES['Piano'])
        set_volume(ser, 0, 20)
        set_volume(ser, 1, 22)
        set_volume(ser, 2, 18)
        note_on_sf2(ser, 0, 0, 48)   # piano C3
        time.sleep(0.05)
        set_adsr(ser, ADSR_TEMPLATES['Strings'])
        note_on_sf2(ser, 1, 7, 60)   # strings C4
        time.sleep(0.05)
        set_adsr(ser, ADSR_TEMPLATES['Harp'])
        note_on_sf2(ser, 2, 8, 72)   # harp C5
        time.sleep(4.0)
        note_off(ser, 0)
        note_off(ser, 1)
        note_off(ser, 2)
        time.sleep(0.5)

    elif 'all' in args:
        # 所有乐器同时
        print("\n所有乐器同时 @ C4")
        for i, (idx, name) in enumerate(INSTRUMENTS):
            if i >= 6:
                print(f"  跳过 {name} (超出 6 通道)")
                continue
            adsr = ADSR_TEMPLATES.get(name, DEFAULT_ADSR)
            set_volume(ser, i, 20)
            note_on_sf2(ser, i, idx, midi_note)
            time.sleep(0.05)
        time.sleep(4.0)
        for i in range(6):
            note_off(ser, i)
        time.sleep(0.5)

    elif len(args) >= 1:
        # 指定乐器名
        name = args[0].lower()
        if len(args) >= 2:
            midi_note = int(args[1])

        found = False
        for idx, iname in INSTRUMENTS:
            if iname.lower() == name:
                print(f"\n播放 {iname} @ MIDI {midi_note}")
                play_instrument(ser, idx, iname, midi_note)
                found = True
                break
        if not found:
            print(f"未知乐器: {name}")
            print(f"可用: {', '.join(n for _, n in INSTRUMENTS)}")

    else:
        # 默认: 依次播放所有乐器
        print("\n依次播放 10 个乐器 @ C4\n")
        for idx, name in INSTRUMENTS:
            play_instrument(ser, idx, name, midi_note, duration=2.5)

    print("\nDone!")
    ser.close()


if __name__ == '__main__':
    main()
