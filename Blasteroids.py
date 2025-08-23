# =====================================================================================
# LED ASTEROID FIELD SIMULATION — With Ship AI, Missiles, Sparks, and Black Hole Logic
#
# Author       : William McEvoy 
# Framework    : LEDarcade (custom game and display framework for LED matrices)
# Hardware     : Raspberry Pi w/ Adafruit or compatible RGB LED Matrix (e.g. 64x32)
# Dependencies : pygame, numpy, numba, LEDarcade (custom), Pillow (for fonts/images)
#
# Description  :
# This is a real-time arcade-style simulation rendered on an LED matrix display. The
# game features autonomous AI ship navigation, dynamic asteroid fields, projectile
# tracking (missiles), particle effects (sparks), and gravitational anomalies (black
# holes). Entities interact with physics-inspired behaviors including momentum, elastic
# collisions, gravity fields, and boundary reflection.
#
# The engine runs on a virtual playfield larger than the visible LED matrix, allowing
# for a scrolling effect and spatial simulation beyond the constrained screen size.
#
# Core Features:
#  - Autonomous AI-controlled ship with vision-based targeting and thrust behavior
#  - Asteroid spawning, health, splitting, and collision physics (elastic, resolved)
#  - Black holes that attract nearby objects and destroy on proximity/contact
#  - Missile launching with limited lifespan and projectile targeting
#  - Real-time particle system for visual effects (sparks on impact/destruction)
#  - LED-safe rendering pipeline using off-screen buffers and VSync frame swapping
#  - Numba-accelerated collision physics for performance on embedded hardware
#  - FPS tracking and average asteroid speed diagnostics
#
# Architectural Notes:
#  - GameObject is the parent class for all moving entities (Ship, Asteroids, Missiles)
#  - All rendering is done via LED.setpixelCanvas() into the back buffer, followed by
#    SwapOnVSync() to commit the frame
#  - A viewport window into the larger virtual space is centered around the display
#  - Ship behavior uses angular targeting and thrust arcs to avoid jittery movement
#  - `@njit` is used where high-frequency numeric operations are required (Numba)
#
# Known Limitations / To-Do:
#  - No player input; all gameplay is autonomous (demo-style)
#  - Ship has no health system (can’t be destroyed)
#  - No high score tracking or persistent state
#
# Version      : 1.0.0
# License      : Non-commercial use only. Contact william.mcevoy@gmail.com for licensing.
#
# =====================================================================================


import LEDarcade as LED
import random
import time
import math
import pygame
from datetime import datetime





# --- Black Hole Parameters ---
BLACKHOLE_GRAVITY  = 6
BLACKHOLE_MIN_SIZE = 1
BLACKHOLE_MAX_SIZE = 15
BLACKHOLE_MAX_SPEED = 2
BLACKHOLE_APPEAR_INTERVAL = 120
BLACKHOLE_LIFESPAN = 30
BLACKHOLE_GROW_DURATION = 2


# --- Ship Parameters ---
MAX_SPEED      = 0.4
SHIP_THRUST    = 0.006
SHIP_TURN_RATE = 0.3
SHIP_COLOR     = (0, 155, 255)
SHIP_THRUST_DURATION = 3.0
SHIP_THRUST_COOLDOWN = 0.5
THRUST_TRAIL_LENGTH  = 6
SHIP_VISION_RADIUS   = 30


# --- Missile Parameters ---
MISSILE_SPEED         = 1.25
MISSILE_LIFESPAN      = 0.75
MISSILE_GRAVITY_FORCE = 0.1
FIRE_CHANCE   = 0.1
MISSILE_COLOR = (255, 255, 255)
MISSILE_TRAIL_MIN_BRIGHTNESS = 10
MISSILE_TRAIL_LENGTH         = 8
MAX_MISSILES                 = 1

# --- Terminal Parameters ---
ScrollSleep         = 0.025
MainSleep           = 0.05
TerminalTypeSpeed   = 0.02  #pause in seconds between characters
TerminalScrollSpeed = 0.02  #pause in seconds between new lines
CursorRGB           = (0,255,0)
CursorDarkRGB       = (0,50,0)


# --- Asteroid Parameters ---
ASTEROIDS = 2
ASTEROIDS_MERGE_CHANCE = 0.75
MAX_ASTEROID_SIZE = 15
MIN_ASTEROID_SIZE = 2
ASTEROID_GROWTH_DURATION = 0.25
FRAME_DELAY = 0.03
ASTEROID_MIN_SPEED = 0.05
ASTEROID_MAX_SPEED = 0.4
THRUST_TRAIL_COLOR = (255, 0, 0)
ASTEROID_TARGET_COLOR = (255, 255, 0)
ASTEROID_CROSSHAIR_COLOR = (255, 0, 255)
ASTEROID_LIGHTING_CONTRAST = 1
ASTEROID_COLOR_MIN_BRIGHTNESS = 100
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
SPARK_TRAIL_LENGTH = 6
SPARK_TRAIL_MAX_LENGTH = 8 #length gets modified by size of objects exploding, this clamps it
SPARK_COLOR = (255, 200, 100)



# --- Display Settings ---
WIDTH            = LED.HatWidth
HEIGHT           = LED.HatHeight
SCROLL_FONT_SIZE = 12

# --- Virtual Playfield Size ---
PLAYFIELD_WIDTH = 78
PLAYFIELD_HEIGHT = 50


# Center the visible matrix in the virtual playfield
VIEWPORT_X_OFFSET = (PLAYFIELD_WIDTH - WIDTH) // 2
VIEWPORT_Y_OFFSET = (PLAYFIELD_HEIGHT - HEIGHT) // 2







# At the top of PlayBlasteroids, ensure b
global blackhole
blackhole = None  # Initialize explicitly


#Time date
last_time_str = ""
ClockFontSize = 12
ClockRGB = (0,200,0)

clock_img = LED.GenerateClockImageWithFixedTiles(FontSize=ClockFontSize, TextColor=ClockRGB, BackgroundColor=(0, 0, 0))




from numba import njit
import numpy as np



from PIL import Image

def draw_clock_overlay(clock_image):
    img_w, img_h = clock_image.size
    H = (WIDTH  - img_w) // 2
    V = (HEIGHT - img_h) // 2

    if not blackhole:
        # Just draw centered
        for y in range(img_h):
            for x in range(img_w):
                r, g, b = clock_image.getpixel((x, y))
                if (r, g, b) != (0, 0, 0):
                    px = H + x
                    py = V + y
                    if 0 <= px < WIDTH and 0 <= py < HEIGHT:
                        LED.setpixelCanvas(px, py, r, g, b)
        return

    # Create a new blank image the same size as the LED matrix
    stretched = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))

    bhx = blackhole.x - VIEWPORT_X_OFFSET
    bhy = blackhole.y - VIEWPORT_Y_OFFSET
    

    # Paste original clock centered into LED-space image
    stretched.paste(clock_image, (H, V))

    # Warp pixels outward toward black hole
    source = np.array(stretched)
    target = np.zeros_like(source)

    for y in range(HEIGHT):
        for x in range(WIDTH):
            dx = bhx - x
            dy = bhy - y
            dist_sq = dx * dx + dy * dy
            if dist_sq == 0:
                src_x, src_y = x, y
            else:
                force = BLACKHOLE_GRAVITY * 2 * blackhole.radius / dist_sq
                src_x = int(x - dx * force)
                src_y = int(y - dy * force)

            if 0 <= src_x < WIDTH and 0 <= src_y < HEIGHT:
                target[y, x] = source[src_y, src_x]

    # Draw final warped image
    for y in range(HEIGHT):
        for x in range(WIDTH):
            r, g, b = target[y, x]
            if (r, g, b) != (0, 0, 0):
                LED.setpixelCanvas(x, y+1, r, g, b)



def draw_clock_overlay_old(clock_image):
    """
    Draws the clock image centered on the LED display.

    Parameters:
        clock_image (PIL.Image): The clock image to draw.
    """
    pixels = clock_image.load()
    img_w, img_h = clock_image.size

    # Compute top-left offset to center the image
    H = (WIDTH  - img_w) // 2
    V = (HEIGHT - img_h) // 2

    for y in range(img_h):
        for x in range(img_w):
            r, g, b = pixels[x, y]
            px = H + x
            py = V + y
            if 0 <= px < WIDTH and 0 <= py < HEIGHT:
                if (r, g, b) != (0, 0, 0):
                    # Offset by 1 to nudge the clock down slightly for visual centering
                    LED.setpixelCanvas(px, py +1, r, g, b)
                    









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
            # Allow higher speed if near a black hole
            if blackhole and isinstance(self, Asteroid):
                dist_sq = (self.x - blackhole.x)**2 + (self.y - blackhole.y)**2
                if dist_sq < 100:  # Within 10 units of black hole
                    max_speed *= 2  # Double max speed to allow gravity to have more impact
            if speed > max_speed:
                scale = max_speed / speed
                self.dx *= scale
                self.dy *= scale
        self.x += self.dx
        self.y += self.dy
        self.x, self.y, self.dx, self.dy = enforce_bounds_and_bounce(
            self.x, self.y, self.dx, self.dy, PLAYFIELD_WIDTH, PLAYFIELD_HEIGHT
        )


    def update_position_old(self):
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
    def __init__(self, x, y, radius,size=1):
        self.x = x
        self.y = y
        self.spawn_time = time.time()
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(0.05, 0.2)
        dx = math.cos(angle) * speed
        dy = math.sin(angle) * speed
        super().__init__(x, y, dx, dy)
        self.size = 1
        self.max_speed = BLACKHOLE_MAX_SPEED
        self.growing = True
        self.grow_start_time = time.time()

        self.target_size = radius  # unify
        self.radius = 1  # will grow from 1 to target



    def move(self):
        self.update_position()  # from GameObject



    def expired(self):
        out_of_bounds = (
            self.x < -self.radius or self.x > PLAYFIELD_WIDTH + self.radius or
            self.y < -self.radius or self.y > PLAYFIELD_HEIGHT + self.radius
        )
        return out_of_bounds or (time.time() - self.spawn_time > BLACKHOLE_LIFESPAN)


    def draw(self):
        grow_duration = BLACKHOLE_GROW_DURATION
        elapsed = time.time() - self.grow_start_time

        if self.growing:
            grow_factor = elapsed / grow_duration
            if elapsed >= grow_duration:
                self.size = self.target_size
                self.growing = False
            else:
                self.size = max(1, int(round(self.target_size * grow_factor)))
        else:
            self.size = self.target_size

        self.radius = self.size  # Update radius used for interaction

        for dy in range(-self.radius, self.radius + 1):
            for dx in range(-self.radius, self.radius + 1):
                px = int(self.x + dx)
                py = int(self.y + dy)
                if (VIEWPORT_X_OFFSET <= px < VIEWPORT_X_OFFSET + WIDTH and
                    VIEWPORT_Y_OFFSET <= py < VIEWPORT_Y_OFFSET + HEIGHT):

                    dist = math.hypot(dx, dy)
                    # Fill everything within the radius — outer ring white, inner black
                    if dist <= self.radius:
                        if dist >= self.radius - 1:
                            LED.setpixelCanvas(px - VIEWPORT_X_OFFSET, py - VIEWPORT_Y_OFFSET, 255, 255, 255)
                        else:
                            LED.setpixelCanvas(px - VIEWPORT_X_OFFSET, py - VIEWPORT_Y_OFFSET, 1, 1, 1)


# Attraction & Collision (apply per object)
def apply_blackhole_gravity(obj, asteroids_list=None):
    global sparks
    if not blackhole:
        return
    dx = blackhole.x - obj.x
    dy = blackhole.y - obj.y
    dist_sq = dx * dx + dy * dy
    if dist_sq == 0:
        return
    dist = math.sqrt(dist_sq)
    # Calculate effective radii (radius = 2 * size)
    obj_radius = obj.size * 2 if hasattr(obj, 'size') else 0
    blackhole_diameter = blackhole.radius * 2

    
    # If asteroid collides with Blackhole, it is destroyed
    if dist <= ((obj_radius + blackhole_diameter) / 3) and isinstance(obj, Asteroid) and asteroids_list is not None:
        for _ in range(1,20):
          angle = random.uniform(0, 2 * math.pi)
          speed = random.uniform(SPARK_SPEED_MIN, SPARK_SPEED_MAX * 2)
          sparks.append(Spark(obj.x, obj.y, angle, speed,int(obj.size * 2)))

        asteroids_list.remove(obj)  # Remove asteroid on collision
        return



    # Apply gravity if no collision
    force = BLACKHOLE_GRAVITY * blackhole.radius / dist_sq


    # Scale it down for missiles
    if isinstance(obj, Missile):
        force *= MISSILE_GRAVITY_FORCE

    if hasattr(obj, 'dx') and hasattr(obj, 'dy'):
        obj.dx += force * dx / dist
        obj.dy += force * dy / dist
    elif hasattr(obj, 'speed_x') and hasattr(obj, 'speed_y'):
        obj.speed_x += force * dx / dist
        obj.speed_y += force * dy / dist



@njit
def compute_collisions(positions, velocities, sizes):
    collision_scale = 0.5
    n = len(sizes)
    for i in range(n):
        for j in range(i + 1, n):
            dx = positions[j, 0] - positions[i, 0]
            dy = positions[j, 1] - positions[i, 1]
            dist_sq = dx * dx + dy * dy
            min_dist = (sizes[i] + sizes[j]) * collision_scale
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
    merged_indices = set()
    new_asteroids = []

    for i in range(len(asteroids)):
        if i in merged_indices:
            continue
        a1 = asteroids[i]
        for j in range(i + 1, len(asteroids)):
            if j in merged_indices:
                continue
            a2 = asteroids[j]

            if hasattr(a1, 'born_time') and hasattr(a2, 'born_time'):
                if time.time() - a1.born_time < 0.5 or time.time() - a2.born_time < 0.5:
                    continue  # Skip merging newly spawned asteroids

            dx = a2.x - a1.x
            dy = a2.y - a1.y
            dist_sq = dx * dx + dy * dy
            min_dist = (a1.size + a2.size) * 0.5
            if dist_sq < min_dist * min_dist:
                if random.random() < ASTEROIDS_MERGE_CHANCE:
                    total_mass = a1.size + a2.size
                    new_x = (a1.x * a1.size + a2.x * a2.size) / total_mass
                    new_y = (a1.y * a1.size + a2.y * a2.size) / total_mass
                    new_dx = (a1.dx * a1.size + a2.dx * a2.size) / total_mass
                    new_dy = (a1.dy * a1.size + a2.dy * a2.size) / total_mass
                    new_size = min(MAX_ASTEROID_SIZE, total_mass)
                    new_color = a1.color if random.random() < 0.5 else a2.color

                    #new_asteroids.append(Asteroid(new_x, new_y, size=new_size, color=new_color))
                    new_a = Asteroid(new_x, new_y, size=new_size, color=new_color)
                    new_a.growing = False
                    new_a.size = new_a.target_size
                    new_asteroids.append(new_a)



                    merged_indices.update([i, j])
                else:
                    # Fallback to bounce
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

    # Remove merged ones and add new ones
    asteroids[:] = [a for idx, a in enumerate(asteroids) if idx not in merged_indices]
    asteroids.extend(new_asteroids)




def handle_collisions_old(asteroids):
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




import random
import math
import time

# Assuming these constants are defined elsewhere
# WIDTH, HEIGHT, VIEWPORT_X_OFFSET, VIEWPORT_Y_OFFSET, ASTEROID_MIN_SPEED, 
# ASTEROID_MAX_SPEED, MAX_ASTEROID_SIZE, ASTEROID_COLOR_OPTIONS, 
# ASTEROID_LIGHTING_CONTRAST, LED, GameObject

class Asteroid(GameObject):
    def __init__(self, x=None, y=None, size=None, color=None):
        x = x if x is not None else random.uniform(0, WIDTH)
        y = y if y is not None else random.uniform(0, HEIGHT)
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(ASTEROID_MIN_SPEED, ASTEROID_MAX_SPEED)
        dx = math.cos(angle) * speed
        dy = math.sin(angle) * speed
        super().__init__(x, y, dx, dy)
        self.max_speed = ASTEROID_MAX_SPEED
        #self.target_size = size if size is not None else random.randint(2, MAX_ASTEROID_SIZE)
        self.target_size = size if size is not None else random.randint(MIN_ASTEROID_SIZE, MAX_ASTEROID_SIZE)
        self.size = 1  # Start small
        self.growing = True
        self.grow_start_time = time.time()
        self.health = self.target_size * 2
        self.last_hit_time = 0
        self.alive = True
        self.born_time = time.time()

        if color:
            self.color = color
        else:
            roll = random.random()
            if roll < 0.9:
                self.color = ASTEROID_COLOR_OPTIONS[0]
            elif roll < 0.95:
                self.color = ASTEROID_COLOR_OPTIONS[1]
            else:
                self.color = ASTEROID_COLOR_OPTIONS[2]
        
        # Generate lumps for lumpy shape
        self.lumps = []
        number_of_lumps = random.randint(3, 6)
        for _ in range(number_of_lumps):
            angle = random.uniform(0, 2 * math.pi)
            distance_frac = random.uniform(0, 0.5)
            lump_radius_frac = random.uniform(0.2, 0.5)
            frac_dx = math.cos(angle) * distance_frac
            frac_dy = math.sin(angle) * distance_frac
            self.lumps.append((frac_dx, frac_dy, lump_radius_frac))

    @classmethod
    def create(cls, **kwargs):
        asteroid = cls(**kwargs)
        asteroid.growing = True
        asteroid.grow_start_time = time.time()
        asteroid.size = 1
        return asteroid

    def move(self):
        self.update_position()

    def draw(self):
        if not hasattr(self, "_debug_draw_count"):
            self._debug_draw_count = 0
        self._debug_draw_count += 1
        
        # Handle growth
        if self.growing:
            grow_duration = ASTEROID_GROWTH_DURATION
            elapsed = time.time() - self.grow_start_time
            if elapsed >= grow_duration:
                self.size = self.target_size
                self.growing = False
            else:
                grow_factor = elapsed / grow_duration
                self.size = max(1, int(self.target_size * grow_factor))
        
        # Define bounding box, slightly larger to account for protruding lumps
        bounding_size = int(self.size * 1.2)
        for i in range(-bounding_size, bounding_size + 1):
            for j in range(-bounding_size, bounding_size + 1):
                max_depth = -1
                selected_lump = None
                # Check each lump
                for lump in self.lumps:
                    frac_dx, frac_dy, frac_r = lump
                    effective_dx = frac_dx * self.size
                    effective_dy = frac_dy * self.size
                    effective_radius = frac_r * self.size
                    distance = math.sqrt((i - effective_dx)**2 + (j - effective_dy)**2)
                    if distance < effective_radius:
                        depth = effective_radius - distance
                        if depth > max_depth:
                            max_depth = depth
                            selected_lump = lump
                if selected_lump:
                    # Calculate shading using the selected lump
                    frac_dx, frac_dy, frac_r = selected_lump
                    effective_dx = frac_dx * self.size
                    effective_dy = frac_dy * self.size
                    effective_radius = frac_r * self.size
                    rel_i = i - effective_dx
                    rel_j = j - effective_dy
                    brightness_factor = 1.0 - ASTEROID_LIGHTING_CONTRAST * (rel_i + rel_j) / (2 * effective_radius)
                    brightness_factor = max(0.5, min(1.5, brightness_factor))
                    r, g, b = self.color
                    r_out = min(255, int(r * brightness_factor))
                    g_out = min(255, int(g * brightness_factor))
                    b_out = min(255, int(b * brightness_factor))
                    px = int(self.x) + i
                    py = int(self.y) + j
                    if (VIEWPORT_X_OFFSET <= px < VIEWPORT_X_OFFSET + WIDTH and
                        VIEWPORT_Y_OFFSET <= py < VIEWPORT_Y_OFFSET + HEIGHT):
                        LED.setpixelCanvas(px - VIEWPORT_X_OFFSET, py - VIEWPORT_Y_OFFSET, r_out, g_out, b_out)






class Asteroid_old(GameObject):
    def __init__(self, x=None, y=None, size=None, color=None):
        x = x if x is not None else random.uniform(0, WIDTH)
        y = y if y is not None else random.uniform(0, HEIGHT)
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(ASTEROID_MIN_SPEED, ASTEROID_MAX_SPEED)
        dx = math.cos(angle) * speed
        dy = math.sin(angle) * speed
        super().__init__(x, y, dx, dy)
        self.max_speed = ASTEROID_MAX_SPEED
        self.target_size = size if size is not None else random.randint(2, MAX_ASTEROID_SIZE)
        self.size = 1  # Start small
        self.growing = True
        self.grow_start_time = time.time()
        self.health = self.target_size * 2
        self.last_hit_time = 0
        self.alive = True
        if color:
            self.color = color
        else:
            roll = random.random()
            if roll < 0.9:
                self.color = ASTEROID_COLOR_OPTIONS[0]
            elif roll < 0.95:
                self.color = ASTEROID_COLOR_OPTIONS[1]
            else:
                self.color = ASTEROID_COLOR_OPTIONS[2]

    @classmethod
    def create(cls, **kwargs):
        asteroid = cls(**kwargs)
        asteroid.growing = True
        asteroid.grow_start_time = time.time()
        asteroid.size = 1
        return asteroid


    def move(self):
        self.update_position()

    
    
    
    def draw(self):
      if not hasattr(self, "_debug_draw_count"):
          self._debug_draw_count = 0
      self._debug_draw_count += 1


      if self.growing:
        grow_duration = ASTEROID_GROWTH_DURATION
        elapsed = time.time() - self.grow_start_time
        grow_factor = elapsed / grow_duration
        if elapsed >= grow_duration:
            self.size = self.target_size
            self.growing = False
        else:
            self.size = max(1, int(self.target_size * grow_factor))


        if grow_factor >= 1.0:
            self.growing = False
      else:
        self.size = self.target_size

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
                    LED.setpixelCanvas(px - VIEWPORT_X_OFFSET, py - VIEWPORT_Y_OFFSET, r_out, g_out, b_out)


class Missile(GameObject):
    def __init__(self, x, y, angle):
        self.birth_time = time.time()
        dx = math.cos(angle) * MISSILE_SPEED
        dy = math.sin(angle) * MISSILE_SPEED
        super().__init__(x, y, dx, dy)
        self.angle = angle
        self.speed = MISSILE_SPEED
        self.trail = [(x, y)]  # Initialize trail with current position

    def move(self):
        self.x += self.dx
        self.y += self.dy
        # Append current position to trail
        self.trail.append((self.x, self.y))
        # Keep trail length within MISSILE_TRAIL_LENGTH
        if len(self.trail) > MISSILE_TRAIL_LENGTH:
            self.trail.pop(0)

    def draw(self):
        # Draw the missile head
        tx = int(self.x)
        ty = int(self.y)
        if (VIEWPORT_X_OFFSET <= tx < VIEWPORT_X_OFFSET + WIDTH and
            VIEWPORT_Y_OFFSET <= ty < VIEWPORT_Y_OFFSET + HEIGHT):
            LED.setpixelCanvas(tx - VIEWPORT_X_OFFSET, ty - VIEWPORT_Y_OFFSET, *MISSILE_COLOR)
        # Draw the trail using stored positions
        for i, (tx, ty) in enumerate(self.trail):
            tx, ty = int(tx), int(ty)
            if (VIEWPORT_X_OFFSET <= tx < VIEWPORT_X_OFFSET + WIDTH and
                VIEWPORT_Y_OFFSET <= ty < VIEWPORT_Y_OFFSET + HEIGHT):
                # Fade brightness based on trail position (oldest points dimmer)
                #brightness = max(MISSILE_TRAIL_MIN, MISSILE_COLOR[0] - i * (MISSILE_COLOR[0] // MISSILE_TRAIL_LENGTH))

                brightness = max(
                    MISSILE_TRAIL_MIN_BRIGHTNESS,
                    MISSILE_COLOR[0] - (MISSILE_TRAIL_LENGTH - i - 1) * (MISSILE_COLOR[0] // MISSILE_TRAIL_LENGTH)
                )


                LED.setpixelCanvas(tx - VIEWPORT_X_OFFSET, ty - VIEWPORT_Y_OFFSET, brightness, brightness, brightness)


# [Previous imports, constants, and other classes remain unchanged]

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
        global missiles

        current_thrust = SHIP_THRUST * 2 if blackhole else SHIP_THRUST
        current_max_speed = MAX_SPEED * 2 if blackhole else MAX_SPEED
        desired_angle = 0

        # Handle thrusting timing
        current_time = time.time()
        if self.thrusting and current_time - self.last_thrust_time > SHIP_THRUST_DURATION:
            self.thrusting = False
            self.last_thrust_time = current_time
        elif not self.thrusting and current_time - self.last_thrust_time > SHIP_THRUST_COOLDOWN:
            self.thrusting = True
            self.last_thrust_time = current_time

        # --- Avoidance and Targeting Logic ---
        avoid_dx = 0
        avoid_dy = 0
        visible_targets = [a for a in asteroids if (a.x - self.x)**2 + (a.y - self.y)**2 <= SHIP_VISION_RADIUS**2]
        
        if blackhole:
            # Flee from black hole with highest priority
            dx = self.x - blackhole.x
            dy = self.y - blackhole.y
            desired_angle = math.atan2(dy, dx)
            self.target = None
        elif visible_targets:
            # Select a target and move toward/attack it
            self.target = random.choice(visible_targets)
            dx = self.target.x - self.x
            dy = self.target.y - self.y
            desired_angle = math.atan2(dy, dx)
            
            # Fire missile if aligned or close
            distance_sq = dx**2 + dy**2
            target_angle = math.atan2(dy, dx)
            angle_delta = abs((target_angle - self.angle + math.pi) % (2 * math.pi) - math.pi)
            if len(missiles) < MAX_MISSILES and (angle_delta < math.pi / 2 or distance_sq < 25):
                missiles.append(Missile(self.x, self.y, self.angle))
            
            # Avoid if too close
            if distance_sq < (self.target.size + 2)**2 * 2:
                scale = ((self.target.size + 2)**2) / (distance_sq + 1e-5) * 0.5
                avoid_dx += dx * scale
                avoid_dy += dy * scale
                desired_angle = math.atan2(avoid_dy, avoid_dx)
        else:
            # No targets, move to center of visible screen
            self.target = None
            cx = VIEWPORT_X_OFFSET + WIDTH / 2
            cy = VIEWPORT_Y_OFFSET + HEIGHT / 2
            dx = cx - self.x
            dy = cy - self.y
            desired_angle = math.atan2(dy, dx) if dx != 0 or dy != 0 else self.angle

        # Apply rotation
        angle_diff = (desired_angle - self.angle + math.pi) % (2 * math.pi) - math.pi
        self.angle += max(-SHIP_TURN_RATE, min(SHIP_TURN_RATE, angle_diff))

        # Apply thrust
        if self.thrusting:
            thrust = current_thrust
            if blackhole:
                thrust *= 4.0  # Stronger thrust when fleeing black hole
            elif visible_targets and abs(avoid_dx) > 0.01 or abs(avoid_dy) > 0.01:
                thrust *= 2.0  # Moderate thrust when avoiding
            ax = math.cos(self.angle) * thrust
            ay = math.sin(self.angle) * thrust
            self.speed_x += ax
            self.speed_y += ay

        # Clamp speed
        speed = math.hypot(self.speed_x, self.speed_y)
        if speed > current_max_speed:
            scale = current_max_speed / speed
            self.speed_x *= scale
            self.speed_y *= scale

        # Update position
        self.x += self.speed_x
        self.y += self.speed_y

        # Clamp to visible area with 1 pixel margin
        self.x = max(VIEWPORT_X_OFFSET + 1, min(self.x, VIEWPORT_X_OFFSET + WIDTH - 2))
        self.y = max(VIEWPORT_Y_OFFSET + 1, min(self.y, VIEWPORT_Y_OFFSET + HEIGHT - 2))

        self.frame += 1

    def draw(self):
        cx = int(self.x)
        cy = int(self.y)
        r, g, b = self.color
        if self.thrusting:
            current_thrust = math.hypot(self.speed_x, self.speed_y)
            trail_strength = int(min(current_thrust / (MAX_SPEED * (2 if blackhole else 1)), 1.0) * THRUST_TRAIL_LENGTH)
            for i in range(1, trail_strength + 1):
                tx = int(self.x - math.cos(self.angle) * i)
                ty = int(self.y - math.sin(self.angle) * i)
                red_intensity = max(0, THRUST_TRAIL_COLOR[0] - i * (THRUST_TRAIL_COLOR[0] // THRUST_TRAIL_LENGTH))
                LED.setpixelCanvas(tx - VIEWPORT_X_OFFSET, ty - VIEWPORT_Y_OFFSET, red_intensity, 0, 0)

        LED.setpixelCanvas(cx - VIEWPORT_X_OFFSET, cy - VIEWPORT_Y_OFFSET, r, g, b)
        dx = int(round(math.cos(self.angle)))
        dy = int(round(math.sin(self.angle)))
        LED.setpixelCanvas(int(cx + dx - VIEWPORT_X_OFFSET), int(cy + dy - VIEWPORT_Y_OFFSET), r, g, b)



class Spark:
    def __init__(self, x, y, angle, speed, length):
        self.x = x
        self.y = y
        self.angle = angle
        self.speed = speed
        # Clamp the length to a max value
        self.length = max(1, min(length, SPARK_TRAIL_MAX_LENGTH))  # <-- clamp to a max of 10
        
        self.lifespan = SPARK_TRAIL_LENGTH #count down timer of how many frames the spark should exist

    def move(self):
        self.x += math.cos(self.angle) * self.speed
        self.y += math.sin(self.angle) * self.speed

    def draw(self):
        for i in range(self.length):
            tx = int(self.x - math.cos(self.angle) * i)
            ty = int(self.y - math.sin(self.angle) * i)

            fade = max(32, SPARK_COLOR[0] - i * (SPARK_COLOR[0] // SPARK_TRAIL_LENGTH * 2))
            #LED.setpixelCanvas(tx, ty, fade, fade * 3 // 4, fade // 2)
            LED.setpixelCanvas(tx - VIEWPORT_X_OFFSET, ty - VIEWPORT_Y_OFFSET, fade, fade * 3 // 4, fade // 2)
            














missiles = []
ship = Ship()
#asteroids = [Asteroid() for _ in range(ASTEROIDS)]
asteroids = [Asteroid.create() for _ in range(ASTEROIDS)]




sparks = []



clock = pygame.time.Clock()
fps_counter = 0
fps_timer = time.time()

# Insert into test2.py: Initialization Section
last_blackhole_time = time.time()
blackhole = None
    



def hard_clear_canvas():
    for y in range(HEIGHT):
        for x in range(WIDTH):
            LED.Canvas.SetPixel(x,y,0,0,0)






def PlayBlasteroids(Duration = 10000, StopEvent = None):
    
    global last_blackhole_time, fps_timer, fps_counter
    global blackhole
    
    #Time date
    last_time_str = ""
    ClockFontSize = 12
    ClockRGB = (0,200,0)

    clock_img = LED.GenerateClockImageWithFixedTiles(FontSize=ClockFontSize, TextColor=ClockRGB, BackgroundColor=(0, 0, 0))

    for asteroid in asteroids:
        asteroid.grow_start_time = time.time()
        asteroid.draw()


    try:
        
        #zoom clock into screen
        clock_img = LED.GenerateClockImageWithFixedTiles(FontSize=ClockFontSize, TextColor=ClockRGB, BackgroundColor=(0, 0, 0))
        LED.ZoomImageObject(clock_img, 0, 110, 0.05, 20)
        
        Done = False
        while (Done == False):
            
            hard_clear_canvas()
            if StopEvent and StopEvent.is_set():
                print("\n" + "="*40)
                print("[Blasteroids] StopEvent received")
                print("-> Shutting down gracefully...")
                print("="*40 + "\n")
                Done = True
                break


            now = time.time()

            # Paint the time as the background
            current_time_str = datetime.now().strftime('%H:%M')
            if current_time_str != last_time_str:
                clock_img = LED.GenerateClockImageWithFixedTiles(FontSize=ClockFontSize, TextColor=ClockRGB, BackgroundColor=(0, 0, 0))
                last_time_str = current_time_str
                print("Time: ",current_time_str)
            draw_clock_overlay(clock_img)
            

            if now - last_blackhole_time > BLACKHOLE_APPEAR_INTERVAL:
                bx = PLAYFIELD_WIDTH // 2
                by = PLAYFIELD_HEIGHT // 2
                
                #the larger sizes should occur less often
                bradius = random.randint(BLACKHOLE_MIN_SIZE, BLACKHOLE_MAX_SIZE)
                if bradius >= 5:
                    bradius = random.randint(BLACKHOLE_MIN_SIZE, BLACKHOLE_MAX_SIZE)
                    if bradius >= 5:
                        bradius = random.randint(BLACKHOLE_MIN_SIZE, BLACKHOLE_MAX_SIZE)

                blackhole = BlackHole(bx, by, bradius)
                blackhole.growing = True
                blackhole.grow_start_time = time.time()
                last_blackhole_time = time.time()


            '''
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
                blackhole.grow_start_time = time.time()
                last_blackhole_time       = time.time()
            '''                


            if blackhole and blackhole.expired():
                blackhole = None


            if not asteroids:
                asteroids.append(Asteroid.create(size=random.randint(MIN_ASTEROID_SIZE,MAX_ASTEROID_SIZE)))
                asteroids.append(Asteroid.create(size=random.randint(MIN_ASTEROID_SIZE,MAX_ASTEROID_SIZE)))
                asteroids.append(Asteroid.create(size=random.randint(MIN_ASTEROID_SIZE,MAX_ASTEROID_SIZE)))
                


            
            handle_collisions(asteroids)




            new_asteroids = []
            for asteroid in asteroids[:]:  # Iterate over a copy to allow removal
                apply_blackhole_gravity(asteroid, asteroids)  # Pass asteroids list for removal
                asteroid.move()
                asteroid.draw()
                if asteroid == ship.target:
                    cx = int(asteroid.x)
                    cy = int(asteroid.y)
                    LED.setpixelCanvas(cx - VIEWPORT_X_OFFSET, cy - VIEWPORT_Y_OFFSET, ASTEROID_TARGET_COLOR[0], ASTEROID_TARGET_COLOR[1], ASTEROID_TARGET_COLOR[2])
                    
                dx = ship.x - asteroid.x
                dy = ship.y - asteroid.y
                if dx * dx + dy * dy < (asteroid.size +1)**2:
                    if time.time() - asteroid.last_hit_time > 1.0:
                        asteroid.health -= 1
                        asteroid.last_hit_time = time.time()
                    if asteroid.health <= 0:
                        new_size = max(MIN_ASTEROID_SIZE, asteroid.size // 2)
                        if new_size < asteroid.size:
                            new_asteroids.append(Asteroid(asteroid.x + 0.5, asteroid.y + 0.5, new_size, color=asteroid.color))
                            new_asteroids.append(Asteroid(asteroid.x - 0.5, asteroid.y - 0.5, new_size))
                        for _ in range(SPARK_COUNT):
                            angle = random.uniform(0, 2 * math.pi)
                            speed = random.uniform(SPARK_SPEED_MIN, SPARK_SPEED_MAX)
                            sparks.append(Spark(asteroid.x, asteroid.y, angle, speed,int(asteroid.size *1.5)))
                        if asteroid in asteroids:
                            asteroids.remove(asteroid)
                        continue
                angle = math.atan2(dy, dx)
                thrust = MAX_SPEED
                ship.speed_x = math.cos(angle + math.pi) * thrust
                ship.speed_y = math.sin(angle + math.pi) * thrust




            apply_blackhole_gravity(ship)


            if len(missiles) < MAX_MISSILES  and random.random() < FIRE_CHANCE and ship.target:
                missiles.append(Missile(ship.x, ship.y, ship.angle))

            for missile in missiles[:]:
                apply_blackhole_gravity(missile)

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
                    new_size = max(MIN_ASTEROID_SIZE, hit.size // 2)
                    if new_size < hit.size:
                        new_asteroids.append(Asteroid(hit.x + 0.5, hit.y + 0.5, new_size, color=hit.color))
                        new_asteroids.append(Asteroid(hit.x - 0.5, hit.y - 0.5, new_size))
                    missiles.remove(missile)
                    for _ in range(SPARK_COUNT):
                        angle = random.uniform(0, 2 * math.pi)
                        speed = random.uniform(SPARK_SPEED_MIN, SPARK_SPEED_MAX)
                        sparks.append(Spark(spark_origin_x, spark_origin_y, angle, speed, int(asteroid.size * 2)))
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
            #    LED.setpixelCanvas(x, 0, 0, 0, 255)  # Top edge
            #    LED.setpixelCanvas(x, HEIGHT - 1, 0, 0, 255)  # Bottom edge
            #for y in range(HEIGHT):
            #    LED.setpixelCanvas(0, y, 0, 0, 255)  # Left edge
            #    LED.setpixelCanvas(WIDTH - 1, y, 0, 0, 255)  # Right edge



            ship.move()
            ship.draw()

            if blackhole:
                blackhole.move()
                blackhole.draw()


            LED.Canvas = LED.TheMatrix.SwapOnVSync(LED.Canvas)

            clock.tick(60)  # Cap the frame rate to 60 FPS

            fps_counter += 1
            if time.time() - fps_timer >= 10.0:
                asteroid_speeds = [math.hypot(a.dx, a.dy) for a in asteroids]
                avg_speed = sum(asteroid_speeds) / len(asteroid_speeds) if asteroid_speeds else 0
                print(f"FPS: {fps_counter / (time.time() - fps_timer):.2f} | Asteroids: {len(asteroids)} | Avg Asteroid Speed: {avg_speed:.3f}")
                fps_counter = 0
                fps_timer = time.time()


            
            


    except KeyboardInterrupt:
        LED.ClearBuffers()
        LED.TheMatrix.SwapOnVSync(LED.Canvas)
        raise






def LaunchBlasteroids(Duration = 10000,ShowIntro=True,StopEvent=None):

  #print("ShowIntro:",ShowIntro)
       
  #LED.scroll_random_movie_intro()       
  if(ShowIntro == True):
    #--------------------------------------
    # M A I N   P R O C E S S I N G      --
    #--------------------------------------
    LED.LoadConfigData()

    LED.ShowTitleScreen(
        BigText             = 'BLAST!',
        BigTextRGB          = LED.HighOrange,
        BigTextShadowRGB    = LED.ShadowOrange,
        LittleText          = '',
        LittleTextZoom      = 1,
        LittleTextRGB       = LED.MedGreen,
        LittleTextShadowRGB = (0,10,0), 
        ScrollText          = 'Get those space rocks before they get you...',
        ScrollTextRGB       = LED.MedYellow,
        ScrollSleep         = 0.03, # time in seconds to control the scrolling (0.005 is fast, 0.1 is kinda slow)
        DisplayTime         = 1,           # time in seconds to wait before exiting 
        ExitEffect          = 0,            # 0=Random / 1=shrink / 2=zoom out / 3=bounce / 4=fade /5=fallingsand
        BigText2RGB         = LED.HighBlue,
        BigText2ShadowRGB   = LED.ShadowRed,

        )


    LED.ClearBigLED()
    LED.ClearBuffers()
    CursorH = 0
    CursorV = 0
    LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"somebody is chucking space rocks at your home planet....",CursorH=CursorH,CursorV=CursorV,MessageRGB=(225,0,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalTypeSpeed)
    LED.BlinkCursor(CursorH= CursorH,CursorV=CursorV,CursorRGB=CursorRGB,CursorDarkRGB=CursorDarkRGB,BlinkSpeed=0.5,BlinkCount=2)
    LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"go blast them, young pilot!",CursorH=CursorH,CursorV=CursorV,MessageRGB=(150,150,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalTypeSpeed)
    LED.BlinkCursor(CursorH= CursorH,CursorV=CursorV,CursorRGB=CursorRGB,CursorDarkRGB=CursorDarkRGB,BlinkSpeed=0.5,BlinkCount=2)


  PlayBlasteroids(Duration=Duration,StopEvent=StopEvent)
      









#execute if this script is executed directly from command line
if __name__ == "__main__":
    try:
        #LED.scroll_sentence_star_wars("A long time ago in a clock far far away...", tilt_factor=0.6, scroll_delay=0.06, font_path="/usr/share/fonts/truetype/noto/NotoMono-Regular.ttf")
        #LED.scroll_random_movie_intro()
        LaunchBlasteroids(Duration=100000, ShowIntro=False, StopEvent=None)

    except KeyboardInterrupt:
        print("Exiting game due to Ctrl-C.")


















