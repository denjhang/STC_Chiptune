"""usb_cdc_test 一键构建脚本

用法:
    py -3 build.py         # 全量编译 + 链接 + 生成 HEX
    py -3 build.py clean   # 仅清理

输出: src/build/MAIN.hex
"""
import os
import sys
import subprocess
import glob

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC  = os.path.join(ROOT, "src")
BUILD = os.path.join(SRC, "build")
KEIL = r"D:\Keil_v5\C251\BIN"
C251 = os.path.join(KEIL, "C251.exe")
L251 = os.path.join(KEIL, "l251.exe")
OH251 = os.path.join(KEIL, "OH251.exe")

SOURCES = [
    "main", "ay8910", "sn76489", "scc", "nes", "fds", "gb", "usb", "usb_desc",
    "usb_req_class", "usb_req_std", "usb_req_vendor",
    "util", "timer",  # 不用 uart.c (CDC2/UART 透传), 单 CDC 直接 USB -> Buffer
]


def run(cmd):
    print(f">>> {' '.join(cmd)}")
    r = subprocess.run(cmd, cwd=SRC, capture_output=True)
    out = (r.stdout or b"").decode("utf-8", errors="replace") + (r.stderr or b"").decode("utf-8", errors="replace")
    print(out)
    return r.returncode, out


def clean():
    for f in glob.glob(os.path.join(SRC, "*.OBJ")):
        os.remove(f)
    for f in glob.glob(os.path.join(SRC, "*.LST")):
        os.remove(f)
    os.makedirs(BUILD, exist_ok=True)
    for f in glob.glob(os.path.join(BUILD, "*")):
        os.remove(f)
    print("cleaned.")


def main():
    if "clean" in sys.argv:
        clean()
        return

    clean()
    os.makedirs(BUILD, exist_ok=True)

    # 1. 编译 — C251 即便有 WARNING 也可能返回非 0, 只看 ERROR 计数
    for s in SOURCES:
        rc, out = run([C251, f"{s}.c", "LARGE", "OPTIMIZE(8,SPEED)", "INCDIR(inc)"])
        if "ERROR(S)" in out and not out.rstrip().endswith("0 ERROR(S)"):
            print(f"!!! 编译 {s}.c 失败")
            sys.exit(1)

    # 2. 链接
    objs = [f"{s}.OBJ" for s in SOURCES]
    link_args = ",".join(objs) + " TO build/MAIN"
    args_file = os.path.join(SRC, "link.args")
    with open(args_file, "w") as f:
        f.write(link_args + "\n")
    rc, out = run([L251, "@link.args"])
    # L57 (UNCALLED FUNCTION) 是无害警告, L251 警告也会 rc!=0
    # 只看真正的 ERROR 标记
    if "*** ERROR" in out or "FATAL" in out:
        print("!!! 链接失败")
        sys.exit(1)

    # 3. 生成 HEX
    rc, out = run([OH251, "build/MAIN", "HEXFILE(build/MAIN.hex)"])
    if rc != 0:
        print("!!! HEX 生成失败")
        sys.exit(1)

    hex_path = os.path.join(BUILD, "MAIN.hex")
    size = os.path.getsize(hex_path)
    print(f"\n=== BUILD OK ===")
    print(f"HEX: src/build/MAIN.hex ({size} bytes)")


if __name__ == "__main__":
    main()
