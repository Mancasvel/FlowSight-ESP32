# FlowSight ESP32

<!-- impeccable:product-schema 1 -->

## Platform

Embedded ESP32 touchscreen, connected to a computer by USB or powered independently.

## Users and purpose

The owner of FlowSight wants a simplified physical version of the timer on the connected ESP32, replacing Marauder. The device must show time clearly and provide useful touch controls for starting, pausing, resuming and resetting a session.

## Capabilities and constraints

Native firmware, offline operation, USB controls, configurable focus and break durations. The desktop FlowSight application does not currently expose a verified timer-control API; USB protocol support must not be presented as an existing desktop integration. No cloud account or network credentials are needed. Hardware is identified from the attached board before flashing.

## Brand commitments

Inherit the FlowSight desktop identity: Manrope / Plus Jakarta Sans where supported, teal accents and slate surfaces. Interface copy is Spanish. Keep the timer dominant and touch controls easy to hit.

## Implementation decisions

Arduino C++ with PlatformIO and LovyanGFX, selected for a native SPI display and resistive touch. No browser runtime runs on the ESP32.
