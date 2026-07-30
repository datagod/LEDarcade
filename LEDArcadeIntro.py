# LEDArcadeIntro.py — Spectacular LEDcommander boot title
"""
Multi-layer parallax stars; big letters fire into place from all angles to form
two-line "LED / ARCADE", a specular light shine sweeps across them, then they
hold and fly off before the idle rotation.
"""

from __future__ import annotations

import copy
import math
import random
import time

import LEDarcade as LED

TITLE_LINE1 = "LED"
TITLE_LINE2 = "ARCADE"
TITLE_GAP = 1
TITLE_LINE_GAP = 1
MAX_ZOOM = 4

# Bright primary / primary-ish colors for whole words (picked at random per run)
WORD_COLOR_PALETTE = (
    (255, 40, 40),     # red
    (40, 80, 255),     # blue
    (40, 220, 60),     # green
    (255, 220, 30),    # yellow
    (255, 140, 20),    # orange
    (220, 40, 255),    # magenta
    (30, 230, 255),    # cyan
    (255, 255, 255),   # white
)

LETTER_SPAWN_GAP = 0.22    # seconds between letter launches
FIRE_SPEED = 5.5           # px per step toward rest seat
FIRE_STAGGER = 0.0         # all aim at final seats (no orbit)
# After title locks: brief settle → light sweep → hold → fly off
TITLE_SETTLE_SEC = 0.35    # pause before the shine starts
SHINE_SEC = 0.90           # duration of one light pass across the title
SHINE_BAND = 4.5           # half-width of bright core (screen px)
SHINE_SOFT = 5.0           # soft halo around the core
TITLE_HOLD_SEC = 1.15      # hold after shine before fly-off
FLYOFF_SPEED = 5.0
FADE_SEC = 0.4
MAX_INTRO_SEC = 30.0
MARGIN = 1                 # keep title inset from panel edge


def _stop(StopEvent):
    try:
        return StopEvent is not None and StopEvent.is_set()
    except Exception:
        return False


def _letter_sprite(char):
    ch = char.upper()
    if not ("A" <= ch <= "Z"):
        return None
    idx = ord(ch) - ord("A")
    try:
        return LED.TrimSprite(copy.deepcopy(LED.AlphaSpriteList[idx]))
    except Exception:
        return None


def _sprite_pixels(sprite, zoom, rgb, shadow_rgb):
    pixels = []
    shadow = []
    sw, sh = sprite.width, sprite.height
    for count in range(sw * sh):
        if sprite.grid[count] == 0:
            continue
        y, x = divmod(count, sw)
        for zv in range(zoom):
            for zh in range(zoom):
                pixels.append((x * zoom + zh, y * zoom + zv, rgb))
                shadow.append((x * zoom + zh + 1, y * zoom + zv + 1, shadow_rgb))
    return pixels, shadow, sw * zoom, sh * zoom


def _line_pixel_width(text, zoom, gap):
    total = 0
    for i, ch in enumerate(text):
        sprite = _letter_sprite(ch)
        if sprite is None:
            continue
        total += sprite.width * zoom
        if i < len(text) - 1:
            total += gap
    return total


def _line_pixel_height(text, zoom):
    h = 0
    for ch in text:
        sprite = _letter_sprite(ch)
        if sprite is not None:
            h = max(h, sprite.height * zoom)
    return h


def _fit_title_zoom(panel_w, panel_h):
    """
    Largest integer zoom where LED and ARCADE both fit on two lines
    with margin inside the panel.
    """
    usable_w = panel_w - MARGIN * 2
    usable_h = panel_h - MARGIN * 2
    best = 1
    for z in range(1, MAX_ZOOM + 1):
        gap = max(1, TITLE_GAP)
        line_gap = max(1, TITLE_LINE_GAP)
        w1 = _line_pixel_width(TITLE_LINE1, z, gap)
        w2 = _line_pixel_width(TITLE_LINE2, z, gap)
        h1 = _line_pixel_height(TITLE_LINE1, z)
        h2 = _line_pixel_height(TITLE_LINE2, z)
        total_h = h1 + line_gap + h2
        if max(w1, w2) <= usable_w and total_h <= usable_h:
            best = z
        else:
            break
    return best


class IntroStarField(object):
    """Three-layer parallax star scroll (far / mid / near)."""

    def __init__(self, panel_w, panel_h, seed=19):
        self.panel_w = int(panel_w)
        self.panel_h = int(panel_h)
        rng = random.Random(seed)
        specs = (
            (36, (14, 48), 1.4, 0.22, 22),
            (28, (28, 90), 3.2, 0.50, 30),
            (18, (50, 150), 6.5, 1.05, 45),
        )
        self.layers = []
        for count, (b0, b1), sh, sv, blue in specs:
            stars = []
            for _ in range(count):
                stars.append((
                    rng.uniform(0, self.panel_w),
                    rng.uniform(0, self.panel_h),
                    rng.randint(b0, b1),
                    rng.uniform(0, 2 * math.pi),
                    rng.uniform(0.3, 0.7),
                    blue,
                ))
            self.layers.append({
                "stars": stars,
                "off_h": 0.0,
                "off_v": 0.0,
                "speed_h": sh,
                "speed_v": sv,
            })

    def update(self, dt):
        dt = max(0.0, min(0.05, float(dt)))
        pw = float(self.panel_w)
        ph = float(self.panel_h)
        for layer in self.layers:
            layer["off_h"] = (layer["off_h"] + layer["speed_h"] * dt) % pw
            layer["off_v"] = (layer["off_v"] + layer["speed_v"] * dt) % ph

    def draw(self, canvas, t_sec, fade=1.0):
        fade = max(0.0, min(1.0, float(fade)))
        if fade <= 0.001:
            return
        set_px = canvas.SetPixel
        pw, ph = self.panel_w, self.panel_h
        for layer in self.layers:
            oh, ov = layer["off_h"], layer["off_v"]
            for x, y, bright, phase, pulse, blue in layer["stars"]:
                px = int((x + oh) % pw) % pw
                py = int((y + ov) % ph) % ph
                pulse_amt = 0.82 + 0.18 * (0.5 + 0.5 * math.sin(t_sec * pulse + phase))
                b = max(6, min(200, int(bright * pulse_amt * fade)))
                set_px(
                    px, py,
                    max(0, b * 2 // 5),
                    max(0, b * 3 // 5),
                    max(0, min(255, b + int((blue // 3) * fade))),
                )


class IntroLetter(object):
    """Letter that fires from a random off-screen angle straight into its seat."""

    def __init__(self, char, pixels, shadow, width, height, rest_x, rest_y, panel_w, panel_h):
        self.char = char
        self.pixels = pixels
        self.shadow = shadow
        self.width = width
        self.height = height
        self.rest_x = float(rest_x)
        self.rest_y = float(rest_y)
        self.panel_w = panel_w
        self.panel_h = panel_h
        self.x = 0.0
        self.y = 0.0
        self.state = "waiting"  # waiting → firing → settled → flying → gone
        self.fly_vx = 0.0
        self.fly_vy = 0.0
        self.visible = False
        self._spawn_offscreen()

    def _spawn_offscreen(self):
        """Place start position outside the panel, aiming at rest seat from any angle."""
        # Random angle from rest position; start beyond the panel edge
        ang = random.uniform(0, 2 * math.pi)
        # Distance large enough to clear the panel from rest seat
        dist = max(self.panel_w, self.panel_h) * 0.75 + random.uniform(8, 24)
        self.x = self.rest_x + math.cos(ang) * dist
        self.y = self.rest_y + math.sin(ang) * dist
        # Ensure truly outside (nudge further if still inside margin)
        for _ in range(8):
            if (
                self.x < -self.width - 2
                or self.x > self.panel_w + 2
                or self.y < -self.height - 2
                or self.y > self.panel_h + 2
            ):
                break
            dist += 12
            self.x = self.rest_x + math.cos(ang) * dist
            self.y = self.rest_y + math.sin(ang) * dist

    def start_fire(self):
        self.state = "firing"
        self.visible = True

    def update_fire(self, step):
        """Fly straight toward rest seat; ease in slightly as we approach."""
        dx = self.rest_x - self.x
        dy = self.rest_y - self.y
        dist = math.hypot(dx, dy)
        if dist <= 1.2:
            self.x = self.rest_x
            self.y = self.rest_y
            self.state = "settled"
            return
        # Speed up when far, snap when close
        speed = FIRE_SPEED * (1.15 if dist > 20 else 0.75)
        self.x += (dx / dist) * speed * step
        self.y += (dy / dist) * speed * step
        # Overshoot protection
        if (self.rest_x - self.x) * dx < 0 and (self.rest_y - self.y) * dy < 0:
            self.x = self.rest_x
            self.y = self.rest_y
            self.state = "settled"

    def start_flyoff(self):
        self.state = "flying"
        # Continue outward roughly along approach vector (or random)
        ang = math.atan2(self.y - self.panel_h * 0.5, self.x - self.panel_w * 0.5)
        ang += random.uniform(-0.5, 0.5)
        sp = FLYOFF_SPEED * random.uniform(0.9, 1.4)
        self.fly_vx = math.cos(ang) * sp
        self.fly_vy = math.sin(ang) * sp

    def update_flyoff(self, step):
        self.x += self.fly_vx * step
        self.y += self.fly_vy * step
        if (
            self.x < -30 or self.x > self.panel_w + 30
            or self.y < -30 or self.y > self.panel_h + 30
        ):
            self.visible = False
            self.state = "gone"

    def draw(self, canvas, fade=1.0, shine_pos=None):
        """
        Draw letter. When shine_pos is set, a diagonal band of strong light
        (specular sweep) boosts pixels near that screen coordinate toward white.
        shine_pos is the band center along (x + 0.35*y).
        """
        if not self.visible:
            return
        fade = max(0.0, min(1.0, float(fade)))
        if fade <= 0.001:
            return
        sx, sy = int(round(self.x)), int(round(self.y))
        set_px = canvas.SetPixel
        pw, ph = self.panel_w, self.panel_h
        band = float(SHINE_BAND)
        soft = float(SHINE_SOFT)
        total = band + soft

        def _lit(rgb, px, py):
            r, g, b = rgb[0], rgb[1], rgb[2]
            if shine_pos is not None:
                # Diagonal sweep (slight top-left → bottom-right slant)
                d = abs((px + 0.35 * py) - shine_pos)
                if d < total:
                    if d <= band:
                        t = 1.0 - 0.15 * (d / max(0.01, band))
                    else:
                        t = 1.0 - (d - band) / max(0.01, soft)
                    t = max(0.0, min(1.0, t))
                    t = t * t * (3.0 - 2.0 * t)  # smoothstep
                    # Strong light: lift toward white / hot highlight
                    r = min(255, int(r + (255 - r) * t * 0.98))
                    g = min(255, int(g + (255 - g) * t * 0.95))
                    b = min(255, int(b + (255 - b) * t * 0.90))
                    # Extra punch in the core
                    if d <= band * 0.45:
                        r = min(255, r + 40)
                        g = min(255, g + 40)
                        b = min(255, b + 35)
            return (
                int(r * fade),
                int(g * fade),
                int(b * fade),
            )

        for dx, dy, rgb in self.shadow:
            px, py = sx + dx, sy + dy
            if 0 <= px < pw and 0 <= py < ph:
                rr, gg, bb = _lit(rgb, px, py)
                set_px(px, py, rr, gg, bb)
        for dx, dy, rgb in self.pixels:
            px, py = sx + dx, sy + dy
            if 0 <= px < pw and 0 <= py < ph:
                rr, gg, bb = _lit(rgb, px, py)
                set_px(px, py, rr, gg, bb)


def _pick_word_colors(n_words):
    """
    One bright primary color per word. Prefer distinct colors when the palette
    is large enough; otherwise allow repeats.
    """
    palette = list(WORD_COLOR_PALETTE)
    random.shuffle(palette)
    if n_words <= len(palette):
        return palette[:n_words]
    # More words than palette entries — cycle shuffled palette
    out = []
    while len(out) < n_words:
        random.shuffle(palette)
        out.extend(palette)
    return out[:n_words]


def _build_letters(panel_w, panel_h, zoom):
    gap = max(1, TITLE_GAP)
    line_gap = max(1, TITLE_LINE_GAP)
    lines = [TITLE_LINE1, TITLE_LINE2]
    word_colors = _pick_word_colors(len(lines))
    print(
        "[LEDArcadeIntro] Word colors: "
        + " / ".join(
            "{}={}".format(lines[i], word_colors[i]) for i in range(len(lines))
        )
    )

    line_specs = []
    max_h = 0
    for line_i, line in enumerate(lines):
        # Entire word shares one random bright primary color
        rgb = word_colors[line_i]
        shadow = tuple(max(0, int(c * 0.28)) for c in rgb)
        specs = []
        for ch in line:
            sprite = _letter_sprite(ch)
            if sprite is None:
                continue
            pix, sh, lw, lh = _sprite_pixels(sprite, zoom, rgb, shadow)
            specs.append((ch, pix, sh, lw, lh, rgb))
            max_h = max(max_h, lh)
        if specs:
            line_specs.append(specs)

    if not line_specs:
        return []

    heights = [
        max(s[4] for s in specs) for specs in line_specs
    ]
    total_h = sum(heights) + line_gap * max(0, len(line_specs) - 1)
    top_y = max(MARGIN, (panel_h - total_h) // 2)

    letters = []
    y_cursor = top_y
    for line_i, specs in enumerate(line_specs):
        total_w = sum(s[3] for s in specs) + gap * max(0, len(specs) - 1)
        x_cursor = max(MARGIN, (panel_w - total_w) // 2)
        line_h = heights[line_i]
        for ch, pix, sh, lw, lh, rgb in specs:
            rest_x = x_cursor
            rest_y = y_cursor + (line_h - lh) // 2
            letters.append(IntroLetter(
                ch, pix, sh, lw, lh, rest_x, rest_y, panel_w, panel_h,
            ))
            x_cursor += lw + gap
        y_cursor += line_h + line_gap

    return letters


def PlayLEDArcadeIntro(StopEvent=None):
    """
    Boot title for LEDcommander:
      parallax stars → big letters fire in from all angles → LED/ARCADE → fly off.
    """
    LED.Initialize()
    panel_w = int(getattr(LED, "HatWidth", 64) or 64)
    panel_h = int(getattr(LED, "HatHeight", 32) or 32)

    zoom = _fit_title_zoom(panel_w, panel_h)
    letters = _build_letters(panel_w, panel_h, zoom)
    print(
        f"[LEDArcadeIntro] Title zoom={zoom}  "
        f"LED={_line_pixel_width(TITLE_LINE1, zoom, TITLE_GAP)}px  "
        f"ARCADE={_line_pixel_width(TITLE_LINE2, zoom, TITLE_GAP)}px  "
        f"h={_line_pixel_height(TITLE_LINE1, zoom) + TITLE_LINE_GAP + _line_pixel_height(TITLE_LINE2, zoom)}px"
    )

    try:
        canvas = LED.TheMatrix.CreateFrameCanvas()
    except Exception:
        canvas = LED.Canvas

    stars = IntroStarField(panel_w, panel_h, seed=42)
    if not letters:
        print("[LEDArcadeIntro] No letter sprites — skipping")
        return

    print("[LEDArcadeIntro] Spectacular start — letters fire into place")
    start = time.time()
    last = start
    # fire → settle → shine (light pass) → hold → flyoff → fade
    phase = "fire"
    next_spawn_i = 0
    next_spawn_t = start + 0.25
    settle_start = None
    shine_start = None
    hold_start = None
    fade_start = None
    letter_fade = 1.0
    star_fade = 1.0
    shine_pos = None  # diagonal band center; None = no shine

    # Sweep range covers whole panel with a slight diagonal slant
    shine_start_pos = -SHINE_BAND - SHINE_SOFT - 4.0
    shine_end_pos = panel_w + 0.35 * panel_h + SHINE_BAND + SHINE_SOFT + 4.0

    try:
        while True:
            if _stop(StopEvent):
                break
            now = time.time()
            elapsed = now - start
            if elapsed >= MAX_INTRO_SEC:
                break
            dt = max(0.001, now - last)
            last = now
            step = min(3.0, dt * 30.0)
            stars.update(dt)
            shine_pos = None

            if phase == "fire":
                # Launch next letter from a random off-screen angle
                if next_spawn_i < len(letters) and now >= next_spawn_t:
                    letters[next_spawn_i].start_fire()
                    print(f"[LEDArcadeIntro] Fire '{letters[next_spawn_i].char}'")
                    next_spawn_i += 1
                    next_spawn_t = now + LETTER_SPAWN_GAP
                for L in letters:
                    if L.state == "firing":
                        L.update_fire(step)
                if next_spawn_i >= len(letters) and all(
                    L.state == "settled" for L in letters
                ):
                    phase = "settle"
                    settle_start = now
                    print("[LEDArcadeIntro] Title locked — LED / ARCADE")

            elif phase == "settle":
                for L in letters:
                    L.x, L.y = L.rest_x, L.rest_y
                if now - settle_start >= TITLE_SETTLE_SEC:
                    phase = "shine"
                    shine_start = now
                    print("[LEDArcadeIntro] Shine pass")

            elif phase == "shine":
                for L in letters:
                    L.x, L.y = L.rest_x, L.rest_y
                t = (now - shine_start) / max(0.05, SHINE_SEC)
                # Ease-in-out so the light eases across the face
                te = t * t * (3.0 - 2.0 * t)
                shine_pos = shine_start_pos + (shine_end_pos - shine_start_pos) * te
                if t >= 1.0:
                    phase = "hold"
                    hold_start = now
                    shine_pos = None
                    print("[LEDArcadeIntro] Shine complete — hold")

            elif phase == "hold":
                for L in letters:
                    L.x, L.y = L.rest_x, L.rest_y
                if now - hold_start >= TITLE_HOLD_SEC:
                    phase = "flyoff"
                    for L in letters:
                        L.start_flyoff()
                    print("[LEDArcadeIntro] Letters fly away")

            elif phase == "flyoff":
                for L in letters:
                    if L.state == "flying":
                        L.update_flyoff(step)
                if all(L.state == "gone" or not L.visible for L in letters):
                    phase = "fade"
                    fade_start = now
                    print("[LEDArcadeIntro] Fade stars")

            elif phase == "fade":
                t = (now - fade_start) / max(0.05, FADE_SEC)
                letter_fade = 0.0
                star_fade = max(0.0, 1.0 - t)
                if star_fade <= 0.0:
                    break
            else:
                star_fade = 1.0

            if phase != "fade":
                star_fade = 1.0
                letter_fade = 1.0

            try:
                canvas.Fill(0, 0, 0)
                stars.draw(canvas, elapsed, fade=star_fade)
                for L in letters:
                    L.draw(canvas, fade=letter_fade, shine_pos=shine_pos)
                canvas = LED.TheMatrix.SwapOnVSync(canvas)
            except Exception:
                pass

    except KeyboardInterrupt:
        pass

    try:
        LED.ClearBigLED()
        LED.ClearBuffers()
    except Exception:
        pass
    print("[LEDArcadeIntro] Done — entering rotation")
