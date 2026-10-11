# Verification — protocol 2

The prior standalone-timer verification does not apply to firmware 0.2.0. This version mirrors a running FlowSight app.

## Confirmed hardware

- Connected CS-32 N4XX, ESP32-D0WD-V3, 4 MB flash, CH340 on COM3.
- GPIO27 backlight and shared LCD/touch SPI illuminated the screen; the GPIO21 profile did not.
- Landscape offset rotation 6 corrected mirroring. The owner confirmed readable orientation.
- Raw touch was initially misaligned. Four-point calibration was completed, saved, and the owner confirmed correct touch response. Firmware status reported `touch_calibrated: true` and physical touch counts.

## Application checks

- FlowSight desktop integration reuses the existing timer, translated labels, calendar context, and monitoring controls.
- Renderer suite passed; additional focused tests cover exact clock/goal snapshots, language publication, Pomodoro break actions, overlapping controls and stale action rejection.
- Windows Rust suite: 288 passed, 2 pre-existing ignored.
- Vite production build and release manifest consistency passed.
- Native lint with all targets/features and warnings denied passed.
- Actual ESP32 protocol checks: 15 passed, including exact snapshot clock/goal, explicit start/pause, duplicate prevention, English/Spanish changes, Pomodoro clock, malformed input, disconnect freeze and reconnect.
- Firmware built and flashed at 230400 baud with verified flash hash. App image: 454,304 bytes; merged bootable image: 519,840 bytes. Static RAM: 28,480 bytes. Runtime status after update retained touch calibration and showed 259,108 bytes free heap.
- The four current framebuffer captures were inspected together for layout, labels, control states and text clipping.
- The desktop release build and live-app verification are still pending.

`tools/verify_device.py` drives the actual firmware through a test host. Its captures are device-rendered fixtures. They establish firmware layout and transport behavior; they do not establish a live app reading or independently prove physical touch alignment.
