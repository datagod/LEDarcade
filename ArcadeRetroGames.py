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
#      _    ____   ____    _    ____  _____    ____ _     ___   ____ _  __   --
#     / \  |  _ \ / ___|  / \  |  _ \| ____|  / ___| |   / _ \ / ___| |/ /   --
#    / _ \ | |_) | |     / _ \ | | | |  _|   | |   | |  | | | | |   | ' /    --
#   / ___ \|  _ <| |___ / ___ \| |_| | |___  | |___| |__| |_| | |___| . \    --
#  /_/   \_\_| \_\\____/_/   \_\____/|_____|  \____|_____\___/ \____|_|\_\   --
#                                                                            --
#                                                                            --
#  Main Programs                                                             --
#                                                                            --
#------------------------------------------------------------------------------



#------------------------------------------------------------------------------
#  Arcade Retro Games
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
#   Date:    December 13, 2021                                               --
#   Reason:  Creating a library of games that can be called from other       --
#            programs.                                                       --
#------------------------------------------------------------------------------
#------------------------------------------------------------------------------



#NOTES

#Future Work
#revisit curses for reading keypress.  Only initialize once.


#running PacDot automatically as background task (non interactive)
# cd /etc
# sudo nano rc.local
# nohup sudo python /home/pi/Pimoroni/unicornhat/examples/PacDot.py 0.07 0.07 0.07 20 40 200 >/dev/null 2>&1 &

#running PacDot after auto-loggin in
#modify profile script to include call to bash file
#cd /etc
#sudo nano profile
#cd pi
#./go.sh

import LEDarcade as LED
import copy
import random
import time


#------------------------------------------------------------------------------
# Initialization Section                                                     --
#------------------------------------------------------------------------------


#----------------------------
#-- SpaceDot               --
#----------------------------
SpaceDotWallLives   = 50
SpaceDotGroundLives = 25
PlanetSurfaceSleep  = 1000
DebrisCleanupSleep  = 2000 #make sure empty cells on playfield are displayed as empty (0,0,0) 



#Wave
MinHomingMissileWave = 5 #homning missles / ufos only show up after this wave
MinBomberWave        = 3 #homning missles / ufos only show up after this wave


SpaceDotMinH = 25
SpaceDotMaxH = 63
SpaceDotMinV = 0
SpaceDotMaxV = 26

#Ground
GroundV = SpaceDotMaxV - 1

#Player
PlayerShipSpeed       = 200
PlayerShipMinSpeed    = 50
PlayerShipAbsoluteMinSpeed = 10
MaxPlayerMissiles     = 5
PlayerMissiles        = 2
PlayerMissileSpeed    = 25
PlayerMissileMinSpeed = 8
PlayerShipLives       = 3


#BomberShip
BomberShipSpeed       = 80
ChanceOfBomberShip    = 2000  #chance of a bomberhsip appearing
BomberRockSpeed       = 30   #how fast the bomber dropped asteroid falls

#UFO
UFOMissileSpeed = 50
UFOShipSpeed    = 50  #also known as the EnemeyShip
UFOShipMinSpeed = 25
UFOShipMaxSpeed = 100

#HomingMissile 
UFOFrameRate               = 50  #random animated homing missiles
HomingMissileFrameRate     = 50  #the white one that looks like satellite from astrosmash
HomingMissileInitialSpeed  = 75
HomingMissileLives         = 25
HomingMissileSprites       = 12    #number of different sprites that can be homing missiles
HomingMissileDescentChance = 3     #chance of homing missile  not descending, lower number greater chance of being slow
ChanceOfHomingMissile      = 10000  #chance of a homing missile appearing



#Points
SpaceDotScore        = 0
UFOPoints            = 10
BomberPoints         = 5
BomberHitPoints      = 1
HomingMissilePoints  = 5
AsteroidLandedPoints = 1
AsteroidPoints       = 5

#Asteroids
WaveStartV           = -5
WaveMinSpeed         = 5     #The fastest the wave of asteroids can fall
WaveSpeedRange       = 60    #how much variance in the wave speed min and max
AsteroidMinSpeed     = 30    #lower the number the faster the movement (based on ticks)
AsteroidMaxSpeed     = 60  
AsteroidSpawnChance  = 100  #lower the number the greater the chance
WaveDropSpeed        = 550  #how often the next chunk of the wave is dropped
MovesBetweenWaves    = 2000
AsteroidsInWaveMax   = 200
AsteroidsInWaveMin   = 5 
AsteroidsToDropMin   = 1     #Number of asteroids to drop at a time
AsteroidsToDropMax   = 5   #Number of asteroids to drop at a time


Empty      = LED.Ship(-1,-1,0,0,0,0,1,0,0,0,'EmptyObject',0,0)


KeyboardSpeed  = 15
#Create playfield
Playfield = ([[]])
Playfield = [[0 for i in range(LED.HatWidth)] for i in range(LED.HatHeight)]





#----------------------
#-- Clock Variables  --
#----------------------


CheckTime        = 60
ClockOnDuration  = 3
ClockOffDuration = CheckTime - ClockOnDuration
ClockSlideSpeed  = 1 
CheckClockSpeed  = 500

BrightRGB = (0,200,0)
ShadowRGB = (0,5,0)

#apply CPU modifier
#VirusTopSpeed     = VirusTopSpeed    * LED.CPUModifier
#VirusBottomSpeed  = VirusBottomSpeed * LED.CPUModifier


random.seed()
start_time = time.time()


#----------------------------
#-- PacDot                 --
#----------------------------

#thise things are left over from before I made the PacDot function
#cleanup later I hope (likely too lazy, likkit bitch!)

PowerPills  = 25
moves       = 0
DotsEaten   = 0
Pacmoves    = 0
PowerPillActive = 0
PowerPillMoves  = 0
BlueGhostmoves = 250


# StartGhostSpeed1    = 3
# StartGhostSpeed2    = 3
# StartGhostSpeed3    = 4
# StartGhostSpeed4    = 5
# GhostSpeed1    = StartGhostSpeed1
# GhostSpeed2    = StartGhostSpeed2
# GhostSpeed3    = StartGhostSpeed3
# GhostSpeed4    = StartGhostSpeed4
# PacSpeed       = 2
# BlueGhostSpeed = 4


LevelCount     = 1
PacPoints      = 0


PacStuckMaxCount = 20
PacStuckCount    = 1
PacOldH          = 0
PacOldV          = 0

#Pac Scoring
DotPoints         = 1
BlueGhostPoints   = 20
PillPoints        = 5
PacDotScore       = 0



MaxMoves = 2000

#Timers




#----------------------------
#-- Dot Invaders           --
#----------------------------



PlayerShipR = LED.SDMedBlueR
PlayerShipG = LED.SDMedBlueG
PlayerShipB = LED.SDMedBlueB
PlayerMissileR = LED.SDMedWhiteR
PlayerMissileG = LED.SDMedWhiteG
PlayerMissileB = LED.SDMedWhiteB


PlayerMissile1 = LED.Ship(-0,-0,PlayerMissileR,PlayerMissileG,PlayerMissileB,1,1,5,0,0,'PlayerMissile', 0,0)
PlayerMissile2 = LED.Ship(-0,-0,PlayerMissileR,PlayerMissileG,PlayerMissileB,1,1,5,0,0,'PlayerMissile', 0,0)


UFOMissile1   = LED.Ship(-1,-0,PlayerMissileR,PlayerMissileG,PlayerMissileB,3,3,UFOMissileSpeed,0,0,'UFOMissile',0,0)
UFOMissile2   = LED.Ship(-1,-0,PlayerMissileR,PlayerMissileG,PlayerMissileB,3,3,UFOMissileSpeed,0,0,'UFOMissile',0,0)
UFOMissile3   = LED.Ship(-1,-0,PlayerMissileR,PlayerMissileG,PlayerMissileB,3,3,UFOMissileSpeed,0,0,'UFOMissile',0,0)





# # MAX
# # 39 40 41 42 43 44 45
# ColorList.append((255,  0,  0))  #MAX-RED
# ColorList.append((  0,255,  0))  #MAX-GREEN
# ColorList.append((  0,  0,255))  #MAX-BLUE
# ColorList.append((255,255,0  ))  #MAX-YELLOW
# ColorList.append((255,  0,255))  #MAX-PURPLE
# ColorList.append((  0,255,255))  #MAX-CYAN
# ColorList.append((255,255,255))  #MAX-WHITE


AsteroidExplosion = LED.ColorAnimatedSprite(
  h      = 0 , 
  v      = 0, 
  name   = 'Asteroid',
  width  = 3, 
  height = 3,
  frames = 5,
 framerate    = 10,
  grid=[]
)

AsteroidExplosion.grid.append(
  [0, 0, 0,
   0,45, 0,
   0, 0, 0
  ]
)

AsteroidExplosion.grid.append(
  [0,45, 0,
  45,45,45,
   0,45, 0
  ]
)
AsteroidExplosion.grid.append(
  [0,45, 0,
  45, 8,45,
   0,45, 0
  ]
)
AsteroidExplosion.grid.append(
  [0, 8, 0,
   8, 0, 8,
   0, 8, 0
  ]
)
AsteroidExplosion.grid.append(
  [0, 0, 0,
   0, 0, 0,
   0, 0, 0
  ]
)



AsteroidExplosion2 = LED.ColorAnimatedSprite(
  h      = 0 , 
  v      = 0, 
  name   = 'Asteroid',
  width  = 3, 
  height = 1,
  frames = 7,
 framerate    = 50,
  grid=[]
)

AsteroidExplosion2.grid.append(
  [
    0,45, 0
  ]
)

AsteroidExplosion2.grid.append(
  [
   45,20,45
  ]
)

AsteroidExplosion2.grid.append(
  [
   20,20,20
  ]
)

AsteroidExplosion2.grid.append(
  [
    8, 8, 8
  ]
)

AsteroidExplosion2.grid.append(
  [
    8, 6, 8
  ]
)

AsteroidExplosion2.grid.append(
  [
    6, 5, 6
  ]
)

AsteroidExplosion2.grid.append(
  [
    5, 5, 5
  ]
)




PlayerShipExplosion = LED.ColorAnimatedSprite(
  h=0, v=0, name="Explosion", width=5, height=5, 
  frames=14,
  framerate=2,grid=[]
)
PlayerShipExplosion.grid.append(
  [0,0,0,0,0,
   0,0,0,0,0,
   0,0,4,0,0,
   0,0,0,0,0,
   0,0,0,0,0
   ]
)

PlayerShipExplosion.grid.append(
   [0,0,0,0,0,
    0, 0, 4, 0,0,
    0, 4,18, 4,0,
    0, 0, 4, 0,0,
    0,0,0,0,0
   ]
)
  
PlayerShipExplosion.grid.append(
   [ 0, 0, 4, 0, 0,
     0,18,18,18, 0,
     4,18,19,18, 4,
     0,18,18,18, 0,
     0, 0, 4, 0,0
   ]
)
PlayerShipExplosion.grid.append(
   [ 0,18,18,18, 0,
    18,19,19,19,18,
    18,18,20,19,18,
    18,19,19,19,18,
     0,18,18,18, 0
   ]
)
PlayerShipExplosion.grid.append(
   [ 0,19,19,19, 0,
    19,20,20,20,19,
    19,20,20,20,19,
    19,20,20,20,19,
     0,19,19,19, 0
   ]
)
PlayerShipExplosion.grid.append(
   [ 0,20,20,20, 0,
    20,20,20,20,20,
    20,20,20,20,20,
    20,20,20,20,20,
     0,20,20,20, 0
   ]


)
PlayerShipExplosion.grid.append(
   [00,20,20,20,00,
    20,20,20,20,20,
    20,20, 8,20,20,
    20,20,20,20,20,
    00,20,20,20,00
   ]
)
PlayerShipExplosion.grid.append(
   [ 0,20,20,20, 0,
    20,20, 8,20,20,
    20, 8, 7, 8,20,
    20,20, 8,20,20,
     0,20,20,20, 0
   ]
)  

PlayerShipExplosion.grid.append(
   [ 0,20, 8,20, 0,
    20, 8, 7, 8,20,
     8, 7, 6, 7, 8,
    20, 8, 7, 8,20,
     0,20, 8,20, 0
   ]
)
PlayerShipExplosion.grid.append(
   [ 0, 8, 7, 8, 0,
     8, 7, 6, 7, 8,
     7, 6, 5, 6, 7,
     8, 7, 6, 7, 8,
     0, 8, 7, 8, 0
   ]
)
PlayerShipExplosion.grid.append(
   [ 0, 7, 6, 7, 0,
     7, 6, 0, 6, 7,
     6, 5, 0, 5, 6,
     7, 6, 0, 6, 7,
     0, 7, 6, 7, 0
   ]
)
PlayerShipExplosion.grid.append(
   [ 0, 6, 5, 6, 0,
     6, 5, 0, 5, 6,
     5, 0, 0, 0, 5,
     6, 5, 0, 5, 6,
     0, 6, 5, 6, 0
   ]
)
PlayerShipExplosion.grid.append(
   [ 0, 5, 0, 5, 0,
     5, 0, 0, 0, 5,
     0, 0, 0, 0, 0,
     5, 0, 0, 0, 5,
     0, 5, 0, 5, 0
   ]
)  

PlayerShipExplosion.grid.append(
   [ 0, 0, 0, 0, 0,
     0, 0, 0, 0, 0,
     0, 0, 0, 0, 0,
     0, 0, 0, 0, 0,
     0, 0, 0, 0, 0
   ]
)  




BomberShipExplosion = LED.ColorAnimatedSprite(
  h = 0, 
  v = 0,
  name         = "Explosion", 
  width        = 5, 
  height       = 5, 
  frames       = 9,
 framerate    = 15, 
  grid         = []
)
BomberShipExplosion.grid.append(
   [ 0, 0, 0, 0, 0,
     0, 0,45, 0, 0,
     0,45,45,45, 0,
     0, 0,45, 0, 0,
     0, 0, 0, 0, 0
   ]
)

BomberShipExplosion.grid.append(
   [ 0, 0,45, 0, 0,
     0,45,45,45, 0,
    45,45,45,45,45,
     0,45,45,45, 0,
     0, 0,45, 0, 0
   ]
)

BomberShipExplosion.grid.append(
   [ 0, 0,42, 0, 0,
     0,45,42,45, 0,
    42,42,42,42,42,
     0,45,42,45, 0,
     0, 0,42, 0, 0
   ]
)


BomberShipExplosion.grid.append(
   [ 0, 0,42, 0, 0,
     0, 2,20, 2, 0,
    42,20,20,20,42,
     0, 2,20, 2, 0,
     0, 0,42, 0, 0
   ]
)


BomberShipExplosion.grid.append(
   [ 0, 0,20, 0, 0,
     0, 1,20, 1, 0,
    20,20,39,20,20,
     0, 1,20, 1, 0,
     0, 0,20, 0, 0
   ]
)

BomberShipExplosion.grid.append(
   [ 0, 0,39, 0, 0,
     0, 1,39, 1, 0,
    39,39,39,39,20,
     0, 1,39, 1, 0,
     0, 0,39, 0, 0
   ]
)

BomberShipExplosion.grid.append(
   [ 0, 0,39, 0, 0,
     0, 1, 8, 1, 0,
    39, 8, 6, 8,39,
     0, 1, 8, 1, 0,
     0, 0,39, 0, 0
   ]
)


BomberShipExplosion.grid.append(
   [ 0, 0, 0, 0, 0,
     0, 0, 5, 0, 0,
     0, 5, 5, 5, 0,
     0, 0, 5, 0, 0,
     0, 0, 0, 0, 0
   ]
)

BomberShipExplosion.grid.append(
   [ 0, 0, 0, 0, 0,
     0, 0, 0, 0, 0,
     0, 0, 0, 0, 0,
     0, 0, 0, 0, 0,
     0, 0, 0, 0, 0
   ]
)





SmallExplosion = LED.ColorAnimatedSprite(
  h=-1, v=-1, name="Explosion", width=3, height=3,
  frames=7,
  framerate = 2,grid=[])
SmallExplosion.grid.append(
  [
   0, 0, 0,
   0,29, 0,
   0, 0, 0,
   
   ]
)

SmallExplosion.grid.append(
   [ 
     0,29, 0,
    29,30,29,
     0,29, 0, 
   
   ]
)
  
SmallExplosion.grid.append(
   [ 
      0,30, 0,
     30,31,30,
      0,30, 0,
     
   ]
)
SmallExplosion.grid.append(
   [
     0,31, 0,
    31,32,31,
     0,31, 0,
    
   ]
)

SmallExplosion.grid.append(
   [
     0,32, 0,
    32, 8,32,
     0,32, 0
   ]
)
   

SmallExplosion.grid.append(
   [
     0,20, 0,
    20, 0,20,
     0,20, 0,
    
   ]
)

   
SmallExplosion.grid.append(
   [
     0, 0, 0,
     0, 0, 0,
     0, 0, 0,
    
   ]
)



BigGroundExplosion = LED.ColorAnimatedSprite(
  h            = -1, #this is important, it is used to indicate if the explosion is brand new.  I think.
  v            = -1,  
  name         = "Explosion", 
  width        = 9, 
  height       = 3, 
  frames       = 6, 
 framerate    = 150,
  grid         = []
)


BigGroundExplosion.grid.append(
  [
  44, 0, 0, 0, 0, 0, 0, 0, 0,
   0, 0, 0, 0, 4, 0, 0, 0, 0,
   0, 0, 0, 0, 0, 0, 0, 0, 0
   ]
)

BigGroundExplosion.grid.append(
  [
  44, 0, 0, 0, 0, 0, 0, 0, 0,
   0, 0, 0, 4, 4, 4, 0, 0, 0,
   0, 0, 0, 0, 0, 0, 0, 0, 0
   ]
)
BigGroundExplosion.grid.append(
  [
  44, 0, 0, 0, 4, 0, 0, 0, 0,
   0, 0, 4, 4, 4, 4, 4, 0, 0,
   0, 0, 0, 0, 4, 0, 0, 0, 0
   ]
)
BigGroundExplosion.grid.append(
  [
  44, 0, 0, 0, 4, 0, 0, 0, 0,
   0, 4, 4, 4, 4, 4, 4, 4, 0,
   0, 0, 0, 0, 4, 0, 0, 0, 0
   ]
)
BigGroundExplosion.grid.append(
  [
  44, 0, 0, 0, 4, 0, 0, 0, 0,
   4, 4, 4, 0, 0, 0, 4, 4, 4,
   0, 0, 0, 0, 4, 0, 0, 0, 0
   ]
)
BigGroundExplosion.grid.append(
  [
  44, 0, 0, 0, 0, 0, 0, 0, 0,
   4, 0, 0, 0, 0, 0, 0, 0, 4,
   0, 0, 0, 0, 0, 0, 0, 0, 0
   ]
)
BigGroundExplosion.grid.append(
  [
  44, 0, 0, 0, 0, 0, 0, 0, 0,
   0, 0, 0, 0, 0, 0, 0, 0, 0,
   0, 0, 0, 0, 0, 0, 0, 0, 0
   ]
)





BigShipExplosion = LED.ColorAnimatedSprite(
  h = 0, 
  v = 0,
  name         = "Explosion", 
  width        = 8, 
  height       = 5, 
  frames       = 10,
 framerate    = 15, 
  grid         = []
)
BigShipExplosion.grid.append(
   [ 0, 0, 0, 0, 0, 0, 0, 0, 
     0, 0, 0, 5, 5, 0, 0, 0, 
     0, 0, 5, 5, 5, 5, 0, 0, 
     0, 0, 0, 5, 5, 0, 0, 0, 
     0, 0, 0, 0, 0, 0, 0, 0
   ]
)
BigShipExplosion.grid.append(
   [ 0, 0, 0, 0, 0, 0, 0, 0, 
     0, 0, 0, 5, 5, 0, 0, 0, 
     0, 0, 5, 5, 5, 5, 0, 0, 
     0, 0, 0, 5, 5, 0, 0, 0, 
     0, 0, 0, 0, 0, 0, 0, 0
   ]
)

BigShipExplosion.grid.append(
   [ 0, 0, 0, 5, 5, 0, 0, 0, 
     0, 0, 0, 7, 7, 0, 0, 0, 
     0, 5, 7, 7, 7, 7, 5, 0, 
     0, 0, 0, 7, 7, 0, 0, 0, 
     0, 0, 0, 5, 5, 0, 0, 0
   ]
)
BigShipExplosion.grid.append(
   [ 0, 0, 0, 5, 5, 0, 0, 0, 
     0, 0, 0, 7, 7, 0, 0, 0, 
     0, 5, 7, 7, 7, 7, 5, 0, 
     0, 0, 0, 7, 7, 0, 0, 0, 
     0, 0, 0, 5, 5, 0, 0, 0
   ]
)

BigShipExplosion.grid.append(
   [ 0, 0, 0, 8, 8, 0, 0, 0, 
     0, 0, 0,39,39, 0, 0, 0, 
     8, 8,39,39,39,39, 8, 8, 
     0, 0, 0,39,39, 0, 0, 0, 
     0, 0, 0, 8, 8, 0, 0, 0
   ]
)

BigShipExplosion.grid.append(
   [ 0, 0, 0,39,39, 0, 0, 0, 
     0, 0, 0,45,45, 0, 0, 0, 
    39,39,45,45,45,45,39,39, 
     0, 0, 0,45,45, 0, 0, 0, 
     0, 0, 0,39,39, 0, 0, 0
   ]
)


BigShipExplosion.grid.append(
   [ 0, 0, 0,45,45, 0, 0, 0, 
     0, 0,45,45,45,45, 0, 0, 
    45,45,45,45,45,45,45,45, 
     0, 0,45,45,45,45, 0, 0, 
     0, 0, 0,45,45, 0, 0, 0
   ]
)


BigShipExplosion.grid.append(
   [ 0, 0, 0, 8, 8, 0, 0, 0, 
     0, 0, 5, 5, 5, 5, 0, 0, 
     8, 8, 5, 5, 5, 5, 8, 8, 
     0, 0, 5, 5, 5, 5, 0, 0, 
     0, 0, 0, 8, 8, 0, 0, 0
   ]
)

BigShipExplosion.grid.append(
   [ 0, 0, 0, 8, 8, 0, 0, 0, 
     0, 0, 5, 5, 5, 5, 0, 0, 
     8, 8, 5, 5, 5, 5, 8, 8, 
     0, 0, 5, 5, 5, 5, 0, 0, 
     0, 0, 0, 8, 8, 0, 0, 0
   ]
)

BigShipExplosion.grid.append(
   [ 0, 0, 0, 0, 0, 0, 0, 0, 
     0, 0, 0, 0, 0, 0, 0, 0, 
     0, 0, 0, 0, 0, 0, 0, 0, 
     0, 0, 0, 0, 0, 0, 0, 0, 
     0, 0, 0, 0, 0, 0, 0, 0
   ]
)


DropShip = LED.ColorAnimatedSprite(h=0, v=0, name="DropShip", width=5, height=8, frames=2, framerate=1,grid=[])
DropShip.grid.append(
  [
    0, 0, 0, 0, 0,
    0, 0,15, 0, 0,
    0, 0,15, 0, 0,
    0,14,15,14, 0,
    0,14, 7,14, 0,
    0, 0, 6, 0, 0,
    0, 0, 5, 0, 0,
    0, 0, 0, 0, 0,
  ]
)

DropShip.grid.append(
  [
    0, 0, 0, 0, 0,
    0, 0,15, 0, 0,
    0, 0,15, 0, 0,
    0,14,15,14, 0,
    0,14, 6,14, 0,
    0, 0, 5, 0, 0,
    0, 0, 5, 0, 0,
    0, 0, 0, 0, 0,
  ]
)



SpaceInvader = LED.ColorAnimatedSprite(h=0, v=0, name="SpaceInvader", width=13, height=8, frames=2, framerate=1,grid=[])
SpaceInvader.grid.append(
  [
    0, 0, 9, 0, 0, 0, 0, 0, 0, 0, 0, 9, 0,
    0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 
    0, 0, 9, 9,11, 9, 9, 9,11, 9, 9, 0, 0,
    0, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 0,
    0, 9, 0, 9, 9, 9, 9, 9, 9, 9, 0, 9, 0,
    0, 9, 0, 9, 0, 0, 0, 0, 0, 9, 0, 9, 0,
    0, 0, 0, 0, 9, 0, 0, 0, 9, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
  ]
)
SpaceInvader.grid.append(
  [
    0, 0, 9, 0, 0, 0, 0, 0, 0, 0, 0, 9, 0,
    0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9, 0, 0,
    0, 0, 9, 9,11, 9, 9, 9,11, 9, 9, 0, 0,
    0, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 0,
    0, 9, 0, 9, 9, 9, 9, 9, 9, 9, 0, 9, 0,
    0, 9, 0, 9, 0, 0, 0, 0, 0, 9, 0, 9, 0,
    0, 0, 0, 9, 0, 0, 0, 0, 0, 9, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
  ]
)



TinyInvader = LED.ColorAnimatedSprite(h=0, v=0, name="TinyInvader", width=7, height=6, frames=4, framerate=1,grid=[])
TinyInvader.grid.append(
  [
   0, 0, 0, 8, 0, 0, 0,
   0, 0, 9, 9, 9, 0, 0,
   0, 9,11, 9,11, 9, 0,
   0, 9, 9, 9, 9, 9, 0,
   0, 0, 9, 0, 9, 0, 0,
   0, 9, 0, 0, 0, 9, 0
  ]
)
TinyInvader.grid.append(
  [
   0, 0, 0, 8, 0, 0, 0, 
   0, 0, 9, 9, 9, 0, 0, 
   0, 9,11, 9,11, 9, 0, 
   0, 9, 9, 9, 9, 9, 0, 
   0, 0, 9, 0, 9, 0, 0, 
   0, 9, 0, 0, 0, 9, 0
  ]
)
TinyInvader.grid.append(
  [
   0, 0, 0,16, 0, 0, 0,
   0, 0, 9, 9, 9, 0, 0,
   0, 9,11, 9,11, 9, 0,
   0, 9, 9, 9, 9, 9, 0,
   0, 0, 9, 0, 9, 0, 0,
   0, 9, 0, 0, 0, 9, 0
  ]
)

TinyInvader.grid.append(
  [
   0, 0, 0,16, 0, 0, 0,
   0, 0, 9, 9, 9, 0, 0,
   0, 9,11, 9,11, 9, 0,
   0, 9, 9, 9, 9, 9, 0,
   0, 0, 9, 0, 9, 0, 0,
   0, 0, 9, 0, 9, 0, 0
  ]
)




SmallInvader = LED.ColorAnimatedSprite(h=0, v=0, name="SmallInvader", width=9, height=6, frames=2, framerate=1,grid=[])
SmallInvader.grid.append(
  [
    0, 0, 0, 9, 9, 9, 0, 0, 0,
    0, 0, 9, 9, 9, 9, 9, 0, 0,
    0, 9,10,11, 9,11,10, 9, 0,
    0, 9, 9, 9, 9, 9, 9, 9, 0,
    0, 9, 0, 9, 0, 9, 0, 9, 0,
    0, 0, 9, 0, 9, 0, 9, 0, 0,
  ]
)
SmallInvader.grid.append(
  [
    0, 0, 0, 9, 9, 9, 0, 0, 0,
    0, 0, 9, 9, 9, 9, 9, 0, 0,
    0, 9,10,11, 9,11,10, 9, 0,
    0, 9, 9, 9, 9, 9, 9, 9, 0,
    0, 9, 0, 9, 0, 9, 0, 9, 0,
    0, 9, 0, 9, 0, 9, 0, 9, 0,
  ]
)



LittleShipFlying = LED.ColorAnimatedSprite(h=0, v=0, name="LittleShips", width=16, height=8, frames=2, framerate=1,grid=[])

LittleShipFlying.grid.append(
  [
    0, 0, 0, 0, 0, 0, 0, 0, 0,15, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 5, 6, 7, 8, 5,14,14,14, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,15, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 5, 6, 7, 8, 5,14,14,14,
    0, 0, 0, 0, 0,15, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 6, 7, 8, 5,14,14,14, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    
   ]
)

LittleShipFlying.grid.append(
  [
    0, 0, 0, 0, 0, 0, 0, 0, 0,15, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 5, 6, 7, 8, 5,14,14,14, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,15, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 5, 6, 7, 8, 5,14,14,14,
    0, 0, 0, 0, 0,15, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 6, 7, 8, 5,14,14,14, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    
   ]
)


                  
BigShipFlying = LED.ColorAnimatedSprite(h=0, v=0, name="BigShipFlying", width=36, height=8, frames=6, framerate=1,grid=[])

BigShipFlying.grid.append(
  [
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0,15,15,15,15, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 5, 5, 5, 5,14,14,14,14,14,16,14,16,14,14,14,14, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 5, 5, 5, 5, 6, 6, 7, 7, 8, 8,17,14,14, 9,14, 9,14,14,13,13,13,13, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,15, 0, 0,
    0, 5, 5, 5, 5, 6, 6, 7, 7, 8, 8,17,14,14,14, 9,14, 9,13,13, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,17,14,14,14,
    0, 0, 0, 0, 0, 0, 0, 5, 5, 5, 5, 1,14,13,13,13,13,13, 8, 8, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 5,13,13,13,13, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
   ]
)

BigShipFlying.grid.append(
  [
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0,15,15,15,15, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 5, 5, 5, 5,14,14,15,14,14,16,14,16,14,14,14,14, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 5, 5, 5, 5, 6, 6, 7, 8, 8, 5,17,14,15, 9,14, 9,14,14,13,13,13,13, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,15, 0, 0,
    0, 5, 5, 5, 5, 6, 6, 7, 8, 8, 5,17,14,15,14, 9,14, 9,13,13, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5,14,14,14,
    0, 0, 0, 0, 0, 0, 0, 5, 5, 5, 5, 1,14,15,13,13,13,13, 0, 5, 5, 5, 7, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 5,13,13,13,13, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
   ]
)

BigShipFlying.grid.append(
  [
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0,15,15,15,15, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 5, 5, 5, 5,14,14,15,14,14,16,14,16,14,14,14,14, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 5, 5, 5, 5, 6, 6, 7, 8, 8, 5,17,14,15, 9,14, 9,14,14,13,13,13,13, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,15, 0, 0,
    0, 5, 5, 5, 5, 6, 6, 7, 8, 8, 5,17,14,15,14, 9,14, 9,13,13, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,17,14,14,14,
    0, 0, 0, 0, 0, 0, 0, 5, 5, 5, 5, 1,14,15,13,13,13,13, 0, 0, 0, 0, 0, 5, 5, 5, 7, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 5,13,13,13,13, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
   ]
)

BigShipFlying.grid.append(
  [
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0,15,15,15,15, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 5, 5, 5, 5,14,14,15,14,14,16,14,16,14,14,14,14, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 5, 5, 5, 5, 6, 6, 7, 8, 8, 5,17,14,15, 9,14, 9,14,14,13,13,13,13, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,15, 0, 0,
    0, 5, 5, 5, 5, 6, 6, 7, 8, 8, 5,17,14,15,14, 9,14, 9,13,13, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5,14,14,14,
    0, 0, 0, 0, 0, 0, 0, 5, 5, 5, 5, 1,14,15,13,13,13,13, 0, 0, 0, 0, 0, 0, 0, 0, 5, 5, 5, 7, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 5,13,13,13,13, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
   ]
)

BigShipFlying.grid.append(
  [
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0,15,15,15,15, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 5, 5, 5, 5,14,14,15,14,14,16,14,16,14,14,14,14, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 5, 5, 5, 5, 6, 6, 7, 8, 8, 5,17,14,15, 9,14, 9,14,14,13,13,13,13, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,15, 0, 0,
    0, 5, 5, 5, 5, 6, 6, 7, 8, 8, 5,17,14,15,14, 9,14, 9,13,13, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,17,14,14,14,
    0, 0, 0, 0, 0, 0, 0, 5, 5, 5, 5, 1,14,15,13,13,13,13, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5, 5, 5, 7, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 5,13,13,13,13, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
   ]
)

BigShipFlying.grid.append(
  [
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0,15,15,15,15, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 5, 5, 5, 5,14,14,15,14,14,16,14,16,14,14,14,14, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 5, 5, 5, 5, 6, 6, 7, 8, 8, 5,17,14,15, 9,14, 9,14,14,13,13,13,13, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,15, 0, 0,
    0, 5, 5, 5, 5, 6, 6, 7, 8, 8, 5,17,14,15,14, 9,14, 9,13,13, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5,14,14,14,
    0, 0, 0, 0, 0, 0, 0, 5, 5, 5, 5, 1,14,15,13,13,13,13, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5, 5, 5,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 5,13,13,13,13, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
   ]
)
 

#This will hold HH:MM
BigSprite = LED.Sprite(16,5,LED.GreenR,LED.GreenG,LED.GreenB,
[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
)


#DotZerk Human Death
HumanExplosion = LED.ColorAnimatedSprite(h=0, v=0, name="HumanExplosion", width=3, height=3, frames=6, framerate=1,grid=[])
HumanExplosion.grid.append(
  [
    0, 0, 0,
    0, 5, 0,
    0, 0, 0
  ]
)
HumanExplosion.grid.append(
  [
    0, 5, 0,
    5, 6, 5,
    0, 5, 0
  ]
)
HumanExplosion.grid.append(
  [
    0, 6, 0,
    6, 7, 6,
    0, 6, 0
  ]
)
HumanExplosion.grid.append(
  [
    0, 7, 0,
    7, 8, 7,
    0, 7, 0
  ]
)
HumanExplosion.grid.append(
  [
    0, 8, 0,
    8, 0, 8,
    0, 8, 0
  ]
)

HumanExplosion.grid.append(
  [
    0, 0, 0,
    0, 0, 0,
    0, 0, 0
  ]
)



#DotZerk Human Death
HumanExplosion2 = LED.ColorAnimatedSprite(h=0, v=0, name="HumanExplosion", width=3, height=3, frames=8, framerate=1,grid=[])
HumanExplosion2.grid.append(
  [
    0, 0, 0,
    0, 5, 0,
    0, 0, 0
  ]
)
HumanExplosion2.grid.append(
  [
    0, 5, 0,
    5, 6, 5,
    0, 5, 0
  ]
)
HumanExplosion2.grid.append(
  [
    0, 6, 0,
    6, 7, 6,
    0, 6, 0
  ]
)
HumanExplosion2.grid.append(
  [
    0, 7, 0,
    7, 8, 7,
    0, 7, 0
  ]
)
HumanExplosion2.grid.append(
  [
    0, 8, 0,
    8,20, 8,
    0, 8, 0
  ]
)

HumanExplosion2.grid.append(
  [
    0,20, 0,
   20, 0,20,
    0,20, 0
  ]
)

HumanExplosion2.grid.append(
  [
    5, 0, 5,
    0, 0, 0,
    5, 0, 5
  ]
)

HumanExplosion2.grid.append(
  [
    0, 0, 0,
    0, 0, 0,
    0, 0, 0
  ]
)


DotZerkRobot = LED.ColorAnimatedSprite(h=0, v=0, name="Robot", width=10, height=8, frames=9, framerate=1,grid=[])
DotZerkRobot.grid.append(
  [
    0, 0, 0, 6, 6, 6, 6, 0, 0, 0,
    0, 0, 6, 8, 1, 6, 6, 6, 0, 0,
    0, 6, 6, 6, 6, 6, 6, 6, 6, 0,
    0, 6, 0, 6, 6, 6, 6, 0, 6, 0,
    0, 6, 0, 6, 6, 6, 6, 0, 6, 0,
    0, 0, 0, 6, 6, 6, 6, 0, 0, 0,
    0, 0, 0, 6, 0, 0, 6, 0, 0, 0,
    0, 0, 6, 6, 0, 0, 6, 6, 0, 0

  ]
)
DotZerkRobot.grid.append(
  [
    0, 0, 0, 6, 6, 6, 6, 0, 0, 0,
    0, 0, 6, 1, 8, 6, 6, 6, 0, 0,
    0, 6, 6, 6, 6, 6, 6, 6, 6, 0,
    0, 6, 0, 6, 6, 6, 6, 0, 6, 0,
    0, 6, 0, 6, 6, 6, 6, 0, 6, 0,
    0, 0, 0, 6, 6, 6, 6, 0, 0, 0,
    0, 0, 0, 6, 0, 0, 6, 0, 0, 0,
    0, 0, 6, 6, 0, 0, 6, 6, 0, 0

  ]
)
DotZerkRobot.grid.append(
  [
    0, 0, 0, 6, 6, 6, 6, 0, 0, 0,
    0, 0, 6, 6, 1, 8, 6, 6, 0, 0,
    0, 6, 6, 6, 6, 6, 6, 6, 6, 0,
    0, 6, 0, 6, 6, 6, 6, 0, 6, 0,
    0, 6, 0, 6, 6, 6, 6, 0, 6, 0,
    0, 0, 0, 6, 6, 6, 6, 0, 0, 0,
    0, 0, 0, 6, 0, 0, 6, 0, 0, 0,
    0, 0, 6, 6, 0, 0, 6, 6, 0, 0

  ]
)
DotZerkRobot.grid.append(
  [
    0, 0, 0, 6, 6, 6, 6, 0, 0, 0,
    0, 0, 6, 6, 6, 1, 8, 6, 0, 0,
    0, 6, 6, 6, 6, 6, 6, 6, 6, 0,
    0, 6, 0, 6, 6, 6, 6, 0, 6, 0,
    0, 6, 0, 6, 6, 6, 6, 0, 6, 0,
    0, 0, 0, 6, 6, 6, 6, 0, 0, 0,
    0, 0, 0, 6, 0, 0, 6, 0, 0, 0,
    0, 0, 6, 6, 0, 0, 6, 6, 0, 0

  ]
)


DotZerkRobot.grid.append(
  [
    0, 0, 0, 6, 6, 6, 6, 0, 0, 0,
    0, 0, 6, 6, 6, 1, 8, 6, 0, 0,
    0, 6, 6, 6, 6, 6, 6, 6, 6, 0,
    0, 6, 0, 6, 6, 6, 6, 0, 6, 0,
    0, 6, 0, 6, 6, 6, 6, 0, 6, 0,
    0, 0, 0, 6, 6, 6, 6, 0, 0, 0,
    0, 0, 0, 6, 0, 0, 6, 0, 0, 0,
    0, 0, 6, 6, 0, 0, 6, 6, 0, 0

  ]
)

DotZerkRobot.grid.append(
  [
    0, 0, 0, 6, 6, 6, 6, 0, 0, 0,
    0, 0, 6, 6, 6, 8, 1, 6, 0, 0,
    0, 6, 6, 6, 6, 6, 6, 6, 6, 0,
    0, 6, 0, 6, 6, 6, 6, 0, 6, 0,
    0, 6, 0, 6, 6, 6, 6, 0, 6, 0,
    0, 0, 0, 6, 6, 6, 6, 0, 0, 0,
    0, 0, 0, 6, 0, 0, 6, 0, 0, 0,
    0, 0, 6, 6, 0, 0, 6, 6, 0, 0

  ]
)


DotZerkRobot.grid.append(
  [
    0, 0, 0, 6, 6, 6, 6, 0, 0, 0,
    0, 0, 6, 6, 8, 1, 6, 6, 0, 0,
    0, 6, 6, 6, 6, 6, 6, 6, 6, 0,
    0, 6, 0, 6, 6, 6, 6, 0, 6, 0,
    0, 6, 0, 6, 6, 6, 6, 0, 6, 0,
    0, 0, 0, 6, 6, 6, 6, 0, 0, 0,
    0, 0, 0, 6, 0, 0, 6, 0, 0, 0,
    0, 0, 6, 6, 0, 0, 6, 6, 0, 0

  ]
)


DotZerkRobot.grid.append(
  [
    0, 0, 0, 6, 6, 6, 6, 0, 0, 0,
    0, 0, 6, 8, 1, 6, 6, 6, 0, 0,
    0, 6, 6, 6, 6, 6, 6, 6, 6, 0,
    0, 6, 0, 6, 6, 6, 6, 0, 6, 0,
    0, 6, 0, 6, 6, 6, 6, 0, 6, 0,
    0, 0, 0, 6, 6, 6, 6, 0, 0, 0,
    0, 0, 0, 6, 0, 0, 6, 0, 0, 0,
    0, 0, 6, 6, 0, 0, 6, 6, 0, 0

  ]
)

DotZerkRobot.grid.append(
  [
    0, 0, 0, 6, 6, 6, 6, 0, 0, 0,
    0, 0, 6, 8, 1, 6, 6, 6, 0, 0,
    0, 6, 6, 6, 6, 6, 6, 6, 6, 0,
    0, 6, 0, 6, 6, 6, 6, 0, 6, 0,
    0, 6, 0, 6, 6, 6, 6, 0, 6, 0,
    0, 0, 0, 6, 6, 6, 6, 0, 0, 0,
    0, 0, 0, 6, 0, 0, 6, 0, 0, 0,
    0, 0, 6, 6, 0, 0, 6, 6, 0, 0,

  ]
)




DotZerkRobotWalking = LED.ColorAnimatedSprite(h=0, v=0, name="Robot", width=10, height=8, frames=2, framerate=1,grid=[])
DotZerkRobotWalking.grid.append(
  [
    0, 0, 0, 6, 6, 6, 6, 0, 0, 0,
    0, 0, 6,14,14, 6, 6, 6, 0, 0,
    0, 6, 6, 6, 6, 6, 6, 6, 6, 0,
    0, 6, 0, 6, 6, 6, 6, 0, 6, 0,
    0, 6, 0, 6, 6, 6, 6, 0, 6, 0,
    0, 0, 0, 6, 6, 6, 6, 0, 0, 0,
    0, 0, 0, 6, 0, 0, 6, 0, 0, 0,
    0, 0, 6, 6, 0, 6, 6, 0, 0, 0,

  ]
)
DotZerkRobotWalking.grid.append(
  [
    0, 0, 0, 6, 6, 6, 6, 0, 0, 0,
    0, 0, 6,14,14, 6, 6, 6, 0, 0,
    0, 6, 6, 6, 6, 6, 6, 6, 6, 0,
    0, 6, 0, 6, 6, 6, 6, 0, 6, 0,
    0, 6, 0, 6, 6, 6, 6, 0, 6, 0,
    0, 0, 0, 0, 6, 6, 0, 0, 0, 0,
    0, 0, 0, 0, 6, 6, 0, 0, 0, 0,
    0, 0, 0, 6, 6, 6, 0, 0, 0, 0

  ]
)


DotZerkRobotWalkingSmall = LED.ColorAnimatedSprite(h=0, v=0, name="Robot", width=9, height=5, frames=4, framerate=1,grid=[])
DotZerkRobotWalkingSmall.grid.append(
  [
   0, 0, 0,10,10,10,10, 0, 0,
   0, 0,10, 7, 7,10,10,10, 0,
   0, 0,10,10,10,10,10,10, 0,
   0, 0,10, 0, 0, 0, 0,10, 0,
   0, 10,10, 0, 0, 0,10,10, 0

  ]
)
DotZerkRobotWalkingSmall.grid.append(
  [
   0, 0, 0,10,10,10,10, 0, 0,
   0, 0,10, 7, 7,10,10,10, 0,
   0, 0,10,10,10,10,10,10, 0,
   0, 0, 0,10, 0, 0,10, 0, 0,
   0, 0,10,10, 0,10,10, 0, 0,

  ]
)

DotZerkRobotWalkingSmall.grid.append(
  [
   0, 0, 0,10,10,10,10, 0, 0,
   0, 0,10, 7, 7,10,10,10, 0,
   0, 0,10,10,10,10,10,10, 0,
   0, 0, 0, 0,10,10, 0, 0, 0,
   0, 0, 0,10,10,10, 0, 0, 0,

  ]
)
DotZerkRobotWalkingSmall.grid.append(
  [
   0, 0, 0,10,10,10,10, 0, 0,
   0, 0,10, 7, 7,10,10,10, 0,
   0, 0,10,10,10,10,10,10, 0,
   0, 0, 0,10, 0, 0,10, 0, 0,
   0, 0,10,10, 0,10,10, 0, 0,

  ]
)






ChickenRunning = LED.ColorAnimatedSprite(h=0, v=0, name="Chicken", width=8, height=8, frames=4, framerate=1,grid=[])
ChickenRunning.grid.append(
  [
    0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 5, 0, 0, 0, 0, 0,
    0,17, 2, 0, 0, 0, 0, 0,
    0, 0, 5, 2, 0, 2, 2, 0,
    0, 0, 0, 2, 2, 2, 0, 0,
    0, 0, 0, 0,22, 0, 0, 0,
    0, 0, 0,22, 0,21, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0

  ]
)

ChickenRunning.grid.append(
  [
    0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 5, 0, 0, 0, 0, 0,
    0,17, 2, 0, 0, 0, 0, 0,
    0, 0, 5, 2, 0, 2, 2, 0,
    0, 0, 0, 2, 2, 2, 0, 0,
    0, 0, 0, 0,22, 0, 0, 0,
    0, 0, 0, 0,22, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0

  ]
)

ChickenRunning.grid.append(
  [
    0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 5, 0, 0, 0, 0, 0,
    0,17, 2, 0, 0, 0, 0, 0,
    0, 0, 5, 2, 0, 2, 2, 0,
    0, 0, 0, 2, 2, 2, 0, 0,
    0, 0, 0, 0,22, 0, 0, 0,
    0, 0, 0,21, 0,22, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0

  ]
)


ChickenRunning.grid.append(
  [
    0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 5, 0, 0, 0, 0, 0,
    0,17, 2, 0, 0, 0, 0, 0,
    0, 0, 5, 2, 0, 2, 2, 0,
    0, 0, 0, 2, 2, 2, 0, 0,
    0, 0, 0, 0,22, 0, 0, 0,
    0, 0, 0, 0,22, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0

  ]
)







WormChasingChicken = LED.ColorAnimatedSprite(h=0, v=0, name="Chicken", width=24, height=8, frames=4, framerate=1,grid=[])
WormChasingChicken.grid.append(
  [
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0,17, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 5, 2, 0, 2, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 2, 2, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0,22, 0, 0, 0, 0, 0, 0, 0,17,17,17,17,17,17,17,17, 0, 0, 0, 0,
    0, 0, 0,22, 0,21, 0, 0, 0, 0, 0, 0,17,17,17,17,17,17,17,17, 0, 0, 0, 0,

  ]
)

WormChasingChicken.grid.append(
  [
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0,17, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 5, 2, 0, 2, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 2, 2, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,17,17, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0,22, 0, 0, 0, 0, 0, 0, 0, 0,17,17,17,17,17,17,17, 0, 0, 0, 0,
    0, 0, 0, 0,22, 0, 0, 0, 0, 0, 0, 0, 0,17,17,17, 0, 0,17,17, 0, 0, 0, 0,

  ]
)

WormChasingChicken.grid.append(
  [
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0,17, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 5, 2, 0, 2, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0,17,17, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 2, 2, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,17,17, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0,22, 0, 0, 0, 0, 0, 0, 0, 0, 0,17,17, 0, 0,17,17, 0, 0, 0, 0,
    0, 0, 0,21, 0,22, 0, 0, 0, 0, 0, 0, 0, 0,17,17, 0, 0,17,17, 0, 0, 0, 0

  ]
)


WormChasingChicken.grid.append(
  [
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0,17, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 5, 2, 0, 2, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 2, 2, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,17,17, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0,22, 0, 0, 0, 0, 0, 0, 0, 0,17,17,17,17,17,17,17, 0, 0, 0, 0,
    0, 0, 0, 0,22, 0, 0, 0, 0, 0, 0, 0, 0,17,17,17, 0, 0,17,17, 0, 0, 0, 0

  ]
)












ChickenChasingWorm = LED.ColorAnimatedSprite(h=0, v=0, name="Chicken", width=16, height=8, frames=4, framerate=1,grid=[])
ChickenChasingWorm.grid.append(
  [
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0,17, 2, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5, 2, 0, 2, 2, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 2, 2, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,22, 0, 0, 0,
    5,17, 5,17,17, 0, 0, 0, 0, 0, 0,22, 0,21, 0, 0

  ]
)

ChickenChasingWorm.grid.append(
  [
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0,17, 2, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5, 2, 0, 2, 2, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 2, 2, 0, 0,
    0, 0, 0, 5, 0, 0, 0, 0, 0, 0, 0, 0,22, 0, 0, 0,
    0, 5,17, 0,17, 0, 0, 0, 0, 0, 0, 0,22, 0, 0, 0

  ]
)

ChickenChasingWorm.grid.append(
  [
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0,17, 2, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5, 2, 0, 2, 2, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 2, 2, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,22, 0, 0, 0,
    5,17, 5,17,17, 0, 0, 0, 0, 0, 0,21, 0,22, 0, 0

  ]
)


ChickenChasingWorm.grid.append(
  [
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0,17, 2, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5, 2, 0, 2, 2, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 2, 2, 0, 0,
    0, 0, 0, 5, 0, 0, 0, 0, 0, 0, 0, 0,22, 0, 0, 0,
    0, 5,17, 0,17, 0, 0, 0, 0, 0, 0, 0,22, 0, 0, 0

  ]
)








    
#------------------------------------------------------------------------------
# Functions                                                                  --
#------------------------------------------------------------------------------

def CheckElapsedTime(seconds):
  global start_time
  elapsed_time = time.time() - start_time
  elapsed_hours, rem = divmod(elapsed_time, 3600)
  elapsed_minutes, elapsed_seconds = divmod(rem, 60)


  m,r = divmod(round(elapsed_seconds), seconds)
  #print("Elapsed Time: {:0>2}:{:0>2}:{:05.2f}".format(int(elapsed_hours),int(elapsed_minutes),elapsed_seconds)," CheckSeconds:",seconds," remainder:",r,end="\r")

  #if (elapsed_seconds >= seconds ):
    #start_time = time.time()
  if (r == 0):
    return 1
  else:
    return 0




def ProcessKeypress(Key):
  #I moved this back into the main program because it was getting awkward trying to start another game
  #from within CommonFunctions

  global MainSleep
  global ScrollSleep
  global NumDots

  # a = animation demo
  # b = Big Clock
  # h = set time - hours minutes
  # q = quit - go on to next game
  # i = show IP address
  # r = reboot
  # p or space = pause 5 seconds
  # c = analog clock for 1 hour
  # t = Clock Only mode
  # 1 - 8 Games
  # 8 = ShowDotZerkRobotTime
  # 0 = ?
  # m = Debug Playfield/Map
    
  if (Key == "p" or Key == " "):
    time.sleep(5)
  elif (Key == "q"):
    LED.ClearBigLED()
    Message = ("EXIT GAME")
    TheBanner = LED.CreateBannerSprite(Message)
    TheBanner.r = 200
    TheBanner.g = 0
    TheBanner.b = 0
    TheBanner.Display((LED.HatWidth / 2) - (TheBanner.width / 2) ,(LED.HatHeight / 2) -3)
    time.sleep(1)


  elif (Key == "r"):
    LED.TheMatrix.Clear
    #ShowScrollingBanner("Reboot!",100,0,0,ScrollSleep * 0.55)
    os.execl(sys.executable, sys.executable, *sys.argv)
  elif (Key == "t"):

    ActivateClockMode(60)

  elif (Key == "c"):
    LED.DrawTinyClock(60)
  elif (Key == "h"):
    SetTimeHHMM()
  elif (Key == "i"):
    ShowIPAddress()
  elif (Key == "a"):
    ShowAllAnimations(ScrollSleep * 0.5)
  elif (Key == "b"):
    ActivateBigClock()


  elif (Key == "1"): 
    PlayPacDot(30)
  elif (Key == "2"):
    PlaySuperWorms()
  elif (Key == "3"):
    PlayWormDot()
  elif (Key == "4"):
    PlaySpaceDot()
  elif (Key == "5"):
    PlayDotZerk()
  elif (Key == "6"):
    PlayDotInvaders()
  elif (Key == "7"):
    LED.TheMatrix.Clear
    PlayRallyDot()
  elif (Key == "8"):
    LED.TheMatrix.Clear
    PlayOutbreak()


    
  elif (Key == "9"):
    LED.TheMatrix.Clear
    ShowDotZerkRobotTime(0.03)
    ShowFrogTime(0.04)
  elif (Key == "0"):
    LED.TheMatrix.Clear
    DrawSnake(random.randint(0,LED.HatWidth-1),random.randint(0,LED.HatWidth-1),255,0,0,random.randint(1,4),.5)
    DrawSnake(random.randint(0,LED.HatWidth-1),random.randint(0,LED.HatWidth-1),0,255,0,random.randint(1,4),.5)
    DrawSnake(random.randint(0,LED.HatWidth-1),random.randint(0,LED.HatWidth-1),0,0,255,random.randint(1,4),.5)
    DrawSnake(random.randint(0,LED.HatWidth-1),random.randint(0,LED.HatWidth-1),125,125,0,random.randint(1,4),.5)
    DrawSnake(random.randint(0,LED.HatWidth-1),random.randint(0,LED.HatWidth-1),0,125,125,random.randint(1,4),.5)
    DrawSnake(random.randint(0,LED.HatWidth-1),random.randint(0,LED.HatWidth-1),125,0,125,random.randint(1,4),.5)
  elif (Key == "+"):
    MainSleep = MainSleep -0.01
    ScrollSleep = ScrollSleep * 0.75
    if (MainSleep <= 0.01):
      MainSleep = 0.01

    #print("Game speeding up")
    #print("MainSleep: ",MainSleep, " ScrollSleep: ",ScrollSleep)
  elif (Key == "-"):
    MainSleep = MainSleep +0.01
    ScrollSleep = ScrollSleep / 0.75
    #print("Game slowing down ")
    #print("MainSleep: ",MainSleep, " ScrollSleep: ",ScrollSleep)







#Draws the dots on the screen  
def DrawDotMatrix(DotMatrix):
  #LED.ClearBigLED()      
  #print ("--DrawLED.DotMatrix--")
  NumDots = 0
  for h in range (0,LED.HatWidth):
    for v in range (0,LED.HatHeight):
      #print ("hv dot: ",h,v,DotMatrix[h][v])
      if (LED.DotMatrix[h][v] == 1):
        NumDots = NumDots + 1
        LED.setpixel(h,v,LED.DotR,LED.DotG,LED.DotB)

  #print ("Dots Found: ",NumDots)
  
  #SendBufferPacket(RemoteDisplay,LED.HatHeight,LED.HatWidth)
  return NumDots;
  

def CountDotsRemaining(DotMatrix):
  NumDots = 0
  lasth   = 0
  lastv   = 0
  for h in range (0,LED.HatWidth):
    for v in range (0,LED.HatHeight):
      #print ("hv dot: ",h,v,DotMatrix[h][v])
      if (DotMatrix[h][v] == 1):
        NumDots = NumDots + 1
        lasth = h
        lastv = v
  if (NumDots == 1 ):
    LED.setpixel(lasth,lastv,LED.DotR,LED.DotG,LED.DotB)
    #FlashDot4(lasth,lastv,.01)
  return NumDots;



  
  
  
def DrawPowerPills(PowerPills):
  global DotMatrix
  global NumDots
  r = 0
  g = 0
  b = 0
  h = randint(0,LED.HatWidth-1)
  v = randint(0,LED.HatHeight-1)
  DotCount = 1
  while DotCount <= PowerPills:
   # print ("Green Pill: ",h," ",v)
    
    if (LED.DotMatrix[h][v] == 1):
      # 0/1/2  empty/dot/pill
      LED.DotMatrix[h][v] = 2
      #r,g,b = LED.getpixel(h,v)
      LED.setpixel(h,v,LED.PillR,LED.PillG,LED.PillB)
      DotCount = DotCount + 1  
      #NumDots = NumDots -1        
    
      #if we overwrite a dot, take one away from count
      #if (r == DotR and g == DotG and b == DotB ):
        #DotMatrix[h][v] = 0
        #NumDots = NumDots -1  
  

    h = randint(0,LED.HatWidth-1)
    v = randint(0,LED.HatHeight-1)
  return;

def DrawDots( NumDots ):
  #Keep track of the dots in a 2D array
  #DotMatrix = [[0 for x in range (LED.HatWidth)] for y in range (LED.HatWidth)] 
  #print("--DrawDots--")

  r = 0
  g = 0
  b = 0

  if (NumDots < 5 or NumDots > (LED.HatWidth * LED.HatHeight)):
    print ("ERROR - NumDots not valid: ",NumDots)
    NumDots = 1000
    
  global DotMatrix
  h = randint(0,LED.HatWidth-1)
  v = randint(0,LED.HatHeight-1)
  DotCount = 1
  Tries    = 0
  while (DotCount <= NumDots and Tries <= 10000):
    Tries = Tries + 1
    if (LED.DotMatrix[h][v] != 1):
      r,g,b = LED.getpixel(h,v)
      print (h,v,r,g,b)
      if (r == 0 and g == 0 and b == 0):
        LED.DotMatrix[h][v] = 1
        LED.FlashDot5(h,v,0.001)
        LED.setpixel(h,v,LED.DotR,LED.DotG,LED.DotB)  
        DotCount = DotCount + 1
    h = randint(0,LED.HatWidth-1)
    v = randint(0,LED.HatHeight-1)
  return LED.DotMatrix; 

 

def DrawMaze():
  LED.setpixel(41,1,LED.WallR,LED.WallG,LED.WallB)
  LED.setpixel(42,2,LED.WallR,LED.WallG,LED.WallB)
  LED.setpixel(43,3,LED.WallR,LED.WallG,LED.WallB)
  LED.setpixel(44,4,LED.WallR,LED.WallG,LED.WallB)
  LED.setpixel(45,5,LED.WallR,LED.WallG,LED.WallB)
  LED.setpixel(46,6,LED.WallR,LED.WallG,LED.WallB)
  LED.setpixel(47,7,LED.WallR,LED.WallG,LED.WallB)

  return; 

  
  
#Not sure why this returns h,v -- will be removed
def DrawGhost(h,v,r,g,b):
   global PowerPillActive
   if PowerPillActive == 1:
     LED.setpixel(h,v,LED.BlueGhostR,LED.BlueGhostG,LED.BlueGhostB)
   else:
     LED.setpixel(h,v,r,g,b)
   return h,v;


def DrawPacDot(h,v,r,g,b):
   LED.setpixel(h,v,r,g,b)
   #unicorn.show()
   return h,v;
 


  
def FollowScanner(h,v,Direction):
  ScanHit = LED.ScanBox(h,v,Direction)
  SanDirection = Direction
    
  ScanH = 0
  ScanV = 0

  #This is a waterfall list
  #top items get priority
  if ScanHit   == "leftblueghost":
    Direction  =  LED.TurnLeft(Direction)
  elif ScanHit == "rightblueghost":
    Direction  =   LED.TurnRight(Direction)
  elif ScanHit == "frontblueghost":
    Direction  =   Direction
  elif ScanHit == "leftpill":
    Direction  =  LED.TurnLeft(Direction)
  elif ScanHit == "frontpill":
    Direction  =  Direction
  elif ScanHit == "rightpill":
    Direction  =   LED.TurnRight(Direction)
  elif ScanHit == "leftdot":
    Direction  = LED.TurnLeft(Direction)
  elif ScanHit == "rightdot":
    print ("Turning for rightdot")
    Direction  =  LED.TurnRight(Direction)
  elif ScanHit == "frontdot":
    Direction  = Direction

  #More complex situations go here
  elif ScanHit == "frontghost":
    Direction  = LED.ReverseDirection(Direction)
  elif ScanHit == "frontwall":
    ScanDirection  = LED.TurnRight(Direction)
    ScanH, ScanV, ScanDirection = LED.CalculateMovement(h,v,ScanDirection)
    ScanHit = LED.ScanDot(ScanH,ScanV)

    if (ScanHit == "empty" or ScanHit == "pill" or ScanHit == "blueghost" or ScanHit == "dot"):
      Direction = ScanDirection
    else:
      ScanDirection  = LED.TurnLeft(Direction)
      ScanH, ScanV, ScanDirection = LED.CalculateMovement(h,v,ScanDirection)
      ScanHit = LED.ScanDot(ScanH,ScanV)
      if (ScanHit == "empty" or ScanHit == "pill" or ScanHit == "blueghost" or ScanHit == "dot"):
        Direction = ScanDirection
      else:
        Direction  = LED.ReverseDirection(Direction)
         

    

            
  
  
  return Direction;
  
  
  


# We need to move the ghost and leave behind the proper colored pixel
  
def MoveGhost(h,v,CurrentDirection,r,g,b):
  global DotMatrix
  item = "NULL"
  #print ("MoveGhost old:",h,v,CurrentDirection)
  
  newh, newv, CurrentDirection = LED.CalculateMovement(h,v,CurrentDirection)
  item = LED.ScanDot(newh,newv)

  #print ("MoveGhost New:",newh,newv,CurrentDirection, item)
  
  #ghosts avoid walls, pills, and other ghosts
  if item == "wall" or item == "pill" or item == "ghost":
    CurrentDirection = randint(1,4)
    newh = h
    newv = v     

  elif item == "empty" or item == "dot":
    LED.setpixel(newh,newv,r,g,b)
    #if where we were coming from is a dot, replace, otherwise put blank
    if (LED.DotMatrix[h][v]==1):
      LED.setpixel(h,v,LED.DotR,LED.DotG,LED.DotB)
    else:
      LED.setpixel(h,v,0,0,0)

  #if item is pacot, don't do anything just sit there
  elif item == "pacdot":
    newh = h
    newv = v     

  elif item == "boundary":    
    CurrentDirection = randint(1,4)
    newh = h
    newv = v     
 
  #unicorn.show()

  #print "After  HVD:",h,v,CurrentDirection
  return newh,newv,CurrentDirection;


def KillGhost(h,v):  
    global Ghost1Alive
    global Ghost1H
    global Ghost1V
    global Ghost2Alive
    global Ghost2H
    global Ghost2V
    global Ghost3Alive
    global Ghost3H
    global Ghost3V
    global Ghost4Alive
    global Ghost4H
    global Ghost4V
    if h == Ghost1H and v == Ghost1V:
      Ghost1Alive = 0
      #print ("Killing Ghost:",Ghost1Alive)
    if h == Ghost2H and v == Ghost2V:
      Ghost2Alive = 0
      #print ("Killing Ghost:",Ghost2Alive)
    if h == Ghost3H and v == Ghost3V:
      Ghost3Alive = 0
      #print ("Killing Ghost:",Ghost3Alive)
    if h == Ghost4H and v == Ghost4V:
      Ghost4Alive = 0
      #print ("Killing Ghost:",Ghost3Alive)







def FindClosestDot(PacDotH,PacDotV,DotMatrix):
  #We want the player car to journey towards the the powerpill or regular dots
  ClosestX     = LED.HatWidth // 2
  ClosestY     = LED.HatHeight // 2
  MinDistance  = 9999
  Distance     = 0
  for x in range(0,LED.HatWidth):
    for y in range(0,LED.HatHeight):
      #Look for alive dots
      #print("DotMatrix[x][y]",x,y,DotMatrix[x][y])
      if (DotMatrix[x][y] == 1):
        Distance = LED.GetDistanceBetweenDots(PacDotH,PacDotV,x,y)
        #print ("Distance: ",Distance, " MinDistance:",MinDistance, "xy:",x,y)
        if (Distance <= MinDistance):
          MinDistance = Distance
          ClosestX = x
          ClosestY = y
      elif (DotMatrix[x][y] == 2 and PowerPillActive == 0):
        Distance = LED.GetDistanceBetweenDots(PacDotH,PacDotV,x,y)
        MinDistance = Distance
        ClosestX = x
        ClosestY = y


    
  #FlashDot5(ClosestX,ClosestY,0.003)
  return ClosestX,ClosestY;


def MovePacDot(h,v,CurrentDirection,r,g,b,DotsEaten):
  global Pacmoves
  global PowerPillActive
  global Ghost1Alive
  global Ghost2Alive
  global Ghost3Alive
  global DotMatrix
  global PacDotScore
  global DotPoints
  global PillPoints
  global BlueGhosePoints
  global Ghost1Alive
  global Ghost2Alive
  global Ghost3Alive
  global Ghost4Alive
  global MovesSinceEatingGhost     
  
  
  Pacmoves = Pacmoves + 1
  item = "NULL"

  newh, newv, CurrentDirection = LED.CalculateMovement(h,v,CurrentDirection)
  item = LED.ScanDot(newh,newv)

  #print ("MovePacDot item:",item)
  if item == "dot":
    DotsEaten = DotsEaten + 1
    LED.MovesSinceSmartSeekFlip = 0
    LED.PacDotSmarkSeekMode = 1
    Pacmoves = 0
    PacDotScore = PacDotScore + DotPoints
    LED.setpixel(newh,newv,r,g,b)
    LED.setpixel(h,v,0,0,0)
    LED.DotMatrix[newh][newv] = 0
    
  elif item == "pill":
    Pacmoves = 0
    LED.MovesSinceSmartSeekFlip = 0
    LED.PacDotSmartSeekMode = 1
    PacDotScore = PacDotScore + PillPoints
    LED.setpixel(newh,newv,r,g,b)
    LED.setpixel(h,v,0,0,0)
    LED.DotMatrix[newh][newv] = 0
    PowerPillActive = 1
    
    if Ghost1Alive == 1: DrawGhost(Ghost1H,Ghost1V,LED.Ghost1R,LED.Ghost1G,LED.Ghost1B)
    if Ghost2Alive == 1: DrawGhost(Ghost2H,Ghost2V,LED.Ghost2R,LED.Ghost2G,LED.Ghost2B)
    if Ghost3Alive == 1: DrawGhost(Ghost3H,Ghost3V,LED.Ghost3R,LED.Ghost3G,LED.Ghost3B)
    if Ghost4Alive == 1: DrawGhost(Ghost4H,Ghost4V,LED.Ghost4R,LED.Ghost4G,LED.Ghost4B)
    

  #Pacman needs to leave walls alone
  elif item == "wall":
    Pacmoves = 0
    CurrentDirection = randint(1,4)
    newh = h
    newv = v     
    

    
    
  elif item == "blueghost":
    Pacmoves = 0
    MovesSinceSmartSeekFlip       = 0
    PacDotSmartSeekMode       = 1
    
    PacDotScore = PacDotScore + BlueGhostPoints
    LED.setpixel(newh,newv,r,g,b)
    LED.setpixel(h,v,0,0,0)
    LED.DotMatrix[newh][newv] = 0

    KillGhost(newh,newv)

    
  elif item == "ghost":
    if PowerPillActive == 1:
      KillGhost(newh, newv)
      MovesSinceSmartSeekFlip       = 0
      PacDotSmartSeekMode       = 1
    else:  
      CurrentDirection = LED.TurnLeftOrRight(CurrentDirection)
      #Ghosts scare pacdot, and he goes into dumb mode
      PacDotSmartSeekMode       = 0

    CurrentDirection = CurrentDirection
    newh = h
    newv = v

      
      
  elif item == "empty":
    LED.setpixel(newh,newv,r,g,b)
    LED.setpixel(h,v,0,0,0)
    LED.DotMatrix[newh][newv] = 0

  elif item == "boundary":    
    CurrentDirection = randint(1,4)
    newh = h
    newv = v     


  #print "After  HVD:",h,v,CurrentDirection
  return newh,newv,CurrentDirection,DotsEaten;


  
  
    

  
#--------------------------------------
#--          Light Dot               --
#--------------------------------------



def ScanWorms(h,v):
# I am keeping this simple for now, will remove color checking later
# border
# empty
# wall

  
  global GreenObstacleFadeValue
  global GreenObstacleMinVisible

  Item = ''
  OutOfBounds = LED.CheckBoundary(h,v)
  
  if (OutOfBounds == 1):
    Item = 'border'
  else:
    #FlashDot(h,v,0)
    r,g,b = LED.getpixel(h,v)  
    #print ("rgb scanned:",r,g,b)
    if (r == 0 and g == 0 and b == 0):
      Item = 'EmptyObject'
    
    #wormdot obstacles are green
    #Every time they are scanned, they grow dim and eventually disappear
    elif (r == 0 and g >= GreenObstacleMinVisible and b == 0):
      #print ("Green obstacle found g:,g")  
      g = g - GreenObstacleFadeValue
      if (g < GreenObstacleMinVisible):
        LED.setpixel(h,v,0,0,0)
        Item = 'EmptyObject'
      else:
        LED.setpixel(h,v,0,g,0)
        Item = 'obstacle'
    elif (r == LED.SDLowRedR and g == LED.SDLowRedG and b == LED.SDLowRedB):      
        #setpixel(h,v,0,0,0)
        Item = 'speeduppill'      
    else:
      Item = 'wall'
  #print("Scanned:",Item)
  return Item
    


#This function is for the game where worms hit obstacles
def MoveWorm(Dot):
  h = 0
  v = 0
  Dot.trail.append((Dot.h, Dot.v))

  ItemList = []

  #Scan all around, make decision, move
  ItemList = ScanSuperWormsDirection(Dot.h,Dot.v,Dot.direction)

  
  
  #print('DotName: ', Dot.name, 'hv',Dot.h,Dot.v, ' ', *ItemList, sep='|')
  
  #get possible items, then prioritize

  #The red dot must be hit head on
  #once this happens we erase it and increase the speed
  if (ItemList[3] == 'speeduppill'):
    h,v = LED.CalculateDotMovement(Dot.h,Dot.v,Dot.direction)
    Dot.speed = Dot.speed -1
    Dot.maxtrail = Dot.maxtrail + 1
    if (Dot.speed <= 3):
      Dot.speed = 3
    ItemList[3] = 'EmptyObject'
    #print ("Speed: ",Dot.speed)
    LED.setpixel(h,v,0,0,0)
  
 
  #Red on left
  if (ItemList[1] == 'speeduppill'):
    Dot.direction = LED.TurnLeft(Dot.direction)
    h,v = LED.CalculateDotMovement(Dot.h,Dot.v,Dot.direction)    
    Dot.speed = Dot.speed -1
    Dot.maxtrail = Dot.maxtrail + 1
    if (Dot.speed <= 1):
      Dot.speed = 1
    ItemList[1] = 'EmptyObject'
    #print ("Speed: ",Dot.speed)
    LED.setpixel(h,v,0,0,0)

  elif (ItemList[5] == 'speeduppill'):
    Dot.direction =  LED.TurnRight(Dot.direction)
    h,v = LED.CalculateDotMovement(Dot.h,Dot.v,Dot.direction)    
    Dot.maxtrail = Dot.maxtrail + 1
    Dot.speed = Dot.speed -1
    if (Dot.speed <= 1):
      Dot.speed = 1
    ItemList[5] = 'EmptyObject'
    #print ("Speed: ",Dot.speed)
    LED.setpixel(h,v,0,0,0)

  #empty = move forward
  elif (ItemList[3] == 'EmptyObject'):
    Dot.h, Dot.v = LED.CalculateDotMovement(Dot.h,Dot.v,Dot.direction)

  #This was an accident, but I like it
  #If the worm has a head on collision with the obstacle, it gets stuck and the obstacle
  #fades, almost as if the worm is ` it.  The worm ends up shorter though!  Weird.
  #print ('ItemList[3]:', ItemList[3])
  if ItemList[3]  == 'obstacle':
    #print ("Obstacle hit!  Draining our power!")
    r,g,b = LED.getpixel(h,v)
    if (g > 45):
      r,g,b = FadePixel(r,g,b,1)
      LED.setpixel(h,v,r,g,b)
      
      #I have decided to try moving away from green dot
      Dot.direction = LED.TurnLeftOrRight(Dot.direction)
      Dot.h, Dot.v = LED.CalculateDotMovement(Dot.h,Dot.v,Dot.direction)    
      Dot.speed = Dot.speed +1


    
    
  #if heading to boundary or wall
  elif (ItemList[3] == 'wall' or ItemList[3] == 'border' or ItemList[3] == 'obstacle'):
    if (ItemList[1] == 'EmptyObject' and ItemList[5] == 'EmptyObject'):
      #print ("both empty picking random direction")
      Dot.direction = LED.TurnLeftOrRight(Dot.direction)
      Dot.h, Dot.v = LED.CalculateDotMovement(Dot.h,Dot.v,Dot.direction)
    elif (ItemList[1] == 'EmptyObject' and ItemList[5] != 'EmptyObject'):
      #print ("left empty turning left")
      Dot.direction = LED.TurnLeft(Dot.direction)
      Dot.h, Dot.v = LED.CalculateDotMovement(Dot.h,Dot.v,Dot.direction)
    elif (ItemList[5] == 'EmptyObject' and ItemList[1] != 'EmptyObject'):
      #print ("left empty turning right")
      Dot.direction =  LED.TurnRight(Dot.direction)
      Dot.h, Dot.v = LED.CalculateDotMovement(Dot.h,Dot.v,Dot.direction)
    
    
    else:
      #print ("you died")
      ReverseOrDie(Dot)
      #Dot.alive = 0
      #Dot.trail.append((Dot.h, Dot.v))
      #Dot.EraseTrail('forward','flash')
  
  return Dot



  
  
def ScanSuperWorms(h,v):
# I am keeping this simple for now, will remove color checking later
# border
# empty
# wall

  
  global GreenObstacleFadeValue
  global GreenObstacleMinVisible

  Item = ''
  OutOfBounds = LED.CheckBoundary(h,v)
  
  if (OutOfBounds == 1):
    Item = 'border'
  else:
    #FlashDot(h,v,0)
    r,g,b = LED.getpixel(h,v)  
    #print ("rgb scanned:",r,g,b)
    if (r == 0 and g == 0 and b == 0):
      Item = 'EmptyObject'
    
    else:
      Item = 'wall'
  
  return Item
    
    
def ScanSuperWormsDirection(h,v,direction):
  ScanDirection = 0
  ScanH         = 0
  ScanV         = 0
  Item          = ''
  ItemList      = ['NULL']
  
  # We will scan 7 spots around the dot
  #  LF FF FR
  #  LL    RR 
  #  BL    BR
  #
  #  2  3  4
  #  1     5
  #  7     6
  
  #Scanning Probe
  #Turn left move one + SCAN
  #Turn Right move one + SCAN
  #Turn Right Move one + SCAN 
  #Move one + SCAN 
  #Turn Right Move one + SCAN 
  
  
  #LL 1
  ScanDirection = LED.TurnLeft(direction)
  ScanH, ScanV = LED.CalculateDotMovement(h,v,ScanDirection)
  Item = ScanSuperWorms(ScanH,ScanV)
  ItemList.append(Item)
  
  #LF 2
  ScanDirection =  LED.TurnRight(ScanDirection)
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = ScanSuperWorms(ScanH,ScanV)
  ItemList.append(Item)
  
  #FF 3
  ScanDirection =  LED.TurnRight(ScanDirection)
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = ScanSuperWorms(ScanH,ScanV)
  ItemList.append(Item)
  
  #FR 4
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = ScanSuperWorms(ScanH,ScanV)
  ItemList.append(Item)
  
  #RR 5
  ScanDirection =  LED.TurnRight(ScanDirection)
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = ScanSuperWorms(ScanH,ScanV)
  ItemList.append(Item)

  #BR 6
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = ScanSuperWorms(ScanH,ScanV)
  ItemList.append(Item)


  #BL 7
  ScanDirection =  LED.TurnRight(ScanDirection)
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = ScanSuperWorms(ScanH,ScanV)
  ItemList.append(Item)
  return ItemList;


def FadePixel(r,g,b,fadeval):
  newr = r - fadeval
  newg = g - fadeval
  newb = b - fadeval
  
  if (newr < 0):
    newr = 0
  if (newg < 0):
    newg = 0
  if (newb < 0):
    newb = 0

  return r,g,b;
  

#This one is for the game where there are NOT obstacles, just long worms  
def MoveSuperWorm(Dot):
  h = 0
  v = 0
  Dot.trail.append((Dot.h, Dot.v))
  Dot.score = Dot.score + 1
  ItemList = []

  #Scan all around, make decision, move
  ItemList = ScanSuperWormsDirection(Dot.h,Dot.v,Dot.direction)


  #  2  3  4
  #  1     5
  #  7     6

  # If there way is clear, but another worm is in 6 or 7, cut them off
  if (ItemList[2] == 'EmptyObject' and
      ItemList[3] == 'EmptyObject' and
      ItemList[4] == 'EmptyObject'):


    if (ItemList[1] == 'EmptyObject' and ItemList[7] == 'wall'):
      #print ("sharp turn to left")
      Dot.direction = LED.TurnLeft(Dot.direction)
      Dot.h, Dot.v = LED.CalculateDotMovement(Dot.h,Dot.v,Dot.direction)

    elif (ItemList[5] == 'EmptyObject' and ItemList[6] == 'wall'):
      #print ("sharp turn to right")
      Dot.direction = LED.TurnRight(Dot.direction)
      Dot.h, Dot.v = LED.CalculateDotMovement(Dot.h,Dot.v,Dot.direction)
    else:
      #print ("keep moving forward no sharp turns")
      Dot.h, Dot.v = LED.CalculateDotMovement(Dot.h,Dot.v,Dot.direction)
      
  #if heading to boundary or wall
  elif (ItemList[3] == 'wall' or ItemList[3] == 'border' or ItemList[3] == 'obstacle'):
    if (ItemList[1] == 'EmptyObject' and ItemList[5] == 'EmptyObject'):
      #print ("both empty picking random direction")
      Dot.direction = LED.TurnLeftOrRight(Dot.direction)
      Dot.h, Dot.v = LED.CalculateDotMovement(Dot.h,Dot.v,Dot.direction)
    elif (ItemList[1] == 'EmptyObject' and ItemList[5] != 'EmptyObject'):
      #print ("left empty turning left")
      Dot.direction = LED.TurnLeft(Dot.direction)
      Dot.h, Dot.v = LED.CalculateDotMovement(Dot.h,Dot.v,Dot.direction)
    elif (ItemList[5] == 'EmptyObject' and ItemList[1] != 'EmptyObject'):
      #print ("left empty turning right")
      Dot.direction =  LED.TurnRight(Dot.direction)
      Dot.h, Dot.v = LED.CalculateDotMovement(Dot.h,Dot.v,Dot.direction)
    else:
      ReverseOrDie(Dot)
    

  
  elif (ItemList[3] == 'EmptyObject'):
    #print ("keep moving forward")
    Dot.h, Dot.v = LED.CalculateDotMovement(Dot.h,Dot.v,Dot.direction)

  else:
    print ("you died")
    ReverseOrDie(Dot)
      #Dot.alive = 0
      #Dot.trail.append((Dot.h, Dot.v))
      #Dot.EraseTrail('forward','flash')
  
    #If dead, erase.  This is only for display purposes.  Other logic will
    #handle the death of the superworm
    if (Dot.alive == 0):
      Dot.Kill()
  return Dot

  

  


def ReverseOrDie(WormDot):

  #We need to tell what direction the trail is facing  
  h,v   = WormDot.trail[0] #the very back of the trail
  h1,v1 = WormDot.trail[1]
  NewDirection = 0
  if (v1 < v):
    NewDirection = 3
  elif (v1 > v):
    NewDirection = 1
  elif (h1 < h):
    NewDirection = 2
  elif (h1 > h):
    NewDirection = 4

  #Scan behind of the superworm
  ItemList     = ScanSuperWormsDirection(h,v,NewDirection)

  #print (ItemList)
  if (ItemList[3] == 'EmptyObject'):
    WormDot.ReverseWorm()
    print ("** Full Reverse! **")
    #LED.ShowScreenArray()    
  else:
    print ("** worm death imminent ** ")
    WormDot.Kill()

  return    

  
  



def CreateSuperWormMap(MapLevel):
  
  
  print ("CreateSuperWorm Map: ",MapLevel)

  #Create maze 0
  SuperWormMap = []
  SuperWormMap.append(LED.Maze(
    h      = 0,
    v      = 0,
    width  = 64, 
    height = 32
    )
  )
  SuperWormMap[0].ColorList = {
    ' ' : (0,0,0),
    'O' : LED.WallRGB,
    '-' : (0,50,0),
    '|' : LED.WallRGB
  }


  SuperWormMap[0].TypeList = {
    ' ' : 'EmptyObject',
    'O' : 'wall',
    '-' : 'wall',
    '|' : 'wall'

  }



  SuperWormMap[0].map= (
    #0.........1.........2.........3.........4.........5.........6...64    
    "                ------------------------------------------------", #0  
    "                -                                              -",
    "                -                                              -",
    "                -                                              -",
    "                -                                              -",
    "                -                                              -",
    "                -                                              -",
    "                -                                              -",
    "                -                                              -",
    "                -                                              -",
    "                -                                              -", #10
    "                -                                              -",
    "                -                                              -",
    "                -                                              -",
    "                -                                              -",
    "                -                                              -",
    "                -                                              -",
    "                -                                              -",
    "                -                                              -",
    "                -                                              -",
    "                -                                              -", #20
    "                -                                              -",
    "                -                                              -",
    "                -                                              -",
    "                -                                              -",
    "                -                                              -",
    "                -------------------------------------------------",
    "                                                                 ",
    "                                                                 ",
    "                                                                 ",
    "                                                                 ", #30
    "                                                                 ",
    "OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO" #32
  )

#Create maze 1
  SuperWormMap.append(LED.Maze(
    h      = 0,
    v      = 0,
    width  = 64, 
    height = 32
    )
  )
  SuperWormMap[1].ColorList = {
    ' ' : (0,0,0),
    '`' : (1,0,0),
    'O' : (100,100,100),
    '-' : (30,0,75),
    '|' : LED.WallRGB,
    '.' : (  0,  5,225),
    ',' : ( 25, 15,  0),
    'x' : (100,  0,  0),
    '#' : (200,  0,  0),
    'X' : (  0,  0,220),
    'p' : (LED.MedPink),
    'c' : (LED.MedCyan),
    'o' : (LED.MedOrange),
    'b' : (LED.MedBlue),
    'g' : (LED.MedGreen),
    'y' : (LED.MedYellow),
    'r' : (LED.LowRed),
    'R' : (LED.MedRed),
  }


  SuperWormMap[1].TypeList = {
    ' ' : 'EmptyObject',
    '`' : 'wall',
    'O' : 'wall',
    '-' : 'wall',
    '|' : 'wall',
    '.' : 'wall',
    ',' : 'wall',
    'x' : 'wall',
    '#' : 'wall',
    'X' : 'wall',
    'p' : 'wall',
    'c' : 'wall',
    'o' : 'wall',
    'b' : 'wall',
    'g' : 'wall',
    'y' : 'wall',
    'r' : 'wall',
    'R' : 'wall'

  }



  SuperWormMap[1].map= (
    #0.........1.........2.........3.........4.........5.........6...64    
    "                `                                               ", #0  
    "                `                                               ",
    "                `                                               ",
    "                `                                               ",
    "                `                                               ",
    "                `                                               ",
    "                `                                               ",
    "                `                                               ",
    "                `                                               ",
    "                `                                               ",
    "                `                                               ", #10
    "                `                                               ",
    "                `                                               ",
    "                `                                               ",
    "                `                                               ",
    "                `                                               ",
    "                `                                               ",
    "                `                                               ",
    "                `                                               ",
    "                `                                               ",
    "                `                                               ", #20
    "                `                                               ",
    "                `                                               ",
    "                `                                               ",
    "                `                                               ",
    "                `                                               ",
    "                ````````````````````````````````````````````````",
    "                                                                ",
    "                                                                ",
    "                                                                ",
    "                                                                ", #30
    "                                                                ",
    "OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO" #32
  )



  #Create maze 2
  SuperWormMap.append(LED.Maze(
    h      = 0,
    v      = 0,
    width  = 64, 
    height = 32
    )
  )
  SuperWormMap[2].ColorList = {
    ' ' : (0,0,0),
    '`' : (0,1,0),
    'O' : (0,0,55),
    '-' : (0,0,50),
    '|' : LED.WallRGB,
    '.' : ( 50,  0,  0),
    'o' : (200,  0,  0),
    'x' : (100,  0,  0),
    '#' : (220,  0,  0),
  }


  SuperWormMap[2].TypeList = {
    ' ' : 'EmptyObject',
    '`' : 'EmptyObject',
    'O' : 'wall',
    '-' : 'wall',
    '|' : 'wall',
    '.' : 'wall',
    'x' : 'wall',
    '#' : 'wall'

  }



  SuperWormMap[2].map= (
    #0.........1.........2.........3.........4.........5.........6...64    
    "                ````````````````````````````````````````````````", #0  
    "                `                                              `",
    "                `                                              `",
    "                `                                              `",
    "                `                     xx                       `",
    "                `                    x##x                      `",
    "                `             xxxxxxxxxxxxxxxxxx               `",
    "                `              x..............x                `",
    "                `              x..............x                `",
    "                `             xxxxxxxxxxxxxxxxxx               `",
    "                `              x..x        x..x                `", #10
    "                `              x..x        x..x                `",
    "                `              x..x        x..x                `",
    "                `              xxxx        xxxx                `",
    "                `              x..x        x..x                `",
    "                `              x..x        x..x                `",
    "                `              x..x        x..x                `",
    "                `              x..x        x..x                `",
    "                `              x...x      x...x                `",
    "                `              xxxxxx    xxxxxx                `",
    "                `                                              `", #20
    "                `                                              `",
    "                `                                              `",
    "                `                                              `",
    "                `                                              `",
    "                `                                              `",
    "                ````````````````````````````````````````````````",
    "                                                                ",
    "                                                                ",
    "                                                                ",
    "                                                                ", #30
    "                                                                ",
    "OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO" #32
  )
  

#Create maze 3
  SuperWormMap.append(LED.Maze(
    h      = 0,
    v      = 0,
    width  = 64, 
    height = 32
    )
  )
  SuperWormMap[3].ColorList = {
    ' ' : (0,0,0),
    'O' : (0,0,55),
    '-' : (70,0, 0),
    '|' : LED.WallRGB,
    '.' : ( 50,  0,  0),
    'o' : (200,  0,  0),
    'x' : (100,  0,  0),
    '#' : (200,  0,  0),
    'X' : (  0,  0,220)
  }


  SuperWormMap[3].TypeList = {
    ' ' : 'EmptyObject',
    'O' : 'wall',
    '-' : 'wall',
    '|' : 'wall',
    '.' : 'wall',
    'x' : 'wall',
    '#' : 'wall',
    'X' : 'wall'

  }



  SuperWormMap[3].map= (
    #0........1.........2.........3.........4.........5.........6...64    
    "                    ----------------------------------------    ", #0  
    "                   -                                        -   ",
    "                  -                                          -  ",
    "                 -                                            - ",
    "                -                     xx                       -",
    "                -                    xXXx                      -",
    "                -             xxxxxxxxxxxxxxxxxx               -",
    "                -              x..............x                -",
    "                -              x..............x                -",
    "                -             xxxxxxxxxxxxxxxxxx               -",
    "                -              x..x        x..x                -", #10
    "                -              x..x        x..x                -",
    "                -              x..x        x..x                -",
    "                -              xxxx        xxxx                -",
    "                -              x..x        x..x                -",
    "                -              x..x        x..x                -",
    "                -              x..x        x..x                -",
    "                -              x..x        x..x                -",
    "                -              x...x      x...x                -",
    "                -              xxxxxx    xxxxxx                -",
    "                -                                              -", #20
    "                -                                              -",
    "                -                                              -",
    "                 -                                            - ",
    "                  -                                          -  ",
    "                   -                                        -   ",
    "                    ----------------------------------------    ",
    "                                                                ",
    "                                                                ",
    "                                                                ",
    "                                                                ", #30
    "                                                                ",
    "OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO" #32
  )
  


#Create maze 4
  SuperWormMap.append(LED.Maze(
    h      = 0,
    v      = 0,
    width  = 64, 
    height = 32
    )
  )
  SuperWormMap[4].ColorList = {
    ' ' : (0,0,0),
    '`' : (0,1,0),
    'O' : (0,0,55),
    '-' : (0,0,50),
    '|' : LED.WallRGB,
    '.' : ( 60, 35,  0),
    ',' : ( 25, 15,  0),
    'x' : (100,  0,  0),
    '#' : (200,  0,  0),
    'X' : (  0,  0,220),
    'p' : (LED.MedPink),
    'c' : (LED.MedCyan),
    'o' : (LED.MedOrange),
    'b' : (LED.MedBlue),
    'g' : (LED.MedGreen),
    'y' : (LED.MedYellow)
  }


  SuperWormMap[4].TypeList = {
    ' ' : 'EmptyObject',
    '`' : 'EmptyObject',
    'O' : 'wall',
    '-' : 'wall',
    '|' : 'wall',
    '.' : 'wall',
    ',' : 'wall',
    'x' : 'wall',
    '#' : 'wall',
    'X' : 'wall',
    'p' : 'wall',
    'c' : 'wall',
    'o' : 'wall',
    'b' : 'wall',
    'g' : 'wall',
    'y' : 'wall'

  }



  SuperWormMap[4].map= (
    #0.........1.........2.........3.........4.........5.........6...64    
    "                ````````````````````````````````````````````````", #0  
    "                `                                              `",
    "                `                       ,                      `",
    "                `                     . , .                    `",
    "                `                 ...,.,.., . ,                `",
    "                `               . .,. . ., .,. .               `",
    "                `             yp ., .,. . . .,. yp             `",
    "                `             yppp ,,..,.,.,. yyyp             `",
    "                `             ypppcc. . , . ggyyyp             `",
    "                `             ypppccco,.,,bgggyyyp             `",
    "                `             ypppcccooobbbgggyyyp             `", #10
    "                `             ypppcccooobbbgggyyyp             `",
    "                `             ypppcccooobbbgggyyyp             `",
    "                `             ypppcccooobbbgggyyyp             `",
    "                `             ypppcccooobbbgggyyyp             `",
    "                `             ypppcccooobbbgggyyyp             `",
    "                `             ypppcccooobbbgggyyyp             `",
    "                `             ypppcccooobbbgggyyyp             `",
    "                `               ppcccooobbbgggyy               `",
    "                `                  ccooobbbgg                  `",
    "                `                     oobb                     `", #20
    "                `                                              `",
    "                `                                              `",
    "                `                                              `",
    "                `                                              `",
    "                `                                              `",
    "                ````````````````````````````````````````````````",
    "                                                                ",
    "                                                                ",
    "                                                                ",
    "                                                                ", #30
    "                                                                ",
    "OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO" #32
  )
  
#Create maze 5
  SuperWormMap.append(LED.Maze(
    h      = 0,
    v      = 0,
    width  = 64, 
    height = 32
    )
  )
  SuperWormMap[5].ColorList = {
    ' ' : (0,0,0),
    '`' : (0,1,0),
    'O' : (0,0,55),
    '-' : (30,0,75),
    '|' : LED.WallRGB,
    '.' : ( 60, 35,  0),
    ',' : ( 25, 15,  0),
    'x' : (100,  0,  0),
    '#' : (200,  0,  0),
    'X' : (  0,  0,220),
    'p' : (LED.MedPink),
    'c' : (LED.MedCyan),
    'o' : (LED.MedOrange),
    'b' : (LED.MedBlue),
    'g' : (LED.MedGreen),
    'y' : (LED.MedYellow)
  }


  SuperWormMap[5].TypeList = {
    ' ' : 'EmptyObject',
    '`' : 'wall',
    'O' : 'wall',
    '-' : 'wall',
    '|' : 'wall',
    '.' : 'wall',
    ',' : 'wall',
    'x' : 'wall',
    '#' : 'wall',
    'X' : 'wall',
    'p' : 'wall',
    'c' : 'wall',
    'o' : 'wall',
    'b' : 'wall',
    'g' : 'wall',
    'y' : 'wall'

  }




  SuperWormMap[5].map= (
    #0.........1.........2.........3.........4.........5.........6...64    
    "                ```````````````-------------------``````````````", #0  
    "                ``````````````-ooooooooooooooooooo-`````````````",
    "                ``````````````-o---------------- o-`````````````",
    "                ``````````````-o-               -o-`````````````",
    "                ``````````````-o-               -o-`````````````",
    "                `-------------o-                 -o------------`",
    "                -ooooooooooooo-                   -oooooooooooo-",
    "                -o------------                     -----------o-",
    "                -o-                                          -o-",
    "                -o-                                          -o-",
    "                -o-                                          -o-", #10
    "                -o-                                          -o-",
    "                -o-                                          -o-",
    "                -o-                                          -o-",
    "                -o-                                          -o-",
    "                -o-                                          -o-",
    "                -o-                                          -o-",
    "                -o-                                          -o-",
    "                -o-                                          -o-",
    "                -o------------                     -----------o-",
    "                -ooooooooooooo-                   -oooooooooooo-", #20
    "                `-------------o-                 -o------------ ",
    "                ``````````````-o-               -o-`````````````",
    "                ``````````````-o-               -o-`````````````",
    "                ``````````````-o-----------------o-`````````````",
    "                ``````````````-ooooooooooooooooooo-`````````````",
    "                ```````````````-------------------``````````````",
    "                                                                ",
    "                                                                ",
    "                                                                ",
    "                                                                ", #30
    "                                                                ",
    "OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO" #32
  )


  # SuperWormMap[4].map= (
    # #0.........1.........2.........3.........4.........5.........6...64    
    # "                ------------------------------------------------", #0  
    # "                -                                              -",
    # "                -                                              -",
    # "                -                                              -",
    # "                -                                              -",
    # "                -                                              -",
    # "                -                                              -",
    # "                -                                              -",
    # "                -                                              -",
    # "                -                                              -",
    # "                -                                              -", #10
    # "                -                                              -",
    # "                -                                              -",
    # "                -                                              -",
    # "                -                                              -",
    # "                -                                              -",
    # "                -                                              -",
    # "                -                                              -",
    # "                -                                              -",
    # "                -                                              -",
    # "                -                                              -", #20
    # "                -                                              -",
    # "                -                                              -",
    # "                -                                              -",
    # "                -                                              -",
    # "                -                                              -",
    # "                ------------------------------------------------",
    # "                                                                ",
    # "                                                                ",
    # "                                                                ",
    # "                                                                ", #30
    # "                                                                ",
    # "OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO" #32
  # )


  
  SuperWormMap[MapLevel].LoadMap()


  return



  
def PlaySuperWorms():
  
  

  #Local variables
  moves      = 0
  Finished   = 'N'
  LevelCount = 0
  HighScore  = 0
  SuperWormMapCount = 6

  maxtrail     = LED.StartMaxTrail
  SpeedUpSpeed = LED.SpeedUpSpeed
  
  
  OriginalSleep = LED.MainSleep * 5
  SleepTime     = LED.SuperWormSleep


  #Clock and date sprites
  ClockSprite   = LED.CreateClockSprite(12)
  #ClockH        = LED.HatWidth  // 2 - (ClockSprite.width // 2)
  #ClockV        = LED.HatHeight // 2 - (ClockSprite.height // 2)

  DayOfWeekSprite     = LED.CreateDayOfWeekSprite()
  MonthSprite         = LED.CreateMonthSprite()
  DayOfMonthSprite    = LED.CreateDayOfMonthSprite()
  
  if(LED.ShowCrypto == 'Y'):
    CurrencySprite      = CreateCurrencySprite()

  
  
  
  



  #Make an array of worms
  SuperWorms = []
  for i in range(0,LED.SuperWormCount):
    print ("Making worm:",i)
    r,g,b = LED.BrightColorList[random.randint(1,27)]
    direction  = random.randint(1,4)
    startspeed = random.randint(LED.StartSpeedHigh,LED.StartSpeedLow)
    alive      = 1
    name       = 'Superworm - ' + str(i)
    
    SpotFound = False
    h          = random.randint(30,63)
    v          = random.randint(0,31)

    while (SpotFound == False):
      if (LED.IsSpotEmpty(h,v) == True):
        SuperWorms.append(LED.Dot(h,v,r,g,b,direction,startspeed,alive,name,(0,0),0, LED.StartMaxTrail,LED.EraseSpeed,(r,g,b)))
        SpotFound = True
      else:
        h  = random.randint(30,63)
        v  = random.randint(0,31)


    

      
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


  LED.ShowGlowingText(CenterHoriz = True,h = -8,v = 0,   Text = 'TRON', RGB = LED.HighBlue, ShadowRGB = LED.ShadowBlue, ZoomFactor = 8,GlowLevels=0,DropShadow=False)
  LED.TheMatrix.Clear()
  LED.ShowGlowingText(CenterHoriz = True,h = -8,v = 0,   Text = 'TRON', RGB = LED.HighBlue, ShadowRGB = LED.ShadowBlue, ZoomFactor = 7,GlowLevels=0,DropShadow=False)
  LED.TheMatrix.Clear()
  LED.ShowGlowingText(CenterHoriz = True,h = -8,v = 0,   Text = 'TRON', RGB = LED.HighBlue, ShadowRGB = LED.ShadowBlue, ZoomFactor = 6,GlowLevels=0,DropShadow=False)
  LED.TheMatrix.Clear()
  LED.ShowGlowingText(CenterHoriz = True,h = -8,v = 0,   Text = 'TRON', RGB = LED.HighBlue, ShadowRGB = LED.ShadowBlue, ZoomFactor = 5,GlowLevels=0,DropShadow=False)
  LED.TheMatrix.Clear()
  LED.ShowGlowingText(CenterHoriz = True,h = -8,v = 0,   Text = 'TRON', RGB = LED.HighBlue, ShadowRGB = LED.ShadowBlue, ZoomFactor = 4,GlowLevels=0,DropShadow=False)
  LED.TheMatrix.Clear()
  LED.ShowGlowingText(CenterHoriz = True,h = -8,v = 0,   Text = 'TRON', RGB = LED.HighBlue, ShadowRGB = LED.ShadowBlue, ZoomFactor = 3,GlowLevels=0,DropShadow=False)

  LED.TheMatrix.Clear()
  LED.ClearBuffers()
  LED.ShowGlowingText(CenterHoriz = True,h = 0 ,v = 0,   Text = 'TRON',       RGB = LED.HighBlue,   ShadowRGB = LED.ShadowBlue,   ZoomFactor = 2,GlowLevels=50, DropShadow=True)
  LED.ShowGlowingText(CenterHoriz = True,h = 0 ,v = 16,  Text = 'LIGHT CYCLE',RGB = LED.HighRed,    ShadowRGB = LED.ShadowRed,    ZoomFactor = 1,GlowLevels=200,DropShadow=True)

  
  BrightRGB, ShadowRGB = LED.GetBrightAndShadowRGB()
  Message = LED.TronGetRandomMessage(MessageType = 'SHORTGAME')
  LED.ShowGlowingText(CenterHoriz = True,h = 0 ,v = 26,  Text = Message, RGB = BrightRGB,  ShadowRGB = ShadowRGB,  ZoomFactor = 1,GlowLevels=200,DropShadow=True,FadeLevels=200)

  LED.EraseMessageArea(LinesFromBottom=6)
  BrightRGB, ShadowRGB = LED.GetBrightAndShadowRGB()
  Message = LED.TronGetRandomMessage(MessageType = 'CHALLENGE')
  LED.ShowScrollingBanner2(Message,BrightRGB,LED.ScrollSleep,26)

  LED.TheMatrix.Clear()
  LED.Canvas.Clear()
  LED.ZoomScreen(LED.ScreenArray,32,256,0,Fade=True)
  LED.TheMatrix.Clear()



  
  while (LevelCount < LED.SuperWormLevels):
    print ("Drawing Snake")
    #DrawSnake(0,0,(LED.MedOrange),3,1)
    #LED.ShowLevelCount(LevelCount)
    
    
    LevelCount = LevelCount + 1
    LED.ClearBigLED()
    CreateSuperWormMap(random.randint(0,SuperWormMapCount-1))
    
    LED.EraseMessageArea(LinesFromBottom=5)
    LED.DisplayScoreMessage(Message="Level " + str(LevelCount),RGB=LED.HighOrange,FillerRGB=(0,0,0))
    time.sleep(1.5)
    LED.EraseMessageArea(LinesFromBottom=5)
    LED.DisplayScoreMessage(h=33,Message=str(LevelCount),RGB=LED.HighOrange,FillerRGB=(0,0,0))

    #Show Custom Sprite
    LED.CopySpriteToPixelsZoom(ClockSprite,      LED.ClockH,      LED.ClockV,      LED.ClockRGB,       LED.SpriteFillerRGB,1)
    LED.CopySpriteToPixelsZoom(DayOfWeekSprite,  LED.DayOfWeekH,  LED.DayOfWeekV,  LED.DayOfWeekRGB,   LED.SpriteFillerRGB,1)
    LED.CopySpriteToPixelsZoom(MonthSprite,      LED.MonthH,      LED.MonthV,      LED.MonthRGB,       LED.SpriteFillerRGB,1)
    LED.CopySpriteToPixelsZoom(DayOfMonthSprite, LED.DayOfMonthH, LED.DayOfMonthV, LED.DayOfMonthRGB , LED.SpriteFillerRGB,1)
    if(LED.ShowCrypto == 'Y'):
      LED.CopySpriteToPixelsZoom(CurrencySprite,   LED.CurrencyH,   LED.CurrencyV,   LED.CurrencyRGB,    LED.SpriteFillerRGB,1)

   

    
    #Reset Variables between rounds
    for i in range(0,LED.SuperWormCount):
      print ("Resetting worm:",i)
      SuperWorms[i].score = 0
      SuperWorms[i].SetStartingPoint()
      SuperWorms[i].direction = (random.randint(1,4))
      SuperWorms[i].alive     = 1
      SuperWorms[i].maxtrail  = LED.StartMaxTrail
      SuperWorms[i].trail     = [(SuperWorms[i].h, SuperWorms[i].v)]
      
    
    LevelFinished = 'N'
    SleepTime = LED.SuperWormSleep
    


    while (LevelFinished == 'N'):
      
      
      #Check for keyboard input
      m,r = divmod(moves,KeyboardSpeed)
      if (r == 0):
        Key = LED.PollKeyboard()
        ProcessKeypress(Key)
        if (Key == 'q'):
          LevelCount    = LED.SuperWormLevels + 1
          LevelFinished = 'Y'
          return
        if (Key == 'n'):
          CreateSuperWormMap(random.randint(0,SuperWormMapCount-1))
      #Show clock
      m,r = divmod(moves,CheckClockSpeed)
      if (r == 0):
        CheckClockTimer(ClockSprite)
        LED.CopySpriteToPixelsZoom(ClockSprite,      LED.ClockH,      LED.ClockV,      LED.ClockRGB,       LED.SpriteFillerRGB,1)
        LED.CopySpriteToPixelsZoom(DayOfWeekSprite,  LED.DayOfWeekH,  LED.DayOfWeekV,  LED.DayOfWeekRGB,   LED.SpriteFillerRGB,1)
        LED.CopySpriteToPixelsZoom(MonthSprite,      LED.MonthH,      LED.MonthV,      LED.MonthRGB,       LED.SpriteFillerRGB,1)
        LED.CopySpriteToPixelsZoom(DayOfMonthSprite, LED.DayOfMonthH, LED.DayOfMonthV, LED.DayOfMonthRGB,  LED.SpriteFillerRGB,1)

      if(LED.ShowCrypto == 'Y'):
        m,r = divmod(moves,LED.CheckCurrencySpeed)
        if (r == 0):  
          CurrencySprite = CreateCurrencySprite()
          LED.CopySpriteToPixelsZoom(CurrencySprite,   LED.CurrencyH,   LED.CurrencyV,   LED.CurrencyRGB,    LED.SpriteFillerRGB,1)




      #Display dots if they are alive
      #Do other stuff too
      WormsAlive = 0
      Score = 0
      ScoreRGB = (0,0,0)

      for i in range(0,LED.SuperWormCount):

        if (SuperWorms[i].alive == 1):
          SuperWorms[i].Display()
          SuperWorms[i].TrimTrail()
          WormsAlive = WormsAlive + 1
          if (Score < SuperWorms[i].score):
            Score = SuperWorms[i].score
            ScoreRGB = SuperWorms[i].r,SuperWorms[i].g,SuperWorms[i].b


          #Increase speed if necessary
          m,r = divmod(moves,LED.IncreaseTrailLengthSpeed)
          if (r == 0):
            SuperWorms[i].IncreaseMaxTrailLength(1)


          #Move worm if it is their time
          m,r = divmod(moves,SuperWorms[i].speed)
          if (r == 0):
            MoveSuperWorm(SuperWorms[i])
            #check for head on collisions
            #if the head of the superworm hits another head, reverse or die
            for sw in range (0,LED.SuperWormCount):
              if (SuperWorms[sw].alive and i != sw and SuperWorms[i].h == SuperWorms[sw].h  and SuperWorms[i].v == SuperWorms[sw].v):
                SuperWorms[i].Kill()
                SuperWorms[sw].Kill()
                print ("Head on collision.  Both worms died")
                WormsAlive = WormsAlive - 2
                break;



        else:
          r = random.randint(0,LED.ResurrectionChance)
          if (r == 1):
            SuperWorms[i].Resurrect()
        
        

      print ("WormsAlive:",WormsAlive," ",end="\r")




      #Calculate Movement / Display Score
      moves = moves +1

      #don't print the screen every move, otherwise it slows game down
      #this is a good spot for implementing multithreading
      if (random.randint(1,10) == 1):
        LED.DisplayScore(Score,ScoreRGB)

      

      LevelFinished = 'Y'

      for i in range(0,LED.SuperWormCount):
        if (SuperWorms[i].alive == 1):
          LevelFinished = 'N'


      # if(Worm1Dot.alive == 0 and Worm2Dot.alive == 0 and Worm3Dot.alive == 0 and Worm4Dot.alive == 0 and Worm5Dot.alive == 0):
        # LevelFinished = 'Y'
      
      #print ("Alive:",Worm1Dot.alive,Worm2Dot.alive,Worm3Dot.alive)
    

      #Increase speed
      m,r = divmod(moves,SpeedUpSpeed)
      if (r == 0):
        SleepTime = SleepTime * 0.95
        if (SleepTime < LED.MinSleepTime):
          SleepTime = LED.MinSleepTime
      
      if (SleepTime >= LED.MinSleepTime):
        time.sleep(SleepTime)

    #get a random message to show at bottom of screen
    Message = LED.TronGetRandomMessage()
    LED.EraseMessageArea(LinesFromBottom=5)
    LED.DisplayScoreMessage(Message=Message ,RGB=LED.HighOrange,FillerRGB=(20,0,0))
    time.sleep(1.5)
    LED.ZoomScreen(LED.ScreenArray,32,256,0,Fade=True)

  LED.ShowGlowingText(CenterHoriz=True,h=0,v=0 ,Text= 'END',  RGB= LED.HighRed,ShadowRGB= LED.ShadowRed,ZoomFactor= 2,GlowLevels=55, DropShadow=False)
  LED.ShowGlowingText(CenterHoriz=True,h=0,v=11,Text= 'OF',   RGB= LED.HighRed,ShadowRGB= LED.ShadowRed,ZoomFactor= 2,GlowLevels=55, DropShadow=False)
  LED.ShowGlowingText(CenterHoriz=True,h=0,v=22,Text= 'LINE', RGB= LED.HighRed,ShadowRGB= LED.ShadowRed,ZoomFactor= 2,GlowLevels=55, DropShadow=False)
  time.sleep(1)
  LED.ZoomScreen(LED.ScreenArray,32,256,0,Fade=True)



  #Determine winner
  LongestTrail     = 1
  WinningSuperWorm = 0
  for i in range (0,LED.SuperWormCount):
    if (LongestTrail < len(SuperWorms[i].trail)):
      LongestTrail     = len(SuperWorms[i].trail)
      WinningSuperWorm = i
  print ("Winner: SuperWorm",i," score:",LongestTrail)
  #SuperWorms[WinningSuperWorm].score = SuperWorms[WinningSuperWorm].score + LongestTrail

  FinalScore  = str(LongestTrail)
  FinalWinner = SuperWorms[WinningSuperWorm].name
  Finalr      = SuperWorms[WinningSuperWorm].r
  Finalg      = SuperWorms[WinningSuperWorm].g
  Finalb      = SuperWorms[WinningSuperWorm].b 
  FinalRGB    = (Finalr,Finalg,Finalb)
  
  LED.TheMatrix.Clear()
  LED.ClearBuffers()
  #LED.ShowGlowingText(CenterHoriz=True,h=0,v=1 ,Text= 'FINAL',      RGB= LED.HighRed,    ShadowRGB= LED.ShadowRed,    ZoomFactor= 2,GlowLevels=150, DropShadow=True)
  #LED.ShowGlowingText(CenterHoriz=True,h=0,v=12,Text= 'SCORE',      RGB= LED.HighRed,    ShadowRGB= LED.ShadowRed,    ZoomFactor= 2,GlowLevels=150, DropShadow=True)
  #LED.ShowGlowingText(CenterHoriz=True,h=0,v=26,Text= FinalScore,   RGB= FinalRGB,      ShadowRGB= (15,15,15),      ZoomFactor= 1,GlowLevels=150, FadeLevels=150,DropShadow=True)
  #ThreeGhostSprite.ScrollAcrossScreen(0,26,'right',LED.ScrollSleep)
  #LED.TheMatrix.Clear()
  #LED.Canvas.Clear()
  #LED.ZoomScreen(LED.ScreenArray,32,256,0,Fade=True)






  return;



#--------------------------------------
#  WormDOt                           --
#--------------------------------------

def TrimTrail(Dot):
  if (len(Dot.trail) > Dot.maxtrail):
    h,v = Dot.trail[0]
    LED.setpixel(h,v,0,0,0)
    del Dot.trail[0]

def PlaceGreenObstacle():
  finished = 'N'
  h = 1
  v = 0

  h = random.randint(0,LED.HatWidth-1)
  v = random.randint(0,LED.HatWidth-1)

  while (finished == 'N'):
    h = random.randint(0,LED.HatWidth-1)
    v = random.randint(0,LED.HatWidth-1)
    while ((h == 1  and v == 0)
        or (h == 0  and v == 1)
        or (h == 15 and v == 1)
        or (h == 0  and v == 14)
        or (h == 15 and v == 14)
        or (h == 1  and v == 15)
        or (h == 14  and v == 15)
        or (h == 14  and v == 0)):
        
        # actually, I will allow it for now
        #or (v == 1) # I decided to not let any obstacles on these rows, to increase play time
        #or (v == 6)
        #or (h == 1)
        #or (h == 6)):
      h = random.randint(0,LED.HatWidth-1)
      v = random.randint(0,LED.HatWidth-1)
    r,g,b = LED.getpixel(h,v)
    #print ("got pixel rgb hv",r,g,b,h,v)
    
    #The color of green is very important as it denotes an obstacle
    #The scanner will fade the obstacle until it disappears
    if (r == 0 and g == 0 and b == 0):
      
      #Once in a while, we will make the obstacle permanent (white dot)
      if (random.randint(1,3) == 1):
        LED.setpixel(h,v,0,125,125)
      else:
        LED.setpixel(h,v,0,75,0)
  
      finished = 'Y'
    
    #Sometimes it takes too long to find a empty spot and the program
    #seems to hang. We now have a 1 in 20 chance of exiting
    if (random.randint(1,20) == 1):
      finished = 'Y'

        
      
      

def PlaceSpeedupPill():
  finished = 'N'
  while (finished == 'N'):
    h = random.randint(0,LED.HatWidth-1)
    v = random.randint(0,LED.HatWidth-1)
    r,g,b = LED.getpixel(h,v)
    if (r == 0 and g == 0 and b == 0):
      LED.setpixel(h,v,LED.SDLowRedR,LED.SDLowRedG,LED.SDLowRedB)
      finished = 'Y'

    
    
def PlayWormDot():
  
  #Local variables
  moves       = 0
  Finished    = 'N'
  LevelCount  = 3
  Worm1h      = 0
  Worm1v      = 0
  Worm2h      = 0
  Worm2v      = 0
  Worm3h      = 0
  Worm3v      = 0
  SleepTime   = LED.MainSleep / 8
  
  #How often to obstacles appear?
  ObstacleTrigger = 150
  SpeedupTrigger  = 75
  SpeedupMultiplier = 0.75
  
  
  
  #def __init__(self,h,v,r,g,b,direction,speed,alive,name,trail,score,maxtrail,erasespeed):
  Worm1Dot = LED.Dot(Worm1h,Worm1v,LED.SDLowBlueR,LED.SDLowBlueG,LED.SDLowBlueB,(random.randint(1,5)),1,1,'Blue',(Worm1h, Worm1v), 0, 1,0.03)
  Worm2Dot = LED.Dot(Worm2h,Worm2v,LED.SDLowPurpleR,LED.SDLowPurpleG,LED.SDLowPurpleB,(random.randint(1,5)),1,1,'Purple',(Worm2h,Worm2v),0, 1,0.03)
  Worm3Dot = LED.Dot(Worm3h,Worm3v,LED.SDDarkOrangeR,LED.SDDarkOrangeG,LED.SDDarkOrangeB,(random.randint(1,5)),1,1,'Orange',(Worm3h,Worm3v),0, 1,0.03)
 
  
  #Title
  LED.ClearBigLED()
  LED.ShowScrollingBanner2("Worms",(LED.MedOrange),LED.ScrollSleep)
    

  
  while (LevelCount > 0):
    #print ("show worms")
    LED.ClearBigLED()
    #Display animation and clock every 30 seconds

    #print ("Show level")
    LED.ShowLevelCount(LevelCount)
    LevelCount = LevelCount - 1
    LED.ClearBigLED()
    #print ("===============================")
  
    #Reset Variables between rounds
    Worm1Dot.speed = 1 * LED.CPUModifier
    Worm2Dot.speed = 1 * LED.CPUModifier
    Worm3Dot.speed = 1 * LED.CPUModifier
    Worm1Dot.maxtrail = 0
    Worm2Dot.maxtrail = 0
    Worm3Dot.maxtrail = 0
    Worm1Dots = 0
    Worm2Dots = 0
    Worm3Dots = 0
    LevelFinished = 'N'
    moves     = 0

    #Place obstacles
    PlaceGreenObstacle()
    PlaceGreenObstacle()
    PlaceGreenObstacle()
    PlaceGreenObstacle()
    PlaceGreenObstacle()
    PlaceGreenObstacle()
    
    
    #Increase length of trail
    Worm1Dot.maxtrail = Worm1Dot.maxtrail + 1
    Worm2Dot.maxtrail = Worm2Dot.maxtrail + 1
    Worm3Dot.maxtrail = Worm3Dot.maxtrail + 1
    
    #Set random starting points
    Worm1h = random.randint(1,6)
    Worm1v = random.randint(1,6)
    Worm2h = random.randint(1,6)
    Worm2v = random.randint(1,6)
    Worm3h = random.randint(1,6)
    Worm3v = random.randint(1,6)
    while (Worm2h == Worm1h and Worm2v == Worm1v):
      Worm2h = random.randint(1,6)
      Worm2v = random.randint(1,6)
    while ((Worm3h == Worm2h and Worm3v == Worm2v) or (Worm3h == Worm1h and Worm3v == Worm1v)):
      Worm3h = random.randint(1,6)
      Worm3v = random.randint(1,6)
      
         
      
    Worm1Dot.h         = Worm1h
    Worm1Dot.v         = Worm1v
    Worm1Dot.direction = (random.randint(1,4))
    Worm1Dot.alive     = 1
    Worm1Dot.trail     = [(Worm1h, Worm1v)]
    
    Worm2Dot.h         = Worm2h
    Worm2Dot.v         = Worm2v
    Worm2Dot.direction = (random.randint(1,4))
    Worm2Dot.alive     = 1
    Worm2Dot.trail     = [(Worm2h, Worm2v)]
    

    Worm3Dot.h         = Worm3h
    Worm3Dot.v         = Worm3v
    Worm3Dot.direction = (random.randint(1,4))
    Worm3Dot.alive     = 1
    Worm3Dot.trail     = [(Worm3h, Worm3v)]

    while (LevelFinished == 'N'):
      
      #reset variables
      #Display animation and clock every X seconds
      if (CheckElapsedTime(CheckTime) == 1):
        ScrollScreenShowChickenWormTime('up',LED.ScrollSleep)


      
      
      #print ("direction:",Worm1Dot.direction,Worm2Dot.direction,Worm3Dot.direction)
      #Display dots if they are alive
      if (Worm1Dot.alive == 1):
        Worm1Dot.Display()
      if (Worm2Dot.alive == 1):
        Worm2Dot.Display()
      if (Worm3Dot.alive == 1):
        Worm3Dot.Display()
      #unicorn.show()
      #SendBufferPacket(RemoteDisplay,LED.HatHeight,LED.HatWidth)
    

      #Calculate Movement
      moves = moves +1

      #Check for keyboard input
      m,r = divmod(moves,KeyboardSpeed)
      if (r == 0):
        Key = LED.PollKeyboard()
        ProcessKeypress(Key)

        if (Key == 'q'):
          LevelFinished = 'Y'
          LevelCount = 0
          return
      
      #PlaceObstacle and Increase Speed of the game
      m,r = divmod(moves,ObstacleTrigger)
      if (r==0):
        PlaceGreenObstacle()
        #This isn't used anymore since I went to HD
        #SleepTime = SleepTime * SpeedupMultiplier

      #PlaceSpeedupPill
      m,r = divmod(moves,SpeedupTrigger)
      if (r==0):
        PlaceSpeedupPill()
        
        
      if (Worm1Dot.alive == 1):
        m,r = divmod(moves,Worm1Dot.speed)
        if (r == 0):
          MoveWorm(Worm1Dot)
          Worm1Dot.score = Worm1Dot.score + 1
          #check for head on collisions
          if ((Worm1Dot.h == Worm2Dot.h and Worm1Dot.v == Worm2Dot.v and Worm2Dot.alive == 1) or (Worm1Dot.h == Worm3Dot.h and Worm1Dot.v == Worm3Dot.v and Worm3Dot.alive == 1)):
            #Worm1Dot.alive = 0
            #Worm1Dot.EraseTrail()
            Worm1Dot.maxtrail - 1
            if (Worm1Dot.maxtrail <= 0):
              Worm1Dot.maxtrail = 1
            Worm1Dot.speed = Worm1Dot.speed + 2

      if (Worm2Dot.alive == 1):
        m,r = divmod(moves,Worm2Dot.speed)
        if (r == 0):
          #Worm2Dot.trail.append((Worm2Dot.h, Worm2Dot.v))
          MoveWorm(Worm2Dot)
          Worm2Dot.score = Worm2Dot.score + 1
          #check for head on collisions
          if ((Worm2Dot.h == Worm3Dot.h and Worm2Dot.v == Worm3Dot.v and Worm3Dot.alive == 1) or (Worm2Dot.h == Worm1Dot.h and Worm2Dot.v == Worm1Dot.v and Worm1Dot.alive == 1)):
            #Worm2Dot.alive = 0
            #Worm2Dot.EraseTrail()
            Worm2Dot.maxtrail - 1
            if (Worm2Dot.maxtrail <= 0):
              Worm1Dot.maxtrail = 1
            Worm2Dot.speed = Worm2Dot.speed + 2

      if (Worm3Dot.alive == 1):
        m,r = divmod(moves,Worm3Dot.speed)
        if (r == 0):
          #Worm3Dot.trail.append((Worm3Dot.h, Worm3Dot.v))
          MoveWorm(Worm3Dot)
          Worm3Dot.score = Worm3Dot.score + 1
          #check for head on collisions
          if ((Worm3Dot.h == Worm2Dot.h and Worm3Dot.v == Worm2Dot.v and Worm2Dot.alive == 1) or (Worm3Dot.h == Worm1Dot.h and Worm3Dot.v == Worm1Dot.v and Worm1Dot.alive == 1)):
            #Worm3Dot.alive = 0
            #Worm3Dot.EraseTrail()
            Worm3Dot.maxtrail - 1
            if (Worm3Dot.maxtrail <= 0):
              Worm1Dot.maxtrail = 1
            Worm3Dot.speed = Worm3Dot.speed + 2
      
      #Trim length of Tails
      TrimTrail(Worm1Dot)
      TrimTrail(Worm2Dot)
      TrimTrail(Worm3Dot)
      
      
      if(Worm1Dot.alive == 0 and Worm2Dot.alive == 0 and Worm3Dot.alive == 0):
        LevelFinished = 'Y'
      
      #print ("Alive:",Worm1Dot.alive,Worm2Dot.alive,Worm3Dot.alive)
    
      PlayersAlive = Worm1Dot.alive + Worm2Dot.alive + Worm3Dot.alive
      # if (PlayersAlive == 2):
        # SleepTime = (SleepTime )
      # elif (PlayersAlive == 1):
        # SleepTime = (SleepTime )
      #time.sleep(SleepTime)
    
    
  
  #Calculate Game score
  FinalWinner = ''
  FinalScore  = 0
  Finalr      = 0
  Finalg      = 0
  Finalb      = 0
  if (Worm1Dot.score > Worm2Dot.score and Worm1Dot.score >= Worm3Dot.score):
    FinalScore  = Worm1Dot.score
    FinalWinner = Worm1Dot.name
    Finalr      = Worm1Dot.r
    Finalg      = Worm1Dot.g
    Finalb      = Worm1Dot.b
  elif (Worm2Dot.score >= Worm1Dot.score and Worm2Dot.score >= Worm3Dot.score):
    FinalScore  = Worm2Dot.score
    FinalWinner = Worm2Dot.name
    Finalr      = Worm2Dot.r
    Finalg      = Worm2Dot.g
    Finalb      = Worm2Dot.b
  else:
    FinalScore = Worm3Dot.score
    FinalWinner = Worm3Dot.name
    Finalr      = Worm3Dot.r
    Finalg      = Worm3Dot.g
    Finalb      = Worm3Dot.b

  LED.ClearBigLED()
  ScrollString = FinalWinner + ' ' + str(FinalScore)
  
  LED.ShowScrollingBanner(ScrollString,Finalr,Finalg,Finalb,LED.ScrollSleep)
  LED.ShowScrollingBanner("GAME OVER",LED.SDMedPinkR,LED.SDMedPinkG,LED.SDMedPinkB,LED.ScrollSleep)












  

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
  h = BomberShip.h
  v = BomberShip.v
  if (BomberShip.lives > 0):
    BomberShip.lives = BomberShip.lives - 1
    LED.SpaceDotScore = LED.SpaceDotScore + LED.BomberHitPoints
  else:
    #BomberShip.alive = 0
    #LED.SpaceDotScore = LED.SpaceDotScore + LED.BomberPoints
    #PlayerShipExplosion.Animate(h-2,v-2,'forward',0.025)
    BomberShip.exploding = 1
    BomberShip.alive     = 0
    BomberShip.Explosion.h = h
    BomberShip.Explosion.v = v

    LED.SpaceDotScore = LED.SpaceDotScore + LED.BomberPoints

    #Erase playfield (ship is 3 dots across)
    if (h > 0 and h <= LED.HatWidth-1):
      Playfield[v][h] = LED.EmptyObject
    if (h+1 > 0 and h+1 <= LED.HatWidth-1):
      Playfield[v][h+1] = LED.EmptyObject
    if (h+2 > 0 and h+2 <= LED.HatWidth-1):
      Playfield[v][h+2] = LED.EmptyObject
    BomberShip.Erase()

def HitHomingMissile(HomingMissileShip,HomingMissileSprite):
  h = HomingMissileShip.h
  v = HomingMissileShip.v
  if (HomingMissileShip.lives > 0):
    HomingMissileShip.lives = HomingMissileShip.lives - 1
    LED.SpaceDotScore = LED.SpaceDotScore + LED.HomingMissilePoints

  if (HomingMissileShip.lives == 0):
    HomingMissileShip.exploding = 1
    HomingMissileShip.alive     = 0
    #print ("blowing up homing missile")
    #LED.FlashDot(h,v,1)
    HomingMissileSprite.h = h
    HomingMissileSprite.v = v
    Playfield     = HomingMissileSprite.EraseSpriteFromPlayfield(Playfield)
    LED.SpaceDotScore = LED.SpaceDotScore + LED.HomingMissilePoints



def HitPlayerShip(PlayerShip):
  if (PlayerShip.lives > 0):
    PlayerShip.lives = PlayerShip.lives - 1

  if (PlayerShip.lives == 0):
    PlayerShip.exploding = 1
    PlayerShip.alive     = 0
    #Playfield[Playership.v][Playership.h] = LED.EmptyObject()
    


def HitGround(Ground):
  h = Ground.h
  v = Ground.v

  #The ground is messed up.  Missiles hit it and the ground objects are getting overwritten with LED.EmptyObject
  #because of this I am  just going to change the color of the ground but leave the pieces alive
  Ground.alive   = 1

  #if (Ground.lives > 0):
  #  Ground.lives = Ground.lives - 1
  Ground.r = Ground.r +25
  Ground.g = Ground.g +5
  Ground.b = Ground.b = 0

  if (Ground.r >= 255):
    Ground.r = 255
  if (Ground.g >= 255):
    Ground.g = 0


    
  Playfield[v][h].r = Ground.r
  Playfield[v][h].g = Ground.g
  Playfield[v][h].b = Ground.b

  print("Ground hit hv:",Ground.h,Ground.v," rgb",Ground.r,Ground.g,Ground.b,' lives:',Ground.lives)

  #calculate score
  LED.SpaceDotScore = LED.SpaceDotScore - LED.AsteroidLandedPoints



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

    for i in range(0,LED.PlayerMissiles):
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
      
      #print ("MPS - ENEMY TO LEFT Enemy.name HV direction",Playfield[0][h-1].name,Playfield[0][h-1].h,Playfield[0][h-1].v, Playfield[0][h-1].direction)
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
      m,r = divmod(moves,LED.PlanetSurfaceSleep)  
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
    if (random.randint(1,LED.HomingMissileDescentChance) == LED.HomingMissileDescentChance):
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




  if(ScanV == LED.GroundV):
    print ('missile at ground.  name:',Missile.name,' item:',Item,ScanH,ScanV)
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
    print('Adding points:',LED.SpaceDotScore,LED.AsteroidPoints)
    LED.SpaceDotScore = LED.SpaceDotScore + LED.AsteroidPoints


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

    Playfield[v][h] = LED.EmptyObject
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










def RedrawGround(TheGround):
  GroundCount = 0
  for i in range (SpaceDotMinH,SpaceDotMaxH):
    Playfield[LED.GroundV][i] = TheGround[GroundCount]
    Playfield[LED.GroundV][i].Display()
    GroundCount = GroundCount + 1
  return







#------------------------------------------------------------------------------
#- SPACE DOT 
#-
#------------------------------------------------------------------------------






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
  





  
def PlaySpaceDot():
  
  
  LED.ClearBigLED()
  LED.SpaceDotScore = 0
  
  #Local variables
  moves       = 0
  Finished    = 'N'
  LevelCount  = 3
  Playerh     = 0
  Playerv     = 0
  SleepTime   = LED.MainSleep / 4
  ChanceOfUFO = 200
  

  #Timers / Clock display
  ClockSprite = LED.CreateClockSprite(12)
  #lockH        = LED.HatWidth  // 2 - (ClockSprite.width // 2)
  #lockV        = LED.HatHeight // 2 - (ClockSprite.height // 2)
  start_time    = time.time()
  DayOfWeekSprite     = LED.CreateDayOfWeekSprite()
  MonthSprite         = LED.CreateMonthSprite()
  DayOfMonthSprite    = LED.CreateDayOfMonthSprite()
  if(LED.ShowCrypto == 'Y'):
    CurrencySprite      = CreateCurrencySprite()

  



  #define objects
  #def __init__(self,h,v,r,g,b,direction,scandirection,speed,alive,lifes,name,score,exploding):
  PlayerShip = LED.Ship(3 + SpaceDotMinH,SpaceDotMaxV - 2,PlayerShipR,PlayerShipG,PlayerShipB,4,1,PlayerShipSpeed,1,3,'Player1', 0,0)
  PlayerShip.lives = PlayerShipLives
  

  EnemyShip  = LED.Ship(SpaceDotMinH,0,LED.SDMedPurpleR,LED.SDMedPurpleG,LED.SDMedPurpleB,4,3,LED.UFOShipSpeed,0,3,'UFO', 0,0)
  Empty      = LED.Ship(-1,-1,0,0,0,0,1,0,0,0,'EmptyObject',0,0)
   
  BomberShip.h = -2 + SpaceDotMinH
  BomberShip.v =  SpaceDotMinV
  BomberShip.alive = 0
  #HomingMissileShip.h =  SpaceDotMinH + (int(SpaceDotMinH / 2))
  #HomingMissileShip.v =  SpaceDotMinV
  
  HomingMissileShip    = LED.Ship(SpaceDotMinH,SpaceDotMaxV - 1,PlayerShipR,PlayerShipG,PlayerShipB,4,1,8,1,3,'HomingMissile', 0,0)
  HomingMissileSprite  = HomingMissileSpriteList[random.randint(0,LED.HomingMissileSprites -1 )]

  #Explosion Sprites
  PlayerShip.Explosion = copy.deepcopy(PlayerShipExplosion)  
  BomberShip.Explosion = copy.deepcopy(BomberShipExplosion)  

  BomberShip.Explosion.framerate = 10
  BomberRock.Explosion           = copy.deepcopy(PlayerShipExplosion)  
  BomberRock.Explosion.framerate = 2
  BomberRock.Explosion.h         = -1
  BomberRock.Explosion.v         = -1

  #HomingMissileShipExplosion    = copy.deepcopy(PlayerShipExplosion)  
  HomingMissileShipExplosion    = copy.deepcopy(BigShipExplosion)  

  LED.CenterSpriteOnShip(HomingMissileShipExplosion,HomingMissileShip)
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
  Wave = LED.AsteroidWave(LED.AsteroidsInWaveMin)
  







  #Reset Playfield
  for x in range (0,LED.HatWidth):
    for y in range (0,LED.HatHeight):
      #print ("XY",x,y)
      Playfield[y][x] = Empty
               
  Playfield[PlayerShip.v][PlayerShip.h] = PlayerShip




  #Title
  #LED.ShowScrollingBanner2("SpaceDot",(LED.MedOrange),LED.ScrollSleep)

  #Animation Sequence
  #ShowBigShipTime(LED.ScrollSleep)  

  LED.TheMatrix.Clear()
  LED.ClearBuffers()
  




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


  LED.ShowGlowingText(CenterHoriz = True,h = -8,v = 0,   Text = 'ASTRO', RGB = LED.MedGreen,  ShadowRGB = LED.ShadowGreen, ZoomFactor = 8,GlowLevels=0,DropShadow=False)
  LED.TheMatrix.Clear()
  LED.ShowGlowingText(CenterHoriz = True,h = -8,v = 0,   Text = 'ASTRO', RGB = LED.MedGreen, ShadowRGB = LED.ShadowGreen, ZoomFactor = 7,GlowLevels=0,DropShadow=False)
  LED.TheMatrix.Clear()
  LED.ShowGlowingText(CenterHoriz = True,h = -8,v = 0,   Text = 'ASTRO', RGB = LED.MedGreen, ShadowRGB = LED.ShadowGreen, ZoomFactor = 6,GlowLevels=0,DropShadow=False)
  LED.TheMatrix.Clear()
  LED.ShowGlowingText(CenterHoriz = True,h = -8,v = 0,   Text = 'ASTRO', RGB = LED.MedGreen, ShadowRGB = LED.ShadowGreen, ZoomFactor = 5,GlowLevels=0,DropShadow=False)
  LED.TheMatrix.Clear()
  LED.ShowGlowingText(CenterHoriz = True,h = -8,v = 0,   Text = 'ASTRO', RGB = LED.MedGreen, ShadowRGB = LED.ShadowGreen, ZoomFactor = 4,GlowLevels=0,DropShadow=False)
  LED.TheMatrix.Clear()
  LED.ShowGlowingText(CenterHoriz = True,h = -8,v = 0,   Text = 'ASTRO', RGB = LED.MedGreen, ShadowRGB = LED.ShadowGreen, ZoomFactor = 3,GlowLevels=0,DropShadow=False)

  LED.TheMatrix.Clear()
  LED.ClearBuffers()
  LED.ShowGlowingText(CenterHoriz = True,h = -8,v = 0,   Text = 'ASTRO',      RGB = LED.HighGreen,  ShadowRGB = LED.ShadowGreen,  ZoomFactor = 2,GlowLevels=200,DropShadow=False)
  LED.ShowGlowingText(CenterHoriz = True,h = 0 ,v = 12,  Text = 'SMASH!',     RGB = (255,0,0),     ShadowRGB = LED.ShadowRed,    ZoomFactor = 2,GlowLevels=50,DropShadow=True)
  RGB = LED.BrightColorList[random.randint(1,LED.BrightColorCount)]
  Message = LED.TronGetRandomMessage(MessageType = 'SHORTGAME')
  LED.ShowGlowingText(CenterHoriz = True,h = 0 ,v = 26,  Text = Message, RGB = BrightRGB,  ShadowRGB = ShadowRGB,  ZoomFactor = 1,GlowLevels=200,DropShadow=True,FadeLevels=200)
  time.sleep(1)
  LED.TheMatrix.Clear()
  LED.Canvas.Clear()
  LED.ZoomScreen(LED.ScreenArray,32,128,0)
  LED.ZoomScreen(LED.ScreenArray,128,1,0,Fade=True)
  



  #Show clock
  CheckClockTimer(ClockSprite)
  LED.CopySpriteToPixelsZoom(ClockSprite,      LED.ClockH,      LED.ClockV,      LED.ClockRGB,       LED.SpriteFillerRGB,1)
  LED.CopySpriteToPixelsZoom(DayOfWeekSprite,  LED.DayOfWeekH,  LED.DayOfWeekV,  LED.DayOfWeekRGB,   LED.SpriteFillerRGB,1)
  LED.CopySpriteToPixelsZoom(MonthSprite,      LED.MonthH,      LED.MonthV,      LED.MonthRGB,       LED.SpriteFillerRGB,1)
  LED.CopySpriteToPixelsZoom(DayOfMonthSprite, LED.DayOfMonthH, LED.DayOfMonthV, LED.DayOfMonthRGB,  LED.SpriteFillerRGB,1)
  if(LED.ShowCrypto == 'Y'):
    LED.CopySpriteToPixelsZoom(CurrencySprite,   LED.CurrencyH,   LED.CurrencyV,   LED.CurrencyRGB,    LED.SpriteFillerRGB,1)



  
  

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


    EnemyShip.speed   = random.randint (LED.UFOShipMinSpeed,LED.UFOShipMaxSpeed)
    
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
    BomberShip.lives = 3
    HomingMissileShip.alive = 0
    HomingMissileShip.lives = LED.HomingMissileLives
    

    #Make a wave of asteroids
    
    Wave = LED.AsteroidWave(LED.AsteroidsInWaveMin)
    Wave.CreateAsteroidWave()
    LED.DisplayLevel(Wave.WaveCount,LED.MedBlue)
    

    
    #Reset Playfield
    for x in range (0,LED.HatWidth):
      for y in range (0,LED.HatHeight):
        #print ("XY",x,y)
        Playfield[y][x] = Empty
                 
    Playfield[PlayerShip.v][PlayerShip.h] = PlayerShip

    #Create the ground
    color = random.randint(1,7) * 4 + 1
    r,g,b = LED.ColorList[color]    
    TheGround   = []    
    GroundCount = 0
    for i in range (SpaceDotMinH,SpaceDotMaxH):
      TheGround.append(LED.Ship(i,LED.GroundV,r,g,b,0,0,0,1,LED.SpaceDotGroundLives,'Ground', 0,0))
      Playfield[LED.GroundV][i] = TheGround[GroundCount]
      Playfield[LED.GroundV][i].Display()
      LED.FlashDot2(i,LED.GroundV,0.04)
      #print("Ground:",i,LED.GroundV)
      GroundCount = GroundCount + 1





    
    # Main timing loop
    while (LevelFinished == 'N' and PlayerShip.alive == 1):
      moves = moves + 1

      
      #Draw bottom background
      m,r = divmod(moves,LED.PlanetSurfaceSleep)  
      if (r == 0):
        RedrawGround(TheGround)

      #Cleanup debris (leftover pixels from explosions)
      m,r = divmod(moves,LED.DebrisCleanupSleep)
      if (r == 0):
        LED.CleanupDebris(SpaceDotMinH,SpaceDotMaxH,SpaceDotMinV,SpaceDotMaxV,Playfield)

     

      #Check for keyboard input
      m,r = divmod(moves,KeyboardSpeed)
      if (r == 0):
        Key = LED.PollKeyboard()
        ProcessKeypress(Key)
        if (Key == 'Q' or Key == 'q'):
          LevelCount = 0
          return
        elif (Key == 'd'):
          LED.DebugPlayfield(Playfield,LED.HatWidth,LED.HatHeight)
          for i in range (0,LED.PlayerMissiles):
            print("Name HV Alive Exploding Speed:",PlayerMissiles[i].name,PlayerMissiles[i].h,PlayerMissiles[i].v,PlayerMissiles[i].alive,PlayerMissiles[i].exploding,PlayerMissiles[i].speed)
          time.sleep(2)

        elif (Key == 'n'):
          Playfield            = HomingMissileSprite.EraseSpriteFromPlayfield(Playfield)
          HomingMissileShip.h     = 32
          HomingMissileShip.v     = 0
          HomingMissileShip.lives = 10
          HomingMissileShip.alive = 1
          HomingMissileSprite.v   = 0
          HomingMissileSprite     = HomingMissileSpriteList[random.randint(0,LED.HomingMissileSprites -1 )]

      
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
        LED.CopySpriteToPixelsZoom(ClockSprite,      LED.ClockH,      LED.ClockV,      LED.ClockRGB,       LED.SpriteFillerRGB,1)
        LED.CopySpriteToPixelsZoom(DayOfWeekSprite,  LED.DayOfWeekH,  LED.DayOfWeekV,  LED.DayOfWeekRGB,   LED.SpriteFillerRGB,1)
        LED.CopySpriteToPixelsZoom(MonthSprite,      LED.MonthH,      LED.MonthV,      LED.MonthRGB,       LED.SpriteFillerRGB,1)
        LED.CopySpriteToPixelsZoom(DayOfMonthSprite, LED.DayOfMonthH, LED.DayOfMonthV, LED.DayOfMonthRGB,  LED.SpriteFillerRGB,1)
 

      if(LED.ShowCrypto == 'Y'):
  
        m,r = divmod(moves,LED.CheckCurrencySpeed)
        if (r == 0):  
          CurrencySprite = CreateCurrencySprite()
        m,r = divmod(moves,LED.DisplayCurrencySpeed)
        if (r == 0):  
          LED.CopySpriteToPixelsZoom(CurrencySprite,   LED.CurrencyH,   LED.CurrencyV,   LED.CurrencyRGB,    LED.SpriteFillerRGB,1)





      
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

          
        LED.CenterSpriteOnShip(BomberSprite,BomberShip) 
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
          LED.CenterSpriteOnShip(HomingMissileSprite,HomingMissileShip)
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
      for i in range (0,LED.PlayerMissiles):
        #print ("Checking player missile:",i)

        #check for buggy missiles that have gone out of range
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
        m,r = divmod(moves,LED.WaveDropSpeed)
        if (r == 0):
          Wave.UpdateCounts()
          Wave.DropAsteroids((random.randint(LED.AsteroidsToDropMin,LED.AsteroidsToDropMax)),Playfield)

          
        #Move asteroids that are alive
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
      if (Wave.WaveCount >= LED.MinBomberWave):

        m,r = divmod(moves,LED.ChanceOfBomberShip)
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
          BomberRock.speed = LED.BomberRockSpeed
          BomberRock.h     = BomberShip.h 
          BomberRock.v     = BomberShip.v +1
          


        
      #move BomberRock
      if (BomberRock.alive == 1 and BomberRock.exploding == 0):
        m,r = divmod(moves,BomberRock.speed)
        if (r == 0):
          MoveMissile(BomberRock)


      
        
          
      #Spawn Homing missile
      if (Wave.WaveCount >= LED.MinHomingMissileWave):
        m,r = divmod(moves,LED.ChanceOfHomingMissile)
        if (r == 0 and HomingMissileShip.alive == 0):

          HomingMissileSprite   = HomingMissileSpriteList[random.randint(0,LED.HomingMissileSprites -1)]
          HomingMissileShip.alive = 1
          HomingMissileShip.lives = LED.HomingMissileLives
          MissileSpawned = False
          while (MissileSpawned == False):
            h = random.randint(SpaceDotMinH,SpaceDotMaxH)
            v = SpaceDotMinV 
            if (Playfield[v][h].name == 'EmptyObject'):
              HomingMissileShip.h = h
              HomingMissileShip.v = v
              Playfield[v][h] = HomingMissileShip
              HomingMissileShip.speed = LED.HomingMissileInitialSpeed
              MissileSpawned = True
              LED.CenterSpriteOnShip(HomingMissileSprite,HomingMissileShip)
        

      
          
      


     
      #-----------------------------
      # Check for exploding objects
      #-----------------------------

      #player missiles
      for i in range (0,LED.PlayerMissiles):
        if (PlayerMissiles[i].exploding == 1):
          #print("------> PlayerMissile1.exploding: ",PlayerMissile1.exploding)
          PlayerMissiles[i].Explosion.h = PlayerMissiles[i].h
          PlayerMissiles[i].Explosion.v = PlayerMissiles[i].v
          PlayerMissiles[i].Explosion.DisplayAnimated()
          
        #Kill missile after explosion animation is complete
        if (PlayerMissiles[i].Explosion.currentframe >= PlayerMissiles[i].Explosion.frames-1):
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
        if (Wave.Asteroids[i].Explosion.currentframe >= Wave.Asteroids[i].Explosion.frames-1):

          Wave.Asteroids[i].Explosion.h            = -1
          Wave.Asteroids[i].Explosion.v            = -1
          Wave.Asteroids[i].Explosion.currentframe = 0
          Wave.Asteroids[i].Explosion.exploding    = 0
          Wave.Asteroids[i].Explosion.alive        = 0
          Wave.Asteroids[i].alive = 0
          Wave.Asteroids[i].exploding = 0

          Wave.Asteroids[i].h                      = -1
          Wave.Asteroids[i].v                      = -1
          Playfield[Wave.Asteroids[i].v][Wave.Asteroids[i].h] = TheGround[i]

#handle points somewhere else.


      #BomberRock
      if (BomberRock.exploding == 1 ):

        if (BomberRock.Explosion.h == -1):
          BomberRock.Explosion.h = BomberRock.h -2
          BomberRock.Explosion.v = BomberRock.v -2

        BomberRock.Explosion.DisplayAnimated()

        if (BomberRock.Explosion.currentframe >= BomberRock.Explosion.frames-1):
          BomberRock.Explosion.h            = -1
          BomberRock.Explosion.v            = -1
          BomberRock.Explosion.currentframe = 0
          BomberRock.Explosion.exploding    = 0
          BomberRock.Explosion.alive        = 0
          BomberRock.exploding              = 0
          BomberRock.alive                  = 0
          BomberRock.h                      = -1
          BomberRock.v                      = -1
          RedrawGround(TheGround)
          #compute score
          LED.SpaceDotScore = LED.SpaceDotScore + LED.AsteroidPoints
        


              
      #BomberShip
      if (BomberShip.exploding == 1):
        BomberShip.Explosion.DisplayAnimated()

        #Kill bombership after explosion animation is complete
        if (BomberShip.Explosion.currentframe >= BomberShip.Explosion.frames-1):
          BomberShip.Explosion.currentframe = 0
          BomberShip.Explosion.exploding    = 0
          BomberShip.Explosion.alive        = 0
          BomberShip.exploding              = 0
          BomberShip.alive                  = 0
          RedrawGround(TheGround)
          #compute score
          LED.SpaceDotScore = LED.SpaceDotScore + LED.BomberPoints


      #HomingMissileShip
      if (HomingMissileShip.exploding == 1):
        if (HomingMissileShipExplosion.h == -1):
          LED.CenterSpriteOnShip(HomingMissileShipExplosion,HomingMissileShip)
        HomingMissileShipExplosion.DisplayAnimated()

        #Kill homing missile after explosion animation is complete
        if (HomingMissileShipExplosion.currentframe >= HomingMissileShipExplosion.frames-1):
          HomingMissileShipExplosion.currentframe = 0
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
          LED.SpaceDotScore = LED.SpaceDotScore + LED.HomingMissilePoints

      #PlayerShip
      if (PlayerShip.exploding == 1):
        PlayerShip.Explosion.h = PlayerShip.h
        PlayerShip.Explosion.v = PlayerShip.v
        PlayerShip.Explosion.DisplayAnimated()

        #Kill PlayerShip after explosion animation is complete
        if (PlayerShip.Explosion.currentframe >= PlayerShipExplosion.frames-1):
          PlayerShip.Explosion.currentframe = 0
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
        if (UFOMissile1.Explosion.currentframe >= UFOMissile1.Explosion.frames-1):
          UFOMissile1.Explosion.currentframe = 0
          UFOMissile1.Explosion.exploding    = 0
          UFOMissile1.Explosion.alive        = 0
          UFOMissile1.exploding              = 0
          UFOMissile1.alive                  = 0
          UFOMissile1.Explosion.h            = -1
          UFOMissile1.Explosion.v            = -1
          RedrawGround(TheGround)
          #compute score
          LED.SpaceDotScore = LED.SpaceDotScore + LED.AsteroidPoints

       



      #UFO Missiles need to be optimized into an array like we did with asteroids
      if (UFOMissile2.exploding == 1 ):
        if (UFOMissile2.Explosion.h == -1):
          UFOMissile2.Explosion.h = UFOMissile2.h
          UFOMissile2.Explosion.v = UFOMissile2.v
        UFOMissile2.Explosion.DisplayAnimated()

        #Kill missile after explosion animation is complete
        if (UFOMissile2.Explosion.currentframe >= UFOMissile2.Explosion.frames-1):
          UFOMissile2.Explosion.currentframe = 0
          UFOMissile2.Explosion.exploding    = 0
          UFOMissile2.Explosion.alive        = 0
          UFOMissile2.exploding              = 0
          UFOMissile2.alive                  = 0
          UFOMissile2.Explosion.h            = -1
          UFOMissile2.Explosion.v            = -1
          RedrawGround(TheGround)
          #compute score
          LED.SpaceDotScore = LED.SpaceDotScore + LED.AsteroidPoints

      #UFO Missiles need to be optimized into an array like we did with asteroids
      if (UFOMissile3.exploding == 1 ):
        if (UFOMissile3.Explosion.h == -1):
          UFOMissile3.Explosion.h = UFOMissile3.h
          UFOMissile3.Explosion.v = UFOMissile3.v
        UFOMissile3.Explosion.DisplayAnimated()

        #Kill missile after explosion animation is complete
        if (UFOMissile3.Explosion.currentframe >= UFOMissile3.Explosion.frames-1):
          UFOMissile3.Explosion.currentframe = 0
          UFOMissile3.Explosion.exploding    = 0
          UFOMissile3.Explosion.alive        = 0
          UFOMissile3.exploding              = 0
          UFOMissile3.alive                  = 0
          UFOMissile3.Explosion.h            = -1
          UFOMissile3.Explosion.v            = -1
          RedrawGround(TheGround)
          #compute score
          LED.SpaceDotScore = LED.SpaceDotScore + LED.AsteroidPoints





      #if (PlayerShip.alive == 0):
      #  PlayerShipExplosion.Animate(PlayerShip.h-2,PlayerShip.v-2,'forward',0.025)
        
      #Display animation and clock every X seconds
      #if (CheckElapsedTime(CheckTime) == 1):
      #  ScrollScreenShowLittleShipTime(LED.ScrollSleep)         
  
     
      #-------------------------------------
      # Display Score
      #-------------------------------------
      LED.DisplayScore(LED.SpaceDotScore,LED.MedGreen)


     
      #-------------------------------------
      # End of Wave 
      #-------------------------------------
      
      #check for time between armadas
      if (Wave.Alive == False):
        MovesSinceWaveStop = MovesSinceWaveStop + 1
        
        #print("Moves since wave stop:",MovesSinceWaveStop)
        if (MovesSinceWaveStop > LED.MovesBetweenWaves):
          print("--End of Wave--")
          MovesSinceWaveStop = 0
          Wave.Alive  = True


          LED.PlayerMissiles = LED.PlayerMissiles + 1
          if (LED.PlayerMissiles >= LED.MaxPlayerMissiles):
            LED.PlayerMissiles = LED.MaxPlayerMissiles
          PlayerMissiles.append(LED.Ship(-0,-0,PlayerMissileR,PlayerMissileG,PlayerMissileB,1,1,5,0,1,'PlayerMissile', 0,0))
          PlayerMissiles[-1].alive     = 0
          PlayerMissiles[-1].exploding = 0
          PlayerMissiles[-1].Explosion = copy.deepcopy(SmallExplosion)

          #increase speed of all missiles
          LED.PlayerMissileSpeed = LED.PlayerMissileSpeed -1
          if(LED.PlayerMissileSpeed <= LED.PlayerMissileMinSpeed):
            LED.PlayerMissileSpeed = LED.PlayerMissileMinSpeed

          for i in range(0,LED.PlayerMissiles):
            PlayerMissiles[i].speed = LED.PlayerMissileSpeed

          #increase speed of player ship
          PlayerShipSpeed = PlayerShipSpeed -5
          PlayerShipMinSpeed = PlayerShipMinSpeed -5
          if(PlayerShipMinSpeed <= PlayerShipAbsoluteMinSpeed):
            PlayerShipMinSpeed = PlayerShipAbsoluteMinSpeed

          if(PlayerShipSpeed <= PlayerShipAbsoluteMinSpeed):
            PlayerShipSpeed = PlayerShipAbsoluteMinSpeed

          PlayerShip.speed = PlayerShipSpeed



          #adjust speeds, lower number is faster
          LED.AsteroidMinSpeed = LED.AsteroidMinSpeed - 1
          if(LED.AsteroidMinSpeed < LED.WaveMinSpeed):
            LED.AsteroidMinSpeed = LED.WaveMinSpeed
          
          LED.AsteroidMaxSpeed = LED.AsteroidMaxSpeed - 1
          if(LED.AsteroidMaxSpeed < LED.WaveMinSpeed + LED.WaveSpeedRange ):
            LED.AsteroidMaxSpeed = LED.WaveMinSpeed + LED.WaveSpeedRange

          LED.DisplayLevel(Wave.WaveCount,LED.MedBlue)


          #launch next wave of asteroids, maybe show some fancy graphics here
          Wave.AsteroidCount = Wave.AsteroidCount + 1
          Wave.WaveCount     = Wave.WaveCount + 1

          if(Wave.AsteroidCount  >= LED.AsteroidsInWaveMax):
            Wave.AsteroidCount    = LED.AsteroidsInWaveMax

          Wave.CreateAsteroidWave()

          Wave.Alive        = True
          
          print ("Wave:",Wave.WaveCount,"Asteroids in wave:",Wave.AsteroidCount)
          print("----")
          

        
      #time.sleep(LED.MainSleep / 25)
      
      








#------------------------------------------------------------------------------
#- DOT INVADERS 
#-
#------------------------------------------------------------------------------

#right side area of LED display will be used for non game items
RightSideSize = 20


def ShowDropShip(h,v,action,speed):
   
  print("ShowDropShip:",action)
  LED.setpixel(h,v,PlayerShipR,PlayerShipG,PlayerShipB)
  #Canvas = unicorn.get_pixels()
  LED.setpixel(h,v,0,0,0)
  #Buffer2 = unicorn.get_pixels()
  LED.setpixel(h,v,PlayerShipR,PlayerShipG,PlayerShipB)
  
  if (action == 'pickup'):
    
    DropShip.Animate(h-2,v+1,'forward',speed)
    DropShip.Animate(h-2,v+1,'forward',speed)
    DropShip.Animate(h-2,v+1,'forward',speed)
    DropShip.Animate(h-2,v+1,'forward',speed)
    DropShip.Animate(h-2,v+1,'forward',speed)
    DropShip.Animate(h-2,v+1,'forward',speed)
    DropShip.Animate(h-2,v+1,'forward',speed)
    DropShip.Animate(h-2,v+1,'forward',speed)
    DropShip.Animate(h-2,v+1,'forward',speed)

    #print("Sleeping")
    for y in range(v-5,-10,-1):
      DropShip.Animate(h-2,y,'forward',speed)
      DropShip.Animate(h-2,y,'forward',speed)
      DropShip.Animate(h-2,y,'forward',speed)
  else:
    for y in range(-14,v-5):
      DropShip.Animate(h-2,y,'forward',speed)
      DropShip.Animate(h-2,y,'forward',speed)
      DropShip.Animate(h-2,y,'forward',speed)

    DropShip.Animate(h-2,v+1,'forward',speed)
    DropShip.Animate(h-2,v+1,'forward',speed)
    DropShip.Animate(h-2,v+1,'forward',speed)
    DropShip.Animate(h-2,v+1,'forward',speed)
    DropShip.Animate(h-2,v+1,'forward',speed)
    DropShip.Animate(h-2,v+1,'forward',speed)
    DropShip.Animate(h-2,v+1,'forward',speed)
    DropShip.Animate(h-2,v+1,'forward',speed)
    DropShip.Animate(h-2,v+1,'forward',speed)
    
    
    for y in range(v-5,-10,-1):
      DropShip.Animate(h-2,y,'forward',speed)
      DropShip.Animate(h-2,y,'forward',speed)
      DropShip.Animate(h-2,y,'forward',speed)




#Enemy ship is the UFO
def MoveUFO(UFOShip):
  #print ("MBS - Name Direction HV:",BomberShip.name,Ship.direction,Ship.h,Ship.v)
  
  #Player ships always points up, enemy ships point down
  h = UFOShip.h
  v = UFOShip.v
  
  #print("checking border")
  if ((UFOShip.direction == 2 and UFOShip.h >= LED.HatWidth-RightSideSize-2) or
      (UFOShip.direction == 4 and UFOShip.h < 2)):
    UFOShip.direction = LED.ReverseDirection(UFOShip.direction)


  NewH, NewV = LED.CalculateDotMovement(UFOShip.h,UFOShip.v,UFOShip.direction)
  UFOShip.Erase()
  UFOShip.h, UFOShip.v = NewH, NewV
  UFOShip.Display()
  

  return 





def PutArmadaOnPlayfield(Armada,ArmadaHeight,ArmadaWidth,Playfield):
  #we need to examine the armada, and see which ones are visible and should be put on the playfield
  r = Armada[1][1].r
  g = Armada[1][1].g
  b = Armada[1][1].b
  print(ArmadaHeight,ArmadaWidth)
  for x in range (ArmadaWidth):
    for y in range (ArmadaHeight):
      if(Armada[y][x].alive == 1):
        Playfield[Armada[y][x].v][Armada[y][x].h] = Armada[y][x]
        LED.TheMatrix.SetPixel(Armada[y][x].h,Armada[y][x].v,255,255,255)
        time.sleep(0.01)
        LED.TheMatrix.SetPixel(Armada[y][x].h,Armada[y][x].v,r,g,b)

        
        

def DisplayPlayfield(Playfield):
  print("Display Playfield")
  for x in range (LED.HatWidth):
    for y in range (LED.HatHeight):
      if (Playfield[y][x].name != 'EmptyObject'):
        print("Playfield: ",Playfield[y][x].name)
        Playfield[y][x].Display()
        if (Playfield[y][x].name == 'ArmadaShip'):
          LED.FlashDot2(x,y,0.1)
        
        
        
        
def CreateSpecialArmada(ShowTime=True):
    #Does the same as Display, but does not call show(), allowing calling function to further modify the Buffer
    #before displaying
    x = 0,
    y = 0
    ZoomFactor = 2

    
    # Random medium brightness color
    #7 11 15 19 23 27 32

    
    color = random.randint(1,7) * 4 + 3
    r,g,b = LED.ColorList[color]
    
    
    #Show time or word
    if ((random.randint(1,2) == 1) or ShowTime == True):
      TheArmadaSprite = LED.CreateClockSprite(12)
    else:
      WordList=("PACMAN","ALIEN","DARTH","VADER","1943","USA","CAN","AUS","NZ","UK","[-O-]","QBERT","KONG",
                "IOI",":)","BARF","LOLZ")
      TheMessage = WordList[random.randint(1,len(WordList)-1)]
      print ("Armada Message:",TheMessage)
      TheArmadaSprite = LED.CreateBannerSprite(TheMessage)
      print ("Armada launched!")
      
      #calculate zoomfactor
      if(len(TheMessage) >= 5):
        ZoomFactor = 1
      elif (len(TheMessage) >= 3 and len(TheMessage) <= 4):
        ZoomFactor = 2
      else:
        ZoomFactor = 3
    


    #if the HH has double digits, sprite is too wide.  Trim the left empty columns.
    ArmadaHeight = TheArmadaSprite.height * ZoomFactor
    ArmadaWidth  = TheArmadaSprite.width  * ZoomFactor
    Armada = [[ LED.Ship(1,1,r,g,b,2,3,50,0,0,'ArmadaShip', 0,0) for i in range(ArmadaWidth+ZoomFactor*2)] for i in range(ArmadaHeight+ZoomFactor*2)]
   

    for count in range (0,(TheArmadaSprite.width * TheArmadaSprite.height)):
      y,x = divmod(count,TheArmadaSprite.width)
      #print("TheArmadaSprite.width count y x:",TheArmadaSprite.width, count,y,x)
      y = y * ZoomFactor
      x = x * ZoomFactor

      for zv in range (0,ZoomFactor):
        for zh in range (0,ZoomFactor):
          H = x+zh
          V = y+zv
          #print("Count:",count,"xy",x,y,"HV",H,V)
  
          if TheArmadaSprite.grid[count] == 1:
            Armada[V][H].alive = 1
            Armada[V][H].name = 'ArmadaShip'
            
          else:
            Armada[V][H].alive = 0
      
   
    return Armada,ArmadaHeight,ArmadaWidth;



        
def DotInvadersCheckBoundary(h,v):
  BoundaryHit = 0
  #On the larger Matrix LED displays (64x32) we don't go all the way over to the right
  #because that looks weird.

  if (v < 0 or v > LED.HatHeight-1 or h < 0 or h > LED.HatWidth-RightSideSize):
    BoundaryHit = 1
  return BoundaryHit;



def DotInvadersExplodeMissile(Ship,Playfield,increment):
  Ship.r = Ship.r + increment
  Ship.g = 0 #Ship.g + increment
  Ship.b = 0 #Ship.b + increment

  #After explosion, reset colors
  if (Ship.r >= 255 or Ship.g >= 255 or Ship.b >= 255):
    if (Ship.name == 'PlayerMissile'):
      Ship.r = PlayerMissileR
      Ship.g = PlayerMissileG
      Ship.b = PlayerMissileB
    elif (Ship.name == 'Asteroid'):
      Ship.r = LED.SDDarkOrangeR
      Ship.g = LED.SDDarkOrangeG
      Ship.b = LED.SDDarkOrangeB
    elif (Ship.name == 'UFOMissile'):
      Ship.r = PlayerMissileR
      Ship.g = PlayerMissileG
      Ship.b = PlayerMissileB
    elif (Ship.name == 'UFO'):
      Ship.r = LED.SDDarkPurpleR
      Ship.g = LED.SDDarkPurpleG
      Ship.b = LED.SDDarkPurpleB

    Ship.exploding = 0
    Ship.alive     = 0
    #print ("Ship Exploded")
    Ship.Erase()
    Playfield[Ship.v][Ship.h].alive = 0
    Playfield[Ship.v][Ship.h] = Empty

  if (Ship.exploding == 1):
    LED.setpixel(Ship.h,Ship.v,255,255,255)
    LED.setpixel(Ship.h,Ship.v,Ship.r,Ship.g,Ship.b)
    #print("EM - Ship.exploding: ",Ship.exploding)
    #print("EM - After: ",Ship.name, "HV",Ship.h,Ship.v," rgb",Ship.r,Ship.g,Ship.b)
  
  



def MoveArmada(Armada,ArmadaHeight,ArmadaWidth,Playfield):
  #every ship in the armada will look in the directon they are travelling
  #if a wall is found, drop down a level and reverse direction
  #if you hit the ground, game over

  ScanH = 0
  ScanV = 0
  direction = 0
  x = 0
  y = 0
  #print ("MA - moving armada")
  BorderDetected = 0
  LowestV = 0


#  print ("=====***************************************************================")
#  for x in range(ArmadaWidth-1,-1,-1):
#    for y in range (ArmadaHeight-1,-1,-1):
#      h = Armada[y][x].h
#      v = Armada[y][x].v
#      LED.FlashDot(h,v,0.005)
#      print ("XY hv Alive Armada.Name Playfield.Name",x,y,h,v,Armada[y][x].alive,Armada[y][x].name,Playfield[v][h].name)
#  print ("=====***************************************************================")



  
  #Check for border
  for x in range(ArmadaWidth-1,-1,-1):
    for y in range (ArmadaHeight-1,-1,-1):
      if (Armada[y][x].alive == 1):
        #print ("MA - Calculating Armada[y][x].hv: ",x,y,Armada[y][x].h,Armada[y][x].v)
        h = Armada[y][x].h
        v = Armada[y][x].v
        direction = Armada[y][x].direction
        ScanH,ScanV = LED.CalculateDotMovement(h,v,direction)
        
        #we just want to know the lowest armada ship, for firing missiles
        if (LowestV < v):
          LowestV = v
        #if (DotInvadersCheckBoundary(ScanH, ScanV) == 0):
        #FlashDot(h,v,0.005)
          
        #print ("MA - checking xy ScanH ScanV: ",x,y,ScanH,ScanV)
        if (DotInvadersCheckBoundary(ScanH, ScanV) == 1):
          BorderDetected = 1
          #print ("MA - border detected - inner break")
          break
      if (DotInvadersCheckBoundary(ScanH, ScanV) == 1):
        BorderDetected = 1
        #print ("MA - border detected - outer break")
        break
  
  #Move
  if (BorderDetected == 1):
    direction = LED.ReverseDirection(direction)
  
  if (direction == 2):
    for x in range(ArmadaWidth-1,-1,-1):
      for y in range (ArmadaHeight-1,-1,-1):
        if (Armada[y][x].alive == 1):

          OldH = Armada[y][x].h
          OldV = Armada[y][x].v
          #print ("MA  - OldH OldV direction",OldH,OldV,direction)
          
          NewH, NewV = LED.CalculateDotMovement(OldH,OldV,direction)
          if(BorderDetected == 1):
            NewH = OldH
            NewV = NewV + 1
          Armada[y][x].h = NewH
          Armada[y][x].v = NewV

          LED.setpixel(OldH,OldV,0,0,0)
          Armada[y][x].Display()
          Armada[y][x].direction = direction

         
          Playfield[OldV][OldH] = Empty


          #print ("NewH NewV",NewH,NewV)
          if (NewV <= LED.HatHeight - 2):
            Playfield[NewV][NewH] = Armada[y][x]
          else:
            print ("Game Over")
          
  else:
    for x in range(ArmadaWidth):
      for y in range (ArmadaHeight-1,-1,-1):
        if (Armada[y][x].alive == 1):
  
          OldH = Armada[y][x].h
          OldV = Armada[y][x].v
          #print ("MA  - OldH OldV direction",OldH,OldV,direction)
          
          NewH, NewV = LED.CalculateDotMovement(OldH,OldV,direction)
          if(BorderDetected == 1):
            NewH = OldH
            NewV = NewV + 1
            NewV = NewV 
          Armada[y][x].h = NewH
          Armada[y][x].v = NewV

          LED.setpixel(OldH,OldV,0,0,0)
          Armada[y][x].Display()
          Armada[y][x].direction = direction

          Playfield[OldV][OldH] = Empty
          Playfield[NewV][NewH] = Armada[y][x]
          
          
  #Count Armada alive
  ArmadaCount = 0
  for x in range (ArmadaWidth):
    for y in range (ArmadaHeight):
      if (Armada[y][x].alive == 1):
        ArmadaCount = ArmadaCount + 1
  

  #Drop missiles
  h,v = NewH, NewV
  if (UFOMissile1.alive == 0 and UFOMissile1.exploding == 0):
    UFOMissile1.h = h
    UFOMissile1.v = LowestV
    UFOMissile1.alive = 1
  elif (UFOMissile2.alive == 0 and UFOMissile2.exploding == 0 and ArmadaCount > 1):
    UFOMissile2.h = h
    UFOMissile2.v = LowestV
    UFOMissile2.alive = 1

      
def DotInvadersMoveMissile(Missile,Ship,Playfield):
  global Empty
  #print ("MM - MoveMissile:",Missile.name)
  
  #Record the current coordinates
  h = Missile.h
  v = Missile.v

  
  #Missiles simply drop to bottom and kablamo!
  #FF (one square in front of missile direction of travel)
  ScanH, ScanV = LED.CalculateDotMovement(Missile.h,Missile.v,Missile.scandirection)
  Item = DotInvadersScanSpaceDot(ScanH,ScanV)
  
  #print("Item: ",Item)
  
  #Priority
  # 1 Hit target
  # 2 See if we are hit by enemy missle
  # 3 Move forward
  

  #See if other target ship is hit
  if (Item  in ('Player1','ArmadaShip','UFO','UFOMissile','Bunker')):
    #target hit, kill target
    #print ("DIMM - Item Name", Item, Playfield[ScanV][ScanH].name)
    Playfield[ScanV][ScanH].alive = 0
    Playfield[ScanV][ScanH]= Empty
    LED.setpixel(ScanH,ScanV,0,0,0)
    LED.setpixel(h,v,0,0,255)
    if (Item == 'EnemyShip'):
      Ship.score = Ship.score + random.randint(1,11)
    else:
      Ship.score = Ship.score + 1


    Missile.h = ScanH
    Missile.v = ScanV
    #Playfield[Missile.h][Missile.v] = Missile
    Missile.Display()
    Missile.exploding = 1
    Missile.alive = 0
    

  
  #Player missiles fire off into space
  #Enemy missiles explode on ground
  elif (Item == 'border' and Missile.name == 'PlayerMissile'):
    #print ("MM - Missile hit border")
    Missile.alive  = 0
    Missile.exploding = 0
    Missile.Erase()
  elif (Item == 'border' and (Missile.name == 'UFOMissile' or Missile.name == 'Asteroid')):
    #print ("MM - Missile hit border")
    Missile.alive  = 0
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
    

  if ((h != Missile.h or v != Missile.v) or
     (Missile.alive == 0)):
    Playfield[v][h] = Empty
    LED.setpixel(h,v,0,0,0)
    #print ("MM - Erasing Missile")
  #unicorn.show()
  #SendBufferPacket(RemoteDisplay,LED.HatHeight,LED.HatWidth)
  
  return 
    



def DotInvadersScanSpaceDot(h,v):
# border
# empty
# wall
  

  #print ("SSD - HV:",h,v)
  Item = ''
  OutOfBounds = DotInvadersCheckBoundary(h,v)
  
  if (OutOfBounds == 1):
    Item = 'border'
#    print ("Border found HV: ",h,v)
  else:
    #FlashDot(h,v,0.01)
    Item = Playfield[v][h].name
  return Item


        
def DotInvaderScanShip(h,v,direction,Playfield):
  ScanDirection = 0
  ScanH         = 0
  ScanV         = 0
  Item          = ''
  ItemList      = ['NULL']
  
  
  # 37 38 39
  #    ...
  #    14
  # 11 12 13
  #    10
  #     9
  #     8
  #     7
  #     6
  #  2  3  4
  #  1     5
  #
  
  
  #LL 1
  ScanDirection = LED.TurnLeft(direction)
  ScanH, ScanV = LED.CalculateDotMovement(h,v,ScanDirection)
  Item = DotInvadersScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)
  #print ("DISS1 - hv ScanH ScanV Item",h,v,ScanH,ScanV, Item)
  
  #LF 2
  ScanDirection =  LED.TurnRight(ScanDirection)
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = DotInvadersScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)
  #print ("DISS2 - hv ScanH ScanV Item",h,v,ScanH,ScanV, Item)
  
  #FF 3
  ScanDirection =  LED.TurnRight(ScanDirection)
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = DotInvadersScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)
  #print ("DISS3 - hv ScanH ScanV Item",h,v,ScanH,ScanV, Item)
  
  #FR 4
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = DotInvadersScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)
  #print ("DISS4 - hv ScanH ScanV Item",h,v,ScanH,ScanV, Item)
  
  #RR 5
  ScanDirection =  LED.TurnRight(ScanDirection)
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = DotInvadersScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)
  #print ("DISS5 - hv ScanH ScanV Item",h,v,ScanH,ScanV, Item)

  #F1 6
  ScanDirection = LED.ReverseDirection(ScanDirection)
  ScanH, ScanV  = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  ScanDirection = LED.TurnLeft(ScanDirection)
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  ScanDirection =  LED.TurnRight(ScanDirection)
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = DotInvadersScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)
  #print ("DISS6 - hv ScanH ScanV Item",h,v,ScanH,ScanV, Item)

  #F2 7
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = DotInvadersScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)
  #print ("DISS7 - hv ScanH ScanV Item",h,v,ScanH,ScanV, Item)
  
  #F3 8
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = DotInvadersScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)
  #print ("DISS8 - hv ScanH ScanV Item",h,v,ScanH,ScanV, Item)
  
  #F4 9
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = DotInvadersScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)
  #print ("DISS9 - hv ScanH ScanV Item",h,v,ScanH,ScanV, Item)

  #F5 10
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = DotInvadersScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)
  #print ("DISS10 - hv ScanH ScanV Item",h,v,ScanH,ScanV, Item)

  #F6 11
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  ScanDirection = LED.TurnLeft(ScanDirection)
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = DotInvadersScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)
  #print ("DISS11 - hv ScanH ScanV Item",h,v,ScanH,ScanV, Item)

  #F7 12
  ScanDirection = LED.ReverseDirection(ScanDirection)
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = DotInvadersScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)
  #print ("DISS12 - hv ScanH ScanV Item",h,v,ScanH,ScanV, Item)

  #F8 13
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = DotInvadersScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)
  #print ("DISS13 - hv ScanH ScanV Item",h,v,ScanH,ScanV, Item)

  
  #14 -- new additions since moving to larger grid
  ScanDirection = LED.ReverseDirection(ScanDirection)
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  ScanDirection =  LED.TurnRight(ScanDirection)
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = DotInvadersScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)


  
  #15:36
  for j in range(1,23):
    ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
    Item = DotInvadersScanSpaceDot(ScanH,ScanV)
    ItemList.append(Item)
    #LED.TheMatrix.SetPixel(ScanH,ScanV,0,0,50)


  #37
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  ScanDirection = LED.TurnLeft(ScanDirection)
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = DotInvadersScanSpaceDot(ScanH,ScanV)
  #LED.TheMatrix.SetPixel(ScanH,ScanV,255,255,0)
  ItemList.append(Item)
  


  #38
  ScanDirection = LED.ReverseDirection(ScanDirection)
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = DotInvadersScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)
  #LED.TheMatrix.SetPixel(ScanH,ScanV,255,0,0)

  #39
  ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
  Item = DotInvadersScanSpaceDot(ScanH,ScanV)
  ItemList.append(Item)
  #LED.TheMatrix.SetPixel(ScanH,ScanV,255,255,0)

  return ItemList;


def DotInvaderMovePlayerShip(Ship,Playfield):
  #print ("DIMPS - moveship HV Direction:",Ship.h,Ship.v,Ship.direction)
  
  #Player ships always points up, enemy ships point down
  h = Ship.h
  v = Ship.v
  ItemList = []
  #Scan all around, make decision, move
  ItemList = DotInvaderScanShip(Ship.h,Ship.v,Ship.scandirection,Playfield)
  
  #print("MPS - ItemList",ItemList)
  #print("MPS - Ship.name HV",Ship.name,Ship.h,Ship.v)
  #get possible items, then prioritize

  #Priority
  # 1 Evade close objects
  # 2 Blast far objects

  #If UFO is detected, fire missile!
  if ("ArmadaShip" in ItemList or "UFO" in ItemList or "UFOMissile" in ItemList ):
    if (ItemList[3] != "Bunker" and ItemList[6] != "Bunker"):

      if (PlayerMissile1.alive == 0 and PlayerMissile1.exploding == 0):
        #print ("MPS - UFO/Bomber/aseroid Detected PlayerMissile1.alive:",PlayerMissile1.alive)
        PlayerMissile1.h = h
        PlayerMissile1.v = v
        PlayerMissile1.alive = 1
        PlayerMissile1.exploding = 0
        Ship.score = Ship.score + 1
          
  #    elif (PlayerMissile2.alive == 0 and PlayerMissile2.exploding == 0):
  #      #print ("MPS - UFO or asteroid Detected PlayerMissile1.alive:",PlayerMissile1.alive)
  #      PlayerMissile2.h = h
  #      PlayerMissile2.v = v
  #      PlayerMissile2.alive = 1
  #      PlayerMissile2.exploding = 0

  #Follow UFO
  #slow down if ahead of UFO, speed up if behind
  if (ItemList[37] == 'UFO' or ItemList[37] == 'ArmadaShip'):
    #follow the bomber or UFO
    
    #print("H",h)
    print("Playfield object HV Name:",Playfield[0][h-1].h,Playfield[0][h-1].v,Playfield[0][h-1].name)

    Ship.direction = Playfield[0][h-1].direction
    #print ("MPS - ENEMY TO LEFT Enemy.name HV direction speed",Playfield[0][h-1].name,Playfield[0][h-1].h,Playfield[0][h-1].v, Playfield[0][h-1].direction,Playfield[0][h-1].speed)
    if (Playfield[0][h-1].direction == 4):
      AdjustSpeed(Ship,'fast',5)
    elif (Playfield[0][h-1].direction == 2):
      AdjustSpeed(Ship,'slow',1)
    
  elif (ItemList[39] == 'UFO' or ItemList[39] == 'ArmadaShip'):

    #for x in range (0,LED.HatWidth):
      #for y in range (0,LED.HatHeight):
        #print("Playfield[x][y].name HV speed direction: ",x,y,Playfield[x][y].name,Playfield[x][y].h,Playfield[x][y].v,Playfield[x][y].speed,Playfield[x][y].direction)


    Ship.direction = Playfield[0][h+1].direction
    #print ("MPS - ENEMY TO RIGHT Enemy.name HV direction",Playfield[0][h+1].name,Playfield[0][h+1].h,Playfield[0][h+1].v, Playfield[0][h+1].direction)
    if (Playfield[0][h+1].direction == 2):
      #print ("MPS - adjusting speed fast 3")
      AdjustSpeed(Ship,'fast',4)
    elif (Playfield[0][h+1].direction == 4):
      #print ("MPS - adjusting speed slow 1")
      AdjustSpeed(Ship,'slow',1)
  
    
     
  
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
  elif ((Ship.direction == 4 and ((ItemList[1] != 'EmptyObject' and ItemList[1] != 'Bunker') or (ItemList[2] != 'EmptyObject'and ItemList[2] != 'Bunker'))) or
        (Ship.direction == 2 and ((ItemList[5] != 'EmptyObject' and ItemList[5] != 'Bunker') or (ItemList[4] != 'EmptyObject' and ItemList[4] != 'Bunker')))):      
    Ship.direction = LED.ReverseDirection(Ship.direction)
    #print("MPS - object in path, reversed direction")
    #print("MPS - 3Ship.direction: ",Ship.direction)
    

  # - speed up and move if object is directly above
  elif ((Ship.direction == 4 and (ItemList[3] != 'EmptyObject' and ItemList[1] == 'EmptyObject')) or
        (Ship.direction == 2 and (ItemList[3] != 'EmptyObject' and ItemList[5] == 'EmptyObject'))):
    AdjustSpeed(Ship,'fast',8)
    Ship.h, Ship.v =  LED.CalculateDotMovement(Ship.h,Ship.v,Ship.direction)

  # - travelling left, move if empty
  # - travelling right, move if empty
  # - randomly switch directions
  elif ((ItemList[1] == 'EmptyObject' and Ship.direction == 4) or 
        (ItemList[5] == 'EmptyObject' and Ship.direction == 2 )):
    if ((random.randint(0,20) == 1) and Ship.h != 0 and Ship.h != 15):
      Ship.direction = LED.ReverseDirection(Ship.direction)
    
    #make sure we are not going off the edge
    h1,v1 = LED.CalculateDotMovement(Ship.h,Ship.v,Ship.direction)
    if(DotInvadersCheckBoundary(h1,v1) == 0):
      Ship.h, Ship.v =  h1, v1

    #print("MPS - Travelling, move if empty")


  #if nothing nearby, and near the middle, stop moving
  if (ItemList[1]  == 'EmptyObject' and
      ItemList[2]  == 'EmptyObject' and
      ItemList[3]  == 'EmptyObject' and
      ItemList[4]  == 'EmptyObject' and
      ItemList[5]  == 'EmptyObject' and
      ItemList[6]  == 'EmptyObject' and
      ItemList[7]  == 'EmptyObject' and
      ItemList[8]  == 'EmptyObject' and
      ItemList[9]  == 'EmptyObject' and
      ItemList[10] == 'EmptyObject' and
      ItemList[11] == 'EmptyObject' and
      ItemList[12] == 'EmptyObject' and
      ItemList[13] == 'EmptyObject' and
      ItemList[14] == 'EmptyObject' and
      ItemList[15] == 'EmptyObject' and
      ItemList[16] == 'EmptyObject' and
      ItemList[17] == 'EmptyObject' and
      ItemList[18] == 'EmptyObject' and
      ItemList[19] == 'EmptyObject' and
      ItemList[20] == 'EmptyObject' and
      ItemList[21] == 'EmptyObject' and 
      Ship.h >= 10 and Ship.h <= (LED.HatWidth - RightSideSize)-10):
    if (random.randint (0,10) != 1):
      #print ("MPS - Staying in the middle")
      Ship.h = h
      Ship.v = v
    
  #print("MPS - 6Ship.direction: ",Ship.direction)

  #print("MPS - OldHV: ",h,v, " NewHV: ",Ship.h,Ship.v, "direction: ",Ship.direction)
  Playfield[Ship.v][Ship.h]= Ship
  Ship.Display()
  
  if ((h != Ship.h or v != Ship.v) or
     (Ship.alive == 0)):
    Playfield[v][h] = Empty
    LED.setpixel(h,v,0,0,0)
    #print ("MPS - Erasing Player")
  #unicorn.show()
  #SendBufferPacket(RemoteDisplay,LED.HatHeight,LED.HatWidth)

  #print("MPS - 7Ship.direction: ",Ship.direction)

  return 
        

def ShowFireworks(FireWorksExplosion,count,speed):
  x = 0
  h = 0
  v = 0
  for x in range(1,count):
    h = random.randint(2,12)
    v = random.randint(0,7)
    FireWorksExplosion.Animate(h,v,'forward',speed)        


        
          
def PlayDotInvaders():
  
  #Local variables
  moves       = 0
  Finished    = 'N'
  LevelCount  = 1
  Playerh     = 0
  Playerv     = 0
  SleepTime   = LED.MainSleep / 4
  ChanceOfEnemyShip = 800


  PlayerShipR = LED.SDMedBlueR
  PlayerShipG = LED.SDMedBlueG
  PlayerShipB = LED.SDMedBlueB
  PlayerMissileR = LED.SDMedWhiteR
  PlayerMissileG = LED.SDMedWhiteG
  PlayerMissileB = LED.SDMedWhiteB


  #define sprite objects
  BunkerRows  = 4
  BunkerBases = 4
  BunkerWidth = 5
  BunkerStartH = 3
  BunkerSpacing = round((LED.HatWidth - RightSideSize)/ BunkerBases)
  b           = 0
  BunkerDots  = ([])
  BunkerDots  = [ (0,0,0) for i in range(BunkerWidth * BunkerRows * BunkerBases)]

  i = 0
  y = LED.HatHeight-2 - BunkerRows
  for r in range(BunkerRows):
    for x in range(LED.HatWidth - RightSideSize):
      a,b = divmod(x,BunkerSpacing)
      if(b == 0):
        
        for j in range(BunkerWidth):
          #def __init__(self,h,v,r,g,b,direction,scandirection,speed,alive,lives,name,score,exploding):
          #print("Making Bunker:",i, "XY",x,y)
          BunkerDots[i]  = LED.Ship( x + BunkerStartH,y + r,LED.SDLowGreenR,LED.SDLowGreenG,LED.SDLowGreenB,1,1,999,1,5,'Bunker', 0,0)    
          x = x + 1
          i = i + 1
  BunkerDotCount = i    
  #print("Bunkers created:",i)
  

    
    
  
  


  PlayerShip  = LED.Ship( 7,15,PlayerShipR,PlayerShipG,PlayerShipB,4,1,10,1,5,'Player1', 0,0)
  EnemyShip   = LED.Ship(0,0,LED.SDLowPurpleR,LED.SDLowPurpleG,LED.SDLowPurpleB,4,3,50,0,3,'UFO', 0,0)
  #LED.Ship(15,0,LED.SDLowPurpleR,LED.SDLowPurpleG,LED.SDLowPurpleB,4,3,50,0,3,'UFO', 0,0)
  Empty      = LED.Ship(-1,-1,0,0,0,0,1,0,0,0,'EmptyObject',0,0)


 
  #CreateExplosionSprites
  FireworksExplosion  = copy.deepcopy(PlayerShipExplosion)  
  BomberShipExplosion = copy.deepcopy(PlayerShipExplosion)  
  
  #Title
  LED.ClearBigLED()
  #LED.ShowScrollingBanner2("DotInvader",(LED.MedGreen),LED.ScrollSleep)
  #ShowSpaceInvaderTime(LED.ScrollSleep)
  #TinyInvader.ScrollAcrossScreen(0,5,'left',LED.ScrollSleep)

  FirstTime = True

  #Main Game Loop
  while (Finished == 'N'):

    #First time through, always show the time
    #Armada, ArmadaHeight, ArmadaWidth = CreateSpecialArmada(FirstTime)
    Armada, ArmadaHeight, ArmadaWidth = CreateSpecialArmada(False)
    FirstTime = False

    # Set initial starting positions
    for x in range (ArmadaWidth):
      for y in range(ArmadaHeight):
        Armada[y][x].h = x + (((LED.HatWidth - RightSideSize) // 2) - ((ArmadaWidth ) //2))
        Armada[y][x].v = y + 1
        #Armada[y][x].alive = 1
    ArmadaSpeed = 125
    ArmadaAlive = 1

    
    
    LED.ClearBigLED()
    LevelCount = LevelCount + 1
    #ShowLevelCount(LevelCount)
    

    
    #Reset Variables between rounds
    LevelFinished     = 'N'
    moves             = 1
    PlayerShip.alive  = 1
    PlayerShip.speed  = PlayerShipSpeed
    PlayerShip.h      = (LED.HatWidth - RightSideSize)  // 2
    PlayerShip.v      = LED.HatHeight -1
    PlayerMissile1.speed = 2
    if (random.randint(0,2) == 1):
      PlayerShip.direction = 2
    else:
      PlayerShip.direction = 4
    EnemyShip.alive   = 0
    UFOMissile1.alive = 0
    UFOMissile2.alive = 0
    EnemyShip.speed   = random.randint (100,500)
    
    #ShowDropShip(PlayerShip.h,PlayerShip.v,'dropoff',LED.ScrollSleep * 0.25)


    #Speed up last life for player
    if (PlayerShip.lives == 1):
      PlayerShip.speed = 1

    
    #Reset colors
    UFOMissile1.r = PlayerMissileR
    UFOMissile1.g = PlayerMissileG
    UFOMissile1.b = PlayerMissileB
    UFOMissile2.r = PlayerMissileR
    UFOMissile2.g = PlayerMissileG
    UFOMissile2.b = PlayerMissileB
    PlayerMissile1.r     = PlayerMissileR
    PlayerMissile1.g     = PlayerMissileG
    PlayerMissile1.b     = PlayerMissileB
    PlayerMissile1.alive = 0

    
    #Reset Playfield
    for x in range (0,LED.HatWidth):
      for y in range (0,LED.HatHeight):
        #print ("XY",x,y)
        Playfield[y][x] = Empty



    #Put items on Playfield
    print("Playership vh",PlayerShip.v,PlayerShip.h)
    Playfield[PlayerShip.v][PlayerShip.h] = PlayerShip
    PutArmadaOnPlayfield(Armada,ArmadaHeight,ArmadaWidth,Playfield)
    #DisplayPlayfield(Playfield)

        
    
    #Draw Bunkers
    for i in range(BunkerDotCount):
      #print("Bunker:",i)
      Playfield[BunkerDots[i].v][BunkerDots[i].h] = BunkerDots[i]
      BunkerDots[i].alive = 1
      #BunkerDots[i].Flash()
      LED.FlashDot(BunkerDots[i].h,BunkerDots[i].v,0.01)
      BunkerDots[i].Display()

    
    # Main timing loop
    while (LevelFinished == 'N' and PlayerShip.alive == 1):
      moves = moves + 1

      #Check for keyboard input
      m,r = divmod(moves,KeyboardSpeed)
      if (r == 0):
        Key = LED.PollKeyboard()
        ProcessKeypress(Key)
        if (Key == 'q'):
          LevelFinished = 'Y'
          Finished      = 'Y'
          PlayerShip.alive   = 0
          return

        
      
#      print ("=================================================")
#      for H in range(0,LED.HatWidth-1):
#        for V in range (0,LED.HatWidth-1):
#          if (Playfield[v][h].name != 'EmptyObject'):
#            print ("Playfield: HV Name Alive",H,V,Playfield[v][h].name,Playfield[v][h].alive)
#      print ("=================================================")
      

      
      #Spawn EnemyShip
      m,r = divmod(moves,ChanceOfEnemyShip)
      if (r == 0 and EnemyShip.alive == 0):
        #print ("Spawning UFO")
        EnemyShip.alive = 1
        EnemyShip.direction = LED.ReverseDirection(EnemyShip.direction)
        if (EnemyShip.direction == 2):
          EnemyShip.h = 0
          EnemyShip.v = 0
        else:
          EnemyShip.h = LED.HatWidth - RightSideSize-1
          EnemyShip.v = 0
        EnemyShip.Display()
      
      
      
      if (PlayerShip.alive == 1):
        #print ("M - Playership HV speed alive exploding direction: ",PlayerShip.h, PlayerShip.v,PlayerShip.speed, PlayerShip.alive, PlayerShip.exploding, PlayerShip.direction)
        m,r = divmod(moves,PlayerShip.speed)
        if (r == 0):
          DotInvaderMovePlayerShip(PlayerShip,Playfield)
          i = random.randint(0,5)
          if (i >= 0):
            AdjustSpeed(PlayerShip,'fast',1)
          #print ("M - Player moved?")
          
            
      
      if (EnemyShip.alive == 1):
        m,r = divmod(moves,EnemyShip.speed)
        if (r == 0):
          if ((EnemyShip.h == 0  and EnemyShip.direction == 4)
            or EnemyShip.h == LED.HatWidth - RightSideSize -1 and EnemyShip.direction == 2):
            EnemyShip.alive = 0
            Playfield[EnemyShip.v][EnemyShip.h] = Empty
            LED.setpixel(EnemyShip.h,EnemyShip.v,0,0,0)
          else:
            MoveUFO(EnemyShip)
        
          

      if (ArmadaAlive == 1):
        m,r = divmod(moves,ArmadaSpeed)
        if (r == 0):
          MoveArmada(Armada,ArmadaHeight,ArmadaWidth,Playfield)
        
          
          
      if (UFOMissile1.alive == 1 and UFOMissile1.exploding == 0):
        m,r = divmod(moves,UFOMissile1.speed)
        if (r == 0):
          DotInvadersMoveMissile(UFOMissile1,PlayerShip,Playfield)

      if (UFOMissile2.alive == 1 and UFOMissile2.exploding == 0):
        m,r = divmod(moves,UFOMissile2.speed)
        if (r == 0):
          DotInvadersMoveMissile(UFOMissile2,PlayerShip,Playfield)

      if (UFOMissile3.alive == 1 and UFOMissile3.exploding == 0):
        m,r = divmod(moves,UFOMissile3.speed)
        if (r == 0):
          DotInvadersMoveMissile(UFOMissile3,PlayerShip,Playfield)

          
      if (PlayerMissile1.alive == 1 and PlayerMissile1.exploding == 0):
        m,r = divmod(moves,PlayerMissile1.speed)
        if (r == 0):
          DotInvadersMoveMissile(PlayerMissile1,PlayerShip,Playfield)

#      if (PlayerMissile2.alive == 1 and PlayerMissile2.exploding == 0):
#        m,r = divmod(moves,PlayerMissile2.speed)
#        if (r == 0):
#          DotInvadersMoveMissile(PlayerMissile2,PlayerShip,Playfield)

          
 
      
          
          

        

      #Check for exploding objects
      if (PlayerMissile1.exploding == 1):
        #print("------> PlayerMissile1.exploding: ",PlayerMissile1.exploding)
        DotInvadersExplodeMissile(PlayerMissile1,Playfield,5)

#      if (PlayerMissile2.exploding == 1 ):
#        #print("------> PlayerMissile2.exploding: ",PlayerMissile2.exploding)
#        DotInvadersExplodeMissile(PlayerMissile2,Playfield,20)


      if (UFOMissile1.exploding == 1 ):
        #print("------> UFOMissile1.exploding: ",UFOMissile1.exploding)
        DotInvadersExplodeMissile(UFOMissile1,Playfield,5)

      if (UFOMissile2.exploding == 1 ):
        #print("------> UFOMissile2.exploding: ",UFOMissile2.exploding)
        DotInvadersExplodeMissile(UFOMissile2,Playfield,5)

        
      #Display animation and clock every X seconds
      #if (CheckElapsedTime(CheckTime) == 1):
      #  ScrollScreenShowLittleShipTime('up',LED.ScrollSleep)         
     
      #=================================
      #= End of level conditions       =
      #=================================
     
      #Count armada UFOs alive
      #See how low down Armada is
      ArmadaCount = 0
      ArmadaLevel = 0
      for x in range (ArmadaWidth):
        for y in range (ArmadaHeight):
          if (Armada[y][x].alive == 1):
            ArmadaCount = ArmadaCount + 1
            if (Armada[y][x].v > ArmadaLevel):
              ArmadaLevel = Armada[y][x].v
      #print ("M - Armada AliveCount ArmadaLevel: ",ArmadaCount,ArmadaLevel)
      ArmadaSpeed = ArmadaCount * 10 + 25
        

      if (ArmadaCount == 0):
        LevelFinished = 'Y'
        #print ("M - Level:", LevelCount)
        LED.setpixel(PlayerMissile1.h,PlayerMissile1.v,0,0,0)
        LED.setpixel(UFOMissile1.h,UFOMissile1.v,0,0,0)
        LED.setpixel(UFOMissile2.h,UFOMissile2.v,0,0,0)

        FireworksExplosion.Animate(EnemyShip.h,EnemyShip.v,'forward',0.03)        
        FireworksExplosion.Animate(PlayerMissile1.h,PlayerMissile1.v,'forward',0.03)        
        FireworksExplosion.Animate(PlayerMissile2.h,PlayerMissile2.v,'forward',0.03)        
        FireworksExplosion.Animate(UFOMissile1.h,UFOMissile1.v,'forward',0.03)        
        FireworksExplosion.Animate(UFOMissile2.h,UFOMissile2.v,'forward',0.03)        
        FireworksExplosion.Animate(EnemyShip.h,EnemyShip.v,'forward',0.03)        
        
        
        ShowFireworks(FireworksExplosion,(random.randint(1,10)),0.03)
        ShowDropShip(PlayerShip.h,PlayerShip.v,'pickup',LED.ScrollSleep * 0.001)

      
      if (ArmadaLevel == LED.HatHeight-1):
        PlayerShip.alive = 0
        LevelFinished = 'Y'

      
        if (PlayerShip.lives <=0):
          Finished = 'Y'


        else:
          PlayerShip.alive = 1
        PlayerShipExplosion.Animate(PlayerShip.h-2,PlayerShip.v-2,'forward',0.025)

      #Display animation and clock every X seconds
      #if (CheckElapsedTime(CheckTime) == 1):
      #  ScrollScreenShowClock('up',LED.ScrollSleep)         



        
      #time.sleep(MainSleep / 5)
  print ("M - The end?")    
  LED.ClearBigLED()
  
  ScoreString = str(PlayerShip.score) 
  LED.ShowScrollingBanner("Score",LED.SDLowGreenR,LED.SDLowGreenG,LED.SDLowGreenB,LED.ScrollSleep)
  LED.ShowScrollingBanner(ScoreString,LED.SDLowYellowR,LED.SDLowYellowG,LED.SDLowYellowB,(LED.ScrollSleep * 2))
  LED.ShowScrollingBanner("GAME OVER",LED.SDMedRedR,LED.SDMedRedG,LED.SDMedRedR,LED.ScrollSleep)




      







      
      
      
      



  
#--------------------------------------
# M A I N   P R O C E S S I N G      --
#--------------------------------------

PlayDotInvaders()
    





















