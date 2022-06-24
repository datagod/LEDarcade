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






LED.TheMatrix.brightness = StreamBrightness
LED.ZoomImage(ImageName="./images/TwinGalaxies.png",ZoomStart=1,ZoomStop=256,ZoomSleep=0.025,Step=4)
LED.ZoomImage(ImageName="./images/TwinGalaxies.png",ZoomStart=256,ZoomStop=64,ZoomSleep=0.025,Step=4)
time.sleep(3)
LED.ClearBigLED()
LED.TheMatrix.brightness = MaxBrightness







LED.ShowTitleScreen(
BigText             = "SUBARCTICA",
BigTextRGB          = LED.MedPurple,
BigTextShadowRGB    = LED.ShadowPurple,
LittleText          = "control center #1",
LittleTextRGB       = LED.MedRed,
LittleTextShadowRGB = LED.ShadowRed, 
ScrollText          = "There is no escapae",
ScrollTextRGB       = LED.MedYellow,
ScrollSleep         = ScrollSleep /2, # time in seconds to control the scrolling (0.005 is fast, 0.1 is kinda slow)
DisplayTime         = 1,           # time in seconds to wait before exiting 
ExitEffect          = 5,           # 0=Random / 1=shrink / 2=zoom out / 3=bounce / 4=fade /5=fallingsand
LittleTextZoom      = 1
)


LED.StarryNightDisplayText(
Text1 = "jacob mcevoy is a cool dude",
Text2 = "your mission is to eat cheese",
Text3 = "how  many times can a dead dog fart?",
RunSeconds = 60
)                    






# %%

 