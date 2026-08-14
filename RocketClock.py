# =====================================================================================
# ROCKET CLOCK — full-panel digital HH:MM with rocket digit transitions
#
# Font: Anton (bold smooth sans) — sized to fit the panel without chunky
# nearest-neighbor upscaling (soft anti-aliased edges).
#
# Steady face: HH:MM. Digits rocket up on change; replacements descend with a
# Starship-style blue Raptor jet. Landings are perfect, crash, miss (off bottom),
# or collide into a neighbor — every pad cross gets a white dust puff. Crashes
# and collisions burn yellow/orange/red.
#
# Fueling: changing digits start dark and fill bottom-up with bright clock color
# over 60s (1 px every 60/N s). In flight, fuel burns top-first (bright shrinks
# from the top); ideally empty exactly at touchdown. Empty mid-descent → crash.
# Touchdown kills jets + dust. Out-of-control landings tilt L/R.
#
# Launch: LEDpanel / action "rocketclock" / LEDcommander / standalone
# =====================================================================================

from __future__ import annotations

import math
import random
import time
from datetime import datetime, timedelta

import LEDarcade as LED

LED.Initialize()

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    HAS_PIL = True
except Exception:
    HAS_PIL = False

try:
    import pygame
    HAS_PYGAME = True
except Exception:
    HAS_PYGAME = False


# ---- Config ----
TARGET_FPS = 30
USE_24H = True
ROCKET_SECONDS = 19.0          # hold + takeoff + descent + dust (+ miss/crash retry)
LAUNCH_HOLD_SECONDS = 1.0      # flames on pad before ascent
# Landing outcome weights (non-safe approaches)
OUTCOME_PERFECT = 0.55
OUTCOME_CRASH = 0.16
OUTCOME_MISS = 0.14
OUTCOME_COLLIDE = 0.15
# Colon second bar disabled
COLON_COUNTDOWN = False
FUEL_EMPTY = 0.32              # unfueled / spent pixel = clock color * this
FUEL_FAST_SECONDS = 3.5        # non–minute-ones digits: quick one-pixel-at-a-time fill
# HH:MM slots — index 4 is minute ones ("last minute" digit)
SLOT_MINUTE_ONES = 4
# Smooth bold display face
FONT_CANDIDATES = (
    "Anton-Regular.ttf",
    "DejaVuSans-Bold.ttf",
    "CHECKBK0.TTF",
)
# Clock face colors — randomized at each PlayRocketClock start
DIGIT_HI = (210, 245, 255)
DIGIT_MID = (40, 190, 230)
DIGIT_LO = (10, 80, 120)
# Starship / Raptor-style methane jet — blue-white core, deep blue fringe
JET_BLUE = (
    (230, 245, 255),
    (160, 210, 255),
    (90, 170, 255),
    (40, 120, 255),
    (20, 70, 220),
    (10, 40, 180),
    (120, 190, 255),
    (200, 230, 255),
    (60, 140, 240),
)
# Crash / RUD fireball — yellow / orange / red
CRASH_FIRE = (
    (255, 250, 180),
    (255, 230, 80),
    (255, 180, 40),
    (255, 120, 20),
    (255, 60, 10),
    (220, 30, 8),
    (180, 20, 5),
    (255, 200, 50),
)
SMOKE_COLORS = (
    (255, 255, 255),
    (230, 230, 235),
    (200, 200, 210),
    (170, 170, 180),
    (140, 140, 150),
)
BG = (0, 0, 0)
CHAR_GAP = 2
COLON_GAP = 3


def _minute_elapsed():
    """Seconds into the current minute, with fractional precision [0, 60)."""
    now = datetime.now()
    return now.second + now.microsecond / 1_000_000.0


def _upcoming_hhmm():
    """HH:MM string after the next minute rollover (what the face will become)."""
    now = datetime.now()
    nxt = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
    fmt = "%H:%M" if USE_24H else "%I:%M"
    return nxt.strftime(fmt)


def _changing_slot_indices(current, upcoming):
    """Slot indices (0-4) where the glyph will change at the next minute."""
    cur = list(current)
    up = list(upcoming)
    if len(cur) != 5 or len(up) != 5:
        return set()
    return {i for i in range(5) if cur[i] != up[i] and cur[i] != ":"}


def _darken_clock_rgb(rgb, factor=FUEL_EMPTY):
    """Darker (empty/spent) shade of the clock color."""
    f = max(0.05, min(1.0, float(factor)))
    return tuple(max(0, min(255, int(c * f))) for c in rgb)


def _pixels_for_fuel_level(home, fuel_frac):
    """
    Render glyph by fuel level in [0, 1].
    Empty (dark) by default; bright fuel occupies the bottom fraction of pixels
    one pixel at a time (floor).
    """
    if not home:
        return home
    n = len(home)
    if n <= 0:
        return home
    frac = max(0.0, min(1.0, float(fuel_frac)))
    # floor so pixels light one-at-a-time as frac creeps up
    n_bright = int(frac * n)
    if frac >= 1.0:
        n_bright = n
    keys = sorted(home.keys(), key=lambda p: (-p[1], p[0]))
    out = {}
    bright = set(keys[:n_bright])
    for k, rgb in home.items():
        out[k] = rgb if k in bright else _darken_clock_rgb(rgb)
    return out


def _refuel_frac(elapsed_sec, epoch_sec, window_sec=None):
    """
    Fueling progress in [0, 1] from epoch over `window_sec`.
    Default window = remaining seconds in the minute (e.g. 52s if epoch=8).
    Fast digits pass a short window (still one pixel at a time via floor).
    """
    elapsed = max(0.0, float(elapsed_sec))
    epoch = max(0.0, float(epoch_sec))
    if window_sec is None:
        window = max(0.05, 60.0 - min(59.999, epoch))
    else:
        window = max(0.05, float(window_sec))
    return max(0.0, min(1.0, (elapsed - epoch) / window))


def _fuel_pixels_for_refuel(home, elapsed_sec, epoch_sec, window_sec=None):
    """Bottom-up bright fill over the refuel window."""
    return _pixels_for_fuel_level(
        home, _refuel_frac(elapsed_sec, epoch_sec, window_sec),
    )


# Primary face palettes: (hi, mid, lo) vertical gradient
PRIMARY_PALETTES = (
    # Red
    ((255, 200, 200), (255, 40, 40), (90, 10, 10)),
    # Green
    ((200, 255, 200), (40, 220, 50), (8, 70, 12)),
    # Blue
    ((200, 220, 255), (40, 90, 255), (8, 20, 100)),
    # Yellow (classic primary with R/G/B)
    ((255, 255, 200), (240, 220, 30), (90, 80, 8)),
)


def _pick_clock_palette():
    """
    Pick a primary color for this run (red / green / blue / yellow).
    Sets DIGIT_HI / MID / LO. Returns (hi, mid, lo) for logging.
    """
    global DIGIT_HI, DIGIT_MID, DIGIT_LO
    DIGIT_HI, DIGIT_MID, DIGIT_LO = random.choice(PRIMARY_PALETTES)
    return DIGIT_HI, DIGIT_MID, DIGIT_LO


def _pick_landing_outcome():
    """perfect | crash | miss | collide"""
    r = random.random()
    if r < OUTCOME_PERFECT:
        return "perfect"
    r -= OUTCOME_PERFECT
    if r < OUTCOME_CRASH:
        return "crash"
    r -= OUTCOME_CRASH
    if r < OUTCOME_MISS:
        return "miss"
    return "collide"


def _stop(StopEvent):
    try:
        return StopEvent is not None and StopEvent.is_set()
    except Exception:
        return False


def _now_hhmm():
    fmt = "%H:%M" if USE_24H else "%I:%M"
    return datetime.now().strftime(fmt)


def _resolve_font_path():
    for name in FONT_CANDIDATES:
        try:
            path = LED.ResolveFontPath(name)
            # Probe load
            ImageFont.truetype(path, 16)
            return path, name
        except Exception:
            continue
    return LED.ResolveFontPath(FONT_CANDIDATES[0]), FONT_CANDIDATES[0]


def _measure_char(draw, font, ch):
    bb = draw.textbbox((0, 0), ch, font=font)
    return bb, max(1, bb[2] - bb[0]), max(1, bb[3] - bb[1])


def _fixed_layout_width(digit_w, colon_w):
    """Fixed HH:MM slot width: D D : D D with constant gaps."""
    # [D][gap][D][gap][:][gap][D][gap][D]
    return 4 * digit_w + colon_w + 2 * CHAR_GAP + 2 * COLON_GAP


def _best_font(path, panel_w, panel_h, sample="23:59"):
    """Largest size whose fixed monospaced HH:MM layout fits ~80% panel width."""
    max_w = max(8, int(round(panel_w * 0.80)))
    max_h = panel_h - 2
    best = None
    probe = Image.new("L", (panel_w * 3, panel_h * 3), 0)
    draw = ImageDraw.Draw(probe)
    for size in range(36, 10, -1):
        try:
            font = ImageFont.truetype(path, size)
        except Exception:
            continue
        # Monospace slot = widest digit 0-9 (keeps face position fixed forever)
        digit_w = 1
        digit_h = 1
        for d in "0123456789":
            _, cw, ch = _measure_char(draw, font, d)
            digit_w = max(digit_w, cw)
            digit_h = max(digit_h, ch)
        _, colon_w, colon_h = _measure_char(draw, font, ":")
        digit_h = max(digit_h, colon_h)
        total_w = _fixed_layout_width(digit_w, colon_w)
        if total_w <= max_w and digit_h <= max_h:
            best = (font, size, digit_w, colon_w, digit_h)
            break
    if best is None:
        font = ImageFont.truetype(path, 14)
        digit_w = colon_w = digit_h = 8
        for d in "0123456789:":
            _, cw, ch = _measure_char(draw, font, d)
            if d == ":":
                colon_w = cw
            else:
                digit_w = max(digit_w, cw)
            digit_h = max(digit_h, ch)
        return font, 14, digit_w, colon_w, digit_h
    return best


def _shade_rgb(y, h):
    """Soft vertical gradient across a glyph."""
    t = y / max(1, h - 1)
    # top bright → bottom cooler
    r = int(DIGIT_HI[0] * (1 - t) + DIGIT_LO[0] * t)
    g = int(DIGIT_HI[1] * (1 - t) + DIGIT_LO[1] * t)
    b = int(DIGIT_HI[2] * (1 - t) + DIGIT_LO[2] * t)
    # mix mid for body
    r = int(r * 0.45 + DIGIT_MID[0] * 0.55)
    g = int(g * 0.45 + DIGIT_MID[1] * 0.55)
    b = int(b * 0.45 + DIGIT_MID[2] * 0.55)
    return (min(255, r), min(255, g), min(255, b))


def _glyph_to_pixels(img_l, ox, oy):
    """Convert grayscale glyph image to {(x,y):(r,g,b)} with soft AA."""
    w, h = img_l.size
    px = img_l.load()
    lit = {}
    for y in range(h):
        for x in range(w):
            a = px[x, y]
            if a < 20:
                continue
            base = _shade_rgb(y, h)
            # Anti-alias: scale color by coverage
            cov = a / 255.0
            # Slight boost so mid AA still reads
            cov = min(1.0, cov * 1.15)
            rgb = tuple(min(255, int(c * cov)) for c in base)
            lit[(ox + x, oy + y)] = rgb
    return lit


class Glyph(object):
    """One character (digit or colon) as a pixel cloud with motion."""

    # Modes: idle | launch | gone | approach | dust | explode | miss_fall

    def __init__(self, ch, pixels, cx, cy):
        self.ch = ch
        self.home = dict(pixels)          # local absolute panel coords
        self.cx = float(cx)               # center x for rocket axis
        self.cy = float(cy)
        self.dx = 0.0
        self.dy = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.mode = "idle"
        self.t = 0.0
        self.exhaust = []                 # [x,y,life,rgb]
        self.smoke = []                   # [x,y,vx,vy,life,rgb]
        self.debris = []                  # [x,y,vx,vy,life,rgb]
        self.land_speed = 1.0
        self.outcome = "perfect"          # perfect | crash | miss | collide
        self.safe_retry = False
        self.collide_idx = None           # neighbor index to smash into
        self._pad_smoke_done = False
        self.tilt = 0.0                   # radians — L/R sway when out of control
        self.fuel = 1.0                   # 0..1 remaining (bright fraction)
        self.fuel_epoch = None            # when refuel began (None = full/idle)
        self.fuel_window = None           # seconds to fill (None = rest of minute)
        self._fuel_path = 1.0             # descent distance for matched burn
        self._fuel_empty_at = 1.0         # progress at which fuel hits 0
        self._saved_pixels = None
        self._saved_cx = 0.0
        self._saved_cy = 0.0
        self.slot_index = 0

    def begin_refuel(self, epoch=None, fast=False):
        """
        Start pre-launch fueling at the current second.
        Minute-ones: fill over remaining minute (e.g. 52s if :08).
        Other digits: fill quickly (FUEL_FAST_SECONDS), still one pixel at a time.
        """
        if epoch is None:
            epoch = _minute_elapsed()
        self.fuel_epoch = max(0.0, min(59.999, float(epoch)))
        if fast:
            self.fuel_window = float(FUEL_FAST_SECONDS)
        else:
            self.fuel_window = max(0.05, 60.0 - self.fuel_epoch)
        self.fuel = 0.0
        self.dx = self.dy = 0.0
        self.vx = self.vy = 0.0
        self.tilt = 0.0
        self.mode = "idle"
        self.t = 0.0

    def set_full_bright(self):
        """Settled digit that is not fueling for next change."""
        self.fuel_epoch = None
        self.fuel_window = None
        self.fuel = 1.0
        self.dx = self.dy = 0.0
        self.vx = self.vy = 0.0
        self.tilt = 0.0
        self.mode = "idle"
        self.t = 0.0

    def set_pixels(self, pixels, cx, cy, refuel=False):
        self.home = dict(pixels)
        self.cx = float(cx)
        self.cy = float(cy)
        self.dx = self.dy = 0.0
        self.vx = self.vy = 0.0
        self.mode = "idle"
        self.t = 0.0
        self.exhaust = []
        self.smoke = []
        self.debris = []
        self.outcome = "perfect"
        self.safe_retry = False
        self.collide_idx = None
        self._pad_smoke_done = False
        self.tilt = 0.0
        if refuel:
            self.begin_refuel(fast=(self.slot_index != SLOT_MINUTE_ONES))
        else:
            self.fuel = 1.0
            self.fuel_epoch = None
            self.fuel_window = None

    def begin_launch(self):
        self.mode = "launch"
        self.t = 0.0
        self.dx = self.dy = 0.0
        # Stored for after the pad-hold; no motion until LAUNCH_HOLD_SECONDS
        self.vx = random.uniform(-4.0, 4.0)
        self.vy = -2.0
        self.exhaust = []
        self.smoke = []
        self.debris = []
        self.outcome = "perfect"
        self.safe_retry = False
        self.collide_idx = None
        self._pad_smoke_done = False
        self.tilt = 0.0
        # Blast-off is fully fueled — keep full bright look for the whole ascent
        self.fuel = 1.0
        self.fuel_epoch = None
        self.fuel_window = None
        self._fuel_path = max(8.0, self.cy + 14.0)
        # Immediate ignition burst on the pad
        self._spawn_jet(count=10, intensity=1.3, spit=True, crash=False)

    def begin_approach(self, pixels, cx, cy, safe=False):
        self.home = dict(pixels)
        self._saved_pixels = dict(pixels)
        self._saved_cx = float(cx)
        self._saved_cy = float(cy)
        self.cx = float(cx)
        self.cy = float(cy)
        self.dx = random.uniform(-1.4, 1.4)
        self.dy = -(cy + random.uniform(16, 26))
        self.vx = 0.0
        self.vy = 0.0
        self.safe_retry = bool(safe)
        self.collide_idx = None
        self._pad_smoke_done = False
        self.tilt = 0.0
        self._fuel_path = max(1.0, -self.dy)
        self.fuel = 1.0
        # Speeds are 2× prior ranges (slowest descent is twice as fast)
        if self.safe_retry:
            self.outcome = "perfect"
            self.land_speed = random.uniform(1.80, 2.40)
            # Matched burn: empty exactly at touchdown
            self._fuel_empty_at = 1.0
        else:
            self.outcome = _pick_landing_outcome()
            if self.outcome == "crash":
                self.land_speed = random.uniform(3.6, 5.6)
                # Runs dry mid-descent → guaranteed crash
                self._fuel_empty_at = random.uniform(0.42, 0.68)
            elif self.outcome == "miss":
                self.land_speed = random.uniform(3.0, 4.5)
                # Dry just before pad, then falls through
                self._fuel_empty_at = random.uniform(0.88, 0.97)
            elif self.outcome == "collide":
                self.land_speed = random.uniform(2.4, 3.8)
                self.dx = random.uniform(-2.5, 2.5)
                self._fuel_empty_at = random.uniform(0.55, 0.85)
            else:
                # Perfect — fuel timed to hit zero at the pad
                self._fuel_empty_at = 1.0
                roll = random.random()
                if roll < 0.40:
                    self.land_speed = random.uniform(1.70, 2.40)
                elif roll < 0.78:
                    self.land_speed = random.uniform(2.50, 3.50)
                else:
                    self.land_speed = random.uniform(3.70, 4.80)
        self.mode = "approach"
        self.t = 0.0
        self.exhaust = []
        self.smoke = []
        self.debris = []

    def _sync_fuel_descent(self):
        """Burn fuel vs descent progress. empty_at=1 → dry exactly at pad."""
        path = max(1e-3, self._fuel_path)
        dist_left = max(0.0, -self.dy)
        progress = max(0.0, min(1.0, 1.0 - dist_left / path))
        empty_at = max(0.15, float(self._fuel_empty_at))
        self.fuel = max(0.0, 1.0 - progress / empty_at)

    def _sync_fuel_ascent(self):
        """Consume fuel while blasting off the panel."""
        path = max(1e-3, self._fuel_path)
        gone = max(0.0, -self.dy)
        self.fuel = max(0.0, 1.0 - gone / path)

    def _use_crash_fire(self):
        return self.outcome in ("crash", "collide") or self.mode == "explode"

    def _spawn_jet(self, count=3, intensity=1.0, spit=False, crash=None):
        """
        Starship Heavy / Raptor plume simulation.
        Normal: elongated blue-white jet with sparkle fringe.
        Crash: dense yellow/orange/red fireball spray.
        """
        intensity = max(0.15, min(1.8, float(intensity)))
        is_crash = self._use_crash_fire() if crash is None else bool(crash)
        palette = CRASH_FIRE if is_crash else JET_BLUE
        base_y = self.cy + self.dy + (3.2 if not spit else 3.8)
        # Starship: long thin plume; crash: wide spray
        if is_crash:
            spread = 3.5 + 3.5 * intensity
            plume = 2.0 + 5.0 * intensity
            life_lo, life_hi = 0.16, 0.36
        else:
            spread = 1.2 + 1.6 * intensity
            plume = 3.5 + 7.0 * intensity   # long blue column under booster
            life_lo, life_hi = 0.12, 0.28
        for _ in range(count):
            # Core samples stay tighter/brighter; fringe wider
            core = random.random() < 0.45
            sx = spread * (0.35 if core else 1.0)
            self.exhaust.append([
                self.cx + self.dx + random.uniform(-sx, sx),
                base_y + random.uniform(0, plume),
                random.uniform(life_lo, life_hi) * (0.8 + 0.5 * intensity),
                random.choice(palette[:4] if core and not is_crash else palette),
            ])

    def _spawn_smoke_puff(self, burst=False, at_y=None):
        """White dust/smoke under the digit (call only after flames are cleared)."""
        base_y = (self.cy + self.dy + 4.0) if at_y is None else float(at_y)
        count = random.randint(12, 18) if burst else random.randint(2, 5)
        for _ in range(count):
            self.smoke.append([
                self.cx + self.dx + random.uniform(-3.8, 3.8),
                base_y + random.uniform(-0.5, 2.2),
                random.uniform(-7.0, 7.0),
                random.uniform(-11.0, -3.0),
                random.uniform(0.55, 1.2) if burst else random.uniform(0.35, 0.75),
                random.choice(SMOKE_COLORS),
            ])

    def _clear_flames(self):
        """Hard-stop all jet/fire particles."""
        self.exhaust = []

    def _start_dust(self, next_mode="idle", at_y=None, burst=True):
        """
        Extinguish every flame, then emit white dust/smoke.
        next_mode: where to go after dust finishes (idle | miss_fall | reapproach).
        """
        self._clear_flames()
        self._spawn_smoke_puff(burst=burst, at_y=at_y)
        self.mode = "dust"
        self.t = 0.0
        self._dust_next = next_mode
        self._pad_smoke_done = True

    def _explode(self, keep_saved=True):
        """Shatter into debris + yellow/orange/red fireball (dust comes after flames die)."""
        self.mode = "explode"
        self.t = 0.0
        self._pad_smoke_done = False
        # Sample pixels into debris
        items = list(self.home.items())
        if len(items) > 48:
            items = random.sample(items, 48)
        for (x, y), rgb in items:
            ang = random.uniform(0, math.tau)
            spd = random.uniform(18.0, 58.0)
            self.debris.append([
                float(x) + self.dx,
                float(y) + self.dy,
                math.cos(ang) * spd + random.uniform(-10, 10),
                math.sin(ang) * spd - random.uniform(5, 28),
                random.uniform(0.45, 0.95),
                rgb,
            ])
        # Heavy crash fire only — dust waits until flames are cleared
        for _ in range(22):
            self._spawn_jet(count=1, intensity=1.6, spit=True, crash=True)
        self.home = {}
        if not keep_saved:
            pass

    def prepare_victim_reland(self):
        """After being smashed while idle — save seat for a perfect re-land."""
        if self._saved_pixels is None and self.home:
            self._saved_pixels = dict(self.home)
            self._saved_cx = self.cx
            self._saved_cy = self.cy
        self.outcome = "crash"
        self._explode()

    def world_center(self):
        return (self.cx + self.dx, self.cy + self.dy)

    def update(self, dt, panel_h=32):
        self.t += dt
        if self.mode == "launch":
            # Stay fully bright the entire launch (hold + climb)
            self.fuel = 1.0
            if self.t < LAUNCH_HOLD_SECONDS:
                # Flames blow on the pad; ascent delayed
                self.dx = self.dy = 0.0
                if random.random() < 0.98:
                    self._spawn_jet(count=5, intensity=1.25, spit=True, crash=False)
                if random.random() < 0.35:
                    self._spawn_jet(count=3, intensity=1.4, spit=True, crash=False)
            else:
                # Liftoff — full fuel look preserved (no ascent burn visual)
                self.vy -= 38.0 * dt
                self.vx += math.sin(self.t * 14.0) * 10.0 * dt
                self.dx += self.vx * dt
                self.dy += self.vy * dt
                if random.random() < 0.92:
                    self._spawn_jet(count=4, intensity=1.1, crash=False)
                if self.cy + self.dy < -12:
                    self.mode = "gone"

        elif self.mode == "approach":
            spd = max(0.7, float(self.land_speed))

            if self.outcome == "miss":
                # Intentional overshoot — never grabs the pad
                self.dx *= (1.0 - 0.5 * dt)
                sink = (2.2 + min(4.0, max(0.0, -self.dy) * 0.2)) * spd
                self.dy += sink * dt
                self._sync_fuel_descent()
                if self.fuel > 0.02 and random.random() < 0.9:
                    self._spawn_jet(count=4, intensity=1.0, crash=False)
                if self.dy >= 0.0 and not self._pad_smoke_done:
                    self.dy = 0.0
                    self.fuel = 0.0
                    self.vx = self.vy = 0.0
                    self._start_dust(
                        next_mode="miss_fall",
                        at_y=self.cy + 4.0,
                        burst=True,
                    )

            elif self.outcome == "crash":
                # Tumbling out-of-control — tilt left/right like a failing booster
                amp = 0.28 + 0.40 * min(1.0, max(0.0, 1.0 + self.dy / 28.0))
                self.tilt = math.sin(self.t * 6.5) * amp
                self.dx += math.sin(self.t * 11.0) * 10.0 * dt * (spd * 0.35)
                self.dx *= (1.0 - 0.55 * dt)
                sink = (3.8 + min(9.0, max(0.0, -self.dy) * 0.5)) * spd * 0.5
                self.dy += sink * dt
                self._sync_fuel_descent()
                if self.fuel > 0.02 and random.random() < 0.96:
                    self._spawn_jet(count=5, intensity=1.3, crash=True)
                if self.dy >= 0.0:
                    self.dy = 0.0
                    self.dx = 0.0
                    self.fuel = 0.0
                    self.vx = self.vy = 0.0
                    self.tilt = 0.0
                    self._explode()

            elif self.outcome == "collide":
                amp = 0.22 + 0.32 * min(1.0, max(0.0, 1.0 + self.dy / 28.0))
                self.tilt = math.sin(self.t * 5.2 + 0.8) * amp
                if self.collide_idx is not None and hasattr(self, "_collide_tx"):
                    want = self._collide_tx - self.cx
                    self.dx += (want - self.dx) * min(1.0, 2.2 * dt)
                else:
                    self.dx += math.sin(self.t * 7.0) * 6.0 * dt
                sink = (2.0 + min(3.5, max(0.0, -self.dy) * 0.18)) * spd
                self.dy += sink * dt
                self._sync_fuel_descent()
                if self.fuel > 0.02 and random.random() < 0.9:
                    self._spawn_jet(count=4, intensity=1.05, crash=False)
                if self.dy >= 0.0:
                    self.dy = 0.0
                    self.dx = 0.0
                    self.fuel = 0.0
                    self.tilt = 0.0
                    self._explode()

            else:
                # Perfect / controlled — fuel timed to empty at the pad
                self.tilt = 0.0
                self.dx *= (1.0 - 1.5 * dt)
                sink = (1.0 + min(1.6, max(0.0, -self.dy) * 0.11)) * spd
                self.dy += sink * dt
                self._sync_fuel_descent()
                # Dry tanks before pad → tumble crash
                if self.fuel <= 0.0 and self.dy < -1.5:
                    self.outcome = "crash"
                elif self.fuel > 0.02 and random.random() < 0.9:
                    self._spawn_jet(count=4, intensity=0.9 + 0.15 * spd, crash=False)
                if self.outcome == "perfect" and self.dy >= 0.0:
                    self.dy = 0.0
                    self.dx = 0.0
                    self.fuel = 0.0
                    self.vx = self.vy = 0.0
                    self.tilt = 0.0
                    self._start_dust(next_mode="idle", burst=True)

        elif self.mode == "dust":
            # No flames during dust; keep exhaust empty
            self._clear_flames()
            self.tilt = 0.0
            if self._dust_next != "miss_fall":
                self.dx = self.dy = 0.0
            # Brief extra wisps
            if self.t < 0.45 and random.random() < 0.4:
                self._spawn_smoke_puff(burst=False)
            dust_done = self.t >= 0.85 or (self.t >= 0.4 and not self.smoke)
            if dust_done:
                nxt = getattr(self, "_dust_next", "idle")
                if nxt == "miss_fall":
                    self.mode = "miss_fall"
                    self.t = 0.0
                    self.vy = 28.0 + 10.0 * max(0.7, float(self.land_speed))
                elif nxt == "reapproach":
                    px = self._saved_pixels or {}
                    self.begin_approach(px, self._saved_cx, self._saved_cy, safe=True)
                else:
                    # Landed dry — start refuel at current second (no full-bright flash)
                    self.begin_refuel(
                        fast=(self.slot_index != SLOT_MINUTE_ONES),
                    )

        elif self.mode == "miss_fall":
            # Rapid exit off the bottom after missing the pad
            self.tilt = math.sin(self.t * 8.0) * 0.35
            self.vy += 70.0 * dt
            self.dy += self.vy * dt
            self.dx += math.sin(self.t * 9.0) * 8.0 * dt
            if random.random() < 0.85:
                self._spawn_jet(count=3, intensity=0.9, crash=False)
            if self.cy + self.dy > panel_h + 14:
                px = self._saved_pixels or {}
                self.begin_approach(px, self._saved_cx, self._saved_cy, safe=True)

        elif self.mode == "explode":
            # Crash fireball, then kill flames + dust before re-land
            self.tilt = 0.0
            if random.random() < 0.55 and self.t < 0.45:
                self._spawn_jet(count=2, intensity=1.2, spit=True, crash=True)
            if not self._pad_smoke_done and (
                self.t >= 0.75 or (self.t > 0.45 and not self.exhaust)
            ):
                self._start_dust(next_mode="reapproach", burst=True)

        # Age jet particles (skip aging if dust just cleared them this frame)
        if self.mode != "dust":
            alive = []
            for p in self.exhaust:
                p[1] += 22.0 * dt
                p[0] += random.uniform(-8.0, 8.0) * dt
                p[2] -= dt * 1.05
                if p[2] > 0:
                    alive.append(p)
            self.exhaust = alive
        else:
            self.exhaust = []

        alive_s = []
        for p in self.smoke:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[2] *= (1.0 - 0.8 * dt)
            p[3] *= (1.0 - 0.35 * dt)
            p[3] -= 1.5 * dt
            p[4] -= dt * 0.7
            if p[4] > 0:
                alive_s.append(p)
        self.smoke = alive_s

        alive_d = []
        for p in self.debris:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[3] += 55.0 * dt
            p[2] *= (1.0 - 0.4 * dt)
            p[4] -= dt * 1.1
            if p[4] > 0:
                alive_d.append(p)
        self.debris = alive_d

    def draw(self, canvas, panel_w, panel_h, fuel_elapsed=None, fueling=False):
        set_px = canvas.SetPixel
        if self.mode not in ("gone", "explode") and self.home:
            pix = self.home
            # Idle + fueling: always respect fuel line (never flash full bright)
            if self.mode == "idle" and self.ch != ":":
                if self.fuel_epoch is not None and fuel_elapsed is not None:
                    pix = _fuel_pixels_for_refuel(
                        self.home, fuel_elapsed, self.fuel_epoch, self.fuel_window,
                    )
                elif fueling and fuel_elapsed is not None:
                    win = (
                        FUEL_FAST_SECONDS
                        if self.slot_index != SLOT_MINUTE_ONES
                        else max(0.05, 60.0 - fuel_elapsed)
                    )
                    pix = _fuel_pixels_for_refuel(
                        self.home, fuel_elapsed, fuel_elapsed, win,
                    )
                elif self.fuel < 0.999:
                    pix = _pixels_for_fuel_level(self.home, self.fuel)
            # Launch: full fuel (original bright glyph). Descent: fuel burns down.
            elif self.mode == "launch":
                pix = self.home  # full bright — tanks topped for takeoff
            elif self.mode in ("approach", "miss_fall", "dust"):
                pix = _pixels_for_fuel_level(self.home, self.fuel)
            upright = (
                self.mode == "idle"
                and abs(self.dx) < 1e-6
                and abs(self.dy) < 1e-6
                and abs(self.tilt) < 1e-4
            )
            if upright:
                for (x, y), rgb in pix.items():
                    if 0 <= x < panel_w and 0 <= y < panel_h:
                        set_px(x, y, *rgb)
            else:
                # Translate + optional tilt around rocket axis
                ca = math.cos(self.tilt)
                sa = math.sin(self.tilt)
                ox, oy = self.dx, self.dy
                for (x, y), rgb in pix.items():
                    lx = x - self.cx
                    ly = y - self.cy
                    rx = lx * ca - ly * sa
                    ry = lx * sa + ly * ca
                    px = int(round(self.cx + ox + rx))
                    py = int(round(self.cy + oy + ry))
                    if 0 <= px < panel_w and 0 <= py < panel_h:
                        set_px(px, py, *rgb)

        for x, y, life, rgb in self.exhaust:
            px, py = int(round(x)), int(round(y))
            if 0 <= px < panel_w and 0 <= py < panel_h:
                fade = max(0.18, min(1.0, life * 5.5))
                set_px(
                    px, py,
                    min(255, int(rgb[0] * fade)),
                    min(255, int(rgb[1] * fade)),
                    min(255, int(rgb[2] * fade)),
                )

        for x, y, _vx, _vy, life, rgb in self.smoke:
            px, py = int(round(x)), int(round(y))
            if 0 <= px < panel_w and 0 <= py < panel_h:
                fade = max(0.12, min(1.0, life * 1.4))
                set_px(
                    px, py,
                    min(255, int(rgb[0] * fade)),
                    min(255, int(rgb[1] * fade)),
                    min(255, int(rgb[2] * fade)),
                )

        for x, y, _vx, _vy, life, rgb in self.debris:
            px, py = int(round(x)), int(round(y))
            if 0 <= px < panel_w and 0 <= py < panel_h:
                fade = max(0.2, min(1.0, life * 1.8))
                set_px(
                    px, py,
                    min(255, int(rgb[0] * fade)),
                    min(255, int(rgb[1] * fade)),
                    min(255, int(rgb[2] * fade)),
                )


def _render_chars(text, panel_w, panel_h, font_path, layout=None):
    """
    Render each character of HH:MM into fixed monospaced slots.
    Slot positions never depend on which digits are shown — no jitter.
    layout: optional cached (font, size, digit_w, colon_w, digit_h, x0, y0)
    Returns (glyphs, size, layout).
    """
    if layout is None:
        font, size, digit_w, colon_w, digit_h = _best_font(
            font_path, panel_w, panel_h, "23:59",
        )
        total_w = _fixed_layout_width(digit_w, colon_w)
        x0 = (panel_w - total_w) // 2
        y0 = (panel_h - digit_h) // 2
        layout = (font, size, digit_w, colon_w, digit_h, x0, y0)
    else:
        font, size, digit_w, colon_w, digit_h, x0, y0 = layout

    # Fixed slot origins for H H : M M
    slot_widths = [digit_w, digit_w, colon_w, digit_w, digit_w]
    slot_gaps = [0, CHAR_GAP, COLON_GAP, COLON_GAP, CHAR_GAP]
    # gaps before each slot: after first digit CHAR_GAP, before colon COLON_GAP, etc.
    # Layout: D + CHAR_GAP + D + COLON_GAP + : + COLON_GAP + D + CHAR_GAP + D
    slot_x = []
    x = x0
    for i, sw in enumerate(slot_widths):
        if i == 0:
            pass
        elif i == 1:
            x += CHAR_GAP
        elif i == 2:
            x += COLON_GAP
        elif i == 3:
            x += COLON_GAP
        elif i == 4:
            x += CHAR_GAP
        slot_x.append(x)
        x += sw

    # Ensure text is 5 chars HH:MM
    chars = list(text)
    if len(chars) != 5:
        chars = list(_now_hhmm())

    glyphs = []
    for i, ch in enumerate(chars):
        sw = slot_widths[i]
        sx = slot_x[i]
        probe = Image.new("L", (panel_w * 2, panel_h * 2), 0)
        draw = ImageDraw.Draw(probe)
        bb, cw, ch_h = _measure_char(draw, font, ch)
        # Center glyph inside fixed slot (integer math only — no float jitter)
        ox = sx + (sw - cw) // 2
        oy = y0 + (digit_h - ch_h) // 2
        pad = 2
        raw = Image.new("L", (cw + pad * 2, ch_h + pad * 2), 0)
        d = ImageDraw.Draw(raw)
        d.text((pad - bb[0], pad - bb[1]), ch, font=font, fill=255)
        try:
            raw = raw.filter(ImageFilter.GaussianBlur(radius=0.45))
        except Exception:
            pass
        pixels = _glyph_to_pixels(raw, ox - pad, oy - pad)
        pixels = {
            (px, py): rgb
            for (px, py), rgb in pixels.items()
            if 0 <= px < panel_w and 0 <= py < panel_h and sum(rgb) > 12
        }
        # Rocket axis = fixed slot center (never moves with glyph ink bounds)
        cx = sx + sw / 2.0
        cy = y0 + digit_h / 2.0
        g = Glyph(ch, pixels, cx, cy)
        g.slot_index = i
        glyphs.append(g)

    return glyphs, size, layout


def _assign_collide_target(glyphs, attacker):
    """Pick a neighbor digit (not colon, not self) for a mid-air collision."""
    candidates = []
    for i, g in enumerate(glyphs):
        if g is attacker:
            continue
        if g.ch == ":":
            continue
        if g.mode in ("gone", "explode", "launch", "miss_fall"):
            continue
        candidates.append(i)
    if not candidates:
        attacker.outcome = "crash"
        attacker.collide_idx = None
        return
    # Prefer nearest horizontal neighbor
    candidates.sort(key=lambda i: abs(glyphs[i].cx - attacker.cx))
    idx = candidates[0]
    attacker.collide_idx = idx
    attacker._collide_tx = glyphs[idx].cx + random.uniform(-1.5, 1.5)


def _check_midair_collisions(glyphs):
    """If a collide-approach gets close to another digit, both explode."""
    for i, g in enumerate(glyphs):
        if g.mode != "approach" or g.outcome != "collide":
            continue
        if g.collide_idx is None:
            _assign_collide_target(glyphs, g)
            if g.outcome != "collide":
                continue
        j = g.collide_idx
        if j is None or j < 0 or j >= len(glyphs):
            continue
        other = glyphs[j]
        if other.mode in ("gone", "explode", "launch", "miss_fall"):
            continue
        gx, gy = g.world_center()
        ox, oy = other.world_center()
        # Hit when near pad altitude and overlapping horizontally
        if abs(gx - ox) < 7.5 and abs(gy - oy) < 10.0 and g.dy > -12:
            print(
                f"[RocketClock]   COLLISION! {g.ch!r} smashed into {other.ch!r}"
            )
            # Attacker always re-lands its intended digit
            g._explode()
            # Victim destroyed — re-land same (or pending next if mid-swap)
            if other.mode != "explode":
                if getattr(other, "_next", None) is not None:
                    nxt = other._next
                    other.ch = nxt.ch
                    other._saved_pixels = dict(nxt.home)
                    other._saved_cx = nxt.cx
                    other._saved_cy = nxt.cy
                    other._next = None
                elif other.home:
                    other._saved_pixels = dict(other.home)
                    other._saved_cx = other.cx
                    other._saved_cy = other.cy
                other.prepare_victim_reland()


def PlayRocketClock(Duration=10, StopEvent=None):
    """Full-panel smooth digital HH:MM — digits rocket away, new ones land."""
    panel_w = int(getattr(LED, "HatWidth", 64) or 64)
    panel_h = int(getattr(LED, "HatHeight", 32) or 32)

    try:
        canvas = LED.TheMatrix.CreateFrameCanvas()
    except Exception:
        canvas = LED.Canvas

    try:
        run_min = float(Duration)
    except (TypeError, ValueError):
        run_min = 10.0
    if run_min <= 0:
        run_min = 10.0

    font_path, font_name = _resolve_font_path()
    tick = pygame.time.Clock() if HAS_PYGAME else None
    start = time.time()
    hi, mid, lo = _pick_clock_palette()
    current = _now_hhmm()
    # Fixed layout cached once — digit slots never move (uses current palette)
    glyphs, font_size, layout = _render_chars(current, panel_w, panel_h, font_path)
    layout_x0, layout_y0 = layout[5], layout[6]

    def _apply_refuel_state(glyph_list, face_text):
        """Changing digits begin refuel; minute-ones slow, other digits fast."""
        elapsed = _minute_elapsed()
        changing = _changing_slot_indices(face_text, _upcoming_hhmm())
        for i, g in enumerate(glyph_list):
            g.slot_index = i
            if i in changing:
                # Minute ones: remaining minute. Other digits: quick one-px-at-a-time.
                g.begin_refuel(elapsed, fast=(i != SLOT_MINUTE_ONES))
            else:
                g.set_full_bright()

    _apply_refuel_state(glyphs, current)

    phase = "steady"  # steady | rocket
    rocket_t0 = 0.0
    pending_text = current

    print(
        f"[RocketClock] {panel_w}x{panel_h}  font={font_name}@{font_size}  "
        f"fixed slots @({layout_x0},{layout_y0})  "
        f"smooth AA  rocket={ROCKET_SECONDS}s  duration={run_min} min  "
        f"refuel_epoch={_minute_elapsed():.1f}s  "
        f"color hi={hi} mid={mid} lo={lo}"
    )

    try:
        while True:
            if _stop(StopEvent):
                print("[RocketClock] StopEvent — exit")
                break
            if time.time() - start > run_min * 60.0:
                print("[RocketClock] Duration reached — exit")
                break

            now = time.time()
            hhmm = _now_hhmm()
            dt = 1.0 / TARGET_FPS

            if phase == "steady":
                if hhmm != current:
                    pending_text = hhmm
                    new_glyphs, _, layout = _render_chars(
                        pending_text, panel_w, panel_h, font_path, layout=layout,
                    )
                    # Match by index; launch any slot whose character changed
                    for i, g in enumerate(glyphs):
                        if i < len(new_glyphs) and g.ch != new_glyphs[i].ch:
                            g.begin_launch()
                        elif i < len(new_glyphs):
                            # Unchanged: same fixed slot pixels/centers
                            g.set_pixels(
                                new_glyphs[i].home, new_glyphs[i].cx, new_glyphs[i].cy,
                            )
                    phase = "rocket"
                    rocket_t0 = now
                    for i, g in enumerate(glyphs):
                        if i < len(new_glyphs) and g.mode == "launch":
                            g._next = new_glyphs[i]
                        else:
                            g._next = None
                    print(f"[RocketClock] {current} → {pending_text}  rocket launch")

            elif phase == "rocket":
                t = now - rocket_t0
                for g in glyphs:
                    prev_mode = g.mode
                    g.update(dt, panel_h=panel_h)
                    # When launch clears the top, bring the replacement in
                    if g.mode == "gone" and getattr(g, "_next", None) is not None:
                        nxt = g._next
                        g.ch = nxt.ch
                        g.begin_approach(nxt.home, nxt.cx, nxt.cy, safe=False)
                        g._next = None
                        if g.outcome == "collide":
                            _assign_collide_target(glyphs, g)
                        print(
                            f"[RocketClock]   slot land {g.ch!r}  "
                            f"{g.outcome} spd={g.land_speed:.2f}"
                        )
                    if prev_mode != "explode" and g.mode == "explode":
                        print(f"[RocketClock]   BOOM! digit {g.ch!r} shattered")
                    if prev_mode == "approach" and g.mode == "miss_fall":
                        print(f"[RocketClock]   MISS! digit {g.ch!r} overshot pad")
                    if prev_mode in ("explode", "miss_fall") and g.mode == "approach":
                        print(f"[RocketClock]   re-land {g.ch!r}  spd={g.land_speed:.2f}")

                _check_midair_collisions(glyphs)

                # Done when every glyph is idle (jet + any retry done)
                all_settled = all(
                    g.mode == "idle"
                    and getattr(g, "_next", None) is None
                    and not g.smoke
                    and not g.debris
                    for g in glyphs
                )
                busy = any(
                    g.mode in (
                        "explode", "approach", "dust",
                        "launch", "gone", "miss_fall",
                    )
                    or getattr(g, "_next", None) is not None
                    for g in glyphs
                )
                if all_settled or (t >= ROCKET_SECONDS and not busy):
                    # Snap seats; refuel changing digits from *now* (no full-bright flash)
                    fresh, _, layout = _render_chars(
                        pending_text, panel_w, panel_h, font_path, layout=layout,
                    )
                    glyphs = fresh
                    current = pending_text
                    _apply_refuel_state(glyphs, current)
                    phase = "steady"
                    print(
                        f"[RocketClock] settled {current}  "
                        f"refuel@{_minute_elapsed():.1f}s"
                    )
                elif t >= ROCKET_SECONDS + 8.0:
                    fresh, _, layout = _render_chars(
                        pending_text, panel_w, panel_h, font_path, layout=layout,
                    )
                    glyphs = fresh
                    current = pending_text
                    _apply_refuel_state(glyphs, current)
                    phase = "steady"
                    print(f"[RocketClock] settled {current} (timeout)")

            # Draw — fueling digits respect fuel line / remaining-minute window
            try:
                canvas.Fill(*BG)
            except Exception:
                pass
            elapsed = _minute_elapsed()
            if phase == "steady":
                fuel_slots = _changing_slot_indices(current, _upcoming_hhmm())
                # Keep epoch if already fueling; only init missing epochs
                for i, g in enumerate(glyphs):
                    if i in fuel_slots and g.fuel_epoch is None and g.mode == "idle":
                        g.begin_refuel(elapsed, fast=(i != SLOT_MINUTE_ONES))
            else:
                fuel_slots = set()
            for i, g in enumerate(glyphs):
                g.draw(
                    canvas, panel_w, panel_h,
                    fuel_elapsed=elapsed,
                    fueling=(i in fuel_slots or g.fuel_epoch is not None),
                )

            try:
                canvas = LED.TheMatrix.SwapOnVSync(canvas)
                LED.Canvas = canvas
            except Exception:
                pass

            if tick:
                tick.tick(TARGET_FPS)
            else:
                time.sleep(1.0 / TARGET_FPS)

    except KeyboardInterrupt:
        print("[RocketClock] Interrupted")

    try:
        LED.ClearBuffers()
        LED.TheMatrix.Clear()
    except Exception:
        pass


def LaunchRocketClock(Duration=10, ShowIntro=False, StopEvent=None):
    try:
        LED.LoadConfigData()
    except Exception:
        pass
    PlayRocketClock(Duration=Duration, StopEvent=StopEvent)


if __name__ == "__main__":
    try:
        LaunchRocketClock(Duration=60, StopEvent=None)
    except KeyboardInterrupt:
        print("Exiting RocketClock.")
