# USB protocol

115200 baud, 8N1. Requests are UTF-8 JSON objects terminated by a newline, up to 383 bytes without the newline. Responses echo the numeric `id`. The serial monitor must be closed before opening another connection.

```json
{"cmd":"duration","minutes":25,"id":1}
{"cmd":"start","id":2}
{"cmd":"pause","id":3}
{"cmd":"resume","id":4}
{"cmd":"status","id":5}
```

`phase` is `idle`, `running`, `paused` or `complete`. The remaining time is reported both as `remaining_ms` and ceiling-rounded `seconds`. `mode` is `focus` or `break`. Completion is counted once, only for focus sessions. `start` continues a paused session; `resume` rejects idle or complete sessions. `reset` is an explicit command that discards the current block without resetting completed-session history.

Duration and mode changes reject active or paused sessions. Reset first if discarding that block is intended. `clear_sessions` resets the lifetime completion count only when idle/complete and accompanied by `"confirm":true`.

Additional events include `ready`, `action`, `completed`, `state`, `calibrated`, `calibration_error`, `calibration_timeout` and `selftest`. The device periodically emits `state` while it has a recent USB request. `status` includes physical `touch_count`, most recent mapped/raw coordinates, current view and whether a custom touch calibration is saved.

`tap` invokes the visible button at `x`, `y` for UI automation. It intentionally does **not** increment physical `touch_count`. `calibrate` enters a nonblocking, four-point calibration screen; `home` exits it. A valid calibration maps raw XPT2046 coordinates through an affine transform and validates a fourth point before saving.

`screen` returns a JSON `frame` header with width 320, height 240 and format `rgb565-rle-le`. It is followed by pairs of little-endian unsigned 16-bit `(run length, RGB565 pixel)` until 76,800 pixels are decoded, then a newline. The ESP32 renders the same frozen state through the same two strip buffers used for the LCD; this is not a photograph of the panel. The provided Python client validates bounds and encodes a PNG without imaging dependencies.

No network service is exposed by this firmware. Pairing/authentication for any future network bridge belongs in that bridge; the current control boundary is access to the physical USB serial port.

`panel_check` reads six pixels back from the LCD controller over SPI and compares them with the framebuffer. `panel_readback_matches` is `-1` before the first check, then 0–6. A match verifies display-controller memory communication, not physical viewing angle, backlight quality or touch alignment. Some panel variants may not support readback.
