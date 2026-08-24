# =====================================================================================
# CLOCK 3D — standalone experiment
#
# Fully shaded 3D HH:MM. Extruded 5×7 digits, shiny green metal, moving light.
# 4× supersample + gamma downsample for the smoothest edges the panel allows.
# Pure black background. Opens from a single pixel, zooms to a steady full
# view, then 5s before each minute zooms back out and in with the new time.
#
# Run:  python3 Clock3D.py
# =====================================================================================

from __future__ import annotations

import math
import time
from datetime import datetime

import LEDarcade as LED

try:
    import pygame
    HAS_PYGAME = True
except Exception:
    HAS_PYGAME = False


TARGET_FPS = 60
USE_24H = True
SSAA = 4                  # 4× supersample — smoothest silhouettes we can afford

# Camera: sit on -Z, look toward the origin
CAM_Y = 1.15
CAM_Z = -22.0
CAM_Z_SPECK = -1300.0     # ~1 LED pixel of clock
FOCAL = 52.0
PITCH = math.radians(16.0)
YAW = 0.0                 # locked facing the camera

INTRO_BLANK_SEC = 0.70
INTRO_SPECK_SEC = 0.55
INTRO_ZOOM_SEC = 3.20
ZOOM_LEAD_SEC = 5.0       # start zoom-out this many seconds before :00
SPECK_HOLD_SEC = 0.40     # pause on the pixel after the time flips

# Moving key light — clock stays put, highlights travel
LIGHT_ORBIT_SPEED = 0.85  # rad/s
LIGHT_ELEVATION = 0.58    # y component before normalize
AMBIENT = 0.20
KEY_DIFF = 1.05
FILL_DIFF = 0.38
SPEC_AMT = 0.95
SPEC_POW = 36.0

DIGIT_RGB = (40, 255, 80)
COLON_RGB = (55, 255, 100)
SPEC_RGB = (230, 255, 230)

DIGIT_W = 5
DIGIT_H = 7
DIGIT_D = 3
CELL = 1.0
GAP = 1.0
COLON_W = 2.0

# Chunky 5×7 scoreboard — 2-pixel strokes. Bit 4 = left column.
_DIGITS = (
    (0x1F, 0x1B, 0x1B, 0x1B, 0x1B, 0x1B, 0x1F),  # 0
    (0x0C, 0x1C, 0x0C, 0x0C, 0x0C, 0x0C, 0x1F),  # 1
    (0x1F, 0x03, 0x03, 0x1F, 0x18, 0x18, 0x1F),  # 2
    (0x1F, 0x03, 0x03, 0x0F, 0x03, 0x03, 0x1F),  # 3
    (0x1B, 0x1B, 0x1B, 0x1F, 0x03, 0x03, 0x03),  # 4
    (0x1F, 0x18, 0x18, 0x1F, 0x03, 0x03, 0x1F),  # 5
    (0x1F, 0x18, 0x18, 0x1F, 0x1B, 0x1B, 0x1F),  # 6
    (0x1F, 0x03, 0x03, 0x06, 0x0C, 0x0C, 0x0C),  # 7
    (0x1F, 0x1B, 0x1B, 0x1F, 0x1B, 0x1B, 0x1F),  # 8
    (0x1F, 0x1B, 0x1B, 0x1F, 0x03, 0x03, 0x1F),  # 9
)


def _stop(StopEvent):
    try:
        return StopEvent is not None and StopEvent.is_set()
    except Exception:
        return False


def _panel_size():
    w = int(getattr(LED, "HatWidth", 64) or 64)
    h = int(getattr(LED, "HatHeight", 32) or 32)
    return max(16, w), max(16, h)


def _vadd(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _vsub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _vmul(a, s):
    return (a[0] * s, a[1] * s, a[2] * s)


def _vdot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _vcross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _vlen(a):
    return math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])


def _vnorm(a):
    L = _vlen(a)
    if L < 1e-9:
        return (0.0, 1.0, 0.0)
    return (a[0] / L, a[1] / L, a[2] / L)


def _rx(p, c, s):
    y, z = p[1], p[2]
    return (p[0], y * c - z * s, y * s + z * c)


def _ry(p, c, s):
    x, z = p[0], p[2]
    return (x * c + z * s, p[1], -x * s + z * c)


def _rot(p, yaw, pitch):
    cy, sy = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)
    return _ry(_rx(p, cp, sp), cy, sy)


def _smoothstep(t):
    t = 0.0 if t < 0.0 else 1.0 if t > 1.0 else t
    # smootherstep — zero 1st and 2nd derivatives at the ends
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def _secs_to_minute():
    n = datetime.now()
    return 60.0 - (n.second + n.microsecond * 1e-6)


def _now_hhmm():
    dt = datetime.now()
    if USE_24H:
        return dt.strftime("%H%M")
    h = dt.hour % 12
    if h == 0:
        h = 12
    return "{:02d}{:02d}".format(h, dt.minute)


def _layout_cells():
    # H H . : . M M   ('.' = 1-cell gap) → 25 cells (0..24)
    return DIGIT_W * 4 + int(COLON_W) + 4


def _voxel_set(hhmm):
    """Integer voxels for HH:MM, plus a set of colon cells. Centered."""
    digits = set()
    colon = set()

    def stamp(ox, ch, dest):
        if ch < "0" or ch > "9":
            return
        rows = _DIGITS[ord(ch) - 48]
        for row, bits in enumerate(rows):
            vy = DIGIT_H - 1 - row
            for col in range(DIGIT_W):
                if bits & (1 << (DIGIT_W - 1 - col)):
                    for d in range(DIGIT_D):
                        dest.add((ox + col, vy, d))

    x = 0
    stamp(x, hhmm[0], digits)
    x += DIGIT_W + 1
    stamp(x, hhmm[1], digits)
    x += DIGIT_W + 1
    for d in range(DIGIT_D):
        for ox in range(int(COLON_W)):
            colon.add((x + ox, 1, d))
            colon.add((x + ox, 2, d))
            colon.add((x + ox, 4, d))
            colon.add((x + ox, 5, d))
    x += int(COLON_W) + 1
    stamp(x, hhmm[2], digits)
    x += DIGIT_W + 1
    stamp(x, hhmm[3], digits)

    sx = _layout_cells() // 2
    sy = DIGIT_H // 2
    sz = DIGIT_D // 2

    def recenter(src):
        return {(vx - sx, vy - sy, vz - sz) for (vx, vy, vz) in src}

    return recenter(digits), recenter(colon)


def _add_tri(tris, a, b, c, rgb, center):
    n = _vcross(_vsub(b, a), _vsub(c, a))
    mid = _vmul(_vadd(_vadd(a, b), c), 1.0 / 3.0)
    if _vdot(n, _vsub(mid, center)) < 0.0:
        a, c = c, a
        n = _vmul(n, -1.0)
    n = _vnorm(n)
    tris.append((a, b, c, n, rgb))


def _emit_exposed_faces(tris, voxels, rgb):
    nbr = (
        (1, 0, 0), (-1, 0, 0),
        (0, 1, 0), (0, -1, 0),
        (0, 0, 1), (0, 0, -1),
    )
    s = CELL
    pad = 0.0
    for vx, vy, vz in voxels:
        x = vx * CELL + pad
        y = vy * CELL + pad
        z = vz * CELL + pad
        x0, y0, z0 = x, y, z
        x1, y1, z1 = x + s, y + s, z + s
        ctr = (
            vx * CELL + CELL * 0.5,
            vy * CELL + CELL * 0.5,
            vz * CELL + CELL * 0.5,
        )
        for dx, dy, dz in nbr:
            if (vx + dx, vy + dy, vz + dz) in voxels:
                continue
            if dx == 1:
                q = ((x1, y0, z0), (x1, y0, z1), (x1, y1, z1), (x1, y1, z0))
            elif dx == -1:
                q = ((x0, y0, z1), (x0, y0, z0), (x0, y1, z0), (x0, y1, z1))
            elif dy == 1:
                q = ((x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1))
            elif dy == -1:
                q = ((x0, y0, z1), (x1, y0, z1), (x1, y0, z0), (x0, y0, z0))
            elif dz == 1:
                q = ((x0, y0, z1), (x0, y1, z1), (x1, y1, z1), (x1, y0, z1))
            else:
                q = ((x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z0))
            _add_tri(tris, q[0], q[1], q[2], rgb, ctr)
            _add_tri(tris, q[0], q[2], q[3], rgb, ctr)


def _build_mesh(hhmm):
    digits, colon = _voxel_set(hhmm)
    tris = []
    _emit_exposed_faces(tris, digits, DIGIT_RGB)
    _emit_exposed_faces(tris, colon, COLON_RGB)
    return tris


def _orbit_lights(angle):
    """Key light circles the clock; fill sits opposite and lower."""
    ce, se = math.cos(angle), math.sin(angle)
    key = _vnorm((ce, LIGHT_ELEVATION, se))
    fill = _vnorm((-ce * 0.55, 0.22, -se * 0.55))
    return key, fill


def _shade(n, p_world, rgb, cam_z=CAM_Z, key_n=None, fill_n=None):
    if key_n is None:
        key_n, fill_n = _orbit_lights(0.4)
    view = _vnorm((-p_world[0], CAM_Y - p_world[1], cam_z - p_world[2]))
    ndl = max(0.0, _vdot(n, key_n))
    ndf = max(0.0, _vdot(n, fill_n))
    half = _vnorm(_vadd(key_n, view))
    spec = (max(0.0, _vdot(n, half)) ** SPEC_POW) * SPEC_AMT * (0.25 + 0.75 * ndl)
    diff = AMBIENT + KEY_DIFF * ndl + FILL_DIFF * ndf
    fog = 1.0 / (1.0 + 0.012 * max(0.0, p_world[2] + 8.0))
    diff *= fog
    spec *= fog
    r = min(255, int(rgb[0] * diff + SPEC_RGB[0] * spec))
    g = min(255, int(rgb[1] * diff + SPEC_RGB[1] * spec))
    b = min(255, int(rgb[2] * diff + SPEC_RGB[2] * spec))
    return (r, g, b)


def _project(p, rw, rh, focal, cam_z=CAM_Z):
    z = p[2] - cam_z
    if z < 0.35:
        return None
    f = focal / z
    sx = rw * 0.5 + p[0] * f
    sy = rh * 0.5 - (p[1] - CAM_Y) * f
    return (sx, sy, z)


def _raster_tri(zbuf, rbuf, gbuf, bbuf, rw, rh, p0, p1, p2, col):
    x0, y0, z0 = p0
    x1, y1, z1 = p1
    x2, y2, z2 = p2
    minx = max(0, int(math.floor(min(x0, x1, x2))))
    maxx = min(rw - 1, int(math.ceil(max(x0, x1, x2))))
    miny = max(0, int(math.floor(min(y0, y1, y2))))
    maxy = min(rh - 1, int(math.ceil(max(y0, y1, y2))))
    if minx > maxx or miny > maxy:
        return
    area = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
    if abs(area) < 1e-8:
        return
    inv_a = 1.0 / area
    cr, cg, cb = col
    for y in range(miny, maxy + 1):
        py = y + 0.5
        row = y * rw
        for x in range(minx, maxx + 1):
            px = x + 0.5
            w0 = ((x1 - px) * (y2 - py) - (x2 - px) * (y1 - py)) * inv_a
            w1 = ((x2 - px) * (y0 - py) - (x0 - px) * (y2 - py)) * inv_a
            w2 = 1.0 - w0 - w1
            if w0 < 0.0 or w1 < 0.0 or w2 < 0.0:
                continue
            # Perspective-aware z
            z = w0 * z0 + w1 * z1 + w2 * z2
            i = row + x
            if z >= zbuf[i]:
                continue
            zbuf[i] = z
            rbuf[i] = cr
            gbuf[i] = cg
            bbuf[i] = cb


def _zoom_cam_z(t):
    """t=0 speck (far), t=1 full view. Log-space dolly so the pixel grows evenly."""
    t = 0.0 if t < 0.0 else 1.0 if t > 1.0 else t
    a = -CAM_Z_SPECK
    b = -CAM_Z
    return -math.exp(math.log(a) * (1.0 - t) + math.log(b) * t)


def _render(tris, yaw, rw, rh, focal, cam_z=CAM_Z, key_n=None, fill_n=None):
    n = rw * rh
    inf = 1e9
    zbuf = [inf] * n
    rbuf = [0] * n
    gbuf = [0] * n
    bbuf = [0] * n
    cy, sy = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(PITCH), math.sin(PITCH)

    for a, b, c, nrm, rgb in tris:
        aw = _ry(_rx(a, cp, sp), cy, sy)
        bw = _ry(_rx(b, cp, sp), cy, sy)
        cw = _ry(_rx(c, cp, sp), cy, sy)
        nw = _ry(_rx(nrm, cp, sp), cy, sy)
        mid = (
            (aw[0] + bw[0] + cw[0]) / 3.0,
            (aw[1] + bw[1] + cw[1]) / 3.0,
            (aw[2] + bw[2] + cw[2]) / 3.0,
        )
        to_cam = (0.0 - mid[0], CAM_Y - mid[1], cam_z - mid[2])
        if _vdot(nw, to_cam) <= 0.0:
            continue
        pa = _project(aw, rw, rh, focal, cam_z)
        pb = _project(bw, rw, rh, focal, cam_z)
        pc = _project(cw, rw, rh, focal, cam_z)
        if pa is None or pb is None or pc is None:
            continue
        col = _shade(nw, mid, rgb, cam_z, key_n, fill_n)
        _raster_tri(zbuf, rbuf, gbuf, bbuf, rw, rh, pa, pb, pc, col)
    return rbuf, gbuf, bbuf


def _blit(canvas, rbuf, gbuf, bbuf, vw, vh, rw, rh):
    """Box-filter SSAA in linear light so edges don't stair-step as hard."""
    sx = SSAA
    n = float(sx * sx)
    inv_g = 1.0 / 2.2
    canvas.Fill(0, 0, 0)
    for y in range(vh):
        for x in range(vw):
            rs = gs = bs = 0.0
            for oy in range(sx):
                row = (y * sx + oy) * rw
                for ox in range(sx):
                    i = row + x * sx + ox
                    rs += (rbuf[i] / 255.0) ** 2.2
                    gs += (gbuf[i] / 255.0) ** 2.2
                    bs += (bbuf[i] / 255.0) ** 2.2
            canvas.SetPixel(
                x, y,
                min(255, int(((rs / n) ** inv_g) * 255.0 + 0.5)),
                min(255, int(((gs / n) ** inv_g) * 255.0 + 0.5)),
                min(255, int(((bs / n) ** inv_g) * 255.0 + 0.5)),
            )


def PlayClock3D(Duration=0, StopEvent=None, ShowIntro=True):
    vw, vh = _panel_size()
    rw, rh = vw * SSAA, vh * SSAA
    focal = FOCAL * (vw / 64.0) * SSAA
    print("[Clock3D] {}x{}  SSAA={}  {} FPS  (standalone)".format(
        vw, vh, SSAA, TARGET_FPS
    ))

    canvas = getattr(LED, "Canvas", None)
    if canvas is None and getattr(LED, "TheMatrix", None) is not None:
        canvas = LED.TheMatrix.CreateFrameCanvas()
        LED.Canvas = canvas

    hhmm = _now_hhmm()
    tris = _build_mesh(hhmm)
    yaw = YAW
    light_ang = 0.35
    clock = pygame.time.Clock() if HAS_PYGAME else None
    start = time.time()
    last = start
    frame_dt = 1.0 / TARGET_FPS
    if ShowIntro:
        phase = "blank"
        phase_t = 0.0
        cam_u = 0.0
    else:
        phase = "idle"
        phase_t = 0.0
        cam_u = 1.0
    zoom_out_dur = INTRO_ZOOM_SEC
    flipped = False

    try:
        while True:
            if _stop(StopEvent):
                print("[Clock3D] StopEvent")
                return
            if Duration and Duration > 0:
                if (time.time() - start) >= Duration * 60.0:
                    print("[Clock3D] Duration reached")
                    return

            now = time.time()
            dt = now - last
            last = now
            if dt <= 0:
                dt = frame_dt
            dt = min(dt, 2.0 * frame_dt)
            phase_t += dt

            nxt = _now_hhmm()
            skip_draw = False

            if phase == "blank":
                skip_draw = True
                cam_u = 0.0
                if phase_t >= INTRO_BLANK_SEC:
                    phase = "speck"
                    phase_t = 0.0
                    flipped = True
            elif phase == "speck":
                cam_u = 0.0
                if not flipped and nxt != hhmm:
                    hhmm = nxt
                    tris = _build_mesh(hhmm)
                    flipped = True
                    phase_t = 0.0
                    print("[Clock3D] {}".format(hhmm[:2] + ":" + hhmm[2:]))
                hold = INTRO_SPECK_SEC if flipped else SPECK_HOLD_SEC
                if flipped and phase_t >= hold:
                    phase = "zoom_in"
                    phase_t = 0.0
            elif phase == "zoom_in":
                u = min(1.0, phase_t / INTRO_ZOOM_SEC)
                cam_u = _smoothstep(u)
                if u >= 1.0:
                    phase = "idle"
                    phase_t = 0.0
                    cam_u = 1.0
            elif phase == "idle":
                cam_u = 1.0
                lead = _secs_to_minute()
                if lead <= ZOOM_LEAD_SEC:
                    phase = "zoom_out"
                    phase_t = 0.0
                    zoom_out_dur = max(0.55, lead - 0.12)
                    flipped = False
            elif phase == "zoom_out":
                u = min(1.0, phase_t / zoom_out_dur)
                cam_u = _smoothstep(1.0 - u)
                if u >= 1.0:
                    phase = "speck"
                    phase_t = 0.0
                    cam_u = 0.0

            if skip_draw:
                if canvas is not None:
                    canvas.Fill(0, 0, 0)
                    canvas = LED.TheMatrix.SwapOnVSync(canvas)
                    LED.Canvas = canvas
            else:
                cam_z = _zoom_cam_z(cam_u)
                light_ang += LIGHT_ORBIT_SPEED * dt
                if light_ang > math.pi * 2:
                    light_ang -= math.pi * 2
                key_n, fill_n = _orbit_lights(light_ang)
                rbuf, gbuf, bbuf = _render(
                    tris, yaw, rw, rh, focal, cam_z, key_n, fill_n
                )
                if canvas is not None:
                    _blit(canvas, rbuf, gbuf, bbuf, vw, vh, rw, rh)
                    canvas = LED.TheMatrix.SwapOnVSync(canvas)
                    LED.Canvas = canvas

            if clock is not None:
                clock.tick(TARGET_FPS)
            else:
                time.sleep(max(0.0, frame_dt - (time.time() - now)))
    except KeyboardInterrupt:
        print("[Clock3D] Interrupted")


def LaunchClock3D(Duration=0, ShowIntro=True, StopEvent=None):
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
    PlayClock3D(Duration=Duration, StopEvent=StopEvent, ShowIntro=ShowIntro)


if __name__ == "__main__":
    try:
        LaunchClock3D(Duration=0)
    except KeyboardInterrupt:
        print("Exiting Clock 3D.")
