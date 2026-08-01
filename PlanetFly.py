# =====================================================================================
# PLANET BLAST — orbital strike tour of a procedural world
#
# Title: "PLANET BLAST" letter zoom, then parallax space → planet approach →
# surface flyover with city targeting, bombing, night vision, and patrol.
#
# Launch:
#   LEDsim key 7 / LEDpanel / action "launch_planet" / ?planet
#   Idle rotation includes Planet Blast between games.
# =====================================================================================

from __future__ import annotations

import copy
import math
import random
import time

import LEDarcade as LED

LED.Initialize()

try:
    import pygame
    HAS_PYGAME = True
except Exception:
    HAS_PYGAME = False


# ---------------- Configuration ----------------
TARGET_FPS = 18
# Flight altitudes (feet) — top-down view; FOV → ground span
_FOV_DEG = 50.0
# City tour: zoom in until city ≈ CITY_TARGET_PX wide, bomb until gone, next
CITY_TARGET_PX = 20.0          # zoom until city footprint is ~this many pixels wide
CITY_WIDE_PX = 4.0             # overview size before zoom-in / after zoom-out
ZOOM_IN_SEC = 4.5
ZOOM_OUT_SEC = 4.0
# Alternate batches: 5 night targets, then 5 day, repeat until all gone
TARGETS_PER_BATCH = 5
NIGHT_DAY_MAX = 0.40           # day_factor ≤ this → night target
DAY_DAY_MIN = 0.58             # day_factor ≥ this → day target
# After every N cities bombed: peaceful patrol (no weapons)
PATROL_EVERY = 10              # cities destroyed before patrol
PATROL_SEC = 60.0              # patrol duration
PATROL_LEG_MIN = 5.0           # seconds between patrol waypoints
PATROL_LEG_MAX = 9.0
# Opening cruise over the surface before first target acquire
CRUISE_SEC = 60.0
CRUISE_LEG_MIN = 6.0
CRUISE_LEG_MAX = 10.0
CRUISE_TICKER_PPS = 18.0       # pixels/sec — ~1 px/frame @ 18fps for smooth marquee
# WARCOM / intel chatter + stats during opening cruise
_WARCOM_LINES = (
    "WARCOM: HOLD PATTERN",
    "WARCOM: WEAPONS COLD",
    "WARCOM: AWAIT AUTHORIZATION",
    "WARCOM: UPLINK NOMINAL",
    "WARCOM: SENSOR SWEEP ACTIVE",
    "WARCOM: DO NOT ENGAGE",
    "WARCOM: PACKAGE STANDBY",
    "WARCOM: CONFIRM ROE",
    "WARCOM: EYES ON SURFACE",
    "WARCOM: TRACKING THERMALS",
    "WARCOM: GRID LOCK PENDING",
    "WARCOM: ORBITAL FEED GREEN",
    "WARCOM: MAINTAIN HEADING",
    "WARCOM: NO FRIENDLIES MARKED",
    "WARCOM: CIVILIAN MASK HIGH",
    "WARCOM: ECM QUIET",
    "WARCOM: BIRDS IN THE PIPE",
    "WARCOM: STANDBY FOR TASKING",
    "WARCOM: PRIORITY TARGET LIST LOADING",
    "WARCOM: ATMOS ENTRY COMPLETE",
    "WARCOM: ALT HOLD",
    "WARCOM: COMM CHECK 1 2",
    "WARCOM: STRIKE WINDOW OPENING",
    "WARCOM: WATCH THE THERMALS",
    "WARCOM: CITY LIGHTS CONFIRMED",
    "WARCOM: NIGHT SIDE APPROACH",
    "WARCOM: DAY SIDE CLEAR",
    "INTEL: POPULATION DENSITY HIGH",
    "INTEL: INFRA GRID ONLINE",
    "INTEL: POWER NODES ACTIVE",
    "INTEL: TRANSIT LINKS LIVE",
    "INTEL: UNKNOWN AA SIGNATURE",
    "INTEL: FOREST FIRE RISK ELEVATED",
    "INTEL: COASTAL CITIES LIT",
    "INTEL: MEGA HUB IDENTIFIED",
    "INTEL: RURAL OUTPOSTS SPARSE",
    "INTEL: RIVER CROSSINGS MAPPED",
    "INTEL: HIGHWAY SPINE DETECTED",
    "INTEL: RAIL CORRIDOR HOT",
    "PILOT: VISUAL ON SURFACE",
    "PILOT: CRUISE NOMINAL",
    "PILOT: FUEL STATE GOOD",
    "PILOT: CAM FEED CLEAN",
    "PILOT: REQUESTING NEXT WAYPOINT",
    "PILOT: HOLDING PATTERN",
    "PILOT: CROSSWIND LIGHT",
    "SYS: NAV FIX OK",
    "SYS: HUD SYNC",
    "SYS: TICKER BUFFER FULL",
    "SYS: LINK 16 RELAY",
    "SYS: RECORDING PASS",
    "SYS: TELEMETRY NOMINAL",
    "ALERT: THERMAL SPIKE EAST",
    "ALERT: SMOKE COLUMN SIGHTED",
    "ALERT: POWER FLICKER IN GRID 7",
    "ALERT: UNKNOWN CONTACT LOST",
    "ALERT: WEATHER FRONT MOVING",
    "NOTE: REMEMBER THE ROE",
    "NOTE: CITIES FIRST",
    "NOTE: MINIMIZE COLLATERAL",
    "NOTE: LOG ALL IMPACTS",
    "NOTE: FIRE SPREAD POSSIBLE",
    "CHATTER: ANOTHER QUIET PASS",
    "CHATTER: WORLD LOOKS ALIVE",
    "CHATTER: TOO MANY LIGHTS",
    "CHATTER: THEY DONT KNOW YET",
    "CHATTER: CLOCK IS TICKING",
    "CHATTER: PRETTY FROM UP HERE",
    "CHATTER: DONT GET COMFORTABLE",
    "CHATTER: WARCOM IS LISTENING",
)
# End-of-cruise urgent attack orders ({world} filled at runtime)
CRUISE_ORDER_ALERT_SEC = 0.45   # red ALERT shows before scroll starts
CRUISE_ORDER_END_HOLD = 0.55    # hold after message finishes scrolling
_WARCOM_ATTACK_ORDERS = (
    "WARCOM URGENT: ATTACK {world}",
    "WARCOM FLASH: WEAPONS FREE — {world}",
    "WARCOM PRIORITY: ENGAGE ALL CITIES ON {world}",
    "WARCOM ORDER: BEGIN ORBITAL STRIKE ON {world}",
    "WARCOM URGENT: AUTHORIZE FULL PACKAGE — {world}",
    "WARCOM FLASH: GO HOT ON {world} NOW",
    "WARCOM ORDER: DESTROY SURFACE TARGETS — {world}",
    "WARCOM URGENT: STRIKE WINDOW OPEN — ATTACK {world}",
    "WARCOM FLASH: NO DELAY — BOMB {world}",
    "WARCOM PRIORITY: EXECUTE TASKING ON {world}",
    "WARCOM ORDER: WEAPONS RELEASE AUTHORIZED — {world}",
    "WARCOM URGENT: PLANET {world} IS HOSTILE — ATTACK",
    "WARCOM FLASH: CLEAR TO ENGAGE — {world}",
    "WARCOM ORDER: COMMENCE BOMBING RUNS ON {world}",
    "WARCOM URGENT: ALL FLIGHTS — ATTACK {world}",
    "WARCOM FLASH: ROE UPDATED — DESTROY CITIES ON {world}",
    "WARCOM PRIORITY: LIGHT THEM UP — {world}",
    "WARCOM ORDER: TARGET MEGACITIES FIRST — {world}",
    "WARCOM URGENT: BREAK CRUISE — ATTACK {world}",
    "WARCOM FLASH: MISSION IS GO ON {world}",
    "WARCOM ORDER: RAIN FIRE ON {world}",
    "WARCOM URGENT: SURFACE STRIKE AUTHORIZED — {world}",
    "WARCOM FLASH: DO NOT HOLD — ATTACK {world}",
    "WARCOM PRIORITY: LEVEL THE GRID ON {world}",
    "WARCOM ORDER: OPEN FIRE ON {world}",
    "WARCOM URGENT: PACKAGE AWAY WHEN READY — {world}",
    "WARCOM FLASH: WARCOM SAYS ATTACK {world}",
    "WARCOM ORDER: END THE QUIET — STRIKE {world}",
    "WARCOM URGENT: HOSTILE WORLD {world} — ENGAGE",
    "WARCOM FLASH: CLOCK ZERO — ATTACK {world}",
    "WARCOM PRIORITY: BURN THE SPINES OF {world}",
    "WARCOM ORDER: ALL BIRDS GO — {world}",
    "WARCOM URGENT: NO MORE HOLD — DESTROY {world}",
    "WARCOM FLASH: EXECUTE ORBITAL DOCTRINE ON {world}",
    "WARCOM ORDER: CITIES ARE THE PRIORITY — {world}",
    "WARCOM URGENT: YOU ARE CLEARED HOT ON {world}",
    "WARCOM FLASH: WAR PLAN ALPHA — ATTACK {world}",
    "WARCOM PRIORITY: LEAVE NOTHING STANDING ON {world}",
    "WARCOM ORDER: BEGIN GLASSING RUNS — {world}",
    "WARCOM URGENT: TARGET LIST LIVE — ATTACK {world}",
)
# Bombing run
BOMB_DROP_INTERVAL = 0.85      # seconds between bombs
BOMB_FALL_SEC = 1.15           # hang time while falling (shrinks)
BOMB_AIM_SPREAD = 0.55         # aim scatter as fraction of city radius (wide variance)
BOMB_AIM_LONGSHOT = 0.22       # chance of a long miss beyond normal spread
BOMB_DAMAGE = 0.14             # damage per hit near center (size scales)
SMOKE_RING_SEC = 2.4           # slow expanding smoke ring
FIRE_SEC = 1.8
CROSSHAIR_UP_PX = 4            # reticle is panel-center, this many px up
# Camera track error while bombing (city under reticle, imperfect)
CAM_AIM_ERR_M = 32_000.0       # max wander from ideal city lock (m)
CAM_AIM_WANDER = 0.55          # how fast aim error drifts
CROSSHAIR_LOCK_RGB = (255, 30, 20)   # red when weapons free / locked
CROSSHAIR_ACQ_LO = (12, 70, 28)      # dark green (targeting pulse low)
CROSSHAIR_ACQ_HI = (40, 255, 90)     # bright green (targeting pulse high)
BOMB_RGB = (48, 12, 72)            # dark purple shell
BOMB_SHELL_HI = (95, 35, 130)      # muted purple highlight
BOMB_CORE_RGB = (255, 30, 40)      # bright red core
SMOKE_RGB = (220, 218, 215)    # default pale white smoke
FIRE_RGB = (255, 40, 15)
FIRE_CORE = (255, 200, 40)
RUBBLE_RGB = (55, 48, 42)
ASH_RGB = (42, 36, 30)             # scorched forest floor (static paint)
ASH_EMBER = (70, 38, 22)           # static dark ember flecks in ash
# Wildfire: permanent scorched paint; rare slow spread ticks (not per-frame)
FIRE_CELL = 6_000.0                # meters per fire cell (coarser = cheaper)
FIRE_TICK_SEC = 2.8                # seconds between spread steps
FIRE_SPREAD_PER_TICK = 12          # max new cells painted per tick
FIRE_MAX_CELLS = 6_000             # hard cap
FIRE_SEED_DMG = 0.12               # city damage before it seeds wildfire
# Night vision (when dark): mono green; hot explosions → black
NV_DAY_THRESH = 0.38           # day_factor below this → NV on
NV_GAIN = 2.15                 # amplify surface contrast so terrain reads
NV_FLOOR = 18.0                # pedestal so oceans/land stay visible
NV_SURF_DAY = 0.78             # sample surface lit enough to show biome detail
# HUD — 3×5 micro font (teeny but readable on LED panels)
HUD_RGB = (40, 255, 90)          # targeting / scan green
HUD_FIRE_RGB = (255, 200, 40)    # firing amber
HUD_ALERT_RGB = (255, 50, 40)    # destroyed red
HUD_DIM_RGB = (20, 140, 70)
HUD_NAME_RGB = (180, 255, 200)   # acquired city name
# Alien-but-readable English city name parts
_NAME_ONSET = (
    "Zor", "Kel", "Vyn", "Ash", "Tor", "Xel", "Mir", "Qan", "Dra", "Nex",
    "Syl", "Vor", "Lun", "Pha", "Ryn", "Thal", "Bry", "Kor", "Jex", "Wyn",
    "Sael", "Orn", "Vesk", "Nyx", "Cra", "Hel", "Isk", "Ul", "Pra", "Ghy",
)
_NAME_CORE = (
    "a", "e", "i", "o", "u", "ae", "ia", "io", "ou", "y", "ei", "au",
)
_NAME_CODA = (
    "thar", "voss", "dria", "nox", "veil", "spire", "reach", "holm", "gate",
    "mere", "strand", "fall", "wick", "borne", "crest", "shade", "march",
    "haven", "forge", "rift", "vale", "watch", "point", "ridge", "delta",
)
_NAME_TITLE = (
    "", "", "", "Prime", "Minor", "Deep", "High", "Outer", "New", "Old",
)
# Planet names (readable English shape, alien worlds)
_PLANET_ONSET = (
    "Vor", "Kel", "Nyx", "Ash", "Xel", "Mir", "Thal", "Zor", "Sael", "Orn",
    "Dra", "Lun", "Pha", "Ryn", "Vesk", "Hel", "Isk", "Pra", "Qan", "Bry",
)
_PLANET_BODY = (
    "ath", "ion", "ara", "os", "is", "or", "eth", "ax", "ium", "ara",
    "on", "is", "ael", "une", "ora", "ith", "yx", "eus", "ara", "ion",
)
_PLANET_TAIL = (
    "", "", "", " Prime", " Minor", " Major", " Deep", " Reach",
)
# 3 wide × 5 tall bit rows (MSB left). Space = empty.
_HUD_GLYPHS = {
    " ": (0, 0, 0, 0, 0),
    "A": (0b010, 0b101, 0b111, 0b101, 0b101),
    "B": (0b110, 0b101, 0b110, 0b101, 0b110),
    "C": (0b011, 0b100, 0b100, 0b100, 0b011),
    "D": (0b110, 0b101, 0b101, 0b101, 0b110),
    "E": (0b111, 0b100, 0b110, 0b100, 0b111),
    "F": (0b111, 0b100, 0b110, 0b100, 0b100),
    "G": (0b011, 0b100, 0b101, 0b101, 0b011),
    "H": (0b101, 0b101, 0b111, 0b101, 0b101),
    "I": (0b111, 0b010, 0b010, 0b010, 0b111),
    "J": (0b001, 0b001, 0b001, 0b101, 0b010),
    "K": (0b101, 0b101, 0b110, 0b101, 0b101),
    "L": (0b100, 0b100, 0b100, 0b100, 0b111),
    "M": (0b101, 0b111, 0b111, 0b101, 0b101),
    "N": (0b101, 0b111, 0b111, 0b111, 0b101),
    "O": (0b010, 0b101, 0b101, 0b101, 0b010),
    "P": (0b110, 0b101, 0b110, 0b100, 0b100),
    "Q": (0b010, 0b101, 0b101, 0b111, 0b011),
    "R": (0b110, 0b101, 0b110, 0b101, 0b101),
    "S": (0b011, 0b100, 0b010, 0b001, 0b110),
    "T": (0b111, 0b010, 0b010, 0b010, 0b010),
    "U": (0b101, 0b101, 0b101, 0b101, 0b111),
    "V": (0b101, 0b101, 0b101, 0b101, 0b010),
    "W": (0b101, 0b101, 0b111, 0b111, 0b101),
    "X": (0b101, 0b101, 0b010, 0b101, 0b101),
    "Y": (0b101, 0b101, 0b010, 0b010, 0b010),
    "Z": (0b111, 0b001, 0b010, 0b100, 0b111),
    "0": (0b111, 0b101, 0b101, 0b101, 0b111),
    "1": (0b010, 0b110, 0b010, 0b010, 0b111),
    "2": (0b111, 0b001, 0b111, 0b100, 0b111),
    "3": (0b111, 0b001, 0b111, 0b001, 0b111),
    "4": (0b101, 0b101, 0b111, 0b001, 0b001),
    "5": (0b111, 0b100, 0b111, 0b001, 0b111),
    "6": (0b111, 0b100, 0b111, 0b101, 0b111),
    "7": (0b111, 0b001, 0b010, 0b010, 0b010),
    "8": (0b111, 0b101, 0b111, 0b101, 0b111),
    "9": (0b111, 0b101, 0b111, 0b001, 0b111),
    ".": (0b000, 0b000, 0b000, 0b000, 0b010),
    ":": (0b000, 0b010, 0b000, 0b010, 0b000),
    "-": (0b000, 0b000, 0b111, 0b000, 0b000),
    "!": (0b010, 0b010, 0b010, 0b000, 0b010),
    "?": (0b111, 0b001, 0b010, 0b000, 0b010),
    "/": (0b001, 0b001, 0b010, 0b100, 0b100),
    ">": (0b100, 0b010, 0b001, 0b010, 0b100),
    "*": (0b101, 0b010, 0b111, 0b010, 0b101),
}
_HUD_CHAR_W = 3
_HUD_CHAR_H = 5
_HUD_GAP = 1          # 1px between letters
# Ground speed as fraction of visible span per second (scroll feel)
CRUISE_SPAN_PER_SEC = 0.18
TURN_PERIOD = 22.0
LEG_MIN = 6.0
LEG_MAX = 12.0
# Noise world is continuous in meters; larger scale = bigger oceans/continents
CONTINENT_SCALE = 1.0 / 720_000.0   # broad continents
DETAIL_SCALE = 1.0 / 70_000.0
RIVER_SCALE = 1.0 / 32_000.0
MOUNTAIN_SCALE = 1.0 / 110_000.0
# ---- Space intro (parallax stars → planet dot → zoom) ----
STAR_DRIFT_SEC = 3.8       # pure starfield before the planet appears
PLANET_DOT_SEC = 1.6       # bright dot visible before zoom begins
PLANET_ZOOM_SEC = 3.8      # approach / grow the planet disc
STAR_DIM = 0.70            # match Space Explorer dimming feel
# Oversized wrap layers (Space Explorer style) — tall for vertical scroll
SPACE_LAYER_W = 160
SPACE_LAYER_H = 240
# Scroll rate divisors: higher = slower layer (Defender2 / SpaceExplorer)
# Foreground scrolls fastest (rate 3), far stars slowest (rate 14)
SPACE_FAR_RATE = 14.0
SPACE_BG_RATE = 8.0
SPACE_MID_RATE = 5.0
SPACE_FG_RATE = 3.0
# Base downward world speed (layer-px per second at rate=1 equivalent)
SPACE_SCROLL_V = 48.0


def _stop(StopEvent):
    try:
        return StopEvent is not None and StopEvent.is_set()
    except Exception:
        return False


def _clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def _lerp(a, b, t):
    return a + (b - a) * t


def _smoothstep(t):
    t = _clamp(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _lerp_rgb(c0, c1, t):
    t = _clamp(t, 0.0, 1.0)
    return (
        int(c0[0] + (c1[0] - c0[0]) * t),
        int(c0[1] + (c1[1] - c0[1]) * t),
        int(c0[2] + (c1[2] - c0[2]) * t),
    )


# ---------------- Hash noise (no deps) ----------------
def _hash2(ix, iy, seed):
    """Deterministic 0..1 hash of integer lattice + seed."""
    n = (ix * 374761393 + iy * 668265263 + seed * 1274126177) & 0x7FFFFFFF
    n = (n ^ (n >> 13)) * 1274126177
    n = n ^ (n >> 16)
    return (n & 0x7FFFFFFF) / float(0x7FFFFFFF)


def _value_noise(x, y, seed):
    """Bilinear value noise; x,y continuous."""
    x0 = int(math.floor(x))
    y0 = int(math.floor(y))
    fx = x - x0
    fy = y - y0
    # Smooth fade
    ux = fx * fx * (3.0 - 2.0 * fx)
    uy = fy * fy * (3.0 - 2.0 * fy)
    v00 = _hash2(x0, y0, seed)
    v10 = _hash2(x0 + 1, y0, seed)
    v01 = _hash2(x0, y0 + 1, seed)
    v11 = _hash2(x0 + 1, y0 + 1, seed)
    a = _lerp(v00, v10, ux)
    b = _lerp(v01, v11, ux)
    return _lerp(a, b, uy)


def _fbm(x, y, seed, octaves=5, lacunarity=2.05, gain=0.5):
    amp = 1.0
    freq = 1.0
    total = 0.0
    norm = 0.0
    for i in range(octaves):
        total += amp * _value_noise(x * freq, y * freq, seed + i * 1013)
        norm += amp
        amp *= gain
        freq *= lacunarity
    return total / max(1e-9, norm)


# ---------------- Shared planet surface map ----------------
# World coords are meters on an equirectangular unwrap; same map for globe + flyover.
PLANET_R = 2_000_000.0       # map scale: lon/lat * PLANET_R → meters
# Elevation threshold: ~75% of the surface is ocean (land only above this)
SEA_LEVEL = 0.58
CITY_CELL = 80_000.0         # spatial hash cell for cities/roads (m)
ROAD_RGB = (55, 55, 58)
HIGHWAY_RGB = (70, 70, 75)
RAIL_RGB = (40, 32, 28)
BRIDGE_RGB = (110, 100, 90)
CITY_DAY = (105, 105, 112)       # readable gray urban mass from altitude
CITY_DAY_CORE = (130, 128, 125)  # denser core
CITY_NIGHT = (255, 200, 90)
CITY_GLOW = (255, 140, 40)


def _smooth_edge(v, a, b):
    """0..1 smoothstep across [a,b]."""
    if b <= a:
        return 1.0 if v >= a else 0.0
    return _smoothstep((v - a) / (b - a))


def _dist_point_seg(px, py, x0, y0, x1, y1):
    dx, dy = x1 - x0, y1 - y0
    len2 = dx * dx + dy * dy
    if len2 < 1e-6:
        return math.hypot(px - x0, py - y0)
    t = _clamp(((px - x0) * dx + (py - y0) * dy) / len2, 0.0, 1.0)
    return math.hypot(px - (x0 + t * dx), py - (y0 + t * dy))


def _generate_alien_city_name(rng, size=3):
    """
    Readable English-shaped name with alien flavor.
    Examples: Zorvoss, Kelthar Prime, Vynspire, Ashdria, Xelreach.
    """
    onset = rng.choice(_NAME_ONSET)
    # Sometimes glue onset + coda; sometimes insert a vowel core
    if rng.random() < 0.55:
        name = onset + rng.choice(_NAME_CODA)
    else:
        core = rng.choice(_NAME_CORE)
        coda = rng.choice(_NAME_CODA)
        # Avoid ugly triple vowels
        if onset[-1] in "aeiouyAEIOUY" and core[0] in "aeiouy":
            name = onset + coda
        else:
            name = onset + core + coda
    # Title for larger settlements
    if size >= 4 and rng.random() < 0.45:
        title = rng.choice(_NAME_TITLE)
        if title:
            name = name + " " + title
    elif size >= 5 and rng.random() < 0.55:
        title = rng.choice([t for t in _NAME_TITLE if t] or ["Prime"])
        name = name + " " + title
    # Normalize casing: Title Case for multi-word
    parts = name.split()
    parts = [p[:1].upper() + p[1:].lower() if p else p for p in parts]
    return " ".join(parts)


def _assign_city_names(cities, seed):
    """Unique alien names for every city."""
    rng = random.Random(int(seed) ^ 0xA11E11)
    used = set()
    for c in cities:
        for _ in range(40):
            nm = _generate_alien_city_name(rng, size=int(c.get("size", 3)))
            key = nm.upper()
            if key not in used:
                used.add(key)
                c["name"] = nm
                break
        else:
            c["name"] = "Node " + str(len(used) + 1)
            used.add(c["name"].upper())


def _generate_planet_name(seed):
    """Readable alien world name, e.g. Voreth, Kelion Prime, Nyxara."""
    rng = random.Random(int(seed) ^ 0x51A7E7)
    onset = rng.choice(_PLANET_ONSET)
    body = rng.choice(_PLANET_BODY)
    # Avoid awkward vowel piles
    if onset[-1].lower() in "aeiouy" and body[0] in "aeiouy":
        body = rng.choice([b for b in _PLANET_BODY if b[0] not in "aeiouy"] or _PLANET_BODY)
    name = onset + body
    name = name[:1].upper() + name[1:].lower()
    tail = rng.choice(_PLANET_TAIL)
    if tail:
        name = name + tail
    return name


class PlanetMap(object):
    """
    One consistent planetary surface: terrain, rivers, cities, highways,
    railways, bridges. Used for both globe zoom and surface flight.
    """

    def __init__(self, seed=None):
        self.seed = int(seed if seed is not None else random.randint(1, 1_000_000))
        # Sun: randomized so each approach sees different day/night mix
        rng_sun = random.Random(self.seed ^ 0x50A1)
        self.sun_lon = rng_sun.uniform(-math.pi, math.pi)
        # Sphere light direction roughly consistent with sun_lon (slight tilt)
        tilt = rng_sun.uniform(-0.35, 0.35)
        self.sun = self._norm(
            math.sin(self.sun_lon),
            tilt,
            math.cos(self.sun_lon),
        )
        self.name = _generate_planet_name(self.seed)
        self.cities = []     # dict x,y,size (1..5), name-ish
        self.roads = []      # dict x0,y0,x1,y1,kind highway|rail|road, width
        self.city_grid = {}  # (cx,cy) -> [city indices]
        self.road_grid = {}  # (cx,cy) -> [road indices]
        # Wildfire: permanent scorched cells + sparse frontier for slow spread
        self.fire_scorch = set()   # {(ix,iy)} painted ash forever
        self.fire_front = []      # keys that may still expand into green
        self._fire_tick_t = 0.0
        self._build_civilization()
        print(
            f"[PlanetBlast] World {self.name}  seed={self.seed}  "
            f"cities={len(self.cities)}  routes={len(self.roads)}"
        )

    @staticmethod
    def _norm(x, y, z):
        m = math.sqrt(x * x + y * y + z * z) or 1.0
        return (x / m, y / m, z / m)

    def elev_raw(self, wx, wy):
        c = _fbm(wx * CONTINENT_SCALE, wy * CONTINENT_SCALE, self.seed, octaves=3)
        d = _fbm(wx * DETAIL_SCALE, wy * DETAIL_SCALE, self.seed + 7, octaves=2)
        m_raw = _fbm(wx * MOUNTAIN_SCALE, wy * MOUNTAIN_SCALE, self.seed + 19, octaves=2)
        mountain = 1.0 - abs(2.0 * m_raw - 1.0)
        mountain *= mountain
        # Continent-scale dominates so land forms large coherent masses
        elev = _clamp(c * 0.72 + d * 0.14 + mountain * 0.14, 0.0, 1.0)
        return elev, c, d, mountain

    def is_river(self, wx, wy, elev, moist):
        river_n = _value_noise(wx * RIVER_SCALE, wy * RIVER_SCALE, self.seed + 55)
        river_ridge = 1.0 - abs(2.0 * river_n - 1.0)
        river_w = _smooth_edge(river_ridge, 0.84, 0.96)
        river_ok = _smooth_edge(elev, SEA_LEVEL + 0.01, SEA_LEVEL + 0.04)
        river_ok *= 1.0 - _smooth_edge(elev, 0.68, 0.78)
        river_ok *= _smooth_edge(moist, 0.28, 0.45)
        return river_w * river_ok

    def is_land(self, wx, wy):
        elev, _, _, _ = self.elev_raw(wx, wy)
        return elev >= SEA_LEVEL + 0.02

    def world_from_sphere(self, nx, ny, nz):
        """Map unit sphere normal → world meters (equirectangular unwrap)."""
        lon = math.atan2(nx, nz)
        lat = math.asin(_clamp(ny, -1.0, 1.0))
        return lon * PLANET_R, lat * PLANET_R

    def sphere_from_world(self, wx, wy):
        lon = wx / PLANET_R
        lat = _clamp(wy / PLANET_R, -math.pi * 0.5 + 0.01, math.pi * 0.5 - 0.01)
        cl = math.cos(lat)
        return (math.sin(lon) * cl, math.sin(lat), math.cos(lon) * cl)

    def day_factor_flat(self, wx, wy):
        """Day amount on the unwrapped map from sun longitude (soft terminator)."""
        lon = wx / PLANET_R
        # cos(lon - sun_lon): 1 = noon, -1 = midnight
        return _clamp(0.5 + 0.55 * math.cos(lon - self.sun_lon), 0.0, 1.0)

    def day_factor_sphere(self, nx, ny, nz):
        """Day amount from planet-surface normal vs sun direction."""
        s = self.sun
        raw = nx * s[0] + ny * s[1] + nz * s[2]
        # Soft terminator — not a hard cut
        return _smooth_edge(raw, -0.15, 0.28)

    def is_twilight(self, wx, wy, lo=0.18, hi=0.58):
        """True if world point sits near the day/night terminator."""
        d = self.day_factor_flat(wx, wy)
        return lo <= d <= hi

    def twilight_score(self, wx, wy, ideal=0.36):
        """
        Higher = closer to dusk/dawn band (ideal ~ NV edge / soft terminator).
        1.0 at ideal day_factor, falls off toward full day or full night.
        """
        d = self.day_factor_flat(wx, wy)
        return max(0.0, 1.0 - abs(d - ideal) / 0.42)

    def pick_landing(self):
        """Prefer temperate land for flyover start."""
        for _ in range(80):
            wx = random.uniform(-math.pi * PLANET_R * 0.9, math.pi * PLANET_R * 0.9)
            wy = random.uniform(-PLANET_R * 0.55, PLANET_R * 0.55)
            elev, c, _, _ = self.elev_raw(wx, wy)
            if elev > SEA_LEVEL + 0.04 and elev < 0.75 and abs(wy) < PLANET_R * 0.65:
                return wx, wy
        return 0.0, 0.0

    def city_lighting_side(self, city):
        """'night', 'day', or 'twilight' from current sun."""
        d = self.day_factor_flat(city["x"], city["y"])
        if d <= NIGHT_DAY_MAX:
            return "night"
        if d >= DAY_DAY_MIN:
            return "day"
        return "twilight"

    def _place_sun_for_side(self, city, side):
        """Orient sun so city is solidly night or day."""
        city_lon = float(city["x"]) / PLANET_R
        if side == "night":
            # day_factor ≈ 0.22 → cos ≈ -0.51
            cos_t = (0.22 - 0.5) / 0.55
        else:
            # day_factor ≈ 0.88 → cos ≈ 0.69
            cos_t = (0.88 - 0.5) / 0.55
        cos_t = _clamp(cos_t, -1.0, 1.0)
        offset = math.acos(cos_t)
        if random.random() < 0.5:
            offset = -offset
        self.sun_lon = city_lon - offset + random.uniform(-0.06, 0.06)

    def _place_sun_for_twilight(self, city):
        """Orient sun so the city is near dusk (day_factor ≈ 0.36)."""
        city_lon = float(city["x"]) / PLANET_R
        offset = math.acos(_clamp(-0.255, -1.0, 1.0))
        if random.random() < 0.35:
            offset = -offset
        self.sun_lon = city_lon - offset + random.uniform(-0.08, 0.08)

    def pick_city_for_side(self, side, exclude=None, prefer_unvisited=None):
        """Intact city on the night or day side of the terminator."""
        side = "night" if side != "day" else "day"
        exclude = exclude or ()
        candidates = [
            c for c in self.cities
            if c not in exclude and not c.get("obliterated")
        ]
        if prefer_unvisited is not None:
            unvis = [c for c in candidates if id(c) not in prefer_unvisited]
            if unvis:
                candidates = unvis
        if not candidates:
            for c in self.cities:
                c["damage"] = 0.0
                c["obliterated"] = False
            candidates = [c for c in self.cities if c not in exclude] or list(self.cities)

        def matches(c):
            d = self.day_factor_flat(c["x"], c["y"])
            if side == "night":
                return d <= NIGHT_DAY_MAX
            return d >= DAY_DAY_MIN

        pool = [c for c in candidates if matches(c)]
        if not pool:
            pool_src = [c for c in candidates if c["size"] >= 3] or candidates
            if not pool_src:
                return self.pick_showcase_city()
            pick = random.choice(pool_src)
            self._place_sun_for_side(pick, side)
            return pick

        scored = []
        for c in pool:
            d = self.day_factor_flat(c["x"], c["y"])
            if side == "night":
                side_pref = (NIGHT_DAY_MAX - d) * 4.0
            else:
                side_pref = (d - DAY_DAY_MIN) * 4.0
            scored.append((c["size"] * 2.0 + side_pref + random.random(), c))
        scored.sort(key=lambda t: -t[0])
        return random.choice(scored[: max(3, min(8, len(scored)))])[1]

    def pick_approach_site(self):
        """
        Random surface site for globe zoom-in. Does NOT reorient the sun,
        so day/night framing varies each run.
        """
        big = [c for c in self.cities if c["size"] >= 3]
        if not big:
            big = list(self.cities)
        if big:
            # Prefer larger cities but pick among a random shortlist
            scored = [(c["size"] + random.random() * 2.0, c) for c in big]
            scored.sort(key=lambda t: -t[0])
            return random.choice(scored[: max(4, min(12, len(scored)))])[1]
        x, y = self.pick_landing()
        c = {
            "x": x, "y": y, "size": 4, "pulse": 0.0,
            "damage": 0.0, "obliterated": False, "name": "",
        }
        _assign_city_names([c], self.seed ^ 0xA22)
        self.cities.append(c)
        key = self._cell(x, y)
        self.city_grid.setdefault(key, []).append(len(self.cities) - 1)
        return c

    def pick_showcase_city(self):
        """
        Prefer a large city for opening play. Does not force night lighting —
        sun stays put so approach day/night varies. Night batch targeting
        is handled later via pick_city_for_side.
        """
        return self.pick_approach_site()

    def pick_twilight_city(self, exclude=None, prefer_unvisited=None):
        """Legacy helper: intact city near the day/night border."""
        exclude = exclude or ()
        candidates = [
            c for c in self.cities
            if c not in exclude and not c.get("obliterated")
        ]
        if prefer_unvisited is not None:
            unvis = [c for c in candidates if id(c) not in prefer_unvisited]
            if unvis:
                candidates = unvis
        if not candidates:
            return self.pick_showcase_city()
        scored = []
        for c in candidates:
            if not self.is_twilight(c["x"], c["y"]):
                continue
            tw = self.twilight_score(c["x"], c["y"])
            scored.append((c["size"] * 1.5 + tw * 10.0 + random.random(), c))
        if not scored:
            pool = [c for c in candidates if c["size"] >= 3] or candidates
            pick = random.choice(pool)
            self._place_sun_for_twilight(pick)
            return pick
        scored.sort(key=lambda t: -t[0])
        return random.choice(scored[: max(3, min(8, len(scored)))])[1]

    def _cell(self, wx, wy):
        return (int(math.floor(wx / CITY_CELL)), int(math.floor(wy / CITY_CELL)))

    def _build_civilization(self):
        rng = random.Random(self.seed ^ 0xC17E5)
        # Cities of varying sizes on land
        attempts = 0
        while len(self.cities) < 90 and attempts < 800:
            attempts += 1
            wx = rng.uniform(-math.pi * PLANET_R, math.pi * PLANET_R)
            wy = rng.uniform(-PLANET_R * 0.85, PLANET_R * 0.85)
            elev, _, _, _ = self.elev_raw(wx, wy)
            if elev < SEA_LEVEL + 0.03 or elev > 0.78:
                continue
            moist = _fbm(
                wx * DETAIL_SCALE * 0.7, wy * DETAIL_SCALE * 0.7,
                self.seed + 31, octaves=2,
            )
            # Avoid pure desert wasteland for large cities
            r = rng.random()
            if r < 0.10:
                size = 5  # megacity
            elif r < 0.28:
                size = 4
            elif r < 0.50:
                size = 3
            elif r < 0.75:
                size = 2
            else:
                size = 1
            if moist < 0.25 and size >= 4:
                size = 2
            # Spacing
            ok = True
            min_d = 35_000 + size * 22_000
            for c in self.cities:
                if math.hypot(c["x"] - wx, c["y"] - wy) < min_d:
                    ok = False
                    break
            if not ok:
                continue
            self.cities.append({
                "x": wx, "y": wy, "size": size,
                "pulse": rng.random() * math.pi * 2,
                "damage": 0.0,
                "obliterated": False,
                "name": "",
            })
        # Guarantee at least a few large cities for the opening zoom
        while sum(1 for c in self.cities if c["size"] >= 4) < 4 and attempts < 1200:
            attempts += 1
            wx = rng.uniform(-math.pi * PLANET_R * 0.8, math.pi * PLANET_R * 0.8)
            wy = rng.uniform(-PLANET_R * 0.5, PLANET_R * 0.5)
            if not self.is_land(wx, wy):
                continue
            size = 5 if rng.random() < 0.4 else 4
            ok = all(
                math.hypot(c["x"] - wx, c["y"] - wy) > 60_000 for c in self.cities
            )
            if not ok:
                continue
            self.cities.append({
                "x": wx, "y": wy, "size": size,
                "pulse": rng.random() * math.pi * 2,
                "damage": 0.0,
                "obliterated": False,
                "name": "",
            })
        _assign_city_names(self.cities, self.seed)
        # Spatial hash cities
        for i, c in enumerate(self.cities):
            key = self._cell(c["x"], c["y"])
            self.city_grid.setdefault(key, []).append(i)

        # Highways / roads between nearby cities; rails between large ones
        for i, a in enumerate(self.cities):
            # nearest neighbors
            dists = []
            for j, b in enumerate(self.cities):
                if i == j:
                    continue
                d = math.hypot(a["x"] - b["x"], a["y"] - b["y"])
                dists.append((d, j))
            dists.sort()
            n_conn = 1 + (1 if a["size"] >= 3 else 0) + (1 if a["size"] >= 5 else 0)
            for d, j in dists[:n_conn]:
                if d > 450_000:
                    break
                b = self.cities[j]
                if i > j:
                    continue  # add once
                if a["size"] >= 3 and b["size"] >= 3 and d < 380_000 and rng.random() < 0.55:
                    kind = "rail"
                    width = 900.0
                elif a["size"] >= 2 and b["size"] >= 2 and d < 320_000:
                    kind = "highway"
                    width = 1400.0
                else:
                    kind = "road"
                    width = 900.0
                self.roads.append({
                    "x0": a["x"], "y0": a["y"],
                    "x1": b["x"], "y1": b["y"],
                    "kind": kind, "width": width,
                })
        # Hash roads into cells along each segment
        for ri, rd in enumerate(self.roads):
            steps = max(2, int(math.hypot(rd["x1"] - rd["x0"], rd["y1"] - rd["y0"]) / (CITY_CELL * 0.5)))
            for s in range(steps + 1):
                t = s / float(steps)
                x = _lerp(rd["x0"], rd["x1"], t)
                y = _lerp(rd["y0"], rd["y1"], t)
                key = self._cell(x, y)
                self.road_grid.setdefault(key, []).append(ri)

    def _nearby_roads(self, wx, wy):
        cx, cy = self._cell(wx, wy)
        seen = set()
        out = []
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                for ri in self.road_grid.get((cx + dx, cy + dy), ()):
                    if ri not in seen:
                        seen.add(ri)
                        out.append(self.roads[ri])
        return out

    def _nearby_cities(self, wx, wy):
        # Wider stencil — megacities span multiple cells
        cx, cy = self._cell(wx, wy)
        out = []
        for dy in (-2, -1, 0, 1, 2):
            for dx in (-2, -1, 0, 1, 2):
                for i in self.city_grid.get((cx + dx, cy + dy), ()):
                    out.append(self.cities[i])
        return out

    def _fire_key(self, wx, wy):
        return (
            int(math.floor(wx / FIRE_CELL)),
            int(math.floor(wy / FIRE_CELL)),
        )

    def _fire_key_center(self, key):
        ix, iy = key
        return (ix + 0.5) * FIRE_CELL, (iy + 0.5) * FIRE_CELL

    def is_green_fuel(self, wx, wy):
        """True if terrain is grass/forest that can burn (not desert/ice/water/rock)."""
        elev, _, _, mountain = self.elev_raw(wx, wy)
        if elev < SEA_LEVEL + 0.01:
            return False
        moist = _fbm(
            wx * DETAIL_SCALE * 0.7, wy * DETAIL_SCALE * 0.7,
            self.seed + 31, octaves=2,
        )
        lat_norm = _clamp(wy / (PLANET_R * (math.pi * 0.5)), -1.0, 1.0)
        ice_lat = _smooth_edge(abs(lat_norm), 2.0 / 3.0, 2.0 / 3.0 + 0.06)
        if ice_lat > 0.35:
            return False
        land_h = (elev - SEA_LEVEL) / max(1e-6, 1.0 - SEA_LEVEL)
        if land_h > 0.70 or mountain > 0.72:
            return False
        t_dry = 1.0 - _smooth_edge(moist, 0.22, 0.42)
        if t_dry > 0.72:
            return False  # desert scrub — little fuel
        # Grass and especially forest (wetter) burn
        return moist > 0.24

    def _ignite_cell(self, key):
        """
        Paint a green cell as permanent scorched ground (no animation).
        Returns True if newly painted.
        """
        if key in self.fire_scorch:
            return False
        if len(self.fire_scorch) >= FIRE_MAX_CELLS:
            return False
        wx, wy = self._fire_key_center(key)
        if not self.is_green_fuel(wx, wy):
            return False
        self.fire_scorch.add(key)
        self.fire_front.append(key)
        # Cap frontier list
        if len(self.fire_front) > 800:
            self.fire_front = self.fire_front[-400:]
        return True

    def seed_city_wildfire(self, city):
        """One-shot: paint scorched ring around a burning city (not every frame)."""
        dmg = _clamp(float(city.get("damage", 0.0)), 0.0, 1.0)
        if not city.get("obliterated") and dmg < FIRE_SEED_DMG:
            return
        cr = 12_000.0 + city["size"] * 14_000.0
        ring0 = cr * 0.55
        ring1 = cr * (1.05 + 0.35 * dmg)
        # Sparse seeds only — cheap paint, slow later spread fills gaps
        steps = max(6, int((ring1 * 1.4) / FIRE_CELL))
        cx, cy = float(city["x"]), float(city["y"])
        for i in range(steps):
            ang = (i / float(steps)) * math.pi * 2.0
            rad = ring0 if (i % 2 == 0) else ring1
            self._ignite_cell(self._fire_key(
                cx + math.cos(ang) * rad,
                cy + math.sin(ang) * rad,
            ))
        for _ in range(2 + int(dmg * 2)):
            ang = random.uniform(0, math.pi * 2)
            rad = random.uniform(ring0, ring1)
            self._ignite_cell(self._fire_key(
                cx + math.cos(ang) * rad,
                cy + math.sin(ang) * rad,
            ))

    def seed_impact_wildfire(self, wx, wy, strength=1.0):
        """Bomb impact paints a small scorched patch (static)."""
        r_cells = 1 + int(1.5 * _clamp(strength, 0.0, 1.0))
        ix, iy = self._fire_key(wx, wy)
        for dy in range(-r_cells, r_cells + 1):
            for dx in range(-r_cells, r_cells + 1):
                if dx * dx + dy * dy > r_cells * r_cells + 1:
                    continue
                self._ignite_cell((ix + dx, iy + dy))

    def update_wildfire(self, dt):
        """
        Rare slow spread tick only — no per-frame fuel/flame simulation.
        Each tick paints a few new permanent ash cells at the frontier.
        """
        if dt <= 0 or not self.fire_front:
            return
        self._fire_tick_t += dt
        if self._fire_tick_t < FIRE_TICK_SEC:
            return
        self._fire_tick_t = 0.0

        # Sample a handful of frontier cells; expand into one green neighbor each
        front = self.fire_front
        if len(front) > 200:
            # Random subset — don't walk thousands of cells
            picks = [front[random.randrange(len(front))] for _ in range(min(40, len(front)))]
        else:
            picks = list(front)
            random.shuffle(picks)
            picks = picks[:40]

        new_front = []
        painted = 0
        nbrs_all = ((1, 0), (-1, 0), (0, 1), (0, -1))
        for key in picks:
            if painted >= FIRE_SPREAD_PER_TICK:
                new_front.append(key)
                continue
            ix, iy = key
            order = list(nbrs_all)
            random.shuffle(order)
            expanded = False
            for dx, dy in order:
                nkey = (ix + dx, iy + dy)
                if self._ignite_cell(nkey):
                    new_front.append(nkey)
                    painted += 1
                    expanded = True
                    break
            # Keep cell on frontier if it still might expand later
            if not expanded:
                # Chance to drop dead-end cells from the front list
                if random.random() < 0.35:
                    continue
            new_front.append(key)

        # Merge remaining front (keep some old edge)
        keep = [k for k in front[-120:] if k in self.fire_scorch]
        self.fire_front = (keep + new_front)[-500:]

    def is_scorched(self, wx, wy):
        """True if this world point is permanent wildfire ash paint."""
        if not self.fire_scorch:
            return False
        return self._fire_key(wx, wy) in self.fire_scorch

    def sample_biome(self, wx, wy):
        """Daytime surface color + meta (elev, river strength, land)."""
        elev, c, d, mountain = self.elev_raw(wx, wy)
        moist = _fbm(
            wx * DETAIL_SCALE * 0.7, wy * DETAIL_SCALE * 0.7,
            self.seed + 31, octaves=2,
        )
        # Geographic latitude −1..+1 (south..north) from equirectangular map
        lat_norm = _clamp(wy / (PLANET_R * (math.pi * 0.5)), -1.0, 1.0)

        deep = (8, 25, 70)
        mid_sea = (15, 55, 120)
        shallow = (40, 130, 170)
        foam = (120, 160, 175)  # muted shore foam — not white
        river_amt = 0.0
        if elev < SEA_LEVEL:
            t_deep = _smooth_edge(elev, SEA_LEVEL - 0.14, SEA_LEVEL - 0.06)
            rgb = _lerp_rgb(deep, mid_sea, t_deep)
            t_shal = _smooth_edge(elev, SEA_LEVEL - 0.07, SEA_LEVEL - 0.01)
            rgb = _lerp_rgb(rgb, shallow, t_shal)
            t_foam = _smooth_edge(elev, SEA_LEVEL - 0.015, SEA_LEVEL)
            rgb = _lerp_rgb(rgb, foam, t_foam * 0.22)
            land = False
        else:
            land = True
            land_h = (elev - SEA_LEVEL) / max(1e-6, 1.0 - SEA_LEVEL)
            desert = _lerp_rgb((170, 150, 90), (200, 170, 100), land_h)
            grass = _lerp_rgb((50, 110, 40), (90, 140, 50), land_h * 0.6 + moist * 0.3)
            forest = _lerp_rgb((20, 80, 30), (35, 110, 40), 0.4 + 0.4 * land_h)
            rock = _lerp_rgb((90, 85, 75), (160, 155, 145), _smooth_edge(land_h, 0.45, 0.85))
            rock = _lerp_rgb(rock, (70, 95, 60), _smooth_edge(moist, 0.45, 0.75) * 0.3)
            # Snow/ice only in the top & bottom 1/6 of the planet (|lat| > 2/3)
            snow = _lerp_rgb((200, 210, 220), (235, 240, 245), _smooth_edge(land_h, 0.55, 0.90))
            t_dry = 1.0 - _smooth_edge(moist, 0.22, 0.42)
            t_wet = _smooth_edge(moist, 0.55, 0.75)
            rgb = _lerp_rgb(grass, desert, t_dry)
            rgb = _lerp_rgb(rgb, forest, t_wet)
            rgb = _lerp_rgb(rgb, rock, _smooth_edge(land_h, 0.48, 0.68))
            # Polar sixths only — soft edge at ±2/3 latitude
            ice_lat = _smooth_edge(abs(lat_norm), 2.0 / 3.0, 2.0 / 3.0 + 0.06)
            ice = ice_lat * (0.55 + 0.45 * _smooth_edge(land_h, 0.15, 0.70))
            rgb = _lerp_rgb(rgb, snow, ice)
            t_beach = 1.0 - _smooth_edge(elev, SEA_LEVEL, SEA_LEVEL + 0.035)
            rgb = _lerp_rgb(rgb, (194, 178, 128), t_beach * (1.0 - ice) * 0.85)
            # Soften coastal foam so it doesn't read as white cloud bands
            # (foam only applied on water branch above)
            river_amt = self.is_river(wx, wy, elev, moist)
            rgb = _lerp_rgb(rgb, (35, 90, 140), river_amt)

        # Terrain micro-lighting
        ndot = _clamp(0.62 + 0.38 * (mountain * 0.5 + (d - 0.5) * -0.4), 0.35, 1.1)
        r = rgb[0] * ndot
        g = rgb[1] * ndot
        b = rgb[2] * ndot
        haze = 0.12 + 0.06 * (1.0 - elev)
        r = r * (1.0 - haze) + 40 * haze
        g = g * (1.0 - haze) + 70 * haze
        b = b * (1.0 - haze) + 120 * haze
        return (r, g, b), elev, river_amt, land

    def sample(self, wx, wy, day_factor=1.0):
        """
        Full surface sample including cities, roads, rails, bridges, night lights.
        day_factor 0 = night, 1 = full day (from light source).
        """
        day = _clamp(day_factor, 0.0, 1.0)
        (r, g, b), elev, river_amt, land = self.sample_biome(wx, wy)

        # Roads / rails / bridges
        if land or river_amt > 0.2:
            for rd in self._nearby_roads(wx, wy):
                dist = _dist_point_seg(wx, wy, rd["x0"], rd["y0"], rd["x1"], rd["y1"])
                half = rd["width"] * 0.5
                if dist > half * 1.8:
                    continue
                edge = 1.0 - _smooth_edge(dist, half * 0.35, half * 1.6)
                if edge <= 0.01:
                    continue
                if river_amt > 0.35 and rd["kind"] in ("highway", "road", "rail"):
                    col = BRIDGE_RGB
                elif rd["kind"] == "rail":
                    col = RAIL_RGB
                elif rd["kind"] == "highway":
                    col = HIGHWAY_RGB
                else:
                    col = ROAD_RGB
                r = _lerp(r, col[0], edge * 0.85)
                g = _lerp(g, col[1], edge * 0.85)
                b = _lerp(b, col[2], edge * 0.85)

        # Cities painted into the surface (stable world-grid blocks — no sparkle)
        light_r = light_g = light_b = 0.0
        light_w = 0.0
        for city in self._nearby_cities(wx, wy):
            dx = wx - city["x"]
            dy = wy - city["y"]
            dist = math.hypot(dx, dy)
            radius = 12_000.0 + city["size"] * 14_000.0
            if dist > radius * 1.5:
                continue
            dmg = _clamp(float(city.get("damage", 0.0)), 0.0, 1.0)
            dead = city.get("obliterated", False) or dmg >= 0.99
            disc = 1.0 - _smooth_edge(dist, radius * 0.35, radius)
            core = 1.0 - _smooth_edge(dist, radius * 0.08, radius * 0.42)
            if dead or dmg > 0.05:
                # Permanent scorched paint as damage rises
                rubble_w = disc * (0.45 + 0.55 * dmg)
                if rubble_w > 0.02:
                    ash = (
                        int(RUBBLE_RGB[0] * (0.7 + 0.3 * (1.0 - dmg))),
                        int(RUBBLE_RGB[1] * (0.65 + 0.2 * (1.0 - dmg))),
                        int(RUBBLE_RGB[2] * 0.7),
                    )
                    r = _lerp(r, ash[0], rubble_w * 0.92)
                    g = _lerp(g, ash[1], rubble_w * 0.92)
                    b = _lerp(b, ash[2], rubble_w * 0.92)
                # Fixed embers (hash only — never time-animated)
                if dmg > 0.35 and dist < radius * 0.65:
                    cell = 5000.0
                    gx = int(math.floor((wx - city["x"]) / cell))
                    gy = int(math.floor((wy - city["y"]) / cell))
                    h = _hash2(gx, gy, 91)
                    if h > 0.88:
                        r = _lerp(r, FIRE_RGB[0], 0.4 * dmg)
                        g = _lerp(g, FIRE_RGB[1], 0.4 * dmg)
                        b = _lerp(b, FIRE_RGB[2], 0.3 * dmg)
            if not dead:
                intact = 1.0 - dmg
                # Solid urban disc baked onto terrain
                if disc > 0.02 and intact > 0.05:
                    k = disc * 0.88 * intact
                    r = _lerp(r, CITY_DAY[0], k)
                    g = _lerp(g, CITY_DAY[1], k)
                    b = _lerp(b, CITY_DAY[2], k)
                if core > 0.02 and intact > 0.05:
                    k = core * 0.75 * intact
                    r = _lerp(r, CITY_DAY_CORE[0], k)
                    g = _lerp(g, CITY_DAY_CORE[1], k)
                    b = _lerp(b, CITY_DAY_CORE[2], k)
                # Coarse permanent block paint (stable world cells)
                if dist < radius * 0.92 and intact > 0.08:
                    cell = 5200.0
                    gx = int(math.floor((wx - city["x"]) / cell))
                    gy = int(math.floor((wy - city["y"]) / cell))
                    h = _hash2(gx, gy, 77 + city["size"] * 3)
                    if h > 0.38:
                        # Building block shade from hash — fixed forever
                        shade_b = 0.55 + 0.45 * h
                        br = int(100 + 55 * shade_b)
                        bg = int(98 + 50 * shade_b)
                        bb = int(95 + 48 * shade_b)
                        blk = (0.55 + 0.35 * h) * intact * max(disc, 0.25)
                        r = _lerp(r, br, blk)
                        g = _lerp(g, bg, blk)
                        b = _lerp(b, bb, blk)
                    elif h < 0.18 and disc > 0.2:
                        # Park / courtyard patches
                        r = _lerp(r, 55, 0.35 * intact * disc)
                        g = _lerp(g, 95, 0.35 * intact * disc)
                        b = _lerp(b, 50, 0.35 * intact * disc)
                # Night lights: warm street/building glow (pops on dark terrain)
                glow = 1.0 - _smooth_edge(dist, radius * 0.12, radius * 1.35)
                if glow > 0.01 and intact > 0.1:
                    intensity = glow * glow * (0.7 + 0.28 * city["size"]) * intact
                    light_r += CITY_NIGHT[0] * intensity
                    light_g += CITY_NIGHT[1] * intensity
                    light_b += CITY_NIGHT[2] * intensity
                    light_w += intensity
                    if dist < radius * 0.35 and city["size"] >= 3:
                        light_r += CITY_GLOW[0] * intensity * 0.65
                        light_g += CITY_GLOW[1] * intensity * 0.65
                        light_b += CITY_GLOW[2] * intensity * 0.55
                    # Sparse bright building windows
                    if dist < radius * 0.85:
                        cell = 4800.0
                        gx = int(math.floor((wx - city["x"]) / cell))
                        gy = int(math.floor((wy - city["y"]) / cell))
                        wh = _hash2(gx, gy, 55 + city["size"])
                        if wh > 0.72:
                            light_r += 255 * intensity * 0.35 * wh
                            light_g += 220 * intensity * 0.3 * wh
                            light_b += 120 * intensity * 0.15 * wh
                            light_w += intensity * 0.25

        # Wildfire — static scorched paint only (no animated flame)
        if land and self.fire_scorch and self._fire_key(wx, wy) in self.fire_scorch:
            r = _lerp(r, ASH_RGB[0], 0.88)
            g = _lerp(g, ASH_RGB[1], 0.88)
            b = _lerp(b, ASH_RGB[2], 0.85)
            # Sparse permanent ember flecks (hash — not time-based)
            gx = int(math.floor(wx / 2800.0))
            gy = int(math.floor(wy / 2800.0))
            if _hash2(gx, gy, 44) > 0.90:
                r = _lerp(r, ASH_EMBER[0], 0.55)
                g = _lerp(g, ASH_EMBER[1], 0.55)
                b = _lerp(b, ASH_EMBER[2], 0.4)

        # Day / night mix — respect light source (deep night away from sun)
        night_floor = 0.04  # dark atmosphere, not pure black
        shade = night_floor + (1.0 - night_floor) * (day ** 1.25)
        r *= shade
        g *= shade
        b *= shade
        # City lights dominate at night / dusk
        night = 1.0 - day
        if light_w > 0.01 and night > 0.04:
            k = _clamp(night * 1.35, 0.0, 1.0)
            r = r + light_r * k * 0.85
            g = g + light_g * k * 0.8
            b = b + light_b * k * 0.55

        return (
            int(_clamp(r, 0, 255)),
            int(_clamp(g, 0, 255)),
            int(_clamp(b, 0, 255)),
        )


# ---------------- Parallax space (Space Explorer techniques) ----------------
def _star_rgb(brightness, purple=False):
    """Blue-tinted star, dimmed 30% like Space Explorer."""
    brightness = max(1, int(brightness * STAR_DIM))
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


def _empty_layer(lw, lh):
    return [[(0, 0, 0) for _ in range(lw)] for _ in range(lh)]


def _add_far_stars(layer_map, lw, lh, chance=180):
    """Sparse far stars — Space Explorer far-field."""
    for y in range(lh):
        for x in range(lw):
            if random.randint(0, chance) != 1:
                continue
            bri = random.randint(25, 150)
            purple = random.random() < 0.08
            layer_map[y][x] = _star_rgb(bri, purple=purple)


def _add_bg_stars(layer_map, lw, lh, chance=95):
    for y in range(lh):
        for x in range(lw):
            if random.randint(0, chance) != 1:
                continue
            if layer_map[y][x] != (0, 0, 0):
                continue
            bri = random.randint(40, 180)
            layer_map[y][x] = _star_rgb(bri)


def _nebula_falloff(dx, dy, blobs):
    best = 0.0
    for ox, oy, radius, sh, sv in blobs:
        bx = (dx - ox) / sh
        by = (dy - oy) / sv
        d2 = bx * bx + by * by
        lim = radius * radius
        if d2 < lim:
            best = max(best, 1.0 - d2 / lim)
    return best


def _add_nebula_patches(layer_map, lw, lh, count=7):
    """Irregular nebula clouds from merged soft blobs (Space Explorer)."""
    palette = (
        (20, 0, 40),
        (0, 20, 50),
        (30, 10, 45),
        (10, 25, 35),
    )
    for _ in range(count):
        cx = random.randint(0, lw - 1)
        cy = random.randint(0, lh - 1)
        base = random.choice(palette)
        blobs = []
        for _ in range(random.randint(3, 6)):
            blobs.append((
                random.randint(-14, 14),
                random.randint(-10, 10),
                random.randint(12, 26),
                random.uniform(0.55, 1.45),
                random.uniform(0.55, 1.45),
            ))
        extent = 0
        for ox, oy, radius, sh, sv in blobs:
            extent = max(extent, int(abs(ox) + radius * sh), int(abs(oy) + radius * sv))
        extent += 2
        for dy in range(-extent, extent + 1):
            for dx in range(-extent, extent + 1):
                fall = _nebula_falloff(dx, dy, blobs)
                if fall <= 0:
                    continue
                x = (cx + dx) % lw
                y = (cy + dy) % lh
                if layer_map[y][x] == (0, 0, 0):
                    layer_map[y][x] = tuple(
                        max(0, min(255, int(c * fall))) for c in base
                    )


class SpaceParallax(object):
    """
    Four oversized wrap layers + smooth fractional scroll — Space Explorer /
    Skyfall style starfield (no other planets — our world is the only one).
    Scroll is primarily *down* the screen.
    """

    def __init__(self, panel_w, panel_h):
        self.pw = int(panel_w)
        self.ph = int(panel_h)
        self.lw = SPACE_LAYER_W
        self.lh = SPACE_LAYER_H
        print("[PlanetFly] Building space layers (parallax stars + nebulae)…")
        # Far: sparse blue stars only
        self.far = _empty_layer(self.lw, self.lh)
        _add_far_stars(self.far, self.lw, self.lh)
        # Background: soft nebulae + denser stars (no gas giants)
        self.bg = _empty_layer(self.lw, self.lh)
        _add_nebula_patches(self.bg, self.lw, self.lh, count=8)
        _add_bg_stars(self.bg, self.lw, self.lh)
        # Middleground: more stars
        self.mid = _empty_layer(self.lw, self.lh)
        _add_bg_stars(self.mid, self.lw, self.lh, chance=100)
        # Foreground: bright sparse stars (closest layer)
        self.fg = _empty_layer(self.lw, self.lh)
        _add_bg_stars(self.fg, self.lw, self.lh, chance=150)
        # Integer scroll offsets + fractional carry (SpaceExplorer smooth scroll)
        self.far_v = random.randint(0, self.lh - 1)
        self.bg_v = random.randint(0, self.lh - 1)
        self.mid_v = random.randint(0, self.lh - 1)
        self.fg_v = random.randint(0, self.lh - 1)
        self.far_h = random.randint(0, self.lw - 1)
        self.bg_h = random.randint(0, self.lw - 1)
        self.mid_h = random.randint(0, self.lw - 1)
        self.fg_h = random.randint(0, self.lw - 1)
        self.carry_far = 0.0
        self.carry_bg = 0.0
        self.carry_mid = 0.0
        self.carry_fg = 0.0
        self.carry_far_h = 0.0
        self.carry_bg_h = 0.0
        self.carry_mid_h = 0.0
        self.carry_fg_h = 0.0
        print("[PlanetFly] Space layers ready — scrolling down")

    def update(self, dt, streak=0.0):
        """
        Advance parallax. Positive vel scrolls content *down* the panel.
        streak > 0 speeds everything (planet approach dive).
        """
        boost = 1.0 + 3.8 * streak
        # World velocity in “layer px per second” at rate-unit 1
        vel_v = SPACE_SCROLL_V * boost
        vel_h = SPACE_SCROLL_V * 0.08 * boost  # slight side drift

        def _step(carry, offset, rate, vel, limit):
            # SpaceExplorer: carry += vel / rate; integer steps when carry crosses 1
            carry += (vel / rate) * dt
            di = int(carry)
            if di != 0:
                carry -= di
                offset = (offset + di) % limit
            return carry, offset

        # Downward: increasing v offset with sample (y + v) moves content up;
        # we use (y - v) in paint so increasing v moves content down.
        self.carry_far, self.far_v = _step(
            self.carry_far, self.far_v, SPACE_FAR_RATE, vel_v, self.lh,
        )
        self.carry_bg, self.bg_v = _step(
            self.carry_bg, self.bg_v, SPACE_BG_RATE, vel_v, self.lh,
        )
        self.carry_mid, self.mid_v = _step(
            self.carry_mid, self.mid_v, SPACE_MID_RATE, vel_v, self.lh,
        )
        self.carry_fg, self.fg_v = _step(
            self.carry_fg, self.fg_v, SPACE_FG_RATE, vel_v, self.lh,
        )
        self.carry_far_h, self.far_h = _step(
            self.carry_far_h, self.far_h, SPACE_FAR_RATE, vel_h * 0.4, self.lw,
        )
        self.carry_bg_h, self.bg_h = _step(
            self.carry_bg_h, self.bg_h, SPACE_BG_RATE, vel_h * 0.55, self.lw,
        )
        self.carry_mid_h, self.mid_h = _step(
            self.carry_mid_h, self.mid_h, SPACE_MID_RATE, vel_h * 0.7, self.lw,
        )
        self.carry_fg_h, self.fg_h = _step(
            self.carry_fg_h, self.fg_h, SPACE_FG_RATE, vel_h, self.lw,
        )

    def draw(self, canvas, fade=1.0):
        """Composite four layers front-to-back (SpaceExplorer paint_parallax)."""
        set_px = canvas.SetPixel
        fade = _clamp(fade, 0.0, 1.0)
        far, bg, mid, fg = self.far, self.bg, self.mid, self.fg
        lw, lh = self.lw, self.lh
        # Precompute row indices for smooth wrap (downward: y - scroll)
        far_rows = [((y - self.far_v) % lh) for y in range(self.ph)]
        bg_rows = [((y - self.bg_v) % lh) for y in range(self.ph)]
        mid_rows = [((y - self.mid_v) % lh) for y in range(self.ph)]
        fg_rows = [((y - self.fg_v) % lh) for y in range(self.ph)]

        for x in range(self.pw):
            far_x = (x + self.far_h) % lw
            bg_x = (x + self.bg_h) % lw
            mid_x = (x + self.mid_h) % lw
            fg_x = (x + self.fg_h) % lw
            for y in range(self.ph):
                rgb = fg[fg_rows[y]][fg_x]
                if rgb == (0, 0, 0):
                    rgb = mid[mid_rows[y]][mid_x]
                    if rgb == (0, 0, 0):
                        rgb = bg[bg_rows[y]][bg_x]
                        if rgb == (0, 0, 0):
                            rgb = far[far_rows[y]][far_x]
                if fade < 0.999:
                    set_px(
                        x, y,
                        int(rgb[0] * fade),
                        int(rgb[1] * fade),
                        int(rgb[2] * fade),
                    )
                else:
                    set_px(x, y, rgb[0], rgb[1], rgb[2])


class SpaceIntro(object):
    """
    starfield → bright planet dot → zoom into *the same surface map* → flyover.
    Phases: stars | dot | zoom | done
    """

    def __init__(self, width, height, planet=None):
        self.w = int(width)
        self.h = int(height)
        self.space = SpaceParallax(width, height)
        self.planet = planet if planet is not None else PlanetMap()
        self.phase = "stars"
        self.t = 0.0
        # Random approach site so day/night framing is not always the same
        self.showcase = self.planet.pick_approach_site()
        self.land_x = self.showcase["x"]
        self.land_y = self.showcase["y"]
        # Orientation: rotate so approach site faces the camera (+Z)
        self.land_lon = self.land_x / PLANET_R
        self.land_lat = _clamp(self.land_y / PLANET_R, -1.2, 1.2)
        # Planet appears off-center a bit (not dead middle)
        self.px = self.w * random.uniform(0.35, 0.65)
        self.py = self.h * random.uniform(0.30, 0.70)
        self.dot_bright = 0.0
        self.planet_r = 0.4
        self.zoom_u = 0.0
        self.hud_text = ""
        self.hud_rgb = HUD_RGB
        day0 = self.planet.day_factor_flat(self.land_x, self.land_y)
        print(
            f"[PlanetBlast] Space intro — approaching {self.planet.name}  "
            f"site day={day0:.2f}  @ ({self.px:.0f},{self.py:.0f})"
        )

    @property
    def done(self):
        return self.phase == "done"

    def update(self, dt):
        self.t += dt
        if self.phase == "stars":
            self.space.update(dt, streak=0.0)
            self.hud_text = ""
            if self.t >= STAR_DRIFT_SEC:
                self.phase = "dot"
                self.t = 0.0
                print(f"[PlanetBlast] {self.planet.name} sighted — bright dot")
        elif self.phase == "dot":
            self.space.update(dt, streak=0.0)
            self.dot_bright = _smoothstep(self.t / 0.55)
            # Identify the world as we close in
            self.hud_text = _hud_fit(
                str(self.planet.name).upper(), max(8, self.w - 2),
            )
            self.hud_rgb = HUD_NAME_RGB
            if self.t >= PLANET_DOT_SEC:
                self.phase = "zoom"
                self.t = 0.0
                print(f"[PlanetBlast] Approaching {self.planet.name}…")
        elif self.phase == "zoom":
            u = _smoothstep(self.t / PLANET_ZOOM_SEC)
            self.zoom_u = u
            self.space.update(dt, streak=u * u)
            self.dot_bright = 1.0
            max_r = math.hypot(self.w, self.h) * 0.72
            self.planet_r = _lerp(0.6, max_r, u * u * (0.4 + 0.6 * u))
            self.px = _lerp(self.px, self.w * 0.5, dt * 0.35)
            self.py = _lerp(self.py, self.h * 0.5, dt * 0.35)
            self.hud_text = _hud_fit(
                str(self.planet.name).upper(), max(8, self.w - 2),
            )
            self.hud_rgb = HUD_NAME_RGB
            if self.t >= PLANET_ZOOM_SEC:
                self.phase = "done"
                print(f"[PlanetBlast] Entering atmosphere — {self.planet.name}")

    def draw(self, canvas):
        set_px = canvas.SetPixel
        try:
            canvas.Fill(0, 0, 4)
        except Exception:
            for y in range(self.h):
                for x in range(self.w):
                    set_px(x, y, 0, 0, 4)

        star_fade = 1.0
        if self.phase == "zoom":
            u = _smoothstep(self.t / PLANET_ZOOM_SEC)
            star_fade = 1.0 - u * 0.92
        self.space.draw(canvas, fade=star_fade)

        if self.phase in ("dot", "zoom"):
            self._draw_planet(canvas)
        # HUD: planet name while approaching
        if self.hud_text:
            tw = _hud_text_width(self.hud_text)
            hx = 1
            if tw + 2 > self.w:
                hx = max(0, self.w - tw)
            hy = max(0, self.h - _HUD_CHAR_H - 1)
            _draw_hud_text(
                canvas, self.hud_text, hx, hy, self.hud_rgb, self.w, self.h,
            )

    def _view_to_planet_normal(self, nx, ny, nz):
        """
        Rotate view-space sphere normal so the landing site faces the camera.
        View: +Z toward camera. Landing should map near (0,0,1).
        """
        # Start from lon/lat of landing; build rotation that maps landing → +Z
        lon, lat = self.land_lon, self.land_lat
        # Inverse of: rotate by -lon around Y, then -lat around X
        # Apply R = Ry(lon) * Rx(lat) to view normal to get planet-frame normal
        # Rx(lat)
        cl, sl = math.cos(lat), math.sin(lat)
        x1, y1, z1 = nx, ny * cl - nz * sl, ny * sl + nz * cl
        # Ry(lon)
        co, so = math.cos(lon), math.sin(lon)
        x2 = x1 * co + z1 * so
        y2 = y1
        z2 = -x1 * so + z1 * co
        return x2, y2, z2

    def _draw_planet(self, canvas):
        """Grow disc using the shared PlanetMap (day/night + cities)."""
        set_px = canvas.SetPixel
        cx, cy = self.px, self.py
        radius = max(0.5, self.planet_r)
        glow_r = radius + 1.2 + min(3.0, radius * 0.08)
        x0 = max(0, int(cx - glow_r - 1))
        x1 = min(self.w - 1, int(cx + glow_r + 1))
        y0 = max(0, int(cy - glow_r - 1))
        y1 = min(self.h - 1, int(cy + glow_r + 1))
        b = _clamp(self.dot_bright, 0.0, 1.0)
        # As we zoom, blend from full-sphere UV toward a local window around landing
        # (keeps continuity into the flyover camera)
        local_blend = _smoothstep((radius - 4.0) / max(1.0, min(self.w, self.h) * 0.45))

        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                dx = x + 0.5 - cx
                dy = y + 0.5 - cy
                d = math.hypot(dx, dy)
                if d > glow_r:
                    continue
                if radius < 1.25:
                    if d < 0.75:
                        set_px(x, y, int(255 * b), int(240 * b), int(200 * b))
                    elif d < 1.6:
                        k = (1.0 - (d - 0.75) / 0.85) * 0.45 * b
                        set_px(x, y, int(180 * k), int(160 * k), int(120 * k))
                    continue

                if d <= radius:
                    nx = dx / radius
                    ny = dy / radius
                    nz2 = 1.0 - nx * nx - ny * ny
                    if nz2 < 0:
                        continue
                    nz = math.sqrt(nz2)
                    # Planet-frame normal (landing faces camera)
                    pnx, pny, pnz = self._view_to_planet_normal(nx, ny, nz)
                    wx_s, wy_s = self.planet.world_from_sphere(pnx, pny, pnz)
                    # Local zoom window around landing (same map, tighter FOV)
                    mpp = (PLANET_R * 1.8) / max(radius, 1.0)  # shrinks as disc grows
                    wx_l = self.land_x + dx * mpp
                    wy_l = self.land_y + dy * mpp
                    wx = _lerp(wx_s, wx_l, local_blend)
                    wy = _lerp(wy_s, wy_l, local_blend)

                    day = self.planet.day_factor_sphere(pnx, pny, pnz)
                    # When heavily zoomed local, use flat terminator too
                    day_f = self.planet.day_factor_flat(wx, wy)
                    day = _lerp(day, day_f, local_blend * 0.65)

                    tr, tg, tb = self.planet.sample(wx, wy, day_factor=day)
                    # Sphere limb shading (shape cue)
                    limb = 0.55 + 0.45 * nz
                    fade = 1.0 if radius > 3 else _clamp(radius / 3.0, 0.0, 1.0)
                    set_px(
                        x, y,
                        int(_clamp(tr * limb * fade, 0, 255)),
                        int(_clamp(tg * limb * fade, 0, 255)),
                        int(_clamp(tb * limb * fade, 0, 255)),
                    )
                elif d <= glow_r:
                    t = 1.0 - (d - radius) / max(0.2, glow_r - radius)
                    t = t * t * 0.55
                    set_px(x, y, int(80 * t), int(140 * t), int(220 * t))


# ---------------- Camera / flight ----------------
def _hud_text_width(text):
    """Pixel width of HUD string (3×5 glyphs + 1px gaps)."""
    n = len(text)
    if n <= 0:
        return 0
    return n * _HUD_CHAR_W + max(0, n - 1) * _HUD_GAP


def _hud_fit(text, max_px):
    """Truncate text so it fits max_px width in the micro font."""
    t = str(text or "")
    while t and _hud_text_width(t) > max_px:
        t = t[:-1]
    return t


def _city_display_name(city):
    nm = (city or {}).get("name") or ""
    if not nm:
        return "UNKNOWN"
    return str(nm).upper()


def _draw_hud_text(canvas, text, x, y, rgb, panel_w, panel_h):
    """
    Draw teeny 3×5 bitmap HUD text. Still readable on 64×32 LEDs.
    Only paints lit glyph pixels (transparent background).
    """
    if not text:
        return
    set_px = canvas.SetPixel
    r, g, b = rgb
    cx = int(x)
    cy = int(y)
    for ch in str(text).upper():
        rows = _HUD_GLYPHS.get(ch, _HUD_GLYPHS.get("?", (0b111, 0b001, 0b010, 0b000, 0b010)))
        for row_i, bits in enumerate(rows):
            py = cy + row_i
            if py < 0 or py >= panel_h:
                continue
            for col in range(_HUD_CHAR_W):
                if bits & (0b100 >> col):
                    px = cx + col
                    if 0 <= px < panel_w:
                        set_px(px, py, r, g, b)
        cx += _HUD_CHAR_W + _HUD_GAP


def _ground_span_m(alt_ft):
    """Visible ground height (m) at altitude for fixed FOV."""
    alt_m = max(1000.0, alt_ft * 0.3048)
    return 2.0 * alt_m * math.tan(math.radians(_FOV_DEG) * 0.5)


def _city_radius_m(city):
    """Match PlanetMap.sample urban footprint."""
    return 12_000.0 + city["size"] * 14_000.0


def _alt_for_city_pixels(city, panel_h, target_px=CITY_TARGET_PX):
    """
    Altitude (ft) so the city's diameter is about target_px on screen.
    Larger target_px → lower altitude (closer). Smaller px → higher (farther).
    """
    diameter = 2.0 * _city_radius_m(city)
    mpp = diameter / max(1.5, float(target_px))
    span = mpp * float(max(1, panel_h))
    alt_m = span / (2.0 * math.tan(math.radians(_FOV_DEG) * 0.5))
    return max(20_000.0, alt_m / 0.3048)


class PlanetCamera(object):
    """
    Top-down surface camera: zoom to a city (~20px), red crosshairs, bomb until
    obliterated, zoom out, next city. Travel scrolls the map down the panel.
    """

    def __init__(self, width, height, planet=None, start_xy=None, city=None):
        self.w = int(width)
        self.h = int(height)
        self.planet = planet if planet is not None else PlanetMap()
        self.seed = self.planet.seed
        self.visited = set()
        self.city = city if city is not None else self.planet.pick_showcase_city()
        self._mark_visited(self.city)
        self.x = float(self.city["x"])
        self.y = float(self.city["y"])
        self.heading = random.uniform(0, math.pi * 2)
        self.turn_rate = 0.0
        self.leg_t = 0.0
        self.leg_len = random.uniform(LEG_MIN, LEG_MAX)
        self.t = 0.0
        # Opening: cruise the surface 1 min (clock HUD) before first acquire
        self.phase = "cruise"
        self.phase_t = 0.0
        self.cruise_t = 0.0
        self.cruise_leg_t = 0.0
        self.cruise_leg_len = random.uniform(CRUISE_LEG_MIN, CRUISE_LEG_MAX)
        self.alt_wide = _alt_for_city_pixels(self.city, self.h, CITY_WIDE_PX)
        self.alt_close = _alt_for_city_pixels(self.city, self.h, CITY_TARGET_PX)
        self.alt_ft = float(self.alt_wide)
        self.alt_from = float(self.alt_wide)
        self.alt_to = float(self.alt_close)
        self.bombs = []       # falling ordnance
        self.blasts = []      # smoke rings + fire
        self.bomb_cd = 0.0
        self._nv = False      # night-vision mode (dark side)
        # Camera aim wander (keeps city near reticle, not perfect)
        self.aim_err_x = random.uniform(-0.4, 0.4) * CAM_AIM_ERR_M
        self.aim_err_y = random.uniform(-0.4, 0.4) * CAM_AIM_ERR_M
        self.hud_text = ""
        self.hud_rgb = HUD_RGB
        self.clock_text = "00:00"     # when set, always drawn upper-left
        self.cruise_stream = ""       # continuous marquee text
        self.cruise_scroll_x = float(self.w)  # pixel offset (smooth)
        self.cruise_ticker_queue = []
        self._prev = [[(0, 0, 0) for _ in range(self.w)] for _ in range(self.h)]
        # Batches: 5 night → 5 day → repeat until all destroyed
        self.batch_side = "night"
        self.batch_done = 0  # completed targets in current batch (current counts as #1)
        self.cities_bombed = 0
        self.since_patrol = 0  # destroyed since last patrol
        self.patrol_t = 0.0
        self.patrol_leg_t = 0.0
        self.patrol_leg_len = PATROL_LEG_MAX
        # Approach site for cruise; first strike city chosen after WARCOM order
        self.strike_city = None
        self.city = self._pick_patrol_city()
        # Keep sun as-is during approach/cruise so day-night mix stays varied
        self._cruise_refill_ticker(force=True)
        day0 = self.planet.day_factor_flat(self.x, self.y)
        print(
            f"[PlanetBlast] Surface cruise {CRUISE_SEC:.0f}s over "
            f"{getattr(self.planet, 'name', 'world')}  "
            f"(local day={day0:.2f}) — then acquire targets"
        )

    def _mark_visited(self, city):
        self.visited.add(id(city))

    def _intact_cities(self):
        return [c for c in self.planet.cities if not c.get("obliterated")]

    def _advance_batch_after_kill(self):
        """After a city is destroyed: count toward 5, then flip night/day."""
        self.batch_done += 1
        if self.batch_done >= TARGETS_PER_BATCH:
            self.batch_side = "day" if self.batch_side == "night" else "night"
            self.batch_done = 0
            print(
                f"[PlanetFly] === Switching to {self.batch_side.upper()} targets "
                f"({TARGETS_PER_BATCH} next) ==="
            )

    def _pick_next_city(self, count_kill=True):
        """
        Next bomb target from the current batch side (night or day).
        After 5 kills on a side, switch to the other side. Repeat until none left.
        count_kill: if True, register the city we just finished toward the batch.
        """
        alive = self._intact_cities()
        if not alive:
            # All destroyed — reset world and restart night batch
            for c in self.planet.cities:
                c["damage"] = 0.0
                c["obliterated"] = False
            self.visited.clear()
            self.batch_side = "night"
            self.batch_done = 0
            print("[PlanetFly] All targets destroyed — world reset, NIGHT batch")
            return self.planet.pick_city_for_side(
                "night", exclude=(), prefer_unvisited=self.visited,
            )

        if count_kill:
            self._advance_batch_after_kill()

        side = self.batch_side
        # If no intact cities remain on this side, flip early
        side_left = [
            c for c in alive
            if c is not self.city and (
                (side == "night" and self.planet.day_factor_flat(c["x"], c["y"]) <= NIGHT_DAY_MAX)
                or (side == "day" and self.planet.day_factor_flat(c["x"], c["y"]) >= DAY_DAY_MIN)
            )
        ]
        if not side_left and len(alive) > 1:
            other = "day" if side == "night" else "night"
            print(
                f"[PlanetFly] No more {side} cities — early switch to {other.upper()}"
            )
            self.batch_side = other
            self.batch_done = 0
            side = other

        nxt = self.planet.pick_city_for_side(
            side,
            exclude=(self.city,),
            prefer_unvisited=self.visited,
        )
        # Prefer some travel distance between targets
        if nxt is self.city or math.hypot(nxt["x"] - self.x, nxt["y"] - self.y) < 40_000:
            alt = self.planet.pick_city_for_side(
                side,
                exclude=(self.city, nxt),
                prefer_unvisited=self.visited,
            )
            if alt is not self.city:
                nxt = alt
        return nxt

    def _pick_patrol_city(self):
        """Waypoint city for sightseeing patrol — prefer ahead, not sharp turns."""
        pool = [c for c in self.planet.cities if c is not self.city]
        if not pool:
            pool = list(self.planet.cities)
        if not pool:
            return self.city
        cos_h = math.cos(self.heading)
        sin_h = math.sin(self.heading)
        scored = []
        for c in pool:
            dx = c["x"] - self.x
            dy = c["y"] - self.y
            d = math.hypot(dx, dy)
            if d < 80_000:
                continue
            # Prefer targets generally ahead of current heading
            if d > 1.0:
                ahead = (dx * cos_h + dy * sin_h) / d  # cos of turn angle
            else:
                ahead = 0.0
            if ahead < -0.15:
                continue  # skip hard reverse turns
            scored.append((
                c["size"] * 1.5 + ahead * 6.0 + min(d, 500_000) * 0.000008 + random.random(),
                c,
            ))
        if not scored:
            # Fallback: any distant city
            far = [c for c in pool if math.hypot(c["x"] - self.x, c["y"] - self.y) > 60_000]
            return random.choice(far or pool)
        scored.sort(key=lambda t: -t[0])
        return random.choice(scored[: max(2, min(6, len(scored)))])[1]

    def _begin_patrol(self):
        """Mid-mission cruise between cities — no bombing; full chatter HUD."""
        self.phase = "patrol"
        self.phase_t = 0.0
        self.patrol_t = 0.0
        self.patrol_leg_t = 0.0
        self.patrol_leg_len = random.uniform(PATROL_LEG_MIN, PATROL_LEG_MAX)
        self.bombs = []
        self.blasts = []
        self.bomb_cd = 999.0
        # Overview altitude for touring
        self.alt_wide = max(
            self.alt_wide,
            _alt_for_city_pixels(self.city, self.h, CITY_WIDE_PX),
        )
        self.alt_ft = float(self.alt_wide)
        self.city = self._pick_patrol_city()
        self.hud_text = ""
        self.hud_rgb = HUD_RGB
        lt = time.localtime()
        self.clock_text = f"{lt.tm_hour:02d}:{lt.tm_min:02d}"
        # Same stats + WARCOM chatter as opening cruise
        self.cruise_stream = ""
        self.cruise_scroll_x = float(self.w)
        self.cruise_ticker_queue = []
        self._cruise_refill_ticker(force=True)
        print(
            f"[PlanetBlast] === PATROL CRUISE {PATROL_SEC:.0f}s  "
            f"(after {self.cities_bombed} cities bombed) — chatter online ==="
        )

    def _end_patrol(self):
        """Resume strike package after patrol window."""
        print("[PlanetBlast] === PATROL complete — resuming targets ===")
        self.since_patrol = 0
        self.clock_text = ""
        self.cruise_stream = ""
        nxt = self._pick_next_city(count_kill=False)
        self._begin_zoom_in(nxt)

    def _update_patrol(self, dt):
        """Fly city to city at cruise altitude; clock + WARCOM ticker like opening."""
        self.patrol_t += dt
        self.patrol_leg_t += dt
        cx, cy = float(self.city["x"]), float(self.city["y"])
        # Hold a wide sightseeing altitude
        cruise = max(self.alt_wide * 0.9, _alt_for_city_pixels(self.city, self.h, CITY_WIDE_PX))
        self.alt_ft = _lerp(self.alt_ft, cruise, min(1.0, 0.6 * dt))
        dx = cx - self.x
        dy = cy - self.y
        dist = math.hypot(dx, dy)
        if dist > 500.0:
            desired = math.atan2(dy, dx)
            # Gentle bank toward waypoint — no hard spins
            err = (desired - self.heading + math.pi) % (math.pi * 2) - math.pi
            self.heading += _clamp(err, -0.22 * dt, 0.22 * dt)
        speed = self._mpp() * self.h * CRUISE_SPAN_PER_SEC * 0.55
        self.x += math.cos(self.heading) * speed * dt
        self.y += math.sin(self.heading) * speed * dt
        # Next waypoint when close or leg timer expires
        near = dist < max(35_000.0, _city_radius_m(self.city) * 1.0)
        if near or self.patrol_leg_t >= self.patrol_leg_len:
            self.city = self._pick_patrol_city()
            self.patrol_leg_t = 0.0
            self.patrol_leg_len = random.uniform(PATROL_LEG_MIN, PATROL_LEG_MAX)
        # Clock upper-left + scrolling stats/WARCOM (same as opening cruise)
        lt = time.localtime()
        self.clock_text = f"{lt.tm_hour:02d}:{lt.tm_min:02d}"
        self.hud_text = ""
        self.hud_rgb = HUD_RGB
        self._update_cruise_ticker(dt)
        if self.patrol_t >= PATROL_SEC:
            self.clock_text = ""
            self._end_patrol()

    def _mpp(self):
        return _ground_span_m(self.alt_ft) / float(max(1, self.h))

    def _world_to_screen(self, wx, wy):
        """Map world meters → screen pixel (float)."""
        mpp = self._mpp()
        cos_h = math.cos(self.heading)
        sin_h = math.sin(self.heading)
        dx = wx - self.x
        dy = wy - self.y
        # forward / right in cam frame
        fwd = dx * cos_h + dy * sin_h
        right = dx * (-sin_h) + dy * cos_h
        sx = self.w * 0.5 + right / mpp
        sy = self.h * 0.5 - fwd / mpp
        return sx, sy

    def _crosshair_screen(self):
        """Dead-center reticle, CROSSHAIR_UP_PX above vertical middle."""
        return self.w * 0.5, self.h * 0.5 - float(CROSSHAIR_UP_PX)

    def _screen_to_world(self, sx, sy):
        """Inverse of _world_to_screen: pixel → world meters under camera."""
        mpp = self._mpp()
        cos_h = math.cos(self.heading)
        sin_h = math.sin(self.heading)
        right = (sx - self.w * 0.5) * mpp
        fwd = (self.h * 0.5 - sy) * mpp
        dx = cos_h * fwd - sin_h * right
        dy = sin_h * fwd + cos_h * right
        return self.x + dx, self.y + dy

    def _aim_point_world(self):
        """World point the crosshair is pointing at right now."""
        return self._screen_to_world(*self._crosshair_screen())

    def _begin_zoom_in(self, city):
        """Acquire next target; do not revive already-obliterated cities."""
        self.city = city
        self.strike_city = city
        self.city["damage"] = float(self.city.get("damage", 0.0))
        self.city["obliterated"] = bool(self.city.get("obliterated", False))
        self._mark_visited(city)
        self.phase = "zoom_in"
        self.phase_t = 0.0
        self.alt_wide = _alt_for_city_pixels(city, self.h, CITY_WIDE_PX)
        self.alt_close = _alt_for_city_pixels(city, self.h, CITY_TARGET_PX)
        self.alt_from = max(float(self.alt_ft), self.alt_wide)
        self.alt_to = float(self.alt_close)
        self.alt_ft = self.alt_from
        self.bombs = []
        self.blasts = []
        self.bomb_cd = 0.4
        self.aim_err_x = random.uniform(-0.5, 0.5) * CAM_AIM_ERR_M
        self.aim_err_y = random.uniform(-0.5, 0.5) * CAM_AIM_ERR_M
        self.hud_text = "SCAN"
        self.hud_rgb = HUD_RGB
        self.clock_text = ""  # no clock during strike acquire/bomb
        day0 = self.planet.day_factor_flat(city["x"], city["y"])
        n = self.batch_done + 1  # current is next slot in batch
        cname = _city_display_name(city)
        print(
            f"[PlanetBlast] {self.batch_side.upper()} batch {n}/{TARGETS_PER_BATCH}  "
            f"city={cname} size={city['size']}  day={day0:.2f}  "
            f"→ ~{CITY_TARGET_PX:.0f}px @ {self.alt_close:.0f} ft"
        )

    def _end_opening_cruise(self):
        """After cruise: flash urgent WARCOM attack order, then acquire."""
        world = str(getattr(self.planet, "name", "UNKNOWN")).upper()
        tmpl = random.choice(_WARCOM_ATTACK_ORDERS)
        order = tmpl.format(world=world)
        self.phase = "warcom_order"
        self.phase_t = 0.0
        self.warcom_order = order
        # Start just off the right edge; scroll until fully past the left
        self.warcom_order_scroll = float(self.w)
        self.warcom_order_w = float(_hud_text_width(order))
        self.warcom_order_done = False
        self.warcom_order_done_t = 0.0
        self.hud_text = "ALERT"
        self.hud_rgb = HUD_ALERT_RGB
        # Time needed for full marquee: alert beat + travel distance / speed
        scroll_speed = CRUISE_TICKER_PPS * 1.15
        travel_px = self.warcom_order_scroll + self.warcom_order_w + 4.0
        scroll_sec = travel_px / max(1.0, scroll_speed)
        self.warcom_order_need = (
            CRUISE_ORDER_ALERT_SEC + scroll_sec + CRUISE_ORDER_END_HOLD
        )
        print(
            f"[PlanetBlast] {order}  "
            f"(scroll ~{scroll_sec:.1f}s, total ~{self.warcom_order_need:.1f}s)"
        )

    def _begin_first_strike(self):
        """After WARCOM order — begin first night-batch target acquire."""
        print(
            f"[PlanetBlast] Order acknowledged — acquiring first target on "
            f"{getattr(self.planet, 'name', 'world')}"
        )
        # Night batch starts here; may reorient sun only for strike targeting
        self.batch_side = "night"
        self.batch_done = 0
        target = self.planet.pick_city_for_side(
            "night",
            exclude=(),
            prefer_unvisited=self.visited,
        )
        self.strike_city = target
        self._begin_zoom_in(target)

    def _update_warcom_order(self, dt):
        """Hold cruise flight until the full WARCOM order has scrolled off."""
        self.phase_t += dt
        # Keep gentle forward motion
        speed = self._mpp() * self.h * CRUISE_SPAN_PER_SEC * 0.35
        self.x += math.cos(self.heading) * speed * dt
        self.y += math.sin(self.heading) * speed * dt
        self.heading += 0.015 * dt
        # Clock off — solid red ALERT in its place (upper left)
        self.clock_text = ""
        self.hud_text = "ALERT"
        self.hud_rgb = HUD_ALERT_RGB
        # Scroll only after ALERT is readable; do not loop — wait for full pass
        if self.phase_t >= CRUISE_ORDER_ALERT_SEC:
            if not self.warcom_order_done:
                self.warcom_order_scroll -= CRUISE_TICKER_PPS * 1.15 * dt
                # Fully past left edge when right edge of text is < 0
                if self.warcom_order_scroll + self.warcom_order_w < -2:
                    self.warcom_order_done = True
                    self.warcom_order_done_t = 0.0
            else:
                self.warcom_order_done_t += dt
                if self.warcom_order_done_t >= CRUISE_ORDER_END_HOLD:
                    self._begin_first_strike()
        # Safety: never hang forever if timing math is off
        if self.phase_t >= getattr(self, "warcom_order_need", 30.0) + 2.0:
            self._begin_first_strike()

    def _cruise_population(self):
        """Synthetic world population from city sizes (not obliterated weight more)."""
        total = 0
        for c in self.planet.cities:
            base = (8_000, 45_000, 180_000, 650_000, 2_400_000, 9_500_000)
            sz = int(_clamp(c.get("size", 1), 1, 5))
            pop = base[sz]
            if c.get("obliterated"):
                pop = int(pop * 0.08)
            else:
                dmg = float(c.get("damage", 0.0))
                pop = int(pop * (1.0 - 0.75 * dmg))
            total += pop
        return total

    def _cruise_stat_messages(self):
        """Live stats lines for the cruise ticker."""
        cities = self.planet.cities
        n = max(1, len(cities))
        destroyed = sum(1 for c in cities if c.get("obliterated"))
        left = n - destroyed
        damaged = sum(
            1 for c in cities
            if not c.get("obliterated") and float(c.get("damage", 0.0)) > 0.05
        )
        fires = len(getattr(self.planet, "fire_scorch", ()) or ())
        pop = self._cruise_population()
        world = str(getattr(self.planet, "name", "UNKNOWN")).upper()
        alt = int(self.alt_ft)
        if self.phase == "patrol":
            mode_line = f"PATROL {max(0, int(PATROL_SEC - self.patrol_t))}S"
        else:
            mode_line = f"CRUISE {max(0, int(CRUISE_SEC - self.cruise_t))}S"
        msgs = [
            f"WORLD {world}",
            f"POP {pop // 1000}K",
            f"CITIES {left}/{n} LIVE",
            f"DESTROYED {destroyed}",
            f"DAMAGED {damaged}",
            f"FIRES {fires}",
            f"ALT {alt} FT",
            f"BOMBED {self.cities_bombed}",
            mode_line,
        ]
        return msgs

    def _cruise_refill_ticker(self, force=False):
        """Queue a mix of stats + WARCOM chatter for the bottom scroll."""
        if self.cruise_ticker_queue and not force:
            return
        stats = self._cruise_stat_messages()
        chatter = list(_WARCOM_LINES)
        random.shuffle(chatter)
        queue = []
        ci = 0
        for i, st in enumerate(stats):
            queue.append(st)
            for _ in range(2):
                if ci < len(chatter):
                    queue.append(chatter[ci])
                    ci += 1
            if i % 2 == 1 and ci < len(chatter):
                queue.append(chatter[ci])
                ci += 1
        while ci < len(chatter):
            queue.append(chatter[ci])
            ci += 1
        random.shuffle(queue)
        head = stats[:3]
        random.shuffle(head)
        self.cruise_ticker_queue = head + queue

    def _cruise_append_stream(self, min_px=None):
        """Keep marquee string long enough for continuous pixel scroll."""
        if min_px is None:
            min_px = self.w * 4
        sep = "    "
        if not self.cruise_ticker_queue:
            self._cruise_refill_ticker(force=True)
        # Append until stream spans enough pixels beyond the scroll window
        guard = 0
        while _hud_text_width(self.cruise_stream) < min_px and guard < 40:
            if not self.cruise_ticker_queue:
                self._cruise_refill_ticker(force=True)
            msg = str(self.cruise_ticker_queue.pop(0)).upper()
            if self.cruise_stream:
                self.cruise_stream += sep + msg
            else:
                self.cruise_stream = msg
            guard += 1

    def _update_cruise_ticker(self, dt):
        """
        Smooth pixel marquee: scroll left by fractional pixels each frame,
        trim fully off-screen characters to keep the string short.
        """
        char_step = float(_HUD_CHAR_W + _HUD_GAP)
        if not self.cruise_stream:
            self.cruise_scroll_x = float(self.w)
            self._cruise_append_stream()
        else:
            # Top up stream before it runs out
            stream_w = _hud_text_width(self.cruise_stream)
            if self.cruise_scroll_x + stream_w < self.w * 2:
                self._cruise_append_stream(min_px=self.w * 4)

        # Smooth continuous motion (sub-pixel accumulated)
        self.cruise_scroll_x -= CRUISE_TICKER_PPS * dt

        # Drop characters that have fully scrolled off the left edge
        while self.cruise_stream and self.cruise_scroll_x <= -char_step:
            self.cruise_stream = self.cruise_stream[1:]
            self.cruise_scroll_x += char_step
            if not self.cruise_stream:
                self._cruise_append_stream()
                break

    def _cruise_ticker_draw_x(self):
        """Integer pixel x for drawing (rounded from smooth scroll)."""
        return int(round(self.cruise_scroll_x))

    def _update_cruise(self, dt):
        """
        Opening surface cruise: fly city-to-city, no weapons.
        Clock top-left; scrolling stats + WARCOM chatter bottom.
        """
        self.cruise_t += dt
        self.cruise_leg_t += dt
        cx, cy = float(self.city["x"]), float(self.city["y"])
        cruise = max(
            self.alt_wide * 0.95,
            _alt_for_city_pixels(self.city, self.h, CITY_WIDE_PX),
        )
        self.alt_ft = _lerp(self.alt_ft, cruise, min(1.0, 0.6 * dt))
        dx = cx - self.x
        dy = cy - self.y
        dist = math.hypot(dx, dy)
        if dist > 500.0:
            desired = math.atan2(dy, dx)
            err = (desired - self.heading + math.pi) % (math.pi * 2) - math.pi
            self.heading += _clamp(err, -0.22 * dt, 0.22 * dt)
        speed = self._mpp() * self.h * CRUISE_SPAN_PER_SEC * 0.5
        self.x += math.cos(self.heading) * speed * dt
        self.y += math.sin(self.heading) * speed * dt
        near = dist < max(35_000.0, _city_radius_m(self.city) * 1.0)
        if near or self.cruise_leg_t >= self.cruise_leg_len:
            self.city = self._pick_patrol_city()
            self.cruise_leg_t = 0.0
            self.cruise_leg_len = random.uniform(CRUISE_LEG_MIN, CRUISE_LEG_MAX)
        # Clock upper-left + scrolling intel ticker bottom
        lt = time.localtime()
        self.clock_text = f"{lt.tm_hour:02d}:{lt.tm_min:02d}"
        self.hud_text = ""
        self.hud_rgb = HUD_RGB
        self._update_cruise_ticker(dt)
        if self.cruise_t >= CRUISE_SEC:
            self.clock_text = ""
            self._end_opening_cruise()

    def _drop_bomb(self):
        """Spawn large bomb; falls near the crosshair with wide landing variance."""
        # Primary aim = reticle world point (camera track already imperfect)
        ax, ay = self._aim_point_world()
        cr = _city_radius_m(self.city)
        # Wide scatter: most inside/near city, some far longshots
        if random.random() < BOMB_AIM_LONGSHOT:
            # Long miss — past the city rim into the countryside
            spread = cr * random.uniform(0.9, 1.85)
        else:
            # Normal miss distribution biased toward outskirts, not dead-center
            # (sqrt-uniform: more hits mid-ring than pin-point)
            u = math.sqrt(random.random())
            spread = cr * BOMB_AIM_SPREAD * (0.15 + 0.85 * u)
        ang = random.uniform(0, math.pi * 2)
        # Slight elliptical stretch so pattern isn't a perfect circle
        stretch = random.uniform(0.65, 1.35)
        tx = ax + math.cos(ang) * spread * stretch
        ty = ay + math.sin(ang) * spread / stretch
        # Release from various screen points (top / sides / upper half)
        edge = random.random()
        if edge < 0.45:
            spawn_sx = random.uniform(1.0, self.w - 2.0)
            spawn_sy = random.uniform(-3.0, 2.0)          # above top
        elif edge < 0.70:
            spawn_sx = random.uniform(-2.0, 2.0)         # left
            spawn_sy = random.uniform(0.0, self.h * 0.55)
        elif edge < 0.95:
            spawn_sx = random.uniform(self.w - 3.0, self.w + 1.0)  # right
            spawn_sy = random.uniform(0.0, self.h * 0.55)
        else:
            spawn_sx = random.uniform(2.0, self.w - 3.0)
            spawn_sy = random.uniform(1.0, self.h * 0.35)  # upper field
        self.bombs.append({
            "x": tx,
            "y": ty,
            "spawn_sx": spawn_sx,
            "spawn_sy": spawn_sy,
            "z": 1.0,           # 1 = high, 0 = impact
            "size0": 7.5,       # large on release
            "t": 0.0,
        })

    def _detonate(self, wx, wy):
        """Impact: smoke ring + fire core; apply city damage; seed wildfire."""
        cr = _city_radius_m(self.city)
        dist = math.hypot(wx - self.city["x"], wy - self.city["y"])
        fall = 1.0 - _smooth_edge(dist, cr * 0.12, cr * 1.05)
        dmg = BOMB_DAMAGE * (0.75 + 0.12 * self.city["size"]) * (0.5 + 0.5 * fall)
        self.city["damage"] = _clamp(
            float(self.city.get("damage", 0.0)) + dmg, 0.0, 1.0,
        )
        tone = random.random()
        if tone < 0.55:
            s = random.uniform(210, 255)
        else:
            s = random.uniform(165, 210)
        smoke = (int(s), int(s * 0.99), int(s * 0.97))
        self.blasts.append({
            "x": wx, "y": wy,
            "t": 0.0,
            "max_r_m": cr * (0.28 + 0.4 * fall),
            "smoke": smoke,
        })
        # Throw fire into surrounding green (forests / grass)
        self.planet.seed_impact_wildfire(wx, wy, strength=0.55 + 0.45 * fall)
        self.planet.seed_city_wildfire(self.city)
        if self.city["damage"] >= 0.98 and not self.city.get("obliterated"):
            self.city["obliterated"] = True
            self.city["damage"] = 1.0
            self.planet.seed_city_wildfire(self.city)
            print(
                f"[PlanetFly] City size={self.city['size']} OBLITERATED"
            )

    def _update_fx(self, dt):
        # Falling bombs
        alive = []
        for b in self.bombs:
            b["t"] += dt
            u = _clamp(b["t"] / BOMB_FALL_SEC, 0.0, 1.0)
            # Ease down: hang then accelerate
            b["z"] = 1.0 - u * u
            if u >= 1.0:
                self._detonate(b["x"], b["y"])
            else:
                alive.append(b)
        self.bombs = alive
        # Smoke rings + fire
        alive_b = []
        for bl in self.blasts:
            bl["t"] += dt
            if bl["t"] < max(SMOKE_RING_SEC, FIRE_SEC):
                alive_b.append(bl)
        self.blasts = alive_b

    def update(self, dt):
        self.t += dt
        self.phase_t += dt
        cx, cy = self.city["x"], self.city["y"]

        # Always advance bombs / blasts
        self._update_fx(dt)
        # Forests slowly burn outward from cities on fire
        self.planet.update_wildfire(dt)

        if self.phase == "cruise":
            self._update_cruise(dt)

        elif self.phase == "warcom_order":
            self._update_warcom_order(dt)

        elif self.phase == "zoom_in":
            u = _smoothstep(self.phase_t / ZOOM_IN_SEC)
            self.alt_ft = _lerp(self.alt_from, self.alt_to, u)
            # Put city under reticle (fwd offset for CROSSHAIR_UP_PX)
            mpp = self._mpp()
            cos_h = math.cos(self.heading)
            sin_h = math.sin(self.heading)
            fwd = float(CROSSHAIR_UP_PX) * mpp
            # Ideal cam so city sits under crosshair, plus imperfect aim error
            ideal_x = cx - cos_h * fwd + self.aim_err_x
            ideal_y = cy - sin_h * fwd + self.aim_err_y
            self.x = _lerp(self.x, ideal_x, min(1.0, 2.4 * dt))
            self.y = _lerp(self.y, ideal_y, min(1.0, 2.4 * dt))
            self.heading += 0.02 * dt
            # Drift aim error slowly
            self.aim_err_x += random.uniform(-1, 1) * CAM_AIM_ERR_M * CAM_AIM_WANDER * dt
            self.aim_err_y += random.uniform(-1, 1) * CAM_AIM_ERR_M * CAM_AIM_WANDER * dt
            self.aim_err_x = _clamp(self.aim_err_x, -CAM_AIM_ERR_M, CAM_AIM_ERR_M)
            self.aim_err_y = _clamp(self.aim_err_y, -CAM_AIM_ERR_M, CAM_AIM_ERR_M)
            # Acquire: SCAN → city name → then lock
            if self.phase_t < ZOOM_IN_SEC * 0.28:
                self.hud_text, self.hud_rgb = "SCAN", HUD_RGB
            else:
                # Target acquired — show alien city name before bombs
                name = _hud_fit(
                    _city_display_name(self.city),
                    max(8, self.w - 2),
                )
                self.hud_text, self.hud_rgb = name, HUD_NAME_RGB
            if self.phase_t >= ZOOM_IN_SEC:
                self.alt_ft = self.alt_to
                self.phase = "bomb"
                self.phase_t = 0.0
                self.bomb_cd = 0.35
                self.hud_text, self.hud_rgb = "LOCKED", HUD_RGB
                print(
                    f"[PlanetFly] Weapons free — {_city_display_name(self.city)}  "
                    f"size={self.city['size']}  crosshairs on target"
                )

        elif self.phase == "bomb":
            # Keep flying — track city under reticle (imperfect), never stop
            self.alt_ft = self.alt_close
            mpp = self._mpp()
            cos_h = math.cos(self.heading)
            sin_h = math.sin(self.heading)
            # Light drift only — stay mostly level while on target
            self.heading += 0.04 * dt
            cos_h = math.cos(self.heading)
            sin_h = math.sin(self.heading)
            speed = mpp * self.h * CRUISE_SPAN_PER_SEC * 0.22
            self.x += cos_h * speed * dt
            self.y += sin_h * speed * dt
            # Wander aim error so lock is not 100% accurate
            self.aim_err_x += random.uniform(-1, 1) * CAM_AIM_ERR_M * CAM_AIM_WANDER * dt
            self.aim_err_y += random.uniform(-1, 1) * CAM_AIM_ERR_M * CAM_AIM_WANDER * dt
            self.aim_err_x = _clamp(self.aim_err_x, -CAM_AIM_ERR_M, CAM_AIM_ERR_M)
            self.aim_err_y = _clamp(self.aim_err_y, -CAM_AIM_ERR_M, CAM_AIM_ERR_M)
            # Ideal cam: city under crosshair + error
            fwd = float(CROSSHAIR_UP_PX) * mpp
            ideal_x = cx - cos_h * fwd + self.aim_err_x
            ideal_y = cy - sin_h * fwd + self.aim_err_y
            pull = min(1.0, 0.7 * dt)
            self.x = _lerp(self.x, ideal_x, pull)
            self.y = _lerp(self.y, ideal_y, pull)
            # Drop bombs at crosshair aim point until obliterated
            self.bomb_cd -= dt
            if self.bomb_cd <= 0.0 and not self.city.get("obliterated"):
                self._drop_bomb()
                self.bomb_cd = BOMB_DROP_INTERVAL * random.uniform(0.75, 1.2)
            if self.city.get("obliterated"):
                self.hud_text, self.hud_rgb = "DESTROYED", HUD_ALERT_RGB
            elif self.phase_t < 0.7:
                self.hud_text, self.hud_rgb = "LOCKED", HUD_RGB
            else:
                self.hud_text, self.hud_rgb = "FIRING", HUD_FIRE_RGB
            # Wait for lingering smoke before leaving the crater
            if self.city.get("obliterated") and not self.bombs and not self.blasts:
                self.phase = "zoom_out"
                self.phase_t = 0.0
                self.alt_from = float(self.alt_ft)
                self.alt_to = float(self.alt_wide)
                self.cities_bombed += 1
                self.since_patrol += 1
                self.hud_text, self.hud_rgb = "NEXT TGT", HUD_RGB
                print(
                    f"[PlanetFly] Target destroyed — total bombed={self.cities_bombed}  "
                    f"since patrol={self.since_patrol}/{PATROL_EVERY}"
                )

        elif self.phase == "zoom_out":
            u = _smoothstep(self.phase_t / ZOOM_OUT_SEC)
            self.alt_ft = _lerp(self.alt_from, self.alt_to, u)
            speed = self._mpp() * self.h * CRUISE_SPAN_PER_SEC * 0.4
            self.heading += 0.02 * dt
            self.x += math.cos(self.heading) * speed * dt
            self.y += math.sin(self.heading) * speed * dt
            self.hud_text, self.hud_rgb = "NEXT TGT", HUD_RGB
            if self.phase_t >= ZOOM_OUT_SEC:
                self.alt_ft = float(self.alt_wide)
                # After every N cities: peaceful patrol instead of next strike
                if self.since_patrol >= PATROL_EVERY:
                    self.since_patrol = 0
                    self._advance_batch_after_kill()
                    self._begin_patrol()
                else:
                    nxt = self._pick_next_city(count_kill=True)
                    self._begin_zoom_in(nxt)

        elif self.phase == "patrol":
            self._update_patrol(dt)

    def _night_vision_on(self):
        """NV when the camera is on the dark side of the terminator."""
        day = self.planet.day_factor_flat(self.x, self.y)
        return day < NV_DAY_THRESH

    @staticmethod
    def _to_night_vision(r, g, b):
        """Map a pixel to green mono NV with enough contrast to read terrain."""
        lum = 0.299 * r + 0.587 * g + 0.114 * b
        # Expand midtones so land/ocean/city structure separates
        t = _clamp(lum / 255.0, 0.0, 1.0)
        t = t * t * (3.0 - 2.0 * t)  # smoothstep contrast
        v = _clamp(t * 255.0 * NV_GAIN + NV_FLOOR, 0.0, 255.0)
        # Classic phosphor green
        return (
            int(v * 0.12),
            int(min(255, v * 0.98)),
            int(v * 0.18),
        )

    @staticmethod
    def _nv_hot_to_black(brightness):
        """
        NV bloom: bright sources (explosions) bloom to black.
        brightness 0 = dim (mid green), 1 = white-hot → black.
        """
        b = _clamp(brightness, 0.0, 1.0)
        # Hot core black; cooler edge dark green so shape still reads
        v = int((1.0 - b) * (1.0 - b) * 95 + 4)
        return (int(v * 0.08), v, int(v * 0.12))

    def render(self, canvas):
        """Top-down map + crosshairs, bombs, smoke rings, fire."""
        mpp = self._mpp()
        cos_h = math.cos(self.heading)
        sin_h = math.sin(self.heading)
        rx, ry = -sin_h, cos_h
        half_w = self.w * 0.5
        half_h = self.h * 0.5
        set_px = canvas.SetPixel
        taa = 0.08 if self.phase in ("zoom_in", "bomb") else 0.22
        planet = self.planet
        nv = self._night_vision_on()
        self._nv = nv  # for FX drawers
        alt_haze = _clamp((self.alt_ft - 200_000) / 1_800_000.0, 0.0, 0.20)
        if self.phase in ("patrol", "cruise", "warcom_order"):
            alt_haze = max(alt_haze, 0.04)

        for py in range(self.h):
            for px in range(self.w):
                sx = (px + 0.5 - half_w) * mpp
                sf = (half_h - (py + 0.5)) * mpp
                wx = self.x + cos_h * sf + rx * sx
                wy = self.y + sin_h * sf + ry * sx
                day = planet.day_factor_flat(wx, wy)
                if nv:
                    # Amp surface lighting so oceans, land, cities keep shape
                    # (true night would crush everything to black before NV)
                    day_s = max(day, NV_SURF_DAY)
                    r, g, b = planet.sample(wx, wy, day_factor=day_s)
                    r, g, b = self._to_night_vision(r, g, b)
                    # Scorched / burned land blooms bright under NV (−25%)
                    if planet.fire_scorch and planet.is_scorched(wx, wy):
                        h = _hash2(
                            int(math.floor(wx / 2800.0)),
                            int(math.floor(wy / 2800.0)),
                            71,
                        )
                        g_hot = int((230 + 25 * h) * 0.75)
                        r, g, b = (
                            int((50 + 40 * h) * 0.75),
                            g_hot,
                            int((70 + 30 * h) * 0.75),
                        )
                else:
                    r, g, b = planet.sample(wx, wy, day_factor=day)
                    if alt_haze > 0.01 and self.phase == "zoom_out":
                        r = int(r * (1.0 - alt_haze) + 50 * alt_haze)
                        g = int(g * (1.0 - alt_haze) + 75 * alt_haze)
                        b = int(b * (1.0 - alt_haze) + 120 * alt_haze)
                pr, pg, pb = self._prev[py][px]
                r = int(r * (1.0 - taa) + pr * taa)
                g = int(g * (1.0 - taa) + pg * taa)
                b = int(b * (1.0 - taa) + pb * taa)
                self._prev[py][px] = (r, g, b)
                set_px(px, py, r, g, b)

        # FX overlays (no TAA — stay sharp). No weapons UI on cruise/patrol/order.
        if self.phase not in ("patrol", "cruise", "warcom_order"):
            self._draw_blasts(canvas)
            self._draw_bombs(canvas)
            if self.phase in ("zoom_in", "bomb") and not self.city.get("obliterated"):
                if self.phase == "bomb" or self.phase_t > ZOOM_IN_SEC * 0.55:
                    self._draw_crosshairs(canvas)
        self._draw_hud(canvas)

    def _draw_hud(self, canvas):
        """
        Teeny 3×5 HUD.
        clock_text (HH:MM) always upper-left when set; other HUD as appropriate.
        """
        nv = getattr(self, "_nv", False)
        rgb = HUD_RGB if nv else self.hud_rgb

        # Time always upper-left whenever shown
        clock = getattr(self, "clock_text", "") or ""
        if clock:
            crgb = HUD_RGB if nv else HUD_RGB
            _draw_hud_text(canvas, clock, 1, 1, crgb, self.w, self.h)

        if self.phase in ("cruise", "patrol"):
            # Bottom marquee: stats + WARCOM / intel chatter
            stream = self.cruise_stream or ""
            if stream:
                hy = max(0, self.h - _HUD_CHAR_H - 1)
                trgb = HUD_RGB if nv else HUD_FIRE_RGB
                _draw_hud_text(
                    canvas, stream,
                    self._cruise_ticker_draw_x(), hy,
                    trgb, self.w, self.h,
                )
            return

        if self.phase == "warcom_order":
            # No clock — red ALERT top-left; order scrolls bottom
            ar = HUD_RGB if nv else HUD_ALERT_RGB
            _draw_hud_text(canvas, "ALERT", 1, 1, ar, self.w, self.h)
            order = getattr(self, "warcom_order", "") or ""
            if (
                order
                and self.phase_t >= CRUISE_ORDER_ALERT_SEC
                and not getattr(self, "warcom_order_done", False)
            ):
                hy = max(0, self.h - _HUD_CHAR_H - 1)
                orr = HUD_RGB if nv else HUD_ALERT_RGB
                _draw_hud_text(
                    canvas, order,
                    int(round(self.warcom_order_scroll)), hy,
                    orr, self.w, self.h,
                )
            return

        text = self.hud_text or ""
        if not text:
            return
        tw = _hud_text_width(text)
        hx = 1
        if tw + 2 > self.w:
            hx = max(0, self.w - tw)
        hy = max(0, self.h - _HUD_CHAR_H - 1)
        _draw_hud_text(canvas, text, hx, hy, rgb, self.w, self.h)

    def _draw_crosshairs(self, canvas):
        """
        Minimal 1px crosshairs — dead center, CROSSHAIR_UP_PX up.
        Green pulse while targeting; solid red when locked (bomb phase).
        """
        sx, sy = self._crosshair_screen()
        cx, cy = int(round(sx)), int(round(sy))
        set_px = canvas.SetPixel
        if self.phase == "bomb":
            rr, rg, rb = CROSSHAIR_LOCK_RGB
        else:
            # Smooth pulse green → dark green while acquiring
            u = 0.5 + 0.5 * math.sin(self.t * 4.5)
            rr = int(_lerp(CROSSHAIR_ACQ_LO[0], CROSSHAIR_ACQ_HI[0], u))
            rg = int(_lerp(CROSSHAIR_ACQ_LO[1], CROSSHAIR_ACQ_HI[1], u))
            rb = int(_lerp(CROSSHAIR_ACQ_LO[2], CROSSHAIR_ACQ_HI[2], u))
        arm = max(4, min(self.w, self.h) // 5)
        # 1-pixel-wide arms with a 1px gap at the aim point
        for d in range(2, arm + 1):
            for px, py in (
                (cx + d, cy), (cx - d, cy), (cx, cy + d), (cx, cy - d),
            ):
                if 0 <= px < self.w and 0 <= py < self.h:
                    set_px(px, py, rr, rg, rb)

    def _draw_bombs(self, canvas):
        """Large dark-purple bombs with red core; NV: dark green shell, black core."""
        set_px = canvas.SetPixel
        nv = getattr(self, "_nv", False)
        for b in self.bombs:
            ix, iy = self._world_to_screen(b["x"], b["y"])
            u = 1.0 - b["z"]
            fall = u * u
            sx = _lerp(b["spawn_sx"], ix, fall)
            sy = _lerp(b["spawn_sy"], iy, fall)
            sz = max(0.85, b["size0"] * (0.12 + 0.88 * b["z"]))
            cr = int(math.ceil(sz))
            cx, cy = int(round(sx)), int(round(sy))
            core_r2 = max(0.4, sz * 0.28) ** 2
            shell_r2 = sz * sz
            for dy in range(-cr, cr + 1):
                for dx in range(-cr, cr + 1):
                    d2 = dx * dx + dy * dy
                    if d2 > shell_r2:
                        continue
                    px, py = cx + dx, cy + dy
                    if 0 <= px < self.w and 0 <= py < self.h:
                        if d2 < core_r2:
                            if nv:
                                set_px(px, py, 0, 0, 0)  # hot core → black
                            else:
                                set_px(
                                    px, py,
                                    BOMB_CORE_RGB[0], BOMB_CORE_RGB[1], BOMB_CORE_RGB[2],
                                )
                        else:
                            t = math.sqrt(d2) / max(0.5, sz)
                            shine = _clamp(
                                0.55 + 0.45 * (1.0 - t)
                                + 0.2 * (1.0 if dx + dy < 0 else 0.0),
                                0.0, 1.0,
                            )
                            r = int(_lerp(BOMB_RGB[0], BOMB_SHELL_HI[0], shine))
                            g = int(_lerp(BOMB_RGB[1], BOMB_SHELL_HI[1], shine))
                            bcol = int(_lerp(BOMB_RGB[2], BOMB_SHELL_HI[2], shine))
                            if nv:
                                r, g, bcol = self._to_night_vision(r, g, bcol)
                            set_px(px, py, r, g, bcol)

    def _draw_blasts(self, canvas):
        """Slow smoke ring + fire core. NV: bright blast → black bloom."""
        set_px = canvas.SetPixel
        mpp = self._mpp()
        nv = getattr(self, "_nv", False)
        for bl in self.blasts:
            sx, sy = self._world_to_screen(bl["x"], bl["y"])
            cx, cy = int(round(sx)), int(round(sy))
            u_s = _clamp(bl["t"] / SMOKE_RING_SEC, 0.0, 1.0)
            ring_r = (1.0 + bl["max_r_m"] / max(1.0, mpp)) * (u_s * (2.0 - u_s))
            ring_r = max(1.2, ring_r)
            smoke_a = (1.0 - u_s) * 0.95
            ri = int(math.ceil(ring_r)) + 1
            sr, sg, sb = bl.get("smoke", SMOKE_RGB)
            for dy in range(-ri - 1, ri + 2):
                for dx in range(-ri - 1, ri + 2):
                    d = math.hypot(dx, dy)
                    band = abs(d - ring_r)
                    if band < 1.5 and smoke_a > 0.04:
                        k = (1.0 - band / 1.5) * smoke_a
                        px, py = cx + dx, cy + dy
                        if 0 <= px < self.w and 0 <= py < self.h:
                            if nv:
                                # White smoke is "hot" in NV → near-black ring
                                hot = k * 0.85
                                set_px(px, py, *self._nv_hot_to_black(hot))
                            else:
                                set_px(
                                    px, py,
                                    int(_lerp(70, sr, k)),
                                    int(_lerp(70, sg, k)),
                                    int(_lerp(72, sb, k)),
                                )
            # Fire core
            u_f = _clamp(bl["t"] / FIRE_SEC, 0.0, 1.0)
            fire_r = (2.6 + 1.4 * (1.0 - u_f)) * (1.0 - u_f * 0.45)
            fire_a = (1.0 - u_f) ** 0.65
            fri = int(math.ceil(fire_r)) + 1
            for dy in range(-fri - 1, fri + 2):
                for dx in range(-fri - 1, fri + 2):
                    d = math.hypot(dx, dy)
                    if d > fire_r:
                        continue
                    t = 1.0 - d / max(0.25, fire_r)
                    px, py = cx + dx, cy + dy
                    if 0 <= px < self.w and 0 <= py < self.h:
                        if nv:
                            # Brightest fire → pure black under night vision
                            hot = t * fire_a
                            set_px(px, py, *self._nv_hot_to_black(0.55 + 0.45 * hot))
                        else:
                            fr = int(_lerp(FIRE_RGB[0], FIRE_CORE[0], t * t) * fire_a)
                            fg = int(_lerp(FIRE_RGB[1], FIRE_CORE[1], t * t) * fire_a)
                            fb = int(_lerp(FIRE_RGB[2], FIRE_CORE[2], t * 0.45) * fire_a)
                            set_px(px, py, fr, fg, fb)


# ---------------- Title (Central Park–style letters, shiny purple) ----------------
_PB_TITLE_LINE1 = "PLANET"
_PB_TITLE_LINE2 = "BLAST"
_PB_TITLE_ZOOM = 1
_PB_TITLE_GAP = 1
_PB_TITLE_LINE_GAP = 2
# Shiny purple body shades (highlight → deep)
_PB_TITLE_SHADES = (
    (220, 160, 255),   # bright lilac highlight
    (200, 100, 255),
    (180, 70, 245),
    (160, 50, 230),
    (210, 130, 255),
    (150, 40, 220),
    (190, 90, 250),
    (130, 30, 200),
    (240, 180, 255),   # near-white purple sheen
    (170, 60, 240),
    (145, 35, 210),
    (200, 110, 255),
)
_PB_SHADOW_SCALE = 0.22       # deep purple drop shadow
_PB_SHADOW_RGB = (40, 0, 70)  # fixed dark purple shadow tint
_PB_FADE_IN_SEC = 2.4
_PB_FADE_STAGGER = 0.12
_PB_HOLD_SEC = 0.55
_PB_TITLE_FPS = 28
# After title: target letters with crosshair + bombs → particle detonations
_PB_COMBAT_MAX_SEC = 18.0
_PB_AIM_SEC = 0.45             # crosshair lock before each drop
_PB_BOMB_FALL_SEC = 0.55
_PB_PARTICLE_COLORS = (
    (255, 220, 80),
    (255, 120, 40),
    (255, 60, 30),
    (220, 80, 255),
    (180, 60, 255),
    (255, 255, 200),
    (160, 40, 200),
)


def _pb_title_letter_sprite(char):
    ch = char.upper()
    if not ("A" <= ch <= "Z"):
        return None
    idx = ord(ch) - ord("A")
    try:
        return LED.TrimSprite(copy.deepcopy(LED.AlphaSpriteList[idx]))
    except Exception:
        return None


def _pb_title_sprite_pixels(sprite, zoom, rgb, shadow_rgb):
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


def _pb_title_shade(i):
    return _PB_TITLE_SHADES[i % len(_PB_TITLE_SHADES)]


def _pb_title_shadow(rgb):
    """Deep purple drop shadow with a touch of letter color."""
    return (
        max(0, min(255, int(_PB_SHADOW_RGB[0] * 0.75 + rgb[0] * _PB_SHADOW_SCALE))),
        max(0, min(255, int(_PB_SHADOW_RGB[1] * 0.75 + rgb[1] * _PB_SHADOW_SCALE))),
        max(0, min(255, int(_PB_SHADOW_RGB[2] * 0.75 + rgb[2] * _PB_SHADOW_SCALE))),
    )


class _PbTitleLetter(object):
    """Title letter that fades in, then can detonate into particles."""

    def __init__(self, pixels, shadow_pixels, width, height, rest_x, rest_y, fade_delay):
        self.pixels = pixels
        self.shadow_pixels = shadow_pixels
        self.width = width
        self.height = height
        self.x = float(rest_x)
        self.y = float(rest_y)
        self.fade_delay = float(fade_delay)
        self.alpha = 0.0
        self.alive = True

    def center(self):
        return self.x + self.width * 0.5, self.y + self.height * 0.5

    def update_fade(self, elapsed):
        t = elapsed - self.fade_delay
        if t <= 0:
            self.alpha = 0.0
            return False
        self.alpha = min(1.0, t / _PB_FADE_IN_SEC)
        return self.alpha >= 1.0

    def detonate(self):
        """
        Convert letter pixels into outward particles (Defender/DotZerk style).
        Returns list of particle dicts; marks letter dead.
        """
        parts = []
        if not self.alive:
            return parts
        self.alive = False
        ox, oy = self.x, self.y
        cx, cy = self.center()
        for dx, dy, rgb in self.pixels:
            px = ox + dx
            py = oy + dy
            # Burst outward from letter center + random kick
            ang = math.atan2(py - cy, px - cx) + random.uniform(-0.4, 0.4)
            if abs(px - cx) + abs(py - cy) < 0.2:
                ang = random.uniform(0, math.pi * 2)
            speed = 0.35 + random.random() * 1.35
            parts.append({
                "x": float(px),
                "y": float(py),
                "vx": math.cos(ang) * speed + random.uniform(-0.25, 0.25),
                "vy": math.sin(ang) * speed + random.uniform(-0.45, 0.1),
                "life": random.uniform(0.45, 1.15),
                "t": 0.0,
                "rgb": rgb,
                "hot": random.random() < 0.35,
            })
            # Extra spark every few pixels
            if random.random() < 0.35:
                spark = random.choice(_PB_PARTICLE_COLORS)
                parts.append({
                    "x": float(px),
                    "y": float(py),
                    "vx": random.uniform(-1.2, 1.2),
                    "vy": random.uniform(-1.6, 0.4),
                    "life": random.uniform(0.3, 0.8),
                    "t": 0.0,
                    "rgb": spark,
                    "hot": True,
                })
        return parts

    def draw(self, canvas, panel_w, panel_h):
        if not self.alive or self.alpha <= 0.02:
            return
        a = self.alpha
        set_px = canvas.SetPixel
        ox, oy = int(round(self.x)), int(round(self.y))
        for dx, dy, rgb in self.shadow_pixels:
            px, py = ox + dx, oy + dy
            if 0 <= px < panel_w and 0 <= py < panel_h:
                set_px(
                    px, py,
                    int(rgb[0] * a),
                    int(rgb[1] * a),
                    int(rgb[2] * a),
                )
        for dx, dy, rgb in self.pixels:
            px, py = ox + dx, oy + dy
            if 0 <= px < panel_w and 0 <= py < panel_h:
                set_px(
                    px, py,
                    int(rgb[0] * a),
                    int(rgb[1] * a),
                    int(rgb[2] * a),
                )


def _pb_draw_crosshair(canvas, cx, cy, panel_w, panel_h, rgb=None):
    """1px reticle on a title letter."""
    rr, rg, rb = rgb if rgb is not None else CROSSHAIR_LOCK_RGB
    set_px = canvas.SetPixel
    cx, cy = int(round(cx)), int(round(cy))
    arm = 4
    for d in range(2, arm + 1):
        for px, py in (
            (cx + d, cy), (cx - d, cy), (cx, cy + d), (cx, cy - d),
        ):
            if 0 <= px < panel_w and 0 <= py < panel_h:
                set_px(px, py, rr, rg, rb)


def _pb_draw_title_bomb(canvas, sx, sy, size, panel_w, panel_h):
    """Dark purple bomb with red core (matches in-mission ordnance)."""
    set_px = canvas.SetPixel
    cr = int(math.ceil(size))
    cx, cy = int(round(sx)), int(round(sy))
    core_r2 = max(0.4, size * 0.28) ** 2
    shell_r2 = size * size
    for dy in range(-cr, cr + 1):
        for dx in range(-cr, cr + 1):
            d2 = dx * dx + dy * dy
            if d2 > shell_r2:
                continue
            px, py = cx + dx, cy + dy
            if 0 <= px < panel_w and 0 <= py < panel_h:
                if d2 < core_r2:
                    set_px(px, py, BOMB_CORE_RGB[0], BOMB_CORE_RGB[1], BOMB_CORE_RGB[2])
                else:
                    set_px(px, py, BOMB_RGB[0], BOMB_RGB[1], BOMB_RGB[2])


def _pb_update_particles(particles, dt, panel_w, panel_h):
    alive = []
    for p in particles:
        p["t"] += dt
        if p["t"] >= p["life"]:
            continue
        p["vy"] += 2.8 * dt  # gravity
        p["x"] += p["vx"] * dt * 28.0
        p["y"] += p["vy"] * dt * 28.0
        if -2 <= p["x"] < panel_w + 2 and -2 <= p["y"] < panel_h + 2:
            alive.append(p)
    return alive


def _pb_draw_particles(canvas, particles, panel_w, panel_h):
    set_px = canvas.SetPixel
    for p in particles:
        u = _clamp(p["t"] / max(0.05, p["life"]), 0.0, 1.0)
        fade = 1.0 - u
        px, py = int(round(p["x"])), int(round(p["y"]))
        if not (0 <= px < panel_w and 0 <= py < panel_h):
            continue
        if p.get("hot") and u < 0.25:
            set_px(px, py, 255, 240, 120)
        else:
            r, g, b = p["rgb"]
            set_px(
                px, py,
                int(r * fade),
                int(g * fade),
                int(b * fade),
            )


def _build_planet_blast_title_letters(panel_w, panel_h):
    """PLANET / BLAST — multi-shade reds, blues, purples like Central Park."""
    lines = [_PB_TITLE_LINE1, _PB_TITLE_LINE2]
    line_specs = []
    max_h = 0
    shade_i = 0
    for line in lines:
        specs = []
        for char in line:
            if char == " ":
                continue
            sprite = _pb_title_letter_sprite(char)
            if sprite is None:
                continue
            rgb = _pb_title_shade(shade_i)
            shade_i += 1
            shadow = _pb_title_shadow(rgb)
            pixels, shadow_pixels, lw, lh = _pb_title_sprite_pixels(
                sprite, _PB_TITLE_ZOOM, rgb, shadow,
            )
            specs.append((pixels, shadow_pixels, lw, lh))
            if lh > max_h:
                max_h = lh
        line_specs.append(specs)

    if not any(line_specs):
        return []

    total_h = max_h * len(line_specs) + _PB_TITLE_LINE_GAP * max(0, len(line_specs) - 1)
    top_y = max(0, (panel_h - total_h) // 2)
    letters = []
    letter_index = 0
    for line_i, specs in enumerate(line_specs):
        if not specs:
            continue
        total_w = sum(s[2] for s in specs) + _PB_TITLE_GAP * max(0, len(specs) - 1)
        x_cursor = max(0, (panel_w - total_w) // 2)
        rest_y = top_y + line_i * (max_h + _PB_TITLE_LINE_GAP)
        for pixels, shadow_pixels, lw, lh in specs:
            letters.append(_PbTitleLetter(
                pixels, shadow_pixels, lw, lh,
                x_cursor, rest_y + (max_h - lh),
                fade_delay=letter_index * _PB_FADE_STAGGER,
            ))
            x_cursor += lw + _PB_TITLE_GAP
            letter_index += 1
    return letters


def PlayPlanetBlastTitle(StopEvent=None):
    """
    PLANET / BLAST title:
      1) Shiny purple letters fade in (Central Park style)
      2) Crosshair locks random letters and bombs destroy them
      3) Hit letters detonate into particles
    """
    if _stop(StopEvent):
        return
    panel_w = int(getattr(LED, "HatWidth", 64) or 64)
    panel_h = int(getattr(LED, "HatHeight", 32) or 32)
    letters = _build_planet_blast_title_letters(panel_w, panel_h)
    if not letters:
        print("[PlanetBlast] Title skipped (no letter sprites)")
        return

    print("[PlanetBlast] Title — PLANET BLAST (purple letters → bomb letters)")
    try:
        canvas = LED.TheMatrix.CreateFrameCanvas()
    except Exception:
        canvas = LED.Canvas

    tick = pygame.time.Clock() if HAS_PYGAME else None
    t0 = time.time()
    fully_in_at = None
    phase = "fade"          # fade | combat | cleanup
    combat_t0 = None
    cleanup_t0 = 0.0
    aim_t = 0.0
    target = None
    bombs = []              # in-flight bombs; aim next letter while they fall
    particles = []
    last = time.time()

    def _reserved_letters():
        """Letters already assigned to a falling bomb or current aim."""
        res = set()
        if target is not None:
            res.add(id(target))
        for b in bombs:
            t = b.get("target")
            if t is not None:
                res.add(id(t))
        return res

    def _spawn_bomb_at(letter):
        tx, ty = letter.center()
        return {
            "sx": random.uniform(2.0, panel_w - 3.0),
            "sy": random.uniform(-4.0, 1.0),
            "tx": tx + random.uniform(-1.2, 1.2),
            "ty": ty + random.uniform(-0.8, 0.8),
            "t": 0.0,
            "size0": 4.5,
            "target": letter,
            "x": 0.0,
            "y": 0.0,
            "z": 1.0,
        }

    try:
        while True:
            if _stop(StopEvent):
                break
            now = time.time()
            dt = _clamp(now - last, 0.001, 0.08)
            last = now
            elapsed = now - t0

            if phase == "fade":
                all_in = True
                for L in letters:
                    if not L.update_fade(elapsed):
                        all_in = False
                if all_in and fully_in_at is None:
                    fully_in_at = now
                if fully_in_at is not None and (now - fully_in_at) >= _PB_HOLD_SEC:
                    phase = "combat"
                    combat_t0 = now
                    aim_t = 0.0
                    target = None
                    bombs = []
                    print("[PlanetBlast] Title combat — bombing letters (pipelined)")
                if elapsed > _PB_FADE_IN_SEC + len(letters) * _PB_FADE_STAGGER + _PB_HOLD_SEC + 2.0:
                    phase = "combat"
                    combat_t0 = now

            elif phase == "combat":
                alive = [L for L in letters if L.alive]
                if not alive and not particles and not bombs:
                    phase = "cleanup"
                    cleanup_t0 = now
                elif combat_t0 is not None and (now - combat_t0) > _PB_COMBAT_MAX_SEC:
                    for L in alive:
                        particles.extend(L.detonate())
                    bombs = []
                    target = None
                    phase = "cleanup"
                    cleanup_t0 = now
                else:
                    reserved = _reserved_letters()
                    free = [L for L in alive if id(L) not in reserved]

                    # Always work the reticle: aim / drop even while bombs fall
                    if target is None and free:
                        target = random.choice(free)
                        aim_t = 0.0
                    if target is not None:
                        if not target.alive:
                            target = None
                            aim_t = 0.0
                        else:
                            aim_t += dt
                            if aim_t >= _PB_AIM_SEC:
                                bombs.append(_spawn_bomb_at(target))
                                target = None
                                aim_t = 0.0
                                # Immediately start acquiring the next free letter
                                reserved = _reserved_letters()
                                free = [L for L in letters if L.alive and id(L) not in reserved]
                                if free:
                                    target = random.choice(free)
                                    aim_t = 0.0

                    # Advance all in-flight bombs
                    still = []
                    for bomb in bombs:
                        bomb["t"] += dt
                        u = _clamp(bomb["t"] / _PB_BOMB_FALL_SEC, 0.0, 1.0)
                        fall = u * u
                        bx = _lerp(bomb["sx"], bomb["tx"], fall)
                        by = _lerp(bomb["sy"], bomb["ty"], fall)
                        bomb["x"] = bx
                        bomb["y"] = by
                        bomb["z"] = 1.0 - u
                        if u < 1.0:
                            still.append(bomb)
                            continue
                        # Impact
                        tgt = bomb.get("target")
                        if tgt is not None and tgt.alive:
                            particles.extend(tgt.detonate())
                        for _ in range(10):
                            ang = random.uniform(0, math.pi * 2)
                            sp = 0.5 + random.random() * 1.2
                            particles.append({
                                "x": bx, "y": by,
                                "vx": math.cos(ang) * sp,
                                "vy": math.sin(ang) * sp,
                                "life": random.uniform(0.25, 0.7),
                                "t": 0.0,
                                "rgb": random.choice(_PB_PARTICLE_COLORS),
                                "hot": True,
                            })
                    bombs = still

                particles = _pb_update_particles(particles, dt, panel_w, panel_h)

            elif phase == "cleanup":
                particles = _pb_update_particles(particles, dt, panel_w, panel_h)
                if not particles or (now - cleanup_t0) > 1.4:
                    break

            # Draw
            try:
                canvas.Fill(0, 0, 0)
                for L in letters:
                    L.draw(canvas, panel_w, panel_h)
                _pb_draw_particles(canvas, particles, panel_w, panel_h)
                if phase == "combat":
                    if target is not None and target.alive:
                        tcx, tcy = target.center()
                        _pb_draw_crosshair(canvas, tcx, tcy, panel_w, panel_h)
                    for bomb in bombs:
                        sz = max(1.0, bomb["size0"] * (0.2 + 0.8 * bomb.get("z", 1.0)))
                        _pb_draw_title_bomb(
                            canvas, bomb["x"], bomb["y"], sz, panel_w, panel_h,
                        )
                canvas = LED.TheMatrix.SwapOnVSync(canvas)
                LED.Canvas = canvas
            except Exception:
                pass

            if tick:
                tick.tick(_PB_TITLE_FPS)
            else:
                time.sleep(1.0 / _PB_TITLE_FPS)
    except Exception as exc:
        print(f"[PlanetBlast] title failed: {exc}")

    try:
        LED.ClearBigLED()
        LED.ClearBuffers()
        LED.TheMatrix.Clear()
    except Exception:
        pass
    print("[PlanetBlast] Title complete — beginning mission")


def PlayPlanetFly(Duration=10, StopEvent=None):
    """Space intro → planet approach → surface strike tour. Duration in minutes."""
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

    # One planet map for globe zoom AND surface flight
    planet = PlanetMap()
    intro = SpaceIntro(width, height, planet=planet)
    cam = None
    tick = pygame.time.Clock() if HAS_PYGAME else None
    last = time.time()

    print(
        f"[PlanetBlast] {width}x{height}  space → zoom city → strike  "
        f"duration={run_min} min  fps~{TARGET_FPS}"
    )

    try:
        while True:
            if _stop(StopEvent):
                print("[PlanetFly] StopEvent — exit")
                break
            if time.time() - start > run_min * 60.0:
                print("[PlanetFly] Duration reached — exit")
                break

            now = time.time()
            dt = _clamp(now - last, 0.001, 0.1)
            last = now

            try:
                if cam is None:
                    intro.update(dt)
                    intro.draw(canvas)
                    if intro.done:
                        cam = PlanetCamera(
                            width, height,
                            planet=intro.planet,
                            city=intro.showcase,
                        )
                else:
                    cam.update(dt)
                    canvas.Fill(0, 0, 8)
                    cam.render(canvas)

                canvas = LED.TheMatrix.SwapOnVSync(canvas)
                LED.Canvas = canvas
            except Exception:
                pass

            if tick:
                tick.tick(TARGET_FPS)
            else:
                time.sleep(1.0 / TARGET_FPS)

    except KeyboardInterrupt:
        print("[PlanetFly] Interrupted")

    try:
        LED.ClearBuffers()
        LED.TheMatrix.Clear()
    except Exception:
        pass


def LaunchPlanetFly(Duration=10, ShowIntro=True, StopEvent=None):
    """Public entry for LEDcommander / Twitch / LEDsim — Planet Blast."""
    try:
        LED.LoadConfigData()
    except Exception:
        pass
    if ShowIntro:
        try:
            PlayPlanetBlastTitle(StopEvent=StopEvent)
        except Exception as exc:
            print(f"[PlanetBlast] intro failed: {exc}")
        try:
            LED.ClearBigLED()
            LED.ClearBuffers()
        except Exception:
            pass
    if _stop(StopEvent):
        return
    PlayPlanetFly(Duration=Duration, StopEvent=StopEvent)


# Friendly alias
LaunchPlanetBlast = LaunchPlanetFly


if __name__ == "__main__":
    try:
        LaunchPlanetFly(Duration=30, ShowIntro=True, StopEvent=None)
    except KeyboardInterrupt:
        print("Exiting Planet Blast.")
