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
  python vgm_player.py --wt-scale              # WT full scale test
"""

import argparse
import gzip
import glob
import os
import re
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

ACK_OK = 0xAA
ACK_ERR = 0xFF


def fmt_bytes(n):
    """字节数格式化: <1024 用 B, 否则 KB 保留 1 位小数"""
    if n < 1024:
        return f"{n}B"
    return f"{n/1024:.1f}KB"


def progress_bar(cur, total, width=24):
    """生成 ASCII 进度条: [████████████░░░░░░░░░░] 50%"""
    if total <= 0:
        return '[' + ' ' * width + '] 0%'
    pct = min(cur / total, 1.0)
    filled = int(pct * width)
    bar = '█' * filled + '░' * (width - filled)
    return f'[{bar}] {pct*100:3.0f}%'


def dmc_send_block(ser, addr, payload):
    """把一个 DMC 块分片发到 MCU (0xB6 命令). 每 512B yield 1ms 防 RX 溢出."""
    o = 0
    while o < len(payload):
        chunk = payload[o: o + 32]
        ser.write(bytes([0xB6, addr & 0xFF, (addr >> 8) & 0xFF, len(chunk)]) + bytes(chunk))
        o += len(chunk)
        addr += len(chunk)
        if o % 512 == 0:
            time.sleep(0.001)


def uart_send(ser, data, ack=True):
    """发送带 XOR 校验的命令包
    ack=True: 等待 ACK, 超时重发 (最多3次), 用于 FM/直接命令
    ack=False: 不等 ACK, 下位机校验错则丢弃, 用于 VGM 流
    """
    chk = 0
    for b in data:
        chk ^= b
    pkt = bytes(list(data) + [chk])
    if not ack:
        ser.write(pkt)
        return True
    for retry in range(3):
        ser.write(pkt)
        resp = ser.read(1)
        if resp and resp[0] == ACK_OK:
            return True
    return False


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
    # GD3 标签 10 字段 (VGM spec):
    # 0/1 = 曲名英/日, 2/3 = 游戏名英/日, 4/5 = 系统名英/日,
    # 6/7 = 作者英/日, 8 = 发布日期, 9 = VGM 作者(ripper)
    # GD3 tag (对齐 libvgm vgmplayer.cpp GetTagData, line 428-467):
    #   [magic 'Gd3 '][version u32][tag_len u32][utf16le 字段数据]
    #   字段用 UTF-16 \0 分隔, 共 11 个 (libvgm _TAG_COUNT=11):
    #     0/1 TITLE/TITLE-JPN, 2/3 GAME/GAME-JPN, 4/5 SYSTEM/SYSTEM-JPN,
    #     6/7 ARTIST/ARTIST-JPN, 8 DATE, 9 ENCODED_BY (ripper), 10 COMMENT
    gd3 = {'title_en': '', 'title_jp': '', 'game_en': '', 'game_jp': '',
           'system_en': '', 'system_jp': '', 'author_en': '', 'author_jp': '',
           'date': '', 'vgm_author': '', 'comment': '', 'raw': []}
    if gd3_off and gd3_off + 12 <= len(data):
        try:
            magic = data[gd3_off:gd3_off+4]
            if magic == b'Gd3 ':
                tag_ver = struct.unpack_from('<I', data, gd3_off+4)[0]
                # libvgm 要求 0x100 <= ver < 0x200, 否则视为坏 tag
                if 0x100 <= tag_ver < 0x200:
                    tag_len = struct.unpack_from('<I', data, gd3_off+8)[0]
                    tag_data = data[gd3_off+12:gd3_off+12+tag_len]
                    text = tag_data.decode('utf-16-le', errors='replace')
                    # 不能过滤空字段 — jp 字段经常空, 过滤会导致索引错位
                    fields = text.split('\x00')
                    while fields and not fields[-1]:
                        fields.pop()
                    gd3['raw'] = fields
                    keys = ['title_en','title_jp','game_en','game_jp','system_en','system_jp',
                            'author_en','author_jp','date','vgm_author','comment']
                    for i, f in enumerate(fields[:11]):
                        gd3[keys[i]] = f.strip('\x00')
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

    # NES APU 时钟 (header 0x84, vgm 1.60+), bit31=逆位, 低位为实际 Hz.
    # 不再强制默认 NTSC — clock=0 表示该 VGM 不含 NES 音源, 显示时按命令统计过滤.
    # NTSC=1789773, PAL=1662607, 部分野 VGM 用 1652098
    nes_clock = 0
    if ver >= 0x160 and len(data) > 0x87:
        nes_clock = struct.unpack_from('<I', data, 0x84)[0] & 0x7FFFFFFF

    # GB DMG 时钟 (header 0x80, vgm 1.61+). DMG 固定 4194304 Hz.
    gb_clock = 0
    if ver >= 0x161 and len(data) > 0x83:
        gb_clock = struct.unpack_from('<I', data, 0x80)[0] & 0x7FFFFFFF

    # AY8910/YM2149 时钟 + chipFlags (对齐 libvgm _CHIPCLK_OFS + ayintf.h):
    #   v1.50: clock @0x40 (AY8910 是第 6 个芯片)
    #   v1.70: clock @0x74 (芯片列表重排, AY8910 索引 18)
    #   chipType  @0x78 (0x10=YM2149, 0x00=AY-3-8910)
    #   chipFlags @0x79, bit4 (0x10) = YM2149_PIN26_LOW = 内置 /2 分频器 (clock 减半, 低八度)
    #     (注意: 是 bit4=0x10, 不是 bit0! bit0 是 AY8910_CHNTYPE 等, 见 ayintf.h)
    # 两处都试, 取非零值. chipFlags 只在 header 长度够时读.
    ay_clock = 0
    if len(data) > 0x43:
        ay_clock = struct.unpack_from('<I', data, 0x40)[0] & 0x7FFFFFFF   # v1.50 偏移
    if ay_clock == 0 and len(data) > 0x77:
        ay_clock = struct.unpack_from('<I', data, 0x74)[0] & 0x7FFFFFFF   # v1.70 偏移
    ay_chiptype = data[0x78] if len(data) > 0x78 else 0x00
    ay_chipflags = data[0x79] if len(data) > 0x79 else 0x00
    # chipFlags bit4 (YM2149_PIN26_LOW=0x10) = /2 分频器, 实际 clock = clock / 2
    ay_effective_clock = ay_clock // 2 if (ay_chipflags & 0x10) else ay_clock

    # 扫 0x67 data block, 提取 type=0xC2 NES APU RAM write 的 DMC 采样数据
    # 格式: [0x67][0x66][0xC2][size:4][addr_lo][addr_hi][data...]
    # addr 是 NES CPU 地址 ($C000+), data 是采样字节
    nes_dmc_blocks = []  # list of (cpu_addr, bytes)
    scan_pos = data_off
    while scan_pos < eof and scan_pos + 7 < len(data):
        b = data[scan_pos]
        if b == 0x66: break
        if b == 0x67:
            second = data[scan_pos + 1]  # 固定 0x66
            tp = data[scan_pos + 2]
            sz = struct.unpack_from('<I', data, scan_pos + 3)[0]
            chip_id_bit = (sz >> 31) & 1
            sz &= 0x7FFFFFFF
            if tp == 0xC2 and sz >= 2 and scan_pos + 7 + sz <= len(data):
                ram_addr = struct.unpack_from('<H', data, scan_pos + 7)[0]
                payload = data[scan_pos + 9: scan_pos + 7 + sz]
                nes_dmc_blocks.append((ram_addr, payload))
            scan_pos += 7 + sz
        elif b in (0xA0, 0x51, 0xB3, 0xB4, 0xBD, 0x52): scan_pos += 3
        elif b == 0x50: scan_pos += 2
        elif b == 0xD2: scan_pos += 4
        elif b == 0x61: scan_pos += 3
        elif b in (0x62, 0x63): scan_pos += 1
        elif 0x70 <= b <= 0x9F: scan_pos += 1
        else: scan_pos += 1

    return {
        'version': ver, 'eof': eof, 'data_offset': data_off,
        'loop_offset': loop_off, 'loop_samples': loop_samples,
        'total_samples': total_samples, 'gd3': gd3,
        'sn_variant': sn_variant, 'nes_clock': nes_clock, 'gb_clock': gb_clock,
        'ay_clock': ay_clock, 'ay_chiptype': ay_chiptype, 'ay_chipflags': ay_chipflags,
        'ay_effective_clock': ay_effective_clock,
        'nes_dmc_blocks': nes_dmc_blocks,
    }


def scan_vgm_stats(data, hdr):
    pos = hdr['data_offset']
    end = min(hdr['eof'], len(data))
    scc = ay = sn = gb = nes = saa = ym = wait = other = 0
    total_wait_samples = 0
    while pos < end:
        b = data[pos]
        if b == 0x66: break
        if b == 0x67:
            # [0x67][0x66][type][size:4 LE][data]
            if pos + 7 <= end:
                sz = struct.unpack_from('<I', data, pos + 3)[0]
                pos += 7 + sz
            else:
                break
            continue
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


def play_vgm(data, hdr, stats, ser, speed=1.0, loop=0, allow_interrupt=False):
    global _kb_cmd
    """
    loop: 循环次数
      0 = 不循环 (播完一次即停)
      1+ = 循环 N 次 (即总共播 N+1 遍, 第一遍后还要 N 遍 loop 段)
    allow_interrupt: True 时检查全局 _kb_cmd, 收到 n/b/q 返回 ('next'/'back'/'quit')
    返回值: None (正常播完) 或 'next'/'back'/'quit' (被中断)
    """
    """
    Python 控制节拍 (perf_counter 累积模式):
    - perf_counter 记录实际流逝时间 → 转为 VGM samples budget
    - 每个 1ms Sleep 轮询一次, 累积 budget, 一次性处理所有命令
    - 避免 time.sleep() 累积误差
    """
    pos = hdr['data_offset']
    end = min(hdr['eof'], len(data))

    # 开播前复位所有音源芯片: 清除上一首残留的相位/步进/cycles_left/lfsr 状态.
    # 必须发, 否则单曲模式第二次播放时下位机 GB 带着脏状态 (wave/noise cycles_left 残留),
    # 第一组 trigger 命令进来后循环爆 guard → ISR 超时 → 卡死.
    # playlist 模式 mute_all_chips 已发, 这里再发一次幂等无害.
    ser.write(bytes([0xF0]))
    time.sleep(0.02)

    # GD3 完整显示 (英文优先, 日文做 fallback)
    gd3 = hdr['gd3']
    def gbk(s):
        return s.encode('gbk', errors='replace').decode('gbk')
    def pick(en, jp):
        return en or jp or ''
    title = pick(gd3.get('title_en'), gd3.get('title_jp'))
    game = pick(gd3.get('game_en'), gd3.get('game_jp'))
    system = pick(gd3.get('system_en'), gd3.get('system_jp'))
    author = pick(gd3.get('author_en'), gd3.get('author_jp'))
    date = gd3.get('date', '')
    vgm_author = gd3.get('vgm_author', '')
    # GD3 第 11 字段 COMMENT (注释/备注, 如 gbs2vgm 转换信息)
    comment = gd3.get('comment', '')
    if title or game:
        line = f"  Track: {gbk(title)}" if title else "  Track:"
        if game: line += f"  [{gbk(game)}]"
        print(line)
    if system:
        print(f"  System: {gbk(system)}")
    if author:
        print(f"  Author: {gbk(author)}")
    if date:        print(f"  Date: {date}")
    if vgm_author:  print(f"  Rip: {gbk(vgm_author)}")
    if comment:     print(f"  Comment: {gbk(comment)}")
    print(f"  Duration: {stats['duration']:.1f}s @44100Hz  (data {end - pos} bytes)")
    print(f"  CMD: SCC:{stats['scc']} AY:{stats['ay']} SN:{stats['sn']} GB:{stats['gb']} NES:{stats['nes']} SAA:{stats['saa']} YM:{stats['ym']} Wait:{stats['wait']}")
    # SN76489 变体自动检测 (仅当有 SN 命令时)
    sn_var = hdr.get('sn_variant')
    sn_names = {0: 'SN76489(15bit)', 1: 'SegaVDP(16bit)', 2: 'SN76489A(17bit)'}
    if sn_var is not None and stats['sn'] > 0:
        print(f"  SN variant: {sn_names.get(sn_var, '?')}")
        ser.write(bytes([0x52, sn_var]))
    # NES APU 时钟下发 (仅当有 NES 命令时, 避免对纯 GB/AY 曲发无关 NES clock)
    nes_clk = hdr.get('nes_clock') or 0
    if stats['nes'] > 0:
        if nes_clk == 0: nes_clk = 1789773   # 无 header clock, 默认 NTSC
        region = 'NTSC' if nes_clk > 1700000 else 'PAL'
        print(f"  NES clock: {nes_clk} Hz ({region})")
        ser.write(bytes([0xB5]) + struct.pack('<I', nes_clk))
    # AY8910/YM2149 时钟下发 (仅当有 AY 命令时).
    # chipFlags bit0=1 (YM2149 /2 分频器) 时实际 clock 减半, 下发 effective_clock.
    # Gimmick: YM2149 clock=1789773 + chipFlags=0x11 (bit0=1) → 下发 894886 (低八度).
    ay_raw = hdr.get('ay_clock') or 0
    ay_eff = hdr.get('ay_effective_clock') or 0
    ay_cf = hdr.get('ay_chipflags') or 0
    ay_ct = hdr.get('ay_chiptype') or 0
    if stats['ay'] > 0 and ay_eff > 0:
        chiptype_name = {0x00:'AY-3-8910', 0x10:'YM2149'}.get(ay_ct, f'AY-type({ay_ct:#x})')
        div_note = ' /2 divider' if (ay_cf & 0x10) else ''
        print(f"  {chiptype_name} clock: {ay_raw} Hz{div_note} → effective {ay_eff} Hz")
        ser.write(bytes([0xB7]) + struct.pack('<I', ay_eff))
    # GB DMG 时钟显示 (仅当有 GB 命令时; GB clock 固定不下发, 固件硬编码 4194304)
    gb_clk = hdr.get('gb_clock') or 0
    if stats['gb'] > 0 and gb_clk:
        print(f"  GB clock: {gb_clk} Hz (DMG)")
    # NES DMC 采样: 按总大小自动选模式 (MCU nes_dmc_buf = 16KB).
    #   ≤ 16KB → 预存 (开播前一次性发完, 不占 samples_budget, 节拍稳)
    #   > 16KB → 流式 (主循环遇 0x67 0xC2 实时下发, 否则 16KB 装不下, 如 Gimmick 132KB)
    # 同地址多块按时序覆盖 (符合真实 NES 语义: 后写覆盖先写).
    DMC_PRELOAD_LIMIT = 16384
    dmc_blocks = hdr.get('nes_dmc_blocks') or []
    total_dmc_bytes = sum(len(p) for _, p in dmc_blocks)
    dmc_stream_mode = total_dmc_bytes > DMC_PRELOAD_LIMIT
    dmc_stream_sent = 0  # 流式已发送累计字节 (主循环用)
    dmc_stream_seq = 0   # 流式块序号 (主循环用)
    if dmc_blocks:
        mode_label = 'STREAM ' if dmc_stream_mode else 'PRELOAD'
        total_str = fmt_bytes(total_dmc_bytes)
        if not dmc_stream_mode:
            # 预存: 按出现顺序逐块下发, 后到的覆盖先到的. 带进度条.
            print(f"  DMC [{mode_label}] {len(dmc_blocks)} blocks, {total_str} total")
            sent = 0
            t0 = time.perf_counter()
            for i, (blk_addr, blk_data) in enumerate(dmc_blocks):
                dmc_send_block(ser, blk_addr, blk_data)
                sent += len(blk_data)
                # 同行刷新进度条 (每块或每 512B 更新一次)
                line = (f"\r  DMC [{mode_label}] {progress_bar(sent, total_dmc_bytes)} "
                        f"{fmt_bytes(sent)} / {total_str}  blk{i+1}/{len(dmc_blocks)}")
                print(line, end='', flush=True)
            time.sleep(0.02)
            dt = time.perf_counter() - t0
            print(f"\r  DMC [{mode_label}] {progress_bar(total_dmc_bytes, total_dmc_bytes)} "
                  f"{total_str} / {total_str}  {len(dmc_blocks)} blocks  {dt*1000:.0f}ms  OK")
        else:
            # 流式: 主循环遇 0x67 0xC2 实时下发. 开播前只显示计划.
            print(f"  DMC [{mode_label}] {len(dmc_blocks)} blocks, {total_str} total (>16KB, on-the-fly)")
    loop_remaining = loop if isinstance(loop, int) else (2 if loop else 0)
    if loop_remaining > 0 and hdr['loop_offset'] > 0:
        print(f"  Speed: {speed:.1f}x [LOOP x{loop_remaining}]")
    else:
        print(f"  Speed: {speed:.1f}x")
    print()

    last_time = time.perf_counter()
    samples_budget = 0.0  # 累积的 VGM samples budget
    current_samples = 0
    iteration = 0
    interrupt_cmd = None

    while True:
        # 1ms 轮询
        time.sleep(0.001)

        # 播放列表模式下检查键盘命令
        if allow_interrupt and _kb_cmd in ('n', 'b', 'q'):
            interrupt_cmd = _kb_cmd
            _kb_cmd = ''
            break

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
                if loop_remaining > 0 and hdr['loop_offset'] > 0:
                    loop_remaining -= 1
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
                # Data block: [0x67][0x66][type][size:4 LE][data]
                # 预存模式 (≤16KB): 开播前已发, 这里只跳过.
                # 流式模式 (>16KB): 遇 0xC2 NES DMC 块实时分片下发 0xB6 到 MCU 16K buffer.
                #   时序安全: 0xC2 LOAD 总在 $4015 TRIG 之前到达.
                #   重置 last_time 让传输耗时不计入 samples_budget (避免追跑).
                if pos + 6 <= end:
                    tp = data[pos + 1]
                    sz = struct.unpack_from('<I', data, pos + 2)[0] & 0x7FFFFFFF
                    if dmc_stream_mode and tp == 0xC2 and sz >= 2 and pos + 6 + sz <= end:
                        ram_addr = struct.unpack_from('<H', data, pos + 6)[0]
                        payload = data[pos + 8: pos + 6 + sz]
                        last_time = time.perf_counter()
                        dmc_send_block(ser, ram_addr, payload)
                        last_time = time.perf_counter()
                        # 流式实时进度: 每块刷新一行 (序号/地址/本块/累计/总进度)
                        dmc_stream_seq += 1
                        dmc_stream_sent += len(payload)
                        total_str = fmt_bytes(total_dmc_bytes)
                        nblk = len(dmc_blocks)
                        print(f"\r  DMC [STREAM ] #{dmc_stream_seq:03d}/{nblk} "
                              f"${ram_addr:04X} {fmt_bytes(len(payload)):<7s} "
                              f"{progress_bar(dmc_stream_sent, total_dmc_bytes, 16)} "
                              f"{fmt_bytes(dmc_stream_sent)} / {total_str}", end='', flush=True)
                    pos += 6 + sz
                else:
                    pos = end

            else:
                # Unknown: skip by length
                skip = VGM_CMD_LEN[b]
                if skip > 1:
                    pos += skip - 1

        if pos >= end:
            break

    # 流式进度条换行 (避免和 END/CUT 挤一行)
    if dmc_stream_mode and dmc_stream_seq > 0:
        print()
    real_sec = current_samples / SAMPLES_PER_SEC / speed
    if interrupt_cmd:
        print(f"  [CUT {interrupt_cmd.upper()}] {real_sec:.1f}s")
    else:
        print(f"  [END] {real_sec:.1f}s")
    return interrupt_cmd


def list_song_files(vgm_dir):
    """返回去重后的 VGM 文件路径列表"""
    files = sorted(glob.glob(os.path.join(vgm_dir, '*.vgz')))
    files += sorted(glob.glob(os.path.join(vgm_dir, '*.vgm')))
    seen = set(); unique = []
    for f in files:
        name = os.path.basename(f)
        if name not in seen:
            seen.add(name); unique.append(f)
    return unique


# 全局键盘状态 (主线程读, 后台线程写)
_kb_cmd = ''      # 'n' next, 'b' back, 'q' quit, '' idle
_kb_lock = False  # 简单 flag, 不用 threading.Lock 避免依赖


def _kb_watcher():
    """后台线程: 读按键, 设置全局命令"""
    global _kb_cmd
    try:
        import msvcrt
        while True:
            if msvcrt.kbhit():
                ch = msvcrt.getch().decode('ascii', errors='ignore').lower()
                if ch in ('n', 'b', 'q'):
                    _kb_cmd = ch
            time.sleep(0.05)
    except ImportError:
        # 非 Windows: 用 select 轮询 stdin
        try:
            import select, sys
            while True:
                r, _, _ = select.select([sys.stdin], [], [], 0.1)
                if r:
                    ch = sys.stdin.readline().strip().lower()[:1]
                    if ch in ('n', 'b', 'q'):
                        _kb_cmd = ch
        except Exception:
            pass


def play_playlist(ser, vgm_dir, speed=1.0, loop=0, start_idx=0):
    """顺序播放整个目录
    按键: n=下一曲, b=上一曲, q=退出
    loop: 每首歌循环次数 (0=不循环)
    """
    global _kb_cmd
    files = list_song_files(vgm_dir)
    if not files:
        print(f"No .vgm/.vgz in {vgm_dir}/"); return

    # 启动键盘监听线程
    import threading
    watcher = threading.Thread(target=_kb_watcher, daemon=True)
    watcher.start()

    print(f"\n=== Playlist mode: {len(files)} tracks ===")
    print("Keys: [n] next  [b] back  [q] quit\n")

    idx = start_idx
    global _kb_cmd

    def mute_all_chips():
        """切换曲目前复位所有芯片
        0xF0 = 固件调用 sn_init/ay_init/scc_init/nes_init, 清除所有残留状态
        (相位累加器/步进值/波表/key 状态), 这是从根上解决切歌第一音音高错误"""
        ser.write(bytes([0xF0]))
        time.sleep(0.05)

    while 0 <= idx < len(files):
        filepath = files[idx]
        name = os.path.basename(filepath)
        print(f"[{idx+1}/{len(files)}] {name}")
        cmd = None
        try:
            data = load_vgm(filepath)
            hdr = parse_vgm_header(data)
            stats = scan_vgm_stats(data, hdr)
            cmd = play_vgm(data, hdr, stats, ser=ser, speed=speed, loop=loop, allow_interrupt=True)
        except KeyboardInterrupt:
            cmd = 'q'
        except Exception as e:
            print(f"  Skip (error: {e})")

        # 切换曲目前静音所有芯片
        mute_all_chips()
        # 短歌之间留 0.3 秒间隔
        time.sleep(0.3)

        # 命令可能来自 play_vgm 返回值, 也可能来自 sleep 期间按下
        if not cmd:
            cmd = _kb_cmd
            _kb_cmd = ''

        if cmd == 'q':
            print("\n[QUIT]")
            break
        elif cmd == 'n':
            print("[NEXT]\n")
            idx += 1
        elif cmd == 'b':
            idx = max(0, idx - 1)
            print(f"[BACK to {idx+1}]\n")
        else:
            idx += 1

    if idx >= len(files):
        print("\n=== Playlist end ===")


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

# WT 波形名称 (按类型排列: 方波/sine类/其他)
# 寄存器 0x13 data = type<<4 | index
WT_WAVES = {
    (0,0): 'sq12',   (0,1): 'sq25',   (0,2): 'pulse50', (0,3): 'sq75',
    (1,0): 'sin',    (1,1): 'clipsin', (1,2): 'abssin',  (1,3): 'halfsin',
    (1,4): 'qsin',   (1,5): 'altsin', (1,6): 'althalfsin', (1,7): 'tri',
    (2,0): 'saw',    (2,1): 'gb_dmg',
}
# 扁平列表 (按 wave table 索引 0-13)
WT_WAVE_NAMES = ['sq12', 'sq25', 'pulse50', 'sq75', 'sin', 'clipsin',
                 'abssin', 'halfsin', 'qsin', 'altsin', 'althalfsin', 'tri',
                 'saw', 'gb_dmg']
# wave table 索引 -> 寄存器 data (type<<4|index)
WT_WAVE_REG = [0x00,0x01,0x02,0x03, 0x10,0x11,0x12,0x13,0x14,0x15,0x16,0x17, 0x20,0x21]

def fm_send_note(ser, voice, note, duration_ms=300):
    """发送 FM Note On, 等待, Note Off (OPLL 分页模式)"""
    uart_send(ser, [0x51, 0x10 | (voice & 0x0F), note & 0x7F])
    time.sleep(duration_ms / 1000.0)
    uart_send(ser, [0x51, 0x20 | (voice & 0x0F), 0])
    time.sleep(0.05)

def fm_scale(ser):
    """FM 全音阶: 8 voice 轮流分配, 最多同时 3 音, 从 C1 到 C9"""
    print("\n  === FM Scale (C1-C9) ===")
    # 设置快 release (reg 0x06/0x07 低4位=rel, 1=最快)
    uart_send(ser, [0x51, 0x06, 0x0F])  # mod rel=15(最快)
    uart_send(ser, [0x51, 0x07, 0x0F])  # car rel=15(最快)
    time.sleep(0.05)
    notes = list(range(24, 109))  # MIDI 24(C1) to 108(C8)
    vi = 0  # voice 轮转计数器
    active = []  # (voice, note)
    hold = 2     # 最多同时几音
    for note in notes:
        names = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
        oct = note // 12 - 1
        nm = names[note % 12]
        print(f"  voice{vi % 8}: {nm}{oct} (MIDI {note})")
        # 先关超出的音
        while len(active) >= hold:
            old_v = active.pop(0)
            uart_send(ser, [0x51, 0x20 | old_v, 0])
            time.sleep(0.05)
        # 再开新音
        uart_send(ser, [0x51, 0x10 | (vi % 8), note & 0x7F])
        active.append(vi % 8)
        vi += 1
        time.sleep(0.15)
    # 关闭所有剩余音
    time.sleep(0.3)
    for v in active:
        uart_send(ser, [0x51, 0x20 | v, 0])
    time.sleep(0.1)
    print("  FM Scale done.")


# ========== WT Wavetable Player ==========

def wt_send(ser, addr, data):
    """发送 WT 命令 [0xC0][addr][data][xor] 等待 ACK"""
    chk = 0xC0 ^ addr ^ data
    uart_send(ser, [0xC0, addr, data, chk], ack=True)

def wt_note_on(ser, ch, note):
    """WT note on: ch 0-3, note 24-127"""
    wt_send(ser, 0x00 | ch, note)

def wt_note_off(ser, ch):
    """WT note off: ch 0-3"""
    wt_send(ser, 0x04 | ch, 0)

def wt_set_wave(ser, wave_idx):
    """WT set wave: wave table 索引 0-13"""
    wt_send(ser, 0x13, wave_idx)

def wt_set_release(ser, rel_val):
    """WT set release: 0-15"""
    wt_send(ser, 0x12, rel_val)

def wt_scale(ser, wave_idx=None):
    """WT 全音阶: 4 通道轮替, 指定或轮替波形, 中等 release"""
    wave_name = WT_WAVE_NAMES[wave_idx] if wave_idx is not None else "auto-cycle"
    print(f"\n  === WT Scale (C1-C8, {wave_name}) ===")
    # 设置中等 release (7)
    wt_set_release(ser, 7)
    time.sleep(0.05)

    start_note = 24  # C1
    end_note = 108   # C8

    ch = 0
    wave = wave_idx if wave_idx is not None else 0

    if wave_idx is not None:
        wt_set_wave(ser, wave_idx)
        time.sleep(0.05)

    for note in range(start_note, end_note + 1):
        # 每 12 音 (一个八度) 切换波形 (仅当未指定时)
        if wave_idx is None and note > start_note and (note - start_note) % 12 == 0:
            wave = (wave + 1) % len(WT_WAVE_NAMES)
            wt_set_wave(ser, wave)
            print(f"  --- 切换波形: {WT_WAVE_NAMES[wave]} ---")
        names = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
        oct = note // 12 - 1
        nm = names[note % 12]
        print(f"  ch{ch} {nm}{oct} (MIDI {note})")

        wt_note_on(ser, ch, note)
        ch = (ch + 1) % 4
        time.sleep(0.15)

    print("  等待所有音符结束...")
    time.sleep(3.0)

    # 确保关闭所有通道
    for c in range(4):
        wt_note_off(ser, c)
    time.sleep(0.5)
    print("  WT Scale done.")


# ========== Gigatron .gbas.c Player ==========

# FNUM 频率表 (同参考实现 fnum_table.h, 96 条, index 0-95)
GT_FNUM_TABLE = [
    0x0045, 0x0049, 0x004d, 0x0052, 0x0056, 0x005c, 0x0061, 0x0067, 0x006d, 0x0073, 0x007a, 0x0081,
    0x0089, 0x0091, 0x009a, 0x00a3, 0x00ad, 0x00b7, 0x00c2, 0x00ce, 0x00da, 0x00e7, 0x00f4, 0x0103,
    0x0112, 0x0123, 0x0134, 0x0146, 0x015a, 0x016e, 0x0184, 0x019b, 0x01b3, 0x01cd, 0x01e9, 0x0206,
    0x0225, 0x0245, 0x0268, 0x028c, 0x02b3, 0x02dc, 0x0308, 0x0336, 0x0367, 0x039b, 0x03d2, 0x040c,
    0x0449, 0x048b, 0x04d0, 0x0519, 0x0567, 0x05b9, 0x0610, 0x066c, 0x06ce, 0x0735, 0x07a3, 0x0817,
    0x0893, 0x0915, 0x099f, 0x0a32, 0x0acd, 0x0b72, 0x0c20, 0x0cd8, 0x0d9c, 0x0e6b, 0x0f46, 0x102f,
    0x1125, 0x122a, 0x133f, 0x1464, 0x159a, 0x16e3, 0x183f, 0x19b1, 0x1b38, 0x1cd6, 0x1e8d, 0x205e,
    0x224b, 0x2455, 0x267e, 0x28c8, 0x2b34, 0x2dc6, 0x307f, 0x3361, 0x366f, 0x39ac, 0x3d1a, 0x0000,
]

# Gigatron 帧率: 60Hz (Gigatron 原始 vCPU 帧率)
GT_FRAME_RATE = 60.0

# GT UART 命令前缀
GT_CMD = 0xB0

# GT 固件寄存器地址
GT_REG_FNUML = 0x00  # ch0-3: +ch
GT_REG_FNUMH = 0x04  # ch0-3: +ch
GT_REG_WAVX  = 0x08  # ch0-3: +ch
GT_REG_WAVA  = 0x0C  # ch0-3: +ch
GT_REG_OFF   = 0x10  # ch0-3: +ch, note off


def gt_send(ser, addr, data):
    """发送 GT 寄存器写入 (XOR 校验, 单发)"""
    chk = GT_CMD ^ addr ^ data
    ser.write(bytes([GT_CMD, addr, data, chk]))


def gt_note_off(ser, ch):
    gt_send(ser, GT_REG_OFF + ch, 0)


def gt_note_on(ser, ch, note, wavA=0, wavX=0, octave_shift=0.0):
    """发送 note on: 查 FNUM 表, 写 fnumL + fnumH + wavA + wavX
    ch: 0-3 (固件地址), note: FNUM 表索引
    octave_shift: 正数降八度 (1=-1oct), 负数升八度, 支持小数
    """
    if note >= len(GT_FNUM_TABLE) or note < 0:
        gt_note_off(ser, ch)
        return
    fnum = GT_FNUM_TABLE[note]
    # key = FNUM * 3125 / 882: 参考实现→STC32G tick rate 精确换算
    key = (fnum * 3125 + 441) // 882
    # 八度偏移: 每八度除以2
    if octave_shift != 0.0:
        key = int(key / (2.0 ** octave_shift) + 0.5)
    if key > 16383:
        key = 16383
    if key < 1:
        key = 1
    fnumL = key & 0x7F
    fnumH = (key >> 7) & 0x7F
    fnumL = fnum & 0x7F
    fnumH = (fnum >> 7) & 0x7F
    gt_send(ser, GT_REG_WAVA + ch, wavA)
    gt_send(ser, GT_REG_WAVX + ch, wavX)
    gt_send(ser, GT_REG_FNUML + ch, fnumL)
    gt_send(ser, GT_REG_FNUMH + ch, fnumH)


def parse_gbas_c(filepath):
    """解析 .gbas.c 文件, 返回帧事件列表 [(frame, cmd, ch, note, wavA, wavX), ...]
    cmd: 'D'=delay, 'X'=off, 'N'=note, 'M'=note+wavA, 'W'=note+wavA+wavX
    """
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    # 找到所有 segment: nohop static const byte xxx[] = { ... };
    segments = []
    pattern = r'nohop\s+static\s+const\s+byte\s+\w+\[\]\s*=\s*\{([^}]*)\}'
    for m in re.finditer(pattern, content):
        seg_text = m.group(1)
        seg_bytes = []
        # 解析宏调用
        pos = 0
        while pos < len(seg_text):
            # 跳过空白和逗号
            m2 = re.match(r'[\s,]+', seg_text[pos:])
            if m2:
                pos += m2.end()
                continue
            if pos >= len(seg_text):
                break

            # 检查结尾 0
            m2 = re.match(r'\b0\b\s*([,}\s]|$)', seg_text[pos:])
            if m2:
                seg_bytes.append(('Z', 0, 0, 0, 0))
                pos += 1
                continue

            # 匹配宏: D(x), X(c), N(c,n), M(c,n,v), W(c,n,v,w)
            m2 = re.match(r'([DZXNMW])\s*\(([^)]*)\)', seg_text[pos:])
            if m2:
                cmd = m2.group(1)
                args = [int(x.strip()) for x in m2.group(2).split(',')]
                if cmd == 'D':
                    seg_bytes.append(('D', args[0], 0, 0, 0))
                elif cmd == 'X':
                    seg_bytes.append(('X', args[0], 0, 0, 0))
                elif cmd == 'N':
                    seg_bytes.append(('N', args[0], args[1], 0, 0))
                elif cmd == 'M':
                    seg_bytes.append(('M', args[0], args[1], args[2], 0))
                elif cmd == 'W':
                    seg_bytes.append(('W', args[0], args[1], args[2], args[3]))
                pos += m2.end()
            else:
                pos += 1
        segments.append(seg_bytes)

    return segments


def build_gt_timeline(segments):
    """将解析后的 segments 构建为帧事件时间轴
    返回: [(frame, cmd, ch, note, wavA, wavX), ...] 已按 frame 排序
    """
    timeline = []
    abs_frame = 0

    for seg in segments:
        for cmd, a1, a2, a3, a4 in seg:
            if cmd == 'Z':
                continue  # segment 结束标记
            elif cmd == 'D':
                abs_frame += a1
            elif cmd == 'X':
                # ch off: ch = a1 (0-3)
                timeline.append((abs_frame, 'X', a1, 0, 0, 0))
            elif cmd == 'N':
                # note on: ch=a1, note=a2
                timeline.append((abs_frame, 'N', a1, a2, 0, 0))
            elif cmd == 'M':
                # note+wavA: ch=a1, note=a2, wavA=a3
                timeline.append((abs_frame, 'M', a1, a2, a3, 0))
            elif cmd == 'W':
                # note+wavA+wavX: ch=a1, note=a2, wavA=a3, wavX=a4
                timeline.append((abs_frame, 'W', a1, a2, a3, a4))
        # segments 之间 frame 继续累加 (不重置)

    timeline.sort(key=lambda e: e[0])
    return timeline


def play_gigatron(ser, filepath, speed=1.0, loop=False, octave_shift=0.0):
    """播放 Gigatron .gbas.c 文件"""
    segments = parse_gbas_c(filepath)
    if not segments:
        print(f"  No data in {filepath}")
        return

    total_notes = sum(len(s) for s in segments)
    timeline = build_gt_timeline(segments)
    if not timeline:
        print(f"  Empty timeline")
        return

    max_frame = timeline[-1][0]
    duration = max_frame / GT_FRAME_RATE

    print(f"  Segments: {len(segments)}, Events: {len(timeline)}, Frames: {max_frame}")
    print(f"  Duration: {duration:.1f}s @60Hz")
    print(f"  Speed: {speed:.2f}x" + (" [LOOP]" if loop else ""))
    if octave_shift != 0.0:
        print(f"  Octave shift: {-octave_shift:+.1f} oct ({'down' if octave_shift > 0 else 'up'})")
    print()

    while True:
        play_pos = 0
        last_time = time.perf_counter()
        frame_budget = 0.0
        current_frame = 0

        while True:
            time.sleep(0.001)
            now = time.perf_counter()
            elapsed = now - last_time
            last_time = now
            frame_budget += elapsed * GT_FRAME_RATE * speed

            while frame_budget >= 1.0 and play_pos < len(timeline):
                target_frame = int(current_frame)
                # 发送当前帧的所有事件
                while play_pos < len(timeline) and timeline[play_pos][0] <= target_frame:
                    evt = timeline[play_pos]
                    cmd = evt[1]
                    ch = evt[2] - 1  # 1-indexed → 0-indexed
                    if ch < 0 or ch > 3:
                        play_pos += 1
                        continue
                    if cmd == 'X':
                        gt_note_off(ser, ch)
                    elif cmd in ('N', 'M', 'W'):
                        note = evt[3]
                        wavA = evt[4] if cmd in ('M', 'W') else 0
                        wavX = evt[5] if cmd == 'W' else 0
                        gt_note_on(ser, ch, note, wavA, wavX, octave_shift)
                    play_pos += 1

                frame_budget -= 1.0
                current_frame += 1

            if play_pos >= len(timeline):
                break

        if not loop:
            break
        # loop: 全部 off 再重来
        for c in range(4):
            gt_note_off(ser, c)
        time.sleep(0.1)

    # 结束: 全部静音
    for c in range(4):
        gt_note_off(ser, c)
    print(f"  [END] {duration / speed:.1f}s")


def list_gt_songs(gt_dir):
    files = sorted(glob.glob(os.path.join(gt_dir, '*.gbas.c')))
    files += sorted(glob.glob(os.path.join(gt_dir, '*.c')))
    if not files:
        print(f"No .gbas.c in {gt_dir}/")
        return
    print(f"\n{'#':>3}  {'File':<50} {'Segs':>5} {'Events':>7} {'Duration':>8}")
    print("-" * 80)
    for i, f in enumerate(files, 1):
        name = os.path.basename(f)
        try:
            segs = parse_gbas_c(f)
            tl = build_gt_timeline(segs)
            max_frame = tl[-1][0] if tl else 0
            dur = f"{max_frame / GT_FRAME_RATE:.1f}s"
            print(f"{i:3}  {name:<50} {len(segs):5} {len(tl):7} {dur:>8}")
        except Exception as e:
            print(f"{i:3}  {name:<50} ERROR: {e}")


def fm_demo(ser):
    """FM 演示: 和弦 + 音色切换 + 旋律"""
    print("\n  === FM Demo ===")

    # C4+E4+G4 三音和弦
    print("  C4 E4 G4 chord ...")
    uart_send(ser, [0x51, 0x10, 60])
    uart_send(ser, [0x51, 0x11, 64])
    uart_send(ser, [0x51, 0x12, 67])
    time.sleep(1.0)
    for v in range(3):
        uart_send(ser, [0x51, 0x20 | v, 0])
    time.sleep(0.1)

    # 波形演示 (改 carrier wave)
    print("  Wave sweep (carrier) ...")
    for wi, wname in enumerate(FM_WAVE_NAMES):
        print(f"    {wname}")
        uart_send(ser, [0x51, 0x09, wi])
        uart_send(ser, [0x51, 0x10, 60])
        time.sleep(0.5)
        uart_send(ser, [0x51, 0x20, 0])
        time.sleep(0.1)

    # 旋律
    print("  Melody ...")
    melody = [60, 62, 64, 65, 67, 69, 71, 72, 71, 69, 67, 65, 64, 62, 60]
    for note in melody:
        uart_send(ser, [0x51, 0x10, note])
        time.sleep(0.2)
    uart_send(ser, [0x51, 0x20, 0])
    time.sleep(0.1)

    print("  FM Demo done.")


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    vgm_dir = os.path.join(script_dir, '..', 'vgm')

    parser = argparse.ArgumentParser(description='VGM Player for STC Chiptune Synth')
    parser.add_argument('song', nargs='?', help='Track number or name')
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--port', default='COM24', help='Serial port (default COM24)')
    parser.add_argument('--baud', type=int, default=115200)
    parser.add_argument('--speed', type=float, default=1.0)
    parser.add_argument('--loop', type=int, nargs='?', const=2, default=0, metavar='N',
                        help='Loop N times (default 2 if --loop without value)')
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
    parser.add_argument('--wt-scale', action='store_true',
                        help='WT full scale test (C1-C8, 4 channels)')
    parser.add_argument('--wt-wave', type=int, metavar='WAVE',
                        help='WT waveform index (0-13): sq12/sq25/pulse50/sq75/sin/clipsin/abssin/halfsin/qsin/altsin/althalfsin/tri/saw/gb_dmg')
    parser.add_argument('--gt', type=int, metavar='N',
                        help='Play Gigatron .gbas.c track number')
    parser.add_argument('--gt-dir', default=None,
                        help='Gigatron music directory')
    parser.add_argument('--gt-list', action='store_true',
                        help='List Gigatron .gbas.c tracks')
    parser.add_argument('--gt-shift', type=float, default=0.0, metavar='OCT',
                        help='Gigatron octave shift (1 = -1 octave, -0.5 = +half octave)')
    args = parser.parse_args()
    if args.vgm_dir: vgm_dir = args.vgm_dir

    # FM direct commands (no VGM needed)
    if args.fm_note is not None or args.fm_off is not None or args.fm_wave is not None or args.fm_demo or args.fm_scale or args.wt_scale:
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
                uart_send(ser, [0x51, 0x10 | (voice & 0x0F), note & 0x7F])
                print(f"FM Note On: voice={voice} note={note}")
            if args.fm_off is not None:
                uart_send(ser, [0x51, 0x20 | (args.fm_off & 0x0F), 0])
                print(f"FM Note Off: voice={args.fm_off}")
            if args.fm_wave:
                voice, wave = args.fm_wave
                uart_send(ser, [0x51, 0x09, wave & 0x07])
                uart_send(ser, [0x51, 0x08, wave & 0x07])
                print(f"FM Set Wave: voice={voice} wave={wave}")
            if args.fm_demo:
                fm_demo(ser)
            if args.fm_scale:
                fm_scale(ser)
            if args.wt_scale:
                wt_scale(ser, args.wt_wave)
        except Exception as e:
            print(f"Error: {e}")
        finally:
            ser.close()
        return

    # Gigatron commands
    gt_dir = args.gt_dir or os.path.join(script_dir, '..', 'vgm', 'giagtron')
    if args.gt_list:
        list_gt_songs(gt_dir); return

    if args.gt is not None:
        files = sorted(glob.glob(os.path.join(gt_dir, '*.gbas.c')))
        if not files:
            print(f"No .gbas.c files in {gt_dir}/"); sys.exit(1)
        idx = args.gt - 1
        if idx < 0 or idx >= len(files):
            print(f"Track {args.gt} out of range (1-{len(files)})"); sys.exit(1)
        filepath = files[idx]
        print(f"GT: {os.path.basename(filepath)}")
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
            gt_speed = args.speed
            play_gigatron(ser, filepath, speed=gt_speed, loop=args.loop, octave_shift=args.gt_shift)
        except KeyboardInterrupt:
            print("\n  Stopped.")
        finally:
            for c in range(4):
                gt_note_off(ser, c)
            time.sleep(0.01)
            ser.close()
        return

    if args.list:
        list_songs(vgm_dir); return

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

    def mute_all():
        # 全局静音: FM 16 voice off
        for v in range(16):
            uart_send(ser, [0x51, 0x20 | v, 0], ack=False)
        # 复位所有音源芯片 (清相位/步进/key/波表状态)
        ser.write(bytes([0xF0]))
        # GT: 4 ch note off
        for ch in range(4):
            addr = 0x10 + ch
            ser.write(bytes([0xB0, addr, 0, 0xB0 ^ addr]))
        time.sleep(0.02)

    try:
        if not args.song:
            # 无歌曲参数: 播放列表模式 (顺序播放整个目录)
            play_playlist(ser, vgm_dir, speed=args.speed, loop=args.loop)
        else:
            # 单曲模式
            filepath = resolve_song(args.song, vgm_dir)
            if not filepath:
                print(f"Song not found: '{args.song}'"); sys.exit(1)
            if args.dump:
                data = load_vgm(filepath)
                hdr = parse_vgm_header(data)
                dump_vgm(data, hdr); return
            print(f"Loading: {os.path.basename(filepath)}")
            data = load_vgm(filepath)
            hdr = parse_vgm_header(data)
            stats = scan_vgm_stats(data, hdr)
            play_vgm(data, hdr, stats, ser=ser, speed=args.speed, loop=args.loop)
    except KeyboardInterrupt:
        print("\n  Stopped.")
    finally:
        mute_all()
        ser.close()


if __name__ == '__main__':
    main()
