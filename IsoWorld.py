#!/usr/bin/env python
#------------------------------------------------------------------------------
#  ISO WORLD — a 2×4-panel isometric city of tetromino blocks
#
#  The floor is two display panels wide and four tall (128×128 on a 64×32 hat).
#  Buildings are Tetris rectangles: I O T L J S Z.  Each story is 2 pixels high.
#  The current panel is a camera into that world.  Streets are left open
#  for creatures later.
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

# 2:1 isometric cell. Each story / diamond short edge is 2 px.
TILE_W = 4
TILE_H = 2
WALL_H = 2
# Layout grain for the 2×4-panel floor — independent of drawn height.
CELL_PX = 3

CAMERA_SPEED = 2.4          # cells per second along the tour
CAMERA_DWELL = 1.1          # seconds paused at each landmark

SKY_TOP = (8, 10, 22)
SKY_HORIZON = (18, 16, 28)
FLOOR_RGB = (22, 24, 32)
STREET_RGB = (32, 34, 44)
PLAZA_RGB = (38, 36, 48)
GRID_RGB = (40, 44, 58)

# Classic tetromino hues — top / left / right faces derived from these.
PIECE_RGB = {
    "I": (40, 190, 210),
    "O": (220, 190, 50),
    "T": (160, 70, 200),
    "L": (220, 120, 40),
    "J": (50, 90, 220),
    "S": (50, 190, 80),
    "Z": (210, 50, 60),
}

TETROMINOES = {
    "I": ((0, 0), (1, 0), (2, 0), (3, 0)),
    "O": ((0, 0), (1, 0), (0, 1), (1, 1)),
    "T": ((0, 0), (1, 0), (2, 0), (1, 1)),
    "L": ((0, 0), (0, 1), (0, 2), (1, 2)),
    "J": ((1, 0), (1, 1), (1, 2), (0, 2)),
    "S": ((1, 0), (2, 0), (0, 1), (1, 1)),
    "Z": ((0, 0), (1, 0), (1, 1), (2, 1)),
}

# Kind: empty / street / plaza / block
EMPTY, STREET, PLAZA, BLOCK = 0, 1, 2, 3


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


def _mix(a, b, t):
    t = _clamp(t, 0.0, 1.0)
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


def _rotate_cells(cells, rot):
    out = list(cells)
    for _ in range(rot & 3):
        out = [(y, -x) for x, y in out]
    min_x = min(c[0] for c in out)
    min_y = min(c[1] for c in out)
    return [(x - min_x, y - min_y) for x, y in out]


def _piece_size(cells):
    return max(c[0] for c in cells) + 1, max(c[1] for c in cells) + 1


#------------------------------------------------------------------------------
# World
#------------------------------------------------------------------------------

class World(object):
    """Occupancy grid in cell units.  One cell = one tetromino square."""

    def __init__(self, grid_w, grid_h):
        self.w = grid_w
        self.h = grid_h
        self.kind = [[EMPTY for _ in range(grid_w)] for _ in range(grid_h)]
        self.height = [[0 for _ in range(grid_w)] for _ in range(grid_h)]
        self.piece = [[None for _ in range(grid_w)] for _ in range(grid_h)]
        self.rgb = [[None for _ in range(grid_w)] for _ in range(grid_h)]
        self.blocks = []

    def in_bounds_rect(self, x, y, w, h):
        return x >= 0 and y >= 0 and x + w <= self.w and y + h <= self.h

    def walkable(self, x, y):
        if x < 0 or y < 0 or x >= self.w or y >= self.h:
            return False
        return self.kind[y][x] != BLOCK

    def height_at(self, x, y):
        if x < 0 or y < 0 or x >= self.w or y >= self.h:
            return 0
        return self.height[y][x]

    def mark_rect(self, x0, y0, x1, y1, kind):
        x0 = _clamp(x0, 0, self.w)
        y0 = _clamp(y0, 0, self.h)
        x1 = _clamp(x1, 0, self.w)
        y1 = _clamp(y1, 0, self.h)
        for y in range(y0, y1):
            for x in range(x0, x1):
                if self.kind[y][x] == BLOCK:
                    continue
                self.kind[y][x] = kind

    def can_place(self, cells, x, y):
        for dx, dy in cells:
            px, py = x + dx, y + dy
            if px < 0 or py < 0 or px >= self.w or py >= self.h:
                return False
            if self.kind[py][px] != EMPTY:
                return False
        return True

    def place(self, shape, x, y, rot, height, tint=1.0):
        cells = _rotate_cells(TETROMINOES[shape], rot)
        if not self.can_place(cells, x, y):
            return False
        base = PIECE_RGB[shape]
        rgb = _shade(base, tint)
        height = max(1, int(height))
        for dx, dy in cells:
            px, py = x + dx, y + dy
            self.kind[py][px] = BLOCK
            self.height[py][px] = height
            self.piece[py][px] = shape
            self.rgb[py][px] = rgb
        self.blocks.append((shape, x, y, rot, height, rgb, cells))
        return True


def _grid_size(panel_w, panel_h):
    """World floor = 2×4 panels, carved into 3-px cells."""
    world_w = panel_w * PANELS_W
    world_h = panel_h * PANELS_H
    return max(16, world_w // CELL_PX), max(16, world_h // CELL_PX)


def build_world(panel_w, panel_h):
    """A composed tetromino city — avenues, a plaza, districts, a wall."""
    gw, gh = _grid_size(panel_w, panel_h)
    world = World(gw, gh)
    rng = random.Random(1984)

    cx, cy = gw // 2, gh // 2

    # Cross avenues and a central plaza — creature space.
    world.mark_rect(cx - 1, 1, cx + 2, gh - 1, STREET)
    world.mark_rect(1, cy - 1, gw - 1, cy + 2, STREET)
    world.mark_rect(cx - 5, cy - 5, cx + 5, cy + 5, PLAZA)

    # Ring road just inside the rim.
    world.mark_rect(1, 1, gw - 1, 3, STREET)
    world.mark_rect(1, gh - 3, gw - 1, gh - 1, STREET)
    world.mark_rect(1, 1, 3, gh - 1, STREET)
    world.mark_rect(gw - 3, 1, gw - 1, gh - 1, STREET)

    # Designed landmarks (shape, x, y, rot, height).
    landmarks = [
        # Outer I-walls
        ("I", 4, 3, 0, 2),
        ("I", 10, 3, 0, 2),
        ("I", gw - 14, 3, 0, 2),
        ("I", gw - 8, 3, 0, 2),
        ("I", 4, gh - 5, 0, 2),
        ("I", 10, gh - 5, 0, 2),
        ("I", gw - 14, gh - 5, 0, 2),
        ("I", gw - 8, gh - 5, 0, 2),
        ("I", 3, 6, 1, 2),
        ("I", 3, gh - 12, 1, 2),
        ("I", gw - 5, 6, 1, 2),
        ("I", gw - 5, gh - 12, 1, 2),
        # Plaza gatehouses
        ("T", cx - 4, cy - 8, 2, 3),
        ("T", cx + 1, cy - 8, 2, 3),
        ("T", cx - 4, cy + 6, 0, 3),
        ("T", cx + 1, cy + 6, 0, 3),
        # Corner keeps
        ("L", 5, 6, 0, 3),
        ("J", gw - 8, 6, 0, 3),
        ("J", 5, gh - 10, 2, 3),
        ("L", gw - 8, gh - 10, 2, 3),
        # Towers (O)
        ("O", 8, cy - 8, 0, 5),
        ("O", gw - 11, cy - 8, 0, 5),
        ("O", 8, cy + 5, 0, 4),
        ("O", gw - 11, cy + 5, 0, 4),
        # Warehouses (S/Z)
        ("S", 12, 8, 0, 2),
        ("Z", gw - 16, 8, 0, 2),
        ("Z", 12, gh - 11, 0, 2),
        ("S", gw - 16, gh - 11, 0, 2),
        # Barracks along the west avenue
        ("I", 6, cy - 12, 1, 2),
        ("I", 6, cy + 6, 1, 2),
        ("I", gw - 8, cy - 12, 1, 2),
        ("I", gw - 8, cy + 6, 1, 2),
    ]

    for shape, x, y, rot, height in landmarks:
        world.place(shape, x, y, rot, height, tint=1.0)

    # Fill remaining lots with pieces that fit — streets stay clear.
    shapes = ("O", "T", "L", "J", "S", "Z", "I")
    for y in range(3, gh - 4):
        for x in range(3, gw - 4):
            if world.kind[y][x] != EMPTY:
                continue
            # Only start a building on a modest empty patch.
            if rng.random() > 0.55:
                continue
            shape = rng.choice(shapes)
            rot = rng.randint(0, 3)
            height = rng.choice((1, 2, 2, 3, 3, 4))
            if shape == "O":
                height = rng.choice((3, 4, 5))
            if shape == "I":
                height = rng.choice((1, 2, 2))
            tint = rng.uniform(0.82, 1.08)
            world.place(shape, x, y, rot, height, tint=tint)

    return world


#------------------------------------------------------------------------------
# Camera
#------------------------------------------------------------------------------

def _world_to_screen(wx, wy, wz, cam_x, cam_y, origin_x, origin_y):
    dx = wx - cam_x
    dy = wy - cam_y
    sx = origin_x + (dx - dy) * (TILE_W * 0.5)
    sy = origin_y + (dx + dy) * (TILE_H * 0.5) - wz * WALL_H
    return sx, sy


def _tour_waypoints(world):
    gw, gh = world.w, world.h
    cx, cy = gw * 0.5, gh * 0.5
    return (
        (cx, cy),
        (8.0, 8.0),
        (gw - 10.0, 10.0),
        (gw - 10.0, gh - 10.0),
        (10.0, gh - 10.0),
        (cx, 10.0),
        (cx, gh - 10.0),
        (cx, cy),
    )


def _camera_at(waypoints, t):
    """Piecewise-linear tour with a short dwell on each landmark."""
    if not waypoints:
        return 0.0, 0.0
    # Precompute segment durations from distance.
    segs = []
    for i, (x0, y0) in enumerate(waypoints):
        x1, y1 = waypoints[(i + 1) % len(waypoints)]
        dist = math.hypot(x1 - x0, y1 - y0)
        segs.append((x0, y0, x1, y1, CAMERA_DWELL + dist / CAMERA_SPEED))
    total = sum(s[4] for s in segs) or 1.0
    u = t % total
    acc = 0.0
    for x0, y0, x1, y1, dur in segs:
        if u <= acc + dur:
            local = u - acc
            if local < CAMERA_DWELL:
                return x0, y0
            travel = dur - CAMERA_DWELL
            k = 0.0 if travel <= 0 else (local - CAMERA_DWELL) / travel
            # Smoothstep so the camera eases between blocks.
            k = k * k * (3.0 - 2.0 * k)
            return x0 + (x1 - x0) * k, y0 + (y1 - y0) * k
        acc += dur
    return waypoints[0]


#------------------------------------------------------------------------------
# Raster
#------------------------------------------------------------------------------

def _fill_triangle(color, depth, zbuf, p0, p1, p2, rgb, z):
    width = len(color[0])
    height = len(color)
    xs = (p0[0], p1[0], p2[0])
    ys = (p0[1], p1[1], p2[1])
    min_x = max(0, int(math.floor(min(xs))))
    max_x = min(width - 1, int(math.ceil(max(xs))))
    min_y = max(0, int(math.floor(min(ys))))
    max_y = min(height - 1, int(math.ceil(max(ys))))
    if min_x > max_x or min_y > max_y:
        return

    ax, ay = p0
    bx, by = p1
    cx, cy = p2
    area = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
    if abs(area) < 0.25:
        return

    for py in range(min_y, max_y + 1):
        cy_s = py + 0.5
        row_c = color[py]
        row_z = zbuf[py]
        for px in range(min_x, max_x + 1):
            cx_s = px + 0.5
            w0 = (bx - cx_s) * (cy - cy_s) - (by - cy_s) * (cx - cx_s)
            w1 = (cx - cx_s) * (ay - cy_s) - (cy - cy_s) * (ax - cx_s)
            w2 = (ax - cx_s) * (by - cy_s) - (ay - cy_s) * (bx - cx_s)
            if area > 0:
                if w0 < 0 or w1 < 0 or w2 < 0:
                    continue
            else:
                if w0 > 0 or w1 > 0 or w2 > 0:
                    continue
            if z < row_z[px]:
                continue
            row_c[px] = rgb
            row_z[px] = z


def _fill_quad(color, depth, zbuf, pts, rgb, z):
    _fill_triangle(color, depth, zbuf, pts[0], pts[1], pts[2], rgb, z)
    _fill_triangle(color, depth, zbuf, pts[0], pts[2], pts[3], rgb, z)


def _stroke_poly(color, depth, zbuf, pts, rgb, z):
    """1-px outline so faces stay readable on a 64×32 panel."""
    width = len(color[0])
    height = len(color)
    n = len(pts)
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        steps = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        for s in range(steps + 1):
            t = s / float(steps)
            px = int(round(x0 + (x1 - x0) * t))
            py = int(round(y0 + (y1 - y0) * t))
            if 0 <= px < width and 0 <= py < height and z >= zbuf[py][px]:
                color[py][px] = rgb
                zbuf[py][px] = z


def _cell_corners(gx, gy, gz, cam_x, cam_y, ox, oy):
    """Four ground corners + four roof corners of one cell column."""
    def P(x, y, z):
        return _world_to_screen(x, y, z, cam_x, cam_y, ox, oy)

    a = P(gx, gy, gz)
    b = P(gx + 1, gy, gz)
    c = P(gx + 1, gy + 1, gz)
    d = P(gx, gy + 1, gz)
    a2 = P(gx, gy, gz + 1)
    b2 = P(gx + 1, gy, gz + 1)
    c2 = P(gx + 1, gy + 1, gz + 1)
    d2 = P(gx, gy + 1, gz + 1)
    return a, b, c, d, a2, b2, c2, d2


def _draw_ground_cell(color, depth, zbuf, gx, gy, kind, cam_x, cam_y, ox, oy):
    a, b, c, d, _, _, _, _ = _cell_corners(gx, gy, 0, cam_x, cam_y, ox, oy)
    if kind == STREET:
        rgb = STREET_RGB
    elif kind == PLAZA:
        rgb = PLAZA_RGB
    else:
        rgb = FLOOR_RGB
        if (gx + gy) & 1:
            rgb = _shade(rgb, 0.88)
    z = (gx + gy) * 10
    _fill_quad(color, depth, zbuf, (a, b, c, d), rgb, z)
    if kind in (STREET, PLAZA) or ((gx + gy) & 1) == 0:
        _stroke_poly(color, depth, zbuf, (a, b, c, d), GRID_RGB, z + 0.5)


def _draw_column(color, depth, zbuf, gx, gy, height, rgb, cam_x, cam_y, ox, oy):
    """One tetromino cell extruded `height` stories.  Three visible faces."""
    top = _shade(rgb, 1.18)
    left = _shade(rgb, 0.62)
    right = _shade(rgb, 0.42)
    edge = _shade(rgb, 0.22)
    # Depth: farther (small x+y) drawn first by caller; z-buffer still wins ties.
    base_z = (gx + gy) * 10 + height
    a, b, c, d, a2, b2, c2, d2 = _cell_corners(
        gx, gy, 0, cam_x, cam_y, ox, oy
    )
    # Roof at full height — recompute top ring only.
    _, _, _, _, a2, b2, c2, d2 = _cell_corners(
        gx, gy, height, cam_x, cam_y, ox, oy
    )

    # Right face (toward +x) and left face (toward +y), then roof.
    _fill_quad(color, depth, zbuf, (b, c, c2, b2), right, base_z)
    _fill_quad(color, depth, zbuf, (d, c, c2, d2), left, base_z + 0.2)
    _fill_quad(color, depth, zbuf, (a2, b2, c2, d2), top, base_z + 0.4)
    _stroke_poly(color, depth, zbuf, (b, c, c2, b2), edge, base_z + 0.5)
    _stroke_poly(color, depth, zbuf, (d, c, c2, d2), edge, base_z + 0.6)
    _stroke_poly(color, depth, zbuf, (a2, b2, c2, d2), edge, base_z + 0.7)


def _visible_range(cam_x, cam_y, grid_w, grid_h, screen_w, screen_h):
    """Cells that can touch the current panel.  Generous pad for tall towers."""
    pad = 12
    # Smaller 4×2 tiles — pull a wider neighborhood so the panel stays full.
    span = 22
    x0 = int(math.floor(cam_x - span))
    y0 = int(math.floor(cam_y - span))
    x1 = int(math.ceil(cam_x + span))
    y1 = int(math.ceil(cam_y + span))
    return (
        _clamp(x0 - pad, 0, grid_w),
        _clamp(y0 - pad, 0, grid_h),
        _clamp(x1 + pad, 0, grid_w),
        _clamp(y1 + pad, 0, grid_h),
    )


def _paint_sky(color, screen_h):
    for y in range(screen_h):
        t = y / float(max(1, screen_h - 1))
        rgb = _mix(SKY_TOP, SKY_HORIZON, t)
        row = color[y]
        for x in range(len(row)):
            row[x] = rgb


def render_world(world, cam_x, cam_y, screen_w, screen_h):
    color = [[SKY_TOP for _ in range(screen_w)] for _ in range(screen_h)]
    zbuf = [[-1e9 for _ in range(screen_w)] for _ in range(screen_h)]
    _paint_sky(color, screen_h)

    ox = screen_w * 0.5
    oy = screen_h * 0.62

    x0, y0, x1, y1 = _visible_range(cam_x, cam_y, world.w, world.h, screen_w, screen_h)

    # Ground first (far to near).
    ground_cells = []
    columns = []
    for gy in range(y0, y1):
        row_kind = world.kind[gy]
        row_h = world.height[gy]
        row_rgb = world.rgb[gy]
        for gx in range(x0, x1):
            kind = row_kind[gx]
            if kind == BLOCK:
                columns.append((gx + gy, gx, gy, row_h[gx], row_rgb[gx]))
            else:
                ground_cells.append((gx + gy, gx, gy, kind))

    ground_cells.sort(key=lambda t: t[0])
    for _, gx, gy, kind in ground_cells:
        _draw_ground_cell(color, None, zbuf, gx, gy, kind, cam_x, cam_y, ox, oy)

    columns.sort(key=lambda t: t[0])
    for _, gx, gy, height, rgb in columns:
        if rgb is None:
            continue
        _draw_column(color, None, zbuf, gx, gy, height, rgb, cam_x, cam_y, ox, oy)

    return color


def _blit(canvas, color, screen_w, screen_h):
    set_pixel = canvas.SetPixel
    for y in range(screen_h):
        row = color[y]
        for x in range(screen_w):
            r, g, b = row[x]
            set_pixel(x, y, r, g, b)


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


def PlayIsoWorld(Duration=10, StopEvent=None):
    global WIDTH, HEIGHT

    if _stop_requested(StopEvent):
        print("[IsoWorld] Play aborted before start (StopEvent)")
        _cleanup()
        return

    WIDTH, HEIGHT = _panel_size()
    world = build_world(WIDTH, HEIGHT)
    waypoints = _tour_waypoints(world)
    canvas = LED.TheMatrix.CreateFrameCanvas()

    try:
        duration_min = float(Duration) if Duration is not None else 0.0
    except (TypeError, ValueError):
        duration_min = 10.0

    blocks = len(world.blocks)
    print(
        "[IsoWorld] panel {}x{}  world {}x{} cells  ({}x{} panels)  "
        "blocks={}  Duration={} min".format(
            WIDTH, HEIGHT, world.w, world.h, PANELS_W, PANELS_H,
            blocks, duration_min,
        )
    )

    start = time.time()

    try:
        while True:
            if _stop_requested(StopEvent):
                print("[IsoWorld] StopEvent received — exiting")
                break

            now = time.time()
            if duration_min > 0 and (now - start) / 60.0 >= duration_min:
                print("[IsoWorld] Duration reached")
                break

            cam_x, cam_y = _camera_at(waypoints, now - start)
            color = render_world(world, cam_x, cam_y, WIDTH, HEIGHT)
            _blit(canvas, color, WIDTH, HEIGHT)
            canvas = LED.TheMatrix.SwapOnVSync(canvas)
    except KeyboardInterrupt:
        print("[IsoWorld] interrupted")
    finally:
        _cleanup()


def LaunchIsoWorld(Duration=10, StopEvent=None):
    if _stop_requested(StopEvent):
        print("[IsoWorld] Launch aborted (StopEvent already set)")
        _cleanup()
        return

    LED.ClearBigLED()
    LED.ClearBuffers()
    PlayIsoWorld(Duration=Duration, StopEvent=StopEvent)


if __name__ == "__main__":
    LED.Initialize()
    try:
        LaunchIsoWorld(Duration=100000, StopEvent=None)
    except KeyboardInterrupt:
        print("Exiting IsoWorld.")
