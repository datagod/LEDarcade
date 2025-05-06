# GravitySim.py

import LEDarcade as LED
import math
import time
import random

# Configuration
NumParticles = 10
G = 1.0
SunMass = 500.0
TimeStep = 0.2
ScrollSleep = 0.01
MaxSpeed = 12.0
SpawnInterval = 50
MergeDistance = 1.5

HatWidth = LED.HatWidth
HatHeight = LED.HatHeight

SunX = HatWidth / 2
SunY = HatHeight / 2
SunRGB = LED.HighYellow
TrailFade = 15

class Particle:
    def __init__(self, x, y, vx, vy, mass, color):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.mass = mass
        self.color = color
        self.flash = 0

    def update(self, particles):
        dx = SunX - self.x
        dy = SunY - self.y
        dist_sq = dx * dx + dy * dy + 0.01
        dist = math.sqrt(dist_sq)
        force = G * SunMass / dist_sq
        ax = force * dx / dist
        ay = force * dy / dist

        for other in particles:
            if other is self:
                continue
            dx = other.x - self.x
            dy = other.y - self.y
            dist_sq = dx * dx + dy * dy + 0.01
            dist = math.sqrt(dist_sq)
            force = G * other.mass / dist_sq
            ax += force * dx / dist
            ay += force * dy / dist

        self.vx += ax * TimeStep
        self.vy += ay * TimeStep

        speed = math.sqrt(self.vx ** 2 + self.vy ** 2)
        if speed > MaxSpeed:
            scale = MaxSpeed / speed
            self.vx *= scale
            self.vy *= scale

        self.x += self.vx * TimeStep
        self.y += self.vy * TimeStep

        if self.flash > 0:
            self.flash -= 1

    def draw(self):
        h = int(round(self.x))
        v = int(round(self.y))
        if 0 <= h < HatWidth and 0 <= v < HatHeight:
            rgb = (255, 255, 255) if self.flash > 0 else self.color
            radius = min(2, max(1, int(self.mass / 3)))
            for dv in range(-radius + 1, radius):
                for dh in range(-radius + 1, radius):
                    nh, nv = h + dh, v + dv
                    if 0 <= nh < HatWidth and 0 <= nv < HatHeight:
                        LED.setpixel(nh, nv, *rgb)

particles = []

def spawn_orbiting_particle():
    angle = random.uniform(0, 2 * math.pi)
    radius = random.uniform(5, min(HatWidth, HatHeight) / 3)
    x = SunX + radius * math.cos(angle)
    y = SunY + radius * math.sin(angle)
    speed = math.sqrt(G * SunMass / radius)
    vx = -speed * math.sin(angle)
    vy = speed * math.cos(angle)
    mass = random.uniform(0.5, 2.0)
    color = (random.randint(50, 255), random.randint(50, 255), random.randint(50, 255))
    particles.append(Particle(x, y, vx, vy, mass, color))

for _ in range(NumParticles):
    spawn_orbiting_particle()

frame = 0
while True:
    for v in range(HatHeight):
        for h in range(HatWidth):
            r, g, b = LED.ScreenArray[v][h]
            r = max(0, r - TrailFade)
            g = max(0, g - TrailFade)
            b = max(0, b - TrailFade)
            LED.setpixel(h, v, r, g, b)

    LED.setpixel(int(SunX), int(SunY), *SunRGB)

    if frame % SpawnInterval == 0:
        edge = random.choice(['top', 'bottom', 'left', 'right'])
        if edge == 'top':
            x = random.uniform(0, HatWidth)
            y = 0
        elif edge == 'bottom':
            x = random.uniform(0, HatWidth)
            y = HatHeight
        elif edge == 'left':
            x = 0
            y = random.uniform(0, HatHeight)
        else:
            x = HatWidth
            y = random.uniform(0, HatHeight)

        dx = SunX - x
        dy = SunY - y
        dist = math.sqrt(dx ** 2 + dy ** 2)
        perp_angle = math.atan2(dy, dx) + math.pi / 2
        base_speed = random.uniform(3.0, 6.0)
        vx = math.cos(perp_angle) * base_speed
        vy = math.sin(perp_angle) * base_speed
        mass = random.uniform(0.5, 3.0)
        color = (random.randint(128, 255), random.randint(100, 255), random.randint(100, 255))
        particles.append(Particle(x, y, vx, vy, mass, color))

    new_particles = []
    to_remove = set()
    for i, p1 in enumerate(particles):
        if p1 in to_remove:
            continue
        for j, p2 in enumerate(particles):
            if i >= j or p2 in to_remove:
                continue
            dx = p1.x - p2.x
            dy = p1.y - p2.y
            if math.hypot(dx, dy) < MergeDistance:
                total_mass = p1.mass + p2.mass
                vx = (p1.vx * p1.mass + p2.vx * p2.mass) / total_mass
                vy = (p1.vy * p1.mass + p2.vy * p2.mass) / total_mass
                x = (p1.x * p1.mass + p2.x * p2.mass) / total_mass
                y = (p1.y * p1.mass + p2.y * p2.mass) / total_mass
                color = tuple(min(255, int((c1 + c2) / 2)) for c1, c2 in zip(p1.color, p2.color))
                merged = Particle(x, y, vx, vy, total_mass, color)
                merged.flash = 3
                new_particles.append(merged)
                to_remove.update([p1, p2])
                break

    particles = [p for p in particles if p not in to_remove] + new_particles

    for p in particles:
        p.update(particles)
        p.draw()

    LED.Canvas = LED.TheMatrix.SwapOnVSync(LED.Canvas)
    time.sleep(ScrollSleep)
    frame += 1
