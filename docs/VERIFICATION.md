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
- Actual ESP32 protocol checks: 24 passed, including exact snapshot clock/goal, explicit start/pause, duplicate prevention, English/Spanish changes, Pomodoro clock, malformed input, disconnect freeze, reconnect, Settings/Back at the measured physical coordinate (269, 49), brightness cycling, mode confirmation/cancellation, and offline brightness/calibration.
- Firmware built and flashed at 230400 baud with verified flash hash. App image: 455,136 bytes; merged bootable image: 520,672 bytes. Static RAM: 28,504 bytes. Runtime status after update retained touch calibration and showed 259,068 bytes of free heap.
- The four current framebuffer captures were inspected together for layout, labels, control states and text clipping.
- FlowSight 6.1.1 release build and all PR checks passed. Installed app files match the verified release installer payload. The original profile and daily total were preserved.
- Live desktop and device readings matched after an actual tracking/pause cycle, including the six-hour goal, Spanish labels and paused action. The owner confirmed physical play/pause controlled the app.
- The header target was widened after the real sensor reported Settings touches just below the original button rectangle. The same correction applies to Back. Only the primary action's in-flight touch is cancelled when app state changes.
- Follow-up settings correction confirms the initial button with two samples, tolerates an isolated displaced sample at release, and cancels deliberate dragging. Eleven compiled native gesture scenarios passed, including redraw delays and timer wrap-around. Settings and calibration no longer repaint for unrelated app clock updates. Local gestures also survive connection changes.
- The updated firmware was installed without erasing NVS. Physical Settings/Back/Brightness confirmation from the owner is still pending; serial button commands and gesture unit tests do not replace this check.
- FlowSight 6.1.1 is public. The public updater manifest reports 6.1.1, contains a signature and points to a working installer URL (HTTP 200). The duplicate publication build was cancelled after the identical source had already passed the full release build.

`tools/verify_device.py` drives the actual firmware through a test host. Its captures are device-rendered fixtures. They establish firmware layout and transport behavior; they do not establish a live app reading or independently prove physical touch alignment.
