#!/usr/bin/env python
#------------------------------------------------------------------------------
#  SPACE EXPLORER
#
#  Forked from Defender2's star-field parallax idea: four oversized scrolling
#  layers (far background / background / middleground / foreground) with a tiny
#  ship locked to
#  the center of the screen.  Ground terrain is omitted.  The world drifts in
#  sixteen directions so the star fields move at different speeds on both axes.
#------------------------------------------------------------------------------

import LEDarcade as LED
LED.Initialize()

import copy
import math
import random
import time

# --- Display ---
WIDTH = LED.HatWidth
HEIGHT = LED.HatHeight

# --- World maps (larger than the physical panel in both dimensions) ---
LAYER_WIDTH = 640
LAYER_HEIGHT = max(HEIGHT * 30, 960)

# Movement — staggered layer scroll rates like Defender2 (no per-frame sleep).
SCROLL_STEP = 1.6
FAR_RATE = 14   # far star field; scrolled smoothly every frame
BRATE = 8
MRATE = 6
FRATE = 4

# Ship inertia — Blasteroids-style: rotate at fixed rate, thrust when aligned, coast.
# Rates are tuned for 60fps and scaled by frame delta for smooth motion on the Pi.
PHYSICS_FPS = 60.0
SHIP_TURN_RATE = 0.10
SHIP_THRUST = 0.056
MAX_SHIP_SPEED = 3.75
SHIP_THRUST_ALIGN_RAD = 0.45
HUNT_LEAD_SEC = 0.55
SHIP_HUNT_TURN_RATE = 0.14
SHIP_HUNT_ALIGN_RAD = 0.72
SHIP_HUNT_CLOSE_DIST = 32
SHIP_HUNT_CLOSE_ALIGN_RAD = 1.05
HUNT_INTERCEPT_MIN_TIME = 0.05
HUNT_INTERCEPT_MAX_TIME = 4.0
HUNT_MIN_PURSUIT_SPEED = 0.85
HUNT_TARGET_REACQUIRE_RATIO = 0.55
HUNT_ORBIT_CLOSE_DIST = 70
TRACTOR_BEAM_RGB = (40, 255, 70)
TRACTOR_MAX_WORLD_DIST = 90
TRACTOR_MOMENTUM_DAMP = 0.035
TRACTOR_PULL_RATE = 0.016
TRACTOR_SHIP_MATCH_RATE = 0.07
TRACTOR_SHIP_CLOSE_RATE = 0.85
TRACTOR_COOLDOWN_SEC = 2.0
TRACTOR_MAX_SHIP_SPEED = 5.34375
SHIP_TURBO_THRUST = 0.144
SHIP_TURBO_MAX_SPEED = 6.5625
SHIP_TURBO_TURN_RATE = 0.20
SHIP_TURBO_ALIGN_RAD = 0.75
TURBO_CLOSE_DIST = 30
TURBO_ORBIT_STALL_FRAMES = 10
TURBO_ORBIT_CLOSE_MIN = 0.12
TURBO_DURATION_SEC = 5.0
TURBO_COOLDOWN_SEC = 2.0
ROCK_NEARBY_DIST = 58
CRUISE_MAX_SPEED = 1.05
CRUISE_THRUST = 0.024
CRUISE_TURN_RATE = 0.08
GAS_GIANT_COUNT = 4
GAS_GIANT_ARRIVAL_PAD = 30
BOUNCE_DAMPING = 0.88
SHIP_BOUNCE_DAMPING = 0.44
BOUNCE_COOLDOWN_FRAMES = 12
ENEMY_BOUNCE_COOLDOWN_FRAMES = 10
LOOKAHEAD = 18
THRUST_FLAME_COLORS = (
    (255, 210, 70),
    (255, 140, 30),
    (220, 60, 0),
    (160, 30, 0),
)

# Defender-style enemy ships (world coords on the scrolling map)
ENEMY_SHIP_COUNT = 12
LARGE_ENEMY_SHIP_COUNT = 2
ENEMY_TURN_RATE = 0.14
ENEMY_THRUST = 0.006
ENEMY_MAX_SPEED = 0.32
LARGE_ENEMY_TURN_RATE = 0.10
LARGE_ENEMY_THRUST = 0.004
LARGE_ENEMY_MAX_SPEED = 0.20
ENEMY_BRIGHTNESS = 1.85
ENEMY_RGB_FLOOR = 52
ENEMY_LARGE_BRIGHTNESS = 2.15
ENEMY_LARGE_RGB_FLOOR = 64
ENEMY_SHIP_TYPES = tuple(range(8))  # SmallUFOSprite … SmallUFOSprite7
# LargeUFOSprite5 (8×5) and LargeUFOSprite6 (8×4) in LED.ShipSprites
LARGE_ENEMY_SHIP_TYPES = (22, 23)
ENEMY_DIRECTION_8WAY = {
    1: (0, -1), 2: (1, -1), 3: (1, 0), 4: (1, 1),
    5: (0, 1), 6: (-1, 1), 7: (-1, 0), 8: (-1, -1),
}
CHAIN_PLAYER = object()
CHAIN_LINK_GAP = 2.0
PLAYER_CHAIN_RADIUS = 1.8
CHAIN_LIMP_POS_BLEND = 0.20
CHAIN_LIMP_VEL_MATCH = 0.94
CHAIN_LIMP_CORRECTION = 0.06
CHAIN_WEAVE_AMPLITUDE = 0.38
CHAIN_WEAVE_HZ = 0.55
CHAIN_UFO_GRAPPLE_EXTRA = 20
CHAIN_BAIT_PASS_DIST = 34
CHAIN_BAIT_PASS_SLIP = 0.48
ENEMY_CRYSTAL_BREAK_DIST = 52

# Tiny ship at screen center
SHIP_H = WIDTH // 2
SHIP_V = HEIGHT // 2
SHIP_CORE_RGB = (255, 255, 255)
SHIP_BODY_RGB = (90, 140, 220)
SHIP_NOSE_RGB = (180, 220, 255)

DIRECTION_COUNT = 16

# 16-wind compass (clockwise from north): 1=N, 2=NNE, 3=NE, ... 16=NNW
DIRECTION_DELTAS = {
    1:  (0, -1),
    2:  (1, -2),
    3:  (1, -1),
    4:  (2, -1),
    5:  (1, 0),
    6:  (2, 1),
    7:  (1, 1),
    8:  (1, 2),
    9:  (0, 1),
    10: (-1, 2),
    11: (-1, 1),
    12: (-2, 1),
    13: (-1, 0),
    14: (-2, -1),
    15: (-1, -1),
    16: (-1, -2),
}


def _nose_for_delta(dh, dv):
    """Single-pixel nose direction from a movement vector."""
    if dh == 0:
        return (0, 1 if dv > 0 else -1)
    if dv == 0:
        return (1 if dh > 0 else -1, 0)
    return (1 if dh > 0 else -1, 1 if dv > 0 else -1)


DIRECTION_NOSE = {d: _nose_for_delta(dh, dv) for d, (dh, dv) in DIRECTION_DELTAS.items()}

ScrollSleep = 0.02
TerminalTypeSpeed = 0.015
TerminalScrollSpeed = 0.015
CursorRGB = (0, 255, 0)
CursorDarkRGB = (0, 50, 0)

# Asteroid styling (from Blasteroids lump renderer)
ASTEROID_LIGHTING_CONTRAST = 1.0
ASTEROID_COLOR_OPTIONS = (
    (138, 138, 145),
    (125, 133, 252),
    (252, 55, 252),
)
FOREGROUND_ASTEROID_COLORS = (
    (210, 195, 175),
    (255, 140, 90),
    (200, 210, 255),
)
LAYER_ASTEROIDS = (
    # layer, count, (min_size, max_size), dim_factor
    # Stars live on FarBackground only — no rocks on Background (avoids star-like specks).
    ("middleground", 11, (4, 8), 0.6),
    ("foreground", 18, (2, 9), 0.75),
)

# Foreground rocks = free-floating breakable objects (not parallax layer pixels).
FOREGROUND_ASTEROID_COUNT = 44
FOREGROUND_ASTEROID_SIZE_RANGE = (2, 9)
FOREGROUND_ASTEROID_DIM = 1.15
FOREGROUND_ASTEROID_MIN_SPEED = 0.1
FOREGROUND_ASTEROID_MAX_SPEED = 0.25
# Extra large slow breakable rocks (same ForegroundAsteroid class as the 44 above).
LARGE_SLOW_ASTEROID_COUNT = 10
LARGE_SLOW_ASTEROID_SIZE_RANGE = (8, 12)
LARGE_SLOW_ASTEROID_MIN_SPEED = 0.04
LARGE_SLOW_ASTEROID_MAX_SPEED = 0.08
FOREGROUND_ASTEROID_SPLIT_ANGLE = 0.45
MIN_FOREGROUND_ASTEROID_SIZE = 3
ASTEROID_TIER_BIG_MIN = 7
ASTEROID_TIER_SMALL_MIN = 4
ASTEROID_HITS_HUGE_MIN = 10
ASTEROID_HITS_BIG_MIN = 7
ASTEROID_SMALL_SIZE_RANGE = (4, 6)
ASTEROID_TINY_SIZE_RANGE = (2, 3)
BIG_ROCK_SPLIT_COUNT = 4
SMALL_ROCK_SPLIT_COUNT = 3
SPLIT_FLY_APART_BIG = (0.14, 0.24)
SPLIT_FLY_APART_SMALL = (0.24, 0.42)
SPLIT_PARENT_MOMENTUM = 0.12
SPLIT_PERP_SPREAD_RAD = 0.85
SPLIT_SPAWN_OFFSET = 1.6
TINY_ROCK_SPARK_COUNT = 12
ASTEROID_COLLIDE_SCALE = 0.95
ASTEROID_MERGE_COOLDOWN_SEC = 2.0

SPARK_COUNT = 8
SPARK_TRAIL_LENGTH = 5
SPARK_COLOR = (255, 200, 100)
ENEMY_PARTICLE_GRAVITY = 0.01
ENEMY_PARTICLE_LIFESPAN = 48

CRYSTAL_MAX_PER_BREAK = 3
CRYSTAL_HUNT_DIST = 90
CRYSTAL_MIN_SPEED = 0.05
CRYSTAL_MAX_SPEED = 0.16
CRYSTAL_PIXELS = ((0, 0, (255, 255, 0)),)

# Large mother UFO — metallic sphere; hunted with crystal missiles after 10 loot
MOTHER_RADIUS = 6                 # ~13×13 sprite
MOTHER_HIT_POINTS = 20
MOTHER_CRYSTAL_HUNT_MIN = 10      # banked crystals to start the hunt
MOTHER_FLOAT_SPEED = 0.11
MOTHER_TURN_WANDER = 0.035
MOTHER_RESPAWN_SEC = 45.0
CRYSTAL_MISSILE_SPEED = 2.4
CRYSTAL_MISSILE_TURN = 0.22
CRYSTAL_MISSILE_HIT_R = 7.5
CRYSTAL_MISSILE_FIRE_INTERVAL = 0.32
CRYSTAL_MISSILE_TRAIL = 3
MOTHER_EXPLOSION_SPARKS = 48
MOTHER_EXPLOSION_PARTICLES = 90
MOTHER_LIGHT_BLINK_HZ = 2.4

SHIP_HITBOX = (
    (0, 0), (0, -1), (0, 1), (-1, 0), (1, 0),
    (-1, -1), (1, -1), (-1, 1), (1, 1),
)


def _generate_asteroid_lumps():
    """Blasteroids-style lumpy asteroid shape definition."""
    lumps = []
    for _ in range(random.randint(3, 6)):
        angle = random.uniform(0, 2 * math.pi)
        distance_frac = random.uniform(0, 0.5)
        lump_radius_frac = random.uniform(0.2, 0.5)
        lumps.append((
            math.cos(angle) * distance_frac,
            math.sin(angle) * distance_frac,
            lump_radius_frac,
        ))
    return lumps


def _pick_asteroid_color():
    roll = random.random()
    if roll < 0.9:
        return ASTEROID_COLOR_OPTIONS[0]
    if roll < 0.95:
        return ASTEROID_COLOR_OPTIONS[1]
    return ASTEROID_COLOR_OPTIONS[2]


def _shade_asteroid_color(color, brightness_factor):
    r, g, b = color
    return (
        min(255, int(r * brightness_factor)),
        min(255, int(g * brightness_factor)),
        min(255, int(b * brightness_factor)),
    )


def _asteroid_pixel_solid(i, j, size, lumps):
    """True when map offset (i, j) from asteroid center is inside the lump shape."""
    bounding_size = int(size * 1.2)
    if abs(i) > bounding_size or abs(j) > bounding_size:
        return False

    for frac_dx, frac_dy, frac_r in lumps:
        effective_dx = frac_dx * size
        effective_dy = frac_dy * size
        effective_radius = frac_r * size
        distance = math.sqrt((i - effective_dx) ** 2 + (j - effective_dy) ** 2)
        if distance < effective_radius:
            return True
    return False


def _paint_asteroid_to_layer(layer, cx, cy, size, color, lumps, dim_factor=1.0, obstacle_map=None):
    """Stamp one lump-shaded asteroid into a layer map (Blasteroids draw logic)."""
    bounding_size = int(size * 1.2)
    lw = layer.width
    lh = layer.height

    for j in range(-bounding_size, bounding_size + 1):
        for i in range(-bounding_size, bounding_size + 1):
            max_depth = -1.0
            selected_lump = None
            for frac_dx, frac_dy, frac_r in lumps:
                effective_dx = frac_dx * size
                effective_dy = frac_dy * size
                effective_radius = frac_r * size
                distance = math.sqrt((i - effective_dx) ** 2 + (j - effective_dy) ** 2)
                if distance < effective_radius:
                    depth = effective_radius - distance
                    if depth > max_depth:
                        max_depth = depth
                        selected_lump = (frac_dx, frac_dy, frac_r)

            if not selected_lump:
                continue

            frac_dx, frac_dy, frac_r = selected_lump
            effective_dx = frac_dx * size
            effective_dy = frac_dy * size
            effective_radius = frac_r * size
            rel_i = i - effective_dx
            rel_j = j - effective_dy
            brightness = 1.0 - ASTEROID_LIGHTING_CONTRAST * (rel_i + rel_j) / (2 * max(effective_radius, 0.5))
            brightness = max(0.64, min(1.35, brightness)) * dim_factor
            rgb = _shade_asteroid_color(color, brightness)
            x = (cx + i) % lw
            y = (cy + j) % lh
            layer.map[y][x] = rgb
            if obstacle_map is not None:
                obstacle_map[y][x] = True


def _pick_layer_asteroid_color(layer_name):
    if layer_name == "foreground":
        return random.choice(FOREGROUND_ASTEROID_COLORS)
    return _pick_asteroid_color()


def _build_asteroid_sprite_pixels(size, color, lumps, dim_factor=1.0):
    """Precompute lump-shaded pixels once — avoids heavy per-frame math on the Pi."""
    pixels = []
    bounding_size = int(size * 1.2)
    for j in range(-bounding_size, bounding_size + 1):
        for i in range(-bounding_size, bounding_size + 1):
            max_depth = -1.0
            selected_lump = None
            for frac_dx, frac_dy, frac_r in lumps:
                effective_dx = frac_dx * size
                effective_dy = frac_dy * size
                effective_radius = frac_r * size
                distance = math.sqrt((i - effective_dx) ** 2 + (j - effective_dy) ** 2)
                if distance < effective_radius:
                    depth = effective_radius - distance
                    if depth > max_depth:
                        max_depth = depth
                        selected_lump = (frac_dx, frac_dy, frac_r)

            if not selected_lump:
                continue

            frac_dx, frac_dy, frac_r = selected_lump
            effective_dx = frac_dx * size
            effective_dy = frac_dy * size
            effective_radius = frac_r * size
            rel_i = i - effective_dx
            rel_j = j - effective_dy
            brightness = 1.0 - ASTEROID_LIGHTING_CONTRAST * (rel_i + rel_j) / (2 * max(effective_radius, 0.5))
            brightness = max(0.64, min(1.35, brightness)) * dim_factor
            pixels.append((i, j, _shade_asteroid_color(color, brightness)))
    return pixels


class ForegroundAsteroid:
    """Breakable drifting rock — world position, velocity, Blasteroids-style lumps."""

    def __init__(
        self, h, v, size=None, color=None, dx=None, dy=None, speed_range=None,
        merge_cooldown_until=0.0,
    ):
        self.h = float(h)
        self.v = float(v)
        self.size = size if size is not None else random.randint(*FOREGROUND_ASTEROID_SIZE_RANGE)
        self.color = color if color is not None else random.choice(FOREGROUND_ASTEROID_COLORS)
        self.lumps = _generate_asteroid_lumps()
        dim = FOREGROUND_ASTEROID_DIM
        self.sprite_pixels = _build_asteroid_sprite_pixels(
            self.size, self.color, self.lumps, dim,
        )
        self.alive = True
        self.hits_to_break = _asteroid_hits_to_break(self.size)
        self.hits_taken = 0
        self.merge_cooldown_until = merge_cooldown_until
        if dx is None or dy is None:
            angle = random.uniform(0, 2 * math.pi)
            if speed_range is None:
                speed_range = (FOREGROUND_ASTEROID_MIN_SPEED, FOREGROUND_ASTEROID_MAX_SPEED)
            speed = random.uniform(*speed_range)
            self.dx = math.cos(angle) * speed
            self.dy = math.sin(angle) * speed
        else:
            self.dx = dx
            self.dy = dy

    def move(self):
        self.h = (self.h + self.dx) % LAYER_WIDTH
        self.v = (self.v + self.dy) % LAYER_HEIGHT

    def touches_ship_pixels(self, fh, fy, ship_pixels):
        """Screen-space hit test — matches the same rounding used when drawing."""
        sh, sv = world_to_screen(self.h, self.v, fh, fy)
        center_h = int(round(sh))
        center_v = int(round(sv))
        for i, j, _ in self.sprite_pixels:
            if (center_h + i, center_v + j) in ship_pixels:
                return True
        return False

    def draw(self, canvas, fh, fy):
        """Blit cached sprite pixels to the canvas (like a ship sprite)."""
        sh, sv = world_to_screen(self.h, self.v, fh, fy)
        center_h = int(round(sh))
        center_v = int(round(sv))
        for i, j, rgb in self.sprite_pixels:
            px = center_h + i
            py = center_v + j
            if 0 <= px < WIDTH and 0 <= py < HEIGHT:
                canvas.SetPixel(px, py, *rgb)


class Crystal:
    """Bright yellow loot — drifts after rock breaks; ship and aliens race to collect."""

    def __init__(self, h, v, dx=None, dy=None):
        self.h = float(h)
        self.v = float(v)
        self.alive = True
        if dx is None or dy is None:
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(CRYSTAL_MIN_SPEED, CRYSTAL_MAX_SPEED)
            self.dx = math.cos(angle) * speed
            self.dy = math.sin(angle) * speed
        else:
            self.dx = dx
            self.dy = dy

    def move(self):
        self.h = (self.h + self.dx) % LAYER_WIDTH
        self.v = (self.v + self.dy) % LAYER_HEIGHT

    def screen_pixels(self, fh, fy):
        sh, sv = world_to_screen(self.h, self.v, fh, fy)
        center_h = int(round(sh))
        center_v = int(round(sv))
        return [
            (center_h + dx, center_v + dy, rgb)
            for dx, dy, rgb in CRYSTAL_PIXELS
        ]

    def touches_ship_pixels(self, fh, fy, ship_pixels):
        for px, py, _ in self.screen_pixels(fh, fy):
            if (px, py) in ship_pixels:
                return True
        return False

    def touches_enemy_sprite(self, fh, fy, ship):
        sh, sv = world_to_screen(ship.h, ship.v, fh, fy)
        sh = int(round(sh))
        sv = int(round(sv))
        frame = _enemy_animation_frame(ship)
        grid = ship.grid[frame]
        crystal_pixels = {(px, py) for px, py, _ in self.screen_pixels(fh, fy)}
        for count in range(ship.width * ship.height):
            y, x = divmod(count, ship.width)
            r, g, b = LED.ColorList[grid[count]]
            if r > 0 or g > 0 or b > 0:
                if (sh + x, sv + y) in crystal_pixels:
                    return True
        return False

    def draw(self, canvas, fh, fy):
        for px, py, rgb in self.screen_pixels(fh, fy):
            if 0 <= px < WIDTH and 0 <= py < HEIGHT:
                canvas.SetPixel(px, py, *rgb)


#------------------------------------------------------------------------------
# Mother UFO — large metallic sphere with blinking nav lights
#------------------------------------------------------------------------------

def _build_mother_sphere_frame(light_phase):
    """
    Procedural shaded metal sphere (center = 0,0).
    light_phase 0/1 toggles red↔green nav lights around the equator.
    """
    pixels = []
    R = MOTHER_RADIUS
    R2 = R * R
    # Nav light seats on the equator (left/right/top-ish)
    light_seats = (
        (-R + 1, 0),
        (R - 1, 0),
        (0, -R + 2),
        (0, R - 2),
        (-R + 2, -R + 3),
        (R - 2, R - 3),
    )
    for dy in range(-R, R + 1):
        for dx in range(-R, R + 1):
            d2 = dx * dx + dy * dy
            if d2 > R2:
                continue
            # Sphere normal
            nz = math.sqrt(max(0.0, R2 - d2)) / float(R)
            nx = dx / float(R)
            ny = dy / float(R)
            # Key light from upper-left
            ndotl = max(0.0, nx * (-0.45) + ny * (-0.55) + nz * 0.78)
            # Cool metallic base
            metal = 38 + int(165 * ndotl)
            rim = (1.0 - nz) * 0.55
            r = min(255, int(metal * 0.92 + rim * 50))
            g = min(255, int(metal * 0.95 + rim * 55))
            b = min(255, int(metal * 1.08 + rim * 70))
            # Specular glint
            if ndotl > 0.88 and nz > 0.55:
                glint = int((ndotl - 0.88) * 900)
                r = min(255, r + glint)
                g = min(255, g + glint)
                b = min(255, b + glint)
            # Equator belt slightly darker (panel seam)
            if abs(dy) <= 1 and d2 < (R - 1) * (R - 1):
                r = max(20, int(r * 0.78))
                g = max(20, int(g * 0.80))
                b = max(30, int(b * 0.88))
            pixels.append((dx, dy, (r, g, b)))

    # Blinking red / green nav lights
    for i, (lx, ly) in enumerate(light_seats):
        # Alternate colors; swap every phase
        if ((i + light_phase) % 2) == 0:
            rgb = (255, 30, 25)   # red
        else:
            rgb = (30, 255, 50)   # green
        # Bright core + dim halo
        for hx, hy, scale in (
            (0, 0, 1.0),
            (1, 0, 0.45), (-1, 0, 0.45),
            (0, 1, 0.45), (0, -1, 0.45),
        ):
            px, py = lx + hx, ly + hy
            if px * px + py * py > R2 + 2:
                continue
            pixels.append((
                px, py,
                (
                    min(255, int(rgb[0] * scale)),
                    min(255, int(rgb[1] * scale)),
                    min(255, int(rgb[2] * scale)),
                ),
            ))
    return pixels


# Cache two animation frames (light phase 0 / 1)
_MOTHER_FRAMES = None


def _mother_frames():
    global _MOTHER_FRAMES
    if _MOTHER_FRAMES is None:
        _MOTHER_FRAMES = (
            _build_mother_sphere_frame(0),
            _build_mother_sphere_frame(1),
        )
    return _MOTHER_FRAMES


class MotherShip(object):
    """Large floating metallic sphere UFO — minds its own business until hunted."""

    def __init__(self, h=None, v=None):
        if h is None or v is None:
            h = random.uniform(0, LAYER_WIDTH)
            v = random.uniform(0, LAYER_HEIGHT)
        self.h = float(h)
        self.v = float(v)
        angle = random.uniform(0, 2 * math.pi)
        self.vel_h = math.cos(angle) * MOTHER_FLOAT_SPEED
        self.vel_v = math.sin(angle) * MOTHER_FLOAT_SPEED
        self.heading = angle
        self.alive = True
        self.hits = 0
        self.radius = float(MOTHER_RADIUS)
        self.respawn_at = 0.0
        # Aliases for hunt intercept math (same fields as asteroids)
        self.dx = self.vel_h
        self.dy = self.vel_v

    def update(self, dt):
        if not self.alive:
            return
        # Gentle wander — slow heading drift, constant float speed
        self.heading += random.uniform(-MOTHER_TURN_WANDER, MOTHER_TURN_WANDER) * (
            dt * PHYSICS_FPS
        )
        speed = MOTHER_FLOAT_SPEED
        target_vh = math.cos(self.heading) * speed
        target_vv = math.sin(self.heading) * speed
        blend = min(1.0, 0.04 * dt * PHYSICS_FPS)
        self.vel_h += (target_vh - self.vel_h) * blend
        self.vel_v += (target_vv - self.vel_v) * blend
        self.dx = self.vel_h
        self.dy = self.vel_v
        self.h = (self.h + self.vel_h * dt * PHYSICS_FPS) % LAYER_WIDTH
        self.v = (self.v + self.vel_v * dt * PHYSICS_FPS) % LAYER_HEIGHT

    def frame_pixels(self, now):
        phase = int(now * MOTHER_LIGHT_BLINK_HZ) % 2
        return _mother_frames()[phase]

    def draw(self, canvas, fh, fy, now):
        if not self.alive:
            return
        sh, sv = world_to_screen(self.h, self.v, fh, fy)
        cx = int(round(sh))
        cy = int(round(sv))
        # Off-screen cull with margin
        if (
            cx + self.radius < -2
            or cy + self.radius < -2
            or cx - self.radius > WIDTH + 2
            or cy - self.radius > HEIGHT + 2
        ):
            return
        for dx, dy, rgb in self.frame_pixels(now):
            px, py = cx + dx, cy + dy
            if 0 <= px < WIDTH and 0 <= py < HEIGHT:
                canvas.SetPixel(px, py, *rgb)

    def contains_world_point(self, wh, wv):
        dh = _toroidal_delta(self.h, wh, LAYER_WIDTH)
        dv = _toroidal_delta(self.v, wv, LAYER_HEIGHT)
        return math.hypot(dh, dv) <= self.radius + 0.8

    def take_hit(self):
        if not self.alive:
            return False
        self.hits += 1
        return self.hits >= MOTHER_HIT_POINTS


class CrystalMissile(object):
    """Homed crystal fired from the ship when hunting the mother UFO."""

    def __init__(self, h, v, angle):
        self.h = float(h)
        self.v = float(v)
        self.angle = float(angle)
        self.speed = CRYSTAL_MISSILE_SPEED
        self.alive = True
        self.age = 0.0

    def update(self, dt, target):
        if not self.alive:
            return
        self.age += dt
        if self.age > 8.0:
            self.alive = False
            return
        if target is not None and target.alive:
            dh = _toroidal_delta(self.h, target.h, LAYER_WIDTH)
            dv = _toroidal_delta(self.v, target.v, LAYER_HEIGHT)
            desired = math.atan2(dv, dh)
            # Shortest turn toward target
            err = (desired - self.angle + math.pi) % (2 * math.pi) - math.pi
            max_turn = CRYSTAL_MISSILE_TURN * dt * PHYSICS_FPS
            if err > max_turn:
                err = max_turn
            elif err < -max_turn:
                err = -max_turn
            self.angle += err
        step = self.speed * dt * PHYSICS_FPS
        self.h = (self.h + math.cos(self.angle) * step) % LAYER_WIDTH
        self.v = (self.v + math.sin(self.angle) * step) % LAYER_HEIGHT
        if target is not None and target.alive:
            if target.contains_world_point(self.h, self.v):
                self.alive = False
                return "hit"
        return None

    def draw(self, canvas, fh, fy):
        if not self.alive:
            return
        for i in range(CRYSTAL_MISSILE_TRAIL):
            wh = (self.h - math.cos(self.angle) * i * 0.9) % LAYER_WIDTH
            wv = (self.v - math.sin(self.angle) * i * 0.9) % LAYER_HEIGHT
            sh, sv = world_to_screen(wh, wv, fh, fy)
            px, py = int(round(sh)), int(round(sv))
            if not (0 <= px < WIDTH and 0 <= py < HEIGHT):
                continue
            fade = max(0.25, 1.0 - i * 0.28)
            canvas.SetPixel(
                px, py,
                min(255, int(255 * fade)),
                min(255, int(255 * fade)),
                min(255, int(40 * fade)),
            )


def create_mother_ship(fh=0, fy=0):
    """Spawn mother UFO well away from the player."""
    player_wh, player_wv = player_world_position(fh, fy)
    for _ in range(40):
        h = random.uniform(0, LAYER_WIDTH)
        v = random.uniform(0, LAYER_HEIGHT)
        dh = min((h - player_wh) % LAYER_WIDTH, (player_wh - h) % LAYER_WIDTH)
        dv = min((v - player_wv) % LAYER_HEIGHT, (player_wv - v) % LAYER_HEIGHT)
        if math.hypot(dh, dv) > 120:
            return MotherShip(h, v)
    return MotherShip()


def mother_fantastic_explosion(mother):
    """Huge multi-color debris + spark bloom when the mother UFO is destroyed."""
    particles = []
    sparks = []
    # Shatter every metal sphere pixel into debris
    for dx, dy, rgb in _mother_frames()[0]:
        if random.random() > 0.55 and (dx * dx + dy * dy) > 4:
            continue
        wh = _wrap_world_coord(mother.h + dx, LAYER_WIDTH)
        wv = _wrap_world_coord(mother.v + dy, LAYER_HEIGHT)
        ang = math.atan2(dy, dx) if (dx or dy) else random.uniform(0, 2 * math.pi)
        speed = random.uniform(0.6, 2.8)
        particles.append(EnemyParticle(
            wh, wv, rgb[0], rgb[1], rgb[2],
            math.cos(ang) * speed + random.uniform(-0.3, 0.3),
            math.sin(ang) * speed + random.uniform(-0.3, 0.3),
        ))
        particles[-1].lifespan = int(ENEMY_PARTICLE_LIFESPAN * random.uniform(1.4, 2.4))

    # Extra white/hot core burst
    for _ in range(MOTHER_EXPLOSION_PARTICLES):
        ang = random.uniform(0, 2 * math.pi)
        speed = random.uniform(0.4, 3.2)
        tone = random.choice((
            (255, 255, 255), (255, 220, 80), (255, 120, 30),
            (80, 200, 255), (255, 40, 40), (40, 255, 80),
        ))
        p = EnemyParticle(
            mother.h, mother.v, *tone,
            math.cos(ang) * speed, math.sin(ang) * speed,
        )
        p.lifespan = int(ENEMY_PARTICLE_LIFESPAN * random.uniform(1.6, 2.8))
        particles.append(p)

    for _ in range(MOTHER_EXPLOSION_SPARKS):
        ang = random.uniform(0, 2 * math.pi)
        sparks.append(Spark(
            mother.h, mother.v, ang,
            speed=random.uniform(1.2, 3.5),
            length=random.randint(4, 8),
        ))
    return particles, sparks


def update_crystal_missiles(missiles, mother, dt):
    """Home missiles toward mother. Returns number of new hits this frame."""
    hits = 0
    if mother is None:
        for m in missiles:
            if m.alive:
                m.update(dt, None)
        missiles[:] = [m for m in missiles if m.alive]
        return 0
    for m in missiles:
        if not m.alive:
            continue
        result = m.update(dt, mother)
        if result == "hit":
            hits += 1
    missiles[:] = [m for m in missiles if m.alive]
    return hits


def fire_crystal_missile(missiles, fh, fy, ship_angle, mother):
    """Launch one homing crystal from the ship toward the mother UFO."""
    player_wh, player_wv = player_world_position(fh, fy)
    # Lead slightly along ship nose
    nose_h = player_wh + math.cos(ship_angle) * 2.5
    nose_v = player_wv + math.sin(ship_angle) * 2.5
    angle = ship_angle
    if mother is not None and mother.alive:
        dh = _toroidal_delta(nose_h, mother.h, LAYER_WIDTH)
        dv = _toroidal_delta(nose_v, mother.v, LAYER_HEIGHT)
        angle = math.atan2(dv, dh)
    missiles.append(CrystalMissile(nose_h, nose_v, angle))


class Spark:
    """Short-lived explosion streak in world coordinates."""

    def __init__(self, wh, wv, angle, speed, length):
        self.wh = wh
        self.wv = wv
        self.angle = angle
        self.speed = speed
        self.length = max(1, min(length, 8))
        self.lifespan = SPARK_TRAIL_LENGTH

    def move(self, layer_width, layer_height):
        self.wh = (self.wh + math.cos(self.angle) * self.speed) % layer_width
        self.wv = (self.wv + math.sin(self.angle) * self.speed) % layer_height

    def draw(self, canvas, fh, fy):
        for i in range(self.length):
            wh = (self.wh - math.cos(self.angle) * i) % LAYER_WIDTH
            wv = (self.wv - math.sin(self.angle) * i) % LAYER_HEIGHT
            sh, sv = world_to_screen(wh, wv, fh, fy)
            if not (0 <= sh < WIDTH and 0 <= sv < HEIGHT):
                continue
            fade = max(32, SPARK_COLOR[0] - i * (SPARK_COLOR[0] // SPARK_TRAIL_LENGTH * 2))
            canvas.SetPixel(sh, sv, fade, fade * 3 // 4, fade // 2)


class EnemyParticle:
    """Defender-style debris — one colored sprite pixel with drift and gravity."""

    def __init__(self, wh, wv, r, g, b, vel_h, vel_v):
        self.wh = float(wh)
        self.wv = float(wv)
        self.r, self.g, self.b = r, g, b
        self.vel_h = vel_h
        self.vel_v = vel_v
        self.alive = True
        self.lifespan = ENEMY_PARTICLE_LIFESPAN

    def move(self, dt):
        self.vel_v += _physics_scale(ENEMY_PARTICLE_GRAVITY, dt)
        self.wh = (self.wh + self.vel_h) % LAYER_WIDTH
        self.wv = (self.wv + self.vel_v) % LAYER_HEIGHT
        self.lifespan -= 1

    def draw(self, canvas, fh, fy):
        sh, sv = world_to_screen(self.wh, self.wv, fh, fy)
        sh = int(round(sh))
        sv = int(round(sv))
        if 0 <= sh < WIDTH and 0 <= sv < HEIGHT:
            canvas.SetPixel(sh, sv, self.r, self.g, self.b)


def _random_asteroid_world_spawn(player_wh, player_wv):
    """Spawn a drifting rock somewhere on the map, away from the player."""
    for _ in range(40):
        wh = random.randint(0, LAYER_WIDTH - 1)
        wv = random.randint(0, LAYER_HEIGHT - 1)
        dh = min((wh - player_wh) % LAYER_WIDTH, (player_wh - wh) % LAYER_WIDTH)
        dv = min((wv - player_wv) % LAYER_HEIGHT, (player_wv - wv) % LAYER_HEIGHT)
        if dh + dv > 24:
            return wh, wv
    return random.randint(0, LAYER_WIDTH - 1), random.randint(0, LAYER_HEIGHT - 1)


def _random_large_asteroid_spawn(player_wh, player_wv):
    """Place a large breakable rock within hunt range on the wrapping map."""
    for _ in range(40):
        wh = random.randint(0, LAYER_WIDTH - 1)
        wv = random.randint(0, LAYER_HEIGHT - 1)
        dh = min((wh - player_wh) % LAYER_WIDTH, (player_wh - wh) % LAYER_WIDTH)
        dv = min((wv - player_wv) % LAYER_HEIGHT, (player_wv - wv) % LAYER_HEIGHT)
        dist = math.hypot(dh, dv)
        if 28 <= dist <= 160:
            return wh, wv
    return _random_asteroid_world_spawn(player_wh, player_wv)


def create_foreground_asteroids(count, size_range, fh=0, fy=0):
    """Spawn breakable rocks with random drift trajectories in world space."""
    smin, smax = size_range
    player_wh, player_wv = player_world_position(fh, fy)
    asteroids = []
    for _ in range(count):
        wh, wv = _random_asteroid_world_spawn(player_wh, player_wv)
        asteroids.append(ForegroundAsteroid(wh, wv, size=random.randint(smin, smax)))
    return asteroids


def create_large_slow_asteroids(count, fh=0, fy=0):
    """Spawn large slow breakable rocks — split on contact like the smaller ones."""
    smin, smax = LARGE_SLOW_ASTEROID_SIZE_RANGE
    player_wh, player_wv = player_world_position(fh, fy)
    asteroids = []
    for _ in range(count):
        wh, wv = _random_large_asteroid_spawn(player_wh, player_wv)
        asteroids.append(ForegroundAsteroid(
            wh, wv,
            size=random.randint(smin, smax),
            speed_range=(LARGE_SLOW_ASTEROID_MIN_SPEED, LARGE_SLOW_ASTEROID_MAX_SPEED),
        ))
    return asteroids


def create_all_foreground_asteroids(fh=0, fy=0):
    """22 standard breakable rocks plus 5 large slow breakable rocks."""
    asteroids = create_foreground_asteroids(
        FOREGROUND_ASTEROID_COUNT, FOREGROUND_ASTEROID_SIZE_RANGE, fh, fy,
    )
    asteroids.extend(create_large_slow_asteroids(LARGE_SLOW_ASTEROID_COUNT, fh, fy))
    return asteroids


def count_alive_foreground_asteroids(foreground_asteroids):
    return sum(1 for asteroid in foreground_asteroids if asteroid.alive)


def replenish_foreground_asteroids_if_empty(foreground_asteroids, fh, fy):
    """Drop in a fresh wave once the player has blown up every rock."""
    if count_alive_foreground_asteroids(foreground_asteroids) > 0:
        return False
    foreground_asteroids.extend(create_all_foreground_asteroids(fh, fy))
    return True


def _asteroid_mass(size):
    """Mass scales with sprite area (size²)."""
    return size * size


def _asteroid_collision_radius(size):
    return size * FOREGROUND_ASTEROID_DIM


def _asteroids_collide(a, b):
    """True when two breakable rocks overlap on the wrapping map."""
    dh = _toroidal_delta(a.h, b.h, LAYER_WIDTH)
    dv = _toroidal_delta(a.v, b.v, LAYER_HEIGHT)
    dist = math.hypot(dh, dv)
    touch_dist = (
        _asteroid_collision_radius(a.size) + _asteroid_collision_radius(b.size)
    ) * ASTEROID_COLLIDE_SCALE
    return dist < touch_dist


def asteroid_can_merge(asteroid, now):
    """Split fragments cannot recombine until their merge cooldown expires."""
    return now >= asteroid.merge_cooldown_until


def _asteroids_can_merge(a, b, now):
    return (
        _asteroids_collide(a, b)
        and asteroid_can_merge(a, now)
        and asteroid_can_merge(b, now)
    )


def merge_two_asteroids(a, b):
    """Combine two colliding rocks — summed area, momentum-conserving velocity."""
    m1 = _asteroid_mass(a.size)
    m2 = _asteroid_mass(b.size)
    total_mass = m1 + m2

    dh = _toroidal_delta(a.h, b.h, LAYER_WIDTH)
    dv = _toroidal_delta(a.v, b.v, LAYER_HEIGHT)
    h = _wrap_world_coord(a.h + dh * m2 / total_mass, LAYER_WIDTH)
    v = _wrap_world_coord(a.v + dv * m2 / total_mass, LAYER_HEIGHT)

    new_size = max(MIN_FOREGROUND_ASTEROID_SIZE, round(math.sqrt(m1 + m2)))
    dx = (m1 * a.dx + m2 * b.dx) / total_mass
    dy = (m1 * a.dy + m2 * b.dy) / total_mass
    color = a.color if a.size >= b.size else b.color

    return ForegroundAsteroid(h, v, size=new_size, color=color, dx=dx, dy=dy)


def resolve_asteroid_collisions(foreground_asteroids, now):
    """Merge breakable rocks that collide — one pair per pass until stable."""
    merged_any = True
    while merged_any:
        merged_any = False
        alive = [a for a in foreground_asteroids if a.alive]
        for i in range(len(alive)):
            for j in range(i + 1, len(alive)):
                if _asteroids_can_merge(alive[i], alive[j], now):
                    merged = merge_two_asteroids(alive[i], alive[j])
                    alive[i].alive = False
                    alive[j].alive = False
                    foreground_asteroids.append(merged)
                    merged_any = True
                    break
            if merged_any:
                break


def update_foreground_asteroids(foreground_asteroids, now):
    for asteroid in foreground_asteroids:
        if asteroid.alive:
            asteroid.move()
    resolve_asteroid_collisions(foreground_asteroids, now)


def draw_foreground_asteroids(canvas, foreground_asteroids, fh, fy):
    for asteroid in foreground_asteroids:
        if asteroid.alive:
            asteroid.draw(canvas, fh, fy)
    return canvas


def ship_hits_foreground_asteroids(foreground_asteroids, fh, fy):
    return bool(asteroids_touching_ship(foreground_asteroids, fh, fy))


_SHIP_PIXELS = frozenset((SHIP_H + dx, SHIP_V + dy) for dx, dy in SHIP_HITBOX)


def _expand_pixel_zone(pixels):
    """Include every pixel orthogonally and diagonally beside a zone."""
    zone = set(pixels)
    for px, py in pixels:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                zone.add((px + dx, py + dy))
    return frozenset(zone)


_SHIP_COLLECT_PIXELS = _expand_pixel_zone(_SHIP_PIXELS)


def asteroids_touching_ship(foreground_asteroids, fh, fy):
    """Return foreground asteroids whose drawn pixels overlap the ship hitbox."""
    touching = []
    for asteroid in foreground_asteroids:
        if asteroid.alive and asteroid.touches_ship_pixels(fh, fy, _SHIP_PIXELS):
            touching.append(asteroid)
    return touching


def _asteroid_break_tier(size):
    """big (7+) → small (4–6) → tiny (2–3) → explode."""
    if size >= ASTEROID_TIER_BIG_MIN:
        return "big"
    if size >= ASTEROID_TIER_SMALL_MIN:
        return "small"
    return "tiny"


def _asteroid_hits_to_break(size):
    """Ram hits required before the rock splits — 4 for huge, stepping down to 1."""
    if size >= ASTEROID_HITS_HUGE_MIN:
        return 4
    if size >= ASTEROID_HITS_BIG_MIN:
        return 3
    if size >= ASTEROID_TIER_SMALL_MIN:
        return 2
    return 1


def apply_ship_hits_to_asteroids(hit_asteroids):
    """Count one player ram per rock; return those damaged enough to split."""
    ready_to_split = []
    for asteroid in hit_asteroids:
        if not asteroid.alive:
            continue
        asteroid.hits_taken += 1
        if asteroid.hits_taken >= asteroid.hits_to_break:
            ready_to_split.append(asteroid)
    return ready_to_split


def _split_child_sizes(parent_size, tier, count):
    """Pick child sizes one tier below the parent, with slight variation."""
    smin, smax = ASTEROID_SMALL_SIZE_RANGE if tier == "big" else ASTEROID_TINY_SIZE_RANGE
    base = max(smin, min(smax, parent_size // 2))
    sizes = []
    for _ in range(count):
        size = base + random.randint(-1, 0)
        sizes.append(max(smin, min(smax, size)))
    return sizes


def _split_fragment_angles(ship_angle, count):
    """Random break headings anchored perpendicular to the ramming ship."""
    angles = []
    for _ in range(count):
        side = random.choice((-1, 1))
        angles.append(
            ship_angle
            + side * (
                math.pi / 2
                + random.uniform(-SPLIT_PERP_SPREAD_RAD, SPLIT_PERP_SPREAD_RAD)
            )
        )
    return angles


def _split_fly_apart_burst(tier):
    """Outward shove applied along each fragment's break angle."""
    if tier == "big":
        return random.uniform(*SPLIT_FLY_APART_BIG)
    return random.uniform(*SPLIT_FLY_APART_SMALL)


def _split_fragment_state(asteroid, angle, tier, child_size):
    """Spawn position and velocity for a fragment flying away from the break."""
    burst = _split_fly_apart_burst(tier)
    offset = SPLIT_SPAWN_OFFSET + child_size * 0.2
    h = asteroid.h + math.cos(angle) * offset
    v = asteroid.v + math.sin(angle) * offset
    dx = asteroid.dx * SPLIT_PARENT_MOMENTUM + math.cos(angle) * burst
    dy = asteroid.dy * SPLIT_PARENT_MOMENTUM + math.sin(angle) * burst
    speed = math.hypot(dx, dy)
    max_speed = FOREGROUND_ASTEROID_MAX_SPEED * 1.35
    if speed > max_speed:
        scale = max_speed / speed
        dx *= scale
        dy *= scale
    return h, v, dx, dy


def spawn_crystals_from_break(wh, wv, ship_angle):
    """0–3 bright crystals ejected perpendicular to the ramming ship."""
    crystals = []
    for _ in range(random.randint(0, CRYSTAL_MAX_PER_BREAK)):
        side = random.choice((-1, 1))
        angle = (
            ship_angle
            + side * (math.pi / 2 + random.uniform(-0.6, 0.6))
        )
        speed = random.uniform(0.10, 0.22)
        offset = random.uniform(0.8, 2.2)
        crystals.append(Crystal(
            wh + math.cos(angle) * offset,
            wv + math.sin(angle) * offset,
            dx=math.cos(angle) * speed,
            dy=math.sin(angle) * speed,
        ))
    return crystals


def split_asteroids(foreground_asteroids, hit_asteroids, now, ship_angle):
    """
    Tiered break on ship contact — big rocks split to several small pieces,
    small rocks split to several tiny pieces, tiny rocks explode into sparks only.
    """
    if not hit_asteroids:
        return [], []

    new_asteroids = []
    sparks = []
    crystals = []
    merge_cooldown_until = now + ASTEROID_MERGE_COOLDOWN_SEC

    for asteroid in hit_asteroids:
        if not asteroid.alive:
            continue
        asteroid.alive = False
        tier = _asteroid_break_tier(asteroid.size)

        if tier != "tiny":
            split_count = BIG_ROCK_SPLIT_COUNT if tier == "big" else SMALL_ROCK_SPLIT_COUNT
            for angle, child_size in zip(
                _split_fragment_angles(ship_angle, split_count),
                _split_child_sizes(asteroid.size, tier, split_count),
            ):
                frag_h, frag_v, frag_dx, frag_dy = _split_fragment_state(
                    asteroid, angle, tier, child_size,
                )
                new_asteroids.append(ForegroundAsteroid(
                    frag_h,
                    frag_v,
                    child_size,
                    asteroid.color,
                    dx=frag_dx,
                    dy=frag_dy,
                    merge_cooldown_until=merge_cooldown_until,
                ))

        spark_count = TINY_ROCK_SPARK_COUNT if tier == "tiny" else SPARK_COUNT
        for _ in range(spark_count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(0.15, 1.2)
            sparks.append(Spark(asteroid.h, asteroid.v, angle, speed, int(asteroid.size * 1.5)))
        crystals.extend(spawn_crystals_from_break(asteroid.h, asteroid.v, ship_angle))

    foreground_asteroids[:] = [a for a in foreground_asteroids if a.alive]
    foreground_asteroids.extend(new_asteroids)
    return sparks, crystals


def find_nearest_crystal(crystals, fh, fy):
    """Return the closest alive crystal to the centered ship."""
    nearest = None
    nearest_dist = float("inf")
    for crystal in crystals:
        if not crystal.alive:
            continue
        dist = distance_to_world_point(fh, fy, crystal.h, crystal.v)
        if dist < nearest_dist:
            nearest_dist = dist
            nearest = crystal
    return nearest, nearest_dist


def crystal_on_screen(crystal, fh, fy):
    if crystal is None or not crystal.alive:
        return False
    sh, sv = world_to_screen(crystal.h, crystal.v, fh, fy)
    sh = int(round(sh))
    sv = int(round(sv))
    return _rect_visible_on_screen(sh, sv, 1, 1)


def update_crystals(crystals):
    for crystal in crystals:
        if crystal.alive:
            crystal.move()


def collect_crystals_for_ship(crystals, fh, fy):
    """Remove crystals on or beside the player ship."""
    collected = 0
    for crystal in crystals:
        if crystal.alive and crystal.touches_ship_pixels(fh, fy, _SHIP_COLLECT_PIXELS):
            crystal.alive = False
            collected += 1
    return collected


def collect_crystals_for_enemies(crystals, enemy_ships, fh, fy):
    """Remove crystals alien ships scoop up."""
    for ship in enemy_ships:
        if not _enemy_alive(ship):
            continue
        for crystal in crystals:
            if crystal.alive and crystal.touches_enemy_sprite(fh, fy, ship):
                crystal.alive = False


def prune_dead_crystals(crystals):
    crystals[:] = [crystal for crystal in crystals if crystal.alive]


def draw_crystals(canvas, crystals, fh, fy):
    for crystal in crystals:
        if crystal.alive:
            crystal.draw(canvas, fh, fy)
    return canvas


def update_sparks(sparks):
    alive = []
    for spark in sparks:
        spark.move(LAYER_WIDTH, LAYER_HEIGHT)
        spark.lifespan -= 1
        if spark.lifespan > 0:
            alive.append(spark)
    sparks[:] = alive


def draw_sparks(canvas, sparks, fh, fy):
    for spark in sparks:
        spark.draw(canvas, fh, fy)


def update_enemy_particles(particles, dt):
    alive = []
    for particle in particles:
        if not particle.alive:
            continue
        particle.move(dt)
        if particle.lifespan > 0:
            alive.append(particle)
    particles[:] = alive


def draw_enemy_particles(canvas, particles, fh, fy):
    for particle in particles:
        particle.draw(canvas, fh, fy)


def _add_asteroids_to_layer(layer, count, size_range, dim_factor=1.0, obstacle_map=None, layer_name=None):
    """Scatter Blasteroids-style rocks across a parallax layer."""
    smin, smax = size_range
    for _ in range(count):
        cx = random.randint(0, layer.width - 1)
        cy = random.randint(0, layer.height - 1)
        size = random.randint(smin, smax)
        color = _pick_layer_asteroid_color(layer_name) if layer_name else _pick_asteroid_color()
        _paint_asteroid_to_layer(
            layer, cx, cy, size, color, _generate_asteroid_lumps(),
            dim_factor, obstacle_map=obstacle_map,
        )


STAR_DIM_FACTOR = 0.7


def _star_rgb(brightness, purple=False):
    """Blue-tinted star, dimmed 30%; optional slight purple for distant stars."""
    brightness = max(1, int(brightness * STAR_DIM_FACTOR))
    if purple:
        return (
            max(0, min(255, brightness * 45 // 100)),
            max(0, min(255, brightness * 22 // 100)),
            max(0, min(255, brightness * 88 // 100)),
        )
    return (
        max(0, brightness // 5),
        max(0, brightness // 3),
        brightness,
    )


def _add_far_stars(layer, starchance=184, progress_cb=None):
    """Sparse blue stars on FarBackground only — varying brightness."""
    lw = layer.width
    lh = layer.height
    star_positions = []

    for y in range(lh):
        for x in range(lw):
            if random.randint(0, starchance) != 1:
                layer.map[y][x] = (0, 0, 0)
                continue

            brightness = random.randint(25, 150)
            layer.map[y][x] = _star_rgb(brightness)
            star_positions.append((x, y, brightness))
        if progress_cb is not None and (y & 31) == 0:
            try:
                progress_cb()
            except Exception:
                pass

    for x, y, brightness in random.sample(
        star_positions, min(2, len(star_positions)),
    ):
        layer.map[y][x] = _star_rgb(brightness, purple=True)


def _add_background_stars(layer, starchance=99, progress_cb=None):
    """Extra stars on Background — denser than far field, up to 30% brighter."""
    max_brightness = min(255, int(150 * 1.3))
    for y in range(layer.height):
        for x in range(layer.width):
            if layer.map[y][x] != (0, 0, 0):
                continue
            if random.randint(0, starchance) != 1:
                continue
            brightness = random.randint(25, max_brightness)
            layer.map[y][x] = _star_rgb(brightness)
        if progress_cb is not None and (y & 31) == 0:
            try:
                progress_cb()
            except Exception:
                pass


def create_star_layers(progress_cb=None):
    """Build four oversized parallax layers.
    progress_cb() is optional — called between heavy steps so the intro
    starfield can keep animating during load.
    """
    def _tick():
        if progress_cb is not None:
            try:
                progress_cb()
            except Exception:
                pass

    far_background = LED.Layer(name="space_far", width=LAYER_WIDTH, height=LAYER_HEIGHT, h=0, v=0)
    background = LED.Layer(name="space_bg", width=LAYER_WIDTH, height=LAYER_HEIGHT, h=0, v=0)
    middleground = LED.Layer(name="space_mid", width=LAYER_WIDTH, height=LAYER_HEIGHT, h=0, v=0)
    foreground = LED.Layer(name="space_fg", width=LAYER_WIDTH, height=LAYER_HEIGHT, h=0, v=0)
    _tick()

    # FarBackground: blue stars only (25–150 brightness).
    _add_far_stars(far_background, progress_cb=progress_cb)
    _tick()

    # Background: nebula, gas giants, asteroid + metal ship clocks, then brighter stars in gaps.
    _add_nebula_patches(background, count=8)
    _tick()
    gas_giants = _add_gas_giants(background)
    _tick()
    clock_stations = _add_clock_stations(background)
    clock_stations.extend(_gas_giant_clock_stations(gas_giants))
    _tick()
    _add_background_stars(background, progress_cb=progress_cb)
    _tick()
    # Middleground: asteroids only.

    # Foreground parallax: small decorative rocks; breakable rocks are free objects on top.
    layer_map = {
        "background": background,
        "middleground": middleground,
        "foreground": foreground,
    }
    for layer_name, count, size_range, dim_factor in LAYER_ASTEROIDS:
        _add_asteroids_to_layer(
            layer_map[layer_name], count, size_range, dim_factor,
            layer_name=layer_name,
        )
        _tick()

    return far_background, background, middleground, foreground, clock_stations, gas_giants


def _nebula_blob_extent(blobs):
    extent = 0
    for ox, oy, radius, _, _ in blobs:
        extent = max(extent, abs(ox) + radius, abs(oy) + radius)
    return int(extent) + 2


def _nebula_falloff_at(dx, dy, blobs):
    """Merge overlapping soft blobs into one irregular gas mass."""
    best = 0.0
    for ox, oy, radius, stretch_h, stretch_v in blobs:
        bx = (dx - ox) / stretch_h
        by = (dy - oy) / stretch_v
        dist_sq = bx * bx + by * by
        limit = radius * radius
        if dist_sq < limit:
            best = max(best, 1.0 - dist_sq / limit)
    return best


def _add_nebula_patches(layer, count=8, dim=False):
    """Large irregular nebula clouds built from merged soft blobs."""
    palette = (
        (20, 0, 40),
        (0, 20, 50),
        (30, 10, 45),
        (10, 25, 35),
    )
    for _ in range(count):
        cx = random.randint(0, layer.width - 1)
        cy = random.randint(0, layer.height - 1)
        base = random.choice(palette)
        if dim:
            base = tuple(max(0, c // 2) for c in base)

        blobs = []
        for _ in range(random.randint(3, 6)):
            blobs.append((
                random.randint(-16, 16),
                random.randint(-12, 12),
                random.randint(16, 30),
                random.uniform(0.55, 1.45),
                random.uniform(0.55, 1.45),
            ))

        extent = _nebula_blob_extent(blobs)
        for dy in range(-extent, extent + 1):
            for dx in range(-extent, extent + 1):
                falloff = _nebula_falloff_at(dx, dy, blobs)
                if falloff <= 0:
                    continue
                x = (cx + dx) % layer.width
                y = (cy + dy) % layer.height
                if layer.map[y][x] == (0, 0, 0):
                    layer.map[y][x] = tuple(
                        max(0, min(255, int(c * falloff))) for c in base
                    )


def _gas_giant_rgb(dx, dy, radius, colors):
    """Soft banded sphere with limb darkening and a lit crescent."""
    dist = math.hypot(dx, dy)
    if dist > radius:
        return None

    band_idx = int((dy / max(1.0, radius * 0.42)) + 1.5) % len(colors)
    r, g, b = colors[band_idx]
    limb = 1.0 - 0.42 * (dist / max(radius, 1)) ** 1.15
    lit = 1.0 + 0.22 * max(0.0, (-dx * 0.65 - dy * 0.75) / radius)
    factor = max(0.38, min(1.3, limb * lit))
    return tuple(min(255, int(channel * factor)) for channel in (r, g, b))


def _gas_giant_clock_colors(colors):
    """Readable HH:MM accent and recessed backdrop from a planet palette."""
    brightest = max(colors, key=sum)
    darkest = min(colors, key=sum)
    mid = sorted(colors, key=sum)[1]
    label_rgb = tuple(
        min(255, max(72, int(channel * 1.08 + mid[i] * 0.22 + 28)))
        for i, channel in enumerate(brightest)
    )
    back_rgb = tuple(
        max(6, int(channel * 0.18 + darkest[i] * 0.35))
        for i, channel in enumerate(mid)
    )
    return label_rgb, back_rgb


def _paint_gas_giant_to_layer(layer, cx, cy, radius, colors, ringed):
    """Stamp one banded gas giant (and optional rings) onto the background layer."""
    for dy in range(-radius - 4, radius + 5):
        for dx in range(-radius - 8, radius + 9):
            x = (cx + dx) % layer.width
            y = (cy + dy) % layer.height

            if ringed and abs(dy) <= max(2, radius // 7):
                ring_dist = abs(math.hypot(dx, dy) - radius * 0.92)
                if ring_dist < 2.2 and abs(dx) > radius * 0.35:
                    ring_rgb = tuple(
                        min(255, int(channel * 0.72 + colors[1][i] * 0.28))
                        for i, channel in enumerate(colors[0])
                    )
                    layer.map[y][x] = ring_rgb
                    continue

            rgb = _gas_giant_rgb(dx, dy, radius, colors)
            if rgb is not None:
                layer.map[y][x] = rgb


def _add_gas_giants(layer, count=None):
    """Paint large banded planets onto the background layer."""
    if count is None:
        count = GAS_GIANT_COUNT

    planets = []
    palettes = (
        ((185, 145, 95), (150, 105, 65), (205, 165, 105)),
        ((215, 185, 135), (165, 135, 95), (110, 85, 60)),
        ((75, 115, 175), (50, 85, 140), (115, 150, 205)),
    )

    for _ in range(count):
        cx = random.randint(0, layer.width - 1)
        cy = random.randint(0, layer.height - 1)
        radius = random.randint(16, 24)
        colors = random.choice(palettes)
        ringed = random.random() < 0.45
        _paint_gas_giant_to_layer(layer, cx, cy, radius, colors, ringed)
        planets.append({
            "cx": cx, "cy": cy, "radius": radius,
            "colors": colors, "ringed": ringed,
        })

    return planets


def _gas_giant_clock_stations(gas_giants):
    """One HH:MM station per gas giant, tinted to that planet's palette."""
    stations = []
    for planet in gas_giants:
        label_rgb, back_rgb = _gas_giant_clock_colors(planet["colors"])
        stations.append({
            "cx": planet["cx"],
            "cy": planet["cy"],
            "kind": "gas_giant",
            "radius": planet["radius"],
            "colors": planet["colors"],
            "ringed": planet["ringed"],
            "label_rgb": label_rgb,
            "back_rgb": back_rgb,
        })
    return stations


ASTEROID_CLOCK_COUNT = 4
METAL_SHIP_CLOCK_COUNT = 1
ASTEROID_CLOCK_SIZE = 16
ASTEROID_CLOCK_COLOR = (142, 132, 118)
METAL_HIGHLIGHT = (168, 172, 182)
METAL_FACE = (96, 100, 112)
METAL_SHADOW = (42, 45, 54)
METAL_EDGE = (128, 132, 142)
INNER_BAY = (16, 19, 26)
TIME_LABEL_RGB = (90, 255, 140)
TIME_BACK_RGB = (8, 10, 16)
TIME_BACK_PAD_H = 2
TIME_BACK_PAD_V = 1


def _clock_asteroid_lumps():
    """Fixed bumpy lump profile for the interstellar clock asteroid."""
    return (
        (0.0, 0.0, 0.58),
        (0.34, 0.14, 0.42),
        (-0.30, 0.24, 0.44),
        (0.18, -0.36, 0.40),
        (-0.42, -0.18, 0.38),
        (0.44, -0.26, 0.34),
        (-0.14, 0.46, 0.32),
        (0.28, 0.38, 0.30),
        (-0.38, -0.36, 0.36),
        (0.06, -0.48, 0.32),
        (-0.46, 0.08, 0.28),
        (0.40, 0.30, 0.26),
    )


def _asteroid_clock_spawn_sites(layer_width, layer_height, count=ASTEROID_CLOCK_COUNT):
    """Spread asteroid clocks evenly across the map quadrants."""
    margin_h = layer_width // 8
    margin_v = layer_height // 8
    sites = (
        (margin_h * 2, margin_v * 2),
        (layer_width - margin_h * 2, margin_v * 2),
        (margin_h * 2, layer_height - margin_v * 2),
        (layer_width - margin_h * 2, layer_height - margin_v * 2),
    )
    return [(cx % layer_width, cy % layer_height) for cx, cy in sites[:count]]


def _metal_ship_clock_spawn_site(layer_width, layer_height):
    """Place the metal ship clock at the map center."""
    return layer_width // 2, layer_height // 2


def _metal_ship_clock_solid(dx, dy):
    """Large pointed-hull silhouette for the metal ship clock."""
    if abs(dx) <= 3 and -11 <= dy <= 7:
        return True
    if dy < -7 and abs(dx) <= max(0, (-dy - 6) // 2) + 1:
        return True
    if -7 <= dy <= 4 and abs(dx) <= 6:
        return True
    if -1 <= dy <= 3 and 4 <= abs(dx) <= 8:
        return True
    if 4 <= dy <= 8 and abs(dx) <= 5:
        return True
    if 6 <= dy <= 10 and 2 <= abs(dx) <= 5:
        return True
    return False


def _metal_ship_clock_rgb(dx, dy):
    """Shaded metallic hull pixel for the spaceship clock."""
    if not _metal_ship_clock_solid(dx, dy):
        return None

    if abs(dx) <= 5 and -1 <= dy <= 3:
        shade = 1.0 - 0.1 * (dx + 5) / 10.0
        return tuple(min(255, int(INNER_BAY[i] * shade)) for i in range(3))

    if dy <= -6:
        return METAL_HIGHLIGHT if dx <= 0 else METAL_EDGE
    if dy >= 6:
        return METAL_SHADOW if dx >= 0 else METAL_EDGE
    if abs(dx) >= 6:
        return METAL_EDGE

    gradient = 0.78 + 0.22 * ((-dx * 0.6 - dy * 0.4) / 12.0 + 0.5)
    gradient = max(0.65, min(1.15, gradient))
    return tuple(min(255, int(METAL_FACE[i] * gradient)) for i in range(3))


def _paint_metal_ship_clock(layer, cx, cy):
    """Stamp one large shaded metal spaceship hull onto the background layer."""
    for dy in range(-13, 12):
        for dx in range(-10, 11):
            rgb = _metal_ship_clock_rgb(dx, dy)
            if rgb is None:
                continue
            x = (cx + dx) % layer.width
            y = (cy + dy) % layer.height
            layer.map[y][x] = rgb


def _add_clock_stations(layer):
    """Paint asteroid clocks and one large metal spaceship clock on the background layer."""
    stations = []
    lumps = _clock_asteroid_lumps()
    for cx, cy in _asteroid_clock_spawn_sites(layer.width, layer.height):
        _paint_asteroid_to_layer(
            layer, cx, cy, ASTEROID_CLOCK_SIZE, ASTEROID_CLOCK_COLOR, lumps,
            dim_factor=1.0,
        )
        stations.append({
            "cx": cx, "cy": cy, "kind": "asteroid", "size": ASTEROID_CLOCK_SIZE,
        })

    for _ in range(METAL_SHIP_CLOCK_COUNT):
        cx, cy = _metal_ship_clock_spawn_site(layer.width, layer.height)
        _paint_metal_ship_clock(layer, cx, cy)
        stations.append({"cx": cx, "cy": cy, "kind": "metal_ship"})
    return stations


def _build_hhmm_sprite(hhmm):
    """Build a small HH:MM sprite from LED digit tiles."""
    h1, h2, m1, m2 = int(hhmm[0]), int(hhmm[1]), int(hhmm[3]), int(hhmm[4])
    sprite = LED.JoinSprite(LED.DigitSpriteList[h1], LED.DigitSpriteList[h2], 1)
    sprite = LED.JoinSprite(sprite, LED.ColonSprite, 0)
    sprite = LED.JoinSprite(sprite, LED.DigitSpriteList[m1], 0)
    sprite = LED.JoinSprite(sprite, LED.DigitSpriteList[m2], 1)
    return sprite


def _sprite_pixel_grid(sprite):
    """Return a flat on/off grid for static or animated LED sprites."""
    grid = sprite.grid
    if not grid:
        return []
    if isinstance(grid[0], list):
        frame = getattr(sprite, "currentframe", 1)
        frames = getattr(sprite, "frames", len(grid) - 1)
        if frame > frames or frame == 0:
            frame = 1
        return grid[frame]
    return grid


def _paint_time_backdrop_to_layer(layer, left, top, width, height, back_rgb=None):
    """Dark recessed panel stamped into the background layer map."""
    rgb = back_rgb or TIME_BACK_RGB
    lw = layer.width
    lh = layer.height
    for py in range(top, top + height):
        for px in range(left, left + width):
            layer.map[py % lh][px % lw] = rgb


def _paint_time_sprite_to_layer(layer, cx, cy, time_sprite, label_rgb=None, back_rgb=None):
    """Stamp HH:MM into the background layer, centered on a clock station."""
    digits_rgb = label_rgb or TIME_LABEL_RGB
    tw, th = time_sprite.width, time_sprite.height
    sh = int(round(cx - tw / 2))
    sv = int(round(cy - th / 2))
    _paint_time_backdrop_to_layer(
        layer,
        sh - TIME_BACK_PAD_H, sv - TIME_BACK_PAD_V,
        tw + TIME_BACK_PAD_H * 2, th + TIME_BACK_PAD_V * 2,
        back_rgb=back_rgb,
    )
    grid = _sprite_pixel_grid(time_sprite)
    lw = layer.width
    lh = layer.height
    for count in range(tw * th):
        if not grid[count]:
            continue
        y, x = divmod(count, tw)
        layer.map[(sv + y) % lh][(sh + x) % lw] = digits_rgb


def _restore_clock_station(layer, station):
    """Repaint a clock hull so an old minute readout can be replaced cleanly."""
    if station["kind"] == "asteroid":
        _paint_asteroid_to_layer(
            layer, station["cx"], station["cy"],
            station["size"], ASTEROID_CLOCK_COLOR, _clock_asteroid_lumps(),
            dim_factor=1.0,
        )
    elif station["kind"] == "gas_giant":
        _paint_gas_giant_to_layer(
            layer, station["cx"], station["cy"],
            station["radius"], station["colors"], station["ringed"],
        )
    else:
        _paint_metal_ship_clock(layer, station["cx"], station["cy"])


def update_clock_times_on_layer(layer, stations, hhmm):
    """Paint HH:MM onto each clock station in the background layer — once per minute."""
    time_sprite = _build_hhmm_sprite(hhmm)
    for station in stations:
        _restore_clock_station(layer, station)
        _paint_time_sprite_to_layer(
            layer, station["cx"], station["cy"], time_sprite,
            label_rgb=station.get("label_rgb"),
            back_rgb=station.get("back_rgb"),
        )


def _row_indices(oy, layer_height):
    """Precompute wrapped row indices once per frame (Defender-style optimisation)."""
    return tuple((y + oy) % layer_height for y in range(HEIGHT))


def paint_parallax_canvas(
    canvas, far_background, background, middleground, foreground,
    far_h, far_v, bh, by, mh, my, fh, fy,
):
    """
    Fast 4-layer 2D parallax — column-first with cached maps, matching
    LED.PaintFourLayerCanvas structure but with vertical offsets too.
    """
    far_map = far_background.map
    bg_map = background.map
    mg_map = middleground.map
    fg_map = foreground.map
    farwidth = far_background.width
    bwidth = background.width
    mwidth = middleground.width
    fwidth = foreground.width
    farheight = far_background.height
    bheight = background.height
    mheight = middleground.height
    fheight = foreground.height

    far_rows = _row_indices(far_v, farheight)
    bg_rows = _row_indices(by, bheight)
    mg_rows = _row_indices(my, mheight)
    fg_rows = _row_indices(fy, fheight)
    range_w = range(WIDTH)
    range_h = range(HEIGHT)

    for x in range_w:
        far_x = (x + far_h) % farwidth
        bx = (x + bh) % bwidth
        mx = (x + mh) % mwidth
        fx = (x + fh) % fwidth

        for y in range_h:
            rgb = fg_map[fg_rows[y]][fx]
            if rgb == (0, 0, 0):
                rgb = mg_map[mg_rows[y]][mx]
                if rgb == (0, 0, 0):
                    rgb = bg_map[bg_rows[y]][bx]
                    if rgb == (0, 0, 0):
                        rgb = far_map[far_rows[y]][far_x]
            canvas.SetPixel(x, y, *rgb)

    return canvas


def _enemy_alive(sprite):
    return sprite.alive in (True, 1)


def player_world_position(fh, fy):
    """World map coords of the centered player ship."""
    return (SHIP_H + fh) % LAYER_WIDTH, (SHIP_V + fy) % LAYER_HEIGHT


def world_to_screen(wh, wv, fh, fy):
    """Screen coords from the player-centered view — may be negative or past the panel edge."""
    player_wh, player_wv = player_world_position(fh, fy)
    sh = SHIP_H + _toroidal_delta(player_wh, wh, LAYER_WIDTH)
    sv = SHIP_V + _toroidal_delta(player_wv, wv, LAYER_HEIGHT)
    return sh, sv


def _rect_visible_on_screen(sh, sv, width, height):
    """True when any part of a sprite rectangle could appear on the panel."""
    return not (
        sh + width <= 0
        or sv + height <= 0
        or sh >= WIDTH
        or sv >= HEIGHT
    )


def _wrap_world_coord(value, limit):
    return value % limit


def _toroidal_delta(from_coord, to_coord, limit):
    delta = (to_coord - from_coord) % limit
    if delta > limit // 2:
        delta -= limit
    return delta


def _angle_to_direction_8way(angle):
    """Pick the best 8-way sprite heading for a continuous radians angle."""
    dx = math.cos(angle)
    dy = math.sin(angle)
    best_dir = 1
    best_dot = -2.0
    for direction, (ddh, ddv) in ENEMY_DIRECTION_8WAY.items():
        mag = math.hypot(ddh, ddv)
        dot = (dx * ddh + dy * ddv) / mag
        if dot > best_dot:
            best_dot = dot
            best_dir = direction
    return best_dir


def chase_angle_toward_point(from_wh, from_wv, to_wh, to_wv):
    """Continuous heading toward a toroidal world-map target."""
    dh = _toroidal_delta(from_wh, to_wh, LAYER_WIDTH)
    dv = _toroidal_delta(from_wv, to_wv, LAYER_HEIGHT)
    if dh == 0 and dv == 0:
        return None
    return math.atan2(dv, dh)


def chase_angle_toward_player(wh, wv, player_wh, player_wv):
    return chase_angle_toward_point(wh, wv, player_wh, player_wv)


def _physics_scale(rate_per_frame, dt):
    """Convert per-frame constants to elapsed wall-clock time."""
    return rate_per_frame * dt * PHYSICS_FPS


def _enemy_is_large(ship):
    return getattr(ship, "enemy_large", False)


def _enemy_chase_target(ship, player_wh, player_wv, crystals):
    """Prefer nearby crystals over the player when they are closer."""
    center_h = ship.h + ship.width / 2
    center_v = ship.v + ship.height / 2
    nearest_crystal = None
    nearest_crystal_dist = float("inf")
    for crystal in crystals:
        if not crystal.alive:
            continue
        dh = _toroidal_delta(center_h, crystal.h, LAYER_WIDTH)
        dv = _toroidal_delta(center_v, crystal.v, LAYER_HEIGHT)
        dist = math.hypot(dh, dv)
        if dist < nearest_crystal_dist:
            nearest_crystal_dist = dist
            nearest_crystal = crystal
    player_dist = math.hypot(
        _toroidal_delta(center_h, player_wh, LAYER_WIDTH),
        _toroidal_delta(center_v, player_wv, LAYER_HEIGHT),
    )
    if nearest_crystal is not None and nearest_crystal_dist < player_dist * 0.88:
        return nearest_crystal.h, nearest_crystal.v
    return player_wh, player_wv


def update_enemy_inertia(ship, target_wh, target_wv, dt):
    """Blasteroids-style pursuit — turn toward target, thrust, keep momentum."""
    center_h = ship.h + ship.width / 2
    center_v = ship.v + ship.height / 2
    desired_angle = chase_angle_toward_point(center_h, center_v, target_wh, target_wv)
    if _enemy_is_large(ship):
        turn_rate = _physics_scale(LARGE_ENEMY_TURN_RATE, dt)
        thrust_rate = LARGE_ENEMY_THRUST
        max_speed = LARGE_ENEMY_MAX_SPEED
    else:
        turn_rate = _physics_scale(ENEMY_TURN_RATE, dt)
        thrust_rate = ENEMY_THRUST
        max_speed = ENEMY_MAX_SPEED

    if desired_angle is not None:
        angle_diff = _angle_difference(desired_angle, ship.angle)
        ship.angle += max(-turn_rate, min(turn_rate, angle_diff))
        if abs(angle_diff) <= SHIP_THRUST_ALIGN_RAD:
            thrust = _physics_scale(thrust_rate, dt)
            ship.vel_h += math.cos(ship.angle) * thrust
            ship.vel_v += math.sin(ship.angle) * thrust

    speed = math.hypot(ship.vel_h, ship.vel_v)
    if speed > max_speed:
        scale = max_speed / speed
        ship.vel_h *= scale
        ship.vel_v *= scale

    ship.h = _wrap_world_coord(ship.h + ship.vel_h, LAYER_WIDTH)
    ship.v = _wrap_world_coord(ship.v + ship.vel_v, LAYER_HEIGHT)
    ship.direction = _angle_to_direction_8way(ship.angle)


def _random_enemy_world_spawn(player_wh, player_wv, min_dist=40):
    """Scatter enemies across the full map, away from the player."""
    for _ in range(40):
        wh = random.randint(0, LAYER_WIDTH - 1)
        wv = random.randint(0, LAYER_HEIGHT - 1)
        dh = min((wh - player_wh) % LAYER_WIDTH, (player_wh - wh) % LAYER_WIDTH)
        dv = min((wv - player_wv) % LAYER_HEIGHT, (player_wv - wv) % LAYER_HEIGHT)
        if dh + dv > min_dist:
            return wh, wv
    return random.randint(0, LAYER_WIDTH - 1), random.randint(0, LAYER_HEIGHT - 1)


def _make_enemy_ship(sprite_type, player_wh, player_wv, large=False):
    """Create one pursuing UFO from a ShipSprites index."""
    sprite = copy.deepcopy(LED.ShipSprites[sprite_type])
    sprite.name = "LargeEnemyShip" if large else "EnemyShip"
    sprite.alive = True
    sprite.enemy_large = large
    sprite.framerate = random.randint(3, 10) if large else random.randint(2, 8)
    sprite.angle = random.uniform(0, 2 * math.pi)
    sprite.vel_h = 0.0
    sprite.vel_v = 0.0
    sprite.bounce_cooldown = 0
    sprite.chain_parent = None
    sprite.direction = _angle_to_direction_8way(sprite.angle)
    min_dist = 56 if large else 40
    sprite.h, sprite.v = _random_enemy_world_spawn(player_wh, player_wv, min_dist)
    return sprite


def create_enemy_ships(fh=0, fy=0):
    """Spawn small UFOs plus a couple of large animated sprites per wave."""
    player_wh, player_wv = player_world_position(fh, fy)
    enemies = []
    for _ in range(ENEMY_SHIP_COUNT):
        enemies.append(_make_enemy_ship(
            random.choice(ENEMY_SHIP_TYPES), player_wh, player_wv, large=False,
        ))
    large_types = list(LARGE_ENEMY_SHIP_TYPES)
    random.shuffle(large_types)
    for sprite_type in large_types[:LARGE_ENEMY_SHIP_COUNT]:
        enemies.append(_make_enemy_ship(sprite_type, player_wh, player_wv, large=True))
    return enemies


def count_alive_enemy_ships(enemy_ships):
    return sum(1 for ship in enemy_ships if _enemy_alive(ship))


def replenish_enemy_wave_if_empty(enemy_ships, fh, fy):
    """Spawn a fresh UFO wave once the player has destroyed every enemy."""
    if count_alive_enemy_ships(enemy_ships) > 0:
        return False
    enemy_ships[:] = create_enemy_ships(fh, fy)
    return True


def _enemy_is_chained(ship):
    return getattr(ship, "chain_parent", None) is not None


def _enemy_chain_attached_to_player(ship):
    """True when this UFO is part of a daisy chain rooted on the player."""
    if not _enemy_is_chained(ship):
        return False
    node = ship
    while _enemy_is_chained(node):
        parent = node.chain_parent
        if parent is CHAIN_PLAYER:
            return True
        if parent is None:
            break
        node = parent
    return False


def count_enemies_chained_to_player(enemy_ships):
    return sum(
        1 for ship in enemy_ships
        if _enemy_alive(ship) and _enemy_chain_attached_to_player(ship)
    )


def _any_enemy_chain_active(enemy_ships):
    """True when any UFO is part of a daisy chain (including tail links)."""
    return any(
        _enemy_alive(ship) and _enemy_is_chained(ship)
        for ship in enemy_ships
    )


def _enemy_in_player_grapple_range(ship, fh, fy):
    """Close enough to latch onto the player or dangle on the chain."""
    player_wh, player_wv = player_world_position(fh, fy)
    ch, cv = _enemy_center(ship)
    dh = _toroidal_delta(player_wh, ch, LAYER_WIDTH)
    dv = _toroidal_delta(player_wv, cv, LAYER_HEIGHT)
    max_dist = (
        PLAYER_CHAIN_RADIUS
        + _enemy_collision_radius(ship)
        + CHAIN_LINK_GAP
        + CHAIN_UFO_GRAPPLE_EXTRA
    )
    return math.hypot(dh, dv) <= max_dist


def tractor_blocked_by_ufo_chain(enemy_ships, fh, fy):
    """Tractor stays off while any UFO chain is active or UFOs grapple the player."""
    if _any_enemy_chain_active(enemy_ships):
        return True
    if count_enemies_chained_to_player(enemy_ships) > 0:
        return True
    if enemies_touching_ship(enemy_ships, fh, fy):
        return True
    for ship in enemy_ships:
        if _enemy_alive(ship) and _enemy_in_player_grapple_range(ship, fh, fy):
            return True
    return False


def chain_escape_heading(enemy_ships, fh, fy, now, ship_angle):
    """Thrust away from the attached chain with a slow left-right weave."""
    player_wh, player_wv = player_world_position(fh, fy)
    pull_h = 0.0
    pull_v = 0.0
    for ship in enemy_ships:
        if not _enemy_alive(ship) or not _enemy_chain_attached_to_player(ship):
            continue
        ch, cv = _enemy_center(ship)
        pull_h += _toroidal_delta(player_wh, ch, LAYER_WIDTH)
        pull_v += _toroidal_delta(player_wv, cv, LAYER_HEIGHT)

    if pull_h == 0.0 and pull_v == 0.0:
        away_angle = ship_angle
    else:
        away_angle = math.atan2(-pull_v, -pull_h)

    weave = CHAIN_WEAVE_AMPLITUDE * math.sin(now * CHAIN_WEAVE_HZ * 2 * math.pi)
    return (away_angle + weave) % (2 * math.pi)


def chain_asteroid_bait_heading(
    enemy_ships, foreground_asteroids, fh, fy,
    ship_angle, ship_vel_h, ship_vel_v, now,
):
    """
    Hunt the nearest drifting rock so the limp UFO string behind the player
    slams into it and shatters — skim past when close so the tail takes the hit.
    """
    bait_target = find_nearest_asteroid(foreground_asteroids, fh, fy)
    if bait_target is None:
        return (
            chain_escape_heading(enemy_ships, fh, fy, now, ship_angle),
            None,
            float("inf"),
            0.0,
        )

    hunt_closing, hunt_dist = hunt_closing_rate(
        fh, fy, bait_target, ship_vel_h, ship_vel_v,
    )
    if hunt_dist > CHAIN_BAIT_PASS_DIST:
        desired_angle = hunt_intercept_angle(
            fh, fy, bait_target, ship_vel_h, ship_vel_v, max_speed=MAX_SHIP_SPEED,
        )
    else:
        to_rock = angle_toward_world_point(fh, fy, bait_target.h, bait_target.v)
        weave = CHAIN_WEAVE_AMPLITUDE * math.sin(now * CHAIN_WEAVE_HZ * 2 * math.pi)
        desired_angle = (
            to_rock + math.pi * CHAIN_BAIT_PASS_SLIP + weave
        ) % (2 * math.pi)

    if desired_angle is None:
        desired_angle = chain_escape_heading(enemy_ships, fh, fy, now, ship_angle)
    return desired_angle, bait_target, hunt_dist, hunt_closing


def _chain_parent_radius(parent):
    if parent is CHAIN_PLAYER:
        return PLAYER_CHAIN_RADIUS
    return _enemy_collision_radius(parent)


def _chain_slot_distance(parent, ship):
    """Keep chained hulls separated with a visible gap — no overlap."""
    return _chain_parent_radius(parent) + _enemy_collision_radius(ship) + CHAIN_LINK_GAP


def _chain_would_cycle(ship, parent):
    """Prevent a daisy-chain link that would loop back on itself."""
    node = parent
    while node is not None and node is not CHAIN_PLAYER:
        if node is ship:
            return True
        node = getattr(node, "chain_parent", None)
    return False


def _chain_parent_state(parent, fh, fy, ship_angle, ship_vel_h, ship_vel_v):
    if parent is CHAIN_PLAYER:
        return (
            *player_world_position(fh, fy),
            ship_angle,
            ship_vel_h,
            ship_vel_v,
        )
    center_h, center_v = _enemy_center(parent)
    return center_h, center_v, parent.angle, parent.vel_h, parent.vel_v


def _enemy_should_break_for_crystal(ship, crystals, fh, fy):
    """Chained UFOs peel off when a crystal is visible and close enough."""
    center_h, center_v = _enemy_center(ship)
    for crystal in crystals:
        if not crystal.alive or not crystal_on_screen(crystal, fh, fy):
            continue
        dh = _toroidal_delta(center_h, crystal.h, LAYER_WIDTH)
        dv = _toroidal_delta(center_v, crystal.v, LAYER_HEIGHT)
        if math.hypot(dh, dv) <= ENEMY_CRYSTAL_BREAK_DIST:
            return True
    return False


def _separate_chained_pair(a, b):
    """Nudge overlapping chained UFOs apart along the line between their centers."""
    ac_h, ac_v = _enemy_center(a)
    bc_h, bc_v = _enemy_center(b)
    dh = _toroidal_delta(ac_h, bc_h, LAYER_WIDTH)
    dv = _toroidal_delta(ac_v, bc_v, LAYER_HEIGHT)
    dist = math.hypot(dh, dv)
    min_dist = (
        _enemy_collision_radius(a) + _enemy_collision_radius(b) + CHAIN_LINK_GAP
    )
    overlap = min_dist - dist
    if overlap <= 0:
        return False

    if dist < 0.001:
        angle = random.uniform(0, 2 * math.pi)
        nx = math.cos(angle)
        ny = math.sin(angle)
    else:
        nx = dh / dist
        ny = dv / dist

    sep = overlap * 0.52
    a.h = _wrap_world_coord(a.h - nx * sep, LAYER_WIDTH)
    a.v = _wrap_world_coord(a.v - ny * sep, LAYER_HEIGHT)
    b.h = _wrap_world_coord(b.h + nx * sep, LAYER_WIDTH)
    b.v = _wrap_world_coord(b.v + ny * sep, LAYER_HEIGHT)
    return True


def resolve_chained_enemy_spacing(enemy_ships):
    """Push chained UFOs apart if hulls still overlap after slot following."""
    alive = [ship for ship in enemy_ships if _enemy_alive(ship) and _enemy_is_chained(ship)]
    for _ in range(max(1, len(alive))):
        moved_any = False
        for i in range(len(alive)):
            for j in range(i + 1, len(alive)):
                if _enemies_collide(alive[i], alive[j]):
                    if _separate_chained_pair(alive[i], alive[j]):
                        moved_any = True
                        break
            if moved_any:
                break
        if not moved_any:
            break


def update_chained_enemy_follow(ship, fh, fy, dt, ship_angle, ship_vel_h, ship_vel_v):
    """Limp string follow — dragged behind the parent with little independent thrust."""
    parent = ship.chain_parent
    if parent is None:
        return

    p_h, p_v, p_angle, p_vel_h, p_vel_v = _chain_parent_state(
        parent, fh, fy, ship_angle, ship_vel_h, ship_vel_v,
    )
    link_dist = _chain_slot_distance(parent, ship)
    back_dx = -math.cos(p_angle) * link_dist
    back_dy = -math.sin(p_angle) * link_dist
    slot_h = _wrap_world_coord(p_h + back_dx, LAYER_WIDTH)
    slot_v = _wrap_world_coord(p_v + back_dy, LAYER_HEIGHT)

    center_h, center_v = _enemy_center(ship)
    dh = _toroidal_delta(center_h, slot_h, LAYER_WIDTH)
    dv = _toroidal_delta(center_v, slot_v, LAYER_HEIGHT)
    pos_blend = min(1.0, _physics_scale(CHAIN_LIMP_POS_BLEND, dt))
    new_center_h = _wrap_world_coord(center_h + dh * pos_blend, LAYER_WIDTH)
    new_center_v = _wrap_world_coord(center_v + dv * pos_blend, LAYER_HEIGHT)

    ship.h = _wrap_world_coord(new_center_h - ship.width / 2, LAYER_WIDTH)
    ship.v = _wrap_world_coord(new_center_v - ship.height / 2, LAYER_HEIGHT)

    vel_match = CHAIN_LIMP_VEL_MATCH
    correction = _physics_scale(CHAIN_LIMP_CORRECTION, dt)
    ship.vel_h = p_vel_h * vel_match + dh * correction
    ship.vel_v = p_vel_v * vel_match + dv * correction

    ship.angle = p_angle
    ship.direction = _angle_to_direction_8way(ship.angle)


def attach_daisy_chain_links(enemy_ships, fh, fy):
    """Latch free UFOs onto the player or onto UFOs already in the chain."""
    alive = [ship for ship in enemy_ships if _enemy_alive(ship)]
    changed = True
    while changed:
        changed = False
        for ship in enemies_touching_ship(alive, fh, fy):
            if not _enemy_is_chained(ship):
                ship.chain_parent = CHAIN_PLAYER
                ship.vel_h = 0.0
                ship.vel_v = 0.0
                changed = True
        for ship in alive:
            if _enemy_is_chained(ship):
                continue
            for chained in alive:
                if chained is ship or not _enemy_is_chained(chained):
                    continue
                if _chain_would_cycle(ship, chained):
                    continue
                if _enemies_collide(ship, chained):
                    ship.chain_parent = chained
                    ship.vel_h = chained.vel_h
                    ship.vel_v = chained.vel_v
                    changed = True
                    break


def _chained_enemy_update_order(enemies):
    """Update parents before children so the tail drags like a string."""
    chained = [ship for ship in enemies if _enemy_alive(ship) and _enemy_is_chained(ship)]
    ordered = []
    remaining = list(chained)
    while remaining:
        progress = False
        for ship in list(remaining):
            parent = ship.chain_parent
            if parent is CHAIN_PLAYER or parent not in remaining:
                ordered.append(ship)
                remaining.remove(ship)
                progress = True
        if not progress:
            ordered.extend(remaining)
            break
    return ordered


def update_enemy_ships(enemies, fh, fy, dt, crystals, ship_angle, ship_vel_h, ship_vel_v):
    """Pursue crystals or the player; chained UFOs go limp on a string behind their parent."""
    player_wh, player_wv = player_world_position(fh, fy)
    for ship in enemies:
        if not _enemy_alive(ship):
            continue
        if ship.bounce_cooldown > 0:
            ship.bounce_cooldown -= 1
        if _enemy_is_chained(ship) and _enemy_should_break_for_crystal(ship, crystals, fh, fy):
            ship.chain_parent = None

    for ship in enemies:
        if not _enemy_alive(ship) or _enemy_is_chained(ship):
            continue
        target_wh, target_wv = _enemy_chase_target(ship, player_wh, player_wv, crystals)
        update_enemy_inertia(ship, target_wh, target_wv, dt)

    for ship in _chained_enemy_update_order(enemies):
        update_chained_enemy_follow(
            ship, fh, fy, dt, ship_angle, ship_vel_h, ship_vel_v,
        )
    resolve_chained_enemy_spacing(enemies)
    resolve_enemy_collisions(enemies)


def _enemy_center(ship):
    return ship.h + ship.width / 2, ship.v + ship.height / 2


def _enemy_collision_radius(ship):
    return max(ship.width, ship.height) * 0.52


def _enemy_mass(ship):
    return ship.width * ship.height * (1.5 if _enemy_is_large(ship) else 1.0)


def _enemies_collide(a, b):
    """True when two UFOs overlap on the wrapping map."""
    ac_h, ac_v = _enemy_center(a)
    bc_h, bc_v = _enemy_center(b)
    dh = _toroidal_delta(ac_h, bc_h, LAYER_WIDTH)
    dv = _toroidal_delta(ac_v, bc_v, LAYER_HEIGHT)
    touch_dist = _enemy_collision_radius(a) + _enemy_collision_radius(b)
    return math.hypot(dh, dv) < touch_dist


def _bounce_enemy_pair(a, b):
    """Elastic bounce — separate overlapping UFOs and swap momentum along the impact normal."""
    ac_h, ac_v = _enemy_center(a)
    bc_h, bc_v = _enemy_center(b)
    dh = _toroidal_delta(ac_h, bc_h, LAYER_WIDTH)
    dv = _toroidal_delta(ac_v, bc_v, LAYER_HEIGHT)
    dist = math.hypot(dh, dv)
    touch_dist = _enemy_collision_radius(a) + _enemy_collision_radius(b)
    overlap = touch_dist - dist
    if overlap <= 0:
        return False

    if dist < 0.001:
        angle = random.uniform(0, 2 * math.pi)
        nx = math.cos(angle)
        ny = math.sin(angle)
        dist = 0.001
    else:
        nx = dh / dist
        ny = dv / dist

    rel_normal = (a.vel_h - b.vel_h) * nx + (a.vel_v - b.vel_v) * ny
    if rel_normal < 0:
        m1 = _enemy_mass(a)
        m2 = _enemy_mass(b)
        impulse = -(1.0 + BOUNCE_DAMPING) * rel_normal / (1.0 / m1 + 1.0 / m2)
        a.vel_h += impulse * nx / m1
        a.vel_v += impulse * ny / m1
        b.vel_h -= impulse * nx / m2
        b.vel_v -= impulse * ny / m2

        for ship in (a, b):
            if _enemy_is_large(ship):
                max_speed = LARGE_ENEMY_MAX_SPEED
            else:
                max_speed = ENEMY_MAX_SPEED
            speed = math.hypot(ship.vel_h, ship.vel_v)
            if speed > max_speed:
                scale = max_speed / speed
                ship.vel_h *= scale
                ship.vel_v *= scale
            if speed > 0.02:
                ship.angle = math.atan2(ship.vel_v, ship.vel_h)
                ship.direction = _angle_to_direction_8way(ship.angle)

    sep = overlap * 0.51
    a.h = _wrap_world_coord(a.h + nx * sep, LAYER_WIDTH)
    a.v = _wrap_world_coord(a.v + ny * sep, LAYER_HEIGHT)
    b.h = _wrap_world_coord(b.h - nx * sep, LAYER_WIDTH)
    b.v = _wrap_world_coord(b.v - ny * sep, LAYER_HEIGHT)

    a.bounce_cooldown = ENEMY_BOUNCE_COOLDOWN_FRAMES
    b.bounce_cooldown = ENEMY_BOUNCE_COOLDOWN_FRAMES
    return True


def resolve_enemy_collisions(enemy_ships):
    """Bounce UFOs apart when they collide — one pair per pass until stable."""
    alive = [ship for ship in enemy_ships if _enemy_alive(ship)]
    max_passes = max(1, len(alive) * len(alive))
    for _ in range(max_passes):
        bounced_any = False
        for i in range(len(alive)):
            for j in range(i + 1, len(alive)):
                a, b = alive[i], alive[j]
                if (
                    a.bounce_cooldown > 0 or b.bounce_cooldown > 0
                    or _enemy_is_chained(a) or _enemy_is_chained(b)
                ):
                    continue
                if _enemies_collide(a, b) and _bounce_enemy_pair(a, b):
                    bounced_any = True
                    break
            if bounced_any:
                break
        if not bounced_any:
            break


def _enemy_animation_frame(ship):
    frame = ship.currentframe
    if frame > ship.frames or frame == 0:
        frame = 1
    return frame


def _enemy_touches_ship_pixels(ship, fh, fy):
    """Screen-space hit test — matches non-transparent UFO sprite pixels."""
    sh, sv = world_to_screen(ship.h, ship.v, fh, fy)
    sh = int(round(sh))
    sv = int(round(sv))
    frame = _enemy_animation_frame(ship)
    grid = ship.grid[frame]
    for count in range(ship.width * ship.height):
        y, x = divmod(count, ship.width)
        r, g, b = LED.ColorList[grid[count]]
        if r > 0 or g > 0 or b > 0:
            if (sh + x, sv + y) in _SHIP_PIXELS:
                return True
    return False


def enemies_touching_ship(enemy_ships, fh, fy):
    """Return enemy UFOs whose drawn pixels overlap the ship hitbox."""
    hitting = []
    for ship in enemy_ships:
        if _enemy_alive(ship) and _enemy_touches_ship_pixels(ship, fh, fy):
            hitting.append(ship)
    return hitting


def _asteroid_enemy_screen_pixels(asteroid, ship, fh, fy):
    """Screen pixels for a rough foreground rock and UFO overlap test."""
    ash, asv = world_to_screen(asteroid.h, asteroid.v, fh, fy)
    acenter_h = int(round(ash))
    acenter_v = int(round(asv))
    asteroid_pixels = {
        (acenter_h + i, acenter_v + j)
        for i, j, _ in asteroid.sprite_pixels
    }

    sh, sv = world_to_screen(ship.h, ship.v, fh, fy)
    sh = int(round(sh))
    sv = int(round(sv))
    frame = _enemy_animation_frame(ship)
    grid = ship.grid[frame]
    enemy_pixels = []
    for count in range(ship.width * ship.height):
        y, x = divmod(count, ship.width)
        r, g, b = LED.ColorList[grid[count]]
        if r > 0 or g > 0 or b > 0:
            enemy_pixels.append((sh + x, sv + y))
    return asteroid_pixels, enemy_pixels


def _asteroid_touches_enemy_pixels(asteroid, ship, fh, fy):
    """True when a drifting foreground rock overlaps a UFO sprite pixel."""
    asteroid_pixels, enemy_pixels = _asteroid_enemy_screen_pixels(asteroid, ship, fh, fy)
    for px, py in enemy_pixels:
        if (px, py) in asteroid_pixels:
            return True
    return False


def _asteroid_enemy_nearby(asteroid, ship):
    """Cheap toroidal bounds check before the pixel hit test."""
    ec_h, ec_v = _enemy_center(ship)
    dh = _toroidal_delta(asteroid.h, ec_h, LAYER_WIDTH)
    dv = _toroidal_delta(asteroid.v, ec_v, LAYER_HEIGHT)
    touch_dist = asteroid.size * 1.2 + _enemy_collision_radius(ship)
    return math.hypot(dh, dv) < touch_dist


def enemies_hit_by_asteroids(foreground_asteroids, enemy_ships, fh, fy):
    """Return UFOs whose hull pixels touch a moving foreground asteroid."""
    hits = []
    hit_ids = set()
    for asteroid in foreground_asteroids:
        if not asteroid.alive:
            continue
        if math.hypot(asteroid.dx, asteroid.dy) < 0.01:
            continue
        for ship in enemy_ships:
            if not _enemy_alive(ship) or id(ship) in hit_ids:
                continue
            if not _asteroid_enemy_nearby(asteroid, ship):
                continue
            if _asteroid_touches_enemy_pixels(asteroid, ship, fh, fy):
                hits.append(ship)
                hit_ids.add(id(ship))
    return hits


def _release_chain_children(dead_ship, enemy_ships):
    """Promote daisy-chain children when a link is destroyed."""
    new_parent = dead_ship.chain_parent
    for ship in enemy_ships:
        if _enemy_alive(ship) and ship.chain_parent is dead_ship:
            ship.chain_parent = new_parent
            if new_parent is not None and new_parent is not CHAIN_PLAYER:
                ship.vel_h = new_parent.vel_h
                ship.vel_v = new_parent.vel_v


def _enemy_sprite_to_particles(ship):
    """Convert a UFO sprite into colored debris — Defender ConvertSpriteToParticles."""
    particles = []
    frame = _enemy_animation_frame(ship)
    grid = ship.grid[frame]
    large = _enemy_is_large(ship)
    for count in range(ship.width * ship.height):
        y, x = divmod(count, ship.width)
        r, g, b = LED.ColorList[grid[count]]
        if r == 0 and g == 0 and b == 0:
            continue
        r, g, b = _brighten_enemy_rgb(r, g, b, large)
        wh = _wrap_world_coord(ship.h + x, LAYER_WIDTH)
        wv = _wrap_world_coord(ship.v + y, LAYER_HEIGHT)
        vel_h = random.random() * (random.randint(0, 1) * 2 - 1)
        vel_v = random.random() * (random.randint(0, 1) * 2 - 1)
        particles.append(EnemyParticle(wh, wv, r, g, b, vel_h, vel_v))
    return particles


def destroy_enemies_as_particles(hit_enemies, enemy_ships):
    """Shatter rammed UFOs into Defender-style sprite particles.
    Each killed UFO drops exactly one yellow crystal at its center.
    Returns (particles, crystals).
    """
    particles = []
    drop_crystals = []
    for ship in hit_enemies:
        if not _enemy_alive(ship):
            continue
        wh = _wrap_world_coord(ship.h + ship.width / 2, LAYER_WIDTH)
        wv = _wrap_world_coord(ship.v + ship.height / 2, LAYER_HEIGHT)
        # One crystal per UFO, slight scatter so it doesn't sit under debris forever
        ang = random.uniform(0, 2 * math.pi)
        speed = random.uniform(0.06, 0.14)
        drop_crystals.append(Crystal(
            wh, wv,
            dx=math.cos(ang) * speed,
            dy=math.sin(ang) * speed,
        ))
        _release_chain_children(ship, enemy_ships)
        ship.alive = False
        particles.extend(_enemy_sprite_to_particles(ship))
    return particles, drop_crystals


def destroy_enemies(hit_enemies):
    """Blow up rammed UFOs and scatter sparks at their world centers."""
    sparks = []
    for ship in hit_enemies:
        if not _enemy_alive(ship):
            continue
        ship.alive = False
        wh = _wrap_world_coord(ship.h + ship.width / 2, LAYER_WIDTH)
        wv = _wrap_world_coord(ship.v + ship.height / 2, LAYER_HEIGHT)
        spark_count = SPARK_COUNT + 6 if _enemy_is_large(ship) else SPARK_COUNT
        spark_len = 6 if _enemy_is_large(ship) else 4
        for _ in range(spark_count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(0.2, 1.4)
            sparks.append(Spark(wh, wv, angle, speed, spark_len))
    return sparks


def _brighten_enemy_rgb(r, g, b, large=False):
    """Boost UFO sprite colors so aliens read clearly on the parallax field."""
    if r == 0 and g == 0 and b == 0:
        return 0, 0, 0
    brightness = ENEMY_LARGE_BRIGHTNESS if large else ENEMY_BRIGHTNESS
    rgb_floor = ENEMY_LARGE_RGB_FLOOR if large else ENEMY_RGB_FLOOR
    return (
        min(255, max(rgb_floor, int(r * brightness))),
        min(255, max(rgb_floor, int(g * brightness))),
        min(255, max(rgb_floor, int(b * brightness))),
    )


def _paint_enemy_ship_to_canvas(ship, sh, sv, canvas):
    """Draw an animated UFO with boosted brightness."""
    ship.ticks += 1
    if ship.ticks >= ship.framerate:
        ship.currentframe += 1
        ship.ticks = 0
    if ship.currentframe > ship.frames or ship.currentframe == 0:
        ship.currentframe = 1

    grid = ship.grid[ship.currentframe]
    for count in range(ship.width * ship.height):
        y, x = divmod(count, ship.width)
        px = sh + x
        py = sv + y
        if not (0 <= px < WIDTH and 0 <= py < HEIGHT):
            continue
        r, g, b = LED.ColorList[grid[count]]
        if r > 0 or g > 0 or b > 0:
            canvas.SetPixel(px, py, *_brighten_enemy_rgb(r, g, b, _enemy_is_large(ship)))
    return canvas


def draw_enemy_ships(canvas, enemies, fh, fy):
    for ship in enemies:
        if not _enemy_alive(ship):
            continue
        sh, sv = world_to_screen(ship.h, ship.v, fh, fy)
        sh = int(round(sh))
        sv = int(round(sv))
        if not _rect_visible_on_screen(sh, sv, ship.width, ship.height):
            continue
        _paint_enemy_ship_to_canvas(ship, sh, sv, canvas)
    return canvas


def _draw_thrust_flames(canvas, ship_angle, turbo, frame_count):
    """Blasteroids-style exhaust — flickering orange trail behind the engine."""
    back_dx = -int(round(math.cos(ship_angle)))
    back_dy = -int(round(math.sin(ship_angle)))
    if back_dx == 0 and back_dy == 0:
        return

    perp_dx = -int(round(math.sin(ship_angle)))
    perp_dy = int(round(math.cos(ship_angle)))
    trail_len = len(THRUST_FLAME_COLORS) if turbo else 2
    flicker = frame_count % 3

    for i in range(1, trail_len + 1):
        color = THRUST_FLAME_COLORS[min(i - 1, len(THRUST_FLAME_COLORS) - 1)]
        px = SHIP_H + back_dx * i
        py = SHIP_V + back_dy * i
        if 0 <= px < WIDTH and 0 <= py < HEIGHT:
            canvas.SetPixel(px, py, *color)

        if turbo and i <= 2 and flicker:
            for side in (-1, 1):
                sx = px + perp_dx * side
                sy = py + perp_dy * side
                if 0 <= sx < WIDTH and 0 <= sy < HEIGHT:
                    canvas.SetPixel(sx, sy, *THRUST_FLAME_COLORS[1])


def ship_nose_screen_position(ship_angle):
    """Screen coords of the one-pixel nose tip on the centered ship."""
    nose_dx = int(round(math.cos(ship_angle)))
    nose_dy = int(round(math.sin(ship_angle)))
    return SHIP_H + nose_dx, SHIP_V + nose_dy


def asteroid_screen_center(asteroid, fh, fy):
    """Rounded screen position of a foreground asteroid's world center."""
    sh, sv = world_to_screen(asteroid.h, asteroid.v, fh, fy)
    return int(round(sh)), int(round(sv))


def asteroid_on_screen(asteroid, fh, fy):
    """True when any part of the asteroid could be visible on the panel."""
    if asteroid is None or not asteroid.alive:
        return False
    center_h, center_v = asteroid_screen_center(asteroid, fh, fy)
    margin = max(2, asteroid.size + 1)
    return (
        -margin <= center_h < WIDTH + margin
        and -margin <= center_v < HEIGHT + margin
    )


def can_tractor_attach(fh, fy, asteroid):
    """Lock the beam when a breakable rock is on-screen and within tractor range."""
    if not asteroid_on_screen(asteroid, fh, fy):
        return False
    return distance_to_world_point(fh, fy, asteroid.h, asteroid.v) <= TRACTOR_MAX_WORLD_DIST


def tractor_on_cooldown(now, tractor_cooldown_until):
    return now < tractor_cooldown_until


def sever_tractor_beam(now):
    """Drop the lock and block re-attach for TRACTOR_COOLDOWN_SEC."""
    return None, now + TRACTOR_COOLDOWN_SEC


def update_tractor_lock(
    fh, fy, hunt_target, tractor_target, now, tractor_cooldown_until,
    ufo_chain_blocks=False,
):
    """Keep an active lock while valid; attach to the hunt target when it becomes visible."""
    if ufo_chain_blocks or tractor_on_cooldown(now, tractor_cooldown_until):
        return None
    if tractor_target is not None and tractor_target.alive and can_tractor_attach(fh, fy, tractor_target):
        return tractor_target
    if can_tractor_attach(fh, fy, hunt_target):
        return hunt_target
    return None


def apply_tractor_beam_physics(
    tractor_target, fh, fy, ship_vel_h, ship_vel_v, dt,
    max_ship_speed=TRACTOR_MAX_SHIP_SPEED,
):
    """
    Damp asteroid momentum and slowly draw ship and rock together while matched.
    Returns updated ship velocity.
    """
    player_wh, player_wv = player_world_position(fh, fy)
    dh = _toroidal_delta(player_wh, tractor_target.h, LAYER_WIDTH)
    dv = _toroidal_delta(player_wv, tractor_target.v, LAYER_HEIGHT)
    dist = math.hypot(dh, dv)

    damp = 1.0 - _physics_scale(TRACTOR_MOMENTUM_DAMP, dt)
    tractor_target.dx *= damp
    tractor_target.dy *= damp

    if dist > 0.5:
        pull = _physics_scale(TRACTOR_PULL_RATE, dt)
        tractor_target.h = _wrap_world_coord(tractor_target.h - dh * pull, LAYER_WIDTH)
        tractor_target.v = _wrap_world_coord(tractor_target.v - dv * pull, LAYER_HEIGHT)
        norm_dh = dh / dist
        norm_dv = dv / dist
        ship_vel_h += norm_dh * pull * TRACTOR_SHIP_CLOSE_RATE
        ship_vel_v += norm_dv * pull * TRACTOR_SHIP_CLOSE_RATE

    match = _physics_scale(TRACTOR_SHIP_MATCH_RATE, dt)
    ship_vel_h += (tractor_target.dx - ship_vel_h) * match
    ship_vel_v += (tractor_target.dy - ship_vel_v) * match

    speed = math.hypot(ship_vel_h, ship_vel_v)
    if speed > max_ship_speed:
        scale = max_ship_speed / speed
        ship_vel_h *= scale
        ship_vel_v *= scale
    return ship_vel_h, ship_vel_v


def _draw_line_pixel(canvas, x0, y0, x1, y1, rgb):
    """One-pixel-wide Bresenham line."""
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    x, y = x0, y0
    while True:
        if 0 <= x < WIDTH and 0 <= y < HEIGHT:
            canvas.SetPixel(x, y, *rgb)
        if x == x1 and y == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x += sx
        if e2 < dx:
            err += dx
            y += sy


def draw_tractor_beam(canvas, ship_angle, tractor_target, fh, fy):
    """Green beam from the ship nose to the locked asteroid center."""
    if tractor_target is None or not tractor_target.alive:
        return canvas
    nx, ny = ship_nose_screen_position(ship_angle)
    ax, ay = asteroid_screen_center(tractor_target, fh, fy)
    _draw_line_pixel(canvas, nx, ny, ax, ay, TRACTOR_BEAM_RGB)
    return canvas


def draw_tiny_ship(canvas, ship_angle, thrusting=False, turbo=False, frame_count=0):
    """Draw a 3-pixel-tall ship fixed at the center of the screen."""
    if thrusting:
        _draw_thrust_flames(canvas, ship_angle, turbo, frame_count)

    canvas.SetPixel(SHIP_H, SHIP_V, *SHIP_CORE_RGB)

    nose_dx = int(round(math.cos(ship_angle)))
    nose_dy = int(round(math.sin(ship_angle)))
    nx = SHIP_H + nose_dx
    ny = SHIP_V + nose_dy
    if 0 <= nx < WIDTH and 0 <= ny < HEIGHT:
        canvas.SetPixel(nx, ny, *SHIP_NOSE_RGB)

    for dx, dy in ((-1, 0), (1, 0), (0, 1)):
        if dx == nose_dx and dy == nose_dy:
            continue
        bx = SHIP_H + dx
        by = SHIP_V + dy
        if 0 <= bx < WIDTH and 0 <= by < HEIGHT:
            canvas.SetPixel(bx, by, *SHIP_BODY_RGB)


def heading_to_direction(heading):
    direction = int(round(heading))
    while direction < 1:
        direction += DIRECTION_COUNT
    while direction > DIRECTION_COUNT:
        direction -= DIRECTION_COUNT
    return direction


def shortest_heading_delta(current, target):
    """Signed shortest turn on the 16-point compass (-8..8)."""
    cur = (current - 1) % DIRECTION_COUNT
    tgt = (target - 1) % DIRECTION_COUNT
    diff = (tgt - cur) % DIRECTION_COUNT
    if diff > DIRECTION_COUNT // 2:
        diff -= DIRECTION_COUNT
    return diff


def advance_heading_toward(heading, target, turn_rate):
    delta = shortest_heading_delta(heading, target)
    if abs(delta) <= turn_rate:
        return float(target)
    return heading + turn_rate * (1.0 if delta > 0 else -1.0)


def direction_toward_world_point(from_wh, from_wv, to_wh, to_wv):
    """16-way heading that best intercepts a toroidal world-map target."""
    dh = _toroidal_delta(from_wh, to_wh, LAYER_WIDTH)
    dv = _toroidal_delta(from_wv, to_wv, LAYER_HEIGHT)
    if dh == 0 and dv == 0:
        return float(random.randint(1, DIRECTION_COUNT))

    best_dir = 1
    best_score = -float("inf")
    for direction, (ddh, ddv) in DIRECTION_DELTAS.items():
        mag = math.hypot(ddh, ddv)
        score = (dh * ddh + dv * ddv) / mag
        if score > best_score:
            best_score = score
            best_dir = direction
    return float(best_dir)


def find_nearest_asteroid(foreground_asteroids, fh, fy):
    """Return the closest alive foreground asteroid to the centered ship."""
    player_wh, player_wv = player_world_position(fh, fy)
    nearest = None
    nearest_dist_sq = float("inf")

    for asteroid in foreground_asteroids:
        if not asteroid.alive:
            continue
        dh = _toroidal_delta(player_wh, asteroid.h, LAYER_WIDTH)
        dv = _toroidal_delta(player_wv, asteroid.v, LAYER_HEIGHT)
        dist_sq = dh * dh + dv * dv
        if dist_sq < nearest_dist_sq:
            nearest_dist_sq = dist_sq
            nearest = asteroid

    return nearest


def refresh_hunt_target(foreground_asteroids, fh, fy, hunt_target):
    """
    Keep the locked asteroid unless it dies or a much closer rock appears.
    Avoids re-targeting every frame, which causes endless orbit loops.
    """
    nearest = find_nearest_asteroid(foreground_asteroids, fh, fy)
    if nearest is None:
        return None
    if hunt_target is None or not hunt_target.alive:
        return nearest

    current_dist = hunt_distance_to_target(fh, fy, hunt_target)
    nearest_dist = hunt_distance_to_target(fh, fy, nearest)
    if nearest_dist < current_dist * HUNT_TARGET_REACQUIRE_RATIO:
        return nearest
    return hunt_target


def _angle_difference(target_angle, current_angle):
    """Signed shortest turn between two radians (-pi..pi)."""
    return (target_angle - current_angle + math.pi) % (2 * math.pi) - math.pi


def _relative_hunt_vector(fh, fy, hunt_target):
    """Toroidal offset and relative velocity from ship to a locked asteroid."""
    player_wh, player_wv = player_world_position(fh, fy)
    dh = _toroidal_delta(player_wh, hunt_target.h, LAYER_WIDTH)
    dv = _toroidal_delta(player_wv, hunt_target.v, LAYER_HEIGHT)
    rel_vh = hunt_target.dx
    rel_vv = hunt_target.dy
    return dh, dv, rel_vh, rel_vv


def hunt_closing_rate(fh, fy, hunt_target, ship_vel_h, ship_vel_v):
    """
    Positive when distance to the target is shrinking.
    Negative values mean the ship is orbiting or falling behind.
    """
    if hunt_target is None or not hunt_target.alive:
        return 0.0, float("inf")
    dh, dv, rel_vh, rel_vv = _relative_hunt_vector(fh, fy, hunt_target)
    rel_vh -= ship_vel_h
    rel_vv -= ship_vel_v
    dist = math.hypot(dh, dv)
    if dist < 0.5:
        return 0.0, dist
    return -(dh * rel_vh + dv * rel_vv) / dist, dist


def _solve_intercept_time(rel_dh, rel_dv, rel_vh, rel_vv, pursuer_speed):
    """Solve |r + v*t| = speed*t for the earliest positive intercept time."""
    a = rel_vh * rel_vh + rel_vv * rel_vv - pursuer_speed * pursuer_speed
    b = 2.0 * (rel_dh * rel_vh + rel_dv * rel_vv)
    c = rel_dh * rel_dh + rel_dv * rel_dv
    if abs(a) < 1e-6:
        if abs(b) < 1e-6:
            return None
        t = -c / b
        return t if t > HUNT_INTERCEPT_MIN_TIME else None

    disc = b * b - 4.0 * a * c
    if disc < 0:
        return None

    sqrt_disc = math.sqrt(disc)
    candidates = []
    for sign in (-1.0, 1.0):
        t = (-b + sign * sqrt_disc) / (2.0 * a)
        if HUNT_INTERCEPT_MIN_TIME <= t <= HUNT_INTERCEPT_MAX_TIME:
            candidates.append(t)
    return min(candidates) if candidates else None


def hunt_intercept_angle(fh, fy, hunt_target, ship_vel_h, ship_vel_v, max_speed=MAX_SHIP_SPEED):
    """
    Aim at a true intercept point using relative motion, not a fixed lead time.
    Falls back to proportional lead when a direct intercept is impossible.
    """
    if hunt_target is None or not hunt_target.alive:
        return None

    dh, dv, asteroid_vh, asteroid_vv = _relative_hunt_vector(fh, fy, hunt_target)
    rel_vh = asteroid_vh - ship_vel_h
    rel_vv = asteroid_vv - ship_vel_v
    dist = math.hypot(dh, dv)
    if dist < 0.5:
        return math.atan2(dv, dh)

    current_speed = math.hypot(ship_vel_h, ship_vel_v)
    pursuer_speed = max(
        current_speed,
        max_speed * HUNT_MIN_PURSUIT_SPEED,
        FOREGROUND_ASTEROID_MAX_SPEED * 2.0,
    )

    lead_t = _solve_intercept_time(dh, dv, rel_vh, rel_vv, pursuer_speed)
    if lead_t is None:
        lead_t = min(
            HUNT_INTERCEPT_MAX_TIME,
            max(HUNT_LEAD_SEC, dist / max(pursuer_speed, 0.1)),
        )

    aim_dh = dh + rel_vh * lead_t
    aim_dv = dv + rel_vv * lead_t
    if math.hypot(aim_dh, aim_dv) < 0.5:
        aim_dh, aim_dv = dh, dv
    return math.atan2(aim_dv, aim_dh)


def hunt_angle_for_target(fh, fy, hunt_target, ship_vel_h=0.0, ship_vel_v=0.0, lead_sec=HUNT_LEAD_SEC):
    """Radians toward the locked asteroid — uses intercept math when velocity is known."""
    if hunt_target is None or not hunt_target.alive:
        return None
    if ship_vel_h != 0.0 or ship_vel_v != 0.0:
        return hunt_intercept_angle(fh, fy, hunt_target, ship_vel_h, ship_vel_v)
    player_wh, player_wv = player_world_position(fh, fy)
    target_h = (hunt_target.h + hunt_target.dx * lead_sec) % LAYER_WIDTH
    target_v = (hunt_target.v + hunt_target.dy * lead_sec) % LAYER_HEIGHT
    dh = _toroidal_delta(player_wh, target_h, LAYER_WIDTH)
    dv = _toroidal_delta(player_wv, target_v, LAYER_HEIGHT)
    return math.atan2(dv, dh)


def hunt_distance_to_target(fh, fy, hunt_target):
    """Toroidal distance from the ship to the locked asteroid."""
    if hunt_target is None or not hunt_target.alive:
        return float("inf")
    return distance_to_world_point(fh, fy, hunt_target.h, hunt_target.v)


def distance_to_world_point(fh, fy, wh, wv):
    """Toroidal distance from the ship to a world-map point."""
    player_wh, player_wv = player_world_position(fh, fy)
    dh = _toroidal_delta(player_wh, wh, LAYER_WIDTH)
    dv = _toroidal_delta(player_wv, wv, LAYER_HEIGHT)
    return math.hypot(dh, dv)


def angle_toward_world_point(fh, fy, wh, wv):
    """Radians toward a world-map point across the wrapping map."""
    player_wh, player_wv = player_world_position(fh, fy)
    dh = _toroidal_delta(player_wh, wh, LAYER_WIDTH)
    dv = _toroidal_delta(player_wv, wv, LAYER_HEIGHT)
    return math.atan2(dv, dh)


def nearest_gas_giant_index(fh, fy, gas_giants):
    """Pick the closest gas giant as the initial cruise destination."""
    best_index = 0
    best_dist = float("inf")
    for i, planet in enumerate(gas_giants):
        dist = distance_to_world_point(fh, fy, planet["cx"], planet["cy"])
        if dist < best_dist:
            best_dist = dist
            best_index = i
    return best_index


def advance_cruise_target(fh, fy, gas_giants, cruise_index):
    """Hop to the next gas giant once the current one has been reached."""
    if not gas_giants:
        return cruise_index
    planet = gas_giants[cruise_index]
    dist = distance_to_world_point(fh, fy, planet["cx"], planet["cy"])
    if dist <= planet["radius"] + GAS_GIANT_ARRIVAL_PAD:
        return (cruise_index + 1) % len(gas_giants)
    return cruise_index


def rocks_nearby(fh, fy, hunt_target):
    """True when a breakable rock is close enough to resume the hunt."""
    return hunt_distance_to_target(fh, fy, hunt_target) <= ROCK_NEARBY_DIST


def update_turbo_state(
    fh, fy, hunt_target, ship_vel_h, ship_vel_v, last_dist, stall_frames, closing_rate=0.0,
):
    """
    Engage turbo when close enough to ram, or when orbit-stall is detected
    (distance stops closing while the ship still has speed).
    """
    dist = hunt_distance_to_target(fh, fy, hunt_target)
    if dist == float("inf"):
        return False, dist, 0

    speed = math.hypot(ship_vel_h, ship_vel_v)
    if last_dist != float("inf") and speed > 0.35:
        if last_dist - dist < TURBO_ORBIT_CLOSE_MIN:
            stall_frames += 1
        else:
            stall_frames = 0

    orbit_stall = (
        closing_rate < -0.02
        and dist <= HUNT_ORBIT_CLOSE_DIST
        and speed > 0.25
    )
    wants_turbo = (
        dist <= TURBO_CLOSE_DIST
        or stall_frames >= TURBO_ORBIT_STALL_FRAMES
        or orbit_stall
    )
    return wants_turbo, dist, stall_frames


def apply_turbo_timing(wants_turbo, now, turbo_active_until, turbo_cooldown_until):
    """Fire turbo for five seconds, then enforce a two-second recharge."""
    if now < turbo_active_until:
        return True, turbo_active_until, turbo_cooldown_until

    if turbo_active_until > 0:
        turbo_active_until = 0.0
        turbo_cooldown_until = now + TURBO_COOLDOWN_SEC

    if now < turbo_cooldown_until:
        return False, turbo_active_until, turbo_cooldown_until

    if wants_turbo:
        turbo_active_until = now + TURBO_DURATION_SEC
        return True, turbo_active_until, turbo_cooldown_until

    return False, turbo_active_until, turbo_cooldown_until


def cancel_turbo_burst(now, turbo_active_until, turbo_cooldown_until):
    """End an in-progress burst and start the cooldown (e.g. after a bounce)."""
    if turbo_active_until > now:
        turbo_cooldown_until = now + TURBO_COOLDOWN_SEC
    return 0.0, turbo_cooldown_until


def update_ship_inertia(
    ship_angle, ship_vel_h, ship_vel_v, desired_angle, recoiling,
    turbo=False, cruise=False, crystal=False, hunt=False, tractor=False,
    hunt_dist=float("inf"), hunt_closing=0.0,
    dt=1 / 60,
):
    """
    Blasteroids-style flight — constant turn rate, thrust only when nose is aligned,
    otherwise coast on existing momentum (no drag in vacuum).
    """
    if cruise and not turbo:
        base_turn = CRUISE_TURN_RATE
        base_thrust = CRUISE_THRUST
        align_limit = SHIP_THRUST_ALIGN_RAD * 1.15
        max_speed = CRUISE_MAX_SPEED
    elif crystal:
        base_turn = SHIP_HUNT_TURN_RATE
        base_thrust = SHIP_TURBO_THRUST
        align_limit = SHIP_TURBO_ALIGN_RAD
        max_speed = MAX_SHIP_SPEED
    elif turbo:
        base_turn = SHIP_TURBO_TURN_RATE
        base_thrust = SHIP_TURBO_THRUST
        align_limit = SHIP_TURBO_ALIGN_RAD
        max_speed = SHIP_TURBO_MAX_SPEED
    elif hunt:
        base_turn = SHIP_HUNT_TURN_RATE
        base_thrust = SHIP_THRUST
        align_limit = SHIP_HUNT_ALIGN_RAD
        if hunt_dist <= SHIP_HUNT_CLOSE_DIST:
            align_limit = SHIP_HUNT_CLOSE_ALIGN_RAD
        if hunt_closing < -0.02 and hunt_dist <= HUNT_ORBIT_CLOSE_DIST:
            align_limit = max(align_limit, SHIP_TURBO_ALIGN_RAD)
        max_speed = TRACTOR_MAX_SHIP_SPEED if tractor else MAX_SHIP_SPEED
    else:
        base_turn = SHIP_TURN_RATE
        base_thrust = SHIP_THRUST
        align_limit = SHIP_THRUST_ALIGN_RAD
        max_speed = MAX_SHIP_SPEED

    turn_rate = _physics_scale(base_turn, dt)
    thrusting = False

    if desired_angle is not None:
        angle_diff = _angle_difference(desired_angle, ship_angle)
        ship_angle += max(-turn_rate, min(turn_rate, angle_diff))

    if not recoiling and desired_angle is not None:
        angle_err = abs(_angle_difference(desired_angle, ship_angle))
        if angle_err <= align_limit:
            thrusting = True
            thrust = _physics_scale(base_thrust, dt)
            if hunt and hunt_dist <= SHIP_HUNT_CLOSE_DIST and angle_err > SHIP_THRUST_ALIGN_RAD:
                thrust *= max(0.45, 1.0 - (angle_err - SHIP_THRUST_ALIGN_RAD))
            ship_vel_h += math.cos(ship_angle) * thrust
            ship_vel_v += math.sin(ship_angle) * thrust
    speed = math.hypot(ship_vel_h, ship_vel_v)
    if speed > max_speed:
        scale = max_speed / speed
        ship_vel_h *= scale
        ship_vel_v *= scale

    return ship_angle, ship_vel_h, ship_vel_v, thrusting


def bounce_ship_momentum(ship_angle, ship_vel_h, ship_vel_v):
    """Reflect off a rock — retain inertia but punch away from the impact."""
    speed = math.hypot(ship_vel_h, ship_vel_v) * SHIP_BOUNCE_DAMPING
    speed = min(MAX_SHIP_SPEED, speed)
    ship_angle = (ship_angle + math.pi) % (2 * math.pi)
    return ship_angle, math.cos(ship_angle) * speed, math.sin(ship_angle) * speed


def _obstacle_at_screen(obstacle_map, fh, fy, sx, sy, fwidth, fheight):
    return obstacle_map[(sy + fy) % fheight][(sx + fh) % fwidth]


def ship_obstacle_hits(obstacle_map, fh, fy, fwidth, fheight, sx=SHIP_H, sy=SHIP_V):
    for dx, dy in SHIP_HITBOX:
        if _obstacle_at_screen(obstacle_map, fh, fy, sx + dx, sy + dy, fwidth, fheight):
            return True
    return False


def lookahead_hits(direction, obstacle_map, fh, fy, fwidth, fheight):
    """Weighted count of foreground asteroid pixels ahead (closer = worse)."""
    dh, dv = DIRECTION_DELTAS[direction]
    hits = 0
    for dist in range(1, LOOKAHEAD + 1):
        weight = (LOOKAHEAD + 1 - dist) * 4
        for dx, dy in SHIP_HITBOX:
            if _obstacle_at_screen(
                obstacle_map, fh, fy,
                SHIP_H + dx + dh * dist, SHIP_V + dy + dv * dist,
                fwidth, fheight,
            ):
                hits += weight
    return hits


def choose_avoidance_heading(heading, obstacle_map, fh, fy, fwidth, fheight):
    """Pick the clearest heading, preferring small turns from current course."""
    current = heading_to_direction(heading)
    best_heading = float(current)
    best_cost = float("inf")

    for candidate in range(1, DIRECTION_COUNT + 1):
        hits = lookahead_hits(candidate, obstacle_map, fh, fy, fwidth, fheight)
        turn_cost = abs(shortest_heading_delta(current, candidate)) * 2.0
        cost = hits * 8 + turn_cost
        if cost < best_cost:
            best_cost = cost
            best_heading = float(candidate)

    return best_heading


def bounce_from_collision(heading, velocity, obstacle_map, fh, fy, fwidth, fheight):
    """
    Bounce off a foreground asteroid: head roughly opposite, pick the clearest
    nearby escape heading, and bleed speed.
    """
    bounced = heading + 8.0
    while bounced > DIRECTION_COUNT:
        bounced -= DIRECTION_COUNT
    while bounced < 1.0:
        bounced += DIRECTION_COUNT

    base = heading_to_direction(bounced)
    best_heading = float(base)
    best_hits = float("inf")
    for offset in (0, 1, -1, 2, -2, 3, -3):
        candidate = heading_to_direction(base + offset)
        hits = lookahead_hits(candidate, obstacle_map, fh, fy, fwidth, fheight)
        if hits < best_hits:
            best_hits = hits
            best_heading = float(candidate)

    return best_heading, max(MIN_VELOCITY, velocity * BOUNCE_DAMPING)


def predict_foreground_collision(obstacle_map, fh, fy, carry_fh, carry_fy, heading, velocity, count, fwidth, fheight):
    """Return True if the next foreground scroll tick would overlap an asteroid."""
    if count % FRATE != 0:
        return False

    direction = heading_to_direction(heading)
    dh, dv = DIRECTION_DELTAS[direction]
    step = velocity * SCROLL_STEP
    next_carry_fh = carry_fh + dh * step
    next_carry_fy = carry_fy + dv * step
    next_fh = (fh + int(next_carry_fh)) % LAYER_WIDTH
    next_fy = (fy + int(next_carry_fy)) % LAYER_HEIGHT
    return ship_obstacle_hits(obstacle_map, next_fh, next_fy, fwidth, fheight)


def update_velocity(velocity, heading, target_heading):
    alignment = 1.0 - min(1.0, abs(shortest_heading_delta(heading, target_heading)) / 4.0)
    velocity += ACCELERATION * alignment
    if abs(shortest_heading_delta(heading, target_heading)) > 2:
        velocity *= TURN_DRAG
    return max(MIN_VELOCITY, min(MAX_VELOCITY, velocity))


def scroll_offsets_momentum(
    far_h, far_v, bh, by, mh, my, fh, fy,
    carry_far_h, carry_far_v, carry_bh, carry_by, carry_mh, carry_my, carry_fh, carry_fy,
    ship_vel_h, ship_vel_v, count,
):
    """Advance layer offsets from the ship's inertia velocity vector."""
    # World scroll: smooth every frame so free-floating rocks and enemies don't judder.
    carry_fh += ship_vel_h / FRATE
    carry_fy += ship_vel_v / FRATE
    di_h = int(carry_fh)
    di_v = int(carry_fy)
    carry_fh -= di_h
    carry_fy -= di_v
    fh = (fh + di_h) % LAYER_WIDTH
    fy = (fy + di_v) % LAYER_HEIGHT

    carry_mh += ship_vel_h / MRATE
    carry_my += ship_vel_v / MRATE
    di_h = int(carry_mh)
    di_v = int(carry_my)
    carry_mh -= di_h
    carry_my -= di_v
    mh = (mh + di_h) % LAYER_WIDTH
    my = (my + di_v) % LAYER_HEIGHT

    carry_bh += ship_vel_h / BRATE
    carry_by += ship_vel_v / BRATE
    di_h = int(carry_bh)
    di_v = int(carry_by)
    carry_bh -= di_h
    carry_by -= di_v
    bh = (bh + di_h) % LAYER_WIDTH
    by = (by + di_v) % LAYER_HEIGHT

    carry_far_h += ship_vel_h / FAR_RATE
    carry_far_v += ship_vel_v / FAR_RATE
    di_h = int(carry_far_h)
    di_v = int(carry_far_v)
    carry_far_h -= di_h
    carry_far_v -= di_v
    far_h = (far_h + di_h) % LAYER_WIDTH
    far_v = (far_v + di_v) % LAYER_HEIGHT

    return (
        far_h, far_v, bh, by, mh, my, fh, fy,
        carry_far_h, carry_far_v, carry_bh, carry_by, carry_mh, carry_my, carry_fh, carry_fy,
    )


def _pump_load_starfield(canvas, starfield, panel_w, panel_h, state, StopEvent=None):
    """Keep the intro starfield scrolling during heavy world generation."""
    if starfield is None or canvas is None:
        return canvas
    if StopEvent is not None:
        try:
            if StopEvent.is_set():
                return canvas
        except Exception:
            pass
    now = time.time()
    last = state.get("last", now)
    dt = max(0.001, min(0.05, now - last))
    state["last"] = now
    state["t"] = state.get("t", 0.0) + dt
    try:
        starfield.update(dt)
        canvas.Fill(0, 0, 0)
        starfield.draw(canvas, state["t"], fade=1.0)
        canvas = LED.TheMatrix.SwapOnVSync(canvas)
    except Exception:
        pass
    return canvas


def PlaySpaceExplorer(Duration=10000, StopEvent=None, load_starfield=None, load_canvas=None):
    """Main flight loop — ship centered, world scrolls in sixteen directions.
    If load_starfield/load_canvas are provided (from the title intro), the
    starfield keeps animating while layers and entities are built so there is
    no black freeze between title and gameplay.
    """
    panel_w = int(getattr(LED, "HatWidth", WIDTH) or WIDTH)
    panel_h = int(getattr(LED, "HatHeight", HEIGHT) or HEIGHT)
    canvas = load_canvas
    if canvas is None:
        try:
            canvas = LED.TheMatrix.CreateFrameCanvas()
        except Exception:
            canvas = LED.Canvas
    starfield = load_starfield
    if starfield is None and load_starfield is not False:
        # No intro: still show a short loading starfield during world gen
        starfield = SeIntroStarField(panel_w, panel_h, seed=91)
    pump_state = {"last": time.time(), "t": 0.0}

    def _progress():
        nonlocal canvas
        canvas = _pump_load_starfield(
            canvas, starfield, panel_w, panel_h, pump_state, StopEvent=StopEvent,
        )

    # Pump once so the matrix never sits on a frozen/black frame
    _progress()
    far_background, background, middleground, foreground, clock_stations, gas_giants = (
        create_star_layers(progress_cb=_progress)
    )
    _progress()
    clock_minute = int(time.time()) // 60
    display_time = time.strftime("%H:%M", time.localtime())
    update_clock_times_on_layer(background, clock_stations, display_time)
    _progress()
    foreground_asteroids = create_all_foreground_asteroids(fh=0, fy=0)
    _progress()
    enemy_ships = create_enemy_ships(fh=0, fy=0)
    _progress()
    mother_ship = create_mother_ship(fh=0, fy=0)
    _progress()
    sparks = []
    enemy_particles = []
    crystals = []
    crystal_missiles = []
    crystal_score = 0
    last_crystal_fire_time = 0.0
    mother_respawn_at = 0.0

    try:
        canvas.Fill(0, 0, 0)
    except Exception:
        pass

    far_h = far_v = bh = by = mh = my = fh = fy = 0
    carry_far_h = carry_far_v = 0.0
    carry_bh = carry_by = carry_mh = carry_my = carry_fh = carry_fy = 0.0
    ship_angle = random.uniform(0, 2 * math.pi)
    ship_vel_h = 0.0
    ship_vel_v = 0.0
    count = 0
    hunt_target = find_nearest_asteroid(foreground_asteroids, fh, fy)
    tractor_target = None
    tractor_cooldown_until = 0.0
    bounce_cooldown = 0
    last_hunt_dist = float("inf")
    orbit_stall_frames = 0
    turbo_boost = False
    turbo_active_until = 0.0
    turbo_cooldown_until = 0.0
    chain_escape_was_active = False
    ufo_chain_engaged = False
    thrusting = False
    cruise_index = nearest_gas_giant_index(0, 0, gas_giants) if gas_giants else 0
    start_time = time.time()
    last_physics_time = start_time

    print(f"[SpaceExplorer] {LAYER_WIDTH}x{LAYER_HEIGHT} maps on {WIDTH}x{HEIGHT} panel (no frame sleep)")

    try:
        while True:
            if StopEvent and StopEvent.is_set():
                print("[SpaceExplorer] StopEvent received — exiting")
                break

            now = time.time()
            dt = min(max(now - last_physics_time, 0.001), 0.05)
            last_physics_time = now
            elapsed_min = (now - start_time) / 60.0
            if Duration and elapsed_min >= Duration:
                print(f"[SpaceExplorer] Duration reached ({Duration} min)")
                break

            count += 1
            if bounce_cooldown > 0:
                bounce_cooldown -= 1

            replenish_foreground_asteroids_if_empty(foreground_asteroids, fh, fy)
            hunt_target = refresh_hunt_target(foreground_asteroids, fh, fy, hunt_target)

            recoiling = bounce_cooldown > 0
            ufo_chain_active = (
                ufo_chain_engaged
                or tractor_blocked_by_ufo_chain(enemy_ships, fh, fy)
            )
            chain_escape = not recoiling and ufo_chain_active
            if (
                bounce_cooldown > 0
                or tractor_on_cooldown(now, tractor_cooldown_until)
                or ufo_chain_active
            ):
                tractor_target = None
            else:
                tractor_target = update_tractor_lock(
                    fh, fy, hunt_target, tractor_target, now, tractor_cooldown_until,
                    ufo_chain_blocks=False,
                )

            tractor_locked = tractor_target is not None and not ufo_chain_active
            crystal_target, crystal_dist = find_nearest_crystal(crystals, fh, fy)
            crystal_hunt = not recoiling and not chain_escape and crystal_target is not None
            # With a crystal bank of 10+, hunt the mother UFO and fire crystals as missiles
            mother_hunt = (
                not recoiling
                and not chain_escape
                and mother_ship is not None
                and mother_ship.alive
                and crystal_score >= MOTHER_CRYSTAL_HUNT_MIN
            )
            cruise_mode = (
                not recoiling
                and not chain_escape
                and not mother_hunt
                and not crystal_hunt
                and not tractor_locked
                and gas_giants
                and not rocks_nearby(fh, fy, hunt_target)
            )
            hunt_closing = 0.0
            hunt_dist = float("inf")
            chain_bait_target = None

            if recoiling:
                desired_angle = (ship_angle + math.pi) % (2 * math.pi)
                turbo_active_until, turbo_cooldown_until = cancel_turbo_burst(
                    now, turbo_active_until, turbo_cooldown_until,
                )
                turbo_boost = False
                orbit_stall_frames = 0
            elif chain_escape:
                (
                    desired_angle, chain_bait_target, hunt_dist, hunt_closing,
                ) = chain_asteroid_bait_heading(
                    enemy_ships, foreground_asteroids, fh, fy,
                    ship_angle, ship_vel_h, ship_vel_v, now,
                )
                new_chain_latch = not chain_escape_was_active
                turbo_boost, turbo_active_until, turbo_cooldown_until = apply_turbo_timing(
                    new_chain_latch or chain_bait_target is not None,
                    now, turbo_active_until, turbo_cooldown_until,
                )
                orbit_stall_frames = 0
            elif mother_hunt:
                desired_angle = hunt_intercept_angle(
                    fh, fy, mother_ship, ship_vel_h, ship_vel_v,
                    max_speed=SHIP_TURBO_MAX_SPEED,
                )
                turbo_boost = True
                orbit_stall_frames = 0
                # Spend crystals as homing missiles only while the mother UFO is on screen
                mother_on_screen = False
                if mother_ship is not None and mother_ship.alive:
                    msh, msv = world_to_screen(mother_ship.h, mother_ship.v, fh, fy)
                    margin = mother_ship.radius + 1
                    mother_on_screen = (
                        -margin <= msh < WIDTH + margin
                        and -margin <= msv < HEIGHT + margin
                    )
                if (
                    mother_on_screen
                    and crystal_score > 0
                    and (now - last_crystal_fire_time) >= CRYSTAL_MISSILE_FIRE_INTERVAL
                ):
                    fire_crystal_missile(
                        crystal_missiles, fh, fy, ship_angle, mother_ship,
                    )
                    crystal_score -= 1
                    last_crystal_fire_time = now
            elif crystal_hunt:
                desired_angle = hunt_intercept_angle(
                    fh, fy, crystal_target, ship_vel_h, ship_vel_v, max_speed=MAX_SHIP_SPEED,
                )
                turbo_boost = False
                orbit_stall_frames = 0
            elif tractor_locked:
                hunt_closing, hunt_dist = hunt_closing_rate(
                    fh, fy, tractor_target, ship_vel_h, ship_vel_v,
                )
                desired_angle = angle_toward_world_point(
                    fh, fy, tractor_target.h, tractor_target.v,
                )
                turbo_boost = False
                orbit_stall_frames = 0
            elif cruise_mode:
                cruise_index = advance_cruise_target(fh, fy, gas_giants, cruise_index)
                planet = gas_giants[cruise_index]
                desired_angle = angle_toward_world_point(
                    fh, fy, planet["cx"], planet["cy"],
                )
                turbo_boost = False
                orbit_stall_frames = 0
            else:
                hunt_closing, hunt_dist = hunt_closing_rate(
                    fh, fy, hunt_target, ship_vel_h, ship_vel_v,
                )
                desired_angle = hunt_angle_for_target(
                    fh, fy, hunt_target, ship_vel_h, ship_vel_v,
                )
                wants_turbo, last_hunt_dist, orbit_stall_frames = update_turbo_state(
                    fh, fy, hunt_target, ship_vel_h, ship_vel_v,
                    last_hunt_dist, orbit_stall_frames, hunt_closing,
                )
                turbo_boost, turbo_active_until, turbo_cooldown_until = apply_turbo_timing(
                    wants_turbo, now, turbo_active_until, turbo_cooldown_until,
                )

            chain_escape_was_active = chain_escape

            chain_asteroid_bait = chain_escape and chain_bait_target is not None

            ship_angle, ship_vel_h, ship_vel_v, thrusting = update_ship_inertia(
                ship_angle, ship_vel_h, ship_vel_v, desired_angle, recoiling,
                turbo_boost, cruise_mode and not chain_escape,
                crystal=crystal_hunt and not mother_hunt,
                hunt=(
                    not recoiling
                    and not cruise_mode
                    and not crystal_hunt
                    and not mother_hunt
                    and (chain_asteroid_bait or not chain_escape)
                ),
                tractor=tractor_locked and not chain_escape and not mother_hunt,
                hunt_dist=hunt_dist,
                hunt_closing=hunt_closing,
                dt=dt,
            )

            if tractor_locked and not chain_escape:
                ship_vel_h, ship_vel_v = apply_tractor_beam_physics(
                    tractor_target, fh, fy, ship_vel_h, ship_vel_v, dt,
                )

            scroll_before = (
                far_h, far_v, bh, by, mh, my, fh, fy,
                carry_far_h, carry_far_v, carry_bh, carry_by, carry_mh, carry_my, carry_fh, carry_fy,
            )
            (
                far_h, far_v, bh, by, mh, my, fh, fy,
                carry_far_h, carry_far_v, carry_bh, carry_by, carry_mh, carry_my, carry_fh, carry_fy,
            ) = scroll_offsets_momentum(
                far_h, far_v, bh, by, mh, my, fh, fy,
                carry_far_h, carry_far_v, carry_bh, carry_by, carry_mh, carry_my, carry_fh, carry_fy,
                ship_vel_h, ship_vel_v, count,
            )

            update_foreground_asteroids(foreground_asteroids, now)

            hit_asteroids = asteroids_touching_ship(foreground_asteroids, fh, fy)
            if hit_asteroids:
                (
                    far_h, far_v, bh, by, mh, my, fh, fy,
                    carry_far_h, carry_far_v, carry_bh, carry_by, carry_mh, carry_my, carry_fh, carry_fy,
                ) = scroll_before
                broken_asteroids = apply_ship_hits_to_asteroids(hit_asteroids)
                if broken_asteroids:
                    new_sparks, new_crystals = split_asteroids(
                        foreground_asteroids, broken_asteroids, now, ship_angle,
                    )
                    sparks.extend(new_sparks)
                    crystals.extend(new_crystals)
                    replenish_foreground_asteroids_if_empty(foreground_asteroids, fh, fy)
                    hunt_target = refresh_hunt_target(foreground_asteroids, fh, fy, None)
                tractor_target, tractor_cooldown_until = sever_tractor_beam(now)
                ship_angle, ship_vel_h, ship_vel_v = bounce_ship_momentum(
                    ship_angle, ship_vel_h, ship_vel_v,
                )
                bounce_cooldown = BOUNCE_COOLDOWN_FRAMES
                last_hunt_dist = float("inf")
                orbit_stall_frames = 0
            update_crystals(crystals)
            crystal_score += collect_crystals_for_ship(crystals, fh, fy)

            # Mother UFO float + crystal-missile combat
            if mother_ship is not None and mother_ship.alive:
                mother_ship.update(dt)
            elif mother_ship is not None and not mother_ship.alive:
                if mother_respawn_at <= 0:
                    mother_respawn_at = now + MOTHER_RESPAWN_SEC
                elif now >= mother_respawn_at:
                    mother_ship = create_mother_ship(fh, fy)
                    mother_respawn_at = 0.0
                    print("[SpaceExplorer] Mother UFO re-entered the system")

            missile_hits = update_crystal_missiles(crystal_missiles, mother_ship, dt)
            if missile_hits and mother_ship is not None and mother_ship.alive:
                for _ in range(missile_hits):
                    if mother_ship.take_hit():
                        print(
                            "[SpaceExplorer] Mother UFO destroyed after {} hits!".format(
                                mother_ship.hits,
                            )
                        )
                        boom_p, boom_s = mother_fantastic_explosion(mother_ship)
                        enemy_particles.extend(boom_p)
                        sparks.extend(boom_s)
                        mother_ship.alive = False
                        mother_respawn_at = now + MOTHER_RESPAWN_SEC
                        break
                    else:
                        # Small hit spark on impact
                        sparks.append(Spark(
                            mother_ship.h, mother_ship.v,
                            random.uniform(0, 2 * math.pi),
                            speed=random.uniform(0.8, 1.8),
                            length=random.randint(3, 5),
                        ))

            update_enemy_ships(
                enemy_ships, fh, fy, dt, crystals,
                ship_angle, ship_vel_h, ship_vel_v,
            )
            attach_daisy_chain_links(enemy_ships, fh, fy)
            ufo_chain_engaged = _any_enemy_chain_active(enemy_ships)
            ufo_chain_active = (
                ufo_chain_engaged
                or tractor_blocked_by_ufo_chain(enemy_ships, fh, fy)
            )
            if ufo_chain_active:
                tractor_target = None
                tractor_locked = False
            asteroid_hit_enemies = enemies_hit_by_asteroids(
                foreground_asteroids, enemy_ships, fh, fy,
            )
            if asteroid_hit_enemies:
                boom_parts, ufo_crystals = destroy_enemies_as_particles(
                    asteroid_hit_enemies, enemy_ships,
                )
                enemy_particles.extend(boom_parts)
                crystals.extend(ufo_crystals)
            collect_crystals_for_enemies(crystals, enemy_ships, fh, fy)
            prune_dead_crystals(crystals)

            replenish_enemy_wave_if_empty(enemy_ships, fh, fy)

            update_sparks(sparks)
            update_enemy_particles(enemy_particles, dt)

            minute_epoch = int(time.time()) // 60
            if minute_epoch != clock_minute:
                clock_minute = minute_epoch
                display_time = time.strftime("%H:%M", time.localtime())
                update_clock_times_on_layer(background, clock_stations, display_time)

            canvas = paint_parallax_canvas(
                canvas, far_background, background, middleground, foreground,
                far_h, far_v, bh, by, mh, my, fh, fy,
            )
            draw_foreground_asteroids(canvas, foreground_asteroids, fh, fy)
            draw_crystals(canvas, crystals, fh, fy)
            if tractor_target is not None and not ufo_chain_active:
                draw_tractor_beam(canvas, ship_angle, tractor_target, fh, fy)
            draw_enemy_ships(canvas, enemy_ships, fh, fy)
            if mother_ship is not None and mother_ship.alive:
                mother_ship.draw(canvas, fh, fy, now)
            for m in crystal_missiles:
                m.draw(canvas, fh, fy)
            draw_sparks(canvas, sparks, fh, fy)
            draw_enemy_particles(canvas, enemy_particles, fh, fy)
            draw_tiny_ship(
                canvas, ship_angle,
                thrusting=thrusting,
                turbo=turbo_boost,
                frame_count=count,
            )

            canvas = LED.TheMatrix.SwapOnVSync(canvas)

    except KeyboardInterrupt:
        print("[SpaceExplorer] Interrupted")

    LED.ClearBuffers()
    try:
        LED.TheMatrix.SwapOnVSync(LED.Canvas)
    except Exception:
        pass


#------------------------------------------------------------------------------
# Title intro — "SPACE EXPLORER" swirls in blue, then slams into place
#------------------------------------------------------------------------------
SE_TITLE_LINE1 = "SPACE"
SE_TITLE_LINE2 = "EXPLORER"
SE_TITLE_ZOOM = 1
SE_TITLE_GAP = 1
SE_TITLE_LINE_GAP = 2
# Shades of blue (dark → bright) cycled across letters
SE_BLUE_SHADES = (
    (15, 35, 100),
    (20, 55, 140),
    (30, 80, 180),
    (40, 110, 210),
    (55, 140, 235),
    (80, 170, 255),
    (110, 195, 255),
    (150, 220, 255),
    (40, 90, 200),
    (25, 60, 160),
    (60, 130, 240),
    (90, 160, 250),
    (35, 100, 220),
)
SE_SHADOW_SCALE = 0.28
SE_ORBIT_COUNT = 2.5           # full revolutions before slam
SE_ORBIT_OMEGA = 0.55          # base rad/s (was 2.55 — much slower swirl)
SE_ORBIT_RADIUS = 11.0         # base orbit radius (px)
SE_SLAM_SPEED = 11.0
SE_SLAM_EPS = 1.0
SE_SLAM_STAGGER = 0.045
SE_FADE_SECONDS = 0.55         # fade title+stars to black, then game starts immediately
SE_INTRO_MAX_SECONDS = 45.0    # room for slower orbits


def _se_stop(StopEvent):
    try:
        return StopEvent is not None and StopEvent.is_set()
    except Exception:
        return False


def _se_letter_sprite(char):
    ch = char.upper()
    if not ("A" <= ch <= "Z"):
        return None
    idx = ord(ch) - ord("A")
    try:
        return LED.TrimSprite(copy.deepcopy(LED.AlphaSpriteList[idx]))
    except Exception:
        return None


def _se_sprite_pixels(sprite, zoom, rgb, shadow_rgb):
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


def _se_blue_for_index(i):
    return SE_BLUE_SHADES[i % len(SE_BLUE_SHADES)]


def _se_shadow_for_rgb(rgb):
    return tuple(max(0, int(c * SE_SHADOW_SCALE)) for c in rgb)


class SeTitleLetter(object):
    """Letter that orbits the screen center, then slams to its rest seat."""

    def __init__(
        self, char, pixels, shadow_pixels, width, height,
        rest_x, rest_y, orbit_phase, orbit_radius, orbit_omega,
    ):
        self.char = char
        self.pixels = pixels
        self.shadow_pixels = shadow_pixels
        self.width = width
        self.height = height
        self.rest_x = float(rest_x)
        self.rest_y = float(rest_y)
        self.orbit_phase = float(orbit_phase)
        self.orbit_radius = float(orbit_radius)
        self.orbit_omega = float(orbit_omega)
        self.angle = float(orbit_phase)
        self.x = float(rest_x)
        self.y = float(rest_y)
        self.visible = True
        self.settled = False
        self.slam_delay = 0.0
        self.slam_started = False

    def update_orbit(self, step, cx, cy, aspect):
        self.angle += self.orbit_omega * step
        # Elliptical path so the swirl fills 64×32 nicely
        self.x = cx - self.width * 0.5 + math.cos(self.angle) * self.orbit_radius
        self.y = cy - self.height * 0.5 + math.sin(self.angle) * self.orbit_radius * aspect

    def prepare_slam(self, index):
        self.slam_delay = index * SE_SLAM_STAGGER
        self.slam_started = False
        self.settled = False
        self.visible = True

    def update_slam(self, step, elapsed):
        if self.settled:
            self.x = self.rest_x
            self.y = self.rest_y
            return
        if elapsed < self.slam_delay:
            return
        self.slam_started = True
        dx = self.rest_x - self.x
        dy = self.rest_y - self.y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist <= SE_SLAM_EPS:
            self.x = self.rest_x
            self.y = self.rest_y
            self.settled = True
            return
        speed = SE_SLAM_SPEED
        self.x += (dx / dist) * speed * step
        self.y += (dy / dist) * speed * step
        # Snap if we crossed rest
        if abs(self.x - self.rest_x) < SE_SLAM_EPS and abs(self.y - self.rest_y) < SE_SLAM_EPS:
            self.x = self.rest_x
            self.y = self.rest_y
            self.settled = True

    def force_settle(self):
        self.x = self.rest_x
        self.y = self.rest_y
        self.settled = True
        self.visible = True

    def draw(self, canvas, panel_w, panel_h, fade=1.0):
        if not self.visible:
            return
        fade = max(0.0, min(1.0, float(fade)))
        if fade <= 0.001:
            return
        sx = int(round(self.x))
        sy = int(round(self.y))
        set_px = canvas.SetPixel
        for dx, dy, rgb in self.shadow_pixels:
            px, py = sx + dx, sy + dy
            if 0 <= px < panel_w and 0 <= py < panel_h:
                set_px(
                    px, py,
                    int(rgb[0] * fade), int(rgb[1] * fade), int(rgb[2] * fade),
                )
        for dx, dy, rgb in self.pixels:
            px, py = sx + dx, sy + dy
            if 0 <= px < panel_w and 0 <= py < panel_h:
                set_px(
                    px, py,
                    int(rgb[0] * fade), int(rgb[1] * fade), int(rgb[2] * fade),
                )


def _build_se_title_letters(panel_w, panel_h):
    lines = [SE_TITLE_LINE1, SE_TITLE_LINE2]
    line_specs = []
    max_h = 0
    shade_i = 0
    for line in lines:
        specs = []
        for char in line:
            if char == " ":
                continue
            sprite = _se_letter_sprite(char)
            if sprite is None:
                continue
            rgb = _se_blue_for_index(shade_i)
            shade_i += 1
            shadow = _se_shadow_for_rgb(rgb)
            pixels, shadow_pixels, lw, lh = _se_sprite_pixels(
                sprite, SE_TITLE_ZOOM, rgb, shadow,
            )
            specs.append((char, pixels, shadow_pixels, lw, lh))
            if lh > max_h:
                max_h = lh
        line_specs.append(specs)

    if not any(line_specs):
        return []

    total_h = max_h * len(line_specs) + SE_TITLE_LINE_GAP * max(0, len(line_specs) - 1)
    top_y = max(0, (panel_h - total_h) // 2)

    letters = []
    letter_index = 0
    total_letters = sum(len(s) for s in line_specs)
    for line_i, specs in enumerate(line_specs):
        if not specs:
            continue
        total_w = sum(s[3] for s in specs) + SE_TITLE_GAP * max(0, len(specs) - 1)
        x_cursor = max(0, (panel_w - total_w) // 2)
        rest_y = top_y + line_i * (max_h + SE_TITLE_LINE_GAP)
        for char, pixels, shadow_pixels, lw, lh in specs:
            # Spread on a ring with slight radius / speed variation
            phase = (letter_index / max(1, total_letters)) * 2.0 * math.pi
            radius = SE_ORBIT_RADIUS + (letter_index % 4) * 1.8 + (line_i * 1.2)
            omega = SE_ORBIT_OMEGA * (0.88 + 0.06 * (letter_index % 5))
            # Outer letters orbit slightly opposite for a swirl feel
            if letter_index % 2 == 1:
                omega = -omega * 0.92
            letters.append(SeTitleLetter(
                char, pixels, shadow_pixels, lw, lh,
                x_cursor, rest_y + (max_h - lh),
                orbit_phase=phase,
                orbit_radius=radius,
                orbit_omega=omega,
            ))
            x_cursor += lw + SE_TITLE_GAP
            letter_index += 1
    return letters


class SeIntroStarField(object):
    """
    Fixed multi-layer star positions scrolled with continuous float offsets
    (same idea as SpaceExplorer parallax — no per-frame re-roll, no jitter).
    """

    def __init__(self, panel_w, panel_h, seed=42):
        self.panel_w = int(panel_w)
        self.panel_h = int(panel_h)
        rng = random.Random(seed)
        # Far / mid / near — staggered drift like FAR/BRATE/MRATE (px/sec)
        # (count, base_bright_range, speed_h, speed_v, blue_boost)
        specs = (
            (30, (18, 55),  1.8, 0.28, 18),   # far — slow
            (24, (30, 95),  3.6, 0.55, 28),   # mid
            (16, (50, 135), 6.0, 0.95, 40),   # near — a bit faster
        )
        self.layers = []
        for count, (b0, b1), sh, sv, blue in specs:
            stars = []
            for _ in range(count):
                # Fixed home positions on the panel; scroll wraps smoothly
                x = rng.uniform(0, self.panel_w)
                y = rng.uniform(0, self.panel_h)
                bright = rng.randint(b0, b1)
                phase = rng.uniform(0, 2.0 * math.pi)
                pulse = rng.uniform(0.25, 0.55)  # gentle sine pulse rad/s
                stars.append((x, y, bright, phase, pulse, blue))
            self.layers.append({
                "stars": stars,
                "off_h": 0.0,
                "off_v": 0.0,
                "speed_h": sh,
                "speed_v": sv,
            })

    def update(self, dt):
        """Advance scroll offsets smoothly (dt in seconds)."""
        dt = max(0.0, min(0.05, float(dt)))
        pw = float(self.panel_w)
        ph = float(self.panel_h)
        for layer in self.layers:
            layer["off_h"] = (layer["off_h"] + layer["speed_h"] * dt) % pw
            layer["off_v"] = (layer["off_v"] + layer["speed_v"] * dt) % ph

    def draw(self, canvas, t_sec, fade=1.0):
        """Paint blue-tinted stars with smooth brightness pulse."""
        fade = max(0.0, min(1.0, float(fade)))
        if fade <= 0.001:
            return
        set_px = canvas.SetPixel
        pw = self.panel_w
        ph = self.panel_h
        for layer in self.layers:
            oh = layer["off_h"]
            ov = layer["off_v"]
            for x, y, bright, phase, pulse, blue in layer["stars"]:
                # Continuous wrap; quantize only when addressing pixels
                sx = (x + oh) % pw
                sy = (y + ov) % ph
                px = int(sx) % pw
                py = int(sy) % ph
                # Smooth pulse 0.85–1.0 of base (never hard on/off flicker)
                pulse_amt = 0.85 + 0.15 * (0.5 + 0.5 * math.sin(t_sec * pulse + phase))
                b = max(8, min(180, int(bright * pulse_amt * fade)))
                r = max(0, b * 2 // 5)
                g = max(0, b * 3 // 5)
                bb = max(0, min(255, b + int((blue // 3) * fade)))
                set_px(px, py, r, g, bb)


def _draw_se_title_frame(canvas, letters, panel_w, panel_h, starfield=None, t_sec=0.0, fade=1.0):
    canvas.Fill(0, 0, 0)
    if starfield is not None:
        starfield.draw(canvas, t_sec, fade=fade)
    for letter in letters:
        letter.draw(canvas, panel_w, panel_h, fade=fade)
    return LED.TheMatrix.SwapOnVSync(canvas)


def PlaySpaceExplorerTitleIntro(StopEvent=None):
    """
    SPACE / EXPLORER in blue shades: swirl around screen center for a few
    orbits, then slam into a centered two-line title (RallyDot-style motion).
    Starfield behind letters scrolls smoothly (parallax-style), no jitter.
    """
    panel_w = int(getattr(LED, "HatWidth", WIDTH) or WIDTH)
    panel_h = int(getattr(LED, "HatHeight", HEIGHT) or HEIGHT)
    letters = _build_se_title_letters(panel_w, panel_h)
    try:
        canvas = LED.TheMatrix.CreateFrameCanvas()
    except Exception:
        canvas = LED.Canvas
    starfield = SeIntroStarField(panel_w, panel_h, seed=77)

    if not letters:
        print("[SpaceExplorer] Title intro skipped (no letter sprites)")
        return starfield, canvas

    if _se_stop(StopEvent):
        print("[SpaceExplorer] Title intro skipped (StopEvent)")
        return starfield, canvas

    print("[SpaceExplorer] Title intro — blue swirl then slam")

    cx = panel_w * 0.5
    cy = panel_h * 0.5
    # Flatten orbit vertically for the wide panel
    aspect = max(0.45, min(0.75, (panel_h / float(panel_w)) * 1.6))

    start = time.time()
    last = start
    phase = "orbit"  # → slam → fade → game
    slam_start = None
    fade_start = None
    fade = 1.0
    # Track orbit progress via |omega| * time on first letter
    orbit_progress = 0.0

    try:
        while True:
            if _se_stop(StopEvent):
                break
            now = time.time()
            elapsed = now - start
            if elapsed >= SE_INTRO_MAX_SECONDS and phase != "fade":
                for L in letters:
                    L.force_settle()
                # Fade letters quickly if we hit the cap mid-title
                phase = "fade"
                fade_start = now

            dt = max(0.001, now - last)
            last = now
            step = min(3.0, dt * 30.0)
            # Real-time seconds for smooth star scroll (not tick-scaled step)
            starfield.update(dt)

            if phase == "orbit":
                for L in letters:
                    L.update_orbit(step, cx, cy, aspect)
                # Average absolute angular advance
                avg_omega = sum(abs(L.orbit_omega) for L in letters) / max(1, len(letters))
                orbit_progress += avg_omega * step
                if orbit_progress >= SE_ORBIT_COUNT * 2.0 * math.pi:
                    phase = "slam"
                    slam_start = now
                    for i, L in enumerate(letters):
                        L.prepare_slam(i)
                    print("[SpaceExplorer] Title intro — slam")

            elif phase == "slam":
                slam_elapsed = now - slam_start
                for L in letters:
                    L.update_slam(step, slam_elapsed)
                if all(L.settled for L in letters):
                    # Fade letters only; starfield stays full for seamless load cover
                    phase = "fade"
                    fade_start = now
                    print("[SpaceExplorer] Title intro — fade letters (stars continue)")

            elif phase == "fade":
                for L in letters:
                    L.force_settle()
                t_fade = (now - fade_start) / max(0.05, SE_FADE_SECONDS)
                letter_fade = max(0.0, 1.0 - t_fade)
                fade = letter_fade  # used for letters in draw path below
                if letter_fade <= 0.0:
                    # Leave starfield running — world gen will keep pumping it
                    break

            try:
                # During letter fade: stars stay at full brightness (fade only letters)
                if phase == "fade":
                    canvas.Fill(0, 0, 0)
                    starfield.draw(canvas, elapsed, fade=1.0)
                    for letter in letters:
                        letter.draw(canvas, panel_w, panel_h, fade=fade)
                    canvas = LED.TheMatrix.SwapOnVSync(canvas)
                else:
                    canvas = _draw_se_title_frame(
                        canvas, letters, panel_w, panel_h,
                        starfield=starfield, t_sec=elapsed, fade=1.0,
                    )
            except Exception:
                try:
                    LED.ClearBigLED()
                    for L in letters:
                        L.draw(LED.Canvas, panel_w, panel_h, fade=fade)
                    LED.TheMatrix.SwapOnVSync(LED.Canvas)
                except Exception:
                    pass

    except KeyboardInterrupt:
        pass

    # Hand starfield + canvas to gameplay so load stays animated (no black gap)
    return starfield, canvas


def LaunchSpaceExplorer(Duration=10000, ShowIntro=True, StopEvent=None):
    load_starfield = None
    load_canvas = None
    if ShowIntro:
        try:
            load_starfield, load_canvas = PlaySpaceExplorerTitleIntro(StopEvent=StopEvent)
        except Exception as e:
            import traceback
            print("[SpaceExplorer] title intro failed:", e)
            traceback.print_exc()
            load_starfield, load_canvas = None, None

    PlaySpaceExplorer(
        Duration=Duration,
        StopEvent=StopEvent,
        load_starfield=load_starfield,
        load_canvas=load_canvas,
    )


if __name__ == "__main__":
    try:
        LaunchSpaceExplorer(Duration=100000, ShowIntro=True, StopEvent=None)
    except KeyboardInterrupt:
        print("Exiting SpaceExplorer.")