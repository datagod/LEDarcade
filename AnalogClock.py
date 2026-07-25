
# ┌────────────────────────────────────────────────────────────────────────────┐
# │   FILE:        AnalogClock.py                                              │
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
# │  USAGE (standalone):                                                       │
# │   $ python AnalogClock.py                                                  │
# │                                                                            │
# │  USAGE (LEDcommander): import only — call RunClock(Duration, StopEvent).   │
# │  Do NOT call LED.Initialize() at import time (crashes LEDsim shm races).   │
# │                                                                            │
# └────────────────────────────────────────────────────────────────────────────┘


import time
from datetime import datetime
import math

# Constants (panel is 64x32; face centered)
CENTER_X = 32
CENTER_Y = 16
RADIUS = 14


def draw_line(LED, x0, y0, x1, y1, color):
    dx, dy = x1 - x0, y1 - y0
    steps = max(abs(dx), abs(dy))
    if steps == 0:
        LED.setpixelCanvas(int(x0), int(y0), *color)
        return
    x_inc = dx / steps
    y_inc = dy / steps
    x, y = float(x0), float(y0)
    for _ in range(int(steps) + 1):
        LED.setpixelCanvas(int(round(x)), int(round(y)), *color)
        x += x_inc
        y += y_inc


def draw_face(LED):
    for hour in range(12):
        angle = math.pi / 6 * hour
        x = int(CENTER_X + RADIUS * math.sin(angle))
        y = int(CENTER_Y - RADIUS * math.cos(angle))
        LED.setpixelCanvas(x, y, 100, 100, 100)


def _hand_color(LED, name, fallback):
    c = getattr(LED, name, None)
    if c is None:
        return fallback
    if isinstance(c, (tuple, list)) and len(c) >= 3:
        return (int(c[0]), int(c[1]), int(c[2]))
    return fallback


def draw_hands(LED, now):
    # Hour hand
    h_angle = math.radians((now.hour % 12 + now.minute / 60.0) * 30.0)
    draw_line(
        LED,
        CENTER_X,
        CENTER_Y,
        CENTER_X + int(7 * math.sin(h_angle)),
        CENTER_Y - int(7 * math.cos(h_angle)),
        _hand_color(LED, "HighRed", (255, 0, 0)),
    )

    # Minute hand
    m_angle = math.radians((now.minute + now.second / 60.0) * 6.0)
    draw_line(
        LED,
        CENTER_X,
        CENTER_Y,
        CENTER_X + int(10 * math.sin(m_angle)),
        CENTER_Y - int(10 * math.cos(m_angle)),
        _hand_color(LED, "HighGreen", (0, 255, 0)),
    )

    # Second hand
    s_angle = math.radians(now.second * 6.0)
    draw_line(
        LED,
        CENTER_X,
        CENTER_Y,
        CENTER_X + int(13 * math.sin(s_angle)),
        CENTER_Y - int(13 * math.cos(s_angle)),
        _hand_color(LED, "HighBlue", (0, 0, 255)),
    )


def RunClock(Duration=10, StopEvent=None):
    """
    Draw the analog face until StopEvent or Duration minutes elapse.

    Duration is in *minutes* (same as LEDcommander clock commands).
    Caller (LEDcommander) must already have called LED.Initialize().
    """
    import LEDarcade as LED

    try:
        run_minutes = float(Duration)
    except (TypeError, ValueError):
        run_minutes = 10.0
    if run_minutes <= 0:
        run_minutes = 10.0

    try:
        LED.ClearBuffers()
    except Exception:
        pass
    try:
        LED.ClearBigLED()
    except Exception:
        pass

    start = time.time()
    print(
        f"[AnalogClock] Running for {run_minutes:g} minute(s) "
        f"(StopEvent={'yes' if StopEvent is not None else 'no'})"
    )

    while True:
        if StopEvent is not None and StopEvent.is_set():
            print("\n" + "=" * 40)
            print("[AnalogClock] StopEvent received")
            print("-> Shutting down gracefully...")
            print("=" * 40 + "\n")
            break

        elapsed_min = (time.time() - start) / 60.0
        if elapsed_min >= run_minutes:
            print(f"[AnalogClock] Duration reached ({run_minutes:g} min) — exiting.")
            break

        try:
            LED.ClearBuffers()
            draw_face(LED)
            draw_hands(LED, datetime.now())
            LED.Canvas = LED.TheMatrix.SwapOnVSync(LED.Canvas)
        except Exception as exc:
            print(f"[AnalogClock] frame error: {exc}")
            # Keep running; a single bad frame should not kill the clock
            time.sleep(1)
            continue

        # Interruptible sleep so StopEvent is responsive
        deadline = time.time() + 1.0
        while time.time() < deadline:
            if StopEvent is not None and StopEvent.is_set():
                break
            time.sleep(0.05)


if __name__ == "__main__":
    import LEDarcade as LED

    LED.Initialize()
    RunClock(Duration=10, StopEvent=None)
