# Product

FlowSight ESP32 is an Operate surface: a physical touchscreen control and glanceable status display for a running FlowSight desktop app. It mirrors the app's timer, daily goal, status, language, mode and calendar context over USB. The app owns tracking, Pomodoro transitions and protection rules.

The supported unit is a CS-32 N4XX with a 320 × 240 landscape LCD and XPT2046 resistive touch. One USB-C cable carries power and serial data. The confirmed board profile uses GPIO27 backlight and shared SPI.

Primary actions are explicit start/pause/resume/end-break requests. Stop and mode changes require local confirmation. Disconnection freezes the last reading and disables session actions. Brightness and calibration remain usable locally. English/Spanish follow the app.
