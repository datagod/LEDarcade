# =====================================================================================
# NIGHT DRIVER — 1976-style first-person night drive
#
# Black screen. White roadside pylons start as specks at the horizon and grow as
# they rush the camera. Auto-play steers to stay between the posts.
#
# Launch: LEDpanel / LEDcommander "launch_nightdriver" / standalone
# =====================================================================================

from __future__ import annotations

import math
import random
import time
from collections import deque

import LEDarcade as LED

LED.Initialize()

try:
    import pygame
    HAS_PYGAME = True
except Exception:
    HAS_PYGAME = False


# ---- Panel ----
# High present rate so pylons step ~1px instead of jumping rows.
TARGET_FPS = 90
VIEW_W = int(getattr(LED, "HatWidth", 64) or 64)
VIEW_H = int(getattr(LED, "HatHeight", 32) or 32)

HORIZON_Y = 8
Y_BOTTOM = 30

# Perspective (world units). Near posts sit at the bottom; far posts meet
# at a 1-pixel vanishing point — the classic Night Driver cheat.
Z_NEAR = 1.00
Z_FAR = 20.0
FOCAL = 13.0
POST_SPACING = 1.55
ROAD_HALF = 1.20
ROAD_HALF_MIN = 0.78

# Motion — tuned so near posts move about 1 screen pixel per frame at 90 FPS.
SPEED_CRUISE = 3.2
SPEED_FAST = 3.9
SPEED_SLOW = 2.2
MAX_LATERAL = 1.6          # world units / sec
AI_LOOK_NEAR = 4.5
AI_LOOK_FAR = 9.0
AI_LAG = 5.5               # 1/sec toward desired line
AI_WOBBLE = 0.02
CAM_LAG = 6.0              # camera hugs the car so the horizon is free to swing
CAR_HALF_WORLD = 0.28
CAR_MARGIN = 3             # keep the 7-wide hood on-panel
# Night Driver cheat: true 1/z barely moves the horizon. Amplify the bend
# between hood and vanishing point so far pylons walk left/right.
VP_PX_PER_UNIT = 5.8
VP_MAX = 18.0

STAR_COUNT = 14
HEADLIGHT_RGB = (255, 255, 180)
HOOD_RGB = (28, 36, 22)
HOOD_HI_RGB = (50, 62, 40)
WHEEL_RGB = (12, 12, 12)

INTRO_SEC = 2.4
TITLE_RGB = (240, 240, 255)

# Tiny dim HH:MM — 3×5 digits, upper left
CLOCK_X = 0
CLOCK_Y = 0
CLOCK_RGB = (20, 20, 24)


def _stop(StopEvent):
    try:
        return StopEvent is not None and StopEvent.is_set()
    except Exception:
        return False


def _clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def _panel_size():
    w = int(getattr(LED, "HatWidth", 64) or 64)
    h = int(getattr(LED, "HatHeight", 32) or 32)
    return max(16, w), max(16, h)


def _put(canvas, x, y, rgb, vw, vh):
    xi, yi = int(x), int(y)
    if 0 <= xi < vw and 0 <= yi < vh:
        canvas.SetPixel(xi, yi, int(rgb[0]), int(rgb[1]), int(rgb[2]))


def _rect(canvas, x0, y0, w, h, rgb, vw, vh):
    x0 = int(round(x0))
    y0 = int(round(y0))
    w = max(1, int(w))
    h = max(1, int(h))
    r, g, b = int(rgb[0]), int(rgb[1]), int(rgb[2])
    for yy in range(y0, y0 + h):
        if yy < 0 or yy >= vh:
            continue
        for xx in range(x0, x0 + w):
            if 0 <= xx < vw:
                canvas.SetPixel(xx, yy, r, g, b)


def _blit_banner(canvas, text, cx, cy, rgb, vw, vh):
    try:
        spr = LED.CreateBannerSprite(str(text))
    except Exception:
        return
    grid = getattr(spr, "grid", None)
    if not grid:
        return
    h0 = int(cx - spr.width // 2)
    v0 = int(cy - spr.height // 2)
    r, g, b = int(rgb[0]), int(rgb[1]), int(rgb[2])
    for count in range(spr.width * spr.height):
        try:
            on = grid[count] == 1
        except Exception:
            continue
        if not on:
            continue
        y, x = divmod(count, spr.width)
        px, py = h0 + x, v0 + y
        if 0 <= px < vw and 0 <= py < vh:
            canvas.SetPixel(px, py, r, g, b)


def _project_k():
    denom = (1.0 / Z_NEAR) - (1.0 / Z_FAR)
    return (Y_BOTTOM - HORIZON_Y) / denom if denom else 1.0


def _project(wx, cam_x, z, vw, k=None, vp_extra=0.0):
    """World (x, z) → screen (sx, sy, scale). None if behind camera.

    Past the hood (z < Z_NEAR) perspective is frozen and Y continues linearly
    so pylons slide off the bottom one pixel at a time instead of popping out.

    vp_extra (pixels) is added at the horizon and fades to 0 at the hood —
    that's the moving vanishing point that reads as a curve.
    """
    if z <= 0.12:
        return None
    if k is None:
        k = _project_k()
    z_x = max(z, Z_NEAR)
    scale = FOCAL / z_x
    sx = vw * 0.5 + (wx - cam_x) * scale
    if z >= Z_NEAR:
        t = _clamp((z - Z_NEAR) / (Z_FAR - Z_NEAR), 0.0, 1.0)
        sx += vp_extra * (t ** 0.55)
        sy = HORIZON_Y + k * ((1.0 / z) - (1.0 / Z_FAR))
    else:
        sy = Y_BOTTOM + (Z_NEAR - z) * (k / (Z_NEAR * Z_NEAR))
    return sx, sy, scale


def _draw_digit3x5(canvas, digit, x, y, rgb, vw, vh):
    try:
        grid = LED.DigitList[int(digit) % 10]
    except Exception:
        return
    for i, on in enumerate(grid):
        if not on:
            continue
        yy, xx = divmod(i, 3)
        _put(canvas, x + xx, y + yy, rgb, vw, vh)


def _draw_hhmm(canvas, vw, vh):
    """Smallest 3×5 HH:MM in the upper-left corner."""
    hhmm = time.strftime("%H%M")
    x, y = CLOCK_X, CLOCK_Y
    rgb = CLOCK_RGB
    _draw_digit3x5(canvas, hhmm[0], x, y, rgb, vw, vh)
    x += 4
    _draw_digit3x5(canvas, hhmm[1], x, y, rgb, vw, vh)
    x += 3
    _put(canvas, x, y + 1, rgb, vw, vh)
    _put(canvas, x, y + 3, rgb, vw, vh)
    x += 2
    _draw_digit3x5(canvas, hhmm[2], x, y, rgb, vw, vh)
    x += 4
    _draw_digit3x5(canvas, hhmm[3], x, y, rgb, vw, vh)


def _post_rgb(z):
    """Far posts dimmer so the horizon is a vanishing speck, not noise."""
    t = _clamp((Z_FAR - z) / (Z_FAR - Z_NEAR), 0.0, 1.0)
    t = t ** 0.62
    b = int(78 + 177 * t)
    return (b, b, int(b * 0.95))


class NightWorld(object):
    def __init__(self, vw, vh):
        self.vw = vw
        self.vh = vh
        self.s = 0.0
        self.x = 0.0              # car world x (follows the road at the hood)
        self.cam_x = 0.0          # camera world x (hugs the car)
        self.car_sx = None        # last on-screen car x; steps 1px toward the road
        self.vp_px = 0.0          # horizon swing in pixels (moving vanishing point)
        self.speed = SPEED_CRUISE
        self.steer = 0.0
        self.curv = 0.0
        self.curv_target = 0.0
        self.curv_hold = 6.0
        self.spawn_center = 0.0
        self.next_post_s = 0.0
        self.road_half = ROAD_HALF
        self.centers = deque()          # (s, center, half)
        self.posts = deque()            # {s, x}
        self.stars = []
        self.miles = 0.0
        self.ai_line = 0.0
        self.proj_k = _project_k()
        # World step that moves a hood-distance post by ~1 screen pixel
        self.max_ds = (Z_NEAR * Z_NEAR) / max(self.proj_k, 1e-6)
        self._seed_stars()
        self._fill_ahead()

    def _seed_stars(self):
        self.stars = []
        for _ in range(STAR_COUNT):
            self.stars.append((
                random.randint(0, self.vw - 1),
                random.randint(0, max(0, HORIZON_Y - 1)),
                random.randint(10, 28),
            ))

    def _roll_curve(self):
        r = random.random()
        if r < 0.38:
            self.curv_target = 0.0
            self.curv_hold = random.uniform(7.0, 18.0)
        elif r < 0.86:
            self.curv_target = random.choice((-1.0, 1.0)) * random.uniform(0.07, 0.20)
            self.curv_hold = random.uniform(5.5, 13.0)
        else:
            self.curv_target = random.choice((-1.0, 1.0)) * random.uniform(0.26, 0.40)
            self.curv_hold = random.uniform(3.8, 7.5)

    def _spawn_pair(self, s):
        self.curv_hold -= POST_SPACING
        if self.curv_hold <= 0:
            self._roll_curve()
        self.curv += (self.curv_target - self.curv) * 0.28
        self.spawn_center += self.curv * POST_SPACING
        half = self.road_half
        self.centers.append((s, self.spawn_center, half))
        self.posts.append({"s": s, "x": self.spawn_center - half})
        self.posts.append({"s": s, "x": self.spawn_center + half})
        self.next_post_s = s + POST_SPACING

    def _fill_ahead(self):
        s = self.s + Z_NEAR
        while s <= self.s + Z_FAR + POST_SPACING:
            self._spawn_pair(s)
            s += POST_SPACING

    def center_at(self, s):
        samples = self.centers
        if not samples:
            return 0.0, self.road_half
        if s <= samples[0][0]:
            return samples[0][1], samples[0][2]
        if s >= samples[-1][0]:
            return samples[-1][1], samples[-1][2]
        prev = samples[0]
        for nxt in samples:
            if nxt[0] >= s:
                ds = nxt[0] - prev[0]
                t = 0.0 if ds <= 1e-6 else (s - prev[0]) / ds
                c = prev[1] + (nxt[1] - prev[1]) * t
                h = prev[2] + (nxt[2] - prev[2]) * t
                return c, h
            prev = nxt
        return samples[-1][1], samples[-1][2]

    def _prune(self):
        # Keep pylons until they have scrolled fully off the bottom of the panel.
        post_cut = self.s + 0.20
        while self.posts and self.posts[0]["s"] < post_cut:
            self.posts.popleft()
        center_cut = self.s + Z_NEAR - 2.0
        while self.centers and self.centers[0][0] < center_cut:
            self.centers.popleft()

    def _ai_steer(self, dt):
        # Sit in the gap between the near posts; glance a little ahead for curves.
        c_hood, _ = self.center_at(self.s + Z_NEAR)
        c_n, _ = self.center_at(self.s + AI_LOOK_NEAR)
        desired = c_hood * 0.72 + c_n * 0.28
        desired -= self.curv * 0.25
        self.ai_line += (desired - self.ai_line) * (1.0 - math.exp(-AI_LAG * dt))
        self.ai_line += random.uniform(-AI_WOBBLE, AI_WOBBLE)
        err = self.ai_line - self.x
        self.steer = _clamp(err * 2.15, -MAX_LATERAL, MAX_LATERAL)

    def step(self, dt):
        # Narrow slowly, like the coin-op tracks
        self.road_half = max(
            ROAD_HALF_MIN,
            ROAD_HALF - self.s * 0.00055,
        )

        if abs(self.curv) < 0.04:
            target_speed = SPEED_FAST
        elif abs(self.curv) > 0.24:
            target_speed = SPEED_SLOW
        else:
            target_speed = SPEED_CRUISE
        self.speed += (target_speed - self.speed) * min(1.0, dt * 1.8)

        self._ai_steer(dt)
        # Cap lateral shift so posts don't jump sideways more than ~1px
        max_dx = (Z_NEAR / FOCAL) * 1.0
        dx = _clamp(self.steer * dt, -max_dx, max_dx)
        self.x += dx

        # Camera stays with the car so the *upcoming* road can leave center —
        # that offset is the curve. A little look-ahead keeps the car sliding.
        c_look, _ = self.center_at(self.s + AI_LOOK_FAR)
        cam_target = self.x * 0.82 + c_look * 0.18
        cam_step = (cam_target - self.cam_x) * (1.0 - math.exp(-CAM_LAG * dt))
        self.cam_x += _clamp(cam_step, -max_dx, max_dx)

        # Vanishing point: how much the road has bent from hood to horizon.
        c_hood, _ = self.center_at(self.s + Z_NEAR)
        c_horizon, _ = self.center_at(self.s + Z_FAR)
        target_vp = _clamp(
            (c_horizon - c_hood) * VP_PX_PER_UNIT, -VP_MAX, VP_MAX
        )
        if target_vp > self.vp_px:
            self.vp_px = min(self.vp_px + 1.0, target_vp)
        elif target_vp < self.vp_px:
            self.vp_px = max(self.vp_px - 1.0, target_vp)

        # Cap forward step so near pylons don't skip rows
        ds = min(self.speed * dt, self.max_ds)
        self.s += ds
        self.miles += ds * 0.012

        while self.next_post_s < self.s + Z_FAR + POST_SPACING:
            self._spawn_pair(self.next_post_s)
        self._prune()

        # Stay on the road — pull back, no flash
        c_hood, half = self.center_at(self.s + Z_NEAR)
        lim = max(0.08, half - CAR_HALF_WORLD)
        self.x = _clamp(self.x, c_hood - lim, c_hood + lim)

    def draw(self, canvas, title_fade=0.0):
        vw, vh = self.vw, self.vh
        canvas.Fill(0, 0, 0)

        for sx, sy, b in self.stars:
            canvas.SetPixel(sx, sy, b, b, min(255, b + 6))

        k = self.proj_k
        items = []
        for p in self.posts:
            z = p["s"] - self.s
            if 0.12 < z < Z_FAR:
                items.append((z, p["x"]))
        items.sort(key=lambda it: -it[0])

        for z, wx in items:
            pr = _project(wx, self.cam_x, z, vw, k=k, vp_extra=self.vp_px)
            if pr is None:
                continue
            sx, sy, _scale = pr
            grow = Z_NEAR / max(z, Z_NEAR)
            w = 1 if grow < 1.35 else 2
            h = max(1, int(round(5.0 * grow)))
            # Clip off the bottom; don't pop when the foot hits the last row.
            if sy - h >= vh:
                continue
            if sy < HORIZON_Y - 1:
                continue
            rgb = _post_rgb(z)
            _rect(canvas, sx - w * 0.5, sy - h, w, h, rgb, vw, vh)

        self._draw_car(canvas)

        if title_fade > 0.01:
            fade = _clamp(title_fade, 0.0, 1.0)
            rgb = (
                int(TITLE_RGB[0] * fade),
                int(TITLE_RGB[1] * fade),
                int(TITLE_RGB[2] * fade),
            )
            _blit_banner(canvas, "NITE", vw // 2, 3, rgb, vw, vh)
            _blit_banner(canvas, "DRIVE", vw // 2, 11, rgb, vw, vh)

        self._draw_clock(canvas)

    def _draw_clock(self, canvas):
        _draw_hhmm(canvas, self.vw, self.vh)

    def _draw_car(self, canvas):
        vw, vh = self.vw, self.vh
        pr = _project(
            self.x, self.cam_x, Z_NEAR, vw, k=self.proj_k, vp_extra=self.vp_px
        )
        target = int(round(pr[0])) if pr is not None else vw // 2
        target = _clamp(target, CAR_MARGIN, vw - 1 - CAR_MARGIN)
        if self.car_sx is None:
            self.car_sx = target
        elif target > self.car_sx:
            self.car_sx += 1
        elif target < self.car_sx:
            self.car_sx -= 1
        cx = self.car_sx
        by = vh - 1
        _put(canvas, cx - 3, by, WHEEL_RGB, vw, vh)
        _put(canvas, cx + 3, by, WHEEL_RGB, vw, vh)
        for dx in range(-3, 4):
            _put(canvas, cx + dx, by - 1, HOOD_RGB, vw, vh)
        for dx in range(-2, 3):
            _put(canvas, cx + dx, by - 2, HOOD_HI_RGB, vw, vh)
        _put(canvas, cx - 2, by - 3, HEADLIGHT_RGB, vw, vh)
        _put(canvas, cx + 2, by - 3, HEADLIGHT_RGB, vw, vh)


def _elapsed_minutes(start):
    try:
        _, minutes, _ = LED.GetElapsedTime(start, time.time())
        return float(minutes)
    except Exception:
        return (time.time() - start) / 60.0


def PlayNightDriver(Duration=5, StopEvent=None, ShowIntro=True):
    global VIEW_W, VIEW_H
    VIEW_W, VIEW_H = _panel_size()
    print("[NightDriver] {}x{}  auto-play  {} FPS  duration={} min".format(
        VIEW_W, VIEW_H, TARGET_FPS, Duration
    ))

    world = NightWorld(VIEW_W, VIEW_H)
    canvas = LED.Canvas
    if canvas is None and LED.TheMatrix is not None:
        canvas = LED.TheMatrix.CreateFrameCanvas()
        LED.Canvas = canvas

    clock = pygame.time.Clock() if HAS_PYGAME else None
    start = time.time()
    last = start
    intro_left = INTRO_SEC if ShowIntro else 0.0
    frame_dt = 1.0 / TARGET_FPS

    try:
        while True:
            if _stop(StopEvent):
                print("[NightDriver] StopEvent")
                return
            if Duration and Duration > 0 and _elapsed_minutes(start) >= Duration:
                print("[NightDriver] Duration reached ({:.1f} min)".format(
                    Duration
                ))
                return

            now = time.time()
            dt = now - last
            last = now
            if dt <= 0:
                dt = frame_dt
            # Never simulate more than two frames — late frames hitch, they
            # do not jump pylons several pixels.
            dt = min(dt, frame_dt * 2.0)

            world.step(dt)
            intro_left = max(0.0, intro_left - dt)
            if intro_left > 0.7:
                fade = 1.0
            elif intro_left > 0:
                fade = intro_left / 0.7
            else:
                fade = 0.0

            if canvas is None:
                time.sleep(frame_dt)
                continue
            world.draw(canvas, title_fade=fade)
            canvas = LED.TheMatrix.SwapOnVSync(canvas)
            LED.Canvas = canvas

            if clock is not None:
                clock.tick(TARGET_FPS)
            else:
                time.sleep(max(0.0, frame_dt - (time.time() - now)))
    except KeyboardInterrupt:
        print("[NightDriver] Interrupted")


def LaunchNightDriver(Duration=5, ShowIntro=True, StopEvent=None):
    try:
        LED.LoadConfigData()
    except Exception:
        pass
    try:
        LED.ClearBigLED()
        LED.ClearBuffers()
    except Exception:
        pass
    if _stop(StopEvent):
        return
    PlayNightDriver(Duration=Duration, StopEvent=StopEvent, ShowIntro=ShowIntro)


if __name__ == "__main__":
    try:
        LaunchNightDriver(Duration=0, ShowIntro=True, StopEvent=None)
    except KeyboardInterrupt:
        print("Exiting Night Driver.")
