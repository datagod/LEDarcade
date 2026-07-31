# =====================================================================================
# WATER CLOCK — shaded HH:MM with sloshing water
#
# Fixed upper seat: HH:MM in a soft multi-shade 3x5 digit font (scaled).
# Tide water washes around solid clock glyphs. A little sailboat tries to
# cross shore-to-shore under wind + current. Once a minute the water rises
# Starts calm at the pier with the boat ready to sail. Later: five-minute
# fishing trips, dock unload with scoreboard, cast off, weather resumes.
# Yellow sun + pale moon follow Ottawa civil times on a fixed sky path.
#
# Launch:
#   LEDsim key 6 / LEDpanel / action "waterclock" / ?waterclock
# =====================================================================================

from __future__ import annotations

import math
import random
import time
from datetime import date, datetime, timedelta, timezone

import LEDarcade as LED

LED.Initialize()

try:
    import pygame
    HAS_PYGAME = True
except Exception:
    HAS_PYGAME = False


# ---------------- Configuration ----------------
TARGET_FPS = 28
USE_24H = True

# Digit look (3×5 base from LEDarcade DigitList, scaled up)
DIGIT_W0 = 3
DIGIT_H0 = 5
DIGIT_ZOOM = 2                 # → 6×10 glyphs
DIGIT_GAP = 2
COLON_W = 2
# Soft cool-white with cyan/blue shading (reads well over dark + water)
DIGIT_HI = (230, 245, 255)     # top/left highlight
DIGIT_MID = (160, 200, 230)    # body
DIGIT_LO = (60, 100, 140)      # bottom/right shade
DIGIT_EDGE = (30, 50, 75)      # soft outline
COLON_RGB = (180, 220, 255)

# ---- Tide water (rise / drain / slosh) ----
# Tall enough that high tide can cover the lower part of the HH:MM glyphs
WATER_BAND_FRAC = 0.62         # fraction of height reserved for water
WATER_MIN_FRAC = 0.10          # min mean fill of the band (calm low tide)
WATER_MAX_FRAC = 0.98          # max mean fill — reaches bottom of the clock
MAX_DROPLETS = 24              # was 48 — half the splash particles
SLOSH_PERIOD = 4.6             # seconds per left↔right slosh (slower = calmer)
LEVEL_PERIOD = 18.0            # seconds for a full rise/drain breathe
VISCOSITY = 0.32               # surface smoothing (higher = flatter / calmer)
# Base slosh is mild; sea-state multiplies this (calm ~low, rough ~high)
SLOSH_STRENGTH = 0.22          # calm-default wave tilt as fraction of band
WATER_GRAVITY = 0.18
SPLASH_CHANCE = 0.02           # was 0.04 — half the splash spawn rate
# Sea state: biased calm; rough bursts are shorter but can get wild
SEA_CALM_CHANCE = 0.72         # probability a new weather spell is calm
SEA_CALM_DUR = (9.0, 20.0)     # calm spell length (seconds)
SEA_ROUGH_DUR = (2.5, 6.5)     # rough spell length (shorter storms)
SEA_CALM_SLOSH = (0.35, 0.70)  # multiplier on SLOSH_STRENGTH while calm
SEA_ROUGH_SLOSH = (1.8, 3.2)   # multiplier while rough (pretty rough)
SEA_CALM_WAVE = 0.08           # column wave amp as fraction of band
SEA_ROUGH_WAVE = 0.36          # column wave amp when rough

# Sailboat + wind / current
BOAT_SPEED = 4.8               # px/sec sail thrust baseline
BOAT_EDGE_PAD = 3
BOAT_GOAL_MARGIN = 4           # how close to a shore counts as "arrived"
# Forces on the hull (multipliers on normalized wind/current in [-1, 1])
CURRENT_PUSH = 3.2             # water current drift (px/sec at full current)
WIND_DRIFT = 1.4               # hull drift from wind even when not sailing well
WIND_SAIL_BONUS = 3.6          # extra speed when wind fills the sail (same way)
WIND_SAIL_BEAT = 0.42          # fraction of sail power when beating into wind
# Wind field (independent of water slosh current)
WIND_PERIOD = 11.0             # slow wind shift left↔right
WIND_GUST_CHANCE = 0.012
WIND_GUST_MIN = 1.2
WIND_GUST_MAX = 2.8
# Drop anchor when seas stay calm long enough (thresholds randomized per stop)
CALM_CURRENT = 0.16            # |tide flow| below this = calm current
CALM_WIND = 0.28               # |wind| below this = calm air
CALM_NEED_MIN = 2.0            # seconds of calm before considering anchor
CALM_NEED_MAX = 5.5
ANCHOR_MIN = 3.5               # stay put at least this long once anchored
ANCHOR_MAX = 10.0
ROUGH_WEIGH = 0.9              # seconds of rough water before weighing anchor
BOAT_HULL = (170, 100, 45)
BOAT_HULL_DARK = (110, 60, 25)
BOAT_SAIL = (245, 245, 255)
BOAT_MAST = (90, 65, 40)
BOAT_ANCHOR = (140, 140, 150)  # chain / anchor pixel
# Fishing line + hook (minute calm)
LINE_RGB = (160, 160, 170)
HOOK_RGB = (220, 200, 70)
HOOK_TIP_RGB = (255, 240, 120)  # bright point of the J

# ---- Fishing trip (calm → fish 5 min → dock → unload → sail off) ----
# After FISHING_INTERVAL: water rises + wind dies, boat fishes for
# FISHING_DURATION. Then calms home to a wooden pier on the right, unloads,
# shows catch count on a dock display, sails the other way, weather resumes.
FISHING_INTERVAL = 60.0        # seconds between full trips
FISHING_DURATION = 300.0       # five minutes of fishing
START_READY_HOLD = 5.0         # opening: docked at pier before first cast-off
FISHING_RISE_FRAC = 0.96       # target mean water fill while fishing / dock calm
FISHING_LINE_MIN = 3.0         # shallow drop (surface school)
FISHING_LINE_MAX = 11.0        # deep drop (bottom dwellers)
FISHING_LINE_SPEED = 2.8       # line pay-out px/sec
FISHING_REEL_SPEED = 5.5       # reel-in speed when a fish is on
FISHING_DEPTH_HOLD = (2.5, 5.5)  # seconds at a depth before re-dropping
FISH_COUNT_MIN = 3
FISH_COUNT_MAX = 6
FISH_SPEED = (3.5, 7.5)        # px/sec (small/medium)
FISH_SPEED_BIG = (2.2, 4.5)    # bigger fish are slower
FISH_INVESTIGATE_RANGE = 14.0  # how far fish notice the hook
FISH_HOOK_TOUCH = 1.35         # distance to count as touching the J
FISH_CATCH_FLASH = 1.4         # seconds the catch sits in the boat
FISH_RARE_CHANCE = 0.10        # chance of the rare big red per school
FISH_RESPAWN_EVERY = 18.0      # restock water during long fishing trips
BOAT_HOME_SPEED = 6.5          # px/sec sailing to pier / away
DOCK_HOLD = 0.6                # brief settle after tip touches dock
SAIL_LOWER_TIME = 2.2          # seconds to lower the sail before unload
UNLOAD_INTERVAL = 0.38         # seconds between fish tossed onto the pier
SCORE_HOLD = 2.8               # hold scoreboard after last fish
BOAT_BOW_OFFSET = 2            # hull-center → bow tip (sprite nose at +2)
PIER_WOOD = (150, 95, 45)
PIER_WOOD_DARK = (95, 55, 25)
PIER_POST = (110, 70, 35)
SCORE_RGB = (40, 255, 120)     # dock digital display
FISH_COLORS = (
    (255, 160, 40),
    (255, 90, 70),
    (240, 220, 60),
    (100, 200, 255),
    (200, 120, 255),
    (90, 230, 140),
)
FISH_RARE_RED = (230, 20, 35)  # rare big red

# Sun / Moon (Ottawa, Canada civil times → fixed sky path on panel)
OTTAWA_LAT = 45.4215
OTTAWA_LON = -75.6972          # west negative
SUN_CORE = (255, 230, 50)
SUN_GLOW = (255, 170, 30)
SUN_HALO = (180, 90, 15)
SUN_EDGE_PAD = 1               # inset from panel rim along the path
MOON_CORE = (230, 235, 250)    # cool silver
MOON_GLOW = (150, 160, 195)
MOON_HALO = (70, 80, 110)
MOON_EDGE_PAD = 1
# Upper-limb + refraction horizon (deg below geometric) for moon rise/set
MOON_HORIZON_ALT = -0.833
# Sunset-style glitter path on the water (same color as the body, distorted)
REFLECT_NEAR = 11.0           # start when body is within this many px of waterline
REFLECT_MAX = 0.85             # peak strength of sun/moon color on the path
REFLECT_DEPTH = 7              # how far the glitter runs down into the water
REFLECT_JITTER = 1.6           # max horizontal distortion (px) deeper in the path

BG = (0, 0, 4)
# Water palette (deep → surface foam)
WATER_DEEP = (8, 35, 90)
WATER_MID = (20, 90, 170)
WATER_TOP = (70, 170, 230)
WATER_FOAM = (180, 230, 255)
WATER_DROP = (120, 200, 255)


def _stop(StopEvent):
    try:
        return StopEvent is not None and StopEvent.is_set()
    except Exception:
        return False


def _clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def _lerp(a, b, t):
    return a + (b - a) * t


def _lerp_rgb(c0, c1, t):
    t = _clamp(t, 0.0, 1.0)
    return (
        int(c0[0] + (c1[0] - c0[0]) * t),
        int(c0[1] + (c1[1] - c0[1]) * t),
        int(c0[2] + (c1[2] - c0[2]) * t),
    )


# ---------------- Shaded digits ----------------
def _digit_grid(d):
    d = int(d) % 10
    try:
        g = LED.DigitList[d]
        if len(g) >= DIGIT_W0 * DIGIT_H0:
            return g
    except Exception:
        pass
    return [1] * (DIGIT_W0 * DIGIT_H0)


def _digit_pixel_size():
    return DIGIT_W0 * DIGIT_ZOOM, DIGIT_H0 * DIGIT_ZOOM


def _clock_total_width():
    dw, _dh = _digit_pixel_size()
    # HH : MM → 4 digits + colon + 3 gaps between the 5 pieces
    return 4 * dw + COLON_W + 3 * DIGIT_GAP


def _shade_for_cell(lx, ly, on_left, on_up, on_right, on_down):
    """
    Multi-stop shade: highlight top-left, mid body, deeper bottom-right.
    Edge cells get a slight edge tone for definition.
    """
    # Normalized position in glyph
    nx = lx / max(1, DIGIT_W0 - 1)
    ny = ly / max(1, DIGIT_H0 - 1)
    # Prefer highlight when more "upper-left"
    hi = (1.0 - nx) * 0.55 + (1.0 - ny) * 0.45
    if hi > 0.62:
        base = _lerp_rgb(DIGIT_MID, DIGIT_HI, (hi - 0.62) / 0.38)
    elif hi < 0.38:
        base = _lerp_rgb(DIGIT_LO, DIGIT_MID, hi / 0.38)
    else:
        base = DIGIT_MID
    # Soft outline where a neighbor is empty
    edge = (not on_left) or (not on_up) or (not on_right) or (not on_down)
    if edge:
        base = _lerp_rgb(base, DIGIT_EDGE, 0.28)
    return base


def draw_shaded_digit(canvas, ox, oy, digit, width, height):
    grid = _digit_grid(digit)
    z = DIGIT_ZOOM

    def on(cx, cy):
        if not (0 <= cx < DIGIT_W0 and 0 <= cy < DIGIT_H0):
            return False
        return bool(grid[cy * DIGIT_W0 + cx])

    for ly in range(DIGIT_H0):
        for lx in range(DIGIT_W0):
            if not on(lx, ly):
                continue
            rgb = _shade_for_cell(
                lx, ly,
                on(lx - 1, ly), on(lx, ly - 1),
                on(lx + 1, ly), on(lx, ly + 1),
            )
            for zv in range(z):
                for zh in range(z):
                    # Sub-pixel shade: upper-left micro-highlight inside block
                    if zh == 0 and zv == 0 and z > 1:
                        c = _lerp_rgb(rgb, DIGIT_HI, 0.35)
                    elif zh == z - 1 and zv == z - 1 and z > 1:
                        c = _lerp_rgb(rgb, DIGIT_LO, 0.40)
                    else:
                        c = rgb
                    sx = ox + lx * z + zh
                    sy = oy + ly * z + zv
                    if 0 <= sx < width and 0 <= sy < height:
                        canvas.SetPixel(sx, sy, c[0], c[1], c[2])


def draw_colon(canvas, ox, oy, digit_h, blink_on, width, height):
    if not blink_on:
        return
    # Two square dots vertically centered in digit height
    dot = max(1, DIGIT_ZOOM)
    cx = ox + max(0, (COLON_W - dot) // 2)
    y1 = oy + digit_h // 3 - dot // 2
    y2 = oy + (2 * digit_h) // 3 - dot // 2
    for dy in range(dot):
        for dx in range(dot):
            for y, bright in ((y1 + dy, 1.0), (y2 + dy, 0.85)):
                sx, sy = cx + dx, y
                if 0 <= sx < width and 0 <= sy < height:
                    r = int(COLON_RGB[0] * bright)
                    g = int(COLON_RGB[1] * bright)
                    b = int(COLON_RGB[2] * bright)
                    canvas.SetPixel(sx, sy, r, g, b)


def _clock_origin(width, height):
    """
    Fixed upper-center seat for HH:MM — never moves with the tide.
    Leaves the lower band free for water; high tide can wet the glyph bottoms.
    """
    dw, dh = _digit_pixel_size()
    total_w = _clock_total_width()
    ox = max(0, (width - total_w) // 2)
    # Sit in the upper half, slightly above vertical center of the dry band
    dry_h = max(dh + 2, height - int(height * WATER_BAND_FRAC))
    oy = max(1, (dry_h - dh) // 2)
    # Keep a little air under the glyphs so water can crest around them
    oy = min(oy, max(1, height // 2 - dh - 1))
    return ox, oy, dw, dh


def _now_digits():
    now = time.localtime()
    hour = now.tm_hour
    if not USE_24H:
        hour = hour % 12
        if hour == 0:
            hour = 12
    return (
        hour // 10, hour % 10,
        now.tm_min // 10, now.tm_min % 10,
    )


def _collect_digit_solid(ox, oy, digit, solid):
    """Add solid (on) pixels of one scaled digit into a set of (x, y)."""
    grid = _digit_grid(digit)
    z = DIGIT_ZOOM
    for ly in range(DIGIT_H0):
        for lx in range(DIGIT_W0):
            if not grid[ly * DIGIT_W0 + lx]:
                continue
            for zv in range(z):
                for zh in range(z):
                    solid.add((ox + lx * z + zh, oy + ly * z + zv))


def build_clock_solid_mask(width, height, blink_on=True):
    """
    Pixel set occupied by the fixed clock glyphs (digits + colon when lit).
    Water rendering skips these so the tide washes *around* the time.
    """
    ox, oy, dw, dh = _clock_origin(width, height)
    digits = _now_digits()
    solid = set()
    x = ox
    _collect_digit_solid(x, oy, digits[0], solid)
    x += dw + DIGIT_GAP
    _collect_digit_solid(x, oy, digits[1], solid)
    x += dw + DIGIT_GAP
    if blink_on:
        dot = max(1, DIGIT_ZOOM)
        cx = x + max(0, (COLON_W - dot) // 2)
        y1 = oy + dh // 3 - dot // 2
        y2 = oy + (2 * dh) // 3 - dot // 2
        for dy in range(dot):
            for dx in range(dot):
                solid.add((cx + dx, y1 + dy))
                solid.add((cx + dx, y2 + dy))
    x += COLON_W + DIGIT_GAP
    _collect_digit_solid(x, oy, digits[2], solid)
    x += dw + DIGIT_GAP
    _collect_digit_solid(x, oy, digits[3], solid)
    return solid


def draw_time(canvas, width, height):
    """HH:MM at a fixed upper-center seat (independent of water level)."""
    ox, oy, dw, dh = _clock_origin(width, height)
    digits = _now_digits()
    blink = (int(time.time()) % 2) == 0
    x = ox
    draw_shaded_digit(canvas, x, oy, digits[0], width, height)
    x += dw + DIGIT_GAP
    draw_shaded_digit(canvas, x, oy, digits[1], width, height)
    x += dw + DIGIT_GAP
    draw_colon(canvas, x, oy, dh, blink, width, height)
    x += COLON_W + DIGIT_GAP
    draw_shaded_digit(canvas, x, oy, digits[2], width, height)
    x += dw + DIGIT_GAP
    draw_shaded_digit(canvas, x, oy, digits[3], width, height)


# ---------------- Water simulation ----------------
class WaterSim(object):
    """
    Column surface fluid + free droplets:
      - Mean level rises and drains over LEVEL_PERIOD (high tide can wet clock)
      - Sea state biased calm; rough spells are shorter but can get wild
      - Traveling/sloshing bias pushes water left/right
      - Neighbor viscosity keeps the surface coherent
      - Droplets splash when the surface is agitated (half the old rate)
    """

    def __init__(self, width, height):
        self.w = int(width)
        self.h = int(height)
        self.band = max(4, int(round(self.h * WATER_BAND_FRAC)))
        self.floor_y = self.h - 1
        self.band_top = self.h - self.band
        self.level = [self.band * 0.35 for _ in range(self.w)]
        self.flow = [0.0 for _ in range(self.w)]
        self.droplets = []
        self.t = 0.0
        self.level_phase = random.uniform(0, math.pi * 2)
        self.slosh_phase = random.uniform(0, math.pi * 2)
        self.event_t = 0.0
        self.event_bias = 0.0
        # Sea state: start calm more often than rough
        self.sea_rough = False
        self.sea_t = 0.0
        self.sea_slosh_mul = 0.5
        self.sea_wave_frac = SEA_CALM_WAVE
        self.fishing = False           # minute calm: high flat water
        self._roll_sea_state(force_calm=True)

    def set_fishing(self, active):
        """Enter/leave the once-a-minute high, glassy-water fishing calm."""
        was = self.fishing
        self.fishing = bool(active)
        if self.fishing and not was:
            self.sea_rough = False
            self.sea_slosh_mul = 0.08
            self.sea_wave_frac = 0.02
            self.sea_t = FISHING_DURATION + 2.0
            self.event_bias = 0.18
            self.event_t = FISHING_DURATION + 2.0
            self.droplets = []
        elif not self.fishing and was:
            self._roll_sea_state(force_calm=True)
            self.event_t = 0.5

    def _roll_sea_state(self, force_calm=False):
        """Pick a new calm or rough spell (biased toward calm)."""
        if self.fishing:
            self.sea_rough = False
            self.sea_slosh_mul = 0.08
            self.sea_wave_frac = 0.02
            self.sea_t = 4.0
            return
        if force_calm or random.random() < SEA_CALM_CHANCE:
            self.sea_rough = False
            self.sea_slosh_mul = random.uniform(*SEA_CALM_SLOSH)
            self.sea_wave_frac = SEA_CALM_WAVE * random.uniform(0.7, 1.15)
            self.sea_t = random.uniform(*SEA_CALM_DUR)
        else:
            self.sea_rough = True
            self.sea_slosh_mul = random.uniform(*SEA_ROUGH_SLOSH)
            self.sea_wave_frac = SEA_ROUGH_WAVE * random.uniform(0.85, 1.2)
            self.sea_t = random.uniform(*SEA_ROUGH_DUR)

    def update(self, dt, solid_mask=None):
        self.t += dt
        # Weather / sea state — calm dominates; rough is brief but strong
        # (frozen glassy during fishing calm)
        if not self.fishing:
            self.sea_t -= dt
            if self.sea_t <= 0.0:
                self._roll_sea_state()

        if not self.fishing:
            self.event_t -= dt
            if self.event_t <= 0.0:
                # Tide bias: mild most of the time; high-water crests more often
                # so the surface can climb over the lower clock rows
                r = random.random()
                if r < 0.50:
                    # Quiet mid/low water
                    self.event_bias = random.uniform(-0.18, 0.06)
                elif r < 0.78:
                    # High tide — can cover bottom of the time
                    self.event_bias = random.uniform(0.10, 0.22)
                else:
                    # Drain
                    self.event_bias = random.uniform(-0.28, -0.10)
                self.event_t = random.uniform(3.5, 7.5)

        if self.fishing:
            # Rise gently toward a high, flat waterline — almost no breathe/slosh
            mean_frac = FISHING_RISE_FRAC
            target_mean = self.band * mean_frac
            slosh_amp = 0.0
            wave_amp = 0.0
            track = 0.55          # slow, gentle rise
            flow_push = 0.0
            max_level = float(self.band) + 2.0
        else:
            breathe = 0.5 + 0.5 * math.sin(
                self.t * (2 * math.pi / LEVEL_PERIOD) + self.level_phase
            )
            # Soften the breathe toward mid when calm so level isn't always slamming
            if not self.sea_rough:
                breathe = 0.5 + (breathe - 0.5) * 0.72
            mean_frac = _clamp(
                _lerp(WATER_MIN_FRAC, WATER_MAX_FRAC, breathe) + self.event_bias,
                WATER_MIN_FRAC * 0.5,
                1.05,  # slight overshoot so high tide can crest into the glyphs
            )
            target_mean = self.band * mean_frac
            # Slosh slower when calm, a bit snappier when rough
            slosh_rate = (2 * math.pi / SLOSH_PERIOD) * (1.35 if self.sea_rough else 0.85)
            self.slosh_phase += dt * slosh_rate
            slosh_amp = SLOSH_STRENGTH * self.sea_slosh_mul
            wave_amp = self.sea_wave_frac * self.band
            track = 2.4 if self.sea_rough else 1.15
            flow_push = 0.55 if self.sea_rough else 0.22
            max_level = float(self.band) + (2.5 if mean_frac > 0.9 else 1.0)

        tilt = math.sin(self.slosh_phase) * slosh_amp * self.band
        wave_k = 2 * math.pi / max(8.0, self.w * 0.85)

        desired = [0.0] * self.w
        for x in range(self.w):
            wave = math.sin(x * wave_k + self.slosh_phase * 1.3) * wave_amp
            nx = (x / max(1, self.w - 1)) * 2.0 - 1.0
            des = target_mean + tilt * (-nx) * 0.55 + wave
            desired[x] = _clamp(des, 0.0, max_level)

        # Surface tracks desired more gently when calm
        new_level = [0.0] * self.w
        for x in range(self.w):
            L = self.level[x]
            L += (desired[x] - L) * min(1.0, track * dt)
            if 0 < x < self.w - 1:
                avg = (self.level[x - 1] + self.level[x] + self.level[x + 1]) / 3.0
                # Extra viscosity when calm → flatter surface
                visc = VISCOSITY * (0.75 if self.sea_rough else 1.15)
                if self.fishing:
                    visc = min(0.95, VISCOSITY * 1.6)
                L = _lerp(L, avg, min(0.9, visc))
            flow_dir = 0.0 if self.fishing else math.cos(self.slosh_phase)
            self.flow[x] = self.flow[x] * (0.82 if self.fishing else 0.90) + flow_dir * flow_push
            new_level[x] = _clamp(L, 0.0, max_level)

        advected = list(new_level)
        advect_scale = 0.0 if self.fishing else (9.0 if self.sea_rough else 3.5)
        for x in range(self.w):
            f = self.flow[x] * dt * advect_scale
            if abs(f) < 0.01:
                continue
            dst = int(round(x + f))
            if dst == x or not (0 <= dst < self.w):
                continue
            move = min(0.45 if self.sea_rough else 0.22, abs(f) * 0.08) * new_level[x]
            if new_level[x] > move:
                advected[x] -= move
                advected[dst] = min(max_level, advected[dst] + move)
        self.level = [_clamp(v, 0.0, max_level) for v in advected]

        # Splash: half the particles/chance; mostly when rough; none while fishing
        if self.fishing:
            self.droplets = []
            return

        agitate = abs(math.cos(self.slosh_phase)) * (1.0 if self.sea_rough else 0.35)
        splash_p = SPLASH_CHANCE + 0.04 * agitate * (1.0 if self.sea_rough else 0.25)
        if len(self.droplets) < MAX_DROPLETS and random.random() < splash_p:
            x = random.randint(0, self.w - 1)
            surface_y = self.floor_y - self.level[x]
            if self.level[x] > 1.5:
                self.droplets.append({
                    "x": float(x) + random.uniform(0, 1),
                    "y": float(surface_y) - random.uniform(0.2, 1.2),
                    "vx": self.flow[x] * 0.9 + random.uniform(-0.4, 0.4),
                    "vy": -random.uniform(0.4, 1.6) * (0.5 + agitate),
                })

        alive = []
        for d in self.droplets:
            d["vy"] += WATER_GRAVITY
            d["vx"] *= 0.99
            d["x"] += d["vx"]
            d["y"] += d["vy"]
            if d["x"] < 0:
                d["x"] = 0.0
                d["vx"] = abs(d["vx"]) * 0.5
            elif d["x"] >= self.w:
                d["x"] = self.w - 0.01
                d["vx"] = -abs(d["vx"]) * 0.5
            ix = int(_clamp(d["x"], 0, self.w - 1))
            surface_y = self.floor_y - self.level[ix]
            if d["y"] >= surface_y:
                self.level[ix] = min(max_level, self.level[ix] + 0.15)
                continue
            if d["y"] > self.h + 2:
                continue
            alive.append(d)
        self.droplets = alive

    def surface_y_at(self, x):
        """World y of water surface at horizontal x (float)."""
        ix = int(_clamp(x, 0, self.w - 1))
        return float(self.floor_y) - float(self.level[ix])

    def mean_surface_y(self):
        """Average waterline y (for sun set / rise height)."""
        if not self.level:
            return float(self.h) * 0.7
        return sum(self.floor_y - L for L in self.level) / float(len(self.level))

    def mean_flow(self):
        """
        Horizontal current bias: >0 water pushing right, <0 left.
        Matches the slosh phase cos term used in the surface model.
        """
        if self.fishing:
            return 0.0
        return math.cos(self.slosh_phase)

    def draw(self, canvas, solid_mask=None):
        set_px = canvas.SetPixel
        mask = solid_mask or set()
        for x in range(self.w):
            h_water = self.level[x]
            if h_water <= 0.05:
                continue
            top = int(math.floor(self.floor_y - h_water + 0.5))
            top = _clamp(top, 0, self.floor_y)
            depth = self.floor_y - top + 1
            for y in range(top, self.floor_y + 1):
                if (x, y) in mask:
                    continue
                t = (y - top) / float(max(1, depth - 1)) if depth > 1 else 1.0
                if y == top:
                    rgb = WATER_FOAM if h_water > 0.8 else WATER_TOP
                elif t < 0.35:
                    rgb = _lerp_rgb(WATER_TOP, WATER_MID, t / 0.35)
                else:
                    rgb = _lerp_rgb(WATER_MID, WATER_DEEP, (t - 0.35) / 0.65)
                set_px(x, y, rgb[0], rgb[1], rgb[2])
            if h_water > 1.2 and (x + int(self.t * 7)) % 11 == 0:
                if 0 <= top < self.h and (x, top) not in mask:
                    set_px(x, top, WATER_FOAM[0], WATER_FOAM[1], WATER_FOAM[2])

        for d in self.droplets:
            sx = int(d["x"])
            sy = int(d["y"])
            if 0 <= sx < self.w and 0 <= sy < self.h and (sx, sy) not in mask:
                set_px(sx, sy, WATER_DROP[0], WATER_DROP[1], WATER_DROP[2])
                ty = sy + 1
                if 0 <= ty < self.h and (sx, ty) not in mask:
                    set_px(
                        sx, ty,
                        WATER_MID[0] // 2, WATER_MID[1] // 2, WATER_MID[2] // 2,
                    )


# ---------------- Ottawa sun (civil sunrise → sunset) ----------------
def _nth_weekday_of_month(year, month, weekday, n):
    """weekday: Mon=0 .. Sun=6; n: 1=first, 2=second, …"""
    d = date(year, month, 1)
    # advance to first desired weekday
    add = (weekday - d.weekday()) % 7
    d = d + timedelta(days=add + 7 * (n - 1))
    return d


def _eastern_offset_for_date(d: date):
    """
    America/Toronto style offset: EDT (UTC−4) from 2nd Sunday of March
    through the day before the 1st Sunday of November; else EST (UTC−5).
    Reliable without system tzdata.
    """
    # 2nd Sunday of March
    dst_start = _nth_weekday_of_month(d.year, 3, 6, 2)
    # 1st Sunday of November
    dst_end = _nth_weekday_of_month(d.year, 11, 6, 1)
    if dst_start <= d < dst_end:
        return timedelta(hours=-4)
    return timedelta(hours=-5)


def _ottawa_tz_for_date(d: date):
    return timezone(_eastern_offset_for_date(d))


def _ottawa_now():
    # Use UTC wall clock then attach Eastern offset for "now"
    utc = datetime.now(timezone.utc)
    off = _eastern_offset_for_date(utc.date())
    # Recompute with local date after offset (DST boundary edge is fine for clock art)
    local = utc.astimezone(timezone(off))
    return local.replace(tzinfo=_ottawa_tz_for_date(local.date()))


def _sun_times_ottawa(on_date: date):
    """
    Civil sunrise / sunset for Ottawa on the given local date.

    Uses the classic USNO/Almanac algorithm (good to a couple of minutes).
    Returns (sunrise, sunset) as America/Toronto-aware datetimes.
    """
    lat = OTTAWA_LAT
    lon = OTTAWA_LON  # east-positive
    zenith = 90.833   # civil sunrise/set
    d2r = math.pi / 180.0

    # Day of year
    n1 = math.floor(275 * on_date.month / 9)
    n2 = math.floor((on_date.month + 9) / 12)
    n3 = 1 + math.floor((on_date.year - 4 * math.floor(on_date.year / 4) + 2) / 3)
    n = int(n1 - (n2 * n3) + on_date.day - 30)

    lng_hour = lon / 15.0

    def _event_utc_hours(rising: bool):
        t = n + ((6.0 - lng_hour) / 24.0) if rising else n + ((18.0 - lng_hour) / 24.0)
        m_anom = (0.9856 * t) - 3.289
        l_sun = (
            m_anom
            + (1.916 * math.sin(m_anom * d2r))
            + (0.020 * math.sin(2 * m_anom * d2r))
            + 282.634
        ) % 360.0
        ra = math.degrees(math.atan(0.91764 * math.tan(l_sun * d2r))) % 360.0
        l_quad = math.floor(l_sun / 90.0) * 90.0
        ra_quad = math.floor(ra / 90.0) * 90.0
        ra = (ra + (l_quad - ra_quad)) / 15.0
        sin_dec = 0.39782 * math.sin(l_sun * d2r)
        cos_dec = math.cos(math.asin(sin_dec))
        cos_h = (
            math.cos(zenith * d2r) - (sin_dec * math.sin(lat * d2r))
        ) / (cos_dec * math.cos(lat * d2r))
        if cos_h > 1.0 or cos_h < -1.0:
            return None
        if rising:
            h = 360.0 - math.degrees(math.acos(cos_h))
        else:
            h = math.degrees(math.acos(cos_h))
        h = h / 15.0
        t_local = h + ra - (0.06571 * t) - 6.622
        ut = (t_local - lng_hour) % 24.0
        return ut

    rise_ut = _event_utc_hours(True)
    set_ut = _event_utc_hours(False)
    if rise_ut is None or set_ut is None:
        return None, None

    tz = _ottawa_tz_for_date(on_date)
    # UTC midnight of that calendar date + UT hours → Eastern local
    utc_midnight = datetime(on_date.year, on_date.month, on_date.day, tzinfo=timezone.utc)

    def _ut_to_local(ut_hours):
        local = (utc_midnight + timedelta(hours=ut_hours)).astimezone(tz)
        if local.date() < on_date:
            local += timedelta(days=1)
        elif local.date() > on_date:
            local -= timedelta(days=1)
        return local

    return _ut_to_local(rise_ut), _ut_to_local(set_ut)


class Sun(object):
    """
    Yellow sun with soft glow.

    Path (day fraction 0=sunrise → 1=sunset, Ottawa times):
      1) Rise at waterline on the RIGHT edge, climb the right side
      2) Cross the TOP right → left  (midday / day_t≈0.5 = top-center)
      3) Descend the LEFT side down to the waterline (sunset)
    Hidden at night. Drawn under lit clock segments so noon can shine
    through the unlit gaps of the digits.
    """

    def __init__(self, width, height):
        self.w = int(width)
        self.h = int(height)
        self.x = 0.0
        self.y = 0.0
        self.visible = False
        self.day_t = 0.0
        self._date = None
        self._sunrise = None
        self._sunset = None
        self._refresh_times(_ottawa_now())

    def _refresh_times(self, now):
        d = now.date()
        if self._date == d and self._sunrise and self._sunset:
            return
        self._date = d
        rise, sett = _sun_times_ottawa(d)
        self._sunrise, self._sunset = rise, sett
        if rise and sett:
            print(
                f"[WaterClock] Ottawa sun  {d.isoformat()}  "
                f"rise {rise.strftime('%H:%M')}  set {sett.strftime('%H:%M')}"
            )

    def update(self, water=None):
        """
        Position depends only on real Ottawa civil time — not on water motion.
        Horizon for rise/set is a fixed panel y (stable sky path).
        """
        now = _ottawa_now()
        self._refresh_times(now)
        if not self._sunrise or not self._sunset:
            self.visible = False
            return

        # Day fraction between civil rise and set (wall-clock only)
        t0 = self._sunrise.timestamp()
        t1 = self._sunset.timestamp()
        tn = now.timestamp()
        if tn < t0 or tn > t1 or t1 <= t0:
            self.visible = False
            return
        self.day_t = (tn - t0) / (t1 - t0)
        self.visible = True
        self.x, self.y = _sky_path_xy(self.day_t, self.w, self.h, SUN_EDGE_PAD)

    def draw(self, canvas, solid_mask=None):
        if not self.visible:
            return
        set_px = canvas.SetPixel
        mask = solid_mask or set()
        cx = int(round(self.x))
        cy = int(round(self.y))
        # Warmth shifts slightly through the day (cooler noon, warmer rise/set)
        edge = abs(self.day_t - 0.5) * 2.0  # 0 noon → 1 rise/set
        core = (
            255,
            int(230 - 40 * edge),
            int(50 + 30 * (1.0 - edge)),
        )
        glow = (
            255,
            int(170 - 30 * edge),
            int(30 + 10 * edge),
        )
        halo = (
            int(180 + 40 * edge),
            int(90 - 20 * edge),
            15,
        )
        # Halo (r≈2), glow (r≈1), then hard core
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                d2 = dx * dx + dy * dy
                if d2 == 0 or d2 > 4:
                    continue
                sx, sy = cx + dx, cy + dy
                if mask and (sx, sy) in mask:
                    continue
                if not (0 <= sx < self.w and 0 <= sy < self.h):
                    continue
                if d2 >= 3:
                    # outer halo — dim
                    set_px(sx, sy, halo[0] // 2, halo[1] // 2, halo[2] // 2)
                else:
                    set_px(sx, sy, glow[0], glow[1], glow[2])
        # Core pixel on top
        if 0 <= cx < self.w and 0 <= cy < self.h:
            if not (mask and (cx, cy) in mask):
                set_px(cx, cy, core[0], core[1], core[2])
        # Extra warm touch next to core along path (subtle 4-neighbor glow)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            sx, sy = cx + dx, cy + dy
            if mask and (sx, sy) in mask:
                continue
            if 0 <= sx < self.w and 0 <= sy < self.h:
                # Don't stomp brighter core; glow already set — reinforce
                set_px(sx, sy, glow[0], glow[1], glow[2])

    def _body_colors(self):
        edge = abs(self.day_t - 0.5) * 2.0
        core = (255, int(230 - 40 * edge), int(50 + 30 * (1.0 - edge)))
        glow = (255, int(170 - 30 * edge), int(30 + 10 * edge))
        return core, glow

    def draw_reflection(self, canvas, water, solid_mask=None):
        """Sunset glitter path — same warm sun color, broken & distorted on water."""
        if not self.visible or water is None:
            return
        core, glow = self._body_colors()
        _draw_water_reflection(
            canvas, water, self.x, self.y, core, glow,
            solid_mask=solid_mask, panel_w=self.w, panel_h=self.h,
        )


# ---------------- Moon (Ottawa rise → set, same sky path) ----------------
def _julian_date_utc(dt_utc: datetime) -> float:
    """Julian Date for a timezone-aware UTC datetime."""
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
    else:
        dt_utc = dt_utc.astimezone(timezone.utc)
    y = dt_utc.year
    m = dt_utc.month
    d = dt_utc.day + (
        dt_utc.hour
        + dt_utc.minute / 60.0
        + dt_utc.second / 3600.0
        + dt_utc.microsecond / 3.6e9
    ) / 24.0
    if m <= 2:
        y -= 1
        m += 12
    a = y // 100
    b = 2 - a + a // 4
    return int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + b - 1524.5


def _moon_ra_dec(jd: float):
    """
    Approximate geocentric RA (hours) and Dec (degrees) of the Moon.
    Low-order series — typically within a few minutes on rise/set times.
    """
    d = jd - 2451545.0
    d2r = math.pi / 180.0
    # Mean orbital elements (degrees)
    L = (218.316 + 13.176396 * d) % 360.0          # mean longitude
    M = (134.963 + 13.064993 * d) % 360.0          # mean anomaly
    F = (93.272 + 13.229350 * d) % 360.0           # arg of latitude
    # Ecliptic longitude / latitude (degrees) — leading periodic terms
    lon = (L + 6.289 * math.sin(M * d2r)) % 360.0
    lat = 5.128 * math.sin(F * d2r)
    # Mean obliquity of the ecliptic
    eps = 23.439 - 0.00000036 * d
    lon_r = lon * d2r
    lat_r = lat * d2r
    eps_r = eps * d2r
    ra = math.atan2(
        math.sin(lon_r) * math.cos(eps_r) - math.tan(lat_r) * math.sin(eps_r),
        math.cos(lon_r),
    )
    dec = math.asin(
        math.sin(lat_r) * math.cos(eps_r)
        + math.cos(lat_r) * math.sin(eps_r) * math.sin(lon_r)
    )
    ra_h = (math.degrees(ra) % 360.0) / 15.0
    dec_d = math.degrees(dec)
    return ra_h, dec_d


def _gmst_hours(jd: float) -> float:
    """Greenwich mean sidereal time in hours (0–24)."""
    t = (jd - 2451545.0) / 36525.0
    gmst = (
        280.46061837
        + 360.98564736629 * (jd - 2451545.0)
        + 0.000387933 * t * t
        - (t * t * t) / 38710000.0
    )
    return (gmst % 360.0) / 15.0


def _moon_altitude_deg(lat: float, lon: float, dt_utc: datetime) -> float:
    """Apparent altitude of the Moon center (degrees) at lat/lon for UTC time."""
    jd = _julian_date_utc(dt_utc)
    ra_h, dec_d = _moon_ra_dec(jd)
    lst_h = (_gmst_hours(jd) + lon / 15.0) % 24.0
    ha_deg = (lst_h - ra_h) * 15.0
    d2r = math.pi / 180.0
    alt = math.asin(
        math.sin(lat * d2r) * math.sin(dec_d * d2r)
        + math.cos(lat * d2r) * math.cos(dec_d * d2r) * math.cos(ha_deg * d2r)
    )
    return math.degrees(alt)


def _moon_illumination(jd: float) -> float:
    """
    Illuminated fraction of the Moon's disc (0=new … 1=full), approximate.
    """
    d = jd - 2451545.0
    # Synodic phase from known new-moon epoch (2000-01-06 ≈ JD 2451550.1)
    phase = ((jd - 2451550.1) / 29.530588853) % 1.0
    # Geometric illumination ~ (1 - cos phase_angle) / 2
    return 0.5 * (1.0 - math.cos(2.0 * math.pi * phase))


def _find_moon_crossing(t0: datetime, t1: datetime, rising: bool, step_s: float = 300.0):
    """
    Find UTC time when moon altitude crosses MOON_HORIZON_ALT between t0 and t1.
    rising=True → upward crossing (moonrise); False → downward (moonset).
    Returns aware UTC datetime or None.
    """
    lat, lon = OTTAWA_LAT, OTTAWA_LON
    thr = MOON_HORIZON_ALT
    prev_t = t0
    prev_a = _moon_altitude_deg(lat, lon, t0)
    t = t0 + timedelta(seconds=step_s)
    while t <= t1 + timedelta(seconds=1):
        a = _moon_altitude_deg(lat, lon, t)
        crossed = False
        if rising and prev_a < thr <= a:
            crossed = True
        elif (not rising) and prev_a > thr >= a:
            crossed = True
        if crossed:
            # Linear interpolate in altitude
            if abs(a - prev_a) < 1e-9:
                return prev_t
            u = (thr - prev_a) / (a - prev_a)
            u = max(0.0, min(1.0, u))
            return prev_t + timedelta(seconds=(t - prev_t).total_seconds() * u)
        prev_t, prev_a = t, a
        t = t + timedelta(seconds=step_s)
    return None


def _moon_pass_ottawa(now_local: datetime):
    """
    Active moonrise → moonset window containing (or nearest after) now for Ottawa.

    Returns (rise_local, set_local, illumination) or (None, None, illum).
    Handles overnight moons (rise evening, set next morning).
    """
    # Work in UTC for astronomy; convert results to Ottawa local
    now_utc = now_local.astimezone(timezone.utc)
    # Search window: 36h before → 36h after (covers full pass + neighbors)
    win0 = now_utc - timedelta(hours=36)
    win1 = now_utc + timedelta(hours=36)

    # Collect all rise and set events in the window (coarse then refine)
    rises = []
    sets = []
    # Coarse scan every 20 min to seed intervals, then refine with 5 min
    step = 1200.0
    lat, lon = OTTAWA_LAT, OTTAWA_LON
    thr = MOON_HORIZON_ALT
    t = win0
    prev_a = _moon_altitude_deg(lat, lon, t)
    prev_t = t
    t = t + timedelta(seconds=step)
    while t <= win1:
        a = _moon_altitude_deg(lat, lon, t)
        if prev_a < thr <= a:
            exact = _find_moon_crossing(
                prev_t - timedelta(seconds=step),
                t + timedelta(seconds=60),
                rising=True,
                step_s=120.0,
            )
            if exact is None:
                exact = prev_t
            rises.append(exact)
        elif prev_a > thr >= a:
            exact = _find_moon_crossing(
                prev_t - timedelta(seconds=step),
                t + timedelta(seconds=60),
                rising=False,
                step_s=120.0,
            )
            if exact is None:
                exact = prev_t
            sets.append(exact)
        prev_a, prev_t = a, t
        t = t + timedelta(seconds=step)

    rises.sort()
    sets.sort()

    # Pair each rise with the next set after it
    pairs = []
    si = 0
    for r in rises:
        while si < len(sets) and sets[si] <= r:
            si += 1
        if si < len(sets):
            pairs.append((r, sets[si]))
            si += 1

    jd_now = _julian_date_utc(now_utc)
    illum = _moon_illumination(jd_now)

    # Prefer the pass that currently contains now; else next upcoming pass
    active = None
    upcoming = None
    for r, s in pairs:
        if r <= now_utc <= s:
            active = (r, s)
            break
        if r > now_utc and upcoming is None:
            upcoming = (r, s)

    chosen = active or upcoming
    if not chosen:
        return None, None, illum

    rise_utc, set_utc = chosen
    # Convert to Ottawa local using the local calendar date of each event
    def _to_ottawa(utc_dt):
        # Attach the Eastern offset for the UTC calendar date (DST-safe enough)
        local = utc_dt.astimezone(timezone.utc)
        # Use Eastern offset for the local civil date after conversion trial
        # First get a rough local, then re-stamp with correct offset for that date
        off_probe = _eastern_offset_for_date(local.date())
        rough = utc_dt.astimezone(timezone(off_probe))
        return rough.astimezone(_ottawa_tz_for_date(rough.date()))

    return _to_ottawa(rise_utc), _to_ottawa(set_utc), illum


def _sky_path_xy(day_t: float, width: int, height: int, edge_pad: int = 1):
    """
    Shared sun/moon path on the panel.
    day_t 0 = rise (right waterline) → 1 = set (left waterline).
    Midday (day_t = 0.5) is the middle of the top edge (top-center).
    """
    top_y = float(edge_pad)
    bot_y = float(height) * (1.0 - WATER_BAND_FRAC * 0.55)
    bot_y = max(top_y + 3.0, min(bot_y, float(height) - 3.0))
    right_x = float(width - 1 - edge_pad)
    left_x = float(edge_pad)
    t = max(0.0, min(1.0, float(day_t)))
    if t < 1.0 / 3.0:
        u = t * 3.0
        return right_x, bot_y + (top_y - bot_y) * u
    if t < 2.0 / 3.0:
        u = (t - 1.0 / 3.0) * 3.0
        return right_x + (left_x - right_x) * u, top_y
    u = (t - 2.0 / 3.0) * 3.0
    return left_x, top_y + (bot_y - top_y) * u


def _draw_water_reflection(
    canvas, water, body_x, body_y, core_rgb, glow_rgb=None,
    solid_mask=None, panel_w=None, panel_h=None,
):
    """
    Real-sunset style reflection: the body's own color as a broken, distorted
    vertical glitter path on the water (wobbles side-to-side, gaps, fades deep).
    """
    if water is None:
        return
    w = int(panel_w if panel_w is not None else water.w)
    h = int(panel_h if panel_h is not None else water.h)
    mask = solid_mask or set()
    set_px = canvas.SetPixel
    if glow_rgb is None:
        glow_rgb = core_rgb

    surf = water.surface_y_at(body_x)
    gap = surf - float(body_y)
    if gap > REFLECT_NEAR:
        return
    if gap < -2.5:
        return

    if gap >= 0.0:
        proximity = 1.0 - (gap / REFLECT_NEAR)
    else:
        proximity = 1.0
    proximity = _clamp(proximity, 0.0, 1.0)
    # Bloom near the horizon (sunset / moonset)
    proximity = proximity * proximity * (3.0 - 2.0 * proximity)
    strength = REFLECT_MAX * proximity
    if strength < 0.06:
        return

    # Vertical path length grows as the body sits lower
    depth_rows = int(round(3 + REFLECT_DEPTH * proximity))
    depth_rows = max(3, min(REFLECT_DEPTH + 2, depth_rows))
    top = int(math.floor(surf + 0.35))
    t = float(getattr(water, "t", 0.0))

    for row in range(depth_rows):
        sy = top + row
        if sy < 0 or sy >= h or sy > water.floor_y:
            continue
        # Deeper = more horizontal distortion (chop on the water)
        depth_u = row / float(max(1, depth_rows - 1))
        # Broken path: skip some rows like wave facets
        break_wave = math.sin(t * 5.1 + row * 1.7 + body_x * 0.4)
        if break_wave < -0.55 and row > 0:
            continue
        # Sideways shimmer — increases with depth (classic glitter road)
        jitter = (
            math.sin(t * 3.3 + row * 2.1 + body_x * 0.55) * REFLECT_JITTER * (0.35 + 0.65 * depth_u)
            + math.sin(t * 7.0 + row * 0.9) * 0.45 * depth_u
        )
        # Path width: a little wider mid-path, thin near the end
        if row == 0:
            half_w = 1
        elif depth_u < 0.55:
            half_w = 1 if break_wave > 0.2 else 0
        else:
            half_w = 0  # single-pixel glitter deeper down

        # Brightness: strong at surface, dimmer/broken deeper
        row_str = strength * (1.0 - 0.72 * depth_u)
        # Alternate core vs softer glow along the path
        use_core = (row % 2 == 0) or row == 0
        src = core_rgb if use_core else glow_rgb

        for dx in range(-half_w, half_w + 1):
            sx = int(round(body_x + jitter + dx))
            if not (0 <= sx < w):
                continue
            if mask and (sx, sy) in mask:
                continue
            local_surf = water.surface_y_at(sx)
            if sy < int(math.floor(local_surf)):
                continue
            if water.level[sx] < 0.35:
                continue
            # Edge of path a bit dimmer
            edge = 1.0 if dx == 0 else 0.62
            mix = row_str * edge
            if mix < 0.05:
                continue
            # Mix sun/moon color into the water at that depth
            if row <= 1:
                water_rgb = WATER_TOP
            elif row <= 3:
                water_rgb = WATER_MID
            else:
                water_rgb = WATER_DEEP
            r = int(water_rgb[0] * (1.0 - mix) + src[0] * mix)
            g = int(water_rgb[1] * (1.0 - mix) + src[1] * mix)
            b = int(water_rgb[2] * (1.0 - mix) + src[2] * mix)
            set_px(sx, sy, _clamp(r, 0, 255), _clamp(g, 0, 255), _clamp(b, 0, 255))

        # Occasional twin sparkle offset (distorted double image)
        if row > 1 and break_wave > 0.65:
            sx2 = int(round(body_x - jitter * 0.7))
            if 0 <= sx2 < w and not (mask and (sx2, sy) in mask):
                if water.level[sx2] >= 0.35 and sy >= int(math.floor(water.surface_y_at(sx2))):
                    mix2 = row_str * 0.4
                    water_rgb = WATER_MID if row <= 3 else WATER_DEEP
                    r = int(water_rgb[0] * (1.0 - mix2) + glow_rgb[0] * mix2)
                    g = int(water_rgb[1] * (1.0 - mix2) + glow_rgb[1] * mix2)
                    b = int(water_rgb[2] * (1.0 - mix2) + glow_rgb[2] * mix2)
                    set_px(sx2, sy, _clamp(r, 0, 255), _clamp(g, 0, 255), _clamp(b, 0, 255))


class Moon(object):
    """
    Pale moon with soft cool glow.

    Same fixed sky path as the sun (right rise → top → left set), driven by
    Ottawa moonrise → moonset wall-clock times (handles overnight moons).
    Brightness scales with illuminated fraction; never fully black while up.
    """

    def __init__(self, width, height):
        self.w = int(width)
        self.h = int(height)
        self.x = 0.0
        self.y = 0.0
        self.visible = False
        self.day_t = 0.0
        self.illum = 0.5
        self._rise = None
        self._set = None
        self._cache_key = None  # (local date hour bucket) for pass refresh
        self._refresh_pass(_ottawa_now())

    def _refresh_pass(self, now):
        # Recompute moon pass about once per 15 local minutes (cheap enough)
        key = (now.date(), now.hour, now.minute // 15)
        if self._cache_key == key and self._rise and self._set:
            return
        self._cache_key = key
        rise, sett, illum = _moon_pass_ottawa(now)
        changed = (rise != self._rise) or (sett != self._set)
        self._rise, self._set, self.illum = rise, sett, illum
        if changed and rise and sett:
            print(
                f"[WaterClock] Ottawa moon  rise {rise.strftime('%Y-%m-%d %H:%M')}  "
                f"set {sett.strftime('%Y-%m-%d %H:%M')}  illum={illum:.0%}"
            )

    def update(self, water=None):
        """Position from real Ottawa moonrise/set only — not water motion."""
        now = _ottawa_now()
        self._refresh_pass(now)
        # Keep illumination fresh each frame (cheap)
        self.illum = _moon_illumination(_julian_date_utc(now.astimezone(timezone.utc)))

        if not self._rise or not self._set:
            self.visible = False
            return

        t0 = self._rise.timestamp()
        t1 = self._set.timestamp()
        tn = now.timestamp()
        if tn < t0 or tn > t1 or t1 <= t0:
            self.visible = False
            return
        self.day_t = (tn - t0) / (t1 - t0)
        self.visible = True
        self.x, self.y = _sky_path_xy(self.day_t, self.w, self.h, MOON_EDGE_PAD)

    def draw(self, canvas, solid_mask=None):
        if not self.visible:
            return
        set_px = canvas.SetPixel
        mask = solid_mask or set()
        cx = int(round(self.x))
        cy = int(round(self.y))
        # Dim with phase; keep a visible floor so a thin crescent still reads
        b = 0.22 + 0.78 * max(0.0, min(1.0, self.illum))
        core = (
            int(MOON_CORE[0] * b),
            int(MOON_CORE[1] * b),
            int(MOON_CORE[2] * b),
        )
        glow = (
            int(MOON_GLOW[0] * b),
            int(MOON_GLOW[1] * b),
            int(MOON_GLOW[2] * b),
        )
        halo = (
            int(MOON_HALO[0] * b * 0.7),
            int(MOON_HALO[1] * b * 0.7),
            int(MOON_HALO[2] * b * 0.7),
        )
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                d2 = dx * dx + dy * dy
                if d2 == 0 or d2 > 4:
                    continue
                sx, sy = cx + dx, cy + dy
                if mask and (sx, sy) in mask:
                    continue
                if not (0 <= sx < self.w and 0 <= sy < self.h):
                    continue
                if d2 >= 3:
                    set_px(sx, sy, halo[0], halo[1], halo[2])
                else:
                    set_px(sx, sy, glow[0], glow[1], glow[2])
        if 0 <= cx < self.w and 0 <= cy < self.h:
            if not (mask and (cx, cy) in mask):
                set_px(cx, cy, core[0], core[1], core[2])
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            sx, sy = cx + dx, cy + dy
            if mask and (sx, sy) in mask:
                continue
            if 0 <= sx < self.w and 0 <= sy < self.h:
                set_px(sx, sy, glow[0], glow[1], glow[2])

    def _body_colors(self):
        b = 0.22 + 0.78 * max(0.0, min(1.0, self.illum))
        core = (
            int(MOON_CORE[0] * b),
            int(MOON_CORE[1] * b),
            int(MOON_CORE[2] * b),
        )
        glow = (
            int(MOON_GLOW[0] * b),
            int(MOON_GLOW[1] * b),
            int(MOON_GLOW[2] * b),
        )
        return core, glow

    def draw_reflection(self, canvas, water, solid_mask=None):
        """Moonpath on the water — same silver as the disc, broken & distorted."""
        if not self.visible or water is None:
            return
        core, glow = self._body_colors()
        _draw_water_reflection(
            canvas, water, self.x, self.y, core, glow,
            solid_mask=solid_mask, panel_w=self.w, panel_h=self.h,
        )


# ---------------- Wind + current + sailboat ----------------
# Tiny pixel sprites, origin at hull center on the waterline.
# Facing right (+x). Left is dx mirrored. Bow tip is at dx=+2.
_SAILBOAT_HULL = (
    (-2, 0, BOAT_HULL), (-1, 0, BOAT_HULL), (0, 0, BOAT_HULL),
    (1, 0, BOAT_HULL), (2, 0, BOAT_HULL),
    (-1, 1, BOAT_HULL_DARK), (0, 1, BOAT_HULL_DARK), (1, 1, BOAT_HULL_DARK),
    # mast (stays up when sail is lowered)
    (0, -1, BOAT_MAST), (0, -2, BOAT_MAST), (0, -3, BOAT_MAST),
)
# Sail pixels relative to mast; drawn by height fraction (sail_raise 0..1)
_SAILBOAT_SAIL = (
    (1, -1, BOAT_SAIL), (1, -2, BOAT_SAIL),
    (2, -1, BOAT_SAIL),
)
# Back-compat full sprite list
_SAILBOAT_RIGHT = _SAILBOAT_HULL + _SAILBOAT_SAIL


class WindField(object):
    """
    Horizontal wind independent of the water current.
    Value in roughly [-1, 1]; gusts temporarily push harder.
    During fishing calm the wind dies to zero.
    """

    def __init__(self):
        self.t = 0.0
        self.phase = random.uniform(0, math.pi * 2)
        self.wind = 0.0
        self.gust = 0.0
        self.gust_t = 0.0
        self.stopped = False

    def set_fishing(self, active):
        self.stopped = bool(active)
        if self.stopped:
            self.gust = 0.0
            self.gust_t = 0.0

    def update(self, dt):
        self.t += dt
        if self.stopped:
            # Wind falls off and stays dead calm
            self.wind *= max(0.0, 1.0 - 3.5 * dt)
            if abs(self.wind) < 0.02:
                self.wind = 0.0
            self.gust = 0.0
            return self.wind

        base = math.sin(self.t * (2.0 * math.pi / WIND_PERIOD) + self.phase)
        # Soft secondary wobble
        base += 0.25 * math.sin(self.t * 0.7 + self.phase * 0.3)
        base = _clamp(base, -1.0, 1.0)

        self.gust_t -= dt
        if self.gust_t <= 0.0 and random.random() < WIND_GUST_CHANCE:
            # Gust in the current wind direction (or random if slack)
            sign = 1.0 if abs(base) < 0.15 else (1.0 if base > 0 else -1.0)
            if random.random() < 0.25:
                sign = -sign
            self.gust = sign * random.uniform(0.45, 1.0)
            self.gust_t = random.uniform(WIND_GUST_MIN, WIND_GUST_MAX)
        if self.gust_t <= 0.0:
            self.gust *= 0.90
            if abs(self.gust) < 0.05:
                self.gust = 0.0

        self.wind = _clamp(base + self.gust, -1.35, 1.35)
        return self.wind


class Sailboat(object):
    """
    Little sailboat trying to cross to the far shore.

    Forces:
      • Sail thrust toward the goal (stronger with a fair wind)
      • Water current drift (from the tide/slosh)
      • Wind drift on the hull

    If wind + current stay calm for a random while, drops anchor and holds
    station until the seas pick up again (after a minimum rest).

    During the once-a-minute fishing calm: stops, holds station, and pays out
    a fishing line with a small hook.
    """

    def __init__(self, width, height):
        self.w = int(width)
        self.h = int(height)
        # Start near one shore, goal is the other
        if random.random() < 0.5:
            self.x = float(BOAT_EDGE_PAD + 1)
            self.goal = 1   # make for the right
        else:
            self.x = float(self.w - 1 - BOAT_EDGE_PAD - 1)
            self.goal = -1  # make for the left
        self.dir = self.goal            # bow faces goal
        self.y = float(self.h - 4)
        self.bob_phase = random.uniform(0, math.pi * 2)
        self.crossings = 0
        self.stuck_t = 0.0              # if battered backward too long, dig in
        # Anchoring
        self.anchored = False
        self.calm_t = 0.0
        self.rough_t = 0.0
        self.anchor_t = 0.0
        self.calm_need = random.uniform(CALM_NEED_MIN, CALM_NEED_MAX)
        self.anchor_hold = random.uniform(ANCHOR_MIN, ANCHOR_MAX)
        # Fishing / trip scripting
        self.fishing = False
        self.line_len = 0.0             # paid-out length in px
        self.line_target = FISHING_LINE_MIN  # current target drop depth
        self.depth_hold_t = 0.0         # time left at this depth before re-drop
        self.reeling = False            # True while hauling a hooked fish
        self.catches = 0
        self.catch_flash_t = 0.0        # show last catch on deck
        self.catch_rgb = FISH_COLORS[0]
        self.catch_size = 1
        self._pre_fish_anchored = False
        self.scripted = False           # trip director steers the boat
        self.script_target_x = None
        self.script_speed = BOAT_HOME_SPEED
        self.sail_raise = 1.0           # 1 = full sail, 0 = lowered (furled)

    def set_fishing(self, active, reset_catches=False):
        """Stop for fishing and pay out a hook, or reel in."""
        active = bool(active)
        if active and not self.fishing:
            self._pre_fish_anchored = self.anchored
            self.fishing = True
            self.scripted = False
            self.anchored = True
            self.line_len = 0.0
            self.reeling = False
            self.catch_flash_t = 0.0
            self.catch_size = 1
            self.stuck_t = 0.0
            if reset_catches:
                self.catches = 0
            self._pick_line_depth(reason="cast")
            print(f"[WaterClock] Sailboat fishing  x={self.x:.1f}")
        elif not active and self.fishing:
            self.fishing = False
            self.line_len = 0.0
            self.reeling = False
            if not self.scripted:
                if not self._pre_fish_anchored:
                    self.anchored = False
                    self.calm_t = 0.0
                    self.calm_need = random.uniform(CALM_NEED_MIN, CALM_NEED_MAX)
                self.rough_t = 0.0
            print(
                f"[WaterClock] Sailboat reeled in  "
                f"(caught {self.catches})"
            )

    def start_scripted_sail(self, target_x, direction, speed=None, raise_sail=True):
        """Trip director: sail to an x under calm weather (no free AI)."""
        self.scripted = True
        self.script_target_x = float(target_x)
        self.script_speed = float(speed if speed is not None else BOAT_HOME_SPEED)
        self.fishing = False
        self.line_len = 0.0
        self.reeling = False
        self.anchored = False
        self.dir = 1 if direction >= 0 else -1
        self.goal = self.dir
        self.stuck_t = 0.0
        if raise_sail:
            self.sail_raise = 1.0

    def clear_scripted(self):
        self.scripted = False
        self.script_target_x = None
        self.anchored = False
        self.calm_t = 0.0
        self.rough_t = 0.0
        self.calm_need = random.uniform(CALM_NEED_MIN, CALM_NEED_MAX)
        self.sail_raise = 1.0

    def lower_sail(self, dt, duration=SAIL_LOWER_TIME):
        """Animate sail down; returns True when fully lowered."""
        if duration <= 0:
            self.sail_raise = 0.0
            return True
        self.sail_raise = max(0.0, self.sail_raise - dt / float(duration))
        return self.sail_raise <= 0.001

    def arrived_scripted(self, tol=1.2):
        if not self.scripted or self.script_target_x is None:
            return True
        return abs(self.x - self.script_target_x) <= tol

    def _pick_line_depth(self, reason=""):
        """
        Choose a new hook depth. Mix of shallow / mid / deep drops so the
        boat can reach both surface minnows and bottom dwellers.
        """
        r = random.random()
        if r < 0.30:
            # Shallow — surface school
            self.line_target = random.uniform(FISHING_LINE_MIN, FISHING_LINE_MIN + 2.5)
            zone = "shallow"
        elif r < 0.65:
            # Mid water
            mid0 = FISHING_LINE_MIN + 2.0
            mid1 = FISHING_LINE_MAX * 0.65
            self.line_target = random.uniform(mid0, max(mid0 + 0.5, mid1))
            zone = "mid"
        else:
            # Deep — big fish country
            deep0 = FISHING_LINE_MAX * 0.65
            self.line_target = random.uniform(deep0, FISHING_LINE_MAX)
            zone = "deep"
        self.depth_hold_t = random.uniform(*FISHING_DEPTH_HOLD)
        msg = f"[WaterClock] Hook drop {zone}  target={self.line_target:.1f}px"
        if reason:
            msg += f"  ({reason})"
        print(msg)

    def _line_x(self):
        return self.x + (1.0 if self.dir >= 0 else -1.0)

    def _hook_open(self):
        """Side the J opens toward (same way as the bow)."""
        return 1 if self.dir >= 0 else -1

    def hook_tip(self):
        """
        World position of the catchy point of the J-hook.
        Returns None if the line isn't out far enough yet.
        """
        if not self.fishing or self.line_len < 2.0:
            return None
        lx = self._line_x()
        # Line drops to y = hull + line_len; J hangs below that
        base_y = self.y + self.line_len
        open_d = self._hook_open()
        # Tip of the J points back up one pixel from the bend
        return (lx + open_d, base_y + 1.0)

    def start_reel(self):
        """Begin hauling the line in (fish is on the hook)."""
        if self.fishing:
            self.reeling = True

    def finish_catch(self, rgb=None, size=1, rare=False):
        """Fish reached the boat — count it and flash on deck."""
        self.catches += 1
        self.reeling = False
        self.catch_flash_t = FISH_CATCH_FLASH * (1.35 if size >= 3 else 1.0)
        self.catch_size = max(1, int(size))
        if rgb is not None:
            self.catch_rgb = rgb
        kind = "RARE RED" if rare else ("big" if size >= 3 else "fish")
        print(f"[WaterClock] Caught {kind}!  total={self.catches}")
        # Shorten line then pick a new depth for the next cast
        self.line_len = max(FISHING_LINE_MIN * 0.5, self.line_len * 0.25)
        self._pick_line_depth(reason="recast")

    def _set_goal(self, goal):
        self.goal = 1 if goal >= 0 else -1
        self.dir = self.goal
        self.stuck_t = 0.0

    def _seas_calm(self, current, wind):
        return abs(current) <= CALM_CURRENT and abs(wind) <= CALM_WIND

    def _drop_anchor(self):
        self.anchored = True
        self.anchor_t = 0.0
        self.anchor_hold = random.uniform(ANCHOR_MIN, ANCHOR_MAX)
        self.calm_t = 0.0
        self.rough_t = 0.0
        print(f"[WaterClock] Sailboat dropped anchor  x={self.x:.1f}")

    def _weigh_anchor(self, reason=""):
        if self.fishing:
            return  # stay put while fishing
        self.anchored = False
        self.calm_t = 0.0
        self.rough_t = 0.0
        self.calm_need = random.uniform(CALM_NEED_MIN, CALM_NEED_MAX)
        msg = f"[WaterClock] Sailboat weighed anchor"
        if reason:
            msg += f"  ({reason})"
        print(msg)

    def update(self, dt, water, wind):
        current = water.mean_flow()     # -1..1-ish from tide
        w = float(wind)
        calm = self._seas_calm(current, w)

        # --- Scripted trip sail (home to pier / depart) ---
        if self.scripted and self.script_target_x is not None:
            self.bob_phase += dt * 2.4
            bob = 0.22 * math.sin(self.bob_phase)
            self.y = water.surface_y_at(self.x) + bob
            if self.catch_flash_t > 0.0:
                self.catch_flash_t = max(0.0, self.catch_flash_t - dt)
            tx = self.script_target_x
            dx = tx - self.x
            if abs(dx) <= 0.6:
                self.x = tx
                self.y = water.surface_y_at(self.x) + bob
                return
            step = self.script_speed * dt
            if abs(dx) <= step:
                self.x = tx
            else:
                self.x += math.copysign(step, dx)
            self.dir = 1 if dx >= 0 else -1
            lo = float(BOAT_EDGE_PAD)
            hi = float(self.w - 1 - BOAT_EDGE_PAD)
            self.x = _clamp(self.x, lo, hi)
            return

        # --- Fishing calm: hold station, lower / reel hook ---
        if self.fishing:
            self.anchored = True
            self.bob_phase += dt * 1.4
            bob = 0.10 * math.sin(self.bob_phase)
            self.y = water.surface_y_at(self.x) + bob
            if self.catch_flash_t > 0.0:
                self.catch_flash_t = max(0.0, self.catch_flash_t - dt)
            # Physical max (leave room for the 2-px J above the floor)
            floor_cap = max(2.5, float(self.h - 1) - self.y - 3.0)
            max_line = min(FISHING_LINE_MAX, floor_cap)
            target = _clamp(self.line_target, FISHING_LINE_MIN, max_line)
            if self.reeling:
                # Haul fish up into the boat
                self.line_len = max(0.6, self.line_len - FISHING_REEL_SPEED * dt)
            else:
                # Ease line toward the current target depth
                if abs(self.line_len - target) > 0.12:
                    step = FISHING_LINE_SPEED * dt
                    if self.line_len < target:
                        self.line_len = min(target, self.line_len + step)
                    else:
                        self.line_len = max(target, self.line_len - step * 0.85)
                else:
                    self.line_len = target
                    # Hold at this depth, then re-drop to a new depth
                    self.depth_hold_t -= dt
                    if self.depth_hold_t <= 0.0:
                        self._pick_line_depth(reason="search")
            return

        # --- Anchor logic ---
        if self.anchored:
            self.anchor_t += dt
            if calm:
                self.rough_t = 0.0
            else:
                self.rough_t += dt
            # Stay put at least anchor_hold; leave if seas roughen after that,
            # or if still calm but we've rested long enough and want to move on
            if self.anchor_t >= self.anchor_hold and self.rough_t >= ROUGH_WEIGH:
                self._weigh_anchor("seas up")
            elif self.anchor_t >= self.anchor_hold * 1.35 and calm:
                # Optional: get bored at anchor in endless calm and sail on
                if random.random() < 0.008:
                    self._weigh_anchor("cast off")
        else:
            if calm:
                self.calm_t += dt
                self.rough_t = 0.0
                if self.calm_t >= self.calm_need:
                    self._drop_anchor()
            else:
                self.calm_t = max(0.0, self.calm_t - dt * 1.5)
                self.rough_t += dt

        # Always face the destination when underway
        if not self.anchored:
            self.dir = self.goal

        # --- Motion ---
        if self.anchored:
            # Hold station; still ride the surface with a softer bob
            self.bob_phase += dt * 2.0
            bob = 0.18 * math.sin(self.bob_phase)
            self.y = water.surface_y_at(self.x) + bob
            return

        # --- Forces (px/sec) while sailing ---
        fair = max(0.0, w * self.goal)
        foul = max(0.0, -w * self.goal)
        sail = BOAT_SPEED * (
            0.55
            + WIND_SAIL_BONUS * 0.25 * fair
            + WIND_SAIL_BEAT * 0.15 * (1.0 - min(1.0, foul))
        )
        thrust = self.goal * sail
        drift = CURRENT_PUSH * current + WIND_DRIFT * w
        vx = thrust + drift

        if self.goal * vx < 0.6:
            self.stuck_t += dt
            if self.stuck_t > 1.2:
                vx = self.goal * max(0.9, abs(vx) * 0.3 + 0.9)
        else:
            self.stuck_t = max(0.0, self.stuck_t - dt * 0.5)

        self.x += vx * dt

        lo = float(BOAT_EDGE_PAD)
        hi = float(self.w - 1 - BOAT_EDGE_PAD)
        self.x = _clamp(self.x, lo, hi)

        # Reached the far side?
        if self.goal > 0 and self.x >= self.w - 1 - BOAT_GOAL_MARGIN:
            self.crossings += 1
            self._set_goal(-1)
            self.calm_t = 0.0
            self.calm_need = random.uniform(CALM_NEED_MIN, CALM_NEED_MAX)
            print(f"[WaterClock] Sailboat reached RIGHT shore  (crossings={self.crossings})")
        elif self.goal < 0 and self.x <= BOAT_GOAL_MARGIN:
            self.crossings += 1
            self._set_goal(1)
            self.calm_t = 0.0
            self.calm_need = random.uniform(CALM_NEED_MIN, CALM_NEED_MAX)
            print(f"[WaterClock] Sailboat reached LEFT shore  (crossings={self.crossings})")

        # Ride the local surface + gentle bob
        self.bob_phase += dt * 3.2
        bob = 0.35 * math.sin(self.bob_phase)
        self.y = water.surface_y_at(self.x) + bob

    def draw(self, canvas, solid_mask=None):
        set_px = canvas.SetPixel
        mask = solid_mask or set()
        ox = int(round(self.x))
        oy = int(round(self.y))
        face = 1 if self.dir >= 0 else -1

        def put_rel(dx, dy, rgb):
            sx = ox + (dx if face >= 0 else -dx)
            sy = oy + dy
            if mask and (sx, sy) in mask:
                return
            if 0 <= sx < self.w and 0 <= sy < self.h:
                set_px(sx, sy, rgb[0], rgb[1], rgb[2])

        for dx, dy, rgb in _SAILBOAT_HULL:
            put_rel(dx, dy, rgb)

        # Sail: slowly lowers by dropping upper pixels first (furls toward boom)
        raise_amt = _clamp(self.sail_raise, 0.0, 1.0)
        if raise_amt > 0.04:
            for dx, dy, rgb in _SAILBOAT_SAIL:
                # dy is negative (up). Keep lower sail longer as raise falls.
                # Full sail uses dy in {-1,-2}; at half only dy=-1; at 0 none.
                sail_h = -dy  # 1 or 2
                max_h = 1.0 + 1.0 * raise_amt  # 1..2
                if sail_h <= max_h + 0.01:
                    # Collapse height: blend upper pixels down toward boom
                    draw_dy = dy
                    if raise_amt < 0.55 and dy <= -2:
                        continue
                    if raise_amt < 0.25:
                        # Almost furled — tiny flap at boom
                        if dy != -1 or dx != 1:
                            continue
                        draw_dy = 0
                    put_rel(dx, draw_dy, rgb)
        # Catch resting on deck (brief flash after a reel-in; bigger = more pixels)
        if self.fishing and self.catch_flash_t > 0.0:
            cr, cg, cb = self.catch_rgb
            face = 1 if self.dir >= 0 else -1
            if self.catch_size >= 3:
                deck_pts = (
                    (0, -1), (face, -1), (-face, -1),
                    (0, -2), (face, -2),
                    (0, -3),
                )
            elif self.catch_size >= 2:
                deck_pts = ((0, -1), (face, -1), (0, -2))
            else:
                deck_pts = ((0, -1), (face, -1))
            for dx, dy in deck_pts:
                sx, sy = ox + dx, oy + dy
                if mask and (sx, sy) in mask:
                    continue
                if 0 <= sx < self.w and 0 <= sy < self.h:
                    set_px(sx, sy, cr, cg, cb)

        # Fishing line + J-hook (minute calm)
        if self.fishing and self.line_len > 0.4:
            line_x = int(round(self._line_x()))
            n = max(1, int(math.floor(self.line_len)))
            for i in range(1, n + 1):
                sx, sy = line_x, oy + i
                if mask and (sx, sy) in mask:
                    continue
                if 0 <= sx < self.w and 0 <= sy < self.h:
                    set_px(sx, sy, LINE_RGB[0], LINE_RGB[1], LINE_RGB[2])
            # Little J at the end of the line:
            #   |
            #   |
            #   └─   (opens toward the bow; tip curls back up)
            open_d = self._hook_open()
            base_x, base_y = line_x, oy + n
            # (dx, dy, rgb) relative to line end
            j_pts = (
                (0, 0, HOOK_RGB),           # shank top (on line end)
                (0, 1, HOOK_RGB),           # shank
                (0, 2, HOOK_RGB),           # bottom of bend
                (open_d, 2, HOOK_RGB),      # bend out
                (open_d, 1, HOOK_TIP_RGB),  # tip of the J (point)
            )
            for dx, dy, rgb in j_pts:
                sx, sy = base_x + dx, base_y + dy
                if mask and (sx, sy) in mask:
                    continue
                if 0 <= sx < self.w and 0 <= sy < self.h:
                    set_px(sx, sy, rgb[0], rgb[1], rgb[2])
        # Anchor rode when at rest (not fishing — line replaces chain)
        elif self.anchored:
            for dy in (1, 2):
                sx, sy = ox, oy + dy
                if mask and (sx, sy) in mask:
                    continue
                if 0 <= sx < self.w and 0 <= sy < self.h:
                    set_px(sx, sy, BOAT_ANCHOR[0], BOAT_ANCHOR[1], BOAT_ANCHOR[2])


class FishSchool(object):
    """
    Fish during the fishing calm.

    Size tracks preferred depth: small near the surface, bigger near the
    bottom. A rare large red fish patrols the deep. They investigate the
    J-hook; touch = reeled into the boat.
    States: free | curious | hooked
    """

    def __init__(self, width, height):
        self.w = int(width)
        self.h = int(height)
        self.fish = []     # dicts
        self.active = False
        self._respawn_t = 0.0

    def set_fishing(self, active):
        active = bool(active)
        if active and not self.active:
            self.active = True
            self._respawn_t = FISH_RESPAWN_EVERY
            self._spawn()
        elif not active and self.active:
            self.active = False
            # Unhook anyone still on the line; free fish swim off
            for f in self.fish:
                if f["state"] == "hooked":
                    f["state"] = "free"

    def _make_fish(self, size, rare=False):
        """Build one fish. Bigger size → deeper preferred depth."""
        from_left = random.random() < 0.5
        if size >= 3:
            speed = random.uniform(*FISH_SPEED_BIG)
        else:
            speed = random.uniform(*FISH_SPEED)
        if from_left:
            x = random.uniform(-8.0 if size >= 3 else -6.0, -1.0)
            vx = speed
        else:
            x = random.uniform(self.w + 1.0, self.w + (8.0 if size >= 3 else 6.0))
            vx = -speed
        # Depth preference by size (0 = surface, 1 = floor)
        if size <= 1:
            depth_frac = random.uniform(0.12, 0.40)   # surface
        elif size == 2:
            depth_frac = random.uniform(0.40, 0.70)   # mid
        else:
            depth_frac = random.uniform(0.72, 0.95)   # bottom
        if rare:
            rgb = FISH_RARE_RED
            size = 4
            depth_frac = random.uniform(0.80, 0.97)
            speed = random.uniform(1.8, 3.4)
            vx = speed if from_left else -speed
        else:
            rgb = random.choice(FISH_COLORS)
        return {
            "x": x,
            "y": float(self.h) * (0.55 + 0.35 * depth_frac),
            "vx": vx,
            "vy": 0.0,
            "phase": random.uniform(0, math.pi * 2),
            "depth_frac": depth_frac,
            "rgb": rgb,
            "wiggle": random.uniform(1.6, 3.2) if size >= 3 else random.uniform(2.2, 4.5),
            "size": size,
            "rare": rare,
            "state": "free",
            "curious_t": random.uniform(0.8, 4.0) if size >= 3 else random.uniform(0.5, 3.5),
            "nibble_t": 0.0,
        }

    def _spawn(self):
        self.fish = []
        n = random.randint(FISH_COUNT_MIN, FISH_COUNT_MAX)
        rare_slot = random.random() < FISH_RARE_CHANCE
        for i in range(n):
            # Size mix: mostly small, some medium, occasional big bottom-dweller
            r = random.random()
            if r < 0.50:
                size = 1
            elif r < 0.82:
                size = 2
            else:
                size = 3
            self.fish.append(self._make_fish(size, rare=False))
        if rare_slot:
            self.fish.append(self._make_fish(4, rare=True))
            print(
                f"[WaterClock] {len(self.fish)} fish swimming in  "
                f"(including a RARE RED near the bottom)"
            )
        else:
            bigs = sum(1 for f in self.fish if f["size"] >= 3)
            print(
                f"[WaterClock] {len(self.fish)} fish swimming in  "
                f"({bigs} big bottom-dwellers)"
            )

    def update(self, dt, water, boat=None):
        # During long fishing trips, restock when the school thins out
        if self.active:
            self._respawn_t -= dt
            free_n = sum(1 for f in self.fish if f["state"] != "hooked")
            if self._respawn_t <= 0.0 or free_n < 2:
                self._respawn_t = FISH_RESPAWN_EVERY
                add = random.randint(1, 3)
                for _ in range(add):
                    r = random.random()
                    size = 1 if r < 0.55 else (2 if r < 0.88 else 3)
                    rare = random.random() < (FISH_RARE_CHANCE * 0.35)
                    self.fish.append(self._make_fish(4 if rare else size, rare=rare))
                if any(f.get("rare") for f in self.fish[-add:]):
                    print("[WaterClock] More fish (incl. rare red?) swam in")

        if not self.fish:
            return
        hook = boat.hook_tip() if boat is not None else None
        someone_hooked = any(f["state"] == "hooked" for f in self.fish)
        alive = []
        for f in self.fish:
            f["phase"] += dt * f["wiggle"]
            size = f["size"]
            touch_r = FISH_HOOK_TOUCH * (1.15 if size >= 3 else 1.0)
            notice_r = FISH_INVESTIGATE_RANGE * (0.85 if size >= 3 else 1.0)

            # ---- Hooked: stick to the J and ride the reel into the boat ----
            if f["state"] == "hooked" and boat is not None and boat.fishing:
                tip = boat.hook_tip()
                if tip is None:
                    boat.finish_catch(f["rgb"], size=f["size"], rare=f.get("rare", False))
                    continue
                f["x"], f["y"] = tip[0], tip[1]
                f["vx"] = 0.0
                f["vy"] = 0.0
                # Bigger fish fight a little — slightly slower effective land
                land_line = 1.4 if size >= 3 else 1.2
                if boat.line_len <= land_line or f["y"] <= boat.y + 1.5:
                    boat.finish_catch(f["rgb"], size=f["size"], rare=f.get("rare", False))
                    continue
                alive.append(f)
                continue

            # ---- Leaving when calm ends ----
            if not self.active:
                if f["x"] < self.w * 0.5:
                    f["vx"] = -abs(f["vx"]) - 2.0
                else:
                    f["vx"] = abs(f["vx"]) + 2.0
                f["x"] += f["vx"] * dt
                if -4.0 < f["x"] < self.w + 4.0:
                    alive.append(f)
                continue

            # ---- Free / curious swimming ----
            surf = water.surface_y_at(f["x"])
            floor = float(water.floor_y)
            water_depth = max(1.5, floor - surf)
            # Bigger fish hug the bottom more tightly
            rest_y = surf + 0.5 + f["depth_frac"] * (water_depth - 1.0)
            lo_y = surf + 0.7
            hi_y = floor - (0.35 if size >= 3 else 0.5)
            rest_y = _clamp(rest_y, lo_y, hi_y)
            bob = (0.22 if size >= 3 else 0.35) * math.sin(f["phase"])

            f["curious_t"] = max(0.0, f["curious_t"] - dt)
            can_investigate = (
                hook is not None
                and not someone_hooked
                and not (boat and boat.reeling)
                and f["curious_t"] <= 0.0
            )
            if can_investigate and f["state"] == "free":
                hx, hy = hook
                # Prefer hooks near their depth band (big fish ignore shallow bait)
                depth_ok = abs(hy - rest_y) < (5.5 if size >= 3 else 8.0)
                if depth_ok and math.hypot(f["x"] - hx, f["y"] - hy) < notice_r:
                    chance = 0.022 if size >= 3 else 0.038
                    if f.get("rare"):
                        chance *= 0.7  # rare red is wary
                    if random.random() < chance + 0.015 * dt * 10:
                        f["state"] = "curious"
                        f["nibble_t"] = random.uniform(1.4, 4.0) if size >= 3 else random.uniform(1.2, 3.5)

            if f["state"] == "curious" and hook is not None and not someone_hooked:
                hx, hy = hook
                dx = hx - f["x"]
                dy = hy - f["y"]
                dist = math.hypot(dx, dy) + 1e-6
                approach = (3.2 if size >= 3 else 4.2) if dist > 3.0 else (1.3 if size >= 3 else 1.8)
                f["vx"] = (dx / dist) * approach + (-dy / dist) * 1.1 * math.sin(f["phase"])
                f["vy"] = (dy / dist) * approach * 0.85
                f["x"] += f["vx"] * dt
                f["y"] += f["vy"] * dt
                f["y"] = _clamp(f["y"], lo_y, hi_y)
                f["nibble_t"] -= dt
                if dist <= touch_r:
                    f["state"] = "hooked"
                    f["x"], f["y"] = hx, hy
                    someone_hooked = True
                    if boat is not None:
                        boat.start_reel()
                    tag = "RARE RED" if f.get("rare") else ("big fish" if size >= 3 else "fish")
                    print(f"[WaterClock] {tag} took the hook!")
                elif f["nibble_t"] <= 0.0 and dist > 2.5:
                    f["state"] = "free"
                    f["curious_t"] = random.uniform(2.0, 5.5) if size >= 3 else random.uniform(1.5, 4.0)
                    spd_lo, spd_hi = FISH_SPEED_BIG if size >= 3 else FISH_SPEED
                    f["vx"] = random.choice((-1.0, 1.0)) * random.uniform(spd_lo, spd_hi)
            else:
                f["state"] = "free" if f["state"] != "hooked" else f["state"]
                f["y"] += ((rest_y + bob) - f["y"]) * min(1.0, 2.4 * dt if size >= 3 else 3.0 * dt)
                f["vx"] += random.uniform(-0.3, 0.3) * dt
                spd = abs(f["vx"])
                lo_s, hi_s = FISH_SPEED_BIG if size >= 3 else FISH_SPEED
                if spd < lo_s * 0.7:
                    f["vx"] = math.copysign(lo_s, f["vx"] if f["vx"] != 0 else 1.0)
                elif spd > hi_s:
                    f["vx"] = math.copysign(hi_s, f["vx"])
                if 4 < f["x"] < self.w - 4 and random.random() < (0.002 if size >= 3 else 0.004):
                    f["vx"] = -f["vx"]
                f["x"] += f["vx"] * dt

            if f["x"] < -2.0:
                f["x"] = -1.5
                f["vx"] = abs(f["vx"])
            elif f["x"] > self.w + 1.0:
                f["x"] = self.w + 0.5
                f["vx"] = -abs(f["vx"])
            alive.append(f)
        self.fish = alive

    def draw(self, canvas, solid_mask=None):
        if not self.fish:
            return
        set_px = canvas.SetPixel
        mask = solid_mask or set()
        for f in self.fish:
            fx = int(round(f["x"]))
            fy = int(round(f["y"]))
            r, g, b = f["rgb"]
            size = f["size"]
            if f["state"] == "hooked":
                facing = 1 if int(f["phase"] * 3) % 2 == 0 else -1
            else:
                facing = 1 if f["vx"] >= 0 else -1
            # Sprite scales with size (1 tiny … 4 rare red)
            if size <= 1:
                parts = [(0, 0), (facing, 0)]
            elif size == 2:
                parts = [(0, 0), (facing, 0), (-facing, 0), (0, -1)]
            elif size == 3:
                parts = [
                    (0, 0), (facing, 0), (2 * facing, 0),
                    (-facing, 0), (0, -1), (0, 1),
                ]
            else:
                # Rare red — chunky
                parts = [
                    (0, 0), (facing, 0), (2 * facing, 0),
                    (-facing, 0), (-2 * facing, 0),
                    (0, -1), (facing, -1),
                    (0, 1), (facing, 1),
                ]
            for dx, dy in parts:
                sx, sy = fx + dx, fy + dy
                if mask and (sx, sy) in mask:
                    continue
                if 0 <= sx < self.w and 0 <= sy < self.h:
                    if dx == facing or dx == 2 * facing:
                        set_px(sx, sy, min(255, r + 30), min(255, g + 20), min(255, b + 10))
                    else:
                        set_px(sx, sy, r, g, b)


def _draw_tiny_digit(canvas, ox, oy, digit, rgb, width, height):
    """1× scale 3×5 digit for the pier scoreboard."""
    grid = _digit_grid(digit)
    r, g, b = rgb
    set_px = canvas.SetPixel
    for ly in range(DIGIT_H0):
        for lx in range(DIGIT_W0):
            if not grid[ly * DIGIT_W0 + lx]:
                continue
            sx, sy = ox + lx, oy + ly
            if 0 <= sx < width and 0 <= sy < height:
                set_px(sx, sy, r, g, b)


def _draw_tiny_number(canvas, ox, oy, value, rgb, width, height):
    """Draw 0–99 as tiny digits, right-aligned toward ox as left of first digit."""
    n = int(max(0, min(99, value)))
    if n >= 10:
        _draw_tiny_digit(canvas, ox, oy, n // 10, rgb, width, height)
        _draw_tiny_digit(canvas, ox + DIGIT_W0 + 1, oy, n % 10, rgb, width, height)
    else:
        _draw_tiny_digit(canvas, ox + DIGIT_W0 + 1, oy, n, rgb, width, height)


class WoodenPier(object):
    """
    Simple brown dock: deck plank one pixel above the waterline + shade line.
    When the boat sails away, the dock scrolls off the opposite way at the
    same speed.
    """

    def __init__(self, width, height):
        self.w = int(width)
        self.h = int(height)
        self.fade = 0.0                 # 0..1
        self.target_fade = 0.0
        self.show_score = False
        self.display_count = 0          # digits on the board (counts up)
        self.goal_count = 0
        self.pile = []                  # fish resting on the pier {x,y,rgb,size}
        self.flying = []                # unload animation {x,y,tx,ty,rgb,size,t}
        # Compact deck near the right edge (home position)
        self.base_x0 = self.w - 8
        self.base_x1 = self.w - 3
        self.scroll_x = 0.0             # horizontal offset (scrolls when departing)
        self.scrolling_away = False

    @property
    def deck_x0(self):
        return int(round(self.base_x0 + self.scroll_x))

    @property
    def deck_x1(self):
        return int(round(self.base_x1 + self.scroll_x))

    @property
    def dock_x(self):
        """Center of the deck plank (scroll-aware)."""
        return (self.base_x0 + self.base_x1) * 0.5 + self.scroll_x

    def berth_x(self, facing=1):
        """
        Hull-center X so the bow tip just touches the dock (does not overlap).
        Approaching from the left, facing right: tip at +BOAT_BOW_OFFSET meets
        the left edge of the deck.
        """
        left = float(self.base_x0 + self.scroll_x)
        right = float(self.base_x1 + self.scroll_x)
        if facing >= 0:
            return left - float(BOAT_BOW_OFFSET)
        return right + float(BOAT_BOW_OFFSET)

    def show(self):
        """Bring dock to home position (only when unloading)."""
        self.scroll_x = 0.0
        self.scrolling_away = False
        self.target_fade = 1.0
        self.fade = 1.0  # pop in for the berth — boat is already in place

    def hide(self):
        """Remove dock until next unload (stays off-screen)."""
        self.target_fade = 0.0
        self.fade = 0.0
        self.show_score = False
        self.scrolling_away = False
        # Park off-screen so it cannot flash back until show()
        self.scroll_x = float(self.w + 4)

    def start_scroll_away(self):
        """Begin sliding off-screen opposite the boat (set during depart)."""
        self.scrolling_away = True
        self.show_score = False
        self.target_fade = 1.0  # stay solid while sliding

    def off_screen(self):
        return self.deck_x1 < 0 or self.deck_x0 >= self.w

    def reset_cargo(self):
        self.pile = []
        self.flying = []
        self.display_count = 0
        self.goal_count = 0
        self.show_score = False

    def begin_unload(self, catch_total):
        self.goal_count = int(max(0, catch_total))
        self.display_count = 0
        self.show_score = True
        self.flying = []
        self.pile = []

    def toss_one(self, rgb, size=1, from_xy=None):
        """Start one fish flying from the boat onto the pier deck."""
        slot = len(self.pile) + len(self.flying)
        span = max(1, self.base_x1 - self.base_x0 - 1)
        tx = self.base_x0 + 1 + (slot % span) + self.scroll_x
        ty = 0.0
        if from_xy is not None:
            sx, sy = from_xy
        else:
            sx, sy = self.dock_x - 2.0, float(self.h) * 0.55
        self.flying.append({
            "x": float(sx),
            "y": float(sy),
            "tx": float(tx),
            "ty": float(ty),
            "rgb": rgb,
            "size": size,
            "t": 0.0,
            "_sy": float(sy),
            "on_deck": True,
            "slot": slot % span,
        })

    def update(self, dt, water=None, boat_dx=0.0):
        # Fade pier in/out (not used while scrolling away)
        if not self.scrolling_away:
            if self.fade < self.target_fade:
                self.fade = min(self.target_fade, self.fade + dt * 1.2)
            elif self.fade > self.target_fade:
                self.fade = max(self.target_fade, self.fade - dt * 1.4)

        # Scroll opposite the boat at the same speed
        if self.scrolling_away and boat_dx != 0.0:
            self.scroll_x -= float(boat_dx)
            # Cargo rides the deck
            for p in self.pile:
                p["x"] -= float(boat_dx)
            for f in self.flying:
                f["x"] -= float(boat_dx)
                f["tx"] -= float(boat_dx)

        deck = self.deck_y(water)

        landed = []
        still = []
        for f in self.flying:
            f["ty"] = deck
            f["t"] += dt
            u = _clamp(f["t"] / 0.45, 0.0, 1.0)
            ease = u * u * (3.0 - 2.0 * u)
            sx0 = f.get("_sx", f["x"])
            if "_sx" not in f:
                f["_sx"] = f["x"]
                sx0 = f["x"]
            f["x"] = _lerp(sx0, f["tx"], ease)
            hop = 2.2 * math.sin(math.pi * u)
            f["y"] = _lerp(f.get("_sy", f["y"]), f["ty"], ease) - hop
            if u >= 1.0:
                landed.append(f)
            else:
                still.append(f)
        self.flying = still
        for f in landed:
            self.pile.append({
                "x": f["tx"], "y": deck,
                "rgb": f["rgb"], "size": f["size"],
            })
            if self.show_score:
                self.display_count = min(self.goal_count, self.display_count + 1)
        for p in self.pile:
            p["y"] = deck

    def unload_done(self):
        if not self.show_score:
            return False
        if self.flying:
            return False
        if self.goal_count <= 0:
            return True
        return self.display_count >= self.goal_count

    def deck_y(self, water):
        """Deck plank — exactly one pixel above the waterline."""
        if water is not None:
            return float(int(math.floor(water.surface_y_at(self.dock_x)))) - 1.0
        return float(self.h) * 0.55 - 1.0

    def draw(self, canvas, water=None, solid_mask=None):
        if self.fade < 0.05 and not self.scrolling_away:
            return
        if self.off_screen():
            return
        set_px = canvas.SetPixel
        mask = solid_mask or set()
        a = 1.0 if self.scrolling_away else self.fade
        if a < 0.05:
            return
        wood = (
            int(PIER_WOOD[0] * a),
            int(PIER_WOOD[1] * a),
            int(PIER_WOOD[2] * a),
        )
        shade = (
            int(PIER_WOOD_DARK[0] * a),
            int(PIER_WOOD_DARK[1] * a),
            int(PIER_WOOD_DARK[2] * a),
        )
        dy = int(round(self.deck_y(water)))
        dy = _clamp(dy, 1, self.h - 3)
        x0, x1 = self.deck_x0, self.deck_x1

        def put(x, y, rgb):
            if mask and (x, y) in mask:
                return
            if 0 <= x < self.w and 0 <= y < self.h:
                set_px(x, y, rgb[0], rgb[1], rgb[2])

        # Deck + shade only (no legs)
        #   ██████  ← deck 1px above water
        #   ░░░░░░  ← shade under deck
        for x in range(x0, x1 + 1):
            put(x, dy, wood)
            put(x, dy + 1, shade)

        if self.show_score and a > 0.6 and not self.scrolling_away:
            score_rgb = (
                int(SCORE_RGB[0] * a),
                int(SCORE_RGB[1] * a),
                int(SCORE_RGB[2] * a),
            )
            _draw_tiny_number(
                canvas, x0, max(0, dy - DIGIT_H0 - 1),
                self.display_count, score_rgb, self.w, self.h,
            )

        for f in self.pile:
            self._draw_fish_px(set_px, mask, f["x"], f["y"], f["rgb"], f["size"], a)
        for f in self.flying:
            self._draw_fish_px(set_px, mask, f["x"], f["y"], f["rgb"], f["size"], a)

    def _draw_fish_px(self, set_px, mask, x, y, rgb, size, a):
        r = int(rgb[0] * a)
        g = int(rgb[1] * a)
        b = int(rgb[2] * a)
        fx, fy = int(round(x)), int(round(y))
        pts = [(0, 0), (1, 0)]
        if size >= 2:
            pts.append((-1, 0))
        if size >= 3:
            pts.extend([(0, -1), (2, 0)])
        for dx, dy in pts:
            sx, sy = fx + dx, fy + dy
            if mask and (sx, sy) in mask:
                continue
            if 0 <= sx < self.w and 0 <= sy < self.h:
                set_px(sx, sy, r, g, b)


class FishingTrip(object):
    """
    Full fishing voyage:

      ready (start at pier) → depart → idle weather → fishing (5 min) →
      home → dock → unload → score → depart → weather resumes …

    Alias: FishingCalm (kept for older call sites).
    """

    def __init__(self, width, height):
        self.w = int(width)
        self.h = int(height)
        # ready|idle|fishing|home|dock|unload|score|depart
        self.phase = "idle"
        self.t = 0.0
        self.t_next = FISHING_INTERVAL
        self.sessions = 0
        self.pier = WoodenPier(width, height)
        self._unload_left = 0
        self._unload_timer = 0.0
        self._catch_rgbs = []           # colors to toss (padded if needed)
        self.active = False             # any non-idle phase
        self._prev_boat_x = None

    def begin_at_dock(self, water, wind, boat, fish):
        """
        Opening scene: calm water, pier up, boat tip just touching the dock.
        Called once from PlayWaterClock before the main loop.
        """
        self.phase = "ready"
        self.t = 0.0
        self.active = True
        self.pier.reset_cargo()
        self.pier.scroll_x = 0.0
        self.pier.scrolling_away = False
        self.pier.fade = 1.0
        self.pier.target_fade = 1.0
        self.pier.show_score = False
        self._prev_boat_x = None
        # Glassy high water + dead wind
        water.set_fishing(True)
        # Snap water flat/high immediately (no slow rise on boot)
        target = water.band * FISHING_RISE_FRAC
        water.level = [target for _ in range(water.w)]
        water.flow = [0.0 for _ in range(water.w)]
        water.droplets = []
        wind.set_fishing(True)
        wind.wind = 0.0
        wind.gust = 0.0
        fish.set_fishing(False)
        fish.fish = []
        # Bow tip just kisses the left edge of the dock (facing right)
        boat.fishing = False
        boat.line_len = 0.0
        boat.reeling = False
        boat.catches = 0
        boat.scripted = True
        boat.dir = 1
        boat.goal = 1
        boat.sail_raise = 1.0
        boat.x = self.pier.berth_x(facing=1)
        boat.script_target_x = boat.x
        boat.anchored = True
        boat.y = water.surface_y_at(boat.x)
        print(
            f"[WaterClock] Opening at the pier — calm water, boat ready to sail  "
            f"({START_READY_HOLD:.0f}s)"
        )

    def update(self, dt, water, wind, boat, fish):
        if self.phase == "idle":
            self.active = False
            self.t_next -= dt
            if self.t_next <= 0.0:
                self._begin_fishing(water, wind, boat, fish)
            return

        self.active = True
        self.t += dt
        # Track boat motion so the dock can scroll the opposite way
        if self._prev_boat_x is None:
            self._prev_boat_x = boat.x
        boat_dx = boat.x - self._prev_boat_x
        self._prev_boat_x = boat.x
        self.pier.update(dt, water, boat_dx=boat_dx)

        if self.phase == "ready":
            # Hold with bow tip on the dock, then cast off into the day
            boat.x = self.pier.berth_x(facing=1)
            boat.dir = 1
            boat.anchored = True
            boat.scripted = True
            boat.script_target_x = boat.x
            self._prev_boat_x = boat.x
            if self.t >= START_READY_HOLD:
                self._begin_depart(boat)

        elif self.phase == "fishing":
            if self.t >= FISHING_DURATION:
                self._begin_home(water, wind, boat, fish)

        elif self.phase == "home":
            # Dock stays off-screen until unload; boat sails to berth alone
            if boat.arrived_scripted():
                self._begin_dock(boat)

        elif self.phase == "dock":
            # Tip on dock; slowly lower the sail, then unload
            boat.x = self.pier.berth_x(facing=1)
            boat.dir = 1
            boat.anchored = True
            boat.scripted = True
            boat.script_target_x = boat.x
            if self.t >= DOCK_HOLD and boat.lower_sail(dt, SAIL_LOWER_TIME):
                self._begin_unload(boat)

        elif self.phase == "unload":
            self._unload_timer -= dt
            if self._unload_left > 0 and self._unload_timer <= 0.0:
                rgb = FISH_COLORS[0]
                size = 1
                if self._catch_rgbs:
                    rgb, size = self._catch_rgbs.pop(0)
                self.pier.toss_one(
                    rgb, size=size, from_xy=(boat.x, boat.y - 1.0),
                )
                self._unload_left -= 1
                self._unload_timer = UNLOAD_INTERVAL
            if self._unload_left <= 0 and self.pier.unload_done():
                self.phase = "score"
                self.t = 0.0
                # Snap display to full total
                self.pier.display_count = self.pier.goal_count
                print(
                    f"[WaterClock] Unloaded at pier — scoreboard {self.pier.goal_count}"
                )

        elif self.phase == "score":
            if self.t >= SCORE_HOLD:
                self._begin_depart(boat)

        elif self.phase == "depart":
            # Done when boat reaches the far side (dock has scrolled off opposite)
            if boat.arrived_scripted() or boat.x <= BOAT_EDGE_PAD + 2:
                self._resume(water, wind, boat, fish)

    def draw(self, canvas, water=None, solid_mask=None):
        self.pier.draw(canvas, water=water, solid_mask=solid_mask)

    def _begin_fishing(self, water, wind, boat, fish):
        self.phase = "fishing"
        self.t = 0.0
        self.sessions += 1
        self.pier.reset_cargo()
        self.pier.hide()
        water.set_fishing(True)
        wind.set_fishing(True)
        boat.clear_scripted()
        boat.set_fishing(True, reset_catches=True)
        fish.set_fishing(True)
        print(
            f"[WaterClock] Fishing trip #{self.sessions}  "
            f"({FISHING_DURATION / 60.0:.0f} min) — water rising, wind dead"
        )

    def _begin_home(self, water, wind, boat, fish):
        self.phase = "home"
        self.t = 0.0
        # Still calm seas; reel in, fish leave. Dock stays hidden until unload.
        boat.set_fishing(False)
        fish.set_fishing(False)
        water.set_fishing(True)   # stay glassy for the home run
        wind.set_fishing(True)
        self.pier.hide()          # do not reappear until unload
        self._prev_boat_x = boat.x
        # Sail to berth position (bow tip will touch dock when pier appears)
        berth = self.pier.berth_x(facing=1)
        # berth_x while scroll is off-screen uses wrong x — use home berth
        berth = float(self.pier.base_x0 - BOAT_BOW_OFFSET)
        boat.start_scripted_sail(berth, direction=1, speed=BOAT_HOME_SPEED)
        print(
            f"[WaterClock] Heading home with {boat.catches} fish "
            f"(dock waits until unload)"
        )

    def _begin_dock(self, boat):
        self.phase = "dock"
        self.t = 0.0
        # Only now does the dock reappear
        self.pier.show()
        boat.dir = 1
        boat.x = self.pier.berth_x(facing=1)
        boat.anchored = True
        boat.scripted = True
        boat.script_target_x = boat.x
        boat.sail_raise = 1.0  # will lower before unload
        print("[WaterClock] Docked — bow tip on the pier, lowering sail")

    def _begin_unload(self, boat):
        self.phase = "unload"
        self.t = 0.0
        total = max(0, int(boat.catches))
        self.pier.begin_unload(total)
        # Build toss list (use catch flash color if we only know total)
        self._catch_rgbs = []
        for i in range(total):
            self._catch_rgbs.append((
                random.choice(FISH_COLORS) if i > 0 or total == 0 else (
                    boat.catch_rgb if boat.catches else random.choice(FISH_COLORS)
                ),
                1 + (i % 3),
            ))
        # Ensure at least we show the number even with 0 fish
        self._unload_left = total
        self._unload_timer = 0.15
        if total == 0:
            self.pier.display_count = 0
            self.pier.show_score = True
        print(f"[WaterClock] Unloading {total} fish onto the pier")

    def _begin_depart(self, boat):
        self.phase = "depart"
        self.t = 0.0
        boat.anchored = False
        boat.sail_raise = 1.0  # raise sail for cast-off
        # Sail left; dock scrolls right at the same speed
        if self.pier.fade > 0.05 or not self.pier.off_screen():
            self.pier.start_scroll_away()
        self._prev_boat_x = boat.x
        boat.start_scripted_sail(
            float(BOAT_EDGE_PAD + 2), direction=-1, speed=BOAT_HOME_SPEED * 1.05,
            raise_sail=True,
        )
        print("[WaterClock] Cast off — dock scrolling opposite the boat")

    def _resume(self, water, wind, boat, fish):
        self.phase = "idle"
        self.t = 0.0
        self.t_next = FISHING_INTERVAL
        self.active = False
        self._prev_boat_x = None
        water.set_fishing(False)
        wind.set_fishing(False)
        fish.set_fishing(False)
        boat.clear_scripted()
        boat.goal = -1
        boat.dir = -1
        boat.sail_raise = 1.0
        self.pier.hide()  # off-screen until next unload
        self.pier.reset_cargo()
        print("[WaterClock] Trip complete — weather patterns resume")


# Back-compat name used by the main loop
FishingCalm = FishingTrip


# ---------------- Main loop ----------------
def PlayWaterClock(Duration=10, StopEvent=None):
    """Shaded HH:MM + tide water + sailboat. Duration in minutes."""
    width = int(getattr(LED, "HatWidth", 64) or 64)
    height = int(getattr(LED, "HatHeight", 32) or 32)

    try:
        canvas = LED.TheMatrix.CreateFrameCanvas()
    except Exception:
        canvas = LED.Canvas

    start = time.time()
    try:
        run_min = float(Duration)
    except (TypeError, ValueError):
        run_min = 10.0
    if run_min <= 0:
        run_min = 10.0

    water = WaterSim(width, height)
    wind = WindField()
    boat = Sailboat(width, height)
    fish = FishSchool(width, height)
    fishing = FishingTrip(width, height)
    # Opening: calm water, pier up, boat docked and ready to sail
    fishing.begin_at_dock(water, wind, boat, fish)
    sun = Sun(width, height)
    moon = Moon(width, height)
    tick = pygame.time.Clock() if HAS_PYGAME else None
    last = time.time()

    print(
        f"[WaterClock] {width}x{height}  shaded HH:MM + tide + sailboat + Ottawa sun/moon  "
        f"(wind + current)  start at pier → fishing trip {FISHING_DURATION / 60.0:.0f}min "
        f"every {FISHING_INTERVAL:.0f}s  duration={run_min} min  fps~{TARGET_FPS}"
    )

    try:
        while True:
            if _stop(StopEvent):
                print("[WaterClock] StopEvent — exit")
                break
            if time.time() - start > run_min * 60.0:
                print("[WaterClock] Duration reached — exit")
                break

            now = time.time()
            dt = _clamp(now - last, 0.001, 0.1)
            last = now

            blink = (int(time.time()) % 2) == 0
            # Lit glyph pixels only — sun/moon/water show through unlit segments
            mask = build_clock_solid_mask(width, height, blink_on=blink)
            # Minute fishing calm drives water / wind / boat / fish together
            fishing.update(dt, water, wind, boat, fish)
            water.update(dt, solid_mask=mask)
            wval = wind.update(dt)
            boat.update(dt, water, wval)
            fish.update(dt, water, boat=boat)
            sun.update()   # position from real Ottawa civil time only
            moon.update()  # moonrise → moonset on the same fixed path

            try:
                canvas.Fill(BG[0], BG[1], BG[2])
                # Sky first; reflections after water; lit digits last
                moon.draw(canvas, solid_mask=mask)
                sun.draw(canvas, solid_mask=mask)
                water.draw(canvas, solid_mask=mask)
                moon.draw_reflection(canvas, water, solid_mask=mask)
                sun.draw_reflection(canvas, water, solid_mask=mask)
                fishing.draw(canvas, water=water, solid_mask=mask)
                fish.draw(canvas, solid_mask=mask)
                boat.draw(canvas, solid_mask=mask)
                draw_time(canvas, width, height)
                canvas = LED.TheMatrix.SwapOnVSync(canvas)
                LED.Canvas = canvas
            except Exception:
                pass

            if tick:
                tick.tick(TARGET_FPS)
            else:
                time.sleep(1.0 / TARGET_FPS)

    except KeyboardInterrupt:
        print("[WaterClock] Interrupted")

    try:
        LED.ClearBuffers()
        LED.TheMatrix.Clear()
    except Exception:
        pass


def LaunchWaterClock(Duration=10, ShowIntro=False, StopEvent=None, Style=None):
    """Launch the water clock (Style arg ignored for API compatibility)."""
    try:
        LED.LoadConfigData()
    except Exception:
        pass
    PlayWaterClock(Duration=Duration, StopEvent=StopEvent)


if __name__ == "__main__":
    try:
        LaunchWaterClock(Duration=30, StopEvent=None)
    except KeyboardInterrupt:
        print("Exiting WaterClock.")
