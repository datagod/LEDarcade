# Add this to the bottom of gravitysim.py or integrate cleanly
import LEDarcade as LED
import numpy as np
import math
import random
import time

class Ship:
    def __init__(self):
        self.x = LED.HatWidth / 4
        self.y = LED.HatHeight / 2
        self.vx = 0.0
        self.vy = 1.0
        self.ax = 0.0
        self.ay = 0.0
        self.color = (255, 255, 255)
        self.offsets = [(0, 0), (1, 0), (0, 1)]  # 3-pixel shape
        self.thrust_cooldown = 0

    def apply_gravity(self):
        dx = SunX - self.x
        dy = SunY - self.y
        dist_sq = dx * dx + dy * dy + 0.01
        dist = math.sqrt(dist_sq)
        force = G * SunMass / dist_sq
        ax = force * dx / dist
        ay = force * dy / dist
        self.ax = ax
        self.ay = ay

    def apply_thrust(self):
        if self.thrust_cooldown > 0:
            self.thrust_cooldown -= 1
            return

        # Occasionally thrust away from the sun
        if random.random() < 0.05:
            dx = self.x - SunX
            dy = self.y - SunY
            dist = math.sqrt(dx**2 + dy**2)
            if dist > 0:
                thrust = 1.5
                self.vx += thrust * dx / dist
                self.vy += thrust * dy / dist
                self.thrust_cooldown = 20

    def update(self):
        self.apply_gravity()
        self.apply_thrust()

        self.vx += self.ax * TimeStep
        self.vy += self.ay * TimeStep

        speed = math.sqrt(self.vx**2 + self.vy**2)
        if speed > MaxSpeed:
            scale = MaxSpeed / speed
            self.vx *= scale
            self.vy *= scale

        self.x += self.vx * TimeStep
        self.y += self.vy * TimeStep

    def draw(self):
        for dx, dy in self.offsets:
            px = int(self.x) + dx
            py = int(self.y) + dy
            if 0 <= px < LED.HatWidth and 0 <= py < LED.HatHeight:
                LED.SetPixel(px, py, *self.color)


# Initialize ship
ship = Ship()

# Modify main loop to include the ship
frame = 0
while True:
    LED.ClearBuffers()

    update_particles(particles, active_mask, G, SunMass, TimeStep, MaxSpeed)

    for i in range(particles.shape[0]):
        if not active_mask[i]:
            continue
        x, y, r, g, b = particles[i,0], particles[i,1], int(particles[i,5]), int(particles[i,6]), int(particles[i,7])
        if 0 <= int(x) < LED.HatWidth and 0 <= int(y) < LED.HatHeight:
            LED.SetPixel(int(x), int(y), r, g, b)

    ship.update()
    ship.draw()

    LED.SetPixel(int(SunX), int(SunY), *SunRGB)
    LED.SwapBuffers()
    time.sleep(ScrollSleep)
    frame += 1

    if frame % SpawnInterval == 0:
        spawn_particle()
