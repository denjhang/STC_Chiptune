#!/usr/bin/env py -3
"""STC32 USB HID 一键烧录脚本

流程:
1. 通过 USB CDC 发 @STCISP# 触发芯片进 ISP 模式 (HID 设备, VID=0x34BF PID=0x1001)
2. 走 HID 协议烧录 HEX: start → info → unlock → erase → 分块写 → reset

严格对齐参考脚本 stc32_hid_program.py 的节奏:
- send_packet 单次 read(64) 丢弃响应 (不循环等, 不验证), 靠 HID 流控背压
- apmorton pyhidapi 的 read/write 超时会抛 HIDException, 必须 try/except

用法:
    py -3 tools/stc32_hid_flash.py                              # 烧默认 MAIN.hex
    py -3 tools/stc32_hid_flash.py path/to/firmware.hex
    py -3 tools/stc32_hid_flash.py --port COM24
    py -3 tools/stc32_hid_flash.py --no-trigger                 # 芯片已在 ISP

依赖: hid (apmorton pyhidapi 1.0.9), intelhex, tqdm, pyserial
"""
import argparse
import os
import struct
import sys
import time

USB_VID = 0x34BF
USB_PID = 0x1001
PACKET_START = bytes([0x46, 0xB9])
PACKET_END   = bytes([0x16])
PACKET_HOST  = bytes([0x6A])


def trigger_isp_via_cdc(port, timeout=2.0):
    """通过 USB CDC 发 @STCISP# 触发芯片进 HID ISP 模式."""
    import serial
    try:
        ser = serial.Serial(port, 115200, timeout=0.3)
        ser.reset_input_buffer()
        ser.write(b'@STCISP#')
        ser.flush()
        print(f"  已发 @STCISP# 到 {port}")
    except Exception as e:
        print(f"  发送失败 (可能正常, CDC 断开): {e}")
    finally:
        try: ser.close()
        except: pass


def wait_for_hid_device(vid, pid, timeout=5.0):
    """等待 HID 设备出现, 返回 Device 对象 (apmorton pyhidapi)."""
    import hid
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            devs = list(hid.enumerate(vid, pid))
            if devs:
                return hid.Device(path=devs[0]['path'])
        except Exception:
            pass
        time.sleep(0.2)
    return None


def send_packet(h, packet_data):
    """发送 HID 协议包 + 单次 read(64) 丢弃响应 (严格对齐参考脚本).
    格式: [0x46 0xB9][0x6A][len:2 BE][payload][checksum:2 BE][0x16]
    reset 包 (0xFF) 不读响应.
    apmorton read/write 超时抛 HIDException, 全部 try/except 吞掉."""
    packet = bytearray()
    packet += PACKET_START
    packet += PACKET_HOST
    packet += struct.pack(">H", len(packet_data) + 6)
    packet += packet_data
    packet += struct.pack(">H", sum(packet[2:]) & 0xFFFF)
    packet += PACKET_END

    try:
        h.write(bytes([0x00]) + bytes(packet))
    except Exception as e:
        # write 偶尔抛 HIDException (设备忙), 短暂等待重试一次
        time.sleep(0.1)
        try:
            h.write(bytes([0x00]) + bytes(packet))
        except Exception as e2:
            raise RuntimeError(f"write 失败: {e2}")

    # 非复位包: 单次 read 丢弃 (不验证, 不循环, 保持节奏)
    if packet_data[0] != 0xFF:
        try:
            h.read(64, timeout=5000)   # 阻塞读, 5 秒超时足够 flash 写入
        except Exception:
            pass   # 超时/异常都吞掉, 参考脚本就是丢弃


def program_hex(h, hex_path):
    """完整烧录: info → unlock → erase → 分块写 → reset."""
    from intelhex import IntelHex
    from tqdm import tqdm

    print(f"  加载 HEX: {hex_path}")
    ih = IntelHex()
    ih.loadhex(hex_path)
    total = ih.maxaddr() - ih.minaddr() + 1
    print(f"  代码范围: 0x{ih.minaddr():06X} - 0x{ih.maxaddr():06X} ({total} 字节)")

    print("  [1/5] 初始化...")
    send_packet(h, bytes([0x00, 0x00]))
    send_packet(h, bytes([0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x80, 0x00]))
    print("  [2/5] 解锁...")
    send_packet(h, bytes([0x05, 0x00, 0x00, 0x5A, 0xA5]))
    print("  [3/5] 擦除...")
    send_packet(h, bytes([0x03, 0x00, 0x00, 0x5A, 0xA5]))

    print("  [4/5] 写入...")
    block_size = 0x80
    chunks = list(range(ih.minaddr(), ih.maxaddr() + 1, block_size))
    for i in tqdm(chunks, unit="块", ncols=50):
        chunk = ih[i:i + block_size].tobinarray()
        cmd = bytes([0x32]) if i == ih.minaddr() else bytes([0x12])
        payload = cmd + bytes([(i >> 8) & 0xFF, i & 0xFF, 0x5A, 0xA5]) + bytes(chunk)
        send_packet(h, payload)

    print("  [5/5] 复位...")
    send_packet(h, bytes([0xFF]))   # reset 不读响应


def main():
    ap = argparse.ArgumentParser(description="STC32 USB HID 烧录")
    ap.add_argument('hex', nargs='?', default='src/build/MAIN.hex',
                    help='HEX 文件路径 (默认 src/build/MAIN.hex)')
    ap.add_argument('--port', default='COM24', help='触发 ISP 用的 CDC 端口')
    ap.add_argument('--no-trigger', action='store_true', help='跳过 @STCISP# 触发')
    args = ap.parse_args()

    hex_path = args.hex
    if not os.path.isabs(hex_path):
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        hex_path = os.path.join(base, hex_path)
    if not os.path.exists(hex_path):
        print(f"错误: HEX 文件不存在: {hex_path}"); sys.exit(1)

    if not args.no_trigger:
        print(f"=== 触发 ISP ({args.port}) ===")
        trigger_isp_via_cdc(args.port)
        print("  等待 HID 设备枚举...")

    print(f"=== 连接 HID 设备 (VID=0x{USB_VID:04X} PID=0x{USB_PID:04X}) ===")
    h = wait_for_hid_device(USB_VID, USB_PID, timeout=5.0)
    if h is None:
        print("错误: 未找到 STC HID 设备")
        print("      请确认: 1) 芯片已进 ISP 模式  2) STC-ISP 软件没占用设备")
        sys.exit(1)
    try:
        print(f"  已连接: {h.product or 'STC USB-HID'}")
    except: pass

    print("=== 烧录 ===")
    try:
        program_hex(h, hex_path)
    except Exception as e:
        print(f"\n烧录失败: {e}")
        try: h.close()
        except: pass
        sys.exit(1)

    try: h.close()
    except: pass
    print("\n=== 烧录完成, 芯片已复位 ===")


if __name__ == '__main__':
    main()
