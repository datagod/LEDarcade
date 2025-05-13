
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
ScrollSleep         = 0.015
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






LED.ShowTitleScreen(
BigText             = "ALERT!",
BigTextRGB          = LED.MedPurple,
BigTextShadowRGB    = LED.ShadowPurple,
LittleText          = "by datagod",
LittleTextRGB       = LED.MedRed,
LittleTextShadowRGB = LED.ShadowRed, 
ScrollText          = "intruders will be interregated, tortured, then released.  maybe.",
ScrollTextRGB       = LED.MedYellow,
ScrollSleep         = ScrollSleep *2 , # time in seconds to control the scrolling (0.005 is fast, 0.1 is kinda slow)
DisplayTime         = 1,           # time in seconds to wait before exiting 
ExitEffect          = 5,           # 0=Random / 1=shrink / 2=zoom out / 3=bounce / 4=fade /5=fallingsand
LittleTextZoom      = 1
)


print ("--Start--")
#Fake boot sequence
LED.ClearBigLED()
LED.ClearBuffers()
CursorH = 0
CursorV = 0
LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"METROPOLIS DREAMWARE SYSTEM COMPUTER BOOTING",CursorH=CursorH,CursorV=CursorV,MessageRGB=(0,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalTypeSpeed)
LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,".........................",CursorH=CursorH,CursorV=CursorV,MessageRGB=(0,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.025,ScrollSpeed=ScrollSleep)
LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"ACTIVATING SENTINEL PROGRAMS",CursorH=CursorH,CursorV=CursorV,MessageRGB=(0,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalTypeSpeed)
LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,".........................",CursorH=CursorH,CursorV=CursorV,MessageRGB=(0,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=ScrollSleep)
LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"SENTINEL ACTIVE AND AWAITING FURTHER INSTRUCTIONS",CursorH=CursorH,CursorV=CursorV,MessageRGB=(0,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)
LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,".........................",CursorH=CursorH,CursorV=CursorV,MessageRGB=(0,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.025,ScrollSpeed=ScrollSleep)
LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"YOU ARE BEING WATCHED",CursorH=CursorH,CursorV=CursorV,MessageRGB=(200,000,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)
LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,".........................",CursorH=CursorH,CursorV=CursorV,MessageRGB=(0,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.025,ScrollSpeed=ScrollSleep)
LED.BlinkCursor(CursorH= CursorH,CursorV=CursorV,CursorRGB=CursorRGB,CursorDarkRGB=CursorDarkRGB,BlinkSpeed=0.5,BlinkCount=2)
#IPAddress = LED.ShowIPAddress(Wait=5)






while (1==1):

    LED.StarryNightDisplayText(
    Text1 = "METROPOLIS DREAMWARE",
    Text2 = "RESEARCH AND DEVELOPMENT DEPARTMENT",
    Text3 = "THIS IS A CLASSIFIED RESEARCH FACILITY.  ACCESS DENIED!",
    RunSeconds = 60
    )                    





