# FlowSight ESP32

A native, offline FlowSight focus timer for the **ESP32-2432S028R (Cheap Yellow Display / CYD)** with a 320 × 240 touchscreen. The firmware replaces the previous application on the board.

![FlowSight running on the ESP32 framebuffer](artifacts/device-screen.png)

## On the screen

- Large countdown with **Empezar**, **Pausar** and **Reanudar**.
- Focus and break modes, with separate saved durations.
- Reset confirmation while a session is active.
- Completed focus session count, preserved across restarts.
- Brightness control and four-point touch calibration.
- Offline operation from USB power, with no account, Wi-Fi or cloud connection.
- Saved sessions resume **paused** after a restart. Running sessions checkpoint every 30 seconds; up to 30 seconds may be repeated after abrupt power loss.

Tap **Ajustes** to change modes or durations. A running or paused session must be reset before its duration can be changed. Focus duration is 1–180 minutes; breaks are 1–60 minutes. A completed focus session offers **Descansar**; a completed break offers **Volver al foco**. Nothing starts automatically.

The physical **BOOT** button is an alternative start/pause/resume control. Hold it for 1.5 seconds **after boot** to calibrate touch. Tap the four targets, releasing between each. A short BOOT press cancels calibration; it also times out after 90 seconds. Do not hold BOOT while applying power unless you want the ESP32 download mode.

## Hardware

This build targets the original CYD with **ILI9341** LCD and **XPT2046** resistive touch, not every board sold as “ESP32 with display”. The connected board's previous firmware identified itself as `Marauder vCYD`; its ESP32-D0WD-V3 has 4 MB flash. Confirm the screen visually after flashing.

| Connection | GPIO |
|---|---|
| LCD SCLK / MOSI / MISO | 14 / 13 / 12 |
| LCD CS / DC / backlight | 15 / 2 / 21 |
| Touch SCLK / MOSI / MISO | 25 / 32 / 39 |
| Touch CS / IRQ | 33 / 36 |
| BOOT | 0 |

The two-USB CYD variant can use ST7789 and needs a different panel configuration. The display driver contains a `FLOWSIGHT_ST7789` build option, but this variant is not hardware verified here.

## Build and install

Install Python 3 and run from this repository:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m platformio run
.\.venv\Scripts\python -m platformio run --target upload --upload-port COM3
```

PlatformIO keeps its toolchain inside `.local/platformio`. Compilation output is in `.pio`. On Linux/macOS use `.venv/bin/python` and the appropriate `/dev/ttyUSB…` port.

For the **first replacement of Marauder**, clear flash only after building successfully. This erases the previous firmware and its settings:

```powershell
.\.venv\Scripts\python -m esptool --port COM3 erase-flash
.\.venv\Scripts\python -m platformio run --target upload --upload-port COM3
```

Do not erase flash during normal updates if you want to retain timer settings and calibration.

## Local USB control

```powershell
.\.venv\Scripts\python tools/device.py --port COM3 status
.\.venv\Scripts\python tools/device.py --port COM3 start
.\.venv\Scripts\python tools/device.py --port COM3 pause
.\.venv\Scripts\python tools/device.py --port COM3 resume
.\.venv\Scripts\python tools/device.py --port COM3 reset
.\.venv\Scripts\python tools/device.py --port COM3 duration 45
.\.venv\Scripts\python tools/device.py --port COM3 screen artifacts/device-screen.png
```

Only one process can own the serial port. Close serial monitors before uploading or using this tool. The tool leaves DTR/RTS inactive on open to avoid intentionally restarting the timer.

The device accepts newline-delimited JSON at 115200 baud. A request such as `{"cmd":"pause","id":7}` receives a `response` with the same ID, timer state and an `ok` flag. Commands: `status`, `start`, `pause`, `resume`, `reset`, `mode` (`value`: `focus` / `break`), `duration` (`minutes`), `calibrate`, `home` and `screen`. Invalid commands and changes to active-session duration are rejected. `tap` (`x`, `y`) is a USB automation command; it does not count as physical touch evidence.

The screenshot is a **snapshot rendered by the ESP32 itself**, sent over USB. It uses the same frozen timer state and two RGB565 strip buffers that draw the LCD. It verifies firmware rendering; it is not a photograph of the LCD and does not prove panel colors, orientation or touch alignment.

## Desktop integration boundary

This release runs its own timer. It **does not yet synchronize the timer or history of the FlowSight desktop application**. The USB protocol is ready for a desktop adapter, but no existing desktop API is assumed and no FlowSight database is edited.

## Source and licensing

The source is licensed under AGPL-3.0, consistent with FlowSight's open-source edition. Dependencies retain their licenses: Arduino-ESP32, LovyanGFX and ArduinoJson. `Display.h` documents hardware configuration; `Timer.h` is a hardware-independent state machine; `src/main.cpp` implements native rendering, input, persistence and USB control. Technical verification is recorded separately in `docs/VERIFICATION.md`.

Manrope is bundled under SIL OFL 1.1. The generated font subsets in `include/Fonts.h` are ready to compile. To regenerate them, install `Pillow==11.2.1` and run `python tools/make_fonts.py`.

`python tools/merge_firmware.py` produces a single firmware image at `firmware/FlowSight-ESP32.bin`, written at **address 0x0**. Do not write that merged image at 0x10000. Downloadable images are distributed through GitHub Releases instead of storing build outputs in Git history.

The firmware runs the hardware-independent timer assertions on the ESP32 at startup. `python tools/verify_device.py --port COM3 --fresh-device` performs the USB integration checks, including a real one-minute session and a device reset. This test resets the timer and completed-session count; use it only on a fresh test device.
