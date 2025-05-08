# ============================================================================
# Gravity Particle Simulator for LED Matrix Displays
# ----------------------------------------------------------------------------
# Developed collaboratively by ChatGPT (OpenAI) and Gizmo (Datagod)
#
# DESCRIPTION:
# This is a highly optimized 2D gravity simulation designed for LED matrix
# displays such as 32x32, 64x32, or 128x32 pixel arrays controlled via the
# LEDarcade framework.
#
# The simulation models Newtonian gravitational interactions between a central
# "sun" and a swarm of particles, which orbit, interact, and may eventually
# escape or merge. Realistic orbital behavior is created using tangential
# velocity initialization.
#
# Key features:
# - High-performance physics using NumPy and Numba JIT acceleration.
# - Dynamic visual zooming (in/out) with fixed camera centered on the sun.
# - Real-time particle rendering with trail fading for motion effect.
# - Screen-space scaling of particles based on zoom factor.
#
# SYSTEM REQUIREMENTS:
# - Python 3.x
# - NumPy, Numba, and LEDarcade module
# - RGBMatrix and compatible LED panel
#
# VERSION:
# - Initial version with dynamic zoom and centered camera: May 2025
#
# CONTRIBUTORS:
# - Gizmo / Datagod: LEDarcade ecosystem, integration, visual tuning
# - ChatGPT: Physics core, optimization, and documentation
#
# ----------------------------------------------------------------------------
# CHANGELOG:
# ----------------------------------------------------------------------------
# May 2025 - Initial version with dynamic zooming and centered camera offset
# May 2025 - Sun position fixed relative to screen center while zooming
# May 2025 - Particle merging logic planned for future integration
#
# ----------------------------------------------------------------------------
# USAGE:
# ----------------------------------------------------------------------------
# 1. Install dependencies:
#    pip install numpy numba rgbmatrix
#
# 2. Ensure LEDarcade is configured for your matrix dimensions
#
# 3. Run the script on a Raspberry Pi connected to an LED matrix:
#    python3 this_file.py
#
# 4. Watch particles spawn, orbit, and fade in and out
#    You can stop the program with Ctrl+C
# ============================================================================

import LEDarcade as LED
import math
import time
import random
import numpy as np
from numba import njit, prange


import sys
import select
import tty
import termios



# Configuration
G = 10.0
TimeStep = 0.1
ScrollSleep = 0.01
MaxSpeed = 100.0
SpawnInterval = 100
MergeDistance = 1.5
NumParticles = 10
max_particles = 50

MinMass = 0.01
MaxMass = 50.0
MinSpeed = 1.0
MaxSpeed = 150.0
SunMass = 100000.0
TrailFade = 5  # lower numbers mean slower fading
OffscreenLimit = 1.0  # Multiplier that defines how far particles can drift beyond SimWidth before being removed
SmoothFactor = 0.05

HatWidth = LED.HatWidth
HatHeight = LED.HatHeight
SimWidth = HatWidth * 10  # Simulation space (max zoom out)
SimHeight = HatHeight * 10
SunX = SimWidth / 2
SunY = SimHeight / 2
SunRGB = LED.HighYellow

zoom = 1.0
MinZoom = 1
MaxZoom = 256
zoom_direction = -0.01

# Particle fields: x, y, vx, vy, mass, r, g, b, flash
particles = np.zeros((max_particles, 9), dtype=np.float32)
active_mask = np.zeros(max_particles, dtype=np.bool_)


BurstBiasChance = 0.25
BurstSize = 5
BiasDuration = 50  # frames
burst_bias = None  # Will hold a (vx, vy) direction
burst_timer = 0

manual_zoom_active = False
manual_zoom_level = 1.0





def get_keypress():
    dr, _, _ = select.select([sys.stdin], [], [], 0)
    if dr:
        return sys.stdin.read(1)
    return None

# Set terminal to raw mode to capture single keypresses
old_settings = termios.tcgetattr(sys.stdin)
tty.setcbreak(sys.stdin.fileno())




@njit(parallel=True)
def update_particles(particles, active_mask, G, SunMass, SunX, SunY, TimeStep, MaxSpeed, SimWidth, SimHeight, OffscreenLimit):
    n = particles.shape[0]
    for i in prange(n):
        if not active_mask[i]:
            continue
        x, y, vx, vy, m = particles[i, :5]
        # Absorb into sun if too close
        dx_sun = SunX - x
        dy_sun = SunY - y
        dist_to_sun_sq = dx_sun * dx_sun + dy_sun * dy_sun
        if dist_to_sun_sq < MergeDistance * MergeDistance:
            particles[i,8] = 5  # Set flash first
            active_mask[i] = False
            continue

        if dist_to_sun_sq > (SimWidth * OffscreenLimit) ** 2:
            particles[i,8] = 5  # Set flash first
            active_mask[i] = False
            continue


        dx = SunX - x
        dy = SunY - y
        dist_sq = dx*dx + dy*dy + 0.01
        dist = np.sqrt(dist_sq)
        force = G * SunMass / dist_sq
        ax = force * dx / dist
        ay = force * dy / dist
        for j in range(n):
            if i == j or not active_mask[j]:
                continue
            dx = particles[j,0] - x
            dy = particles[j,1] - y
            dist_sq = dx*dx + dy*dy + 0.01
            dist = np.sqrt(dist_sq)
            f = G * particles[j,4] / dist_sq
            ax += f * dx / dist
            ay += f * dy / dist
        vx += ax * TimeStep
        vy += ay * TimeStep
        speed = np.sqrt(vx*vx + vy*vy)
        if speed > MaxSpeed:
            scale = MaxSpeed / speed
            vx *= scale
            vy *= scale
        x += vx * TimeStep
        y += vy * TimeStep

        if (x < -SimWidth * OffscreenLimit or x > SimWidth * (1 + OffscreenLimit) or
            y < -SimHeight * OffscreenLimit or y > SimHeight * (1 + OffscreenLimit)):
            active_mask[i] = False
            continue

        particles[i,0] = x
        particles[i,1] = y
        particles[i,2] = vx
        particles[i,3] = vy


        
        
        

@njit
def find_empty_slot(active_mask):
    for i in range(active_mask.size):
        if not active_mask[i]:
            return i
    return -1

@njit
def init_particle_array(i, x, y, vx, vy, mass, r, g, b, particles):
    particles[i,0] = x
    particles[i,1] = y
    particles[i,2] = vx
    particles[i,3] = vy
    particles[i,4] = mass
    particles[i,5] = r
    particles[i,6] = g
    particles[i,7] = b
    speed_mag = np.sqrt(vx**2 + vy**2)
    particles[i,8] = int(min(10, max(1, (mass + speed_mag) / 10)))



def spawn_particle():
    global burst_bias, burst_timer

    i = find_empty_slot(active_mask)
    if i == -1:
        return

    # Choose spawn edge
    side = random.choice(['left', 'right', 'top', 'bottom'])

    if side == 'left':
        x = -1
        y = random.uniform(0, SimHeight)
    elif side == 'right':
        x = SimWidth + 1
        y = random.uniform(0, SimHeight)
    elif side == 'top':
        x = random.uniform(0, SimWidth)
        y = -1
    else:
        x = random.uniform(0, SimWidth)
        y = SimHeight + 1

    dx = SunX - x
    dy = SunY - y
    distance = math.sqrt(dx**2 + dy**2)
    angle_to_sun = math.atan2(dy, dx)

    # Apply burst bias if active
    if burst_bias and burst_timer > 0:
        orbit_angle = math.atan2(burst_bias[1], burst_bias[0])
        speed = np.linalg.norm(burst_bias)
        burst_timer -= 1
    else:
        direction = random.choice([-1, 1])
        orbit_angle = angle_to_sun + direction * math.pi / 2
        speed = math.sqrt(G * SunMass / distance) * random.uniform(0.9, 1.1)

        # Start a new burst occasionally
        if random.random() < BurstBiasChance:
            burst_bias = (
                speed * math.cos(orbit_angle),
                speed * math.sin(orbit_angle)
            )
            burst_timer = BiasDuration

    vx = speed * math.cos(orbit_angle)
    vy = speed * math.sin(orbit_angle)

    # Occasionally spawn rogue high-speed eccentric object
    if random.random() < 0.1:
        speed *= 2.0
        vx = speed * math.cos(orbit_angle)
        vy = speed * math.sin(orbit_angle)

    mass = random.uniform(MinMass, MaxMass)
    r, g, b = [random.randint(50, 255) for _ in range(3)]
    init_particle_array(i, x, y, vx, vy, mass, r, g, b, particles)
    active_mask[i] = True

    print(f"Spawn: Particle {i}")





    # Ensure minimum movement to prevent accidental explosion
    speed_sq = vx**2 + vy**2
    if speed_sq < 0.01:
        angle = angle_to_sun + math.pi / 2  # Tangential direction
        vx = 1.0 * math.cos(angle)
        vy = 1.0 * math.sin(angle)
        print("Spawn kick applied")  # Optional debug


def draw_particles():
    offset_x = SunX - (HatWidth / 2) * zoom
    offset_y = SunY - (HatHeight / 2) * zoom
    for i in range(particles.shape[0]):
        if not active_mask[i]:
            continue
        x = int(round((particles[i,0] - offset_x) / zoom))
        y = int(round((particles[i,1] - offset_y) / zoom))
        r, g, b = (255,255,255) if particles[i,8] > 0 else tuple(map(int, particles[i,5:8]))


        



@njit
def compute_max_distance(particles, active_mask, SunX, SunY):
    max_distance = 0.0
    for i in range(particles.shape[0]):
        if not active_mask[i]:
            continue
        dx = particles[i,0] - SunX
        dy = particles[i,1] - SunY
        dist = np.sqrt(dx*dx + dy*dy)
        if dist > max_distance:
            max_distance = dist
    return max_distance



@njit
def merge_particles_grid(particles, active_mask, MergeDistance, SimWidth, SimHeight):
    cell_size = MergeDistance
    grid_width = int(SimWidth // cell_size) + 2
    grid_height = int(SimHeight // cell_size) + 2
    max_per_cell = 16

    grid = -1 * np.ones((grid_width, grid_height, max_per_cell), dtype=np.int32)
    counts = np.zeros((grid_width, grid_height), dtype=np.int32)
    merged_mask = np.zeros(particles.shape[0], dtype=np.bool_)

    def get_cell(x, y):
        return int(x // cell_size), int(y // cell_size)

    n = particles.shape[0]
    for i in range(n):
        if not active_mask[i]:
            continue
        cx, cy = get_cell(particles[i, 0], particles[i, 1])
        if 0 <= cx < grid_width and 0 <= cy < grid_height:
            count = counts[cx, cy]
            if count < max_per_cell:
                grid[cx, cy, count] = i
                counts[cx, cy] += 1

    for i in range(n):
        if not active_mask[i] or merged_mask[i]:
            continue
        xi, yi = particles[i, 0], particles[i, 1]
        ci, cj = get_cell(xi, yi)

        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                ni, nj = ci + dx, cj + dy
                if 0 <= ni < grid_width and 0 <= nj < grid_height:
                    for k in range(counts[ni, nj]):
                        j = grid[ni, nj, k]
                        if i == j or not active_mask[j] or merged_mask[j] or j < i:
                            continue
                        xj, yj = particles[j, 0], particles[j, 1]
                        dx_ = xi - xj
                        dy_ = yi - yj
                        dist = np.sqrt(dx_ * dx_ + dy_ * dy_)
                        if dist < MergeDistance:
                            mi, mj = particles[i,4], particles[j,4]
                            mtot = mi + mj
                            particles[i,0] = (xi*mi + xj*mj)/mtot
                            particles[i,1] = (yi*mi + yj*mj)/mtot
                            particles[i,2] = (particles[i,2]*mi + particles[j,2]*mj)/mtot
                            particles[i,3] = (particles[i,3]*mi + particles[j,3]*mj)/mtot
                            particles[i,4] = mtot

                            # Ensure merged particle keeps moving
                            v2 = particles[i,2]**2 + particles[i,3]**2
                            if v2 < 0.01:  # Too slow = nearly frozen
                                # Add tiny tangential nudge
                                angle = math.atan2(particles[i,1] - SunY, particles[i,0] - SunX) + math.pi / 2
                                particles[i,2] += 0.5 * math.cos(angle)
                                particles[i,3] += 0.5 * math.sin(angle)


                            for c in range(5,8):
                                particles[i,c] = (particles[i,c] + particles[j,c]) / 2
                            particles[i,8] = 3
                            active_mask[j] = False
                            merged_mask[i] = True
                            break


for _ in range(NumParticles):
    spawn_particle()

frame = 0
last_time = time.time()
fps_counter = 0


try:
    while True:
        key = get_keypress()
        if key:
            if key == '0':
                manual_zoom_active = False
            elif key in '123456789':
                level = int(key)
                manual_zoom_level = min(MaxZoom, 2 ** (level - 1))  # 1→1, 2→2, 3→4, ..., 9→256
                manual_zoom_active = True


        for v in range(HatHeight):
            for h in range(HatWidth):
                r,g,b = LED.ScreenArray[v][h]
                LED.setpixel(h, v, max(0,r-TrailFade), max(0,g-TrailFade), max(0,b-TrailFade))

        offset_x = SunX - (HatWidth / 2) * zoom
        offset_y = SunY - (HatHeight / 2) * zoom
        LED.setpixel(int((SunX - offset_x) / zoom), int((SunY - offset_y) / zoom), *SunRGB)

        if frame % SpawnInterval == 0:
            spawn_particle()

        update_particles(particles, active_mask, G, SunMass, SunX, SunY, TimeStep, MaxSpeed, SimWidth, SimHeight, OffscreenLimit)
        merge_particles_grid(particles, active_mask, MergeDistance, SimWidth, SimHeight)

        draw_particles()
        LED.Canvas = LED.TheMatrix.SwapOnVSync(LED.Canvas)

        max_distance = compute_max_distance(particles, active_mask, SunX, SunY)
        target_radius = max(HatWidth, HatHeight) * 0.45
        target_zoom = max(MinZoom, min(MaxZoom, max_distance / target_radius))

        if manual_zoom_active:
            zoom = manual_zoom_level
        else:
            zoom = zoom + SmoothFactor * (target_zoom - zoom)

        fps_counter += 1
        current_time = time.time()
        if current_time - last_time >= 1.0:
            print(f"FPS: {fps_counter} Zoom: {zoom}")
            fps_counter = 0
            last_time = current_time

        frame += 1

finally:
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
