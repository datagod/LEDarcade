# Optimized Gravity Simulator with NumPy and Numba (Eccentric Orbits)
import LEDarcade as LED
import math
import time
import random
import numpy as np
from numba import njit, prange

# Configuration
G = 1.0
SunMass = 500.0
TimeStep = 0.2
ScrollSleep = 0.01
MaxSpeed = 20.0
SpawnInterval = 100
MergeDistance = 1.5
NumParticles = 5

HatWidth = LED.HatWidth
HatHeight = LED.HatHeight
SunX = HatWidth / 2
SunY = HatHeight / 2
SunRGB = LED.HighYellow
TrailFade = 15

# Particle fields: x, y, vx, vy, mass, r, g, b, flash
max_particles = 512
particles = np.zeros((max_particles, 9), dtype=np.float32)
active_mask = np.zeros(max_particles, dtype=np.bool_)

@njit(parallel=True)
def update_particles(particles, active_mask, G, SunMass, TimeStep, MaxSpeed):
    n = particles.shape[0]
    for i in prange(n):
        if not active_mask[i]:
            continue
        x, y, vx, vy, m = particles[i, :5]
        dx = SunX - x
        dy = SunY - y
        dist_sq = dx*dx + dy*dy + 0.01
        dist = math.sqrt(dist_sq)
        force = G * SunMass / dist_sq
        ax = force * dx / dist
        ay = force * dy / dist
        for j in range(n):
            if i == j or not active_mask[j]:
                continue
            dx = particles[j,0] - x
            dy = particles[j,1] - y
            dist_sq = dx*dx + dy*dy + 0.01
            dist = math.sqrt(dist_sq)
            f = G * particles[j,4] / dist_sq
            ax += f * dx / dist
            ay += f * dy / dist
        vx += ax * TimeStep
        vy += ay * TimeStep
        speed = math.sqrt(vx*vx + vy*vy)
        if speed > MaxSpeed:
            scale = MaxSpeed / speed
            vx *= scale
            vy *= scale
        particles[i,0] += vx * TimeStep
        particles[i,1] += vy * TimeStep
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
    angle = random.uniform(0, 2 * math.pi)
    radius = random.uniform(min(HatWidth, HatHeight)/2.5, min(HatWidth, HatHeight)/2 - 1)
    x = SunX + radius * math.cos(angle)
    y = SunY + radius * math.sin(angle)
    speed = math.sqrt(G * SunMass / radius)

    # Eccentric variation and random direction
    ecc_factor = random.uniform(0.5, 1.5)
    direction = random.choice([-1, 1])
    vx = direction * -speed * math.sin(angle) * ecc_factor
    vy = direction * speed * math.cos(angle) * ecc_factor

    mass = random.uniform(0.5, 2.0)
    color = [random.randint(50,255) for _ in range(3)]
    particles[i,:] = [x, y, vx, vy, mass, *color, 0]
    active_mask[i] = True

# The rest of the code remains unchanged

def draw_particles():
    for i in range(particles.shape[0]):
        if not active_mask[i]:
            continue
        x, y = int(round(particles[i,0])), int(round(particles[i,1]))
        r, g, b = (255,255,255) if particles[i,8] > 0 else tuple(map(int, particles[i,5:8]))
        radius = min(2, max(1, int(particles[i,4] / 3)))
        for dv in range(-radius + 1, radius):
            for dh in range(-radius + 1, radius):
                h, v = x+dh, y+dv
                if 0 <= h < HatWidth and 0 <= v < HatHeight:
                    LED.setpixel(h, v, r, g, b)

def merge_particles():
    for i in range(particles.shape[0]):
        if not active_mask[i]: continue
        for j in range(i+1, particles.shape[0]):
            if not active_mask[j]: continue
            dx = particles[i,0] - particles[j,0]
            dy = particles[i,1] - particles[j,1]
            if math.hypot(dx,dy) < MergeDistance:
                mi, mj = particles[i,4], particles[j,4]
                mtot = mi + mj
                new_x = (particles[i,0]*mi + particles[j,0]*mj)/mtot
                new_y = (particles[i,1]*mi + particles[j,1]*mj)/mtot
                new_vx = (particles[i,2]*mi + particles[j,2]*mj)/mtot
                new_vy = (particles[i,3]*mi + particles[j,3]*mj)/mtot
                new_rgb = [int((particles[i,k] + particles[j,k])/2) for k in range(5,8)]
                slot = find_empty_slot(active_mask)
                if slot != -1:
                    particles[slot] = [new_x, new_y, new_vx, new_vy, mtot, *new_rgb, 3]
                    active_mask[slot] = True
                active_mask[i] = False
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

    update_particles(particles, active_mask, G, SunMass, TimeStep, MaxSpeed)
    merge_particles()
    draw_particles()
    LED.Canvas = LED.TheMatrix.SwapOnVSync(LED.Canvas)
    #time.sleep(ScrollSleep)
    frame += 1
