#!/usr/bin/env python3
"""Wrap stc8usb to accept HEX files: auto-convert HEX->BIN then flash"""
import sys, os, tempfile, subprocess

def hex2bin(hexfile, binfile):
    size = 65536
    data = bytearray(size)
    with open(hexfile, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line[0] != ':': continue
            count = int(line[1:3], 16)
            addr = int(line[3:7], 16)
            rtype = int(line[7:9], 16)
            if rtype == 0x00:
                for i in range(count):
                    byte = int(line[9 + i*2:11 + i*2], 16)
                    if addr + i < size:
                        data[addr + i] = byte
            elif rtype == 0x01:
                break
    end = size
    while end > 0 and data[end-1] == 0xFF:
        end -= 1
    with open(binfile, 'wb') as f:
        f.write(data[:end])

if __name__ == '__main__':
    args = sys.argv[1:]
    bin_args = []
    flash_file = None
    i = 0
    while i < len(args):
        if args[i] in ('-f', '--flash') and i + 1 < len(args):
            flash_file = args[i + 1]
            i += 2
        else:
            bin_args.append(args[i])
            i += 1

    if flash_file and (flash_file.endswith('.hex') or flash_file.endswith('.HEX')):
        bin_file = flash_file.rsplit('.', 1)[0] + '.bin'
        hex2bin(flash_file, bin_file)
        bin_args.extend(['-f', bin_file])
    elif flash_file:
        bin_args.extend(['-f', flash_file])

    stc8usb_dir = os.path.dirname(os.path.abspath(__file__))
    stc8usb = os.path.join(stc8usb_dir, 'stc8usb.py')
    subprocess.run([sys.executable, stc8usb] + bin_args)
