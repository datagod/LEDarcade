#!/usr/bin/env python
#------------------------------------------------------------------------------
#  OUTBREAK3 — Single-celled organisms on a 64×32 petri dish
#
#  Goals:
#    1. Same-strain particles join into leader-driven blobs
#    2. Different-strain contact = infection fight; winner converts loser
#       to the winner's strain/color (particle is taken over, not killed)
#    3. Large blobs extend tentacle arms (probes / food when enabled)
#    4. Optional food → grow / replicate (FOOD_ENABLED)
#  Timing: one tick per loop, no frame sleep (Outbreak style).
#------------------------------------------------------------------------------

from __future__ import print_function

import math
import random
import time

import numpy as np

import LEDarcade as LED

LED.Initialize()

WIDTH = 64
HEIGHT = 32

if LED.HatWidth != WIDTH or LED.HatHeight != HEIGHT:
    print(
        "[Outbreak3] Panel is {}x{}; playfield is {}x{} (1:1 when sizes match)".format(
            LED.HatWidth, LED.HatHeight, WIDTH, HEIGHT,
        )
    )
    WIDTH = LED.HatWidth
    HEIGHT = LED.HatHeight

# --- Outbreak timing (lower speed value = moves more often) ---
VirusTopSpeed = 5
VirusBottomSpeed = 12
VirusStartSpeed = 8
MaxTicks = 1000000

INITIAL_VIRUS_COUNT = 100
MAX_VIRUSES = 400
# Spawn fresh free particles on a wall-clock timer (enter from screen edges)
PARTICLE_SPAWN_ENABLED = True
PARTICLE_SPAWN_INTERVAL_SEC = 3.0
PARTICLE_SPAWN_BATCH = 1      # new viruses per spawn event
# Few strains so same colors reliably find each other and form blobs
if INITIAL_VIRUS_COUNT <= 40:
    ACTIVE_STRAIN_COUNT = 2
else:
    ACTIVE_STRAIN_COUNT = 4

FLEE_DURATION = 40
FLEE_SPEED_BOOST = 4
ChanceOfSpeedup = 70
ChanceOfSlowdown = 220

ENERGY_START = 10.0
ENERGY_PER_CELL = 4.0

# Blob = colony with this many cells or more
BLOB_MIN_SIZE = 2

# --- Food ---
FOOD_ENABLED = True
FOOD_COLOR = (80, 80, 20)
FOOD_MAX = 40
FOOD_SPAWN_INTERVAL_SEC = 5.0  # one pellet every N wall-clock seconds
FOOD_SPAWN_BATCH = 1           # pellets per spawn event
FOOD_ENERGY = 7.0              # personal energy gained per bite
FOOD_COLONY_ENERGY = 2.0
REPLICATE_MIN_ENERGY = 16.0
REPLICATE_COST = 9.0

# --- Sensing / steering ---
SENSE_RADIUS = 12
SEEK_FOOD_STRENGTH = 0.70     # hungry, but not exclusive of clumping
FEAR_ENABLED = False          # solos avoid blobs when True
AVOID_BLOB_STRENGTH = 0.45    # fear is secondary to food
AVOID_BLOB_CLOSE = 3.5        # only really scare when this close
HUNT_PREY_STRENGTH = 0.88
HUNT_RIVAL_STRENGTH = 0.92
SEEK_BLOB_STRENGTH = 0.95     # blobs chase other same-strain blobs to merge
CLUMP_STRENGTH = 0.80         # strong same-strain pull
CLUMP_RADIUS = 14             # how far solos sense kin
CLUMP_NEAR = 5.0              # when kin this close, clump beats food
CLUMP_WANDER_SCALE = 0.25

# Blob leadership — leader dominates path; body still ripples but obeys hard
WAVE_RADIUS = 1               # only immediate neighbors pass the turn
WAVE_BLEND = 0.78             # strong upstream adopt
WAVE_SPEED_BLEND = 0.70       # speed snaps toward leader chain
LEADER_HEADING_FORCE = 0.65   # direct blend toward leader heading each tick
LEADER_SPEED_FORCE = 0.80     # direct blend toward leader speed each tick
FOLLOW_CATCHUP_BLEND = 0.92   # hard reel-in toward leader position
FOLLOW_CATCHUP_DIST = 0.8
FOLLOW_MAX_LAG = 3.0          # body cannot trail far

# Clump stickiness — glue to pack, but leader still owns the heading
STICKINESS = 0.45             # local glue (weaker than leader force)
STICKY_RADIUS = 5             # neighborhood for sticky pull
STICKY_POS_PULL = 0.28        # continuous-position glue each tick
STICKY_LEADER_BIAS = 0.55     # sticky centroid weighted toward leader

# Large-blob tentacles (arms that stretch toward food)
TENTACLES_ENABLED = False     # set True to re-enable arms
TENTACLE_MIN_MASS = 8         # only sizable packs grow arms
TENTACLE_MAX_ARMS = 3
TENTACLE_ARM_FRACTION = 0.40  # leave most mass in the core
TENTACLE_SENSE = 22           # smell food farther
TENTACLE_TIP_SEEK = 0.95
TENTACLE_SEGMENT_FOLLOW = 0.78
TENTACLE_STRETCH = 24.0
TENTACLE_LEASH_STRENGTH = 0.35
TENTACLE_CORE_BLEND = 0.60    # body core packs tightly
TENTACLE_PROBE = True         # exploratory arms
# Only true tentacle breakaways become new blobs (not every gap)
SPLIT_ONLY_TENTACLES = True

# Combat / infection (different colors fight; winner converts loser)
FIGHT_NOISE = 4.0              # luck in cell-vs-cell fights
INFECTION_ON_CONTACT = True   # different strain → fight → convert to winner

# Blob energy conservation — aggressive roam, hard burst in combat
BLOB_IDLE_STEP_SCALE = 1.05   # cruise faster than free particles
BLOB_MERGE_STEP_SCALE = 1.25  # hard push when chasing a same-strain blob
BLOB_EXPLORE_STEP_SCALE = 1.10  # keep roaming when scouting
BLOB_NO_FOOD_STEP_SCALE = 0.06  # crawl when no food (if FOOD_AWARE_PACE)
BLOB_FOOD_SENSE = 12          # food within this → not food-starved
FOOD_AWARE_PACE = False       # blobs slow hard when no food nearby
BLOB_COMBAT_STEP_SCALE = 1.65 # burst speed during fights / pursuit
COMBAT_BURST_TICKS = 90       # stay hot longer after contact
COMBAT_SENSE = 16             # pick fights from farther away
ENERGY_IDLE_REGEN = 0.06      # recover faster so they can keep bursting
ENERGY_COMBAT_DRAIN = 0.07    # less drain — stay aggressive longer
ENERGY_COMBAT_MIN = 1.0       # low threshold before forced idle

# Blob exploration — always keep moving toward new waypoints
BLOB_EXPLORE_STRENGTH = 0.70  # how hard to chase explore waypoint
BLOB_EXPLORE_ARRIVE = 4.0     # retarget when this close to waypoint
BLOB_EXPLORE_RETARGET_MIN = 40
BLOB_EXPLORE_RETARGET_MAX = 140
BLOB_EXPLORE_WANDER = 0.12    # continuous heading noise while scouting
# Re-elect blob leader every N seconds: member closest to screen center
LEADER_ELECTION_INTERVAL_SEC = 60.0
BLOB_LARGE_MASS = 6           # packs this big get a small speed kick
BLOB_LARGE_STEP_BOOST = 1.20  # keep large packs from feeling stuck
# Periodic fission: large blobs split into two differently colored packs
BLOB_FISSION_ENABLED = True
BLOB_FISSION_INTERVAL_SEC = 20.0
BLOB_FISSION_MIN_MASS = 4     # need at least this many cells to split

# --- Outbreak strain palette ---
VIRUS_STRAIN_COLORS = {
    '1': (0, 200, 0),
    '2': (150, 0, 0),
    '3': (150, 100, 0),
    '4': (0, 0, 100),
    '5': (200, 0, 50),
    '6': (125, 185, 0),
    '7': (200, 0, 200),
    '8': (50, 150, 75),
}
STRAIN_KEYS = tuple(VIRUS_STRAIN_COLORS.keys())
ACTIVE_STRAINS = STRAIN_KEYS[: min(ACTIVE_STRAIN_COUNT, len(STRAIN_KEYS))]

TURN_NOISE = 0.035
TURN_RATE_DAMP = 0.94
TURN_RATE_MAX = 0.12
WANDER_ANGLE_JITTER = 0.25
WANDER_CHECK_INTERVAL = 5
BASE_DRIFT = 0.20             # faster baseline motion
TWO_PI = math.pi * 2.0


def normalize_angle(angle):
    angle = angle % TWO_PI
    if angle < 0:
        angle += TWO_PI
    return angle


def random_angle():
    return random.uniform(0.0, TWO_PI)


def angle_away_from(ax, ay, bx, by):
    dx = ax - bx
    dy = ay - by
    if dx == 0 and dy == 0:
        return random_angle()
    return normalize_angle(math.atan2(dy, dx) + random.uniform(-0.35, 0.35))


def clamp_speed(speed):
    if speed > VirusBottomSpeed:
        return VirusBottomSpeed
    if speed < VirusTopSpeed:
        return VirusTopSpeed
    return speed


def random_speed():
    # Bias toward the fast end of the range (lower number = faster)
    return random.randint(VirusTopSpeed, VirusTopSpeed + 5)


def mutate_color(rgb):
    """Slightly different color for a split-off tentacle blob."""
    r, g, b = rgb
    # Nudge each channel; keep at least one channel clearly shifted
    def nudge(c, amount=None):
        if amount is None:
            amount = random.randint(-55, 55)
        return max(20, min(255, int(c) + amount))

    nr, ng, nb = nudge(r), nudge(g), nudge(b)
    # Guarantee a visible delta from parent
    if abs(nr - r) + abs(ng - g) + abs(nb - b) < 40:
        channel = random.randrange(3)
        boost = random.choice([-70, 70])
        if channel == 0:
            nr = nudge(r, boost)
        elif channel == 1:
            ng = nudge(g, boost)
        else:
            nb = nudge(b, boost)
    return (nr, ng, nb)


class Colony(object):
    __slots__ = (
        "colony_id", "strain_key", "color", "energy", "mass",
        "leader_id", "combat_timer",
        "explore_tx", "explore_ty", "explore_timer",
    )

    def __init__(self, colony_id, strain_key, leader_id=None, color=None):
        self.colony_id = colony_id
        self.strain_key = strain_key
        if color is not None:
            self.color = color
        elif strain_key in VIRUS_STRAIN_COLORS:
            self.color = VIRUS_STRAIN_COLORS[strain_key]
        else:
            self.color = (120, 120, 120)
        self.energy = ENERGY_START
        self.mass = 0
        self.leader_id = leader_id
        self.combat_timer = 0  # >0 → pack is in combat burst
        self.explore_tx = None
        self.explore_ty = None
        self.explore_timer = 0

    def strength(self):
        return self.energy + self.mass * ENERGY_PER_CELL

    def is_blob(self):
        return self.mass >= BLOB_MIN_SIZE

    def in_combat(self):
        return self.combat_timer > 0 and self.energy >= ENERGY_COMBAT_MIN


class Virus(object):
    __slots__ = (
        "virus_id", "x", "y", "px", "py", "colony_id", "angle",
        "turn_rate", "speed", "flee_timer", "alive", "energy",
        "tentacle", "tentacle_tip", "tentacle_tx", "tentacle_ty",
        "combat_timer", "seeking_merge",
    )

    def __init__(self, virus_id, x, y, colony_id, angle=None, speed=None, energy=None):
        self.virus_id = virus_id
        self.x = x
        self.y = y
        self.colony_id = colony_id
        self.angle = normalize_angle(angle) if angle is not None else random_angle()
        self.px = float(x) + random.uniform(0.15, 0.85)
        self.py = float(y) + random.uniform(0.15, 0.85)
        self.turn_rate = random.uniform(-TURN_RATE_MAX, TURN_RATE_MAX) * 0.5
        self.speed = clamp_speed(speed if speed is not None else random_speed())
        self.flee_timer = 0
        self.alive = True
        self.energy = float(ENERGY_START if energy is None else energy)
        # Tentacle arm state (reassigned each tick for large blobs)
        self.tentacle = False
        self.tentacle_tip = False
        self.tentacle_tx = None
        self.tentacle_ty = None
        self.combat_timer = 0
        self.seeking_merge = False

    def adjust_speed(self, increment):
        self.speed = clamp_speed(self.speed + increment)

    def effective_speed(self):
        if self.flee_timer > 0:
            return max(VirusTopSpeed, self.speed - FLEE_SPEED_BOOST)
        return self.speed

    def drift_step(self):
        return BASE_DRIFT * (float(VirusBottomSpeed) / float(self.effective_speed()))

    def cell_power(self, colony):
        """Per-component combat power for blob fights / conversion."""
        mass = colony.mass if colony is not None else 1
        return self.energy + mass * 1.5 + colony.energy * 0.15 if colony else self.energy


class Playfield(object):
    """Native 64×32 grid — one cell per LED."""

    def __init__(self):
        self.width = WIDTH
        self.height = HEIGHT
        self.grid = np.full((HEIGHT, WIDTH), -1, dtype=np.int32)
        self.rgb = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        self.viruses = {}
        self.colonies = {}
        self.food = set()  # (x, y) cells with food
        self._next_virus_id = 1
        self._next_colony_id = 1
        self.tick = 0
        self._last_food_spawn = time.time()
        self._last_particle_spawn = time.time()
        self._last_leader_election = time.time()
        self._last_blob_fission = time.time()
        self._particle_spawn_index = 0

    # ------------------------------------------------------------------ setup
    def _new_colony(self, strain_key, color=None):
        cid = self._next_colony_id
        self._next_colony_id += 1
        colony = Colony(cid, strain_key, color=color)
        self.colonies[cid] = colony
        return colony

    def _spawn_virus(self, x, y, strain_key, energy=None, speed=None, colony=None):
        if self.grid[y, x] != -1:
            return None
        if (x, y) in self.food:
            self.food.discard((x, y))
        if colony is None:
            colony = self._new_colony(strain_key)
        vid = self._next_virus_id
        self._next_virus_id += 1
        virus = Virus(vid, x, y, colony.colony_id, speed=speed, energy=energy)
        self.viruses[vid] = virus
        colony.mass = len(self._colony_members(colony.colony_id))
        if colony.leader_id is None:
            colony.leader_id = vid
        self.grid[y, x] = vid
        self._paint_cell(y, x, colony.color)
        return virus

    def _cell_isolated(self, x, y, min_gap=2):
        """True if no virus is within min_gap cells (avoid starting as blobs)."""
        for dy in range(-min_gap, min_gap + 1):
            for dx in range(-min_gap, min_gap + 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    if self.grid[ny, nx] != -1:
                        return False
        return True

    def seed(self, count=INITIAL_VIRUS_COUNT):
        # Balanced strains, each particle alone (no starter clumps)
        strain_cycle = list(ACTIVE_STRAINS)
        if not strain_cycle:
            strain_cycle = list(STRAIN_KEYS)
        placed = 0
        attempts = 0
        while placed < count and attempts < count * 80:
            attempts += 1
            x = random.randrange(self.width)
            y = random.randrange(self.height)
            if self.grid[y, x] != -1:
                continue
            # Prefer spacing so same-strain neighbors don't start already joined
            if placed > 0 and not self._cell_isolated(x, y, min_gap=2):
                if attempts < count * 50:
                    continue
            strain_key = strain_cycle[placed % len(strain_cycle)]
            if self._spawn_virus(x, y, strain_key):
                placed += 1
        if FOOD_ENABLED:
            # Start with a couple pellets; rest arrive on the timer
            self._seed_food(count=min(3, FOOD_MAX))
            self._last_food_spawn = time.time()
        else:
            self.food.clear()
        print(
            "[Outbreak3] Seeded {} individual viruses, strains: {} ({})".format(
                placed, len(strain_cycle), ",".join(strain_cycle),
            )
        )
        return placed

    def _seed_food(self, count):
        if not FOOD_ENABLED:
            return 0
        attempts = 0
        placed = 0
        while placed < count and attempts < count * 30:
            attempts += 1
            x = random.randrange(self.width)
            y = random.randrange(self.height)
            if self.grid[y, x] != -1 or (x, y) in self.food:
                continue
            self.food.add((x, y))
            placed += 1
        return placed

    def _spawn_food_tick(self):
        """Drop food pellets on a wall-clock interval (not tick count)."""
        if not FOOD_ENABLED:
            return
        now = time.time()
        if now - self._last_food_spawn < FOOD_SPAWN_INTERVAL_SEC:
            return
        self._last_food_spawn = now
        if len(self.food) >= FOOD_MAX:
            return
        need = min(FOOD_SPAWN_BATCH, FOOD_MAX - len(self.food))
        self._seed_food(need)

    def _random_edge_cell(self):
        """Pick a free cell on the outer rim so particles enter from off-screen edges."""
        for _ in range(60):
            edge = random.randrange(4)
            if edge == 0:  # top
                x = random.randrange(self.width)
                y = 0
                inward = random.uniform(0.15, math.pi - 0.15)  # downward
            elif edge == 1:  # bottom
                x = random.randrange(self.width)
                y = self.height - 1
                inward = random.uniform(-math.pi + 0.15, -0.15)  # upward
            elif edge == 2:  # left
                x = 0
                y = random.randrange(self.height)
                inward = random.uniform(-math.pi * 0.5 + 0.15, math.pi * 0.5 - 0.15)
            else:  # right
                x = self.width - 1
                y = random.randrange(self.height)
                # toward left: around pi
                inward = normalize_angle(
                    math.pi + random.uniform(-math.pi * 0.5 + 0.15, math.pi * 0.5 - 0.15)
                )
            if self.grid[y, x] != -1 or (x, y) in self.food:
                continue
            return x, y, inward
        return None

    def _spawn_particle_tick(self):
        """Introduce new free viruses from the screen edges every interval."""
        if not PARTICLE_SPAWN_ENABLED:
            return
        now = time.time()
        if now - self._last_particle_spawn < PARTICLE_SPAWN_INTERVAL_SEC:
            return
        self._last_particle_spawn = now
        if len(self.viruses) >= MAX_VIRUSES:
            return

        strains = list(ACTIVE_STRAINS) if ACTIVE_STRAINS else list(STRAIN_KEYS)
        placed = 0
        attempts = 0
        while placed < PARTICLE_SPAWN_BATCH and attempts < PARTICLE_SPAWN_BATCH * 40:
            attempts += 1
            if len(self.viruses) >= MAX_VIRUSES:
                break
            edge = self._random_edge_cell()
            if edge is None:
                break
            x, y, inward = edge
            strain_key = strains[self._particle_spawn_index % len(strains)]
            self._particle_spawn_index += 1
            virus = self._spawn_virus(x, y, strain_key)
            if virus is not None:
                # Enter the playfield from the rim
                virus.angle = normalize_angle(inward)
                virus.px = float(x) + 0.5 + math.cos(virus.angle) * 0.2
                virus.py = float(y) + 0.5 + math.sin(virus.angle) * 0.2
                placed += 1

    # ------------------------------------------------------------------ paint
    def _paint_cell(self, y, x, color):
        self.rgb[y, x, 0] = color[0]
        self.rgb[y, x, 1] = color[1]
        self.rgb[y, x, 2] = color[2]

    def _clear_cell(self, y, x):
        self.grid[y, x] = -1
        if (x, y) in self.food:
            self._paint_cell(y, x, FOOD_COLOR)
        else:
            self.rgb[y, x] = (0, 0, 0)

    def _paint_food_layer(self):
        if not FOOD_ENABLED:
            return
        for (x, y) in self.food:
            if self.grid[y, x] == -1:
                self._paint_cell(y, x, FOOD_COLOR)

    # ------------------------------------------------------------------ colony
    def _colony(self, colony_id):
        return self.colonies.get(colony_id)

    def _colony_members(self, colony_id):
        return [
            virus for virus in self.viruses.values()
            if virus.alive and virus.colony_id == colony_id
        ]

    def _sync_colony_mass(self, colony_id):
        colony = self._colony(colony_id)
        if colony:
            colony.mass = len(self._colony_members(colony_id))

    def _ensure_leader(self, colony_id):
        colony = self._colony(colony_id)
        if colony is None:
            return None
        leader = self.viruses.get(colony.leader_id)
        if (
            leader is not None
            and leader.alive
            and leader.colony_id == colony_id
        ):
            return leader
        members = self._colony_members(colony_id)
        if not members:
            colony.leader_id = None
            return None
        # Fallback: nearest to colony centroid
        cx = sum(v.px for v in members) / float(len(members))
        cy = sum(v.py for v in members) / float(len(members))
        members.sort(key=lambda v: (v.px - cx) ** 2 + (v.py - cy) ** 2)
        colony.leader_id = members[0].virus_id
        return members[0]

    def _elect_leader_screen_center(self, colony_id):
        """Pick the member closest to the center of the playfield as leader."""
        colony = self._colony(colony_id)
        if colony is None:
            return None
        members = self._colony_members(colony_id)
        if not members:
            colony.leader_id = None
            return None
        # Screen / playfield center
        cx = (self.width - 1) * 0.5
        cy = (self.height - 1) * 0.5
        members.sort(key=lambda v: (v.px - cx) ** 2 + (v.py - cy) ** 2)
        new_leader = members[0]
        old_id = colony.leader_id
        colony.leader_id = new_leader.virus_id
        # Fresh heading/explore so a new leader immediately drives the pack
        if old_id != new_leader.virus_id:
            self._pick_explore_waypoint(new_leader, colony)
            new_leader.adjust_speed(-2)
            new_leader.angle = normalize_angle(
                new_leader.angle + random.uniform(-0.5, 0.5),
            )
            new_leader.seeking_merge = False
        return new_leader

    def _elect_leaders_tick(self):
        """Every LEADER_ELECTION_INTERVAL_SEC, re-elect blob leaders by screen center."""
        now = time.time()
        if now - self._last_leader_election < LEADER_ELECTION_INTERVAL_SEC:
            return
        self._last_leader_election = now
        for colony_id, colony in list(self.colonies.items()):
            if colony is None or not colony.is_blob():
                continue
            leader = self._elect_leader_screen_center(colony_id)
            if leader is not None:
                # Nudge whole pack energy so large blobs wake up
                colony.energy = min(
                    ENERGY_START * 4.0 + colony.mass * 2.0,
                    colony.energy + 3.0,
                )

    def _is_leader(self, virus):
        leader = self._ensure_leader(virus.colony_id)
        return leader is not None and leader.virus_id == virus.virus_id

    def _is_blob_virus(self, virus):
        colony = self._colony(virus.colony_id)
        return colony is not None and colony.is_blob()

    def _paint_colony_members(self, colony_id):
        colony = self._colony(colony_id)
        if colony is None:
            return
        for virus in self._colony_members(colony_id):
            self.grid[virus.y, virus.x] = virus.virus_id
            self._paint_cell(virus.y, virus.x, colony.color)

    def _cell_is_free(self, nx, ny, virus_id):
        occupant = self.grid[ny, nx]
        return occupant == -1 or occupant == virus_id

    # ------------------------------------------------------------------ merge / convert / kill
    def _merge_colonies(self, winner_id, loser_id):
        if winner_id == loser_id:
            return winner_id
        winner = self.colonies.get(winner_id)
        loser = self.colonies.get(loser_id)
        if winner is None or loser is None:
            return winner_id or loser_id

        keep_leader_id = winner.leader_id
        if loser.mass > winner.mass:
            keep_leader_id = loser.leader_id

        leader = self.viruses.get(keep_leader_id)
        leader_speed = leader.speed if leader is not None and leader.alive else VirusStartSpeed

        for virus in self.viruses.values():
            if virus.alive and virus.colony_id == loser_id:
                virus.colony_id = winner_id
                virus.speed = clamp_speed(leader_speed)

        winner.energy += loser.energy * 0.5
        winner.leader_id = keep_leader_id
        del self.colonies[loser_id]
        self._sync_colony_mass(winner_id)
        self._ensure_leader(winner_id)
        self._paint_colony_members(winner_id)
        return winner_id

    def _convert_virus(self, victim, winner_colony_id):
        """Infect victim: joins winner's colony (same strain/color)."""
        if not victim.alive:
            return
        if victim.colony_id == winner_colony_id:
            return
        winner = self._colony(winner_colony_id)
        if winner is None:
            return

        old_id = victim.colony_id
        old = self._colony(old_id)
        was_leader = old is not None and old.leader_id == victim.virus_id

        victim.colony_id = winner_colony_id
        leader = self._ensure_leader(winner_colony_id)
        if leader is not None:
            victim.speed = leader.speed
            victim.angle = self._blend_angle(victim.angle, leader.angle, 0.5)
        victim.energy = max(3.0, victim.energy * 0.6)
        winner.energy += 2.0

        # Clear tentacle state — newly infected cell follows the new body
        victim.tentacle = False
        victim.tentacle_tip = False
        victim.tentacle_tx = None
        victim.tentacle_ty = None

        self._paint_cell(victim.y, victim.x, winner.color)
        self.grid[victim.y, victim.x] = victim.virus_id

        if old is not None:
            self._sync_colony_mass(old_id)
            if old.mass <= 0:
                if old_id in self.colonies:
                    del self.colonies[old_id]
            elif was_leader:
                self._ensure_leader(old_id)
            else:
                self._sync_colony_mass(old_id)

        self._sync_colony_mass(winner_colony_id)
        self._ensure_leader(winner_colony_id)

    def _raise_combat(self, colony=None, virus=None, ticks=COMBAT_BURST_TICKS):
        """Put a pack/cell into combat burst (fast move, energy drain)."""
        if colony is not None:
            colony.combat_timer = max(int(colony.combat_timer), int(ticks))
        if virus is not None:
            virus.combat_timer = max(int(virus.combat_timer), int(ticks))

    def _infect(self, victor, victim):
        """Victor wins the fight — victim becomes victor's strain (infection)."""
        if not victor.alive or not victim.alive:
            return
        if victor.colony_id == victim.colony_id:
            return
        vcol = self._colony(victor.colony_id)
        if vcol is None:
            return
        # Capture loser colony before convert (victim colony_id changes)
        loser_col = self._colony(victim.colony_id)
        self._convert_virus(victim, victor.colony_id)
        victor.energy += 1.5
        # Combat adrenaline — winner pack bursts; residual heat on loser pack
        self._raise_combat(vcol, victor)
        self._raise_combat(loser_col, None, ticks=COMBAT_BURST_TICKS // 2)
        self._anchor_virus_to_cell(victor)
        if victim.alive:
            self._anchor_virus_to_cell(victim)

    def _kill_virus(self, virus):
        if not virus.alive:
            return
        colony_id = virus.colony_id
        was_leader = False
        colony = self._colony(colony_id)
        if colony is not None and colony.leader_id == virus.virus_id:
            was_leader = True
            colony.leader_id = None

        self._clear_cell(virus.y, virus.x)
        virus.alive = False
        del self.viruses[virus.virus_id]

        colony = self._colony(colony_id)
        if colony is None:
            return
        self._sync_colony_mass(colony_id)
        if colony.mass <= 0:
            del self.colonies[colony_id]
            return
        if was_leader:
            self._ensure_leader(colony_id)

    # ------------------------------------------------------------------ food / replicate
    def _try_eat_food(self, virus):
        if not FOOD_ENABLED:
            return False
        key = (virus.x, virus.y)
        if key not in self.food:
            return False
        self.food.discard(key)
        virus.energy += FOOD_ENERGY
        colony = self._colony(virus.colony_id)
        if colony is not None:
            colony.energy += FOOD_COLONY_ENERGY
        # stronger after eating → slightly faster
        if random.random() < 0.45:
            virus.adjust_speed(-1)
        self._try_replicate(virus)
        return True

    def _try_replicate(self, virus):
        if not virus.alive or virus.energy < REPLICATE_MIN_ENERGY:
            return None
        if len(self.viruses) >= MAX_VIRUSES:
            return None
        colony = self._colony(virus.colony_id)
        if colony is None:
            return None

        # Birth into nearest empty neighbor
        empty = self._find_nearest_empty(virus.x, virus.y)
        if empty is None:
            return None
        # Prefer adjacent cells only
        if abs(empty[0] - virus.x) > 2 or abs(empty[1] - virus.y) > 2:
            # search tight ring
            found = None
            for r in range(1, 3):
                for dy in range(-r, r + 1):
                    for dx in range(-r, r + 1):
                        if abs(dx) != r and abs(dy) != r:
                            continue
                        nx, ny = virus.x + dx, virus.y + dy
                        if 0 <= nx < self.width and 0 <= ny < self.height:
                            if self.grid[ny, nx] == -1:
                                found = (nx, ny)
                                break
                    if found:
                        break
                if found:
                    break
            if not found:
                return None
            empty = found

        virus.energy -= REPLICATE_COST
        child_energy = max(ENERGY_START * 0.7, virus.energy * 0.35)
        # Solo parents spawn a new solo colony (same strain). Blob parents add to blob.
        if colony.is_blob():
            child = self._spawn_virus(
                empty[0], empty[1], colony.strain_key,
                energy=child_energy, speed=virus.speed, colony=colony,
            )
        else:
            child = self._spawn_virus(
                empty[0], empty[1], colony.strain_key,
                energy=child_energy, speed=virus.speed, colony=None,
            )
        if child is not None:
            self._sync_colony_mass(colony.colony_id)
            if child.colony_id != colony.colony_id:
                self._sync_colony_mass(child.colony_id)
        return child

    # ------------------------------------------------------------------ sensing
    def _scan_neighborhood(self, virus, radius=SENSE_RADIUS):
        """Return food, threat, prey, rival blob, ally blob (same strain, other colony)."""
        colony = self._colony(virus.colony_id)
        if colony is None:
            return None, None, None, None, None

        best_food = None
        best_food_d2 = radius * radius + 1
        best_threat = None
        best_threat_d2 = radius * radius + 1
        best_prey = None
        best_prey_d2 = radius * radius + 1
        best_rival = None
        best_rival_d2 = radius * radius + 1
        best_ally = None
        best_ally_d2 = radius * radius + 1

        x0, y0 = virus.x, virus.y
        r = radius
        for dy in range(-r, r + 1):
            ny = y0 + dy
            if ny < 0 or ny >= self.height:
                continue
            for dx in range(-r, r + 1):
                if dx == 0 and dy == 0:
                    continue
                nx = x0 + dx
                if nx < 0 or nx >= self.width:
                    continue
                d2 = dx * dx + dy * dy
                if d2 > r * r:
                    continue

                if FOOD_ENABLED and (nx, ny) in self.food and d2 < best_food_d2:
                    best_food_d2 = d2
                    best_food = (nx + 0.5, ny + 0.5)

                oid = int(self.grid[ny, nx])
                if oid < 0:
                    continue
                other = self.viruses.get(oid)
                if other is None or not other.alive:
                    continue
                oc = self._colony(other.colony_id)
                if oc is None or other.colony_id == virus.colony_id:
                    continue

                # Threat: foreign blob to a solo particle
                if not colony.is_blob() and oc.is_blob() and d2 < best_threat_d2:
                    best_threat_d2 = d2
                    best_threat = (other.px, other.py)

                # Prey: solo particle for a blob
                if colony.is_blob() and not oc.is_blob() and d2 < best_prey_d2:
                    best_prey_d2 = d2
                    best_prey = (other.px, other.py)

                # Ally blob: same strain, other colony → merge target
                if (
                    colony.is_blob()
                    and oc.is_blob()
                    and oc.strain_key == colony.strain_key
                    and d2 < best_ally_d2
                ):
                    best_ally_d2 = d2
                    best_ally = (other.px, other.py)

                # Rival blob: different strain
                if (
                    colony.is_blob()
                    and oc.is_blob()
                    and oc.strain_key != colony.strain_key
                    and d2 < best_rival_d2
                ):
                    best_rival_d2 = d2
                    best_rival = (other.px, other.py)

        return best_food, best_threat, best_prey, best_rival, best_ally

    def _find_ally_blob(self, virus):
        """Dish-wide search for nearest same-strain other blob (merge target)."""
        colony = self._colony(virus.colony_id)
        if colony is None or not colony.is_blob():
            return None, None
        best = None
        best_d2 = None
        for other in self.viruses.values():
            if not other.alive or other.colony_id == virus.colony_id:
                continue
            oc = self._colony(other.colony_id)
            if oc is None or not oc.is_blob():
                continue
            if oc.strain_key != colony.strain_key:
                continue
            # Prefer the other colony's leader if known (cleaner approach vector)
            lead = self._ensure_leader(other.colony_id)
            tx = lead.px if lead is not None else other.px
            ty = lead.py if lead is not None else other.py
            dx = tx - virus.px
            dy = ty - virus.py
            d2 = dx * dx + dy * dy
            if best_d2 is None or d2 < best_d2:
                best_d2 = d2
                best = (tx, ty)
        if best is None:
            return None, None
        return best, math.sqrt(best_d2)

    def _same_strain_solo_pull(self, virus):
        """Pull solo toward same-strain kin (solos or small blobs) to clump.

        Scans all viruses (not just local grid) so sparse populations still find kin.
        Returns (angle, nearest_dist) or (None, None).
        """
        colony = self._colony(virus.colony_id)
        if colony is None or colony.is_blob():
            return None, None
        ax = ay = total = 0.0
        nearest = None
        # Dish-wide search when the population is small; otherwise local radius
        max_d2 = float(self.width * self.width + self.height * self.height)
        if len(self.viruses) > 40:
            max_d2 = float(CLUMP_RADIUS * CLUMP_RADIUS)

        for other in self.viruses.values():
            if not other.alive or other.virus_id == virus.virus_id:
                continue
            if other.colony_id == virus.colony_id:
                continue
            oc = self._colony(other.colony_id)
            if oc is None or oc.strain_key != colony.strain_key:
                continue
            # Prefer other solos / small packs
            if oc.mass > 12:
                continue
            pdx = other.px - virus.px
            pdy = other.py - virus.py
            d2 = pdx * pdx + pdy * pdy
            if d2 < 1e-6 or d2 > max_d2:
                continue
            dist = math.sqrt(d2)
            if nearest is None or dist < nearest:
                nearest = dist
            # Nearer kin weigh more; small bonus for other solos
            w = (1.0 / d2) * (1.5 if not oc.is_blob() else 1.0)
            ax += pdx * w
            ay += pdy * w
            total += w
        if total <= 0:
            return None, None
        return math.atan2(ay, ax), nearest

    def _blend_angle(self, current, target, strength):
        delta = (target - current + math.pi) % TWO_PI - math.pi
        return normalize_angle(current + delta * strength)

    # ------------------------------------------------------------------ encounters
    def _resolve_encounter(self, mover, occupant):
        if mover.virus_id == occupant.virus_id:
            return "block"

        colony_a = self._colony(mover.colony_id)
        colony_b = self._colony(occupant.colony_id)
        if colony_a is None or colony_b is None:
            return "block"
        if mover.colony_id == occupant.colony_id:
            return "block"

        same_strain = colony_a.strain_key == colony_b.strain_key

        # --- Same strain: join into one colony (blob growth) ---
        if same_strain:
            if colony_a.strength() >= colony_b.strength():
                self._merge_colonies(mover.colony_id, occupant.colony_id)
            else:
                self._merge_colonies(occupant.colony_id, mover.colony_id)
            # Keep them adjacent — join should grow a visible pack
            self._anchor_virus_to_cell(mover)
            self._anchor_virus_to_cell(occupant)
            # Point both toward each other slightly so they don't drift apart
            mid_ang = math.atan2(occupant.py - mover.py, occupant.px - mover.px)
            mover.angle = self._blend_angle(mover.angle, mid_ang, 0.4)
            occupant.angle = self._blend_angle(
                occupant.angle, mid_ang + math.pi, 0.4,
            )
            return "join"

        # --- Different strain: infection fight (winner takes over loser) ---
        if not INFECTION_ON_CONTACT:
            self._retreat_from_block(mover, hard=False)
            return "block"

        power_a = mover.cell_power(colony_a) + random.uniform(0, FIGHT_NOISE)
        power_b = occupant.cell_power(colony_b) + random.uniform(0, FIGHT_NOISE)
        # Slight mass advantage for bigger colonies (infection pressure)
        power_a += colony_a.mass * 0.8
        power_b += colony_b.mass * 0.8

        if power_a > power_b:
            self._infect(mover, occupant)
            return "infect"
        if power_b > power_a:
            self._infect(occupant, mover)
            return "infect"
        # Exact tie: bounce and try again later
        self._retreat_from_block(mover, hard=True)
        return "block"

    # ------------------------------------------------------------------ motion helpers
    def _clamp_position(self, virus):
        lo = 0.05
        hi_x = self.width - 0.05
        hi_y = self.height - 0.05
        if virus.px < lo:
            virus.px = lo + (lo - virus.px)
            virus.angle = normalize_angle(math.pi - virus.angle + random.uniform(-0.25, 0.25))
            virus.turn_rate *= -0.5
        elif virus.px > hi_x:
            virus.px = hi_x - (virus.px - hi_x)
            virus.angle = normalize_angle(math.pi - virus.angle + random.uniform(-0.25, 0.25))
            virus.turn_rate *= -0.5
        if virus.py < lo:
            virus.py = lo + (lo - virus.py)
            virus.angle = normalize_angle(-virus.angle + random.uniform(-0.25, 0.25))
            virus.turn_rate *= -0.5
        elif virus.py > hi_y:
            virus.py = hi_y - (virus.py - hi_y)
            virus.angle = normalize_angle(-virus.angle + random.uniform(-0.25, 0.25))
            virus.turn_rate *= -0.5
        virus.px = max(lo, min(hi_x, virus.px))
        virus.py = max(lo, min(hi_y, virus.py))

    def _retreat_from_block(self, virus, hard=True):
        step = virus.drift_step()
        if hard:
            virus.px -= math.cos(virus.angle) * step * 1.5
            virus.py -= math.sin(virus.angle) * step * 1.5
            virus.turn_rate = random.uniform(-TURN_RATE_MAX, TURN_RATE_MAX)
            virus.angle = normalize_angle(virus.angle + random.uniform(-0.9, 0.9))
        else:
            virus.px -= math.cos(virus.angle) * step * 0.6
            virus.py -= math.sin(virus.angle) * step * 0.6
            virus.angle = normalize_angle(virus.angle + random.uniform(-0.4, 0.4))
            virus.turn_rate *= 0.5
        self._clamp_position(virus)
        nx = int(virus.px)
        ny = int(virus.py)
        if 0 <= nx < self.width and 0 <= ny < self.height:
            if (nx != virus.x or ny != virus.y) and self._cell_is_free(nx, ny, virus.virus_id):
                self._occupy_cell(virus, nx, ny)

    def _anchor_virus_to_cell(self, virus):
        if not virus.alive:
            return
        if int(virus.px) != virus.x or int(virus.py) != virus.y:
            virus.px = float(virus.x) + 0.5 + random.uniform(-0.2, 0.2)
            virus.py = float(virus.y) + 0.5 + random.uniform(-0.2, 0.2)
        self.grid[virus.y, virus.x] = virus.virus_id
        colony = self._colony(virus.colony_id)
        if colony:
            self._paint_cell(virus.y, virus.x, colony.color)

    def _occupy_cell(self, virus, nx, ny):
        if not self._cell_is_free(nx, ny, virus.virus_id):
            return False
        colony = self._colony(virus.colony_id)
        self._clear_cell(virus.y, virus.x)
        virus.x = nx
        virus.y = ny
        self.grid[ny, nx] = virus.virus_id
        if colony:
            self._paint_cell(ny, nx, colony.color)
        self._try_eat_food(virus)
        return True

    # ------------------------------------------------------------------ tentacles
    def _clear_tentacle_flags(self):
        for virus in self.viruses.values():
            virus.tentacle = False
            virus.tentacle_tip = False
            virus.tentacle_tx = None
            virus.tentacle_ty = None

    def _update_tentacles(self):
        """Large blobs assign arm cells that stretch toward food / probe outward."""
        self._clear_tentacle_flags()
        if not TENTACLES_ENABLED:
            return

        by_colony = {}
        for virus in self.viruses.values():
            if virus.alive:
                by_colony.setdefault(virus.colony_id, []).append(virus)

        for colony_id, members in by_colony.items():
            colony = self._colony(colony_id)
            if colony is None or colony.mass < TENTACLE_MIN_MASS:
                continue
            leader = self._ensure_leader(colony_id)
            if leader is None:
                continue

            cx = sum(m.px for m in members) / float(len(members))
            cy = sum(m.py for m in members) / float(len(members))

            targets = []
            sense2 = float(TENTACLE_SENSE * TENTACLE_SENSE)
            if FOOD_ENABLED:
                for (fx, fy) in self.food:
                    ftx = fx + 0.5
                    fty = fy + 0.5
                    d2 = (ftx - cx) ** 2 + (fty - cy) ** 2
                    if d2 <= sense2:
                        targets.append((d2, ftx, fty, True))  # real food
                targets.sort(key=lambda t: t[0])

            max_arms = min(TENTACLE_MAX_ARMS, max(1, colony.mass // 4))
            # Exploratory probes when little/no food — arms still shoot out
            if TENTACLE_PROBE:
                while len(targets) < max_arms:
                    ang = random.uniform(0.0, TWO_PI)
                    reach = TENTACLE_SENSE * random.uniform(0.55, 0.95)
                    ptx = cx + math.cos(ang) * reach
                    pty = cy + math.sin(ang) * reach
                    ptx = max(0.5, min(self.width - 0.5, ptx))
                    pty = max(0.5, min(self.height - 0.5, pty))
                    d2 = (ptx - cx) ** 2 + (pty - cy) ** 2
                    targets.append((d2, ptx, pty, False))

            if not targets:
                continue

            arm_budget = max(3, int(colony.mass * TENTACLE_ARM_FRACTION))
            per_arm = max(2, arm_budget // max_arms)
            claimed = set([leader.virus_id])

            for arm_i in range(min(max_arms, len(targets))):
                _d2, ftx, fty, _is_food = targets[arm_i]
                fdx = ftx - leader.px
                fdy = fty - leader.py
                flen = math.sqrt(fdx * fdx + fdy * fdy) or 1.0
                ux = fdx / flen
                uy = fdy / flen

                scored = []
                for m in members:
                    if m.virus_id in claimed:
                        continue
                    mx = m.px - leader.px
                    my = m.py - leader.py
                    proj = mx * ux + my * uy
                    # Allow more cells to be drafted into the arm (even near center side)
                    if proj < -0.5:
                        continue
                    lateral = abs(mx * uy - my * ux)
                    score = proj * 1.4 - 0.25 * lateral
                    scored.append((score, m))
                scored.sort(key=lambda t: -t[0])
                arm_cells = [t[1] for t in scored[:per_arm]]
                if len(arm_cells) < 2:
                    continue

                tip = max(
                    arm_cells,
                    key=lambda m: (m.px - leader.px) * ux + (m.py - leader.py) * uy,
                )
                for m in arm_cells:
                    m.tentacle = True
                    m.tentacle_tx = ftx
                    m.tentacle_ty = fty
                    m.tentacle_tip = (m.virus_id == tip.virus_id)
                    claimed.add(m.virus_id)

    def _colony_components(self, members):
        """8-connected components of colony members on the grid."""
        pos = {}
        for v in members:
            if v.alive:
                pos[(v.x, v.y)] = v
        seen = set()
        comps = []
        for v in members:
            if not v.alive or v.virus_id in seen:
                continue
            stack = [v]
            seen.add(v.virus_id)
            comp = []
            while stack:
                cur = stack.pop()
                comp.append(cur)
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        other = pos.get((cur.x + dx, cur.y + dy))
                        if other is None or other.virus_id in seen:
                            continue
                        seen.add(other.virus_id)
                        stack.append(other)
            comps.append(comp)
        return comps

    def _split_off_members(self, members, parent_colony):
        """Detached group becomes a new blob with a slightly different color."""
        if not members or parent_colony is None:
            return None
        # Unique strain so they don't instantly re-merge as "same strain"
        strain_key = "m{}".format(self._next_colony_id)
        new_color = mutate_color(parent_colony.color)
        colony = self._new_colony(strain_key, color=new_color)
        # Pick a leader near the group's center
        cx = sum(v.px for v in members) / float(len(members))
        cy = sum(v.py for v in members) / float(len(members))
        members_sorted = sorted(
            members,
            key=lambda v: (v.px - cx) ** 2 + (v.py - cy) ** 2,
        )
        colony.leader_id = members_sorted[0].virus_id
        colony.energy = max(ENERGY_START, parent_colony.energy * 0.25)

        for v in members:
            v.colony_id = colony.colony_id
            v.tentacle = False
            v.tentacle_tip = False
            v.tentacle_tx = None
            v.tentacle_ty = None
            # Fresh heading for the new organism
            v.angle = normalize_angle(
                v.angle + random.uniform(-0.8, 0.8)
            )
            self._paint_cell(v.y, v.x, colony.color)

        self._sync_colony_mass(colony.colony_id)
        self._ensure_leader(colony.colony_id)
        # New fission offspring should explore away from the parent
        if colony.leader_id is not None:
            lead = self.viruses.get(colony.leader_id)
            if lead is not None:
                self._pick_explore_waypoint(lead, colony)
        return colony

    def _fission_colony(self, colony_id):
        """Split one blob into two packs of different colors."""
        parent = self._colony(colony_id)
        if parent is None or not parent.is_blob():
            return None
        members = self._colony_members(colony_id)
        if len(members) < BLOB_FISSION_MIN_MASS:
            return None

        # Partition by a random axis through the pack centroid
        cx = sum(v.px for v in members) / float(len(members))
        cy = sum(v.py for v in members) / float(len(members))
        if random.random() < 0.5:
            members_sorted = sorted(members, key=lambda v: v.px)
        else:
            members_sorted = sorted(members, key=lambda v: v.py)
        mid = max(1, len(members_sorted) // 2)
        # Keep the half that still includes the current leader when possible
        group_stay = members_sorted[:mid]
        group_go = members_sorted[mid:]
        leader = self.viruses.get(parent.leader_id)
        if leader is not None and leader in group_go and len(group_stay) > 0:
            group_stay, group_go = group_go, group_stay
        if len(group_go) < 1 or len(group_stay) < 1:
            return None

        child = self._split_off_members(group_go, parent)
        self._sync_colony_mass(colony_id)
        stay_leader = self._ensure_leader(colony_id)
        if stay_leader is not None:
            self._pick_explore_waypoint(stay_leader, parent)
            # Push the two packs apart along the split axis
            if child is not None:
                child_lead = self.viruses.get(child.leader_id)
                if child_lead is not None:
                    away = math.atan2(
                        child_lead.py - stay_leader.py,
                        child_lead.px - stay_leader.px,
                    )
                    stay_leader.angle = normalize_angle(away + math.pi)
                    child_lead.angle = away
        return child

    def _blob_fission_tick(self):
        """Every BLOB_FISSION_INTERVAL_SEC, each large enough blob splits in two colors."""
        if not BLOB_FISSION_ENABLED:
            return
        now = time.time()
        if now - self._last_blob_fission < BLOB_FISSION_INTERVAL_SEC:
            return
        self._last_blob_fission = now

        # Snapshot ids — fission mutates colonies mid-loop
        for colony_id in list(self.colonies.keys()):
            colony = self._colony(colony_id)
            if colony is None:
                continue
            # Refresh mass before threshold check
            self._sync_colony_mass(colony_id)
            if colony.mass >= BLOB_FISSION_MIN_MASS:
                self._fission_colony(colony_id)

    def _split_disconnected_groups(self):
        """Tentacle arms that lose contact become a new colored blob.

        Ordinary body gaps do NOT split — that was dissolving blobs into
        unique mutant strains that could never re-clump.
        """
        if not TENTACLES_ENABLED:
            return
        by_colony = {}
        for virus in self.viruses.values():
            if virus.alive:
                by_colony.setdefault(virus.colony_id, []).append(virus)

        for colony_id in list(by_colony.keys()):
            parent = self._colony(colony_id)
            if parent is None or parent.mass < TENTACLE_MIN_MASS:
                continue
            members = [
                v for v in self.viruses.values()
                if v.alive and v.colony_id == colony_id
            ]
            if len(members) < 2:
                continue
            leader = self._ensure_leader(colony_id)
            if leader is None:
                continue

            comps = self._colony_components(members)
            if len(comps) <= 1:
                continue

            main = None
            for comp in comps:
                if any(v.virus_id == leader.virus_id for v in comp):
                    main = comp
                    break
            if main is None:
                main = max(comps, key=len)

            for comp in comps:
                if comp is main or not comp:
                    continue
                # Only tentacle breakaways (or disabled filter) become new blobs
                if SPLIT_ONLY_TENTACLES and not any(v.tentacle for v in comp):
                    continue
                self._split_off_members(comp, parent)

            self._sync_colony_mass(colony_id)
            if parent.mass <= 0 and colony_id in self.colonies:
                del self.colonies[colony_id]
            else:
                self._ensure_leader(colony_id)
                self._paint_colony_members(colony_id)

    # ------------------------------------------------------------------ steering
    def _base_turn(self, virus, noise_scale=1.0):
        virus.turn_rate = (
            virus.turn_rate * TURN_RATE_DAMP
            + random.uniform(-TURN_NOISE, TURN_NOISE) * noise_scale
        )
        if virus.turn_rate > TURN_RATE_MAX:
            virus.turn_rate = TURN_RATE_MAX
        elif virus.turn_rate < -TURN_RATE_MAX:
            virus.turn_rate = -TURN_RATE_MAX
        virus.angle = normalize_angle(virus.angle + virus.turn_rate * noise_scale)

    def _steer_leader(self, virus):
        """Leader goals: solo → clump/food; blob → hunt prey / rivals."""
        if FEAR_ENABLED and virus.flee_timer > 0:
            # Keep fleeing heading; small noise only
            self._base_turn(virus, noise_scale=0.3)
            return True
        if not FEAR_ENABLED:
            virus.flee_timer = 0

        colony = self._colony(virus.colony_id)
        food, threat, prey, rival, ally = self._scan_neighborhood(virus)

        self._base_turn(virus, noise_scale=1.0)

        if colony is not None and not colony.is_blob():
            # --- Solo particle goals ---
            # Kin clumping is always evaluated so food does not starve blob formation
            kin_angle, kin_dist = self._same_strain_solo_pull(virus)
            near_kin = kin_angle is not None and kin_dist is not None

            # 1) Any same-strain kin on the dish → head toward them (primary goal)
            if near_kin:
                strength = CLUMP_STRENGTH
                if kin_dist <= CLUMP_NEAR:
                    strength = min(0.98, CLUMP_STRENGTH + 0.15)
                elif kin_dist > 20:
                    # Far kin: still commit hard so sparse packs find each other
                    strength = min(0.95, CLUMP_STRENGTH + 0.10)
                virus.angle = self._blend_angle(virus.angle, kin_angle, strength)
                return True

            # 2) Seek food only when no kin to clump with
            if food is not None:
                toward = math.atan2(food[1] - virus.py, food[0] - virus.px)
                virus.angle = self._blend_angle(virus.angle, toward, SEEK_FOOD_STRENGTH)
                if FEAR_ENABLED and threat is not None:
                    tdx = threat[0] - virus.px
                    tdy = threat[1] - virus.py
                    tdist = math.sqrt(tdx * tdx + tdy * tdy)
                    if tdist < AVOID_BLOB_CLOSE:
                        away = angle_away_from(virus.px, virus.py, threat[0], threat[1])
                        virus.angle = self._blend_angle(
                            virus.angle, away, AVOID_BLOB_STRENGTH * 0.6,
                        )
                return True

            # 3) Avoid blobs when nothing else to do
            if FEAR_ENABLED and threat is not None:
                away = angle_away_from(virus.px, virus.py, threat[0], threat[1])
                tdx = threat[0] - virus.px
                tdy = threat[1] - virus.py
                tdist = math.sqrt(tdx * tdx + tdy * tdy)
                strength = AVOID_BLOB_STRENGTH
                if tdist < AVOID_BLOB_CLOSE:
                    strength = min(0.9, AVOID_BLOB_STRENGTH + 0.35)
                    virus.flee_timer = max(virus.flee_timer, 6)
                virus.angle = self._blend_angle(virus.angle, away, strength)
                return True
        else:
            # --- Blob leader goals: roam, merge with ally blobs, fight rivals ---
            large = colony is not None and colony.mass >= TENTACLE_MIN_MASS
            # Mark merge-seeking so step scale can boost
            virus.seeking_merge = False

            # 1) Same-strain other blob — primary: move to join/merge
            ally_pos, ally_dist = self._find_ally_blob(virus)
            if ally_pos is None and ally is not None:
                ally_pos = ally
                ally_dist = math.sqrt(
                    (ally[0] - virus.px) ** 2 + (ally[1] - virus.py) ** 2
                )
            if ally_pos is not None:
                toward = math.atan2(ally_pos[1] - virus.py, ally_pos[0] - virus.px)
                virus.angle = self._blend_angle(
                    virus.angle, toward, SEEK_BLOB_STRENGTH,
                )
                virus.seeking_merge = True
                return True

            # 2) Rival blobs — engage (infection)
            if rival is not None:
                rdx = rival[0] - virus.px
                rdy = rival[1] - virus.py
                if (rdx * rdx + rdy * rdy) <= float(COMBAT_SENSE * COMBAT_SENSE):
                    self._raise_combat(colony, virus)
                toward = math.atan2(rival[1] - virus.py, rival[0] - virus.px)
                virus.angle = self._blend_angle(virus.angle, toward, HUNT_RIVAL_STRENGTH)
                return True

            # 3) Prey solos
            if prey is not None:
                pdx = prey[0] - virus.px
                pdy = prey[1] - virus.py
                if (pdx * pdx + pdy * pdy) <= float(COMBAT_SENSE * COMBAT_SENSE):
                    self._raise_combat(colony, virus)
                toward = math.atan2(prey[1] - virus.py, prey[0] - virus.px)
                virus.angle = self._blend_angle(virus.angle, toward, HUNT_PREY_STRENGTH)
                return True

            # 4) Food snack — still keep a bit of exploration drift
            if food is not None:
                toward = math.atan2(food[1] - virus.py, food[0] - virus.px)
                strength = SEEK_FOOD_STRENGTH * (0.35 if large else 0.55)
                virus.angle = self._blend_angle(virus.angle, toward, strength)
                self._blob_explore_nudge(virus, colony, strength=0.25)
                virus.seeking_merge = False
                return True  # keep moving (exploring)

            # 5) No targets — explore the dish (never sit still)
            self._blob_explore(virus, colony)
            return True

        if self.tick % WANDER_CHECK_INTERVAL == 0:
            if random.randint(1, 4) == 1:
                virus.angle = normalize_angle(
                    virus.angle + random.uniform(-WANDER_ANGLE_JITTER, WANDER_ANGLE_JITTER),
                )
            if random.randint(1, ChanceOfSpeedup) == 1:
                virus.adjust_speed(-1)
            elif random.randint(1, ChanceOfSlowdown) == 1:
                virus.adjust_speed(1)
        return False

    def _pick_explore_waypoint(self, virus, colony):
        """Choose a new far-ish point on the dish for the pack to scout."""
        # Prefer points away from current position so packs cross the board
        for _ in range(12):
            tx = random.uniform(1.0, self.width - 1.0)
            ty = random.uniform(1.0, self.height - 1.0)
            dx = tx - virus.px
            dy = ty - virus.py
            if dx * dx + dy * dy >= 64.0:  # at least ~8 cells away
                colony.explore_tx = tx
                colony.explore_ty = ty
                colony.explore_timer = random.randint(
                    BLOB_EXPLORE_RETARGET_MIN, BLOB_EXPLORE_RETARGET_MAX,
                )
                return
        colony.explore_tx = random.uniform(1.0, self.width - 1.0)
        colony.explore_ty = random.uniform(1.0, self.height - 1.0)
        colony.explore_timer = random.randint(
            BLOB_EXPLORE_RETARGET_MIN, BLOB_EXPLORE_RETARGET_MAX,
        )

    def _blob_explore(self, virus, colony):
        """Drive the blob leader toward a roaming waypoint."""
        if colony is None:
            virus.angle = normalize_angle(
                virus.angle + random.uniform(-0.4, 0.4),
            )
            return
        if colony.explore_timer > 0:
            colony.explore_timer -= 1
        need_new = (
            colony.explore_tx is None
            or colony.explore_ty is None
            or colony.explore_timer <= 0
        )
        if not need_new:
            dx = colony.explore_tx - virus.px
            dy = colony.explore_ty - virus.py
            if dx * dx + dy * dy <= BLOB_EXPLORE_ARRIVE * BLOB_EXPLORE_ARRIVE:
                need_new = True
        if need_new:
            self._pick_explore_waypoint(virus, colony)
        toward = math.atan2(
            colony.explore_ty - virus.py,
            colony.explore_tx - virus.px,
        )
        virus.angle = self._blend_angle(
            virus.angle, toward, BLOB_EXPLORE_STRENGTH,
        )
        # Continuous curiosity noise so paths aren't straight rails
        virus.angle = normalize_angle(
            virus.angle + random.uniform(-BLOB_EXPLORE_WANDER, BLOB_EXPLORE_WANDER),
        )
        virus.seeking_merge = False

    def _blob_explore_nudge(self, virus, colony, strength=0.25):
        """Mild explore blend while also doing another goal (food, etc.)."""
        if colony is None:
            return
        if colony.explore_tx is None or colony.explore_timer <= 0:
            self._pick_explore_waypoint(virus, colony)
        if colony.explore_timer > 0:
            colony.explore_timer -= 1
        toward = math.atan2(
            colony.explore_ty - virus.py,
            colony.explore_tx - virus.px,
        )
        virus.angle = self._blend_angle(virus.angle, toward, strength)

    def _steer_tentacle(self, virus, leader):
        """Arm cells: tip reaches for food; segments trail the next outer cell."""
        ftx = virus.tentacle_tx
        fty = virus.tentacle_ty
        if ftx is None or fty is None:
            return self._steer_follower_wave(virus, leader)

        fdx = ftx - leader.px
        fdy = fty - leader.py
        flen = math.sqrt(fdx * fdx + fdy * fdy) or 1.0
        ux = fdx / flen
        uy = fdy / flen
        my_proj = (virus.px - leader.px) * ux + (virus.py - leader.py) * uy
        lead_dist = math.sqrt(
            (virus.px - leader.px) ** 2 + (virus.py - leader.py) ** 2
        )

        if virus.tentacle_tip:
            toward = math.atan2(fty - virus.py, ftx - virus.px)
            virus.angle = self._blend_angle(virus.angle, toward, TENTACLE_TIP_SEEK)
            # Shoot outward — keep speeding tips up
            if self.tick % 4 == 0:
                virus.adjust_speed(-1)
            # Weak leash only at extreme range (breaks free often → new blobs)
            if lead_dist > TENTACLE_STRETCH:
                back = math.atan2(leader.py - virus.py, leader.px - virus.px)
                virus.angle = self._blend_angle(
                    virus.angle, back, TENTACLE_LEASH_STRENGTH,
                )
            return True

        # Segment: chase the colony-mate further along the arm (higher proj)
        best = None
        best_proj = my_proj
        r = 2
        for dy in range(-r, r + 1):
            ny = virus.y + dy
            if ny < 0 or ny >= self.height:
                continue
            for dx in range(-r, r + 1):
                if dx == 0 and dy == 0:
                    continue
                nx = virus.x + dx
                if nx < 0 or nx >= self.width:
                    continue
                oid = int(self.grid[ny, nx])
                if oid < 0:
                    continue
                other = self.viruses.get(oid)
                if (
                    other is None
                    or not other.alive
                    or other.colony_id != virus.colony_id
                ):
                    continue
                if not other.tentacle:
                    continue
                o_proj = (other.px - leader.px) * ux + (other.py - leader.py) * uy
                if o_proj > best_proj:
                    best_proj = o_proj
                    best = other

        if best is not None:
            toward = math.atan2(best.py - virus.py, best.px - virus.px)
            virus.angle = self._blend_angle(
                virus.angle, toward, TENTACLE_SEGMENT_FOLLOW,
            )
            virus.angle = self._blend_angle(virus.angle, best.angle, 0.35)
            virus.speed = clamp_speed(int(round(
                float(virus.speed) * 0.5 + float(best.speed) * 0.5
            )))
        else:
            # No outer neighbor — crawl toward the food target yourself
            toward = math.atan2(fty - virus.py, ftx - virus.px)
            virus.angle = self._blend_angle(virus.angle, toward, 0.55)

        # Very soft body link — arms are allowed to snap off
        if lead_dist > TENTACLE_STRETCH * 0.9:
            back = math.atan2(leader.py - virus.py, leader.px - virus.px)
            virus.angle = self._blend_angle(
                virus.angle, back, TENTACLE_LEASH_STRENGTH * 0.5,
            )
        return True

    def _steer_follower_wave(self, virus, leader):
        """Body follows a forceful leader: wave + hard snap to leader path/speed."""
        ldx = leader.px - virus.px
        ldy = leader.py - virus.py
        my_lead_d2 = ldx * ldx + ldy * ldy
        my_lead_dist = math.sqrt(my_lead_d2)

        ax = 0.0
        ay = 0.0
        speed_acc = 0.0
        total = 0.0
        r = WAVE_RADIUS
        snap = getattr(self, "_heading_snap", None)

        for dy in range(-r, r + 1):
            ny = virus.y + dy
            if ny < 0 or ny >= self.height:
                continue
            for dx in range(-r, r + 1):
                if dx == 0 and dy == 0:
                    continue
                nx = virus.x + dx
                if nx < 0 or nx >= self.width:
                    continue
                oid = int(self.grid[ny, nx])
                if oid < 0:
                    continue
                other = self.viruses.get(oid)
                if (
                    other is None
                    or not other.alive
                    or other.colony_id != virus.colony_id
                ):
                    continue

                if snap is not None and oid in snap:
                    o_angle, o_speed, opx, opy = snap[oid]
                else:
                    o_angle, o_speed = other.angle, other.speed
                    opx, opy = other.px, other.py

                odx = leader.px - opx
                ody = leader.py - opy
                other_lead_d2 = odx * odx + ody * ody
                if other_lead_d2 > my_lead_d2 + 0.35:
                    continue

                n_dist = math.sqrt(float(dx * dx + dy * dy))
                w = (1.0 / max(0.5, n_dist)) * (1.0 + 2.0 / (1.0 + other_lead_d2))
                ax += math.cos(o_angle) * w
                ay += math.sin(o_angle) * w
                speed_acc += float(o_speed) * w
                total += w

        if total > 0.0:
            target = math.atan2(ay, ax)
            virus.angle = self._blend_angle(virus.angle, target, WAVE_BLEND)
            new_speed = speed_acc / total
            virus.speed = clamp_speed(int(round(
                float(virus.speed) * (1.0 - WAVE_SPEED_BLEND)
                + new_speed * WAVE_SPEED_BLEND
            )))
            virus.turn_rate *= 0.35

        # Forceful leader override — path and pace come from the head of the pack
        virus.angle = self._blend_angle(
            virus.angle, leader.angle, LEADER_HEADING_FORCE,
        )
        virus.speed = clamp_speed(int(round(
            float(virus.speed) * (1.0 - LEADER_SPEED_FORCE)
            + float(leader.speed) * LEADER_SPEED_FORCE
        )))
        virus.turn_rate = leader.turn_rate * 0.5

        # Hard reel toward leader so the body cannot refuse the turn
        catch = FOLLOW_CATCHUP_BLEND
        max_lag = FOLLOW_MAX_LAG
        if not virus.tentacle:
            catch = max(catch, TENTACLE_CORE_BLEND)
            max_lag = FOLLOW_MAX_LAG * 0.7

        if my_lead_dist > FOLLOW_CATCHUP_DIST:
            toward = math.atan2(ldy, ldx)
            if my_lead_dist >= max_lag:
                virus.angle = self._blend_angle(virus.angle, toward, min(0.98, catch * 1.4))
                # Extra position yank when lagging badly
                pull = min(0.45, 0.12 * my_lead_dist)
                virus.px += math.cos(toward) * pull
                virus.py += math.sin(toward) * pull
            else:
                t = (my_lead_dist - FOLLOW_CATCHUP_DIST) / max(
                    0.01, max_lag - FOLLOW_CATCHUP_DIST,
                )
                virus.angle = self._blend_angle(
                    virus.angle, toward, catch * min(1.0, t),
                )
        return my_lead_dist > FOLLOW_CATCHUP_DIST

    def _nearest_food_dist(self, virus):
        """Distance to nearest food pellet, or a large number if none / disabled."""
        if not FOOD_ENABLED or not self.food:
            return 1e9
        best = 1e9
        for (fx, fy) in self.food:
            dx = (fx + 0.5) - virus.px
            dy = (fy + 0.5) - virus.py
            d2 = dx * dx + dy * dy
            if d2 < best:
                best = d2
        return math.sqrt(best)

    def _apply_stickiness(self, virus):
        """Pull blob cells toward pack mates, biased toward the leader."""
        if virus.tentacle_tip:
            return  # tips can stretch; segments/core stay gluey
        lead = self._ensure_leader(virus.colony_id)
        ax = 0.0
        ay = 0.0
        n = 0.0
        r = STICKY_RADIUS
        for dy in range(-r, r + 1):
            ny = virus.y + dy
            if ny < 0 or ny >= self.height:
                continue
            for dx in range(-r, r + 1):
                if dx == 0 and dy == 0:
                    continue
                nx = virus.x + dx
                if nx < 0 or nx >= self.width:
                    continue
                oid = int(self.grid[ny, nx])
                if oid < 0:
                    continue
                other = self.viruses.get(oid)
                if (
                    other is None
                    or not other.alive
                    or other.colony_id != virus.colony_id
                ):
                    continue
                # Prefer core mates; leader counts extra so glue follows the head
                w = 2.0 if not other.tentacle else 0.6
                if lead is not None and other.virus_id == lead.virus_id:
                    w *= 3.0
                ax += other.px * w
                ay += other.py * w
                n += w
        if n <= 0:
            if lead is None or lead.virus_id == virus.virus_id:
                return
            ax, ay, n = lead.px, lead.py, 1.0
        else:
            ax /= n
            ay /= n
        # Bias sticky target toward leader so pack doesn't drag the head around
        if lead is not None and lead.virus_id != virus.virus_id:
            ax = ax * (1.0 - STICKY_LEADER_BIAS) + lead.px * STICKY_LEADER_BIAS
            ay = ay * (1.0 - STICKY_LEADER_BIAS) + lead.py * STICKY_LEADER_BIAS
        # Position glue
        virus.px += (ax - virus.px) * STICKY_POS_PULL
        virus.py += (ay - virus.py) * STICKY_POS_PULL
        # Heading: mild lean to pack, then re-assert leader path
        toward = math.atan2(ay - virus.py, ax - virus.px)
        virus.angle = self._blend_angle(virus.angle, toward, STICKINESS * 0.25)
        if lead is not None and lead.virus_id != virus.virus_id:
            virus.angle = self._blend_angle(
                virus.angle, lead.angle, LEADER_HEADING_FORCE * 0.5,
            )
        self._clamp_position(virus)

    def _steer_follower(self, virus, leader):
        if virus.tentacle and virus.tentacle_tx is not None:
            return self._steer_tentacle(virus, leader)
        return self._steer_follower_wave(virus, leader)

    def _steer_virus(self, virus):
        if FEAR_ENABLED and virus.flee_timer > 0:
            # Solo still steers away while fleeing
            if not self._is_blob_virus(virus):
                return self._steer_leader(virus)
            return False

        leader = self._ensure_leader(virus.colony_id)
        if leader is None or leader.virus_id == virus.virus_id:
            return self._steer_leader(virus)
        return self._steer_follower(virus, leader)

    def _integrate_virus(self, virus):
        if not virus.alive:
            return

        if not FEAR_ENABLED:
            virus.flee_timer = 0
        elif virus.flee_timer > 0:
            virus.flee_timer -= 1

        if virus.combat_timer > 0:
            virus.combat_timer -= 1

        lagging = self._steer_virus(virus)
        colony = self._colony(virus.colony_id)

        step = virus.drift_step()
        # --- Blob: sticky pack, food-aware pace, combat burst ---
        if colony is not None and colony.is_blob():
            combat = colony.in_combat() or virus.combat_timer > 0
            food_near = True
            if FOOD_AWARE_PACE:
                food_near = self._nearest_food_dist(virus) <= BLOB_FOOD_SENSE

            seeking_merge = virus.seeking_merge
            if not seeking_merge:
                lead = self._ensure_leader(virus.colony_id)
                if lead is not None and lead.seeking_merge:
                    seeking_merge = True
            if combat and colony.energy >= ENERGY_COMBAT_MIN:
                step *= BLOB_COMBAT_STEP_SCALE
                colony.energy = max(0.0, colony.energy - ENERGY_COMBAT_DRAIN)
                virus.energy = max(1.0, virus.energy - ENERGY_COMBAT_DRAIN * 0.4)
            elif seeking_merge:
                # Actively chasing another same-strain blob to join
                step *= BLOB_MERGE_STEP_SCALE
                colony.energy = min(
                    ENERGY_START * 4.0 + colony.mass * 2.0,
                    colony.energy + ENERGY_IDLE_REGEN * 0.5,
                )
            elif food_near or not FOOD_AWARE_PACE:
                # Default: keep exploring at solid cruise speed
                step *= BLOB_EXPLORE_STEP_SCALE if lagging else BLOB_IDLE_STEP_SCALE
                colony.energy = min(
                    ENERGY_START * 4.0 + colony.mass * 2.0,
                    colony.energy + ENERGY_IDLE_REGEN,
                )
            else:
                # No food nearby — conserve hard, almost torpid
                step *= BLOB_NO_FOOD_STEP_SCALE
                colony.energy = min(
                    ENERGY_START * 4.0 + colony.mass * 2.0,
                    colony.energy + ENERGY_IDLE_REGEN * 1.5,
                )
            # Large packs: extra push so they don't feel frozen
            if colony.mass >= BLOB_LARGE_MASS:
                step *= BLOB_LARGE_STEP_BOOST
            # Tentacles: stretch unless food-aware mode says otherwise
            if virus.tentacle and not combat:
                step *= 1.15 if food_near else 0.5
            elif virus.tentacle_tip and combat:
                step *= 1.1
        else:
            # Free particles keep normal pace
            if not self._is_leader(virus) and lagging:
                step *= 1.15
            elif self._is_leader(virus) and lagging:
                step *= 1.05

        virus.px += math.cos(virus.angle) * step
        virus.py += math.sin(virus.angle) * step
        self._clamp_position(virus)

        # Sticky cohesion for body only — never glue the leader in place
        if (
            colony is not None
            and colony.is_blob()
            and not virus.tentacle_tip
            and not self._is_leader(virus)
        ):
            self._apply_stickiness(virus)

        nx = int(virus.px)
        ny = int(virus.py)
        if nx < 0 or nx >= self.width or ny < 0 or ny >= self.height:
            return
        if nx == virus.x and ny == virus.y:
            # still try to eat if food lands under us
            self._try_eat_food(virus)
            return

        if not self._cell_is_free(nx, ny, virus.virus_id):
            other_id = self.grid[ny, nx]
            other = self.viruses.get(other_id)
            if other is None or not other.alive:
                self._clear_cell(ny, nx)
                self._occupy_cell(virus, nx, ny)
                return
            if other.virus_id == virus.virus_id:
                return

            colony_a = self._colony(virus.colony_id)
            colony_b = self._colony(other.colony_id)
            same_colony = other.colony_id == virus.colony_id
            same_strain = (
                colony_a is not None and colony_b is not None
                and colony_a.strain_key == colony_b.strain_key
            )

            if same_colony:
                lead = self._ensure_leader(virus.colony_id)
                is_lead = lead is not None and lead.virus_id == virus.virus_id
                if is_lead:
                    # Leader pushes through body cells (swap) so big packs don't freeze
                    ox, oy = other.x, other.y
                    lx, ly = virus.x, virus.y
                    self._clear_cell(ly, lx)
                    self._clear_cell(oy, ox)
                    other.x, other.y = lx, ly
                    other.px = float(lx) + 0.5
                    other.py = float(ly) + 0.5
                    virus.x, virus.y = ox, oy
                    virus.px = float(ox) + 0.5 + math.cos(virus.angle) * 0.25
                    virus.py = float(oy) + 0.5 + math.sin(virus.angle) * 0.25
                    self.grid[other.y, other.x] = other.virus_id
                    self.grid[virus.y, virus.x] = virus.virus_id
                    self._paint_cell(other.y, other.x, colony_a.color if colony_a else (0, 0, 0))
                    self._paint_cell(virus.y, virus.x, colony_a.color if colony_a else (0, 0, 0))
                    return
                # Followers: sticky collision — settle beside mate, don't scatter
                virus.px = float(virus.x) + 0.5 + random.uniform(-0.08, 0.08)
                virus.py = float(virus.y) + 0.5 + random.uniform(-0.08, 0.08)
                virus.angle = self._blend_angle(virus.angle, other.angle, STICKINESS)
                if lead is not None and lead.virus_id != virus.virus_id:
                    virus.angle = self._blend_angle(
                        virus.angle,
                        math.atan2(lead.py - virus.py, lead.px - virus.px),
                        0.45,
                    )
                self._apply_stickiness(virus)
                self._anchor_virus_to_cell(virus)
                self._anchor_virus_to_cell(other)
                return

            # Join / infect
            result = self._resolve_encounter(virus, other)
            # After join/infect, stay put so the blob remains visually packed.
            # Only plain blocks bounce away.
            if result == "block" and virus.alive:
                self._retreat_from_block(virus, hard=False)
            return

        self._occupy_cell(virus, nx, ny)

    def step(self):
        self.tick += 1
        self._spawn_food_tick()
        self._spawn_particle_tick()
        self._elect_leaders_tick()
        self._blob_fission_tick()

        # Tick down colony combat timers once per frame
        for colony in self.colonies.values():
            if colony.combat_timer > 0:
                colony.combat_timer -= 1

        # Snapshot headings so follower waves advance one neighbor-ring per tick
        # (angle, speed, px, py) — followers read this, not live mid-tick updates.
        self._heading_snap = {}
        for virus in self.viruses.values():
            if virus.alive:
                self._heading_snap[virus.virus_id] = (
                    virus.angle, virus.speed, virus.px, virus.py,
                )

        # Assign tentacle arms before movement so this tick uses fresh targets
        self._update_tentacles()

        leaders = []
        followers = []
        leader_of = {}
        for virus in self.viruses.values():
            if not virus.alive:
                continue
            leader = self._ensure_leader(virus.colony_id)
            leader_of[virus.virus_id] = leader
            if leader is not None and leader.virus_id == virus.virus_id:
                leaders.append(virus)
            else:
                followers.append(virus)

        random.shuffle(leaders)

        # Body wave: near-leader first. Tentacle tips last so arms trail outward.
        def _follow_order(v):
            lead = leader_of.get(v.virus_id)
            if lead is None:
                return (0, 0.0)
            dx = v.px - lead.px
            dy = v.py - lead.py
            d2 = dx * dx + dy * dy
            # non-tentacle first (0), tentacle segments (1), tips (2)
            if v.tentacle_tip:
                tier = 2
            elif v.tentacle:
                tier = 1
            else:
                tier = 0
            return (tier, d2)

        followers.sort(key=_follow_order)

        for virus in leaders:
            if virus.alive:
                self._integrate_virus(virus)
        for virus in followers:
            if virus.alive:
                self._integrate_virus(virus)

        self._enforce_unique_positions()
        # Broken tentacles / separated clumps become new color-variant blobs
        self._split_disconnected_groups()

        # Optional top-up of free particles (off while testing small counts)
        # solos = sum(
        #     1 for v in self.viruses.values()
        #     if v.alive and not self._is_blob_virus(v)
        # )
        # if solos < 6 and len(self.viruses) < MAX_VIRUSES:
        #     self.seed(count=4)

    def _enforce_unique_positions(self):
        self.grid[:, :] = -1
        self.rgb[:, :] = 0
        seen = set()
        for virus in self.viruses.values():
            if not virus.alive:
                continue
            key = (virus.x, virus.y)
            if key in seen or not (0 <= virus.x < self.width and 0 <= virus.y < self.height):
                empty = self._find_nearest_empty(virus.x, virus.y)
                if empty is None:
                    continue
                virus.x, virus.y = empty
                virus.px = float(virus.x) + random.uniform(0.2, 0.8)
                virus.py = float(virus.y) + random.uniform(0.2, 0.8)
                key = (virus.x, virus.y)
            if key in seen:
                continue
            seen.add(key)
            self.grid[virus.y, virus.x] = virus.virus_id
            colony = self._colony(virus.colony_id)
            if colony:
                self._paint_cell(virus.y, virus.x, colony.color)
        self._paint_food_layer()

    def _find_nearest_empty(self, cx, cy):
        for radius in range(1, max(self.width, self.height)):
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    if abs(dx) != radius and abs(dy) != radius:
                        continue
                    nx = cx + dx
                    ny = cy + dy
                    if 0 <= nx < self.width and 0 <= ny < self.height and self.grid[ny, nx] == -1:
                        return nx, ny
        return None

    def render(self):
        set_pixel = LED.TheMatrix.SetPixel
        rgb = self.rgb
        for y in range(self.height):
            row = rgb[y]
            for x in range(self.width):
                px = row[x]
                set_pixel(x, y, int(px[0]), int(px[1]), int(px[2]))


def PlayOutbreak3(duration_minutes, stop_event=None):
    dish = Playfield()
    count = dish.seed(INITIAL_VIRUS_COUNT)
    print("[Outbreak3] Seeded {} viruses + {} food on {}x{} (goals: food/blobs/convert)".format(
        count, len(dish.food), WIDTH, HEIGHT,
    ))

    start_time = time.time()
    running = True

    while running:
        if stop_event and stop_event.is_set():
            print("[Outbreak3] StopEvent received — shutting down")
            break

        if dish.tick >= MaxTicks:
            print("[Outbreak3] MaxTicks reached ({})".format(MaxTicks))
            break

        elapsed_min = (time.time() - start_time) / 60.0
        if elapsed_min >= duration_minutes:
            print("[Outbreak3] Duration reached ({:.1f} min, {} ticks)".format(
                duration_minutes, dish.tick,
            ))
            break

        dish.step()
        dish.render()

    LED.ClearBigLED()
    return dish.tick


def LaunchOutbreak3(duration=10, show_intro=True, stop_event=None):
    if show_intro:
        LED.ShowTitleScreen(
            BigText="OUTBRK3",
            BigTextRGB=LED.HighRed,
            BigTextShadowRGB=LED.ShadowRed,
            LittleText="EAT JOIN FIGHT",
            LittleTextRGB=LED.MedGreen,
            LittleTextShadowRGB=(0, 10, 0),
            ScrollText="FOOD  BLOBS  CONVERT",
            ScrollTextRGB=LED.MedYellow,
            ScrollSleep=0.03,
            DisplayTime=1,
            ExitEffect=0,
        )
        LED.ClearBigLED()

    PlayOutbreak3(duration, stop_event)


if __name__ == "__main__":
    LED.LoadConfigData()
    LaunchOutbreak3(duration=100000, show_intro=False, stop_event=None)
