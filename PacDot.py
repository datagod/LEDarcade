#!/usr/bin/env python
#------------------------------------------------------------------------------
#  PACDOT — half-screen (32x32) on a 64x32 LED matrix
#
#  Left half  : playfield (Pac, ghosts, dots, pills)
#  Right half : HUD (score / level / high score)
#
#  Ported from ArcadeRetroClockHD PlayPacDot AI loop, adapted for LEDarcade
#  and the 64x32 panel layout.
#------------------------------------------------------------------------------

import LEDarcade as LED
import copy
import math
import random
import time
from datetime import datetime
from random import randint

LED.Initialize()

#------------------------------------------------------------------------------
# Layout
#------------------------------------------------------------------------------
PF_H0 = 0
PF_V0 = 0
PF_W  = 32
PF_H  = 32

HUD_H0 = 32  # right half starts here

#------------------------------------------------------------------------------
# Tunables
#------------------------------------------------------------------------------
NUM_DOTS_DEFAULT   = 220
POWER_PILLS        = 5
PAC_SPEED          = 5
START_GHOST_SPEED1 = 5
START_GHOST_SPEED2 = 6
START_GHOST_SPEED3 = 7
START_GHOST_SPEED4 = 10
BLUE_GHOST_SPEED   = 15
BLUE_GHOST_MOVES   = 500
MAX_MOVES          = 10000
PAC_STUCK_MAX      = 300
MAIN_SLEEP         = 0.008
HUD_REFRESH_EVERY  = 8

DOT_POINTS         = 1
PILL_POINTS        = 10
BLUE_GHOST_POINTS  = 5

# Title intro (Skyfall-style letters, horizontal slide from sides)
TITLE_WORD             = "PACDOT"
TITLE_LETTER_ZOOM      = 2
TITLE_LETTER_GAP       = 1
TITLE_LETTER_RGB       = (220, 200, 40)    # pac yellow
TITLE_LETTER_SHADOW_RGB = (40, 35, 5)
TITLE_LETTER_STAGGER   = 0.18
TITLE_SLIDE_SPEED      = 1.35             # pixels per frame-unit
TITLE_HOLD_SECONDS     = 1.6
TITLE_INTRO_MAX_SECONDS = 12.0

#------------------------------------------------------------------------------
# Runtime state
#------------------------------------------------------------------------------
PowerPillActive = 0
PowerPillMoves  = 0
PacDotScore     = 0
PacDotHighScore = 0
PacDotGamesPlayed = 0
LevelCount      = 1

Ghost1Alive = Ghost2Alive = Ghost3Alive = Ghost4Alive = 1
Ghost1H = Ghost1V = 0
Ghost2H = Ghost2V = 0
Ghost3H = Ghost3V = 0
Ghost4H = Ghost4V = 0

# Ghost train: free ghosts that touch Pac latch on and follow like a snake.
# GhostTrain is ordered list of ghost ids (1–4); first = immediately behind Pac.
Ghost1Attached = Ghost2Attached = Ghost3Attached = Ghost4Attached = 0
GhostTrain = []
PacDead = False
PacLives = 3
PAC_START_LIVES = 3

Pacmoves = 0


#------------------------------------------------------------------------------
# Geometry helpers
#------------------------------------------------------------------------------
def pf_in_bounds(h, v):
    return (PF_H0 <= h < PF_H0 + PF_W) and (PF_V0 <= v < PF_V0 + PF_H)


def CalculateMovement(h, v, direction):
    # 1N 2E 3S 4W
    if direction == 1:
        v -= 1
    elif direction == 2:
        h += 1
    elif direction == 3:
        v += 1
    elif direction == 4:
        h -= 1
    return h, v, direction


def TurnTowardsDot4Way(source_h, source_v, source_direction, target_h, target_v):
    x = source_h - target_h
    y = source_v - target_v
    if abs(y) >= abs(x):
        return 3 if y <= 0 else 1
    return 2 if x <= 0 else 4


def TurnAwayFromDot4Way(source_h, source_v, source_direction, target_h, target_v):
    x = source_h - target_h
    y = source_v - target_v
    if abs(y) >= abs(x):
        return 1 if y <= 0 else 3
    return 4 if x <= 0 else 2


#------------------------------------------------------------------------------
# Scan / draw
#------------------------------------------------------------------------------
def ScanDot(h, v):
    """Classify a cell by color + DotMatrix. Outside playfield = boundary."""
    if not pf_in_bounds(h, v):
        return "boundary"

    r, g, b = LED.getpixel(h, v)
    try:
        dm = LED.DotMatrix[h][v]
    except Exception:
        dm = 0

    if dm == 2:
        item = "pill"
    elif r == LED.DotR and g == LED.DotG and b == LED.DotB:
        item = "dot"
    elif r == LED.PillR and g == LED.PillG and b == LED.PillB:
        item = "pill"
    elif (r == LED.Ghost1R and g == LED.Ghost1G and b == LED.Ghost1B) or \
         (r == LED.Ghost2R and g == LED.Ghost2G and b == LED.Ghost2B) or \
         (r == LED.Ghost3R and g == LED.Ghost3G and b == LED.Ghost3B) or \
         (r == LED.Ghost4R and g == LED.Ghost4G and b == LED.Ghost4B):
        item = "ghost"
    elif r == LED.PacR and g == LED.PacG and b == LED.PacB:
        item = "pacdot"
    elif r == LED.BlueGhostR and g == LED.BlueGhostG and b == LED.BlueGhostB:
        item = "blueghost"
    elif r == LED.WallR and g == LED.WallG and b == LED.WallB:
        item = "wall"
    else:
        item = "empty"

    if dm == 1:
        item = "dot"
    elif dm == 2:
        item = "pill"
    return item


def ScanBox(h, v, direction):
    scan_hit = "NULL"

    # Front
    if scan_hit == "NULL":
        sh, sv, sd = CalculateMovement(h, v, direction)
        item = ScanDot(sh, sv)
        if item == "dot":
            scan_hit = "frontdot"
        elif item == "ghost":
            scan_hit = "frontghost"
        elif item == "blueghost":
            scan_hit = "frontblueghost"
        elif item == "pill":
            scan_hit = "frontpill"
        elif item == "wall":
            scan_hit = "frontwall"

    # Left
    if scan_hit == "NULL":
        sd = LED.TurnLeft(direction)
        sh, sv, sd = CalculateMovement(h, v, sd)
        item = ScanDot(sh, sv)
        if item == "dot":
            scan_hit = "leftdot"
        elif item == "ghost":
            scan_hit = "leftghost"
        elif item == "blueghost":
            scan_hit = "leftblueghost"
        elif item == "pill":
            scan_hit = "leftpill"
        elif item == "wall":
            scan_hit = "leftwall"

    # Right
    if scan_hit == "NULL":
        sd = LED.TurnRight(direction)
        sh, sv, sd = CalculateMovement(h, v, sd)
        item = ScanDot(sh, sv)
        if item == "dot":
            scan_hit = "rightdot"
        elif item == "ghost":
            scan_hit = "rightghost"
        elif item == "blueghost":
            scan_hit = "rightblueghost"
        elif item == "pill":
            scan_hit = "rightpill"
        elif item == "wall":
            scan_hit = "rightwall"

    if scan_hit == "NULL":
        scan_hit = "empty"
    return scan_hit


def FollowScanner(h, v, direction):
    scan_hit = ScanBox(h, v, direction)

    if scan_hit == "leftblueghost":
        return LED.TurnLeft(direction)
    if scan_hit == "rightblueghost":
        return LED.TurnRight(direction)
    if scan_hit == "frontblueghost":
        return direction
    if scan_hit == "leftpill":
        return LED.TurnLeft(direction)
    if scan_hit == "frontpill":
        return direction
    if scan_hit == "rightpill":
        return LED.TurnRight(direction)
    if scan_hit == "leftdot":
        return LED.TurnLeft(direction)
    if scan_hit == "rightdot":
        return LED.TurnRight(direction)
    if scan_hit == "frontdot":
        return direction
    if scan_hit == "frontghost":
        return LED.ReverseDirection(direction)
    if scan_hit == "frontwall":
        sd = LED.TurnRight(direction)
        sh, sv, sd = CalculateMovement(h, v, sd)
        item = ScanDot(sh, sv)
        if item in ("empty", "pill", "blueghost", "dot"):
            return sd
        sd = LED.TurnLeft(direction)
        sh, sv, sd = CalculateMovement(h, v, sd)
        item = ScanDot(sh, sv)
        if item in ("empty", "pill", "blueghost", "dot"):
            return sd
        return LED.ReverseDirection(direction)
    return direction


def DrawGhost(h, v, r, g, b):
    global PowerPillActive
    if PowerPillActive == 1:
        LED.setpixel(h, v, LED.BlueGhostR, LED.BlueGhostG, LED.BlueGhostB)
    else:
        LED.setpixel(h, v, r, g, b)
    return h, v


def DrawPacDot(h, v, r, g, b):
    LED.setpixel(h, v, r, g, b)
    return h, v


def is_border_cell(h, v):
    """True if (h,v) is on the playfield blue wall ring."""
    if not pf_in_bounds(h, v):
        return False
    return (
        h == PF_H0 or h == PF_H0 + PF_W - 1 or
        v == PF_V0 or v == PF_V0 + PF_H - 1
    )


def DrawPlayfieldBorder():
    """Full solid blue wall around the playfield, then lives on the bottom edge."""
    wr, wg, wb = LED.WallR, LED.WallG, LED.WallB
    # Top + bottom rows (full width, including corners)
    for h in range(PF_H0, PF_H0 + PF_W):
        LED.setpixel(h, PF_V0, wr, wg, wb)
        LED.setpixel(h, PF_V0 + PF_H - 1, wr, wg, wb)
    # Left + right columns (corners written twice — fine)
    for v in range(PF_V0, PF_V0 + PF_H):
        LED.setpixel(PF_H0, v, wr, wg, wb)
        LED.setpixel(PF_H0 + PF_W - 1, v, wr, wg, wb)
    # Lives sit on the bottom wall (yellow pac dots)
    DrawLivesIndicator()


def ClearPlayfield():
    for h in range(PF_H0, PF_H0 + PF_W):
        for v in range(PF_V0, PF_V0 + PF_H):
            LED.setpixel(h, v, 0, 0, 0)


def ClearHUD():
    for h in range(HUD_H0, LED.HatWidth):
        for v in range(0, LED.HatHeight):
            LED.setpixel(h, v, 0, 0, 0)


def ResetDotMatrix():
    LED.DotMatrix = [[0 for _ in range(LED.HatHeight)] for _ in range(LED.HatWidth)]


def DrawDots(num_dots):
    if num_dots < 5:
        num_dots = 5
    max_cells = (PF_W - 2) * (PF_H - 2)
    if num_dots > max_cells - 10:
        num_dots = max_cells - 10

    placed = 0
    tries = 0
    while placed < num_dots and tries < 20000:
        tries += 1
        h = randint(PF_H0 + 1, PF_H0 + PF_W - 2)
        v = randint(PF_V0 + 1, PF_V0 + PF_H - 2)
        if LED.DotMatrix[h][v] == 1:
            continue
        r, g, b = LED.getpixel(h, v)
        if r == 0 and g == 0 and b == 0:
            LED.DotMatrix[h][v] = 1
            LED.setpixel(h, v, LED.DotR, LED.DotG, LED.DotB)
            placed += 1
    return placed


def DrawPowerPills(count):
    placed = 0
    tries = 0
    while placed < count and tries < 5000:
        tries += 1
        h = randint(PF_H0 + 1, PF_H0 + PF_W - 2)
        v = randint(PF_V0 + 1, PF_V0 + PF_H - 2)
        if LED.DotMatrix[h][v] == 1:
            LED.DotMatrix[h][v] = 2
            LED.setpixel(h, v, LED.PillR, LED.PillG, LED.PillB)
            placed += 1


def DrawDotMatrix():
    n = 0
    for h in range(PF_H0, PF_H0 + PF_W):
        for v in range(PF_V0, PF_V0 + PF_H):
            if is_border_cell(h, v):
                continue
            if LED.DotMatrix[h][v] == 1:
                n += 1
                LED.setpixel(h, v, LED.DotR, LED.DotG, LED.DotB)
            elif LED.DotMatrix[h][v] == 2:
                LED.setpixel(h, v, LED.PillR, LED.PillG, LED.PillB)
    return n


def CountDotsRemaining():
    n = 0
    for h in range(PF_H0, PF_H0 + PF_W):
        for v in range(PF_V0, PF_V0 + PF_H):
            if LED.DotMatrix[h][v] == 1:
                n += 1
    return n


def FindClosestDot(pac_h, pac_v):
    global PowerPillActive
    closest_x = PF_H0 + PF_W // 2
    closest_y = PF_V0 + PF_H // 2
    min_dist = 9999
    for x in range(PF_H0, PF_H0 + PF_W):
        for y in range(PF_V0, PF_V0 + PF_H):
            dm = LED.DotMatrix[x][y]
            if dm == 1:
                dist = LED.GetDistanceBetweenDots(pac_h, pac_v, x, y)
                if dist <= min_dist:
                    min_dist = dist
                    closest_x, closest_y = x, y
            elif dm == 2 and PowerPillActive == 0:
                dist = LED.GetDistanceBetweenDots(pac_h, pac_v, x, y)
                if dist < min_dist:
                    min_dist = dist
                    closest_x, closest_y = x, y
    return closest_x, closest_y


#------------------------------------------------------------------------------
# Ghost train + movement
#------------------------------------------------------------------------------
def _ghost_rgb(gid):
    if gid == 1:
        return LED.Ghost1R, LED.Ghost1G, LED.Ghost1B
    if gid == 2:
        return LED.Ghost2R, LED.Ghost2G, LED.Ghost2B
    if gid == 3:
        return LED.Ghost3R, LED.Ghost3G, LED.Ghost3B
    return LED.Ghost4R, LED.Ghost4G, LED.Ghost4B


def _get_ghost_pos(gid):
    if gid == 1:
        return Ghost1H, Ghost1V
    if gid == 2:
        return Ghost2H, Ghost2V
    if gid == 3:
        return Ghost3H, Ghost3V
    return Ghost4H, Ghost4V


def _set_ghost_pos(gid, h, v):
    global Ghost1H, Ghost1V, Ghost2H, Ghost2V, Ghost3H, Ghost3V, Ghost4H, Ghost4V
    if gid == 1:
        Ghost1H, Ghost1V = h, v
    elif gid == 2:
        Ghost2H, Ghost2V = h, v
    elif gid == 3:
        Ghost3H, Ghost3V = h, v
    else:
        Ghost4H, Ghost4V = h, v


def _is_attached(gid):
    if gid == 1:
        return Ghost1Attached
    if gid == 2:
        return Ghost2Attached
    if gid == 3:
        return Ghost3Attached
    return Ghost4Attached


def _set_attached(gid, value):
    global Ghost1Attached, Ghost2Attached, Ghost3Attached, Ghost4Attached
    if gid == 1:
        Ghost1Attached = value
    elif gid == 2:
        Ghost2Attached = value
    elif gid == 3:
        Ghost3Attached = value
    else:
        Ghost4Attached = value


def _is_alive(gid):
    if gid == 1:
        return Ghost1Alive
    if gid == 2:
        return Ghost2Alive
    if gid == 3:
        return Ghost3Alive
    return Ghost4Alive


def _set_alive(gid, value):
    global Ghost1Alive, Ghost2Alive, Ghost3Alive, Ghost4Alive
    if gid == 1:
        Ghost1Alive = value
    elif gid == 2:
        Ghost2Alive = value
    elif gid == 3:
        Ghost3Alive = value
    else:
        Ghost4Alive = value


def IdentifyGhost(h, v):
    """Return ghost id (1–4) at cell, or 0."""
    if Ghost1Alive and Ghost1H == h and Ghost1V == v:
        return 1
    if Ghost2Alive and Ghost2H == h and Ghost2V == v:
        return 2
    if Ghost3Alive and Ghost3H == h and Ghost3V == v:
        return 3
    if Ghost4Alive and Ghost4H == h and Ghost4V == v:
        return 4
    return 0


def RestoreCell(h, v):
    """Redraw a playfield cell after a train car / explosion leaves it."""
    if not pf_in_bounds(h, v):
        return
    if is_border_cell(h, v):
        LED.setpixel(h, v, LED.WallR, LED.WallG, LED.WallB)
        return
    if LED.DotMatrix[h][v] == 1:
        LED.setpixel(h, v, LED.DotR, LED.DotG, LED.DotB)
    elif LED.DotMatrix[h][v] == 2:
        LED.setpixel(h, v, LED.PillR, LED.PillG, LED.PillB)
    else:
        LED.setpixel(h, v, 0, 0, 0)


def AttachGhost(gid):
    """Latch a free ghost onto the end of Pac's train."""
    global GhostTrain
    if gid < 1 or gid > 4:
        return False
    if not _is_alive(gid) or _is_attached(gid):
        return False
    if gid in GhostTrain:
        return False
    _set_attached(gid, 1)
    GhostTrain.append(gid)
    print("[PacDot] Ghost {} attached  train={}".format(gid, GhostTrain))
    return True


def DetachGhost(gid):
    global GhostTrain
    _set_attached(gid, 0)
    if gid in GhostTrain:
        GhostTrain.remove(gid)


def ReleaseAllAttachedGhosts():
    """Power pill frees the train — ghosts become blue free roamers."""
    global GhostTrain
    for gid in list(GhostTrain):
        _set_attached(gid, 0)
        gh, gv = _get_ghost_pos(gid)
        DrawGhost(gh, gv, *_ghost_rgb(gid))
    GhostTrain = []


def ResetGhostTrain():
    global GhostTrain
    global Ghost1Attached, Ghost2Attached, Ghost3Attached, Ghost4Attached
    GhostTrain = []
    Ghost1Attached = Ghost2Attached = Ghost3Attached = Ghost4Attached = 0


def KillGhost(h, v):
    """Kill ghost at cell (eaten while blue). Detach if it was in the train."""
    gid = IdentifyGhost(h, v)
    if gid == 0:
        # Fall back to position match without alive check edge cases
        global Ghost1Alive, Ghost2Alive, Ghost3Alive, Ghost4Alive
        global Ghost1H, Ghost1V, Ghost2H, Ghost2V, Ghost3H, Ghost3V, Ghost4H, Ghost4V
        if h == Ghost1H and v == Ghost1V:
            gid = 1
        elif h == Ghost2H and v == Ghost2V:
            gid = 2
        elif h == Ghost3H and v == Ghost3V:
            gid = 3
        elif h == Ghost4H and v == Ghost4V:
            gid = 4
    if gid:
        DetachGhost(gid)
        _set_alive(gid, 0)


def UpdateGhostTrain(old_pac_h, old_pac_v):
    """
    Snake/train follow: first attached ghost takes Pac's previous cell,
    each next car takes the previous car's old cell.
    """
    global GhostTrain
    if not GhostTrain:
        return

    # Snapshot current train car positions (before move)
    old_positions = [(old_pac_h, old_pac_v)]
    for gid in GhostTrain:
        old_positions.append(_get_ghost_pos(gid))

    # Clear previous car pixels (restore dots)
    for gid in GhostTrain:
        gh, gv = _get_ghost_pos(gid)
        RestoreCell(gh, gv)

    # Assign new positions along the chain
    for i, gid in enumerate(GhostTrain):
        nh, nv = old_positions[i]
        _set_ghost_pos(gid, nh, nv)
        r, g, b = _ghost_rgb(gid)
        DrawGhost(nh, nv, r, g, b)


def DrawGhostTrain():
    """Redraw all attached ghosts (after power-pill recolor etc.)."""
    for gid in GhostTrain:
        if not _is_alive(gid):
            continue
        gh, gv = _get_ghost_pos(gid)
        DrawGhost(gh, gv, *_ghost_rgb(gid))


def AllGhostsAttached():
    """True when all four living ghosts are latched (or all four slots filled)."""
    if len(GhostTrain) >= 4:
        return True
    # Count living free ghosts — if none free and at least one attached and all living are attached
    living = [g for g in (1, 2, 3, 4) if _is_alive(g)]
    if not living:
        return False
    return all(_is_attached(g) for g in living) and len(living) >= 4


def ShowBlueGhostExplosion(h, v):
    """
    Small explosion when Pac eats a blue ghost.
    Uses LED.SmallExplosion (3x3 ColorAnimatedSprite) centered on the cell.
    """
    eh = h - 1  # center 3x3 on ghost pixel
    ev = v - 1
    try:
        boom = copy.deepcopy(LED.SmallExplosion)
        boom.currentframe = 1
        boom.h = eh
        boom.v = ev
        boom.Animate(eh, ev, "forward", 0.035)
    except Exception as e:
        print(f"[PacDot] SmallExplosion fallback: {e}")
        for br in (220, 140, 60, 0):
            LED.setpixel(h, v, br, br, min(255, br + 40))
            time.sleep(0.03)

    for dy in range(-1, 2):
        for dx in range(-1, 2):
            x, y = h + dx, v + dy
            if not pf_in_bounds(x, y):
                continue
            RestoreCell(x, y)
    # Explosions near the edge punch wall pixels — reseal the ring
    DrawPlayfieldBorder()


def ShowPacMegaExplosion(h, v):
    """
    Bigger death explosion when the full ghost train attaches.
    Uses PlayerShipExplosion (5x5) then SmallExplosion for extra spark.
    """
    print("[PacDot] MEGA EXPLOSION at {},{}".format(h, v))
    try:
        big = copy.deepcopy(LED.PlayerShipExplosion)
        big.currentframe = 1
        big.h = h - 2
        big.v = v - 2
        big.Animate(h - 2, v - 2, "forward", 0.04)
    except Exception as e:
        print(f"[PacDot] PlayerShipExplosion failed: {e}")
        try:
            big2 = copy.deepcopy(LED.BigShipExplosion)
            big2.currentframe = 1
            big2.Animate(h - 4, v - 2, "forward", 0.04)
        except Exception as e2:
            print(f"[PacDot] BigShipExplosion failed: {e2}")

    # Secondary spark
    try:
        spark = copy.deepcopy(LED.SmallExplosion)
        spark.currentframe = 1
        spark.Animate(h - 1, v - 1, "forward", 0.03)
    except Exception:
        pass

    # Wipe local area clean
    for dy in range(-3, 4):
        for dx in range(-3, 4):
            x, y = h + dx, v + dy
            if pf_in_bounds(x, y):
                RestoreCell(x, y)
    DrawPlayfieldBorder()


def MoveGhost(h, v, direction, r, g, b, ghost_id):
    """Move a free (non-attached) ghost. Touching Pac attaches to the train."""
    global PowerPillActive
    if _is_attached(ghost_id):
        return h, v, direction

    newh, newv, direction = CalculateMovement(h, v, direction)
    item = ScanDot(newh, newv)

    if item in ("wall", "pill", "ghost", "boundary"):
        direction = randint(1, 4)
        return h, v, direction

    if item in ("empty", "dot"):
        if PowerPillActive == 1:
            LED.setpixel(newh, newv, LED.BlueGhostR, LED.BlueGhostG, LED.BlueGhostB)
        else:
            LED.setpixel(newh, newv, r, g, b)
        if LED.DotMatrix[h][v] == 1:
            LED.setpixel(h, v, LED.DotR, LED.DotG, LED.DotB)
        elif LED.DotMatrix[h][v] == 2:
            LED.setpixel(h, v, LED.PillR, LED.PillG, LED.PillB)
        else:
            LED.setpixel(h, v, 0, 0, 0)
        return newh, newv, direction

    if item == "pacdot":
        if PowerPillActive == 0:
            # Latch onto Pac's train; stay put until train update places us
            AttachGhost(ghost_id)
        return h, v, direction

    return h, v, direction


def MovePacDot(h, v, direction, r, g, b, dots_eaten):
    global Pacmoves, PowerPillActive, PacDotScore
    global Ghost1Alive, Ghost2Alive, Ghost3Alive, Ghost4Alive
    global Ghost1H, Ghost1V, Ghost2H, Ghost2V, Ghost3H, Ghost3V, Ghost4H, Ghost4V

    Pacmoves += 1
    newh, newv, direction = CalculateMovement(h, v, direction)
    item = ScanDot(newh, newv)

    if item == "dot":
        dots_eaten += 1
        Pacmoves = 0
        PacDotScore += DOT_POINTS
        LED.setpixel(newh, newv, r, g, b)
        LED.setpixel(h, v, 0, 0, 0)
        LED.DotMatrix[newh][newv] = 0

    elif item == "pill":
        Pacmoves = 0
        PacDotScore += PILL_POINTS
        LED.setpixel(newh, newv, r, g, b)
        LED.setpixel(h, v, 0, 0, 0)
        LED.DotMatrix[newh][newv] = 0
        PowerPillActive = 1
        # Power pill shakes free any attached ghosts
        ReleaseAllAttachedGhosts()
        if Ghost1Alive == 1:
            DrawGhost(Ghost1H, Ghost1V, LED.Ghost1R, LED.Ghost1G, LED.Ghost1B)
        if Ghost2Alive == 1:
            DrawGhost(Ghost2H, Ghost2V, LED.Ghost2R, LED.Ghost2G, LED.Ghost2B)
        if Ghost3Alive == 1:
            DrawGhost(Ghost3H, Ghost3V, LED.Ghost3R, LED.Ghost3G, LED.Ghost3B)
        if Ghost4Alive == 1:
            DrawGhost(Ghost4H, Ghost4V, LED.Ghost4R, LED.Ghost4G, LED.Ghost4B)

    elif item in ("wall", "boundary"):
        Pacmoves = 0
        direction = randint(1, 4)
        newh, newv = h, v

    elif item == "blueghost":
        Pacmoves = 0
        PacDotScore += BLUE_GHOST_POINTS
        LED.setpixel(h, v, 0, 0, 0)
        LED.DotMatrix[newh][newv] = 0
        KillGhost(newh, newv)
        ShowBlueGhostExplosion(newh, newv)
        LED.setpixel(newh, newv, r, g, b)

    elif item == "ghost":
        gid = IdentifyGhost(newh, newv)
        if PowerPillActive == 1:
            Pacmoves = 0
            PacDotScore += BLUE_GHOST_POINTS
            LED.setpixel(h, v, 0, 0, 0)
            KillGhost(newh, newv)
            ShowBlueGhostExplosion(newh, newv)
            LED.setpixel(newh, newv, r, g, b)
        else:
            # Ghost latches on; Pac keeps moving (train follows on next tick)
            if gid:
                AttachGhost(gid)
            # Pac can still move onto empty-looking logic: stay put one step
            # so we don't stack pixels; turn slightly scared
            direction = LED.TurnLeftOrRight(direction)
            newh, newv = h, v

    elif item == "empty":
        LED.setpixel(newh, newv, r, g, b)
        LED.setpixel(h, v, 0, 0, 0)

    return newh, newv, direction, dots_eaten


#------------------------------------------------------------------------------
# Title intro — letters slide in from left/right (Skyfall-inspired)
#------------------------------------------------------------------------------
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


class SlideLetter:
    """Banner letter that slides horizontally from a screen edge to rest_x."""

    def __init__(self, char, pixels, shadow_pixels, width, height,
                 rest_x, rest_y, start_x, drop_delay, from_left):
        self.char = char
        self.pixels = pixels
        self.shadow_pixels = shadow_pixels
        self.width = width
        self.height = height
        self.rest_x = float(rest_x)
        self.rest_y = float(rest_y)
        self.x = float(start_x)
        self.y = float(rest_y)
        self.drop_delay = drop_delay
        self.from_left = from_left
        self.started = False
        self.settled = False

    def update(self, step, elapsed, speed):
        if self.settled:
            self.x = self.rest_x
            return
        if elapsed < self.drop_delay:
            return
        self.started = True
        # Ease-out approach toward rest_x
        dx = self.rest_x - self.x
        if abs(dx) < 0.5:
            self.x = self.rest_x
            self.settled = True
            return
        # Move a fraction of remaining distance + min step so we always progress
        move = max(0.4, abs(dx) * 0.22) * speed * step
        if move > abs(dx):
            move = abs(dx)
        self.x += move if dx > 0 else -move
        if abs(self.rest_x - self.x) < 0.5:
            self.x = self.rest_x
            self.settled = True

    def force_settle(self):
        self.x = self.rest_x
        self.y = self.rest_y
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
    for index, (char, pixels, shadow_pixels, letter_w, letter_h) in enumerate(specs):
        from_left = (index % 2 == 0)
        if from_left:
            spawn_x = -letter_w - 4
        else:
            spawn_x = panel_w + 4
        y_off = letter_height - letter_h
        letters.append(SlideLetter(
            char, pixels, shadow_pixels, letter_w, letter_h,
            rest_x=x_cursor,
            rest_y=rest_y + y_off,
            start_x=spawn_x,
            drop_delay=index * TITLE_LETTER_STAGGER,
            from_left=from_left,
        ))
        x_cursor += letter_w + TITLE_LETTER_GAP
    return letters


def PlayPacDotTitleIntro(StopEvent=None):
    """Slide PACDOT letters in from left/right until centered, then hold."""
    panel_w = LED.HatWidth
    panel_h = LED.HatHeight
    letters = _build_title_letters(panel_w, panel_h)
    if not letters:
        return

    if StopEvent is not None and StopEvent.is_set():
        print("[PacDot] Title intro skipped (StopEvent)")
        return

    print("[PacDot] Title intro — sliding letters from sides")
    try:
        canvas = LED.TheMatrix.CreateFrameCanvas()
    except Exception:
        canvas = None

    start = time.time()
    last_frame = start
    hold_start = None

    try:
        while True:
            if StopEvent is not None and StopEvent.is_set():
                print("[PacDot] Title intro — StopEvent")
                break

            now = time.time()
            elapsed = now - start
            if elapsed >= TITLE_INTRO_MAX_SECONDS:
                for letter in letters:
                    letter.force_settle()
                break

            frame_dt = max(0.001, now - last_frame)
            last_frame = now
            # Normalize to ~30fps step units (similar feel to Skyfall)
            step = min(3.0, frame_dt * 30.0)

            for letter in letters:
                letter.update(step, elapsed, TITLE_SLIDE_SPEED)

            if hold_start is None and all(letter.settled for letter in letters):
                hold_start = now

            if hold_start is not None and (now - hold_start) >= TITLE_HOLD_SECONDS:
                break

            if canvas is not None:
                canvas.Fill(0, 0, 0)
                for letter in letters:
                    if letter.started or letter.settled:
                        letter.draw(canvas, panel_w, panel_h)
                canvas = LED.TheMatrix.SwapOnVSync(canvas)
            else:
                LED.ClearBigLED()
                # Fallback: draw via setpixel
                for letter in letters:
                    if not (letter.started or letter.settled):
                        continue
                    sx = int(round(letter.x))
                    sy = int(round(letter.y))
                    for dx, dy, rgb in letter.pixels:
                        LED.setpixel(sx + dx, sy + dy, *rgb)
                time.sleep(0.03)

    except KeyboardInterrupt:
        pass

    # Brief clear before game
    try:
        LED.ClearBigLED()
        LED.ClearBuffers()
    except Exception:
        pass


#------------------------------------------------------------------------------
# Scores (ClockConfig.ini [scores], same pattern as SpaceDot / DotInvaders)
#------------------------------------------------------------------------------
def LoadPacDotScores():
    """Reload PacDot high score / games played from ClockConfig.ini."""
    global PacDotHighScore, PacDotGamesPlayed
    try:
        LED.LoadConfigData()
        PacDotHighScore = int(getattr(LED, "PacDotHighScore", 0) or 0)
        PacDotGamesPlayed = int(getattr(LED, "PacDotGamesPlayed", 0) or 0)
    except Exception as e:
        print(f"[PacDot] LoadPacDotScores: {e}")
        PacDotHighScore = 0
        PacDotGamesPlayed = 0
    print("[PacDot] Loaded high score={}  games={}".format(
        PacDotHighScore, PacDotGamesPlayed))


def SavePacDotScores():
    """Persist PacDot high score / games played into ClockConfig.ini."""
    global PacDotHighScore, PacDotGamesPlayed
    try:
        LED.PacDotHighScore = int(PacDotHighScore)
        LED.PacDotGamesPlayed = int(PacDotGamesPlayed)
        LED.SaveConfigData()
        print("[PacDot] Saved high score={}  games={}".format(
            PacDotHighScore, PacDotGamesPlayed))
    except Exception as e:
        print(f"[PacDot] SavePacDotScores: {e}")


def MaybeUpdateHighScore():
    """If current run beat the high score, update + save."""
    global PacDotHighScore, PacDotScore
    if PacDotScore > PacDotHighScore:
        PacDotHighScore = PacDotScore
        SavePacDotScores()
        return True
    return False


#------------------------------------------------------------------------------
# HUD
#------------------------------------------------------------------------------
def _draw_clock_sprite_on_hud(clock_sprite, h0, v0, rgb):
    """Draw CreateClockSprite grid into the HUD with setpixel."""
    r, g, b = rgb
    for count in range(clock_sprite.width * clock_sprite.height):
        if clock_sprite.grid[count] == 0:
            continue
        y, x = divmod(count, clock_sprite.width)
        hx = h0 + x
        hy = v0 + y
        if hx >= HUD_H0 and hx < LED.HatWidth and 0 <= hy < LED.HatHeight:
            LED.setpixel(hx, hy, r, g, b)


def _hud_right_text(v, message, rgb):
    """Right-justify a banner message in the HUD (right half of panel)."""
    msg = str(message).upper()
    if not msg:
        return
    try:
        banner = LED.CreateBannerSprite(msg)
        # 1px padding from right edge
        h = LED.HatWidth - banner.width - 1
        if h < HUD_H0:
            h = HUD_H0
        LED.DisplayScoreMessage(
            h=h, v=v, Message=msg, RGB=rgb, FillerRGB=(0, 0, 0),
        )
    except Exception as e:
        print(f"[PacDot] HUD right text '{msg}': {e}")


def DrawLivesIndicator():
    """
    Pac lives on the bottom blue wall of the playfield, bottom-left,
    along the border line (h=1,3,5 …).
    """
    v = PF_V0 + PF_H - 1  # bottom wall row
    for i in range(PAC_START_LIVES):
        h = 1 + i * 2
        if not pf_in_bounds(h, v):
            continue
        if i < PacLives:
            LED.setpixel(h, v, LED.PacR, LED.PacG, LED.PacB)
        else:
            # empty slot — restore blue wall
            LED.setpixel(h, v, LED.WallR, LED.WallG, LED.WallB)


def draw_hud(force=False, moves=0):
    """Right-half status: time / level / score / high score (right-justified)."""
    if not force and moves % HUD_REFRESH_EVERY != 0:
        return

    for h in range(HUD_H0, LED.HatWidth):
        for v in range(0, LED.HatHeight):
            LED.setpixel(h, v, 0, 0, 0)

    try:
        # Current time (HH:MM), right-justified in HUD
        clock = LED.CreateClockSprite(24)
        clock_h = LED.HatWidth - clock.width - 1
        if clock_h < HUD_H0:
            clock_h = HUD_H0
        clock_rgb = LED.MedCyan if hasattr(LED, "MedCyan") else (0, 180, 180)
        _draw_clock_sprite_on_hud(clock, clock_h, 1, clock_rgb)

        _hud_right_text(8, "L" + str(LevelCount), LED.MedCyan)
        _hud_right_text(15, str(PacDotScore), LED.MedGreen)
        _hud_right_text(21, "HI", LED.MedRed)
        _hud_right_text(26, str(PacDotHighScore), LED.MedBlue)
    except Exception as e:
        print(f"[PacDot] HUD text fallback: {e}")
        try:
            now = datetime.now().strftime("%H%M")
            _hud_right_text(1, now, LED.MedCyan)
        except Exception:
            pass

    # Lives sit on the playfield bottom border (not the HUD)
    DrawLivesIndicator()


def start_positions():
    """Scale classic spawn layout into 32x32 playfield interior."""
    cx = PF_H0 + PF_W // 2
    pac = (cx, PF_V0 + 2)
    gv = PF_V0 + PF_H - 4
    g1 = (cx - 3, gv)
    g2 = (cx - 1, gv)
    g3 = (cx + 1, gv)
    g4 = (cx + 3, gv)
    return pac, g1, g2, g3, g4


#------------------------------------------------------------------------------
# Inter-level / game-over animations
# Uses the same MoveAnimatedSprite* helpers as DisplayDigitalClock styles
# (not the old ScrollAcrossScreen path — that looks broken on 64x32).
#------------------------------------------------------------------------------
def _stop_requested(StopEvent):
    try:
        return StopEvent is not None and StopEvent.is_set()
    except Exception:
        return False


def _prep_anim_screen():
    """Clear LED + ScreenArray so MoveAnimated* floats over a clean field."""
    try:
        LED.ClearBigLED()
        LED.ClearBuffers()
    except Exception:
        pass


def _anim_ghosts_chase_pac(zoom=None, sleep=0.03):
    """Clock-style: ThreeGhostPacSprite right (DisplayDigitalClock r==3)."""
    z = zoom if zoom is not None else random.randint(1, 2)
    LED.MoveAnimatedSpriteAcrossScreenFramesPerStep(
        LED.ThreeGhostPacSprite,
        Position="bottom",
        direction="right",
        FramesPerStep=1,
        ZoomFactor=z,
        sleep=sleep,
    )


def _anim_pac_chases_blue_ghosts(zoom=None, sleep=0.02):
    """Clock-style: ThreeBlueGhostPacSprite left (power-pill reverse)."""
    z = zoom if zoom is not None else random.randint(1, 2)
    LED.MoveAnimatedSpriteAcrossScreenFramesPerStep(
        LED.ThreeBlueGhostPacSprite,
        Position="bottom",
        direction="left",
        FramesPerStep=1,
        ZoomFactor=z,
        sleep=sleep,
    )


def _anim_pac_solo(direction="right", zoom=None, sleep=None):
    """Clock-style: PacManLeft/Right via StepsPerFrame (DisplayDigitalClock r==13)."""
    z = zoom if zoom is not None else random.randint(1, 3)
    if sleep is None:
        sleep = 0.03 / max(1, z)
    if direction == "right":
        spr = LED.PacManRightSprite
    else:
        spr = LED.PacManLeftSprite
    LED.MoveAnimatedSpriteAcrossScreenStepsPerFrame(
        spr,
        Position="bottom",
        Vadjust=0,
        direction=direction,
        StepsPerFrame=max(1, z),
        ZoomFactor=z,
        sleep=sleep,
    )


def _anim_pac_round_trip():
    """Pac chomps right, then left — same pattern as clock style 13."""
    z = random.randint(1, 3)
    LED.MoveAnimatedSpriteAcrossScreenStepsPerFrame(
        LED.PacManRightSprite,
        Position="random",
        Vadjust=0,
        direction="right",
        StepsPerFrame=z,
        ZoomFactor=z,
        sleep=0.03 / z,
    )
    z = random.randint(1, 3)
    LED.MoveAnimatedSpriteAcrossScreenStepsPerFrame(
        LED.PacManLeftSprite,
        Position="random",
        Vadjust=0,
        direction="left",
        StepsPerFrame=z,
        ZoomFactor=z,
        sleep=0.03 / z,
    )


def _anim_classic_chase_pair():
    """Exact clock-style ghost chase pair used in DisplayDigitalClock / DisplayRandomAnimation."""
    z = random.randint(1, 2)
    LED.MoveAnimatedSpriteAcrossScreenFramesPerStep(
        LED.ThreeGhostPacSprite,
        Position="bottom",
        direction="right",
        FramesPerStep=1,
        ZoomFactor=z,
        sleep=0.03,
    )
    z = random.randint(1, 2)
    LED.MoveAnimatedSpriteAcrossScreenFramesPerStep(
        LED.ThreeBlueGhostPacSprite,
        Position="bottom",
        direction="left",
        FramesPerStep=1,
        ZoomFactor=z,
        sleep=0.02,
    )


def _show_level_banner(level):
    """Glowing level text (same ShowGlowingText path as clock/demo banners)."""
    _prep_anim_screen()
    try:
        LED.ShowGlowingText(
            CenterHoriz=True, CenterVert=True, h=0, v=0,
            Text="LVL " + str(level),
            RGB=getattr(LED, "HighYellow", (200, 180, 0)),
            ShadowRGB=getattr(LED, "ShadowYellow", (30, 30, 0)),
            ZoomFactor=2, GlowLevels=50, DropShadow=True,
            FadeLevels=40, FadeDelay=0.35,
        )
    except Exception:
        try:
            LED.DisplayScoreMessage(
                Message="L" + str(level),
                RGB=getattr(LED, "MedYellow", (180, 160, 0)),
                FillerRGB=(0, 0, 0),
            )
            time.sleep(0.5)
        except Exception:
            time.sleep(0.2)


def PlayInterLevelAnimation(cleared_level, next_level, StopEvent=None):
    """
    Celebrate a cleared level using DisplayDigitalClock animation helpers.
    Sequences rotate so consecutive levels feel different.
    """
    if _stop_requested(StopEvent):
        return

    print("[PacDot] Inter-level animation after level {} (clock-style movers)".format(
        cleared_level))
    _prep_anim_screen()
    _show_level_banner(cleared_level)
    if _stop_requested(StopEvent):
        return

    _prep_anim_screen()
    seq = cleared_level % 5
    try:
        if seq == 1:
            # Classic clock r==3 pair
            _anim_classic_chase_pair()
        elif seq == 2:
            # Pac round-trip (clock r==13)
            _anim_pac_round_trip()
        elif seq == 3:
            # Pac then ghosts chase
            _anim_pac_solo("right", zoom=2)
            if _stop_requested(StopEvent):
                return
            _prep_anim_screen()
            _anim_ghosts_chase_pac(zoom=2, sleep=0.025)
        elif seq == 4:
            # Power-pill reverse then solo pac
            _anim_pac_chases_blue_ghosts(zoom=2, sleep=0.02)
            if _stop_requested(StopEvent):
                return
            _prep_anim_screen()
            _anim_pac_solo("left", zoom=2)
        else:
            # Bigger victory lap (zoom 2–3)
            _anim_pac_solo("right", zoom=3)
            if _stop_requested(StopEvent):
                return
            _prep_anim_screen()
            _anim_classic_chase_pair()
    except Exception as e:
        print(f"[PacDot] Inter-level animation error: {e}")

    if _stop_requested(StopEvent):
        return

    _prep_anim_screen()
    try:
        LED.ShowGlowingText(
            CenterHoriz=True, CenterVert=True, h=0, v=0,
            Text="GO " + str(next_level),
            RGB=getattr(LED, "MedGreen", (0, 180, 0)),
            ShadowRGB=getattr(LED, "ShadowGreen", (0, 25, 0)),
            ZoomFactor=2, GlowLevels=40, DropShadow=True,
            FadeLevels=30, FadeDelay=0.3,
        )
    except Exception:
        time.sleep(0.25)

    _prep_anim_screen()


def ShowGameOverSlideDown(StopEvent=None):
    """
    'GAME OVER' slides from above the top of the panel straight down
    and off the bottom (vertical scroll, not horizontal banner).
    """
    if _stop_requested(StopEvent):
        return
    print("[PacDot] GAME OVER slide-down")
    _prep_anim_screen()

    try:
        banner = LED.CreateBannerSprite("GAME OVER")
    except Exception as e:
        print(f"[PacDot] CreateBannerSprite failed: {e}")
        try:
            LED.ShowGlowingText(
                CenterHoriz=True, CenterVert=True, h=0, v=0,
                Text="GAME OVER",
                RGB=getattr(LED, "HighRed", (200, 0, 0)),
                ShadowRGB=getattr(LED, "ShadowRed", (30, 0, 0)),
                ZoomFactor=1, GlowLevels=30, DropShadow=True,
            )
            time.sleep(1.2)
        except Exception:
            pass
        return

    # Fit on 64-wide panel; zoom 1 keeps "GAME OVER" readable
    zoom = 1
    text_w = banner.width * zoom
    text_h = banner.height * zoom
    if text_w > LED.HatWidth and banner.width > 0:
        zoom = 1
    h = max(0, (LED.HatWidth - banner.width * zoom) // 2)
    rgb = getattr(LED, "HighRed", (220, 0, 0))
    sleep = 0.035

    # Start fully above the panel; end fully below
    v_start = -text_h - 1
    v_end = LED.HatHeight + text_h + 1
    for v in range(v_start, v_end + 1):
        if _stop_requested(StopEvent):
            return
        try:
            LED.ClearBigLED()
        except Exception:
            pass
        try:
            LED.CopySpriteToPixelsZoom(
                banner, h, v, rgb, (0, 0, 0), zoom, Fill=False,
            )
        except Exception:
            # Fallback: draw via Display if CopySprite fails
            try:
                banner.r, banner.g, banner.b = rgb
                banner.Display(h, v)
            except Exception:
                pass
        time.sleep(sleep)

    _prep_anim_screen()


def BuildPacMan32ScreenArray(mouth_deg=42):
    """
    Build a full-panel ScreenArray with a crisp 32×32 classic Pac-Man
    (full panel height) centered horizontally. Mouth opens to the right.
    Used as the source image for the final spin/shrink exit.
    """
    size = 32
    w = LED.HatWidth
    h = LED.HatHeight
    arr = [[(0, 0, 0) for _ in range(w)] for _ in range(h)]

    # Center 32×32 block on the matrix (on 64×32: ox=16, oy=0)
    ox = max(0, (w - size) // 2)
    oy = max(0, (h - size) // 2)

    # Pac yellow (match game colors)
    try:
        body = (LED.PacR, LED.PacG, LED.PacB)
    except Exception:
        body = getattr(LED, "HighYellow", (220, 200, 40))
    # Slightly brighter highlight / darker eye
    try:
        highlight = getattr(LED, "HighYellow", body)
    except Exception:
        highlight = body
    eye = (15, 15, 50)

    cx = size / 2.0 - 0.5
    cy = size / 2.0 - 0.5
    radius = size / 2.0 - 0.6
    mouth_half = math.radians(mouth_deg)

    for py in range(size):
        for px in range(size):
            dx = px - cx
            dy = py - cy
            dist = math.sqrt(dx * dx + dy * dy)
            if dist > radius:
                continue

            # Angle: 0 = +X (right), range (-pi, pi]
            ang = math.atan2(dy, dx)
            # Open mouth wedge facing right
            if abs(ang) < mouth_half:
                continue

            # Soft outer rim — a touch brighter
            if dist > radius - 1.1:
                rgb = highlight
            else:
                rgb = body

            arr[oy + py][ox + px] = rgb

    # Eye (upper-left of face center, classic look)
    eye_cx = int(round(cx - 2))
    eye_cy = int(round(cy - 7))
    for ey in range(eye_cy - 1, eye_cy + 2):
        for ex in range(eye_cx - 1, eye_cx + 2):
            if 0 <= ex < size and 0 <= ey < size:
                if (ex - eye_cx) ** 2 + (ey - eye_cy) ** 2 <= 2:
                    arr[oy + ey][ox + ex] = eye
    # Pupil
    if 0 <= eye_cx < size and 0 <= eye_cy < size:
        arr[oy + eye_cy][ox + eye_cx] = (0, 0, 0)

    return arr


def ShowPacSpinShrink(StopEvent=None):
    """
    32×32 Pac-Man centered on the panel, spinning while shrinking away.
    Uses SpinShrinkTransition (same family as clock title exits).
    """
    if _stop_requested(StopEvent):
        return
    print("[PacDot] PacMan 32x32 spin-shrink exit")
    _prep_anim_screen()

    try:
        arr = BuildPacMan32ScreenArray(mouth_deg=42)
        # Rotate ~2 full turns while shrinking from full size to nothing
        LED.SpinShrinkTransition(
            arr,
            steps=60,
            delay=0.028,
            start_zoom=100,
            end_zoom=0,
            StopEvent=StopEvent,
        )
    except Exception as e:
        print(f"[PacDot] Pac 32x32 spin-shrink failed: {e}")
        # Fallback: paint 32x32 static then simple step-down
        try:
            arr = BuildPacMan32ScreenArray()
            for y in range(LED.HatHeight):
                for x in range(LED.HatWidth):
                    r, g, b = arr[y][x]
                    LED.setpixel(x, y, r, g, b)
            time.sleep(0.4)
            LED.SpinShrinkTransition(
                arr, steps=40, delay=0.03,
                start_zoom=100, end_zoom=0, StopEvent=StopEvent,
            )
        except Exception as e2:
            print(f"[PacDot] Pac shrink fallback failed: {e2}")

    _prep_anim_screen()


def PlayGameOverAnimation(StopEvent=None):
    """
    Final death sequence (after 3 lives):
      1. GAME OVER slides from top off the bottom
      2. Large PacMan spins and shrinks away
    """
    if _stop_requested(StopEvent):
        return
    print("[PacDot] Final GAME OVER sequence")
    _prep_anim_screen()

    ShowGameOverSlideDown(StopEvent=StopEvent)
    if _stop_requested(StopEvent):
        return
    time.sleep(0.2)
    ShowPacSpinShrink(StopEvent=StopEvent)
    _prep_anim_screen()


#------------------------------------------------------------------------------
# Main play loop
#------------------------------------------------------------------------------
def PlayPacDot(Duration=10, StopEvent=None):
    """
    Run PacDot AI game on left 32x32.
    Duration: minutes (wall clock), same convention as DotInvaders/SpaceDot.
    """
    global PowerPillActive, PowerPillMoves, PacDotScore, PacDotHighScore
    global PacDotGamesPlayed, LevelCount
    global Ghost1Alive, Ghost2Alive, Ghost3Alive, Ghost4Alive
    global Ghost1H, Ghost1V, Ghost2H, Ghost2V, Ghost3H, Ghost3V, Ghost4H, Ghost4V
    global Pacmoves, PacDead, PacLives

    print("[PacDot] PlayPacDot start  PF={}x{} at ({},{})  Duration={} min".format(
        PF_W, PF_H, PF_H0, PF_V0, Duration))

    LoadPacDotScores()

    start_time = time.time()
    PacDotScore = 0
    LevelCount = 1
    PacLives = PAC_START_LIVES
    finished = False

    while not finished:
        if StopEvent is not None and StopEvent.is_set():
            print("[PacDot] StopEvent before level")
            return

        try:
            _h, m_e, _s = LED.GetElapsedTime(start_time, time.time())
        except Exception:
            m_e = (time.time() - start_time) / 60.0
        if m_e >= Duration:
            print("[PacDot] Duration reached")
            break

        LED.ClearBigLED()
        ClearPlayfield()
        ClearHUD()
        ResetDotMatrix()
        DrawPlayfieldBorder()

        pac, g1, g2, g3, g4 = start_positions()
        PacDotH, PacDotV = pac
        Ghost1H, Ghost1V = g1
        Ghost2H, Ghost2V = g2
        Ghost3H, Ghost3V = g3
        Ghost4H, Ghost4V = g4

        Ghost1Alive = Ghost2Alive = Ghost3Alive = Ghost4Alive = 1
        ResetGhostTrain()
        PacDead = False
        PowerPillActive = 0
        PowerPillMoves = 0
        PacStuckCount = 0
        PacOldH, PacOldV = -1, -1
        dots_eaten = 0
        moves = 0

        ghost_speed1 = START_GHOST_SPEED1
        ghost_speed2 = START_GHOST_SPEED2
        ghost_speed3 = START_GHOST_SPEED3
        ghost_speed4 = START_GHOST_SPEED4
        dir1 = randint(1, 4)
        dir2 = randint(1, 4)
        dir3 = randint(1, 4)
        dir4 = randint(1, 4)
        dir_pac = randint(1, 4)

        DrawDots(NUM_DOTS_DEFAULT)
        for hh, vv in (pac, g1, g2, g3, g4):
            LED.DotMatrix[hh][vv] = 0
            LED.setpixel(hh, vv, 0, 0, 0)

        DrawPowerPills(POWER_PILLS)
        DrawDotMatrix()

        DrawGhost(Ghost1H, Ghost1V, LED.Ghost1R, LED.Ghost1G, LED.Ghost1B)
        DrawGhost(Ghost2H, Ghost2V, LED.Ghost2R, LED.Ghost2G, LED.Ghost2B)
        DrawGhost(Ghost3H, Ghost3V, LED.Ghost3R, LED.Ghost3G, LED.Ghost3B)
        DrawGhost(Ghost4H, Ghost4V, LED.Ghost4R, LED.Ghost4G, LED.Ghost4B)
        DrawPacDot(PacDotH, PacDotV, LED.PacR, LED.PacG, LED.PacB)
        draw_hud(force=True)

        dots_remaining = CountDotsRemaining()
        print("[PacDot] Level {}  dots={}".format(LevelCount, dots_remaining))

        while (moves < MAX_MOVES and dots_remaining > 0 and
               PacStuckCount <= PAC_STUCK_MAX and not PacDead):

            if StopEvent is not None and StopEvent.is_set():
                print("[PacDot] StopEvent in loop")
                return

            try:
                _h, m_e, _s = LED.GetElapsedTime(start_time, time.time())
            except Exception:
                m_e = (time.time() - start_time) / 60.0
            if m_e >= Duration:
                print("[PacDot] Duration reached mid-level")
                finished = True
                break

            dots_remaining = CountDotsRemaining()
            moves += 1
            PacOldH, PacOldV = PacDotH, PacDotV

            if PowerPillActive == 1:
                PowerPillMoves += 1
                ghost_speed1 = BLUE_GHOST_SPEED
                ghost_speed2 = BLUE_GHOST_SPEED
                ghost_speed3 = BLUE_GHOST_SPEED
                ghost_speed4 = BLUE_GHOST_SPEED
                if Ghost1Alive == 0 and Ghost2Alive == 0 and Ghost3Alive == 0 and Ghost4Alive == 0:
                    PowerPillActive = 0
                    PowerPillMoves = 999

                if PowerPillMoves >= BLUE_GHOST_MOVES:
                    dots_remaining = CountDotsRemaining()
                    PowerPillActive = 0
                    PowerPillMoves = 0
                    ghost_speed1 = START_GHOST_SPEED1
                    ghost_speed2 = START_GHOST_SPEED2
                    ghost_speed3 = START_GHOST_SPEED3
                    ghost_speed4 = START_GHOST_SPEED4
                    if Ghost1Alive == 0:
                        Ghost1Alive = 1
                        Ghost1H, Ghost1V = g1
                    if Ghost2Alive == 0:
                        Ghost2Alive = 1
                        Ghost2H, Ghost2V = g2
                    if Ghost3Alive == 0:
                        Ghost3Alive = 1
                        Ghost3H, Ghost3V = g3
                    if Ghost4Alive == 0:
                        Ghost4Alive = 1
                        Ghost4H, Ghost4V = g4

            # Free ghosts only (attached ones follow as train behind Pac)
            if Ghost1Alive == 1 and not Ghost1Attached and moves % ghost_speed1 == 0:
                if PowerPillActive == 1:
                    dir1 = TurnAwayFromDot4Way(Ghost1H, Ghost1V, dir1, PacDotH, PacDotV)
                elif randint(1, 3) == 1:
                    dir1 = TurnTowardsDot4Way(Ghost1H, Ghost1V, dir1, PacDotH, PacDotV)
                Ghost1H, Ghost1V, dir1 = MoveGhost(
                    Ghost1H, Ghost1V, dir1, LED.Ghost1R, LED.Ghost1G, LED.Ghost1B, 1)
                if not Ghost1Attached:
                    DrawGhost(Ghost1H, Ghost1V, LED.Ghost1R, LED.Ghost1G, LED.Ghost1B)

            if Ghost2Alive == 1 and not Ghost2Attached and moves % ghost_speed2 == 0:
                if PowerPillActive == 1:
                    dir2 = TurnAwayFromDot4Way(Ghost2H, Ghost2V, dir2, PacDotH, PacDotV)
                elif randint(1, 4) == 1:
                    dir2 = TurnTowardsDot4Way(Ghost2H, Ghost2V, dir2, PacDotH, PacDotV)
                Ghost2H, Ghost2V, dir2 = MoveGhost(
                    Ghost2H, Ghost2V, dir2, LED.Ghost2R, LED.Ghost2G, LED.Ghost2B, 2)
                if not Ghost2Attached:
                    DrawGhost(Ghost2H, Ghost2V, LED.Ghost2R, LED.Ghost2G, LED.Ghost2B)

            if Ghost3Alive == 1 and not Ghost3Attached and moves % ghost_speed3 == 0:
                if PowerPillActive == 1:
                    dir3 = TurnAwayFromDot4Way(Ghost3H, Ghost3V, dir3, PacDotH, PacDotV)
                elif randint(1, 4) == 1:
                    dir3 = TurnTowardsDot4Way(Ghost3H, Ghost3V, dir3, PacDotH, PacDotV)
                Ghost3H, Ghost3V, dir3 = MoveGhost(
                    Ghost3H, Ghost3V, dir3, LED.Ghost3R, LED.Ghost3G, LED.Ghost3B, 3)
                if not Ghost3Attached:
                    DrawGhost(Ghost3H, Ghost3V, LED.Ghost3R, LED.Ghost3G, LED.Ghost3B)

            if Ghost4Alive == 1 and not Ghost4Attached and moves % ghost_speed4 == 0:
                if PowerPillActive == 1:
                    dir4 = TurnAwayFromDot4Way(Ghost4H, Ghost4V, dir4, PacDotH, PacDotV)
                elif randint(1, 5) == 1:
                    dir4 = TurnTowardsDot4Way(Ghost4H, Ghost4V, dir4, PacDotH, PacDotV)
                Ghost4H, Ghost4V, dir4 = MoveGhost(
                    Ghost4H, Ghost4V, dir4, LED.Ghost4R, LED.Ghost4G, LED.Ghost4B, 4)
                if not Ghost4Attached:
                    DrawGhost(Ghost4H, Ghost4V, LED.Ghost4R, LED.Ghost4G, LED.Ghost4B)

            if moves % PAC_SPEED == 0:
                if PowerPillActive == 1:
                    # Hunt free living ghosts (skip attached — they aren't free targets)
                    for gid in (1, 2, 3, 4):
                        if _is_alive(gid) and not _is_attached(gid):
                            th, tv = _get_ghost_pos(gid)
                            dir_pac = TurnTowardsDot4Way(PacDotH, PacDotV, dir_pac, th, tv)
                            break
                else:
                    if randint(1, 5) == 1:
                        cx, cy = FindClosestDot(PacDotH, PacDotV)
                        dir_pac = TurnTowardsDot4Way(PacDotH, PacDotV, dir_pac, cx, cy)

                dir_pac = FollowScanner(PacDotH, PacDotV, dir_pac)
                prev_h, prev_v = PacDotH, PacDotV
                PacDotH, PacDotV, dir_pac, dots_eaten = MovePacDot(
                    PacDotH, PacDotV, dir_pac, LED.PacR, LED.PacG, LED.PacB, dots_eaten)
                # Snake follow: attached ghosts trail Pac's previous cell
                if (PacDotH, PacDotV) != (prev_h, prev_v):
                    UpdateGhostTrain(prev_h, prev_v)
                else:
                    # Pac didn't move (wall/turn) — still redraw train cars
                    DrawGhostTrain()
                DrawPacDot(PacDotH, PacDotV, LED.PacR, LED.PacG, LED.PacB)

                # Full train = death
                if AllGhostsAttached():
                    PacDead = True
                    ShowPacMegaExplosion(PacDotH, PacDotV)
                    print("[PacDot] All ghosts attached — PacDot destroyed")

            if randint(1, 40) == 1:
                DrawDotMatrix()
                # Re-draw actors on top of refreshed dots
                DrawGhostTrain()
                if Ghost1Alive and not Ghost1Attached:
                    DrawGhost(Ghost1H, Ghost1V, LED.Ghost1R, LED.Ghost1G, LED.Ghost1B)
                if Ghost2Alive and not Ghost2Attached:
                    DrawGhost(Ghost2H, Ghost2V, LED.Ghost2R, LED.Ghost2G, LED.Ghost2B)
                if Ghost3Alive and not Ghost3Attached:
                    DrawGhost(Ghost3H, Ghost3V, LED.Ghost3R, LED.Ghost3G, LED.Ghost3B)
                if Ghost4Alive and not Ghost4Attached:
                    DrawGhost(Ghost4H, Ghost4V, LED.Ghost4R, LED.Ghost4G, LED.Ghost4B)
                DrawPacDot(PacDotH, PacDotV, LED.PacR, LED.PacG, LED.PacB)

            if PacOldH == PacDotH and PacOldV == PacDotV:
                PacStuckCount += 1
            else:
                PacStuckCount = 0

            draw_hud(moves=moves)
            # Keep the blue wall solid (explosions / trail restore can punch holes)
            DrawPlayfieldBorder()
            if MAIN_SLEEP > 0:
                time.sleep(MAIN_SLEEP)

        if finished:
            break

        # Death: full ghost train, or stuck for too long
        died = PacDead or (dots_remaining > 0 and PacStuckCount > PAC_STUCK_MAX)
        if died:
            PacLives -= 1
            print("[PacDot] Death  lives left={}  score={}  train={}".format(
                PacLives, PacDotScore, PacDead))
            if not PacDead:
                # Stuck death — still play a boom at Pac
                try:
                    ShowPacMegaExplosion(PacDotH, PacDotV)
                except Exception:
                    pass

            if PacLives > 0:
                # Brief "lives remaining" flash, then respawn same level
                try:
                    LED.ClearBigLED()
                    LED.ClearBuffers()
                    LED.ShowGlowingText(
                        CenterHoriz=True, CenterVert=True, h=0, v=0,
                        Text=str(PacLives) + " LEFT",
                        RGB=getattr(LED, "HighYellow", (220, 200, 0)),
                        ShadowRGB=getattr(LED, "ShadowYellow", (30, 30, 0)),
                        ZoomFactor=2, GlowLevels=35, DropShadow=True,
                        FadeLevels=25, FadeDelay=0.45,
                    )
                except Exception:
                    time.sleep(0.6)
                continue  # same LevelCount, new life

            # Out of lives — final sequence, then exit so LEDcommander can rotate
            PacDotGamesPlayed += 1
            MaybeUpdateHighScore()
            SavePacDotScores()
            PlayGameOverAnimation(StopEvent=StopEvent)
            print("[PacDot] Game over — exiting session for next rotation item")
            return

        if dots_remaining == 0:
            print("[PacDot] Level {} cleared  score={}".format(LevelCount, PacDotScore))
            MaybeUpdateHighScore()
            cleared = LevelCount
            LevelCount += 1
            PlayInterLevelAnimation(cleared, LevelCount, StopEvent=StopEvent)
            if StopEvent is not None and StopEvent.is_set():
                return
            continue

        # Max moves without clearing — treat as soft end of run (no life loss)
        print("[PacDot] Level timeout  score={}  moves={}".format(PacDotScore, moves))
        LevelCount += 1
        continue

    print("[PacDot] Done  score={}  high={}  levels={}  lives={}".format(
        PacDotScore, PacDotHighScore, LevelCount, PacLives))


def LaunchPacDot(Duration=5, ShowIntro=True, StopEvent=None):
    """
    Entry point for LEDcommander / standalone.
    Duration is minutes (default 5). Returns when time is up, StopEvent fires,
    or Pac runs out of lives (after GAME OVER sequence) so rotation can continue.
    """
    # Always load scores before a session (high score on HUD)
    LoadPacDotScores()

    try:
        Duration = int(Duration)
    except (TypeError, ValueError):
        Duration = 5
    if Duration <= 0:
        Duration = 5

    if ShowIntro:
        if StopEvent is not None and StopEvent.is_set():
            return
        LED.ClearBigLED()
        LED.ClearBuffers()
        # Skyfall-style letter intro, but letters slide in from left/right
        PlayPacDotTitleIntro(StopEvent=StopEvent)

    if StopEvent is not None and StopEvent.is_set():
        return

    LED.ClearBigLED()
    LED.ClearBuffers()
    PlayPacDot(Duration=Duration, StopEvent=StopEvent)
    print("[PacDot] LaunchPacDot complete")


if __name__ == "__main__":
    while True:
        LaunchPacDot(Duration=100000, ShowIntro=True, StopEvent=None)
