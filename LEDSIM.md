# LEDsim — Windows / desktop simulator for LEDcommander

Run the full **LEDcommander** stack on a PC. Instead of driving a Raspberry Pi LED matrix, frames appear in a desktop window — either **native 64×32** or **integer-scaled** (blocky LED look).

## How it works

| Piece | Role |
|-------|------|
| `LEDsim.py` | Launcher: shared frame buffer + processes |
| pygame **viewer** | Single window; native 1:1 or nearest-neighbor scale |
| **LEDcommander** | Same queue / mode dispatcher as on the Pi |
| Web panel `:5055` | Same CRT control UI (`LEDpanel.py`) |
| `ledsim/` | Software `rgbmatrix` API + shared memory |

Set `LEDARCADE_DISPLAY=sim` (done automatically by `LEDsim.py`). `LEDarcade` then imports `ledsim.rgbmatrix_compat` instead of the Pi-only `rpi-rgb-led-matrix` bindings.

## Requirements (Windows)

- Python 3.10+ recommended  
- Packages:

```bat
pip install pygame pillow numpy flask requests numba
```

- **Not** required: `rpi-rgb-led-matrix`, sudo, GPIO  
- Optional: `ffmpeg` on PATH for LEDtv local video  

## Run

```bat
python LEDsim.py
```

or double-click / run:

```bat
run_ledsim.bat
```

Then open **http://127.0.0.1:5055/** for the control panel.

### Display size

| Command | Window size | Notes |
|---------|-------------|--------|
| `python LEDsim.py` | **960×480** | Default scale ×15 |
| `python LEDsim.py --native` | **64×32** | True panel resolution (1:1) |
| `python LEDsim.py --scale 1` | **64×32** | Same as `--native` |
| `python LEDsim.py --scale 10` | **640×320** | Custom integer zoom |

### Other flags

```bat
python LEDsim.py --port 5055
python LEDsim.py --width 64 --height 32
python LEDsim.py --no-web
```

### Viewer hotkeys (window focused)

| Key | Action |
|-----|--------|
| **N** | **Next** program (stop current, advance LEDcommander playlist) |
| **T** | Launch **LEDtv** (channel-surf / local video) |
| **1** | Native 1:1 (64×32) |
| **S** | Default scaled size (×15) |
| **+** / **=** | Zoom in |
| **-** | Zoom out (down to native) |
| **F** | Toggle **borderless** / framed window |
| **Esc** | Quit |

**Borderless** is the default (no title bar, no pygame logo chrome). **Left-click and drag** anywhere on the panel to move the window (works borderless or framed). Use `python LEDsim.py --bordered` for a normal title bar.

You can also `POST /command` with `{"Action": "next"}` from the web panel API.

Closing the window also stops LEDsim.

## Environment variables

| Variable | Meaning |
|----------|---------|
| `LEDARCADE_DISPLAY=sim` | Use software matrix backend |
| `LEDARCADE_SIM_SCALE` | Pixel scale (`1` = native; default `15`) |
| `LEDARCADE_SIM_BORDERLESS` | `1` / `0` — borderless window (default `1`) |
| `LEDARCADE_SIM_WIDTH` / `HEIGHT` | Panel size (must match launcher) |
| `LEDARCADE_STREAM_MODE=0` | Full brightness (standalone) |
| `LEDARCADE_SKIP_BOOT_UPDATE=1` | Skip git boot update (set by LEDsim) |

## Pi / hardware unchanged

On the Raspberry Pi, leave `LEDARCADE_DISPLAY` unset (or `hardware`). `LEDarcade` still imports the real `rgbmatrix` package and drives the HAT as before.

## Smoke test (no window)

```bat
set LEDARCADE_DISPLAY=sim
python -c "import LEDarcade as LED; LED.Initialize(); print(LED.DISPLAY_BACKEND, LED.HatWidth, LED.HatHeight)"
```

Expected: `sim 64 32` (shared memory may be missing outside LEDsim; pixels still work in-process).

## Known limits

- Not a cycle-accurate PWM / brightness hardware emulator  
- Some games need `numba` / extra native wheels on Windows  
- Twitch entry (`twitch.py`) is not the primary path; it can use the same sim backend if `LEDARCADE_DISPLAY=sim` is set first  
- Boot update check in LEDcommander may touch git/network on start  

## Architecture sketch

```
Browser :5055  ──► CommandQueue ──► LEDcommander.Run
                                         │
                                         ▼
                              Display child Process
                              LED.Initialize() [sim]
                              TheMatrix / Canvas
                                         │
                                         ▼
                              shared memory RGB frame
                                         │
                                         ▼
                              LEDsim pygame viewer window
```
