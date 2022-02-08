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


#For displaying crypto currency
#from pycoingecko import CoinGeckoAPI
#price = CoinGeckoAPI().get_price(ids='bitcoin', vs_currencies='usd')



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



#--------------------------------------
# DefenderWorld                      --
#--------------------------------------


class DefenderWorld(object):
  def __init__(self,name,width,height,Map,Playfield,CurrentRoomH,CurrentRoomV,DisplayH, DisplayV, mutationrate, replicationrate,mutationdeathrate,VirusStartSpeed):
    self.name      = name
    self.width     = width
    self.height    = height
    self.Foreground   = Layer()
    self.Middleground = Layer()
    self.Background   = Layer()
    self.Playfield    = ([[]])
    self.DisplayH     = DisplayH
    self.DisplayV     = DisplayV

    self.Map             = [[0 for i in range(self.width)] for i in range(self.height)]
    self.Playfield       = [[LED.EmptyObject for i in range(self.width)] for i in range(self.height)]

        
      

  def CopySpriteToPlayfield(self,TheSprite,h,v, ColorTuple=(-1,-1,-1),ObjectType = 'Wall',Filler='EmptyObject'):
    #Copy a regular sprite to the Playfield.  Sprite will be treated as a wall.

    #print ("Copying sprite to playfield:",TheSprite.name, ObjectType, Filler)

    width   = self.width 
    height  = self.height
    
    if (ColorTuple == (-1,-1,-1)):
      r = TheSprite.r
      g = TheSprite.g
      b - TheSprite.b
    else:
      r,g,b   = ColorTuple

    #Copy sprite to map 
    for count in range (0,(TheSprite.width * TheSprite.height)):
      y,x = divmod(count,TheSprite.width)

    #check the sprite grid at location[count] to see if it has a 1 or zero.  Remember the grid is a simple array.
    #I was young and new when I first wrote the first sprite functions, and did not understand arrays in python.  :)
      if TheSprite.grid[count] != 0:
        if (ObjectType == 'Wall'):
          self.Playfield[y+v][x+h] = LED.Wall(x,y,r,g,b,1,1,'Wall')
        elif(ObjectType == 'WallBreakable'):
          self.Playfield[y+v][x+h] = LED.Wall(x,y,r,g,b,1,1,'WallBreakable')
        elif(ObjectType == 'Virus'):
          self.Playfield[y+v][x+h] = Virus(x,y,x,y,r,g,b,1,1, self.VirusStartSpeed   ,1,10,'?',0,0,10,'West',0,self.mutationrate,0,self.replicationrate,self.mutationdeathrate)
      else:
        if (Filler == 'EmptyObject'):
          self.Playfield[y+v][x+h] = LED.EmptyObject
        elif (Filler == 'DarkWall'):
          #dark wall
          self.Playfield[y+v][x+h] = LED.Wall(x,y,5,5,5,1,1,'Wall')
        else:
          self.Playfield[y+v][x+h] = LED.EmptyObject

           
    return;




  def DisplayWindow(self,h,v,ZoomFactor = 0):
    #This function accepts h,v coordinates for the entire map (e.g. 1,8  20,20,  64,64)    
    #Displays what is on the playfield currently, including walls, cars, etc.
    #Zoom factor is used to shrink/expand the display
    r = 0
    g = 0
    b = 0
    count = 0
    H_modifier = 0
    V_modifier = 0
    
    HIndentFactor = 0    
    VIndentFactor = 0    



    if (ZoomFactor > 1):
      H_modifier = (1 / LED.HatWidth ) * ZoomFactor * 2  #BigLED is 2 times wider than tall. Hardcoding now, will fix later. 
      V_modifier = (1 / LED.HatHeight ) * ZoomFactor
      NewHeight = round(LED.HatHeight * V_modifier)
      NewWidth  = round(LED.HatWidth * H_modifier)


      HIndentFactor = (LED.HatWidth / 2)  - (NewWidth /2)
      VIndentFactor = (LED.HatHeight / 2) - (NewHeight /2)
    else:
      IndentFactor = 0

    #print("LED.HatWidth",LED.HatWidth," NewWidth",NewWidth," ZoomFactor:",ZoomFactor,"HV_modifier",HV_modifier, "IndentFactor:",IndentFactor)

    for V in range(0,LED.HatHeight):
      for H in range (0,LED.HatWidth):
        #print ("DisplayWindow hv HV: ",h,v,H,V) 
        name = self.Playfield[v+V][h+H].name
        #print ("Display: ",name,V,H)
        if (name == 'EmptyObject'):
          r = 0
          g = 0
          b = 0          

        else:
          r = self.Playfield[v+V][h+H].r
          g = self.Playfield[v+V][h+H].g
          b = self.Playfield[v+V][h+H].b
          
        #Our map is an array V of array H  [V][1,2,3,4...etc]
        if (ZoomFactor > 0):
          LED.TheMatrix.SetPixel((H * H_modifier) + HIndentFactor ,(V * V_modifier) + VIndentFactor,r,g,b)
        
    

        else:
          LED.TheMatrix.SetPixel(H,V,r,g,b)
    
    #unicorn.show()
    #SendBufferPacket(RemoteDisplay,LED.HatHeight,LED.HatWidth)



  def DisplayWindowZoom(self,h,v,Z1=8,Z2=1,ZoomSleep=0.05):
    #uses playfield to display items

    if (Z1 <= Z2):
      for Z in range (Z1,Z2):
        LED.TheMatrix.Clear()
        self.DisplayWindow(h,v,Z)
        #time.sleep(ZoomSleep)
        
    else:
      for Z in reversed(range(Z2,Z1)):
        LED.TheMatrix.Clear()        
        self.DisplayWindow(h,v,Z)
        #time.sleep(ZoomSleep)
        


            
  def DisplayWindowWithSprite(self,h,v,ClockSprite):
    #This function accepts h,v coordinates for the entire map (e.g. 1,8  20,20,  64,64)    
    #Displays what is on the playfield currently, including walls, cars, etc.
    r = 0
    g = 0
    b = 0
    count = 0
        

    for V in range(0,LED.HatWidth):
      for H in range (0,LED.HatHeight):
         
        name = self.Playfield[v+V][h+H].name
        #print ("Display: ",name,V,H)
        if (name == 'EmptyObject'):
          r = 0
          g = 0
          b = 0          

        else:
          r = self.Playfield[v+V][h+H].r
          g = self.Playfield[v+V][h+H].g
          b = self.Playfield[v+V][h+H].b
          
        #Our map is an array of arrays [v][h] but we draw h,v
        LED.TheMatrix.SetPixel(H,V,r,g,b)

    #Display clock at current location
    #Clock hv will allow external functions to slide clock all over screen

    #print ("Clock info  hv on: ",ClockSprite.h,ClockSprite.v,ClockSprite.on)
    ClockSprite.CopySpriteToBuffer(ClockSprite.h,ClockSprite.v)
        
    #unicorn.show()
    #SendBufferPacket(RemoteDisplay,LED.HatHeight,LED.HatWidth)






  def FindClosestObject(self,SourceH,SourceV, Radius = 10, ObjectType = 'WallBreakable'):
    #Find the HV co-ordinates of the closest playfield object
    #
    #print("Searching for nearby food SourceH SourceV Radius ObjectType",SourceH, SourceV, Radius, ObjectType)
    #Prepare co-ordinates for search grid
    StartX = SourceH - Radius
    StopX  = SourceH + Radius
    StartY = SourceV - Radius
    StopY  = SourceV + Radius
    
    
    ClosestX     = -1
    ClosestY     = -1
    MinDistance  = 9999
    Distance     = 0

    #Check boundaries
    if (StartX < 0):
      StartX = 0
    if (StartX > LED.HatWidth-1):
      StartX = LED.HatWidth-1
    if (StartY < 0):
      StartY = 0
    if (StartY > LED.HatHeight-1):
      StartY = LED.HatHeight-1

    if (StopX < 0):
      StopX = 0
    if (StopX > LED.HatWidth-1):
      StopX = LED.HatWidth-1
    if (StopY < 0):
      StopY = 0
    if (StopY > LED.HatHeight-1):
      StopY = LED.HatHeight-1
        

    #print("Start XY Stop XY",StartX,StartY, StopX, StopY)
    
    for x in range(StartX,StopX):
      for y in range(StartY, StopY):
        #Look for object on the playfield
        #print ("searching xy: ",x,y, " found ",self.Playfield[y][x].name)

        #remember playfield coordinates are swapped
        if (self.Playfield[y][x].name == ObjectType):
          Distance = GetDistanceBetweenDots(SourceH,SourceV,x,y)
          #print ("Distance: ",Distance, " MinDistance:",MinDistance, "xy:",x,y)
          if (Distance <= MinDistance):
            MinDistance = Distance
            ClosestX = x
            ClosestY = y
      
    #FlashDot5(ClosestX,ClosestY,0.003)
    return ClosestX,ClosestY;






#-----------------------------
# Outbreak Global Variables --
#-----------------------------
InstabilityFactor = 50
ScrollSpeedLong   = 500
ScrollSpeedShort  = 5
MinBright         = 100
MaxBright         = 255







    


def PlayDefender(GameMaxMinutes):      
 


  finished      = 'N'
  LevelCount    = 0

  ClockSprite         = LED.CreateClockSprite(24)
  DayOfWeekSprite     = LED.CreateDayOfWeekSprite()
  MonthSprite         = LED.CreateMonthSprite()
  DayOfMonthSprite    = LED.CreateDayOfMonthSprite()

  ClockSprite.on      = 0



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
  Ground       = LED.Layer(name="ground",    width=2048, height=32,h=0,v=0)

  Background.CreateStars(15,0,50,50)
  Middleground.CreateStars(0,0,100,100)
  Foreground.CreateStars(0,0,250,150)
  Ground.CreateMountains(0,32,0,maxheight=16)
  
  
  


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
    DefenderV = 20

    while(1==1):
      #main counter
      count = count + 1
           
      #check the time once in a while
      if(random.randint(0,500) == 1):
        if (ClockSprite.hhmm != datetime.now().strftime('%H:%M')):
          ClockSprite = LED.CreateClockSprite(24)
    


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


      #ground
      m,r = divmod(count,grate)
      if(r == 0):
        gx = gx + 1
        if(gx >= gwidth + LED.HatWidth ):
          gx = 0
      #Canvas = Ground.PaintOnCanvas(gx,0,Canvas)


      #Canvas = LED.PaintThreeLayerCanvas(bx,mx,fx,Background,Middleground,Ground,Canvas)
      Canvas = LED.PaintFourLayerCanvas(bx,mx,fx,gx,Background,Middleground,Foreground,Ground,Canvas)


      
      #Canvas = LED.RunningMan3Sprite.PaintAnimatedToCanvas(-6,14,Canvas)

      
      if(Ground.map[DefenderV + 5][gx ] != (0,0,0)): 
        if(random.randint(0,5) == 1):
          DefenderV = DefenderV - 1
      else:
        if(random.randint(0,15) == 1):
          DefenderV = DefenderV + 1
      
      Canvas = LED.Defender.PaintAnimatedToCanvas(5,DefenderV,Canvas)
      Canvas = LED.CopySpriteToCanvasZoom(ClockSprite,30,2,(0,100,0),(0,5,0),2,False,Canvas)
     
      Canvas = LED.TheMatrix.SwapOnVSync(Canvas)
      
    




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


















