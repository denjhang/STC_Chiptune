#!/usr/bin/env python3
"""Simple Intel HEX to binary converter for STC8H"""
import sys

def hex2bin(hexfile, binfile, size=65536):
    data = bytearray(size)
    with open(hexfile, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line[0] != ':':
                continue
            count = int(line[1:3], 16)
            addr = int(line[3:7], 16)
            rtype = int(line[7:9], 16)
            if rtype == 0x00:  # data record
                for i in range(count):
                    byte = int(line[9 + i*2 : 11 + i*2], 16)
                    if addr + i < size:
                        data[addr + i] = byte
            elif rtype == 0x01:  # EOF
                break
    # trim trailing 0xFF
    end = size
    while end > 0 and data[end-1] == 0xFF:
        end -= 1
    with open(binfile, 'wb') as f:
        f.write(data[:end])

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} input.hex output.bin")
        sys.exit(1)
    hex2bin(sys.argv[1], sys.argv[2])
