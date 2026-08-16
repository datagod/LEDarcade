# =====================================================================================
# FRACTAL BLASTER — multi-type fractal explorer for the LED matrix
#
# Title: "FRACTAL BLASTER" zooms in, dives into a letter, then the tour begins.
#
# Tour (repeats until duration ends):
#   1) Pick a random fractal type (Mandelbrot, Julia, Burning Ship, …)
#   2) Smooth zoom-in hops (5 s each) toward coastline spots — 5 levels deep
#   3) Classic color rotation at the deepest view
#   4) Zoom into a bright digital HH:MM clock
#   5) Smooth zoom back out to the starting framing
#
# Launch:
#   LEDsim key 5 / LEDpanel / LEDcommander "launch_fractal" / ?fractal
# =====================================================================================

from __future__ import annotations

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
TARGET_FPS = 20
# Default framing (overridden per fractal type)
INIT_CX = -0.55
INIT_CY = 0.0
INIT_SCALE = 1.35          # half-height of view in complex plane

# New tour timing
ZOOM_LEVELS = 5            # zoom hops before color cycle
ZOOM_IN_SEC = 5.0          # smooth zoom per level
ZOOM_OUT_SEC = 8.0         # return to start framing
COLOR_CYCLE_SEC = 10.0     # full palette rotation at deepest level
COLOR_CYCLE_SPEED = 0.55   # hue shifts per second
ZOOM_IN_FACTOR = 0.22      # scale *= this each zoom-in hop
MAX_ZOOM_DEPTH = 1e-12
LEVEL_PAUSE_SEC = 0.35     # brief settle between hops
# Digital clock reveal at deepest level (before zoom-out)
CLOCK_ZOOM_SEC = 4.0       # longer smooth zoom-in of HH:MM
CLOCK_HOLD_SEC = 2.2       # hold full clock before pull-out
CLOCK_RGB = (255, 255, 255)  # bright white digital face
CLOCK_GLOW = (60, 200, 255)  # soft cyan glow under digits

# Iterations grow as we zoom (detail)
BASE_ITERS = 48
MAX_ITERS = 220

# Fractal kinds available each tour cycle
FRACTAL_KINDS = (
    "mandelbrot",
    "julia",
    "burning_ship",
    "tricorn",
    "multibrot3",
)

# Interesting Julia seeds
JULIA_C_CHOICES = (
    (-0.7, 0.27015),
    (-0.8, 0.156),
    (-0.4, 0.6),
    (0.285, 0.01),
    (-0.835, -0.2321),
    (-0.7269, 0.1889),
    (0.355, 0.355),
    (-0.162, 1.04),
)

# Per-kind default camera (cx, cy, scale)
FRACTAL_START = {
    "mandelbrot": (-0.55, 0.0, 1.35),
    "julia": (0.0, 0.0, 1.55),
    "burning_ship": (-0.45, -0.55, 1.55),
    "tricorn": (-0.25, 0.0, 1.55),
    "multibrot3": (0.0, 0.0, 1.45),
}

# ---- Blaster ship leftovers (unused in new tour; kept for possible re-enable) ----
ENABLE_BLASTER_SHIP = False
BLAST_FRAMES = 130
BLAST_SHIP_SPEED = 0.72
BLAST_TURN = 0.35
BLAST_SHOT_COOLDOWN = 7
BLAST_SHOT_SPEED = 1.55
BLAST_MAX_SHOTS = 6
BLAST_MAX_SPARKS = 96
BLAST_HOLE_R = 1
BLAST_SPARKS_PER_HIT = (5, 11)
BLAST_SHIP_RGB = (240, 245, 255)
BLAST_SHIP_ACCENT = (40, 200, 255)
BLAST_SHOT_RGB = (255, 230, 80)


def _stop(StopEvent):
    try:
        return StopEvent is not None and StopEvent.is_set()
    except Exception:
        return False


def _clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def _smoothstep(t):
    t = _clamp(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _smootherstep(t):
    """Perlin smootherstep — softer ease-in/out for zoom animations."""
    t = _clamp(t, 0.0, 1.0)
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


# ---------------- Color palette ----------------
_PALETTE_STOPS = (
    (0.00, (5, 5, 40)),
    (0.12, (10, 30, 140)),
    (0.28, (20, 140, 200)),
    (0.42, (30, 200, 90)),
    (0.55, (200, 210, 30)),
    (0.70, (255, 100, 20)),
    (0.85, (220, 30, 160)),
    (1.00, (255, 240, 255)),
)


def _palette_color(t, inside=False, shift=0.0):
    """
    Map normalized escape (0..1) to RGB. Interior of the set = near black.
    shift (0..1) rotates the palette for classic color cycling.
    """
    if inside:
        return (0, 0, 0)
    t = _clamp(float(t), 0.0, 1.0)
    # Classic rotation: slide along the gradient, wrap
    t = (t + float(shift)) % 1.0
    stops = _PALETTE_STOPS
    for i in range(len(stops) - 1):
        t0, c0 = stops[i]
        t1, c1 = stops[i + 1]
        if t0 <= t <= t1:
            u = (t - t0) / max(1e-9, t1 - t0)
            return (
                int(c0[0] + (c1[0] - c0[0]) * u),
                int(c0[1] + (c1[1] - c0[1]) * u),
                int(c0[2] + (c1[2] - c0[2]) * u),
            )
    return stops[-1][1]


def _iters_for_scale(scale):
    """More iterations as we zoom in (log depth)."""
    depth = max(0.0, -math.log10(max(scale, 1e-16)))
    it = int(BASE_ITERS + depth * 28)
    return _clamp(it, BASE_ITERS, MAX_ITERS)


def _smooth_escape(n, zx, zy, max_iter):
    """Smooth iteration count → 0..1 exterior value."""
    r2 = zx * zx + zy * zy
    if r2 <= 0:
        return _clamp((n + 1) / float(max_iter), 0.0, 1.0)
    log_zn = math.log(r2) * 0.5
    nu = math.log(log_zn / math.log(2.0)) / math.log(2.0) if log_zn > 0 else 0.0
    smooth = (n + 1 - nu) / float(max_iter)
    return _clamp(smooth, 0.0, 1.0)


# ---------------- Fractal iterators ----------------
def fractal_escape(kind, cx, cy, max_iter, julia_c=None):
    """
    Escape-time for various fractal families.
    Returns (escaped, value) with value 0..1 exterior, 0 interior.
    """
    kind = (kind or "mandelbrot").lower()
    if kind == "julia":
        jx, jy = julia_c if julia_c else (-0.7, 0.27015)
        zx, zy = cx, cy
        for n in range(max_iter):
            zx2 = zx * zx
            zy2 = zy * zy
            if zx2 + zy2 > 4.0:
                return True, _smooth_escape(n, zx, zy, max_iter)
            zy = 2.0 * zx * zy + jy
            zx = zx2 - zy2 + jx
        return False, 0.0

    if kind == "burning_ship":
        zx = zy = 0.0
        for n in range(max_iter):
            # z = (|Re z| + i |Im z|)^2 + c
            ax = abs(zx)
            ay = abs(zy)
            zx2 = ax * ax
            zy2 = ay * ay
            if zx2 + zy2 > 4.0:
                return True, _smooth_escape(n, ax, ay, max_iter)
            zy = 2.0 * ax * ay + cy
            zx = zx2 - zy2 + cx
        return False, 0.0

    if kind == "tricorn":
        # Mandelbar: z → conj(z)^2 + c
        zx = zy = 0.0
        for n in range(max_iter):
            zx2 = zx * zx
            zy2 = zy * zy
            if zx2 + zy2 > 4.0:
                return True, _smooth_escape(n, zx, zy, max_iter)
            # conj(z)^2 = (zx - i zy)^2 = zx^2 - zy^2 - 2 i zx zy
            zy = -2.0 * zx * zy + cy
            zx = zx2 - zy2 + cx
        return False, 0.0

    if kind == "multibrot3":
        # z → z^3 + c
        zx = zy = 0.0
        for n in range(max_iter):
            r2 = zx * zx + zy * zy
            if r2 > 4.0:
                return True, _smooth_escape(n, zx, zy, max_iter)
            # (zx + i zy)^3 = zx^3 - 3 zx zy^2 + i (3 zx^2 zy - zy^3)
            zx2 = zx * zx
            zy2 = zy * zy
            nx = zx * (zx2 - 3.0 * zy2) + cx
            ny = zy * (3.0 * zx2 - zy2) + cy
            zx, zy = nx, ny
        return False, 0.0

    # Default: Mandelbrot z → z^2 + c
    zx = zy = 0.0
    for n in range(max_iter):
        zx2 = zx * zx
        zy2 = zy * zy
        if zx2 + zy2 > 4.0:
            return True, _smooth_escape(n, zx, zy, max_iter)
        zy = 2.0 * zx * zy + cy
        zx = zx2 - zy2 + cx
    return False, 0.0


def render_fractal(
    width, height, center_x, center_y, scale, max_iter,
    kind="mandelbrot", julia_c=None, color_shift=0.0,
):
    """
    Render fractal to pixel rows + escape map.
    scale = half-height in the complex plane (aspect-correct width).
    """
    aspect = width / float(max(1, height))
    half_h = scale
    half_w = scale * aspect
    x0 = center_x - half_w
    y0 = center_y - half_h
    dx = (2.0 * half_w) / float(max(1, width))
    dy = (2.0 * half_h) / float(max(1, height))

    pixels = [[(0, 0, 0) for _ in range(width)] for _ in range(height)]
    escape = [[0.0 for _ in range(width)] for _ in range(height)]

    for py in range(height):
        icy = y0 + (py + 0.5) * dy
        row_pix = pixels[py]
        row_esc = escape[py]
        for px in range(width):
            icx = x0 + (px + 0.5) * dx
            escaped, val = fractal_escape(kind, icx, icy, max_iter, julia_c=julia_c)
            if escaped:
                row_esc[px] = val
                row_pix[px] = _palette_color(val, inside=False, shift=color_shift)
            else:
                row_esc[px] = 0.0
                row_pix[px] = _palette_color(0.0, inside=True, shift=color_shift)
    return pixels, escape


def render_mandelbrot(width, height, center_x, center_y, scale, max_iter, color_shift=0.0):
    """Back-compat wrapper (title intro, etc.)."""
    return render_fractal(
        width, height, center_x, center_y, scale, max_iter,
        kind="mandelbrot", color_shift=color_shift,
    )


def pick_fractal_kind():
    """Random fractal family + optional Julia parameter."""
    kind = random.choice(FRACTAL_KINDS)
    julia_c = None
    if kind == "julia":
        julia_c = random.choice(JULIA_C_CHOICES)
    start = FRACTAL_START.get(kind, (INIT_CX, INIT_CY, INIT_SCALE))
    return kind, julia_c, start


def blit_pixels(canvas, pixels, width, height):
    set_px = canvas.SetPixel
    for y in range(height):
        row = pixels[y]
        for x in range(width):
            r, g, b = row[x]
            set_px(x, y, r, g, b)


# ---------------- Blaster ship (pixel destruction + sparks) ----------------
def _pixel_brightness(rgb):
    r, g, b = rgb
    return r * 0.30 + g * 0.59 + b * 0.11


def _blit_with_holes(canvas, pixels, width, height, holes):
    """Draw fractal frame with destroyed pixels punched out (near-black)."""
    set_px = canvas.SetPixel
    for y in range(height):
        row = pixels[y]
        for x in range(width):
            if (x, y) in holes:
                set_px(x, y, 0, 0, 0)
            else:
                r, g, b = row[x]
                set_px(x, y, r, g, b)


class FractalBlasterShip(object):
    """
    Tiny combat craft that flies over a frozen Mandelbrot frame, shoots
    colorful pixels into spark showers, and leaves lasting holes.
    Camera stays fixed during the blast phase.
    """

    def __init__(self, width, height):
        self.w = int(width)
        self.h = int(height)
        self.x = self.w * 0.2
        self.y = self.h * 0.5
        self.vx = 0.6
        self.vy = 0.0
        self.facing = 1        # -1 left / +1 right (sprite mirror)
        self.cooldown = 0
        self.shots = []        # {x,y,vx,vy,life}
        self.sparks = []       # {x,y,vx,vy,life,max_life,r,g,b}
        self.holes = set()     # destroyed (x,y)
        self.target = None     # (tx, ty) pixel to attack
        self.retarget_t = 0
        self.alive = True

    def reset(self):
        self.x = random.uniform(2.0, max(3.0, self.w * 0.35))
        self.y = random.uniform(2.0, max(3.0, self.h - 3.0))
        ang = random.uniform(-0.6, 0.6)
        self.vx = math.cos(ang) * BLAST_SHIP_SPEED
        self.vy = math.sin(ang) * BLAST_SHIP_SPEED
        self.facing = 1 if self.vx >= 0 else -1
        self.cooldown = 4
        self.shots = []
        self.sparks = []
        self.holes = set()
        self.target = None
        self.retarget_t = 0
        self.alive = True

    def _pick_target(self, pixels):
        """Prefer bright, not-yet-destroyed pixels (colorful coastline candy)."""
        candidates = []
        # Sparse scan — cheap on 64×32
        step_x = 2 if self.w > 40 else 1
        step_y = 2 if self.h > 24 else 1
        for py in range(1, self.h - 1, step_y):
            row = pixels[py]
            for px in range(1, self.w - 1, step_x):
                if (px, py) in self.holes:
                    continue
                bri = _pixel_brightness(row[px])
                if bri < 28:
                    continue
                # Prefer mid-screen targets slightly + distance from ship
                dx = px - self.x
                dy = py - self.y
                dist = math.hypot(dx, dy) + 0.01
                # Not too close (already chewing) and not edge-glued
                if dist < 2.5:
                    continue
                score = bri * (1.0 + 0.15 * random.random()) / (0.6 + dist * 0.08)
                candidates.append((score, px, py))
        if not candidates:
            # Fallback: any non-hole pixel with some color
            for _ in range(40):
                px = random.randint(1, self.w - 2)
                py = random.randint(1, self.h - 2)
                if (px, py) not in self.holes and _pixel_brightness(pixels[py][px]) > 12:
                    return (px, py)
            return (
                random.randint(2, self.w - 3),
                random.randint(2, self.h - 3),
            )
        candidates.sort(key=lambda t: -t[0])
        top = candidates[: max(4, min(12, len(candidates)))]
        _s, px, py = random.choice(top)
        return (px, py)

    def _destroy_at(self, px, py, pixels):
        """Punch a hole and emit colored sparks from that neighborhood."""
        px = int(px)
        py = int(py)
        r = BLAST_HOLE_R
        hit_colors = []
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if dx * dx + dy * dy > r * r + 0.5:
                    continue
                x, y = px + dx, py + dy
                if not (0 <= x < self.w and 0 <= y < self.h):
                    continue
                if (x, y) in self.holes:
                    continue
                self.holes.add((x, y))
                rgb = pixels[y][x]
                if _pixel_brightness(rgb) > 8:
                    hit_colors.append(rgb)
        if not hit_colors:
            hit_colors = [BLAST_SHOT_RGB]
        n_sparks = random.randint(*BLAST_SPARKS_PER_HIT)
        for _ in range(n_sparks):
            if len(self.sparks) >= BLAST_MAX_SPARKS:
                break
            cr, cg, cb = random.choice(hit_colors)
            # Boost spark brightness a bit so they read on LEDs
            cr = min(255, int(cr * 1.25) + 20)
            cg = min(255, int(cg * 1.15) + 15)
            cb = min(255, int(cb * 1.20) + 20)
            ang = random.uniform(0, math.pi * 2)
            spd = random.uniform(0.35, 1.65)
            life = random.uniform(8.0, 18.0)
            self.sparks.append({
                "x": float(px) + random.uniform(-0.3, 0.3),
                "y": float(py) + random.uniform(-0.3, 0.3),
                "vx": math.cos(ang) * spd,
                "vy": math.sin(ang) * spd - random.uniform(0.05, 0.35),
                "life": life,
                "max_life": life,
                "r": cr, "g": cg, "b": cb,
            })

    def update(self, pixels):
        """One combat frame: steer, shoot, move shots/sparks, punch holes."""
        if not self.alive:
            return

        self.retarget_t -= 1
        if (
            self.target is None
            or self.retarget_t <= 0
            or (self.target in self.holes)
        ):
            self.target = self._pick_target(pixels)
            self.retarget_t = random.randint(12, 28)

        tx, ty = self.target
        # Steer toward target with a little wander so flight isn't laser-straight
        want_x = tx - self.x + random.uniform(-0.4, 0.4)
        want_y = ty - self.y + random.uniform(-0.4, 0.4)
        dist = math.hypot(want_x, want_y) + 1e-6
        speed = BLAST_SHIP_SPEED * (0.75 + 0.35 * random.random())
        # Circle a bit when close so we rake fire across a region
        if dist < 5.0:
            # tangential drift
            want_x += -want_y * 0.55
            want_y += (tx - self.x) * 0.25
            dist = math.hypot(want_x, want_y) + 1e-6
        t_vx = (want_x / dist) * speed
        t_vy = (want_y / dist) * speed
        self.vx = self.vx * (1.0 - BLAST_TURN) + t_vx * BLAST_TURN
        self.vy = self.vy * (1.0 - BLAST_TURN) + t_vy * BLAST_TURN
        # Normalize to roughly constant speed
        sp = math.hypot(self.vx, self.vy) + 1e-6
        self.vx = (self.vx / sp) * BLAST_SHIP_SPEED
        self.vy = (self.vy / sp) * BLAST_SHIP_SPEED
        self.x += self.vx
        self.y += self.vy
        # Bounce off panel edges
        if self.x < 1.0:
            self.x = 1.0
            self.vx = abs(self.vx)
        elif self.x > self.w - 2.0:
            self.x = self.w - 2.0
            self.vx = -abs(self.vx)
        if self.y < 1.0:
            self.y = 1.0
            self.vy = abs(self.vy)
        elif self.y > self.h - 2.0:
            self.y = self.h - 2.0
            self.vy = -abs(self.vy)
        if abs(self.vx) > 0.05:
            self.facing = 1 if self.vx >= 0 else -1

        # Fire toward target when lined up / close enough
        self.cooldown -= 1
        if (
            self.cooldown <= 0
            and len(self.shots) < BLAST_MAX_SHOTS
            and dist < max(self.w, self.h) * 0.85
        ):
            aim_x = tx - self.x
            aim_y = ty - self.y
            ad = math.hypot(aim_x, aim_y) + 1e-6
            # Nose offset
            nose = 1.4
            self.shots.append({
                "x": self.x + (aim_x / ad) * nose,
                "y": self.y + (aim_y / ad) * nose,
                "vx": (aim_x / ad) * BLAST_SHOT_SPEED,
                "vy": (aim_y / ad) * BLAST_SHOT_SPEED,
                "life": 40,
            })
            self.cooldown = BLAST_SHOT_COOLDOWN + random.randint(0, 3)

        # Advance shots; destroy on impact with a live pixel
        alive_shots = []
        for s in self.shots:
            s["x"] += s["vx"]
            s["y"] += s["vy"]
            s["life"] -= 1
            ix, iy = int(round(s["x"])), int(round(s["y"]))
            if s["life"] <= 0 or not (0 <= ix < self.w and 0 <= iy < self.h):
                continue
            # Hit if this cell (or neighbor) still has fractal color
            hit = False
            for dy in (0, -1, 1):
                for dx in (0, -1, 1):
                    hx, hy = ix + dx, iy + dy
                    if not (0 <= hx < self.w and 0 <= hy < self.h):
                        continue
                    if (hx, hy) in self.holes:
                        continue
                    if _pixel_brightness(pixels[hy][hx]) >= 14:
                        self._destroy_at(hx, hy, pixels)
                        hit = True
                        break
                if hit:
                    break
            if not hit:
                alive_shots.append(s)
        self.shots = alive_shots

        # Occasional ram-blast if we fly through dense color
        sx, sy = int(round(self.x)), int(round(self.y))
        if 0 <= sx < self.w and 0 <= sy < self.h:
            if (sx, sy) not in self.holes and _pixel_brightness(pixels[sy][sx]) > 40:
                if random.random() < 0.18:
                    self._destroy_at(sx, sy, pixels)

        # Sparks
        alive_sparks = []
        for p in self.sparks:
            p["vy"] += 0.04          # slight gravity
            p["vx"] *= 0.98
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["life"] -= 1.0
            if p["life"] <= 0:
                continue
            if not (-1 <= p["x"] < self.w + 1 and -1 <= p["y"] < self.h + 1):
                continue
            alive_sparks.append(p)
        self.sparks = alive_sparks

    def draw(self, canvas, pixels):
        """Blit fractal with holes, then sparks, shots, and ship on top."""
        _blit_with_holes(canvas, pixels, self.w, self.h, self.holes)
        set_px = canvas.SetPixel

        # Sparks (fade with life)
        for p in self.sparks:
            ix, iy = int(round(p["x"])), int(round(p["y"]))
            if not (0 <= ix < self.w and 0 <= iy < self.h):
                continue
            u = _clamp(p["life"] / max(1.0, p["max_life"]), 0.0, 1.0)
            # Hot core early, dim embers late
            br = 0.35 + 0.65 * u
            set_px(
                ix, iy,
                int(p["r"] * br),
                int(p["g"] * br),
                int(p["b"] * br),
            )
            # Tiny trail pixel
            if u > 0.45:
                tx = int(round(p["x"] - p["vx"]))
                ty = int(round(p["y"] - p["vy"]))
                if 0 <= tx < self.w and 0 <= ty < self.h:
                    set_px(
                        tx, ty,
                        int(p["r"] * br * 0.45),
                        int(p["g"] * br * 0.45),
                        int(p["b"] * br * 0.45),
                    )

        # Shots
        sr, sg, sb = BLAST_SHOT_RGB
        for s in self.shots:
            ix, iy = int(round(s["x"])), int(round(s["y"]))
            if 0 <= ix < self.w and 0 <= iy < self.h:
                set_px(ix, iy, sr, sg, sb)
                # streak
                bx = int(round(s["x"] - s["vx"] * 0.6))
                by = int(round(s["y"] - s["vy"] * 0.6))
                if 0 <= bx < self.w and 0 <= by < self.h:
                    set_px(bx, by, sr // 2, sg // 2, sb // 3)

        # Ship sprite — tiny arrow/fighter, mirrored by facing
        sx = int(round(self.x))
        sy = int(round(self.y))
        f = self.facing
        body = BLAST_SHIP_RGB
        accent = BLAST_SHIP_ACCENT
        # pixels relative to center: nose points along +x when facing right
        parts = (
            (0, 0, body),           # core
            (1 * f, 0, accent),     # nose
            (2 * f, 0, accent),     # nose tip
            (-1 * f, 0, body),      # tail
            (0, -1, body),          # upper wing
            (0, 1, body),           # lower wing
            (-1 * f, -1, accent),   # wing tip
            (-1 * f, 1, accent),
        )
        for dx, dy, rgb in parts:
            px, py = sx + dx, sy + dy
            if 0 <= px < self.w and 0 <= py < self.h:
                set_px(px, py, rgb[0], rgb[1], rgb[2])


# ---------------- Zoom target selection (coastline only) ----------------
# Known Mandelbrot *coastal* landmarks (set boundary / fjords / bulbs)
_COASTAL_LANDMARKS = (
    (-0.75, 0.1),              # main cardioid / period-2 bulb neck
    (-0.16, 1.0405),           # top of northern mini-set fjord
    (-0.16, -1.0405),          # southern mirror
    (-1.25, 0.02),             # seahorse valley approach
    (-0.7269, 0.1889),         # spiral coastline
    (-0.7453, 0.1127),         # classic seahorse valley
    (-0.74529, 0.11307),
    (-0.8, 0.156),
    (-0.235125, 0.827215),     # antenna tip region
    (-0.761574, -0.0847596),
    (0.28, 0.008),             # elephant valley (east coast)
    (0.37, 0.16),
    (-1.7687788, 0.0017389),   # mini Mandelbrot coastline
    (-0.1011, 0.9563),
    (-0.75, 0.11),
    (-0.748, 0.1),
)


def _is_interior(escape, px, py):
    """Interior of the set: did not escape (stored as 0.0)."""
    return escape[py][px] <= 1e-12


def _coast_score(escape, px, py, width, height):
    """
    Score how 'coastal' a pixel is.

    True coastline = sits on the boundary between land (interior) and sea
    (exterior). We count 4/8-neighbors that differ in inside/outside status
    and boost mid-range exterior escape (detail-rich water next to shore).
    Returns 0 if not on a land/sea edge.
    """
    inside = _is_interior(escape, px, py)
    e = escape[py][px]
    land_n = 0
    sea_n = 0
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            nx, ny = px + dx, py + dy
            if not (0 <= nx < width and 0 <= ny < height):
                continue
            if _is_interior(escape, nx, ny):
                land_n += 1
            else:
                sea_n += 1
    # Must touch both land and sea to count as coast
    if land_n == 0 or sea_n == 0:
        return 0.0
    # Stronger score for more mixed neighborhood (ragged fjords)
    mix = min(land_n, sea_n) / 4.0
    # Exterior shore pixels with mid escape = colorful coastline detail
    if not inside:
        # Prefer not deep open ocean (e near 0 after smooth) nor white blowout
        detail = 1.0 - abs(e - 0.35) / 0.55
        detail = max(0.15, detail)
    else:
        # Interior edge of the set — still coast, slightly lower preference
        detail = 0.55
    return (0.55 + 0.45 * mix) * detail


def pick_zoom_target(center_x, center_y, scale, width, height, escape, prefer_edge=True):
    """
    Choose a complex-plane point on the Mandelbrot *coastline* to zoom toward.

    Scans the current frame for land/sea boundary pixels only — never deep
    interior or open exterior. Falls back to known coastal landmarks.
    """
    aspect = width / float(max(1, height))
    half_h = scale
    half_w = scale * aspect
    x0 = center_x - half_w
    y0 = center_y - half_h
    dx = (2.0 * half_w) / float(max(1, width))
    dy = (2.0 * half_h) / float(max(1, height))

    coast = []
    if prefer_edge and escape is not None:
        # Margin: avoid screen-edge artifacts
        for py in range(1, height - 1):
            for px in range(1, width - 1):
                score = _coast_score(escape, px, py, width, height)
                if score > 0.0:
                    coast.append((px, py, score))

        if coast:
            # Keep the best coastal candidates, weighted-random pick
            coast.sort(key=lambda t: -t[2])
            top_n = max(6, min(len(coast), max(6, len(coast) // 4)))
            pool = coast[:top_n]
            # Weight by score^2 so the ragged/interesting shore wins more often
            weights = [s * s for _px, _py, s in pool]
            total_w = sum(weights) or 1.0
            r = random.random() * total_w
            acc = 0.0
            px, py, _s = pool[-1]
            for i, (cpx, cpy, s) in enumerate(pool):
                acc += weights[i]
                if r <= acc:
                    px, py = cpx, cpy
                    break
            # Small jitter so we don't always hit pixel centers
            jx = random.uniform(-0.4, 0.4)
            jy = random.uniform(-0.4, 0.4)
            tx = x0 + (px + 0.5 + jx) * dx
            ty = y0 + (py + 0.5 + jy) * dy
            return tx, ty

    # No coast found in this frame (rare) — use a known coastal landmark
    # that still lies near the current view when possible
    best = None
    best_d = 1e99
    for lx, ly in _COASTAL_LANDMARKS:
        # Prefer landmarks inside / near the current view
        if abs(lx - center_x) <= half_w * 1.2 and abs(ly - center_y) <= half_h * 1.2:
            d = (lx - center_x) ** 2 + (ly - center_y) ** 2
            if d < best_d:
                best_d = d
                best = (lx, ly)
    if best is not None:
        return best
    return random.choice(_COASTAL_LANDMARKS)


# ---------------- Tour helpers ----------------
def _lerp_view(z_from, z_to, u):
    """Smoothstep view lerp; log-lerp scale for constant perceived zoom speed."""
    u = _smoothstep(u)
    cx = z_from[0] + (z_to[0] - z_from[0]) * u
    cy = z_from[1] + (z_to[1] - z_from[1]) * u
    s0, s1 = z_from[2], z_to[2]
    if s0 > 0 and s1 > 0:
        scale = math.exp(math.log(s0) + (math.log(s1) - math.log(s0)) * u)
    else:
        scale = s0 + (s1 - s0) * u
    return cx, cy, scale


def _begin_zoom_in(cx, cy, scale, width, height, escape):
    tx, ty = pick_zoom_target(cx, cy, scale, width, height, escape)
    target_scale = max(MAX_ZOOM_DEPTH, scale * ZOOM_IN_FACTOR)
    return (cx, cy, scale), (tx, ty, target_scale)


# ---------------- Digital clock overlay (depth reveal) ----------------
# Compact 3×5 digits + colon for HH:MM (fits 64×32 when scaled)
_DIGIT_3X5 = {
    "0": ("111", "101", "101", "101", "111"),
    "1": ("010", "110", "010", "010", "111"),
    "2": ("111", "001", "111", "100", "111"),
    "3": ("111", "001", "111", "001", "111"),
    "4": ("101", "101", "111", "001", "001"),
    "5": ("111", "100", "111", "001", "111"),
    "6": ("111", "100", "111", "101", "111"),
    "7": ("111", "001", "001", "001", "001"),
    "8": ("111", "101", "111", "101", "111"),
    "9": ("111", "101", "111", "001", "111"),
    ":": ("0", "1", "0", "1", "0"),
}


def _clock_text_now():
    return time.strftime("%H:%M")


def _clock_glyph_size(ch):
    rows = _DIGIT_3X5.get(ch, _DIGIT_3X5["0"])
    return len(rows[0]), len(rows)


def _clock_layout_size(text):
    """Native (unscaled) width/height of the digit string with 1px gaps."""
    tw, th = 0, 5
    for i, ch in enumerate(text):
        w, h = _clock_glyph_size(ch)
        th = max(th, h)
        tw += w
        if i < len(text) - 1:
            tw += 1  # gap
    return tw, th


def _clock_lit_cells(text):
    """List of (ux0, uy0, ux1, uy1) unit rectangles for lit digit cells."""
    cells = []
    x = 0.0
    for i, ch in enumerate(text):
        rows = _DIGIT_3X5.get(ch, _DIGIT_3X5["0"])
        gw = len(rows[0])
        for ry, row in enumerate(rows):
            for rx, bit in enumerate(row):
                if bit == "1":
                    cells.append((x + rx, float(ry), x + rx + 1.0, float(ry + 1)))
        x += gw + (1 if i < len(text) - 1 else 0)
    return cells


def _draw_digital_clock(canvas, width, height, scale, rgb=None, glow=None):
    """
    Draw HH:MM centered with *continuous* scale (smooth zoom, not integer steps).
    Samples each LED with soft coverage for anti-aliased growth.
    """
    text = _clock_text_now()
    rgb = rgb or CLOCK_RGB
    glow = glow or CLOCK_GLOW
    nw, nh = _clock_layout_size(text)
    if nw < 1 or nh < 1:
        return
    # Max unit→pixel scale that fits with margin
    max_sc = min(
        (width - 4) / float(nw),
        (height - 4) / float(nh),
    )
    # Continuous scale — no int() snap (was the choppy zoom)
    sc = max(0.35, float(scale) * max_sc)
    block_w = nw * sc
    block_h = nh * sc
    ox = (width - block_w) * 0.5
    oy = (height - block_h) * 0.5

    cells = _clock_lit_cells(text)
    if not cells:
        return

    # Bounds in panel space (+ soft margin for glow)
    soft_u = 0.65  # soft edge in unit cells
    pad = sc * (soft_u + 0.35)
    x_lo = max(0, int(math.floor(ox - pad)))
    y_lo = max(0, int(math.floor(oy - pad)))
    x_hi = min(width, int(math.ceil(ox + block_w + pad)))
    y_hi = min(height, int(math.ceil(oy + block_h + pad)))

    set_px = canvas.SetPixel
    inv_sc = 1.0 / sc

    for py in range(y_lo, y_hi):
        # pixel center → unit coords
        uy = (py + 0.5 - oy) * inv_sc
        for px in range(x_lo, x_hi):
            ux = (px + 0.5 - ox) * inv_sc
            # Max coverage over any lit cell (core + soft)
            core = 0.0
            halo = 0.0
            for cx0, cy0, cx1, cy1 in cells:
                # Expand glow rect slightly
                g0x, g0y = cx0 - 0.35, cy0 - 0.35
                g1x, g1y = cx1 + 0.35, cy1 + 0.35
                # Distance-based soft cover for core cell
                # pixel as unit-square mapped: (ux±0.5/sc)
                half = 0.5 * inv_sc
                # Treat LED as point sample with soft radius in unit space
                # Core
                dx = 0.0
                if ux < cx0:
                    dx = cx0 - ux
                elif ux > cx1:
                    dx = ux - cx1
                dy = 0.0
                if uy < cy0:
                    dy = cy0 - uy
                elif uy > cy1:
                    dy = uy - cy1
                if dx <= 0.0 and dy <= 0.0:
                    core = 1.0
                else:
                    d = math.hypot(dx, dy) if (dx > 0 and dy > 0) else (dx + dy)
                    # Soft AA rim ~0.4 unit cells (smooth as sc grows)
                    rim = 0.45
                    if d < rim:
                        core = max(core, 1.0 - d / rim)
                # Halo
                hdx = 0.0
                if ux < g0x:
                    hdx = g0x - ux
                elif ux > g1x:
                    hdx = ux - g1x
                hdy = 0.0
                if uy < g0y:
                    hdy = g0y - uy
                elif uy > g1y:
                    hdy = uy - g1y
                if hdx <= 0.0 and hdy <= 0.0:
                    halo = max(halo, 0.55)
                else:
                    hd = math.hypot(hdx, hdy) if (hdx > 0 and hdy > 0) else (hdx + hdy)
                    hr = 0.55
                    if hd < hr:
                        halo = max(halo, 0.55 * (1.0 - hd / hr))
                if core >= 0.99:
                    break

            if core < 0.02 and halo < 0.02:
                continue
            # Composite: glow under bright core
            cr = int(glow[0] * halo * (1.0 - core) + rgb[0] * core)
            cg = int(glow[1] * halo * (1.0 - core) + rgb[1] * core)
            cb = int(glow[2] * halo * (1.0 - core) + rgb[2] * core)
            cr = min(255, cr)
            cg = min(255, cg)
            cb = min(255, cb)
            if cr + cg + cb > 8:
                set_px(px, py, cr, cg, cb)


# ---------------- Main loop ----------------
def PlayFractal(Duration=10, StopEvent=None, start_cam=None):
    """
    Multi-type fractal tour (Duration in minutes):

      pick fractal → zoom-in ×5 → color cycle → digital clock zoom-in →
      zoom out to start → repeat

    start_cam: optional {cx, cy, scale} from the title intro (first Mandelbrot cycle).
    """
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

    tick = pygame.time.Clock() if HAS_PYGAME else None
    zoom_in_frames = max(1, int(round(ZOOM_IN_SEC * TARGET_FPS)))
    zoom_out_frames = max(1, int(round(ZOOM_OUT_SEC * TARGET_FPS)))
    color_frames = max(1, int(round(COLOR_CYCLE_SEC * TARGET_FPS)))
    pause_frames = max(1, int(round(LEVEL_PAUSE_SEC * TARGET_FPS)))
    clock_zoom_frames = max(1, int(round(CLOCK_ZOOM_SEC * TARGET_FPS)))
    clock_hold_frames = max(1, int(round(CLOCK_HOLD_SEC * TARGET_FPS)))

    kind = "mandelbrot"
    julia_c = None
    start_view = (INIT_CX, INIT_CY, INIT_SCALE)
    cx, cy, scale = start_view
    color_shift = 0.0
    last_escape = None
    level = 0
    cycle = 0
    clock_scale = 0.0          # 0..1 digital clock zoom amount
    fractal_dim = 1.0          # dim fractal under the clock

    phase = "new_cycle"
    phase_t = 0
    phase_len = 1
    z_from = start_view
    z_to = start_view

    def _start_new_cycle():
        nonlocal kind, julia_c, start_view, cx, cy, scale, color_shift
        nonlocal last_escape, level, cycle, phase, phase_t, phase_len, z_from, z_to
        nonlocal clock_scale, fractal_dim
        cycle += 1
        kind, julia_c, start_view = pick_fractal_kind()
        if (
            cycle == 1
            and start_cam
            and isinstance(start_cam, dict)
            and kind == "mandelbrot"
        ):
            cx = float(start_cam.get("cx", start_view[0]))
            cy = float(start_cam.get("cy", start_view[1]))
            scale = float(start_cam.get("scale", start_view[2]))
            start_view = (cx, cy, scale)
        else:
            cx, cy, scale = start_view
        color_shift = 0.0
        clock_scale = 0.0
        fractal_dim = 1.0
        level = 0
        last_escape = None
        max_iter = _iters_for_scale(scale)
        _pix, last_escape = render_fractal(
            width, height, cx, cy, scale, max_iter,
            kind=kind, julia_c=julia_c, color_shift=0.0,
        )
        z_from, z_to = _begin_zoom_in(cx, cy, scale, width, height, last_escape)
        phase = "zoom_in"
        phase_t = 0
        phase_len = zoom_in_frames
        level = 1
        jc = f"  c={julia_c}" if julia_c else ""
        print(
            f"[Fractal] Cycle #{cycle}: {kind}{jc}  "
            f"start=({start_view[0]:.4f},{start_view[1]:.4f}) "
            f"scale={start_view[2]:.3f}  "
            f"→ zoom-in level 1/{ZOOM_LEVELS}"
        )

    def _begin_next_zoom_in():
        nonlocal phase, phase_t, phase_len, z_from, z_to, level
        z_from, z_to = _begin_zoom_in(cx, cy, scale, width, height, last_escape)
        phase = "zoom_in"
        phase_t = 0
        phase_len = zoom_in_frames
        level += 1
        print(
            f"[Fractal] Zoom-in level {level}/{ZOOM_LEVELS}  "
            f"→ ({z_to[0]:.6f}, {z_to[1]:.6f})  "
            f"scale {z_from[2]:.3e} → {z_to[2]:.3e}"
        )

    def _begin_color_cycle():
        nonlocal phase, phase_t, phase_len, color_shift
        phase = "color_cycle"
        phase_t = 0
        phase_len = color_frames
        color_shift = 0.0
        print(
            f"[Fractal] Color rotation @ depth scale={scale:.3e}  "
            f"({COLOR_CYCLE_SEC:.1f}s)"
        )

    def _begin_clock_zoom():
        nonlocal phase, phase_t, phase_len, clock_scale, fractal_dim
        phase = "clock_zoom"
        phase_t = 0
        phase_len = clock_zoom_frames
        clock_scale = 0.12
        fractal_dim = 1.0
        print(
            f"[Fractal] Digital clock zoom-in  ({CLOCK_ZOOM_SEC:.1f}s)  "
            f"time={_clock_text_now()}"
        )

    def _begin_clock_hold():
        nonlocal phase, phase_t, phase_len, clock_scale, fractal_dim
        phase = "clock_hold"
        phase_t = 0
        phase_len = clock_hold_frames
        clock_scale = 1.0
        fractal_dim = 0.22
        print(f"[Fractal] Clock hold  {_clock_text_now()}  ({CLOCK_HOLD_SEC:.1f}s)")

    def _begin_zoom_out():
        nonlocal phase, phase_t, phase_len, z_from, z_to, color_shift
        nonlocal clock_scale, fractal_dim
        z_from = (cx, cy, scale)
        z_to = start_view
        phase = "zoom_out"
        phase_t = 0
        phase_len = zoom_out_frames
        color_shift = 0.0
        clock_scale = 0.0
        fractal_dim = 1.0
        print(
            f"[Fractal] Zoom-out → start  "
            f"scale {z_from[2]:.3e} → {z_to[2]:.3e}  ({ZOOM_OUT_SEC:.1f}s)"
        )

    _start_new_cycle()

    print(
        f"[Fractal] Multi-type tour  {width}x{height}  "
        f"levels={ZOOM_LEVELS}  zoom={ZOOM_IN_SEC}s  "
        f"color={COLOR_CYCLE_SEC}s  clock={CLOCK_ZOOM_SEC}+{CLOCK_HOLD_SEC}s  "
        f"out={ZOOM_OUT_SEC}s  duration={run_min} min  fps~{TARGET_FPS}"
    )

    try:
        while True:
            if _stop(StopEvent):
                print("[Fractal] StopEvent — exit")
                break
            if time.time() - start > run_min * 60.0:
                print("[Fractal] Duration reached — exit")
                break

            max_iter = _iters_for_scale(scale)
            show_clock = False

            if phase == "zoom_in":
                phase_t += 1
                u = phase_t / float(max(1, phase_len))
                cx, cy, scale = _lerp_view(z_from, z_to, u)
                if phase_t >= phase_len:
                    cx, cy, scale = z_to[0], z_to[1], z_to[2]
                    phase = "pause"
                    phase_t = 0
                    phase_len = pause_frames

            elif phase == "pause":
                phase_t += 1
                if phase_t >= phase_len:
                    if level < ZOOM_LEVELS:
                        _begin_next_zoom_in()
                    else:
                        _begin_color_cycle()

            elif phase == "color_cycle":
                phase_t += 1
                color_shift = (
                    (phase_t / float(TARGET_FPS)) * COLOR_CYCLE_SPEED
                ) % 1.0
                if phase_t >= phase_len:
                    _begin_clock_zoom()

            elif phase == "clock_zoom":
                phase_t += 1
                # Smootherstep for gentler ease-in/out (no linear jumps)
                u = _smootherstep(phase_t / float(max(1, phase_len)))
                # Clock grows continuously 0.08 → 1.0; fractal dims underneath
                clock_scale = 0.08 + 0.92 * u
                fractal_dim = 1.0 - 0.82 * u
                show_clock = True
                if phase_t >= phase_len:
                    _begin_clock_hold()

            elif phase == "clock_hold":
                phase_t += 1
                clock_scale = 1.0
                fractal_dim = 0.18
                show_clock = True
                if phase_t >= phase_len:
                    _begin_zoom_out()

            elif phase == "zoom_out":
                phase_t += 1
                u = phase_t / float(max(1, phase_len))
                cx, cy, scale = _lerp_view(z_from, z_to, u)
                color_shift = 0.0
                clock_scale = 0.0
                fractal_dim = 1.0
                if phase_t >= phase_len:
                    cx, cy, scale = start_view
                    print(f"[Fractal] Cycle #{cycle} complete — next fractal")
                    _start_new_cycle()

            elif phase == "new_cycle":
                _start_new_cycle()

            try:
                canvas.Fill(0, 0, 0)
                pixels, last_escape = render_fractal(
                    width, height, cx, cy, scale, max_iter,
                    kind=kind, julia_c=julia_c, color_shift=color_shift,
                )
                # Dim fractal under the clock reveal
                if fractal_dim < 0.999:
                    dim = max(0.0, min(1.0, fractal_dim))
                    set_px = canvas.SetPixel
                    for y in range(height):
                        row = pixels[y]
                        for x in range(width):
                            r, g, b = row[x]
                            set_px(
                                x, y,
                                int(r * dim), int(g * dim), int(b * dim),
                            )
                else:
                    blit_pixels(canvas, pixels, width, height)
                if show_clock and clock_scale > 0.05:
                    _draw_digital_clock(
                        canvas, width, height, clock_scale,
                        rgb=CLOCK_RGB, glow=CLOCK_GLOW,
                    )
                canvas = LED.TheMatrix.SwapOnVSync(canvas)
                LED.Canvas = canvas
            except Exception:
                pass

            if tick:
                tick.tick(TARGET_FPS)
            else:
                time.sleep(1.0 / TARGET_FPS)

    except KeyboardInterrupt:
        print("[Fractal] Interrupted")

    try:
        LED.ClearBuffers()
        LED.TheMatrix.Clear()
    except Exception:
        pass


# ---------------- Title intro: "Fractal Blaster" ----------------
TITLE_LINE1 = "FRACTAL"
TITLE_LINE2 = "BLASTER"
TITLE_GAP = 1
TITLE_LINE_GAP = 2
TITLE_COLORS = (
    (255, 50, 40),
    (40, 200, 255),
    (255, 200, 30),
    (180, 60, 255),
    (40, 255, 120),
)
# Intro timing (seconds)
INTRO_ZOOM_IN_SEC = 1.15      # title scales up from nothing
INTRO_HOLD_SEC = 0.55
INTRO_DIVE_SEC = 1.35         # zoom into one letter
INTRO_PORTAL_SEC = 0.55       # letter → fractal blend
INTRO_FPS = 24


def _title_letter_sprite(char):
    ch = char.upper()
    if not ("A" <= ch <= "Z"):
        return None
    idx = ord(ch) - ord("A")
    try:
        import copy
        return LED.TrimSprite(copy.deepcopy(LED.AlphaSpriteList[idx]))
    except Exception:
        return None


def _title_sprite_pixels(sprite, rgb):
    pixels = []
    if sprite is None:
        return pixels, 0, 0
    sw, sh = sprite.width, sprite.height
    for count in range(sw * sh):
        if sprite.grid[count] == 0:
            continue
        y, x = divmod(count, sw)
        pixels.append((x, y, rgb))
    return pixels, sw, sh


def _build_title_letters(panel_w, panel_h, rgb):
    """
    Layout FRACTAL / BLASTER as two centered lines of 5×5 alpha sprites.
    Returns list of dicts: char, pixels, w, h, rest_x, rest_y, cx, cy
    """
    lines = [TITLE_LINE1, TITLE_LINE2]
    line_specs = []
    max_h = 0
    for line in lines:
        specs = []
        for ch in line:
            if ch == " ":
                continue
            sprite = _title_letter_sprite(ch)
            if sprite is None:
                continue
            pixels, lw, lh = _title_sprite_pixels(sprite, rgb)
            specs.append((ch, pixels, lw, lh))
            max_h = max(max_h, lh)
        line_specs.append(specs)
    if not any(line_specs):
        return []

    total_h = max_h * len(line_specs) + TITLE_LINE_GAP * max(0, len(line_specs) - 1)
    top_y = max(0, (panel_h - total_h) // 2)
    letters = []
    for line_i, specs in enumerate(line_specs):
        if not specs:
            continue
        total_w = sum(s[2] for s in specs) + TITLE_GAP * max(0, len(specs) - 1)
        x_cursor = max(0, (panel_w - total_w) // 2)
        rest_y = top_y + line_i * (max_h + TITLE_LINE_GAP)
        for ch, pixels, lw, lh in specs:
            rx = float(x_cursor)
            ry = float(rest_y + (max_h - lh))
            letters.append({
                "char": ch,
                "pixels": pixels,
                "w": lw,
                "h": lh,
                "rest_x": rx,
                "rest_y": ry,
                "cx": rx + lw * 0.5,
                "cy": ry + lh * 0.5,
            })
            x_cursor += lw + TITLE_GAP
    return letters


def _draw_title_letters(canvas, letters, panel_w, panel_h, cam_cx, cam_cy, cam_scale, fade=1.0):
    """
    Draw title letters with a 2D camera (center + scale).
    Screen pos = (world - cam) * scale + panel_center
    """
    fade = _clamp(fade, 0.0, 1.0)
    if fade <= 0.01 or cam_scale <= 0.001:
        return
    set_px = canvas.SetPixel
    pcx = panel_w * 0.5
    pcy = panel_h * 0.5
    for L in letters:
        for dx, dy, rgb in L["pixels"]:
            wx = L["rest_x"] + dx
            wy = L["rest_y"] + dy
            sx = int(round((wx - cam_cx) * cam_scale + pcx))
            sy = int(round((wy - cam_cy) * cam_scale + pcy))
            if 0 <= sx < panel_w and 0 <= sy < panel_h:
                set_px(
                    sx, sy,
                    int(rgb[0] * fade),
                    int(rgb[1] * fade),
                    int(rgb[2] * fade),
                )


def _smooth(t):
    t = _clamp(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def PlayFractalTitleIntro(StopEvent=None):
    """
    FRACTAL BLASTER title:
      1) Zooms into view from nothing
      2) Brief hold
      3) Camera dives into a random letter
      4) Letter dissolves into the Mandelbrot — fractal begins there

    Returns optional start camera dict for PlayFractal, or None.
    """
    if _stop(StopEvent):
        return None
    width = int(getattr(LED, "HatWidth", 64) or 64)
    height = int(getattr(LED, "HatHeight", 32) or 32)
    try:
        canvas = LED.TheMatrix.CreateFrameCanvas()
    except Exception:
        canvas = LED.Canvas

    rgb = random.choice(TITLE_COLORS)
    letters = _build_title_letters(width, height, rgb)
    if not letters:
        print("[Fractal] Title intro skipped (no letters)")
        return None

    # Pick a letter to dive into (prefer middle of words, not edges only)
    dive_letter = random.choice(letters)
    # Prefer letters with more body (not I) when possible
    meaty = [L for L in letters if L["char"] not in ("I", "L", "J", "T")]
    if meaty:
        dive_letter = random.choice(meaty)

    print(
        f"[Fractal] Title intro — FRACTAL BLASTER  "
        f"dive into '{dive_letter['char']}'"
    )

    # Camera starts tiny at panel center looking at title center
    title_cx = sum(L["cx"] for L in letters) / len(letters)
    title_cy = sum(L["cy"] for L in letters) / len(letters)
    dive_cx, dive_cy = dive_letter["cx"], dive_letter["cy"]

    # How far to zoom so the dive letter roughly fills the panel
    letter_span = max(dive_letter["w"], dive_letter["h"], 3)
    dive_scale = min(width, height) / float(letter_span) * 0.92

    tick = pygame.time.Clock() if HAS_PYGAME else None
    start = time.time()
    phase = "zoom_in"
    phase_t0 = start
    handoff = None

    try:
        while True:
            if _stop(StopEvent):
                break
            now = time.time()
            elapsed = now - phase_t0

            cam_cx, cam_cy = title_cx, title_cy
            cam_scale = 1.0
            letter_fade = 1.0
            fractal_fade = 0.0
            frac_cx, frac_cy, frac_scale = INIT_CX, INIT_CY, INIT_SCALE

            if phase == "zoom_in":
                # Scale from ~0 → 1, camera locked on title center
                t = _smooth(elapsed / max(0.05, INTRO_ZOOM_IN_SEC))
                cam_scale = 0.04 + 0.96 * t
                cam_cx, cam_cy = title_cx, title_cy
                if elapsed >= INTRO_ZOOM_IN_SEC:
                    phase = "hold"
                    phase_t0 = now
                    print("[Fractal] Title locked — FRACTAL BLASTER")

            elif phase == "hold":
                cam_scale = 1.0
                cam_cx, cam_cy = title_cx, title_cy
                if elapsed >= INTRO_HOLD_SEC:
                    phase = "dive"
                    phase_t0 = now
                    print(f"[Fractal] Diving into letter '{dive_letter['char']}'")

            elif phase == "dive":
                # Pan toward letter + zoom hard
                t = _smooth(elapsed / max(0.05, INTRO_DIVE_SEC))
                cam_cx = title_cx + (dive_cx - title_cx) * t
                cam_cy = title_cy + (dive_cy - title_cy) * t
                # Log-ish zoom so the rush feels strong near the end
                cam_scale = math.exp(
                    math.log(1.0) + (math.log(dive_scale) - math.log(1.0)) * t
                )
                # Late in the dive, start revealing fractal under the letter
                if t > 0.55:
                    fractal_fade = _smooth((t - 0.55) / 0.45) * 0.85
                    # Fractal also "zooms in" a bit as if the letter opens a portal
                    frac_scale = INIT_SCALE * (1.0 - 0.55 * _smooth((t - 0.55) / 0.45))
                if elapsed >= INTRO_DIVE_SEC:
                    phase = "portal"
                    phase_t0 = now
                    print("[Fractal] Letter portal → Mandelbrot")

            elif phase == "portal":
                # Letter fades out; fractal takes over and continues zooming in
                t = _smooth(elapsed / max(0.05, INTRO_PORTAL_SEC))
                cam_cx, cam_cy = dive_cx, dive_cy
                cam_scale = dive_scale * (1.0 + 0.35 * t)
                letter_fade = max(0.0, 1.0 - t * 1.15)
                fractal_fade = 1.0
                frac_scale = INIT_SCALE * (0.45 - 0.12 * t)
                frac_scale = max(0.18, frac_scale)
                if elapsed >= INTRO_PORTAL_SEC:
                    handoff = {
                        "cx": INIT_CX,
                        "cy": INIT_CY,
                        "scale": max(0.22, INIT_SCALE * 0.28),
                    }
                    break
            else:
                break

            # Render
            try:
                canvas.Fill(0, 0, 0)
                if fractal_fade > 0.02:
                    max_iter = _iters_for_scale(frac_scale)
                    pixels, _esc = render_mandelbrot(
                        width, height, frac_cx, frac_cy, frac_scale, max_iter,
                    )
                    # Blend fractal by dimming toward black then draw
                    set_px = canvas.SetPixel
                    ff = fractal_fade
                    for y in range(height):
                        row = pixels[y]
                        for x in range(width):
                            r, g, b = row[x]
                            set_px(
                                x, y,
                                int(r * ff), int(g * ff), int(b * ff),
                            )
                if letter_fade > 0.02:
                    _draw_title_letters(
                        canvas, letters, width, height,
                        cam_cx, cam_cy, cam_scale, fade=letter_fade,
                    )
                canvas = LED.TheMatrix.SwapOnVSync(canvas)
                LED.Canvas = canvas
            except Exception:
                pass

            if tick:
                tick.tick(INTRO_FPS)
            else:
                time.sleep(1.0 / INTRO_FPS)

    except KeyboardInterrupt:
        pass
    except Exception as exc:
        print(f"[Fractal] title intro error: {exc}")
        handoff = None

    print("[Fractal] Title intro complete — entering fractal tour")
    return handoff


def LaunchFractal(Duration=10, ShowIntro=True, StopEvent=None):
    """Public entry for LEDcommander / Twitch / LEDsim."""
    try:
        LED.LoadConfigData()
    except Exception:
        pass
    start_cam = None
    if ShowIntro:
        try:
            start_cam = PlayFractalTitleIntro(StopEvent=StopEvent)
        except Exception as exc:
            print(f"[Fractal] intro failed: {exc}")
            start_cam = None
        try:
            LED.ClearBigLED()
            LED.ClearBuffers()
        except Exception:
            pass
    PlayFractal(Duration=Duration, StopEvent=StopEvent, start_cam=start_cam)


if __name__ == "__main__":
    try:
        LaunchFractal(Duration=30, ShowIntro=True, StopEvent=None)
    except KeyboardInterrupt:
        print("Exiting Fractal Blaster.")
