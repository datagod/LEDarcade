import LEDarcade as LED
import time
import random
import numpy as np
from numba import njit, prange, types
from numba.typed import List

# Configuration
PARTICLE_COLOR = (150, 150, 0)
EXPLOSION_COLOR = (255, 50, 50)
COLOR_DELTA_RANGE = 10
SPAWN_RATE = 30  # spawn a new particle every X frames
MAX_PARTICLES = 100
MAX_LIFETIME = 200
WIDTH = LED.HatWidth
HEIGHT = LED.HatHeight
RADIUS = 1
GRAVITY = 0.05
DAMPING = 0.99
STOP_THRESHOLD = 0.1  # minimum speed below which a particle sticks
TRAIL_FADE = 15
COEFF_RESTITUTION = 0.6  # realistic bounce energy retention
ABSORB_LIMIT = 3
PARTICLES_PER_EXPLOSION = 4
COOLDOWN_FRAMES = 10  # cooldown time before particle can absorb others

# Particle fields: x, y, vx, vy, r, g, b, lifetime, absorb_count, cooldown
particles = np.zeros((MAX_PARTICLES, 10), dtype=np.float32)
active_mask = np.zeros(MAX_PARTICLES, dtype=np.bool_)

@njit
def clip(x):
    return max(0, min(255, int(x)))

@njit
def mutate_color(r, g, b):
    r += random.randint(-COLOR_DELTA_RANGE, COLOR_DELTA_RANGE)
    g += random.randint(-COLOR_DELTA_RANGE, COLOR_DELTA_RANGE)
    b += random.randint(-COLOR_DELTA_RANGE, COLOR_DELTA_RANGE)
    return clip(r), clip(g), clip(b)

@njit
def find_empty_slot(mask):
    for i in range(mask.size):
        if not mask[i]:
            return i
    return -1

def spawn_particle():
    i = find_empty_slot(active_mask)
    if i == -1:
        return
    x = random.uniform(0, WIDTH - 1)
    y = 0.0
    vx = random.uniform(-1.0, 1.0)
    vy = 0.0
    r, g, b = PARTICLE_COLOR
    lifetime = MAX_LIFETIME
    particles[i] = [x, y, vx, vy, r, g, b, lifetime, 0, 0]
    active_mask[i] = True

def spawn_particle_at(x, y):
    i = find_empty_slot(active_mask)
    if i == -1:
        return
    angle = random.uniform(0, 2 * np.pi)
    speed = random.uniform(1.0, 3.0)
    vx = speed * np.cos(angle)
    vy = speed * np.sin(angle)
    r, g, b = EXPLOSION_COLOR
    lifetime = MAX_LIFETIME
    particles[i] = [x, y, vx, vy, r, g, b, lifetime, 0, COOLDOWN_FRAMES]
    active_mask[i] = True

@njit
def update_particles(particles, active_mask, exploded_xs, exploded_ys):
    for i in range(particles.shape[0]):
        if not active_mask[i]:
            continue

        x, y, vx, vy, r, g, b, lifetime, absorb_count, cooldown = particles[i]

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

        if x_new < 0 or x_new >= WIDTH:
            vx *= -COEFF_RESTITUTION
            x_new = max(0, min(WIDTH - 1, x_new))

        if y_new >= HEIGHT:
            vy = -abs(vy) * COEFF_RESTITUTION
            y_new = HEIGHT - 1

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
                    r, g, b = mutate_color(r, g, b)
                    if absorb_count >= ABSORB_LIMIT:
                        active_mask[i] = False
                        exploded_xs.append(np.float32(x_new))
                        exploded_ys.append(np.float32(y_new))
                        exploded = True
                        break
                    vx = -vx * COEFF_RESTITUTION
                    vy = -vy * COEFF_RESTITUTION

        if exploded:
            continue

        if abs(vx) < STOP_THRESHOLD and abs(vy) < STOP_THRESHOLD:
            vx = 0.0
            vy = 0.0

        particles[i] = [x_new, y_new, vx, vy, r, g, b, lifetime, absorb_count, cooldown]

# === MAIN LOOP ===
from numba.typed import List
frame = 1
try:
    while True:
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

        for v in range(HEIGHT):
            for h in range(WIDTH):
                r, g, b = LED.ScreenArray[v][h]
                LED.setpixel(h, v, max(0, r - TRAIL_FADE), max(0, g - TRAIL_FADE), max(0, b - TRAIL_FADE))

        for i in range(MAX_PARTICLES):
            if not active_mask[i]:
                continue
            x, y, _, _, r, g, b, _, _, _ = particles[i]
            if not np.isfinite(x) or not np.isfinite(y):
                continue
            h, v = int(round(x)), int(round(y))
            if 0 <= h < WIDTH and 0 <= v < HEIGHT:
                LED.setpixel(h, v, int(r), int(g), int(b))

        LED.Canvas = LED.TheMatrix.SwapOnVSync(LED.Canvas)
        frame += 1
        time.sleep(0.01)
except KeyboardInterrupt:
    LED.ClearBuffers()
    LED.Canvas = LED.TheMatrix.SwapOnVSync(LED.Canvas)
    print("Exiting Falling Sand Game.")