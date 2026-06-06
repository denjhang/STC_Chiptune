#!/usr/bin/env python3
"""STC Chiptune Synth Test - sends commands over UART"""

import serial
import time
import sys

def send_cmd(ser, cmd, data_h=0, data_l=0):
    """Send 4-byte command: CMD DATA_H DATA_L CHECKSUM"""
    ck = (cmd + data_h + data_l) & 0xFF
    frame = bytes([cmd, data_h, data_l, ck])
    ser.write(frame)

def ping(ser):
    """Send PING and wait for 0xAA reply"""
    ser.reset_input_buffer()
    send_cmd(ser, 0xFF)
    timeout = time.time() + 2
    while time.time() < timeout:
        if ser.in_waiting:
            b = ser.read(1)[0]
            if b == 0xAA:
                print("  PING OK")
                return True
    print("  PING FAILED")
    return False

def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "COM3"
    baud = 115200

    print(f"Opening {port} @ {baud}...")
    ser = serial.Serial(port, baud, timeout=0.5)
    time.sleep(0.1)

    # Wait for chip to be ready (may need power cycle after flash)
    print("Waiting for chip...")
    time.sleep(1)

    if not ping(ser):
        print("No response. Make sure chip is flashed and connected.")
        ser.close()
        return

    print("\n--- Playing demo sequence ---")

    # NOTE_ON: A4 (440Hz) sine
    print("NOTE_ON A4 sine...")
    send_cmd(ser, 0x04, 0x01, 0xB8)  # 440
    send_cmd(ser, 0x02, 0x00, 0x00)  # sine
    time.sleep(1.5)

    # Change to saw
    print("WAVE saw...")
    send_cmd(ser, 0x02, 0x00, 0x01)
    time.sleep(1.5)

    # Change to triangle
    print("WAVE triangle...")
    send_cmd(ser, 0x02, 0x00, 0x02)
    time.sleep(1.5)

    # Change to square
    print("WAVE square...")
    send_cmd(ser, 0x02, 0x00, 0x03)
    time.sleep(1.5)

    # Back to sine
    send_cmd(ser, 0x02, 0x00, 0x00)
    time.sleep(0.3)

    # C4 (262Hz)
    print("NOTE_ON C4...")
    send_cmd(ser, 0x04, 0x01, 0x06)
    time.sleep(1)

    # E4 (330Hz)
    print("NOTE_ON E4...")
    send_cmd(ser, 0x04, 0x01, 0x4A)
    time.sleep(1)

    # G4 (392Hz)
    print("NOTE_ON G4...")
    send_cmd(ser, 0x04, 0x01, 0x88)
    time.sleep(1)

    # A4 (440Hz)
    print("NOTE_ON A4...")
    send_cmd(ser, 0x04, 0x01, 0xB8)
    time.sleep(1)

    # C5 (523Hz)
    print("NOTE_ON C5...")
    send_cmd(ser, 0x04, 0x02, 0x0B)
    time.sleep(1.5)

    # Volume down
    print("SET_VOL 8...")
    send_cmd(ser, 0x03, 0x00, 0x08)
    time.sleep(1)

    # Volume down
    print("SET_VOL 4...")
    send_cmd(ser, 0x03, 0x00, 0x04)
    time.sleep(1)

    # Volume max
    print("SET_VOL 15...")
    send_cmd(ser, 0x03, 0x00, 0x0F)
    time.sleep(0.5)

    # Note off
    print("NOTE_OFF...")
    send_cmd(ser, 0x05)
    time.sleep(0.5)

    # Simple melody: Twinkle Twinkle
    print("\n--- Twinkle Twinkle Little Star ---")
    notes = [
        (262, 1.0), (262, 1.0), (330, 1.0), (330, 1.0), (392, 1.0), (392, 1.0), (330, 1.5),
        (262, 1.0), (262, 1.0), (294, 1.0), (294, 1.0), (247, 1.0), (247, 1.0), (220, 1.5),
        (262, 1.0), (262, 1.0), (330, 1.0), (330, 1.0), (294, 1.0), (294, 1.0), (247, 1.5),
        (262, 1.0), (262, 1.0), (330, 1.0), (294, 1.0), (247, 1.0), (247, 1.0), (220, 1.5),
    ]
    for freq, dur in notes:
        send_cmd(ser, 0x04, (freq >> 8) & 0xFF, freq & 0xFF)
        time.sleep(dur)
        send_cmd(ser, 0x05)
        time.sleep(0.05)

    send_cmd(ser, 0x05)
    print("\nDone!")
    ser.close()

if __name__ == "__main__":
    main()
