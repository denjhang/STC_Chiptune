#!/usr/bin/env python3
"""ADPCM 鼓机超级加强版 - 从 drum.ini + drum_patterns/*.ini 读取

用法:
    python tools/adpcm_drumkit_pro.py           # 依次播放全部风格
    python tools/adpcm_drumkit_pro.py 3          # 只播第 3 个
    python tools/adpcm_drumkit_pro.py list       # 列出全部风格
"""

import serial, sys, time, os

ENC = 'utf-8'
PORT = "COM12"
BAUD = 115200

BASE_STEP = [0x0100, 0x0100, 0x0080, 0x0100, 0x0080, 0x0080]

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DRUM_INI = os.path.join(SCRIPT_DIR, "drum.ini")
PATTERNS_DIR = os.path.join(SCRIPT_DIR, "drum_patterns")


def load_map(path):
    midi_map = {}
    section = None
    with open(path, encoding=ENC) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line.startswith('['):
                section = line.strip('[]')
                continue
            if section == 'map':
                if '|' in line:
                    parts = line.split('|')
                    note = int(parts[0].split('=')[0].strip())
                    drum_id = int(parts[1].strip())
                    ratio = float(parts[2].strip())
                    midi_map[note] = (drum_id, ratio)
    return midi_map


def load_aliases(path):
    aliases = {}
    section = None
    with open(path, encoding=ENC) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line.startswith('['):
                section = line.strip('[]')
                continue
            if section == 'aliases':
                if '=' in line and '|' not in line:
                    k, v = line.split('=', 1)
                    aliases[k.strip()] = int(v.strip())
    return aliases


def load_volume(path):
    vol_map = {}
    section = None
    with open(path, encoding=ENC) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line.startswith('['):
                section = line.strip('[]')
                continue
            if section == 'volume':
                if '=' in line:
                    k, v = line.split('=', 1)
                    k = k.strip()
                    if k.startswith('vol_'):
                        vol_map[k] = int(v.strip())
    return vol_map


def load_pattern(path, aliases):
    info = {'bpm': 120, 'bars': 4, 'swing': 0}
    pattern = []
    section = None
    with open(path, encoding=ENC) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line.startswith('['):
                section = line.strip('[]')
                continue
            if section == 'info':
                if '=' in line:
                    k, v = line.split('=', 1)
                    k = k.strip()
                    v = v.strip()
                    if k in ('bpm', 'bars', 'swing'):
                        info[k] = int(v)
                    elif k.startswith('vol_'):
                        info[k] = int(v)
            elif section == 'pattern':
                if line:
                    step = parse_step(line, aliases)
                    pattern.append(step)
    return info, pattern


def parse_step(line, aliases):
    step = []
    for token in line.replace(',', ' ').split():
        token = token.strip()
        if not token or token == '.':
            continue
        if token in aliases:
            step.append(aliases[token])
        else:
            try:
                step.append(int(token))
            except ValueError:
                pass
    return step


def scan_patterns(pdir):
    files = sorted(f for f in os.listdir(pdir) if f.endswith('.ini'))
    return [(os.path.splitext(f)[0], os.path.join(pdir, f)) for f in files if os.path.isfile(os.path.join(pdir, f))]


def send(ser, addr, data):
    ser.write(bytes([0xC0, addr, data, 0xC0 ^ addr ^ data]))
    time.sleep(0.002)
    ser.read(1)


def hit(ser, ch, midi_note, midi_map):
    if midi_note not in midi_map:
        return
    drum_id, ratio = midi_map[midi_note]
    step = int(BASE_STEP[drum_id] * ratio)
    step = max(0x0020, step)
    send(ser, 0x27 + ch, (step >> 8) & 0xFF)
    send(ser, 0x2D + ch, step & 0xFF)
    send(ser, 0x15 + ch, drum_id)


def vol(ser, ch, v):
    send(ser, 0x21 + ch, v & 0x1F)


def off(ser, ch):
    send(ser, 0x1B + ch, 0)


VOL_KEYS = ['vol_bd', 'vol_sd', 'vol_cy', 'vol_hh', 'vol_tm', 'vol_rs']

def build_vol_map(global_vol, info):
    vol_map = {}
    for i, key in enumerate(VOL_KEYS):
        v = info.get(key, global_vol.get(key, 24))
        vol_map[i] = v
    return vol_map

def play_pattern(ser, pattern, bpm, bars, swing, midi_map, vol_map=None):
    step_dur = 60.0 / bpm / 4
    for bar in range(bars):
        for i, step in enumerate(pattern):
            for midi_note in step:
                if midi_note not in midi_map:
                    continue
                ch = midi_map[midi_note][0]
                if vol_map and ch in vol_map:
                    vol(ser, ch, vol_map[ch])
                hit(ser, ch, midi_note, midi_map)
            d = step_dur
            if swing > 0:
                sw = swing / 100.0
                if i % 2 == 0:
                    d *= (1 + sw)
                else:
                    d *= (1 - sw)
            time.sleep(d)
        if bar < bars - 1:
            time.sleep(step_dur * 0.25)


def main():
    if not os.path.exists(DRUM_INI):
        print(f"错误: 找不到 {DRUM_INI}")
        sys.exit(1)
    if not os.path.isdir(PATTERNS_DIR):
        print(f"错误: 找不到 {PATTERNS_DIR}")
        sys.exit(1)

    midi_map = load_map(DRUM_INI)
    aliases = load_aliases(DRUM_INI)
    global_vol = load_volume(DRUM_INI)
    patterns = scan_patterns(PATTERNS_DIR)

    if not patterns:
        print("错误: drum_patterns/ 下无 .ini 文件")
        sys.exit(1)

    if len(sys.argv) > 1 and sys.argv[1] == 'list':
        for name, path in patterns:
            info, _ = load_pattern(path, aliases)
            print(f"  {name}  BPM={info['bpm']}  bars={info['bars']}  swing={info['swing']}")
        print(f"\n共 {len(patterns)} 个风格, 用法: python adpcm_drumkit_pro.py [编号]")
        return

    idx = int(sys.argv[1]) if len(sys.argv) > 1 else -1
    targets = patterns if idx < 0 else [patterns[idx]] if idx < len(patterns) else []

    if not targets:
        print(f"错误: 编号 {idx} 超出范围 (0-{len(patterns)-1})")
        sys.exit(1)

    print(f"ADPCM 鼓机超级加强版 - {PORT} @ {BAUD}")
    print(f"映射: {len(midi_map)} MIDI鼓, 别名: {len(aliases)} 个")
    print(f"风格: {len(patterns)} 个")
    print()

    ser = serial.Serial(PORT, BAUD, timeout=0.1)
    time.sleep(0.1)
    ser.reset_input_buffer()

    for ch in range(6):
        vol(ser, ch, 24)

    for name, path in targets:
        info, pattern = load_pattern(path, aliases)
        vol_map = build_vol_map(global_vol, info)
        print(f">> {name}  BPM={info['bpm']}  bars={info['bars']}  swing={info['swing']}")
        if vol_map:
            names = {0:'BD',1:'SD',2:'CY',3:'HH',4:'TM',5:'RS'}
            vstr = ', '.join(f'{names[k]}={v}' for k,v in vol_map.items())
            print(f'   vol: {vstr}')
        play_pattern(ser, pattern, info['bpm'], info['bars'], info['swing'], midi_map, vol_map)
        time.sleep(0.5)

    for ch in range(6):
        off(ser, ch)

    print("\nDone!")
    ser.close()


if __name__ == "__main__":
    main()
