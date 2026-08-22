#!/usr/bin/env python3
"""Preview StickFigureWalking on the LED matrix (walk in place, then stroll)."""

from __future__ import annotations

import time

import LEDarcade as LED

LED.Initialize()


def main():
    sprite = LED.StickFigureWalking
    print(
        f"[preview] {sprite.name}  "
        f"{sprite.width}x{sprite.height}  frames={sprite.frames}  "
        f"framerate={sprite.framerate}  grid_len={len(sprite.grid)}"
    )

    LED.TheMatrix.Clear()
    LED.ClearBuffers()

    # Center-ish on the panel
    h = max(0, (LED.HatWidth - sprite.width) // 2)
    v = max(0, (LED.HatHeight - sprite.height) // 2 - 2)

    # 1) Walk in place
    print("[preview] walking in place…")
    for _ in range(48):
        LED.TheMatrix.Clear()
        sprite.DisplayAnimated(h, v)
        time.sleep(0.06)

    # 2) Stroll left → right across the panel
    print("[preview] strolling across…")
    sprite.currentframe = 1
    sprite.ticks = 0
    start = -sprite.width
    end = LED.HatWidth + 1
    for x in range(start, end):
        LED.TheMatrix.Clear()
        sprite.DisplayAnimated(x, v)
        time.sleep(0.05)

    # Hold last pose briefly
    time.sleep(0.4)
    LED.TheMatrix.Clear()
    print("[preview] done")


if __name__ == "__main__":
    main()
