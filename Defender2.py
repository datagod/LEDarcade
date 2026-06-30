
#Standardize alive = True/False not 1/0
#change enemyship garbage collection to the same as human



#!/usr/bin/env python
#print("moves:",moves,end='\r', flush=True)
#notes: check all playfield[v][h] in all versions to make sure v comes first.  I found one where it was switched
#       and this may account for when the zombie dots don't die
# - ship objects that also have a sprite should have
#   their HV co-ordinates looked at.  We want to draw the sprite around the center of the sprite, not the corner
#   Look at SpaceDot homing missile for an example.
#------------------------------------------------------------------------------



#------------------------------------------------------------------------------
#                                                                            --
#  ____  _____ _____ _____ _   _ ____  _____ ____                            --
# |  _ \| ____|  ___| ____| \ | |  _ \| ____|  _ \                           --
# | | | |  _| | |_  |  _| |  \| | | | |  _| | |_) |                          --
# | |_| | |___|  _| | |___| |\  | |_| | |___|  _ <                           --
# |____/|_____|_|   |_____|_| \_|____/|_____|_| \_\                          -- 
#                                                                            --
#------------------------------------------------------------------------------

#offender? yes! Indeed!!

#------------------------------------------------------------------------------
#  Arcade Retro Clock RGB
#  
#  Copyright 2021 William McEvoy
#  Metropolis Dreamware Inc.
#  william.mcevoy@gmail.com
#
#  NOT FOR COMMERCIAL USE
#  If you want to use my code for commercial purposes, contact William McEvoy
#  and we can make a deal.
#
#
#------------------------------------------------------------------------------
#   Version: 2.0                                                             --
#   Date:    June 25, 2026                                                   --
#   Reason:  Defender2 — fresh fork of Defender for experimentation          --
#------------------------------------------------------------------------------



#------------------------------------------------------------------------------
# Initialization Section                                                     --
#------------------------------------------------------------------------------
from __future__ import print_function


import LEDarcade as LED
LED.Initialize()

import copy
import random
import time

#from numba import njit  #high performance math
import numpy as np

import math
from datetime import datetime, timedelta
from rgbmatrix import graphics





random.seed()
start_time = time.time()






#-----------------------------
# Defender Global Variables --
#-----------------------------

#Sprite display locations
ClockH,      ClockV,      ClockRGB      = 0,0,  (0,100,0)
DayOfWeekH,  DayOfWeekV,  DayOfWeekRGB  = 0,6,  (150,0,0)
MonthH,      MonthV,      MonthRGB      = 0,12, (0,20,200)
DayOfMonthH, DayOfMonthV, DayOfMonthRGB = 2,18, (100,100,0)
CurrencyH,   CurrencyV,   CurrencyRGB   = 0,27, (0,150,0)

#Sprite filler tuple
SpriteFillerRGB = (0,4,0)

#GroundRGB = (random.randint(0,255),random.randint(0,255),random.randint(0,255))
DirtGreen     = (0,24,0)
SurfaceGreen  = (0,50,0)

DirtYellow    = (24,24,0)
SurfaceYellow = (54,54,0)

DirtPurple    = (20,0,20)
SurfacePurple = (50,0,50)

DirtOrange    = (30,10,0)
SurfaceOrange = (50,30,0)

GroundColorList = ((DirtGreen,SurfaceGreen),
                   (DirtYellow,SurfaceYellow),
                   (DirtPurple,SurfacePurple),
                   (DirtOrange,SurfaceOrange)
                  )
GroundColorCount = 4

ExplosionBrightnessModifier = 100  #used to increase brightness of particles
ExplosionR = 0
ExplosionG = 0
ExplosionB = 0



LaserR = 0
LaserG = 255
LaserB = 0
GROUND_LASER_MIN = 50
GROUND_LASER_MAX = 255

DefenderWorldWidth = 2048
MaxMountainHeight  = 16
HumanCount         = 15
EnemyShipCount     = 50
AddEnemyCount      = 50
SpawnNewEnemiesTargetCount = 5
SpawnNewHumansTargetCount  = 5
ShipTypes                  = 27
RedrawGroundWaveCount      = 5
ShowHumans                 = True
ShowEnemies                = True
ShowCountHUD               = False
BOMB_CRATER_SCALE          = 0.7
BOMB_FLASH_MAX_RADIUS      = 5
#GameSleep                  = 0.005



#Movement
DefenderSpeed              = 0.5
ReversingAdjustmentSpeed   = 0.25
ReversingSteps             = 64
OldSpeed                   = 0
SlowingDown                = 0
DefenderSpeedIncrement     = 0.25
DefenderMaxSpeed           = 5
DefenderMinSpeed           = 0.5
DefenderMoveUpRate         = 10
DefenderMoveDownRate       = 10
ReversingChance            = 2000
DefenderSpeedChangeChance  = 100
DefenderDirection          = 1
DefenderReversing          = 0
UpDownChance               = 150
HumanMoveChance        = 5
EnemyMoveSpeed         = 8            #lower is faster
GarbageCleanupChance   = 1000
GroundCleanupChance    = 500
GroundRadarChance      = 10
FrontRadarChance       = 15
ShootGroundShipCount   = 50
AttackDistance         = LED.HatWidth
HumanRunDistance       = LED.HatWidth

ShootWaitTime          = 0.5
EnemyFearFactor        = 10  #the lower the number, the more likely the enemy will run away
#Gravity
GroundParticleGravity  = 0.04
HumanParticleGravity   = 0.006
EnemyParticleGravity   = 0.01
BombGravity            = 0.0198
DevenderReversing      = 0
CurrentH               = 0
TargetH                = 0


#Bomb
DefenderBombVelocityH  =  0.6 
DefenderBombVelocityV  = -0.2
BlastFactor            = 4     
StrafeLaserStrength    = 5
LaserTurnOffChance     = 20
BombDropChance         = 75
RequestBombDrop        = False
RequestGroundLaser     = False
RequestedBombVelocityH = 0.2
RequestedBombVelocityV = 0.05
BombDetonationHeight   = 20
MaxBombBounces         = 3

#Human
HumanCountH = 25
HumanCountV = 0
HumanCountRGB = (100,0,200)

#Enemy
EnemyCountH = 10
EnemyCountV = 0
EnemyCountRGB = (10,0,200)

#Defender
DefenderStartH = 4


#change display based on display dimensions
if(LED.HatWidth > 60):
  EnemyCountH = 36
  HumanCountH = 50
  ClockZoom = 1
  DefenderStartH = 2
else:
  ClockZoom = 1



#---------------------------------------
#Variable declaration section
#---------------------------------------
ScrollSleep         = 0.025
TerminalTypeSpeed   = 0.02  #pause in seconds between characters
TerminalScrollSpeed = 0.02  #pause in seconds between new lines
CursorRGB           = (0,255,0)
CursorDarkRGB       = (0,50,0)


BrightRGB  = (0,200,0)
ShadowRGB  = (0,5,0)
KeyboardSpeed   = 500
CheckClockSpeed = 500

CheckTime        = 60







#------------------------------
# Sprites, Arrays, Functions --
#------------------------------


def is_alive(sprite):
    """Return True whether alive is stored as bool or 1/0."""
    return sprite.alive in (True, 1)


def chance(max_n):
    """Fast equivalent to random.randint(0, max_n) == 1."""
    return random.random() < (1.0 / (max_n + 1))


def chance_one(max_n):
    """Fast equivalent to random.randint(1, max_n) == 1."""
    return random.random() < (1.0 / max_n)


def count_alive(sprites):
    alive = 0
    for sprite in sprites:
        if is_alive(sprite):
            alive += 1
    return alive


class DefenderState:
    """Lightweight per-game defender position; rendering uses LED.Defender templates."""
    __slots__ = ("h", "v", "width")

    def __init__(self, template):
        self.h = 0
        self.v = 25
        self.width = template.width


def get_alive_human_coords_with_target(Humans, def_h, def_v):
    human_h = []
    human_v = []
    closest_human = None
    min_dist = 1e9

    for h in Humans:
        if is_alive(h):
            human_h.append(h.h)
            human_v.append(h.v)

            # Calculate Manhattan distance
            dist = abs(h.h - def_h) + abs(h.v - def_v)
            if dist < min_dist:
                min_dist = dist
                closest_human = h

    return (
        np.array(human_h, dtype=np.int32),
        np.array(human_v, dtype=np.int32),
        closest_human
    )



#@njit
def find_nearest_human(def_h, def_v, human_h_list, human_v_list):
    min_dist = 1e9
    target_h = -1
    target_v = -1

    for i in range(len(human_h_list)):
        h = human_h_list[i]
        v = human_v_list[i]
        dx = h - def_h
        dy = v - def_v
        dist = abs(dx) + abs(dy)  # Manhattan distance

        if dist < min_dist:
            min_dist = dist
            target_h = h
            target_v = v

    return target_h, target_v


def find_nearest_alive_human(Humans, playfield_h, playfield_v):
    """Nearest living human in playfield coordinates."""
    min_dist = 1e9
    target_h = -1
    target_v = -1

    for human in Humans:
        if not is_alive(human):
            continue
        dist = abs(human.h - playfield_h) + abs(human.v - playfield_v)
        if dist < min_dist:
            min_dist = dist
            target_h = human.h
            target_v = human.v

    return target_h, target_v


def apply_human_hunt_steering(Defender, gx, Humans, hat_height):
    """Steer toward the nearest human once all enemies are gone."""
    global DefenderSpeed

    playfield_h = round(gx + Defender.h)
    nearest_h, nearest_v = find_nearest_alive_human(
        Humans, playfield_h + 12, Defender.v,
    )
    if nearest_h < 0:
        return

    if nearest_v > Defender.v + 1:
        Defender.v = min(Defender.v + 2, hat_height - 3)
    elif nearest_v < Defender.v - 1:
        Defender.v = max(Defender.v - 2, 5)

    human_screen_h = nearest_h - round(gx)
    if human_screen_h > Defender.h + 12:
        DefenderSpeed = min(DefenderSpeed + DefenderSpeedIncrement * 2, DefenderMaxSpeed)
    elif human_screen_h < Defender.h - 2:
        DefenderSpeed = max(DefenderSpeed - DefenderSpeedIncrement, DefenderMinSpeed)



def DebugRGBMap(map, h, v, width, height, bomb_h=None, bomb_v=None):
    print("===============================================================")
    print(f"DEBUG RGB Map at origin H={h}, V={v}, width={width}, height={height}")
    for y in range(v, v + height):
        row = ''
        for x in range(h, h + width):
            try:
                if bomb_h == x and bomb_v == y:
                    row += '**'  # mark bomb position
                else:
                    pixel = map[y][x]
                    if pixel == (0,0,0):
                        row += '  '  # empty
                    else:
                        row += '##'  # colored pixel
            except IndexError:
                row += '??'
        print(row)
    print("===============================================================")
  



def ScanInFrontOfDefender(H,V,Defender,DefenderPlayfield):
  
  ScanDirection = 2
  ScanH         = Defender.h + Defender.width  #start in front of ship
  ScanV         = Defender.v
    
  Item          = ''
  ItemList      = ['NULL']
  RadarRange    = LED.HatWidth - 14

  
  # x 1234567890...50
  
  
  try:
    for x in range(0,RadarRange,2):
      ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
      if(ScanH + H < DefenderPlayfield.width):
        Item = DefenderPlayfield.map[ScanV + V][ScanH + H].name
        ItemList.append(Item)
        break
  except:
    print("ERROR at location:",ScanV + V, ScanH + H)
  

    

  return ItemList



def ScanFarAway(H,V,Defender,DefenderPlayfield):
  #HV are the current upper left hand corner of the displayed playfield window
  ScanDirection = 2  # 4 way direction, 2 = right/east/forward

  ScanH         = Defender.h + Defender.width  #start in front of ship
  ScanV         = Defender.v
  Item          = ''
  ItemList      = [('EmptyObject',0,0)]
  RadarStart    = 5
  RadarStop     = LED.HatWidth
  RadarStepH    = 4
  RadarStepV    = 4
  
  
  # x 20...50
  
 
  try:
    found = False
    
    #Scan multiple lines
    for y in range (-2,4,RadarStepV):
      ScanV         = Defender.v + y
      #print("ScanFarAway: ScanH ScanV:",ScanH, ScanV)
      for x in range(RadarStart,RadarStop,RadarStepH):
        ScanH        = Defender.h + Defender.width + x
        ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
        #LED.TheMatrix.SetPixel(ScanH, ScanV,50,50,250)
        

        if(ScanH + H < DefenderPlayfield.width):
          
          if(DefenderPlayfield.map[ScanV][ScanH + H].alive == True):
            Item = DefenderPlayfield.map[ScanV][ScanH + H].name
            #print("SCAN - adding item to list:",DefenderPlayfield.map[ScanV][ScanH + H].name, DefenderPlayfield.map[ScanV][ScanH + H].h,DefenderPlayfield.map[ScanV ][ScanH + H].v)
            ItemList.append((Item,ScanH,ScanV))
            found = True
            #print("SCAN - Found:", DefenderPlayfield.map[ScanV][ScanH + H].name)
            break
      if(found == True):
        break

  except:
    print("ERROR at location:",ScanV , ScanH + H)

  return ItemList




def LookForTargets2(H,V,TargetName,Defender, DefenderPlayfield,Canvas,EnemyShips):
  #Draw a box, scan each location and make a list of enemies
  
  #HV are the current upper left hand corner of the displayed playfield window
  #Defender.h is relative to the LED display (64x32)


  if (DefenderDirection == 1):
    ScanStartH = H + Defender.width + Defender.h
    ScanStopH  = ScanStartH + 40
  else:
    ScanStartH = H 
    ScanStopH  = ScanStartH + 40 + Defender.h
    


  ScanStartV = Defender.v -5
  ScanStopV  = Defender.v + 8


  EnemyName = ''
  EnemyH    = 0
  EnemyV    = 0  

  if(ScanStartV <= 0):
    ScanStartV = 0
  if(ScanStartV >= LED.HatHeight - 1):
    ScanStartV = LED.HatHeight - 1

  if(ScanStartH >= DefenderPlayfield.width - 1):
    ScanStartH = DefenderPlayfield.width - 1

  #build list of enemies that fall within the radar box
  #graphics.DrawLine(Canvas,ScanStartH -H, ScanStartV,ScanStopH-H,ScanStartV, graphics.Color(0,255,0))
  #graphics.DrawLine(Canvas,ScanStartH-H, ScanStartV,ScanStartH-H,ScanStopV, graphics.Color(0,255,0))
  #graphics.DrawLine(Canvas,ScanStartH-H, ScanStopV,ScanStopH-H,ScanStopV, graphics.Color(0,255,0))
  #graphics.DrawLine(Canvas,ScanStopH-H,  ScanStopV,ScanStopH-H,ScanStartV, graphics.Color(0,255,0))
  

  #Built ItemList
  TargetFound = False
  ItemList = []
  for Ship in EnemyShips:
    #print('Scanning:',Ship.h,Ship.v)

    if(Ship.alive == True):

      #LED.TheMatrix.SetPixel(Ship.h - H,Ship.v,255,255,255)
      #graphics.DrawCircle(Canvas,Ship.h - H,Ship.v,4,graphics.Color(255,255,255))
      

      if((ScanStartH <= Ship.h <= ScanStopH) and (ScanStartV <= Ship.v <= ScanStopV)):
        TargetFound = True
        EnemyName = Ship.name
        EnemyH    = Ship.h
        EnemyV    = Ship.v
        #print("LookForTarget2: EnemyFound HV",EnemyH, EnemyV)
        break

  return EnemyName, EnemyH, EnemyV, TargetFound








def LookForTargets(H,V,TargetName,Defender, DefenderPlayfield,Canvas):
  ## Deprecaged, old and slow
  global RequestBombDrop
  #This is my tradition method of examining the playfield to see if enemies are within range of the radar probes
  #examining things one cell at a time


  #HV are the current upper left hand corner of the displayed playfield window
  EnemyName = 'EmptyObject'
  EnemyH    = -1
  EnemyV    = -1

  #To improve performance, we will not scan every pixel in radar range
  #Radar scanning will be interlaced
  #This procedure is called continuously so lets scan a net instead of a solid area
  #The size of the holes in the net is determined by ScanStep
  StartX    = H + LED.HatWidth -1
  StopX     = H + 10
  StartY    = 0
  StopY     = LED.HatHeight -1
  ScanStep  = 4
  
  #Add a bit of randomness to the vertical start pixel
  if random.randint(0,1) == 1:
    StartY = 1

  try:

    #Look at furthest part of the screen and start checking for enemies
    x = 0
    y = 0
    
    #Adjust StartX if it is too close to the end of the playfield
    if (StartX >= DefenderPlayfield.width - 1):
      StartX = DefenderPlayfield.width - 1
  
    #If an enemy is on screen, take note and exit the loops
    #sprites are usually bigger than a dot, so we use range step to increase speed of scan
    Found = False
    for x in range (StartX,0,-ScanStep):
      #print(DefenderPlayfield.map[y][x].name)
      for y in range(StartY,StopY,ScanStep):

        if(DefenderPlayfield.map[y][x].name == TargetName and DefenderPlayfield.map[y][x].alive == True):
          
          #print('Enemy found on radar:',DefenderPlayfield.map[y][x].h,DefenderPlayfield.map[y][x].v,DefenderPlayfield.map[y][x].name)


          #Move defender to follow enemy
          if(DefenderPlayfield.map[y][x].v < Defender.v):
            #we do randint to stop the jitteriness of ship moving up and down
            if chance(DefenderMoveUpRate):
              Defender.v = Defender.v - 1
            Found = True
            break
          elif(DefenderPlayfield.map[y][x].v > Defender.v):
            if chance(DefenderMoveDownRate):
              Defender.v = Defender.v + 1
            Found = True
            break
      if(Found == True):
        break


  except:
    print("ERROR at location: xy H StartX x",x,y,H, StartX,x)
    print("A stupid error has occurred when finding targets.  Please fix this soon.")

  
  #If an target was found, scan to see if it is in firing range
  TargetInRange = False
  if(Found == True):
    ItemList = ScanFarAway(H,V,Defender,DefenderPlayfield)
    #EnemyTargets = ['Human','EnemyShip']
    #print("Itemlist from Scanner:")
    #print(ItemList)
    
    for i in range (0,len(ItemList)):
      EnemyName,EnemyH, EnemyV = ItemList[i]
      if(EnemyName == TargetName):
        #print("EnemyFound TargetName",EnemyName, TargetName)
        TargetInRange = True
        break
    #if target was on screen, but not in firing range try dropping a bomb
    RequestBombDrop = True
  
  #print("Was EnemyNearby?",Found)
  #print("Was TargetInRange?",TargetInRange)
  return EnemyName,EnemyH, EnemyV, TargetInRange

  
  
    #if ( any(item in EnemyTargets for item,h,v in ItemList)):
      #for x in range (0,45):
      #  LED.setpixel(Defender.h + 5 + x,Defender.v + 2,255,0,0)







def LookForGroundTargets(Defender,DefenderPlayfield,Ground,Humans,EnemyShips,hunt_humans=False):
  global RequestBombDrop
  global RequestGroundLaser

  #upper left hand corner of currently displayed playfield window
  PlayfieldH   = round(DefenderPlayfield.DisplayH)
  PlayfieldV   = DefenderPlayfield.DisplayV
  RadarWidth   = 18 if hunt_humans else 10
  RadarHeight  = 8 if hunt_humans else 6
  RadarAdjustH = 5
  RadarAdjustV = 5
  GroundV      = 0

  if hunt_humans:
      aim_h = PlayfieldH + Defender.h + 10
      aim_v = Defender.v
      nearest_h, nearest_v = find_nearest_alive_human(Humans, aim_h, aim_v)
      if nearest_h >= 0:
          RequestGroundLaser = True
          RequestBombDrop = True
          GroundV = max(0, nearest_v - 1)
          StartX = max(0, nearest_h - RadarWidth // 2)
          StopX = min(DefenderPlayfield.width - 1, nearest_h + RadarWidth // 2)
          StartY = max(0, nearest_v - 2)
          StopY = min(LED.HatHeight - 1, nearest_v + RadarHeight)
          for human in Humans:
              if (is_alive(human)
                      and StartX <= human.h <= StopX
                      and StartY <= human.v <= StopY):
                  GroundV = max(0, human.v - 1)
                  break
      return RequestGroundLaser, RequestBombDrop, GroundV, Humans, EnemyShips

  
  #avoid end of the playfield
  if(PlayfieldH + RadarAdjustH + RadarWidth >= DefenderPlayfield.width -1):
    PlayfieldH =  PlayfieldH - RadarAdjustH - RadarWidth


  #Find the ground
  for GroundV in range (Defender.v, LED.HatHeight-2):
    
    if(Ground.map[GroundV][PlayfieldH + RadarAdjustV] != (0,0,0)):
      break
  
  #Radar box starts at the ground surface
  StartX    = PlayfieldH + RadarAdjustH 
  StopX     = PlayfieldH + RadarAdjustH + RadarWidth
  StartY    = GroundV -2
  StopY     = GroundV + RadarHeight
  ScanStep  = 2
  
  if(StopY >= LED.HatHeight):
    StopY = LED.HatHeight

  #Add a bit of randomness to the vertical start pixel
  if random.randint(0,1) == 1:
    StartY = StartY + 1

  #new method
  Found = False
  
  for human in Humans:
    if is_alive(human) and StartX <= human.h <= StopX and StartY <= human.v <= StopY:
        RequestGroundLaser = True
        RequestBombDrop = True
        Found = True
        break  # optional: stop after first target      
  
  
  for ship in EnemyShips:
    if is_alive(ship) and StartX <= ship.h <= StopX and StartY <= ship.v <= StopY:
        RequestGroundLaser = True
        RequestBombDrop = True
        Found = True
        break










  
  return RequestGroundLaser, RequestBombDrop, GroundV, Humans,EnemyShips

  



def ShootTarget(PlayfieldH, PlayfieldV, TargetName, TargetH,TargetV,Defender, DefenderPlayfield,Canvas):
  
  
  TargetHit = False

  #PlayfieldH is the upper left hand corner of the playfield window being displayed
  #TargetH and TargetV are on screen co-ordinates (64x32)

  #we override the target because we want to shoot from the nose of the Defender then 
  #check to see if we hit the enemy
  TargetV = Defender.v + 2

  #print("ST - TargetName:",TargetName)
  #print("ST - Shooting:",DefenderPlayfield.map[TargetV][TargetH+PlayfieldH].name, TargetH+PlayfieldH, TargetV)
  

  if(DefenderPlayfield.map[TargetV][TargetH].name != "EmptyObject" and DefenderPlayfield.map[TargetV][TargetH].alive == True):
    DefenderPlayfield.map[TargetV][TargetH].ConvertSpriteToParticles()
    DefenderPlayfield.map[TargetV][TargetH].EraseSpriteFromPlayfield2(DefenderPlayfield)
    DefenderPlayfield.map[TargetV][TargetH].alive = False
    TargetHit = True
    #we want to always shoot straight from the Defender.  If it hits, good. If not, too bad.
    if(DefenderDirection == -1):
      graphics.DrawLine(Canvas,Defender.h , Defender.v +2 , TargetH - DefenderPlayfield.DisplayH, TargetV, graphics.Color(255,0,0))
    else:
      graphics.DrawLine(Canvas,Defender.h + 7, Defender.v +2 , TargetH , TargetV, graphics.Color(255,0,0))


  else:
    #Laser misses, draw to end of screen
    if(DefenderDirection == 1):
      graphics.DrawLine(Canvas,Defender.h + 5, Defender.v +2 , LED.HatWidth , TargetV, graphics.Color(255,0,0))
    else:
      graphics.DrawLine(Canvas,Defender.h , Defender.v +2 , 0 , TargetV, graphics.Color(255,0,255))

      
  
  return DefenderPlayfield,TargetHit



def ShootGround(PlayfieldH, PlayfieldV, GroundV, Defender, DefenderPlayfield, Ground, Canvas, Humans, HumanParticles, EnemyShips, GroundParticles):
  #PlayfieldH is the upper left hand corner of the playfield window being displayed
  #Defender.h and Defender.v are relative to 64x32 display NOT the playfield 
  #print("Defender.h",Defender.h)

  ScanH = round(PlayfieldH + Defender.h + 3)
  ScanV = Defender.v + 2
  ScreenH = Defender.h + 3 
  ScreenV = Defender.v + 2
  i = 0

  #Found = False
  #GroundRGB = (0,0,0)
  #if(ScanH  < DefenderPlayfield.width):
  #  #find ground under defender
  #  for i in range (ScanV, LED.HatHeight):
  #    GroundRGB = Ground.map[i][ScanH]
  #    if GroundRGB != (0,0,0):
  #      break
  
  LaserR = 0
  LaserG = random.randint(GROUND_LASER_MIN, GROUND_LASER_MAX)
  LaserB = 0
  if(ScanH  >= DefenderPlayfield.width - 1):
    ScanH = DefenderPlayfield.width - 1
  
  LineV = GroundV + 2
  if(LineV > LED.HatHeight -1):
    LineV = LED.HatHeight -1
  if(LineV < Defender.v + 2):
    LineV = Defender.v + 2

  graphics.DrawLine(Canvas,ScreenH, ScreenV, ScreenH, LineV, graphics.Color(LaserR,LaserG,LaserB))
  #Convert ground to particle
  #Explode Ground
  for j in range(0,StrafeLaserStrength):
    if (GroundV + j < LED.HatHeight):
      #print("Strafe HV:",ScanH, GroundV + j)


      if(random.randint(0,1) == 1 and Ground.map[GroundV+j][ScanH] != (0,0,0)):
        GroundParticles      = AddGroundParticles(ScreenH,GroundV+j,LaserR, LaserG, 0,GroundParticles,LaserBlast=True)
      else:
        Ground.map[GroundV+j][ScanH] = (0,0,0)
      

  #examine the killzone
  Humans, HumanParticles, EnemyShips  = KillEnemiesInBlastZone(ScanH,GroundV + j,StrafeLaserStrength, Humans, HumanParticles, EnemyShips,DefenderPlayfield)
   

  return DefenderPlayfield, Ground, GroundParticles, Humans, HumanParticles, EnemyShips



def DebugPlayfield(Playfield,h,v,width,height):
  #Show contents of playfield - in text window, for debugging purposes
    
  print ("Map width height:",width,height)

  
  print ("===============================================================")

  for V in range(0,height):
    for H in range (0,width):
       
      name = Playfield[V+v][H+h].name
      #print ("Display: ",name,V,H)
      if (name == 'EmptyObject'):
        print ('  ',end='')

      #draw border walls
        
      #draw interior
      elif (name == 'Wall'):
        print (' #',end='')

      elif (name == 'Ground'):
        print (' G',end='')

        

      #draw Human
      elif (name == 'Human'):
        print (' H',end='')

      #draw EnemyShip
      elif (name == 'EnemyShip'):
        print ('**',end='')




      #draw interior
      elif (name == 'WallBreakable'):
        print (' o',end='')

      elif (Playfield[V][H].alive == 1):
        print (' ?',end='')
        #print ("Name?:",name," alive:",Playfield[V][H].alive)
      elif (Playfield[V][H].alive == 0):
        print (' !',end='')
        #print ("Name!:",name," alive:",Playfield[V][H].alive)
      else:
        print (' X',end='')
        #print ("NameX:",name," alive:",Playfield[V][H].alive)

    print('')
  print ("=============================================")


  return

    

def CreateHumans(HumanCount,Ground,DefenderPlayfield):

  Humans = []

  #humans must be located at least HatWidth from the start
  for count in range (0,HumanCount):
    
    #LED.HumanSprite.framerate = random.randint(15,50)
    
    TheSprite = LED.HumanSprite
    TheSprite.h         = random.randint(63,DefenderWorldWidth)
    TheSprite.v         = random.randint(16,LED.HatHeight-1)
    
    if(random.randint(0,1) == 1):
      TheSprite.direction = 1
    else:
      TheSprite.direction = -1
    
    Humans.append(copy.deepcopy(TheSprite))
    print("Placing humans:",count)
    DefenderPlayfield.CopyAnimatedSpriteToPlayfield(Humans[count].h,Humans[count].v,Humans[count])
 


  return Humans, DefenderPlayfield


def CreateEnemyWave(ShipType,ShipCount,Ground,DefenderPlayfield):
  global EnemyShipCount

  EnemyShipCount = ShipCount
  EnemyShips = []
  
  for count in range (0,ShipCount):
    NewSprite = copy.deepcopy(LED.ShipSprites[ShipType])
    NewSprite.framerate = random.randint(2,12)
    NewSprite.name = "EnemyShip"
    
    if(random.randint(0,EnemyFearFactor) == 1):
      NewSprite.afraid = True
    else:
      NewSprite.afraid = False

    if(random.randint(0,1) == 1):
      NewSprite.direction = 1
    else:
      NewSprite.direction = -1
    

    EnemyShips.append(NewSprite)
    
    #EnemyShips[count].ConvertSpriteToParticles()


    
    Finished = False
    while (Finished == False):
      #Find a spot in the sky for the ship
      h = random.randint(64,DefenderWorldWidth)
      v = random.randint(1,LED.HatHeight-1)
      
      try:

        if(Ground.map[v][h] == (0,0,0)):
          EnemyShips[count].h = h
          EnemyShips[count].v = v
          
          Finished = True
          print("Placing EnemyShips # HV:",count,h,v)
          DefenderPlayfield.CopyAnimatedSpriteToPlayfield(EnemyShips[count].h,EnemyShips[count].v,EnemyShips[count])

      except:
        print("Error placing ship HV",h,v)

  
  return EnemyShips,DefenderPlayfield



def AddEnemyShips(EnemyShips,ShipType,ShipCount,Ground,DefenderPlayfield):
  global EnemyShipCount
    

  for count in range (0,ShipCount):
    NewSprite = copy.deepcopy(LED.ShipSprites[ShipType])
    NewSprite.framerate = random.randint(2,12)
    NewSprite.name = "EnemyShip"

    if(random.randint(0,EnemyFearFactor) == 1):
      NewSprite.afraid = True
    else:
      NewSprite.afraid = False
    
    if(random.randint(0,1) == 1):
      NewSprite.direction = 1
    else:
      NewSprite.direction = -1


    Finished = False
    while (Finished == False):
      #Find a spot in the sky for the ship
      h = random.randint(64,DefenderWorldWidth)
      v = random.randint(1,LED.HatHeight-1)

      try:

        if(Ground.map[v][h] == (0,0,0)):
          NewSprite.h = h
          NewSprite.v = v
          
          Finished = True
          print("Placing EnemyShips i hv:",count, h,v)
          EnemyShips.append(NewSprite)
          DefenderPlayfield.CopyAnimatedSpriteToPlayfield(h,v,EnemyShips[count])
          print("Placing EnemyShip HV: h,v")

      except:
        print("Error placing ship HV",h,v)
    




    #We might have to let garbage cleanup determine if they are alive or not
    #otherwise the counts get messed up
    #Update total enemy count
    EnemyShipCount = count_alive(EnemyShips)
    
  return EnemyShips, EnemyShipCount, DefenderPlayfield







def AddHumans(Humans,NewHumanCount,Ground,DefenderPlayfield):
  global HumanCount

  #humans must be located at least HatWidth from the start
  for count in range (0,NewHumanCount):
    
    #LED.HumanSprite.framerate = random.randint(15,50)
    
    TheSprite   = LED.HumanSprite
    TheSprite.h = random.randint(63,DefenderWorldWidth)
    TheSprite.v = random.randint(16,LED.HatHeight-1)
    TheSprite.alive = True
    
    if(random.randint(0,1) == 1):
      TheSprite.direction = 1
    else:
      TheSprite.direction = -1
    
    Humans.append(copy.deepcopy(TheSprite))
    DefenderPlayfield.CopyAnimatedSpriteToPlayfield(Humans[count].h,Humans[count].v,Humans[count])
  
    #HumanCount = len(Humans)
    HumanCount = count_alive(Humans)

  return Humans,HumanCount, DefenderPlayfield


def DropPilot(H,V,Humans,DefenderPlayfield):
  global HumanCount

  #humans must be located at least HatWidth from the start
  TheSprite   = LED.HumanSprite
  TheSprite.h = H
  TheSprite.v = V
  TheSprite.alive = True
    
  #pilots run away
  TheSprite.direction = 1
  
  #if(random.randint(0,1) == 1):
  #  TheSprite.direction = 1
  #else:
  #  TheSprite.direction = -1

  HumanCount = HumanCount + 1
  Humans.append(copy.deepcopy(TheSprite))
  DefenderPlayfield.CopyAnimatedSpriteToPlayfield(Humans[-1].h,Humans[-1].v,Humans[-1])
  
  return Humans, HumanCount, DefenderPlayfield




def AddGroundParticles(h,v,r,g,b,GroundParticles,LaserBlast = False):
    #particles don't interact with anything other than the ground so
    #they are HV co-ordinates that match the display, not the playfield
    NewParticle = LED.Ship(h, v,r,g,b,2,2,2,1,1,'ground',0,0)
    #NewParticle.velocityH = random.random() * (random.randint(0,1) *2 -1) / 5

    if(LaserBlast == True):
      NewParticle.velocityH = random.uniform(-1,1)
      NewParticle.velocityV = random.uniform(-1,1) 
    else:
      NewParticle.velocityH = random.random() * -1 
      NewParticle.velocityV = random.random() * -1

    NewParticle.alive = True
    GroundParticles.append(NewParticle)
    return GroundParticles
    

def AddHumanParticles(h,v,r,g,b,HumanParticles):
    #particles don't interact with anything other than the ground so
    #they are HV co-ordinates that match the display, not the playfield
    NewParticle = LED.Ship(h,v,r,g,b,2,2,2,1,1,'human',0,0)
    NewParticle.velocityH = random.random() * -2 
    NewParticle.velocityV = random.random() * -2
    NewParticle.alive = True
    HumanParticles.append(NewParticle)
    #print('AddHumanParticles HV:',h,v)
    return HumanParticles



def KillEnemiesInBlastZone(BlastH,BlastV,BlastStrength, Humans, HumanParticles, EnemyShips,DefenderPlayfield):

  #DisplayH is the current window (upper left hand coordinates) of the playfield
  #BlastHV use playfield co-ordinates

  DisplayH = DefenderPlayfield.DisplayH
    
  #Define hitbox
  h1 = BlastH - BlastStrength 
  h2 = BlastH + BlastStrength 
  v1 = BlastV - BlastStrength
  v2 = BlastV + BlastStrength
  ph = 0
  pv = 0

  if(v1 <= 0):
    v1 = 0
  if(v2 >= LED.HatHeight-1):
    v2 = LED.HatHeight-1
  
  #print("Kill Humans Blast Zone DisplayH:",DisplayH)
  #print("Blast Zone h1 v1 h2 v2",h1,v1,h2,v2)

  HumanCount = len(Humans)
  #print("(Killzone)Human Count:",HumanCount)
  for i in range (0,HumanCount):
    if(Humans[i].alive == 1 and (h1 <= Humans[i].h <= h2) and (v1 <= Humans[i].v <= v2)):
      print("----------> Human killed")

      Humans[i].alive = False
      #print("*******************************************************************")
      #print("")
      #print("i alive hv:",i, Humans[i].alive, Humans[i].h,Humans[i].v)
      #print("")
      
      for j in range (0,4):
        ph = Humans[i].h - DisplayH
        pv = Humans[i].v
        #print("ph pv:",ph,pv)
        HumanParticles = AddHumanParticles((Humans[i].h + j -DisplayH),Humans[i].v,255,0,0,HumanParticles)
    
  ShipCount = len(EnemyShips)
  #print("(Killzone)EnemyShip Count:",ShipCount)
  for i in range (0,ShipCount):
    if(EnemyShips[i].alive == 1 and (h1 <= EnemyShips[i].h <= h2) and (v1 <= EnemyShips[i].v <= v2)):
      #print("----------> Enemy ship killed")
      EnemyShips[i].alive = False
      EnemyShips[i].ConvertSpriteToParticles()



  return Humans, HumanParticles, EnemyShips

 #This might be slow, trying searching the whole human list instead
 # for x in (h1,h2):
 #   for y in (v1,v2):
      #if(DefenderPlayfield.map[y][DisplayH + x].name == 'Human' and DefenderPlayfield.map[y][DisplayH + x].alive == 1):
      #  DefenderPlayfield.map[y][DisplayH + x].alive == 0
      #  for i in (0,1):
      #    HumanParticles = AddHumanParticles(x,y,random.randint(100,255),0,0,HumanParticles)
 
  return HumanParticles, DefenderPlayfield


def draw_bomb_explosion_flash(Canvas, cx, cy, blast_strength):
    """Brief tight impact flash — small rings, not a big blast."""
    flash_colors = (
        (255, 255, 255),
        (255, 255, 180),
        (255, 230, 60),
        (255, 160, 0),
        (255, 80, 0),
    )
    flash_radius = min(BOMB_FLASH_MAX_RADIUS, max(3, blast_strength // 3))

    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            Canvas.SetPixel(cx + dx, cy + dy, 255, 255, 255)
    for i, rgb in enumerate(flash_colors[:flash_radius]):
        graphics.DrawCircle(Canvas, cx, cy, i + 1, graphics.Color(*rgb))


def carve_irregular_bomb_crater(ground_map, gh, gv, blast_strength, rng=None):
    """Carve a natural irregular crater instead of the legacy cone-shaped blast."""
    if rng is None:
        rng = random.Random()

    blast_strength = max(2, round(blast_strength * BOMB_CRATER_SCALE))

    height = len(ground_map)
    width = len(ground_map[0]) if height else 0
    if width == 0:
        return ground_map

    h_span = blast_strength + rng.randint(2, 5)
    v_span_up = rng.randint(3, 6)
    v_span_down = blast_strength + rng.randint(0, 3)
    h_min = max(0, gh - h_span)
    h_max = min(width - 1, gh + h_span)
    v_min = max(0, gv - v_span_up)
    v_max = min(height - 1, gv + v_span_down)

    blobs = []
    for _ in range(rng.randint(4, 7)):
        blobs.append((
            gh + rng.randint(-blast_strength // 2, blast_strength // 2),
            gv + rng.randint(-2, max(1, blast_strength // 2)),
            rng.uniform(0.35, 1.05) * (blast_strength + rng.uniform(-1, 2)),
            rng.uniform(0.35, 1.15) * (blast_strength + rng.uniform(-1, 3)),
            rng.uniform(0.62, 1.18),
        ))

    for gy in range(v_min, v_max + 1):
        for gx in range(h_min, h_max + 1):
            if ground_map[gy][gx] == (0, 0, 0):
                continue

            destroy = False
            for cx, cy, rx, ry, edge in blobs:
                dx = (gx - cx) / max(rx, 0.5)
                dy = (gy - cy) / max(ry, 0.5)
                dist = math.sqrt(dx * dx + dy * dy)
                if dist < edge + rng.uniform(-0.2, 0.2):
                    destroy = True
                    break

            if destroy:
                ground_map[gy][gx] = (0, 0, 0)

    return ground_map


def DetonateBombIfAtGround(PlayfieldH,PLayfieldV,DefenderBomb,Ground,GroundParticles,Humans,HumanParticles,EnemyShips, DefenderPlayfield,Canvas,GroundRGB, SurfaceRGB):
  # PlayfieldH, PlayfieldV = upper left hand corner of the window being displayed
  #Defenderbomb.h is relative to the  64x32 display
  #BlastHV is relative to the  64x32 display

  
  BlastH = round(DefenderBomb.h)
  BlastV = round(DefenderBomb.v)
  



  #the further the bomb travels, the more power it gains
  if (DefenderDirection == 1):
    BlastStrength  = round(DefenderBomb.h / 10 + BlastFactor)
  else:
    BlastStrength  = round( (LED.HatWidth - DefenderBomb.h)     / 10 + BlastFactor)

  try:

    #Blow up bomb if it touches ground or runs out of velocity
    #try:
    #blow up pieces of ground



    #print("Bounces:",DefenderBomb.bounces)
    if((Ground.map[BlastV][BlastH+PlayfieldH] != (0,0,0))
       or DefenderBomb.bounces >= MaxBombBounces
       ):

      
      carve_irregular_bomb_crater(
          Ground.map,
          BlastH + PlayfieldH,
          BlastV,
          BlastStrength,
      )


  except:
    print("Bomb error while destroying ground BlastH BlastV PlayfieldH:",BlastH, BlastV ,PlayfieldH)      


  try:
      draw_bomb_explosion_flash(Canvas, BlastH, BlastV, BlastStrength)
      for i in range(0, round(BlastStrength / 2)):
          GroundParticles = AddGroundParticles(
              BlastH, BlastV, ExplosionR, ExplosionG, ExplosionB, GroundParticles,
          )
      Humans, HumanParticles, EnemyShips = KillEnemiesInBlastZone(
          BlastH + PlayfieldH, BlastV, BlastStrength,
          Humans, HumanParticles, EnemyShips, DefenderPlayfield,
      )
     
      DefenderBomb.alive = False
      #DefenderBomb.bounces = 0
      #print ("Bomb Dead.",DefenderBomb.alive)


  except:
    print("Bomb error drawing explosion BlastH BlastV PlayfieldH:",BlastH, BlastV, PlayfieldH)


  if(DefenderBomb.alive == False):
    BlastRadius = round(BlastStrength / 2)
    Ground = FlattenGround(PlayfieldH + BlastH - BlastRadius -4,PlayfieldH + BlastH + BlastRadius + 4,MaxMountainHeight,Ground)


  #except:
  #  print("Error detonating bomb HV velocityV: ",bh+PlayfieldH,BlastV,DefenderBomb.velocityV)
                
  return DefenderBomb, GroundParticles, Humans, HumanParticles, EnemyShips, Ground, DefenderPlayfield,Canvas






def MoveBomb(gx,DefenderBomb,DefenderPlayfield,Canvas):
  if(DefenderBomb.alive == True):
    #print ("Bomb alive")
    #Move bomb
    DefenderBomb.UpdateLocationWithGravity()
    
    bh = round(DefenderBomb.h)
    bv = round(DefenderBomb.v)

    if(bv >= LED.HatHeight):
      bv = LED.HatHeight -1
      DefenderBomb.velocityV = abs(DefenderBomb.velocityV) * -0.75
      DefenderBomb.bounces = DefenderBomb.bounces + 1
      
      
    #if(bh >= LED.HatWidth -1):
    #  bh = LED.HatWidth -2
    #  DefenderBomb.UpdateLocationWithGravity()
       
  Canvas = DefenderBomb.PaintAnimatedToCanvas(bh,bv,Canvas)
  return bh, bv, DefenderBomb, DefenderPlayfield, Canvas








def MoveGroundParticles (GroundParticles,Canvas):
  #Move ground particles (exploding bomb)
  ParticleCount = len(GroundParticles)
  if(ParticleCount > 0):
    for i in range (0,ParticleCount):
      #print("Particles:",len(GroundParticles))

      if(GroundParticles[i].alive == True):
        GroundParticles[i].UpdateLocationWithGravity(GroundParticleGravity)
        gph = GroundParticles[i].h
        gpv = GroundParticles[i].v
        
        #print("GROUNDParticle location:",gph,gpv)
    
        #only display particles on screen
        r  = GroundParticles[i].r
        g  = GroundParticles[i].g
        b  = GroundParticles[i].b
        Canvas.SetPixel(gph,gpv,r,g,b)
          
      #kill the particle if they go off the screen
      else:
        GroundParticles[i].alive = False




def MoveHumanParticles (HumanParticles,Canvas):
  
  #ParticleCount = len(HumanParticles)
  #if(ParticleCount > 0):
  #for i in range (0,ParticleCount):
  for Particle in HumanParticles:
    
    #print("HumanParticle:",i," alive:",Particle.alive)

    if(Particle.alive == True):
      Particle.UpdateLocationWithGravity(HumanParticleGravity)
      if ShowHumans:
        hph = Particle.h
        hpv = Particle.v
        r  = Particle.r
        g  = Particle.g
        b  = Particle.b
        Canvas.SetPixel(hph,hpv,r,g,b)
        

def DisplayCount(h,v,RGB, Header,Count,Canvas):
  CountSprite = LED.CreateBannerSprite(Header + str(Count))
  Canvas = LED.CopySpriteToCanvasZoom(CountSprite,h,v,(RGB),(0,0,0),ZoomFactor = 1,Fill=False,Canvas=Canvas)
  #Canvas = LED.TheMatrix.SwapOnVSync(Canvas)
  return Canvas, CountSprite



# Blasteroids-style overlapping lump blobs for shaded terrain (see Outbreak obstacle stamping).
TERRAIN_LUMP_STAMP_SPACING = 3
TERRAIN_LUMP_SIZE_MIN = 6
TERRAIN_LUMP_SIZE_MAX = 14
TERRAIN_LUMP_CONTRAST = 1
TERRAIN_BRIGHTNESS = 1.15


def terrain_ground_rgb(ground_rgb):
    """Scale base dirt palette before depth and lump shading."""
    r, g, b = ground_rgb
    return (
        min(255, int(r * TERRAIN_BRIGHTNESS)),
        min(255, int(g * TERRAIN_BRIGHTNESS)),
        min(255, int(b * TERRAIN_BRIGHTNESS)),
    )


def generate_terrain_lumps(rng, count_min=3, count_max=6):
    """Random overlapping circles — same layout as Blasteroids.Asteroid."""
    lumps = []
    for _ in range(rng.randint(count_min, count_max)):
        angle = rng.uniform(0, 2 * math.pi)
        distance_frac = rng.uniform(0, 0.5)
        lump_radius_frac = rng.uniform(0.2, 0.5)
        lumps.append((
            math.cos(angle) * distance_frac,
            math.sin(angle) * distance_frac,
            lump_radius_frac,
        ))
    return lumps


def compute_lump_shaded_rgb(i, j, size, lumps, base_rgb, contrast=TERRAIN_LUMP_CONTRAST):
    """Return shaded RGB for a pixel inside the lump union, or None for outside."""
    max_depth = -1
    selected_lump = None
    for frac_dx, frac_dy, frac_r in lumps:
        effective_dx = frac_dx * size
        effective_dy = frac_dy * size
        effective_radius = frac_r * size
        distance = math.sqrt((i - effective_dx) ** 2 + (j - effective_dy) ** 2)
        if distance < effective_radius:
            depth = effective_radius - distance
            if depth > max_depth:
                max_depth = depth
                selected_lump = (frac_dx, frac_dy, frac_r)

    if selected_lump is None:
        return None

    frac_dx, frac_dy, frac_r = selected_lump
    effective_dx = frac_dx * size
    effective_dy = frac_dy * size
    effective_radius = frac_r * size
    rel_i = i - effective_dx
    rel_j = j - effective_dy
    brightness_factor = 1.0 - contrast * (rel_i + rel_j) / (2 * effective_radius)
    brightness_factor = max(0.5, min(1.5, brightness_factor))
    r, g, b = base_rgb
    return (
        min(255, int(r * brightness_factor)),
        min(255, int(g * brightness_factor)),
        min(255, int(b * brightness_factor)),
    )


def column_ground_extent(ground_map, x, height):
    """Return (top_y, bottom_y) for non-empty ground in a column, or None."""
    top_y = None
    for y in range(height):
        if ground_map[y][x] != (0, 0, 0):
            top_y = y
            break
    if top_y is None:
        return None
    bottom_y = top_y
    for y in range(height - 1, top_y - 1, -1):
        if ground_map[y][x] != (0, 0, 0):
            bottom_y = y
            break
    return top_y, bottom_y


def terrain_base_rgb(y, ground_rgb):
    """Depth-shaded base color for lump texture (no bright surface-top line)."""
    return LED.AdjustBrightnessRGB(terrain_ground_rgb(ground_rgb), -y + 20)


def terrain_fallback_shade(base_rgb, gx, gy):
    """Light dither so gaps between lump circles are not flat fills."""
    nudge = ((gx * 7 + gy * 13) % 7) - 3
    return LED.AdjustBrightnessRGB(base_rgb, nudge)


def apply_lumpy_terrain_shading(Ground, ground_rgb, surface_rgb, seed=None):
    """Stamp Blasteroids-style lump shading across the full ground column."""
    ground_map = Ground.map
    height = Ground.height
    width = Ground.width
    rng = random.Random(seed if seed is not None else random.randint(0, 2**31 - 1))
    stamp_cache = {}

    for gx in range(width):
        extent = column_ground_extent(ground_map, gx, height)
        if extent is None:
            continue
        top_y, bottom_y = extent
        col_depth = bottom_y - top_y + 1

        band = gx // TERRAIN_LUMP_STAMP_SPACING
        if band not in stamp_cache:
            band_rng = random.Random(rng.randint(0, 2**31 - 1))
            stamp_cache[band] = (
                band_rng.randint(TERRAIN_LUMP_SIZE_MIN, TERRAIN_LUMP_SIZE_MAX),
                generate_terrain_lumps(band_rng, count_min=5, count_max=9),
            )
        size, lumps = stamp_cache[band]
        size = max(size, col_depth + 2)

        cx = band * TERRAIN_LUMP_STAMP_SPACING + (TERRAIN_LUMP_STAMP_SPACING // 2)
        cy = (top_y + bottom_y) // 2

        for gy in range(top_y, bottom_y + 1):
            base = terrain_base_rgb(gy, ground_rgb)
            shaded = compute_lump_shaded_rgb(gx - cx, gy - cy, size, lumps, base)
            if shaded is not None:
                ground_map[gy][gx] = shaded
            else:
                ground_map[gy][gx] = terrain_fallback_shade(base, gx, gy)


def create_mountains_base(Ground, ground_rgb, maxheight=MaxMountainHeight):
    """Mountain silhouette with depth shading only (no bright surface-top pixel)."""
    mv = LED.HatHeight - 1
    chance = 10
    step = random.randint(1, 3)
    half_width = round(Ground.width / 2)

    for x in range(0, half_width):
        if random.randint(0, chance) == 1:
            mv = mv - step
        elif random.randint(0, chance) == 2:
            mv = mv + step

        if mv > LED.HatHeight - 1:
            mv = LED.HatHeight - 1
        if mv < LED.HatHeight - maxheight:
            mv = LED.HatHeight - maxheight

        for y in range(0, LED.HatHeight):
            if y >= mv:
                Ground.map[y][x] = LED.AdjustBrightnessRGB(terrain_ground_rgb(ground_rgb), -y + 20)
            else:
                Ground.map[y][x] = (0, 0, 0)

    for x in range(0, half_width):
        for y in range(0, LED.HatHeight):
            Ground.map[y][x + half_width] = Ground.map[y][half_width - 1 - x]

    return Ground


def create_lumpy_mountains(Ground, ground_rgb, surface_rgb, maxheight=MaxMountainHeight, seed=None):
    """Build scrolling mountains, then bake lumpy shaded texture into the dirt."""
    create_mountains_base(Ground, ground_rgb, maxheight=maxheight)
    apply_lumpy_terrain_shading(Ground, ground_rgb, surface_rgb, seed=seed)
    return Ground


def FlattenGround(h1,h2,v,Ground):
  #h1,h2 are the start/stop columns to examine
  #v is the max height of the ground to check (saves time by not looking at sky)
  
  #examine holes in ground and make top layers fall to bottom
   
  #look for top ground particle
  #then look for bottom empty
  #swap

  
  h1 = round(h1)
  h2 = round(h2)
  minv = v
  maxv = Ground.height -2
  GroundFound = False
  HoleFound   = False
  Finished    = False
  GroundV     = 0 

  #check boundaries
  if(h2 < h1):
    h2 = h1

  for x in range (h1,h2):
    
    minv = v
    maxv = Ground.height -1
    #print("Sorting column: ",x)
    Finished    = False
    GroundFound = False
    HoleFound   = False

    #work our way down to find ground
    #work our way up to find holes
    #do the swaparoo and continue until we meet in the middle
    while (Finished == False):
      GroundFound = False
      HoleFound   = False
      while (GroundFound == False):
        if (minv >= maxv):
          Finished = True
          break

        try:
          if(Ground.map[minv][x] != (0,0,0)):
            #print("Found ground:",minv)
            GroundFound = True
            break
          else:
            minv = minv + 1
            #print("minv maxv:",minv,maxv)
        except:
          #weird stuff happens at the end of the playfield
          print(" Finding Ground Error:",minv,maxv)
          Finished = True
          break


      
      #No ground found, move on
      if (Finished == True):
        #print("No ground found")
        break

      while(HoleFound == False):
        if(maxv <= minv):
          Finished = True
          break

        if(Ground.map[maxv][x] == (0,0,0)):
          HoleFound = True
          #print("Found hole:",maxv)
          break
        else:
          maxv = maxv -1
          
      
      #no hole found, move on
      if (Finished == True):
        break

      if(GroundFound == True and HoleFound == True):
        Ground.map[maxv][x] = Ground.map[minv][x] 
        Ground.map[minv][x] = (0,0,0)      
    
        #increment/decrement our v counts
        minv = minv + 1
        maxv = maxv - 1
  return Ground


def advance_wave(
    fresh_wave,
    WaveCount,
    ShipType,
    EnemyShips,
    DefenderPlayfield,
    Ground,
    Background,
    Middleground,
    Foreground,
    Canvas,
    Defender,
    bx,
    mx,
    fx,
    gx,
    ClockSprite,
    EnemyCountSprite,
    HumanCountSprite,
    ground_rgb,
    surface_rgb,
):
    """Run WAVE transition and spawn enemies. fresh_wave replaces the wave; otherwise reinforce."""
    global EnemyShipCount, DefenderSpeed, ExplosionR, ExplosionG, ExplosionB

    ShipType = ShipType + 1
    if ShipType > 27:
        ShipType = 0

    ShipH = round((LED.HatWidth - LED.ShipSprites[ShipType].width) / 2)
    ShipV = 11
    LED.ShipSprites[ShipType].currentframe = round(LED.ShipSprites[ShipType].frames / 2)

    print("bx mx fx gx:", bx, mx, fx, gx)
    ScreenA = LED.PaintFourLayerScreenArray(bx, mx, fx, gx, Background, Middleground, Foreground, Ground, Canvas)
    ScreenA = LED.CopySpriteToScreenArrayZoom(
        ClockSprite, ClockSprite.h, ClockSprite.v, ClockSprite.rgb,
        ZoomFactor=ClockZoom, InputScreenArray=ScreenA,
    )
    if ShowCountHUD:
        ScreenA = LED.CopySpriteToScreenArrayZoom(
            EnemyCountSprite, EnemyCountH, EnemyCountV, (EnemyCountRGB), (0, 0, 0),
            ZoomFactor=1, Fill=False, InputScreenArray=ScreenA,
        )
        ScreenA = LED.CopySpriteToScreenArrayZoom(
            HumanCountSprite, HumanCountH, HumanCountV, (EnemyCountRGB), (0, 0, 0),
            ZoomFactor=1, Fill=False, InputScreenArray=ScreenA,
        )
    ScreenA = LED.CopyAnimatedSpriteToScreenArrayZoom(
        LED.Defender, Defender.h, Defender.v, ZoomFactor=1, TheScreenArray=ScreenA,
    )
    print("Capturing ScreenA")
    time.sleep(1)

    m, r = divmod(WaveCount, RedrawGroundWaveCount)
    if r == 0:
        i = random.randint(0, GroundColorCount - 1)
        ground_rgb, surface_rgb = GroundColorList[i]
        print("** Redrawing Ground GroundRGB:", ground_rgb)
        Ground = create_lumpy_mountains(
            Ground, ground_rgb, surface_rgb, maxheight=MaxMountainHeight, seed=WaveCount * 1337,
        )
        ExplosionR, ExplosionG, ExplosionB = LED.AdjustBrightnessRGB(
            surface_rgb, ExplosionBrightnessModifier,
        )
    else:
        print("** Flattening Ground")
        Ground = FlattenGround(0, Ground.width, MaxMountainHeight, Ground)
        apply_lumpy_terrain_shading(Ground, ground_rgb, surface_rgb, seed=WaveCount * 1337 + 7)

    ScreenB = LED.PaintFourLayerScreenArray(bx, mx, fx, gx, Background, Middleground, Foreground, Ground, Canvas)
    ScreenB = LED.CopyAnimatedSpriteToScreenArrayZoom(
        LED.Defender, Defender.h, Defender.v, ZoomFactor=1, TheScreenArray=ScreenB,
    )

    LED.TransitionBetweenScreenArrays(ScreenA, ScreenB, TransitionType=2)
    print("Transition A --> B")
    time.sleep(1)

    Message = "WAVE " + str(WaveCount)
    MessageBanner = LED.CreateBannerSprite(Message)
    CursorH = round((LED.HatWidth - MessageBanner.width) / 2)
    CursorV = 2
    ScreenC, CursorH, CursorV = LED.TerminalTypeLine(
        ScreenB, Message, CursorH=CursorH, CursorV=CursorV, MessageRGB=(0, 100, 0),
        CursorRGB=(0, 255, 0), CursorDarkRGB=(0, 50, 0), StartingLineFeed=1,
        TypeSpeed=TerminalTypeSpeed, ScrollSpeed=TerminalTypeSpeed * 2,
    )
    ScreenD = LED.CopyAnimatedSpriteToScreenArrayZoom(
        LED.ShipSprites[ShipType], ShipH, ShipV, ZoomFactor=2, TheScreenArray=ScreenC,
    )
    LED.TransitionBetweenScreenArrays(ScreenC, ScreenD, TransitionType=1)

    if fresh_wave:
        EnemyShips, DefenderPlayfield = CreateEnemyWave(
            ShipType=ShipType, ShipCount=AddEnemyCount, Ground=Ground,
            DefenderPlayfield=DefenderPlayfield,
        )
    else:
        EnemyShips, EnemyShipCount, DefenderPlayfield = AddEnemyShips(
            EnemyShips, ShipType=ShipType, ShipCount=AddEnemyCount, Ground=Ground,
            DefenderPlayfield=DefenderPlayfield,
        )

    LED.TransitionBetweenScreenArrays(ScreenD, ScreenB, TransitionType=1)
    DefenderSpeed = DefenderMinSpeed

    return (
        ShipType,
        EnemyShips,
        DefenderPlayfield,
        Ground,
        count_alive(EnemyShips),
        ground_rgb,
        surface_rgb,
    )


def PlayDefender2(Duration,StopEvent=None):      
 
  global EnemyShipCount
  global HumanCount
  global RequestBombDrop
  global RequestGroundLaser
  global ExplosionR
  global ExplosionG
  global ExplosionB
  global MeltingGroundR
  global MeltingGroundG
  global MeltingGroundB
  global DefenderSpeed
  global DefenderDirection
  global DefenderReversing

  LevelCount          = 0
  EnemyAliveCount     = 0
  OldEnemyAliveCount  = 0
  OldHumanCount       = 0
  WaveCount           = 1
  wave_enemies_spawned = False
  last_wave_advance_time = 0

  #time
  random.seed()
  start_time       = time.time()


  ClockSprite   = LED.CreateClockSprite(24)
  ClockSprite.h = (LED.HatWidth - ClockSprite.width -2)
  ClockSprite.v = 0
  ClockSprite.rgb = ClockRGB

  DayOfWeekSprite     = LED.CreateDayOfWeekSprite()
  MonthSprite         = LED.CreateMonthSprite()
  DayOfMonthSprite    = LED.CreateDayOfMonthSprite()

  ClockSprite.on      = 0


  DefenderPlayfield = LED.PlayField(
      name   = "DefenderWorld",
      width  = DefenderWorldWidth,
      height = LED.HatHeight,
      h      = 0,
      v      = 0
    )
  DefenderPlayfield.DisplayH = 0
  DefenderPlayfield.DisplayV = 0


  #LED.TheMatrix.Clear()
  #LED.Canvas.Clear()
  
  Canvas = LED.TheMatrix.CreateFrameCanvas()
  Canvas.Fill(0,0,0)
  #Canvas = LED.TheMatrix.SwapOnVSync(Canvas)



  #The map is an array of a lists.  You can address each element has VH e.g. [V][H]
  #Copying the map to the playfield needs to follow the exact same shape



  #----------------------
  #-- Prepare Level    --
  #----------------------
  print("")
  print("")
  print("*****************************************************")
  #LED.DefenderGamesPlayed = LED.DefenderGamesPlayed + 1
  #LED.SaveConfigData()
  print("*****************************************************")

  
  




  #--------------------------------
  #-- Create Layers              --
  #--------------------------------

  Background   = LED.Layer(name="backround", width=4048, height=32,h=0,v=0)
  Middleground = LED.Layer(name="backround", width=4048, height=32,h=0,v=0)
  Foreground   = LED.Layer(name="backround", width=4048, height=32,h=0,v=0)
  Ground       = LED.Layer(name="ground",    width=DefenderWorldWidth, height=32,h=0,v=0)

  Background.CreateStars(5,0,50,50)
  Middleground.CreateStars(0,0,100,100)
  Foreground.CreateStars(0,0,200,200)
 
  
  i = random.randint(0,GroundColorCount -1)
  GroundRGB, SurfaceRGB      = GroundColorList[i]
  GroundR,GroundG,GroundB    = GroundRGB
  SurfaceR,SurfaceG,SurfaceB = SurfaceRGB
  ExplosionR, ExplosionG, ExplosionB = LED.AdjustBrightnessRGB(SurfaceRGB,ExplosionBrightnessModifier)

  Ground = create_lumpy_mountains(Ground, GroundRGB, SurfaceRGB, maxheight=MaxMountainHeight, seed=WaveCount * 1337)
  


  #Add text to a layer
  TextColorCount = len(LED.TextColorList)

  #Get a bunch of random colors for each text layer  
  i = random.randint(0,TextColorCount -1)
  A,B,C,D = LED.TextColorList[i]
  Text1RGB = C

  i = random.randint(0,TextColorCount -1)
  A,B,C,D = LED.TextColorList[i]
  Text2RGB = B
  
  i = random.randint(0,TextColorCount -1)
  A,B,C,D = LED.TextColorList[i]
  Text3RGB = B

  
  TheBanner1 = LED.CreateBannerSprite("THIS IS TACO PLANET")
  h1         = round(Middleground.width * 0.80)
  v1         = 24
  Middleground = LED.CopySpriteToLayerZoom(TheBanner1,h1,v1,Text3RGB,(0,0,0),ZoomFactor=1,Fill=False,Layer=Middleground)

  
  TheBanner1 = LED.CreateBannerSprite("HELP!")
  h1         = round(Ground.width * 0.25)
  v1         = LED.HatHeight - (TheBanner1.height * 3)
  Ground     = LED.CopySpriteToLayerZoom(TheBanner1,h1,v1,Text1RGB,(0,0,0),ZoomFactor=2,Fill=False,Layer=Ground)
  TheBanner1 = LED.CreateBannerSprite("S.O.S.")
  h1         = round(Ground.width * 0.50)
  v1         = LED.HatHeight - (TheBanner1.height * 3)
  Ground     = LED.CopySpriteToLayerZoom(TheBanner1,h1,v1,Text2RGB,(0,0,0),ZoomFactor=2,Fill=False,Layer=Ground)
  TheBanner1 = LED.CreateBannerSprite("argh!!!")
  h1         = round(Ground.width * 0.75)
  v1         = LED.HatHeight - (TheBanner1.height * 3)
  Ground     = LED.CopySpriteToLayerZoom(TheBanner1,h1,v1,Text3RGB,(0,0,0),ZoomFactor=2,Fill=False,Layer=Ground)



  #Pick a random ship type to start
  ShipType = random.randint(1,27)

  
  
  



  
 

  #--------------------------------
  #-- Create Enemies             --
  #--------------------------------

  #Display message
  CursorH = 10
  CursorV = 2
  ShipH   = round((LED.HatWidth - LED.ShipSprites[ShipType].width) / 2 )
  ShipV   = 11
  LED.ShipSprites[ShipType].currentframe = round(LED.ShipSprites[ShipType].frames / 2)

  #display wave message
  Message        = "WAVE " + str(WaveCount)
  MessageBanner  = LED.CreateBannerSprite(Message)  #to determine the length in pixels
  CursorH        = round((LED.HatWidth - MessageBanner.width) / 2 )
  BackgroundScreenArray = LED.PaintFourLayerScreenArray(0,0,0,0,Background,Middleground,Foreground,Ground,Canvas)
  LED.TransitionBetweenScreenArrays(LED.ScreenArray,BackgroundScreenArray,TransitionType=2)
  LED.ScreenArray,CursorH,CursorV = LED.TerminalTypeLine(LED.ScreenArray,Message,CursorH=CursorH,CursorV=CursorV,MessageRGB=(0,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalTypeSpeed*2)
  NewScreenArray = LED.CopyAnimatedSpriteToScreenArrayZoom(LED.ShipSprites[ShipType],ShipH,ShipV,ZoomFactor=2,TheScreenArray=LED.ScreenArray)
  LED.TransitionBetweenScreenArrays(NewScreenArray,LED.ScreenArray,TransitionType=2)


  Humans,     DefenderPlayfield = CreateHumans(HumanCount=HumanCount, Ground=Ground,DefenderPlayfield=DefenderPlayfield)
  HumanCountSprite = LED.CreateBannerSprite('H' + str(HumanCount))
  if ShowCountHUD:
    Canvas, HumanCountSprite = DisplayCount(HumanCountH, HumanCountV, HumanCountRGB,'H',HumanCount,Canvas)

  EnemyShips, DefenderPlayfield = CreateEnemyWave(ShipType=ShipType,ShipCount=EnemyShipCount, Ground=Ground,DefenderPlayfield=DefenderPlayfield)
  EnemyCountSprite = LED.CreateBannerSprite('E'+str(EnemyShipCount))
  if ShowCountHUD:
    Canvas, EnemyCountSprite = DisplayCount(EnemyCountH, EnemyCountV, EnemyCountRGB,'E',EnemyShipCount,Canvas)
  wave_enemies_spawned = True
  OldEnemyAliveCount = EnemyShipCount
  
  #Erase message
  LED.TransitionBetweenScreenArrays(NewScreenArray,BackgroundScreenArray,TransitionType=1,FadeSleep=0.08)


  DefenderBomb = LED.BombSprite
  DefenderBomb.alive = False
  DefenderBomb.velocityH = 0
  DefenderBomb.velocityV = 0

  GroundParticles = []
  HumanParticles = []



  #--------------------------------
  #-- Main timing loop           --
  #--------------------------------

  x = 0


  #Canvas2 = LED.TheMatrix.CreateFrameCanvas()
  #Canvas2.Fill(22,0,0)
  
  
  Finished = False
  while (Finished == False):
    if StopEvent and StopEvent.is_set():
      print("*******************************")
      print("*******************************")
      print("[Defender2] Stop requested — exiting early.")
      print("*******************************")
      print("*******************************")
      Finished = True
      break
    
      
    
    count  = 0
    bx     = 0
    mx     = 0
    fx     = 0
    gx     = 0
    bwidth = Background.width    - LED.HatWidth
    mwidth = Middleground.width  - LED.HatWidth
    fwidth = Foreground.width    - LED.HatWidth
    gwidth = Ground.width        - LED.HatWidth
    brate  = 8
    mrate  = 6
    frate  = 4
    grate  = 1
    DisplayH  = 0
    DisplayV  = 0
    TargetHit = False
    

    Defender = DefenderState(LED.Defender)
    Defender.h = DefenderStartH + (DefenderSpeed * 2)
    Defender.v = 25
    hat_width = LED.HatWidth
    hat_height = LED.HatHeight
    ground_map = Ground.map
    frame_periodic_interval = 5000
    
    
    Done = False
    while(Done == False):
      if StopEvent and StopEvent.is_set():
        print("\n" + "="*40)
        print("[DEFENDER2] StopEvent received")
        print("-> Shutting down gracefully...")
        print("="*40 + "\n")
        Finished = True
        Done     = True
        break


      #main counter
      count = count + 1

      #check the time once in a while
      if count % frame_periodic_interval == 0:
        if (ClockSprite.hhmm != datetime.now().strftime('%H:%M')):
          ClockSprite   = LED.CreateClockSprite(24)
          ClockSprite.h = (LED.HatWidth - ClockSprite.width -2)
          ClockSprite.v = 0
          ClockSprite.rgb = ClockRGB

          #we need to earase the clock fist, commenting out for now
          #Background = LED.CopySpriteToLayerZoom(ClockSprite,bx + 30,10,(5,0,5),(0,5,0),2,False,Layer=Background)

          #Copy a big clock to the foreground layer
          h1         = LED.HatWidth + 60
          v1         = 10
          Foreground = LED.CopySpriteToLayerZoom(ClockSprite,h1,v1,Text1RGB,(0,0,0),ZoomFactor=2,Fill=True,Layer=Foreground)

          h1         = LED.HatWidth + round(Foreground.width * 0.20)
          v1         = 10
          Foreground = LED.CopySpriteToLayerZoom(ClockSprite,h1,v1,Text2RGB,(0,0,0),ZoomFactor=2,Fill=True,Layer=Foreground)

          h1         = LED.HatWidth + round(Foreground.width * 0.40)
          v1         = 10
          Foreground = LED.CopySpriteToLayerZoom(ClockSprite,h1,v1,Text1RGB,(0,0,0),ZoomFactor=2,Fill=True,Layer=Foreground)

          h1         = LED.HatWidth + round(Foreground.width * 0.60)
          v1         = 10
          Foreground = LED.CopySpriteToLayerZoom(ClockSprite,h1,v1,Text3RGB,(0,0,0),ZoomFactor=2,Fill=True,Layer=Foreground)

          h1         = LED.HatWidth + round(Foreground.width * 0.80)
          v1         = 10
          Foreground = LED.CopySpriteToLayerZoom(ClockSprite,h1,v1,Text3RGB,(0,0,0),ZoomFactor=2,Fill=True,Layer=Foreground)



        #End game after X seconds
        h,m,s    = LED.GetElapsedTime(start_time,time.time())

        if(m > Duration):
          LED.SaveConfigData()
          print("Ending game after",m," minutes")

          LED.ClearBigLED()
          LED.ClearBuffers()
          CursorH = 0
          CursorV = 0
          LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"ALIEN MUTANTS ARE VANQUISHED",CursorH=CursorH,CursorV=CursorV,MessageRGB=(150,0,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalTypeSpeed)
          LED.BlinkCursor(CursorH= CursorH,CursorV=CursorV,CursorRGB=CursorRGB,CursorDarkRGB=CursorDarkRGB,BlinkSpeed=0.5,BlinkCount=2)
          LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"LIVE TO FIGHT ANOTHER DAY",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)
          LED.BlinkCursor(CursorH= CursorH,CursorV=CursorV,CursorRGB=CursorRGB,CursorDarkRGB=CursorDarkRGB,BlinkSpeed=0.5,BlinkCount=2)
          
          return();




      #Background
      if count % brate == 0:
        bx = (bx + (DefenderSpeed / 2 * DefenderDirection)) % Background.width
        if(bx < 0 ):
          bx = bx + Background.width

      #Middleground
      if count % mrate == 0:
        mx = (mx + (DefenderSpeed / 2 * DefenderDirection)) % Middleground.width
        if(mx < 0 ):
          mx = mx + Middleground.width
        
      #foreground
      if count % frate == 0:
        fx = (fx + (DefenderSpeed / 2 * DefenderDirection)) % Foreground.width
        if(fx < 0 ):
          fx = fx + Foreground.width
      

        

#notes 
# we need to find out when GX get modified if the end of the ground map is reached



      #ground / display
      if count % grate == 0:
        gx = (gx + (DefenderSpeed / 2 * DefenderDirection)) % Ground.width

      DisplayH = int(gx)
      DisplayMaxH = DisplayH + hat_width
      DefenderPlayfield.DisplayH = DisplayH
      DefenderPlayfield.DisplayV = 0
      enemy_moves_this_frame = (count % EnemyMoveSpeed == 0)

      Canvas = LED.PaintFourLayerCanvas(bx,mx,fx,gx,Background,Middleground,Foreground,Ground,Canvas,DefenderDirection)

      #-------------------------------
      #-- Move Humans               --
      #-------------------------------

      OldH = 0
      OldV = 0
      #MoveHumans
      #for i in range (0,HumanCount):
      for Human in Humans:
        if is_alive(Human):
          OldH = Human.h
          OldV = Human.v

          if chance(HumanMoveChance):
            if (abs(gx + Defender.h - Human.h) < HumanRunDistance):
              #move human, but follow ground
              Human.h = Human.h + Human.direction

              #check boundaries
              if(Human.direction == 1):
                if Human.h >= DefenderPlayfield.width -2:
                  Human.h = 0
              else:
                if Human.h <= 0:
                  Human.h = DefenderPlayfield.width -1


              if(Human.v >= hat_height -1):
                Human.v = hat_height -2

              #print(Human.v,Human.h)

              #check ground
              #If hole, move down

              try:
                rgb = ground_map[Human.v][Human.h + Human.direction]
              except:
                print("Error moving human: i vh direction",i,Human.v,Human.h, Human.direction,end="\r")



              if(rgb == (0,0,0)):
                #if a hole at the bottom is encountered, run away
                if(Human.v > hat_height -4):
                  Human.direction = Human.direction * -1
                #print("Moving down:",Human.v)
                else:
                  Human.v = Human.v + 1
              else:
                if chance(HumanMoveChance):
                  Human.v = Human.v -1
              
          
          hH = Human.h
          hV = Human.v
        
          #check if human is in currently displayed area
          if ShowHumans and (DisplayH <=  hH  <= DisplayMaxH):
            Canvas = Human.PaintAnimatedToCanvas(hH-DisplayH,hV,Canvas)

         

      #-------------------------------
      #-- Move EnemyShips           --
      #-------------------------------

      OldH = 0
      OldV = 0
      NewH = 0
      NewV = 0
      #MoveEnemyShips
      
      #for i in range (0,EnemyShipCount):
      for EnemyShip in EnemyShips:

        if is_alive(EnemyShip):
          OldH = EnemyShip.h
          OldV = EnemyShip.v
        
          if(OldV < 0):
            print("Invalid V - EnemyShip HV",OldH, OldV)
            OldV = 0

          if(OldH < 0):
            print("Invalid H - EnemyShip HV",OldH, OldV)
            OldH = 0


          #Move if it is time to move
          if enemy_moves_this_frame:

            #Move if within X pixels from Defender
            if (abs(gx + Defender.h - EnemyShip.h) < AttackDistance):


              #check fear factor and change enemy fear status
              if chance(EnemyFearFactor):
                if(EnemyShip.afraid == True):
                  EnemyShip.afraid = False
                else:
                  EnemyShip.afraid = True
              
              
              #Move towards defender if not afraid
              if(EnemyShip.afraid == True) and (EnemyAliveCount >= 5):
                EnemyShip.direction = LED.PointAwayFromObject8Way(OldH,OldV,Defender.h,Defender.v)
              else:
                EnemyShip.direction = LED.PointTowardsObject8Way(OldH,OldV,Defender.h,Defender.v)

              #move Enemy
              NewH, NewV = LED.CalculateDotMovement8Way(OldH, OldV, EnemyShip.direction)
              #print("NewH NewV direction:",NewH,NewV,EnemyShip.direction)


              #check boundaries
              if(NewH >= DefenderPlayfield.width - EnemyShip.width):
                NewH = 0
              elif(NewH <= 0):
                NewH = DefenderPlayfield.width - EnemyShip.width
              #Might need to adjust this for enemy ships
              if(NewV >= hat_height -2):
                NewV = hat_height -3
              elif(NewV <=3):
                NewV = 3
              
            
              EnemyShip.h = NewH
              EnemyShip.v = NewV
          

              #Place EnemyShip on playfield
              
              #for some reason when we erase the sprite, it doesn't draw anymore on the canvas
              #This is likely because the sprite on the playfield points at the actual ship object
              #and ends up getting erased.  To avoid this we can always draw sprites with a border
              #of nothing, which will get written as emptyObject dots
              
              DefenderPlayfield.EraseAnimatedSpriteFromPlayfield(OldH,OldV,EnemyShip)
            
              try:
                DefenderPlayfield.CopyAnimatedSpriteToPlayfield(NewH, NewV,EnemyShip)
              except:
                print("Something went wrong copying the enemy ship sprite to the playfield")
                print("hv:",EnemyShip.h, EnemyShip.v)

            
        
          #check if Enemy is in currently displayed area
          if ShowEnemies and (DisplayH - EnemyShip.width <=  EnemyShip.h  <= (DisplayH + hat_width + EnemyShip.width)):
            Canvas = EnemyShip.PaintAnimatedToCanvas(EnemyShip.h-DisplayH,EnemyShip.v,Canvas)
            
          

        #If ship is dead, move particles
        if(EnemyShip.alive == False):
          for Particle in EnemyShip.Particles:
            

            if (Particle.alive == 1):
              Particle.UpdateLocationWithGravity(EnemyParticleGravity)
              ph = Particle.h
              pv = Particle.v

              #only display particles on screen
              if ShowEnemies and (DisplayH <=  ph  <= DisplayMaxH):
                r  = Particle.r
                g  = Particle.g
                b  = Particle.b
                Canvas.SetPixel(ph - DisplayH,pv,r,g,b)
              
              #kill the particle if the go off the screen
              else:
                Particle.alive = 0


      
      #--------------------------------
      #-- Move Defender              --
      #--------------------------------

      #defender needs to avoid the ground
      #shoot enemies
      #pick up humans
      GroundV = 0

      enemy_alive_now = count_alive(EnemyShips)
      human_alive_now = count_alive(Humans)
      human_hunt_mode = enemy_alive_now == 0 and human_alive_now > 0

      if human_hunt_mode:
        apply_human_hunt_steering(Defender, gx, Humans, hat_height)
      elif (DefenderReversing == 0):
        if chance(UpDownChance):
          Defender.v = Defender.v -1
        elif chance(UpDownChance):
          Defender.v = Defender.v +1

      
      
      #speed up defender randomly, but only if not in a reversing mode
      if chance_one(DefenderSpeedChangeChance) and (DefenderReversing == 0):
        if random.random() < 0.5:
          DefenderSpeed = DefenderSpeed + DefenderSpeedIncrement
        else:
          DefenderSpeed = DefenderSpeed - DefenderSpeedIncrement
        if(DefenderSpeed < DefenderMinSpeed):
          DefenderSpeed = DefenderMinSpeed
        if(DefenderSpeed > DefenderMaxSpeed):
          DefenderSpeed = DefenderMaxSpeed

        #place Defender further ahead on screen if moving faster
        if (DefenderDirection == 1):
          Defender.h = DefenderStartH +  (DefenderSpeed *2)
        else:
          Defender.h = hat_width - DefenderStartH - Defender.width - (DefenderSpeed * 2)

          
      ScanV = Defender.v + 10
      if(ScanV > hat_height -2):
        ScanV = hat_height -2

      ScanH = round(gx + 5)
      if(ScanH >= DefenderPlayfield.width -1) or (ScanH <= 0):
        ScanH = 0
      

      if(ground_map[ScanV][ScanH] != (0,0,0)): 
        if chance(3):
          Defender.v = Defender.v - 1
      else:
        if chance(200):
          Defender.v = Defender.v + 1

      #keep defender within the screen borders
      if(Defender.v >= hat_height-3):
        Defender.v = hat_height-3
      if(Defender.v <= 5):
        Defender.v = 5


      


      #-------------------------------------
      #-- Find targets and start blasting --
      #-------------------------------------

      TargetFound = False
      #Shoot forward laser
      if (not human_hunt_mode) and chance(FrontRadarChance):
        EnemyName, EnemyH, EnemyV, TargetFound = LookForTargets2(gx,0, 'EnemyShip',Defender,DefenderPlayfield,Canvas,EnemyShips)
        #EnemyName, EnemyH, EnemyV, TargetFound = LookForTargets(gx,0, 'EnemyShip',Defender,DefenderPlayfield,Canvas)
        
        if(TargetFound == True):
          #print("Target found.  Shooting:",EnemyName, EnemyH ,EnemyV)
          DefenderPlayfield,TargetHit = ShootTarget(gx, 0, EnemyName,EnemyH, EnemyV, Defender,DefenderPlayfield,Canvas)
          TargetFound = False

          if(TargetHit == True):
            Humans, HumanCount, DefenderPlayfield = DropPilot(EnemyH, EnemyV, Humans, DefenderPlayfield)
          #graphics.DrawLine(Canvas,Defender.h + 5, Defender.v + 2, Defender.h + 40, Defender.v + 2, graphics.Color(255,0,0));
            TargetHit = False
          else:
            #missed, so move Defender closer to enemy
            if(EnemyV > Defender.v):
              Defender.v = Defender.v + 1
            elif(EnemyV < Defender.v):
              Defender.v = Defender.v - 1


            DefenderSpeed = DefenderSpeed - DefenderSpeedIncrement
            if(DefenderSpeed < DefenderMinSpeed):
              DefenderSpeed = DefenderMinSpeed
            #Defender.h = Defender.h + (DefenderSpeed * 2 * DefenderDirection)



            RequestBombDrop = True

      #Look for targets on the ground
      if human_hunt_mode:
        RequestGroundLaser, RequestBombDrop, GroundV, Humans, EnemyShips = LookForGroundTargets(
            Defender, DefenderPlayfield, Ground, Humans, EnemyShips, hunt_humans=True,
        )
      elif(EnemyShipCount <= ShootGroundShipCount):
        if chance(GroundRadarChance):
          RequestGroundLaser, RequestBombDrop, GroundV,Humans,EnemyShips = LookForGroundTargets(Defender,DefenderPlayfield,Ground,Humans,EnemyShips)

      #Strafe Ground with lasers when requested
      if(RequestGroundLaser == True):
        #print("Shooting ground!")
        DefenderPlayfield, Ground, GroundParticles, Humans, HumanParticles, EnemyShips = ShootGround(gx,0,GroundV, Defender, DefenderPlayfield,Ground,Canvas,Humans, HumanParticles, EnemyShips,GroundParticles)  

        #greater chance of slowing down
        if chance_one(DefenderSpeedChangeChance):
          DefenderSpeed = DefenderSpeed - DefenderSpeedIncrement
          if(DefenderSpeed < DefenderMinSpeed):
            DefenderSpeed = DefenderMinSpeed
          #Defender.h = Defender.h + (DefenderSpeed * 2 * DefenderDirection)
        


        
        Ground = FlattenGround(gx + Defender.h +1,gx + Defender.h +3,MaxMountainHeight,Ground)
        ground_map = Ground.map
        
        if chance(LaserTurnOffChance):
          RequestGroundLaser = False      
      
      






      #--------------------------------
      #-- Reverse Defender           --
      #--------------------------------
      
      '''
      - record current h
      - record target h
      - turn on "reversing" indicator
      
      - flip ship
      - count from current_h to target_h
        - determine speed incredments needed to slow down from current speed, reach 0, then increase to opposite direction speed
        - each increment, change current h until it is target h
      
      '''

      if chance(ReversingChance) and (DefenderReversing == 0):
        DefenderReversing = 1
        CurrentH          = Defender.h
        OldSpeed          = DefenderSpeed
        SlowingDown       = 1

        if(DefenderDirection == 1):
          TargetH = hat_width - DefenderStartH
        else:
          TargetH = DefenderStartH
        MovementH = round(abs(CurrentH - TargetH) / ReversingSteps)
        DefenderDirection = DefenderDirection * -1

     
      if(DefenderReversing == 1):

        #ground / display
        if count % 2 == 0:
          gx = (gx + (DefenderSpeed / 2 * DefenderDirection)) % Ground.width


        #we want to slow down until we reach the minimum, then start going back up until OldSpeed
        if (SlowingDown == 1):
          DefenderSpeed = DefenderSpeed - ReversingAdjustmentSpeed
        else:
          DefenderSpeed = DefenderSpeed + ReversingAdjustmentSpeed
       
        
        Defender.h = Defender.h + (MovementH * DefenderDirection * -1) 
        
          
         #Keep h and speed in boundaries
        if Defender.h < DefenderStartH:
          Defender.h = DefenderStartH
        if Defender.h > (hat_width - DefenderStartH):
          Defender.h = (hat_width - DefenderStartH - Defender.width)

        if(DefenderSpeed < DefenderMinSpeed):
          DefenderSpeed = DefenderMinSpeed
          SlowingDown = 0
        if(DefenderSpeed > OldSpeed):
          DefenderSpeed = OldSpeed
          SlowingDown = 0

          
        #Stop reversing if at the target distance
        if(abs(Defender.h - TargetH) <= Defender.width ):
          DefenderReversing = 0
          #DefenderSpeed     = 1

        #print("Defender.h CurrentH TargetH MovementH DefenderSpeed DefenderReversing :",Defender.h,CurrentH,TargetH,MovementH,DefenderSpeed,DefenderReversing)         
          









      #--------------------------------
      #-- Paint defender on canvas   --
      #--------------------------------
      

      #paint normal Defender and Jet Trails
      if(DefenderDirection == 1):
        Canvas = LED.Defender.PaintAnimatedToCanvas(Defender.h,Defender.v,Canvas)
        
        if(DefenderSpeed > 1):
          for x in range(1,round(DefenderSpeed) * 2):
            r =  175 - x*25
            if(r <0):
              r = 0
            Canvas.SetPixel(Defender.h - x+1, Defender.v + 2,r,0,0)


      #Paint reverse Defender and Jet Trails
      else:
        #we only use DefenderReverse to draw the image, all other values are tracked by Defender original sprite
        Canvas = LED.DefenderReverse.PaintAnimatedToCanvas(Defender.h,Defender.v,Canvas)
      
        if(DefenderSpeed > 1):
          for x in range(1,round(DefenderSpeed) * 2):
            r =  175 - x*25
            if(r <0):
              r = 0
            Canvas.SetPixel(Defender.h + Defender.width +x-2, Defender.v + 2,r,0,0)


      

      


      #--------------------------------
      #-- Move Defender Bomb         --
      #--------------------------------

      #start dropping bombs when 15 enemies left
      #print("EnemyShipCount:",EnemyShipCount)
      if (RequestBombDrop == True
              or human_hunt_mode
              or (ShootGroundShipCount <= EnemyShipCount <= (ShootGroundShipCount * 2))):
      
        if(DefenderBomb.alive == False):
          #Lob the bombs for increased range and blast
          #print("Lobbing Bombs")
          if human_hunt_mode or chance(BombDropChance):
            DefenderBomb.alive = True
            RequestBombDrop = False
            DefenderBomb.h = Defender.h + (3 * DefenderDirection)
            DefenderBomb.v = Defender.v + 1
            DefenderBomb.velocityH = DefenderBombVelocityH * DefenderDirection
            DefenderBomb.velocityV = DefenderBombVelocityV
            DefenderBomb.bounces = 0
          
        

      #when 5 are left, drop bombs faster
      elif((5 <= EnemyShipCount <= 10) and DefenderBomb.alive == False):
        if chance(25):
          #print ("Making Bomb alive",DefenderBomb.alive,DefenderBomb.h,DefenderBomb.v)
          DefenderBomb.alive = True
          RequestBombDrop = False
          #bombs requested are more direct, to hit aliens hiding in the rocks
          DefenderBomb.h = Defender.h + 2
          DefenderBomb.v = Defender.v + 1
          DefenderBomb.velocityH = DefenderBombVelocityH / 2 * DefenderDirection
          DefenderBomb.velocityV = DefenderBombVelocityV * -3
          DefenderBomb.bounces = 0


      #Move bomb if it is alive
      if (DefenderBomb.alive == True):
        bh, bv, DefenderBomb, DefenderPlayfield, Canvas = MoveBomb(gx,DefenderBomb,DefenderPlayfield,Canvas)


        bh = round(DefenderBomb.h)
        bv = round(DefenderBomb.v)

        if 0 <= bv < hat_height and 0 <= (bh + DisplayH) < Ground.width:
            pixel = ground_map[bv][bh + DisplayH]
        else:
            pixel = (0, 0, 0)

        if pixel != (0, 0, 0) or DefenderBomb.bounces >= MaxBombBounces:
            (DefenderBomb,
            GroundParticles,
            Humans,
            HumanParticles,
            EnemyShips,
            Ground,
            DefenderPlayfield,
            Canvas
            ) = DetonateBombIfAtGround(DisplayH,
                                        0,
                                        DefenderBomb,
                                        Ground,
                                        GroundParticles,
                                        Humans,
                                        HumanParticles,
                                        EnemyShips,
                                        DefenderPlayfield,
                                        Canvas,
                                        GroundRGB,
                                        SurfaceRGB)
        #reset the bomb
        if (DefenderBomb.alive == False):
          RequestBombDrop        = False
          DefenderBomb.velocityH = 0
          DefenderBomb.velocityV = 0
          DefenderBomb.h         = 0
          DefenderBomb.v         = 0








      #--------------------------------
      #-- Move Particles             --
      #--------------------------------
      MoveGroundParticles(GroundParticles,Canvas)
      MoveHumanParticles(HumanParticles,Canvas)







      #--------------------------------
      #-- Numerical Displays         --
      #--------------------------------

      #This displayes a small clock in upper right hand corner
      #removing it in favor of a scrolling clock
      #ClockSprite.h = LED.HatWidth - (ClockSprite.width * ClockZoom)
      #Canvas = LED.CopySpriteToCanvasZoom(ClockSprite,ClockSprite.h,ClockSprite.v,ClockSprite.rgb,(0,0,0),ClockZoom,False,Canvas)


      #Add display
      EnemyAliveCount = count_alive(EnemyShips)
      EnemyShipCount = EnemyAliveCount
      
      if ShowCountHUD:
        if(OldEnemyAliveCount != EnemyAliveCount):
          Canvas,EnemyCountSprite = DisplayCount(EnemyCountH, EnemyCountV, EnemyCountRGB,'E',EnemyAliveCount,Canvas)
          OldEnemyAliveCount = EnemyAliveCount
        else:
          Canvas = LED.CopySpriteToCanvasZoom(EnemyCountSprite,EnemyCountH,EnemyCountV,(EnemyCountRGB),(0,0,0),ZoomFactor = 1,Fill=False,Canvas=Canvas)

      # Level clear: all enemies and humans eliminated before next wave.
      humans_alive_now = count_alive(Humans)
      if (wave_enemies_spawned and EnemyAliveCount == 0 and humans_alive_now == 0
              and len(EnemyShips) > 0
              and time.time() - last_wave_advance_time > 1):
          LevelCount += 1
          WaveCount += 1
          print(f"[Defender2] Level complete. Advancing to wave {WaveCount}.")
          last_wave_advance_time = time.time()
          (ShipType, EnemyShips, DefenderPlayfield, Ground, EnemyAliveCount,
           GroundRGB, SurfaceRGB) = advance_wave(
              True, WaveCount, ShipType, EnemyShips, DefenderPlayfield, Ground,
              Background, Middleground, Foreground, Canvas, Defender,
              bx, mx, fx, gx, ClockSprite, EnemyCountSprite, HumanCountSprite,
              GroundRGB, SurfaceRGB,
          )
          EnemyShipCount = EnemyAliveCount
          OldEnemyAliveCount = -1
          wave_enemies_spawned = True
          ground_map = Ground.map
          Canvas = LED.TheMatrix.SwapOnVSync(Canvas)
          continue

      HumanCount = count_alive(Humans)
      if ShowCountHUD:
        if(OldHumanCount != HumanCount):
          Canvas, HumanCountSprite = DisplayCount(HumanCountH, HumanCountV, HumanCountRGB,'H', HumanCount,Canvas)
          OldHumanCount = HumanCount
        else:
          Canvas = LED.CopySpriteToCanvasZoom(HumanCountSprite,HumanCountH,HumanCountV,(HumanCountRGB),(0,0,0),ZoomFactor = 1,Fill=False,Canvas=Canvas)

    
   

      


      #--------------------------------
      #-- Display canvas             --
      #--------------------------------

      Canvas = LED.TheMatrix.SwapOnVSync(Canvas)


      #--------------------------------
      #-- Add more enemies           --
      #--------------------------------

      if (0 < EnemyAliveCount <= SpawnNewEnemiesTargetCount
              and time.time() - last_wave_advance_time > 1):
        WaveCount = WaveCount + 1
        last_wave_advance_time = time.time()
        print(f"[Defender2] Reinforcements for wave {WaveCount}.")
        (ShipType, EnemyShips, DefenderPlayfield, Ground, EnemyAliveCount,
         GroundRGB, SurfaceRGB) = advance_wave(
            False, WaveCount, ShipType, EnemyShips, DefenderPlayfield, Ground,
            Background, Middleground, Foreground, Canvas, Defender,
            bx, mx, fx, gx, ClockSprite, EnemyCountSprite, HumanCountSprite,
            GroundRGB, SurfaceRGB,
        )
        EnemyShipCount = EnemyAliveCount
        OldEnemyAliveCount = -1
        ground_map = Ground.map



        

   


      #--------------------------------
      #-- Garbage Cleanup            --
      #--------------------------------

      # To reduce the amount of objects being tracked, we remove old
      # ships and particles that are off-screen and no longer active.

      DeleteH = DisplayH - hat_width

      # -- Enemy Ships Cleanup --
      if count % (GarbageCleanupChance + 1) == 0:
          EnemyShips = [
              ship for ship in EnemyShips
              if is_alive(ship) or (DeleteH <= ship.h <= DisplayH + hat_width)
          ]
          #print("Garbage cleanup EnemyShips:", len(EnemyShips))

      # -- Ground Particles Cleanup --
      if count % (GroundCleanupChance + 1) == 0:
          GroundParticles = [
              particle for particle in GroundParticles
              if particle.h >= (DisplayH - 1)
          ]
          #print("Ground cleanup")
          
      #--------------------------------
      #-- Human and Particle Cleanup --
      #--------------------------------

      if count % (GarbageCleanupChance + 1) == 0:
          # Clean up dead humans
          Humans = [h for h in Humans if is_alive(h)]

          # Optional debug print
          # print("Garbage cleanup Human count:", len(Humans))

          # Clean up off-screen human particles
          if count % 51 == 0:
              DeleteH = DisplayH - 1
              HumanParticles = [
                  p for p in HumanParticles
                  if DeleteH <= p.h <= DeleteH + hat_width
              ]



      #time.sleep(GameSleep)



        




  #let the display show the final results before clearing
  time.sleep(1)
  LED.ClearBigLED()

  return






























def LaunchDefender2(Duration = 10000,ShowIntro=True,StopEvent=None):
  
  #--------------------------------------
  # M A I N   P R O C E S S I N G      --
  #--------------------------------------

  global SlowingDown


  if(ShowIntro == True):


    LED.ShowTitleScreen(
        BigText             = 'SPACE',
        BigTextRGB          = LED.HighRed,
        BigTextShadowRGB    = LED.ShadowRed,
        LittleText          = 'OFFENDER II',
        LittleTextRGB       = LED.MedGreen,
        LittleTextShadowRGB = (0,10,0), 
        ScrollText          = 'DEFENDER 2 — TIME FOR PAYBACK',
        ScrollTextRGB       = LED.MedYellow,
        ScrollSleep         = 0.03, # time in seconds to control the scrolling (0.005 is fast, 0.1 is kinda slow)
        DisplayTime         = 1,           # time in seconds to wait before exiting 
        ExitEffect          = 0            # 0=Random / 1=shrink / 2=zoom out / 3=bounce / 4=fade /5=fallingsand
        )


  
    LED.ClearBigLED()
    LED.ClearBuffers()
    CursorH = 0
    CursorV = 0
    LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"CONNECTING TO DEEP SPACE ARRAY",CursorH=CursorH,CursorV=CursorV,MessageRGB=(150,150,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalTypeSpeed)
    LED.BlinkCursor(CursorH= CursorH,CursorV=CursorV,CursorRGB=CursorRGB,CursorDarkRGB=CursorDarkRGB,BlinkSpeed=0.5,BlinkCount=2)
    LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"TRANSMITTING COORDINATES",CursorH=CursorH,CursorV=CursorV,MessageRGB=(150,150,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalTypeSpeed)
    LED.BlinkCursor(CursorH= CursorH,CursorV=CursorV,CursorRGB=CursorRGB,CursorDarkRGB=CursorDarkRGB,BlinkSpeed=0.5,BlinkCount=2)
    LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"FIRE AT WILL!",CursorH=CursorH,CursorV=CursorV,MessageRGB=(225,0,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)
    LED.BlinkCursor(CursorH= CursorH,CursorV=CursorV,CursorRGB=CursorRGB,CursorDarkRGB=CursorDarkRGB,BlinkSpeed=0.5,BlinkCount=2)


  PlayDefender2(Duration,StopEvent)
      

  LED.ClearBigLED()
  LED.ClearBuffers()
  CursorH = 0
  CursorV = 0
  LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"MISSION COMPLETE",CursorH=CursorH,CursorV=CursorV,MessageRGB=(0,175,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalTypeSpeed)
  LED.BlinkCursor(CursorH= CursorH,CursorV=CursorV,CursorRGB=CursorRGB,CursorDarkRGB=CursorDarkRGB,BlinkSpeed=0.5,BlinkCount=2)






#execute if this script is called directly
if __name__ == "__main__" :
  StopEvent=None
  while(1==1):
    #LED.LoadConfigData()
    #LED.SaveConfigData()
    print("After SAVE DefenderGamesPlayed:",LED.DefenderGamesPlayed)
    LaunchDefender2(100000,False,StopEvent)        


















