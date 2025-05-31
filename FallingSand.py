


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

-------------------------------------------------------------------------------
PARTICLE STRUCTURE
-------------------------------------------------------------------------------

Each particle is represented as a row in a NumPy array with 14 float values:
[x, y, vx, vy, r, g, b, lifetime, absorb_count, cooldown, exploded_flag, 
 explosion_r, explosion_g, explosion_b]

Meaning:
- Position: (x, y)
- Velocity: (vx, vy)
- Color: (r, g, b)
- Lifetime: how many frames before expiration
- Absorb count: number of collisions endured
- Cooldown: frames before it can be absorbed again
- Explosion flag and color: used to change color during an explosion

-------------------------------------------------------------------------------
RENDERING
-------------------------------------------------------------------------------

Particles are simulated on a virtual canvas 2x the screen resolution for
better dynamics and scaled/cropped to the LED matrix view window.

Each frame:
- Screen is faded by subtracting a trail fade constant from each RGB channel.
- Active particles are rendered to the display if within view boundaries.
- Particle states are updated in-place using the JIT-compiled function.


===============================================================================
"""



import LEDarcade as LED
LED.Initialize()

import time
import random
import numpy as np
from numba import njit, prange, types
from numba.typed import List

# Configuration
PARTICLE_COLOR = (150, 150, 0)
SPAWN_RATE = 20
MAX_PARTICLES = 200
MAX_LIFETIME = 1000
WIDTH = LED.HatWidth
HEIGHT = LED.HatHeight
SIM_WIDTH = WIDTH 
SIM_HEIGHT = HEIGHT * 2
RADIUS = 1
GRAVITY = 0.075
DAMPING = 0.99
TRAIL_FADE = 15
COEFF_RESTITUTION = 0.6
ABSORB_LIMIT = 5
PARTICLES_PER_EXPLOSION = 3
COOLDOWN_FRAMES = 10

# Particle fields:
# x, y, vx, vy, r, g, b, lifetime, absorb_count, cooldown, exploded_flag, explosion_r, explosion_g, explosion_b
particles = np.zeros((MAX_PARTICLES, 14), dtype=np.float32)
active_mask = np.zeros(MAX_PARTICLES, dtype=np.bool_)

@njit
def clip(x):
    return max(0, min(255, int(x)))

@njit
def find_empty_slot(mask):
    for i in range(mask.size):
        if not mask[i]:
            return i
    return -1

def random_explosion_color():
    return (
        float(random.randint(100, 255)),
        float(random.randint(0, 200)),
        float(random.randint(0, 200))
    )

def spawn_particle():
    i = find_empty_slot(active_mask)
    if i == -1:
        return
    x = float(random.uniform((SIM_WIDTH - WIDTH) // 2, (SIM_WIDTH + WIDTH) // 2))
    y = float(SIM_HEIGHT - HEIGHT - 1)  # 1 pixel above the visible screen
    vx = float(random.uniform(-1.0, 1.0))
    vy = 0.0
    r, g, b = map(float, PARTICLE_COLOR)
    lifetime = float(MAX_LIFETIME)
    exploded_flag = 0.0
    explosion_r, explosion_g, explosion_b = 0.0, 0.0, 0.0
    particles[i] = [x, y, vx, vy, r, g, b, lifetime, 0.0, 0.0, exploded_flag, explosion_r, explosion_g, explosion_b]
    active_mask[i] = True

def spawn_particle_at(x, y):
    i = find_empty_slot(active_mask)
    if i == -1:
        return
    angle = random.uniform(0, 2 * np.pi)
    speed = random.uniform(1.0, 3.0)
    vx = float(speed * np.cos(angle))
    vy = float(speed * np.sin(angle))
    r, g, b = random_explosion_color()
    lifetime = float(MAX_LIFETIME)
    particles[i] = [x, y, vx, vy, r, g, b, lifetime, 0.0, float(COOLDOWN_FRAMES), 1.0, r, g, b]
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

        # Allow particles to leave the left/right edges

        if y_new >= SIM_HEIGHT:
            vy = -abs(vy) * COEFF_RESTITUTION
            y_new = SIM_HEIGHT - 1

        if y_new < 0:
            vy = abs(vy) * COEFF_RESTITUTION
            y_new = 0

        exploded = False
        if cooldown <= 0:
            for j in range(particles.shape[0]):
                if i == j or not active_mask[j]:
                    continue
                xj, yj = particles[j, 0], particles[j, 1]
                dx = x_new - xj
                dy = y_new - yj
                dist_sq = dx * dx + dy * dy
                if dist_sq < RADIUS * RADIUS:
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

        particles[i] = [x_new, y_new, vx, vy, r, g, b, lifetime, absorb_count, cooldown, exploded_flag, explosion_r, explosion_g, explosion_b]



def LaunchFallingSand(Duration=10, ShowIntro=True, StopEvent=None):
    import LEDarcade as LED
    LED.Initialize()


    if ShowIntro:
        LED.ShowTitleScreen(
            BigText="Falling",
            BigTextRGB=LED.HighYellow,
            BigTextZoom = 2,
            BigTextShadowRGB=LED.ShadowYellow,
            LittleText="SAND",
            LittleTextZoom = 2,
            LittleTextRGB=LED.HighOrange,
            LittleTextShadowRGB=LED.ShadowOrange,
            ScrollText="Particle Simulation Engine",
            ScrollTextRGB=LED.MedGreen,
            ScrollSleep=0.02,
            DisplayTime=1,
            ExitEffect=5
        )


        LED.ScreenArray, CursorH, CursorV = LED.TerminalScroll(
            LED.ScreenArray,
            Message="Preparing particle array, please be patient while we load the next phase of the simulation....",
            CursorH=0,
            CursorV=0,
            MessageRGB=LED.MedYellow,
            CursorRGB=LED.MedGreen,
            CursorDarkRGB=LED.DarkGreen,
            StartingLineFeed=1,
            TypeSpeed=0.02,
            ScrollSpeed=0.01
        )
        #LED.ZoomScreen(LED.ScreenArray, 32, 1, Fade=True, ZoomSleep=0.03)






    frame = 1


    try:
        print("Compiling... Please wait for JIT warm-up.")
        dummy_xs = List.empty_list(types.float32)
        dummy_ys = List.empty_list(types.float32)
        update_particles(particles, active_mask, dummy_xs, dummy_ys)
        print("JIT warm-up complete. Starting simulation.")
        Done = False
        while Done == False:

            if StopEvent and StopEvent.is_set():
                print("\n" + "="*40)
                print("[TRON] StopEvent received")
                print("-> Shutting down gracefully...")
                print("="*40 + "\n")
                Done = True
                break


            if frame % SPAWN_RATE == 0:
                spawn_particle()

            exploded_xs = List.empty_list(types.float32)
            exploded_ys = List.empty_list(types.float32)
            update_particles(particles, active_mask, exploded_xs, exploded_ys)

            for idx in range(len(exploded_xs)):
                x = exploded_xs[idx]
                y = exploded_ys[idx]
                for _ in range(PARTICLES_PER_EXPLOSION):
                    spawn_particle_at(x, y)

            CAMERA_X = (SIM_WIDTH - WIDTH) // 2
            CAMERA_Y = SIM_HEIGHT - HEIGHT

            for v in range(HEIGHT):
                for h in range(WIDTH):
                    r, g, b = LED.ScreenArray[v][h]
                    LED.setpixel(h, v, max(0, r - TRAIL_FADE), max(0, g - TRAIL_FADE), max(0, b - TRAIL_FADE))

            for i in range(MAX_PARTICLES):
                if not active_mask[i]:
                    continue
                x, y, _, _, r, g, b, _, _, _, _, _, _, _ = particles[i]
                if not np.isfinite(x) or not np.isfinite(y):
                    continue
                h = int(round(x)) - CAMERA_X
                v = int(round(y)) - CAMERA_Y
                if 0 <= h < WIDTH and 0 <= v < HEIGHT:
                    LED.setpixel(h, v, int(r), int(g), int(b))

            LED.Canvas = LED.TheMatrix.SwapOnVSync(LED.Canvas)
            frame += 1
    except KeyboardInterrupt:
        LED.ClearBuffers()
        LED.Canvas = LED.TheMatrix.SwapOnVSync(LED.Canvas)
        print("Exiting Falling Sand Game.")


        LED.SweepClean()

   


#execute if this script is called directly
if __name__ == "__main__" :
  while(1==1):
    LaunchFallingSand(Duration=1000, ShowIntro=True, StopEvent = None)        








