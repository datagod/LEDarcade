# =====================================================================================
# WHEEL CLOCK — HH:MM:SS on six identical digit wheels
#
# Every digit is its own reel. New figures come over the top and land in
# the HH:MM:SS window. Tens/ones roll independently (odometer style).
# Fonts: arcade (3×5), round (5×5), seven (7-seg), plus TTF faces from fonts/.
# Random bright color at each launch.
#
# Run:  python3 WheelClock.py
#       python3 WheelClock.py arcade|round|seven|anton|bebas|terminal|checkbook
#       python3 WheelClock.py cycle
# Idle rotation: clock slot "wheelclock" (5 min).
# =====================================================================================

from __future__ import annotations

import math
import os
import random
import sys
import time
from datetime import datetime

import LEDarcade as LED

try:
    import pygame
    HAS_PYGAME = True
except Exception:
    HAS_PYGAME = False


TARGET_FPS = 50
ROLL_SEC = 0.46
FONT = "arcade"      # default face; override with argv
FONT_HOLD_SEC = 12   # seconds per face in cycle mode

DIGIT_COLORS = (
    ("gold",    (255, 214, 64)),
    ("red",     (255, 36, 36)),
    ("orange",  (255, 140, 16)),
    ("lime",    (72, 255, 48)),
    ("cyan",    (16, 220, 255)),
    ("magenta", (255, 48, 196)),
    ("blue",    (64, 112, 255)),
    ("white",   (255, 255, 255)),
)
DIGIT_RGB = DIGIT_COLORS[0][1]
WELL_RGB = (8, 8, 12)
RAIL_RGB = (36, 34, 42)
RIM_RGB = (70, 62, 48)

# H1 0-2, H2 0-9, M1 0-5, M2 0-9, S1 0-5, S2 0-9
MODULI = (3, 10, 6, 10, 6, 10)

_SEG_A, _SEG_B, _SEG_C, _SEG_D = 0x01, 0x02, 0x04, 0x08
_SEG_E, _SEG_F, _SEG_G = 0x10, 0x20, 0x40
_SEG_MASKS = (0x3F, 0x06, 0x5B, 0x4F, 0x66, 0x6D, 0x7D, 0x07, 0x7F, 0x6F)

# 5×5 rows, bit 4 = leftmost
_ROUND_5X5 = (
    (0b01110, 0b10001, 0b10001, 0b10001, 0b01110),
    (0b01100, 0b00100, 0b00100, 0b00100, 0b01110),
    (0b01110, 0b10001, 0b00110, 0b01000, 0b11111),
    (0b11110, 0b00001, 0b01110, 0b00001, 0b11110),
    (0b10010, 0b10010, 0b11111, 0b00010, 0b00010),
    (0b11111, 0b10000, 0b11110, 0b00001, 0b11110),
    (0b01110, 0b10000, 0b11110, 0b10001, 0b01110),
    (0b11111, 0b00001, 0b00010, 0b00100, 0b00100),
    (0b01110, 0b10001, 0b01110, 0b10001, 0b01110),
    (0b01110, 0b10001, 0b01111, 0b00001, 0b01110),
)

_TTF_FACES = (
    ("anton", "Anton-Regular.ttf"),
    ("bebas", "BebasNeue-Regular.ttf"),
    ("terminal", "3270Condensed-Regular.ttf"),
    ("checkbook", "CHECKBK0.TTF"),
)


class FontFace(object):
    def __init__(self, name, width, height, grids, pair_gap, colon_gap):
        self.name = name
        self.width = int(width)
        self.height = int(height)
        self.grids = grids
        self.pair_gap = int(pair_gap)
        self.colon_gap = int(colon_gap)


def _stop(StopEvent):
    try:
        return StopEvent is not None and StopEvent.is_set()
    except Exception:
        return False


def _ease_out(t):
    t = 0.0 if t < 0.0 else 1.0 if t > 1.0 else t
    return 1.0 - (1.0 - t) ** 3


def _now_digits():
    n = datetime.now()
    s = n.strftime("%H%M%S")
    return tuple(int(c) for c in s)


def _mul(rgb, k):
    k = 0.0 if k < 0.0 else 1.0 if k > 1.0 else k
    return (int(rgb[0] * k), int(rgb[1] * k), int(rgb[2] * k))


def _gaps_for(dw, dh, vw, vh):
    if dh > vh - 2:
        return None
    for pair, colon in ((1, 2), (1, 1), (0, 1), (0, 0)):
        if 6 * dw + 3 * pair + 2 * colon <= vw:
            return pair, colon
    return None


def _expand(grid, fw, fh, zoom):
    w, h = fw * zoom, fh * zoom
    out = [0] * (w * h)
    for y in range(fh):
        for x in range(fw):
            if not grid[y * fw + x]:
                continue
            for zv in range(zoom):
                for zh in range(zoom):
                    out[(y * zoom + zv) * w + (x * zoom + zh)] = 1
    return w, h, out


def _bitmap_font(name, grids, fw, fh, vw, vh):
    best = None
    for z in range(1, 9):
        dw, dh = fw * z, fh * z
        gaps = _gaps_for(dw, dh, vw, vh)
        if gaps is None:
            break
        best = (z, gaps[0], gaps[1])
    if best is None:
        return None
    z, pair, colon = best
    out = []
    for g in grids:
        _, _, exp = _expand(g, fw, fh, z)
        out.append(exp)
    return FontFace(name, fw * z, fh * z, out, pair, colon)


def _rows_to_grid(rows, bits):
    h = len(rows)
    g = []
    for row in rows:
        for x in range(bits):
            g.append(1 if (row >> (bits - 1 - x)) & 1 else 0)
    return g


def _arcade_grids():
    return [list(LED.DigitList[i]) for i in range(10)]


def _round_grids():
    return [_rows_to_grid(_ROUND_5X5[d], 5) for d in range(10)]


def _seven_grid(digit, w=5, h=9, t=1):
    grid = [0] * (w * h)
    mid = h // 2
    hx0, hx1 = t, w - 1 - t
    mask = _SEG_MASKS[int(digit) % 10]

    def hseg(x0, x1, y):
        for x in range(x0, x1 + 1):
            grid[y * w + x] = 1

    def vseg(x, y0, y1):
        for y in range(y0, y1 + 1):
            grid[y * w + x] = 1

    if mask & _SEG_A:
        hseg(hx0, hx1, 0)
    if mask & _SEG_G:
        hseg(hx0, hx1, mid)
    if mask & _SEG_D:
        hseg(hx0, hx1, h - t)
    if mask & _SEG_F:
        vseg(0, t, mid - 1)
    if mask & _SEG_B:
        vseg(w - t, t, mid - 1)
    if mask & _SEG_E:
        vseg(0, mid + t, h - 1 - t)
    if mask & _SEG_C:
        vseg(w - t, mid + t, h - 1 - t)
    return grid


def _seven_grids():
    return [_seven_grid(d) for d in range(10)]


def _measure_text(draw, font, ch):
    try:
        bb = draw.textbbox((0, 0), ch, font=font)
        return bb, max(1, bb[2] - bb[0]), max(1, bb[3] - bb[1])
    except Exception:
        tw, th = font.getsize(ch)
        return (0, 0, tw, th), max(1, tw), max(1, th)


def _ttf_font(name, filename, vw, vh):
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        return None
    path = LED.ResolveFontPath(filename)
    if not path or not os.path.isfile(path):
        return None
    probe = Image.new("L", (96, 96), 0)
    draw = ImageDraw.Draw(probe)
    chosen = None
    for size in range(28, 7, -1):
        try:
            font = ImageFont.truetype(path, size)
        except Exception:
            return None
        dw = dh = 1
        for d in "0123456789":
            _, cw, ch = _measure_text(draw, font, d)
            dw = max(dw, cw)
            dh = max(dh, ch)
        gaps = _gaps_for(dw, dh, vw, vh)
        if gaps is None:
            continue
        chosen = (font, dw, dh, gaps[0], gaps[1])
        break
    if chosen is None:
        return None
    font, dw, dh, pair, colon = chosen
    grids = []
    for d in "0123456789":
        img = Image.new("L", (dw, dh), 0)
        dr = ImageDraw.Draw(img)
        bb, cw, ch = _measure_text(dr, font, d)
        x = (dw - cw) // 2 - bb[0]
        y = (dh - ch) // 2 - bb[1]
        dr.text((x, y), d, font=font, fill=255)
        pix = img.load()
        g = []
        for yy in range(dh):
            for xx in range(dw):
                g.append(1 if pix[xx, yy] > 96 else 0)
        grids.append(g)
    return FontFace(name, dw, dh, grids, pair, colon)


def _build_fonts(vw, vh):
    fonts = []
    for face in (
        _bitmap_font("arcade", _arcade_grids(), 3, 5, vw, vh),
        _bitmap_font("round", _round_grids(), 5, 5, vw, vh),
        _bitmap_font("seven", _seven_grids(), 5, 9, vw, vh),
    ):
        if face is not None:
            fonts.append(face)
    for name, filename in _TTF_FACES:
        face = _ttf_font(name, filename, vw, vh)
        if face is not None:
            fonts.append(face)
    return fonts


def _pick_font(fonts, choice):
    if not fonts:
        return None, False
    key = (choice or FONT or "arcade").strip().lower()
    if key in ("cycle", "all", "rotate"):
        return fonts[0], True
    for i, face in enumerate(fonts):
        if face.name == key:
            return fonts[i], False
    print("[WheelClock] unknown font '{}'  try: {}".format(
        key, " ".join(f.name for f in fonts),
    ))
    return fonts[0], False


def _blit_digit(canvas, grid, fw, fh, h, v, rgb, clip_top, clip_bot, shade_cy, shade_r):
    r0, g0, b0 = rgb
    vw = int(getattr(LED, "HatWidth", 64) or 64)
    vh = int(getattr(LED, "HatHeight", 32) or 32)
    inv_r = 1.0 / shade_r if shade_r > 0.5 else 1.0
    y0 = int(round(v))
    x0 = int(h)
    for count in range(fw * fh):
        if not grid[count]:
            continue
        y, x = divmod(count, fw)
        px = x0 + x
        py = y0 + y
        if px < 0 or px >= vw or py < clip_top or py >= clip_bot:
            continue
        ny = (py - shade_cy) * inv_r
        if ny < -1.0:
            ny = -1.0
        elif ny > 1.0:
            ny = 1.0
        fall = math.cos(ny * math.pi * 0.5)
        k = 0.18 + 0.82 * fall * fall
        canvas.SetPixel(px, py, int(r0 * k), int(g0 * k), int(b0 * k))


def _fill_rect(canvas, x0, y0, x1, y1, rgb):
    vw = int(getattr(LED, "HatWidth", 64) or 64)
    vh = int(getattr(LED, "HatHeight", 32) or 32)
    r, g, b = rgb
    for y in range(max(0, y0), min(vh, y1)):
        for x in range(max(0, x0), min(vw, x1)):
            canvas.SetPixel(x, y, r, g, b)


def _layout(vw, face):
    dw = face.width
    dh = face.height
    pair = face.pair_gap
    colon = face.colon_gap
    total = 6 * dw + 3 * pair + 2 * colon
    x = max(0, (vw - total) // 2)
    xs = []
    for g in range(3):
        xs.append(x)
        x += dw + pair
        xs.append(x)
        x += dw
        if g < 2:
            x += colon
    return xs, dw, dh, x


class DigitWheel(object):
    """One 0..(mod-1) reel. Next digit drops in from the top and lands."""

    def __init__(self, modulus=10):
        self.mod = max(2, int(modulus))
        self.shown = 0
        self.incoming = 0
        self.t = 1.0

    def _wrap(self, d):
        return int(d) % self.mod

    def set_digit(self, d):
        d = self._wrap(d)
        if d == self.incoming:
            return
        if self.t < 1.0:
            self.shown = self.incoming
        self.incoming = d
        self.t = 0.0

    def tick(self, dt):
        if self.t < 1.0:
            self.t = min(1.0, self.t + dt / ROLL_SEC)
            if self.t >= 1.0:
                self.shown = self.incoming

    def draw(self, canvas, x, land_y, face, clip_top, clip_bot):
        h = face.height
        shade_cy = land_y + h * 0.5
        shade_r = h * 0.72
        u = _ease_out(self.t)

        if self.t < 1.0:
            cards = (
                (self._wrap(self.incoming + 1), -2.0 + u),
                (self.incoming,                 -1.0 + u),
                (self.shown,                     0.0 + u),
                (self._wrap(self.shown - 1),     1.0 + u),
            )
        else:
            cards = (
                (self._wrap(self.shown + 1), -1.0),
                (self.shown,                  0.0),
                (self._wrap(self.shown - 1),  1.0),
            )

        for d, slot in cards:
            y = land_y + slot * h
            if y + h < clip_top or y >= clip_bot:
                continue
            dist = abs(slot)
            dim = 1.0 if dist < 0.15 else max(0.28, 1.0 - 0.55 * dist)
            _blit_digit(
                canvas, face.grids[int(d) % 10], face.width, face.height,
                x, y, _mul(DIGIT_RGB, dim),
                clip_top, clip_bot, shade_cy, shade_r,
            )


def _draw_housing(canvas, x0, x1, digit_xs, colon_gap, vw, vh):
    _fill_rect(canvas, x0, 0, x1, vh, WELL_RGB)
    _fill_rect(canvas, x0, 0, x0 + 1, vh, RAIL_RGB)
    _fill_rect(canvas, x1 - 1, 0, x1, vh, RAIL_RGB)
    for y in range(0, vh, 4):
        canvas.SetPixel(x0, y, *RIM_RGB)
        canvas.SetPixel(x1 - 1, y, *RIM_RGB)

    # rails only between HH | MM | SS (the old colon slots)
    if colon_gap > 0:
        for i in (2, 4):
            sx = digit_xs[i] - 1
            if 0 <= sx < vw:
                for y in range(vh):
                    canvas.SetPixel(sx, y, *RAIL_RGB)


def _apply_face(vw, vh, face):
    xs, dw, dh, x_end = _layout(vw, face)
    well_x0 = max(0, xs[0] - 1)
    well_x1 = min(vw, x_end + 1)
    land_y = max(0, (vh - dh) // 2)
    print("[WheelClock] font={}  {}x{}  pair={} colon={}".format(
        face.name, dw, dh, face.pair_gap, face.colon_gap,
    ))
    return xs, dw, dh, well_x0, well_x1, land_y


def PlayWheelClock(Duration=0, StopEvent=None, FontName=None):
    global DIGIT_RGB
    vw = int(getattr(LED, "HatWidth", 64) or 64)
    vh = int(getattr(LED, "HatHeight", 32) or 32)
    color_name, DIGIT_RGB = random.choice(DIGIT_COLORS)
    print("[WheelClock] color={} {}".format(color_name, DIGIT_RGB))

    fonts = _build_fonts(vw, vh)
    if not fonts:
        print("[WheelClock] no fonts available")
        return
    print("[WheelClock] {}x{}  fonts: {}".format(
        vw, vh, " ".join(f.name for f in fonts),
    ))

    choice = FontName if FontName is not None else FONT
    face, cycling = _pick_font(fonts, choice)
    font_i = fonts.index(face)
    xs, dw, dh, well_x0, well_x1, land_y = _apply_face(vw, vh, face)

    canvas = getattr(LED, "Canvas", None)
    if canvas is None and getattr(LED, "TheMatrix", None) is not None:
        canvas = LED.TheMatrix.CreateFrameCanvas()
        LED.Canvas = canvas

    wheels = [DigitWheel(m) for m in MODULI]
    digits = _now_digits()
    for i, d in enumerate(digits):
        wheels[i].shown = wheels[i].incoming = wheels[i]._wrap(d)
        wheels[i].t = 1.0

    clock = pygame.time.Clock() if HAS_PYGAME else None
    start = time.time()
    last = start
    font_t = start
    frame_dt = 1.0 / TARGET_FPS

    try:
        while True:
            if _stop(StopEvent):
                print("[WheelClock] StopEvent")
                return
            if Duration and float(Duration) > 0:
                if (time.time() - start) >= float(Duration) * 60.0:
                    print("[WheelClock] Duration reached")
                    return

            now = time.time()
            dt = now - last
            last = now
            if dt <= 0:
                dt = frame_dt
            dt = min(dt, 2.0 * frame_dt)

            if HAS_PYGAME:
                try:
                    for event in pygame.event.get():
                        if event.type != pygame.KEYDOWN:
                            continue
                        nxt = event.key in (
                            pygame.K_SPACE, pygame.K_n, pygame.K_RIGHT,
                        )
                        prv = event.key in (pygame.K_p, pygame.K_LEFT)
                        if nxt or prv:
                            cycling = False
                            font_i = (font_i + (1 if nxt else -1)) % len(fonts)
                            face = fonts[font_i]
                            xs, dw, dh, well_x0, well_x1, land_y = _apply_face(
                                vw, vh, face,
                            )
                            font_t = now
                except Exception:
                    pass

            if cycling and (now - font_t) >= FONT_HOLD_SEC:
                font_i = (font_i + 1) % len(fonts)
                face = fonts[font_i]
                xs, dw, dh, well_x0, well_x1, land_y = _apply_face(vw, vh, face)
                font_t = now

            digits = _now_digits()
            for i, d in enumerate(digits):
                wheels[i].set_digit(d)
                wheels[i].tick(dt)

            if canvas is None:
                time.sleep(frame_dt)
                continue
            canvas.Fill(0, 0, 0)
            _draw_housing(canvas, well_x0, well_x1, xs, face.colon_gap, vw, vh)
            for i, w in enumerate(wheels):
                w.draw(canvas, xs[i], land_y, face, 0, vh)
            canvas = LED.TheMatrix.SwapOnVSync(canvas)
            LED.Canvas = canvas

            if clock is not None:
                clock.tick(TARGET_FPS)
            else:
                time.sleep(max(0.0, frame_dt - (time.time() - now)))
    except KeyboardInterrupt:
        print("[WheelClock] Interrupted")


def LaunchWheelClock(Duration=0, ShowIntro=True, StopEvent=None, FontName=None):
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
    PlayWheelClock(Duration=Duration, StopEvent=StopEvent, FontName=FontName)


if __name__ == "__main__":
    try:
        font = sys.argv[1] if len(sys.argv) > 1 else None
        LaunchWheelClock(Duration=0, FontName=font)
    except KeyboardInterrupt:
        print("Exiting WheelClock.")
