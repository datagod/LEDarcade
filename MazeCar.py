#!/usr/bin/env python
#------------------------------------------------------------------------------
#  MAZECAR - Self-playing maze (full maze on screen)
#
#  The entire maze fits on the 64x32 panel.  Black background, walls only.
#  AI car drives from start to goal.
#------------------------------------------------------------------------------

import LEDarcade as LED
import random
import time
from collections import deque


# --- Display size (from matrix config) ---
WIDTH  = LED.HatWidth
HEIGHT = LED.HatHeight

# --- Maze fills the panel (2:1 aspect), centered with margins ---
TILE_SIZE   = 2
MAZE_COLS   = 31
MAZE_ROWS   = 15
MAZE_WIDTH  = MAZE_COLS * TILE_SIZE
MAZE_HEIGHT = MAZE_ROWS * TILE_SIZE
OFFSET_H    = (WIDTH  - MAZE_WIDTH)  // 2
OFFSET_V    = (HEIGHT - MAZE_HEIGHT) // 2

CAR_RADIUS = 0   # 1x1 car fits 2px corridors

# --- Colors ---
WALL_RGB  = LED.WallRGB
EMPTY_RGB = (0, 0, 0)
GOAL_RGB  = (0, 200, 60)
CAR_BODY  = (220, 40, 40)
CAR_CAB   = (255, 200, 60)

FRAME_DELAY   = 0.035
MOVE_COOLDOWN = 2
PATH_RECALC   = 8


class Cell(object):
  def __init__(self, name, r, g, b):
    self.name = name
    self.r    = r
    self.g    = g
    self.b    = b


EmptyCell = Cell('empty', *EMPTY_RGB)
GoalCell  = Cell('goal',  *GOAL_RGB)


class Car(object):
  def __init__(self, h, v, direction=2):
    self.h         = h
    self.v         = v
    self.direction = direction


class MazeWorld(object):
  def __init__(self, width, height):
    self.width  = width
    self.height = height
    self.map    = [[EmptyCell for _ in range(width)] for _ in range(height)]

  def set_cell(self, h, v, cell):
    if 0 <= h < self.width and 0 <= v < self.height:
      self.map[v][h] = cell

  def is_wall(self, h, v):
    if h < 0 or v < 0 or h >= self.width or v >= self.height:
      return True
    return self.map[v][h].name == 'wall'

  def display(self, car):
    LED.Canvas.Clear()

    for v in range(self.height):
      for h in range(self.width):
        cell = self.map[v][h]
        if cell.name == 'wall':
          LED.setpixelCanvas(h + OFFSET_H, v + OFFSET_V, cell.r, cell.g, cell.b)
        elif cell.name == 'goal':
          LED.setpixelCanvas(h + OFFSET_H, v + OFFSET_V, cell.r, cell.g, cell.b)

    draw_car(car)
    LED.TheMatrix.SwapOnVSync(LED.Canvas)


def generate_cell_maze(cols, rows):
  grid = [[1 for _ in range(cols)] for _ in range(rows)]
  stack = [(1, 1)]
  grid[1][1] = 0

  while stack:
    x, y = stack[-1]
    dirs = [(0, -2), (0, 2), (-2, 0), (2, 0)]
    random.shuffle(dirs)
    carved = False
    for dx, dy in dirs:
      nx, ny = x + dx, y + dy
      if 1 <= nx < cols - 1 and 1 <= ny < rows - 1 and grid[ny][nx] == 1:
        grid[y + dy // 2][x + dx // 2] = 0
        grid[ny][nx] = 0
        stack.append((nx, ny))
        carved = True
        break
    if not carved:
      stack.pop()

  for x in range(cols):
    grid[0][x] = 1
    grid[rows - 1][x] = 1
  for y in range(rows):
    grid[y][0] = 1
    grid[y][cols - 1] = 1

  return grid


def expand_to_world(cell_grid, cols, rows):
  world = MazeWorld(MAZE_WIDTH, MAZE_HEIGHT)
  wall  = Cell('wall', *WALL_RGB)

  for cy in range(rows):
    for cx in range(cols):
      cell = wall if cell_grid[cy][cx] == 1 else EmptyCell
      for py in range(TILE_SIZE):
        for px in range(TILE_SIZE):
          world.set_cell(cx * TILE_SIZE + px, cy * TILE_SIZE + py, cell)

  return world


def cell_center(cx, cy):
  return cx * TILE_SIZE + TILE_SIZE // 2, cy * TILE_SIZE + TILE_SIZE // 2


def find_floor_cell(cell_grid, cols, rows, near_cx, near_cy):
  for radius in range(max(cols, rows)):
    for dy in range(-radius, radius + 1):
      for dx in range(-radius, radius + 1):
        cx = near_cx + dx
        cy = near_cy + dy
        if 1 <= cx < cols - 1 and 1 <= cy < rows - 1 and cell_grid[cy][cx] == 0:
          return cx, cy
  return 1, 1


def build_world():
  cell_grid = generate_cell_maze(MAZE_COLS, MAZE_ROWS)
  world     = expand_to_world(cell_grid, MAZE_COLS, MAZE_ROWS)

  start_cx, start_cy = find_floor_cell(cell_grid, MAZE_COLS, MAZE_ROWS, 1, 1)
  goal_cx,  goal_cy  = find_floor_cell(cell_grid, MAZE_COLS, MAZE_ROWS, MAZE_COLS - 2, MAZE_ROWS - 2)
  start_h, start_v   = cell_center(start_cx, start_cy)
  goal_h,  goal_v    = cell_center(goal_cx, goal_cy)
  world.set_cell(goal_h, goal_v, GoalCell)

  return world, start_h, start_v, goal_h, goal_v, cell_grid


def draw_car(car):
  h = car.h + OFFSET_H
  v = car.v + OFFSET_V
  d = car.direction

  if 0 <= h < WIDTH and 0 <= v < HEIGHT:
    LED.setpixelCanvas(h, v, *CAR_BODY)

  if d == 1 and 0 <= h < WIDTH and 0 <= v - 1 < HEIGHT:
    LED.setpixelCanvas(h, v - 1, *CAR_CAB)
  elif d == 2 and 0 <= h + 1 < WIDTH and 0 <= v < HEIGHT:
    LED.setpixelCanvas(h + 1, v, *CAR_CAB)
  elif d == 3 and 0 <= h < WIDTH and 0 <= v + 1 < HEIGHT:
    LED.setpixelCanvas(h, v + 1, *CAR_CAB)
  elif d == 4 and 0 <= h - 1 < WIDTH and 0 <= v < HEIGHT:
    LED.setpixelCanvas(h - 1, v, *CAR_CAB)


def direction_between(h1, v1, h2, v2):
  dh = h2 - h1
  dv = v2 - v1
  if abs(dh) >= abs(dv):
    return 2 if dh > 0 else 4
  return 3 if dv > 0 else 1


def bfs_next_direction(cell_grid, car, goal_h, goal_v):
  start = (car.h // TILE_SIZE, car.v // TILE_SIZE)
  goal  = (goal_h // TILE_SIZE, goal_v // TILE_SIZE)
  if start == goal:
    return car.direction

  prev  = {start: None}
  queue = deque([start])

  while queue:
    cx, cy = queue.popleft()
    if (cx, cy) == goal:
      break
    for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
      nx, ny = cx + dx, cy + dy
      if 0 <= nx < MAZE_COLS and 0 <= ny < MAZE_ROWS and (nx, ny) not in prev:
        if cell_grid[ny][nx] == 0:
          prev[(nx, ny)] = (cx, cy)
          queue.append((nx, ny))

  if goal not in prev:
    return pick_fallback_direction(cell_grid, car)

  step = goal
  while prev[step] is not None and prev[step] != start:
    step = prev[step]

  sh, sv = cell_center(*start)
  nh, nv = cell_center(*step)
  return direction_between(sh, sv, nh, nv)


def pick_fallback_direction(cell_grid, car):
  order = [car.direction, 2, 3, 4, 1]
  seen  = set()
  for direction in order:
    if direction in seen:
      continue
    seen.add(direction)
    nh, nv = LED.CalculateDotMovement(car.h, car.v, direction)
    if not car_blocked_at(cell_grid, nh, nv):
      return direction
  return car.direction


def car_blocked_at(cell_grid, h, v):
  for dh in range(-CAR_RADIUS, CAR_RADIUS + 1):
    for dv in range(-CAR_RADIUS, CAR_RADIUS + 1):
      ph = h + dh
      pv = v + dv
      cx = ph // TILE_SIZE
      cy = pv // TILE_SIZE
      if cx < 0 or cy < 0 or cx >= MAZE_COLS or cy >= MAZE_ROWS or cell_grid[cy][cx] == 1:
        return True
  return False


def try_move_car(cell_grid, car, direction):
  nh, nv = LED.CalculateDotMovement(car.h, car.v, direction)
  if car_blocked_at(cell_grid, nh, nv):
    return False
  car.h = nh
  car.v = nv
  car.direction = direction
  return True


def show_win_banner():
  LED.ShowScrollingBanner2('MAZE CLEAR!', (0, 220, 80), LED.ScrollSleep)


def PlayMazeCar(Duration=10000, StopEvent=None):
  world, start_h, start_v, goal_h, goal_v, cell_grid = build_world()
  car = Car(start_h, start_v, direction=2)

  move_cooldown = 0
  path_cooldown = 0
  planned_dir   = 2
  start_time    = time.time()

  while True:
    if StopEvent and StopEvent.is_set():
      return

    _, minutes, _ = LED.GetElapsedTime(start_time, time.time())
    if minutes > Duration:
      return

    if path_cooldown <= 0:
      planned_dir = bfs_next_direction(cell_grid, car, goal_h, goal_v)
      path_cooldown = PATH_RECALC

    if move_cooldown <= 0:
      if try_move_car(cell_grid, car, planned_dir):
        move_cooldown = MOVE_COOLDOWN
        if abs(car.h - goal_h) <= 1 and abs(car.v - goal_v) <= 1:
          world.display(car)
          show_win_banner()
          world, start_h, start_v, goal_h, goal_v, cell_grid = build_world()
          car = Car(start_h, start_v, direction=2)
          planned_dir = 2
          path_cooldown = 0
      else:
        planned_dir = pick_fallback_direction(cell_grid, car)
        path_cooldown = 0
    else:
      move_cooldown -= 1

    path_cooldown -= 1
    world.display(car)
    time.sleep(FRAME_DELAY)


def LaunchMazeCar(Duration=10000, ShowIntro=True, StopEvent=None):
  if ShowIntro:
    LED.LoadConfigData()
    LED.ShowTitleScreen(
      BigText             = 'MAZE',
      BigTextRGB          = LED.HighGreen,
      BigTextShadowRGB    = LED.ShadowGreen,
      LittleText          = 'CAR',
      LittleTextRGB       = LED.MedOrange,
      LittleTextShadowRGB = (40, 10, 0),
      ScrollText          = 'Self-driving through the maze',
      ScrollTextRGB       = LED.MedCyan,
      ScrollSleep         = 0.03,
      DisplayTime         = 1,
      ExitEffect          = 0,
    )

  LED.ClearBigLED()
  LED.ClearBuffers()
  PlayMazeCar(Duration=Duration, StopEvent=StopEvent)


if __name__ == '__main__':
  LED.Initialize()
  while True:
    LaunchMazeCar(Duration=100000, ShowIntro=True, StopEvent=None)