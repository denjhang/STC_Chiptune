"""HID 回环测试: STC32G144K246 EP1 OUT -> EP1 IN

依赖: pip install hid (cython-hidapi 0.15.0)
"""
import sys
import time

import hid  # cython-hidapi

VID = 0x34bf
PID = 0xff01

def main():
    devs = list(hid.enumerate(VID, PID))
    if not devs:
        print(f"没找到设备 VID={VID:04x} PID={PID:04x}")
        return
    print(f"找到 {len(devs)} 个匹配设备")
    info = devs[0]
    # info 可能是 dict (pyhidapi) 或 DeviceInfo (cython-hidapi), 都支持 .get / getattr
    def g(key, default=''):
        if isinstance(info, dict):
            return info.get(key, default)
        return getattr(info, key, default)
    print(f"  path: {g('path')}")
    print(f"  product: {g('product_string')!r}")
    print(f"  usage_page=0x{g('usage_page', 0):04x} usage=0x{g('usage', 0):04x}")
    print(f"  release: 0x{g('release_number', 0):04x}")

    path = g('path')
    if path:
        dev = hid.Device(path=path)
    else:
        dev = hid.Device(VID, PID)
    print(f"已打开: {dev.manufacturer} / {dev.product}")

    def loopback(name, payload):
        # Windows hidapi 期望第 1 字节是 report id (我们用 0)
        msg = bytes([0]) + payload
        print(f"\n[{name}] 发送 {len(payload)}B: {payload[:8].hex()} ...")
        n = dev.write(msg)
        print(f"    write 返回 {n}")
        time.sleep(0.05)
        try:
            data = dev.read(64, timeout=2000)
        except Exception as e:
            print(f"    read 异常: {e}")
            return
        data = bytes(data)
        print(f"    read {len(data)}B: {data[:8].hex()} ...")
        if data == payload:
            print("    PASS")
        elif data:
            diff = [(i, payload[i] if i < len(payload) else None, data[i])
                    for i in range(len(data))
                    if i >= len(payload) or payload[i] != data[i]]
            print(f"    FAIL, 差异 {len(diff)} 处: {diff[:5]}")
        else:
            print("    FAIL, 没收到数据 (超时)")

    loopback("递增 0..63", bytes(range(64)))
    loopback("全 0xAA", bytes([0xAA] * 64))
    loopback("全 0x55", bytes([0x55] * 64))
    loopback("全 0xFF", bytes([0xFF] * 64))

    dev.close()
    print("\n完成")

if __name__ == "__main__":
    main()
