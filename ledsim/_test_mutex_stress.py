"""Stress concurrent frame file read/write. Run:
  python -m ledsim._test_mutex_stress
"""
from __future__ import annotations

import os
import sys
import time
from multiprocessing import Process, set_start_method

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def hammer(n: int, frames: int = 120) -> None:
    os.environ["LEDARCADE_DISPLAY"] = "sim"
    from ledsim import shared

    for i in range(frames):
        rgb = bytes([(i + n) & 255, 128, 64]) * (64 * 32)
        shared.publish_frame(rgb)
        if i % 15 == 0:
            shared.clear_shared()
        time.sleep(0.001)
    print(f"worker {n} done", flush=True)


def main() -> int:
    try:
        set_start_method("spawn", force=True)
    except RuntimeError:
        pass

    from ledsim import shared

    handle, name, w, h = shared.create_shared_buffer(64, 32)
    print("frame", name)

    procs = [Process(target=hammer, args=(i,)) for i in range(4)]
    for p in procs:
        p.start()

    oks = 0
    errors = 0
    for _ in range(300):
        try:
            c, data = shared.read_frame()
            if c >= 0 and len(data) == 64 * 32 * 3:
                oks += 1
            time.sleep(0.002)
        except Exception as exc:
            errors += 1
            print("read err", exc)

    for p in procs:
        p.join(60)
        print("exit", p.pid, p.exitcode)
        if p.exitcode not in (0, None):
            errors += 1

    print("oks", oks, "errors", errors)
    try:
        handle.close()
        handle.unlink()
    except Exception:
        pass

    if errors or any(p.exitcode != 0 for p in procs):
        print("STRESS FAIL")
        return 1
    print("STRESS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
