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

# Numba: cache=True writes machine code under __pycache__ for reuse across runs.
try:
    from numba import njit as _numba_njit
    HAS_NUMBA = True
except ImportError:
    HAS_NUMBA = False
    _numba_njit = None


def _jit(fn):
    """@njit(cache=True) when Numba is available; identity otherwise."""
    if HAS_NUMBA:
        return _numba_njit(cache=True)(fn)
    return fn


_numba_warmed = False


# ---------------- Configuration ----------------
TARGET_FPS = 30
# Flight altitudes (feet) — top-down view; FOV → ground span
_FOV_DEG = 50.0
# City tour: zoom in until city ≈ CITY_TARGET_PX wide, bomb until gone, next
CITY_TARGET_PX = 20.0          # zoom until city footprint is ~this many pixels wide
CITY_WIDE_PX = 4.0             # overview size before zoom-in / after zoom-out
ZOOM_IN_SEC = 2.8              # SCAN → LOCK (was 4.5 — snappier acquire)
ZOOM_OUT_SEC = 4.0
# After a kill: pull out to full globe, orbit, pick next target, dive in
ORBIT_OUT_SEC = 7.0            # smooth climb surface → full planet (no hard cut)
ORBIT_OUT_FLAT_U = 0.55        # fraction of pullback spent as flat map zoom-out
ORBIT_TURN_SEC = 5.5           # rotate around the world before/while locking next tgt
ORBIT_IN_SEC = 7.5             # continuous dive globe → surface → strike alt (no jump)
ORBIT_IN_FLAT_U = 0.38         # fraction of dive spent flattening sphere → map
ORBIT_SPIN_RAD = 1.35          # radians of free spin before target lock
# (Megacity stamp overlays removed — cities only via baked city_paint)
# Night vision: only true night (below twilight). Day + twilight stay normal color.
NV_NIGHT_MAX = 0.20            # day_factor < this → night (NV on)
# After a kill (legacy cruise path kept for first strike / patrol handoff)
NEXT_MIN_SEP_M = 22_000.0      # ignore targets basically under the crater
CRUISE_TO_ARRIVE_M = 52_000.0  # must be this close before zoom-in starts
CRUISE_TO_MPS = 48_000.0       # strike-alt transit (m/s) — doubled for readable scan flight
CRUISE_TO_MAX_SEC = 10.0       # if ETA > this at strike speed → climb + go faster
CRUISE_TO_FAST_MPS = 120_000.0 # high-altitude dash speed cap (m/s)
CRUISE_TO_APPROACH_M = 120_000.0  # begin descent (shorter slow segment than 200 km)
ZOOM_TRACK_MPS = 28_000.0      # reticle fine-track during zoom-in / SCAN
# Alternate batches: 5 night targets, then 5 day, repeat until all gone
TARGETS_PER_BATCH = 5
NIGHT_DAY_MAX = 0.40           # day_factor ≤ this → night target
DAY_DAY_MIN = 0.58             # day_factor ≥ this → day target
# After every N cities bombed: peaceful patrol (no weapons)
PATROL_EVERY = 10              # cities destroyed before patrol
PATROL_SEC = 60.0              # patrol duration
PATROL_LEG_MIN = 5.0           # seconds between patrol waypoints
PATROL_LEG_MAX = 9.0
# Engagement: roll city quota before strike; dice surrender after each kill
SURRENDER_QUOTA_MIN = 2        # min cities WARCOM expects to hit
SURRENDER_QUOTA_MAX = 8        # max engagement target (capped by planet city count)
SURRENDER_BASE_CHANCE = 0.10   # surrender chance after 1st kill
SURRENDER_PER_KILL = 0.12      # added chance per additional kill
SURRENDER_AT_QUOTA = 0.55      # chance when engagement quota met (not forced)
SURRENDER_SHOW_SEC = 3.5       # hold SURRENDER HUD before leaving the world
# Opening: hold full globe with clock + WARCOM chatter, then attack order, then dive
ORBIT_HOLD_SEC = 50.0          # chatter / hold at planet level before WARCOM GO
CRUISE_SEC = 60.0              # legacy surface-cruise duration (patrol ticker fallback)
CRUISE_LEG_MIN = 6.0
CRUISE_LEG_MAX = 10.0
CRUISE_TICKER_PPS = 30.0       # pixels/sec — ~1 px/frame @ TARGET_FPS for smooth marquee
# WARCOM / intel chatter + stats (orbit hold, transit, patrol)
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
BOMB_AIM_SPREAD = 0.4125       # aim scatter as fraction of city radius (−25% error)
BOMB_AIM_LONGSHOT = 0.165      # chance of a long miss beyond normal spread (−25%)
BOMB_DAMAGE = 0.14             # damage per hit near center (size scales)
SMOKE_RING_SEC = 2.4           # slow expanding smoke ring
FIRE_SEC = 1.8
CROSSHAIR_UP_PX = 4            # reticle is panel-center, this many px up
# Camera track error while bombing (city under reticle, imperfect)
CAM_AIM_ERR_M = 24_000.0       # max wander from ideal city lock (m) (−25%)
CAM_AIM_WANDER = 0.41          # how fast aim error drifts (−25%)
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
ASH_RGB = (42, 36, 30)             # scorched forest floor (map paint)
# Fire/ember colors stamped onto the map (varying mix — not a separate layer)
_FIRE_PAINT_COLORS = (
    (255, 48, 12),   # hot red
    (230, 60, 18),   # red-orange
    (200, 55, 22),   # deep ember
    (160, 42, 20),   # dark ember
    (110, 48, 28),   # charred brown
    (70, 40, 28),    # near-ash
    (48, 36, 28),    # ash
    (255, 90, 25),   # bright edge
    (180, 70, 30),   # warm coal
)
# Globe / far view: soft cities (less flicker) + optional 1px pins
GLOBE_CITY_PIN_MIN_SIZE = 3      # stamp stable 1px for cities this size and up
GLOBE_CITY_PIN_MPP = 6_500.0     # only pin when mpp above this (far / full planet)
# Cities + fire share one paint map: stamped once, overwritten by bombs/spread
FIRE_CELL = 8_000.0                # meters per paint cell (coarser → fewer embers)
FIRE_TICK_SEC = 12.0               # slower crawl between spread ticks
FIRE_SPREAD_PER_TICK = 4           # fewer new green cells per tick
FIRE_MAX_CELLS = 3_500             # hard cap on burned cells
FIRE_SEED_DMG = 0.18               # need a bit more damage before wildfire seeds
FIRE_IMPACT_R_CELLS = 1            # impact seed radius in cells (diameter ~1–2)
FIRE_CITY_RING_SCALE = 0.55        # city ring radii vs urban footprint (smaller patches)
# If engagement quota is hit and planet still fights: faster wildfire
FIRE_RAGE_TICK_SEC = 7.0           # shorter interval (still calmer than old rage)
FIRE_RAGE_SPREAD_PER_TICK = 7      # moderate boost when planet refuses to fold
# Night vision (when dark): mono green; hot explosions → black
NV_DAY_THRESH = 0.38           # day_factor below this → NV on
NV_GAIN = 2.15                 # amplify surface contrast so terrain reads
NV_FLOOR = 18.0                # pedestal so oceans/land stay visible
NV_SURF_DAY = 0.78             # sample surface lit enough to show biome detail
# HUD — 3×5 micro font (teeny but readable on LED panels)
# HUD text colors at 80% brightness (20% dimmer than full panel primaries)
HUD_RGB = (32, 204, 72)          # targeting / scan green
HUD_FIRE_RGB = (204, 160, 32)    # firing amber
HUD_ALERT_RGB = (204, 40, 32)    # destroyed red
HUD_DIM_RGB = (16, 112, 56)
HUD_NAME_RGB = (144, 204, 160)   # acquired city name
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
# 50 named worlds (star-system ordinals: Vulcanis III, Tantr X, …)
_PLANET_NAMES = (
    "Vulcanis III", "Tantr X", "Keldor IV", "Nyxara VII", "Ashmere II",
    "Xelion IX", "Miros V", "Thalos VIII", "Zoran Prime", "Saelith VI",
    "Ornax III", "Dravak XII", "Lunaris IV", "Pharos XI", "Rynos II",
    "Veskara IX", "Helion VII", "Iskan V", "Praxis III", "Qantor VIII",
    "Brynnos IV", "Corvex VI", "Deneb Minor", "Eryndor X", "Fomal X",
    "Ganymar III", "Hyperion IX", "Iridon II", "Jotun IV", "Krynn VII",
    "Lothor V", "Manticore III", "Nexara VIII", "Oberon VI", "Phaeton IX",
    "Quoros II", "Rigel Minor", "Solara IV", "Titanos VII", "Umbra III",
    "Vortex V", "Weyland IX", "Xandar II", "Ymir IV", "Zephyros VIII",
    "Andaros VI", "Boreas III", "Cygnus IX", "Delphos IV", "Erebus VII",
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
# Noise scales CONTINENT_SCALE / DETAIL_SCALE / … defined with planet map constants
# ---- Space intro (parallax stars → clock → fly-through → planet zoom) ----
STAR_DRIFT_SEC = 3.0       # pure starfield before the clock appears
SPACE_CLOCK_SEC = 30.0     # floating digital clock in space before planet
SPACE_CLOCK_FLY_SEC = 2.8  # fly-through: clock scales up and we pass through
PLANET_DOT_SEC = 2.2       # bright planet dot after clock fly-through
PLANET_ZOOM_SEC = 5.5      # approach / grow the planet disc to large globe
BRIEFING_HOLD_SEC = 1.2    # brief pause after terminal finishes typing
PLANET_DESCENT_SEC = 0.0   # intro ends at full globe; camera owns continuous dive
# First approach dive (globe → flat → strike) reuses ORBIT_IN_*; clock/chatter on
# Large retro digital clock — 5×9 hairline digits (1px strokes, open counters)
_CLOCK_DIGIT_W = 5
_CLOCK_DIGIT_H = 9
_CLOCK_DIGIT_GAP = 1
_CLOCK_RGB = (40, 220, 180)       # teal CRT / retro digital
# 5-wide bit rows (MSB left) — single-pixel stroke skeleton
_CLOCK_DIGITS = {
    "0": (
        0b01110,
        0b10001,
        0b10001,
        0b10001,
        0b10001,
        0b10001,
        0b10001,
        0b10001,
        0b01110,
    ),
    "1": (
        0b00100,
        0b01100,
        0b00100,
        0b00100,
        0b00100,
        0b00100,
        0b00100,
        0b00100,
        0b01110,
    ),
    "2": (
        0b01110,
        0b10001,
        0b00001,
        0b00001,
        0b00010,
        0b00100,
        0b01000,
        0b10000,
        0b11111,
    ),
    "3": (
        0b01110,
        0b10001,
        0b00001,
        0b00001,
        0b00110,
        0b00001,
        0b00001,
        0b10001,
        0b01110,
    ),
    "4": (
        0b00010,
        0b00110,
        0b01010,
        0b10010,
        0b11111,
        0b00010,
        0b00010,
        0b00010,
        0b00010,
    ),
    "5": (
        0b11111,
        0b10000,
        0b10000,
        0b11110,
        0b00001,
        0b00001,
        0b00001,
        0b10001,
        0b01110,
    ),
    "6": (
        0b00110,
        0b01000,
        0b10000,
        0b11110,
        0b10001,
        0b10001,
        0b10001,
        0b10001,
        0b01110,
    ),
    "7": (
        0b11111,
        0b00001,
        0b00010,
        0b00010,
        0b00100,
        0b00100,
        0b01000,
        0b01000,
        0b01000,
    ),
    "8": (
        0b01110,
        0b10001,
        0b10001,
        0b10001,
        0b01110,
        0b10001,
        0b10001,
        0b10001,
        0b01110,
    ),
    "9": (
        0b01110,
        0b10001,
        0b10001,
        0b10001,
        0b01111,
        0b00001,
        0b00001,
        0b00010,
        0b01100,
    ),
    ":": (
        0b00000,
        0b00100,
        0b00100,
        0b00000,
        0b00000,
        0b00000,
        0b00100,
        0b00100,
        0b00000,
    ),
}
# Empire news ticker during space clock (built once, ≥100 items)
# Frame-locked 1 px per update — matches TARGET_FPS for even LED marquee motion
SPACE_NEWS_PPS = float(TARGET_FPS)
TERM_CPS = 14.0            # approach dossier typewriter chars/sec
TERM_LINE_GAP = 1          # px between terminal rows
TERM_SCROLL_SEC = 0.30     # smooth line-up: one row height over this many seconds
# Random dossier STATUS: lines (picked once per approach)
TERM_STATUSES = (
    "PENDING",
    "GUILTY",
    "ENDANGERED",
    "INDICTED",
    "WANTED",
    "HOSTILE",
    "QUARANTINED",
    "CONDEMNED",
    "AT LARGE",
    "SENTENCED",
    "HIGH PRIORITY",
    "UNDER REVIEW",
    "EXTERMINATUS PENDING",
    "CLEARED FOR STRIKE",
    "ARMED RESPONSE",
    "NO SURRENDER",
    "THREAT LEVEL RED",
    "ORBITAL AUTHORIZED",
)
# Terminal starts only once the disc is a large globe (end of zoom)
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


# ---------------- Shared planet surface map (constants before Numba kernels) ---
# World coords are meters on an equirectangular unwrap; same map for globe + flyover.
PLANET_R = 2_000_000.0       # baseline map scale: lon/lat * R → meters (LARGEST)
# Per-planet radius multiplier — always strictly below baseline (1.0×)
# Log-uniform in [MIN, MAX]; baseline 1.0× is never rolled.
PLANET_SIZE_MIN = 0.22       # dwarf / moonlet
PLANET_SIZE_MAX = 0.98       # near-baseline (still smaller than 1.0×)
# Elevation threshold: ~75% of the surface is ocean (land only above this)
SEA_LEVEL = 0.58
CITY_CELL = 80_000.0         # spatial hash cell for cities (m)
CITY_COUNT_MIN = 10
CITY_COUNT_MAX = 50          # hard cap — fewer cities, no road network
CITY_DAY = (105, 105, 112)       # readable gray urban mass from altitude
CITY_DAY_CORE = (130, 128, 125)  # denser core
CITY_NIGHT = (255, 200, 90)
CITY_GLOW = (255, 140, 40)
# Noise scales (also used as module globals inside @njit)
CONTINENT_SCALE = 1.0 / 720_000.0   # broad continents
DETAIL_SCALE = 1.0 / 70_000.0
RIVER_SCALE = 1.0 / 32_000.0
MOUNTAIN_SCALE = 1.0 / 110_000.0


# ---------------- Hash noise + terrain (Numba @njit cache=True) ----------------
# Hot path: every surface pixel samples elev via FBM.
# cache=True → machine code saved under __pycache__; reloads next process.
_INV_I31 = 1.0 / 2147483647.0


@_jit
def _n_clamp(v, lo, hi):
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


@_jit
def _n_smoothstep(t):
    if t < 0.0:
        t = 0.0
    elif t > 1.0:
        t = 1.0
    return t * t * (3.0 - 2.0 * t)


@_jit
def _n_smooth_edge(v, a, b):
    if b <= a:
        return 1.0 if v >= a else 0.0
    return _n_smoothstep((v - a) / (b - a))


@_jit
def _hash2(ix, iy, seed):
    """Deterministic 0..1 hash of integer lattice + seed."""
    n = (ix * 374761393 + iy * 668265263 + seed * 1274126177) & 0x7FFFFFFF
    n = (n ^ (n >> 13)) * 1274126177
    n = (n ^ (n >> 16)) & 0x7FFFFFFF
    return n * _INV_I31


@_jit
def _value_noise(x, y, seed):
    """Bilinear value noise; x,y continuous. Hash corners inlined."""
    x0 = int(math.floor(x))
    y0 = int(math.floor(y))
    fx = x - x0
    fy = y - y0
    ux = fx * fx * (3.0 - 2.0 * fx)
    uy = fy * fy * (3.0 - 2.0 * fy)
    s = seed
    n = (x0 * 374761393 + y0 * 668265263 + s * 1274126177) & 0x7FFFFFFF
    n = (n ^ (n >> 13)) * 1274126177
    v00 = ((n ^ (n >> 16)) & 0x7FFFFFFF) * _INV_I31
    n = ((x0 + 1) * 374761393 + y0 * 668265263 + s * 1274126177) & 0x7FFFFFFF
    n = (n ^ (n >> 13)) * 1274126177
    v10 = ((n ^ (n >> 16)) & 0x7FFFFFFF) * _INV_I31
    n = (x0 * 374761393 + (y0 + 1) * 668265263 + s * 1274126177) & 0x7FFFFFFF
    n = (n ^ (n >> 13)) * 1274126177
    v01 = ((n ^ (n >> 16)) & 0x7FFFFFFF) * _INV_I31
    n = ((x0 + 1) * 374761393 + (y0 + 1) * 668265263 + s * 1274126177) & 0x7FFFFFFF
    n = (n ^ (n >> 13)) * 1274126177
    v11 = ((n ^ (n >> 16)) & 0x7FFFFFFF) * _INV_I31
    a = v00 + (v10 - v00) * ux
    b = v01 + (v11 - v01) * ux
    return a + (b - a) * uy


@_jit
def _fbm(x, y, seed, octaves, lacunarity, gain):
    amp = 1.0
    freq = 1.0
    total = 0.0
    norm = 0.0
    for i in range(octaves):
        total += amp * _value_noise(x * freq, y * freq, seed + i * 1013)
        norm += amp
        amp *= gain
        freq *= lacunarity
    if norm < 1e-9:
        return 0.0
    return total / norm


@_jit
def _fbm_fast(x, y, seed, octaves):
    """
    Cheap FBM for realtime surface (fixed lacunarity 2, gain 0.5).
    Unrolled for 1–3 octaves — the elev hot path.
    """
    if octaves <= 1:
        return _value_noise(x, y, seed)
    v = _value_noise(x, y, seed)
    v2 = _value_noise(x * 2.0, y * 2.0, seed + 1013)
    if octaves == 2:
        return (v + 0.5 * v2) * (1.0 / 1.5)
    v3 = _value_noise(x * 4.0, y * 4.0, seed + 2026)
    return (v + 0.5 * v2 + 0.25 * v3) * (1.0 / 1.75)


@_jit
def _elev_raw_n(wx, wy, seed, lod):
    """
    Elevation + continent/detail/mountain.
    lod 0: 1 octave continent only; lod 1–2: 2+1+1 octaves.
    Returns (elev, c, d, mountain).
    """
    if lod <= 0:
        c = _fbm_fast(wx * CONTINENT_SCALE, wy * CONTINENT_SCALE, seed, 1)
        if c < 0.0:
            c = 0.0
        elif c > 1.0:
            c = 1.0
        return c, c, 0.5, 0.0
    c = _fbm_fast(wx * CONTINENT_SCALE, wy * CONTINENT_SCALE, seed, 2)
    d = _fbm_fast(wx * DETAIL_SCALE, wy * DETAIL_SCALE, seed + 7, 1)
    m_raw = _fbm_fast(wx * MOUNTAIN_SCALE, wy * MOUNTAIN_SCALE, seed + 19, 1)
    mountain = 1.0 - abs(2.0 * m_raw - 1.0)
    mountain *= mountain
    elev = c * 0.72 + d * 0.14 + mountain * 0.14
    if elev < 0.0:
        elev = 0.0
    elif elev > 1.0:
        elev = 1.0
    return elev, c, d, mountain


@_jit
def _is_river_n(wx, wy, elev, moist, seed):
    river_n = _value_noise(wx * RIVER_SCALE, wy * RIVER_SCALE, seed + 55)
    river_ridge = 1.0 - abs(2.0 * river_n - 1.0)
    river_w = _n_smooth_edge(river_ridge, 0.84, 0.96)
    river_ok = _n_smooth_edge(elev, SEA_LEVEL + 0.01, SEA_LEVEL + 0.04)
    river_ok *= 1.0 - _n_smooth_edge(elev, 0.68, 0.78)
    river_ok *= _n_smooth_edge(moist, 0.28, 0.45)
    return river_w * river_ok


@_jit
def _sample_biome_n(wx, wy, seed, lod):
    """
    Daytime surface color + meta.
    Returns (r, g, b, elev, river_amt, land_flag) with land_flag 1.0 or 0.0.
    """
    elev, c, d, mountain = _elev_raw_n(wx, wy, seed, lod)
    if lod <= 0:
        moist = 0.45
    else:
        moist_oct = 1 if lod < 2 else 2
        moist = _fbm_fast(
            wx * DETAIL_SCALE * 0.7, wy * DETAIL_SCALE * 0.7,
            seed + 31, moist_oct,
        )
    lat_norm = wy / (PLANET_R * (math.pi * 0.5))
    if lat_norm < -1.0:
        lat_norm = -1.0
    elif lat_norm > 1.0:
        lat_norm = 1.0

    river_amt = 0.0
    land = 0.0
    if elev < SEA_LEVEL:
        # Oceans: deep navy → mid cobalt → thin shallow shelf (high contrast)
        # deep abyss (low elev)
        t_deep = _n_smooth_edge(elev, SEA_LEVEL - 0.16, SEA_LEVEL - 0.05)
        r = 2.0 + (6.0 - 2.0) * t_deep
        g = 12.0 + (32.0 - 12.0) * t_deep
        b = 55.0 + (110.0 - 55.0) * t_deep
        # shallow shelf — still blue, not teal/cyan wash
        t_shal = _n_smooth_edge(elev, SEA_LEVEL - 0.055, SEA_LEVEL - 0.008)
        r = r + (18.0 - r) * t_shal
        g = g + (70.0 - g) * t_shal
        b = b + (145.0 - b) * t_shal
        if lod >= 1:
            # thin shore line only — less foam so blue stays deep
            t_foam = _n_smooth_edge(elev, SEA_LEVEL - 0.012, SEA_LEVEL) * 0.14
            r = r + (90.0 - r) * t_foam
            g = g + (130.0 - g) * t_foam
            b = b + (155.0 - b) * t_foam
        land = 0.0
    else:
        land = 1.0
        denom = 1.0 - SEA_LEVEL
        if denom < 1e-6:
            denom = 1e-6
        land_h = (elev - SEA_LEVEL) / denom
        # desert (warm sand/ochre) vs grass/forest (saturated green) — push apart
        # sand / desert: yellower, less green mud
        dr = 195.0 + (225.0 - 195.0) * land_h
        dg = 145.0 + (165.0 - 145.0) * land_h
        db = 55.0 + (70.0 - 55.0) * land_h
        # grass: deeper emerald, less brown
        gt = land_h * 0.45 + moist * 0.4
        gr = 28.0 + (55.0 - 28.0) * gt
        gg = 105.0 + (155.0 - 105.0) * gt
        gb = 28.0 + (42.0 - 28.0) * gt
        # forest: dark green canopy
        ft = 0.35 + 0.45 * land_h
        fr = 10.0 + (22.0 - 10.0) * ft
        fg = 70.0 + (105.0 - 70.0) * ft
        fb = 18.0 + (32.0 - 18.0) * ft
        rt = _n_smooth_edge(land_h, 0.45, 0.85)
        rr = 90.0 + (160.0 - 90.0) * rt
        rg = 85.0 + (155.0 - 85.0) * rt
        rb = 75.0 + (145.0 - 75.0) * rt
        rm = _n_smooth_edge(moist, 0.45, 0.75) * 0.3
        rr = rr + (70.0 - rr) * rm
        rg = rg + (95.0 - rg) * rm
        rb = rb + (60.0 - rb) * rm
        st = _n_smooth_edge(land_h, 0.55, 0.90)
        sr = 200.0 + (235.0 - 200.0) * st
        sg = 210.0 + (240.0 - 210.0) * st
        sb = 220.0 + (245.0 - 220.0) * st
        # Sharper dry↔wet so sand and green don't muddy together
        t_dry = 1.0 - _n_smooth_edge(moist, 0.28, 0.40)
        t_wet = _n_smooth_edge(moist, 0.52, 0.68)
        r = gr + (dr - gr) * t_dry
        g = gg + (dg - gg) * t_dry
        b = gb + (db - gb) * t_dry
        r = r + (fr - r) * t_wet
        g = g + (fg - g) * t_wet
        b = b + (fb - b) * t_wet
        rk = _n_smooth_edge(land_h, 0.48, 0.68)
        r = r + (rr - r) * rk
        g = g + (rg - g) * rk
        b = b + (rb - b) * rk
        ice_lat = _n_smooth_edge(abs(lat_norm), 2.0 / 3.0, 2.0 / 3.0 + 0.06)
        ice = ice_lat * (0.55 + 0.45 * _n_smooth_edge(land_h, 0.15, 0.70))
        r = r + (sr - r) * ice
        g = g + (sg - g) * ice
        b = b + (sb - b) * ice
        # Narrower beach so sand doesn't wash out the coast green/blue split
        t_beach = (1.0 - _n_smooth_edge(elev, SEA_LEVEL, SEA_LEVEL + 0.022)) * (1.0 - ice) * 0.72
        r = r + (210.0 - r) * t_beach
        g = g + (175.0 - g) * t_beach
        b = b + (95.0 - b) * t_beach
        if lod >= 1:
            river_amt = _is_river_n(wx, wy, elev, moist, seed)
            r = r + (18.0 - r) * river_amt
            g = g + (70.0 - g) * river_amt
            b = b + (130.0 - b) * river_amt

    # Slightly stronger relief for biome readability on 64×32
    ndot = 0.55 + 0.48 * (mountain * 0.55 + (d - 0.5) * -0.45)
    if ndot < 0.32:
        ndot = 0.32
    elif ndot > 1.15:
        ndot = 1.15
    r = r * ndot
    g = g * ndot
    b = b * ndot
    # No atmospheric haze — keep biome colors crisp on the LED panel
    return r, g, b, elev, river_amt, land


def _smooth_edge(v, a, b):
    """0..1 smoothstep across [a,b]."""
    if b <= a:
        return 1.0 if v >= a else 0.0
    return _smoothstep((v - a) / (b - a))


def _warm_planet_numba(StopEvent=None):
    """
    Compile or load cached Numba kernels for surface sampling.
    First cold compile can take a few seconds; later launches load from disk.
    """
    global _numba_warmed
    if _numba_warmed:
        return
    if not HAS_NUMBA:
        print("[PlanetBlast] Numba not available — pure Python surface path")
        _numba_warmed = True
        return
    try:
        if StopEvent is not None and StopEvent.is_set():
            return
    except Exception:
        pass
    print(
        "[PlanetBlast] Warming Numba surface kernels (cache=True)...",
        flush=True,
    )
    t0 = time.time()
    # Touch every cached kernel (lod 0/1/2)
    _hash2(1, 2, 3)
    _value_noise(0.25, 0.75, 42)
    _fbm(0.1, 0.2, 7, 2, 2.05, 0.5)
    _fbm_fast(0.1, 0.2, 7, 2)
    _elev_raw_n(1000.0, -500.0, 42, 0)
    _elev_raw_n(1000.0, -500.0, 42, 2)
    _is_river_n(1000.0, -500.0, 0.7, 0.5, 42)
    _sample_biome_n(1000.0, -500.0, 42, 0)
    _sample_biome_n(1000.0, -500.0, 42, 1)
    _sample_biome_n(1000.0, -500.0, 42, 2)
    _numba_warmed = True
    print(
        f"[PlanetBlast] Surface kernels ready ({time.time() - t0:.1f}s; "
        f"cached for next launch).",
        flush=True,
    )


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


# 50 alien species (readable English shape)
_SPECIES_NAMES = (
    "the Vorthari", "the Kelion Hives", "the Nyxari Collective",
    "the Ashmeer Clans", "the Xelith Swarm", "House Mirox",
    "the Thalos Dominion", "the Zorani Choir", "the Free Saelith",
    "the Ornavi Mandate", "the Dravak Hordes", "the Lunari Weavers",
    "the Pharosi Guild", "the Rynax Brethren", "the Veskari League",
    "the Helion Spinners", "the Iskari Lattice", "the Praxari Court",
    "the Qantor Blades", "the Brynnos Kin", "the Corvexi",
    "the Denebi Drift", "the Eryndari", "the Fomari Reef",
    "the Ganymari", "the Hyperion Veil", "the Iridonites",
    "the Jotunari", "the Krynnari", "the Lothorii",
    "the Manticore Host", "the Nexari Cabal", "the Oberoni",
    "the Phaetoni", "the Quorosi", "the Rigellian March",
    "the Solari Choir", "the Titanos Guard", "the Umbri Shade",
    "the Vortexi", "the Weylandi", "the Xandari",
    "the Ymirfolk", "the Zephyrosi", "the Andarosi",
    "the Boreali", "the Cygnari", "the Delphosi",
    "the Erebim", "the Krellari Assembly",
)

# 50 crimes against the Human Empire (serious + silly)
_EMPIRE_CRIMES = (
    # Serious
    "TREASON AGAINST THE HUMAN EMPIRE",
    "HARBORING ENEMY FLEETS",
    "ATTACK ON IMPERIAL COLONIES",
    "BLOCKADE OF TRADE LANES",
    "THEFT OF IMPERIAL SHIPS",
    "SABOTAGE OF JUMP GATES",
    "ASSASSINATION OF IMPERIAL ENVOYS",
    "GENOCIDE OF HUMAN OUTPOSTS",
    "ILLEGAL WEAPONS RESEARCH",
    "BIOWEAPON DEPLOYMENT",
    "SLAVERY OF HUMAN CITIZENS",
    "PIRACY IN EMPIRE SPACE",
    "DESECRATION OF HUMAN TOMBS",
    "BREACH OF THE CEASEFIRE",
    "SPYING ON IMPERIAL COMMAND",
    "FALSIFYING PEACE TREATIES",
    "RAIDING SUPPLY CONVOYS",
    "COLLUSION WITH OUTER REBELS",
    "DESTRUCTION OF STARPORTS",
    "POISONING OF COLONY WORLDS",
    "KIDNAPPING IMPERIAL OFFICERS",
    "REFUSAL OF IMPERIAL TAX",
    "SHELTERING WAR CRIMINALS",
    "ORBITAL BOMBARDMENT OF CIVILIANS",
    "THEFT OF TERRAFORMING SEEDS",
    "HACKING THE IMPERIAL NET",
    "SMUGGLING FORBIDDEN TECH",
    "OPEN REBELLION IN SECTOR 7",
    "MURDER OF A GOVERNOR",
    "INVASION OF HUMAN SPACE",
    # Silly
    "UNPAID PARKING TICKETS",
    "LEAVING THE SEAT UP",
    "LEAVING BAD TIPS",
    "RETURNING LIBRARY BOOKS LATE",
    "CUTTING IN LINE AT CUSTOMS",
    "SPOILING THE SEASON FINALE",
    "STEALING OFFICE SNACKS",
    "PLAYING MUSIC TOO LOUD AT NIGHT",
    "USING ALL THE HOT WATER",
    "FORGETTING TO RSVP",
    "DOUBLE DIPPING THE DIP",
    "REPLYING ALL TO EMPIRE MAIL",
    "TAKING THE LAST DOUGHNUT",
    "MISPRONOUNCING THE EMPEROR",
    "JAYWALKING ON ORBITAL DECKS",
    "LEAVING DISHES IN THE SINK",
    "HOARDING THE GOOD CHAIRS",
    "SKIPPING THE GROUP PHOTO",
    "PUTTING EMPTY CARTONS BACK",
    "WEARING BOOTS ON THE COUCH",
)


def _generate_planet_name(seed):
    """Pick from 50 fixed star-system style names (e.g. Vulcanis III)."""
    rng = random.Random(int(seed) ^ 0x51A7E7)
    return rng.choice(_PLANET_NAMES)


def _generate_species_name(rng):
    """Pick from 50 fixed alien species names."""
    return rng.choice(_SPECIES_NAMES)


def _build_empire_news_feed(count=120):
    """
    Build a large pool of empire news/chatter lines for the space-clock ticker.
    Deterministic seed so the pool is stable; callers may shuffle a copy.
    Guarantees at least `count` items (default 120).
    """
    rng = random.Random(0xE1A5_FEED)
    planets = list(_PLANET_NAMES)
    species = [s.replace("the ", "").replace("House ", "") for s in _SPECIES_NAMES]
    # City-style names from onset/core/coda
    cities = []
    for _ in range(80):
        cities.append(
            rng.choice(_NAME_ONSET) + rng.choice(_NAME_CORE) + rng.choice(_NAME_CODA)
        )
    fleets = (
        "3RD FLEET", "7TH ARMADA", "TASK FORCE VYRN", "STRIKE GROUP OMEGA",
        "BLACK LANTERN WING", "RED SUN FLOTILLA", "GHOST WING", "SPEAR OF SOL",
    )
    sectors = (
        "SECTOR 7", "THE OUTER RIM", "THE VEIL MARCH", "SPINWARD REACH",
        "THE DEAD MARCH", "ORION SPUR", "THE ASH LANE", "GRID 19",
    )
    templates = (
        "NEWS: {sp} seize orbital docks over {pl}",
        "RUMOR: war drums on {pl} — {sp} mobilizing",
        "MILITARY: {fl} claims victory near {pl}",
        "EMPIRE: new tariff on goods from {pl}",
        "FUNNY: {sp} fine citizens for smiling after dark on {pl}",
        "RUMOR: ghost freighter spotted leaving {ci}",
        "CONQUEST: {sp} raise banner over {ci}",
        "NEWS: ceasefire talks collapse on {pl}",
        "ALERT: pirate activity spikes in {sec}",
        "MILITARY: {fl} en route to {pl}",
        "RUMOR: {sp} hiding a jump gate under {ci}",
        "NEWS: harvest festival cancelled on {pl} — again",
        "FUNNY: {sp} declare war on empty parking orbits",
        "EMPIRE: medal ceremony delayed; medals lost on {pl}",
        "CONQUEST: last holdouts in {ci} request snacks then surrender",
        "RUMOR: the Emperor's cat is missing — {sec} on lockdown",
        "NEWS: {sp} broadcast apology, then invade {pl}",
        "MILITARY: orbital yards at {pl} working triple shifts",
        "FUNNY: {ci} elects a potted plant as mayor",
        "ALERT: unauthorized parade of mechs through {ci}",
        "RUMOR: ancient weapon unearthed beneath {pl}",
        "NEWS: {sp} ban humming in public on {pl}",
        "MILITARY: training exercise 'accidentally' levels {ci}",
        "EMPIRE: tax auditors arrive on {pl} — locals flee",
        "CONQUEST: {fl} plants flag, immediately asks for directions",
        "RUMOR: {sp} negotiating with space whales near {sec}",
        "NEWS: spice prices crash after glut from {pl}",
        "FUNNY: duel scheduled between admirals over last pastry on {pl}",
        "ALERT: blackout across {ci} — blame assigned to {sp}",
        "MILITARY: siege of {pl} enters day {n}",
        "RUMOR: deserters from {fl} opening a cafe in {ci}",
        "NEWS: {sp} claim {pl} was 'always theirs'",
        "EMPIRE: recruitment drive hits record on {pl}",
        "FUNNY: {sp} issue formal complaint about gravity on {pl}",
        "CONQUEST: {ci} falls before breakfast",
        "ALERT: smugglers using tourist shuttles in {sec}",
        "RUMOR: secret base under the ice of {pl}",
        "NEWS: {sp} host peace concert, sell tickets to invasion",
        "MILITARY: {fl} resupply complete at {pl}",
        "FUNNY: local weather on {pl} declared 'personally rude'",
        "EMPIRE: ban on novelty hats reaches {ci}",
        "RUMOR: {sp} invent faster-than-light gossip",
        "NEWS: refugee fleets from {pl} request parking",
        "CONQUEST: {sp} rename {ci} for the third time this year",
        "ALERT: unknown signature shadowing {fl}",
        "MILITARY: live-fire exercise authorized near {pl}",
        "FUNNY: {ci} runs out of coffee — martial law considered",
        "RUMOR: the maps of {sec} are lying on purpose",
        "NEWS: {sp} demand apology for a meme about {pl}",
        "EMPIRE: holiday declared after minor win at {pl}",
        "CONQUEST: last tower in {ci} flies a white dish towel",
        "MILITARY: troop transports leave for {pl} at dawn",
        "RUMOR: {sp} stockpiling rubber ducks for unknown strategy",
        "NEWS: trade route reopened through {sec}",
        "FUNNY: senator confuses {pl} with a dessert",
        "ALERT: civil unrest in {ci} after power rate hike",
        "EMPIRE: new anthem leaked — mostly bass",
        "RUMOR: twin planets both claim to be the real {pl}",
        "MILITARY: ace pilot from {pl} scores kill number {n}",
        "NEWS: {sp} open embassy, install turrets first",
        "CONQUEST: {fl} accepts surrender, loses paperwork",
        "FUNNY: {ci} tourism board markets 'scenic craters'",
        "RUMOR: ancient AI still arguing in a basement on {pl}",
        "NEWS: black market jump crystals flood {sec}",
        "MILITARY: drills cancelled — too realistic last time",
        "ALERT: solar flare scrambles comms near {pl}",
        "EMPIRE: census on {pl} finds more pets than people",
        "RUMOR: {sp} planning a surprise party that is not a party",
        "CONQUEST: high ground secured above {ci}",
        "FUNNY: {pl} weather report: 'spicy'",
        "NEWS: peace treaty signed in edible ink on {pl}",
        "MILITARY: {fl} requests more socks for the troops",
        "RUMOR: ghost parade marches through {ci} every third night",
        "ALERT: counterfeit medals circulating in {sec}",
        "EMPIRE: overtime banned, then immediately required on {pl}",
        "NEWS: {sp} invent a holiday to avoid battle",
        "CONQUEST: orbital control of {pl} contested for hour {n}",
        "FUNNY: lost tourist asks {fl} for directions to {ci}",
        "RUMOR: the Emperor's speech was written by a toaster",
        "MILITARY: munitions factory on {pl} exceeds quota",
        "NEWS: {sp} and rivals both claim to have invented tea",
        "ALERT: derelict hulk drifts toward {pl}",
        "EMPIRE: parade route through {ci} still on fire",
        "RUMOR: lucky charm of {fl} is a single sock",
        "CONQUEST: street-by-street push into old {ci}",
        "FUNNY: {sp} outlaw bad puns — enforcement ongoing",
        "NEWS: archive heist on {pl} steals only memes",
        "MILITARY: silent running drill ends with someone sneezing",
        "RUMOR: double agent living as a baker in {ci}",
        "ALERT: supply crate full of rubber chickens for {fl}",
        "EMPIRE: new tax on looking suspicious in {sec}",
        "NEWS: {sp} host open house on conquered {pl}",
        "FUNNY: {ci} mayor debates a hologram and loses",
        "CONQUEST: flag raised, immediately stolen as souvenir",
        "MILITARY: recon drones map every cafe on {pl}",
        "RUMOR: the war will end when someone finds the remote",
        "NEWS: ceasefire broken by competitive cooking show on {pl}",
        "ALERT: unknown fleet staging in dark of {sec}",
        "EMPIRE: victory declared early to improve morale stats",
        "FUNNY: {sp} request better enemy uniforms for contrast",
        "MILITARY: boarding action succeeds; finds only snacks",
        "RUMOR: {ci} built on a sleeping leviathan",
        "NEWS: trade guilds strike until {pl} pays tab",
        "CONQUEST: {fl} holds parade, then asks who won",
    )
    out = []
    # Ensure we generate well past the minimum
    target = max(100, int(count))
    guard = 0
    while len(out) < target and guard < target * 4:
        guard += 1
        tmpl = rng.choice(templates)
        line = tmpl.format(
            sp=rng.choice(species).upper(),
            pl=rng.choice(planets).upper(),
            ci=rng.choice(cities).upper(),
            fl=rng.choice(fleets),
            sec=rng.choice(sectors),
            n=rng.randint(2, 99),
        )
        if line not in out:
            out.append(line)
    # Pad if templates collided
    while len(out) < target:
        out.append(
            f"NEWS: update {len(out)+1} from "
            f"{rng.choice(planets).upper()} — status nominal"
        )
    return out


# Built once at import — stable pool of empire news for the space-clock marquee
_EMPIRE_NEWS_FEED = _build_empire_news_feed(120)


def _generate_world_dossier(seed, world_name):
    """
    Species + single empire crime for approach briefing.
    Returns (species_str, list_of_crimes with one entry).
    """
    rng = random.Random(int(seed) ^ 0xC41BE1)
    species = _generate_species_name(rng)
    crime = rng.choice(_EMPIRE_CRIMES)
    return species, [crime]


class PlanetMap(object):
    """
    One consistent planetary surface: terrain, rivers, cities.
    (No roads/bridges/rails — invisible at panel scale, skipped for speed.)
    Used for both globe zoom and surface flight.
    """

    def __init__(self, seed=None):
        self.seed = int(seed if seed is not None else random.randint(1, 1_000_000))
        # World radius: log-uniform dwarf → near-baseline (never ≥ 1.0×)
        rng_size = random.Random(self.seed ^ 0x5121)
        log_lo = math.log(PLANET_SIZE_MIN)
        log_hi = math.log(PLANET_SIZE_MAX)
        self.size_scale = math.exp(rng_size.uniform(log_lo, log_hi))
        # Safety: baseline is the hard ceiling
        if self.size_scale >= 1.0:
            self.size_scale = PLANET_SIZE_MAX
        self.R = PLANET_R * self.size_scale
        # Classes relative to baseline=largest (all worlds are sub-baseline)
        if self.size_scale < 0.35:
            self.size_class = "dwarf"
        elif self.size_scale < 0.55:
            self.size_class = "small"
        elif self.size_scale < 0.75:
            self.size_class = "medium"
        elif self.size_scale < 0.90:
            self.size_class = "large"
        else:
            self.size_class = "massive"  # near-baseline, still < 1.0×
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
        self.species, self.crimes = _generate_world_dossier(self.seed, self.name)
        self.cities = []     # dict x,y,size (1..5), name-ish
        self.city_grid = {}  # (cx,cy) -> [city indices]
        # Shared surface paint: cell key → (r, g, b, glow). Cities baked at gen;
        # bombs and wildfire permanently overwrite cells (no separate ember layer).
        self.city_paint = {}
        self.fire_scorch = set()   # keys already burned (for spread frontier only)
        self.fire_front = []      # edge keys that may expand into green
        self._fire_tick_t = 0.0
        # Live wildfire pace (can accelerate if planet refuses to surrender)
        self.fire_tick_sec = float(FIRE_TICK_SEC)
        self.fire_spread_per_tick = int(FIRE_SPREAD_PER_TICK)
        self.fire_raged = False
        self._build_civilization()
        self._bake_all_cities()
        print(
            f"[PlanetBlast] World {self.name}  size={self.size_class} "
            f"({self.size_scale:.2f}x)  species={self.species}  "
            f"seed={self.seed}  cities={len(self.cities)}  "
            f"city_cells={len(self.city_paint)}  "
            f"crime={self.crimes[0] if self.crimes else 'none'}"
        )

    @staticmethod
    def _norm(x, y, z):
        m = math.sqrt(x * x + y * y + z * z) or 1.0
        return (x / m, y / m, z / m)

    def elev_raw(self, wx, wy, lod=2):
        """
        Elevation + continent/detail/mountain components (Numba when available).
        lod 0: 1 octave continent only (far overview)
        lod 1–2: 2+1+1 octaves (readable on 64×32 without 3×2×2 cost)
        """
        return _elev_raw_n(float(wx), float(wy), int(self.seed), int(lod))

    def is_river(self, wx, wy, elev, moist):
        return _is_river_n(
            float(wx), float(wy), float(elev), float(moist), int(self.seed),
        )

    def is_land(self, wx, wy):
        elev, _, _, _ = self.elev_raw(wx, wy)
        return elev >= SEA_LEVEL + 0.02

    def world_from_sphere(self, nx, ny, nz):
        """Map unit sphere normal → world meters (equirectangular unwrap)."""
        lon = math.atan2(nx, nz)
        lat = math.asin(_clamp(ny, -1.0, 1.0))
        return lon * self.R, lat * self.R

    def sphere_from_world(self, wx, wy):
        lon = wx / self.R
        lat = _clamp(wy / self.R, -math.pi * 0.5 + 0.01, math.pi * 0.5 - 0.01)
        cl = math.cos(lat)
        return (math.sin(lon) * cl, math.sin(lat), math.cos(lon) * cl)

    def day_factor_flat(self, wx, wy):
        """Day amount on the unwrapped map from sun longitude (soft terminator)."""
        lon = wx / self.R
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
        R = self.R
        for _ in range(80):
            wx = random.uniform(-math.pi * R * 0.9, math.pi * R * 0.9)
            wy = random.uniform(-R * 0.55, R * 0.55)
            elev, c, _, _ = self.elev_raw(wx, wy)
            if elev > SEA_LEVEL + 0.04 and elev < 0.75 and abs(wy) < R * 0.65:
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
        city_lon = float(city["x"]) / self.R
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
        city_lon = float(city["x"]) / self.R
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
            self.fire_scorch.clear()
            self.fire_front = []
            self._bake_all_cities()
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
        # Random city count per planet (10–50 hard max)
        target_n = rng.randint(CITY_COUNT_MIN, CITY_COUNT_MAX)
        self.city_count = target_n
        dens = (target_n - CITY_COUNT_MIN) / max(
            1.0, float(CITY_COUNT_MAX - CITY_COUNT_MIN),
        )
        space_scale = 1.0 - 0.35 * dens
        max_attempts = max(600, target_n * 30)
        attempts = 0
        R = self.R
        while len(self.cities) < target_n and attempts < max_attempts:
            attempts += 1
            wx = rng.uniform(-math.pi * R, math.pi * R)
            wy = rng.uniform(-R * 0.85, R * 0.85)
            elev, _, _, _ = self.elev_raw(wx, wy)
            if elev < SEA_LEVEL + 0.03 or elev > 0.78:
                continue
            moist = _fbm(
                wx * DETAIL_SCALE * 0.7, wy * DETAIL_SCALE * 0.7,
                self.seed + 31, 2, 2.05, 0.5,
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
            ok = True
            min_d = (35_000 + size * 22_000) * space_scale
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
        # Guarantee a few large cities for zoom/targets (without exceeding target_n)
        want_large = min(4, max(1, target_n // 5))
        large_min_d = 60_000 * space_scale
        while (
            sum(1 for c in self.cities if c["size"] >= 4) < want_large
            and len(self.cities) < target_n
            and attempts < max_attempts + 400
        ):
            attempts += 1
            wx = rng.uniform(-math.pi * R * 0.8, math.pi * R * 0.8)
            wy = rng.uniform(-R * 0.5, R * 0.5)
            if not self.is_land(wx, wy):
                continue
            size = 5 if rng.random() < 0.4 else 4
            ok = all(
                math.hypot(c["x"] - wx, c["y"] - wy) > large_min_d
                for c in self.cities
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
        # Hard cap
        if len(self.cities) > CITY_COUNT_MAX:
            self.cities = self.cities[:CITY_COUNT_MAX]
        _assign_city_names(self.cities, self.seed)
        # Spatial hash cities only (no road network)
        self.city_grid = {}
        for i, c in enumerate(self.cities):
            key = self._cell(c["x"], c["y"])
            self.city_grid.setdefault(key, []).append(i)

    def _bake_all_cities(self):
        """Stamp every city into city_paint once — sample() only looks up cells."""
        self.city_paint = {}
        for city in self.cities:
            self._bake_city(city)

    def _bake_city(self, city):
        """
        Rasterize one city disc into the permanent paint map.
        Damage later overwrites these cells; bombs never re-run disc math.
        """
        cx = float(city["x"])
        cy = float(city["y"])
        size = int(city.get("size", 3))
        radius = 12_000.0 + size * 14_000.0
        cell = FIRE_CELL
        ix0 = int(math.floor((cx - radius * 1.05) / cell))
        ix1 = int(math.floor((cx + radius * 1.05) / cell))
        iy0 = int(math.floor((cy - radius * 1.05) / cell))
        iy1 = int(math.floor((cy + radius * 1.05) / cell))
        for iy in range(iy0, iy1 + 1):
            for ix in range(ix0, ix1 + 1):
                wx = (ix + 0.5) * cell
                wy = (iy + 0.5) * cell
                dx = wx - cx
                dy = wy - cy
                dist2 = dx * dx + dy * dy
                r_lim = radius * 1.05
                if dist2 > r_lim * r_lim:
                    continue
                dist = math.sqrt(dist2)
                disc = 1.0 - _smooth_edge(dist, radius * 0.35, radius)
                core = 1.0 - _smooth_edge(dist, radius * 0.08, radius * 0.42)
                if disc < 0.02:
                    continue
                # Sample underlying biome once so city sits on real terrain
                (br, bg, bb), elev, river_amt, land = self.sample_biome(
                    wx, wy, lod=1,
                )
                r, g, b = float(br), float(bg), float(bb)
                # Urban mass
                k = disc * 0.88
                r = r + (CITY_DAY[0] - r) * k
                g = g + (CITY_DAY[1] - g) * k
                b = b + (CITY_DAY[2] - b) * k
                if core > 0.02:
                    ck = core * 0.75
                    r = r + (CITY_DAY_CORE[0] - r) * ck
                    g = g + (CITY_DAY_CORE[1] - g) * ck
                    b = b + (CITY_DAY_CORE[2] - b) * ck
                # Building blocks / parks (stable hash — baked, never re-rolled)
                if dist < radius * 0.92:
                    bcell = 11_000.0
                    rel_x = (wx - cx) / bcell
                    rel_y = (wy - cy) / bcell
                    gx = int(math.floor(rel_x))
                    gy = int(math.floor(rel_y))
                    fx = rel_x - gx
                    fy = rel_y - gy
                    edge = min(fx, 1.0 - fx, fy, 1.0 - fy) * 2.0
                    edge = _clamp(edge, 0.0, 1.0)
                    edge = edge * edge * (3.0 - 2.0 * edge)
                    h = _hash2(gx, gy, 77 + size * 3)
                    if h > 0.34 and edge > 0.05:
                        shade_b = 0.55 + 0.45 * h
                        br2 = 100 + 55 * shade_b
                        bg2 = 98 + 50 * shade_b
                        bb2 = 95 + 48 * shade_b
                        blk = (0.40 + 0.30 * h) * max(disc, 0.25) * edge
                        r = r + (br2 - r) * blk
                        g = g + (bg2 - g) * blk
                        b = b + (bb2 - b) * blk
                    elif h < 0.16 and disc > 0.2 and edge > 0.08:
                        pk = 0.28 * disc * edge
                        r = r + (55 - r) * pk
                        g = g + (95 - g) * pk
                        b = b + (50 - b) * pk
                # Night-light weight (applied at sample time from day_factor)
                glow = 1.0 - _smooth_edge(dist, radius * 0.12, radius * 1.2)
                glow = glow * glow * (0.55 + 0.22 * size)
                if dist < radius * 0.35 and size >= 3:
                    glow *= 1.25
                key = (ix, iy)
                # Prefer denser overwrite if cells overlap (rare)
                prev = self.city_paint.get(key)
                if prev is not None and prev[3] >= glow and disc < 0.5:
                    continue
                self.city_paint[key] = (
                    int(_clamp(r, 0, 255)),
                    int(_clamp(g, 0, 255)),
                    int(_clamp(b, 0, 255)),
                    float(_clamp(glow, 0.0, 2.5)),
                )

    def stamp_damage_patch(self, wx, wy, radius_m, strength=1.0):
        """
        Permanently overwrite baked city paint with rubble around an impact.
        Also ignites red embers that crawl into surrounding green.
        """
        strength = _clamp(float(strength), 0.0, 1.0)
        # Compact crater + sparse ember seeds (smaller diameter, fewer cells)
        radius_m = max(FIRE_CELL * 0.45, float(radius_m) * 0.65)
        cell = FIRE_CELL
        ix0 = int(math.floor((wx - radius_m) / cell))
        ix1 = int(math.floor((wx + radius_m) / cell))
        iy0 = int(math.floor((wy - radius_m) / cell))
        iy1 = int(math.floor((wy + radius_m) / cell))
        for iy in range(iy0, iy1 + 1):
            for ix in range(ix0, ix1 + 1):
                cx = (ix + 0.5) * cell
                cy = (iy + 0.5) * cell
                d = math.hypot(cx - wx, cy - wy)
                if d > radius_m:
                    continue
                fall = 1.0 - d / max(1.0, radius_m)
                fall = fall * fall
                key = (ix, iy)
                # Rubble / crater overwrite of baked city cells
                if key in self.city_paint or fall > 0.40:
                    ash_k = 0.55 + 0.45 * strength * fall
                    rr = int(RUBBLE_RGB[0] * (0.75 + 0.25 * (1.0 - strength)))
                    gg = int(RUBBLE_RGB[1] * (0.70 + 0.20 * (1.0 - strength)))
                    bb = int(RUBBLE_RGB[2] * 0.75)
                    # Hot flecks only near core, and only on some cells
                    if fall > 0.55 and strength > 0.40 and _hash2(ix, iy, 91) > 0.55:
                        er, eg, eb = self._fire_paint_rgb(ix, iy, hot=True)
                        mix = 0.30 + 0.40 * strength * fall
                        rr = int(rr + (er - rr) * mix)
                        gg = int(gg + (eg - gg) * mix)
                        bb = int(bb + (eb - bb) * mix)
                    if key in self.city_paint:
                        pr, pg, pb, glow = self.city_paint[key]
                        k = ash_k * 0.92
                        self.city_paint[key] = (
                            int(pr + (rr - pr) * k),
                            int(pg + (gg - pg) * k),
                            int(pb + (bb - pb) * k),
                            float(glow) * (1.0 - 0.85 * strength * fall),
                        )
                    else:
                        self.city_paint[key] = (rr, gg, bb, 0.0)
                # Fewer frontier seeds — denser core only
                if fall > 0.40 and _hash2(ix, iy, 17) > 0.45:
                    self._ignite_cell(key, force=True)

    def stamp_city_damage(self, city):
        """
        Re-stamp a city disc from current damage: intact bake is already done;
        raise damage by overwriting more of the disc with rubble / embers.
        """
        dmg = _clamp(float(city.get("damage", 0.0)), 0.0, 1.0)
        if dmg < 0.04 and not city.get("obliterated"):
            return
        cx = float(city["x"])
        cy = float(city["y"])
        cr = 12_000.0 + float(city.get("size", 3)) * 14_000.0
        # Compact damage footprint (not the full urban disc every time)
        if city.get("obliterated") or dmg >= 0.98:
            rad = cr * 0.55
            strength = 1.0
        else:
            rad = cr * (0.18 + 0.35 * dmg)
            strength = 0.45 + 0.55 * dmg
        self.stamp_damage_patch(cx, cy, rad, strength=strength)

    def _nearby_cities(self, wx, wy, radius_cells=2):
        # Wider stencil — megacities span multiple cells (radius 2 default)
        cx, cy = self._cell(wx, wy)
        seen = set()
        out = []
        r = max(0, int(radius_cells))
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                for i in self.city_grid.get((cx + dx, cy + dy), ()):
                    if i not in seen:
                        seen.add(i)
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
            self.seed + 31, 2, 2.05, 0.5,
        )
        lat_norm = _clamp(wy / (self.R * (math.pi * 0.5)), -1.0, 1.0)
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

    @staticmethod
    def _fire_paint_rgb(ix, iy, hot=True):
        """Varying ember / ash color for a map cell (stable hash, no animation)."""
        h = _hash2(ix, iy, 61 if hot else 19)
        n = len(_FIRE_PAINT_COLORS)
        if hot:
            # Bias toward brighter reds/oranges
            idx = int(h * (n * 0.65)) % n
        else:
            idx = int(h * n) % n
        base = _FIRE_PAINT_COLORS[idx]
        # Slight per-cell variance so the burn field isn't uniform
        j = 0.85 + 0.30 * _hash2(ix, iy, 88)
        return (
            int(_clamp(base[0] * j, 0, 255)),
            int(_clamp(base[1] * j, 0, 255)),
            int(_clamp(base[2] * j, 0, 255)),
        )

    def _paint_fire_cell(self, key, hot=True):
        """Stamp one fire/ember color onto the shared map paint (city_paint)."""
        ix, iy = key
        rr, gg, bb = self._fire_paint_rgb(ix, iy, hot=hot)
        prev = self.city_paint.get(key)
        if prev is not None:
            pr, pg, pb, glow = prev
            # Overwrite urban/terrain with burn color (keep a little of prior)
            k = 0.82 if hot else 0.90
            self.city_paint[key] = (
                int(pr + (rr - pr) * k),
                int(pg + (gg - pg) * k),
                int(pb + (bb - pb) * k),
                float(glow) * 0.15,
            )
        else:
            self.city_paint[key] = (rr, gg, bb, 0.0)

    def _ignite_cell(self, key, force=False):
        """
        Paint fire/ember color onto the map and track frontier for slow spread.
        force=True: crater/city cells (not green). Else only green fuel.
        """
        if len(self.fire_scorch) >= FIRE_MAX_CELLS and key not in self.fire_scorch:
            return False
        wx, wy = self._fire_key_center(key)
        if key not in self.fire_scorch:
            if not force and not self.is_green_fuel(wx, wy):
                return False
            self.fire_scorch.add(key)
            self.fire_front.append(key)
            if len(self.fire_front) > 280:
                self.fire_front = self.fire_front[-160:]
            # Draw burn onto the map immediately (varying colors)
            self._paint_fire_cell(key, hot=True)
            return True
        return False

    def seed_city_wildfire(self, city):
        """Sparse, tight burn ring — fewer embers, smaller diameter."""
        dmg = _clamp(float(city.get("damage", 0.0)), 0.0, 1.0)
        if not city.get("obliterated") and dmg < FIRE_SEED_DMG:
            return
        cr = (12_000.0 + city["size"] * 14_000.0) * FIRE_CITY_RING_SCALE
        ring0 = cr * 0.35
        ring1 = cr * (0.70 + 0.25 * dmg)
        # Single outer ring only (was 3 rings × many steps)
        steps = max(4, int((ring1 * 0.9) / FIRE_CELL))
        cx, cy = float(city["x"]), float(city["y"])
        for i in range(steps):
            ang = (i / float(steps)) * math.pi * 2.0
            # Skip every other sample for a sparser ring
            if i % 2 == 1:
                continue
            self._ignite_cell(self._fire_key(
                cx + math.cos(ang) * ring0,
                cy + math.sin(ang) * ring0,
            ), force=True)
            self._ignite_cell(self._fire_key(
                cx + math.cos(ang) * ring1,
                cy + math.sin(ang) * ring1,
            ), force=False)
        # A couple of random green sparks only
        for _ in range(1 + int(dmg * 1.5)):
            ang = random.uniform(0, math.pi * 2)
            rad = random.uniform(ring0, ring1 * 1.05)
            self._ignite_cell(self._fire_key(
                cx + math.cos(ang) * rad,
                cy + math.sin(ang) * rad,
            ), force=False)

    def seed_impact_wildfire(self, wx, wy, strength=1.0):
        """Tiny impact seed — single cell core, optional 1-cell rim."""
        r_cells = int(FIRE_IMPACT_R_CELLS)
        if strength > 0.75:
            r_cells = min(r_cells + 1, 2)
        ix, iy = self._fire_key(wx, wy)
        for dy in range(-r_cells, r_cells + 1):
            for dx in range(-r_cells, r_cells + 1):
                if dx * dx + dy * dy > r_cells * r_cells:
                    continue
                # Core always; rim only on some cells
                force = (dx == 0 and dy == 0)
                if not force and _hash2(ix + dx, iy + dy, 33) < 0.45:
                    continue
                self._ignite_cell((ix + dx, iy + dy), force=force)

    def accelerate_wildfire(self):
        """
        Planet refused to surrender after engagement quota — fires spread faster.
        Idempotent: only ramps once per world.
        """
        if self.fire_raged:
            return
        self.fire_raged = True
        self.fire_tick_sec = float(FIRE_RAGE_TICK_SEC)
        self.fire_spread_per_tick = int(FIRE_RAGE_SPREAD_PER_TICK)
        # Nudge next tick sooner so the rage is felt quickly
        self._fire_tick_t = max(float(self._fire_tick_t), self.fire_tick_sec * 0.65)
        print(
            f"[PlanetBlast] Wildfire RAGE on {self.name}: "
            f"tick {FIRE_TICK_SEC:.0f}s→{self.fire_tick_sec:.1f}s  "
            f"spread {FIRE_SPREAD_PER_TICK}→{self.fire_spread_per_tick}/tick"
        )

    def update_wildfire(self, dt):
        """
        Periodic paint of new fire cells onto the map along the green edge.
        Pace uses fire_tick_sec / fire_spread_per_tick (can accelerate in rage).
        """
        if dt <= 0 or not self.fire_front:
            return
        tick = float(getattr(self, "fire_tick_sec", FIRE_TICK_SEC) or FIRE_TICK_SEC)
        spread_n = int(getattr(self, "fire_spread_per_tick", FIRE_SPREAD_PER_TICK)
                       or FIRE_SPREAD_PER_TICK)
        self._fire_tick_t += dt
        if self._fire_tick_t < tick:
            return
        self._fire_tick_t = 0.0

        front = self.fire_front
        # Sample fewer frontier cells → fewer new embers overall
        pick_n = min(18, len(front))
        if len(front) > pick_n:
            picks = [front[random.randrange(len(front))] for _ in range(pick_n)]
        else:
            picks = list(front)
            random.shuffle(picks)

        new_front = []
        painted = 0
        # Cardinal only (no diagonals) — slower radial growth / smaller patches
        nbrs_all = ((1, 0), (-1, 0), (0, 1), (0, -1))
        for key in picks:
            if painted >= spread_n:
                new_front.append(key)
                continue
            ix, iy = key
            order = list(nbrs_all)
            random.shuffle(order)
            expanded = False
            for dx, dy in order:
                nkey = (ix + dx, iy + dy)
                if self._ignite_cell(nkey, force=False):
                    new_front.append(nkey)
                    painted += 1
                    expanded = True
                    break
            if not expanded and random.random() < 0.50:
                continue
            new_front.append(key)

        keep = [k for k in front[-80:] if k in self.fire_scorch]
        self.fire_front = (keep + new_front)[-220:]

    def is_scorched(self, wx, wy):
        """True if this world point is permanent wildfire ash paint."""
        if not self.fire_scorch:
            return False
        return self._fire_key(wx, wy) in self.fire_scorch

    def sample_biome(self, wx, wy, lod=2):
        """Daytime surface color + meta (elev, river strength, land). lod 0–2.

        Implemented in Numba (_sample_biome_n) when available; disk-cached.
        """
        r, g, b, elev, river_amt, land_f = _sample_biome_n(
            float(wx), float(wy), int(self.seed), int(lod),
        )
        return (r, g, b), elev, river_amt, land_f > 0.5

    def sample(self, wx, wy, day_factor=1.0, lod=2):
        """
        Full surface sample: biome + baked city paint + wildfire embers.
        Cities are stamped once at world gen (city_paint); bombs overwrite cells.
        lod 0 = far overview (cheap), 1 = cruise/approach, 2 = close strike.
        Far LOD caps city brightness so sub-pixel cities don't strobe hard.
        """
        day = _clamp(day_factor, 0.0, 1.0)
        lod = int(lod)
        (r, g, b), elev, river_amt, land = self.sample_biome(wx, wy, lod=lod)
        light_r = light_g = light_b = 0.0
        light_w = 0.0

        # O(1) map paint — cities, bomb rubble, and fire colors all live here
        key = self._fire_key(wx, wy)
        paint = self.city_paint.get(key) if self.city_paint else None
        if paint is not None:
            pr, pg, pb, glow = float(paint[0]), float(paint[1]), float(paint[2]), float(paint[3])
            if lod <= 0:
                # Globe / far: soft urban blend into biome + heavily capped lights
                # (reduces harsh on/off flicker when samples skim city cells)
                ub = 0.34
                r = r + (pr - r) * ub
                g = g + (pg - g) * ub
                b = b + (pb - b) * ub
                glow_scale = 0.18
            elif lod == 1:
                ub = 0.72
                r = r + (pr - r) * ub
                g = g + (pg - g) * ub
                b = b + (pb - b) * ub
                glow_scale = 0.50
            else:
                r, g, b = pr, pg, pb
                glow_scale = 1.0
            if glow > 0.04 and glow_scale > 0.01:
                intensity = glow * glow_scale
                light_r += CITY_NIGHT[0] * intensity
                light_g += CITY_NIGHT[1] * intensity
                light_b += CITY_NIGHT[2] * intensity
                light_w += intensity
                light_r += CITY_GLOW[0] * intensity * 0.45
                light_g += CITY_GLOW[1] * intensity * 0.45
                light_b += CITY_GLOW[2] * intensity * 0.35

        # Day / night mix — respect light source (deep night away from sun)
        night_floor = 0.04  # dark atmosphere, not pure black
        shade = night_floor + (1.0 - night_floor) * (day ** 1.25)
        night = 1.0 - day
        # Lit cities at night: darken the gray daytime urban bake so yellow
        # lights aren't sitting on a whitish disc (looked like another layer).
        if paint is not None and light_w > 0.04 and night > 0.35:
            r *= night_floor + (1.0 - night_floor) * (1.0 - night) * 0.35
            g *= night_floor + (1.0 - night_floor) * (1.0 - night) * 0.35
            b *= night_floor + (1.0 - night_floor) * (1.0 - night) * 0.35
        else:
            r *= shade
            g *= shade
            b *= shade

        # City lights dominate at night / dusk (from baked glow)
        if light_w > 0.01 and night > 0.04:
            k = night * 1.35
            if k > 1.0:
                k = 1.0
            # Extra cap at far LOD so lights don't strobe as bright flashes
            if lod <= 0:
                k *= 0.55
            elif lod == 1:
                k *= 0.80
            r = r + light_r * k * 0.85
            g = g + light_g * k * 0.8
            b = b + light_b * k * 0.55

        if r < 0:
            r = 0
        elif r > 255:
            r = 255
        if g < 0:
            g = 0
        elif g > 255:
            g = 255
        if b < 0:
            b = 0
        elif b > 255:
            b = 255
        return (int(r), int(g), int(b))


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

    def draw(self, canvas, fade=1.0, frame=None):
        """
        Composite four layers front-to-back (SpaceExplorer paint_parallax).
        Optional frame buffer: keep composite in sync for full-frame NV (no HUD trails).
        """
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
                    rr = int(rgb[0] * fade)
                    gg = int(rgb[1] * fade)
                    bb = int(rgb[2] * fade)
                else:
                    rr, gg, bb = rgb[0], rgb[1], rgb[2]
                set_px(x, y, rr, gg, bb)
                if frame is not None:
                    frame[y][x] = (rr, gg, bb)


class SpaceIntro(object):
    """
    starfield → floating digital clock → fly-through → planet sighted →
    zoom → terminal briefing → handoff.
    Phases: stars | space_clock | clock_fly | dot | zoom | briefing | hold | done
    """

    def __init__(self, width, height, planet=None, space=None):
        self.w = int(width)
        self.h = int(height)
        # One shared starfield for intro + camera globe (do not build twice)
        self.space = space if space is not None else SpaceParallax(width, height)
        self.planet = planet if planet is not None else PlanetMap()
        self.phase = "stars"
        self.t = 0.0
        # Random approach site so day/night framing is not always the same
        self.showcase = self.planet.pick_approach_site()
        self.land_x = self.showcase["x"]
        self.land_y = self.showcase["y"]
        # Orientation: rotate so approach site faces the camera (+Z)
        R = float(getattr(self.planet, "R", PLANET_R))
        self.land_lon = self.land_x / R
        self.land_lat = _clamp(self.land_y / R, -1.2, 1.2)
        # Planet appears off-center a bit (not dead middle)
        self.px = self.w * random.uniform(0.35, 0.65)
        self.py = self.h * random.uniform(0.30, 0.70)
        self.dot_bright = 0.0
        self.planet_r = 0.4
        self.zoom_u = 0.0
        self.descent_u = 0.0       # 0..1 surface zoom after briefing
        self.descent_r0 = 0.0      # disc radius at start of descent
        self.term_fade = 1.0       # terminal opacity (fades out on descent)
        # Floating space clock (before planet)
        self.clock_scale = 1.0
        self.clock_alpha = 1.0
        self.clock_bob = 0.0
        # Pixel scale: hairline 5×9 glyphs (~50% larger than native 1px strokes)
        self.clock_px = 1.5
        self.hand_off_mpp = None   # FOV when handing off (full globe)
        self.hand_off_r = None     # disc radius matching intro globe
        self.hand_off_x = self.land_x
        self.hand_off_y = self.land_y
        # Clock + chatter (descent HUD kept for draw path if phase re-enabled)
        self.clock_text = ""
        self.cruise_stream = ""
        self.cruise_scroll_x = float(self.w)
        self._scroll_accum = 0.0
        self.cruise_ticker_queue = []
        # Terminal geometry (3×5 font + gap)
        self.term_cols = max(8, (self.w - 2) // (_HUD_CHAR_W + _HUD_GAP))
        self.term_row_h = _HUD_CHAR_H + TERM_LINE_GAP
        self.term_rows = max(3, (self.h - 2) // self.term_row_h)
        self.term_script = ""
        self.term_script_i = 0
        self.term_carry = 0.0
        self.term_lines = []       # completed lines (oldest first)
        self.term_cur = ""         # current line being typed
        self.term_done = False
        self.term_cursor_on = True
        self.term_scroll_px = 0.0  # pixels scrolled up during line-feed anim
        self.term_scrolling = False
        self._build_approach_terminal()
        day0 = self.planet.day_factor_flat(self.land_x, self.land_y)
        size_cls = getattr(self.planet, "size_class", "?")
        size_sc = float(getattr(self.planet, "size_scale", 1.0))
        print(
            f"[PlanetBlast] Space intro — approaching {self.planet.name}  "
            f"size={size_cls} ({size_sc:.2f}x)  species={self.planet.species}  "
            f"site day={day0:.2f}  terminal {self.term_cols}x{self.term_rows}"
        )

    def _globe_max_r(self):
        """Full-planet disc radius (matches orbit-hold view — no handoff pop)."""
        return _full_planet_disc_r(
            self.w, self.h,
            size_scale=float(getattr(self.planet, "size_scale", 1.0)),
        )

    def _build_approach_terminal(self):
        """
        Label on its own line, value on the next, blank line between sections:
          PLANET:
          BARFUS III

          CRIME:
          BLAH BLAH BLAH.
        """
        world = str(self.planet.name).upper()
        species = str(getattr(self.planet, "species", "UNKNOWN")).upper()
        crimes = list(getattr(self.planet, "crimes", ()) or ())
        crime = str(crimes[0]).upper() if crimes else "UNKNOWN"
        status = random.choice(TERM_STATUSES)
        # Each block: [label, value...] — blank line inserted between blocks
        blocks = [
            ["PLANET:", world],
            ["SPECIES:", species],
            ["CRIME:", crime],
            ["STATUS:", status],
            ["AWAITING SURFACE DESCENT..."],
        ]
        script_parts = []
        for bi, block in enumerate(blocks):
            for line in block:
                script_parts.extend(self._wrap_line(line, self.term_cols))
            if bi < len(blocks) - 1:
                script_parts.append("")
        self.term_script = "\n".join(script_parts) + "\n"
        self.term_script_i = 0
        self.term_carry = 0.0
        self.term_lines = []
        self.term_cur = ""
        self.term_done = False
        self.term_scroll_px = 0.0
        self.term_scrolling = False

    @staticmethod
    def _wrap_line(text, cols):
        """Word-wrap a single line to col width; returns list of row strings."""
        text = str(text)
        if len(text) <= cols:
            return [text]
        words = text.split(" ")
        rows = []
        cur = ""
        for w in words:
            if not w:
                continue
            if len(w) > cols:
                if cur:
                    rows.append(cur)
                    cur = ""
                for i in range(0, len(w), cols):
                    rows.append(w[i: i + cols])
                continue
            trial = w if not cur else (cur + " " + w)
            if len(trial) <= cols:
                cur = trial
            else:
                if cur:
                    rows.append(cur)
                cur = w
        if cur:
            rows.append(cur)
        return rows or [""]

    def _term_line_rgb(self, line):
        """Terminal dossier is mono green (night-vision / warcom feed)."""
        fade = _clamp(getattr(self, "term_fade", 1.0), 0.0, 1.0)
        r, g, b = HUD_RGB
        return (int(r * fade), int(g * fade), int(b * fade))

    def _term_push_line(self):
        """Commit current line; start smooth scroll-up if at bottom."""
        self.term_lines.append(self.term_cur)
        self.term_cur = ""
        if len(self.term_lines) >= self.term_rows and not self.term_scrolling:
            # Slide content up one row (px/frame), then drop the oldest line
            self.term_scrolling = True
            self.term_scroll_px = 0.0

    def _term_finish_scroll(self):
        """Finalize scroll: remove lines that scrolled off the top."""
        while len(self.term_lines) >= self.term_rows:
            self.term_lines.pop(0)
        self.term_scrolling = False
        self.term_scroll_px = 0.0

    def _update_terminal(self, dt):
        """Typewriter L→R; smooth pixel scroll when a new line needs room."""
        self.term_cursor_on = (int(self.t * 3.2) % 2) == 0

        # Smooth scroll-up: constant px/sec so each LED row steps evenly
        if self.term_scrolling:
            # Cap dt so a hitch doesn't jump a full row in one frame
            step = min(dt, TERM_SCROLL_SEC * 0.35)
            speed = float(self.term_row_h) / max(0.05, TERM_SCROLL_SEC)
            self.term_scroll_px += speed * step
            if self.term_scroll_px >= float(self.term_row_h):
                self._term_finish_scroll()
            return

        if self.term_done:
            return
        self.term_carry += TERM_CPS * dt
        while self.term_carry >= 1.0 and not self.term_done and not self.term_scrolling:
            self.term_carry -= 1.0
            if self.term_script_i >= len(self.term_script):
                if self.term_cur:
                    self._term_push_line()
                if not self.term_scrolling:
                    self.term_done = True
                break
            ch = self.term_script[self.term_script_i]
            self.term_script_i += 1
            if ch == "\n":
                self._term_push_line()
            else:
                self.term_cur += ch
                if len(self.term_cur) >= self.term_cols:
                    self._term_push_line()
            if self.term_scrolling:
                break
        # If scroll started after last char, don't mark done until scroll ends
        if (
            self.term_script_i >= len(self.term_script)
            and not self.term_cur
            and not self.term_scrolling
        ):
            self.term_done = True

    def _draw_terminal(self, canvas):
        """
        Paint terminal text over the live planet (no solid plate).
        Blinking square block cursor; smooth vertical scroll on new lines.
        """
        total_h = self.term_rows * self.term_row_h
        y0 = max(0, self.h - total_h - 1)
        y_clip_bot = self.h
        set_px = canvas.SetPixel

        rows = list(self.term_lines) + [self.term_cur]
        # During scroll keep one extra row so content slides in from below
        if self.term_scrolling:
            rows = rows[-(self.term_rows + 1):]
        else:
            rows = rows[-self.term_rows:]

        # Integer pixel offset: advance 0 → row_h upward, one LED row at a time
        offset_px = 0
        if self.term_scrolling:
            offset_px = -int(min(self.term_scroll_px, float(self.term_row_h)))

        cursor_col = len(self.term_cur)
        cursor_row_index = len(rows) - 1

        for i, line in enumerate(rows):
            hy = y0 + i * self.term_row_h + offset_px
            # Clip to terminal band (line exits cleanly at the top)
            if hy + _HUD_CHAR_H < y0:
                continue
            if hy >= y_clip_bot:
                break
            rgb = self._term_line_rgb(line)
            text = _hud_fit(line, self.w - 2)
            if text:
                self._draw_term_line_clipped(
                    canvas, text, 1, hy, rgb, y0, y_clip_bot,
                )

        # Square block cursor at end of typing line (blinks; hidden while scrolling)
        if self.term_cursor_on and not self.term_scrolling and self.term_fade > 0.2:
            cx = 1 + cursor_col * (_HUD_CHAR_W + _HUD_GAP)
            cy = y0 + cursor_row_index * self.term_row_h + offset_px
            cr, cg, cb = self._term_line_rgb("")
            if y0 <= cy < self.h:
                for dy in range(_HUD_CHAR_H):
                    for dx in range(_HUD_CHAR_W):
                        px, py = cx + dx, cy + dy
                        if 0 <= px < self.w and y0 <= py < self.h:
                            set_px(px, py, cr, cg, cb)

    def _draw_term_line_clipped(self, canvas, text, x, y, rgb, y_lo, y_hi):
        """Draw HUD text with vertical clip so scroll edges stay clean."""
        set_px = canvas.SetPixel
        r, g, b = rgb
        cx = int(x)
        cy = int(y)
        for ch in str(text).upper():
            rows = _HUD_GLYPHS.get(
                ch, _HUD_GLYPHS.get("?", (0b111, 0b001, 0b010, 0b000, 0b010)),
            )
            for row_i, bits in enumerate(rows):
                py = cy + row_i
                if py < y_lo or py >= y_hi or py < 0 or py >= self.h:
                    continue
                for col in range(_HUD_CHAR_W):
                    if bits & (0b100 >> col):
                        px = cx + col
                        if 0 <= px < self.w:
                            set_px(px, py, r, g, b)
            cx += _HUD_CHAR_W + _HUD_GAP

    @property
    def done(self):
        return self.phase == "done"

    def _clock_string(self):
        """Local time as HH:MM for the large space clock."""
        lt = time.localtime()
        return f"{lt.tm_hour:02d}:{lt.tm_min:02d}"

    def _clock_pixel_size(self):
        """Width/height of full HH:MM block at current scale (unscaled base)."""
        sc = max(1.0, float(self.clock_px))
        total_units = 5 * _CLOCK_DIGIT_W + 4 * _CLOCK_DIGIT_GAP
        return int(round(total_units * sc)), int(round(_CLOCK_DIGIT_H * sc))

    def _start_empire_news(self):
        """Shuffle the empire news pool into the bottom marquee for the clock phase."""
        feed = list(_EMPIRE_NEWS_FEED)
        random.shuffle(feed)
        head = [
            "EMPIRE NEWS NET",
            "SECTOR BRIEFING",
            "RUMORS OF WAR",
            f"FEEDS ONLINE  {len(feed)} ITEMS",
        ]
        self.cruise_ticker_queue = head + feed
        self.cruise_stream = ""
        self.cruise_scroll_x = float(self.w)
        self._scroll_accum = 0.0
        print(
            f"[PlanetBlast] Empire news ticker — {len(feed)} items  "
            f"@ {SPACE_NEWS_PPS:.0f} px/s"
        )

    def _update_space_news(self, dt):
        """
        Scroll empire news marquee (space_clock / clock_fly).

        Frame-locked: exactly 1 pixel per update. LED marquees look jittery when
        dt-based accumulation sometimes steps 0 and sometimes 2; locking to the
        render tick matches TARGET_FPS and keeps motion even.
        """
        char_step = _HUD_CHAR_W + _HUD_GAP  # integer glyph cell
        sep = "    "

        def _refill():
            if not self.cruise_ticker_queue:
                more = list(_EMPIRE_NEWS_FEED)
                random.shuffle(more)
                self.cruise_ticker_queue = more

        def _append(min_px=None):
            if min_px is None:
                min_px = self.w * 6
            guard = 0
            while _hud_text_width(self.cruise_stream) < min_px and guard < 80:
                _refill()
                if not self.cruise_ticker_queue:
                    break
                msg = str(self.cruise_ticker_queue.pop(0)).upper()
                if self.cruise_stream:
                    self.cruise_stream += sep + msg
                else:
                    self.cruise_stream = msg
                guard += 1

        if not self.cruise_stream:
            self.cruise_scroll_x = float(self.w)
            self._scroll_accum = 0.0
            _append()
        else:
            stream_w = _hud_text_width(self.cruise_stream)
            if self.cruise_scroll_x + stream_w < self.w * 3:
                _append(min_px=self.w * 6)

        # Exactly one whole pixel left per frame — no residual, no multi-step
        self.cruise_scroll_x = float(int(self.cruise_scroll_x) - 1)
        self._scroll_accum = 0.0

        # Drop fully off-screen characters (keep x continuous, no jump)
        while self.cruise_stream and self.cruise_scroll_x <= -char_step:
            self.cruise_stream = self.cruise_stream[1:]
            self.cruise_scroll_x += float(char_step)
            if not self.cruise_stream:
                _append()
                break

    def _draw_space_news(self, canvas, alpha=1.0):
        """Bottom marquee: empire news / rumors during the space clock."""
        stream = getattr(self, "cruise_stream", "") or ""
        if not stream:
            return
        a = _clamp(float(alpha), 0.0, 1.0)
        if a < 0.04:
            return
        r = int(HUD_FIRE_RGB[0] * a)
        g = int(HUD_FIRE_RGB[1] * a)
        b = int(HUD_FIRE_RGB[2] * a)
        hy = max(0, self.h - _HUD_CHAR_H - 1)
        # Integer x only (scroll is already whole-pixel stepped)
        _draw_hud_text(
            canvas, stream,
            int(self.cruise_scroll_x), hy,
            (r, g, b), self.w, self.h,
        )

    def _draw_space_clock(self, canvas):
        """
        Skinny hairline digital clock — solid color only (no shadow, no AA).

        Fly-through uses continuous float scale anchored at the rest-clock
        center so growth is smooth. Any pixel the stroke touches is full
        clock color (same footprint as coverage AA, no dim edge pixels).
        """
        set_px = canvas.SetPixel
        text = self._clock_string()
        base_sc = max(1.0, float(self.clock_px))
        fly = max(1.0, float(getattr(self, "clock_scale", 1.0)))
        sc = base_sc * fly
        alpha = _clamp(float(getattr(self, "clock_alpha", 1.0)), 0.0, 1.0)
        if alpha < 0.02:
            return

        n = len(text)
        unit_x = []
        u = 0.0
        for i, ch in enumerate(text):
            unit_x.append(u)
            u += float(_CLOCK_DIGIT_W)
            if i < n - 1:
                u += float(_CLOCK_DIGIT_GAP)
        total_units = u
        total_w = total_units * sc
        total_h = float(_CLOCK_DIGIT_H) * sc

        rest_w = total_units * base_sc
        rest_h = float(_CLOCK_DIGIT_H) * base_sc
        rest_x0 = (self.w - rest_w) * 0.5
        rest_y0 = float(max(1, min(2, self.h // 14)))
        ax = rest_x0 + rest_w * 0.5
        ay = rest_y0 + rest_h * 0.5
        x0 = ax - total_w * 0.5
        y0 = ay - total_h * 0.5

        cr = int(_CLOCK_RGB[0] * alpha)
        cg = int(_CLOCK_RGB[1] * alpha)
        cb = int(_CLOCK_RGB[2] * alpha)
        msb = 1 << (_CLOCK_DIGIT_W - 1)
        lit = set()

        def _stamp_rect(sx0, sy0, sx1, sy1):
            """Solid-fill every pixel the continuous stroke cell overlaps."""
            if sx1 <= sx0 or sy1 <= sy0:
                return
            ix0 = max(0, int(math.floor(sx0)))
            iy0 = max(0, int(math.floor(sy0)))
            ix1 = min(self.w, int(math.ceil(sx1)))
            iy1 = min(self.h, int(math.ceil(sy1)))
            for py in range(iy0, iy1):
                if min(sy1, py + 1.0) - max(sy0, float(py)) <= 0.0:
                    continue
                for px in range(ix0, ix1):
                    if min(sx1, px + 1.0) - max(sx0, float(px)) <= 0.0:
                        continue
                    lit.add(py * self.w + px)

        for i, ch in enumerate(text):
            rows = _CLOCK_DIGITS.get(ch)
            if rows is None:
                continue
            ux = unit_x[i]
            for row_i, bits in enumerate(rows):
                for col in range(_CLOCK_DIGIT_W):
                    if not (bits & (msb >> col)):
                        continue
                    sx0 = x0 + (ux + col) * sc
                    sy0 = y0 + row_i * sc
                    _stamp_rect(sx0, sy0, sx0 + sc, sy0 + sc)

        for key in lit:
            set_px(key % self.w, key // self.w, cr, cg, cb)

    def update(self, dt):
        self.t += dt
        if self.phase == "stars":
            self.space.update(dt, streak=0.0)
            if self.t >= STAR_DRIFT_SEC:
                self.phase = "space_clock"
                self.t = 0.0
                self.clock_scale = 1.0
                self.clock_alpha = 1.0
                self._start_empire_news()
                print(
                    f"[PlanetBlast] Space clock — floating {SPACE_CLOCK_SEC:.0f}s  "
                    f"then fly-through"
                )
        elif self.phase == "space_clock":
            # Stars + nebula keep scrolling; clock fixed near top; news scrolls
            self.space.update(dt, streak=0.05)
            self.clock_bob = 0.0
            self.clock_scale = 1.0
            self.clock_alpha = 1.0
            self._update_space_news(dt)
            if self.t >= SPACE_CLOCK_SEC:
                self.phase = "clock_fly"
                self.t = 0.0
                print("[PlanetBlast] Fly-through clock — entering system…")
        elif self.phase == "clock_fly":
            # Smooth fly-through: continuous scale (drawn with float sc), ease-in-out
            u = _clamp(self.t / max(0.05, SPACE_CLOCK_FLY_SEC), 0.0, 1.0)
            # Smootherstep — zero 1st/2nd derivative at ends (less jumpy than smoothstep)
            ease = u * u * u * (u * (u * 6.0 - 15.0) + 10.0)
            self.space.update(dt, streak=0.15 + 1.6 * ease)
            self.clock_scale = _lerp(1.0, 10.0, ease)
            # Hold full opacity briefly, then fade as we pass through
            self.clock_alpha = max(0.0, 1.0 - max(0.0, ease - 0.35) / 0.65)
            self.clock_bob = 0.0
            self._update_space_news(dt)
            if self.t >= SPACE_CLOCK_FLY_SEC:
                self.phase = "dot"
                self.t = 0.0
                self.clock_alpha = 0.0
                self.cruise_stream = ""
                self.cruise_ticker_queue = []
                print(f"[PlanetBlast] {self.planet.name} sighted — bright dot")
                print(f"[PlanetBlast] Species: {self.planet.species}")
                if self.planet.crimes:
                    print(f"[PlanetBlast] Crime: {self.planet.crimes[0]}")
        elif self.phase == "dot":
            # Planet as a distant point only — no briefing text yet
            self.space.update(dt, streak=0.15)
            self.dot_bright = _smoothstep(self.t / 0.55)
            if self.t >= PLANET_DOT_SEC:
                self.phase = "zoom"
                self.t = 0.0
                print(f"[PlanetBlast] Approaching {self.planet.name}…")
        elif self.phase == "zoom":
            # Grow to full globe first; terminal waits until fully zoomed
            u = _smoothstep(min(1.0, self.t / PLANET_ZOOM_SEC))
            self.zoom_u = u
            self.space.update(dt, streak=u * u)
            self.dot_bright = 1.0
            max_r = self._globe_max_r()
            self.planet_r = _lerp(0.6, max_r, u * u * (0.4 + 0.6 * u))
            self.px = _lerp(self.px, self.w * 0.5, dt * 0.35)
            self.py = _lerp(self.py, self.h * 0.5, dt * 0.35)
            if self.t >= PLANET_ZOOM_SEC:
                self.phase = "briefing"
                self.t = 0.0
                print(f"[PlanetBlast] Globe locked — terminal briefing")
        elif self.phase == "briefing":
            # Full-size planet visible; type world / species / charges
            self.space.update(dt, streak=1.0)
            self.dot_bright = 1.0
            self.planet_r = self._globe_max_r()
            self.px = self.w * 0.5
            self.py = self.h * 0.5
            self.term_fade = 1.0
            self._update_terminal(dt)
            if self.term_done:
                self.phase = "hold"
                self.t = 0.0
                print(f"[PlanetBlast] Briefing complete — {self.planet.name}")
        elif self.phase == "hold":
            self.space.update(dt, streak=1.0)
            self.dot_bright = 1.0
            self.planet_r = self._globe_max_r()
            self.px = self.w * 0.5
            self.py = self.h * 0.5
            self.term_fade = 1.0
            self._update_terminal(dt)
            if self.t >= BRIEFING_HOLD_SEC:
                # Full globe locked on pick city — hand off to camera for the
                # continuous sphere→flat→strike dive (no projection jump).
                self.planet_r = self._globe_max_r()
                self.px = self.w * 0.5
                self.py = self.h * 0.5
                self.hand_off_mpp = self._sphere_mpp()
                self.hand_off_r = float(self.planet_r)
                self.hand_off_x = float(self.land_x)
                self.hand_off_y = float(self.land_y)
                city = self.showcase if isinstance(self.showcase, dict) else None
                self.phase = "done"
                print(
                    f"[PlanetBlast] Globe locked — orbit hold on "
                    f"{_city_display_name(city) if city else 'TARGET'}  "
                    f"r={self.hand_off_r:.1f}px  mpp={self.hand_off_mpp:.0f}"
                )
        elif self.phase == "descent":
            # Legacy path: should not run (handoff is at globe after hold).
            self.phase = "done"

    def _update_descent_hud(self, dt):
        """Clock + scrolling chatter while diving from orbit to the city."""
        lt = time.localtime()
        self.clock_text = f"{lt.tm_hour:02d}:{lt.tm_min:02d}"
        # Simple WARCOM marquee (no full PlanetCamera deps)
        if not self.cruise_ticker_queue:
            chatter = list(_WARCOM_LINES)
            random.shuffle(chatter)
            world = str(getattr(self.planet, "name", "WORLD")).upper()
            city = _city_display_name(self.showcase) if isinstance(self.showcase, dict) else "TARGET"
            head = [f"WORLD {world}", f"TGT {city}", "DESCENT", "WEAPONS STANDBY"]
            self.cruise_ticker_queue = head + chatter
        if not self.cruise_stream:
            self.cruise_scroll_x = float(self.w)
            self._scroll_accum = 0.0
            while _hud_text_width(self.cruise_stream) < self.w * 4 and self.cruise_ticker_queue:
                msg = str(self.cruise_ticker_queue.pop(0)).upper()
                if self.cruise_stream:
                    self.cruise_stream += "    " + msg
                else:
                    self.cruise_stream = msg
        else:
            if self.cruise_scroll_x + _hud_text_width(self.cruise_stream) < self.w * 2:
                while (
                    _hud_text_width(self.cruise_stream) < self.w * 4
                    and self.cruise_ticker_queue
                ):
                    msg = str(self.cruise_ticker_queue.pop(0)).upper()
                    self.cruise_stream += "    " + msg
                if not self.cruise_ticker_queue:
                    self.cruise_ticker_queue = list(_WARCOM_LINES)
                    random.shuffle(self.cruise_ticker_queue)
        self._scroll_accum += CRUISE_TICKER_PPS * min(dt, 0.08)
        step = int(self._scroll_accum)
        if step > 0:
            self.cruise_scroll_x -= float(step)
            self._scroll_accum -= float(step)
        char_step = float(_HUD_CHAR_W + _HUD_GAP)
        while self.cruise_stream and self.cruise_scroll_x <= -char_step:
            self.cruise_stream = self.cruise_stream[1:]
            self.cruise_scroll_x += char_step

    def draw(self, canvas):
        set_px = canvas.SetPixel
        try:
            canvas.Fill(0, 0, 4)
        except Exception:
            for y in range(self.h):
                for x in range(self.w):
                    set_px(x, y, 0, 0, 4)

        star_fade = 1.0
        if self.phase in ("space_clock", "clock_fly", "stars"):
            star_fade = 1.0
        elif self.phase == "zoom":
            u = _smoothstep(min(1.0, self.t / PLANET_ZOOM_SEC))
            star_fade = 1.0 - u * 0.92
        elif self.phase in ("briefing", "hold"):
            star_fade = 0.08
        elif self.phase == "descent":
            star_fade = 0.08 * max(0.0, 1.0 - self.descent_u * 1.4)
        self.space.draw(canvas, fade=star_fade)

        # Floating / fly-through digital clock + empire news marquee
        if self.phase in ("space_clock", "clock_fly"):
            self._draw_space_clock(canvas)
            news_a = 1.0 if self.phase == "space_clock" else float(
                getattr(self, "clock_alpha", 1.0)
            )
            self._draw_space_news(canvas, alpha=news_a)

        if self.phase in ("dot", "zoom", "briefing", "hold", "descent"):
            self._draw_planet(canvas)
        # Terminal over the globe only before dive
        if self.phase in ("briefing", "hold") and self.term_fade > 0.04:
            self._draw_terminal(canvas)
        # Clock + chatter during continuous dive to city
        if self.phase == "descent":
            clock = getattr(self, "clock_text", "") or ""
            if clock:
                _draw_hud_text(canvas, clock, 1, 1, HUD_RGB, self.w, self.h)
            stream = getattr(self, "cruise_stream", "") or ""
            if stream:
                hy = max(0, self.h - _HUD_CHAR_H - 1)
                _draw_hud_text(
                    canvas, stream,
                    int(self.cruise_scroll_x), hy,
                    HUD_FIRE_RGB, self.w, self.h,
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

    def _sphere_mpp(self):
        """
        Meters-per-pixel for the current disc size on the shared planet map.
        Screen offset ≈ planet_r maps to ~1 radian on the unit sphere → R meters.
        Same formula from first sighting through deep dive (continuous FOV).
        """
        world_r = float(getattr(self.planet, "R", PLANET_R) or PLANET_R)
        return world_r / max(float(self.planet_r), 0.5)

    def _draw_planet(self, canvas):
        """
        Draw the planet using ONLY the shared PlanetMap sphere projection.
        No second UV / flat-window morph — that caused landmasses to jump while zooming.
        Growing planet_r continuously tightens FOV on the same map.
        """
        set_px = canvas.SetPixel
        cx, cy = self.px, self.py
        radius = max(0.5, self.planet_r)
        glow_r = radius + 1.2 + min(3.0, radius * 0.08)
        x0 = max(0, int(cx - glow_r - 1))
        x1 = min(self.w - 1, int(cx + glow_r + 1))
        y0 = max(0, int(cy - glow_r - 1))
        y1 = min(self.h - 1, int(cy + glow_r + 1))
        b = _clamp(self.dot_bright, 0.0, 1.0)
        descent = _clamp(getattr(self, "descent_u", 0.0), 0.0, 1.0)
        # Full globe / briefing: lod 0 so city brightness is capped (less flicker)
        world_r = float(getattr(self.planet, "R", PLANET_R) or PLANET_R)
        mpp_est = world_r / max(radius, 0.5)
        if radius < 5.0 or mpp_est > 8_000.0 or radius < min(self.w, self.h) * 0.95:
            lod = 0
        elif mpp_est > 3_500.0:
            lod = 1
        else:
            lod = 2
        step = 1  # full resolution — no blocky sparse sampling
        sample = self.planet.sample
        day_sphere = self.planet.day_factor_sphere
        world_from = self.planet.world_from_sphere
        view_to = self._view_to_planet_normal
        fade = 1.0 if radius > 3 else _clamp(radius / 3.0, 0.0, 1.0)
        glow_span = max(0.2, glow_r - radius)
        # Limb → flat as we dive (visual only; UVs stay spherical/map-consistent)
        limb_flat = _smoothstep(descent)

        for y in range(y0, y1 + 1, step):
            for x in range(x0, x1 + 1, step):
                dx = x + 0.5 - cx
                dy = y + 0.5 - cy
                d2 = dx * dx + dy * dy
                if d2 > glow_r * glow_r:
                    continue
                d = math.sqrt(d2)
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
                    # Single map path: sphere normal → planet equirectangular meters
                    pnx, pny, pnz = view_to(nx, ny, nz)
                    wx, wy = world_from(pnx, pny, pnz)
                    day = day_sphere(pnx, pny, pnz)
                    tr, tg, tb = sample(wx, wy, day_factor=day, lod=lod)
                    limb = 0.55 + 0.45 * nz
                    limb = limb + (1.0 - limb) * limb_flat
                    lf = limb * fade
                    rr = int(_clamp(tr * lf, 0, 255))
                    gg = int(_clamp(tg * lf, 0, 255))
                    bb = int(_clamp(tb * lf, 0, 255))
                    if step == 1:
                        set_px(x, y, rr, gg, bb)
                    else:
                        for fy in range(y, min(y + step, y1 + 1)):
                            for fx in range(x, min(x + step, x1 + 1)):
                                set_px(fx, fy, rr, gg, bb)
                elif d <= glow_r:
                    if descent > 0.45:
                        continue
                    t = 1.0 - (d - radius) / glow_span
                    t = t * t * 0.55 * (1.0 - descent)
                    gr, gg, gb = int(80 * t), int(140 * t), int(220 * t)
                    if step == 1:
                        set_px(x, y, gr, gg, gb)
                    else:
                        for fy in range(y, min(y + step, y1 + 1)):
                            for fx in range(x, min(x + step, x1 + 1)):
                                set_px(fx, fy, gr, gg, gb)

        # Stable 1px city pins at full-globe range (same idea as camera globe)
        if mpp_est >= GLOBE_CITY_PIN_MPP and radius >= 5.0:
            self._stamp_intro_city_pins(canvas, cx, cy, radius)

    def _stamp_intro_city_pins(self, canvas, cx, cy, radius):
        """1px city pins during intro globe (muted; no disc overlay)."""
        set_px = canvas.SetPixel
        world_r = float(getattr(self.planet, "R", PLANET_R) or PLANET_R)
        lon, lat = self.land_lon, self.land_lat
        min_sz = int(GLOBE_CITY_PIN_MIN_SIZE)
        for city in self.planet.cities:
            sz = int(city.get("size", 1))
            if sz < min_sz:
                continue
            if city.get("obliterated"):
                continue
            clon = float(city["x"]) / world_r
            clat = _clamp(float(city["y"]) / world_r, -1.2, 1.2)
            cl = math.cos(clat)
            px = math.sin(clon) * cl
            py = math.sin(clat)
            pz = math.cos(clon) * cl
            vx, vy, vz = _planet_to_view_normal(px, py, pz, lon, lat)
            if vz < 0.18:
                continue
            sx = cx + vx * radius
            sy = cy + vy * radius
            if (sx - cx) ** 2 + (sy - cy) ** 2 > (radius * 1.02) ** 2:
                continue
            ix, iy = int(round(sx)), int(round(sy))
            if ix < 0 or ix >= self.w or iy < 0 or iy >= self.h:
                continue
            day = self.planet.day_factor_flat(float(city["x"]), float(city["y"]))
            if day < NV_NIGHT_MAX:
                cr, cg, cb = (190, 130, 48) if sz >= 5 else (160, 110, 40)
            else:
                cr, cg, cb = (115, 112, 110) if sz >= 5 else (95, 95, 100)
            set_px(ix, iy, cr, cg, cb)


# ---------------- Camera / flight ----------------
def _view_to_planet_normal(nx, ny, nz, lon, lat):
    """
    Rotate view-space sphere normal so (lon, lat) faces the camera (+Z).
    View: +Z toward camera. Used by intro globe and mid-mission orbit.
    """
    cl, sl = math.cos(lat), math.sin(lat)
    x1, y1, z1 = nx, ny * cl - nz * sl, ny * sl + nz * cl
    co, so = math.cos(lon), math.sin(lon)
    x2 = x1 * co + z1 * so
    y2 = y1
    z2 = -x1 * so + z1 * co
    return x2, y2, z2


def _planet_to_view_normal(px, py, pz, lon, lat):
    """
    Inverse of _view_to_planet_normal: planet-frame unit vector → view space.
    View +Z faces the camera; z>0 means on the visible hemisphere.
    """
    co, so = math.cos(lon), math.sin(lon)
    # Inverse Ry(lon)
    x1 = px * co - pz * so
    y1 = py
    z1 = px * so + pz * co
    # Inverse Rx(lat)
    cl, sl = math.cos(lat), math.sin(lat)
    nx = x1
    ny = y1 * cl + z1 * sl
    nz = -y1 * sl + z1 * cl
    return nx, ny, nz


def _hud_text_width(text):
    """Pixel width of HUD string (3×5 glyphs + 1px gaps)."""
    n = len(text)
    if n <= 0:
        return 0
    return n * _HUD_CHAR_W + max(0, n - 1) * _HUD_GAP


def _full_planet_disc_r(panel_w, panel_h, size_scale=1.0):
    """
    Screen disc radius for a full-planet view with starfield rim.
    Shared by intro briefing and orbit hold so zoom never jumps at handoff.
    Slight size variation: dwarfs a bit smaller, large worlds use full fit.
    """
    fit = min(int(panel_w), int(panel_h)) * 0.46
    s = _clamp(float(size_scale), PLANET_SIZE_MIN, PLANET_SIZE_MAX)
    t = (math.log(s) - math.log(PLANET_SIZE_MIN)) / (
        math.log(PLANET_SIZE_MAX) - math.log(PLANET_SIZE_MIN)
    )
    return fit * _lerp(0.82, 1.0, t)


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


def _draw_hud_text(canvas, text, x, y, rgb, panel_w, panel_h, frame=None):
    """
    Draw teeny 3×5 bitmap HUD text. Still readable on 64×32 LEDs.
    Only paints lit glyph pixels (transparent background).
    Optional frame buffer keeps composite for full-frame NV.
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
                        if frame is not None:
                            frame[py][px] = (r, g, b)
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

    def __init__(
        self, width, height, planet=None, start_xy=None, city=None,
        start_mpp=None, start_globe_r=None, first_approach=True, space=None,
    ):
        self.w = int(width)
        self.h = int(height)
        self.planet = planet if planet is not None else PlanetMap()
        self.seed = self.planet.seed
        self.visited = set()
        # Shared starfield from intro (one simulation for the whole mission)
        self._orbit_space = space
        # First strike city = approach city from planet zoom (same map, no teleport)
        self.city = city if city is not None else self.planet.pick_showcase_city()
        self._mark_visited(self.city)
        if start_xy is not None:
            self.x = float(start_xy[0])
            self.y = float(start_xy[1])
        else:
            self.x = float(self.city["x"])
            self.y = float(self.city["y"])
        # Heading -π/2 matches sphere→flat UV axes (screen right→+X, down→+Y)
        self.heading = -math.pi * 0.5
        self.turn_rate = 0.0
        self.leg_t = 0.0
        self.leg_len = random.uniform(LEG_MIN, LEG_MAX)
        self.t = 0.0
        self.phase_t = 0.0
        self.cruise_t = 0.0
        self.cruise_leg_t = 0.0
        self.cruise_leg_len = random.uniform(CRUISE_LEG_MIN, CRUISE_LEG_MAX)
        self.alt_wide = _alt_for_city_pixels(self.city, self.h, CITY_WIDE_PX)
        self.alt_close = _alt_for_city_pixels(self.city, self.h, CITY_TARGET_PX)
        if start_mpp is not None and float(start_mpp) > 1.0:
            self.alt_ft = self._alt_from_mpp(float(start_mpp))
        else:
            self.alt_ft = float(self.alt_close)
        self.alt_from = float(self.alt_ft)
        self.alt_to = float(self.alt_close)
        self.bombs = []
        self.blasts = []
        self.bomb_cd = 0.35
        self._nv = False
        self.aim_err_x = random.uniform(-0.35, 0.35) * CAM_AIM_ERR_M
        self.aim_err_y = random.uniform(-0.35, 0.35) * CAM_AIM_ERR_M
        self.hud_text = "SCAN"
        self.hud_rgb = HUD_RGB
        self.clock_text = ""
        self.cruise_stream = ""
        self.cruise_scroll_x = float(self.w)
        self._scroll_accum = 0.0
        self.cruise_ticker_queue = []
        self._prev = [[(0, 0, 0) for _ in range(self.w)] for _ in range(self.h)]
        self._frame = [[(0, 0, 0) for _ in range(self.w)] for _ in range(self.h)]
        # Match first city's lighting so the following nearby targets stay local
        d0 = self.planet.day_factor_flat(self.city["x"], self.city["y"])
        self.batch_side = "night" if d0 < 0.5 else "day"
        self.batch_done = 0
        self.cities_bombed = 0
        self.since_patrol = 0
        self.patrol_t = 0.0
        self.patrol_leg_t = 0.0
        self.patrol_leg_len = PATROL_LEG_MAX
        self.strike_city = self.city
        self.next_city = None
        self._pending_patrol = False
        self.orbit_picked = False
        self.surrendered = False
        self.mission_done = False
        self._init_engagement_quota()
        self._first_approach = bool(first_approach)
        # Continuous first dive from full globe (same projection blend as orbit_in).
        # Avoids the sphere-intro → flat-surface jump.
        if first_approach:
            self._begin_first_approach(
                self.city,
                globe_r=start_globe_r,
                start_mpp=start_mpp,
            )
        else:
            self.phase = "bomb"
            self.phase_t = 0.0
            self.alt_ft = float(self.alt_close)

    def _mark_visited(self, city):
        self.visited.add(id(city))

    def _init_engagement_quota(self):
        """
        Before engagement: roll how many cities WARCOM expects to bomb.
        After each kill a surrender dice roll runs; at quota, surrender is certain.
        """
        n = max(1, len(self.planet.cities))
        lo = min(SURRENDER_QUOTA_MIN, n)
        hi = min(SURRENDER_QUOTA_MAX, n)
        if hi < lo:
            hi = lo
        self.surrender_quota = int(random.randint(lo, hi))
        world = str(getattr(self.planet, "name", "WORLD"))
        print(
            f"[PlanetBlast] Engagement on {world}: bomb target = "
            f"{self.surrender_quota} cities  (of {n}) — then expect surrender"
        )

    def _roll_surrender(self):
        """
        Dice after a city is destroyed. Returns True if the planet surrenders.
        Chance rises with cities bombed. Meeting engagement quota raises chance
        but does not force surrender — holdouts get faster wildfire instead.
        """
        bombed = int(self.cities_bombed)
        quota = max(1, int(getattr(self, "surrender_quota", SURRENDER_QUOTA_MIN)))
        if bombed >= quota:
            chance = max(
                SURRENDER_AT_QUOTA,
                SURRENDER_BASE_CHANCE + SURRENDER_PER_KILL * max(0, bombed - 1),
            )
            chance = min(0.85, chance)
        else:
            chance = SURRENDER_BASE_CHANCE + SURRENDER_PER_KILL * max(0, bombed - 1)
            chance = min(0.72, chance)
        roll = random.random()
        print(
            f"[PlanetBlast] Surrender dice: roll={roll:.3f} need<{chance:.3f}  "
            f"bombed={bombed}/{quota}"
        )
        return roll < chance

    def _maybe_rage_fire_after_kill(self):
        """If engagement quota is met and they still fight, speed up wildfire."""
        quota = max(1, int(getattr(self, "surrender_quota", SURRENDER_QUOTA_MIN)))
        if self.cities_bombed < quota:
            return
        if getattr(self.planet, "fire_raged", False):
            return
        world = str(getattr(self.planet, "name", "WORLD")).upper()
        print(
            f"[PlanetBlast] {world} refuses to surrender after {quota} cities — "
            f"wildfires accelerate"
        )
        self.planet.accelerate_wildfire()

    def _begin_surrender(self):
        """Planet folds — show SURRENDER, then mission_done → new world."""
        world = str(getattr(self.planet, "name", "WORLD")).upper()
        self.surrendered = True
        self.phase = "surrender"
        self.phase_t = 0.0
        self.bombs = []
        self.blasts = []
        self.bomb_cd = 999.0
        self.clock_text = ""
        self.cruise_stream = ""
        self.cruise_ticker_queue = []
        self.hud_text = "SURRENDER"
        self.hud_rgb = HUD_ALERT_RGB
        # Pull back slightly so the surface reads as "leaving station"
        self.alt_from = float(self.alt_ft)
        self.alt_to = max(
            float(self.alt_ft) * 2.2,
            _alt_for_city_pixels(self.city, self.h, CITY_WIDE_PX) * 1.4,
        )
        print(
            f"[PlanetBlast] *** {world} HAS SURRENDERED ***  "
            f"after {self.cities_bombed} cities  "
            f"(quota was {getattr(self, 'surrender_quota', '?')})  "
            f"— leaving orbit for next planet"
        )

    def _update_surrender(self, dt):
        """Hold SURRENDER banner, climb, then flag mission complete."""
        self.phase_t += dt
        self.alt_ft = _lerp(
            self.alt_from, self.alt_to,
            _smoothstep(min(1.0, self.phase_t / max(0.8, SURRENDER_SHOW_SEC * 0.65))),
        )
        self.heading += 0.02 * dt
        self.hud_text = "SURRENDER"
        self.hud_rgb = HUD_ALERT_RGB
        self.clock_text = ""
        if self.phase_t >= SURRENDER_SHOW_SEC:
            self.mission_done = True
            print("[PlanetBlast] Leaving system — searching for next hostile world…")

    def _globe_max_r_for_planet(self):
        """Full-planet disc radius (same formula as SpaceIntro briefing/hold)."""
        return _full_planet_disc_r(
            self.w, self.h,
            size_scale=float(getattr(self.planet, "size_scale", 1.0)),
        )

    def _begin_first_approach(self, city, globe_r=None, start_mpp=None):
        """
        City already picked. Hold full globe with clock + WARCOM chatter until
        the attack order scrolls — only then dive to strike altitude.
        """
        if city is None:
            city = self.planet.pick_showcase_city()
        self.city = city
        self.strike_city = city
        self.next_city = city
        self.x = float(city["x"])
        self.y = float(city["y"])
        # Fixed heading matches sphere local UV (see _render_globe blend axes)
        self.heading = -math.pi * 0.5
        self._orbit_dive_heading_set = True
        lon, lat = self._world_to_lon_lat(city["x"], city["y"])
        self.orbit_lon = lon
        self.orbit_lat = lat
        self.orbit_lon0 = lon
        self.orbit_lat0 = lat
        self.orbit_lon1 = lon
        self.orbit_lat1 = lat
        self.orbit_spin_dir = 1.0 if random.random() < 0.5 else -1.0
        self.orbit_spin_amt = ORBIT_SPIN_RAD * 0.35
        self.orbit_limb_flat = 0.0
        # Same full-planet disc as intro briefing (shared _full_planet_disc_r)
        self.orbit_r_full = self._globe_max_r_for_planet()
        if globe_r is not None and float(globe_r) > 2.0:
            # Prefer handoff r if it matches the shared formula (within 1px)
            if abs(float(globe_r) - self.orbit_r_full) < 1.5:
                self.orbit_r_full = float(globe_r)
        world_r = float(getattr(self.planet, "R", PLANET_R) or PLANET_R)
        # Sphere FOV: mpp = R / r (not aircraft altitude — that misleads logs)
        mpp_globe = world_r / max(self.orbit_r_full, 0.5)
        self.orbit_mpp0 = mpp_globe
        self.orbit_mpp1 = mpp_globe
        self.orbit_mpp = mpp_globe
        self.orbit_r = float(self.orbit_r_full)
        self.orbit_px = self.w * 0.5
        self.orbit_py = self.h * 0.5
        self.orbit_local_blend = 0.0
        self.orbit_use_surface = False
        self.orbit_picked = True
        self.alt_wide = _alt_for_city_pixels(city, self.h, CITY_WIDE_PX)
        self.alt_close = _alt_for_city_pixels(city, self.h, CITY_TARGET_PX)
        # Keep a strike-ready alt; globe phases log r/mpp, not this fake FOV alt
        self.alt_ft = float(self.alt_close)
        self.alt_from = float(self.alt_ft)
        self.alt_to = float(self.alt_close)
        self.bombs = []
        self.blasts = []
        self.bomb_cd = 999.0
        self.clock_text = ""
        self.hud_text = ""
        self.hud_rgb = HUD_RGB
        self.cruise_stream = ""
        self.cruise_scroll_x = float(self.w)
        self._scroll_accum = 0.0
        self.cruise_ticker_queue = []
        # Hold at planet level — do NOT dive until WARCOM attack order
        self.phase = "orbit_hold"
        self.phase_t = 0.0
        self._first_approach = True
        self._cruise_refill_ticker(force=True)
        # Reuse shared starfield only — never build a second SpaceParallax here
        day0 = self.planet.day_factor_flat(city["x"], city["y"])
        print(
            f"[PlanetBlast] Orbit hold — {_city_display_name(city)}  "
            f"size={city.get('size')}  day={day0:.2f}  "
            f"chatter {ORBIT_HOLD_SEC:.0f}s then WARCOM order → dive"
        )

    def _unwrap_lon(self, current, target):
        """Return target longitude unwrapped so the path from current is shortest."""
        d = (float(target) - float(current) + math.pi) % (math.pi * 2) - math.pi
        return float(current) + d

    def _set_dive_facing_targets(self, city):
        """
        Aim the globe at city without snapping: keep current lon/lat and set
        continuous lon1/lat1 for a smooth slew during the dive.
        """
        tlon, tlat = self._world_to_lon_lat(city["x"], city["y"])
        cur_lon = float(getattr(self, "orbit_lon", tlon))
        cur_lat = float(getattr(self, "orbit_lat", tlat))
        self.orbit_lon0 = cur_lon
        self.orbit_lat0 = cur_lat
        self.orbit_lon1 = self._unwrap_lon(cur_lon, tlon)
        self.orbit_lat1 = float(tlat)
        # Leave orbit_lon/lat at current — dive update eases toward lon1/lat1

    def _cam_for_city_under_crosshair(self, city, mpp=None):
        """
        Surface camera pose so the city sits under the reticle (not dead center).
        Matches bomb/zoom_in framing to avoid a handoff jump.
        """
        if mpp is None:
            mpp = self._mpp()
        hdg = -math.pi * 0.5
        cos_h = math.cos(hdg)
        sin_h = math.sin(hdg)
        fwd = float(CROSSHAIR_UP_PX) * float(mpp)
        cx = float(city["x"])
        cy = float(city["y"])
        return (
            cx - cos_h * fwd,
            cy - sin_h * fwd,
            hdg,
        )

    def _begin_first_dive(self):
        """WARCOM authorized — continuous dive to the pick city, then fire."""
        city = self.next_city or self.city or self.strike_city
        if city is None:
            city = self.planet.pick_showcase_city()
        self.city = city
        self.strike_city = city
        self.next_city = city
        # Surface pose ready for late-dive handoff (city under crosshair)
        mpp0 = float(getattr(self, "orbit_mpp0", self._mpp()) or self._mpp())
        self.x, self.y, self.heading = self._cam_for_city_under_crosshair(city, mpp0)
        # Do NOT snap globe facing to the city — slew smoothly from hold spin
        self._set_dive_facing_targets(city)
        self.orbit_local_blend = 0.0
        self.orbit_use_surface = False
        self.orbit_r = float(self.orbit_r_full)
        self.orbit_mpp = float(self.orbit_mpp0)
        self._orbit_dive_heading_set = True
        self.aim_err_x = 0.0
        self.aim_err_y = 0.0
        self.phase = "orbit_in"
        self.phase_t = 0.0
        self._first_approach = True
        self.clock_text = ""
        self.cruise_stream = ""
        self.cruise_ticker_queue = []
        self.hud_text, self.hud_rgb = "SCAN", HUD_RGB
        print(
            f"[PlanetBlast] WARCOM GO — diving to {_city_display_name(city)}  "
            f"→ strike @ {self.alt_close:.0f} ft"
        )

    def _hold_full_planet_view(self, dt, spin_rate=0.14):
        """
        Whole-planet disc + slow free rotation (no zoom, no city lock-on).
        Used during orbit_hold and first-mission WARCOM authorization.
        """
        # Continuous slow spin — do not lerp back to the pick city (that killed
        # the rotation and made the hold feel stuck / half-zoomed).
        spin = float(spin_rate) * float(getattr(self, "orbit_spin_dir", 1.0))
        self.orbit_lon += spin * dt
        # Gentle latitude bob so the view isn't a fixed equator band
        bob = 0.04 * math.sin(self.t * 0.35)
        lat0 = float(getattr(self, "orbit_lat0", 0.0))
        self.orbit_lat = _clamp(lat0 + bob, -0.55, 0.55)
        # Full globe only — same radius as intro handoff
        self.orbit_r = float(self.orbit_r_full)
        self.orbit_local_blend = 0.0
        self.orbit_use_surface = False
        self.orbit_px = self.w * 0.5
        self.orbit_py = self.h * 0.5
        if getattr(self, "orbit_mpp0", None) is not None:
            self.orbit_mpp = float(self.orbit_mpp0)
        # Do not map globe mpp → aircraft altitude (that made ~14M ft logs)

    def _update_orbit_hold(self, dt):
        """
        Full-planet hold: whole world slowly rotating + clock + WARCOM chatter.
        Does not dive until hold time elapses → attack order → dive.
        """
        self._hold_full_planet_view(dt, spin_rate=0.14)
        lt = time.localtime()
        self.clock_text = f"{lt.tm_hour:02d}:{lt.tm_min:02d}"
        self.hud_text = ""
        self.hud_rgb = HUD_RGB
        self._update_cruise_ticker(dt)
        if self._orbit_space is not None:
            self._orbit_space.update(dt, streak=0.08)
        if self.phase_t >= ORBIT_HOLD_SEC:
            self.clock_text = ""
            self.cruise_stream = ""
            self._end_opening_cruise()

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

    def _city_on_side(self, city, side):
        d = self.planet.day_factor_flat(city["x"], city["y"])
        if side == "night":
            return d <= NIGHT_DAY_MAX
        return d >= DAY_DAY_MIN

    def _pick_next_city(self, count_kill=True):
        """
        Next bomb target from the current batch side (night or day).
        Prefers a nearby intact city so zoom-out → cruise_to feels continuous.
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
            # Restore baked city paint + clear burn frontier for the next tour
            self.planet.fire_scorch.clear()
            self.planet.fire_front = []
            self.planet._bake_all_cities()
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
            if c is not self.city and self._city_on_side(c, side)
        ]
        if not side_left and len(alive) > 1:
            other = "day" if side == "night" else "night"
            print(
                f"[PlanetFly] No more {side} cities — early switch to {other.upper()}"
            )
            self.batch_side = other
            self.batch_done = 0
            side = other

        # Rank by distance from current camera — nearby first
        ox, oy = float(self.x), float(self.y)
        ranked = []
        for c in alive:
            if c is self.city:
                continue
            if not self._city_on_side(c, side):
                continue
            d = math.hypot(float(c["x"]) - ox, float(c["y"]) - oy)
            if d < NEXT_MIN_SEP_M:
                continue
            unvis = 1 if id(c) not in self.visited else 0
            # Closer is better; small bonuses for unvisited + larger cities
            score = (
                d
                - unvis * 45_000.0
                - float(c.get("size", 1)) * 10_000.0
                + random.uniform(0.0, 18_000.0)
            )
            ranked.append((score, d, c))

        if not ranked:
            # Fallback: any intact on side (or any alive) without min-sep filter
            pool = [
                c for c in alive
                if c is not self.city and self._city_on_side(c, side)
            ] or [c for c in alive if c is not self.city] or alive
            return random.choice(pool)

        ranked.sort(key=lambda t: t[0])
        # Weighted pick among the nearest handful (still local, not globe-hopping)
        near = ranked[: max(1, min(5, len(ranked)))]
        weights = []
        for _score, d, _c in near:
            weights.append(1.0 / (1.0 + d / 80_000.0))
        total_w = sum(weights) or 1.0
        r = random.random() * total_w
        acc = 0.0
        nxt = near[0][2]
        for (_score, d, c), w in zip(near, weights):
            acc += w
            if r <= acc:
                nxt = c
                break
        dist_km = math.hypot(float(nxt["x"]) - ox, float(nxt["y"]) - oy) / 1000.0
        print(
            f"[PlanetFly] Next target nearby: {_city_display_name(nxt)}  "
            f"~{dist_km:.0f} km  side={side}"
        )
        return nxt

    def _steer_toward(self, wx, wy, dt, turn_rate=0.55):
        """Bank heading toward a world point (gentle; no whip turns)."""
        dx = float(wx) - self.x
        dy = float(wy) - self.y
        dist = math.hypot(dx, dy)
        if dist < 500.0:
            return dist
        desired = math.atan2(dy, dx)
        err = (desired - self.heading + math.pi) % (math.pi * 2) - math.pi
        rate = min(float(turn_rate), 0.40)
        self.heading += _clamp(err, -rate * dt, rate * dt)
        return dist

    def _fly_forward(self, dt, span_frac, max_mps=None):
        """Advance along heading; optional hard cap so transit never warps."""
        speed = self._mpp() * self.h * CRUISE_SPAN_PER_SEC * span_frac
        if max_mps is not None:
            speed = min(speed, float(max_mps))
        self.x += math.cos(self.heading) * speed * dt
        self.y += math.sin(self.heading) * speed * dt

    def _cruise_toward(self, wx, wy, dt, speed_mps=CRUISE_TO_MPS, turn_rate=0.5):
        """
        Fly to a world point without pursuit circles.
        Far: soft bank + forward flight.
        Near: lock heading at the target and slide straight in (or pure nudge).
        Returns remaining distance (m).
        """
        tx, ty = float(wx), float(wy)
        dx = tx - self.x
        dy = ty - self.y
        dist = math.hypot(dx, dy)
        if dist < 200.0:
            return dist

        # --- Always soft-bank toward target (never snap heading = map spin jump) ---
        TERMINAL_M = 100_000.0
        DIRECT_M = 70_000.0
        desired = math.atan2(dy, dx)
        err = (desired - self.heading + math.pi) % (math.pi * 2) - math.pi
        # Closer → allow faster bank, but still rate-limited (no 1-frame spin)
        if dist <= DIRECT_M:
            rate = max(float(turn_rate), 0.85)
        elif dist <= TERMINAL_M:
            rate = max(float(turn_rate), 0.55)
        else:
            rate = min(float(turn_rate), 0.32)
        # Stuck-orbit recovery: still bank hard, never teleport heading
        last = getattr(self, "_cruise_prev_dist", None)
        if last is not None and dist > last * 0.998 and self.phase_t > 1.5:
            rate = max(rate, 0.90)
        self.heading += _clamp(err, -rate * dt, rate * dt)
        self._cruise_prev_dist = dist

        if dist <= DIRECT_M:
            spd = min(float(speed_mps) * 0.55, dist / max(dt, 1e-3) * 0.9)
            self._nudge_toward(tx, ty, dt, max_mps=max(spd, 1.0))
            return math.hypot(tx - self.x, ty - self.y)

        if dist <= TERMINAL_M:
            spd = float(speed_mps) * _clamp(0.40 + 0.50 * (dist / TERMINAL_M), 0.40, 0.90)
            step = min(spd * dt, max(0.0, dist - 120.0))
            self.x += math.cos(self.heading) * step
            self.y += math.sin(self.heading) * step
            return max(0.0, dist - step)

        # Far: only fly forward if roughly pointed at target (avoid side-slip circles)
        abs_err = abs((desired - self.heading + math.pi) % (math.pi * 2) - math.pi)
        if abs_err > 0.55:
            step = min(float(speed_mps) * 0.12 * dt, dist * 0.05)
        else:
            step = min(float(speed_mps) * dt, max(0.0, dist - 150.0))
        self.x += math.cos(self.heading) * step
        self.y += math.sin(self.heading) * step
        return math.hypot(tx - self.x, ty - self.y)

    def _nudge_toward(self, wx, wy, dt, max_mps=ZOOM_TRACK_MPS):
        """Rate-limited position nudge (fine aim only — no map jumps)."""
        dx = float(wx) - self.x
        dy = float(wy) - self.y
        d = math.hypot(dx, dy)
        if d < 1.0:
            return 0.0
        step = min(float(max_mps) * dt, d)
        self.x += dx * (step / d)
        self.y += dy * (step / d)
        return d - step

    def _begin_cruise_to(self, city):
        """
        Silent transit to a nearby city. Short hops stay at strike altitude;
        if ETA at strike speed would exceed ~10s, climb and dash faster, then
        descend for SCAN→LOCK→FIRE.
        """
        if city is None:
            city = self._pick_next_city(count_kill=False)
        self.next_city = city
        self.strike_city = city
        self.phase = "cruise_to"
        self.phase_t = 0.0
        self.bombs = []
        self.blasts = []
        self.bomb_cd = 999.0
        # Remember strike altitude to return to before the next bomb run
        hold_alt = float(self.alt_ft) if self.alt_ft > 1000.0 else float(self.alt_close)
        self._strike_hold_alt = hold_alt
        self.alt_close = hold_alt
        dist_m = math.hypot(
            float(city["x"]) - self.x, float(city["y"]) - self.y,
        )
        base_speed = CRUISE_TO_MPS  # full strike-alt cruise (was 0.55× — felt crawl-y)
        eta = dist_m / max(1.0, base_speed)
        if eta > CRUISE_TO_MAX_SEC:
            # Long hop: climb for a wider view and cover ground faster
            self._cruise_high = True
            overview = _alt_for_city_pixels(city, self.h, CITY_WIDE_PX)
            # Climb enough to read the trip, but cap so the map stays readable
            self._cruise_transit_alt = min(
                max(overview * 1.25, hold_alt * 2.4, 400_000.0),
                max(hold_alt * 4.5, 1_200_000.0),
                2_200_000.0,
            )
            # Aim to arrive in ~CRUISE_TO_MAX_SEC (leave a little for climb/descent)
            need_mps = dist_m / max(3.0, CRUISE_TO_MAX_SEC * 0.65)
            self._cruise_speed = min(
                CRUISE_TO_FAST_MPS,
                max(base_speed * 1.6, need_mps),
            )
            self.alt_wide = float(self._cruise_transit_alt)
            # Start climbing immediately (smooth lerp in update)
            mode = (
                f"HIGH DASH ~{self._cruise_speed / 1000.0:.0f} km/s  "
                f"alt→{self._cruise_transit_alt:.0f} ft"
            )
        else:
            self._cruise_high = False
            self._cruise_transit_alt = hold_alt
            self._cruise_speed = base_speed
            self.alt_wide = hold_alt
            self.alt_ft = hold_alt
            mode = f"LOW ~{base_speed / 1000.0:.0f} km/s  alt={hold_alt:.0f} ft"
        # Do NOT snap heading here — map would spin in one frame. Bank in update.
        self._cruise_prev_dist = dist_m
        # Silent transit — no marquee, no clock, no mid-screen labels
        self.hud_text = ""
        self.hud_rgb = HUD_RGB
        self.clock_text = ""
        self.cruise_stream = ""
        self.cruise_ticker_queue = []
        self.cruise_scroll_x = float(self.w)
        self._scroll_accum = 0.0
        print(
            f"[PlanetBlast] Next nearby — {_city_display_name(city)}  "
            f"~{dist_m / 1000.0:.0f} km  ETA@strike={eta:.1f}s  ({mode})"
        )

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
        """Resume strike package after patrol window — globe orbit to next tgt."""
        print("[PlanetBlast] === PATROL complete — orbital search for next target ===")
        self.since_patrol = 0
        self.clock_text = ""
        self.cruise_stream = ""
        self._begin_globe_search(count_kill=False)

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

    def _log_alt_if_changed(self):
        """
        Log altitude when it changes (surface flight), or globe disc radius
        during orbit phases (aircraft alt is meaningless on the sphere).
        """
        phase = str(getattr(self, "phase", "?"))
        if phase in (
            "orbit_hold", "orbit_turn", "orbit_in", "orbit_out", "warcom_order",
        ):
            r = float(getattr(self, "orbit_r", 0.0) or 0.0)
            mpp = getattr(self, "orbit_mpp", None)
            if mpp is None:
                world_r = float(getattr(self.planet, "R", PLANET_R) or PLANET_R)
                mpp = world_r / max(r, 0.5)
            else:
                mpp = float(mpp)
            key = (round(r, 1), round(mpp, 0), phase)
            if key == getattr(self, "_log_zoom_prev", None):
                return
            self._log_zoom_prev = key
            print(
                f"[PlanetBlast] zoom r={r:.1f}px  mpp={mpp:.0f}  phase={phase}"
            )
            return

        alt = float(getattr(self, "alt_ft", 0.0) or 0.0)
        prev = getattr(self, "_log_alt_prev", None)
        thr = max(500.0, abs(prev) * 0.01) if prev is not None else 0.0
        if prev is not None and abs(alt - prev) < thr:
            return
        self._log_alt_prev = alt
        print(f"[PlanetBlast] alt={alt:.0f} ft  phase={phase}")

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

    def _city_on_screen(self, city, margin_px=1.0):
        """True if any of the city footprint intersects the panel."""
        if not city:
            return False
        sx, sy = self._world_to_screen(float(city["x"]), float(city["y"]))
        r_px = _city_radius_m(city) / max(1.0, self._mpp())
        r_px = max(0.5, r_px)
        return (
            sx + r_px >= -margin_px
            and sx - r_px < self.w + margin_px
            and sy + r_px >= -margin_px
            and sy - r_px < self.h + margin_px
        )

    def _target_label(self, city):
        """HUD line: TARGET: CITYNAME (fitted to panel width)."""
        name = _city_display_name(city)
        return _hud_fit(f"TARGET: {name}", max(8, self.w - 2))

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
        """
        Start altitude zoom + reticle fine-track. Camera x/y stay put —
        caller must already have cruised near the city (no teleports).
        """
        self.city = city
        self.strike_city = city
        self.next_city = None
        self.city["damage"] = float(self.city.get("damage", 0.0))
        self.city["obliterated"] = bool(self.city.get("obliterated", False))
        self._mark_visited(city)
        self.phase = "zoom_in"
        self.phase_t = 0.0
        self.alt_wide = _alt_for_city_pixels(city, self.h, CITY_WIDE_PX)
        self.alt_close = _alt_for_city_pixels(city, self.h, CITY_TARGET_PX)
        # Descend from wherever we are — never snap altitude or position
        self.alt_from = float(self.alt_ft)
        self.alt_to = float(self.alt_close)
        self.bombs = []
        self.blasts = []
        self.bomb_cd = 0.4
        # No aim teleport on acquire — wander builds up during zoom_in/bomb
        self.aim_err_x = 0.0
        self.aim_err_y = 0.0
        self.hud_text = "SCAN"
        self.hud_rgb = HUD_RGB
        self.clock_text = ""  # no clock during strike acquire/bomb
        self.cruise_stream = ""  # no chatter during acquire/fire
        self.cruise_ticker_queue = []
        day0 = self.planet.day_factor_flat(city["x"], city["y"])
        n = self.batch_done + 1  # current is next slot in batch
        cname = _city_display_name(city)
        print(
            f"[PlanetBlast] {self.batch_side.upper()} batch {n}/{TARGETS_PER_BATCH}  "
            f"city={cname} size={city['size']}  day={day0:.2f}  "
            f"→ ~{CITY_TARGET_PX:.0f}px @ {self.alt_close:.0f} ft"
        )

    def _globe_max_r(self):
        """Pixel radius so the whole planet fits on the panel with a little rim."""
        return min(self.w, self.h) * 0.48

    def _world_to_lon_lat(self, wx, wy):
        world_r = float(getattr(self.planet, "R", PLANET_R) or PLANET_R)
        lon = float(wx) / world_r
        lat = _clamp(float(wy) / world_r, -1.15, 1.15)
        return lon, lat

    def _begin_globe_search(self, count_kill=True):
        """
        After a strike (or patrol): smooth climb from surface map to full-planet
        globe, orbit, pick next target, then dive back. No hard cuts.

        One PlanetMap; FOV uses identity mpp = R / disc_r so surface→sphere
        handoff does not change scale when the projection switches.
        """
        self._orbit_count_kill = bool(count_kill)
        lon0, lat0 = self._world_to_lon_lat(self.x, self.y)
        self.orbit_lon = lon0
        self.orbit_lat = lat0
        self.orbit_lon0 = lon0
        self.orbit_lat0 = lat0
        self.orbit_lon1 = lon0
        self.orbit_lat1 = lat0
        self.orbit_spin_dir = 1.0 if random.random() < 0.5 else -1.0
        self.orbit_spin_amt = ORBIT_SPIN_RAD * random.uniform(0.85, 1.25)
        # Same full-planet disc as intro / first approach (size_scale aware)
        self.orbit_r_full = self._globe_max_r_for_planet()
        world_r = float(getattr(self.planet, "R", PLANET_R) or PLANET_R)
        # Start from current surface FOV; end at full-globe FOV (R / r_full)
        self.orbit_mpp0 = max(self._mpp(), 500.0)
        self.orbit_mpp1 = world_r / max(self.orbit_r_full, 0.5)
        self.orbit_mpp = float(self.orbit_mpp0)
        # Disc radius always tracks FOV identity (huge when low / close)
        self.orbit_r = world_r / max(self.orbit_mpp, 1.0)
        self.orbit_px = self.w * 0.5
        self.orbit_py = self.h * 0.5
        self.orbit_local_blend = 1.0   # start as flat map over current site
        self.orbit_use_surface = True  # surface raster first, then globe
        self.orbit_picked = False
        self._orbit_dive_heading_set = False
        self.next_city = None
        self.bombs = []
        self.blasts = []
        self.bomb_cd = 999.0
        self.clock_text = ""
        self.hud_text = "ORBIT"
        self.hud_rgb = HUD_RGB
        self.alt_from = float(self.alt_ft)
        self.alt_to = self._alt_from_mpp(self.orbit_mpp1)
        # Keep existing shared starfield (_orbit_space); do not construct another
        self.phase = "orbit_out"
        self.phase_t = 0.0
        print(
            f"[PlanetBlast] Climbing to orbit — smooth pullback to full planet "
            f"(then rotate / pick next target)"
        )

    def _pick_orbit_target(self):
        """
        Choose next strike city for globe search — prefer distant unvisited
        targets so the orbit rotation is visible and dramatic.
        """
        # Register batch advance when coming from a kill
        if getattr(self, "_orbit_count_kill", False):
            self._orbit_count_kill = False
            self._advance_batch_after_kill()

        alive = self._intact_cities()
        if not alive:
            # All destroyed — reset world (same as surface picker)
            return self._pick_next_city(count_kill=False)

        side = self.batch_side
        side_left = [
            c for c in alive
            if c is not self.city and self._city_on_side(c, side)
        ]
        if not side_left and len(alive) > 1:
            other = "day" if side == "night" else "night"
            print(
                f"[PlanetFly] No more {side} cities — early switch to {other.upper()}"
            )
            self.batch_side = other
            self.batch_done = 0
            side = other
            side_left = [
                c for c in alive
                if c is not self.city and self._city_on_side(c, side)
            ]

        pool = side_left or [c for c in alive if c is not self.city] or alive
        ox, oy = float(self.x), float(self.y)
        scored = []
        for c in pool:
            d = math.hypot(float(c["x"]) - ox, float(c["y"]) - oy)
            if d < NEXT_MIN_SEP_M:
                continue
            unvis = 1 if id(c) not in self.visited else 0
            # Prefer far + unvisited + larger (dramatic globe hop)
            score = (
                d
                + unvis * 120_000.0
                + float(c.get("size", 1)) * 25_000.0
                + random.uniform(0.0, 40_000.0)
            )
            scored.append((score, d, c))
        if not scored:
            return random.choice(pool)
        scored.sort(key=lambda t: -t[0])
        top = scored[: max(2, min(6, len(scored)))]
        city = random.choice(top)[2]
        dist_km = math.hypot(float(city["x"]) - ox, float(city["y"]) - oy) / 1000.0
        print(
            f"[PlanetFly] Orbit target: {_city_display_name(city)}  "
            f"~{dist_km:.0f} km  side={side}"
        )
        return city

    def _update_orbit_out(self, dt):
        """
        Smooth reverse of the dive: surface zoom-out, then sphere with the
        same FOV identity (mpp = R / disc_r). Heading eases to sphere UV axes
        before the projection switch so landmasses don't spin/jump.
        """
        u_lin = _clamp(self.phase_t / max(0.05, ORBIT_OUT_SEC), 0.0, 1.0)
        flat_u = ORBIT_OUT_FLAT_U
        mpp0 = float(getattr(self, "orbit_mpp0", self._mpp()))
        mpp1 = float(getattr(self, "orbit_mpp1", mpp0 * 8.0))
        world_r = float(getattr(self.planet, "R", PLANET_R) or PLANET_R)
        # Continuous FOV climb for the whole pullback (no mid-stage mpp kink)
        ease = u_lin * u_lin * (3.0 - 2.0 * u_lin)
        self.orbit_mpp = _lerp(mpp0, mpp1, ease)
        # Disc radius always matches sphere FOV identity
        self.orbit_r = world_r / max(float(self.orbit_mpp), 1.0)
        self.alt_ft = self._alt_from_mpp(self.orbit_mpp)

        # Ease heading toward sphere local UV (-π/2) so flat→sphere axes match
        target_h = -math.pi * 0.5
        herr = (target_h - self.heading + math.pi) % (math.pi * 2) - math.pi
        self.heading += _clamp(herr, -0.55 * dt, 0.55 * dt)

        # Keep sphere facing locked on camera center (no lon snap later)
        self.orbit_lon0, self.orbit_lat0 = self._world_to_lon_lat(self.x, self.y)

        if u_lin < flat_u:
            # Stage A — top-down surface zoom-out only
            self.orbit_local_blend = 1.0
            self.orbit_use_surface = True
            self.orbit_lon = self.orbit_lon0
            self.orbit_lat = self.orbit_lat0
            self.orbit_limb_flat = 1.0
        else:
            # Stage B — sphere at matched FOV; start spin once projection is on
            t = _smoothstep((u_lin - flat_u) / max(0.05, 1.0 - flat_u))
            # Switch as soon as stage B starts (FOV already continuous via mpp)
            self.orbit_use_surface = False
            self.orbit_local_blend = 0.0
            self.orbit_limb_flat = max(0.0, 1.0 - t)
            # Snap heading fully once on sphere (axes already near target)
            if t > 0.05:
                self.heading = target_h
            self.orbit_lon = (
                self.orbit_lon0
                + self.orbit_spin_dir * self.orbit_spin_amt * t * 0.4
            )
            self.orbit_lat = self.orbit_lat0
            # Clamp disc to full-planet size once we reach it (don't overshoot)
            self.orbit_r = max(float(self.orbit_r_full), min(
                float(self.orbit_r), world_r / max(mpp0, 1.0),
            ))
            if self.orbit_mpp >= mpp1 * 0.98:
                self.orbit_r = float(self.orbit_r_full)
                self.orbit_mpp = mpp1

        self.orbit_px = self.w * 0.5
        self.orbit_py = self.h * 0.5
        self.hud_text, self.hud_rgb = "ORBIT", HUD_RGB
        if self._orbit_space is not None:
            star_u = 0.0 if self.orbit_use_surface else (
                _smoothstep((u_lin - flat_u) / max(0.05, 1.0 - flat_u))
            )
            self._orbit_space.update(dt, streak=0.1 + 0.2 * star_u)
        if self.phase_t >= ORBIT_OUT_SEC:
            self.orbit_r = float(self.orbit_r_full)
            self.orbit_local_blend = 0.0
            self.orbit_limb_flat = 0.0
            self.orbit_mpp = mpp1
            self.orbit_use_surface = False
            self.heading = -math.pi * 0.5
            self.phase = "orbit_turn"
            self.phase_t = 0.0
            self.orbit_lon0 = self.orbit_lon
            self.orbit_lat0 = self.orbit_lat
            print("[PlanetBlast] Full planet locked — scanning for next target")

    def _update_orbit_turn(self, dt):
        """Rotate around the planet; pick next target mid-orbit and face it."""
        u = _smoothstep(min(1.0, self.phase_t / max(0.05, ORBIT_TURN_SEC)))
        pick_at = 0.38
        if not self.orbit_picked and u >= pick_at:
            city = self._pick_orbit_target()
            self.next_city = city
            self.strike_city = city
            self.orbit_picked = True
            # Freeze free-spin origin at current facing, aim at new city
            self.orbit_lon0 = self.orbit_lon
            self.orbit_lat0 = self.orbit_lat
            self.orbit_lon1, self.orbit_lat1 = self._world_to_lon_lat(
                city["x"], city["y"],
            )
            # Prefer continuing the spin direction for a dramatic approach
            dlon = self.orbit_lon1 - self.orbit_lon0
            while self.orbit_spin_dir > 0 and dlon < 0.4:
                self.orbit_lon1 += math.pi * 2
                dlon = self.orbit_lon1 - self.orbit_lon0
            while self.orbit_spin_dir < 0 and dlon > -0.4:
                self.orbit_lon1 -= math.pi * 2
                dlon = self.orbit_lon1 - self.orbit_lon0
            print(
                f"[PlanetBlast] Orbital lock → {_city_display_name(city)}  "
                f"size={city.get('size')}  side={self.batch_side}"
            )
        if not self.orbit_picked:
            # Free spin away from the crater
            spin_u = min(1.0, u / max(0.05, pick_at))
            self.orbit_lon = (
                self.orbit_lon0
                + self.orbit_spin_dir * self.orbit_spin_amt * spin_u
            )
            self.hud_text, self.hud_rgb = "SCAN", HUD_RGB
        else:
            # Ease facing toward the chosen city
            t = _smoothstep((u - pick_at) / max(0.05, 1.0 - pick_at))
            self.orbit_lon = _lerp(self.orbit_lon0, self.orbit_lon1, t)
            self.orbit_lat = _lerp(self.orbit_lat0, self.orbit_lat1, t)
            name = _hud_fit(
                _city_display_name(self.next_city), max(8, self.w - 2),
            )
            self.hud_text, self.hud_rgb = name, HUD_NAME_RGB
        self.orbit_r = self.orbit_r_full
        self.orbit_local_blend = 0.0
        if self._orbit_space is not None:
            self._orbit_space.update(dt, streak=0.25)
        if self.phase_t >= ORBIT_TURN_SEC:
            if self.next_city is None:
                self.next_city = self._pick_orbit_target()
                self.orbit_picked = True
            # Keep continuous facing into the dive (no lon re-wrap snap)
            self._set_dive_facing_targets(self.next_city)
            # If turn already finished facing the city, lon≈lon1 — no visible move
            self.aim_err_x = 0.0
            self.aim_err_y = 0.0
            self.orbit_use_surface = False
            self.phase = "orbit_in"
            self.phase_t = 0.0
            print(
                f"[PlanetBlast] Diving to surface — {_city_display_name(self.next_city)}"
            )

    def _alt_from_mpp(self, mpp):
        """Altitude (ft) for a given meters-per-pixel ground scale."""
        span = float(mpp) * float(max(1, self.h))
        alt_m = span / (2.0 * math.tan(math.radians(_FOV_DEG) * 0.5))
        return max(20_000.0, alt_m / 0.3048)

    def _city_is_night(self, city):
        """True night only (not twilight, not day) — NV applies here."""
        if not city:
            return False
        d = self.planet.day_factor_flat(float(city["x"]), float(city["y"]))
        return d < NV_NIGHT_MAX

    def _update_orbit_in(self, dt):
        """
        Continuous dive on ONE PlanetMap.

        Early: sphere zoom while facing slews smoothly onto the city
        (no lon re-wrap snap toward principal range).

        Late: when the disc overfills the panel, switch to the flat surface
        raster at the same mpp with the city already under the crosshair —
        so weapons-free is the same projection (no end-of-dive map jump).
        """
        city = self.next_city
        if city is None:
            city = self._pick_orbit_target()
            self.next_city = city
            self._set_dive_facing_targets(city)

        # Continuous facing targets (set at dive start; never re-principalize)
        if not hasattr(self, "orbit_lon1") or self.orbit_lon1 is None:
            self._set_dive_facing_targets(city)
        tlon = float(self.orbit_lon1)
        tlat = float(self.orbit_lat1)

        diameter = 2.0 * _city_radius_m(city)
        mpp_close = diameter / max(1.5, CITY_TARGET_PX)
        world_r = float(getattr(self.planet, "R", PLANET_R) or PLANET_R)
        first = getattr(self, "_first_approach", False)
        if first and getattr(self, "orbit_mpp0", None) is not None:
            mpp_orbit = float(self.orbit_mpp0)
        else:
            mpp_orbit = world_r / max(float(self.orbit_r_full), 0.5)

        u_lin = _clamp(self.phase_t / max(0.05, ORBIT_IN_SEC), 0.0, 1.0)
        ease = u_lin * u_lin * (3.0 - 2.0 * u_lin)

        # FOV: continuous sphere identity mpp = R / r
        mpp_start = max(float(mpp_orbit), float(mpp_close))
        self.orbit_mpp = _lerp(mpp_start, mpp_close, ease)
        self.orbit_r = world_r / max(float(self.orbit_mpp), 1.0)
        self.orbit_local_blend = 0.0
        self.orbit_limb_flat = ease
        self.orbit_px = self.w * 0.5
        self.orbit_py = self.h * 0.5

        # Slew facing onto the city early, then lock (no principal-lon snap)
        face_k = min(1.0, 3.5 * dt)
        # Finish facing by ~40% of the dive so the zoom is on-target
        face_u = _smoothstep(min(1.0, u_lin / 0.40))
        self.orbit_lon = _lerp(float(self.orbit_lon0), tlon, face_u)
        self.orbit_lat = _lerp(float(self.orbit_lat0), tlat, face_u)
        # Also exponential settle so we never freeze short of the target
        self.orbit_lon += (tlon - self.orbit_lon) * face_k * face_u
        self.orbit_lat += (tlat - self.orbit_lat) * face_k * face_u

        # Late dive: overfilled disc → flat surface at same FOV (bomb path)
        panel_diag = math.hypot(self.w, self.h)
        surface_ready = (
            float(self.orbit_r) >= panel_diag * 0.92
            or ease >= 0.70
        )
        if surface_ready:
            self.orbit_use_surface = True
            self.orbit_limb_flat = 1.0
            self.heading = -math.pi * 0.5
            self._orbit_dive_heading_set = True
            # City under crosshair every frame (matches bomb framing)
            self.x, self.y, self.heading = self._cam_for_city_under_crosshair(
                city, self.orbit_mpp,
            )
        else:
            self.orbit_use_surface = False
            # Pre-position surface cam so the switch frame is already correct
            self.x, self.y, hdg = self._cam_for_city_under_crosshair(
                city, self.orbit_mpp,
            )
            if not getattr(self, "_orbit_dive_heading_set", False):
                self.heading = hdg
                self._orbit_dive_heading_set = True

        self.alt_wide = _alt_for_city_pixels(city, self.h, CITY_WIDE_PX)
        self.alt_close = self._alt_from_mpp(mpp_close)
        self.alt_ft = self._alt_from_mpp(self.orbit_mpp)
        self.aim_err_x = 0.0
        self.aim_err_y = 0.0

        name = _hud_fit(_city_display_name(city), max(8, self.w - 2))
        if first:
            lt = time.localtime()
            self.clock_text = f"{lt.tm_hour:02d}:{lt.tm_min:02d}"
            self._update_cruise_ticker(dt)
            if u_lin < 0.70:
                self.hud_text, self.hud_rgb = name, HUD_NAME_RGB
            elif u_lin < 0.90:
                self.hud_text, self.hud_rgb = "SCAN", HUD_RGB
            else:
                self.hud_text, self.hud_rgb = "LOCKED", HUD_RGB
        else:
            self.clock_text = ""
            if u_lin < 0.55:
                self.hud_text, self.hud_rgb = name, HUD_NAME_RGB
            elif u_lin < 0.82:
                self.hud_text, self.hud_rgb = "SCAN", HUD_RGB
            else:
                self.hud_text, self.hud_rgb = "LOCKED", HUD_RGB

        if self._orbit_space is not None and not self.orbit_use_surface:
            panel_r = math.hypot(self.w, self.h) * 0.55
            star_u = _clamp(1.0 - (self.orbit_r / max(panel_r, 1.0)), 0.0, 1.0)
            self._orbit_space.update(dt, streak=0.1 + 0.4 * star_u)

        if self.phase_t >= ORBIT_IN_SEC:
            # Handoff on SURFACE path already — same FOV, city under reticle
            self.city = city
            self.strike_city = city
            self.next_city = None
            self.city["damage"] = float(self.city.get("damage", 0.0))
            self.city["obliterated"] = bool(self.city.get("obliterated", False))
            self._mark_visited(city)
            self.orbit_mpp = float(mpp_close)
            self.orbit_r = world_r / max(mpp_close, 1.0)
            self.alt_close = self._alt_from_mpp(mpp_close)
            self.alt_ft = float(self.alt_close)
            self.alt_from = float(self.alt_close)
            self.alt_to = float(self.alt_close)
            self.x, self.y, self.heading = self._cam_for_city_under_crosshair(
                city, mpp_close,
            )
            # No random aim teleport — wander starts from zero in bomb phase
            self.aim_err_x = 0.0
            self.aim_err_y = 0.0
            self.bombs = []
            self.blasts = []
            self.bomb_cd = 0.35
            self.phase = "bomb"
            self.phase_t = 0.0
            self.clock_text = ""
            self.hud_text, self.hud_rgb = "LOCKED", HUD_RGB
            self._orbit_dive_heading_set = False
            self.orbit_use_surface = True
            self.orbit_local_blend = 1.0
            self._first_approach = False
            day0 = self.planet.day_factor_flat(city["x"], city["y"])
            nv = "NV" if self._city_is_night(city) else "VIS"
            n = self.batch_done + 1
            print(
                f"[PlanetBlast] {self.batch_side.upper()} batch {n}/{TARGETS_PER_BATCH}  "
                f"city={_city_display_name(city)} size={city['size']}  "
                f"day={day0:.2f} {nv}  weapons free @ {self.alt_close:.0f} ft  "
                f"(surface handoff mpp={mpp_close:.0f})"
            )

    def _render_globe(self, canvas):
        """Draw orbiting full-planet disc (shared with intro style)."""
        set_px = canvas.SetPixel
        # Clear canvas + composite every frame so scrolling HUD never leaves
        # trails under full-frame NV (hardware NV rewrites from _frame).
        bg = (0, 0, 4)
        try:
            canvas.Fill(0, 0, 4)
        except Exception:
            for y in range(self.h):
                for x in range(self.w):
                    set_px(x, y, 0, 0, 4)
        frame = getattr(self, "_frame", None)
        prev = getattr(self, "_prev", None)
        if frame is not None:
            for y in range(self.h):
                frow = frame[y]
                prow = prev[y] if prev is not None else None
                for x in range(self.w):
                    frow[x] = bg
                    if prow is not None:
                        prow[x] = bg
        # Stars behind the planet (fade out as we dive into atmosphere)
        star_fade = 0.55
        if self.phase in ("orbit_hold", "warcom_order"):
            # Holding pattern: full planet + rich starfield
            star_fade = 0.85
        elif self.phase == "orbit_out":
            u = _smoothstep(min(1.0, self.phase_t / max(0.05, ORBIT_OUT_SEC)))
            star_fade = 0.15 + 0.55 * u
        elif self.phase == "orbit_in":
            # Fade stars as the disc grows past the panel (still same map)
            panel_r = math.hypot(self.w, self.h) * 0.55
            rnow = max(0.5, float(getattr(self, "orbit_r", panel_r)))
            star_fade = 0.75 * _clamp(1.0 - (rnow / panel_r) * 0.85, 0.0, 1.0)
        if self._orbit_space is not None and star_fade > 0.02:
            try:
                self._orbit_space.draw(canvas, fade=star_fade, frame=frame)
            except Exception:
                pass

        cx = float(getattr(self, "orbit_px", self.w * 0.5))
        cy = float(getattr(self, "orbit_py", self.h * 0.5))
        radius = max(0.5, float(getattr(self, "orbit_r", self._globe_max_r())))
        local_blend = _clamp(float(getattr(self, "orbit_local_blend", 0.0)), 0.0, 1.0)
        limb_flat = _clamp(float(getattr(self, "orbit_limb_flat", local_blend)), 0.0, 1.0)
        lon = float(getattr(self, "orbit_lon", 0.0))
        lat = float(getattr(self, "orbit_lat", 0.0))
        world_r = float(getattr(self.planet, "R", PLANET_R) or PLANET_R)
        # Sphere FOV: mpp = R / radius (identity used by dive / pullback / hold)
        if (
            getattr(self, "orbit_mpp", None) is not None
            and self.phase in ("orbit_in", "orbit_out")
        ):
            mpp_local = float(self.orbit_mpp)
            radius = world_r / max(mpp_local, 1.0)
            # Never draw smaller than the full-planet disc during pullback end
            if self.phase == "orbit_out":
                r_full = float(getattr(self, "orbit_r_full", radius) or radius)
                if radius < r_full:
                    radius = r_full
                    mpp_local = world_r / max(radius, 0.5)
        else:
            mpp_local = world_r / max(radius, 0.5)
        glow_r = radius + 1.2 + min(3.0, radius * 0.08)
        x0 = max(0, int(cx - glow_r - 1))
        x1 = min(self.w - 1, int(cx + glow_r + 1))
        y0 = max(0, int(cy - glow_r - 1))
        y1 = min(self.h - 1, int(cy + glow_r + 1))
        # Prefer lod 0 on full-planet / high mpp so city brightness is capped
        lod = 0 if (radius < min(self.w, self.h) * 0.95 or mpp_local > 8_000.0) else (
            1 if mpp_local > 3_500.0 else 2
        )
        step = 1  # full resolution — no blocky sparse sampling
        sample = self.planet.sample
        day_sphere = self.planet.day_factor_sphere
        day_flat = self.planet.day_factor_flat
        world_from = self.planet.world_from_sphere
        glow_span = max(0.2, glow_r - radius)
        fade = 1.0 if radius > 3 else _clamp(radius / 3.0, 0.0, 1.0)
        # NV flag for end-of-frame full green pass (terrain drawn full-color here)
        # Chatter / orbit-hold / WARCOM order: always full color (no NV smear on text)
        if self.phase in ("orbit_hold", "warcom_order"):
            self._nv = False
        elif self.phase == "orbit_in":
            tgt = self.next_city or self.city
            self._nv = self._city_is_night(tgt)
        elif self.phase in ("orbit_out", "orbit_turn"):
            self._nv = self._night_vision_on()
        # Dive: always sphere sample of the ONE PlanetMap (no flat UV morph)
        pure_sphere = self.phase == "orbit_in" or local_blend < 0.05
        nv_boost = bool(getattr(self, "_nv", False))

        for y in range(y0, y1 + 1, step):
            for x in range(x0, x1 + 1, step):
                dx = x + 0.5 - cx
                dy = y + 0.5 - cy
                d2 = dx * dx + dy * dy
                if d2 > glow_r * glow_r:
                    continue
                d = math.sqrt(d2)
                if d <= radius:
                    # Sphere projection only → shared PlanetMap sample(wx, wy)
                    nx = dx / radius
                    ny = dy / radius
                    nz2 = 1.0 - nx * nx - ny * ny
                    if nz2 < 0.0:
                        continue
                    nz = math.sqrt(nz2)
                    pnx, pny, pnz = _view_to_planet_normal(nx, ny, nz, lon, lat)
                    wx, wy = world_from(pnx, pny, pnz)
                    day = day_sphere(pnx, pny, pnz)
                    # Near surface: day model matches flat flight (lighting only)
                    if limb_flat > 0.05 or (pure_sphere and mpp_local < 8_000.0):
                        day_f = day_flat(wx, wy)
                        if limb_flat > 0.05:
                            k = limb_flat
                        else:
                            k = _clamp((8_000.0 - mpp_local) / 6_000.0, 0.0, 1.0)
                        day = day + (day_f - day) * k
                    if nv_boost:
                        day = max(day, NV_SURF_DAY)
                    tr, tg, tb = sample(wx, wy, day_factor=day, lod=lod)
                    limb = 0.55 + 0.45 * nz
                    # Flatten limb as we dive so handoff to surface isn't dark-edged
                    limb = limb + (1.0 - limb) * limb_flat
                    lf = limb * fade
                    rr = int(_clamp(tr * lf, 0, 255))
                    gg = int(_clamp(tg * lf, 0, 255))
                    bb = int(_clamp(tb * lf, 0, 255))
                    # Feed composite buffers (full-frame NV runs after HUD)
                    if 0 <= y < self.h and 0 <= x < self.w:
                        self._prev[y][x] = (rr, gg, bb)
                        self._frame[y][x] = (rr, gg, bb)
                    if step == 1:
                        set_px(x, y, rr, gg, bb)
                    else:
                        for fy in range(y, min(y + step, y1 + 1)):
                            for fx in range(x, min(x + step, x1 + 1)):
                                if 0 <= fy < self.h and 0 <= fx < self.w:
                                    self._prev[fy][fx] = (rr, gg, bb)
                                    self._frame[fy][fx] = (rr, gg, bb)
                                set_px(fx, fy, rr, gg, bb)
                elif d <= glow_r and limb_flat < 0.55:
                    t = 1.0 - (d - radius) / glow_span
                    t = t * t * 0.55 * (1.0 - limb_flat)
                    gr, gg, gb = int(80 * t), int(140 * t), int(220 * t)
                    if step == 1:
                        set_px(x, y, gr, gg, gb)
                        if 0 <= y < self.h and 0 <= x < self.w:
                            self._frame[y][x] = (gr, gg, gb)
                    else:
                        for fy in range(y, min(y + step, y1 + 1)):
                            for fx in range(x, min(x + step, x1 + 1)):
                                set_px(fx, fy, gr, gg, gb)
                                if 0 <= fy < self.h and 0 <= fx < self.w:
                                    self._frame[fy][fx] = (gr, gg, gb)

        # Stable 1px city pins at globe range (stops sub-pixel wink; not a disc)
        if mpp_local >= GLOBE_CITY_PIN_MPP:
            self._stamp_globe_city_pins(
                canvas, cx, cy, radius, lon, lat, mpp_local,
            )

    def _stamp_globe_city_pins(self, canvas, cx, cy, radius, lon, lat, mpp):
        """
        Project cities to the disc and force a single pixel so they don't blink
        in/out as sphere samples skim the paint grid. Muted colors only —
        no large whitish overlay disc.
        """
        set_px = canvas.SetPixel
        world_r = float(getattr(self.planet, "R", PLANET_R) or PLANET_R)
        min_sz = int(GLOBE_CITY_PIN_MIN_SIZE)
        frame = getattr(self, "_frame", None)
        for city in self.planet.cities:
            sz = int(city.get("size", 1))
            if sz < min_sz:
                continue
            if city.get("obliterated") or float(city.get("damage", 0.0)) >= 0.99:
                continue
            clon = float(city["x"]) / world_r
            clat = _clamp(float(city["y"]) / world_r, -1.2, 1.2)
            cl = math.cos(clat)
            px = math.sin(clon) * cl
            py = math.sin(clat)
            pz = math.cos(clon) * cl
            vx, vy, vz = _planet_to_view_normal(px, py, pz, lon, lat)
            # Hidden on far side of the globe
            if vz < 0.18:
                continue
            sx = cx + vx * radius
            sy = cy + vy * radius
            # Must land on the visible disc (with tiny margin)
            if (sx - cx) ** 2 + (sy - cy) ** 2 > (radius * 1.02) ** 2:
                continue
            ix = int(round(sx))
            iy = int(round(sy))
            if ix < 0 or ix >= self.w or iy < 0 or iy >= self.h:
                continue
            day = self.planet.day_factor_flat(float(city["x"]), float(city["y"]))
            if day < NV_NIGHT_MAX:
                # Muted amber night light (not full CITY_NIGHT blast)
                cr, cg, cb = 160, 110, 40
                if sz >= 5:
                    cr, cg, cb = 190, 130, 48
            else:
                # Soft day urban pin — stays below land highlight
                cr, cg, cb = 95, 95, 100
                if sz >= 5:
                    cr, cg, cb = 115, 112, 110
            set_px(ix, iy, cr, cg, cb)
            if frame is not None:
                frame[iy][ix] = (cr, cg, cb)

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
        self._warcom_scroll_accum = 0.0
        self.warcom_order_w = float(_hud_text_width(order))
        self.warcom_order_done = False
        self.warcom_order_done_t = 0.0
        self.hud_text = "ALERT"
        self.hud_rgb = HUD_ALERT_RGB
        # Frame-locked 1 px/update (same as space-news marquee) — no multi-pixel jumps
        scroll_speed = float(TARGET_FPS)
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
        """After WARCOM attack order — dive to the pick city and open fire."""
        print(
            f"[PlanetBlast] Order acknowledged — diving on "
            f"{getattr(self.planet, 'name', 'world')}"
        )
        # Keep batch side from first city lighting (set at camera init)
        self.batch_done = 0
        if getattr(self, "_first_approach", False) or getattr(
            self, "orbit_r_full", None,
        ):
            self._begin_first_dive()
        else:
            target = self._pick_next_city(count_kill=False)
            self._begin_cruise_to(target)

    def _update_warcom_order(self, dt):
        """Hold until the full WARCOM order has scrolled off, then strike."""
        self.phase_t += dt
        # First mission: keep whole-planet slow rotation through the order
        if getattr(self, "_first_approach", False):
            self._hold_full_planet_view(dt, spin_rate=0.12)
            if self._orbit_space is not None:
                self._orbit_space.update(dt, streak=0.08)
        else:
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
                # Exactly 1 whole pixel per frame — even motion under variable dt
                self.warcom_order_scroll = float(int(self.warcom_order_scroll) - 1)
                self._warcom_scroll_accum = 0.0
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
        """Live stats lines for the chatter ticker."""
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
        phase = getattr(self, "phase", "")
        if phase == "patrol":
            mode_line = f"PATROL {max(0, int(PATROL_SEC - self.patrol_t))}S"
        elif phase == "orbit_hold":
            remain = max(0, int(ORBIT_HOLD_SEC - self.phase_t))
            mode_line = f"HOLD {remain}S"
        elif phase == "orbit_in" and getattr(self, "_first_approach", False):
            remain = max(0, int(ORBIT_IN_SEC - self.phase_t))
            mode_line = f"DESCENT {remain}S"
        elif phase == "cruise_to":
            mode_line = "TRANSIT"
        elif phase == "cruise":
            mode_line = f"CRUISE {max(0, int(CRUISE_SEC - self.cruise_t))}S"
        else:
            mode_line = "ON STATION"
        msgs = [
            f"WORLD {world}",
            f"POP {pop // 1000}K",
            f"CITIES {left}/{n} LIVE",
            f"DESTROYED {destroyed}",
            f"DAMAGED {damaged}",
            f"FIRES {fires}",
            f"ALT {alt} FT",
            f"BOMBED {self.cities_bombed}/{getattr(self, 'surrender_quota', '?')}",
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
        # Orbit hold / first dive: lead with tasking lines
        head = []
        if getattr(self, "_first_approach", False) and self.phase in (
            "orbit_hold", "orbit_in",
        ):
            cname = _city_display_name(self.city)
            world = str(getattr(self.planet, "name", "WORLD")).upper()
            if self.phase == "orbit_hold":
                quota = int(getattr(self, "surrender_quota", 0) or 0)
                head = [
                    f"WORLD {world}",
                    f"TGT {cname}",
                    f"ENGAGE {quota} CITIES",
                    "ORBIT HOLD",
                    "WEAPONS COLD",
                    "WARCOM: AWAIT AUTHORIZATION",
                    "WARCOM: HOLD PATTERN",
                    "WARCOM: PACKAGE STANDBY",
                ]
            else:
                head = [
                    f"WORLD {world}",
                    f"TGT {cname}",
                    "DESCENT",
                    "WARCOM: STRIKE WINDOW OPENING",
                ]
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
        if not head:
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
        Integer-pixel marquee: accumulate sub-pixels, advance whole pixels only.
        Avoids round() dither at .5 that makes thin glyphs flicker on LEDs.
        """
        char_step = float(_HUD_CHAR_W + _HUD_GAP)
        if not self.cruise_stream:
            self.cruise_scroll_x = float(self.w)
            self._scroll_accum = 0.0
            self._cruise_append_stream()
        else:
            # Top up stream before it runs out
            stream_w = _hud_text_width(self.cruise_stream)
            if self.cruise_scroll_x + stream_w < self.w * 2:
                self._cruise_append_stream(min_px=self.w * 4)

        # Sub-pixel residue → whole-pixel steps (stable under variable dt)
        self._scroll_accum += CRUISE_TICKER_PPS * min(dt, 0.08)
        step = int(self._scroll_accum)
        if step > 0:
            self.cruise_scroll_x -= float(step)
            self._scroll_accum -= float(step)

        # Drop characters that have fully scrolled off the left edge
        while self.cruise_stream and self.cruise_scroll_x <= -char_step:
            self.cruise_stream = self.cruise_stream[1:]
            self.cruise_scroll_x += char_step
            if not self.cruise_stream:
                self._cruise_append_stream()
                break

    def _cruise_ticker_draw_x(self):
        """Integer pixel x for drawing (already whole-pixel stepped)."""
        return int(self.cruise_scroll_x)

    def _update_cruise(self, dt):
        """
        Legacy opening surface cruise (60s tour before weapons).
        Not used on the main path — first mission is dive→lock→fire.
        Kept only if phase is forced to "cruise" externally.
        """
        # Bail out immediately into weapons on the pick city (no 60s wait)
        print(
            "[PlanetBlast] Opening cruise skipped — dive/lock path "
            f"→ {_city_display_name(self.city)}"
        )
        self.clock_text = ""
        self.cruise_stream = ""
        self.alt_close = _alt_for_city_pixels(self.city, self.h, CITY_TARGET_PX)
        self.alt_ft = float(self.alt_close)
        self.x = float(self.city["x"])
        self.y = float(self.city["y"])
        self.phase = "bomb"
        self.phase_t = 0.0
        self.bomb_cd = 0.35
        self.hud_text, self.hud_rgb = "LOCKED", HUD_RGB

    def _drop_bomb(self):
        """Spawn large bomb; falls near the crosshair with wide landing variance."""
        # Primary aim = reticle world point (camera track already imperfect)
        ax, ay = self._aim_point_world()
        cr = _city_radius_m(self.city)
        # Wide scatter: most inside/near city, some far longshots
        if random.random() < BOMB_AIM_LONGSHOT:
            # Long miss — past the city rim into the countryside (tightened 25%)
            spread = cr * random.uniform(0.75, 1.45)
        else:
            # Normal miss distribution biased toward outskirts, not dead-center
            # (sqrt-uniform: more hits mid-ring than pin-point)
            u = math.sqrt(random.random())
            spread = cr * BOMB_AIM_SPREAD * (0.12 + 0.88 * u)
        ang = random.uniform(0, math.pi * 2)
        # Slight elliptical stretch so pattern isn't a perfect circle
        stretch = random.uniform(0.72, 1.28)
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
        """Impact: smoke ring + fire core; overwrite baked city paint; wildfire."""
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
        # Compact crater rubble (smaller ember diameter)
        patch_r = max(FIRE_CELL * 0.7, cr * (0.12 + 0.18 * fall))
        self.planet.stamp_damage_patch(
            wx, wy, patch_r, strength=0.55 + 0.45 * fall,
        )
        # Red embers seed into surrounding green (slow crawl)
        self.planet.seed_impact_wildfire(wx, wy, strength=0.55 + 0.45 * fall)
        self.planet.seed_city_wildfire(self.city)
        if self.city["damage"] >= 0.98 and not self.city.get("obliterated"):
            self.city["obliterated"] = True
            self.city["damage"] = 1.0
            # Full city disc → rubble; embers ring for outward green burn
            self.planet.stamp_city_damage(self.city)
            self.planet.seed_city_wildfire(self.city)
            print(
                f"[PlanetFly] City size={self.city['size']} OBLITERATED"
            )
        elif self.city["damage"] >= FIRE_SEED_DMG:
            # Progressive city-wide damage stamp as hits accumulate
            self.planet.stamp_city_damage(self.city)

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
            # Stable heading during SCAN (no continuous spin — that orbited aim)
            mpp = self._mpp()
            cos_h = math.cos(self.heading)
            sin_h = math.sin(self.heading)
            fwd = float(CROSSHAIR_UP_PX) * mpp
            ideal_x = cx - cos_h * fwd + self.aim_err_x
            ideal_y = cy - sin_h * fwd + self.aim_err_y
            self._nudge_toward(ideal_x, ideal_y, dt, max_mps=ZOOM_TRACK_MPS)
            # Light aim wander only — no fly_forward + heading spin
            self.aim_err_x += random.uniform(-1, 1) * CAM_AIM_ERR_M * CAM_AIM_WANDER * 0.45 * dt
            self.aim_err_y += random.uniform(-1, 1) * CAM_AIM_ERR_M * CAM_AIM_WANDER * 0.45 * dt
            self.aim_err_x = _clamp(self.aim_err_x, -CAM_AIM_ERR_M * 0.6, CAM_AIM_ERR_M * 0.6)
            self.aim_err_y = _clamp(self.aim_err_y, -CAM_AIM_ERR_M * 0.6, CAM_AIM_ERR_M * 0.6)
            # Acquire: SCAN → TARGET: name when city is on-screen → LOCK
            if self.phase_t >= ZOOM_IN_SEC * 0.55:
                self.hud_text, self.hud_rgb = "LOCKED", HUD_RGB
            elif self._city_on_screen(self.city):
                self.hud_text = self._target_label(self.city)
                self.hud_rgb = HUD_NAME_RGB
            else:
                self.hud_text, self.hud_rgb = "SCAN", HUD_RGB
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
            # Tiny heading drift only (was 0.04 rad/s → visible spin circles)
            self.heading += 0.008 * dt
            cos_h = math.cos(self.heading)
            sin_h = math.sin(self.heading)
            speed = mpp * self.h * CRUISE_SPAN_PER_SEC * 0.18
            self.x += cos_h * speed * dt
            self.y += sin_h * speed * dt
            # Wander aim error so lock is not 100% accurate
            self.aim_err_x += random.uniform(-1, 1) * CAM_AIM_ERR_M * CAM_AIM_WANDER * dt
            self.aim_err_y += random.uniform(-1, 1) * CAM_AIM_ERR_M * CAM_AIM_WANDER * dt
            self.aim_err_x = _clamp(self.aim_err_x, -CAM_AIM_ERR_M, CAM_AIM_ERR_M)
            self.aim_err_y = _clamp(self.aim_err_y, -CAM_AIM_ERR_M, CAM_AIM_ERR_M)
            # Ideal cam: city under crosshair + error (rate-limited — no snap)
            fwd = float(CROSSHAIR_UP_PX) * mpp
            ideal_x = cx - cos_h * fwd + self.aim_err_x
            ideal_y = cy - sin_h * fwd + self.aim_err_y
            self._nudge_toward(ideal_x, ideal_y, dt, max_mps=ZOOM_TRACK_MPS * 1.2)
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
                self.cities_bombed += 1
                self.since_patrol += 1
                print(
                    f"[PlanetFly] Target destroyed — total bombed={self.cities_bombed}/"
                    f"{getattr(self, 'surrender_quota', '?')}  "
                    f"since patrol={self.since_patrol}/{PATROL_EVERY}"
                )
                # Dice: do they fold? If yes, leave this world for another planet.
                if self._roll_surrender():
                    self._begin_surrender()
                else:
                    # Quota hit but still fighting → fires spread faster
                    self._maybe_rage_fire_after_kill()
                    # Stay at strike altitude; fly to a nearby city
                    self._pending_patrol = False
                    nxt = self._pick_next_city(count_kill=True)
                    self._begin_cruise_to(nxt)

        elif self.phase == "surrender":
            self._update_surrender(dt)

        elif self.phase == "zoom_out":
            # Climb to overview (used for patrol handoff only)
            u = _smoothstep(min(1.0, self.phase_t / max(0.05, ZOOM_OUT_SEC)))
            self.alt_ft = _lerp(self.alt_from, self.alt_to, u)
            self.heading += 0.02 * dt
            self._fly_forward(dt, 0.35, max_mps=CRUISE_TO_MPS)
            self.hud_text, self.hud_rgb = "NEXT TGT", HUD_RGB
            if self.phase_t >= ZOOM_OUT_SEC:
                self.alt_ft = float(self.alt_wide)
                if self._pending_patrol:
                    self.since_patrol = 0
                    self._pending_patrol = False
                    self._begin_patrol()
                else:
                    self._begin_globe_search(count_kill=False)

        elif self.phase == "orbit_hold":
            self._update_orbit_hold(dt)

        elif self.phase == "orbit_out":
            self._update_orbit_out(dt)

        elif self.phase == "orbit_turn":
            self._update_orbit_turn(dt)

        elif self.phase == "orbit_in":
            self._update_orbit_in(dt)

        elif self.phase == "approach_dive":
            # Only if intro handoff was still high — continuous alt to strike
            self.phase_t += 0.0  # already advanced in update()
            u = _smoothstep(min(1.0, self.phase_t / max(0.05, APPROACH_DIVE_SEC)))
            # Longer real dive if we entered high
            dive_sec = max(APPROACH_DIVE_SEC, 5.0)
            u = _smoothstep(min(1.0, self.phase_t / dive_sec))
            self.alt_ft = _lerp(self.alt_from, self.alt_to, u)
            # Hold city under reticle while descending
            mpp = self._mpp()
            cos_h = math.cos(self.heading)
            sin_h = math.sin(self.heading)
            fwd = float(CROSSHAIR_UP_PX) * mpp
            ideal_x = self.city["x"] - cos_h * fwd
            ideal_y = self.city["y"] - sin_h * fwd
            self._nudge_toward(ideal_x, ideal_y, dt, max_mps=ZOOM_TRACK_MPS)
            lt = time.localtime()
            self.clock_text = f"{lt.tm_hour:02d}:{lt.tm_min:02d}"
            self._update_cruise_ticker(dt)
            name = _hud_fit(_city_display_name(self.city), max(8, self.w - 2))
            self.hud_text, self.hud_rgb = name, HUD_NAME_RGB
            if self.phase_t >= dive_sec:
                self.alt_ft = float(self.alt_close)
                self.phase = "bomb"
                self.phase_t = 0.0
                self.bomb_cd = 0.35
                self.clock_text = ""
                self.hud_text, self.hud_rgb = "LOCKED", HUD_RGB
                print(
                    f"[PlanetFly] Weapons free — {_city_display_name(self.city)}"
                )

        elif self.phase == "cruise_to":
            # Silent transit — short hops at strike alt; long hops climb + dash
            self.clock_text = ""
            self.cruise_stream = ""
            tgt = self.next_city
            if tgt is None:
                tgt = self._pick_next_city(count_kill=False)
                self.next_city = tgt
            strike_alt = float(getattr(self, "_strike_hold_alt", self.alt_close))
            high = bool(getattr(self, "_cruise_high", False))
            # Remaining range before this frame's move
            dist0 = math.hypot(
                float(tgt["x"]) - self.x, float(tgt["y"]) - self.y,
            )
            if high:
                # Cruise high and fast until approach, then drop to strike alt
                if dist0 > CRUISE_TO_APPROACH_M:
                    want_alt = float(getattr(
                        self, "_cruise_transit_alt", strike_alt * 3.0,
                    ))
                    speed = float(getattr(self, "_cruise_speed", CRUISE_TO_MPS))
                    turn = 0.28
                else:
                    want_alt = strike_alt
                    # Final approach: moderate speed; _cruise_toward handles no-orbit
                    speed = CRUISE_TO_MPS * 0.65
                    turn = 0.22
                # Smooth climb / descent (no snap)
                self.alt_ft = _lerp(self.alt_ft, want_alt, min(1.0, 1.6 * dt))
            else:
                self.alt_ft = strike_alt
                speed = float(getattr(self, "_cruise_speed", CRUISE_TO_MPS))
                turn = 0.28
            dist = self._cruise_toward(
                tgt["x"], tgt["y"], dt,
                speed_mps=speed,
                turn_rate=turn,
            )
            # When the next city is visible: TARGET: Name; else SCAN if close
            if self._city_on_screen(tgt):
                self.hud_text = self._target_label(tgt)
                self.hud_rgb = HUD_NAME_RGB
            elif dist < CRUISE_TO_ARRIVE_M * 3.5:
                self.hud_text, self.hud_rgb = "SCAN", HUD_RGB
            else:
                self.hud_text = ""
            if dist <= CRUISE_TO_ARRIVE_M:
                nxt = self.next_city or tgt
                # Back to strike altitude for SCAN→LOCK→FIRE
                hold_alt = strike_alt
                self._begin_zoom_in(nxt)
                self.alt_close = hold_alt
                self.alt_from = hold_alt
                self.alt_to = hold_alt
                self.alt_ft = hold_alt
                self._cruise_high = False

        elif self.phase == "patrol":
            self._update_patrol(dt)

        # Altitude log only when it meaningfully changes
        self._log_alt_if_changed()

    def _night_vision_on(self):
        """
        Night vision only for true night targets during strike ops.
        Never during chatter / orbit-hold / WARCOM order (full-color HUD).
        Day and twilight stay normal color. During dive/bomb, lock to the
        target city's lighting (not the free-camera terminator).
        """
        if self.phase in ("orbit_hold", "warcom_order", "cruise", "patrol"):
            return False
        city = None
        if self.phase in ("orbit_in", "zoom_in", "bomb"):
            city = self.next_city if self.phase == "orbit_in" else self.city
        if city is not None:
            return self._city_is_night(city)
        # Other free-flight: NV only deep night under the camera
        day = self.planet.day_factor_flat(self.x, self.y)
        return day < NV_NIGHT_MAX

    @staticmethod
    def _to_night_vision(r, g, b):
        """Map any RGB pixel to phosphor-green mono NV (luminance → green)."""
        lum = 0.299 * r + 0.587 * g + 0.114 * b
        # Expand midtones so structure separates under mono green
        t = _clamp(lum / 255.0, 0.0, 1.0)
        t = t * t * (3.0 - 2.0 * t)  # smoothstep contrast
        v = _clamp(t * 255.0 * NV_GAIN + NV_FLOOR, 0.0, 255.0)
        # Classic phosphor green — only green channel carries image
        return (
            int(v * 0.10),
            int(min(255, v * 1.0)),
            int(v * 0.14),
        )

    def _put_rgb(self, canvas, x, y, r, g, b):
        """Write a pixel to canvas + composite frame (for full-frame NV)."""
        x = int(x)
        y = int(y)
        if x < 0 or y < 0 or x >= self.w or y >= self.h:
            return
        r = 0 if r < 0 else (255 if r > 255 else int(r))
        g = 0 if g < 0 else (255 if g > 255 else int(g))
        b = 0 if b < 0 else (255 if b > 255 else int(b))
        self._frame[y][x] = (r, g, b)
        canvas.SetPixel(x, y, r, g, b)

    def _apply_full_frame_nv(self, canvas):
        """
        Night vision: entire panel is shades of green — terrain, cities,
        bombs, blasts, crosshairs, HUD. No residual red/amber/white.
        """
        if not getattr(self, "_nv", False):
            return
        to_nv = self._to_night_vision
        set_px = canvas.SetPixel
        w, h = self.w, self.h
        # Prefer live canvas buffer (LEDsim FrameCanvas)
        buf = getattr(canvas, "_buf", None)
        if buf is not None:
            for y in range(h):
                row = buf[y]
                for x in range(w):
                    c = row[x]
                    nr, ng, nb = to_nv(int(c[0]), int(c[1]), int(c[2]))
                    row[x] = (nr, ng, nb)
                    self._frame[y][x] = (nr, ng, nb)
                    self._prev[y][x] = (nr, ng, nb)
            return
        # Hardware: convert composite frame and rewrite canvas
        frame = getattr(self, "_frame", None)
        if frame is None:
            return
        for y in range(h):
            for x in range(w):
                nr, ng, nb = to_nv(*frame[y][x])
                frame[y][x] = (nr, ng, nb)
                self._prev[y][x] = (nr, ng, nb)
                set_px(x, y, nr, ng, nb)

    def _render_lod(self, mpp):
        """
        Choose surface sample quality. Always step=1 (full panel samples) so
        terrain never draws as 2×2/4×4 blocks that crawl while panning.
        Returns (lod, step).
        """
        phase = self.phase
        # Full pixel rate everywhere — if too slow, tune sample/numba next
        if phase in ("cruise", "patrol", "warcom_order", "cruise_to") or mpp >= 14_000.0:
            return 0, 1
        if phase == "zoom_out" or mpp >= 7_000.0:
            return 1, 1
        if phase == "zoom_in" or mpp >= 3_500.0:
            return 1, 1
        # Bomb / low altitude — full detail
        return 2, 1

    def render(self, canvas):
        """Top-down map + crosshairs, bombs, smoke rings, fire — or globe orbit."""
        # Globe for hold/turn and early dive. Late orbit_in uses surface when
        # orbit_use_surface (matched FOV, city under crosshair → no bomb jump).
        use_globe = (
            self.phase in ("orbit_hold", "orbit_turn")
            or (
                self.phase == "warcom_order"
                and getattr(self, "_first_approach", False)
            )
            or (
                self.phase == "orbit_in"
                and not getattr(self, "orbit_use_surface", False)
            )
            or (
                self.phase == "orbit_out"
                and not getattr(self, "orbit_use_surface", False)
            )
        )
        if use_globe:
            self._render_globe(canvas)
            self._draw_hud(canvas)
            if self._nv:
                self._apply_full_frame_nv(canvas)
            return

        # Surface path (strike, cruise, early orbit_out, late orbit_in)
        if self.phase in ("orbit_out", "orbit_in") and getattr(self, "orbit_mpp", None):
            self.alt_ft = self._alt_from_mpp(float(self.orbit_mpp))

        mpp = self._mpp()
        cos_h = math.cos(self.heading)
        sin_h = math.sin(self.heading)
        rx, ry = -sin_h, cos_h
        half_w = self.w * 0.5
        half_h = self.h * 0.5
        set_px = canvas.SetPixel
        lod, step = self._render_lod(mpp)
        planet = self.planet
        nv = self._night_vision_on()
        self._nv = nv  # for FX drawers
        cam_x, cam_y = self.x, self.y
        sample = planet.sample
        prev = self._prev
        frame = self._frame
        w, h = self.w, self.h
        sun_lon = planet.sun_lon
        inv_pr = 1.0 / float(getattr(planet, "R", PLANET_R))

        # Full-color frame; no haze / no temporal smear — crisp surface colors.
        # NV converts the whole panel at the end (terrain + HUD + bombs).
        for py in range(0, h, step):
            sf = (half_h - (py + 0.5)) * mpp
            base_wx = cam_x + cos_h * sf
            base_wy = cam_y + sin_h * sf
            for px in range(0, w, step):
                sx = (px + 0.5 - half_w) * mpp
                wx = base_wx + rx * sx
                wy = base_wy + ry * sx
                # Inline day_factor_flat
                day = 0.5 + 0.55 * math.cos(wx * inv_pr - sun_lon)
                if day < 0.0:
                    day = 0.0
                elif day > 1.0:
                    day = 1.0
                if nv:
                    # Lift surface lighting so mono-green still has biome structure
                    day_s = day if day > NV_SURF_DAY else NV_SURF_DAY
                    r, g, b = sample(wx, wy, day_factor=day_s, lod=lod)
                else:
                    r, g, b = sample(wx, wy, day_factor=day, lod=lod)
                r = int(r)
                g = int(g)
                b = int(b)
                # Write block of step×step pixels
                y1 = py + step if py + step <= h else h
                x1 = px + step if px + step <= w else w
                for fy in range(py, y1):
                    prow = prev[fy]
                    frow = frame[fy]
                    for fx in range(px, x1):
                        prow[fx] = (r, g, b)
                        frow[fx] = (r, g, b)
                        set_px(fx, fy, r, g, b)

        # No separate megacity stamp layer — cities live only in baked city_paint
        # (a solid whitish disc on top of night-yellow lights looked like a 2nd layer).

        # FX overlays. No weapons UI on cruise/patrol/order/orbit.
        if self.phase not in (
            "patrol", "cruise", "warcom_order", "cruise_to",
            "orbit_out", "orbit_turn", "orbit_in",
        ):
            self._draw_blasts(canvas)
            self._draw_bombs(canvas)
            if self.phase in ("zoom_in", "bomb") and not self.city.get("obliterated"):
                if self.phase == "bomb" or self.phase_t > ZOOM_IN_SEC * 0.55:
                    self._draw_crosshairs(canvas)
        self._draw_hud(canvas)

        # Full-panel NV: everything becomes shades of green
        if nv:
            self._apply_full_frame_nv(canvas)

    def _draw_hud(self, canvas):
        """
        Teeny 3×5 HUD.
        clock_text (HH:MM) always upper-left when set; other HUD as appropriate.
        Drawn in full color; full-frame NV converts everything to green mono.
        """
        frame = getattr(self, "_frame", None)
        rgb = self.hud_rgb
        hy = max(0, self.h - _HUD_CHAR_H - 1)

        # Time always upper-left whenever shown
        clock = getattr(self, "clock_text", "") or ""
        if clock:
            _draw_hud_text(canvas, clock, 1, 1, HUD_RGB, self.w, self.h, frame=frame)

        if self.phase in ("cruise", "patrol", "orbit_hold"):
            # Clock (top-left) + bottom WARCOM / stats marquee
            stream = self.cruise_stream or ""
            if stream:
                _draw_hud_text(
                    canvas, stream,
                    self._cruise_ticker_draw_x(), hy,
                    HUD_FIRE_RGB, self.w, self.h, frame=frame,
                )
            return

        # Silent city-to-city transit: only bottom status (SCAN) when set
        if self.phase == "cruise_to":
            text = self.hud_text or ""
            if text:
                _draw_hud_text(canvas, text, 1, hy, rgb, self.w, self.h, frame=frame)
            return

        if self.phase == "warcom_order":
            # No clock — red ALERT top-left; order scrolls bottom
            _draw_hud_text(canvas, "ALERT", 1, 1, HUD_ALERT_RGB, self.w, self.h, frame=frame)
            order = getattr(self, "warcom_order", "") or ""
            if (
                order
                and self.phase_t >= CRUISE_ORDER_ALERT_SEC
                and not getattr(self, "warcom_order_done", False)
            ):
                _draw_hud_text(
                    canvas, order,
                    int(self.warcom_order_scroll), hy,
                    HUD_ALERT_RGB, self.w, self.h, frame=frame,
                )
            return

        text = self.hud_text or ""
        if not text:
            return
        tw = _hud_text_width(text)
        hx = 1
        if tw + 2 > self.w:
            hx = max(0, self.w - tw)
        _draw_hud_text(canvas, text, hx, hy, rgb, self.w, self.h, frame=frame)

    def _draw_crosshairs(self, canvas):
        """
        Minimal 1px crosshairs — dead center, CROSSHAIR_UP_PX up.
        Full color; full-frame NV maps to green mono.
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
                    self._frame[py][px] = (rr, rg, rb)

    def _draw_bombs(self, canvas):
        """Large dark-purple bombs with red core (full-frame NV → green mono)."""
        set_px = canvas.SetPixel
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
                            r, g, bcol = BOMB_CORE_RGB
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
                        set_px(px, py, r, g, bcol)
                        self._frame[py][px] = (r, g, bcol)

    def _draw_blasts(self, canvas):
        """Slow smoke ring + fire core (full-frame NV → green mono)."""
        set_px = canvas.SetPixel
        mpp = self._mpp()
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
                            r = int(_lerp(70, sr, k))
                            g = int(_lerp(70, sg, k))
                            b = int(_lerp(72, sb, k))
                            set_px(px, py, r, g, b)
                            self._frame[py][px] = (r, g, b)
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
                        fr = int(_lerp(FIRE_RGB[0], FIRE_CORE[0], t * t) * fire_a)
                        fg = int(_lerp(FIRE_RGB[1], FIRE_CORE[1], t * t) * fire_a)
                        fb = int(_lerp(FIRE_RGB[2], FIRE_CORE[2], t * 0.45) * fire_a)
                        set_px(px, py, fr, fg, fb)
                        self._frame[py][px] = (fr, fg, fb)


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


def PlayPlanetFly(Duration=5, StopEvent=None):
    """
    Space intro → planet approach → surface strike tour.

    Runs until:
      - StopEvent is set (LEDcommander next/stop/preempt), or
      - wall-clock Duration (minutes) elapses (default 5), or
      - Ctrl-C

    Duration <= 0 disables the wall-clock limit (StopEvent only).
    """
    width = int(getattr(LED, "HatWidth", 64) or 64)
    height = int(getattr(LED, "HatHeight", 32) or 32)

    try:
        duration_min = float(Duration) if Duration not in (None, "") else 5.0
    except (TypeError, ValueError):
        duration_min = 5.0

    try:
        canvas = LED.TheMatrix.CreateFrameCanvas()
    except Exception:
        canvas = LED.Canvas

    # One planet map + one starfield for the whole mission (intro + camera)
    planet = PlanetMap()
    space = SpaceParallax(width, height)
    intro = SpaceIntro(width, height, planet=planet, space=space)
    cam = None
    tick = pygame.time.Clock() if HAS_PYGAME else None
    last = time.time()
    start_time = time.time()

    print(
        f"[PlanetBlast] {width}x{height}  space → zoom city → strike  "
        f"Duration={duration_min} min  "
        f"StopEvent={'yes' if StopEvent is not None else 'no'}  "
        f"fps~{TARGET_FPS}"
    )

    try:
        while True:
            if _stop(StopEvent):
                print("[PlanetBlast] StopEvent received — exiting")
                break

            now = time.time()
            if duration_min > 0 and (now - start_time) / 60.0 >= duration_min:
                print(
                    f"[PlanetBlast] Duration reached "
                    f"({duration_min} min) — exiting."
                )
                break

            dt = _clamp(now - last, 0.001, 0.1)
            last = now

            try:
                if cam is None:
                    intro.update(dt)
                    intro.draw(canvas)
                    if intro.done:
                        # Same planet map + shared starfield. Camera owns dive.
                        cam = PlanetCamera(
                            width, height,
                            planet=intro.planet,
                            city=intro.showcase,
                            start_xy=(
                                getattr(intro, "hand_off_x", intro.land_x),
                                getattr(intro, "hand_off_y", intro.land_y),
                            ),
                            start_mpp=getattr(intro, "hand_off_mpp", None),
                            start_globe_r=getattr(intro, "hand_off_r", None),
                            first_approach=True,
                            space=space,
                        )
                else:
                    cam.update(dt)
                    # Planet surrendered — leave orbit and start a new world
                    if getattr(cam, "mission_done", False):
                        print(
                            f"[PlanetBlast] Departing "
                            f"{getattr(cam.planet, 'name', 'world')} — "
                            f"new planet inbound"
                        )
                        planet = PlanetMap()
                        # Keep the same starfield; only regenerate the world map
                        intro = SpaceIntro(
                            width, height, planet=planet, space=space,
                        )
                        cam = None
                    else:
                        # Draw entire frame into the *back* canvas, then present once.
                        # Never write TheMatrix.SetPixel mid-frame (tears/flickers).
                        canvas.Fill(0, 0, 8)
                        cam.render(canvas)

                # Double-buffer present: show completed back buffer, get next back canvas
                canvas = LED.TheMatrix.SwapOnVSync(canvas)
                LED.Canvas = canvas
            except Exception:
                # Keep looping so StopEvent / duration are still polled every frame
                pass

            if tick:
                tick.tick(TARGET_FPS)
            else:
                time.sleep(1.0 / TARGET_FPS)

    except KeyboardInterrupt:
        print("[PlanetBlast] Interrupted")

    try:
        LED.ClearBuffers()
        LED.TheMatrix.Clear()
    except Exception:
        pass


def LaunchPlanetFly(Duration=5, ShowIntro=True, StopEvent=None):
    """
    Public entry for LEDcommander / Twitch / LEDsim — Planet Blast.

    Honors StopEvent so commander can preempt (next, stop, other launch).
    Duration is wall-clock minutes (default 5). Duration <= 0 = no time limit.
    """
    try:
        duration_min = float(Duration) if Duration not in (None, "") else 5.0
    except (TypeError, ValueError):
        duration_min = 5.0

    try:
        LED.LoadConfigData()
    except Exception:
        pass
    if _stop(StopEvent):
        print("[PlanetBlast] Launch aborted (StopEvent already set)")
        return
    print(
        f"[PlanetBlast] Launch  Duration={duration_min} min  "
        f"intro={bool(ShowIntro)}  "
        f"StopEvent={'yes' if StopEvent is not None else 'no'}"
    )
    # Compile or load cached surface kernels before first frame / title zoom
    _warm_planet_numba(StopEvent)
    if _stop(StopEvent):
        print("[PlanetBlast] StopEvent during Numba warm — exiting")
        return
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
        print("[PlanetBlast] StopEvent after title — exiting")
        return
    PlayPlanetFly(Duration=duration_min, StopEvent=StopEvent)


# Friendly alias
LaunchPlanetBlast = LaunchPlanetFly


if __name__ == "__main__":
    try:
        LaunchPlanetFly(Duration=5, ShowIntro=True, StopEvent=None)
    except KeyboardInterrupt:
        print("Exiting Planet Blast.")
