# =====================================================================================
# NIXIE CLOCK — four IN-12 style tubes, HH:MM
#
# Neon-orange cathodes, glass bulb, stem, bakelite socket, stacked ghosts,
# bloom. Digits snap like real nixies; a brief flicker before each change.
# Idle rotation: clock slot "nixieclock" (5 min).
#
# Run:  python3 NixieClock.py
# =====================================================================================

from __future__ import annotations

import math
import time
from datetime import datetime

import LEDarcade as LED

try:
    import pygame
    HAS_PYGAME = True
except Exception:
    HAS_PYGAME = False


TARGET_FPS = 30

LIT = (127, 39, 7)
GLOW = (70, 16, 3)
GAS = (22, 7, 2)
GHOST = (42, 12, 4)
GLASS = (12, 10, 14)
GLASS_HL = (52, 46, 56)
GLASS_RIM = (28, 24, 32)
CASE = (5, 2, 1)
BASE = (72, 42, 18)
SOCKET = (48, 28, 12)
PIN = (24, 16, 8)
COLON = (255, 70, 12)

TUBE_W = 14
TUBE_H = 32
DIGIT_W = 5
DIGIT_H = 9
ZOOM = 2
PAIR_GAP = 1
COLON_GAP = 4
CHANGE_LEAD = 0.70   # seconds of extra shimmer before a cathode snaps

# 5×9 cathode shapes (bit 4 = leftmost)
_DIGITS = (
    (0b01110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110),
    (0b00100, 0b01100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110),
    (0b01110, 0b10001, 0b00001, 0b00010, 0b00100, 0b01000, 0b10000, 0b10000, 0b11111),
    (0b01110, 0b10001, 0b00001, 0b00110, 0b00001, 0b00001, 0b00001, 0b10001, 0b01110),
    (0b00010, 0b00110, 0b01010, 0b10010, 0b10010, 0b11111, 0b00010, 0b00010, 0b00010),
    (0b11111, 0b10000, 0b10000, 0b11110, 0b00001, 0b00001, 0b00001, 0b10001, 0b01110),
    (0b01110, 0b10001, 0b10000, 0b11110, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110),
    (0b11111, 0b00001, 0b00010, 0b00010, 0b00100, 0b00100, 0b01000, 0b01000, 0b01000),
    (0b01110, 0b10001, 0b10001, 0b01110, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110),
    (0b01110, 0b10001, 0b10001, 0b10001, 0b01111, 0b00001, 0b00001, 0b10001, 0b01110),
)


def _stop(StopEvent):
    try:
        return StopEvent is not None and StopEvent.is_set()
    except Exception:
        return False


def _now_digits(n=None):
    if n is None:
        n = datetime.now()
    s = n.strftime("%H%M")
    return tuple(int(c) for c in s)


def _time_to_change(i, n):
    """Seconds until tube i (H1 H2 M1 M2) switches cathode."""
    frac = n.microsecond / 1e6
    s = n.second + frac
    m = n.minute
    h = n.hour
    until_minute = 60.0 - s
    if i == 3:
        return until_minute
    if i == 2:
        return (9 - (m % 10)) * 60.0 + until_minute
    if i == 1:
        return (59 - m) * 60.0 + until_minute
    if h < 10:
        left = 10 - h
    elif h < 20:
        left = 20 - h
    else:
        left = 24 - h
    return (left - 1) * 3600.0 + (59 - m) * 60.0 + until_minute


def _flicker_for(i, now, n):
    base = 0.93 + 0.07 * math.sin(now * 11.0 + i * 1.7)
    remain = _time_to_change(i, n)
    if remain >= CHANGE_LEAD:
        return base
    u = 1.0 - remain / CHANGE_LEAD
    spark = math.sin(now * 41.0 + i * 2.1) * math.sin(now * 103.0 + i)
    dip = 0.40 if math.sin(now * 67.0 + i * 4.0) < -0.62 else 1.0
    f = (base + 0.28 * u * spark) * (1.0 - 0.12 * u) * dip
    if f < 0.42:
        f = 0.42
    elif f > 1.12:
        f = 1.12
    return f


def _layout(vw, vh):
    total = 4 * TUBE_W + 2 * PAIR_GAP + COLON_GAP
    x = max(0, (vw - total) // 2)
    xs = []
    colons = []
    for g in range(2):
        xs.append(x)
        x += TUBE_W + PAIR_GAP
        xs.append(x)
        x += TUBE_W
        if g == 0:
            colons.append(x + COLON_GAP // 2)
            x += COLON_GAP
    y = max(0, (vh - TUBE_H) // 2)
    return xs, colons, y


def _add(buf, x, y, rgb, vw, vh):
    if x < 0 or y < 0 or x >= vw or y >= vh:
        return
    r, g, b = buf[y][x]
    nr = r + rgb[0]
    ng = g + rgb[1]
    nb = b + rgb[2]
    buf[y][x] = (
        255 if nr > 255 else nr,
        255 if ng > 255 else ng,
        255 if nb > 255 else nb,
    )


def _set(buf, x, y, rgb, vw, vh):
    if x < 0 or y < 0 or x >= vw or y >= vh:
        return
    buf[y][x] = rgb


def _mul(rgb, k):
    if k < 0.0:
        k = 0.0
    elif k > 1.0:
        k = 1.0
    return (int(rgb[0] * k), int(rgb[1] * k), int(rgb[2] * k))


def _digit_pixels(d, ox, oy, zoom=ZOOM):
    rows = _DIGITS[int(d) % 10]
    out = []
    for y, row in enumerate(rows):
        for x in range(DIGIT_W):
            if not (row & (1 << (DIGIT_W - 1 - x))):
                continue
            for zv in range(zoom):
                for zh in range(zoom):
                    out.append((ox + x * zoom + zh, oy + y * zoom + zv))
    return out


def _half_w(ly):
    """Horizontal half-width of the tube at local y. Full-height nixie profile."""
    # 0-2   dome
    # 3-19  bulb
    # 20-23 taper / stem
    # 24-28 socket
    # 29-31 pins
    if ly <= 2:
        return 5.0 + ly * 1.2          # 5.0 → 7.4
    if ly <= 19:
        return 6.6
    if ly <= 23:
        t = (ly - 19) / 4.0
        return 6.6 * (1.0 - 0.45 * t)  # 6.6 → 3.6
    if ly <= 28:
        return 5.4
    return 2.2


def _draw_tube(buf, x0, y0, digit, flicker, vw, vh):
    cx = x0 + TUBE_W * 0.5
    max_hw = TUBE_W * 0.5 - 0.2

    # glass + gas, following the tube silhouette
    for ly in range(TUBE_H):
        hw = min(max_hw, _half_w(ly))
        y = y0 + ly
        for x in range(x0, x0 + TUBE_W):
            dx = abs((x + 0.5) - cx)
            if dx > hw:
                continue
            edge = hw - dx
            if ly >= 29:
                _set(buf, x, y, PIN if dx < 1.6 else CASE, vw, vh)
                continue
            if ly >= 24:
                _set(buf, x, y, SOCKET if edge > 0.6 else BASE, vw, vh)
                continue
            # glass body
            if edge < 1.15:
                rgb = GLASS_HL if (x + 0.5) < cx else GLASS_RIM
                _set(buf, x, y, rgb, vw, vh)
            else:
                _set(buf, x, y, GLASS, vw, vh)
                _add(buf, x, y, _mul(GAS, flicker), vw, vh)
            # left specular
            if (x + 0.5) < cx and edge < 2.2 and ly <= 20:
                _add(buf, x, y, _mul(GLASS_HL, 0.55), vw, vh)

    # mica spacer under the digit
    mica_y = y0 + 22
    for x in range(x0 + 3, x0 + TUBE_W - 3):
        _add(buf, x, mica_y, SOCKET, vw, vh)

    dw = DIGIT_W * ZOOM
    digit_x = int(round(cx - dw * 0.5))
    digit_y = y0 + 3

    # stacked unused cathodes
    for gd, dx, dy, k in (
        ((digit + 3) % 10,  0, -1, 0.70),
        ((digit + 7) % 10,  1,  1, 0.50),
        ((digit + 1) % 10, -1,  0, 0.40),
    ):
        ghost = _mul(GHOST, k * flicker)
        for px, py in _digit_pixels(gd, digit_x + dx, digit_y + dy):
            if py >= mica_y:
                continue
            _add(buf, px, py, ghost, vw, vh)

    lit = _mul(LIT, flicker)
    glow = _mul(GLOW, flicker)
    pts = _digit_pixels(digit, digit_x, digit_y)
    bloom = ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, 1), (1, -1), (-1, -1))
    for px, py in pts:
        if py >= mica_y:
            continue
        for ox, oy in bloom:
            _add(buf, px + ox, py + oy, glow, vw, vh)
        _add(buf, px, py, lit, vw, vh)

    # two pins under the socket
    pin_y = y0 + TUBE_H - 1
    _set(buf, int(cx) - 3, pin_y, PIN, vw, vh)
    _set(buf, int(cx) + 2, pin_y, PIN, vw, vh)


def _draw_colon(buf, cx, y0, flicker, vw, vh):
    """Two tiny neon separator lamps."""
    rgb = _mul(COLON, flicker)
    glow = _mul(GLOW, flicker)
    for by in (y0 + 8, y0 + 16):
        for oy in range(-1, 3):
            for ox in range(-1, 2):
                _add(buf, cx + ox, by + oy, glow, vw, vh)
        for oy in range(2):
            for ox in range(2):
                _add(buf, cx - 1 + ox, by + oy, rgb, vw, vh)


def PlayNixieClock(Duration=0, StopEvent=None):
    vw = int(getattr(LED, "HatWidth", 64) or 64)
    vh = int(getattr(LED, "HatHeight", 32) or 32)
    print("[NixieClock] {}x{}  nixie HH:MM".format(vw, vh))

    canvas = getattr(LED, "Canvas", None)
    if canvas is None and getattr(LED, "TheMatrix", None) is not None:
        canvas = LED.TheMatrix.CreateFrameCanvas()
        LED.Canvas = canvas

    xs, colons, y0 = _layout(vw, vh)
    clock = pygame.time.Clock() if HAS_PYGAME else None
    start = time.time()
    frame_dt = 1.0 / TARGET_FPS

    try:
        while True:
            if _stop(StopEvent):
                print("[NixieClock] StopEvent")
                return
            if Duration and float(Duration) > 0:
                if (time.time() - start) >= float(Duration) * 60.0:
                    print("[NixieClock] Duration reached")
                    return

            now = time.time()
            n = datetime.now()
            digits = _now_digits(n)
            buf = [[CASE for _ in range(vw)] for _ in range(vh)]

            for i, d in enumerate(digits):
                flicker = _flicker_for(i, now, n)
                _draw_tube(buf, xs[i], y0, d, flicker, vw, vh)

            cf = 0.90 + 0.10 * math.sin(now * 9.0)
            for cx in colons:
                _draw_colon(buf, cx, y0, cf, vw, vh)

            if canvas is None:
                time.sleep(frame_dt)
                continue
            canvas.Fill(0, 0, 0)
            for y in range(vh):
                row = buf[y]
                for x in range(vw):
                    r, g, b = row[x]
                    if r or g or b:
                        canvas.SetPixel(x, y, r, g, b)
            canvas = LED.TheMatrix.SwapOnVSync(canvas)
            LED.Canvas = canvas

            if clock is not None:
                clock.tick(TARGET_FPS)
            else:
                time.sleep(max(0.0, frame_dt - (time.time() - now)))
    except KeyboardInterrupt:
        print("[NixieClock] Interrupted")


def LaunchNixieClock(Duration=0, ShowIntro=True, StopEvent=None):
    try:
        LED.LoadConfigData()
    except Exception:
        pass
    LED.Initialize()
    try:
        LED.ClearBigLED()
        LED.ClearBuffers()
    except Exception:
        pass
    if _stop(StopEvent):
        return
    PlayNixieClock(Duration=Duration, StopEvent=StopEvent)


if __name__ == "__main__":
    try:
        LaunchNixieClock(Duration=0)
    except KeyboardInterrupt:
        print("Exiting NixieClock.")
