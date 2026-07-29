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
  python LEDsim.py                 # scaled (default x3 → 192x96)
  python LEDsim.py --native        # true panel size 64x32
  python LEDsim.py --scale 12      # custom integer scale
  python LEDsim.py --port 5055

In the viewer window:
  N = next,  T = LEDtv,  1 = Pinball,  2 = SpaceExplorer,
  R = restart,  0 = native,  S = scale,  +/- = zoom,  F = frame,  Esc = quit

Environment:
  LEDARCADE_DISPLAY=sim          (set automatically)
  LEDARCADE_SIM_SCALE=3          pixel scale (1 = native; default 3)
  LEDARCADE_STREAM_MODE=0        full brightness (set automatically)
"""

from __future__ import annotations

import argparse
import atexit
import os
import signal
import subprocess
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
# Full color/output on desktop (gamma 100% = multiplier 1.0; matrix brightness 100)
os.environ["LEDARCADE_GAMMA"] = "1.0"
# Boot git/panel update check is Pi-oriented; skip on desktop by default
os.environ.setdefault("LEDARCADE_SKIP_BOOT_UPDATE", "1")
os.environ.setdefault("PYTHONUNBUFFERED", "1")

from multiprocessing import Event, Process, Queue, freeze_support

# Fault log lives under the repo (not %TEMP%)
FAULT_LOG_PATH = os.path.join(REPO_DIR, "localdata", "ledsim_fault.log")
_LEDSIM_FAULT_FILE = None


def _setup_faulthandler() -> None:
    """
    Enable faulthandler in the *main* LEDsim process only.

    Must NOT run at module import time: Windows spawn children re-import this
    file and would truncate localdata/ledsim_fault.log with open(..., "w"),
    wiping breadcrumbs from the real viewer process.
    """
    global _LEDSIM_FAULT_FILE
    # Children set this so they never steal/truncate the main log
    if os.environ.get("LEDARCADE_SIM_CHILD") == "1":
        return
    try:
        import faulthandler

        os.makedirs(os.path.dirname(FAULT_LOG_PATH), exist_ok=True)
        # line-buffered so stacks/breadcrumbs hit disk before an AV
        _fh_file = open(
            FAULT_LOG_PATH, "w", encoding="utf-8", errors="replace", buffering=1
        )
        _fh_file.write(f"LEDsim faulthandler started pid={os.getpid()}\n")
        _fh_file.write(f"python={sys.executable}\n")
        _fh_file.write(f"cwd={os.getcwd()}\n")
        _fh_file.write(
            "Note: pure native SDL AVs may leave no Python stack — "
            "look for breadcrumb lines (last action before death).\n"
        )
        _fh_file.flush()
        faulthandler.enable(file=_fh_file, all_threads=True)
        _LEDSIM_FAULT_FILE = _fh_file
        print(f"[LEDsim] faulthandler → {FAULT_LOG_PATH}")
    except Exception as exc:
        print(f"[LEDsim] faulthandler setup failed: {exc}")

DEFAULT_WIDTH = 64
DEFAULT_HEIGHT = 32
DEFAULT_SCALE = 3  # start at x3 zoom; use --scale / +/- to adjust
DEFAULT_PORT = 5055
# Exit code when the viewer presses R. run_ledsim.bat loops on this so a full
# re-launch happens (os.execv after multiprocessing is unreliable on Windows,
# and post-exit orphan cleanup would kill a Popen'd child).
RESTART_EXIT_CODE = 42


def _parse_args():
    p = argparse.ArgumentParser(
        description="LEDsim — Windows LED panel simulator for LEDcommander",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "display size examples:\n"
            "  python LEDsim.py --native          window is 64x32 (true panel pixels)\n"
            "  python LEDsim.py                   window is 192x96 (64x32 x3)\n"
            "  python LEDsim.py --scale 10        window is 640x320\n"
            "  python LEDsim.py --scale 1         same as --native\n"
            "  python LEDsim.py --bordered        normal title-bar window\n"
            "\n"
            "while focused: N=next  T=LEDtv  1=Pinball  2=SpaceExplorer  "
            "R=restart  0=native  S=scaled  +/-=zoom  F=frame  Esc=quit\n"
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
        help="No title bar / window frame (unstable on some Windows/SDL builds)",
    )
    frame.add_argument(
        "--bordered",
        action="store_true",
        help="Normal window with title bar (default on Windows)",
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
    """
    Window chrome: --bordered / --borderless, else env, else borderless.

    Default is no frame (panel look). Use --bordered for a title bar.
    """
    if getattr(args, "bordered", False):
        return False
    if getattr(args, "borderless", None):
        return True
    env = os.environ.get("LEDARCADE_SIM_BORDERLESS")
    if env is not None and str(env).strip() != "":
        return str(env).strip().lower() in ("1", "true", "yes", "on")
    return True  # borderless panel by default


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
    # Mark spawn child so module re-import never steals the main fault log
    os.environ["LEDARCADE_SIM_CHILD"] = "1"
    # Ensure children see sim mode (spawn does not inherit all parent state on all platforms)
    os.environ["LEDARCADE_DISPLAY"] = "sim"
    os.environ["LEDARCADE_STREAM_MODE"] = "0"
    os.environ["LEDARCADE_GAMMA"] = "1.0"
    os.environ.setdefault("LEDARCADE_SKIP_BOOT_UPDATE", "1")
    import LEDarcade as LED
    # Gamma 100% (1.0) before any game loads palette-dependent code
    LED.Gamma = 1.0
    import LEDcommander
    # Standalone brightness — always full blast on LEDsim
    LEDcommander.STREAM_MODE = False
    LEDcommander.STREAM_MAX_BRIGHTNESS = 100
    LEDcommander.STREAM_GAME_BRIGHTNESS = 100
    LEDcommander.STREAM_CLOCK_BRIGHTNESS = 100
    LEDcommander.Run(command_queue)


def _run_web(command_queue, port):
    os.environ["LEDARCADE_SIM_CHILD"] = "1"
    os.environ["LEDARCADE_DISPLAY"] = "sim"
    import LEDcommander
    LEDcommander.serve_web_control(command_queue, port=port)


def main():
    freeze_support()
    # Main process only — before any Process() spawn
    os.environ.pop("LEDARCADE_SIM_CHILD", None)
    _setup_faulthandler()
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
    command_queue_holder = {"q": None}
    _cleanup_done = {"v": False}

    def _kill_tree(pid: int) -> None:
        """Kill a process and all descendants (Windows grandchildren included)."""
        if not pid:
            return
        try:
            if sys.platform == "win32":
                # /T = tree, /F = force — covers LEDcommander display children
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
            else:
                import os as _os
                try:
                    _os.kill(pid, signal.SIGTERM)
                except Exception:
                    pass
        except Exception:
            pass

    def cleanup():
        if _cleanup_done["v"]:
            return
        _cleanup_done["v"] = True
        print("[LEDsim] Shutting down child processes…")
        stop_event.set()

        # Ask commander to quit cleanly first (stops current display)
        q = command_queue_holder.get("q")
        if q is not None:
            try:
                q.put({"Action": "quit"})
            except Exception:
                pass
            try:
                q.put({"Action": "stop"})
            except Exception:
                pass

        # Brief chance for a graceful stop
        time.sleep(0.3)

        for proc in list(processes):
            if proc is None:
                continue
            try:
                pid = proc.pid
            except Exception:
                pid = None
            if pid:
                _kill_tree(pid)
            try:
                if proc.is_alive():
                    proc.terminate()
                proc.join(timeout=1.5)
            except Exception:
                pass
            try:
                if proc.is_alive():
                    proc.kill()
                    proc.join(timeout=1)
            except Exception:
                pass

        if shm is not None:
            try:
                shm.close()
            except Exception:
                pass
            try:
                shm.unlink()
            except Exception:
                pass
            try:
                from ledsim import shared as _shared
                _shared.close(unlink=True)
            except Exception:
                pass
        print("[LEDsim] Children stopped.")

    atexit.register(cleanup)

    def _handle_signal(signum, frame):
        print(f"\n[LEDsim] Signal {signum} (Ctrl+C) — shutting down")
        stop_event.set()
        # Do not call cleanup() here if still inside pygame — set flag and
        # let main path clean up; also kill trees immediately so logs stop.
        for proc in list(processes):
            try:
                if proc is not None and proc.pid:
                    _kill_tree(proc.pid)
            except Exception:
                pass
        # Raise KeyboardInterrupt so run_viewer / main unwind
        raise KeyboardInterrupt

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
    print(
        "  Keys:   N=next  T=LEDtv  1=Pinball  2=SpaceExplorer  "
        "R=restart  0=native  S=scaled  +/-=zoom  F=frame  Esc=quit"
    )
    print("  Mouse:  left-click and drag moves the window")
    print("=" * 60)
    print("")

    try:
        shm, shm_name, width, height = shared.create_shared_buffer(width, height)
        print(f"[LEDsim] Shared frame buffer (file): {shm_name}")
    except Exception as exc:
        print(f"[LEDsim] Failed to create shared buffer: {exc}")
        traceback.print_exc()
        return 1

    command_queue = None
    if not args.no_commander:
        command_queue = Queue()
        command_queue_holder["q"] = command_queue
        commander = Process(
            target=_run_commander,
            args=(command_queue,),
            name="LEDcommander",
            daemon=False,  # we kill the tree explicitly on exit
        )
        commander.start()
        processes.append(commander)
        print("[LEDsim] LEDcommander started")

        if not args.no_web:
            web = Process(
                target=_run_web,
                args=(command_queue, args.port),
                name="LEDweb",
                daemon=False,
            )
            web.start()
            processes.append(web)
            print(f"[LEDsim] Control panel: http://127.0.0.1:{args.port}/")

    # Viewer runs in the MAIN process (most reliable on Windows with pygame/SDL)
    exit_reason = "quit"
    try:
        exit_reason = run_viewer(
            stop_event,
            width=width,
            height=height,
            scale=scale,
            title="LEDsim",
            default_scaled=DEFAULT_SCALE,
            command_queue=command_queue,
            borderless=borderless,
        ) or "quit"
    except KeyboardInterrupt:
        print("\n[LEDsim] Keyboard interrupt — cleaning up")
        stop_event.set()
        exit_reason = "quit"
    except Exception as exc:
        print(f"[LEDsim] Viewer error: {exc}")
        traceback.print_exc()
        stop_event.set()
        exit_reason = "quit"

    cleanup()
    try:
        atexit.unregister(cleanup)
    except Exception:
        pass

    if exit_reason == "restart":
        print("[LEDsim] Restart requested (R) — full process reload")
        script = os.path.join(REPO_DIR, "LEDsim.py")
        # Preserve CLI flags (--scale, --port, …)
        cli_args = list(sys.argv[1:])
        argv = [sys.executable, "-u", script] + cli_args
        os.chdir(REPO_DIR)

        under_wrapper = os.environ.get("LEDARCADE_SIM_WRAPPER", "").strip() in (
            "1", "true", "yes", "on",
        )
        if under_wrapper:
            # run_ledsim.bat will re-invoke us when it sees RESTART_EXIT_CODE
            print(f"[LEDsim] Returning exit code {RESTART_EXIT_CODE} for wrapper restart")
            return RESTART_EXIT_CODE

        # Standalone (python LEDsim.py): spawn a fresh process, then exit
        print(f"[LEDsim] Spawning: {' '.join(argv)}")
        try:
            env = os.environ.copy()
            env["LEDARCADE_DISPLAY"] = "sim"
            env.pop("LEDARCADE_SIM_CHILD", None)
            subprocess.Popen(
                argv,
                cwd=REPO_DIR,
                env=env,
                close_fds=False,
            )
            print("[LEDsim] New LEDsim process started.")
            return 0
        except Exception as exc:
            print(f"[LEDsim] Spawn restart failed: {exc}")
            traceback.print_exc()
            # Last resort: execv (may fail after multiprocessing on Windows)
            try:
                os.execv(sys.executable, argv)
            except Exception as exc2:
                print(f"[LEDsim] execv restart failed: {exc2}")
                traceback.print_exc()
            return RESTART_EXIT_CODE

    print("[LEDsim] Goodbye.")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
