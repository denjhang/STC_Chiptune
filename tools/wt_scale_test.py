#!/usr/bin/env python3
"""WT 全音阶测试 - 4通道轮替，每八度切换波形"""

import serial
import time

PORT = "COM3"
BAUD = 115200

WT_WAVE_NAMES = ['tri', 'sin', 'saw', 'pulse', 'clipsin', 'abssin']

def wt_send(ser, addr, data):
    """发送 WT 命令 [0xC0][addr][data][xor] 等待 ACK"""
    chk = 0xC0 ^ addr ^ data
    pkt = bytes([0xC0, addr, data, chk])
    ser.write(pkt)
    time.sleep(0.002)
    resp = ser.read(1)
    if resp and resp[0] == 0xAA:
        return True
    return False

def wt_note_on(ser, ch, note):
    """WT note on: ch 0-3, note 24-127"""
    wt_send(ser, 0x00 | ch, note)

def wt_note_off(ser, ch):
    """WT note off: ch 0-3"""
    wt_send(ser, 0x04 | ch, 0)

def wt_set_wave(ser, wave_idx):
    """WT set wave: 0-5"""
    wt_send(ser, 0x13, wave_idx)

def wt_set_release(ser, rel_val):
    """WT set release: 0-15 (中等约 7)"""
    wt_send(ser, 0x12, rel_val)

def main():
    print(f"WT 全音阶测试 - {PORT} @ {BAUD}")
    print("每个八度切换波形，4通道轮替")

    ser = serial.Serial(PORT, BAUD, timeout=0.1)
    time.sleep(0.1)
    ser.reset_input_buffer()

    # 设置中等释放
    wt_set_release(ser, 7)

    # 从 C2 (MIDI 36) 到 C7 (MIDI 96)，4个八度 x 12 = 48 音
    start_note = 36
    end_note = 96

    print(f"\n播放 {start_note}-{end_note} (C2-C7)...")

    ch = 0
    wave = 0

    for note in range(start_note, end_note + 1):
        # 每 12 音 (一个八度) 切换波形
        if note > start_note and (note - start_note) % 12 == 0:
            wave = (wave + 1) % 6
            wt_set_wave(ser, wave)
            print(f"\n--- 切换波形: {WT_WAVE_NAMES[wave]} ---")

        wt_note_on(ser, ch, note)
        print(f"ch{ch} note={note:3} ({WT_WAVE_NAMES[wave]})")

        # 轮换通道
        ch = (ch + 1) % 4

        # 等待让音符发声
        time.sleep(0.15)

    print("\n全部发送完成，等待所有音符结束...")
    time.sleep(3.0)

    # 确保所有通道关闭
    for c in range(4):
        wt_note_off(ser, c)

    print("测试完成，LED 流水灯应该恢复")

    ser.close()

if __name__ == "__main__":
    main()
