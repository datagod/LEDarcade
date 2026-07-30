# =====================================================================================
# SEVEN-SEG CLOCK — pinball apron style + date line
#
# Time: exact copy of Pinball's medium 7-segment digits (5×9, thick 1, ghost dim).
# Layout: HH:MM in the upper area; date string below ("Thu July 30" style).
#
# Launch: LEDsim key 4 / LEDpanel / action "sevensegclock"
# =====================================================================================

from __future__ import annotations

import time
from datetime import datetime

import LEDarcade as LED

LED.Initialize()

try:
    import pygame
    HAS_PYGAME = True
except Exception:
    HAS_PYGAME = False


# ---- Exact pinball apron clock constants (Pinball2.py) ----
CLOCK_RGB = (255, 36, 28)           # lit LED red
CLOCK_DIM = (55, 12, 10)            # unlit segment ghost
CLOCK_DIGIT_W = 5
CLOCK_DIGIT_H = 9
CLOCK_THICK = 1
CLOCK_GAP = 1
CLOCK_COLON_W = 2

# Date line (Alpha / Digit sprites, same banner font as other LEDarcade clocks)
DATE_RGB = (200, 80, 50)
DATE_GAP_FROM_CLOCK = 4           # pixels between clock bottom and date top

# 7-segment masks: bit0=A top, B UR, C LR, D bot, E LL, F UL, G mid
_SEG_A, _SEG_B, _SEG_C, _SEG_D = 0x01, 0x02, 0x04, 0x08
_SEG_E, _SEG_F, _SEG_G = 0x10, 0x20, 0x40
_SEG_DIGIT_MASKS = (
    0x3F,  # 0  ABCDEF
    0x06,  # 1  BC
    0x5B,  # 2  ABDEG
    0x4F,  # 3  ABCDG
    0x66,  # 4  BCFG
    0x6D,  # 5  ACDFG
    0x7D,  # 6  ACDEFG
    0x07,  # 7  ABC
    0x7F,  # 8  ABCDEFG
    0x6F,  # 9  ABCDFG
)

BG = (0, 0, 0)
TARGET_FPS = 12
USE_24H = True


def _stop(StopEvent):
    try:
        return StopEvent is not None and StopEvent.is_set()
    except Exception:
        return False


def _clock_total_width():
    """Pixel width of HH:MM in medium 7-seg layout (same as pinball)."""
    return 4 * CLOCK_DIGIT_W + 3 * CLOCK_GAP + CLOCK_COLON_W


def _set_px(canvas, x, y, rgb, width, height):
    if 0 <= x < width and 0 <= y < height:
        canvas.SetPixel(int(x), int(y), int(rgb[0]), int(rgb[1]), int(rgb[2]))


def _draw_7seg_digit(canvas, ox, oy, digit, lit_rgb, dim_rgb, width, height):
    """
    Draw one medium 7-element LED digit at screen (ox, oy) top-left.

    Exact pinball layout (w=5, h=9, thick=1):
        A A A
      F       B
      F       B
        G G G
      E       C
      E       C
        D D D
    """
    w = CLOCK_DIGIT_W
    h = CLOCK_DIGIT_H
    t = CLOCK_THICK
    mid = h // 2
    hx0, hx1 = t, w - 1 - t
    vy0_top, vy1_top = t, mid - 1
    vy0_bot, vy1_bot = mid + t, h - 1 - t
    mask = _SEG_DIGIT_MASKS[int(digit) % 10]

    segs = (
        (_SEG_A, "h", hx0, hx1, 0),
        (_SEG_G, "h", hx0, hx1, mid),
        (_SEG_D, "h", hx0, hx1, h - t),
        (_SEG_F, "v", 0, vy0_top, vy1_top),
        (_SEG_B, "v", w - t, vy0_top, vy1_top),
        (_SEG_E, "v", 0, vy0_bot, vy1_bot),
        (_SEG_C, "v", w - t, vy0_bot, vy1_bot),
    )
    for bit, kind, a, b, c in segs:
        on = (mask & bit) != 0
        if on:
            rgb = lit_rgb
        elif dim_rgb is not None:
            rgb = dim_rgb
        else:
            continue
        if kind == "h":
            for yy in range(c, c + t):
                for xx in range(a, b + 1):
                    _set_px(canvas, ox + xx, oy + yy, rgb, width, height)
        else:
            for xx in range(a, a + t):
                for yy in range(b, c + 1):
                    _set_px(canvas, ox + xx, oy + yy, rgb, width, height)


def _draw_7seg_clock_row(canvas, ox, oy, digits, blink_on, width, height):
    """Red 7-segment HH:MM — pinball apron drawing path."""
    lit = CLOCK_RGB
    dim = CLOCK_DIM
    x = ox
    _draw_7seg_digit(canvas, x, oy, digits[0], lit, dim, width, height)
    x += CLOCK_DIGIT_W + CLOCK_GAP
    _draw_7seg_digit(canvas, x, oy, digits[1], lit, dim, width, height)
    x += CLOCK_DIGIT_W + CLOCK_GAP
    colon_x = x
    mid = CLOCK_DIGIT_H // 2
    if blink_on:
        for dy in (mid - 2, mid + 1):
            for xx in range(CLOCK_COLON_W):
                _set_px(canvas, colon_x + xx, oy + dy, lit, width, height)
    x += CLOCK_COLON_W + CLOCK_GAP
    _draw_7seg_digit(canvas, x, oy, digits[2], lit, dim, width, height)
    x += CLOCK_DIGIT_W + CLOCK_GAP
    _draw_7seg_digit(canvas, x, oy, digits[3], lit, dim, width, height)


def _now_digits():
    now = time.localtime()
    hour = now.tm_hour
    if not USE_24H:
        hour = hour % 12
        if hour == 0:
            hour = 12
    return (
        hour // 10, hour % 10,
        now.tm_min // 10, now.tm_min % 10,
    )


def _date_candidates():
    """
    Prefer 'Thu July 30'; fall back to shorter forms if the banner is too wide.
    Banner font is uppercase (Alpha sprites).
    """
    now = datetime.now()
    day = str(now.day)
    full = f"{now.strftime('%a')} {now.strftime('%B')} {day}"        # Thu July 30
    short_month = f"{now.strftime('%a')} {now.strftime('%b')} {day}"  # Thu Jul 30
    return (full, short_month)


def _build_date_sprite(max_width):
    """LEDarcade 5-row alpha/digit banner; pick longest form that fits."""
    last = (None, "")
    for text in _date_candidates():
        try:
            spr = LED.CreateBannerSprite(text)
            try:
                spr = LED.LeftTrimSprite(spr, 1)
            except Exception:
                pass
            w = int(getattr(spr, "width", 0) or 0)
            if w <= 0:
                continue
            last = (spr, text)
            if w <= max_width:
                print(f"[SevenSegClock] date: {text}  ({w}px)")
                return spr, text
        except Exception as exc:
            print(f"[SevenSegClock] date sprite failed for '{text}': {exc}")
    spr, text = last
    if spr is not None:
        print(
            f"[SevenSegClock] date (wide): {text}  "
            f"({getattr(spr, 'width', '?')}px)"
        )
    return spr, text


def _draw_banner(canvas, sprite, h, v, rgb, width, height):
    """Paint a banner sprite onto the frame canvas at (h, v)."""
    if sprite is None:
        return
    try:
        LED.CopySpriteToCanvasZoom(
            sprite, h, v, rgb, (0, 0, 0),
            ZoomFactor=1, Fill=False, Canvas=canvas,
        )
        return
    except Exception:
        pass
    sw = int(getattr(sprite, "width", 0) or 0)
    sh = int(getattr(sprite, "height", 0) or 0)
    grid = getattr(sprite, "grid", None)
    if not grid or sw <= 0 or sh <= 0:
        return
    for count in range(min(len(grid), sw * sh)):
        if not grid[count]:
            continue
        y, x = divmod(count, sw)
        _set_px(canvas, h + x, v + y, rgb, width, height)


def draw_face(canvas, width, height, date_sprite, blink_on=True):
    canvas.Fill(BG[0], BG[1], BG[2])

    # --- Time: upper area, centered, pinball 7-seg size ---
    total_w = _clock_total_width()
    clock_ox = max(0, (width - total_w) // 2)
    # Upper area — small top pad
    clock_oy = max(2, height // 6)

    digits = _now_digits()
    _draw_7seg_clock_row(
        canvas, clock_ox, clock_oy, digits, blink_on, width, height,
    )

    # --- Date: below the clock, centered ---
    if date_sprite is not None:
        date_h = int(getattr(date_sprite, "height", 5) or 5)
        date_w = int(getattr(date_sprite, "width", 0) or 0)
        date_ox = max(0, (width - date_w) // 2)
        date_oy = clock_oy + CLOCK_DIGIT_H + DATE_GAP_FROM_CLOCK
        if date_oy + date_h > height - 1:
            date_oy = max(0, height - 1 - date_h)
        _draw_banner(canvas, date_sprite, date_ox, date_oy, DATE_RGB, width, height)


def PlaySevenSegClock(Duration=5, StopEvent=None):
    """Full-panel clock: pinball 7-seg HH:MM + date. Duration in minutes."""
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
        run_min = 5.0
    if run_min <= 0:
        run_min = 5.0

    tick = pygame.time.Clock() if HAS_PYGAME else None
    last_date_key = None
    date_sprite = None

    print(
        f"[SevenSegClock] {width}x{height}  "
        f"digit={CLOCK_DIGIT_W}x{CLOCK_DIGIT_H} (pinball apron style)  "
        f"HH:MM + date  duration={run_min} min"
    )

    try:
        while True:
            if _stop(StopEvent):
                print("[SevenSegClock] StopEvent — exit")
                break
            if time.time() - start > run_min * 60.0:
                print("[SevenSegClock] Duration reached — exit")
                break

            date_key = datetime.now().strftime("%Y-%m-%d")
            if date_key != last_date_key:
                last_date_key = date_key
                date_sprite, _text = _build_date_sprite(max_width=width - 2)

            blink_on = (int(time.time()) % 2) == 0
            draw_face(canvas, width, height, date_sprite, blink_on=blink_on)
            try:
                canvas = LED.TheMatrix.SwapOnVSync(canvas)
                LED.Canvas = canvas
            except Exception:
                pass

            if tick:
                tick.tick(TARGET_FPS)
            else:
                time.sleep(1.0 / TARGET_FPS)
    except KeyboardInterrupt:
        print("[SevenSegClock] Interrupted")

    try:
        LED.ClearBuffers()
        LED.TheMatrix.Clear()
    except Exception:
        pass


def LaunchSevenSegClock(Duration=5, ShowIntro=False, StopEvent=None):
    try:
        LED.LoadConfigData()
    except Exception:
        pass
    PlaySevenSegClock(Duration=Duration, StopEvent=StopEvent)


if __name__ == "__main__":
    try:
        LaunchSevenSegClock(Duration=60, StopEvent=None)
    except KeyboardInterrupt:
        print("Exiting SevenSegClock.")
