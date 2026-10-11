# FlowSight ESP32 project log

## Implementation strategy

Use a separate firmware repository for the connected CYD, preserving the existing FlowSight desktop source and its uncommitted work. Build a native offline timer with a USB control protocol rather than assuming the desktop application has an available control API.

Hardware identification: CH340 USB serial, ESP32-D0WD-V3 revision 3.1, 4 MB flash. Read-only inspection of the previous application identified `Marauder vCYD`. The target configuration is ESP32-2432S028R with ILI9341 and XPT2046 on separate SPI buses. A 921600-baud read proved unreliable; subsequent device operations use 230400 baud for flashing and 115200 for the application protocol.

The interface inherits the desktop dark palette and uses native Manrope subsets with Spanish glyphs. UI actions activate on release, cancel when dragged outside a target, and distinguish reset confirmation from the current running session. A nonblocking four-point affine touch calibration validates the fourth point before saving. BOOT provides an independent fallback control.

Timer decisions: use monotonic milliseconds with wrap-safe subtraction; preserve remaining time across pauses; count completion once; restore a checkpoint in paused state after power loss; reject duration/mode changes that would silently discard an active block. Persist running checkpoints every 30 seconds to limit flash writes.

Hardware correction: a full 320 × 240 RGB565 sprite could not obtain a sufficiently large contiguous allocation. The final renderer uses one 320 × 120 RGB565 buffer and draws the top and bottom strips sequentially, preserving color depth and antialiased typography. USB screenshots re-render that same frozen state on the ESP32 through those buffers. The application then started successfully and passed the recorded behavioral checks.

## Deliverable paths

- `src/`, `include/`, `platformio.ini`: editable firmware.
- `tools/device.py`: USB control and live framebuffer capture.
- `tools/verify_device.py`, `test/timer_test.cpp`: behavioral verification.
- `assets/fonts/`: source font and its license.
- `firmware/FlowSight-ESP32.bin`: generated merged installation image, excluded from Git and distributed as a release asset.
- `artifacts/device-screen.png`: current device framebuffer evidence.
- `docs/VERIFICATION.md`: actual verification outcomes and limitations.

Development dependencies, partial firmware reads, temporary references and build caches are local-only and are removed after the final firmware is verified and published.
