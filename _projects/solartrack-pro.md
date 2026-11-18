---
title: "A panel that follows the sun: a dual-axis solar tracker with Arduino"
kisa: An Arduino prototype that finds the sun with four light sensors and turns the panel with two servos.
ozet: "I built a solar panel prototype that follows the sun with four light sensors and two servo motors. The code is short, but it taught me real-world problems like sensor noise, thresholds and operating modes."
date: 2026-08-07
teknolojiler: [Arduino, C++, LDR sensors, SG90 servo, Serial communication]
repo: https://github.com/hasancrlk/SolarTrack-Pro
kategori: donanim
sira: 10
ref: solartrack
---

## The idea

A fixed solar panel faces the sun squarely only at one time of day. Turning
the panel with the sun is the most direct way to get more energy out of the
same panel. SolarTrack Pro is a small prototype that does this on two axes
(left-right and up-down).

## Hardware

- Arduino Uno R3
- 4 LDR light sensors: left, right, up, down
- 10K resistors (voltage dividers for the LDRs)
- 2 SG90 micro servos and a dual-axis pan-tilt mechanism
- 4.2V 100mA solar panel, breadboard and jumper wires

## How it works

Four sensors surround the panel on four sides. When the sun is straight ahead,
opposite sensors see the same light. As the sun moves, one side stays brighter
and the panel turns towards it:

```cpp
int yatayFark = sol - sag;   // horizontal difference: left - right
if (yatayFark > ESIK && yatayAci < YATAY_MAX) {
  yatayAci += ADIM;
} else if (yatayFark < -ESIK && yatayAci > YATAY_MIN) {
  yatayAci -= ADIM;
}
```

The vertical axis uses the same logic with the up and down sensors.

## Two small but important settings

**Threshold (`ESIK = 30`).** Without a threshold, the servo jitters back and
forth at the slightest noise in the sensor readings. Not moving until the
difference exceeds a certain value protects both the motor and the energy
budget.

**Step (`ADIM = 1` degree).** The panel turns one degree at a time instead of
in large jumps. The motion is smooth and it doesn't oscillate around the
target. Servo limits (0–180 degrees) keep the mechanism from straining.

## Operating modes and serial commands

Tracking all the time doesn't make sense. On cloudy days light is diffuse, and
at night there is none. In those cases it is better to lock the panel in the
centre than let it wander:

| Command | Effect |
|---|---|
| `MODE_SUN` | Sun mode: active tracking |
| `MODE_CLOUD` | Cloud mode: servos locked at 90°/90° |
| `MODE_NIGHT` | Night mode: servos locked at 90°/90° |
| `CENTER` | Centre the servos |
| `STOP` / `START` | Pause / resume movement |
| `DELAY_<ms>` | Change the sensor read interval (10–500 ms) |

On every loop the board prints sensor values and servo angles over serial, so
a dashboard can read and plot them. The output looks like this (example
values):

```
Sol:612 Sag:540 Yukari:701 Asagi:655 | YatayAci:94 DikeyAci:91
```

## Next time

Mode changes are manual for now. Picking night and cloud mode automatically
from the total light level is the natural next step. Measuring the panel's
voltage and comparing it with a fixed panel would show, in numbers, how much
efficiency the system actually gains.

## What I learned

In software a condition is either true or false. In the sensor world every
reading is a little noisy. Two small constants, threshold and step, made the
difference between a jittery prototype and a system that works smoothly.
