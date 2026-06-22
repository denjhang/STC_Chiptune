#!/usr/bin/env python3
"""
VGM 命令审计 (基于 libvgm 完整命令表).

扫描 VGM 文件用到的所有命令, 重点标出 NES APU 相关的 DAC 路径:
  - 0xB4 (NES 寄存器写, 含 $4011)
  - 0x67 type=0xC2 (NES CPU RAM write, DMC 采样)
  - 0x68 type=0x07 (PCM RAM write → NES)
  - 0x90-0x95 (DAC Stream Control)

用法: py -3 vgm_cmd_audit.py <vgm 文件>
"""
import sys, os, struct
from collections import Counter

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS_DIR)
import vgm_player as vp

# libvgm 命令参数长度表 (含 cmd 字节本身的总长度)
# 来源: vgmplayer_cmdhandler.cpp _CMD_INFO[0x100].paramLen
LIBVGM_CMD_LEN = [0] * 256
LIBVGM_CMD_LEN[0x30] = 2
LIBVGM_CMD_LEN[0x31] = 2
LIBVGM_CMD_LEN[0x32] = 2
for _i in range(0x33, 0x3F): LIBVGM_CMD_LEN[_i] = 2
LIBVGM_CMD_LEN[0x3F] = 2
LIBVGM_CMD_LEN[0x40] = 3
LIBVGM_CMD_LEN[0x41] = 3
LIBVGM_CMD_LEN[0x42] = 3
for _i in range(0x43, 0x4F): LIBVGM_CMD_LEN[_i] = 3
LIBVGM_CMD_LEN[0x4F] = 2
LIBVGM_CMD_LEN[0x50] = 2
for _i in range(0x51, 0x60): LIBVGM_CMD_LEN[_i] = 3
LIBVGM_CMD_LEN[0x61] = 3
LIBVGM_CMD_LEN[0x62] = 1
LIBVGM_CMD_LEN[0x63] = 1
LIBVGM_CMD_LEN[0x66] = 1
# 0x67 / 0x68 变长, 特殊处理
LIBVGM_CMD_LEN[0x68] = 0x0C  # PCM RAM write
for _i in range(0x70, 0x80): LIBVGM_CMD_LEN[_i] = 1
for _i in range(0x80, 0x90): LIBVGM_CMD_LEN[_i] = 1
LIBVGM_CMD_LEN[0x90] = 5
LIBVGM_CMD_LEN[0x91] = 5
LIBVGM_CMD_LEN[0x92] = 6
LIBVGM_CMD_LEN[0x93] = 0x0B
LIBVGM_CMD_LEN[0x94] = 2
LIBVGM_CMD_LEN[0x95] = 5
for _i in range(0xA0, 0xB0): LIBVGM_CMD_LEN[_i] = 3
for _i in range(0xB0, 0xC0): LIBVGM_CMD_LEN[_i] = 3
for _i in range(0xC0, 0xD0): LIBVGM_CMD_LEN[_i] = 4
for _i in range(0xD0, 0xD7): LIBVGM_CMD_LEN[_i] = 4
# 0xD7-0xDF = 4 (Cmd_unknown)
for _i in range(0xD7, 0xE0): LIBVGM_CMD_LEN[_i] = 4
LIBVGM_CMD_LEN[0xE0] = 5
LIBVGM_CMD_LEN[0xE1] = 5
for _i in range(0xE2, 0x100): LIBVGM_CMD_LEN[_i] = 5


def audit(filepath):
    data = vp.load_vgm(filepath)
    hdr = vp.parse_vgm_header(data)
    pos = hdr['data_offset']
    end = min(hdr['eof'], len(data))

    cmd_counter = Counter()
    nes_b4_reg_counter = Counter()
    datablock_types = Counter()
    dac_stream_cmds = []
    nes_reg11_count = 0
    nes_reg11_values = []
    pcm_ram_write_to_nes = 0
    nes_datablock_total_bytes = 0

    sample_count = 0
    cmd_count = 0

    while pos < end:
        b = data[pos]
        cmd_counter[b] += 1
        cmd_count += 1

        if b == 0x66:
            pos += 1
            break

        elif b == 0x67:
            # [0x67][0x66][type][size:4 LE][data...]
            if pos + 7 <= end:
                tp = data[pos + 2]
                sz = struct.unpack_from('<I', data, pos + 3)[0] & 0x7FFFFFFF
                datablock_types[tp] += 1
                if tp == 0xC2:
                    nes_datablock_total_bytes += (sz - 2) if sz >= 2 else 0
                pos += 7 + sz
            else:
                break

        elif b == 0x68:
            # PCM RAM write: [0x68][0x66][type][dbPos:3][wrtAddr:3][dataLen:3]
            if pos + 0x0C <= end:
                tp = data[pos + 2] & 0x7F
                if tp == 0x07:  # NES APU
                    pcm_ram_write_to_nes += 1
                pos += 0x0C
            else:
                break

        elif b == 0xB4:
            # NES APU register write
            if pos + 3 <= end:
                reg = data[pos + 1] & 0x7F  # bit7 = chipID
                val = data[pos + 2]
                nes_b4_reg_counter[reg] += 1
                if reg == 0x11:
                    nes_reg11_count += 1
                    if len(nes_reg11_values) < 20:
                        nes_reg11_values.append(val)
                pos += 3
            else:
                break

        elif b in (0x90, 0x91, 0x92, 0x93, 0x94, 0x95):
            # DAC Stream Control
            plen = LIBVGM_CMD_LEN[b]
            if b == 0x90 and pos + 5 <= end:
                stream_id = data[pos + 1]
                chip_type = data[pos + 2] & 0x7F
                chip_id = (data[pos + 2] >> 7) & 1
                cmd_hi = data[pos + 3]
                cmd_lo = data[pos + 4]
                dac_stream_cmds.append(('SETUP', stream_id, chip_type, chip_id, cmd_hi, cmd_lo))
            elif b == 0x95 and pos + 5 <= end:
                stream_id = data[pos + 1]
                snd_id = struct.unpack_from('<H', data, pos + 2)[0]
                flags = data[pos + 4]
                dac_stream_cmds.append(('PLAYBLK', stream_id, snd_id, flags))
            elif b == 0x92 and pos + 6 <= end:
                stream_id = data[pos + 1]
                freq = struct.unpack_from('<I', data, pos + 2)[0]
                dac_stream_cmds.append(('SETFREQ', stream_id, freq))
            elif b == 0x93 and pos + 0x0B <= end:
                stream_id = data[pos + 1]
                start_ofs = struct.unpack_from('<I', data, pos + 2)[0]
                pb_mode = data[pos + 6]
                sound_len = struct.unpack_from('<I', data, pos + 7)[0]
                dac_stream_cmds.append(('PLAYLOC', stream_id, start_ofs, pb_mode, sound_len))
            elif b == 0x94 and pos + 2 <= end:
                stream_id = data[pos + 1]
                dac_stream_cmds.append(('STOP', stream_id))
            pos += plen

        elif b == 0x61:
            if pos + 3 <= end:
                sample_count += struct.unpack_from('<H', data, pos + 1)[0]
                pos += 3
            else:
                break
        elif b == 0x62:
            sample_count += 735; pos += 1
        elif b == 0x63:
            sample_count += 882; pos += 1
        elif 0x70 <= b <= 0x7F:
            sample_count += (b & 0x0F) + 1; pos += 1
        elif 0x80 <= b <= 0x8F:
            sample_count += (b & 0x0F); pos += 1   # YM2612 PCM: wait n samples
        else:
            plen = LIBVGM_CMD_LEN[b]
            if plen == 0:
                plen = 1   # 防御
            pos += plen

    # 输出
    print(f"\n{'='*60}")
    print(f"=== {os.path.basename(filepath)} ===")
    print(f"{'='*60}")
    print(f"总命令数: {cmd_count}")
    print(f"总 sample: {sample_count} ({sample_count/44100:.1f}s)")

    print(f"\n--- 命令分布 (top 20) ---")
    for cmd, cnt in cmd_counter.most_common(20):
        print(f"  0x{cmd:02X}  {cnt:6d}")

    print(f"\n--- NES 0xB4 寄存器分布 ---")
    total_b4 = sum(nes_b4_reg_counter.values())
    reg_names = {
        0x00:'SQ1 duty/vol', 0x02:'SQ1 freqL', 0x03:'SQ1 len/freqH',
        0x04:'SQ2 duty/vol', 0x06:'SQ2 freqL', 0x07:'SQ2 len/freqH',
        0x08:'TRI linear', 0x0A:'TRI freqL', 0x0B:'TRI len/freqH',
        0x0C:'NOI vol', 0x0E:'NOI freq', 0x0F:'NOI len',
        0x10:'DMC rate', 0x11:'DMC DAC direct ($4011)',
        0x12:'DMC addr', 0x13:'DMC len', 0x15:'APU status',
    }
    if total_b4 == 0:
        print("  (无 0xB4 命令)")
    else:
        for reg in sorted(nes_b4_reg_counter.keys()):
            cnt = nes_b4_reg_counter[reg]
            pct = cnt * 100 / total_b4
            mark = '  <<< DAC' if reg == 0x11 else ''
            print(f"  ${reg:02X} {reg_names.get(reg, '?'):24s} {cnt:6d}  {pct:5.1f}%{mark}")

    print(f"\n--- 0x67 data block types ---")
    if not datablock_types:
        print("  (无 data block)")
    else:
        for tp, cnt in sorted(datablock_types.items()):
            extra = f'  [NES APU RAM, {nes_datablock_total_bytes} bytes]' if tp == 0xC2 else ''
            print(f"  type 0x{tp:02X}  count={cnt}{extra}")

    print(f"\n--- 0x68 PCM RAM write → NES ---")
    print(f"  count: {pcm_ram_write_to_nes}")

    print(f"\n--- 0x90-0x95 DAC Stream Control ---")
    if not dac_stream_cmds:
        print("  (无 DAC Stream 命令)")
    else:
        chip_names = {0x14:'NES APU', 0x02:'YM2612', 0x05:'RF5C68', 0x17:'OKIM6258'}
        for cmd in dac_stream_cmds[:30]:
            if cmd[0] == 'SETUP':
                _, sid, ct, ci, ch, cl = cmd
                cn = chip_names.get(ct, f'chipType={ct:#x}')
                print(f"  SETUP  stream={sid} chip={cn}(id={ci}) cmdHi=${ch:02X} cmdLo=${cl:02X}")
            elif cmd[0] == 'PLAYBLK':
                _, sid, snd, fl = cmd
                print(f"  PLAYBLK stream={sid} sndID={snd} flags=${fl:02X}")
            elif cmd[0] == 'SETFREQ':
                _, sid, fr = cmd
                print(f"  SETFREQ stream={sid} freq={fr} Hz")
            elif cmd[0] == 'PLAYLOC':
                _, sid, so, pm, sl = cmd
                print(f"  PLAYLOC stream={sid} startOfs={so} pbMode=${pm:02X} len={sl}")
            elif cmd[0] == 'STOP':
                _, sid = cmd
                print(f"  STOP   stream={sid}")
        if len(dac_stream_cmds) > 30:
            print(f"  ... 还有 {len(dac_stream_cmds)-30} 条")

    print(f"\n=== 结论 ===")
    paths = []
    if nes_reg11_count > 0: paths.append(f"0xB4 $4011 直接写 ({nes_reg11_count} 次)")
    if nes_datablock_total_bytes > 0: paths.append(f"0x67 type=0xC2 NES RAM ({nes_datablock_total_bytes} bytes)")
    if pcm_ram_write_to_nes > 0: paths.append(f"0x68 PCM RAM write → NES ({pcm_ram_write_to_nes})")
    if dac_stream_cmds: paths.append(f"0x90-0x95 DAC Stream ({len(dac_stream_cmds)})")
    if paths:
        print("  DAC/采样路径: " + " + ".join(paths))
    else:
        print("  ❗ 该曲无任何 DAC/采样路径, 纯合成音 (方波/三角/噪声)")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("usage: vgm_cmd_audit.py <vgm file>")
        sys.exit(1)
    audit(sys.argv[1])
