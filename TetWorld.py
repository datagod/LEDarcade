#!/usr/bin/env python
#------------------------------------------------------------------------------
#  TET WORLD — hunt
#
#  Floor is two display panels wide and four tall (128×128 on a 64×32 hat).
#  Long wall bars.  Ten 1-pixel robots hunt one blue human.
#  Robots hear noise to 10 px, talk over line of sight, share a suspected
#  Green dots give a weapon and a health stim, then vanish.
#  Camera shows one 64×32 screen at a time, keyed to the human's screen.
#------------------------------------------------------------------------------

from __future__ import print_function

import math
import random
import time

import LEDarcade as LED


WIDTH = LED.HatWidth
HEIGHT = LED.HatHeight

PANELS_W = 2
PANELS_H = 4
CELL = 2
GAP_PX = 4
GAP_CELLS = GAP_PX // CELL

SCREEN_SCROLL = 0.28        # seconds to slide from one screen to the next

ROBOT_COUNT = 10
ROBOT_SPEED = 9.0
HUMAN_SPEED = 22.0
MISSILE_SPEED = 48.0
HEAR_RANGE = 10
SIGHT_RANGE = 28
INTEL_TTL = 4.5
SHOT_COOLDOWN = 0.28
SHOTS_PER_WEAPON = 3
WEAPON_COUNT = 7
HUMAN_MAX_HP = 3
STIM_HEAL = 1
ROBOT_DAMAGE = 1
HIT_IFRAMES = 0.8

ROBOT_RGB = (255, 245, 180)
HUMAN_RGB = (40, 90, 255)
WEAPON_RGB = (20, 255, 70)
MISSILE_RGB = (255, 0, 0)
MISSILE_TRAIL_RGB = (255, 70, 20)

DIRS = (
    (1, 0), (-1, 0), (0, 1), (0, -1),
    (1, 1), (1, -1), (-1, 1), (-1, -1),
)

FLOOR = (0, 0, 0)
WALL_COLORS = (
    (88, 86, 80),
    (70, 74, 82),
    (104, 90, 68),
    (62, 68, 76),
    (96, 78, 72),
)

EMPTY, BLOCK = 0, 1


def _panel_size():
    return int(LED.HatWidth), int(LED.HatHeight)


def _clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def _shade(rgb, factor):
    return (
        _clamp(int(rgb[0] * factor), 0, 255),
        _clamp(int(rgb[1] * factor), 0, 255),
        _clamp(int(rgb[2] * factor), 0, 255),
    )


def _dist(ax, ay, bx, by):
    return math.hypot(ax - bx, ay - by)


#------------------------------------------------------------------------------
# World — long wall bars, 2 px thick, 4 px gaps
#------------------------------------------------------------------------------

class World(object):
    def __init__(self, grid_w, grid_h):
        self.gw = grid_w
        self.gh = grid_h
        self.pw = grid_w * CELL
        self.ph = grid_h * CELL
        self.kind = [[EMPTY for _ in range(grid_w)] for _ in range(grid_h)]
        self.rgb = [[None for _ in range(grid_w)] for _ in range(grid_h)]
        self.blocks = []

    def walkable_px(self, px, py):
        if px < 0 or py < 0 or px >= self.pw or py >= self.ph:
            return False
        return self.kind[py // CELL][px // CELL] != BLOCK

    def _too_close(self, px, py):
        r = GAP_CELLS
        for y in range(max(0, py - r), min(self.gh, py + r + 1)):
            row = self.kind[y]
            for x in range(max(0, px - r), min(self.gw, px + r + 1)):
                if row[x] == BLOCK:
                    return True
        return False

    def can_place_rect(self, x, y, w, h):
        if x < 0 or y < 0 or x + w > self.gw or y + h > self.gh:
            return False
        for dy in range(h):
            for dx in range(w):
                if self.kind[y + dy][x + dx] != EMPTY:
                    return False
                if self._too_close(x + dx, y + dy):
                    return False
        return True

    def place_rect(self, x, y, w, h, rgb):
        if not self.can_place_rect(x, y, w, h):
            return False
        for dy in range(h):
            for dx in range(w):
                self.kind[y + dy][x + dx] = BLOCK
                self.rgb[y + dy][x + dx] = rgb
        self.blocks.append((x, y, w, h, rgb))
        return True


def _world_size(panel_w, panel_h):
    return panel_w * PANELS_W, panel_h * PANELS_H


def build_world(panel_w, panel_h):
    pw, ph = _world_size(panel_w, panel_h)
    gw, gh = pw // CELL, ph // CELL
    world = World(gw, gh)
    rng = random.Random(1984)

    # Designed long halls — then fill remaining lots with more bars.
    halls = [
        (3, 4, 18, 1),
        (24, 4, 16, 1),
        (44, 4, 14, 1),
        (3, gh - 5, 18, 1),
        (24, gh - 5, 16, 1),
        (44, gh - 5, 14, 1),
        (3, 8, 1, 16),
        (3, 28, 1, 16),
        (gw - 5, 8, 1, 16),
        (gw - 5, 28, 1, 16),
        (10, 14, 14, 1),
        (32, 20, 18, 1),
        (14, 10, 1, 14),
        (40, 24, 1, 18),
        (22, 30, 20, 1),
        (8, 40, 1, 12),
        (48, 36, 1, 14),
        (18, 48, 16, 1),
    ]
    for x, y, w, h in halls:
        world.place_rect(x, y, w, h, rng.choice(WALL_COLORS))

    for _ in range(80):
        if rng.random() < 0.55:
            w, h = rng.randint(8, 22), 1
        else:
            w, h = 1, rng.randint(8, 22)
        x = rng.randint(2, max(2, gw - w - 2))
        y = rng.randint(2, max(2, gh - h - 2))
        world.place_rect(x, y, w, h, rng.choice(WALL_COLORS))

    return world


def paint_map(world):
    pixels = [[FLOOR for _ in range(world.pw)] for _ in range(world.ph)]
    for gy in range(world.gh):
        for gx in range(world.gw):
            if world.kind[gy][gx] != BLOCK:
                continue
            rgb = world.rgb[gy][gx]
            edge = _shade(rgb, 0.5)
            x0, y0 = gx * CELL, gy * CELL
            for py in range(CELL):
                row = pixels[y0 + py]
                for px in range(CELL):
                    on_edge = px == 0 or py == 0 or px == CELL - 1 or py == CELL - 1
                    row[x0 + px] = edge if on_edge else rgb
    return pixels


def _floor_pixels(world):
    spots = []
    for py in range(world.ph):
        gy = py // CELL
        row = world.kind[gy]
        for px in range(world.pw):
            if row[px // CELL] != BLOCK:
                spots.append((px, py))
    return spots


#------------------------------------------------------------------------------
# Sight / sound
#------------------------------------------------------------------------------

def _line(x0, y0, x1, y1):
    x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    x, y = x0, y0
    while True:
        yield x, y
        if x == x1 and y == y1:
            return
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x += sx
        if e2 <= dx:
            err += dx
            y += sy


def _los(world, x0, y0, x1, y1):
    first = True
    for x, y in _line(x0, y0, x1, y1):
        if first:
            first = False
            continue
        if x == int(x1) and y == int(y1):
            return True
        if not world.walkable_px(x, y):
            return False
    return True


def _hear(listener, noise_x, noise_y):
    return _dist(listener.x, listener.y, noise_x, noise_y) <= HEAR_RANGE


#------------------------------------------------------------------------------
# Actors
#------------------------------------------------------------------------------

class Noise(object):
    __slots__ = ("x", "y", "t")

    def __init__(self, x, y, t):
        self.x = int(x)
        self.y = int(y)
        self.t = t


class Robot(object):
    def __init__(self, x, y):
        self.x = int(x)
        self.y = int(y)
        self.heading = random.choice(DIRS)
        self.alive = True
        self.next_step = 0.0
        self.unstick_until = 0.0
        self.stuck = 0
        self.suspect = None
        self.intel_t = -1e9

    def hear(self, noise):
        if _hear(self, noise.x, noise.y) and noise.t >= self.intel_t:
            self.suspect = (noise.x, noise.y)
            self.intel_t = noise.t

    def see_human(self, human, world, now):
        if not human.alive:
            return False
        if _dist(self.x, self.y, human.x, human.y) > SIGHT_RANGE:
            return False
        if not _los(world, self.x, self.y, human.x, human.y):
            return False
        self.suspect = (human.x, human.y)
        self.intel_t = now
        return True


class Human(object):
    def __init__(self, x, y):
        self.x = int(x)
        self.y = int(y)
        self.heading = random.choice(DIRS)
        self.alive = True
        self.next_step = 0.0
        self.next_shot = 0.0
        self.ammo = 0
        self.hp = HUMAN_MAX_HP
        self.stims = 0
        self.hurt_until = 0.0
        self.stuck = 0


class Weapon(object):
    def __init__(self, x, y):
        self.x = int(x)
        self.y = int(y)
        self.alive = True


class Missile(object):
    def __init__(self, x, y, dx, dy):
        self.x = float(x)
        self.y = float(y)
        self.dx = dx
        self.dy = dy
        self.alive = True
        self.trail = []


def _pick_spread(spots, count, used, min_sep, rng):
    chosen = []
    rng.shuffle(spots)
    for px, py in spots:
        if any(abs(px - ux) + abs(py - uy) < min_sep for ux, uy in used):
            continue
        chosen.append((px, py))
        used.add((px, py))
        if len(chosen) >= count:
            break
    return chosen


def _spawn_match(world):
    rng = random.Random(int(time.time() * 1000) & 0xFFFFFFFF)
    spots = _floor_pixels(world)
    used = set()
    robots = [Robot(x, y) for x, y in _pick_spread(spots, ROBOT_COUNT, used, 14, rng)]
    humans = _pick_spread(spots, 1, used, 28, rng)
    if not humans:
        humans = [spots[rng.randrange(len(spots))]]
    human = Human(*humans[0])
    nearby = [
        (px, py) for px, py in spots
        if 4 <= abs(px - human.x) + abs(py - human.y) <= 16
        and (px, py) not in used
    ]
    weapons = [Weapon(x, y) for x, y in _pick_spread(nearby or spots, 3, used, 4, rng)]
    weapons.extend(
        Weapon(x, y) for x, y in _pick_spread(spots, WEAPON_COUNT - len(weapons), used, 8, rng)
    )
    return robots, human, weapons


#------------------------------------------------------------------------------
# Movement
#------------------------------------------------------------------------------

def _open_steps(world, x, y):
    steps = []
    for dx, dy in DIRS:
        nx, ny = x + dx, y + dy
        if world.walkable_px(nx, ny):
            steps.append((nx, ny, dx, dy))
    return steps


def _bfs_step(world, x, y, tx, ty, limit=2800):
    start = (int(x), int(y))
    goal = (int(tx), int(ty))
    if start == goal:
        return None
    q = [start]
    came = {start: None}
    qi = 0
    found = None
    while qi < len(q) and qi < limit:
        cx, cy = q[qi]
        qi += 1
        if abs(cx - goal[0]) + abs(cy - goal[1]) <= 1:
            found = (cx, cy)
            break
        for dx, dy in DIRS:
            nx, ny = cx + dx, cy + dy
            if (nx, ny) in came:
                continue
            if not world.walkable_px(nx, ny):
                continue
            came[(nx, ny)] = (cx, cy)
            q.append((nx, ny))
    if found is None:
        return None
    node = found
    while came[node] is not None and came[node] != start:
        node = came[node]
    return node if node != start else None


def _step_interval(speed):
    return 1.0 / max(5.0, speed)


def _wander_step(world, x, y, heading):
    steps = _open_steps(world, x, y)
    if not steps:
        return x, y, heading
    hx, hy = heading if heading in DIRS else DIRS[0]
    for nx, ny, dx, dy in steps:
        if dx == hx and dy == hy:
            return nx, ny, (dx, dy)
    nx, ny, dx, dy = random.choice(steps)
    return nx, ny, (dx, dy)


def _flee_step(world, x, y, threats):
    steps = _open_steps(world, x, y)
    if not steps:
        return None
    best = None
    best_score = -1e9
    for nx, ny, dx, dy in steps:
        score = 0.0
        for tx, ty in threats:
            score += _dist(nx, ny, tx, ty)
        score += random.random() * 0.3
        if score > best_score:
            best_score = score
            best = (nx, ny, dx, dy)
    return best


#------------------------------------------------------------------------------
# AI
#------------------------------------------------------------------------------

def _share_intel(world, robots, now):
    living = [r for r in robots if r.alive]
    for i, a in enumerate(living):
        for b in living[i + 1:]:
            if not _los(world, a.x, a.y, b.x, b.y):
                continue
            if a.intel_t > b.intel_t and a.suspect is not None:
                b.suspect = a.suspect
                b.intel_t = a.intel_t
            elif b.intel_t > a.intel_t and b.suspect is not None:
                a.suspect = b.suspect
                a.intel_t = b.intel_t


def _steer_robots(world, robots, human, noises, now):
    for noise in noises:
        for robot in robots:
            if robot.alive:
                robot.hear(noise)

    _share_intel(world, robots, now)

    for robot in robots:
        if not robot.alive or now < robot.next_step:
            continue
        robot.next_step = now + _step_interval(ROBOT_SPEED)

        if robot.suspect is not None and now - robot.intel_t > INTEL_TTL:
            robot.suspect = None

        saw = robot.see_human(human, world, now)
        target = None
        if saw:
            target = (human.x, human.y)
        elif robot.suspect is not None and now >= robot.unstick_until:
            target = robot.suspect

        moved = False
        if target is not None:
            nxt = _bfs_step(world, robot.x, robot.y, target[0], target[1])
            if nxt is not None:
                robot.heading = (nxt[0] - robot.x, nxt[1] - robot.y)
                robot.x, robot.y = nxt
                robot.stuck = 0
                moved = True
            if (robot.x, robot.y) == tuple(target) and not saw:
                robot.suspect = None

        if not moved:
            robot.stuck += 1
            if target is not None and robot.stuck >= 4:
                robot.unstick_until = now + 0.9
            robot.x, robot.y, robot.heading = _wander_step(
                world, robot.x, robot.y, robot.heading,
            )
            if random.random() < 0.12:
                robot.heading = random.choice(DIRS)


def _nearest_robot(human, robots):
    best = None
    best_d = 1e9
    for robot in robots:
        if not robot.alive:
            continue
        d = _dist(human.x, human.y, robot.x, robot.y)
        if d < best_d:
            best_d = d
            best = robot
    return best, best_d


def _nearest_weapon(human, weapons):
    best = None
    best_d = 1e9
    for weapon in weapons:
        if not weapon.alive:
            continue
        d = _dist(human.x, human.y, weapon.x, weapon.y)
        if d < best_d:
            best_d = d
            best = weapon
    return best, best_d


def _steer_human(world, human, robots, weapons, missiles, now):
    noises = []
    if not human.alive or now < human.next_step:
        return noises
    human.next_step = now + _step_interval(HUMAN_SPEED)

    living = [(r.x, r.y) for r in robots if r.alive]
    nearest, near_d = _nearest_robot(human, robots)
    weapon, weapon_d = _nearest_weapon(human, weapons)

    # Shoot if armed and a robot is in a clear lane.
    if human.ammo > 0 and nearest is not None and now >= human.next_shot:
        if _los(world, human.x, human.y, nearest.x, nearest.y):
            dx = nearest.x - human.x
            dy = nearest.y - human.y
            length = math.hypot(dx, dy) or 1.0
            missiles.append(Missile(human.x, human.y, dx / length, dy / length))
            human.ammo -= 1
            human.next_shot = now + SHOT_COOLDOWN
            noises.append(Noise(human.x, human.y, now))

    moved = False
    panic = living and near_d < 6
    if panic:
        flee = _flee_step(world, human.x, human.y, living)
        if flee is not None:
            human.x, human.y = flee[0], flee[1]
            human.heading = (flee[2], flee[3])
            moved = True
    elif human.ammo <= 0 and weapon is not None:
        nxt = _bfs_step(world, human.x, human.y, weapon.x, weapon.y)
        if nxt is not None:
            human.heading = (nxt[0] - human.x, nxt[1] - human.y)
            human.x, human.y = nxt
            moved = True
    elif living and near_d < 12:
        flee = _flee_step(world, human.x, human.y, living)
        if flee is not None:
            human.x, human.y = flee[0], flee[1]
            human.heading = (flee[2], flee[3])
            moved = True

    if not moved:
        human.x, human.y, human.heading = _wander_step(
            world, human.x, human.y, human.heading,
        )

    noises.append(Noise(human.x, human.y, now))

    for weapon in weapons:
        if weapon.alive and weapon.x == human.x and weapon.y == human.y:
            weapon.alive = False
            human.ammo += SHOTS_PER_WEAPON
            human.stims += 1
            if human.hp < HUMAN_MAX_HP:
                human.stims -= 1
                human.hp = min(HUMAN_MAX_HP, human.hp + STIM_HEAL)
            print(
                "[TetWorld] pickup  weapon+stim  ammo={}  hp={}/{}  stims={}".format(
                    human.ammo, human.hp, HUMAN_MAX_HP, human.stims,
                )
            )

    return noises


def _update_missiles(world, missiles, robots, dt):
    for missile in missiles:
        if not missile.alive:
            continue
        missile.trail.append((int(round(missile.x)), int(round(missile.y))))
        if len(missile.trail) > 3:
            missile.trail.pop(0)
        step = MISSILE_SPEED * dt
        missile.x += missile.dx * step
        missile.y += missile.dy * step
        px, py = int(round(missile.x)), int(round(missile.y))
        if not world.walkable_px(px, py):
            missile.alive = False
            continue
        for robot in robots:
            if robot.alive and robot.x == px and robot.y == py:
                robot.alive = False
                missile.alive = False
                print("[TetWorld] robot destroyed  remaining={}".format(
                    sum(1 for r in robots if r.alive),
                ))
                break
    missiles[:] = [m for m in missiles if m.alive]


def _catch_human(robots, human, now):
    if not human.alive:
        return False
    if now < human.hurt_until:
        return False
    for robot in robots:
        if robot.alive and robot.x == human.x and robot.y == human.y:
            human.hp -= ROBOT_DAMAGE
            human.hurt_until = now + HIT_IFRAMES
            if human.stims > 0 and human.hp < HUMAN_MAX_HP:
                human.stims -= 1
                human.hp = min(HUMAN_MAX_HP, human.hp + STIM_HEAL)
            print(
                "[TetWorld] human hit  hp={}/{}  stims={}".format(
                    human.hp, HUMAN_MAX_HP, human.stims,
                )
            )
            if human.hp <= 0:
                human.alive = False
                return True
            return False
    return False


#------------------------------------------------------------------------------
# Draw / camera
#------------------------------------------------------------------------------

def _clamp_camera(cam_x, cam_y, view_w, view_h, map_w, map_h):
    x0 = _clamp(int(round(cam_x)), 0, max(0, map_w - view_w))
    y0 = _clamp(int(round(cam_y)), 0, max(0, map_h - view_h))
    return x0, y0


def _blit_view(canvas, pixels, x0, y0, view_w, view_h):
    set_pixel = canvas.SetPixel
    for y in range(view_h):
        row = pixels[y0 + y]
        for x in range(view_w):
            r, g, b = row[x0 + x]
            set_pixel(x, y, r, g, b)


def _put(canvas, x0, y0, px, py, rgb, view_w, view_h):
    sx = px - x0
    sy = py - y0
    if 0 <= sx < view_w and 0 <= sy < view_h:
        canvas.SetPixel(sx, sy, *rgb)


def _draw_actors(canvas, robots, human, weapons, missiles, x0, y0, view_w, view_h):
    for weapon in weapons:
        if weapon.alive:
            _put(canvas, x0, y0, weapon.x, weapon.y, WEAPON_RGB, view_w, view_h)
    for missile in missiles:
        for tx, ty in missile.trail:
            _put(canvas, x0, y0, tx, ty, MISSILE_TRAIL_RGB, view_w, view_h)
        _put(
            canvas, x0, y0,
            int(round(missile.x)), int(round(missile.y)),
            MISSILE_RGB, view_w, view_h,
        )
    for robot in robots:
        if robot.alive:
            _put(canvas, x0, y0, robot.x, robot.y, ROBOT_RGB, view_w, view_h)
    if human.alive:
        _put(canvas, x0, y0, human.x, human.y, HUMAN_RGB, view_w, view_h)


def _human_screen(human, view_w, view_h, map_w, map_h):
    """0-based (col, row) of the full panel the human occupies."""
    cols = max(1, map_w // view_w)
    rows = max(1, map_h // view_h)
    col = _clamp(int(human.x) // view_w, 0, cols - 1)
    row = _clamp(int(human.y) // view_h, 0, rows - 1)
    return col, row


def _screen_origin(col, row, view_w, view_h):
    return col * view_w, row * view_h


#------------------------------------------------------------------------------
# Play
#------------------------------------------------------------------------------

def _stop_requested(StopEvent):
    try:
        return StopEvent is not None and StopEvent.is_set()
    except Exception:
        return False


def _cleanup():
    try:
        LED.ClearBigLED()
    except Exception:
        pass
    try:
        LED.ClearBuffers()
    except Exception:
        pass
    try:
        LED.TheMatrix.SwapOnVSync(LED.Canvas)
    except Exception:
        pass


def _hold_result(canvas, pixels, world, robots, human, weapons, missiles,
                 cam_x, cam_y, seconds, StopEvent):
    until = time.time() + seconds
    while time.time() < until:
        if _stop_requested(StopEvent):
            return
        x0, y0 = _clamp_camera(cam_x, cam_y, WIDTH, HEIGHT, world.pw, world.ph)
        _blit_view(canvas, pixels, x0, y0, WIDTH, HEIGHT)
        _draw_actors(canvas, robots, human, weapons, missiles, x0, y0, WIDTH, HEIGHT)
        canvas = LED.TheMatrix.SwapOnVSync(canvas)


def PlayTetWorld(Duration=10, StopEvent=None):
    global WIDTH, HEIGHT

    if _stop_requested(StopEvent):
        print("[TetWorld] Play aborted before start (StopEvent)")
        _cleanup()
        return

    WIDTH, HEIGHT = _panel_size()
    world = build_world(WIDTH, HEIGHT)
    pixels = paint_map(world)
    canvas = LED.TheMatrix.CreateFrameCanvas()

    try:
        duration_min = float(Duration) if Duration is not None else 0.0
    except (TypeError, ValueError):
        duration_min = 10.0

    print(
        "[TetWorld] HUNT  panel {}x{}  map {}x{}  walls={}  "
        "robots={}  human=1  Duration={} min".format(
            WIDTH, HEIGHT, world.pw, world.ph, len(world.blocks),
            ROBOT_COUNT, duration_min,
        )
    )

    start = time.time()

    try:
        while True:
            if _stop_requested(StopEvent):
                print("[TetWorld] StopEvent received — exiting")
                break
            now = time.time()
            if duration_min > 0 and (now - start) / 60.0 >= duration_min:
                print("[TetWorld] Duration reached")
                break

            robots, human, weapons = _spawn_match(world)
            missiles = []
            print("[TetWorld] new match  robots={}  weapons={}".format(
                len(robots), len(weapons),
            ))
            last = time.time()
            screen_col, screen_row = _human_screen(
                human, WIDTH, HEIGHT, world.pw, world.ph,
            )
            cam_x, cam_y = _screen_origin(screen_col, screen_row, WIDTH, HEIGHT)
            scroll_from = (cam_x, cam_y)
            scroll_to = (cam_x, cam_y)
            scroll_u = 1.0
            print("[TetWorld] screen {},{}".format(screen_col + 1, screen_row + 1))
            winner = None

            while winner is None:
                if _stop_requested(StopEvent):
                    print("[TetWorld] StopEvent received — exiting")
                    return
                now = time.time()
                if duration_min > 0 and (now - start) / 60.0 >= duration_min:
                    print("[TetWorld] Duration reached")
                    return
                dt = min(now - last, 0.08)
                last = now

                noises = _steer_human(world, human, robots, weapons, missiles, now)
                _steer_robots(world, robots, human, noises, now)
                _update_missiles(world, missiles, robots, dt)

                if _catch_human(robots, human, now):
                    winner = "robots"
                elif not any(r.alive for r in robots):
                    winner = "human"

                if human.alive:
                    ncol, nrow = _human_screen(
                        human, WIDTH, HEIGHT, world.pw, world.ph,
                    )
                    if (ncol, nrow) != (screen_col, screen_row):
                        scroll_from = (cam_x, cam_y)
                        scroll_to = _screen_origin(ncol, nrow, WIDTH, HEIGHT)
                        scroll_u = 0.0
                        screen_col, screen_row = ncol, nrow
                        print("[TetWorld] screen {},{}".format(
                            screen_col + 1, screen_row + 1,
                        ))

                if scroll_u < 1.0:
                    scroll_u = min(1.0, scroll_u + dt / SCREEN_SCROLL)
                    k = scroll_u * scroll_u * (3.0 - 2.0 * scroll_u)
                    cam_x = scroll_from[0] + (scroll_to[0] - scroll_from[0]) * k
                    cam_y = scroll_from[1] + (scroll_to[1] - scroll_from[1]) * k
                else:
                    cam_x, cam_y = scroll_to

                x0, y0 = _clamp_camera(cam_x, cam_y, WIDTH, HEIGHT, world.pw, world.ph)
                _blit_view(canvas, pixels, x0, y0, WIDTH, HEIGHT)
                _draw_actors(
                    canvas, robots, human, weapons, missiles, x0, y0, WIDTH, HEIGHT,
                )
                canvas = LED.TheMatrix.SwapOnVSync(canvas)

            print("[TetWorld] {} win".format(winner))
            _hold_result(
                canvas, pixels, world, robots, human, weapons, missiles,
                cam_x, cam_y, 3.0, StopEvent,
            )
    except KeyboardInterrupt:
        print("[TetWorld] interrupted")
    finally:
        _cleanup()


def LaunchTetWorld(Duration=10, StopEvent=None):
    if _stop_requested(StopEvent):
        print("[TetWorld] Launch aborted (StopEvent already set)")
        _cleanup()
        return
    LED.ClearBigLED()
    LED.ClearBuffers()
    PlayTetWorld(Duration=Duration, StopEvent=StopEvent)


if __name__ == "__main__":
    LED.Initialize()
    try:
        LaunchTetWorld(Duration=100000, StopEvent=None)
    except KeyboardInterrupt:
        print("Exiting TetWorld.")
