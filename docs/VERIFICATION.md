# Technical verification — 2026-10-11

## Attached device and installation

The USB adapter enumerated as CH340 on COM3. Espressif's ROM loader identified ESP32-D0WD-V3 revision 3.1 and 4 MB flash. The previous application identified itself as `Marauder vCYD`. The firmware targets the original ESP32-2432S028R / ILI9341 / XPT2046 pinout; the display's exact silkscreen model was not independently read.

The first installation erased the entire flash, removing Marauder and its settings. The final merged image was written at address 0x0 using 230400 baud, and esptool verified its data hash. Subsequent application startup and USB requests succeeded.

Build: PlatformIO 6.2.0, Espressif32 6.12.0, Arduino-ESP32 2.0.17, LovyanGFX 1.2.7, ArduinoJson 7.4.2. Static RAM usage is 24,560 bytes. Application flash usage is 447,017 of 1,966,080 bytes. The renderer uses a 76,800-byte RGB565 strip buffer, drawing two 320 × 120 strips to cover the 320 × 240 LCD. This avoids the classic ESP32's contiguous-allocation limit. Approximately 262 KB total free heap was reported after the integration checks.

Merged image: `firmware/FlowSight-ESP32.bin`, 512,912 bytes.

SHA-256: `07dfe89fd6a395a527a4f300a9706c8cc570ca7fe67a79384bdca240c634e275`

## Behavioral results

The timer state-machine assertions ran on the real Xtensa CPU, covering millisecond-accurate pause/resume, duration boundaries, exact-deadline completion, single counting, focus/break distinction, unsigned millisecond wrap, saved-state validation and duplicate start handling.

`tools/verify_device.py --port COM3 --fresh-device` passed 17 integration checks:

- Invalid zero and over-limit durations are rejected.
- Resuming an idle session is rejected.
- The countdown follows elapsed wall time, freezes exactly while paused, and continues after resume.
- Duration and mode changes cannot silently discard a paused session.
- Reset opens a confirmation; cancelling preserves the running session; confirming resets it.
- Settings +5 and -5 actions change the duration through the visible button hit regions.
- A real one-minute session reaches zero, enters the complete state and counts once.
- The completion action starts the break mode.
- A hardware reset restores the exact saved paused checkpoint.

The test session count was cleared. The device was left idle in focus mode at 25:00, with a five-minute break configured.

The finish review requested that mode changes explicitly name their destination. After that copy-only correction, the firmware was rebuilt and flashed; both focus-to-break and break-to-focus confirmations were exercised on the device, their resulting states were checked, and the original reset confirmation was recaptured. The reviewer scored that one fix resolved. No whole-panel hardware approval is implied by that verdict.

## Display and touch evidence limits

Six images were captured from the ESP32's own native renderer: idle timer, paused timer, reset confirmation, settings and both mode-change confirmations. Text, Spanish glyphs, layout and action labels were inspected. A capture re-renders the same frozen timer state through the same two strip buffers used to draw the LCD; it is not a photograph of the physical panel.

An optional SPI readback comparison returned **0 of 6 matching pixels**. This is not a successful panel-memory verification and may indicate unsupported readback or a hardware/configuration difference. Do not use the renderer screenshots as proof of physical panel colors or orientation.

Physical touch alignment and panel appearance require an in-person check. The USB `tap` tests invoke real button action handlers but intentionally do not increment `touch_count`; they are not physical sensor tests. At the end of automated verification, `touch_count` was zero and custom touch calibration was not yet saved. A user confirmation request was sent. If touch alignment is wrong, hold BOOT for 1.5 seconds after startup and complete the four-point calibration.

This release does not synchronize with the FlowSight desktop application's timer or history. It exposes a documented USB control protocol for a future adapter.
