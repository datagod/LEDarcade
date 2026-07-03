#!/usr/bin/env python
#------------------------------------------------------------------------------
#  SKYFALL — Falling asteroids and a bottom-patrol shooter
#
#  Based on SpaceExplorer asteroid lump sprites.  A 3-pixel-tall ship patrols the
#  bottom of the screen, auto-fires upward, and splits rocks on impact.
#------------------------------------------------------------------------------

import copy
import math
import random
import time

import LEDarcade as LED

# Panel size is resolved after LED.Initialize() in LaunchSkyfall.
WIDTH = LED.HatWidth
HEIGHT = LED.HatHeight

TARGET_FPS = 30.0
FRAME_DT = 1.0 / TARGET_FPS
SIM_REFERENCE_FPS = 30.0
SIM_REFERENCE_DT = 1.0 / SIM_REFERENCE_FPS
MAX_SIM_DT = 1.0 / 12.0

SHIP_HEIGHT = 2
SHIP_WIDTH = 3
SHIP_SPEED = 1.27
SHIP_RGB = (90, 180, 255)
SHIP_NOSE_RGB = (220, 240, 255)
# Upward triangle: 1 pixel nose, 3 pixels on the bottom row.
SHIP_SHAPE = (
    (0, 1, 0),
    (1, 1, 1),
)

ASTEROID_COLLIDE_SCALE = 0.95
ASTEROID_BOUNCE_COOLDOWN = 3

BULLET_SPEED = 2.99
BULLET_RGB = (255, 255, 255)
BULLET_STREAK_LEN = 4
MAX_ACTIVE_SHOTS = 2
FIRE_INTERVAL = 0.14
HUNT_SPEED = 0.71
LOOT_INTERCEPT_MAX_FRAMES = 40
SHIP_LOOKAHEAD_FRAMES = 24
SHIP_DANGER_DISTANCE = 8.0
SHIP_URGENT_DANGER = 4.5
SHIP_DODGE_SPEED = 1.01
SHIP_STEER_DEADBAND = 1.25
SHIP_HUNT_SMOOTH = 0.18
SHIP_MOVE_HOLD_BIAS = 2.8
SHIP_REVERSE_PENALTY = 4.0
SHIP_LANE_CLEARANCE = 3.0
SHIP_SURVIVAL_DANGER = 10.0
SHIP_LOOT_DANGER_LIMIT = 18.0
SHIP_EDGE_TRAP_DISTANCE = 4.0
SHIP_LANE_SAMPLE_STEP = 1.5
SHIP_RESPAWN_DURATION = 1.4
SHIP_EXPLOSION_SPARK_COUNT = 28
SHIP_EXPLOSION_DEBRIS_COUNT = 16

ASTEROID_SPAWN_INTERVAL = 1.1
ASTEROID_SPAWN_ABOVE = 10
ASTEROID_SPEED_MIN = 0.52
ASTEROID_SPEED_MAX = 1.21
ASTEROID_ANGLE_SPREAD = 0.85
ASTEROID_SIZE_RANGE = (2, 7)
MAX_ASTEROIDS = 18

ROCK_SPLIT_COUNT = 2
MIN_ASTEROID_SPLIT_SIZE = 3
SPLIT_FLY_APART = (0.25, 0.46)
SPLIT_PARENT_MOMENTUM = 0.40
SPLIT_PERP_SPREAD_RAD = 0.85
SPLIT_SPAWN_OFFSET = 1.6

# Small (0–7), medium (15–18), large (19–24), wide (25) — skip satellite slots 8–14.
ENEMY_SHIP_TYPES = tuple(range(8)) + tuple(range(15, 26))
ENEMY_SPAWN_INTERVAL = 3.8
MAX_ENEMIES = 4
ENEMY_SPEED_MIN = 0.40
ENEMY_SPEED_MAX = 0.83
ENEMY_BRIGHTNESS = 1.85
ENEMY_RGB_FLOOR = 52

ASTEROID_LIGHTING_CONTRAST = 1.0
ASTEROID_COLORS = (
    (210, 195, 175),
    (200, 210, 255),
    (138, 138, 145),
)
RED_ROCK_COLOR = (230, 50, 40)
RED_ROCK_CHANCE = 0.24
RED_ROCK_CRYSTAL_CHANCE = 0.55
RED_ROCK_SHOOT_BONUS = 18.0
BLUE_ROCK_SHOOT_BONUS = 17.0
BLUE_ROCK_COLOR = (55, 120, 230)
BLUE_ROCK_CHANCE = 0.22
BLUE_ROCK_GEM_CHANCE = 0.55
LOOT_MAX_PER_BREAK = 2
CRYSTAL_RGB = (255, 255, 0)
GEM_RGB = (30, 255, 90)
LOOT_PARENT_MOMENTUM = 0.55
LOOT_BURST_MIN = 0.32
LOOT_BURST_MAX = 0.75
LOOT_BURST_SPREAD = 0.75
LOOT_MAX_SPEED = 1.51
LOOT_GRAVITY = 0.040
LOOT_FALL_MIN = 0.51
LOOT_BOUNCE_DAMPING = 0.78
LOOT_BOUNCE_COOLDOWN = 2
LOOT_HUNT_SPEED = 0.83
CRYSTAL_POWER_COST = 5
GEM_POWER_COST = 5
SHOTGUN_BULLET_COUNT = 5
SHOTGUN_SPREAD = 0.32
SHOTGUN_DURATION = 5.0
SHOTGUN_FIRE_INTERVAL = 0.18
LIGHTNING_MIN_TARGETS = 6
LIGHTNING_DANGER_DISTANCE = 5.0
SPARK_STREAM_DURATION = 1.2
SPARK_STREAM_EMIT_FRAMES = 36
SPARK_STREAM_SPARKS_PER_BURST = 3
SPARK_STREAM_SPREAD = 1.35
SPARK_STREAM_SPEED_MIN = 3.22
SPARK_STREAM_SPEED_MAX = 5.98
HOT_SPARK_TRAIL_LEN = 5
HOT_SPARK_MAX_AGE = 90

SPARK_COUNT = 8
TINY_ROCK_SPARK_COUNT = 12
SPARK_TRAIL_LENGTH = 5
SPARK_COLOR = (255, 200, 100)

ENEMY_PARTICLE_GRAVITY = 0.021
DEBRIS_SPEED_MIN = 0.23
DEBRIS_SPEED_MAX = 1.38
EXPLOSION_SPARK_SPEED_MIN = 0.40
EXPLOSION_SPARK_SPEED_MAX = 1.27
SHIP_EXPLOSION_SPARK_SPEED_MIN = 1.03
SHIP_EXPLOSION_SPARK_SPEED_MAX = 3.22
SHIP_EXPLOSION_SPARK_BURST_MIN = 1.61
SHIP_EXPLOSION_SPARK_BURST_MAX = 4.60
SHIP_DEBRIS_SPEED_XY = 2.07
SHIP_DEBRIS_SPEED_Y = 2.88
ENEMY_PARTICLE_LIFESPAN = 48

PARALLAX_LAYER_HEIGHT_MULT = 4
FAR_STAR_STARCHANCE = 170
NEAR_STAR_STARCHANCE = 72
FAR_SCROLL_SPEED = 0.18
NEAR_SCROLL_SPEED = 0.55
GAS_GIANT_SCROLL_SPEED = 0.90
GAS_GIANT_MIN_RADIUS = 20
GAS_GIANT_MAX_RADIUS = 36
GAS_GIANT_APPEAR_INTERVAL = 20.0
GAS_GIANT_PER_CYCLE = 1
STAR_DIM_FACTOR = 0.7
CLOCK_FONT_PATH = "/home/pi/LEDarcade/fonts/CHECKBK0.TTF"
CLOCK_DIGIT_RGB = (48, 200, 140)
CLOCK_SIZE_FACTOR = 0.7425
CLOCK_RESPAWN_DELAY = 10.0
CLOCK_SLIDE_DURATION = 0.52


def _panel_size():
    return LED.HatWidth, LED.HatHeight


def _motion_step(frame_dt):
    """Scale per-frame motion so speeds stay consistent without a frame sleep."""
    if frame_dt <= 0.0:
        return 1.0
    return min(frame_dt, MAX_SIM_DT) / SIM_REFERENCE_DT


def _generate_asteroid_lumps():
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


def _shade_asteroid_color(color, brightness_factor):
    r, g, b = color
    return (
        min(255, int(r * brightness_factor)),
        min(255, int(g * brightness_factor)),
        min(255, int(b * brightness_factor)),
    )


def _build_asteroid_sprite_pixels(size, color, lumps, dim_factor=1.0):
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


def _split_child_pair(parent_size):
    """Always two children, each smaller than the parent."""
    first = max(2, parent_size // 2)
    second = max(2, parent_size - first)
    if first >= parent_size or second >= parent_size:
        return None
    return first, second


def _split_fragment_angles(impact_angle, count):
    angles = []
    for _ in range(count):
        side = random.choice((-1, 1))
        angles.append(
            impact_angle
            + side * (
                math.pi / 2
                + random.uniform(-SPLIT_PERP_SPREAD_RAD, SPLIT_PERP_SPREAD_RAD)
            )
        )
    return angles


def _random_fall_velocity():
    angle = (math.pi / 2) + random.uniform(-ASTEROID_ANGLE_SPREAD, ASTEROID_ANGLE_SPREAD)
    speed = random.uniform(ASTEROID_SPEED_MIN, ASTEROID_SPEED_MAX)
    return math.cos(angle) * speed, math.sin(angle) * speed


def _velocity_toward(x, y, target_x, target_y, speed):
    angle = math.atan2(target_y - y, target_x - x)
    return math.cos(angle) * speed, math.sin(angle) * speed


class Spark:
    """Short-lived explosion streak in screen coordinates."""

    def __init__(self, x, y, angle, speed, length):
        self.x = float(x)
        self.y = float(y)
        self.angle = angle
        self.speed = speed
        self.length = max(1, min(length, 8))
        self.lifespan = SPARK_TRAIL_LENGTH

    def move(self, step=1.0):
        self.x += math.cos(self.angle) * self.speed * step
        self.y += math.sin(self.angle) * self.speed * step
        self.lifespan -= 1

    @property
    def alive(self):
        return self.lifespan > 0

    def draw(self, canvas):
        for i in range(self.length):
            px = int(round(self.x - math.cos(self.angle) * i))
            py = int(round(self.y - math.sin(self.angle) * i))
            if not (0 <= px < WIDTH and 0 <= py < HEIGHT):
                continue
            fade = max(32, SPARK_COLOR[0] - i * (SPARK_COLOR[0] // max(1, SPARK_TRAIL_LENGTH * 2)))
            canvas.SetPixel(px, py, fade, fade * 3 // 4, fade // 2)


class DebrisParticle:
    """Defender-style debris — one colored sprite pixel with drift and gravity."""

    def __init__(self, x, y, r, g, b, vx, vy):
        self.x = float(x)
        self.y = float(y)
        self.r, self.g, self.b = r, g, b
        self.vx = vx
        self.vy = vy
        self.lifespan = ENEMY_PARTICLE_LIFESPAN

    def move(self, step=1.0):
        self.vy += ENEMY_PARTICLE_GRAVITY * step
        self.x += self.vx * step
        self.y += self.vy * step
        self.lifespan -= 1

    @property
    def alive(self):
        return self.lifespan > 0

    def draw(self, canvas):
        px = int(round(self.x))
        py = int(round(self.y))
        if 0 <= px < WIDTH and 0 <= py < HEIGHT:
            fade = max(16, self.lifespan * 5)
            canvas.SetPixel(
                px, py,
                min(255, self.r * fade // 255),
                min(255, self.g * fade // 255),
                min(255, self.b * fade // 255),
            )


def _pick_asteroid_type(is_red=None, is_blue=None):
    if is_red is True:
        return RED_ROCK_COLOR, True, False
    if is_blue is True:
        return BLUE_ROCK_COLOR, False, True
    if is_red is False and is_blue is False:
        return random.choice(ASTEROID_COLORS), False, False
    roll = random.random()
    if roll < RED_ROCK_CHANCE:
        return RED_ROCK_COLOR, True, False
    if roll < RED_ROCK_CHANCE + BLUE_ROCK_CHANCE:
        return BLUE_ROCK_COLOR, False, True
    return random.choice(ASTEROID_COLORS), False, False


def _clamp_loot_speed(vx, vy):
    speed = math.hypot(vx, vy)
    if speed > LOOT_MAX_SPEED:
        scale = LOOT_MAX_SPEED / speed
        return vx * scale, vy * scale
    return vx, vy


class LootPixel:
    """Single-pixel collectible — momentum, gravity fall, and bounces."""

    __slots__ = ("x", "y", "vx", "vy", "alive", "bounce_cooldown", "rgb")

    def __init__(self, x, y, vx, vy, rgb):
        self.x = float(x)
        self.y = float(y)
        self.rgb = rgb
        vy = max(float(vy), LOOT_FALL_MIN)
        self.vx, self.vy = _clamp_loot_speed(float(vx), vy)
        self.alive = True
        self.bounce_cooldown = 0

    def move(self, step=1.0):
        self.vy += LOOT_GRAVITY * step
        self.vx, self.vy = _clamp_loot_speed(self.vx, self.vy)
        self.x += self.vx * step
        self.y += self.vy * step
        if self.bounce_cooldown > 0:
            self.bounce_cooldown -= 1

    def pixel(self):
        return int(round(self.x)), int(round(self.y))

    def collision_radius(self):
        return 0.45

    def off_screen(self, width, height):
        margin = 2
        return (
            self.y > height + margin
            or self.x < -margin
            or self.x > width + margin
        )

    def draw(self, canvas, tick):
        px, py = self.pixel()
        if 0 <= px < WIDTH and 0 <= py < HEIGHT:
            r, g, b = self.rgb
            pulse = 20 if (tick + px + py) % 4 == 0 else 0
            canvas.SetPixel(px, py, min(255, r + pulse), min(255, g + pulse), min(255, b + pulse))


class Crystal(LootPixel):
    def __init__(self, x, y, vx, vy):
        super().__init__(x, y, vx, vy, CRYSTAL_RGB)


class Gem(LootPixel):
    def __init__(self, x, y, vx, vy):
        super().__init__(x, y, vx, vy, GEM_RGB)


class FallingAsteroid:
    """Screen-space asteroid with its own drift trajectory."""

    def __init__(self, x, y, size=None, color=None, vx=None, vy=None, is_red=None, is_blue=None):
        self.x = float(x)
        self.y = float(y)
        self.size = size if size is not None else random.randint(*ASTEROID_SIZE_RANGE)
        if color is None:
            self.color, self.is_red, self.is_blue = _pick_asteroid_type(is_red, is_blue)
        else:
            self.color = color
            self.is_red = is_red if is_red is not None else color == RED_ROCK_COLOR
            self.is_blue = is_blue if is_blue is not None else color == BLUE_ROCK_COLOR
        self.lumps = _generate_asteroid_lumps()
        self.sprite_pixels = _build_asteroid_sprite_pixels(self.size, self.color, self.lumps, 1.0)
        if vx is None or vy is None:
            self.vx, self.vy = _random_fall_velocity()
        else:
            self.vx = vx
            self.vy = vy
        self.alive = True
        self.bounce_cooldown = 0

    def move(self, step=1.0):
        self.x += self.vx * step
        self.y += self.vy * step
        if self.bounce_cooldown > 0:
            self.bounce_cooldown -= 1

    def collision_radius(self):
        return self.size * 0.85

    def off_screen(self, width, height):
        margin = self.size + 3
        if self.y - margin > height:
            return True
        if self.x < -margin or self.x > width + margin:
            return True
        return False

    def hit_test(self, px, py):
        cx = int(round(self.x))
        cy = int(round(self.y))
        dx = px - cx
        dy = py - cy
        reach = self.collision_radius() + 1
        if dx * dx + dy * dy > reach * reach:
            return False
        for i, j, _ in self.sprite_pixels:
            if cx + i == px and cy + j == py:
                return True
        return False

    def draw(self, canvas):
        cx = int(round(self.x))
        cy = int(round(self.y))
        for i, j, rgb in self.sprite_pixels:
            px = cx + i
            py = cy + j
            if 0 <= px < WIDTH and 0 <= py < HEIGHT:
                canvas.SetPixel(px, py, *rgb)


def _split_asteroid(asteroid, impact_angle):
    """Break a rock into exactly two smaller pieces, or sparks if too small."""
    new_asteroids = []
    sparks = []

    child_sizes = None
    if asteroid.size >= MIN_ASTEROID_SPLIT_SIZE:
        child_sizes = _split_child_pair(asteroid.size)

    if child_sizes:
        for angle, child_size in zip(
            _split_fragment_angles(impact_angle, ROCK_SPLIT_COUNT),
            child_sizes,
        ):
            burst = random.uniform(*SPLIT_FLY_APART)
            offset = SPLIT_SPAWN_OFFSET + child_size * 0.2
            cx = asteroid.x + math.cos(angle) * offset
            cy = asteroid.y + math.sin(angle) * offset
            vx = asteroid.vx * SPLIT_PARENT_MOMENTUM + math.cos(angle) * burst
            vy = asteroid.vy * SPLIT_PARENT_MOMENTUM + math.sin(angle) * burst
            speed = math.hypot(vx, vy)
            max_speed = ASTEROID_SPEED_MAX * 1.4
            if speed > max_speed:
                scale = max_speed / speed
                vx *= scale
                vy *= scale
            new_asteroids.append(FallingAsteroid(
                cx, cy,
                size=child_size,
                color=asteroid.color,
                vx=vx,
                vy=vy,
                is_red=asteroid.is_red,
                is_blue=asteroid.is_blue,
            ))

    spark_count = TINY_ROCK_SPARK_COUNT if not child_sizes else SPARK_COUNT
    for _ in range(spark_count):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(DEBRIS_SPEED_MIN, DEBRIS_SPEED_MAX)
        sparks.append(Spark(asteroid.x, asteroid.y, angle, speed, int(asteroid.size * 1.5)))

    crystals = _spawn_loot_from_rock(asteroid, impact_angle, Crystal, RED_ROCK_CRYSTAL_CHANCE, asteroid.is_red)
    gems = _spawn_loot_from_rock(asteroid, impact_angle, Gem, BLUE_ROCK_GEM_CHANCE, asteroid.is_blue)
    return new_asteroids, sparks, crystals, gems


def _spawn_loot_from_rock(asteroid, impact_angle, loot_cls, drop_chance, should_drop):
    loot = []
    if not should_drop or random.random() > drop_chance:
        return loot
    for _ in range(random.randint(1, LOOT_MAX_PER_BREAK)):
        side = random.choice((-1, 1))
        angle = (
            impact_angle
            + side * (math.pi / 2 + random.uniform(-LOOT_BURST_SPREAD, LOOT_BURST_SPREAD))
        )
        burst = random.uniform(LOOT_BURST_MIN, LOOT_BURST_MAX)
        offset = random.uniform(0.8, 2.4)
        vx = asteroid.vx * LOOT_PARENT_MOMENTUM + math.cos(angle) * burst
        vy = asteroid.vy * LOOT_PARENT_MOMENTUM + math.sin(angle) * burst
        loot.append(loot_cls(
            asteroid.x + math.cos(angle) * offset,
            asteroid.y + math.sin(angle) * offset,
            vx,
            vy,
        ))
    return loot


def _brighten_enemy_rgb(r, g, b):
    if r == 0 and g == 0 and b == 0:
        return 0, 0, 0
    return (
        min(255, max(ENEMY_RGB_FLOOR, int(r * ENEMY_BRIGHTNESS))),
        min(255, max(ENEMY_RGB_FLOOR, int(g * ENEMY_BRIGHTNESS))),
        min(255, max(ENEMY_RGB_FLOOR, int(b * ENEMY_BRIGHTNESS))),
    )


class SkyfallEnemy:
    """Animated UFO with its own angled descent."""

    def __init__(self, x, y, sprite_type=None):
        self.sprite = copy.deepcopy(LED.ShipSprites[sprite_type or random.choice(ENEMY_SHIP_TYPES)])
        self.x = float(x)
        self.y = float(y)
        speed = random.uniform(ENEMY_SPEED_MIN, ENEMY_SPEED_MAX)
        target_x = random.uniform(WIDTH * 0.2, WIDTH * 0.8)
        self.vx, self.vy = _velocity_toward(x, y, target_x, HEIGHT, speed)
        self.alive = True
        self.ticks = 0
        self.currentframe = 1
        self._pixel_cache_frame = 0
        self._pixel_cache = []

    def move(self, step=1.0):
        self.x += self.vx * step
        self.y += self.vy * step
        self.ticks += 1
        framerate = max(1, self.sprite.framerate)
        if self.ticks >= framerate:
            self.currentframe += 1
            self.ticks = 0
            if self.currentframe > self.sprite.frames:
                self.currentframe = 1

    def off_screen(self, width, height):
        margin = max(self.sprite.width, self.sprite.height) + 2
        if self.y - margin > height:
            return True
        if self.x < -margin or self.x > width + margin:
            return True
        return False

    def sprite_pixels(self):
        frame = self.currentframe
        if frame > self.sprite.frames or frame == 0:
            frame = 1
        if frame == self._pixel_cache_frame:
            return self._pixel_cache
        grid = self.sprite.grid[frame]
        pixels = []
        sw = self.sprite.width
        for count in range(sw * self.sprite.height):
            y, x = divmod(count, sw)
            r, g, b = LED.ColorList[grid[count]]
            if r > 0 or g > 0 or b > 0:
                pixels.append((x, y, _brighten_enemy_rgb(r, g, b)))
        self._pixel_cache_frame = frame
        self._pixel_cache = pixels
        return pixels

    def hit_test(self, px, py):
        sx = int(round(self.x))
        sy = int(round(self.y))
        sw = self.sprite.width
        sh = self.sprite.height
        if px < sx or px >= sx + sw or py < sy or py >= sy + sh:
            return False
        for x, y, _ in self.sprite_pixels():
            if sx + x == px and sy + y == py:
                return True
        return False

    def draw(self, canvas):
        sx = int(round(self.x))
        sy = int(round(self.y))
        for x, y, rgb in self.sprite_pixels():
            px = sx + x
            py = sy + y
            if 0 <= px < WIDTH and 0 <= py < HEIGHT:
                canvas.SetPixel(px, py, *rgb)


def _enemy_to_particles(enemy):
    """Convert a UFO sprite into colored debris — Defender-style particles."""
    particles = []
    sx = int(round(enemy.x))
    sy = int(round(enemy.y))
    for x, y, rgb in enemy.sprite_pixels():
        px = sx + x
        py = sy + y
        vel_x = random.uniform(-0.9, 0.9) * 1.15
        vel_y = random.uniform(-0.5, 0.8) * 1.15
        particles.append(DebrisParticle(px, py, *rgb, vel_x, vel_y))
    return particles


class Bullet:
    __slots__ = ("x", "y", "vx", "vy", "alive", "shotgun")

    def __init__(self, x, y, vx=0.0, vy=None, shotgun=False):
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(-BULLET_SPEED if vy is None else vy)
        self.alive = True
        self.shotgun = shotgun

    def move(self, step=1.0):
        self.x += self.vx * step
        self.y += self.vy * step

    def draw(self, canvas):
        speed = math.hypot(self.vx, self.vy) or 1.0
        trail_x = self.vx / speed
        trail_y = self.vy / speed
        for i in range(BULLET_STREAK_LEN):
            px = int(round(self.x + trail_x * i))
            py = int(round(self.y + trail_y * i))
            if not (0 <= px < WIDTH and 0 <= py < HEIGHT):
                continue
            if i == 0:
                canvas.SetPixel(px, py, 255, 255, 255)
            else:
                fade = max(48, 220 - i * 55)
                canvas.SetPixel(px, py, fade, fade, min(255, fade + 20))


def _ship_pixels(ship_x, ship_y):
    pixels = []
    half = SHIP_WIDTH // 2
    for row, mask in enumerate(SHIP_SHAPE):
        for col, on in enumerate(mask):
            if on:
                pixels.append((int(ship_x) - half + col, ship_y + row))
    return pixels


def _draw_ship(canvas, ship_x, ship_y):
    half = SHIP_WIDTH // 2
    for row, mask in enumerate(SHIP_SHAPE):
        for col, on in enumerate(mask):
            if not on:
                continue
            px = int(ship_x) - half + col
            py = ship_y + row
            if not (0 <= px < WIDTH and 0 <= py < HEIGHT):
                continue
            if row == 0:
                canvas.SetPixel(px, py, *SHIP_NOSE_RGB)
            else:
                canvas.SetPixel(px, py, *SHIP_RGB)


def _asteroids_overlap(a, b):
    touch_dist = (a.collision_radius() + b.collision_radius()) * ASTEROID_COLLIDE_SCALE
    dx = b.x - a.x
    dy = b.y - a.y
    dist = math.hypot(dx, dy)
    return dist < touch_dist, dx, dy, dist, touch_dist


def _bounce_asteroid_pair(a, b):
    """Elastic bounce — rocks ricochet apart on contact."""
    overlap, dx, dy, dist, touch_dist = _asteroids_overlap(a, b)
    if not overlap:
        return

    if dist < 0.01:
        nx = random.choice((-1.0, 1.0))
        ny = random.uniform(-0.4, 0.4)
        norm = math.hypot(nx, ny) or 1.0
        nx /= norm
        ny /= norm
        dist = 1.0
    else:
        nx = dx / dist
        ny = dy / dist

    separation = touch_dist - dist
    if separation > 0:
        push = separation * 0.52
        a.x -= nx * push
        a.y -= ny * push
        b.x += nx * push
        b.y += ny * push

    m1 = a.size * a.size
    m2 = b.size * b.size
    total_mass = m1 + m2
    rel_vn = (a.vx - b.vx) * nx + (a.vy - b.vy) * ny
    if rel_vn < 0:
        impulse = 2 * rel_vn / total_mass
        a.vx -= impulse * m2 * nx
        a.vy -= impulse * m2 * ny
        b.vx += impulse * m1 * nx
        b.vy += impulse * m1 * ny

    a.bounce_cooldown = ASTEROID_BOUNCE_COOLDOWN
    b.bounce_cooldown = ASTEROID_BOUNCE_COOLDOWN


def _resolve_asteroid_bounces(asteroids):
    alive = [a for a in asteroids if a.alive]
    for i in range(len(alive)):
        for j in range(i + 1, len(alive)):
            a, b = alive[i], alive[j]
            if a.bounce_cooldown > 0 and b.bounce_cooldown > 0:
                continue
            _bounce_asteroid_pair(a, b)


def _enemy_hits_asteroid(enemy, asteroid):
    reach = asteroid.collision_radius() + max(enemy.sprite.width, enemy.sprite.height)
    if math.hypot(asteroid.x - enemy.x, asteroid.y - enemy.y) > reach:
        return False
    sx = int(round(enemy.x))
    sy = int(round(enemy.y))
    for x, y, _ in enemy.sprite_pixels():
        if asteroid.hit_test(sx + x, sy + y):
            return True
    return False


def _resolve_enemy_rock_collisions(enemies, asteroids):
    """UFOs shatter into debris when they strike a falling rock."""
    particles = []
    for enemy in enemies:
        if not enemy.alive:
            continue
        for asteroid in asteroids:
            if not asteroid.alive:
                continue
            if _enemy_hits_asteroid(enemy, asteroid):
                particles.extend(_enemy_to_particles(enemy))
                enemy.alive = False
                break
    return particles


def _star_rgb(brightness, purple=False):
    """Blue-tinted star field — SpaceExplorer palette."""
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


def _create_parallax_star_map(width, layer_height, starchance, brightness_range):
    """Tall star tile — sampled each frame as the field scrolls downward."""
    layer = [[(0, 0, 0) for _ in range(width)] for _ in range(layer_height)]
    bmin, bmax = brightness_range
    purple_positions = []

    for y in range(layer_height):
        for x in range(width):
            if random.randint(0, starchance) != 1:
                continue
            brightness = random.randint(bmin, bmax)
            layer[y][x] = _star_rgb(brightness)
            purple_positions.append((x, y, brightness))

    for x, y, brightness in random.sample(
        purple_positions, min(3, len(purple_positions)),
    ):
        layer[y][x] = _star_rgb(brightness, purple=True)

    return layer


def _gas_giant_rgb(dx, dy, radius, colors):
    dist = math.hypot(dx, dy)
    if dist > radius:
        return None
    band_idx = int((dy / max(1.0, radius * 0.42)) + 1.5) % len(colors)
    r, g, b = colors[band_idx]
    limb = 1.0 - 0.42 * (dist / max(radius, 1)) ** 1.15
    lit = 1.0 + 0.22 * max(0.0, (-dx * 0.65 - dy * 0.75) / radius)
    factor = max(0.38, min(1.3, limb * lit))
    return tuple(min(255, int(channel * factor)) for channel in (r, g, b))


def _paint_gas_giant_to_map(layer, width, layer_height, cx, cy, radius, colors, ringed):
    for dy in range(-radius - 4, radius + 5):
        for dx in range(-radius - 8, radius + 9):
            x = cx + dx
            y = cy + dy
            if not (0 <= x < width and 0 <= y < layer_height):
                continue
            if ringed and abs(dy) <= max(2, radius // 7):
                ring_dist = abs(math.hypot(dx, dy) - radius * 0.92)
                if ring_dist < 2.2 and abs(dx) > radius * 0.35:
                    ring_rgb = tuple(
                        min(255, int(channel * 0.72 + colors[1][i] * 0.28))
                        for i, channel in enumerate(colors[0])
                    )
                    layer[y][x] = ring_rgb
                    continue
            rgb = _gas_giant_rgb(dx, dy, radius, colors)
            if rgb is not None:
                layer[y][x] = rgb


def _gas_giant_extent(radius, ringed):
    if ringed:
        return radius + 8, radius + 4
    return radius, radius


def _gas_giant_layer_height(display_height):
    """Tall enough for doubled-size planets spaced ~20s of scroll apart."""
    max_extent_y = GAS_GIANT_MAX_RADIUS + 4
    scroll_gap = int(GAS_GIANT_APPEAR_INTERVAL * GAS_GIANT_SCROLL_SPEED * TARGET_FPS)
    slot_height = display_height + 2 * max_extent_y
    return GAS_GIANT_PER_CYCLE * (scroll_gap + slot_height)


def _create_gas_giant_parallax_map(width, layer_height, display_height):
    """Foreground parallax — rare huge planets drift closest to the camera."""
    layer = [[(0, 0, 0) for _ in range(width)] for _ in range(layer_height)]
    palettes = (
        ((185, 145, 95), (150, 105, 65), (205, 165, 105)),
        ((215, 185, 135), (165, 135, 95), (110, 85, 60)),
        ((75, 115, 175), (50, 85, 140), (115, 150, 205)),
        ((120, 85, 150), (85, 55, 110), (160, 120, 185)),
    )
    max_extent_y = GAS_GIANT_MAX_RADIUS + 4
    scroll_gap = int(GAS_GIANT_APPEAR_INTERVAL * GAS_GIANT_SCROLL_SPEED * TARGET_FPS)
    slot_height = display_height + 2 * max_extent_y

    for cycle_idx in range(GAS_GIANT_PER_CYCLE):
        radius = random.randint(GAS_GIANT_MIN_RADIUS, GAS_GIANT_MAX_RADIUS)
        colors = random.choice(palettes)
        ringed = random.random() < 0.4
        hx, hy = _gas_giant_extent(radius, ringed)
        slot_start = cycle_idx * (scroll_gap + slot_height) + scroll_gap
        cx = random.randint(-hx + 2, width + hx - 2)
        cy = random.randint(
            slot_start + hy // 2,
            max(slot_start + hy // 2, slot_start + slot_height - hy // 2),
        )
        _paint_gas_giant_to_map(layer, width, layer_height, cx, cy, radius, colors, ringed)
    return layer


def _build_parallax_layers(width, height):
    layer_height = max(height * PARALLAX_LAYER_HEIGHT_MULT, height + 8)
    giant_height = _gas_giant_layer_height(height)
    far_layer = _create_parallax_star_map(
        width, layer_height, FAR_STAR_STARCHANCE, (22, 95),
    )
    near_layer = _create_parallax_star_map(
        width, layer_height, NEAR_STAR_STARCHANCE, (45, 185),
    )
    giant_layer = _create_gas_giant_parallax_map(width, giant_height, height)
    return far_layer, near_layer, giant_layer, layer_height, giant_height


def _draw_parallax_layer(canvas, layer_map, scroll_y, width, height, tick=0, twinkle=False):
    """Paint one scrolling parallax layer — positive scroll drifts content upward."""
    layer_height = len(layer_map)
    base_scroll = int(scroll_y) % layer_height
    set_pixel = canvas.SetPixel
    twinkle_phase = tick

    for sy in range(height):
        row = layer_map[(sy - base_scroll) % layer_height]
        if twinkle:
            for sx in range(width):
                rgb = row[sx]
                if rgb == (0, 0, 0):
                    continue
                if ((twinkle_phase + sx + sy) % 7) == 0:
                    r, g, b = rgb
                    set_pixel(sx, sy, min(255, r + 9), min(255, g + 14), min(255, b + 28))
                else:
                    set_pixel(sx, sy, *rgb)
        else:
            for sx in range(width):
                rgb = row[sx]
                if rgb != (0, 0, 0):
                    set_pixel(sx, sy, *rgb)


def _background_clock_font_size():
    return 22 if WIDTH >= 64 else 16


def _background_clock_scale():
    return CLOCK_SIZE_FACTOR


def _create_background_clock_image(text=None):
    return LED.GenerateClockImageWithFixedTiles(
        FontPath=CLOCK_FONT_PATH,
        FontSize=_background_clock_font_size(),
        TextColor=CLOCK_DIGIT_RGB,
        BackgroundColor=(0, 0, 0),
        Text=text or time.strftime("%H:%M"),
    )


def _background_clock_station():
    """Fixed screen anchor — same left/top every minute so the clock never drifts."""
    scale = _background_clock_scale()
    font_size = _background_clock_font_size()
    cache_key = (WIDTH, HEIGHT, font_size, scale)
    cache = getattr(_background_clock_station, "_cache", None)
    if cache is None:
        cache = {}
        _background_clock_station._cache = cache
    if cache_key not in cache:
        ref_image = _create_background_clock_image(text="88:88")
        cache[cache_key] = _screen_clock_station(ref_image, scale)
    return cache[cache_key]


def _screen_clock_station(clock_image, scale):
    """Fixed screen anchor for the clock — upper sky, centered."""
    clock_w = max(1, math.ceil(clock_image.width * scale))
    clock_h = max(1, math.ceil(clock_image.height * scale))
    top = max(2, (HEIGHT // 3) - clock_h // 2)
    top = min(top, max(2, HEIGHT - clock_h))
    return {
        "left": max(0, (WIDTH - clock_w) // 2),
        "top": top,
        "scale": scale,
        "width": clock_w,
        "height": clock_h,
    }


def _clock_source_xy(dx, dy, scaled_w, scaled_h, img_w, img_h):
    """Map a scaled screen cell back to a source glyph pixel; last row maps to bottom."""
    if scaled_w <= 1:
        sx = 0
    else:
        sx = min(img_w - 1, max(0, (dx * img_w + scaled_w - 1) // scaled_w))
    if scaled_h <= 1:
        sy = 0
    else:
        sy = min(img_h - 1, max(0, (dy * img_h + scaled_h - 1) // scaled_h))
    return sx, sy


def _clock_draw_offset_y(slide_offset_y):
    """Snap the glide to the final row alignment near the end of the slide."""
    if slide_offset_y >= 0.0:
        return 0
    return int(math.ceil(slide_offset_y - 1e-6))


def _clock_screen_pixels(station, clock_image):
    """Bake CHECKBK0 glyphs into screen coordinates — rebuilt only when HH:MM changes."""
    left = station["left"]
    top = station["top"]
    scaled_w = station["width"]
    scaled_h = station["height"]
    baked = []
    pixels = clock_image.load()
    img_w = clock_image.width
    img_h = clock_image.height
    for dy in range(scaled_h):
        for dx in range(scaled_w):
            sx, sy = _clock_source_xy(dx, dy, scaled_w, scaled_h, img_w, img_h)
            rgb = pixels[sx, sy]
            if rgb == (0, 0, 0):
                continue
            px = left + dx
            py = top + dy
            if 0 <= px < WIDTH:
                baked.append((px, py, rgb))
    return baked


class ClockPixel:
    """One CHECKBK0 glyph pixel — destructible during power weapons."""

    __slots__ = ("x", "y", "r", "g", "b", "alive")

    def __init__(self, x, y, rgb):
        self.x = x
        self.y = y
        self.r, self.g, self.b = rgb
        self.alive = True


def _clock_pixels_from_screen_pixels(screen_pixels):
    return [ClockPixel(px, py, rgb) for px, py, rgb in screen_pixels]


def _build_clock_display():
    """Create the clock pixel cache for the current minute."""
    clock_image = _create_background_clock_image()
    station = _background_clock_station()
    return station, _clock_screen_pixels(station, clock_image), time.strftime("%H:%M")


def _new_clock_slide_state(station):
    """Place the clock just above the panel so it can slide into the station."""
    hidden_above = station["top"] + station["height"] + 2
    return {
        "start_offset": -hidden_above,
        "start_time": time.time(),
        "duration": CLOCK_SLIDE_DURATION,
    }


def _clock_slide_offset(slide_state, now):
    """Vertical slide offset for an entering clock (0 = final position)."""
    if slide_state is None:
        return 0.0
    elapsed = now - slide_state["start_time"]
    if elapsed >= slide_state["duration"]:
        return 0.0
    progress = elapsed / slide_state["duration"]
    eased = 1.0 - (1.0 - progress) ** 3
    return slide_state["start_offset"] * (1.0 - eased)


def _rebuild_clock_pixels(animate_entrance=False):
    """Bake a fresh clock for the current minute; slide in only after destruction."""
    station, screen_pixels, minute = _build_clock_display()
    slide_state = _new_clock_slide_state(station) if animate_entrance else None
    return _clock_pixels_from_screen_pixels(screen_pixels), minute, slide_state


def _clock_has_pixels(clock_pixels):
    return any(pixel.alive for pixel in clock_pixels)


def _power_weapon_active(shotgun_until, now, spark_streams):
    if _shotgun_active(shotgun_until, now):
        return True
    return any(stream.alive for stream in spark_streams)


def _resolve_clock_weapon_hits(bullets, spark_streams, clock_pixels, clock_slide_offset=0.0):
    """Shotgun streaks and spark-stream bolts chip individual clock pixels."""
    offset_y = _clock_draw_offset_y(clock_slide_offset)
    for bullet in bullets:
        if not bullet.alive or not bullet.shotgun:
            continue
        px = int(round(bullet.x))
        py = int(round(bullet.y))
        for pixel in clock_pixels:
            if pixel.alive and pixel.x == px and pixel.y + offset_y == py:
                pixel.alive = False
                bullet.alive = False
                break

    for stream in spark_streams:
        for hot in stream.sparks:
            if not hot.alive:
                continue
            px = int(round(hot.x))
            py = int(round(hot.y))
            for pixel in clock_pixels:
                if pixel.alive and pixel.x == px and pixel.y + offset_y == py:
                    pixel.alive = False
                    hot.alive = False
                    break


def _shatter_clock_pixels(clock_pixels, particles):
    """Burst remaining glyph pixels into drifting debris."""
    for pixel in clock_pixels:
        if not pixel.alive:
            continue
        particles.append(DebrisParticle(
            pixel.x, pixel.y, pixel.r, pixel.g, pixel.b,
            random.uniform(-1.4, 1.4) * 1.15,
            random.uniform(-1.8, 0.8) * 1.15,
        ))
        pixel.alive = False


def _draw_clock_pixels(canvas, clock_pixels, slide_offset_y=0.0):
    if not _clock_has_pixels(clock_pixels):
        return
    set_pixel = canvas.SetPixel
    offset_y = _clock_draw_offset_y(slide_offset_y)
    for pixel in clock_pixels:
        if not pixel.alive:
            continue
        py = pixel.y + offset_y
        if 0 <= pixel.x < WIDTH and 0 <= py < HEIGHT:
            set_pixel(pixel.x, py, pixel.r, pixel.g, pixel.b)


def _draw_parallax_background(
    canvas, far_layer, near_layer, giant_layer,
    far_scroll, near_scroll, giant_scroll, tick, clock_pixels,
    clock_slide_offset=0.0,
):
    """Far stars, near stars, gas giants, then fixed clock above both."""
    _draw_parallax_layer(canvas, far_layer, far_scroll, WIDTH, HEIGHT)
    _draw_parallax_layer(canvas, near_layer, near_scroll, WIDTH, HEIGHT, tick=tick, twinkle=True)
    _draw_parallax_layer(canvas, giant_layer, giant_scroll, WIDTH, HEIGHT)
    _draw_clock_pixels(canvas, clock_pixels, clock_slide_offset)


def _spawn_asteroid(width, height, asteroids):
    if len(asteroids) >= MAX_ASTEROIDS:
        return

    margin = 5
    spawn_style = random.choice(("top", "top", "top", "side"))

    if spawn_style == "top":
        x = random.randint(margin, width - margin)
        y = -ASTEROID_SPAWN_ABOVE
        vx, vy = _random_fall_velocity()
    else:
        from_left = random.choice((True, False))
        x = -margin if from_left else width + margin
        y = random.randint(0, max(1, height // 2))
        target_x = random.uniform(width * 0.2, width * 0.8)
        speed = random.uniform(ASTEROID_SPEED_MIN, ASTEROID_SPEED_MAX)
        vx, vy = _velocity_toward(x, y, target_x, height + 4, speed)

    asteroids.append(FallingAsteroid(x, y, vx=vx, vy=vy))


def _spawn_enemy(width, height, enemies):
    if len(enemies) >= MAX_ENEMIES:
        return

    margin = 4
    spawn_style = random.choice(("top", "side"))
    if spawn_style == "top":
        x = random.randint(margin, width - margin)
        y = -random.randint(2, 6)
    else:
        from_left = random.choice((True, False))
        x = -margin if from_left else width + margin
        y = random.randint(0, max(1, height // 3))

    enemies.append(SkyfallEnemy(x, y))


def _intercept_x(obj_x, obj_y, obj_vx, obj_vy, target_y, max_frames=SHIP_LOOKAHEAD_FRAMES):
    """Predict lateral position when an object reaches the hull row."""
    if abs(obj_vy) < 0.05:
        return obj_x
    frames = (target_y - obj_y) / obj_vy
    if frames < 0 or frames > max_frames:
        return obj_x
    return obj_x + obj_vx * frames


def _loot_intercept_x(loot, ship_y):
    """Stand here to catch a falling loot pixel when it reaches the hull row."""
    return _intercept_x(loot.x, loot.y, loot.vx, loot.vy, ship_y, LOOT_INTERCEPT_MAX_FRAMES)


def _asteroid_intercept_x(asteroid, ship_y):
    return _intercept_x(asteroid.x, asteroid.y, asteroid.vx, asteroid.vy, ship_y)


def _enemy_intercept_x(enemy, ship_y):
    ecy = enemy.y + enemy.sprite.height / 2
    return _intercept_x(
        enemy.x + enemy.sprite.width / 2,
        ecy,
        enemy.vx,
        enemy.vy,
        ship_y,
    )


def _shot_intercept_time(obj_y, obj_vy, ship_y, bullet_speed=BULLET_SPEED):
    """Frames until a vertical shot meets a target at its current altitude."""
    fire_y = ship_y - 1
    dy = fire_y - obj_y
    if dy <= 0.5:
        return 0.0
    climb_rate = bullet_speed + obj_vy
    if climb_rate <= 0.05:
        return None
    return dy / climb_rate


def _shot_intercept_x(obj_x, obj_y, obj_vx, obj_vy, ship_y, max_frames=SHIP_LOOKAHEAD_FRAMES):
    """Where to stand so a straight-up shot hits a moving target."""
    t = _shot_intercept_time(obj_y, obj_vy, ship_y)
    if t is None or t < 0.0 or t > max_frames:
        return obj_x
    return obj_x + obj_vx * t


def _asteroid_shot_intercept_x(asteroid, ship_y):
    return _shot_intercept_x(asteroid.x, asteroid.y, asteroid.vx, asteroid.vy, ship_y)


def _enemy_shot_intercept_x(enemy, ship_y):
    cx = enemy.x + enemy.sprite.width / 2
    cy = enemy.y + enemy.sprite.height / 2
    return _shot_intercept_x(cx, cy, enemy.vx, enemy.vy, ship_y)


def _nearest_hunt_loot(ship_x, ship_y, loot_items, width, height, asteroids, enemies):
    """Collectibles are top priority — chase the best intercept point."""
    best_x = None
    best_score = float("inf")
    for loot in loot_items:
        if not loot.alive:
            continue
        intercept_x = _loot_intercept_x(loot, ship_y)
        dx = abs(intercept_x - ship_x)
        urgency = loot.y / max(1.0, height)
        intercept_danger = _danger_score_at_position(
            intercept_x, ship_y, asteroids, enemies, width, height,
        )
        score = dx * 1.0 - urgency * 14.0 + intercept_danger * 0.55
        if score < best_score:
            best_score = score
            best_x = intercept_x
    return best_x, best_score


def _asteroid_on_screen(asteroid, width, height):
    return asteroid.alive and not asteroid.off_screen(width, height)


def _on_screen_asteroids(asteroids, width, height):
    return [a for a in asteroids if _asteroid_on_screen(a, width, height)]


def _asteroid_shootable(asteroid, ship_y, width=None, height=None):
    if not asteroid.alive:
        return False
    if width is not None and height is not None and not _asteroid_on_screen(asteroid, width, height):
        return False
    return asteroid.y <= ship_y + asteroid.size + 2


def _is_loot_rock(asteroid):
    return asteroid.is_red or asteroid.is_blue


def _score_fire_asteroid(ship_x, ship_y, asteroid):
    """Lower is better — red/blue loot rocks are the top shooting priority."""
    intercept_x = _asteroid_shot_intercept_x(asteroid, ship_y)
    dx = abs(intercept_x - ship_x)
    dy = max(0.0, ship_y - asteroid.y)
    threat_bonus = 0.0
    if abs(asteroid.vx) > 0.08:
        threat_bonus = max(0.0, 6.0 - dx) * 0.65
    loot_bonus = 0.0
    if asteroid.is_red:
        loot_bonus += RED_ROCK_SHOOT_BONUS
    elif asteroid.is_blue:
        loot_bonus += BLUE_ROCK_SHOOT_BONUS
    return dx * 1.35 + dy * 0.25 - asteroid.size * 0.2 - threat_bonus - loot_bonus


def _nearest_fire_asteroid(ship_x, ship_y, asteroids, width=None, height=None):
    """Pick a rock to shoot — loot carriers beat plain rocks when any are in range."""
    shootable = [
        a for a in asteroids
        if _asteroid_shootable(a, ship_y, width, height)
    ]
    loot_rocks = [a for a in shootable if _is_loot_rock(a)]
    pool = loot_rocks if loot_rocks else shootable

    best = None
    best_score = float("inf")
    for asteroid in pool:
        score = _score_fire_asteroid(ship_x, ship_y, asteroid)
        if score < best_score:
            best_score = score
            best = asteroid
    return best


def _nearest_hunt_asteroid(ship_x, ship_y, asteroids, width=None, height=None):
    """Pick the rock to slide under while hunting or shooting."""
    return _nearest_fire_asteroid(ship_x, ship_y, asteroids, width, height)


def _best_fire_target(ship_x, ship_y, asteroids, enemies, width=None, height=None):
    """Shooting target — red/blue loot rocks beat everything else on screen."""
    asteroid = _nearest_fire_asteroid(ship_x, ship_y, asteroids, width, height)
    if asteroid is not None:
        return ("asteroid", asteroid)
    enemy = _nearest_hunt_enemy(ship_x, ship_y, enemies)
    if enemy is not None:
        return ("enemy", enemy)
    return None


def _enemy_shootable(enemy, ship_y):
    if not enemy.alive:
        return False
    return enemy.y <= ship_y + max(enemy.sprite.width, enemy.sprite.height) + 2


def _screen_has_fire_targets(ship_y, asteroids, enemies, width=None, height=None):
    """True while anything above the hull is worth shooting — fire never waits on alignment."""
    if any(_asteroid_shootable(a, ship_y, width, height) for a in asteroids):
        return True
    return any(_enemy_shootable(e, ship_y) for e in enemies)


def _nearest_hunt_enemy(ship_x, ship_y, enemies):
    """Nearest UFO worth shooting while the ship hunts loot or patrols."""
    best = None
    best_score = float("inf")
    for enemy in enemies:
        if not enemy.alive:
            continue
        intercept_x = _enemy_shot_intercept_x(enemy, ship_y)
        dx = abs(intercept_x - ship_x)
        dy = max(0.0, ship_y - enemy.y)
        score = dx * 1.4 + dy * 0.4
        if score < best_score:
            best_score = score
            best = enemy
    return best


def _has_fire_target(ship_x, ship_y, asteroids, enemies, width=None, height=None):
    return _screen_has_fire_targets(ship_y, asteroids, enemies, width, height)


def _choose_hunt_target(
    ship_x, ship_y, crystals, gems, asteroids, enemies, width, height,
    crystal_count=0, gem_count=0,
):
    here_danger = _danger_score_at_position(ship_x, ship_y, asteroids, enemies, width, height)
    loot_pool = crystals + gems
    if gem_count < GEM_POWER_COST and gems:
        loot_pool = gems + crystals
    elif crystal_count < CRYSTAL_POWER_COST and crystals:
        loot_pool = crystals + gems

    loot_x, loot_score = _nearest_hunt_loot(
        ship_x, ship_y, loot_pool, width, height, asteroids, enemies,
    )
    loot_limit = SHIP_LOOT_DANGER_LIMIT
    if here_danger > SHIP_SURVIVAL_DANGER:
        loot_limit = 10.0
    fire_target = _best_fire_target(ship_x, ship_y, asteroids, enemies, width, height)
    if fire_target is not None and fire_target[0] == "asteroid" and _is_loot_rock(fire_target[1]):
        return _asteroid_shot_intercept_x(fire_target[1], ship_y), False

    if loot_x is not None and loot_score < loot_limit:
        return loot_x, True

    if fire_target is not None:
        if fire_target[0] == "asteroid":
            return _asteroid_shot_intercept_x(fire_target[1], ship_y), False
        return _enemy_shot_intercept_x(fire_target[1], ship_y), False

    asteroid = _nearest_hunt_asteroid(ship_x, ship_y, asteroids, width, height)
    if asteroid is not None:
        return _asteroid_shot_intercept_x(asteroid, ship_y), False

    enemy = _nearest_hunt_enemy(ship_x, ship_y, enemies)
    if enemy is not None:
        return _enemy_shot_intercept_x(enemy, ship_y), False

    return _safest_open_lane(ship_x, ship_y, asteroids, enemies, width, height), False


def _clamp_ship_x(ship_x, width):
    margin = SHIP_WIDTH // 2 + 1
    return max(margin, min(width - margin - 1, ship_x))


def _steer_ship_toward_target(ship_x, target_x, width, speed=None, step=1.0):
    """Slide the ship under the hunted target."""
    move_speed = (HUNT_SPEED if speed is None else speed) * step
    if ship_x < target_x - SHIP_STEER_DEADBAND:
        ship_x += move_speed
    elif ship_x > target_x + SHIP_STEER_DEADBAND:
        ship_x -= move_speed
    return _clamp_ship_x(ship_x, width)


def _ship_move_direction(delta):
    if delta > 0.05:
        return 1
    if delta < -0.05:
        return -1
    return 0


def _ship_steer_cost_adjustment(delta, last_dir):
    """Prefer holding course — dampens rapid left-right wiggle."""
    cost = 0.0
    if delta == 0.0:
        cost -= SHIP_MOVE_HOLD_BIAS
    new_dir = _ship_move_direction(delta)
    if last_dir and new_dir and new_dir != last_dir:
        cost += SHIP_REVERSE_PENALTY
    return cost


def _edge_trap_penalty(ship_x, width):
    margin = SHIP_WIDTH // 2 + 1
    left = ship_x - margin
    right = (width - margin - 1) - ship_x
    edge = min(left, right)
    if edge >= SHIP_EDGE_TRAP_DISTANCE:
        return 0.0
    return (SHIP_EDGE_TRAP_DISTANCE - edge) * 2.2


def _danger_score_at_position(ship_x, ship_y, asteroids, enemies, width=None, height=None):
    """Higher means less safe — uses current proximity and predicted lane crossings."""
    score = 0.0

    for asteroid in asteroids:
        if not asteroid.alive:
            continue
        if width is not None and height is not None and not _asteroid_on_screen(asteroid, width, height):
            continue
        radius = asteroid.collision_radius()
        dist = math.hypot(asteroid.x - ship_x, asteroid.y - ship_y)
        if dist < radius + SHIP_URGENT_DANGER:
            score += (radius + SHIP_URGENT_DANGER - dist) * 8.0

        if asteroid.vy > 0.05:
            frames = (ship_y - asteroid.y) / asteroid.vy
            if 0 <= frames <= SHIP_LOOKAHEAD_FRAMES:
                pred_x = asteroid.x + asteroid.vx * frames
                dx = abs(pred_x - ship_x)
                lane = radius + SHIP_LANE_CLEARANCE
                if dx < lane:
                    urgency = 1.0 + (SHIP_LOOKAHEAD_FRAMES - frames) / SHIP_LOOKAHEAD_FRAMES * 2.5
                    score += (lane - dx) * urgency * (1.0 + asteroid.size * 0.18)
        elif asteroid.y <= ship_y + radius + 1.5:
            dx = abs(asteroid.x - ship_x)
            lane = radius + SHIP_LANE_CLEARANCE * 0.85
            if dx < lane:
                score += (lane - dx) * 2.2

    for enemy in enemies:
        if not enemy.alive:
            continue
        ecx = enemy.x + enemy.sprite.width / 2
        ecy = enemy.y + enemy.sprite.height / 2
        dist = math.hypot(ecx - ship_x, ecy - ship_y)
        if dist < SHIP_URGENT_DANGER + 3:
            score += (SHIP_URGENT_DANGER + 3 - dist) * 6.0
        if enemy.vy > 0.02:
            frames = (ship_y - ecy) / enemy.vy
            if 0 <= frames <= SHIP_LOOKAHEAD_FRAMES:
                pred_x = ecx + enemy.vx * frames
                dx = abs(pred_x - ship_x)
                lane = max(enemy.sprite.width, enemy.sprite.height) * 0.45 + 2.2
                if dx < lane:
                    urgency = 1.0 + (SHIP_LOOKAHEAD_FRAMES - frames) / SHIP_LOOKAHEAD_FRAMES
                    score += (lane - dx) * urgency * 2.5

    if width is not None:
        score += _edge_trap_penalty(ship_x, width)

    return score


def _safest_open_lane(ship_x, ship_y, asteroids, enemies, width, height):
    """Scan the patrol row and pick the lowest-threat lane."""
    margin = SHIP_WIDTH // 2 + 1
    best_x = ship_x
    best_danger = float("inf")
    x = margin
    while x <= width - margin - 1:
        danger = _danger_score_at_position(x, ship_y, asteroids, enemies, width, height)
        if danger < best_danger:
            best_danger = danger
            best_x = x
        x += SHIP_LANE_SAMPLE_STEP
    return best_x


def _ship_move_speed(hunting_loot, urgent=False):
    if urgent:
        return SHIP_DODGE_SPEED
    return LOOT_HUNT_SPEED if hunting_loot else HUNT_SPEED


def _ship_move_options(hunting_loot, urgent=False, step=1.0):
    """Candidate lateral deltas for one frame — one speed avoids flip-flop."""
    speed = _ship_move_speed(hunting_loot, urgent) * step
    return (0.0, speed, -speed)


def _pick_ship_move(ship_x, ship_y, hunt_x, asteroids, enemies, width, height, deltas, last_dir,
                    danger_weight, hunt_weight=0.0):
    best_x = ship_x
    best_cost = float("inf")
    for delta in deltas:
        cx = _clamp_ship_x(ship_x + delta, width)
        danger = _danger_score_at_position(cx, ship_y, asteroids, enemies, width, height)
        cost = danger * danger_weight
        if hunt_weight > 0.0:
            cost += abs(cx - hunt_x) * hunt_weight
        cost += _ship_steer_cost_adjustment(delta, last_dir)
        if cost < best_cost:
            best_cost = cost
            best_x = cx
    return best_x, _ship_move_direction(best_x - ship_x)


def _update_ship_ai(
    ship_x, ship_y, crystals, gems, asteroids, enemies, width, height,
    crystal_count=0, gem_count=0, ship_steer=None, step=1.0,
):
    """Hunt loot and shooting lanes, but dodge when threats close in."""
    if ship_steer is None:
        ship_steer = {"hunt_x": ship_x, "last_dir": 0}

    raw_hunt_x, hunting_loot = _choose_hunt_target(
        ship_x, ship_y, crystals, gems, asteroids, enemies, width, height,
        crystal_count=crystal_count, gem_count=gem_count,
    )
    rock_target = _best_fire_target(ship_x, ship_y, asteroids, enemies, width, height)
    if rock_target is not None and abs(rock_target[1].vx) > 0.1:
        smooth = 0.40
    elif rock_target is None and not hunting_loot:
        smooth = 0.42
    else:
        smooth = SHIP_HUNT_SMOOTH
    hunt_x = ship_steer["hunt_x"] + (raw_hunt_x - ship_steer["hunt_x"]) * smooth
    ship_steer["hunt_x"] = hunt_x

    here_danger = _danger_score_at_position(ship_x, ship_y, asteroids, enemies, width, height)
    imminent = _ship_danger_imminent(ship_x, ship_y, asteroids, enemies, width, height)
    last_dir = ship_steer["last_dir"]

    if imminent or here_danger > SHIP_SURVIVAL_DANGER + 4.0:
        deltas = _ship_move_options(hunting_loot, urgent=True, step=step)
        best_x, move_dir = _pick_ship_move(
            ship_x, ship_y, hunt_x, asteroids, enemies, width, height, deltas, last_dir,
            danger_weight=5.5, hunt_weight=0.2,
        )
        ship_steer["last_dir"] = move_dir or last_dir
        return best_x, hunting_loot, ship_steer

    if here_danger > SHIP_SURVIVAL_DANGER:
        deltas = _ship_move_options(False, urgent=False, step=step)
        best_x, move_dir = _pick_ship_move(
            ship_x, ship_y, hunt_x, asteroids, enemies, width, height, deltas, last_dir,
            danger_weight=5.5, hunt_weight=0.35,
        )
        ship_steer["last_dir"] = move_dir or last_dir
        return best_x, hunting_loot, ship_steer

    hunt_weight = 1.15 if hunting_loot else 0.9
    danger_weight = 3.6 if hunting_loot else 4.2
    deltas = _ship_move_options(hunting_loot, urgent=False, step=step)
    best_x, move_dir = _pick_ship_move(
        ship_x, ship_y, hunt_x, asteroids, enemies, width, height, deltas, last_dir,
        danger_weight=danger_weight, hunt_weight=hunt_weight,
    )

    if best_x == ship_x and abs(ship_x - hunt_x) > SHIP_STEER_DEADBAND:
        speed = _ship_move_speed(hunting_loot, urgent=False)
        best_x = _steer_ship_toward_target(ship_x, hunt_x, width, speed=speed, step=step)
        move_dir = _ship_move_direction(best_x - ship_x) or last_dir

    ship_steer["last_dir"] = move_dir or last_dir
    return best_x, hunting_loot, ship_steer


def _active_shot_count(bullets):
    return sum(1 for bullet in bullets if bullet.alive)


def _fire_bullet(ship_x, ship_y, bullets):
    if _active_shot_count(bullets) >= MAX_ACTIVE_SHOTS:
        return False
    bullets.append(Bullet(ship_x, ship_y - 1))
    return True


def _fire_shotgun_burst(ship_x, ship_y, bullets):
    """Five bright streaks in a spread — shotgun power."""
    base_angle = -math.pi / 2
    if SHOTGUN_BULLET_COUNT == 1:
        offsets = [0.0]
    else:
        step = (2 * SHOTGUN_SPREAD) / (SHOTGUN_BULLET_COUNT - 1)
        offsets = [-SHOTGUN_SPREAD + step * i for i in range(SHOTGUN_BULLET_COUNT)]
    for offset in offsets:
        angle = base_angle + offset
        bullets.append(Bullet(
            ship_x,
            ship_y - 1,
            vx=math.cos(angle) * BULLET_SPEED,
            vy=math.sin(angle) * BULLET_SPEED,
            shotgun=True,
        ))


def _shotgun_active(shotgun_until, now):
    return now < shotgun_until


def _shotgun_bullets_active(bullets):
    return any(bullet.alive and bullet.shotgun for bullet in bullets)


def _try_activate_shotgun_power(crystal_count, shotgun_until, now):
    """Spend five crystals for five seconds of shotgun — one burst at a time."""
    if crystal_count >= CRYSTAL_POWER_COST and now >= shotgun_until:
        return crystal_count - CRYSTAL_POWER_COST, now + SHOTGUN_DURATION
    return crystal_count, shotgun_until


def _try_shotgun_fire(ship_x, ship_y, bullets, shotgun_until, now, last_shotgun_fire):
    if not _shotgun_active(shotgun_until, now):
        return last_shotgun_fire
    if _shotgun_bullets_active(bullets):
        return last_shotgun_fire
    if now - last_shotgun_fire < SHOTGUN_FIRE_INTERVAL:
        return last_shotgun_fire
    _fire_shotgun_burst(ship_x, ship_y, bullets)
    return now


def _destroy_spark_target(kind, obj, sparks, particles):
    if kind == "asteroid":
        if not obj.alive:
            return
        for _ in range(5):
            angle = random.uniform(0, 2 * math.pi)
            sparks.append(Spark(
                obj.x, obj.y, angle, random.uniform(EXPLOSION_SPARK_SPEED_MIN, EXPLOSION_SPARK_SPEED_MAX), 4,
            ))
        obj.alive = False
    elif kind == "enemy":
        if obj.alive:
            particles.extend(_enemy_to_particles(obj))
            obj.alive = False


def _screen_explode(asteroids, enemies, bullets, sparks, particles):
    for asteroid in asteroids:
        if asteroid.alive:
            for _ in range(3):
                angle = random.uniform(0, 2 * math.pi)
                sparks.append(Spark(
                    asteroid.x, asteroid.y, angle,
                    random.uniform(EXPLOSION_SPARK_SPEED_MIN, EXPLOSION_SPARK_SPEED_MAX), 5,
                ))
            asteroid.alive = False
    for enemy in enemies:
        if enemy.alive:
            particles.extend(_enemy_to_particles(enemy))
            enemy.alive = False
    for bullet in bullets:
        bullet.alive = False


class HotSpark:
    """Red-hot streak that scorches anything it touches."""

    __slots__ = ("x", "y", "vx", "vy", "alive", "age")

    def __init__(self, x, y, angle, speed):
        self.x = float(x)
        self.y = float(y)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.alive = True
        self.age = 0

    def move(self, step=1.0):
        self.x += self.vx * step
        self.y += self.vy * step
        self.age += 1
        if self.age > HOT_SPARK_MAX_AGE:
            self.alive = False
        elif self.x < -6 or self.x > WIDTH + 6 or self.y < -6 or self.y > HEIGHT + 6:
            self.alive = False

    def draw(self, canvas):
        speed = math.hypot(self.vx, self.vy) or 1.0
        trail_x = self.vx / speed
        trail_y = self.vy / speed
        for i in range(HOT_SPARK_TRAIL_LEN):
            px = int(round(self.x + trail_x * i))
            py = int(round(self.y + trail_y * i))
            if not (0 <= px < WIDTH and 0 <= py < HEIGHT):
                continue
            if i == 0:
                canvas.SetPixel(px, py, 255, 70, 10)
            else:
                fade = max(64, 255 - i * 42)
                canvas.SetPixel(px, py, fade, fade // 5, 0)


class SparkStream:
    """Torrent of red-hot sparks from the ship — clears the screen."""

    def __init__(self, ship_x, ship_y):
        self.ship_x = float(ship_x)
        self.ship_y = float(ship_y)
        self.sparks = []
        self.emit_left = SPARK_STREAM_EMIT_FRAMES
        self.cleared = False

    def _emit_burst(self):
        for _ in range(SPARK_STREAM_SPARKS_PER_BURST):
            angle = -math.pi / 2 + random.uniform(-SPARK_STREAM_SPREAD, SPARK_STREAM_SPREAD)
            speed = random.uniform(SPARK_STREAM_SPEED_MIN, SPARK_STREAM_SPEED_MAX)
            ox = random.uniform(-1.4, 1.4)
            oy = random.uniform(-0.6, 0.2)
            self.sparks.append(HotSpark(self.ship_x + ox, self.ship_y + oy, angle, speed))

    def _resolve_hits(self, asteroids, enemies, sparks, particles):
        for hot in self.sparks:
            if not hot.alive:
                continue
            px = int(round(hot.x))
            py = int(round(hot.y))
            for asteroid in asteroids:
                if not asteroid.alive:
                    continue
                reach = asteroid.collision_radius() + 1
                if (px - asteroid.x) ** 2 + (py - asteroid.y) ** 2 > reach * reach:
                    continue
                if asteroid.hit_test(px, py):
                    _destroy_spark_target("asteroid", asteroid, sparks, particles)
                    hot.alive = False
                    break
            if not hot.alive:
                continue
            for enemy in enemies:
                if not enemy.alive:
                    continue
                sx = int(round(enemy.x))
                sy = int(round(enemy.y))
                if px < sx or px >= sx + enemy.sprite.width or py < sy or py >= sy + enemy.sprite.height:
                    continue
                if enemy.hit_test(px, py):
                    _destroy_spark_target("enemy", enemy, sparks, particles)
                    hot.alive = False
                    break

    def move(self, asteroids, enemies, bullets, sparks, particles, step=1.0):
        if self.emit_left > 0:
            self._emit_burst()
            self.emit_left -= 1
        for hot in self.sparks:
            if hot.alive:
                hot.move(step)
        self._resolve_hits(asteroids, enemies, sparks, particles)
        self.sparks = [hot for hot in self.sparks if hot.alive]
        if self.emit_left <= 0 and not self.sparks and not self.cleared:
            _screen_explode(asteroids, enemies, bullets, sparks, particles)
            self.cleared = True

    @property
    def alive(self):
        return self.emit_left > 0 or bool(self.sparks) or not self.cleared

    def draw(self, canvas):
        for hot in self.sparks:
            if hot.alive:
                hot.draw(canvas)


def _count_screen_threats(asteroids, enemies):
    return (
        sum(1 for asteroid in asteroids if asteroid.alive)
        + sum(1 for enemy in enemies if enemy.alive)
    )


def _ship_danger_imminent(ship_x, ship_y, asteroids, enemies, width=None, height=None):
    for px, py in _ship_pixels(ship_x, ship_y):
        for asteroid in asteroids:
            if not asteroid.alive:
                continue
            if width is not None and height is not None and not _asteroid_on_screen(asteroid, width, height):
                continue
            dist = math.hypot(asteroid.x - px, asteroid.y - py)
            if dist <= asteroid.collision_radius() + LIGHTNING_DANGER_DISTANCE:
                return True
        for enemy in enemies:
            if not enemy.alive:
                continue
            cx = enemy.x + enemy.sprite.width / 2
            cy = enemy.y + enemy.sprite.height / 2
            if math.hypot(cx - px, cy - py) <= LIGHTNING_DANGER_DISTANCE + 2:
                return True
    return False


def _should_fire_lightning(gem_count, asteroids, enemies, ship_x, ship_y):
    if gem_count < GEM_POWER_COST:
        return False
    if _count_screen_threats(asteroids, enemies) >= LIGHTNING_MIN_TARGETS:
        return True
    return _ship_danger_imminent(ship_x, ship_y, asteroids, enemies, WIDTH, HEIGHT)


def _try_activate_lightning_power(
    gem_count, lightning_until, now, ship_x, ship_y,
    asteroids, enemies, bullets, sparks, particles,
):
    if not _should_fire_lightning(gem_count, asteroids, enemies, ship_x, ship_y):
        return gem_count, lightning_until, None
    if now < lightning_until:
        return gem_count, lightning_until, None
    stream = SparkStream(ship_x, ship_y)
    return gem_count - GEM_POWER_COST, now + SPARK_STREAM_DURATION, stream


def _reflect_loot_velocity(loot, nx, ny):
    vn = loot.vx * nx + loot.vy * ny
    if vn >= 0:
        return
    damp = LOOT_BOUNCE_DAMPING
    loot.vx -= (1.0 + damp) * vn * nx
    loot.vy -= (1.0 + damp) * vn * ny
    loot.vx, loot.vy = _clamp_loot_speed(loot.vx, loot.vy)


def _bounce_loot_walls(loot, width, height):
    margin = loot.collision_radius()

    if loot.x < margin:
        loot.x = margin
        _reflect_loot_velocity(loot, 1.0, 0.0)
        loot.bounce_cooldown = LOOT_BOUNCE_COOLDOWN
    elif loot.x > width - margin:
        loot.x = width - margin
        _reflect_loot_velocity(loot, -1.0, 0.0)
        loot.bounce_cooldown = LOOT_BOUNCE_COOLDOWN

    if loot.y < margin:
        loot.y = margin
        _reflect_loot_velocity(loot, 0.0, 1.0)
        loot.bounce_cooldown = LOOT_BOUNCE_COOLDOWN
    elif loot.y > height - margin:
        loot.y = height - margin
        _reflect_loot_velocity(loot, 0.0, -1.0)
        loot.bounce_cooldown = LOOT_BOUNCE_COOLDOWN


def _bounce_loot_pair(a, b):
    dx = b.x - a.x
    dy = b.y - a.y
    dist = math.hypot(dx, dy)
    touch = (a.collision_radius() + b.collision_radius()) * 0.95
    if dist >= touch:
        return
    if dist < 0.01:
        nx = random.choice((-1.0, 1.0))
        ny = 0.0
        dist = 1.0
    else:
        nx = dx / dist
        ny = dy / dist

    overlap = touch - dist
    if overlap > 0:
        push = overlap * 0.52
        a.x -= nx * push
        a.y -= ny * push
        b.x += nx * push
        b.y += ny * push

    rel_vn = (a.vx - b.vx) * nx + (a.vy - b.vy) * ny
    if rel_vn < 0:
        impulse = rel_vn * LOOT_BOUNCE_DAMPING
        a.vx -= impulse * nx
        a.vy -= impulse * ny
        b.vx += impulse * nx
        b.vy += impulse * ny
        a.vx, a.vy = _clamp_loot_speed(a.vx, a.vy)
        b.vx, b.vy = _clamp_loot_speed(b.vx, b.vy)
    a.bounce_cooldown = LOOT_BOUNCE_COOLDOWN
    b.bounce_cooldown = LOOT_BOUNCE_COOLDOWN


def _bounce_loot_asteroid(loot, asteroid):
    dx = loot.x - asteroid.x
    dy = loot.y - asteroid.y
    dist = math.hypot(dx, dy)
    touch = loot.collision_radius() + asteroid.collision_radius()
    if dist >= touch or dist < 0.01:
        return

    nx = dx / dist
    ny = dy / dist
    overlap = touch - dist
    if overlap > 0:
        loot.x += nx * overlap * 0.8
        loot.y += ny * overlap * 0.8

    _reflect_loot_velocity(loot, nx, ny)
    loot.bounce_cooldown = LOOT_BOUNCE_COOLDOWN


def _resolve_loot_bounces(loot_items, asteroids, width, height):
    alive = [item for item in loot_items if item.alive]
    for loot in alive:
        _bounce_loot_walls(loot, width, height)

    for i in range(len(alive)):
        for j in range(i + 1, len(alive)):
            a, b = alive[i], alive[j]
            if a.bounce_cooldown > 0 and b.bounce_cooldown > 0:
                continue
            _bounce_loot_pair(a, b)

    for loot in alive:
        if loot.bounce_cooldown > 0:
            continue
        for asteroid in asteroids:
            if not asteroid.alive:
                continue
            reach = loot.collision_radius() + asteroid.collision_radius()
            if (loot.x - asteroid.x) ** 2 + (loot.y - asteroid.y) ** 2 > reach * reach:
                continue
            _bounce_loot_asteroid(loot, asteroid)


def _collect_loot(ship_x, ship_y, loot_items):
    """Only a direct hull touch picks up a loot pixel."""
    ship_pixels = set(_ship_pixels(ship_x, ship_y))
    collected = 0
    for loot in loot_items:
        if loot.alive and loot.pixel() in ship_pixels:
            loot.alive = False
            collected += 1
    return collected


def _lightning_active(lightning_until, now):
    return now < lightning_until


def _draw_power_hud(canvas, crystal_count, gem_count, shotgun_until, lightning_until, now):
    for i in range(min(CRYSTAL_POWER_COST, crystal_count)):
        x = 1 + i * 2
        if 0 <= x < WIDTH:
            canvas.SetPixel(x, 0, *CRYSTAL_RGB)
    for i in range(min(GEM_POWER_COST, gem_count)):
        x = 1 + i * 2
        if 0 <= x < WIDTH and HEIGHT > 1:
            canvas.SetPixel(x, 1, *GEM_RGB)
    if _shotgun_active(shotgun_until, now) and WIDTH > 2:
        flash = 255 if int(now * 8) % 2 == 0 else 180
        canvas.SetPixel(WIDTH - 2, 0, flash, flash, flash)
    if _lightning_active(lightning_until, now) and WIDTH > 2:
        flash = 255 if int(now * 10) % 2 == 0 else 170
        canvas.SetPixel(WIDTH - 1, 0, flash, flash // 4, 0)


def _try_hunt_fire(ship_x, ship_y, bullets, asteroids, enemies, width, height, now, last_fire, shots_ready):
    """
    Two-shot volley — reload only after both bright streaks are gone.
    Keep shooting whenever threats are on screen, even while hunting loot or dodging.
    """
    if _active_shot_count(bullets) == 0:
        shots_ready = MAX_ACTIVE_SHOTS

    if not _screen_has_fire_targets(ship_y, asteroids, enemies, width, height) or shots_ready <= 0:
        return last_fire, shots_ready

    if _active_shot_count(bullets) >= MAX_ACTIVE_SHOTS:
        return last_fire, shots_ready

    if now - last_fire < FIRE_INTERVAL:
        return last_fire, shots_ready

    if _fire_bullet(ship_x, ship_y, bullets):
        shots_ready -= 1
        last_fire = now

    return last_fire, shots_ready


def _handle_shots(asteroids, enemies, bullets):
    new_asteroids = []
    sparks = []
    crystals = []
    gems = []
    particles = []
    hit_flashes = []
    impact_angle = -math.pi / 2

    for bullet in bullets:
        if not bullet.alive:
            continue
        px = int(round(bullet.x))
        py = int(round(bullet.y))

        for enemy in enemies:
            if not enemy.alive:
                continue
            if enemy.hit_test(px, py):
                bullet.alive = False
                particles.extend(_enemy_to_particles(enemy))
                enemy.alive = False
                hit_flashes.append((px, py))
                break
        if not bullet.alive:
            continue

        for asteroid in asteroids:
            if not asteroid.alive:
                continue
            if asteroid.hit_test(px, py):
                bullet.alive = False
                hit_flashes.append((px, py))
                frags, asteroid_sparks, rock_crystals, rock_gems = _split_asteroid(asteroid, impact_angle)
                asteroid.alive = False
                new_asteroids.extend(frags)
                sparks.extend(asteroid_sparks)
                crystals.extend(rock_crystals)
                gems.extend(rock_gems)
                break

    return new_asteroids, sparks, crystals, gems, particles, hit_flashes


def _ship_hit_obstacles(ship_x, ship_y, asteroids, enemies):
    for px, py in _ship_pixels(ship_x, ship_y):
        for asteroid in asteroids:
            if asteroid.alive and asteroid.hit_test(px, py):
                return ("asteroid", asteroid)
        for enemy in enemies:
            if enemy.alive and enemy.hit_test(px, py):
                return ("enemy", enemy)
    return None


def _ship_explosion(ship_x, ship_y, sparks, particles):
    """Spectacular hull burst — sparks, debris, and a hot core flash."""
    for px, py in _ship_pixels(ship_x, ship_y):
        for _ in range(3):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(SHIP_EXPLOSION_SPARK_SPEED_MIN, SHIP_EXPLOSION_SPARK_SPEED_MAX)
            sparks.append(Spark(px, py, angle, speed, random.randint(5, 8)))
        particles.append(DebrisParticle(
            px, py,
            SHIP_NOSE_RGB[0], SHIP_NOSE_RGB[1], SHIP_NOSE_RGB[2],
            random.uniform(-1.8, 1.8) * 1.15,
            random.uniform(-2.4, 0.6) * 1.15,
        ))

    for _ in range(SHIP_EXPLOSION_SPARK_COUNT):
        angle = random.uniform(-math.pi * 0.95, -math.pi * 0.05)
        speed = random.uniform(SHIP_EXPLOSION_SPARK_BURST_MIN, SHIP_EXPLOSION_SPARK_BURST_MAX)
        sparks.append(Spark(
            ship_x, ship_y + 0.5, angle, speed, random.randint(6, 8),
        ))

    for _ in range(SHIP_EXPLOSION_DEBRIS_COUNT):
        rgb = random.choice((SHIP_RGB, SHIP_NOSE_RGB, (255, 120, 40), (255, 220, 120)))
        particles.append(DebrisParticle(
            ship_x + random.uniform(-1.5, 1.5),
            ship_y + random.uniform(-0.5, 1.0),
            rgb[0], rgb[1], rgb[2],
            random.uniform(-SHIP_DEBRIS_SPEED_XY, SHIP_DEBRIS_SPEED_XY),
            random.uniform(-SHIP_DEBRIS_SPEED_Y, 0.8 * 1.15),
        ))


def _destroy_ship_hit_asteroid(asteroid, sparks, particles):
    for _ in range(TINY_ROCK_SPARK_COUNT + 6):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(EXPLOSION_SPARK_SPEED_MIN, EXPLOSION_SPARK_SPEED_MAX * 1.4)
        sparks.append(Spark(asteroid.x, asteroid.y, angle, speed, int(asteroid.size * 1.8)))
    asteroid.alive = False


def _handle_ship_collision(collision, ship_x, ship_y, sparks, particles):
    """Blow up the ship, destroy what it hit, and respawn at center."""
    kind, obj = collision
    _ship_explosion(ship_x, ship_y, sparks, particles)
    if kind == "asteroid":
        _destroy_ship_hit_asteroid(obj, sparks, particles)
    else:
        particles.extend(_enemy_to_particles(obj))
        obj.alive = False
    return WIDTH / 2.0, MAX_ACTIVE_SHOTS


def PlaySkyfall(Duration=10, StopEvent=None):
    global WIDTH, HEIGHT

    WIDTH, HEIGHT = _panel_size()
    ship_y = HEIGHT - SHIP_HEIGHT
    ship_x = WIDTH / 2.0
    ship_steer = {"hunt_x": ship_x, "last_dir": 0}
    ship_respawn_until = 0.0
    shots_ready = MAX_ACTIVE_SHOTS
    crystal_count = 0
    gem_count = 0
    shotgun_until = 0.0
    lightning_until = 0.0
    spark_streams = []

    asteroids = []
    enemies = []
    bullets = []
    crystals = []
    gems = []
    sparks = []
    particles = []
    far_stars, near_stars, giant_layer, _, giant_height = _build_parallax_layers(WIDTH, HEIGHT)
    clock_pixels, clock_displayed_minute, clock_slide = _rebuild_clock_pixels(animate_entrance=False)
    clock_respawn_until = 0.0
    power_was_active = False
    far_scroll = 0.0
    near_scroll = 0.0
    giant_scroll = 0.0
    canvas = LED.TheMatrix.CreateFrameCanvas()

    start_time = time.time()
    last_asteroid_spawn = start_time
    last_enemy_spawn = start_time
    last_fire = start_time
    last_shotgun_fire = start_time
    tick = 0
    score = 0
    last_frame_time = start_time

    print(f"[Skyfall] {WIDTH}x{HEIGHT} — red/blue rocks, loot powers, spark stream")

    try:
        while True:
            if StopEvent and StopEvent.is_set():
                break

            now = time.time()
            frame_dt = now - last_frame_time
            last_frame_time = now
            step = _motion_step(frame_dt)
            if Duration and (now - start_time) / 60.0 >= Duration:
                break

            ship_active = now >= ship_respawn_until

            asteroids = [a for a in asteroids if a.alive and not a.off_screen(WIDTH, HEIGHT)]
            track_asteroids = asteroids

            if ship_active:
                ship_x, _, ship_steer = _update_ship_ai(
                    ship_x, ship_y, crystals, gems, track_asteroids, enemies, WIDTH, HEIGHT,
                    crystal_count=crystal_count, gem_count=gem_count, ship_steer=ship_steer,
                    step=step,
                )

            if now - last_asteroid_spawn >= ASTEROID_SPAWN_INTERVAL:
                _spawn_asteroid(WIDTH, HEIGHT, asteroids)
                last_asteroid_spawn = now

            if now - last_enemy_spawn >= ENEMY_SPAWN_INTERVAL:
                _spawn_enemy(WIDTH, HEIGHT, enemies)
                last_enemy_spawn = now

            gem_count, lightning_until, new_stream = _try_activate_lightning_power(
                gem_count, lightning_until, now, ship_x, ship_y,
                asteroids, enemies, bullets, sparks, particles,
            )
            if new_stream is not None:
                spark_streams.append(new_stream)
            crystal_count, shotgun_until = _try_activate_shotgun_power(
                crystal_count, shotgun_until, now,
            )
            if ship_active and _shotgun_active(shotgun_until, now):
                last_shotgun_fire = _try_shotgun_fire(
                    ship_x, ship_y, bullets, shotgun_until, now, last_shotgun_fire,
                )
            elif ship_active:
                last_fire, shots_ready = _try_hunt_fire(
                    ship_x, ship_y, bullets, track_asteroids, enemies, WIDTH, HEIGHT,
                    now, last_fire, shots_ready,
                )

            for asteroid in asteroids:
                if asteroid.alive:
                    asteroid.move(step)

            _resolve_asteroid_bounces(asteroids)

            for enemy in enemies:
                if enemy.alive:
                    enemy.move(step)

            for bullet in bullets:
                if bullet.alive:
                    bullet.move(step)
                    if bullet.y < -2 or bullet.x < -2 or bullet.x > WIDTH + 2:
                        bullet.alive = False

            for crystal in crystals:
                if crystal.alive:
                    crystal.move(step)
            for gem in gems:
                if gem.alive:
                    gem.move(step)

            _resolve_loot_bounces(crystals + gems, asteroids, WIDTH, HEIGHT)

            new_asteroids, new_sparks, new_crystals, new_gems, new_particles, hit_flashes = _handle_shots(
                asteroids, enemies, bullets,
            )
            asteroids.extend(new_asteroids)
            sparks.extend(new_sparks)
            crystals.extend(new_crystals)
            gems.extend(new_gems)
            particles.extend(new_particles)
            particles.extend(_resolve_enemy_rock_collisions(enemies, asteroids))
            if ship_active:
                crystal_count += _collect_loot(ship_x, ship_y, crystals)
                gem_count += _collect_loot(ship_x, ship_y, gems)
            score += len(hit_flashes)

            for spark in sparks:
                if spark.alive:
                    spark.move(step)
            for particle in particles:
                if particle.alive:
                    particle.move(step)

            asteroids = [a for a in asteroids if a.alive and not a.off_screen(WIDTH, HEIGHT)]
            enemies = [e for e in enemies if e.alive and not e.off_screen(WIDTH, HEIGHT)]
            bullets = [b for b in bullets if b.alive]
            crystals = [c for c in crystals if c.alive and not c.off_screen(WIDTH, HEIGHT)]
            gems = [g for g in gems if g.alive and not g.off_screen(WIDTH, HEIGHT)]
            sparks = [s for s in sparks if s.alive]
            particles = [p for p in particles if p.alive]
            for stream in spark_streams:
                if stream.alive:
                    stream.move(asteroids, enemies, bullets, sparks, particles, step=step)
            spark_streams = [s for s in spark_streams if s.alive]

            power_active = _power_weapon_active(shotgun_until, now, spark_streams)
            clock_slide_offset = _clock_slide_offset(clock_slide, now)
            if power_active and _clock_has_pixels(clock_pixels):
                _resolve_clock_weapon_hits(
                    bullets, spark_streams, clock_pixels, clock_slide_offset,
                )
            if power_was_active and not power_active:
                if _clock_has_pixels(clock_pixels):
                    _shatter_clock_pixels(clock_pixels, particles)
                if not _clock_has_pixels(clock_pixels) and now >= clock_respawn_until:
                    clock_respawn_until = now + CLOCK_RESPAWN_DELAY
            power_was_active = power_active

            if now >= clock_respawn_until and not _clock_has_pixels(clock_pixels):
                clock_pixels, clock_displayed_minute, clock_slide = _rebuild_clock_pixels(
                    animate_entrance=True,
                )

            if ship_active:
                collision = _ship_hit_obstacles(ship_x, ship_y, asteroids, enemies)
                if collision:
                    ship_x, shots_ready = _handle_ship_collision(
                        collision, ship_x, ship_y, sparks, particles,
                    )
                    ship_steer = {"hunt_x": ship_x, "last_dir": 0}
                    bullets = []
                    ship_respawn_until = now + SHIP_RESPAWN_DURATION

            far_scroll = (far_scroll + FAR_SCROLL_SPEED * step) % (len(far_stars) * 1000)
            near_scroll = (near_scroll + NEAR_SCROLL_SPEED * step) % (len(near_stars) * 1000)
            giant_scroll = (giant_scroll + GAS_GIANT_SCROLL_SPEED * step) % (giant_height * 1000)

            canvas.Fill(0, 0, 0)
            display_minute = time.strftime("%H:%M")
            if (
                display_minute != clock_displayed_minute
                and now >= clock_respawn_until
                and _clock_has_pixels(clock_pixels)
            ):
                clock_pixels, clock_displayed_minute, clock_slide = _rebuild_clock_pixels(
                    animate_entrance=False,
                )

            _draw_parallax_background(
                canvas, far_stars, near_stars, giant_layer,
                far_scroll, near_scroll, giant_scroll, tick, clock_pixels,
                clock_slide_offset,
            )
            for asteroid in asteroids:
                if asteroid.alive:
                    asteroid.draw(canvas)
            for enemy in enemies:
                if enemy.alive:
                    enemy.draw(canvas)
            for crystal in crystals:
                if crystal.alive:
                    crystal.draw(canvas, tick)
            for gem in gems:
                if gem.alive:
                    gem.draw(canvas, tick)
            for stream in spark_streams:
                if stream.alive:
                    stream.draw(canvas)
            for bullet in bullets:
                if bullet.alive:
                    bullet.draw(canvas)
            for spark in sparks:
                if spark.alive:
                    spark.draw(canvas)
            for particle in particles:
                if particle.alive:
                    particle.draw(canvas)
            for sx, sy in hit_flashes:
                if 0 <= sx < WIDTH and 0 <= sy < HEIGHT:
                    canvas.SetPixel(sx, sy, 255, 255, 255)
            if ship_active:
                _draw_ship(canvas, ship_x, ship_y)
            _draw_power_hud(canvas, crystal_count, gem_count, shotgun_until, lightning_until, now)

            canvas = LED.TheMatrix.SwapOnVSync(canvas)
            tick += 1

    except KeyboardInterrupt:
        print("[Skyfall] Interrupted")

    LED.ClearBuffers()
    try:
        LED.TheMatrix.SwapOnVSync(LED.Canvas)
    except Exception:
        pass

    print(f"[Skyfall] Score: {score}")


def LaunchSkyfall(Duration=10, ShowIntro=False, StopEvent=None):
    if ShowIntro:
        LED.LoadConfigData()
        LED.ShowTitleScreen(
            BigText="SKY",
            BigTextRGB=LED.HighBlue,
            BigTextShadowRGB=(0, 0, 40),
            LittleText="FALL",
            LittleTextRGB=LED.MedOrange,
            LittleTextShadowRGB=(40, 10, 0),
            ScrollText="Rocks fall. The ship shoots back.",
            ScrollTextRGB=LED.MedYellow,
            ScrollSleep=0.03,
            DisplayTime=1,
            ExitEffect=0,
        )

    LED.ClearBigLED()
    LED.ClearBuffers()
    PlaySkyfall(Duration=Duration, StopEvent=StopEvent)


if __name__ == "__main__":
    LED.Initialize()
    try:
        LaunchSkyfall(Duration=100000, ShowIntro=False, StopEvent=None)
    except KeyboardInterrupt:
        print("Exiting Skyfall.")