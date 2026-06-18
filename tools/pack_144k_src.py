"""打包 STC32G144K246 源码 + tools/*.py 为 zip 备份

用法: python tools/pack_144k_src.py
输出: 项目根目录 STC32G144K246_src_{YYYYMMDD_HHMMSS}.zip

排除: build/, __pycache__/, .git/, *.OBJ/.o/.exe/.lst/.map/.bak
"""
import os
import zipfile
import datetime

EXCLUDES_DIR = {"build", "__pycache__", ".git"}
EXCLUDES_EXT = {".obj", ".o", ".exe", ".lst", ".map", ".bak"}


def main():
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out = f"STC32G144K246_src_{ts}.zip"

    count = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk("STC32G144K246"):
            dirs[:] = [d for d in dirs if d not in EXCLUDES_DIR]
            for f in sorted(files):
                ext = os.path.splitext(f)[1].lower()
                if ext in EXCLUDES_EXT:
                    continue
                zf.write(os.path.join(root, f))
                count += 1
        for f in sorted(os.listdir("tools")):
            if f.endswith(".py"):
                zf.write(os.path.join("tools", f))
                count += 1

    size = os.path.getsize(out)
    print(f"OK: {out}  ({count} files, {size} bytes)")


if __name__ == "__main__":
    main()
