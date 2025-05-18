
# ┌────────────────────────────────────────────────────────────────────────────┐
# │   FILE:        analog_clock.py                                             │
# │   TYPE:        Real-Time Analog Clock Display for 64x32 RGB Matrix         │
# │   PROJECT:     LEDarcade (https://github.com/datagod/LEDarcade)            │
# │                                                                            │
# │   ARCHITECT:   William McEvoy (github.com/datagod)                         │
# │   CODE AUTHOR: ChatGPT-4 (OpenAI) — custom GPT named LEDarcade             │
# │                                                                            │
# │ ────────────────────────────────────────────────────────────────────────── │
# │                                                                            │
# │  DESCRIPTION:                                                              │
# │  This script renders a beautiful and functional analog clock on a 64x32    │
# │  RGB LED matrix panel using trigonometric line drawing and high-color      │
# │  pixel rendering. Designed to run as a standalone module, it leverages     │
# │  the full graphical power of the LEDarcade engine.                         │
# │                                                                            │
# │  The display includes:                                                     │
# │   - A full circular 12-hour face                                           │
# │   - Distinctly colored hour, minute, and second hands                      │
# │   - Smooth updates every second                                            │
# │   - Gamma-corrected colors from LEDarcade’s palette                        │
# │                                                                            │
# │  This module celebrates minimalist design and retro pixel aesthetics       │
# │  while honoring precise timing and visual clarity.                         │
# │                                                                            │
# │ ───────────────────────────────────────────────────────────────────────────│
# │                                                                            │
# │  DEPENDENCIES:                                                             │
# │   • LEDarcade (imported as LED)                                            │
# │   • Python ≥ 3.7                                                           │
# │   • Raspberry Pi with RGBMatrix hardware                                   │
# │                                                                            │
# │  USAGE:                                                                    │
# │   $ python3 analog_clock.py                                                │
# │                                                                            │
# │ ────────────────────────────────────────────────────────────────────────── │
# │                                                                            │
# │  \"Time is an illusion — except in pixels.\"                               │
# │                                                                            │
# └────────────────────────────────────────────────────────────────────────────┘


import time
from datetime import datetime
import math
import LEDarcade as LED
LED.Initialize()
#LED.InitializeColors()
#LED.TheMatrix.brightness = 100  # force brightness again
LED.ClearBigLED()
LED.ClearBuffers()



# Constants
CENTER_X = 32
CENTER_Y = 16
RADIUS = 14

def draw_line(x0, y0, x1, y1, color):
    dx, dy = x1 - x0, y1 - y0
    steps = max(abs(dx), abs(dy))
    if steps == 0:
        LED.setpixelCanvas(int(x0), int(y0), *color)
        return
    x_inc = dx / steps
    y_inc = dy / steps
    x, y = x0, y0
    for _ in range(int(steps)):
        LED.setpixelCanvas(int(round(x)), int(round(y)), *color)
        x += x_inc
        y += y_inc

def draw_face():
    for hour in range(12):
        angle = math.pi / 6 * hour
        x = int(CENTER_X + RADIUS * math.sin(angle))
        y = int(CENTER_Y - RADIUS * math.cos(angle))
        LED.setpixelCanvas(x, y, 100, 100, 100)

def draw_hands(now):
    # Hour hand
    h_angle = math.radians((now.hour % 12 + now.minute / 60) * 30)
    draw_line(CENTER_X, CENTER_Y, CENTER_X + int(7 * math.sin(h_angle)), CENTER_Y - int(7 * math.cos(h_angle)), LED.HighRed)

    # Minute hand
    m_angle = math.radians((now.minute + now.second / 60) * 6)
    draw_line(CENTER_X, CENTER_Y, CENTER_X + int(10 * math.sin(m_angle)), CENTER_Y - int(10 * math.cos(m_angle)), LED.HighGreen)

    # Second hand
    s_angle = math.radians(now.second * 6)
    draw_line(CENTER_X, CENTER_Y, CENTER_X + int(13 * math.sin(s_angle)), CENTER_Y - int(13 * math.cos(s_angle)), LED.HighBlue)

def run_clock():
    LED.ClearBuffers()
    LED.ClearBigLED()
    draw_face()
    while True:
        LED.ClearBuffers()
        draw_face()
        draw_hands(datetime.now())
        LED.Canvas = LED.TheMatrix.SwapOnVSync(LED.Canvas)
        time.sleep(1)

if __name__ == "__main__":
    run_clock()
