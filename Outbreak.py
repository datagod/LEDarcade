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
#    ___        _   _                    _                                   --
#   / _ \ _   _| |_| |__  _ __ ___  __ _| | __                               --
#  | | | | | | | __| '_ \| '__/ _ \/ _` | |/ /                               --
#  | |_| | |_| | |_| |_) | | |  __/ (_| |   <                                --
#   \___/ \__,_|\__|_.__/|_|  \___|\__,_|_|\_\                               --
#                                                                            --
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
LED.Initialize()
import copy
import random
import time
import numpy
import math
from numba import njit


#For displaying crypto currency
#from pycoingecko import CoinGeckoAPI
#price = CoinGeckoAPI().get_price(ids='bitcoin', vs_currencies='usd')



random.seed()
start_time = time.time()






#-----------------------------
# Outbreak Global Variables --
#-----------------------------
VirusTopSpeed     = 1
VirusBottomSpeed  = 15
VirusStartSpeed   = 15  #starting speed of the viruses
MinBright         = 50
MaxBright         = 255

OriginalMutationRate      = 10000
OriginalMutationDeathRate = 500
MaxMutations              = 5      #Maximum number of mutations, if surpassed the virus dies
MutationTypes             = 10     #Number of different types of mutations
OriginalReplicationRate   = 5000
replicationrate           = OriginalReplicationRate
FreakoutReplicationRate   = 10     #new replication rate when a virus freaksout
MaxVirusMoves             = 1000000 #after this many moves the level is over
FreakoutMoves             = 10000  #after this many moves, the viruses will replicate and mutate at a much greater rate
VirusMoves                = 0      #used to count how many times the viruses have moved
ClumpingSpeed             = 25     #This modifies the speed of viruses that contact each other
ReplicationSpeed          = 5      #When a virus replicates, it will be a bit slower.  This number is added to current speed.
ChanceOfSpeedup           = 50     #determines how often a lone virus will spontaneously speed up
SlowTurnMinMoves          = 1      #number of moves a mutated virus moves before turning
SlowTurnMaxMoves          = 40     #number of moves a mutated virus moves before turning
MaxReplications           = 5      #Maximum number of replications, if surpassed the virus dies
InfectionChance           = 5     #Chance of one virus infecting another, lower the number greater the chance
DominanceMaxCount         = 250000   #how many ticks with there being only one virus, when reached level over
VirusNameSpeedupCount     = 1000    #when this many virus strains are on the board, speed them up
ChanceOfDying             = 5000   #random chance of a virus dying
GreatChanceOfDying        = 5000    #random chance of a virus dying when too many straings are alive
ChanceOfHeadingToHV       = 250000  #random chance of all viruses being interested in the same location
ChanceOfHeadingToFood     = 100     #random chance of a virus heading towards the nearest food
FoodCheckRadius           = 15      #radius around the virus when looking for food
ChanceOfTurningIntoFood   = 5      #Random chance of a dying mutating virus to turn into food
ChanceOfTurningIntoWall   = 5      #Random chance of a dying mutating virus to turn into food
VirusFoodWallLives        = 5      #Lives of food before it gets eaten and disappears
AuditSpeed                = 2000   #Every X tick, an audit text window is displayed for debugging purposes
EatingSpeedAdjustment     = 0     #When a virus eats, it gets full and slows down             
SpeedIncrements           = 20     #how many chunks the speed range is cut up into, for increasing gradually
FoodBrightnessSteps       = 25     #each time a food loses life, it gets brighter by this many units
ChanceToStopEating        = 100    #chance that a virus decides to stop eating and carry on with life
ChanceOfRandomFood        = 250000  #chance that random food will show up, which will draw the viruses to it
MapOffset                 = 20     #how many pixels from the left screen does the map really start (so we don't overwrite clocks and other things)
BigFoodLives              = 500    #lives for the big food particle
BigFoodRGB                = (255,0,0)
MaxRandomViruses          = 50     #maximum number of random viruses to place on big food maps
VirusMaxCount             = 500      #maximum number of unique virus strains allowed
MaxLevelsPlayed           = 25      #quit after 5 maps are played

#Sprite display locations
ClockH,      ClockV,      ClockRGB      = 0,0,  (0,150,0)
DayOfWeekH,  DayOfWeekV,  DayOfWeekRGB  = 0,6,  (150,0,0)
MonthH,      MonthV,      MonthRGB      = 0,12, (0,20,200)
DayOfMonthH, DayOfMonthV, DayOfMonthRGB = 2,18, (100,100,0)
CurrencyH,   CurrencyV,   CurrencyRGB   = 0,27, (0,150,0)

#Sprite filler tuple
SpriteFillerRGB = (0,4,0)

  
#RGB Objects
#Canvas = LED.TheMatrix.CreateFrameCanvas()
#Canvas.Fill(0,0,0)

#PreviousFrame = [[(-1, -1, -1) for _ in range(LED.HatWidth)] for _ in range(LED.HatHeight)]
#ScreenArray = [[(0, 0, 0) for _ in range(LED.HatWidth)] for _ in range(LED.HatHeight)]



#---------------------------------------
#Variable declaration section
#---------------------------------------
ScrollSleep         = 0.025
TerminalTypeSpeed   = 0.02  #pause in seconds between characters
TerminalScrollSpeed = 0.02  #pause in seconds between new lines
CursorRGB           = (0,255,0)
CursorDarkRGB       = (0,50,0)
fast_rng            = None  #a faster implementation of random


BrightRGB  = (0,200,0)
ShadowRGB  = (0,5,0)
ShowCrypto = 'N'
KeyboardSpeed   = 500
CheckClockSpeed = 500

CheckTime        = 60
random.seed()
start_time = time.time()


#--------------------------------------
# VirusWorld  / OUTBREAK             --
#--------------------------------------

# Ideas:
# - Mutations happen
# - if virus is mutating, track that in the object itself
# - possible mutations: speed, turning eraticly
# - aggression, defence can be new attributes
# - need a new object virus dot
# - when a virus conquers an area, remove part of the wall and scroll to the next area
# - areas may have dormant viruses that are only acivated once in a while
# - virus will slow down to eat










class FastRandom:
    def __init__(self, seed=1):
        self.state = seed

    def randint(self, low, high):
        self.state = (1103515245 * self.state + 12345) & 0x7FFFFFFF
        return low + (self.state % (high - low + 1))

    def random(self):
        self.state = (1103515245 * self.state + 12345) & 0x7FFFFFFF
        return self.state / 0x7FFFFFFF

    def choice(self, seq):
        index = self.randint(0, len(seq) - 1)
        return seq[index]















#--------------------------------------
# VirusWorld                         --
#--------------------------------------

# Ideas:
# - Mutations happen
# - if virus is mutating, track that in the object itself
# - possible mutations: speed, turning eraticly
# - aggression, defence can be new attributes
# - need a new object virus dot
# - when a virus conquers an area, remove part of the wall and scroll to the next area
# - areas may have dormant viruses that are only acivated once in a while
# - 

class VirusWorld(object):
#Started out as an attempt to make cars follow shapes.  I was not happy with the results so I converted into a petri dish of viruses
  DefaultColorList = {
        ' ' : (  0,  0,  0),
        '-' : ( 10, 10, 10),
        '.' : ( 20, 20, 20),
        'o' : ( 30, 30, 30),
        'O' : ( 40, 40, 40),
        '@' : ( 50, 60, 60),
        '$' : ( 60, 60, 60),
        'A' : (  0,  0, 40),
        'B' : ( 10, 10, 50),
        'C' : ( 20, 20, 60),
        'D' : ( 30, 30, 70),
        'E' : ( 40, 40, 80),
        'F' : ( 50, 50, 90),
        'G' : ( 60, 60,100),
        'H' : ( 70, 70,110),
        'I' : ( 80, 80,120),
        'J' : ( 90, 90,130),
        'K' : (100,100,140),
        'L' : (110,110,150),
        '|' : (150,150,175),
        '*' : (175,175,175),
        '=' : (200,200,200),
        '#' : (150,150,150),
        '1' : (  0,200,  0),
        '2' : (150,  0,  0),
        '3' : (150,100,  0),
        '4' : (  0,  0,100),
        '5' : (200,  0, 50),
        '6' : (125,185,  0),
        '7' : (200,  0,200),
        '8' : ( 50,150, 75)
    }

  DefaultTypeList = {
        ' ' : 'EmptyObject',
        '-' : 'wall',
        '.' : 'wall',
        'o' : 'wall',
        'O' : 'wall',
        '@' : 'wall',
        '#' : 'wall',
        '$' : 'wall',
        '*' : 'wallbreakable',
        'A' : 'wallbreakable',
        'B' : 'wallbreakable',
        'C' : 'wallbreakable',
        'D' : 'wallbreakable',
        'E' : 'wallbreakable',
        'F' : 'wallbreakable',
        'G' : 'wallbreakable',
        'H' : 'wallbreakable',
        'I' : 'wallbreakable',
        'J' : 'wallbreakable',
        'K' : 'wallbreakable',
        'L' : 'wallbreakable',
        '|' : 'wall',
        '1' : 'virus',
        '2' : 'virus',
        '3' : 'virus',
        '4' : 'virus',
        '5' : 'virus',
        '6' : 'virus',
        '7' : 'virus',
        '8' : 'virus'
    }



  def __init__(self,name,width,height,Map,Playfield,CurrentRoomH,CurrentRoomV,DisplayH, DisplayV, mutationrate, replicationrate,mutationdeathrate,VirusStartSpeed):
    self.name      = name
    self.width     = width
    self.height    = height
    self.Map       = ([[]])
    self.Playfield = ([[]])
    self.CurrentRoomH = CurrentRoomH
    self.CurrentRoomV = CurrentRoomV
    self.DisplayH     = DisplayH
    self.DisplayV     = DisplayV
    self.mutationrate      = mutationrate
    self.replicationrate   = replicationrate
    self.mutationdeathrate = mutationdeathrate
    self.VirusStartSpeed   = VirusStartSpeed

    self.Map              = [[0 for i in range(self.width)] for i in range(self.height)]
    self.Playfield        = [[LED.EmptyObject for i in range(self.width)] for i in range(self.height)]
    self.walllives        = VirusFoodWallLives
    self.Viruses          = []


  @staticmethod
  def GenerateEmptyMap(width, height, fill_char=' '):
      """
      Generates a text-based empty map.

      Returns:
          list[str]: A list of strings representing the empty map.
      """
      if len(fill_char) != 1:
          raise ValueError("fill_char must be a single character.")
      return [fill_char * width for _ in range(height)]

  @staticmethod
  def GenerateEmptyMapWithBorder(width, height, wall_char='-', fill_char=' '):
      """
      Generates a map with a solid border of wall characters.

      Returns:
          list[str]: A list of strings representing the bordered map.
      """
      if len(wall_char) != 1 or len(fill_char) != 1:
          raise ValueError("Characters must be single characters.")
      if width < 3 or height < 3:
          raise ValueError("Minimum map size with border is 3x3.")
      map_rows = [wall_char * width]
      for _ in range(height - 2):
          map_rows.append(wall_char + fill_char * (width - 2) + wall_char)
      map_rows.append(wall_char * width)
      return map_rows

  def AddRandomVirusesToPlayfield(self,VirusesToAdd=25):
    global fast_rng

    AddedCount = 0
    
    while (AddedCount <= VirusesToAdd):
      h = fast_rng.randint(15,self.width-2) #we use a 15 pixel offset because of other display items
      v = fast_rng.randint(2,self.height-2)
      #print ("hv",h,v,self.Playfield[v][h].name)
      if (self.Playfield[v][h].name == 'EmptyObject' or
          self.Playfield[v][h].name == 'WallBreakable'
        ):
        #print("empty")
        r,g,b = LED.BrightColorList[fast_rng.randint(1,27)]
        VirusName = str(r) + '-' + str(g) + '-' + str(b)
        self.Playfield[v][h] = Virus(h,v,0,0,r,g,b,1,1, self.VirusStartSpeed   ,1,10,VirusName,0,0,10,'West',0,self.mutationrate,0,self.replicationrate,self.mutationdeathrate)
        self.Viruses.append(self.Playfield[v][h])
        AddedCount = AddedCount + 1
          
          

  def CopyTextMapToPlayfield(self,TextMap):
    global fast_rng

    
    mapchar = ""
    r = 0
    g = 0
    b = 0
    h = 0
    v = 0
    dottype   = ""
    VirusName = ""
    self.Playfield = ([[]])
    self.Playfield = [[LED.EmptyObject for i in range(TextMap.width)] for i in range(TextMap.height)]
    self.Viruses = []


    #read the map string and process one character at a time
    #decode the color and type of dot to place
    for y in range (0,TextMap.height):
      print (TextMap.map[y])
      for x in range (0,TextMap.width):
        mapchar = TextMap.map[y][x]
        r,g,b   = TextMap.ColorList.get(mapchar)
        dottype = TextMap.TypeList.get(mapchar)
        h = x #+ TextMap.h
        v = y #+ TextMap.v
        
        
        if (dottype == "virus"):
          VirusName = str(r) + '-' + str(g) + '-' + str(b)
          
          #(h,v,dh,dv,r,g,b,direction,scandirection,speed,alive,lives,name,score,exploding,radarrange,destination,mutationtype,mutationrate, mutationfactor, replicationrate):
          self.Playfield[v][h] = Virus(h,v,0,0,r,g,b,1,1, self.VirusStartSpeed   ,1,10,VirusName,0,0,10,'West',0,self.mutationrate,0,self.replicationrate,self.mutationdeathrate)
          #self.Playfield[y][x].direction = PointTowardsObject8Way(x,y,height/2,width/2)

          self.Viruses.append(self.Playfield[v][h])
        elif (dottype == "wall"):
          self.Playfield[v][h] = LED.Wall(h,v,r,g,b,1,1,'Wall')

        elif (dottype == "wallbreakable"):
          self.Playfield[v][h] = LED.Wall(h,v,r,g,b,1,self.walllives,'WallBreakable')

        

      
    return



  def CopyMapToPlayfield(self):
    #This function is run once to populate the playfield with viruses, based on the map drawing
    #XY is actually implemented as YX.  Counter intuitive, but it works.

    global fast_rng

    width   = self.width 
    height  = self.height
    self.Viruses = []
    print ("Map width height:",width,height)
    VirusName = ""
   
    print ("RD - CopyMapToPlayfield - Width Height: ", width,height)
    x = 0
    y = 0
    
    
    print ("width height: ",width,height)
    
    for y in range (0,height):
      #print (*self.Map[y])
  
      for x in range(0,width):
        #print ("RD xy color: ",x,y, self.Map[y][x])
        SDColor = self.Map[y][x]
  
        print(str(SDColor).rjust(3,' '),end='')

        if (SDColor == 1):
          r = SDDarkWhiteR
          g = SDDarkWhiteG
          b = SDDarkWhiteB
          self.Playfield[y][x] = LED.Wall(x,y,r,g,b,1,1,'Wall')


        elif (SDColor == 2):
          r = SDDarkWhiteR + 30
          g = SDDarkWhiteG + 30
          b = SDDarkWhiteB + 30
                                    #(h,v,r,g,b,alive,lives,name):
          self.Playfield[y][x] = LED.Wall(x,y,r,g,b,1,10,'Wall')
          #print ("Copying wallbreakable to playfield hv: ",y,x)

        elif (SDColor == 3):
          r = SDDarkWhiteR + 50
          g = SDDarkWhiteG + 50
          b = SDDarkWhiteB + 50
                                    #(h,v,r,g,b,alive,lives,name):
          self.Playfield[y][x] = LED.Wall(x,y,r,g,b,1,10,'Wall')
          #print ("Copying wallbreakable to playfield hv: ",y,x)

        elif (SDColor == 4):
          r = SDDarkWhiteR 
          g = SDDarkWhiteG
          b = SDDarkWhiteR + 60
                                    #(h,v,r,g,b,alive,lives,name):
          self.Playfield[y][x] = LED.Wall(x,y,r,g,b,1,self.walllives,'WallBreakable')
          #print ("Copying wallbreakable to playfield hv: ",y,x)


        #color 5 and up represents moving viruses.
        #We used to let the viruses  have a random direction, but that quickly turns into chaos
        #now each virus will be steered towards the center of the map

        elif (SDColor >=5):
          r,g,b =  ColorList[SDColor]
          VirusName = str(r) + '-' + str(g) + '-' + str(b)
          
          #(h,v,dh,dv,r,g,b,direction,scandirection,speed,alive,lives,name,score,exploding,radarrange,destination,mutationtype,mutationrate, mutationfactor, replicationrate):
          self.Playfield[y][x] = Virus(x,y,x,y,r,g,b,1,1, self.VirusStartSpeed   ,1,10,VirusName,0,0,10,'West',0,self.mutationrate,0,self.replicationrate,self.mutationdeathrate)


          #self.Playfield[y][x].direction = fast_rng.randint(1,8)
          self.Playfield[y][x].direction = PointTowardsObject8Way(x,y,height/2,width/2)
          self.Viruses.append(self.Playfield[y][x])
        else:
          #print ('EmptyObject')
          self.Playfield[y][x] = LED.EmptyObject
      print('')

    self.DebugPlayfield()
    return;







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
          #self.Playfield[y+v][x+h] = LED.Wall(x,y,r,g,b,1,1,'Wall')
          SetPlayfieldObject(v=y+v, h=x+h, obj=LED.Wall(x,y,r,g,b,1,1,'Wall'), Playfield=self.Playfield)
        elif(ObjectType == 'WallBreakable'):
          #self.Playfield[y+v][x+h] = LED.Wall(x,y,r,g,b,1,1,'WallBreakable')
          SetPlayfieldObject(v=y+v, h=x+h, obj=LED.Wall(x,y,r,g,b,1,1,'WallBreakable'), Playfield=self.Playfield)          
        elif(ObjectType == 'Virus'):
          #self.Playfield[y+v][x+h] = Virus(x,y,x,y,r,g,b,1,1, self.VirusStartSpeed   ,1,10,'?',0,0,10,'West',0,self.mutationrate,0,self.replicationrate,self.mutationdeathrate)
          SetPlayfieldObject(v=y+v, h=x+h, obj=Virus(x,y,x,y,r,g,b,1,1, self.VirusStartSpeed   ,1,10,'?',0,0,10,'West',0,self.mutationrate,0,self.replicationrate,self.mutationdeathrate), Playfield=self.Playfield)
      else:
        if (Filler == 'EmptyObject'):
          self.Playfield[y+v][x+h] = LED.EmptyObject
        elif (Filler == 'DarkWall'):
          #dark wall
          self.Playfield[y+v][x+h] = LED.Wall(x,y,5,5,5,1,1,'Wall')
        else:
          self.Playfield[y+v][x+h] = LED.EmptyObject

           
    return;



  # def DisplayWindow(self,h,v):
    # #This function accepts h,v coordinates for the entire map (e.g. 1,8  20,20,  64,64)    
    # #Displays what is on the playfield currently, including walls, cars, etc.
    # r = 0
    # g = 0
    # b = 0
    # count = 0
        

    # for V in range(0,LED.HatWidth):
      # for H in range (0,LED.HatHeight):
        # #print ("DisplayWindow hv HV: ",h,v,H,V) 
        # name = self.Playfield[v+V][h+H].name
        # #print ("Display: ",name,V,H)
        # if (name == 'EmptyObject'):
          # r = 0
          # g = 0
          # b = 0          

        # else:
          # r = self.Playfield[v+V][h+H].r
          # g = self.Playfield[v+V][h+H].g
          # b = self.Playfield[v+V][h+H].b
          
        # #Our map is an array of arrays [v][h] but we draw h,v
        # LED.TheMatrix.SetPixel(H,V,r,g,b)
    
    # #unicorn.show()
    # #SendBufferPacket(RemoteDisplay,LED.HatHeight,LED.HatWidth)



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
        #LED.TheMatrix.Clear()
        self.DisplayWindow(h,v,Z)
        #time.sleep(ZoomSleep)
        
    else:
      for Z in reversed(range(Z2,Z1)):
        #LED.TheMatrix.Clear()        
        self.DisplayWindow(h,v,Z)
        #time.sleep(ZoomSleep)
        


            
  def DisplayWindowWithSprite(self,h,v,ClockSprite):
    #This function accepts h,v coordinates for the entire map (e.g. 1,8  20,20,  64,64)    
    #Displays what is on the playfield currently, including walls, cars, etc.
    r = 0
    g = 0
    b = 0
    count = 0
        

    maxV = min(LED.HatHeight, self.height - v)
    maxH = min(LED.HatWidth, self.width - h)

    for V in range(maxV):
      for H in range(maxH):
        name = self.Playfield[v+V][h+H].name

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




  def CountVirusesInWindow(self,h,v):
    #This function accepts h,v coordinates for the entire map (e.g. 1,8  20,20,  64,64) 
    #and counts how many items are in the area
    count = 0
        
    maxV = min(LED.HatHeight, self.height - v)
    maxH = min(LED.HatWidth, self.width - h)

    for V in range(maxV):
      for H in range(maxH):
        name = self.Playfield[v+V][h+H].name
        #print ("Display: ",name,V,H)
        if (name not in ('EmptyObject',"Wall","WallBreakable")):
          count = count + 1
    return count;






  def DebugPlayfield(self):
    #Show contents of playfield - in text window, for debugging purposes
    

    height = len(self.Playfield)
    width = len(self.Playfield[0]) if height > 0 else 0
    print("DebugPlayfield - actual dimensions:", width, "x", height)
    
    
    print ("Map width height:",width,height)
  
    x = 0
    y = 0
    
    for V in range(0,height):
      for H in range (0,width):
         
        name = self.Playfield[V][H].name
        #print ("Display: ",name,V,H)
        if (name == 'EmptyObject'):
          print ('  ',end='')

        #draw border walls
        elif (name == 'Wall' and (V == 0 or V == height-1)):
          print(' _',end='')
        
        #draw border walls
        elif (name == 'Wall' and (H == 0 or H == width-1)):
          print(' |',end='')
          
        #draw interior
        elif (name == 'Wall'):
          print (' #',end='')

        #draw interior
        elif (name == 'WallBreakable'):
          print (' o',end='')

        elif (self.Playfield[V][H].alive == 1):
          print (' .',end='')
        else:
          print (' X',end='')
          #print ("Name:",name," alive:",self.Playfield[V][H].alive)

          #time.sleep(1)

      print('')





  def FindClosestObject_old(self,SourceH,SourceV, Radius = 10, ObjectType = 'WallBreakable'):
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

        #remember playfield coordinates are swapped
        if (self.Playfield[y][x].name == ObjectType):
          Distance = GetDistanceBetweenDots(SourceH,SourceV,x,y)
          #print ("Distance: ",Distance, " MinDistance:",MinDistance, "xy:",x,y)
          if (Distance <= MinDistance):
            MinDistance = Distance
            ClosestX = x
            ClosestY = y
      
    return ClosestX,ClosestY;




  @njit
  def GetDistanceSquared(self, h1, v1, h2, v2):
      dx = h1 - h2
      dy = v1 - v2
      return dx * dx + dy * dy

  def GetDistanceSquared(self, h1, v1, h2, v2):
      dx = h1 - h2
      dy = v1 - v2
      return dx * dx + dy * dy

  def FindClosestObject(self, SourceH, SourceV, Radius=10, ObjectType='WallBreakable'):
      """
      Find the HV coordinates of the closest object of a given type within a radius.
      Uses squared distance comparison to avoid slow math.sqrt calls.
      """
      StartX = max(0, SourceH - Radius)
      StopX  = min(LED.HatWidth, SourceH + Radius + 1)
      StartY = max(0, SourceV - Radius)
      StopY  = min(LED.HatHeight, SourceV + Radius + 1)

      ClosestX = -1
      ClosestY = -1
      MinDistanceSquared = Radius * Radius + 1

      for x in range(StartX, StopX):
          for y in range(StartY, StopY):
              if self.Playfield[y][x].name == ObjectType:
                  dist_sq = self.GetDistanceSquared(SourceH, SourceV, x, y)
                  if dist_sq < MinDistanceSquared:
                      MinDistanceSquared = dist_sq
                      ClosestX, ClosestY = x, y

      return ClosestX, ClosestY









class Virus(object):
  
  def __init__(self,h,v,dh,dv,r,g,b,direction,scandirection,speed,alive,lives,name,score,exploding,radarrange,destination,mutationtype,mutationrate,mutationfactor,replicationrate,mutationdeathrate):

    self.h               = h         # location on playfield (e.g. 10,35)
    self.v               = v         # location on playfield (e.g. 10,35)
    self.dh              = dh        # location on display   (e.g. 3,4) 
    self.dv              = dv        # location on display   (e.g. 3,4) 
    self.r               = r
    self.g               = g
    self.b               = b
    self.direction       = direction      #direction of travel
    self.scandirection   = scandirection  #direction of scanners, if equipped
    self.speed           = speed
    self.alive           = 1
    self.lives           = 3
    self.name            = name
    self.score           = 0
    self.exploding       = 0
    self.radarrange      = 20
    self.destination     = ""
    self.mutationtype    = mutationtype
    self.mutationrate    = mutationrate      #high number, greater chance 
    self.mutationfactor  = mutationfactor    #used to impact amount of mutation
    self.internalcounter = 0                 #used to count moves between mutation affects (i.e. turn left every 3 moves)
    self.replicationrate = replicationrate    
    self.mutationdeathrate = mutationdeathrate
    self.replications      = 0
    self.mutations         = 0
    self.infectionchance   = InfectionChance
    self.chanceofdying     = ChanceOfDying
    self.eating            = False
    self.clumping          = True


  def Display(self):
    if (self.alive == 1):
      LED.TheMatrix.SetPixel(self.h,self.v,self.r,self.g,self.b)
  
      
  def Erase(self):
    LED.TheMatrix.SetPixel(self.h,self.v,0,0,0)


  #Lower is faster!
  def AdjustSpeed(self, increment):
    speed = self.speed + increment
    if (speed > VirusBottomSpeed):
      speed = VirusBottomSpeed
    elif (speed < VirusTopSpeed):
      speed = VirusTopSpeed

    self.speed = speed
    #print("Adjust speed: ",speed, increment)
    return;

  #Lower is faster!
  def AdjustInfectionChance(self, increment):
    infectionchance = self.infectionchance + increment

    if (infectionchance > InfectionChance):
      infectionchance = InfectionChance
    elif (infectionchance < 1):
      infectionchance = 1

    self.infectionchance = infectionchance
    return;



  def Mutate(self):
    global MaxMutations
    global MutationTypes

    x              = 0
    #number of possible mutations
    # direction
    #   - left 1,2
    #   - left 1,2,3
    #   - right 1,2
    #   - left 1,2,3
    # speed up
    # speed down
    # wobble
    # slow curves left
    # slow curves right
    

    mutationrate   = self.mutationrate
    mutationtype   = self.mutationtype
    mutationfactor = self.mutationfactor
    speed          = self.speed
    MinSpeed       = 1  #* CPUModifier
    MaxSpeed       = 10 #* CPUModifier   #higher = slower!
    r              = 0
    g              = 0
    b              = 0
    name           = 0


    #Mutations can be deadly
    self.mutations += 1
    if ((           fast_rng.randint(1,self.mutationdeathrate)          == 1)
       or (self.mutations >= MaxMutations)):
      self.alive = 0
      self.lives = 0
      self.speed = 999999
      self.name  = 'EmptyObject'
      self.r     = 0
      self.g     = 0
      self.b     = 0
    else:


      #print ("--Virus mutation!--")
      mutationtype = fast_rng.randint(1,MutationTypes)

      
      #Mutations get a new name and color
      x = fast_rng.randint(1,MutationTypes)
      if (x == 1):
        #Big Red
        r = fast_rng.randint(MinBright,MaxBright)
        g = 0
        b = 0
        
      if (x == 2):
        #booger
        r = 0
        g = fast_rng.randint(MinBright,MaxBright)
        b = 0

      if (x == 3):
        #BlueWhale
        r = 0
        g = 0
        b = fast_rng.randint(MinBright,MaxBright)

      if (x == 4):
        #pinky
        r = fast_rng.randint(MinBright,MaxBright)
        g = 0
        b = fast_rng.randint(MinBright,MaxBright)

      if (x == 5):
        #MellowYellow
        r = fast_rng.randint(MinBright,MaxBright)
        g = fast_rng.randint(MinBright,MaxBright)
        b = 0

      if (x == 6):
        #undead
        r = 0
        g = fast_rng.randint(MinBright,MaxBright)
        b = fast_rng.randint(MinBright,MaxBright)



    
      #Directional Behavior - turns left a little
      if (mutationtype == 1):
        #print ("Mutation: turn left a little", self.speed, mutationfactor)
        mutationfactor       = fast_rng.randint(1,2)
        self.AdjustInfectionChance(mutationfactor * -1)

      #Directional Behavior - turns left a lot
      elif (mutationtype == 2):
        #print ("Mutation: turn left a lot", self.speed, mutationfactor)
        mutationfactor       = fast_rng.randint(2,3)
        self.AdjustInfectionChance(mutationfactor * -1)

      #Directional Behavior - turns right a little
      elif (mutationtype == 3):
        #print ("Mutation: turn right a little", self.speed, mutationfactor)
        mutationfactor    = fast_rng.randint(1,2)
        self.AdjustInfectionChance(mutationfactor * -1)

      #Directional Behavior - turns right a lot
      elif (mutationtype == 4):
        #print ("Mutation: turn right a lot", self.speed, mutationfactor)
        mutationfactor       = fast_rng.randint(2,3)
        self.AdjustInfectionChance(mutationfactor * -1)

      #Speed up and infect at a higher rate
      elif (mutationtype == 5):
        mutationfactor = 2
        self.AdjustInfectionChance(mutationfactor * -1)
        self.AdjustSpeed(mutationfactor * -1)
        #print ("Mutation: speed up", self.speed, mutationfactor)
        if (speed < 1):
          speed = 1

      #Speed down
      elif (mutationtype == 6):
        mutationfactor = 1
        self.AdjustSpeed(mutationfactor)
        self.AdjustInfectionChance(mutationfactor * -1)

        #print ("Mutation: slow down", self.speed, mutationfactor)

      #wobble
      elif (mutationtype == 7):
        mutationfactor = fast_rng.randint(1,10)
        self.clumping  = False
        #print ("Mutation: wobble",mutationfactor)
        self.AdjustSpeed(mutationfactor)
        self.AdjustInfectionChance(mutationfactor * -1)

        #swamp mix
        r = fast_rng.randint(MinBright,MaxBright)
        g = fast_rng.randint(MinBright,MaxBright)
        b = fast_rng.randint(MinBright,MaxBright)


      #slow turn left
      elif (mutationtype == 8):
        mutationfactor = fast_rng.randint(SlowTurnMinMoves,SlowTurnMaxMoves)  #higher is slower!
        #print ("Mutation: slow LEFT turn every (",mutationfactor,") moves")
        self.AdjustSpeed(1)
        #swamp mix
        r = fast_rng.randint(MinBright,MaxBright)
        g = fast_rng.randint(MinBright,MaxBright)
        b = fast_rng.randint(MinBright,MaxBright)


      #slow turn right
      elif (mutationtype == 9):
        mutationfactor = fast_rng.randint(SlowTurnMinMoves,SlowTurnMaxMoves)  #higher is slower!
        #print ("Mutation: slow righ turn every (",mutationfactor,") moves")
        self.AdjustSpeed(1)
        #swamp mix
        r = fast_rng.randint(MinBright,MaxBright)
        g = fast_rng.randint(MinBright,MaxBright)
        b = fast_rng.randint(MinBright,MaxBright)


      #Clumping on
      elif (mutationtype == 10):
        self.clumping = True
        self.AdjustSpeed(mutationfactor)
        #Purple Haze
        r = fast_rng.randint(MinBright,MaxBright)
        g = 0
        b = 255

        
      #Update common properties
      self.r              = r
      self.g              = g
      self.b              = b
      if (self.name != 'Wall' and self.name != 'WallBreakable'):
        self.name           = "" + str(self.r) + ' -' + str(self.g)+ ' -' + str(self.b)
      self.mutationtype   = mutationtype
      self.mutationfactor = mutationfactor
      #print ("TheSpeed: ",self.speed)
    
    return;



  def IncreaseBrightness(self,increment):
      
    self.r = self.r + (255 / self.r * increment)
    self.g = self.g + (255 / self.g * increment)
    self.b = self.b + (255 / self.b * increment)
    
    if (self.r > 255):
      self.r = 255
    if (self.g > 255):
      self.g = 255
    if (self.b > 255):
      self.b = 255
    






        
def CreateSimpleObstacleMap(width, height, block_count=8, min_size=4, max_size=8, virus_count=10):
    
    global fast_rng

    #shading_gradient = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L']
    shading_gradient = ['L', 'K', 'J', 'I', 'H', 'G', 'F', 'E', 'D', 'C', 'B', 'A']

    hall = ' '
    border = '='

    grid = [[hall for _ in range(width)] for _ in range(height)]

    for _ in range(block_count):
        w = fast_rng.randint(min_size, max_size)
        h = fast_rng.randint(min_size, max_size)
        x = fast_rng.randint(1, width - w - 2)
        y = fast_rng.randint(1, height - h - 2)

        cx, cy = w / 2, h / 2
        max_dist = ((cx) ** 2 + (cy) ** 2) ** 0.5

        for dy in range(h):
            for dx in range(w):
                gx = x + dx
                gy = y + dy

                if (dx == 0 and dy == 0) or (dx == 0 and dy == h - 1) or (dx == w - 1 and dy == 0) or (dx == w - 1 and dy == h - 1):
                    continue  # rounded corner

                dist = ((dx - cx) ** 2 + (dy - cy) ** 2) ** 0.5
                shade_index = int((dist / max_dist) * (len(shading_gradient) - 1))
                grid[gy][gx] = shading_gradient[shade_index]

    # Borders
    for x in range(width):
        grid[0][x] = border
        grid[-1][x] = border
    for y in range(height):
        grid[y][0] = border
        grid[y][-1] = border

    # Viruses
    placed = 0
    tries = 0
    max_tries = 500
    while placed < virus_count and tries < max_tries:
        x = fast_rng.randint(2, width - 3)
        y = fast_rng.randint(2, height - 3)
        if grid[y][x] == hall:
            grid[y][x] = str((placed % 8) + 1)
            placed += 1
        tries += 1

    return [''.join(row) for row in grid]






def FlashAllViruses(Viruses,VirusCount,DinnerPlate,CameraH,CameraV):
  x = 0
  r = 0
  g = 0
  b = 0
  highcolor = 0
  count = 0
  increment = 50
  H = 0
  V = 0
  name = ""

  for x in range (0,VirusCount):
    highcolor = max(DinnerPlate.Viruses[x].r, DinnerPlate.Viruses[x].g, DinnerPlate.Viruses[x].b)
    while (DinnerPlate.Viruses[x].r < 255  and DinnerPlate.Viruses[x].g < 255 and DinnerPlate.Viruses[x].b < 255):
      if (DinnerPlate.Viruses[x].r == highcolor):
        DinnerPlate.Viruses[x].r = min(255,DinnerPlate.Viruses[x].r + increment)
      elif (DinnerPlate.Viruses[x].g == highcolor):
        DinnerPlate.Viruses[x].g = min(255,DinnerPlate.Viruses[x].g + increment)
      elif (DinnerPlate.Viruses[x].b == highcolor):
        DinnerPlate.Viruses[x].b = min(255,DinnerPlate.Viruses[x].b + increment)

      highcolor = highcolor + increment

      #setpixel(DinnerPlate.Viruses[x].h,DinnerPlate.Viruses[x].v,DinnerPlate.Viruses[x].r,DinnerPlate.Viruses[x].g,DinnerPlate.Viruses[x].b)
      #unicorn.show()
      #time.sleep(0.01)
      
    DinnerPlate.DisplayWindow(CameraH,CameraV)
    #unicorn.show()




def IsThereAVirusNearby_old(h,v,direction,VirusName,Playfield):
  # hv represent desired target location
  # ScanH and ScanV is where we are scanning
  
  #print ("== Scan in Front of Virus ==")
  
  ScanDirection = direction
  ScanH         = 0
  ScanV         = 0

#         7 1 2
#         6 x 3                              
#         5 z 4    x = proposed location, z = current location
  

  #Scan in front
  ScanH, ScanV = CalculateDotMovement8Way(h,v,ScanDirection)
  if (Playfield[ScanV][ScanH].name == VirusName):
    return 1;
  
  
  #Scan front right diagonal
  ScanDirection = TurnRight8Way(ScanDirection)
  ScanH, ScanV = CalculateDotMovement8Way(h,v,ScanDirection)
  if (Playfield[ScanV][ScanH].name == VirusName):
    return 1;
  
  #Scan right 
  ScanDirection = TurnRight8Way(ScanDirection)
  ScanH, ScanV = CalculateDotMovement8Way(h,v,ScanDirection)
  if (Playfield[ScanV][ScanH].name == VirusName):
    return 1;
  
  #Scan behind right diagonal
  ScanH, ScanV = CalculateDotMovement8Way(h,v,ScanDirection)
  if (Playfield[ScanV][ScanH].name == VirusName):
    return 1;
  
  #We don't Scan behind because that is where the virus is!
  ScanDirection = TurnRight8Way(ScanDirection)
  ScanH, ScanV = CalculateDotMovement8Way(h,v,ScanDirection)
  #if (Playfield[ScanV][ScanH].name == VirusName):
  #  return 1;


  #Scan behind left diagonal
  ScanH, ScanV = CalculateDotMovement8Way(h,v,ScanDirection)
  if (Playfield[ScanV][ScanH].name == VirusName):
    return 1;


  #Scan left
  ScanDirection = TurnRight8Way(TurnRight8Way(ScanDirection))
  ScanH, ScanV = CalculateDotMovement8Way(h,v,ScanDirection)
  if (Playfield[ScanV][ScanH].name == VirusName):
    return 1;

  #Scan front left diagonal
  ScanH, ScanV = CalculateDotMovement8Way(h,v,ScanDirection)
  if (Playfield[ScanV][ScanH].name == VirusName):
    return 1;











def VirusWorldScanAround_old(Virus,Playfield):
  # hv represent car location
  # ScanH and ScanV is where we are scanning
  
  #print ("== Scan in Front of Virus ==")
  
  ScanDirection = Virus.direction
  ScanH         = 0
  ScanV         = 0
  h             = Virus.h
  v             = Virus.v
  Item          = ''
  ItemList      = ['EmptyObject']
  count         = 0    #represents number of spaces to scan

#         2 1 3
#         5 x 6                              
#           4   
  
  #FlashDot2(h,v,0.005)

  #Scan in front
  ScanH, ScanV = LED.CalculateDotMovement8Way(h,v,Virus.direction)
  ItemList.append(Playfield[ScanV][ScanH].name)
  
  
  #Scan left diagonal
  ScanDirection = LED.TurnLeft8Way(Virus.direction)
  ScanH, ScanV = LED.CalculateDotMovement8Way(h,v,ScanDirection)
  ItemList.append(Playfield[ScanV][ScanH].name)
  
  #Scan right diagonal
  ScanDirection = LED.TurnRight8Way(Virus.direction)
  ScanH, ScanV = LED.CalculateDotMovement8Way(h,v,ScanDirection)
  ItemList.append(Playfield[ScanV][ScanH].name)
  
  #Scan behind
  ScanDirection = LED.ReverseDirection8Way(Virus.direction)
  ScanH, ScanV = LED.CalculateDotMovement8Way(h,v,ScanDirection)
  ItemList.append(Playfield[ScanV][ScanH].name)
  
  #Scan left
  ScanDirection = LED.TurnLeft8Way(LED.TurnLeft8Way(Virus.direction))
  ScanH, ScanV = LED.CalculateDotMovement8Way(h,v,ScanDirection)
  ItemList.append(Playfield[ScanV][ScanH].name)


  #Scan right
  ScanDirection = LED.TurnRight8Way(LED.TurnRight8Way(Virus.direction))
  ScanH, ScanV = LED.CalculateDotMovement8Way(h,v,ScanDirection)
  ItemList.append(Playfield[ScanV][ScanH].name)


  return ItemList;





def SafeGetName(Playfield, h, v):
    if 0 <= v < len(Playfield) and 0 <= h < len(Playfield[0]):
        return Playfield[v][h].name
    else:
        return 'OutOfBounds'



def VirusWorldScanAround(Virus, Playfield):
    h, v = Virus.h, Virus.v
    ItemList = ['EmptyObject']

    directions = [
        Virus.direction,
        LED.TurnLeft8Way(Virus.direction),
        LED.TurnRight8Way(Virus.direction),
        LED.ReverseDirection8Way(Virus.direction),
        LED.TurnLeft8Way(LED.TurnLeft8Way(Virus.direction)),
        LED.TurnRight8Way(LED.TurnRight8Way(Virus.direction))
    ]

    for dir in directions:
        ScanH, ScanV = LED.CalculateDotMovement8Way(h, v, dir)
        ItemList.append(SafeGetName(Playfield, ScanH, ScanV))

    return ItemList





def GetDistanceBetweenDots(h1,v1,h2,v2):
  a = abs(h1 - h2)
  b = abs(v1 - v2)
  c = math.sqrt(a**2 + b**2)

  return c;  



def IsThereAVirusNearby(ScanH, ScanV, direction, VirusName, Playfield):
    return 1 if SafeGetName(Playfield, ScanH, ScanV) == VirusName else 0


def IsThereAVirusNearby_old(h,v,direction,VirusName,Playfield):
  # hv represent desired target location
  # ScanH and ScanV is where we are scanning
  
  #print ("== Scan in Front of Virus ==")
  
  ScanDirection = direction
  ScanH         = 0
  ScanV         = 0

#         7 1 2
#         6 x 3                              
#         5 z 4    x = proposed location, z = current location
  

  #Scan in front
  ScanH, ScanV = LED.CalculateDotMovement8Way(h,v,ScanDirection)
  if (Playfield[ScanV][ScanH].name == VirusName):
    return 1;
  
  
  #Scan front right diagonal
  ScanDirection = LED.TurnRight8Way(ScanDirection)
  ScanH, ScanV = LED.CalculateDotMovement8Way(h,v,ScanDirection)
  if (Playfield[ScanV][ScanH].name == VirusName):
    return 1;
  
  #Scan right 
  ScanDirection = LED.TurnRight8Way(ScanDirection)
  ScanH, ScanV = LED.CalculateDotMovement8Way(h,v,ScanDirection)
  if (Playfield[ScanV][ScanH].name == VirusName):
    return 1;
  
  #Scan behind right diagonal
  ScanH, ScanV = LED.CalculateDotMovement8Way(h,v,ScanDirection)
  if (Playfield[ScanV][ScanH].name == VirusName):
    return 1;
  
  #We don't Scan behind because that is where the virus is!
  ScanDirection = LED.TurnRight8Way(ScanDirection)
  ScanH, ScanV = LED.CalculateDotMovement8Way(h,v,ScanDirection)
  #if (Playfield[ScanV][ScanH].name == VirusName):
  #  return 1;


  #Scan behind left diagonal
  ScanH, ScanV = LED.CalculateDotMovement8Way(h,v,ScanDirection)
  if (Playfield[ScanV][ScanH].name == VirusName):
    return 1;


  #Scan left
  ScanDirection = LED.TurnRight8Way(LED.TurnRight8Way(ScanDirection))
  ScanH, ScanV = LED.CalculateDotMovement8Way(h,v,ScanDirection)
  if (Playfield[ScanV][ScanH].name == VirusName):
    return 1;

  #Scan front left diagonal
  ScanH, ScanV = LED.CalculateDotMovement8Way(h,v,ScanDirection)
  if (Playfield[ScanV][ScanH].name == VirusName):
    return 1;





def CountNearbyViruses(h,v,direction,VirusName,Playfield):
  #this function returns the number of viruses nearby with the same name
  # hv represent current location
  # ScanH and ScanV is where we are scanning
  
  #print ("== Scan in Front of Virus ==")
  
  ScanDirection = direction
  ScanH         = 0
  ScanV         = 0
  count         = 0
  

#         7 1 2
#         6 x 3                              
#         5 z 4    x = proposed location, z = current location
  

  #Scan in front
  ScanH, ScanV = LED.CalculateDotMovement8Way(h,v,ScanDirection)
  if (Playfield[ScanV][ScanH].name == VirusName):
    count = count + 1
  
  
  #Scan front right diagonal
  ScanDirection = LED.TurnRight8Way(ScanDirection)
  ScanH, ScanV = LED.CalculateDotMovement8Way(h,v,ScanDirection)
  if (Playfield[ScanV][ScanH].name == VirusName):
    count = count + 1
  
  #Scan right 
  ScanDirection = LED.TurnRight8Way(ScanDirection)
  ScanH, ScanV = LED.CalculateDotMovement8Way(h,v,ScanDirection)
  if (Playfield[ScanV][ScanH].name == VirusName):
    count = count + 1
  
  #Scan behind right diagonal
  ScanH, ScanV = LED.CalculateDotMovement8Way(h,v,ScanDirection)
  if (Playfield[ScanV][ScanH].name == VirusName):
    count = count + 1
  
  #Scan behind
  ScanDirection = LED.TurnRight8Way(ScanDirection)
  ScanH, ScanV = LED.CalculateDotMovement8Way(h,v,ScanDirection)
  if (Playfield[ScanV][ScanH].name == VirusName):
    count = count + 1


  #Scan behind left diagonal
  ScanH, ScanV = LED.CalculateDotMovement8Way(h,v,ScanDirection)
  if (Playfield[ScanV][ScanH].name == VirusName):
    count = count + 1


  #Scan left
  ScanDirection = LED.TurnRight8Way(LED.TurnRight8Way(ScanDirection))
  ScanH, ScanV = LED.CalculateDotMovement8Way(h,v,ScanDirection)
  if (Playfield[ScanV][ScanH].name == VirusName):
    count = count + 1

  #Scan front left diagonal
  ScanH, ScanV = LED.CalculateDotMovement8Way(h,v,ScanDirection)
  if (Playfield[ScanV][ScanH].name == VirusName):
    count = count + 1

  return count;



def CountVirusesBehind(h,v,direction,VirusName,Playfield):
  #this function returns the number of viruses behind
  # hv represent current location
  # ScanH and ScanV is where we are scanning
  
  #print ("== Scan in Front of Virus ==")
  
  ScanDirection = direction
  ScanH         = 0
  ScanV         = 0
  count         = 0
  

#         . . .
#         . z .                              
#         1 2 3    z = current location
  

  #Scan behind left diagonal
  ScanDirection = LED.TurnLeft8Way(ScanDirection)
  ScanH, ScanV = LED.CalculateDotMovement8Way(h,v,ScanDirection)
  ScanDirection = LED.TurnLeft8Way(ScanDirection)
  ScanH, ScanV = LED.CalculateDotMovement8Way(h,v,ScanDirection)


  TheObject = GetPlayfieldObject(h=ScanH,v=ScanV,Playfield=Playfield)
  if (TheObject.name == VirusName):
    count = count + 1

  
  #Scan behind
  ScanDirection = LED.TurnLeft8Way(ScanDirection)
  ScanH, ScanV = LED.CalculateDotMovement8Way(h,v,ScanDirection)
  TheObject = GetPlayfieldObject(h=ScanH,v=ScanV,Playfield=Playfield)

  if (TheObject.name == VirusName):
    count = count + 1
  
  #Scan behind right diagonal
  ScanH, ScanV = LED.CalculateDotMovement8Way(h,v,ScanDirection)
  TheObject = GetPlayfieldObject(h=ScanH,v=ScanV,Playfield=Playfield)
  if (TheObject.name == VirusName):
    count = count + 1
  

  return count;







  

def SpreadInfection(Virus1,Virus2,direction):
  global ClumpingSpeed
  global ChanceOfSpeedup
  global InfectionChance
  global OriginalReplicationRate

  #print ("Spread Infection: ",Virus1.name, Virus2.name)
  
  #for some reason, my wall checks still let the odd wall slip past.  This will take care of it.
  if (Virus2.name == "WallBreakable"):
    #print ("Wallbreakable is immune from infections but does sustain damage",Virus2.lives)
    Virus2.lives = Virus2.lives -1
    Virus2.IncreaseBrightness(FoodBrightnessSteps)
           
    #Trying something new here.  When the virus is eating, we still want it to be active (speed) but just not moving
    #until the food is gone
    Virus1.eating = True
    Virus1.clumping = True
    Virus1.AdjustSpeed(EatingSpeedAdjustment)
    Virus1.replicationrate   = Virus1.replicationrate // 2   #floor division
    Virus1.mutationdeathrate = Virus1.mutationdeathrate + 1
   



    if (Virus2.lives <= 0):
      Virus2 = LED.EmptyObject
      Virus2.alive = 0
      #when virus finishes eating, it speeds up
      #Virus1.AdjustSpeed(-3)
      #if (Virus1.speed <= 1):
      #  Virus1.speed = 1
      
      #Done Eating?  Go faster little fella!
      Virus1.eating   = False
      Virus1.clumping = False
      Virus1.AdjustInfectionChance(-1)
      Virus1.AdjustSpeed(-3)
      Virus1.replicationrate = OriginalReplicationRate


  else:

    if(fast_rng.randint(1,InfectionChance) == 1):

      Virus2.name = Virus1.name
      Virus2.r    = Virus1.r   
      Virus2.g    = Virus1.g   
      Virus2.b    = Virus1.b   
      Virus2.direction      = direction
      Virus2.speed          = Virus1.speed
      Virus2.mutationtype   = Virus1.mutationtype
      Virus2.mutationrate   = Virus1.mutationrate
      Virus2.mutationfactor = Virus1.mutationfactor
      Virus2.eating         = Virus1.eating
      Virus2.clumping       = Virus1.clumping
      
      #Too slow.  Need another way to indicate mass infections spreading
      #if (LED.CheckBoundary(Virus2.h,Virus2.v) == 0):
      #  LED.FlashDot6(Virus2.h,Virus2.v)
      
      #Infected virus slows down, attempt to increase clumping
      #Virus2.AdjustSpeed(+ClumpingSpeed)
      
    
      

  
def ReplicateVirus(Virus,DinnerPlate):
  #global MaxReplications

  #         2 1 3
  #         5 x 6                              
  #           4   


  ItemList  = []
  h         = Virus.h
  v         = Virus.v
  ScanV     = 0
  ScanH     = 0
  direction = Virus.direction
  scandirection = 0


  if(Virus.replications <= MaxReplications):
    ItemList               = VirusWorldScanAround(Virus,DinnerPlate.Playfield)
  
    if (ItemList[5] == 'EmptyObject') or (ItemList[6] == 'EmptyObject'):
      VirusCopy              = copy.deepcopy(Virus)
      VirusCopy.replications +=1
      Virus.replications     +=1
    
      if (ItemList[5] == 'EmptyObject'):
        #print ("Open space to the left")
        scandirection  = LED.TurnLeft8Way(LED.TurnLeft8Way(direction))
        #print ("direction scandirection",direction,scandirection)

      elif (ItemList[6] == 'EmptyObject'):
        #print ("Open space to the right")
        scandirection = LED.TurnRight8Way(LED.TurnRight8Way(direction))


      ScanH,ScanV = LED.CalculateDotMovement8Way(h,v,scandirection)
      VirusCopy.v = ScanV
      VirusCopy.h = ScanH
      VirusCopy.AdjustSpeed(ReplicationSpeed)
      DinnerPlate.Playfield[ScanV][ScanH] = VirusCopy
      return VirusCopy; 
  
  return LED.EmptyObject;

  
def SetVirusPositionSafely(Virus, h, v, Playfield):
    if 0 <= v < len(Playfield) and 0 <= h < len(Playfield[0]):
        Virus.v = v
        Virus.h = h
        return True
    else:
        # Optional: log for debug
        # print(f"[Warning] Attempted to place virus out of bounds at ({v},{h})")
        return False  



def MoveVirus(Virus,Playfield):
  global VirusMoves
  global ChanceOfTurningIntoFood
  global fast_rng

  #print ("== MoveVirus : ",Virus.name," hv dh dv alive--",Virus.h,Virus.v,Virus.dh,Virus.dv,Virus.alive)
  
  #print ("")
  h = Virus.h
  v = Virus.v
  oldh  = h
  oldv  = v
  ScanH = 0
  ScanV = 0
  ItemList = []
  DoNothing = ""
  ScanDirection = 1
  WallInFront    = LED.EmptyObject
  VirusInFront   = LED.EmptyObject
  VirusInRear    = LED.EmptyObject
  VirusLeftDiag  = LED.EmptyObject
  VirusRightDiag = LED.EmptyObject
  
  #Infection / mutation modiefers
  #We need a random chance of mutation
  #  possibilities: 
  #  - mutate into another color
  #  - vastly increase/decrease speed
  #  - change direction
  #  - happens right before last move 
  
  InfectionSpeedModifier = -1
 
 

  #print("Current Virus vh direction:",v,h,Virus.direction)
  ItemList = VirusWorldScanAround(Virus,Playfield)
  #print (ItemList)
  
  

  #Grab breakable wall object
  if (ItemList[1] == "WallBreakable"):
    ScanH,ScanV = LED.CalculateDotMovement8Way(h,v,Virus.direction)
    WallInFront = GetPlayfieldObject(ScanH, ScanV, Playfield)


  #Grab potential viruses in scan zones NW N NE S
  #Grab Virus in front
  if (ItemList[1] != "Wall" and ItemList[1] != "WallBreakable" and ItemList[1] != 'EmptyObject' and ItemList[1] != 'OutOfBounds'):
    ScanH,ScanV = LED.CalculateDotMovement8Way(h,v,Virus.direction)
    VirusInFront = GetPlayfieldObject(ScanH, ScanV, Playfield)
    #print ("ScanFront    ",VirusInFront.name,VirusLeftDiag.name,VirusRightDiag.name,VirusInRear.name)

  #Grab Virus left diagonal
  if (ItemList[2] != "Wall" and ItemList[2] != "WallBreakable" and ItemList[2] != 'EmptyObject' and ItemList[2] != 'OutOfBounds'):
    ScanDirection = LED.TurnLeft8Way(Virus.direction)
    ScanH,ScanV = LED.CalculateDotMovement8Way(h,v,ScanDirection)
    VirusLeftDiag = GetPlayfieldObject(ScanH, ScanV, Playfield)
    #print ("ScanLeftDiag ",VirusInFront.name,VirusLeftDiag.name,VirusRightDiag.name,VirusInRear.name)

  #Grab Virus right diagonal
  if (ItemList[3] != "Wall" and ItemList[3] != "WallBreakable" and ItemList[3] != 'EmptyObject' and ItemList[3] != 'OutOfBounds'):
    ScanDirection = LED.TurnRight8Way(Virus.direction)
    ScanH,ScanV = LED.CalculateDotMovement8Way(h,v,ScanDirection)
    VirusRightDiag = GetPlayfieldObject(ScanH, ScanV, Playfield)
    #print ("ScanRightDiag",VirusInFront.name,VirusLeftDiag.name,VirusRightDiag.name,VirusInRear.name)
  
        
  if (ItemList[4] != "Wall" and ItemList[4] != "WallBreakable" and ItemList[4] != 'EmptyObject' and ItemList[4] != 'OutOfBounds'):
    ScanDirection = LED.ReverseDirection8Way(Virus.direction)
    ScanH,ScanV   = LED.CalculateDotMovement8Way(h,v,ScanDirection)
    VirusInRear     = GetPlayfieldObject(ScanH, ScanV, Playfield)
    #print ("ScanRear",VirusInFront.name,VirusLeftDiag.name,VirusRightDiag.name,VirusInRear.name)
  

  #Infect Virus
  #If different virus, take it over (test for chance)
  #else follow it


  #Add damage to breakable walls
  if (WallInFront.name == "WallBreakable"):
    #print ("Wall in front: ",WallInFront.name, WallInFront.lives)
    WallInFront.lives = WallInFront.lives -1
    Virus.eating = True
    WallInFront.IncreaseBrightness(FoodBrightnessSteps)
    if (WallInFront.lives <= 0):
      Playfield[WallInFront.v][WallInFront.h] = LED.EmptyObject


  #print ("Thing in front:",VirusInFront.name, WallInFront.name)
        
  #Check front Virus
  if (VirusInFront.name != 'EmptyObject' and VirusInFront.name != 'WallBreakable'):
    if (VirusInFront.name != Virus.name):
      SpreadInfection(Virus,VirusInFront,Virus.direction)
      #VirusInFront.AdjustSpeed(InfectionSpeedModifier)

  #Check left diagonal Virus
  if (VirusLeftDiag.name != 'EmptyObject'):
    if (VirusLeftDiag.name != Virus.name):
      SpreadInfection(Virus,VirusLeftDiag,(LED.TurnLeft8Way(Virus.direction)))


  #Check right diagonal Virus
  if (VirusRightDiag.name != 'EmptyObject'):
    if (VirusRightDiag.name != Virus.name):
      SpreadInfection(Virus,VirusRightDiag,(LED.TurnRight8Way(Virus.direction)))


  #Check rear Virus
  if (VirusInRear.name != 'EmptyObject'):
    #If different virus, take it over 
    #make it follow
    if (VirusInRear.name != Virus.name):
      SpreadInfection(Virus,VirusInRear,Virus.direction)


  #We follow other virus of the same name
  if (VirusInFront.name == Virus.name):
    Virus.direction = VirusInFront.direction
  elif (VirusLeftDiag.name == Virus.name):
    Virus.direction = VirusLeftDiag.direction
  elif (VirusRightDiag.name == Virus.name):
    Virus.direction = VirusRightDiag.direction
  elif (VirusInRear.name == Virus.name):
    Virus.direction = VirusInRear.direction


  #If no viruses around, increase speed and wander around
  if (all('EmptyObject' == Item for Item in ItemList)):
    if (fast_rng.randint(1,ChanceOfSpeedup) == 1):
      Virus.AdjustSpeed(-1)
  

  #print ("Viruss: ",Virus.name, VirusInFront.name, VirusLeftDiag.name, VirusRightDiag.name, VirusInRear.name)

  
  #If no viruses around, check for walls
  if (all('EmptyObject' == name for name in (VirusInFront.name, VirusLeftDiag.name, VirusRightDiag.name, VirusInRear.name))):
    

    if (ItemList[1] == "WallBreakable"):
      Virus.direction = LED.TurnLeftOrRight8Way(Virus.direction)


    elif((ItemList[1] == "Wall" or ItemList[1] == "WallBreakable") 
      and ItemList[2] == 'EmptyObject' 
      and ItemList[3] == 'EmptyObject'):
      Virus.direction = LED.TurnLeftOrRight8Way(Virus.direction)

    elif((ItemList[1] == "Wall" or ItemList[1] == "WallBreakable") 
      and(ItemList[2] == "Wall" or ItemList[2] == "WallBreakable") 
      and ItemList[3] == 'EmptyObject'):
      Virus.direction = LED.TurnRight8Way(Virus.direction)

    elif((ItemList[1] == "Wall" or ItemList[1] == "WallBreakable")
      and ItemList[2] == 'EmptyObject' 
      and(ItemList[3] == "Wall" or ItemList[3] == "WallBreakable")):
      Virus.direction = LED.TurnLeft8Way(Virus.direction)

    elif((ItemList[1] == "Wall" or ItemList[1] == "WallBreakable")
     and (ItemList[2] == "Wall" or ItemList[2] == "WallBreakable")
     and (ItemList[3] == "Wall" or ItemList[3] == "WallBreakable")):
      Virus.direction = LED.TurnLeftOrRightTwice8Way(LED.ReverseDirection8Way(Virus.direction))
 

  #-----------------------------------------
  #-- Mutations                           --
  #-----------------------------------------

  #Mutate virus
  #print ("MV - mutationrate type factor",Virus.mutationrate, Virus.mutationtype, Virus.mutationfactor)
  if (fast_rng.randint(0,Virus.mutationrate) == 1):
    Virus.Mutate()

    if (Virus.alive == 0):
      #print ("Accident during mutation. Virus died!")
      Virus.lives = 0
      Virus.speed = 1
      Virus.mutationtype   = 0
      Virus.mutationfactor = 0
      Playfield[Virus.v][Virus.h] = LED.EmptyObject


    #If after a mutation the virus dies, there is a small chance to turn into food or a wall
    if (fast_rng.randint(0,ChanceOfTurningIntoFood) == 1):
      Playfield[Virus.v][Virus.h] = LED.Wall(Virus.h,Virus.v,LED.SDDarkWhiteR,LED.SDDarkWhiteG,(LED.SDDarkWhiteB + 60),1,VirusFoodWallLives,'WallBreakable')
    elif (fast_rng.randint(0,ChanceOfTurningIntoWall) == 1):
      Playfield[Virus.v][Virus.h] = LED.Wall(Virus.h,Virus.v,LED.SDDarkWhiteR,LED.SDDarkWhiteG,LED.SDDarkWhiteB,1,VirusFoodWallLives,'Wall')
    else:
      Playfield[Virus.v][Virus.h] = LED.EmptyObject




  #apply directional mutations
  if (Virus.mutationtype in (1,2,8)):
    m,r = divmod(VirusMoves,Virus.mutationfactor)
    if (r == 0):
      Virus.direction = LED.TurnLeft8Way(Virus.direction)

  elif(Virus.mutationtype in (3,4,9)):
    m,r = divmod(VirusMoves,Virus.mutationfactor)
    if (r == 0):
      Virus.direction = LED.TurnRight8Way(Virus.direction)
  
  elif(Virus.mutationtype == 7):
    m,r = divmod(VirusMoves,Virus.mutationfactor)
    if (r == 0):
      Virus.direction = LED.TurnRight8Way(Virus.direction)
      LED.TurnLeftOrRight8Way(Virus.direction)




  #A virus can be in eating mode, but another virus eats the food.  The first virus will stay in eating mode
  #as a work around, we will randomly tell the virus to stop eating
  if (fast_rng.randint(1,ChanceToStopEating) == 1):
    Virus.eating = False


  if (Virus.alive == 1 and Virus.eating == False):  

    #Only move if the space decided upon is actually empty!
    ScanH,ScanV = LED.CalculateDotMovement8Way(h,v,Virus.direction)
    
    TargetObject = GetPlayfieldObject(ScanH,ScanV,Playfield)
    
    if (TargetObject.name == 'EmptyObject'):
      #print("target object:",TargetObject.name)
      #print ("Spot moving to is empty ScanV ScanH",ScanV,ScanH)
      #print ("Virus direction:",Virus.direction)
      

      #If virus is in clumping mode, only move if the target space is bordering on a virus of the same name
      #If clumping mode but no nearby viruses, let the little fella keep going
      if (Virus.clumping == True):
        if (IsThereAVirusNearby(ScanH, ScanV, Virus.direction,Virus.name,Playfield) == 1):
          Virus.h = ScanH
          Virus.v = ScanV
          Playfield[ScanV][ScanH] = Virus
          Playfield[oldv][oldh] = LED.EmptyObject

        elif(CountVirusesBehind(Virus.h, Virus.v, Virus.direction,Virus.name,Playfield) == 0):
          if(SetVirusPositionSafely(Virus,ScanH,ScanV,Playfield)):
            Playfield[ScanV][ScanH] = Virus
            Playfield[oldv][oldh] = LED.EmptyObject

      else:
        if(SetVirusPositionSafely(Virus,ScanH,ScanV,Playfield)):
          Playfield[ScanV][ScanH] = Virus
          Playfield[oldv][oldh] = LED.EmptyObject



    else:
      #print ("spot moving to is not empty: ",Playfield[ScanV][ScanH].name, ScanV,ScanH)
      #Introduce some instability into the virus
      if (fast_rng.randint(0,InstabilityFactor) == 1):
        Virus.direction = LED.TurnLeftOrRight8Way(Virus.direction)
        Virus.AdjustSpeed(fast_rng.randint(-1,1))



  return 



def GenerateEmptyMapWithBorder(width, height, wall_char='-', fill_char=' '):
    """
    Generates a map with a solid border of walls.

    Parameters:
        width (int): Total width of the map including borders.
        height (int): Total height of the map including borders.
        wall_char (str): Character to use for the border (typically a wall).
        fill_char (str): Character to fill the inner area (typically empty space).

    Returns:
        list[str]: A list of strings representing the map with walls.
    """
    if len(wall_char) != 1 or len(fill_char) != 1:
        raise ValueError("wall_char and fill_char must be single characters.")
    if width < 3 or height < 3:
        raise ValueError("Minimum size for bordered map is 3x3.")

    map_rows = []
    for y in range(height):
        if y == 0 or y == height - 1:
            map_rows.append(wall_char * width)
        else:
            map_rows.append(wall_char + (fill_char * (width - 2)) + wall_char)
    return map_rows



def CreateDinnerPlate_old(MapLevel):
  global mutationrate
  
  

  print ("CreateDinnerPlate Map: ",MapLevel)


  TheMap = LED.TextMap(
    h      = 1,
    v      = 1,
    width  = 66, 
    height = 34
    )
  
  TheMap.ColorList = {
    ' ' : (0  ,0  ,0),
    '-' : ( 0 , 0 , 0),
    '.' : ( 5 , 5 , 5),
    'o' : (25 ,25 ,25),
    'O' : (65 ,65 ,65),
    '@' : (95 ,95 ,95),
    '#' : (125,125,125),
    '*' : (  5,  5,  5),
    '1' : (0  ,150,  0),
    '2' : (150,  0,  0),
    '3' : (150,100,  0),
    '4' : (  0,  0,100),
    '5' : (200,  0, 50),
    '6' : (125,185,  0),
    '7' : (200,  0,200),
    '8' : ( 50,150, 75)
  }

  TheMap.TypeList = {
    ' ' : 'EmptyObject',
    '-' : 'wall',
    '.' : 'wall',
    'o' : 'wall',
    'O' : 'wall',
    '@' : 'wall',
    '#' : 'wall',
    '*' : 'wallbreakable',
    '1' : 'virus',
    '2' : 'virus',
    '3' : 'virus',
    '4' : 'virus',
    '5' : 'virus',
    '6' : 'virus',
    '7' : 'virus',
    '8' : 'virus'
  }




  if (MapLevel == 1):
    
    DinnerPlate = VirusWorld(name='TheCave',
                               width        = 66, #we want the playfield to be 1 pixel larger on all sides than the display
                               height       = 34,
                               Map          = [[]],
                               Playfield    = [[]],
                               CurrentRoomH = 1,
                               CurrentRoomV = 1,
                               DisplayH     = 1,
                               DisplayV     = 1,
                               mutationrate = mutationrate,
                               replicationrate = replicationrate,
                               mutationdeathrate = mutationdeathrate,
                               VirusStartSpeed = VirusStartSpeed)

    #Change food to blue for this map
    TheMap.ColorList['*']  =  (0,0,20)

    TheMap.map= (
      #0         1  .......2.........3.........4.........5.........6....65    
      "OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO", #0  
      "O            -ooo.***********************************************O",
      "O            -OOo.****..*****************************************O",
      "O            -@Oo.****..ooo**ooooooo*****************************O",
      "O            -3Oo.****..oooo**OOOOOooooo*************************O",
      "O            -OOo.***...oOOOO*****OOOOOooooo*********************O",
      "O            -ooo***....oO3333********OOOOOooooo*****************O",
      "O            -....**....oO3333            OOOOOooooo*************O",
      "O            -******.ooooO3333   111          OOOOOooooo***..... O", 
      "O            -*****..oOOOO       111              OOOOOoooo..... O", 
      "O            -***....oO          111                  OOOOo..... O", #10
      "O            - . ....oO          11           2          Oo......O",
      "O            - . ....oO          11     **    2          Oo......O",
      "O            - ......oOOOO       1    ******  2          Oo......O",
      "O            - ......ooooO          ********* 22222222   Oo......O",
      "O            -    ......oO        ******@*****22222222   Oo......O",
      "O            -      ....oO     ********@@*****2          Oo......O",
      "O            -     .....oO3333*********##******          Oo......O",    
      "O            -    ......oO3333********OOO********        Oo..... O",
      "O            -   .......oO3333*******OOOO*********    OOOOo..... O", 
      "O            -    ......oOOOOOO*****ooooo*********OOOOOoooo....  O", #20
      "O            -     .....ooooooO*****ooooo*****OOOOOooooooo.....  O",
      "O            -      ........ooO ***...... OOOOOooooooooo......   O",
      "O            -       ........oOOOO.......OOoooooooooo........    O",
      "O            -          ......oooo.......oo...............       O",
      "O            -            ..........................             O",
      "O            -               ..................                  O",
      "O            -                ...............                    O",
      "O            -                                                   O",
      "O            --------------------------                          O",
      "O                                     -                          O", #30
      "O                                     -                          O",
      "O                                     -                          O",
      "OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO"  #33
    )








  if (MapLevel == 2):
    
    DinnerPlate = VirusWorld(name='TheCave2',
                               width        = 66, #we want the playfield to be 1 pixel larger on all sides than the display
                               height       = 34,
                               Map          = [[]],
                               Playfield    = [[]],
                               CurrentRoomH = 1,
                               CurrentRoomV = 1,
                               DisplayH     = 1,
                               DisplayV     = 1,
                               mutationrate = mutationrate,
                               replicationrate = replicationrate,
                               mutationdeathrate = mutationdeathrate,
                               VirusStartSpeed = VirusStartSpeed)



  # TheMap.map= (
    # #0         1  .......2.........3.........4.........5.........6....65    
    # "OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO", #0  
    # "O                                                                O",
    # "O                                                                O",
    # "O                                                                O",
    # "O                                                                O",
    # "O                                                                O",
    # "O                                                                O",
    # "O                                                                O",
    # "O                                                                O", 
    # "O                                                                O", 
    # "O                                                                O", #10
    # "O                                                                O",
    # "O                                                                O",
    # "O                                                                O",
    # "O                                                                O",
    # "O                                                                O",
    # "O                                                                O",
    # "O                                                                O",    
    # "O                                                                O",
    # "O                                                                O", 
    # "O                                                                O", #20
    # "O                                                                O",
    # "O                                                                O",
    # "O                                                                O",
    # "O                                                                O",
    # "O                                                                O",
    # "O                                                                O",
    # "O                                                                O",
    # "O                                                                O",
    # "O                                                                O",
    # "O                                                                O", #30
    # "O                                                                O",
    # "O                                                                O",
    # "OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO"  #33
  # )

    TheMap.ColorList['*']  =  (0,0,20)

    TheMap.map= (
      #0         1  .......2.........3.........4.........5.........6....65    
      "OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO", #0  
      "O            ....................................................O",
      "O            ..........................oooooo....................O",
      "O            .....oooooo..............oOOOOOOoo..................O",
      "O            ....oOOOOOOo............oOO22222OOoo................O",
      "O            ..ooO1*****Oo...........oO********OOoo..............O",
      "O            ..oO11*****OooooooooooooOO*********3OOo.............O",
      "O            ..oO1*******************************3Oo.............O",
      "O            ...oO1*****OooooooooooO*************3Oo.............O",
      "O            ....oO**OOOo.........oO*************3Oo.............O",
      "O            .....o**ooo...........oO444*********3Oo.............O", #10
      "O            ......**..............oO444*********3Oo.............O",
      "O            ......**...............oOOOO*******3Oo..............O",
      "O            ..oooo**oo..............ooooOOO**OOOo...............O",
      "O            .ooOOO**OOo.................ooO**Ooo................O",
      "O            ooO555**55Oo.................oO**Oo.....ooooo.......O",
      "O            oO5555*****Oo................oO**Oo....oOOOOOo......O",
      "O            oO555*******Oo...............oO**Oo...oO*****Ooo....O",
      "O            oO55********Oo...............oO**Oo..oO*******OOo...O",
      "O            oO55********Oo...............oO**Oo.oO*********Oo...O",
      "O            oO**********Oo...............oO**Oo.oO*********Oo...O", #20
      "O            .oO**********Oo.........oooooOO**Oo.oO*********Oo...O",
      "O            ..oO***6******Oo....ooooOOOOOOO**OoooO*********Oo...O",
      "O            ...oOOO6*******OooooOOOOO**********************Oo...O",
      "O            ....oooO6*******OOOOO**************************Oo...O",
      "O            .......oO66************************************Oo...O",
      "O            ........oO666666*****************************88Oo...O",
      "O            .........oOOOOOO***************************888OOo...O",
      "O            ..........ooooooOO**********************8888OOoo....O",
      "O            ................ooO777777777777**88888888OOOoo......O",
      "O            ..................oOOOOOOOOOOOOOOOOOOOOOOOoo........O", #30
      "O            ...................ooooooooooooooooooooooo..........O",
      "O            ....................................................O",
      "OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO"  #33
    )



  if (MapLevel == 3):
    
    DinnerPlate = VirusWorld(name='BigFood',
                               width        = 66, #we want the playfield to be 1 pixel larger on all sides than the display
                               height       = 34,
                               Map          = [[]],
                               Playfield    = [[]],
                               CurrentRoomH = 1,
                               CurrentRoomV = 1,
                               DisplayH     = 1,
                               DisplayV     = 1,
                               mutationrate = mutationrate,
                               replicationrate = replicationrate,
                               mutationdeathrate = mutationdeathrate,
                               VirusStartSpeed = VirusStartSpeed)



    TheMap.ColorList['*']  =  (25,0,0)

    TheMap.map= (
      #0         1   ......2.........3.........4.........5.........6....65    
      "OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO", #0  
      "O            --                                                  O",
      "O            --                                                  O",
      "O            --                                  ...             O",
      "O            --                   *           ....o....          O",
      "O            --                  *.*          ..ooOoo..          O",
      "O            --                 *.o.*        ...oO@Oo...         O",
      "O            --               *..ooo..*      ..oO@#@Oo..         O",
      "O            --              *..ooooo...*    ...oO@Oo...         O", 
      "O            --             *.ooooooooo.*     ..ooOoo..          O", 
      "O            --             *.oOOOOOOOo.*     ....o....          O", #10
      "O            --             *.oO@@@@@Oo.*        ...             O",
      "O            --             *.ooooooooo.*                        O",
      "O            --             *************                        O",
      "O            --             *.ooooooooo.*          8             O",
      "O            --             *.oO@@@@@Oo.*         8.8            O",
      "O            --             *.oOOOOOOOo.*        8ooo8           O",
      "O            --             *.ooooooooo.*       8OOOOO8          O",    
      "O            --             *...ooooo...*      8@@@@@@@8         O",
      "O            --               *..ooo..*       8#########8        O", 
      "O            --                 *.o.*          8@@@@@@@8         O", #20
      "O            --                  *.*            8OOOOO8          O",
      "O            --              ...  *              8ooo8           O",
      "O            --             .ooo.                 8.8            O",
      "O            --            .oOOOo.                 8             O",
      "O            --           .oO@@@Oo.                              O",
      "O            --          .oO@###@Oo.                             O",
      "O            --           .oO@@@Oo.                              O",
      "O            --            .oOOOo.                               O",
      "O            --             .ooo.                                O",
      "O            --              ...                                 O", #30
      "O            --                                                  O",
      "O                                                                O",
      "OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO"  #33
    )





  if (MapLevel == 4):
    
    DinnerPlate = VirusWorld(name='BigFood',
                               width        = 66, #we want the playfield to be 1 pixel larger on all sides than the display
                               height       = 34,
                               Map          = [[]],
                               Playfield    = [[]],
                               CurrentRoomH = 1,
                               CurrentRoomV = 1,
                               DisplayH     = 1,
                               DisplayV     = 1,
                               mutationrate = mutationrate,
                               replicationrate = replicationrate,
                               mutationdeathrate = mutationdeathrate,
                               VirusStartSpeed = VirusStartSpeed)

    DinnerPlate.walllives = fast_rng.randint(1,25) 
    TheMap.ColorList['*']  =  (5,5,5)
    TheMap.ColorList['.']  =  (15,15,15)

    TheMap.map= (
      #0         1   ......2.........3.........4.........5.........6....65    
      "OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO", #0  
      "O            --**************************************************O",
      "O            --**************************************************O",
      "O            --**********************....************************O",
      "O            --**********************....************************O",
      "O            --**********************....************************O",
      "O            --**********************....************************O",
      "O            --**********************....************************O",
      "O            --****************................******************O",
      "O            --****************................******************O",
      "O            --****************................******************O", #10
      "O            --****************................******************O",
      "O            --**********************....************************O",
      "O            --**********************....************************O",
      "O            --**********************....************************O",
      "O            --**********************....************************O",
      "O            --**********************....************************O",
      "O            --**********************....************************O",
      "O            --**********************....************************O",
      "O            --**********************....************************O",
      "O            --**********************....************************O", #20
      "O            --**********************....************************O",
      "O            --**********************....************************O",
      "O            --**********************....************************O",
      "O            --**********************....************************O",
      "O            --**********************....************************O",
      "O            --**********************....************************O",
      "O            --**************************************************O",
      "O            --**************************************************O",
      "O            --**************************************************O",
      "O            --**************************************************O", #30
      "O            --**************************************************O",
      "O            --**************************************************O",
      "OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO"  #33
    )

  

  
  if (MapLevel == 5):
    
    DinnerPlate = VirusWorld(name='BigFood',
                               width        = 66, #we want the playfield to be 1 pixel larger on all sides than the display
                               height       = 34,
                               Map          = [[]],
                               Playfield    = [[]],
                               CurrentRoomH = 1,
                               CurrentRoomV = 1,
                               DisplayH     = 1,
                               DisplayV     = 1,
                               mutationrate = mutationrate,
                               replicationrate = replicationrate,
                               mutationdeathrate = mutationdeathrate,
                               VirusStartSpeed = VirusStartSpeed)

    DinnerPlate.walllives = fast_rng.randint(1,25) 
    TheMap.ColorList['.']  =  (0,10,0)
    TheMap.ColorList['*']  =  (0,10,0)

    TheMap.map= (
      #0         1   ......2.........3.........4.........5.........6....65    
      "OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO", #0  
      "O            --**************************************************O",
      "O            --**************************************************O",
      "O            --**************************************************O",
      "O            --**************************************************O",
      "O            --**************************************************O",
      "O            --**************************************************O",
      "O            --**************************************************O",
      "O            --**************************************************O",
      "O            --**************************************************O",
      "O            --**************************************************O", #10
      "O            --**************************************************O",
      "O            --**************************************.***********O",
      "O            --*************************************...**********O",
      "O            --************************************.....*********O",
      "O            --***********************************.......********O",
      "O            --*****************.****************.........*******O",
      "O            --****************...**************...........******O",
      "O            --***************.....************.............*****O",
      "O            --**************.......**********...............****O",
      "O            --*************.........********.................***O", #20
      "O            --************...........******...................**O",
      "O            --***********.............****.....................*O",
      "O            --**********...............**.......................O",
      "O            --*********.........................................O",
      "O            --********..........................................O",
      "O            --*******...........................................O",
      "O            --**************************************************O",
      "O            --**************************************************O",
      "O            --**************************************************O",
      "O            --**************************************************O", #30
      "O            --**************************************************O",
      "O            --**************************************************O",
      "OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO"  #33
    )


  if (MapLevel == 6):
    DinnerPlate = VirusWorld(name='BigFood',
                               width        = 66, #we want the playfield to be 1 pixel larger on all sides than the display
                               height       = 34,
                               Map          = [[]],
                               Playfield    = [[]],
                               CurrentRoomH = 1,
                               CurrentRoomV = 1,
                               DisplayH     = 1,
                               DisplayV     = 1,
                               mutationrate = mutationrate,
                               replicationrate = replicationrate,
                               mutationdeathrate = mutationdeathrate,
                               VirusStartSpeed = VirusStartSpeed)

    DinnerPlate.walllives = fast_rng.randint(1,25) 
    TheMap.ColorList['*']  =  (0,15,0)

    TheMap.map= (
      #0         1   ......2.........3.........4.........5.........6....65    
      "OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO", #0  
      "O            --**************************************************O",
      "O            --**************************************************O",
      "O            --**************************************************O",
      "O            --********************************.oO***************O",
      "O            --********************O***********.oO****........***O",
      "O            --*******************OoO**********.oO****.ooooooo***O",
      "O            --******************Oo.oO*********.oO****.oOOOOOO***O",
      "O            --*****************Oo.3.oO********.oO****.oO********O",
      "O            --****************Oo.333.oO*******.oO****.oO********O",
      "O            --***************Oo.33333.oO******.oO****.oO********O", #10
      "O            --**************Oo.........oO*****.oO****.oO********O",
      "O            --*************OoooooooooooooO****.oO****.oO********O",
      "O            --************OOOOOOOOOOOOOOOO****.oO***************O",
      "O            --********************************.oO***************O",
      "O            --********************************.oO***************O",
      "O            --*****************OOO************.oO***************O",
      "O            --****************Oo..************.oO*****.oO*******O",
      "O            --***************Oo..*************.oO*****.oO*******O",
      "O            --**************Oo..**************.oO*****.oO*******O",
      "O            --*************Oo..................oO*****.oO*******O", #20
      "O            --*************OooooooooooooooooooooO*****.oO*******O",
      "O            --**************OOOOOOOOOOOOOOOOOOOOO*****.oO*******O",
      "O            --****************************************.oO*******O",
      "O            --****************************************.oO*******O",
      "O            --******************************Oo.*******.oO*******O",
      "O            --******************************Oo.........oO*******O",
      "O            --******************************OoooooooooooO*******O",
      "O            --******************************OOOOOOOOOOOOO*******O",
      "O            --**************************************************O",
      "O            --**************************************************O", #30
      "O            --**************************************************O",
      "O            --**************************************************O",
      "OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO"  #33
    )



  if (MapLevel == 7):
    DinnerPlate = VirusWorld(name='BigFood',
                               width        = 66, #we want the playfield to be 1 pixel larger on all sides than the display
                               height       = 34,
                               Map          = [[]],
                               Playfield    = [[]],
                               CurrentRoomH = 1,
                               CurrentRoomV = 1,
                               DisplayH     = 1,
                               DisplayV     = 1,
                               mutationrate = mutationrate,
                               replicationrate = replicationrate,
                               mutationdeathrate = mutationdeathrate,
                               VirusStartSpeed = VirusStartSpeed)

    DinnerPlate.walllives = fast_rng.randint(1,25) 
    TheMap.ColorList['*']  =  (10,0,10)

    TheMap.map= (
      #0         1   ......2.........3.........4.........5.........6....65    
      "OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO", #0  
      "O            --**************************************************O",
      "O            --*******OOOOOOOOOOOOOO*********OOOOOOOOOOOOOOOOO***O",
      "O            --******oOooooooooooooO********oOoooooooooooooooO***O",
      "O            --*****.oO...........oOOOOOOOOOOO..............oO***O",
      "O            --*****.oO**********.ooooooooooo**************.oO***O",
      "O            --*****.oO**********...........***************.oO***O",
      "O            --*****.oO************************************.oO***O",
      "O            --*****.oO************************************.oO***O",
      "O            --*****.oO**************OOOOOOOOO*************.oO***O",
      "O            --*****.oO*************oOoooooooO*************.oO***O", #10
      "O            --*****.oO************.oO......oO*************.oO***O",
      "O            --*****.oO************.oO*****.oOOOOOOOOOOOOOOOOO***O",
      "O            --*****.oO************.oO*****.ooooooooooooooooo****O",
      "O            --*****.oO************.oO*****.................*****O",
      "O            --*****.oO************.oO***************************O",
      "O            --*****.oO************.oO***************************O",
      "O            --*****.oOOOOO***OOOOOOOO***************************O",
      "O            --*****.ooooo***oooooooo****************************O",
      "O            --*****.....***........*****************************O",
      "O            --**************************************************O", #20
      "O            --**************************************************O",
      "O            --*****************************OOOO**OOOO***********O",
      "O            --****************************oOoo**ooooO***********O",
      "O            --***************************.oO.**....oO***********O",
      "O            --***************************.oO******.oO***********O",
      "O            --***************************.oOOOOOOOOOO***********O",
      "O            --***************************.oooooooooo************O",
      "O            --***************************..........*************O",
      "O            --**************************************************O",
      "O            --**************************************************O", #30
      "O            --**************************************************O",
      "O            --**************************************************O",
      "OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO"  #33
    )

  if (MapLevel == 8):
    DinnerPlate = VirusWorld(name='BigFood',
                               width        = 66, #we want the playfield to be 1 pixel larger on all sides than the display
                               height       = 34,
                               Map          = [[]],
                               Playfield    = [[]],
                               CurrentRoomH = 1,
                               CurrentRoomV = 1,
                               DisplayH     = 1,
                               DisplayV     = 1,
                               mutationrate = mutationrate,
                               replicationrate = replicationrate,
                               mutationdeathrate = mutationdeathrate,
                               VirusStartSpeed = VirusStartSpeed)

    DinnerPlate.walllives = fast_rng.randint(1,25) 
    TheMap.ColorList['*']  =  (15,0,0)

    TheMap.map= (
      #0         1   ......2.........3.........4.........5.........6....65    
      "OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO", #0  
      "O            --**************************************************O",
      "O            --**************************************************O",
      "O            --**************************************************O",
      "O            --**************************************************O",
      "O            --**************************************************O",
      "O            --**************************************************O",
      "O            --**************************************************O",
      "O            --**************************************************O",
      "O            --**************************************************O",
      "O            --**************************************************O", #10
      "O            --**************************************************O",
      "O            --**************************************************O",
      "O            --**************************************************O",
      "O            --**************************************************O",
      "O            --**************************************************O",
      "O            --**************************************************O",
      "O            --**************************************************O",
      "O            --**************************************************O",
      "O            --**************************************************O",
      "O            --**************************************************O", #20
      "O            --**************************************************O",
      "O            --**************************************************O",
      "O            --**************************************************O",
      "O            --**************************************************O",
      "O            --**************************************************O",
      "O            --**************************************************O",
      "O            --**************************************************O",
      "O            --**************************************************O",
      "O            --**************************************************O",
      "O            --**************************************************O", #30
      "O            --**************************************************O",
      "O            --**************************************************O",
      "OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO"  #33
    )




  if (MapLevel == 9):
    
    DinnerPlate = VirusWorld(name='BigFood',
                               width        = 66, #we want the playfield to be 1 pixel larger on all sides than the display
                               height       = 34,
                               Map          = [[]],
                               Playfield    = [[]],
                               CurrentRoomH = 1,
                               CurrentRoomV = 1,
                               DisplayH     = 1,
                               DisplayV     = 1,
                               mutationrate = mutationrate,
                               replicationrate = replicationrate,
                               mutationdeathrate = mutationdeathrate,
                               VirusStartSpeed = VirusStartSpeed)


    TheMap.ColorList = {
      ' ' : (  0,  0,  0),
      '-' : ( 10, 10, 10),  
      '.' : ( 20, 20, 20),
      'o' : ( 30, 30, 30),
      'O' : ( 40, 40, 40),
      '@' : ( 50, 60, 60),
      '$' : ( 60, 60, 60),
      'A' : ( 70, 70, 70),
      'B' : ( 80, 80, 80),
      'C' : ( 90, 90, 90),
      'D' : (100,100,100),
      'E' : (110,110,110),
      'F' : (120,120,120),
      'G' : (130,130,130),
      'H' : (140,140,140),
      'I' : (150,150,150),
      'J' : (160,160,160),
      'K' : (170,170,170),
      'L' : (180,180,180),
      '|' : (  0,  0,  0),
      '*' : (  5,  5,  5),
      '1' : (0  ,150,  0),
      '2' : (150,  0,  0),
      '3' : (150,100,  0),
      '4' : (  0,  0,100),
      '5' : (200,  0, 50),
      '6' : (125,185,  0),
      '7' : (200,  0,200),
      '8' : ( 50,150, 75)
    }

    TheMap.TypeList = {
      ' ' : 'EmptyObject',
      '-' : 'wall',
      '.' : 'wall',
      'o' : 'wall',
      'O' : 'wall',
      '@' : 'wall',
      '#' : 'wall',
      '$' : 'wall',
      '#' : 'wall',
      '*' : 'wallbreakable',
      'A' : 'wall',
      'B' : 'wall',
      'C' : 'wall',
      'D' : 'wall',
      'E' : 'wall',
      'F' : 'wall',
      'G' : 'wall',
      'H' : 'wall',
      'I' : 'wallbreakable',
      'J' : 'wallbreakable',
      'K' : 'wallbreakable',
      'L' : 'wallbreakable',
      '|' : 'wall',
      '1' : 'virus',
      '2' : 'virus',
      '3' : 'virus',
      '4' : 'virus',
      '5' : 'virus',
      '6' : 'virus',
      '7' : 'virus',
      '8' : 'virus'
    }


    TheMap.map= (
      #0         1   ......2.........3.........4.........5.........6....65    
      "OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO", #0  
      "O            |                                                   O",
      "O            |   111                                   333       O",
      "O            |   111                                   333       O",
      "O            |   111                                   333       O",
      "O            |                                                   O",
      "O            |                                                   O",
      "O            |                                                   O",
      "O            |                                                   O", 
      "O            |                   FGHIJ   JIHF                    O", 
      "O            |                  EFGHIJ   JIHFE                   O", #10
      "O            |                 DEFGHIJ   JIHFEFE                 O",
      "O            |                CDEFGHIJ   JIHGFEDC                O",
      "O            |        -.oO@$ABCDEFG         GFEDCBA$@Oo.-        O",
      "O            |        -.oO@$ABCDEFG IJKLKJI GFEDCBA$@Oo.-        O",
      "O            |        -.oO@$ABCDEFG IJKLKJI GFEDCBA$@Oo.-        O",
      "O            |        -.oO@$ABCDEFG I88888I GFEDCBA$@Oo.-        O",
      "O            |        -.oO@$ABCDEFG I88888I GFEDCBA$@Oo.-        O",    
      "O            |        -.oO@$ABCDEFG I88888I GFEDCBA$@Oo.-        O",
      "O            |        -.oO@$ABCDEFG IJKLKJI GFEDCBA$@Oo.-        O", 
      "O            |        -.oO@$ABCDEFG IJKLKJI GFEDCBA$@Oo.-        O", #20
      "O            |                CDEFG         GFEDC                O",
      "O            |                 DEFGHIJ   JIHGFED                 O",
      "O            |                  EFGHIJ   JIHGFE                  O",
      "O            |                   FGHIJ   JIHGF                   O",
      "O            |                                                   O",
      "O            |  22222222                          44444444       O",
      "O            |  22222222                          44444444       O",
      "O            |  22222222                          44444444       O",
      "O            |                                                   O",
      "O            |                                                   O", #30
      "O            |                                                   O",
      "O            |                                                   O",
      "OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO"  #33
    )




  if (MapLevel == 10):
    
    DinnerPlate = VirusWorld(name='BigFood',
                               width        = 66, #we want the playfield to be 1 pixel larger on all sides than the display
                               height       = 34,
                               Map          = [[]],
                               Playfield    = [[]],
                               CurrentRoomH = 1,
                               CurrentRoomV = 1,
                               DisplayH     = 1,
                               DisplayV     = 1,
                               mutationrate = mutationrate,
                               replicationrate = replicationrate,
                               mutationdeathrate = mutationdeathrate,
                               VirusStartSpeed = VirusStartSpeed)


    TheMap.ColorList = {
      ' ' : (  0,  0,  0),
      '-' : ( 10, 10, 10),  
      '.' : ( 20, 20, 20),
      'o' : ( 30, 30, 30),
      'O' : ( 40, 40, 40),
      '@' : ( 50, 60, 60),
      '$' : ( 60, 60, 60),
      'A' : ( 70, 70, 70),
      'B' : ( 80, 80, 80),
      'C' : ( 90, 90, 90),
      'D' : (100,100,100),
      'E' : (110,110,110),
      'F' : (120,120,120),
      'G' : (130,130,130),
      'H' : (140,140,140),
      'I' : (150,150,150),
      'J' : (160,160,160),
      'K' : (170,170,170),
      'L' : (180,180,180),
      '|' : (  0,  0,  0),
      '*' : (  5,  5,  5),
      '1' : (0  ,150,  0),
      '2' : (150,  0,  0),
      '3' : (150,100,  0),
      '4' : (  0,  0,100),
      '5' : (200,  0, 50),
      '6' : (125,185,  0),
      '7' : (200,  0,200),
      '8' : ( 50,150, 75)
    }

    TheMap.TypeList = {
      ' ' : 'EmptyObject',
      '-' : 'wall',
      '.' : 'wall',
      'o' : 'wall',
      'O' : 'wall',
      '@' : 'wall',
      '#' : 'wall',
      '$' : 'wall',
      '#' : 'wall',
      '*' : 'wallbreakable',
      'A' : 'wallbreakable',
      'B' : 'wallbreakable',
      'C' : 'wallbreakable',
      'D' : 'wallbreakable',
      'E' : 'wallbreakable',
      'F' : 'wallbreakable',
      'G' : 'wallbreakable',
      'H' : 'wallbreakable',
      'I' : 'wallbreakable',
      'J' : 'wallbreakable',
      'K' : 'wallbreakable',
      'L' : 'wallbreakable',
      '|' : 'wall',
      '1' : 'virus',
      '2' : 'virus',
      '3' : 'virus',
      '4' : 'virus',
      '5' : 'virus',
      '6' : 'virus',
      '7' : 'virus',
      '8' : 'virus'
    }


    TheMap.map= (
      #0         1   ......2.........3.........4.........5.........6....65    
      "OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO", #0  
      "O            |                                                   O",
      "O            |   1                                       2       O",
      "O            |                                                   O",
      "O            |                                                   O",
      "O            |                                                   O",
      "O            |                                                   O",
      "O            |                                                   O",
      "O            |                                                   O", 
      "O            |                   FGHIJ   JIHF                    O", 
      "O            |                  EFGHIJ   JIHFE                   O", #10
      "O            |                 DEFGHIJ   JIHFEFE                 O",
      "O            |                CDEFGHIJ   JIHGFEDC                O",
      "O            |        -.oO@$ABCDEFG         GFEDCBA$@Oo.-        O",
      "O            |        -.oO@$ABCDEFG IJKLKJI GFEDCBA$@Oo.-        O",
      "O            |        -.oO@$ABCDEFG IJKLKJI GFEDCBA$@Oo.-        O",
      "O            |        -.oO@$ABCDEFG I88888I GFEDCBA$@Oo.-        O",
      "O            |        -.oO@$ABCDEFG I88888I GFEDCBA$@Oo.-        O",    
      "O            |        -.oO@$ABCDEFG I88888I GFEDCBA$@Oo.-        O",
      "O            |        -.oO@$ABCDEFG IJKLKJI GFEDCBA$@Oo.-        O", 
      "O            |        -.oO@$ABCDEFG IJKLKJI GFEDCBA$@Oo.-        O", #20
      "O            |                CDEFG         GFEDC                O",
      "O            |                 DEFGHIJ   JIHGFED                 O",
      "O            |                  EFGHIJ   JIHGFE                  O",
      "O            |                   FGHIJ   JIHGF                   O",
      "O            |                                                   O",
      "O            |                                                   O",
      "O            |                                                   O",
      "O            |                                                   O",
      "O            |                                                   O",
      "O            |                                                   O", #30
      "O            |   3                                       4       O",
      "O            |                                                   O",
      "OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO"  #33
    )





  if (MapLevel == 11):
    
    DinnerPlate = VirusWorld(name='BigFood',
                               width        = 66, #we want the playfield to be 1 pixel larger on all sides than the display
                               height       = 34,
                               Map          = [[]],
                               Playfield    = [[]],
                               CurrentRoomH = 1,
                               CurrentRoomV = 1,
                               DisplayH     = 1,
                               DisplayV     = 1,
                               mutationrate = mutationrate,
                               replicationrate = replicationrate,
                               mutationdeathrate = mutationdeathrate,
                               VirusStartSpeed = VirusStartSpeed)


    TheMap.ColorList = {
      ' ' : (  0,  0,  0),
      '-' : ( 30, 30, 30),  
      '.' : ( 70, 70, 70),
      'o' : ( 100,100,100),
      'O' : ( 130,130,130),
      '|' : (  0,  0,  0),
      '*' : (  5,  5,  5),
      '1' : (0  ,150,  0),
      '2' : (150,  0,  0),
      '3' : (150,100,  0),
      '4' : (  0,  0,100),
      '5' : (200,  0, 50),
      '6' : (125,185,  0),
      '7' : (200,  0,200),
      '8' : ( 50,150, 75)
    }

    TheMap.TypeList = {
      ' ' : 'EmptyObject',
      '-' : 'wall',
      '.' : 'wall',
      'o' : 'wall',
      'O' : 'wall',
      '@' : 'wall',
      '#' : 'wall',
      '$' : 'wall',
      '#' : 'wall',
      '*' : 'wallbreakable',
      '|' : 'wall',
      '1' : 'virus',
      '2' : 'virus',
      '3' : 'virus',
      '4' : 'virus',
      '5' : 'virus',
      '6' : 'virus',
      '7' : 'virus',
      '8' : 'virus'
    }


    TheMap.map= (
      #0         1   ......2.........3.........4.........5.........6....65    
      "OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO", #0  
      "O            |111111111                                2222222222O",
      "O            |11111111                                  222222222O",
      "O            |1111111                                    22222222O",
      "O            |111111                                      2222222O",
      "O            |11111                                        222222O",
      "O            |1111    ************************************* 22222O",
      "O            |111     *-----------------------------------*  2222O",
      "O            |11      *-.................................-*   222O", 
      "O            |1       *-.ooooooooooooooooooooooooooooooo.-*    22O", 
      "O            |        *-.o.............................o.-*     2O", 
      "O            |        *-.o.---------------------------.o.-*      O",
      "O            |        *-.o.-  5555555555555555555    -.o.-*      O", 
      "O            |        *-.o.-  5555555555555555555    -.o.-*      O",
      "O            |        *-.o.-----------****------------.o.-*      O", 
      "O            |        *-.o...........-****-............o.-*      O",
      "O            |        *-.ooooooooooo.-****-.oooooooooooo.-*      O",
      "O            |        *-.............-****-..............-*      O",
      "O            |        *---------------****----------------*      O",
      "O            |        *************************************      O",
      "O            |        *************************************      O",
      "O            |        *************************************      O",
      "O            |        *-----------------------------------*      O",
      "O            |        *-.................................-*      O", 
      "O            |        *-.ooooooooooooooooooooooooooooooo.-*     4O",
      "O            |3       *-.................................-*    44O",
      "O            |33      *-----------------------------------*   444O",
      "O            |333     *************************************  4444O",
      "O            |3333                                          44444O",
      "O            |33333                                        444444O",
      "O            |333333                                      4444444O", #30
      "O            |3333333                                    44444444O",
      "O            |33333333                                  444444444O",
      "OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO"  #33
    )


  if (MapLevel == 12):
    
    DinnerPlate = VirusWorld(name='BigFood',
                               width        = 66, #we want the playfield to be 1 pixel larger on all sides than the display
                               height       = 34,
                               Map          = [[]],
                               Playfield    = [[]],
                               CurrentRoomH = 1,
                               CurrentRoomV = 1,
                               DisplayH     = 1,
                               DisplayV     = 1,
                               mutationrate = mutationrate,
                               replicationrate = replicationrate,
                               mutationdeathrate = mutationdeathrate,
                               VirusStartSpeed = VirusStartSpeed)


    TheMap.ColorList = {
      ' ' : (  0,  0,  0),
      '-' : ( 10, 10, 10),  
      '.' : ( 20, 20, 20),
      'o' : ( 30, 30, 30),
      'O' : ( 40, 40, 40),
      '@' : ( 50, 60, 60),
      '$' : ( 60, 60, 60),
      'A' : ( 70, 70, 70),
      'B' : ( 80, 80, 80),
      'C' : ( 90, 90, 90),
      'D' : (100,100,100),
      'E' : (110,110,110),
      'F' : (120,120,120),
      'G' : (130,130,130),
      'H' : (140,140,140),
      'I' : (150,150,150),
      'J' : (160,160,160),
      'K' : (170,170,170),
      'L' : (180,180,180),
      '|' : (  0,  0,  0),
      '*' : (  5,  5,  5),
      '#' : (150,150,150),
      '1' : (  0,200,  0),
      '2' : (150,  0,  0),
      '3' : (150,100,  0),
      '4' : (  0,  0,100),
      '5' : (200,  0, 50),
      '6' : (125,185,  0),
      '7' : (200,  0,200),
      '8' : ( 50,150, 75)
    }

    TheMap.TypeList = {
      ' ' : 'EmptyObject',
      '-' : 'wall',
      '.' : 'wall',
      'o' : 'wall',
      'O' : 'wall',
      '@' : 'wall',
      '#' : 'wall',
      '$' : 'wall',
      '#' : 'wall',
      '*' : 'wallbreakable',
      'A' : 'wallbreakable',
      'B' : 'wallbreakable',
      'C' : 'wallbreakable',
      'D' : 'wallbreakable',
      'E' : 'wallbreakable',
      'F' : 'wallbreakable',
      'G' : 'wallbreakable',
      'H' : 'wallbreakable',
      'I' : 'wallbreakable',
      'J' : 'wallbreakable',
      'K' : 'wallbreakable',
      'L' : 'wallbreakable',
      '|' : 'wall',
      '1' : 'virus',
      '2' : 'virus',
      '3' : 'virus',
      '4' : 'virus',
      '5' : 'virus',
      '6' : 'virus',
      '7' : 'virus',
      '8' : 'virus'
    }


    TheMap.map= (
     #0         1  .......2.........3.........4.........5.........6....65    
     "OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO", #0  
     "O            |                                                   O",
     "O            |                                                   O",
     "O            |       AAAAAAAAAAAAAAAAAAAAAAA           11        O",
     "O            |       ABBBBBBBBBBBBBBBBBBBBBA                     O",
     "O            |       ABCCCCCCCCCCCCCCCCCCCBA                     O",
     "O            |       ABCDDDDDDDDDDDDDDDDDCBA                     O",
     "O            |       ABCDEEEEEEEEEEEEEEEDCBA                     O",
     "O            |       ABCDEFFFFFFFFFFFFFEDCBA           22        O", 
     "O            |       ABCDEFGGGGGGGGGGGFEDCBA                     O", 
     "O            |       ABCDEFGIIIIIIIIIHFEDCBA                     O", #10
     "O            |       ABCDEFGIJJJJJJJIHFEDCBA                     O",
     "O            |       ABCDEFGIJKKKKKJIHFEDCBA                     O",
     "O            |       ABCDEFGIJK444KJIHFEDCBA           33        O",
     "O            |       ABCDEFGIJK444KJIHFEDCBA                     O",
     "O            |       ABCDEFGIJKKKKKJIHFEDCBA                     O",
     "O            |       ABCDEFGIJJJJJJJIHFEDCBA                     O",
     "O            |       ABCDEFGIIIIIIIIIHFEDCBA                     O",    
     "O            |       ABCDEFGHHHHHHHHHHFEDCBA          44         O",
     "O            |       ABCDEFGFFFFFFFFFFFEDCBA                     O", 
     "O            |       ABCDEEEEEEEEEEEEEEEDCBA                     O", #20
     "O            |       ABCDDDDDDDDDDDDDDDDDCBA                     O",
     "O            |       ABCCCCCCCCCCCCCCCCCCCBA                     O",
     "O            |       ABBBBBBBBBBBBBBBBBBBBBA       55            O",
     "O            |       AAAAAAAAAAAAAAAAAAAAAAA                     O",
     "O|||||||||||||                                                   O",
     "O                                                                O",
     "O                                            66                  O",
     "O 111111                                                         O",
     "O 1   11                        77                        888888 O",
     "O 1    1                                                  888888 O", #30
     "O 1   11                                                  888888 O",
     "O 111111                                                  888888 O",
     "OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO"  #33
   )


  if (MapLevel == 13):
    
    #GenerateEmptyMapWithBorder(width, height, wall_char='-', fill_char=' '):

    TheMap = LED.TextMap(
      h      = 1,
      v      = 1,
      width  = 80, 
      height = 48
      )


    DinnerPlate = VirusWorld(name='Oversized',
                               width        = 80, #we want the playfield to be 1 pixel larger on all sides than the display
                               height       = 48,
                               Map          = [[]],
                               Playfield    = [[]],
                               CurrentRoomH = 1,
                               CurrentRoomV = 1,
                               DisplayH     = 1,
                               DisplayV     = 1,
                               mutationrate = mutationrate,
                               replicationrate = replicationrate,
                               mutationdeathrate = mutationdeathrate,
                               VirusStartSpeed = VirusStartSpeed)


    TheMap.ColorList = {
      ' ' : (  0,  0,  0),
      '-' : ( 10, 10, 10),  
      '.' : ( 20, 20, 20),
      'o' : ( 30, 30, 30),
      'O' : ( 40, 40, 40),
      '@' : ( 50, 60, 60),
      '$' : ( 60, 60, 60),
      'A' : ( 70, 70, 70),
      'B' : ( 80, 80, 80),
      'C' : ( 90, 90, 90),
      'D' : (100,100,100),
      'E' : (110,110,110),
      'F' : (120,120,120),
      'G' : (130,130,130),
      'H' : (140,140,140),
      'I' : (150,150,150),
      'J' : (160,160,160),
      'K' : (170,170,170),
      'L' : (180,180,180),
      '|' : (  0,  0,  0),
      '*' : (  5,  5,  5),
      '#' : (150,150,150),
      '1' : (  0,200,  0),
      '2' : (150,  0,  0),
      '3' : (150,100,  0),
      '4' : (  0,  0,100),
      '5' : (200,  0, 50),
      '6' : (125,185,  0),
      '7' : (200,  0,200),
      '8' : ( 50,150, 75)
    }

    TheMap.TypeList = {
      ' ' : 'EmptyObject',
      '-' : 'wall',
      '.' : 'wall',
      'o' : 'wall',
      'O' : 'wall',
      '@' : 'wall',
      '#' : 'wall',
      '$' : 'wall',
      '#' : 'wall',
      '*' : 'wallbreakable',
      'A' : 'wallbreakable',
      'B' : 'wallbreakable',
      'C' : 'wallbreakable',
      'D' : 'wallbreakable',
      'E' : 'wallbreakable',
      'F' : 'wallbreakable',
      'G' : 'wallbreakable',
      'H' : 'wallbreakable',
      'I' : 'wallbreakable',
      'J' : 'wallbreakable',
      'K' : 'wallbreakable',
      'L' : 'wallbreakable',
      '|' : 'wall',
      '1' : 'virus',
      '2' : 'virus',
      '3' : 'virus',
      '4' : 'virus',
      '5' : 'virus',
      '6' : 'virus',
      '7' : 'virus',
      '8' : 'virus'
    }


    TheMap.map= (
     #0         1  .......2.........3.........4.........5.........6.........7.........8    
     "OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO", #0  
     "O            |                                                                 O",
     "O            |                                                                 O",
     "O            |       AAAAAAAAAAAAAAAAAAAAAAA           11                      O",
     "O            |       ABBBBBBBBBBBBBBBBBBBBBA                                   O",
     "O            |       ABCCCCCCCCCCCCCCCCCCCBA                                   O",
     "O            |       ABCDDDDDDDDDDDDDDDDDCBA                                   O",
     "O            |       ABCDEEEEEEEEEEEEEEEDCBA                                   O",
     "O            |       ABCDEFFFFFFFFFFFFFEDCBA           22                      O", 
     "O            |       ABCDEFGGGGGGGGGGGFEDCBA                                   O", 
     "O            |       ABCDEFGIIIIIIIIIHFEDCBA                                   O", #10
     "O            |       ABCDEFGIJJJJJJJIHFEDCBA                                   O",
     "O            |       ABCDEFGIJKKKKKJIHFEDCBA                                   O",
     "O            |       ABCDEFGIJK444KJIHFEDCBA           33                      O",
     "O            |       ABCDEFGIJK444KJIHFEDCBA                                   O",
     "O            |       ABCDEFGIJKKKKKJIHFEDCBA                                   O",
     "O            |       ABCDEFGIJJJJJJJIHFEDCBA                                   O",
     "O            |       ABCDEFGIIIIIIIIIHFEDCBA                                   O",    
     "O            |       ABCDEFGHHHHHHHHHHFEDCBA          44                       O",
     "O            |       ABCDEFGFFFFFFFFFFFEDCBA                                   O", 
     "O            |       ABCDEEEEEEEEEEEEEEEDCBA                                   O", #20
     "O            |       ABCDDDDDDDDDDDDDDDDDCBA                                   O",
     "O            |       ABCCCCCCCCCCCCCCCCCCCBA                                   O",
     "O            |       ABBBBBBBBBBBBBBBBBBBBBA       55                          O",
     "O            |       AAAAAAAAAAAAAAAAAAAAAAA                                   O",
     "O|||||||||||||                                                                 O",
     "O                                                                              O",
     "O                                            66                                O",
     "O 111111                                                                       O",
     "O 1   11                        77                        888888               O",
     "O 1    1                                                  888888               O", #30
     "O 1   11                                                  888888               O",
     "O 111111                                                  888888               O",
     "O                                                                              O",
     "O                                                                              O",
     "O                                                                              O",
     "O                                                                              O",
     "O                                                                              O",
     "O                                                                              O",
     "O                                                                              O",
     "O                                                                              O", #40
     "O                                                                              O",
     "O                                                                              O",
     "O                                                                              O",
     "O                                                                              O",
     "O                                                                              O",
     "O                                                                              O",
     "OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO" #47
   )

    

  if (MapLevel == 14):
       

    TheMap = LED.TextMap(
      h      = 1,
      v      = 1,
      width  = 100, 
      height = 100
      )


    DinnerPlate = VirusWorld(name='Oversized',
                               width        = 80, #we want the playfield to be 1 pixel larger on all sides than the display
                               height       = 48,
                               Map          = [[]],
                               Playfield    = [[]],
                               CurrentRoomH = 1,
                               CurrentRoomV = 1,
                               DisplayH     = 1,
                               DisplayV     = 1,
                               mutationrate = mutationrate,
                               replicationrate = replicationrate,
                               mutationdeathrate = mutationdeathrate,
                               VirusStartSpeed = VirusStartSpeed)


    TheMap.ColorList = {
      ' ' : (  0,  0,  0),
      '-' : ( 10, 10, 10),  
      '.' : ( 20, 20, 20),
      'o' : ( 30, 30, 30),
      'O' : ( 40, 40, 40),
      '@' : ( 50, 60, 60),
      '$' : ( 60, 60, 60),
      'A' : ( 10, 10, 10),
      'B' : ( 20, 20, 20),
      'C' : ( 30, 30, 30),
      'D' : ( 40, 40, 40),
      'E' : ( 50, 50, 50),
      'F' : ( 60, 60, 60),
      'G' : ( 70, 70, 70),
      'H' : ( 80, 80, 80),
      'I' : ( 90, 90, 90),
      'J' : (100,100,100),
      'K' : (110,110,110),
      'L' : (120,120,120),
      '|' : (  0,  0,  0),
      '*' : (  5,  5,  5),
      '#' : (150,150,150),
      '1' : (  0,200,  0),
      '2' : (150,  0,  0),
      '3' : (150,100,  0),
      '4' : (  0,  0,100),
      '5' : (200,  0, 50),
      '6' : (125,185,  0),
      '7' : (200,  0,200),
      '8' : ( 50,150, 75)
    }

    TheMap.TypeList = {
      ' ' : 'EmptyObject',
      '-' : 'wall',
      '.' : 'wall',
      'o' : 'wall',
      'O' : 'wall',
      '@' : 'wall',
      '#' : 'wall',
      '$' : 'wall',
      '#' : 'wall',
      '*' : 'wallbreakable',
      'A' : 'wallbreakable',
      'B' : 'wallbreakable',
      'C' : 'wallbreakable',
      'D' : 'wallbreakable',
      'E' : 'wallbreakable',
      'F' : 'wallbreakable',
      'G' : 'wallbreakable',
      'H' : 'wallbreakable',
      'I' : 'wallbreakable',
      'J' : 'wallbreakable',
      'K' : 'wallbreakable',
      'L' : 'wallbreakable',
      '|' : 'wall',
      '1' : 'virus',
      '2' : 'virus',
      '3' : 'virus',
      '4' : 'virus',
      '5' : 'virus',
      '6' : 'virus',
      '7' : 'virus',
      '8' : 'virus'
    }

    TheMap.map = GenerateEmptyMapWithBorder(TheMap.width, TheMap.height, wall_char='-', fill_char=' ')

  
  DinnerPlate.CopyTextMapToPlayfield(TheMap)

  #we add random viruses to a plate of big food
  if(DinnerPlate.name == 'BigFood'):
    DinnerPlate.AddRandomVirusesToPlayfield(fast_rng.randint(1,MaxRandomViruses))

  return DinnerPlate;








def CreateDinnerPlate(width=66, height=34, virus_count=8):
    DinnerPlate = VirusWorld(
        name='BigFood',
        width=width,
        height=height,
        Map=[[]],
        Playfield=[[]],
        CurrentRoomH=1,
        CurrentRoomV=1,
        DisplayH=1,
        DisplayV=1,
        mutationrate=mutationrate,
        replicationrate=replicationrate,
        mutationdeathrate=mutationdeathrate,
        VirusStartSpeed=VirusStartSpeed
    )

    TheMap = LED.TextMap(
        h=1,
        v=1,
        width=width,
        height=height
    )

    TheMap.ColorList = DinnerPlate.DefaultColorList.copy()
    TheMap.TypeList = DinnerPlate.DefaultTypeList.copy()

    
    TheMap.map = CreateSimpleObstacleMap(width=width, height=height, block_count=(fast_rng.randint(4,10)), virus_count=virus_count )



    print(f"TheMap dimensions: {TheMap.width}x{TheMap.height}")

    DinnerPlate.CopyTextMapToPlayfield(TheMap)
    return DinnerPlate






def GetPlayfieldObject(h, v, Playfield):
    if 0 <= v < len(Playfield) and 0 <= h < len(Playfield[0]):
        return Playfield[v][h]
    else:
        return LED.OutOfBoundsObject  # safe default



def SetPlayfieldObject(v, h, obj, Playfield):
    if 0 <= v < len(Playfield) and 0 <= h < len(Playfield[0]):
        Playfield[v][h] = obj
        return True
    else:
        # Optional: log for debugging
        # print(f"[Warning] Out-of-bounds write attempt at ({v},{h})")
        return False



#-----------------------------
# Outbreak Global Variables --
#-----------------------------
InstabilityFactor = 50
ScrollSpeedLong   = 500
ScrollSpeedShort  = 5
MinBright         = 100
MaxBright         = 255



    


def PlayOutbreak(Duration,StopEvent):      
 
  global mutationrate 
  global mutationdeathrate
  global OriginalMutationRate
  global OriginalReplicationRate
  global OriginalMutationDeathRate
  global VirusMoves
  global ClumpingSpeed
  global ReplicationSpeed
  global FreakoutReplicationRate
  global FreakoutMoves
  global MaxVirusMoves
  global VirusTopSpeed
  global VirusBottomSpeed
  #global Canvas
  global PreviousFrame
  

  replicationrate   = OriginalReplicationRate
  mutationrate      = OriginalMutationRate
  mutationdeathrate = OriginalMutationDeathRate


  finished      = 'N'
  VirusMoves = 0
  LevelCount    = 0
  MaxLevel      = 14 #number of available mazes
  NameCount     = 0
  Viruses       = []
  VirusCount    = 0
  #Virus         = LED.EmptyObject
  VirusDeleted        = 0
  DominanceCount      = 0
  ClockSprite         = LED.CreateClockSprite(12)
  DayOfWeekSprite     = LED.CreateDayOfWeekSprite()
  MonthSprite         = LED.CreateMonthSprite()
  DayOfMonthSprite    = LED.CreateDayOfMonthSprite()

  ClockSprite.on      = 0
  StrainCreated       = 0
  OldVirusTopSpeed    = VirusTopSpeed
  OldVirusBottomSpeed = VirusBottomSpeed
  NextMaze            = False  #Used to indicate if we skip to the next maze (keyboard input 'n')
  BigFoodAlive        = False

  #PathCount     = len(CameraPath)
  PathPosition  = 0
  PositionSpeed = 100

  CameraDirection = 0
  CameraSpeed     = 5
  VirusesInWindow = 0
  
  #CameraH, CameraV, CameraSpeed = CameraPath[0]
  

  







  #The map is an array of a lists.  You can address each element has VH e.g. [V][H]
  #Copying the map to the playfield needs to follow the exact same shape

  #----------------------
  #-- Prepare Level    --
  #----------------------
  print("")
  print("")
  print("*****************************************************")
  #print("Before OutbreakGamesPlayed:",LED.OutbreakGamesPlayed)
  LED.OutbreakGamesPlayed = LED.OutbreakGamesPlayed + 1
  #print("Before SAVE OutbreakGamesPlayed:",LED.OutbreakGamesPlayed)
  LED.SaveConfigData()
  #print("After SAVE OutbreakGamesPlayed:",LED.OutbreakGamesPlayed)
  print("*****************************************************")

  LevelCount = fast_rng.randint(1,MaxLevel)
  LevelCount = 14    

#  DinnerPlate = CreateDinnerPlate(LevelCount)
  DinnerPlate = CreateDinnerPlate(width=80, height=45, virus_count=200)



  VirusCount = len(DinnerPlate.Viruses)
  print("VirusCount: ",VirusCount)
  DominanceCount = 0
  CameraH        = DinnerPlate.DisplayH
  CameraV        = DinnerPlate.DisplayV

  #af.ShowScrollingBanner("Outbreak!",LED.SDLowYellowR,LED.SDLowYellowG,LED.SDLowYellowB,ScrollSleep *0.8)
  #DinnerPlate.DisplayWindowZoom(CameraH,CameraV,2,16,0.025)
  
  


  NameCount = 1
  LevelsPlayed = 1

  #Show Custom sprites
  #DinnerPlate.CopySpriteToPlayfield(ClockSprite,      ClockH +1,      ClockV+1,      ClockRGB,       ObjectType = 'Wall',  Filler = 'DarkWall')
  #DinnerPlate.CopySpriteToPlayfield(DayOfWeekSprite,  DayOfWeekH +1,  DayOfWeekV+1,  DayOfWeekRGB,   ObjectType = 'Wall',  Filler = 'DarkWall')
  #DinnerPlate.CopySpriteToPlayfield(MonthSprite,      MonthH +1,      MonthV+1,      MonthRGB,       ObjectType = 'Wall',  Filler = 'DarkWall')
  #DinnerPlate.CopySpriteToPlayfield(DayOfMonthSprite, DayOfMonthH +1, DayOfMonthV+1, DayOfMonthRGB , ObjectType = 'Wall',  Filler = 'DarkWall')



  #Zoom out, just a little bit too much then zoom back in.  Nice effect.
  #DinnerPlate.DisplayWindowZoom(CameraH,CameraV,2,96,0)
  #DinnerPlate.DisplayWindowZoom(CameraH,CameraV,96,32,0)




  #--------------------------------
  #-- Main timing loop           --
  #--------------------------------

  while (finished == "N" and VirusMoves < MaxVirusMoves and LevelsPlayed <= MaxLevelsPlayed and VirusCount > 0):
    if StopEvent and StopEvent.is_set():
      print("\n" + "="*40)
      print("[Outbreak] StopEvent received")
      print("-> Shutting down gracefully...")
      print("="*40 + "\n")
      finished = 'Y'
      VirusMoves = MaxVirusMoves
      VirusCount = 0    
      break

    
    VirusMoves = VirusMoves + 1

    if(VirusMoves > LED.OutbreakHighScore):
        LED.OutbreakHighScore = VirusMoves
    

    #We will increase bottome speed X times over the course of a full game
    #OldVirusTopSpeed is the maximum speed we want to use no matter what
    m,r = divmod(VirusMoves, (MaxVirusMoves / SpeedIncrements))
    if (r == 0):
      VirusBottomSpeed = VirusBottomSpeed -1
      VirusTopSpeed    = VirusTopSpeed -1
      if (VirusTopSpeed < OldVirusTopSpeed):
        VirusTopSpeed = OldVirusTopSpeed
      if (VirusBottomSpeed < OldVirusTopSpeed):
        VirusBottomSpeed = OldVirusTopSpeed

    #--------------------------------
    #Check for keyboard input      --
    #--------------------------------
    #If we do this too often, the terminal window (if using telnet) will flicker  (now been fixed, see LED.PollKeyboard function)
    m,r = divmod(VirusMoves,KeyboardSpeed)
    if (r == 0):
      Key = LED.PollKeyboard()
      LED.ProcessKeypress(Key)

      if (Key == 'q'):
        LevelFinished = 'Y'
        Finished      = 'Y'
        return
      elif (Key == 'm'):
        DinnerPlate.DebugPlayfield()
      elif (Key == 'n'):
        #skip to next maze
        NextMaze = True


      #update text window
      #print ("Moves:",VirusMoves," VirusCount:",VirusCount,"NameCount:",NameCount," VirusTopSpeed:",VirusTopSpeed," VirusBottomSpeed:",VirusBottomSpeed,"      ",end="\r")      


    

    #--------------------------------
    #-- Virus actions              --
    #--------------------------------

    VirusCount = len(DinnerPlate.Viruses)
    #print("VirusCount: ",VirusCount)


    firstname = DinnerPlate.Viruses[0].name
    NameCount = 1
    
        
    #It seems that Python determines the "VirusCount-1" value once, and does not re-evaluate.  When some of the virises die, 
    #this thorws off the loop and counts.  I will deal with this internally.
    #for x in range (0,VirusCount-1):

    #Changed the for loop to a while loop
    x = 0


    x = 0
    while x < VirusCount:
      virus = DinnerPlate.Viruses[x]
      VirusDeleted = 0

      if VirusMoves == FreakoutMoves:
          virus.replicationrate = FreakoutReplicationRate

      if virus.name != firstname:
          NameCount += 1

      m, r = divmod(VirusMoves, virus.speed)
      if r == 0 and virus.alive == 1:
          MoveVirus(virus, DinnerPlate.Playfield)

      if virus.alive == 0:
          VirusDeleted = 1
          DinnerPlate.Playfield[virus.v][virus.h] = LED.EmptyObject
          del DinnerPlate.Viruses[x]
          VirusCount -= 1
          continue

      # Replication logic
      if (fast_rng.randint(0, virus.replicationrate) == 1 or 
          (VirusCount == 1 and fast_rng.randint(0, replicationrate) == 1)):
          NewVirus = ReplicateVirus(virus, DinnerPlate)
          if NewVirus.name != 'EmptyObject':
              DinnerPlate.Viruses.append(NewVirus)
              VirusCount = len(DinnerPlate.Viruses)

      # Move toward food
      if fast_rng.randint(1, ChanceOfHeadingToFood) == 1:
          FoodH, FoodV = DinnerPlate.FindClosestObject(
              SourceH=virus.h, SourceV=virus.v, Radius=FoodCheckRadius,
              ObjectType='WallBreakable')
          if LED.CheckBoundary(FoodH, FoodV) == 0:
              virus.direction = LED.PointTowardsObject8Way(virus.h, virus.v, FoodH, FoodV)

      # Random death
      if fast_rng.randint(0, virus.chanceofdying) == 1:
          virus.alive = 0
          virus.lives = 0
          DinnerPlate.Viruses[x] = LED.EmptyObject
          del DinnerPlate.Viruses[x]
          VirusCount -= 1
          continue
      else:
          if NameCount >= VirusNameSpeedupCount:
              virus.chanceofdying = GreatChanceOfDying

      x += 1




      #-------------------------------------------------
      #-- Random food appears!                        --
      #-------------------------------------------------
     
      '''  I just don't like this 
      #Point viruses towards the food
      if (fast_rng.randint(1,ChanceOfRandomFood) == 1 and BigFoodAlive == False):
        BigFoodH,BigFoodV = 0,0
        r,g,b = BigFoodRGB
        FreeSpotFound = False
        Tries         = 0
        
        while (FreeSpotFound == False and Tries <= 20):
          Tries = Tries + 1
          BigFoodH = fast_rng.randint(20,LED.HatWidth)
          BigFoodV = fast_rng.randint(5,LED.HatHeight - 8)


          TheObject = GetPlayfieldObject(h=BigFoodH,v=BigFoodV,Playfield=DinnerPlate.Playfield)
        
          if (TheObject.name == 'EmptyObject'):
            FreeSpotFound = True
            print("BigFood HV",BigFoodH,BigFoodV)
            print("TheObject name",TheObject.name)
            DinnerPlate.Playfield[BigFoodV][BigFoodH] = LED.Wall(BigFoodH,BigFoodV,r,g,b,1,BigFoodLives,'WallBreakable')
            print ("Random food appears:",BigFoodH,BigFoodV)
            for x in range(0,VirusCount):
              DinnerPlate.Viruses[x].direction = LED.PointTowardsObject8Way(DinnerPlate.Viruses[x].h,DinnerPlate.Viruses[x].v,BigFoodH,BigFoodV)
              DinnerPlate.Viruses[x].AdjustSpeed(-1) 
              DinnerPlate.Viruses[x].eating = 0
              DinnerPlate.Viruses[x].clumping = True

              BigFoodAlive = True
      #if the big food is alive, we check to see if the spot is still occupied.  
      #If it is, turn all viruses towardsit
      if (BigFoodAlive == True and fast_rng.randint(1,50) == 1):
        if (DinnerPlate.Playfield[BigFoodV][BigFoodH].name == 'WallBreakable'):
            for x in range(0,VirusCount):
              DinnerPlate.Viruses[x].direction = LED.PointTowardsObject8Way(DinnerPlate.Viruses[x].h,DinnerPlate.Viruses[x].v,BigFoodH,BigFoodV)
              #DinnerPlate.Viruses[x].AdjustSpeed(-5) 
              DinnerPlate.Viruses[x].eating = 0
              #DinnerPlate.Viruses[x].clumping = False
        else:
          BigFoodAlive = False
      '''

      #-------------------------------------------------
      #-- Adjust parameters if too many viruses alive --
      #-------------------------------------------------

      #if too many virus strains, increase speed
      #otherwise reset to original speeds
      if(NameCount >= VirusNameSpeedupCount):
        VirusTopSpeed    = OldVirusTopSpeed
        VirusBottomSpeed = OldVirusTopSpeed
        mutationdeathrate   = 1

    
    #----------------------
    #-- Audit Playfield  --  
    #----------------------
    #There seems to be a bug where an old dead virus is still on the playfield.
    #We will check periodically and remove them
    m,r = divmod(VirusMoves,AuditSpeed)
    if(r == 0):
      #DinnerPlate.DebugPlayfield()
      for v in range(0,DinnerPlate.height):
        for h in range(0,DinnerPlate.width):
          if (DinnerPlate.Playfield[v][h].alive == 0 and DinnerPlate.Playfield[v][h].name != 'EmptyObject'):
            DinnerPlate.Playfield[v][h] = LED.EmptyObject
            #print('Zombie detected:',v,h,DinnerPlate.Playfield[v][h].name)


    #-------------------------------------------
    #-- Level ends when one virus dominates   --
    #-------------------------------------------
  
    if (NameCount == 1 or NextMaze == True):
      DominanceCount = DominanceCount + 1
     
      #one virus remains, increase chance of spreading
      replicationrate   = 1
      mutationdeathrate = mutationdeathrate * 25
      

    

      #print ("DominanceCount:",DominanceCount,"DominanceMaxCount:",DominanceMaxCount,"VirusCount:",VirusCount,"VirusMaxCount:",VirusMaxCount)
      #if one virus dominates for X ticks, reset and load next level
      if (DominanceCount >= DominanceMaxCount) or(VirusCount >= VirusMaxCount) or (NextMaze == True):
        print ("VirusCount:",VirusCount," DominanceCount:",DominanceCount,"NextMaze:",NextMaze)
        #print ("Flashdot hv: ",DinnerPlate.Viruses[0].h,DinnerPlate.Viruses[0].v)
        #FlashDot (DinnerPlate.Viruses[0].h - CameraH,DinnerPlate.Viruses[0].v + CameraV,0.5)
        time.sleep(1)
        #LED.ClearBigLED()
        FlashAllViruses(DinnerPlate.Viruses,VirusCount,DinnerPlate,CameraH,CameraV)
        DinnerPlate.DisplayWindowZoom(CameraH,CameraV,32,1,0.01)

        LED.ClearBuffers()
        LED.ShowGlowingText(h = -1,v = 2,  Text = 'STRAIN', RGB = LED.HighYellow,ShadowRGB = LED.DarkYellow,ZoomFactor=2)
        LED.ShowGlowingText(h = -1,v = 14,  Text = 'SECURE', RGB = LED.HighYellow,ShadowRGB = LED.DarkYellow,ZoomFactor=2)
        time.sleep(1)
        LED.ZoomScreen(LED.ScreenArray,32,1,0.01)
        


        #Prepare new level
        DominanceCount    = 0
        LevelCount        = fast_rng.randint(1,MaxLevel)
        

        replicationrate   = OriginalReplicationRate
        mutationdeathrate = OriginalMutationDeathRate
        VirusTopSpeed    = OldVirusTopSpeed
        VirusBottomSpeed = OldVirusBottomSpeed
        DinnerPlate = CreateDinnerPlate(width=80, height=45, virus_count=250) 

        CameraH             = DinnerPlate.DisplayH
        CameraV             = DinnerPlate.DisplayV
        
        VirusCount          = len(DinnerPlate.Viruses)
        ClockSprite         = LED.CreateClockSprite(12)
        NextMaze            = False
        LevelsPlayed = LevelsPlayed +1


        #Show Custom sprites
        #DinnerPlate.CopySpriteToPlayfield(ClockSprite,      ClockH +1,      ClockV+1,      ClockRGB,       ObjectType = 'Wall',  Filler = 'DarkWall')
        #DinnerPlate.CopySpriteToPlayfield(DayOfWeekSprite,  DayOfWeekH +1,  DayOfWeekV+1,  DayOfWeekRGB,   ObjectType = 'Wall',  Filler = 'DarkWall')
        #DinnerPlate.CopySpriteToPlayfield(MonthSprite,      MonthH +1,      MonthV+1,      MonthRGB,       ObjectType = 'Wall',  Filler = 'DarkWall')
        #DinnerPlate.CopySpriteToPlayfield(DayOfMonthSprite, DayOfMonthH +1, DayOfMonthV+1, DayOfMonthRGB , ObjectType = 'Wall',  Filler = 'DarkWall')

        ClockSprite.on      = 0
        DinnerPlate.DisplayWindowZoom(CameraH,CameraV,2,32,0.025)
        nextname = ""

        LED.SaveConfigData()


    else:
      DominanceCount = 0
      StrainCreated  = 0
        


    #------------------
    #-- Main Display --
    #------------------

    # If it is time to show the clock, turn it on and show it
    # increment clock location if it is time to do so


    
    m,r = divmod(VirusMoves,CheckClockSpeed)
    if (r == 0):  
      #CheckClockTimer(ClockSprite)
      TheTime = LED.CreateClockSprite(12)

      #Show Custom sprites
      #DinnerPlate.CopySpriteToPlayfield(ClockSprite,      ClockH +1,      ClockV +1,      ClockRGB,       ObjectType = 'Wall',  Filler = 'DarkWall')
      #DinnerPlate.CopySpriteToPlayfield(DayOfWeekSprite,  DayOfWeekH +1,  DayOfWeekV+1,  DayOfWeekRGB,   ObjectType = 'Wall',  Filler = 'DarkWall')
      #DinnerPlate.CopySpriteToPlayfield(MonthSprite,      MonthH +1,      MonthV+1,      MonthRGB,       ObjectType = 'Wall',  Filler = 'DarkWall')
      #DinnerPlate.CopySpriteToPlayfield(DayOfMonthSprite, DayOfMonthH +1, DayOfMonthV+1, DayOfMonthRGB , ObjectType = 'Wall',  Filler = 'DarkWall')

  
    # #print ("Camera HV:",CameraH, CameraV)
    # if (ClockSprite.on == 1):
      # #print ("Clock on")
      # DinnerPlate.DisplayWindowWithSprite(CameraH, CameraV, ClockSprite)
      # MoveMessageSprite(VirusMoves,ClockSprite)
    # # else:
    DinnerPlate.DisplayWindow(CameraH, CameraV)
    #frame = DinnerPlate.BuildRGBFrame(CameraH, CameraV)
    #Canvas = DinnerPlate.DisplayWindow(    h=CameraH,    v=CameraV,    PreviousFrame=PreviousFrame,    Canvas=Canvas,    ZoomFactor=0)
  
    
    #-------------------------
    #-- Create Clock Sprite --
    #-------------------------
    # we want to display the clock ever X seconds, so we call the function CheckElapsedTime to see if that many
    # seconds have passed.  If so, create the clock and start sliding it onto the screen at a specific speed.
    # After X seconds, slide off screen and reset the timers.
   
    if (LED.CheckElapsedTime(CheckTime) == 1):
      if (ClockSprite.on == 0):
        ClockSprite = LED.CreateClockSprite(12)
      
      
    #End game if all viruses dead
    VirusCount = len(DinnerPlate.Viruses)
    if (VirusCount == 0 and LevelsPlayed >= MaxLevelsPlayed):
      finished = "Y"
      print("All virises died.  LevelsPlayed:",LevelsPlayed, "MaxLevels:",MaxLevelsPlayed)


    #Load up for the next map
    if(VirusCount == 0):
    
      LED.ClearBigLED()
      LED.ClearBuffers()
      CursorH = 0
      CursorV = 0
      LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"LEVEL " + str(LevelsPlayed) + " CLEARED",CursorH=CursorH,CursorV=CursorV,MessageRGB=(0,175,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalTypeSpeed)
      LED.BlinkCursor(CursorH= CursorH,CursorV=CursorV,CursorRGB=CursorRGB,CursorDarkRGB=CursorDarkRGB,BlinkSpeed=0.5,BlinkCount=2)

      LevelsPlayed = LevelsPlayed +1
    

      #End game after X minutes
      h,m,s    = LED.GetElapsedTime(start_time,time.time())
      if(m > Duration):
        print("Elapsed Time:  mm:ss",m,s)
        LED.SaveConfigData()
        print("Ending game after",m," minutes")
        #LED.ShowFireworks(FireworksExplosion,(fast_rng.randint(5,10)),0.02)

        LED.ClearBigLED()
        LED.ClearBuffers()
        CursorH = 0
        CursorV = 0
        LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"VIRUS SUCCESSFULLY QUARANTINED",CursorH=CursorH,CursorV=CursorV,MessageRGB=(150,0,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalTypeSpeed)
        LED.BlinkCursor(CursorH= CursorH,CursorV=CursorV,CursorRGB=CursorRGB,CursorDarkRGB=CursorDarkRGB,BlinkSpeed=0.5,BlinkCount=2)
        LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"IMMUNITY BOOSTED",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)
        LED.BlinkCursor(CursorH= CursorH,CursorV=CursorV,CursorRGB=CursorRGB,CursorDarkRGB=CursorDarkRGB,BlinkSpeed=0.5,BlinkCount=2)
          
        return();


      #Continue game by loading next level
      print("Loading next level")
      LED.OutbreakGamesPlayed = LED.OutbreakGamesPlayed + 1
      LED.SaveConfigData()
      
      
      LevelCount = fast_rng.randint(1,MaxLevel)
      
      
      
      DinnerPlate = CreateDinnerPlate(width=80, height=44, virus_count=250) 
      VirusCount = len(DinnerPlate.Viruses)
      firstname = DinnerPlate.Viruses[0].name
      print("VirusCount: ",VirusCount)
      DominanceCount = 0
      CameraH        = DinnerPlate.DisplayH
      CameraV        = DinnerPlate.DisplayV
      NameCount = 1
      nextname  = ""
      VirusMoves = 0

      #Show Custom sprites
      #DinnerPlate.CopySpriteToPlayfield(ClockSprite,      ClockH +1,      ClockV+1,      ClockRGB,       ObjectType = 'Wall',  Filler = 'DarkWall')
      #DinnerPlate.CopySpriteToPlayfield(DayOfWeekSprite,  DayOfWeekH +1,  DayOfWeekV+1,  DayOfWeekRGB,   ObjectType = 'Wall',  Filler = 'DarkWall')
      #DinnerPlate.CopySpriteToPlayfield(MonthSprite,      MonthH +1,      MonthV+1,      MonthRGB,       ObjectType = 'Wall',  Filler = 'DarkWall')
      #DinnerPlate.CopySpriteToPlayfield(DayOfMonthSprite, DayOfMonthH +1, DayOfMonthV+1, DayOfMonthRGB , ObjectType = 'Wall',  Filler = 'DarkWall')
      #Zoom out, just a little bit too much then zoom back in.  Nice effect.
      DinnerPlate.DisplayWindowZoom(CameraH,CameraV,2,96,0)
      DinnerPlate.DisplayWindowZoom(CameraH,CameraV,96,32,0)

      finished = "N"
      print(finished, VirusMoves, MaxVirusMoves, LevelsPlayed, MaxLevelsPlayed, VirusCount)
      time.sleep(3)





  #let the display show the final results before clearing
  time.sleep(1)
  LED.ClearBigLED()
  DinnerPlate.DisplayWindowZoom(CameraH,CameraV,32,2,0.025)



  return






























def LaunchOutbreak(Duration = 10000, ShowIntro = True, StopEvent=None):
  
  #--------------------------------------
  # M A I N   P R O C E S S I N G      --
  #--------------------------------------

  print("ShowIntro:",ShowIntro)
  
  
  # Our own customized fast random implementation
  global fast_rng
  fast_rng = FastRandom(seed=1234)  
  
  
  if(ShowIntro == True):

    LED.ShowTitleScreen(
        BigText             = 'UTBR8K',
        BigTextRGB          = LED.HighRed,
        BigTextShadowRGB    = LED.ShadowRed,
        LittleText          = 'AN INFECTION',
        LittleTextRGB       = LED.MedGreen,
        LittleTextShadowRGB = (0,10,0), 
        ScrollText          = 'THE PLAGUE SPREADS',
        ScrollTextRGB       = LED.MedYellow,
        ScrollSleep         = 0.03, # time in seconds to control the scrolling (0.005 is fast, 0.1 is kinda slow)
        DisplayTime         = 1,           # time in seconds to wait before exiting 
        ExitEffect          = 0            # 0=Random / 1=shrink / 2=zoom out / 3=bounce / 4=fade /5=fallingsand
        )


    LED.ClearBigLED()
    LED.ClearBuffers()
    CursorH = 0
    CursorV = 0
    LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"ENTERING THE CATACOMBS",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalTypeSpeed)
    LED.BlinkCursor(CursorH= CursorH,CursorV=CursorV,CursorRGB=CursorRGB,CursorDarkRGB=CursorDarkRGB,BlinkSpeed=0.5,BlinkCount=2)
    LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"COLLECTING VIRUS SAMPLES",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalTypeSpeed)
    LED.BlinkCursor(CursorH= CursorH,CursorV=CursorV,CursorRGB=CursorRGB,CursorDarkRGB=CursorDarkRGB,BlinkSpeed=0.5,BlinkCount=2)
    LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"INITIATING LOCKDOWN PROTOCOLS",CursorH=CursorH,CursorV=CursorV,MessageRGB=(225,0,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)
    LED.BlinkCursor(CursorH= CursorH,CursorV=CursorV,CursorRGB=CursorRGB,CursorDarkRGB=CursorDarkRGB,BlinkSpeed=0.5,BlinkCount=2)


  PlayOutbreak(Duration,StopEvent)
        

  LED.ClearBigLED()
  LED.ClearBuffers()
  CursorH = 0
  CursorV = 0
  LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"VIRAL OUTBREAK HALTED",CursorH=CursorH,CursorV=CursorV,MessageRGB=(0,175,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalTypeSpeed)
  LED.BlinkCursor(CursorH= CursorH,CursorV=CursorV,CursorRGB=CursorRGB,CursorDarkRGB=CursorDarkRGB,BlinkSpeed=0.5,BlinkCount=2)
  LED.ScreenArray, CursorH,CursorV = LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"VIRAL LOAD: " ,CursorH=CursorH,CursorV=CursorV,MessageRGB=(0,205,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)
  LED.ScreenArray, CursorH,CursorV = LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray, str(VirusMoves),CursorH=CursorH,CursorV=CursorV,MessageRGB=(150,150,150),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)
  LED.BlinkCursor(CursorH= CursorH,CursorV=CursorV,CursorRGB=CursorRGB,CursorDarkRGB=CursorDarkRGB,BlinkSpeed=0.5,BlinkCount=1)
  LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"Games Played:",CursorH=CursorH,CursorV=CursorV,MessageRGB=(0,205,0),CursorRGB=(0,200,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)
  LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,str(LED.OutbreakGamesPlayed),CursorH=CursorH,CursorV=CursorV,MessageRGB=(150,150,150),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)
  LED.BlinkCursor(CursorH= CursorH,CursorV=CursorV,CursorRGB=CursorRGB,CursorDarkRGB=CursorDarkRGB,BlinkSpeed=0.5,BlinkCount=1)
  LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"QUARANTINE STILL ACTIVE... OR IS IT?",CursorH=CursorH,CursorV=CursorV,MessageRGB=(225,0,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)
  LED.BlinkCursor(CursorH= CursorH,CursorV=CursorV,CursorRGB=CursorRGB,CursorDarkRGB=CursorDarkRGB,BlinkSpeed=0.5,BlinkCount=2)






#execute if this script is called directly
if __name__ == "__main__" :
  while(1==1):
    LED.LoadConfigData()
    LED.SaveConfigData()
    print("After SAVE OutbreakGamesPlayed:",LED.OutbreakGamesPlayed)
    LaunchOutbreak(100000,ShowIntro = False, StopEvent=None)        


















