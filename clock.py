# %%

import LEDarcade as LED
from rgbmatrix import graphics
from rgbmatrix import RGBMatrix, RGBMatrixOptions
import time
import random

#Variable declaration section
ScrollSleep   = 0.025
HatHeight = 32
HatWidth  = 64


print ("---------------------------------------------------------------")
print ("WELCOME TO THE LED ARCADE             ")
print ("")
print ("BY DATAGOD")
print ("")
print ("This program will demonstrate several LED functions that have")
print ("been developed as part of the Arcade Retro Clock RGB project.")
print ("---------------------------------------------------------------")
print ("")
print ("")








#--------------------------------------
#  SHOW TITLE SCREEN                 --
#--------------------------------------


'''
LED.ShowTitleScreen(
    BigText             = 'CLOCK',
    BigTextRGB          = LED.MedPurple,
    BigTextShadowRGB    = LED.ShadowPurple,
    LittleText          = 'BY LEDARCADE',
    LittleTextRGB       = LED.MedRed,
    LittleTextShadowRGB = LED.ShadowRed, 
    ScrollText          = 'ITS ABOUT TIME',
    ScrollTextRGB       = LED.MedYellow,
    ScrollSleep         = ScrollSleep, # time in seconds to control the scrolling (0.005 is fast, 0.1 is kinda slow)
    DisplayTime         = 1,           # time in seconds to wait before exiting 
    ExitEffect          = 0            # 0=Random / 1=shrink / 2=zoom out / 3=bounce / 4=fade /5=fallingsand
    )
'''



#--------------------------------------
#  SHOW CLOCKS                       --
#--------------------------------------

while 1==1:

    #This allows you to create a title screen with different size text
    #some scrolling text, an animation and even a nice fade to black


    #Starry Night Clock
    if(LED.HatWidth > 64):
      ZoomFactor = 3

    else:
      ZoomFactor = 2


    LED.DisplayDigitalClock(ClockStyle=3,CenterHoriz=True,v=1, hh=24, ZoomFactor = ZoomFactor, AnimationDelay=10, RunMinutes = 5, ScrollSleep = 0.01 )


    LED.DisplayDigitalClock(
      ClockStyle = 1,
      CenterHoriz = True,
      v   = 1, 
      hh  = 24,
      RGB = LED.LowGreen,
      ShadowRGB     = LED.ShadowGreen,
      ZoomFactor    = 3,
      AnimationDelay= 10,
      RunMinutes = 5,
      ScrollSleep = 0.05)

    LED.DisplayDigitalClock(ClockStyle=2,CenterHoriz=True,v=1, hh=24, ZoomFactor = 1, AnimationDelay=10, RunMinutes = 1,ScrollSleep = 0.05 )



# %%

