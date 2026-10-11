# FlowSight ESP32 project log

## Scope

The owner requested replacing Marauder with a FlowSight touchscreen companion, publishing its repository, and fully integrating its timer, controls and language with the installed desktop app. They explicitly authorized desktop changes and a FlowSight.AI release.

## Hardware correction

The connected COM3 unit identifies as ESP32-D0WD-V3 with 4 MB flash. Its case says CS-32 N4XX and it has one USB-C connector. The initial GPIO21 CYD profile produced a dark screen. The ESP32-2432S024R-compatible GPIO27 profile with ILI9341_2 and shared XPT2046 SPI illuminated it. Landscape offset rotation 6 corrected mirroring. The owner confirmed readable text, then completed four-point calibration and confirmed correct touch response. Preserve that NVS calibration during updates.

## Integration

The initial autonomous countdown was superseded by protocol 2. Firmware 0.2.0 takes the app's clock verbatim and sends explicit control requests. It freezes on disconnect and stores only local language, brightness and calibration preferences. No Wi-Fi is required.

Desktop work is isolated in `desktop-source`, branch `feat/esp32-companion`, based on the released 6.1.0 tree. The original Desktop checkout has pre-existing changes and was not edited. FlowSight 6.1.1 adds a Windows serial worker and renderer event transport, reusing existing monitoring, Pomodoro, calendar and localization behavior.

Desktop source commit: `1a29553`; merged through PR https://github.com/Mancasvel/FlowSight.AI/pull/37 at `f4204f6`. Compatible release build https://github.com/Mancasvel/FlowSight.AI/actions/runs/38171382104 passed. Version 6.1.1 was installed from its verified installer payload; only `app.exe` and `dump_tool_schemas.exe` differed from the existing installation. Other resources matched byte-for-byte. Existing MCP processes and the user's profile were preserved.

## Verification and delivery

See `docs/VERIFICATION.md` for evidence. Renderer tests, Rust unit tests, native lint, frontend build and desktop release checks passed. The owner confirmed that physical play/pause controls the app. A real serial snapshot matched the app's paused reading, daily goal and Spanish labels.

Settings initially missed the owner's physical touch at (269, 49), three pixels below its original rectangle. The isolated header hit area was widened for both Settings and Back, and local touches no longer cancel on unrelated timer changes. The corrected firmware passed all 17 device protocol checks, including that exact coordinate, and was flashed without erasing saved calibration.

The release includes a merged image for blank boards and an application-only image for updates that preserve calibration. Keep current source, final firmware and minimal evidence; remove temporary build caches after successful delivery.
