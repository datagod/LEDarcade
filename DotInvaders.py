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
  



  





#------------------------------------------------------------------------------
#- DOT INVADERS 
#-
#------------------------------------------------------------------------------

#right side area of LED display will be used for non game items
RightSideSize = 20





#Enemy ship is the UFO
def MoveUFO(UFOShip):
  #print ("MBS - Name Direction HV:",UFOShip.name,UFOShip.direction,UFOShip.h,UFOShip.v)
  
  #Player ships always points up, enemy ships point down
  h = UFOShip.h
  v = UFOShip.v
  
  #print("checking border")
  if ((UFOShip.direction == 2 and UFOShip.h >= LED.HatWidth-RightSideSize-2) or
      (UFOShip.direction == 4 and UFOShip.h < 2)):
    UFOShip.direction = LED.ReverseDirection(UFOShip.direction)


  NewH, NewV = LED.CalculateDotMovement(UFOShip.h,UFOShip.v,UFOShip.direction)
  UFOShip.Erase()
  Playfield[v][h] = Empty
  
  UFOShip.h, UFOShip.v = NewH, NewV
  Playfield[NewV][NewH] = UFOShip
  

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
    if (Item == 'UFOShip'):
      Ship.score = Ship.score + random.randint(1,11)
    elif (Item == 'Bunker'):
      Ship.score = Ship.score - 1
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

  #if("UFO" in ItemList):
  #  print("UFO Seen!")
  #  print(ItemList[37],ItemList[38],ItemList[39])

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
    h = random.randint(2,LED.HatWidth)
    v = random.randint(2,LED.HatHeight / 2)
    FireWorksExplosion.Animate(h,v,'forward',speed,StartFrame = 1) 
    FireWorksExplosion.EraseLocation(h,v)       






        
          
def PlayDotInvaders():
  
  #Local variables
  moves       = 0
  Finished    = 'N'
  LevelCount  = 1
  Playerh     = 0
  Playerv     = 0
  SleepTime   = LED.MainSleep / 4
  ChanceOfUFOShip = 20000


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
  

    
    
  
  


  PlayerShip = LED.Ship( 7,15,PlayerShipR,PlayerShipG,PlayerShipB,4,1,10,1,5,'Player1', 0,0)
  UFOShip    = LED.Ship(0,0,LED.SDHighPurpleR,LED.SDHighPurpleG,LED.SDHighPurpleB,4,3,50,0,3,'UFO', 0,0)
  Empty      = LED.Ship(-1,-1,0,0,0,0,1,0,0,0,'EmptyObject',0,0)

  ScoreSprite = LED.CreateBannerSprite('0')
  DisplayScoreSpeed = 500
  SpaceInvaderDisplaySpeed = 750

 
  #CreateExplosionSprites
  FireworksExplosion  = copy.deepcopy(LED.PlayerShipExplosion)  
  BomberShipExplosion = copy.deepcopy(LED.PlayerShipExplosion)  
  
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
    UFOShip.alive   = 0
    UFOMissile1.alive = 0
    UFOMissile2.alive = 0
    UFOShip.speed   = random.randint (100,500)
    
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
      LED.FlashDot(BunkerDots[i].h,BunkerDots[i].v,0.005)
      BunkerDots[i].Display()


    #Pre calculate these because they do not change
    InvaderH = LED.HatWidth - LED.SmallInvader.width
    InvaderV = LED.HatHeight - LED.SmallInvader.height - ScoreSprite.height - 2

    
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

      
      
      #Show Space Invader sprite
      m,r = divmod(moves,SpaceInvaderDisplaySpeed)
      if(r == 0):
        LED.SmallInvader.DisplayAnimated(InvaderH,InvaderV)
      
      
      # Show SCORE
      m,r = divmod(moves,DisplayScoreSpeed)
      if(r == 0):
        ScoreH = LED.HatWidth  - ScoreSprite.width
        ScoreV = LED.HatHeight - ScoreSprite.height
        ScoreString = str(PlayerShip.score)         
        ScoreSprite.EraseWholeSprite(ScoreH,ScoreV)
        ScoreSprite = LED.CreateBannerSprite(ScoreString)
        ScoreSprite.Display(ScoreH,ScoreV)

      
      #Spawn UFOShip
      m,r = divmod(moves,ChanceOfUFOShip)
      if (r == 0 and UFOShip.alive == 0):
        print ("Spawning UFO")
        UFOShip.alive = 1
        UFOShip.direction = LED.ReverseDirection(UFOShip.direction)
        if (UFOShip.direction == 2):
          UFOShip.h = 0
          UFOShip.v = 0
        else:
          UFOShip.h = LED.HatWidth - RightSideSize-1
          UFOShip.v = 0
        
        h = UFOShip.h
        v = UFOShip.v
        Playfield[v][h] = UFOShip
        UFOShip.Display()
      
      
    

      
      if (PlayerShip.alive == 1):
        #print ("M - Playership HV speed alive exploding direction: ",PlayerShip.h, PlayerShip.v,PlayerShip.speed, PlayerShip.alive, PlayerShip.exploding, PlayerShip.direction)
        m,r = divmod(moves,PlayerShip.speed)
        if (r == 0):
          DotInvaderMovePlayerShip(PlayerShip,Playfield)
          i = random.randint(0,5)
          if (i >= 0):
            AdjustSpeed(PlayerShip,'fast',1)
          #print ("M - Player moved?")
          
            
      
      if (UFOShip.alive == 1):
        m,r = divmod(moves,UFOShip.speed)
        if (r == 0):
          #Turn off UFO if it reached the side
          if ((UFOShip.h == 0  and UFOShip.direction == 4)
            or UFOShip.h == LED.HatWidth - RightSideSize -1 and UFOShip.direction == 2):
            UFOShip.alive = 0
            Playfield[UFOShip.v][UFOShip.h] = Empty
            LED.setpixel(UFOShip.h,UFOShip.v,0,0,0)
          else:
            MoveUFO(UFOShip)
            UFOShip.Display()
          

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

        FireworksExplosion.Animate(UFOShip.h,UFOShip.v,'forward',0.01,1)        
        FireworksExplosion.Animate(PlayerMissile1.h,PlayerMissile1.v,'forward',0.01,1)        
        FireworksExplosion.Animate(PlayerMissile2.h,PlayerMissile2.v,'forward',0.01,1)        
        FireworksExplosion.Animate(UFOMissile1.h,UFOMissile1.v,'forward',0.01,1)        
        FireworksExplosion.Animate(UFOMissile2.h,UFOMissile2.v,'forward',0.01,1)        
        FireworksExplosion.Animate(UFOShip.h,UFOShip.v,'forward',0.01,1)        
        
        ShowFireworks(FireworksExplosion,(random.randint(1,10)),0.01)
        LED.ShowDropShip(PlayerShip.h,PlayerShip.v,'pickup',LED.ScrollSleep * 0.001)

      
      if (ArmadaLevel == LED.HatHeight-1):
        PlayerShip.alive = 0
        LevelFinished = 'Y'

      
        if (PlayerShip.lives <=0):
          Finished = 'Y'


        else:
          PlayerShip.alive = 1
        
        LED.PlayerShipExplosion.Animate(PlayerShip.h-2,PlayerShip.v-2,'forward',0.025)

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
    





















