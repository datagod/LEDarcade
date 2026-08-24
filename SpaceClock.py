# =====================================================================================
# SPACE CLOCK — parallax fly-through
#
# Skyfall-style wrapping maps, far → near. Camera drifts in a
# slowly wandering direction so parallax is 2D and smooth. Objects live on
# the map off-screen and clip in one pixel at a time. HH:MM sprites sit on
# planets and gas giants. Free-floating 7-seg radios and a flip clock
# hang in space. Idle rotation: launch_spaceclock (5 min).
#
# Run:  python3 SpaceClock.py
# =====================================================================================

from __future__ import annotations

import math
import random
import time
from datetime import datetime

import LEDarcade as LED

try:
    import pygame
    HAS_PYGAME = True
except Exception:
    HAS_PYGAME = False


TARGET_FPS = 90.0
STAR_DIM_FACTOR = 1.0
LAYER_W = 320
LAYER_H = 384

# px/sec at layer 0; nearer layers use the multipliers
BASE_PX_PER_SEC = 4.8
LAYER_SPEEDS = (
    0.15,  # 0 far stars
    2.0,   # 1 far stars (duplicate, nearer)
    3.2,   # 2 nebula
    4.5,   # 3 gas giants
    5.5,   # 4 planets
)
N_LAYERS = len(LAYER_SPEEDS)
TURN_RATE = 0.56          # rad/s toward a new heading
HEADING_HOLD = (8.0, 18.0)
APPROACH_LEAD = 10.0      # seconds before :00 to seek a planet
CRUISE_START = 0.55
CRUISE_MAX = 1.40
CRUISE_ACCEL = 0.110      # speed_scale per second on the journey
SETTLE_RATE = 3.6         # 1/sec — exponential ease toward the clock
SETTLE_STOP = 0.35        # pixels from center → full freeze
SETTLE_MAX_STEP = 1.0     # never skip a pixel while arriving
FLYBY_SLOW = 0.32         # cruise speed while passing a clock
FLYBY_TURN = 1.15         # rad/s pull toward a clock in view
FLYBY_MAX_SEC = 3.8       # then peel off so we don't orbit

GIANT_COUNT = 3
GIANT_MIN_R = 18
GIANT_MAX_R = 32
PLANET_COUNT = 5
PLANET_MIN_R = 8
PLANET_MAX_R = 14
CLOCK_RGB = (240, 235, 90)
CLOCK_BACK = (8, 10, 18)
RADIO_LIT = (255, 36, 28)
RADIO_DIM = (32, 8, 6)
RADIO_FACE = (16, 8, 8)
RADIO_BROWN = (118, 68, 34)
RADIO_BROWN_DK = (72, 38, 18)
_SEG_A, _SEG_B, _SEG_C, _SEG_D = 0x01, 0x02, 0x04, 0x08
_SEG_E, _SEG_F, _SEG_G = 0x10, 0x20, 0x40
_SEG_MASKS = (0x3F, 0x06, 0x5B, 0x4F, 0x66, 0x6D, 0x7D, 0x07, 0x7F, 0x6F)


def _stop(StopEvent):
    try:
        return StopEvent is not None and StopEvent.is_set()
    except Exception:
        return False


def _panel_size():
    w = int(getattr(LED, "HatWidth", 64) or 64)
    h = int(getattr(LED, "HatHeight", 32) or 32)
    return max(16, w), max(16, h)


def _star_rgb(brightness, tint="blue"):
    brightness = max(1, int(brightness * STAR_DIM_FACTOR))
    if tint == "purple":
        return (
            max(0, min(255, brightness * 72 // 100)),
            max(0, min(255, brightness * 10 // 100)),
            max(0, min(255, brightness * 95 // 100)),
        )
    if tint == "red":
        return (
            max(0, min(255, brightness)),
            max(0, min(255, brightness * 12 // 100)),
            max(0, min(255, brightness * 16 // 100)),
        )
    return (max(0, brightness // 5), max(0, brightness // 3), brightness)


def _fill_stars(layer, starchance, brightness_range, purple_n=2, red_n=0):
    bmin, bmax = brightness_range
    hits = []
    lw, lh = layer.width, layer.height
    for y in range(lh):
        for x in range(lw):
            if random.randint(0, starchance) != 1:
                continue
            bri = random.randint(bmin, bmax)
            layer.map[y][x] = _star_rgb(bri)
            hits.append((x, y, bri))
    extra = min(len(hits), purple_n + red_n)
    if extra <= 0:
        return
    picked = random.sample(hits, extra)
    n_p = min(purple_n, extra)
    for x, y, bri in picked[:n_p]:
        layer.map[y][x] = _star_rgb(bri, "purple")
    for x, y, bri in picked[n_p:]:
        layer.map[y][x] = _star_rgb(bri, "red")


def _add_nebula(layer, count=6):
    palette = ((20, 0, 40), (0, 20, 50), (30, 10, 45), (10, 25, 35))
    lw, lh = layer.width, layer.height
    for _ in range(count):
        cx = random.randint(0, lw - 1)
        cy = random.randint(0, lh - 1)
        base = random.choice(palette)
        blobs = []
        for _b in range(random.randint(3, 5)):
            blobs.append((
                random.randint(-14, 14),
                random.randint(-10, 10),
                random.randint(12, 24),
                random.uniform(0.6, 1.4),
                random.uniform(0.6, 1.4),
            ))
        extent = 36
        for dy in range(-extent, extent + 1):
            for dx in range(-extent, extent + 1):
                fall = 0.0
                for ox, oy, rad, sx, sy in blobs:
                    nx = (dx - ox) / max(0.1, rad * sx)
                    ny = (dy - oy) / max(0.1, rad * sy)
                    d2 = nx * nx + ny * ny
                    if d2 < 1.0:
                        fall = max(fall, 1.0 - d2)
                if fall <= 0.12:
                    continue
                x = (cx + dx) % lw
                y = (cy + dy) % lh
                if layer.map[y][x] != (0, 0, 0):
                    continue
                layer.map[y][x] = tuple(
                    max(0, min(255, int(c * fall * 0.85))) for c in base
                )


class Planet(object):
    """Skyfall water-world (copied small, no shooter)."""

    OCEAN_DEEP = (18, 55, 105)
    OCEAN_MID = (35, 95, 155)
    OCEAN_SHALLOW = (55, 130, 185)
    CLOUD_WISP = (165, 200, 225)
    CLOUD_BRIGHT = (205, 228, 245)

    def __init__(self, cx, cy, radius):
        self.cx = cx
        self.cy = cy
        self.radius = radius
        self.seed = random.random() * 1000.0

    def rgb_at(self, dx, dy):
        dist = math.hypot(dx, dy)
        if dist > self.radius:
            return None
        u = dx / max(self.radius, 1)
        v = dy / max(self.radius, 1)
        r_norm = dist / max(self.radius, 1)
        lat = math.sin(v * 2.65 + self.seed * 0.4) * 0.5 + 0.5
        if lat < 0.34:
            base = self.OCEAN_DEEP
        elif lat < 0.68:
            base = self.OCEAN_MID
        else:
            base = self.OCEAN_SHALLOW
        limb = 1.0 - 0.38 * r_norm ** 1.18
        light = 1.0 + 0.14 * max(0.0, (-u * 0.55 - v * 0.70))
        factor = max(0.32, min(1.25, limb * light))
        ocean = tuple(min(255, int(c * factor)) for c in base)
        cover = (
            0.50
            + 0.26 * math.sin(u * 2.35 + v * 1.85 + self.seed)
            + 0.18 * math.cos(u * 3.80 - v * 2.95 + self.seed * 1.55)
        )
        cover = max(0.0, min(1.0, cover))
        if cover < 0.58:
            return ocean
        blend = min(1.0, (cover - 0.58) / 0.42)
        cloud = self.CLOUD_BRIGHT if cover > 0.82 else self.CLOUD_WISP
        return tuple(
            min(255, int(ocean[i] * (1.0 - blend) + cloud[i] * blend))
            for i in range(3)
        )

    def paint(self, layer):
        r = self.radius
        lw, lh = layer.width, layer.height
        for dy in range(-r - 1, r + 2):
            for dx in range(-r - 1, r + 2):
                rgb = self.rgb_at(dx, dy)
                if rgb is None:
                    continue
                layer.map[(self.cy + dy) % lh][(self.cx + dx) % lw] = rgb


def _gas_giant_rgb(dx, dy, radius, colors):
    dist = math.hypot(dx, dy)
    if dist > radius:
        return None
    band_idx = int((dy / max(1.0, radius * 0.42)) + 1.5) % len(colors)
    r, g, b = colors[band_idx]
    limb = 1.0 - 0.42 * (dist / max(radius, 1)) ** 1.15
    lit = 1.0 + 0.22 * max(0.0, (-dx * 0.65 - dy * 0.75) / radius)
    factor = max(0.38, min(1.3, limb * lit))
    return tuple(min(255, int(c * factor)) for c in (r, g, b))


def _paint_giant(layer, cx, cy, radius, colors, ringed):
    lw, lh = layer.width, layer.height
    for dy in range(-radius - 4, radius + 5):
        for dx in range(-radius - 8, radius + 9):
            x = (cx + dx) % lw
            y = (cy + dy) % lh
            if ringed and abs(dy) <= max(2, radius // 7):
                ring_dist = abs(math.hypot(dx, dy) - radius * 0.92)
                if ring_dist < 2.2 and abs(dx) > radius * 0.35:
                    layer.map[y][x] = tuple(
                        min(255, int(c * 0.72 + colors[1][i] * 0.28))
                        for i, c in enumerate(colors[0])
                    )
                    continue
            rgb = _gas_giant_rgb(dx, dy, radius, colors)
            if rgb is not None:
                layer.map[y][x] = rgb


def _place_giants(layer, display_h):
    palettes = (
        ((185, 145, 95), (150, 105, 65), (205, 165, 105)),
        ((215, 185, 135), (165, 135, 95), (110, 85, 60)),
        ((75, 115, 175), (50, 85, 140), (115, 150, 205)),
        ((120, 85, 150), (85, 55, 110), (160, 120, 185)),
    )
    stations = []
    slot = layer.height // GIANT_COUNT
    for i in range(GIANT_COUNT):
        radius = random.randint(GIANT_MIN_R, GIANT_MAX_R)
        ringed = random.random() < 0.4
        colors = random.choice(palettes)
        cx = random.randint(0, layer.width - 1)
        y0 = i * slot + radius + 2
        y1 = min(layer.height - radius - 2, (i + 1) * slot - radius)
        cy = random.randint(y0, max(y0, y1))
        _paint_giant(layer, cx, cy, radius, colors, ringed)
        stations.append({"cx": cx, "cy": cy, "radius": radius})
    return stations


def _place_planets(layer, display_h):
    stations = []
    slot = layer.height // PLANET_COUNT
    for i in range(PLANET_COUNT):
        radius = random.randint(PLANET_MIN_R, PLANET_MAX_R)
        cx = random.randint(0, layer.width - 1)
        y0 = i * slot + radius + 1
        y1 = min(layer.height - radius - 1, (i + 1) * slot - radius)
        cy = random.randint(y0, max(y0, y1))
        Planet(cx, cy, radius).paint(layer)
        stations.append({"cx": cx, "cy": cy, "radius": radius})
    return stations


def _new_layer(name, width, height):
    return LED.Layer(name=name, width=width, height=height, h=0, v=0)


def _build_layers(panel_w, panel_h):
    lw, lh = LAYER_W, LAYER_H
    layers = []

    far = _new_layer("far", lw, lh)
    _fill_stars(far, 340, (55, 170), purple_n=4, red_n=4)
    layers.append(far)

    far2 = _new_layer("far2", lw, lh)
    _fill_stars(far2, 340, (55, 170), purple_n=4, red_n=4)
    layers.append(far2)

    nebula = _new_layer("nebula", lw, lh)
    _add_nebula(nebula, count=7)
    layers.append(nebula)

    giants = _new_layer("giants", lw, lh)
    giant_stations = _place_giants(giants, panel_h)
    layers.append(giants)

    planets = _new_layer("planets", lw, lh)
    planet_stations = _place_planets(planets, panel_h)
    layers.append(planets)

    floaters = _place_floaters(planets, planet_stations)
    return layers, giant_stations, planet_stations, floaters


def _draw_layer(canvas, layer, sh, sv, width, height, smooth=True):
    """Nearest for star fields (1px stars). Bilinear for nebula/planets."""
    lw, lh = layer.width, layer.height
    put = canvas.SetPixel
    mmap = layer.map
    black = (0, 0, 0)
    if not smooth:
        ih = int(math.floor(sh)) % lw
        iv = int(math.floor(sv)) % lh
        for sy in range(height):
            row = mmap[(sy + iv) % lh]
            for sx in range(width):
                rgb = row[(sx + ih) % lw]
                if rgb != black:
                    put(sx, sy, rgb[0], rgb[1], rgb[2])
        return
    for sy in range(height):
        fy = sy + sv
        y0 = int(math.floor(fy)) % lh
        y1 = (y0 + 1) % lh
        ty = fy - math.floor(fy)
        row0 = mmap[y0]
        row1 = mmap[y1]
        ity = 1.0 - ty
        for sx in range(width):
            fx = sx + sh
            x0 = int(math.floor(fx)) % lw
            x1 = (x0 + 1) % lw
            tx = fx - math.floor(fx)
            c00 = row0[x0]
            c10 = row0[x1]
            c01 = row1[x0]
            c11 = row1[x1]
            if c00 == c10 == c01 == c11 == black:
                continue
            itx = 1.0 - tx
            r = (
                c00[0] * itx * ity + c10[0] * tx * ity
                + c01[0] * itx * ty + c11[0] * tx * ty
            )
            g = (
                c00[1] * itx * ity + c10[1] * tx * ity
                + c01[1] * itx * ty + c11[1] * tx * ty
            )
            b = (
                c00[2] * itx * ity + c10[2] * tx * ity
                + c01[2] * itx * ty + c11[2] * tx * ty
            )
            put(sx, sy, int(r + 0.5), int(g + 0.5), int(b + 0.5))
    lw, lh = layer.width, layer.height
    put = canvas.SetPixel
    mmap = layer.map
    black = (0, 0, 0)
    for sy in range(height):
        fy = sy + sv
        y0 = int(math.floor(fy)) % lh
        y1 = (y0 + 1) % lh
        ty = fy - math.floor(fy)
        row0 = mmap[y0]
        row1 = mmap[y1]
        ity = 1.0 - ty
        for sx in range(width):
            fx = sx + sh
            x0 = int(math.floor(fx)) % lw
            x1 = (x0 + 1) % lw
            tx = fx - math.floor(fx)
            c00 = row0[x0]
            c10 = row0[x1]
            c01 = row1[x0]
            c11 = row1[x1]
            if c00 == c10 == c01 == c11 == black:
                continue
            itx = 1.0 - tx
            r = (
                c00[0] * itx * ity + c10[0] * tx * ity
                + c01[0] * itx * ty + c11[0] * tx * ty
            )
            g = (
                c00[1] * itx * ity + c10[1] * tx * ity
                + c01[1] * itx * ty + c11[1] * tx * ty
            )
            b = (
                c00[2] * itx * ity + c10[2] * tx * ity
                + c01[2] * itx * ty + c11[2] * tx * ty
            )
            put(sx, sy, int(r + 0.5), int(g + 0.5), int(b + 0.5))


def _clock_scale_for_planet(rad, tw, th):
    """Fit HH:MM on the disk: ~80% of diameter wide, ~70% of radius tall."""
    if tw < 1 or th < 1 or rad < 1:
        return 1.0
    return max(1.0, min((rad * 1.6) / float(tw), (rad * 0.72) / float(th)))


def _stamp_clock_on_layer(layer, st, sprite):
    """Bake a planet-sized HH:MM into the map (restore underlay on updates)."""
    lw, lh = layer.width, layer.height
    cx, cy, rad = st["cx"], st["cy"], st["radius"]
    tw, th = sprite.width, sprite.height
    scale = st.get("clock_scale")
    if scale is None:
        scale = _clock_scale_for_planet(rad, tw, th)
        st["clock_scale"] = scale
    dw = max(1, int(round(tw * scale)))
    dh = max(1, int(round(th * scale)))
    left = cx - dw // 2
    top = cy - dh // 2
    r2 = rad * rad
    if "underlay" not in st:
        under = []
        for py in range(top - 1, top + dh + 1):
            for px in range(left - 1, left + dw + 1):
                dx, dy = px - cx, py - cy
                if dx * dx + dy * dy > r2:
                    continue
                x, y = px % lw, py % lh
                under.append((x, y, layer.map[y][x]))
        st["underlay"] = under
    else:
        for x, y, rgb in st["underlay"]:
            layer.map[y][x] = rgb
    br, bg, bb = CLOCK_BACK
    cr, cg, cb = CLOCK_RGB
    grid = sprite.grid
    inv = 1.0 / scale if scale > 1e-6 else 1.0
    for py in range(top - 1, top + dh + 1):
        for px in range(left - 1, left + dw + 1):
            dx, dy = px - cx, py - cy
            if dx * dx + dy * dy > r2:
                continue
            mx, my = px % lw, py % lh
            sx = (px - left + 0.5) * inv
            sy = (py - top + 0.5) * inv
            ix, iy = int(math.floor(sx)), int(math.floor(sy))
            if 0 <= ix < tw and 0 <= iy < th and grid[iy * tw + ix]:
                layer.map[my][mx] = (cr, cg, cb)
            else:
                layer.map[my][mx] = (br, bg, bb)


def _stamp_all_clocks(giant_layer, giants, planet_layer, planets, sprite,
                      floaters=None, hhmm=None):
    for st in giants:
        _stamp_clock_on_layer(giant_layer, st, sprite)
    for st in planets:
        _stamp_clock_on_layer(planet_layer, st, sprite)
    if floaters and hhmm is not None:
        for st in floaters:
            _stamp_floater_on_layer(planet_layer, st, hhmm)


def _seg_digit_pixels(ox, oy, digit, lit, dim):
    """Pinball/SevenSegClock 5×9 layout → (x,y,rgb) list."""
    w, h, t = 5, 9, 1
    mid = h // 2
    hx0, hx1 = t, w - 1 - t
    mask = _SEG_MASKS[int(digit) % 10]
    segs = (
        (_SEG_A, "h", hx0, hx1, 0),
        (_SEG_G, "h", hx0, hx1, mid),
        (_SEG_D, "h", hx0, hx1, h - t),
        (_SEG_F, "v", 0, t, mid - 1),
        (_SEG_B, "v", w - t, t, mid - 1),
        (_SEG_E, "v", 0, mid + t, h - 1 - t),
        (_SEG_C, "v", w - t, mid + t, h - 1 - t),
    )
    out = []
    for bit, kind, a, b, c in segs:
        rgb = lit if (mask & bit) else dim
        if kind == "h":
            for yy in range(c, c + t):
                for xx in range(a, b + 1):
                    out.append((ox + xx, oy + yy, rgb))
        else:
            for xx in range(a, a + t):
                for yy in range(b, c + 1):
                    out.append((ox + xx, oy + yy, rgb))
    return out


def _scale_xyrgb(pixels, zoom):
    if zoom <= 1:
        return pixels
    out = []
    for x, y, rgb in pixels:
        for zy in range(zoom):
            for zx in range(zoom):
                out.append((x * zoom + zx, y * zoom + zy, rgb))
    return out


def _radio_clock_pixels(hhmm, zoom=1):
    """Old clock-radio: brown bezel, dark face, red 7-seg."""
    dw, dh, gap, cw = 5, 9, 1, 2
    inner_w = 4 * dw + 3 * gap + cw
    inner_h = dh
    border, pad = 2, 1
    W = inner_w + 2 * pad + 2 * border
    H = inner_h + 2 * pad + 2 * border
    pix = {}
    for y in range(H):
        for x in range(W):
            edge = x < border or y < border or x >= W - border or y >= H - border
            pix[(x, y)] = RADIO_BROWN if edge else RADIO_FACE
            if edge and (x == 0 or y == 0 or x == W - 1 or y == H - 1):
                pix[(x, y)] = RADIO_BROWN_DK
    ox = border + pad
    oy = border + pad
    digits = [int(hhmm[0]), int(hhmm[1]), int(hhmm[2]), int(hhmm[3])]
    x = ox
    for i, d in enumerate(digits):
        if i == 2:
            mid = dh // 2
            for dy in (mid - 2, mid + 1):
                for xx in range(cw):
                    pix[(x + xx, oy + dy)] = RADIO_LIT
            x += cw + gap
        for px, py, rgb in _seg_digit_pixels(0, 0, d, RADIO_LIT, RADIO_DIM):
            pix[(x + px, oy + py)] = rgb
        x += dw + gap
    items = [(x, y, rgb) for (x, y), rgb in pix.items()]
    items = _scale_xyrgb(items, zoom)
    return items, W * zoom, H * zoom


def _plaque_clock_pixels(hhmm, zoom=1):
    """Small LED-sprite HH:MM in a brown frame (etc.)."""
    spr = _hhmm_sprite(hhmm)
    tw, th = spr.width, spr.height
    border, pad = 2, 1
    W = tw + 2 * pad + 2 * border
    H = th + 2 * pad + 2 * border
    pix = {}
    for y in range(H):
        for x in range(W):
            edge = x < border or y < border or x >= W - border or y >= H - border
            pix[(x, y)] = RADIO_BROWN if edge else (6, 6, 10)
            if edge and (x == 0 or y == 0 or x == W - 1 or y == H - 1):
                pix[(x, y)] = RADIO_BROWN_DK
    ox, oy = border + pad, border + pad
    for count in range(tw * th):
        if spr.grid[count]:
            y, x = divmod(count, tw)
            pix[(ox + x, oy + y)] = (40, 255, 80)
    items = [(x, y, rgb) for (x, y), rgb in pix.items()]
    items = _scale_xyrgb(items, zoom)
    return items, W * zoom, H * zoom


def _flip_clock_pixels(hhmm, max_w=38, max_h=16):
    """70s split-flap face from LEDarcade.GenerateFlipClockImage."""
    text = hhmm[:2] + ":" + hhmm[2:]
    try:
        img = LED.GenerateFlipClockImage(Text=text)
        bbox = img.getbbox()
        if bbox:
            img = img.crop(bbox)
        w, h = img.size
        scale = min(max_w / float(w), max_h / float(h), 1.0)
        nw = max(8, int(round(w * scale)))
        nh = max(6, int(round(h * scale)))
        img = img.resize((nw, nh), resample=1)  # NEAREST
        px = img.load()
        items = []
        for y in range(nh):
            for x in range(nw):
                rgb = px[x, y]
                if rgb != (0, 0, 0):
                    items.append((x, y, rgb))
        return items, nw, nh
    except Exception as exc:
        print("[SpaceClock] flip clock face failed: {}".format(exc))
        return _plaque_clock_pixels(hhmm, zoom=2)


def _floater_face(kind, zoom, hhmm):
    if kind == "radio":
        return _radio_clock_pixels(hhmm, zoom=zoom)
    if kind == "flip":
        return _flip_clock_pixels(hhmm)
    return _plaque_clock_pixels(hhmm, zoom=zoom)


def _stamp_floater_on_layer(layer, st, hhmm):
    items, w, h = _floater_face(st["kind"], st.get("zoom", 1), hhmm)
    st["bw"], st["bh"] = w, h
    st["radius"] = max(w, h) * 0.55
    lw, lh = layer.width, layer.height
    cx, cy = st["cx"], st["cy"]
    left, top = cx - w // 2, cy - h // 2
    if "underlay" not in st:
        under = []
        for py in range(h):
            for px in range(w):
                x, y = (left + px) % lw, (top + py) % lh
                under.append((x, y, layer.map[y][x]))
        st["underlay"] = under
    else:
        for x, y, rgb in st["underlay"]:
            layer.map[y][x] = rgb
    for px, py, rgb in items:
        layer.map[(top + py) % lh][(left + px) % lw] = rgb


def _place_floaters(layer, avoid):
    """A few free-floating clocks of mixed styles on the planet layer."""
    specs = (
        ("radio", 1),
        ("radio", 2),
        ("flip", 1),
        ("plaque", 2),
    )
    sizes = {
        ("radio", 1): (31, 15),
        ("radio", 2): (62, 30),
        ("flip", 1): (38, 16),
        ("plaque", 2): (46, 22),
    }
    floaters = []
    for kind, zoom in specs:
        bw, bh = sizes[(kind, zoom)]
        cr = math.hypot(bw, bh) * 0.5
        placed = False
        for _try in range(40):
            cx = random.randint(0, layer.width - 1)
            cy = random.randint(0, layer.height - 1)
            ok = True
            for st in avoid + floaters:
                d = math.hypot(
                    min((cx - st["cx"]) % layer.width,
                        (st["cx"] - cx) % layer.width),
                    min((cy - st["cy"]) % layer.height,
                        (st["cy"] - cy) % layer.height),
                )
                other_r = st.get("radius", cr)
                if d < other_r + cr + 12:
                    ok = False
                    break
            if ok:
                floaters.append({
                    "cx": cx, "cy": cy, "kind": kind, "zoom": zoom,
                    "radius": cr,
                })
                placed = True
                break
        if not placed:
            floaters.append({
                "cx": random.randint(0, layer.width - 1),
                "cy": random.randint(0, layer.height - 1),
                "kind": kind, "zoom": zoom, "radius": cr,
            })
    return floaters


def _hhmm_sprite(hhmm):
    h1, h2, m1, m2 = int(hhmm[0]), int(hhmm[1]), int(hhmm[2]), int(hhmm[3])
    spr = LED.JoinSprite(LED.DigitSpriteList[h1], LED.DigitSpriteList[h2], 1)
    spr = LED.JoinSprite(spr, LED.ColonSprite, 0)
    spr = LED.JoinSprite(spr, LED.DigitSpriteList[m1], 0)
    spr = LED.JoinSprite(spr, LED.DigitSpriteList[m2], 1)
    return spr


def _now_hhmm():
    return datetime.now().strftime("%H%M")


def _secs_to_minute():
    n = datetime.now()
    return 60.0 - (n.second + n.microsecond * 1e-6)


def _nearest_clock(stations_and_views, vw, vh):
    """Closest clock to the view center (unwrapped screen space)."""
    best = None
    best_d = 1e9
    cx, cy = vw * 0.5, vh * 0.5
    for st, sh, sv, layer, li in stations_and_views:
        sx, sy = _map_to_view(st["cx"], st["cy"], sh, sv, layer.width, layer.height)
        dx, dy = sx - cx, sy - cy
        d = math.hypot(dx, dy)
        if d < best_d:
            best_d = d
            best = (dx, dy, d, st, layer, li)
    return best


def _angle_delta(target, current):
    d = (target - current + math.pi) % (2.0 * math.pi) - math.pi
    return d


def _clock_candidates(giant_stations, planet_stations, floaters,
                      scroll_h, scroll_v, layers):
    cands = []
    for st in giant_stations:
        cands.append((st, scroll_h[3], scroll_v[3], layers[3], 3))
    for st in planet_stations:
        cands.append((st, scroll_h[4], scroll_v[4], layers[4], 4))
    for st in floaters:
        cands.append((st, scroll_h[4], scroll_v[4], layers[4], 4))
    return cands


def _clock_in_view(st, sh, sv, layer, vw, vh):
    sx, sy = _map_to_view(st["cx"], st["cy"], sh, sv, layer.width, layer.height)
    r = float(st.get("radius", 10))
    return not (
        sx + r < 0 or sy + r < 0 or sx - r >= vw or sy - r >= vh
    )


def _map_to_view(cx, cy, sh, sv, lw, lh):
    """Nearest unwrapped screen position so objects slide in from the edge."""
    sx = (cx - sh) % lw
    sy = (cy - sv) % lh
    if sx > lw * 0.5:
        sx -= lw
    if sy > lh * 0.5:
        sy -= lh
    return sx, sy


def PlaySpaceClock(Duration=0, StopEvent=None):
    vw, vh = _panel_size()
    print("[SpaceClock] {}x{}  {}-layer parallax  {} FPS".format(
        vw, vh, N_LAYERS, int(TARGET_FPS)
    ))
    layers, giant_stations, planet_stations, floaters = _build_layers(vw, vh)
    speeds = [BASE_PX_PER_SEC * m for m in LAYER_SPEEDS]
    scroll_h = [0.0] * N_LAYERS
    scroll_v = [0.0] * N_LAYERS
    heading = random.uniform(0.0, math.pi * 2.0)
    heading_to = heading
    heading_hold = random.uniform(*HEADING_HOLD)
    speed_scale = CRUISE_START
    approaching = False
    hold_target = None
    flyby_target = None
    flyby_t = 0.0
    flyby_seen = set()
    hhmm = _now_hhmm()
    time_sprite = _hhmm_sprite(hhmm)
    _stamp_all_clocks(
        layers[3], giant_stations, layers[4], planet_stations, time_sprite,
        floaters=floaters, hhmm=hhmm,
    )

    canvas = getattr(LED, "Canvas", None)
    if canvas is None and getattr(LED, "TheMatrix", None) is not None:
        canvas = LED.TheMatrix.CreateFrameCanvas()
        LED.Canvas = canvas

    clock = pygame.time.Clock() if HAS_PYGAME else None
    start = time.time()
    last = start
    frame_dt = 1.0 / TARGET_FPS
    tick = 0

    try:
        while True:
            if _stop(StopEvent):
                print("[SpaceClock] StopEvent")
                return
            if Duration and Duration > 0:
                if (time.time() - start) >= Duration * 60.0:
                    print("[SpaceClock] Duration reached")
                    return

            now = time.time()
            dt = now - last
            last = now
            if dt <= 0:
                dt = frame_dt
            dt = min(dt, 2.0 * frame_dt)

            secs_left = _secs_to_minute()
            seek = secs_left <= APPROACH_LEAD
            hold_steady = False
            if seek:
                approaching = True
                flyby_target = None
                flyby_t = 0.0
                if hold_target is None:
                    candidates = _clock_candidates(
                        giant_stations, planet_stations, floaters,
                        scroll_h, scroll_v, layers,
                    )
                    near = _nearest_clock(candidates, vw, vh)
                    if near is not None:
                        _dx, _dy, _d, st, _layer, li = near
                        hold_target = (st, li)
                if hold_target is not None:
                    st, li = hold_target
                    layer = layers[li]
                    sx, sy = _map_to_view(
                        st["cx"], st["cy"],
                        scroll_h[li], scroll_v[li],
                        layer.width, layer.height,
                    )
                    dh = sx - vw * 0.5
                    dv = sy - vh * 0.5
                    dist = math.hypot(dh, dv)
                    if dist < SETTLE_STOP:
                        hold_steady = True
                        speed_scale = 0.0
                    else:
                        # Exponential ease-in: big steps when far, crawl when close
                        k = 1.0 - math.exp(-SETTLE_RATE * dt)
                        step_h = dh * k
                        step_v = dv * k
                        mag = math.hypot(step_h, step_v)
                        max_step = min(
                            SETTLE_MAX_STEP,
                            0.08 + dist * 0.055,
                        )
                        if mag > max_step > 0.0:
                            step_h *= max_step / mag
                            step_v *= max_step / mag
                        for i in range(N_LAYERS):
                            scroll_h[i] += step_h
                            scroll_v[i] += step_v
                        hold_steady = True
                        speed_scale = mag
            else:
                hold_target = None
                if approaching:
                    approaching = False
                    heading_to = heading + random.uniform(-0.9, 0.9)
                    heading_hold = random.uniform(*HEADING_HOLD)
                cands = _clock_candidates(
                    giant_stations, planet_stations, floaters,
                    scroll_h, scroll_v, layers,
                )
                for st, sh, sv, layer, _li in cands:
                    key = id(st)
                    if key in flyby_seen and not _clock_in_view(
                        st, sh, sv, layer, vw, vh
                    ):
                        flyby_seen.discard(key)

                if flyby_target is not None:
                    st, li = flyby_target
                    layer = layers[li]
                    if not _clock_in_view(
                        st, scroll_h[li], scroll_v[li], layer, vw, vh
                    ) or flyby_t >= FLYBY_MAX_SEC:
                        flyby_seen.add(id(st))
                        flyby_target = None
                        flyby_t = 0.0
                        heading_to = heading + random.choice((-0.55, 0.55))
                        heading_hold = random.uniform(3.0, 7.0)
                    else:
                        sx, sy = _map_to_view(
                            st["cx"], st["cy"],
                            scroll_h[li], scroll_v[li],
                            layer.width, layer.height,
                        )
                        heading_to = math.atan2(sy - vh * 0.5, sx - vw * 0.5)
                        speed_scale += (
                            (FLYBY_SLOW - speed_scale) * min(1.0, dt * 2.0)
                        )
                        flyby_t += dt
                        # steer a bit harder than wander, still a pass not a dock
                        dhead = _angle_delta(heading_to, heading)
                        max_turn = FLYBY_TURN * dt
                        if dhead > max_turn:
                            heading += max_turn
                        elif dhead < -max_turn:
                            heading -= max_turn
                        else:
                            heading = heading_to
                        heading_to = heading
                else:
                    for st, sh, sv, layer, li in cands:
                        if id(st) in flyby_seen:
                            continue
                        if _clock_in_view(st, sh, sv, layer, vw, vh):
                            flyby_target = (st, li)
                            flyby_t = 0.0
                            break
                    if flyby_target is None:
                        heading_hold -= dt
                        if heading_hold <= 0.0:
                            heading_to = random.uniform(0.0, math.pi * 2.0)
                            heading_hold = random.uniform(*HEADING_HOLD)
                        speed_scale += CRUISE_ACCEL * dt
                        if speed_scale > CRUISE_MAX:
                            speed_scale = CRUISE_MAX

            if not hold_steady:
                dhead = _angle_delta(heading_to, heading)
                max_turn = TURN_RATE * dt
                if dhead > max_turn:
                    heading += max_turn
                elif dhead < -max_turn:
                    heading -= max_turn
                else:
                    heading = heading_to
                hx, hy = math.cos(heading), math.sin(heading)
                for i in range(N_LAYERS):
                    step = speeds[i] * dt * speed_scale
                    dx, dy = hx * step, hy * step
                    mag = math.hypot(dx, dy)
                    if mag > 1.0:
                        dx /= mag
                        dy /= mag
                    scroll_h[i] += dx
                    scroll_v[i] += dy

            nxt = _now_hhmm()
            if nxt != hhmm:
                hhmm = nxt
                time_sprite = _hhmm_sprite(hhmm)
                _stamp_all_clocks(
                    layers[3], giant_stations, layers[4], planet_stations,
                    time_sprite, floaters=floaters, hhmm=hhmm,
                )
                print("[SpaceClock] {}:{}".format(hhmm[:2], hhmm[2:]))

            tick += 1

            if canvas is None:
                time.sleep(frame_dt)
                continue
            canvas.Fill(0, 0, 0)
            for i, layer in enumerate(layers):
                _draw_layer(
                    canvas, layer, scroll_h[i], scroll_v[i], vw, vh,
                    smooth=(i >= 2),
                )
            canvas = LED.TheMatrix.SwapOnVSync(canvas)
            LED.Canvas = canvas

            if clock is not None:
                clock.tick(TARGET_FPS)
            else:
                time.sleep(max(0.0, frame_dt - (time.time() - now)))
    except KeyboardInterrupt:
        print("[SpaceClock] Interrupted")


def LaunchSpaceClock(Duration=0, ShowIntro=True, StopEvent=None):
    try:
        LED.LoadConfigData()
    except Exception:
        pass
    LED.Initialize()
    try:
        LED.ClearBigLED()
        LED.ClearBuffers()
    except Exception:
        pass
    if _stop(StopEvent):
        return
    PlaySpaceClock(Duration=Duration, StopEvent=StopEvent)


if __name__ == "__main__":
    try:
        LaunchSpaceClock(Duration=0)
    except KeyboardInterrupt:
        print("Exiting Space Clock.")
