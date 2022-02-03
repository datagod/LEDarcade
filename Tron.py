#------------------------------------------------------------------------------
#                                                                            --
#  _____ ____   ___  _   _                                                   --
# |_   _|  _ \ / _ \| \ | |                                                  --
#   | | | |_) | | | |  \| |                                                  --
#   | | |  _ <| |_| | |\  |                                                  --
#   |_| |_| \_\\___/|_| \_|                                                  --
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


import LEDarcade   as LED
import copy
import random
import time
import numpy
import math
      

#---------------------------------------
#Variable declaration section
#---------------------------------------

ScrollSleep         = 0.025
TerminalTypeSpeed   = 0.02  #pause in seconds between characters
TerminalScrollSpeed = 0.02  #pause in seconds between new lines
CursorRGB           = (0,255,0)
CursorDarkRGB       = (0,50,0)
MainSleep           = 0.01







#----------------------------
#-- SuperWorms             --
#----------------------------
SuperWormSleep = 0.015
EraseSpeed     = 0.001
SpeedUpSpeed   = 75              #The lower the number, the more often a speedup is applied  (e.g. every 1 out of 200 ticks)
StartSpeedHigh =  1              #the lower the number, the faster it goes (e.g. move every X ticks)
StartSpeedLow  =  7              #the lower the number, the faster it goes (e.g. move every X ticks)
ResurrectionChance  = 100000     #what is chance of new worm being added (1 in X)
ResurrectionTries   = 20         #maximum number of tries when trying to find an empty location for the resurrected superworm
MinSleepTime        = 0.001
ResurrectedMaxTrail = 3          #when resurected, you get this for the trail length
StartMaxTrail       = 50         #Trail length at the start of the round
IncreaseTrailLengthSpeed = 10    #how often to increase length of trail (1 in X chance)
MaxTrailLength           = 2048  #Maximum length of the trail
SuperWormCount           = 8     #maximum number of worms in the worm array
SuperWormStartMinH = 25
SuperWormStartMaxH = 63
SuperWormStartMinV = 0
SuperWormStartMaxV = 25
SuperWormLevels    = 3           #number of levels





#Sprite display locations
ClockH,      ClockV,      ClockRGB      = 0,0,  (0,150,0)
DayOfWeekH,  DayOfWeekV,  DayOfWeekRGB  = 0,6,  (150,0,0)
MonthH,      MonthV,      MonthRGB      = 0,12, (0,20,200)
DayOfMonthH, DayOfMonthV, DayOfMonthRGB = 2,18, (100,100,0)
SpriteFillerRGB = (0,4,0)
CheckClockSpeed = 50


  
#--------------------------------------
#--  TRON / LIGHT CYCLE              --
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
  
  global SpeedUpSpeed

  #Local variables
  moves      = 0
  Finished   = 'N'
  LevelCount = 0
  HighScore  = 0
  SuperWormMapCount = 6

  maxtrail     = StartMaxTrail
  
  
  OriginalSleep = MainSleep * 5
  SleepTime     = SuperWormSleep


  #Clock and date sprites
  ClockSprite   = LED.CreateClockSprite(12)
  #ClockH        = HatWidth  // 2 - (ClockSprite.width // 2)
  #ClockV        = HatHeight // 2 - (ClockSprite.height // 2)

  DayOfWeekSprite     = LED.CreateDayOfWeekSprite()
  MonthSprite         = LED.CreateMonthSprite()
  DayOfMonthSprite    = LED.CreateDayOfMonthSprite()
  

  
  
  
  



  #Make an array of worms
  SuperWorms = []
  for i in range(0,SuperWormCount):
    print ("Making worm:",i)
    r,g,b = LED.BrightColorList[random.randint(1,27)]
    direction  = random.randint(1,4)
    startspeed = random.randint(StartSpeedHigh,StartSpeedLow)
    alive      = 1
    name       = 'Superworm - ' + str(i)
    
    SpotFound = False
    h          = random.randint(30,63)
    v          = random.randint(0,31)

    while (SpotFound == False):
      if (LED.IsSpotEmpty(h,v) == True):
        SuperWorms.append(LED.Dot(h,v,r,g,b,direction,startspeed,alive,name,(0,0),0, StartMaxTrail,EraseSpeed,(r,g,b)))
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
  #  - clear all buffers (LED.Canvas and ScreenArray[V][H])
  #  - draw the text at desired last zoom level
  #  - draw the rest of the text, at this point it is all written to ArrayBuffer
  #  - clear the LED Matrix
  #  - clear all buffers (LED.Canvas and ScreenArray[V][H])
  #Call the ZoomScreen function to redraw the display using ScreenArray[V][H] which at this point
  #contains the values last written to the screen.


  
  while (LevelCount < SuperWormLevels):
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
    LED.CopySpriteToPixelsZoom(ClockSprite,      ClockH,      ClockV,      ClockRGB,       SpriteFillerRGB,1)
    LED.CopySpriteToPixelsZoom(DayOfWeekSprite,  DayOfWeekH,  DayOfWeekV,  DayOfWeekRGB,   SpriteFillerRGB,1)
    LED.CopySpriteToPixelsZoom(MonthSprite,      MonthH,      MonthV,      MonthRGB,       SpriteFillerRGB,1)
    LED.CopySpriteToPixelsZoom(DayOfMonthSprite, DayOfMonthH, DayOfMonthV, DayOfMonthRGB , SpriteFillerRGB,1)

   

    
    #Reset Variables between rounds
    for i in range(0,SuperWormCount):
      print ("Resetting worm:",i)
      SuperWorms[i].score = 0
      SuperWorms[i].SetStartingPoint()
      SuperWorms[i].direction = (random.randint(1,4))
      SuperWorms[i].alive     = 1
      SuperWorms[i].maxtrail  = StartMaxTrail
      SuperWorms[i].trail     = [(SuperWorms[i].h, SuperWorms[i].v)]
      
    
    LevelFinished = 'N'
    SleepTime = SuperWormSleep
    


    while (LevelFinished == 'N'):
      
      
      #Check for keyboard input
      m,r = divmod(moves,LED.KeyboardSpeed)
      if (r == 0):
        Key = LED.PollKeyboard()
        LED.ProcessKeypress(Key)
        if (Key == 'q'):
          LevelCount    = SuperWormLevels + 1
          LevelFinished = 'Y'
          return
        if (Key == 'n'):
          CreateSuperWormMap(random.randint(0,SuperWormMapCount-1))
      #Show clock
      m,r = divmod(moves,CheckClockSpeed)
      if (r == 0):
        
        LED.CopySpriteToPixelsZoom(ClockSprite,      ClockH,      ClockV,      ClockRGB,       SpriteFillerRGB,1)
        LED.CopySpriteToPixelsZoom(DayOfWeekSprite,  DayOfWeekH,  DayOfWeekV,  DayOfWeekRGB,   SpriteFillerRGB,1)
        LED.CopySpriteToPixelsZoom(MonthSprite,      MonthH,      MonthV,      MonthRGB,       SpriteFillerRGB,1)
        LED.CopySpriteToPixelsZoom(DayOfMonthSprite, DayOfMonthH, DayOfMonthV, DayOfMonthRGB,  SpriteFillerRGB,1)





      #Display dots if they are alive
      #Do other stuff too
      WormsAlive = 0
      Score = 0
      ScoreRGB = (0,0,0)

      for i in range(0,SuperWormCount):

        if (SuperWorms[i].alive == 1):
          SuperWorms[i].Display()
          SuperWorms[i].TrimTrail()
          WormsAlive = WormsAlive + 1
          if (Score < SuperWorms[i].score):
            Score = SuperWorms[i].score
            ScoreRGB = SuperWorms[i].r,SuperWorms[i].g,SuperWorms[i].b


          #Increase speed if necessary
          m,r = divmod(moves,IncreaseTrailLengthSpeed)
          if (r == 0):
            SuperWorms[i].IncreaseMaxTrailLength(1)


          #Move worm if it is their time
          m,r = divmod(moves,SuperWorms[i].speed)
          if (r == 0):
            MoveSuperWorm(SuperWorms[i])
            #check for head on collisions
            #if the head of the superworm hits another head, reverse or die
            for sw in range (0,SuperWormCount):
              if (SuperWorms[sw].alive and i != sw and SuperWorms[i].h == SuperWorms[sw].h  and SuperWorms[i].v == SuperWorms[sw].v):
                SuperWorms[i].Kill()
                SuperWorms[sw].Kill()
                print ("Head on collision.  Both worms died")
                WormsAlive = WormsAlive - 2
                break;



        else:
          r = random.randint(0,ResurrectionChance)
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

      for i in range(0,SuperWormCount):
        if (SuperWorms[i].alive == 1):
          LevelFinished = 'N'


      # if(Worm1Dot.alive == 0 and Worm2Dot.alive == 0 and Worm3Dot.alive == 0 and Worm4Dot.alive == 0 and Worm5Dot.alive == 0):
        # LevelFinished = 'Y'
      
      #print ("Alive:",Worm1Dot.alive,Worm2Dot.alive,Worm3Dot.alive)
    

      #Increase speed
      m,r = divmod(moves,SpeedUpSpeed)
      if (r == 0):
        SleepTime = SleepTime * 0.95
        if (SleepTime < MinSleepTime):
          SleepTime = MinSleepTime
      
      if (SleepTime >= MinSleepTime):
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
  for i in range (0,SuperWormCount):
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
  #ThreeGhostSprite.ScrollAcrossScreen(0,26,'right',ScrollSleep)
  #LED.TheMatrix.Clear()
  #LED.Canvas.Clear()
  #LED.ZoomScreen(ScreenArray,32,256,0,Fade=True)



















#--------------------------------------
# M A I N   P R O C E S S I N G      --
#--------------------------------------

def LaunchTron(GameMaxMinutes = 10000,ShowIntro="N"):
  
  global start_time
  start_time = time.time()
  LED.LoadConfigData()


  Message1 = LED.TronGetRandomMessage(MessageType = 'SHORTGAME')
  Message2 = LED.TronGetRandomMessage(MessageType = 'CHALLENGE')


  if(ShowIntro = "Y"):
    LED.ClearBigLED()
    LED.ClearBuffers()
    CursorH = 0
    CursorV = 0
    LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"DIALING FLYNNS ARCADE",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalTypeSpeed)
    LED.BlinkCursor(CursorH= CursorH,CursorV=CursorV,CursorRGB=CursorRGB,CursorDarkRGB=CursorDarkRGB,BlinkSpeed=0.5,BlinkCount=2)
    LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"CONNECTING TO SPACE PARANOIDS",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalTypeSpeed)
    LED.BlinkCursor(CursorH= CursorH,CursorV=CursorV,CursorRGB=CursorRGB,CursorDarkRGB=CursorDarkRGB,BlinkSpeed=0.5,BlinkCount=2)
    LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,Message2,CursorH=CursorH,CursorV=CursorV,MessageRGB=(0,0,255),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)
    LED.BlinkCursor(CursorH= CursorH,CursorV=CursorV,CursorRGB=CursorRGB,CursorDarkRGB=CursorDarkRGB,BlinkSpeed=0.5,BlinkCount=2)



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
    LED.ShowScrollingBanner2(Message,BrightRGB,ScrollSleep,26)

    LED.TheMatrix.Clear()
    LED.Canvas.Clear()
    LED.ZoomScreen(LED.ScreenArray,32,256,0,Fade=True)
    LED.TheMatrix.Clear()


  PlaySuperWorms()





    


  #LED.ShowTitleScreen(
  #      BigText             = 'TRON',
  #      BigTextRGB          = LED.HighRed,
  #      BigTextShadowRGB    = LED.ShadowRed,
  #      LittleText          = 'LIGHT CYCLE',
  #      LittleTextRGB       = LED.MedGreen,
  #      LittleTextShadowRGB = (0,10,0), 
  #      ScrollText          = '',
  #      ScrollTextRGB       = LED.MedYellow,
  #      ScrollSleep         = 0.03, # time in seconds to control the scrolling (0.005 is fast, 0.1 is kinda slow)
  #      DisplayTime         = 1,           # time in seconds to wait before exiting 
  #      ExitEffect          = 0            # 0=Random / 1=shrink / 2=zoom out / 3=bounce / 4=fade /5=fallingsand
  #      )


  

  return    







#execute if this script is called directly
if __name__ == "__main__" :
  while(1==1):
    LaunchTron(100000)        











