#!/usr/bin/env python
#------------------------------------------------------------------------------
#  LEDTV — LED matrix television effects
#
#  Default channel-surf loop (effect=channels):
#    1. "LEDTV" letters drop from the sky (Skyfall-style intro)
#    2. Analog static for 3 seconds
#    3. Channel flash 2–5 times (1 second each, CHn up/down)
#    4. Random local video for 30 seconds
#    5. Channel up or down; repeat from (3) until duration ends
#
#  Other effects:
#    white_noise  — classic analog static with green CHn overlay
#    color_bars   — SMPTE-style off-air color bars with green CHn
#    youtube      — stream a YouTube URL or play a local video file
#
#  Local videos live in videos/ (gitignored). Drop .mp4/.webm/etc. there.
#
#  Run:  sudo python3 LEDtv.py
#        sudo python3 LEDtv.py --duration 5
#        sudo python3 LEDtv.py --youtube 'https://www.youtube.com/watch?v=...'
#  Or:   launch_ledtv via LEDcommander / LEDpanel / Twitch ?tv
#------------------------------------------------------------------------------

from __future__ import print_function

import copy
import glob
import os
import random
import shutil
import subprocess
import sys
import threading
import time

import numpy as np
from PIL import Image, ImageSequence

import LEDarcade as LED

LED.Initialize()

# --- display ---
WIDTH = LED.HatWidth
HEIGHT = LED.HatHeight
_HERE = os.path.dirname(os.path.abspath(__file__))
GIF_DIR = os.path.join(_HERE, "images")
VIDEO_DIR = os.path.join(_HERE, "videos")
GIF_FRAME_SLEEP = 0.06       # default delay between GIF frames
GIF_LOOPS_EACH = 2           # full plays of one GIF before picking another
GIF_BETWEEN_BARS_SEC = 0.35  # brief black between channel items
VIDEO_EXTS = (".mp4", ".webm", ".mkv", ".mov", ".avi", ".m4v")

# --- session defaults ---
DEFAULT_DURATION_MIN = 5.0   # commander / Twitch / LaunchLEDtv default
# Standalone CLI (python LEDtv.py) runs until killed unless --duration is set
STANDALONE_DURATION_MIN = 100000.0

# --- channel-surf timing ---
STATIC_BOOT_SEC = 3.0        # static at start (after title)
CHANNEL_FLASH_SEC = 2.0      # momentary video per channel change (if previews on)
CHANNEL_FLASH_MIN = 2
CHANNEL_FLASH_MAX = 5
# 2s channel-preview clips (off by default; surf = sequential landed channels)
CHANNEL_PREVIEWS_ENABLED = False
# How long each landed channel stays on after boot warmup (title + static)
CHANNEL_DWELL_MIN_SEC = 10.0
CHANNEL_DWELL_MAX_SEC = 10.0
CHANNEL_DWELL_SEC = 10.0     # fixed dwell after initial warmup
VIDEO_PLAY_SEC = 10.0        # legacy alias; prefer channel_dwell_sec()
CHANNEL_BUG_SHOW_SEC = 3.0   # CHn visible this long after landing; hide until next change
# Black interstitial between channels (0 = seamless cut; CHn is on the content)
CHANNEL_CHANGE_FLASH_SEC = 0.0
# How long to wait for ffmpeg to die after kill (keep short to avoid pause)
FFMPEG_KILL_WAIT_SEC = 0.25

# --- youtube / video ---
# Low FPS keeps the Pi and the 64x32 readable; bump if the board can take it
VIDEO_FPS = 12
VIDEO_FRAME_BYTES = WIDTH * HEIGHT * 3
# Prefer a recent yt-dlp binary if present
_YT_DLP_CANDIDATES = (
    "/usr/local/bin/yt-dlp",
    "/usr/bin/yt-dlp",
    shutil.which("yt-dlp") or "",
)
_FFMPEG = shutil.which("ffmpeg") or "/usr/bin/ffmpeg"
_FFPROBE = shutil.which("ffprobe") or "/usr/bin/ffprobe"
# Cache of probed durations (path → seconds); avoids re-probing every surf
_DURATION_CACHE = {}

# --- white noise ---
NOISE_FPS = 30
NOISE_MIN = 8
NOISE_MAX = 255
NOISE_SALT_CHANCE = 0.04
NOISE_PEPPER_CHANCE = 0.03

# --- color bars (SMPTE-inspired, sized for small matrices) ---
# 75% bars (classic broadcast look, not blown-out 100%)
_BAR_W = 191  # ~75% of 255
COLOR_BARS_TOP = (
    (_BAR_W, _BAR_W, _BAR_W),  # gray / white
    (_BAR_W, _BAR_W, 0),       # yellow
    (0, _BAR_W, _BAR_W),       # cyan
    (0, _BAR_W, 0),            # green
    (_BAR_W, 0, _BAR_W),       # magenta
    (_BAR_W, 0, 0),            # red
    (0, 0, _BAR_W),            # blue
)
# Lower strip: reverse blues + pluge-ish blacks/grays (simplified SMPTE bottom)
COLOR_BARS_BOT = (
    (0, 0, _BAR_W),            # blue
    (16, 16, 16),              # black
    (_BAR_W, 0, _BAR_W),       # magenta
    (16, 16, 16),              # black
    (0, _BAR_W, _BAR_W),       # cyan
    (16, 16, 16),              # black
    (_BAR_W, _BAR_W, _BAR_W),  # white
)
# Fraction of frame height for the main bars (rest = bottom strip)
COLOR_BARS_TOP_FRAC = 0.70
COLOR_BARS_FPS = 10  # static pattern; light refresh for stop_event

# Channel bug (lower-right overlay) — number climbs as channels change
CH_COLOR = (0, 220, 40)
CH_MARGIN_X = 1
CH_MARGIN_Y = 1
CH_PAD = 1                    # padding around glyphs for dim plate
CH_BG_ALPHA = 0.55            # 0=clear, 1=solid black plate under text
CH_BG_TINT = (0, 25, 0)       # slight green-black tint in the plate
CH_START = 2   # dial range CH2–CH15
CH_MAX = 15
CHANNEL_CLOCK = 5     # special: centered digital clock
CHANNEL_NEWS = 8      # special: news video + silly ticker
CHANNEL_WEATHER = 13  # special: scrolling weather report (WeatherClock / wttr.in)
CHANNEL_GIF_MIN = 14  # CH14–CH15: random GIFs from images/
CHANNEL_GIF_MAX = 15

# --- CH8 news ---
NEWS_VIDEO_NAME = "yt_qHJi8SMFrec_60s.mp4"
NEWS_VIDEO_PATH = os.path.join(VIDEO_DIR, NEWS_VIDEO_NAME)
# Specialty channels use channel_dwell_sec() (global limit); keep alias for clarity
NEWS_PLAY_SEC = None              # None → channel_dwell_sec()
NEWS_FPS = 30                     # fixed pace; higher rate + 1px steps = smooth, no flicker
NEWS_TICKER_H = 6                 # bottom bar (LEDarcade banner font is 5px tall)
NEWS_TICKER_RGB = (255, 220, 40)  # yellow crawl text
NEWS_TICKER_BG = (0, 0, 0)
NEWS_TICKER_BG_ALPHA = 0.78
# Always 1 pixel per frame (2px jumps looked too fast / jumpy)
# 1 @ 30fps ≈ 30 px/s — between the slow 24 and fast 48
NEWS_TICKER_PX_PER_FRAME = 1
NEWS_TICKER_GAP = "   --   "      # between headlines (banner font safe chars)
NEWS_TICKER_V = None              # set at runtime: HEIGHT - 5
# 100 very silly news headlines for the bottom ticker
NEWS_HEADLINES = [
    "Local squirrel elected mayor after promising free acorns for all",
    "Scientists confirm toast always lands butter-side down on purpose",
    "Man teaches goldfish to play chess, loses in three moves",
    "City bans clouds for blocking nice views, weather refuses",
    "New study finds cats have been ignoring humans since forever",
    "Breaking: pizza delivery arrives early, town declares holiday",
    "Robot vacuum forms union, demands better under-couch conditions",
    "Woman's houseplant files for emotional support animal status",
    "Experts warn of critical shortage of left socks nationwide",
    "Duck walks into library, checks out all books on flying",
    "Time traveler from 1998 shocked Wi-Fi is still not free everywhere",
    "Local man invents self-buttering toast, butter files lawsuit",
    "Moon briefly goes dark for maintenance, back online at dawn",
    "Pigeons demand bike lanes, start mid-air traffic circles",
    "Grandma's cookies classified as controlled substances by FDA",
    "Computer refuses to work until complimented on its fonts",
    "Town's only stoplight gains sentience, chooses perpetual yellow",
    "Scientists discover the remote was under the cushion all along",
    "Breaking: dogs confirm they do understand 'no' and ignore it",
    "Alien visitors leave after sampling gas station coffee",
    "New app rates your sandwich construction on a scale of 1-pickle",
    "Local bee gets lost, invents a better GPS for hives",
    "Man claims his shadow clocked out early on Friday",
    "Study: 87% of meetings could have been a single raised eyebrow",
    "Escaped circus balloon holds press conference about freedom",
    "Wi-Fi password found carved into ancient stone tablet",
    "Cat knocks mug off table for science, peer review pending",
    "City installs upside-down street signs to confuse tourists less",
    "Bread rises in revolt, flour negotiates peace deal",
    "Local weatherperson predicts 'vibes', accuracy hits 100%",
    "Fridge light unionizes, refuses to work with door closed",
    "Man completes to-do list, reality glitches briefly",
    "Snail wins marathon after all other racers get distracted",
    "Breaking: the other sock was in the dryer the whole time",
    "New law requires all puns to come with a warning label",
    "Cloud named Kevin refuses to rain on weekends",
    "Dog learns to open fridge, starts meal-prep business",
    "Scientists measure how long 'one more episode' actually is",
    "Local bridge files complaint about people taking it for granted",
    "Toaster achieves enlightenment, only burns existential crumbs",
    "Woman's GPS leads her to destiny, which is a taco truck",
    "Potted plant starts podcast about window views",
    "Breaking: Monday cancelled due to lack of interest",
    "Man builds time machine, uses it only to skip commercials",
    "Ducks form synchronized swimming team without asking anyone",
    "Study finds pillows absorb 3 dreams per night on average",
    "Traffic cone runs for senate on a platform of visibility",
    "Local coffee shop accidentally invents time travel latte",
    "Spider in corner of room named interim CEO of dust",
    "Kids' lemonade stand accepts crypto, crashes the market",
    "Breaking: all the missing pens found in a parallel drawer",
    "Owl holds night class on staring contests, enrollment full",
    "Man's alarm clock goes on strike for better snooze benefits",
    "Garden gnome spotted migrating south for the winter",
    "New diet consists entirely of foods that look like other foods",
    "Elevator music gains critical acclaim, wins Grammy",
    "Local raccoon opens Michelin-star trash tasting menu",
    "Scientists prove the shortest distance is through the snack aisle",
    "Umbrella achieves free will, only opens on sunny days",
    "Breaking: soap opera characters discover they are on a soap opera",
    "Man invents quieter keyboard, typing becomes too peaceful",
    "Lawn flamingo leads peaceful protest for better mulch",
    "Study: people who say 'per my last email' age twice as fast",
    "Mystery of missing remote solved by dog's honest testimony",
    "Local cloud storage full, sky starts deleting old rainbows",
    "Sandwich artist creates edible Mona Lisa, then eats it",
    "Breaking: Friday the 13th rescheduled to a Tuesday",
    "Hamster wheel powers small village for 12 glorious seconds",
    "Man's beard gains sentience, demands its own pillow",
    "Traffic reports now include emotional gridlock ratings",
    "Penguin applies for remote work, prefers cold Zoom backgrounds",
    "New phone update adds feature nobody asked for: jazz hands",
    "Local legend of free parking turns out to be true, briefly",
    "Scientists teach octopus to juggle, regret it immediately",
    "Breaking: the 'close door' elevator button never worked",
    "Cow jumps over moon, files flight plan next time",
    "Man loses argument with autocorrect, issues public apology",
    "Sidewalk cracks form map to buried treasure of bottle caps",
    "Study finds leftover pizza tastes better in alternate timelines",
    "Local mime speaks out, still no one can hear him",
    "Robot lawnmower writes memoir: 'Cut Me Some Slack'",
    "Breaking: all cars honk in B-flat during rush hour symphony",
    "Squirrel files patent on innovative nut-hiding algorithm",
    "Woman's house keys learn to hide better each morning",
    "New yoga pose accidentally summons mild inconvenience",
    "Fish discovers water is wet, publishes controversial paper",
    "Local Wi-Fi named 'FBI Surveillance Van' finally lives up to it",
    "Man sorts recycling wrong, bin starts passive-aggressive notes",
    "Breaking: cloud looks exactly like itself, experts baffled",
    "Toaster pastry declares independence from breakfast",
    "Dog's tail wags so hard it generates renewable energy",
    "Study: saying 'you too' to the waiter is a social superpower",
    "Local pothole elected to fill vacant council seat",
    "Invisible ink finally seen after years of dedication",
    "Breaking: socks and sandals alliance signs peace accord",
    "Man finds meaning of life on a receipt, loses receipt",
    "Butterfly effect confirmed: sneeze in Ohio cancels picnic in Maine",
    "Office printer demands sacrifice of one staple per page",
    "Local hero returns shopping cart from the far corral",
    "Scientists conclude everything is fine, probably, maybe",
]


def random_dwell_sec():
    """Seconds to stay on a channel before surfing to the next (fixed after warmup)."""
    return channel_dwell_sec()


def channel_dwell_sec():
    """Post-warmup dwell: fixed CHANNEL_DWELL_SEC (default 10s)."""
    return float(CHANNEL_DWELL_SEC)


def is_gif_channel(channel):
    n = int(channel)
    return CHANNEL_GIF_MIN <= n <= CHANNEL_GIF_MAX

# --- CH5 clock look ---
_CLOCK_FONT_CANDIDATES = (
    os.path.join(_HERE, "fonts", "Anton-Regular.ttf"),   # bold display face
    os.path.join(_HERE, "fonts", "3270-Regular.ttf"),
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
)
CLOCK_FONT_SIZE = 22          # big enough for 64x32 HH:MM
CLOCK_RGB = (0, 230, 90)      # bright green time
CLOCK_SHADOW_RGB = (0, 35, 12)
CLOCK_SHADOW_OX = 1           # shadow offset right
CLOCK_SHADOW_OY = 1           # shadow offset down
CLOCK_FORMAT = "%H:%M"        # 24h; update once per second

# --- Skyfall-style title drop ("LEDTV") ---
TITLE_WORD = "LEDTV"
TITLE_LETTER_ZOOM = 2
TITLE_LETTER_GAP = 1
TITLE_LETTER_RGB = (220, 40, 40)          # bright TV red
TITLE_LETTER_SHADOW_RGB = (40, 8, 8)
TITLE_LETTER_STAGGER = 0.22               # seconds between letter drops
TITLE_LETTER_GRAVITY = 0.62
TITLE_LETTER_BOUNCE_DAMP = 0.44
TITLE_LETTER_SETTLE_V = 0.38
TITLE_LETTER_MAX_BOUNCES = 4              # a few bounces into vertical center
TITLE_HOLD_SECONDS = 1.6                  # hold after all settled
TITLE_INTRO_MAX_SECONDS = 16.0
TITLE_TARGET_FPS = 30.0
TITLE_SIM_REFERENCE_DT = 1.0 / 60.0       # match Skyfall motion scaling
TITLE_MAX_SIM_DT = 1.0 / 12.0
# End-of-session: color bars then fade to black
END_COLOR_BARS_SEC = 3.5
END_FADE_SEC = 1.5
END_FADE_STEPS = 24

# 5x5 bitmap font (bit 4 = leftmost column)
_FONT_5X5 = {
    "C": (
        0b01110,
        0b10001,
        0b10000,
        0b10001,
        0b01110,
    ),
    "H": (
        0b10001,
        0b10001,
        0b11111,
        0b10001,
        0b10001,
    ),
    "0": (
        0b01110,
        0b10001,
        0b10001,
        0b10001,
        0b01110,
    ),
    "1": (
        0b01100,
        0b00100,
        0b00100,
        0b00100,
        0b01110,
    ),
    "2": (
        0b01110,
        0b10001,
        0b00110,
        0b01000,
        0b11111,
    ),
    "3": (
        0b11110,
        0b00001,
        0b01110,
        0b00001,
        0b11110,
    ),
    "4": (
        0b10010,
        0b10010,
        0b11111,
        0b00010,
        0b00010,
    ),
    "5": (
        0b11111,
        0b10000,
        0b11110,
        0b00001,
        0b11110,
    ),
    "6": (
        0b01110,
        0b10000,
        0b11110,
        0b10001,
        0b01110,
    ),
    "7": (
        0b11111,
        0b00001,
        0b00010,
        0b00100,
        0b00100,
    ),
    "8": (
        0b01110,
        0b10001,
        0b01110,
        0b10001,
        0b01110,
    ),
    "9": (
        0b01110,
        0b10001,
        0b01111,
        0b00001,
        0b01110,
    ),
    " ": (
        0b00000,
        0b00000,
        0b00000,
        0b00000,
        0b00000,
    ),
}
_FW = 5
_FH = 5
_FGAP = 1


#------------------------------------------------------------------------------
#  Drawing helpers
#------------------------------------------------------------------------------

def channel_label(number):
    """Format overlay text, e.g. CH2, CH12 (range CH_START–CH_MAX)."""
    n = int(number)
    span = CH_MAX - CH_START + 1
    if n < CH_START or n > CH_MAX:
        # wrap into [CH_START, CH_MAX]
        n = CH_START + ((n - CH_START) % span)
    return "CH{}".format(n)


def label_size(text):
    n = len(text)
    if n <= 0:
        return 0, 0
    return n * _FW + max(0, n - 1) * _FGAP, _FH


def channel_position(label):
    """Lower-right origin for a channel label string (glyph top-left)."""
    lw, lh = label_size(label)
    return max(0, WIDTH - lw - CH_MARGIN_X), max(0, HEIGHT - lh - CH_MARGIN_Y)


def channel_plate_rect(label):
    """Inclusive pixel box for the dim translucent plate under CHn."""
    x0, y0 = channel_position(label)
    lw, lh = label_size(label)
    left = max(0, x0 - CH_PAD)
    top = max(0, y0 - CH_PAD)
    right = min(WIDTH - 1, x0 + lw - 1 + CH_PAD)
    bottom = min(HEIGHT - 1, y0 + lh - 1 + CH_PAD)
    return left, top, right, bottom


def _blend_dim(px, tint, alpha):
    """Blend pixel toward tint (translucent dim plate)."""
    tr, tg, tb = tint
    r, g, b = px
    a = float(alpha)
    return (
        int(r * (1.0 - a) + tr * a),
        int(g * (1.0 - a) + tg * a),
        int(b * (1.0 - a) + tb * a),
    )


def dim_plate_on_image(img, label, alpha=None, tint=None):
    """Darken a translucent plate under the channel label on a PIL RGB image."""
    if alpha is None:
        alpha = CH_BG_ALPHA
    if tint is None:
        tint = CH_BG_TINT
    left, top, right, bottom = channel_plate_rect(label)
    px = img.load()
    for y in range(top, bottom + 1):
        for x in range(left, right + 1):
            px[x, y] = _blend_dim(px[x, y], tint, alpha)


def draw_label_on_image(img, text, x0, y0, color):
    """Draw 5x5 bitmap text onto a PIL RGB image."""
    r, g, b = int(color[0]), int(color[1]), int(color[2])
    px = img.load()
    x = int(x0)
    for ch in text.upper():
        rows = _FONT_5X5.get(ch, _FONT_5X5[" "])
        for row_i, bits in enumerate(rows):
            yy = y0 + row_i
            if yy < 0 or yy >= HEIGHT:
                continue
            for col in range(_FW):
                if bits & (1 << (_FW - 1 - col)):
                    xx = x + col
                    if 0 <= xx < WIDTH:
                        px[xx, yy] = (r, g, b)
        x += _FW + _FGAP


def apply_channel_bug(img, label, color=None):
    """Dim translucent plate + green channel text on a full-frame PIL image."""
    if color is None:
        color = CH_COLOR
    dim_plate_on_image(img, label)
    x0, y0 = channel_position(label)
    draw_label_on_image(img, label, x0, y0, color)
    return img


def draw_label(canvas, text, x0, y0, color):
    """Draw text on an rgbmatrix canvas (no translucent plate — prefer apply_channel_bug)."""
    r, g, b = int(color[0]), int(color[1]), int(color[2])
    x = int(x0)
    for ch in text.upper():
        rows = _FONT_5X5.get(ch, _FONT_5X5[" "])
        for row_i, bits in enumerate(rows):
            yy = y0 + row_i
            if yy < 0 or yy >= HEIGHT:
                continue
            for col in range(_FW):
                if bits & (1 << (_FW - 1 - col)):
                    xx = x + col
                    if 0 <= xx < WIDTH:
                        canvas.SetPixel(xx, yy, r, g, b)
        x += _FW + _FGAP


def draw_channel_bug_canvas(canvas, label, color=None):
    """
    Dim plate + text on canvas. Plate is a solid-ish dim green-black
    (canvas has no GetPixel; true blend is for PIL paths).
    """
    if color is None:
        color = CH_COLOR
    left, top, right, bottom = channel_plate_rect(label)
    # Approximate translucent dark plate (fixed dim green-black)
    pr = int(CH_BG_TINT[0] * CH_BG_ALPHA)
    pg = int(CH_BG_TINT[1] * CH_BG_ALPHA + 15 * (1.0 - CH_BG_ALPHA))
    pb = int(CH_BG_TINT[2] * CH_BG_ALPHA)
    for y in range(top, bottom + 1):
        for x in range(left, right + 1):
            canvas.SetPixel(x, y, pr, pg, pb)
    x0, y0 = channel_position(label)
    draw_label(canvas, label, x0, y0, color)


def next_channel(current):
    """Advance channel number (wraps CH_MAX → CH_START)."""
    return step_channel(current, +1)


def prev_channel(current):
    """Step channel number down (wraps CH_START → CH_MAX)."""
    return step_channel(current, -1)


def step_channel(current, direction):
    """Move channel by +1 or -1 with wrap."""
    n = int(current) + (1 if direction >= 0 else -1)
    if n > CH_MAX:
        n = CH_START
    elif n < CH_START:
        n = CH_MAX
    return n


def fill_white_noise(canvas):
    """Paint a full frame of traditional analog white noise (grayscale snow)."""
    img = make_white_noise_image()
    if hasattr(canvas, "SetImage"):
        canvas.SetImage(img, 0, 0)
    else:
        set_pixel = canvas.SetPixel
        px = img.load()
        for y in range(HEIGHT):
            for x in range(WIDTH):
                r, g, b = px[x, y]
                set_pixel(x, y, r, g, b)


def make_white_noise_image():
    """Return a PIL RGB frame of analog snow."""
    lum = np.random.randint(NOISE_MIN, NOISE_MAX + 1, size=(HEIGHT, WIDTH), dtype=np.uint8)
    if NOISE_SALT_CHANCE > 0:
        salt = np.random.random((HEIGHT, WIDTH)) < NOISE_SALT_CHANCE
        lum[salt] = 255
    if NOISE_PEPPER_CHANCE > 0:
        pepper = np.random.random((HEIGHT, WIDTH)) < NOISE_PEPPER_CHANCE
        lum[pepper] = 0
    # stack to RGB
    rgb = np.stack([lum, lum, lum], axis=-1)
    return Image.fromarray(rgb, mode="RGB")


def _bar_spans(n_bars, width):
    """Split width into n_bars columns (last bar absorbs remainder)."""
    base = width // n_bars
    rem = width % n_bars
    spans = []
    x = 0
    for i in range(n_bars):
        w = base + (1 if i < rem else 0)
        spans.append((x, x + w))
        x += w
    return spans


def make_color_bars_image():
    """
    SMPTE-style off-air color bars as a PIL RGB image:
      - Top ~70%: gray, yellow, cyan, green, magenta, red, blue
      - Bottom ~30%: blue, black, magenta, black, cyan, black, white
    """
    img = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
    px = img.load()
    top_h = max(1, int(HEIGHT * COLOR_BARS_TOP_FRAC))
    bot_y0 = top_h

    top_spans = _bar_spans(len(COLOR_BARS_TOP), WIDTH)
    for (x0, x1), (r, g, b) in zip(top_spans, COLOR_BARS_TOP):
        for y in range(0, top_h):
            for x in range(x0, x1):
                px[x, y] = (r, g, b)

    bot_spans = _bar_spans(len(COLOR_BARS_BOT), WIDTH)
    for (x0, x1), (r, g, b) in zip(bot_spans, COLOR_BARS_BOT):
        for y in range(bot_y0, HEIGHT):
            for x in range(x0, x1):
                px[x, y] = (r, g, b)
    return img


def fill_color_bars(canvas):
    img = make_color_bars_image()
    if hasattr(canvas, "SetImage"):
        canvas.SetImage(img, 0, 0)
    else:
        set_pixel = canvas.SetPixel
        px = img.load()
        for y in range(HEIGHT):
            for x in range(WIDTH):
                r, g, b = px[x, y]
                set_pixel(x, y, r, g, b)


def _run_loop(
    duration_minutes,
    stop_event,
    fps,
    paint_frame,
    name,
    channel=None,
    clear_on_exit=True,
    show_channel_bug=True,
):
    """Shared canvas loop: paint → SwapOnVSync → pace → honor stop/duration."""
    if channel is None:
        channel = CH_START
    label = channel_label(channel)
    print("[LEDtv] {}  ({}x{}, {:.1f} min, {})".format(
        name, WIDTH, HEIGHT, float(duration_minutes), label,
    ))
    canvas = LED.Canvas
    matrix = LED.TheMatrix
    frame_dt = 1.0 / float(fps)
    start = time.time()
    next_frame = start
    label_x, label_y = channel_position(label)

    while True:
        if stop_event is not None and stop_event.is_set():
            print("[LEDtv] StopEvent received")
            break
        now = time.time()
        if (now - start) / 60.0 >= duration_minutes:
            print("[LEDtv] Duration reached ({:.1f} min)".format((now - start) / 60.0))
            break

        # Build frame in PIL so channel plate can truly blend (translucent)
        if paint_frame is fill_white_noise:
            img = make_white_noise_image()
        elif paint_frame is fill_color_bars:
            img = make_color_bars_image()
        else:
            img = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
            paint_frame(_PilCanvas(img))
        if show_channel_bug:
            apply_channel_bug(img, label)
        # No Clear() — avoids a black flash hitch between noise frames
        canvas.SetImage(img, 0, 0)
        canvas = matrix.SwapOnVSync(canvas)
        LED.Canvas = canvas

        next_frame += frame_dt
        sleep_for = next_frame - time.time()
        if sleep_for > 0.0005:
            time.sleep(sleep_for)
        else:
            # Keep cadence; don't spin if we're late
            next_frame = time.time()

    if clear_on_exit:
        LED.ClearBigLED()
    print("[LEDtv] {} exit".format(name))


class _PilCanvas(object):
    """Minimal canvas shim so paint helpers can write into a PIL image."""

    def __init__(self, img):
        self._img = img
        self._px = img.load()

    def SetPixel(self, x, y, r, g, b):
        if 0 <= x < WIDTH and 0 <= y < HEIGHT:
            self._px[x, y] = (int(r), int(g), int(b))

    def SetImage(self, img, h=0, v=0):
        self._img.paste(img, (int(h), int(v)))

    def Clear(self):
        self._img.paste((0, 0, 0), (0, 0, WIDTH, HEIGHT))


#------------------------------------------------------------------------------
#  Effects
#------------------------------------------------------------------------------

def play_white_noise(
    duration_minutes, stop_event=None, channel=None,
    clear_on_exit=True, show_channel_bug=True,
):
    """Classic TV static with green channel bug in the lower-right corner."""
    _run_loop(
        duration_minutes, stop_event, NOISE_FPS,
        fill_white_noise, "White noise", channel=channel or CH_START,
        clear_on_exit=clear_on_exit, show_channel_bug=show_channel_bug,
    )


def play_color_bars(
    duration_minutes, stop_event=None, channel=None,
    clear_on_exit=True, show_channel_bug=True,
):
    """SMPTE-style color bars (station off the air) with green channel bug."""
    _run_loop(
        duration_minutes, stop_event, COLOR_BARS_FPS,
        fill_color_bars, "Color bars", channel=channel or CH_START,
        clear_on_exit=clear_on_exit, show_channel_bug=show_channel_bug,
    )


#------------------------------------------------------------------------------
#  Skyfall-style "LEDTV" title drop
#------------------------------------------------------------------------------

class _TitleLetter(object):
    """Single banner letter that drops, bounces, and rests on the bottom row."""

    def __init__(self, char, pixels, shadow_pixels, width, height, rest_x, rest_y, drop_delay):
        self.char = char
        self.pixels = pixels
        self.shadow_pixels = shadow_pixels
        self.width = width
        self.height = height
        self.rest_x = rest_x
        self.rest_y = rest_y
        self.drop_delay = drop_delay
        self.x = float(rest_x)
        self.y = float(-height - 6)
        self.vy = 0.0
        self.dropped = False
        self.settled = False
        self.bounce_count = 0

    def update(self, step, elapsed, gravity, bounce_damp, settle_v, max_bounces):
        if self.settled:
            self.y = self.rest_y
            return
        if elapsed < self.drop_delay:
            return
        self.dropped = True
        self.vy += gravity * step
        self.y += self.vy * step
        if self.y >= self.rest_y:
            self.y = self.rest_y
            if abs(self.vy) < settle_v or self.bounce_count >= max_bounces:
                self.vy = 0.0
                self.settled = True
            else:
                self.vy = -abs(self.vy) * bounce_damp
                self.bounce_count += 1

    def force_settle(self):
        self.x = float(self.rest_x)
        self.y = float(self.rest_y)
        self.vy = 0.0
        self.dropped = True
        self.settled = True

    def draw(self, canvas):
        sx = int(round(self.x))
        sy = int(round(self.y))
        set_pixel = canvas.SetPixel
        for dx, dy, rgb in self.shadow_pixels:
            px = sx + dx
            py = sy + dy
            if 0 <= px < WIDTH and 0 <= py < HEIGHT:
                set_pixel(px, py, rgb[0], rgb[1], rgb[2])
        for dx, dy, rgb in self.pixels:
            px = sx + dx
            py = sy + dy
            if 0 <= px < WIDTH and 0 <= py < HEIGHT:
                set_pixel(px, py, rgb[0], rgb[1], rgb[2])


def _letter_sprite(char):
    ch = char.upper()
    if not ("A" <= ch <= "Z"):
        return None
    idx = ord(ch) - ord("A")
    try:
        return LED.TrimSprite(copy.deepcopy(LED.AlphaSpriteList[idx]))
    except Exception:
        return None


def _sprite_pixels_zoomed(sprite, zoom, rgb, shadow_rgb):
    """Expand banner sprite pixels — each lit cell becomes a zoom×zoom block."""
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


def _build_title_letters(width, height):
    specs = []
    for char in TITLE_WORD:
        sprite = _letter_sprite(char)
        if sprite is None:
            continue
        pixels, shadow_pixels, letter_w, letter_h = _sprite_pixels_zoomed(
            sprite, TITLE_LETTER_ZOOM, TITLE_LETTER_RGB, TITLE_LETTER_SHADOW_RGB,
        )
        specs.append((char, pixels, shadow_pixels, letter_w, letter_h))

    if not specs:
        return []

    total_width = sum(s[3] for s in specs) + TITLE_LETTER_GAP * max(0, len(specs) - 1)
    start_x = max(0, (width - total_width) // 2)
    letter_height = max(s[4] for s in specs)
    # Rest / bounce floor = vertically centered (not the bottom row)
    rest_y = max(0, (height - letter_height) // 2)

    letters = []
    x_cursor = start_x
    for index, (char, pixels, shadow_pixels, letter_w, letter_h) in enumerate(specs):
        y_offset = letter_height - letter_h
        letters.append(_TitleLetter(
            char, pixels, shadow_pixels, letter_w, letter_h,
            x_cursor, rest_y + y_offset,
            drop_delay=index * TITLE_LETTER_STAGGER,
        ))
        x_cursor += letter_w + TITLE_LETTER_GAP
    return letters


def play_title_drop(stop_event=None):
    """
    Drop "LEDTV" one letter at a time from the sky — Skyfall-style fall + bounce,
    but settle vertically centered on the panel (bounce up into place).
    """
    letters = _build_title_letters(WIDTH, HEIGHT)
    if not letters:
        print("[LEDtv] Title drop skipped (no letter sprites)")
        return

    print("[LEDtv] Title intro — dropping '{}'".format(TITLE_WORD))
    try:
        canvas = LED.TheMatrix.CreateFrameCanvas()
    except Exception:
        canvas = LED.Canvas

    start = time.time()
    last_frame = start
    hold_start = None
    frame_period = 1.0 / TITLE_TARGET_FPS

    try:
        while True:
            if stop_event is not None and stop_event.is_set():
                break

            now = time.time()
            elapsed = now - start
            if elapsed >= TITLE_INTRO_MAX_SECONDS:
                for letter in letters:
                    letter.force_settle()
                break

            dt = now - last_frame
            last_frame = now
            # Same motion scaling as Skyfall: speeds stay consistent across FPS
            if dt <= 0.0:
                step = 1.0
            else:
                step = min(dt, TITLE_MAX_SIM_DT) / TITLE_SIM_REFERENCE_DT

            for letter in letters:
                letter.update(
                    step, elapsed,
                    TITLE_LETTER_GRAVITY, TITLE_LETTER_BOUNCE_DAMP,
                    TITLE_LETTER_SETTLE_V, TITLE_LETTER_MAX_BOUNCES,
                )

            if hold_start is None and all(letter.settled for letter in letters):
                hold_start = now

            canvas.Clear()
            for letter in letters:
                if letter.dropped or letter.settled:
                    letter.draw(canvas)
            canvas = LED.TheMatrix.SwapOnVSync(canvas)
            LED.Canvas = canvas

            if hold_start is not None and (now - hold_start) >= TITLE_HOLD_SECONDS:
                break

            # Soft pace toward target FPS
            spent = time.time() - now
            if spent < frame_period:
                time.sleep(frame_period - spent)

    except KeyboardInterrupt:
        pass

    # Brief black beat before static
    try:
        canvas.Clear()
        canvas = LED.TheMatrix.SwapOnVSync(canvas)
        LED.Canvas = canvas
    except Exception:
        LED.ClearBigLED()
    time.sleep(0.15)
    print("[LEDtv] Title intro done")


def play_static_seconds(seconds, stop_event=None, channel=None, show_channel_bug=True):
    """Play white noise for a fixed number of seconds (not minutes)."""
    if seconds is None or seconds <= 0:
        return
    mins = float(seconds) / 60.0
    play_white_noise(
        mins, stop_event=stop_event, channel=channel,
        clear_on_exit=False, show_channel_bug=show_channel_bug,
    )


def _clock_font(size=None):
    """Load a display font for the clock channel (cached per size)."""
    if size is None:
        size = CLOCK_FONT_SIZE
    cache = getattr(_clock_font, "_cache", None)
    if cache is None:
        cache = {}
        _clock_font._cache = cache
    if size in cache:
        return cache[size]
    from PIL import ImageFont
    last_err = None
    for path in _CLOCK_FONT_CANDIDATES:
        if not os.path.isfile(path):
            continue
        try:
            font = ImageFont.truetype(path, int(size))
            cache[size] = font
            print("[LEDtv] Clock font: {} @ {}".format(os.path.basename(path), size), flush=True)
            return font
        except Exception as exc:
            last_err = exc
    # Last resort
    font = ImageFont.load_default()
    cache[size] = font
    if last_err:
        print("[LEDtv] Clock font fallback (default): {}".format(last_err), flush=True)
    return font


def make_clock_image(now=None, show_channel_label=None):
    """
    Full-panel RGB image: current time centered, large font + drop shadow.
    Optional CHn bug while show_channel_label is set.
    """
    from PIL import ImageDraw
    if now is None:
        now = time.localtime()
    text = time.strftime(CLOCK_FORMAT, now)
    img = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = _clock_font(CLOCK_FONT_SIZE)

    # Measure and center (account for bbox top offset)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = max(0, (WIDTH - tw) // 2 - bbox[0])
    y = max(0, (HEIGHT - th) // 2 - bbox[1])

    # Shadow first, then main glyphs
    sx = x + int(CLOCK_SHADOW_OX)
    sy = y + int(CLOCK_SHADOW_OY)
    draw.text((sx, sy), text, font=font, fill=tuple(CLOCK_SHADOW_RGB))
    draw.text((x, y), text, font=font, fill=tuple(CLOCK_RGB))

    if show_channel_label:
        apply_channel_bug(img, show_channel_label)
    return img


def play_clock_channel(
    session_start,
    duration_minutes,
    stop_event=None,
    channel=None,
    play_seconds=None,
):
    """
    CH5: centered digital clock (big time + shadow). Runs for play_seconds
    (default VIDEO_PLAY_SEC), updating once per second.
    Returns False if session should end.
    """
    if channel is None:
        channel = CHANNEL_CLOCK
    if play_seconds is None:
        play_seconds = channel_dwell_sec()
    label = channel_label(channel)
    print("[LEDtv] {}  Clock channel ({:.0f}s)".format(label, play_seconds), flush=True)

    canvas = LED.Canvas
    matrix = LED.TheMatrix
    clip_start = time.time()
    last_key = None  # (HH:MM, show_bug)
    bug_until = clip_start + float(CHANNEL_BUG_SHOW_SEC)

    while not _time_up(session_start, duration_minutes, stop_event):
        elapsed = time.time() - clip_start
        if elapsed >= float(play_seconds):
            break
        now = time.localtime()
        text = time.strftime(CLOCK_FORMAT, now)
        show_bug = time.time() < bug_until
        key = (text, show_bug)
        if key != last_key:
            img = make_clock_image(
                now, show_channel_label=label if show_bug else None,
            )
            canvas.SetImage(img, 0, 0)
            canvas = matrix.SwapOnVSync(canvas)
            LED.Canvas = canvas
            last_key = key
        # Wake on second tick or when CHn is about to hide
        until_next_sec = 1.0 - (time.time() % 1.0)
        if until_next_sec < 0.05:
            until_next_sec = 0.05
        if show_bug:
            until_next_sec = min(until_next_sec, max(0.05, bug_until - time.time()))
        time.sleep(min(until_next_sec, 0.5))

    # No ClearBigLED — next channel paints over immediately
    print("[LEDtv] {}  Clock channel done".format(label), flush=True)
    return not _time_up(session_start, duration_minutes, stop_event)


def _make_news_banner(message):
    """
    Build a LEDarcade banner sprite via CreateBannerSprite (same glyphs as
    ShowScrollingBanner / ShowScrollingBanner2). One headline at a time —
    joining all 100 stories into one sprite freezes the display.
    """
    msg = (message or "NEWS").upper()
    safe = []
    for ch in msg:
        o = ord(ch)
        if ch in (" ", "-", ".", ":", ",", "'", '"', "!", "?", "#", "$", "(", ")",
                  "/", "\\", "&", "+", "_", "[", "]", "@", ">", "|", "`"):
            safe.append(ch)
        elif 48 <= o <= 57 or 65 <= o <= 90:
            safe.append(ch)
        elif 97 <= o <= 122:
            safe.append(ch.upper())
        else:
            safe.append(" ")
    msg = "".join(safe)
    banner = LED.CreateBannerSprite(msg)
    r, g, b = NEWS_TICKER_RGB
    banner.r = int(r)
    banner.g = int(g)
    banner.b = int(b)
    return banner


def _pick_news_headline(last=None):
    """Random headline, avoid immediate repeat when possible."""
    if not NEWS_HEADLINES:
        return "NO NEWS IS GOOD NEWS"
    pool = NEWS_HEADLINES
    if last and len(pool) > 1:
        pool = [h for h in NEWS_HEADLINES if h != last] or NEWS_HEADLINES
    return random.choice(pool)


def _news_ticker_v():
    """Vertical origin for 5-row banner along the bottom edge."""
    return max(0, HEIGHT - 5)


def _draw_ticker_bar(img):
    """Dim bar behind the LEDarcade banner crawl."""
    bar_h = min(int(NEWS_TICKER_H), HEIGHT)
    y0 = HEIGHT - bar_h
    px = img.load()
    bg = NEWS_TICKER_BG
    a = float(NEWS_TICKER_BG_ALPHA)
    for y in range(y0, HEIGHT):
        for x in range(WIDTH):
            r, g, b = px[x, y]
            px[x, y] = (
                int(r * (1.0 - a) + bg[0] * a),
                int(g * (1.0 - a) + bg[1] * a),
                int(b * (1.0 - a) + bg[2] * a),
            )


def _paint_banner_on_image(img, banner, h, v):
    """
    Draw a CreateBannerSprite onto a PIL image at (h,v) — same pixels as
    Sprite.Display / DisplayToCanvas (lit grid cells only).
    Only paints cells that land on-screen.
    """
    if banner is None:
        return
    px = img.load()
    br, bg, bb = int(banner.r), int(banner.g), int(banner.b)
    bw = int(banner.width)
    bh = int(banner.height)
    grid = banner.grid
    h = int(h)
    v = int(v)
    # Skip entirely off-screen
    if h >= WIDTH or v >= HEIGHT or h + bw <= 0 or v + bh <= 0:
        return
    for count in range(bw * bh):
        if grid[count] != 1:
            continue
        y, x = divmod(count, bw)
        sx = h + x
        sy = v + y
        if 0 <= sx < WIDTH and 0 <= sy < HEIGHT:
            px[sx, sy] = (br, bg, bb)


def _draw_news_ticker_banner(img, scroll_x, banner):
    """Bottom bar + single LEDarcade banner (ScrollAcrossScreen style)."""
    _draw_ticker_bar(img)
    if banner is not None:
        _paint_banner_on_image(img, banner, int(scroll_x), _news_ticker_v())


def play_news_channel(
    session_start,
    duration_minutes,
    stop_event=None,
    channel=None,
    play_seconds=None,
):
    """
    CH8: news video + LEDarcade CreateBannerSprite ticker.
    Honors global channel dwell (play_seconds / channel_dwell_sec()).
    Scrolls one silly headline at a time (ShowScrollingBanner2 style).
    Returns False if session should end.
    """
    if channel is None:
        channel = CHANNEL_NEWS
    if play_seconds is None:
        play_seconds = NEWS_PLAY_SEC if NEWS_PLAY_SEC is not None else channel_dwell_sec()
    play_seconds = float(play_seconds)
    label = channel_label(channel)
    video_path = NEWS_VIDEO_PATH
    if not os.path.isfile(video_path):
        alt = os.path.join(VIDEO_DIR, "yt_qHJi8SMFrec.mp4")
        if os.path.isfile(alt):
            video_path = alt
    print(
        "[LEDtv] {}  News channel  video={}  ({:.0f}s + banner ticker)".format(
            label, os.path.basename(video_path), play_seconds,
        ),
        flush=True,
    )

    # No black flash — cut straight to news; CHn shows on first frames
    if not os.path.isfile(video_path):
        print("[LEDtv] News video missing: {}".format(video_path), flush=True)
        return _play_news_ticker_only(
            session_start, duration_minutes, stop_event, label, play_seconds,
        )

    if not os.path.isfile(_FFMPEG):
        print("[LEDtv] ffmpeg not found — news video skip", flush=True)
        return _play_news_ticker_only(
            session_start, duration_minutes, stop_event, label, play_seconds,
        )

    seek = _random_seek_sec(video_path, play_seconds=play_seconds)
    frame_bytes = WIDTH * HEIGHT * 3
    # Decode at fixed NEWS_FPS without ffmpeg -re; we pace ourselves for smooth ticker
    cmd = _ffmpeg_rgb_cmd(
        video_path, fps=NEWS_FPS, realtime=False, start_sec=seek,
    )
    print(
        "[LEDtv] VIDEO  {}  name={}  seek={:.1f}s  max={:.0f}s  "
        "ticker=banner @ {}fps / {}px".format(
            label, os.path.basename(video_path), seek, play_seconds,
            NEWS_FPS, NEWS_TICKER_PX_PER_FRAME,
        ),
        flush=True,
    )

    # One headline at a time; preload next banner so swap never stalls a frame
    headline = _pick_news_headline()
    banner = _make_news_banner(headline)
    next_headline = _pick_news_headline(last=headline)
    next_banner = _make_news_banner(next_headline)
    print("[LEDtv] {}  ticker: {}".format(label, headline[:60]), flush=True)
    # Integer scroll — always exactly 1 px/frame (no multi-pixel jumps / flicker)
    scroll_x = int(WIDTH)
    text_w = max(1, int(banner.width))
    step = 1
    frame_period = 1.0 / float(NEWS_FPS)
    clip_start = time.time()
    bug_until = clip_start + float(CHANNEL_BUG_SHOW_SEC)
    proc = None
    frames = 0
    canvas = LED.Canvas
    matrix = LED.TheMatrix
    next_frame_deadline = time.time()
    preload_at = None  # set once we know text_w

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=frame_bytes * 8,
        )
        while not _time_up(session_start, duration_minutes, stop_event):
            frame_t0 = time.time()
            if frame_t0 - clip_start >= float(play_seconds):
                print("[LEDtv] News clip limit ({:.0f}s) after {} frames".format(
                    play_seconds, frames,
                ), flush=True)
                break
            raw = proc.stdout.read(frame_bytes)
            if not raw or len(raw) < frame_bytes:
                print("[LEDtv] News video ended after {} frames".format(frames), flush=True)
                break

            scroll_x -= step
            if scroll_x <= -text_w:
                # Instant swap to prebuilt next (no CreateBannerSprite stall)
                headline = next_headline
                banner = next_banner
                text_w = max(1, int(banner.width))
                scroll_x = int(WIDTH)
                print("[LEDtv] {}  ticker: {}".format(label, headline[:60]), flush=True)
                # Queue following headline for the next cycle
                next_headline = _pick_news_headline(last=headline)
                next_banner = _make_news_banner(next_headline)

            img = Image.frombytes("RGB", (WIDTH, HEIGHT), raw)
            _draw_news_ticker_banner(img, scroll_x, banner)

            if frame_t0 < bug_until:
                apply_channel_bug(img, label)

            # Full-frame swap only (no partial clear flicker)
            canvas.SetImage(img, 0, 0)
            canvas = matrix.SwapOnVSync(canvas)
            LED.Canvas = canvas
            frames += 1

            # Fixed frame pacing — constant interval = constant scroll speed
            next_frame_deadline += frame_period
            sleep_for = next_frame_deadline - time.time()
            if sleep_for > 0.0005:
                time.sleep(sleep_for)
            elif sleep_for < -2.0 * frame_period:
                # Badly behind — resync without spamming catch-up frames
                next_frame_deadline = time.time()
    except Exception as exc:
        print("[LEDtv] News playback error: {}".format(exc), flush=True)
    finally:
        if proc is not None:
            try:
                proc.kill()
            except Exception:
                pass
            try:
                proc.wait(timeout=FFMPEG_KILL_WAIT_SEC)
            except Exception:
                pass

    # No ClearBigLED — next channel paints over immediately
    print("[LEDtv] {}  News channel done".format(label), flush=True)
    return not _time_up(session_start, duration_minutes, stop_event)


def _play_news_ticker_only(
    session_start, duration_minutes, stop_event, label, play_seconds,
):
    """Fallback: black screen + smooth fixed-step banner ticker."""
    headline = _pick_news_headline()
    banner = _make_news_banner(headline)
    next_headline = _pick_news_headline(last=headline)
    next_banner = _make_news_banner(next_headline)
    scroll_x = int(WIDTH)
    text_w = max(1, int(banner.width))
    step = 1
    frame_period = 1.0 / float(NEWS_FPS)
    clip_start = time.time()
    next_frame_deadline = time.time()
    canvas = LED.Canvas
    matrix = LED.TheMatrix
    while not _time_up(session_start, duration_minutes, stop_event):
        now = time.time()
        if now - clip_start >= float(play_seconds):
            break
        scroll_x -= step
        if scroll_x <= -text_w:
            headline = next_headline
            banner = next_banner
            text_w = max(1, int(banner.width))
            scroll_x = int(WIDTH)
            next_headline = _pick_news_headline(last=headline)
            next_banner = _make_news_banner(next_headline)
        img = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
        _draw_news_ticker_banner(img, scroll_x, banner)
        if now - clip_start < float(CHANNEL_BUG_SHOW_SEC):
            apply_channel_bug(img, label)
        canvas.SetImage(img, 0, 0)
        canvas = matrix.SwapOnVSync(canvas)
        LED.Canvas = canvas
        next_frame_deadline += frame_period
        sleep_for = next_frame_deadline - time.time()
        if sleep_for > 0.0005:
            time.sleep(sleep_for)
        elif sleep_for < -2.0 * frame_period:
            next_frame_deadline = time.time()
    return not _time_up(session_start, duration_minutes, stop_event)


def play_weather_report(
    session_start,
    duration_minutes,
    stop_event=None,
    channel=None,
    play_seconds=None,
):
    """
    CH13: scrolling weather report (WeatherClock + terminal scroll).
    Honors global channel dwell (play_seconds / channel_dwell_sec()).
    Returns False if session should end; True to keep surfing.
    """
    if channel is None:
        channel = CHANNEL_WEATHER
    if play_seconds is None:
        play_seconds = channel_dwell_sec()
    play_seconds = float(play_seconds)
    label = channel_label(channel)
    print(
        "[LEDtv] {}  Weather report ({:.0f}s limit)…".format(label, play_seconds),
        flush=True,
    )

    canvas = LED.Canvas
    matrix = LED.TheMatrix
    land_start = time.time()
    deadline = land_start + play_seconds

    def _still_ok():
        if stop_event is not None and stop_event.is_set():
            return False
        if _time_up(session_start, duration_minutes, stop_event):
            return False
        if time.time() >= deadline:
            return False
        return True

    def _time_left():
        return max(0.0, deadline - time.time())

    # Same as other channels: show CHn overlay for CHANNEL_BUG_SHOW_SEC on land
    # (capped by remaining dwell)
    def _show_weather_channel_bug():
        img = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
        apply_channel_bug(img, label)
        canvas.SetImage(img, 0, 0)
        c = matrix.SwapOnVSync(canvas)
        LED.Canvas = c
        return c

    canvas = _show_weather_channel_bug()
    bug_until = land_start + min(float(CHANNEL_BUG_SHOW_SEC), play_seconds)

    # Fetch while CH bug is visible
    try:
        import WeatherClock as WC
    except Exception as exc:
        print("[LEDtv] WeatherClock import failed: {}".format(exc), flush=True)
        while _still_ok() and time.time() < bug_until:
            time.sleep(0.05)
        return not _time_up(session_start, duration_minutes, stop_event)

    location = WC.LoadWeatherLocation()
    units = WC.NormalizeUnits("C")  # metric default
    print("[LEDtv] {}  Fetching weather for {!r}…".format(label, location), flush=True)
    report = WC.FetchWeatherReport(location, units=units)
    if isinstance(report, dict):
        header = report.get("header", "") or ""
        body = report.get("body", "") or ""
        message = " ".join(p for p in (header, body) if p)
    else:
        header, body, message = "", "", str(report)

    if not message:
        message = "Weather unavailable."

    # Keep CHn for normal overlay window (within dwell)
    while _still_ok() and time.time() < bug_until:
        canvas = _show_weather_channel_bug()
        time.sleep(0.05)

    if not _still_ok():
        print("[LEDtv] {}  Weather dwell elapsed before scroll".format(label), flush=True)
        return not _time_up(session_start, duration_minutes, stop_event)

    try:
        LED.ScreenArray = [
            [(0, 0, 0) for _ in range(WIDTH)] for _ in range(HEIGHT)
        ]
    except Exception:
        pass
    LED.ClearBigLED()

    cursor_h, cursor_v = 0, 0
    type_speed = getattr(WC, "WEATHER_TYPE_SPEED", 0.064)
    scroll_speed = 0.05
    body_rgb = (0, 200, 0)
    header_rgb = getattr(WC, "WEATHER_HEADER_RGB", (200, 200, 0))
    cursor_rgb = (0, 255, 0)
    cursor_dark = (0, 50, 0)
    # One pass only when on a short global dwell (no double-scroll)
    repeat = 1 if play_seconds <= 15 else max(int(getattr(WC, "WEATHER_SCROLL_REPEAT", 2)), 1)

    try:
        for rep in range(repeat):
            if not _still_ok():
                break

            if header and body:
                LED.ScreenArray, cursor_h, cursor_v = LED.TerminalScroll(
                    LED.ScreenArray, header,
                    CursorH=cursor_h, CursorV=cursor_v,
                    MessageRGB=header_rgb,
                    CursorRGB=cursor_rgb, CursorDarkRGB=cursor_dark,
                    StartingLineFeed=1,
                    TypeSpeed=type_speed,
                    ScrollSpeed=scroll_speed,
                )
                if not _still_ok():
                    break
                LED.ScreenArray, cursor_h, cursor_v = LED.TerminalScroll(
                    LED.ScreenArray, body,
                    CursorH=cursor_h, CursorV=cursor_v,
                    MessageRGB=body_rgb,
                    CursorRGB=cursor_rgb, CursorDarkRGB=cursor_dark,
                    StartingLineFeed=0,
                    TypeSpeed=type_speed,
                    ScrollSpeed=scroll_speed,
                )
            else:
                LED.ScreenArray, cursor_h, cursor_v = LED.TerminalScroll(
                    LED.ScreenArray, message,
                    CursorH=cursor_h, CursorV=cursor_v,
                    MessageRGB=body_rgb,
                    CursorRGB=cursor_rgb, CursorDarkRGB=cursor_dark,
                    StartingLineFeed=1,
                    TypeSpeed=type_speed,
                    ScrollSpeed=scroll_speed,
                )

            if rep < repeat - 1 and _still_ok():
                LED.ScreenArray, cursor_h, cursor_v = LED.TerminalScroll(
                    LED.ScreenArray, "",
                    CursorH=cursor_h, CursorV=cursor_v,
                    MessageRGB=body_rgb,
                    CursorRGB=cursor_rgb, CursorDarkRGB=cursor_dark,
                    StartingLineFeed=1,
                    TypeSpeed=0,
                    ScrollSpeed=scroll_speed,
                )

        # Brief post wait only if dwell remains
        wait_end = time.time() + min(0.5, _time_left())
        while time.time() < wait_end and _still_ok():
            try:
                LED.BlinkCursor(
                    CursorH=cursor_h, CursorV=cursor_v,
                    CursorRGB=cursor_rgb, CursorDarkRGB=cursor_dark,
                    BlinkSpeed=0.5, BlinkCount=1,
                )
            except Exception:
                time.sleep(0.1)

    except Exception as exc:
        print("[LEDtv] Weather scroll error: {}".format(exc), flush=True)

    # If TerminalScroll overran, still leave when dwell is done
    while _still_ok():
        time.sleep(0.05)

    print(
        "[LEDtv] {}  Weather report done ({:.1f}s)".format(
            label, time.time() - land_start,
        ),
        flush=True,
    )
    return not _time_up(session_start, duration_minutes, stop_event)


def play_channel_flash(seconds, channel, stop_event=None, session_start=None, duration_minutes=None):
    """
    Optional black beat + CHn. With CHANNEL_CHANGE_FLASH_SEC=0 this is a no-op
    so channel changes cut straight to content (CHn overlays the first frames).
    """
    if seconds is None:
        seconds = CHANNEL_CHANGE_FLASH_SEC
    if float(seconds) <= 0.001:
        return not (
            session_start is not None
            and duration_minutes is not None
            and _time_up(session_start, duration_minutes, stop_event)
        )
    if session_start is not None and duration_minutes is not None:
        if _time_up(session_start, duration_minutes, stop_event):
            return False
    end = time.time() + float(seconds)
    label = channel_label(channel)
    canvas = LED.Canvas
    matrix = LED.TheMatrix

    # Draw once (black + CHn); hold for the flash duration
    img = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
    apply_channel_bug(img, label)
    canvas.Clear()
    canvas.SetImage(img, 0, 0)
    canvas = matrix.SwapOnVSync(canvas)
    LED.Canvas = canvas

    while time.time() < end:
        if stop_event is not None and stop_event.is_set():
            return False
        if session_start is not None and duration_minutes is not None:
            if _time_up(session_start, duration_minutes, stop_event):
                return False
        time.sleep(0.05)
    return True


def play_boot_intro(stop_event=None, seconds=None, channel=None):
    """
    After the title drop: pure analog static for a few seconds, then surfing.
    """
    if seconds is None:
        seconds = STATIC_BOOT_SEC
    ch = CH_START if channel is None else int(channel)
    print("[LEDtv] Boot static ({}s, {})".format(seconds, channel_label(ch)))
    play_static_seconds(seconds, stop_event=stop_event, channel=ch, show_channel_bug=True)
    print("[LEDtv] Boot static done — starting channel surf")


def play_end_sequence(stop_event=None):
    """
    Session over: color-signal (SMPTE bars), then fade to black.
    Skipped early if stop_event is already set (commander preemption).
    """
    if stop_event is not None and stop_event.is_set():
        LED.ClearBigLED()
        return

    print("[LEDtv] End sequence — color bars ({:.1f}s)".format(END_COLOR_BARS_SEC))
    bars = make_color_bars_image()
    canvas = LED.Canvas
    matrix = LED.TheMatrix
    bars_end = time.time() + float(END_COLOR_BARS_SEC)
    while time.time() < bars_end:
        if stop_event is not None and stop_event.is_set():
            LED.ClearBigLED()
            return
        canvas.Clear()
        canvas.SetImage(bars, 0, 0)
        canvas = matrix.SwapOnVSync(canvas)
        LED.Canvas = canvas
        time.sleep(0.08)

    print("[LEDtv] End sequence — fade to black ({:.1f}s)".format(END_FADE_SEC))
    # Fade bars toward black
    px = bars.load()
    step_sleep = float(END_FADE_SEC) / float(max(1, END_FADE_STEPS))
    for step in range(1, END_FADE_STEPS + 1):
        if stop_event is not None and stop_event.is_set():
            break
        # remaining brightness 1 → 0
        factor = 1.0 - (float(step) / float(END_FADE_STEPS))
        faded = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
        fp = faded.load()
        for y in range(HEIGHT):
            for x in range(WIDTH):
                r, g, b = px[x, y]
                fp[x, y] = (
                    int(r * factor),
                    int(g * factor),
                    int(b * factor),
                )
        canvas.Clear()
        canvas.SetImage(faded, 0, 0)
        canvas = matrix.SwapOnVSync(canvas)
        LED.Canvas = canvas
        time.sleep(step_sleep)

    try:
        canvas.Clear()
        canvas = matrix.SwapOnVSync(canvas)
        LED.Canvas = canvas
    except Exception:
        LED.ClearBigLED()
    print("[LEDtv] End sequence done")


def _dedupe_paths(paths):
    seen = set()
    out = []
    for p in paths:
        key = os.path.normcase(os.path.abspath(p))
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


def list_gifs(folder=None):
    """All .gif paths under the images folder (non-recursive)."""
    folder = folder or GIF_DIR
    if not os.path.isdir(folder):
        return []
    paths = sorted(glob.glob(os.path.join(folder, "*.gif")))
    paths += sorted(glob.glob(os.path.join(folder, "*.GIF")))
    return _dedupe_paths(paths)


def list_videos(folder=None):
    """Local video files under videos/ (gitignored cache)."""
    folder = folder or VIDEO_DIR
    if not os.path.isdir(folder):
        return []
    paths = []
    for ext in VIDEO_EXTS:
        paths += glob.glob(os.path.join(folder, "*" + ext))
        paths += glob.glob(os.path.join(folder, "*" + ext.upper()))
    return _dedupe_paths(sorted(paths))


# When False, channel rotation only plays local videos/ (no GIFs).
CHANNELS_INCLUDE_GIFS = False
# Back-compat alias for boot static length
BOOT_INTRO_SEC = STATIC_BOOT_SEC


def list_channel_items(gif_dir=None, video_dir=None, include_gifs=None):
    """
    Playlist for channel rotation.
    Each item: {"path": str, "kind": "gif"|"video"}
    GIFs optional (CHANNELS_INCLUDE_GIFS); videos always included when present.
    """
    if include_gifs is None:
        include_gifs = CHANNELS_INCLUDE_GIFS
    items = []
    if include_gifs:
        for p in list_gifs(gif_dir):
            items.append({"path": p, "kind": "gif"})
    for p in list_videos(video_dir):
        items.append({"path": p, "kind": "video"})
    return items


def _fit_size(src_w, src_h, max_w, max_h):
    """
    Scale to fit inside max_w x max_h while keeping aspect ratio.
    Never stretches wider/taller independently; never exceeds the panel.
    """
    if src_w <= 0 or src_h <= 0:
        return max(1, max_w), max(1, max_h)
    scale = min(float(max_w) / float(src_w), float(max_h) / float(src_h))
    # Integer pixel size; clamp so we never exceed the box
    nw = max(1, min(max_w, int(round(src_w * scale))))
    nh = max(1, min(max_h, int(round(src_h * scale))))
    return nw, nh


def _load_gif_frames(path, max_w, max_h):
    """
    Load a GIF as RGB frames, scaled to fit the panel without distortion.
    Aspect ratio is preserved (letterbox/pillarbox when drawn centered).
    """
    frames = []
    delays = []
    gif = Image.open(path)
    # Use the first frame's size as the native aspect reference
    try:
        gif.seek(0)
    except Exception:
        pass
    native_w, native_h = gif.size
    fit_w, fit_h = _fit_size(native_w, native_h, max_w, max_h)

    for frame in ImageSequence.Iterator(gif):
        rgb = frame.convert("RGB")
        # Recompute per-frame in case sizes vary (rare)
        fw, fh = rgb.size
        if fw != native_w or fh != native_h:
            tw, th = _fit_size(fw, fh, max_w, max_h)
        else:
            tw, th = fit_w, fit_h
        if (fw, fh) != (tw, th):
            rgb = rgb.resize((tw, th), Image.LANCZOS)
        frames.append(rgb)
        dur_ms = frame.info.get("duration", 100)
        if not dur_ms or dur_ms < 20:
            dur_ms = int(GIF_FRAME_SLEEP * 1000)
        delays.append(dur_ms / 1000.0)
    return frames, delays


def _time_up(start, duration_minutes, stop_event):
    if stop_event is not None and stop_event.is_set():
        return True
    if (time.time() - start) / 60.0 >= duration_minutes:
        return True
    return False


def _play_gif_item(path, canvas_holder, matrix, label, label_x, label_y,
                   start, duration_minutes, stop_event,
                   show_channel_sec=None, max_seconds=None):
    """
    Play one GIF, looping until max_seconds (or GIF_LOOPS_EACH if max_seconds is None).
    Returns False if session time/stop hit; True to keep surfing.
    CHn overlay only for the first show_channel_sec after start.
    """
    if show_channel_sec is None:
        show_channel_sec = CHANNEL_BUG_SHOW_SEC
    name = os.path.basename(path)
    try:
        frames, delays = _load_gif_frames(path, WIDTH, HEIGHT)
    except Exception as exc:
        print("[LEDtv] Failed to load GIF {}: {}".format(name, exc))
        time.sleep(0.3)
        return True  # keep rotating

    if not frames:
        return True

    canvas = canvas_holder[0]
    item_start = time.time()
    loops = 999999 if max_seconds is not None else GIF_LOOPS_EACH
    for _loop in range(loops):
        if _time_up(start, duration_minutes, stop_event):
            return False
        if max_seconds is not None and (time.time() - item_start) >= float(max_seconds):
            break
        for frame, delay in zip(frames, delays):
            if _time_up(start, duration_minutes, stop_event):
                return False
            if max_seconds is not None and (time.time() - item_start) >= float(max_seconds):
                break
            # Composite onto full panel so plate can blend with letterbox/content
            img = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
            h = max(0, (WIDTH - frame.size[0]) // 2)
            v = max(0, (HEIGHT - frame.size[1]) // 2)
            img.paste(frame, (h, v))
            if (time.time() - item_start) < float(show_channel_sec):
                apply_channel_bug(img, label)
            canvas.SetImage(img, 0, 0)
            canvas = matrix.SwapOnVSync(canvas)
            canvas_holder[0] = canvas
            LED.Canvas = canvas
            time.sleep(delay)
    return not _time_up(start, duration_minutes, stop_event)


def _pick_gif_path(gif_dir=None, last_path=None):
    """Random GIF from images/ (or gif_dir), avoiding last_path when possible."""
    paths = list_gifs(gif_dir)
    if not paths:
        return None
    if last_path and len(paths) > 1:
        choices = [p for p in paths if p != last_path]
        if choices:
            paths = choices
    return random.choice(paths)


def play_gif_channel(
    session_start,
    duration_minutes,
    stop_event=None,
    channel=None,
    play_seconds=None,
    gif_dir=None,
    last_path=None,
    canvas_holder=None,
    matrix=None,
    gif_deck=None,
):
    """
    CH14–CH15: play next GIF from the session-shuffled deck for play_seconds.
    Returns (ok, path_used, gif_deck).
    """
    if channel is None:
        channel = CHANNEL_GIF_MIN
    if play_seconds is None:
        play_seconds = random_dwell_sec()
    label = channel_label(channel)
    if gif_deck is not None:
        path, gif_deck = _draw_gif_from_deck(gif_deck, gif_dir=gif_dir)
    else:
        path = _pick_gif_path(gif_dir=gif_dir, last_path=last_path)
    if not path:
        print("[LEDtv] {}  No GIFs in {}".format(label, gif_dir or GIF_DIR), flush=True)
        ok = play_channel_flash(
            play_seconds, channel,
            stop_event=stop_event,
            session_start=session_start,
            duration_minutes=duration_minutes,
        )
        return ok, last_path, gif_deck

    name = os.path.basename(path)
    print(
        "[LEDtv] {}  GIF  name={}  ({:.1f}s)".format(label, name, play_seconds),
        flush=True,
    )
    if canvas_holder is None:
        canvas_holder = [LED.Canvas]
    if matrix is None:
        matrix = LED.TheMatrix
    label_x, label_y = channel_position(label)
    ok = _play_gif_item(
        path, canvas_holder, matrix, label, label_x, label_y,
        session_start, duration_minutes, stop_event,
        max_seconds=play_seconds,
    )
    return ok, path, gif_deck


def play_random_gif(duration_minutes, stop_event=None, gif_dir=None, start_channel=None):
    """Backward-compatible alias → full channel rotation (GIFs + videos). """
    play_channel_rotation(
        duration_minutes,
        stop_event=stop_event,
        gif_dir=gif_dir,
        start_channel=start_channel,
    )


def play_channel_rotation(
    duration_minutes,
    stop_event=None,
    gif_dir=None,
    video_dir=None,
    start_channel=None,
    boot_intro=True,
    title_intro=False,
):
    """
    Main channel-surf loop (default effect):

      title drop (LaunchLEDtv) → static 3s
      sequential CH2→…→CH15→CH2… each land for 5–15s:
        CH5  clock | CH13 weather | CH14–15 GIFs | else random video
      when time is up: color bars → fade to black
    """
    channel = CH_START if start_channel is None else int(start_channel)
    start = time.time()

    # List media and kick off duration warm ASAP (background) so boot static
    # never freezes while ffprobe walks the video library on the main thread.
    items = list_channel_items(gif_dir=gif_dir, video_dir=video_dir)
    n_gif_dir = len(list_gifs(gif_dir))
    n_vid = sum(1 for i in items if i["kind"] == "video")
    print(
        "[LEDtv] Channel surf  CH{}–CH{}  dwell={:.0f}s (after warmup)  "
        "videos={}  gifs_on_ch14-15={}  (in {})".format(
            CH_START, CH_MAX,
            CHANNEL_DWELL_SEC,
            n_vid, n_gif_dir, gif_dir or GIF_DIR,
        ),
        flush=True,
    )
    if not items and n_gif_dir == 0:
        print("[LEDtv] No media found — end sequence")
        play_end_sequence(stop_event=stop_event)
        return

    extra = [NEWS_VIDEO_PATH] if os.path.isfile(NEWS_VIDEO_PATH) else []
    _start_duration_warm_async(items, extra_paths=extra)

    # Shuffle is cheap; do it now so the first clip is ready after static
    try:
        random.seed(os.urandom(16))
    except Exception:
        random.seed()
    video_deck = _make_shuffled_video_deck(items)
    gif_deck = _make_shuffled_gif_deck(gif_dir)
    print(
        "[LEDtv] Session shuffle: {} videos, {} GIFs (new order each start)".format(
            len(video_deck), len(gif_deck),
        ),
        flush=True,
    )

    if title_intro:
        play_title_drop(stop_event=stop_event)
        if stop_event is not None and stop_event.is_set():
            LED.ClearBigLED()
            return

    if boot_intro:
        # White noise runs free while duration warm continues in the background
        play_boot_intro(
            stop_event=stop_event, seconds=STATIC_BOOT_SEC, channel=channel,
        )
        if stop_event is not None and stop_event.is_set():
            LED.ClearBigLED()
            return

    canvas_holder = [LED.Canvas]
    matrix = LED.TheMatrix
    last_path = None
    last_gif_path = None
    first_cycle = True

    while not _time_up(start, duration_minutes, stop_event):
        # --- sequential channel surf (always on; previews optional) ---
        if CHANNEL_PREVIEWS_ENABLED:
            if first_cycle:
                n_flashes = random.randint(CHANNEL_FLASH_MIN, CHANNEL_FLASH_MAX)
            else:
                n_flashes = 1
            print("[LEDtv] Channel surf x{} (sequential up)".format(n_flashes))
            for i in range(n_flashes):
                if _time_up(start, duration_minutes, stop_event):
                    break
                if not (first_cycle and i == 0):
                    channel = next_channel(channel)
                ok, last_path = _play_momentary_channel_video(
                    items, channel, canvas_holder, matrix,
                    start, duration_minutes, stop_event,
                    last_path=last_path,
                    seconds=CHANNEL_FLASH_SEC,
                )
                if not ok:
                    break
        else:
            if not first_cycle:
                channel = next_channel(channel)

        dwell = channel_dwell_sec()  # 10s after title/static warmup
        print(
            "[LEDtv] Channel {}  dwell={:.0f}s".format(channel_label(channel), dwell),
            flush=True,
        )

        if _time_up(start, duration_minutes, stop_event):
            break

        # --- special / media channels ---
        # Specialty channels (clock / news / weather / future stocks) all use
        # the same global dwell as video channels.
        if int(channel) == int(CHANNEL_CLOCK):
            ok = play_clock_channel(
                start, duration_minutes, stop_event=stop_event, channel=channel,
                play_seconds=dwell,
            )
            first_cycle = False
            if not ok or _time_up(start, duration_minutes, stop_event):
                break
            continue

        if int(channel) == int(CHANNEL_NEWS):
            ok = play_news_channel(
                start, duration_minutes, stop_event=stop_event, channel=channel,
                play_seconds=dwell,
            )
            first_cycle = False
            if not ok or _time_up(start, duration_minutes, stop_event):
                break
            continue

        if int(channel) == int(CHANNEL_WEATHER):
            ok = play_weather_report(
                start, duration_minutes, stop_event=stop_event, channel=channel,
                play_seconds=dwell,
            )
            first_cycle = False
            if not ok or _time_up(start, duration_minutes, stop_event):
                break
            continue

        if is_gif_channel(channel):
            ok, last_gif_path, gif_deck = play_gif_channel(
                start, duration_minutes, stop_event=stop_event, channel=channel,
                play_seconds=dwell, gif_dir=gif_dir, last_path=last_gif_path,
                canvas_holder=canvas_holder, matrix=matrix,
                gif_deck=gif_deck,
            )
            first_cycle = False
            if not ok or _time_up(start, duration_minutes, stop_event):
                break
            continue

        # --- video channels: session-shuffled deck + random seek into clip ---
        path, video_deck = _draw_from_deck(video_deck, items)
        if path is None:
            ok = play_channel_flash(
                dwell, channel,
                stop_event=stop_event,
                session_start=start,
                duration_minutes=duration_minutes,
            )
            first_cycle = False
            if not ok:
                break
            continue
        last_path = path
        name = os.path.basename(path)
        label = channel_label(channel)
        label_x, label_y = channel_position(label)
        print(
            "[LEDtv] {}  Playing VIDEO  video={}  ({:.1f}s max, random seek)  "
            "deck_left={}".format(
                label, name, dwell, len(video_deck),
            ),
            flush=True,
        )
        ok = _play_video_once(
            path, canvas_holder, matrix, label, label_x, label_y,
            start, duration_minutes, stop_event,
            realtime=True,
            max_seconds=dwell,
            random_seek=True,
        )

        first_cycle = False
        if not ok or _time_up(start, duration_minutes, stop_event):
            break
        # next loop: channel++ sequential

    if stop_event is not None and stop_event.is_set():
        print("[LEDtv] StopEvent received")
        LED.ClearBigLED()
    else:
        print("[LEDtv] Duration reached ({:.1f} min)".format(
            (time.time() - start) / 60.0,
        ))
        # Color signal, then fade to black
        play_end_sequence(stop_event=stop_event)

    print("[LEDtv] Channel rotation exit")


#------------------------------------------------------------------------------
#  YouTube / local video
#------------------------------------------------------------------------------

def _find_yt_dlp():
    for path in _YT_DLP_CANDIDATES:
        if path and os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return None


def _is_local_media_path(url_or_path):
    """True if this is an existing local file (not an http URL)."""
    if not url_or_path:
        return False
    s = str(url_or_path).strip()
    if s.startswith("http://") or s.startswith("https://"):
        return False
    # Allow relative paths from LEDarcade root
    candidates = [
        s,
        os.path.join(_HERE, s),
        os.path.join(VIDEO_DIR, os.path.basename(s)),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return True
    return False


def _resolve_local_path(url_or_path):
    s = str(url_or_path).strip()
    for c in (s, os.path.join(_HERE, s), os.path.join(VIDEO_DIR, os.path.basename(s))):
        if os.path.isfile(c):
            return os.path.abspath(c)
    raise FileNotFoundError("Local media not found: {}".format(url_or_path))


def _youtube_stream_url(url):
    """
    Resolve a playable media URL via yt-dlp.
    Prefer a modest progressive MP4 so ffmpeg can seek/stream cleanly.
    """
    ytdlp = _find_yt_dlp()
    if not ytdlp:
        raise RuntimeError("yt-dlp not found (install yt-dlp)")
    # Prefer low-res for bandwidth/CPU; fall back to whatever is available
    fmt = (
        "best[height<=360][ext=mp4]/"
        "best[height<=480][ext=mp4]/"
        "best[height<=360]/"
        "best[ext=mp4]/"
        "best"
    )
    cmd = [
        ytdlp,
        "-f", fmt,
        "-g",
        "--no-playlist",
        "--no-warnings",
        url,
    ]
    print("[LEDtv] Resolving YouTube stream…")
    print("[LEDtv]   {}".format(" ".join(cmd)))
    proc = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=90,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            "yt-dlp failed ({}): {}".format(proc.returncode, (proc.stderr or "")[-400:])
        )
    lines = [ln.strip() for ln in (proc.stdout or "").splitlines() if ln.strip()]
    if not lines:
        raise RuntimeError("yt-dlp returned no stream URL")
    # -g may print video+audio URLs for DASH; first line is usually video
    stream = lines[0]
    print("[LEDtv] Stream OK ({} chars)".format(len(stream)))
    return stream


def _probe_duration_sec(path):
    """Return media duration in seconds, or None if unknown."""
    key = os.path.abspath(str(path))
    if key in _DURATION_CACHE:
        return _DURATION_CACHE[key]
    if not os.path.isfile(_FFPROBE):
        return None
    if not os.path.isfile(key):
        return None
    try:
        proc = subprocess.run(
            [
                _FFPROBE, "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                key,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=15,
        )
        if proc.returncode != 0:
            return None
        text = (proc.stdout or "").strip()
        if not text or text.upper() == "N/A":
            return None
        dur = float(text)
        if dur <= 0:
            return None
        _DURATION_CACHE[key] = dur
        return dur
    except Exception as exc:
        print("[LEDtv] ffprobe failed for {}: {}".format(os.path.basename(key), exc))
        return None


def _random_seek_sec(path, play_seconds=None):
    """
    Pick a random start offset so a clip of play_seconds still fits when possible.
    Returns 0 if duration unknown or too short.
    """
    dur = _probe_duration_sec(path)
    if dur is None or dur <= 1.5:
        return 0.0
    need = float(play_seconds) if play_seconds else 5.0
    # Leave a little room so seek isn't stuck at the very end
    max_start = max(0.0, dur - max(need, 1.0) - 0.25)
    if max_start <= 0.05:
        return 0.0
    return random.uniform(0.0, max_start)


def _ffmpeg_rgb_cmd(input_url, fps=VIDEO_FPS, realtime=True, start_sec=None):
    """
    ffmpeg command that emits fixed-size RGB24 frames:
    scale to fit WIDTH x HEIGHT (aspect preserved) + black pad.
    Optional start_sec seeks to a random/absolute offset (-ss before -i).
    """
    # force_original_aspect_ratio=decrease then pad → never stretches wider
    vf = (
        "scale={w}:{h}:force_original_aspect_ratio=decrease:"
        "flags=bilinear,"
        "pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black,"
        "fps={fps}".format(w=WIDTH, h=HEIGHT, fps=int(fps))
    )
    cmd = [
        _FFMPEG,
        "-hide_banner",
        "-loglevel", "error",
    ]
    if realtime:
        cmd.append("-re")  # pace at native rate (TV feel)
    # Input seek (fast) — used for random in-file start on local files
    if start_sec is not None and float(start_sec) > 0.01:
        cmd += ["-ss", "{:.3f}".format(float(start_sec))]
    cmd += [
        "-i", input_url,
        "-an",                 # no audio (matrix has none)
        "-vf", vf,
        "-pix_fmt", "rgb24",
        "-f", "rawvideo",
        "pipe:1",
    ]
    return cmd


def _play_video_once(
    source,
    canvas_holder,
    matrix,
    label,
    label_x,
    label_y,
    start,
    duration_minutes,
    stop_event,
    fps=VIDEO_FPS,
    realtime=True,
    max_seconds=None,
    show_channel_sec=None,
    random_seek=True,
    start_sec=None,
):
    """
    Decode one video (local path or stream URL) to the panel.
    Returns False if session duration/stop hit mid-play; True if clip finished
    cleanly or hit max_seconds (caller may continue surfing).

    By default seeks to a random point in the file (all local videos).
    CHn overlay is shown only for the first show_channel_sec of the clip
    (default CHANNEL_BUG_SHOW_SEC); reappears on the next channel change.
    """
    if show_channel_sec is None:
        show_channel_sec = CHANNEL_BUG_SHOW_SEC
    if not os.path.isfile(_FFMPEG):
        print("[LEDtv] ffmpeg not found — skip video")
        return True

    # Random in-file start for local media (all videos)
    seek = start_sec
    if seek is None and random_seek and os.path.isfile(str(source)):
        seek = _random_seek_sec(source, play_seconds=max_seconds or VIDEO_PLAY_SEC)
    if seek is None:
        seek = 0.0

    frame_bytes = WIDTH * HEIGHT * 3
    # Fast open: input seek already set; no ffmpeg -re stall if realtime=False preferred
    cmd = _ffmpeg_rgb_cmd(source, fps=fps, realtime=realtime, start_sec=seek)
    video_name = os.path.basename(str(source))
    # Always log the video name (commander/twitch often buffer stdout otherwise)
    print(
        "[LEDtv] VIDEO  {}  name={}  seek={:.1f}s  max={}s  channel={}".format(
            label or "?",
            video_name,
            float(seek or 0),
            "{:.0f}".format(max_seconds) if max_seconds is not None else "full",
            label or "?",
        ),
        flush=True,
    )
    proc = None
    frames = 0
    finished_clean = False
    clip_start = time.time()
    bug_on = True  # log once when CHn turns off
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=frame_bytes * 8,
        )
        canvas = canvas_holder[0]
        while not _time_up(start, duration_minutes, stop_event):
            elapsed_clip = time.time() - clip_start
            if max_seconds is not None and elapsed_clip >= float(max_seconds):
                print("[LEDtv] Video clip limit ({:.0f}s) after {} frames".format(
                    max_seconds, frames,
                ))
                finished_clean = True
                break
            raw = proc.stdout.read(frame_bytes)
            if not raw or len(raw) < frame_bytes:
                finished_clean = True
                print("[LEDtv] Video ended after {} frames".format(frames))
                break
            img = Image.frombytes("RGB", (WIDTH, HEIGHT), raw)
            if elapsed_clip < float(show_channel_sec):
                apply_channel_bug(img, label)
            elif bug_on:
                bug_on = False
                print("[LEDtv] {} overlay off".format(label))
            # Full-frame swap only — no Clear() black gap between frames/channels
            canvas.SetImage(img, 0, 0)
            canvas = matrix.SwapOnVSync(canvas)
            canvas_holder[0] = canvas
            LED.Canvas = canvas
            frames += 1
    except Exception as exc:
        print("[LEDtv] Video playback error: {}".format(exc))
        finished_clean = True
    finally:
        if proc is not None:
            try:
                proc.kill()
            except Exception:
                pass
            try:
                proc.wait(timeout=FFMPEG_KILL_WAIT_SEC)
            except Exception:
                pass

    if _time_up(start, duration_minutes, stop_event):
        return False
    return finished_clean or frames > 0


def _warm_video_duration_cache(items):
    """Probe video lengths once so channel changes don't stall on ffprobe."""
    n = 0
    for it in items or []:
        if it.get("kind") != "video":
            continue
        p = it.get("path")
        if p and os.path.isfile(p):
            if _probe_duration_sec(p) is not None:
                n += 1
    if n:
        print("[LEDtv] Warmed duration cache for {} videos".format(n), flush=True)
    return n


_WARM_THREAD = None
_WARM_LOCK = threading.Lock()


def _start_duration_warm_async(items, extra_paths=None):
    """
    Run ffprobe cache fill on a background thread so the display loop
    (boot static, title, first clips) never freezes.
    """
    global _WARM_THREAD

    paths_extra = list(extra_paths or [])

    def _worker():
        try:
            with _WARM_LOCK:
                print("[LEDtv] Duration warm (background) starting…", flush=True)
                n = _warm_video_duration_cache(items)
                for p in paths_extra:
                    if p and os.path.isfile(p):
                        _probe_duration_sec(p)
                print(
                    "[LEDtv] Duration warm (background) done ({} videos)".format(n),
                    flush=True,
                )
        except Exception as exc:
            print("[LEDtv] Duration warm error: {}".format(exc), flush=True)

    # Don't stack multiple warmers
    if _WARM_THREAD is not None and _WARM_THREAD.is_alive():
        return _WARM_THREAD
    _WARM_THREAD = threading.Thread(target=_worker, name="ledtv-ffprobe-warm", daemon=True)
    _WARM_THREAD.start()
    return _WARM_THREAD


def _pick_video_item(items, last_path=None):
    """Pick a random video (prefer kind=video) avoiding last_path when possible."""
    vids = [it for it in items if it.get("kind") == "video"]
    pool = vids if vids else list(items)
    if not pool:
        return None
    if last_path and len(pool) > 1:
        choices = [it for it in pool if it["path"] != last_path]
        if choices:
            pool = choices
    return random.choice(pool)


def _make_shuffled_video_deck(items):
    """
    Fresh shuffle of all video paths for this LEDtv session (each reboot/start).
    Draw without replacement until empty, then reshuffle.
    """
    paths = [it["path"] for it in (items or []) if it.get("kind") == "video" and it.get("path")]
    if not paths:
        paths = [it["path"] for it in (items or []) if it.get("path")]
    deck = list(paths)
    random.shuffle(deck)
    return deck


def _draw_from_deck(deck, source_items):
    """
    Pop next path from session deck; if empty, reshuffle all videos.
    Returns (path, deck) — path may be None if no media.
    """
    if not deck:
        deck = _make_shuffled_video_deck(source_items)
        if deck:
            print(
                "[LEDtv] Video deck reshuffled ({} clips)".format(len(deck)),
                flush=True,
            )
    if not deck:
        return None, deck
    path = deck.pop()
    return path, deck


def _make_shuffled_gif_deck(gif_dir=None):
    """Fresh shuffle of GIF paths for this session."""
    paths = list_gifs(gif_dir)
    deck = list(paths)
    random.shuffle(deck)
    return deck


def _draw_gif_from_deck(deck, gif_dir=None):
    if not deck:
        deck = _make_shuffled_gif_deck(gif_dir)
        if deck:
            print(
                "[LEDtv] GIF deck reshuffled ({} clips)".format(len(deck)),
                flush=True,
            )
    if not deck:
        return None, deck
    return deck.pop(), deck


def _play_momentary_channel_video(
    items,
    channel,
    canvas_holder,
    matrix,
    start,
    duration_minutes,
    stop_event,
    last_path=None,
    seconds=None,
):
    """
    One channel-change beat: sequential CHn + short random-seek video clip.
    Returns (ok, last_path). ok False means session should end.
    """
    if seconds is None:
        seconds = CHANNEL_FLASH_SEC
    if _time_up(start, duration_minutes, stop_event):
        return False, last_path
    item = _pick_video_item(items, last_path=last_path)
    if item is None:
        # Fallback: black + CHn if no media
        ok = play_channel_flash(
            seconds, channel,
            stop_event=stop_event,
            session_start=start,
            duration_minutes=duration_minutes,
        )
        return ok, last_path
    path = item["path"]
    label = channel_label(channel)
    label_x, label_y = channel_position(label)
    print(
        "[LEDtv] Channel preview  {}  video={}".format(
            label, os.path.basename(path),
        ),
        flush=True,
    )
    ok = _play_video_once(
        path, canvas_holder, matrix, label, label_x, label_y,
        start, duration_minutes, stop_event,
        realtime=True,
        max_seconds=seconds,
        # CHn as usual (CHANNEL_BUG_SHOW_SEC); covers full 2s preview
        show_channel_sec=None,
        random_seek=True,
    )
    return ok, path


def play_youtube(
    url,
    duration_minutes=DEFAULT_DURATION_MIN,
    stop_event=None,
    channel=None,
    loop=True,
    fps=VIDEO_FPS,
):
    """
    Play a YouTube URL *or* a local video file onto the panel.
    Local paths under videos/ (or any absolute/relative file) skip yt-dlp.
    Aspect ratio preserved (letterbox/pillarbox — never stretched wider).
    """
    if not url:
        raise ValueError("play_youtube requires a url or local path")
    if not os.path.isfile(_FFMPEG):
        raise RuntimeError("ffmpeg not found at {}".format(_FFMPEG))

    channel = CH_START if channel is None else int(channel)
    label = channel_label(channel)
    label_x, label_y = channel_position(label)
    start = time.time()
    local = _is_local_media_path(url)

    print("[LEDtv] Video  {}x{} @ {}fps  {}  ({})".format(
        WIDTH, HEIGHT, fps, label, "local" if local else "youtube",
    ))
    print("[LEDtv] Source: {}".format(url))

    canvas_holder = [LED.Canvas]
    matrix = LED.TheMatrix

    while not _time_up(start, duration_minutes, stop_event):
        try:
            if local:
                source = _resolve_local_path(url)
            else:
                source = _youtube_stream_url(url)
        except Exception as exc:
            print("[LEDtv] Media resolve failed: {}".format(exc))
            play_color_bars(min(0.5, duration_minutes), stop_event, channel=channel)
            return

        ok = _play_video_once(
            source, canvas_holder, matrix, label, label_x, label_y,
            start, duration_minutes, stop_event,
            fps=fps, realtime=True,
        )
        if not ok or _time_up(start, duration_minutes, stop_event):
            break
        if not loop:
            break
        print("[LEDtv] Looping video…")
        time.sleep(0.3)

    LED.ClearBigLED()
    if stop_event is not None and stop_event.is_set():
        print("[LEDtv] StopEvent received")
    else:
        print("[LEDtv] Video session end ({:.1f} min)".format(
            (time.time() - start) / 60.0,
        ))


#------------------------------------------------------------------------------
#  Entry points
#------------------------------------------------------------------------------

def _normalize_url(url):
    """Empty / whitespace URL → None (means: run channel surf, not YouTube)."""
    if url is None:
        return None
    s = str(url).strip()
    return s if s else None


def PlayLEDtv(
    duration_minutes,
    stop_event=None,
    effect="channels",
    youtube_url=None,
    channel=None,
):
    """
    Run the requested LEDtv effect / channel.

    No youtube_url → always the agreed channel-surf loop
    (static after title is handled by LaunchLEDtv / boot_intro):
      static → channel flashes → random video 30s → dial → repeat
    With youtube_url → play that stream/file.
    """
    youtube_url = _normalize_url(youtube_url)
    effect = (effect or "channels").lower().strip()

    # No URL → full channel surf (ignore stale/empty effect from panel)
    if not youtube_url and effect in (
        "youtube", "yt", "video", "", "channels", "rotation",
        "random_gif", "gif", "gifs", "channel_gif", "media", "default", "tv",
    ):
        effect = "channels"

    if effect in ("white_noise", "noise", "static", "snow"):
        play_white_noise(duration_minutes, stop_event, channel=channel)
    elif effect in ("color_bars", "bars", "smpte", "offair", "off_air"):
        play_color_bars(duration_minutes, stop_event, channel=channel)
    elif effect in (
        "channels", "rotation", "random_gif", "gif", "gifs",
        "channel_gif", "media", "default", "tv",
    ):
        print("[LEDtv] Channel-surf mode (no URL)")
        play_channel_rotation(
            duration_minutes, stop_event=stop_event, start_channel=channel,
            boot_intro=True,
        )
    elif effect in ("youtube", "yt", "video"):
        if not youtube_url:
            print("[LEDtv] youtube effect needs URL — falling back to channel surf")
            play_channel_rotation(
                duration_minutes, stop_event=stop_event, start_channel=channel,
                boot_intro=True,
            )
        else:
            play_youtube(
                youtube_url,
                duration_minutes=duration_minutes,
                stop_event=stop_event,
                channel=channel,
            )
    else:
        print("[LEDtv] Unknown effect {!r} — falling back to channel surf".format(effect))
        play_channel_rotation(
            duration_minutes, stop_event=stop_event, start_channel=channel,
            boot_intro=True,
        )


def LaunchLEDtv(
    duration=DEFAULT_DURATION_MIN,
    show_intro=True,
    stop_event=None,
    effect="channels",
    youtube_url=None,
    channel=None,
):
    """
    Entry used by LEDcommander / Twitch / CLI / LEDpanel.

    No URL (default):
      1. LEDTV letters drop from the sky (Skyfall-style)
      2. Analog static 3s
      3. Channel flashes 2–5× @ 1s
      4. Random local video 30s (CHn 3s then hide)
      5. Channel up/down; repeat until duration

    With URL: title drop (if show_intro) then play that YouTube/local video.
    Default duration is 5 minutes.
    """
    youtube_url = _normalize_url(youtube_url)
    if channel is not None and str(channel).strip() == "":
        channel = None
    elif channel is not None:
        try:
            channel = int(channel)
        except (TypeError, ValueError):
            channel = None

    # No URL → force channel surf regardless of form leftovers
    if not youtube_url:
        effect = "channels"
    else:
        effect = (effect or "youtube").lower().strip()
        if effect in ("channels", "rotation", "random_gif", "default", "tv", ""):
            effect = "youtube"

    print("[LEDtv] Launch  duration={}min  effect={!r}  url={!r}  intro={}".format(
        duration, effect, youtube_url, bool(show_intro),
    ))

    if show_intro:
        play_title_drop(stop_event=stop_event)
        if stop_event is not None and stop_event.is_set():
            LED.ClearBigLED()
            return
    PlayLEDtv(
        duration,
        stop_event,
        effect=effect,
        youtube_url=youtube_url,
        channel=channel,
    )


def _parse_args(argv):
    """Minimal CLI: --youtube URL|path [--duration MIN] [--channel N] [--effect NAME] [--no-intro]

    Standalone default: no time limit (STANDALONE_DURATION_MIN).
    Commander/Twitch still default to DEFAULT_DURATION_MIN (5).
    """
    url = None
    duration = STANDALONE_DURATION_MIN
    effect = "channels"
    channel = None
    show_intro = True
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("--youtube", "-y", "--video", "-v") and i + 1 < len(argv):
            url = argv[i + 1]
            effect = "youtube"
            i += 2
        elif a in ("--duration", "-d") and i + 1 < len(argv):
            duration = float(argv[i + 1])
            i += 2
        elif a in ("--effect", "-e") and i + 1 < len(argv):
            effect = argv[i + 1]
            i += 2
        elif a in ("--channel", "-c") and i + 1 < len(argv):
            channel = int(argv[i + 1])
            i += 2
        elif a in ("--no-intro",):
            show_intro = False
            i += 1
        elif a.startswith("http://") or a.startswith("https://"):
            url = a
            effect = "youtube"
            i += 1
        elif os.path.isfile(a) or os.path.isfile(os.path.join(_HERE, a)):
            url = a
            effect = "youtube"
            i += 1
        else:
            i += 1
    return effect, url, duration, channel, show_intro


if __name__ == "__main__":
    LED.LoadConfigData()
    effect, url, duration, channel, show_intro = _parse_args(sys.argv[1:])
    print("[LEDtv] Standalone  duration={} min{}".format(
        duration,
        " (no limit)" if duration >= STANDALONE_DURATION_MIN else "",
    ), flush=True)
    LaunchLEDtv(
        duration=duration,
        show_intro=show_intro,
        stop_event=None,
        effect=effect,
        youtube_url=url,
        channel=channel,
    )

