#!/usr/bin/env python3
"""
NES 寄存器分布统计 (复用 vgm_player.py 的解析器, 不自己造).

用法:
  py -3 nes_reg_stats.py <vgm 文件或目录>

输出:
  - 每个文件: NES 命令总数 + 各寄存器 ($4000-$4017) 写入次数
  - 重点标注 $4011 (DMC DAC direct write) 比例
  - $4011 节奏: 连续两次 $4011 之间的平均 sample 间隔
"""
import sys, os, struct, glob

# 复用现有解析器
TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS_DIR)
import vgm_player as vp


def analyze(filepath):
    data = vp.load_vgm(filepath)
    hdr = vp.parse_vgm_header(data)
    pos = hdr['data_offset']
    end = min(hdr['eof'], len(data))

    reg_count = [0] * 0x18       # $4000-$4017
    reg4011_intervals = []       # 两次 $4011 之间的 sample 累计
    cur_sample = 0
    last_4011_sample = None

    while pos < end:
        b = data[pos]; pos += 1
        if b == 0x66:
            break
        elif b == 0xB4:
            # NES APU: [0xB4][reg][data]
            if pos + 2 <= end:
                reg = data[pos]
                val = data[pos+1]
                pos += 2
                if reg <= 0x17:
                    reg_count[reg] += 1
                if reg == 0x11:
                    if last_4011_sample is not None:
                        reg4011_intervals.append(cur_sample - last_4011_sample)
                    last_4011_sample = cur_sample
            else:
                break
        elif b == 0x67:
            if pos + 6 <= end:
                sz = struct.unpack_from('<I', data, pos + 2)[0] & 0x7FFFFFFF
                pos += 6 + sz
            else:
                break
        elif b == 0x61:
            if pos + 2 <= end:
                cur_sample += struct.unpack_from('<H', data, pos)[0]
                pos += 2
        elif b == 0x62:
            cur_sample += 735
        elif b == 0x63:
            cur_sample += 882
        elif 0x70 <= b <= 0x7F:
            cur_sample += (b & 0x0F) + 1
        elif 0x80 <= b <= 0x8F:
            cur_sample += (b & 0x0F) + 1
        elif 0x90 <= b <= 0x9F:
            cur_sample += (b & 0x0F) * 2 + 1
        else:
            skip = vp.VGM_CMD_LEN[b]
            if skip > 1:
                pos += skip - 1

    total_nes = sum(reg_count)
    print(f"\n=== {os.path.basename(filepath)} ===")
    print(f"  NES cmd total: {total_nes}  duration: {cur_sample/44100:.1f}s")
    # 寄存器表
    reg_names = {
        0x00:'SQ1 duty/vol', 0x01:'SQ1 sweep', 0x02:'SQ1 freqL', 0x03:'SQ1 len/freqH',
        0x04:'SQ2 duty/vol', 0x05:'SQ2 sweep', 0x06:'SQ2 freqL', 0x07:'SQ2 len/freqH',
        0x08:'TRI linear',   0x09:'TRI unused', 0x0A:'TRI freqL', 0x0B:'TRI len/freqH',
        0x0C:'NOI vol',      0x0D:'NOI unused', 0x0E:'NOI freq',  0x0F:'NOI len',
        0x10:'DMC IRQ/loop/rate', 0x11:'DMC DAC direct', 0x12:'DMC addr', 0x13:'DMC len',
        0x15:'APU status', 0x16:'frame IRQ', 0x17:'frame ctr',
    }
    print("  reg   name                  count    %")
    for r in range(0x18):
        if reg_count[r] > 0:
            pct = reg_count[r]*100/total_nes if total_nes else 0
            mark = '  <<<' if r == 0x11 else ''
            print(f"  ${r:02X}  {reg_names.get(r,'?'):20s}  {reg_count[r]:6d}  {pct:5.1f}%{mark}")

    # $4011 节奏分析
    if reg4011_intervals:
        import statistics
        avg = statistics.mean(reg4011_intervals)
        med = statistics.median(reg4011_intervals)
        mn = min(reg4011_intervals)
        mx = max(reg4011_intervals)
        print(f"  $4011 节奏 ({len(reg4011_intervals)} 个间隔):")
        print(f"    平均 {avg:.1f} samples ({avg/44100*1000:.2f}ms), 中位 {med}, min {mn}, max {mx}")
        # 平均频率
        print(f"    => 平均每 {(avg/44100):.5f}s 写一次 $4011")


def main():
    if len(sys.argv) < 2:
        print("usage: nes_reg_stats.py <vgm file or dir>")
        sys.exit(1)
    target = sys.argv[1]
    if os.path.isdir(target):
        files = sorted(glob.glob(os.path.join(target, '*.vgm')))
        files += sorted(glob.glob(os.path.join(target, '*.vgz')))
    else:
        files = [target]
    for f in files:
        try:
            analyze(f)
        except Exception as e:
            print(f"\n=== {os.path.basename(f)} === ERROR: {e}")


if __name__ == '__main__':
    main()
