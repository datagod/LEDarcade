# =====================================================================================
# FRACTAL BLASTER — Mandelbrot explorer for the LED matrix
#
# Title: "FRACTAL BLASTER" zooms in from nothing, then the camera dives into
# a letter and the Mandelbrot set begins there.
#
# Tour: zoom in 2–3× (pause between) → pan the coastline → either zoom in
# 2–3× more or zoom out 2–3× (pause between) → repeat.
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
# Initial classic Mandelbrot framing
INIT_CX = -0.55
INIT_CY = 0.0
INIT_SCALE = 1.35          # half-height of view in complex plane
# Motion timing (frames @ TARGET_FPS)
ZOOM_IN_FRAMES = 72        # one zoom-in hop
ZOOM_OUT_FRAMES = 60       # one zoom-out hop
PAN_FRAMES = 90            # coastline pan
PAUSE_FRAMES = 32          # slowdown between hops
START_PAUSE_FRAMES = 36    # pause before a new cycle
# Series length
HOPS_MIN = 2
HOPS_MAX = 3
# Scale change per hop
ZOOM_IN_FACTOR = 0.20      # scale *= this each zoom-in
ZOOM_OUT_FACTOR = 4.0      # scale *= this each zoom-out (capped at INIT)
MAX_ZOOM_DEPTH = 1e-11
# Iterations grow as we zoom (detail)
BASE_ITERS = 48
MAX_ITERS = 220


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


# ---------------- Color palette ----------------
def _palette_color(t, inside=False):
    """
    Map normalized escape (0..1) to RGB. Interior of the set = near black.
    Classic psychedelic LED-friendly ramps.
    """
    if inside:
        return (0, 0, 0)
    t = _clamp(float(t), 0.0, 1.0)
    # Multi-stop palette: deep blue → cyan → lime → gold → magenta → white
    stops = (
        (0.00, (5, 5, 40)),
        (0.12, (10, 30, 140)),
        (0.28, (20, 140, 200)),
        (0.42, (30, 200, 90)),
        (0.55, (200, 210, 30)),
        (0.70, (255, 100, 20)),
        (0.85, (220, 30, 160)),
        (1.00, (255, 240, 255)),
    )
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
    # scale ~1 at start, tiny when deep
    depth = max(0.0, -math.log10(max(scale, 1e-16)))
    it = int(BASE_ITERS + depth * 28)
    return _clamp(it, BASE_ITERS, MAX_ITERS)


# ---------------- Mandelbrot ----------------
def mandelbrot_escape(cx, cy, max_iter):
    """
    Smooth-ish escape value for c = cx + i*cy.
    Returns (escaped, value) where value is 0..1 for exterior, 0 for interior.
    """
    zx = 0.0
    zy = 0.0
    for n in range(max_iter):
        # z = z^2 + c
        zx2 = zx * zx
        zy2 = zy * zy
        if zx2 + zy2 > 4.0:
            # Smooth iteration count
            log_zn = math.log(zx2 + zy2) * 0.5
            nu = math.log(log_zn / math.log(2.0)) / math.log(2.0) if log_zn > 0 else 0.0
            smooth = (n + 1 - nu) / float(max_iter)
            return True, _clamp(smooth, 0.0, 1.0)
        zy = 2.0 * zx * zy + cy
        zx = zx2 - zy2 + cx
    return False, 0.0


def render_mandelbrot(width, height, center_x, center_y, scale, max_iter):
    """
    Render Mandelbrot to a list of (r,g,b) rows.
    Aspect-correct: scale is half-height; width uses height aspect.
    """
    aspect = width / float(max(1, height))
    half_h = scale
    half_w = scale * aspect
    x0 = center_x - half_w
    y0 = center_y - half_h
    dx = (2.0 * half_w) / float(max(1, width))
    dy = (2.0 * half_h) / float(max(1, height))

    # Also return escape map for zoom-target picking (float 0 interior, >0 exterior)
    pixels = [[(0, 0, 0) for _ in range(width)] for _ in range(height)]
    escape = [[0.0 for _ in range(width)] for _ in range(height)]

    for py in range(height):
        cy = y0 + (py + 0.5) * dy
        row_pix = pixels[py]
        row_esc = escape[py]
        for px in range(width):
            cx = x0 + (px + 0.5) * dx
            escaped, val = mandelbrot_escape(cx, cy, max_iter)
            if escaped:
                row_esc[px] = val
                row_pix[px] = _palette_color(val, inside=False)
            else:
                row_esc[px] = 0.0
                row_pix[px] = _palette_color(0.0, inside=True)
    return pixels, escape


def blit_pixels(canvas, pixels, width, height):
    set_px = canvas.SetPixel
    for y in range(height):
        row = pixels[y]
        for x in range(width):
            r, g, b = row[x]
            set_px(x, y, r, g, b)


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


# ---------------- Tour choreography ----------------
def _build_cycle_plan():
    """
    One tour cycle:
      pause → zoom-in ×(2–3) with pauses → pan coastline →
      either zoom-in ×(2–3) or zoom-out ×(2–3) with pauses.
    """
    plan = [("pause", START_PAUSE_FRAMES)]
    n_in = random.randint(HOPS_MIN, HOPS_MAX)
    for i in range(n_in):
        plan.append(("zoom_in", None))
        plan.append(("pause", PAUSE_FRAMES))
    plan.append(("pan", None))
    plan.append(("pause", PAUSE_FRAMES))
    n2 = random.randint(HOPS_MIN, HOPS_MAX)
    if random.random() < 0.5:
        kind = "zoom_in"
    else:
        kind = "zoom_out"
    for i in range(n2):
        plan.append((kind, None))
        plan.append(("pause", PAUSE_FRAMES))
    return plan, n_in, kind, n2


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


def _begin_zoom_out(cx, cy, scale):
    target_scale = min(INIT_SCALE, scale * ZOOM_OUT_FACTOR)
    # Drift center toward the classic full framing as we pull out
    blend = 0.40 if target_scale < INIT_SCALE * 0.9 else 1.0
    tx = cx + (INIT_CX - cx) * blend
    ty = cy + (INIT_CY - cy) * blend
    if target_scale >= INIT_SCALE * 0.98:
        tx, ty, target_scale = INIT_CX, INIT_CY, INIT_SCALE
    return (cx, cy, scale), (tx, ty, target_scale)


def _begin_pan(cx, cy, scale, width, height, escape):
    """Pan to another coastal point at the *same* scale."""
    tx, ty = pick_zoom_target(cx, cy, scale, width, height, escape)
    # Keep scale fixed; if target equals current, nudge along a landmark coast
    if abs(tx - cx) + abs(ty - cy) < scale * 0.02:
        lx, ly = random.choice(_COASTAL_LANDMARKS)
        # Stay roughly at this depth: only move a fraction of the way
        tx = cx + (lx - cx) * 0.15
        ty = cy + (ly - cy) * 0.15
    return (cx, cy, scale), (tx, ty, scale)


# ---------------- Main loop ----------------
def PlayFractal(Duration=10, StopEvent=None, start_cam=None):
    """
    Mandelbrot coastal tour. Duration is minutes (LEDarcade convention).

    start_cam: optional dict {cx, cy, scale} from the title intro letter-dive
    so the fractal continues already mid-zoom after FRACTAL BLASTER.
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

    if start_cam and isinstance(start_cam, dict):
        cx = float(start_cam.get("cx", INIT_CX))
        cy = float(start_cam.get("cy", INIT_CY))
        scale = float(start_cam.get("scale", INIT_SCALE))
    else:
        cx, cy, scale = INIT_CX, INIT_CY, INIT_SCALE
    last_escape = None
    hop = 0

    # Active motion
    phase = "idle"       # idle | pause | zoom_in | zoom_out | pan
    phase_t = 0
    phase_len = 1
    z_from = (cx, cy, scale)
    z_to = (cx, cy, scale)
    pause_left = 0

    plan = []
    cycle = 0

    def _pull_next_action():
        """Start the next planned action; rebuild cycle when empty."""
        nonlocal plan, cycle, phase, phase_t, phase_len, z_from, z_to, pause_left, hop
        nonlocal cx, cy, scale
        while True:
            if not plan:
                plan, n_in, second_kind, n2 = _build_cycle_plan()
                cycle += 1
                print(
                    f"[Fractal] Cycle #{cycle}: zoom-in×{n_in} → pan → "
                    f"{second_kind}×{n2}"
                )
            action, arg = plan.pop(0)
            if action == "pause":
                phase = "pause"
                pause_left = int(arg or PAUSE_FRAMES)
                phase_t = 0
                phase_len = pause_left
                return
            if action == "zoom_in":
                z_from, z_to = _begin_zoom_in(
                    cx, cy, scale, width, height, last_escape,
                )
                phase = "zoom_in"
                phase_t = 0
                phase_len = ZOOM_IN_FRAMES
                hop += 1
                print(
                    f"[Fractal] Zoom-in #{hop} → ({z_to[0]:.6f}, {z_to[1]:.6f})  "
                    f"scale {z_from[2]:.3e} → {z_to[2]:.3e}"
                )
                return
            if action == "zoom_out":
                z_from, z_to = _begin_zoom_out(cx, cy, scale)
                phase = "zoom_out"
                phase_t = 0
                phase_len = ZOOM_OUT_FRAMES
                hop += 1
                print(
                    f"[Fractal] Zoom-out #{hop}  "
                    f"scale {z_from[2]:.3e} → {z_to[2]:.3e}"
                )
                return
            if action == "pan":
                z_from, z_to = _begin_pan(
                    cx, cy, scale, width, height, last_escape,
                )
                phase = "pan"
                phase_t = 0
                phase_len = PAN_FRAMES
                print(
                    f"[Fractal] Pan coastline → ({z_to[0]:.6f}, {z_to[1]:.6f})"
                )
                return

    _pull_next_action()

    print(
        f"[Fractal] Mandelbrot coastal tour  {width}x{height}  "
        f"duration={run_min} min  fps~{TARGET_FPS}"
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

            # --- Advance current action ---
            if phase == "pause":
                pause_left -= 1
                phase_t += 1
                if pause_left <= 0:
                    _pull_next_action()

            elif phase in ("zoom_in", "zoom_out", "pan"):
                phase_t += 1
                u = phase_t / float(max(1, phase_len))
                cx, cy, scale = _lerp_view(z_from, z_to, u)
                if phase_t >= phase_len:
                    cx, cy, scale = z_to[0], z_to[1], z_to[2]
                    _pull_next_action()

            elif phase == "idle":
                _pull_next_action()

            # --- Render ---
            pixels, last_escape = render_mandelbrot(
                width, height, cx, cy, scale, max_iter,
            )
            try:
                canvas.Fill(0, 0, 0)
                blit_pixels(canvas, pixels, width, height)
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
