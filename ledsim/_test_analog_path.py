"""Smoke: AnalogClock-style child + parent reader (like LEDsim viewer)."""
from __future__ import annotations

import os
import sys
import time
from multiprocessing import Process, set_start_method

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_clock() -> None:
    os.environ["LEDARCADE_DISPLAY"] = "sim"
    os.environ["LEDARCADE_STREAM_MODE"] = "0"
    os.environ["LEDARCADE_GAMMA"] = "1.0"
    os.environ.setdefault("LEDARCADE_SKIP_BOOT_UPDATE", "1")
    import LEDarcade as LED

    LED.Initialize()
    import AnalogClock as AC

    # ~3 seconds
    AC.RunClock(Duration=0.05, StopEvent=None)
    print("clock child exit ok", flush=True)


def main() -> int:
    try:
        set_start_method("spawn", force=True)
    except RuntimeError:
        pass

    os.environ["LEDARCADE_DISPLAY"] = "sim"
    from ledsim import shared

    handle, name, w, h = shared.create_shared_buffer(64, 32)
    print("frame", name)

    p = Process(target=run_clock)
    p.start()

    last = -1
    frames = 0
    t0 = time.time()
    while time.time() - t0 < 10:
        c, data = shared.read_frame()
        if c >= 0 and c != last and len(data) == 64 * 32 * 3:
            last = c
            frames += 1
        time.sleep(0.05)
        if not p.is_alive() and time.time() - t0 > 1.5:
            break

    p.join(15)
    print("child exitcode", p.exitcode, "frames_seen", frames)
    try:
        handle.close()
        handle.unlink()
    except Exception:
        pass

    if p.exitcode != 0:
        print("ANALOG PATH FAIL (exitcode)")
        return 1
    if frames < 1:
        print("ANALOG PATH FAIL (no frames)")
        return 1
    print("ANALOG PATH PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
