#!/usr/bin/env python
#------------------------------------------------------------------------------
#  RALLYDOT — Rally-X style chase game for LEDarcade
#
#  Ported from ArcadeRetroClockHD (16x16 Unicorn HD viewport) to 64x32.
#  Large world map + camera centered on the player car.
#------------------------------------------------------------------------------

import copy
import math
import time
import random
from random import randint

import LEDarcade as LED

# Viewport = full panel (read live so ClockConfig 64x32 is honored after Initialize)
def _view_w():
    return int(getattr(LED, "HatWidth", 64) or 64)

def _view_h():
    return int(getattr(LED, "HatHeight", 32) or 32)

# Back-compat names used throughout ported code (updated each frame via refresh_view_size)
VIEW_W = 64
VIEW_H = 32

def refresh_view_size():
    global VIEW_W, VIEW_H
    VIEW_W = _view_w()
    VIEW_H = _view_h()

# Tunables
KEYBOARD_SPEED = 25
CHECK_CLOCK_SPEED = 60   # moves between clock-sprite checks (HD global)
CHECK_TIME = 60          # seconds between clock displays
FRAME_SLEEP = 0.008
CPU_MODIFIER = 1
SCROLL_SLEEP = getattr(LED, "ScrollSleep", 0.03)
FLASH_SLEEP = getattr(LED, "FlashSleep", 0.01)

# Tick slowdown: cars/AI act when (moves % (period * TICK_SCALE)) == 0.
# Higher = slower. TICK_SCALE=4 → ~25% of HD original (half of prior TICK_SCALE=2).
TICK_SCALE = 4
# Extra slowdown for red enemy dots only (2 = half as fast as player-relative enemy pace)
ENEMY_SPEED_SCALE = 2

# Display: ColorList walls use "Low/Dark" RGB (~45–100). Run hot on the panel.
MATRIX_BRIGHTNESS = 100
DISPLAY_GAMMA = 2.55   # scale palette toward full LED output (clamped at 255)


def on_tick(moves_count, period):
  """True when this global move counter is an action tick for `period`."""
  p = max(1, int(period) * TICK_SCALE)
  return (moves_count % p) == 0


def _apply_full_brightness():
  """Matrix at 100% + mark LED.Gamma for any late color uses."""
  try:
    LED.Gamma = 1.0
  except Exception:
    pass
  try:
    LED.TheMatrix.brightness = MATRIX_BRIGHTNESS
  except Exception:
    pass
  print("[RallyDot] brightness={} display_gamma={}".format(
      MATRIX_BRIGHTNESS, DISPLAY_GAMMA))

# HD aliases used by ported loop
CheckClockSpeed = CHECK_CLOCK_SPEED
CheckTime = CHECK_TIME
ClockOnDuration = 3
ClockOffDuration = max(1, CheckTime - ClockOnDuration)
ClockSlideSpeed = 1

# HD used a module-level move counter shared by helpers (e.g. TurnTowardsFuel...)
moves = 0

# Color aliases from LEDarcade
SDLowYellowR = LED.SDLowYellowR
SDLowYellowG = LED.SDLowYellowG
SDLowYellowB = LED.SDLowYellowB
SDLowRedR = LED.SDLowRedR
SDLowRedG = LED.SDLowRedG
SDLowRedB = LED.SDLowRedB
SDLowGreenR = LED.SDLowGreenR
SDLowGreenG = LED.SDLowGreenG
SDLowGreenB = LED.SDLowGreenB
SDMedPurpleR = getattr(LED, "SDMedPurpleR", 100)
SDMedPurpleG = getattr(LED, "SDMedPurpleG", 0)
SDMedPurpleB = getattr(LED, "SDMedPurpleB", 100)


def _stop(StopEvent):
    return StopEvent is not None and StopEvent.is_set()


def poll_keyboard_safe():
    """Keyboard poll that is a no-op when not attached to a real TTY (nohup/sudo)."""
    import sys
    if not sys.stdin.isatty():
        return ""
    try:
        return LED.PollKeyboard()
    except Exception:
        return ""


def _gamma_rgb(r, g, b):
    if r or g or b:
        r = min(255, int(r * DISPLAY_GAMMA))
        g = min(255, int(g * DISPLAY_GAMMA))
        b = min(255, int(b * DISPLAY_GAMMA))
    return r, g, b


def _show():
    """Present the back-buffer canvas once (no direct TheMatrix writes)."""
    try:
        LED.Canvas = LED.TheMatrix.SwapOnVSync(LED.Canvas)
    except Exception:
        try:
            LED.TheMatrix.SwapOnVSync(LED.Canvas)
        except Exception:
            pass


def setpixel(h, v, r, g, b):
    """Plot into canvas only (never TheMatrix.SetPixel — that causes double-draw/ghosts)."""
    if 0 <= h < VIEW_W and 0 <= v < VIEW_H:
        r, g, b = _gamma_rgb(r, g, b)
        try:
            LED.Canvas.SetPixel(h, v, r, g, b)
        except Exception:
            try:
                LED.setpixelCanvas(h, v, r, g, b)
            except Exception:
                pass
        try:
            LED.ScreenArray[v][h] = (r, g, b)
        except Exception:
            pass


# Clock time overlay: dark translucent bar behind digits
CLOCK_BACKDROP_ALPHA = 0.62
CLOCK_BACKDROP_RGB = (0, 0, 0)
CLOCK_BACKDROP_PAD = 2
# Always-on clock: upper-right corner (panel coords)
CLOCK_MARGIN_H = 1
CLOCK_MARGIN_V = 1
CLOCK_ALWAYS_ON = True


def _draw_dark_backdrop(canvas, x, y, w, h, alpha=0.6, color=(0, 0, 0), pad=2):
  """Blend a darker rectangle over current ScreenArray/canvas (fake transparency)."""
  x0 = max(0, int(x) - pad)
  y0 = max(0, int(y) - pad)
  x1 = min(VIEW_W, int(x) + int(w) + pad)
  y1 = min(VIEW_H, int(y) + int(h) + pad)
  cr, cg, cb = color
  a = max(0.0, min(1.0, float(alpha)))
  inv = 1.0 - a
  set_px = canvas.SetPixel
  for py in range(y0, y1):
    for px in range(x0, x1):
      try:
        br, bg, bb = LED.ScreenArray[py][px]
      except Exception:
        br = bg = bb = 0
      r = int(br * inv + cr * a)
      g = int(bg * inv + cg * a)
      b = int(bb * inv + cb * a)
      set_px(px, py, r, g, b)
      try:
        LED.ScreenArray[py][px] = (r, g, b)
      except Exception:
        pass


def _draw_circle(canvas, cx, cy, radius, rgb, panel_w=None, panel_h=None):
  """Midpoint circle (outline) in rgb."""
  panel_w = panel_w if panel_w is not None else VIEW_W
  panel_h = panel_h if panel_h is not None else VIEW_H
  r, g, b = rgb
  x = int(radius)
  y = 0
  err = 0
  set_px = canvas.SetPixel

  def plot(px, py):
    if 0 <= px < panel_w and 0 <= py < panel_h:
      set_px(px, py, r, g, b)

  while x >= y:
    plot(cx + x, cy + y)
    plot(cx + y, cy + x)
    plot(cx - y, cy + x)
    plot(cx - x, cy + y)
    plot(cx - x, cy - y)
    plot(cx - y, cy - x)
    plot(cx + y, cy - x)
    plot(cx + x, cy - y)
    y += 1
    if err <= 0:
      err += 2 * y + 1
    if err > 0:
      x -= 1
      err -= 2 * x + 1


def _draw_text_line(canvas, text, x, y, rgb, panel_w=None, panel_h=None, gap=1):
  """Draw uppercase banner text via AlphaSpriteList (1×)."""
  panel_w = panel_w if panel_w is not None else VIEW_W
  panel_h = panel_h if panel_h is not None else VIEW_H
  r, g, b = rgb
  cursor = int(x)
  set_px = canvas.SetPixel
  for ch in text.upper():
    if ch == " ":
      cursor += 3
      continue
    if not ("A" <= ch <= "Z"):
      cursor += 3
      continue
    try:
      spr = LED.TrimSprite(copy.deepcopy(LED.AlphaSpriteList[ord(ch) - ord("A")]))
    except Exception:
      cursor += 4
      continue
    for count in range(spr.width * spr.height):
      if spr.grid[count] == 0:
        continue
      ly, lx = divmod(count, spr.width)
      px, py = cursor + lx, int(y) + ly
      if 0 <= px < panel_w and 0 <= py < panel_h:
        set_px(px, py, r, g, b)
    cursor += spr.width + gap
  return cursor


def _draw_out_of_fuel_overlay(canvas, screen_x, screen_y):
  """Red circle around the car + OUT OF FUEL label."""
  cx = int(round(screen_x))
  cy = int(round(screen_y))
  # pulsing ring
  radius = 5 + int((time.time() * 4) % 2)
  _draw_circle(canvas, cx, cy, radius, (255, 20, 20))
  _draw_circle(canvas, cx, cy, radius + 1, (180, 0, 0))

  # Label above car (dark bar + text)
  label = "OUT OF FUEL"
  # rough width: ~4px/letter * 10 + gaps
  text_w = 10 * 4 + 9
  tx = max(0, min(VIEW_W - text_w, cx - text_w // 2))
  ty = max(0, cy - 12)
  _draw_dark_backdrop(canvas, tx, ty, text_w, 7, alpha=0.7, color=(0, 0, 0), pad=1)
  _draw_text_line(canvas, label, tx, ty, (255, 40, 40))


class EmptyObject(object):
    def __init__(self, name="EmptyObject"):
        self.name = name
        self.alive = 0
        self.lives = 0
        self.r = 0
        self.g = 0
        self.b = 0
        self.exploding = 0
        self.h = 0
        self.v = 0
        self.direction = 1
        self.scandirection = 1
        self.speed = 1
        self.destination = ""
        self.radarrange = 0


def camera_for_car(car, world):
    """Center viewport on car, clamped to map bounds."""
    refresh_view_size()
    cam_h = int(car.h) - VIEW_W // 2
    cam_v = int(car.v) - VIEW_H // 2
    max_h = max(0, world.width - VIEW_W)
    max_v = max(0, world.height - VIEW_H)
    if cam_h < 0:
        cam_h = 0
    elif cam_h > max_h:
        cam_h = max_h
    if cam_v < 0:
        cam_v = 0
    elif cam_v > max_v:
        cam_v = max_v
    return cam_h, cam_v



def IncreaseColor(Car):

  #Make player car more blue
  if (Car.name == "Player"):
    Car.b = Car.b + 20
    
    if (Car.b >= 255):
      Car.b = 255

  #Make enemy more red
  else:
    Car.r = Car.r + 50
    
    if (Car.r >= 255):
      Car.r = 255

  #print ("Carname rgb",Car.name,Car.r,Car.g,Car.b)      
      
def DecreaseColor(Car):
  #Make player car less blue
  if (Car.name == "Player"):
    Car.b = Car.b - 1

    if (Car.b <= 60):
      Car.b = 60
      
    
  #Make player car less blue
  else:
    Car.r = Car.r - 1

    if (Car.r <= 60):
      Car.r = 60

      
      



class GameWorld(object):
  def __init__(self,name,width,height,Map,Playfield,CurrentRoomH,CurrentRoomV,DisplayH, DisplayV):
    self.name      = name
    self.width     = width
    self.height    = height
    self.Map       = ([[]])
    self.Playfield = ([[]])
    self.CurrentRoomH = 0
    self.CurrentRoomV = 0
    self.DisplayH     = 0
    self.DisplayV     = 0
    
    
    #print ("RD - Initialize map and playfield  width height: ",self.width, self.height)
    self.Map       = [[0 for i in range(self.width)] for i in range(self.height)]
    self.Playfield = [[EmptyObject('EmptyObject') for i in range(self.width)] for i in range(self.height)]

    #print ("--Initializing map--")
    #print (*self.Map[0])
    #print (*self.Map[2])
    #print ("Map Length: ",len(self.Map[0]))
    #print ("Playfield Length",len(self.Playfield[0]))
    #print ("-------------------")
    

    
    
    
    
    

  def DisplayExplodingObjects(self,h,v):
    #This function accepts h,v coordinates for the entire map (e.gv. 1,8  20,20,  64,64)    
    #Displays what is on the playfield currently, including walls, cars, etc.
    r = 0
    g = 0
    b = 0
    count = 0

    for V in range(0,VIEW_H):
      for H in range (0,VIEW_W):
        if (v+V < self.height and h+H < self.width):
          name = self.Playfield[v+V][h+H].name
        
          if (name in ("Enemy") and self.Playfield[v+V][h+H].exploding == 1):
            #print("Exploding Object - h,v,name ",h,v,name)
            r = 0
            g = 0
            b = 0          
            
            #EXPLODE ENEMY CAR BOMBS
            #Source Car blows up
            self.Playfield[v+V][h+H].exploding = 0
            self.Playfield[v+V][h+H].lives = 0
            self.Playfield[v+V][h+H].alive = 0
            setpixel(H,V,255,255,255)
            #remove dead object from playfield
            self.Playfield[v+V][h+H] = EmptyObject('EmptyObject') 
    _show()
    #SendBufferPacket(RemoteDisplay,VIEW_H,VIEW_W)


    return;    
    
    

  def DisplayWindow(self, h, v, do_swap=True):
    """
    Camera window (h,v) = upper-left on virtual map → full panel.
    Always paints every viewport pixel (no leftovers / ghost maps).
    Single canvas path + optional one VSync swap.
    """
    refresh_view_size()
    try:
      LED.Canvas.Clear()
    except Exception:
      pass

    # Clamp camera so we never sample with negative indices
    if h < 0:
      h = 0
    if v < 0:
      v = 0

    pf = self.Playfield
    ph, pw = self.height, self.width
    canvas = LED.Canvas
    set_px = canvas.SetPixel

    for V in range(0, VIEW_H):
      mv = v + V
      for H in range(0, VIEW_W):
        mh = h + H
        if 0 <= mv < ph and 0 <= mh < pw:
          cell = pf[mv][mh]
          if cell.name == "EmptyObject":
            r = g = b = 0
          else:
            r, g, b = _gamma_rgb(cell.r, cell.g, cell.b)
        else:
          r = g = b = 0
        set_px(H, V, r, g, b)
        try:
          LED.ScreenArray[V][H] = (r, g, b)
        except Exception:
          pass

    if do_swap:
      _show()
    return

  def DisolveWindow(self, h, v, sleep=0):
    # Instant clear (no per-pixel sleep)
    try:
      LED.Canvas.Clear()
      _show()
    except Exception:
      pass
    try:
      LED.ClearBigLED()
      LED.ClearBuffers()
    except Exception:
      pass
    return

  def DisplayWindowWithSprite(self, h, v, TheSprite):
    # One frame: map + dark translucent bar + sprite, then one swap
    self.DisplayWindow(h, v, do_swap=False)
    try:
      sw = int(getattr(TheSprite, "width", 12) or 12)
      sh_h = int(getattr(TheSprite, "height", 7) or 7)
      sh = max(0, min(VIEW_W - sw, VIEW_W // 2 - sw // 2))
      sv = max(0, int(getattr(TheSprite, "v", 1) or 1))
      if sv + sh_h > VIEW_H:
        sv = max(0, VIEW_H - sh_h)
      TheSprite.h = sh
      TheSprite.v = sv
      # Dark translucent rectangle behind the clock so time stays readable
      _draw_dark_backdrop(
        LED.Canvas, sh, sv, sw, sh_h,
        alpha=CLOCK_BACKDROP_ALPHA,
        color=CLOCK_BACKDROP_RGB,
        pad=CLOCK_BACKDROP_PAD,
      )
      if hasattr(TheSprite, "Display"):
        try:
          TheSprite.Display(sh, sv)
        except TypeError:
          try:
            TheSprite.Display()
          except Exception:
            pass
    except Exception:
      pass
    _show()
    return

  def UpdateObjectDisplayCoordinates(self,h,v):
    #This function looks at a window (an 8x8 display grid for the unicorn hat)
    #and updates the dh,dv location information for objects in that grid
    #This is useful if we want to blow something up on screen
    
    #scroll off
    for V in range(0,VIEW_H):
      for H in range (0,VIEW_W):
        name = self.Playfield[v+V][h+H].name
        if (name == "Player" or name == "Enemy" or name == "Fuel"):
          self.Playfield[v+V][h+H].dh = H
          self.Playfield[v+V][h+H].dv = V
          

  
  def CopyMapToPlayfield(self):
    #This function is run once to populate the playfield with wall objects, based on the map drawing
    #XY is actually implemented as YX.  Counter intuitive, but it works.

    width  = self.width 
    height = self.height 
   
    #print ("RD - CopyMapToPlayfield - Width Height: ", width,height)
    x = 0
    y = 0
    
    
    #print ("width height: ",width,height)
    
    for y in range (0,height):
      #print ("-------------------")
      #print (*self.Map[y])
  
      for x in range(0,width):
        #print ("RD xy color: ",x,y, self.Map[y][x])
        SDColor = self.Map[y][x]
        
        
  
        if (SDColor != 0):
          try:
            r,g,b = LED.ColorList[SDColor]
          except (IndexError, TypeError):
            r,g,b = (40, 40, 80)
          self.Playfield[y][x] = LED.Wall(x,y,r,g,b,1,1,'Wall')
        else:
          self.Playfield[y][x] = EmptyObject('EmptyObject')
          
          
          
         
      
      
          
          
  def ScrollMapDots(self,direction,dots,speed):

    #we only want to scroll the number of dots, not the whole room
    #DisplayWindow has HV starting in upper left hand corner
    
    x = 0
    ScrollH = self.DisplayH
    ScrollV = self.DisplayV

    #print("ScrollMapDots - ScrollH ScrollV direction width",ScrollH,ScrollV, direction, self.width)
     
    #Scroll Up
    if (direction == 1):
      
      if (ScrollV - dots >= 0):
      
        for x in range (ScrollV-1,ScrollV-dots-1,-1):
          #print ("ScrollMapDots up: ScrollH x",ScrollH,x)
          self.DisplayWindow(ScrollH,x)
        ScrollV = x
         

    
    #Scroll Down
    if (direction == 3):
          
      if (ScrollV + VIEW_W + dots <= self.height):
        for x in range (ScrollV+1,ScrollV+dots+1):
          #print ("ScrollMapDots down: ScrollH x",ScrollH,x)
          self.DisplayWindow(ScrollH,x)
        ScrollV = x
      
    #Scroll right
    if (direction == 2):
      if (ScrollH + VIEW_W + dots  <= self.width):
        for x in range (ScrollH+1,ScrollH+dots+1):
          #print ("ScrollMapDots right: x ScrollV",x,ScrollV)
          self.DisplayWindow(x,ScrollV)
        ScrollH = x
      
    
    #Scroll left
    elif (direction == 4):
      if (ScrollH - dots >= 0):
        for x in range (ScrollH-1,ScrollH-dots-1,-1):
          #print ("ScrollMapDots left: x ScrollV",x,ScrollV)
          self.DisplayWindow(x,ScrollV)
        ScrollH = x


    #Set current room number
    self.CurrentRoomH,r = divmod(ScrollH,8)
    self.CurrentRoomV,r = divmod(ScrollV,8)
    self.DisplayH = ScrollH
    self.DisplayV = ScrollV
  
    #time.sleep(speed)


    
  def ScrollMapDots8Way(self,direction,dots,speed):

    #we only want to scroll the number of dots, not the whole room
    #DisplayWindow has HV starting in upper left hand corner
    
    x = 0
    ScrollH = self.DisplayH
    ScrollV = self.DisplayV

    #print("ScrollMapDots8Way - ScrollH ScrollV direction width",ScrollH,ScrollV, direction, self.width)
     
    #Scroll N
    if (direction == 1):
      
      if (ScrollV - dots >= 0):
      
        for x in range (ScrollV-1,ScrollV-dots-1,-1):
          self.DisplayWindow(ScrollH,x)
        ScrollV = x
         
    #Scroll NE
    if (direction == 2):
      
      #Scroll up and right
      if (ScrollV - dots >= 0):
        for x in range (ScrollV-1,ScrollV-dots-1,-1):
          self.DisplayWindow(ScrollH,x)
        ScrollV = x

      if (ScrollH + 8 + dots  <= self.width):
        for x in range (ScrollH+1,ScrollH+dots+1):
          self.DisplayWindow(x,ScrollV)
        ScrollH = x
         
         
    #Scroll E
    if (direction == 3):
      if (ScrollH + 8 + dots  <= self.width):
        for x in range (ScrollH+1,ScrollH+dots+1):
          self.DisplayWindow(x,ScrollV)
        ScrollH = x

    #Scroll SE
    
    #Scroll right then down
    if (direction == 4):
      if (ScrollH + 8 + dots  <= self.width):
        for x in range (ScrollH+1,ScrollH+dots+1):
          self.DisplayWindow(x,ScrollV)
        ScrollH = x

      if (ScrollV + 8 + dots <= self.height):
        for x in range (ScrollV+1,ScrollV+dots+1):
          self.DisplayWindow(ScrollH,x)
        ScrollV = x

        
        
         
    #Scroll S
    if (direction == 5):
          
      if (ScrollV + 8 + dots <= self.height):
        for x in range (ScrollV+1,ScrollV+dots+1):
          self.DisplayWindow(ScrollH,x)
        ScrollV = x
      
    
    #Scroll SW
    
    #Scroll down then left
    elif (direction == 6):
      if (ScrollH - dots >= 0):
        for x in range (ScrollH-1,ScrollH-dots-1,-1):
          self.DisplayWindow(x,ScrollV)
        ScrollH = x

      if (ScrollV + 8 + dots <= self.height):
        for x in range (ScrollV+1,ScrollV+dots+1):
          self.DisplayWindow(ScrollH,x)
        ScrollV = x
        
        
    #Scroll W
    elif (direction == 7):
      if (ScrollH - dots >= 0):
        for x in range (ScrollH-1,ScrollH-dots-1,-1):
          self.DisplayWindow(x,ScrollV)
        ScrollH = x
      
      
    #Scroll NW
    #Scroll upd then left
    elif (direction == 8):
      if (ScrollV - dots >= 0):
        for x in range (ScrollV-1,ScrollV-dots-1,-1):
          self.DisplayWindow(ScrollH,x)
        ScrollV = x

      if (ScrollH - dots >= 0):
        for x in range (ScrollH-1,ScrollH-dots-1,-1):
          self.DisplayWindow(x,ScrollV)
        ScrollH = x

    
    #time.sleep(0.5)
 


    #Set current room number
    self.CurrentRoomH,r = divmod(ScrollH,8)
    self.CurrentRoomV,r = divmod(ScrollV,8)
    self.DisplayH = ScrollH
    self.DisplayV = ScrollV
  




# -------------------------
# --      Cars           --
# -------------------------




class CarDot(object):
  
  def __init__(self,h,v,dh,dv,r,g,b,direction,scandirection,gear,currentgear,speed,alive,lives,name,score,exploding,radarrange,destination):
    self.h             = h         # location on playfield (e.gv. 10,35)
    self.v             = v         # location on playfield (e.gv. 10,35)
    self.dh            = dh        # location on display   (e.gv. 3,4) 
    self.dv            = dv        # location on display   (e.gv. 3,4) 
    self.r             = r
    self.g             = g
    self.b             = b
    self.direction     = direction      #direction of travel
    self.scandirection = scandirection  #direction of scanners, if equipped
    self.currentgear   = currentgear    
    self.speed         = speed
    self.alive         = 1
    self.lives         = 3
    self.name          = name
    self.score         = 0
    self.exploding     = 0
    self.radarrange    = 20
    self.destination   = ""
    self.gas           = PLAYER_GAS_MAX  # player tank; enemies ignore

    #Hold speeds in a list, acting like gears
    self.gear = []
    self.gear.append(5)
    self.gear.append(4)
    self.gear.append(3)
    self.gear.append(2)
    self.gear.append(1)


  def Display(self):
    if (self.alive == 1):
      setpixel(self.h,self.v,self.r,self.g,self.b)
     # print("display HV:", self.h,self.v)
      _show()
      #SendBufferPacket(RemoteDisplay,VIEW_H,VIEW_W)

      
  def ShiftGear(self,direction):
    #Gears is a list with X gears
    #lists start counting at 0
    #Min gear = 0
    #Max gear = x-1

    NumGears = len(self.gear)

    if (direction == 'down'):
      self.currentgear = self.currentgear -1
    else:
      self.currentgear = self.currentgear +1
    
    #need to put in the CPUModifier here
    #don't let player go too fast or too slow
    if (self.name == "Player"):
      if self.currentgear > NumGears -2:
        self.currentgear = NumGears -2

      if self.currentgear <= 3:
        self.currentgear = 3
    
    
    if (self.currentgear > NumGears -1):
      self.currentgear = NumGears -1
    elif (self.currentgear < 0):
      self.currentgear = 0


      
    #adust speed based on current gear
    self.speed = self.gear[self.currentgear]
    #print ("Name: ", self.name, " Current Gear:",self.currentgear, " Speed: ",self.speed)
  
  
    return;  

  
  def Erase(self):
    setpixel(self.h,self.v,0,0,0)
    _show()
    #SendBufferPacket(RemoteDisplay,VIEW_H,VIEW_W)



  def AdjustSpeed(self, increment):
    speed = self.speed
    speed = self.speed + increment
    if (speed > 1000):
      speed = 1000
    elif (speed <= 1):
      speed = 1

    self.speed = speed
    return;






#------------------------------------------------------------------------------


def CheckElapsedTime(seconds):
  """Return 1 once per `seconds` wall-clock second (mod)."""
  try:
    return 1 if (int(time.time()) % max(1, int(seconds))) == 0 else 0
  except Exception:
    return 0


def _clock_upper_right_pos(ClockSprite):
  """Screen (h,v) for clock in the upper-right corner."""
  refresh_view_size()
  sw = int(getattr(ClockSprite, "width", 12) or 12)
  sh = int(getattr(ClockSprite, "height", 7) or 7)
  h = max(0, VIEW_W - sw - CLOCK_MARGIN_H)
  v = max(0, min(CLOCK_MARGIN_V, max(0, VIEW_H - sh)))
  return h, v


def position_clock_upper_right(ClockSprite):
  """Pin clock sprite to upper-right; keep always on."""
  try:
    h, v = _clock_upper_right_pos(ClockSprite)
    ClockSprite.h = h
    ClockSprite.v = v
    ClockSprite.on = 1
  except Exception:
    pass


def draw_clock_overlay(ClockSprite):
  """Draw dark backdrop + clock digits at upper-right (canvas already has map)."""
  try:
    sw = int(getattr(ClockSprite, "width", 12) or 12)
    sh_h = int(getattr(ClockSprite, "height", 7) or 7)
    sh, sv = _clock_upper_right_pos(ClockSprite)
    ClockSprite.h, ClockSprite.v = sh, sv
    _draw_dark_backdrop(
      LED.Canvas, sh, sv, sw, sh_h,
      alpha=CLOCK_BACKDROP_ALPHA,
      color=CLOCK_BACKDROP_RGB,
      pad=CLOCK_BACKDROP_PAD,
    )
    ClockSprite.Display(sh, sv)
  except Exception:
    pass


def CheckClockTimer(ClockSprite):
  """Keep clock always on in the upper-right (no slide / on-off cycle)."""
  try:
    if CLOCK_ALWAYS_ON:
      ClockSprite.on = 1
      position_clock_upper_right(ClockSprite)
      return 0
    # Legacy toggle path (unused when CLOCK_ALWAYS_ON)
    if not hasattr(ClockSprite, "StartTime") or ClockSprite.StartTime is None:
      ClockSprite.StartTime = time.time()
    elapsed_seconds = time.time() - ClockSprite.StartTime
    if getattr(ClockSprite, "on", 0) == 1:
      if elapsed_seconds >= ClockOnDuration and getattr(ClockSprite, "v", 0) <= -5:
        ClockSprite.on = 0
        ClockSprite.StartTime = time.time()
    else:
      if elapsed_seconds >= ClockOffDuration:
        ClockSprite.on = 1
        ClockSprite.StartTime = time.time()
    position_clock_upper_right(ClockSprite)
  except Exception:
    pass
  return 0


def MoveMessageSprite(moves_count, MessageSprite):
  """Slide message/clock sprite vertically (HD). Safe no-op if attrs missing."""
  try:
    m, r = divmod(moves_count, max(1, ClockSlideSpeed))
    if r != 0:
      return
    if not hasattr(MessageSprite, "v"):
      return
    # Ensure required attributes exist
    if not hasattr(MessageSprite, "DirectionIncrement"):
      MessageSprite.DirectionIncrement = 1
    if not hasattr(MessageSprite, "PausePositionV"):
      MessageSprite.PausePositionV = VIEW_H // 2
    if not hasattr(MessageSprite, "PauseTimerOn"):
      MessageSprite.PauseTimerOn = 0
    if not hasattr(MessageSprite, "Delay"):
      MessageSprite.Delay = 2
    if not hasattr(MessageSprite, "PauseStartTime"):
      MessageSprite.PauseStartTime = time.time()

    if MessageSprite.v == MessageSprite.PausePositionV:
      if MessageSprite.PauseTimerOn == 0:
        MessageSprite.PauseTimerOn = 1
        MessageSprite.PauseStartTime = time.time()
      elapsed_seconds = time.time() - MessageSprite.PauseStartTime
      if elapsed_seconds >= MessageSprite.Delay:
        if MessageSprite.DirectionIncrement >= 0:
          MessageSprite.DirectionIncrement = MessageSprite.DirectionIncrement * -1
        MessageSprite.v = MessageSprite.v + MessageSprite.DirectionIncrement
    else:
      MessageSprite.PauseTimerOn = 0
      MessageSprite.v = MessageSprite.v + MessageSprite.DirectionIncrement

    if MessageSprite.v >= MessageSprite.PausePositionV:
      MessageSprite.DirectionIncrement = MessageSprite.DirectionIncrement * -1

    height = getattr(MessageSprite, "height", 5)
    width = getattr(MessageSprite, "width", 10)
    if MessageSprite.v >= VIEW_H + 2 or (
        MessageSprite.v < (0 - height) and MessageSprite.DirectionIncrement < 0
    ):
      MessageSprite.h = (VIEW_W - width) // 2
      MessageSprite.v = 0 - height
      MessageSprite.on = 0
  except Exception:
    pass


#--          RallyDot                                                      --
#--                                                                        --
#--                                                                        --
#----------------------------------------------------------------------------




# - the player car will not move, but the maze around him will
# - the playfield contains all objects, including cars walls enemies and bullets
# - we loop through the playfield, examining each object
    # - ignore empty
    # - ignore walls
    # - if player/enemy then give it a turn to use radar to find nearby items
        # - make a decision on what to to
        # - decisions are priority based
        # - shoot opponent
        # - run
        # - hide
    # - we still  use a clock/speed value to see if a player/enemy object is going to make a decision this turn
# - objects off screen will still move, but will not be visible
# - draw window function will be used to display the current visible sqare in the map (8x8)    



        
# Active race map: 6 = original (80x144); 7 = map6 flipped 2x2 (160x288)
ACTIVE_MAP_LEVEL = 7

# Player gas tank (Rally-X style) — drains while driving, refilled by fuel dots
PLAYER_GAS_MAX = 450
PLAYER_GAS_DRAIN = 1          # per player move tick
PLAYER_GAS_REFILL = 70        # when eating a fuel pickup
OUT_OF_FUEL_HOLD_SEC = 2.0    # show red ring + label, then lose a life

# Stock lives (credits). PlayerCar.lives is hit-points within the current life.
PLAYER_STOCK_LIVES = 3
PLAYER_HEALTH_MAX = 100




def CreateRaceWorld(MapLevel):

  #The map is an array of a lists.  You can address each element has VH e.g. [V][H]
  #Copying the map to the playfield needs to follow the exact same shape


  if (MapLevel == 1):

    #Set world dimensions
    RaceWorld = GameWorld(name='Level1',
                          width        = 48,
                          height       = 64,
                          Map          = [[]],
                          Playfield    = [[]],
                          CurrentRoomH = 2,
                          CurrentRoomV = 2,
                          DisplayH=1,
                          DisplayV=1)
    
    #Populate Map
    RaceWorld.Map = []
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10,10, 9, 9, 9, 9,10, 9, 9,  9, 9,10, 9, 9, 9, 9, 9,10, 9, 9, 9, 9,10, 9, 9,  9, 9,10, 9, 9, 9, 9,10,10, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0,26,26,26,26,26,26,26, 26, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0,26,26,26,26,26, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0,26, 0, 0, 0, 0, 0, 0, 26, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0,26, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0,26, 0, 0, 0, 0, 0, 0, 26, 0, 0, 0,26,26,26,26,26,26,26,26,26,26,26, 0,  0, 0, 0,26, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0,26, 0,27,27,27,27, 0, 26, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,26, 0,  0, 0, 0,26, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0,26, 0,27,27,27,27, 0, 26, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,26, 0,  0, 0, 0,26, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0,26, 0, 0,28,28, 0, 0, 26, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,26, 0,  0, 0, 0,26, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
                                                                                                                                                                              
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0,26, 0, 0,27,27, 0, 0, 26, 0, 0, 0,26,26,26,26, 0, 0, 0, 0, 0, 0,26, 0,  0, 0, 0,26, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0,26, 0, 0, 0, 0, 0, 0, 26, 0, 0, 0,26, 0, 0,26, 0, 0, 0, 0, 0, 0,26, 0,  0, 0, 0,26, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0,26, 0, 0, 0, 0, 0, 0, 26, 0, 0, 0,26, 0, 0,26, 0, 0, 0, 0, 0, 0,26, 0,  0, 0, 0,26, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0,26, 0, 0, 0, 0, 0, 0, 26, 0, 0, 0,26, 0, 0,26, 0, 0, 0, 0, 0, 0,26, 0,  0, 0, 0,26, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0,26, 0, 0, 0, 0, 0, 0, 26, 0, 0, 0,26, 0, 0,26, 0, 0, 0, 0, 0, 0,26, 0,  0, 0, 0,26, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0,26,26, 0, 0,  0, 0, 0, 0,26, 0, 0,26, 0, 0, 0, 0, 0, 0,26, 0,  0, 0, 0,26, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0,26,13,13,26, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,26, 0,  0, 0, 0,26, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0,26,14,14,26, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,26, 0,  0,26,26,26,26,26, 0, 0,10, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0,26,15,15,26, 0,  0,26,26,26,26,26,26,26,26,26,26, 0, 0, 0,26, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0,26,15,15,26, 0,  0,26, 0, 0,26, 0, 0,26, 0, 0,26, 0, 0, 0,26, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0,26,14,14,26, 0,  0,26, 0, 0,26, 0, 0,26, 0, 0,26, 0, 0, 0,26, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0,26,13,13,26, 0,  0,26, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,26, 0,  0,26, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0,26,26, 0, 0,  0,26, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,26, 0,  0, 0,26, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0,26, 0, 0,26, 0, 0,26, 0, 0,26, 0, 0, 0,26, 0,  0, 0, 0,26, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0,26, 0, 0,26, 0, 0,26, 0, 0,26, 0, 0, 0,26, 0,  0, 0, 0, 0,26, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0,26,26,26,26,26,26,26,26,26,26, 0, 0, 0,26, 0,  0, 0, 0, 0, 0,26, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
                                                                                                                                                                              
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0,26, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25,25,25,25,25,25, 25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0,26, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25,21,22,23,22,21, 25, 0, 0,25, 0, 0,25,25,25,25,25, 0, 0, 0, 0, 0,  0, 0,26, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0,25,21,22,23,22,21, 25, 0, 0,25, 0, 0,25,26,26,26,25, 0, 0, 0, 0, 0,  0,26, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25,21,22,23,22,21, 25, 0, 0,25, 0, 0,25,27,27,27,25, 0, 0, 0, 0, 0,  0, 0,26, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25,25,25,25,25,25, 25, 0, 0,25, 0, 0,25,28,28,28,25, 0, 0, 0, 0, 0,  0, 0, 0,26, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0,25, 0, 0,25,27,27,27,25, 0, 0, 0, 0, 0,  0, 0, 0, 0,26, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0,25, 0, 0,25,26,26,26,25, 0, 0, 0,26, 0,  0, 0, 0, 0, 0,26, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0,25, 0, 0,25,25,25,25,25, 0, 0,26,26,26,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0,25, 0, 0, 0, 0, 0, 0,25, 0, 0, 0,26, 0,  0,26, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0,25,25,25,25,25,  0, 0, 0,25, 0, 0, 0, 0, 0, 0,25, 0, 0, 0, 0, 0,  0, 0,26, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0,25,18,19,18,25,  0, 0, 0,25, 0, 0, 0, 0, 0, 0,25, 0, 0, 0, 0, 0,  0, 0, 0,26, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0,25,18,19,18,25,  0, 0, 0,25, 0, 0, 0, 0, 0, 0,25, 0, 0, 0, 0, 0,  0, 0, 0, 0,26, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0,25,25,25,25,25,  0, 0, 0,25,25,25,25,25,25,25,25, 0, 0, 0,26, 0,  0, 0, 0, 0, 0,26, 0, 0,10, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,26,26,26,  0, 0, 0, 0,26, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,26, 0,  0, 0, 0,26, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
                                                                                                                                                                              
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0,26, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25,25,25,25,25,25, 25, 0, 0, 0,25,25,25,25,25,25,25, 0, 0, 0, 0, 0,  0,26, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0,25, 5, 6, 7, 6, 5, 25, 0, 0, 0,25,29,30,31,30,29,25, 0, 0, 0, 0, 0,  0, 0,26, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 5, 6, 7, 6, 5, 25, 0, 0, 0,25,29,30,31,30,20,25, 0, 0, 0,26, 0,  0, 0, 0,26, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 5, 6, 7, 6, 5, 25, 0, 0, 0,25,25,25,25,25,25,25, 0, 0,26,26,26,  0, 0, 0, 0,26, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25,25,25,25,25,25, 25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,26, 0,  0, 0, 0, 0, 0,26, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10,10, 9, 9, 9, 9,10, 9, 9,  9, 9,10, 9, 9, 9, 9,10,10, 9, 9, 9,10, 9, 9, 9,  9,10, 9, 9, 9, 9, 9,10,10, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])


    RaceWorld.CopyMapToPlayfield()




    
  
  if (MapLevel == 2):

    #Set world dimensions
    RaceWorld = GameWorld(name='Level1',
                          width        = 48,
                          height       = 64,
                          Map          = [[]],
                          Playfield    = [[]],
                          CurrentRoomH = 2,
                          CurrentRoomV = 2,
                          DisplayH=1,
                          DisplayV=1)
    
    #Populate Map
    RaceWorld.Map = []
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10,10, 9, 9, 9, 9,10, 9, 9,  9, 9,10, 9, 9, 9, 9, 9,10, 9, 9, 9, 9,10, 9, 9,  9, 9,10, 9, 9, 9, 9,10,10, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0,25,25, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0,25,26,26,25, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0,25,25,25,25, 25, 0, 0, 0, 0,25,27, 0, 0,27,25, 0, 0, 0, 0,25, 25,25,25,25, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0,25,26,27,26, 25,25,25,25,25,25, 0, 0, 0, 0,25,25,25,25,25,25, 26,27,26,25, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0,25,26,27,26, 25,25,25,25,25,25, 0, 0, 0, 0,25,25,25,25,25,25, 26,27,26,25, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0,25,25,25,25, 25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,25, 26,27,26,25, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,25, 25,25,25,25, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])

    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0,25,25,25,25, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0,26,25,25,25,25,25,25,26, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0,26,25,25,26, 0, 0, 0, 0,26,25,25,26, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0,25,25,26, 0, 0, 0, 0, 0, 0, 0, 0,26,25,25, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0,25,26, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,25, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0,25,25,26, 0, 0, 0, 0, 0, 0, 0, 0,26,25,25, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0,26,25,25,26, 0, 0, 0, 0,26,25,25,26, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0,26,25,25,25,25,25,25,26, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0,25,25,25,25, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])

    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0,25,26, 0,  0, 0, 0, 0, 0, 0, 0,25,25, 0, 0, 0, 0, 0, 0, 0,  0,26,25, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0,25,26, 0,  0, 0, 0, 0, 0, 0,25,25,25,25, 0, 0, 0, 0, 0, 0,  0,26,25, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0,25,26, 0,  0, 0, 0,25,25,25,25,25,25,25,25,25,25, 0, 0, 0,  0,26,25, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0,25,26, 0,  0, 0, 0,25,26,26,26,26,26,26,26,26,25, 0, 0, 0,  0,26,25, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0,25,26, 0,  0, 0, 0,25,26,27,27,27,27,27,27,26,25, 0, 0, 0,  0,26,25, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0,25,26, 0,  0, 0, 0,25,26,27,28,28,28,28,27,26,25, 0, 0, 0,  0,26,25, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0,25,25,25, 25,25,25,25,26,27,28,20,20,28,27,26,25,25,25,25, 25,25,25, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0,25,26,26, 26,26,26,25,26,27,28,20,20,28,27,26,25,26,26,26, 26,26,25, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0,25,26, 0,  0, 0, 0,25,26,27,28,28,28,28,27,26,25, 0, 0, 0,  0,26,25, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0,25,26, 0,  0, 0, 0,25,26,27,27,27,27,27,27,26,25, 0, 0, 0,  0,26,25, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0,25,26, 0,  0, 0, 0,25,26,26,26,26,26,26,26,26,25, 0, 0, 0,  0,26,25, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0,25,26, 0,  0, 0, 0,25,25,25,25,25,25,25,25,25,25, 0, 0, 0,  0,26,25, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0,25,26, 0,  0, 0, 0, 0, 0, 0,25,25,25,25, 0, 0, 0, 0, 0, 0,  0,26,25, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0,25,26, 0,  0, 0, 0, 0, 0, 0, 0,25,25, 0, 0, 0, 0, 0, 0, 0,  0,26,25, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])

    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,26,26, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0,26,26,26, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0,26,26, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,26,26, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0,26,26,26, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0,26,26, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10,10, 9, 9, 9, 9,10, 9, 9,  9, 9,10, 9, 9, 9, 9,10,10, 9, 9, 9,10, 9, 9, 9,  9,10, 9, 9, 9, 9, 9,10,10, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])


    RaceWorld.CopyMapToPlayfield()

    print (RaceWorld.Map[0])
    print (RaceWorld.Map[1])
    print (RaceWorld.Map[2])
    print (RaceWorld.Map[3])
  
    
    
  if (MapLevel == 3):
    #Set world dimentions
    RaceWorld = GameWorld(name='Level3',
                          width        = 40,
                          height       = 40,
                          Map          = [[]],
                          Playfield    = [[]],
                          CurrentRoomH = 2,
                          CurrentRoomV = 2,
                          DisplayH=8,
                          DisplayV=8)

    RaceWorld.Map = []
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  ])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  ])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  ])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  ])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  ])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  ])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  ])  
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10,10, 9, 9, 9,  9,10,10, 9, 9, 9, 9,10, 10, 9, 9, 9, 9,10,10, 9,  9, 9, 9,10,10, 9, 9, 9, 9, 9, 9, 9,  ])  
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,  ])  
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,  ])  
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,  ])  
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,  ])  
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0,25,25,25, 25,25, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0,25,25, 25,25,25, 0, 9, 9, 9, 9, 9, 9, 9, 9,  ])  
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0,  0, 0,25, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0,25, 0, 0,  0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9,  ])  
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0,  0, 0, 0,25, 0, 0, 0, 0,  0, 0, 0, 0,25, 0, 0, 0,  0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,  ])  
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0,  0, 0, 0,26,26,26,26, 0,  0,26,26,26,26, 0, 0, 0,  0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,  ])  

    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0,  0, 0,25,25,25,25,25, 0,  0,25,25,25,25,25, 0, 0,  0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,  ])  
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0,  0, 0,25, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0,25, 0, 0,  0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,  ])  
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0,  0, 0,25, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0,25, 0, 0,  0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9,  ])  
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0,  0, 0,25, 0, 0, 5, 5, 0,  0, 5, 5, 0, 0,25, 0, 0,  0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,  ])  
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0,  0, 0,25, 0, 0, 5, 7, 0,  0, 7, 5, 0, 0,25, 0, 0,  0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,  ])  
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9,25,25,25, 0,  0, 0,25, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0,25, 0, 0,  0,25,25,25, 9, 9, 9, 9, 9, 9, 9, 9,  ])  
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0,25, 0,  0, 0,25, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0,25, 0, 0,  0,25, 0, 0,10, 9, 9, 9, 9, 9, 9, 9,  ])  
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0,  0, 0,25, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0,25, 0, 0,  0,25, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,  ])  
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0,  0, 0,25,25,25,25,25, 0,  0, 0,25,25,25,25, 0, 0,  0,25, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,  ])  
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0,  0, 0, 0,26,26,26,26, 0,  0, 0,26,26,26, 0, 0, 0,  0,25, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,  ])  
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0,  0, 0, 0, 0, 0,26,26, 0,  0, 0,26,26, 0, 0, 0, 0,  0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,  ])  
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9,  ])  
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25,25, 25,25, 0, 0, 0, 0,17, 0,  0,17, 0, 0, 0, 0,25,25, 25,25, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,  ])  
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0,17, 0,  0,17, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,  ])  
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0,17, 0,  0,17, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,  ])  
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,  ])  

    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10,10, 9, 9, 9,  9,10,10, 9, 9, 9, 9,10, 10, 9, 9, 9, 9,10,10, 9,  9, 9, 9,10,10, 9, 9, 9, 9, 9, 9, 9,  ])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  ])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  ])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  ])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  ])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  ])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  ])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  ])

    RaceWorld.CopyMapToPlayfield()


  if (MapLevel == 4):

    #Set world dimensions
    RaceWorld = GameWorld(name='Level1',
                          width        = 48,
                          height       = 64,
                          Map          = [[]],
                          Playfield    = [[]],
                          CurrentRoomH = 1,
                          CurrentRoomV = 1,
                          DisplayH=1,
                          DisplayV=1)
    
    #Populate Map
    RaceWorld.Map = []
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10,10, 9, 9, 9, 9,10, 9, 9,  9, 9,10, 9, 9, 9, 9, 9,10, 9, 9, 9, 9,10, 9, 9,  9, 9,10, 9, 9, 9, 9,10,10, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])

    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0,25,26, 0,  0, 0, 0, 0, 0, 0, 0,25,25, 0, 0, 0, 0, 0, 0, 0,  0,26,25, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0,25,26, 0,  0, 0, 0, 0, 0, 0,25,25,25,25, 0, 0, 0, 0, 0, 0,  0,26,25, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0,25,26, 0,  0, 0, 0,25,25,25,25,25,25,25,25,25,25, 0, 0, 0,  0,26,25, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0,25,26, 0,  0, 0, 0,25,26,26,26,26,26,26,26,26,25, 0, 0, 0,  0,26,25, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0,25,26, 0,  0, 0, 0,25,26,27,27,27,27,27,27,26,25, 0, 0, 0,  0,26,25, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0,25,26, 0,  0, 0, 0,25,26,27,28,28,28,28,27,26,25, 0, 0, 0,  0,26,25, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0,25,25,25, 25,25,25,25,26,27,28,20,20,28,27,26,25,25,25,25, 25,25,25, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0,25,26,26, 26,26,26,25,26,27,28,20,20,28,27,26,25,26,26,26, 26,26,25, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0,25,26, 0,  0, 0, 0,25,26,27,28,28,28,28,27,26,25, 0, 0, 0,  0,26,25, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0,25,26, 0,  0, 0, 0,25,26,27,27,27,27,27,27,26,25, 0, 0, 0,  0,26,25, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0,25,26, 0,  0, 0, 0,25,26,26,26,26,26,26,26,26,25, 0, 0, 0,  0,26,25, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0,25,26, 0,  0, 0, 0,25,25,25,25,25,25,25,25,25,25, 0, 0, 0,  0,26,25, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0,25,26, 0,  0, 0, 0, 0, 0, 0,25,25,25,25, 0, 0, 0, 0, 0, 0,  0,26,25, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0,25,26, 0,  0, 0, 0, 0, 0, 0, 0,25,25, 0, 0, 0, 0, 0, 0, 0,  0,26,25, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])


    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0,25,26, 0,  0, 0, 0, 0, 0, 0, 0,25,25, 0, 0, 0, 0, 0, 0, 0,  0,26,25, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0,25,26, 0,  0, 0, 0, 0, 0, 0,25,25,25,25, 0, 0, 0, 0, 0, 0,  0,26,25, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0,25,26, 0,  0, 0, 0,25,25,25,25,25,25,25,25,25,25, 0, 0, 0,  0,26,25, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0,25,26, 0,  0, 0, 0,25,26,26,26,26,26,26,26,26,25, 0, 0, 0,  0,26,25, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0,25,26, 0,  0, 0, 0,25,26,27,27,27,27,27,27,26,25, 0, 0, 0,  0,26,25, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0,25,26, 0,  0, 0, 0,25,26,27,28,28,28,28,27,26,25, 0, 0, 0,  0,26,25, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0,25,25,25, 25,25,25,25,26,27,28,20,20,28,27,26,25,25,25,25, 25,25,25, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0,25,26,26, 26,26,26,25,26,27,28,20,20,28,27,26,25,26,26,26, 26,26,25, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0,25,26, 0,  0, 0, 0,25,26,27,28,28,28,28,27,26,25, 0, 0, 0,  0,26,25, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0,25,26, 0,  0, 0, 0,25,26,27,27,27,27,27,27,26,25, 0, 0, 0,  0,26,25, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0,25,26, 0,  0, 0, 0,25,26,26,26,26,26,26,26,26,25, 0, 0, 0,  0,26,25, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0,25,26, 0,  0, 0, 0,25,25,25,25,25,25,25,25,25,25, 0, 0, 0,  0,26,25, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0,25,26, 0,  0, 0, 0, 0, 0, 0,25,25,25,25, 0, 0, 0, 0, 0, 0,  0,26,25, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0,25,26, 0,  0, 0, 0, 0, 0, 0, 0,25,25, 0, 0, 0, 0, 0, 0, 0,  0,26,25, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])

    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10,10, 9, 9, 9, 9,10, 9, 9,  9, 9,10, 9, 9, 9, 9,10,10, 9, 9, 9,10, 9, 9, 9,  9,10, 9, 9, 9, 9, 9,10,10, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])

    RaceWorld.CopyMapToPlayfield()


    
  if (MapLevel == 5):
    #Set world dimentions
    RaceWorld = GameWorld(name='Level5',
                          width        = 48,
                          height       = 64,
                          Map          = [[]],
                          Playfield    = [[]],
                          CurrentRoomH = 2,
                          CurrentRoomV = 1,
                          DisplayH=1,
                          DisplayV=1)
    
    
        #Populate Map
    RaceWorld.Map = []
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10,10, 9, 9, 9, 9,10, 9, 9,  9, 9,10, 9, 9, 9, 9, 9,10, 9, 9, 9, 9,10, 9, 9,  9, 9,10, 9, 9, 9, 9,10,10, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
                                                                                                                                                                              
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0,25, 0, 0, 0, 0,25, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0,25,25, 0, 0, 0, 0,25,25, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0,25,26,25, 0, 0, 0, 0,25,26,25, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0,25,26,26,25, 0, 0, 0, 0,25,26,26,25, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0,25,26,26,26,25, 0, 0, 0, 0,25,26,26,26,25, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0, 25,26,26,27,26,25, 0, 0, 0, 0,25,26,27,26,26,25,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0, 25,26,26,26,26,25, 0, 0, 0, 0,25,26,26,26,26,25,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0, 25,25,25,25,25, 0, 0, 0, 0, 0, 0,25,25,25,25,25,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0, 25,25,25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,25,25,25,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0, 25,25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,25,25,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0, 25,25, 0,25,25, 0, 0, 0, 0, 0, 0,25,25, 0,25,25,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0, 25,25, 0,26,27, 0, 0, 0, 0, 0, 0,26,27, 0,25,25,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0, 25,25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,25,25,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0, 25,25, 0, 0, 0, 0,25,25,25,25, 0, 0, 0, 0,25,25,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0, 25,25, 0, 0, 0, 0,25,26,26,25, 0, 0, 0, 0,25,25,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0, 25,25, 0, 0, 0, 0,25,27,27,25, 0, 0, 0, 0,25,25,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
                                                                                                                                                                              
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0, 25,25, 0, 0, 0, 0,25,27,27,25, 0, 0, 0, 0,25,25,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0,25,25, 25,25, 0, 0, 0, 0,25,26,26,25, 0, 0, 0, 0,25,25, 25,25, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0,25,25, 25,25, 0, 0, 0, 0,25,25,25,25, 0, 0, 0, 0,25,25, 25,25, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0,25,25,25,25, 25,25, 0, 0, 0, 0, 0,25,25, 0, 0, 0, 0, 0,25,25, 25,25,25,25, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25,25,25,25,25, 0, 25,25, 0, 0, 0, 0, 0,25,25, 0, 0, 0, 0, 0,25,25,  0,25,25,25,25,25, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25,25, 0, 0, 0, 0, 25,25, 0, 0, 0, 0, 0,25,25, 0, 0, 0, 0, 0,25,25,  0, 0, 0, 0,25,25, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25,25, 0, 0, 0, 0, 25,25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,25,25,  0, 0, 0, 0,25,25, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,26,26, 0, 0, 0, 0, 25,25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,25,25,  0, 0, 0, 0,26,26, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0,26,26, 0, 0, 0, 0, 25,25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,25,25,  0, 0, 0, 0,26,26, 0, 0,10, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,27,27, 0, 0, 0, 0, 25,25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,25,25,  0, 0, 0, 0,27,27, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,27,27, 0, 0, 0, 0, 25,25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,25,25,  0, 0, 0, 0,27,27, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,28,28, 0, 0, 0, 0,  0,25,25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,25,25, 0,  0, 0, 0, 0,28,28, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0,25,25, 0, 0, 0, 0, 0, 0, 0, 0,25,25, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0,25,25, 0, 0, 0, 0, 0, 0,25,25, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0,25,25,25,25,25,25,25,25, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0,25,25,25,25,25,25, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])

    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10,10, 9, 9, 9, 9,10, 9, 9,  9, 9,10, 9, 9, 9, 9,10,10, 9, 9, 9,10, 9, 9, 9,  9,10, 9, 9, 9, 9, 9,10,10, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,])

    RaceWorld.CopyMapToPlayfield()


  if (MapLevel == 6):
    #Set world dimentions
    RaceWorld = GameWorld(name='Level6',
                          width        = 80,
                          height       = 144,
                          Map          = [[]],
                          Playfield    = [[]],
                          CurrentRoomH = 2,
                          CurrentRoomV = 1,
                          DisplayH=1,
                          DisplayV=1)
    
    
        #Populate Map
    RaceWorld.Map = []
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10,10, 9, 9, 9, 9,10, 9, 9,  9, 9,10, 9, 9, 9, 9, 9,10, 9, 9, 9, 9,10, 9, 9,  9, 9,10, 9, 9, 9, 9,10,10, 9, 9, 9, 9, 9, 9, 9,  9, 9,10, 9, 9, 9, 9, 9,10, 9, 9, 9, 9,10, 9, 9,  9, 9,10, 9, 9, 9, 9,10,10, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0,25, 0, 0, 0, 0, 0, 0, 0, 0,25,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0,25, 0, 0, 0, 0, 0, 0, 0, 0,25,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25,25,25,25,25,25, 25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,  0, 0, 0, 0, 0, 0,25, 0, 0, 0, 0, 0, 0, 0, 0,25, 25,25,25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0, 0, 0,25, 25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,25,  0, 0, 0, 0, 0, 0,25, 0, 0, 0,25, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0, 0, 0,25, 25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,25,  0, 0, 0, 0, 0, 0,25, 0, 0, 0,25, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0, 0, 0,25, 25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,25,  0, 0, 0, 0, 0, 0,25, 0, 0, 0,25, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0, 0, 0, 0,  0, 0, 0, 0,25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,25,  0, 0, 0, 0, 0, 0,25, 0, 0, 0,25, 0, 0, 0, 0,25, 25,25,25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0,25, 0, 0, 0, 0, 0,  0, 0, 0, 0,25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,25,  0, 0, 0, 0, 0, 0,25, 0, 0, 0,25, 0, 0, 0, 0,25,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
                                                                                                                                                                                                                                                                               
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0,25, 0, 0, 0, 0, 0,  0, 0, 0, 0,25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,25,  0, 0, 0, 0, 0, 0,25, 0, 0, 0,25, 0, 0, 0, 0,25,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0,25,25, 0,  0, 0, 0, 0,25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,25,  0, 0, 0, 0, 0, 0,25, 0, 0, 0,25, 0, 0, 0, 0,25,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0,25, 0, 0,  0, 0,25,25,25,25,25,25,25,25,25,25, 0, 0, 0,25,  0, 0, 0, 0, 0, 0,25,25,25,25,25, 0, 0, 0, 0,25,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0,25, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,25, 0, 0, 0, 0, 0, 0,25,  0, 0, 0, 0, 0, 0,25, 0, 0, 0, 0, 0, 0, 0, 0,25,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0,25, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,25, 0, 0, 0, 0, 0, 0,25,  0, 0, 0, 0, 0, 0,25, 0, 0, 0, 0, 0, 0, 0, 0,25,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0,25, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,25, 0, 0, 0, 0, 0, 0,25,  0, 0, 0, 0, 0, 0,25, 0, 0, 0, 0, 0, 0, 0, 0,25,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0,25, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,25, 0, 0, 0, 0, 0, 0,25,  0, 0, 0, 0, 0, 0,25, 0, 0, 0, 0, 0, 0, 0, 0,25,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0,25, 0, 0,25, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,25, 0, 0, 0, 0, 0, 0,25,  0, 0, 0, 0, 0, 0,25, 0, 0, 0, 0, 0, 0, 0, 0,25,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0,25, 0, 0,25, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,25, 0, 0, 0, 0, 0, 0,25,  0, 0, 0, 0, 0, 0,25,25,25,25,25,25,25,25,25,25,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0,25, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,25, 0, 0, 0, 0, 0, 0,25,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0,25, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0,25, 0, 0, 0, 0, 0,25,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0,25, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0,25, 0, 0, 0, 0,25,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0,25, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,25, 0, 0, 0,25,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0,25, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,25, 0, 0,25,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0,25, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,25, 0,25,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0,25, 0, 0,25,25,25,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,25,25,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
                                                                                                                                                                                                                                                                               
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0,25, 0, 0, 0, 0, 0,  0, 0,25,25,25,25,25,25,25,25, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0, 0, 0, 0,  0, 0,25, 0, 0, 0, 0, 0, 0,25, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0, 0, 0, 0,  0, 0,25, 0, 0, 0, 0, 0, 0,25, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0, 0, 0, 0,  0, 0,25, 0, 0, 0, 0, 0, 0,25, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0, 0, 0, 0,  0, 0,25, 0, 0, 0, 0, 0, 0,25, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0, 0, 0, 0,  0, 0,25, 0, 0, 0, 0, 0, 0,25, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0, 0, 0, 0,  0, 0,25, 0, 0, 0, 0, 0, 0,25,25, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0,25, 0, 0, 0, 0, 0,  0, 0,25, 0, 0, 0, 0, 0, 0, 0, 0,25, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0,25, 0, 0, 0, 0, 0,  0, 0,25, 0, 0, 0, 0, 0, 0, 0, 0, 0,25, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0, 0, 0, 0,  0, 0,25,25,25,25,25,25, 0, 0, 0, 0, 0,25, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0,25, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,25, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0,25, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0,25, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0,25, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
                                                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                                                               
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0,25, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,25, 25,25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,25,  5,25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0, 0, 0, 0,  0, 0,25,25,25,25,25, 0, 0, 0, 0, 0, 0, 0, 0,25,  5,25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0, 0, 0, 0,  0, 0,25,26,27,26,25, 0, 0, 0, 0, 0, 0, 0, 0,25,  5,25, 0, 0, 0, 0, 0, 0,25,25,25, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25,25,25,25, 0, 0,  0, 0,25,26,27,26,25, 0, 0, 0, 0, 0, 0, 0, 0,25,  5,25, 0, 0, 0, 0, 0,25,26,26,26,25, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25,25,25,25, 0, 0,  0, 0,25,26,27,26,25,25,25,25,25,25,25,25,25,25,  5,25, 0, 0, 0, 0,25,26,27,27,27,26,25, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0,25, 0, 0, 0, 0, 0,  0, 0,25,26,27,26,26,26,26,26,26,26,26,26,26,26,  5,25, 0, 0, 0,25,26,27,28,28,28,27,26,25, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0,25, 0, 0, 0, 0, 0,  0, 0,25,26,27,26,26,26,26,26,26,26,26,26,26,26,  5,25, 0, 0, 0,25,26,27,28, 4,28,27,26,25, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0, 0, 0, 0,  0, 0,25,26,27,26,25,25,25,25,25,25,25,25,25,25,  5,25, 0, 0, 0,25,26,27,28, 4,28,27,26,25, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0, 0, 0, 0,  0, 0,25,26,27,26,25, 0, 0, 0, 0, 0, 0, 0, 0,25,  5,25, 0, 0, 0,25,26,27,28, 4,28,27,26,25, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0, 0, 0, 0,  0, 0,25,26,27,26,25, 0, 0, 0, 0, 0, 0, 0, 0,25,  5,25, 0, 0, 0,25,26,27,28,28,28,27,26,25, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0, 0, 0, 0,  0, 0,25,26,27,26,25, 0, 0, 0, 0, 0, 0, 0, 0,25, 25,25, 0, 0, 0, 0,25,26,27,27,27,26,25, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0, 0, 0, 0,  0, 0,25,25,25,25,25, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0,25,26,26,26,25, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,25,25,25, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0,25, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
                                                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                                                               
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0,25, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,25,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,25,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,25,25,25, 25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,25,  0, 0, 0, 0, 0, 0, 0, 0, 0,25,25,25,25, 0, 0, 0, 25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0, 0, 0, 0, 25,25,25,25,25,25,25,25, 0, 0, 0, 0, 0, 0, 0,25,  0, 0, 0, 0, 0,25,25,25,25, 0, 0, 0, 0, 0, 0, 0, 25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0,25, 0, 0, 0, 0, 0, 0, 0,25,  0, 0, 0, 0, 0,25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0,25, 0, 0, 0, 0, 0, 0, 0,25,  0, 0, 0, 0, 0,25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0,25, 0, 0, 0, 0, 0, 0, 0,25,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0,25, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0,25, 0, 0, 0, 0, 0, 0, 0,25,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0,25, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0,25, 0, 0, 0, 0, 0, 0, 0,25,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0,25, 0, 0, 0, 0, 0, 0, 0,25,  0, 0, 0, 0, 0,25, 0, 0, 0, 0, 0, 0, 0,25,25,25, 25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0, 0, 0, 0,  0, 0, 0,25,25,25,25,25,25,25,25,25,25, 0, 0,25,  0, 0, 0, 0, 0,25, 0, 0, 0,25,25,25,25, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0, 0, 0, 0,  0, 0, 0,25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,25,  0, 0, 0, 0, 0,25,25,25,25, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0, 0, 0, 0,  0, 0, 0,25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,25,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0, 0, 0, 0,  0, 0, 0,25, 0, 0, 0, 0,25,25,25,25,25, 0, 0,25,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0, 0, 0, 0,  0, 0, 0,25, 0, 0, 0, 0,25, 0, 0, 0, 0, 0, 0,25,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0,25, 0, 0, 0, 0, 0,  0, 0, 0,25, 0, 0, 0, 0,25, 0, 0, 0, 0, 0, 0,25,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
                                                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                                                               
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0,25, 0, 0, 0,25,25, 25,25,25,25, 0, 0, 0, 0,25,25,25, 0, 0, 0, 0,25,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0, 0,25, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0,25, 0, 0, 0, 0,25,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0, 0,25, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0,25, 0, 0, 0, 0,25,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0, 0,25, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0,25, 0, 0, 0, 0,25,  0, 0, 0, 0,25,25,25,25,25, 0, 0, 0, 0, 0, 0, 0,  0, 0,25,25,25,25,25, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0, 0,25, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0,25, 0, 0, 0, 0,25,  0, 0, 0, 0,25,18,19,20,19,25,25,25,25, 0, 0, 0,  0, 0,25, 6, 6, 6,25, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0, 0,25,25, 25,25,25,25,25,25,25,25,25,25,25, 0, 0, 0, 0,25,  0, 0, 0, 0,25,18,19,20,19,18,18,18,18,25,25,25,  0, 0,25, 6, 7, 6,25, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,25,  0, 0, 0, 0,25,18,19,20,20,20,20,20,20,20,20, 0, 25,25,25, 6, 8, 6,25, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0,25, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,25,  0, 0, 0, 0,25,18,19,20,19,18,18,18,18,25,25,25,  0, 0,25, 6, 7, 6,25, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0,25, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,25,  0, 0, 0, 0,25,18,19,20,19,25,25,25,25, 0, 0, 0,  0, 0,25, 6, 6, 6,25, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,25,  0, 0, 0, 0,25,25,25,25,25, 0, 0, 0, 0, 0, 0, 0,  0, 0,25,25,25,25,25, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0,25,25,25,25,25,25, 25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0,25,25,25,25,25,25,25,25,25,25,25,25, 25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25, 25,25, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
                                                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                                                               
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0,25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0,25, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0,25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0,25, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0,25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5, 5, 0, 0,  0,25, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9,25,25,25,25,25,25,25,25, 25,25,25,25,25,25,25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 25,25,25,25,25, 0, 0, 0,18,18,18,18,18,18,18, 0,  0, 0, 0, 0, 0, 0, 0,18,18,18,18,18,18,18, 0, 0,  0,25, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9,25,26,26,26,26,26,26,26, 26,26,26,26,26,26,25, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,18, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,18, 0, 0, 0,  0,25, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9,25,26, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0,26,25, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,18, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,18, 0, 0, 0, 0,  0,25, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9,25,26, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0,26,25, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,18, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,18, 0, 0, 0, 0,  0,25, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10,25,26, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0,26,25, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,18, 0, 0, 0,  0,18,18,18,18,18,18, 0, 0, 0,18, 0, 0, 0, 0, 0,  0,25, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10,25,26, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0,26,25, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,18,18, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0,18, 0, 0, 0, 0, 0,  0,25, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9,25,26, 0, 0,15,15,15,15, 15,15,15, 0, 0,26,25, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,18, 0,18, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0,18, 0, 0, 0, 0, 0, 0,  0,25, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9,25,26, 0, 0,15,14,14,14, 14,14,15, 0, 0,26,25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 25,25,25,25,25, 0, 0, 0, 0, 0,18, 0, 0, 0,18, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0,18, 0, 0, 0, 0, 0, 0,  0,25, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9,25,26, 0, 0,15,14,13,13, 13,14,15, 0, 0,26,25, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0,25, 0, 0, 0, 0,18, 0, 0, 0, 0, 0,18,  0, 0, 0, 0, 0, 0, 0, 0,18, 0, 0, 0, 0, 0, 0, 0,  0,25, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9,25,26, 0, 0,15,14,13,13, 13,14,15, 0, 0,26,25, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0,25, 0, 0, 0,18, 0, 0, 0, 0, 0, 0, 0, 18, 0, 0, 0, 0, 0, 0,18, 0, 0, 0, 0, 0, 0, 0, 0,  0,25, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9,25,26, 0, 0,15,14,13,13, 13,14,15, 0, 0,26,25, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0,25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0,25, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9,25,26, 0, 0,15,14,13,13, 13,14,15, 0, 0,26,25, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0,25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0,25, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10,25,26, 0, 0,15,14,13,13, 13,14,15, 0, 0,26,25, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0,25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0,25, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
                                                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                                                               
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10,25,26, 0, 0,15,14,13,13, 13,14,15, 0, 0,26,25, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0,25,25,25,25,25,25,25,25,25,25,25,25, 25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25, 25,25, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9,25,26, 0, 0,15,14,13,13, 13,14,15, 0, 0,26,25, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,25,26,26,26,25, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9,25,26, 0, 0,15,14,13,13, 13,14,15, 0, 0,26,25, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,25,26,26,26,25, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9,25,26, 0, 0,15,14,13,13, 13,14,15, 0, 0,26,25, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,25,25,25,25,25, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9,25,26, 0, 0,15,14,13,13, 13,14,15, 0, 0,26,25, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9,25,26, 0, 0,15,14,13,13, 13,14,15, 0, 0,26,25, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0,25,25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0,25,25, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9,25,26, 0, 0,15,14,13,13, 13,14,15, 0, 0,26,25, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0,25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0,25, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10,25,26, 0, 0,15,14,13,13, 13,14,15, 0, 0,26,25, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0,25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0,25, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10,25,26, 0, 0,15,14,14,14, 14,14,15, 0, 0,26,25, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0,25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0,25, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9,25,26, 0, 0,15,15,15,15, 15,15,15, 0, 0,26,25, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0,25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0,25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0,25, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9,25,26, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0,26,25, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0,25,26,25, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0,25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0,25, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9,25,26, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0,26,25, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0,25,26,26,26,25, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0,25, 0, 0, 0,25,25,25,25,25,25,25,25,25,25,  0, 0, 0,25, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9,25,26, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0,26,25, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0,25,26,26,27,26,26,25, 0, 0, 0, 0, 0, 0, 0,  0, 0,25, 0, 0, 0,25, 0, 0, 0, 0, 0, 0, 0, 0,25,  0, 0, 0,25, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9,25,26, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0,26,25, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0,25,26,26,27,28,27,26,26,25, 0, 0, 0, 0, 0, 0,  0, 0,25, 0, 0, 0,25, 0, 0, 0, 0, 0, 0, 0, 0,25,  0, 0, 0,25, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9,25,26,26,26,26, 0, 0, 0, 26,26,26,26,26,26,25, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0,25,26,26,27,26,26,25, 0, 0, 0, 0, 0, 0, 0,  0, 0,25, 0, 0, 0,25, 0, 0, 0, 0, 0, 0, 0, 0,25,  0, 0, 0,25, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10,25,25,25,25,25, 0, 0, 0, 25,25,25,25,25,25,25, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0,25,26,26,26,25, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0,25, 0, 0, 0,25, 0, 0, 0, 0, 0, 0, 0, 0,25,  0, 0, 0,25, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
                                                                                                                                                                                                                                                                               
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0,25,25, 0, 0, 0, 25,25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0,25,26,25, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0,25,25,25,25,25, 0, 0, 0, 0, 0, 0, 0, 0,25, 25,25,25,25, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0,25,25, 0, 0, 0, 25,25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0,25, 0, 0, 0, 0,25, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0,25,25, 0, 0, 0, 25,25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0,25,25, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0,25, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0,25, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0,25,25,25, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0,25,25,25, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0,25,25,25, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0,25,25,25,25, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,25,25,25,25,25, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,25,25,25,25,25, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0,25,25,25,25,25, 0,  0, 0, 0, 0, 0, 0, 0,25,25,25,25,25,25,25, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0,25,25,25,25,25,25,25, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0,25,25,25,25,25,25,  0, 0, 0, 0, 0, 0,25,25,25,25,25,25,25,25,25, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0,25,25,25,25,25,25,25,25,25, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0,25,25,25,25,25,25, 25, 0, 0, 0, 0,25,25,25,25,25,25,25,25,25,25,25,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10,10, 9, 9, 9, 9,10, 9, 9,  9, 9,10, 9, 9, 9, 9, 9,10, 9, 9, 9, 9,10, 9, 9,  9, 9,10, 9, 9, 9, 9,10,10, 9, 9, 9, 9, 9, 9, 9,  9, 9,10, 9, 9, 9, 9, 9,10, 9, 9, 9, 9,10, 9, 9,  9, 9,10, 9, 9, 9, 9,10,10, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9])
                                                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                                                               

    RaceWorld.CopyMapToPlayfield()


    
    
  if (MapLevel == 99):
    #Set world dimentions
    RaceWorld = GameWorld(name='Level6',
                          width        = 80,
                          height       = 144,
                          Map          = [[]],
                          Playfield    = [[]],
                          CurrentRoomH = 2,
                          CurrentRoomV = 1,
                          DisplayH=1,
                          DisplayV=1)
    
    
        #Populate Map
    RaceWorld.Map = []
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10,10, 9, 9, 9, 9,10, 9, 9,  9, 9,10, 9, 9, 9, 9, 9,10, 9, 9, 9, 9,10, 9, 9,  9, 9,10, 9, 9, 9, 9,10,10, 9, 9, 9, 9, 9, 9, 9,  9, 9,10, 9, 9, 9, 9, 9,10, 9, 9, 9, 9,10, 9, 9,  9, 9,10, 9, 9, 9, 9,10,10, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
                                                                                                                                                                                                                                                                               
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
                                                                                                                                                                                                                                                                               
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
                                                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                                                               
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
                                                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                                                               
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
                                                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                                                               
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
                                                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                                                               
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
                                                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                                                               
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
                                                                                                                                                                                                                                                                               
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0,10, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9,10,10, 9, 9, 9, 9,10, 9, 9,  9, 9,10, 9, 9, 9, 9, 9,10, 9, 9, 9, 9,10, 9, 9,  9, 9,10, 9, 9, 9, 9,10,10, 9, 9, 9, 9, 9, 9, 9,  9, 9,10, 9, 9, 9, 9, 9,10, 9, 9, 9, 9,10, 9, 9,  9, 9,10, 9, 9, 9, 9,10,10, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9])
    RaceWorld.Map.append([  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,  9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9])
                                                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                                                               

    RaceWorld.CopyMapToPlayfield()

  if (MapLevel == 7):
    # Map 7: map6 2x2 flips; ~50% of green seam tunnels closed
    RaceWorld = GameWorld(name='Level7',
                          width        = 160,
                          height       = 288,
                          Map          = [[]],
                          Playfield    = [[]],
                          CurrentRoomH = 2,
                          CurrentRoomV = 1,
                          DisplayH=1,
                          DisplayV=1)
    RaceWorld.Map = []
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 10,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9, 10,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25, 25, 25, 25, 25, 25,   25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25,    0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0, 25,   25, 25, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 25, 25,   25,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,   25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25,   25, 25, 25, 25, 25, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0, 25,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0, 25,  0,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,   25,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0, 25,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0, 25,  0,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,   25,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0, 25,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0, 25,  0,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,   25,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0, 25,  0,  0,  0, 25,  0,  0,  0,  0, 25,   25, 25, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 25, 25,   25,  0,  0,  0,  0, 25,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0, 25,  0,  0,  0, 25,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0, 25,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0, 25,  0,  0,  0, 25,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0, 25,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0, 25, 25,  0,    0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0, 25,  0,  0,  0, 25,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0, 25,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,    0, 25, 25,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0, 25,  0,  0,    0,  0, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0, 25, 25, 25, 25, 25,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0, 25, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25,  0,  0,    0,  0, 25,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 10,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9, 10,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25, 25, 25, 25, 25, 25, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0, 25, 25, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 10,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9, 10,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25, 25, 25,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0, 25, 25, 25, 25, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 10,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9, 10,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0, 25, 25, 25, 25, 25, 25, 25, 25,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0,  0,  0,  0,  0, 25, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25, 25,  0,  0,  0,  0,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0, 25, 25, 25, 25, 25, 25,  0,  0,  0,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0,  0,  0,  0, 25, 25, 25, 25, 25, 25,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 10,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9, 10,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,   25, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 25,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,    5, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  5,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0, 25, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,  0,  0, 25,    5, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  5,   25,  0,  0,  0,  0,  0,  0,  0,  0, 25, 25, 25, 25, 25,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0, 25, 26, 27, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0, 25,    5, 25,  0,  0,  0,  0,  0,  0, 25, 25, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25, 25, 25,  0,  0,  0,  0,  0,  0, 25,  5,   25,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26, 27, 26, 25,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25, 25, 25, 25,  0,  0,    0,  0, 25, 26, 27, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0, 25,    5, 25,  0,  0,  0,  0,  0, 25, 26, 26, 26, 25,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0, 25, 26, 26, 26, 25,  0,  0,  0,  0,  0, 25,  5,   25,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26, 27, 26, 25,  0,  0,    0,  0, 25, 25, 25, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25, 25, 25, 25,  0,  0,    0,  0, 25, 26, 27, 26, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25,    5, 25,  0,  0,  0,  0, 25, 26, 27, 27, 27, 26, 25,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0, 25, 26, 27, 27, 27, 26, 25,  0,  0,  0,  0, 25,  5,   25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 26, 27, 26, 25,  0,  0,    0,  0, 25, 25, 25, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0, 25, 26, 27, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26,    5, 25,  0,  0,  0, 25, 26, 27, 28, 28, 28, 27, 26, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 10,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9, 10,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25, 26, 27, 28, 28, 28, 27, 26, 25,  0,  0,  0, 25,  5,   26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 27, 26, 25,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0, 25, 26, 27, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26,    5, 25,  0,  0,  0, 25, 26, 27, 28,  4, 28, 27, 26, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 10,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9, 10,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25, 26, 27, 28,  4, 28, 27, 26, 25,  0,  0,  0, 25,  5,   26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 27, 26, 25,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0, 25, 26, 27, 26, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25,    5, 25,  0,  0,  0, 25, 26, 27, 28,  4, 28, 27, 26, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25, 26, 27, 28,  4, 28, 27, 26, 25,  0,  0,  0, 25,  5,   25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 26, 27, 26, 25,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0, 25, 26, 27, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0, 25,    5, 25,  0,  0,  0, 25, 26, 27, 28,  4, 28, 27, 26, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25, 26, 27, 28,  4, 28, 27, 26, 25,  0,  0,  0, 25,  5,   25,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26, 27, 26, 25,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0, 25, 26, 27, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0, 25,    5, 25,  0,  0,  0, 25, 26, 27, 28, 28, 28, 27, 26, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25, 26, 27, 28, 28, 28, 27, 26, 25,  0,  0,  0, 25,  5,   25,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26, 27, 26, 25,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0, 25, 26, 27, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0, 25,   25, 25,  0,  0,  0,  0, 25, 26, 27, 27, 27, 26, 25,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0, 25, 26, 27, 27, 27, 26, 25,  0,  0,  0,  0, 25, 25,   25,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26, 27, 26, 25,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0, 25, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0, 25, 26, 26, 26, 25,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0, 25, 26, 26, 26, 25,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 25, 25, 25, 25,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 25, 25, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25, 25, 25,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 25, 25,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,   25, 25, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 25, 25, 25,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,   25, 25, 25, 25, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0, 25, 25, 25, 25,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0, 25, 25, 25, 25, 25, 25, 25, 25,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 10,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9, 10,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0, 25, 25, 25,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,   25, 25, 25,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25,  0,  0, 25,    0,  0,  0,  0,  0, 25,  0,  0,  0, 25, 25, 25, 25,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0, 25, 25, 25, 25,  0,  0,  0, 25,  0,  0,  0,  0,  0,   25,  0,  0, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0, 25, 25, 25, 25,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0, 25,  0,  0,  0,  0, 25, 25, 25, 25, 25,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0, 25, 25, 25, 25, 25,  0,  0,  0,  0, 25,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0, 25,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0, 25,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0, 25,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 10,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9, 10,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0, 25,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0, 25, 25,   25, 25, 25, 25,  0,  0,  0,  0, 25, 25, 25,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 10,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9, 10,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0, 25, 25, 25,  0,  0,  0,  0, 25, 25, 25, 25,   25, 25,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0, 25,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0, 25,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0, 25,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0, 25,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0, 25,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0, 25,    0,  0,  0,  0, 25, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 25, 25, 25, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0, 25, 25, 25, 25, 25,  0,  0,  0,  0,   25,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0, 25,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0, 25,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0, 25,    0,  0,  0,  0, 25, 18, 19, 20, 19, 25, 25, 25, 25,  0,  0,  0,    0,  0, 25,  6,  6,  6, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  6,  6,  6, 25,  0,  0,    0,  0,  0, 25, 25, 25, 25, 19, 20, 19, 18, 25,  0,  0,  0,  0,   25,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0, 25,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0, 25, 25,   25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25,  0,  0,  0,  0, 25,    0,  0,  0,  0, 25, 18, 19, 20, 19, 18, 18, 18, 18, 25, 25, 25,    0,  0, 25,  6,  7,  6, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  6,  7,  6, 25,  0,  0,   25, 25, 25, 18, 18, 18, 18, 19, 20, 19, 18, 25,  0,  0,  0,  0,   25,  0,  0,  0,  0, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25,   25, 25,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0, 25, 18, 19, 20, 20, 20, 20, 20, 20, 20, 20,  0,   25, 25, 25,  6,  8,  6, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  6,  8,  6, 25, 25, 25,    0, 20, 20, 20, 20, 20, 20, 20, 20, 19, 18, 25,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0, 25, 18, 19, 20, 19, 18, 18, 18, 18, 25, 25, 25,    0,  0, 25,  6,  7,  6, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  6,  7,  6, 25,  0,  0,   25, 25, 25, 18, 18, 18, 18, 19, 20, 19, 18, 25,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0, 25, 18, 19, 20, 19, 25, 25, 25, 25,  0,  0,  0,    0,  0, 25,  6,  6,  6, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  6,  6,  6, 25,  0,  0,    0,  0,  0, 25, 25, 25, 25, 19, 20, 19, 18, 25,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0, 25, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 25, 25, 25, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0, 25, 25, 25, 25, 25,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25, 25, 25, 25, 25, 25,   25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25,   25, 25, 25, 25, 25, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25,   25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25,   25, 25,  0,  0,  0,  0,  0,  0, 10,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9, 10,  0,  0,  0,  0,  0,  0, 25, 25,   25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25,   25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0, 25,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0, 25,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0, 25,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0, 25,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  5,  5,  0,  0,    0, 25,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0, 25,  0,    0,  0,  5,  5,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 25, 25, 25, 25, 25, 25, 25,   25, 25, 25, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25, 25, 25, 25, 25,  0,  0,  0, 18, 18, 18, 18, 18, 18, 18,  0,    0,  0,  0,  0,  0,  0,  0, 18, 18, 18, 18, 18, 18, 18,  0,  0,    0, 25,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0, 25,  0,    0,  0, 18, 18, 18, 18, 18, 18, 18,  0,  0,  0,  0,  0,  0,  0,    0, 18, 18, 18, 18, 18, 18, 18,  0,  0,  0, 25, 25, 25, 25, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 25, 25, 25, 25, 25, 25,   25, 25, 25, 25, 25, 25, 25, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26, 26, 26, 26, 26, 26, 26,   26, 26, 26, 26, 26, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 18,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 18,  0,  0,  0,    0, 25,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0, 25,  0,    0,  0,  0, 18,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0, 18,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26, 26, 26, 26, 26, 26,   26, 26, 26, 26, 26, 26, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 18,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 18,  0,  0,  0,  0,    0, 25,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0, 25,  0,    0,  0,  0,  0, 18,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 18,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 18,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 18,  0,  0,  0,  0,    0, 25,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0, 25,  0,    0,  0,  0,  0, 18,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 18,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 18,  0,  0,  0,    0, 18, 18, 18, 18, 18, 18,  0,  0,  0, 18,  0,  0,  0,  0,  0,    0, 25,  0,  0,  0,  0,  0,  0, 10,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9, 10,  0,  0,  0,  0,  0,  0, 25,  0,    0,  0,  0,  0,  0, 18,  0,  0,  0, 18, 18, 18, 18, 18, 18,  0,    0,  0,  0, 18,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 18, 18,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 18,  0,  0,  0,  0,  0,    0, 25,  0,  0,  0,  0,  0,  0, 10,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9, 10,  0,  0,  0,  0,  0,  0, 25,  0,    0,  0,  0,  0,  0, 18,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0, 18, 18,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26,  0,  0, 15, 15, 15, 15,   15, 15, 15,  0,  0, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 18,  0, 18,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 18,  0,  0,  0,  0,  0,  0,    0, 25,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0, 25,  0,    0,  0,  0,  0,  0,  0, 18,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 18,  0, 18,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26,  0,  0, 15, 15, 15,   15, 15, 15, 15,  0,  0, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26,  0,  0, 15, 14, 14, 14,   14, 14, 15,  0,  0, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25, 25, 25, 25, 25,  0,  0,  0,  0,  0, 18,  0,  0,  0, 18,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 18,  0,  0,  0,  0,  0,  0,    0, 25,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0, 25,  0,    0,  0,  0,  0,  0,  0, 18,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0, 18,  0,  0,  0, 18,  0,  0,  0,  0,  0, 25, 25, 25, 25, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26,  0,  0, 15, 14, 14,   14, 14, 14, 15,  0,  0, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26,  0,  0, 15, 14, 13, 13,   13, 14, 15,  0,  0, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0, 25,  0,  0,  0,  0, 18,  0,  0,  0,  0,  0, 18,    0,  0,  0,  0,  0,  0,  0,  0, 18,  0,  0,  0,  0,  0,  0,  0,    0, 25,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0, 25,  0,    0,  0,  0,  0,  0,  0,  0, 18,  0,  0,  0,  0,  0,  0,  0,  0,   18,  0,  0,  0,  0,  0, 18,  0,  0,  0,  0, 25,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26,  0,  0, 15, 14, 13,   13, 13, 14, 15,  0,  0, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26,  0,  0, 15, 14, 13, 13,   13, 14, 15,  0,  0, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0, 25,  0,  0,  0, 18,  0,  0,  0,  0,  0,  0,  0,   18,  0,  0,  0,  0,  0,  0, 18,  0,  0,  0,  0,  0,  0,  0,  0,    0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,    0,  0,  0,  0,  0,  0,  0,  0, 18,  0,  0,  0,  0,  0,  0, 18,    0,  0,  0,  0,  0,  0,  0, 18,  0,  0,  0, 25,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26,  0,  0, 15, 14, 13,   13, 13, 14, 15,  0,  0, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26,  0,  0, 15, 14, 13, 13,   13, 14, 15,  0,  0, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26,  0,  0, 15, 14, 13,   13, 13, 14, 15,  0,  0, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26,  0,  0, 15, 14, 13, 13,   13, 14, 15,  0,  0, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26,  0,  0, 15, 14, 13,   13, 13, 14, 15,  0,  0, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26,  0,  0, 15, 14, 13, 13,   13, 14, 15,  0,  0, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26,  0,  0, 15, 14, 13,   13, 13, 14, 15,  0,  0, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26,  0,  0, 15, 14, 13, 13,   13, 14, 15,  0,  0, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25,   25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25,   25, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 25,   25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25,   25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26,  0,  0, 15, 14, 13,   13, 13, 14, 15,  0,  0, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26,  0,  0, 15, 14, 13, 13,   13, 14, 15,  0,  0, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 25, 26, 26, 26, 25,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0, 25, 26, 26, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26,  0,  0, 15, 14, 13,   13, 13, 14, 15,  0,  0, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26,  0,  0, 15, 14, 13, 13,   13, 14, 15,  0,  0, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 25, 26, 26, 26, 25,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0, 25, 26, 26, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26,  0,  0, 15, 14, 13,   13, 13, 14, 15,  0,  0, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26,  0,  0, 15, 14, 13, 13,   13, 14, 15,  0,  0, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 25, 25, 25, 25, 25,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0, 25, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26,  0,  0, 15, 14, 13,   13, 13, 14, 15,  0,  0, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26,  0,  0, 15, 14, 13, 13,   13, 14, 15,  0,  0, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26,  0,  0, 15, 14, 13,   13, 13, 14, 15,  0,  0, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26,  0,  0, 15, 14, 13, 13,   13, 14, 15,  0,  0, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0, 25, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0, 25, 25,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0, 25, 25,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 25,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26,  0,  0, 15, 14, 13,   13, 13, 14, 15,  0,  0, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26,  0,  0, 15, 14, 13, 13,   13, 14, 15,  0,  0, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0, 25,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0, 25,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26,  0,  0, 15, 14, 13,   13, 13, 14, 15,  0,  0, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26,  0,  0, 15, 14, 13, 13,   13, 14, 15,  0,  0, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0, 25,  0,  0,  0,  0, 10,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9, 10,  0,  0,  0,  0, 25,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26,  0,  0, 15, 14, 13,   13, 13, 14, 15,  0,  0, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26,  0,  0, 15, 14, 14, 14,   14, 14, 15,  0,  0, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0, 25,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0, 25,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26,  0,  0, 15, 14, 14,   14, 14, 14, 15,  0,  0, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26,  0,  0, 15, 15, 15, 15,   15, 15, 15,  0,  0, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0, 25,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0, 25,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26,  0,  0, 15, 15, 15,   15, 15, 15, 15,  0,  0, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0, 25, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0, 25,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0, 25,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26, 25,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0, 25, 26, 26, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0,  0, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25,    0,  0,  0, 25,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0, 25,  0,  0,  0,   25, 25, 25, 25, 25, 25, 25, 25, 25, 25,  0,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 25, 26, 26, 26, 25,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25, 26, 26, 27, 26, 26, 25,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0, 25,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0, 25,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0, 25, 26, 26, 27, 26, 26, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0, 25, 26, 26, 27, 28, 27, 26, 26, 25,  0,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0, 25,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0, 25,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0,  0, 25, 26, 26, 27, 28, 27, 26, 26, 25,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26, 26, 26, 26,  0,  0,  0,   26, 26, 26, 26, 26, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25, 26, 26, 27, 26, 26, 25,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0, 25,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0, 25,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0, 25, 26, 26, 27, 26, 26, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26, 26, 26, 26, 26, 26,    0,  0,  0, 26, 26, 26, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 25, 25, 25, 25,  0,  0,  0,   25, 25, 25, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0, 25, 26, 26, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0, 25,  0,  0,  0,  0, 10,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9, 10,  0,  0,  0,  0, 25,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 25, 26, 26, 26, 25,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 25, 25, 25, 25, 25, 25,    0,  0,  0, 25, 25, 25, 25, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0, 25, 25,  0,  0,  0,   25, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0, 25, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,  0,  0, 25,   25, 25, 25, 25,  0,  0,  0,  0, 10,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9, 10,  0,  0,  0,  0, 25, 25, 25, 25,   25,  0,  0,  0,  0,  0,  0,  0,  0, 25, 25, 25, 25, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26, 25,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 25,    0,  0,  0, 25, 25,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0, 25, 25,  0,  0,  0,   25, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 25,    0,  0,  0, 25, 25,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0, 25, 25,  0,  0,  0,   25, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 25,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0, 25, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 25,    0,  0,  0, 25, 25,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 25, 25,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 25, 25,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0, 25, 25, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0, 25, 25, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 25, 25,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 25, 25, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 25, 25, 25, 25, 25,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0, 25, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0, 25, 25, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 25, 25, 25, 25, 25,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 25, 25, 25, 25,  0,    0,  0,  0,  0,  0,  0,  0, 25, 25, 25, 25, 25, 25, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25, 25, 25, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,  0,    0, 25, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0, 25, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0, 25, 25, 25, 25, 25, 25, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 25, 25, 25, 25, 25,    0,  0,  0,  0,  0,  0, 25, 25, 25, 25, 25, 25, 25, 25, 25,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0, 25, 25, 25, 25, 25, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,   25, 25, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25, 25, 25, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0, 25, 25, 25, 25, 25, 25, 25, 25, 25,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 25, 25, 25, 25, 25,   25,  0,  0,  0,  0, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25,  0,  0,  0,  0, 25,   25, 25, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0, 25, 25, 25, 25, 25, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 10,  9,  9,  9,  0,  0,  0,  0,    0,  9, 10,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9, 10,  9,  9,    9,  9, 10,  9,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9, 10,  9,  9,  9,  9,  9,  9,  9,    9,  9, 10,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9, 10,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9, 10,  0,  0,  0,  0,  0,  0,  9,  9,    9,  9, 10,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9, 10,  9,  9,  9,  9, 10,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,    0,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,    0,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,    0,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,    0,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,    0,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,    0,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,    0,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,    0,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,    0,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,    0,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 10,  9,  9,  9,  0,  0,  0,  0,    0,  9, 10,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9, 10,  9,  9,    9,  9, 10,  9,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9, 10,  9,  9,  9,  9,  9,  9,  9,    9,  9, 10,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  0,  0,  0,  0,  0,  9,  9,  9,  9, 10,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9, 10,  0,  0,  0,  0,  0,  0,  9,  9,    9,  9, 10,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9, 10,  9,  9,  9,  9, 10,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0, 25, 25, 25, 25, 25, 25, 25, 25, 25,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 25, 25, 25, 25, 25,   25,  0,  0,  0,  0, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,   25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25,  0,  0,  0,  0, 25,   25, 25, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0, 25, 25, 25, 25, 25, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0, 25, 25, 25, 25, 25, 25, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 25, 25, 25, 25, 25,    0,  0,  0,  0,  0,  0, 25, 25, 25, 25, 25, 25, 25, 25, 25,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0, 25, 25, 25, 25, 25, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,   25, 25, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25, 25, 25, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 25, 25, 25, 25, 25,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 25, 25, 25, 25,  0,    0,  0,  0,  0,  0,  0,  0, 25, 25, 25, 25, 25, 25, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25, 25, 25, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,  0,    0, 25, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0, 25, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 25, 25,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 25, 25, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 25, 25, 25, 25, 25,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0, 25, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0, 25, 25, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 25, 25,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 25, 25,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0, 25, 25, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0, 25, 25, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0, 25, 25,  0,  0,  0,   25, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 25,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0, 25, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 25,    0,  0,  0, 25, 25,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0, 25, 25,  0,  0,  0,   25, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 25,    0,  0,  0, 25, 25,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0, 25, 25,  0,  0,  0,   25, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0, 25, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,  0,  0, 25,   25, 25, 25, 25,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0, 25, 25, 25, 25,   25,  0,  0,  0,  0,  0,  0,  0,  0, 25, 25, 25, 25, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26, 25,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 25,    0,  0,  0, 25, 25,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 25, 25, 25, 25,  0,  0,  0,   25, 25, 25, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0, 25, 26, 26, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0, 25,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0, 25,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 25, 26, 26, 26, 25,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 25, 25, 25, 25, 25, 25,    0,  0,  0, 25, 25, 25, 25, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26, 26, 26, 26,  0,  0,  0,   26, 26, 26, 26, 26, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25, 26, 26, 27, 26, 26, 25,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0, 25,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0, 25,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0, 25, 26, 26, 27, 26, 26, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26, 26, 26, 26, 26, 26,    0,  0,  0, 26, 26, 26, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0, 25, 26, 26, 27, 28, 27, 26, 26, 25,  0,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0, 25,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0, 25,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0,  0, 25, 26, 26, 27, 28, 27, 26, 26, 25,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25, 26, 26, 27, 26, 26, 25,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0, 25,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0, 25,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0, 25, 26, 26, 27, 26, 26, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0, 25, 26, 26, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0,  0, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25,    0,  0,  0, 25,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0, 25,  0,  0,  0,   25, 25, 25, 25, 25, 25, 25, 25, 25, 25,  0,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 25, 26, 26, 26, 25,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0, 25, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0, 25,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0, 25,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26, 25,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26,  0,  0, 15, 15, 15, 15,   15, 15, 15,  0,  0, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0, 25,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0, 25,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26,  0,  0, 15, 15, 15,   15, 15, 15, 15,  0,  0, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26,  0,  0, 15, 14, 14, 14,   14, 14, 15,  0,  0, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0, 25,  0,  0,  0,  0, 10,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9, 10,  0,  0,  0,  0, 25,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26,  0,  0, 15, 14, 14,   14, 14, 14, 15,  0,  0, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26,  0,  0, 15, 14, 13, 13,   13, 14, 15,  0,  0, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0, 25,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0, 25,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26,  0,  0, 15, 14, 13,   13, 13, 14, 15,  0,  0, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26,  0,  0, 15, 14, 13, 13,   13, 14, 15,  0,  0, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0, 25,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0, 25,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26,  0,  0, 15, 14, 13,   13, 13, 14, 15,  0,  0, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26,  0,  0, 15, 14, 13, 13,   13, 14, 15,  0,  0, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0, 25, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0, 25, 25,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0, 25, 25,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 25,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26,  0,  0, 15, 14, 13,   13, 13, 14, 15,  0,  0, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26,  0,  0, 15, 14, 13, 13,   13, 14, 15,  0,  0, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26,  0,  0, 15, 14, 13,   13, 13, 14, 15,  0,  0, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26,  0,  0, 15, 14, 13, 13,   13, 14, 15,  0,  0, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 25, 25, 25, 25, 25,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0, 25, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26,  0,  0, 15, 14, 13,   13, 13, 14, 15,  0,  0, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26,  0,  0, 15, 14, 13, 13,   13, 14, 15,  0,  0, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 25, 26, 26, 26, 25,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0, 25, 26, 26, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26,  0,  0, 15, 14, 13,   13, 13, 14, 15,  0,  0, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26,  0,  0, 15, 14, 13, 13,   13, 14, 15,  0,  0, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 25, 26, 26, 26, 25,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0, 25, 26, 26, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26,  0,  0, 15, 14, 13,   13, 13, 14, 15,  0,  0, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26,  0,  0, 15, 14, 13, 13,   13, 14, 15,  0,  0, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25,   25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25,   25, 25,  0,  0,  0,  0,  0,  0, 10,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9, 10,  0,  0,  0,  0,  0,  0, 25, 25,   25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25,   25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26,  0,  0, 15, 14, 13,   13, 13, 14, 15,  0,  0, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26,  0,  0, 15, 14, 13, 13,   13, 14, 15,  0,  0, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0, 25,  0,  0,  0,  0,  0,  0, 10,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9, 10,  0,  0,  0,  0,  0,  0, 25,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26,  0,  0, 15, 14, 13,   13, 13, 14, 15,  0,  0, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26,  0,  0, 15, 14, 13, 13,   13, 14, 15,  0,  0, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0, 25,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0, 25,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26,  0,  0, 15, 14, 13,   13, 13, 14, 15,  0,  0, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26,  0,  0, 15, 14, 13, 13,   13, 14, 15,  0,  0, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0, 25,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0, 25,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26,  0,  0, 15, 14, 13,   13, 13, 14, 15,  0,  0, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26,  0,  0, 15, 14, 13, 13,   13, 14, 15,  0,  0, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0, 25,  0,  0,  0, 18,  0,  0,  0,  0,  0,  0,  0,   18,  0,  0,  0,  0,  0,  0, 18,  0,  0,  0,  0,  0,  0,  0,  0,    0, 25,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0, 25,  0,    0,  0,  0,  0,  0,  0,  0,  0, 18,  0,  0,  0,  0,  0,  0, 18,    0,  0,  0,  0,  0,  0,  0, 18,  0,  0,  0, 25,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26,  0,  0, 15, 14, 13,   13, 13, 14, 15,  0,  0, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26,  0,  0, 15, 14, 13, 13,   13, 14, 15,  0,  0, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0, 25,  0,  0,  0,  0, 18,  0,  0,  0,  0,  0, 18,    0,  0,  0,  0,  0,  0,  0,  0, 18,  0,  0,  0,  0,  0,  0,  0,    0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,    0,  0,  0,  0,  0,  0,  0, 18,  0,  0,  0,  0,  0,  0,  0,  0,   18,  0,  0,  0,  0,  0, 18,  0,  0,  0,  0, 25,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26,  0,  0, 15, 14, 13,   13, 13, 14, 15,  0,  0, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26,  0,  0, 15, 14, 14, 14,   14, 14, 15,  0,  0, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25, 25, 25, 25, 25,  0,  0,  0,  0,  0, 18,  0,  0,  0, 18,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 18,  0,  0,  0,  0,  0,  0,    0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,    0,  0,  0,  0,  0,  0, 18,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0, 18,  0,  0,  0, 18,  0,  0,  0,  0,  0, 25, 25, 25, 25, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26,  0,  0, 15, 14, 14,   14, 14, 14, 15,  0,  0, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26,  0,  0, 15, 15, 15, 15,   15, 15, 15,  0,  0, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 18,  0, 18,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 18,  0,  0,  0,  0,  0,  0,    0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,    0,  0,  0,  0,  0,  0, 18,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 18,  0, 18,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26,  0,  0, 15, 15, 15,   15, 15, 15, 15,  0,  0, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 18, 18,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 18,  0,  0,  0,  0,  0,    0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,    0,  0,  0,  0,  0, 18,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0, 18, 18,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 18,  0,  0,  0,    0, 18, 18, 18, 18, 18, 18,  0,  0,  0, 18,  0,  0,  0,  0,  0,    0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,    0,  0,  0,  0,  0, 18,  0,  0,  0, 18, 18, 18, 18, 18, 18,  0,    0,  0,  0, 18,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 18,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 18,  0,  0,  0,  0,    0, 25,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0, 25,  0,    0,  0,  0,  0, 18,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 18,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 18,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 18,  0,  0,  0,  0,    0, 25,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0, 25,  0,    0,  0,  0,  0, 18,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 18,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 26, 26, 26, 26, 26, 26, 26,   26, 26, 26, 26, 26, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 18,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 18,  0,  0,  0,    0, 25,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0, 25,  0,    0,  0,  0, 18,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0, 18,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26, 26, 26, 26, 26, 26,   26, 26, 26, 26, 26, 26, 26, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9, 25, 25, 25, 25, 25, 25, 25, 25,   25, 25, 25, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25, 25, 25, 25, 25,  0,  0,  0, 18, 18, 18, 18, 18, 18, 18,  0,    0,  0,  0,  0,  0,  0,  0, 18, 18, 18, 18, 18, 18, 18,  0,  0,    0, 25,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0, 25,  0,    0,  0, 18, 18, 18, 18, 18, 18, 18,  0,  0,  0,  0,  0,  0,  0,    0, 18, 18, 18, 18, 18, 18, 18,  0,  0,  0, 25, 25, 25, 25, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 25, 25, 25, 25, 25, 25,   25, 25, 25, 25, 25, 25, 25, 25,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  5,  5,  0,  0,    0, 25,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0, 25,  0,    0,  0,  5,  5,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0, 25,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0, 25,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0, 25,  0,  0,  0,  0,  0,  0, 10,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9, 10,  0,  0,  0,  0,  0,  0, 25,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25,   25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25,   25, 25,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0, 25, 25,   25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25,   25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25, 25, 25, 25, 25, 25,   25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25,   25, 25, 25, 25, 25, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0, 25, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 25, 25, 25, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0, 25, 25, 25, 25, 25,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0, 25, 18, 19, 20, 19, 25, 25, 25, 25,  0,  0,  0,    0,  0, 25,  6,  6,  6, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 10,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9, 10,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  6,  6,  6, 25,  0,  0,    0,  0,  0, 25, 25, 25, 25, 19, 20, 19, 18, 25,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0, 25, 18, 19, 20, 19, 18, 18, 18, 18, 25, 25, 25,    0,  0, 25,  6,  7,  6, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 10,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9, 10,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  6,  7,  6, 25,  0,  0,   25, 25, 25, 18, 18, 18, 18, 19, 20, 19, 18, 25,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0, 25, 18, 19, 20, 20, 20, 20, 20, 20, 20, 20,  0,   25, 25, 25,  6,  8,  6, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  6,  8,  6, 25, 25, 25,    0, 20, 20, 20, 20, 20, 20, 20, 20, 19, 18, 25,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0, 25, 25,   25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25,  0,  0,  0,  0, 25,    0,  0,  0,  0, 25, 18, 19, 20, 19, 18, 18, 18, 18, 25, 25, 25,    0,  0, 25,  6,  7,  6, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  6,  7,  6, 25,  0,  0,   25, 25, 25, 18, 18, 18, 18, 19, 20, 19, 18, 25,  0,  0,  0,  0,   25,  0,  0,  0,  0, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25,   25, 25,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0, 25,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0, 25,    0,  0,  0,  0, 25, 18, 19, 20, 19, 25, 25, 25, 25,  0,  0,  0,    0,  0, 25,  6,  6,  6, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  6,  6,  6, 25,  0,  0,    0,  0,  0, 25, 25, 25, 25, 19, 20, 19, 18, 25,  0,  0,  0,  0,   25,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0, 25,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0, 25,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0, 25,    0,  0,  0,  0, 25, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 25, 25, 25, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0, 25, 25, 25, 25, 25,  0,  0,  0,  0,   25,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0, 25,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0, 25,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0, 25,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0, 25,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0, 25,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0, 25, 25,   25, 25, 25, 25,  0,  0,  0,  0, 25, 25, 25,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0, 25, 25, 25,  0,  0,  0,  0, 25, 25, 25, 25,   25, 25,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0, 25,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0, 25,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0, 25,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0, 25,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0, 25,  0,  0,  0,  0, 25, 25, 25, 25, 25,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0, 25, 25, 25, 25, 25,  0,  0,  0,  0, 25,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0, 25, 25, 25, 25,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25,  0,  0, 25,    0,  0,  0,  0,  0, 25,  0,  0,  0, 25, 25, 25, 25,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0, 25, 25, 25, 25,  0,  0,  0, 25,  0,  0,  0,  0,  0,   25,  0,  0, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0, 25, 25, 25,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,   25, 25, 25,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 10,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9, 10,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,   25, 25, 25, 25, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0, 25, 25, 25, 25,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0, 25, 25, 25, 25, 25, 25, 25, 25,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 25, 25, 25,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 25, 25,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,   25, 25, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 10,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9, 10,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 10,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9, 10,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 25, 25, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25, 25, 25,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0, 25, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0, 25, 26, 26, 26, 25,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0, 25, 26, 26, 26, 25,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 25, 25, 25, 25,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0, 25, 26, 27, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0, 25,   25, 25,  0,  0,  0,  0, 25, 26, 27, 27, 27, 26, 25,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0, 25, 26, 27, 27, 27, 26, 25,  0,  0,  0,  0, 25, 25,   25,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26, 27, 26, 25,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0, 25, 26, 27, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0, 25,    5, 25,  0,  0,  0, 25, 26, 27, 28, 28, 28, 27, 26, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25, 26, 27, 28, 28, 28, 27, 26, 25,  0,  0,  0, 25,  5,   25,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26, 27, 26, 25,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0, 25, 26, 27, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0, 25,    5, 25,  0,  0,  0, 25, 26, 27, 28,  4, 28, 27, 26, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25, 26, 27, 28,  4, 28, 27, 26, 25,  0,  0,  0, 25,  5,   25,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26, 27, 26, 25,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0, 25, 26, 27, 26, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25,    5, 25,  0,  0,  0, 25, 26, 27, 28,  4, 28, 27, 26, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25, 26, 27, 28,  4, 28, 27, 26, 25,  0,  0,  0, 25,  5,   25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 26, 27, 26, 25,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0, 25, 26, 27, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26,    5, 25,  0,  0,  0, 25, 26, 27, 28,  4, 28, 27, 26, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25, 26, 27, 28,  4, 28, 27, 26, 25,  0,  0,  0, 25,  5,   26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 27, 26, 25,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0, 25, 26, 27, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26,    5, 25,  0,  0,  0, 25, 26, 27, 28, 28, 28, 27, 26, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25, 26, 27, 28, 28, 28, 27, 26, 25,  0,  0,  0, 25,  5,   26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 27, 26, 25,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25, 25, 25, 25,  0,  0,    0,  0, 25, 26, 27, 26, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25,    5, 25,  0,  0,  0,  0, 25, 26, 27, 27, 27, 26, 25,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0, 25, 26, 27, 27, 27, 26, 25,  0,  0,  0,  0, 25,  5,   25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 26, 27, 26, 25,  0,  0,    0,  0, 25, 25, 25, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25, 25, 25, 25,  0,  0,    0,  0, 25, 26, 27, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0, 25,    5, 25,  0,  0,  0,  0,  0, 25, 26, 26, 26, 25,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0, 25, 26, 26, 26, 25,  0,  0,  0,  0,  0, 25,  5,   25,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26, 27, 26, 25,  0,  0,    0,  0, 25, 25, 25, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0, 25, 26, 27, 26, 25,  0,  0,  0,  0,  0,  0,  0,  0, 25,    5, 25,  0,  0,  0,  0,  0,  0, 25, 25, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25, 25, 25,  0,  0,  0,  0,  0,  0, 25,  5,   25,  0,  0,  0,  0,  0,  0,  0,  0, 25, 26, 27, 26, 25,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0, 25, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,  0,  0, 25,    5, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  5,   25,  0,  0,  0,  0,  0,  0,  0,  0, 25, 25, 25, 25, 25,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,    5, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  5,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,   25, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 25,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 10,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9, 10,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0, 25, 25, 25, 25, 25, 25,  0,  0,  0,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0,  0,  0,  0, 25, 25, 25, 25, 25, 25,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 10,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9, 10,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 10,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9, 10,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0,  0,  0,  0,  0, 25, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25, 25,  0,  0,  0,  0,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0, 25, 25, 25, 25, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0, 25, 25, 25, 25, 25, 25, 25, 25,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0, 25, 25, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25, 25, 25,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 10,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9, 10,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25, 25, 25, 25, 25, 25, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0, 25,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0, 25,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0, 25,  0,  0,    0,  0, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0, 25, 25, 25, 25, 25,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0, 25, 25, 25, 25, 25,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25,  0,  0,    0,  0, 25,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0, 25, 25,  0,    0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0, 25,  0,  0,  0, 25,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0, 25,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,    0, 25, 25,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0, 25,  0,  0,  0, 25,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 10,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9, 10,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0, 25,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0, 25,  0,  0,  0, 25,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 10,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9, 10,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0, 25,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0, 25,  0,  0,  0, 25,  0,  0,  0,  0, 25,   25, 25, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 25, 25,   25,  0,  0,  0,  0, 25,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0, 25,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0, 25,  0,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,   25,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0, 25,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0, 25,  0,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,   25,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25,  0,  0,  0,  0, 25,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0, 25,  0,  0,  0, 25,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0, 25,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,   25,  0,  0,  0,  0, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0, 25, 25, 25, 25, 25, 25,   25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25,    0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0, 25,   25, 25, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25, 25, 25,   25,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,   25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25,   25, 25, 25, 25, 25, 25,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0,  0, 25,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0, 10,  9,  9,  9,  9,  9,  0,  0,    0,  0,  9,  9,  9,  9,  9, 10,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   25,  0,  0,  0,  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,    0,  0,  0,  0,  0,  0,  0,  0,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9])
    RaceWorld.Map.append([  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,    9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9,  9])
    print("[RallyDot] Map 7 loaded 160x288 (map6 x4, half seam tunnels)")
    RaceWorld.CopyMapToPlayfield()


  return RaceWorld;


def ShowShortMessage(RaceWorld,PlayerCar,ShortMessage):
  """Brief overlay message; hard timeout so it cannot hang the game."""
  try:
    ShortMessageSprite = LED.CreateShortMessageSprite(ShortMessage)
  except Exception as e:
    print("[RallyDot] ShowShortMessage sprite failed:", e)
    return
  ShortMessageSprite.on = 1
  if not hasattr(ShortMessageSprite, "StartTime"):
    ShortMessageSprite.StartTime = time.time()
  if not hasattr(ShortMessageSprite, "DirectionIncrement"):
    ShortMessageSprite.DirectionIncrement = 1
  if not hasattr(ShortMessageSprite, "PausePositionV"):
    ShortMessageSprite.PausePositionV = max(2, VIEW_H // 3)
  if not hasattr(ShortMessageSprite, "Delay"):
    ShortMessageSprite.Delay = 0.35
  if not hasattr(ShortMessageSprite, "PauseTimerOn"):
    ShortMessageSprite.PauseTimerOn = 0
  if not hasattr(ShortMessageSprite, "v") or ShortMessageSprite.v is None:
    ShortMessageSprite.v = 0
  if not hasattr(ShortMessageSprite, "h") or ShortMessageSprite.h is None:
    ShortMessageSprite.h = max(0, (VIEW_W - getattr(ShortMessageSprite, "width", 12)) // 2)

  m = 1
  t0 = time.time()
  while ShortMessageSprite.on == 1 and (time.time() - t0) < 2.5:
    try:
      _ch, _cv = camera_for_car(PlayerCar, RaceWorld)
      RaceWorld.DisplayWindowWithSprite(_ch, _cv, ShortMessageSprite)
      MoveMessageSprite(m, ShortMessageSprite)
    except Exception as e:
      print("[RallyDot] ShowShortMessage frame error:", e)
      break
    m += 1
  ShortMessageSprite.on = 0

  













def _pf_name(Playfield, h, v):
  """Safe playfield name lookup; off-map treats as Wall."""
  try:
    if v < 0 or h < 0:
      return "Wall"
    if v >= len(Playfield) or h >= len(Playfield[0]):
      return "Wall"
    return Playfield[v][h].name
  except Exception:
    return "Wall"


def MoveCar(Car,Playfield):
  
  #print ("")
  #print ("== RD Move Car: ",Car.name," --")
  h = Car.h
  v = Car.v
  oldh  = h
  oldv  = v
  ScanH = 0
  ScanV = 0
  ItemList = []
  DoNothing = ""

  #SolidObjects
  SolidObjects = []
  SolidObjects.append("Wall")
  SolidObjects.append("Fuel")
  
  
  #print("Current Car hv direction:",h,v,Car.direction)
  
  ItemList = RallyDotScanAroundCar(Car,Playfield)
  #print (ItemList[1])

  
  # #Handle Enemy actions first
  if (Car.name == "Enemy"):
    #Decrease color if no player nearby
    #Increase if player nearby
    if ('Player' not in ItemList):
      DecreaseColor(Car)
    else:
      #print ("Player nearby, increasing color of Enemy")
      IncreaseColor(Car)

    if ("Player" in ItemList):
      if (ItemList[1] == 'Player'):
        #Deplete player car lives (health)
        ScanH,ScanV = LED.CalculateDotMovement8Way(h,v,Car.direction)
        Playfield[ScanV][ScanH].lives = Playfield[ScanV][ScanH].lives - 1
      elif (ItemList[2] == 'Player'):
        #print("Turn NE")
        Car.direction = LED.TurnRight8Way(Car.direction)
      elif (ItemList[3] == 'Player'):
        #print("Turn E")
        Car.direction = LED.TurnRight8Way(Car.direction)
        Car.direction = LED.TurnRight8Way(Car.direction)
      elif (ItemList[4] == 'Player'):
        #print("Turn SE")
        Car.direction = LED.TurnRight8Way(Car.direction)
        Car.direction = LED.TurnRight8Way(Car.direction)
        Car.direction = LED.TurnRight8Way(Car.direction)
      elif (ItemList[5] == 'Player'):
        #print("Turn S")
        Car.direction = LED.ReverseDirection8Way(Car.direction)
      elif (ItemList[8] == 'Player'):
        #print("Turn NW")
        Car.direction = LED.TurnLeft8Way(Car.direction)
      elif (ItemList[7] == 'Player'):
        #print("Turn W")
        Car.direction = LED.TurnLeft8Way(Car.direction)
        Car.direction = LED.TurnLeft8Way(Car.direction)      
      elif (ItemList[6] == 'Player'):
        #print("Turn SW")
        Car.direction = LED.TurnLeft8Way(Car.direction)
        Car.direction = LED.TurnLeft8Way(Car.direction)      
        Car.direction = LED.TurnLeft8Way(Car.direction)      

      

  #Handle Player actions
  if (Car.name == "Player"):
    #Handle Wall Movements
    if (ItemList[1] == "Wall"):
      #print ("--Wall found--")
      
      #When you hit the middle of a wall, go left or right (randomly)
      if (ItemList[3] == 'EmptyObject' and ItemList[7] == 'EmptyObject'):
        Car.direction = LED.TurnLeftOrRightTwice8Way(Car.direction)
      
      #If you are surrounded, turn around
      elif (ItemList[3] == "Wall" and ItemList[7] == "Wall"):
        Car.direction = LED.ReverseDirection8Way(Car.direction)
      
      elif (ItemList[8] == 'EmptyObject'):
        Car.direction = LED.TurnLeft8Way(Car.direction)
      elif (ItemList[7] in ('EmptyObject',"Fuel")):
        Car.direction = LED.TurnLeft8Way(Car.direction)
        Car.direction = LED.TurnLeft8Way(Car.direction)
      elif (ItemList[2] == 'EmptyObject'):
        Car.direction = LED.TurnRight8Way(Car.direction)
      elif (ItemList[3] in ('EmptyObject',"Fuel")):
        Car.direction = LED.TurnRight8Way(Car.direction)
        Car.direction = LED.TurnRight8Way(Car.direction)
    
    elif (ItemList[1] == "Enemy"):
      if (ItemList[2] != 'EmptyObject' and ItemList[8] != 'EmptyObject' and ItemList[5] == 'EmptyObject'):
        Car.direction = LED.ReverseDirection8Way(Car.direction)
      elif (ItemList[2] == 'EmptyObject'):
        Car.direction = LED.TurnRight8Way(Car.direction)    
      elif (ItemList[3] == 'EmptyObject'):
        Car.direction = LED.TurnRight8Way(Car.direction)    
        Car.direction = LED.TurnRight8Way(Car.direction)    
      elif (ItemList[4] == 'EmptyObject'):
        Car.direction = LED.TurnRight8Way(Car.direction)    
        Car.direction = LED.TurnRight8Way(Car.direction)    
        Car.direction = LED.TurnRight8Way(Car.direction)    
      elif (ItemList[8] == 'EmptyObject'):
        Car.direction = LED.TurnLeft8Way(Car.direction)    
      elif (ItemList[7] == 'EmptyObject'):
        Car.direction = LED.TurnLeft8Way(Car.direction)    
        Car.direction = LED.TurnLeft8Way(Car.direction)    
      elif (ItemList[6] == 'EmptyObject'):
        Car.direction = LED.TurnLeft8Way(Car.direction)    
        Car.direction = LED.TurnLeft8Way(Car.direction)    
        Car.direction = LED.TurnLeft8Way(Car.direction)    
    
    
    #Cars eat fuel
    elif ("Fuel" in ItemList):
      if (ItemList[1] == "Fuel"):
        DoNothing = "nothing"
      elif (ItemList[2] == "Fuel"):
        Car.direction = LED.TurnRight8Way(Car.direction) 
      elif (ItemList[3] == "Fuel"):
        Car.direction = LED.TurnRight8Way(Car.direction) 
        Car.direction = LED.TurnRight8Way(Car.direction) 
      elif (ItemList[4] == "Fuel"):
        Car.direction = LED.TurnRight8Way(Car.direction) 
        Car.direction = LED.TurnRight8Way(Car.direction) 
        Car.direction = LED.TurnRight8Way(Car.direction) 
      elif (ItemList[5] == "Fuel"):
        Car.direction = LED.ReverseDirection8Way(Car.direction) 
      elif (ItemList[8] == "Fuel"):
        Car.direction = LED.TurnLeft8Way(Car.direction) 
      elif (ItemList[7] == "Fuel"):
        Car.direction = LED.TurnLeft8Way(Car.direction) 
        Car.direction = LED.TurnLeft8Way(Car.direction) 
      elif (ItemList[6] == "Fuel"):
        Car.direction = LED.TurnLeft8Way(Car.direction) 
        Car.direction = LED.TurnLeft8Way(Car.direction) 
        Car.direction = LED.TurnLeft8Way(Car.direction) 

      Fuelh, Fuelv = LED.CalculateDotMovement8Way(h,v,Car.direction)
      try:
        if 0 <= Fuelv < len(Playfield) and 0 <= Fuelh < len(Playfield[0]):
          Playfield[Fuelv][Fuelh].alive = 0
          Playfield[Fuelv][Fuelh] = EmptyObject('EmptyObject')
      except Exception:
        pass
      Car.destination = ""
      Car.lives = Car.lives + 50
      if Car.name == "Player":
        Car.gas = min(PLAYER_GAS_MAX, getattr(Car, "gas", 0) + PLAYER_GAS_REFILL)
      
      #make car go faster by lowering the speed value
      Car.ShiftGear("up")
    
    #Turn if following a wall and a corridor opens up
    elif(ItemList[7] == "Wall" and ItemList[8] == 'EmptyObject'):
      Car.direction = LED.ChanceOfTurning8Way(Car.direction,50)
    elif(ItemList[3] == "Wall" and ItemList[2] == 'EmptyObject'):
      Car.direction = LED.ChanceOfTurning8Way(Car.direction,50)


      
  #Only move if the space decided upon is actually empty!
  ScanH,ScanV = LED.CalculateDotMovement8Way(h,v,Car.direction)
  if (_pf_name(Playfield, ScanH, ScanV) == 'EmptyObject'):
    h = ScanH
    v = ScanV

    

  #print ("oldh oldv hv",oldh,oldv,h,v)  
  #IF the car actually moved, update the locations
  if (oldh != h or oldv != v):
    try:
      Car.h = h
      Car.v = v  
      Playfield[v][h] = Car
      Playfield[oldv][oldh] = EmptyObject('EmptyObject')
    except Exception as e:
      print("[RallyDot] MoveCar place failed:", e)
      Car.h, Car.v = oldh, oldv


    
  # #Randomly change direction for a bit of chaos
  # if (Car.name == 'Player'):
    # m,r = divmod(moves,800)
    # if (r == 0):
      # Car.direction = LED.TurnLeftOrRight8Way(Car.direction)
    

  return 



def CountFuelDotsLeft(FuelDots,FuelCount):
  FuelDotsLeft = 0
  for x in range (FuelCount):
    if (FuelDots[x].alive == 1):
      FuelDotsLeft = FuelDotsLeft + 1
  return FuelDotsLeft;

  
def CopyFuelDotsToPlayfield(FuelDots,FuelCount,RaceWorld):
  width  = RaceWorld.width
  height = RaceWorld.height
  
   
  for x in range (FuelCount):
    finished = 'N'
    attempts = 0
    while (finished == 'N' and attempts < 2500):
      attempts += 1
      #Don't put fuel in border area
      lo_h, hi_h = 1, max(2, width-2)
      lo_v, hi_v = 1, max(2, height-2)
      h = random.randint(lo_h, hi_h)
      v = random.randint(lo_v, hi_v)
      
      name = RaceWorld.Playfield[v][h].name
      #print ("Playfield name: ",name)
      
      #print ("FuelDot x h v: ",x,h,v)
      if (name == 'EmptyObject'):
        #print ("Placing Fuel x name: ",x,FuelDots[x].name)
        RaceWorld.Playfield[v][h] = FuelDots[x]
        FuelDots[x].h = h
        FuelDots[x].v = v
        FuelDots[x].alive = 1
        finished = 'Y'


def CopyEnemyCarsToPlayfield(EnemyCars,EnemyCount,RaceWorld):
  width  = RaceWorld.width
  height = RaceWorld.height
  
   
  for x in range (EnemyCount):
    finished = 'N'
    attempts = 0
    while (finished == 'N' and attempts < 500):
      attempts += 1
      #Don't put cars in border area
      lo_h, hi_h = 1, max(2, width-2)
      lo_v, hi_v = 1, max(2, height-2)
      h = random.randint(lo_h, hi_h)
      v = random.randint(lo_v, hi_v)
      
      name = RaceWorld.Playfield[v][h].name
      #print ("Playfield name: ",name)
      
      #print ("FuelDot x h v: ",x,h,v)
      if (name == 'EmptyObject'):
        #print ("Placing car x name: ",x,EnemyCars[x].name)
        RaceWorld.Playfield[v][h] = EnemyCars[x]
        EnemyCars[x].h = h
        EnemyCars[x].v = v
        EnemyCars[x].alive = 1
        finished = 'Y'
      #else:
      #  print ("Spot occupied: ",name)  



  
        













def GetDistanceBetweenCars(Car1,Car2):
  a = abs(Car1.h - Car2.h)
  b = abs(Car1.v - Car2.v)
  c = math.sqrt(a**2 + b**2)

  return c;  
        




def FindClosestFuel(Car,FuelDots,FuelCount):
  #We want the player car to journey towards the closes fuel dot
  #So far, this function points the car.   How do we make it journey there?
  ClosestX     = 0
  MinDistance  = 9999
  FuelDotsLeft = 0
  Distance = 0
  for x in range(FuelCount):
    if (FuelDots[x].alive == 1):
      FuelDotsLeft = FuelDotsLeft + 1
      Distance = GetDistanceBetweenCars(Car,FuelDots[x])
      if (Distance < MinDistance):
        MinDistance = Distance
        ClosestX = x
    
  return ClosestX, MinDistance, FuelDotsLeft;



def ScrollToCar(Car, RaceWorld):
  """Snap camera to car (no multi-frame scroll — that looked like a double draw)."""
  target_h, target_v = camera_for_car(Car, RaceWorld)
  RaceWorld.DisplayWindow(target_h, target_v)
  time.sleep(0.05)


def AdjustCarColor(Car):
  r = 0
  g = 0
  b = 200 + Car.lives
  if (b >= 255):
    b = 255
  if (b <= 200):
    b = 200
  Car.b = b        





def TurnTowardsCarDestination(SourceCar):
  print ("Turning towards: ",SourceCar.name)
  if (SourceCar.h < SourceCar.dh):
    if (SourceCar.direction in (7,8,1,2)):
      SourceCar.direction = LED.TurnRight8Way(SourceCar.direction)
    if (SourceCar.direction in (6,5,4)):
      SourceCar.direction = LED.TurnLeft8Way(SourceCar.direction)
      
  if (SourceCar.h > SourceCar.dh):
    if (SourceCar.direction in (8,1,2,3)):
      SourceCar.direction = LED.TurnLeft8Way(SourceCar.direction)
    if (SourceCar.direction in (6,5,4)):
      SourceCar.direction = LED.TurnRight8Way(SourceCar.direction)


  if (SourceCar.v < SourceCar.dv):
    if (SourceCar.direction in (6,7,8,1)):
      SourceCar.direction = LED.TurnLeft8Way(SourceCar.direction)
    if (SourceCar.direction in (2,3,4)):
      SourceCar.direction = LED.TurnRight8Way(SourceCar.direction)
      
  if (SourceCar.v > SourceCar.dv):
    if (SourceCar.direction in (6,7,8)):
      SourceCar.direction = LED.TurnRight8Way(SourceCar.direction)
    if (SourceCar.direction in (5,4,3,2)):
      SourceCar.direction = LED.TurnLeft8Way(SourceCar.direction)
  return;



  
def TurnTowardsCar(SourceCar,TargetCar):
  if (SourceCar.h < TargetCar.h):
    if (SourceCar.direction in (7,8,1,2)):
      SourceCar.direction = LED.TurnRight8Way(SourceCar.direction)
    if (SourceCar.direction in (6,5,4)):
      SourceCar.direction = LED.TurnLeft8Way(SourceCar.direction)
      
  if (SourceCar.h > TargetCar.h):
    if (SourceCar.direction in (8,1,2,3)):
      SourceCar.direction = LED.TurnLeft8Way(SourceCar.direction)
    if (SourceCar.direction in (6,5,4)):
      SourceCar.direction = LED.TurnRight8Way(SourceCar.direction)


  if (SourceCar.v < TargetCar.v):
    if (SourceCar.direction in (6,7,8,1)):
      SourceCar.direction = LED.TurnLeft8Way(SourceCar.direction)
    if (SourceCar.direction in (2,3,4)):
      SourceCar.direction = LED.TurnRight8Way(SourceCar.direction)
      
  if (SourceCar.v > TargetCar.v):
    if (SourceCar.direction in (6,7,8)):
      SourceCar.direction = LED.TurnRight8Way(SourceCar.direction)
    if (SourceCar.direction in (5,4,3,2)):
      SourceCar.direction = LED.TurnLeft8Way(SourceCar.direction)
  return;
  
  
def TurnTowardsFuelIfThereIsRoom(Car,Playfield,FuelDots,ClosestFuel):
  ItemList = []
  ItemList = RallyDotScanAroundCar(Car,Playfield)          
  if (all('EmptyObject' == Item for Item in ItemList)):
    #print ("Scanners indicate emptiness all around")
    TurnTowardsCar(Car,FuelDots[ClosestFuel])
    #Car.ShiftGear("up")
  elif (ItemList[1] == "Empty" 
    and ItemList[2] == "Empty" 
    and ItemList[3] == "Empty" 
    and ItemList[4] == "Empty" 
    and ItemList[5] == "Empty" 
    and ItemList[8] == "Wall"
    and ItemList[7] == "Wall"
    and ItemList[6] == "Wall"):
    print ("Wall on entire left left")
    LED.TurnRight8Way(Car.direction)
    Car.ShiftGear("up")
  elif (ItemList[1] == "Empty" 
    and ItemList[2] == "Wall" 
    and ItemList[3] == "Wall" 
    and ItemList[4] == "Wall" 
    and ItemList[5] == "Wall" 
    and ItemList[8] == "Empty"
    and ItemList[7] == "Empty"
    and ItemList[6] == "Empty"):
    print ("Wall on entire right left")
    LED.TurnLeft8Way(Car.direction)
    Car.ShiftGear("up")

    
    
  #If the car is near enough, turn towards the fuel (random chance)
  #this is an attempt to get the car out of a loop where it just can't
  #navigate out of a situation
  
  global moves
  if on_tick(moves, 500):
    Distance = GetDistanceBetweenCars(Car,FuelDots[ClosestFuel])    
    if (Distance < 3):
      TurnTowardsCar(Car,FuelDots[ClosestFuel])
    

    
  return
      





  

def RallyDotScanStraightLine(h,v,direction,Playfield):
 
  ScanDirection = direction
  ScanH         = 0
  ScanV         = 0
  Item          = ''
  ItemList      = ['NULL']
  WallHit       = 0
  count         = 0    #represents number of spaces to scan

#           7
#           6
#           5                             
#           4                             
#           3                             
#           2                            
#           1                              
                                           

  #print ("")
  #print("== RD Scan Straight Line")     
  #print("SSL - hv direction",h,v,direction)

  for count in range (8):
    ScanH, ScanV = LED.CalculateDotMovement(h,v,ScanDirection)
    Item = Playfield[ScanV][ScanH].name
    
    if (Item == 'Wall' or WallHit == 1):
      ItemList.append('Wall')
      WallHit = 1
    else:
      ItemList.append(Item)
    #print ("RDSSL - count hv ScanH ScanV Item",count,h,v,ScanH,ScanV, Item)
    
  
  return ItemList;


  
def RallyDotScanAroundCar(Car,Playfield):
  # hv represent car location
  # ScanH and ScanV is where we are scanning
  
  #print ("== Scan around car ==")
  
  ScanDirection = Car.direction
  ScanH         = 0
  ScanV         = 0
  h             = Car.h
  v             = Car.v
  Item          = ''
  ItemList      = ['EmptyObject']
  count         = 0    #represents number of spaces to scan


#         8 1 2
#         7 x 3                             
#         6 5 4
        
  


  for count in range (8):
    ScanH, ScanV = LED.CalculateDotMovement8Way(h,v,ScanDirection)
    
    

    Item = Playfield[ScanV][ScanH].name
    if (Item == 'Wall'):
      ItemList.append('Wall')
    else:
      ItemList.append(Item)
    #print ("RDSAC - count hv ScanH ScanV Item",count,h,v,ScanH,ScanV, Item)

    #Turn to the right
    ScanDirection = LED.TurnRight8Way(ScanDirection)
      

  return ItemList;
  





def RallyDotBlowUp(Car,Playfield):
  
  # Blow up car, do damage all around
  # hv represent car location
  # ScanH and ScanV is where we are scanning
  
  #print ("== Scan around car ==")
  
  ScanDirection = Car.direction
  ScanH         = 0
  ScanV         = 0
  h             = Car.h
  v             = Car.v
  Item          = ''
  ItemList      = ['EmptyObject']
  count         = 0    #represents number of spaces to scan

#         8 1 2
#         7 x 3                             
#         6 5 4
        
  for count in range (8):
    #print ("ScanDirection: ",ScanDirection)
    ScanH, ScanV = LED.CalculateDotMovement8Way(h,v,ScanDirection)
    try:
      if ScanV < 0 or ScanH < 0 or ScanV >= len(Playfield) or ScanH >= len(Playfield[0]):
        ScanDirection = LED.TurnRight8Way(ScanDirection)
        continue
      Item = Playfield[ScanV][ScanH].name
      if (Item == "Enemy"): 
          Playfield[ScanV][ScanH].exploding = 1
      if (Item == "Player"):
        #lives is used as health
        Playfield[ScanV][ScanH].lives = Playfield[ScanV][ScanH].lives -10
        Playfield[ScanV][ScanH].ShiftGear("down")
    except Exception:
      pass

    #Turn to the right
    ScanDirection = LED.TurnRight8Way(ScanDirection)
  
  Car.alive = 0
  Car.exploding = 1

  return;


def _fuel_count_for_world(RaceWorld):
  """Fuel pickups scale with map area (map 6 baseline = 50)."""
  map6_area = 80 * 144
  map_area = max(1, RaceWorld.width * RaceWorld.height)
  return max(50, int(round(50 * map_area / float(map6_area))))


def _make_fuel_dots(fuel_count):
  return [
    CarDot(
      h=8, v=8, dh=-1, dv=-1,
      r=SDLowYellowR, g=SDLowYellowG, b=SDLowYellowB,
      direction=1, scandirection=1, gear=[], speed=1, currentgear=1,
      alive=1, lives=1, name="Fuel", score=0, exploding=0,
      radarrange=0, destination="",
    )
    for _ in range(fuel_count)
  ]


def _make_enemy_cars(enemy_count):
  return [
    CarDot(
      h=5, v=19, dh=-1, dv=-1,
      r=SDLowRedR, g=SDLowRedG, b=SDLowRedB,
      direction=2, scandirection=2, gear=[],
      speed=10, currentgear=1, alive=1, lives=1,
      name="Enemy", score=0, exploding=0,
      radarrange=40, destination="",
    )
    for _ in range(enemy_count)
  ]


def _place_player_on_map(PlayerCar, RaceWorld):
  """Spawn player near map center-bottom on an empty cell."""
  h = RaceWorld.width // 2
  v = max(1, RaceWorld.height - 9)
  # Search nearby if spawn is blocked
  if RaceWorld.Playfield[v][h].name not in ("EmptyObject", "Player"):
    found = False
    for radius in range(1, 24):
      for dv in range(-radius, radius + 1):
        for dh in range(-radius, radius + 1):
          nh, nv = h + dh, v + dv
          if 1 <= nv < RaceWorld.height - 1 and 1 <= nh < RaceWorld.width - 1:
            if RaceWorld.Playfield[nv][nh].name == "EmptyObject":
              h, v = nh, nv
              found = True
              break
        if found:
          break
      if found:
        break
  PlayerCar.h = h
  PlayerCar.v = v
  PlayerCar.direction = 1
  PlayerCar.destination = ""
  PlayerCar.alive = 1
  PlayerCar.exploding = 0
  PlayerCar.lives = PLAYER_HEALTH_MAX
  PlayerCar.gas = PLAYER_GAS_MAX
  PlayerCar.currentgear = 1
  try:
    PlayerCar.speed = PlayerCar.gear[1]
  except Exception:
    PlayerCar.speed = 4
  PlayerCar.radarrange = 8
  RaceWorld.Playfield[v][h] = PlayerCar


def ResetRaceMap(PlayerCar, enemy_car_count=50):
  """
  Full maze restart for a new life: reload map, fuel, enemies, player spawn.
  Returns (RaceWorld, FuelDots, FuelCount, FuelDotsLeft, EnemyCars, EnemyCarCount).
  """
  RaceWorld = CreateRaceWorld(ACTIVE_MAP_LEVEL)
  FuelCount = _fuel_count_for_world(RaceWorld)
  FuelDots = _make_fuel_dots(FuelCount)
  CopyFuelDotsToPlayfield(FuelDots, FuelCount, RaceWorld)
  EnemyCars = _make_enemy_cars(enemy_car_count)
  CopyEnemyCarsToPlayfield(EnemyCars, enemy_car_count, RaceWorld)
  _place_player_on_map(PlayerCar, RaceWorld)
  print(
    "[RallyDot] Map reset",
    RaceWorld.width, "x", RaceWorld.height,
    "fuel", FuelCount, "enemies", enemy_car_count,
  )
  return RaceWorld, FuelDots, FuelCount, FuelCount, EnemyCars, enemy_car_count


def PlayRallyDot(Duration=10, StopEvent=None):
  global moves
  refresh_view_size()
  _apply_full_brightness()
  print ("")
  print ("")
  print ("----------------------")
  print ("-- Rally Dot      ----")
  print ("-- viewport", VIEW_W, "x", VIEW_H, "----")
  print ("----------------------")
  print ("")
  
  #Local Variables 
  LevelCount       = 0
  map_stage        = 0   # which map stage we are on (0=first map)
  LevelFinished    = "N"
  m                = 0
  r                = 0
  moves            = 0
  MaxMoves         = int(globals().get("TEST_MAX_MOVES", 10000))

  Finished         = 'N'
  Distance         = 0
  ClosestFuelDistance = 0
  Minx             = 0
  MinDistance      = 9999
  x                = 0
  y                = 0
  ItemList         = []
  CarOriginalSpeed = 0
  Diaganols        = [2,4,6,8]
  #SpeedModifier    = 1.2 -- decimals seem to cause car to stop working
  SpeedModifier    = 2
  EnemyRadarSpeed  = 10 * CPU_MODIFIER
  PlayerRadarSpeed = 10 * CPU_MODIFIER
  EnemyCount       = 0
  ACarHasExploded  = 0
  EnemyCarSpawnSpeed = 500
  CarWinSleep       = 1
  DisolveSleep      = 0.01
  
  ClockSprite = LED.CreateClockSprite(12)
  ClockSprite.on = 1
  position_clock_upper_right(ClockSprite)
  if not hasattr(ClockSprite, "StartTime"):
    ClockSprite.StartTime = time.time()
  ClockSprite._last_hhmm = time.strftime("%H%M")

  #ShortWordSprite = CreateShortWordSprite("WIN!")
  #ShortWordSprite.on = 0

  
  #Show Intro
  LED.ClearBigLED()
  # Title banner removed — drive-on intro handles branding
  
  
  #---------------------------------
  #-- Prepare World 1             --
  #---------------------------------

  #Create Player Car (lives field = health; stock lives tracked separately)
  PlayerCar = CarDot(h=8,v=19,dh=8,dv=8,r=0,g=150,b=255,direction=1,scandirection=1,
              gear=[1],
              speed=10,
              currentgear=1,
              alive=1,
              lives=PLAYER_HEALTH_MAX, name="Player",score=0,exploding=0,radarrange=16,destination="")

  PlayerStockLives = PLAYER_STOCK_LIVES
  EnemyCarCount = 50
  ClosestFuel = 0
  RaceWorld, FuelDots, FuelCount, FuelDotsLeft, EnemyCars, EnemyCarCount = ResetRaceMap(
    PlayerCar, enemy_car_count=EnemyCarCount)
  print("[RallyDot] Using map level", ACTIVE_MAP_LEVEL,
        "size", RaceWorld.width, "x", RaceWorld.height,
        "stock lives", PlayerStockLives)
  CarOriginalSpeed = PlayerCar.speed
  out_of_fuel_since = None  # wall-clock when tank hit empty
  
  #Display Intro
  #ShowLevelCount(1)
  ScrollToCar(PlayerCar,RaceWorld)

  def _lose_stock_life(reason):
    """Spend one stock life. Restart maze if any remain; else Game Over.
    Returns True if the round is finished (game over).
    """
    nonlocal PlayerStockLives, RaceWorld, FuelDots, FuelCount
    nonlocal FuelDotsLeft, EnemyCars, EnemyCarCount, out_of_fuel_since
    nonlocal ClosestFuel
    PlayerStockLives -= 1
    print("[RallyDot] Life lost ({}) — stock lives left: {}".format(
      reason, PlayerStockLives))
    out_of_fuel_since = None
    if PlayerStockLives <= 0:
      try:
        _ch, _cv = camera_for_car(PlayerCar, RaceWorld)
        RaceWorld.DisplayWindow(_ch, _cv, do_swap=False)
        if reason == "out_of_fuel":
          try:
            _draw_out_of_fuel_overlay(
              LED.Canvas, PlayerCar.h - _ch, PlayerCar.v - _cv)
          except Exception:
            pass
        _show()
        time.sleep(0.35)
      except Exception:
        pass
      try:
        PlayGameOverFall(StopEvent=StopEvent)
      except Exception as e:
        import traceback
        print("[RallyDot] Game Over sequence failed:", e)
        traceback.print_exc()
      return True
    # Restart full map/maze for the next life
    try:
      ShowShortMessage(RaceWorld, PlayerCar, "boom")
    except Exception:
      pass
    RaceWorld, FuelDots, FuelCount, FuelDotsLeft, EnemyCars, EnemyCarCount = (
      ResetRaceMap(PlayerCar, enemy_car_count=EnemyCarCount))
    ClosestFuel = 0
    ScrollToCar(PlayerCar, RaceWorld)
    return False

  #--------------------------------------------------------
  #-- MAIN TIMER LOOP                                    --
  #--------------------------------------------------------
    
  start_time = time.time()
  while (LevelFinished == 'N' and PlayerStockLives > 0):
    if _stop(StopEvent):
      print("[RallyDot] StopEvent")
      return
    try:
      _, minutes, _ = LED.GetElapsedTime(start_time, time.time())
      if minutes >= Duration:
        print("[RallyDot] Duration reached")
        return
    except Exception:
      pass
    #Reset Variables
    moves = moves + 1
    Key   = ''
    LevelCount = LevelCount + 1
    LetEnemyRespawn = 1
    


    #Check for keyboard input
    if on_tick(moves, KEYBOARD_SPEED):
      Key = poll_keyboard_safe()
      if (Key == 'q'):
        LevelFinished = 'Y'
        Finished      = 'Y'
        return


    #--------------------------------
    #-- Player actions             --
    #--------------------------------

    if (PlayerCar.lives > 0):
      gas = getattr(PlayerCar, "gas", PLAYER_GAS_MAX)
      out_of_fuel = gas <= 0

      # Empty tank → show OUT OF FUEL, then lose a life (map restart or GO)
      if out_of_fuel:
        if out_of_fuel_since is None:
          out_of_fuel_since = time.time()
          print("[RallyDot] OUT OF FUEL at", PlayerCar.h, PlayerCar.v,
                "— life pending (stock {})".format(PlayerStockLives))
        elif (time.time() - out_of_fuel_since) >= OUT_OF_FUEL_HOLD_SEC:
          if _lose_stock_life("out_of_fuel"):
            return
          continue
      else:
        out_of_fuel_since = None

      if on_tick(moves, PlayerCar.speed) and not out_of_fuel:
        #Find closest Fuel
        ClosestFuel,ClosestFuelDistance, FuelDotsLeft = FindClosestFuel(PlayerCar,FuelDots,FuelCount)
        #print ("destination: ",PlayerCar.destination)
        
        #If no destination yet, set to nearest fuel if it exists
        if (ClosestFuelDistance <= PlayerCar.radarrange 
            and FuelDotsLeft > 0 
            and PlayerCar.destination == ""):
          PlayerCar.destination = FuelDots[ClosestFuel].name

        
        #Perform radar check around car.  If no solid objects, then move towards destination
        if (FuelDotsLeft > 0 and PlayerCar.destination == "Fuel"):
          TurnTowardsFuelIfThereIsRoom(PlayerCar,RaceWorld.Playfield,FuelDots,ClosestFuel)
          
        #Move car and determine direction
        old_h, old_v = PlayerCar.h, PlayerCar.v
        MoveCar(PlayerCar,RaceWorld.Playfield)
        # Drain tank when the car actually moves
        if PlayerCar.h != old_h or PlayerCar.v != old_v:
          PlayerCar.gas = max(0, getattr(PlayerCar, "gas", PLAYER_GAS_MAX) - PLAYER_GAS_DRAIN)
        direction = PlayerCar.direction
        AdjustCarColor(PlayerCar)

      elif on_tick(moves, PlayerCar.speed) and out_of_fuel:
        # Still track fuel counts for map logic while stranded
        ClosestFuel,ClosestFuelDistance, FuelDotsLeft = FindClosestFuel(PlayerCar,FuelDots,FuelCount)

    # Player lost all health this life → lose a stock life, restart maze
    elif (PlayerCar.lives <= 0):
      if _lose_stock_life("crash"):
        return
      continue
  
          
    #--------------------------------
    #-- Enemy actions              --
    #--------------------------------

    #keep cars alive until they finish exploding
    #Remember, not everythign gets displayed so be careful with how the display module handles explosions and alive
    #maybe have a separate function to handle all exploding cars

    
    #---------------------
    #-- move enemy cars --
    #---------------------

    EnemyCount = 0
    ACarHasExploded = 0
    
    for x in range (EnemyCarCount):
      if (EnemyCars[x].alive == 1):
        EnemyCount = EnemyCount + 1
        if on_tick(moves, EnemyCars[x].speed * ENEMY_SPEED_SCALE):
            
          #Check radar.  If player is near by, move towards
          if on_tick(moves, EnemyRadarSpeed * ENEMY_SPEED_SCALE):
            Distance = GetDistanceBetweenCars(EnemyCars[x],PlayerCar)

            if (Distance < EnemyCars[x].radarrange):
              TurnTowardsCar(EnemyCars[x],PlayerCar)
              EnemyCars[x].destination = "PlayerCar"
              EnemyCars[x].ShiftGear("up")
            else:
              EnemyCars[x].ShiftGear("down")
              EnemyCars[x].destination = ""
  
          EnemyCars[x].direction = LED.ChanceOfTurning8Way(EnemyCars[x].direction,10)
          MoveCar(EnemyCars[x],RaceWorld.Playfield)

          
          #print ("Enemy car X lives heat: ",x,EnemyCars[x].lives, EnemyCars[x].r)
          #Reduce enemy health and speed if they are overheated
          if (EnemyCars[x].name == "Enemy" and EnemyCars[x].r >= 255):
            EnemyCars[x].lives = EnemyCars[x].lives -1
            EnemyCars[x].ShiftGear("down")

          #if they are out of health, they detonate
          if (EnemyCars[x].lives <= 0):
            ACarHasExploded = 1
            #print ("Enemy car[x] exploding: ",x)        
            EnemyCars[x].exploding = 1
            RallyDotBlowUp(EnemyCars[x],RaceWorld.Playfield)



      

      #spawn new enemy      
      else:
        if on_tick(moves, EnemyCarSpawnSpeed):
          if (LetEnemyRespawn == 1):
            EnemyCars[x].alive = 1
            EnemyCars[x].speed = 1
            EnemyCars[x].radar = 30
            EnemyCars[x].lives = 5
            LetEnemyRespawn    = 0
          
        

    #------------------------------------
    #-- Deal with explosions and death --
    #------------------------------------
        
    #Display exploding objects 
    if (ACarHasExploded ==1):
      _ch,_cv=camera_for_car(PlayerCar,RaceWorld); RaceWorld.DisplayExplodingObjects(_ch,_cv)

           
    print ("Moves: ",moves,"Enemy Alive:",EnemyCount,
           " Lives:",PlayerStockLives," HP:",PlayerCar.lives,
           " Gas:",getattr(PlayerCar,"gas",0),
           " Speed: ",PlayerCar.speed,end="\r")
          
    
    #-------------------------
    #- Main Display         --
    #-------------------------

    #-----------------------------------------------------------
    #The cars move virtually on the playfield                 --
    #We can display the screen from any point of view we like --
    #For now we show what the player car is doing             --
    #-----------------------------------------------------------
    
    #These display coordinates are from the point of view of the entire playfield
    #print ("PlayerCar hv:",PlayerCar.h,PlayerCar.v)
 
    
    # Refresh clock digits when the minute changes; keep pinned upper-right
    if on_tick(moves, CheckClockSpeed):
      try:
        hhmm = time.strftime("%H%M")
        if hhmm != getattr(ClockSprite, "_last_hhmm", None):
          ClockSprite = LED.CreateClockSprite(12)
          ClockSprite.on = 1
          ClockSprite._last_hhmm = hhmm
        CheckClockTimer(ClockSprite)
      except Exception:
        CheckClockTimer(ClockSprite)

    _ch, _cv = camera_for_car(PlayerCar, RaceWorld)
    # Always draw map + clock (upper-right); no slide / hide cycle
    RaceWorld.DisplayWindow(_ch, _cv, do_swap=False)
    draw_clock_overlay(ClockSprite)

    # OUT OF FUEL: red ring around car + label (always after map, before swap)
    if getattr(PlayerCar, "gas", 1) <= 0:
      sx = PlayerCar.h - _ch
      sy = PlayerCar.v - _cv
      try:
        _draw_out_of_fuel_overlay(LED.Canvas, sx, sy)
      except Exception as e:
        print("[RallyDot] OOF overlay:", e)
    _show()
    
    
    #print ("moves",moves,"Carh Carv ", PlayerCar.h,PlayerCar.v,"Direction",PlayerCar.direction,"Destination ",PlayerCar.destination,ClosestFuel,"FuelDotsLeft",FuelDotsLeft,FuelDots[0].dh, FuelDots[0].dv,"PlayerCar.lives",PlayerCar.lives,"Player.b",PlayerCar.b,"      ",end="\r")
    #sys.stdout.flush()

    
    
    #-------------------------
    #-- Single map only (ACTIVE_MAP_LEVEL) — no multi-map advance --
    #-------------------------
    if moves >= MaxMoves:
      try:
        PlayGameOverFall(StopEvent=StopEvent)
      except Exception as e:
        import traceback
        print("[RallyDot] Game Over sequence failed:", e)
        traceback.print_exc()
        try:
          LED.ClearBigLED()
          LED.ShowScrollingBanner("Game Over", SDMedPurpleR, SDMedPurpleG, SDMedPurpleB, SCROLL_SLEEP * 0.75)
        except Exception:
          pass
      return

    # Optional: when all fuel cleared, respawn fuel on same map (stay on map 6)
    if FuelDotsLeft == 0 and FuelCount > 0:
      try:
        ShowShortMessage(RaceWorld, PlayerCar, "smile")
      except Exception:
        pass
      FuelDots = [CarDot(
          h=8, v=8, dh=-1, dv=-1,
          r=SDLowYellowR, g=SDLowYellowG, b=SDLowYellowB,
          direction=1, scandirection=1, gear=[], speed=1, currentgear=1,
          alive=1, lives=1, name="Fuel", score=0, exploding=0,
          radarrange=0, destination="",
      ) for _ in range(FuelCount)]
      CopyFuelDotsToPlayfield(FuelDots, FuelCount, RaceWorld)
      FuelDotsLeft = FuelCount
      PlayerCar.destination = ""
      print("[RallyDot] fuel respawned on same map")

    # Clock stays always-on upper-right; minute refresh handled above

    
    
  





#--------------------------------------
#--            PacDot                --
#--------------------------------------


# Note:
#   - after ghosts turn back to normal from blue, their dots don't disappear and I think the numdots counter gets messed up
#








#------------------------------------------------------------------------------
# Title intro — letters scream past, then slam into "RALLY DOT"
#------------------------------------------------------------------------------
TITLE_LINE1 = "RALLY"
TITLE_LINE2 = "DOT"
TITLE_LETTER_ZOOM = 2
TITLE_LETTER_GAP = 1
TITLE_LINE_GAP = 2
TITLE_LETTER_RGB = (0, 220, 80)          # race green
TITLE_LETTER_SHADOW_RGB = (0, 40, 15)
TITLE_FLYPASS_SPEED = 14.0              # px per step unit — scream past (right)
TITLE_SLAM_SPEED = 9.0                  # approach speed when parking from the right
TITLE_SLAM_STAGGER = 0.06               # seconds between letters returning
TITLE_SLAM_EPS = 1.2                    # snap distance for hard park
TITLE_HOLD_SECONDS = 1.15
TITLE_INTRO_MAX_SECONDS = 16.0
TITLE_BEAT_AFTER_FLYPASS = 0.16         # brief black pause before return


def _title_stop(StopEvent):
  return _stop(StopEvent)


def _title_letter_sprite(char):
  ch = char.upper()
  if not ("A" <= ch <= "Z"):
    return None
  idx = ord(ch) - ord("A")
  try:
    return LED.TrimSprite(copy.deepcopy(LED.AlphaSpriteList[idx]))
  except Exception:
    return None


def _sprite_pixels_zoomed(sprite, zoom, rgb, shadow_rgb):
  pixels = []
  shadow_pixels = []
  sw, sh = sprite.width, sprite.height
  for count in range(sw * sh):
    if sprite.grid[count] == 0:
      continue
    y, x = divmod(count, sw)
    for zv in range(zoom):
      for zh in range(zoom):
        pixels.append((x * zoom + zh, y * zoom + zv, rgb))
        shadow_pixels.append((x * zoom + zh + 1, y * zoom + zv + 1, shadow_rgb))
  return pixels, shadow_pixels, sw * zoom, sh * zoom


class TitleLetter(object):
  """Letter used for fly-past and park phases of the title intro."""

  def __init__(self, char, pixels, shadow_pixels, width, height, rest_x, rest_y, line_index=0):
    self.char = char
    self.pixels = pixels
    self.shadow_pixels = shadow_pixels
    self.width = width
    self.height = height
    self.rest_x = float(rest_x)
    self.rest_y = float(rest_y)
    self.line_index = int(line_index)
    self.x = float(rest_x)
    self.y = float(rest_y)
    self.vx = 0.0
    self.vy = 0.0
    self.visible = False
    self.settled = False
    self.slam_delay = 0.0
    self.slam_started = False
    self.slam_dir = -1.0  # park arrives from the right, moving left

  def draw(self, canvas, panel_w, panel_h):
    if not self.visible and not self.settled:
      return
    sx = int(round(self.x))
    sy = int(round(self.y))
    set_pixel = canvas.SetPixel
    for dx, dy, rgb in self.shadow_pixels:
      px, py = sx + dx, sy + dy
      if 0 <= px < panel_w and 0 <= py < panel_h:
        set_pixel(px, py, *rgb)
    for dx, dy, rgb in self.pixels:
      px, py = sx + dx, sy + dy
      if 0 <= px < panel_w and 0 <= py < panel_h:
        set_pixel(px, py, *rgb)

  def force_settle(self):
    self.x = self.rest_x
    self.y = self.rest_y
    self.vx = self.vy = 0.0
    self.visible = True
    self.settled = True
    self.slam_started = True

  def prepare_park_from_right(self, panel_w, index, total):
    """Start off the right edge; travel left into rest position."""
    # Farther-right start for later letters so they stream in leftward
    margin = self.width + 12 + (total - 1 - index) * 6 + index * 2
    self.x = float(panel_w + margin)
    self.y = float(self.rest_y)
    self.slam_dir = -1.0
    self.vx = self.vy = 0.0
    self.visible = False
    self.settled = False
    self.slam_started = False
    self.slam_delay = index * TITLE_SLAM_STAGGER

  def update_park(self, step, elapsed):
    """Move left from off-right into rest (park)."""
    if self.settled:
      self.x = self.rest_x
      self.y = self.rest_y
      return
    if elapsed < self.slam_delay:
      return
    self.slam_started = True
    self.visible = True

    dx = self.rest_x - self.x
    dy = self.rest_y - self.y
    dist = (dx * dx + dy * dy) ** 0.5

    if dist <= TITLE_SLAM_EPS:
      self.x = self.rest_x
      self.y = self.rest_y
      self.vx = self.vy = 0.0
      self.settled = True
      return

    speed = TITLE_SLAM_SPEED
    if dist > 0:
      self.vx = (dx / dist) * speed
      self.vy = (dy / dist) * speed
    self.x += self.vx * step
    self.y += self.vy * step

    # Moving left: lock when we reach/cross rest_x
    if self.x <= self.rest_x:
      self.x = self.rest_x
      self.y = self.rest_y
      self.vx = self.vy = 0.0
      self.settled = True


def _build_title_letters(panel_w, panel_h):
  """Build TitleLetter list for two lines: RALLY / DOT, centered.
  Returns (flat_letters, word_groups) where word_groups is [line0_letters, line1_letters].
  """
  lines = [TITLE_LINE1, TITLE_LINE2]
  line_specs = []
  max_letter_h = 0

  for line in lines:
    specs = []
    for char in line:
      if char == " ":
        continue
      sprite = _title_letter_sprite(char)
      if sprite is None:
        continue
      pixels, shadow_pixels, letter_w, letter_h = _sprite_pixels_zoomed(
        sprite, TITLE_LETTER_ZOOM, TITLE_LETTER_RGB, TITLE_LETTER_SHADOW_RGB,
      )
      specs.append((char, pixels, shadow_pixels, letter_w, letter_h))
      if letter_h > max_letter_h:
        max_letter_h = letter_h
    line_specs.append(specs)

  if not any(line_specs):
    return [], []

  total_h = max_letter_h * len(line_specs) + TITLE_LINE_GAP * max(0, len(line_specs) - 1)
  top_y = max(0, (panel_h - total_h) // 2)

  letters = []
  word_groups = []
  for line_i, specs in enumerate(line_specs):
    group = []
    if not specs:
      word_groups.append(group)
      continue
    total_w = sum(s[3] for s in specs) + TITLE_LETTER_GAP * max(0, len(specs) - 1)
    x_cursor = max(0, (panel_w - total_w) // 2)
    rest_y = top_y + line_i * (max_letter_h + TITLE_LINE_GAP)
    for char, pixels, shadow_pixels, letter_w, letter_h in specs:
      L = TitleLetter(
        char, pixels, shadow_pixels, letter_w, letter_h,
        x_cursor, rest_y + (max_letter_h - letter_h),
        line_index=line_i,
      )
      letters.append(L)
      group.append(L)
      x_cursor += letter_w + TITLE_LETTER_GAP
    word_groups.append(group)
  return letters, word_groups


def _draw_title_frame(canvas, letters, panel_w, panel_h, only=None):
  """Black frame + letters. only=list of letters to draw, or None for all visible."""
  canvas.Fill(0, 0, 0)
  draw_list = only if only is not None else letters
  for letter in draw_list:
    letter.draw(canvas, panel_w, panel_h)
  return LED.TheMatrix.SwapOnVSync(canvas)


def _paint_title_letters_to_screen(letters, panel_w, panel_h):
  """Freeze settled title onto the matrix for a short hold."""
  try:
    LED.ClearBigLED()
    LED.ClearBuffers()
  except Exception:
    pass
  for letter in letters:
    letter.force_settle()
    sx = int(round(letter.x))
    sy = int(round(letter.y))
    for dx, dy, rgb in letter.shadow_pixels:
      px, py = sx + dx, sy + dy
      if 0 <= px < panel_w and 0 <= py < panel_h:
        LED.setpixel(px, py, *rgb)
    for dx, dy, rgb in letter.pixels:
      px, py = sx + dx, sy + dy
      if 0 <= px < panel_w and 0 <= py < panel_h:
        LED.setpixel(px, py, *rgb)


def _title_flypass_word(canvas, word_letters, panel_w, panel_h, StopEvent):
  """
  One whole word screams left→right across the panel (letters keep spacing),
  at rest_y for that line. Returns (canvas, aborted).
  """
  if not word_letters:
    return canvas, False

  min_rest_x = min(L.rest_x for L in word_letters)
  # Start fully off the left edge, preserve letter spacing
  for L in word_letters:
    L.x = float(-8 + (L.rest_x - min_rest_x) - L.width)
    L.y = float(L.rest_y)
    L.visible = True
    L.settled = False

  last = time.time()
  # Done when the leftmost letter is fully past the right edge
  while True:
    if _title_stop(StopEvent):
      for L in word_letters:
        L.visible = False
      return canvas, True
    leftmost = min(L.x for L in word_letters)
    if leftmost > panel_w + 2:
      break
    now = time.time()
    dt = max(0.001, now - last)
    last = now
    step = min(3.5, dt * 30.0)
    for L in word_letters:
      L.x += TITLE_FLYPASS_SPEED * step
    if canvas is not None:
      canvas = _draw_title_frame(canvas, word_letters, panel_w, panel_h)
    else:
      LED.ClearBigLED()
      for L in word_letters:
        sx = int(round(L.x))
        sy = int(round(L.y))
        for dx, dy, rgb in L.pixels:
          if 0 <= sx + dx < panel_w and 0 <= sy + dy < panel_h:
            LED.setpixel(sx + dx, sy + dy, *rgb)
      time.sleep(0.012)

  for L in word_letters:
    L.visible = False
  if canvas is not None:
    canvas.Fill(0, 0, 0)
    canvas = LED.TheMatrix.SwapOnVSync(canvas)
  else:
    try:
      LED.ClearBigLED()
    except Exception:
      pass
  return canvas, False


def PlayRallyDotTitleIntro(StopEvent=None):
  """
  Both words (RALLY, DOT) scream left→right very fast,
  then return from the right and park into place moving left.
  """
  refresh_view_size()
  panel_w = VIEW_W
  panel_h = VIEW_H
  letters, word_groups = _build_title_letters(panel_w, panel_h)
  if not letters:
    print("[RallyDot] Title intro skipped (no letter sprites)")
    return

  if _title_stop(StopEvent):
    print("[RallyDot] Title intro skipped (StopEvent)")
    return

  print("[RallyDot] Title intro — words fly right, park from left")
  try:
    canvas = LED.TheMatrix.CreateFrameCanvas()
  except Exception:
    canvas = None

  intro_start = time.time()
  aborted = False

  try:
    # --- Phase 1: each word screams past L→R (very fast) ---
    for word in word_groups:
      if not word:
        continue
      if _title_stop(StopEvent) or (time.time() - intro_start) >= TITLE_INTRO_MAX_SECONDS:
        aborted = True
        break
      canvas, stop = _title_flypass_word(canvas, word, panel_w, panel_h, StopEvent)
      if stop:
        aborted = True
        break

    if aborted or _title_stop(StopEvent):
      pass
    else:
      # Brief black beat before the return
      beat_until = time.time() + TITLE_BEAT_AFTER_FLYPASS
      while time.time() < beat_until and not _title_stop(StopEvent):
        if canvas is not None:
          canvas.Fill(0, 0, 0)
          canvas = LED.TheMatrix.SwapOnVSync(canvas)
        time.sleep(0.02)

      # --- Phase 2: come back from the right, move left, park ---
      total = len(letters)
      for i, letter in enumerate(letters):
        letter.prepare_park_from_right(panel_w, i, total)

      park_start = time.time()
      last_frame = park_start
      hold_start = None

      while True:
        if _title_stop(StopEvent):
          aborted = True
          break
        now = time.time()
        if (now - intro_start) >= TITLE_INTRO_MAX_SECONDS:
          for letter in letters:
            letter.force_settle()
          break

        frame_dt = max(0.001, now - last_frame)
        last_frame = now
        step = min(3.0, frame_dt * 30.0)
        elapsed = now - park_start

        for letter in letters:
          letter.update_park(step, elapsed)

        if hold_start is None and all(L.settled for L in letters):
          hold_start = now
        if hold_start is not None and (now - hold_start) >= TITLE_HOLD_SECONDS:
          break

        if canvas is not None:
          canvas = _draw_title_frame(canvas, letters, panel_w, panel_h)
        else:
          LED.ClearBigLED()
          for letter in letters:
            if not (letter.visible or letter.settled):
              continue
            sx = int(round(letter.x))
            sy = int(round(letter.y))
            for dx, dy, rgb in letter.pixels:
              if 0 <= sx + dx < panel_w and 0 <= sy + dy < panel_h:
                LED.setpixel(sx + dx, sy + dy, *rgb)
          time.sleep(0.02)

  except KeyboardInterrupt:
    aborted = True

  if not aborted and not _title_stop(StopEvent):
    _paint_title_letters_to_screen(letters, panel_w, panel_h)
    hold_until = time.time() + 0.35
    while time.time() < hold_until and not _title_stop(StopEvent):
      time.sleep(0.05)

  try:
    LED.ClearBigLED()
    LED.ClearBuffers()
  except Exception:
    pass


#------------------------------------------------------------------------------
# Game Over — Skyfall-style drop, bounce to center, shatter into particles
#------------------------------------------------------------------------------
GO_WORD = "GAMEOVER"
GO_LETTER_ZOOM = 1
GO_LETTER_GAP = 1
GO_LETTER_RGB = (220, 40, 80)
GO_LETTER_SHADOW_RGB = (40, 5, 15)
GO_STAGGER = 0.12
GO_GRAVITY = 0.62
GO_BOUNCE_DAMP = 0.44
GO_SETTLE_V = 0.38
GO_MAX_BOUNCES = 4
GO_HOLD_SECONDS = 0.85
GO_PARTICLE_GRAVITY = 0.12   # fall until off-screen (no fixed life kill)
GO_PARTICLE_MARGIN = 1       # fully clear of panel by this many px
GO_MAX_SECONDS = 45.0        # safety cap for fall + hold + shatter start
GO_PARTICLE_MAX_SECONDS = 90.0  # safety cap after shatter only


class GoDebris(object):
  """Single pixel debris after Game Over letters shatter.
  Stays alive until it leaves the panel (not a fixed lifetime).
  """

  def __init__(self, x, y, r, g, b, vx, vy):
    self.x = float(x)
    self.y = float(y)
    self.r, self.g, self.b = int(r), int(g), int(b)
    self.vx = float(vx)
    self.vy = float(vy)
    self.age = 0.0  # for optional soft fade only

  def on_screen(self, panel_w, panel_h, margin=None):
    """True while particle is still inside (or barely outside) the panel."""
    if margin is None:
      margin = GO_PARTICLE_MARGIN
    return (
      -margin <= self.x < panel_w + margin
      and -margin <= self.y < panel_h + margin
    )

  def update(self, step):
    self.vy += GO_PARTICLE_GRAVITY * step
    self.x += self.vx * step
    self.y += self.vy * step
    self.age += step

  def draw(self, canvas, panel_w, panel_h):
    px = int(round(self.x))
    py = int(round(self.y))
    if 0 <= px < panel_w and 0 <= py < panel_h:
      # Mild age fade so old debris softens, but never kills visibility early
      fade = max(0.35, 1.0 - self.age * 0.008)
      canvas.SetPixel(
        px, py,
        min(255, int(self.r * fade)),
        min(255, int(self.g * fade)),
        min(255, int(self.b * fade)),
      )


class FallLetter(object):
  """Letter drops from above, bounces, settles at center rest position."""

  def __init__(self, char, pixels, shadow_pixels, width, height,
               rest_x, rest_y, drop_delay):
    self.char = char
    self.pixels = pixels
    self.shadow_pixels = shadow_pixels
    self.width = width
    self.height = height
    self.rest_x = float(rest_x)
    self.rest_y = float(rest_y)
    self.x = float(rest_x)
    self.y = float(-height - 8)
    self.vy = 0.0
    self.drop_delay = float(drop_delay)
    self.dropped = False
    self.settled = False
    self.shattered = False
    self.bounce_count = 0

  def update(self, step, elapsed):
    if self.settled or self.shattered:
      if self.settled and not self.shattered:
        self.y = self.rest_y
      return
    if elapsed < self.drop_delay:
      return
    self.dropped = True
    self.vy += GO_GRAVITY * step
    self.y += self.vy * step
    if self.y >= self.rest_y:
      self.y = self.rest_y
      if abs(self.vy) < GO_SETTLE_V or self.bounce_count >= GO_MAX_BOUNCES:
        self.vy = 0.0
        self.settled = True
      else:
        self.vy = -abs(self.vy) * GO_BOUNCE_DAMP
        self.bounce_count += 1

  def force_settle(self):
    self.x = self.rest_x
    self.y = self.rest_y
    self.vy = 0.0
    self.dropped = True
    self.settled = True

  def draw(self, canvas, panel_w, panel_h):
    if self.shattered:
      return
    sx = int(round(self.x))
    sy = int(round(self.y))
    set_px = canvas.SetPixel
    for dx, dy, rgb in self.shadow_pixels:
      px, py = sx + dx, sy + dy
      if 0 <= px < panel_w and 0 <= py < panel_h:
        set_px(px, py, *rgb)
    for dx, dy, rgb in self.pixels:
      px, py = sx + dx, sy + dy
      if 0 <= px < panel_w and 0 <= py < panel_h:
        set_px(px, py, *rgb)


def _build_gameover_letters(panel_w, panel_h):
  specs = []
  for char in GO_WORD:
    if char == " ":
      continue
    sprite = _title_letter_sprite(char)
    if sprite is None:
      continue
    pixels, shadow_pixels, letter_w, letter_h = _sprite_pixels_zoomed(
      sprite, GO_LETTER_ZOOM, GO_LETTER_RGB, GO_LETTER_SHADOW_RGB,
    )
    specs.append((char, pixels, shadow_pixels, letter_w, letter_h))
  if not specs:
    return []

  total_width = sum(s[3] for s in specs) + GO_LETTER_GAP * max(0, len(specs) - 1)
  # Fit: if too wide, still center (may clip slightly on tiny panels)
  start_x = max(0, (panel_w - total_width) // 2)
  letter_height = max(s[4] for s in specs)
  rest_y = max(0, (panel_h - letter_height) // 2)  # vertically centered

  letters = []
  x_cursor = start_x
  for index, (char, pixels, shadow_pixels, letter_w, letter_h) in enumerate(specs):
    y_off = letter_height - letter_h
    letters.append(FallLetter(
      char, pixels, shadow_pixels, letter_w, letter_h,
      x_cursor, rest_y + y_off,
      drop_delay=index * GO_STAGGER,
    ))
    x_cursor += letter_w + GO_LETTER_GAP
  return letters


def _shatter_letters(letters, particles):
  for letter in letters:
    if letter.shattered:
      continue
    sx = int(round(letter.x))
    sy = int(round(letter.y))
    for dx, dy, rgb in letter.pixels:
      particles.append(GoDebris(
        sx + dx, sy + dy, rgb[0], rgb[1], rgb[2],
        random.uniform(-1.6, 1.6),
        random.uniform(-2.2, 0.5),
      ))
    for dx, dy, rgb in letter.shadow_pixels:
      particles.append(GoDebris(
        sx + dx, sy + dy, rgb[0], rgb[1], rgb[2],
        random.uniform(-1.2, 1.2),
        random.uniform(-1.6, 0.4),
      ))
    letter.shattered = True


def PlayGameOverFall(StopEvent=None):
  """
  GAMEOVER letters fall from the sky, bounce into a centered rest pose,
  hold briefly, then disintegrate into particles (Skyfall-style).
  """
  refresh_view_size()
  panel_w, panel_h = VIEW_W, VIEW_H
  letters = _build_gameover_letters(panel_w, panel_h)
  if not letters:
    print("[RallyDot] Game Over fall skipped (no sprites)")
    return

  print("[RallyDot] Game Over — fall / bounce / shatter")
  try:
    canvas = LED.TheMatrix.CreateFrameCanvas()
  except Exception:
    canvas = LED.Canvas

  particles = []
  start = time.time()
  last = start
  hold_start = None
  shattered = False
  particle_start = None

  try:
    while True:
      if _stop(StopEvent):
        break
      now = time.time()
      elapsed = now - start

      frame_dt = max(0.001, now - last)
      last = now
      step = min(3.0, frame_dt * 30.0)

      if not shattered:
        # Only cap pre-shatter phase; particle phase waits for off-screen
        if elapsed >= GO_MAX_SECONDS:
          for letter in letters:
            letter.force_settle()
          _shatter_letters(letters, particles)
          shattered = True
          particle_start = now
          print("[RallyDot] Game Over — particles (forced)")
        else:
          for letter in letters:
            letter.update(step, elapsed)
          if hold_start is None and all(L.settled for L in letters):
            hold_start = now
          if hold_start is not None and (now - hold_start) >= GO_HOLD_SECONDS:
            _shatter_letters(letters, particles)
            shattered = True
            particle_start = now
            print("[RallyDot] Game Over — particles (until all off-screen)")
      else:
        for p in particles:
          p.update(step)
        # Keep going until every debris pixel has left the panel
        particles = [p for p in particles if p.on_screen(panel_w, panel_h)]
        if not particles:
          time.sleep(0.12)
          break
        # Safety only — should not hit if gravity clears the panel
        if particle_start is not None and (now - particle_start) >= GO_PARTICLE_MAX_SECONDS:
          print("[RallyDot] Game Over — particle safety timeout")
          break

      try:
        canvas.Fill(0, 0, 0)
      except Exception:
        pass
      if not shattered:
        for letter in letters:
          if letter.dropped or letter.settled:
            letter.draw(canvas, panel_w, panel_h)
      else:
        for p in particles:
          p.draw(canvas, panel_w, panel_h)
      try:
        canvas = LED.TheMatrix.SwapOnVSync(canvas)
      except Exception:
        _show()

  except KeyboardInterrupt:
    pass

  try:
    LED.ClearBigLED()
    LED.ClearBuffers()
  except Exception:
    pass


def LaunchRallyDot(Duration=10, ShowIntro=True, StopEvent=None):
  """LEDcommander / panel entry point. Duration in minutes."""
  refresh_view_size()
  _apply_full_brightness()
  if ShowIntro:
    try:
      LED.LoadConfigData()
    except Exception:
      pass
    try:
      PlayRallyDotTitleIntro(StopEvent=StopEvent)
    except Exception as e:
      print("[RallyDot] title intro failed:", e)

  LED.ClearBigLED()
  LED.ClearBuffers()
  PlayRallyDot(Duration=Duration, StopEvent=StopEvent)


if __name__ == "__main__":
  # Standalone: play forever (restart after Game Over / duration end)
  LED.Initialize()
  show_intro = True
  while True:
    try:
      print("[RallyDot] standalone round starting (intro={})".format(show_intro))
      LaunchRallyDot(Duration=100000, ShowIntro=show_intro, StopEvent=None)
    except KeyboardInterrupt:
      print("[RallyDot] standalone stopped by user")
      break
    except Exception as e:
      import traceback
      print("[RallyDot] standalone round error:", e)
      traceback.print_exc()
      time.sleep(1.0)
    show_intro = True  # title each round
    try:
      LED.ClearBigLED()
      LED.ClearBuffers()
    except Exception:
      pass
    time.sleep(0.35)
