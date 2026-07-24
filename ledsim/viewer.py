# LEDsim pygame viewer — owns the only desktop window
"""
Reads the shared RGB frame buffer and scales it nearest-neighbor for a
blocky LED look.

Display modes:
  scale=1  — native panel resolution (e.g. 64x32 window)
  scale>1  — integer upscale (e.g. 15 → 960x480)

Window chrome:
  borderless (default) — no title bar / OS frame (pygame icon hidden with chrome)
  bordered             — normal window with title bar

Hotkeys while running:
  N        — next program (skip current LEDcommander item)
  T        — launch LEDtv
  1        — native (scale 1)
  S        — restore default scaled size
  + / =    — increase scale
  - / _    — decrease scale (min 1)
  F        — toggle borderless / framed window
  Esc      — quit

Borderless: left-drag anywhere to move the window.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Optional, Tuple

from . import shared

# Default "zoomed" scale when user presses S (or start-up default)
DEFAULT_SCALED = 15
MIN_SCALE = 1
MAX_SCALE = 40


# ---------------------------------------------------------------------------
# Window move helpers (pygame 2.6 often lacks display.get/set_window_position)
# ---------------------------------------------------------------------------

def _get_hwnd():
    """Windows HWND for the pygame window, or None."""
    try:
        import pygame
        info = pygame.display.get_wm_info()
        return info.get("window")
    except Exception:
        return None


def _window_position() -> Optional[Tuple[int, int]]:
    """Return (x, y) of the top-left of the window, or None."""
    import pygame

    if hasattr(pygame.display, "get_window_position"):
        try:
            return tuple(pygame.display.get_window_position())  # type: ignore[return-value]
        except Exception:
            pass

    # pygame._sdl2 (when built with SDL2 helpers)
    try:
        from pygame._sdl2.video import Window  # type: ignore

        win = Window.from_display_module()
        return tuple(win.position)  # type: ignore[return-value]
    except Exception:
        pass

    # Win32
    if sys.platform == "win32":
        hwnd = _get_hwnd()
        if hwnd:
            try:
                import ctypes
                from ctypes import wintypes

                rect = wintypes.RECT()
                if ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                    return int(rect.left), int(rect.top)
            except Exception:
                pass
    return None


def _set_window_position(x: int, y: int) -> bool:
    """Move the window top-left to (x, y). Returns True on success."""
    import pygame

    if hasattr(pygame.display, "set_window_position"):
        try:
            pygame.display.set_window_position(int(x), int(y))  # type: ignore[attr-defined]
            return True
        except Exception:
            pass

    try:
        from pygame._sdl2.video import Window  # type: ignore

        win = Window.from_display_module()
        win.position = (int(x), int(y))
        return True
    except Exception:
        pass

    if sys.platform == "win32":
        hwnd = _get_hwnd()
        if hwnd:
            try:
                import ctypes

                # SWP_NOSIZE | SWP_NOZORDER
                SWP_NOSIZE = 0x0001
                SWP_NOZORDER = 0x0004
                ok = ctypes.windll.user32.SetWindowPos(
                    hwnd, 0, int(x), int(y), 0, 0, SWP_NOSIZE | SWP_NOZORDER
                )
                return bool(ok)
            except Exception:
                pass
    return False


def _screen_mouse_pos() -> Optional[Tuple[int, int]]:
    """Absolute screen coordinates of the cursor."""
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            pt = wintypes.POINT()
            if ctypes.windll.user32.GetCursorPos(ctypes.byref(pt)):
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


def _resize_window(width: int, height: int, scale: int, title: str, borderless: bool):
    """Create/resize the display surface for the current scale and frame mode."""
    import pygame
    win_w = width * scale
    win_h = height * scale
    screen = pygame.display.set_mode((win_w, win_h), _display_flags(borderless))
    _set_caption(title, width, height, scale, borderless)
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
) -> None:
    """
    Blocking viewer loop (main process).

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
        borderless = _env_bool("LEDARCADE_SIM_BORDERLESS", True)

    try:
        import pygame
    except ImportError:
        print("[LEDsim] pygame is required for the viewer. Install with: pip install pygame")
        stop_event.set()
        return

    shared.get_config()

    pygame.display.init()
    _apply_blank_icon()
    try:
        screen, win_w, win_h = _resize_window(width, height, scale, title, borderless)
    except pygame.error as exc:
        print(f"[LEDsim] Could not open display window: {exc}")
        stop_event.set()
        return

    clock = pygame.time.Clock()
    panel = pygame.Surface((width, height))

    # Click-drag to move (borderless has no title bar; also handy windowed)
    dragging = False
    drag_grab: Optional[Tuple[int, int]] = None  # cursor offset inside window on press

    last_counter = -1
    frame_label = "borderless" if borderless else "windowed"
    print(f"[LEDsim] Viewer started — {_mode_label(width, height, scale)} [{frame_label}]")
    print("[LEDsim] Keys: N=next  T=LEDtv  1=native  S=scaled  +/- zoom  F=frame  Esc=quit")
    print("[LEDsim] Mouse: left-click and drag to move the window")

    try:
        while not stop_event.is_set():
            try:
                events = pygame.event.get()
            except Exception:
                events = []

            for event in events:
                if event.type == pygame.QUIT:
                    stop_event.set()
                    break

                # --- mouse: click-and-drag moves the window ---
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    # Record where inside the window the user grabbed
                    drag_grab = event.pos  # (mx, my) relative to window client area
                    dragging = True
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    dragging = False
                    drag_grab = None
                elif event.type == pygame.MOUSEMOTION and dragging and drag_grab is not None:
                    screen_pos = _screen_mouse_pos()
                    if screen_pos is not None:
                        # Place window so grab point stays under the cursor
                        gx, gy = drag_grab
                        new_x = screen_pos[0] - gx
                        new_y = screen_pos[1] - gy
                        _set_window_position(new_x, new_y)
                    else:
                        # Last resort: relative motion from event
                        dx, dy = getattr(event, "rel", (0, 0))
                        origin = _window_position()
                        if origin is not None and (dx or dy):
                            _set_window_position(origin[0] + dx, origin[1] + dy)

                if event.type != pygame.KEYDOWN:
                    continue

                if event.key == pygame.K_ESCAPE:
                    stop_event.set()
                    break

                # Toggle frame / borderless
                if event.key == pygame.K_f:
                    borderless = not borderless
                    dragging = False
                    drag_grab = None
                    try:
                        screen, win_w, win_h = _resize_window(
                            width, height, scale, title, borderless
                        )
                        print(
                            f"[LEDsim] Display: {_mode_label(width, height, scale)} "
                            f"[{'borderless' if borderless else 'windowed'}]"
                        )
                    except pygame.error as exc:
                        print(f"[LEDsim] Resize failed: {exc}")
                    continue

                # Next program in LEDcommander rotation / queue
                if event.key == pygame.K_n:
                    _request_next(command_queue)
                    continue

                # Launch LEDtv
                if event.key == pygame.K_t:
                    _request_ledtv(command_queue)
                    continue

                # Native 1:1 (key "1")
                if event.key == pygame.K_1 or event.key == pygame.K_KP1:
                    if scale != 1:
                        scale = 1
                        try:
                            screen, win_w, win_h = _resize_window(
                                width, height, scale, title, borderless
                            )
                            print(f"[LEDsim] Display: {_mode_label(width, height, scale)}")
                        except pygame.error as exc:
                            print(f"[LEDsim] Resize failed: {exc}")

                # Restore default scaled zoom
                elif event.key == pygame.K_s:
                    if scale != default_scaled:
                        scale = default_scaled
                        try:
                            screen, win_w, win_h = _resize_window(
                                width, height, scale, title, borderless
                            )
                            print(f"[LEDsim] Display: {_mode_label(width, height, scale)}")
                        except pygame.error as exc:
                            print(f"[LEDsim] Resize failed: {exc}")

                # Zoom in
                elif event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                    if scale < MAX_SCALE:
                        scale += 1
                        try:
                            screen, win_w, win_h = _resize_window(
                                width, height, scale, title, borderless
                            )
                            print(f"[LEDsim] Display: {_mode_label(width, height, scale)}")
                        except pygame.error as exc:
                            print(f"[LEDsim] Resize failed: {exc}")

                # Zoom out (down to native)
                elif event.key in (pygame.K_MINUS, pygame.K_UNDERSCORE, pygame.K_KP_MINUS):
                    if scale > MIN_SCALE:
                        scale -= 1
                        try:
                            screen, win_w, win_h = _resize_window(
                                width, height, scale, title, borderless
                            )
                            print(f"[LEDsim] Display: {_mode_label(width, height, scale)}")
                        except pygame.error as exc:
                            print(f"[LEDsim] Resize failed: {exc}")

            if stop_event.is_set():
                break

            counter, rgb = shared.read_frame()
            if counter != last_counter and len(rgb) >= width * height * 3:
                last_counter = counter
                try:
                    frame = pygame.image.frombytes(bytes(rgb), (width, height), "RGB")
                    panel.blit(frame, (0, 0))
                except Exception:
                    try:
                        frame = pygame.image.frombuffer(rgb, (width, height), "RGB")
                        panel.blit(frame, (0, 0))
                    except Exception:
                        i = 0
                        for y in range(height):
                            for x in range(width):
                                panel.set_at((x, y), (rgb[i], rgb[i + 1], rgb[i + 2]))
                                i += 3

            # Native: blit 1:1. Scaled: nearest-neighbor integer upscale.
            if scale <= 1:
                screen.blit(panel, (0, 0))
            else:
                scaled = pygame.transform.scale(panel, (win_w, win_h))
                screen.blit(scaled, (0, 0))
            pygame.display.flip()
            clock.tick(fps)
    finally:
        try:
            pygame.display.quit()
            pygame.quit()
        except Exception:
            pass
        print("[LEDsim] Viewer closed")
        stop_event.set()
