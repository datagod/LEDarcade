# =====================================================================================
# LASER CLOCK — HH:MM forged one dot at a time
#
# The time exists as a shape on a black field and stays invisible until a laser
# reaches it. One beam stays on at full green (0, 255, 0) and sweeps every dot that
# needs to change: left to right, top to bottom, across all of those digits.
# Each dot is blasted into view and throws sparks that arc, fall, and bounce.
# The dot cools from white-hot to red.
# The nozzle at the source fades into and out of existence.
# The weekday is on its own line. The month and day share the line under it.
# Each weld starts from a random corner of the panel.
# A blue two-pixel mark travels the outer edge, one sixtieth per second,
# fading in and out as it moves. At :00 it sits in the center of the top edge.
# A few seconds before the minute, the beam goes out. A digit that is about
# to change falls backwards on its own, slams on the ledge above that caption,
# and shatters into dark particles. Then the beam welds the new one.
#
# A "dot" is one cell of a 5×7 clock font, drawn as a 2×2 block so the strike
# reads as a single hot pixel on a 64×32 panel.
#
# Idle rotation: clock slot "laserclock" (5 min), between the other clocks.
# The whole picture fades in when the clock starts and fades out when it stops.
#
# Run:  python3 LaserClock.py
#       LEDpanel / action "laserclock" / ?laserclock
# =====================================================================================

from __future__ import annotations

import math
import random
import time
from datetime import datetime, timedelta

import LEDarcade as LED

try:
    import pygame
    HAS_PYGAME = True
except Exception:
    HAS_PYGAME = False


TARGET_FPS = 30

# 5×7 glyphs. Bit 4 is the leftmost column.
DIGIT_ROWS = (
    (0b01110, 0b10001, 0b10011, 0b10101, 0b11001, 0b10001, 0b01110),  # 0
    (0b00100, 0b01100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110),  # 1
    (0b01110, 0b10001, 0b00001, 0b00010, 0b00100, 0b01000, 0b11111),  # 2
    (0b11110, 0b00001, 0b00001, 0b01110, 0b00001, 0b00001, 0b11110),  # 3
    (0b10001, 0b10001, 0b10001, 0b11111, 0b00001, 0b00001, 0b00001),  # 4
    (0b11111, 0b10000, 0b10000, 0b11110, 0b00001, 0b00001, 0b11110),  # 5
    (0b01110, 0b10000, 0b10000, 0b11110, 0b10001, 0b10001, 0b01110),  # 6
    (0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b01000, 0b01000),  # 7
    (0b01110, 0b10001, 0b10001, 0b01110, 0b10001, 0b10001, 0b01110),  # 8
    (0b01110, 0b10001, 0b10001, 0b01111, 0b00001, 0b00001, 0b01110),  # 9
)
GLYPH_W = 5
GLYPH_H = 7
COLON_ROWS = (2, 4)   # which glyph rows get a colon dot

# 3×5 captions. Bit 2 is the leftmost column. Widest names are 9 letters.
TINY_W = 3
TINY_H = 5
TINY_GAP = 1
DATE_GAP = 1
DATE_BLOCK = TINY_H * 2 + DATE_GAP
DATE_RGB = (255, 150, 0)
SECOND_RGB = (0, 0, 255)
WEEKDAYS = (
    "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY",
    "FRIDAY", "SATURDAY", "SUNDAY",
)
MONTHS = (
    "JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE",
    "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER",
)
TINY_FONT = {
    "A": (0b111, 0b101, 0b111, 0b101, 0b101),
    "B": (0b110, 0b101, 0b110, 0b101, 0b110),
    "C": (0b111, 0b100, 0b100, 0b100, 0b111),
    "D": (0b110, 0b101, 0b101, 0b101, 0b110),
    "E": (0b111, 0b100, 0b110, 0b100, 0b111),
    "F": (0b111, 0b100, 0b110, 0b100, 0b100),
    "G": (0b111, 0b100, 0b101, 0b101, 0b111),
    "H": (0b101, 0b101, 0b111, 0b101, 0b101),
    "I": (0b010, 0b010, 0b010, 0b010, 0b010),
    "J": (0b001, 0b001, 0b001, 0b101, 0b111),
    "K": (0b101, 0b110, 0b100, 0b110, 0b101),
    "L": (0b100, 0b100, 0b100, 0b100, 0b111),
    "M": (0b101, 0b111, 0b101, 0b101, 0b101),
    "N": (0b101, 0b110, 0b101, 0b101, 0b101),
    "O": (0b111, 0b101, 0b101, 0b101, 0b111),
    "P": (0b111, 0b101, 0b111, 0b100, 0b100),
    "Q": (0b111, 0b101, 0b101, 0b111, 0b001),
    "R": (0b110, 0b101, 0b110, 0b101, 0b101),
    "S": (0b111, 0b100, 0b111, 0b001, 0b111),
    "T": (0b111, 0b010, 0b010, 0b010, 0b010),
    "U": (0b101, 0b101, 0b101, 0b101, 0b111),
    "V": (0b101, 0b101, 0b101, 0b101, 0b010),
    "W": (0b101, 0b101, 0b101, 0b111, 0b101),
    "X": (0b101, 0b101, 0b010, 0b101, 0b101),
    "Y": (0b101, 0b101, 0b010, 0b010, 0b010),
    "Z": (0b111, 0b001, 0b010, 0b100, 0b111),
    "0": (0b111, 0b101, 0b101, 0b101, 0b111),
    "1": (0b010, 0b110, 0b010, 0b010, 0b111),
    "2": (0b111, 0b001, 0b111, 0b100, 0b111),
    "3": (0b111, 0b001, 0b111, 0b001, 0b111),
    "4": (0b101, 0b101, 0b111, 0b001, 0b001),
    "5": (0b111, 0b100, 0b111, 0b001, 0b111),
    "6": (0b111, 0b100, 0b111, 0b101, 0b111),
    "7": (0b111, 0b001, 0b010, 0b010, 0b010),
    "8": (0b111, 0b101, 0b111, 0b101, 0b111),
    "9": (0b111, 0b101, 0b111, 0b001, 0b111),
}

# Largest cell size that still leaves a black margin for the beam to travel.
DOT_ZOOM_CANDIDATES = (2, 1)
MARGIN = 4

INTRO_PAUSE = 0.30     # black field before the beam comes on
FADE_SECONDS = 0.50    # whole picture in at the start, out at the stop
HOP_STEPS = 4          # frames to sweep the head from one dot to the next
FALL_TIME = 0.78       # tip backwards onto the floor
SLAM_TIME = 0.12       # flat contact, still dark
SHATTER_TIME = 0.95    # dark particles, then the weld may start
BREAK_TIME = FALL_TIME + SLAM_TIME + SHATTER_TIME
LEAD_SECONDS = 4.0     # start that break this long before the minute
PERSPECTIVE = 0.055    # how hard depth shrinks a tipping digit
SHARD_GRAVITY = 38.0
NOZZLE_PERIOD = 2.2    # fade in, then out, then gone, then repeat
NOZZLE_OUT = 0.55      # leftover fade after the beam shuts off
NOZZLE_RGB = (255, 244, 180)
BEAM_RGB = (0, 255, 0)

# White-hot → yellow → orange → settled red. Age is in seconds.
# The drop to red takes about 8s, so a digit is still cooling after it is finished.
HEAT_STOPS = (
    (0.00, 255, 255, 255),
    (0.60, 255, 248, 220),
    (1.60, 255, 190, 60),
    (3.50, 255, 80, 0),
    (6.00, 220, 20, 0),
    (8.00, 210, 16, 0),
)

SPARK_GRAVITY = 92.0     # px/s^2, +y is down. Strong enough to land on a 32px panel.
SPARK_BOUNCE = 0.52      # vertical speed kept after hitting the floor
SPARK_FRICTION = 0.78    # horizontal speed kept on that hit
FLASH_TIME = 0.05
SLOT_NAMES = ("H1", "H2", ":", "M1", "M2")


def _stop(StopEvent):
    try:
        return StopEvent is not None and StopEvent.is_set()
    except Exception:
        return False


def _perimeter(vw, vh):
    """Clockwise loop of the outer edge. Corners are included once."""
    if vw <= 1 or vh <= 1:
        return [(x, y) for y in range(max(vh, 0)) for x in range(max(vw, 0))]
    path = []
    for x in range(vw):
        path.append((x, 0))
    for y in range(1, vh):
        path.append((vw - 1, y))
    for x in range(vw - 2, -1, -1):
        path.append((x, vh - 1))
    for y in range(vh - 2, 0, -1):
        path.append((0, y))
    return path


def _second_u(clock):
    """0 at the start of a minute, 1 at the next. Smooth within each second."""
    if clock is None:
        clock = datetime.now()
    return (clock.second + clock.microsecond / 1000000.0) / 60.0


def _outside(x, y, bounds):
    x0, y0, x1, y1 = bounds
    return x < x0 or x > x1 or y < y0 or y > y1


def _line(x0, y0, x1, y1):
    """Bresenham, including both ends."""
    points = []
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    x, y = x0, y0
    while True:
        points.append((x, y))
        if x == x1 and y == y1:
            break
        e2 = err * 2
        if e2 > -dy:
            err -= dy
            x += sx
        if e2 < dx:
            err += dx
            y += sy
    return points


def _heat_rgb(age, now, x, y):
    if age < 0:
        age = 0.0
    stops = HEAT_STOPS
    rgb = stops[-1][1:]
    for i in range(len(stops) - 1):
        t0, r0, g0, b0 = stops[i]
        t1, r1, g1, b1 = stops[i + 1]
        if age <= t1:
            u = 0.0 if t1 == t0 else (age - t0) / (t1 - t0)
            rgb = (
                int(r0 + (r1 - r0) * u),
                int(g0 + (g1 - g0) * u),
                int(b0 + (b1 - b0) * u),
            )
            break
    else:
        # Ember breathes after the metal has settled. Fade it in so the
        # color does not jump on the frame cooling finishes.
        wobble = 0.88 + 0.12 * math.sin(now * 2.3 + x * 1.7 + y * 0.9)
        k = (age - stops[-1][0]) / 0.40
        if k > 1.0:
            k = 1.0
        scale = 1.0 + (wobble - 1.0) * k
        rgb = (
            int(rgb[0] * scale),
            int(rgb[1] * scale),
            int(rgb[2] * scale),
        )
    return rgb


def _set(buf, x, y, rgb, vw, vh):
    if x < 0 or y < 0 or x >= vw or y >= vh:
        return
    buf[y][x] = rgb


def _max(buf, x, y, rgb, vw, vh):
    if x < 0 or y < 0 or x >= vw or y >= vh:
        return
    r, g, b = buf[y][x]
    buf[y][x] = (r if r > rgb[0] else rgb[0], g if g > rgb[1] else rgb[1], b if b > rgb[2] else rgb[2])


def _blend(buf, x, y, rgb, alpha, vw, vh):
    """Fade rgb in over whatever is already there. alpha 0 is gone."""
    if alpha <= 0.0 or x < 0 or y < 0 or x >= vw or y >= vh:
        return
    if alpha > 1.0:
        alpha = 1.0
    r, g, b = buf[y][x]
    buf[y][x] = (
        int(r + (rgb[0] - r) * alpha),
        int(g + (rgb[1] - g) * alpha),
        int(b + (rgb[2] - b) * alpha),
    )


def _tiny_width(text):
    n = len(text)
    if n <= 0:
        return 0
    return n * TINY_W + (n - 1) * TINY_GAP


def _caption(hhmm, clock):
    """Weekday and month for the minute being shown, including a midnight roll."""
    if clock is None:
        clock = datetime.now()
    base = clock.replace(second=0, microsecond=0)
    try:
        shown = base.replace(hour=int(hhmm[0:2]), minute=int(hhmm[2:4]))
    except (ValueError, IndexError):
        shown = clock
    if shown < base:
        shown = shown + timedelta(days=1)
    month = MONTHS[shown.month - 1] + " " + str(shown.day)
    return (WEEKDAYS[shown.weekday()], month)


def layout_for(vw, vh):
    """Place HH : MM above the weekday and the month-day line."""
    zoom = 1
    pair_gap = 1
    colon_gap = 2
    colon_w = 1
    dw = GLYPH_W
    dh = GLYPH_H
    # Top margin, a gap, and the caption. Zoom has to fit above that.
    room_h = vh - DATE_BLOCK - 3
    if room_h < GLYPH_H:
        room_h = vh
    for z in DOT_ZOOM_CANDIDATES:
        dw_z = GLYPH_W * z
        dh_z = GLYPH_H * z
        pair_z = max(1, z)
        colon_gap_z = z + 1
        colon_w_z = z
        total_w = dw_z * 4 + pair_z * 2 + colon_gap_z * 2 + colon_w_z
        total_h = dh_z
        if total_w <= vw - 2 * MARGIN and total_h <= room_h:
            zoom = z
            pair_gap = pair_z
            colon_gap = colon_gap_z
            colon_w = colon_w_z
            dw = dw_z
            dh = dh_z
            break

    total_w = dw * 4 + pair_gap * 2 + colon_gap * 2 + colon_w
    x = max(0, (vw - total_w) // 2)
    date_top = max(0, vh - DATE_BLOCK - 1)
    # The open row above the caption is the floor. The slam stays on it.
    floor = max(0, date_top - 1)
    y = 1 if vh > dh + 2 else 0
    y += 2
    if y + dh > date_top:
        y = max(0, date_top - dh)
    origins = [None] * 5
    origins[0] = (x, y)
    x += dw + pair_gap
    origins[1] = (x, y)
    x += dw + colon_gap
    origins[2] = (x, y)
    x += colon_w + colon_gap
    origins[3] = (x, y)
    x += dw + pair_gap
    origins[4] = (x, y)
    x1 = origins[4][0] + dw - 1
    y1 = y + dh - 1
    return {
        "zoom": zoom,
        "origins": origins,
        "bounds": (origins[0][0], y, x1, y1),
        "dw": dw,
        "dh": dh,
        "date_top": date_top,
        "floor": floor,
    }


def _paint_tiny(buf, text, y, rgb, vw, vh):
    """Center one 3×5 line. Returns the pixels it drew."""
    gap = TINY_GAP
    width = _tiny_width(text)
    if width > vw and text:
        gap = 0
        width = len(text) * TINY_W
    x = max(0, (vw - width) // 2)
    drawn = []
    for ch in text:
        rows = TINY_FONT.get(ch)
        if rows is None:
            x += TINY_W + gap
            continue
        for row, bits in enumerate(rows):
            for col in range(TINY_W):
                if bits & (1 << (TINY_W - 1 - col)):
                    px, py = x + col, y + row
                    _set(buf, px, py, rgb, vw, vh)
                    drawn.append((px, py))
        x += TINY_W + gap
    return drawn


def _cell_pixels(ox, oy, col, row, zoom):
    pixels = []
    base_x = ox + col * zoom
    base_y = oy + row * zoom
    for dy in range(zoom):
        for dx in range(zoom):
            pixels.append((base_x + dx, base_y + dy))
    return tuple(pixels)


def dots_for(layout, slot, ch):
    """Lit cells of one slot. Each entry is the LEDs that ignite together."""
    zoom = layout["zoom"]
    ox, oy = layout["origins"][slot]
    dots = []
    if ch == ":":
        for row in COLON_ROWS:
            dots.append(_cell_pixels(ox, oy, 0, row, zoom))
        return dots
    rows = DIGIT_ROWS[int(ch)]
    for row, bits in enumerate(rows):
        for col in range(GLYPH_W):
            if bits & (1 << (GLYPH_W - 1 - col)):
                dots.append(_cell_pixels(ox, oy, col, row, zoom))
    return dots


def _aim_of(pixels):
    xs = [p[0] for p in pixels]
    ys = [p[1] for p in pixels]
    return ((min(xs) + max(xs)) // 2, (min(ys) + max(ys)) // 2)


def _target_chars(hhmm):
    return [hhmm[0], hhmm[1], ":", hhmm[2], hhmm[3]]


def _dot_key(pixels):
    """Top-to-bottom, then left-to-right. First LED of a cell is its top-left."""
    return (pixels[0][1], pixels[0][0])


def _lerp(a, b, u):
    return (
        int(round(a[0] + (b[0] - a[0]) * u)),
        int(round(a[1] + (b[1] - a[1]) * u)),
    )


class World:
    """Black field. One continuous beam scans every dot that must change."""

    def __init__(self, vw, vh):
        self.vw = int(vw)
        self.vh = int(vh)
        self.layout = layout_for(self.vw, self.vh)
        self.bounds = self.layout["bounds"]
        self.floor = self.layout["floor"]
        self.caption = ("", "")
        self.perimeter = _perimeter(self.vw, self.vh)
        self.second_u = 0.0
        self.live = []          # {slot, pixels, born}
        self.breaks = []        # a digit tipping back, then shards
        self.shards = []        # dark debris, separate from weld sparks
        self.sparks = []
        self.flash = None       # {pixels, until}
        self.beam = None        # continuous ray: origin stays, head sweeps
        self.origin = None
        self.head = None
        self.queue = []         # dots still to strike, raster order
        self.goal = [None] * 5  # char a slot is currently being built as
        self.phase = "pause"
        self.phase_until = None
        self.started = False
        self.shown = [None] * 5
        self.prev = [None] * 5
        self.announced = None
        self.seen_complete = False
        self.last_now = None
        self.lead_hhmm = None       # upcoming minute we already started
        self.nozzle_t0 = None
        self.nozzle_out_t = None
        self.nozzle_out_a = 0.0
        self.nozzle_pixels = []

    def update(self, now, hhmm, clock=None):
        self.second_u = _second_u(clock)
        if not self.started:
            self.started = True
            self.last_now = now
            self.phase = "pause"
            self.phase_until = now + INTRO_PAUSE
            self.caption = _caption(hhmm, clock)
            return

        dt = now - self.last_now
        self.last_now = now
        if dt < 0.0:
            dt = 0.0
        elif dt > 0.1:
            dt = 0.1
        self._move_sparks(dt)
        self._advance_breaks(now, dt)
        if self.nozzle_out_t is not None and (now - self.nozzle_out_t) >= NOZZLE_OUT:
            self.nozzle_out_t = None

        hhmm = self._target_hhmm(hhmm, clock)
        self.caption = _caption(hhmm, clock)
        target = _target_chars(hhmm)
        if self.phase == "beam":
            self._update_beam(now, target)
        elif self.phase == "fade":
            if now >= self.phase_until:
                self._poll(now, target)
        elif self.phase == "pause":
            if now >= self.phase_until:
                self._poll(now, target)
        else:
            self._poll(now, target)

    def _move_sparks(self, dt):
        floor = float(self.floor)
        alive = []
        for s in self.sparks:
            s["age"] += dt
            if s["age"] >= s["life"]:
                continue
            s["vy"] += SPARK_GRAVITY * dt
            s["x"] += s["vx"] * dt
            s["y"] += s["vy"] * dt
            # Land and hop. A weak hit settles instead of buzzing on the floor.
            if s["y"] >= floor and s["vy"] > 0.0:
                s["y"] = floor
                rebound = s["vy"] * SPARK_BOUNCE
                s["vx"] *= SPARK_FRICTION
                if rebound < 14.0:
                    s["vy"] = 0.0
                else:
                    s["vy"] = -rebound
                    s["bounces"] = s.get("bounces", 0) + 1
            alive.append(s)
        if len(alive) > 80:
            alive = alive[-80:]
        self.sparks = alive

    def _poll(self, now, target):
        need = [i for i, ch in enumerate(target) if self.shown[i] != ch]
        if not need:
            self.phase = "hold"
            self._drop_beam(now)
            text = "".join(target)
            if text != self.announced:
                print("[LaserClock] forged {}".format(text))
                self.announced = text
                self.seen_complete = True
            return
        if self._break_slots(need, now):
            self._hide_laser()
            self.phase = "fade"
            self.phase_until = self._break_until(now)
            return
        self._begin_pass(need, target, now)

    def _slot_clearing(self, index, now):
        for b in self.breaks:
            if b["slot"] == index and now < b["until"]:
                return True
        return False

    def _break_until(self, now):
        until = now
        for b in self.breaks:
            if b["until"] > until:
                until = b["until"]
        if until <= now:
            return now + BREAK_TIME
        return until

    def _break_slots(self, slots, now):
        """Tip live digits backwards. Returns True if any slot left the clock."""
        slotset = set(slots)
        grouped = {}
        kept = []
        for dot in self.live:
            slot = dot["slot"]
            if slot not in slotset:
                kept.append(dot)
                continue
            grouped.setdefault(slot, []).append(dot)
        self.live = kept
        self.queue = [d for d in self.queue if d["slot"] not in slotset]
        already = {b["slot"] for b in self.breaks if now < b["until"]}
        ground = float(self.floor)
        had = False
        for i in slots:
            if self.shown[i] is not None:
                self.prev[i] = self.shown[i]
            self.shown[i] = None
            self.goal[i] = None
            dots = grouped.get(i)
            if not dots or i in already:
                continue
            had = True
            xs = []
            ys = []
            for dot in dots:
                for x, y in dot["pixels"]:
                    xs.append(x)
                    ys.append(y)
            pivot_x = (min(xs) + max(xs)) / 2.0
            bottom = float(max(ys))
            floor = ground if ground > bottom else bottom
            pieces = []
            max_ly = 1.0
            half = 1
            for dot in dots:
                px, py = dot["pixels"][0]
                color = _heat_rgb(now - dot["born"], now, px, py)
                for x, y in dot["pixels"]:
                    lx = x - pivot_x
                    ly = bottom - y
                    if ly > max_ly:
                        max_ly = ly
                    if abs(lx) > half:
                        half = abs(lx)
                    pieces.append({"lx": lx, "ly": ly, "color": color})
            self.breaks.append({
                "slot": i,
                "t0": now,
                "until": now + BREAK_TIME,
                "pieces": pieces,
                "pivot_x": pivot_x,
                "bottom": bottom,
                "ground": floor,
                "span": max_ly,
                "half": int(half) + 1,
                "shattered": False,
            })
        return had

    def _advance_breaks(self, now, dt):
        slam_at = FALL_TIME + SLAM_TIME
        alive = []
        for b in self.breaks:
            if (now - b["t0"]) >= slam_at and not b["shattered"]:
                self._spawn_shards(b)
                b["shattered"] = True
            if now < b["until"]:
                alive.append(b)
        self.breaks = alive
        self._move_shards(dt)

    def _spawn_shards(self, b):
        """Dim debris from the floor line. Not the bright weld sparks."""
        room = 120 - len(self.shards)
        if room <= 0:
            return
        pieces = b["pieces"]
        step = 1
        if len(pieces) > room:
            step = (len(pieces) + room - 1) // room
        theta = math.pi * 0.5
        pivot_x = b["pivot_x"]
        ground = b["ground"]
        for i, p in enumerate(pieces):
            if i % step:
                continue
            sx, _sy = self._project(p["lx"], p["ly"], pivot_x, ground, theta)
            spread = sx - pivot_x
            if spread > 0.3:
                direction = 1.0
            elif spread < -0.3:
                direction = -1.0
            else:
                direction = random.choice((-1.0, 1.0))
            vx = direction * random.uniform(8.0, 22.0) + random.uniform(-4.0, 4.0)
            vy = -random.uniform(14.0, 34.0)
            life = random.uniform(SHATTER_TIME * 0.75, SHATTER_TIME)
            self.shards.append({
                "x": sx,
                "y": ground - 0.2,
                "vx": vx,
                "vy": vy,
                "age": 0.0,
                "life": life,
                "r": random.randint(34, 70),
                "g": random.randint(2, 10),
            })

    def _move_shards(self, dt):
        alive = []
        for s in self.shards:
            s["age"] += dt
            if s["age"] >= s["life"]:
                continue
            s["vy"] += SHARD_GRAVITY * dt
            s["x"] += s["vx"] * dt
            s["y"] += s["vy"] * dt
            if s["y"] > self.vh + 1:
                continue
            alive.append(s)
        if len(alive) > 140:
            alive = alive[-140:]
        self.shards = alive

    def _project(self, lx, ly, pivot_x, pivot_y, theta):
        """Tip ly up off the hinge. theta 0 is upright, pi/2 is flat on the floor."""
        z = ly * math.sin(theta)
        height = ly * math.cos(theta)
        denom = 1.0 + z * PERSPECTIVE
        return (pivot_x + lx / denom, pivot_y - height / denom)

    def _break_pose(self, b, now):
        age = now - b["t0"]
        if age < 0.0:
            age = 0.0
        ground = b["ground"]
        bottom = b["bottom"]
        if age < FALL_TIME:
            u = age / FALL_TIME
            ease = u * u
            theta = (math.pi * 0.5) * ease
            pivot_y = bottom + (ground - bottom) * ease
            shade = 0.16 + 0.84 * math.cos(theta)
            slam = 0.0
        elif age < FALL_TIME + SLAM_TIME:
            theta = math.pi * 0.5
            local = (age - FALL_TIME) / SLAM_TIME
            # Bite one pixel into the floor, then settle on it.
            pivot_y = ground + (1.0 if local < 0.45 else 0.0)
            slam = 1.0 - local
            shade = 0.16 + 0.40 * slam
        else:
            theta = math.pi * 0.5
            pivot_y = ground
            shade = 0.0
            slam = 0.0
        cap = float(self.layout["date_top"] - 1)
        if pivot_y > cap:
            pivot_y = cap
        return theta, pivot_y, shade, slam

    def _begin_pass(self, slots, target, now):
        """One sweep, in reading order, over every slot that changed."""
        self.queue = []
        self.goal = [None] * 5
        self.origin = self._pass_origin()
        self.head = self.origin
        self._arm_nozzle(now)
        for i in slots:
            self._enqueue_slot(i, target[i])
        names = " ".join(SLOT_NAMES[i] for i in slots)
        if self.seen_complete:
            print("[LaserClock] reweld {} ({} dots)".format(names, len(self.queue)))
        else:
            print("[LaserClock] welding {} dots across {} (left to right, top to bottom)".format(
                len(self.queue), names))
        self._launch_next(now, target)

    def _enqueue_slot(self, index, ch):
        self.goal[index] = ch
        self.shown[index] = None
        for pixels in dots_for(self.layout, index, ch):
            self.queue.append({"slot": index, "ch": ch, "pixels": pixels})
        self.queue.sort(key=lambda d: _dot_key(d["pixels"]))

    def _reconcile(self, now, target):
        """Drop stale dots and pick up digits that changed during the sweep."""
        self.queue = [
            d for d in self.queue
            if target[d["slot"]] == d["ch"] and self.goal[d["slot"]] == d["ch"]
        ]
        stale = []
        for i, ch in enumerate(target):
            if self.goal[i] not in (None, ch) or self.shown[i] not in (None, ch):
                stale.append(i)
        if stale:
            self._break_slots(stale, now)
        current = self.beam["dot"] if self.beam else None
        for i, ch in enumerate(target):
            if self.shown[i] == ch:
                continue
            if self._slot_clearing(i, now):
                continue
            if self.goal[i] == ch and any(d["slot"] == i for d in self.queue):
                continue
            if (
                current is not None
                and current["slot"] == i
                and current["ch"] == ch
                and self.goal[i] == ch
            ):
                continue
            self._enqueue_slot(i, ch)

    def _launch_next(self, now, target):
        self._reconcile(now, target)
        if self.breaks and any(now < b["until"] for b in self.breaks):
            # A digit is decaying. Leave the queue; the weld resumes after.
            self._hide_laser()
            self.phase = "fade"
            self.phase_until = self._break_until(now)
            return
        if not self.queue:
            pending = [
                i for i, ch in enumerate(target)
                if self.shown[i] != ch
            ]
            if pending and any(self._slot_clearing(i, now) for i in pending):
                self._hide_laser()
                self.phase = "fade"
                self.phase_until = self._break_until(now)
                return
            self._drop_beam(now)
            self.phase = "hold"
            return
        item = self.queue.pop(0)
        aim = _aim_of(item["pixels"])
        frm = self.head if self.head is not None else self.origin
        self.beam = {
            "origin": self.origin,
            "frm": frm,
            "to": aim,
            "step": 0,
            "dot": item,
        }
        self.phase = "beam"

    def _hide_laser(self):
        """Digit decay plays alone. Beam and nozzle are gone, not faded."""
        self.beam = None
        self.nozzle_t0 = None
        self.nozzle_out_t = None
        self.nozzle_out_a = 0.0
        self.nozzle_pixels = []

    def _arm_nozzle(self, now):
        """Start a fade-in. Leave an in-progress cycle alone."""
        self.nozzle_out_t = None
        if self.nozzle_t0 is None:
            self.nozzle_t0 = now

    def _drop_beam(self, now):
        """Beam off. The nozzle finishes fading out instead of popping off."""
        if self.beam is not None and self.nozzle_t0 is not None:
            self.nozzle_out_a = self._nozzle_alpha(now)
            self.nozzle_out_t = now
            self.nozzle_t0 = None
        self.beam = None

    def _nozzle_alpha(self, now):
        """0 → 1 → 0 across one period. Fully gone at both ends."""
        if self.nozzle_t0 is None:
            return 0.0
        u = (now - self.nozzle_t0) / NOZZLE_PERIOD
        u = u - math.floor(u)
        return math.sin(math.pi * u)

    def _target_hhmm(self, hhmm, clock):
        """Use the next minute a few seconds early, and stick with it."""
        if self.lead_hhmm is not None:
            if hhmm == self.lead_hhmm:
                self.lead_hhmm = None
            else:
                return self.lead_hhmm
        if (
            clock is None
            or self.phase != "hold"
            or not self.seen_complete
            or self.beam is not None
        ):
            return hhmm
        sec = clock.second + clock.microsecond / 1000000.0
        if sec < 60.0 - LEAD_SECONDS:
            return hhmm
        nxt = (clock.replace(second=0, microsecond=0) + timedelta(minutes=1)).strftime("%H%M")
        if nxt == hhmm:
            return hhmm
        self.lead_hhmm = nxt
        left = 60.0 - sec
        print("[LaserClock] {} → {} in {:.0f}s, old digits fall and shatter".format(
            hhmm[:2] + ":" + hhmm[2:], nxt[:2] + ":" + nxt[2:], left
        ))
        return nxt

    def _pass_origin(self):
        """One screen corner for this weld. It stays put until the next pass."""
        vw, vh = self.vw, self.vh
        corners = (
            (0, 0),
            (vw - 1, 0),
            (0, vh - 1),
            (vw - 1, vh - 1),
        )
        for ox, oy in random.sample(corners, len(corners)):
            if _outside(ox, oy, self.bounds):
                return (ox, oy)
        return corners[0]

    def _update_beam(self, now, target):
        if self.beam is None:
            self.phase = "hold"
            return
        self.beam["step"] += 1
        if self.beam["step"] < HOP_STEPS:
            return
        item = self.beam["dot"]
        if item is not None and target[item["slot"]] == item["ch"] and self.goal[item["slot"]] == item["ch"]:
            self._ignite(item, now)
        if item is not None:
            self.head = self.beam["to"]
        self._launch_next(now, target)

    def _ignite(self, item, now):
        self.live.append({
            "slot": item["slot"],
            "pixels": item["pixels"],
            "born": now,
        })
        aim = _aim_of(item["pixels"])
        self._spawn_sparks(aim[0], aim[1])
        self._spawn_flash(item["pixels"], now)
        if not any(d["slot"] == item["slot"] for d in self.queue):
            self.shown[item["slot"]] = item["ch"]
            self.prev[item["slot"]] = item["ch"]
            self.goal[item["slot"]] = None

    def _spawn_sparks(self, x, y):
        count = random.randint(10, 14)
        for i in range(count):
            ang = random.uniform(0.0, math.tau)
            if i < 4:
                # These last long enough to reach the floor and hop.
                speed = random.uniform(12.0, 22.0)
                life = random.uniform(1.05, 1.45)
            else:
                speed = random.uniform(10.0, 18.0)
                life = random.uniform(0.30, 0.62)
            vx = math.cos(ang) * speed
            vy = math.sin(ang) * speed - random.uniform(6.0, 14.0)
            # Already in flight on the impact frame, clear of the white dot.
            kick = 0.05
            self.sparks.append({
                "x": float(x) + 0.5 + vx * kick,
                "y": float(y) + 0.5 + vy * kick,
                "vx": vx,
                "vy": vy,
                "age": 0.0,
                "life": life,
                "bounces": 0,
            })

    def _spawn_flash(self, dot, now):
        blocked = set(dot)
        halo = []
        for x, y in dot:
            for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                p = (x + ox, y + oy)
                if p not in blocked:
                    halo.append(p)
        self.flash = {"pixels": halo, "until": now + FLASH_TIME}

    def _beam_pixels(self):
        """Full ray from the fixed origin to the moving head. Stays on."""
        beam = self.beam
        if beam is None:
            return []
        steps = HOP_STEPS
        if steps <= 1:
            u = 1.0
        else:
            u = beam["step"] / float(steps - 1)
        if u < 0.0:
            u = 0.0
        elif u > 1.0:
            u = 1.0
        ox, oy = beam["origin"]
        hx, hy = _lerp(beam["frm"], beam["to"], u)
        full = _line(ox, oy, hx, hy)
        dot = beam.get("dot")
        if dot is not None and u < 1.0:
            blocked = set(dot["pixels"])
            while full and full[-1] in blocked:
                full.pop()
        if not full:
            full = [(ox, oy)]
        return full

    def render(self, now):
        vw, vh = self.vw, self.vh
        buf = [[(0, 0, 0) for _ in range(vw)] for _ in range(vh)]

        for dot in self.live:
            px, py = dot["pixels"][0]
            age = now - dot["born"]
            rgb = _heat_rgb(age, now, px, py)
            for x, y in dot["pixels"]:
                _set(buf, x, y, rgb, vw, vh)
            # Short halo while the dot is still white-hot. Only onto empty LEDs.
            if age < 0.28:
                spill = int(90 * (1.0 - age / 0.28))
                glow = (spill, spill // 2, 0)
                blocked = set(dot["pixels"])
                for x, y in dot["pixels"]:
                    for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nx, ny = x + ox, y + oy
                        if (nx, ny) in blocked:
                            continue
                        if nx < 0 or ny < 0 or nx >= vw or ny >= vh:
                            continue
                        if buf[ny][nx] == (0, 0, 0):
                            _max(buf, nx, ny, glow, vw, vh)

        self._paint_breaks(buf, now, vw, vh)
        self._paint_shards(buf, vw, vh)

        if self.flash is not None and now < self.flash["until"]:
            for x, y in self.flash["pixels"]:
                _max(buf, x, y, (255, 255, 255), vw, vh)

        for s in self.sparks:
            u = s["age"] / s["life"] if s["life"] else 1.0
            if u < 0.22:
                rgb = (255, 255, 230)
            elif u < 0.55:
                rgb = (255, 186, 30)
            else:
                fade = 1.0 - (u - 0.55) / 0.45
                if fade < 0.0:
                    fade = 0.0
                rgb = (int(255 * fade), int(64 * fade), 0)
            sx, sy = int(s["x"]), int(s["y"])
            _max(buf, sx, sy, rgb, vw, vh)
            if u < 0.55:
                tx = int(s["x"] - s["vx"] * 0.016)
                ty = int(s["y"] - s["vy"] * 0.016)
                if (tx, ty) != (sx, sy):
                    _max(buf, tx, ty, (rgb[0] // 3, rgb[1] // 3, 0), vw, vh)

        # The falling digit is on its own. The beam comes back to weld.
        if not any(now < b["until"] for b in self.breaks):
            if self.beam is not None:
                pixels = self._beam_pixels()
                self._paint_beam(buf, pixels, vw, vh)
                self.nozzle_pixels = pixels[:2]
                self._paint_nozzle(buf, self.nozzle_pixels, self._nozzle_alpha(now), vw, vh)
            elif self.nozzle_out_t is not None:
                u = (now - self.nozzle_out_t) / NOZZLE_OUT
                if u < 0.0:
                    u = 0.0
                elif u > 1.0:
                    u = 1.0
                self._paint_nozzle(buf, self.nozzle_pixels, self.nozzle_out_a * (1.0 - u), vw, vh)

        self._paint_caption(buf)
        self._paint_second(buf)
        return buf

    def _paint_second(self, buf):
        """Two blue pixels on the bezel. :00 is the center of the top edge."""
        path = self.perimeter
        n = len(path)
        if n == 0:
            return
        # Even widths sit on the two middle pixels. Odd widths sit on the middle one.
        origin = self.vw // 2 - (0 if self.vw % 2 else 1)
        start = self.second_u * n + origin
        # The mark covers two steps of the loop. A partial step fades.
        i0 = int(math.floor(start))
        i1 = int(math.floor(start + 2.0))
        for i in range(i0, i1 + 1):
            left = i if i > start else start
            right = (i + 1.0) if (i + 1.0) < (start + 2.0) else (start + 2.0)
            alpha = right - left
            if alpha <= 0.02:
                continue
            x, y = path[i % n]
            _blend(buf, x, y, SECOND_RGB, alpha, self.vw, self.vh)

    def _paint_caption(self, buf):
        y = self.layout["date_top"]
        for text in self.caption:
            _paint_tiny(buf, text, y, DATE_RGB, self.vw, self.vh)
            y += TINY_H + DATE_GAP

    def _paint_breaks(self, buf, now, vw, vh):
        for b in self.breaks:
            if b["shattered"]:
                continue
            theta, pivot_y, shade, slam = self._break_pose(b, now)
            span = b["span"] if b["span"] else 1.0
            sink = math.sin(theta)
            if shade > 0.02:
                for p in b["pieces"]:
                    depth = 1.0 - 0.45 * sink * (p["ly"] / span)
                    if depth < 0.35:
                        depth = 0.35
                    sx, sy = self._project(p["lx"], p["ly"], b["pivot_x"], pivot_y, theta)
                    r, g, bcol = p["color"]
                    k = shade * depth
                    rgb = (int(r * k), int(g * k), int(bcol * k))
                    if rgb == (0, 0, 0):
                        continue
                    _max(buf, int(round(sx)), int(round(sy)), rgb, vw, vh)
            if slam > 0.45:
                gy = int(round(pivot_y))
                px = int(round(b["pivot_x"]))
                half = b["half"]
                rgb = (int(78 * slam), int(10 * slam), 0)
                for dx in range(-half, half + 1):
                    _max(buf, px + dx, gy, rgb, vw, vh)

    def _paint_shards(self, buf, vw, vh):
        for s in self.shards:
            life = s["life"] or 1.0
            fade = 1.0 - s["age"] / life
            if fade <= 0.0:
                continue
            rgb = (int(s["r"] * fade), int(s["g"] * fade), 0)
            if rgb[0] <= 0:
                continue
            _max(buf, int(s["x"]), int(s["y"]), rgb, vw, vh)

    def _paint_nozzle(self, buf, pixels, alpha, vw, vh):
        """Yellow source. Alpha 0 is gone, 1 is the solid nozzle."""
        if alpha <= 0.02 or not pixels:
            return
        nr, ng, nb = NOZZLE_RGB
        for x, y in pixels:
            if x < 0 or y < 0 or x >= vw or y >= vh:
                continue
            r, g, b = buf[y][x]
            buf[y][x] = (
                int(r + (nr - r) * alpha),
                int(g + (ng - g) * alpha),
                int(b + (nb - b) * alpha),
            )

    def _paint_beam(self, buf, pixels, vw, vh):
        """Every laser LED is full green. The ray does not dim along its length."""
        for x, y in pixels:
            _max(buf, x, y, BEAM_RGB, vw, vh)


def _smooth(u):
    """Smoothstep. 0 at the start of a fade, 1 at the end."""
    if u <= 0.0:
        return 0.0
    if u >= 1.0:
        return 1.0
    return u * u * (3.0 - 2.0 * u)


def _fade_level(elapsed, remain, stop_elapsed, stop_level):
    """Brightness of the whole picture. 1 is full.

    remain is None when the clock runs until it is stopped.
    stop_elapsed is None until a stop has been requested.
    stop_level is the level captured on that request.
    """
    level = _smooth(elapsed / FADE_SECONDS)
    if remain is not None and remain < FADE_SECONDS:
        level = min(level, _smooth(max(0.0, remain / FADE_SECONDS)))
    if stop_elapsed is not None:
        out = 1.0 - _smooth(min(1.0, stop_elapsed / FADE_SECONDS))
        level = min(level, stop_level * out)
    return level


def _blank_canvas(vw, vh):
    canvas = getattr(LED, "Canvas", None)
    if canvas is None and getattr(LED, "TheMatrix", None) is not None:
        canvas = LED.TheMatrix.CreateFrameCanvas()
        LED.Canvas = canvas
    return canvas, vw, vh


def PlayLaserClock(Duration=0, StopEvent=None):
    vw = int(getattr(LED, "HatWidth", 64) or 64)
    vh = int(getattr(LED, "HatHeight", 32) or 32)
    print("[LaserClock] {}x{}  laser HH:MM".format(vw, vh))

    canvas, vw, vh = _blank_canvas(vw, vh)
    world = World(vw, vh)
    clock = pygame.time.Clock() if HAS_PYGAME else None
    start = time.time()
    frame_dt = 1.0 / TARGET_FPS
    run_seconds = float(Duration) * 60.0 if Duration and float(Duration) > 0 else None
    stop_t = None
    stop_level = 1.0

    try:
        while True:
            now = time.time()
            elapsed = now - start
            remain = None if run_seconds is None else run_seconds - elapsed
            if _stop(StopEvent) and stop_t is None:
                stop_t = now
                stop_level = _fade_level(elapsed, remain, None, 1.0)
            stop_elapsed = None if stop_t is None else now - stop_t
            level = _fade_level(elapsed, remain, stop_elapsed, stop_level)

            clock_now = datetime.now()
            world.update(now, clock_now.strftime("%H%M"), clock_now)

            if canvas is None:
                time.sleep(frame_dt)
            else:
                buf = world.render(now)
                canvas.Fill(0, 0, 0)
                if level > 0.004:
                    for y in range(vh):
                        row = buf[y]
                        for x in range(vw):
                            r, g, b = row[x]
                            if not (r or g or b):
                                continue
                            if level < 0.999:
                                r = int(r * level)
                                g = int(g * level)
                                b = int(b * level)
                            if r or g or b:
                                canvas.SetPixel(x, y, r, g, b)
                canvas = LED.TheMatrix.SwapOnVSync(canvas)
                LED.Canvas = canvas
                if clock is not None:
                    clock.tick(TARGET_FPS)
                else:
                    left = frame_dt - (time.time() - now)
                    if left > 0.0:
                        time.sleep(left)

            if stop_elapsed is not None and stop_elapsed >= FADE_SECONDS:
                print("[LaserClock] StopEvent")
                return
            if remain is not None and remain <= 0.0:
                print("[LaserClock] Duration reached")
                return
    except KeyboardInterrupt:
        print("[LaserClock] Interrupted")


def LaunchLaserClock(Duration=0, ShowIntro=True, StopEvent=None):
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
    PlayLaserClock(Duration=Duration, StopEvent=StopEvent)


if __name__ == "__main__":
    try:
        LaunchLaserClock(Duration=0)
    except KeyboardInterrupt:
        print("Exiting LaserClock.")
