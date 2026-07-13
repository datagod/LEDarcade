# LEDtv video library

How to download clips, convert them for the LED matrix, and run them with **LEDtv**.

The matrix is **64×32**. Full-resolution sources are too heavy to scale live every frame, so clips are **pre-baked** once into panel-sized files. Playback uses those baked files (exact screen output, 30 fps).

---

## Directory layout

```text
LEDarcade/
  videos/                 # optional: temporary full-res downloads
    README.md             # this file
    panel/                # ★ what LEDtv actually plays
      yt_xxxxx.mp4        # 64×32 @ 30 fps, letterboxed
      …
  bake_panel_videos.py    # conversion tool
  LEDtv.py                # player / channel surf
```

| Path | Role |
|------|------|
| `videos/*.mp4` | Optional **source** downloads (any resolution). Safe to delete after baking. |
| `videos/panel/*.mp4` | **Panel library** — required for channel surf. Same basename as the source. |

LEDtv prefers `videos/panel/` when it has files. Originals are **not** required at runtime.

---

## Requirements

On the Pi (or any machine used to prepare media):

```bash
# ffmpeg (decode / scale / encode)
sudo apt-get install -y ffmpeg

# yt-dlp (YouTube download) — keep it updated
sudo pip3 install -U yt-dlp
# or:  sudo curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp
#      sudo chmod a+rx /usr/local/bin/yt-dlp
```

Python needs the same LEDarcade / matrix stack as usual (`LEDarcade`, Pillow, etc.) so `bake_panel_videos.py` can read panel width/height from config.

---

## Target format (panel bake)

Each file under `videos/panel/` should be:

| Property | Value |
|----------|--------|
| Resolution | **64×32** (matches the LED matrix) |
| Aspect | **Letterbox** (black bars; never stretched) |
| Frame rate | **30 fps** (`VIDEO_FPS` in `LEDtv.py`) |
| Video codec | H.264 (`libx264`), yuv420p, no audio |
| Filter pipeline | Lanczos scale → pad to 64×32 → light unsharp → fps=30 |

This matches the live LEDtv scale filter, so a bake is a permanent snapshot of “what would have been sent to the screen.”

---

## Step 1 — Download a source clip

Use **yt-dlp**. Prefer a modest progressive MP4 (≤360p is plenty; the panel is tiny).

```bash
cd /home/pi/LEDarcade/videos

# Example: one YouTube URL → yt_<VIDEO_ID>.mp4
VIDEO_ID="csZ34kBpmcY"
URL="https://www.youtube.com/watch?v=${VIDEO_ID}"

yt-dlp -f 'bv*[height<=360]+ba/b[height<=360]/b' \
  --merge-output-format mp4 \
  --no-playlist \
  -o "yt_${VIDEO_ID}.mp4" \
  "$URL"
```

**Naming convention used in this project**

- `yt_<YouTubeID>.mp4` — whole clip  
- `yt_<YouTubeID>_60s.mp4` or `yt_<YouTubeID>_60s_partNN.mp4` — short segments  

Any basename works; the panel file will reuse the same name (with `.mp4`).

You can also copy any local `.mp4` / `.webm` / `.mkv` into `videos/`.

---

## Step 2 — Bake to panel size

From the LEDarcade root:

```bash
cd /home/pi/LEDarcade

# One file
python3 bake_panel_videos.py videos/yt_csZ34kBpmcY.mp4

# Every top-level file in videos/ (skips ones that already have a panel bake)
python3 bake_panel_videos.py

# Re-encode everything even if panel/ already has the name
python3 bake_panel_videos.py --force
```

Equivalent via LEDtv:

```bash
python3 LEDtv.py --bake
python3 LEDtv.py --bake --force
```

**What this does**

1. Reads the source under `videos/` (never writes over it).  
2. Runs ffmpeg with the panel filter (64×32, letterbox, 30 fps, CRF 16).  
3. Writes `videos/panel/<same_basename>.mp4`.  
4. Skips existing panel files unless `--force`.

Example:

```text
videos/yt_csZ34kBpmcY.mp4          →  source (e.g. 640×360)
videos/panel/yt_csZ34kBpmcY.mp4    →  baked (64×32 @ 30 fps)
```

---

## Step 3 — (Optional) Remove originals

After a successful bake, sources are only needed if you want to re-bake later with different settings.

```bash
cd /home/pi/LEDarcade
# Delete full-res sources only — keep panel/
rm -f videos/*.mp4
```

Do **not** delete `videos/panel/`. That is the runtime library.

---

## Step 4 — Run LEDtv

Stop other LED apps first (matrix is exclusive):

```bash
cd /home/pi/LEDarcade
sudo bash ./stop.sh

# Standalone channel surf (uses videos/panel/, no time limit by default)
sudo python3 LEDtv.py
```

**Other launch paths**

| Method | Action |
|--------|--------|
| Web panel | **Launch LED TV** (`launch_ledtv`) |
| Twitch chat | `?tv` (aliases: `?ledtv`) |
| LEDcommander | `{"Action": "launch_ledtv", "duration": 5}` |

Play one local file (panel bake preferred if present):

```bash
sudo python3 LEDtv.py --youtube /home/pi/LEDarcade/videos/panel/yt_csZ34kBpmcY.mp4 --duration 1
```

---

## How playback chooses files

1. Channel surf calls `list_videos()`.  
2. If `videos/panel/` has clips → those paths are the playlist.  
3. Else → fall back to top-level `videos/*`.  
4. On play, if a panel bake exists for a path’s basename, LEDtv uses it and **skips a second scale** (`panel_bake=yes` in the log).

Log line example:

```text
[LEDtv] VIDEO  CH2  name=yt_csZ34kBpmcY.mp4  …  panel_bake=yes
```

---

## End-to-end recipe (copy/paste)

```bash
cd /home/pi/LEDarcade

VIDEO_ID="csZ34kBpmcY"
URL="https://www.youtube.com/watch?v=${VIDEO_ID}"

# 1. Download source
yt-dlp -f 'bv*[height<=360]+ba/b[height<=360]/b' \
  --merge-output-format mp4 --no-playlist \
  -o "videos/yt_${VIDEO_ID}.mp4" \
  "$URL"

# 2. Bake to 64×32 @ 30 fps
python3 bake_panel_videos.py "videos/yt_${VIDEO_ID}.mp4"

# 3. Optional: drop the heavy source
rm -f "videos/yt_${VIDEO_ID}.mp4"

# 4. Run TV
sudo bash ./stop.sh
sudo python3 LEDtv.py
```

---

## Tuning

| Setting | File | Notes |
|---------|------|--------|
| `VIDEO_FPS` | `LEDtv.py` | Default **30**. Re-bake with `--force` after changing. |
| Panel size | `ClockConfig` / `HatWidth`×`HatHeight` | Bake uses live config dimensions. |
| Channel dwell | `CHANNEL_DWELL_*` in `LEDtv.py` | Seconds per channel after warmup. |

If you change `VIDEO_FPS` or panel size, re-run:

```bash
python3 bake_panel_videos.py --force
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| No video channels | Ensure `videos/panel/` has `.mp4` files. |
| `panel_bake=no` in log | File is not under `panel/` and is not 64×32 — bake it. |
| yt-dlp / JS runtime warnings | Update yt-dlp; see [yt-dlp EJS wiki](https://github.com/yt-dlp/yt-dlp/wiki/EJS). |
| Matrix busy / black screen | `sudo bash ./stop.sh` then start LEDtv as root. |
| Bake refuses overwrite | Sources are never overwritten; only `videos/panel/` is written. Use `--force` to replace a bake. |

---

## Git note

Panel clips are small (~few hundred KB each) and are suitable to commit if you want a ready-to-run library. Full-res sources are large; prefer not storing them once baked.
