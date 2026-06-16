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
    (0,  'AcPiano',   51),
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

# ADSR 模板 (atk/dec/sul/sus/rel 都是 0-15 nibble, 索引 env_cnt[] 数值越大越快)
# 弹拨/打击乐: 高 atk (瞬间峰值) + 中 dec + sul=0 (衰减到 0) + 快 rel
# 持续乐:     低 atk (慢起音) + 中 dec + sul>0 (保持电平) + 中 rel
ADSR_TEMPLATES = {
    # idx  inst_idx  name        atk  dec  sul  sus  rel
    # 0    AcPiano:   (15, 3, 2, 4, 4)
    'AcPiano':    (13, 3, 2, 4, 4),
    # 1    Violin:    (3,  4, 8, 5, 4)
    'Violin':     (10,  4, 2, 10, 10),
    # 2    Strings:   (3,  4, 8, 5, 4)
    'Strings':    (10,  4, 2, 10, 10),
    # 3    Harp:      (15, 3, 2, 4, 4)
    'Harp':       (15, 8, 2, 4, 4),
    # 4    Accordion: (4,  5, 10, 5, 5)
    'Accordion':  (7,  3, 8, 4, 4),
    # 5    Organ:     (5,  6, 12, 6, 5)
    'Organ':      (5,  6, 12, 6, 5),
    # 6    Fretless:  (15, 12, 8, 5, 4)
    'Fretless':   (15, 3, 12, 2, 2),
    # 7    JazzGtr:   (15, 12, 8, 5, 4)
    'JazzGtr':    (15, 3, 12, 2, 2),
    # 8    DistGtr:   (15, 12, 8, 5, 4)
    'DistGtr':    (15, 8, 2, 4, 4),
    # 9    Celesta:   (15, 12, 8, 5, 4)
    'Celesta':    (15, 10, 6, 2, 2),
    # 10   Flute:     (3,  4, 9, 5, 4)
    'Flute':      (3,  4, 9, 5, 4),
    # 11   Recorder:  (3,  4, 9, 5, 4)
    'Recorder':   (10,  4, 2, 10, 10),
    # 12   Oboe:      (4,  5, 8, 5, 5)
    'Oboe':       (10,  4, 2, 10, 10),
    # 13   Clarinet:  (4,  5, 8, 5, 5)
    'Clarinet':   (10,  4, 2, 10, 10),
}
DEFAULT_ADSR = (15, 15, 15, 15, 15)

# env_cnt[16] table (matches brr.c): 数值越大 = 速度越快
ENV_CNT = [0, 1, 2, 3, 4, 5, 7, 10, 13, 20, 29, 43, 64, 86, 128, 255]

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
    print(f"  ADSR: atk={atk} (env_cnt[{atk}]={ENV_CNT[atk]:>3d}) "
          f"dec={dec} (env_cnt[{dec}]={ENV_CNT[dec]:>3d}) "
          f"sul={sul} sus={sus} (env_cnt[{sus}]={ENV_CNT[sus]:>3d}) "
          f"rel={rel} (env_cnt[{rel}]={ENV_CNT[rel]:>3d})")
    d1 = (atk << 4) | dec
    d2 = (sul << 4) | sus
    d3 = rel
    print(f"  -> send 0x18=0x{d1:02X} (wire addr=0x{0x34+0x18:02X})")
    print(f"  -> send 0x19=0x{d2:02X} (wire addr=0x{0x34+0x19:02X})")
    print(f"  -> send 0x1A=0x{d3:02X} (wire addr=0x{0x34+0x1A:02X})")
    send(ser, 0x18, d1)
    send(ser, 0x19, d2)
    send(ser, 0x1A, d3)

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
        # 限制 step 上限 0x0160 (约 +6 半音于本音之上), 超过算力不够音质劣化
        MAX_STEP = 0x0160
        max_semi = int(round(12 * math.log2(MAX_STEP / 0x0100)))
        top = min(orig + 24, orig + max_semi)
        up_notes = white_scale_notes(12, top)
        down_notes = white_scale_notes(top, 12)

        print(f"\n{name} (native={orig} {midi_name(orig)}, 12={midi_name(12)} -> {midi_name(top)} max_step=0x{MAX_STEP:04X})")

        adsr = ADSR_TEMPLATES.get(name, DEFAULT_ADSR)
        set_adsr(ser, atk=adsr[0], dec=adsr[1], sul=adsr[2], sus=adsr[3], rel=adsr[4])
        for c in range(4):
            set_vol(ser, c, 24)

        ch_idx = 0
        for n in up_notes:
            note_off(ser, ch_idx)
            semi = n - orig
            step = int(round(0x0100 * (2.0 ** (semi / 12.0))))
            print(f"  UP   ch{ch_idx} {midi_name(n)} semi={semi:+3d} step=0x{step:04X}")
            note_on(ser, ch_idx, idx, n)
            ch_idx = (ch_idx + 1) % 4
            time.sleep(0.3)

        for n in down_notes:
            note_off(ser, ch_idx)
            semi = n - orig
            step = int(round(0x0100 * (2.0 ** (semi / 12.0))))
            print(f"  DOWN ch{ch_idx} {midi_name(n)} semi={semi:+3d} step=0x{step:04X}")
            note_on(ser, ch_idx, idx, n)
            ch_idx = (ch_idx + 1) % 4
            time.sleep(0.3)

    # 全通道 note_off
    for c in range(4):
        note_off(ser, c)
    time.sleep(1.0)

    print("\nDone!")
    ser.close()


if __name__ == '__main__':
    main()
