---
name: FlowSight ESP32
description: FlowSight's dark visual family on a native touchscreen timer.
colors:
  primary: "#6cdfd0"
  primary-pressed: "#35bfae"
  neutral-bg: "#101d25"
  neutral-surface: "#1a2c36"
  neutral-ink: "#e5f0f1"
  neutral-muted: "#adbec8"
  neutral-line: "#2a414b"
typography:
  display:
    fontFamily: "Manrope"
    fontSize: "72px"
  title:
    fontFamily: "Manrope"
    fontSize: "22px"
  body:
    fontFamily: "Manrope"
    fontSize: "15px"
rounded:
  control: "10px"
  stroke: "2px"
spacing:
  edge: "12px"
  pair-gap: "8px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.neutral-bg}"
    typography: "{typography.body}"
    rounded: "{rounded.control}"
  button-primary-pressed:
    backgroundColor: "{colors.primary-pressed}"
    textColor: "{colors.neutral-bg}"
  button-secondary:
    backgroundColor: "{colors.neutral-surface}"
    textColor: "{colors.neutral-ink}"
    typography: "{typography.body}"
    rounded: "{rounded.control}"
  button-secondary-pressed:
    backgroundColor: "{colors.neutral-line}"
    textColor: "{colors.neutral-ink}"
  button-disabled:
    backgroundColor: "{colors.neutral-bg}"
    textColor: "{colors.neutral-muted}"
    typography: "{typography.body}"
    rounded: "{rounded.control}"
  navigation-button:
    backgroundColor: "{colors.neutral-surface}"
    textColor: "{colors.neutral-ink}"
    typography: "{typography.body}"
    rounded: "{rounded.control}"
    width: "72px"
    height: "44px"
---

# Design System: FlowSight ESP32

## Overview

**Creative North Star: "FlowSight on the small display"**

The implemented interface extends the FlowSight desktop visual family onto a small physical display. A dark slate canvas, pale type and a clear teal action keep the timer dominant. Compact controls use plain Spanish labels and visible state feedback.

The native surface has a fixed landscape frame. Hierarchy comes from type size, spacing and tonal separation; screen changes are immediate, with no decorative motion.

**Key Characteristics:**

- A dominant clock with quieter mode, session count and status text.
- Teal actions and selected modes, supported by explicit wording.
- Rounded controls with visible pressed and disabled states.

Source authority: `src/main.cpp`, `include/Display.h` and the generated subsets in `include/Fonts.h`. The six `artifacts/device-*.png` captures show framebuffer rendering; physical LCD orientation and touch alignment remain unconfirmed. The sidecar's HTML/CSS components and synthesized tonal ramps are documentation previews, not firmware or hardware evidence.

## Colors

The palette has one teal accent and a closely related family of dark slate neutrals. Frontmatter values preserve the RGB source constants; RGB565 rendering quantizes them on the device.

### Primary

- **FlowSight Teal** (`primary`): primary actions, selected mode, mode label, progress fill, calibration target and the two-stroke mark.
- **Pressed Teal** (`primary-pressed`): immediate feedback while a primary control is held.

### Neutral

- **Dark Slate Canvas** (`neutral-bg`): full-screen background and dark labels on teal controls.
- **Slate Surface** (`neutral-surface`): secondary controls.
- **Pale Ink** (`neutral-ink`): clock, headings and enabled secondary labels.
- **Muted Blue-Gray** (`neutral-muted`): supporting text, session count and disabled labels.
- **Slate Line** (`neutral-line`): progress track, disabled outlines and pressed secondary controls.

**The Written State Rule.** Color complements the mode, status and action label; it does not replace them.

## Typography

**Display Font:** Manrope, embedded as `FontClock`.
**Body Font:** Manrope, embedded as `FontBody` and `FontTitle`.

The firmware uses antialiased VLW subsets. `tools/make_fonts.py` requests weight 600 from the bundled Manrope font. There is no runtime font stack or browser fallback in ordinary screens.

### Hierarchy

- **Display:** the `display` token supplies the centered countdown; its subset contains only digits and a colon. Three-digit minute values render at 0.8 scale to fit.
- **Title:** the `title` token supplies the brand name, screen and confirmation headings, and duration value.
- **Body:** the `body` token supplies controls, mode, session count and supporting copy. Its subset includes Spanish accents and inverted punctuation.

Text is positioned directly and wrapping is disabled. The earlier design record requested tabular numerals, but the shipped clock subset has proportional digit advances. This remains an implementation limitation, not a new typography rule.

## Layout

The rendered canvas is fixed at 320 × 240 px in landscape. Content generally aligns to the `edge` inset; paired settings controls share the `pair-gap` spacing. There are no responsive breakpoints or scrolling containers.

The timer places brand and settings above the mode and session count, then the centered clock, one status line, a thin progress bar and bottom actions. Settings and confirmations reuse the same margins and bottom control alignment. Main timer actions are 50 px tall; settings and navigation controls are at least 44 px tall, with 48 px duration controls.

The complete frame is rendered in two 320 × 120 RGB565 strips using one reusable 76,800-byte sprite. Keep coordinates in the full-screen space and subtract the current strip offset when drawing. This avoids requiring a contiguous 153,600-byte framebuffer; the strip boundary is not a visual divider.

## Elevation & Depth

The surface is flat and has no shadows, blur or translucent overlays. Solid slate controls separate from the darker canvas through tone. Confirmation replaces the screen; it is not a floating card or dimmed modal.

## Shapes

Controls use the softly rounded `control` radius. The thinner `stroke` radius rounds the progress bar and the two short offset strokes of the FlowSight mark. Enabled buttons are solid fills; disabled buttons add a thin outline. Calibration uses a circle and crosshair.

## Components

### Buttons

Direct, readable and consistent. Labels are centered within their full touch rectangles. Primary controls use teal with a dark label; secondary controls use slate with pale text. Disabled controls use the canvas fill, muted text and a slate outline, and are excluded from hit testing.

**The Release Rule.** Touching down changes the fill; release activates after a minimum 35 ms press. Sliding off cancels the action, and sliding back does not reactivate it.

The timer's primary label follows the phase: `Empezar`, `Pausar`, `Reanudar`, then `Descansar` or `Volver al foco` on completion. Completion waits for the user's action. `Reiniciar` is disabled while idle. The native device has no hover or keyboard-focus styling.

### Navigation

`Ajustes` and `Volver` are explicit top-right secondary buttons, using the `navigation-button` geometry. Settings offer `Foco` and `Descanso` as a paired selection with teal marking the current mode. Utility controls expose `Calibrar táctil` and `Brillo`.

### Duration controls

The centered minute value sits between `-5` and `+5`. Adjustments are bounded to 1–180 minutes for focus and 1–60 for break, and are disabled during a running or paused block. The supporting message explains when the block must be reset. Saved settings persist; a saved running session restores paused after power loss.

### Confirmation

**The Protected Change Rule.** Resetting or changing mode during a running or paused block requires an explicit on-device confirmation.

The title names the operation: `¿Reiniciar sesión?`, `¿Cambiar a foco?` or `¿Cambiar a descanso?`. The explanation states `Se descartará el tiempo de este bloque.` and `Tus sesiones completadas se conservan.` Bottom actions pair secondary `Cancelar` with primary `Reiniciar` or `Cambiar`, matching the requested operation.

### Clock and progress

The clock carries the greatest visual weight. The elapsed fraction appears below the status as a 4 px teal fill within a slate track. Both update with timer state; no easing or decorative transition is implemented.

## Do's and Don'ts

### Do:

- **Do** preserve FlowSight's dark slate and teal identity on this device.
- **Do** use explicit Spanish labels and keep each state understandable in words.
- **Do** retain touch targets at least 44 px tall and release-to-activate behavior.
- **Do** preserve the complete composition across both rendering strips.

### Don't:

- **Don't** reduce clock prominence to accommodate decorative content.
- **Don't** discard an active or paused block from touch controls without confirmation.
- **Don't** start the next focus or break block automatically on completion.
- **Don't** treat framebuffer captures as proof of physical LCD or touch alignment.
