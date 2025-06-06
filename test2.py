import LEDarcade as LED
import random
import time
import math
import pygame

LED.Initialize()


# --- Black Hole Parameters ---
BLACKHOLE_GRAVITY = 3
BLACKHOLE_MIN_SIZE = 1
BLACKHOLE_MAX_SIZE = 5
BLACKHOLE_MAX_SPEED = 2
BLACKHOLE_APPEAR_INTERVAL = 60
BLACKHOLE_LIFESPAN = 25






# --- Ship Parameters ---
MAX_SPEED = 0.5
SHIP_THRUST = 0.01
SHIP_COLOR = (0, 255, 0)
SHIP_THRUST_DURATION = 3.0
SHIP_THRUST_COOLDOWN = 1.0
THRUST_TRAIL_LENGTH = 8
SHIP_VISION_RADIUS = 20


# --- Missile Parameters ---
MISSILE_SPEED = 1
MISSILE_LIFESPAN = 0.50
FIRE_CHANCE = 0.1
MISSILE_COLOR = (255, 255, 255)
MISSILE_TRAIL_MIN = 50
MISSILE_TRAIL_LENGTH = 8
MAX_MISSILES = 4



# --- Asteroid Parameters ---
ASTEROID_SPLIT_THRESHOLD = 2
MAX_ASTEROID_SIZE = 4
FRAME_DELAY = 0.03
ASTEROIDS = 3
ASTEROID_MIN_SPEED = 0.05
ASTEROID_MAX_SPEED = 0.4
THRUST_TRAIL_COLOR = (255, 0, 0)
ASTEROID_TARGET_COLOR = (255, 255, 0)
ASTEROID_CROSSHAIR_COLOR = (255, 0, 255)
ASTEROID_LIGHTING_CONTRAST = 1
ASTEROID_COLOR_MIN_BRIGHTNESS = 150
ASTEROID_COLOR_MAX_BRIGHTNESS = 250
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

# --- Virtual Playfield Size ---
PLAYFIELD_WIDTH = 68
PLAYFIELD_HEIGHT = 40


# Center the visible matrix in the virtual playfield
VIEWPORT_X_OFFSET = (PLAYFIELD_WIDTH - WIDTH) // 2
VIEWPORT_Y_OFFSET = (PLAYFIELD_HEIGHT - HEIGHT) // 2





from numba import njit
import numpy as np






# Boundary Bounce Logic for Virtual Playfield
@njit
def enforce_bounds_and_bounce(x, y, dx, dy, width, height):
    if x < 0:
        x = 0
        dx = -dx
    elif x > width:
        x = width
        dx = -dx
    if y < 0:
        y = 0
        dy = -dy
    elif y > height:
        y = height
        dy = -dy
    return x, y, dx, dy



class GameObject:
    def __init__(self, x, y, dx, dy):
        self.x = x
        self.y = y
        self.dx = dx
        self.dy = dy

    def update_position(self):
        # Let subclasses define max speed if needed
        max_speed = getattr(self, 'max_speed', None)
        if max_speed is not None:
            speed = math.hypot(self.dx, self.dy)
            if speed > max_speed:
                scale = max_speed / speed
                self.dx *= scale
                self.dy *= scale
        self.x += self.dx
        self.y += self.dy
        self.x, self.y, self.dx, self.dy = enforce_bounds_and_bounce(
            self.x, self.y, self.dx, self.dy, PLAYFIELD_WIDTH, PLAYFIELD_HEIGHT
        )






class BlackHole(GameObject):
    def __init__(self, x, y, radius):
        self.x = x
        self.y = y
        self.radius = radius
        self.spawn_time = time.time()
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(0.05, 0.2)
        dx = math.cos(angle) * speed
        dy = math.sin(angle) * speed
        super().__init__(x, y, dx, dy)
        self.max_speed = BLACKHOLE_MAX_SPEED

    def move(self):
        self.update_position()  # from GameObject



    def expired(self):
        out_of_bounds = (
            self.x < -self.radius or self.x > PLAYFIELD_WIDTH + self.radius or
            self.y < -self.radius or self.y > PLAYFIELD_HEIGHT + self.radius
        )
        return out_of_bounds or (time.time() - self.spawn_time > BLACKHOLE_LIFESPAN)

    def draw(self):
        for dy in range(-self.radius, self.radius + 1):
            for dx in range(-self.radius, self.radius + 1):
                dist = math.sqrt(dx * dx + dy * dy)
                px = int(self.x + dx)
                py = int(self.y + dy)
                if (VIEWPORT_X_OFFSET <= px < VIEWPORT_X_OFFSET + WIDTH and
                    VIEWPORT_Y_OFFSET <= py < VIEWPORT_Y_OFFSET + HEIGHT):
                    if dist <= self.radius:
                        if dist >= self.radius - 1:
                            #LED.setpixel(px, py, 255, 255, 255)
                            LED.setpixel(px - VIEWPORT_X_OFFSET, py - VIEWPORT_Y_OFFSET, 255, 255, 255)
                        else:
                            #LED.setpixel(px, py, 0, 0, 0)
                            LED.setpixel(px - VIEWPORT_X_OFFSET, py - VIEWPORT_Y_OFFSET, 0, 0, 0)


# Attraction & Collision (apply per object)
def apply_blackhole_gravity(obj):
    if not blackhole:
        return
    dx = blackhole.x - obj.x
    dy = blackhole.y - obj.y
    dist_sq = dx * dx + dy * dy
    if dist_sq == 0:
        return
    dist = math.sqrt(dist_sq)
    force = BLACKHOLE_GRAVITY * blackhole.radius / dist_sq
    if hasattr(obj, 'dx') and hasattr(obj, 'dy'):
        obj.dx += force * dx / dist
        obj.dy += force * dy / dist
    elif hasattr(obj, 'speed_x') and hasattr(obj, 'speed_y'):
        obj.speed_x += force * dx / dist
        obj.speed_y += force * dy / dist
    if dist < blackhole.radius:
        if hasattr(obj, 'health'):
            obj.health = 0
        elif hasattr(obj, 'birth_time'):
            obj.birth_time = 0


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


class Asteroid(GameObject):
    def __init__(self, x=None, y=None, size=None, color=None):  # patched for GameObject
        x = x if x is not None else random.uniform(0, WIDTH)
        y = y if y is not None else random.uniform(0, HEIGHT)
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(ASTEROID_MIN_SPEED, ASTEROID_MAX_SPEED)
        dx = math.cos(angle) * speed
        dy = math.sin(angle) * speed
        super().__init__(x, y, dx, dy)
        self.max_speed = ASTEROID_MAX_SPEED
        self.target_size = size if size is not None else random.randint(2, MAX_ASTEROID_SIZE)
        self.size = 1
        self.grow_start_time = time.time()
        self.health = self.target_size * 2
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
        self.update_position()

    def draw(self):
        # Grow animation logic
        grow_duration = 0.5
        elapsed = time.time() - self.grow_start_time
        grow_factor = min(1.0, elapsed / grow_duration)
        current_size = max(1, int(self.target_size * grow_factor))
        self.size = current_size

        r, g, b = self.color
        for i in range(-self.size, self.size + 1):
            for j in range(-self.size, self.size + 1):
                if i**2 + j**2 <= self.size**2:
                    px = int(self.x) + i
                    py = int(self.y) + j
                    if (VIEWPORT_X_OFFSET <= px < VIEWPORT_X_OFFSET + WIDTH and
                        VIEWPORT_Y_OFFSET <= py < VIEWPORT_Y_OFFSET + HEIGHT):
                        brightness_factor = 1.0 - ASTEROID_LIGHTING_CONTRAST * (i + j) / (2 * self.size)
                        brightness_factor = max(0.5, min(1.5, brightness_factor))
                        r_out = min(255, int(r * brightness_factor))
                        g_out = min(255, int(g * brightness_factor))
                        b_out = min(255, int(b * brightness_factor))
                        LED.setpixel(px - VIEWPORT_X_OFFSET, py - VIEWPORT_Y_OFFSET, r_out, g_out, b_out)


class Missile(GameObject):
    def __init__(self, x, y, angle):
        self.birth_time = time.time()
        dx = math.cos(angle) * MISSILE_SPEED
        dy = math.sin(angle) * MISSILE_SPEED
        super().__init__(x, y, dx, dy)
        self.angle = angle
        self.speed = MISSILE_SPEED

    def move(self):
        self.x += self.dx
        self.y += self.dy
        

    def draw(self):
        for i in range(MISSILE_TRAIL_LENGTH):
            tx = int(self.x - math.cos(self.angle) * i)
            ty = int(self.y - math.sin(self.angle) * i)
            brightness = max(MISSILE_TRAIL_MIN, MISSILE_COLOR[0] - i * (MISSILE_COLOR[0] // MISSILE_TRAIL_LENGTH))
            #LED.setpixel(tx, ty, brightness, brightness, brightness)
            LED.setpixel(tx - VIEWPORT_X_OFFSET, ty - VIEWPORT_Y_OFFSET, brightness, brightness, brightness)


class Ship(GameObject):
    def __init__(self):
        super().__init__(PLAYFIELD_WIDTH // 2, PLAYFIELD_HEIGHT // 2, 0.0, 0.0)
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
            cx, cy = PLAYFIELD_WIDTH / 2, PLAYFIELD_HEIGHT / 2
            visible_targets = [a for a in asteroids if (a.x - cx)**2 + (a.y - cy)**2 <= SHIP_VISION_RADIUS**2]
            if visible_targets:
                self.target = random.choice(visible_targets)
            else:
                self.target = None
                dx = cx - self.x
                dy = cy - self.y
                angle_to_center = math.atan2(dy, dx)
                self.angle = angle_to_center
                ax = math.cos(self.angle) * SHIP_THRUST
                ay = math.sin(self.angle) * SHIP_THRUST
                self.speed_x += ax
                self.speed_y += ay



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


                # Clamp ship within visible area, leaving 1 pixel margin inside the visible playfield
                self.x = max(VIEWPORT_X_OFFSET + 2, min(self.x, VIEWPORT_X_OFFSET + WIDTH - 2))
                self.y = max(VIEWPORT_Y_OFFSET + 2, min(self.y, VIEWPORT_Y_OFFSET + HEIGHT - 2))



        speed = math.hypot(self.speed_x, self.speed_y)
        if speed > MAX_SPEED:
            scale = MAX_SPEED / speed
            self.speed_x *= scale
            self.speed_y *= scale
        self.x += self.speed_x
        self.y += self.speed_y
        if self.x < 0:
            self.x = 0
            self.speed_x *= -0.5
        elif self.x > PLAYFIELD_WIDTH:
            self.x = PLAYFIELD_WIDTH
            self.speed_x *= -0.5

        if self.y < 0:
            self.y = 0
            self.speed_y *= -0.5
        elif self.y > PLAYFIELD_HEIGHT:
            self.y = PLAYFIELD_HEIGHT
            self.speed_y *= -0.5
        self.frame += 1

    def draw(self):
        cx = int(self.x)
        cy = int(self.y)
        r, g, b = self.color
        if self.thrusting:
            current_thrust = math.hypot(self.speed_x, self.speed_y)
            trail_strength = int(min(current_thrust / MAX_SPEED, 1.0) * THRUST_TRAIL_LENGTH)
            for i in range(1, trail_strength + 1):
                tx = int(self.x - math.cos(self.angle) * i)
                ty = int(self.y - math.sin(self.angle) * i)
                red_intensity = max(0, THRUST_TRAIL_COLOR[0] - i * (THRUST_TRAIL_COLOR[0] // THRUST_TRAIL_LENGTH))
                #LED.setpixel(tx, ty, red_intensity, 0, 0)
                LED.setpixel(tx - VIEWPORT_X_OFFSET, ty - VIEWPORT_Y_OFFSET, red_intensity, 0, 0)
        #LED.setpixel(cx, cy, r, g, b)
        LED.setpixel(cx - VIEWPORT_X_OFFSET, cy - VIEWPORT_Y_OFFSET, r,g,b)
        
        dx = int(round(math.cos(self.angle)))
        dy = int(round(math.sin(self.angle)))
        #LED.setpixel((cx - dx) % WIDTH, (cy - dy) % HEIGHT, r, g, b)
        LED.setpixel(int(cx - dx - VIEWPORT_X_OFFSET), int(cy - dy - VIEWPORT_Y_OFFSET), r, g, b)






class Spark:
    def __init__(self, x, y, angle, speed):
        self.x = x
        self.y = y
        self.angle = angle
        self.speed = speed
        self.lifespan = SPARK_TRAIL_LENGTH

    def move(self):
        self.x += math.cos(self.angle) * self.speed
        self.y += math.sin(self.angle) * self.speed

    def draw(self):
        for i in range(SPARK_TRAIL_LENGTH):
            tx = int(self.x - math.cos(self.angle) * i)
            ty = int(self.y - math.sin(self.angle) * i)

            fade = max(0, SPARK_COLOR[0] - i * (SPARK_COLOR[0] // SPARK_TRAIL_LENGTH))
            #LED.setpixel(tx, ty, fade, fade * 3 // 4, fade // 2)
            LED.setpixel(tx - VIEWPORT_X_OFFSET, ty - VIEWPORT_Y_OFFSET, fade, fade * 3 // 4, fade // 2)
            








missiles = []
ship = Ship()
asteroids = [Asteroid() for _ in range(ASTEROIDS)]
sparks = []



clock = pygame.time.Clock()
fps_counter = 0
fps_timer = time.time()

# Insert into test2.py: Initialization Section
last_blackhole_time = time.time() - BLACKHOLE_APPEAR_INTERVAL
blackhole = None





try:
    while True:
        now = time.time()


        if now - last_blackhole_time > BLACKHOLE_APPEAR_INTERVAL:
            # Spawn just outside one of the four edges
            side = random.choice(['top', 'bottom', 'left', 'right'])
            if side == 'top':
                bx = random.randint(0, PLAYFIELD_WIDTH)
                by = -BLACKHOLE_MAX_SIZE
            elif side == 'bottom':
                bx = random.randint(0, PLAYFIELD_WIDTH)
                by = PLAYFIELD_HEIGHT + BLACKHOLE_MAX_SIZE
            elif side == 'left':
                bx = -BLACKHOLE_MAX_SIZE
                by = random.randint(0, PLAYFIELD_HEIGHT)
            else:
                bx = PLAYFIELD_WIDTH + BLACKHOLE_MAX_SIZE
                by = random.randint(0, PLAYFIELD_HEIGHT)
            bradius = random.randint(BLACKHOLE_MIN_SIZE, BLACKHOLE_MAX_SIZE)
            blackhole = BlackHole(bx, by, bradius)
            last_blackhole_time = now

        if blackhole and blackhole.expired():
            blackhole = None


        if not asteroids:
            asteroids.append(Asteroid(size=MAX_ASTEROID_SIZE))
        LED.ClearBuffers()
        handle_collisions(asteroids)

        if blackhole:
            blackhole.move()
            blackhole.draw()


        new_asteroids = []
        for asteroid in asteroids:
            apply_blackhole_gravity(asteroid)
            asteroid.move()
            asteroid.draw()
            if asteroid == ship.target:
                cx = int(asteroid.x)
                cy = int(asteroid.y)
                #LED.setpixel(cx, cy, ASTEROID_TARGET_COLOR[0], ASTEROID_TARGET_COLOR[1], ASTEROID_TARGET_COLOR[2])
                LED.setpixel(cx - VIEWPORT_X_OFFSET, cy - VIEWPORT_Y_OFFSET, ASTEROID_TARGET_COLOR[0], ASTEROID_TARGET_COLOR[1], ASTEROID_TARGET_COLOR[2])
                
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

        apply_blackhole_gravity(ship)
        ship.move()
        ship.draw()

        if len(missiles) < MAX_MISSILES and random.random() < FIRE_CHANCE and ship.target:
            missiles.append(Missile(ship.x, ship.y, ship.angle))

        for missile in missiles[:]:
            #apply_blackhole_gravity(missile)

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
            elif not (0 <= missile.x < PLAYFIELD_WIDTH and 0 <= missile.y < PLAYFIELD_HEIGHT):

                missiles.remove(missile)

        asteroids.extend(new_asteroids)



        for spark in sparks[:]:
            spark.move()
            spark.draw()
            spark.lifespan -= 1
            if spark.lifespan <= 0:
                sparks.remove(spark)

        
        
        # Draw visible boundary for the virtual playfield
        #for x in range(WIDTH):
        #    LED.setpixel(x, 0, 0, 0, 255)  # Top edge
        #    LED.setpixel(x, HEIGHT - 1, 0, 0, 255)  # Bottom edge
        #for y in range(HEIGHT):
        #    LED.setpixel(0, y, 0, 0, 255)  # Left edge
        #    LED.setpixel(WIDTH - 1, y, 0, 0, 255)  # Right edge

        
        LED.TheMatrix.SwapOnVSync(LED.Canvas)
        clock.tick(60)  # Cap the frame rate to 60 FPS
        fps_counter += 1
        if time.time() - fps_timer >= 2.0:
            asteroid_speeds = [math.hypot(a.dx, a.dy) for a in asteroids]
            avg_speed = sum(asteroid_speeds) / len(asteroid_speeds) if asteroid_speeds else 0
            print(f"FPS: {fps_counter / (time.time() - fps_timer):.2f} | Asteroids: {len(asteroids)} | Avg Asteroid Speed: {avg_speed:.3f}")
            fps_counter = 0
            fps_timer = time.time()

except KeyboardInterrupt:
    LED.ClearBuffers()
    LED.TheMatrix.SwapOnVSync(LED.Canvas)




















