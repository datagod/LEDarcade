# Optimized Gravity Simulator with NumPy and Numba (Eccentric Orbits)
import LEDarcade as LED
import math
import time
import random
import numpy as np
from numba import njit, prange, int32

# Configuration
G = 1.0

TimeStep = 0.05
ScrollSleep = 0.01
MaxSpeed = 50.0
SpawnInterval = 25
MergeDistance = 1.5
NumParticles = 5
MinMass = 0.01
MaxMass = 50.0
MinSpeed = 1.0
MaxSpeed = 50.0
SunMass = 5000.0

HatWidth = LED.HatWidth
HatHeight = LED.HatHeight
SunX = HatWidth / 2
SunY = HatHeight / 2
SunRGB = LED.HighYellow
TrailFade = 15


OffscreenLimit = 4.0
HatWidth_f = float(HatWidth)
HatHeight_f = float(HatHeight)


# Particle fields: x, y, vx, vy, mass, r, g, b, flash
max_particles = 100
particles = np.zeros((max_particles, 9), dtype=np.float32)
active_mask = np.zeros(max_particles, dtype=np.bool_)


@njit(parallel=True)
def update_particles(particles, active_mask, G, SunMass, SunX, SunY, TimeStep, MaxSpeed, HatWidth, HatHeight, OffscreenLimit):
    n = particles.shape[0]
    for i in prange(n):
        if not active_mask[i]:
            continue
        x, y, vx, vy, m = particles[i, :5]
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

        if (x < -HatWidth * OffscreenLimit or x > HatWidth * (1 + OffscreenLimit) or
            y < -HatHeight * OffscreenLimit or y > HatHeight * (1 + OffscreenLimit)):
            active_mask[i] = False
            continue

        particles[i,0] = x
        particles[i,1] = y
        particles[i,2] = vx
        particles[i,3] = vy
        if particles[i,8] > 0:
            particles[i,8] -= 1




@njit
def find_empty_slot(active_mask):
    for i in range(active_mask.size):
        if not active_mask[i]:
            return i
    return -1




def spawn_particle():
    i = find_empty_slot(active_mask)
    if i == -1:
        return

    margin = 10
    side = random.choice(['left', 'right', 'top', 'bottom'])

    if side == 'left':
        x = -margin
        y = random.uniform(0, HatHeight)
    elif side == 'right':
        x = HatWidth + margin
        y = random.uniform(0, HatHeight)
    elif side == 'top':
        x = random.uniform(0, HatWidth)
        y = -margin
    else:  # bottom
        x = random.uniform(0, HatWidth)
        y = HatHeight + margin

    # Vector to sun
    dx = SunX - x
    dy = SunY - y
    distance = math.sqrt(dx**2 + dy**2)
    angle_to_sun = math.atan2(dy, dx)

    # Tangential velocity: 90 degrees offset
    direction = random.choice([-1, 1])
    orbit_angle = angle_to_sun + direction * math.pi / 2  # ±90 degrees
    speed = math.sqrt(G * SunMass / distance) * random.uniform(0.9, 1.1)  # add some eccentricity
    vx = speed * math.cos(orbit_angle)
    vy = speed * math.sin(orbit_angle)

    mass = random.uniform(MinMass, MaxMass)
    color = [random.randint(50, 255) for _ in range(3)]

    particles[i,:] = [x, y, vx, vy, mass, *color, 0]
    active_mask[i] = True

    #print(f"[SPAWN] Particle {i} | Pos: ({x:.2f}, {y:.2f}) | Vel: ({vx:.2f}, {vy:.2f}) | Mass: {mass:.2f}")





# The rest of the code remains unchanged

def draw_particles():
    for i in range(particles.shape[0]):
        if not active_mask[i]:
            continue
        x, y = int(round(particles[i,0])), int(round(particles[i,1]))
        r, g, b = (255,255,255) if particles[i,8] > 0 else tuple(map(int, particles[i,5:8]))
        if 0 <= x < HatWidth and 0 <= y < HatHeight:
            LED.setpixel(x, y, r, g, b)









@njit
def merge_particles_grid(particles, active_mask, MergeDistance, HatWidth, HatHeight):
    cell_size = MergeDistance
    grid_width = int(HatWidth // cell_size) + 2
    grid_height = int(HatHeight // cell_size) + 2
    max_per_cell = 16

    grid = np.full((grid_width, grid_height, max_per_cell), -1, dtype=int32)
    counts = np.zeros((grid_width, grid_height), dtype=int32)

    def get_cell(x, y):
        return int(x // cell_size), int(y // cell_size)

    n = particles.shape[0]

    # Build the grid
    for i in range(n):
        if not active_mask[i]:
            continue
        cx, cy = get_cell(particles[i, 0], particles[i, 1])
        if 0 <= cx < grid_width and 0 <= cy < grid_height:
            count = counts[cx, cy]
            if count < max_per_cell:
                grid[cx, cy, count] = i
                counts[cx, cy] += 1

    # Check neighbors
    for i in range(n):
        if not active_mask[i]:
            continue
        xi, yi = particles[i, 0], particles[i, 1]
        ci, cj = get_cell(xi, yi)

        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                ni, nj = ci + dx, cj + dy
                if 0 <= ni < grid_width and 0 <= nj < grid_height:
                    for k in range(counts[ni, nj]):
                        j = grid[ni, nj, k]
                        if i == j or not active_mask[j]:
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
                            for c in range(5,8):
                                particles[i,c] = (particles[i,c] + particles[j,c]) / 2
                            particles[i,8] = 3
                            active_mask[j] = False
                            break





for _ in range(NumParticles):
    spawn_particle()

frame = 0
while True:
    for v in range(HatHeight):
        for h in range(HatWidth):
            r,g,b = LED.ScreenArray[v][h]
            LED.setpixel(h, v, max(0,r-TrailFade), max(0,g-TrailFade), max(0,b-TrailFade))

    LED.setpixel(int(SunX), int(SunY), *SunRGB)

    if frame % SpawnInterval == 0:
        spawn_particle()

    
    update_particles(particles, active_mask, G, SunMass, SunX, SunY, TimeStep, MaxSpeed, HatWidth_f, HatHeight_f, OffscreenLimit)

    
    merge_particles_grid(particles, active_mask, MergeDistance, HatWidth, HatHeight)
    draw_particles()
    LED.Canvas = LED.TheMatrix.SwapOnVSync(LED.Canvas)
    #time.sleep(ScrollSleep)
    frame += 1
