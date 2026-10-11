# Design

The device keeps FlowSight's slate surface, warm white text and teal action color. Manrope is bundled locally. The compact Operate layout gives the app's clock the largest type, followed by its state and goal. Calendar context is a single line with UTF-8-safe truncation. The primary and stop controls are 44 pixels high.

Canvas: 320 × 240 landscape. Colors: background #101d25, secondary surface #1a2c36, text #e5f0f1, secondary text #adbec8, accent #6cdfd0, outline #2a414b. Body type 15 px, titles 22 px; the 72 px clock font scales to fit the app's HH:MM:SS or Pomodoro MM:SS string.

Render through a single 320 × 120 RGB565 sprite twice per frame to fit the classic ESP32's contiguous heap. The device never extrapolates the app clock. Pending requests show Applying in FlowSight; rejected or timed-out actions ask the user to check the app. Offline controls are outlined and disabled.

Touch activates on release, requires a minimum 35 ms press, and cancels on sliding away. A change in the offered app action cancels an in-flight primary press. A saved four-point affine transform aligns touch with the corrected panel orientation. Firmware updates keep this calibration.

All app labels arrive translated. Local settings, confirmations, calibration and connection copy use the same English/Spanish preference. Screenshots in artifacts are actual firmware-rendered test snapshots, not photographs.
