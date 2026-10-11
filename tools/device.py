"""Local USB control and framebuffer capture for FlowSight ESP32."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import struct
import time
import zlib

import serial
from serial.tools import list_ports


def find_port() -> str:
    candidates = [p.device for p in list_ports.comports() if p.vid in (0x1A86, 0x10C4, 0x303A)]
    if len(candidates) != 1:
        raise RuntimeError("Specify --port: expected one ESP32 USB serial adapter.")
    return candidates[0]


class Device:
    def __init__(self, port: str | None = None):
        self.serial = serial.Serial()
        self.serial.port = port or find_port()
        self.serial.baudrate = 115200
        self.serial.timeout = 0.25
        self.serial.write_timeout = 3
        self.serial.dtr = False
        self.serial.rts = False
        self.serial.open()
        # A previous host can disconnect in the middle of a JSON line.
        self.serial.write(b"\n")
        self.next_id = 1
        self.events = []

    def close(self):
        self.serial.close()

    def request(self, cmd: str, **args):
        request_id = self.next_id
        self.next_id += 1
        payload = json.dumps({"cmd": cmd, "id": request_id, **args}, separators=(",", ":"))
        self.serial.write(payload.encode("utf-8") + b"\n")
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            line = self.serial.readline()
            try:
                message = json.loads(line)
            except (ValueError, UnicodeDecodeError):
                continue
            if message.get("id") == request_id and message.get("event") in ("response", "frame", "synced"):
                if message.get("ok") is False:
                    raise RuntimeError(message.get("error", "Device rejected command"))
                return message
            self.events.append(message)
        raise TimeoutError("No FlowSight response on the selected port.")

    def exact(self, size: int) -> bytes:
        output = bytearray()
        deadline = time.monotonic() + 5
        while len(output) < size:
            block = self.serial.read(size - len(output))
            if block:
                output.extend(block)
                deadline = time.monotonic() + 5
            elif time.monotonic() > deadline:
                raise TimeoutError("Framebuffer transfer interrupted")
        return bytes(output)

    def capture(self, path: Path):
        meta = self.request("screen")
        if meta.get("format") != "rgb565-rle-le" or (meta.get("width"), meta.get("height")) != (320, 240):
            raise ValueError("Unsupported framebuffer format")
        rgb = bytearray()
        remaining = 320 * 240
        while remaining:
            run, color = struct.unpack("<HH", self.exact(4))
            if run < 1 or run > remaining:
                raise ValueError("Invalid framebuffer run length")
            red, green, blue = (color >> 11) & 31, (color >> 5) & 63, color & 31
            rgb.extend(bytes(((red << 3) | (red >> 2), (green << 2) | (green >> 4), (blue << 3) | (blue >> 2))) * run)
            remaining -= run
        # Encode a lossless PNG using only the Python standard library.
        def chunk(kind, data):
            return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        rows = b"".join(b"\0" + rgb[y*960:(y+1)*960] for y in range(240))
        png = b"\x89PNG\r\n\x1a\n"
        png += chunk(b"IHDR", struct.pack(">IIBBBBB", 320, 240, 8, 2, 0, 0, 0))
        png += chunk(b"IDAT", zlib.compress(rows, 9)) + chunk(b"IEND", b"")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(png)
        return {"path": str(path.resolve()), "source": "device-rendered RGB565 snapshot", **meta}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", help="COM3, /dev/ttyUSB0, etc. Auto-detected if omitted.")
    commands = parser.add_subparsers(dest="cmd", required=True)
    for name in ("status", "home", "calibrate"):
        commands.add_parser(name)
    screen = commands.add_parser("screen")
    screen.add_argument("path", type=Path)
    tap = commands.add_parser("tap", help="Simulated USB button press; does not verify the touch sensor.")
    tap.add_argument("x", type=int)
    tap.add_argument("y", type=int)
    args = parser.parse_args()
    device = Device(args.port)
    try:
        if args.cmd == "screen":
            result = device.capture(args.path)
        else:
            params = {k: v for k, v in vars(args).items() if k not in ("port", "cmd")}
            result = device.request(args.cmd, **params)
        print(json.dumps(result, ensure_ascii=True, indent=2))
    finally:
        device.close()


if __name__ == "__main__":
    main()
