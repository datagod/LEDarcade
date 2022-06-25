# %%

'''
TO DO:

'''



import os
os.system('cls||clear')

import sys

import LEDarcade as LED
from rgbmatrix import graphics
from rgbmatrix import RGBMatrix, RGBMatrixOptions

import random
from configparser import SafeConfigParser
import traceback




import pprint
import copy



import time
from datetime import datetime, timezone


#---------------------------------------
#Variable declaration section
#---------------------------------------
ScrollSleep         = 0.025
TerminalTypeSpeed   = 0.02  #pause in seconds between characters
TerminalScrollSpeed = 0.02  #pause in seconds between new lines
CursorRGB           = (0,255,0)
CursorDarkRGB       = (0,50,0)



HatHeight = 32
HatWidth  = 64
StreamBrightness = 20
GifBrightness    = 25
MaxBrightness    = 80

  



#Sprite display locations
LED.ClockH,      LED.ClockV,      LED.ClockRGB      = 0,0,  (0,150,0)
LED.DayOfWeekH,  LED.DayOfWeekV,  LED.DayOfWeekRGB  = 8,20,  (125,20,20)
LED.MonthH,      LED.MonthV,      LED.MonthRGB      = 28,20, (125,30,0)
LED.DayOfMonthH, LED.DayOfMonthV, LED.DayOfMonthRGB = 47,20, (115,40,10)

#Colors
TerminalRGB = (0,200,0)
CursorRGB = (0,75,0)



time.sleep(10)



LED.ShowTitleScreen(
BigText             = "LED ARCADE",
BigTextRGB          = LED.MedPurple,
BigTextShadowRGB    = LED.ShadowPurple,
LittleText          = "by datagod",
LittleTextRGB       = LED.MedRed,
LittleTextShadowRGB = LED.ShadowRed, 
ScrollText          = "A twitch enabled LED powered retro clock",
ScrollTextRGB       = LED.MedYellow,
ScrollSleep         = ScrollSleep /2, # time in seconds to control the scrolling (0.005 is fast, 0.1 is kinda slow)
DisplayTime         = 1,           # time in seconds to wait before exiting 
ExitEffect          = 5,           # 0=Random / 1=shrink / 2=zoom out / 3=bounce / 4=fade /5=fallingsand
LittleTextZoom      = 1
)


ImageName = "./images/tgthumb.jpg"
ImageName = "./images/TwinGalaxies.png"
LED.ShowImage(ImageName,Fade = True, MaxBright = 100, Duration = 1)
LED.ClearBigLED()



LED.StarryNightDisplayText(
Text1 = "HIGH SCORES",
Text2 = "WATCH THE TOP PLAYERS IN THE WORLD",
Text3 = "BREAK RECORDS, MAKE FRIENDS, CELEBRATE EXCELLENCE",
RunSeconds = 60
)                    






# %%

 