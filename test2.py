import LEDarcade as LED
import random
import time
import math
import pygame

LED.Initialize()

# --- Ship Parameters ---
MAX_SPEED = 0.5
SHIP_THRUST = 0.01
SHIP_COLOR = (0, 255, 0)
SHIP_THRUST_DURATION = 3.0
SHIP_THRUST_COOLDOWN = 1.0
THRUST_TRAIL_LENGTH = 8


# --- Missile Parameters ---
MISSILE_SPEED = 1
MISSILE_LIFESPAN = 0.50
FIRE_CHANCE = 0.01
MISSILE_COLOR = (255, 255, 255)
MISSILE_TRAIL_MIN = 50
MISSILE_TRAIL_LENGTH = 8



# --- Asteroid Parameters ---
ASTEROID_SPLIT_THRESHOLD = 2
MAX_ASTEROID_SIZE = 4
MAX_MISSILES = 4
FRAME_DELAY = 0.03
ASTEROIDS = 2
ASTEROID_MIN_SPEED = 0.05
ASTEROID_MAX_SPEED = 0.5
THRUST_TRAIL_COLOR = (255, 0, 0)
ASTEROID_TARGET_COLOR = (255, 255, 0)
ASTEROID_CROSSHAIR_COLOR = (255, 0, 255)
ASTEROID_LIGHTING_CONTRAST = 1
ASTEROID_COLOR_MIN_BRIGHTNESS = 100
ASTEROID_COLOR_MAX_BRIGHTNESS = 255
ASTEROID_COLOR_OPTIONS = [
    (ASTEROID_COLOR_MIN_BRIGHTNESS, ASTEROID_COLOR_MIN_BRIGHTNESS, ASTEROID_COLOR_MIN_BRIGHTNESS),  # dark grey
    (ASTEROID_COLOR_MIN_BRIGHTNESS, ASTEROID_COLOR_MIN_BRIGHTNESS, ASTEROID_COLOR_MAX_BRIGHTNESS),  # deep blue
    (ASTEROID_COLOR_MAX_BRIGHTNESS, 0, ASTEROID_COLOR_MAX_BRIGHTNESS)  # deep purple
]


# --- Spark Effects ---
SPARK_COUNT = 10
SPARK_SPEED_MIN = 0.001
SPARK_SPEED_MAX = 0.2
SPARK_TRAIL_LENGTH = 8
SPARK_COLOR = (255, 200, 100)


# --- Display Settings ---
WIDTH = LED.HatWidth
HEIGHT = LED.HatHeight

from numba import njit
import numpy as np

@njit
def compute_collisions(positions, velocities, sizes):
    n = len(sizes)
    for i in range(n):
        for j in range(i + 1, n):
            dx = positions[j, 0] - positions[i, 0]
            dy = positions[j, 1] - positions[i, 1]
            dist_sq = dx * dx + dy * dy
            min_dist = sizes[i] + sizes[j]
            if dist_sq < min_dist * min_dist:
                dist = math.sqrt(dist_sq)
                if dist == 0:
                    continue
                nx, ny = dx / dist, dy / dist
                tx, ty = -ny, nx
                dpTan1 = velocities[i, 0] * tx + velocities[i, 1] * ty
                dpTan2 = velocities[j, 0] * tx + velocities[j, 1] * ty
                dpNorm1 = velocities[i, 0] * nx + velocities[i, 1] * ny
                dpNorm2 = velocities[j, 0] * nx + velocities[j, 1] * ny

                velocities[i, 0] = tx * dpTan1 + nx * dpNorm2
                velocities[i, 1] = ty * dpTan1 + ny * dpNorm2
                velocities[j, 0] = tx * dpTan2 + nx * dpNorm1
                velocities[j, 1] = ty * dpTan2 + ny * dpNorm1

                overlap = 0.5 * (min_dist - dist + 0.01)
                positions[i, 0] -= nx * overlap
                positions[i, 1] -= ny * overlap
                positions[j, 0] += nx * overlap
                positions[j, 1] += ny * overlap

def handle_collisions(asteroids):
    n = len(asteroids)
    positions = np.zeros((n, 2), dtype=np.float32)
    velocities = np.zeros((n, 2), dtype=np.float32)
    sizes = np.zeros(n, dtype=np.float32)

    for i, a in enumerate(asteroids):
        positions[i] = [a.x, a.y]
        velocities[i] = [a.dx, a.dy]
        sizes[i] = a.size

    compute_collisions(positions, velocities, sizes)

    for i, a in enumerate(asteroids):
        a.x, a.y = positions[i]
        a.dx, a.dy = velocities[i]

class Asteroid:
    def __init__(self, x=None, y=None, size=None, color=None):
        self.x = x if x is not None else random.uniform(0, WIDTH)
        self.y = y if y is not None else random.uniform(0, HEIGHT)
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(ASTEROID_MIN_SPEED, ASTEROID_MAX_SPEED)
        self.dx = math.cos(angle) * speed
        self.dy = math.sin(angle) * speed
        self.size = size if size is not None else random.randint(2, MAX_ASTEROID_SIZE)
        self.health = self.size * 2
        self.last_hit_time = 0
        if color:
            self.color = color
        else:
            roll = random.random()
            if roll < 0.9:
                self.color = ASTEROID_COLOR_OPTIONS[0]  # 90% grey
            elif roll < 0.95:
                self.color = ASTEROID_COLOR_OPTIONS[1]  # 5% blue
            else:
                self.color = ASTEROID_COLOR_OPTIONS[2]  # 5% purple

    def move(self):
        self.x = (self.x + self.dx) % WIDTH
        self.y = (self.y + self.dy) % HEIGHT

    def draw(self):
        r, g, b = self.color
        for i in range(-self.size, self.size + 1):
            for j in range(-self.size, self.size + 1):
                if i**2 + j**2 <= self.size**2:
                    px = int(self.x) + i
                    py = int(self.y) + j
                    if 0 <= px < WIDTH and 0 <= py < HEIGHT:
                        brightness_factor = 1.0 - ASTEROID_LIGHTING_CONTRAST * (i + j) / (2 * self.size)
                        brightness_factor = max(0.5, min(1.5, brightness_factor))
                        r_out = min(255, int(r * brightness_factor))
                        g_out = min(255, int(g * brightness_factor))
                        b_out = min(255, int(b * brightness_factor))
                        LED.setpixel(px, py, r_out, g_out, b_out)

class Missile:
    def __init__(self, x, y, angle):
        self.birth_time = time.time()
        self.x = x
        self.y = y
        self.angle = angle
        self.speed = MISSILE_SPEED

    def move(self):
        self.x = (self.x + math.cos(self.angle) * self.speed) % WIDTH
        self.y = (self.y + math.sin(self.angle) * self.speed) % HEIGHT

    def draw(self):
        for i in range(MISSILE_TRAIL_LENGTH):
            tx = int((self.x - math.cos(self.angle) * i) % WIDTH)
            ty = int((self.y - math.sin(self.angle) * i) % HEIGHT)
            brightness = max(MISSILE_TRAIL_MIN, MISSILE_COLOR[0] - i * (MISSILE_COLOR[0] // MISSILE_TRAIL_LENGTH))
            LED.setpixel(tx, ty, brightness, brightness, brightness)

missiles = []
asteroids = [Asteroid() for _ in range(ASTEROIDS)]
sparks = []
class Ship:
    def __init__(self):
        self.x = WIDTH // 2
        self.y = HEIGHT // 2
        self.angle = 0
        self.frame = 0
        self.color = SHIP_COLOR
        self.speed_x = 0
        self.speed_y = 0
        self.target = None
        self.last_thrust_time = 0
        self.thrusting = False

    def move(self):
        if not self.target or self.target not in asteroids:
            if asteroids:
                self.target = random.choice(asteroids)

        if self.target:
            current_time = time.time()
            if self.thrusting and current_time - self.last_thrust_time > SHIP_THRUST_DURATION:
                self.thrusting = False
                self.last_thrust_time = current_time
            elif not self.thrusting and current_time - self.last_thrust_time > SHIP_THRUST_COOLDOWN:
                self.thrusting = True
                self.last_thrust_time = current_time

            dx = self.target.x - self.x
            dy = self.target.y - self.y
            desired_angle = math.atan2(dy, dx)
            angle_diff = (desired_angle - self.angle + math.pi) % (2 * math.pi) - math.pi
            self.angle += max(-0.5, min(0.5, angle_diff))

            if self.thrusting:
                dx = self.target.x - self.x
                dy = self.target.y - self.y
                desired_angle = math.atan2(dy, dx)
                angle_diff = (desired_angle - self.angle + math.pi) % (2 * math.pi) - math.pi
                self.angle += max(-0.5, min(0.5, angle_diff))
                if abs(angle_diff) > math.pi / 2:
                    thrust = SHIP_THRUST * 4.0
                elif abs(angle_diff) > math.pi / 4:
                    thrust = SHIP_THRUST * 2.0
                else:
                    thrust = SHIP_THRUST

                ax = math.cos(self.angle) * thrust
                ay = math.sin(self.angle) * thrust
                self.speed_x += ax
                self.speed_y += ay
            

        
        speed = math.hypot(self.speed_x, self.speed_y)
        if speed > MAX_SPEED:
            scale = MAX_SPEED / speed
            self.speed_x *= scale
            self.speed_y *= scale
        self.x = (self.x + self.speed_x) % WIDTH
        self.y = (self.y + self.speed_y) % HEIGHT
        self.frame += 1

    def draw(self):
        cx = int(self.x)
        cy = int(self.y)
        r, g, b = self.color
        if self.thrusting:
            current_thrust = math.hypot(self.speed_x, self.speed_y)
            trail_strength = int(min(current_thrust / MAX_SPEED, 1.0) * THRUST_TRAIL_LENGTH)
            for i in range(1, trail_strength + 1):
                tx = int((self.x - math.cos(self.angle) * i) % WIDTH)
                ty = int((self.y - math.sin(self.angle) * i) % HEIGHT)
                red_intensity = max(0, THRUST_TRAIL_COLOR[0] - i * (THRUST_TRAIL_COLOR[0] // THRUST_TRAIL_LENGTH))
                LED.setpixel(tx, ty, red_intensity, 0, 0)
        LED.setpixel(cx, cy, r, g, b)
        dx = int(round(math.cos(self.angle)))
        dy = int(round(math.sin(self.angle)))
        #LED.setpixel((cx + dx) % WIDTH, (cy + dy) % HEIGHT, r, g, b)
        LED.setpixel((cx - dx) % WIDTH, (cy - dy) % HEIGHT, r, g, b)

ship = Ship()

class Spark:
    def __init__(self, x, y, angle, speed):
        self.x = x
        self.y = y
        self.angle = angle
        self.speed = speed
        self.lifespan = SPARK_TRAIL_LENGTH

    def move(self):
        self.x = (self.x + math.cos(self.angle) * self.speed) % WIDTH
        self.y = (self.y + math.sin(self.angle) * self.speed) % HEIGHT

    def draw(self):
        for i in range(SPARK_TRAIL_LENGTH):
            tx = int((self.x - math.cos(self.angle) * i) % WIDTH)
            ty = int((self.y - math.sin(self.angle) * i) % HEIGHT)
            fade = max(0, SPARK_COLOR[0] - i * (SPARK_COLOR[0] // SPARK_TRAIL_LENGTH))
            LED.setpixel(tx, ty, fade, fade * 3 // 4, fade // 2)

clock = pygame.time.Clock()
fps_counter = 0
fps_timer = time.time()

try:
    while True:
        if not asteroids:
            asteroids.append(Asteroid(size=MAX_ASTEROID_SIZE))
        LED.ClearBuffers()
        handle_collisions(asteroids)

        new_asteroids = []
        for asteroid in asteroids:
            asteroid.move()
            asteroid.draw()
            if asteroid == ship.target:
                cx = int(asteroid.x)
                cy = int(asteroid.y)
                LED.setpixel(cx, cy, ASTEROID_TARGET_COLOR[0], ASTEROID_TARGET_COLOR[1], ASTEROID_TARGET_COLOR[2])
            dx = ship.x - asteroid.x
            dy = ship.y - asteroid.y
            if dx * dx + dy * dy < asteroid.size * asteroid.size:
                if time.time() - asteroid.last_hit_time > 1.0:
                    asteroid.health -= 1
                    asteroid.last_hit_time = time.time()
                if asteroid.health <= 0:
                    if asteroid.size > 1:
                        new_asteroids.append(Asteroid(asteroid.x, asteroid.y, asteroid.size - 1, color=asteroid.color))
                        new_asteroids.append(Asteroid(asteroid.x, asteroid.y, asteroid.size - 1))
                    for _ in range(SPARK_COUNT):
                        angle = random.uniform(0, 2 * math.pi)
                        speed = random.uniform(SPARK_SPEED_MIN, SPARK_SPEED_MAX)
                        sparks.append(Spark(asteroid.x, asteroid.y, angle, speed))
                    continue
                angle = math.atan2(dy, dx)
                thrust = MAX_SPEED
                ship.speed_x = math.cos(angle + math.pi) * thrust
                ship.speed_y = math.sin(angle + math.pi) * thrust

        ship.move()
        ship.draw()

        if len(missiles) < MAX_MISSILES and random.random() < FIRE_CHANCE and ship.target:
            missiles.append(Missile(ship.x, ship.y, ship.angle))

        for missile in missiles[:]:
            missile.move()
            missile.draw()
            if time.time() - missile.birth_time > MISSILE_LIFESPAN:
                missiles.remove(missile)
                continue
            hit_index = None
            for idx, asteroid in enumerate(asteroids):
                dx = missile.x - asteroid.x
                dy = missile.y - asteroid.y
                if dx * dx + dy * dy < asteroid.size * asteroid.size:
                    hit_index = idx
                    break
            if hit_index is not None:
                hit = asteroids.pop(hit_index)
                spark_origin_x = hit.x
                spark_origin_y = hit.y
                if hit.size > 1:
                    new_asteroids.append(Asteroid(hit.x, hit.y, hit.size - 1, color=hit.color))
                    new_asteroids.append(Asteroid(hit.x, hit.y, hit.size - 1))
                missiles.remove(missile)
                for _ in range(SPARK_COUNT):
                    angle = random.uniform(0, 2 * math.pi)
                    speed = random.uniform(SPARK_SPEED_MIN, SPARK_SPEED_MAX)
                    sparks.append(Spark(spark_origin_x, spark_origin_y, angle, speed))
            elif not (0 <= missile.x < WIDTH and 0 <= missile.y < HEIGHT):
                missiles.remove(missile)

        asteroids.extend(new_asteroids)

        for spark in sparks[:]:
            spark.move()
            spark.draw()
            spark.lifespan -= 1
            if spark.lifespan <= 0:
                sparks.remove(spark)

        LED.TheMatrix.SwapOnVSync(LED.Canvas)
        clock.tick(60)  # Cap the frame rate to 60 FPS
        fps_counter += 1
        if time.time() - fps_timer >= 2.0:
            print(f"FPS: {fps_counter / (time.time() - fps_timer):.2f}")
            fps_counter = 0
            fps_timer = time.time()
        import pygame

except KeyboardInterrupt:
    LED.ClearBuffers()
    LED.TheMatrix.SwapOnVSync(LED.Canvas)
