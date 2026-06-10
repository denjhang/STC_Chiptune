#!/usr/bin/env python3
"""WT + PCM 简单测试 COM12"""
import serial, time, sys

PORT = sys.argv[1] if len(sys.argv) > 1 else "COM12"
BAUD = 115200

ser = serial.Serial(PORT, BAUD, timeout=0.5)
time.sleep(2)
ser.reset_input_buffer()
time.sleep(1)

def send_wt(addr, data):
    chk = 0xC0 ^ addr ^ data
    pkt = bytes([0xC0, addr, data, chk])
    ser.write(pkt)
    time.sleep(0.01)
    return ser.read(1)

print("=== WT Test: C4 on ch0 ===")
r = send_wt(0x00, 60)  # note on ch0, MIDI 60
print(f"note on ACK: {r.hex() if r else 'NONE'}")
time.sleep(0.5)
r = send_wt(0x04, 0)   # note off ch0
print(f"note off ACK: {r.hex() if r else 'NONE'}")
time.sleep(1)

print("=== PCM Test: BD drum 0 ===")
r = send_wt(0x15, 0)   # pcm note on ch0, drum 0
print(f"pcm on ACK: {r.hex() if r else 'NONE'}")
time.sleep(1)
r = send_wt(0x1B, 0)   # pcm note off ch0
print(f"pcm off ACK: {r.hex() if r else 'NONE'}")
time.sleep(1)

print("done")
ser.close()
