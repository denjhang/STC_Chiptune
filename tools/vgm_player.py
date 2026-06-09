#!/usr/bin/env python3
"""
VGM Player for STC Chiptune Synth (STC8H / STC32G)

Python 控制节拍: 解析 VGM, 芯片命令直接发串口, wait 用 time.sleep()
固件只做芯片写入, 不解析 wait

支持芯片: SCC, AY8910, SN76489, GB DMG, NES APU, SAA1099, FM (custom 2-op)

Usage:
  python vgm_player.py --list
  python vgm_player.py 1
  python vgm_player.py "02 Vampire Killer" --port COM3
  python vgm_player.py 3 --speed 0.5 --loop
  python vgm_player.py --dump 1
  python vgm_player.py --fm-note 0 60          # FM voice 0, MIDI C4
  python vgm_player.py --fm-off 0              # FM voice 0 off
  python vgm_player.py --fm-demo               # FM demo melody
"""

import argparse
import gzip
import glob
import os
import struct
import sys
import time

try:
    import serial
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False
    print("WARNING: pyserial not installed. pip install pyserial")

SAMPLES_PER_SEC = 44100


def load_vgm(filepath):
    with open(filepath, 'rb') as f:
        header = f.read(4)
    if header[:2] == b'\x1f\x8b':
        with gzip.open(filepath, 'rb') as f:
            return f.read()
    else:
        with open(filepath, 'rb') as f:
            return f.read()


def parse_vgm_header(data):
    if data[0:4] != b'Vgm ':
        raise ValueError("Not a VGM file")
    ver = struct.unpack_from('<I', data, 8)[0]
    eof = struct.unpack_from('<I', data, 4)[0] + 4
    data_off = struct.unpack_from('<I', data, 0x34)[0] + 0x34 if len(data) > 0x34 else 0x38
    if data_off == 0x34:
        data_off = 0x38
    loop_off = struct.unpack_from('<I', data, 0x1C)[0] + 0x1C if len(data) > 0x1C else 0
    loop_samples = struct.unpack_from('<I', data, 0x20)[0] if len(data) > 0x20 else 0
    total_samples = struct.unpack_from('<I', data, 0x18)[0] if len(data) > 0x18 else 0
    gd3_off = struct.unpack_from('<I', data, 0x14)[0] + 0x14 if len(data) > 0x14 else 0
    gd3 = ""
    if gd3_off and gd3_off < len(data):
        try:
            tag_len = struct.unpack_from('<I', data, gd3_off)[0]
            tag_data = data[gd3_off+4:gd3_off+4+tag_len]
            text = tag_data.decode('utf-16-le', errors='replace')
            fields = [f.strip('\x00') for f in text.split('\x00') if f.strip('\x00')]
            if len(fields) >= 4:
                gd3 = f"{fields[0]} - {fields[2]}"
        except Exception:
            pass
    # SN76489 变体检测 (header 0x0C=SN clock, 0x28=taps, 0x2A=SRWidth, 0x2B=flags)
    sn_variant = None
    sn_clock = struct.unpack_from('<I', data, 0x0C)[0] if len(data) > 0x0F else 0
    if sn_clock & 0x3FFFFFFF:  # SN76489 clock present
        sn_taps = struct.unpack_from('<H', data, 0x28)[0] if len(data) > 0x29 else 0
        sn_srw = data[0x2A] if len(data) > 0x2A else 0
        if not sn_srw:
            sn_srw = 16  # default Sega VDP
        if not sn_taps:
            sn_taps = 0x09  # default Sega VDP
        # 映射到固件变体: 0=SN76489(15bit), 1=SegaVDP(16bit), 2=SN76489A(17bit)
        if sn_srw <= 15 or sn_taps == 0x03:
            sn_variant = 0  # SN76489
        elif sn_srw >= 17:
            sn_variant = 2  # SN76489A
        else:
            sn_variant = 1  # Sega VDP (default)

    return {
        'version': ver, 'eof': eof, 'data_offset': data_off,
        'loop_offset': loop_off, 'loop_samples': loop_samples,
        'total_samples': total_samples, 'gd3': gd3,
        'sn_variant': sn_variant,
    }


def scan_vgm_stats(data, hdr):
    pos = hdr['data_offset']
    end = min(hdr['eof'], len(data))
    scc = ay = sn = gb = nes = saa = ym = wait = other = 0
    total_wait_samples = 0
    while pos < end:
        b = data[pos]
        if b == 0x66: break
        if b == 0xD2: scc += 1; pos += 4
        elif b == 0xA0: ay += 1; pos += 3
        elif b == 0x50: sn += 1; pos += 2
        elif b == 0x51: ym += 1; pos += 3
        elif b == 0xB3: gb += 1; pos += 3
        elif b == 0xB4: nes += 1; pos += 3
        elif b == 0xBD: saa += 1; pos += 3
        elif b == 0x61:
            if pos + 3 <= end:
                total_wait_samples += struct.unpack_from('<H', data, pos+1)[0]
            wait += 1; pos += 3
        elif b == 0x62: total_wait_samples += 735; wait += 1; pos += 1
        elif b == 0x63: total_wait_samples += 882; wait += 1; pos += 1
        elif 0x70 <= b <= 0x7F:
            total_wait_samples += (b & 0x0F) + 1; wait += 1; pos += 1
        elif 0x80 <= b <= 0x8F:
            total_wait_samples += (b & 0x0F) + 1; wait += 1; pos += 1
        elif 0x90 <= b <= 0x9F:
            total_wait_samples += (b & 0x0F) * 2 + 1; wait += 1; pos += 1
        else:
            other += 1; pos += 1
    duration = total_wait_samples / SAMPLES_PER_SEC
    return {'scc': scc, 'ay': ay, 'sn': sn, 'gb': gb, 'nes': nes, 'saa': saa, 'ym': ym,
            'wait': wait, 'other': other,
            'total_wait_samples': total_wait_samples, 'duration': duration}


def dump_vgm(data, hdr):
    pos = hdr['data_offset']
    end = min(hdr['eof'], len(data))
    count = 0
    while pos < end and count < 100:
        b = data[pos]
        if b == 0x66:
            print("  END"); break
        elif b == 0xD2 and pos + 4 <= end:
            print(f"  SCC  port={data[pos+1]:02X} reg={data[pos+2]:02X} data={data[pos+3]:02X}")
            pos += 4
        elif b == 0xA0 and pos + 3 <= end:
            print(f"  AY   reg={data[pos+1]:02X} data={data[pos+2]:02X}")
            pos += 3
        elif b == 0xB3 and pos + 3 <= end:
            print(f"  GB   reg={data[pos+1]:02X} data={data[pos+2]:02X}")
            pos += 3
        elif b == 0xB4 and pos + 3 <= end:
            print(f"  NES  reg={data[pos+1]:02X} data={data[pos+2]:02X}")
            pos += 3
        elif b == 0x51 and pos + 3 <= end:
            print(f"  YM   reg={data[pos+1]:02X} data={data[pos+2]:02X}")
            pos += 3
        elif b == 0xBD and pos + 3 <= end:
            print(f"  SAA  addr={data[pos+1]:02X} data={data[pos+2]:02X}")
            pos += 3
        elif b == 0x61 and pos + 3 <= end:
            n = struct.unpack_from('<H', data, pos+1)[0]
            print(f"  WAIT {n} samples")
            pos += 3
        elif b == 0x62:
            print("  WAIT 735 (60Hz)"); pos += 1
        elif b == 0x63:
            print("  WAIT 882 (50Hz)"); pos += 1
        elif 0x70 <= b <= 0x7F:
            print(f"  WAIT {(b&0xF)+1}"); pos += 1
        else:
            pos += 1
        count += 1


# VGM 命令长度表 (参考 RPFM vgm_player.h VGM_CMD_LEN)
VGM_CMD_LEN = [0]*256
VGM_CMD_LEN[0x20] = 3
for _i in range(0x30, 0x40): VGM_CMD_LEN[_i] = 4
VGM_CMD_LEN[0x4E] = 4; VGM_CMD_LEN[0x4F] = 4
VGM_CMD_LEN[0x50] = 2  # SN76489: 0x50 + 1 byte data
VGM_CMD_LEN[0x51] = 3  # YM2413: 0x51 + reg + data
VGM_CMD_LEN[0x52] = 2  # SN76489 variant select (custom)
VGM_CMD_LEN[0x61] = 3
VGM_CMD_LEN[0x62] = 1; VGM_CMD_LEN[0x63] = 1; VGM_CMD_LEN[0x66] = 1
for _i in range(0x70, 0x80): VGM_CMD_LEN[_i] = 1
for _i in range(0x80, 0x90): VGM_CMD_LEN[_i] = 1
for _i in range(0x90, 0xA0): VGM_CMD_LEN[_i] = 1
for _i in range(0xA0, 0xB0): VGM_CMD_LEN[_i] = 3
for _i in range(0xB0, 0xC0): VGM_CMD_LEN[_i] = 4
for _i in range(0xC0, 0xD0): VGM_CMD_LEN[_i] = 5
for _i in range(0xD0, 0xD4): VGM_CMD_LEN[_i] = 4
for _i in range(0xD4, 0xD8): VGM_CMD_LEN[_i] = 5
for _i in range(0xD8, 0xE0): VGM_CMD_LEN[_i] = 4
for _i in range(0xE0, 0xF0): VGM_CMD_LEN[_i] = 5
for _i in range(0xF0, 0x100): VGM_CMD_LEN[_i] = 5


def play_vgm(data, hdr, stats, ser, speed=1.0, loop=False):
    """
    Python 控制节拍 (perf_counter 累积模式):
    - perf_counter 记录实际流逝时间 → 转为 VGM samples budget
    - 每个 1ms Sleep 轮询一次, 累积 budget, 一次性处理所有命令
    - 避免 time.sleep() 累积误差
    """
    pos = hdr['data_offset']
    end = min(hdr['eof'], len(data))

    gd3_text = hdr['gd3'].encode('gbk', errors='replace').decode('gbk')
    print(f"  GD3: {gd3_text}")
    print(f"  Duration: {stats['duration']:.1f}s @44100Hz")
    print(f"  Data: {end - pos} bytes")
    print(f"  SCC:{stats['scc']} AY:{stats['ay']} SN:{stats['sn']} GB:{stats['gb']} NES:{stats['nes']} SAA:{stats['saa']} YM:{stats['ym']} Wait:{stats['wait']}")
    # SN76489 变体自动检测
    sn_var = hdr.get('sn_variant')
    sn_names = {0: 'SN76489(15bit)', 1: 'SegaVDP(16bit)', 2: 'SN76489A(17bit)'}
    if sn_var is not None:
        print(f"  SN variant: {sn_names.get(sn_var, '?')}")
        ser.write(bytes([0x52, sn_var]))
    print(f"  Speed: {speed:.1f}x" + (" [LOOP]" if loop else ""))
    print()

    last_time = time.perf_counter()
    samples_budget = 0.0  # 累积的 VGM samples budget
    current_samples = 0
    iteration = 0

    while True:
        # 1ms 轮询
        time.sleep(0.001)

        now = time.perf_counter()
        elapsed_sec = now - last_time
        last_time = now

        # 累积 budget (实际时间 → VGM samples)
        samples_budget += elapsed_sec * SAMPLES_PER_SEC * speed

        # 处理所有可以发送的命令
        while samples_budget >= 1.0 and pos < end:
            b = data[pos]
            pos += 1

            if b == 0x66:
                if loop and hdr['loop_offset'] > 0:
                    pos = hdr['loop_offset']
                    continue
                else:
                    pos = end
                    break

            elif b == 0x50:
                # SN76489: [0x50][data] - 直接透传
                if pos + 1 <= end:
                    ser.write(data[pos-1:pos+1])
                    pos += 1

            elif b == 0x51:
                # YM2413: [0x51][reg][data] - 直接透传
                if pos + 2 <= end:
                    ser.write(data[pos-1:pos+2])
                    pos += 2

            elif b == 0xA0:
                # AY8910: [0xA0][reg][data] - 直接透传
                if pos + 2 <= end:
                    ser.write(data[pos-1:pos+2])
                    pos += 2

            elif b == 0xB3:
                # GB DMG: [0xB3][reg][data] - 直接透传
                if pos + 2 <= end:
                    ser.write(data[pos-1:pos+2])
                    pos += 2

            elif b == 0xB4:
                # NES APU: [0xB4][reg][data] - 直接透传
                if pos + 2 <= end:
                    ser.write(data[pos-1:pos+2])
                    pos += 2

            elif b == 0xBD:
                # SAA1099: [0xBD][addr][data] - 直接透传
                if pos + 2 <= end:
                    ser.write(data[pos-1:pos+2])
                    pos += 2

            elif b == 0xD2:
                # SCC: [0xD2][port][reg][data] - 直接透传
                if pos + 3 <= end:
                    ser.write(data[pos-1:pos+3])
                    pos += 3

            elif b == 0x61:
                # Wait N samples
                if pos + 2 <= end:
                    n = struct.unpack_from('<H', data, pos)[0]
                    pos += 2
                    samples_budget -= n
                    current_samples += n

            elif b == 0x62:
                samples_budget -= 735
                current_samples += 735

            elif b == 0x63:
                samples_budget -= 882
                current_samples += 882

            elif 0x70 <= b <= 0x7F:
                n = (b & 0x0F) + 1
                samples_budget -= n
                current_samples += n

            elif 0x80 <= b <= 0x8F:
                n = (b & 0x0F) + 1
                samples_budget -= n
                current_samples += n

            elif 0x90 <= b <= 0x9F:
                n = (b & 0x0F) * 2 + 1
                samples_budget -= n
                current_samples += n

            elif b == 0x67:
                # Data block: skip
                if pos + 3 <= end:
                    sz = data[pos] | (data[pos+1] << 8) | (data[pos+2] << 16)
                    pos += 3 + sz
                else:
                    break

            else:
                # Unknown: skip by length
                skip = VGM_CMD_LEN[b]
                if skip > 1:
                    pos += skip - 1

        if pos >= end:
            break

    real_sec = current_samples / SAMPLES_PER_SEC / speed
    print(f"  [END] {real_sec:.1f}s")


def list_songs(vgm_dir):
    files = sorted(glob.glob(os.path.join(vgm_dir, '*.vgz')))
    files += sorted(glob.glob(os.path.join(vgm_dir, '*.vgm')))
    seen = set(); unique = []
    for f in files:
        name = os.path.basename(f)
        if name not in seen:
            seen.add(name); unique.append(f)
    if not unique:
        print(f"No .vgm/.vgz in {vgm_dir}/"); return
    print(f"\n{'#':>3}  {'File':<50} {'Size':>8}  {'Duration':>8}  {'Info'}")
    print("-" * 110)
    for i, f in enumerate(unique, 1):
        name = os.path.basename(f); size = os.path.getsize(f)
        try:
            d = load_vgm(f); h = parse_vgm_header(d); s = scan_vgm_stats(d, h)
            info = f"SCC:{s['scc']} PSG:{s['ay']} SN:{s['sn']} GB:{s['gb']} NES:{s['nes']} SAA:{s['saa']} YM:{s['ym']}"
            dur = f"{s['duration']:.1f}s"
        except Exception:
            info = "?"; dur = "?"
        print(f"{i:3}  {name:<50} {size:>8}  {dur:>8}  {info}")


def find_serial_port():
    if not HAS_SERIAL: return None
    import serial.tools.list_ports
    ports = serial.tools.list_ports.comports()
    for p in ports:
        if any(k in p.description.upper() for k in ['CH340','CH341','CP210','FT232','USB-SERIAL']):
            return p.device
    for p in ports:
        if 'USB' in p.description.upper(): return p.device
    if ports: return ports[0].device
    return None


def resolve_song(selector, vgm_dir):
    files = sorted(glob.glob(os.path.join(vgm_dir, '*.vgz')))
    files += sorted(glob.glob(os.path.join(vgm_dir, '*.vgm')))
    seen = set(); unique = []
    for f in files:
        name = os.path.basename(f)
        if name not in seen:
            seen.add(name); unique.append(f)
    try:
        idx = int(selector)
        if 1 <= idx <= len(unique): return unique[idx - 1]
    except ValueError: pass
    sel = selector.lower()
    for f in unique:
        if sel in os.path.basename(f).lower(): return f
    return None


# FM 波形名称
FM_WAVE_NAMES = ['tri', 'clipsin', 'rect', 'sin', 'saw', 'abssin']

def fm_send_note(ser, voice, note, duration_ms=300):
    """发送 FM Note On, 等待, Note Off (OPLL 分页模式)"""
    ser.write(bytes([0x51, 0x10 | (voice & 0x0F), note & 0x7F]))
    time.sleep(duration_ms / 1000.0)
    ser.write(bytes([0x51, 0x20 | (voice & 0x0F), 0]))
    time.sleep(0.05)

def fm_scale(ser):
    """FM 全音阶: 8 voice 轮流分配, 最多同时 3 音, 从 C1 到 C9"""
    print("\n  === FM Scale (C1-C9) ===")
    notes = list(range(24, 109))  # MIDI 24(C1) to 108(C8)
    notes.append(120)             # 加一个最高音 C9 测试
    vi = 0  # voice 轮转计数器
    active = []  # (voice, note)
    hold = 3     # 最多同时几音
    for note in notes:
        names = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
        oct = note // 12 - 1
        nm = names[note % 12]
        print(f"  voice{vi % 8}: {nm}{oct} (MIDI {note})")
        ser.write(bytes([0x51, 0x10 | (vi % 8), note & 0x7F]))
        active.append(vi % 8)
        vi += 1
        time.sleep(0.15)
        # 关闭超出的音
        while len(active) > hold:
            old_v = active.pop(0)
            ser.write(bytes([0x51, 0x20 | old_v, 0]))
            time.sleep(0.02)
    # 关闭所有剩余音
    time.sleep(0.3)
    for v in active:
        ser.write(bytes([0x51, 0x20 | v, 0]))
    time.sleep(0.1)
    print("  FM Scale done.")

def fm_demo(ser):
    """FM 演示: 和弦 + 音色切换 + 旋律"""
    print("\n  === FM Demo ===")

    # C4+E4+G4 三音和弦
    print("  C4 E4 G4 chord ...")
    ser.write(bytes([0x51, 0x10, 60]))
    ser.write(bytes([0x51, 0x11, 64]))
    ser.write(bytes([0x51, 0x12, 67]))
    time.sleep(1.0)
    for v in range(3):
        ser.write(bytes([0x51, 0x20 | v, 0]))
    time.sleep(0.1)

    # 波形演示 (改 carrier wave)
    print("  Wave sweep (carrier) ...")
    for wi, wname in enumerate(FM_WAVE_NAMES):
        print(f"    {wname}")
        ser.write(bytes([0x51, 0x09, wi]))
        ser.write(bytes([0x51, 0x10, 60]))
        time.sleep(0.5)
        ser.write(bytes([0x51, 0x20, 0]))
        time.sleep(0.1)

    # 旋律
    print("  Melody ...")
    melody = [60, 62, 64, 65, 67, 69, 71, 72, 71, 69, 67, 65, 64, 62, 60]
    for note in melody:
        ser.write(bytes([0x51, 0x10, note]))
        time.sleep(0.2)
    ser.write(bytes([0x51, 0x20, 0]))
    time.sleep(0.1)

    print("  FM Demo done.")


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    vgm_dir = os.path.join(script_dir, '..', 'vgm')

    parser = argparse.ArgumentParser(description='VGM Player for STC Chiptune Synth')
    parser.add_argument('song', nargs='?', help='Track number or name')
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--port', help='Serial port')
    parser.add_argument('--baud', type=int, default=115200)
    parser.add_argument('--speed', type=float, default=1.0)
    parser.add_argument('--loop', action='store_true')
    parser.add_argument('--dump', action='store_true')
    parser.add_argument('--vgm-dir', default=None)
    parser.add_argument('--fm-note', nargs=2, type=int, metavar=('VOICE', 'NOTE'),
                        help='FM Note On: voice(0-3) note(24-127)')
    parser.add_argument('--fm-off', type=int, metavar='VOICE',
                        help='FM Note Off: voice(0-3)')
    parser.add_argument('--fm-wave', nargs=2, type=int, metavar=('VOICE', 'WAVE'),
                        help='FM Set Carrier Wave: voice(0-3) wave(0-5)')
    parser.add_argument('--fm-demo', action='store_true',
                        help='FM demo melody')
    parser.add_argument('--fm-scale', action='store_true',
                        help='FM full scale test (C1-C9, 8 voices)')
    args = parser.parse_args()
    if args.vgm_dir: vgm_dir = args.vgm_dir

    # FM direct commands (no VGM needed)
    if args.fm_note is not None or args.fm_off is not None or args.fm_wave is not None or args.fm_demo or args.fm_scale:
        if not HAS_SERIAL:
            print("Error: pyserial required"); sys.exit(1)
        port = args.port or find_serial_port()
        if not port:
            print("Error: no serial port. --port COMx"); sys.exit(1)
        print(f"Serial: {port} @ {args.baud} baud")
        ser = serial.Serial(port, args.baud, timeout=0.1)
        time.sleep(0.1)
        ser.reset_input_buffer()
        try:
            if args.fm_note:
                voice, note = args.fm_note
                ser.write(bytes([0x51, 0x10 | (voice & 0x0F), note & 0x7F]))
                print(f"FM Note On: voice={voice} note={note}")
            if args.fm_off is not None:
                ser.write(bytes([0x51, 0x20 | (args.fm_off & 0x0F), 0]))
                print(f"FM Note Off: voice={args.fm_off}")
            if args.fm_wave:
                voice, wave = args.fm_wave
                ser.write(bytes([0x51, 0x09, wave & 0x07]))
                ser.write(bytes([0x51, 0x08, wave & 0x07]))
                print(f"FM Set Wave: voice={voice} wave={wave}")
            if args.fm_demo:
                fm_demo(ser)
            if args.fm_scale:
                fm_scale(ser)
        except Exception as e:
            print(f"Error: {e}")
        finally:
            ser.close()
        return

    if args.list:
        list_songs(vgm_dir); return
    if not args.song:
        parser.print_help(); sys.exit(1)

    filepath = resolve_song(args.song, vgm_dir)
    if not filepath:
        print(f"Song not found: '{args.song}'"); sys.exit(1)

    print(f"Loading: {os.path.basename(filepath)}")
    data = load_vgm(filepath)
    hdr = parse_vgm_header(data)
    stats = scan_vgm_stats(data, hdr)

    if args.dump:
        dump_vgm(data, hdr); return

    if not HAS_SERIAL:
        print("Error: pyserial required"); sys.exit(1)

    port = args.port or find_serial_port()
    if not port:
        print("Error: no serial port. --port COMx"); sys.exit(1)
    print(f"Serial: {port} @ {args.baud} baud")

    try:
        ser = serial.Serial(port, args.baud, timeout=0.1)
        time.sleep(0.1)
        ser.reset_input_buffer()
    except Exception as e:
        print(f"Error: {e}"); sys.exit(1)

    try:
        play_vgm(data, hdr, stats, ser=ser, speed=args.speed, loop=args.loop)
    except KeyboardInterrupt:
        print("\n  Stopped.")
    finally:
        # 复位 SCC 寄存器：静音所有通道
        scc_reset = bytes([0xD2, 0x00, 0x03, 0x00])  # keyon = 0
        ser.write(scc_reset)
        time.sleep(0.01)
        ser.close()


if __name__ == '__main__':
    main()
