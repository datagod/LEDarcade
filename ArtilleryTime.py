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
SEG_CLOCK_RGB = (255, 36, 28)       # lit red
SEG_CLOCK_DIM = (27, 6, 5)          # ghost segments
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
# nuke        — one mushroom-cloud super shell per war
WEAPONS = (
    "standard",
    "airburst",
    "heavy",
    "laser",
    "phosphorous",
    "bouncer",
    "sam",
    "nuke",
)
WEAPON_AMMO = {
    "heavy": 2,
    "nuke": 1,
    "sam": 3,
}
WEAPON_RGB = {
    "standard": (255, 240, 120),
    "airburst": (200, 220, 255),
    "heavy": (255, 120, 40),
    "laser": (255, 40, 60),
    "phosphorous": (180, 255, 80),
    "bouncer": (255, 170, 60),
    "sam": (120, 255, 200),
    "nuke": (255, 255, 200),
}
BOUNCE_BOMB_BOUNCES = 3       # bouncer detonates after this many ground hits
AIRBURST_OVER_X = 9.0         # horizontal window over enemy for airburst fuse
SAM_OVER_X = 11.0             # SAM fuse window over enemy
SAM_AIR_CLEARANCE = 4.5       # min px above surface / target for SAM fuse

# ---- Timing (seconds) ----
THINK_SEC = 1.4
CHARGE_SEC = 1.1
IMPACT_HOLD = 1.0
ROUND_BANNER = 1.2
WAR_BANNER = 1.0
PHOS_BURN_SEC = 2.8
MUSHROOM_SEC = 2.2
DESTROY_FX_SEC = 1.5          # big death explosion hold
DRIVE_IN_SEC = 2.2            # replacement rolls onto the field
VICTORY_DRIVE_SEC = 2.8       # winner to center
VICTORY_FIREWORKS_SEC = 4.0   # fireworks + YOU WIN
YOU_WIN_RGB = (255, 230, 60)

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
    """Soft moon at night. Returns (cx, cy, rad) or None."""
    h = float(hour) % 24.0
    elev = math.cos((h - 12.0) / 12.0 * math.pi)
    if elev >= -0.12:
        return None
    day_u = _clamp((h - 5.0) / 15.0, 0.0, 1.0)
    moon_u = (day_u + 0.55) % 1.0
    cx = 5.0 + moon_u * (width - 10.0)
    cy = height * (0.16 + 0.12 * min(1.0, abs(elev)))
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
    r = int(radius)
    for dx in range(-r, r + 1):
        px = xi + dx
        if 0 <= px < len(heights):
            fall = 1.0 - (abs(dx) / float(max(1, r)))
            dig = depth * fall * fall
            heights[px] = int(_clamp(heights[px] + dig, VIEW_H * 0.35, VIEW_H - 2))


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
            if self.ammo <= 0 and self.weapon in ("heavy", "nuke", "sam"):
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
    vx = math.cos(rad) * speed
    vy = -math.sin(rad) * speed
    x, y = float(x0), float(y0)
    best = 1e9
    path = [(x, y)] if record_path else None
    bounces = 0
    aim_y = enemy_y - 8.0

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


def ai_choose_shot(gun, enemy, wind, heights):
    """Search angle/power for best predicted hit (weapon-aware)."""
    best = None
    best_score = 1e18
    weapon = gun.weapon
    if gun.side == "L":
        if weapon == "laser":
            angles = range(15, 70, 2)   # lower bank angles
        elif weapon == "sam":
            angles = range(40, 82, 2)  # loft toward sky then enemy
        else:
            angles = range(28, 78, 2)
    else:
        if weapon == "laser":
            angles = range(110, 165, 2)
        elif weapon == "sam":
            angles = range(98, 140, 2)
        else:
            angles = range(102, 152, 2)
    for ang in angles:
        for p10 in range(25, 100, 3):
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
            score += random.uniform(0, 0.35)
            if score < best_score:
                best_score = score
                best = (float(ang), power, mind)
    if best is None:
        return 45.0 if gun.side == "L" else 135.0, 0.6, 99.0
    return best


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
          fly | ground | oob | dead | airburst | sam_burst | burn | mushroom
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
            return "dead"

        self.age += dt
        self.trail.append([self.x, self.y, 1.0])
        max_trail = SHELL_TRAIL + (20 if self.kind == "laser" else 0)
        if self.kind == "sam":
            max_trail = SHELL_TRAIL + 10
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
            return "ground"
        return "fly"


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
    """HH:MM red 7-seg clock, top-center. alpha 0=hidden, 1=full bright."""
    a = _clamp(float(alpha), 0.0, 1.0)
    if a < 0.02:
        return
    lit = _scale_rgb(SEG_CLOCK_RGB, a)
    dim = _scale_rgb(SEG_CLOCK_DIM, a)
    if lit is None:
        return
    now = datetime.now()
    hh = now.hour
    mm = now.minute
    digits = (hh // 10, hh % 10, mm // 10, mm % 10)
    total_w = _seg_clock_width()
    ox = (width - total_w) // 2
    oy = 1
    x = ox
    _draw_7seg_digit(canvas, x, oy, digits[0], lit, dim, width, height)
    x += SEG_DIGIT_W + SEG_GAP
    _draw_7seg_digit(canvas, x, oy, digits[1], lit, dim, width, height)
    x += SEG_DIGIT_W + SEG_GAP
    # Colon
    set_px = canvas.SetPixel
    mid = SEG_DIGIT_H // 2
    for cy in (mid - 2, mid + 1):
        for xx in range(SEG_COLON_W):
            for yy in range(SEG_THICK):
                px, py = x + xx, oy + cy + yy
                if 0 <= px < width and 0 <= py < height:
                    set_px(px, py, *lit)
    x += SEG_COLON_W + SEG_GAP
    _draw_7seg_digit(canvas, x, oy, digits[2], lit, dim, width, height)
    x += SEG_DIGIT_W + SEG_GAP
    _draw_7seg_digit(canvas, x, oy, digits[3], lit, dim, width, height)


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
    cam_x = 0.0
    last_impact = None
    hit_kind = None           # "direct" | "shrapnel" | "miss"
    pending_angle = 45.0
    pending_power = 0.5
    charge_show = 0.0
    aim_preview = []
    killed_side = None
    round_winner = None
    victory_side = None
    you_win_scale = 0.0
    # 7-seg clock visibility: full at war/round start & end; fades during combat
    clock_alpha = 1.0
    CLOCK_FADE_SPEED = 2.2   # alpha units per second

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
        nonlocal war_weapons, war_ammo
        heights = generate_terrain(WORLD_W, VIEW_H)
        gun_l = Gun("L", 10, heights)
        gun_r = Gun("R", WORLD_W - 11, heights)
        guns = {"L": gun_l, "R": gun_r}
        if new_war:
            assign_random_weapons(gun_l, gun_r)
            war_weapons = {"L": gun_l.weapon, "R": gun_r.weapon}
            war_ammo = {"L": gun_l.ammo, "R": gun_r.ammo}
        else:
            _restore_weapons_on_guns()
        shell = None
        sparks = []
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
        ang, power, mind = ai_choose_shot(active, enemy, wind, heights)
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
        print(
            f"[ArtilleryTime] {turn}/{active.weapon} aims  ang={ang:.0f}°  "
            f"pwr={power:.2f}  wind={wind:+.1f}  pred~{mind:.1f}px"
        )

    def _fire():
        nonlocal shell, phase, phase_t, war_ammo
        active = guns[turn]
        enemy = guns["R" if turn == "L" else "L"]
        mx, my = active.muzzle()
        rad = math.radians(active.angle)
        kind = active.weapon
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
        vx = math.cos(rad) * speed
        vy = -math.sin(rad) * speed
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

    def _damage_at(ix, iy, direct_r, shrap_r, crater_r, crater_d, n_sparks, kind_label="HE"):
        """Apply blast damage at (ix,iy). Returns True if round ended."""
        nonlocal hit_kind, last_impact, phase, phase_t, score, killed_side
        last_impact = (ix, iy)
        if crater_r > 0:
            crater(heights, ix, radius=crater_r, depth=crater_d)
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

        # Brightness ramps up with zoom progress
        bright = 0.35 + 0.65 * t
        base_r = YOU_WIN_RGB[0] * bright
        base_g = YOU_WIN_RGB[1] * bright
        base_b = YOU_WIN_RGB[2] * bright

        set_px = canvas.SetPixel
        # Soft-box stamp: each lit unit cell becomes an sc×sc square with
        # edge coverage so fractional scales look continuous, not stepped.
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
                    if cov < 0.04:
                        continue
                    cov = min(1.0, cov)
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

    def _draw_shell():
        if shell is None:
            return
        if not shell.alive and not shell.trail and shell.burn_t <= 0 and shell.effect_t <= 0:
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

            # Clock: visible at beginning/end; hidden during combat + victory show
            if phase in ("war_start", "round_end", "war_end", "destroy_fx", "drive_in"):
                clock_target = 1.0 if phase in ("war_start", "round_end", "war_end") else 0.35
            elif phase in ("victory_drive", "victory_fx"):
                clock_target = 0.0
            else:
                clock_target = 0.0
            if clock_alpha < clock_target:
                clock_alpha = min(clock_target, clock_alpha + CLOCK_FADE_SPEED * dt)
            elif clock_alpha > clock_target:
                clock_alpha = max(clock_target, clock_alpha - CLOCK_FADE_SPEED * dt)

            # ---- Phase machine ----
            if phase == "war_start":
                cam_x = camera_follow(WORLD_W * 0.5, cam_x, snap=(phase_t < 0.05))
                if phase_t >= ROUND_BANNER:
                    # Terrain/guns refresh; weapons come from war loadout
                    _reset_round(new_war=False)
                    _start_think()

            elif phase == "think":
                active = guns[turn]
                cam_x = camera_follow(active.x, cam_x)
                active.angle = pending_angle
                if phase_t >= THINK_SEC:
                    active.angle = pending_angle
                    phase = "charge"
                    phase_t = 0.0
                    charge_show = 0.0

            elif phase == "charge":
                active = guns[turn]
                cam_x = camera_follow(active.x, cam_x)
                charge_show = _smooth(phase_t / max(0.05, CHARGE_SEC))
                active.power = pending_power * charge_show
                if phase_t >= CHARGE_SEC:
                    active.power = pending_power
                    _fire()

            elif phase == "flight":
                if shell is not None:
                    status = shell.update(dt, wind, heights, sparks=sparks)
                    cam_x = camera_follow(shell.x, cam_x)
                    if shell.alive:
                        # Airburst / SAM only detonate on fuse over enemy —
                        # direct body hits still count for solid shells.
                        if shell.kind not in ("airburst", "sam"):
                            hit_r = {
                                "laser": 2.2, "heavy": 2.4, "nuke": 2.8,
                                "phosphorous": 1.7, "bouncer": 1.9,
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
                        phase = "impact"
                        phase_t = 0.0
                    elif status == "dead" and not shell.trail:
                        if phase != "round_end":
                            phase = "impact"
                            phase_t = 0.0
                else:
                    phase = "impact"
                    phase_t = 0.0

            elif phase == "impact":
                if shell is not None:
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
                focus = last_impact[0] if last_impact else (
                    shell.x if shell else WORLD_W * 0.5
                )
                cam_x = camera_follow(focus, cam_x)
                trail_done = (
                    shell is None
                    or (
                        not shell.alive
                        and len(shell.trail) < 2
                        and shell.burn_t <= 0
                        and shell.effect_t <= 0
                    )
                )
                if phase_t >= IMPACT_HOLD and trail_done:
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
                _draw_mid_pedestal()
                if phase not in ("victory_drive", "victory_fx", "destroy_fx", "drive_in"):
                    _draw_trajectory()
                _draw_gun(gun_l)
                _draw_gun(gun_r)
                if phase not in ("victory_drive", "victory_fx"):
                    _draw_power_pips()
                _draw_shell()
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
