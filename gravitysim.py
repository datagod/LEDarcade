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
MaxMass = 10000.0
MinSpeed = 1.0
MaxSpeed = 150.0
SunMass = 100000.0
TrailFade = 5  # lower numbers mean slower fading
OffscreenLimit = 1.0  # Multiplier that defines how far particles can drift beyond SimWidth before being removed
SmoothFactor = 0.05

HatWidth = LED.HatWidth
HatHeight = LED.HatHeight
SimWidth = HatWidth * 12  # Simulation space (max zoom out)
SimHeight = HatHeight * 12
SunX = SimWidth / 2
SunY = SimHeight / 2
SunRGB = LED.HighYellow
SunRadius = 2
SunRadiusIncrease = 0.05
sun_draw_counter = 0
sun_draw_interval = 3  # recalculate radius every 3 frames
cached_sun_radius = 0
cached_sun_mask = []
GravityCutoffDistance = 20.0  # Only consider particle gravity within this range


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


try:
    old_settings = termios.tcgetattr(sys.stdin)
    tty.setcbreak(sys.stdin.fileno())
except Exception as e:
    print("Failed to set raw terminal mode:", e)
    old_settings = None




def compute_sun_radius(mass):
    return SunRadius + SunRadiusIncrease * math.sqrt(mass)


@njit(parallel=True)
def update_particles(particles, active_mask, G, sun_mass, sun_x, sun_y,
                     timestep, max_speed, sim_width, sim_height,
                     offscreen_limit, sun_radius_sq):
    mass_gain = 0.0
    n = particles.shape[0]
    for i in range(n):
        if not active_mask[i]:
            continue
        x, y, vx, vy, m = particles[i, :5]

        dx_sun = sun_x - x
        dy_sun = sun_y - y
        dist_to_sun_sq = dx_sun * dx_sun + dy_sun * dy_sun
        if dist_to_sun_sq < sun_radius_sq:
            particles[i, 8] = 5
            active_mask[i] = False
            mass_gain += m
            continue

        if dist_to_sun_sq > (sim_width * offscreen_limit) ** 2:
            particles[i, 8] = 5
            active_mask[i] = False
            continue

        dx = sun_x - x
        dy = sun_y - y
        dist_sq = dx * dx + dy * dy + 0.01
        dist = np.sqrt(dist_sq)
        force = G * sun_mass / dist_sq
        ax = force * dx / dist
        ay = force * dy / dist

        for j in range(n):
            if i == j or not active_mask[j]:
                continue
            dx = particles[j, 0] - x
            dy = particles[j, 1] - y
            dist_sq = dx * dx + dy * dy + 0.01
            dist = np.sqrt(dist_sq)
            f = G * particles[j, 4] / dist_sq
            ax += f * dx / dist
            ay += f * dy / dist

        vx += ax * timestep
        vy += ay * timestep
        speed = np.sqrt(vx * vx + vy * vy)
        if speed > max_speed:
            scale = max_speed / speed
            vx *= scale
            vy *= scale
        x += vx * timestep
        y += vy * timestep

        if (x < -sim_width * offscreen_limit or x > sim_width * (1 + offscreen_limit) or
            y < -sim_height * offscreen_limit or y > sim_height * (1 + offscreen_limit)):
            active_mask[i] = False
            continue

        particles[i, 0] = x
        particles[i, 1] = y
        particles[i, 2] = vx
        particles[i, 3] = vy

        if particles[i, 8] > 0:
            particles[i, 8] -= 1

    return mass_gain        




@njit
def build_particle_grid(particles, active_mask, sim_width, sim_height, merge_distance, max_per_cell):
    n = particles.shape[0]
    cell_size = merge_distance
    grid_width = int(sim_width // cell_size) + 2
    grid_height = int(sim_height // cell_size) + 2

    grid = -1 * np.ones((grid_width, grid_height, max_per_cell), dtype=np.int32)
    counts = np.zeros((grid_width, grid_height), dtype=np.int32)

    for i in range(n):
        if not active_mask[i]:
            continue
        cx = int(particles[i, 0] // cell_size)
        cy = int(particles[i, 1] // cell_size)
        if 0 <= cx < grid_width and 0 <= cy < grid_height:
            count = counts[cx, cy]
            if count < max_per_cell:
                grid[cx, cy, count] = i
                counts[cx, cy] += 1

    return grid, counts, grid_width, grid_height


@njit(parallel=True)
def apply_gravity_parallel(particles, active_mask, G, sun_mass, sun_x, sun_y,
                           timestep, max_speed, grid, counts,
                           grid_width, grid_height, cell_size,
                           cutoff_distance_sq):
    n = particles.shape[0]

    for i in prange(n):
        if not active_mask[i]:
            continue

        x, y, vx, vy, m = particles[i, :5]

        # Sun gravity
        dx = sun_x - x
        dy = sun_y - y
        dist_sq = dx * dx + dy * dy + 0.01
        inv_dist = 1.0 / np.sqrt(dist_sq)
        force = G * sun_mass / dist_sq
        ax = force * dx * inv_dist
        ay = force * dy * inv_dist

        # Inter-particle gravity
        ci = int(x // cell_size)
        cj = int(y // cell_size)

        for dxg in (-1, 0, 1):
            for dyg in (-1, 0, 1):
                ni = ci + dxg
                nj = cj + dyg
                if 0 <= ni < grid_width and 0 <= nj < grid_height:
                    for k in range(counts[ni, nj]):
                        j = grid[ni, nj, k]
                        if j == i or not active_mask[j]:
                            continue
                        dxp = particles[j, 0] - x
                        dyp = particles[j, 1] - y
                        distsq = dxp * dxp + dyp * dyp
                        if distsq > cutoff_distance_sq:
                            continue
                        inv_d = 1.0 / np.sqrt(distsq + 0.01)
                        f = G * particles[j, 4] / distsq
                        ax += f * dxp * inv_d
                        ay += f * dyp * inv_d

        # Update motion
        vx += ax * timestep
        vy += ay * timestep
        speed_sq = vx * vx + vy * vy
        if speed_sq > max_speed * max_speed:
            scale = max_speed / np.sqrt(speed_sq)
            vx *= scale
            vy *= scale
        x += vx * timestep
        y += vy * timestep

        particles[i, 0] = x
        particles[i, 1] = y
        particles[i, 2] = vx
        particles[i, 3] = vy





# Serial: absorb into sun, check bounds, apply particle decay, and accumulate mass gain
@njit
def post_process_particles(
    particles, active_mask, sun_x, sun_y,
    sim_width, sim_height, offscreen_limit,
    sun_radius_sq,
    min_x, max_x, min_y, max_y, max_radius_sq
):
    mass_gain = 0.0
    n = particles.shape[0]
    for i in range(n):
        if not active_mask[i]:
            continue

        x, y = particles[i, 0], particles[i, 1]
        dx = sun_x - x
        dy = sun_y - y
        dist_to_sun_sq = dx * dx + dy * dy

        if dist_to_sun_sq < sun_radius_sq:
            particles[i, 8] = 5
            active_mask[i] = False
            mass_gain += particles[i, 4]
            continue

        if dist_to_sun_sq > max_radius_sq:
            particles[i, 8] = 5
            active_mask[i] = False
            continue

        if x < min_x or x > max_x or y < min_y or y > max_y:
            active_mask[i] = False
            continue

        if particles[i, 8] > 0:
            particles[i, 8] -= 1

    return mass_gain





def draw_sun():
    global sun_draw_counter, cached_sun_radius, cached_sun_mask
    global SunMass, SunX, SunY, zoom

    sun_draw_counter += 1
    if sun_draw_counter % sun_draw_interval == 0:
        # Recalculate radius and mask
        radius = compute_sun_radius(SunMass)
        cached_sun_radius = max(1, int(radius / zoom))
        cached_sun_mask = []
        for dx in range(-cached_sun_radius, cached_sun_radius + 1):
            for dy in range(-cached_sun_radius, cached_sun_radius + 1):
                if dx * dx + dy * dy <= cached_sun_radius * cached_sun_radius:
                    cached_sun_mask.append((dx, dy))

    offset_x = SunX - (HatWidth / 2) * zoom
    offset_y = SunY - (HatHeight / 2) * zoom
    cx = int((SunX - offset_x) / zoom)
    cy = int((SunY - offset_y) / zoom)

    for dx, dy in cached_sun_mask:
        x = cx + dx
        y = cy + dy
        if 0 <= x < HatWidth and 0 <= y < HatHeight:
            LED.setpixel(x, y, *SunRGB)



    



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



@njit
def _spawn_particle(
    i, side, x_spawn, y_spawn,
    vx, vy, mass, r, g, b,
    SunX, SunY, particles, active_mask
):
    if side == 0:   # left
        x = -1
        y = y_spawn
    elif side == 1:  # right
        x = SimWidth + 1
        y = y_spawn
    elif side == 2:  # top
        x = x_spawn
        y = -1
    else:           # bottom
        x = x_spawn
        y = SimHeight + 1

    particles[i, 0] = x
    particles[i, 1] = y
    particles[i, 2] = vx
    particles[i, 3] = vy
    particles[i, 4] = mass
    particles[i, 5] = r
    particles[i, 6] = g
    particles[i, 7] = b
    particles[i, 8] = 5
    active_mask[i] = True




def spawn_particle():
    global burst_bias, burst_timer

    i = find_empty_slot(active_mask)
    if i == -1:
        return

    side = np.random.randint(0, 4)
    direction = -1 if np.random.rand() < 0.5 else 1

    if side in [0, 1]:  # left or right
        x_spawn = 0
        y_spawn = np.random.uniform(0, SimHeight)
    else:  # top or bottom
        x_spawn = np.random.uniform(0, SimWidth)
        y_spawn = 0

    # Approximate spawn position toward sun
    dx = SunX - (0 if side == 0 else SimWidth if side == 1 else x_spawn)
    dy = SunY - (y_spawn if side in [0, 1] else 0 if side == 2 else SimHeight)
    distance = math.sqrt(dx**2 + dy**2)
    angle_to_sun = math.atan2(dy, dx)

    orbit_angle = angle_to_sun + direction * math.pi / 2
    speed = math.sqrt(G * SunMass / max(distance, 1)) * np.random.uniform(0.9, 1.1)

    # Bias burst logic (optional)
    if burst_bias and burst_timer > 0:
        vx, vy = burst_bias
        burst_timer -= 1
    else:
        vx = speed * math.cos(orbit_angle)
        vy = speed * math.sin(orbit_angle)
        if np.random.rand() < BurstBiasChance:
            burst_bias = (vx, vy)
            burst_timer = BiasDuration

    if np.random.rand() < 0.1:
        vx *= 2
        vy *= 2

    # Safety minimum velocity
    if vx**2 + vy**2 < 0.01:
        vx = 1.0 * math.cos(orbit_angle)
        vy = 1.0 * math.sin(orbit_angle)
        print("Spawn kick applied")



    mass = np.random.uniform(MinMass, MaxMass)
    r, g, b = [np.random.randint(50, 256) for _ in range(3)]

    _spawn_particle(i, side, x_spawn, y_spawn, vx, vy, mass, r, g, b, SunX, SunY, particles, active_mask)

    print(f"Spawn: Particle {i} Mass {mass:.2f}")





def draw_particles():
    offset_x = SunX - (HatWidth / 2) * zoom
    offset_y = SunY - (HatHeight / 2) * zoom
    for i in range(particles.shape[0]):
        if not active_mask[i]:
            continue
        x = int(round((particles[i,0] - offset_x) / zoom))
        y = int(round((particles[i,1] - offset_y) / zoom))
        r, g, b = (255,255,255) if particles[i,8] > 0 else tuple(map(int, particles[i,5:8]))

        LED.setpixel(x, y, r, g, b)




@njit(parallel=True)
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



# Optimized particle merging using grid bucket system
@njit
def merge_particles_grid(particles, active_mask, merge_distance, sim_width, sim_height, sun_x, sun_y):
    cell_size = merge_distance
    grid_width = int(sim_width // cell_size) + 2
    grid_height = int(sim_height // cell_size) + 2
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
                        dist_sq = dx_ * dx_ + dy_ * dy_
                        if dist_sq < merge_distance * merge_distance:
                            mi, mj = particles[i, 4], particles[j, 4]
                            mtot = mi + mj
                            if mtot == 0:
                                continue
                            particles[i, 0] = (xi * mi + xj * mj) / mtot
                            particles[i, 1] = (yi * mi + yj * mj) / mtot
                            particles[i, 2] = (particles[i, 2] * mi + particles[j, 2] * mj) / mtot
                            particles[i, 3] = (particles[i, 3] * mi + particles[j, 3] * mj) / mtot
                            particles[i, 4] = mtot

                            v2 = particles[i, 2] ** 2 + particles[i, 3] ** 2
                            if v2 < 0.01:
                                angle = math.atan2(particles[i, 1] - sun_y, particles[i, 0] - sun_x) + math.pi / 2
                                particles[i, 2] += 0.5 * math.cos(angle)
                                particles[i, 3] += 0.5 * math.sin(angle)

                            for c in range(5, 8):
                                particles[i, c] = (particles[i, c] + particles[j, c]) / 2

                            particles[i, 8] = 3
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

        draw_sun()


        if frame % SpawnInterval == 0:
            spawn_particle()

        
        # Replace update_particles(...) with two calls:
        sun_radius = compute_sun_radius(SunMass)
        sun_radius_sq = sun_radius * sun_radius
        
        
        
        
        grid, counts, gw, gh = build_particle_grid(
            particles, active_mask, SimWidth, SimHeight, MergeDistance, max_per_cell=16
        )

        apply_gravity_parallel(
            particles, active_mask, G, SunMass, SunX, SunY,
            TimeStep, MaxSpeed,
            grid, counts, gw, gh, MergeDistance,
            GravityCutoffDistance ** 2
        )


        min_x = -SimWidth * OffscreenLimit
        max_x = SimWidth * (1 + OffscreenLimit)
        min_y = -SimHeight * OffscreenLimit
        max_y = SimHeight * (1 + OffscreenLimit)
        max_radius_sq = (SimWidth * OffscreenLimit) ** 2

        mass_gain = post_process_particles(
            particles, active_mask, SunX, SunY,
            SimWidth, SimHeight, OffscreenLimit,
            sun_radius_sq,
            min_x, max_x, min_y, max_y, max_radius_sq
        )
        SunMass += mass_gain



        merge_particles_grid(particles, active_mask, MergeDistance, SimWidth, SimHeight, SunX, SunY)



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
            print(f"FPS: {fps_counter} Zoom: {zoom:.2f} SunMass: {SunMass:.2f} SunRadius: {SunRadius:.4f}")
            fps_counter = 0
            last_time = current_time

        frame += 1

finally:
    if old_settings:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)



