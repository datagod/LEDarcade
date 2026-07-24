#!/usr/bin/env python3
# LEDsim.py — Run LEDcommander on Windows with a desktop panel window
"""
===============================================================================
LEDsim — Software LED matrix simulator for LEDarcade / LEDcommander
===============================================================================

Starts:
  1. A pygame viewer window (native 64x32 or integer-scaled)
  2. LEDcommander dispatcher (same command queue as on the Pi)
  3. Flask control panel at http://127.0.0.1:5055

Display children write pixels into a shared memory framebuffer; the viewer
is the only process that owns a window (stable across mode switches).

Usage:
  python LEDsim.py                 # scaled (default x15 → 960x480)
  python LEDsim.py --native        # true panel size 64x32
  python LEDsim.py --scale 12      # custom integer scale
  python LEDsim.py --port 5055

In the viewer window:
  N = next program,  T = LEDtv,  1 = native 1:1,  S = default scale,  +/- = zoom,  Esc = quit

Environment:
  LEDARCADE_DISPLAY=sim          (set automatically)
  LEDARCADE_SIM_SCALE=15         pixel scale (1 = native; default 15)
  LEDARCADE_STREAM_MODE=0        full brightness (set automatically)
"""

from __future__ import annotations

import argparse
import atexit
import os
import signal
import sys
import time
import traceback

# ---------------------------------------------------------------------------
# Must set sim mode BEFORE any LEDarcade / LEDcommander import
# ---------------------------------------------------------------------------
REPO_DIR = os.path.dirname(os.path.abspath(__file__))
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)

os.environ["LEDARCADE_DISPLAY"] = "sim"
os.environ["LEDARCADE_STREAM_MODE"] = "0"
# Boot git/panel update check is Pi-oriented; skip on desktop by default
os.environ.setdefault("LEDARCADE_SKIP_BOOT_UPDATE", "1")
os.environ.setdefault("PYTHONUNBUFFERED", "1")

from multiprocessing import Event, Process, Queue, freeze_support

DEFAULT_WIDTH = 64
DEFAULT_HEIGHT = 32
DEFAULT_SCALE = 15  # comfortable desktop zoom; use --native for 1:1
DEFAULT_PORT = 5055


def _parse_args():
    p = argparse.ArgumentParser(
        description="LEDsim — Windows LED panel simulator for LEDcommander",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "display size examples:\n"
            "  python LEDsim.py --native          window is 64x32 (true panel pixels)\n"
            "  python LEDsim.py                   window is 960x480 (64x32 x15)\n"
            "  python LEDsim.py --scale 10        window is 640x320\n"
            "  python LEDsim.py --scale 1         same as --native\n"
            "  python LEDsim.py --bordered        normal title-bar window\n"
            "\n"
            "while focused: N=next  T=LEDtv  1=native  S=scaled  +/-=zoom  F=frame  Esc=quit\n"
            "borderless: left-drag moves the window"
        ),
    )
    p.add_argument("--width", type=int, default=DEFAULT_WIDTH, help="Panel width in pixels (default 64)")
    p.add_argument("--height", type=int, default=DEFAULT_HEIGHT, help="Panel height in pixels (default 32)")
    p.add_argument(
        "--native",
        action="store_true",
        help="Show the panel at native resolution (1:1 pixels, e.g. 64x32 window)",
    )
    p.add_argument(
        "--scale",
        type=int,
        default=None,
        metavar="N",
        help=(
            f"Integer window scale factor (1=native, default {DEFAULT_SCALE}). "
            "Ignored if --native is set."
        ),
    )
    frame = p.add_mutually_exclusive_group()
    frame.add_argument(
        "--borderless",
        action="store_true",
        default=None,
        help="No title bar / window frame (default)",
    )
    frame.add_argument(
        "--bordered",
        action="store_true",
        help="Normal window with title bar and system icon",
    )
    p.add_argument("--port", type=int, default=DEFAULT_PORT, help="Web control panel port")
    p.add_argument(
        "--no-web",
        action="store_true",
        help="Do not start the Flask control panel",
    )
    p.add_argument(
        "--no-commander",
        action="store_true",
        help="Only open the viewer (debug)",
    )
    return p.parse_args()


def _resolve_borderless(args) -> bool:
    """Default borderless; --bordered forces frame; env LEDARCADE_SIM_BORDERLESS overrides default."""
    if getattr(args, "bordered", False):
        return False
    if getattr(args, "borderless", None):
        return True
    env = os.environ.get("LEDARCADE_SIM_BORDERLESS")
    if env is not None and str(env).strip() != "":
        return str(env).strip().lower() in ("1", "true", "yes", "on")
    return True  # default: borderless (no pygame logo chrome)


def _resolve_scale(args) -> int:
    """Native wins; else --scale; else env; else default scaled zoom."""
    if getattr(args, "native", False):
        return 1
    if args.scale is not None:
        return max(1, int(args.scale))
    env = os.environ.get("LEDARCADE_SIM_SCALE")
    if env is not None and str(env).strip() != "":
        try:
            return max(1, int(env))
        except ValueError:
            pass
    return DEFAULT_SCALE


def _run_commander(command_queue):
    # Ensure children see sim mode (spawn does not inherit all parent state on all platforms)
    os.environ["LEDARCADE_DISPLAY"] = "sim"
    os.environ["LEDARCADE_STREAM_MODE"] = "0"
    os.environ.setdefault("LEDARCADE_SKIP_BOOT_UPDATE", "1")
    import LEDcommander
    # Standalone brightness
    LEDcommander.STREAM_MODE = False
    LEDcommander.STREAM_GAME_BRIGHTNESS = LEDcommander.STREAM_MAX_BRIGHTNESS
    LEDcommander.STREAM_CLOCK_BRIGHTNESS = LEDcommander.STREAM_MAX_BRIGHTNESS
    LEDcommander.Run(command_queue)


def _run_web(command_queue, port):
    os.environ["LEDARCADE_DISPLAY"] = "sim"
    import LEDcommander
    LEDcommander.serve_web_control(command_queue, port=port)


def main():
    freeze_support()
    args = _parse_args()

    width = max(8, args.width)
    height = max(8, args.height)
    scale = _resolve_scale(args)
    borderless = _resolve_borderless(args)

    os.environ["LEDARCADE_SIM_SCALE"] = str(scale)
    os.environ["LEDARCADE_SIM_DEFAULT_SCALE"] = str(DEFAULT_SCALE)
    os.environ["LEDARCADE_SIM_WIDTH"] = str(width)
    os.environ["LEDARCADE_SIM_HEIGHT"] = str(height)
    os.environ["LEDARCADE_SIM_BORDERLESS"] = "1" if borderless else "0"

    # Prefer spawn on all platforms for consistency with Windows
    try:
        import multiprocessing as mp
        mp.set_start_method("spawn", force=True)
    except RuntimeError:
        pass  # already set

    from ledsim import shared
    from ledsim.viewer import run_viewer

    shm = None
    stop_event = Event()
    processes = []

    def cleanup():
        stop_event.set()
        for proc in processes:
            if proc is not None and proc.is_alive():
                proc.terminate()
                proc.join(timeout=2)
                if proc.is_alive():
                    try:
                        proc.kill()
                    except Exception:
                        pass
        if shm is not None:
            try:
                shm.close()
                shm.unlink()
            except Exception:
                pass

    atexit.register(cleanup)

    def _handle_signal(signum, frame):
        print(f"\n[LEDsim] Signal {signum} — shutting down")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, _handle_signal)
        except Exception:
            pass

    mode = "native 1:1" if scale <= 1 else f"scaled x{scale}"
    frame = "borderless" if borderless else "windowed"
    print("")
    print("=" * 60)
    print("  LEDsim — LEDarcade software panel")
    print("=" * 60)
    print(f"  Panel:  {width}x{height}  mode={mode}  frame={frame}")
    print(f"  Window: {width * scale}x{height * scale}")
    print(f"  Web:    http://127.0.0.1:{args.port}/" + (" (disabled)" if args.no_web else ""))
    print("  Keys:   N=next  T=LEDtv  1=native  S=scaled  +/-=zoom  F=frame  Esc=quit")
    print("  Mouse:  left-click and drag moves the window")
    print("=" * 60)
    print("")

    try:
        shm, shm_name, width, height = shared.create_shared_buffer(width, height)
        print(f"[LEDsim] Shared frame buffer: {shm_name}")
    except Exception as exc:
        print(f"[LEDsim] Failed to create shared buffer: {exc}")
        traceback.print_exc()
        return 1

    command_queue = None
    if not args.no_commander:
        command_queue = Queue()
        commander = Process(
            target=_run_commander,
            args=(command_queue,),
            name="LEDcommander",
        )
        commander.start()
        processes.append(commander)
        print("[LEDsim] LEDcommander started")

        if not args.no_web:
            web = Process(
                target=_run_web,
                args=(command_queue, args.port),
                name="LEDweb",
            )
            web.start()
            processes.append(web)
            print(f"[LEDsim] Control panel: http://127.0.0.1:{args.port}/")

    # Viewer runs in the MAIN process (most reliable on Windows with pygame/SDL)
    try:
        run_viewer(
            stop_event,
            width=width,
            height=height,
            scale=scale,
            title="LEDsim",
            default_scaled=DEFAULT_SCALE,
            command_queue=command_queue,
            borderless=borderless,
        )
    except KeyboardInterrupt:
        print("\n[LEDsim] Keyboard interrupt")
        stop_event.set()
    except Exception as exc:
        print(f"[LEDsim] Viewer error: {exc}")
        traceback.print_exc()
        stop_event.set()

    cleanup()
    print("[LEDsim] Goodbye.")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
