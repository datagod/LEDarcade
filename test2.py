import LEDarcade as LED
import random
import time
import math

LED.Initialize()

MAX_SPEED = 2.0
SHIP_THRUST = 0.1
MISSILE_SPEED = 1.0
MISSILE_LIFESPAN = 3.0
FIRE_CHANCE = 0.1
ASTEROID_SPLIT_THRESHOLD = 1
FRAME_DELAY = 0.03
ASTEROIDS = 3
WIDTH = LED.HatWidth
HEIGHT = LED.HatHeight

def handle_collisions(asteroids):
    for i in range(len(asteroids)):
        for j in range(i + 1, len(asteroids)):
            a1, a2 = asteroids[i], asteroids[j]
            dx = a2.x - a1.x
            dy = a2.y - a1.y
            dist_sq = dx * dx + dy * dy
            min_dist = a1.size + a2.size
            if dist_sq < min_dist * min_dist:
                dist = math.sqrt(dist_sq)
                if dist == 0:
                    continue
                nx, ny = dx / dist, dy / dist
                tx, ty = -ny, nx

                dpTan1 = a1.dx * tx + a1.dy * ty
                dpTan2 = a2.dx * tx + a2.dy * ty
                dpNorm1 = a1.dx * nx + a1.dy * ny
                dpNorm2 = a2.dx * nx + a2.dy * ny

                a1.dx = tx * dpTan1 + nx * dpNorm2
                a1.dy = ty * dpTan1 + ny * dpNorm2
                a2.dx = tx * dpTan2 + nx * dpNorm1
                a2.dy = ty * dpTan2 + ny * dpNorm1

                overlap = 0.5 * (min_dist - dist + 0.01)
                a1.x -= nx * overlap
                a1.y -= ny * overlap
                a2.x += nx * overlap
                a2.y += ny * overlap

class Asteroid:
    def __init__(self, x=None, y=None, size=None):
        self.x = x if x is not None else random.uniform(0, WIDTH)
        self.y = y if y is not None else random.uniform(0, HEIGHT)
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(0.1, 0.4)
        self.dx = math.cos(angle) * speed
        self.dy = math.sin(angle) * speed
        self.size = size if size is not None else random.choice([2, 3])
        gray = random.randint(30, 120)
        blue = random.randint(30, 100)
        purple = random.randint(30, 100)
        self.color = random.choice([
            (gray, gray, gray),
            (blue // 2, blue // 2, blue),
            (purple, 0, purple)
        ])

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
                        LED.setpixel(px, py, r, g, b)

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
        LED.setpixel(int(self.x), int(self.y), 255, 255, 255)

missile = None
asteroids = [Asteroid() for _ in range(ASTEROIDS)]
class Ship:
    def __init__(self):
        self.x = WIDTH // 2
        self.y = HEIGHT // 2
        self.angle = 0
        self.frame = 0
        self.color = (0, 255, 0)
        self.speed_x = 0
        self.speed_y = 0
        self.target = None

    def move(self):
        if not self.target or self.target not in asteroids:
            if asteroids:
                self.target = random.choice(asteroids)

        if self.target:
            dx = self.target.x - self.x
            dy = self.target.y - self.y
            desired_angle = math.atan2(dy, dx) + math.pi / 2  # orbiting angle
            angle_diff = (desired_angle - self.angle + math.pi) % (2 * math.pi) - math.pi
            self.angle += max(-0.3, min(0.3, angle_diff))

        ax = math.cos(self.angle) * SHIP_THRUST
        ay = math.sin(self.angle) * SHIP_THRUST
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
        if self.frame % 5 == 0:
            self.angle += random.uniform(-0.3, 0.3)
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
        LED.setpixel(cx, cy, r, g, b)
        LED.setpixel((cx + 1) % WIDTH, cy, r, g, b)
        LED.setpixel(cx, (cy + 1) % HEIGHT, r, g, b)

ship = Ship()

try:
    while True:
        LED.ClearBuffers()
        handle_collisions(asteroids)

        new_asteroids = []
        for asteroid in asteroids:
            asteroid.move()
            asteroid.draw()
            dx = ship.x - asteroid.x
            dy = ship.y - asteroid.y
            if dx * dx + dy * dy < asteroid.size * asteroid.size:
                angle = math.atan2(dy, dx)
                thrust = MAX_SPEED
                ship.speed_x = math.cos(angle + math.pi) * thrust
                ship.speed_y = math.sin(angle + math.pi) * thrust

        ship.move()
        ship.draw()

        if missile is None and random.random() < FIRE_CHANCE:
            missile = Missile(ship.x, ship.y, ship.angle)

        if missile:
            missile.move()
            missile.draw()
            if time.time() - missile.birth_time > MISSILE_LIFESPAN:
                missile = None
            else:
                hit_index = None
                for idx, asteroid in enumerate(asteroids):
                    dx = missile.x - asteroid.x
                    dy = missile.y - asteroid.y
                    if dx * dx + dy * dy < asteroid.size * asteroid.size:
                        hit_index = idx
                        break
                if hit_index is not None:
                    hit = asteroids.pop(hit_index)
                    if hit.size > 1:
                        new_asteroids.append(Asteroid(hit.x, hit.y, hit.size - 1))
                        new_asteroids.append(Asteroid(hit.x, hit.y, hit.size - 1))
                    missile = None
                elif not (0 <= missile.x < WIDTH and 0 <= missile.y < HEIGHT):
                    missile = None

        asteroids.extend(new_asteroids)

        LED.TheMatrix.SwapOnVSync(LED.Canvas)
        time.sleep(FRAME_DELAY)
except KeyboardInterrupt:
    LED.ClearBuffers()
    LED.TheMatrix.SwapOnVSync(LED.Canvas)
