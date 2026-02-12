#!/usr/bin/env python3
"""Test Piper TTS Wyoming protocol to understand exact response format."""
import socket
import json
import time

PIPER_HOST = "piper"
PIPER_PORT = 10200

def test_wyoming():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(10)
    s.connect((PIPER_HOST, PIPER_PORT))

    # Send synthesize event (newline-delimited JSON)
    event = {
        "type": "synthesize",
        "data": {
            "text": "Merhaba",
            "voice": {"name": "tr_TR-dfki-medium"},
        },
    }
    event_line = json.dumps(event, ensure_ascii=False) + "\n"
    print(f"Sending: {event_line.strip()}")
    s.sendall(event_line.encode("utf-8"))

    # Read raw response
    time.sleep(3)
    chunks = []
    try:
        while True:
            data = s.recv(8192)
            if not data:
                break
            chunks.append(data)
    except socket.timeout:
        pass

    s.close()

    if not chunks:
        print("No data received!")
        return

    raw = b"".join(chunks)
    print(f"\nTotal bytes received: {len(raw)}")
    print(f"\nFirst 500 bytes (repr): {repr(raw[:500])}")

    # Try to find JSON lines
    text_part = b""
    for i, byte in enumerate(raw):
        if byte == 10:  # newline
            try:
                line = raw[:i].decode("utf-8")
                parsed = json.loads(line)
                print(f"\nFirst JSON event: {json.dumps(parsed, indent=2)}")
                print(f"JSON ends at byte {i}")
                print(f"Next bytes after JSON+newline: {repr(raw[i+1:i+50])}")
            except json.JSONDecodeError as e:
                print(f"\nJSON parse error at newline pos {i}: {e}")
                print(f"Content: {repr(raw[:i])}")
            break
    else:
        # No newline found, try parsing whole thing
        try:
            parsed = json.loads(raw.decode("utf-8", errors="replace"))
            print(f"\nParsed as single JSON: {json.dumps(parsed, indent=2)}")
        except json.JSONDecodeError as e:
            print(f"\nFailed to parse: {e}")
            # Show hex dump of first 200 bytes
            print(f"Hex: {raw[:200].hex()}")


if __name__ == "__main__":
    test_wyoming()
