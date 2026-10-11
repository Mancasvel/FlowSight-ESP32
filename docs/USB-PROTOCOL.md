# USB protocol 2

115200 baud, 8N1. UTF-8 JSON lines, maximum 4095 input bytes before the newline. Oversized lines are discarded through the next newline. DTR/RTS stay inactive during normal app attachment. Quit FlowSight before a serial monitor, flashing tool or diagnostic client opens the port.

The host sends `{"cmd":"hello"}`. Compatible firmware answers with `event: "hello"`, `product: "flowsight-esp32"`, `protocol: 2` and `version: "0.2.0"`. No state is sent before the identity check.

The host sends a snapshot approximately every 500 ms:

```json
{"cmd":"sync","state":{"language":"es","mode":"normal","mode_label":"Normal","kind":"Registrado hoy","clock":"01:47:22","status":"Listo","phase":"ready","total_seconds":6442,"goal_seconds":21600,"goal_label":"Objetivo diario","goal_value":"6 horas","context":"Calendario conectado","primary_action":"start","primary_label":"Iniciar registro","primary_enabled":true,"stop_enabled":false,"mode_enabled":true,"busy":false}}
```

The firmware acknowledges with `event: "synced"` and the optional request `id`, plus its received `clock`, `language`, `phase`, physical `touch_count` and `touch_calibrated` for diagnostics. Snapshot size is bounded to 3000 bytes in the desktop transport. The clock is copied verbatim, never advanced on the ESP32. Five seconds without a valid snapshot freezes the last reading and disables controls.

A physical action sends `{"event":"control","id":1,"action":"pause"}`. IDs increase across the current device boot. Actions are `start`, `pause`, `resume`, `stop`, `end_break`, `mode_normal`, `mode_pomodoro`. The desktop serial worker deduplicates IDs within each connection. Its renderer checks current availability and explicit action identity before invoking the app's existing control. Completion returns `{"cmd":"ack","id":1,"ok":true}`. This acknowledgement does not change the device's timer state; only the next snapshot does. No optimistic or offline control replay occurs.

Only one control can be pending on the device. An acknowledgement timeout after eight seconds clears the waiting state and displays a message. App startup or protection flows can still require interaction on the PC.

## Diagnostics

`status`, `home`, `calibrate`, and `tap` respond with `event: "response"`, `ok`, and the supplied `id`. Status includes app state, connection freshness, pending ID, physical `touch_count`, last mapped/raw coordinates, calibration status, brightness and free heap. `tap` invokes the visible enabled button at integer `x`, `y` and does not increment physical touch counts.

`screen` returns `event: "frame"`, the supplied `id`, width 320, height 240 and format `rgb565-rle-le`. It is followed by little-endian uint16 pairs `(run length, RGB565 pixel)` until 76,800 pixels are decoded, then a newline. It renders the same frozen state through the LCD's two-strip renderer. This is framebuffer evidence, not a photograph of the panel.

Legacy standalone commands such as start, reset or duration are not accepted. App control originates through explicit firmware button events and is executed by FlowSight.
