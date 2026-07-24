# rgbmatrix-compatible software backend for LEDsim
"""
Drop-in substitutes for:
  from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics

Double-buffered canvas with SwapOnVSync; presents the front buffer into the
shared LEDsim frame (see ledsim.shared).
"""

from __future__ import annotations

import copy
from typing import Any, Optional, Tuple, Union

from . import shared


# ---------------------------------------------------------------------------
# Options (attribute bag — GPIO fields ignored in sim)
# ---------------------------------------------------------------------------

class RGBMatrixOptions:
    def __init__(self) -> None:
        self.rows = 32
        self.cols = 64
        self.chain_length = 1
        self.parallel = 1
        self.hardware_mapping = "adafruit-hat"
        self.gpio_slowdown = 3
        self.brightness = 100
        self.pwm_bits = 11
        self.pwm_lsb_nanoseconds = 130
        self.scan_mode = 0
        self.disable_hardware_pulsing = False
        self.drop_privileges = False
        self.show_refresh_rate = False


# ---------------------------------------------------------------------------
# Pixel buffer helpers
# ---------------------------------------------------------------------------

def _empty_buffer(width: int, height: int):
    """Row-major list of (r,g,b) tuples: buffer[y][x]."""
    return [[(0, 0, 0) for _ in range(width)] for _ in range(height)]


def _clamp_rgb(r, g, b) -> Tuple[int, int, int]:
    return (
        max(0, min(255, int(r))),
        max(0, min(255, int(g))),
        max(0, min(255, int(b))),
    )


def _parse_color_args(args) -> Tuple[int, int, int]:
    """Accept (r,g,b) or a single Color / tuple."""
    if len(args) == 3:
        return _clamp_rgb(args[0], args[1], args[2])
    if len(args) == 1:
        c = args[0]
        if isinstance(c, Color):
            return _clamp_rgb(c.red, c.green, c.blue)
        if isinstance(c, (tuple, list)) and len(c) >= 3:
            return _clamp_rgb(c[0], c[1], c[2])
        # Unusual: graphics.Color constructed from a single tuple in some call sites
        if hasattr(c, "red"):
            return _clamp_rgb(c.red, c.green, c.blue)
    raise TypeError(f"Expected (r,g,b) or Color, got {args!r}")


def buffer_to_rgb_bytes(buffer, width: int, height: int, brightness: int = 100) -> bytes:
    """Flatten buffer[y][x] → RGB24 bytes, applying brightness scale."""
    scale = max(0, min(100, int(brightness))) / 100.0
    out = bytearray(width * height * 3)
    i = 0
    for y in range(height):
        row = buffer[y]
        for x in range(width):
            r, g, b = row[x]
            if scale < 1.0:
                r = int(r * scale)
                g = int(g * scale)
                b = int(b * scale)
            out[i] = r
            out[i + 1] = g
            out[i + 2] = b
            i += 3
    return bytes(out)


# ---------------------------------------------------------------------------
# Canvas
# ---------------------------------------------------------------------------

class FrameCanvas:
    def __init__(self, width: int, height: int, matrix: Optional["RGBMatrix"] = None):
        self.width = width
        self.height = height
        self._matrix = matrix
        self._buf = _empty_buffer(width, height)

    def SetPixel(self, x: int, y: int, *color_args) -> None:
        x = int(x)
        y = int(y)
        if x < 0 or y < 0 or x >= self.width or y >= self.height:
            return
        r, g, b = _parse_color_args(color_args)
        self._buf[y][x] = (r, g, b)

    def Clear(self) -> None:
        self._buf = _empty_buffer(self.width, self.height)

    def Fill(self, r: int, g: int, b: int) -> None:
        rgb = _clamp_rgb(r, g, b)
        self._buf = [[rgb for _ in range(self.width)] for _ in range(self.height)]

    def SetImage(self, image, offset_x: int = 0, offset_y: int = 0, *args, **kwargs) -> None:
        """Paste a PIL Image (RGB) onto the canvas at offset."""
        try:
            img = image.convert("RGB")
        except Exception:
            img = image
        ox, oy = int(offset_x), int(offset_y)
        w, h = img.size
        px = img.load()
        for j in range(h):
            y = oy + j
            if y < 0 or y >= self.height:
                continue
            for i in range(w):
                x = ox + i
                if x < 0 or x >= self.width:
                    continue
                r, g, b = px[i, j][:3]
                self._buf[y][x] = _clamp_rgb(r, g, b)

    def _clone_buf(self):
        return [row[:] for row in self._buf]


# ---------------------------------------------------------------------------
# Matrix
# ---------------------------------------------------------------------------

class RGBMatrix:
    def __init__(self, options: Optional[RGBMatrixOptions] = None, *args, **kwargs):
        opts = options or RGBMatrixOptions()
        self._options = opts
        # Match LEDarcade ActivateRGBMatrix: width=cols, height=rows
        self.width = int(getattr(opts, "cols", 64) or 64)
        self.height = int(getattr(opts, "rows", 32) or 32)
        if getattr(opts, "chain_length", 1):
            # chain extends width (hzeller semantics); LEDarcade uses chain_length=1
            pass
        self._brightness = int(getattr(opts, "brightness", 100) or 100)
        # Front buffer (what the viewer shows); canvas is the back buffer
        self._front = _empty_buffer(self.width, self.height)
        self._canvas = FrameCanvas(self.width, self.height, matrix=self)
        # Ensure shared config dimensions match if parent set env
        name, sw, sh = shared.get_config()
        if name and (sw != self.width or sh != self.height):
            # Prefer matrix size from options; parent should match
            pass
        self._publish_front()

    # -- brightness property (commander reads/writes this) --
    @property
    def brightness(self) -> int:
        return self._brightness

    @brightness.setter
    def brightness(self, value: int) -> None:
        self._brightness = max(0, min(100, int(value)))
        # Re-present so dimming is visible without a new draw
        self._publish_front()

    def CreateFrameCanvas(self) -> FrameCanvas:
        self._canvas = FrameCanvas(self.width, self.height, matrix=self)
        return self._canvas

    def SetPixel(self, x: int, y: int, *color_args) -> None:
        """Immediate pixel write to the front buffer + shared memory."""
        x = int(x)
        y = int(y)
        if x < 0 or y < 0 or x >= self.width or y >= self.height:
            return
        r, g, b = _parse_color_args(color_args)
        self._front[y][x] = (r, g, b)
        # Scale for shared publish of single pixel
        scale = self._brightness / 100.0
        shared.publish_pixel(
            x, y,
            int(r * scale), int(g * scale), int(b * scale),
        )

    def Clear(self) -> None:
        self._front = _empty_buffer(self.width, self.height)
        if self._canvas is not None:
            self._canvas.Clear()
        shared.clear_shared()

    def Fill(self, r: int, g: int, b: int) -> None:
        rgb = _clamp_rgb(r, g, b)
        self._front = [[rgb for _ in range(self.width)] for _ in range(self.height)]
        self._publish_front()

    def SetImage(self, image, offset_x: int = 0, offset_y: int = 0, *args, **kwargs) -> None:
        """Immediate image blit onto the front buffer."""
        try:
            img = image.convert("RGB")
        except Exception:
            img = image
        ox, oy = int(offset_x), int(offset_y)
        w, h = img.size
        px = img.load()
        for j in range(h):
            y = oy + j
            if y < 0 or y >= self.height:
                continue
            for i in range(w):
                x = ox + i
                if x < 0 or x >= self.width:
                    continue
                r, g, b = px[i, j][:3]
                self._front[y][x] = _clamp_rgb(r, g, b)
        self._publish_front()

    def SwapOnVSync(self, canvas: FrameCanvas) -> FrameCanvas:
        """
        Present canvas as the new front buffer; return a canvas for further
        drawing. Matches double-buffer swap: the returned canvas is a new back
        buffer (contents are the frame just shown; most code fully redraws).
        """
        if canvas is None:
            canvas = self._canvas
        # Promote back buffer → front (copy so later canvas edits don't mutate front)
        self._front = canvas._clone_buf()
        self._publish_front()
        # Returned canvas = new back buffer (independent copy of shown frame)
        back = FrameCanvas(self.width, self.height, matrix=self)
        back._buf = canvas._clone_buf()
        self._canvas = back
        return back

    def _publish_front(self) -> None:
        rgb = buffer_to_rgb_bytes(
            self._front, self.width, self.height, self._brightness
        )
        shared.publish_frame(rgb)


# ---------------------------------------------------------------------------
# graphics submodule-style API
# ---------------------------------------------------------------------------

class Color:
    def __init__(self, *args):
        # graphics.Color(r, g, b) or Color((r,g,b)) used in one LEDarcade path
        if len(args) == 3:
            self.red, self.green, self.blue = _clamp_rgb(args[0], args[1], args[2])
        elif len(args) == 1 and isinstance(args[0], (tuple, list)) and len(args[0]) >= 3:
            self.red, self.green, self.blue = _clamp_rgb(args[0][0], args[0][1], args[0][2])
        elif len(args) == 1 and isinstance(args[0], Color):
            self.red, self.green, self.blue = args[0].red, args[0].green, args[0].blue
        else:
            self.red = self.green = self.blue = 0

    def __iter__(self):
        yield self.red
        yield self.green
        yield self.blue


def DrawLine(canvas, x1, y1, x2, y2, color) -> None:
    """Bresenham line on canvas (or matrix)."""
    if isinstance(color, Color):
        r, g, b = color.red, color.green, color.blue
    elif isinstance(color, (tuple, list)):
        r, g, b = color[0], color[1], color[2]
    else:
        r = getattr(color, "red", 255)
        g = getattr(color, "green", 255)
        b = getattr(color, "blue", 255)

    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
    dx = abs(x2 - x1)
    dy = -abs(y2 - y1)
    sx = 1 if x1 < x2 else -1
    sy = 1 if y1 < y2 else -1
    err = dx + dy
    x, y = x1, y1
    while True:
        if hasattr(canvas, "SetPixel"):
            canvas.SetPixel(x, y, r, g, b)
        if x == x2 and y == y2:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x += sx
        if e2 <= dx:
            err += dx
            y += sy


def DrawCircle(canvas, x, y, radius, color) -> None:
    """Midpoint circle on canvas."""
    if isinstance(color, Color):
        r, g, b = color.red, color.green, color.blue
    elif isinstance(color, (tuple, list)):
        r, g, b = color[0], color[1], color[2]
    else:
        r = getattr(color, "red", 255)
        g = getattr(color, "green", 255)
        b = getattr(color, "blue", 255)

    cx, cy, rad = int(x), int(y), int(radius)
    if rad < 0:
        return
    xi = rad
    yi = 0
    err = 1 - xi

    def plot(px, py):
        if hasattr(canvas, "SetPixel"):
            canvas.SetPixel(px, py, r, g, b)

    while xi >= yi:
        plot(cx + xi, cy + yi)
        plot(cx + yi, cy + xi)
        plot(cx - yi, cy + xi)
        plot(cx - xi, cy + yi)
        plot(cx - xi, cy - yi)
        plot(cx - yi, cy - xi)
        plot(cx + yi, cy - xi)
        plot(cx + xi, cy - yi)
        yi += 1
        if err < 0:
            err += 2 * yi + 1
        else:
            xi -= 1
            err += 2 * (yi - xi) + 1


def DrawText(font, canvas, x, y, color, text) -> int:
    """Minimal no-op / PIL-free stub; returns approximate width."""
    # Full font rendering is rarely required if games use LEDarcade text APIs.
    # Provide a simple pixel-font fallback for width calculation.
    if text is None:
        return 0
    s = str(text)
    # 5px wide approx per char
    return len(s) * 5


# Allow `from rgbmatrix import graphics` pattern via module attribute
class _GraphicsModule:
    Color = Color
    DrawLine = staticmethod(DrawLine)
    DrawCircle = staticmethod(DrawCircle)
    DrawText = staticmethod(DrawText)


graphics = _GraphicsModule()
