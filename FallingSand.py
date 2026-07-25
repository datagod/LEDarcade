


"""
===============================================================================
                                 FALLING SAND
                          PARTICLE SIMULATION ENGINE
===============================================================================

Author: Datagod and ChatGPT (great partners!)
Project: LEDarcade
Platform: Raspberry Pi + RGB LED Matrix (32x32, 64x32, etc.)
Dependencies: Numba, NumPy, LEDarcade, RGBMatrix

-------------------------------------------------------------------------------
DESCRIPTION
-------------------------------------------------------------------------------

This Python script simulates a particle system that displays physics-based 
interactions such as gravity, damping, and collision-based particle explosions 
on an LED matrix. It utilizes a fixed-size particle array to manage state and 
updates all particles in-place for performance. The output is rendered onto 
the LED matrix using the LEDarcade API.

Key features:
- Particles are spawned at a configurable rate and obey gravity.
- On collision with each other, particles can "absorb" and eventually "explode"
  into multiple new particles, simulating a chain-reaction effect.
- Particles bounce off the top and bottom edges and are allowed to wrap or 
  escape laterally.
- A trail-fading effect provides persistence and smoother visuals.

-------------------------------------------------------------------------------
NUMBA JIT COMPILATION
-------------------------------------------------------------------------------

Numba's `@njit` decorator is used to accelerate functions via Just-In-Time
(JIT) compilation. JIT translates a subset of Python and NumPy code into 
optimized machine code at runtime, significantly improving the performance
of tight loops and math-heavy logic.

Why use JIT here:
- The particle update logic runs every frame and is performance-critical.
- JIT provides near-C speeds while maintaining Pythonic syntax.
- Numba supports `prange`, `List`, and common math operations, making it 
  ideal for simulations like this.

On LEDsim / Windows the *first* call can take tens of seconds (looks like a hang).
We print a clear message during that warm-up.

-------------------------------------------------------------------------------
PARTICLE STRUCTURE
-------------------------------------------------------------------------------

Each particle is represented as a row in a NumPy array with 14 float values:
[x, y, vx, vy, r, g, b, lifetime, absorb_count, cooldown, exploded_flag, 
 explosion_r, explosion_g, explosion_b]

-------------------------------------------------------------------------------
RENDERING
-------------------------------------------------------------------------------

Draw into the frame canvas, then SwapOnVSync once per frame. Do not mix
TheMatrix.SetPixel with SwapOnVSync(Canvas) — on LEDsim that presents an empty
canvas and looks like a black hang.
===============================================================================
"""

# FALLING SAND - BLAZING FAST VERSION

import LEDarcade as LED

import time
import random
import numpy as np
from numba import njit, types
from numba.typed import List

# Configuration
PARTICLE_COLOR = (150, 150, 0)
SPAWN_RATE = 60
MAX_PARTICLES = 50
MAX_LIFETIME = 1000
# Panel size is fixed after LED.Initialize() (commander does that before import).
WIDTH = getattr(LED, "HatWidth", 64) or 64
HEIGHT = getattr(LED, "HatHeight", 32) or 32
SIM_WIDTH = WIDTH
SIM_HEIGHT = HEIGHT * 2
GRAVITY = 0.075
DAMPING = 0.99
TRAIL_FADE = 15
COEFF_RESTITUTION = 0.6
ABSORB_LIMIT = 5
PARTICLES_PER_EXPLOSION = 3
COOLDOWN_FRAMES = 10

# Particle data
particles = np.zeros((MAX_PARTICLES, 14), dtype=np.float32)
active_mask = np.zeros(MAX_PARTICLES, dtype=np.bool_)
next_spawn_index = 0
_numba_warmed = False


@njit
def random_explosion_color():
    return (
        float(random.randint(100, 255)),
        float(random.randint(0, 200)),
        float(random.randint(0, 200)),
    )


@njit
def spawn_particle_fast(particles, active_mask, i):
    x = float(random.uniform((SIM_WIDTH - WIDTH) // 2, (SIM_WIDTH + WIDTH) // 2))
    y = float(SIM_HEIGHT - HEIGHT - 1)
    vx = float(random.uniform(-1.0, 1.0))
    vy = 0.0
    r, g, b = PARTICLE_COLOR
    particles[i, 0:14] = [x, y, vx, vy, r, g, b, MAX_LIFETIME, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    active_mask[i] = True


@njit
def spawn_explosion_particle(particles, active_mask, i, x, y):
    angle = random.uniform(0, 2 * np.pi)
    speed = random.uniform(1.0, 3.0)
    vx = speed * np.cos(angle)
    vy = speed * np.sin(angle)
    r = float(random.randint(100, 255))
    g = float(random.randint(0, 200))
    b = float(random.randint(0, 200))
    particles[i, 0:14] = [x, y, vx, vy, r, g, b, MAX_LIFETIME, 0.0, COOLDOWN_FRAMES, 1.0, r, g, b]
    active_mask[i] = True


@njit
def update_particles(particles, active_mask, exploded_xs, exploded_ys):
    for i in range(particles.shape[0]):
        if not active_mask[i]:
            continue

        x, y, vx, vy, r, g, b, lifetime, absorb_count, cooldown, exploded_flag, explosion_r, explosion_g, explosion_b = particles[i]

        lifetime -= 1
        if lifetime <= 0:
            active_mask[i] = False
            continue

        if cooldown > 0:
            cooldown -= 1

        vy += GRAVITY
        vx *= DAMPING

        x_new = x + vx
        y_new = y + vy

        if y_new >= SIM_HEIGHT:
            vy = -abs(vy) * COEFF_RESTITUTION
            y_new = SIM_HEIGHT - 1
        elif y_new < 0:
            vy = abs(vy) * COEFF_RESTITUTION
            y_new = 0

        exploded = False
        if cooldown <= 0:
            for j in range(particles.shape[0]):
                if i == j or not active_mask[j]:
                    continue
                dx = x_new - particles[j, 0]
                dy = y_new - particles[j, 1]
                if dx * dx + dy * dy < 1.0:
                    absorb_count += 1
                    if absorb_count >= ABSORB_LIMIT:
                        active_mask[i] = False
                        exploded_xs.append(np.float32(x_new))
                        exploded_ys.append(np.float32(y_new))
                        exploded = True
                        break
                    else:
                        vx = -vx * COEFF_RESTITUTION
                        vy = -vy * COEFF_RESTITUTION
                        if exploded_flag == 0:
                            explosion_r = float(random.randint(100, 255))
                            explosion_g = float(random.randint(0, 200))
                            explosion_b = float(random.randint(0, 200))
                        r = explosion_r
                        g = explosion_g
                        b = explosion_b
                        exploded_flag = 1.0

        if exploded:
            continue

        particles[i, 0:14] = [
            x_new, y_new, vx, vy, r, g, b, lifetime, absorb_count, cooldown,
            exploded_flag, explosion_r, explosion_g, explosion_b,
        ]


def _warm_numba(StopEvent=None):
    """
    First Numba call compiles update_particles to machine code — can take
    10-60+ seconds on Windows/LEDsim and looks like a hang if silent.
    """
    global _numba_warmed
    if _numba_warmed:
        return
    if StopEvent is not None and StopEvent.is_set():
        return
    print("[FallingSand] Compiling particle engine (Numba JIT, first run only)...", flush=True)
    t0 = time.time()
    dummy_xs = List.empty_list(types.float32)
    dummy_ys = List.empty_list(types.float32)
    update_particles(particles, active_mask, dummy_xs, dummy_ys)
    _numba_warmed = True
    print(
        f"[FallingSand] Particle engine ready ({time.time() - t0:.1f}s).",
        flush=True,
    )


def LaunchFallingSand(Duration=10, ShowIntro=True, StopEvent=None):
    global next_spawn_index, WIDTH, HEIGHT, SIM_WIDTH, SIM_HEIGHT

    # Sync sim size in case Initialize ran after this module was first imported
    WIDTH = int(getattr(LED, "HatWidth", WIDTH) or WIDTH)
    HEIGHT = int(getattr(LED, "HatHeight", HEIGHT) or HEIGHT)
    SIM_WIDTH = WIDTH
    SIM_HEIGHT = HEIGHT * 2

    if ShowIntro and not (StopEvent and StopEvent.is_set()):
        LED.ShowTitleScreen(
            BigText="Falling",
            BigTextRGB=LED.HighYellow,
            BigTextZoom=2,
            BigTextShadowRGB=LED.ShadowYellow,
            LittleText="SAND",
            LittleTextZoom=2,
            LittleTextRGB=LED.HighOrange,
            LittleTextShadowRGB=LED.ShadowOrange,
            ScrollText="Particle Simulation Engine",
            ScrollTextRGB=LED.MedGreen,
            ScrollSleep=0.02,
            DisplayTime=1,
            # ExitEffect 5 re-enters fallingsand-style FX and felt like a hang on LEDsim
            ExitEffect=0,
        )
    if StopEvent and StopEvent.is_set():
        print("[FallingSand] StopEvent before start — exiting.")
        return

    try:
        LED.ScreenArray, CursorH, CursorV = LED.TerminalScroll(
            LED.ScreenArray,
            Message="Loading particles...",
            CursorH=0,
            CursorV=0,
            MessageRGB=LED.MedYellow,
            CursorRGB=LED.MedGreen,
            CursorDarkRGB=LED.DarkGreen,
            StartingLineFeed=1,
            TypeSpeed=0.01,
            ScrollSpeed=0.01,
        )
    except Exception as exc:
        print(f"[FallingSand] Loading banner skipped: {exc}")

    _warm_numba(StopEvent)
    if StopEvent and StopEvent.is_set():
        print("[FallingSand] StopEvent after JIT — exiting.")
        return

    try:
        LED.ClearBuffers()
    except Exception:
        pass

    start_time = time.time()
    frame = 0
    print(
        f"[FallingSand] Running for {Duration} min "
        f"(StopEvent={'yes' if StopEvent is not None else 'no'})",
        flush=True,
    )

    try:
        while True:
            if StopEvent and StopEvent.is_set():
                print("[FallingSand] StopEvent received — exiting.")
                break

            if Duration and (time.time() - start_time > (float(Duration) * 60)):
                print("[FallingSand] Duration limit reached — exiting.")
                break

            if frame % SPAWN_RATE == 0:
                for _ in range(5):
                    for _ in range(MAX_PARTICLES):
                        i = next_spawn_index
                        next_spawn_index = (next_spawn_index + 1) % MAX_PARTICLES
                        if not active_mask[i]:
                            spawn_particle_fast(particles, active_mask, i)
                            break

            exploded_xs = List.empty_list(types.float32)
            exploded_ys = List.empty_list(types.float32)
            update_particles(particles, active_mask, exploded_xs, exploded_ys)

            for idx in range(len(exploded_xs)):
                x, y = exploded_xs[idx], exploded_ys[idx]
                for _ in range(PARTICLES_PER_EXPLOSION):
                    for _ in range(MAX_PARTICLES):
                        i = next_spawn_index
                        next_spawn_index = (next_spawn_index + 1) % MAX_PARTICLES
                        if not active_mask[i]:
                            spawn_explosion_particle(particles, active_mask, i, x, y)
                            break

            CAMERA_X = (SIM_WIDTH - WIDTH) // 2
            CAMERA_Y = SIM_HEIGHT - HEIGHT

            # Draw into Canvas only, then one SwapOnVSync.
            # Old path: TheMatrix.SetPixel for every pixel, then SwapOnVSync(Canvas)
            # which on LEDsim published an empty canvas → black "hang".
            canvas = LED.Canvas
            if canvas is None:
                canvas = LED.TheMatrix.CreateFrameCanvas()
                LED.Canvas = canvas

            for v in range(HEIGHT):
                for h in range(WIDTH):
                    r, g, b = LED.ScreenArray[v][h]
                    nr = max(0, int(r) - TRAIL_FADE)
                    ng = max(0, int(g) - TRAIL_FADE)
                    nb = max(0, int(b) - TRAIL_FADE)
                    LED.ScreenArray[v][h] = (nr, ng, nb)
                    canvas.SetPixel(h, v, nr, ng, nb)

            for i in range(MAX_PARTICLES):
                if not active_mask[i]:
                    continue
                x, y, _, _, r, g, b, *_ = particles[i]
                h = int(x) - CAMERA_X
                v = int(y) - CAMERA_Y
                if 0 <= h < WIDTH and 0 <= v < HEIGHT:
                    ir, ig, ib = int(r), int(g), int(b)
                    LED.ScreenArray[v][h] = (ir, ig, ib)
                    canvas.SetPixel(h, v, ir, ig, ib)

            LED.Canvas = LED.TheMatrix.SwapOnVSync(canvas)
            frame += 1
            if frame % 30 == 0:
                time.sleep(0.001)
    except KeyboardInterrupt:
        print("[FallingSand] Simulation interrupted by user.")


if __name__ == "__main__":
    LED.Initialize()
    LaunchFallingSand(Duration=1000, ShowIntro=True, StopEvent=None)
