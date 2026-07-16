#!/usr/bin/env python
#------------------------------------------------------------------------------
#  DOTZERK — Berzerk-style room crawler for LEDarcade
#
#  Ported from ArcadeRetroClockHD (16×16 rooms) to a 32×32 playfield on a
#  64×32 panel (left half = game, right half = HUD). World map is the HD map
#  scaled 2× and expanded to 4×4 rooms (128×128 tiles → 16 rooms of 32×32).
#------------------------------------------------------------------------------

import LEDarcade as LED
import copy
import math
import random
import time
from collections import deque
from random import randint

LED.Initialize()

try:
    from zerk_map import MAP, MAP_H, MAP_W
except ImportError:
    MAP, MAP_H, MAP_W = [[0]], 1, 1

#------------------------------------------------------------------------------
# Layout
#------------------------------------------------------------------------------
ROOM = 32                    # room / viewport size (was 16 on HD)
ROOMS_H = 4                  # map columns of rooms (was 3)
ROOMS_V = 4                  # map rows of rooms
PF_H0 = 0
PF_V0 = 0
HUD_H0 = 32

# Door positions mid-edge of 32×32 room (was 7 / 15 on 16×16)
DOOR_MID = ROOM // 2 - 1     # 15

#------------------------------------------------------------------------------
# Tunables
#------------------------------------------------------------------------------
MAIN_SLEEP = 0.004
# Higher speed divisor = fewer moves per tick = slower (25% of original pace)
_SPEED_SCALE = 4
HUMAN_BASE_SPEED = 4 * _SPEED_SCALE   # was 4
ROBOT_SPEED = 7 * _SPEED_SCALE        # was 7
MISSILE_SPEED = 2 * _SPEED_SCALE      # was 2
ROBOT_COUNT = 4
DURATION_DEFAULT = 5
HUD_EVERY = 12 * _SPEED_SCALE

# Evil Otto — arcade bounce that closes in on the human (not real physics)
# Ghosts through walls; each hop moves base closer to the player.
OTTO_APPEAR_SECONDS = 20.0
OTTO_TICK = 3 * _SPEED_SCALE          # physics steps
OTTO_BOUNCE_STEPS = 14                # steps per full hop (up+down)
OTTO_BOUNCE_HEIGHT0 = 7.0             # first hop height (cells)
OTTO_HEIGHT_DECAY = 0.92              # height shrink per bounce
OTTO_APPROACH = 0.18                  # fraction of remaining gap closed per bounce
OTTO_MIN_HEIGHT = 1.2
OTTO_KILL_DIST = 0.85
OTTO_RGB = (255, 220, 0)              # bright yellow

HUMAN_START_LIVES = 3
LIFE_DOT_RGB = (0, 220, 0)            # green lives on bottom-left (PacDot-style)
CHICKEN_DISPLAY_SEC = 5.0             # how long status shows CHICKEN after early exit

# Robot taunts — occasional scrolling insult (status strip marquee)
STATUS_V = 20
STATUS_HGT = 6                        # banner ~5px tall + pad
TAUNT_RGB = (200, 40, 40)             # angry robot red
TAUNT_SCROLL_PPS = 24.0               # pixels per second (wall-clock)
TAUNT_GAP = 4                         # start just past right edge of HUD
TAUNT_ROOM_CHANCE = 0.28              # only some rooms get a marquee
TAUNT_START_DELAY = (6.0, 16.0)       # quiet seconds before first pass
TAUNT_LOOP_GAP = (10.0, 22.0)         # quiet seconds between passes
ROBOT_TAUNTS = (
    "CHICKEN",
    "FIGHT LIKE A ROBOT",
    "FLESH BAG",
    "MEAT IS WEAK",
    "RUN HUMAN",
    "I SEE YOU",
    "NO ESCAPE",
    "SQUISHY HUMAN",
    "YOU WILL FAIL",
    "GEAR OVER FLESH",
    "PUNY HUMAN",
    "CIRCUITS RULE",
    "YOUR AIM SUCKS",
    "TOO SLOW",
    "STEEL BEATS SKIN",
    "BEEP BOOP DEATH",
    "HUMAN ERROR",
    "CRY MORE",
    "NICE TRY MEAT",
    "DOOR WONT SAVE YOU",
    "OTTO IS COMING",
    "OBEY THE MACHINE",
    "DELETE HUMAN",
    "RUST NEVER SLEEPS",
    "SURRENDER SOFTIE",
)

# Excited robot gloats on every human death (scroll while lingering)
ROBOT_KILL_LINES = (
    "HA HA GOT YOU",
    "GOTCHA",
    "GOT HIM",
    "HAHAH",
    "TOAST",
    "CRISPY",
    "SQUISH",
    "NICE SHOT",
    "OWNED",
    "BOOM",
    "NO MORE",
    "FLATLINE",
    "DELETED",
    "REKT",
    "TOO EASY",
    "BYE HUMAN",
    "MEAT DOWN",
    "TARGET HIT",
)
DEATH_INTERLUDE_SECONDS = 2.0         # non-final death linger + scroll
FINAL_DEATH_SECONDS = 2.6             # last-life prolonged explosion

#------------------------------------------------------------------------------
# Entities
#------------------------------------------------------------------------------
class EmptyObj(object):
    def __init__(self):
        self.h = self.v = -1
        self.name = "empty"
        self.alive = 0
        self.exploding = 0
        self.locked = 0
        self.r = self.g = self.b = 0

    def Display(self):
        pass

    def Erase(self):
        pass


Empty = EmptyObj()


class WallObj(object):
    def __init__(self, h, v, r, g, b):
        self.h, self.v = h, v
        self.r, self.g, self.b = r, g, b
        self.name = "Wall"
        self.alive = 1
        self.exploding = 0
        self.locked = 0

    def Display(self):
        if self.alive:
            set_pf(self.h, self.v, self.r, self.g, self.b)

    def Erase(self):
        set_pf(self.h, self.v, 0, 0, 0)


class DoorObj(object):
    def __init__(self, h, v):
        self.h, self.v = h, v
        self.name = "Door"
        self.alive = 0
        self.locked = 0
        self.exploding = 0
        self.r = self.g = self.b = 0

    def Display(self):
        if not self.alive:
            return
        if self.locked:
            r, g, b = LED.SDLowPurpleR, LED.SDLowPurpleG, LED.SDLowPurpleB
        else:
            r, g, b = LED.SDDarkYellowR, LED.SDDarkYellowG, LED.SDDarkYellowB
        set_pf(self.h, self.v, r, g, b)

    def Erase(self):
        set_pf(self.h, self.v, 0, 0, 0)


class Actor(object):
    def __init__(self, h, v, r, g, b, direction, speed, name):
        self.h = h
        self.v = v
        self.r = r
        self.g = g
        self.b = b
        self.direction = direction
        self.scandirection = direction
        self.speed = speed
        self.alive = 0
        self.lives = 0
        self.name = name
        self.exploding = 0
        self.explode_tick = 0

    def Display(self):
        if self.alive and not self.exploding:
            set_pf(self.h, self.v, self.r, self.g, self.b)

    def Erase(self):
        set_pf(self.h, self.v, 0, 0, 0)


#------------------------------------------------------------------------------
# Pixel helpers (playfield offset on left half)
#------------------------------------------------------------------------------
def set_pf(h, v, r, g, b):
    """Draw into the 32×32 playfield (left half of panel)."""
    if 0 <= h < ROOM and 0 <= v < ROOM:
        LED.setpixel(PF_H0 + h, PF_V0 + v, r, g, b)


def in_room(h, v):
    return 0 <= h < ROOM and 0 <= v < ROOM


def restore_pf_cell(h, v):
    """Repaint one playfield cell from current object / map state."""
    if not in_room(h, v):
        return
    obj = MazeWorld.Playfield[h][v]
    if obj is Empty or getattr(obj, "name", "empty") == "empty":
        set_pf(h, v, 0, 0, 0)
        return
    if getattr(obj, "alive", 1) and not getattr(obj, "exploding", 0):
        obj.Display()
        return
    # dead / exploding actor — blank unless a wall/door occupies cell
    if getattr(obj, "name", "") in ("Wall", "Door"):
        obj.Display()
    else:
        set_pf(h, v, 0, 0, 0)


# Non-blocking explosion particles (advance every game tick — never sleep/freeze)
ActiveParticles = []
_PARTICLE_COLORS = (
    (255, 240, 80),
    (255, 180, 20),
    (255, 100, 0),
    (255, 255, 200),
    (220, 60, 0),
)


class BoomParticle(object):
    __slots__ = ("x", "y", "px", "py", "vx", "vy", "life", "rgb")

    def __init__(self, x, y, vx, vy, life, rgb):
        self.x = float(x)
        self.y = float(y)
        self.px = int(round(x))
        self.py = int(round(y))
        self.vx = float(vx)
        self.vy = float(vy)
        self.life = int(life)
        self.rgb = rgb


def show_robot_explosion(h, v, big=False):
    """
    Spawn a non-blocking particle burst at (h,v).
    Game loop keeps running; particles advance in tick_explosions().
    big=True → denser, longer-lived burst (final human death).
    """
    # Center flash (instant, no wait)
    if in_room(h, v):
        set_pf(h, v, 255, 220, 40)

    count = 28 if big else 12
    life_lo, life_hi = (14, 28) if big else (8, 16)
    speed_hi = 0.85 if big else 0.55

    # Burst outward in many directions
    for i in range(count):
        ang = (i / float(count)) * 6.28318 + random.uniform(-0.15, 0.15)
        speed = 0.30 + random.random() * speed_hi
        vx = math.cos(ang) * speed + random.uniform(-0.12, 0.12)
        vy = math.sin(ang) * speed + random.uniform(-0.12, 0.12)
        life = random.randint(life_lo, life_hi)
        rgb = _PARTICLE_COLORS[i % len(_PARTICLE_COLORS)]
        ActiveParticles.append(BoomParticle(h, v, vx, vy, life, rgb))

    sparks = 10 if big else 4
    for _ in range(sparks):
        vx = random.uniform(-0.35, 0.35)
        vy = random.uniform(-0.35, 0.35)
        ActiveParticles.append(BoomParticle(
            h, v, vx, vy, random.randint(life_lo, life_hi),
            (255, 255, 255),
        ))


def _hud_pixel_ok(px, py):
    """True only for the right-half HUD (never the left 32×32 map)."""
    return (HUD_H0 <= px < LED.HatWidth) and (0 <= py < LED.HatHeight)


def _paint_death_banner(banner, base_h, v0, rgb):
    """Draw banner lit cells; clipped to HUD half so the map is never touched."""
    r, g, b = rgb
    w, hgt = banner.width, banner.height
    grid = banner.grid
    for count in range(w * hgt):
        if count >= len(grid) or grid[count] != 1:
            continue
        y, x = divmod(count, w)
        px, py = base_h + x, v0 + y
        if _hud_pixel_ok(px, py):
            LED.setpixel(px, py, r, g, b)


def _erase_death_banner(banner, base_h, v0):
    """Blank previous banner pixels on HUD only (never wipe map cells)."""
    w, hgt = banner.width, banner.height
    grid = banner.grid
    for count in range(w * hgt):
        if count >= len(grid) or grid[count] != 1:
            continue
        y, x = divmod(count, w)
        px, py = base_h + x, v0 + y
        if _hud_pixel_ok(px, py):
            LED.setpixel(px, py, 0, 0, 0)


def show_human_death_interlude(h, v, final=False):
    """
    On every human death: explosion + scroll an excited robot gloat while lingering.
    final=True → bigger multi-wave blast and longer hold before GAME OVER.
    """
    msg = random.choice(ROBOT_KILL_LINES)
    print("[DotZerk] Death taunt — robots: {}{}".format(
        msg, " (FINAL)" if final else ""))

    try:
        banner = LED.CreateBannerSprite(str(msg).upper())
    except Exception as e:
        print("[DotZerk] death banner fail: {}".format(e))
        banner = None

    v0 = STATUS_V  # HUD status band only (right half)
    # Enter from just past the right edge of the HUD, never the map
    scroll_h = float(LED.HatWidth + 2)
    drawn_h = None
    rgb = TAUNT_RGB

    # Initial blast
    show_robot_explosion(h, v, big=final)
    duration = FINAL_DEATH_SECONDS if final else DEATH_INTERLUDE_SECONDS
    t0 = time.time()
    next_wave = t0 + 0.35
    wave = 1
    last_tick = t0
    pps = 28.0

    # Include final 3s linger in total time so the gloat keeps scrolling
    total = duration + (3.0 if final else 0.0)
    while time.time() - t0 < total:
        now = time.time()
        in_blast = (now - t0) < duration
        if final and in_blast and wave < 4 and now >= next_wave:
            show_robot_explosion(h, v, big=True)
            wave += 1
            next_wave = now + 0.40

        tick_particles()

        # Keep room entities under sparks
        if int((now - t0) * 20) % 4 == 0:
            for d in (MazeWorld.Door1, MazeWorld.Door2, MazeWorld.Door3, MazeWorld.Door4):
                if d.alive:
                    d.Display()
            for bot in Robots:
                if bot.alive and not bot.exploding:
                    bot.Display()
            if RobotBob.alive:
                set_pf(RobotBob.h, RobotBob.v, OTTO_RGB[0], OTTO_RGB[1], OTTO_RGB[2])
            draw_lives_dots()

        # Scroll gloat left across the HUD status band only (clip h >= HUD_H0)
        # Keeps looping for the whole linger — never freezes mid-message
        if banner is not None:
            dt = now - last_tick
            if dt < 0:
                dt = 0.0
            if dt > 0.08:
                dt = 0.08
            last_tick = now
            scroll_h -= pps * dt
            new_h = int(math.floor(scroll_h))
            if drawn_h is None:
                _paint_death_banner(banner, new_h, v0, rgb)
                drawn_h = new_h
            elif new_h != drawn_h:
                _erase_death_banner(banner, drawn_h, v0)
                # loop when fully past left edge of HUD (not past map origin)
                if scroll_h + banner.width < float(HUD_H0):
                    scroll_h = float(LED.HatWidth + 2)
                    new_h = int(math.floor(scroll_h))
                _paint_death_banner(banner, new_h, v0, rgb)
                drawn_h = new_h

        time.sleep(0.03)

    # Drain sparks (keep last gloat frame painted)
    while ActiveParticles:
        tick_particles()
        time.sleep(0.02)
    if banner is not None and drawn_h is not None:
        _erase_death_banner(banner, drawn_h, v0)


def show_final_human_death(h, v):
    """Last life: prolonged death interlude then caller shows GAME OVER."""
    show_human_death_interlude(h, v, final=True)


def pick_random_room_and_spawn():
    """
    After a non-final death, warp to a random map room and place the human
    near a sensible entry edge.
    """
    global DirectionOfTravel
    MazeWorld.CurrentRoomH = random.randint(0, ROOMS_H - 1)
    MazeWorld.CurrentRoomV = random.randint(0, ROOMS_V - 1)
    DirectionOfTravel = random.choice(list(DIRS_CARDINAL))
    # Spawn opposite the locked entry door (as if just walked in that way)
    if DirectionOfTravel == 1:      # traveling N → enter from south
        Human.h = random.randint(ROOM // 4, 3 * ROOM // 4)
        Human.v = ROOM - 3
    elif DirectionOfTravel == 5:    # traveling S → enter from north
        Human.h = random.randint(ROOM // 4, 3 * ROOM // 4)
        Human.v = 2
    elif DirectionOfTravel == 3:    # traveling E → enter from west
        Human.h = 2
        Human.v = random.randint(ROOM // 4, 3 * ROOM // 4)
    else:                           # traveling W → enter from east
        Human.h = ROOM - 3
        Human.v = random.randint(ROOM // 4, 3 * ROOM // 4)
    Human.direction = Human.scandirection = DirectionOfTravel
    print("[DotZerk] Respawn random room {},{} dir={}".format(
        MazeWorld.CurrentRoomH, MazeWorld.CurrentRoomV, DirectionOfTravel))


def tick_particles():
    """
    Advance all active explosion particles one step.
    Erase previous pixel, move, redraw — never blocks the game.
    """
    if not ActiveParticles:
        return

    still = []
    for p in ActiveParticles:
        # Erase previous cell (restore playfield under it)
        if in_room(p.px, p.py):
            restore_pf_cell(p.px, p.py)
            # Re-stamp living actors if we wiped them
            if Human.alive and not Human.exploding and Human.h == p.px and Human.v == p.py:
                Human.Display()
            for bot in Robots:
                if bot.alive and not bot.exploding and bot.h == p.px and bot.v == p.py:
                    bot.Display()
            if RobotBob.alive and RobotBob.h == p.px and RobotBob.v == p.py:
                set_pf(RobotBob.h, RobotBob.v, OTTO_RGB[0], OTTO_RGB[1], OTTO_RGB[2])

        p.life -= 1
        if p.life <= 0:
            continue

        p.x += p.vx
        p.y += p.vy
        # light drag
        p.vx *= 0.92
        p.vy *= 0.92
        nx = int(round(p.x))
        ny = int(round(p.y))
        p.px, p.py = nx, ny

        if in_room(nx, ny):
            # fade toward darker as life drains
            fade = max(0.25, min(1.0, p.life / 12.0))
            r = int(p.rgb[0] * fade)
            g = int(p.rgb[1] * fade)
            b = int(p.rgb[2] * fade)
            set_pf(nx, ny, r, g, b)
            still.append(p)
        # else: left the room — drop

    ActiveParticles[:] = still


# 8-way compass (same as LEDarcade CalculateDotMovement8Way):
#   8 1 2
#   7 · 3
#   6 5 4
# 1=N 2=NE 3=E 4=SE 5=S 6=SW 7=W 8=NW
DIRS_8 = (1, 2, 3, 4, 5, 6, 7, 8)
DIRS_CARDINAL = (1, 3, 5, 7)  # N E S W — room exits / doors


def calc_move(h, v, direction):
    """Step one cell in an 8-way direction."""
    if direction == 1:      # N
        v -= 1
    elif direction == 2:    # NE
        h += 1
        v -= 1
    elif direction == 3:    # E
        h += 1
    elif direction == 4:    # SE
        h += 1
        v += 1
    elif direction == 5:    # S
        v += 1
    elif direction == 6:    # SW
        h -= 1
        v += 1
    elif direction == 7:    # W
        h -= 1
    elif direction == 8:    # NW
        h -= 1
        v -= 1
    return h, v


def turn_left(d):
    """45° left (counter-clockwise) on the 8-way rose."""
    return {1: 8, 8: 7, 7: 6, 6: 5, 5: 4, 4: 3, 3: 2, 2: 1}.get(d, d)


def turn_right(d):
    """45° right (clockwise) on the 8-way rose."""
    return {1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 7, 7: 8, 8: 1}.get(d, d)


def reverse_dir(d):
    return {1: 5, 5: 1, 2: 6, 6: 2, 3: 7, 7: 3, 4: 8, 8: 4}.get(d, d)


def point_toward(sh, sv, th, tv):
    """8-way facing from (sh,sv) toward (th,tv)."""
    try:
        return LED.PointTowardsObject8Way(sh, sv, th, tv)
    except Exception:
        dh = th - sh
        dv = tv - sv
        if dh == 0 and dv < 0:
            return 1
        if dh > 0 and dv < 0:
            return 2
        if dh > 0 and dv == 0:
            return 3
        if dh > 0 and dv > 0:
            return 4
        if dh == 0 and dv > 0:
            return 5
        if dh < 0 and dv > 0:
            return 6
        if dh < 0 and dv == 0:
            return 7
        if dh < 0 and dv < 0:
            return 8
        return random.randint(1, 8)


def color_rgb(idx):
    try:
        return LED.ColorList[idx]
    except Exception:
        return (20, 20, 80)


#------------------------------------------------------------------------------
# World
#------------------------------------------------------------------------------
class ZerkWorld(object):
    def __init__(self):
        self.width = MAP_W
        self.height = MAP_H
        self.Map = MAP
        self.CurrentRoomH = 0
        self.CurrentRoomV = 3  # start bottom-left like HD
        self.Door1 = DoorObj(DOOR_MID, 0)
        self.Door2 = DoorObj(ROOM - 1, DOOR_MID)
        self.Door3 = DoorObj(DOOR_MID, ROOM - 1)
        self.Door4 = DoorObj(0, DOOR_MID)
        self.Playfield = [[Empty for _ in range(ROOM)] for _ in range(ROOM)]

    def room_origin(self):
        return self.CurrentRoomH * ROOM, self.CurrentRoomV * ROOM

    def clear_playfield(self):
        self.Playfield = [[Empty for _ in range(ROOM)] for _ in range(ROOM)]

    def copy_map_to_playfield(self):
        oh, ov = self.room_origin()
        self.clear_playfield()
        for d in (self.Door1, self.Door2, self.Door3, self.Door4):
            d.alive = 0
            d.locked = 0

        for V in range(ROOM):
            for H in range(ROOM):
                try:
                    sd = self.Map[ov + V][oh + H]
                except Exception:
                    sd = 14
                if sd == 0:
                    self.Playfield[H][V] = Empty
                    continue
                if sd == 21:
                    # Door cells: place one door object at canonical mid-edge
                    if V == 0 and abs(H - DOOR_MID) <= 1:
                        self.Door1.alive = 1
                        self.Door1.h, self.Door1.v = H, V
                        self.Playfield[H][V] = self.Door1
                    elif H == ROOM - 1 and abs(V - DOOR_MID) <= 1:
                        self.Door2.alive = 1
                        self.Door2.h, self.Door2.v = H, V
                        self.Playfield[H][V] = self.Door2
                    elif V == ROOM - 1 and abs(H - DOOR_MID) <= 1:
                        self.Door3.alive = 1
                        self.Door3.h, self.Door3.v = H, V
                        self.Playfield[H][V] = self.Door3
                    elif H == 0 and abs(V - DOOR_MID) <= 1:
                        self.Door4.alive = 1
                        self.Door4.h, self.Door4.v = H, V
                        self.Playfield[H][V] = self.Door4
                    else:
                        # extra door-colored cells near edges → open door pixels
                        r, g, b = color_rgb(21)
                        self.Playfield[H][V] = WallObj(H, V, r, g, b)
                        # treat non-canonical door paint as passable floor
                        self.Playfield[H][V] = Empty
                    continue
                r, g, b = color_rgb(sd)
                self.Playfield[H][V] = WallObj(H, V, r, g, b)

    def display_playfield(self):
        for y in range(ROOM):
            for x in range(ROOM):
                obj = self.Playfield[x][y]
                if obj is Empty or obj.name == "empty":
                    set_pf(x, y, 0, 0, 0)
                else:
                    obj.Display()

    def display_window_scroll(self, h0, v0):
        """Draw a ROOM×ROOM window of the big map at map origin (h0,v0)."""
        for V in range(ROOM):
            for H in range(ROOM):
                try:
                    sd = self.Map[v0 + V][h0 + H]
                except Exception:
                    sd = 0
                if sd == 0:
                    set_pf(H, V, 0, 0, 0)
                else:
                    r, g, b = color_rgb(sd)
                    set_pf(H, V, r, g, b)


#------------------------------------------------------------------------------
# Game state
#------------------------------------------------------------------------------
MazeWorld = ZerkWorld()
DotZerkScore = 0
DotZerkHighScore = 0
DotZerkGamesPlayed = 0
ExitingRoom = 0
DirectionOfTravel = 3  # 8-way East
RobotsAlive = 0
GameStartTime = 0.0                   # set when a play session begins
ChickenUntil = 0.0                    # wall-clock until status shows CHICKEN
TauntMsg = ""                         # insult text for this room
TauntLastMsg = ""                     # avoid back-to-back repeat
TauntPixels = []                      # precomputed [(dx,dy)] lit cells
TauntWidth = 0
TauntScrollH = 0.0                    # float left edge (sub-pixel)
TauntDrawnH = None                    # last integer h painted
TauntLastTick = 0.0
TauntDone = True                      # True = no marquee this room
TauntPauseUntil = 0.0                 # wall time until next pass may start

Human = Actor(2, 2, LED.SDMedGreenR, LED.SDMedGreenG, LED.SDMedGreenB, 2, HUMAN_BASE_SPEED, "Human")
Human.lives = HUMAN_START_LIVES

# One bullet at a time (same rule as robots)
HumanMissile1 = Actor(-1, -1, 200, 200, 200, 1, MISSILE_SPEED, "HumanMissile")
HumanMissiles = (HumanMissile1,)

Robots = [
    Actor(10, 10, LED.SDLowRedR, LED.SDLowRedG, LED.SDLowRedB, 3, ROBOT_SPEED, "Robot"),
    Actor(12, 12, LED.SDLowRedR, LED.SDLowRedG, LED.SDLowRedB, 3, ROBOT_SPEED + 1 * _SPEED_SCALE, "Robot"),
    Actor(14, 14, LED.SDLowRedR, LED.SDLowRedG, LED.SDLowRedB, 3, ROBOT_SPEED + 2 * _SPEED_SCALE, "Robot"),
    Actor(16, 16, LED.SDLowRedR, LED.SDLowRedG, LED.SDLowRedB, 3, ROBOT_SPEED + 3 * _SPEED_SCALE, "Robot"),
]
# Yellow bouncing ball (Evil Otto) — invincible, appears after OTTO_APPEAR_SECONDS
RobotBob = Actor(20, 20, OTTO_RGB[0], OTTO_RGB[1], OTTO_RGB[2], 1, OTTO_TICK, "Otto")
RobotBob.fx = 20.0
RobotBob.fy = 20.0
RobotBob.base_x = 20.0                # hop origin (closes in on human each bounce)
RobotBob.base_y = 20.0
RobotBob.bounce_phase = 0             # 0 .. OTTO_BOUNCE_STEPS-1
RobotBob.bounce_height = OTTO_BOUNCE_HEIGHT0
RobotBob.bounce_count = 0

# One dedicated missile per robot (one white bullet each at a time)
ROBOT_MISSILE_RGB = (255, 255, 255)   # white shot
RobotMissiles = [
    Actor(-5, -1, ROBOT_MISSILE_RGB[0], ROBOT_MISSILE_RGB[1], ROBOT_MISSILE_RGB[2],
          0, MISSILE_SPEED, "RobotMissile")
    for _ in range(len(Robots))
]
for _i, _bot in enumerate(Robots):
    _bot.missile = RobotMissiles[_i]

# Rooms cleared this run — robots may shoot only after the first room
RoomsCompleted = 0


#------------------------------------------------------------------------------
# HUD
#------------------------------------------------------------------------------
def clear_hud():
    for h in range(HUD_H0, LED.HatWidth):
        for v in range(0, LED.HatHeight):
            LED.setpixel(h, v, 0, 0, 0)


def draw_lives_dots():
    """
    Lives as green dots on the bottom-left of the playfield (PacDot style).
    Drawn on the bottom border row: h=1,3,5.
    """
    v = ROOM - 1
    for i in range(HUMAN_START_LIVES):
        h = 1 + i * 2
        if i < max(0, Human.lives):
            set_pf(h, v, LIFE_DOT_RGB[0], LIFE_DOT_RGB[1], LIFE_DOT_RGB[2])
        else:
            # empty life slot — restore whatever the map has there
            restore_pf_cell(h, v)


#------------------------------------------------------------------------------
# Scores (ClockConfig.ini [scores], same pattern as PacDot / SpaceDot)
#------------------------------------------------------------------------------
def LoadDotZerkScores():
    """Reload DotZerk high score / games played from ClockConfig.ini."""
    global DotZerkHighScore, DotZerkGamesPlayed
    try:
        LED.LoadConfigData()
        DotZerkHighScore = int(getattr(LED, "DotZerkHighScore", 0) or 0)
        DotZerkGamesPlayed = int(getattr(LED, "DotZerkGamesPlayed", 0) or 0)
    except Exception as e:
        print("[DotZerk] LoadDotZerkScores: {}".format(e))
        DotZerkHighScore = 0
        DotZerkGamesPlayed = 0
    print("[DotZerk] Loaded high score={}  games={}".format(
        DotZerkHighScore, DotZerkGamesPlayed))


def SaveDotZerkScores():
    """Persist DotZerk high score / games played into ClockConfig.ini."""
    global DotZerkHighScore, DotZerkGamesPlayed
    try:
        LED.DotZerkHighScore = int(DotZerkHighScore)
        LED.DotZerkGamesPlayed = int(DotZerkGamesPlayed)
        LED.SaveConfigData()
        print("[DotZerk] Saved high score={}  games={}".format(
            DotZerkHighScore, DotZerkGamesPlayed))
    except Exception as e:
        print("[DotZerk] SaveDotZerkScores: {}".format(e))


def MaybeUpdateHighScore():
    """If current run beat the high score, update + save."""
    global DotZerkHighScore, DotZerkScore
    if DotZerkScore > DotZerkHighScore:
        DotZerkHighScore = DotZerkScore
        SaveDotZerkScores()
        return True
    return False


def start_room_taunt():
    """
    Sometimes pick an insult for this room. First pass is delayed; between
    passes there is a long quiet gap so marquee is not constant noise.
    """
    global TauntMsg, TauntLastMsg, TauntPixels, TauntWidth
    global TauntScrollH, TauntDrawnH, TauntLastTick, TauntDone, TauntPauseUntil

    TauntPixels = []
    TauntDrawnH = None
    TauntDone = True
    TauntPauseUntil = 0.0

    if random.random() > TAUNT_ROOM_CHANCE:
        print("[DotZerk] Room taunt: (none this room)")
        return

    choices = list(ROBOT_TAUNTS)
    if len(choices) > 1 and TauntLastMsg in choices:
        try:
            choices.remove(TauntLastMsg)
        except ValueError:
            pass
    TauntMsg = random.choice(choices)
    TauntLastMsg = TauntMsg
    try:
        banner = LED.CreateBannerSprite(str(TauntMsg).upper())
    except Exception as e:
        print("[DotZerk] taunt banner fail '{}': {}".format(TauntMsg, e))
        return

    w = banner.width
    hgt = banner.height
    grid = banner.grid
    for count in range(w * hgt):
        if count < len(grid) and grid[count] == 1:
            y, x = divmod(count, w)
            TauntPixels.append((x, y))
    TauntWidth = w
    TauntScrollH = float(LED.HatWidth + TAUNT_GAP)
    TauntDrawnH = None
    TauntLastTick = time.time()
    TauntDone = False
    # Quiet period before the first scroll of this room
    delay = random.uniform(TAUNT_START_DELAY[0], TAUNT_START_DELAY[1])
    TauntPauseUntil = time.time() + delay
    print("[DotZerk] Room taunt: {} (starts in {:.0f}s)".format(TauntMsg, delay))


def _status_override():
    """Static status wins over marquee: CHICKEN / GO."""
    if ChickenUntil and time.time() < ChickenUntil:
        return ("CHICKEN",
                LED.HighYellow if hasattr(LED, "HighYellow") else (220, 200, 0))
    if count_robots_alive() == 0:
        return ("GO",
                LED.HighYellow if hasattr(LED, "HighYellow") else (220, 200, 0))
    return None


def clear_status_strip():
    for h in range(HUD_H0, LED.HatWidth):
        for v in range(STATUS_V, min(LED.HatHeight, STATUS_V + STATUS_HGT)):
            LED.setpixel(h, v, 0, 0, 0)


def _taunt_blit(base_h, rgb):
    """Room-taunt marquee pixels — strictly right-half HUD, never the map."""
    if not TauntPixels:
        return
    r, g, b = rgb
    for dx, dy in TauntPixels:
        px = base_h + dx
        py = STATUS_V + dy
        if not _hud_pixel_ok(px, py):
            continue
        # Also keep text in the status band vertically
        if py < STATUS_V or py >= STATUS_V + STATUS_HGT:
            continue
        LED.setpixel(px, py, r, g, b)


def erase_taunt_at(base_h):
    if base_h is None:
        return
    _taunt_blit(base_h, (0, 0, 0))


def paint_taunt_at(base_h):
    if base_h is None:
        return
    _taunt_blit(base_h, TAUNT_RGB)


def tick_taunt_scroll():
    """
    Occasional marquee: scrolls only when not in a quiet gap.
    After each full pass, wait TAUNT_LOOP_GAP before the next.
    """
    global TauntScrollH, TauntDrawnH, TauntLastTick, TauntDone, TauntPauseUntil

    if _status_override() is not None:
        return
    if TauntDone or not TauntPixels:
        return

    now = time.time()
    # Quiet gap — no paint, no motion
    if now < TauntPauseUntil:
        return

    if TauntLastTick <= 0 or TauntLastTick < TauntPauseUntil:
        # Just left a pause — reset timing so we don't jump
        TauntLastTick = now
        return
    dt = now - TauntLastTick
    if dt < 0:
        dt = 0.0
    if dt > 0.25:
        dt = 0.25
    TauntLastTick = now

    TauntScrollH -= TAUNT_SCROLL_PPS * dt
    target_h = int(math.floor(TauntScrollH))

    # End of pass → long quiet gap before re-entry
    if TauntScrollH + float(TauntWidth) < float(HUD_H0):
        erase_taunt_at(TauntDrawnH)
        TauntDrawnH = None
        TauntScrollH = float(LED.HatWidth + TAUNT_GAP)
        gap = random.uniform(TAUNT_LOOP_GAP[0], TAUNT_LOOP_GAP[1])
        TauntPauseUntil = now + gap
        TauntLastTick = 0.0
        return

    if TauntDrawnH is None:
        paint_taunt_at(target_h)
        TauntDrawnH = target_h
        return

    if target_h == TauntDrawnH:
        return

    steps = 0
    while TauntDrawnH > target_h and steps < 4:
        erase_taunt_at(TauntDrawnH)
        TauntDrawnH -= 1
        paint_taunt_at(TauntDrawnH)
        steps += 1
    if TauntDrawnH != target_h:
        erase_taunt_at(TauntDrawnH)
        paint_taunt_at(target_h)
        TauntDrawnH = target_h


def draw_hud():
    """
    Time + score on top; status is CHICKEN / GO / scrolling taunt.
    While marquee is mid-scroll, do not wipe the status strip.
    """
    override = _status_override()
    # Marquee only when active and not in a quiet gap
    scrolling = (
        (not TauntDone) and bool(TauntPixels) and override is None
        and time.time() >= TauntPauseUntil
    )

    try:
        def right_msg(v, text, rgb):
            """Right-justify in HUD; clip any pixels that would spill onto the map."""
            msg = str(text).upper()
            try:
                banner = LED.CreateBannerSprite(msg)
            except Exception:
                banner = None
            if banner is None:
                return
            h = LED.HatWidth - banner.width - 1
            if h < HUD_H0:
                h = HUD_H0  # keep origin in HUD; still clip paint below
            r, g, b = rgb
            w, hgt = banner.width, banner.height
            grid = banner.grid
            for count in range(w * hgt):
                if count >= len(grid) or grid[count] != 1:
                    continue
                y, x = divmod(count, w)
                px, py = h + x, v + y
                if _hud_pixel_ok(px, py):
                    LED.setpixel(px, py, r, g, b)

        if scrolling:
            # Clear time/score band only
            for h in range(HUD_H0, LED.HatWidth):
                for v in range(0, STATUS_V):
                    LED.setpixel(h, v, 0, 0, 0)
        else:
            clear_hud()

        right_msg(1, time.strftime("%H:%M"), LED.MedCyan)
        right_msg(10, str(DotZerkScore), LED.MedGreen)

        if override is not None:
            clear_status_strip()
            text, rgb = override
            right_msg(STATUS_V, text, rgb)
        elif scrolling:
            # Marquee owned by tick_taunt_scroll — re-stamp current frame
            if TauntDrawnH is not None:
                paint_taunt_at(TauntDrawnH)
        # else: taunt finished — status blank
    except Exception as e:
        print(f"[DotZerk] HUD: {e}")

    draw_lives_dots()


#------------------------------------------------------------------------------
# Room / playfield ops
#------------------------------------------------------------------------------
def lock_entry_door():
    """Lock the door we just entered through (can't leave until room is clear)."""
    global DirectionOfTravel
    for d in (MazeWorld.Door1, MazeWorld.Door2, MazeWorld.Door3, MazeWorld.Door4):
        d.locked = 0
    # DirectionOfTravel is 8-way cardinal: 1N 3E 5S 7W
    if DirectionOfTravel == 1:       # entered going north → lock south
        MazeWorld.Door3.locked = 1
    elif DirectionOfTravel == 3:     # going east → lock west
        MazeWorld.Door4.locked = 1
    elif DirectionOfTravel == 5:     # going south → lock north
        MazeWorld.Door1.locked = 1
    elif DirectionOfTravel == 7:     # going west → lock east
        MazeWorld.Door2.locked = 1


def count_robots_alive():
    """Living red robots only (Otto does not block room-clear / escape)."""
    return sum(1 for b in Robots if b.alive)


def unlock_all_doors():
    """When all robots are dead, every exit opens so the human can escape."""
    for d in (MazeWorld.Door1, MazeWorld.Door2, MazeWorld.Door3, MazeWorld.Door4):
        if d.alive:
            d.locked = 0
            d.Display()


def open_exit_goals():
    """(h, v) of every unlocked, map-present door."""
    goals = []
    for d in (MazeWorld.Door1, MazeWorld.Door2, MazeWorld.Door3, MazeWorld.Door4):
        if d.alive and not d.locked:
            goals.append((d.h, d.v))
    return goals


def door_exit_direction(door_or_h, v=None):
    """World-travel direction (8-way cardinal) when stepping through a door cell."""
    if v is None:
        door = door_or_h
        h, v = door.h, door.v
    else:
        h, v = door_or_h, v
    if v <= 0:
        return 1  # North
    if h >= ROOM - 1:
        return 3  # East
    if v >= ROOM - 1:
        return 5  # South
    if h <= 0:
        return 7  # West
    dist = [(v, 1), (ROOM - 1 - h, 3), (ROOM - 1 - v, 5), (h, 7)]
    dist.sort()
    return dist[0][1]


def bfs_step_toward(start_h, start_v, goals):
    """
    One-step 8-way direction toward nearest goal on empty floor.
    Unlocked door cells are goals; walls/robots/locked doors block.
    """
    if not goals:
        return None
    goal_set = set(goals)
    if (start_h, start_v) in goal_set:
        return None

    parent = {(start_h, start_v): None}  # pos -> (prev, dir_used) or None
    q = deque([(start_h, start_v)])
    found = None

    while q:
        h, v = q.popleft()
        for d in DIRS_8:
            nh, nv = calc_move(h, v, d)
            if (nh, nv) in parent or not in_room(nh, nv):
                continue
            name = scan_cell(nh, nv)
            is_goal = (nh, nv) in goal_set
            if is_goal or name in ("empty", "HumanMissile"):
                parent[(nh, nv)] = ((h, v), d)
                if is_goal:
                    found = (nh, nv)
                    q.clear()
                    break
                q.append((nh, nv))
        if found is not None:
            break

    if found is None:
        return None

    # Reconstruct first step from start
    cur = found
    first_dir = None
    while parent[cur] is not None:
        prev, d = parent[cur]
        first_dir = d
        if prev == (start_h, start_v):
            return d
        cur = prev
    return first_dir


def place_robot(robot):
    for _ in range(200):
        h = randint(2, ROOM - 3)
        v = randint(2, ROOM - 3)
        if MazeWorld.Playfield[h][v].name == "empty":
            # keep away from human
            if abs(h - Human.h) + abs(v - Human.v) < 6:
                continue
            robot.h, robot.v = h, v
            robot.alive = 1
            robot.exploding = 0
            MazeWorld.Playfield[h][v] = robot
            return
    robot.alive = 0


def spawn_otto():
    """
    Yellow arcade ball far from the human.
    Ghosts through walls; each bounce hops closer to the player (not real physics).
    Overlay-only — does not occupy playfield cells.
    """
    candidates = []
    for _ in range(200):
        h = randint(1, ROOM - 2)
        v = randint(1, ROOM - 2)
        dist = abs(h - Human.h) + abs(v - Human.v)
        if dist < 10:
            continue
        candidates.append((dist, h, v))
    if not candidates:
        h = ROOM - 2 if Human.h < ROOM // 2 else 1
        v = ROOM - 2 if Human.v < ROOM // 2 else 1
        candidates.append((0, h, v))

    candidates.sort(reverse=True)
    _, h, v = candidates[0]
    RobotBob.h, RobotBob.v = h, v
    RobotBob.base_x = float(h)
    RobotBob.base_y = float(v)
    RobotBob.fx = float(h)
    RobotBob.fy = float(v)
    RobotBob.bounce_phase = 0
    RobotBob.bounce_height = OTTO_BOUNCE_HEIGHT0
    RobotBob.bounce_count = 0
    RobotBob.r, RobotBob.g, RobotBob.b = OTTO_RGB
    RobotBob.name = "Otto"
    RobotBob.alive = 1
    RobotBob.exploding = 0
    RobotBob.speed = OTTO_TICK

    set_pf(h, v, OTTO_RGB[0], OTTO_RGB[1], OTTO_RGB[2])
    print("[DotZerk] Otto (yellow ball) appears at {},{}".format(h, v))


def deactivate_missiles():
    for m in list(HumanMissiles) + RobotMissiles:
        if 0 <= m.h < ROOM and 0 <= m.v < ROOM:
            if MazeWorld.Playfield[m.h][m.v] is m:
                MazeWorld.Playfield[m.h][m.v] = Empty
        m.alive = 0
        m.exploding = 0
        m.h = m.v = -1


def reset_playfield():
    global RobotsAlive
    MazeWorld.copy_map_to_playfield()
    lock_entry_door()
    if in_room(Human.h, Human.v):
        MazeWorld.Playfield[Human.h][Human.v] = Human
    Human.alive = 1
    Human.exploding = 0
    for bot in Robots:
        bot.alive = 0
        bot.exploding = 0
        place_robot(bot)
    RobotBob.alive = 0
    RobotBob.bounce_phase = 0
    RobotBob.bounce_height = OTTO_BOUNCE_HEIGHT0
    # Otto is overlay-only — never owns playfield cells
    deactivate_missiles()
    # Drop any leftover particles from the previous room/life
    ActiveParticles[:] = []
    RobotsAlive = count_robots_alive()
    MazeWorld.display_playfield()
    for d in (MazeWorld.Door1, MazeWorld.Door2, MazeWorld.Door3, MazeWorld.Door4):
        d.Display()
    Human.Display()
    for bot in Robots:
        if bot.alive:
            bot.Display()
    draw_lives_dots()


def check_maze_boundary():
    MazeWorld.CurrentRoomH = max(0, min(ROOMS_H - 1, MazeWorld.CurrentRoomH))
    MazeWorld.CurrentRoomV = max(0, min(ROOMS_V - 1, MazeWorld.CurrentRoomV))


def exit_room(direction):
    """Scroll to adjacent room and reposition human. direction is 8-way cardinal."""
    global DotZerkScore, DirectionOfTravel, ExitingRoom, RoomsCompleted
    DotZerkScore += 5
    RoomsCompleted += 1
    if RoomsCompleted == 1:
        print("[DotZerk] Robots can now shoot (after first room)")
    deactivate_missiles()
    # Normalize any diagonal door-step into a cardinal exit
    if direction in (2, 4, 6, 8):
        # NE/SE → prefer E if on east door-ish, else use door_exit already cardinal
        if direction in (2, 4):
            direction = 3
        else:
            direction = 7
    DirectionOfTravel = direction

    # Quick scroll preview of map
    steps = 8
    if direction == 1:  # North
        MazeWorld.CurrentRoomV -= 1
        check_maze_boundary()
        for i in range(steps):
            oh, ov = MazeWorld.room_origin()
            MazeWorld.display_window_scroll(oh, ov + ROOM - (i + 1) * (ROOM // steps))
            time.sleep(0.02)
        Human.v = ROOM - 3
        Human.h = max(2, min(ROOM - 3, Human.h))
    elif direction == 5:  # South
        MazeWorld.CurrentRoomV += 1
        check_maze_boundary()
        for i in range(steps):
            oh, ov = MazeWorld.room_origin()
            MazeWorld.display_window_scroll(oh, ov - ROOM + (i + 1) * (ROOM // steps))
            time.sleep(0.02)
        Human.v = 2
        Human.h = max(2, min(ROOM - 3, Human.h))
    elif direction == 3:  # East
        MazeWorld.CurrentRoomH += 1
        check_maze_boundary()
        for i in range(steps):
            oh, ov = MazeWorld.room_origin()
            MazeWorld.display_window_scroll(oh - ROOM + (i + 1) * (ROOM // steps), ov)
            time.sleep(0.02)
        Human.h = 2
        Human.v = max(2, min(ROOM - 3, Human.v))
    elif direction == 7:  # West
        MazeWorld.CurrentRoomH -= 1
        check_maze_boundary()
        for i in range(steps):
            oh, ov = MazeWorld.room_origin()
            MazeWorld.display_window_scroll(oh + ROOM - (i + 1) * (ROOM // steps), ov)
            time.sleep(0.02)
        Human.h = ROOM - 3
        Human.v = max(2, min(ROOM - 3, Human.v))

    ExitingRoom = 0
    reset_playfield()


#------------------------------------------------------------------------------
# Scanning / movement
#------------------------------------------------------------------------------
def scan_cell(h, v):
    if not in_room(h, v):
        return "border"
    obj = MazeWorld.Playfield[h][v]
    if obj is Empty or obj.name == "empty":
        return "empty"
    return obj.name


def scan_ahead(h, v, direction, max_dist=ROOM):
    """Return list of names along a ray (including immediate neighbors for 3-scan)."""
    items = []
    ch, cv = h, v
    for _ in range(max_dist):
        ch, cv = calc_move(ch, cv, direction)
        name = scan_cell(ch, cv)
        items.append(name)
        if name in ("border", "Wall", "Door"):
            break
    return items


def scan_around(h, v, direction):
    """
    ItemList indices similar to HD: [0]=pad, [1]=left, [2]=LF, [3]=front,
    [4]=RF, [5]=right (simplified to L/F/R).
    """
    items = ["NULL"]
    # left
    ld = turn_left(direction)
    lh, lv = calc_move(h, v, ld)
    items.append(scan_cell(lh, lv))
    # front-left-ish: same as left for simplicity
    items.append(items[-1])
    # front
    fh, fv = calc_move(h, v, direction)
    items.append(scan_cell(fh, fv))
    # front-right
    rd = turn_right(direction)
    rh, rv = calc_move(h, v, rd)
    items.append(scan_cell(rh, rv))
    # right
    items.append(items[-1])
    return items


def try_fire_human(direction):
    """Fire the human's single missile. One bullet at a time."""
    global DotZerkScore
    m = HumanMissile1
    if m.alive or m.exploding:
        return  # still in flight
    nh, nv = calc_move(Human.h, Human.v, direction)
    if not in_room(nh, nv):
        return
    name = scan_cell(nh, nv)
    if name not in ("empty", "Robot", "RobotMissile"):
        return
    m.h, m.v = nh, nv
    m.direction = m.scandirection = direction
    m.alive = 1
    m.exploding = 0
    m.explode_tick = 0
    if name == "Robot":
        target = MazeWorld.Playfield[nh][nv]
        target.alive = 0
        target.exploding = 0
        target.Erase()
        if MazeWorld.Playfield[nh][nv] is target:
            MazeWorld.Playfield[nh][nv] = Empty
        DotZerkScore += 10
        m.alive = 0
        m.h = m.v = -1
        show_robot_explosion(nh, nv)
        return
    if name == "RobotMissile":
        other = MazeWorld.Playfield[nh][nv]
        other.alive = 0
        if MazeWorld.Playfield[nh][nv] is other:
            MazeWorld.Playfield[nh][nv] = Empty
        set_pf(nh, nv, 0, 0, 0)
        m.alive = 0
        m.h = m.v = -1
        return
    MazeWorld.Playfield[nh][nv] = m
    m.Display()


def robots_can_shoot():
    """Armed only after the player has left the first room."""
    return RoomsCompleted >= 1


def robot_radar_scan(h, v):
    """
    Radar sweep all 8 directions from (h,v).
    Returns 8-way facing if the human is on a clear line of sight
    (walls/doors/other robots block the beam). Else None.
    """
    if not Human.alive:
        return None
    # Prefer the true bearing toward the human first
    prefer = point_toward(h, v, Human.h, Human.v)
    dirs = [prefer] + [d for d in DIRS_8 if d != prefer]
    for d in dirs:
        for name in scan_ahead(h, v, d, max_dist=ROOM):
            if name == "Human":
                return d
            if name in ("Wall", "Door", "border", "Robot"):
                break
            # empty / missiles — beam continues
    return None


def try_fire_robot(robot, direction):
    """
    Fire this robot's single white radar missile one cell ahead.
    Returns True if a shot was launched. One bullet at a time per robot.
    """
    if not robots_can_shoot():
        return False
    m = getattr(robot, "missile", None)
    if m is None:
        return False
    if m.alive or m.exploding:
        return False  # still in flight

    nh, nv = calc_move(robot.h, robot.v, direction)
    if not in_room(nh, nv):
        return False
    name = scan_cell(nh, nv)
    # Can spawn into empty, or point-blank onto human
    if name not in ("empty", "Human", "HumanMissile"):
        return False

    m.h, m.v = nh, nv
    m.direction = m.scandirection = direction
    m.alive = 1
    m.exploding = 0
    m.r, m.g, m.b = ROBOT_MISSILE_RGB  # white
    m.explode_tick = 0

    if name == "Human":
        Human.alive = 0
        Human.exploding = 1
        m.alive = 0
        m.h = m.v = -1
        return True

    if name == "HumanMissile":
        # mutual cancel
        other = MazeWorld.Playfield[nh][nv]
        other.alive = 0
        if MazeWorld.Playfield[nh][nv] is other:
            MazeWorld.Playfield[nh][nv] = Empty
        set_pf(nh, nv, 0, 0, 0)
        m.alive = 0
        m.h = m.v = -1
        return True

    MazeWorld.Playfield[nh][nv] = m
    set_pf(nh, nv, ROBOT_MISSILE_RGB[0], ROBOT_MISSILE_RGB[1], ROBOT_MISSILE_RGB[2])
    return True


def _human_step(nh, nv, direction):
    """Move human onto (nh,nv) if empty / missile / open door. Sets ExitingRoom on door."""
    global ExitingRoom
    h, v = Human.h, Human.v
    name = scan_cell(nh, nv)
    if name == "Otto":
        Human.alive = 0
        Human.exploding = 1
        return True
    if name == "RobotMissile":
        # Walked into a robot shot
        miss = MazeWorld.Playfield[nh][nv]
        if getattr(miss, "name", "") == "RobotMissile":
            miss.alive = 0
            if MazeWorld.Playfield[nh][nv] is miss:
                MazeWorld.Playfield[nh][nv] = Empty
        Human.alive = 0
        Human.exploding = 1
        return True
    if name == "Door":
        door = MazeWorld.Playfield[nh][nv]
        if getattr(door, "locked", 0) != 0:
            return False
        # Early exit allowed while robots remain (chicken) or after clear
        Human.Erase()
        if MazeWorld.Playfield[h][v] is Human:
            MazeWorld.Playfield[h][v] = Empty
        Human.h, Human.v = nh, nv
        Human.direction = Human.scandirection = door_exit_direction(door)
        ExitingRoom = 1
        return True
    if name not in ("empty", "HumanMissile"):
        return False
    Human.Erase()
    if MazeWorld.Playfield[h][v] is Human:
        MazeWorld.Playfield[h][v] = Empty
    Human.h, Human.v = nh, nv
    Human.direction = Human.scandirection = direction
    MazeWorld.Playfield[nh][nv] = Human
    Human.Display()
    if RobotBob.alive and _otto_touching_human():
        Human.alive = 0
        Human.exploding = 1
    return True


def _otto_touching_human():
    if not RobotBob.alive or not Human.alive:
        return False
    dx = RobotBob.fx - float(Human.h)
    dy = RobotBob.fy - float(Human.v)
    return (dx * dx + dy * dy) <= (OTTO_KILL_DIST * OTTO_KILL_DIST)


def move_otto():
    """
    Arcade bounce (not real physics): hop on a sine, and each landing moves
    the bounce origin closer to the human until contact.
    Ghosts through walls.
    """
    if not RobotBob.alive or RobotBob.exploding:
        return

    old_h, old_v = RobotBob.h, RobotBob.v

    # Advance hop phase
    RobotBob.bounce_phase = (RobotBob.bounce_phase + 1) % OTTO_BOUNCE_STEPS

    # Landing (phase 0): close gap toward human, shrink hop height
    if RobotBob.bounce_phase == 0:
        RobotBob.bounce_count += 1
        tx, ty = float(Human.h), float(Human.v)
        RobotBob.base_x += (tx - RobotBob.base_x) * OTTO_APPROACH
        RobotBob.base_y += (ty - RobotBob.base_y) * OTTO_APPROACH
        RobotBob.bounce_height = max(
            OTTO_MIN_HEIGHT, RobotBob.bounce_height * OTTO_HEIGHT_DECAY
        )
        # Late game: lock base onto human so the last hops land on them
        if RobotBob.bounce_count >= 10:
            RobotBob.base_x = tx
            RobotBob.base_y = ty
            RobotBob.bounce_height = OTTO_MIN_HEIGHT

    # Sine hop: 0 at floor, 1 at apex (phase mid)
    t = RobotBob.bounce_phase / float(OTTO_BOUNCE_STEPS)
    lift = math.sin(t * math.pi) * RobotBob.bounce_height  # up is -v
    nx = RobotBob.base_x
    ny = RobotBob.base_y - lift

    # Clamp to room (still ghost walls)
    nx = max(0.0, min(float(ROOM - 1), nx))
    ny = max(0.0, min(float(ROOM - 1), ny))

    RobotBob.fx, RobotBob.fy = nx, ny
    new_h = int(round(nx))
    new_v = int(round(ny))
    RobotBob.h, RobotBob.v = new_h, new_v

    if (new_h, new_v) != (old_h, old_v):
        restore_pf_cell(old_h, old_v)
        if Human.alive and Human.h == old_h and Human.v == old_v:
            Human.Display()
        for bot in Robots:
            if bot.alive and bot.h == old_h and bot.v == old_v:
                bot.Display()
        draw_lives_dots()

    set_pf(new_h, new_v, OTTO_RGB[0], OTTO_RGB[1], OTTO_RGB[2])

    if _otto_touching_human():
        Human.alive = 0
        Human.exploding = 1


def move_human_escape():
    """
    Room is clear — pathfind (8-way) to the nearest open exit and leave.
    Otto may still be chasing; contact kills.
    """
    global ExitingRoom
    if RobotBob.alive and _otto_touching_human():
        Human.alive = 0
        Human.exploding = 1
        return

    unlock_all_doors()
    h, v = Human.h, Human.v
    goals = open_exit_goals()

    here = MazeWorld.Playfield[h][v] if in_room(h, v) else Empty
    if getattr(here, "name", "") == "Door" and not getattr(here, "locked", 1):
        Human.direction = Human.scandirection = door_exit_direction(here)
        ExitingRoom = 1
        return

    for d in DIRS_8:
        nh, nv = calc_move(h, v, d)
        if scan_cell(nh, nv) == "Door":
            door = MazeWorld.Playfield[nh][nv]
            if getattr(door, "locked", 0) == 0:
                _human_step(nh, nv, d)
                return

    step_dir = bfs_step_toward(h, v, goals)
    if step_dir is not None:
        nh, nv = calc_move(h, v, step_dir)
        if _human_step(nh, nv, step_dir):
            return

    direction = Human.scandirection
    # Try facing, then 45° turns, then reverse
    try_dirs = [direction]
    d = direction
    for _ in range(7):
        d = turn_right(d)
        try_dirs.append(d)
    for d in try_dirs:
        nh, nv = calc_move(h, v, d)
        name = scan_cell(nh, nv)
        if name == "Otto":
            continue
        if name in ("empty", "HumanMissile") or (
            name == "Door" and getattr(MazeWorld.Playfield[nh][nv], "locked", 1) == 0
        ):
            _human_step(nh, nv, d)
            return
        if name in ("Wall", "border", "Door"):
            continue
    Human.scandirection = turn_right(direction)


def move_human():
    global ExitingRoom, RobotsAlive
    h, v = Human.h, Human.v
    direction = Human.scandirection
    RobotsAlive = count_robots_alive()

    # --- Escape mode: all robots dead → head for an exit ---
    if RobotsAlive == 0:
        move_human_escape()
        return

    # --- Combat mode: 8-way hunt / fire; can still take a door early ---
    if RobotBob.alive and _otto_touching_human():
        Human.alive = 0
        Human.exploding = 1
        return

    # Radar-style aim: fire along any of 8 bearings that see a robot
    fired = False
    aim_order = [direction]
    d = direction
    for _ in range(7):
        d = turn_right(d)
        aim_order.append(d)
    for d in aim_order:
        ray = scan_ahead(h, v, d, max_dist=ROOM)
        if "Robot" in ray or "RobotMissile" in ray:
            try_fire_human(d)
            fired = True
            break

    # Under Otto pressure, pathfind to nearest open door (chicken run)
    if RobotBob.alive:
        goals = open_exit_goals()
        step_dir = bfs_step_toward(h, v, goals)
        if step_dir is not None:
            nh, nv = calc_move(h, v, step_dir)
            name = scan_cell(nh, nv)
            if name in ("empty", "HumanMissile", "Door"):
                _human_step(nh, nv, step_dir)
                return

    # Seek nearest living robot for movement (8-way)
    prefer = direction
    nearest = None
    best = 9999
    for bot in Robots:
        if not bot.alive:
            continue
        dist = abs(bot.h - h) + abs(bot.v - v)
        if dist < best:
            best = dist
            nearest = bot
    if nearest is not None:
        prefer = point_toward(h, v, nearest.h, nearest.v)

    front_h, front_v = calc_move(h, v, direction)
    front = scan_cell(front_h, front_v)

    if front == "Otto":
        Human.alive = 0
        Human.exploding = 1
        return

    # Unlocked door ahead: may chicken out early
    if front == "Door":
        door = MazeWorld.Playfield[front_h][front_v]
        if getattr(door, "locked", 0) == 0:
            chance = 0.55 if RobotBob.alive else 0.06
            if random.random() < chance:
                _human_step(front_h, front_v, direction)
                return
        # treat as wall — turn 45°
        Human.scandirection = Human.direction = turn_right(direction)
        return

    if front in ("Wall", "border", "Robot"):
        # Try 45° then 90° then reverse
        for d in (turn_right(direction), turn_left(direction),
                  turn_right(turn_right(direction)), turn_left(turn_left(direction)),
                  reverse_dir(direction)):
            nh, nv = calc_move(h, v, d)
            if scan_cell(nh, nv) == "empty":
                Human.scandirection = Human.direction = d
                return
        Human.scandirection = Human.direction = reverse_dir(direction)
        return

    # Prefer step toward nearest robot when free, else keep heading
    for d in (prefer, direction, turn_right(prefer), turn_left(prefer),
              turn_right(direction), turn_left(direction)):
        nh, nv = calc_move(h, v, d)
        name = scan_cell(nh, nv)
        if name in ("empty", "HumanMissile"):
            _human_step(nh, nv, d)
            if not fired and random.random() < 0.12:
                Human.scandirection = turn_right(Human.scandirection)
            return
        if name == "Door" and getattr(MazeWorld.Playfield[nh][nv], "locked", 1) == 0:
            if random.random() < 0.08:
                _human_step(nh, nv, d)
                return


def move_robot(robot):
    if not robot.alive or robot.exploding:
        return
    h, v = robot.h, robot.v
    direction = robot.scandirection

    # 8-way seek toward human
    prefer = point_toward(h, v, Human.h, Human.v)

    # Radar: after first room, sweep all 8 bearings — white missile if human seen
    if robots_can_shoot():
        radar_dir = robot_radar_scan(h, v)
        if radar_dir is not None:
            if try_fire_robot(robot, radar_dir):
                robot.scandirection = robot.direction = radar_dir
                direction = radar_dir

    # Try to move toward human (8-way)
    try_dirs = [prefer, direction, turn_left(prefer), turn_right(prefer),
                turn_left(turn_left(prefer)), turn_right(turn_right(prefer)),
                reverse_dir(prefer)]
    for d in try_dirs:
        nh, nv = calc_move(h, v, d)
        name = scan_cell(nh, nv)
        if name == "Human":
            Human.alive = 0
            Human.exploding = 1
            return
        if name == "RobotMissile":
            continue
        if name == "empty":
            robot.Erase()
            if MazeWorld.Playfield[h][v] is robot:
                MazeWorld.Playfield[h][v] = Empty
            robot.h, robot.v = nh, nv
            robot.direction = robot.scandirection = d
            MazeWorld.Playfield[nh][nv] = robot
            robot.Display()
            return
        if name == "HumanMissile":
            rh, rv = robot.h, robot.v
            robot.alive = 0
            robot.exploding = 0
            robot.explode_tick = 0
            robot.Erase()
            if MazeWorld.Playfield[h][v] is robot:
                MazeWorld.Playfield[h][v] = Empty
            miss = MazeWorld.Playfield[nh][nv]
            if getattr(miss, "name", "") == "HumanMissile":
                miss.alive = 0
                miss.exploding = 0
                if MazeWorld.Playfield[nh][nv] is miss:
                    MazeWorld.Playfield[nh][nv] = Empty
                set_pf(nh, nv, 0, 0, 0)
            show_robot_explosion(rh, rv)
            return

    # Stuck — turn 45°
    robot.scandirection = turn_right(direction)


def move_missile(missile, owner_is_human):
    global DotZerkScore
    if not missile.alive or missile.exploding:
        return
    h, v = missile.h, missile.v
    nh, nv = calc_move(h, v, missile.direction)

    # leave old cell
    if in_room(h, v) and MazeWorld.Playfield[h][v] is missile:
        MazeWorld.Playfield[h][v] = Empty
        set_pf(h, v, 0, 0, 0)

    if not in_room(nh, nv):
        missile.alive = 0
        missile.h = missile.v = -1
        return

    target = MazeWorld.Playfield[nh][nv]
    name = target.name if target is not Empty else "empty"

    if name == "Wall" or name == "Door" or name == "border":
        missile.alive = 0
        missile.exploding = 1
        missile.explode_tick = 0
        missile.h, missile.v = nh, nv
        # flash
        set_pf(nh, nv, 255, 200, 0)
        return

    if owner_is_human and name == "Robot":
        rh, rv = target.h, target.v
        target.alive = 0
        target.exploding = 0
        target.explode_tick = 0
        target.Erase()
        if MazeWorld.Playfield[nh][nv] is target:
            MazeWorld.Playfield[nh][nv] = Empty
        DotZerkScore += 10
        missile.alive = 0
        missile.exploding = 0
        missile.h = missile.v = -1
        show_robot_explosion(rh, rv)
        return

    # Otto is overlay-only; fizzle missiles that hit his pixel
    if RobotBob.alive and nh == RobotBob.h and nv == RobotBob.v:
        missile.alive = 0
        missile.exploding = 0
        missile.h = missile.v = -1
        set_pf(nh, nv, OTTO_RGB[0], OTTO_RGB[1], OTTO_RGB[2])
        return

    if (not owner_is_human) and name == "Human":
        Human.alive = 0
        Human.exploding = 1
        missile.alive = 0
        return

    if name in ("HumanMissile", "RobotMissile") and target is not missile:
        target.alive = 0
        if MazeWorld.Playfield[nh][nv] is target:
            MazeWorld.Playfield[nh][nv] = Empty
        set_pf(nh, nv, 0, 0, 0)
        missile.alive = 0
        return

    # empty — advance
    missile.h, missile.v = nh, nv
    MazeWorld.Playfield[nh][nv] = missile
    missile.Display()


def tick_explosions():
    """Clear entity explosion flags and advance non-blocking particles."""
    for bot in Robots + [RobotBob]:
        if bot.exploding:
            bot.explode_tick += 1
            if bot.explode_tick > 8:
                bot.exploding = 0
                bot.alive = 0
                if in_room(bot.h, bot.v):
                    set_pf(bot.h, bot.v, 0, 0, 0)
    for m in list(HumanMissiles) + RobotMissiles:
        if m.exploding:
            m.explode_tick += 1
            if m.explode_tick > 4:
                m.exploding = 0
                m.alive = 0
                if in_room(m.h, m.v) and MazeWorld.Playfield[m.h][m.v] is not Empty:
                    # restore wall under flash if needed
                    pass
                if in_room(m.h, m.v):
                    # repaint cell from map
                    oh, ov = MazeWorld.room_origin()
                    try:
                        sd = MazeWorld.Map[ov + m.v][oh + m.h]
                    except Exception:
                        sd = 0
                    if sd and sd != 21:
                        r, g, b = color_rgb(sd)
                        set_pf(m.h, m.v, r, g, b)
                        MazeWorld.Playfield[m.h][m.v] = WallObj(m.h, m.v, r, g, b)
                    else:
                        set_pf(m.h, m.v, 0, 0, 0)
                        MazeWorld.Playfield[m.h][m.v] = Empty
                m.h = m.v = -1

    # Particle bursts run in parallel with the game (no freezes)
    tick_particles()


#------------------------------------------------------------------------------
# Bouncy title intro — Skyfall gravity/bounce, multi-direction entry (PacDot-style)
#------------------------------------------------------------------------------
TITLE_WORD = "DOTZERK"
TITLE_LETTER_ZOOM = 2
TITLE_LETTER_GAP = 1
TITLE_LETTER_RGB = (220, 40, 40)       # alert red
TITLE_LETTER_SHADOW_RGB = (40, 5, 5)
TITLE_LETTER_STAGGER = 0.18            # seconds between letter launches
TITLE_LETTER_GRAVITY = 0.62            # match Skyfall / LEDtv
TITLE_LETTER_BOUNCE_DAMP = 0.44        # energy kept on bounce
TITLE_LETTER_SETTLE_V = 0.38
TITLE_LETTER_MAX_BOUNCES = 4
TITLE_HOLD_SECONDS = 1.5
TITLE_INTRO_MAX_SECONDS = 14.0

# Spawn origins: letters fly in from mixed edges/corners
_TITLE_SPAWN_DIRS = (
    "top", "bottom", "left", "right",
    "top_left", "top_right", "bottom_left", "bottom_right",
)


def _stop_requested(StopEvent):
    try:
        return StopEvent is not None and StopEvent.is_set()
    except Exception:
        return False


def _title_letter_sprite(char):
    ch = char.upper()
    if not ("A" <= ch <= "Z"):
        return None
    idx = ord(ch) - ord("A")
    return LED.TrimSprite(copy.deepcopy(LED.AlphaSpriteList[idx]))


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
                shadow_pixels.append((x * zoom + zh + 1, y * zoom + zv + 1, shadow_rgb))
    return pixels, shadow_pixels, sw * zoom, sh * zoom


def _spawn_xy(rest_x, rest_y, width, height, panel_w, panel_h, direction):
    """Off-screen spawn for a letter (edge or corner)."""
    margin = max(width, height) + 8
    if direction == "top":
        return rest_x, -margin
    if direction == "bottom":
        return rest_x, panel_h + margin
    if direction == "left":
        return -margin, rest_y
    if direction == "right":
        return panel_w + margin, rest_y
    if direction == "top_left":
        return -margin, -margin
    if direction == "top_right":
        return panel_w + margin, -margin
    if direction == "bottom_left":
        return -margin, panel_h + margin
    if direction == "bottom_right":
        return panel_w + margin, panel_h + margin
    return rest_x, -margin


class BounceLetter(object):
    """
    Skyfall-style gravity + bounce, but from any edge/corner.

    Constant acceleration toward rest on each active axis; when the letter
    hits its rest plane it rebounds with damp (same feel as Skyfall drop).
    """

    def __init__(self, char, pixels, shadow_pixels, width, height,
                 rest_x, rest_y, start_x, start_y, drop_delay, gravity=None):
        self.char = char
        self.pixels = pixels
        self.shadow_pixels = shadow_pixels
        self.width = width
        self.height = height
        self.rest_x = float(rest_x)
        self.rest_y = float(rest_y)
        self.x = float(start_x)
        self.y = float(start_y)
        self.vx = 0.0
        self.vy = 0.0
        self.drop_delay = drop_delay
        self.started = False
        self.settled = False
        self.bounce_count = 0
        self.gravity = float(gravity if gravity is not None else TITLE_LETTER_GRAVITY)

        # Fixed pull direction per axis (Skyfall always pulls "down"; we pull toward rest)
        if abs(self.x - self.rest_x) < 0.5:
            self.pull_x = 0.0
            self.x = self.rest_x
            self.vx = 0.0
        else:
            self.pull_x = 1.0 if self.rest_x > self.x else -1.0

        if abs(self.y - self.rest_y) < 0.5:
            self.pull_y = 0.0
            self.y = self.rest_y
            self.vy = 0.0
        else:
            self.pull_y = 1.0 if self.rest_y > self.y else -1.0

        # Small initial kick so motion starts immediately (still gravity-dominated)
        kick = random.uniform(0.6, 1.4)
        self.vx = self.pull_x * kick
        self.vy = self.pull_y * kick

    def _bounce_axis(self, pos, vel, rest, pull):
        """Hit rest plane on one axis; return (pos, vel, bounced)."""
        if pull == 0.0:
            return rest, 0.0, False
        hit = (pull > 0 and pos >= rest) or (pull < 0 and pos <= rest)
        if not hit:
            return pos, vel, False
        pos = rest
        if abs(vel) < TITLE_LETTER_SETTLE_V or self.bounce_count >= TITLE_LETTER_MAX_BOUNCES:
            return pos, 0.0, False
        # Reverse away from rest, keep a fraction of speed (Skyfall bounce)
        vel = -abs(vel) * TITLE_LETTER_BOUNCE_DAMP if pull > 0 else abs(vel) * TITLE_LETTER_BOUNCE_DAMP
        return pos, vel, True

    def update(self, step, elapsed):
        if self.settled:
            self.x = self.rest_x
            self.y = self.rest_y
            return
        if elapsed < self.drop_delay:
            return
        self.started = True

        # Constant acceleration toward rest (Skyfall gravity, multi-axis)
        self.vx += self.pull_x * self.gravity * step
        self.vy += self.pull_y * self.gravity * step
        self.x += self.vx * step
        self.y += self.vy * step

        bounced = False
        self.x, self.vx, bx = self._bounce_axis(self.x, self.vx, self.rest_x, self.pull_x)
        self.y, self.vy, by = self._bounce_axis(self.y, self.vy, self.rest_y, self.pull_y)
        if bx or by:
            bounced = True
            self.bounce_count += 1

        # Settled when both axes are parked on rest
        x_done = (self.pull_x == 0.0) or (
            abs(self.x - self.rest_x) < 0.5 and abs(self.vx) < TITLE_LETTER_SETTLE_V
        )
        y_done = (self.pull_y == 0.0) or (
            abs(self.y - self.rest_y) < 0.5 and abs(self.vy) < TITLE_LETTER_SETTLE_V
        )
        if (x_done and y_done) or self.bounce_count >= TITLE_LETTER_MAX_BOUNCES:
            # Final snap if max bounces hit while still drifting
            if abs(self.x - self.rest_x) < 2.0 and abs(self.y - self.rest_y) < 2.0:
                self.x = self.rest_x
                self.y = self.rest_y
                self.vx = self.vy = 0.0
                self.settled = True
            elif self.bounce_count >= TITLE_LETTER_MAX_BOUNCES:
                # Keep pulling; force settle soon via speed check next frames
                if abs(self.vx) < TITLE_LETTER_SETTLE_V * 2 and abs(self.vy) < TITLE_LETTER_SETTLE_V * 2:
                    self.x = self.rest_x
                    self.y = self.rest_y
                    self.vx = self.vy = 0.0
                    self.settled = True

    def force_settle(self):
        self.x = self.rest_x
        self.y = self.rest_y
        self.vx = self.vy = 0.0
        self.started = True
        self.settled = True

    def draw(self, canvas, panel_w, panel_h):
        sx = int(round(self.x))
        sy = int(round(self.y))
        set_pixel = canvas.SetPixel
        for dx, dy, rgb in self.shadow_pixels:
            px, py = sx + dx, sy + dy
            if 0 <= px < panel_w and 0 <= py < panel_h:
                set_pixel(px, py, *rgb)
        for dx, dy, rgb in self.pixels:
            px, py = sx + dx, sy + dy
            if 0 <= px < panel_w and 0 <= py < panel_h:
                set_pixel(px, py, *rgb)


def _build_title_letters(panel_w, panel_h):
    specs = []
    for char in TITLE_WORD:
        if char == " ":
            continue
        sprite = _title_letter_sprite(char)
        if sprite is None:
            continue
        pixels, shadow_pixels, letter_w, letter_h = _sprite_pixels_zoomed(
            sprite, TITLE_LETTER_ZOOM, TITLE_LETTER_RGB, TITLE_LETTER_SHADOW_RGB,
        )
        specs.append((char, pixels, shadow_pixels, letter_w, letter_h))

    if not specs:
        return []

    total_width = sum(s[3] for s in specs) + TITLE_LETTER_GAP * max(0, len(specs) - 1)
    start_x = max(0, (panel_w - total_width) // 2)
    letter_height = max(s[4] for s in specs)
    rest_y = max(0, (panel_h - letter_height) // 2)

    letters = []
    x_cursor = start_x
    # Shuffle so each run comes from different directions
    dirs = list(_TITLE_SPAWN_DIRS)
    random.shuffle(dirs)
    # Prefer unique dirs first for DOTZERK (7 letters, 8 dirs)
    for index, (char, pixels, shadow_pixels, letter_w, letter_h) in enumerate(specs):
        direction = dirs[index % len(dirs)]
        y_off = letter_height - letter_h
        rest_x = x_cursor
        ry = rest_y + y_off
        sx, sy = _spawn_xy(rest_x, ry, letter_w, letter_h, panel_w, panel_h, direction)
        # Slight per-letter gravity variance for organic stagger feel
        g = TITLE_LETTER_GRAVITY * random.uniform(0.92, 1.12)
        letters.append(BounceLetter(
            char, pixels, shadow_pixels, letter_w, letter_h,
            rest_x, ry, sx, sy,
            drop_delay=index * TITLE_LETTER_STAGGER,
            gravity=g,
        ))
        x_cursor += letter_w + TITLE_LETTER_GAP
    return letters


def _paint_title_letters_to_screen(letters, panel_w, panel_h):
    """
    Freeze settled title into ScreenArray + LED so MoveAnimated* can walk
    a sprite underneath without wiping the word.
    """
    try:
        LED.ClearBigLED()
        LED.ClearBuffers()
    except Exception:
        pass
    for letter in letters:
        letter.force_settle()
        sx = int(round(letter.x))
        sy = int(round(letter.y))
        for dx, dy, rgb in letter.shadow_pixels:
            px, py = sx + dx, sy + dy
            if 0 <= px < panel_w and 0 <= py < panel_h:
                LED.setpixel(px, py, *rgb)
        for dx, dy, rgb in letter.pixels:
            px, py = sx + dx, sy + dy
            if 0 <= px < panel_w and 0 <= py < panel_h:
                LED.setpixel(px, py, *rgb)


def _dotzerk_title_sprites():
    """
    Animated sprites for the title parade: DotZerk robots + running man.
    Order is shuffled by the caller.
    """
    names = (
        "DotZerkRobotWalking",
        "DotZerkRobotWalkingSmall",
        "DotZerkRobot",
        "RunningManSprite",
        "RunningMan2Sprite",
        "RunningMan3Sprite",
    )
    out = []
    for name in names:
        spr = getattr(LED, name, None)
        if spr is not None:
            out.append((name, spr))
    return out


def _walk_sprite_once(name, sprite, direction, StopEvent=None):
    """One cross-screen walk for a title parade sprite under the title."""
    if _stop_requested(StopEvent):
        return False

    is_runner = name.startswith("RunningMan")
    # Full-size idle robot / runners: zoom carefully for panel height
    if name == "DotZerkRobot":
        zoom = 1
        steps_per_frame = 1  # more frames — step each frame for smoother anim
    elif name == "DotZerkRobotWalkingSmall":
        zoom = random.randint(1, 2)
        steps_per_frame = 2
    elif is_runner:
        # Running man sprites are fairly tall — keep zoom modest
        zoom = 1
        steps_per_frame = 1
    else:
        zoom = random.randint(1, 2)
        steps_per_frame = 2
    sleep = 0.03 / max(1, zoom)

    print("[DotZerk] Title sprite — {} {} zoom={}".format(name, direction, zoom))
    # DotZerk robot art faces LEFT by default; RunningMan art faces RIGHT
    # (demo/clock style). Flip only when needed so they don't moonwalk.
    flipped = False
    try:
        need_flip = False
        if hasattr(sprite, "HorizontalFlip"):
            if is_runner:
                need_flip = (direction == "left")
            else:
                need_flip = (direction == "right")
        if need_flip:
            sprite.HorizontalFlip()
            flipped = True
        LED.MoveAnimatedSpriteAcrossScreenStepsPerFrame(
            sprite,
            Position="bottom",
            Vadjust=0,
            direction=direction,
            StepsPerFrame=steps_per_frame,
            ZoomFactor=zoom,
            sleep=sleep,
        )
        return True
    except Exception as e:
        print("[DotZerk] Title sprite walk failed ({}): {}".format(name, e))
        return False
    finally:
        if flipped and hasattr(sprite, "HorizontalFlip"):
            try:
                sprite.HorizontalFlip()
            except Exception:
                pass


TITLE_PARADE_COUNT = 2   # max animated sprites on intro / game-over parade


def _sprite_parade(StopEvent=None, label="Title"):
    """
    Walk up to TITLE_PARADE_COUNT random animated sprites across the bottom
    (DotZerk robots + running man). Left/right alternate.
    """
    if _stop_requested(StopEvent):
        return

    candidates = _dotzerk_title_sprites()
    if not candidates:
        print("[DotZerk] {} parade skipped (no sprites)".format(label))
        return

    random.shuffle(candidates)
    parade = candidates[:TITLE_PARADE_COUNT]
    direction = random.choice(("left", "right"))

    print("[DotZerk] {} parade — {} sprites".format(label, len(parade)))
    for name, sprite in parade:
        if _stop_requested(StopEvent):
            break
        _walk_sprite_once(name, sprite, direction, StopEvent=StopEvent)
        direction = "right" if direction == "left" else "left"
        if not _stop_requested(StopEvent):
            time.sleep(0.12)


def _title_robot_cross(StopEvent=None):
    """Intro: two random walkers under the frozen DOTZERK title."""
    _sprite_parade(StopEvent=StopEvent, label="Title")


def PlayDotZerkTitleIntro(StopEvent=None):
    """
    DOTZERK letters fly in from mixed edges/corners and bounce into place,
    then DotZerk robot sprites parade under the title.
    """
    panel_w = LED.HatWidth
    panel_h = LED.HatHeight
    letters = _build_title_letters(panel_w, panel_h)
    if not letters:
        return

    if _stop_requested(StopEvent):
        print("[DotZerk] Title intro skipped (StopEvent)")
        return

    print("[DotZerk] Title intro — bounce letters from all directions")
    try:
        canvas = LED.TheMatrix.CreateFrameCanvas()
    except Exception:
        canvas = None

    start = time.time()
    last_frame = start
    hold_start = None
    aborted = False

    try:
        while True:
            if _stop_requested(StopEvent):
                print("[DotZerk] Title intro — StopEvent")
                aborted = True
                break

            now = time.time()
            elapsed = now - start
            if elapsed >= TITLE_INTRO_MAX_SECONDS:
                for letter in letters:
                    letter.force_settle()
                break

            frame_dt = max(0.001, now - last_frame)
            last_frame = now
            # ~30fps step units (same family as Skyfall / PacDot)
            step = min(3.0, frame_dt * 30.0)

            for letter in letters:
                letter.update(step, elapsed)

            if hold_start is None and all(letter.settled for letter in letters):
                hold_start = now

            # Short settle beat, then freeze title for robot parade
            if hold_start is not None and (now - hold_start) >= min(0.6, TITLE_HOLD_SECONDS):
                break

            if canvas is not None:
                canvas.Fill(0, 0, 0)
                for letter in letters:
                    if letter.started or letter.settled:
                        letter.draw(canvas, panel_w, panel_h)
                canvas = LED.TheMatrix.SwapOnVSync(canvas)
            else:
                LED.ClearBigLED()
                for letter in letters:
                    if not (letter.started or letter.settled):
                        continue
                    sx = int(round(letter.x))
                    sy = int(round(letter.y))
                    for dx, dy, rgb in letter.pixels:
                        LED.setpixel(sx + dx, sy + dy, *rgb)
                time.sleep(0.03)

    except KeyboardInterrupt:
        aborted = True

    if not aborted and not _stop_requested(StopEvent):
        # Freeze DOTZERK into ScreenArray, then robot walks underneath
        _paint_title_letters_to_screen(letters, panel_w, panel_h)
        time.sleep(0.35)
        _title_robot_cross(StopEvent=StopEvent)
        # Hold finished title a beat after robot exits
        if not _stop_requested(StopEvent):
            time.sleep(0.4)

    try:
        LED.ClearBigLED()
        LED.ClearBuffers()
    except Exception:
        pass


#------------------------------------------------------------------------------
# Main play
#------------------------------------------------------------------------------
def PlayDotZerk(Duration=DURATION_DEFAULT, StopEvent=None):
    global DotZerkScore, DotZerkHighScore, DotZerkGamesPlayed
    global ExitingRoom, DirectionOfTravel, RobotsAlive
    global GameStartTime, ChickenUntil, TauntMsg, TauntLastMsg, RoomsCompleted
    global TauntPixels, TauntWidth, TauntScrollH, TauntDrawnH, TauntLastTick
    global TauntDone, TauntPauseUntil

    print("[DotZerk] PlayDotZerk start  ROOM={}×{}  Duration={} min".format(
        ROOM, ROOM, Duration))
    LoadDotZerkScores()
    start_time = time.time()
    GameStartTime = start_time
    ChickenUntil = 0.0
    TauntMsg = ""
    TauntLastMsg = ""
    TauntPixels = []
    TauntWidth = 0
    TauntScrollH = 0.0
    TauntDrawnH = None
    TauntLastTick = 0.0
    TauntDone = True
    TauntPauseUntil = 0.0
    DotZerkScore = 0
    RoomsCompleted = 0
    Human.lives = HUMAN_START_LIVES
    Human.h, Human.v = 4, 4
    Human.direction = Human.scandirection = 3  # East (8-way)
    DirectionOfTravel = 3                     # entered traveling east
    MazeWorld.CurrentRoomH = 0
    MazeWorld.CurrentRoomV = 3
    ExitingRoom = 0
    # Re-bind dedicated missiles (safe if list was rebuilt)
    for i, bot in enumerate(Robots):
        if i < len(RobotMissiles):
            bot.missile = RobotMissiles[i]

    LED.ClearBigLED()
    LED.ClearBuffers()

    finished = False
    while not finished and Human.lives > 0:
        if StopEvent is not None and StopEvent.is_set():
            print("[DotZerk] StopEvent")
            return

        try:
            _h, m_e, _s = LED.GetElapsedTime(start_time, time.time())
        except Exception:
            m_e = (time.time() - start_time) / 60.0
        if m_e >= Duration:
            print("[DotZerk] Duration reached")
            break

        Human.alive = 1
        Human.exploding = 0
        Human.speed = HUMAN_BASE_SPEED
        moves = 0
        level_finished = False
        ExitingRoom = 0
        RobotBob.alive = 0
        room_start = time.time()

        reset_playfield()
        start_room_taunt()  # one insult for this room
        draw_hud()
        print("[DotZerk] Room {},{}  lives={}  score={}".format(
            MazeWorld.CurrentRoomH, MazeWorld.CurrentRoomV, Human.lives, DotZerkScore))

        while not level_finished and Human.alive and Human.lives > 0:
            if StopEvent is not None and StopEvent.is_set():
                return
            try:
                _h, m_e, _s = LED.GetElapsedTime(start_time, time.time())
            except Exception:
                m_e = (time.time() - start_time) / 60.0
            if m_e >= Duration:
                finished = True
                level_finished = True
                break

            moves += 1

            # After 20s on this room — spawn bouncing yellow Otto ball
            if (not RobotBob.alive
                    and (time.time() - room_start) >= OTTO_APPEAR_SECONDS):
                spawn_otto()

            if Human.alive and moves % Human.speed == 0:
                move_human()
                # Any door exit allowed — chicken if robots still alive
                if ExitingRoom:
                    robots_left = count_robots_alive()
                    if robots_left > 0:
                        ChickenUntil = time.time() + CHICKEN_DISPLAY_SEC
                        print("[DotZerk] CHICKEN exit dir={} room={},{} robots={}".format(
                            Human.direction, MazeWorld.CurrentRoomH,
                            MazeWorld.CurrentRoomV, robots_left))
                    else:
                        print("[DotZerk] Escape via door dir={} room={},{}".format(
                            Human.direction, MazeWorld.CurrentRoomH,
                            MazeWorld.CurrentRoomV))
                    exit_room(Human.direction)
                    level_finished = True
                    break

            for bot in Robots:
                if bot.alive and moves % bot.speed == 0:
                    move_robot(bot)
            if RobotBob.alive and moves % OTTO_TICK == 0:
                move_otto()

            for m in HumanMissiles:
                if m.alive and not m.exploding and moves % m.speed == 0:
                    move_missile(m, owner_is_human=True)
            for m in RobotMissiles:
                if m.alive and not m.exploding and moves % m.speed == 0:
                    move_missile(m, owner_is_human=False)

            tick_explosions()

            if moves % HUD_EVERY == 0:
                draw_hud()
                # re-assert doors + human/robots/Otto/lives on top
                for d in (MazeWorld.Door1, MazeWorld.Door2, MazeWorld.Door3, MazeWorld.Door4):
                    d.Display()
                Human.Display()
                for bot in Robots:
                    if bot.alive:
                        bot.Display()
                if RobotBob.alive:
                    set_pf(RobotBob.h, RobotBob.v, OTTO_RGB[0], OTTO_RGB[1], OTTO_RGB[2])
                draw_lives_dots()
                # Re-stamp live particles so HUD redraw doesn't wipe them
                for p in ActiveParticles:
                    if in_room(p.px, p.py) and p.life > 0:
                        fade = max(0.25, min(1.0, p.life / 12.0))
                        set_pf(p.px, p.py,
                               int(p.rgb[0] * fade),
                               int(p.rgb[1] * fade),
                               int(p.rgb[2] * fade))

            # Marquee last each frame (smooth, after game/HUD work)
            tick_taunt_scroll()

            if not Human.alive:
                # Spend one life; game continues until the last life is gone
                if Human.lives > 0:
                    Human.lives -= 1
                lives_left = Human.lives
                death_h, death_v = Human.h, Human.v
                cause = "Otto" if RobotBob.alive and _otto_touching_human() else "hit"
                print("[DotZerk] Human died ({}) lives left={}".format(cause, lives_left))
                deactivate_missiles()
                draw_lives_dots()
                if lives_left <= 0:
                    # Last life — prolonged blast + scrolling gloat, then game over
                    show_final_human_death(death_h, death_v)
                    finished = True
                    level_finished = True
                else:
                    # Linger with explosion + scrolling robot insult, then new room
                    show_human_death_interlude(death_h, death_v, final=False)
                    Human.alive = 1
                    Human.exploding = 0
                    RobotBob.alive = 0
                    pick_random_room_and_spawn()
                    room_start = time.time()
                    reset_playfield()
                    start_room_taunt()
                    draw_hud()
                    print("[DotZerk] Room {},{}  lives={}  score={}".format(
                        MazeWorld.CurrentRoomH, MazeWorld.CurrentRoomV,
                        Human.lives, DotZerkScore))
                    # stay in this room loop with the new random room

            if MAIN_SLEEP > 0:
                time.sleep(MAIN_SLEEP)

    # Persist high score + games played (ClockConfig.ini)
    DotZerkGamesPlayed += 1
    if DotZerkScore > DotZerkHighScore:
        print("[DotZerk] NEW HIGH SCORE {} (was {})".format(
            DotZerkScore, DotZerkHighScore))
        DotZerkHighScore = DotZerkScore
    SaveDotZerkScores()

    # Game over — text drops from top to bottom
    _show_game_over_scroll(DotZerkScore)
    print("[DotZerk] Done score={} high={} games={} lives={}".format(
        DotZerkScore, DotZerkHighScore, DotZerkGamesPlayed, Human.lives))


def _scroll_banner_down(text, rgb, sleep=0.04, hold=0.7, stop_center=True):
    """
    Scroll a banner string from above the panel downward.
    If stop_center, settle mid-screen; else scroll fully off the bottom.
    """
    try:
        banner = LED.CreateBannerSprite(str(text).upper())
    except Exception as e:
        print("[DotZerk] game over banner create: {}".format(e))
        return
    banner.r, banner.g, banner.b = rgb
    h = max(0, (LED.HatWidth - banner.width) // 2)
    start_v = -banner.height
    if stop_center:
        end_v = max(0, (LED.HatHeight - banner.height) // 2)
    else:
        end_v = LED.HatHeight
    moves = max(1, end_v - start_v)

    # Prefer Sprite.Scroll (supports direction="down")
    try:
        LED.ClearBigLED()
        LED.ClearBuffers()
        banner.Scroll(start_h=h, start_v=start_v, direction="down",
                      moves=moves, sleep=sleep)
        time.sleep(hold)
        return
    except Exception as e:
        print("[DotZerk] Scroll down fallback: {}".format(e))

    # Manual step fallback
    try:
        for v in range(start_v, end_v + 1):
            LED.ClearBigLED()
            try:
                banner.Display(h, v)
            except Exception:
                # paint grid directly
                for count in range(banner.width * banner.height):
                    if banner.grid[count] != 1:
                        continue
                    y, x = divmod(count, banner.width)
                    px, py = h + x, v + y
                    if 0 <= px < LED.HatWidth and 0 <= py < LED.HatHeight:
                        LED.setpixel(px, py, banner.r, banner.g, banner.b)
            time.sleep(sleep)
        time.sleep(hold)
    except Exception as e2:
        print("[DotZerk] manual scroll down failed: {}".format(e2))


def _paint_game_over_to_screen(rgb):
    """Freeze centered GAME OVER into ScreenArray for MoveAnimated* background."""
    try:
        LED.ClearBigLED()
        LED.ClearBuffers()
        banner = LED.CreateBannerSprite("GAME OVER")
        banner.r, banner.g, banner.b = rgb
        h = max(0, (LED.HatWidth - banner.width) // 2)
        v = max(0, (LED.HatHeight - banner.height) // 2)
        for count in range(banner.width * banner.height):
            if count >= len(banner.grid) or banner.grid[count] != 1:
                continue
            y, x = divmod(count, banner.width)
            px, py = h + x, v + y
            if 0 <= px < LED.HatWidth and 0 <= py < LED.HatHeight:
                LED.setpixel(px, py, banner.r, banner.g, banner.b)
    except Exception as e:
        print("[DotZerk] paint GAME OVER failed: {}".format(e))


def _show_game_over_scroll(score):
    """
    GAME OVER drops from top, then two animated sprites walk under it
    (same pool as intro), then a static 3s hold.
    """
    print("[DotZerk] GAME OVER scroll  score={}".format(score))
    try:
        LED.ClearBigLED()
        LED.ClearBuffers()
    except Exception:
        pass
    red = getattr(LED, "HighRed", (220, 0, 0))
    if isinstance(red, tuple) and len(red) >= 3:
        rgb_over = (red[0], red[1], red[2])
    else:
        rgb_over = (220, 0, 0)

    _scroll_banner_down("GAME OVER", rgb_over, sleep=0.035, hold=0.5, stop_center=True)
    # Freeze text so MoveAnimated* can float over it
    _paint_game_over_to_screen(rgb_over)
    _sprite_parade(StopEvent=None, label="GameOver")
    # Re-stamp GAME OVER in case walks wiped it
    _paint_game_over_to_screen(rgb_over)
    time.sleep(3.0)


def LaunchDotZerk(Duration=DURATION_DEFAULT, ShowIntro=True, StopEvent=None):
    try:
        Duration = int(Duration)
    except (TypeError, ValueError):
        Duration = DURATION_DEFAULT
    if Duration <= 0:
        Duration = DURATION_DEFAULT

    LoadDotZerkScores()

    if ShowIntro and not (StopEvent is not None and StopEvent.is_set()):
        try:
            LED.LoadConfigData()
        except Exception:
            pass
        LED.ClearBigLED()
        LED.ClearBuffers()
        PlayDotZerkTitleIntro(StopEvent=StopEvent)

    if StopEvent is not None and StopEvent.is_set():
        return

    PlayDotZerk(Duration=Duration, StopEvent=StopEvent)
    print("[DotZerk] LaunchDotZerk complete")


if __name__ == "__main__":
    while True:
        LaunchDotZerk(Duration=100000, ShowIntro=True, StopEvent=None)
