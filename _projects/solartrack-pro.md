---
title: "A solar tracker from my Computer Organization course"
kisa: An Arduino prototype that finds the sun with four light sensors and turns the panel with two servos.
ozet: "I built a dual-axis solar tracker for my Computer Organization course. In this prototype, running on four light sensors and two servo motors, servo jitter was the issue that took the most time."
date: 2026-08-07
teknolojiler: [Arduino, C++, LDR sensors, SG90 servo, Serial communication]
repo: https://github.com/hasancrlk/SolarTrack-Pro
kategori: donanim
sira: 10
ref: solartrack
---

A fixed solar panel faces the sun squarely only during part of the day.
Turning the panel with the sun is a direct way to get more energy from the
same panel. SolarTrack Pro is a prototype that applies this on two axes
(left-right and up-down), developed for my Computer Organization course.

## Hardware

- Arduino Uno R3
- 4 LDR light sensors (left, right, up, down)
- Voltage dividers with 10K resistors for the LDRs
- 2 SG90 micro servos and a dual-axis pan-tilt mechanism
- 4.2V 100mA solar panel, breadboard and jumper wires

## How it works

The four sensors sit on the four sides of the panel. When the sun is straight
ahead, opposite sensors read the same light level. As the sun moves, one side
receives more light and the panel turns towards it. On the horizontal axis
the difference between the left and right sensors is used:

```cpp
int yatayFark = sol - sag;   // horizontal difference: left - right
if (yatayFark > ESIK && yatayAci < YATAY_MAX) {
  yatayAci += ADIM;
} else if (yatayFark < -ESIK && yatayAci > YATAY_MIN) {
  yatayAci -= ADIM;
}
```

The vertical axis applies the same logic with the up and down sensors.

## Servo jitter

The issue that took the most time in the prototype was servo jitter. LDR
readings constantly show small fluctuations. When the code reacts to every
difference between sensors, the servo moves back and forth even when the
panel is already in the right position.

The code has two constants against this:

- **Threshold (`ESIK = 30`):** the servo doesn't move until the difference
  between opposite sensors exceeds this value, so measurement noise doesn't
  turn into movement.
- **Step (`ADIM = 1` degree):** the panel turns only one degree per loop.
  Larger steps can cause oscillation around the target.

Servo angles are also limited to 0–180 degrees so the mechanism isn't
strained.

## Operating modes

On cloudy days light is diffuse and the sensors don't point in a clear
direction; at night there is nothing to track. In those cases the panel is
locked in the centre instead of wandering. Modes are changed with commands
over the serial port:

- `MODE_SUN`: active tracking.
- `MODE_CLOUD` and `MODE_NIGHT`: servos locked at 90°/90°.
- `CENTER`: centres the servos.
- `STOP` / `START`: pauses or resumes movement.
- `DELAY_<ms>`: sets the sensor read interval between 10 and 500 ms.

On every loop the board writes sensor values and servo angles to the serial
port, so the output can be read and plotted by a dashboard.

## Possible improvements

- Choosing cloud and night mode automatically from the total light level.
- Measuring the panel's voltage and comparing it with a fixed panel. That
  comparison would show the efficiency gain in numbers.
