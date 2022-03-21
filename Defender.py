
#Standardize alive = True/False not 1/0
#change enemyship garbage collection to the same as human
#have some enemies fligh away from defender fast

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
# |____/|_____|_|   |_____|_| \_|____/|_____|_| \_\                          --                                                                            --
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
from __future__ import print_function


import LEDarcade as LED
import copy
import random
import time
import numpy
import math
from datetime import datetime, timedelta
from rgbmatrix import graphics





random.seed()
start_time = time.time()






#-----------------------------
# Defender Global Variables --
#-----------------------------

#Sprite display locations
ClockH,      ClockV,      ClockRGB      = 0,0,  (0,150,0)
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



LaserR = 150
LaserG = 75
LaserB = 0

DefenderWorldWidth = 2048
MaxMountainHeight  = 16
HumanCount         = 5
EnemyShipCount     = 10
AddEnemyCount      = 5
SpawnNewEnemiesTargetCount = 5
SpawnNewHumansTargetCount  = 5

#Movement
DefenderMoveUpRate   = 3
DefenderMoveDownRate = 3
HumanMoveChance      = 2
EnemyMoveSpeed       = 6
GarbageCleanupChance = 500
GroundRadarChance    = 10
FrontRadarChance     = 5
ShootGroundShipCount = 10
AttackDistance       = 64
HumanRunDistance     = 64
ShootTime            = time.time()
ShootWaitTime        = 0.5
EnemyFearFactor      = 10  #the lower the number, the more likely the enemy will run away
#Gravity
GroundParticleGravity  = 0.05
HumanParticleGravity   = 0.05
EnemyParticleGravity   = 0.0198
BombGravity            = 0.0198



#Bomb
DefenderBombVelocityH  =  0.6
DefenderBombVelocityV  = -0.2
BlastFactor            = 3     
StrafeLaserStrength    = 4
LaserTurnOffChance     = 20
BombDropChance         = 10
RequestBombDrop        = False
RequestGroundLaser     = False
RequestedBombVelocityH = 0.2
RequestedBombVelocityV = 0.05
BombDetonationHeight   = 20
MaxBombBounces         = 2

#Human
HumanCountH = 25
HumanCountV = 0
HumanCountRGB = (100,0,200)

#Enemy
EnemyCountH = 10
EnemyCountV = 0
EnemyCountRGB = (10,0,200)



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
ShowCrypto = 'N'
KeyboardSpeed   = 500
CheckClockSpeed = 500

CheckTime        = 60
random.seed()
start_time = time.time()





#------------------------------
# Sprites, Arrays, Functions --
#------------------------------



  



def ScanInFrontOfDefender(H,V,Defender,DefenderPlayfield):
  
  ScanDirection = 2
  ScanH         = Defender.h + Defender.width  #start in front of ship
  ScanV         = Defender.v
    
  Item          = ''
  ItemList      = ['NULL']
  RadarRange    = 50
  
  # x 1234567890...50
  
  
  try:

    for x in range(0,RadarRange):
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
  RadarStop     = 50
  RadarStepH    = 3
  RadarStepV    = 2
  
  
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
  #HV are the current upper left hand corner of the displayed playfield window
  #Defender.h is relative to the LED display (64x32)

  ScanStartH = H + Defender.width + Defender.h
  ScanStopH  = ScanStartH + 40
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
            if(random.randint(0,DefenderMoveUpRate) == 1):
              Defender.v = Defender.v - 1
            Found = True
            break
          elif(DefenderPlayfield.map[y][x].v > Defender.v):
            if(random.randint(0,DefenderMoveDownRate) == 1):
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







def LookForGroundTargets(Defender,DefenderPlayfield,Ground,Humans,EnemyShips):
  global RequestBombDrop
  global RequestGroundLaser

  #upper left hand corner of currently displayed playfield window
  PlayfieldH   = DefenderPlayfield.DisplayH
  PlayfieldV   = DefenderPlayfield.DisplayV
  RadarWidth   = 10
  RadarHeight  = 6
  RadarAdjustH = 5
  RadarAdjustV = 5
  GroundV      = 0


  #To improve performance, we will not scan every pixel in radar range
  #Radar scanning will be interlaced
  #This procedure is called continuously so lets scan a net instead of a solid area
  #The size of the holes in the net is determined by ScanStep

  #avoid end of the playfield
  if(PlayfieldH + RadarAdjustH + RadarWidth >= DefenderPlayfield.width -1):
    PlayfieldH =  PlayfieldH - RadarAdjustH - RadarWidth


  #Find the ground
  for GroundV in range (Defender.v, LED.HatHeight-2):
    #LED.TheMatrix.SetPixel(Defender.h,Defender.v + V,255,5,10)
    
    if(Ground.map[GroundV][PlayfieldH + RadarAdjustV] != (0,0,0)):
      #print("Ground hit V H:",V,PlayfieldH + Defender.h)
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
  for i in range (0,len(Humans)):
    if(StartX <= Humans[i].h <= StopX  and StartY <= Humans[i].v <=  StopY):
      #print("Found Human[i]hv | StartStopX |:",Humans[i].h,Humans[i].v," | ",StartX, StopX )
      #LED.TheMatrix.SetPixel(Humans[i].h - PlayfieldH,Humans[i].v,255,255,255)
      Found = True
      RequestGroundLaser = True
      RequestBombDrop    = True
      #time.sleep(0.25)
      
  for i in range (0,len(EnemyShips)):
    if(StartX <= EnemyShips[i].h <= StopX  and StartY <= EnemyShips[i].v <=  StopY):
      #print("Found EnemyShip[i]hv | StartStopX |:",EnemyShips[i].h,EnemyShips[i].v," | ",StartX, StopX )
      #LED.TheMatrix.SetPixel(EnemyShips[i].h - PlayfieldH,EnemyShips[i].v,255,255,255)
      Found = True
      RequestGroundLaser = True
      RequestBombDrop    = True
      #time.sleep(0.25)


      
      
  #except:
  #  print("A stupid error has occurred when ground finding targets.  Please fix this soon.")
  #if(Found == False):
  #  RequestGroundLaser = False
  
  return RequestGroundLaser, RequestBombDrop, GroundV, Humans,EnemyShips

  



def ShootTarget(PlayfieldH, PlayfieldV, TargetName, TargetH,TargetV,Defender, DefenderPlayfield,Canvas):
  global ShootTime
  
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
    graphics.DrawLine(Canvas,Defender.h + 5, Defender.v +2 , TargetH - DefenderPlayfield.DisplayH, TargetV, graphics.Color(255,0,0))

  else:
    #Laser misses, draw to end of screen
    graphics.DrawLine(Canvas,Defender.h + 5, Defender.v +2 , LED.HatWidth , TargetV, graphics.Color(255,0,0))

  
  return DefenderPlayfield,TargetHit



def ShootGround(PlayfieldH, PlayfieldV, GroundV, Defender, DefenderPlayfield, Ground, Canvas, Humans, HumanParticles, EnemyShips, GroundParticles):
  #PlayfieldH is the upper left hand corner of the playfield window being displayed
  #Defender.h and Defender.v are relative to 64x32 display NOT the playfield 
  #print("Defender.h",Defender.h)

  ScanH = PlayfieldH + Defender.h + 3 
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
  
  LaserR = random.randint(50,255)
  LaserG = random.randint(0,100)
  LaserB = random.randint(50,255)
  if(ScanH  >= DefenderPlayfield.width - 1):
    ScanH = DefenderPlayfield.width - 1
  

  graphics.DrawLine(Canvas,ScreenH, ScreenV, ScreenH, GroundV +2, graphics.Color(LaserR,LaserG,LaserB))
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


def CreateEnemyWave(ShipCount,Ground,DefenderPlayfield):
  global EnemyShipCount

  EnemyShipCount = ShipCount
  EnemyShips = []
  ShipType = random.randint(0,27)
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



def AddEnemyShips(EnemyShips,ShipCount,Ground,DefenderPlayfield):
  global EnemyShipCount

    
  ShipType = random.randint(0,27)
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
    EnemyShipCount = sum(1 for e in EnemyShips if e.alive == 1)
    
  return EnemyShips, EnemyShipCount, DefenderPlayfield







def AddHumans(Humans,NewHumanCount,Ground,DefenderPlayfield):
  global HumanCount

  #humans must be located at least HatWidth from the start
  for count in range (0,NewHumanCount):
    
    #LED.HumanSprite.framerate = random.randint(15,50)
    
    TheSprite   = LED.HumanSprite
    TheSprite.h = random.randint(63,DefenderWorldWidth)
    TheSprite.v = random.randint(16,LED.HatHeight-1)
    TheSprite.alive == True
    
    if(random.randint(0,1) == 1):
      TheSprite.direction = 1
    else:
      TheSprite.direction = -1
    
    Humans.append(copy.deepcopy(TheSprite))
    DefenderPlayfield.CopyAnimatedSpriteToPlayfield(Humans[count].h,Humans[count].v,Humans[count])
  
    #HumanCount = len(Humans)
    HumanCount = sum(1 for h in Humans if h.alive == 1)

  return Humans,HumanCount, DefenderPlayfield


def DropPilot(H,V,Humans,DefenderPlayfield):
  global HumanCount

  #humans must be located at least HatWidth from the start
  TheSprite   = LED.HumanSprite
  TheSprite.h = H
  TheSprite.v = V
  TheSprite.alive = True
    
  if(random.randint(0,1) == 1):
    TheSprite.direction = 1
  else:
    TheSprite.direction = -1

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


def DetonateBombIfAtGround(PlayfieldH,PLayfieldV,DefenderBomb,Ground,GroundParticles,Humans,HumanParticles,EnemyShips, DefenderPlayfield,Canvas,GroundRGB, SurfaceRGB):
  # PlayfieldH, PlayfieldV = upper left hand corner of the window being displayed
  #Defenderbomb.h is relative to the  64x32 display
  #BlastHV is relative to the  64x32 display

  Floor = LED.HatHeight
  Finished = False
  
  BlastH = round(DefenderBomb.h)
  BlastV = round(DefenderBomb.v)
  
  #the further the bomb travels, the more power it gains
  BlastStrength  = round(DefenderBomb.h / 10 + BlastFactor)
  

  SurfaceR, SurfaceG, SurfaceB = SurfaceRGB
  GroundR, GroundG, GroundB    = GroundRGB

  
  #print("BlastHV BombvelocityHV:",BlastH,BlastV,DefenderBomb.velocityH, DefenderBomb.velocityV)

  try:

    #Blow up bomb if it touches ground or runs out of velocity
    #try:
    #blow up pieces of ground
    
    #print("Bounces:",DefenderBomb.bounces)
    if((Ground.map[BlastV][BlastH+PlayfieldH] != (0,0,0))
       or DefenderBomb.bounces >= MaxBombBounces
       ):
      
      #destroy ground
      gv = BlastV
      gh = BlastH+PlayfieldH
      for j in range (-4,BlastStrength):
        for i in range (-BlastStrength + j ,BlastStrength - j   ):

          #near to the blast gets erased
          if(gv + j < LED.HatHeight and gh + i < Ground.width):
            Ground.map[gv +j][gh +i] = (0,0,0)
          else:
            gv = gv -1
            Finished = True
            break
        if(Finished == True):
          break
        #set ground outside the blast zone to different color
        else:
          if (j >= 0):         
            if(gv + j < LED.HatHeight and (gh + BlastStrength + j) < Ground.width):
              if(Ground.map[gv +j][gh - BlastStrength +j - 1] != (0,0,0)):
                Ground.map[gv +j][gh - BlastStrength +j - 1] = (SurfaceR,SurfaceG,SurfaceB)
              
              if(Ground.map[gv +j][gh + BlastStrength -j ] != (0,0,0)):
                Ground.map[gv +j][gh + BlastStrength -j ] = (SurfaceR,SurfaceG,SurfaceB)
          

      #beside blast gets colored green
          
      #Ground.map[gv +j][gh +i -j + 1] = (0,35,0)
      #Ground.map[gv +j][gh +i -j - 1] = (0,35,0)


      #Big white flash
      for i in range (1,BlastStrength):
        graphics.DrawCircle(Canvas,BlastH,BlastV,i,graphics.Color(255,255,255))

      #Explode Ground
      for i in range(0,round(BlastStrength / 2)):
        GroundParticles = AddGroundParticles(BlastH,BlastV,ExplosionR, ExplosionG, ExplosionB,GroundParticles)

      Humans, HumanParticles, EnemyShips = KillEnemiesInBlastZone(BlastH + PlayfieldH,BlastV,BlastStrength, Humans, HumanParticles,EnemyShips, DefenderPlayfield)

     
      DefenderBomb.alive = False
      #DefenderBomb.bounces = 0
      #print ("Bomb Dead.",DefenderBomb.alive)


  except:
    print("Bomb error BlastH BlastV PlayfieldH:",BlastH, BlastV ,PlayfieldH)      


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
        GroundParticles[i].alive == False




def MoveHumanParticles (HumanParticles,Canvas):
  
  ParticleCount = len(HumanParticles)
  if(ParticleCount > 0):
    for i in range (0,ParticleCount):
      
      #print("HumanParticle:",i," alive:",HumanParticles[i].alive)

      if(HumanParticles[i].alive == True):
        HumanParticles[i].UpdateLocationWithGravity(HumanParticleGravity)
        hph = HumanParticles[i].h
        hpv = HumanParticles[i].v
        
            
        #only display particles on screen
        r  = HumanParticles[i].r
        g  = HumanParticles[i].g
        b  = HumanParticles[i].b
        Canvas.SetPixel(hph,hpv,r,g,b)
          

def DisplayCount(h,v,RGB, Count,Canvas):
  CountSprite = LED.CreateBannerSprite(str(Count))
  Canvas = LED.CopySpriteToCanvasZoom(CountSprite,h,v,(RGB),(0,0,0),ZoomFactor = 1,Fill=False,Canvas=Canvas)
  #Canvas = LED.TheMatrix.SwapOnVSync(Canvas)
  return Canvas, CountSprite



def FlattenGround(h1,h2,v,Ground):
  #h1,h2 are the start/stop columns to examine
  #v is the max height of the ground to check (saves time by not looking at sky)
  
  #examine holes in ground and make top layers fall to bottom
   
  #look for top ground particle
  #then look for bottom empty
  #swap

  

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


def PlayDefender(GameMaxMinutes):      
 
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

  finished            = 'N'
  LevelCount          = 0
  EnemyAliveCount     = 0
  OldEnemyAliveCount  = 0
  OldHumanCount       = 0
  

  ClockSprite         = LED.CreateClockSprite(24)
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


  LED.TheMatrix.Clear()
  LED.Canvas.Clear()
  
  Canvas = LED.TheMatrix.CreateFrameCanvas()
  Canvas.Fill(0,0,0)
  Canvas = LED.TheMatrix.SwapOnVSync(Canvas)



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

  Background   = LED.Layer(name="backround", width=2048, height=32,h=0,v=0)
  Middleground = LED.Layer(name="backround", width=2048, height=32,h=0,v=0)
  Foreground   = LED.Layer(name="backround", width=2048, height=32,h=0,v=0)
  Ground       = LED.Layer(name="ground",    width=DefenderWorldWidth, height=32,h=0,v=0)

  Background.CreateStars(5,0,50,50)
  Middleground.CreateStars(0,0,100,100)
  Foreground.CreateStars(0,0,200,200)
 
  
  i = random.randint(0,GroundColorCount -1)
  GroundRGB, SurfaceRGB      = GroundColorList[i]
  GroundR,GroundG,GroundB    = GroundRGB
  SurfaceR,SurfaceG,SurfaceB = SurfaceRGB
  ExplosionR, ExplosionG, ExplosionB = LED.AdjustBrightnessRGB(SurfaceRGB,ExplosionBrightnessModifier)

  Ground.CreateMountains(GroundRGB,SurfaceRGB,maxheight=MaxMountainHeight)
  

  
  
  



  #--------------------------------
  # Fancy Intro                  --
  #--------------------------------
  
  OldScreenArray  = ([[]])
  OldScreenArray  = [[ (0,0,0) for i in range(LED.HatWidth)] for i in range(LED.HatHeight)]

  NewScreenArray = LED.PaintFourLayerScreenArray(0,0,0,0,Background,Middleground,Foreground,Ground,Canvas)
  LED.TransitionBetweenScreenArrays(OldScreenArray,NewScreenArray,TransitionType=2)



#--------------------------------
  #-- Create Enemies             --
  #--------------------------------

     

  

  Humans,     DefenderPlayfield = CreateHumans(HumanCount=HumanCount, Ground=Ground,DefenderPlayfield=DefenderPlayfield)
  HumanCountSprite = LED.CreateBannerSprite(str(HumanCount))
  Canvas, HumanCountSprite = DisplayCount(HumanCountH, HumanCountV, HumanCountRGB,HumanCount,Canvas)
    

  EnemyShips, DefenderPlayfield = CreateEnemyWave(ShipCount=EnemyShipCount, Ground=Ground,DefenderPlayfield=DefenderPlayfield)
  EnemyShipCountSprite = LED.CreateBannerSprite(str(EnemyShipCount))
  Canvas, EnemyCountSprite = DisplayCount(EnemyCountH, EnemyCountV, EnemyCountRGB,EnemyShipCount,Canvas)
  


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
  
  

  while (finished == "N"):
    
    count  = 0
    bx     = 0
    mx     = 0
    fx     = 0
    gx     = -1
    bwidth = Background.width    - LED.HatWidth
    mwidth = Middleground.width  - LED.HatWidth
    fwidth = Foreground.width    - LED.HatWidth
    gwidth = Ground.width        - LED.HatWidth
    brate  = 6
    mrate  = 4
    frate  = 2
    grate  = 1
    DisplayH = 0
    DisplayV = 0
    TargetHit = False
    

    Defender = copy.deepcopy(LED.Defender)
    Defender.h = 5
    Defender.v = 20
     


    while(1==1):
      #main counter
      count = count + 1

      
      #check the time once in a while
      if(random.randint(0,1000) == 1):
        if (ClockSprite.hhmm != datetime.now().strftime('%H:%M')):
          ClockSprite = LED.CreateClockSprite(24)
          Background = LED.CopySpriteToLayerZoom(ClockSprite,bx + 30,10,(5,0,5),(0,5,0),2,False,Layer=Background)



        #End game after X seconds
        h,m,s    = LED.GetElapsedTime(start_time,time.time())
        if(m > GameMaxMinutes):
          print("Elapsed Time:  mm:ss",m,s)
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
      m,r = divmod(count,brate)
      if(r == 0):
        bx = bx + 1
        if(bx > bwidth):
          bx = 0
      #Canvas = Background.PaintOnCanvas(bx,0,Canvas)


      #Middleground
      m,r = divmod(count,mrate)
      if(r == 0):
        mx = mx + 1
        if(mx > mwidth):
          mx = 0
      #Canvas = Middleground.PaintOnCanvas(mx,0,Canvas)

        
      #foreground
      m,r = divmod(count,frate)
      if(r == 0):
        fx = fx + 1
        if(fx > fwidth):
          fx = 0
      #Canvas = Foreground.PaintOnCanvas(fx,0,Canvas)


      #ground / display
      m,r = divmod(count,grate)
      if(r == 0):
        gx = gx + 1
        if(gx >= gwidth + LED.HatWidth ):
          gx = 0
        DisplayH = gx
      #Canvas = Ground.PaintOnCanvas(gx,0,Canvas)


      Canvas = LED.PaintFourLayerCanvas(bx,mx,fx,gx,Background,Middleground,Foreground,Ground,Canvas)
      #Canvas = LED.RunningMan3Sprite.PaintAnimatedToCanvas(-6,14,Canvas)

      #Update DefenderPlayfield
      DefenderPlayfield.DisplayH = gx
      DefenderPlayfield.DisplayV = 0


      DisplayMaxH = DisplayH + LED.HatWidth

      #-------------------------------
      #-- Move Humans               --
      #-------------------------------

      OldH = 0
      OldV = 0
      #MoveHumans
      for i in range (0,HumanCount):
        if(Humans[i].alive == True):
          OldH = Humans[i].h
          OldV = Humans[i].v

          if(random.randint(0,HumanMoveChance) == 1):
            if (abs(gx + Defender.h - Humans[i].h) < HumanRunDistance):
              #move human, but follow ground
              Humans[i].h = Humans[i].h + Humans[i].direction

              #check boundaries
              if(Humans[i].direction == 1):
                if Humans[i].h >= DefenderPlayfield.width -2:
                  Humans[i].h = 0
              else:
                if Humans[i].h <= 0:
                  Humans[i].h = DefenderPlayfield.width -1


              if(Humans[i].v >= LED.HatHeight -2):
                Humans[i].v = LED.HatHeight -3

              #print(Humans[i].v,Humans[i].h)

              #check ground
              #If hole, move down

              try:
                rgb = Ground.map[Humans[i].v][Humans[i].h + Humans[i].direction]
              except:
                print("Error moving human: i vh direction",i,Humans[i].v,Humans[i].h, Humans[i].direction,end="\r")



              if(rgb == (0,0,0)):
                #if a hole at the bottom is encountered, run away
                if(Humans[i].v > LED.HatHeight -4):
                  Humans[i].direction = Humans[i].direction * -1
                #print("Moving down:",Humans[i].v)
                else:
                  Humans[i].v = Humans[i].v + 1
              else:
                if(random.randint(0,HumanMoveChance) == 1):
                  Humans[i].v = Humans[i].v -1
              
          
          hH = Humans[i].h
          hV = Humans[i].v
        
          #check if human is in currently displayed area
          if(DisplayH <=  hH  <= DisplayMaxH):
            Canvas = Humans[i].PaintAnimatedToCanvas(hH-DisplayH,hV,Canvas)

          #Place Human on playfield
          
          #for some reason when we erase the sprite, it doesn't draw anymore on the canvas
          #DefenderPlayfield = Humans[i].EraseSpriteFromPlayfield2(DefenderPlayfield)
          #DefenderPlayfield.CopyAnimatedSpriteToPlayfield(Humans[i].h,Humans[i].v,Humans[i])


      #-------------------------------
      #-- Move EnemyShips           --
      #-------------------------------

      OldH = 0
      OldV = 0
      NewH = 0
      NewV = 0
      #MoveEnemyShips
      
      for i in range (0,EnemyShipCount):

        if(EnemyShips[i].alive == True):
          OldH = EnemyShips[i].h
          OldV = EnemyShips[i].v
        
          if(OldV < 0):
            print("Invalid V - EnemyShip HV",OldH, OldV)
            OldV = 0

          if(OldH < 0):
            print("Invalid H - EnemyShip HV",OldH, OldV)
            OldH = 0


          #Move if it is time to move
          m,r = divmod(count,EnemyMoveSpeed)
          if(r == 0):
       

            #Move if within X pixels from Defender
            if (abs(gx + Defender.h - EnemyShips[i].h) < AttackDistance):


              #check fear factor and change enemy fear status
              if(random.randint(0,EnemyFearFactor) == 1):
                if(EnemyShips[i].afraid == True):
                  EnemyShips[i].afraid = False
                else:
                  EnemyShips[i].afraid = True
              
              
              #Move towards defender if not afraid
              if(EnemyShips[i].afraid == True):
                EnemyShips[i].direction = LED.PointAwayFromObject8Way(OldH,OldV,Defender.h,Defender.v)
              else:
                EnemyShips[i].direction = LED.PointTowardsObject8Way(OldH,OldV,Defender.h,Defender.v)

              #move Enemy
              NewH, NewV = LED.CalculateDotMovement8Way(OldH, OldV, EnemyShips[i].direction)
              #print("NewH NewV direction:",NewH,NewV,EnemyShips[i].direction)


              #check boundaries
              if(NewH >= DefenderPlayfield.width - EnemyShips[i].width):
                NewH = 0
              elif(NewH <= 0):
                NewH = DefenderPlayfield.width - EnemyShips[i].width
              #Might need to adjust this for enemy ships
              if(NewV >= LED.HatHeight -2):
                NewV = LED.HatHeight -3
              elif(NewV <=3):
                NewV = 3
              
            
              EnemyShips[i].h = NewH
              EnemyShips[i].v = NewV
          

              #Place EnemyShip on playfield
              
              #for some reason when we erase the sprite, it doesn't draw anymore on the canvas
              #This is likely because the sprite on the playfield points at the actual ship object
              #and ends up getting erased.  To avoid this we can always draw sprites with a border
              #of nothing, which will get written as emptyObject dots
              
              DefenderPlayfield.EraseAnimatedSpriteFromPlayfield(OldH,OldV,EnemyShips[i])
            
              try:
                DefenderPlayfield.CopyAnimatedSpriteToPlayfield(NewH, NewV,EnemyShips[i])
              except:
                print("Something went wrong copying the enemy ship sprite to the playfield")
                print("hv:",EnemyShips[i].h, EnemyShips[i].v)

            
        
          #check if Enemy is in currently displayed area
          if(DisplayH - EnemyShips[i].width <=  EnemyShips[i].h  <= (DisplayH + LED.HatWidth + EnemyShips[i].width)):
            Canvas = EnemyShips[i].PaintAnimatedToCanvas(EnemyShips[i].h-DisplayH,EnemyShips[i].v,Canvas)
            
          

        #If ship is dead, move particles
        if(EnemyShips[i].alive == False):
          for j in range (0, (len(EnemyShips[i].Particles))):

            if (EnemyShips[i].Particles[j].alive == 1):
              EnemyShips[i].Particles[j].UpdateLocationWithGravity(EnemyParticleGravity)
              ph = EnemyShips[i].Particles[j].h
              pv = EnemyShips[i].Particles[j].v

              #only display particles on screen
              if(DisplayH <=  ph  <= DisplayMaxH):
                r  = EnemyShips[i].Particles[j].r
                g  = EnemyShips[i].Particles[j].g
                b  = EnemyShips[i].Particles[j].b
                #print("Ship Particle:",i,j)  
                Canvas.SetPixel(ph - DisplayH,pv,r,g,b)
              
              #kill the particle if the go off the screen
              else:
                EnemyShips[i].Particles[j].alive == 0


      
      #--------------------------------
      #-- Move Defender              --
      #--------------------------------

      #defender needs to avoid the ground
      #shoot enemies
      #pick up humans
      
      DefenderPlayfield.DisplayH = gx
      DefenderPlayfield.DisplayV = 0


      if(random.randint(0,25) == 1):
        Defender.v = Defender.v -1
      elif(random.randint(0,25) == 1):
        Defender.v = Defender.v +1


      ScanV = Defender.v + 10
      if(ScanV > LED.HatHeight -2):
        ScanV = LED.HatHeight -2

      ScanH = gx + 5
      if(ScanH >= DefenderPlayfield.width -1):
        ScanH = 0

      if(Ground.map[ScanV][ScanH] != (0,0,0)): 
        if(random.randint(0,3) == 1):
          Defender.v = Defender.v - 1
      else:
        if(random.randint(0,200) == 1):
          Defender.v = Defender.v + 1

      #keep defender within the screen borders
      if(Defender.v >= LED.HatHeight-3):
        Defender.v = LED.HatHeight-3
      if(Defender.v <= 5):
        Defender.v = 5



      #-------------------------------------
      #-- Find targets and start blasting --
      #-------------------------------------

      TargetFound = False
      #Shoot forward laser
      if(random.randint(0,FrontRadarChance) == 1):
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

            RequestBombDrop = True

      #Shoot ground laser when X ships left

      #Look for targets on the ground
      if(EnemyShipCount <= ShootGroundShipCount ):
        if(random.randint(0,GroundRadarChance) == 1):
          RequestGroundLaser, RequestBombDrop, GroundV,Humans,EnemyShips = LookForGroundTargets(Defender,DefenderPlayfield,Ground,Humans,EnemyShips)

      #Strafe Ground with lasers when requested
      if(RequestGroundLaser == True):
        #print("Shooting ground!")
        DefenderPlayfield, Ground, GroundParticles, Humans, HumanParticles, EnemyShips = ShootGround(gx,0,GroundV, Defender, DefenderPlayfield,Ground,Canvas,Humans, HumanParticles, EnemyShips,GroundParticles)  

        
        Ground = FlattenGround(gx + Defender.h +1,gx + Defender.h +3,MaxMountainHeight,Ground)
        
        if(random.randint(0,LaserTurnOffChance) == 1):
          RequestGroundLaser = False      
      
      Canvas = LED.Defender.PaintAnimatedToCanvas(5,Defender.v,Canvas)


      #--------------------------------
      #-- Move Defender Bomb         --
      #--------------------------------

      #start dropping bombs when 15 enemies left
      #print("EnemyShipCount:",EnemyShipCount)
      if (RequestBombDrop == True  or (ShootGroundShipCount <= EnemyShipCount <= (ShootGroundShipCount * 2))):
      
        if(DefenderBomb.alive == False):
          #Lob the bombs for increased range and blast
          #print("Lobbing Bombs")
          if(random.randint(0,BombDropChance) == 1):
            DefenderBomb.alive = True
            RequestBombDrop = False
            DefenderBomb.h = Defender.h + 3
            DefenderBomb.v = Defender.v + 1
            DefenderBomb.velocityH = DefenderBombVelocityH
            DefenderBomb.velocityV = DefenderBombVelocityV
            DefenderBomb.bounces = 0
          
        

      #when 5 are left, drop bombs faster
      elif((5 <= EnemyShipCount <= 10) and DefenderBomb.alive == False):
        if(random.randint(0,25) == 1):
          #print ("Making Bomb alive",DefenderBomb.alive,DefenderBomb.h,DefenderBomb.v)
          DefenderBomb.alive = True
          RequestBombDrop = False
          #bombs requested are more direct, to hit aliens hiding in the rocks
          DefenderBomb.h = Defender.h + 2
          DefenderBomb.v = Defender.v + 1
          DefenderBomb.velocityH = DefenderBombVelocityH / 2
          DefenderBomb.velocityV = DefenderBombVelocityV * -3
          DefenderBomb.bounces = 0


      #Move bomb if it is alive
      if (DefenderBomb.alive == True):
        bh, bv, DefenderBomb, DefenderPlayfield, Canvas = MoveBomb(gx,DefenderBomb,DefenderPlayfield,Canvas)
       
        if(DefenderBomb.v >= BombDetonationHeight):
          #Detonate Bomb if at ground
          (DefenderBomb, 
          GroundParticles, 
          Humans,
          HumanParticles,
          EnemyShips,
          Ground, 
          DefenderPlayfield,
          Canvas
          )  = DetonateBombIfAtGround(DisplayH,
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
                            SurfaceRGB
                            )
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

      #Add clock
      Canvas = LED.CopySpriteToCanvasZoom(ClockSprite,(LED.HatWidth - ClockSprite.width -2),0,(0,100,0),(0,5,0),1,False,Canvas)


      #Add display
      EnemyAliveCount = sum(1 for e in EnemyShips if e.alive == 1)
      
      #Only change display sprite if the count changes
      if(OldEnemyAliveCount != EnemyAliveCount):
        Canvas,EnemyCountSprite = DisplayCount(EnemyCountH, EnemyCountV, EnemyCountRGB,EnemyAliveCount,Canvas)
        OldEnemyAliveCount = EnemyAliveCount
      else:
        Canvas = LED.CopySpriteToCanvasZoom(EnemyCountSprite,EnemyCountH,EnemyCountV,(EnemyCountRGB),(0,0,0),ZoomFactor = 1,Fill=False,Canvas=Canvas)



      #Human counts
      HumanCount = sum(1 for h in Humans if h.alive == 1)
      #Only change display if the count changes
      if(OldHumanCount != HumanCount):
        Canvas, HumanCountSprite = DisplayCount(HumanCountH, HumanCountV, HumanCountRGB,HumanCount,Canvas)
        OldHumanCount = HumanCount
        
        #this is just a test
        Background = LED.CopySpriteToLayerZoom(HumanCountSprite,bx + 30,HumanCountV + 10,(5,0,5),(1,1,1),ZoomFactor = 2,Fill=False,Layer=Background)

      else:
        Canvas = LED.CopySpriteToCanvasZoom(HumanCountSprite,HumanCountH,HumanCountV,(HumanCountRGB),(0,0,0),ZoomFactor = 1,Fill=False,Canvas=Canvas)


        
    





      #--------------------------------
      #-- Add more enemies           --
      #--------------------------------

      if(EnemyShipCount <= SpawnNewEnemiesTargetCount):
        EnemyShips, EnemyShipCount, DefenderPlayfield = AddEnemyShips(EnemyShips, ShipCount=AddEnemyCount, Ground=Ground,DefenderPlayfield=DefenderPlayfield)


      if(HumanCount <= SpawnNewHumansTargetCount):
        Humans, HumanCount, DefenderPlayfield = AddHumans(Humans, NewHumanCount=20, Ground=Ground,DefenderPlayfield=DefenderPlayfield)


      #--------------------------------
      #-- Display canvas             --
      #--------------------------------

      Canvas = LED.TheMatrix.SwapOnVSync(Canvas)
     

    
      #--------------------------------
      #-- Garbage Cleanup            --
      #--------------------------------


      
      #to reduce the amount of objects being tracked we remove old
      #ships, if they are far enough off the screen to not have any
      #particles still bouncing

      DeleteH = DisplayH - LED.HatWidth


      #ships and their particles
      DeletedShips = 0
      j = 0
      if(random.randint(0,GarbageCleanupChance) == 1):
        #Update EnemyShipCount to get ALL the ships, alive or dead
        EnemyShipCount = len(EnemyShips)
        for i in range (0,EnemyShipCount):
          
          #print("i j EnemyShipCount LenEnemyShip:",i,j,EnemyShipCount,len(EnemyShips))
          H = EnemyShips[j].h 
          V = EnemyShips[j].v 
          
          
          #if enemy is dead and is off screen, nuke them
          if(EnemyShips[j].alive == False):
            #check if EnemyShip is in currently NOT in displayed area
            
            if(H < DeleteH or H > DisplayH + LED.HatWidth):
              del EnemyShips[j]
              DeletedShips = DeletedShips + 1
              #print("Deleting ship j DeletedShips EnemyShipCount:",j,DeletedShips,EnemyShipCount)
                
              j = j - 1
          
          j = j + 1
              
              #break
        #I did it this way to avoid changing the variable used in a for loop
        EnemyShipCount = EnemyShipCount - DeletedShips
        
        print("Garbage cleanup EnemyShips:",EnemyShipCount)              
      
      #delete ground particles
      j = 0
      if(random.randint(0,50) == 1):
        GroundParticleCount = len(GroundParticles)
        if(GroundParticleCount >= 1):

          for i in range (0,GroundParticleCount):
            H = GroundParticles[j].h 
            V = GroundParticles[j].v 
            
            DeleteH = DisplayH -1
            
            #if enemy is dead and is off screen, nuke them
            if(H < DeleteH):
              del GroundParticles[j]
              j = j - 1
            
            j = j + 1
                

      #delete old bomb
          
          

      #humans and their particles
      #DeletedHumans = 0
      #j = 0
      #if(random.randint(0,GarbageCleanupChance) == 1):
      #  for i in range (0,HumanCount):
          
      #    H = Humans[j].h 
      #    V = Humans[j].v 
          
      #    DeleteH = DisplayH - LED.HatWidth
          
      #    #if enemy is dead and is off screen, nuke them
      #    if(Humans[j].alive == False):
      #      #check if EnemyShip is in currently NOT in displayed area
            
      #      if(H < DeleteH or H > DeleteH + LED.HatWidth):
      #        del Humans[j]
      #        DeletedHumans = DeletedHumans + 1
      #        j = j - 1
          
      #    j = j + 1



      DeletedHumans = 0
      j = 0
      if(random.randint(0,GarbageCleanupChance) == 1):
        Humans = [i for i in Humans if (i.alive == True)]

        HumanCount = len(Humans)
        print("Garbage cleanup Human count:",HumanCount)

        #delete human particles
        if(random.randint(0,50) == 1):
          HumanParticleCount = len(HumanParticles)
          if(HumanParticleCount >= 1):

            for i in range (0,HumanParticleCount):
              H = HumanParticles[j].h 
              V = HumanParticles[j].v 
              
              DeleteH = DisplayH -1
              
              #if enemy is dead and is off screen, nuke them
              if(H < DeleteH or (H > DeleteH + LED.HatWidth)):
                del HumanParticles[j]





        #print("Garbage cleanup EnemyShipCount:",EnemyShipCount," HumanCount:",HumanCount)
      






      #if(random.randint(0,50) == 1):
      #  DebugPlayfield(DefenderPlayfield.map,gx,0,64,32)




  #let the display show the final results before clearing
  time.sleep(1)
  LED.ClearBigLED()

  return






























def LaunchDefender(GameMaxMinutes = 10000,ShowIntro=True):
  
  #--------------------------------------
  # M A I N   P R O C E S S I N G      --
  #--------------------------------------

  if(ShowIntro == True):


    LED.ShowTitleScreen(
        BigText             = 'SPACE',
        BigTextRGB          = LED.HighRed,
        BigTextShadowRGB    = LED.ShadowRed,
        LittleText          = 'OFFENDER',
        LittleTextRGB       = LED.MedGreen,
        LittleTextShadowRGB = (0,10,0), 
        ScrollText          = 'TIME FOR PAYBACK',
        ScrollTextRGB       = LED.MedYellow,
        ScrollSleep         = 0.03, # time in seconds to control the scrolling (0.005 is fast, 0.1 is kinda slow)
        DisplayTime         = 1,           # time in seconds to wait before exiting 
        ExitEffect          = 0            # 0=Random / 1=shrink / 2=zoom out / 3=bounce / 4=fade /5=fallingsand
        )


  
    LED.ClearBigLED()
    LED.ClearBuffers()
    CursorH = 0
    CursorV = 0
    LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"CONNECTING TO DEEP SPACE ARRAY",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalTypeSpeed)
    LED.BlinkCursor(CursorH= CursorH,CursorV=CursorV,CursorRGB=CursorRGB,CursorDarkRGB=CursorDarkRGB,BlinkSpeed=0.5,BlinkCount=2)
    LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"TRANSMITTING COORDINATES",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalTypeSpeed)
    LED.BlinkCursor(CursorH= CursorH,CursorV=CursorV,CursorRGB=CursorRGB,CursorDarkRGB=CursorDarkRGB,BlinkSpeed=0.5,BlinkCount=2)
    LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"DESTROY ALL INVADERS!",CursorH=CursorH,CursorV=CursorV,MessageRGB=(225,0,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)
    LED.BlinkCursor(CursorH= CursorH,CursorV=CursorV,CursorRGB=CursorRGB,CursorDarkRGB=CursorDarkRGB,BlinkSpeed=0.5,BlinkCount=2)


  PlayDefender(GameMaxMinutes)
      

  LED.ClearBigLED()
  LED.ClearBuffers()
  CursorH = 0
  CursorV = 0
  LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"MISSION COMPLETE",CursorH=CursorH,CursorV=CursorV,MessageRGB=(0,175,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalTypeSpeed)
  LED.BlinkCursor(CursorH= CursorH,CursorV=CursorV,CursorRGB=CursorRGB,CursorDarkRGB=CursorDarkRGB,BlinkSpeed=0.5,BlinkCount=2)






#execute if this script is called directly
if __name__ == "__main__" :
  while(1==1):
    #LED.LoadConfigData()
    #LED.SaveConfigData()
    print("After SAVE DefenderGamesPlayed:",LED.DefenderGamesPlayed)
    LaunchDefender(100000,False)        


















