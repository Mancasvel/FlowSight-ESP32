"""Create a single image that can be written at flash address 0x0."""
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
build = root / ".pio/build/cyd"
boot_app = root / ".local/platformio/packages/framework-arduinoespressif32/tools/partitions/boot_app0.bin"
destination = root / "firmware/FlowSight-ESP32.bin"
destination.parent.mkdir(exist_ok=True)
subprocess.run([
    sys.executable, "-m", "esptool", "--chip", "esp32", "merge-bin",
    "--output", str(destination), "--flash-mode", "dio", "--flash-freq", "40m", "--flash-size", "4MB",
    "0x1000", str(build / "bootloader.bin"), "0x8000", str(build / "partitions.bin"),
    "0xe000", str(boot_app), "0x10000", str(build / "firmware.bin"),
], check=True)
print(destination)
