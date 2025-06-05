#!/usr/bin/env python
#print("moves:",moves,end='\r', flush=True)
#notes: check all playfield[v][h] in all versions to make sure v comes first.  I found one where it was switched
#       and this may account for when the zombie dots don't die
# - ship objects tLED.Hat also have a sprite should have
#   their HV co-ordinates looked at.  We want to draw the sprite around the center of the sprite, not the corner
#   Look at SpaceDot homing missile for an example.
#------------------------------------------------------------------------------



#------------------------------------------------------------------------------
#  SPACEDOT                                                                  --
#                                                                            --
#------------------------------------------------------------------------------



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
#   Version: 0.1                                                             --
#   Date:    January 15, 2022                                                --
#   Reason:  Converted to use LEDarcade                                      --
#------------------------------------------------------------------------------



#------------------------------------------------------------------------------
# Initialization Section                                                     --
#------------------------------------------------------------------------------

import LEDarcade as LED
LED.Initialize()
import copy
import random
import time
import numpy
import math
from datetime import datetime, timedelta


random.seed()
start_time = time.time()






#----------------------------
#-- GLOBAL VARIABLES       --
#----------------------------
SpaceDotWallLives   = 50
SpaceDotGroundLives = 1
PlanetSurfaceSleep  = 1000
DebrisCleanupSleep  = 2000 #make sure empty cells on playfield are displayed as empty (0,0,0) 

Playfield = ([[]])
Playfield = [[0 for i in range(LED.HatWidth)] for i in range(LED.HatHeight)]


#Wave
MinHomingMissileWave = 5 #homning missles / ufos only show up after this wave
MinBomberWave        = 3 #homning missles / ufos only show up after this wave


SpaceDotMinH = 25
SpaceDotMaxH = 63
SpaceDotMinV = 0
SpaceDotMaxV = 26

#Ground
GroundV = SpaceDotMaxV - 1
moves   = 1

#Player
PlayerShipSpeed       = 250
PlayerShipMinSpeed    = 25
PlayerShipAbsoluteMinSpeed = 10
MaxPlayerMissiles     = 5
PlayerMissileCount    = 2
PlayerMissileSpeed    = 25
PlayerMissileMinSpeed = 8
PlayerShipLives       = 3


#BomberShip
BomberShipSpeed       = 80
ChanceOfBomberShip    = 50000  #chance of a bomberhsip appearing
BomberRockSpeed       = 30    #how fast the bomber dropped asteroid falls
BomberShipLives       = 3     #takes X hits before exploding

#UFO
UFOMissileSpeed = 50
UFOShipSpeed    = 50  #also known as the EnemeyShip
UFOShipMinSpeed = 25
UFOShipMaxSpeed = 100
UFOLives    = 1
ChanceOfUFO = 30000

#HomingMissile 
UFOFrameRate               = 50  #random animated homing missiles
HomingMissileFrameRate     = 100  
HomingMissileInitialSpeed  = 75
HomingMissileLives         = 35
HomingMissileSprites       = 12     #number of different sprites tLED.Hat can be homing missiles
HomingMissileDescentChance = 3      #chance of homing missile  not descending, lower number greater chance of being slow
ChanceOfHomingMissile      = 75000  #chance of a homing missile appearing



#Points
SpaceDotScore        = 0
UFOPoints            = 10
BomberPoints         = 5
BomberHitPoints      = 1
HomingMissilePoints  = 5
AsteroidLandedPoints = 1
AsteroidPoints       = 5

#Asteroids
WaveStartV           = -15
WaveMinSpeed         = 5     #The fastest the wave of asteroids can fall
WaveSpeedRange       = 80    #how much variance in the wave speed min and max
AsteroidMinSpeed     = 20    #lower the number the faster the movement (based on ticks)
AsteroidMaxSpeed     = 80  
AsteroidSpawnChance  = 100   #lower the number the greater the chance
WaveDropSpeed        = 500   #how often the next chunk of the wave is dropped
MovesBetweenWaves    = 500
AsteroidsInWaveMax   = 200
AsteroidsInWaveMin   = 5 
AsteroidsToDropMin   = 3    #Number of asteroids to drop at a time
AsteroidsToDropMax   = 5   #Number of asteroids to drop at a time

#Ground
GroundDamageLimit    = 10
GroundExplosions     = 25
DamageR              = 50
DamageG              = 5

ScrollSleep         = 0.025
MainSleep           = 0.05
TerminalTypeSpeed   = 0.02  #pause in seconds between characters
TerminalScrollSpeed = 0.02  #pause in seconds between new lines
CursorRGB           = (0,255,0)
CursorDarkRGB       = (0,50,0)


#Sprite display locations
ClockH,      ClockV,      ClockRGB      = 0,0,  (0,150,0)
DayOfWeekH,  DayOfWeekV,  DayOfWeekRGB  = 0,6,  (150,0,0)
MonthH,      MonthV,      MonthRGB      = 0,12, (0,20,200)
DayOfMonthH, DayOfMonthV, DayOfMonthRGB = 2,18, (100,100,0)
SpriteFillerRGB = (0,4,0)
CheckClockSpeed = 50






#------------------------------
#-- Ship and Missile objects --
#------------------------------


PlayerShipR = LED.SDMedBlueR
PlayerShipG = LED.SDMedBlueG
PlayerShipB = LED.SDMedBlueB
PlayerMissileR = LED.SDMedWhiteR
PlayerMissileG = LED.SDMedWhiteG
PlayerMissileB = LED.SDMedWhiteB


#def __init__(h,v,r,g,b,direction,scandirection,speed,alive,lives,name,score,exploding):
Empty      = LED.Ship(-1,-1,0,0,0,0,1,0,0,0,'EmptyObject',0,0)


#define objects
#def __init__(self,h,v,r,g,b,direction,scandirection,speed,alive,lifes,name,score,exploding):
PlayerShip = LED.Ship(3 + SpaceDotMinH,SpaceDotMaxV - 2,PlayerShipR,PlayerShipG,PlayerShipB,4,1,PlayerShipSpeed,1,3,'Player1', 0,0)
PlayerShip.lives = PlayerShipLives


EnemyShip  = LED.Ship(SpaceDotMinH,0,LED.SDMedPurpleR,LED.SDMedPurpleG,LED.SDMedPurpleB,4,3,UFOShipSpeed,0,3,'UFO', 0,0)
EnemyShip.lives = UFOLives
Empty      = LED.Ship(-1,-1,0,0,0,0,1,0,0,0,'EmptyObject',0,0)
  


#Make a bomber rock
BomberRock = LED.Ship(-1,-1,200,0,0,3,3,15,0,1,'BomberRock', 0,0)
BomberRock.alive = 0
BomberRock.speed = BomberRockSpeed
BomberRock.exploding = 0



UFOMissile1   = LED.Ship(-1,-0,PlayerMissileR,PlayerMissileG,PlayerMissileB,3,3,UFOMissileSpeed,0,0,'UFOMissile',0,0)
UFOMissile2   = LED.Ship(-1,-0,PlayerMissileR,PlayerMissileG,PlayerMissileB,3,3,UFOMissileSpeed,0,0,'UFOMissile',0,0)
UFOMissile3   = LED.Ship(-1,-0,PlayerMissileR,PlayerMissileG,PlayerMissileB,3,3,UFOMissileSpeed,0,0,'UFOMissile',0,0)

UFOMissile1.Explosion = copy.deepcopy(LED.AsteroidExplosion)
UFOMissile2.Explosion = copy.deepcopy(LED.AsteroidExplosion)
UFOMissile3.Explosion = copy.deepcopy(LED.AsteroidExplosion)



# BomberShip records the location and status
# BomberSprite is the color animated sprite of the ship

#(self,h,v,name,width,height,frames,currentframe,framerate,grid):
BomberSprite = LED.ColorAnimatedSprite(h=0, v=0, name="BomberShip", width=3, height=1, frames=4, framerate=25,grid=[])
BomberSprite.grid.append(
  [ 9, 9, 9 ]
)
BomberSprite.grid.append(
  [ 9,10, 9 ]
)
BomberSprite.grid.append(
  [ 9,11, 9 ]
)
BomberSprite.grid.append(
  [ 9,10, 9 ]
)

BomberShip = LED.Ship(
  h=0,
  v=0,
  r=0,g=0,b=0,
  direction=2,scandirection=3,
  speed=BomberShipSpeed,alive=0,lives=BomberShipLives,name="BomberShip",score=0,exploding=0
) 



BomberShip.h = -2 + SpaceDotMinH
BomberShip.v =  SpaceDotMinV
BomberShip.alive = 0
#HomingMissileShip.h =  SpaceDotMinH + (int(SpaceDotMinH / 2))
#HomingMissileShip.v =  SpaceDotMinV



#Explosion Sprites
PlayerShip.Explosion = copy.deepcopy(LED.PlayerShipExplosion)  
BomberShip.Explosion = copy.deepcopy(LED.BomberShipExplosion)  




BomberShip.Explosion.framerate = 10
BomberRock.Explosion           = copy.deepcopy(LED.PlayerShipExplosion)  
BomberRock.Explosion.framerate = 2
BomberRock.Explosion.h         = -1
BomberRock.Explosion.v         = -1

#HomingMissileShipExplosion    = copy.deepcopy(PlayerShipExplosion)  
HomingMissileShipExplosion    = copy.deepcopy(LED.BigShipExplosion)  





#Custom Sprite List
HomingMissileSpriteList = []


#HomingMissileSpriteList.append(ChickenRunning) #chicken needs work
HomingMissileSpriteList.append(LED.SatelliteSprite)
HomingMissileSpriteList.append(LED.SatelliteSprite2)
HomingMissileSpriteList.append(LED.SatelliteSprite3)
HomingMissileSpriteList.append(LED.SatelliteSprite4)
HomingMissileSpriteList.append(LED.SatelliteSprite5)
HomingMissileSpriteList.append(LED.SatelliteSprite6)
HomingMissileSpriteList.append(LED.SatelliteSprite7)
HomingMissileSpriteList.append(LED.SmallUFOSprite)
HomingMissileSpriteList.append(LED.SmallUFOSprite2)
HomingMissileSpriteList.append(LED.SmallUFOSprite3)
HomingMissileSpriteList.append(LED.SmallUFOSprite4)
HomingMissileSpriteList.append(LED.SmallUFOSprite5)
HomingMissileSpriteList.append(LED.SmallUFOSprite6)
HomingMissileSpriteList.append(LED.SmallUFOSprite7)
HomingMissileSpriteList.append(LED.MediumUFOSprite)
HomingMissileSpriteList.append(LED.MediumUFOSprite2)
HomingMissileSpriteList.append(LED.MediumUFOSprite3)
HomingMissileSpriteList.append(LED.MediumUFOSprite4)
HomingMissileSpriteList.append(LED.LargeUFOSprite1)
HomingMissileSpriteList.append(LED.LargeUFOSprite2)
HomingMissileSpriteList.append(LED.LargeUFOSprite3)
HomingMissileSpriteList.append(LED.LargeUFOSprite4)
HomingMissileSpriteList.append(LED.LargeUFOSprite5)
HomingMissileSpriteList.append(LED.LargeUFOSprite6)
HomingMissileSpriteList.append(LED.WideUFOSprite1)
HomingMissileSprites = len(HomingMissileSpriteList)

HomingMissileShip    = LED.Ship(SpaceDotMinH,SpaceDotMaxV - 1,PlayerShipR,PlayerShipG,PlayerShipB,4,1,8,1,3,'HomingMissile', 0,0)
HomingMissileSprite  = HomingMissileSpriteList[random.randint(0,HomingMissileSprites -1 )]
HomingMissileSprite.framerate = HomingMissileFrameRate


HomingMissileSprite   = HomingMissileSpriteList[random.randint(0,HomingMissileSprites -1 )]
HomingMissileSprite.h = -1
HomingMissileSprite.v = -1
HomingMissileSprite.direction     = 5
HomingMissileSprite.scandirection = 3
HomingMissileSprite.speed = HomingMissileInitialSpeed
HomingMissileSprite.alive = 0
HomingMissileSprite.lives = HomingMissileLives
HomingMissileSprite.name  = "HomingMissile"
HomingMissileSprite.score = 0
HomingMissileSprite.exploding = 0
HomingMissileSprite.framerate = HomingMissileFrameRate







#Make an array of PlayerMissiles
PlayerMissiles = []
for i in range(0,PlayerMissileCount):
  print ("Making PlayerMissile:",i)
  r,g,b = (200,200,200)
  PlayerMissiles.append(LED.Ship(-1,-1,PlayerMissileR,PlayerMissileG,PlayerMissileB,1,1,5,0,1,'PlayerMissile', 0,0))
  PlayerMissiles[i].alive = 0
  PlayerMissiles[i].exploding = 0
  PlayerMissiles[i].Explosion = copy.deepcopy(LED.SmallExplosion)
  PlayerMissiles[i].Explosion.alive = 0
  PlayerMissiles[i].Explosion.exploding = 0
  PlayerMissiles[i].speed = PlayerMissileSpeed
  PlayerMissiles[i].h = -1
  PlayerMissiles[i].v = -1







#----------------------------
#-- SpaceDot               --
#----------------------------

#Custom Colors because we will be running at full brightness
# Future work: convert to proper tuples.






class AsteroidWave(object):

  def __init__(
    self,
    AsteroidCount    = AsteroidsInWaveMin,
    AsteroidMinSpeed = AsteroidMinSpeed,
    AsteroidMaxSpeed = AsteroidMaxSpeed
    ):

    self.AsteroidCount      = AsteroidCount
    self.AsteroidMinSpeed   = AsteroidMinSpeed
    self.AsteroidMaxSpeed   = AsteroidMaxSpeed
    self.Asteroids          = []
    self.TotalDropped       = 0
    self.TotalAlive         = 0
    self.Alive              = True
    self.WaveCount          = 1
    self.WaveDropSpeed      = WaveDropSpeed


    self.Explosion = LED.ColorAnimatedSprite(
      h      = 0 , 
      v      = 0, 
      name   = 'Debris',
      width  = 3, 
      height = 1,
      frames = 7,
      framerate    = 50,
      grid=[]
    )

    self.Explosion.grid.append(      [        0,44, 0      ]    )
    self.Explosion.grid.append(      [       45,20,45      ]    )
    self.Explosion.grid.append(      [       20,20,20      ]    )
    self.Explosion.grid.append(      [        8, 8, 8      ]    )
    self.Explosion.grid.append(      [        8, 6, 8      ]    )
    self.Explosion.grid.append(      [        6, 5, 6      ]    )
    self.Explosion.grid.append(      [        5, 5, 5      ]    )



#Create seems to be slow.  Maybe only create once, then refresh it the next time.



  def CreateAsteroidWave(self):
      #Make an wave of asteroids
      r,g,b = LED.BrightColorList[random.randint(1,27)]

      self.Asteroids = []      

      #print("--Create Asteroids:",self.AsteroidCount," RGB:",r,g,b)
      for i in range(0,self.AsteroidCount):
        #print ("Asteroid:",i)
        self.Asteroids.append( LED.Ship(
          h = -1,
          v = -1,
          r = r,
          g = g,
          b = b,
          direction     = 3,
          scandirection = 3,
          speed         = random.randint(self.AsteroidMinSpeed,self.AsteroidMaxSpeed),
          alive         = 1,
          lives         = 1,
          name          = 'Asteroid',
          score         = 0,
          exploding     = 0)
        )
        self.Asteroids[i].alive       = 1
        self.Asteroids[i].Droppeded   = 0
        self.Asteroids[i].Explosion   = self.Explosion
        self.Asteroids[i].Explosion.h = -1
        self.Asteroids[i].Explosion.v = -1
        self.Asteroids[i].Explosion.alive     = 0
        self.Asteroids[i].Explosion.alive     = 0
        self.Asteroids[i].Explosion.exploding = 0

      self.UpdateCounts()
      #print("Wave Alive:",self.Alive," AsteroidCount:",self.AsteroidCount,"TotalAlive:",self.TotalAlive," TotalDropped:",self.TotalDropped)
      #print ("--end--")
      return


  def UpdateCounts(self):
    AsteroidsAlive   = 0
    AsteroidsDropped = 0
    #print("Updating counts.  Asteroids:",self.AsteroidCount)    

    for i in range(0,self.AsteroidCount):

      if self.Asteroids[i].alive == 1:
        AsteroidsAlive = AsteroidsAlive + 1
        #FlashDot(self.Asteroids[i].h,self.Asteroids[i].v,0.01)
        #print("stuck:",self.Asteroids[i].h,self.Asteroids[i].v,self.Asteroids[i].alive,self.Asteroids[i].lives,self.Asteroids[i].speed,self.Asteroids[i].r,self.Asteroids[i].g,self.Asteroids[i].b,self.Asteroids[i].name)
      if self.Asteroids[i].dropped == 1:
        AsteroidsDropped = AsteroidsDropped + 1

      

    self.TotalAlive   = AsteroidsAlive
    self.TotalDropped = AsteroidsDropped
    
    if(self.TotalAlive >0):
      self.Alive = True
    else:
      self.Alive = False
      self.TotalAlive = 0

    #print("Update Counts:  Wave.Alive:",self.Alive," AsteroidCount:",self.AsteroidCount,"TotalAlive:",self.TotalAlive," TotalDropped:",self.TotalDropped)

    return



  def DropAsteroids(self,AsteroidsToDrop,Playfield):
      
    
    self.UpdateCounts()
    i = 0
    AsteroidsDropped = 0
    StartH           = 0
    StartV           = -5
    tries            = 0  # we are goign to try to a maximum of 255 times then exit, so we don't slow down game


    if (self.TotalAlive <= AsteroidsToDrop):
      AsteroidsToDrop = self.TotalAlive

    #print("AsteroidsToDrop:",AsteroidsToDrop,"Asteroids in wave:",self.AsteroidCount)


    #Place asteroids to drop on the playfield
    i = 0
    while (AsteroidsDropped < AsteroidsToDrop and tries < 255 and i < self.AsteroidCount): 
      if (self.Asteroids[i].alive == 1 and self.Asteroids[i].dropped == 0):
        StartV = 0
        StartH = random.randint(SpaceDotMinH,SpaceDotMaxH)
        #print("Drop Asteroid i:",i)
        #find unoccupied spot
        while (Playfield[StartV][StartH].name != 'EmptyObject' and tries <= 255):
          tries = tries + 1
          StartH = random.randint(SpaceDotMinH,SpaceDotMaxH)      

        if (tries < 255):        
          self.Asteroids[i].h       = random.randint(SpaceDotMinH,SpaceDotMaxH)
          self.Asteroids[i].v       = StartV
          self.Asteroids[i].dropped = 1
          AsteroidsDropped          = AsteroidsDropped + 1
          self.Asteroids[i].Display()

        else:
          break

      i = i + 1
        
    self.UpdateCounts()





def CleanupDebris(StartH,EndH,StartV,EndV,Playfield):
  for V in range(StartV,EndV):
    for H in range (StartH,EndH):
      if ((Playfield[V][H].name  == 'EmptyObject') 
       or (Playfield[V][H].name  in ('Explosion','HomingMissile') and Playfield[V][H].alive == 0)):
        LED.setpixel(H,V,0,0,0)
        Playfield[V][H] = LED.EmptyObject


  








#--------------------------------------
#  SpaceDot       PlaySpaceDot       -- 
#--------------------------------------


#We need an 16 x 16 grid to represent the playfield
#each ship, each missile, each bunker will be an object tLED.Hat
#is located on the playfield.  TLED.Hat way we can scan the individual 
#objects and not have to rely on the pixel colors to determine wLED.Hat is wLED.Hat












def CheckBoundarySpaceDot(h,v):
  BoundaryHit = 0
  if (v < SpaceDotMinV or v > SpaceDotMaxV  or h < SpaceDotMinH or h > SpaceDotMaxH):
    BoundaryHit = 1
  return BoundaryHit;




  
def ScanSpaceDot(h,v):

  Item = ''
  OutOfBounds = CheckBoundarySpaceDot(h,v)
  
  #top of the playfield is ok, lets asteroids fall
  

  if (OutOfBounds == 1 and v < 0):
    Item = 'aboveborder'
    #print ("Border found HV: ",h,v)
  elif (OutOfBounds == 1 and v >= 0):
    Item = 'border'

  else:

    try:
      Item = Playfield[v][h].name
      
      
    except:
      print ('Playfield error h,v:',h,v)
      print(Playfield[v][h])
      LED.FlashDot(h,v,3)
    
  return Item
  

def ScanAroundShip(h,v,direction):
  ScanDirection = 0
  ScanH         = 0
  ScanV         = 0
  Item          = ''
  ItemList      = ['NULL']
  
  #  8 1 2
  #  7   3  
  #  6 5 4  

  #
  
  
  #1
  ScanDirection = direction
  ScanH, ScanV = LED.CalculateDotMovement(h,v,ScanDirection)
  Item = ScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)
  #2
  ScanDirection =  LED.TurnRight(ScanDirection)
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = ScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)
  #3
  ScanDirection =  LED.TurnRight(ScanDirection)
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = ScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)

  #4
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = ScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)

  #5
  ScanDirection =  LED.TurnRight(ScanDirection)
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = ScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)

  #6
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = ScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)

  #7
  ScanDirection =  LED.TurnRight(ScanDirection)
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = ScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)

  #8
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = ScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)

  return ItemList

  
def ScanShip(h,v,direction):
  ScanDirection = 0
  ScanH         = 0
  ScanV         = 0
  Item          = ''
  ItemList      = ['NULL']

  
  # We will scan 5 spots around the dot
  # and 6 more in front
  
  # Note: we now have grass, so the scan distance is 1 level shorter
  #       It will be complicated to remove slot 7 
  #       (because of the use of slots 11,12,13, so I will instead populate it
  #       with a copy of slot 6.
  #       
  #       Upgraded to 64x32 display
  #       
  #  33 33 33
  #     32
  #     31
  #     30
  #     29
  #     28
  #     27
  #     26
  #     25 
  #     24
  #     23
  #  20 21 22
  #     19
  #     18
  #     17
  #     16
  #     15
  #     14
  #  11 12 13
  #    10
  #     9
  #     8
  #     7
  #     6
  #  2  3  4
  #  1     5
  #
  
  #Scanning Probe
  #Turn left move one + SCAN
  #Turn Right move one + SCAN
  #Turn Right Move one + SCAN 
  #Move one + SCAN 
  #Turn Right Move one + SCAN 
  
  
  #LL 1
  ScanDirection = LED.TurnLeft(direction)
  ScanH, ScanV = LED.CalculateDotMovement(h,v,ScanDirection)
  Item = ScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)
  
  #LF 2
  ScanDirection =  LED.TurnRight(ScanDirection)
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = ScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)
  
  #FF 3
  ScanDirection =  LED.TurnRight(ScanDirection)
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = ScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)
  
  #FR 4
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = ScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)
  
  #RR 5
  ScanDirection =  LED.TurnRight(ScanDirection)
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = ScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)

  #F1 6
  ScanDirection = LED.ReverseDirection(ScanDirection)
  ScanH, ScanV  = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  ScanDirection = LED.TurnLeft(ScanDirection)
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  ScanDirection =  LED.TurnRight(ScanDirection)
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = ScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)

  #F2 7
  # This slot has become redundant due to a shorter playfield.
  #ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = ScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)
  
  #F3 8
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = ScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)
  
  #F4 9
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = ScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)

  #F5 10
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = ScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)

  #F6 11
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  ScanDirection = LED.TurnLeft(ScanDirection)
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = ScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)

  #F7 12
  ScanDirection = LED.ReverseDirection(ScanDirection)
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = ScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)

  #F8 13
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = ScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)

  #14 -- new additions since moving to larger grid
  ScanDirection = LED.ReverseDirection(ScanDirection)
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  ScanDirection =  LED.TurnRight(ScanDirection)
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = ScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)

  #15
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = ScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)

  #16
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = ScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)

  #17
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = ScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)

  #18
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = ScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)

  #19
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = ScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)
  
  #20
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  ScanDirection = LED.TurnLeft(ScanDirection)
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = ScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)

  #21
  ScanDirection = LED.ReverseDirection(ScanDirection)
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = ScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)
  

  #22
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = ScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)


  #23
  ScanDirection = LED.ReverseDirection(ScanDirection)
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  ScanDirection =  LED.TurnRight(ScanDirection)
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  
  Item = ScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)

  #24
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = ScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)

  #25
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = ScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)
  #26
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = ScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)
  #27
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = ScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)
  #28
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = ScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)
  #29
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = ScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)
  #30
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = ScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)
  #31
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = ScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)
  #32
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = ScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)
  

  #33
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  ScanDirection = LED.TurnLeft(ScanDirection)
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = ScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)

  #34
  ScanDirection = LED.ReverseDirection(ScanDirection)
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = ScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)
  

  #35
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = ScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)


  return ItemList;


def ScanBomberShip(BomberShip):
  ScanDirection = BomberShip.direction
  ScanH         = BomberShip.h
  ScanV         = BomberShip.v
  Item          = ''
  ItemList      = ['NULL']
  i             = 0

  
  # We will scan  around the dot
  # and  more in front
  
  # Note: we now have grass, so the scan distance is 1 level shorter
  #       It will be complicated to remove slot 7 
  #       (because of the use of slots 11,12,13, so I will instead populate it
  #       with a copy of slot 6.
  #       
  
  #
  #          
  #      
  #  1  .  .  .  3
  #  x  x  2  x  x
  #        4
  #        5
  #        6
  #        7
  #        8
  #        9
  #        10
  #        11
  #        12
  #        ..
  #        ..
  #        25  
  
  
  #1
  ScanH = ScanH-1
  Item = ScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)
  
  #2
  ScanH, ScanV = ScanH +2, ScanV + 1
  Item = ScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)
  
  #3
  ScanH, ScanV = ScanH + 2, ScanV -1
  Item = ScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)
  
  #4 - 25
  for i in range(i,20):
    ScanH, ScanV = ScanH -2, ScanV + 2
    Item = ScanSpaceDot(ScanH,ScanV)
    ItemList.append(Item)
  

  return ItemList;


  
  
def HitBomber(BomberShip):
  global SpaceDotScore

  h = BomberShip.h
  v = BomberShip.v
  if (BomberShip.lives > 0):
    BomberShip.lives = BomberShip.lives - 1
    SpaceDotScore = SpaceDotScore + BomberHitPoints
  else:
    #BomberShip.alive = 0
    #SpaceDotScore = SpaceDotScore + BomberPoints
    #PlayerShipExplosion.Animate(h-2,v-2,'forward',0.025)
    BomberShip.exploding = 1
    BomberShip.alive     = 0
    BomberShip.Explosion.h = h
    BomberShip.Explosion.v = v

    SpaceDotScore = SpaceDotScore + BomberPoints

    #Erase playfield (ship is 3 dots across)
    if (h-1 > 0 and h-1 <= LED.HatWidth-1):
      Playfield[v][h-1] = Empty

    if (h > 0 and h <= LED.HatWidth-1):
      Playfield[v][h] = Empty

    if (h+1 > 0 and h+1 <= LED.HatWidth-1):
      Playfield[v][h+1] = Empty

    if (h+2 > 0 and h+2 <= LED.HatWidth-1):
      Playfield[v][h+2] = Empty
    BomberShip.Erase()


def HitHomingMissile(HomingMissileShip,HomingMissileSprite):
  global SpaceDotScore
  global Playfield

  h = HomingMissileShip.h
  v = HomingMissileShip.v
  if (HomingMissileShip.lives > 0):
    HomingMissileShip.lives = HomingMissileShip.lives - 1
    SpaceDotScore = SpaceDotScore + HomingMissilePoints

  if (HomingMissileShip.lives == 0):
    HomingMissileShip.exploding = 1
    HomingMissileShip.alive     = 0
    #print ("blowing up homing missile")
    #LED.FlashDot(h,v,1)
    HomingMissileSprite.h = h
    HomingMissileSprite.v = v
    Playfield     = HomingMissileSprite.EraseSpriteFromPlayfield(Playfield)
    SpaceDotScore = SpaceDotScore + HomingMissilePoints



def HitPlayerShip(PlayerShip):
  if (PlayerShip.lives > 0):
    PlayerShip.lives = PlayerShip.lives - 1
    PlayerShip.exploding = 1

  else:
    PlayerShip.exploding = 1
    PlayerShip.alive     = 0
    #Playfield[Playership.v][Playership.h] = EmptyObject()
    


def HitGround(Ground):
  global SpaceDotScore

  h = Ground.h
  v = Ground.v

  #The ground is messed up.  Missiles hit it and the ground objects are getting overwritten with EmptyObject
  #because of this I am  just going to change the color of the ground but leave the pieces alive
  Ground.alive   = 1

  #if (Ground.lives > 0):
  #  Ground.lives = Ground.lives - 1
  Ground.r = Ground.r + DamageR
  Ground.g = Ground.g + DamageG
  Ground.b = Ground.b = 0

  if (Ground.r >= 255):
    Ground.r = 255
  if (Ground.g >= 150):
    Ground.g = 0


    
  Playfield[v][h].r = Ground.r
  Playfield[v][h].g = Ground.g
  Playfield[v][h].b = Ground.b

  #print("Ground hit hv:",Ground.h,Ground.v," rgb",Ground.r,Ground.g,Ground.b,' lives:',Ground.lives)

  #calculate score
  SpaceDotScore = SpaceDotScore - AsteroidLandedPoints



  return  


  
def AdjustSpeed(Ship,setting,amount):
  #print ("AS - BEFORE Ship.name Ship.speed setting amount",Ship.name, Ship.speed, setting,amount)
  if (setting == 'slow'):
    Ship.speed = Ship.speed + amount
  else:
    Ship.speed = Ship.speed - amount
  
  if (Ship.speed <= PlayerShipMinSpeed):
    Ship.speed = PlayerShipMinSpeed
  elif (Ship.speed >= 50):
    Ship.speed = 50   
  #print ("AS - AFTER Ship.name Ship.speed setting amount",Ship.name, Ship.speed, setting,amount)
  


 
def ShowExplosion(Explosion):

  h = Explosion.h 
  v = Explosion.v 
  #print("boom:",Explosion.currentframe,Explosion.name)
  
  Explosion.Display(h,v)
  #Explosion.currentframe = Explosion.currentframe + 1
  

def PointTowardsNearestAsteroid(Ship,Asteroids):
  h = Ship.h
  v = Ship.v
  nearest  = 0
  distance = 0
  shortest = LED.HatWidth

  for i in range (0,len(Asteroids)):
    if (Asteroids[i].alive == 1 and Asteroids[i].v > 0):
      distance = abs(h - Asteroids[i].h)
      if distance < shortest:
        shortest = distance
        nearest  = i

  if (nearest > 0):
    #print ("Nearst asteroid found.  Turning towards:",Wave.Asteroids[nearest].h)
    LED.PointTowardsObjectH(Ship,Asteroids[nearest])

  return

  
  
      
      

  
def MovePlayerShip(Ship, HomingMissileShip, Asteroids):
  global PlayerMissileCount

  #print ("moveship Direction HV:",Ship.name,Ship.direction,Ship.h,Ship.v)
  
  EnemyTargets = ['UFO','Asteroid','UFOMissile','BomberShip','HomingMissile','BomberRock']
  EnemyToFollow = ['UFO','BomberShip','HomingMissile']

  #Player ships always points up, enemy ships point down
  h = Ship.h
  v = Ship.v
  ItemList = []
  #Scan all around, make decision, move
  ItemList = ScanShip(Ship.h,Ship.v,Ship.scandirection)
  
  #these are special radar points to the left or right, above the player ship
  ItemsOnLeft  = [ItemList[11],ItemList[20],ItemList[33]]
  ItemsOnRight = [ItemList[13],ItemList[22],ItemList[35]]

  #Priority
  # 1 Evade close objects
  # 2 Blast far objects

  #If Enemy is detected, fire missile!
  if ( any(item in EnemyTargets for item in ItemList)):

    for i in range(0,PlayerMissileCount):
      if (PlayerMissiles[i].alive == 0 and PlayerMissiles[i].exploding == 0):
        #print ("MPS - UFO/Bomber/asteroid Detected PlayerMissile1.alive:",PlayerMissiles[i].alive)
        PlayerMissiles[i].h = h
        PlayerMissiles[i].v = v
        PlayerMissiles[i].alive = 1
        #PlayerMissiles[i].lives = 1
        PlayerMissiles[i].exploding = 0
        break  


  #Homing missile must be destroyed!  Follow and intercept
  if (HomingMissileShip.alive == 1 and HomingMissileShip.v <= SpaceDotMaxV -4):
    LED.PointTowardsObjectH(Ship,HomingMissileShip)
    AdjustSpeed(Ship,'fast',5)

  else:

    #Follow UFO
    #slow down if ahead of UFO, speed up if behind
    if ( any(item in EnemyToFollow for item in ItemsOnLeft)):
      
      #We are looking at the playfield to find the UFO or Bombership's direction
      #Look at top of screen
      if (Playfield[0][h-1].name in EnemyToFollow):
        Ship.direction = Playfield[0][h-1].direction

      #Look at middle of screen (according to scan area)
      elif (Playfield[LED.HatHeight-1][h-1].name in EnemyToFollow):
        Ship.direction = Playfield[LED.HatHeight-1][h-1].direction
      
      #print ("MPS - ENEMY TO LEFT Enemy.name HV direction",Playfield[h-1][0].name,Playfield[h-1][0].h,Playfield[h-1][0].v, Playfield[h-1][0].direction)
      if (Playfield[0][h-1].direction == 4 or
        Playfield[LED.HatHeight-1][h-1].direction == 4):
        AdjustSpeed(Ship,'fast',5)

      elif (Playfield[0][h-1].direction == 2 or
            Playfield[LED.HatHeight-1][h-1].direction == 2):
        AdjustSpeed(Ship,'slow',1)
      
    elif ( any(item in EnemyToFollow for item in ItemsOnRight)):
   
      #We are looking at the playfield to find the UFO or Bombership's direction
      #Look at top of screen
      if (Playfield[0][h+1].name in EnemyToFollow):
        Ship.direction = Playfield[0][h+1].direction

      #Look at middle of screen (according to scan area)
      elif (Playfield[LED.HatHeight-1][h+1].name in EnemyToFollow):
        Ship.direction = Playfield[LED.HatHeight-1][h+1].direction

      #print ("MPS - ENEMY TO RIGHT Enemy.name HV direction",Playfield[0][h+1].name,Playfield[0][h+1].h,Playfield[0][h+1].v, Playfield[0][h+1].direction)
      if (Playfield[0][h+1].direction == 2 or
          Playfield[LED.HatHeight-1][h+1].direction == 2):
        #print ("MPS - adjusting speed fast 3")
        AdjustSpeed(Ship,'fast',4)
      elif (Playfield[0][h+1].direction == 4 or
            Playfield[LED.HatHeight-1][h+1].direction == 4):
        #print ("MPS - adjusting speed slow 1")
        AdjustSpeed(Ship,'slow',1)

    #point towards asteroids
    else:
      m,r = divmod(moves,PlanetSurfaceSleep)  
      if (r == 0):
        PointTowardsNearestAsteroid(Ship,Asteroids)

      
  #print("MPS - 1Ship.direction: ",Ship.direction)
    
  
  #if heading to boundary or wall Reverse direction
  #print("checking border")
  if ((Ship.direction == 4 and ItemList[1] == 'border') or
      (Ship.direction == 2 and ItemList[5] == 'border')):
    Ship.direction = LED.ReverseDirection(Ship.direction)
    #print ("MPS - border detected, reversing direction")
    AdjustSpeed(Ship,'slow',1)
    #print("MPS - 2Ship.direction: ",Ship.direction)
  
  #Evade close objects
  # - if object in path of travel, reverse direction
  elif ((Ship.direction == 4 and (ItemList[1] != 'EmptyObject' or ItemList[2] != 'EmptyObject')) or
        (Ship.direction == 2 and (ItemList[5] != 'EmptyObject' or ItemList[4] != 'EmptyObject'))):      
    Ship.direction = LED.ReverseDirection(Ship.direction)
    #print("MPS - object in path, reversed direction")
    #print("MPS - 3Ship.direction: ",Ship.direction)
    

  # - speed up and move if object is directly above
  elif ((Ship.direction == 4 and (ItemList[3] != 'EmptyObject' and ItemList[1] == 'EmptyObject')) or
        (Ship.direction == 2 and (ItemList[3] != 'EmptyObject' and ItemList[5] == 'EmptyObject'))):
    AdjustSpeed(Ship,'fast',8)
    Ship.h, Ship.v =  LED.CalculateDotMovement(Ship.h,Ship.v,Ship.direction)
    #print("MPS - speeding up to avoid collision")
    #print("MPS - 4Ship.direction: ",Ship.direction)

  # - travelling left, move if empty
  # - travelling right, move if empty
  # - randomly switch directions
  elif ((ItemList[1] == 'EmptyObject' and Ship.direction == 4) or 
        (ItemList[5] == 'EmptyObject' and Ship.direction == 2 )):
    if ((random.randint(0,LED.HatWidth-1) <= 2) and Ship.h != 0 and Ship.h != LED.HatWidth-1):
      Ship.direction = LED.ReverseDirection(Ship.direction)
    Ship.h, Ship.v =  LED.CalculateDotMovement(Ship.h,Ship.v,Ship.direction)
    #print("MPS - Travelling, move if empty")
    #print("MPS - 5Ship.direction: ",Ship.direction)


  #if nothing nearby, and near the middle, stop moving
  if (all('EmptyObject' == Item for Item in ItemList)
      and Ship.h >= 6 and Ship.h <= 11):
    if (random.randint (0,2) == 1):
      #print ("MPS - Staying in the middle")
      Ship.h = h
      Ship.v = v
    
  #print("MPS - 6Ship.direction: ",Ship.direction)

  #print("MPS - OldHV: ",h,v, " NewHV: ",Ship.h,Ship.v, "direction: ",Ship.direction)
  if (Ship.h >= SpaceDotMaxH):
    Ship.h = SpaceDotMaxH
  if (Ship.v >= SpaceDotMaxV):
    Ship.v = SpaceDotMaxV
  Playfield[Ship.v][Ship.h]= Ship
  Ship.Display()
  
  if ((h != Ship.h or v != Ship.v) or
     (Ship.alive == 0)):
    Playfield[v][h] = Empty
    LED.setpixel(h,v,0,0,0)
    #print ("MPS - Erasing Player")
  #unicorn.show()

  #print ("Ship hv direction speed:",Ship.h,Ship.v,Ship.direction,Ship.speed)

  return 

  
def MoveEnemyShip(Ship):
  #print ("MES - moveship Direction HV:",Ship.name,Ship.direction,Ship.h,Ship.v)
  
  #Player ships always points up, enemy ships point down
  h = Ship.h
  v = Ship.v
  ItemList = []
  #Scan all around, make decision, move
  ItemList = ScanShip(Ship.h,Ship.v,Ship.scandirection)
  #print("MES - ItemList: ",ItemList)    
  #get possible items, then prioritize

  #Priority
  # 1 Shoot Player
  

  #If player is detected, fire missile!
  if ("Player1" in ItemList):
    if (UFOMissile1.alive == 0 and UFOMissile1.exploding == 0):
      UFOMissile1.h = h
      UFOMissile1.v = v
      UFOMissile1.alive = 1
    elif (UFOMissile2.alive == 0 and UFOMissile2.exploding == 0):
      UFOMissile2.h = h
      UFOMissile2.v = v
      UFOMissile2.alive = 1
    elif (UFOMissile3.alive == 0 and UFOMissile3.exploding == 0):
      UFOMissile3.h = h
      UFOMissile3.v = v
      UFOMissile3.alive = 1
    

  
  #UFO goes from one side to the other
  #print("checking border")
  if ((Ship.direction == 2 and ItemList[1] == 'border') or
      (Ship.direction == 4 and ItemList[5] == 'border')):
    #Ship.alive = 0
    Ship.v = Ship.v + 1
    if (Ship.v > SpaceDotMaxV-3):
      Ship.v = SpaceDotMaxV-3
    Ship.direction = LED.ReverseDirection(Ship.direction)
    Ship.h, Ship.v =  LED.CalculateDotMovement(Ship.h,Ship.v,Ship.direction)
    if (Ship.h == SpaceDotMaxH-2):
      Ship.h = SpaceDotMaxH-1
    elif (Ship.h == 1):
      Ship.h == 0
    
    #print ("MES - hit border, died")
  

  # - travelling left, move if empty
  # - travelling right, move if empty
  elif ((ItemList[5] == 'EmptyObject' and Ship.direction == 4) or 
        (ItemList[1] == 'EmptyObject' and Ship.direction == 2 )):
    Ship.h, Ship.v =  LED.CalculateDotMovement(Ship.h,Ship.v,Ship.direction)
    #print("MES - Travelling, move if empty")
      
      
  #print("OldHV: ",h,v, " NewHV: ",Ship.h,Ship.v)
  Playfield[Ship.v][Ship.h]= Ship
  Ship.Display()
  
  if ((h != Ship.h or v != Ship.v) or
     (Ship.alive == 0)):
    Playfield[v][h] = Empty
    LED.setpixel(h,v,0,0,0)
    #print ("MES - Erasing UFO")
  #unicorn.show()

  return 
  

#Enemy ship is the UFO
def MoveBomberShip(BomberShip,BomberSprite):
  #print ("MBS - Name Direction HV:",BomberShip.name,Ship.direction,Ship.h,Ship.v)
  
  #Player ships always points up, enemy ships point down
  h = BomberShip.h
  v = BomberShip.v
  ItemList = []
  #Scan all around, make decision, move
  ItemList = ScanBomberShip(BomberShip)
  
  #Priority
  # 1 Shoot Player
  
  #Bomber needs to be allowed to go off the screen
  
  
  #Bomber goes from one side to the other
  #print("checking border")
  if ((BomberShip.direction == 2 and ItemList[1] == 'border' and BomberShip.h > SpaceDotMinH+1)):
    BomberShip.v = BomberShip.v + 1
    BomberShip.direction = LED.ReverseDirection(BomberShip.direction)
  elif ((BomberShip.direction == 4 and ItemList[3] == 'border' and BomberShip.h < SpaceDotMaxH-2)):
    BomberShip.v = BomberShip.v + 1
    BomberShip.direction = LED.ReverseDirection(BomberShip.direction)

  BomberShip.h, BomberShip.v =  LED.CalculateDotMovement(BomberShip.h,BomberShip.v,BomberShip.direction)
  
  # - travelling left, move if empty
  # - travelling right, move if empty
  if ((ItemList[3] == 'EmptyObject' and BomberShip.direction == 4) or 
     (ItemList[1] == 'EmptyObject' and BomberShip.direction == 2 )):
    BomberShip.h, BomberShip.v =  LED.CalculateDotMovement(BomberShip.h,BomberShip.v,BomberShip.direction)
    #print("MES - Travelling, move if empty")

  return 


def MoveHomingMissile(HomingMissileShip,HomingMissileSprite,PlayerShip):
  #Scan all around, make decision, move
  distance = 0
  ItemList = []
  h        = HomingMissileShip.h
  v        = HomingMissileShip.v
  OldH     = HomingMissileShip.h
  OldV     = HomingMissileShip.v
  HomingMissileShip.direction = LED.PointTowardsObject8Way(h,v,PlayerShip.h,PlayerShip.v)
  ItemList = ScanAroundShip(h,v,HomingMissileShip.direction)
  
  


  # - travelling left, move if empty
  # - travelling right, move if empty

  #print(ItemList)
  #only move if a spot is empty
  if (ItemList[1] == 'EmptyObject' or ItemList[1] == 'HomingMissile'):
    #print("spot empty, moving homingmissile")

    #Calculate new position
    h, v = LED.CalculateDotMovement8Way(h,v,HomingMissileShip.direction)

    #we want to slow down the vertical descent
    if (random.randint(1,HomingMissileDescentChance) == HomingMissileDescentChance):
      HomingMissileShip.h = h
      HomingMissileShip.v = OldV
    else:
      HomingMissileShip.h = h  
      HomingMissileShip.v = v

    #don't go down too far
    if HomingMissileShip.v > SpaceDotMaxV -1:
      HomingMissileShip.v = HomingMissileShip.v -1

  #print (ItemList)
  distance = LED.GetDistanceBetweenDots(HomingMissileShip.h,HomingMissileShip.v,PlayerShip.h,PlayerShip.v)
  #print("Player 1 detected distance: ",distance)
  if(distance <= 4):
    HitPlayerShip(PlayerShip)  
    HomingMissileShip.exploding = 1
    #HomingMissileShip.alive     = 0
    #PlayerShip.Alive            = 0
    PlayerShip.Exploding        = 1

  HomingMissileSprite.h = HomingMissileShip.h
  HomingMissileSprite.v = HomingMissileShip.v

  return 
  

  
  

def MoveMissile(Missile):
  #player and UFO shots, even asteroids are treated as "missiles"
  #they move in a straight line and blow up when they hit something
  global Empty
  global SpaceDotScore
  
  #Record the current coordinates
  h = Missile.h
  v = Missile.v

  
  RegularTargets = ['Player1','UFO','UFOMissile','Asteroid','Wall','BomberRock']
  
  #Missiles simply drop to bottom and kablamo!
  #FF (one square in front of missile direction of travel)
  ScanH, ScanV = LED.CalculateDotMovement(h,v,Missile.scandirection)
  Item = ScanSpaceDot(ScanH,ScanV)
  
  

  #Priority
  # 1 Hit target
  # 2 See if we are hit by enemy missle
  # 3 Move forward




  #if(ScanV == GroundV):
    #print ('missile at ground.  name:',Missile.name,' item:',Item,ScanH,ScanV)
    #LED.FlashDot(ScanH,ScanV,0.05)
  
  #BomberShip is special
  if (Item == 'BomberShip' and Missile.name != 'BomberRock'):
    #print ("MM - Playfield - BEFORE Bomberhit",Playfield[ScanV][ScanH].name)
    HitBomber(Playfield[ScanV][ScanH])  
    #print ("MM - Playfield - AFTER Bomberhit",Playfield[ScanV][ScanH].name)
    Missile.h = ScanH
    Missile.v = ScanV
    #Playfield[Missile.h][Missile.v] = Missile
    Missile.Display()
    Missile.exploding = 1
    Missile.alive = 0
    

  #HomingMissile is special
  elif (Item == 'HomingMissile' and Missile.name != 'Asteroid'):
    HitHomingMissile(Playfield[ScanV][ScanH],HomingMissileSprite)  
    Missile.h = ScanH
    Missile.v = ScanV
    Missile.Display()
    Missile.exploding = 1
    Missile.alive = 0



  #Playership is special
  elif (Item == 'Player1'):
    HitPlayerShip(Playfield[ScanV][ScanH])  
    Missile.h = ScanH
    Missile.v = ScanV
    Missile.Display()
    Missile.exploding = 1
    Missile.alive = 0


  elif(Item == 'Asteroid' and Missile.name != 'Asteroid'):
    #print('Adding points:',SpaceDotScore,AsteroidPoints)
    SpaceDotScore = SpaceDotScore + AsteroidPoints


  #Ground is special too.  See the pattern yet?
  if (Item == 'Ground'):
    #print ("item is the ground")
    HitGround(Playfield[ScanV][ScanH])  
    Missile.h = -1
    Missile.v = -1
    Missile.exploding = 1
    #Missile.alive = 0
    if(Missile.name == 'Asteroid' or Missile.name == 'UFOMissile'):
      Missile.Explosion.h = ScanH
      Missile.Explosion.v = ScanV
    else:
      #center the big explosion
      Missile.Explosion.h = ScanH - (Missile.Explosion.width / 2) + 1
      Missile.Explosion.v = ScanV - 2

    Playfield[v][h] = Empty
    #Missile.Display()
    Missile.Explosion.DisplayAnimated()
    LED.setpixel(h,v,0,0,0)
    return

  #See if other target ship is hit
  #try not to let asteroids blow each other up
  elif (Item  in RegularTargets and Missile.name != Playfield[ScanV][ScanH].name):
    #target hit, kill target

    Playfield[ScanV][ScanH].alive = 0
    Playfield[ScanV][ScanH].lives = Playfield[ScanV][ScanH].lives -1
    Playfield[ScanV][ScanH]= Empty
    LED.setpixel(ScanH,ScanV,0,0,0)
    LED.setpixel(h,v,0,0,0)

    Missile.h = ScanH
    Missile.v = ScanV
    #Playfield[Missile.h][Missile.v] = Missile
    Missile.Display()
    Missile.exploding = 1
    Missile.alive = 0
    Missile.lives = Missile.lives - 1
  
#  elif (Item  == 'PlayerMissile'):
#    #We are hit
#    Missile.Alive = 0
#    Missile.exploding = 1
#    Playfield[ScanV][ScanH].alive = 0
#    Playfield[ScanV][ScanH]= Empty
#    Missile.Erase()
#    print ("MM - We have been  hit!")
  
  #Player missiles fire off into space
  #Enemy missiles explode on ground
  
  elif (Item == 'aboveborder' and Missile.name == 'Asteroid'):
    #print ("asteroid above border")
    Missile.h = ScanH
    Missile.v = ScanV
    Playfield[Missile.v][Missile.h] = Missile
    

  elif (Item == 'aboveborder' and Missile.name == 'PlayerMissile'):
    #print ("MM - Missile hit border")
    Missile.alive  = 0
    Missile.lives  = Missile.lives - 1
    Missile.exploding = 0
    Missile.Erase()
  elif (Item == 'border' and (Missile.name == 'UFOMissile' or Missile.name == 'Asteroid' or Missile.name == 'BomberRock')
                         and not(Missile.name == 'Asteroid' and Missile.v <= 0)):


    #print ("MM - Missile hit border")
    Missile.alive = 0
    Missile.lives = Missile.lives - 1
    Missile.exploding = 1
    Missile.Erase()
    #print ("MM - UFO hit border HV:",Missile.h,Missile.v)
    
  #empty = move forward
  elif (Item == 'EmptyObject' and Missile.alive == 1):
    Missile.h = ScanH
    Missile.v = ScanV
    Playfield[Missile.v][Missile.h] = Missile
    Missile.Display()
    #print ("MM - empty, moving forward")
    


  if ((h != Missile.h or v != Missile.v) or (Missile.alive == 0)):
    
    if (Playfield[v][h].name != 'Ground'):
      Playfield[v][h] = Empty
      LED.setpixel(h,v,0,0,0)
  
  return 






def ShowFireworks(FireworksExplosion,count,speed):
  x = 0
  h = 0
  v = 0

  #FireworksExplosion  = copy.deepcopy(LED.PlayerShipExplosion)  
  
  for x in range(1,count):
    h = random.randint(2,LED.HatWidth)
    v = random.randint(2,LED.HatHeight / 2)
    FireworksExplosion.Animate(h,v,'forward',speed,StartFrame = 1) 
    FireworksExplosion.EraseLocation(h,v)       





def ExplodeGround(count,speed):
  x = 0
  h = 0
  v = GroundV
  
  GroundExplosion = []
  GroundExplosion.append(LED.BigShipExplosion)
  GroundExplosion.append(LED.PlayerShipExplosion)
  GroundExplosion.append(LED.BomberShipExplosion)

  
  for x in range(1,count):
    h = random.randint(SpaceDotMinH,SpaceDotMaxH)
    i = random.randint(0,2)
    GroundExplosion[i].Animate(h,v,'forward',speed,StartFrame = 1) 
    #GroundExplosion[i].EraseLocation(h,v)       





def RedrawGround(TheGround):
  GroundCount = 0
  for i in range (SpaceDotMinH,SpaceDotMaxH):
    Playfield[GroundV][i] = TheGround[GroundCount]
    if(Playfield[GroundV][i].r < 255):
      Playfield[GroundV][i].Display()
    GroundCount = GroundCount + 1
  return


def CheckGroundDamage(TheGround):
  global PlayerShip
  
  DamageCount = 0
  for i in range (SpaceDotMinH,SpaceDotMaxH):
    if (Playfield[GroundV][i].r == 255):
      DamageCount = DamageCount + 1
      #print ("Ground Damage:",DamageCount)

  if(DamageCount >= GroundDamageLimit):
    print ("*** PLANET CRUST DESTROYED ***")
    ExplodeGround(GroundExplosions,0.01)
    PlayerShip.alive = 0
    PlayerShip.lives = 0
  return




def CenterSpriteOnShip(Sprite,Ship):
  Sprite.h = Ship.h - (Sprite.width // 2)
  Sprite.v = Ship.v - (Sprite.height // 2)






  
def PlaySpaceDot(Duration = 5,StopEvent=None):
   
  global PlayerShip
  global EnemyShip
  global BomberShip
  global PlayerShipSpeed
  global Playfield
  global PlayerMissiles
  global PlayerMissileCount
  global MaxPlayerMissiles
  global PlayerMissileSpeed
  global PlayerShipMinSpeed
  global PlayerShipMaxSpeed
  global AsteroidMinSpeed
  global AsteroidMaxSpeed
  global HomingMissileSpriteList
  global HomingMissileSprite

  global SpaceDotMinH
  global SpaceDotMaxH
  global SpaceDotMinV
  global SpaceDotMaxV
  global SpaceDotScore
  

  LED.ClearBigLED()
  SpaceDotScore = 0
  
  #Local variables
  moves       = 0
  Finished    = 'N'
  LevelCount  = 3
  Playerh     = 0
  Playerv     = 0
  SleepTime   = MainSleep / 4
  
  

  #Timers / Clock display
  ClockSprite = LED.CreateClockSprite(12)
  #lockH        = LED.HatWidth  // 2 - (ClockSprite.width // 2)
  #lockV        = LED.HatHeight // 2 - (ClockSprite.height // 2)
  start_time    = time.time()
  DayOfWeekSprite     = LED.CreateDayOfWeekSprite()
  MonthSprite         = LED.CreateMonthSprite()
  DayOfMonthSprite    = LED.CreateDayOfMonthSprite()
  
  



  
  
  
  CenterSpriteOnShip(HomingMissileShipExplosion,HomingMissileShip)
  #HomingMissileShipExplosion.h  = -1
  #HomingMissileShipExplosion.v  = -1
  HomingOldH = -1
  HomingOldV = -1
  #PlayerMissile1Explosion = copy.deepcopy(SmallExplosion)
  #PlayerMissile2Explosion = copy.deepcopy(SmallExplosion)




  #Tracking moves between waves
  MovesSinceWaveStop  = 0
  WaveAlive           = 1
  AsteroidsAlive      = 0

  #Make wave of asteroids
  Wave = AsteroidWave(AsteroidsInWaveMin)
  







  #Reset Playfield
  for x in range (0,LED.HatWidth):
    for y in range (0,LED.HatHeight):
      #print ("XY",x,y)
      Playfield[y][x] = Empty
               
  Playfield[PlayerShip.v][PlayerShip.h] = PlayerShip




  #Title
  #LED.ShowScrollingBanner2("SpaceDot",(LED.MedOrange),ScrollSleep)

  #Animation Sequence
  #ShowBigShipTime(ScrollSleep)  

  #Title
  LED.TheMatrix.Clear()
  LED.ClearBuffers()


  #Draw the Big text
  #Clear only the LED matrix
  #Draw the next size down
  #When at the final zoom level
  #  - clear the LED Matrix
  #  - clear all buffers (canvas and ScreenArray[V][H])
  #  - draw the text at desired last zoom level
  #  - draw the rest of the text, at this point it is all written to ArrayBuffer
  #  - clear the LED Matrix
  #  - clear all buffers (canvas and ScreenArray[V][H])
  #Call the ZoomScreen function to redraw the display using ScreenArray[V][H] which at this point
  #contains the values last written to the screen.


  #LED.ShowGlowingText(CenterHoriz = True,h = -8,v = 0,   Text = 'ASTRO', RGB = LED.MedGreen,  ShadowRGB = LED.ShadowGreen, ZoomFactor = 8,GlowLevels=0,DropShadow=False)
  #LED.TheMatrix.Clear()
  #LED.ShowGlowingText(CenterHoriz = True,h = -8,v = 0,   Text = 'ASTRO', RGB = LED.MedGreen, ShadowRGB = LED.ShadowGreen, ZoomFactor = 7,GlowLevels=0,DropShadow=False)
  #LED.TheMatrix.Clear()
  #LED.ShowGlowingText(CenterHoriz = True,h = -8,v = 0,   Text = 'ASTRO', RGB = LED.MedGreen, ShadowRGB = LED.ShadowGreen, ZoomFactor = 6,GlowLevels=0,DropShadow=False)
  #LED.TheMatrix.Clear()
  #LED.ShowGlowingText(CenterHoriz = True,h = -8,v = 0,   Text = 'ASTRO', RGB = LED.MedGreen, ShadowRGB = LED.ShadowGreen, ZoomFactor = 5,GlowLevels=0,DropShadow=False)
  #LED.TheMatrix.Clear()
  #LED.ShowGlowingText(CenterHoriz = True,h = -8,v = 0,   Text = 'ASTRO', RGB = LED.MedGreen, ShadowRGB = LED.ShadowGreen, ZoomFactor = 4,GlowLevels=0,DropShadow=False)
  #LED.TheMatrix.Clear()
  #LED.ShowGlowingText(CenterHoriz = True,h = -8,v = 0,   Text = 'ASTRO', RGB = LED.MedGreen, ShadowRGB = LED.ShadowGreen, ZoomFactor = 3,GlowLevels=0,DropShadow=False)

  #LED.TheMatrix.Clear()
  #LED.ClearBuffers()
  #LED.ShowGlowingText(CenterHoriz = True,h = -8,v = 0,   Text = 'ASTRO',      RGB = LED.HighGreen,  ShadowRGB = LED.ShadowGreen,  ZoomFactor = 2,GlowLevels=200,DropShadow=False)
  #LED.ShowGlowingText(CenterHoriz = True,h = 0 ,v = 12,  Text = 'SMASH!',     RGB = (255,0,0),     ShadowRGB = LED.ShadowRed,    ZoomFactor = 2,GlowLevels=50,DropShadow=True)
  #RGB = LED.BrightColorList[random.randint(1,LED.BrightColorCount)]
  #Message = LED.TronGetRandomMessage(MessageType = 'SHORTGAME')
  
  
  BrightRGB, ShadowRGB = LED.GetBrightAndShadowRGB()
    
  #LED.ShowGlowingText(CenterHoriz = True,h = 0 ,v = 26,  Text = Message, RGB = BrightRGB,  ShadowRGB = ShadowRGB,  ZoomFactor = 1,GlowLevels=200,DropShadow=True,FadeLevels=200)
  #time.sleep(1)
  #LED.TheMatrix.Clear()
  #LED.Canvas.Clear()
  #LED.ZoomScreen(LED.ScreenArray,32,128,0)
  #LED.ZoomScreen(LED.ScreenArray,128,1,0,Fade=True)
  



  #Show clock
  #LED.CheckClockTimer(ClockSprite)
  LED.CopySpriteToPixelsZoom(ClockSprite,      ClockH,      ClockV,      ClockRGB,       SpriteFillerRGB,1)
  LED.CopySpriteToPixelsZoom(DayOfWeekSprite,  DayOfWeekH,  DayOfWeekV,  DayOfWeekRGB,   SpriteFillerRGB,1)
  LED.CopySpriteToPixelsZoom(MonthSprite,      MonthH,      MonthV,      MonthRGB,       SpriteFillerRGB,1)
  LED.CopySpriteToPixelsZoom(DayOfMonthSprite, DayOfMonthH, DayOfMonthV, DayOfMonthRGB,  SpriteFillerRGB,1)


  LED.SpaceDotGamesPlayed = LED.SpaceDotGamesPlayed + 1
  
  

  while (LevelCount > 0):
    #print ("show playership")
    
    #print ("Show level")

    #LED.ShowLevelCount(LevelCount)
    LevelCount = LevelCount - 1
    
    
    #Reset Variables between rounds
    LevelFinished        = 'N'
    moves                = 1
    PlayerShip.alive     = 1
    PlayerShip.exploding = 0
    PlayerShip.speed     = PlayerShipSpeed
    PlayerShip.h         = random.randint (SpaceDotMinH,SpaceDotMaxH)
    PlayerShip.Explosion.alive = 0

    if (random.randint(0,2) == 1):
      PlayerShip.direction = 2
    else:
      PlayerShip.direction = 4
    EnemyShip.alive   = 0
    UFOMissile1.alive = 0
    UFOMissile2.alive = 0
    UFOMissile3.alive = 0
    UFOMissile1.h     = -1
    UFOMissile2.v     = -1
    UFOMissile2.h     = -1
    UFOMissile2.v     = -1
    UFOMissile3.h     = -1
    UFOMissile3.v     = -1


    EnemyShip.speed   = random.randint (UFOShipMinSpeed,UFOShipMaxSpeed)
    
    #Reset colors
    UFOMissile1.r = PlayerMissileR
    UFOMissile1.g = PlayerMissileG
    UFOMissile1.b = PlayerMissileB
    UFOMissile2.r = PlayerMissileR
    UFOMissile2.g = PlayerMissileG
    UFOMissile2.b = PlayerMissileB
    UFOMissile3.r = PlayerMissileR
    UFOMissile3.g = PlayerMissileG
    UFOMissile3.b = PlayerMissileB
    BomberShip.alive = 0
    BomberShip.lives = BomberShipLives
    HomingMissileShip.alive = 0
    HomingMissileShip.lives = HomingMissileLives
    

    #Make a wave of asteroids
    
    Wave = AsteroidWave(AsteroidsInWaveMin)
    Wave.CreateAsteroidWave()
    LED.DisplayLevel(Wave.WaveCount,LED.MedBlue)
    

    
    #Reset Playfield
    for x in range (0,LED.HatWidth):
      for y in range (0,LED.HatHeight):
        #print ("XY",x,y)
        Playfield[y][x] = Empty
                 
    Playfield[PlayerShip.v][PlayerShip.h] = PlayerShip

    
    
    #Draw the ground
    color = random.randint(1,7) * 4 + 1
    r,g,b = LED.ColorList[color]    
    TheGround   = []    
    GroundCount = 0
    for i in range (SpaceDotMinH,SpaceDotMaxH):
      TheGround.append(LED.Ship(i,GroundV,r,g,b,0,0,0,1,SpaceDotGroundLives,'Ground', 0,0))
      Playfield[GroundV][i] = TheGround[GroundCount]
      Playfield[GroundV][i].Display()
      LED.FlashDot2(i,GroundV,0.02)
      #print("Ground:",i,GroundV)
      GroundCount = GroundCount + 1





    
    # Main timing loop
    while (LevelFinished == 'N' and PlayerShip.alive == 1 ):
      moves = moves + 1

      if StopEvent and StopEvent.is_set():
        print("\n" + "="*40)
        print("[SpaceDot] StopEvent received")
        print("-> Shutting down gracefully...")
        print("="*40 + "\n")
        LevelFinished = 'Y'
        PlayerShip.alive = 0
        break


      #check the time once in a while
      if(random.randint(0,1000) == 1):
        if (ClockSprite.hhmm != datetime.now().strftime('%H:%M')):
          ClockSprite   = LED.CreateClockSprite(24)
          ClockSprite.h = (LED.HatWidth - ClockSprite.width -2)
          ClockSprite.v = 0
          ClockSprite.rgb = ClockRGB

          #Background = LED.CopySpriteToLayerZoom(ClockSprite,bx + 30,10,(5,0,5),(0,5,0),2,False,Layer=Background)



        #End game after X seconds
        h,m,s    = LED.GetElapsedTime(start_time,time.time())
        #print("Elapsed Time:  mm:ss",m,s)

        if(m > Duration):
          LED.SaveConfigData()
          print("Ending game after",m," minutes")

          LED.ClearBigLED()
          LED.ClearBuffers()
          CursorH = 0
          CursorV = 0
          LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"ALIEN ATTACK HAS BEEN DEFLECTED",CursorH=CursorH,CursorV=CursorV,MessageRGB=(150,0,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalTypeSpeed)
          LED.BlinkCursor(CursorH= CursorH,CursorV=CursorV,CursorRGB=CursorRGB,CursorDarkRGB=CursorDarkRGB,BlinkSpeed=0.5,BlinkCount=2)
          LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"FOR NOW...",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)
          LED.BlinkCursor(CursorH= CursorH,CursorV=CursorV,CursorRGB=CursorRGB,CursorDarkRGB=CursorDarkRGB,BlinkSpeed=0.5,BlinkCount=2)
          
          return();










      #Draw bottom background
      m,r = divmod(moves,PlanetSurfaceSleep)  
      if (r == 0):
        RedrawGround(TheGround)
        CheckGroundDamage(TheGround)



      #Cleanup debris (leftover pixels from explosions)
      m,r = divmod(moves,DebrisCleanupSleep)
      if (r == 0):
        CleanupDebris(SpaceDotMinH,SpaceDotMaxH,SpaceDotMinV,SpaceDotMaxV,Playfield)

     

      #Check for keyboard input
      #m,r = divmod(moves,LED.KeyboardSpeed)
      #if (r == 0):
      #  Key = LED.PollKeyboard()
      #  LED.ProcessKeypress(Key)
      #  if (Key == 'Q' or Key == 'q'):
      #    LevelCount = 0
      #    return
      #  elif (Key == 'd'):
      #    LED.DebugPlayfield(Playfield,LED.HatWidth,LED.HatHeight)
      #    for i in range (0,PlayerMissileCount):
      #      print("Name HV Alive Exploding Speed:",PlayerMissiles[i].name,PlayerMissiles[i].h,PlayerMissiles[i].v,PlayerMissiles[i].alive,PlayerMissiles[i].exploding,PlayerMissiles[i].speed)
      #    time.sleep(2)
      #
      #  elif (Key == 'n'):
      #    Playfield               = HomingMissileSprite.EraseSpriteFromPlayfield(Playfield)
      #    HomingMissileSprite     = HomingMissileSpriteList[random.randint(0,HomingMissileSprites -1 )]
      #    HomingMissileShip.h     = 32
      #    HomingMissileShip.v     = 0
      #    HomingMissileShip.lives = HomingMissileLives
      #    HomingMissileShip.alive = 1
      #    HomingMissileSprite.v   = 0
      #    HomingMissileSprite.framerate = HomingMissileFrameRate
      #    HomingMissileShip.speed = HomingMissileInitialSpeed
                         

      
#      print ("=================================================")
#      for H in range(0,LED.HatWidth-1):
#        for V in range (0,LED.HatWidth-1):
#          if (Playfield[v][h].name != 'EmptyObject'):
#            print ("Playfield: HV Name",H,V,Playfield[v][h].name)
#      print ("=================================================")
      


      m,r = divmod(moves,CheckClockSpeed)
      if (r == 0):  
        #CheckClockTimer(ClockSprite)
        TheTime = LED.CreateClockSprite(12)

        #Show Custom sprites
        LED.CopySpriteToPixelsZoom(ClockSprite,      ClockH,      ClockV,      ClockRGB,       SpriteFillerRGB,1)
        LED.CopySpriteToPixelsZoom(DayOfWeekSprite,  DayOfWeekH,  DayOfWeekV,  DayOfWeekRGB,   SpriteFillerRGB,1)
        LED.CopySpriteToPixelsZoom(MonthSprite,      MonthH,      MonthV,      MonthRGB,       SpriteFillerRGB,1)
        LED.CopySpriteToPixelsZoom(DayOfMonthSprite, DayOfMonthH, DayOfMonthV, DayOfMonthRGB,  SpriteFillerRGB,1)
 






      
      if (PlayerShip.alive == 1):
        #print ("M - Playership HV speed alive exploding direction: ",PlayerShip.h, PlayerShip.v,PlayerShip.speed, PlayerShip.alive, PlayerShip.exploding, PlayerShip.direction)
        #print ("M - moves: ", moves)        
        m,r = divmod(moves,PlayerShip.speed)
        if (r == 0):
          MovePlayerShip(PlayerShip,HomingMissileShip,Wave.Asteroids)
          i = random.randint(0,2)
          if (i >= 0):
            AdjustSpeed(PlayerShip,'fast',1)
            
      
      if (EnemyShip.alive == 1):
        m,r = divmod(moves,EnemyShip.speed)
        if (r == 0):
          MoveEnemyShip(EnemyShip)
          


      #print ("M - Bombership Alive Lives HV:",BomberShip.alive, BomberShip.lives,BomberShip.h,BomberShip.v)
      if (BomberShip.alive == 1):
        m,r = divmod(moves,BomberShip.speed)
        if (r == 0):
          if (BomberShip.v == SpaceDotMaxV):
            BomberShip.v = 0
          BomberOldH = BomberShip.h
          BomberOldV = BomberShip.v
          MoveBomberShip(BomberShip,BomberSprite)
          Playfield = BomberSprite.EraseSpriteFromPlayfield(Playfield)
          Playfield = BomberSprite.CopyAnimatedSpriteToPlayfield(Playfield,BomberShip)

          
        CenterSpriteOnShip(BomberSprite,BomberShip) 
        BomberSprite.DisplayAnimated()





          
      #print ("M - Homingship Alive Lives HV:",HomingShip.alive, HomingShip.lives,HomingShip.h,HomingShip.v)
      if (HomingMissileShip.alive == 1):
        m,r = divmod(moves,HomingMissileShip.speed)
        if (r == 0):
            
          #LED.CenterSpriteOnShip(HomingMissileSprite,HomingMissileShip)
          #HomingOldH = HomingMissileShip.h
          #HomingOldV = HomingMissileShip.v

          #Need to erase old position, and draw new position to playfield
          #HomingMissileSprite.h = HomingOldH
          #HomingMissileSprite.v = HomingOldV
        
          Playfield = HomingMissileSprite.EraseSpriteFromPlayfield(Playfield)
          MoveHomingMissile(HomingMissileShip,HomingMissileSprite,PlayerShip)
          CenterSpriteOnShip(HomingMissileSprite,HomingMissileShip)
          Playfield = HomingMissileSprite.CopyAnimatedSpriteToPlayfield(Playfield,HomingMissileShip)
          
          

        #even if we don't move, we still animate the sprite
        if(HomingMissileShip.alive == 1):
          HomingMissileSprite.DisplayAnimated(HomingMissileSprite.h,HomingMissileSprite.v)
        

          
      if (UFOMissile1.alive == 1 and UFOMissile1.exploding == 0):
        m,r = divmod(moves,UFOMissile1.speed)
        if (r == 0):
          MoveMissile(UFOMissile1)

      if (UFOMissile2.alive == 1 and UFOMissile2.exploding == 0):
        m,r = divmod(moves,UFOMissile2.speed)
        if (r == 0):
          MoveMissile(UFOMissile2)

      if (UFOMissile3.alive == 1 and UFOMissile3.exploding == 0):
        m,r = divmod(moves,UFOMissile3.speed)
        if (r == 0):
          MoveMissile(UFOMissile3)

          

      #Check all player missiles
      for i in range (0,PlayerMissileCount):
        #print ("Checking player missile:",i)

        #check for buggy missiles tLED.Hat have gone out of range
        #this check should be removed once we determine why someitmes missile.h = 24
        if(PlayerMissiles[i].h < SpaceDotMinH and PlayerMissiles[i].h >= 0):
          PlayerMissiles[i].alive = 0
          PlayerMissiles[i].exploding = 0

        if (PlayerMissiles[i].alive == 1 and PlayerMissiles[i].exploding == 0):
          m,r = divmod(moves,PlayerMissiles[i].speed)
          if (r == 0):
            MoveMissile(PlayerMissiles[i])
        if (PlayerMissiles[i].v <= -1):
          PlayerMissiles[i].alive = 0
          PlayerMissiles[i].exploding = 0
         
      



      #Spawn asteroids or move asteroids (asteroids are treated as missiles)
      if (Wave.Alive  == True):
        #print("moves:",moves,end='\r', flush=True)
        m,r = divmod(moves,WaveDropSpeed)
        if (r == 0):
          Wave.UpdateCounts()
          Wave.DropAsteroids((random.randint(AsteroidsToDropMin,AsteroidsToDropMax)),Playfield)

          
        #Move asteroids tLED.Hat are alive
        for i in range (0,Wave.AsteroidCount): 

          #if asteroid is alive move it
          if (Wave.Asteroids[i].alive == 1):
            #print ("Asteroid alive moves speed hv:",moves,Wave.Asteroids[i].speed, Wave.Asteroids[i].h,Wave.Asteroids[i].v)

            m,r = divmod(moves,Wave.Asteroids[i].speed)
            if (r == 0):
              #print("Moving alive asteroid:",Wave.Asteroids[i].h,Wave.Asteroids[i].v)
              MoveMissile(Wave.Asteroids[i])
              Wave.Asteroids[i].Display()


            
        

        

        
            
          

      #Spawn enemy ship UFO
      m,r = divmod(moves,ChanceOfUFO)
      if (r == 0 and EnemyShip.alive == 0):
        #print ("Spawning UFO")
        EnemyShip.alive = 1
        EnemyShip.lives = UFOLives
        EnemyShip.direction = LED.ReverseDirection(EnemyShip.direction)
        if (EnemyShip.direction == 2):
          EnemyShip.h = SpaceDotMinH
          EnemyShip.v = SpaceDotMinV
          #EnemyShip.v = random.randint(0,4)
        else:
          EnemyShip.h = SpaceDotMaxH
          EnemyShip.v = SpaceDotMinV
        EnemyShip.Display()


        

      #Spawn BomberShip
      if (Wave.WaveCount >= MinBomberWave):

        m,r = divmod(moves,ChanceOfBomberShip)
        if (r == 0 and BomberShip.alive == 0):
          #print ("Spawning BomberShip")
          BomberShip.alive = 1
          BomberShip.lives = 3 #(takes 3 hits to die)
          BomberShip.direction = LED.ReverseDirection(BomberShip.direction)
          if (BomberShip.direction == 2):
            BomberShip.h = SpaceDotMinH-2
            BomberShip.v = SpaceDotMinV
            Playfield[SpaceDotMinV][SpaceDotMinH] = BomberShip
          else:
            BomberShip.h = LED.HatWidth
            BomberShip.v = 0
            Playfield[SpaceDotMinV][SpaceDotMaxH] = BomberShip

        #Bombership drops a red asteroid (#4)
        if (BomberShip.h >= SpaceDotMinH +3 and BomberShip.h <= SpaceDotMaxH -3 and BomberRock.alive == 0 and BomberShip.lives <=2 and BomberShip.alive == 1):
          BomberRock.alive = 1
          BomberRock.speed = BomberRockSpeed
          BomberRock.h     = BomberShip.h 
          BomberRock.v     = BomberShip.v +1
          


        
      #move BomberRock
      if (BomberRock.alive == 1 and BomberRock.exploding == 0):
        m,r = divmod(moves,BomberRock.speed)
        if (r == 0):
          MoveMissile(BomberRock)


      
        
          
      #Spawn Homing missile
      if (Wave.WaveCount >= MinHomingMissileWave):
        m,r = divmod(moves,ChanceOfHomingMissile)
        if (r == 0 and HomingMissileShip.alive == 0):

          HomingMissileSprite   = HomingMissileSpriteList[random.randint(0,HomingMissileSprites -1)]
          HomingMissileShip.alive = 1
          HomingMissileShip.lives = HomingMissileLives
          MissileSpawned = False
          while (MissileSpawned == False):
            h = random.randint(SpaceDotMinH,SpaceDotMaxH)
            v = SpaceDotMinV 
            if (Playfield[v][h].name == 'EmptyObject'):
              HomingMissileShip.h = h
              HomingMissileShip.v = v
              Playfield[v][h] = HomingMissileShip
              HomingMissileShip.speed = HomingMissileInitialSpeed
              MissileSpawned = True
              CenterSpriteOnShip(HomingMissileSprite,HomingMissileShip)
        

      
          
      


     
      #-----------------------------
      # Check for exploding objects
      #-----------------------------

      #player missiles
      for i in range (0,PlayerMissileCount):
        if (PlayerMissiles[i].exploding == 1):
          #print("------> PlayerMissile1.exploding: ",PlayerMissile1.exploding)
          PlayerMissiles[i].Explosion.h = PlayerMissiles[i].h
          PlayerMissiles[i].Explosion.v = PlayerMissiles[i].v
          PlayerMissiles[i].Explosion.DisplayAnimated()
          
        #Kill missile after explosion animation is complete
        if (PlayerMissiles[i].Explosion.currentframe >= PlayerMissiles[i].Explosion.frames):
          #print ("killing missile")
          PlayerMissiles[i].Explosion.currentframe = 0
          PlayerMissiles[i].Explosion.exploding    = 0
          PlayerMissiles[i].Explosion.alive        = 0
          
          PlayerMissiles[i].exploding = 0
          PlayerMissiles[i].alive = 0
          
        
      #Asteroids
      for i in range(0,Wave.AsteroidCount):
        if (Wave.Asteroids[i].exploding == 1 ):
          if (Wave.Asteroids[i].Explosion.h == -1):
            Wave.Asteroids[i].Explosion.h    = Wave.Asteroids[i].h-1
            Wave.Asteroids[i].Explosion.v    = Wave.Asteroids[i].v-1
          Wave.Asteroids[i].Explosion.DisplayAnimated()
         
        #Kill asteroids after explosion animation is complete 
        #AND replace the ground object on the playfield
        if (Wave.Asteroids[i].Explosion.currentframe >= Wave.Asteroids[i].Explosion.frames):

          Wave.Asteroids[i].Explosion.h            = -1
          Wave.Asteroids[i].Explosion.v            = -1
          Wave.Asteroids[i].Explosion.currentframe = 1
          Wave.Asteroids[i].Explosion.exploding    = 0
          Wave.Asteroids[i].Explosion.alive        = 0
          Wave.Asteroids[i].alive = 0
          Wave.Asteroids[i].exploding = 0

          Wave.Asteroids[i].h                      = -1
          Wave.Asteroids[i].v                      = -1
          
          
          
          #this is broken
          #Playfield[Wave.Asteroids[i].v][Wave.Asteroids[i].h] = TheGround[i]

#handle points somewhere else.


      #BomberRock
      if (BomberRock.exploding == 1 ):

        if (BomberRock.Explosion.h == -1):
          BomberRock.Explosion.h = BomberRock.h -2
          BomberRock.Explosion.v = BomberRock.v -2

        BomberRock.Explosion.DisplayAnimated()

        if (BomberRock.Explosion.currentframe >= BomberRock.Explosion.frames):
          BomberRock.Explosion.h            = -1
          BomberRock.Explosion.v            = -1
          BomberRock.Explosion.currentframe = 1
          BomberRock.Explosion.exploding    = 0
          BomberRock.Explosion.alive        = 0
          BomberRock.exploding              = 0
          BomberRock.alive                  = 0
          BomberRock.h                      = -1
          BomberRock.v                      = -1
          RedrawGround(TheGround)
          #compute score
          SpaceDotScore = SpaceDotScore + AsteroidPoints
        


              
      #BomberShip
      if (BomberShip.exploding == 1):
        BomberShip.Explosion.DisplayAnimated()

        #Kill bombership after explosion animation is complete
        if (BomberShip.Explosion.currentframe >= BomberShip.Explosion.frames):
          BomberShip.Explosion.currentframe = 1
          BomberShip.Explosion.exploding    = 0
          BomberShip.Explosion.alive        = 0
          BomberShip.exploding              = 0
          BomberShip.alive                  = 0
          RedrawGround(TheGround)
          #compute score
          SpaceDotScore = SpaceDotScore + BomberPoints


      #HomingMissileShip
      if (HomingMissileShip.exploding == 1):
        if (HomingMissileShipExplosion.h == -1):
          CenterSpriteOnShip(HomingMissileShipExplosion,HomingMissileShip)
        HomingMissileShipExplosion.DisplayAnimated()

        #Kill homing missile after explosion animation is complete
        if (HomingMissileShipExplosion.currentframe >= HomingMissileShipExplosion.frames):
          HomingMissileShipExplosion.currentframe = 1
          HomingMissileShipExplosion.exploding    = 0
          HomingMissileShipExplosion.alive        = 0
          HomingMissileShip.exploding             = 0
          HomingMissileShip.alive                 = 0
          HomingMissileShipExplosion.h = HomingMissileShip.h
          HomingMissileShipExplosion.v = HomingMissileShip.v
          Playfield = HomingMissileShipExplosion.EraseSpriteFromPlayfield(Playfield)
          Playfield = HomingMissileSprite.EraseSpriteFromPlayfield(Playfield)
          HomingMissileShipExplosion.h = -1 
          HomingMissileShipExplosion.v = -1 
          RedrawGround(TheGround)
          #compute score
          SpaceDotScore = SpaceDotScore + HomingMissilePoints

      #PlayerShip
      if (PlayerShip.exploding == 1):
        PlayerShip.Explosion.h = PlayerShip.h
        PlayerShip.Explosion.v = PlayerShip.v
        PlayerShip.Explosion.DisplayAnimated()
        #LED.SaveConfigData()

        #Kill PlayerShip after explosion animation is complete
        if (PlayerShip.Explosion.currentframe >= LED.PlayerShipExplosion.frames):
          PlayerShip.Explosion.currentframe = 1
          PlayerShip.Explosion.exploding    = 0
          PlayerShip.Explosion.alive        = 0
          PlayerShip.exploding              = 0
          PlayerShip.alive                  = 0
          PlayerShip.Explosion.h            = -1
          PlayerShip.Explosion.v            = -1



      #UFO Missiles need to be optimized into an array like we did with asteroids
      if (UFOMissile1.exploding == 1 ):
        if (UFOMissile1.Explosion.h == -1):
          UFOMissile1.Explosion.h = UFOMissile1.h
          UFOMissile1.Explosion.v = UFOMissile1.v
        UFOMissile1.Explosion.DisplayAnimated()


        #Kill UFOMissile after explosion animation is complete
        if (UFOMissile1.Explosion.currentframe >= UFOMissile1.Explosion.frames):
          UFOMissile1.Explosion.currentframe = 1
          UFOMissile1.Explosion.exploding    = 0
          UFOMissile1.Explosion.alive        = 0
          UFOMissile1.exploding              = 0
          UFOMissile1.alive                  = 0
          UFOMissile1.Explosion.h            = -1
          UFOMissile1.Explosion.v            = -1
          RedrawGround(TheGround)
          #compute score
          SpaceDotScore = SpaceDotScore + AsteroidPoints

       



      #UFO Missiles need to be optimized into an array like we did with asteroids
      if (UFOMissile2.exploding == 1 ):
        if (UFOMissile2.Explosion.h == -1):
          UFOMissile2.Explosion.h = UFOMissile2.h
          UFOMissile2.Explosion.v = UFOMissile2.v
        UFOMissile2.Explosion.DisplayAnimated()

        #Kill missile after explosion animation is complete
        if (UFOMissile2.Explosion.currentframe >= UFOMissile2.Explosion.frames):
          UFOMissile2.Explosion.currentframe = 1
          UFOMissile2.Explosion.exploding    = 0
          UFOMissile2.Explosion.alive        = 0
          UFOMissile2.exploding              = 0
          UFOMissile2.alive                  = 0
          UFOMissile2.Explosion.h            = -1
          UFOMissile2.Explosion.v            = -1
          RedrawGround(TheGround)
          #compute score
          SpaceDotScore = SpaceDotScore + AsteroidPoints

      #UFO Missiles need to be optimized into an array like we did with asteroids
      if (UFOMissile3.exploding == 1 ):
        if (UFOMissile3.Explosion.h == -1):
          UFOMissile3.Explosion.h = UFOMissile3.h
          UFOMissile3.Explosion.v = UFOMissile3.v
        UFOMissile3.Explosion.DisplayAnimated()

        #Kill missile after explosion animation is complete
        if (UFOMissile3.Explosion.currentframe >= UFOMissile3.Explosion.frames):
          UFOMissile3.Explosion.currentframe = 1
          UFOMissile3.Explosion.exploding    = 0
          UFOMissile3.Explosion.alive        = 0
          UFOMissile3.exploding              = 0
          UFOMissile3.alive                  = 0
          UFOMissile3.Explosion.h            = -1
          UFOMissile3.Explosion.v            = -1
          RedrawGround(TheGround)
          #compute score
          SpaceDotScore = SpaceDotScore + AsteroidPoints





      #if (PlayerShip.alive == 0):
      #  PlayerShipExplosion.Animate(PlayerShip.h-2,PlayerShip.v-2,'forward',0.025)
        
      #Display animation and clock every X seconds
      #if (CheckElapsedTime(CheckTime) == 1):
      #  ScrollScreenShowLittleShipTime(ScrollSleep)         
  
     
      #-------------------------------------
      # Display Score
      #-------------------------------------
      LED.DisplayScore(SpaceDotScore,LED.MedGreen)
      if(SpaceDotScore > LED.SpaceDotHighScore):
        LED.SpaceDotHighScore = SpaceDotScore


     
      #-------------------------------------
      # End of Wave 
      #-------------------------------------
      
      #check for time between armadas
      if (Wave.Alive == False):
        MovesSinceWaveStop = MovesSinceWaveStop + 1
        
        #print("Moves since wave stop:",MovesSinceWaveStop)
        if (MovesSinceWaveStop > MovesBetweenWaves):
          print("--End of Wave--")
          MovesSinceWaveStop = 0
          Wave.Alive  = True
                   

          PlayerMissileCount = PlayerMissileCount + 1
          if (PlayerMissileCount >= MaxPlayerMissiles):
            PlayerMissileCount = MaxPlayerMissiles
          PlayerMissiles.append(LED.Ship(-0,-0,PlayerMissileR,PlayerMissileG,PlayerMissileB,1,1,5,0,1,'PlayerMissile', 0,0))
          PlayerMissiles[-1].alive     = 0
          PlayerMissiles[-1].exploding = 0
          PlayerMissiles[-1].Explosion = copy.deepcopy(LED.SmallExplosion)

          #increase speed of all missiles
          PlayerMissileSpeed = PlayerMissileSpeed -1
          if(PlayerMissileSpeed <= PlayerMissileMinSpeed):
            PlayerMissileSpeed = PlayerMissileMinSpeed

          for i in range(0,PlayerMissileCount):
            PlayerMissiles[i].speed = PlayerMissileSpeed

          #increase speed of player ship
          PlayerShipSpeed = PlayerShipSpeed -5
          PlayerShipMinSpeed = PlayerShipMinSpeed -5
          if(PlayerShipMinSpeed <= PlayerShipAbsoluteMinSpeed):
            PlayerShipMinSpeed = PlayerShipAbsoluteMinSpeed

          if(PlayerShipSpeed <= PlayerShipAbsoluteMinSpeed):
            PlayerShipSpeed = PlayerShipAbsoluteMinSpeed

          PlayerShip.speed = PlayerShipSpeed



          #adjust speeds, lower number is faster
          AsteroidMinSpeed = AsteroidMinSpeed - 1
          if(AsteroidMinSpeed < WaveMinSpeed):
            AsteroidMinSpeed = WaveMinSpeed
          
          AsteroidMaxSpeed = AsteroidMaxSpeed - 1
          if(AsteroidMaxSpeed < WaveMinSpeed + WaveSpeedRange ):
            AsteroidMaxSpeed = WaveMinSpeed + WaveSpeedRange

          LED.DisplayLevel(Wave.WaveCount,LED.MedBlue)


          #launch next wave of asteroids, maybe show some fancy graphics here
          Wave.AsteroidCount = Wave.AsteroidCount + 1
          Wave.WaveCount     = Wave.WaveCount + 1

          if(Wave.AsteroidCount  >= AsteroidsInWaveMax):
            Wave.AsteroidCount    = AsteroidsInWaveMax

          Wave.CreateAsteroidWave()
          Wave.Alive        = True
          

          m,r = divmod(Wave.WaveCount, 5)
          if(r == 0):
            LED.SaveConfigData()

          #print ("Wave:",Wave.WaveCount,"Asteroids in wave:",Wave.AsteroidCount)
          #print("----")
          

        
      time.sleep(MainSleep / 50)
      
      
  LED.ClearBigLED()
  LED.ClearBuffers()
  CursorH = 0
  CursorV = 0
  LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"THE PLANET SURFACE IS DESTROYED",CursorH=CursorH,CursorV=CursorV,MessageRGB=(225,0,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalTypeSpeed)
  LED.BlinkCursor(CursorH= CursorH,CursorV=CursorV,CursorRGB=CursorRGB,CursorDarkRGB=CursorDarkRGB,BlinkSpeed=0.5,BlinkCount=2)
  LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"YOUR EFFORTS WERE VALIANT BUT INSUFFICIENT",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalTypeSpeed)
  LED.BlinkCursor(CursorH= CursorH,CursorV=CursorV,CursorRGB=CursorRGB,CursorDarkRGB=CursorDarkRGB,BlinkSpeed=0.5,BlinkCount=2)

  LED.ScreenArray, CursorH,CursorV = LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"HIGH SCORE: " ,CursorH=CursorH,CursorV=CursorV,MessageRGB=(0,205,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)
  LED.ScreenArray, CursorH,CursorV = LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray, str(LED.SpaceDotHighScore),CursorH=CursorH,CursorV=CursorV,MessageRGB=(150,150,150),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)
  LED.BlinkCursor(CursorH= CursorH,CursorV=CursorV,CursorRGB=CursorRGB,CursorDarkRGB=CursorDarkRGB,BlinkSpeed=0.5,BlinkCount=1)

  LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"Games Played:",CursorH=CursorH,CursorV=CursorV,MessageRGB=(0,205,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)
  LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,str(LED.SpaceDotGamesPlayed),CursorH=CursorH,CursorV=CursorV,MessageRGB=(150,150,150),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)
  LED.BlinkCursor(CursorH= CursorH,CursorV=CursorV,CursorRGB=CursorRGB,CursorDarkRGB=CursorDarkRGB,BlinkSpeed=0.5,BlinkCount=1)
  LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"UNTIL NEXT TIME...",CursorH=CursorH,CursorV=CursorV,MessageRGB=(0,0,200),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)
  LED.BlinkCursor(CursorH= CursorH,CursorV=CursorV,CursorRGB=CursorRGB,CursorDarkRGB=CursorDarkRGB,BlinkSpeed=0.5,BlinkCount=2)


  return





def LaunchSpaceDot(Duration = 10000,ShowIntro=True,StopEvent=None):
  
    
    
    
  if(ShowIntro == True):

    #--------------------------------------
    # M A I N   P R O C E S S I N G      --
    #--------------------------------------
    LED.LoadConfigData()

    LED.ShowTitleScreen(
        BigText             = 'ASTRO',
        BigTextRGB          = LED.HighBlue,
        BigTextShadowRGB    = LED.ShadowRed,
        LittleText          = 'SMASH',
        LittleTextRGB       = LED.MedGreen,
        LittleTextShadowRGB = (0,10,0), 
        ScrollText          = 'The sky really is falling',
        ScrollTextRGB       = LED.MedYellow,
        ScrollSleep         = 0.03, # time in seconds to control the scrolling (0.005 is fast, 0.1 is kinda slow)
        DisplayTime         = 1,           # time in seconds to wait before exiting 
        ExitEffect          = 0,            # 0=Random / 1=shrink / 2=zoom out / 3=bounce / 4=fade /5=fallingsand
        BigText2            = 'SMASH',
        BigText2RGB         = LED.HighBlue,
        BigText2ShadowRGB   = LED.ShadowRed,

        )


  LED.ClearBigLED()
  LED.ClearBuffers()
  CursorH = 0
  CursorV = 0
  LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"MASS DRIVERS DETECTED",CursorH=CursorH,CursorV=CursorV,MessageRGB=(225,0,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalTypeSpeed)
  LED.BlinkCursor(CursorH= CursorH,CursorV=CursorV,CursorRGB=CursorRGB,CursorDarkRGB=CursorDarkRGB,BlinkSpeed=0.5,BlinkCount=2)
  LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"ALIEN SHIPS AND ASTEROIDS ARE HURTLING TOWARDS THE EARTH",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalTypeSpeed)
  LED.BlinkCursor(CursorH= CursorH,CursorV=CursorV,CursorRGB=CursorRGB,CursorDarkRGB=CursorDarkRGB,BlinkSpeed=0.5,BlinkCount=2)
  #LED.ScreenArray, CursorH,CursorV = LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"HIGH SCORE: " ,CursorH=CursorH,CursorV=CursorV,MessageRGB=(0,205,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)
  #LED.ScreenArray, CursorH,CursorV = LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray, str(LED.OutbreakHighScore),CursorH=CursorH,CursorV=CursorV,MessageRGB=(150,150,150),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)
  #LED.BlinkCursor(CursorH= CursorH,CursorV=CursorV,CursorRGB=CursorRGB,CursorDarkRGB=CursorDarkRGB,BlinkSpeed=0.5,BlinkCount=1)
  #LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"Games Played:",CursorH=CursorH,CursorV=CursorV,MessageRGB=(0,205,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)
  #LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,str(LED.OutbreakGamesPlayed),CursorH=CursorH,CursorV=CursorV,MessageRGB=(150,150,150),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)
  #LED.BlinkCursor(CursorH= CursorH,CursorV=CursorV,CursorRGB=CursorRGB,CursorDarkRGB=CursorDarkRGB,BlinkSpeed=0.5,BlinkCount=1)
  LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"GOOD LUCK!",CursorH=CursorH,CursorV=CursorV,MessageRGB=(0,0,200),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)
  LED.BlinkCursor(CursorH= CursorH,CursorV=CursorV,CursorRGB=CursorRGB,CursorDarkRGB=CursorDarkRGB,BlinkSpeed=0.5,BlinkCount=2)


  PlaySpaceDot(Duration,StopEvent)
      







#execute if this script is called direction
if __name__ == "__main__" :
  while(1==1):
    #print("After SAVE OutbreakGamesPlayed:",LED.OutbreakGamesPlayed)
    LaunchSpaceDot(Duration=100000, ShowIntro=True, StopEvent=None)        












