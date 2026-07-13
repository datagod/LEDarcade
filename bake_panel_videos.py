#!/usr/bin/env python3
"""
Bake LEDtv source videos into panel-sized files under videos/panel/.

- Never overwrites originals in videos/
- Uses the same scale/letterbox/unsharp pipeline as live LEDtv playback
- Skip existing panel files unless --force

Usage:
  python3 bake_panel_videos.py
  python3 bake_panel_videos.py --force
  python3 bake_panel_videos.py path/to/one.mp4
"""
from __future__ import print_function

import argparse
import os
import sys

# Initialize LED config so HatWidth/Height match the panel before import uses them
import LEDarcade as LED

LED.LoadConfigData()

import LEDtv as TV


def main(argv=None):
    parser = argparse.ArgumentParser(description="Bake LEDtv videos to panel size")
    parser.add_argument(
        "paths",
        nargs="*",
        help="Optional source files (default: all videos/ top-level)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-bake even if videos/panel/<name> already exists",
    )
    args = parser.parse_args(argv)

    print(
        "[bake] Panel size {}x{}  fps={}  out={}".format(
            TV.WIDTH, TV.HEIGHT, TV.VIDEO_FPS, TV.PANEL_VIDEO_DIR,
        )
    )

    if args.paths:
        ok = skip = fail = 0
        for p in args.paths:
            if not os.path.isfile(p):
                print("[bake] missing:", p)
                fail += 1
                continue
            dest = TV.panel_bake_path(p)
            if os.path.isfile(dest) and not args.force:
                print("[bake] exists, skip:", dest)
                skip += 1
                continue
            if TV.bake_panel_video(p, dest_path=dest, force=args.force):
                ok += 1
            else:
                fail += 1
        print("[bake] done ok={} skipped={} failed={}".format(ok, skip, fail))
        return 0 if fail == 0 else 1

    ok, skip, fail = TV.bake_all_panel_videos(force=args.force)
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
