#!/usr/bin/env python3
"""
VGM Player for STC8H SCC Synth

Parse VGM/VGZ files and stream commands over UART to STC8H8K64U.

VGM 命令直接透传，固件自行解析:
  0xD2 = SCC  [0xD2][port][reg][data]  → 固件展开 scc_wr(port<<1, reg) + scc_wr(port<<1|1, data)
  0xA0 = AY   [0xA0][reg][data]       → 固件预留
  0x61 = Wait N samples (2 bytes)
  0x62 = Wait 735 samples (44100/60)
  0x63 = Wait 882 samples (44100/50)
  0x70-7F = Short wait (n&0xF)+1 samples
  0x80-8F = Short wait (n&0xF)+1 samples
  0x90-9F = Short wait (n&0xF)*2+1 samples
  0x66 = End

  自定义协议:
  0xFF [ticks] = Wait N main-loop ticks
  0xFE = 关闭测试播放
  0xFD = 开启测试播放

Usage:
  python vgm_player.py --list
  python vgm_player.py 1
  python vgm_player.py "02 Vampire Killer"
  python vgm_player.py 1 --port COM3 --baud 230400
  python vgm_player.py --loop 1
  python vgm_player.py --dump 1
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
    print("WARNING: pyserial not installed. Use --dump mode or pip install pyserial")

# VGM 命令长度表 (参考 RPFM ay8910_window.cpp)
VGM_CMD_LEN = [0] * 256
# 0x20: AY8910 write = 3 bytes (legacy, 0xA0 is newer)
VGM_CMD_LEN[0x20] = 3
# 0x30-0x3F: YM2203/YM2608 port writes = 4 bytes
for i in range(0x30, 0x40): VGM_CMD_LEN[i] = 4
# 0x4E-0x4F: YM2413 = 4
VGM_CMD_LEN[0x4E] = 4; VGM_CMD_LEN[0x4F] = 4
# 0x50-0x5F: YM2608/YM2610 = 4
for i in range(0x50, 0x60): VGM_CMD_LEN[i] = 4
# 0x61: wait N = 3
VGM_CMD_LEN[0x61] = 3
# 0x62-0x63: wait frame = 1
VGM_CMD_LEN[0x62] = 1; VGM_CMD_LEN[0x63] = 1
# 0x66: end = 1
VGM_CMD_LEN[0x66] = 1
# 0x67: data block = variable (skip)
# 0x68-0x6F: reserved
# 0x70-0x7F: short wait = 1
for i in range(0x70, 0x80): VGM_CMD_LEN[i] = 1
# 0x80-0x8F: short wait = 1
for i in range(0x80, 0x90): VGM_CMD_LEN[i] = 1
# 0x90-0x9F: short wait = 1
for i in range(0x90, 0xA0): VGM_CMD_LEN[i] = 1
# 0xA0-0xAF: AY8910 = 3
for i in range(0xA0, 0xB0): VGM_CMD_LEN[i] = 3
# 0xB0-0xBF: YM2612 = 4
for i in range(0xB0, 0xC0): VGM_CMD_LEN[i] = 4
# 0xC0-0xCF: YM2608 = 4
for i in range(0xC0, 0xD0): VGM_CMD_LEN[i] = 4
# 0xD0-0xDF: various port writes = 4-5
for i in range(0xD0, 0xD4): VGM_CMD_LEN[i] = 4
for i in range(0xD4, 0xD8): VGM_CMD_LEN[i] = 5
for i in range(0xD8, 0xE0): VGM_CMD_LEN[i] = 4
# 0xD2: SCC = 4 bytes [D2][port][reg][data]
VGM_CMD_LEN[0xD2] = 4
# 0xE0: reserved
# default = 1 (skip single byte)


def load_vgm(filepath):
    """Load VGM or VGZ file, return raw bytes."""
    with open(filepath, 'rb') as f:
        header = f.read(4)
    if header[:2] == b'\x1f\x8b':
        with gzip.open(filepath, 'rb') as f:
            return f.read()
    else:
        with open(filepath, 'rb') as f:
            return f.read()


def parse_vgm_header(data):
    """Parse VGM header, return dict with offsets."""
    if data[0:4] != b'Vgm ':
        raise ValueError("Not a VGM file")
    ver = struct.unpack_from('<I', data, 8)[0]
    eof = struct.unpack_from('<I', data, 4)[0] + 4
    data_off = struct.unpack_from('<I', data, 0x34)[0] + 0x34 if len(data) > 0x34 else 0x38
    if data_off == 0x34:
        data_off = 0x38
    loop_off = struct.unpack_from('<I', data, 0x1C)[0] + 0x1C if len(data) > 0x1C else 0
    loop_samples = struct.unpack_from('<I', data, 0x20)[0] if len(data) > 0x20 else 0
    # GD3 tag
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
    return {
        'version': ver,
        'eof': eof,
        'data_offset': data_off,
        'loop_offset': loop_off,
        'loop_samples': loop_samples,
        'gd3': gd3,
    }


def samples_to_ticks(n_samples, target_rate=16000, source_rate=44100):
    """Convert VGM sample count to main-loop ticks."""
    return max(1, n_samples * target_rate // source_rate)


def scan_vgm(data, hdr):
    """Scan VGM commands, return (commands, stats)."""
    pos = hdr['data_offset']
    end = min(hdr['eof'], len(data))
    cmds = []       # (type, raw_bytes)
    scc = ay = wait = other = 0

    while pos < end:
        b = data[pos]
        if b == 0x66:
            cmds.append(('end', bytes([0x66])))
            break
        elif b == 0xD2:
            # SCC: [D2][port][reg][data] = 4 bytes, 透传
            if pos + 4 <= end:
                cmds.append(('scc', data[pos:pos+4]))
                scc += 1
                pos += 4
            else:
                break
        elif b == 0xA0:
            # AY: [A0][reg][data] = 3 bytes, 透传
            if pos + 3 <= end:
                cmds.append(('ay', data[pos:pos+3]))
                ay += 1
                pos += 3
            else:
                break
        elif b == 0x61:
            # Wait N samples
            if pos + 3 <= end:
                n = struct.unpack_from('<H', data, pos+1)[0]
                ticks = samples_to_ticks(n)
                cmds.append(('wait', ticks))
                wait += 1
                pos += 3
            else:
                break
        elif b == 0x62:
            cmds.append(('wait', samples_to_ticks(735)))
            wait += 1; pos += 1
        elif b == 0x63:
            cmds.append(('wait', samples_to_ticks(882)))
            wait += 1; pos += 1
        elif 0x70 <= b <= 0x7F:
            n = (b & 0x0F) + 1
            cmds.append(('wait', samples_to_ticks(n)))
            wait += 1; pos += 1
        elif 0x80 <= b <= 0x8F:
            n = (b & 0x0F) + 1
            cmds.append(('wait', samples_to_ticks(n)))
            wait += 1; pos += 1
        elif 0x90 <= b <= 0x9F:
            n = (b & 0x0F) * 2 + 1
            cmds.append(('wait', samples_to_ticks(n)))
            wait += 1; pos += 1
        else:
            # Unknown command, skip
            skip = VGM_CMD_LEN[b]
            if skip <= 0:
                skip = 1
            pos += skip
            other += 1

    return cmds, {'scc': scc, 'ay': ay, 'wait': wait, 'other': other}


# ── Protocol bytes ──

PROTO_STOP_TEST = 0xFE
PROTO_PLAY_TEST = 0xFD
PROTO_WAIT      = 0xFF


def play_vgm(cmds, stats, ser=None, speed=1.0, loop=False):
    """Stream VGM commands over UART."""
    if ser:
        ser.write(bytes([PROTO_STOP_TEST]))
        time.sleep(0.05)

    print(f"  GD3: {stats.get('gd3', '')}")
    print(f"  SCC:{stats['scc']} AY:{stats['ay']} Wait:{stats['wait']} Other(skipped):{stats['other']}")
    print(f"  Speed: {speed:.1f}x" + (" [LOOP]" if loop else ""))
    print()

    buf = bytearray()
    buf.append(PROTO_STOP_TEST)

    iteration = 0
    while True:
        for ctype, cdata in cmds:
            if ctype == 'end':
                if loop:
                    buf.append(PROTO_WAIT)
                    buf.append(120)
                    break
                else:
                    if ser:
                        _flush(ser, buf, speed)
                    print("  [END]")
                    return

            elif ctype in ('scc', 'ay'):
                buf.extend(cdata)

            elif ctype == 'wait':
                n = max(1, int(cdata / speed)) if speed != 1.0 else cdata
                while n > 0:
                    chunk = min(n, 254)
                    buf.append(PROTO_WAIT)
                    buf.append(chunk)
                    n -= chunk

            # Flush when buffer gets big
            if len(buf) >= 64 and ser:
                _flush(ser, buf, speed)
                buf = bytearray()

        if not loop:
            break
        iteration += 1
        print(f"  [Loop #{iteration}]")

    if ser and buf:
        _flush(ser, buf, speed)
    if ser:
        print("  Done.")


def _flush(ser, buf, speed):
    if not buf:
        return
    ser.write(bytes(buf))
    # Calculate wait ticks in this batch
    wait_ticks = 0
    i = 0
    while i < len(buf):
        if buf[i] == PROTO_WAIT and i + 1 < len(buf):
            wait_ticks += buf[i + 1]
            i += 2
        elif buf[i] in (0xD2,):
            i += 4  # SCC = 4 bytes
        elif buf[i] in (0xA0,):
            i += 3  # AY = 3 bytes
        else:
            i += 1
    # Main-loop tick ≈ 0.15ms at 45MHz with delay(1)
    sleep_time = wait_ticks * 0.00015 / speed
    if sleep_time > 0.01:
        time.sleep(sleep_time)
    elif sleep_time > 0:
        time.sleep(0.002)


def dump_vgm(cmds, stats):
    """Dump commands for debugging."""
    print(f"  SCC:{stats['scc']} AY:{stats['ay']} Wait:{stats['wait']}")
    for ctype, cdata in cmds:
        if ctype == 'scc':
            print(f"  SCC  port={cdata[1]:02X} reg={cdata[2]:02X} data={cdata[3]:02X}")
        elif ctype == 'ay':
            print(f"  AY   reg={cdata[1]:02X} data={cdata[2]:02X}")
        elif ctype == 'wait':
            print(f"  WAIT {cdata} ticks")
        elif ctype == 'end':
            print(f"  END")
            break


# ── Song listing ──

def list_songs(vgm_dir):
    files = sorted(glob.glob(os.path.join(vgm_dir, '*.vgz')))
    files += sorted(glob.glob(os.path.join(vgm_dir, '*.vgm')))
    seen = set()
    unique = []
    for f in files:
        name = os.path.basename(f)
        if name not in seen:
            seen.add(name)
            unique.append(f)
    if not unique:
        print(f"No .vgm/.vgz found in {vgm_dir}/")
        return
    print(f"\n{'#':>3}  {'File':<50} {'Size':>8}  {'Info'}")
    print("-" * 90)
    for i, f in enumerate(unique, 1):
        name = os.path.basename(f)
        size = os.path.getsize(f)
        try:
            data = load_vgm(f)
            hdr = parse_vgm_header(data)
            cmds, st = scan_vgm(data, hdr)
            info = f"SCC:{st['scc']} PSG:{st['ay']}"
        except Exception:
            info = "?"
        print(f"{i:3}  {name:<50} {size:>8}  {info}")


def find_serial_port():
    if not HAS_SERIAL:
        return None
    import serial.tools.list_ports
    ports = serial.tools.list_ports.comports()
    for p in ports:
        if any(k in p.description.upper() for k in ['CH340','CH341','CP210','FT232','USB-SERIAL']):
            return p.device
    for p in ports:
        if 'USB' in p.description.upper():
            return p.device
    if ports:
        return ports[0].device
    return None


def resolve_song(selector, vgm_dir):
    files = sorted(glob.glob(os.path.join(vgm_dir, '*.vgz')))
    files += sorted(glob.glob(os.path.join(vgm_dir, '*.vgm')))
    seen = set()
    unique = []
    for f in files:
        name = os.path.basename(f)
        if name not in seen:
            seen.add(name)
            unique.append(f)
    try:
        idx = int(selector)
        if 1 <= idx <= len(unique):
            return unique[idx - 1]
    except ValueError:
        pass
    sel = selector.lower()
    for f in unique:
        if sel in os.path.basename(f).lower():
            return f
    return None


# ── Main ──

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    vgm_dir = os.path.join(script_dir, '..', 'vgm')

    parser = argparse.ArgumentParser(
        description='VGM Player for STC8H SCC Synth',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python vgm_player.py --list
  python vgm_player.py 1
  python vgm_player.py "02 Vampire Killer" --port COM3
  python vgm_player.py 3 --speed 0.5 --loop
  python vgm_player.py --dump 1
        """)
    parser.add_argument('song', nargs='?', help='Track number or name')
    parser.add_argument('--list', action='store_true', help='List songs')
    parser.add_argument('--port', help='Serial port')
    parser.add_argument('--baud', type=int, default=230400, help='Baud rate (default 230400)')
    parser.add_argument('--speed', type=float, default=1.0, help='Speed (default 1.0)')
    parser.add_argument('--loop', action='store_true', help='Loop playback')
    parser.add_argument('--dump', action='store_true', help='Dump commands to stdout')
    parser.add_argument('--vgm-dir', default=None, help='VGM directory')

    args = parser.parse_args()
    if args.vgm_dir:
        vgm_dir = args.vgm_dir

    if args.list:
        list_songs(vgm_dir)
        return

    if not args.song:
        parser.print_help()
        print("\nError: specify a song or --list")
        sys.exit(1)

    filepath = resolve_song(args.song, vgm_dir)
    if not filepath:
        print(f"Song not found: '{args.song}'")
        sys.exit(1)

    print(f"Loading: {os.path.basename(filepath)}")
    data = load_vgm(filepath)
    hdr = parse_vgm_header(data)
    cmds, stats = scan_vgm(data, hdr)

    if args.dump:
        dump_vgm(cmds, stats)
        return

    if not HAS_SERIAL:
        print("Error: pyserial required. pip install pyserial")
        sys.exit(1)

    port = args.port or find_serial_port()
    if not port:
        print("Error: no serial port found. Use --port COMx")
        sys.exit(1)
    print(f"Serial: {port} @ {args.baud} baud")

    try:
        ser = serial.Serial(port, args.baud, timeout=0.1)
        time.sleep(0.1)
        ser.reset_input_buffer()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    try:
        play_vgm(cmds, stats, ser=ser, speed=args.speed, loop=args.loop)
    except KeyboardInterrupt:
        print("\n  Stopped.")
    finally:
        ser.write(bytes([PROTO_PLAY_TEST]))
        ser.close()


if __name__ == '__main__':
    main()
