#!/usr/bin/env python
#------------------------------------------------------------------------------
#  OUTBREAK4 — Organic blobs on a 2D LED surface
#
#  Particles stick to their own kind and resist others.
#  Each kind has: speed, aggressiveness, hit points, fear sensitivity,
#  desire to split.
#
#  Fear starts at 0 per particle; only rises when attacked.
#  Cross-kind contact battles: winner absorbs loser into its blob.
#  Higher trait speed = faster motion.
#  Timing: one tick per loop (Outbreak style).
#------------------------------------------------------------------------------

from __future__ import print_function

import math
import random
import time
from collections import deque

import numpy as np

import LEDarcade as LED

LED.Initialize()

WIDTH = 64
HEIGHT = 32

if LED.HatWidth != WIDTH or LED.HatHeight != HEIGHT:
    print(
        "[Outbreak4] Panel is {}x{}; playfield is {}x{}".format(
            LED.HatWidth, LED.HatHeight, WIDTH, HEIGHT,
        )
    )
    WIDTH = LED.HatWidth
    HEIGHT = LED.HatHeight

# --- population ---
# Solo demo: fixed pack size — never grow past this
STARTER_BLOB_COUNT = 3
STARTER_BLOB_SIZE = 50
MAX_PARTICLES = STARTER_BLOB_COUNT * STARTER_BLOB_SIZE  # 3 packs, fixed size
MaxTicks = 10 ** 12  # effectively unlimited for long demo runs
# Continuous edge reinforcements (off for clean wander demo)
PARTICLE_SPAWN_ENABLED = False
PARTICLE_SPAWN_INTERVAL_SEC = 2.0
PARTICLE_SPAWN_BATCH = 1

# --- motion (higher speed trait = faster) ---
# Full-speed step per tick (no frame sleeps)
BASE_STEP = 0.45
MIN_SPEED = 0.7
MAX_SPEED = 3.5
WANDER_NOISE = 0.06
CONQUEST_STEP_BOOST = 1.0
SPATIAL_BIN = 4
# Shared pack wander — hold a heading long enough to cross the screen
BLOB_EXPLORE_STRENGTH = 0.90
BLOB_EXPLORE_ARRIVE = 4.0
BLOB_EXPLORE_RETARGET_MIN = 120
BLOB_EXPLORE_RETARGET_MAX = 280
BLOB_EXPLORE_WANDER = 0.006   # tiny noise — no twitchy lead
BLOB_COHERE_STRENGTH = 0.92   # stick hard so it looks like one organism
# Solid body + direction ripple: lead decides, signal hops slowly
BLOB_HEADING_STRENGTH = 0.88
BLOB_CENTROID_PULL = 0.85
BLOB_BODY_RADIUS = 6.5        # soft max distance from pack center (~50 cells)
BLOB_SOLID_EVERY = 1          # enforce 4-connected body every N ticks
BLOB_WAVE_MOVE = True         # lead→tail command ripple (not rigid lockstep)
BLOB_WAVE_HOP_TICKS = 3       # command advances 1 cell every N ticks
BLOB_LEAD_FRAC = 0.16         # front fraction used for wall-bounce priority
BLOB_TURN_RATE = 0.04         # still gradual, but snappier at full speed
BLOB_MAX_TURN_PER_TICK = 0.05 # hard cap — gentle steer, not reverse
BLOB_EXPLORE_MAX_BEARING = 1.0  # rad (~57°) — waypoints only ahead / gentle side
BLOB_WALL_DEFLECT = 0.65      # rad — wall hits nudge heading, never reverse
BLOB_CMD_TURN_THRESH = 0.55   # rad — new cmd_seq only on big intent shifts
BLOB_LEADER_COLOR = (255, 0, 0)  # bright red — sticky particle, not recomputed tip
BLOB_LEADER_STEP_BOOST = 1.85    # leader pulls ahead; body chases
BLOB_FOLLOW_STEP = 1.55          # body keeps up at full speed
BLOB_LEADER_STUCK_TICKS = 8      # re-elect quickly when tip can't step
BLOB_IDLE_TICKS = 40             # no centroid progress → unstuck nudge
BLOB_IDLE_CELL_EPS = 0.25        # centroid shift smaller than this = idle

# --- stickiness / resistance ---
STICK_RADIUS = 8
STICK_STRENGTH = 0.90
ALIGN_STRENGTH = 0.85
REPEL_STRENGTH = 0.70
REPEL_RADIUS = 3

# --- combat (disabled for single-blob wander demo) ---
COMBAT_ENABLED = False
FIGHT_THRESHOLD = 0.12
FIGHT_NOISE = 4.0
FIGHT_DAMAGE_BASE = 2.5
FIGHT_DAMAGE_SCALE = 4.0
CONVERT_CHANCE = 0.55
CHASE_RADIUS = 16
CHASE_STRENGTH = 0.95
CONQUEST_PRIORITY = False
CROWD_FIGHT_BLOB_COUNT = 10
CROWD_CHASE_STRENGTH = 1.0
CROWD_STEP_BOOST = 1.35

# --- death / population pressure (off for clean demo) ---
DEATH_ENABLED = False
STARVE_DAMAGE = 0.04
STARVE_CHECK_RADIUS = 10
OVERCROWD_RATIO = 0.75
OVERCROWD_KILL_CHANCE = 0.012
OLD_AGE_TICKS = 2500
OLD_AGE_KILL_CHANCE = 0.008

# --- fear ---
FEAR_RADIUS = 12
FEAR_STRENGTH_SCALE = 0.80
FEAR_ON_ATTACK = 0.40
FEAR_DECAY = 0.012
FEAR_MAX = 1.0

# --- split (off for single-blob demo) ---
SPLIT_ENABLED = False
SPLIT_MIN_MASS = 5
SPLIT_CHECK_INTERVAL_SEC = 1.5
SPLIT_ROLL_SCALE = 1.6
BLOB_MAX_MASS = 100
BLOB_SIZE_SPLIT_COOLOFF_SEC = 20.0

# --- food (off so the pack just wanders) ---
FOOD_ENABLED = False
FOOD_COLOR = (90, 90, 25)
FOOD_SPAWN_INTERVAL_SEC = 6.0
FOOD_CLUMP_MIN = 2
FOOD_CLUMP_MAX = 6
FOOD_MAX_CELLS = 120
FOOD_SENSE_RADIUS = 22
FOOD_SEEK_STRENGTH = 0.90
FOOD_HUNGER_HP_FRAC = 0.95
FOOD_START_HP_FRAC = 1.0          # full health; not food-seeking
FOOD_DESPERATE_HP_FRAC = 0.25
FOOD_HEAL = 3.5
FOOD_STARTER_CLUMPS = 0

# --- spawn spacing ---
SPAWN_MIN_GAP = 1

TWO_PI = math.pi * 2.0


def normalize_angle(a):
    a = a % TWO_PI
    if a < 0:
        a += TWO_PI
    return a


def blend_angle(current, target, strength):
    delta = (target - current + math.pi) % TWO_PI - math.pi
    return normalize_angle(current + delta * strength)


def angle_delta(a, b):
    """Signed shortest delta from a to b in (-pi, pi]."""
    return (b - a + math.pi) % TWO_PI - math.pi


def steer_heading(current, desired, max_turn, ease=1.0):
    """
    Gently steer current toward desired.
    Never turns more than max_turn radians in one step (no 180 flips).
    """
    delta = angle_delta(current, desired)
    # Ease first, then hard-cap so even large desired errors only nudge
    delta *= clamp(ease, 0.0, 1.0)
    if delta > max_turn:
        delta = max_turn
    elif delta < -max_turn:
        delta = -max_turn
    return normalize_angle(current + delta)


def clamp(v, lo, hi):
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


def mutate_color(rgb):
    """Slightly different color for a size-cap split offspring."""
    r, g, b = rgb

    def nudge(c, amount=None):
        if amount is None:
            amount = random.randint(-60, 60)
        return max(25, min(255, int(c) + amount))

    nr, ng, nb = nudge(r), nudge(g), nudge(b)
    if abs(nr - r) + abs(ng - g) + abs(nb - b) < 45:
        ch = random.randrange(3)
        boost = random.choice((-75, 75))
        if ch == 0:
            nr = nudge(r, boost)
        elif ch == 1:
            ng = nudge(g, boost)
        else:
            nb = nudge(b, boost)
    return (nr, ng, nb)


#------------------------------------------------------------------------------
#  Kind — species traits
#------------------------------------------------------------------------------

class Kind(object):
    __slots__ = (
        "kind_id", "name", "color",
        "speed", "aggressiveness", "max_hp", "fear_sensitivity", "desire_to_split",
    )

    def __init__(
        self, kind_id, name, color,
        speed, aggressiveness, max_hp, fear_sensitivity, desire_to_split,
    ):
        self.kind_id = kind_id
        self.name = name
        self.color = color
        self.speed = clamp(float(speed), MIN_SPEED, MAX_SPEED)
        self.aggressiveness = clamp(float(aggressiveness), 0.0, 1.0)
        self.max_hp = max(1.0, float(max_hp))
        # How strongly this kind reacts once fear is gained (not starting fear)
        self.fear_sensitivity = clamp(float(fear_sensitivity), 0.0, 1.0)
        self.desire_to_split = clamp(float(desire_to_split), 0.0, 1.0)


def default_kinds():
    """Three distinct personalities. Fear always starts at 0 on particles."""
    return [
        Kind(
            0, "Swift", (0, 200, 80),
            speed=3.0, aggressiveness=0.80, max_hp=8.0,
            fear_sensitivity=0.65, desire_to_split=0.55,
        ),
        Kind(
            1, "Brute", (200, 40, 40),
            speed=2.2, aggressiveness=0.98, max_hp=16.0,
            fear_sensitivity=0.15, desire_to_split=0.35,
        ),
        Kind(
            2, "Fission", (40, 80, 220),
            speed=2.6, aggressiveness=0.85, max_hp=11.0,
            fear_sensitivity=0.40, desire_to_split=0.95,
        ),
    ]


#------------------------------------------------------------------------------
#  Particle / Blob
#------------------------------------------------------------------------------

class Particle(object):
    __slots__ = (
        "pid", "x", "y", "px", "py", "angle", "kind_id", "blob_id",
        "hp", "alive", "fear", "age", "_hunting", "_crowd_fight",
        "wave_seq", "fx", "fy",  # command ripple + local step accumulators
        "is_leader",
    )

    def __init__(self, pid, x, y, kind_id, max_hp, angle=None):
        self.pid = pid
        self.x = x
        self.y = y
        self.px = float(x) + random.uniform(0.2, 0.8)
        self.py = float(y) + random.uniform(0.2, 0.8)
        self.angle = normalize_angle(angle if angle is not None else random.uniform(0, TWO_PI))
        self.kind_id = kind_id
        self.blob_id = None
        # Start hungry so packs hunt food immediately
        self.hp = float(max_hp) * FOOD_START_HP_FRAC
        self.alive = True
        self.fear = 0.0  # only rises when attacked
        self.age = 0
        self._hunting = False
        self._crowd_fight = False
        self.wave_seq = 0
        self.fx = 0.0
        self.fy = 0.0
        self.is_leader = False


class Blob(object):
    __slots__ = (
        "blob_id", "kind_id", "mass",
        "explore_tx", "explore_ty", "explore_timer",
        "cx", "cy", "heading",
        "cmd_seq",  # increments when lead commits a new direction
        "leader_pid",  # current leader particle (bright red)
        "leader_stuck",  # consecutive failed leader moves
        "idle_ticks",  # pack not making progress
        "last_prog_cx", "last_prog_cy",
    )

    def __init__(self, blob_id, kind_id):
        self.blob_id = blob_id
        self.kind_id = kind_id
        self.mass = 0
        self.explore_tx = None
        self.explore_ty = None
        self.explore_timer = 0
        self.cx = None
        self.cy = None
        self.heading = None
        self.cmd_seq = 1
        self.leader_pid = None
        self.leader_stuck = 0
        self.idle_ticks = 0
        self.last_prog_cx = None
        self.last_prog_cy = None


#------------------------------------------------------------------------------
#  Playfield
#------------------------------------------------------------------------------

class Playfield(object):
    def __init__(self, kinds=None):
        self.width = WIDTH
        self.height = HEIGHT
        self.grid = np.full((HEIGHT, WIDTH), -1, dtype=np.int32)
        self.rgb = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        self.kinds = list(kinds if kinds is not None else default_kinds())
        self.particles = {}
        self.blobs = {}
        self.food = set()  # (x, y) food cells — clumpy organic pellets
        self._next_pid = 1
        self._next_blob_id = 1
        self.tick = 0
        self._last_split_check = time.time()
        self._last_food_spawn = time.time()
        self._last_particle_spawn = time.time()
        self._particle_spawn_index = 0
        # Dirty cells for fast SetPixel (only paint what changed)
        self._dirty = set()
        self._food_dirty = True
        self._spatial = {}  # rebuilt each step
        # frozenset({blob_a, blob_b}) -> expire timestamp (no fight, only avoid)
        self._cooloff_pairs = {}

    def kind(self, kind_id):
        return self.kinds[kind_id]

    # --- paint ---
    def _paint(self, y, x, color):
        r, g, b = color[0], color[1], color[2]
        if (
            self.rgb[y, x, 0] != r
            or self.rgb[y, x, 1] != g
            or self.rgb[y, x, 2] != b
        ):
            self.rgb[y, x, 0] = r
            self.rgb[y, x, 1] = g
            self.rgb[y, x, 2] = b
            self._dirty.add((x, y))

    def _clear_cell(self, y, x):
        """Free grid cell and blank the LED (must dirty-track or trails fill the panel)."""
        self.grid[y, x] = -1
        if (x, y) in self.food:
            self._paint(y, x, FOOD_COLOR)
        else:
            # Go through _paint so hardware SetPixel actually clears the pixel
            self._paint(y, x, (0, 0, 0))

    def _paint_food_layer(self):
        if not FOOD_ENABLED:
            return
        for (x, y) in self.food:
            if self.grid[y, x] == -1:
                self._paint(y, x, FOOD_COLOR)
        self._food_dirty = False

    def _paint_particle(self, p):
        k = self.kind(p.kind_id)
        # Front tip of the blob reads as bright red leader
        if p.is_leader:
            c = BLOB_LEADER_COLOR
        else:
            c = k.color
        self.grid[p.y, p.x] = p.pid
        self._paint(p.y, p.x, c)

    # --- spawn ---
    def _cell_free(self, x, y):
        return 0 <= x < self.width and 0 <= y < self.height and self.grid[y, x] == -1

    def _cell_isolated(self, x, y, gap=SPAWN_MIN_GAP):
        for dy in range(-gap, gap + 1):
            for dx in range(-gap, gap + 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    if self.grid[ny, nx] != -1:
                        return False
        return True

    def _spawn(self, x, y, kind_id, angle=None, blob_id=None):
        if not self._cell_free(x, y):
            return None
        if len(self.particles) >= MAX_PARTICLES:
            return None
        k = self.kind(kind_id)
        pid = self._next_pid
        self._next_pid += 1
        p = Particle(pid, x, y, kind_id, k.max_hp, angle=angle)
        if blob_id is None:
            bid = self._next_blob_id
            self._next_blob_id += 1
            blob = Blob(bid, kind_id)
            blob.mass = 1
            blob.leader_pid = pid  # founding cell is sticky leader
            self.blobs[bid] = blob
            p.blob_id = bid
            p.is_leader = True
        else:
            p.blob_id = blob_id
            blob = self.blobs.get(blob_id)
            if blob is not None:
                blob.mass += 1
                if blob.leader_pid is None:
                    blob.leader_pid = pid
                    p.is_leader = True
        self.particles[pid] = p
        self._paint_particle(p)
        return p

    def _spawn_small_blob(self, kind_id, size):
        """Grow a connected clump of same-kind particles as one blob."""
        # Pick a center with room for a small pack
        cx = cy = None
        for _ in range(60):
            x = random.randrange(3, max(4, self.width - 3))
            y = random.randrange(2, max(3, self.height - 2))
            if self._cell_free(x, y):
                cx, cy = x, y
                break
        if cx is None:
            return 0
        angle = random.uniform(0, TWO_PI)
        first = self._spawn(cx, cy, kind_id, angle=angle)
        if first is None:
            return 0
        bid = first.blob_id
        cells = [(cx, cy)]
        placed = 1
        attempts = 0
        while placed < size and attempts < size * 25:
            attempts += 1
            bx, by = random.choice(cells)
            dx, dy = random.choice((
                (-1, 0), (1, 0), (0, -1), (0, 1),
                (-1, -1), (-1, 1), (1, -1), (1, 1),
            ))
            nx, ny = bx + dx, by + dy
            if not self._cell_free(nx, ny):
                continue
            p = self._spawn(nx, ny, kind_id, angle=angle + random.uniform(-0.4, 0.4), blob_id=bid)
            if p is not None:
                cells.append((nx, ny))
                placed += 1
        # Sticky leader = front edge along spawn heading (not the center seed cell)
        blob = self.blobs.get(bid)
        if blob is not None:
            members = self._blob_members(bid)
            if members:
                hx = math.cos(angle)
                hy = math.sin(angle)
                tip = max(members, key=lambda p: p.x * hx + p.y * hy)
                for p in members:
                    if p.is_leader and p.pid != tip.pid:
                        p.is_leader = False
                        self._paint_particle(p)
                tip.is_leader = True
                blob.leader_pid = tip.pid
                blob.heading = angle
                self._paint_particle(tip)
        return placed

    def seed(self, count=None):
        """Seed starter blob(s) — default: one 25-cell pack to wander the dish."""
        placed = 0
        n_kinds = len(self.kinds)
        n_blobs = STARTER_BLOB_COUNT
        size = STARTER_BLOB_SIZE
        for i in range(n_blobs):
            kind_id = i % n_kinds
            n = self._spawn_small_blob(kind_id, size)
            placed += n
        # Give each blob a shared wander target
        for blob in self.blobs.values():
            self._pick_blob_explore(blob)
        if FOOD_ENABLED:
            for _ in range(FOOD_STARTER_CLUMPS):
                self._spawn_food_clump()
            self._last_food_spawn = time.time()
        self._last_particle_spawn = time.time()
        print(
            "[Outbreak4] Seeded {} blob(s), {} particles, food={}".format(
                len(self.blobs), placed, len(self.food),
            )
        )
        return placed

    def _pick_blob_explore(self, blob):
        """Shared roam waypoint — only ahead / gentle side, never behind."""
        members = [
            p for p in self.particles.values()
            if p.alive and p.blob_id == blob.blob_id
        ]
        if members:
            cx = sum(p.px for p in members) / len(members)
            cy = sum(p.py for p in members) / len(members)
        else:
            cx = self.width * 0.5
            cy = self.height * 0.5
        heading = blob.heading if blob.heading is not None else random.uniform(0, TWO_PI)

        for _ in range(24):
            # Sample mostly forward cone around current heading
            bearing = random.uniform(-BLOB_EXPLORE_MAX_BEARING, BLOB_EXPLORE_MAX_BEARING)
            dist = random.uniform(10.0, 30.0)
            ang = normalize_angle(heading + bearing)
            tx = clamp(cx + math.cos(ang) * dist, 2.0, self.width - 2.0)
            ty = clamp(cy + math.sin(ang) * dist, 2.0, self.height - 2.0)
            if (tx - cx) ** 2 + (ty - cy) ** 2 < 64:
                continue
            # Reject anything behind the pack
            to_ang = math.atan2(ty - cy, tx - cx)
            if abs(angle_delta(heading, to_ang)) > BLOB_EXPLORE_MAX_BEARING:
                continue
            blob.explore_tx = tx
            blob.explore_ty = ty
            blob.explore_timer = random.randint(
                BLOB_EXPLORE_RETARGET_MIN, BLOB_EXPLORE_RETARGET_MAX,
            )
            return
        # Fallback: straight ahead
        dist = 18.0
        blob.explore_tx = clamp(cx + math.cos(heading) * dist, 2.0, self.width - 2.0)
        blob.explore_ty = clamp(cy + math.sin(heading) * dist, 2.0, self.height - 2.0)
        blob.explore_timer = random.randint(
            BLOB_EXPLORE_RETARGET_MIN, BLOB_EXPLORE_RETARGET_MAX,
        )

    # --- food ---
    def _spawn_food_clump(self):
        """Place a connected clump of 1–5 food pixels on free cells."""
        if not FOOD_ENABLED:
            return 0
        if len(self.food) >= FOOD_MAX_CELLS:
            return 0
        size = random.randint(FOOD_CLUMP_MIN, FOOD_CLUMP_MAX)
        size = min(size, FOOD_MAX_CELLS - len(self.food))
        # Seed center on empty open cell
        cx = cy = None
        for _ in range(50):
            x = random.randrange(self.width)
            y = random.randrange(self.height)
            if self.grid[y, x] == -1 and (x, y) not in self.food:
                cx, cy = x, y
                break
        if cx is None:
            return 0
        cells = [(cx, cy)]
        self.food.add((cx, cy))
        # Grow clump with random walks to neighbors (organic blob shape)
        placed = 1
        attempts = 0
        while placed < size and attempts < size * 20:
            attempts += 1
            bx, by = random.choice(cells)
            dx, dy = random.choice(((-1, 0), (1, 0), (0, -1), (0, 1),
                                    (-1, -1), (-1, 1), (1, -1), (1, 1)))
            nx, ny = bx + dx, by + dy
            if not (0 <= nx < self.width and 0 <= ny < self.height):
                continue
            if self.grid[ny, nx] != -1 or (nx, ny) in self.food:
                continue
            self.food.add((nx, ny))
            cells.append((nx, ny))
            placed += 1
        self._paint_food_layer()
        return placed

    def _spawn_food_tick(self):
        if not FOOD_ENABLED:
            return
        now = time.time()
        if now - self._last_food_spawn < FOOD_SPAWN_INTERVAL_SEC:
            return
        self._last_food_spawn = now
        # Sometimes drop two clumps for chaos
        n = self._spawn_food_clump()
        if random.random() < 0.45:
            n += self._spawn_food_clump()
        if n > 0:
            self._food_dirty = True

    def _random_edge_cell(self):
        """Free rim cell + inward heading so reinforcements enter the dish."""
        for _ in range(50):
            edge = random.randrange(4)
            if edge == 0:
                x, y = random.randrange(self.width), 0
                ang = random.uniform(0.2, math.pi - 0.2)
            elif edge == 1:
                x, y = random.randrange(self.width), self.height - 1
                ang = random.uniform(-math.pi + 0.2, -0.2)
            elif edge == 2:
                x, y = 0, random.randrange(self.height)
                ang = random.uniform(-math.pi * 0.45, math.pi * 0.45)
            else:
                x, y = self.width - 1, random.randrange(self.height)
                ang = normalize_angle(math.pi + random.uniform(-math.pi * 0.45, math.pi * 0.45))
            if self.grid[y, x] == -1 and (x, y) not in self.food:
                return x, y, ang
        return None

    def _spawn_particle_tick(self):
        """Edge reinforcements keep the dish lively."""
        if not PARTICLE_SPAWN_ENABLED:
            return
        now = time.time()
        if now - self._last_particle_spawn < PARTICLE_SPAWN_INTERVAL_SEC:
            return
        self._last_particle_spawn = now
        n_kinds = len(self.kinds)
        for _ in range(PARTICLE_SPAWN_BATCH):
            if len(self.particles) >= MAX_PARTICLES:
                break
            edge = self._random_edge_cell()
            if edge is None:
                break
            x, y, ang = edge
            kind_id = self._particle_spawn_index % n_kinds
            self._particle_spawn_index += 1
            p = self._spawn(x, y, kind_id, angle=ang)
            if p is not None:
                p.px = float(x) + 0.5 + math.cos(ang) * 0.2
                p.py = float(y) + 0.5 + math.sin(ang) * 0.2

    def _nearest_food(self, p, radius=FOOD_SENSE_RADIUS):
        """Return (fx, fy, dist) of nearest food within radius, or None."""
        if not FOOD_ENABLED or not self.food:
            return None
        best = None
        best_d2 = float(radius * radius)
        x0, y0 = p.x, p.y
        # food set is usually small — scan it directly (cheaper than grid radius)
        for (fx, fy) in self.food:
            dx = fx - x0
            dy = fy - y0
            d2 = dx * dx + dy * dy
            if d2 <= best_d2:
                best_d2 = d2
                best = (fx + 0.5, fy + 0.5, math.sqrt(d2) if d2 > 0 else 0.0)
        return best

    def _is_hungry(self, p):
        k = self.kind(p.kind_id)
        return p.hp < k.max_hp * FOOD_HUNGER_HP_FRAC

    def _try_eat_food(self, p):
        key = (p.x, p.y)
        if key not in self.food:
            return False
        self.food.discard(key)
        k = self.kind(p.kind_id)
        p.hp = min(k.max_hp, p.hp + FOOD_HEAL)
        self._paint_particle(p)
        self._food_dirty = True
        return True

    # --- kill / damage ---
    def _kill(self, p):
        if not p.alive:
            return
        p.alive = False
        self._clear_cell(p.y, p.x)
        bid = p.blob_id
        if p.pid in self.particles:
            del self.particles[p.pid]
        if bid is not None and bid in self.blobs:
            self.blobs[bid].mass = max(0, self.blobs[bid].mass - 1)
            if self.blobs[bid].mass <= 0:
                del self.blobs[bid]

    def _damage(self, p, amount):
        if not p.alive:
            return
        p.hp -= amount
        if p.hp <= 0:
            self._kill(p)
        else:
            self._paint_particle(p)

    def _raise_fear(self, p, amount=None):
        """Fear only appears after being attacked."""
        if not p.alive:
            return
        k = self.kind(p.kind_id)
        bump = FEAR_ON_ATTACK if amount is None else amount
        bump *= (0.4 + 0.6 * k.fear_sensitivity)
        p.fear = clamp(p.fear + bump, 0.0, FEAR_MAX)

    def _raise_fear_on_blob(self, blob_id, exclude_pid=None):
        if blob_id is None:
            return
        for p in self.particles.values():
            if not p.alive or p.blob_id != blob_id:
                continue
            if exclude_pid is not None and p.pid == exclude_pid:
                continue
            self._raise_fear(p)

    def _combat_power(self, p):
        k = self.kind(p.kind_id)
        blob = self.blobs.get(p.blob_id)
        mass = blob.mass if blob else 1
        return (
            k.aggressiveness * 10.0
            + p.hp * 0.5
            + mass * 1.2
            + k.speed * 1.5
            + random.uniform(0, FIGHT_NOISE)
        )

    def _set_cooloff(self, blob_a, blob_b, seconds=BLOB_SIZE_SPLIT_COOLOFF_SEC):
        if blob_a is None or blob_b is None or blob_a == blob_b:
            return
        key = frozenset((blob_a, blob_b))
        self._cooloff_pairs[key] = time.time() + seconds

    def _in_cooloff(self, blob_a, blob_b):
        if blob_a is None or blob_b is None or blob_a == blob_b:
            return False
        key = frozenset((blob_a, blob_b))
        exp = self._cooloff_pairs.get(key)
        if exp is None:
            return False
        if time.time() >= exp:
            del self._cooloff_pairs[key]
            return False
        return True

    def _in_cooloff_any(self, p):
        """True if this particle's blob has any active cooloff partner nearby (used for flee)."""
        if p.blob_id is None or not self._cooloff_pairs:
            return False
        now = time.time()
        for key, exp in self._cooloff_pairs.items():
            if exp > now and p.blob_id in key:
                return True
        return False

    def _prune_cooloff(self):
        now = time.time()
        dead = [k for k, exp in self._cooloff_pairs.items() if now >= exp]
        for k in dead:
            del self._cooloff_pairs[k]

    def _new_mutant_kind(self, parent_kind):
        """Register a new kind with a different color (size-cap fission)."""
        kid = len(self.kinds)
        color = mutate_color(parent_kind.color)
        nk = Kind(
            kid,
            parent_kind.name + str(kid),
            color,
            speed=parent_kind.speed * random.uniform(0.9, 1.1),
            aggressiveness=clamp(
                parent_kind.aggressiveness + random.uniform(-0.1, 0.1), 0.0, 1.0,
            ),
            max_hp=parent_kind.max_hp,
            fear_sensitivity=parent_kind.fear_sensitivity,
            desire_to_split=parent_kind.desire_to_split,
        )
        self.kinds.append(nk)
        return nk

    def _convert_particle(self, loser, winner):
        """Winner absorbs loser into its blob/kind (battle spoils)."""
        if not loser.alive or not winner.alive:
            return
        if loser.pid == winner.pid:
            return
        # Cooloff packs do not convert each other
        if self._in_cooloff(loser.blob_id, winner.blob_id):
            return
        old_blob = loser.blob_id
        # Survivors of the attacked pack get scared
        self._raise_fear_on_blob(old_blob, exclude_pid=loser.pid)

        wk = self.kind(winner.kind_id)
        loser.kind_id = winner.kind_id
        loser.blob_id = winner.blob_id
        loser.fear = 0.0  # new allegiance — fear resets
        loser.hp = min(wk.max_hp, max(loser.hp, wk.max_hp * 0.4))
        loser.angle = blend_angle(loser.angle, winner.angle, 0.5)
        self._paint_particle(loser)

        # Fix blob masses
        if old_blob is not None and old_blob in self.blobs and old_blob != winner.blob_id:
            self.blobs[old_blob].mass = max(0, self.blobs[old_blob].mass - 1)
            if self.blobs[old_blob].mass <= 0:
                del self.blobs[old_blob]
        wb = self.blobs.get(winner.blob_id)
        if wb is not None:
            wb.mass += 1
            wb.kind_id = winner.kind_id
            # Enforce hard size cap after growth
            if wb.mass > BLOB_MAX_MASS:
                self._split_oversize_blob(winner.blob_id)

    # --- blob membership ---
    def _merge_blobs(self, a_id, b_id):
        if a_id == b_id:
            return a_id
        a = self.blobs.get(a_id)
        b = self.blobs.get(b_id)
        if a is None:
            return b_id
        if b is None:
            return a_id
        if a.kind_id != b.kind_id:
            return a_id
        # Fold b into a
        for p in self.particles.values():
            if p.alive and p.blob_id == b_id:
                p.blob_id = a_id
        a.mass += b.mass
        del self.blobs[b_id]
        return a_id

    def _join_same_kind(self, a, b):
        if a.kind_id != b.kind_id:
            return
        if a.blob_id is None or b.blob_id is None:
            return
        if a.blob_id == b.blob_id:
            return
        # Prefer larger blob as winner id
        ba = self.blobs.get(a.blob_id)
        bb = self.blobs.get(b.blob_id)
        if ba is None or bb is None:
            return
        if ba.mass >= bb.mass:
            self._merge_blobs(a.blob_id, b.blob_id)
        else:
            self._merge_blobs(b.blob_id, a.blob_id)

    def _sync_blob_masses(self):
        counts = {}
        for p in self.particles.values():
            if p.alive and p.blob_id is not None:
                counts[p.blob_id] = counts.get(p.blob_id, 0) + 1
        dead = []
        for bid, blob in self.blobs.items():
            m = counts.get(bid, 0)
            blob.mass = m
            if m <= 0:
                dead.append(bid)
        for bid in dead:
            del self.blobs[bid]

    # --- sensing helpers ---
    def _rebuild_spatial(self):
        """Bin particles for local neighbor queries (O(n + k) per query)."""
        bins = {}
        bs = SPATIAL_BIN
        for other in self.particles.values():
            if not other.alive:
                continue
            key = (other.x // bs, other.y // bs)
            bucket = bins.get(key)
            if bucket is None:
                bins[key] = [other]
            else:
                bucket.append(other)
        self._spatial = bins

    def _neighbors(self, p, radius):
        """Yield (other, dx, dy, dist2) using spatial bins — not full O(n) scan."""
        r2 = float(radius * radius)
        bs = SPATIAL_BIN
        br = int(radius) // bs + 1
        bx = p.x // bs
        by = p.y // bs
        px, py = p.x, p.y
        bins = self._spatial
        for iy in range(by - br, by + br + 1):
            for ix in range(bx - br, bx + br + 1):
                bucket = bins.get((ix, iy))
                if not bucket:
                    continue
                for other in bucket:
                    if other.pid == p.pid or not other.alive:
                        continue
                    dx = other.x - px
                    dy = other.y - py
                    d2 = dx * dx + dy * dy
                    if 0 < d2 <= r2:
                        yield other, dx, dy, d2

    def _blob_threat_score(self, kind, other_kind, other_blob_mass):
        """How scary is a rival pack to this kind."""
        return other_kind.aggressiveness * (1.0 + 0.15 * other_blob_mass) * other_kind.speed

    def _crowd_fight_mode(self):
        """Too many blobs on the dish → free-for-all combat mode."""
        return len(self.blobs) > CROWD_FIGHT_BLOB_COUNT

    # --- steering ---
    def _update_blob_explore(self, blob):
        """Advance shared wander target once per tick (not once per particle)."""
        if blob is None:
            return
        if blob.explore_timer > 0:
            blob.explore_timer -= 1
        need = (
            blob.explore_tx is None
            or blob.explore_ty is None
            or blob.explore_timer <= 0
        )
        if not need and blob.explore_tx is not None:
            # Retarget when pack centroid arrives (not each particle)
            members = [
                p for p in self.particles.values()
                if p.alive and p.blob_id == blob.blob_id
            ]
            if members:
                cx = sum(p.px for p in members) / len(members)
                cy = sum(p.py for p in members) / len(members)
                dx = blob.explore_tx - cx
                dy = blob.explore_ty - cy
                if dx * dx + dy * dy <= BLOB_EXPLORE_ARRIVE * BLOB_EXPLORE_ARRIVE:
                    need = True
        if need:
            self._pick_blob_explore(blob)

    def _update_all_blob_explore(self):
        for blob in self.blobs.values():
            self._update_blob_explore(blob)

    def _blob_leader(self, blob, members=None):
        """Sticky leader particle — same cell until it dies."""
        if members is None:
            members = self._blob_members(blob.blob_id)
        if not members:
            return None
        leader = None
        if blob.leader_pid is not None:
            leader = self.particles.get(blob.leader_pid)
        if (
            leader is None
            or not leader.alive
            or leader.blob_id != blob.blob_id
        ):
            # Only reassign on death/missing — pick current front once
            if blob.heading is not None:
                hx = math.cos(blob.heading)
                hy = math.sin(blob.heading)
                leader = max(members, key=lambda p: p.x * hx + p.y * hy)
            else:
                leader = members[0]
            blob.leader_pid = leader.pid
        return leader

    def _update_leader_paint(self, blob, members):
        """Ensure only the sticky leader is bright red."""
        leader = self._blob_leader(blob, members)
        if leader is None:
            return None
        for p in members:
            want = p.pid == leader.pid
            if p.is_leader != want:
                p.is_leader = want
                self._paint_particle(p)
            elif want:
                # Keep red after moves
                if not p.is_leader:
                    p.is_leader = True
                self._paint_particle(p)
        return leader

    def _cache_blob_kinematics(self):
        """Centroid + lead intent heading from sticky leader (not recomputed tip)."""
        for blob in self.blobs.values():
            members = self._blob_members(blob.blob_id)
            if not members:
                blob.cx = blob.cy = blob.heading = None
                continue
            cx = sum(p.px for p in members) / float(len(members))
            cy = sum(p.py for p in members) / float(len(members))
            blob.cx = cx
            blob.cy = cy
            leader = self._blob_leader(blob, members)
            # Steer from the leader cell so the red tip aims the pack
            ox = leader.px if leader is not None else cx
            oy = leader.py if leader is not None else cy
            if blob.explore_tx is not None and blob.explore_ty is not None:
                desired = math.atan2(
                    blob.explore_ty - oy, blob.explore_tx - ox,
                )
            else:
                sc = sum(math.cos(p.angle) for p in members)
                ss = sum(math.sin(p.angle) for p in members)
                desired = math.atan2(ss, sc) if (sc or ss) else 0.0
            desired = normalize_angle(
                desired + random.uniform(-BLOB_EXPLORE_WANDER, BLOB_EXPLORE_WANDER),
            )
            if blob.heading is None:
                blob.heading = desired
                blob.cmd_seq = max(1, blob.cmd_seq)
            else:
                # If explore is behind, fold it into a gentle side bearing (no reverse)
                err = angle_delta(blob.heading, desired)
                if abs(err) > BLOB_EXPLORE_MAX_BEARING:
                    desired = normalize_angle(
                        blob.heading + (
                            BLOB_EXPLORE_MAX_BEARING
                            if err > 0 else -BLOB_EXPLORE_MAX_BEARING
                        ),
                    )
                turn = abs(angle_delta(blob.heading, desired))
                if turn >= BLOB_CMD_TURN_THRESH:
                    blob.cmd_seq += 1
                # Gentle steer only — hard-capped turn rate, never 180
                blob.heading = steer_heading(
                    blob.heading, desired,
                    BLOB_MAX_TURN_PER_TICK, ease=BLOB_TURN_RATE / 0.028,
                )

    def _blob_members(self, blob_id):
        return [
            p for p in self.particles.values()
            if p.alive and p.blob_id == blob_id
        ]

    def _blob_cell_map(self, members):
        return dict(((p.x, p.y), p) for p in members)

    def _propagate_blob_wave(self, blob, members):
        """Sticky leader injects heading; copies hop 1 cell every BLOB_WAVE_HOP_TICKS."""
        if blob.heading is None or not members:
            return
        leader = self._update_leader_paint(blob, members)
        if leader is None:
            return
        hx = math.cos(blob.heading)
        hy = math.sin(blob.heading)

        # Only the sticky leader originates the command (no frontmost hopping)
        leader.angle = blob.heading
        leader.wave_seq = blob.cmd_seq

        # Wave only advances one hop every N ticks
        if self.tick % BLOB_WAVE_HOP_TICKS != 0:
            return

        # Snapshot: adopt angle from best upstream neighbor (max seq, then nearer leader)
        cell_map = self._blob_cell_map(members)
        lx, ly = leader.x, leader.y
        new_seq = {}
        new_ang = {}
        for p in members:
            best_seq = p.wave_seq
            best_ang = p.angle
            best_d2 = (p.x - lx) * (p.x - lx) + (p.y - ly) * (p.y - ly)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = cell_map.get((p.x + dx, p.y + dy))
                if n is None:
                    continue
                n_d2 = (n.x - lx) * (n.x - lx) + (n.y - ly) * (n.y - ly)
                if n.wave_seq > best_seq or (
                    n.wave_seq == best_seq and n.wave_seq >= p.wave_seq and n_d2 < best_d2
                ):
                    if n.wave_seq > best_seq or n_d2 < best_d2:
                        best_seq = n.wave_seq
                        best_ang = n.angle
                        best_d2 = n_d2
            new_seq[p.pid] = best_seq
            new_ang[p.pid] = best_ang
        for p in members:
            if p.pid == leader.pid:
                continue
            if new_seq[p.pid] > p.wave_seq:
                p.wave_seq = new_seq[p.pid]
                p.angle = new_ang[p.pid]
            elif new_seq[p.pid] == p.wave_seq and new_ang[p.pid] != p.angle:
                p.angle = new_ang[p.pid]

    def _try_cell_step(self, p, sx, sy):
        """Move one particle one cardinal cell if free / in-bounds."""
        nx = p.x + sx
        ny = p.y + sy
        if nx < 0 or nx >= self.width or ny < 0 or ny >= self.height:
            return "wall"
        if not self._cell_free(nx, ny) and self.grid[ny, nx] != p.pid:
            return "blocked"
        self._occupy(p, nx, ny)
        return "ok"

    def _blob_follow_tree(self, leader, members):
        """BFS from leader → graph distance + parent (one step closer to leader)."""
        cell_map = self._blob_cell_map(members)
        dist = {leader.pid: 0}
        parent = {leader.pid: None}
        q = deque([leader])
        while q:
            cur = q.popleft()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = cell_map.get((cur.x + dx, cur.y + dy))
                if n is None or n.pid in dist:
                    continue
                dist[n.pid] = dist[cur.pid] + 1
                parent[n.pid] = cur
                q.append(n)
        return parent, dist

    def _bounce_blob_heading(self, blob, sx, sy):
        """Wall touch: gentle deflect, never reverse 180."""
        h = blob.heading if blob.heading is not None else 0.0
        # Prefer the turn that points more into the open board
        side = 1.0 if random.random() < 0.5 else -1.0
        if blob.cx is not None:
            if sx != 0:
                # Hit left/right wall — bias turn toward vertical free space
                side = 1.0 if blob.cy < self.height * 0.5 else -1.0
            elif sy != 0:
                side = 1.0 if blob.cx < self.width * 0.5 else -1.0
        bounce_dir = normalize_angle(h + side * BLOB_WALL_DEFLECT)
        # Keep explore in the forward cone of the new gentle heading
        blob.cmd_seq += 1
        if blob.cx is not None:
            dist = random.uniform(12.0, 28.0)
            tx = clamp(blob.cx + math.cos(bounce_dir) * dist, 2.0, self.width - 2.0)
            ty = clamp(blob.cy + math.sin(bounce_dir) * dist, 2.0, self.height - 2.0)
            blob.explore_tx = tx
            blob.explore_ty = ty
            blob.explore_timer = random.randint(
                BLOB_EXPLORE_RETARGET_MIN, BLOB_EXPLORE_RETARGET_MAX,
            )

    def _cardinal_from_accum(self, p):
        if abs(p.fx) < 1.0 and abs(p.fy) < 1.0:
            return None
        if abs(p.fx) >= abs(p.fy):
            return (1 if p.fx > 0 else -1, 0)
        return (0, 1 if p.fy > 0 else -1)

    def _apply_step_result(self, p, sx, sy, result, blob, is_leader):
        if result == "ok":
            if sx != 0:
                p.fx -= float(sx)
            if sy != 0:
                p.fy -= float(sy)
            if is_leader:
                self._paint_particle(p)
                blob.leader_stuck = 0
        elif result == "wall":
            if is_leader:
                self._bounce_blob_heading(blob, sx, sy)
            p.fx = 0.0
            p.fy = 0.0
        else:
            if sx != 0:
                p.fx *= 0.35
            if sy != 0:
                p.fy *= 0.35

    def _blob_cell_set(self, members):
        return set((p.x, p.y) for p in members)

    def _is_blob_edge(self, p, cell_set):
        """True if any 4-neighbor is outside the blob (open space or board edge)."""
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (p.x + dx, p.y + dy)
            if n not in cell_set:
                return True
        return False

    def _leader_open_cells(self, leader):
        """Absolute empty cells orthogonally adjacent to the leader."""
        opens = set()
        for sx, sy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = leader.x + sx, leader.y + sy
            if 0 <= nx < self.width and 0 <= ny < self.height:
                if self.grid[ny, nx] == -1:
                    opens.add((nx, ny))
        return opens

    def _leader_free_dirs(self, p, heading):
        """Clear neighboring cells ranked by alignment with heading (best first)."""
        hx = math.cos(heading) if heading is not None else 0.0
        hy = math.sin(heading) if heading is not None else 0.0
        opts = []
        for sx, sy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = p.x + sx, p.y + sy
            if not (0 <= nx < self.width and 0 <= ny < self.height):
                continue
            # Empty cell only
            if self.grid[ny, nx] != -1:
                continue
            align = sx * hx + sy * hy
            opts.append((align, sx, sy, nx, ny))
        opts.sort(key=lambda t: -t[0])
        return opts

    def _preferred_cardinal(self, heading):
        hx = math.cos(heading)
        hy = math.sin(heading)
        if abs(hx) >= abs(hy):
            return (1 if hx >= 0 else -1, 0)
        return (0, 1 if hy >= 0 else -1)

    def _local_3x3_members(self, members, origin):
        """Same-blob cells in the 3x3 around origin (excluding origin itself)."""
        if origin is None:
            return list(members)
        ox, oy = origin.x, origin.y
        local = []
        for p in members:
            if p.pid == origin.pid:
                continue
            if max(abs(p.x - ox), abs(p.y - oy)) <= 1:
                local.append(p)
        return local

    def _elect_new_leader(self, blob, members, old_leader):
        """
        New leader only from 3x3 around current leader, and only edge cells.
        No jumping across the body; no buried interior tip.
        """
        if not members:
            return None
        h = blob.heading if blob.heading is not None else 0.0
        hx = math.cos(h)
        hy = math.sin(h)
        cell_set = self._blob_cell_set(members)

        local = self._local_3x3_members(members, old_leader)
        # Must be on the rim of the blob
        edge_local = [p for p in local if self._is_blob_edge(p, cell_set)]

        scored = []
        for p in edge_local:
            free = self._leader_free_dirs(p, h)
            free_n = len(free)
            best_align = free[0][0] if free else -1.0
            proj = p.x * hx + p.y * hy
            # Prefer open forward exits, then more free sides, then forward position
            scored.append((best_align, free_n, proj, p))
        if not scored:
            # No edge neighbor in 3x3 — keep old if it is still edge; else stay put
            if old_leader is not None and self._is_blob_edge(old_leader, cell_set):
                blob.leader_stuck = 0
                return old_leader
            if old_leader is not None:
                blob.leader_stuck = 0
            return old_leader

        scored.sort(key=lambda t: (t[0], t[1], t[2]), reverse=True)
        new_leader = scored[0][3]

        if old_leader is not None and old_leader.pid == new_leader.pid:
            blob.leader_stuck = 0
            return new_leader

        if old_leader is not None:
            old_leader.is_leader = False
            old_leader.fx = 0.0
            old_leader.fy = 0.0
            self._paint_particle(old_leader)

        new_leader.is_leader = True
        new_leader.angle = h
        new_leader.wave_seq = blob.cmd_seq + 1
        new_leader.fx = 0.0
        new_leader.fy = 0.0
        blob.leader_pid = new_leader.pid
        blob.leader_stuck = 0
        blob.cmd_seq += 1  # new command generation from new tip
        self._paint_particle(new_leader)
        # Nudge explore ahead of the new tip so it has somewhere to go
        dist = random.uniform(12.0, 24.0)
        blob.explore_tx = clamp(
            new_leader.px + math.cos(h) * dist, 2.0, self.width - 2.0,
        )
        blob.explore_ty = clamp(
            new_leader.py + math.sin(h) * dist, 2.0, self.height - 2.0,
        )
        blob.explore_timer = random.randint(
            BLOB_EXPLORE_RETARGET_MIN, BLOB_EXPLORE_RETARGET_MAX,
        )
        return new_leader

    def _move_leader(self, leader, blob, base):
        """
        Keep the leader moving.
        Clear neighbors are always valid exits — step into them; never sit still.
        """
        h = blob.heading if blob.heading is not None else leader.angle
        leader.angle = h
        leader.wave_seq = blob.cmd_seq
        # Idle packs get a temporary boost so they break free
        boost = BLOB_LEADER_STEP_BOOST
        if blob.idle_ticks > BLOB_IDLE_TICKS // 3:
            boost *= 1.8
        lstep = base * boost

        free = self._leader_free_dirs(leader, h)
        pref = self._preferred_cardinal(h)
        free_dirs = [(sx, sy) for (_a, sx, sy, _nx, _ny) in free]
        free_set = set(free_dirs)

        if not free_dirs:
            # Boxed in — stuck; deflect if against a wall
            blob.leader_stuck += 1
            px, py = pref
            nx, ny = leader.x + px, leader.y + py
            if not (0 <= nx < self.width and 0 <= ny < self.height):
                self._bounce_blob_heading(blob, px, py)
            elif self.grid[ny, nx] != -1:
                # Blocked by body/other blob — gentle side turn for next try
                side = 1.0 if random.random() < 0.5 else -1.0
                blob.heading = normalize_angle(h + side * BLOB_WALL_DEFLECT)
            leader.fx = 0.0
            leader.fy = 0.0
            return False

        pref_clear = pref in free_set
        if pref_clear:
            leader.fx += math.cos(h) * lstep
            leader.fy += math.sin(h) * lstep
            move_order = [pref] + [d for d in free_dirs if d != pref]
        else:
            # Open cell exists but not straight ahead — go there now
            _a, bx, by, _nx, _ny = free[0]
            free_ang = math.atan2(float(by), float(bx))
            blob.heading = steer_heading(
                h, free_ang, BLOB_MAX_TURN_PER_TICK * 2.5, ease=1.0,
            )
            leader.angle = blob.heading
            # Force a committed step into clear space (don't wait on slow accum)
            leader.fx = float(bx)
            leader.fy = float(by)
            move_order = free_dirs[:]

        candidates = []
        seen = set()
        step_xy = self._cardinal_from_accum(leader)
        if step_xy is not None and step_xy in free_set:
            candidates.append(step_xy)
            seen.add(step_xy)
        # Always allow immediate escape into any clear neighbor when:
        # - preferred is blocked, or pack is going idle, or accum already full
        force_step = (
            not pref_clear
            or blob.idle_ticks > 10
            or blob.leader_stuck > 0
            or step_xy is not None
        )
        if force_step:
            for d in move_order:
                if d not in seen:
                    candidates.append(d)
                    seen.add(d)

        for sx, sy in candidates:
            result = self._try_cell_step(leader, sx, sy)
            if result == "ok":
                self._apply_step_result(leader, sx, sy, result, blob, True)
                blob.leader_stuck = 0
                return True
            if result == "wall":
                self._bounce_blob_heading(blob, sx, sy)
                continue

        if pref_clear and step_xy is None and not force_step:
            return False  # winding up toward open preferred cell

        if free_dirs:
            bx, by = free_dirs[0]
            leader.fx = float(bx)
            leader.fy = float(by)
            # One more immediate try on best free cell
            result = self._try_cell_step(leader, bx, by)
            if result == "ok":
                self._apply_step_result(leader, bx, by, result, blob, True)
                blob.leader_stuck = 0
                return True
            blob.leader_stuck = max(0, blob.leader_stuck - 1)
            return False

        blob.leader_stuck += 1
        return False

    def _ensure_leader_on_edge(self, blob, members, leader):
        """If leader is buried inside the body, hand off to a 3x3 edge neighbor."""
        if leader is None:
            return None
        cell_set = self._blob_cell_set(members)
        if self._is_blob_edge(leader, cell_set):
            return leader
        return self._elect_new_leader(blob, members, leader)

    def _nudge_blob_unstuck(self, blob, members, leader):
        """Pack has not progressed — re-aim and hand tip to a mobile edge cell."""
        h = blob.heading if blob.heading is not None else 0.0
        side = 1.0 if random.random() < 0.5 else -1.0
        blob.heading = normalize_angle(h + side * BLOB_WALL_DEFLECT)
        blob.cmd_seq += 1
        self._pick_blob_explore(blob)
        blob.idle_ticks = 0
        blob.leader_stuck = 0
        new_leader = self._elect_new_leader(blob, members, leader)
        return new_leader if new_leader is not None else leader

    def _track_blob_progress(self, blob, members):
        """Update idle counter from centroid motion."""
        if not members:
            return
        cx = sum(p.x for p in members) / float(len(members))
        cy = sum(p.y for p in members) / float(len(members))
        if blob.last_prog_cx is None:
            blob.last_prog_cx = cx
            blob.last_prog_cy = cy
            blob.idle_ticks = 0
            return
        dist = abs(cx - blob.last_prog_cx) + abs(cy - blob.last_prog_cy)
        if dist >= BLOB_IDLE_CELL_EPS:
            blob.last_prog_cx = cx
            blob.last_prog_cy = cy
            blob.idle_ticks = 0
        else:
            blob.idle_ticks += 1

    def _move_blob_bodies(self):
        """
        Leader alone steers and moves first in the new direction.
        Blobs must keep progressing — re-elect / re-aim when stuck or idle.
        """
        if not BLOB_WAVE_MOVE:
            return
        for bid, blob in list(self.blobs.items()):
            members = self._blob_members(bid)
            if not members or blob.heading is None:
                continue

            # 1) Leader injects new heading; body receives it on a delay
            self._propagate_blob_wave(blob, members)
            leader = self._blob_leader(blob, members)
            if leader is None:
                continue

            # Must stay on the rim — never a buried interior cell
            leader = self._ensure_leader_on_edge(blob, members, leader)
            if leader is None:
                continue

            k = self.kind(blob.kind_id)
            base = BASE_STEP * max(MIN_SPEED, min(MAX_SPEED, k.speed))

            # Pack-level freeze recovery
            if blob.idle_ticks >= BLOB_IDLE_TICKS:
                leader = self._nudge_blob_unstuck(blob, members, leader)

            # 2) LEADER keeps moving (into clear edge space); re-elect if jammed
            moved = self._move_leader(leader, blob, base)
            if not moved and blob.leader_stuck >= BLOB_LEADER_STUCK_TICKS:
                leader = self._elect_new_leader(blob, members, leader)
                if leader is not None:
                    # Immediate second attempt with new tip
                    self._move_leader(leader, blob, base)

            if leader is None:
                continue

            # Re-check edge after the leader's own step
            leader = self._ensure_leader_on_edge(blob, members, leader)
            if leader is None:
                continue

            # Tree after leader motion
            parent, dist = self._blob_follow_tree(leader, members)
            lx, ly = leader.x, leader.y
            # Protect free faces of the tip so followers can't bury the leader
            leader_opens = self._leader_open_cells(leader)

            # 3) FOLLOWERS — near-leader first; never occupy leader's open edge cells
            followers = [p for p in members if p.pid != leader.pid]
            followers.sort(key=lambda p: dist.get(p.pid, 10 ** 9))

            for p in followers:
                par = parent.get(p.pid)
                if par is not None:
                    tx, ty = par.x, par.y
                else:
                    tx, ty = lx, ly

                follow_ang = math.atan2(
                    float(ty) + 0.5 - p.py,
                    float(tx) + 0.5 - p.px,
                )
                if p.wave_seq >= blob.cmd_seq:
                    aim = blend_angle(follow_ang, p.angle, 0.45)
                elif p.wave_seq > 0:
                    aim = blend_angle(follow_ang, p.angle, 0.25)
                else:
                    aim = follow_ang
                p.angle = aim

                fstep = base * BLOB_FOLLOW_STEP
                p.fx += math.cos(aim) * fstep
                p.fy += math.sin(aim) * fstep
                step_xy = self._cardinal_from_accum(p)
                if step_xy is None:
                    continue
                sx, sy = step_xy
                nx, ny = p.x + sx, p.y + sy

                def _follower_step_ok(ax, ay):
                    tx_, ty_ = p.x + ax, p.y + ay
                    # Do not fill the leader's open perimeter (keeps tip on edge)
                    if (tx_, ty_) in leader_opens:
                        return False
                    return True

                cur_d = abs(p.x - lx) + abs(p.y - ly)
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    new_d = abs(nx - lx) + abs(ny - ly)
                    if new_d > cur_d or not _follower_step_ok(sx, sy):
                        dx = lx - p.x
                        dy = ly - p.y
                        alt = []
                        if dx != 0:
                            alt.append((1 if dx > 0 else -1, 0))
                        if dy != 0:
                            alt.append((0, 1 if dy > 0 else -1))
                        stepped = False
                        for ax, ay in alt:
                            if not _follower_step_ok(ax, ay):
                                continue
                            ad = abs(p.x + ax - lx) + abs(p.y + ay - ly)
                            if ad <= cur_d:
                                result = self._try_cell_step(p, ax, ay)
                                if result == "ok":
                                    self._apply_step_result(p, ax, ay, result, blob, False)
                                    stepped = True
                                    break
                        if not stepped:
                            p.fx *= 0.4
                            p.fy *= 0.4
                        continue
                if not _follower_step_ok(sx, sy):
                    p.fx *= 0.4
                    p.fy *= 0.4
                    continue
                result = self._try_cell_step(p, sx, sy)
                self._apply_step_result(p, sx, sy, result, blob, False)

            # Final edge guard after the body shuffles
            members = self._blob_members(bid)
            leader = self._blob_leader(blob, members)
            self._ensure_leader_on_edge(blob, members, leader)
            # Pack progress — drives idle unstuck if centroid freezes
            self._track_blob_progress(blob, members)

    def _steer(self, p):
        k = self.kind(p.kind_id)
        crowd = self._crowd_fight_mode() if COMBAT_ENABLED else False
        if p.fear > 0:
            decay = FEAR_DECAY * (2.5 if crowd else 1.0)
            p.fear = max(0.0, p.fear - decay)

        # Tiny noise only — independent wander tears the body apart
        p.angle = normalize_angle(
            p.angle + random.uniform(-WANDER_NOISE * 0.35, WANDER_NOISE * 0.35),
        )

        stick_x = stick_y = 0.0
        stick_w = 0.0
        align_c = align_s = 0.0
        align_n = 0
        flee_x = flee_y = 0.0
        flee_w = 0.0
        chase_x = chase_y = 0.0
        chase_w = 0.0

        my_blob = self.blobs.get(p.blob_id)

        for other, dx, dy, d2 in self._neighbors(p, max(STICK_RADIUS, FEAR_RADIUS, CHASE_RADIUS)):
            pdx = other.px - p.px
            pdy = other.py - p.py

            # Only glue to own blob mates (not random same-kind loners)
            same_blob = (
                other.blob_id is not None
                and p.blob_id is not None
                and other.blob_id == p.blob_id
            )
            if same_blob or (other.kind_id == p.kind_id and not COMBAT_ENABLED):
                if d2 <= STICK_RADIUS * STICK_RADIUS:
                    w = 1.0 / max(0.25, d2)
                    stick_x += pdx * w
                    stick_y += pdy * w
                    stick_w += w
                    align_c += math.cos(other.angle)
                    align_s += math.sin(other.angle)
                    align_n += 1
            elif COMBAT_ENABLED and other.kind_id != p.kind_id:
                if self._in_cooloff(p.blob_id, other.blob_id):
                    fw = 2.5 / max(0.35, d2)
                    flee_x -= pdx * fw
                    flee_y -= pdy * fw
                    flee_w += fw
                    continue
                ok = self.kind(other.kind_id)
                if (
                    not crowd
                    and d2 <= FEAR_RADIUS * FEAR_RADIUS
                    and p.fear > 0.05
                ):
                    ob = self.blobs.get(other.blob_id)
                    om = ob.mass if ob else 1
                    threat = self._blob_threat_score(k, ok, om)
                    fw = (p.fear * k.fear_sensitivity * (0.5 + threat)) / max(0.5, d2)
                    flee_x -= pdx * fw
                    flee_y -= pdy * fw
                    flee_w += fw
                can_hunt = crowd or (
                    k.aggressiveness > FIGHT_THRESHOLD and p.fear < 0.70
                )
                if d2 <= CHASE_RADIUS * CHASE_RADIUS and can_hunt:
                    ob = self.blobs.get(other.blob_id)
                    om = ob.mass if ob else 1
                    base_agg = 1.0 if crowd else k.aggressiveness
                    cw = (base_agg * (1.0 + 0.08 * om)) / max(0.35, d2)
                    chase_x += pdx * cw
                    chase_y += pdy * cw
                    chase_w += cw

        # Shared pack heading + centroid pull = one solid organism
        if my_blob is not None:
            if my_blob.heading is not None:
                p.angle = blend_angle(
                    p.angle, my_blob.heading, BLOB_HEADING_STRENGTH,
                )
                p.angle = normalize_angle(
                    p.angle + random.uniform(
                        -BLOB_EXPLORE_WANDER, BLOB_EXPLORE_WANDER,
                    ),
                )
            if my_blob.cx is not None:
                dx = my_blob.cx - p.px
                dy = my_blob.cy - p.py
                dist = math.sqrt(dx * dx + dy * dy)
                if dist > 0.4:
                    pull = BLOB_CENTROID_PULL
                    if dist > BLOB_BODY_RADIUS:
                        pull = 0.98  # hard snap-in if drifting off the body
                    p.angle = blend_angle(
                        p.angle, math.atan2(dy, dx), pull,
                    )

        food_target = None
        desperate = p.hp < k.max_hp * FOOD_DESPERATE_HP_FRAC
        if FOOD_ENABLED and self._is_hungry(p) and not crowd:
            food_target = self._nearest_food(p)
        elif FOOD_ENABLED and self._is_hungry(p) and desperate:
            food_target = self._nearest_food(p)

        hunting = chase_w > 0 and COMBAT_ENABLED
        p._hunting = hunting
        p._crowd_fight = crowd

        if flee_w > 0 and (self._in_cooloff_any(p) or (p.fear > 0.05 and not crowd)):
            p.angle = blend_angle(
                p.angle, math.atan2(flee_y, flee_x),
                FEAR_STRENGTH_SCALE * max(p.fear, 0.5) * (
                    k.fear_sensitivity if not crowd else 0.6
                ),
            )
        elif hunting and (crowd or (CONQUEST_PRIORITY and not desperate)):
            strength = CROWD_CHASE_STRENGTH if crowd else CHASE_STRENGTH * k.aggressiveness
            p.angle = blend_angle(
                p.angle, math.atan2(chase_y, chase_x), strength,
            )
        elif food_target is not None:
            fx, fy, _fd = food_target
            hunger = 1.0 - clamp(p.hp / k.max_hp, 0.0, 1.0)
            strength = FOOD_SEEK_STRENGTH * (0.55 + 0.45 * max(hunger, 0.35))
            p.angle = blend_angle(
                p.angle, math.atan2(fy - p.py, fx - p.px), strength,
            )

        # Local glue — stay packed with neighbors
        if stick_w > 0:
            p.angle = blend_angle(
                p.angle, math.atan2(stick_y, stick_x), BLOB_COHERE_STRENGTH,
            )
        if align_n > 0:
            p.angle = blend_angle(
                p.angle, math.atan2(align_s, align_c), ALIGN_STRENGTH,
            )

    def _clamp(self, p):
        lo = 0.05
        hi_x = self.width - 0.05
        hi_y = self.height - 0.05
        bounced = False
        if p.px < lo:
            p.px = lo
            p.angle = normalize_angle(math.pi - p.angle)
            bounced = True
        elif p.px > hi_x:
            p.px = hi_x
            p.angle = normalize_angle(math.pi - p.angle)
            bounced = True
        if p.py < lo:
            p.py = lo
            p.angle = normalize_angle(-p.angle)
            bounced = True
        elif p.py > hi_y:
            p.py = hi_y
            p.angle = normalize_angle(-p.angle)
            bounced = True
        if bounced:
            p.angle = normalize_angle(p.angle + random.uniform(-0.3, 0.3))

    def _retreat(self, p, hard=False):
        k = self.kind(p.kind_id)
        step = BASE_STEP * k.speed
        mul = 1.4 if hard else 0.7
        p.px -= math.cos(p.angle) * step * mul
        p.py -= math.sin(p.angle) * step * mul
        p.angle = normalize_angle(p.angle + random.uniform(-0.8, 0.8))
        self._clamp(p)

    def _occupy(self, p, nx, ny):
        if not self._cell_free(nx, ny) and self.grid[ny, nx] != p.pid:
            return False
        self._clear_cell(p.y, p.x)
        p.x = nx
        p.y = ny
        self._paint_particle(p)
        self._try_eat_food(p)
        return True

    def _resolve_contact(self, mover, other):
        if mover.kind_id == other.kind_id:
            self._join_same_kind(mover, other)
            # Glue in place — never bounce same-kind apart (that leaves gaps)
            mid = blend_angle(mover.angle, other.angle, 0.5)
            mover.angle = blend_angle(mover.angle, mid, 0.55)
            other.angle = blend_angle(other.angle, mid, 0.55)
            # Keep continuous pos on the occupied cell so it doesn't drift off-body
            mover.px = float(mover.x) + 0.5
            mover.py = float(mover.y) + 0.5
            return "stick"

        mk = self.kind(mover.kind_id)
        ok = self.kind(other.kind_id)
        # Size-cap fission cooloff: no fighting, just avoid
        if self._in_cooloff(mover.blob_id, other.blob_id):
            self._retreat(mover, hard=True)
            other.angle = normalize_angle(
                math.atan2(other.py - mover.py, other.px - mover.px)
                + random.uniform(-0.3, 0.3),
            )
            return "cooloff"

        if not COMBAT_ENABLED:
            self._retreat(mover, hard=True)
            other.angle = normalize_angle(other.angle + random.uniform(-0.5, 0.5))
            return "resist"

        # Battle if aggressive enough — or always when blob count is high
        crowd = self._crowd_fight_mode()
        fight = crowd or (
            mk.aggressiveness >= FIGHT_THRESHOLD
            or ok.aggressiveness >= FIGHT_THRESHOLD
        )
        # High personal fear can refuse (not in crowd free-for-all)
        if fight and not crowd and mover.fear > 0.65:
            fight = False

        if fight:
            # Battle: deal damage; death if HP runs out, else chance to convert
            power_m = self._combat_power(mover)
            power_o = self._combat_power(other)
            if mk.aggressiveness >= ok.aggressiveness:
                self._raise_fear(other)
            else:
                self._raise_fear(mover)

            if power_m >= power_o:
                winner, loser = mover, other
                wk, lk = mk, ok
            else:
                winner, loser = other, mover
                wk, lk = ok, mk

            dmg = FIGHT_DAMAGE_BASE + wk.aggressiveness * FIGHT_DAMAGE_SCALE
            # Crowd free-for-all hits harder (keeps population down)
            if crowd:
                dmg *= 1.35
            self._damage(loser, dmg)
            # Winner takes a smaller scrape
            if winner.alive:
                self._damage(winner, dmg * 0.25)

            if not loser.alive:
                if mover.alive:
                    self._retreat(mover, hard=False)
                return "kill"

            # Loser wounded but alive — absorb or bounce
            if random.random() < CONVERT_CHANCE:
                self._convert_particle(loser, winner)
            else:
                # Failed absorb: extra fear on loser, both bounce
                self._raise_fear(loser, FEAR_ON_ATTACK * 0.5)
            if mover.alive:
                self._retreat(mover, hard=False)
            return "battle"

        # Resist: bounce (no battle)
        self._retreat(mover, hard=True)
        other.angle = normalize_angle(other.angle + random.uniform(-0.5, 0.5))
        return "resist"

    def _apply_natural_death(self, p):
        """Starvation, old age, overcrowding — keeps the dish from packing solid."""
        if not DEATH_ENABLED or not p.alive:
            return
        k = self.kind(p.kind_id)
        p.age += 1

        # Starvation: hungry and no food nearby → drip HP
        if self._is_hungry(p):
            food = self._nearest_food(p, radius=STARVE_CHECK_RADIUS)
            if food is None:
                self._damage(p, STARVE_DAMAGE)
                if not p.alive:
                    return

        n = len(self.particles)
        # Overcrowding cull
        if n >= int(MAX_PARTICLES * OVERCROWD_RATIO):
            # Weaker / more wounded more likely to die
            wound = 1.0 - clamp(p.hp / k.max_hp, 0.0, 1.0)
            chance = OVERCROWD_KILL_CHANCE * (0.5 + wound)
            if n >= MAX_PARTICLES:
                chance *= 2.5
            if random.random() < chance:
                self._kill(p)
                return

        # Old age
        if p.age > OLD_AGE_TICKS and random.random() < OLD_AGE_KILL_CHANCE:
            self._kill(p)

    def _integrate(self, p):
        if not p.alive:
            return
        # Wave blob body is moved in _move_blob_bodies — skip per-cell scramble
        if BLOB_WAVE_MOVE and p.blob_id is not None and p.blob_id in self.blobs:
            self._apply_natural_death(p)
            return
        k = self.kind(p.kind_id)
        self._apply_natural_death(p)
        if not p.alive:
            return
        self._steer(p)
        step = BASE_STEP * k.speed
        # Blobs speed up when on a conquest hunt / crowd free-for-all
        if getattr(p, "_hunting", False):
            step *= CONQUEST_STEP_BOOST
        if getattr(p, "_crowd_fight", False):
            step *= CROWD_STEP_BOOST
        p.px += math.cos(p.angle) * step
        p.py += math.sin(p.angle) * step
        self._clamp(p)

        nx = int(p.px)
        ny = int(p.py)
        if nx < 0 or nx >= self.width or ny < 0 or ny >= self.height:
            return
        if nx == p.x and ny == p.y:
            self._try_eat_food(p)
            return

        if self._cell_free(nx, ny):
            self._occupy(p, nx, ny)
            return

        oid = int(self.grid[ny, nx])
        if oid == p.pid:
            return
        other = self.particles.get(oid)
        if other is None or not other.alive:
            self._clear_cell(ny, nx)
            self._occupy(p, nx, ny)
            return

        self._resolve_contact(p, other)

    # --- split ---
    def _partition_blob_members(self, members):
        """Split members into two non-empty groups along a random axis."""
        if len(members) < 2:
            return None, None
        if random.random() < 0.5:
            members = sorted(members, key=lambda p: p.px)
        else:
            members = sorted(members, key=lambda p: p.py)
        mid = max(1, len(members) // 2)
        if mid >= len(members):
            mid = len(members) - 1
        return members[:mid], members[mid:]

    def _split_oversize_blob(self, bid):
        """Hard cap: mass > BLOB_MAX_MASS → two differently colored blobs + cooloff."""
        blob = self.blobs.get(bid)
        if blob is None or blob.mass <= BLOB_MAX_MASS:
            return None
        members = [
            p for p in self.particles.values()
            if p.alive and p.blob_id == bid
        ]
        if len(members) <= BLOB_MAX_MASS:
            blob.mass = len(members)
            return None
        group_a, group_b = self._partition_blob_members(members)
        if not group_a or not group_b:
            return None

        # Cap: keep group_a on original; group_b becomes new color/kind
        parent_kind = self.kind(blob.kind_id)
        new_kind = self._new_mutant_kind(parent_kind)
        new_bid = self._next_blob_id
        self._next_blob_id += 1
        nb = Blob(new_bid, new_kind.kind_id)
        nb.mass = len(group_b)
        self.blobs[new_bid] = nb

        for p in group_b:
            p.blob_id = new_bid
            p.kind_id = new_kind.kind_id
            # Keep hp in new kind's range
            p.hp = min(new_kind.max_hp, p.hp)
            p.angle = normalize_angle(p.angle + random.uniform(0.8, 1.6))
            self._paint_particle(p)
        for p in group_a:
            p.angle = normalize_angle(p.angle + random.uniform(-1.6, -0.8))
        blob.mass = len(group_a)
        blob.kind_id = parent_kind.kind_id

        # 20s cooloff: no fighting, only avoidance between the two halves
        self._set_cooloff(bid, new_bid, BLOB_SIZE_SPLIT_COOLOFF_SEC)
        return new_bid

    def _enforce_size_caps(self):
        """Split any blob that grew past BLOB_MAX_MASS."""
        for bid in list(self.blobs.keys()):
            blob = self.blobs.get(bid)
            if blob is not None and blob.mass > BLOB_MAX_MASS:
                self._split_oversize_blob(bid)

    def _try_splits(self):
        """Desire-based same-kind fission (smaller organic splits)."""
        if not SPLIT_ENABLED:
            # Still enforce hard size cap if somehow exceeded
            self._enforce_size_caps()
            return
        now = time.time()
        if now - self._last_split_check < SPLIT_CHECK_INTERVAL_SEC:
            return
        self._last_split_check = now

        for bid in list(self.blobs.keys()):
            blob = self.blobs.get(bid)
            if blob is None or blob.mass < SPLIT_MIN_MASS:
                continue
            # Leave hard-cap splits to _enforce_size_caps
            if blob.mass > BLOB_MAX_MASS:
                self._split_oversize_blob(bid)
                continue
            k = self.kind(blob.kind_id)
            chance = k.desire_to_split * SPLIT_ROLL_SCALE
            if random.random() > chance:
                continue
            members = [
                p for p in self.particles.values()
                if p.alive and p.blob_id == bid
            ]
            if len(members) < SPLIT_MIN_MASS:
                continue
            group_a, group_b = self._partition_blob_members(members)
            if not group_a or not group_b:
                continue
            # Same-kind organic split (can rejoin later — no cooloff)
            new_bid = self._next_blob_id
            self._next_blob_id += 1
            nb = Blob(new_bid, blob.kind_id)
            nb.mass = len(group_b)
            self.blobs[new_bid] = nb
            for p in group_b:
                p.blob_id = new_bid
                p.angle = normalize_angle(p.angle + random.uniform(0.6, 1.4))
            for p in group_a:
                p.angle = normalize_angle(p.angle + random.uniform(-1.4, -0.6))
            blob.mass = len(group_a)

    def _find_attach_cell(self, body_cells, near_x, near_y):
        """Free 4-neighbor of the solid body, closest to (near_x, near_y)."""
        best = None
        best_d = 1e18
        for bx, by in body_cells:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = bx + dx, by + dy
                if not (0 <= nx < self.width and 0 <= ny < self.height):
                    continue
                if self.grid[ny, nx] != -1:
                    continue
                d = (nx - near_x) * (nx - near_x) + (ny - near_y) * (ny - near_y)
                if d < best_d:
                    best_d = d
                    best = (nx, ny)
        return best

    def _enforce_blob_solidity(self):
        """Keep every particle 4-connected to its blob body — no stragglers, no gaps."""
        for bid in list(self.blobs.keys()):
            blob = self.blobs.get(bid)
            if blob is None:
                continue
            members = [
                p for p in self.particles.values()
                if p.alive and p.blob_id == bid
            ]
            if len(members) < 2:
                continue

            cell_set = set()
            for p in members:
                cell_set.add((p.x, p.y))

            cx = sum(p.x for p in members) / float(len(members))
            cy = sum(p.y for p in members) / float(len(members))
            seed = min(
                members,
                key=lambda p: (p.x - cx) * (p.x - cx) + (p.y - cy) * (p.y - cy),
            )

            # BFS over 4-neighbors that belong to this blob
            q = deque([(seed.x, seed.y)])
            connected = set([(seed.x, seed.y)])
            while q:
                x, y = q.popleft()
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    n = (x + dx, y + dy)
                    if n in cell_set and n not in connected:
                        connected.add(n)
                        q.append(n)

            orphans = [p for p in members if (p.x, p.y) not in connected]
            if not orphans:
                continue

            # Re-attach farthest first so body grows outward cleanly
            orphans.sort(
                key=lambda p: -((p.x - cx) * (p.x - cx) + (p.y - cy) * (p.y - cy)),
            )
            body = list(connected)
            for p in orphans:
                target = self._find_attach_cell(body, p.x, p.y)
                if target is None:
                    # Fallback: free cell nearest centroid around body
                    target = self._find_attach_cell(body, int(cx), int(cy))
                if target is None:
                    continue
                ox, oy = p.x, p.y
                if (ox, oy) == target:
                    continue
                self._clear_cell(oy, ox)
                p.x, p.y = target[0], target[1]
                p.px = float(target[0]) + 0.5
                p.py = float(target[1]) + 0.5
                # Keep local heading; wave will refresh intent from neighbors
                self._paint_particle(p)
                body.append(target)
                connected.add(target)

    def step(self):
        self.tick += 1
        self._spawn_food_tick()
        self._spawn_particle_tick()
        if self.tick % 30 == 0:
            self._prune_cooloff()
        # One spatial index per tick for all neighbor queries
        self._rebuild_spatial()
        # Shared wander targets + pack kinematics once per tick
        self._update_all_blob_explore()
        self._cache_blob_kinematics()
        # Whole body translates together toward explore heading
        self._move_blob_bodies()
        ids = list(self.particles.keys())
        if self.tick % 4 == 0:
            random.shuffle(ids)
        for pid in ids:
            p = self.particles.get(pid)
            if p and p.alive:
                self._integrate(p)
        # Hard rule: every cell stays 4-connected to the blob body
        if self.tick % BLOB_SOLID_EVERY == 0:
            self._enforce_blob_solidity()
        if self.tick % 8 == 0:
            self._sync_blob_masses()
            self._enforce_size_caps()
        self._try_splits()
        if self.tick % 90 == 0:
            self._rebuild_grid()
        elif self._food_dirty:
            self._paint_food_layer()

    def _rebuild_grid(self):
        self.grid[:, :] = -1
        # Mark currently lit cells dirty so they clear on render
        for y in range(self.height):
            for x in range(self.width):
                if self.rgb[y, x, 0] or self.rgb[y, x, 1] or self.rgb[y, x, 2]:
                    self._dirty.add((x, y))
        self.rgb[:, :] = 0
        seen = set()
        for p in self.particles.values():
            if not p.alive:
                continue
            key = (p.x, p.y)
            if key in seen or not (0 <= p.x < self.width and 0 <= p.y < self.height):
                found = False
                for r in range(1, 8):
                    for dy in range(-r, r + 1):
                        for dx in range(-r, r + 1):
                            nx, ny = p.x + dx, p.y + dy
                            if self._cell_free(nx, ny):
                                p.x, p.y = nx, ny
                                p.px = float(nx) + 0.5
                                p.py = float(ny) + 0.5
                                key = (nx, ny)
                                found = True
                                break
                        if found:
                            break
                    if found:
                        break
                if not found:
                    continue
            if key in seen:
                continue
            seen.add(key)
            self._paint_particle(p)
        self._paint_food_layer()

    def render(self):
        """Only SetPixel dirty cells — keeps frame rate high on the Pi."""
        if not self._dirty:
            return
        set_pixel = LED.TheMatrix.SetPixel
        rgb = self.rgb
        for (x, y) in self._dirty:
            set_pixel(x, y, int(rgb[y, x, 0]), int(rgb[y, x, 1]), int(rgb[y, x, 2]))
        self._dirty.clear()


#------------------------------------------------------------------------------
#  Entry points
#------------------------------------------------------------------------------

def PlayOutbreak4(duration_minutes, stop_event=None):
    dish = Playfield()
    n = dish.seed()
    print("[Outbreak4] Running {} particles / {} blob(s) on {}x{}".format(
        n, len(dish.blobs), WIDTH, HEIGHT,
    ))

    start = time.time()
    while True:
        if stop_event is not None and stop_event.is_set():
            print("[Outbreak4] StopEvent received")
            break
        if dish.tick >= MaxTicks:
            print("[Outbreak4] MaxTicks reached")
            break
        if (time.time() - start) / 60.0 >= duration_minutes:
            print("[Outbreak4] Duration reached ({:.1f} min, {} ticks)".format(
                duration_minutes, dish.tick,
            ))
            break
        dish.step()
        dish.render()

    LED.ClearBigLED()
    return dish.tick


def LaunchOutbreak4(duration=10, show_intro=True, stop_event=None):
    if show_intro:
        LED.ShowTitleScreen(
            BigText="OUTBRK4",
            BigTextRGB=LED.HighRed,
            BigTextShadowRGB=LED.ShadowRed,
            LittleText="ORGANIC",
            LittleTextRGB=LED.MedGreen,
            LittleTextShadowRGB=(0, 10, 0),
            ScrollText="STICK  FEED  FIGHT  SPLIT",
            ScrollTextRGB=LED.MedYellow,
            ScrollSleep=0.03,
            DisplayTime=1,
            ExitEffect=0,
        )
        LED.ClearBigLED()
    PlayOutbreak4(duration, stop_event)


if __name__ == "__main__":
    LED.LoadConfigData()
    LaunchOutbreak4(duration=100000, show_intro=False, stop_event=None)
