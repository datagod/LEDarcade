# LEDsim pygame viewer — owns the only desktop window
"""
Reads the shared RGB frame buffer and scales it nearest-neighbor for a
blocky LED look.

Display modes:
  scale=1  — native panel resolution (e.g. 64x32 window)
  scale>1  — integer upscale (e.g. 3 → 192x96)

Window chrome:
  borderless (default) — no title bar / OS frame (pygame icon hidden with chrome)
  bordered             — normal window with title bar

Hotkeys while running:
  N        — next program (skip current LEDcommander item)
  T        — launch LEDtv
  R        — restart LEDsim (full process restart)
  1        — launch Pinball
  2        — launch Space Explorer
  0        — native (scale 1)
  S        — restore default scaled size
  + / =    — increase scale
  - / _    — decrease scale (min 1)
  F        — toggle borderless / framed window
  A        — toggle always-on-top
  Esc      — quit

Borderless: left-drag anywhere to move the window.
Always-on-top is on by default (env LEDARCADE_SIM_TOPMOST=0 to disable).
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any, Optional, Tuple

from . import shared

# Default "zoomed" scale when user presses S (or start-up default)
DEFAULT_SCALED = 3
MIN_SCALE = 1
# Zoom keys (+/-) stop here so the panel does not shrink to an invisible 64×32
# speck. Press "0" for true native 1:1 when you really want it.
MIN_ZOOM_KEY_SCALE = 3
MAX_SCALE = 40

# Sticky top-left (screen coords). Survives set_mode; updated on drag.
_STICKY_POS: Optional[Tuple[int, int]] = None

# How often to re-assert always-on-top (seconds). Too frequent + bad HWND
# prototypes was a source of 0xC0000005 on Win x64.
_TOPMOST_REASSERT_SEC = 2.0

# Repo-local fault breadcrumb log (same file as LEDsim faulthandler)
_FAULT_LOG_PATH: Optional[str] = None


def _fault_log_path() -> str:
    global _FAULT_LOG_PATH
    if _FAULT_LOG_PATH:
        return _FAULT_LOG_PATH
    # ledsim/viewer.py → repo root
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    local = os.path.join(root, "localdata")
    os.makedirs(local, exist_ok=True)
    _FAULT_LOG_PATH = os.path.join(local, "ledsim_fault.log")
    return _FAULT_LOG_PATH


def _breadcrumb(msg: str) -> None:
    """
    Append a line to localdata/ledsim_fault.log and print it.

    Uses a separate open+append+fsync so lines survive even when faulthandler
    holds another handle. Also prints so the bat console shows last steps.
    """
    line = f"{time.strftime('%H:%M:%S')} [{os.getpid()}] {msg}"
    try:
        print(f"[LEDsim/bc] {msg}", flush=True)
    except Exception:
        pass
    try:
        path = _fault_log_path()
        with open(path, "a", encoding="utf-8", errors="replace") as f:
            f.write(line + "\n")
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError:
                pass
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Win32 user32 with correct 64-bit HWND prototypes (REQUIRED on Win x64)
# ---------------------------------------------------------------------------
# Without restype/argtypes, ctypes defaults many integers to c_int (32-bit).
# HWND values get truncated → SetWindowPos/GetWindowRect touch bad memory →
# STATUS_ACCESS_VIOLATION (-1073741819) in the LEDsim *viewer* process.

_user32_mod = None


def _win32_ready() -> bool:
    return sys.platform == "win32"


def _user32():
    """Return user32 with pointer-sized HWND prototypes bound once."""
    global _user32_mod
    if not _win32_ready():
        return None
    if _user32_mod is not None:
        return _user32_mod
    try:
        import ctypes
        from ctypes import wintypes

        u = ctypes.windll.user32

        # HWND is pointer-sized on x64
        HWND = wintypes.HWND
        BOOL = wintypes.BOOL
        UINT = wintypes.UINT
        INT = ctypes.c_int
        LPARAM = wintypes.LPARAM

        u.GetWindowRect.argtypes = [HWND, ctypes.POINTER(wintypes.RECT)]
        u.GetWindowRect.restype = BOOL

        u.SetWindowPos.argtypes = [
            HWND, HWND, INT, INT, INT, INT, UINT,
        ]
        u.SetWindowPos.restype = BOOL

        u.ShowWindow.argtypes = [HWND, INT]
        u.ShowWindow.restype = BOOL

        u.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
        u.GetCursorPos.restype = BOOL

        u.GetSystemMetrics.argtypes = [INT]
        u.GetSystemMetrics.restype = INT

        # SystemParametersInfoW — safer than MonitorFromPoint/GetMonitorInfo
        # (those HMONITOR paths were AVing the viewer: ledsim_fault.log)
        u.SystemParametersInfoW.argtypes = [
            wintypes.UINT, wintypes.UINT, ctypes.c_void_p, wintypes.UINT,
        ]
        u.SystemParametersInfoW.restype = BOOL

        u.SetProcessDPIAware.argtypes = []
        u.SetProcessDPIAware.restype = BOOL

        _user32_mod = u
        return u
    except Exception as exc:
        print(f"[LEDsim] user32 bind failed: {exc}")
        return None


def _as_hwnd(hwnd) -> Any:
    """Coerce pygame HWND to an int suitable for wintypes.HWND."""
    if hwnd is None:
        return None
    try:
        return int(hwnd)
    except Exception:
        return hwnd


# ---------------------------------------------------------------------------
# Window move helpers (pygame 2.6 often lacks display.get/set_window_position)
# ---------------------------------------------------------------------------

def _get_hwnd():
    """Windows HWND for the pygame window, or None."""
    try:
        import pygame
        info = pygame.display.get_wm_info()
        hwnd = info.get("window")
        if hwnd:
            return _as_hwnd(hwnd)
    except Exception:
        pass
    return None


def _window_rect() -> Optional[Tuple[int, int, int, int]]:
    """Screen rect (left, top, right, bottom) via Win32 — most reliable on Windows."""
    if _win32_ready():
        hwnd = _get_hwnd()
        u = _user32()
        if hwnd and u is not None:
            try:
                from ctypes import wintypes, byref

                rect = wintypes.RECT()
                if u.GetWindowRect(hwnd, byref(rect)):
                    return (
                        int(rect.left),
                        int(rect.top),
                        int(rect.right),
                        int(rect.bottom),
                    )
            except Exception:
                pass
    return None


def _window_position() -> Optional[Tuple[int, int]]:
    """Return (x, y) of the top-left of the window, or None."""
    # Win32 first (accurate for borderless drag). No pygame._sdl2.Window.
    rect = _window_rect()
    if rect is not None:
        return rect[0], rect[1]
    try:
        import pygame
        if hasattr(pygame.display, "get_window_position"):
            return tuple(pygame.display.get_window_position())  # type: ignore[return-value]
    except Exception:
        pass
    if _STICKY_POS is not None:
        return _STICKY_POS
    return None


def _cursor_screen_pos() -> Optional[Tuple[int, int]]:
    """Absolute screen cursor position (needed for borderless drag)."""
    u = _user32()
    if u is not None:
        try:
            from ctypes import byref, wintypes

            pt = wintypes.POINT()
            if u.GetCursorPos(byref(pt)):
                return int(pt.x), int(pt.y)
        except Exception:
            pass
    return None


def _window_size() -> Optional[Tuple[int, int]]:
    """Current outer size of the window, or client size fallback."""
    rect = _window_rect()
    if rect is not None:
        return rect[2] - rect[0], rect[3] - rect[1]
    try:
        import pygame
        surf = pygame.display.get_surface()
        if surf is not None:
            return int(surf.get_width()), int(surf.get_height())
    except Exception:
        pass
    return None


def _primary_work_area() -> Optional[Tuple[int, int, int, int]]:
    """
    Primary monitor work area (left, top, right, bottom).

    Uses SPI_GETWORKAREA only — no HMONITOR APIs (those caused 0xC0000005
    in _window_is_on_any_monitor / MonitorFromPoint on Win x64).
    """
    u = _user32()
    if u is None:
        return None
    try:
        from ctypes import byref, wintypes

        SPI_GETWORKAREA = 0x0030
        rect = wintypes.RECT()
        if u.SystemParametersInfoW(SPI_GETWORKAREA, 0, byref(rect), 0):
            return int(rect.left), int(rect.top), int(rect.right), int(rect.bottom)
    except Exception:
        pass
    return None


def _virtual_screen() -> Optional[Tuple[int, int, int, int]]:
    """Virtual screen bounds covering all monitors (left, top, right, bottom)."""
    u = _user32()
    if u is None:
        return None
    try:
        # SM_XVIRTUALSCREEN=76, SM_YVIRTUALSCREEN=77,
        # SM_CXVIRTUALSCREEN=78, SM_CYVIRTUALSCREEN=79
        vx = int(u.GetSystemMetrics(76))
        vy = int(u.GetSystemMetrics(77))
        vw = int(u.GetSystemMetrics(78))
        vh = int(u.GetSystemMetrics(79))
        if vw <= 0 or vh <= 0:
            return None
        return vx, vy, vx + vw, vy + vh
    except Exception:
        return None


def _work_area_for_point(x: int, y: int) -> Optional[Tuple[int, int, int, int]]:
    """Work area near (x,y) — primary work area is good enough for clamping."""
    return _primary_work_area() or _virtual_screen()


def _work_area_for_window() -> Optional[Tuple[int, int, int, int]]:
    """Work area for clamping the pygame window."""
    return _primary_work_area() or _virtual_screen()


def _clamp_window_pos(x: int, y: int, win_w: int, win_h: int) -> Tuple[int, int]:
    """Force the whole window (or most of it) onto the work area."""
    area = _work_area_for_point(x + win_w // 2, y + win_h // 2)
    if area is None:
        area = _work_area_for_window()
    if area is None:
        left, top = 0, 0
        u = _user32()
        try:
            if u is not None:
                right = int(u.GetSystemMetrics(0))
                bottom = int(u.GetSystemMetrics(1))
            else:
                right, bottom = 1920, 1080
        except Exception:
            right, bottom = 1920, 1080
    else:
        left, top, right, bottom = area

    # Prefer fully on-screen; if larger than work area, pin top-left into it
    if win_w <= (right - left):
        x = max(left, min(right - win_w, int(x)))
    else:
        x = left
    if win_h <= (bottom - top):
        y = max(top, min(bottom - win_h, int(y)))
    else:
        y = top
    return int(x), int(y)


def _hwnd_insert_after(always_on_top: bool):
    """HWND_TOPMOST / HWND_NOTOPMOST as pointer-sized values."""
    from ctypes import wintypes
    # -1 / -2 must be full-width HWNDs on x64
    val = -1 if always_on_top else -2
    return wintypes.HWND(val)


def _set_window_pos_topmost(x: int, y: int, always_on_top: bool = True) -> bool:
    """
    Move the window and set Z-order in one Win32 call.
    Critical: never use HWND_TOP (0) when topmost is desired — that clears TOPMOST.
    """
    if not _win32_ready():
        return _set_window_position(x, y)

    hwnd = _get_hwnd()
    u = _user32()
    if not hwnd or u is None:
        return _set_window_position(x, y)
    try:
        SWP_NOSIZE = 0x0001
        SWP_SHOWWINDOW = 0x0040
        SWP_NOACTIVATE = 0x0010
        ok = u.SetWindowPos(
            hwnd,
            _hwnd_insert_after(always_on_top),
            int(x), int(y), 0, 0,
            SWP_NOSIZE | SWP_SHOWWINDOW | SWP_NOACTIVATE,
        )
        return bool(ok)
    except Exception:
        return _set_window_position(x, y)


def _set_window_position(x: int, y: int) -> bool:
    """Move window top-left via pygame if available (no SDL2 Window API)."""
    try:
        import pygame
        if hasattr(pygame.display, "set_window_position"):
            pygame.display.set_window_position(int(x), int(y))  # type: ignore[attr-defined]
            return True
    except Exception:
        pass
    return False


def _move_window_screen(x: int, y: int) -> bool:
    """
    Move the window to screen (x, y) without resizing or changing Z-order.

    Uses Win32 SetWindowPos(SWP_NOSIZE|SWP_NOZORDER|SWP_NOACTIVATE) only —
    no TOPMOST, no ShowWindow, no SDL2. Safe path for borderless click-drag.
    """
    global _STICKY_POS
    x, y = int(x), int(y)
    u = _user32()
    hwnd = _get_hwnd()
    if u is not None and hwnd:
        try:
            SWP_NOSIZE = 0x0001
            SWP_NOZORDER = 0x0004
            SWP_NOACTIVATE = 0x0010
            ok = u.SetWindowPos(
                hwnd,
                0,  # ignored with SWP_NOZORDER
                x, y, 0, 0,
                SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE,
            )
            if ok:
                _STICKY_POS = (x, y)
                return True
        except Exception:
            pass
    if _set_window_position(x, y):
        _STICKY_POS = (x, y)
        return True
    return False


def _ensure_dpi_aware() -> None:
    """Best-effort DPI awareness — failures are ignored (never fatal)."""
    if not _win32_ready():
        return
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            import ctypes
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def _show_window() -> None:
    """No-op: Win32 ShowWindow on the SDL HWND was unsafe; SDL owns visibility."""
    return


def _move_window_only(x: int, y: int, always_on_top: bool = True) -> bool:
    """Move without resize (drag). always_on_top ignored (disabled for stability)."""
    return _move_window_screen(int(x), int(y))


def _place_window(
    x: int,
    y: int,
    win_w: int,
    win_h: int,
    always_on_top: bool = True,
) -> Tuple[int, int]:
    """Clamp and move; size is owned by set_mode."""
    global _STICKY_POS
    x, y = _clamp_window_pos(int(x), int(y), int(win_w), int(win_h))
    _STICKY_POS = (x, y)
    _move_window_screen(x, y)
    return x, y


def _set_always_on_top(enabled: bool = True) -> bool:
    """
    Pin (or unpin) the viewer above other windows via Win32 only.

    Uses SetWindowPos(HWND_TOPMOST / HWND_NOTOPMOST) — never pygame._sdl2
    always_on_top (that path AVed event.get on some Windows hosts).
    """
    if not _win32_ready():
        return False
    hwnd = _get_hwnd()
    u = _user32()
    if not hwnd or u is None:
        return False
    try:
        SWP_NOSIZE = 0x0001
        SWP_NOMOVE = 0x0002
        SWP_NOACTIVATE = 0x0010
        SWP_SHOWWINDOW = 0x0040
        ok = u.SetWindowPos(
            hwnd,
            _hwnd_insert_after(bool(enabled)),
            0, 0, 0, 0,
            SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE | SWP_SHOWWINDOW,
        )
        return bool(ok)
    except Exception as exc:
        _breadcrumb(f"set_always_on_top failed: {exc}")
        return False


def _window_is_on_any_monitor() -> bool:
    """
    True if any part of the window intersects the virtual screen.

    Uses GetSystemMetrics virtual-screen bounds only — never HMONITOR
    (MonitorFromPoint/GetMonitorInfoW AVed the viewer process).
    """
    try:
        rect = _window_rect()
        if rect is None:
            return True  # unknown — assume ok
        rx, ry, rr, rb = rect
        area = _virtual_screen() or _primary_work_area()
        if area is None:
            return True
        left, top, right, bottom = area
        # Any intersection with virtual/primary area counts as "on screen"
        if rr < left or rx > right or rb < top or ry > bottom:
            return False
        return True
    except Exception:
        return True


def _screen_mouse_pos() -> Optional[Tuple[int, int]]:
    """Absolute screen coordinates of the cursor."""
    u = _user32()
    if u is not None:
        try:
            from ctypes import byref, wintypes

            pt = wintypes.POINT()
            if u.GetCursorPos(byref(pt)):
                return int(pt.x), int(pt.y)
        except Exception:
            pass
    # Fallback: window-relative + window origin
    try:
        import pygame

        origin = _window_position()
        if origin is None:
            return None
        mx, my = pygame.mouse.get_pos()
        return origin[0] + mx, origin[1] + my
    except Exception:
        return None


def _mode_label(width: int, height: int, scale: int) -> str:
    win_w, win_h = width * scale, height * scale
    if scale <= 1:
        return f"{width}x{height} native"
    return f"{width}x{height} x{scale} ({win_w}x{win_h})"


def _set_caption(title: str, width: int, height: int, scale: int, borderless: bool) -> None:
    import pygame
    mode = _mode_label(width, height, scale)
    frame = "borderless" if borderless else "windowed"
    pygame.display.set_caption(f"{title} — {mode} [{frame}]")


def _apply_blank_icon() -> None:
    """Replace the default pygame logo with a plain black icon (taskbar / alt-tab)."""
    import pygame
    try:
        icon = pygame.Surface((32, 32))
        icon.fill((0, 0, 0))
        # Tiny green corner so it still shows as "a panel" if the taskbar is visible
        icon.fill((0, 180, 0), rect=pygame.Rect(12, 12, 8, 8))
        pygame.display.set_icon(icon)
    except Exception:
        pass


def _display_flags(borderless: bool) -> int:
    import pygame
    flags = 0
    if borderless:
        flags |= pygame.NOFRAME
    return flags


def _default_borderless() -> bool:
    """Default: no window chrome (borderless panel)."""
    return _env_bool("LEDARCADE_SIM_BORDERLESS", True)


def _default_topmost() -> bool:
    """
    On by default so the panel stays visible over other apps.
    Uses Win32 TOPMOST (not SDL2). Set LEDARCADE_SIM_TOPMOST=0 to disable.
    """
    return _env_bool("LEDARCADE_SIM_TOPMOST", True)


# Debounce window resizes (holding +/- must not spam set_mode)
_RESIZE_COOLDOWN_SEC = 0.18
_last_resize_mono = 0.0


def _open_display(
    width: int,
    height: int,
    scale: int,
    title: str,
    borderless: bool,
    always_on_top: bool = False,
):
    """
    Create the viewer window once — minimal pygame path.

    No display.quit/reinit, no Win32 SetWindowPos at create (those AVed
    event.get). Position via SDL_VIDEO_WINDOW_POS only.
    """
    global _STICKY_POS
    import pygame

    win_w = width * scale
    win_h = height * scale

    area = _primary_work_area() or _virtual_screen()
    if area is not None:
        left, top, right, bottom = area
        new_x = left + max(0, (right - left - win_w) // 2)
        new_y = top + max(0, (bottom - top - win_h) // 2)
    else:
        new_x, new_y = 80, 80
    _STICKY_POS = (new_x, new_y)
    os.environ["SDL_VIDEO_WINDOW_POS"] = f"{new_x},{new_y}"
    os.environ.setdefault("SDL_VIDEODRIVER", "windows")

    _breadcrumb(f"open_display set_mode {win_w}x{win_h} borderless={borderless}")
    print(f"[LEDsim] opening display {win_w}x{win_h} borderless={borderless}…", flush=True)

    if not pygame.get_init():
        pygame.init()
    elif not pygame.display.get_init():
        pygame.display.init()

    flags = _display_flags(borderless)
    screen = pygame.display.set_mode((win_w, win_h), flags)
    _set_caption(title, width, height, scale, borderless)
    _breadcrumb("open_display set_mode ok")
    print(f"[LEDsim] Window size {win_w}x{win_h} (pos hint {new_x},{new_y})")
    return screen, win_w, win_h


def _resize_display(
    width: int,
    height: int,
    scale: int,
    title: str,
    borderless: bool,
    force: bool = False,
):
    """
    Resize the OS window to panel*scale (in-place set_mode, no display.quit).

    Preserves the *center* of the previous window so shrinking to 64x32 does not
    jump off-screen or into a corner where a tiny borderless panel "vanishes".
    After set_mode, re-pins with Win32 move (SDL often ignores env pos on resize).
    """
    global _STICKY_POS, _last_resize_mono
    import pygame

    now = time.monotonic()
    if not force and (now - _last_resize_mono) < _RESIZE_COOLDOWN_SEC:
        return None
    _last_resize_mono = now

    win_w = max(1, int(width) * int(scale))
    win_h = max(1, int(height) * int(scale))

    # Center-preserving resize from current rect (or sticky)
    old = _window_rect()
    if old is not None:
        ol, ot, orr, ob = old
        ocx = (ol + orr) // 2
        ocy = (ot + ob) // 2
        new_x = ocx - win_w // 2
        new_y = ocy - win_h // 2
    elif _STICKY_POS is not None:
        # Treat sticky as top-left of previous large panel: keep that corner
        new_x, new_y = _STICKY_POS
    else:
        new_x, new_y = 80, 80

    new_x, new_y = _clamp_window_pos(int(new_x), int(new_y), win_w, win_h)
    # Tiny windows: if clamp pinned them oddly, snap near work-area center
    if win_w <= 128 or win_h <= 64:
        area = _primary_work_area() or _virtual_screen()
        if area is not None:
            left, top, right, bottom = area
            # Prefer keeping near previous center if still on-screen
            if old is not None:
                pass  # already center-preserved + clamped
            else:
                new_x = left + max(0, (right - left - win_w) // 2)
                new_y = top + max(0, (bottom - top - win_h) // 2)
                new_x, new_y = _clamp_window_pos(new_x, new_y, win_w, win_h)

    _STICKY_POS = (new_x, new_y)
    os.environ["SDL_VIDEO_WINDOW_POS"] = f"{new_x},{new_y}"

    _breadcrumb(
        f"resize set_mode {win_w}x{win_h} scale={scale} borderless={borderless} "
        f"pos=({new_x},{new_y})"
    )
    try:
        screen = pygame.display.set_mode((win_w, win_h), _display_flags(borderless))
    except Exception as exc:
        _breadcrumb(f"resize set_mode failed: {exc}")
        print(f"[LEDsim] Resize failed: {exc}")
        return None

    # SDL often places tiny NOFRAME windows at (0,0) or off-screen — re-pin
    _move_window_screen(new_x, new_y)
    # Second pin after a short pump so HWND is ready
    try:
        pygame.event.pump()
    except Exception:
        pass
    _move_window_screen(new_x, new_y)

    _set_caption(title, width, height, scale, borderless)
    _breadcrumb(f"resize ok {win_w}x{win_h} @ ({new_x},{new_y})")
    print(
        f"[LEDsim] Display: {_mode_label(width, height, scale)} "
        f"@ ({new_x},{new_y}) size {win_w}x{win_h}",
        flush=True,
    )
    if scale <= 2:
        print(
            f"[LEDsim] Native/tiny panel is only {win_w}x{win_h} px — "
            f"look at ({new_x},{new_y}). Press S to restore large size.",
            flush=True,
        )
    return screen, win_w, win_h


def _send_command(command_queue: Optional[Any], command: dict, label: str) -> None:
    """Put a command dict onto the LEDcommander queue."""
    if command_queue is None:
        print(f"[LEDsim] {label}: no command queue (commander not running)")
        return
    try:
        command_queue.put(command)
        print(f"[LEDsim] {label} → LEDcommander {command}")
    except Exception as exc:
        print(f"[LEDsim] {label} failed: {exc}")


def _request_next(command_queue: Optional[Any]) -> None:
    """Ask LEDcommander to stop the current mode and run the next playlist item."""
    _send_command(command_queue, {"Action": "next"}, "Next")


def _request_ledtv(command_queue: Optional[Any]) -> None:
    """Launch LEDtv (channel-surf / local video mode; default duration from commander)."""
    _send_command(
        command_queue,
        {"Action": "launch_ledtv"},
        "LEDtv",
    )


def _request_pinball(command_queue: Optional[Any]) -> None:
    """Launch Pinball table simulation."""
    _send_command(
        command_queue,
        {"Action": "launch_pinball", "duration": 10},
        "Pinball",
    )


def _request_spaceexplorer(command_queue: Optional[Any]) -> None:
    """Launch Space Explorer."""
    _send_command(
        command_queue,
        {"Action": "launch_spaceexplorer", "duration": 10},
        "SpaceExplorer",
    )


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or str(raw).strip() == "":
        return default
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


def run_viewer(
    stop_event,
    width: int = 64,
    height: int = 32,
    scale: Optional[int] = None,
    title: str = "LEDsim",
    fps: int = 60,
    default_scaled: Optional[int] = None,
    command_queue: Optional[Any] = None,
    borderless: Optional[bool] = None,
) -> str:
    """
    Blocking viewer loop (main process).

    Returns:
      "quit"     — Esc / window close / stop_event
      "restart"  — R key (caller should restart the sim process)

    scale:
      1  = native 64x32 (or panel size) window
      N  = integer nearest-neighbor scale

    borderless:
      True  = no title bar / window chrome (pygame.NOFRAME)
      False = normal framed window
    """
    if scale is None:
        scale = int(os.environ.get("LEDARCADE_SIM_SCALE", str(DEFAULT_SCALED)))
    scale = max(MIN_SCALE, min(MAX_SCALE, int(scale)))

    if default_scaled is None:
        try:
            default_scaled = int(os.environ.get("LEDARCADE_SIM_DEFAULT_SCALE", str(DEFAULT_SCALED)))
        except ValueError:
            default_scaled = DEFAULT_SCALED
    default_scaled = max(2, min(MAX_SCALE, int(default_scaled)))

    if borderless is None:
        borderless = _default_borderless()

    always_on_top = _default_topmost()
    # DPI awareness can interact badly with SDL on some Win boxes — optional
    if _env_bool("LEDARCADE_SIM_DPI_AWARE", False):
        _ensure_dpi_aware()

    try:
        import pygame
    except ImportError:
        print("[LEDsim] pygame is required for the viewer. Install with: pip install pygame")
        stop_event.set()
        return "quit"

    shared.get_config()

    try:
        screen, win_w, win_h = _open_display(
            width, height, scale, title, borderless,
            always_on_top=always_on_top,
        )
    except pygame.error as exc:
        print(f"[LEDsim] Could not open display window: {exc}")
        _breadcrumb(f"open_display failed: {exc}")
        stop_event.set()
        return "quit"

    # Win32 TOPMOST only — do not use pygame._sdl2 always_on_top
    if always_on_top:
        ok = _set_always_on_top(True)
        print(
            f"[LEDsim] Always-on-top: {'on' if ok else 'requested (Win32 may be unavailable)'}"
        )
    else:
        print("[LEDsim] Always-on-top: off (LEDARCADE_SIM_TOPMOST=0)")

    clock = pygame.time.Clock()
    panel = pygame.Surface((width, height))
    last_topmost_assert = time.monotonic()
    _breadcrumb(f"viewer start scale={scale} window={win_w}x{win_h} borderless={borderless}")

    def _apply_scale(new_scale: int) -> bool:
        """Shrink/grow the entire OS window to panel * new_scale."""
        nonlocal screen, win_w, win_h, scale, panel, dragging, drag_grab
        new_scale = max(MIN_SCALE, min(MAX_SCALE, int(new_scale)))
        if new_scale == scale:
            return True
        # Key "1" / large jumps: never debounce away
        force = abs(new_scale - scale) >= 2 or new_scale <= 2
        result = _resize_display(
            width, height, new_scale, title, borderless, force=force,
        )
        if result is None:
            print("[LEDsim] Resize debounced — try again in a moment")
            return False
        screen, win_w, win_h = result
        scale = new_scale
        # Fresh panel after set_mode (safer than reusing)
        panel = pygame.Surface((width, height))
        dragging = False
        drag_grab = None
        if always_on_top:
            _set_always_on_top(True)
        return True

    def _toggle_frame() -> None:
        nonlocal screen, win_w, win_h, borderless, panel, dragging, drag_grab
        new_borderless = not borderless
        _breadcrumb(f"frame toggle → borderless={new_borderless}")
        try:
            result = _resize_display(
                width, height, scale, title, new_borderless, force=True,
            )
            if result is None:
                return
            screen, win_w, win_h = result
            borderless = new_borderless
            panel = pygame.Surface((width, height))
            dragging = False
            drag_grab = None
            if always_on_top:
                _set_always_on_top(True)
            print(
                f"[LEDsim] Display: {_mode_label(width, height, scale)} "
                f"[{'borderless' if borderless else 'windowed'}]"
            )
        except Exception as exc:
            _breadcrumb(f"frame toggle failed: {exc}")
            print(f"[LEDsim] Frame toggle failed: {exc}")

    # Click-drag moves borderless window (SDL2 only — no Win32 SetWindowPos)
    dragging = False
    drag_grab: Optional[Tuple[int, int]] = None

    last_counter = -1
    frame_label = "borderless" if borderless else "windowed"
    print(f"[LEDsim] Viewer started — {_mode_label(width, height, scale)} [{frame_label}]")
    print(
        "[LEDsim] Keys: N=next  T=LEDtv  1=Pinball  2=SpaceExplorer  "
        "R=restart  0=native  S=scaled  +/- zoom  F=frame  A=topmost  Esc=quit"
    )
    print("[LEDsim] Mouse: left-click and drag anywhere to move the panel")

    exit_reason = "quit"
    frame_i = 0
    global _STICKY_POS
    try:
        while not stop_event.is_set():
            frame_i += 1

            if frame_i == 1:
                _breadcrumb("before first event.get")
            try:
                events = pygame.event.get()
            except Exception:
                events = []
            if frame_i == 1:
                _breadcrumb(f"first event.get ok n={len(events)}")

            for event in events:
                if event.type == pygame.QUIT:
                    stop_event.set()
                    exit_reason = "quit"
                    break

                # --- Click-drag moves the borderless window (screen coords) ---
                # grab = cursor_screen - window_topleft; both in screen space so
                # client-relative event.pos cannot fight the moving window.
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    sp = _cursor_screen_pos()
                    wp = _window_position()
                    if sp is not None and wp is not None:
                        drag_grab = (sp[0] - wp[0], sp[1] - wp[1])
                        dragging = True
                        _STICKY_POS = (int(wp[0]), int(wp[1]))
                    else:
                        drag_grab = None
                        dragging = False
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    dragging = False
                    drag_grab = None
                    pos = _window_position()
                    if pos is not None:
                        _STICKY_POS = (int(pos[0]), int(pos[1]))
                elif event.type == pygame.MOUSEMOTION and dragging and drag_grab is not None:
                    sp = _cursor_screen_pos()
                    if sp is not None:
                        gx, gy = drag_grab
                        nx = sp[0] - gx
                        ny = sp[1] - gy
                        _move_window_screen(nx, ny)

                if event.type != pygame.KEYDOWN:
                    continue

                if event.key == pygame.K_ESCAPE:
                    stop_event.set()
                    exit_reason = "quit"
                    break

                # R = full LEDsim restart (process reload via LEDsim.py / run_ledsim.bat)
                key_ch = (getattr(event, "unicode", None) or "").lower()
                if event.key in (pygame.K_r,) or key_ch == "r":
                    print("[LEDsim] Restart requested (R) — reloading LEDsim")
                    stop_event.set()
                    exit_reason = "restart"
                    break

                if event.key == pygame.K_f:
                    _toggle_frame()
                    continue

                if event.key == pygame.K_a:
                    always_on_top = not always_on_top
                    ok = _set_always_on_top(always_on_top)
                    print(
                        f"[LEDsim] Always-on-top: "
                        f"{'on' if always_on_top else 'off'}"
                        f"{'' if ok else ' (may be unsupported)'}"
                    )
                    continue

                if event.key == pygame.K_n:
                    _request_next(command_queue)
                    continue

                if event.key == pygame.K_t:
                    _request_ledtv(command_queue)
                    continue

                # Game shortcuts (main number row + keypad)
                if event.key == pygame.K_1 or event.key == pygame.K_KP1:
                    _request_pinball(command_queue)
                    continue

                if event.key == pygame.K_2 or event.key == pygame.K_KP2:
                    _request_spaceexplorer(command_queue)
                    continue

                # 0 = native 1:1 scale (was key 1 before game shortcuts)
                if event.key == pygame.K_0 or event.key == pygame.K_KP0:
                    _apply_scale(1)
                    continue

                # +/- resize the whole window to panel * scale
                if event.key == pygame.K_s:
                    _apply_scale(default_scaled)

                elif event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                    if scale < MAX_SCALE:
                        _apply_scale(scale + 1)

                elif event.key in (pygame.K_MINUS, pygame.K_UNDERSCORE, pygame.K_KP_MINUS):
                    if scale > MIN_ZOOM_KEY_SCALE:
                        _apply_scale(scale - 1)
                    elif scale > MIN_SCALE:
                        print(
                            f"[LEDsim] Zoom floor is x{MIN_ZOOM_KEY_SCALE} "
                            f"({width * MIN_ZOOM_KEY_SCALE}x{height * MIN_ZOOM_KEY_SCALE}). "
                            f"Press 0 for true native {width}x{height}."
                        )

            if stop_event.is_set():
                break

            try:
                counter, rgb = shared.read_frame()
            except Exception:
                counter, rgb = last_counter, b""
            need = width * height * 3
            if counter != last_counter and len(rgb) == need:
                last_counter = counter
                try:
                    frame = pygame.image.frombytes(bytes(rgb), (width, height), "RGB")
                    panel.blit(frame, (0, 0))
                except Exception:
                    try:
                        i = 0
                        for y in range(height):
                            for x in range(width):
                                panel.set_at(
                                    (x, y),
                                    (rgb[i], rgb[i + 1], rgb[i + 2]),
                                )
                                i += 3
                    except Exception:
                        pass

            # Fill the entire window (window size == panel * scale)
            try:
                if scale <= 1:
                    screen.blit(panel, (0, 0))
                else:
                    scaled = pygame.transform.scale(panel, (win_w, win_h))
                    screen.blit(scaled, (0, 0))
                # Tiny native windows disappear into dark desktops — outline them
                if scale <= 2 and win_w > 2 and win_h > 2:
                    pygame.draw.rect(
                        screen, (0, 220, 80), (0, 0, win_w - 1, win_h - 1), 1
                    )
                pygame.display.flip()
            except Exception:
                pass
            # Periodically re-assert TOPMOST so other apps don't bury the panel
            if always_on_top:
                now_m = time.monotonic()
                if now_m - last_topmost_assert >= _TOPMOST_REASSERT_SEC:
                    _set_always_on_top(True)
                    last_topmost_assert = now_m
            clock.tick(fps)
    finally:
        _breadcrumb("viewer finally / closing")
        try:
            pygame.display.quit()
            pygame.quit()
        except Exception:
            pass
        print("[LEDsim] Viewer closed")
        stop_event.set()

    return exit_reason