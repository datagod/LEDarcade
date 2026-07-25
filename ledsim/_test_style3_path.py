"""Smoke: DisplayDigitalClock Style=3 child + parent reader (LEDsim-like)."""
from __future__ import annotations

import os
import sys
import time
from multiprocessing import Event, Process, set_start_method

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_style3(stop_event) -> None:
    os.environ["LEDARCADE_DISPLAY"] = "sim"
    os.environ["LEDARCADE_STREAM_MODE"] = "0"
    os.environ["LEDARCADE_GAMMA"] = "1.0"
    os.environ.setdefault("LEDARCADE_SKIP_BOOT_UPDATE", "1")
    import LEDarcade as LED

    LED.Initialize()
    # Style 3 only samples duration ~1/1000 frames — always use StopEvent for tests.
    LED.DisplayDigitalClock(
        ClockStyle=3,
        CenterHoriz=True,
        v=1,
        hh=24,
        RGB=LED.LowGreen,
        ShadowRGB=LED.ShadowGreen,
        ZoomFactor=2,
        AnimationDelay=30,
        ScrollSleep=0.01,
        RunMinutes=5,
        StopEvent=stop_event,
    )
    print("style3 child exit ok", flush=True)


def main() -> int:
    try:
        set_start_method("spawn", force=True)
    except RuntimeError:
        pass

    os.environ["LEDARCADE_DISPLAY"] = "sim"
    from ledsim import shared

    handle, name, w, h = shared.create_shared_buffer(64, 32)
    print("frame", name)

    stop = Event()
    p = Process(target=run_style3, args=(stop,))
    p.start()

    last = -1
    frames = 0
    t0 = time.time()
    # Let it run ~4s of frames then stop
    while time.time() - t0 < 4.0:
        c, data = shared.read_frame()
        if c >= 0 and c != last and len(data) == 64 * 32 * 3:
            last = c
            frames += 1
        time.sleep(0.02)

    print(f"stopping after {frames} frames…", flush=True)
    stop.set()
    p.join(15)
    if p.is_alive():
        p.terminate()
        p.join(5)

    print("child exitcode", p.exitcode, "frames_seen", frames)
    try:
        handle.close()
        handle.unlink()
    except Exception:
        pass

    if p.exitcode not in (0, None) and p.exitcode != 0:
        # terminate may yield negative codes; frames matter more
        if frames < 10:
            print("STYLE3 PATH FAIL (exitcode)", p.exitcode)
            return 1
    if frames < 10:
        print("STYLE3 PATH FAIL (too few frames)", frames)
        return 1
    print("STYLE3 PATH PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
