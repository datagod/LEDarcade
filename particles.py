# =====================================================================================
# PARTICLES - LED Sand Nozzle Simulation
#
# A classic particle physics / cellular automata sand simulator for RGB LED matrices.
# Sand falls from a nozzle at the top, obeys gravity, stacks into piles using
# realistic diagonal avalanching rules, and drains through a "plug" at the bottom
# the entire floor opens on a timer so the pile periodically drains away.
#
# Modes:
#   clock (default) — nozzle loops the full screen border, no floor, sand sprays a
#     digital clock into existence; clock pixels are visual-only (sand flows through).
#   sandbox — partial border path, purple platforms, floor drops on a 120s timer.
#
# Key behaviors:
#   - Nozzle pressure (speed, flow rate, spread) breathes smoothly over time.
#   - Shot grains arc through the air (velocity + gravity), bounce a few times,
#     then settle into the pile as grid cells.
#   - Settled sand falls down, or diagonally when blocked (stable diagonal order).
#   - Resting grains can be nudged or knocked airborne by incoming flying grains.
#
# Animation speed / framebuffers:
#   After examining gravitysim.py, FallingSand.py, and Blasteroids.py:
#   - Blasteroids (heavy Canvas + SwapOnVSync user) uses pygame.time.Clock().tick(60)
#     AFTER SwapOnVSync for explicit, smooth framebuffer pacing.
#   - FallingSand.py and gravitysim.py build frames (often with trail fade on ScreenArray)
#     then do LED.Canvas = TheMatrix.SwapOnVSync(...) and let Python speed + VSync
#     determine rate (frequently very fast for light sims).
#   - For this sand sim we want deliberate, visible falling and stacking, not frantic motion.
#   - Best observed speed for this style on 64x32 (and similar) is ~25-35 FPS.
#     We use pygame Clock.tick(TARGET_FPS) after SwapOnVSync when pygame is available.
#     Falls back to time.sleep(1/TARGET_FPS) otherwise.
#
# Rendering:
#   - Double-buffered via setpixelCanvas + SwapOnVSync (consistent with Blasteroids).
#   - Full clear of backbuffer each frame, then redraw current sand state + decorations.
#
# Author: Built for LEDarcade (following patterns from gravitysim, FallingSand, Blasteroids,
#         Outbreak, Defender, etc.)
# =====================================================================================

import LEDarcade as LED
LED.Initialize()

import math
import time
import random
from datetime import datetime, timedelta

# Try to get precise framebuffer frame pacing like Blasteroids
try:
    import pygame
    HAS_PYGAME = True
except Exception:
    HAS_PYGAME = False


# ---------------- Configuration ----------------

WIDTH = LED.HatWidth
HEIGHT = LED.HatHeight

# Simulation modes
MODE_CLOCK = "clock"
MODE_SANDBOX = "sandbox"
DEFAULT_MODE = MODE_CLOCK

# Nozzle path (clock = full border; sandbox = left/top/right partial loop)
NOZZLE_WIDTH = 3
NOZZLE_MARGIN = 1           # inset from the outer edge along the border path
PATH_SPEED = 0.0062         # base segment progress per frame (slightly faster)
SIDE_DEPTH = max(5, HEIGHT // 3)  # sandbox: how far down side walls the nozzle travels
PATH_LENGTH_SANDBOX = 3.0
PATH_LENGTH_CLOCK = 4.0     # left, top, right, bottom
# Flying sand (arcs and bounces before joining the grid)
FLY_GRAVITY = 0.11
SHOOT_SPEED_MIN = 0.55      # speed at lowest nozzle pressure
SHOOT_SPEED_MAX = 1.85      # speed at highest nozzle pressure
SPREAD_ANGLE = 0.32         # radians of random aim jitter at mid pressure
SPREAD_TIGHT_SCALE = 0.55   # spread multiplier at full pressure (tighter stream)
SPREAD_WIDE_SCALE = 1.25    # spread multiplier at low pressure (wider fan)

# Nozzle pressure breathes smoothly over time (speed + flow rate + spread)
PRESSURE_PHASE_SPEED = 0.011
SPAWN_RATE_MIN = 0.018      # grains/frame equivalent at lowest pressure
SPAWN_RATE_MAX = 0.95       # grains/frame equivalent at highest pressure
SIDE_PRESSURE_BOOST = 0.38  # extra pressure while nozzle is on left/right walls
SIDE_SPAWN_MULT = 1.55      # flow multiplier on side walls
SIDE_SPEED_MULT = 1.30      # launch speed multiplier on side walls
SIDE_SHOOT_UP = 0.52        # radians — side shots aimed upward for arcing trajectories
BOUNCE_RESTITUTION = 0.38   # energy kept on wall/floor/pile bounce
BOUNCE_FRICTION = 0.82      # horizontal damping on bounce
MAX_BOUNCES = 4
SETTLE_SPEED = 0.28         # speed below which a grain tries to lock into the grid
JOSTLE_SPEED_MIN = 0.32     # incoming speed needed to nudge a resting grain
JOSTLE_LAUNCH_MIN = 0.58    # incoming speed needed to knock a grain back into flight
JOSTLE_IMPULSE_SCALE = 0.48 # how much impact velocity transfers to a resting grain

# Sand colors cycle through a palette as the nozzle moves and shoots
SAND_PALETTE = [
    (230, 195, 90),   # classic sand
    (255, 200, 70),   # bright gold
    (255, 150, 50),   # amber
    (220, 100, 60),   # terracotta
    (255, 120, 90),   # coral
    (200, 220, 100),  # pale lime-gold
    (255, 230, 140),  # cream
    (180, 140, 255),  # soft lavender (accent)
    (100, 200, 255),  # sky blue (accent)
]
COLOR_CYCLE_SPEED = 0.005   # palette drift per frame (slow, gradual shift)
COLOR_SPAWN_BUMP = 0.015    # extra drift each grain spawned
COLOR_JITTER = 8            # per-grain RGB wobble

# Floor drop (scheduled timer — entire bottom row opens briefly)
FLOOR_DROP_INTERVAL_SECONDS = 120
FLOORLESS_SECONDS = 5
ENABLE_DRAIN = False        # legacy plug drain disabled
DRAIN_X = WIDTH // 2
DRAIN_WIDTH = 7

TARGET_FPS = 30             # Best speed for nice visible stacking + falling (see notes above)
FLOOR_DROP_INTERVAL_FRAMES = int(FLOOR_DROP_INTERVAL_SECONDS * TARGET_FPS)
FLOORLESS_FRAMES = int(FLOORLESS_SECONDS * TARGET_FPS)

# Purple platforms (random horizontal ledges at startup)
PLATFORM_COUNT_MIN = 2
PLATFORM_COUNT_MAX = 8
PLATFORM_WIDTH_MIN = 3
PLATFORM_WIDTH_MAX = 8
PLATFORM_TOP_MARGIN = 5     # platforms must stay at least this many pixels below the top

# Sand-sprayed digital clock (LEDarcade CreateClockSprite digit face)
CLOCK_ZOOM = 3 if WIDTH >= 64 else 2
CLOCK_RGB = LED.MedGreen
CLOCK_GHOST_DIVISOR = 7     # dim unfilled digit targets (lower = brighter ghost)
CLOCK_PREDESTRUCT_SECONDS = 15  # before minute rollover, changing digits become erasable
CLOCK_SPRAY_BOOST_SECONDS = 10  # high-intensity spray window after the new time appears
CLOCK_SPRAY_BOOST_PEAK = 0.42   # extra effective pressure at full boost
CLOCK_SPRAY_RAMP_UP_SECONDS = 0.8
CLOCK_SPRAY_RAMP_DOWN_SECONDS = 2.5
CLOCK_SEEK_SPEED_MULT = 1.65    # modest speed-up while homing on changed digits
CLOCK_SEEK_EASE = 0.18          # slow the final approach so the nozzle glides in
CLOCK_SEEK_ARRIVE_DIST = 0.06   # path-distance window treated as "on target"
CLOCK_SEEK_ORBIT_SPAN = 0.11    # gentle sweep along the top border over the digit
CLOCK_SEEK_ORBIT_SPEED = 0.038
CLOCK_SEEK_CYCLE_SECONDS = 3.0  # rotate between multiple changed digits during spray boost

# Visuals
NOZZLE_COLOR = (70, 70, 70)
HOLE_COLOR = (15, 8, 0)
WALL_COLOR = (40, 30, 20)

# Timers / duration handling (Duration is in MINUTES like other LEDarcade modules)
ScrollSleep = 0.02
TerminalTypeSpeed = 0.015
TerminalScrollSpeed = 0.015
CursorRGB = (0, 255, 0)
CursorDarkRGB = (0, 50, 0)


# ---------------- Simulation State ----------------

# grid[y][x] = None (empty) or (r, g, b)
grid = [[None for _ in range(WIDTH)] for _ in range(HEIGHT)]
frame_counter = 0
nozzle_x = 1
nozzle_y = SIDE_DEPTH
nozzle_side = "left"
path_distance = 0.0         # continuous 0..3 around left->top->right perimeter
path_direction = 1
path_speed_mult = 1.0
path_pause_until = 0
mood_cooldown = 0
color_phase = 0.0
pressure_phase = 0.0
nozzle_pressure = 0.5       # smoothed 0..1 — low = gentle trickle, high = hard blast
spawn_accumulator = 0.0
floor_removed_until = 0     # frame when the bottom floor returns (0 = floor intact)
next_floor_drop_frame = 0   # frame when the next floor drop begins
flying_particles = []
platforms = []              # list of {x, y, w, color} horizontal ledges
platform_cells = set()      # fast lookup of solid platform pixels
clock_mask = {}             # (x, y) -> rgb target pixels for the current time
clock_layer = {}            # (x, y) -> rgb sand stuck on the clock
clock_hhmm = ""             # last-built clock time (HH:MM)
clock_destructible = set()  # mask pixels about to change — sand erases instead of sticking
clock_spray_boost_start_frame = 0  # frame when post-rollover spray boost began (0 = off)
clock_seek_targets = []         # border path distances above changing digits
clock_seek_index = 0
sim_mode = DEFAULT_MODE


def clock_mode_active():
    return sim_mode == MODE_CLOCK


def sandbox_mode_active():
    return sim_mode == MODE_SANDBOX


def _path_length():
    return PATH_LENGTH_CLOCK if clock_mode_active() else PATH_LENGTH_SANDBOX


def _is_platform(x, y):
    return (x, y) in platform_cells


def _clock_position(sprite, zoom):
    """Center the clock sprite like DisplayDigitalClock."""
    h = (WIDTH // 2) - ((sprite.width * zoom) // 2) - 1
    v = (HEIGHT // 2) - ((sprite.height * zoom) // 2) - zoom
    return h, v


def _mask_from_clock_sprite(sprite, h, v, zoom, rgb):
    """Build a pixel mask from a LEDarcade clock sprite."""
    mask = {}
    for count in range(sprite.width * sprite.height):
        if sprite.grid[count] == 0:
            continue
        sy, sx = divmod(count, sprite.width)
        for zv in range(zoom):
            for zh in range(zoom):
                x = sx * zoom + zh + h
                y = sy * zoom + zv + v
                if 0 <= x < WIDTH and 0 <= y < HEIGHT:
                    mask[(x, y)] = rgb
    return mask


def _clock_mask_for_hhmmss(hhmmss):
    """Build a clock pixel mask for an explicit HH:MM:SS string."""
    sprite = LED.CreateClockSprite(24, hhmmss=hhmmss)
    sprite.TrimLeftEmptyColumns(0)
    h, v = _clock_position(sprite, CLOCK_ZOOM)
    return _mask_from_clock_sprite(sprite, h, v, CLOCK_ZOOM, CLOCK_RGB)


def _left_trim_cols(sprite, leave_columns=1):
    """Count left columns trimmed by TrimLeftEmptyColumns (before mutating sprite)."""
    if sprite.width <= leave_columns:
        return 0

    empty_count = 0
    for col in range(sprite.width):
        column_used = False
        for row in range(sprite.height):
            if sprite.grid[row * sprite.width + col]:
                column_used = True
                break
        if column_used:
            break
        empty_count += 1

    return max(0, empty_count - leave_columns)


def _clock_component_layout(hhmmss):
    """Untrimmed x-offset and sprite for each HH:MM component."""
    hh, mm, _ = hhmmss.split(":")
    h1, h2, m1, m2 = int(hh[0]), int(hh[1]), int(mm[0]), int(mm[1])
    s_h1 = LED.DigitSpriteList[h1]
    s_h2 = LED.DigitSpriteList[h2]
    s_colon = LED.ColonSprite
    s_m1 = LED.DigitSpriteList[m1]
    s_m2 = LED.DigitSpriteList[m2]
    x_h2 = s_h1.width + 1
    x_colon = x_h2 + s_h2.width
    x_m1 = x_colon + s_colon.width
    x_m2 = x_m1 + s_m1.width + 1
    return {
        "h1": (0, s_h1),
        "h2": (x_h2, s_h2),
        "colon": (x_colon, s_colon),
        "m1": (x_m1, s_m1),
        "m2": (x_m2, s_m2),
    }


def _mask_positions_for_component(part_sprite, anchor_h, anchor_v, part_x, trim_cols):
    """Screen positions for one clock component using the shared trimmed layout."""
    positions = set()
    screen_x_base = anchor_h + (part_x - trim_cols) * CLOCK_ZOOM
    for count in range(part_sprite.width * part_sprite.height):
        if part_sprite.grid[count] == 0:
            continue
        sy, sx = divmod(count, part_sprite.width)
        for zv in range(CLOCK_ZOOM):
            for zh in range(CLOCK_ZOOM):
                x = sx * CLOCK_ZOOM + zh + screen_x_base
                y = sy * CLOCK_ZOOM + zv + anchor_v
                if 0 <= x < WIDTH and 0 <= y < HEIGHT:
                    positions.add((x, y))
    return positions


def _clock_component_masks(hhmmss):
    """Map each clock component to its on-screen pixel positions."""
    sprite = LED.CreateClockSprite(24, hhmmss=hhmmss)
    trim_cols = _left_trim_cols(sprite)
    sprite.TrimLeftEmptyColumns(0)
    h, v = _clock_position(sprite, CLOCK_ZOOM)
    return {
        key: _mask_positions_for_component(part_sprite, h, v, part_x, trim_cols)
        for key, (part_x, part_sprite) in _clock_component_layout(hhmmss).items()
    }


def _changing_components_between(prev_hhmm, curr_hhmm):
    """Digit components whose displayed value changes between two HH:MM times."""
    prev_h, prev_m = prev_hhmm.split(":")
    curr_h, curr_m = curr_hhmm.split(":")
    changing = []
    if prev_h[0] != curr_h[0]:
        changing.append("h1")
    if prev_h[1] != curr_h[1]:
        changing.append("h2")
    if prev_m[0] != curr_m[0]:
        changing.append("m1")
    if prev_m[1] != curr_m[1]:
        changing.append("m2")
    return changing


def _cleared_component_positions(prev_hhmm, curr_hhmm):
    """Screen pixels in digit regions that should reset to dim targets on rollover."""
    cleared = set()
    for key in _changing_components_between(prev_hhmm, curr_hhmm):
        cleared |= _clock_component_masks(f"{prev_hhmm}:00")[key]
        cleared |= _clock_component_masks(f"{curr_hhmm}:00")[key]
    return cleared


def _component_center(positions):
    """Bounding-box center for a clock component mask."""
    if not positions:
        return WIDTH / 2.0, HEIGHT / 2.0
    xs = [pos[0] for pos in positions]
    ys = [pos[1] for pos in positions]
    return (min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0


def _top_border_distance_for_digit(cx):
    """Map a digit center to the top-border path distance directly above it."""
    min_x = NOZZLE_MARGIN
    max_x = WIDTH - 1 - NOZZLE_MARGIN
    span_x = max(1, max_x - min_x)
    u = (cx - min_x) / span_x
    u = max(0.03, min(0.97, u))
    return 1.0 + u


def _start_clock_digit_seek(prev_hhmm, curr_hhmm):
    """Queue border-path targets above the digits that just changed."""
    global clock_seek_targets, clock_seek_index

    changing = _changing_components_between(prev_hhmm, curr_hhmm)
    if not changing:
        clock_seek_targets = []
        clock_seek_index = 0
        return

    component_masks = _clock_component_masks(f"{curr_hhmm}:00")
    clock_seek_targets = []
    for key in ("h1", "h2", "m1", "m2"):
        if key not in changing:
            continue
        cx, _cy = _component_center(component_masks[key])
        clock_seek_targets.append(_top_border_distance_for_digit(cx))

    clock_seek_index = 0
    if clock_seek_targets:
        print(f"[particles] Nozzle seeking {len(clock_seek_targets)} changed digit(s)")


def _active_clock_seek_target():
    """Current border-path target while repainting changed digits."""
    if not clock_seek_targets:
        return None

    elapsed = (frame_counter - clock_spray_boost_start_frame) / float(TARGET_FPS)
    if len(clock_seek_targets) > 1 and elapsed > 0:
        cycle = int(elapsed / CLOCK_SEEK_CYCLE_SECONDS) % len(clock_seek_targets)
        return clock_seek_targets[cycle]
    return clock_seek_targets[0]


def _apply_clock_digit_seek():
    """Ease the nozzle toward the changing digit during post-rollover spray."""
    global path_distance, path_direction, path_pause_until

    if not clock_mode_active() or not clock_seek_targets or _clock_spray_boost() <= 0:
        return False

    target = _active_clock_seek_target()
    if target is None:
        return False

    path_pause_until = 0
    diff = target - path_distance

    if abs(diff) <= CLOCK_SEEK_ARRIVE_DIST:
        orbit = math.sin(frame_counter * CLOCK_SEEK_ORBIT_SPEED) * CLOCK_SEEK_ORBIT_SPAN
        path_distance = max(1.02, min(1.98, target + orbit))
        path_direction = 1 if orbit >= 0 else -1
    else:
        seek_cap = PATH_SPEED * path_speed_mult * CLOCK_SEEK_SPEED_MULT
        seek_step = min(seek_cap, max(PATH_SPEED * 0.45, abs(diff) * CLOCK_SEEK_EASE))
        path_direction = 1 if diff > 0 else -1
        path_distance += path_direction * seek_step
        path_distance = max(0.0, min(PATH_LENGTH_CLOCK, path_distance))
        if path_distance <= 0.0:
            path_direction = 1
        elif path_distance >= PATH_LENGTH_CLOCK:
            path_direction = -1
    return True


def _start_clock_spray_boost():
    """Ramp spray intensity up to repaint the freshly updated clock digits."""
    global clock_spray_boost_start_frame

    clock_spray_boost_start_frame = frame_counter
    print(
        f"[particles] Clock spray boost for {CLOCK_SPRAY_BOOST_SECONDS}s "
        f"(peak +{CLOCK_SPRAY_BOOST_PEAK:.2f} pressure)"
    )


def _clock_spray_boost():
    """Extra nozzle pressure after a minute rollover (0 until boost ends)."""
    if not clock_mode_active() or clock_spray_boost_start_frame <= 0:
        return 0.0

    elapsed = (frame_counter - clock_spray_boost_start_frame) / float(TARGET_FPS)
    total = CLOCK_SPRAY_BOOST_SECONDS + CLOCK_SPRAY_RAMP_DOWN_SECONDS
    if elapsed >= total:
        return 0.0

    if elapsed < CLOCK_SPRAY_RAMP_UP_SECONDS:
        t = elapsed / CLOCK_SPRAY_RAMP_UP_SECONDS
        return CLOCK_SPRAY_BOOST_PEAK * t

    if elapsed < CLOCK_SPRAY_BOOST_SECONDS:
        return CLOCK_SPRAY_BOOST_PEAK

    down_t = elapsed - CLOCK_SPRAY_BOOST_SECONDS
    return CLOCK_SPRAY_BOOST_PEAK * max(0.0, 1.0 - down_t / CLOCK_SPRAY_RAMP_DOWN_SECONDS)


def update_clock_mask():
    """Refresh the clock digit mask when the minute changes."""
    global clock_mask, clock_layer, clock_hhmm, clock_destructible

    if not clock_mode_active():
        clock_mask = {}
        clock_layer = {}
        clock_hhmm = ""
        clock_destructible = set()
        return

    now_hhmm = datetime.now().strftime("%H:%M")
    if now_hhmm == clock_hhmm and clock_mask:
        return

    previous_hhmm = clock_hhmm
    now_hhmmss = datetime.now().strftime("%H:%M:00")
    new_mask = _clock_mask_for_hhmmss(now_hhmmss)
    clock_hhmm = now_hhmm

    if previous_hhmm:
        cleared = _cleared_component_positions(previous_hhmm, now_hhmm)
        if cleared:
            clock_layer = {
                pos: color for pos, color in clock_layer.items() if pos not in cleared
            }

    clock_mask = new_mask
    clock_layer = {pos: color for pos, color in clock_layer.items() if pos in clock_mask}
    clock_destructible = set()
    print(f"[particles] Clock mask updated for {clock_hhmm} ({len(clock_mask)} pixels)")
    if previous_hhmm:
        _start_clock_spray_boost()
        _start_clock_digit_seek(previous_hhmm, now_hhmm)


def update_clock_destructible():
    """Mark current-shape pixels in changing digits so sand can erase them pre-rollover."""
    global clock_destructible

    if not clock_mode_active() or not clock_mask:
        clock_destructible = set()
        return

    now = datetime.now()
    if now.second < 60 - CLOCK_PREDESTRUCT_SECONDS:
        clock_destructible = set()
        return

    next_minute = now + timedelta(minutes=1)
    component_masks = _clock_component_masks(now.strftime("%H:%M:00"))
    clock_destructible = set()
    for key in _changing_components_between(
        now.strftime("%H:%M"),
        next_minute.strftime("%H:%M"),
    ):
        clock_destructible |= component_masks[key]
    clock_destructible &= set(clock_mask.keys())


def _paint_clock_if_masked(px, py):
    """Paint an unfilled clock pixel when sand passes through (non-blocking)."""
    global clock_layer

    if not clock_mode_active():
        return

    cx = int(round(px))
    cy = int(round(py))
    if (cx, cy) not in clock_mask:
        return

    if (cx, cy) in clock_destructible:
        if (cx, cy) in clock_layer:
            del clock_layer[(cx, cy)]
        return

    if (cx, cy) in clock_layer:
        return

    clock_layer[(cx, cy)] = clock_mask[(cx, cy)]


def generate_platforms():
    """Create random horizontal purple platforms at the start of a run."""
    global platforms, platform_cells

    platforms = []
    platform_cells = set()
    used = set()
    target = random.randint(PLATFORM_COUNT_MIN, PLATFORM_COUNT_MAX)
    attempts = 0

    while len(platforms) < target and attempts < 120:
        attempts += 1
        width = random.randint(PLATFORM_WIDTH_MIN, PLATFORM_WIDTH_MAX)
        x = random.randint(1, WIDTH - 1 - width)
        y_max = HEIGHT - 3
        if y_max < PLATFORM_TOP_MARGIN:
            break
        y = random.randint(PLATFORM_TOP_MARGIN, y_max)
        cells = {(x + i, y) for i in range(width)}
        if cells & used:
            continue

        used |= cells
        color = (
            random.randint(110, 175),
            random.randint(25, 70),
            random.randint(170, 255),
        )
        platforms.append({"x": x, "y": y, "w": width, "color": color})
        platform_cells |= cells

    print(f"[particles] Generated {len(platforms)} purple platforms")


def clear_canvas():
    """Clear the backbuffer (Canvas) and our tracking ScreenArray. Redraw fresh each frame."""
    global grid  # not needed here but for symmetry
    for y in range(HEIGHT):
        for x in range(WIDTH):
            LED.Canvas.SetPixel(x, y, 0, 0, 0)
            LED.ScreenArray[y][x] = (0, 0, 0)


def _clamp_rgb(r, g, b):
    return (
        max(0, min(255, int(r))),
        max(0, min(255, int(g))),
        max(0, min(255, int(b))),
    )


def _palette_color(t):
    """Interpolate between palette entries at fractional index t."""
    n = len(SAND_PALETTE)
    if n == 0:
        return (230, 195, 90)
    if n == 1:
        return SAND_PALETTE[0]

    t = t % n
    i = int(t)
    f = t - i
    c0 = SAND_PALETTE[i]
    c1 = SAND_PALETTE[(i + 1) % n]
    return (
        c0[0] + (c1[0] - c0[0]) * f,
        c0[1] + (c1[1] - c0[1]) * f,
        c0[2] + (c1[2] - c0[2]) * f,
    )


def get_sand_color():
    """Return a sand color that slowly shifts along the palette."""
    global color_phase

    color_phase += COLOR_SPAWN_BUMP
    base = _palette_color(color_phase)
    path_tint = _palette_color(color_phase + path_distance * 0.18)
    r = (base[0] * 0.82 + path_tint[0] * 0.18) + random.randint(-COLOR_JITTER, COLOR_JITTER)
    g = (base[1] * 0.82 + path_tint[1] * 0.18) + random.randint(-COLOR_JITTER, COLOR_JITTER)
    b = (base[2] * 0.82 + path_tint[2] * 0.18) + random.randint(-COLOR_JITTER, COLOR_JITTER)
    return _clamp_rgb(r, g, b)


def _position_sandbox(distance):
    """Partial loop: left wall, top, right wall."""
    min_x = NOZZLE_MARGIN
    max_x = WIDTH - 1 - NOZZLE_MARGIN
    t = max(0.0, min(PATH_LENGTH_SANDBOX, distance))

    if t < 1.0:
        return 1, int((1.0 - t) * SIDE_DEPTH), "left"
    if t < 2.0:
        u = t - 1.0
        return min_x + int(u * (max_x - min_x)), 0, "top"
    u = t - 2.0
    return WIDTH - 2, int(u * SIDE_DEPTH), "right"


def _position_clock_border(distance):
    """Full screen border: left up, top, right down, bottom."""
    min_x = NOZZLE_MARGIN
    max_x = WIDTH - 1 - NOZZLE_MARGIN
    max_y = HEIGHT - 1 - NOZZLE_MARGIN
    t = max(0.0, min(PATH_LENGTH_CLOCK, distance))

    if t < 1.0:
        return min_x, int((1.0 - t) * max_y), "left"
    if t < 2.0:
        u = t - 1.0
        return min_x + int(u * (max_x - min_x)), NOZZLE_MARGIN, "top"
    if t < 3.0:
        u = t - 2.0
        return max_x, int(u * max_y), "right"
    u = t - 3.0
    return max_x - int(u * (max_x - min_x)), max_y, "bottom"


def _position_from_distance(distance):
    if clock_mode_active():
        return _position_clock_border(distance)
    return _position_sandbox(distance)


def floor_is_removed():
    """True when sand can fall through the bottom row."""
    if clock_mode_active():
        return True
    return frame_counter < floor_removed_until


def _tick_nozzle_mood():
    """Occasionally pause, slow down, speed up, or reverse along the same path."""
    global path_speed_mult, path_pause_until, mood_cooldown, path_direction

    if mood_cooldown > 0:
        mood_cooldown -= 1
        if path_speed_mult < 1.0:
            path_speed_mult = min(1.0, path_speed_mult + 0.025)
        elif path_speed_mult > 1.0:
            path_speed_mult = max(1.0, path_speed_mult - 0.03)
        return

    roll = random.random()
    if roll < 0.007:
        path_pause_until = frame_counter + random.randint(12, 40)
        mood_cooldown = random.randint(50, 110)
    elif roll < 0.022:
        path_speed_mult = random.uniform(0.18, 0.5)
        mood_cooldown = random.randint(35, 85)
    elif roll < 0.034:
        path_speed_mult = random.uniform(1.35, 2.1)
        mood_cooldown = random.randint(20, 45)
    elif roll < 0.048:
        path_direction *= -1
        mood_cooldown = random.randint(70, 140)


def update_nozzle_pressure():
    """Drift nozzle pressure smoothly using layered sine waves."""
    global pressure_phase, nozzle_pressure

    pressure_phase += PRESSURE_PHASE_SPEED
    wave = (
        0.62 * math.sin(pressure_phase)
        + 0.28 * math.sin(pressure_phase * 0.43 + 1.1)
        + 0.10 * math.sin(pressure_phase * 0.17 + 2.4)
    )
    nozzle_pressure = max(0.0, min(1.0, 0.5 + 0.5 * wave))


def _border_side_boost():
    """Sides that get extra pressure for arcing streams into the playfield."""
    if clock_mode_active():
        return nozzle_side in ("left", "right", "bottom")
    return nozzle_side in ("left", "right")


def _effective_pressure():
    """Base pressure with a boost on border sides for stronger arcing streams."""
    pressure = nozzle_pressure + _clock_spray_boost()
    if _border_side_boost():
        pressure = min(1.0, pressure + SIDE_PRESSURE_BOOST)
    return min(1.0, pressure)


def _pressure_shoot_speed():
    """Map current pressure to a launch speed with slight per-grain variation."""
    pressure = _effective_pressure()
    center = SHOOT_SPEED_MIN + pressure * (SHOOT_SPEED_MAX - SHOOT_SPEED_MIN)
    if _border_side_boost():
        center *= SIDE_SPEED_MULT
    spread = 0.06 + pressure * 0.10
    return random.uniform(center - spread, center + spread)


def _pressure_spread_scale():
    """Higher pressure tightens the stream; lower pressure widens it."""
    pressure = _effective_pressure()
    return SPREAD_WIDE_SCALE + pressure * (SPREAD_TIGHT_SCALE - SPREAD_WIDE_SCALE)


def _spawn_from_pressure():
    """Emit grains according to the smoothly varying nozzle flow rate."""
    global spawn_accumulator

    pressure = _effective_pressure()
    rate = SPAWN_RATE_MIN + pressure * (SPAWN_RATE_MAX - SPAWN_RATE_MIN)
    if _border_side_boost():
        rate *= SIDE_SPAWN_MULT
    spawn_accumulator += rate
    while spawn_accumulator >= 1.0:
        spawn_from_nozzle()
        spawn_accumulator -= 1.0


def update_nozzle_position():
    """Travel continuously around the border path, ping-pong forever."""
    global nozzle_x, nozzle_y, nozzle_side, path_distance, path_direction, color_phase

    color_phase += COLOR_CYCLE_SPEED
    update_nozzle_pressure()
    _tick_nozzle_mood()

    nozzle_x, nozzle_y, nozzle_side = _position_from_distance(path_distance)

    if _apply_clock_digit_seek():
        nozzle_x, nozzle_y, nozzle_side = _position_from_distance(path_distance)
        return

    if frame_counter < path_pause_until:
        return

    step = PATH_SPEED * path_speed_mult * random.uniform(0.9, 1.1)
    path_distance += step * path_direction
    path_len = _path_length()

    if path_distance >= path_len:
        path_distance = path_len
        path_direction = -1
    elif path_distance <= 0.0:
        path_distance = 0.0
        path_direction = 1

    nozzle_x, nozzle_y, nozzle_side = _position_from_distance(path_distance)


def _shoot_angle():
    """Aim direction based on where the nozzle sits on the border."""
    spread = SPREAD_ANGLE * _pressure_spread_scale()
    if nozzle_side == "top":
        center_bias = (nozzle_x - (WIDTH - 1) / 2.0) * 0.018
        return math.pi / 2 + center_bias + random.uniform(-spread, spread)
    if nozzle_side == "bottom":
        center_bias = (nozzle_x - (WIDTH - 1) / 2.0) * 0.018
        return -math.pi / 2 + center_bias + random.uniform(-spread, spread)
    if nozzle_side == "left":
        base = -SIDE_SHOOT_UP
        return base + random.uniform(-spread * 0.45, spread * 0.30)
    base = -math.pi + SIDE_SHOOT_UP
    return base + random.uniform(-spread * 0.30, spread * 0.45)


def spawn_from_nozzle():
    """Shoot a single sand grain from the nozzle with initial velocity."""
    global flying_particles

    if nozzle_x < 1 or nozzle_x >= WIDTH - 1:
        return
    if nozzle_y < 0 or nozzle_y >= HEIGHT:
        return

    angle = _shoot_angle()
    speed = _pressure_shoot_speed()
    flying_particles.append({
        "x": float(nozzle_x),
        "y": float(nozzle_y),
        "vx": speed * math.cos(angle),
        "vy": speed * math.sin(angle),
        "color": get_sand_color(),
        "bounces": 0,
    })


def _grid_occupied(x, y):
    if x < 0 or x >= WIDTH or y < 0 or y >= HEIGHT:
        return True
    return grid[y][x] is not None


def _sand_cell_free(x, y):
    """True if settled sand can occupy this cell."""
    if x < 0 or x >= WIDTH or y < 0 or y >= HEIGHT:
        return False
    if _is_platform(x, y):
        return False
    return grid[y][x] is None


def _try_settle_grain(px, py, color):
    """Place a grain on the grid at the nearest open cell under (px, py)."""
    _paint_clock_if_masked(px, py)

    cx = max(1, min(WIDTH - 2, int(round(px))))
    cy = max(0, min(HEIGHT - 1, int(round(py))))

    for sy in range(cy, -1, -1):
        if _sand_cell_free(cx, sy):
            grid[sy][cx] = color
            return True

    for sx in (cx - 1, cx + 1):
        if 1 <= sx < WIDTH - 1 and _sand_cell_free(sx, cy):
            grid[cy][sx] = color
            return True

    return False


def _bounce_off_surface(vx, vy, normal_x, normal_y):
    """Reflect velocity across a surface normal and apply bounce damping."""
    dot = vx * normal_x + vy * normal_y
    rx = vx - 2 * dot * normal_x
    ry = vy - 2 * dot * normal_y
    return rx * BOUNCE_RESTITUTION, ry * BOUNCE_RESTITUTION


def _resting_sand_at(x, y):
    return 1 <= x < WIDTH - 1 and 0 <= y < HEIGHT and grid[y][x] is not None and not _is_platform(x, y)


def _jostle_settled_grain(hit_x, hit_y, impulse_vx, impulse_vy):
    """Nudge or relaunch a resting grain struck by an incoming flying grain."""
    global grid, flying_particles

    if not _resting_sand_at(hit_x, hit_y):
        return False

    color = grid[hit_y][hit_x]
    impulse_speed = math.sqrt(impulse_vx * impulse_vx + impulse_vy * impulse_vy)
    if impulse_speed < JOSTLE_SPEED_MIN:
        return False

    grid[hit_y][hit_x] = None

    if impulse_speed >= JOSTLE_LAUNCH_MIN:
        flying_particles.append({
            "x": float(hit_x),
            "y": float(hit_y),
            "vx": impulse_vx * JOSTLE_IMPULSE_SCALE + random.uniform(-0.12, 0.12),
            "vy": impulse_vy * JOSTLE_IMPULSE_SCALE + random.uniform(-0.18, 0.08),
            "color": color,
            "bounces": 0,
        })
        return True

    if abs(impulse_vx) >= abs(impulse_vy):
        nudge_dirs = [
            (1 if impulse_vx >= 0 else -1, 0),
            (0, -1),
            (-1 if impulse_vx >= 0 else 1, 0),
            (0, 1),
        ]
    else:
        nudge_dirs = [
            (0, -1),
            (1 if impulse_vx >= 0 else -1, 0),
            (-1 if impulse_vx >= 0 else 1, 0),
            (0, 1),
        ]

    for dx, dy in nudge_dirs:
        nx, ny = hit_x + dx, hit_y + dy
        if _sand_cell_free(nx, ny):
            grid[ny][nx] = color
            return True

    grid[hit_y][hit_x] = color
    return False


def _jostle_from_impact(hit_x, hit_y, impulse_vx, impulse_vy):
    """Jostle a struck grain and lightly disturb its immediate neighbors."""
    struck = _jostle_settled_grain(hit_x, hit_y, impulse_vx, impulse_vy)
    if struck:
        neighbor_vx = impulse_vx * 0.35
        neighbor_vy = impulse_vy * 0.35
        for dx, dy in ((-1, 0), (1, 0), (0, -1)):
            _jostle_settled_grain(hit_x + dx, hit_y + dy, neighbor_vx, neighbor_vy)
    return struck


def update_flying_particles():
    """Integrate airborne grains: gravity, wall/floor/pile collisions, settle into grid."""
    global flying_particles

    remaining = []

    for grain in flying_particles:
        vx = grain["vx"]
        vy = grain["vy"]
        vy += FLY_GRAVITY

        nx = grain["x"] + vx
        ny = grain["y"] + vy
        bounces = grain["bounces"]
        settled = False

        if nx < 1:
            nx = 1.0
            vx, vy = _bounce_off_surface(vx, vy, 1.0, 0.0)
            vx *= BOUNCE_FRICTION
            bounces += 1
        elif nx >= WIDTH - 1:
            nx = float(WIDTH - 2)
            vx, vy = _bounce_off_surface(vx, vy, -1.0, 0.0)
            vx *= BOUNCE_FRICTION
            bounces += 1

        if ny < 0:
            ny = 0.0
            vx, vy = _bounce_off_surface(vx, vy, 0.0, 1.0)
            bounces += 1

        cx = int(round(nx))
        cy = int(round(ny))
        speed = math.sqrt(vx * vx + vy * vy)

        _paint_clock_if_masked(nx, ny)

        if not settled:
            if floor_is_removed() and ny >= HEIGHT:
                continue

            floor_hit = ny >= HEIGHT - 1 and not floor_is_removed()
            pile_hit = (
                1 <= cx < WIDTH - 1
                and cy < HEIGHT - 1
                and (_grid_occupied(cx, cy + 1) or _is_platform(cx, cy + 1))
                and ny >= cy
            )
            embed_hit = 1 <= cx < WIDTH - 1 and (_grid_occupied(cx, cy) or _is_platform(cx, cy))
        else:
            floor_hit = pile_hit = embed_hit = False

        if not settled and (floor_hit or pile_hit or embed_hit):
            if cy >= HEIGHT:
                cy = HEIGHT - 1
                ny = float(HEIGHT - 1)

            if pile_hit and _resting_sand_at(cx, cy + 1):
                _jostle_from_impact(cx, cy + 1, vx, vy)
            elif embed_hit and _resting_sand_at(cx, cy):
                _jostle_from_impact(cx, cy, vx, vy)

            if speed > SETTLE_SPEED and bounces < MAX_BOUNCES:
                if floor_hit:
                    vx *= BOUNCE_FRICTION
                    vy, vx = _bounce_off_surface(vx, vy, 0.0, -1.0)
                    vy *= BOUNCE_FRICTION
                    ny = float(HEIGHT - 2) if HEIGHT > 2 else 0.0
                elif pile_hit:
                    vx *= BOUNCE_FRICTION
                    vx, vy = _bounce_off_surface(vx, vy, 0.0, -1.0)
                    vy *= BOUNCE_FRICTION
                    ny = float(max(0, cy - 1))
                else:
                    vx, vy = _bounce_off_surface(vx, vy, 0.0, -1.0)
                    ny = float(max(0, cy - 1))
                bounces += 1
            elif _try_settle_grain(nx, ny, grain["color"]):
                settled = True
            else:
                vx *= 0.5
                vy = -abs(vy) * BOUNCE_RESTITUTION * 0.5
                bounces += 1

        if not settled:
            if speed < SETTLE_SPEED and bounces > 0 and _try_settle_grain(nx, ny, grain["color"]):
                settled = True

        if not settled:
            grain["x"] = nx
            grain["y"] = ny
            grain["vx"] = vx
            grain["vy"] = vy
            grain["bounces"] = bounces
            remaining.append(grain)

    flying_particles = remaining


def _can_fall_to(grid_state, next_grid, x, y):
    """True if (x, y) is in bounds and unoccupied in both the current and next grid."""
    if x < 0 or x >= WIDTH or y < 0 or y >= HEIGHT:
        return False
    if _is_platform(x, y):
        return False
    return grid_state[y][x] is None and next_grid[y][x] is None


def _diagonal_targets(x, y):
    """Return diagonal fall targets in a stable, position-based order (no per-frame randomness)."""
    if (x + y) % 2 == 0:
        order = [(-1, 1), (1, 1)]
    else:
        order = [(1, 1), (-1, 1)]
    return [(x + dx, y + dy) for dx, dy in order]


def update_sand():
    """
    Classic falling-sand rules using a double-buffered grid.

    Read from `grid`, write to `next_grid`, then swap. This prevents two grains
    from claiming the same cell in one frame (the main source of flicker).
    Diagonal preference is deterministic per cell so grains don't zigzag on slopes.
    """
    global grid

    next_grid = [[None for _ in range(WIDTH)] for _ in range(HEIGHT)]

    # Bottom-up: lower grains claim destination cells in next_grid first
    for y in range(HEIGHT - 1, -1, -1):
        for x in range(WIDTH):
            color = grid[y][x]
            if color is None:
                continue

            moved = False

            if y == HEIGHT - 1 and floor_is_removed():
                continue

            _paint_clock_if_masked(x, y)

            if y < HEIGHT - 1:
                # 1. Straight down
                if _can_fall_to(grid, next_grid, x, y + 1):
                    next_grid[y + 1][x] = color
                    moved = True

                # 2. Diagonals (stable order, first open slot wins)
                if not moved:
                    for nx, ny in _diagonal_targets(x, y):
                        if _can_fall_to(grid, next_grid, nx, ny):
                            next_grid[ny][nx] = color
                            moved = True
                            break

            # 3. Stay put (bottom row holds when the floor is intact)
            if not moved and next_grid[y][x] is None:
                next_grid[y][x] = color

    grid = next_grid


def open_floor():
    """Drop the entire bottom row so the pile drains for FLOORLESS_SECONDS."""
    global floor_removed_until, grid

    for x in range(WIDTH):
        grid[HEIGHT - 1][x] = None
    floor_removed_until = frame_counter + FLOORLESS_FRAMES
    print(f"[particles] Floor opened for {FLOORLESS_SECONDS}s")


def restore_floor():
    """Restore the bottom floor and schedule the next drop."""
    global floor_removed_until, next_floor_drop_frame

    floor_removed_until = 0
    next_floor_drop_frame = frame_counter + FLOOR_DROP_INTERVAL_FRAMES
    print(f"[particles] Floor restored — next drop in {FLOOR_DROP_INTERVAL_SECONDS}s")


def _tick_floor_drop_timer():
    """Open the floor on schedule; restore it when the drop window ends."""
    if clock_mode_active():
        return

    if floor_is_removed():
        if frame_counter >= floor_removed_until:
            restore_floor()
        return

    if frame_counter >= next_floor_drop_frame:
        open_floor()


def count_particles():
    count = len(flying_particles) + len(clock_layer)
    for y in range(HEIGHT):
        for x in range(WIDTH):
            if grid[y][x] is not None:
                count += 1
    return count


def nozzle_blocked():
    """Return True if sand has piled up against the nozzle opening."""
    x = nozzle_x
    y = nozzle_y
    if x < 1 or x >= WIDTH - 1 or y < 0 or y >= HEIGHT:
        return False
    if grid[y][x] is not None:
        return True
    if nozzle_side == "top" and y + 1 < HEIGHT and grid[y + 1][x] is not None:
        return True
    if nozzle_side == "right" and x - 1 >= 0 and grid[y][x - 1] is not None:
        return True
    if nozzle_side == "left" and x + 1 < WIDTH and grid[y][x + 1] is not None:
        return True
    if nozzle_side == "bottom" and y - 1 >= 0 and grid[y - 1][x] is not None:
        return True
    return False


def draw_nozzle():
    """Draw the nozzle at its current position (top/bottom bar or side spout)."""
    lip_color = (50, 50, 50)
    spout_color = (90, 70, 40)

    if nozzle_side in ("top", "bottom"):
        y = nozzle_y
        left = max(1, nozzle_x - NOZZLE_WIDTH // 2)
        right = min(WIDTH - 2, nozzle_x + NOZZLE_WIDTH // 2)
        for x in range(left, right + 1):
            LED.setpixelCanvas(x, y, *NOZZLE_COLOR)
        if left > 0:
            LED.setpixelCanvas(left - 1, y, *lip_color)
        if right < WIDTH - 1:
            LED.setpixelCanvas(right + 1, y, *lip_color)
        if nozzle_side == "bottom" and y > 0:
            LED.setpixelCanvas(nozzle_x, y - 1, *spout_color)
    else:
        x = nozzle_x
        top = max(1, nozzle_y - NOZZLE_WIDTH // 2)
        bottom = min(HEIGHT - 2, nozzle_y + NOZZLE_WIDTH // 2)
        for y in range(top, bottom + 1):
            LED.setpixelCanvas(x, y, *NOZZLE_COLOR)
        if top > 0:
            LED.setpixelCanvas(x, top - 1, *lip_color)
        if bottom < HEIGHT - 1:
            LED.setpixelCanvas(x, bottom + 1, *lip_color)
        if nozzle_side == "right" and x > 1:
            LED.setpixelCanvas(x - 1, nozzle_y, *spout_color)
        elif nozzle_side == "left" and x < WIDTH - 2:
            LED.setpixelCanvas(x + 1, nozzle_y, *spout_color)


def draw_open_floor():
    """Show the open bottom row during a floor drop (sandbox mode only)."""
    if clock_mode_active() or not floor_is_removed():
        return

    y = HEIGHT - 1
    for x in range(1, WIDTH - 1):
        LED.setpixelCanvas(x, y, *HOLE_COLOR)
    if y > 0:
        for x in range(1, WIDTH - 1):
            LED.setpixelCanvas(x, y - 1, 10, 5, 0)


def draw_drain():
    """Legacy center plug visual (disabled)."""
    if not ENABLE_DRAIN:
        return
    y = HEIGHT - 1
    left = max(0, DRAIN_X - DRAIN_WIDTH // 2)
    right = min(WIDTH - 1, DRAIN_X + DRAIN_WIDTH // 2)

    for x in range(left, right + 1):
        LED.setpixelCanvas(x, y, *HOLE_COLOR)

    if y > 0:
        for x in range(left, right + 1):
            LED.setpixelCanvas(x, y - 1, 10, 5, 0)


def draw_walls():
    """Optional subtle side walls / container feel (very faint)."""
    # Draw faint vertical lines on the extreme left/right
    for y in range(HEIGHT):
        LED.setpixelCanvas(0, y, *WALL_COLOR)
        LED.setpixelCanvas(WIDTH - 1, y, *WALL_COLOR)


def draw_platforms():
    """Draw the startup purple horizontal platforms."""
    for platform in platforms:
        color = platform["color"]
        y = platform["y"]
        for x in range(platform["x"], platform["x"] + platform["w"]):
            LED.setpixelCanvas(x, y, *color)


def render_sand():
    """Draw all settled sand particles from the grid."""
    for y in range(HEIGHT):
        for x in range(WIDTH):
            color = grid[y][x]
            if color is not None:
                LED.setpixelCanvas(x, y, *color)


def draw_clock_ghost():
    """Dim unfilled clock targets — the new time appears here until sand fills it in."""
    if not clock_mode_active():
        return

    divisor = max(2, CLOCK_GHOST_DIVISOR)
    for (x, y), color in clock_mask.items():
        if (x, y) in clock_layer:
            continue
        LED.setpixelCanvas(
            x, y,
            max(0, color[0] // divisor),
            max(0, color[1] // divisor),
            max(0, color[2] // divisor),
        )


def render_clock_layer():
    """Draw visual-only clock pixels painted by passing sand."""
    if not clock_mode_active():
        return

    for (x, y), color in clock_layer.items():
        LED.setpixelCanvas(x, y, *color)


def render_flying_particles():
    """Draw grains still in flight (arcing / bouncing)."""
    for grain in flying_particles:
        x = int(round(grain["x"]))
        y = int(round(grain["y"]))
        if 0 <= x < WIDTH and 0 <= y < HEIGHT:
            LED.setpixelCanvas(x, y, *grain["color"])


def reset_grid():
    """Clear all sand (used on major state changes if desired)."""
    global grid
    grid = [[None for _ in range(WIDTH)] for _ in range(HEIGHT)]


# ---------------- Main Simulation Loop ----------------

def PlayParticles(Duration=10000, StopEvent=None, Mode=None):
    """
    The core simulation. Duration is in minutes (consistent with other LEDarcade modules).
    Mode: MODE_CLOCK (default) or MODE_SANDBOX.
    """
    global grid, frame_counter, sim_mode
    global nozzle_x, nozzle_y, nozzle_side, flying_particles
    global path_distance, path_direction, path_speed_mult
    global path_pause_until, mood_cooldown, color_phase
    global floor_removed_until, next_floor_drop_frame
    global pressure_phase, nozzle_pressure, spawn_accumulator
    global platforms, platform_cells
    global clock_mask, clock_layer, clock_hhmm, clock_destructible
    global clock_spray_boost_start_frame, clock_seek_targets, clock_seek_index

    sim_mode = Mode or DEFAULT_MODE

    # Fresh state
    LED.ClearBuffers()
    grid = [[None for _ in range(WIDTH)] for _ in range(HEIGHT)]
    platforms = []
    platform_cells = set()
    if sandbox_mode_active():
        generate_platforms()
    frame_counter = 0
    nozzle_x = 1
    nozzle_y = SIDE_DEPTH
    nozzle_side = "left"
    path_distance = 0.0
    path_direction = 1
    path_speed_mult = 1.0
    path_pause_until = 0
    mood_cooldown = 0
    color_phase = 0.0
    pressure_phase = random.uniform(0.0, math.pi * 2.0)
    nozzle_pressure = 0.5
    spawn_accumulator = 0.0
    floor_removed_until = 0
    next_floor_drop_frame = FLOOR_DROP_INTERVAL_FRAMES
    clock_mask = {}
    clock_layer = {}
    clock_hhmm = ""
    clock_destructible = set()
    clock_spray_boost_start_frame = 0
    clock_seek_targets = []
    clock_seek_index = 0
    update_clock_mask()
    flying_particles = []

    clock = pygame.time.Clock() if HAS_PYGAME else None
    start_time = time.time()

    print(f"[particles] Starting {sim_mode} mode on {WIDTH}x{HEIGHT} (TARGET_FPS={TARGET_FPS})")
    print(f"[particles] Using {'pygame.Clock' if HAS_PYGAME else 'time.sleep'} for framebuffer pacing")

    try:
        while True:
            # --- Control / exit conditions ---
            if StopEvent and StopEvent.is_set():
                print("[particles] StopEvent received - shutting down gracefully")
                break

            if Duration and (time.time() - start_time > Duration * 60):
                print("[particles] Duration reached")
                break

            # --- Clear backbuffer (framebuffer style) ---
            clear_canvas()

            update_clock_mask()
            update_clock_destructible()

            # --- Move nozzle and shoot sand ---
            update_nozzle_position()
            _spawn_from_pressure()

            # --- Physics: airborne arcs/bounces, then settled pile rules ---
            update_flying_particles()
            update_sand()

            _tick_floor_drop_timer()

            pcount = count_particles()

            # --- Draw everything ---
            if sandbox_mode_active():
                draw_walls()
                draw_platforms()
                draw_open_floor()
            draw_clock_ghost()
            render_sand()
            render_clock_layer()
            render_flying_particles()
            draw_nozzle()

            # --- Present the frame (double-buffered) ---
            LED.Canvas = LED.TheMatrix.SwapOnVSync(LED.Canvas)

            # --- Frame pacing (the key part the user asked about) ---
            # Using explicit clock.tick after SwapOnVSync gives predictable, smooth
            # animation speed when using the framebuffer model (see Blasteroids.py).
            if clock:
                clock.tick(TARGET_FPS)
            else:
                time.sleep(1.0 / TARGET_FPS)

            frame_counter += 1

            # Occasional diagnostics
            if frame_counter % 300 == 0:
                floorless = floor_is_removed()
                print(f"[particles] frame={frame_counter} particles={pcount} floorless={floorless}")

    except KeyboardInterrupt:
        print("[particles] Interrupted by user")

    # Clean shutdown visuals
    LED.ClearBuffers()
    try:
        LED.TheMatrix.SwapOnVSync(LED.Canvas)
    except Exception:
        pass


# ---------------- Launcher (standard LEDarcade pattern) ----------------

def LaunchParticles(Duration=10000, ShowIntro=False, StopEvent=None, Mode=None):
    """Entry point used by LEDcommander, arcade.py, direct execution, etc."""
    mode = Mode or DEFAULT_MODE
    if ShowIntro:
        LED.LoadConfigData()

        LED.ShowTitleScreen(
            BigText="SAND",
            BigTextRGB=LED.HighYellow,
            BigTextShadowRGB=LED.ShadowYellow,
            LittleText="PARTICLES",
            LittleTextRGB=LED.MedOrange,
            LittleTextShadowRGB=(60, 30, 0),
            ScrollText="Clock mode: sand sprays time into life." if mode == MODE_CLOCK else "Sandbox mode: pile and drain.",
            ScrollTextRGB=LED.MedGreen,
            ScrollSleep=ScrollSleep,
            DisplayTime=1,
            ExitEffect=0,
        )

        LED.ClearBigLED()
        LED.ClearBuffers()

        CursorH = 0
        CursorV = 0
        LED.ScreenArray, CursorH, CursorV = LED.TerminalScroll(
            LED.ScreenArray,
            "OPENING THE NOZZLE",
            CursorH=CursorH,
            CursorV=CursorV,
            MessageRGB=(200, 170, 60),
            CursorRGB=CursorRGB,
            CursorDarkRGB=CursorDarkRGB,
            StartingLineFeed=1,
            TypeSpeed=TerminalTypeSpeed,
            ScrollSpeed=TerminalScrollSpeed,
        )
        LED.BlinkCursor(CursorH=CursorH, CursorV=CursorV, CursorRGB=CursorRGB, CursorDarkRGB=CursorDarkRGB, BlinkSpeed=0.4, BlinkCount=2)

        LED.ScreenArray, CursorH, CursorV = LED.TerminalScroll(
            LED.ScreenArray,
            "GRAVITY ENGAGED",
            CursorH=CursorH,
            CursorV=CursorV,
            MessageRGB=(180, 140, 40),
            CursorRGB=CursorRGB,
            CursorDarkRGB=CursorDarkRGB,
            StartingLineFeed=1,
            TypeSpeed=TerminalTypeSpeed,
            ScrollSpeed=TerminalScrollSpeed,
        )
        LED.BlinkCursor(CursorH=CursorH, CursorV=CursorV, CursorRGB=CursorRGB, CursorDarkRGB=CursorDarkRGB, BlinkSpeed=0.4, BlinkCount=1)

        LED.ScreenArray, CursorH, CursorV = LED.TerminalScroll(
            LED.ScreenArray,
            "CLOCK MODE: BORDER NOZZLE, NO FLOOR." if mode == MODE_CLOCK else "FLOOR DROPS EVERY 120 SECONDS.",
            CursorH=CursorH,
            CursorV=CursorV,
            MessageRGB=(120, 90, 30),
            CursorRGB=CursorRGB,
            CursorDarkRGB=CursorDarkRGB,
            StartingLineFeed=1,
            TypeSpeed=0.008,
            ScrollSpeed=ScrollSleep,
        )
        LED.BlinkCursor(CursorH=CursorH, CursorV=CursorV, CursorRGB=CursorRGB, CursorDarkRGB=CursorDarkRGB, BlinkSpeed=0.4, BlinkCount=2)

    PlayParticles(Duration=Duration, StopEvent=StopEvent, Mode=mode)


# ---------------- Direct execution ----------------

if __name__ == "__main__":
    try:
        LaunchParticles(Duration=100000, ShowIntro=False, StopEvent=None)
    except KeyboardInterrupt:
        print("Exiting particles simulation.")