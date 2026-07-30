# =====================================================================================
# PINBALL — LED matrix pinball table simulation
#
# A tall (7× screen height) single-width playfield with:
#   - Two animated flippers at the bottom corners
#   - A silver ball with gravity, wall bounce, and flipper hits
#   - Camera that pans vertically to follow the ball
#
# Rendering uses the LEDarcade canvas + SwapOnVSync path (LEDsim-safe).
# =====================================================================================

from __future__ import annotations

import LEDarcade as LED

LED.Initialize()

import copy
import math
import time
import random

try:
    import pygame
    HAS_PYGAME = True
except Exception:
    HAS_PYGAME = False


# ---------------- Configuration ----------------

WIDTH = int(LED.HatWidth)
HEIGHT = int(LED.HatHeight)

# World is one screen wide, tall playfield (longer = more room for camera tracking)
MAP_SCALE_Y = 7
# Extra world height for the playfield (table taller by this many pixels)
TABLE_EXTRA_H = 2
MAP_W = WIDTH
MAP_H = HEIGHT * MAP_SCALE_Y + TABLE_EXTRA_H

TARGET_FPS = 40
PHYSICS_SUBSTEPS = 3               # smoother collision / less tunneling & jitter
GRAVITY = 0.085
AIR_DRAG = 0.9992                  # slightly less drag per full frame via substeps
BOUNCE = 0.72
MAX_SPEED = 6.5 * 0.75          # 25% slower cap (was 6.5)
BALL_RADIUS = 1.15  # collision radius in world pixels
# Keep the ball on-screen, clear of top/bottom view edges
VIEW_EDGE_MARGIN = 6               # min pixels between ball and top/bottom of view
CAMERA_FOLLOW = 0.14               # smooth pan (lower = less jitter)
CAMERA_CATCHUP = 0.42              # only when ball near view edge
# Extra world padding so camera can track without pinning the ball to the rim
WORLD_TOP_PAD = 4
WORLD_BOTTOM_PAD = 4
# Curved top rail — ball stays on the *inside* and rolls along it
ARC_RGB = (90, 100, 120)
ARC_HIGHLIGHT = (140, 155, 180)
ARC_BOUNCE = 0.55                  # soft so it doesn't buzz on the curve
ARC_TANGENT_FRICTION = 0.997
ARC_SLOP = 0.08                    # penetration tolerance (reduces micro-jitter)

# Flippers — classic bottom layout with a clear center drain between tips.
#
# Standard lower playfield (Italian bottom / EM era), left → right:
#   wall | OUTLANE | SLING | inlane → FLIPPER |  D R A I N  | FLIPPER ← inlane | SLING | OUTLANE | wall | plunger
#
# Flippers sit at the very bottom; rest tips aim gently down-center but leave
# a gap wide enough for the ball (plus flipper collision thickness) to fall through.
FLIPPER_LEN = max(10, int(WIDTH * 0.17))
FLIPPER_THICK = 1.4
FLIPPER_PAD = 0.55
# Hit envelope half-width of a resting bat (ball center must clear both tips)
_FLIPPER_HIT_R = BALL_RADIUS + FLIPPER_THICK * 0.5 + FLIPPER_PAD
# Tip-to-tip open gap at rest — roomy center drain (classic ~1.5–2 ball widths
# of free air; we size by collision radii so the ball never wedges)
FLIPPER_DRAIN_GAP = max(6.5, 2.0 * _FLIPPER_HIT_R + 1.6)
# Pivot height above the bottom edge (world y = MAP_H - this)
FLIPPER_BOTTOM_INSET = 3.5 + 10
# Rest: tips point gently down-center; active: tips rise (classic bat swing)
LEFT_REST = 0.38
LEFT_ACTIVE = -0.95
RIGHT_REST = math.pi - 0.38
RIGHT_ACTIVE = math.pi + 0.95
FLIPPER_SWING_SPEED = 0.26
FLIPPER_POWER = 2.85
# Skill AI: hold ball on rest blade, flip at a chosen position along the flipper
FLIP_HOLD_SPEED = 0.95
FLIP_CATCH_DIST = 2.4
FLIP_BASE_T = 0.28
FLIP_MID_T = 0.55
FLIP_TIP_T = 0.82
# Upper-third side flippers (symmetric, almost on the walls)
UPPER_FLIPPER_LEN = max(8, int(FLIPPER_LEN * 0.90))
UPPER_FLIPPER_SIDE_INSET = 2.2      # pivot almost touching each side wall
UPPER_FLIPPER_Y_FRAC = 0.26         # fraction of playfield height from top
# Aggressive upper AI: faster swing, harder hits, earlier intercept
UPPER_FLIPPER_SWING_SPEED = FLIPPER_SWING_SPEED * 1.55
UPPER_FLIPPER_POWER = FLIPPER_POWER * 1.35
UPPER_FLIP_CATCH_DIST = FLIP_CATCH_DIST * 1.55
UPPER_FLIP_LOOKAHEAD = 10.0         # predict ball position (px-ish)
UPPER_FLIP_REACT_Y = 22.0           # start tracking this far above the bat

# Plunger lane (right side — traditional pinball launch)
PLUNGER_LANE_W = 3                 # width of the right-hand lane
# Full pull hard into the top arc; every launch is floored so the ball
# always clears the chute into the playfield (strength only varies exit speed).
PLUNGER_POWER = 6.6                # nominal full upward launch speed
PLUNGER_CHARGE_FRAMES = 22         # frames for a full visual pull-back
PLUNGER_RELOAD_FRAMES = 40         # delay after drain before next shot
# After a drain: apron anim (clock → score → clock) then plunger
# Camera stays put; only the bottom apron content scrolls in place.
APRON_SCROLL_SECONDS = 0.45       # clock down / score in (and reverse)
APRON_SCORE_HOLD_SECONDS = 1.0    # score stays before clock returns
# Auto-play: each launch picks a random pull strength in this range
# (soft = just clears chute; full = hard skill-shot crank)
PLUNGER_STRENGTH_MIN = 0.35
PLUNGER_STRENGTH_MAX = 1.0
# Safety net if a launch still stalls in the lane (should be rare)
PLUNGER_RETRY_STRENGTH_BOOST = 0.12
PLUNGER_RETRY_POWER_SCALE = 1.12
PLUNGER_RETRY_MAX_POWER = PLUNGER_POWER * 1.20
# Chute launches must exceed playfield MAX_SPEED or they never clear the lane
PLUNGER_LANE_MAX_SPEED = PLUNGER_RETRY_MAX_POWER
PLUNGER_CLIMB_CLEAR = 10.0
PLUNGER_RETURN_Y = 6.5
PLUNGER_RETURN_SPEED = 0.35
PLUNGER_RETRY_MIN_FRAMES = 12
# Lane opens into the playfield *inside* the top arc (not outside the curve)
PLUNGER_EXIT_INSET = 2.2           # how far inside the arc the ball is delivered
# --- 1960s–early-70s EM layout vocabulary ---
# Classic arrangement (bottom → top):
#   flippers + center drain → slingshots just above/outside each bat
#   → midfield targets → triangle of 3 pop bumpers under the top curve
#   → plunger on the right. Drop-target bank sits mid-playfield.
#
# Pop bumpers (active "thumper" bumpers)
BUMPER_RGB = (50, 90, 200)
BUMPER_LIT_RGB = (120, 180, 255)
BUMPER_R = 2.5
BUMPER_KICK = 0.72
# Slingshots — just above and to either side of the flippers (classic EM)
# Tall wall, short base; long rubber faces the playfield. Apexes stay
# outside the center drain corridor so the ball can always fall middle.
SLING_KICK = 2.35 * 0.5           # 50% weaker pop (was 2.35)
SLING_RGB = (160, 40, 40)
SLING_RUBBER = (230, 85, 65)
SLING_LIT_RGB = (255, 190, 90)
SLING_PAD = 0.95                  # collision half-width (body + rubber solid)
# Upper-center bounce triangle (between top flippers) — weak sling-like
UPPER_TRI_SIDE = 10.0             # equilateral side length (px)
UPPER_TRI_KICK = SLING_KICK * 0.45  # bounce pop, weaker than slingshots
UPPER_TRI_RGB = (140, 150, 165)
UPPER_TRI_EDGE = (200, 210, 225)
UPPER_TRI_PAD = 0.9
SLING_HEIGHT = 13.0            # tall relative to short base
SLING_BASE = 4.2               # short base toward center — never closes the drain
# Extra open space between left/right sling apexes (flippers stay put)
SLING_GAP_WIDEN = 4.0          # total pixels — 2px each side, away from center
# Whole sling shifted outward (left← / right→) and up; flippers unchanged
SLING_OUTWARD_SHIFT = 2.0 + 3.0   # prior 2 + move over 3 more
SLING_UP_SHIFT = 3.0              # entire shape raised (smaller y)
# Narrow outlane between side wall and sling outer face (~1 ball + margin)
OUTLANE_W = max(2.8, BALL_RADIUS * 2.4)
# Outlane / inlane guides: vertical midway wall↔sling, curve to the flipper
#   wall | OUTLANE | guide | inlane → flipper | DRAIN | …
OUTLANE_GUIDE_RGB = (100, 110, 130)
OUTLANE_GUIDE_THICK = 0.5         # collision half-width for a true 1px rail
# Vertical top sits this many px above the slingshot top
OUTLANE_GUIDE_ABOVE_SLING = 2.0
# Drop-target banks — vertical columns along the sides (room behind for ball)
DROP_COUNT = 7                    # targets per outer vertical bank
DROP_INNER_COUNT = 5              # second column each side (slightly inboard)
DROP_W = 2.4                      # face width (toward center)
DROP_H = 2.4                      # each target height in the stack
DROP_GAP = 0.75
DROP_BEHIND_GAP = max(3.4, BALL_RADIUS * 2.8)  # wall → bank gap (ball fits)
DROP_COL_GAP = 3.2                # gap between outer and inner columns
# Horizontal row flanking the bottom eject hole (10 px below the hole)
DROP_BOTTOM_LINE_EACH = 3         # targets left of hole + targets right of hole
DROP_BOTTOM_LINE_BELOW = 10.0     # px further down than the bottom saucer
DROP_BOTTOM_LINE_GAP = 3.2        # clear space left/right of the hole center
DROP_RGB = (200, 160, 40)
DROP_EDGE = (120, 90, 20)
DROP_DOWN_RGB = (35, 30, 15)
DROP_RESET_SECONDS = 4.5
# Stand-up targets (single posts — don't drop)
STANDUP_RGB = (180, 60, 160)
STANDUP_LIT = (255, 140, 230)
STANDUP_R = 1.35
# Passive / guide posts (passive, light bounce)
POST_RGB = (90, 95, 110)
POST_R = 1.15
# Center skill ramp — flipper aim target; launches ball into upper bumper cluster
RAMP_BASE_W = 6.0                 # wide end (faces flippers / down-table)
RAMP_TOP_W = 2.0                  # narrow lip (faces up-table)
RAMP_H = 8.0
# Silver metal look (body / edge / bright lip)
RAMP_RGB = (165, 172, 185)
RAMP_EDGE = (210, 218, 230)
RAMP_LIP = (245, 248, 255)
RAMP_SHADE = (110, 118, 130)
RAMP_LAUNCH = 3.55                # upward speed when leaving the lip
RAMP_CLIMB = 0.14                 # extra climb assist while riding up
RAMP_CENTER_PULL = 0.10           # keep ball on the ramp face
# After leaving the lip, ball flies over mid toys (drops/posts/spinners/etc.)
RAMP_AIRBORNE_SECONDS = 0.42
# Spinners (EM reels — spin when hit; multiple sizes on the table)
SPINNER_RGB = (200, 200, 80)
SPINNER_LIT = (255, 255, 140)
SPINNER_R = 2.0                 # default / medium
SPINNER_FRICTION = 0.965
# Top rollover lane switches (3)
ROLLOVER_RGB = (40, 80, 140)
ROLLOVER_LIT = (80, 180, 255)
# Saucer / kick-out holes (network: enter one → vanish → pan → exit another)
SAUCER_RGB = (30, 30, 40)
SAUCER_RIM = (100, 100, 120)
SAUCER_KICK = 2.8
# Tiny trajectory jitter on eject (radians / relative speed)
SAUCER_EJECT_ANGLE_JITTER = 0.18   # ± ~10° around the base kick aim
SAUCER_EJECT_SPEED_JITTER = 0.08   # ±8% kick speed
SAUCER_CAPTURE_R = 2.0
SAUCER_TOP_BELOW_APEX = 5.0 + 3.0  # top hole: was apex+5, moved 3 px lower
SCORE_SAUCER = 100                 # enter any hole → points + teleport to another
SAUCER_VANISH_SECONDS = 0.50       # fade out at entry hole
SAUCER_PAN_SECONDS = 0.45          # camera pan to exit (ball invisible)
# Bottom apron clock — red 7-segment LED digits (medium), world-space strip
# below the flippers (scrolls with the playfield camera)
CLOCK_RGB = (255, 36, 28)           # lit LED red
CLOCK_DIM = (55, 12, 10)            # unlit segment ghost
CLOCK_DIGIT_W = 5
CLOCK_DIGIT_H = 9
CLOCK_THICK = 1
CLOCK_GAP = 1
CLOCK_COLON_W = 2
CLOCK_APRON_H = CLOCK_DIGIT_H + 3   # world strip height below the playfield
CLOCK_APRON_RGB = (12, 8, 10)       # dark apron panel behind the digits
CLOCK_APRON_EDGE = (50, 25, 28)     # thin red-ish rail above apron
# Score — 70s flip-clock style 5-digit display at the top (scrolls with table)
SCORE_DIGITS = 5
SCORE_MAX = 10 ** SCORE_DIGITS - 1
SCORE_BUMPER = 10
SCORE_SLING = 5
SCORE_TARGET = 1                  # rollovers, drop targets, standups
# SCORE_SAUCER defined with saucer constants
# Flip-card face (mirrors LEDarcade GenerateFlipClockImage look)
FLIP_CARD_BG = (0, 0, 0)
FLIP_CARD_FRAME = (40, 40, 40)
FLIP_CARD_SEAM = (96, 96, 96)
FLIP_CARD_LOWER = (8, 8, 8)
FLIP_DIGIT_RGB = (255, 255, 255)
FLIP_DIGIT_W = 3                  # LEDarcade DigitList is 3×5
FLIP_DIGIT_H = 5
FLIP_CARD_PAD_X = 1
FLIP_CARD_PAD_Y = 1
FLIP_CARD_GAP = 1
FLIP_SCORE_Y = 1 - 3              # world y of score strip (moved 3 px up)
# 7-segment masks: bit0=A top, B UR, C LR, D bot, E LL, F UL, G mid
_SEG_A, _SEG_B, _SEG_C, _SEG_D = 0x01, 0x02, 0x04, 0x08
_SEG_E, _SEG_F, _SEG_G = 0x10, 0x20, 0x40
_SEG_DIGIT_MASKS = (
    0x3F,  # 0  ABCDEF
    0x06,  # 1  BC
    0x5B,  # 2  ABDEG
    0x4F,  # 3  ABCDG
    0x66,  # 4  BCFG
    0x6D,  # 5  ACDFG
    0x7D,  # 6  ACDEFG
    0x07,  # 7  ABC
    0x7F,  # 8  ABCDEFG
    0x6F,  # 9  ABCDFG
)

# Colors
BG = (0, 0, 0)
WALL_RGB = (40, 45, 55)
RAIL_RGB = (70, 80, 100)
FLOOR_RGB = (25, 20, 30)
BALL_CORE = (220, 225, 235)
BALL_HIGH = (255, 255, 255)
BALL_SHADE = (110, 120, 140)
FLIPPER_RGB = (200, 40, 40)
FLIPPER_EDGE_RGB = (160, 30, 30)   # darker rim for AA soft edge
FLIPPER_LIP = (255, 110, 85)
DECOR_RGB = (30, 50, 70)
PLUNGER_RGB = (160, 160, 170)
PLUNGER_SPRING = (100, 100, 110)

ScrollSleep = 0.02


def _stop(StopEvent):
    try:
        return StopEvent is not None and StopEvent.is_set()
    except Exception:
        return False


# ---------------- Geometry helpers ----------------

def _clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def _lerp_angle(a, b, t):
    """Shortest-path angle lerp."""
    d = (b - a + math.pi) % (2 * math.pi) - math.pi
    return a + d * _clamp(t, 0.0, 1.0)


def _segment_points(px, py, angle, length):
    tx = px + math.cos(angle) * length
    ty = py + math.sin(angle) * length
    return px, py, tx, ty


def _dist_point_segment(px, py, x1, y1, x2, y2):
    """Distance from point to segment; returns (dist, nearest_x, nearest_y, t)."""
    dx = x2 - x1
    dy = y2 - y1
    den = dx * dx + dy * dy
    if den < 1e-9:
        return math.hypot(px - x1, py - y1), x1, y1, 0.0
    t = ((px - x1) * dx + (py - y1) * dy) / den
    t = _clamp(t, 0.0, 1.0)
    nx = x1 + t * dx
    ny = y1 + t * dy
    return math.hypot(px - nx, py - ny), nx, ny, t


def _draw_line(canvas, x0, y0, x1, y1, rgb, camera_y, thick=0):
    """Bresenham line in world space → screen via camera_y (solid, no AA)."""
    x0, y0, x1, y1 = int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    r, g, b = rgb
    set_px = canvas.SetPixel
    while True:
        sx_s = x0
        sy_s = y0 - int(round(camera_y))
        if 0 <= sx_s < WIDTH and 0 <= sy_s < HEIGHT:
            set_px(sx_s, sy_s, r, g, b)
            if thick:
                for ox, oy in ((1, 0), (0, 1), (-1, 0), (0, -1)):
                    xx, yy = sx_s + ox, sy_s + oy
                    if 0 <= xx < WIDTH and 0 <= yy < HEIGHT:
                        set_px(xx, yy, r, g, b)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def _ipart(x):
    return int(math.floor(x))


def _fpart(x):
    return x - math.floor(x)


def _rfpart(x):
    return 1.0 - _fpart(x)


def _plot_aa(canvas, sx, sy, rgb, cover):
    """Blend rgb onto canvas at integer screen pixel with coverage 0..1."""
    if cover <= 0.02 or not (0 <= sx < WIDTH and 0 <= sy < HEIGHT):
        return
    cover = _clamp(cover, 0.0, 1.0)
    # Soft AA: scale color toward black (panel is black bg) — good enough on LED
    r = int(rgb[0] * cover)
    g = int(rgb[1] * cover)
    b = int(rgb[2] * cover)
    if r | g | b:
        canvas.SetPixel(int(sx), int(sy), r, g, b)


def _draw_aa_line_screen(canvas, x0, y0, x1, y1, rgb):
    """
    Xiaolin Wu anti-aliased line in *screen* pixel space.
    Softens flipper edges on the low-res LED panel.
    """
    steep = abs(y1 - y0) > abs(x1 - x0)
    if steep:
        x0, y0 = y0, x0
        x1, y1 = y1, x1
    if x0 > x1:
        x0, x1 = x1, x0
        y0, y1 = y1, y0

    dx = x1 - x0
    dy = y1 - y0
    gradient = dy / dx if abs(dx) > 1e-9 else 1.0

    # First endpoint
    xend = round(x0)
    yend = y0 + gradient * (xend - x0)
    xgap = _rfpart(x0 + 0.5)
    xpxl1 = int(xend)
    ypxl1 = _ipart(yend)
    if steep:
        _plot_aa(canvas, ypxl1, xpxl1, rgb, _rfpart(yend) * xgap)
        _plot_aa(canvas, ypxl1 + 1, xpxl1, rgb, _fpart(yend) * xgap)
    else:
        _plot_aa(canvas, xpxl1, ypxl1, rgb, _rfpart(yend) * xgap)
        _plot_aa(canvas, xpxl1, ypxl1 + 1, rgb, _fpart(yend) * xgap)
    intery = yend + gradient

    # Second endpoint
    xend = round(x1)
    yend = y1 + gradient * (xend - x1)
    xgap = _fpart(x1 + 0.5)
    xpxl2 = int(xend)
    ypxl2 = _ipart(yend)
    if steep:
        _plot_aa(canvas, ypxl2, xpxl2, rgb, _rfpart(yend) * xgap)
        _plot_aa(canvas, ypxl2 + 1, xpxl2, rgb, _fpart(yend) * xgap)
    else:
        _plot_aa(canvas, xpxl2, ypxl2, rgb, _rfpart(yend) * xgap)
        _plot_aa(canvas, xpxl2, ypxl2 + 1, rgb, _fpart(yend) * xgap)

    # Main loop
    if steep:
        for x in range(xpxl1 + 1, xpxl2):
            y = _ipart(intery)
            _plot_aa(canvas, y, x, rgb, _rfpart(intery))
            _plot_aa(canvas, y + 1, x, rgb, _fpart(intery))
            intery += gradient
    else:
        for x in range(xpxl1 + 1, xpxl2):
            y = _ipart(intery)
            _plot_aa(canvas, x, y, rgb, _rfpart(intery))
            _plot_aa(canvas, x, y + 1, rgb, _fpart(intery))
            intery += gradient


def _draw_aa_flipper_blade(canvas, x0, y0, x1, y1, rgb, edge_rgb, camera_y, half_width=1.15):
    """
    Anti-aliased thick flipper blade: core line + parallel AA edges.
    half_width is in world/screen pixels (≈1–1.5 on 64×32).
    """
    # World → screen
    sx0 = float(x0)
    sy0 = float(y0) - float(camera_y)
    sx1 = float(x1)
    sy1 = float(y1) - float(camera_y)

    dx = sx1 - sx0
    dy = sy1 - sy0
    length = math.hypot(dx, dy) or 1.0
    # Perpendicular unit normal
    nx = -dy / length
    ny = dx / length

    # Soft outer edges (darker) then bright core
    for offset, col, in (
        (-half_width, edge_rgb),
        (half_width, edge_rgb),
        (-half_width * 0.45, rgb),
        (half_width * 0.45, rgb),
        (0.0, rgb),
    ):
        _draw_aa_line_screen(
            canvas,
            sx0 + nx * offset, sy0 + ny * offset,
            sx1 + nx * offset, sy1 + ny * offset,
            col,
        )


def _draw_world_pixel(canvas, wx, wy, rgb, camera_y):
    sx = int(round(wx))
    sy = int(round(wy - camera_y))
    if 0 <= sx < WIDTH and 0 <= sy < HEIGHT:
        canvas.SetPixel(sx, sy, rgb[0], rgb[1], rgb[2])


def _draw_aa_disk(canvas, wx, wy, radius, rgb, camera_y):
    """Soft circular blob (pivot / tip highlights) with radial falloff."""
    cx = wx
    cy = wy - camera_y
    r = max(0.8, float(radius))
    r2 = r * r
    x0 = int(math.floor(cx - r - 1))
    x1 = int(math.ceil(cx + r + 1))
    y0 = int(math.floor(cy - r - 1))
    y1 = int(math.ceil(cy + r + 1))
    for sy in range(y0, y1 + 1):
        for sx in range(x0, x1 + 1):
            d2 = (sx + 0.5 - cx) ** 2 + (sy + 0.5 - cy) ** 2
            if d2 > r2:
                continue
            # Smooth coverage at the rim
            d = math.sqrt(d2)
            cover = 1.0 if d <= r - 0.65 else _clamp(1.0 - (d - (r - 0.65)) / 0.65, 0.0, 1.0)
            _plot_aa(canvas, sx, sy, rgb, cover)


# ---------------- Flipper ----------------

class Flipper:
    def __init__(
        self, pivot_x, pivot_y, rest_angle, active_angle, length, side,
        swing_speed=None, power=None,
    ):
        self.px = float(pivot_x)
        self.py = float(pivot_y)
        self.rest = float(rest_angle)
        self.active = float(active_angle)
        self.length = float(length)
        self.side = side  # "left" or "right"
        self.swing_speed = float(
            FLIPPER_SWING_SPEED if swing_speed is None else swing_speed
        )
        self.power = float(FLIPPER_POWER if power is None else power)
        self.angle = float(rest_angle)
        self.target = float(rest_angle)
        self.omega = 0.0  # rad/frame (for hit impulse)
        self.pressed = False

    def set_pressed(self, pressed):
        self.pressed = bool(pressed)
        self.target = self.active if self.pressed else self.rest

    def update(self):
        prev = self.angle
        # Move toward target with capped step
        d = (self.target - self.angle + math.pi) % (2 * math.pi) - math.pi
        step = _clamp(d, -self.swing_speed, self.swing_speed)
        self.angle += step
        self.omega = self.angle - prev

    def endpoints(self):
        return _segment_points(self.px, self.py, self.angle, self.length)

    def tip(self):
        _, _, tx, ty = self.endpoints()
        return tx, ty

    def draw(self, canvas, camera_y):
        x1, y1, x2, y2 = self.endpoints()
        # Anti-aliased thick blade (core + soft edges)
        _draw_aa_flipper_blade(
            canvas, x1, y1, x2, y2,
            FLIPPER_RGB, FLIPPER_EDGE_RGB, camera_y,
            half_width=1.25,
        )
        # Soft pivot + tip caps
        _draw_aa_disk(canvas, x1, y1, 1.35, FLIPPER_LIP, camera_y)
        _draw_aa_disk(canvas, x2, y2, 1.05, FLIPPER_LIP, camera_y)


# ---------------- Ball ----------------

class Ball:
    def __init__(self, x, y, vx=0.0, vy=0.0):
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.alive = True
        self.in_plunger = True  # right-hand launch lane
        self.visible = 1.0      # 0..1 (saucer vanish fade)
        self.airborne = 0       # frames of ramp-jump (skip mid toys)

    def speed(self):
        return math.hypot(self.vx, self.vy)

    def place_in_plunger(self):
        """Seat the ball at the bottom of the right-hand plunger lane."""
        lane_x = MAP_W - 1.5
        self.x = float(lane_x)
        self.y = float(_playfield_bottom() - 6.0)
        self.vx = 0.0
        self.vy = 0.0
        self.alive = True
        self.in_plunger = True
        self.visible = 1.0
        self.airborne = 0

    def fire_plunger(self, power=None):
        """Launch up the plunger lane (traditional plunger)."""
        p = PLUNGER_POWER if power is None else float(power)
        # Stable launch — tiny horizontal only (no random power jitter)
        self.vx = -0.02
        self.vy = -abs(p)
        self.in_plunger = True
        self.alive = True
        self.visible = 1.0
        self.airborne = 0

    def is_airborne(self):
        """True while jumping off a ramp (ignores nearby obstacles)."""
        return int(getattr(self, "airborne", 0)) > 0

    def launch(self, x=None, y=None):
        """Compatibility: seat for plunger (fire happens in main loop)."""
        self.place_in_plunger()

    def integrate(self, dt_scale=1.0):
        """Advance physics by dt_scale (1.0 = one full frame; use 1/N in substeps)."""
        if self.in_plunger and abs(self.vy) < 0.01 and abs(self.vx) < 0.01:
            # Sitting on the plunger — no free motion until fired
            return
        s = float(dt_scale)
        self.vy += GRAVITY * s
        # Air drag per substep so full-frame damping stays similar
        drag = AIR_DRAG ** s
        self.vx *= drag
        self.vy *= drag
        sp = self.speed()
        # Playfield is capped at MAX_SPEED; plunger lane allows full launch power
        # so the ball can still clear the chute after the 25% playfield slowdown.
        speed_cap = PLUNGER_LANE_MAX_SPEED if self.in_plunger else MAX_SPEED
        if sp > speed_cap:
            k = speed_cap / sp
            self.vx *= k
            self.vy *= k
        self.x += self.vx * s
        self.y += self.vy * s

    def draw(self, canvas, camera_y):
        """Draw ball in view; never place pixels outside the panel."""
        vis = float(getattr(self, "visible", 1.0))
        if vis <= 0.02:
            return
        # Use rounded world→screen without fighting the camera (camera already tracks)
        cx = int(round(self.x))
        cy = int(round(self.y - camera_y))
        # Safety only — should rarely engage if camera is correct
        cy = _clamp(cy, VIEW_EDGE_MARGIN, HEIGHT - 1 - VIEW_EDGE_MARGIN)
        cx = _clamp(cx, 1, WIDTH - 2)
        # 3×3 silver blob with highlight / shade (dimmed by visible for saucer vanish)
        offsets = (
            (0, 0, BALL_CORE),
            (1, 0, BALL_CORE),
            (-1, 0, BALL_SHADE),
            (0, 1, BALL_SHADE),
            (0, -1, BALL_HIGH),
            (1, -1, BALL_HIGH),
            (-1, 1, BALL_SHADE),
        )
        set_px = canvas.SetPixel
        for ox, oy, rgb in offsets:
            sx, sy = cx + ox, cy + oy
            if 0 <= sx < WIDTH and 0 <= sy < HEIGHT:
                set_px(
                    sx, sy,
                    int(rgb[0] * vis),
                    int(rgb[1] * vis),
                    int(rgb[2] * vis),
                )


# ---------------- World / camera ----------------

def _lane_left_x():
    """World x of the wall separating main table from the plunger lane."""
    return float(MAP_W - PLUNGER_LANE_W - 1)


def _top_arc():
    """
    Circular arc ceiling over the main playfield (not the plunger lane).

    Center is below the apex so the ball rolls on the *inside* of the upper
    semicircle. Returns (cx, cy, radius, left_x, right_x).
    """
    left_x = 1.0
    right_x = _lane_left_x() - 0.5
    span = max(8.0, right_x - left_x)
    cx = 0.5 * (left_x + right_x)
    # Full semicircle from left wall to right wall (equator at side posts)
    radius = span * 0.5 + 0.35
    # Apex of the arc at WORLD_TOP_PAD
    cy = float(WORLD_TOP_PAD) + radius
    return cx, cy, radius, left_x, right_x


def _plunger_exit_pose():
    """
    World point where the plunger lane feeds the ball into the playfield.

    Chosen on the *inside* of the top arc (right side, slightly below apex
    toward the equator) so the ball never pops outside the curve.
    """
    cx, cy, radius, left_x, right_x = _top_arc()
    # Angle from center: 0 = right equator, -pi/2 = apex. ~-0.55 rad is inside.
    a = -0.55
    inset = BALL_RADIUS + PLUNGER_EXIT_INSET
    ex = cx + (radius - inset) * math.cos(a)
    ey = cy + (radius - inset) * math.sin(a)
    # Keep left of the lane wall so we are clearly in the main field
    lane_l = _lane_left_x()
    ex = min(ex, lane_l - BALL_RADIUS - 0.6)
    ex = max(ex, left_x + BALL_RADIUS + 0.5)
    return float(ex), float(ey)


def _plunger_exit_y():
    """Y threshold: ball high enough in the lane to transfer into the field."""
    _ex, ey = _plunger_exit_pose()
    # Start the handoff a bit below the final pose so motion eases in
    return float(ey + 3.5)


def plunger_min_exit_power():
    """
    Minimum upward launch speed so the ball reaches the chute exit under
    gravity + air drag (with a small safety margin). Every fire is floored
    at this value so launches always leave the plunger lane.
    """
    start_y = float(_playfield_bottom() - 4.0)
    climb = max(8.0, start_y - _plunger_exit_y())
    # Ideal ballistic: v = sqrt(2 g h); pad for drag / substep integration
    base = math.sqrt(max(0.0, 2.0 * GRAVITY * climb))
    # ~6.0 clears a 7×-tall 64px table in sim; keep a modest cushion
    return float(max(base * 1.06 + 0.20, PLUNGER_POWER * 0.92))


def plunger_power_for_strength(strength, floor_power=None):
    """
    Map pull strength [0..1] → launch speed.

    Soft pulls just clear the chute; full pulls hit PLUNGER_POWER (and a
    little beyond on retries). Never returns below the exit floor.
    """
    s = _clamp(float(strength), 0.0, 1.0)
    floor_p = plunger_min_exit_power() if floor_power is None else float(floor_power)
    top_p = max(floor_p, PLUNGER_POWER * 1.05)
    return float(floor_p + (top_p - floor_p) * s)


def _ball_y_min():
    """Highest the ball may go — just under the arc apex (inside the curve)."""
    cx, cy, radius, _, _ = _top_arc()
    return float(cy - radius + BALL_RADIUS + 0.5)


def _playfield_bottom():
    """
    World y of the bottom of the active playfield (top edge of the clock apron).

    The apron strip [playfield_bottom .. MAP_H) is display-only and scrolls
    with the camera; the ball drains at this line rather than into the digits.
    """
    return float(MAP_H - CLOCK_APRON_H)


def _ball_y_max():
    """Lowest the ball may go before drain logic (main field)."""
    return float(_playfield_bottom() - WORLD_BOTTOM_PAD - BALL_RADIUS - 1.0)


def _arc_inside_limit():
    """Max distance from arc center for the ball center (inside surface)."""
    _cx, _cy, radius, _, _ = _top_arc()
    return radius - BALL_RADIUS


def ensure_ball_inside_arc(ball):
    """
    Soft constraint: while near the top arc, keep the ball on the inside.
    Does not yank the ball from deep in the playfield (only upper region).
    """
    if ball.in_plunger:
        return
    cx, cy, radius, left_x, right_x = _top_arc()
    if ball.y > cy + 1.0:
        return
    if ball.x < left_x - 1.0 or ball.x > right_x + 1.5:
        return
    dx = ball.x - cx
    dy = ball.y - cy
    dist = math.hypot(dx, dy)
    if dist < 1e-6:
        return
    limit = radius - BALL_RADIUS
    if dist > limit + ARC_SLOP:
        # Project smoothly onto the inner surface
        nx, ny = dx / dist, dy / dist
        ball.x = cx + nx * limit
        ball.y = cy + ny * limit
        vn = ball.vx * nx + ball.vy * ny
        if vn > 0.0:
            # Kill outward component only (no hard bounce impulse here)
            ball.vx -= vn * nx
            ball.vy -= vn * ny


def collide_top_arc(ball):
    """
    Ball rolls on the *inside* of the top arc.

    Soft projection + remove outward velocity + keep tangential roll.
    Tuned for low jitter (slop + gentle restitution).
    """
    if ball.in_plunger:
        return False
    cx, cy, radius, left_x, right_x = _top_arc()
    # Upper half of the circle only (ceiling)
    if ball.y > cy + 1.5:
        return False
    if ball.x < left_x - 1.0 or ball.x > right_x + 1.5:
        return False

    limit = radius - BALL_RADIUS
    hit = False
    for _ in range(3):
        dx = ball.x - cx
        dy = ball.y - cy
        dist = math.hypot(dx, dy)
        if dist < 1e-6:
            break

        nx, ny = dx / dist, dy / dist
        # Inside with slop — only strip outward velocity if pressing into the rail
        if dist <= limit + ARC_SLOP:
            vn = ball.vx * nx + ball.vy * ny
            if vn > 0.0:
                ball.vx -= vn * nx * (0.85 + 0.15 * ARC_BOUNCE)
                ball.vy -= vn * ny * (0.85 + 0.15 * ARC_BOUNCE)
                hit = True
            # Light tangent damping while in contact band
            if dist >= limit - ARC_SLOP:
                tx, ty = -ny, nx
                vt = ball.vx * tx + ball.vy * ty
                vn2 = ball.vx * nx + ball.vy * ny
                if vn2 > 0.0:
                    vn2 = 0.0
                ball.vx = nx * vn2 + tx * vt * ARC_TANGENT_FRICTION
                ball.vy = ny * vn2 + ty * vt * ARC_TANGENT_FRICTION
            break

        # Outside the inner surface — project back inside
        ball.x = cx + nx * limit
        ball.y = cy + ny * limit
        hit = True

        vn = ball.vx * nx + ball.vy * ny
        if vn > 0.0:
            # Soft bounce (not 1+e full reflection — avoids buzz)
            ball.vx -= (1.0 + ARC_BOUNCE * 0.65) * vn * nx
            ball.vy -= (1.0 + ARC_BOUNCE * 0.65) * vn * ny
        tx, ty = -ny, nx
        vt = ball.vx * tx + ball.vy * ty
        vn2 = ball.vx * nx + ball.vy * ny
        if vn2 > 0.0:
            vn2 = 0.0
        ball.vx = nx * vn2 + tx * vt * ARC_TANGENT_FRICTION
        ball.vy = ny * vn2 + ty * vt * ARC_TANGENT_FRICTION
    return hit


def force_plunger_exit(ball, retain_speed=True):
    """
    Always hand the ball out of the chute into the playfield (inside the
    top arc). Used for normal high-lane exits and as a guarantee when the
    ball crests in the lane without quite hitting the soft threshold.
    """
    if not ball.in_plunger:
        return False
    ex, ey = _plunger_exit_pose()
    # Blend toward the exit pose so it doesn't teleport hard
    ball.x += (ex - ball.x) * 0.70
    ball.y += (ey - ball.y) * 0.65
    # Snap if still far (guarantees leave-chute even from a short crest)
    if abs(ball.x - ex) > 2.5:
        ball.x = ex
    if abs(ball.y - ey) > 3.5:
        ball.y = ey
    ball.in_plunger = False
    # Feed into the field along the inside of the arc (left + slight up)
    if retain_speed:
        ball.vx = min(ball.vx, 0.0) - 0.85
        # Keep some upward momentum if still climbing; else a gentle feed
        if ball.vy < -0.2:
            ball.vy = min(ball.vy, -0.4)
        else:
            ball.vy = min(ball.vy, 0.0) - 0.55
    else:
        ball.vx = -0.9
        ball.vy = -0.6
    ensure_ball_inside_arc(ball)
    collide_top_arc(ball)
    return True


def try_plunger_exit(ball):
    """
    When the ball reaches the top of the plunger lane, hand it off into the
    main playfield at a point *inside* the top arc (never outside the curve).
    """
    if not ball.in_plunger:
        return False
    exit_y = _plunger_exit_y()
    # Soft window: at / above exit, or cresting just below it
    near_exit = ball.y <= exit_y + 2.5
    cresting = ball.vy >= -0.05 and ball.y <= exit_y + 8.0
    if not near_exit and not cresting:
        return False
    # Reject only if still deep in the lane and falling hard (not at exit)
    if ball.y > exit_y + 2.5 and ball.vy > 0.55:
        return False
    return force_plunger_exit(ball, retain_speed=True)


def draw_top_arc(canvas, camera_y):
    """Draw the curved top rail (AA samples along the upper semicircle)."""
    cx, cy, radius, left_x, right_x = _top_arc()
    # Angles: pi (left) → 3π/2 (apex) → 2π (right)  — upper semicircle only
    # Point: (cx + R*cos(a), cy + R*sin(a))
    a0 = math.pi
    a1 = 2.0 * math.pi
    steps = max(28, int(radius * 2.8))
    prev = None
    for i in range(steps + 1):
        t = i / float(steps)
        a = a0 + (a1 - a0) * t
        wx = cx + radius * math.cos(a)
        wy = cy + radius * math.sin(a)
        if left_x - 0.5 <= wx <= right_x + 0.5:
            if prev is not None:
                _draw_aa_flipper_blade(
                    canvas, prev[0], prev[1], wx, wy,
                    ARC_RGB, (ARC_RGB[0] // 2, ARC_RGB[1] // 2, ARC_RGB[2] // 2),
                    camera_y, half_width=0.85,
                )
            prev = (wx, wy)
        else:
            prev = None
    # Apex highlight
    apex_x, apex_y = cx, cy - radius
    _draw_aa_disk(canvas, apex_x, apex_y, 1.1, ARC_HIGHLIGHT, camera_y)


def camera_for_ball(ball_y, prev_camera=None):
    """
    Vertical camera so the ball stays on-screen and clear of top/bottom edges.

    Smooth follow with soft catch-up near the view edges (avoids jittery snaps).
    """
    margin = float(VIEW_EDGE_MARGIN)
    ideal = ball_y - HEIGHT * 0.48
    cam_lo = ball_y - (HEIGHT - margin)
    cam_hi = ball_y - margin
    target = _clamp(ideal, cam_lo, cam_hi)
    world_lo = 0.0
    world_hi = max(0.0, float(MAP_H - HEIGHT))
    target = _clamp(target, world_lo, world_hi)

    if prev_camera is None:
        return target
    prev = float(prev_camera)
    screen_y = ball_y - prev
    # Soft edge band: ease faster only when close to leaving the view
    edge = margin + 2.0
    if screen_y < edge or screen_y > HEIGHT - edge:
        alpha = CAMERA_CATCHUP
    else:
        alpha = CAMERA_FOLLOW
    return prev + (target - prev) * alpha


def clamp_ball_on_table(ball):
    """Keep ball inside the playable world (arc handles the curved top)."""
    # Drain at playfield bottom (above the scrolling clock apron)
    pf_bot = _playfield_bottom()
    if not ball.in_plunger and ball.y > pf_bot + 2:
        ball.alive = False
        return
    if ball.in_plunger and ball.y > pf_bot - 3.5:
        ball.y = pf_bot - 3.5
        ball.vy = min(0.0, ball.vy)
    # Soft apex guard (inside arc)
    ensure_ball_inside_arc(ball)


def collide_walls(ball):
    r = BALL_RADIUS
    lane_l = _lane_left_x()
    pf_bot = _playfield_bottom()

    if ball.in_plunger:
        # Constrain to right-hand lane until exit into the arc/playfield
        if ball.x < lane_l + r + 0.2:
            ball.x = lane_l + r + 0.2
            if ball.vx < 0:
                ball.vx = 0.0
        if ball.x > MAP_W - 1.2 - r:
            ball.x = MAP_W - 1.2 - r
            ball.vx = -abs(ball.vx) * BOUNCE * 0.4
        # Bottom of lane (plunger cup) — playfield bottom, not into apron
        if ball.y > pf_bot - 4.0:
            ball.y = pf_bot - 4.0
            ball.vy = min(0.0, ball.vy)
        # Hand off into playfield inside the top arc
        try_plunger_exit(ball)
        return

    # --- Main playfield ---
    if ball.x < r + 1:
        ball.x = r + 1
        if ball.vx < 0:
            ball.vx = -ball.vx * BOUNCE
    # Right side: bounce off lane wall (opening only near top exit)
    if ball.x > lane_l - r:
        ex, ey = _plunger_exit_pose()
        # Allow free motion only near the designed exit height
        if ball.y > ey + 5.0:
            ball.x = lane_l - r
            if ball.vx > 0:
                ball.vx = -ball.vx * BOUNCE
        elif ball.x > MAP_W - 1.2 - r:
            ball.x = MAP_W - 1.2 - r
            ball.vx = -abs(ball.vx) * BOUNCE
    # Curved top rail — ball on the *inside*
    collide_top_arc(ball)
    ensure_ball_inside_arc(ball)
    # Drain below flippers (not in plunger)
    if ball.y > MAP_H + 4:
        ball.alive = False


def collide_flipper(ball, flipper):
    """
    Ball vs flipper segment.

    Stationary flipper → bounce only (no free energy). Swinging flipper
    (nonzero omega) imparts bat velocity / FLIPPER_POWER along the swing.
    """
    x1, y1, x2, y2 = flipper.endpoints()
    dist, nx, ny, t = _dist_point_segment(ball.x, ball.y, x1, y1, x2, y2)
    hit_r = BALL_RADIUS + FLIPPER_THICK * 0.5 + FLIPPER_PAD
    if dist >= hit_r or dist < 1e-6:
        return False

    # Surface normal from segment toward ball
    sx, sy = x2 - x1, y2 - y1
    nlen = math.hypot(sx, sy) or 1.0
    n1x, n1y = -sy / nlen, sx / nlen
    n2x, n2y = sy / nlen, -sx / nlen
    to_bx, to_by = ball.x - nx, ball.y - ny
    if n1x * to_bx + n1y * to_by >= n2x * to_bx + n2y * to_by:
        nnx, nny = n1x, n1y
    else:
        nnx, nny = n2x, n2y

    # Push out of the solid blade
    pen = hit_r - dist
    ball.x += nnx * pen
    ball.y += nny * pen

    speed = ball.speed()
    # Cradle: resting flipper holds a slow ball instead of batting it away
    if (not flipper.pressed) and speed < FLIP_HOLD_SPEED and 0.05 <= t <= 0.98:
        vn = ball.vx * nnx + ball.vy * nny
        if vn < 0:
            ball.vx -= vn * nnx
            ball.vy -= vn * nny
        tx, ty = (x2 - x1), (y2 - y1)
        tl = math.hypot(tx, ty) or 1.0
        tx, ty = tx / tl, ty / tl
        vt = ball.vx * tx + ball.vy * ty
        ball.vx = tx * vt * 0.88
        ball.vy = ty * vt * 0.88 + 0.02
        return True

    # Always: elastic-ish bounce off the solid bat (no energy added yet)
    vn = ball.vx * nnx + ball.vy * nny
    if vn < 0:
        ball.vx -= (1.0 + BOUNCE) * vn * nnx
        ball.vy -= (1.0 + BOUNCE) * vn * nny

    # Active hit only while the flipper is *moving* (swinging omega).
    # Held-still raised bats do not give free power.
    omega_eps = 0.04
    if abs(flipper.omega) > omega_eps:
        tip_scale = 0.55 + 0.75 * _clamp(t, 0.0, 1.0)
        rx, ry = nx - flipper.px, ny - flipper.py
        fvx = -flipper.omega * ry
        fvy = flipper.omega * rx
        # Only add energy when the bat face is swinging into the ball
        bat_into_ball = fvx * nnx + fvy * nny
        if bat_into_ball > 0.0:
            f_power = float(getattr(flipper, "power", FLIPPER_POWER))
            f_swing = float(getattr(flipper, "swing_speed", FLIPPER_SWING_SPEED))
            swing = abs(flipper.omega) / max(1e-3, f_swing)
            power = f_power * tip_scale * (0.45 + 0.55 * _clamp(swing, 0.0, 1.2))
            ball.vx += fvx * power
            ball.vy += fvy * power - abs(flipper.omega) * f_power * tip_scale * 0.55

    # Cap
    sp = ball.speed()
    if sp > MAX_SPEED:
        s = MAX_SPEED / sp
        ball.vx *= s
        ball.vy *= s
    return True


def _ball_flipper_contact(ball, flipper):
    """
    If the ball is near the flipper blade, return (t, dist) where t is
    0 at the pivot and 1 at the tip. Otherwise (None, None).
    """
    x1, y1, x2, y2 = flipper.endpoints()
    dist, _nx, _ny, t = _dist_point_segment(ball.x, ball.y, x1, y1, x2, y2)
    if dist <= FLIP_CATCH_DIST and -0.05 <= t <= 1.05:
        return _clamp(t, 0.0, 1.0), dist
    return None, None


def _pick_shot_t():
    """
    Choose where along the flipper to release (base / mid / tip).

    Bias toward tip/mid so bottom flippers often feed the center skill ramp
    (path up the middle into the upper bumper cluster).
    """
    r = random.random()
    if r < 0.18:
        return random.uniform(FLIP_BASE_T - 0.06, FLIP_BASE_T + 0.08)  # short
    if r < 0.48:
        return random.uniform(FLIP_MID_T - 0.08, FLIP_MID_T + 0.10)    # medium
    return random.uniform(FLIP_TIP_T - 0.06, min(0.95, FLIP_TIP_T + 0.08))  # long → ramp


# ---------------- Auto flipper AI (hold + timed shots) ----------------

def update_flipper_ai(ball, left, right, frame, ai_state=None):
    """
    Skill-style flipper control:

      • Catch / cradle a slow ball on the resting blade
      • Hold until the ball rolls to a chosen point along the flipper
      • Flip at base / mid / tip for different shot strengths
      • Reactive flip if the ball is falling fast onto the blade
      • Light idle flex when the ball is high on the table
    """
    if ai_state is None:
        ai_state = {}

    def _side_ai(flipper, key):
        st = ai_state.setdefault(key, {
            "mode": "idle",       # idle | cradle | flip
            "target_t": FLIP_MID_T,
            "flip_timer": 0,
            "cooldown": 0,
        })
        if st["cooldown"] > 0:
            st["cooldown"] -= 1

        t, dist = _ball_flipper_contact(ball, flipper)
        on_blade = t is not None
        slow = ball.speed() < FLIP_HOLD_SPEED
        approaching = ball.vy > -0.05  # falling or settling

        # High on table → no action (idle flex handled outside)
        if ball.y < MAP_H - HEIGHT * 0.85 and not on_blade:
            st["mode"] = "idle"
            return False

        if st["mode"] == "flip":
            st["flip_timer"] -= 1
            if st["flip_timer"] <= 0:
                st["mode"] = "idle"
                st["cooldown"] = 8
                return False
            return True  # keep raised briefly

        if st["cooldown"] > 0 and not on_blade:
            return False

        if on_blade and approaching:
            # Fast drop onto flipper → emergency slap save
            if ball.speed() > 1.6 and ball.vy > 0.4:
                st["mode"] = "flip"
                st["flip_timer"] = 7
                st["target_t"] = max(t, 0.5)
                return True

            if slow or st["mode"] == "cradle":
                # Cradle: hold rest, wait for ball to roll to target_t
                if st["mode"] != "cradle":
                    st["mode"] = "cradle"
                    st["target_t"] = _pick_shot_t()
                # Ball rolling toward tip (t increasing for left? depends on side)
                # Release when at or past target, or starting to fall off tip/base
                if t >= st["target_t"] - 0.04:
                    st["mode"] = "flip"
                    st["flip_timer"] = 8
                    return True
                if t > 0.92 or (t < 0.08 and ball.speed() > 0.4):
                    # About to lose the ball — flip now
                    st["mode"] = "flip"
                    st["flip_timer"] = 7
                    return True
                return False  # hold rest = cradle

            # Medium speed on blade — timed flip by location
            st["mode"] = "flip"
            st["flip_timer"] = 7
            st["target_t"] = t
            return True

        # Ball in catch zone above flipper but not touching yet
        x1, y1, x2, y2 = flipper.endpoints()
        tip_x, tip_y = x2, y2
        mid_x = 0.5 * (x1 + x2)
        mid_y = 0.5 * (y1 + y2)
        if (
            ball.y > min(y1, y2) - 12
            and ball.y < max(y1, y2) + 4
            and abs(ball.x - mid_x) < FLIPPER_LEN * 0.95
            and ball.vy > 0.15
            and ball.speed() > 1.1
        ):
            # Late reactive flip as ball drops in
            st["mode"] = "flip"
            st["flip_timer"] = 6
            return True

        st["mode"] = "idle"
        return False

    left_want = _side_ai(left, "L")
    right_want = _side_ai(right, "R")

    # Idle flex when ball is high — slow alternate flaps
    if ball.y < MAP_H - HEIGHT * 1.15 and not left_want and not right_want:
        phase = (frame // 22) % 6
        if phase == 0:
            left_want = True
        elif phase == 3:
            right_want = True

    left.set_pressed(left_want)
    right.set_pressed(right_want)
    return ai_state


def update_upper_flipper_ai(ball, left, right, frame, ai_state=None):
    """
    Aggressive, accurate upper-side flipper control.

    Unlike the bottom AI (which idles when the ball is high), these bats live
    in the top third and must always track nearby balls:
      • Wide intercept zone with velocity look-ahead
      • Early pre-fire so the bat is swinging on contact
      • Minimal cradle — prefer hard saves / redirects
      • Prefer tip shots into the center of the upper field
    """
    if ai_state is None:
        ai_state = {}

    def _predict(frames=3.0):
        # Simple ballistic peek (ignore drag)
        return (
            ball.x + ball.vx * frames,
            ball.y + ball.vy * frames + 0.5 * GRAVITY * frames * frames,
        )

    def _side_ai(flipper, key):
        st = ai_state.setdefault(key, {
            "mode": "idle",
            "flip_timer": 0,
            "cooldown": 0,
        })
        if st["cooldown"] > 0:
            st["cooldown"] -= 1

        catch = UPPER_FLIP_CATCH_DIST
        x1, y1, x2, y2 = flipper.endpoints()
        mid_x = 0.5 * (x1 + x2)
        mid_y = 0.5 * (y1 + y2)
        tip_x, tip_y = x2, y2
        # Contact on current blade
        dist, _qx, _qy, t = _dist_point_segment(ball.x, ball.y, x1, y1, x2, y2)
        on_blade = dist <= catch and -0.08 <= t <= 1.08
        t = _clamp(t, 0.0, 1.0)

        # Predicted intercept
        px, py = _predict(UPPER_FLIP_LOOKAHEAD * 0.35)
        pdist, _pqx, _pqy, pt = _dist_point_segment(px, py, x1, y1, x2, y2)
        will_hit = pdist <= catch * 1.25 and -0.1 <= pt <= 1.12

        # Zone around this flipper (generous)
        near_x = abs(ball.x - mid_x) < flipper.length * 1.35
        near_y = (ball.y > min(y1, y2, tip_y) - UPPER_FLIP_REACT_Y
                  and ball.y < max(y1, y2, tip_y) + 8.0)
        in_zone = near_x and near_y

        if st["mode"] == "flip":
            st["flip_timer"] -= 1
            if st["flip_timer"] <= 0:
                st["mode"] = "idle"
                st["cooldown"] = 3  # short cooldown — stay aggressive
                return False
            return True

        if st["cooldown"] > 0 and not on_blade and not will_hit:
            return False

        # Already on the bat — slap hard, especially tip/mid
        if on_blade:
            # Any speed on upper bats → fire (minimal cradle)
            st["mode"] = "flip"
            st["flip_timer"] = 9
            return True

        # Pre-fire: ball on a path to the blade — start the swing early
        if will_hit and (ball.vy > -0.15 or ball.speed() > 0.9):
            st["mode"] = "flip"
            st["flip_timer"] = 10
            return True

        # Reactive: falling into the intercept corridor
        if in_zone and ball.vy > 0.08 and ball.speed() > 0.55:
            # On the correct side of the bat's swing arc
            if flipper.side == "left" and ball.x < mid_x + flipper.length * 0.55:
                st["mode"] = "flip"
                st["flip_timer"] = 8
                return True
            if flipper.side == "right" and ball.x > mid_x - flipper.length * 0.55:
                st["mode"] = "flip"
                st["flip_timer"] = 8
                return True

        # High-speed lateral save near tip
        if (
            in_zone
            and ball.speed() > 1.8
            and abs(ball.x - tip_x) < flipper.length * 0.85
            and abs(ball.y - tip_y) < UPPER_FLIP_REACT_Y * 0.7
        ):
            st["mode"] = "flip"
            st["flip_timer"] = 8
            return True

        st["mode"] = "idle"
        return False

    left_want = _side_ai(left, "UL")
    right_want = _side_ai(right, "UR")

    # No idle flex — upper bats only move when the ball is a threat
    left.set_pressed(left_want)
    right.set_pressed(right_want)
    return ai_state


# ---------------- Decor / rails / bumpers / drop targets / clock ----------------

def _pop_bumpers():
    """
    Classic EM pop bumpers:

      • Upper triangle under the top curve (1 high center + 2 lower flanks)
      • Side midfield pair near the left/right rails — bounce the ball
        back into the middle when it hugs a wall at mid-table

    Returns list of (x, y, radius).
    """
    lane_l = _lane_left_x()
    play_w = max(10.0, lane_l - 2.0)
    _cx, cy, radius, _, _ = _top_arc()
    # Cluster sits in the upper third of the main field, clear of the arc rail
    y_hi = float(cy - radius * 0.22)
    y_lo = y_hi + 7.5
    cx = play_w * 0.48
    # Mid-table side thumpers (classic wall-hug pop bumpers)
    mid_y = MAP_H * 0.50
    mid_y2 = MAP_H * 0.56
    side_inset = max(3.5, BUMPER_R + 1.8)
    return (
        (cx, y_hi, BUMPER_R * 1.05),                 # top center
        (play_w * 0.30, y_lo, BUMPER_R),             # lower left (upper cluster)
        (play_w * 0.68, y_lo, BUMPER_R),             # lower right (upper cluster)
        (side_inset, mid_y, BUMPER_R * 0.95),        # left mid-side
        (play_w - side_inset, mid_y, BUMPER_R * 0.95),  # right mid-side
        (side_inset + 1.2, mid_y2, BUMPER_R * 0.85), # left lower-mid side
        (play_w - side_inset - 1.2, mid_y2, BUMPER_R * 0.85),  # right lower-mid side
    )


# Back-compat name used elsewhere
def _top_bumpers():
    return _pop_bumpers()


def build_skill_ramps():
    """
    Two silver skill ramps (same size as before), mid-table, separated by at
    least 10 px between bases. Bottom flippers feed either; lips launch into
    the upper pop-bumper cluster.

    Returns list of ramp dicts for draw/collide.
    """
    lane_l = _lane_left_x()
    play_w = max(12.0, lane_l - 2.0)
    mid_cx = play_w * 0.48
    # Edge-to-edge gap >= 10 → center spacing >= base_w + 10
    center_sep = max(RAMP_BASE_W + 10.0, 16.0)
    left_cx = mid_cx - 0.5 * center_sep
    right_cx = mid_cx + 0.5 * center_sep
    # Empty-ish band: above flipper/sling zone, below big mid spinner cluster
    bottom_y = float(_playfield_bottom() * 0.68)
    top_y = bottom_y - RAMP_H
    _cx, cy, radius, _, _ = _top_arc()
    bumper_y = float(cy - radius * 0.22) + 4.0
    bumper_x = play_w * 0.48
    aim = (float(bumper_x), float(bumper_y))
    ramps = []
    for cx in (left_cx, right_cx):
        ramps.append({
            "cx": float(cx),
            "top_y": float(top_y),
            "bottom_y": float(bottom_y),
            "top_w": float(RAMP_TOP_W),
            "base_w": float(RAMP_BASE_W),
            "aim": aim,
        })
    return ramps


def build_center_ramp():
    """Back-compat: first of the dual skill ramps."""
    rs = build_skill_ramps()
    return rs[0] if rs else None


def _ramp_half_width(ramp, y):
    """Half-width of trapezoid at world y (0 at top lip → base at bottom)."""
    top_y = ramp["top_y"]
    bot_y = ramp["bottom_y"]
    if bot_y <= top_y:
        return 0.5 * ramp["base_w"]
    t = _clamp((y - top_y) / (bot_y - top_y), 0.0, 1.0)
    w = ramp["top_w"] + (ramp["base_w"] - ramp["top_w"]) * t
    return 0.5 * w


def draw_ramp(canvas, camera_y, ramp):
    """Draw the silver trapezoid skill ramp (base toward flippers, lip toward top)."""
    if not ramp:
        return
    cx = ramp["cx"]
    top_y = ramp["top_y"]
    bot_y = ramp["bottom_y"]
    h = max(1.0, bot_y - top_y)
    # Fill scanlines of the trapezoid with metallic gradient
    y0 = int(math.floor(top_y))
    y1 = int(math.ceil(bot_y))
    for yi in range(y0, y1 + 1):
        t = _clamp((yi + 0.5 - top_y) / h, 0.0, 1.0)
        hw = _ramp_half_width(ramp, float(yi) + 0.5)
        x0 = int(math.floor(cx - hw))
        x1 = int(math.ceil(cx + hw))
        for xi in range(x0, x1 + 1):
            # Edge highlight vs body; left edge a bit brighter (specular)
            on_left = abs(xi - (cx - hw)) < 0.7
            on_right = abs(xi - (cx + hw)) < 0.7
            on_bot = yi >= y1 - 0
            if yi == y0:
                rgb = RAMP_LIP
            elif on_left:
                rgb = RAMP_EDGE
            elif on_right or on_bot:
                rgb = RAMP_SHADE
            else:
                # Subtle top→bottom silver falloff
                k = 1.0 - 0.22 * t
                rgb = (
                    int(RAMP_RGB[0] * k),
                    int(RAMP_RGB[1] * k),
                    int(RAMP_RGB[2] * k),
                )
            _draw_world_pixel(canvas, xi, yi, rgb, camera_y)
    # Bright lip at the top (launch edge) — specular highlight row
    thw = 0.5 * ramp["top_w"]
    lip_y = int(round(top_y))
    for xi in range(int(math.floor(cx - thw)), int(math.ceil(cx + thw)) + 1):
        _draw_world_pixel(canvas, xi, lip_y, RAMP_LIP, camera_y)
        if lip_y + 1 <= y1:
            _draw_world_pixel(canvas, xi, lip_y + 1, RAMP_EDGE, camera_y)


def draw_ramps(canvas, camera_y, ramps):
    for ramp in ramps or ():
        draw_ramp(canvas, camera_y, ramp)


def collide_ramps(ball, ramps, states):
    """Collide against every skill ramp (independent cooldowns)."""
    if ball.in_plunger or not ramps:
        return
    if states is None:
        states = [{} for _ in ramps]
    while len(states) < len(ramps):
        states.append({"cooldown": 0})
    for ramp, st in zip(ramps, states):
        collide_ramp(ball, ramp, st)


def _ramp_airborne_frames():
    return max(6, int(round(TARGET_FPS * RAMP_AIRBORNE_SECONDS)))


def collide_ramp(ball, ramp, state):
    """
    Ride the ramp when moving up-table; launch off the top lip into the
    upper bumper cluster. Side hits bounce; falling onto the ramp from above
    is a soft bounce off the lip.

    On lip launch the ball becomes airborne and skips nearby toys until it lands.
    """
    if ball.in_plunger or not ramp:
        return
    # Already jumping — don't re-grab this ramp
    if ball.is_airborne():
        return
    if state is None:
        state = {}
    cd = int(state.get("cooldown", 0))
    if cd > 0:
        state["cooldown"] = cd - 1
        return

    cx = ramp["cx"]
    top_y = ramp["top_y"]
    bot_y = ramp["bottom_y"]
    # Expand slightly for ball radius
    if ball.y < top_y - BALL_RADIUS - 0.4 or ball.y > bot_y + BALL_RADIUS + 0.3:
        return

    hw = _ramp_half_width(ramp, _clamp(ball.y, top_y, bot_y))
    dx = ball.x - cx
    # Outside trapezoid horizontally
    if abs(dx) > hw + BALL_RADIUS + 0.15:
        return

    # Side wall of ramp — bounce inward/outward
    if abs(dx) > hw * 0.92 and abs(dx) <= hw + BALL_RADIUS + 0.2:
        side = 1.0 if dx > 0 else -1.0
        ball.x = cx + side * (hw + BALL_RADIUS * 0.35)
        if ball.vx * side > 0:
            ball.vx = -ball.vx * BOUNCE * 0.85
        return

    # Inside footprint
    # Hitting lip from above (falling) — soft bounce
    if ball.y <= top_y + BALL_RADIUS * 0.6 and ball.vy > 0.05:
        ball.y = top_y - BALL_RADIUS * 0.2
        ball.vy = -abs(ball.vy) * BOUNCE * 0.55
        return

    # Climbing up the ramp (toward top of table: vy negative)
    if ball.vy < -0.05 or (ball.y > top_y and ball.y < bot_y and ball.speed() > 0.4):
        # Keep centered on the face
        ball.x += (cx - ball.x) * RAMP_CENTER_PULL
        if ball.vy < 0:
            ball.vy -= RAMP_CLIMB
        # Near / past the lip while still going up → launch into bumpers
        if ball.y <= top_y + 1.2 and ball.vy < 0:
            aim_x, aim_y = ramp["aim"]
            # Jump: strong up + steer toward bumper cluster center
            ball.y = top_y - BALL_RADIUS - 0.3
            launch = max(RAMP_LAUNCH, abs(ball.vy) * 0.85 + 1.2)
            ball.vy = -launch
            ball.vx = ball.vx * 0.35 + (aim_x - ball.x) * 0.12
            # Mild horizontal noise so it fans the bumper triangle
            ball.vx += random.uniform(-0.25, 0.25)
            sp = ball.speed()
            if sp > MAX_SPEED:
                s = MAX_SPEED / sp
                ball.vx *= s
                ball.vy *= s
            # Fly over nearby obstacles until airborne timer expires
            ball.airborne = _ramp_airborne_frames()
            state["cooldown"] = 18
            return

        # Soft floor while on the ramp body (prevent falling through)
        if top_y < ball.y < bot_y and ball.vy > 0.2:
            ball.vy *= 0.4


def _drop_target_banks():
    """
    Vertical drop-target banks along both sides (symmetric), plus a horizontal
    line flanking the bottom eject hole (10 px further down).

    Each side:
      wall | ball-gap | outer column (tall) | gap | inner column | open field

    Bottom hole row (bank ids 4 / 5):
      [targets…]  (gap)  hole  (gap)  […targets]   at y = hole_y + 10

    Returns list of (x, y, w, h, bank_id).
    """
    lane_l = _lane_left_x()
    play_w = max(12.0, lane_l - 2.0)
    # Long side runs — upper third down toward lower mid
    y0_outer = MAP_H * 0.28
    y0_inner = MAP_H * 0.32
    left_outer = float(DROP_BEHIND_GAP)
    left_inner = left_outer + DROP_W + DROP_COL_GAP
    right_outer = float(min(play_w - DROP_BEHIND_GAP - DROP_W, lane_l - DROP_W - 2.0))
    right_inner = right_outer - DROP_W - DROP_COL_GAP
    rects = []
    columns = (
        (0, left_outer, y0_outer, DROP_COUNT),
        (1, left_inner, y0_inner, DROP_INNER_COUNT),
        (2, right_inner, y0_inner, DROP_INNER_COUNT),
        (3, right_outer, y0_outer, DROP_COUNT),
    )
    for bank_id, x0, y0, count in columns:
        for i in range(count):
            y = y0 + i * (DROP_H + DROP_GAP)
            rects.append((x0, y, DROP_W, DROP_H, bank_id))

    # Horizontal lines L/R of the bottom eject hole (must match saucer_low layout)
    hole_x, hole_y = _bottom_saucer_xy(play_w)
    row_y = hole_y + DROP_BOTTOM_LINE_BELOW
    gap = DROP_BOTTOM_LINE_GAP
    # Left of hole (bank 4) — extend leftward
    for i in range(DROP_BOTTOM_LINE_EACH):
        x = hole_x - gap - DROP_W - i * (DROP_W + DROP_GAP)
        if x >= 1.5:
            rects.append((x, row_y, DROP_W, DROP_H, 4))
    # Right of hole (bank 5) — extend rightward
    for i in range(DROP_BOTTOM_LINE_EACH):
        x = hole_x + gap + i * (DROP_W + DROP_GAP)
        if x + DROP_W <= lane_l - 1.5:
            rects.append((x, row_y, DROP_W, DROP_H, 5))
    return rects


def _drop_target_bank():
    """Back-compat flat list without bank ids (unused)."""
    return [(x, y, w, h) for x, y, w, h, _bid in _drop_target_banks()]


def _bottom_saucer_xy(play_w=None):
    """World position of the bottom eject hole (shared with drop-target row)."""
    if play_w is None:
        play_w = max(12.0, _lane_left_x() - 2.0)
    return (float(play_w * 0.50), float(MAP_H * 0.72))


def draw_background(canvas, camera_y, plunger_charge=0.0):
    """Rails, plunger lane, curved top, bottom apron; bumpers drawn separately."""
    y0 = int(camera_y)
    y1 = y0 + HEIGHT
    lane_l = int(round(_lane_left_x()))

    exit_y = int(_plunger_exit_y())
    # Side walls + plunger lane divider (opens near arc exit into the playfield)
    for y in range(y0, y1):
        _draw_world_pixel(canvas, 0, y, WALL_RGB, camera_y)
        _draw_world_pixel(canvas, MAP_W - 1, y, WALL_RGB, camera_y)
        if y > exit_y:
            _draw_world_pixel(canvas, lane_l, y, RAIL_RGB, camera_y)

    # Curved top rail — ball rolls on the *inside*
    draw_top_arc(canvas, camera_y)

    # Mark where the plunger feeds into the arc (inside the curve / playfield)
    ex, ey = _plunger_exit_pose()
    if y0 - 2 <= ey <= y1 + 2:
        _draw_aa_disk(canvas, ex, ey, 1.0, ARC_HIGHLIGHT, camera_y)

    # Guide lines each screen height (main field only)
    for band in range(1, MAP_SCALE_Y):
        wy = band * HEIGHT
        if y0 <= wy < y1:
            for x in range(2, lane_l - 1, 2):
                _draw_world_pixel(canvas, x, wy, DECOR_RGB, camera_y)

    # Floor at playfield bottom (above scrolling clock apron)
    pf_bot = int(_playfield_bottom())
    for y in range(max(pf_bot - 2, 0), pf_bot):
        if y0 <= y < y1:
            for x in range(0, lane_l):
                _draw_world_pixel(canvas, x, y, FLOOR_RGB, camera_y)

    # Plunger spring visual at bottom of lane (playfield bottom)
    charge = _clamp(plunger_charge, 0.0, 1.0)
    spring_top = pf_bot - 3 - int(charge * 5)
    for y in range(spring_top, pf_bot - 1):
        if y0 <= y < y1:
            for x in range(lane_l + 1, MAP_W - 1):
                rgb = PLUNGER_SPRING if (y + x) % 2 == 0 else PLUNGER_RGB
                _draw_world_pixel(canvas, x, y, rgb, camera_y)


def draw_bumpers(canvas, camera_y, lit_until=None):
    """Draw upper-cluster + mid-side pop bumpers (flash on hit)."""
    lit_until = lit_until or {}
    now = time.time()
    for i, (px, py, pr) in enumerate(_pop_bumpers()):
        lit = now < lit_until.get(i, 0.0)
        rgb = BUMPER_LIT_RGB if lit else BUMPER_RGB
        r = max(1, int(round(pr)))
        # Soft disk body
        _draw_aa_disk(canvas, px, py, pr + 0.35, rgb, camera_y)
        # Cap / skirt ring
        for a in range(0, 360, 40):
            rad = math.radians(a)
            _draw_world_pixel(
                canvas,
                px + math.cos(rad) * pr,
                py + math.sin(rad) * pr,
                (min(255, rgb[0] + 40), min(255, rgb[1] + 40), min(255, rgb[2] + 40)),
                camera_y,
            )
        _draw_world_pixel(canvas, px, py, BALL_HIGH if lit else (200, 220, 255), camera_y)


def add_score(score_state, points):
    """Clamp score to SCORE_DIGITS display range."""
    if not score_state:
        return
    score_state["score"] = min(
        SCORE_MAX, max(0, int(score_state.get("score", 0)) + int(points))
    )


def collide_bumpers(ball, lit_until, score_state=None):
    """Active pop-bumper kick — EM thumper style."""
    if ball.in_plunger:
        return
    now = time.time()
    for i, (px, py, pr) in enumerate(_pop_bumpers()):
        dx = ball.x - px
        dy = ball.y - py
        d = math.hypot(dx, dy)
        min_d = pr + BALL_RADIUS
        if d < min_d and d > 1e-6:
            fresh = now >= lit_until.get(i, 0.0)
            nx, ny = dx / d, dy / d
            pen = min_d - d
            ball.x += nx * pen
            ball.y += ny * pen
            vn = ball.vx * nx + ball.vy * ny
            if vn < 0:
                ball.vx -= (1.0 + BOUNCE * 1.05) * vn * nx
                ball.vy -= (1.0 + BOUNCE * 1.05) * vn * ny
            # Strong active kick (solenoid pop)
            ball.vx += nx * BUMPER_KICK
            ball.vy += ny * BUMPER_KICK
            sp = ball.speed()
            if sp > MAX_SPEED:
                s = MAX_SPEED / sp
                ball.vx *= s
                ball.vy *= s
            if fresh:
                add_score(score_state, SCORE_BUMPER)
            lit_until[i] = now + 0.16


def _sling_from_triangle(a, b, c, prefer_right=True):
    """
    Build a slingshot from 3 vertices. The rubber (bouncy) edge is always the
    *longest* side of the triangle (classic long rubber strip), not the wall.
    """
    edges = [
        (a, b),
        (b, c),
        (c, a),
    ]
    lengths = []
    for (x1, y1), (x2, y2) in edges:
        lengths.append(math.hypot(x2 - x1, y2 - y1))
    # Longest edge = rubber; if wall is vertical and longest, pick next-longest
    order = sorted(range(3), key=lambda i: lengths[i], reverse=True)
    rubber_i = order[0]
    (p1, p2) = edges[rubber_i]
    # If that edge is the pure wall (same x, nearly vertical), use 2nd longest
    if abs(p1[0] - p2[0]) < 0.35 and abs(p1[1] - p2[1]) > 4.0:
        rubber_i = order[1]
        p1, p2 = edges[rubber_i]

    x1, y1 = p1
    x2, y2 = p2
    dx, dy = x2 - x1, y2 - y1
    elen = math.hypot(dx, dy) or 1.0
    n1x, n1y = -dy / elen, dx / elen
    n2x, n2y = dy / elen, -dx / elen
    # Kick toward playfield center / up
    if prefer_right:
        nx, ny = (n1x, n1y) if n1x > n2x else (n2x, n2y)
    else:
        nx, ny = (n1x, n1y) if n1x < n2x else (n2x, n2y)
    ny = min(ny, -0.38)
    nlen = math.hypot(nx, ny) or 1.0
    nx, ny = nx / nlen, ny / nlen
    return {
        "verts": (a, b, c),
        "rubber": (x1, y1, x2, y2),
        "kick": (nx, ny),
        "rubber_len": elen,
    }


def _flipper_rest_tip(px, py, rest_angle, length):
    """World position of flipper tip at rest."""
    return (
        px + math.cos(rest_angle) * length,
        py + math.sin(rest_angle) * length,
    )


def place_flippers(lane_l, flipper_y):
    """
    Classic bottom flipper placement with a clear center drain.

    Rest tips are aimed at the edges of a FLIPPER_DRAIN_GAP corridor on the
    playfield centerline. Pivots are back along each rest bat so the bats
    form the familiar shallow V with open middle for the ball to drain.
    """
    # Playfield center (main field only — plunger lane is to the right of lane_l)
    center_x = 0.5 * (1.0 + lane_l)
    half_drain = 0.5 * FLIPPER_DRAIN_GAP
    # Rest tip targets: either side of the center drain corridor
    left_tip_x = center_x - half_drain
    right_tip_x = center_x + half_drain
    # Pivot is back along the rest-angle direction from the tip
    left_px = left_tip_x - FLIPPER_LEN * math.cos(LEFT_REST)
    right_px = right_tip_x - FLIPPER_LEN * math.cos(RIGHT_REST)
    # Keep pivots on-table, outside the drain, clear of plunger lane
    min_sep = half_drain + 2.0
    left_px = _clamp(left_px, 3.0, center_x - min_sep)
    right_px = _clamp(right_px, center_x + min_sep, lane_l - 3.0)
    # Re-check drain: if clamps closed the gap, push pivots apart first
    lt = left_px + FLIPPER_LEN * math.cos(LEFT_REST)
    rt = right_px + FLIPPER_LEN * math.cos(RIGHT_REST)
    if rt - lt < FLIPPER_DRAIN_GAP:
        need = FLIPPER_DRAIN_GAP - (rt - lt)
        left_px -= need * 0.5
        right_px += need * 0.5
    # Final hard clamp so tips never cross into the drain corridor
    lt = left_px + FLIPPER_LEN * math.cos(LEFT_REST)
    rt = right_px + FLIPPER_LEN * math.cos(RIGHT_REST)
    if lt > center_x - half_drain:
        left_px -= lt - (center_x - half_drain)
    if rt < center_x + half_drain:
        right_px += (center_x + half_drain) - rt
    return float(left_px), float(right_px), float(center_x)


def build_slingshots(left_px, right_px, flipper_y, lane_l):
    """
    Classic EM slingshots: just above and to either side of the flippers.

      wall | OUTLANE | SLING | (inlane onto flipper) | DRAIN | flipper | …

    Each sling is a tall / short-base triangle whose long rubber faces the
    playfield. The outer face sits one outlane-width in from the wall; the
    apex points toward center but is clamped short of the drain corridor
    and short of the flipper tip so the ball can always fall down the middle.
    """
    h = SLING_HEIGHT
    base = SLING_BASE
    center_x = 0.5 * (1.0 + lane_l)
    half_drain = 0.5 * FLIPPER_DRAIN_GAP
    # Keep apex well clear of the open drain; widen gap between slings
    # without moving the flippers (pull each apex away from center).
    half_widen = 0.5 * SLING_GAP_WIDEN
    drain_left = center_x - half_drain - BALL_RADIUS * 1.2 - half_widen
    drain_right = center_x + half_drain + BALL_RADIUS * 1.2 + half_widen

    # --- Left sling: just above + outside left flipper ---
    # Outer face sits one outlane-width in from the left wall, but never
    # past the flipper pivot (slings stay beside the bats, not midfield).
    lx = max(1.2 + OUTLANE_W, left_px - 2.0)
    lx = min(lx, left_px - 0.8)               # always outside the pivot
    la = (lx, flipper_y - h)                  # top of outer wall post
    lb = (lx, flipper_y - 2.4)                # bottom of outer wall post
    left_tip_x = left_px + FLIPPER_LEN * math.cos(LEFT_REST)
    # Apex: short base inward, never into drain, never past flipper tip
    lc_x = min(lx + base, left_px + FLIPPER_LEN * 0.30, left_tip_x - 1.8, drain_left)
    lc_x = max(lc_x, lx + 2.0)
    # Extra 2px each side of the total 4px widen (apex further from center)
    lc_x = min(lc_x, drain_left)
    lc = (lc_x, flipper_y - 2.8)              # just above the flipper bat
    # Shift entire left sling outward (toward left wall) and up
    shift_l = SLING_OUTWARD_SHIFT
    up = SLING_UP_SHIFT
    la = (la[0] - shift_l, la[1] - up)
    lb = (lb[0] - shift_l, lb[1] - up)
    lc = (lc[0] - shift_l, lc[1] - up)
    left = _sling_from_triangle(la, lb, lc, prefer_right=True)
    left["side"] = "left"

    # --- Right sling: mirror, clear of plunger lane ---
    rx = min(lane_l - 1.2 - OUTLANE_W, right_px + 2.0)
    rx = max(rx, right_px + 0.8)              # always outside the pivot
    ra = (rx, flipper_y - h)
    rb = (rx, flipper_y - 2.4)
    right_tip_x = right_px + FLIPPER_LEN * math.cos(RIGHT_REST)
    rc_x = max(rx - base, right_px - FLIPPER_LEN * 0.30, right_tip_x + 1.8, drain_right)
    rc_x = min(rc_x, rx - 2.0)
    rc_x = max(rc_x, drain_right)
    rc = (rc_x, flipper_y - 2.8)
    # Shift entire right sling outward (toward right / plunger wall) and up
    shift_r = SLING_OUTWARD_SHIFT
    ra = (ra[0] + shift_r, ra[1] - up)
    rb = (rb[0] + shift_r, rb[1] - up)
    rc = (rc[0] + shift_r, rc[1] - up)
    right = _sling_from_triangle(ra, rb, rc, prefer_right=False)
    right["side"] = "right"

    return [left, right]


def _sling_outer_x(sling, side):
    """Wall-facing x of a sling triangle (left = min x, right = max x)."""
    xs = [float(v[0]) for v in sling.get("verts", ())]
    if not xs:
        return 0.0 if side == "left" else 0.0
    return min(xs) if side == "left" else max(xs)


def build_outlane_guides(left_px, right_px, flipper_y, lane_l, slings=None):
    """
    Classic outlane / inlane wireforms on each side:

      wall | OUTLANE | vertical guide | curve → flipper | DRAIN | …

    Vertical rail sits halfway between the side wall and that side's sling
    outer face; at the bottom it curves inward toward the flipper so the
    ball either drains outside the rail or is funnelled onto the bat.
    """
    # Sling top is SLING_HEIGHT above flippers, then raised by SLING_UP_SHIFT;
    # guide vertical only sticks OUTLANE_GUIDE_ABOVE_SLING px above that.
    sling_top_y = flipper_y - SLING_HEIGHT - SLING_UP_SHIFT
    y_top = sling_top_y - OUTLANE_GUIDE_ABOVE_SLING
    # Start the bend a little above the flipper line
    y_bend = flipper_y - 1.5
    # Curve end: just above / outside each flipper pivot (feeds the bat)
    left_end = (left_px + 1.2, flipper_y - 0.4)
    right_end = (right_px - 1.2, flipper_y - 0.4)

    # Walls and sling outer faces → midpoints for the vertical rails
    left_wall = 0.0
    right_wall = float(lane_l)
    if slings and len(slings) >= 2:
        left_sling_x = _sling_outer_x(slings[0], "left")
        right_sling_x = _sling_outer_x(slings[1], "right")
    else:
        left_sling_x = left_px - 2.0
        right_sling_x = right_px + 2.0
    lx = 0.5 * (left_wall + left_sling_x)
    rx = 0.5 * (right_wall + right_sling_x)

    def _curve_points(x0, y0, x1, y1, side, steps=10):
        """Quarter-ish arc from vertical rail bottom into the flipper."""
        pts = []
        for i in range(1, steps + 1):
            t = i / float(steps)
            # Ease: stay near vertical early, then sweep hard to the flipper
            te = t * t * (3.0 - 2.0 * t)  # smoothstep
            if side == "left":
                # Arc bulging down-right (from wall rail toward center/flipper)
                erx = max(1.0, x1 - x0)
                ery = max(1.0, y1 - y0)
                ex = x0 + erx * (1.0 - math.cos(te * math.pi * 0.5))
                ey = y0 + ery * math.sin(te * math.pi * 0.5)
                lin_x = x0 + (x1 - x0) * te
                lin_y = y0 + (y1 - y0) * te
                pts.append((ex * 0.55 + lin_x * 0.45, ey * 0.55 + lin_y * 0.45))
            else:
                erx = max(1.0, x0 - x1)
                ery = max(1.0, y1 - y0)
                ex = x0 - erx * (1.0 - math.cos(te * math.pi * 0.5))
                ey = y0 + ery * math.sin(te * math.pi * 0.5)
                lin_x = x0 + (x1 - x0) * te
                lin_y = y0 + (y1 - y0) * te
                pts.append((ex * 0.55 + lin_x * 0.45, ey * 0.55 + lin_y * 0.45))
        # Snap final point exactly onto the flipper feed
        pts[-1] = (x1, y1)
        return pts

    # Left: vertical at midpoint wall↔sling, then curve toward left flipper
    left_pts = [(lx, y_top), (lx, y_bend)]
    left_pts.extend(_curve_points(lx, y_bend, left_end[0], left_end[1], "left"))

    # Right: vertical at midpoint wall↔sling, curve toward right flipper
    right_pts = [(rx, y_top), (rx, y_bend)]
    right_pts.extend(_curve_points(rx, y_bend, right_end[0], right_end[1], "right"))

    return [
        {"side": "left", "points": left_pts, "x": lx},
        {"side": "right", "points": right_pts, "x": rx},
    ]


def _guide_segments(guides):
    """Expand guide polylines into (x1,y1,x2,y2) segments."""
    segs = []
    for g in guides or ():
        pts = g.get("points") or ()
        for i in range(len(pts) - 1):
            x1, y1 = pts[i]
            x2, y2 = pts[i + 1]
            segs.append((float(x1), float(y1), float(x2), float(y2)))
    return segs


def _draw_world_line_1px(canvas, x1, y1, x2, y2, rgb, camera_y):
    """Single-pixel-thick world-space line (Bresenham-style)."""
    x1i, y1i = int(round(x1)), int(round(y1))
    x2i, y2i = int(round(x2)), int(round(y2))
    dx = abs(x2i - x1i)
    dy = abs(y2i - y1i)
    sx = 1 if x1i < x2i else -1
    sy = 1 if y1i < y2i else -1
    err = dx - dy
    x, y = x1i, y1i
    # Cap steps so a bad segment never loops forever
    for _ in range(dx + dy + 2):
        _draw_world_pixel(canvas, x, y, rgb, camera_y)
        if x == x2i and y == y2i:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x += sx
        if e2 < dx:
            err += dx
            y += sy


def draw_outlane_guides(canvas, camera_y, guides):
    """Draw outlane rails + bottom curves as true 1px-thick lines."""
    rgb = OUTLANE_GUIDE_RGB
    for g in guides or ():
        pts = g.get("points") or ()
        for i in range(len(pts) - 1):
            x1, y1 = pts[i]
            x2, y2 = pts[i + 1]
            _draw_world_line_1px(canvas, x1, y1, x2, y2, rgb, camera_y)


def collide_outlane_guides(ball, guides):
    """
    Bounce the ball off outlane / inlane rails.

    Outside the rail (toward the wall) the ball can fall to a drain;
    inside, the bottom curve funnels it onto the flipper.
    """
    if ball.in_plunger or not guides:
        return
    hit_r = BALL_RADIUS + OUTLANE_GUIDE_THICK
    for x1, y1, x2, y2 in _guide_segments(guides):
        dist, nx, ny, _t = _dist_point_segment(ball.x, ball.y, x1, y1, x2, y2)
        if dist >= hit_r or dist < 1e-6:
            continue
        # Normal from segment toward ball
        sx, sy = x2 - x1, y2 - y1
        sl = math.hypot(sx, sy) or 1.0
        n1x, n1y = -sy / sl, sx / sl
        n2x, n2y = sy / sl, -sx / sl
        to_bx, to_by = ball.x - nx, ball.y - ny
        if n1x * to_bx + n1y * to_by >= n2x * to_bx + n2y * to_by:
            nnx, nny = n1x, n1y
        else:
            nnx, nny = n2x, n2y
        pen = hit_r - dist + 0.05
        ball.x += nnx * pen
        ball.y += nny * pen
        vn = ball.vx * nnx + ball.vy * nny
        if vn < 0:
            ball.vx -= (1.0 + BOUNCE * 0.85) * vn * nnx
            ball.vy -= (1.0 + BOUNCE * 0.85) * vn * nny


# ---- Extra playfield toys (standups, posts, spinner, rollovers, saucer) ----

def _layout_playfield_toys():
    """
    Positions for additional EM toys relative to the tall table.
    Returns dict of static geometry lists.
    """
    lane_l = _lane_left_x()
    play_w = max(12.0, lane_l - 2.0)
    arc_cx, cy, radius, _, _ = _top_arc()
    upper = cy - radius * 0.15
    low_mid = MAP_H * 0.62

    standups = [
        # Upper flanks — feed pop-bumper cluster
        (play_w * 0.14, upper + 10.0),
        (play_w * 0.86, upper + 10.0),
        # Mid flanks beside drop bank
        (play_w * 0.12, MAP_H * 0.40),
        (play_w * 0.78, MAP_H * 0.40),
        # Lower approach posts above slings
        (play_w * 0.22, low_mid),
        (play_w * 0.72, low_mid),
    ]

    posts = [
        # Guide posts around pop bumpers
        (play_w * 0.48, upper + 14.0),
        (play_w * 0.22, upper + 16.0),
        (play_w * 0.74, upper + 16.0),
        # Outlane-top posts are placed after guides are built (top of each rail)
    ]


    # Spinners — EM reels; big cluster in mid-table (where the clock used to sit)
    # Each entry: (x, y, radius)
    # (center-upper spinner removed — bounce triangle sits between top flippers)
    spinners = [
        # Big midfield trio (center of the tall table)
        (play_w * 0.32, MAP_H * 0.48, 3.5),
        (play_w * 0.50, MAP_H * 0.50, 4.2),   # largest — table center
        (play_w * 0.68, MAP_H * 0.48, 3.5),
        # Upper / flanks (smaller variety)
        (play_w * 0.78, MAP_H * 0.33, 2.0),
        (play_w * 0.22, MAP_H * 0.30, 2.6),
        (play_w * 0.42, MAP_H * 0.58, 2.8),   # lower-mid large
        (play_w * 0.60, MAP_H * 0.58, 2.8),
    ]

    # Top rollover switches in a shallow lane under the arc
    rollover_y = upper + 5.5
    rollovers = [
        (play_w * 0.30, rollover_y),
        (play_w * 0.48, rollover_y),
        (play_w * 0.66, rollover_y),
    ]

    # Eject-hole network (4): enter any → vanish → pan → exit another
    apex_y = cy - radius
    saucer_top = (float(arc_cx), float(apex_y + SAUCER_TOP_BELOW_APEX))
    saucer_mid_l = (play_w * 0.16, MAP_H * 0.46)
    saucer_mid_r = (play_w * 0.80, MAP_H * 0.46)
    saucer_low = _bottom_saucer_xy(play_w)
    saucers = [saucer_top, saucer_mid_l, saucer_mid_r, saucer_low]

    return {
        "standups": standups,
        "posts": posts,
        "spinners": spinners,
        "rollovers": rollovers,
        "saucers": saucers,
        # Back-compat single handle
        "saucer": saucer_mid_l,
    }


def draw_standups(canvas, camera_y, standups, lit_until=None):
    lit_until = lit_until or {}
    now = time.time()
    for i, (px, py) in enumerate(standups):
        lit = now < lit_until.get(i, 0.0)
        rgb = STANDUP_LIT if lit else STANDUP_RGB
        _draw_aa_disk(canvas, px, py, STANDUP_R + 0.2, rgb, camera_y)
        _draw_world_pixel(canvas, px, py, (255, 220, 255) if lit else (220, 120, 200), camera_y)


def collide_standups(ball, standups, lit_until, score_state=None):
    if ball.in_plunger:
        return
    now = time.time()
    for i, (px, py) in enumerate(standups):
        dx, dy = ball.x - px, ball.y - py
        d = math.hypot(dx, dy)
        min_d = STANDUP_R + BALL_RADIUS
        if d < min_d and d > 1e-6:
            fresh = now >= lit_until.get(i, 0.0)
            nx, ny = dx / d, dy / d
            ball.x = px + nx * min_d
            ball.y = py + ny * min_d
            vn = ball.vx * nx + ball.vy * ny
            if vn < 0:
                ball.vx -= (1.0 + BOUNCE) * vn * nx
                ball.vy -= (1.0 + BOUNCE) * vn * ny
            if fresh:
                add_score(score_state, SCORE_TARGET)
            lit_until[i] = now + 0.2


def draw_posts(canvas, camera_y, posts):
    for px, py in posts:
        _draw_aa_disk(canvas, px, py, POST_R, POST_RGB, camera_y)
        _draw_world_pixel(canvas, px, py, (140, 145, 160), camera_y)


def collide_posts(ball, posts):
    if ball.in_plunger:
        return
    for px, py in posts:
        dx, dy = ball.x - px, ball.y - py
        d = math.hypot(dx, dy)
        min_d = POST_R + BALL_RADIUS
        if d < min_d and d > 1e-6:
            nx, ny = dx / d, dy / d
            ball.x = px + nx * min_d
            ball.y = py + ny * min_d
            vn = ball.vx * nx + ball.vy * ny
            if vn < 0:
                ball.vx -= (1.0 + BOUNCE * 0.9) * vn * nx
                ball.vy -= (1.0 + BOUNCE * 0.9) * vn * ny


def _spinner_radius(spinner):
    """Accept (x, y) | (x, y, r) | dict — return radius."""
    if isinstance(spinner, dict):
        return float(spinner.get("r", SPINNER_R))
    if len(spinner) >= 3:
        return float(spinner[2])
    return float(SPINNER_R)


def _spinner_xy(spinner):
    if isinstance(spinner, dict):
        return float(spinner["x"]), float(spinner["y"])
    return float(spinner[0]), float(spinner[1])


def draw_spinner(canvas, camera_y, spinner, angle, lit_until=0.0):
    """Draw one spinner reel (size from spinner radius)."""
    px, py = _spinner_xy(spinner)
    radius = _spinner_radius(spinner)
    lit = time.time() < lit_until
    rgb = SPINNER_LIT if lit else SPINNER_RGB
    hub_r = max(0.55, radius * 0.55)
    vane_hw = max(0.45, min(1.1, radius * 0.38))
    _draw_aa_disk(canvas, px, py, hub_r, (40, 40, 30), camera_y)
    # Rotating vane
    ca, sa = math.cos(angle), math.sin(angle)
    x1 = px - ca * radius
    y1 = py - sa * radius
    x2 = px + ca * radius
    y2 = py + sa * radius
    _draw_aa_flipper_blade(
        canvas, x1, y1, x2, y2, rgb,
        (rgb[0] // 2, rgb[1] // 2, rgb[2] // 2),
        camera_y, half_width=vane_hw,
    )


def draw_spinners(canvas, camera_y, spinners, states):
    """Draw all playfield spinners."""
    for i, sp in enumerate(spinners or ()):
        st = states[i] if i < len(states) else {}
        draw_spinner(
            canvas, camera_y, sp,
            st.get("angle", 0.0),
            st.get("lit_until", 0.0),
        )


def collide_spinner(ball, spinner, state):
    """
    state: dict with angle, omega, lit_until
    Hitting the spinner adds spin; ball gets a light deflection.
    Larger reels spin a bit slower / hit a bit softer per size.
    """
    if ball.in_plunger:
        return
    px, py = _spinner_xy(spinner)
    radius = _spinner_radius(spinner)
    dx, dy = ball.x - px, ball.y - py
    d = math.hypot(dx, dy)
    min_d = radius + BALL_RADIUS
    if d < min_d and d > 1e-6:
        nx, ny = dx / d, dy / d
        ball.x = px + nx * min_d
        ball.y = py + ny * min_d
        vn = ball.vx * nx + ball.vy * ny
        if vn < 0:
            ball.vx -= (1.0 + 0.5) * vn * nx
            ball.vy -= (1.0 + 0.5) * vn * ny
        # Impulse → angular velocity (EM reel); scale with size a little
        size_scale = SPINNER_R / max(0.8, radius)
        tang = ball.vx * (-ny) + ball.vy * nx
        state["omega"] += (
            tang * 0.35 * size_scale
            + (0.4 if abs(tang) < 0.1 else 0.0)
        )
        max_w = 1.0 + 0.35 * size_scale
        state["omega"] = _clamp(state["omega"], -max_w, max_w)
        state["lit_until"] = time.time() + 0.35
        # Slight speed transfer along tangent
        ball.vx += -ny * 0.15
        ball.vy += nx * 0.15


def collide_spinners(ball, spinners, states):
    """Collide ball against every spinner reel."""
    if ball.in_plunger or not spinners:
        return
    for i, sp in enumerate(spinners):
        if i >= len(states):
            break
        collide_spinner(ball, sp, states[i])


def update_spinner(state):
    state["angle"] = (state.get("angle", 0.0) + state.get("omega", 0.0)) % (2 * math.pi)
    state["omega"] = state.get("omega", 0.0) * SPINNER_FRICTION
    if abs(state["omega"]) < 0.01:
        state["omega"] = 0.0


def update_spinners(states):
    for st in states or ():
        update_spinner(st)


def make_spinner_states(spinners):
    """One independent spin state per spinner."""
    return [
        {"angle": random.uniform(0.0, 2.0 * math.pi), "omega": 0.0, "lit_until": 0.0}
        for _ in (spinners or ())
    ]


def draw_rollovers(canvas, camera_y, rollovers, lit):
    for i, (px, py) in enumerate(rollovers):
        on = lit[i] if i < len(lit) else False
        rgb = ROLLOVER_LIT if on else ROLLOVER_RGB
        # Small gate / switch bar
        for ox in (-1, 0, 1):
            _draw_world_pixel(canvas, px + ox, py, rgb, camera_y)
        _draw_world_pixel(canvas, px, py - 1, rgb, camera_y)


def collide_rollovers(ball, rollovers, lit, score_state=None):
    """Light a rollover when the ball passes over it (center proximity)."""
    if ball.in_plunger:
        return
    for i, (px, py) in enumerate(rollovers):
        if math.hypot(ball.x - px, ball.y - py) < 2.2:
            if not lit[i]:
                add_score(score_state, SCORE_TARGET)
            lit[i] = True


def draw_saucer(canvas, camera_y, saucer_xy, occupied=False):
    px, py = saucer_xy
    _draw_aa_disk(canvas, px, py, 2.4, SAUCER_RIM, camera_y)
    _draw_aa_disk(canvas, px, py, 1.5, SAUCER_RGB, camera_y)
    if occupied:
        _draw_aa_disk(canvas, px, py, 1.0, BALL_CORE, camera_y)


def draw_saucers(canvas, camera_y, saucers, state):
    """Draw all eject holes; highlight entry while vanishing, exit while panning."""
    held_i = None
    if state.get("held"):
        if state.get("phase") == "pan":
            held_i = state.get("to_i")
        else:
            held_i = state.get("from_i")
    for i, xy in enumerate(saucers or ()):
        draw_saucer(canvas, camera_y, xy, occupied=(held_i == i))


def _saucer_eject_velocity(exit_xy, saucers=None):
    """
    Kick direction out of an eject hole based on table position.
    High holes → mostly downward; lower holes → up/center.
    """
    px, py = exit_xy
    field_cx = MAP_W * 0.48
    pf = _playfield_bottom()
    # High on table → kick down; low → kick up; mid → toward center-up
    if py < pf * 0.35:
        knx, kny = field_cx - px, 6.5
    elif py > pf * 0.62:
        knx, kny = field_cx - px, -8.0
    else:
        knx, kny = (field_cx - px) * 1.15, -6.0
    n = math.hypot(knx, kny) or 1.0
    base_ang = math.atan2(kny / n, knx / n)
    ang = base_ang + random.uniform(
        -SAUCER_EJECT_ANGLE_JITTER, SAUCER_EJECT_ANGLE_JITTER
    )
    speed = SAUCER_KICK * random.uniform(
        1.0 - SAUCER_EJECT_SPEED_JITTER,
        1.0 + SAUCER_EJECT_SPEED_JITTER,
    )
    return math.cos(ang) * speed, math.sin(ang) * speed


def _saucer_frame_counts():
    """Vanish / pan lengths in frames (based on TARGET_FPS)."""
    vanish = max(8, int(round(TARGET_FPS * SAUCER_VANISH_SECONDS)))
    pan = max(6, int(round(TARGET_FPS * SAUCER_PAN_SECONDS)))
    return vanish, pan


def update_saucers(ball, saucers, state, score_state=None):
    """
    Eject-hole network:
      capture → +SCORE_SAUCER → fade out (~0.5s) at entry →
      camera pans to a different exit hole → ball ejects there.

    state keys:
      held, phase ('vanish'|'pan'), timer, from_i, to_i,
      entry_xy, exit_xy, focus_y, cooldown[]
    """
    if ball.in_plunger or not saucers:
        return

    n = len(saucers)
    cds = state.setdefault("cooldown", [0] * n)
    while len(cds) < n:
        cds.append(0)

    for i in range(n):
        if cds[i] > 0:
            cds[i] -= 1

    vanish_n, pan_n = _saucer_frame_counts()

    if state.get("held"):
        state["timer"] = state.get("timer", 0) + 1
        phase = state.get("phase") or "vanish"
        from_i = int(state.get("from_i", 0)) % n
        to_i = int(state.get("to_i", (from_i + 1) % n)) % n
        ex, ey = state.get("exit_xy") or saucers[to_i]
        hx, hy = state.get("entry_xy") or saucers[from_i]

        if phase == "vanish":
            # Stay at entry; slowly fade the ball out
            ball.x, ball.y = float(hx), float(hy)
            ball.vx = ball.vy = 0.0
            t = _clamp(state["timer"] / float(vanish_n), 0.0, 1.0)
            ball.visible = 1.0 - t
            state["focus_y"] = float(hy)
            if state["timer"] >= vanish_n:
                state["phase"] = "pan"
                state["timer"] = 0
                ball.visible = 0.0
                # Park at exit (invisible) so camera has a destination
                ball.x, ball.y = float(ex), float(ey)
                state["focus_y"] = float(hy)  # start pan from entry
        elif phase == "pan":
            # Invisible at exit; camera focus lerps entry → exit
            ball.x, ball.y = float(ex), float(ey)
            ball.vx = ball.vy = 0.0
            ball.visible = 0.0
            t = _clamp(state["timer"] / float(pan_n), 0.0, 1.0)
            # Smoothstep
            te = t * t * (3.0 - 2.0 * t)
            state["focus_y"] = float(hy) + (float(ey) - float(hy)) * te
            state["focus_x"] = float(hx) + (float(ex) - float(hx)) * te
            if state["timer"] >= pan_n:
                # Eject!
                ball.x, ball.y = float(ex), float(ey)
                ball.vx, ball.vy = _saucer_eject_velocity((ex, ey), saucers)
                ball.visible = 1.0
                state["held"] = False
                state["phase"] = None
                state["timer"] = 0
                state["from_i"] = None
                state["to_i"] = None
                state["focus_y"] = None
                state["focus_x"] = None
                cds[from_i] = 55
                cds[to_i] = 55
                print(
                    f"[pinball] Saucer eject  #{from_i}→#{to_i}  "
                    f"+{SCORE_SAUCER}  score="
                    f"{score_state.get('score', 0) if score_state else 0}"
                )
        return

    # Capture: slow ball over a hole that is not cooling down
    if ball.speed() > 2.2:
        return
    for i, (px, py) in enumerate(saucers):
        if cds[i] > 0:
            continue
        if math.hypot(ball.x - px, ball.y - py) < SAUCER_CAPTURE_R:
            # Pick a different exit hole at random
            others = [j for j in range(n) if j != i]
            to_i = random.choice(others) if others else i
            ex, ey = saucers[to_i]
            state["held"] = True
            state["phase"] = "vanish"
            state["timer"] = 0
            state["from_i"] = i
            state["to_i"] = to_i
            state["entry_xy"] = (float(px), float(py))
            state["exit_xy"] = (float(ex), float(ey))
            state["focus_y"] = float(py)
            state["focus_x"] = float(px)
            ball.x, ball.y = float(px), float(py)
            ball.vx = ball.vy = 0.0
            ball.visible = 1.0
            add_score(score_state, SCORE_SAUCER)
            print(
                f"[pinball] Saucer capture  #{i}→#{to_i}  +{SCORE_SAUCER}"
            )
            return


def update_saucer(ball, saucer_xy, state, score_state=None):
    """Back-compat: single saucer treated as a 1-hole list (no teleport)."""
    update_saucers(ball, [saucer_xy], state, score_state=score_state)


def make_drop_targets():
    """Create drop-target state: list of dicts with rect + up flag + bank id."""
    bank = []
    for (x, y, w, h, bank_id) in _drop_target_banks():
        bank.append({
            "x": float(x), "y": float(y), "w": float(w), "h": float(h),
            "up": True,
            "bank": int(bank_id),
        })
    return bank


def reset_drop_targets(targets, bank_id=None):
    """Reset all targets, or only one vertical bank if bank_id is set."""
    for t in targets:
        if bank_id is None or t.get("bank") == bank_id:
            t["up"] = True


def draw_drop_targets(canvas, camera_y, targets):
    """Draw upright targets as short posts; down targets as faint floor marks."""
    for t in targets:
        x, y, w, h = t["x"], t["y"], t["w"], t["h"]
        if t["up"]:
            # Face
            for yy in range(int(y), int(y + h) + 1):
                for xx in range(int(x), int(x + w) + 1):
                    edge = (
                        xx == int(x) or xx == int(x + w)
                        or yy == int(y) or yy == int(y + h)
                    )
                    rgb = DROP_EDGE if edge else DROP_RGB
                    _draw_world_pixel(canvas, xx, yy, rgb, camera_y)
            # Top lip highlight
            for xx in range(int(x), int(x + w) + 1):
                _draw_world_pixel(canvas, xx, y, (255, 220, 100), camera_y)
        else:
            # Down — small dark plate on the playfield
            mid_y = int(y + h - 1)
            for xx in range(int(x), int(x + w) + 1):
                _draw_world_pixel(canvas, xx, mid_y, DROP_DOWN_RGB, camera_y)


def collide_drop_targets(ball, targets, score_state=None):
    """
    Hit an upright drop target → it drops (disappears as an obstacle).
    Returns True if any target was dropped this call.
    """
    if ball.in_plunger:
        return False
    dropped = False
    for t in targets:
        if not t["up"]:
            continue
        # Expand rect slightly for the ball radius
        left = t["x"] - BALL_RADIUS * 0.35
        right = t["x"] + t["w"] + BALL_RADIUS * 0.35
        top = t["y"] - BALL_RADIUS * 0.35
        bot = t["y"] + t["h"] + BALL_RADIUS * 0.35
        if not (left <= ball.x <= right and top <= ball.y <= bot):
            continue

        # Resolve which face was hit (simple AABB push-out)
        dl = ball.x - left
        dr = right - ball.x
        dt = ball.y - top
        db = bot - ball.y
        m = min(dl, dr, dt, db)
        if m == dl:
            ball.x = left
            ball.vx = -abs(ball.vx) * BOUNCE - 0.25
        elif m == dr:
            ball.x = right
            ball.vx = abs(ball.vx) * BOUNCE + 0.25
        elif m == dt:
            ball.y = top
            ball.vy = -abs(ball.vy) * BOUNCE - 0.2
        else:
            ball.y = bot
            ball.vy = abs(ball.vy) * BOUNCE + 0.2

        t["up"] = False
        add_score(score_state, SCORE_TARGET)
        dropped = True
    return dropped


def update_drop_targets(targets, bank_timers):
    """
    Per-bank EM reset: when a vertical bank is fully down, restore it after
    DROP_RESET_SECONDS. bank_timers maps bank_id → all-down start time.
    Returns (bank_timers, just_reset).
    """
    if bank_timers is None:
        bank_timers = {}
    now = time.time()
    just_reset = False
    bank_ids = sorted({t.get("bank", 0) for t in targets})
    for bid in bank_ids:
        bank = [t for t in targets if t.get("bank", 0) == bid]
        if not bank:
            continue
        all_down = all(not t["up"] for t in bank)
        if all_down:
            if bank_timers.get(bid) is None:
                bank_timers[bid] = now
            elif now - bank_timers[bid] >= DROP_RESET_SECONDS:
                reset_drop_targets(targets, bank_id=bid)
                bank_timers[bid] = None
                just_reset = True
        else:
            bank_timers[bid] = None
    return bank_timers, just_reset


def place_upper_flippers(lane_l):
    """
    Symmetric upper-third side flippers, almost on the walls.

    Left pivot near left wall (tips rest toward center/down);
    right pivot near main-field right wall (mirror).
    """
    pf = _playfield_bottom()
    y = float(pf * UPPER_FLIPPER_Y_FRAC)
    left_px = float(UPPER_FLIPPER_SIDE_INSET)
    right_px = float(lane_l - UPPER_FLIPPER_SIDE_INSET)
    return left_px, right_px, y


def build_upper_bounce_triangle(up_left_px, up_right_px, up_flipper_y):
    """
    Equilateral bounce triangle (side UPPER_TRI_SIDE) centered between the
    upper flippers. Apex points up-table; base faces down into the field.
    Weaker pop than a slingshot; solid edges (ball cannot pass through).
    """
    cx = 0.5 * (float(up_left_px) + float(up_right_px))
    cy = float(up_flipper_y)
    s = float(UPPER_TRI_SIDE)
    h = s * math.sqrt(3.0) * 0.5
    # Centroid at (cx, cy): apex up, base down
    apex = (cx, cy - (2.0 / 3.0) * h)
    bl = (cx - 0.5 * s, cy + (1.0 / 3.0) * h)
    br = (cx + 0.5 * s, cy + (1.0 / 3.0) * h)
    # Prefer kick mostly up/center (toward playfield interior)
    tri = _sling_from_triangle(apex, bl, br, prefer_right=True)
    # Override kick: mild up + slight toward center of field
    knx, kny = tri["kick"]
    # Soften and bias upward (negative y)
    knx = knx * 0.35
    kny = min(kny, -0.55)
    nlen = math.hypot(knx, kny) or 1.0
    tri["kick"] = (knx / nlen, kny / nlen)
    tri["side"] = "upper_center"
    tri["kick_scale"] = UPPER_TRI_KICK / max(1e-6, SLING_KICK)
    return tri


def draw_bounce_triangle(canvas, camera_y, tri, lit=False):
    """Draw the upper-center bounce triangle (steel-ish)."""
    if not tri:
        return
    body = UPPER_TRI_EDGE if lit else UPPER_TRI_RGB
    edge = (min(255, body[0] + 40), min(255, body[1] + 40), min(255, body[2] + 40))
    v0, v1, v2 = tri["verts"]
    for (ax, ay), (bx, by) in ((v0, v1), (v1, v2), (v2, v0)):
        _draw_aa_flipper_blade(
            canvas, ax, ay, bx, by,
            body, edge, camera_y, half_width=0.85,
        )
    # Fill a couple interior points so it reads as a solid wedge
    cx = (v0[0] + v1[0] + v2[0]) / 3.0
    cy = (v0[1] + v1[1] + v2[1]) / 3.0
    _draw_aa_disk(canvas, cx, cy, 0.9, body, camera_y)


def collide_bounce_triangle(ball, tri, lit_state=None, score_state=None):
    """
    Solid equilateral wedge between the upper flippers.

    All edges are hard walls (no pass-through). The long face gets a weak
    center/up kick — slingshot-like but much softer.
    """
    if ball.in_plunger or not tri or ball.is_airborne():
        return
    if lit_state is None:
        lit_state = {}
    now = time.time()
    hit_r = BALL_RADIUS + UPPER_TRI_PAD
    verts = tri.get("verts")
    if not verts or len(verts) < 3:
        return
    a, b, c = verts[0], verts[1], verts[2]
    tcx = (a[0] + b[0] + c[0]) / 3.0
    tcy = (a[1] + b[1] + c[1]) / 3.0
    knx, kny = tri["kick"]
    rx1, ry1, rx2, ry2 = tri["rubber"]
    edges = ((a, b), (b, c), (c, a))
    hit_rubber = False
    hit_any = False

    for (p1, p2) in edges:
        x1, y1 = p1
        x2, y2 = p2
        dist, qx, qy, _t = _dist_point_segment(ball.x, ball.y, x1, y1, x2, y2)
        if dist >= hit_r or dist < 1e-9:
            continue
        hit_any = True
        sx, sy = x2 - x1, y2 - y1
        sl = math.hypot(sx, sy) or 1.0
        n1x, n1y = -sy / sl, sx / sl
        n2x, n2y = sy / sl, -sx / sl
        if n1x * (qx - tcx) + n1y * (qy - tcy) > 0:
            nnx, nny = n1x, n1y
        else:
            nnx, nny = n2x, n2y
        to_bx, to_by = ball.x - qx, ball.y - qy
        if nnx * to_bx + nny * to_by < 0:
            nnx, nny = -nnx, -nny
        pen = hit_r - dist + 0.2
        ball.x += nnx * pen
        ball.y += nny * pen
        vn = ball.vx * nnx + ball.vy * nny
        if vn < 0:
            ball.vx -= (1.0 + BOUNCE) * vn * nnx
            ball.vy -= (1.0 + BOUNCE) * vn * nny
        is_rubber = (
            (abs(x1 - rx1) < 0.2 and abs(y1 - ry1) < 0.2
             and abs(x2 - rx2) < 0.2 and abs(y2 - ry2) < 0.2)
            or (abs(x1 - rx2) < 0.2 and abs(y1 - ry2) < 0.2
                and abs(x2 - rx1) < 0.2 and abs(y2 - ry1) < 0.2)
        )
        if is_rubber:
            hit_rubber = True

    if _point_in_triangle(ball.x, ball.y, a, b, c):
        hit_any = True
        best = None
        best_d = 1e9
        for (p1, p2) in edges:
            dist, qx, qy, _t = _dist_point_segment(
                ball.x, ball.y, p1[0], p1[1], p2[0], p2[1],
            )
            if dist < best_d:
                best_d = dist
                best = (p1, p2, qx, qy)
        if best is not None:
            p1, p2, qx, qy = best
            sx, sy = p2[0] - p1[0], p2[1] - p1[1]
            sl = math.hypot(sx, sy) or 1.0
            n1x, n1y = -sy / sl, sx / sl
            if n1x * (qx - tcx) + n1y * (qy - tcy) < 0:
                n1x, n1y = -n1x, -n1y
            ball.x = qx + n1x * (hit_r + 0.25)
            ball.y = qy + n1y * (hit_r + 0.25)
            vn = ball.vx * n1x + ball.vy * n1y
            if vn < 0:
                ball.vx -= (1.0 + BOUNCE) * vn * n1x
                ball.vy -= (1.0 + BOUNCE) * vn * n1y

    if hit_rubber:
        fresh = now >= lit_state.get(0, 0.0)
        vn_k = ball.vx * knx + ball.vy * kny
        if vn_k < 0.15:
            ball.vx += knx * UPPER_TRI_KICK
            ball.vy += kny * UPPER_TRI_KICK
        sp = ball.speed()
        if sp > MAX_SPEED:
            s = MAX_SPEED / sp
            ball.vx *= s
            ball.vy *= s
        if fresh:
            add_score(score_state, SCORE_TARGET)
        lit_state[0] = now + 0.14
    elif hit_any:
        sp = ball.speed()
        if sp > MAX_SPEED:
            s = MAX_SPEED / sp
            ball.vx *= s
            ball.vy *= s


def draw_slingshots(canvas, camera_y, slings, lit_until=None):
    """Draw triangular slingshot bodies + bright rubber faces."""
    lit_until = lit_until or {}
    now = time.time()
    for i, s in enumerate(slings):
        lit = now < lit_until.get(i, 0.0)
        body = SLING_LIT_RGB if lit else SLING_RGB
        rubber = (255, 220, 120) if lit else SLING_RUBBER
        v0, v1, v2 = s["verts"]
        # Body edges (AA)
        for (ax, ay), (bx, by) in ((v0, v1), (v1, v2), (v2, v0)):
            _draw_aa_flipper_blade(
                canvas, ax, ay, bx, by,
                body, (max(0, body[0] // 2), max(0, body[1] // 2), max(0, body[2] // 2)),
                camera_y, half_width=0.7,
            )
        # Rubber face thicker / brighter
        x1, y1, x2, y2 = s["rubber"]
        _draw_aa_flipper_blade(
            canvas, x1, y1, x2, y2,
            rubber, (rubber[0] // 2, rubber[1] // 2, rubber[2] // 2),
            camera_y, half_width=1.1,
        )


def _point_in_triangle(px, py, a, b, c):
    """True if (px, py) is inside triangle abc (inclusive edges)."""
    def _cross(ox, oy, ax, ay, bx, by):
        return (ax - ox) * (by - oy) - (ay - oy) * (bx - ox)

    c1 = _cross(a[0], a[1], b[0], b[1], px, py)
    c2 = _cross(b[0], b[1], c[0], c[1], px, py)
    c3 = _cross(c[0], c[1], a[0], a[1], px, py)
    has_neg = (c1 < 0) or (c2 < 0) or (c3 < 0)
    has_pos = (c1 > 0) or (c2 > 0) or (c3 > 0)
    return not (has_neg and has_pos)


def collide_slingshots(ball, slings, lit_until, score_state=None):
    """
    Solid triangular slingshot bodies — ball cannot pass through.

    All three edges are hard walls; the rubber face also applies the (reduced)
    solenoid kick toward center/up.
    """
    if ball.in_plunger or not slings:
        return
    now = time.time()
    hit_r = BALL_RADIUS + SLING_PAD
    for i, s in enumerate(slings):
        verts = s.get("verts")
        if not verts or len(verts) < 3:
            continue
        a, b, c = verts[0], verts[1], verts[2]
        cx = (a[0] + b[0] + c[0]) / 3.0
        cy = (a[1] + b[1] + c[1]) / 3.0
        rx1, ry1, rx2, ry2 = s["rubber"]
        knx, kny = s["kick"]
        edges = ((a, b), (b, c), (c, a))
        hit_rubber = False
        hit_any = False

        # 1) Solid edges — push out and reflect (no tunneling through walls)
        for (p1, p2) in edges:
            x1, y1 = p1
            x2, y2 = p2
            dist, qx, qy, _t = _dist_point_segment(ball.x, ball.y, x1, y1, x2, y2)
            if dist >= hit_r or dist < 1e-9:
                continue
            hit_any = True
            # Normal from edge toward ball; if ball is inside tri, force outward
            sx, sy = x2 - x1, y2 - y1
            sl = math.hypot(sx, sy) or 1.0
            n1x, n1y = -sy / sl, sx / sl
            n2x, n2y = sy / sl, -sx / sl
            # Prefer normal pointing away from triangle centroid
            if n1x * (qx - cx) + n1y * (qy - cy) > 0:
                nnx, nny = n1x, n1y
            else:
                nnx, nny = n2x, n2y
            # If ball is clearly outside, flip normal toward ball if needed
            to_bx, to_by = ball.x - qx, ball.y - qy
            if nnx * to_bx + nny * to_by < 0:
                nnx, nny = -nnx, -nny
            pen = hit_r - dist + 0.2
            ball.x += nnx * pen
            ball.y += nny * pen
            vn = ball.vx * nnx + ball.vy * nny
            if vn < 0:
                ball.vx -= (1.0 + BOUNCE) * vn * nnx
                ball.vy -= (1.0 + BOUNCE) * vn * nny
            # Rubber edge → score + kick (once per fresh hit window)
            is_rubber = (
                (abs(x1 - rx1) < 0.2 and abs(y1 - ry1) < 0.2
                 and abs(x2 - rx2) < 0.2 and abs(y2 - ry2) < 0.2)
                or (abs(x1 - rx2) < 0.2 and abs(y1 - ry2) < 0.2
                    and abs(x2 - rx1) < 0.2 and abs(y2 - ry1) < 0.2)
            )
            if is_rubber:
                hit_rubber = True

        # 2) If center is still inside the triangle, eject to nearest edge
        if _point_in_triangle(ball.x, ball.y, a, b, c):
            hit_any = True
            best = None
            best_d = 1e9
            for (p1, p2) in edges:
                dist, qx, qy, _t = _dist_point_segment(
                    ball.x, ball.y, p1[0], p1[1], p2[0], p2[1],
                )
                if dist < best_d:
                    best_d = dist
                    best = (p1, p2, qx, qy)
            if best is not None:
                p1, p2, qx, qy = best
                sx, sy = p2[0] - p1[0], p2[1] - p1[1]
                sl = math.hypot(sx, sy) or 1.0
                n1x, n1y = -sy / sl, sx / sl
                # Outward from centroid
                if n1x * (qx - cx) + n1y * (qy - cy) < 0:
                    n1x, n1y = -n1x, -n1y
                ball.x = qx + n1x * (hit_r + 0.25)
                ball.y = qy + n1y * (hit_r + 0.25)
                vn = ball.vx * n1x + ball.vy * n1y
                if vn < 0:
                    ball.vx -= (1.0 + BOUNCE) * vn * n1x
                    ball.vy -= (1.0 + BOUNCE) * vn * n1y

        if hit_rubber:
            fresh = now >= lit_until.get(i, 0.0)
            # Kick only if still moving into the rubber (or just hit)
            vn_k = ball.vx * knx + ball.vy * kny
            if vn_k < 0.15:
                ball.vx += knx * SLING_KICK
                ball.vy += kny * SLING_KICK
            sp = ball.speed()
            if sp > MAX_SPEED:
                s_scale = MAX_SPEED / sp
                ball.vx *= s_scale
                ball.vy *= s_scale
            if fresh:
                add_score(score_state, SCORE_SLING)
            lit_until[i] = now + 0.16
        elif hit_any:
            # Body bounce only — still cap speed
            sp = ball.speed()
            if sp > MAX_SPEED:
                s_scale = MAX_SPEED / sp
                ball.vx *= s_scale
                ball.vy *= s_scale


def _clock_total_width():
    """Pixel width of HH:MM in medium 7-seg layout."""
    return 4 * CLOCK_DIGIT_W + 3 * CLOCK_GAP + CLOCK_COLON_W


def _seg_hspan_world(canvas, ox, oy, x0, x1, y, thick, rgb, camera_y):
    """Horizontal segment bar in world pixels."""
    for yy in range(y, y + thick):
        for xx in range(x0, x1 + 1):
            _draw_world_pixel(canvas, ox + xx, oy + yy, rgb, camera_y)


def _seg_vspan_world(canvas, ox, oy, x, y0, y1, thick, rgb, camera_y):
    """Vertical segment bar in world pixels."""
    for xx in range(x, x + thick):
        for yy in range(y0, y1 + 1):
            _draw_world_pixel(canvas, ox + xx, oy + yy, rgb, camera_y)


def _draw_7seg_digit_world(canvas, ox, oy, digit, lit_rgb, dim_rgb, camera_y):
    """
    Draw one medium 7-element LED digit at world (ox, oy) top-left.

    Layout (w=5, h=9, thick=1):
        A A A
      F       B
      F       B
        G G G
      E       C
      E       C
        D D D
    """
    w = CLOCK_DIGIT_W
    h = CLOCK_DIGIT_H
    t = CLOCK_THICK
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
    for bit, kind, a, b, c in segs:
        on = (mask & bit) != 0
        if on:
            rgb = lit_rgb
        elif dim_rgb is not None:
            rgb = dim_rgb
        else:
            continue
        if kind == "h":
            _seg_hspan_world(canvas, ox, oy, a, b, c, t, rgb, camera_y)
        else:
            _seg_vspan_world(canvas, ox, oy, a, b, c, t, rgb, camera_y)


def _flip_digit_grid(digit):
    """3×5 on/off grid for digit 0–9 (from LEDarcade DigitList / DigitSpriteList)."""
    d = int(digit) % 10
    try:
        grid = LED.DigitList[d]
        if len(grid) >= FLIP_DIGIT_W * FLIP_DIGIT_H:
            return grid
    except Exception:
        pass
    try:
        spr = LED.DigitSpriteList[d]
        return spr.grid
    except Exception:
        pass
    # Fallback solid block
    return [1] * (FLIP_DIGIT_W * FLIP_DIGIT_H)


def _flip_card_size():
    """Outer size of one flip-clock digit card."""
    w = FLIP_DIGIT_W + FLIP_CARD_PAD_X * 2
    h = FLIP_DIGIT_H + FLIP_CARD_PAD_Y * 2 + 2  # +2 room for mid seam look
    return w, h


def _draw_world_pixel_clipped(canvas, wx, wy, rgb, camera_y, clip_y0=None, clip_y1=None):
    """World pixel with optional exclusive [clip_y0, clip_y1) vertical clip."""
    if clip_y0 is not None and wy < clip_y0:
        return
    if clip_y1 is not None and wy >= clip_y1:
        return
    _draw_world_pixel(canvas, wx, wy, rgb, camera_y)


def draw_flip_score(canvas, camera_y, score, oy=None, clip_y0=None, clip_y1=None):
    """
    5-digit 70s flip-clock score (world-space).

    Default: top of table. Pass oy / clip to draw inside the bottom apron
    during the post-drain score reveal animation.
    """
    text = f"{max(0, int(score)) % (SCORE_MAX + 1):0{SCORE_DIGITS}d}"
    card_w, card_h = _flip_card_size()
    total_w = SCORE_DIGITS * card_w + (SCORE_DIGITS - 1) * FLIP_CARD_GAP
    ox = max(0, int((MAP_W - total_w) // 2))
    if oy is None:
        oy = FLIP_SCORE_Y
    mid_off = card_h // 2

    def plot(wx, wy, rgb):
        _draw_world_pixel_clipped(canvas, wx, wy, rgb, camera_y, clip_y0, clip_y1)

    x = ox
    for ch in text:
        for yy in range(card_h):
            for xx in range(card_w):
                wx, wy = x + xx, oy + yy
                edge = (
                    xx == 0 or yy == 0
                    or xx == card_w - 1 or yy == card_h - 1
                )
                if edge:
                    rgb = FLIP_CARD_FRAME
                elif yy > mid_off:
                    rgb = FLIP_CARD_LOWER
                else:
                    rgb = FLIP_CARD_BG
                plot(wx, wy, rgb)
        for xx in range(1, card_w - 1):
            plot(x + xx, oy + mid_off, FLIP_CARD_SEAM)
        grid = _flip_digit_grid(ch)
        dx0 = x + FLIP_CARD_PAD_X
        dy0 = oy + FLIP_CARD_PAD_Y + 1
        for i, on in enumerate(grid):
            if not on or i >= FLIP_DIGIT_W * FLIP_DIGIT_H:
                continue
            r, c = divmod(i, FLIP_DIGIT_W)
            plot(dx0 + c, dy0 + r, FLIP_DIGIT_RGB)
        x += card_w + FLIP_CARD_GAP


def _draw_7seg_clock_row(canvas, camera_y, oy, blink_on=True, clip_y0=None, clip_y1=None):
    """Red 7-segment HH:MM at world y = oy (top of digits), optional y-clip."""
    now = time.localtime()
    digits = (now.tm_hour // 10, now.tm_hour % 10, now.tm_min // 10, now.tm_min % 10)
    total_w = _clock_total_width()
    ox = max(0, int((MAP_W - total_w) // 2))
    lit = CLOCK_RGB
    dim = CLOCK_DIM

    # Thin wrappers that honor apron clip
    def dig(oxd, oyd, d):
        w = CLOCK_DIGIT_W
        h = CLOCK_DIGIT_H
        t = CLOCK_THICK
        mid = h // 2
        hx0, hx1 = t, w - 1 - t
        vy0_top, vy1_top = t, mid - 1
        vy0_bot, vy1_bot = mid + t, h - 1 - t
        mask = _SEG_DIGIT_MASKS[int(d) % 10]
        segs = (
            (_SEG_A, "h", hx0, hx1, 0),
            (_SEG_G, "h", hx0, hx1, mid),
            (_SEG_D, "h", hx0, hx1, h - t),
            (_SEG_F, "v", 0, vy0_top, vy1_top),
            (_SEG_B, "v", w - t, vy0_top, vy1_top),
            (_SEG_E, "v", 0, vy0_bot, vy1_bot),
            (_SEG_C, "v", w - t, vy0_bot, vy1_bot),
        )
        for bit, kind, a, b, c in segs:
            on = (mask & bit) != 0
            if on:
                rgb = lit
            elif dim is not None:
                rgb = dim
            else:
                continue
            if kind == "h":
                for yy in range(c, c + t):
                    for xx in range(a, b + 1):
                        _draw_world_pixel_clipped(
                            canvas, oxd + xx, oyd + yy, rgb, camera_y, clip_y0, clip_y1,
                        )
            else:
                for xx in range(a, a + t):
                    for yy in range(b, c + 1):
                        _draw_world_pixel_clipped(
                            canvas, oxd + xx, oyd + yy, rgb, camera_y, clip_y0, clip_y1,
                        )

    x = ox
    dig(x, oy, digits[0])
    x += CLOCK_DIGIT_W + CLOCK_GAP
    dig(x, oy, digits[1])
    x += CLOCK_DIGIT_W + CLOCK_GAP
    colon_x = x
    mid = CLOCK_DIGIT_H // 2
    if blink_on:
        for dy in (mid - 2, mid + 1):
            for xx in range(CLOCK_COLON_W):
                _draw_world_pixel_clipped(
                    canvas, colon_x + xx, oy + dy, lit, camera_y, clip_y0, clip_y1,
                )
    x += CLOCK_COLON_W + CLOCK_GAP
    dig(x, oy, digits[2])
    x += CLOCK_DIGIT_W + CLOCK_GAP
    dig(x, oy, digits[3])


def update_apron_drain_anim(anim, dt):
    """
    Advance post-drain apron animation.

    Phases: to_score (clock ↓, score in from above) → hold →
    to_clock (score ↑ out, clock ↑ from below) → done.
    Returns True when the sequence has finished (plunger may charge).
    """
    if not anim or not anim.get("active"):
        return True
    phase = anim.get("phase") or "to_score"
    if phase == "to_score":
        anim["t"] = min(1.0, float(anim.get("t", 0.0)) + dt / max(0.05, APRON_SCROLL_SECONDS))
        if anim["t"] >= 1.0:
            anim["phase"] = "hold"
            anim["t"] = 1.0
            anim["hold_left"] = float(APRON_SCORE_HOLD_SECONDS)
    elif phase == "hold":
        anim["hold_left"] = float(anim.get("hold_left", APRON_SCORE_HOLD_SECONDS)) - dt
        if anim["hold_left"] <= 0.0:
            anim["phase"] = "to_clock"
            anim["t"] = 0.0
    elif phase == "to_clock":
        anim["t"] = min(1.0, float(anim.get("t", 0.0)) + dt / max(0.05, APRON_SCROLL_SECONDS))
        if anim["t"] >= 1.0:
            anim["active"] = False
            anim["phase"] = "done"
            anim["t"] = 0.0
            return True
    return False


def draw_bottom_apron_display(canvas, camera_y, score=0, anim=None, blink_on=True):
    """
    Bottom apron strip: normally the 7-seg clock.

    During post-drain anim (in place, table fixed):
      1) clock scrolls down, score scrolls in from above
      2) score holds 1s
      3) score scrolls up out, clock scrolls up from below into place
    Content is clipped to the apron so the playfield is not disturbed.
    """
    pf_bot = _playfield_bottom()
    apron_y0 = int(pf_bot)
    apron_y1 = int(MAP_H)
    apron_h = float(CLOCK_APRON_H)

    # Dark panel + top edge rail (always fixed)
    for wy in range(apron_y0, apron_y1):
        rgb = CLOCK_APRON_EDGE if wy == apron_y0 else CLOCK_APRON_RGB
        for wx in range(MAP_W):
            _draw_world_pixel(canvas, wx, wy, rgb, camera_y)

    base_oy = apron_y0 + max(1, (CLOCK_APRON_H - CLOCK_DIGIT_H) // 2)
    card_w, card_h = _flip_card_size()
    score_base_oy = apron_y0 + max(1, (CLOCK_APRON_H - card_h) // 2)

    active = anim and anim.get("active")
    phase = (anim or {}).get("phase")
    t = float((anim or {}).get("t", 0.0))
    # Ease scroll
    te = t * t * (3.0 - 2.0 * t)

    if not active or phase in (None, "done"):
        _draw_7seg_clock_row(
            canvas, camera_y, base_oy, blink_on=blink_on,
            clip_y0=apron_y0, clip_y1=apron_y1,
        )
        return

    if phase == "to_score":
        # Clock moves down; score enters from above
        clock_oy = base_oy + te * apron_h
        score_oy = score_base_oy - apron_h + te * apron_h
        _draw_7seg_clock_row(
            canvas, camera_y, int(round(clock_oy)), blink_on=blink_on,
            clip_y0=apron_y0, clip_y1=apron_y1,
        )
        draw_flip_score(
            canvas, camera_y, score, oy=int(round(score_oy)),
            clip_y0=apron_y0, clip_y1=apron_y1,
        )
    elif phase == "hold":
        draw_flip_score(
            canvas, camera_y, score, oy=score_base_oy,
            clip_y0=apron_y0, clip_y1=apron_y1,
        )
    elif phase == "to_clock":
        # Both scroll upward: score exits up; clock rises from below into place
        score_oy = score_base_oy - te * apron_h
        clock_oy = base_oy + apron_h - te * apron_h
        draw_flip_score(
            canvas, camera_y, score, oy=int(round(score_oy)),
            clip_y0=apron_y0, clip_y1=apron_y1,
        )
        _draw_7seg_clock_row(
            canvas, camera_y, int(round(clock_oy)), blink_on=blink_on,
            clip_y0=apron_y0, clip_y1=apron_y1,
        )


def draw_bottom_apron_clock(canvas, camera_y, blink_on=True):
    """Back-compat: static 7-seg clock on the apron."""
    draw_bottom_apron_display(canvas, camera_y, score=0, anim=None, blink_on=blink_on)


# ---------------- Main loop ----------------

def PlayPinball(Duration=10000, StopEvent=None):
    """
    Run the pinball table. Duration is minutes (LEDarcade convention).
    Ball launches from a right-hand plunger, climbs to three top bumpers,
    with a scrolling flip-clock score at the top and a 7-segment clock apron below.
    """
    global WIDTH, HEIGHT, MAP_W, MAP_H
    WIDTH = int(LED.HatWidth)
    HEIGHT = int(LED.HatHeight)
    MAP_W = WIDTH
    # Playfield height (+ table extra) + dedicated scrolling clock apron below
    MAP_H = HEIGHT * MAP_SCALE_Y + TABLE_EXTRA_H + CLOCK_APRON_H

    try:
        canvas = LED.TheMatrix.CreateFrameCanvas()
    except Exception:
        canvas = LED.Canvas

    # Classic bottom: flippers with open center drain; slings above/outside
    # Flippers sit on the playfield; apron with clock is below them.
    lane_l = _lane_left_x()
    flipper_y = _playfield_bottom() - FLIPPER_BOTTOM_INSET
    left_px, right_px, field_cx = place_flippers(lane_l, flipper_y)

    left = Flipper(
        pivot_x=left_px,
        pivot_y=flipper_y,
        rest_angle=LEFT_REST,
        active_angle=LEFT_ACTIVE,
        length=FLIPPER_LEN,
        side="left",
    )
    right = Flipper(
        pivot_x=right_px,
        pivot_y=flipper_y,
        rest_angle=RIGHT_REST,
        active_angle=RIGHT_ACTIVE,
        length=FLIPPER_LEN,
        side="right",
    )

    # Upper-third side flippers (symmetric, almost touching the walls)
    up_left_px, up_right_px, up_flipper_y = place_upper_flippers(lane_l)
    up_left = Flipper(
        pivot_x=up_left_px,
        pivot_y=up_flipper_y,
        rest_angle=LEFT_REST,
        active_angle=LEFT_ACTIVE,
        length=UPPER_FLIPPER_LEN,
        side="left",
        swing_speed=UPPER_FLIPPER_SWING_SPEED,
        power=UPPER_FLIPPER_POWER,
    )
    up_right = Flipper(
        pivot_x=up_right_px,
        pivot_y=up_flipper_y,
        rest_angle=RIGHT_REST,
        active_angle=RIGHT_ACTIVE,
        length=UPPER_FLIPPER_LEN,
        side="right",
        swing_speed=UPPER_FLIPPER_SWING_SPEED,
        power=UPPER_FLIPPER_POWER,
    )
    upper_tri = build_upper_bounce_triangle(up_left_px, up_right_px, up_flipper_y)
    upper_tri_lit = {}
    ut = upper_tri["verts"]
    print(
        f"[pinball] upper flippers y={up_flipper_y:.1f} "
        f"pivots=({up_left_px:.1f},{up_right_px:.1f}) "
        f"len={UPPER_FLIPPER_LEN}  "
        f"bounce_tri side={UPPER_TRI_SIDE:.0f} "
        f"centroid=({(ut[0][0]+ut[1][0]+ut[2][0])/3:.1f},"
        f"{(ut[0][1]+ut[1][1]+ut[2][1])/3:.1f})"
    )

    slings = build_slingshots(left_px, right_px, flipper_y, lane_l)
    outlane_guides = build_outlane_guides(
        left_px, right_px, flipper_y, lane_l, slings=slings,
    )
    # Grey guide posts sit at the very top of each outlane rail (into bottom flippers)
    toys = _layout_playfield_toys()
    for g in outlane_guides:
        pts = g.get("points") or ()
        if pts:
            toys.setdefault("posts", []).append(
                (float(pts[0][0]), float(pts[0][1]))
            )
    flipper_ai_state = {}
    upper_ai_state = {}
    # Debug classic lower layout once at start
    lt = _flipper_rest_tip(left_px, flipper_y, LEFT_REST, FLIPPER_LEN)
    rt = _flipper_rest_tip(right_px, flipper_y, RIGHT_REST, FLIPPER_LEN)
    tip_gap = rt[0] - lt[0]
    lv = slings[0]["verts"]
    rv = slings[1]["verts"]
    # Apex = most-inboard vertex of each sling triangle
    l_apex = max(v[0] for v in lv)
    r_apex = min(v[0] for v in rv)
    l_guide_x = outlane_guides[0].get("x", 0.0)
    r_guide_x = outlane_guides[1].get("x", 0.0)
    l_sling_x = _sling_outer_x(slings[0], "left")
    r_sling_x = _sling_outer_x(slings[1], "right")
    print(
        f"[pinball] classic bottom: tip_gap={tip_gap:.1f} "
        f"(need>={FLIPPER_DRAIN_GAP:.1f}, hit_r={_FLIPPER_HIT_R:.1f})  "
        f"pivots=({left_px:.1f},{right_px:.1f})  "
        f"sling_apex=({l_apex:.1f}..{r_apex:.1f})  "
        f"drain_open={r_apex - l_apex:.1f}  "
        f"guides mid wall/sling L={l_guide_x:.1f} "
        f"(wall0–sling{l_sling_x:.1f}) R={r_guide_x:.1f} "
        f"(sling{r_sling_x:.1f}–wall{lane_l:.1f})"
    )
    drop_targets = make_drop_targets()
    drop_bank_timers = {}
    ramps = build_skill_ramps()
    ramp_states = [{"cooldown": 0} for _ in ramps]
    if ramps:
        print(
            f"[pinball] skill ramps×{len(ramps)}  base={RAMP_BASE_W:.0f} "
            f"top={RAMP_TOP_W:.0f} h={RAMP_H:.0f}  "
            f"cx=({ramps[0]['cx']:.1f},{ramps[1]['cx']:.1f})  "
            f"sep={ramps[1]['cx'] - ramps[0]['cx']:.1f}  "
            f"y={ramps[0]['top_y']:.1f}..{ramps[0]['bottom_y']:.1f}"
        )
    standup_lit = {}
    spinner_states = make_spinner_states(toys.get("spinners"))
    rollover_lit = [False] * len(toys["rollovers"])
    saucer_state = {
        "held": False,
        "phase": None,
        "timer": 0,
        "from_i": None,
        "to_i": None,
        "focus_y": None,
        "cooldown": [0, 0, 0, 0],
    }

    ball = Ball(0, 0)
    ball.place_in_plunger()
    score_state = {"score": 0}
    # Post-drain apron anim: clock scrolls out → score holds 1s → clock returns
    apron_anim = {
        "active": False,
        "phase": "done",
        "t": 0.0,
        "hold_left": 0.0,
    }
    apron_relaunch_ready = False

    # Plunger state: idle → charging → fire → in_play
    # Each charge picks a random pull strength (soft / medium / full crank)
    def _pick_plunger_strength():
        # Bias slightly toward mid pulls; still spans soft tip-in → full power
        r = random.random()
        if r < 0.22:
            return random.uniform(PLUNGER_STRENGTH_MIN, 0.58)   # soft
        if r < 0.55:
            return random.uniform(0.58, 0.82)                   # medium
        if r < 0.82:
            return random.uniform(0.82, 0.95)                   # strong
        return random.uniform(0.95, PLUNGER_STRENGTH_MAX)       # full crank

    plunger_phase = "charging"  # auto-fire for demo play
    plunger_timer = 0
    plunger_charge = 0.0
    plunger_target = _pick_plunger_strength()
    plunger_last_power = 0.0
    plunger_climbed = False     # ball went up the lane after fire
    bumper_lit = {}
    sling_lit = {}

    camera_y = camera_for_ball(ball.y)
    frame = 0
    start = time.time()
    tick_clock = pygame.time.Clock() if HAS_PYGAME else None

    print(
        f"[pinball] EM layout {MAP_W}x{MAP_H} (×{MAP_SCALE_Y}): "
        f"pops, side mid bumpers, long-rubber slings, drops, standups, "
        f"posts, {len(toys.get('spinners') or [])} spinners, "
        f"rollovers, {len(toys.get('saucers') or [])} saucers  fps={TARGET_FPS}"
    )

    try:
        while True:
            if _stop(StopEvent):
                print("[pinball] StopEvent — exit")
                break
            if Duration and (time.time() - start > float(Duration) * 60):
                print("[pinball] Duration reached — exit")
                break

            # --- Plunger sequence (varied pull strengths + failed-launch retry) ---
            if ball.alive and ball.in_plunger:
                if plunger_phase == "idle":
                    plunger_timer += 1
                    if plunger_timer >= PLUNGER_RELOAD_FRAMES:
                        plunger_phase = "charging"
                        plunger_timer = 0
                        plunger_charge = 0.0
                        plunger_target = _pick_plunger_strength()
                        plunger_climbed = False
                elif plunger_phase == "charging":
                    plunger_timer += 1
                    # Charge only as far as this shot's target pull (varied strokes)
                    charge_frames = max(
                        6, int(round(PLUNGER_CHARGE_FRAMES * max(0.35, plunger_target)))
                    )
                    plunger_charge = min(
                        plunger_target,
                        plunger_timer / float(PLUNGER_CHARGE_FRAMES),
                    )
                    # Hold ball on the rising spring cup (deeper pull = more compress)
                    ball.x = MAP_W - 1.5
                    ball.y = _playfield_bottom() - 4.0 - plunger_charge * 5.0
                    ball.vx = ball.vy = 0.0
                    if plunger_timer >= charge_frames:
                        # Strength varies exit speed; floor guarantees chute clear
                        min_p = plunger_min_exit_power()
                        power = plunger_power_for_strength(plunger_target, min_p)
                        power *= random.uniform(0.98, 1.03)
                        if plunger_last_power > 0:
                            power = max(power, plunger_last_power)
                        # Never below exit floor, never above retry cap
                        power = _clamp(power, min_p, PLUNGER_RETRY_MAX_POWER)
                        ball.fire_plunger(power)
                        plunger_last_power = power
                        plunger_phase = "fired"
                        plunger_timer = 0
                        plunger_charge = 0.0
                        plunger_climbed = False
                        print(
                            f"[pinball] Plunger fired  "
                            f"strength={plunger_target:.0%}  power={power:.2f}  "
                            f"(exit_floor={min_p:.2f})"
                        )
                elif plunger_phase == "fired":
                    plunger_timer += 1
                    pf_bot = _playfield_bottom()
                    # Track whether the ball climbed the lane after launch
                    if ball.y < pf_bot - PLUNGER_CLIMB_CLEAR:
                        plunger_climbed = True
                    # Cresting high in the lane → force chute exit (guarantee leave)
                    mid_lane = 0.5 * (pf_bot + _plunger_exit_y())
                    if (
                        ball.in_plunger
                        and plunger_climbed
                        and ball.y < mid_lane
                        and ball.vy > 0.05
                    ):
                        force_plunger_exit(ball, retain_speed=True)
                        print("[pinball] Plunger crest → forced chute exit")
                    # Successful handoff into the playfield
                    if not ball.in_plunger:
                        plunger_phase = "in_play"
                        plunger_climbed = False
                        plunger_last_power = 0.0
                    # Rare stall: went up, fell all the way back — boost & re-pull
                    elif (
                        plunger_climbed
                        and plunger_timer >= PLUNGER_RETRY_MIN_FRAMES
                        and ball.y >= pf_bot - PLUNGER_RETURN_Y
                        and ball.speed() <= PLUNGER_RETURN_SPEED
                        and ball.vy >= -0.08
                    ):
                        old_str = plunger_target
                        old_pwr = plunger_last_power
                        plunger_target = min(
                            PLUNGER_STRENGTH_MAX,
                            max(plunger_target, 0.85) + PLUNGER_RETRY_STRENGTH_BOOST,
                        )
                        min_p = plunger_min_exit_power()
                        plunger_last_power = min(
                            PLUNGER_RETRY_MAX_POWER,
                            max(
                                old_pwr * PLUNGER_RETRY_POWER_SCALE,
                                plunger_power_for_strength(plunger_target, min_p),
                                min_p * 1.05,
                            ),
                        )
                        ball.place_in_plunger()
                        plunger_phase = "charging"
                        plunger_timer = 0
                        plunger_charge = 0.0
                        plunger_climbed = False
                        print(
                            f"[pinball] Plunger short — retry  "
                            f"strength {old_str:.0%}→{plunger_target:.0%}  "
                            f"power {old_pwr:.2f}→{plunger_last_power:.2f}"
                        )
            elif not ball.alive:
                # Drain: apron anim in place (clock ↓ score ↑ hold clock ↑) then plunger
                plunger_phase = "idle"
                plunger_timer = 0
                plunger_charge = 0.0
                plunger_climbed = False
                plunger_last_power = 0.0
                # Kick off apron sequence once per drain
                if (
                    not apron_anim.get("active")
                    and not apron_relaunch_ready
                    and apron_anim.get("phase") in (None, "done", "idle")
                ):
                    apron_anim["active"] = True
                    apron_anim["phase"] = "to_score"
                    apron_anim["t"] = 0.0
                    apron_anim["hold_left"] = APRON_SCORE_HOLD_SECONDS
                    print(
                        f"[pinball] Ball drained — score={score_state['score']:05d}  "
                        f"apron clock→score reveal"
                    )
                if apron_anim.get("active"):
                    if update_apron_drain_anim(apron_anim, 1.0 / float(TARGET_FPS)):
                        apron_relaunch_ready = True
                if apron_relaunch_ready and not apron_anim.get("active"):
                    ball.place_in_plunger()
                    plunger_phase = "charging"
                    plunger_target = _pick_plunger_strength()
                    apron_relaunch_ready = False
                    apron_anim["phase"] = "done"
                    print(
                        f"[pinball] Re-launch after apron score reveal  "
                        f"score={score_state['score']:05d}"
                    )

            # --- Skill flipper AI: bottom pair + upper side pair ---
            if not ball.in_plunger and not saucer_state.get("held"):
                flipper_ai_state = update_flipper_ai(
                    ball, left, right, frame, ai_state=flipper_ai_state,
                )
                upper_ai_state = update_upper_flipper_ai(
                    ball, up_left, up_right, frame, ai_state=upper_ai_state,
                )
            else:
                left.set_pressed(False)
                right.set_pressed(False)
                up_left.set_pressed(False)
                up_right.set_pressed(False)
            left.update()
            right.update()
            up_left.update()
            up_right.update()

            # --- Saucers once per frame (vanish/pan timers must not run ×substeps) ---
            if ball.alive:
                update_saucers(
                    ball,
                    toys.get("saucers") or [toys["saucer"]],
                    saucer_state,
                    score_state,
                )

            # --- Physics (fixed substeps = smoother, less jitter / tunneling) ---
            if ball.alive and not saucer_state.get("held"):
                step_scale = 1.0 / float(PHYSICS_SUBSTEPS)
                for _ in range(PHYSICS_SUBSTEPS):
                    ball.integrate(dt_scale=step_scale)
                    collide_walls(ball)
                    if not ball.in_plunger:
                        airborne = ball.is_airborne()
                        collide_top_arc(ball)
                        # Bumpers stay live — ramp jump lands in the upper cluster
                        collide_bumpers(ball, bumper_lit, score_state)
                        if not airborne:
                            # Mid-table toys the ramp jump should clear
                            collide_drop_targets(ball, drop_targets, score_state)
                            collide_standups(
                                ball, toys["standups"], standup_lit, score_state,
                            )
                            collide_posts(ball, toys["posts"])
                            collide_spinners(
                                ball, toys.get("spinners"), spinner_states,
                            )
                            collide_rollovers(
                                ball, toys["rollovers"], rollover_lit, score_state,
                            )
                            collide_outlane_guides(ball, outlane_guides)
                            collide_slingshots(ball, slings, sling_lit, score_state)
                            collide_bounce_triangle(
                                ball, upper_tri, upper_tri_lit, score_state,
                            )
                            collide_ramps(ball, ramps, ramp_states)
                        collide_flipper(ball, left)
                        collide_flipper(ball, right)
                        collide_flipper(ball, up_left)
                        collide_flipper(ball, up_right)
                        collide_top_arc(ball)
                        ensure_ball_inside_arc(ball)
                    clamp_ball_on_table(ball)
                # Tick airborne once per frame (not per substep)
                if ball.is_airborne():
                    ball.airborne = max(0, int(ball.airborne) - 1)

            update_spinners(spinner_states)
            drop_bank_timers, just_reset = update_drop_targets(
                drop_targets, drop_bank_timers,
            )
            if just_reset:
                print("[pinball] Drop-target bank reset")
                # Light all rollovers off on bank reset (fresh cycle)
                for i in range(len(rollover_lit)):
                    rollover_lit[i] = False

            # Camera: pan with ball; saucer focus during vanish/pan; drain linger
            if saucer_state.get("held") and saucer_state.get("focus_y") is not None:
                camera_y = camera_for_ball(
                    float(saucer_state["focus_y"]), prev_camera=camera_y,
                )
            elif ball.alive:
                camera_y = camera_for_ball(ball.y, prev_camera=camera_y)
            else:
                camera_y = camera_for_ball(
                    _playfield_bottom() - 4.0, prev_camera=camera_y,
                )

            # --- Draw ---
            canvas.Fill(0, 0, 0)
            draw_background(canvas, camera_y, plunger_charge=plunger_charge)
            # Top flip-clock score (scrolls with the playfield)
            draw_flip_score(canvas, camera_y, score_state.get("score", 0))
            draw_rollovers(canvas, camera_y, toys["rollovers"], rollover_lit)
            draw_posts(canvas, camera_y, toys["posts"])
            draw_bumpers(canvas, camera_y, lit_until=bumper_lit)
            draw_drop_targets(canvas, camera_y, drop_targets)
            draw_standups(canvas, camera_y, toys["standups"], lit_until=standup_lit)
            draw_ramps(canvas, camera_y, ramps)
            draw_spinners(canvas, camera_y, toys.get("spinners"), spinner_states)
            draw_saucers(
                canvas, camera_y,
                toys.get("saucers") or [toys["saucer"]],
                saucer_state,
            )
            draw_outlane_guides(canvas, camera_y, outlane_guides)
            draw_slingshots(canvas, camera_y, slings, lit_until=sling_lit)
            draw_bounce_triangle(
                canvas, camera_y, upper_tri,
                lit=time.time() < upper_tri_lit.get(0, 0.0),
            )
            left.draw(canvas, camera_y)
            right.draw(canvas, camera_y)
            up_left.draw(canvas, camera_y)
            up_right.draw(canvas, camera_y)
            # Draw ball during vanish (fading); hide fully during pan (visible=0)
            if ball.alive and (
                not saucer_state.get("held")
                or saucer_state.get("phase") == "vanish"
                or float(getattr(ball, "visible", 1.0)) > 0.02
            ):
                ball.draw(canvas, camera_y)
            # Bottom apron: clock, or post-drain clock↔score scroll (table fixed)
            draw_bottom_apron_display(
                canvas, camera_y,
                score=score_state.get("score", 0),
                anim=apron_anim,
                blink_on=(int(time.time()) % 2 == 0),
            )

            canvas = LED.TheMatrix.SwapOnVSync(canvas)
            LED.Canvas = canvas

            if tick_clock:
                tick_clock.tick(TARGET_FPS)
            else:
                time.sleep(1.0 / TARGET_FPS)

            frame += 1
            if frame % 400 == 0:
                print(
                    f"[pinball] frame={frame} ball=({ball.x:.1f},{ball.y:.1f}) "
                    f"lane={ball.in_plunger} cam_y={camera_y:.1f} "
                    f"score={score_state.get('score', 0):05d} "
                    f"clock={time.strftime('%H:%M')}"
                )

    except KeyboardInterrupt:
        print("[pinball] Interrupted")

    try:
        LED.ClearBuffers()
        LED.TheMatrix.Clear()
    except Exception:
        pass


# ===========================================================================
# Title intro — fade-in letters + silver ball knockdown (Skyfall parallax bg)
# ===========================================================================
PB_TITLE_LINE1 = "PINBALL"
PB_TITLE_LINE2 = "TIME"
PB_TITLE_ZOOM = 1
PB_TITLE_SCALE = 1.0            # normal-size intro letters
PB_TITLE_GAP = 1
PB_TITLE_LINE_GAP = 2
# Red / amber pinball palette
PB_TITLE_SHADES = (
    (120, 20, 20),
    (180, 30, 30),
    (220, 45, 40),
    (255, 70, 50),
    (255, 120, 40),
    (255, 170, 50),
    (255, 200, 70),
    (200, 40, 40),
    (255, 90, 60),
    (160, 25, 25),
    (240, 140, 45),
    (255, 60, 55),
)
PB_SHADOW_SCALE = 0.28
# Fade letters into existence (slow)
PB_FADE_IN_SECONDS = 2.4
PB_FADE_STAGGER = 0.12          # delay between letters starting their fade
PB_HOLD_SECONDS = 0.45          # fully visible before the ball enters
# Big silver ball arrives from a random angle aimed at screen center
PB_INTRO_BALL_R = 4.2           # collision / draw radius (big pinball)
PB_INTRO_BALL_SPEED = 1.15 * 1.25 * 2.0  # prior intro speed, then 2× faster
PB_INTRO_BALL_GRAVITY = 0.008
PB_INTRO_BALL_BOUNCE = 0.72
PB_KNOCK_IMPULSE = 2.4
PB_LETTER_GRAVITY = 0.16
PB_LETTER_BOUNCE = 0.58         # floor / wall restitution
PB_LETTER_FRICTION = 0.88       # horizontal friction on floor bounce
PB_LETTER_SPIN_DAMP = 0.985
PB_LETTER_AIR_DRAG = 0.995
PB_SCATTER_SECONDS = 3.2        # max time after first hit before cut
PB_INTRO_MAX_SECONDS = 20.0
PB_INTRO_FPS = 30


def _pb_letter_sprite(char):
    ch = char.upper()
    if not ("A" <= ch <= "Z"):
        return None
    idx = ord(ch) - ord("A")
    try:
        return LED.TrimSprite(copy.deepcopy(LED.AlphaSpriteList[idx]))
    except Exception:
        return None


def _pb_sprite_pixels(sprite, zoom, rgb, shadow_rgb):
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


def _pb_shade(i):
    return PB_TITLE_SHADES[i % len(PB_TITLE_SHADES)]


def _pb_shadow(rgb):
    return tuple(max(0, int(c * PB_SHADOW_SCALE)) for c in rgb)


class PbTitleLetter(object):
    """Title letter: fade in at rest, then bounce/tumble when knocked by the ball."""

    def __init__(self, char, pixels, shadow_pixels, width, height, rest_x, rest_y, fade_delay):
        self.char = char
        self.pixels = pixels
        self.shadow_pixels = shadow_pixels
        self.width = width
        self.height = height
        self.rest_x = float(rest_x)
        self.rest_y = float(rest_y)
        self.x = float(rest_x)
        self.y = float(rest_y)
        self.vx = 0.0
        self.vy = 0.0
        self.angle = 0.0          # radians — tumble orientation
        self.omega = 0.0          # angular velocity
        self.fade_delay = float(fade_delay)
        self.alpha = 0.0
        self.knocked = False
        self.visible = True
        self.bounces = 0

    def center(self):
        return self.x + self.width * 0.5, self.y + self.height * 0.5

    def update_fade(self, elapsed):
        """Slowly raise alpha after stagger delay. Returns True when fully in."""
        t = elapsed - self.fade_delay
        if t <= 0:
            self.alpha = 0.0
            return False
        self.alpha = min(1.0, t / PB_FADE_IN_SECONDS)
        return self.alpha >= 1.0

    def knock(self, ball_x, ball_y, ball_vx, ball_vy):
        """Launch letter away from ball impact with realistic spin (torque)."""
        if self.knocked:
            return
        self.knocked = True
        self.alpha = 1.0
        cx, cy = self.center()
        dx = cx - ball_x
        dy = cy - ball_y
        dist = math.hypot(dx, dy) or 1.0
        nx, ny = dx / dist, dy / dist
        # Linear impulse: ball momentum + outward normal
        self.vx = ball_vx * 0.65 + nx * PB_KNOCK_IMPULSE + random.uniform(-0.35, 0.35)
        self.vy = ball_vy * 0.55 + ny * PB_KNOCK_IMPULSE * 0.9 - random.uniform(0.4, 1.1)
        # Torque from off-center hit: r × F  (2D: dx*Fy - dy*Fx)
        fx = ball_vx * 0.4 + nx * PB_KNOCK_IMPULSE
        fy = ball_vy * 0.4 + ny * PB_KNOCK_IMPULSE
        torque = dx * fy - dy * fx
        self.omega = _clamp(torque * 0.08, -0.55, 0.55) + random.uniform(-0.12, 0.12)

    def update_flight(self, step, panel_w, panel_h):
        """Gravity, tumble, and elastic bounces off floor/walls."""
        if not self.knocked:
            return
        self.vy += PB_LETTER_GRAVITY * step
        self.vx *= PB_LETTER_AIR_DRAG
        self.vy *= PB_LETTER_AIR_DRAG
        self.x += self.vx * step
        self.y += self.vy * step
        self.angle += self.omega * step
        self.omega *= PB_LETTER_SPIN_DAMP

        # Approximate AABB in world space for bounce (pre-rotation extents)
        hw = self.width * 0.5
        hh = self.height * 0.5
        cx, cy = self.center()

        # Floor
        floor = panel_h - 1.0
        if cy + hh >= floor and self.vy > 0:
            cy = floor - hh
            self.y = cy - hh
            self.vy = -abs(self.vy) * PB_LETTER_BOUNCE
            self.vx *= PB_LETTER_FRICTION
            # Spin couples to floor friction
            self.omega = -self.omega * 0.65 + self.vx * 0.04
            self.bounces += 1
            if abs(self.vy) < 0.22 and abs(self.vx) < 0.18:
                self.vy = 0.0
                self.vx *= 0.5
                self.omega *= 0.4

        # Ceiling
        if cy - hh <= 0 and self.vy < 0:
            cy = hh
            self.y = cy - hh
            self.vy = abs(self.vy) * PB_LETTER_BOUNCE
            self.omega = -self.omega * 0.7
            self.bounces += 1

        # Left / right walls
        if cx - hw <= 0 and self.vx < 0:
            cx = hw
            self.x = cx - hw
            self.vx = abs(self.vx) * PB_LETTER_BOUNCE
            self.omega = -self.omega * 0.75 + random.uniform(-0.05, 0.05)
            self.bounces += 1
        elif cx + hw >= panel_w - 1 and self.vx > 0:
            cx = panel_w - 1 - hw
            self.x = cx - hw
            self.vx = -abs(self.vx) * PB_LETTER_BOUNCE
            self.omega = -self.omega * 0.75 + random.uniform(-0.05, 0.05)
            self.bounces += 1

        # Slow fade only after several bounces / low energy
        speed = math.hypot(self.vx, self.vy)
        if self.bounces >= 2 and speed < 0.35:
            self.alpha = max(0.0, self.alpha - 0.02 * step)
        elif self.bounces >= 4:
            self.alpha = max(0.0, self.alpha - 0.015 * step)

    def on_screen(self, panel_w, panel_h, margin=8):
        if self.alpha <= 0.02:
            return False
        return (
            self.x + self.width > -margin
            and self.x < panel_w + margin
            and self.y + self.height > -margin
            and self.y < panel_h + margin
        )

    def hits_ball(self, bx, by, br):
        """AABB vs circle (approx) for knockdown trigger."""
        if self.knocked or self.alpha < 0.5:
            return False
        cx = max(self.x, min(bx, self.x + self.width))
        cy = max(self.y, min(by, self.y + self.height))
        return (bx - cx) ** 2 + (by - cy) ** 2 <= br * br

    def draw(self, canvas, panel_w, panel_h):
        if not self.visible or self.alpha <= 0.02:
            return
        fade = max(0.0, min(1.0, self.alpha))
        set_px = canvas.SetPixel
        cx, cy = self.center()
        cos_a = math.cos(self.angle)
        sin_a = math.sin(self.angle)
        ox = self.width * 0.5
        oy = self.height * 0.5

        def plot(dx, dy, rgb):
            # Rotate around letter center (tumble)
            lx = dx - ox
            ly = dy - oy
            rx = lx * cos_a - ly * sin_a
            ry = lx * sin_a + ly * cos_a
            px = int(round(cx + rx))
            py = int(round(cy + ry))
            if 0 <= px < panel_w and 0 <= py < panel_h:
                set_px(
                    px, py,
                    int(rgb[0] * fade), int(rgb[1] * fade), int(rgb[2] * fade),
                )

        for dx, dy, rgb in self.shadow_pixels:
            plot(dx, dy, rgb)
        for dx, dy, rgb in self.pixels:
            plot(dx, dy, rgb)


def _build_pb_title_letters(panel_w, panel_h):
    lines = [PB_TITLE_LINE1, PB_TITLE_LINE2]
    line_specs = []
    max_h = 0
    shade_i = 0
    for line in lines:
        specs = []
        for char in line:
            if char == " ":
                continue
            sprite = _pb_letter_sprite(char)
            if sprite is None:
                continue
            rgb = _pb_shade(shade_i)
            shade_i += 1
            shadow = _pb_shadow(rgb)
            pixels, shadow_pixels, lw, lh = _pb_sprite_pixels(
                sprite, PB_TITLE_ZOOM, rgb, shadow,
            )
            specs.append((char, pixels, shadow_pixels, lw, lh))
            if lh > max_h:
                max_h = lh
        line_specs.append(specs)

    if not any(line_specs):
        return []

    total_h = max_h * len(line_specs) + PB_TITLE_LINE_GAP * max(0, len(line_specs) - 1)
    top_y = max(0, (panel_h - total_h) // 2)

    letters = []
    letter_index = 0
    for line_i, specs in enumerate(line_specs):
        if not specs:
            continue
        total_w = sum(s[3] for s in specs) + PB_TITLE_GAP * max(0, len(specs) - 1)
        x_cursor = max(0, (panel_w - total_w) // 2)
        rest_y = top_y + line_i * (max_h + PB_TITLE_LINE_GAP)
        for char, pixels, shadow_pixels, lw, lh in specs:
            letters.append(PbTitleLetter(
                char, pixels, shadow_pixels, lw, lh,
                x_cursor, rest_y + (max_h - lh),
                fade_delay=letter_index * PB_FADE_STAGGER,
            ))
            x_cursor += lw + PB_TITLE_GAP
            letter_index += 1
    return letters


def _spawn_intro_ball(letters, panel_w, panel_h):
    """
    Place the silver ball off-screen at a random approach angle and aim it
    straight at the panel center so it drives through the title.
    """
    # Always head toward screen center (title is centered on top of it)
    ax = panel_w * 0.5
    ay = panel_h * 0.5

    # Random approach angle (from outside the panel)
    theta = random.uniform(0.0, 2.0 * math.pi)
    # Prefer side entries a bit more than pure vertical
    if random.random() < 0.55:
        theta = random.choice((
            random.uniform(-0.5, 0.5),                 # from left
            random.uniform(math.pi - 0.5, math.pi + 0.5),  # from right
            random.uniform(0.3, math.pi - 0.3),        # from top-ish
            random.uniform(-math.pi + 0.3, -0.3),      # from bottom-ish
        ))

    dist = max(panel_w, panel_h) * random.uniform(0.65, 0.95) + PB_INTRO_BALL_R * 2
    ball_x = ax + math.cos(theta) * dist
    ball_y = ay + math.sin(theta) * dist

    # Velocity toward center
    dx = ax - ball_x
    dy = ay - ball_y
    d = math.hypot(dx, dy) or 1.0
    speed = PB_INTRO_BALL_SPEED * random.uniform(0.95, 1.15)
    ball_vx = (dx / d) * speed
    ball_vy = (dy / d) * speed
    return ball_x, ball_y, ball_vx, ball_vy


def _draw_intro_silver_ball(canvas, bx, by, radius, panel_w, panel_h):
    """Large metallic ball (highlight + shade) for the intro knockdown."""
    cx, cy = int(round(bx)), int(round(by))
    r = max(2, int(round(radius)))
    r2 = r * r
    set_px = canvas.SetPixel
    for oy in range(-r, r + 1):
        for ox in range(-r, r + 1):
            d2 = ox * ox + oy * oy
            if d2 > r2:
                continue
            px, py = cx + ox, cy + oy
            if not (0 <= px < panel_w and 0 <= py < panel_h):
                continue
            # Radial shading toward bottom-right, bright upper-left
            n = math.sqrt(d2) / max(1.0, float(r))
            light = 0.55 + 0.45 * max(0.0, (-ox * 0.4 - oy * 0.7) / max(1.0, r) + 0.35)
            light = max(0.25, min(1.15, light * (1.0 - 0.35 * n * n)))
            # Core silver
            base = 200.0 * light
            if ox <= -r * 0.25 and oy <= -r * 0.2 and d2 < (r * 0.45) ** 2:
                # Specular highlight
                set_px(px, py, 255, 255, 255)
            else:
                set_px(
                    px, py,
                    min(255, int(base + 25)),
                    min(255, int(base + 30)),
                    min(255, int(base + 40)),
                )


def _import_skyfall_parallax():
    """Lazy-import Skyfall parallax builders/drawers (avoids load cost when intro off)."""
    import Skyfall as SF
    return SF


def PlayPinballTitleIntro(StopEvent=None):
    """
    PINBALL / TIME title on Skyfall parallax:
      1) Letters slowly fade into existence
      2) Hold briefly
      3) Big silver ball rolls in toward center and knocks letters away
    """
    panel_w = int(getattr(LED, "HatWidth", WIDTH) or WIDTH)
    panel_h = int(getattr(LED, "HatHeight", HEIGHT) or HEIGHT)
    letters = _build_pb_title_letters(panel_w, panel_h)

    try:
        canvas = LED.TheMatrix.CreateFrameCanvas()
    except Exception:
        canvas = LED.Canvas

    if not letters:
        print("[pinball] Title intro skipped (no letter sprites)")
        return

    if _stop(StopEvent):
        print("[pinball] Title intro skipped (StopEvent)")
        return

    print("[pinball] Title intro — fade-in, silver ball knockdown, Skyfall parallax")

    # --- Skyfall multi-layer parallax maps ---
    try:
        SF = _import_skyfall_parallax()
        SF.WIDTH = panel_w
        SF.HEIGHT = panel_h
        (
            far_layer,
            near_layer,
            giant_layer,
            planet_layer,
            _layer_h,
            giant_height,
            planet_height,
        ) = SF._build_parallax_layers(panel_w, panel_h)
        far_speed = SF.FAR_SCROLL_SPEED
        near_speed = SF.NEAR_SCROLL_SPEED
        giant_speed = SF.GAS_GIANT_SCROLL_SPEED
        planet_speed = SF.PLANET_SCROLL_SPEED
        draw_layer = SF._draw_parallax_layer
        use_skyfall = True
        print("[pinball] Skyfall parallax layers ready")
    except Exception as exc:
        print(f"[pinball] Skyfall parallax unavailable ({exc}) — black backdrop")
        use_skyfall = False
        far_layer = near_layer = giant_layer = planet_layer = None
        far_speed = near_speed = giant_speed = planet_speed = 0.0
        giant_height = planet_height = 1
        draw_layer = None

    far_scroll = 0.0
    near_scroll = 0.0
    giant_scroll = 0.0
    planet_scroll = 0.0
    tick = 0

    # Ball spawns from a random angle, aimed at panel center
    ball_x, ball_y, ball_vx, ball_vy = _spawn_intro_ball(letters, panel_w, panel_h)
    ball_active = False
    first_hit_time = None

    start = time.time()
    last = start
    phase = "fade_in"  # → hold → ball → done
    hold_start = None
    clock = pygame.time.Clock() if HAS_PYGAME else None

    def _paint():
        nonlocal canvas
        canvas.Fill(0, 0, 0)
        if use_skyfall and draw_layer is not None:
            draw_layer(canvas, far_layer, far_scroll, panel_w, panel_h)
            draw_layer(
                canvas, near_layer, near_scroll, panel_w, panel_h,
                tick=tick, twinkle=True,
            )
            draw_layer(canvas, giant_layer, giant_scroll, panel_w, panel_h)
            draw_layer(canvas, planet_layer, planet_scroll, panel_w, panel_h)
        for letter in letters:
            letter.draw(canvas, panel_w, panel_h)
        if ball_active:
            _draw_intro_silver_ball(
                canvas, ball_x, ball_y, PB_INTRO_BALL_R, panel_w, panel_h,
            )
        canvas = LED.TheMatrix.SwapOnVSync(canvas)
        LED.Canvas = canvas

    try:
        while True:
            if _stop(StopEvent):
                break
            now = time.time()
            elapsed = now - start
            if elapsed >= PB_INTRO_MAX_SECONDS:
                break

            dt = max(0.001, now - last)
            last = now
            step = min(3.0, dt * 30.0)
            tick += 1

            if use_skyfall:
                far_scroll = (far_scroll + far_speed * step) % (max(1, len(far_layer)) * 1000)
                near_scroll = (near_scroll + near_speed * step) % (max(1, len(near_layer)) * 1000)
                giant_scroll = (giant_scroll + giant_speed * step) % max(1, giant_height)
                planet_scroll = (planet_scroll + planet_speed * step) % max(1, planet_height)

            if phase == "fade_in":
                all_in = True
                for L in letters:
                    if not L.update_fade(elapsed):
                        all_in = False
                if all_in:
                    phase = "hold"
                    hold_start = now
                    print("[pinball] Title intro — letters solid")

            elif phase == "hold":
                for L in letters:
                    L.alpha = 1.0
                if (now - hold_start) >= PB_HOLD_SECONDS:
                    phase = "ball"
                    ball_active = True
                    ball_x, ball_y, ball_vx, ball_vy = _spawn_intro_ball(
                        letters, panel_w, panel_h,
                    )
                    print(
                        f"[pinball] Title intro — silver ball from "
                        f"({ball_x:.0f},{ball_y:.0f}) vel=({ball_vx:.2f},{ball_vy:.2f})"
                    )

            elif phase == "ball":
                ball_vy += PB_INTRO_BALL_GRAVITY * step
                ball_x += ball_vx * step
                ball_y += ball_vy * step

                # Ball bounces on panel edges so it can clip more letters
                br = PB_INTRO_BALL_R
                if ball_x < br and ball_vx < 0:
                    ball_x = br
                    ball_vx = abs(ball_vx) * PB_INTRO_BALL_BOUNCE
                elif ball_x > panel_w - br and ball_vx > 0:
                    ball_x = panel_w - br
                    ball_vx = -abs(ball_vx) * PB_INTRO_BALL_BOUNCE
                if ball_y < br and ball_vy < 0:
                    ball_y = br
                    ball_vy = abs(ball_vy) * PB_INTRO_BALL_BOUNCE
                elif ball_y > panel_h - br and ball_vy > 0:
                    ball_y = panel_h - br
                    ball_vy = -abs(ball_vy) * PB_INTRO_BALL_BOUNCE

                for L in letters:
                    if L.hits_ball(ball_x, ball_y, PB_INTRO_BALL_R + 0.8):
                        L.knock(ball_x, ball_y, ball_vx, ball_vy)
                        # Ball reacts slightly to impact
                        ball_vx *= 0.92
                        ball_vy *= 0.92
                        if first_hit_time is None:
                            first_hit_time = now
                            print(f"[pinball] Title intro — hit '{L.char}'")
                    L.update_flight(step, panel_w, panel_h)

                margin = PB_INTRO_BALL_R * 4
                ball_gone = (
                    ball_x < -margin or ball_x > panel_w + margin
                    or ball_y < -margin or ball_y > panel_h + margin
                )
                all_knocked = all(L.knocked for L in letters)
                letters_settled = all(
                    (not L.knocked)
                    or L.alpha < 0.1
                    or (L.bounces >= 2 and math.hypot(L.vx, L.vy) < 0.3)
                    or not L.on_screen(panel_w, panel_h)
                    for L in letters
                )
                scatter_done = (
                    first_hit_time is not None
                    and (now - first_hit_time) >= PB_SCATTER_SECONDS
                )
                if first_hit_time is None and ball_gone:
                    # Missed — one re-roll then continue
                    ball_x, ball_y, ball_vx, ball_vy = _spawn_intro_ball(
                        letters, panel_w, panel_h,
                    )
                    print("[pinball] Title intro — re-aim ball")
                elif scatter_done or (all_knocked and letters_settled):
                    break

            try:
                _paint()
            except Exception as paint_exc:
                print(f"[pinball] intro frame error: {paint_exc}")
                break

            if clock:
                clock.tick(PB_INTRO_FPS)
            else:
                time.sleep(1.0 / PB_INTRO_FPS)

    except KeyboardInterrupt:
        pass

    try:
        LED.ClearBuffers()
        LED.TheMatrix.Clear()
    except Exception:
        pass
    print("[pinball] Title intro complete")


def LaunchPinball(Duration=10000, ShowIntro=True, StopEvent=None):
    if ShowIntro:
        try:
            LED.LoadConfigData()
        except Exception:
            pass
        try:
            PlayPinballTitleIntro(StopEvent=StopEvent)
        except Exception as exc:
            import traceback
            print(f"[pinball] intro failed: {exc}")
            traceback.print_exc()
        try:
            LED.ClearBigLED()
            LED.ClearBuffers()
        except Exception:
            pass

    PlayPinball(Duration=Duration, StopEvent=StopEvent)


if __name__ == "__main__":
    try:
        LaunchPinball(Duration=100000, ShowIntro=True, StopEvent=None)
    except KeyboardInterrupt:
        print("Exiting pinball.")
