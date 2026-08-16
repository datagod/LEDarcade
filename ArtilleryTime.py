# =====================================================================================
# ARTILLERY TIME — turn-based artillery duel on a wide scrolling battlefield
#
# World is wider than the 64×32 panel. Two guns face off across hills of dirt and
# earth. A digital HUD sits mid-field. Each turn the active gun reads the wind,
# range, and charge, then lob a shell. One direct hit or two shrapnel hits ends a
# round. Best 2 of 3 wins the war.
#
# Launch: LEDpanel / LEDcommander "launch_artillerytime" / standalone
# =====================================================================================

from __future__ import annotations

import copy
import math
import random
import time
from datetime import datetime

import LEDarcade as LED

LED.Initialize()

try:
    import pygame
    HAS_PYGAME = True
except Exception:
    HAS_PYGAME = False


# ---- Panel / world ----
TARGET_FPS = 30
WORLD_W = 128                 # wider than playfield (camera scrolls)
VIEW_W = int(getattr(LED, "HatWidth", 64) or 64)
VIEW_H = int(getattr(LED, "HatHeight", 32) or 32)

# ---- Title intro ("ARTY TIME" stylized letters + shell barrage) ----
TITLE_LINE1 = "ARTY"
TITLE_LINE2 = "TIME"
TITLE_LETTER_ZOOM = 2
TITLE_LETTER_GAP = 1
TITLE_LINE_GAP = 2
TITLE_LETTER_RGB = (255, 90, 40)
TITLE_LETTER_SHADOW_RGB = (70, 18, 8)
TITLE_LETTER_STAGGER = 0.18
TITLE_LETTER_GRAVITY = 0.58
TITLE_LETTER_BOUNCE_DAMP = 0.42
TITLE_LETTER_SETTLE_V = 0.35
TITLE_LETTER_MAX_BOUNCES = 3
TITLE_HOLD_SECONDS = 1.1
TITLE_BARRAGE_SECONDS = 4.5
TITLE_INTRO_MAX_SECONDS = 16.0
TITLE_SHELL_RGB = (255, 230, 90)
TITLE_INTRO_FPS = 30

# ---- Terrain ----
# Fallback sky (overridden by real-time sky_colors_for_hour)
SKY_TOP = (8, 12, 40)
SKY_BOT = (40, 70, 120)
GRASS = (40, 160, 50)
GRASS_DARK = (25, 100, 35)
DIRT = (110, 70, 30)
DIRT_DARK = (70, 42, 18)
ROCK = (90, 90, 95)

# Time-of-day sky keyframes: (hour 0..24, zenith RGB, horizon RGB)
# Night = pure black; day = deep blue (clouds drawn separately).
_SKY_KEYS = (
    (0.00, (0, 0, 0),       (0, 0, 0)),         # midnight — black
    (4.50, (0, 0, 0),       (0, 0, 0)),         # deep night
    (5.50, (4, 6, 14),      (20, 18, 30)),      # predawn
    (6.25, (25, 40, 90),    (160, 95, 50)),     # sunrise
    (7.50, (12, 42, 120),   (35, 80, 155)),     # deep blue morning
    (12.00, (8, 35, 110),   (28, 75, 155)),     # noon deep blue
    (16.00, (10, 40, 115),  (32, 78, 155)),     # afternoon
    (17.75, (30, 55, 110),  (170, 110, 60)),    # golden hour
    (19.00, (25, 25, 55),   (180, 70, 30)),     # sunset
    (20.25, (5, 5, 12),     (20, 12, 18)),      # dusk
    (21.25, (0, 0, 0),      (0, 0, 0)),         # night — black
    (24.00, (0, 0, 0),      (0, 0, 0)),
)

# Daytime puffy clouds: (y_frac, speed_px/s, scale, x_phase)
_SKY_CLOUDS = (
    (0.14, 0.55, 1.00, 0.0),
    (0.26, 0.38, 1.25, 28.0),
    (0.10, 0.70, 0.85, 52.0),
    (0.22, 0.45, 0.95, 80.0),
)
# Overlapping soft puffs that make one cloud (ox, oy, radius)
_CLOUD_PUFFS = (
    (0.0, 0.0, 2.3),
    (-2.8, 0.4, 1.7),
    (2.6, 0.3, 1.8),
    (-1.0, -1.3, 1.5),
    (1.4, -1.1, 1.4),
    (0.2, 1.0, 1.3),
)

# ---- Top HUD 7-seg clock (same style as SevenSegClock / pinball apron) ----
SEG_CLOCK_RGB = (255, 36, 28)       # lit red (night / default)
SEG_CLOCK_DIM = (27, 6, 5)          # ghost segments
SEG_CLOCK_RGB_DAY = (255, 70, 45)   # brighter red-orange for blue day sky
SEG_CLOCK_DIM_DAY = (55, 14, 10)    # stronger ghost so digits still read
SEG_DIGIT_W = 5
SEG_DIGIT_H = 9
SEG_THICK = 1
SEG_GAP = 1
SEG_COLON_W = 2
_SEG_A, _SEG_B, _SEG_C, _SEG_D = 0x01, 0x02, 0x04, 0x08
_SEG_E, _SEG_F, _SEG_G = 0x10, 0x20, 0x40
_SEG_DIGIT_MASKS = (
    0x3F, 0x06, 0x5B, 0x4F, 0x66, 0x6D, 0x7D, 0x07, 0x7F, 0x6F,
)

# ---- Guns ----
GUN_L_RGB = (60, 180, 255)
GUN_R_RGB = (255, 90, 60)
GUN_BARREL = (220, 220, 230)
HP_MAX_SHRAPNEL = 2           # survive this many indirect hits
# one direct hit always destroys

# ---- Ballistics ----
GRAVITY = 28.0                # px/s^2 downward
WIND_MIN, WIND_MAX = -4.5, 4.5
SHELL_TRAIL = 14
SHELL_TRAIL_LIFE = 0.55
SHELL_TRAIL_FADE_RATE = 1.85
SHELL_RGB = (255, 240, 120)
EXPLODE_SPARKS = 22

# ---- Weapons (assigned random per gun at each war start) ----
# standard    — classic HE
# airburst    — only detonates once over the enemy, rain of shrapnel
# heavy       — huge blast crater; only 2 shots per war
# laser       — bank-shot beam bouncing off the top of the screen
# phosphorous — bouncing burner that keeps sparking
# bouncer     — bouncing bomb; 3 ground bounces then detonates
# sam         — surface-to-air missile; huge airburst over the target
# acid        — dissolves earth; ground collapses/shifts (re-aim needed)
# flame       — lands and flames burst out across the ground
# mg30        — high-arc 30mm; bullets fall in a storm
# drone       — single-pixel drones hover over enemy, intercept shots, then storm
# nuke        — one mushroom-cloud super shell per war
WEAPONS = (
    "standard",
    "airburst",
    "heavy",
    "laser",
    "phosphorous",
    "bouncer",
    "sam",
    "acid",
    "flame",
    "mg30",
    "drone",
    "nuke",
)
WEAPON_AMMO = {
    "heavy": 2,
    "nuke": 1,
    "sam": 3,
    "acid": 3,
    "mg30": 4,
    "drone": 2,
}
WEAPON_RGB = {
    "standard": (255, 240, 120),
    "airburst": (200, 220, 255),
    "heavy": (255, 120, 40),
    "laser": (255, 40, 60),
    "phosphorous": (180, 255, 80),
    "bouncer": (255, 170, 60),
    "sam": (120, 255, 200),
    "acid": (80, 255, 40),
    "flame": (255, 90, 20),
    "mg30": (200, 200, 180),
    "drone": (100, 230, 255),
    "nuke": (255, 255, 200),
}
BOUNCE_BOMB_BOUNCES = 3       # bouncer detonates after this many ground hits
AIRBURST_OVER_X = 9.0         # horizontal window over enemy for airburst fuse
SAM_OVER_X = 11.0             # SAM fuse window over enemy
SAM_AIR_CLEARANCE = 4.5       # min px above surface / target for SAM fuse
ACID_RADIUS = 12
ACID_DEPTH = 6
FLAME_MAX_REACH = 16
MG30_BULLETS = 32
DRONE_COUNT = 5
DRONE_SPEED = 32.0
DRONE_INTERCEPT_R = 2.6
DRONE_HOVER_MAX = 7.5         # storm if no intercept by then
DRONE_HOVER_MIN = 1.2         # min hover before timeout storm

# ---- Timing (seconds) ----
THINK_SEC = 1.4
CHARGE_SEC = 1.1
IMPACT_HOLD = 1.0
CLOCK_HOLD_SEC = 5.0          # full clock visible this long at banners
# Banner: fade-in (~1s) + 5s hold + fade-out (~0.9s)
ROUND_BANNER = 7.0
WAR_BANNER = 7.0
PHOS_BURN_SEC = 2.8
MUSHROOM_SEC = 2.2
ACID_FX_SEC = 1.9
FLAME_BURST_SEC = 2.5
MG_RAIN_SEC = 1.6
DRONE_STORM_SEC = 1.8
DESTROY_FX_SEC = 1.5          # big death explosion hold
DRIVE_IN_SEC = 2.2            # replacement rolls onto the field
VICTORY_DRIVE_SEC = 2.8       # winner to center
VICTORY_FIREWORKS_SEC = 4.0   # fireworks + YOU WIN
YOU_WIN_RGB = (255, 255, 0)   # solid pure yellow

# ---- Match ----
ROUNDS_TO_WIN = 2


def _stop(StopEvent):
    try:
        return StopEvent is not None and StopEvent.is_set()
    except Exception:
        return False


def _clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def _lerp(a, b, t):
    return a + (b - a) * t


def _lerp_rgb(a, b, t):
    return (
        int(_lerp(a[0], b[0], t)),
        int(_lerp(a[1], b[1], t)),
        int(_lerp(a[2], b[2], t)),
    )


def _smooth(t):
    t = _clamp(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _smoother(t):
    """Quintic smoothstep — very soft ease-in/out for zoom."""
    t = _clamp(t, 0.0, 1.0)
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def sky_hour_now(now=None):
    """Fractional local hour in [0, 24)."""
    if now is None:
        now = datetime.now()
    return (
        now.hour
        + now.minute / 60.0
        + now.second / 3600.0
        + now.microsecond / 3_600_000_000.0
    ) % 24.0


def sky_colors_for_hour(hour=None):
    """
    Zenith + horizon RGB for the given fractional hour (0..24).
    Matches real clock: night, dawn, day, sunset, dusk.
    """
    if hour is None:
        hour = sky_hour_now()
    h = float(hour) % 24.0
    keys = _SKY_KEYS
    # Find surrounding keyframes (last key is 24.0 wrapping to midnight)
    for i in range(len(keys) - 1):
        h0, top0, bot0 = keys[i]
        h1, top1, bot1 = keys[i + 1]
        if h0 <= h <= h1 or (i == len(keys) - 2 and h >= h0):
            span = max(1e-6, h1 - h0)
            u = _smooth((h - h0) / span)
            return _lerp_rgb(top0, top1, u), _lerp_rgb(bot0, bot1, u)
    return keys[0][1], keys[0][2]


def sky_is_night(top_rgb, bot_rgb):
    """True for black / near-black night sky (stars + moon)."""
    lum = 0.30 * bot_rgb[0] + 0.59 * bot_rgb[1] + 0.11 * bot_rgb[2]
    top_lum = 0.30 * top_rgb[0] + 0.59 * top_rgb[1] + 0.11 * top_rgb[2]
    return lum < 18.0 and top_lum < 18.0


def sky_is_day(hour=None):
    """True when the sun is well up — deep blue + drifting clouds."""
    if hour is None:
        hour = sky_hour_now()
    h = float(hour) % 24.0
    # Roughly after sunrise through before sunset
    return 7.2 <= h <= 17.4


# A few fixed star positions — sparse night sky
_NIGHT_STARS = (
    (0.10, 0.12),
    (0.22, 0.06),
    (0.38, 0.18),
    (0.55, 0.09),
    (0.70, 0.15),
    (0.84, 0.05),
    (0.92, 0.20),
)


def _moon_params(hour, width, height):
    """Soft moon at night — high and left. Returns (cx, cy, rad) or None."""
    h = float(hour) % 24.0
    elev = math.cos((h - 12.0) / 12.0 * math.pi)
    if elev >= -0.12:
        return None
    # Stay on the left third of the panel; tiny drift with hour so it isn't frozen
    day_u = _clamp((h - 5.0) / 15.0, 0.0, 1.0)
    cx = 4.0 + day_u * (width * 0.22)   # roughly x 4..18 on 64-wide
    cy = height * (0.06 + 0.04 * min(1.0, abs(elev)))  # high near top
    return cx, cy, 1.35


def _draw_puffy_cloud(set_px, cx, cy, width, height, scale=1.0):
    """Stamp one soft white cloud (overlapping puffs) onto the sky."""
    # Soft white with a hint of blue so it sits in deep blue sky
    core = (230, 235, 245)
    edge = (160, 185, 220)
    for ox, oy, rr in _CLOUD_PUFFS:
        r = rr * scale
        x0 = max(0, int(math.floor(cx + ox * scale - r - 0.5)))
        x1 = min(width - 1, int(math.ceil(cx + ox * scale + r + 0.5)))
        y0 = max(0, int(math.floor(cy + oy * scale - r - 0.5)))
        y1 = min(height - 1, int(math.ceil(cy + oy * scale + r + 0.5)))
        px0 = cx + ox * scale
        py0 = cy + oy * scale
        for py in range(y0, y1 + 1):
            for px in range(x0, x1 + 1):
                d = math.hypot(px + 0.5 - px0, py + 0.5 - py0)
                if d > r:
                    continue
                # Soft falloff — puffy, not hard circles
                k = 1.0 - (d / r)
                k = k * k * (3.0 - 2.0 * k)
                if k < 0.12:
                    continue
                # Bright core, softer blue-white rim
                if k > 0.55:
                    set_px(
                        px, py,
                        min(255, int(_lerp(edge[0], core[0], k))),
                        min(255, int(_lerp(edge[1], core[1], k))),
                        min(255, int(_lerp(edge[2], core[2], k))),
                    )
                else:
                    # Lighter blend — still readable on deep blue
                    set_px(
                        px, py,
                        min(255, int(28 + edge[0] * k * 0.9)),
                        min(255, int(70 + edge[1] * k * 0.75)),
                        min(255, int(140 + edge[2] * k * 0.45)),
                    )


def _draw_day_clouds(canvas, width, height):
    """Slow-drifting puffy clouds (wall-clock based so motion is continuous)."""
    set_px = canvas.SetPixel
    t = time.time()
    span = float(width + 24)  # wrap margin so clouds re-enter smoothly
    for y_frac, speed, scale, phase in _SKY_CLOUDS:
        cy = y_frac * (height - 1)
        # Drift left→right slowly, wrap
        cx = ((t * speed + phase) % span) - 12.0
        _draw_puffy_cloud(set_px, cx, cy, width, height, scale=scale)


def fill_sky(canvas, width, height, hour=None):
    """
    Time-of-day sky:
      night — pure black + very faint blue stars + moon
      day   — deep blue + slow puffy clouds
    """
    if hour is None:
        hour = sky_hour_now()
    top, bot = sky_colors_for_hour(hour)
    night = sky_is_night(top, bot)
    day = sky_is_day(hour)
    set_px = canvas.SetPixel
    denom = max(1, height - 1)

    # 1) Base gradient
    for y in range(height):
        t = y / denom
        u = t * t * (3.0 - 2.0 * t)
        r = int(_lerp(top[0], bot[0], u))
        g = int(_lerp(top[1], bot[1], u))
        b = int(_lerp(top[2], bot[2], u))
        for x in range(width):
            set_px(x, y, r, g, b)

    # 2) Day: slow floating puffy clouds
    if day:
        _draw_day_clouds(canvas, width, height)
        return top, bot

    if not night:
        return top, bot

    # 3) Night: very faint blue stars on black
    for i, (fx, fy) in enumerate(_NIGHT_STARS):
        sx = int(round(fx * (width - 1)))
        sy = int(round(fy * (height - 1)))
        if not (0 <= sx < width and 0 <= sy < height):
            continue
        # Barely-there cool blue; tiny brightness wobble
        phase = (hour * 0.12 + i * 0.9) % 1.0
        br = 0.70 + 0.30 * (0.5 + 0.5 * math.sin(phase * math.tau))
        set_px(
            sx, sy,
            min(255, int(18 * br)),
            min(255, int(28 * br)),
            min(255, int(55 * br)),
        )

    # 4) Soft moon
    moon = _moon_params(hour, width, height)
    if moon is not None:
        mx, my, rad = moon
        x0 = max(0, int(math.floor(mx - rad - 1)))
        x1 = min(width - 1, int(math.ceil(mx + rad + 1)))
        y0 = max(0, int(math.floor(my - rad - 1)))
        y1 = min(height - 1, int(math.ceil(my + rad + 1)))
        for py in range(y0, y1 + 1):
            for px in range(x0, x1 + 1):
                d = math.hypot(px + 0.5 - mx, py + 0.5 - my)
                if d <= rad * 0.55:
                    set_px(px, py, 180, 185, 200)
                elif d <= rad:
                    k = 1.0 - (d / rad)
                    set_px(
                        px, py,
                        min(255, int(20 + 140 * k)),
                        min(255, int(22 + 145 * k)),
                        min(255, int(30 + 155 * k)),
                    )
    return top, bot


# ---------------- Tiny 3×5 digits for HUD / score ----------------
_DIGIT = {
    "0": ("111", "101", "101", "101", "111"),
    "1": ("010", "110", "010", "010", "111"),
    "2": ("111", "001", "111", "100", "111"),
    "3": ("111", "001", "111", "001", "111"),
    "4": ("101", "101", "111", "001", "001"),
    "5": ("111", "100", "111", "001", "111"),
    "6": ("111", "100", "111", "101", "111"),
    "7": ("111", "001", "001", "001", "001"),
    "8": ("111", "101", "111", "101", "111"),
    "9": ("111", "101", "111", "001", "111"),
    "-": ("000", "000", "111", "000", "000"),
    "+": ("000", "010", "111", "010", "000"),
    "W": ("101", "101", "101", "101", "010"),
    "I": ("111", "010", "010", "010", "111"),
    "N": ("101", "111", "111", "101", "101"),
    "D": ("110", "101", "101", "101", "110"),
    " ": ("000", "000", "000", "000", "000"),
    ":": ("0", "1", "0", "1", "0"),
    "L": ("100", "100", "100", "100", "111"),
    "R": ("110", "101", "110", "101", "101"),
    "S": ("111", "100", "111", "001", "111"),
    "C": ("111", "100", "100", "100", "111"),
    "H": ("101", "101", "111", "101", "101"),
    "T": ("111", "010", "010", "010", "010"),
    "E": ("111", "100", "111", "100", "111"),
    "A": ("010", "101", "111", "101", "101"),
    "G": ("111", "100", "101", "101", "111"),
    "O": ("111", "101", "101", "101", "111"),
    "U": ("101", "101", "101", "101", "111"),
    "V": ("101", "101", "101", "101", "010"),
    "Y": ("101", "101", "010", "010", "010"),
    "B": ("110", "101", "110", "101", "110"),
    "F": ("111", "100", "110", "100", "100"),
    "P": ("111", "101", "111", "100", "100"),
    "M": ("101", "111", "111", "101", "101"),
    "!": ("010", "010", "010", "000", "010"),
}


def _draw_text(canvas, sx, sy, text, rgb, cam_x=0, scale=1):
    """Draw string in world or screen space. cam_x shifts world→screen."""
    set_px = canvas.SetPixel
    x = float(sx)
    sc = max(1, int(scale))
    for ch in text.upper():
        rows = _DIGIT.get(ch, _DIGIT.get(" ", ("000",) * 5))
        gw = len(rows[0])
        for ry, row in enumerate(rows):
            for rx, bit in enumerate(row):
                if bit != "1":
                    continue
                for dy in range(sc):
                    for dx in range(sc):
                        px = int(round(x + rx * sc + dx - cam_x))
                        py = int(sy + ry * sc + dy)
                        if 0 <= px < VIEW_W and 0 <= py < VIEW_H:
                            set_px(px, py, *rgb)
        x += (gw + 1) * sc


# ---------------- Terrain ----------------
def generate_terrain(world_w, view_h, seed=None):
    """
    Heightmap: surface y for each world x (0=top). Returns list of ints.
    Ground fills from surface down to bottom with dirt layers.
    """
    rng = random.Random(seed if seed is not None else random.randrange(1 << 30))
    # Mid-height baseline with rolling hills
    base = view_h * 0.55
    heights = []
    h = base + rng.uniform(-2, 2)
    for x in range(world_w):
        h += rng.uniform(-0.55, 0.55)
        # Low-frequency hills
        h += math.sin(x * 0.07 + rng.random()) * 0.15
        h += math.sin(x * 0.03) * 0.35
        # Flatten near gun pads
        if x < 18 or x > world_w - 19:
            h = _lerp(h, view_h * 0.62, 0.25)
        # Slight valley mid for the digital display mound
        mid = world_w * 0.5
        if abs(x - mid) < 14:
            h = _lerp(h, view_h * 0.58, 0.12)
        h = _clamp(h, view_h * 0.38, view_h * 0.78)
        heights.append(h)
    # Smooth a few passes
    for _ in range(3):
        nxt = heights[:]
        for x in range(1, world_w - 1):
            nxt[x] = 0.25 * heights[x - 1] + 0.5 * heights[x] + 0.25 * heights[x + 1]
        heights = nxt
    return [int(round(v)) for v in heights]


def surface_y(heights, x):
    xi = int(_clamp(round(x), 0, len(heights) - 1))
    return float(heights[xi])


def crater(heights, x, radius=4, depth=3):
    """Blast a bowl into the heightmap."""
    xi = int(round(x))
    r = int(max(1, radius))
    d0 = max(1, depth)
    for dx in range(-r, r + 1):
        px = xi + dx
        if 0 <= px < len(heights):
            fall = 1.0 - (abs(dx) / float(max(1, r)))
            dig = d0 * fall * fall
            heights[px] = int(_clamp(heights[px] + dig, VIEW_H * 0.35, VIEW_H - 2))


def blast_push_gun(g, heights, ix, iy, radius, strength=1.0):
    """
    If a gun is close to a blast, shove it away from the impact and reseat
    it on the (possibly cratered) ground. Returns True if moved.
    """
    if g is None or not g.alive or g.driving:
        return False
    dx = g.x - float(ix)
    dy = g.y - float(iy)
    dist = math.hypot(dx, dy)
    horiz = abs(dx)
    r = max(2.5, float(radius))
    # Use the nearer of full distance / horizontal so high airbursts still shove
    use = min(dist, horiz) if dist > 0.01 else horiz
    if use > r:
        return False
    falloff = 1.0 - (use / r)
    push = (1.8 + 5.5 * falloff * falloff) * max(0.35, strength)
    if push < 0.6:
        return False
    direction = 1.0 if dx >= 0.0 else -1.0
    if abs(dx) < 0.4:
        direction = -1.0 if g.side == "L" else 1.0
    g.x = _clamp(g.x + direction * push, 5.0, WORLD_W - 6.0)
    g.home_x = g.x
    g.sit_on_ground(heights)
    return True


def acid_dissolve(heights, x, radius=ACID_RADIUS, depth=ACID_DEPTH, strength=1.0):
    """
    Dissolve earth under x and shift/settle the surface so hills collapse
    into the pit — opponent must re-calculate ballistics.
    """
    xi = int(round(x))
    r = int(max(2, radius))
    n = len(heights)
    lo, hi = VIEW_H * 0.35, VIEW_H - 2
    # Eat an irregular acidic pit (larger height = lower surface)
    for dx in range(-r, r + 1):
        px = xi + dx
        if not (0 <= px < n):
            continue
        fall = 1.0 - (abs(dx) / float(r))
        dig = depth * strength * (fall ** 1.15) * random.uniform(0.75, 1.2)
        heights[px] = int(_clamp(heights[px] + dig, lo, hi))
    # Collapse: taller ground (smaller y) shifts into deeper pockets
    for _ in range(3):
        nxt = heights[:]
        for px in range(1, n - 1):
            # Smooth settle
            nxt[px] = (
                0.18 * heights[px - 1]
                + 0.64 * heights[px]
                + 0.18 * heights[px + 1]
            )
        heights[:] = [int(round(_clamp(v, lo, hi))) for v in nxt]
    # Lateral shift: peaks slump toward valleys
    for px in range(2, n - 2):
        for d in (-1, 1):
            # If neighbor is higher ground (lower surface y), pull material in
            if heights[px] > heights[px + d] + 1.5:
                shift = 0.55 * strength
                heights[px] = int(_clamp(heights[px] - shift * 0.35, lo, hi))
                heights[px + d] = int(_clamp(heights[px + d] + shift, lo, hi))


def smooth_terrain(heights, passes=1):
    """Light blur so acid-shifted ground looks settled."""
    n = len(heights)
    lo, hi = VIEW_H * 0.35, VIEW_H - 2
    for _ in range(passes):
        nxt = heights[:]
        for px in range(1, n - 1):
            nxt[px] = 0.25 * heights[px - 1] + 0.5 * heights[px] + 0.25 * heights[px + 1]
        heights[:] = [int(round(_clamp(v, lo, hi))) for v in nxt]


# ---------------- Guns ----------------
class Gun(object):
    def __init__(self, side, x, heights, weapon=None):
        self.side = side          # "L" or "R"
        self.home_x = float(x)    # pad position
        self.x = float(x)
        self.y = surface_y(heights, x) - 1.0
        self.angle = 45.0 if side == "L" else 135.0  # degrees from +x
        self.power = 0.55         # 0..1 charge
        self.hp = HP_MAX_SHRAPNEL
        self.alive = True
        self.rgb = GUN_L_RGB if side == "L" else GUN_R_RGB
        self.flash = 0.0
        self.weapon = weapon or "standard"
        self.ammo = WEAPON_AMMO.get(self.weapon)  # None = unlimited
        self.driving = False
        self.drive_from = self.x
        self.drive_to = self.x
        self.drive_t = 0.0
        self.drive_dur = DRIVE_IN_SEC
        self.wheel_phase = 0.0
        self.explode_t = 0.0      # death explosion timer

    def sit_on_ground(self, heights):
        self.y = surface_y(heights, self.x) - 1.0

    def begin_drive(self, from_x, to_x, duration=None):
        self.driving = True
        self.drive_from = float(from_x)
        self.drive_to = float(to_x)
        self.drive_t = 0.0
        self.drive_dur = float(duration if duration is not None else DRIVE_IN_SEC)
        self.x = self.drive_from
        self.alive = True
        self.hp = HP_MAX_SHRAPNEL
        self.explode_t = 0.0

    def update_drive(self, dt, heights):
        if not self.driving:
            return False
        self.drive_t += dt
        u = _smooth(self.drive_t / max(0.05, self.drive_dur))
        self.x = _lerp(self.drive_from, self.drive_to, u)
        self.sit_on_ground(heights)
        self.wheel_phase += dt * 14.0
        # Bounce slightly while rolling
        self.y += math.sin(self.wheel_phase * 2.0) * 0.15 * (1.0 - u)
        if self.drive_t >= self.drive_dur:
            self.x = self.drive_to
            self.home_x = self.drive_to
            self.driving = False
            self.sit_on_ground(heights)
            return True  # arrived
        return False

    def muzzle(self):
        rad = math.radians(self.angle)
        return (
            self.x + math.cos(rad) * 3.2,
            self.y - math.sin(rad) * 3.2,
        )

    def start_death_explosion(self, sparks):
        """Big multi-wave blast when destroyed."""
        self.explode_t = DESTROY_FX_SEC
        self.alive = False
        self.hp = 0
        for _ in range(40):
            sparks.append(Spark(self.x, self.y, self.rgb))
        for _ in range(25):
            sparks.append(Spark(
                self.x, self.y,
                random.choice(((255, 200, 40), (255, 100, 20), (255, 255, 200), (120, 120, 120))),
            ))
        # Loft some debris high
        for _ in range(12):
            s = Spark(self.x, self.y, self.rgb)
            s.vy = -random.uniform(25, 55)
            s.vx = random.uniform(-30, 30)
            s.life = random.uniform(0.5, 1.1)
            sparks.append(s)

    def can_fire(self):
        if not self.alive:
            return False
        if self.ammo is None:
            return True
        return self.ammo > 0

    def consume_ammo(self):
        if self.ammo is not None and self.ammo > 0:
            self.ammo -= 1
            # Out of special ammo → fall back to standard
            if self.ammo <= 0 and self.weapon in (
                "heavy", "nuke", "sam", "acid", "mg30", "drone",
            ):
                print(f"[ArtilleryTime] {self.side} {self.weapon} ammo empty → standard")
                self.weapon = "standard"
                self.ammo = None


def assign_random_weapons(gun_l, gun_r):
    """Each artillery gets a random weapon for this war."""
    for g in (gun_l, gun_r):
        g.weapon = random.choice(WEAPONS)
        g.ammo = WEAPON_AMMO.get(g.weapon)
        print(f"[ArtilleryTime] {g.side} armed with {g.weapon}"
              + (f" x{g.ammo}" if g.ammo is not None else ""))


# ---------------- Ballistics AI ----------------
def simulate_shot(
    x0, y0, angle_deg, power, wind, heights, enemy_x, enemy_y,
    dt=1.0 / 40.0, record_path=False, weapon="standard",
):
    """
    Integrate projectile until ground / airburst / OOB.
    Returns (impact_x, impact_y, min_dist_to_enemy, frames[, path]).
    """
    # Drone swarm: straight-ish climb toward a hover point over the enemy
    if weapon == "drone":
        hx = enemy_x
        hy = max(3.0, enemy_y - 9.0)
        x, y = float(x0), float(y0)
        path = [(x, y)] if record_path else None
        best = math.hypot(x - enemy_x, y - enemy_y)
        for frame in range(120):
            dx = hx - x
            dy = hy - y
            dist = math.hypot(dx, dy) or 1.0
            step = DRONE_SPEED * dt
            if dist <= step:
                x, y = hx, hy
                if record_path:
                    path.append((x, y))
                best = min(best, math.hypot(x - enemy_x, y - enemy_y))
                if record_path:
                    return x, y, best, frame, path
                return x, y, best, frame
            x += (dx / dist) * step
            y += (dy / dist) * step
            if record_path and frame % 2 == 0:
                path.append((x, y))
            best = min(best, math.hypot(x - enemy_x, y - enemy_y))
        if record_path:
            return x, y, best, 120, path
        return x, y, best, 120

    rad = math.radians(angle_deg)
    speed = 8.0 + power * 42.0
    if weapon == "heavy":
        speed *= 0.92
    elif weapon == "nuke":
        speed *= 0.85
    elif weapon == "laser":
        speed = 90.0 + power * 40.0
    elif weapon == "sam":
        speed = 16.0 + power * 36.0
    elif weapon == "bouncer":
        speed *= 0.95
    elif weapon == "acid":
        speed *= 0.90
    elif weapon == "flame":
        speed *= 0.96
    elif weapon == "mg30":
        # High lofting 30mm — slightly slower horizontal, more hang time
        speed = 10.0 + power * 34.0
    vx = math.cos(rad) * speed
    vy = -math.sin(rad) * speed
    if weapon == "mg30":
        # Bias upward for high arc
        vy -= 6.0 + power * 8.0
    x, y = float(x0), float(y0)
    best = 1e9
    path = [(x, y)] if record_path else None
    bounces = 0
    aim_y = enemy_y - 8.0
    passed_apex = False

    for frame in range(500):
        if weapon == "laser":
            # No gravity; bounce off top of screen (bank shot)
            x += vx * dt
            y += vy * dt
            if y < 0.5:
                y = 0.5
                vy = abs(vy)
                bounces += 1
        elif weapon == "sam":
            # Guided surface-to-air: reduced gravity + steer over enemy
            dx = enemy_x - x
            dy = aim_y - y
            dist = math.hypot(dx, dy) or 1.0
            steer = 55.0
            vx += (dx / dist) * steer * dt
            vy += (dy / dist) * steer * dt
            # Cap speed
            spd = math.hypot(vx, vy)
            max_spd = 48.0
            if spd > max_spd:
                vx *= max_spd / spd
                vy *= max_spd / spd
            vx += wind * 1.2 * dt
            vy += GRAVITY * 0.35 * dt
            x += vx * dt
            y += vy * dt
            if y < 0.4:
                y = 0.4
                vy = abs(vy) * 0.4
        else:
            vx += wind * 3.2 * dt
            vy += GRAVITY * dt
            x += vx * dt
            y += vy * dt

        if record_path and frame % 2 == 0:
            path.append((x, y))
        d = math.hypot(x - enemy_x, y - enemy_y)
        if d < best:
            best = d

        if x < -4 or x > WORLD_W + 4 or y > VIEW_H + 4:
            if record_path:
                return x, y, best, frame, path
            return x, y, best, frame

        surf = surface_y(heights, x)
        left_home = abs(x - x0) > 10.0

        # Airburst / SAM: only fuse once horizontally over the enemy
        if weapon in ("airburst", "sam") and frame > 6 and left_home:
            over_x = SAM_OVER_X if weapon == "sam" else AIRBURST_OVER_X
            over_enemy = abs(x - enemy_x) <= over_x
            clear = SAM_AIR_CLEARANCE if weapon == "sam" else 3.5
            airborne = y < surf - clear and y < enemy_y - 1.5
            if over_enemy and airborne:
                if record_path:
                    path.append((x, y))
                    return x, y, best, frame, path
                return x, y, best, frame

        # MG30: open the bullet storm high over the enemy half
        if weapon == "mg30" and frame > 10:
            if vy > 0:
                passed_apex = True
            if (
                passed_apex
                and left_home
                and y < surf - 6
                and abs(x - enemy_x) < 22
            ):
                if record_path:
                    path.append((x, y))
                    return x, y, best, frame, path
                return x, y, best, frame

        if y >= surf - 0.3 and frame > 3:
            if weapon == "phosphorous" and bounces < 5:
                y = surf - 0.5
                vy = -abs(vy) * 0.72
                vx *= 0.88
                bounces += 1
                continue
            if weapon == "bouncer" and bounces < BOUNCE_BOMB_BOUNCES:
                y = surf - 0.55
                vy = -abs(vy) * 0.70 - 2.0
                vx *= 0.90
                bounces += 1
                continue
            if record_path:
                path.append((x, y))
                return x, y, best, frame, path
            return x, y, best, frame
    if record_path:
        return x, y, best, 500, path
    return x, y, best, 500


def ai_choose_shot(gun, enemy, wind, heights, power_bias=0.0):
    """
    Search angle/power for best predicted hit (weapon-aware).
    power_bias > 0 after short shots → prefer higher charge.
    """
    best = None
    best_score = 1e18
    weapon = gun.weapon
    bias = _clamp(float(power_bias), -0.25, 0.4)
    if gun.side == "L":
        if weapon == "laser":
            angles = range(15, 70, 2)   # lower bank angles
        elif weapon == "sam":
            angles = range(40, 82, 2)  # loft toward sky then enemy
        elif weapon == "mg30":
            angles = range(52, 84, 2)  # high arc for bullet storm
        else:
            angles = range(28, 78, 2)
    else:
        if weapon == "laser":
            angles = range(110, 165, 2)
        elif weapon == "sam":
            angles = range(98, 140, 2)
        elif weapon == "mg30":
            angles = range(96, 128, 2)
        else:
            angles = range(102, 152, 2)
    # After falling short, don't even consider weak charges
    p_lo = 25
    p_hi = 100
    if bias > 0.04:
        p_lo = min(82, 25 + int(bias * 120))
    elif bias < -0.04:
        # Long last time — prefer not maxing power again
        p_hi = max(p_lo + 15, 100 + int(bias * 90))
    for ang in angles:
        for p10 in range(p_lo, p_hi, 3):
            power = p10 / 100.0
            mx, my = gun.muzzle()
            ix, iy, mind, _fr = simulate_shot(
                mx, my, ang, power, wind, heights, enemy.x, enemy.y,
                weapon=weapon,
            )
            score = mind + abs(ix - enemy.x) * 0.15
            if weapon in ("airburst", "sam"):
                # Prefer detonation over enemy, still high
                score += abs(ix - enemy.x) * 0.45
                score += max(0, iy - (enemy.y - 5)) * 0.12
            if weapon == "laser":
                score += abs(iy - enemy.y) * 0.1
            if weapon == "bouncer":
                score += abs(ix - enemy.x) * 0.2
            if weapon == "acid":
                # Prefer dissolve under / near enemy pad
                score += abs(ix - enemy.x) * 0.25
            if weapon == "flame":
                score += abs(ix - enemy.x) * 0.2
            if weapon == "mg30":
                # Prefer opening the storm near enemy column, still high
                score += abs(ix - enemy.x) * 0.35
                score += max(0, iy - 8) * 0.05
            if weapon == "drone":
                # Always deploy toward enemy — angle barely matters
                score = abs(ix - enemy.x) * 0.1 + mind * 0.5
            # Bias: reward reaching / passing the enemy when we were short
            if bias > 0.02:
                if gun.side == "L":
                    short_err = max(0.0, enemy.x - ix)
                else:
                    short_err = max(0.0, ix - enemy.x)
                score += short_err * (0.25 + bias * 1.2)
                # Prefer stronger charges after short falls
                score += max(0.0, (0.5 + bias) - power) * 1.8
            elif bias < -0.02:
                if gun.side == "L":
                    long_err = max(0.0, ix - enemy.x)
                else:
                    long_err = max(0.0, enemy.x - ix)
                score += long_err * 0.2
            score += random.uniform(0, 0.35)
            if score < best_score:
                best_score = score
                best = (float(ang), power, mind)
    if best is None:
        return 45.0 if gun.side == "L" else 135.0, 0.6, 99.0
    ang, power, mind = best
    # Direct power nudge from learned short/long memory
    power = _clamp(power + bias * 0.85, 0.22, 1.0)
    return ang, power, mind


# ---------------- Shell / FX ----------------
class Shell(object):
    def __init__(self, x, y, vx, vy, owner, kind="standard",
                 target_x=None, target_y=None):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.alive = True
        self.trail = []          # [x, y, life]
        self.owner = owner
        self.kind = kind
        self.bounces = 0
        self.burn_t = 0.0        # phosphorous burn timer
        self.fuse_done = False
        self.effect_t = 0.0      # mushroom / lingering FX
        self.rgb = WEAPON_RGB.get(kind, SHELL_RGB)
        self.start_x = float(x)
        self.target_x = float(target_x if target_x is not None else x)
        self.target_y = float(target_y if target_y is not None else y)
        self.age = 0.0
        self.passed_apex = False

    def _age_trail(self, dt, rate=None):
        r = SHELL_TRAIL_FADE_RATE if rate is None else rate
        alive = []
        for p in self.trail:
            p[2] -= r * dt
            if p[2] > 0.02:
                alive.append(p)
        self.trail = alive

    def _over_enemy_fuse(self, heights):
        """True when shell is over the enemy and high enough to airburst."""
        surf = surface_y(heights, self.x)
        over_x = SAM_OVER_X if self.kind == "sam" else AIRBURST_OVER_X
        if abs(self.x - self.target_x) > over_x:
            return False
        if abs(self.x - self.start_x) < 10.0:
            return False
        clear = SAM_AIR_CLEARANCE if self.kind == "sam" else 3.5
        if self.y >= surf - clear:
            return False
        if self.y >= self.target_y - 1.5:
            return False
        return True

    def update(self, dt, wind, heights, sparks=None):
        """
        Returns status:
          fly | ground | oob | dead | airburst | sam_burst | burn |
          mushroom | mg_rain
        """
        self._age_trail(dt)
        if not self.alive:
            if self.kind == "phosphorous" and self.burn_t > 0:
                self.burn_t -= dt
                # Keep throwing sparks while burning
                if sparks is not None and random.random() < 0.55:
                    sparks.append(Spark(
                        self.x + random.uniform(-1, 1),
                        self.y + random.uniform(-1, 0),
                        random.choice(((255, 200, 40), (255, 120, 20), (200, 255, 80))),
                    ))
                if self.burn_t <= 0 and not self.trail:
                    return "dead"
                return "burn"
            if self.kind == "nuke" and self.effect_t > 0:
                self.effect_t -= dt
                return "mushroom" if self.effect_t > 0 else "dead"
            if self.kind == "mg30" and self.effect_t > 0:
                self.effect_t -= dt
                return "mg_rain" if self.effect_t > 0 else "dead"
            return "dead"

        self.age += dt
        self.trail.append([self.x, self.y, 1.0])
        max_trail = SHELL_TRAIL + (20 if self.kind == "laser" else 0)
        if self.kind == "sam":
            max_trail = SHELL_TRAIL + 10
        if self.kind == "mg30":
            max_trail = SHELL_TRAIL + 8
        if len(self.trail) > max_trail:
            self.trail.pop(0)

        if self.kind == "laser":
            # Fast beam, bank off top of screen
            steps = 3
            for _ in range(steps):
                self.x += self.vx * dt / steps
                self.y += self.vy * dt / steps
                if self.y < 0.4:
                    self.y = 0.4
                    self.vy = abs(self.vy)
                    self.bounces += 1
                self.trail.append([self.x, self.y, 1.0])
                if len(self.trail) > max_trail:
                    self.trail.pop(0)
        elif self.kind == "sam":
            # Surface-to-air: steer toward a point above the target
            aim_y = self.target_y - 8.0
            dx = self.target_x - self.x
            dy = aim_y - self.y
            dist = math.hypot(dx, dy) or 1.0
            steer = 55.0
            self.vx += (dx / dist) * steer * dt
            self.vy += (dy / dist) * steer * dt
            spd = math.hypot(self.vx, self.vy)
            max_spd = 48.0
            if spd > max_spd:
                self.vx *= max_spd / spd
                self.vy *= max_spd / spd
            self.vx += wind * 1.2 * dt
            self.vy += GRAVITY * 0.35 * dt
            self.x += self.vx * dt
            self.y += self.vy * dt
            if self.y < 0.4:
                self.y = 0.4
                self.vy = abs(self.vy) * 0.4
        else:
            self.vx += wind * 3.2 * dt
            self.vy += GRAVITY * dt
            self.x += self.vx * dt
            self.y += self.vy * dt

        if self.x < -6 or self.x > WORLD_W + 6 or self.y > VIEW_H + 6:
            self.alive = False
            self.trail.append([self.x, self.y, 1.0])
            return "oob"

        # Airburst / SAM: only detonate once over the enemy (not mid-flight)
        if self.kind in ("airburst", "sam") and not self.fuse_done and self.age > 0.12:
            if self._over_enemy_fuse(heights):
                self.alive = False
                self.fuse_done = True
                self.trail.append([self.x, self.y, 1.0])
                return "sam_burst" if self.kind == "sam" else "airburst"

        # MG30: after high apex, open bullet storm near enemy
        if self.kind == "mg30" and not self.fuse_done and self.age > 0.2:
            if self.vy > 0:
                self.passed_apex = True
            surf_chk = surface_y(heights, self.x)
            if (
                self.passed_apex
                and abs(self.x - self.start_x) > 10
                and self.y < surf_chk - 6
                and abs(self.x - self.target_x) < 22
            ):
                self.alive = False
                self.fuse_done = True
                self.effect_t = MG_RAIN_SEC
                self.trail.append([self.x, self.y, 1.0])
                return "mg_rain"

        surf = surface_y(heights, self.x)
        if self.y >= surf - 0.2:
            # Phosphorous: many hops then burn
            if self.kind == "phosphorous" and self.bounces < 6:
                self.y = surf - 0.6
                self.vy = -abs(self.vy) * 0.68 - random.uniform(0, 4)
                self.vx *= 0.85
                self.bounces += 1
                if sparks is not None:
                    for _ in range(4):
                        sparks.append(Spark(self.x, self.y, (255, 180, 40)))
                return "fly"
            # Bouncing bomb: exactly N bounces, then detonate
            if self.kind == "bouncer" and self.bounces < BOUNCE_BOMB_BOUNCES:
                self.y = surf - 0.55
                self.vy = -abs(self.vy) * 0.70 - random.uniform(1.5, 4.0)
                self.vx *= 0.90
                self.bounces += 1
                if sparks is not None:
                    for _ in range(3):
                        sparks.append(Spark(self.x, self.y, (255, 160, 50)))
                return "fly"
            self.alive = False
            self.trail.append([self.x, self.y, 1.0])
            if self.kind == "phosphorous":
                self.burn_t = PHOS_BURN_SEC
                return "burn"
            if self.kind == "nuke":
                self.effect_t = MUSHROOM_SEC
                return "mushroom"
            # Airburst/SAM that hit dirt without fusing still go boom
            if self.kind == "airburst":
                self.fuse_done = True
                return "airburst"
            if self.kind == "sam":
                self.fuse_done = True
                return "sam_burst"
            if self.kind == "mg30":
                self.fuse_done = True
                self.effect_t = MG_RAIN_SEC
                return "mg_rain"
            return "ground"
        return "fly"


class RainBullet(object):
    """Single 30mm round in an MG storm."""
    __slots__ = ("x", "y", "vx", "vy", "owner", "alive", "hit")

    def __init__(self, x, y, owner, aim_x=None):
        self.x = float(x) + random.uniform(-1.5, 1.5)
        self.y = float(y) + random.uniform(-1.0, 1.0)
        # Fall mostly down with scatter toward aim
        self.vx = random.uniform(-10, 10)
        if aim_x is not None:
            self.vx += _clamp((aim_x - self.x) * 0.35, -14, 14)
        self.vy = random.uniform(8, 22)
        self.owner = owner
        self.alive = True
        self.hit = False

    def update(self, dt, wind, heights):
        if not self.alive:
            return "dead"
        self.vx += wind * 1.5 * dt
        self.vy += GRAVITY * 1.15 * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.x < -4 or self.x > WORLD_W + 4 or self.y > VIEW_H + 4:
            self.alive = False
            return "oob"
        surf = surface_y(heights, self.x)
        if self.y >= surf - 0.15:
            self.y = surf - 0.15
            self.alive = False
            self.hit = True
            return "ground"
        return "fly"


class GroundFX(object):
    """Lingering ground effect: acid dissolve or surface flame burst."""
    __slots__ = ("kind", "x", "life", "max_life", "reach", "tick", "owner")

    def __init__(self, kind, x, life, owner=None):
        self.kind = kind          # "acid" | "flame"
        self.x = float(x)
        self.life = float(life)
        self.max_life = float(life)
        self.reach = 0.0
        self.tick = 0.0
        self.owner = owner

    def update(self, dt, heights, sparks=None):
        self.life -= dt
        self.tick += dt
        if self.kind == "acid":
            # Keep dissolving / shifting ground while active
            if self.tick >= 0.22:
                self.tick = 0.0
                acid_dissolve(
                    heights, self.x,
                    radius=int(ACID_RADIUS * (0.55 + 0.45 * (self.life / self.max_life))),
                    depth=max(1, int(ACID_DEPTH * 0.35)),
                    strength=0.45,
                )
                if sparks is not None:
                    for _ in range(3):
                        sparks.append(Spark(
                            self.x + random.uniform(-ACID_RADIUS * 0.6, ACID_RADIUS * 0.6),
                            surface_y(heights, self.x) - random.uniform(0, 2),
                            random.choice(((60, 255, 40), (120, 255, 80), (40, 180, 30))),
                        ))
        elif self.kind == "flame":
            # Flames race outward along the surface
            self.reach = min(
                FLAME_MAX_REACH,
                self.reach + dt * (FLAME_MAX_REACH / max(0.35, FLAME_BURST_SEC * 0.55)),
            )
            if sparks is not None and random.random() < 0.7:
                dx = random.uniform(-self.reach, self.reach)
                fx = self.x + dx
                sparks.append(Spark(
                    fx,
                    surface_y(heights, fx) - random.uniform(0, 1.5),
                    random.choice(((255, 80, 10), (255, 160, 20), (255, 220, 40), (200, 40, 10))),
                ))
        return self.life > 0


class Drone(object):
    """
    Single-pixel interceptor drone.
    Flies from the cannon, hovers over the enemy, swats incoming shells,
    then dumps into an electric storm.
    """
    __slots__ = (
        "x", "y", "owner", "state", "hx", "hy", "ox", "oy",
        "delay", "hover_t", "phase", "alive",
    )

    def __init__(self, x, y, owner, hover_x, hover_y, delay=0.0):
        self.x = float(x)
        self.y = float(y)
        self.owner = owner
        self.state = "fly"       # fly | hover | dead
        self.ox = random.uniform(-5.5, 5.5)
        self.oy = random.uniform(-2.0, 1.5)
        self.hx = float(hover_x) + self.ox
        self.hy = float(hover_y) + self.oy
        self.delay = float(delay)
        self.hover_t = 0.0
        self.phase = random.uniform(0, math.tau)
        self.alive = True

    def update(self, dt, enemy_x, enemy_y):
        if not self.alive or self.state == "dead":
            return
        if self.delay > 0:
            self.delay -= dt
            return
        # Hover point tracks enemy pad
        self.hx = enemy_x + self.ox
        self.hy = max(2.5, enemy_y - 8.5 + self.oy)
        if self.state == "fly":
            dx = self.hx - self.x
            dy = self.hy - self.y
            dist = math.hypot(dx, dy) or 1.0
            step = DRONE_SPEED * dt
            if dist <= step + 0.8:
                self.x = self.hx
                self.y = self.hy
                self.state = "hover"
                self.hover_t = 0.0
            else:
                self.x += (dx / dist) * step
                self.y += (dy / dist) * step
        elif self.state == "hover":
            self.hover_t += dt
            self.phase += dt * 5.5
            # Soft track + bob
            self.x = _lerp(self.x, self.hx, min(1.0, 4.0 * dt))
            self.y = _lerp(self.y, self.hy, min(1.0, 4.0 * dt))
            self.y += math.sin(self.phase) * 0.12


class ElectricStorm(object):
    """Short cyan lightning storm over a world point."""
    __slots__ = ("x", "y", "life", "max_life", "bolts", "tick")

    def __init__(self, x, y, life=DRONE_STORM_SEC):
        self.x = float(x)
        self.y = float(y)
        self.life = float(life)
        self.max_life = float(life)
        self.bolts = []  # list of [(x,y), ...] polylines in world space
        self.tick = 0.0
        self._regen_bolts()

    def _regen_bolts(self):
        self.bolts = []
        for _ in range(random.randint(3, 6)):
            x0 = self.x + random.uniform(-8, 8)
            y0 = self.y + random.uniform(-4, 1)
            pts = [(x0, y0)]
            x, y = x0, y0
            for _seg in range(random.randint(3, 6)):
                x += random.uniform(-2.5, 2.5)
                y += random.uniform(1.2, 3.2)
                pts.append((x, y))
            self.bolts.append(pts)

    def update(self, dt, sparks=None):
        self.life -= dt
        self.tick += dt
        if self.tick >= 0.08:
            self.tick = 0.0
            self._regen_bolts()
            if sparks is not None and random.random() < 0.7:
                sparks.append(Spark(
                    self.x + random.uniform(-6, 6),
                    self.y + random.uniform(-2, 4),
                    random.choice(((120, 220, 255), (200, 240, 255), (80, 160, 255))),
                ))
        return self.life > 0


class Spark(object):
    __slots__ = ("x", "y", "vx", "vy", "life", "rgb")

    def __init__(self, x, y, rgb=None):
        ang = random.uniform(0, math.tau)
        spd = random.uniform(8, 40)
        self.x = x
        self.y = y
        self.vx = math.cos(ang) * spd
        self.vy = math.sin(ang) * spd - random.uniform(5, 20)
        self.life = random.uniform(0.25, 0.7)
        self.rgb = rgb or random.choice(
            ((255, 200, 40), (255, 100, 20), (255, 255, 200), (180, 180, 180))
        )

    def update(self, dt):
        self.vy += GRAVITY * 0.6 * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt


# ---------------- Camera ----------------
def camera_follow(target_x, cam_x, view_w=VIEW_W, world_w=WORLD_W, snap=False):
    desired = target_x - view_w * 0.5
    desired = _clamp(desired, 0, max(0, world_w - view_w))
    if snap:
        return desired
    return _lerp(cam_x, desired, 0.12)


# ---------------- Top 7-seg red clock (screen space) ----------------
def _seg_clock_width():
    return 4 * SEG_DIGIT_W + 3 * SEG_GAP + SEG_COLON_W


def _draw_7seg_digit(canvas, ox, oy, digit, lit_rgb, dim_rgb, width, height):
    """One 5×9 7-element digit (pinball / SevenSegClock layout)."""
    w, h, t = SEG_DIGIT_W, SEG_DIGIT_H, SEG_THICK
    mid = h // 2
    hx0, hx1 = t, w - 1 - t
    vy0_top, vy1_top = t, mid - 1
    vy0_bot, vy1_bot = mid + t, h - 1 - t
    mask = _SEG_DIGIT_MASKS[int(digit) % 10]
    segs = (
        (_SEG_A, "h", hx0, hx1, 0),
        (_SEG_G, "h", hx0, hx1, mid),
        (_SEG_D, "h", hx0, hx1, h - t),
        (_SEG_F, "v", 0, vy0_top, vy1_top),
        (_SEG_B, "v", w - t, vy0_top, vy1_top),
        (_SEG_E, "v", 0, vy0_bot, vy1_bot),
        (_SEG_C, "v", w - t, vy0_bot, vy1_bot),
    )
    set_px = canvas.SetPixel
    for bit, kind, a, b, c in segs:
        on = (mask & bit) != 0
        rgb = lit_rgb if on else dim_rgb
        if rgb is None:
            continue
        if kind == "h":
            for yy in range(c, c + t):
                for xx in range(a, b + 1):
                    px, py = ox + xx, oy + yy
                    if 0 <= px < width and 0 <= py < height:
                        set_px(px, py, *rgb)
        else:
            for xx in range(a, a + t):
                for yy in range(b, c + 1):
                    px, py = ox + xx, oy + yy
                    if 0 <= px < width and 0 <= py < height:
                        set_px(px, py, *rgb)


def _scale_rgb(rgb, a):
    a = _clamp(float(a), 0.0, 1.0)
    if a <= 0.0:
        return None
    return (
        min(255, int(rgb[0] * a)),
        min(255, int(rgb[1] * a)),
        min(255, int(rgb[2] * a)),
    )


def _draw_top_7seg_clock(canvas, width, height, alpha=1.0):
    """HH:MM red 7-seg clock, top-center on a dark plate.
    alpha 0=hidden → 1=full (callers ramp this for fade in/out).
    Daytime uses a hotter red for blue sky; boost scales with alpha so
    fades stay smooth.
    """
    # Ease curve so fade in/out feels soft, not linear
    t = _clamp(float(alpha), 0.0, 1.0)
    if t < 0.01:
        return
    a = _smooth(t)
    day = sky_is_day()
    if day:
        # Hotter palette; multiply only (no floor) so fade can reach zero
        a_draw = min(1.0, a * 1.28)
        base_lit, base_dim = SEG_CLOCK_RGB_DAY, SEG_CLOCK_DIM_DAY
    else:
        a_draw = a
        base_lit, base_dim = SEG_CLOCK_RGB, SEG_CLOCK_DIM
    lit = _scale_rgb(base_lit, a_draw)
    dim = _scale_rgb(base_dim, a_draw)
    if lit is None:
        return
    # Day core only once mostly faded in (keeps early fade soft)
    lit_core = None
    if day and a_draw > 0.55:
        k = (a_draw - 0.55) / 0.45
        lit_core = (
            min(255, int(lit[0] + 40 * k)),
            min(255, int(lit[1] + 55 * k)),
            min(255, int(lit[2] + 30 * k)),
        )
    now = datetime.now()
    hh = now.hour
    mm = now.minute
    digits = (hh // 10, hh % 10, mm // 10, mm % 10)
    total_w = _seg_clock_width()
    ox = (width - total_w) // 2
    oy = 1
    set_px = canvas.SetPixel

    # Dark plate behind the digits — opacity tracks fade
    pad_x, pad_y = 1, 1
    bx0 = max(0, ox - pad_x)
    by0 = max(0, oy - pad_y)
    bx1 = min(width - 1, ox + total_w + pad_x - 1)
    by1 = min(height - 1, oy + SEG_DIGIT_H + pad_y - 1)
    # Near-black plate; at low alpha almost invisible so sky shows through feel
    plate = (
        min(255, int(6 * a_draw)),
        min(255, int(3 * a_draw)),
        min(255, int(3 * a_draw)),
    )
    for py in range(by0, by1 + 1):
        for px in range(bx0, bx1 + 1):
            set_px(px, py, *plate)

    x = ox
    colon = lit_core or lit
    _draw_7seg_digit(canvas, x, oy, digits[0], colon, dim, width, height)
    x += SEG_DIGIT_W + SEG_GAP
    _draw_7seg_digit(canvas, x, oy, digits[1], colon, dim, width, height)
    x += SEG_DIGIT_W + SEG_GAP
    # Colon
    mid = SEG_DIGIT_H // 2
    for cy in (mid - 2, mid + 1):
        for xx in range(SEG_COLON_W):
            for yy in range(SEG_THICK):
                px, py = x + xx, oy + cy + yy
                if 0 <= px < width and 0 <= py < height:
                    set_px(px, py, *colon)
    x += SEG_COLON_W + SEG_GAP
    _draw_7seg_digit(canvas, x, oy, digits[2], colon, dim, width, height)
    x += SEG_DIGIT_W + SEG_GAP
    _draw_7seg_digit(canvas, x, oy, digits[3], colon, dim, width, height)


# ---------------- Main game ----------------
def PlayArtilleryTime(Duration=10, StopEvent=None):
    """
    Duration in minutes. Best-of-3 artillery wars until time expires.
    Duration <= 0 means run forever (standalone / no time limit).
    """
    global VIEW_W, VIEW_H
    VIEW_W = int(getattr(LED, "HatWidth", 64) or 64)
    VIEW_H = int(getattr(LED, "HatHeight", 32) or 32)

    try:
        canvas = LED.TheMatrix.CreateFrameCanvas()
    except Exception:
        canvas = LED.Canvas

    try:
        run_min = float(Duration)
    except (TypeError, ValueError):
        run_min = 10.0
    # <= 0 → unlimited (used by standalone)
    forever = run_min <= 0

    tick = pygame.time.Clock() if HAS_PYGAME else None
    start = time.time()
    dt = 1.0 / TARGET_FPS

    # Match state
    score = {"L": 0, "R": 0}
    war = 1
    phase = "war_start"
    # war_start | think | charge | flight | impact | destroy_fx | drive_in |
    # victory_drive | victory_fx | round_end | war_end
    phase_t = 0.0
    turn = "L"
    wind = 0.0
    shell = None
    sparks = []
    ground_fx = []            # acid pools / surface flame bursts
    rain_bullets = []         # 30mm storm
    drones = []               # interceptor drones (persist across turns)
    storms = []               # electric storm FX
    cam_x = 0.0
    last_impact = None
    hit_kind = None           # "direct" | "shrapnel" | "miss"
    pending_angle = 45.0
    pending_power = 0.5
    charge_show = 0.0
    aim_preview = []
    # Per-side aim learning: raise power after short shots, ease off after longs
    power_bias = {"L": 0.0, "R": 0.0}
    last_shot = {"owner": None, "kind": None, "enemy_x": None}
    killed_side = None
    round_winner = None
    victory_side = None
    you_win_scale = 0.0
    # 7-seg clock visibility: full at war/round start & end; fades during combat
    # Start hidden so the first war_start fades the clock in
    clock_alpha = 0.0
    CLOCK_FADE_IN_SEC = 1.05   # seconds 0 → full
    CLOCK_FADE_OUT_SEC = 0.90  # seconds full → 0

    heights = generate_terrain(WORLD_W, VIEW_H)
    gun_l = Gun("L", 10, heights)
    gun_r = Gun("R", WORLD_W - 11, heights)
    guns = {"L": gun_l, "R": gun_r}
    # War loadout — each side gets a random weapon for this war
    assign_random_weapons(gun_l, gun_r)
    war_weapons = {"L": gun_l.weapon, "R": gun_r.weapon}
    war_ammo = {"L": gun_l.ammo, "R": gun_r.ammo}

    def _restore_weapons_on_guns():
        """Keep war weapons when a new round regenerates gun objects."""
        for side, g in guns.items():
            g.weapon = war_weapons.get(side, "standard")
            # Preserve remaining ammo across rounds within a war
            if side in war_ammo:
                g.ammo = war_ammo[side]
            else:
                g.ammo = WEAPON_AMMO.get(g.weapon)

    def _reset_round(new_war=False):
        nonlocal heights, gun_l, gun_r, guns, shell, sparks, wind, turn
        nonlocal phase, phase_t, hit_kind, last_impact, aim_preview, charge_show
        nonlocal war_weapons, war_ammo, ground_fx, rain_bullets, drones, storms
        nonlocal power_bias
        heights = generate_terrain(WORLD_W, VIEW_H)
        gun_l = Gun("L", 10, heights)
        gun_r = Gun("R", WORLD_W - 11, heights)
        guns = {"L": gun_l, "R": gun_r}
        if new_war:
            assign_random_weapons(gun_l, gun_r)
            war_weapons = {"L": gun_l.weapon, "R": gun_r.weapon}
            war_ammo = {"L": gun_l.ammo, "R": gun_r.ammo}
            power_bias = {"L": 0.0, "R": 0.0}
        else:
            _restore_weapons_on_guns()
        shell = None
        sparks = []
        ground_fx = []
        rain_bullets = []
        drones = []
        storms = []
        last_shot["owner"] = None
        last_shot["kind"] = None
        wind = random.uniform(WIND_MIN, WIND_MAX)
        turn = random.choice(("L", "R"))
        phase = "think"
        phase_t = 0.0
        hit_kind = None
        last_impact = None
        aim_preview = []
        charge_show = 0.0
        gun_l.sit_on_ground(heights)
        gun_r.sit_on_ground(heights)

    def _spawn_mg_rain(cx, cy, owner, aim_x):
        """Open a high-arc 30mm bullet storm centered near (cx, cy)."""
        nonlocal rain_bullets, last_impact
        last_impact = (cx, cy)
        n = MG30_BULLETS + random.randint(-4, 6)
        for i in range(n):
            # Stagger spawn positions in a cloud above the target column
            bx = cx + random.uniform(-14, 14) + (aim_x - cx) * 0.15
            by = cy + random.uniform(-3, 5)
            rain_bullets.append(RainBullet(bx, by, owner, aim_x=aim_x))
        print(f"[ArtilleryTime] MG30 storm x{n} over ~{cx:.0f}")

    def _update_ground_fx(dt):
        """Advance acid/flame ground effects; re-seat guns after acid shifts."""
        nonlocal ground_fx
        if not ground_fx:
            return
        alive = []
        acid_moved = False
        for fx in ground_fx:
            if fx.update(dt, heights, sparks=sparks):
                alive.append(fx)
                if fx.kind == "acid":
                    acid_moved = True
            elif fx.kind == "acid":
                acid_moved = True
        ground_fx = alive
        if acid_moved:
            for g in guns.values():
                if g.alive:
                    g.sit_on_ground(heights)

    def _update_rain_bullets(dt):
        """Falling 30mm rounds — damage guns on near hit / ground splash."""
        nonlocal rain_bullets, hit_kind, killed_side
        if not rain_bullets:
            return
        alive = []
        for b in rain_bullets:
            st = b.update(dt, wind, heights)
            if st == "fly":
                # Direct hit while falling
                for side, g in guns.items():
                    if not g.alive or side == b.owner:
                        continue
                    if math.hypot(b.x - g.x, b.y - g.y) <= 1.35:
                        b.alive = False
                        b.hit = True
                        g.hp -= 1
                        hit_kind = "shrapnel" if hit_kind in (None, "miss") else hit_kind
                        sparks.append(Spark(b.x, b.y, (255, 220, 120)))
                        print(f"[ArtilleryTime] MG30 hit {side} hp={g.hp}")
                        if g.hp <= 0:
                            g.start_death_explosion(sparks)
                            killed_side = side
                            hit_kind = "direct"
                            print(f"[ArtilleryTime] {side} destroyed by MG30")
                            _check_round_over()
                        break
                if b.alive:
                    alive.append(b)
            elif st == "ground" and b.hit:
                # Every round scars the dirt; close hits shove the piece
                crater(heights, b.x, radius=2, depth=1)
                for side, g in guns.items():
                    if not g.alive or side == b.owner:
                        continue
                    if blast_push_gun(g, heights, b.x, b.y, radius=4.5, strength=0.45):
                        print(f"[ArtilleryTime] MG30 blast shoved {side} → x={g.x:.1f}")
                    if abs(b.x - g.x) <= 2.8 and abs(b.y - g.y) <= 3.5:
                        g.hp -= 1
                        hit_kind = "shrapnel" if hit_kind in (None, "miss") else hit_kind
                        sparks.append(Spark(g.x, g.y, (255, 200, 80)))
                        print(f"[ArtilleryTime] MG30 splash {side} hp={g.hp}")
                        if g.hp <= 0:
                            g.start_death_explosion(sparks)
                            killed_side = side
                            print(f"[ArtilleryTime] {side} destroyed by MG30 splash")
                            _check_round_over()
                    g.sit_on_ground(heights)
                if random.random() < 0.25:
                    sparks.append(Spark(b.x, b.y, (200, 200, 160)))
        rain_bullets = alive

    def _flame_damage_tick():
        """Flames spreading on the ground burn any gun in the fire line."""
        nonlocal hit_kind, killed_side
        for fx in ground_fx:
            if fx.kind != "flame" or fx.reach < 1.0:
                continue
            for side, g in guns.items():
                if not g.alive:
                    continue
                if abs(g.x - fx.x) <= fx.reach + 0.5:
                    # Occasional burn tick
                    if random.random() < 0.04:
                        g.hp -= 1
                        hit_kind = "shrapnel" if hit_kind in (None, "miss") else hit_kind
                        sparks.append(Spark(g.x, g.y - 1, (255, 100, 20)))
                        print(f"[ArtilleryTime] Flame burn {side} hp={g.hp}")
                        if g.hp <= 0:
                            g.start_death_explosion(sparks)
                            killed_side = side
                            print(f"[ArtilleryTime] {side} destroyed by flame")
                            _check_round_over()

    def _learn_from_shot(owner, impact_x, enemy_x, result="miss"):
        """Adjust power_bias when a shell lands short (or long) of the enemy."""
        nonlocal power_bias
        if owner not in ("L", "R"):
            return
        if result in ("direct", "shrapnel"):
            # Close enough — decay learned bias
            power_bias[owner] *= 0.45
            return
        # Sign: negative delta = fell short of enemy column
        if owner == "L":
            delta = float(impact_x) - float(enemy_x)
        else:
            delta = float(enemy_x) - float(impact_x)
        if delta < -2.5:
            short_by = -delta
            boost = _clamp(0.06 + short_by * 0.012, 0.06, 0.28)
            power_bias[owner] = _clamp(power_bias[owner] + boost, -0.2, 0.42)
            print(
                f"[ArtilleryTime] {owner} SHORT by {short_by:.1f}px "
                f"→ power bias {power_bias[owner]:+.2f}"
            )
        elif delta > 6.0:
            power_bias[owner] = _clamp(power_bias[owner] - 0.08, -0.2, 0.42)
            print(
                f"[ArtilleryTime] {owner} LONG by {delta:.1f}px "
                f"→ power bias {power_bias[owner]:+.2f}"
            )
        else:
            power_bias[owner] *= 0.75

    def _record_shot_outcome(impact_x=None, result=None):
        """Apply learning for the shell that just resolved."""
        owner = last_shot.get("owner")
        kind = last_shot.get("kind")
        if owner is None or kind in (None, "drone"):
            return
        ix = impact_x
        if ix is None and last_impact is not None:
            ix = last_impact[0]
        if ix is None:
            return
        enemy_x = last_shot.get("enemy_x")
        if enemy_x is None:
            foe = guns.get("R" if owner == "L" else "L")
            enemy_x = foe.x if foe else WORLD_W * 0.5
        res = result if result is not None else (hit_kind or "miss")
        _learn_from_shot(owner, ix, enemy_x, result=res)
        last_shot["owner"] = None
        last_shot["kind"] = None

    def _start_think():
        nonlocal phase, phase_t, pending_angle, pending_power, aim_preview, wind
        active = guns[turn]
        enemy = guns["R" if turn == "L" else "L"]
        if not active.alive or not enemy.alive:
            return
        if not active.can_fire():
            active.weapon = "standard"
            active.ammo = None
        wind = _clamp(wind + random.uniform(-1.2, 1.2), WIND_MIN, WIND_MAX)
        bias = power_bias.get(turn, 0.0)
        ang, power, mind = ai_choose_shot(
            active, enemy, wind, heights, power_bias=bias,
        )
        pending_angle = ang
        pending_power = power
        active.angle = ang
        active.power = power
        mx, my = active.muzzle()
        _ix, _iy, _mind, _fr, path = simulate_shot(
            mx, my, ang, power, wind, heights, enemy.x, enemy.y,
            record_path=True, weapon=active.weapon,
        )
        aim_preview = path or []
        phase = "think"
        phase_t = 0.0
        bias_s = f"  bias={bias:+.2f}" if abs(bias) > 0.02 else ""
        print(
            f"[ArtilleryTime] {turn}/{active.weapon} aims  ang={ang:.0f}°  "
            f"pwr={power:.2f}  wind={wind:+.1f}  pred~{mind:.1f}px{bias_s}"
        )

    def _spawn_drones(owner_gun, enemy_gun):
        """Launch single-pixel drones from the muzzle toward the enemy sky."""
        nonlocal drones, last_impact
        mx, my = owner_gun.muzzle()
        # Clear any prior swarm from this side (new deploy replaces)
        drones = [d for d in drones if d.owner != owner_gun.side and d.alive]
        n = DRONE_COUNT
        for i in range(n):
            hx = enemy_gun.x
            hy = max(3.0, enemy_gun.y - 9.0)
            drones.append(Drone(
                mx + random.uniform(-0.4, 0.4),
                my + random.uniform(-0.4, 0.4),
                owner_gun.side,
                hx, hy,
                delay=i * 0.07,
            ))
        last_impact = (enemy_gun.x, enemy_gun.y - 8)
        print(f"[ArtilleryTime] {owner_gun.side} deploys {n} drones")

    def _update_drones(dt):
        """Fly / hover all live drones; track their assigned enemy."""
        if not drones:
            return
        for d in drones:
            if not d.alive:
                continue
            foe = guns.get("R" if d.owner == "L" else "L")
            if foe is None:
                continue
            # Track pad even if wrecked so hover still makes sense
            d.update(dt, foe.x, foe.y)

    def _trigger_drone_storm(owner, reason="timeout"):
        """Drones dump into an electric storm over the enemy."""
        nonlocal drones, storms, last_impact, phase, phase_t
        swarm = [d for d in drones if d.owner == owner and d.alive]
        if not swarm:
            return
        foe = guns.get("R" if owner == "L" else "L")
        cx = sum(d.x for d in swarm) / len(swarm)
        cy = sum(d.y for d in swarm) / len(swarm)
        if foe is not None:
            cx = _lerp(cx, foe.x, 0.55)
            cy = _lerp(cy, max(3.0, foe.y - 6.0), 0.4)
        last_impact = (cx, cy)
        # Pop drones into sparks
        for d in swarm:
            d.alive = False
            d.state = "dead"
            sparks.append(Spark(d.x, d.y, (100, 230, 255)))
            sparks.append(Spark(d.x, d.y, (200, 240, 255)))
        drones[:] = [d for d in drones if d.alive]
        storms.append(ElectricStorm(cx, cy, DRONE_STORM_SEC))
        print(f"[ArtilleryTime] Drone electric storm ({reason}) by {owner} @ {cx:.0f}")
        # Big electric damage over the enemy
        for _ in range(14):
            sparks.append(Spark(
                cx + random.uniform(-7, 7),
                cy + random.uniform(-3, 5),
                random.choice(((100, 220, 255), (180, 240, 255), (60, 140, 255))),
            ))
        # learn=False: storm is not the live shell's landing
        _damage_at(
            cx, cy if foe is None else foe.y - 2,
            direct_r=3.2, shrap_r=11.0,
            crater_r=2, crater_d=1, n_sparks=30, kind_label="drone-storm",
            learn=False,
        )
        # Never freeze a live shell in impact — stay in flight so it can finish
        if phase in ("destroy_fx", "round_end", "victory_drive", "victory_fx"):
            return
        if shell is not None and shell.alive:
            return
        if phase != "impact":
            phase = "impact"
            phase_t = 0.0

    def _try_drone_intercept():
        """
        Hovering enemy drones swat the live shell / rain bullets.
        On intercept → electric storm from that swarm.
        Returns True if the shell was killed.
        """
        nonlocal shell, hit_kind, rain_bullets
        shell_killed = False
        if shell is not None and shell.alive:
            for d in drones:
                if not d.alive or d.state != "hover":
                    continue
                if d.owner == shell.owner:
                    continue
                if math.hypot(d.x - shell.x, d.y - shell.y) <= DRONE_INTERCEPT_R:
                    shell.alive = False
                    shell.trail.append([shell.x, shell.y, 1.0])
                    shell._detonated = True  # no ground boom
                    shell_killed = True
                    hit_kind = "miss"
                    for _ in range(8):
                        sparks.append(Spark(
                            shell.x, shell.y,
                            random.choice(((100, 230, 255), (255, 255, 200), (80, 180, 255))),
                        ))
                    print(f"[ArtilleryTime] Drone intercept! shell from {shell.owner}")
                    _trigger_drone_storm(d.owner, reason="intercept")
                    break
        # Also swat MG rain belonging to the other side
        if rain_bullets:
            kept = []
            for b in rain_bullets:
                swatted = False
                if b.alive:
                    for d in drones:
                        if not d.alive or d.state != "hover" or d.owner == b.owner:
                            continue
                        if math.hypot(d.x - b.x, d.y - b.y) <= DRONE_INTERCEPT_R:
                            b.alive = False
                            swatted = True
                            sparks.append(Spark(b.x, b.y, (100, 230, 255)))
                            print("[ArtilleryTime] Drone swatted MG round")
                            _trigger_drone_storm(d.owner, reason="intercept-mg")
                            break
                if b.alive and not swatted:
                    kept.append(b)
            rain_bullets = kept
        return shell_killed

    def _drone_timeout_storms(dt):
        """If a swarm has hovered long enough without intercept, storm anyway."""
        owners_hover = {}
        for d in drones:
            if d.alive and d.state == "hover":
                owners_hover.setdefault(d.owner, []).append(d)
        for owner, swarm in owners_hover.items():
            # Use max hover time in the swarm
            ht = max(d.hover_t for d in swarm)
            if ht >= DRONE_HOVER_MAX:
                _trigger_drone_storm(owner, reason="timeout")

    def _update_storms(dt):
        nonlocal storms
        if not storms:
            return
        alive = []
        for st in storms:
            if st.update(dt, sparks=sparks):
                alive.append(st)
        storms = alive

    def _fire():
        nonlocal shell, phase, phase_t, war_ammo
        active = guns[turn]
        enemy = guns["R" if turn == "L" else "L"]
        mx, my = active.muzzle()
        rad = math.radians(active.angle)
        kind = active.weapon
        last_shot["owner"] = turn
        last_shot["kind"] = kind
        last_shot["enemy_x"] = enemy.x if enemy else WORLD_W * 0.5
        if kind == "drone":
            # Swarm launch — no ballistic shell
            shell = None
            _spawn_drones(active, enemy)
            active.flash = 0.3
            active.consume_ammo()
            war_ammo[turn] = active.ammo
            phase = "flight"
            phase_t = 0.0
            print(f"[ArtilleryTime] {turn} FIRE drone!")
            return
        speed = 8.0 + active.power * 42.0
        if kind == "heavy":
            speed *= 0.92
        elif kind == "nuke":
            speed *= 0.85
        elif kind == "laser":
            speed = 90.0 + active.power * 40.0
        elif kind == "sam":
            speed = 16.0 + active.power * 36.0
        elif kind == "bouncer":
            speed *= 0.95
        elif kind == "acid":
            speed *= 0.90
        elif kind == "flame":
            speed *= 0.96
        elif kind == "mg30":
            speed = 10.0 + active.power * 34.0
        vx = math.cos(rad) * speed
        vy = -math.sin(rad) * speed
        if kind == "mg30":
            vy -= 6.0 + active.power * 8.0
        shell = Shell(
            mx, my, vx, vy, turn, kind=kind,
            target_x=enemy.x, target_y=enemy.y,
        )
        active.flash = 0.25
        active.consume_ammo()
        war_ammo[turn] = active.ammo
        phase = "flight"
        phase_t = 0.0
        print(f"[ArtilleryTime] {turn} FIRE {kind}!")

    def _damage_at(
        ix, iy, direct_r, shrap_r, crater_r, crater_d, n_sparks,
        kind_label="HE", learn=True,
    ):
        """
        Apply blast at (ix,iy): always scar the ground, shove nearby guns,
        then HP / kill checks. Returns True if round ended.
        learn=False skips short/long power memory (e.g. drone storms).
        """
        nonlocal hit_kind, last_impact, phase, phase_t, score, killed_side
        last_impact = (ix, iy)

        # Every hit damages the ground — at least a small pock if weapon
        # passed crater_r=0 (e.g. acid already dissolved, still add scar).
        cr = int(crater_r)
        cd = int(crater_d)
        if cr <= 0:
            cr = max(2, int(round(1.2 + shrap_r * 0.22)))
        if cd <= 0:
            cd = max(1, int(round(1 + shrap_r * 0.1)))
        crater(heights, ix, radius=cr, depth=cd)

        # Blast shove: pieces close to the impact are moved by the force
        push_r = max(float(shrap_r) + 1.5, float(cr) + 2.5, 5.5)
        push_str = 0.55 + cd * 0.18 + cr * 0.07
        for side, g in guns.items():
            if not g.alive:
                continue
            if blast_push_gun(g, heights, ix, iy, push_r, strength=push_str):
                print(
                    f"[ArtilleryTime] Blast shoved {side} "
                    f"→ x={g.x:.1f} ({kind_label})"
                )
                for _ in range(3):
                    sparks.append(Spark(g.x, g.y, (160, 140, 100)))

        hit_kind = "miss"
        for side, g in guns.items():
            if not g.alive:
                continue
            d = math.hypot(ix - g.x, iy - g.y)
            if d <= direct_r:
                hit_kind = "direct"
                g.start_death_explosion(sparks)
                killed_side = side
                print(f"[ArtilleryTime] DIRECT ({kind_label}) on {side}!")
            elif d <= shrap_r:
                g.hp -= 1
                hit_kind = "shrapnel" if hit_kind == "miss" else hit_kind
                for _ in range(max(3, n_sparks // 2)):
                    sparks.append(Spark(ix, iy))
                print(f"[ArtilleryTime] Shrapnel ({kind_label}) on {side} hp={g.hp}")
                if g.hp <= 0:
                    g.start_death_explosion(sparks)
                    killed_side = side
                    print(f"[ArtilleryTime] {side} destroyed by shrapnel")
            g.sit_on_ground(heights)
        for _ in range(n_sparks):
            sparks.append(Spark(ix, iy))
        # Learn short/long for the shooter who just landed this blast
        if learn and last_shot.get("owner") is not None:
            _record_shot_outcome(impact_x=ix, result=hit_kind)
        return _check_round_over()

    def _check_round_over():
        nonlocal phase, phase_t, score, round_winner
        if not gun_l.alive or not gun_r.alive:
            if not gun_l.alive and not gun_r.alive:
                round_winner = None
                phase = "destroy_fx"
                phase_t = 0.0
                return True
            winner = "R" if not gun_l.alive else "L"
            score[winner] += 1
            round_winner = winner
            phase = "destroy_fx"
            phase_t = 0.0
            print(f"[ArtilleryTime] Round to {winner}  score L{score['L']}-R{score['R']}")
            return True
        return False

    def _begin_drive_in():
        """After a kill, roll a replacement gun in from the side (keep winner)."""
        nonlocal phase, phase_t, gun_l, gun_r, guns, heights
        # New battlefield, winner already on pad, loser drives in
        heights = generate_terrain(WORLD_W, VIEW_H)
        winner = round_winner
        loser = "R" if winner == "L" else "L"
        # Recreate both; place winner at pad, loser off-screen
        w_home = 10 if winner == "L" else WORLD_W - 11
        l_home = 10 if loser == "L" else WORLD_W - 11
        gun_w = Gun(winner, w_home, heights)
        gun_l_obj = Gun(loser, l_home, heights)
        # Restore weapons/ammo
        for g in (gun_w, gun_l_obj):
            g.weapon = war_weapons.get(g.side, "standard")
            g.ammo = war_ammo.get(g.side)
            if g.ammo is None and g.weapon in WEAPON_AMMO:
                g.ammo = WEAPON_AMMO.get(g.weapon)
        gun_w.sit_on_ground(heights)
        # Loser starts off-screen and drives in
        off = -8.0 if loser == "L" else WORLD_W + 8.0
        gun_l_obj.begin_drive(off, l_home, DRIVE_IN_SEC)
        gun_l_obj.sit_on_ground(heights)
        if winner == "L":
            gun_l, gun_r = gun_w, gun_l_obj
        else:
            gun_l, gun_r = gun_l_obj, gun_w
        guns = {"L": gun_l, "R": gun_r}
        phase = "drive_in"
        phase_t = 0.0
        print(f"[ArtilleryTime] Replacement {loser} rolling in")

    def _begin_victory(winner_side):
        nonlocal phase, phase_t, victory_side, you_win_scale
        victory_side = winner_side
        you_win_scale = 0.05
        phase = "victory_drive"
        phase_t = 0.0
        w = guns[winner_side]
        w.alive = True
        mid = WORLD_W * 0.5
        w.begin_drive(w.x, mid, VICTORY_DRIVE_SEC)
        print(f"[ArtilleryTime] Victory drive — {winner_side}")

    def _spawn_fireworks(cx, cy, n=8):
        for _ in range(n):
            ang = random.uniform(0, math.tau)
            spd = random.uniform(15, 45)
            s = Spark(cx, cy, random.choice((
                (255, 40, 40), (40, 200, 255), (255, 220, 40),
                (80, 255, 80), (255, 100, 200), (255, 255, 255),
            )))
            s.vx = math.cos(ang) * spd
            s.vy = math.sin(ang) * spd - random.uniform(10, 30)
            s.life = random.uniform(0.4, 1.0)
            sparks.append(s)

    def _draw_you_win(scale):
        """
        YOU WIN continuous zoom (screen space).
        scale: 0..1 progress. Glyphs use fractional pixel scale so growth
        is smooth; final size spans full panel width (VIEW_W), height
        clamped to VIEW_H.
        """
        text = "YOU WIN"
        # Build unit-space lit cells (glyph grid, 1 unit per font pixel)
        cells = []  # (ux, uy)
        ux = 0
        for i, ch in enumerate(text):
            rows = _DIGIT.get(ch, _DIGIT.get(" ", ("000",) * 5))
            gw = len(rows[0])
            for ry, row in enumerate(rows):
                for rx, bit in enumerate(row):
                    if bit == "1":
                        cells.append((ux + rx, ry))
            ux += gw
            if i < len(text) - 1:
                ux += 1  # 1-unit gap between characters
        unit_w = max(1, ux)
        unit_h = 5

        # Final zoom target: as wide as the screen, never taller than panel
        max_w = float(VIEW_W)
        max_h = float(VIEW_H)
        max_sc = min(max_w / float(unit_w), max_h / float(unit_h))
        max_sc = max(0.5, max_sc)

        # Continuous scale: start tiny, ease to full cap
        t = _clamp(scale, 0.0, 1.0)
        sc = max_sc * (0.12 + 0.88 * t)  # never zero; ends at max_sc

        tw = unit_w * sc
        th = unit_h * sc
        # Safety clamp if float drift ever edges past cap
        if tw > max_w:
            sc *= max_w / tw
            tw = unit_w * sc
            th = unit_h * sc
        if th > max_h:
            sc *= max_h / th
            tw = unit_w * sc
            th = unit_h * sc

        ox = (VIEW_W - tw) * 0.5
        oy = (VIEW_H - th) * 0.5

        # Solid yellow — only a tiny ramp at the very start of the zoom
        bright = 0.92 + 0.08 * t
        base_r = YOU_WIN_RGB[0] * bright
        base_g = YOU_WIN_RGB[1] * bright
        base_b = YOU_WIN_RGB[2] * bright

        set_px = canvas.SetPixel
        # Soft-box stamp: each lit unit cell becomes an sc×sc square with
        # edge coverage so fractional scales look continuous, not stepped.
        # Interior pixels are forced solid yellow (no washed-out orange).
        for cx, cy in cells:
            x0 = ox + cx * sc
            y0 = oy + cy * sc
            x1 = x0 + sc
            y1 = y0 + sc
            ix0 = max(0, int(math.floor(x0)))
            iy0 = max(0, int(math.floor(y0)))
            ix1 = min(VIEW_W - 1, int(math.ceil(x1) - 1))
            iy1 = min(VIEW_H - 1, int(math.ceil(y1) - 1))
            for py in range(iy0, iy1 + 1):
                # Vertical coverage of pixel [py, py+1) with [y0, y1)
                cov_y = min(y1, py + 1.0) - max(y0, float(py))
                if cov_y <= 0.0:
                    continue
                for px in range(ix0, ix1 + 1):
                    cov_x = min(x1, px + 1.0) - max(x0, float(px))
                    if cov_x <= 0.0:
                        continue
                    cov = cov_x * cov_y  # 0..1 for sc>=1; smaller when sc<1
                    if cov < 0.08:
                        continue
                    # Solid fill for most of each cell; soft only on hairline edges
                    if cov >= 0.35:
                        cov = 1.0
                    else:
                        cov = min(1.0, cov * 2.2)
                    set_px(
                        px, py,
                        min(255, int(base_r * cov)),
                        min(255, int(base_g * cov)),
                        min(255, int(base_b * cov)),
                    )

    def _apply_hit(ix, iy, kind="standard"):
        nonlocal phase, phase_t
        if kind == "airburst":
            # Wide airburst — light crater, big shrapnel radius (over enemy)
            for _ in range(4):
                sparks.append(Spark(
                    ix + random.uniform(-3, 3),
                    iy + random.uniform(-2, 2),
                    (200, 220, 255),
                ))
            if _damage_at(ix, iy, direct_r=3.5, shrap_r=9.0,
                          crater_r=2, crater_d=1, n_sparks=28, kind_label="airburst"):
                return
        elif kind == "sam":
            # Surface-to-air: huge airburst over the target
            for _ in range(10):
                sparks.append(Spark(
                    ix + random.uniform(-6, 6),
                    iy + random.uniform(-5, 3),
                    random.choice(((120, 255, 200), (200, 255, 255), (255, 255, 180))),
                ))
            # Secondary ring of shrapnel raining down
            for _ in range(16):
                ang = random.uniform(0, math.tau)
                r = random.uniform(2, 10)
                sparks.append(Spark(
                    ix + math.cos(ang) * r,
                    iy + math.sin(ang) * r * 0.4 + 1,
                    (180, 240, 220),
                ))
            if _damage_at(ix, iy, direct_r=5.5, shrap_r=14.0,
                          crater_r=3, crater_d=2, n_sparks=48, kind_label="SAM"):
                return
        elif kind == "heavy":
            if _damage_at(ix, iy, direct_r=4.0, shrap_r=8.0,
                          crater_r=8, crater_d=5, n_sparks=40, kind_label="heavy"):
                return
        elif kind == "nuke":
            if _damage_at(ix, iy, direct_r=7.0, shrap_r=14.0,
                          crater_r=12, crater_d=7, n_sparks=55, kind_label="nuke"):
                return
            # Mushroom continues as shell.effect_t
        elif kind == "laser":
            if _damage_at(ix, iy, direct_r=2.0, shrap_r=3.5,
                          crater_r=1, crater_d=1, n_sparks=12, kind_label="laser"):
                return
        elif kind == "phosphorous":
            if _damage_at(ix, iy, direct_r=2.5, shrap_r=5.5,
                          crater_r=3, crater_d=2, n_sparks=18, kind_label="phos"):
                return
        elif kind == "bouncer":
            # Bouncing bomb final detonation — solid HE after 3 hops
            if _damage_at(ix, iy, direct_r=3.2, shrap_r=7.0,
                          crater_r=5, crater_d=3, n_sparks=32, kind_label="bouncer"):
                return
        elif kind == "acid":
            # Dissolve earth + collapse/shift surrounding ground
            for _ in range(8):
                sparks.append(Spark(
                    ix + random.uniform(-5, 5),
                    iy + random.uniform(-2, 1),
                    random.choice(((60, 255, 40), (100, 255, 70), (40, 160, 30))),
                ))
            acid_dissolve(heights, ix, radius=ACID_RADIUS, depth=ACID_DEPTH, strength=1.0)
            smooth_terrain(heights, passes=1)
            for g in guns.values():
                if g.alive:
                    g.sit_on_ground(heights)
            ground_fx.append(GroundFX("acid", ix, ACID_FX_SEC, owner=None))
            # Mild chemical burn damage near the pit
            if _damage_at(ix, iy, direct_r=2.0, shrap_r=6.5,
                          crater_r=0, crater_d=0, n_sparks=12, kind_label="acid"):
                return
        elif kind == "flame":
            # Impact then flames burst along the ground
            for _ in range(10):
                sparks.append(Spark(
                    ix + random.uniform(-3, 3),
                    iy + random.uniform(-1, 1),
                    random.choice(((255, 80, 10), (255, 160, 20), (255, 220, 40))),
                ))
            ground_fx.append(GroundFX("flame", ix, FLAME_BURST_SEC, owner=None))
            if _damage_at(ix, iy, direct_r=2.4, shrap_r=5.5,
                          crater_r=2, crater_d=1, n_sparks=16, kind_label="flame"):
                return
        elif kind == "mg30":
            # Primary shell opens the storm; bullets apply most of the hurt
            if _damage_at(ix, iy, direct_r=1.5, shrap_r=3.0,
                          crater_r=1, crater_d=1, n_sparks=8, kind_label="mg30"):
                return
        else:
            if _damage_at(ix, iy, direct_r=2.2, shrap_r=5.0,
                          crater_r=random.randint(3, 5),
                          crater_d=random.randint(2, 4),
                          n_sparks=EXPLODE_SPARKS, kind_label="HE"):
                return
        phase = "impact"
        phase_t = 0.0

    def _draw_sky():
        # Real-time sky: night / dawn / day / sunset / dusk from local clock
        fill_sky(canvas, VIEW_W, VIEW_H)

    def _draw_terrain():
        set_px = canvas.SetPixel
        x0 = int(math.floor(cam_x))
        for sx in range(VIEW_W):
            wx = x0 + sx
            if wx < 0 or wx >= WORLD_W:
                continue
            surf = heights[wx]
            for y in range(surf, VIEW_H):
                depth = y - surf
                if depth == 0:
                    rgb = GRASS if (wx + y) % 3 else GRASS_DARK
                elif depth < 3:
                    rgb = DIRT
                elif depth < 7:
                    rgb = DIRT_DARK if (wx * 3 + y) % 5 else DIRT
                else:
                    rgb = ROCK if (wx + y * 2) % 7 == 0 else DIRT_DARK
                set_px(sx, y, *rgb)

    def _draw_gun(g):
        set_px = canvas.SetPixel
        sx = g.x - cam_x
        sy = g.y
        # Death fireball ring
        if not g.alive and g.explode_t > 0:
            t = 1.0 - g.explode_t / DESTROY_FX_SEC
            r = int(2 + t * 8)
            for ang in range(0, 360, 20):
                rad = math.radians(ang + t * 90)
                px = int(round(sx + math.cos(rad) * r))
                py = int(round(sy + math.sin(rad) * r * 0.6 - t * 2))
                if 0 <= px < VIEW_W and 0 <= py < VIEW_H:
                    set_px(px, py, 255, int(180 - t * 100), int(40 * (1 - t)))
            # Core glow
            for dx, dy in ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)):
                px, py = int(round(sx + dx)), int(round(sy + dy))
                if 0 <= px < VIEW_W and 0 <= py < VIEW_H:
                    set_px(px, py, 255, 220, 80)
            return
        if not g.alive:
            # Smoldering wreck
            for dx, dy in ((0, 0), (-1, 0), (1, 0), (0, 1)):
                px = int(round(sx + dx))
                py = int(round(sy + dy))
                if 0 <= px < VIEW_W and 0 <= py < VIEW_H:
                    set_px(px, py, 55, 35, 30)
            return
        # Body (+ wheel dots while driving)
        body = (
            (0, 0), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1),
        )
        for dx, dy in body:
            px = int(round(sx + dx))
            py = int(round(sy + dy))
            if 0 <= px < VIEW_W and 0 <= py < VIEW_H:
                set_px(px, py, *g.rgb)
        if g.driving:
            # Rolling wheels
            wh = 1 if int(g.wheel_phase) % 2 == 0 else 0
            for dx in (-1, 1):
                px = int(round(sx + dx))
                py = int(round(sy + 2))
                if 0 <= px < VIEW_W and 0 <= py < VIEW_H:
                    set_px(px, py, 30, 30, 30)
                    if wh:
                        set_px(px, py, 90, 90, 90)
        # Barrel (hide while driving in / victory roll uses forward angle)
        if g.driving:
            rad = math.radians(0.0 if g.side == "L" or g.drive_to > g.drive_from else 180.0)
            if g.drive_to < g.drive_from:
                rad = math.radians(180.0)
            else:
                rad = math.radians(0.0)
        else:
            rad = math.radians(g.angle)
        for i in (1, 2, 3):
            px = int(round(sx + math.cos(rad) * i))
            py = int(round(sy - math.sin(rad) * i))
            if 0 <= px < VIEW_W and 0 <= py < VIEW_H:
                set_px(px, py, *GUN_BARREL)
        if g.flash > 0:
            mx, my = g.muzzle()
            for _ in range(4):
                px = int(round(mx - cam_x + random.uniform(-1, 1)))
                py = int(round(my + random.uniform(-1, 1)))
                if 0 <= px < VIEW_W and 0 <= py < VIEW_H:
                    set_px(px, py, 255, 200, 40)
        if not g.driving:
            for i in range(HP_MAX_SHRAPNEL):
                px = int(round(sx - 1 + i * 2))
                py = int(round(sy - 3))
                if 0 <= px < VIEW_W and 0 <= py < VIEW_H:
                    on = i < g.hp and g.alive
                    set_px(px, py, *(0, 220, 80) if on else (50, 30, 30))
            wrgb = WEAPON_RGB.get(g.weapon, (200, 200, 200))
            px = int(round(sx))
            py = int(round(sy - 5))
            if 0 <= px < VIEW_W and 0 <= py < VIEW_H:
                set_px(px, py, *wrgb)

    def _draw_trajectory():
        """Aiming line from barrel along calculated flight path."""
        if phase not in ("think", "charge") or not aim_preview:
            return
        set_px = canvas.SetPixel
        # Short aim stub from the barrel (25% of full predicted arc)
        AIM_LINE_FRAC = 0.25
        reveal = 1.0 if phase == "charge" else _smooth(min(1.0, phase_t / max(0.05, THINK_SEC * 0.85)))
        n = max(2, int(len(aim_preview) * AIM_LINE_FRAC * reveal))
        for i, (tx, ty) in enumerate(aim_preview[:n]):
            # Dashed / fading compute line
            if i % 2 == 1 and phase == "think":
                continue
            px = int(round(tx - cam_x))
            py = int(round(ty))
            if 0 <= px < VIEW_W and 0 <= py < VIEW_H:
                fade = 0.45 + 0.55 * (i / max(1, n - 1))
                # Very dark grey aiming line
                g = min(255, int(28 * fade))
                set_px(px, py, g, g, g)

    def _draw_power_pips():
        """Red pixels powering up next to the active gun during charge."""
        if phase != "charge":
            return
        active = guns[turn]
        if not active.alive:
            return
        set_px = canvas.SetPixel
        # Stack of red pips behind/beside the gun (away from enemy)
        n_pips = 8
        lit = int(round(n_pips * _clamp(charge_show, 0.0, 1.0)))
        # Place vertical column just behind the gun
        side = -1 if active.side == "L" else 1  # behind = away from center
        # Actually "behind" relative to facing: L faces right, behind is left
        behind = -1 if active.side == "L" else 1
        base_x = active.x + behind * 3.0
        base_y = active.y + 1.0
        for i in range(n_pips):
            px = int(round(base_x - cam_x))
            py = int(round(base_y - i))  # grow upward as power fills
            if not (0 <= px < VIEW_W and 0 <= py < VIEW_H):
                continue
            if i < lit:
                # Hot red power-up
                heat = 0.55 + 0.45 * (i / max(1, n_pips - 1))
                set_px(px, py, 255, int(30 * (1.0 - heat)), int(10 * (1.0 - heat)))
            else:
                # Dim empty socket
                set_px(px, py, 50, 10, 10)

    def _draw_score_pips():
        """Silent match score: colored pips left/right below the 7-seg clock."""
        set_px = canvas.SetPixel
        py = SEG_DIGIT_H + 2  # under the red clock
        for i in range(ROUNDS_TO_WIN):
            px = 1 + i * 2
            on = i < score["L"]
            if 0 <= px < VIEW_W and 0 <= py < VIEW_H:
                set_px(px, py, *(GUN_L_RGB if on else (20, 30, 40)))
            px = VIEW_W - 2 - i * 2
            on = i < score["R"]
            if 0 <= px < VIEW_W and 0 <= py < VIEW_H:
                set_px(px, py, *(GUN_R_RGB if on else (40, 20, 20)))

    def _draw_wind_pips():
        """Silent wind bar just under the 7-seg clock center."""
        set_px = canvas.SetPixel
        ax = VIEW_W // 2
        py = SEG_DIGIT_H + 2
        n = max(1, min(5, int(round(abs(wind) * 1.1))))
        for i in range(1, n + 1):
            px = ax + (i if wind >= 0 else -i)
            if 0 <= px < VIEW_W and 0 <= py < VIEW_H:
                strength = min(255, 70 + int(abs(wind) * 35))
                set_px(px, py, strength, strength, 50)

    def _draw_mid_pedestal():
        """Center mound only — no text display."""
        mid = WORLD_W * 0.5
        set_px = canvas.SetPixel
        for wx in range(int(mid - 10), int(mid + 11)):
            sy = surface_y(heights, wx) - 1
            for dy in range(0, 3):
                px = int(round(wx - cam_x))
                py = int(sy - dy)
                if 0 <= px < VIEW_W and 0 <= py < VIEW_H:
                    set_px(px, py, 40, 40, 55)

    def _draw_ground_fx():
        """Acid stains + surface flame burst along the terrain."""
        if not ground_fx:
            return
        set_px = canvas.SetPixel
        for fx in ground_fx:
            if fx.kind == "acid":
                r = int(ACID_RADIUS * (0.4 + 0.6 * (fx.life / max(0.01, fx.max_life))))
                for dx in range(-r, r + 1):
                    wx = int(round(fx.x + dx))
                    if wx < 0 or wx >= WORLD_W:
                        continue
                    sy = int(surface_y(heights, wx))
                    px = int(round(wx - cam_x))
                    # Greenish slime on surface + one deep pixel
                    for dy in (0, 1):
                        py = sy + dy
                        if 0 <= px < VIEW_W and 0 <= py < VIEW_H:
                            fall = 1.0 - abs(dx) / float(max(1, r))
                            set_px(
                                px, py,
                                min(255, int(30 + 40 * fall)),
                                min(255, int(140 + 100 * fall)),
                                min(255, int(20 + 30 * fall)),
                            )
            elif fx.kind == "flame":
                reach = int(math.ceil(fx.reach))
                for dx in range(-reach, reach + 1):
                    wx = int(round(fx.x + dx))
                    if wx < 0 or wx >= WORLD_W:
                        continue
                    sy = int(surface_y(heights, wx))
                    px = int(round(wx - cam_x))
                    # Fire line on the ground + flicker upward
                    flick = random.randint(1, 3)
                    for dy in range(0, flick + 1):
                        py = sy - dy
                        if not (0 <= px < VIEW_W and 0 <= py < VIEW_H):
                            continue
                        if dy == 0:
                            set_px(px, py, 255, 90, 15)
                        elif dy == 1:
                            set_px(px, py, 255, 160, 30)
                        else:
                            set_px(px, py, 255, 220, 60)

    def _draw_rain_bullets():
        if not rain_bullets:
            return
        set_px = canvas.SetPixel
        for b in rain_bullets:
            if not b.alive:
                continue
            px = int(round(b.x - cam_x))
            py = int(round(b.y))
            if 0 <= px < VIEW_W and 0 <= py < VIEW_H:
                set_px(px, py, 220, 210, 160)
                # short streak
                py2 = py - 1
                if 0 <= py2 < VIEW_H:
                    set_px(px, py2, 140, 140, 110)

    def _draw_drones():
        """Single-pixel drones — cyan while flying, brighter on station."""
        if not drones:
            return
        set_px = canvas.SetPixel
        for d in drones:
            if not d.alive:
                continue
            px = int(round(d.x - cam_x))
            py = int(round(d.y))
            if not (0 <= px < VIEW_W and 0 <= py < VIEW_H):
                continue
            if d.state == "hover":
                # Tiny blink while on station
                blink = 0.55 + 0.45 * (0.5 + 0.5 * math.sin(d.phase * 2.0))
                set_px(
                    px, py,
                    min(255, int(100 * blink + 40)),
                    min(255, int(230 * blink)),
                    255,
                )
            else:
                set_px(px, py, 80, 180, 220)

    def _draw_storms():
        """Electric storm lightning bolts (world → screen)."""
        if not storms:
            return
        set_px = canvas.SetPixel
        for st in storms:
            fade = _clamp(st.life / max(0.05, st.max_life), 0.2, 1.0)
            for bolt in st.bolts:
                for i in range(len(bolt) - 1):
                    x0, y0 = bolt[i]
                    x1, y1 = bolt[i + 1]
                    steps = max(1, int(math.hypot(x1 - x0, y1 - y0)))
                    for s in range(steps + 1):
                        u = s / float(steps)
                        wx = x0 + (x1 - x0) * u
                        wy = y0 + (y1 - y0) * u
                        px = int(round(wx - cam_x))
                        py = int(round(wy))
                        if 0 <= px < VIEW_W and 0 <= py < VIEW_H:
                            set_px(
                                px, py,
                                min(255, int(140 * fade)),
                                min(255, int(220 * fade)),
                                255,
                            )
            # Core glow at storm origin
            cxp = int(round(st.x - cam_x))
            cyp = int(round(st.y))
            for dx, dy in ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)):
                px, py = cxp + dx, cyp + dy
                if 0 <= px < VIEW_W and 0 <= py < VIEW_H:
                    set_px(px, py, 200, 240, 255)

    def _draw_shell():
        if shell is None:
            return
        if (
            not shell.alive
            and not shell.trail
            and shell.burn_t <= 0
            and shell.effect_t <= 0
            and not rain_bullets
        ):
            return
        set_px = canvas.SetPixel
        rgb = shell.rgb
        for p in shell.trail:
            tx, ty, life = p[0], p[1], p[2]
            px = int(round(tx - cam_x))
            py = int(round(ty))
            if 0 <= px < VIEW_W and 0 <= py < VIEW_H and life > 0:
                fade = _clamp(life, 0.0, 1.0)
                fade = fade * fade
                set_px(
                    px, py,
                    min(255, int(rgb[0] * fade)),
                    min(255, int(rgb[1] * fade * 0.9)),
                    min(255, int(rgb[2] * fade * 0.45)),
                )
        if shell.alive or shell.burn_t > 0:
            px = int(round(shell.x - cam_x))
            py = int(round(shell.y))
            if 0 <= px < VIEW_W and 0 <= py < VIEW_H:
                set_px(px, py, *rgb)
                if shell.kind == "phosphorous" and shell.burn_t > 0:
                    # Burning core
                    for dx, dy in ((-1, 0), (1, 0), (0, -1)):
                        qx, qy = px + dx, py + dy
                        if 0 <= qx < VIEW_W and 0 <= qy < VIEW_H:
                            set_px(qx, qy, 255, 160, 30)
                elif shell.kind == "sam":
                    # Missile body + bright nose
                    for dx, dy in ((-1, 0), (0, -1)):
                        qx, qy = px + dx, py + dy
                        if 0 <= qx < VIEW_W and 0 <= qy < VIEW_H:
                            set_px(qx, qy, 80, 200, 160)
                    if 0 <= px + 1 < VIEW_W:
                        set_px(px + 1, py, 255, 255, 220)
                elif shell.kind == "bouncer" and shell.bounces > 0:
                    # Flash on bounce
                    for dx, dy in ((-1, 0), (1, 0), (0, -1)):
                        qx, qy = px + dx, py + dy
                        if 0 <= qx < VIEW_W and 0 <= qy < VIEW_H:
                            set_px(qx, qy, 255, 140, 40)
                elif shell.kind == "acid":
                    for dx, dy in ((-1, 0), (1, 0), (0, -1)):
                        qx, qy = px + dx, py + dy
                        if 0 <= qx < VIEW_W and 0 <= qy < VIEW_H:
                            set_px(qx, qy, 40, 200, 30)
                elif shell.kind == "flame":
                    for dx, dy in ((-1, 0), (1, 0), (0, -1)):
                        qx, qy = px + dx, py + dy
                        if 0 <= qx < VIEW_W and 0 <= qy < VIEW_H:
                            set_px(qx, qy, 255, 120, 20)
                elif shell.kind == "mg30":
                    # Tracer round
                    if 0 <= py - 1 < VIEW_H:
                        set_px(px, py - 1, 255, 240, 120)
        # Mushroom cloud after nuke impact
        if shell.kind == "nuke" and shell.effect_t > 0 and not shell.alive:
            t = 1.0 - shell.effect_t / MUSHROOM_SEC
            cxp = int(round(shell.x - cam_x))
            base_y = int(round(shell.y))
            # Stem
            stem_h = int(2 + t * 10)
            for i in range(stem_h):
                py = base_y - i
                for dx in (-1, 0, 1):
                    px = cxp + dx
                    if 0 <= px < VIEW_W and 0 <= py < VIEW_H:
                        set_px(px, py, 180, 180, 190)
            # Cap
            cap_y = base_y - stem_h
            cap_r = int(2 + t * 7)
            for dy in range(-cap_r // 2, cap_r // 2 + 1):
                for dx in range(-cap_r, cap_r + 1):
                    if dx * dx + dy * dy * 2 > cap_r * cap_r:
                        continue
                    px, py = cxp + dx, cap_y + dy
                    if 0 <= px < VIEW_W and 0 <= py < VIEW_H:
                        set_px(px, py, 220, 200, 160)
            # Glow ring
            for ang in range(0, 360, 30):
                rad = math.radians(ang)
                px = int(cxp + math.cos(rad) * (3 + t * 5))
                py = int(base_y - 1 + math.sin(rad) * 1.5)
                if 0 <= px < VIEW_W and 0 <= py < VIEW_H:
                    set_px(px, py, 255, 120, 30)

    def _draw_sparks():
        set_px = canvas.SetPixel
        for s in sparks:
            px = int(round(s.x - cam_x))
            py = int(round(s.y))
            if 0 <= px < VIEW_W and 0 <= py < VIEW_H and s.life > 0:
                f = _clamp(s.life * 2.5, 0.15, 1.0)
                set_px(
                    px, py,
                    min(255, int(s.rgb[0] * f)),
                    min(255, int(s.rgb[1] * f)),
                    min(255, int(s.rgb[2] * f)),
                )

    # Kick off (no on-screen messages)
    phase = "war_start"
    phase_t = 0.0
    print(
        f"[ArtilleryTime] {VIEW_W}x{VIEW_H} world={WORLD_W}  "
        f"best of {ROUNDS_TO_WIN * 2 - 1}  "
        f"duration={'forever' if forever else f'{run_min} min'}"
    )

    try:
        while True:
            if _stop(StopEvent):
                print("[ArtilleryTime] StopEvent — exit")
                break
            if not forever and time.time() - start > run_min * 60.0:
                print("[ArtilleryTime] Duration reached — exit")
                break

            phase_t += dt

            # Clock: fade in, hold ~5s full, then fade out with the banner
            if phase in ("war_start", "round_end", "war_end"):
                # Full for CLOCK_HOLD_SEC after fade-in completes
                if phase_t < CLOCK_FADE_IN_SEC + CLOCK_HOLD_SEC:
                    clock_target = 1.0
                else:
                    clock_target = 0.0
            elif phase in ("destroy_fx", "drive_in"):
                clock_target = 0.35
            else:
                # think / charge / flight / impact / victory — fully out
                clock_target = 0.0
            if clock_alpha < clock_target:
                step = dt / max(0.05, CLOCK_FADE_IN_SEC)
                clock_alpha = min(clock_target, clock_alpha + step)
            elif clock_alpha > clock_target:
                step = dt / max(0.05, CLOCK_FADE_OUT_SEC)
                clock_alpha = max(clock_target, clock_alpha - step)

            # ---- Phase machine ----
            if phase == "war_start":
                cam_x = camera_follow(WORLD_W * 0.5, cam_x, snap=(phase_t < 0.05))
                # Wait for fade-in + 5s hold + fade-out before combat
                if phase_t >= ROUND_BANNER:
                    # Terrain/guns refresh; weapons come from war loadout
                    _reset_round(new_war=False)
                    _start_think()

            elif phase == "think":
                # Hovering drones keep station / may timeout into storm
                _update_drones(dt)
                _drone_timeout_storms(dt)
                _update_storms(dt)
                active = guns[turn]
                cam_x = camera_follow(active.x, cam_x)
                active.angle = pending_angle
                if phase_t >= THINK_SEC:
                    active.angle = pending_angle
                    phase = "charge"
                    phase_t = 0.0
                    charge_show = 0.0

            elif phase == "charge":
                _update_drones(dt)
                _drone_timeout_storms(dt)
                _update_storms(dt)
                active = guns[turn]
                cam_x = camera_follow(active.x, cam_x)
                charge_show = _smooth(phase_t / max(0.05, CHARGE_SEC))
                active.power = pending_power * charge_show
                if phase_t >= CHARGE_SEC:
                    active.power = pending_power
                    _fire()

            elif phase == "flight":
                # Drones always tick (deploy flight + intercept watch)
                _update_drones(dt)
                _drone_timeout_storms(dt)
                _update_storms(dt)

                if shell is not None:
                    # Enemy drones may swat this shell before it advances
                    if _try_drone_intercept():
                        if phase not in ("destroy_fx", "round_end"):
                            phase = "impact"
                            phase_t = 0.0
                    else:
                        status = shell.update(dt, wind, heights, sparks=sparks)
                        cam_x = camera_follow(shell.x, cam_x)
                        # Intercept again mid-path (drones near shell)
                        if shell.alive and _try_drone_intercept():
                            if phase not in ("destroy_fx", "round_end"):
                                phase = "impact"
                                phase_t = 0.0
                            status = "intercepted"
                        if shell.alive:
                            # Airburst / SAM only detonate on fuse over enemy —
                            # direct body hits still count for solid shells.
                            if shell.kind not in ("airburst", "sam", "mg30"):
                                hit_r = {
                                    "laser": 2.2, "heavy": 2.4, "nuke": 2.8,
                                    "phosphorous": 1.7, "bouncer": 1.9,
                                    "acid": 1.8, "flame": 1.8,
                                }.get(shell.kind, 1.6)
                                for side, g in guns.items():
                                    if not g.alive or side == shell.owner:
                                        continue
                                    if math.hypot(shell.x - g.x, shell.y - g.y) <= hit_r:
                                        shell.alive = False
                                        shell.trail.append([shell.x, shell.y, 1.0])
                                        if shell.kind == "nuke":
                                            shell.effect_t = MUSHROOM_SEC
                                        if shell.kind == "phosphorous":
                                            shell.burn_t = PHOS_BURN_SEC
                                        if not getattr(shell, "_detonated", False):
                                            shell._detonated = True
                                            _apply_hit(shell.x, shell.y, kind=shell.kind)
                                        status = "hit"
                                        break
                            else:
                                # Keep target locked on live enemy while guiding
                                foe = guns.get("R" if shell.owner == "L" else "L")
                                if foe and foe.alive:
                                    shell.target_x = foe.x
                                    shell.target_y = foe.y

                        def _detonate_once(kind):
                            if getattr(shell, "_detonated", False):
                                return
                            shell._detonated = True
                            _apply_hit(shell.x, shell.y, kind=kind)

                        if status == "ground":
                            _detonate_once(shell.kind)
                        elif status == "airburst":
                            _detonate_once("airburst")
                        elif status == "sam_burst":
                            _detonate_once("sam")
                        elif status == "mg_rain":
                            if not getattr(shell, "_rain_spawned", False):
                                shell._rain_spawned = True
                                aim = shell.target_x
                                _spawn_mg_rain(shell.x, shell.y, shell.owner, aim)
                                # Tiny open-burst at rain origin
                                if not getattr(shell, "_detonated", False):
                                    shell._detonated = True
                                    _apply_hit(shell.x, shell.y, kind="mg30")
                            _update_rain_bullets(dt)
                            _try_drone_intercept()
                            if shell.effect_t <= 0 and not rain_bullets and not shell.trail:
                                if phase not in ("round_end", "destroy_fx"):
                                    phase = "impact"
                                    phase_t = 0.0
                        elif status == "mushroom":
                            _detonate_once("nuke")
                            if shell.effect_t <= 0 and not shell.trail:
                                if phase != "round_end":
                                    phase = "impact"
                                    phase_t = 0.0
                        elif status == "burn":
                            _detonate_once("phosphorous")
                            if shell.burn_t <= 0 and not shell.trail:
                                if phase != "round_end":
                                    phase = "impact"
                                    phase_t = max(phase_t, IMPACT_HOLD * 0.4)
                        elif status == "oob":
                            hit_kind = "miss"
                            # OOB counts as short/long for power learning
                            ox = shell.x if shell is not None else None
                            if ox is not None:
                                last_impact = (ox, shell.y if shell else 0)
                                _record_shot_outcome(impact_x=ox, result="miss")
                            phase = "impact"
                            phase_t = 0.0
                        elif status == "intercepted":
                            # Intercepted — don't treat as short ballistic miss
                            last_shot["owner"] = None
                            last_shot["kind"] = None
                        elif status == "dead" and not shell.trail and not rain_bullets:
                            if phase != "round_end":
                                phase = "impact"
                                phase_t = 0.0
                        # Lingering ground FX can start mid-flight (acid/flame detonate)
                        _update_ground_fx(dt)
                        _flame_damage_tick()
                        if rain_bullets and status != "mg_rain":
                            _update_rain_bullets(dt)
                            _try_drone_intercept()
                else:
                    # Drone deploy in progress (no shell)
                    flying = any(
                        d.alive and d.owner == turn and d.state == "fly"
                        for d in drones
                    )
                    hovering = any(
                        d.alive and d.owner == turn and d.state == "hover"
                        for d in drones
                    )
                    if hovering and not flying:
                        # Swarm on station — end deploy turn
                        phase = "impact"
                        phase_t = 0.0
                        hit_kind = hit_kind or "miss"
                        print(f"[ArtilleryTime] Drones on station ({turn})")
                    elif not flying and not hovering:
                        # Deploy failed / empty
                        phase = "impact"
                        phase_t = 0.0
                        hit_kind = "miss"
                    else:
                        # Follow the lead drone
                        lead = next(
                            (d for d in drones if d.alive and d.owner == turn),
                            None,
                        )
                        if lead is not None:
                            cam_x = camera_follow(lead.x, cam_x)

            elif phase == "impact":
                # If a live shell was yanked into impact (e.g. old storm bug),
                # keep integrating it so the turn cannot freeze forever.
                if shell is not None and shell.alive:
                    st = shell.update(dt, wind, heights, sparks=sparks)
                    cam_x = camera_follow(shell.x, cam_x)
                    if st in ("ground", "airburst", "sam_burst", "mg_rain", "mushroom", "burn"):
                        if not getattr(shell, "_detonated", False):
                            shell._detonated = True
                            kind = {
                                "airburst": "airburst",
                                "sam_burst": "sam",
                                "mg_rain": "mg30",
                                "mushroom": "nuke",
                                "burn": "phosphorous",
                            }.get(st, shell.kind)
                            if st == "mg_rain" and not getattr(shell, "_rain_spawned", False):
                                shell._rain_spawned = True
                                _spawn_mg_rain(
                                    shell.x, shell.y, shell.owner, shell.target_x,
                                )
                            _apply_hit(shell.x, shell.y, kind=kind)
                    elif st == "oob":
                        shell.alive = False
                        hit_kind = "miss"
                        _record_shot_outcome(impact_x=shell.x, result="miss")
                elif shell is not None:
                    shell._age_trail(dt, rate=SHELL_TRAIL_FADE_RATE * 1.15)
                    if shell.kind == "phosphorous" and shell.burn_t > 0:
                        shell.update(dt, wind, heights, sparks=sparks)
                    if shell.kind == "nuke" and shell.effect_t > 0:
                        shell.effect_t -= dt
                        if random.random() < 0.7:
                            sparks.append(Spark(
                                shell.x + random.uniform(-4, 4),
                                shell.y - random.uniform(0, 8),
                                random.choice(((255, 200, 40), (255, 100, 20), (200, 200, 200))),
                            ))
                    if shell.kind == "mg30" and shell.effect_t > 0:
                        shell.effect_t -= dt
                _update_drones(dt)
                _drone_timeout_storms(dt)
                _update_storms(dt)
                _update_ground_fx(dt)
                _flame_damage_tick()
                _update_rain_bullets(dt)
                _try_drone_intercept()
                focus = last_impact[0] if last_impact else (
                    shell.x if shell else WORLD_W * 0.5
                )
                if rain_bullets:
                    focus = rain_bullets[0].x
                if storms:
                    focus = storms[0].x
                if shell is not None and shell.alive:
                    focus = shell.x
                cam_x = camera_follow(focus, cam_x)
                trail_done = (
                    (
                        shell is None
                        or (
                            not shell.alive
                            and len(shell.trail) < 2
                            and shell.burn_t <= 0
                            and shell.effect_t <= 0
                        )
                    )
                    and not ground_fx
                    and not rain_bullets
                    and not storms
                )
                # Drones that just reached hover: don't wait forever on impact
                # (they persist into later turns)
                hold = IMPACT_HOLD
                if shell is not None and shell.kind in ("acid", "flame", "mg30"):
                    hold = max(hold, 1.6)
                if storms:
                    hold = max(hold, DRONE_STORM_SEC * 0.85)
                # If only drones hovering (deploy done), short hold
                if (
                    shell is None
                    and not storms
                    and any(d.alive and d.state == "hover" for d in drones)
                ):
                    hold = min(hold, 0.7)
                # Hard safety: never freeze the match on a stuck shell / FX
                IMPACT_MAX_SEC = 6.0
                if phase_t >= IMPACT_MAX_SEC and not trail_done:
                    print("[ArtilleryTime] impact timeout — forcing turn advance")
                    shell = None
                    ground_fx = []
                    rain_bullets = []
                    storms = []
                    trail_done = True
                    hold = 0.0
                if phase_t >= hold and trail_done:
                    if not guns["L"].alive or not guns["R"].alive:
                        # Death already set phase to destroy_fx via _check_round_over
                        if phase != "destroy_fx":
                            phase = "destroy_fx"
                            phase_t = 0.0
                    else:
                        turn = "R" if turn == "L" else "L"
                        if not guns[turn].alive:
                            turn = "R" if turn == "L" else "L"
                        if guns["L"].alive and guns["R"].alive:
                            _start_think()
                        else:
                            phase = "destroy_fx"
                            phase_t = 0.0

            elif phase == "destroy_fx":
                # Big death explosion hang — keep spraying fire
                focus = None
                for side, g in guns.items():
                    if g.explode_t > 0:
                        g.explode_t = max(0.0, g.explode_t - dt)
                        focus = g.x
                        if random.random() < 0.65:
                            sparks.append(Spark(
                                g.x + random.uniform(-2, 2),
                                g.y + random.uniform(-2, 1),
                                random.choice((g.rgb, (255, 160, 30), (255, 80, 10))),
                            ))
                if focus is not None:
                    cam_x = camera_follow(focus, cam_x)
                if phase_t >= DESTROY_FX_SEC:
                    if score["L"] >= ROUNDS_TO_WIN or score["R"] >= ROUNDS_TO_WIN:
                        winner = "L" if score["L"] >= ROUNDS_TO_WIN else "R"
                        _begin_victory(winner)
                    elif round_winner is not None:
                        _begin_drive_in()
                    else:
                        # Draw — just reset round
                        war += 1
                        phase = "war_start"
                        phase_t = 0.0

            elif phase == "drive_in":
                # Replacement rolls onto the field from the side
                arrived = True
                for g in guns.values():
                    if g.driving:
                        done = g.update_drive(dt, heights)
                        cam_x = camera_follow(g.x, cam_x)
                        arrived = arrived and done
                        # Dust puffs under wheels
                        if random.random() < 0.4:
                            sparks.append(Spark(
                                g.x + random.uniform(-1, 1),
                                g.y + 1.5,
                                (140, 110, 60),
                            ))
                            sparks[-1].vy = random.uniform(-2, 4)
                            sparks[-1].life = random.uniform(0.15, 0.35)
                    else:
                        g.sit_on_ground(heights)
                if arrived or phase_t >= DRIVE_IN_SEC + 0.3:
                    for g in guns.values():
                        g.driving = False
                        g.sit_on_ground(heights)
                    turn = random.choice(("L", "R"))
                    wind = random.uniform(WIND_MIN, WIND_MAX)
                    shell = None
                    phase = "think"
                    phase_t = 0.0
                    _start_think()

            elif phase == "victory_drive":
                w = guns.get(victory_side)
                if w is None:
                    phase = "war_end"
                    phase_t = 0.0
                else:
                    w.update_drive(dt, heights)
                    cam_x = camera_follow(w.x, cam_x)
                    if random.random() < 0.35:
                        sparks.append(Spark(
                            w.x + random.uniform(-1, 1), w.y + 1.2, (160, 120, 50),
                        ))
                    if not w.driving or phase_t >= VICTORY_DRIVE_SEC:
                        w.driving = False
                        w.x = WORLD_W * 0.5
                        w.sit_on_ground(heights)
                        phase = "victory_fx"
                        phase_t = 0.0
                        you_win_scale = 0.0
                        _spawn_fireworks(w.x, w.y - 4, n=16)
                        print("[ArtilleryTime] Fireworks + YOU WIN")

            elif phase == "victory_fx":
                w = guns.get(victory_side)
                if w:
                    cam_x = camera_follow(w.x, cam_x)
                    # Continuous fireworks
                    if random.random() < 0.35:
                        _spawn_fireworks(
                            w.x + random.uniform(-6, 6),
                            w.y - random.uniform(2, 12),
                            n=random.randint(4, 10),
                        )
                # YOU WIN zooms in very smoothly over most of the fireworks beat
                zoom_dur = max(0.5, VICTORY_FIREWORKS_SEC * 0.85)
                you_win_scale = _smoother(min(1.0, phase_t / zoom_dur))
                if phase_t >= VICTORY_FIREWORKS_SEC:
                    phase = "war_end"
                    phase_t = 0.0
                    print(f"[ArtilleryTime] WAR OVER — {victory_side}  {score}")

            elif phase == "round_end":
                cam_x = camera_follow(WORLD_W * 0.5, cam_x)
                if phase_t >= ROUND_BANNER:
                    phase = "war_start"
                    phase_t = 0.0

            elif phase == "war_end":
                cam_x = camera_follow(WORLD_W * 0.5, cam_x)
                if phase_t >= WAR_BANNER:
                    score = {"L": 0, "R": 0}
                    war = 1
                    phase = "war_start"
                    phase_t = 0.0
                    wl = random.choice(WEAPONS)
                    wr = random.choice(WEAPONS)
                    war_weapons["L"] = wl
                    war_weapons["R"] = wr
                    war_ammo["L"] = WEAPON_AMMO.get(wl)
                    war_ammo["R"] = WEAPON_AMMO.get(wr)
                    print(f"[ArtilleryTime] Next war loadout  L={wl}  R={wr}")

            # FX
            for g in guns.values():
                if g.flash > 0:
                    g.flash = max(0.0, g.flash - dt)
                if g.explode_t > 0 and phase != "destroy_fx":
                    g.explode_t = max(0.0, g.explode_t - dt)
            alive_sp = []
            for s in sparks:
                s.update(dt)
                if s.life > 0 and s.y < VIEW_H + 8:
                    alive_sp.append(s)
            sparks = alive_sp

            # ---- Draw: sky → terrain → action → HUD ----
            try:
                _draw_sky()
                _draw_terrain()
                _draw_ground_fx()
                _draw_mid_pedestal()
                if phase not in ("victory_drive", "victory_fx", "destroy_fx", "drive_in"):
                    _draw_trajectory()
                _draw_gun(gun_l)
                _draw_gun(gun_r)
                if phase not in ("victory_drive", "victory_fx"):
                    _draw_power_pips()
                _draw_shell()
                _draw_rain_bullets()
                _draw_drones()
                _draw_storms()
                _draw_sparks()
                if phase == "victory_fx" and you_win_scale > 0.05:
                    _draw_you_win(you_win_scale)
                _draw_top_7seg_clock(canvas, VIEW_W, VIEW_H, alpha=clock_alpha)
                if clock_alpha > 0.15:
                    _draw_score_pips()
                    _draw_wind_pips()
                canvas = LED.TheMatrix.SwapOnVSync(canvas)
                LED.Canvas = canvas
            except Exception:
                pass

            if tick:
                tick.tick(TARGET_FPS)
            else:
                time.sleep(dt)

    except KeyboardInterrupt:
        print("[ArtilleryTime] Interrupted")

    try:
        LED.ClearBuffers()
        LED.TheMatrix.Clear()
    except Exception:
        pass


# ===========================================================================
# Title intro — Skyfall-style letters, then artillery shells destroy them
# ===========================================================================
def _title_letter_sprite(char):
    ch = char.upper()
    if not ("A" <= ch <= "Z"):
        return None
    idx = ord(ch) - ord("A")
    try:
        return LED.TrimSprite(copy.deepcopy(LED.AlphaSpriteList[idx]))
    except Exception:
        return None


def _sprite_pixels_zoomed(sprite, zoom, rgb, shadow_rgb):
    pixels = []
    shadow_pixels = []
    sw, sh = sprite.width, sprite.height
    for count in range(sw * sh):
        if sprite.grid[count] == 0:
            continue
        y, x = divmod(count, sw)
        for zv in range(zoom):
            for zh in range(zoom):
                pixels.append((x * zoom + zh, y * zoom + zv, rgb))
                shadow_pixels.append(
                    (x * zoom + zh + 1, y * zoom + zv + 1, shadow_rgb)
                )
    return pixels, shadow_pixels, sw * zoom, sh * zoom


class TitleLetter(object):
    """Banner letter that drops, bounces, rests, then can be shattered."""

    def __init__(self, char, pixels, shadow_pixels, width, height, rest_x, rest_y, drop_delay):
        self.char = char
        self.pixels = pixels
        self.shadow_pixels = shadow_pixels
        self.width = width
        self.height = height
        self.rest_x = rest_x
        self.rest_y = rest_y
        self.drop_delay = drop_delay
        self.x = float(rest_x)
        self.y = float(-height - 6)
        self.vy = 0.0
        self.dropped = False
        self.settled = False
        self.shattered = False
        self.bounce_count = 0

    def center(self):
        return (self.x + self.width * 0.5, self.y + self.height * 0.5)

    def contains_point(self, px, py, pad=1.0):
        return (
            self.x - pad <= px <= self.x + self.width + pad
            and self.y - pad <= py <= self.y + self.height + pad
        )

    def update(self, step, elapsed):
        if self.settled or self.shattered:
            if self.settled and not self.shattered:
                self.y = self.rest_y
            return
        if elapsed < self.drop_delay:
            return
        self.dropped = True
        self.vy += TITLE_LETTER_GRAVITY * step
        self.y += self.vy * step
        if self.y >= self.rest_y:
            self.y = self.rest_y
            if abs(self.vy) < TITLE_LETTER_SETTLE_V or self.bounce_count >= TITLE_LETTER_MAX_BOUNCES:
                self.vy = 0.0
                self.settled = True
            else:
                self.vy = -abs(self.vy) * TITLE_LETTER_BOUNCE_DAMP
                self.bounce_count += 1

    def force_settle(self):
        self.x = float(self.rest_x)
        self.y = float(self.rest_y)
        self.vy = 0.0
        self.dropped = True
        self.settled = True

    def draw(self, canvas, width, height):
        if self.shattered:
            return
        sx = int(round(self.x))
        sy = int(round(self.y))
        set_px = canvas.SetPixel
        for dx, dy, rgb in self.shadow_pixels:
            px, py = sx + dx, sy + dy
            if 0 <= px < width and 0 <= py < height:
                set_px(px, py, *rgb)
        for dx, dy, rgb in self.pixels:
            px, py = sx + dx, sy + dy
            if 0 <= px < width and 0 <= py < height:
                set_px(px, py, *rgb)


def _build_title_letters(width, height):
    """Two-line ARTY / TIME layout, Skyfall-style zoomed Alpha sprites."""
    lines = (TITLE_LINE1, TITLE_LINE2)
    line_specs = []
    for line in lines:
        specs = []
        for char in line:
            if char == " ":
                continue
            sprite = _title_letter_sprite(char)
            if sprite is None:
                continue
            pixels, shadow, lw, lh = _sprite_pixels_zoomed(
                sprite, TITLE_LETTER_ZOOM,
                TITLE_LETTER_RGB, TITLE_LETTER_SHADOW_RGB,
            )
            specs.append((char, pixels, shadow, lw, lh))
        line_specs.append(specs)

    if not any(line_specs):
        return []

    line_heights = [
        max((s[4] for s in specs), default=0) for specs in line_specs
    ]
    total_h = sum(line_heights) + TITLE_LINE_GAP * max(0, len(line_specs) - 1)
    start_y = max(1, (height - total_h) // 2)

    letters = []
    y_cursor = start_y
    delay_i = 0
    for li, specs in enumerate(line_specs):
        if not specs:
            continue
        total_w = sum(s[3] for s in specs) + TITLE_LETTER_GAP * max(0, len(specs) - 1)
        x_cursor = max(0, (width - total_w) // 2)
        row_h = line_heights[li]
        for char, pixels, shadow, lw, lh in specs:
            y_off = row_h - lh
            letters.append(TitleLetter(
                char, pixels, shadow, lw, lh,
                x_cursor, y_cursor + y_off,
                drop_delay=delay_i * TITLE_LETTER_STAGGER,
            ))
            x_cursor += lw + TITLE_LETTER_GAP
            delay_i += 1
        y_cursor += row_h + TITLE_LINE_GAP
    return letters


def _shatter_letter(letter, debris):
    """Explode one letter into debris sparks."""
    if letter.shattered:
        return
    sx = int(round(letter.x))
    sy = int(round(letter.y))
    for dx, dy, rgb in letter.pixels:
        debris.append(Spark(sx + dx, sy + dy, rgb))
        debris[-1].vx = random.uniform(-35, 35)
        debris[-1].vy = random.uniform(-40, 15)
        debris[-1].life = random.uniform(0.35, 0.9)
    for dx, dy, rgb in letter.shadow_pixels:
        debris.append(Spark(sx + dx, sy + dy, rgb))
        debris[-1].life = random.uniform(0.2, 0.5)
    letter.shattered = True


class IntroShell(object):
    """Shell that streaks in from off-screen and destroys title letters."""

    def __init__(self, x, y, vx, vy):
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.alive = True
        self.trail = []  # [x,y,life]

    def update(self, dt):
        self.trail.append([self.x, self.y, 1.0])
        if len(self.trail) > 12:
            self.trail.pop(0)
        for p in self.trail:
            p[2] -= 2.4 * dt
        self.trail = [p for p in self.trail if p[2] > 0.05]
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.x < -20 or self.x > VIEW_W + 20 or self.y < -20 or self.y > VIEW_H + 20:
            self.alive = False

    def draw(self, canvas, width, height):
        set_px = canvas.SetPixel
        for p in self.trail:
            px, py = int(round(p[0])), int(round(p[1]))
            if 0 <= px < width and 0 <= py < height:
                f = _clamp(p[2], 0.0, 1.0)
                set_px(
                    px, py,
                    min(255, int(TITLE_SHELL_RGB[0] * f)),
                    min(255, int(TITLE_SHELL_RGB[1] * f * 0.85)),
                    min(255, int(TITLE_SHELL_RGB[2] * f * 0.3)),
                )
        if self.alive:
            px, py = int(round(self.x)), int(round(self.y))
            if 0 <= px < width and 0 <= py < height:
                set_px(px, py, *TITLE_SHELL_RGB)


def _spawn_intro_shell(width, height, letters):
    """Spawn a shell from left, right, or top aimed at a living letter."""
    targets = [L for L in letters if not L.shattered and L.settled]
    if not targets:
        targets = [L for L in letters if not L.shattered]
    if not targets:
        return None
    letter = random.choice(targets)
    tx, ty = letter.center()
    side = random.choice(("left", "right", "top", "top", "left", "right"))
    if side == "left":
        x, y = -3.0, random.uniform(2, height - 4)
    elif side == "right":
        x, y = width + 3.0, random.uniform(2, height - 4)
    else:
        x, y = random.uniform(2, width - 3), -3.0
    dx, dy = tx - x, ty - y
    dist = math.hypot(dx, dy) or 1.0
    speed = random.uniform(48.0, 78.0)
    # Slight aim noise so hits aren't always dead-center
    jx = random.uniform(-2.5, 2.5)
    jy = random.uniform(-2.0, 2.0)
    dx, dy = (tx + jx) - x, (ty + jy) - y
    dist = math.hypot(dx, dy) or 1.0
    return IntroShell(x, y, dx / dist * speed, dy / dist * speed)


def PlayArtilleryTitleIntro(StopEvent=None):
    """
    Stylized ARTY / TIME letters drop and bounce (Skyfall style), then
    artillery rounds streak from the sides and above to destroy them.
    """
    global VIEW_W, VIEW_H
    VIEW_W = int(getattr(LED, "HatWidth", 64) or 64)
    VIEW_H = int(getattr(LED, "HatHeight", 32) or 32)
    width, height = VIEW_W, VIEW_H

    if _stop(StopEvent):
        return

    letters = _build_title_letters(width, height)
    if not letters:
        print("[ArtilleryTime] Title intro skipped (no letter sprites)")
        return

    try:
        canvas = LED.TheMatrix.CreateFrameCanvas()
    except Exception:
        canvas = LED.Canvas

    tick = pygame.time.Clock() if HAS_PYGAME else None
    start = time.time()
    last = start
    hold_start = None
    barrage_start = None
    shells = []
    debris = []
    spawn_cd = 0.0
    print("[ArtilleryTime] Title intro — ARTY TIME drop + shell barrage")

    try:
        while True:
            if _stop(StopEvent):
                print("[ArtilleryTime] Title intro — StopEvent")
                break
            now = time.time()
            elapsed = now - start
            dt = min(0.05, now - last)
            last = now
            step = dt * TITLE_INTRO_FPS  # motion scaled like Skyfall

            if elapsed >= TITLE_INTRO_MAX_SECONDS:
                for L in letters:
                    if not L.shattered:
                        _shatter_letter(L, debris)
                break

            # --- Phase: drop / hold / barrage ---
            for L in letters:
                L.update(step, elapsed)

            all_settled = all(L.settled or L.shattered for L in letters)
            if hold_start is None and all_settled:
                hold_start = now
                print("[ArtilleryTime] Title settled — hold")

            if (
                hold_start is not None
                and barrage_start is None
                and now - hold_start >= TITLE_HOLD_SECONDS
            ):
                barrage_start = now
                print("[ArtilleryTime] Shell barrage!")

            if barrage_start is not None:
                spawn_cd -= dt
                living = sum(1 for L in letters if not L.shattered)
                if living > 0 and spawn_cd <= 0:
                    # Fire faster as more letters fall
                    spawn_cd = random.uniform(0.12, 0.28)
                    sh = _spawn_intro_shell(width, height, letters)
                    if sh:
                        shells.append(sh)
                # Update shells + hits
                for sh in shells:
                    if not sh.alive:
                        continue
                    sh.update(dt)
                    for L in letters:
                        if L.shattered:
                            continue
                        if L.contains_point(sh.x, sh.y, pad=1.2):
                            sh.alive = False
                            _shatter_letter(L, debris)
                            # Extra blast sparks
                            for _ in range(8):
                                debris.append(Spark(sh.x, sh.y, TITLE_SHELL_RGB))
                            break
                shells = [s for s in shells if s.alive or s.trail]
                # Done when all letters gone and debris mostly dead
                if living == 0 and barrage_start and now - barrage_start > 0.6:
                    if not any(d.life > 0.1 for d in debris):
                        break
                if now - barrage_start >= TITLE_BARRAGE_SECONDS:
                    for L in letters:
                        if not L.shattered:
                            _shatter_letter(L, debris)
                    if now - barrage_start >= TITLE_BARRAGE_SECONDS + 0.8:
                        break

            # Debris
            alive_d = []
            for d in debris:
                d.update(dt)
                if d.life > 0 and -4 < d.y < height + 6:
                    alive_d.append(d)
            debris = alive_d

            # Draw
            try:
                canvas.Fill(0, 0, 0)
                # Time-of-day sky (same clock as in-game)
                fill_sky(canvas, width, height)
                set_px = canvas.SetPixel
                for L in letters:
                    if not L.shattered and (L.dropped or L.settled):
                        L.draw(canvas, width, height)
                for sh in shells:
                    sh.draw(canvas, width, height)
                for d in debris:
                    px, py = int(round(d.x)), int(round(d.y))
                    if 0 <= px < width and 0 <= py < height and d.life > 0:
                        f = _clamp(d.life * 2.0, 0.1, 1.0)
                        set_px(
                            px, py,
                            min(255, int(d.rgb[0] * f)),
                            min(255, int(d.rgb[1] * f)),
                            min(255, int(d.rgb[2] * f)),
                        )
                canvas = LED.TheMatrix.SwapOnVSync(canvas)
                LED.Canvas = canvas
            except Exception:
                pass

            if tick:
                tick.tick(TITLE_INTRO_FPS)
            else:
                time.sleep(1.0 / TITLE_INTRO_FPS)

    except KeyboardInterrupt:
        pass
    except Exception as exc:
        print(f"[ArtilleryTime] title intro error: {exc}")

    print("[ArtilleryTime] Title intro complete")
    try:
        LED.ClearBuffers()
        LED.TheMatrix.Clear()
    except Exception:
        pass


def LaunchArtilleryTime(Duration=10, ShowIntro=True, StopEvent=None):
    try:
        LED.LoadConfigData()
    except Exception:
        pass
    if ShowIntro and not _stop(StopEvent):
        try:
            PlayArtilleryTitleIntro(StopEvent=StopEvent)
        except Exception as exc:
            print(f"[ArtilleryTime] intro failed: {exc}")
    if _stop(StopEvent):
        return
    PlayArtilleryTime(Duration=Duration, StopEvent=StopEvent)


if __name__ == "__main__":
    # Standalone: run forever until Ctrl-C / kill
    try:
        LaunchArtilleryTime(Duration=0, ShowIntro=True, StopEvent=None)
    except KeyboardInterrupt:
        print("Exiting Artillery Time.")
