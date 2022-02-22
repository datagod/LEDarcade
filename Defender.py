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


DefenderWorldWidth = 2048
HumanCount         = 20
EnemyShipCount     = 50


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
  except:
    print("ERROR at location:",ScanV + V, ScanH + H)
  

    

  return ItemList



def ScanFarAway(H,V,Defender,DefenderPlayfield):
  #HV are the current upper left hand corner of the displayed playfield window
  ScanDirection = 2
  ScanH         = Defender.h + Defender.width  #start in front of ship
  ScanV         = Defender.v
  Item          = ''
  ItemList      = [('EmptyObject',0,0)]
  RadarStart    = 20
  RadarStop     = 50
  
  # x 20...50
  
 
  try:

    for x in range(RadarStart,RadarStop):
      ScanH, ScanV = LED.CalculateDotMovement(ScanH,ScanV,ScanDirection)
      if(ScanH + H < DefenderPlayfield.width):
        
        if(DefenderPlayfield.map[ScanV + V][ScanH + H].alive == True):
          Item = DefenderPlayfield.map[ScanV + V][ScanH + H].name
          ItemList.append((Item,ScanH,ScanV))
  except:
    print("ERROR at location:",ScanV + V, ScanH + H)

  return ItemList



def LookForTargets(H,V,TargetName,Defender, DefenderPlayfield,Canvas):
  #HV are the current upper left hand corner of the displayed playfield window
  EnemyName = 'EmptyObject'
  EnemyH    = -1
  EnemyV    = -1
  StartX    = 64
  StopX     = 40


  try:

    #Look at furthest part of the screen and start checking for enemies
    x = 0
    y = 0
    
    if (LED.HatWidth + H >= DefenderPlayfield.width):
      StartX =  LED.HatWidth - (LED.HatWidth + H -DefenderPlayfield.width)
    else:
      StartX = LED.HatWidth -1

    #If an enemy is on screen, take note and exit the loops
    #sprites are usually bigger than a dot, so we use range step of 2 to increase speed
    Found = False
    for x in range (StartX,0,-2):
      #print(DefenderPlayfield.map[y][x].name)
      for y in range(0,LED.HatHeight-1,2):

        if(DefenderPlayfield.map[y][x + H - 1].name == TargetName and DefenderPlayfield.map[y][x + H - 1].alive == True):
          
          if(DefenderPlayfield.map[y][x + H - 1].v < Defender.v):
            #we do randint to stop the jitteriness of ship moving up and down
            if(random.randint(0,10) == 1):
              Defender.v = Defender.v - 1
            Found = True
            break
          elif(DefenderPlayfield.map[y][x + H -1].v > Defender.v):
            if(random.randint(0,10) == 1):
              Defender.v = Defender.v + 1
            Found = True
            break
      if(Found == True):
        break


  except:
    print("ERROR at location: xy H StartX x+H",x,y,StartX,x+H)
    print("A stupid error has occurred when finding targets.  Please fix this soon.")

  
  #If an target was found, scan to see if it is in firing range
  if(Found == True):
    ItemList = ScanFarAway(H,V,Defender,DefenderPlayfield)
    EnemyTargets = ['Human','EnemyShip']

    
    #print(ItemList)
    
    for i in range (0,len(ItemList)):
      EnemyName,EnemyH, EnemyV = ItemList[i]
      if(EnemyName in EnemyTargets):
        break
    

  return EnemyName,EnemyH, EnemyV
      

    #if ( any(item in EnemyTargets for item,h,v in ItemList)):
      #for x in range (0,45):
      #  LED.setpixel(Defender.h + 5 + x,Defender.v + 2,255,0,0)




def ShootTarget(PlayfieldH, PlayfieldV, TargetName, TargetH,TargetV,Defender, DefenderPlayfield,Canvas):\
  #PlayfieldH is the upper left hand corner of the playfield window being displayed
  #TargetH and TargetV are on screen co-ordinates (64x32)
  print("TargetName:",TargetName)
  print("Shooting:",DefenderPlayfield.map[TargetV][TargetH+PlayfieldH].name)
  graphics.DrawLine(Canvas,Defender.h + 5, Defender.v +2, TargetH, TargetV +2, graphics.Color(255,0,0))
  DefenderPlayfield.map[TargetV][TargetH+PlayfieldH].alive = False
  DefenderPlayfield.map[TargetV][TargetH+PlayfieldH].EraseSpriteFromPlayfield(DefenderPlayfield)


  return DefenderPlayfield 

  

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

    


def PlayDefender(GameMaxMinutes):      
 


  finished      = 'N'
  LevelCount    = 0

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




  LED.TheMatrix.Clear()
  LED.Canvas.Clear()
  


  #The map is an array of a lists.  You can address each element has VH e.g. [V][H]
  #Copying the map to the playfield needs to follow the exact same shape



  #----------------------
  #-- Prepare Level    --
  #----------------------
  print("")
  print("")
  print("*****************************************************")
  #LED.OutbreakGamesPlayed = LED.OutbreakGamesPlayed + 1
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
  Ground.CreateMountains(0,32,0,maxheight=16)
  
  
  
  #--------------------------------
  #-- Create Enemies             --
  #--------------------------------


  Humans = []

  #humans must be located at least HatWidth from the start
  for count in range (0,HumanCount):
    LED.HumanSprite.framerate = random.randint(15,50)
    Humans.append(copy.deepcopy(LED.HumanSprite))
    Humans[count].h = random.randint(64,DefenderWorldWidth)
    Humans[count].v = random.randint(16,LED.HatHeight-1)
    
    print("Placing humans:",count)
    DefenderPlayfield.CopyAnimatedSpriteToPlayfield(Humans[count].h,Humans[count].v,Humans[count])
    

  EnemyShips = []
  for count in range (0,EnemyShipCount):
    NewSprite = copy.deepcopy(LED.ShipSprites[random.randint(0,27)])
    NewSprite.framerate = random.randint(2,12)
    NewSprite.name = "EnemyShip"
    EnemyShips.append(NewSprite)

    Finished = False
    while (Finished == False):
      #Find a spot in the sky for the ship
      h = random.randint(64,DefenderWorldWidth)
      v = random.randint(1,LED.HatHeight-1)

      if(Ground.map[v][h] == (0,0,0)):
        EnemyShips[count].h = h
        EnemyShips[count].v = v
        
        Finished = True
        print("Placing EnemyShips:",count)
        DefenderPlayfield.CopyAnimatedSpriteToPlayfield(EnemyShips[count].h,EnemyShips[count].v,EnemyShips[count])




  #--------------------------------
  #-- Main timing loop           --
  #--------------------------------


  x = 0

  Canvas = LED.TheMatrix.CreateFrameCanvas()
  Canvas.Fill(0,5,0)
  Canvas = LED.TheMatrix.SwapOnVSync(Canvas)



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
    DisplayH  = 0
    DiosplayV = 0

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


      #paint humans on Canvas 
      for i in range (0,HumanCount):
        if(EnemyShips[i].alive == True):
          if(random.randint(0,5) == 1):
            #move human
            Humans[i].h = Humans[i].h + 1
            if Humans[i].h > DefenderPlayfield.width:
              Humans[i].h = 0
          
          hH = Humans[i].h
          hV = Humans[i].v
        
          #check if human is in currently displayed area
          if(DisplayH <=  hH  <= (DisplayH + LED.HatWidth)):
            Canvas = Humans[i].PaintAnimatedToCanvas(hH-DisplayH,hV,Canvas)



      #paint EnemyShip on Canvas
      for i in range (0,EnemyShipCount):
        if(EnemyShips[i].alive == True):
          H = EnemyShips[i].h 
          V = EnemyShips[i].v 
          #check if EnemyShip is in currently displayed area
          if((DisplayH <=  H  <= (DisplayH + LED.HatWidth)) or
            (DisplayH <=  H + EnemyShips[i].width  <= (DisplayH + LED.HatWidth))):
            Canvas = EnemyShips[i].PaintAnimatedToCanvas(H-DisplayH,V,Canvas)
      


      
      #--------------------------------
      #-- Move Defender              --
      #--------------------------------

      #defender needs to avoid the ground
      #shoot enemies
      #pick up humans
      


      
      ScanV = Defender.v + 5
      if(ScanV > LED.HatHeight -2):
        ScanV = LED.HatHeight -2

      
      if(Ground.map[ScanV][gx] != (0,0,0)): 
        if(random.randint(0,20) == 1):
          Defender.v = Defender.v - 1
      else:
        if(random.randint(0,15) == 1):
          Defender.v = Defender.v + 1

      #Find targets and start blasting
      EnemyName, EnemyH, EnemyV = LookForTargets(gx,0, 'EnemyShip',Defender,DefenderPlayfield,Canvas)
      if(EnemyName == 'EnemyShip'):
        #print("Shooting:",EnemyName, EnemyH ,EnemyV)
        DefenderPlayfield = ShootTarget(gx, 0, EnemyName,EnemyH, EnemyV, Defender,DefenderPlayfield,Canvas)
        #graphics.DrawLine(Canvas,Defender.h + 5, Defender.v + 2, Defender.h + 40, Defender.v + 2, graphics.Color(255,0,0));

      Canvas = LED.Defender.PaintAnimatedToCanvas(5,Defender.v,Canvas)



      


      Canvas = LED.CopySpriteToCanvasZoom(ClockSprite,30,2,(0,100,0),(0,5,0),2,False,Canvas)
      Canvas = LED.TheMatrix.SwapOnVSync(Canvas)
      
    



      #if(random.randint(0,50) == 1):
      #  DebugPlayfield(DefenderPlayfield.map,gx,0,64,32)




  #let the display show the final results before clearing
  time.sleep(1)
  LED.ClearBigLED()

  return






























def LaunchDefender(GameMaxMinutes = 10000):
  
    PlayDefender(GameMaxMinutes)
    
    #--------------------------------------
    # M A I N   P R O C E S S I N G      --
    #--------------------------------------

    LED.ShowTitleScreen(
        BigText             = 'SPACE',
        BigTextRGB          = LED.HighRed,
        BigTextShadowRGB    = LED.ShadowRed,
        LittleText          = 'DEFENDER',
        LittleTextRGB       = LED.MedGreen,
        LittleTextShadowRGB = (0,10,0), 
        ScrollText          = 'BRING ON THE MUTANTS',
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






#execute if this script is called direction
if __name__ == "__main__" :
  while(1==1):
    #LED.LoadConfigData()
    #LED.SaveConfigData()
    print("After SAVE OutbreakGamesPlayed:",LED.OutbreakGamesPlayed)
    LaunchDefender(100000)        


















