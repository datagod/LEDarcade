
import os
os.system('cls||clear')

import time
import sys

import LEDarcade as LED
from rgbmatrix import graphics
from rgbmatrix import RGBMatrix, RGBMatrixOptions


LED.TheMatrix.brightness = 50
print("GIF TEST")

while(1==1):
  LED.TheMatrix.Clear()

  LED.DisplayGIF('./images/donkeykong.gif',32,32,5,0.12)
  LED.TheMatrix.Clear()
  LED.DisplayGIF('./images/marioprincesskiss.gif',32,32,1,0.06)
  
  LED.TheMatrix.Clear()
  LED.DisplayGIF('./images/samusbounce.gif',32,32,15,0.09)
  LED.DisplayGIF('./images/minions.gif',64,32,15,0.06)
  LED.TheMatrix.Clear()
  LED.DisplayGIF('./images/samus.gif',32,32,20,0.06)
  LED.DisplayGIF('./images/diner.gif',64,32,5,0.04)
  LED.DisplayGIF('./images/homer_marge2.gif',64,32,5,0.04)
  LED.DisplayGIF('./images/runningman2.gif',64,32,1,0.04)
  LED.DisplayGIF('./images/arcade1.gif',64,32,25,0.12)
  LED.DisplayGIF('./images/arcade2.gif',64,32,25,0.12)
  LED.TheMatrix.Clear()
  LED.DisplayGIF('./images/mario.gif',32,32,15,0.05)
  LED.DisplayGIF('./images/homer_marge.gif',64,32,5,0.04)
  LED.DisplayGIF('./images/fishburger.gif',64,32,2,0.04)
  LED.TheMatrix.Clear()
  LED.DisplayGIF('./images/ghosts.gif',64,32,10,0.04)



print("TEST COMPLETE")



