# -*- coding: utf-8 -*-



# Notes
# =====
#
# - make a function to copy a sprite to a virus playfield
# - use the new pacmaze drawing technique to create sprites
#
# make sure we use setpixel to draw, not .SetPixel.  We need to always update the buffer.

# The buffer is a 2D array.  32 lines of 64 pixels
# BUFFER[V][H]  



"""
================================================================================
LEDarcade - Modular Display Framework for Raspberry Pi LED Panels
================================================================================

Author: William McEvoy (@datagod)
License: Non-commercial use only. Contact for commercial licensing.

DESCRIPTION:
------------
LEDarcade is a Python framework that enables high-performance rendering of
sprites, animations, clocks, and interactive graphics on RGB LED matrices
attached to a Raspberry Pi. It serves as the core display engine for a suite
of retro-inspired games and visualizers such as DotInvaders, Outbreak,
Defender, and custom Twitch integrations.

ARCHITECTURE OVERVIEW:
----------------------
- Framebuffer Architecture:
    ▸ Screen drawing is abstracted via a `ScreenArray` 2D RGB buffer.
    ▸ Rendering occurs off-screen and is then pushed to the LED display for flicker-free visuals.
- RGBMatrix Integration:
    ▸ Uses the `rpi-rgb-led-matrix` C++ library bindings for low-level control.
    ▸ All pixel updates are batched for performance.
- Game Coordination:
    ▸ Centralized color schemes, game configurations, and runtime globals.
    ▸ Enables simultaneous support for multiple games via `LEDcommander`.

KEY FEATURES:
-------------
- Multi-game support (DotInvaders, Defender, Outbreak, etc.)
- Gamma correction for color tuning
- Dynamic sprite rendering and layering
- Twitch and Patreon listener integration (via async Flask and TwitchIO)
- CLI and terminal emulation modes
- Numba and NumPy support for optimized math-heavy visualizations

DISPLAY LAYOUT:
---------------
- 2D array: ScreenArray[V][H] representing vertical/horizontal pixels
- Configurable sizes (32x32, 64x32, 128x32)
- Location constants for clock/date/ticker overlays
- Sprites drawn using pixel buffers and copied with color masking

RECOMMENDED USAGE:
------------------
This module should be imported only from child processes that interact
with the display hardware. The GPIO matrix setup must *never* be done in
the parent process to prevent hardware lockup.

===============================================================================
CLASS REFERENCE
===============================================================================

class EmptyObject:
    - A generic object blueprint used for game entities like ships, missiles,
      particles, etc.
    - Attributes: position (h, v), direction, color (rgb), lives, speed, score
    - Typically used as a placeholder or default object

FUNCTIONS AND GLOBALS:
----------------------
- LoadConfigData():
    ▸ Reads scores, display settings, and dimensions from `ClockConfig.ini`.
- Global configuration values:
    ▸ HatWidth / HatHeight: Display dimensions
    ▸ Gamma: Controls color brightness correction
    ▸ DotMatrix / ScreenArray: Core pixel state buffers
    ▸ Clock and overlay constants for positioning

NOTES:
------
- All pixel rendering should use `setpixel()` to ensure buffer updates.
- Sprites should be drawn centered (not from corners).
- Avoid `.SetPixel()` direct calls; rely on `ScreenArray` for tracking state.

"""



# Methods of writing to the screen
# We write to the LED directly for simplicity
# We write to the Canvas and swap to the LED for speed
# We write to the ScreenArray buffer so we know what is on the screen in case we
# need to check it

# Patreon - Multiprocessing - Port 5050
# We launch a process to monitor port 5050 using Flask.  This is the port we have set up to 
# listen for Patreon traffic.
# Telebit:  5050.YourTelebitAddress.telebit.io
#
# Twitch - EventSub - Port 5051
# Using Asyncio Client we start a task that subscribes to twitch events.
# Telebit:  5051.YourTelebitAddress.telebit.io
#


#------------------------------------------------------------------------------
#   _     _____ ____                          _                              --
#  | |   | ____|  _ \  __ _ _ __ ___ __ _  __| | ___                         --
#  | |   |  _| | | | |/ _` | '__/ __/ _` |/ _` |/ _ \                        --
#  | |___| |___| |_| | (_| | | | (_| (_| | (_| |  __/                        --
#  |_____|_____|____/ \__,_|_|  \___\__,_|\__,_|\___|                        --
#                                                                            --
#                                                                            --
#   This is a collection of classes and functions derived from the           --
#   Arcade Retro Clock RGB project.                                          --
#                                                                            --
#   This project will enable you to display animated text and sprites on     --
#   LED display attached to a Raspberry Pi computer.                         --
#                                                                            --
#                                                                            --
#   Copyright 2021 William McEvoy                                            --
#                                                                            --
#------------------------------------------------------------------------------
#   Version: 1.0                                                             --
#   Date:    October 4, 2020                                                 --
#   Reason:  Initial Creation                                                --
#------------------------------------------------------------------------------

import time


print("")
print("==========================================")
print("== IMPORTING LEDarcade                  ==")
print("==========================================")
print("")


import gc
import random
import os

from configparser import SafeConfigParser
import sys

#to help with debugging
import inspect



#RGB Matrix and graphics
from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
from PIL import Image, ImageDraw, ImageFont, ImageSequence


TheMatrix = None
Canvas    = None



#URL
import urllib.request
import io



from datetime import datetime, timedelta
from random import randint
import argparse
import copy
import numpy
from numba import njit
import numpy as np


import math
import subprocess
import traceback
#import unicornhathd as unicorn

#For capturing keypresses
import curses

#Crypto
#from pycoingecko import CoinGeckoAPI

#JSON
import requests
#import simplejson as json

#Asynchronous / Multiprocessing
import asyncio
#import multiprocessing as MPM



#--------------------------------------
# Global Variables                   --
#--------------------------------------

KeyboardSpeed  = 2000
ConfigFileName = "ClockConfig.ini"

MainSleep        = 0
FlashSleep       = 0
PacSleep         = 0.01
ScrollSleep      = 0.03
TinyClockStartHH = 0
TinyClockHours   = 0
CPUModifier      = 0
Gamma            = 1
ShowCrypto       = 'N'
HatWidth         = 32  # These defaults can be overwritten in the ClockConfig.ini file
HatHeight        = 32  # These defaults can be overwritten in the ClockConfig.ini file
KeyboardPoll     = 10
BrightColorCount = 27


DotMatrix = [[0 for x in range(HatHeight)] for y in range(HatWidth)] 





#-----------------------------
# Timers                    --
#-----------------------------
StartTime = time.time()




if(HatWidth > 64):
  HorizAdjust = 32
else:
  HorizAdjust = 0

#Sprite display locations
ClockH,      ClockV,      ClockRGB      = 0  + HorizAdjust,0,  (0,150,0)
DayOfWeekH,  DayOfWeekV,  DayOfWeekRGB  = 10 + HorizAdjust,20, (125,20,20)
MonthH,      MonthV,      MonthRGB      = 30 + HorizAdjust,20, (125,30,0)
DayOfMonthH, DayOfMonthV, DayOfMonthRGB = 49 + HorizAdjust,20, (115,40,10)
CurrencyH,   CurrencyV,   CurrencyRGB   = 56 + HorizAdjust,20, (0,150,0)


#Sprite filler tuple
SpriteFillerRGB = (0,0,0)



#Screen array is a copy of the matrix light layout because RGBMatrix is not queryable.  
ScreenArray  = ([[]])
ScreenArray  = [[ (0,0,0) for i in range(HatWidth)] for i in range(HatHeight)]

EmptyArray  = ([[]])
EmptyArray  = [[ (0,0,0) for i in range(HatWidth)] for i in range(HatHeight)]











#------------------------------------------------------------------------------
# COLORS                                                                     --
#------------------------------------------------------------------------------

#This section evolved and came out of several different video games (SDColor = SpaceDotColor for example) so the
#names are not always clear.  Obvious names are useful, use any combination you like.

#There are many colors defined here
#some as three separate values representing R,G,b
#some as tubles (R,G,B)
# YellowR, YellowG, YellowB would be used as  color = (YellowR, YellowG, YellowB)


def ApplyGamma(color,TheGamma):
  #Need to round to integer
  NewColor = int(color * TheGamma)
  
  if NewColor > 255: NewColor = 255
  
  #print ("Old:",color," New:",NewColor)
  return NewColor




#Yellow
YellowR = ApplyGamma(220,Gamma)
YellowG = ApplyGamma(220,Gamma)
YellowB = ApplyGamma(0,Gamma)

#Red
RedR = ApplyGamma(100,Gamma)
RedG = ApplyGamma(0,Gamma)
RedB = ApplyGamma(0,Gamma)

#HighRed
HighRedR = ApplyGamma(225,Gamma)
HighRedG = ApplyGamma(0,Gamma)
HighRedB = ApplyGamma(0,Gamma)

#MedRed
MedRedR = ApplyGamma(100,Gamma)
MedRedG = ApplyGamma(0,Gamma)
MedRedB = ApplyGamma(0,Gamma)

#Orange
OrangeR = ApplyGamma(100,Gamma)
OrangeG = ApplyGamma(50,Gamma)
OrangeB = ApplyGamma(0,Gamma)


#Purple
PurpleR = ApplyGamma(75,Gamma)
PurpleG = ApplyGamma(0,Gamma)
PurpleB = ApplyGamma(75,Gamma)

#Green
GreenR = ApplyGamma(0,Gamma)
GreenG = ApplyGamma(100,Gamma)
GreenB = ApplyGamma(0,Gamma)

#HighGreen
HighGreenR = ApplyGamma(0,Gamma)
HighGreenG = ApplyGamma(225,Gamma)
HighGreenB = ApplyGamma(0,Gamma)

#MedGreen
MedGreenR = ApplyGamma(0,Gamma)
MedGreenG = ApplyGamma(155,Gamma)
MedGreenB = ApplyGamma(0,Gamma)

#LowGreen
LowGreenR = ApplyGamma(0,Gamma)
LowGreenG = ApplyGamma(100,Gamma)
LowGreenB = ApplyGamma(0,Gamma)

#DarkGreen
DarkGreenR = ApplyGamma(0,Gamma)
DarkGreenG = ApplyGamma(45,Gamma)
DarkGreenB = ApplyGamma(0,Gamma)


#Blue
BlueR = ApplyGamma(0,Gamma)
BlueG = ApplyGamma(0,Gamma)
BlueB = ApplyGamma(100,Gamma)

#WhiteLow
WhiteLowR = ApplyGamma(45,Gamma)
WhiteLowG = ApplyGamma(45,Gamma)
WhiteLowB = ApplyGamma(45,Gamma)

#WhiteMed
WhiteMedR = ApplyGamma(100,Gamma)
WhiteMedG = ApplyGamma(100,Gamma)
WhiteMedB = ApplyGamma(100,Gamma)

#WhiteHigh
WhiteHighR = ApplyGamma(225,Gamma)
WhiteHighG = ApplyGamma(225,Gamma)
WhiteHighB = ApplyGamma(225,Gamma)

#Character Colors
PacR = ApplyGamma(YellowR,Gamma)
PacG = ApplyGamma(YellowG,Gamma)
PacB = ApplyGamma(YellowB,Gamma)


#Red
Ghost1R = ApplyGamma(150,Gamma)
Ghost1G = ApplyGamma(0,Gamma)
Ghost1B = ApplyGamma(0,Gamma)

#Orange
Ghost2R = ApplyGamma(130,Gamma)
Ghost2G = ApplyGamma(75,Gamma)
Ghost2B = ApplyGamma(0,Gamma)

#Purple
Ghost3R = ApplyGamma(125,Gamma)
Ghost3G = ApplyGamma(0,Gamma)
Ghost3B = ApplyGamma(125,Gamma)

#LightBlue
Ghost4R = ApplyGamma(0,Gamma)
Ghost4G = ApplyGamma(150,Gamma)
Ghost4B = ApplyGamma(150,Gamma)


#Dots
DotR = ApplyGamma(95,Gamma)
DotG = ApplyGamma(95,Gamma)
DotB = ApplyGamma(95,Gamma)

DotRGB = (DotR,DotG,DotB)

#Wall
WallR = ApplyGamma(10,Gamma)
WallG = ApplyGamma(10,Gamma)
WallB = ApplyGamma(100,Gamma)

WallRGB = (WallR,WallG,WallB)


#PowerPills
PillR = ApplyGamma(0,Gamma)
PillG = ApplyGamma(200,Gamma)
PillB = ApplyGamma(0,Gamma)

BlueGhostR = ApplyGamma(0,Gamma)
BlueGhostG = ApplyGamma(0,Gamma)
BlueGhostB = ApplyGamma(200,Gamma)






#HighRed
SDHighRedR = ApplyGamma(255,Gamma)
SDHighRedG = ApplyGamma(0,Gamma)
SDHighRedB = ApplyGamma(0,Gamma)


#MedRed
SDMedRedR = ApplyGamma(175,Gamma)
SDMedRedG = ApplyGamma(0,Gamma)
SDMedRedB = ApplyGamma(0,Gamma)


#LowRed
SDLowRedR = ApplyGamma(100,Gamma)
SDLowRedG = ApplyGamma(0,Gamma)
SDLowRedB = ApplyGamma(0,Gamma)

#DarkRed
SDDarkRedR = ApplyGamma(45,Gamma)
SDDarkRedG = ApplyGamma(0,Gamma)
SDDarkRedB = ApplyGamma(0,Gamma)

# Red RGB Tuples
HighRed = (SDHighRedR,SDHighRedG,SDHighRedB)
MedRed  = (SDMedRedR ,SDMedRedG ,SDMedRedB)
LowRed  = (SDLowRedR ,SDLowRedG ,SDLowRedB)
DarkRed = (SDDarkRedR,SDDarkRedG,SDDarkRedB)
ShadowRed = (25,0,0)


#HighOrange
SDHighOrangeR = ApplyGamma(255,Gamma)
SDHighOrangeG = ApplyGamma(128,Gamma)
SDHighOrangeB = ApplyGamma(0,Gamma)

#MedOrange
SDMedOrangeR = ApplyGamma(200,Gamma)
SDMedOrangeG = ApplyGamma(100,Gamma)
SDMedOrangeB = ApplyGamma(0,Gamma)

#LowOrange
SDLowOrangeR = ApplyGamma(155,Gamma)
SDLowOrangeG = ApplyGamma(75,Gamma)
SDLowOrangeB = ApplyGamma(0,Gamma)

#DarkOrange
SDDarkOrangeR = ApplyGamma(100,Gamma)
SDDarkOrangeG = ApplyGamma(45,Gamma)
SDDarkOrangeB = ApplyGamma(0,Gamma)

HighOrange = (SDHighOrangeR,SDHighOrangeG,SDHighOrangeB)
MedOrange  = (SDMedOrangeR, SDMedOrangeG, SDMedOrangeB)
LowOrange  = (SDLowOrangeR, SDLowOrangeG, SDLowOrangeB)
DarkOrange = (SDDarkOrangeR,SDDarkOrangeG,SDDarkOrangeB)
ShadowOrange = (50,20,0)

# High = (R,G,B)
# Med  = (R,G,B)
# Low  = (R,G,B)
# Dark = (R,G,B)


#SDHighPurple
SDHighPurpleR = ApplyGamma(230,Gamma)
SDHighPurpleG = ApplyGamma(0,Gamma)
SDHighPurpleB = ApplyGamma(255,Gamma)

#MedPurple
SDMedPurpleR = ApplyGamma(105,Gamma)
SDMedPurpleG = ApplyGamma(0,Gamma)
SDMedPurpleB = ApplyGamma(155,Gamma)

#SDLowPurple
SDLowPurpleR = ApplyGamma(75,Gamma)
SDLowPurpleG = ApplyGamma(0,Gamma)
SDLowPurpleB = ApplyGamma(120,Gamma)


#SDDarkPurple
SDDarkPurpleR = ApplyGamma(45,Gamma)
SDDarkPurpleG = ApplyGamma(0,Gamma)
SDDarkPurpleB = ApplyGamma(45,Gamma)

# Purple RGB Tuples
HighPurple = (SDHighPurpleR,SDHighPurpleG,SDHighPurpleB)
MedPurple  = (SDMedPurpleR ,SDMedPurpleG ,SDMedPurpleB)
LowPurple  = (SDLowPurpleR ,SDLowPurpleG ,SDLowPurpleB)
DarkPurple = (SDDarkPurpleR,SDDarkPurpleG,SDDarkPurpleB)
ShadowPurple = (25,0,25)





#HighGreen
SDHighGreenR = ApplyGamma(0,Gamma)
SDHighGreenG = ApplyGamma(255,Gamma)
SDHighGreenB = ApplyGamma(0,Gamma)

#MedGreen
SDMedGreenR = ApplyGamma(0,Gamma)
SDMedGreenG = ApplyGamma(200,Gamma)
SDMedGreenB = ApplyGamma(0,Gamma)

#LowGreen
SDLowGreenR = ApplyGamma(0,Gamma)
SDLowGreenG = ApplyGamma(100,Gamma)
SDLowGreenB = ApplyGamma(0,Gamma)

#DarkGreen
SDDarkGreenR = ApplyGamma(0,Gamma)
SDDarkGreenG = ApplyGamma(45,Gamma)
SDDarkGreenB = ApplyGamma(0,Gamma)

#Green tuples
HighGreen = (SDHighGreenR,SDHighGreenG,SDHighGreenB)
MedGreen  = (SDMedGreenR,SDMedGreenG,SDMedGreenB)
LowGreen  = (SDLowGreenR,SDLowGreenG,SDLowGreenB)
DarkGreen = (SDDarkGreenR,SDDarkGreenG,SDDarkGreenB)
ShadowGreen = (0,35,0)




#HighBlue
SDHighBlueR = ApplyGamma(0,Gamma)
SDHighBlueG = ApplyGamma(0,Gamma)
SDHighBlueB = ApplyGamma(255,Gamma)


#MedBlue
SDMedBlueR = ApplyGamma(0,Gamma)
SDMedBlueG = ApplyGamma(0,Gamma)
SDMedBlueB = ApplyGamma(175,Gamma)

#LowBlue
SDLowBlueR = ApplyGamma(0,Gamma)
SDLowBlueG = ApplyGamma(0,Gamma)
SDLowBlueB = ApplyGamma(100,Gamma)

#DarkBlue
SDDarkBlueR = ApplyGamma(0,Gamma)
SDDarkBlueG = ApplyGamma(0,Gamma)
SDDarkBlueB = ApplyGamma(45,Gamma)


# Blue RGB Tuples
HighBlue = (SDHighBlueR,SDHighBlueG,SDHighBlueB)
MedBlue  = (SDHighBlueR,SDHighBlueG,SDHighBlueB)
LowBlue  = (SDHighBlueR,SDHighBlueG,SDHighBlueB)
DarkBlue = (SDHighBlueR,SDHighBlueG,SDHighBlueB)
ShadowBlue = (0,0,25)


#WhiteMax
SDMaxWhiteR = ApplyGamma(255,Gamma)
SDMaxWhiteG = ApplyGamma(255,Gamma)
SDMaxWhiteB = ApplyGamma(255,Gamma)

#WhiteHigh
SDHighWhiteR = ApplyGamma(255,Gamma)
SDHighWhiteG = ApplyGamma(255,Gamma)
SDHighWhiteB = ApplyGamma(255,Gamma)

#WhiteMed
SDMedWhiteR = ApplyGamma(150,Gamma)
SDMedWhiteG = ApplyGamma(150,Gamma)
SDMedWhiteB = ApplyGamma(150,Gamma)

#WhiteLow
SDLowWhiteR = ApplyGamma(100,Gamma)
SDLowWhiteG = ApplyGamma(100,Gamma)
SDLowWhiteB = ApplyGamma(100,Gamma)

#WhiteDark
SDDarkWhiteR = ApplyGamma(35,Gamma)
SDDarkWhiteG = ApplyGamma(35,Gamma)
SDDarkWhiteB = ApplyGamma(35,Gamma)


# White RGB Tuples
MaxWhite  = (SDMaxWhiteR,SDMaxWhiteG,SDMaxWhiteB)
HighWhite = (SDHighWhiteR,SDHighWhiteG,SDHighWhiteB)
MedWhite  = (SDHighWhiteR,SDHighWhiteG,SDHighWhiteB)
LowWhite  = (SDHighWhiteR,SDHighWhiteG,SDHighWhiteB)
DarkWhite = (SDHighWhiteR,SDHighWhiteG,SDHighWhiteB)
ShadowWhite = (15,15,15)


#YellowMax
SDMaxYellowR = ApplyGamma(255,Gamma)
SDMaxYellowG = ApplyGamma(255,Gamma)
SDMaxYellowB = ApplyGamma(0,Gamma)


#YellowHigh
SDHighYellowR = ApplyGamma(215,Gamma)
SDHighYellowG = ApplyGamma(215,Gamma)
SDHighYellowB = ApplyGamma(0,Gamma)

#YellowMed
SDMedYellowR = ApplyGamma(175,Gamma)
SDMedYellowG = ApplyGamma(175,Gamma)
SDMedYellowB = ApplyGamma(0,Gamma)

#YellowLow
SDLowYellowR = ApplyGamma(100,Gamma)
SDLowYellowG = ApplyGamma(100,Gamma)
SDLowYellowB = ApplyGamma(0,Gamma)


#YellowDark
SDDarkYellowR = ApplyGamma(55,Gamma)
SDDarkYellowG = ApplyGamma(55,Gamma)
SDDarkYellowB = ApplyGamma(0,Gamma)


# Yellow RGB Tuples
MaxYellow  = (SDMaxYellowR,SDMaxYellowG,SDMaxYellowB)
HighYellow = (SDHighYellowR,SDHighYellowG,SDHighYellowB)
MedYellow  = (SDMedYellowR,SDMedYellowG,SDMedYellowB)
LowYellow  = (SDLowYellowR,SDLowYellowG,SDLowYellowB)
DarkYellow = (SDDarkYellowR,SDDarkYellowG,SDDarkYellowB)
ShadowYellow = (30,30,0)


#Pink
SDMaxPinkR = ApplyGamma(155,Gamma)
SDMaxPinkG = ApplyGamma(0,Gamma)
SDMaxPinkB = ApplyGamma(130,Gamma)

SDHighPinkR = ApplyGamma(130,Gamma)
SDHighPinkG = ApplyGamma(0,Gamma)
SDHighPinkB = ApplyGamma(105,Gamma)

SDMedPinkR = ApplyGamma(100,Gamma)
SDMedPinkG = ApplyGamma(0,Gamma)
SDMedPinkB = ApplyGamma(75,Gamma)

SDLowPinkR = ApplyGamma(75,Gamma)
SDLowPinkG = ApplyGamma(0,Gamma)
SDLowPinkB = ApplyGamma(50,Gamma)

SDDarkPinkR = ApplyGamma(45,Gamma)
SDDarkPinkG = ApplyGamma(0,Gamma)
SDDarkPinkB = ApplyGamma(50,Gamma)


# Pink RGB Tuples
MaxPink  = (SDMaxPinkR,SDMaxPinkG,SDMaxPinkB)
HighPink = (SDHighPinkR,SDHighPinkG,SDHighPinkB)
MedPink  = (SDHighPinkR,SDHighPinkG,SDHighPinkB)
LowPink  = (SDHighPinkR,SDHighPinkG,SDHighPinkB)
DarkPink = (SDHighPinkR,SDHighPinkG,SDHighPinkB)
ShadowPink = (22,0,25)


#Cyan
SDMaxCyanR = ApplyGamma(0,Gamma)
SDMaxCyanG = ApplyGamma(255,Gamma)
SDMaxCyanB = ApplyGamma(255,Gamma)

SDHighCyanR = ApplyGamma(0,Gamma)
SDHighCyanG = ApplyGamma(150,Gamma)
SDHighCyanB = ApplyGamma(150,Gamma)

SDMedCyanR = ApplyGamma(0,Gamma)
SDMedCyanG = ApplyGamma(100,Gamma)
SDMedCyanB = ApplyGamma(100,Gamma)

SDLowCyanR = ApplyGamma(0,Gamma)
SDLowCyanG = ApplyGamma(75,Gamma)
SDLowCyanB = ApplyGamma(75,Gamma)

SDDarkCyanR = ApplyGamma(0,Gamma)
SDDarkCyanG = ApplyGamma(50,Gamma)
SDDarkCyanB = ApplyGamma(50,Gamma)

# Cyan RGB Tuples
MaxCyan  = (SDMaxCyanR,SDMaxCyanG,SDMaxCyanB)
HighCyan = (SDHighCyanR,SDHighCyanG,SDHighCyanB)
MedCyan  = (SDHighCyanR,SDHighCyanG,SDHighCyanB)
LowCyan  = (SDHighCyanR,SDHighCyanG,SDHighCyanB)
DarkCyan = (SDHighCyanR,SDHighCyanG,SDHighCyanB)
ShadowCyan = (0,20,20)




ColorList = []
ColorList.append((0,0,0))
# 1 2 3 4
ColorList.append((SDDarkWhiteR,SDDarkWhiteG,SDDarkWhiteB))
ColorList.append((SDLowWhiteR,SDLowWhiteG,SDLowWhiteB))
ColorList.append((SDMedWhiteR,SDMedWhiteG,SDMedWhiteB))
ColorList.append((SDHighWhiteR,SDHighWhiteG,SDHighWhiteB))

# 5 6 7 8
ColorList.append((SDDarkRedR,SDDarkRedG,SDDarkRedB))
ColorList.append((SDLowRedR,SDLowRedG,SDLowRedB))
ColorList.append((SDMedRedR,SDMedRedG,SDMedRedB))
ColorList.append((SDHighRedR,SDHighRedG,SDHighRedB))

# 9 10 11 12
ColorList.append((SDDarkGreenR,SDDarkGreenG,SDDarkGreenB))
ColorList.append((SDLowGreenR,SDLowGreenG,SDLowGreenB))
ColorList.append((SDMedGreenR,SDMedGreenG,SDMedGreenB))
ColorList.append((SDHighGreenR,SDHighGreenG,SDHighGreenB))

# 13 14 15 16
ColorList.append((SDDarkBlueR,SDDarkBlueG,SDDarkBlueB))
ColorList.append((SDLowBlueR,SDLowBlueG,SDLowBlueB))
ColorList.append((SDMedBlueR,SDMedBlueG,SDMedBlueB))
ColorList.append((SDHighBlueR,SDHighBlueG,SDHighBlueB))

# 17 18 19 20
ColorList.append((SDDarkOrangeR,SDDarkOrangeG,SDDarkOrangeB))
ColorList.append((SDLowOrangeR,SDLowOrangeG,SDLowOrangeB))
ColorList.append((SDMedOrangeR,SDMedOrangeG,SDMedOrangeB))
ColorList.append((SDHighOrangeR,SDHighOrangeG,SDHighOrangeB))

# 21 22 23 24
ColorList.append((SDDarkYellowR,SDDarkYellowG,SDDarkYellowB))
ColorList.append((SDLowYellowR,SDLowYellowG,SDLowYellowB))
ColorList.append((SDMedYellowR,SDMedYellowG,SDMedYellowB))
ColorList.append((SDHighYellowR,SDHighYellowG,SDHighYellowB))

# 25 26 27 28
ColorList.append((SDDarkPurpleR,SDDarkPurpleG,SDDarkPurpleB))
ColorList.append((SDLowPurpleR,SDLowPurpleG,SDLowPurpleB))
ColorList.append((SDMedPurpleR,SDMedPurpleG,SDMedPurpleB))
ColorList.append((SDHighPurpleR,SDHighPurpleG,SDHighPurpleB))

# 29 30 31 32 33
ColorList.append((SDDarkPinkR,SDDarkPinkG,SDDarkPinkB))
ColorList.append((SDLowPinkR,SDLowPinkG,SDLowPinkB))
ColorList.append((SDMedPinkR,SDMedPinkG,SDMedPinkB))
ColorList.append((SDHighPinkR,SDHighPinkG,SDHighPinkB))
ColorList.append((SDMaxPinkR,SDMaxPinkG,SDMaxPinkB))


# 34 35 36 37 38
ColorList.append((SDDarkCyanR,SDDarkCyanG,SDDarkCyanB))
ColorList.append((SDLowCyanR,SDLowCyanG,SDLowCyanB))
ColorList.append((SDMedCyanR,SDMedCyanG,SDMedCyanB))
ColorList.append((SDHighCyanR,SDHighCyanG,SDHighCyanB))
ColorList.append((SDMaxCyanR,SDMaxCyanG,SDMaxCyanB))


# MAX
# 39 40 41 42 43 44 45
ColorList.append((255,  0,  0))  #MAX-RED    39
ColorList.append((  0,255,  0))  #MAX-GREEN  40
ColorList.append((  0,  0,255))  #MAX-BLUE   41
ColorList.append((255,255,0  ))  #MAX-YELLOW 42
ColorList.append((255,  0,255))  #MAX-PURPLE 43
ColorList.append((  0,255,255))  #MAX-CYAN   44
ColorList.append((255,255,255))  #MAX-WHITE  45

#max orange is 20

ColorList.append((SDMaxCyanR,SDMaxCyanG,SDMaxCyanB))



GlowingTextRGB   = []
GlowingShadowRGB = []

GlowingTextRGB.append((250,250,250)) #WHITE
GlowingTextRGB.append((200,  0,  0)) #RED
GlowingTextRGB.append((  0,200,  0)) #Green
GlowingTextRGB.append((  0,  0,200)) #Blue
GlowingTextRGB.append((200,200,  0)) #Yellow
GlowingTextRGB.append((200,  0,200)) #Purple
GlowingTextRGB.append((  0,200,200)) #Cyan
GlowingTextRGB.append((200,100,200)) #Orange

GlowingShadowRGB.append(( 20, 20, 20)) #WHITE
GlowingShadowRGB.append(( 20,  0,  0)) #RED
GlowingShadowRGB.append((  0, 20,  0)) #Green
GlowingShadowRGB.append((  0,  0, 20)) #Blue
GlowingShadowRGB.append(( 20, 20,  0)) #Yellow
GlowingShadowRGB.append(( 20,  0, 20)) #Purple
GlowingShadowRGB.append((  0, 20, 20)) #Cyan
GlowingShadowRGB.append(( 20, 10,  0)) #Orange




# MAX
# 39 40 41 42 43 44 45
ColorList.append((255,  0,  0))  #MAX-RED    39
ColorList.append((  0,255,  0))  #MAX-GREEN  40
ColorList.append((  0,  0,255))  #MAX-BLUE   41
ColorList.append((255,255,0  ))  #MAX-YELLOW 42
ColorList.append((255,  0,255))  #MAX-PURPLE 43
ColorList.append((  0,255,255))  #MAX-CYAN   44
ColorList.append((255,255,255))  #MAX-WHITE  45




BrightColorList = []
BrightColorList.append((0,0,0))
# 1 2 3
BrightColorList.append((SDLowWhiteR,SDLowWhiteG,SDLowWhiteB))
BrightColorList.append((SDMedWhiteR,SDMedWhiteG,SDMedWhiteB))
BrightColorList.append((SDHighWhiteR,SDHighWhiteG,SDHighWhiteB))

# 4 5 6
BrightColorList.append(LowRed)
BrightColorList.append(MedRed)
BrightColorList.append(HighRed)

# 7 8 9
BrightColorList.append((SDLowGreenR,SDLowGreenG,SDLowGreenB))
BrightColorList.append((SDMedGreenR,SDMedGreenG,SDMedGreenB))
BrightColorList.append((SDHighGreenR,SDHighGreenG,SDHighGreenB))

# 10 11 12
BrightColorList.append((SDLowBlueR,SDLowBlueG,SDLowBlueB))
BrightColorList.append((SDMedBlueR,SDMedBlueG,SDMedBlueB))
BrightColorList.append((SDHighBlueR,SDHighBlueG,SDHighBlueB))

# 13 14 15
BrightColorList.append((SDLowOrangeR,SDLowOrangeG,SDLowOrangeB))
BrightColorList.append((SDMedOrangeR,SDMedOrangeG,SDMedOrangeB))
BrightColorList.append((SDHighOrangeR,SDHighOrangeG,SDHighOrangeB))

# 16 17 18
BrightColorList.append((SDLowYellowR,SDLowYellowG,SDLowYellowB))
BrightColorList.append((SDMedYellowR,SDMedYellowG,SDMedYellowB))
BrightColorList.append((SDHighYellowR,SDHighYellowG,SDHighYellowB))

# 19 20 21
BrightColorList.append((SDLowPurpleR,SDLowPurpleG,SDLowPurpleB))
BrightColorList.append((SDMedPurpleR,SDMedPurpleG,SDMedPurpleB))
BrightColorList.append((SDHighPurpleR,SDHighPurpleG,SDHighPurpleB))

# 22 23 24
BrightColorList.append((SDMedPinkR,SDMedPinkG,SDMedPinkB))
BrightColorList.append((SDHighPinkR,SDHighPinkG,SDHighPinkB))
BrightColorList.append((SDMaxPinkR,SDMaxPinkG,SDMaxPinkB))


# 25 26 27
BrightColorList.append((SDMedCyanR,SDMedCyanG,SDMedCyanB))
BrightColorList.append((SDHighCyanR,SDHighCyanG,SDHighCyanB))
BrightColorList.append((SDMaxCyanR,SDMaxCyanG,SDMaxCyanB))


#Define color list
TextColorList = ((ShadowPurple,DarkPurple,LowPurple,MedPurple),
                  #(ShadowRed,   DarkRed,   LowRed,   MedRed),
                  (DarkRed,     LowRed,    MedRed,   HighRed),
                  (ShadowOrange,DarkOrange,LowOrange,MedOrange),
                  (ShadowYellow,DarkYellow,LowYellow,MedYellow),
                  #(ShadowGreen, DarkGreen, LowGreen, MedGreen),
                  (DarkGreen,   LowGreen,  MedGreen, HighGreen),
                  (ShadowBlue,  DarkBlue,  LowBlue,  MedBlue),
                  (ShadowPink,  DarkPink,  LowPink,  MedPink),
                  (ShadowCyan,  DarkCyan,  LowCyan,  MedCyan)

                  )







#ColorList.append((SDDarkR,SDDarkG,SDDarkB))
#ColorList.append((SDLowR,SDLowG,SDLowB))
#ColorList.append((SDMedR,SDMedG,SDMedB))
#ColorList.append((SDHighR,SDHighG,SDHighB))


#--> need to apply gamma to SD variables directly, as they are referenced later




# def ApplyGamma(r,g,b,Gamma):
  # NewR = r * Gamma
  # NewG = g * Gamma
  # NewB = b * Gamma
  
  # if NewR > 255: NewR = 255
  # if NewG > 255: NewG = 255
  # if NewB > 255: NewB = 255
  # print ("Old:",r,g,b," New:",NewR,NewG,NewB)
  # return NewR,NewG,NewB

# if (Gamma > 1):
  # for index in range(1,38):
    # r,g,b = ColorList[index]
    # r,g,b = ApplyGamma(r,g,b,Gamma)
    # ColorList[index] = r,g,b















#-----------------------------
# Arcade Games              --
#-----------------------------
DotInvadersHighScore   = 0
DotInvadersGamesPlayed = 0
OutbreakHighScore      = 0
OutbreakGamesPlayed    = 0
SpaceDotHighScore      = 0
SpaceDotGamesPlayed    = 0
DefenderGamesPlayed    = 0
DefenderHighScore      = 0





#Asteroids
#WaveStartV           = -5
#WaveMinSpeed         = 5     #The fastest the wave of asteroids can fall
#WaveSpeedRange       = 60    #how much variance in the wave speed min and max
AsteroidMinSpeed     = 30    #lower the number the faster the movement (based on ticks)
AsteroidMaxSpeed     = 60  
#AsteroidSpawnChance  = 100  #lower the number the greater the chance
WaveDropSpeed        = 550  #how often the next chunk of the wave is dropped
#MovesBetweenWaves    = 2000
AsteroidsInWaveMax   = 200
AsteroidsInWaveMin   = 5 
#AsteroidsToDropMin   = 1     #Number of asteroids to drop at a time
#AsteroidsToDropMax   = 5   #Number of asteroids to drop at a time





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





def ShowOnAir(StopEvent=None,duration=60):
    width  = HatWidth
    height = HatHeight

    def MakeMessageImage():
        msg = "ON AIR"

        # Create blank image and drawing context
        image = Image.new("RGB", (width, height), color=(255, 0, 0))  # Red background
        draw = ImageDraw.Draw(image)

        #draw shadow
        font = ImageFont.truetype("/home/pi/LEDarcade/fonts/Anton-Regular.ttf", 21)
        bbox = draw.textbbox((0, 0), msg, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (width - text_width) // 2
        y = (height - text_height) // 2 -bbox[1]
        draw.text((x, y), msg, font=font, fill=(0, 0, 0))  # black (for outline)


        #draw text
        font = ImageFont.truetype("/home/pi/LEDarcade/fonts/Anton-Regular.ttf", 20)
        # Measure text size and center it
        bbox = draw.textbbox((0, 0), msg, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (width - text_width) // 2
        y = (height - text_height) // 2 -bbox[1]
        draw.text((x, y), msg, font=font, fill=(255, 255, 255))  # black (for outline)

        return image



    # Display image using LEDarcade canvas
    image = MakeMessageImage()
    ScreenArray  = CopyImageToScreenArray(image, 0, 0)



    SpinShrinkTransition(ScreenArray, steps=32, delay=0.01, start_zoom=0, end_zoom=100)

    # Timer logic
    start_time = time.time()
    try:
        while True:
            if StopEvent and StopEvent.is_set():
                break
            if time.time() - start_time >= duration:
                break
            time.sleep(1)  # prevent busy loop
    except KeyboardInterrupt:
        TheMatrix.Clear()






#----------------------------
#-- Custom Clock Functions --
#----------------------------

def DisplayCustomFontClock(StopEvent=None):
    width  = HatWidth
    height = HatHeight

    def MakeTimeImage():
        now = datetime.now()
        current_minute = now.strftime("%H:%M")

        # Create blank image and drawing context
        image = Image.new("RGB", (width, height))
        draw = ImageDraw.Draw(image)

        # Measure text size and center it using textbbox
        bbox = draw.textbbox((0, 0), current_minute, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (width - text_width) // 2
        y = (height - text_height) // 4
        draw.text((x, y), current_minute, font=font, fill=(0, 200, 0))  # Red
        return image
        
    font = ImageFont.truetype("/home/pi/LEDarcade/fonts/CHECKBK0.TTF", 22)

    # Display image using LEDarcade canvas
    image = MakeTimeImage()
    ScreenArray  = CopyImageToScreenArray(image, 0, 0)
    ScreenArray2 = CopyImageToScreenArray(image, 0, 0)



    SpinShrinkTransition(ScreenArray, steps=32, delay=0.01, start_zoom=0, end_zoom=100)

    # Clock loop
    last_minute = None
    try:
        Done = False
        while Done == False:
            if StopEvent and StopEvent.is_set():
                Done = True
                SpinShrinkTransition(ScreenArray, steps=32, delay=0.01, start_zoom=100, end_zoom=0)

                break


            now = datetime.now()
            current_minute = now.strftime("%H:%M")

            if current_minute != last_minute:
                image = MakeTimeImage()
                ScreenArray  = CopyImageToScreenArray(image, 0, 0)
                TransitionBetweenScreenArrays(ScreenArray2,ScreenArray,TransitionType=2,FadeSleep=0.02)

            time.sleep(1)
            last_minute = current_minute
            ScreenArray2 = CopyImageToScreenArray(image, 0, 0)



    except KeyboardInterrupt:
        TheMatrix.Clear()


#----------------------------
#-- Custom Clock Functions --
#----------------------------

def DisplayCustomFontClock(StopEvent=None):
    width  = HatWidth
    height = HatHeight

    def MakeTimeImage():
        now = datetime.now()
        current_minute = now.strftime("%H:%M")

        # Create blank image and drawing context
        image = Image.new("RGB", (width, height))
        draw = ImageDraw.Draw(image)

        # Measure text size and center it using textbbox
        bbox = draw.textbbox((0, 0), current_minute, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (width - text_width) // 2
        y = (height - text_height) // 4
        draw.text((x, y), current_minute, font=font, fill=(0, 200, 0))  # Red
        return image
        
    font = ImageFont.truetype("/home/pi/LEDarcade/fonts/CHECKBK0.TTF", 22)

    # Display image using LEDarcade canvas
    image = MakeTimeImage()
    ScreenArray  = CopyImageToScreenArray(image, 0, 0)
    ScreenArray2 = CopyImageToScreenArray(image, 0, 0)



    SpinShrinkTransition(ScreenArray, steps=32, delay=0.01, start_zoom=0, end_zoom=100)

    # Clock loop
    last_minute = None
    try:
        Done = False
        while Done == False:
            if StopEvent and StopEvent.is_set():
                Done = True
                SpinShrinkTransition(ScreenArray, steps=32, delay=0.01, start_zoom=100, end_zoom=0)

                break


            now = datetime.now()
            current_minute = now.strftime("%H:%M")

            if current_minute != last_minute:
                image = MakeTimeImage()
                ScreenArray  = CopyImageToScreenArray(image, 0, 0)
                TransitionBetweenScreenArrays(ScreenArray2,ScreenArray,TransitionType=2,FadeSleep=0.02)

            time.sleep(1)
            last_minute = current_minute
            ScreenArray2 = CopyImageToScreenArray(image, 0, 0)



    except KeyboardInterrupt:
        TheMatrix.Clear()








def GenerateClockImage(FontPath="/home/pi/LEDarcade/fonts/CHECKBK0.TTF", FontSize=12, TextColor=(0, 200, 0), BackgroundColor=(0, 0, 0)):
    """
    Generates a PIL image of the current time in HH:MM format using the given font and size.

    Parameters:
        FontPath (str): Path to the .ttf font file.
        FontSize (int): Desired font size.
        TextColor (tuple): RGB tuple for the text color.
        BackgroundColor (tuple): RGB tuple for the background color.

    Returns:
        Image: PIL Image object with the rendered clock.
    """
    now = datetime.now()
    time_str = now.strftime("%H:%M")

    # Load font
    font = ImageFont.truetype(FontPath, FontSize)

    # Create temporary image to calculate text size
    temp_img = Image.new("RGB", (1, 1))
    draw = ImageDraw.Draw(temp_img)
    bbox = draw.textbbox((0, 0), time_str, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # Create actual image with just enough size to fit text
    image = Image.new("RGB", (text_width, text_height), BackgroundColor)
    draw = ImageDraw.Draw(image)
    draw.text((0, 0), time_str, font=font, fill=TextColor)

    return image






from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

def GenerateClockImageWithFixedTiles(FontPath="/home/pi/LEDarcade/fonts/CHECKBK0.TTF",
                                     FontSize=12,
                                     TextColor=(0, 200, 0),
                                     BackgroundColor=(0, 0, 0),
                                     TileSize=None,
                                     Text=None):
    """
    Generates a clock image (HH:MM) using variable-width font rendered per character,
    padded into fixed-size tiles. The colon ':' uses a half-width tile.

    Parameters:
        FontPath (str): Path to .ttf font file.
        FontSize (int): Font size.
        TextColor (tuple): RGB color for the text.
        BackgroundColor (tuple): RGB color for padding.
        TileSize (tuple or None): Optional (tile_width, tile_height). If None, auto-calculated.
        Text (str): Optional override for testing (e.g., "12:45")

    Returns:
        PIL.Image: Final composed clock image
    """

    # Step 1: Determine time string
    time_str = Text if Text else datetime.now().strftime("%H:%M")

    # Step 2: Load font
    font_key = (FontPath, FontSize)
    if not hasattr(GenerateClockImageWithFixedTiles, "_font_cache"):
        GenerateClockImageWithFixedTiles._font_cache = {}

    if font_key not in GenerateClockImageWithFixedTiles._font_cache:
        GenerateClockImageWithFixedTiles._font_cache[font_key] = ImageFont.truetype(FontPath, FontSize)

    font = GenerateClockImageWithFixedTiles._font_cache[font_key]

    # Step 3: Measure max width/height if TileSize not provided
    if TileSize is None:
        max_width = 0
        max_height = 0
        for char in "0123456789:":
            img = Image.new("RGB", (1, 1))
            draw = ImageDraw.Draw(img)
            bbox = draw.textbbox((0, 0), char, font=font)
            char_w = bbox[2] - bbox[0]
            char_h = bbox[3] - bbox[1]
            max_width = max(max_width, char_w)
            max_height = max(max_height, char_h)
        tile_width = max_width
        tile_height = max_height
    else:
        tile_width, tile_height = TileSize

    colon_tile_width = tile_width // 2

    # Step 4: Build tiles
    char_tiles = []
    char_widths = []

    for char in time_str:
        this_tile_width = colon_tile_width if char == ":" else tile_width

        # Measure character bounds
        temp_img = Image.new("RGB", (1, 1))
        draw = ImageDraw.Draw(temp_img)
        bbox = draw.textbbox((0, 0), char, font=font)
        char_w = bbox[2] - bbox[0]
        char_h = bbox[3] - bbox[1]

        # Create minimal character image
        char_img = Image.new("RGB", (char_w, char_h), BackgroundColor)
        draw = ImageDraw.Draw(char_img)
        draw.text((-bbox[0], -bbox[1]), char, font=font, fill=TextColor)

        # Paste into tile
        tile_img = Image.new("RGB", (this_tile_width, tile_height), BackgroundColor)
        x_offset = (this_tile_width - char_w) // 2
        y_offset = (tile_height - char_h) // 2
        tile_img.paste(char_img, (x_offset, y_offset))

        char_tiles.append(tile_img)
        char_widths.append(this_tile_width)

    # Step 5: Assemble clock image
    total_width = sum(char_widths)
    clock_img = Image.new("RGB", (total_width, tile_height), BackgroundColor)

    x_cursor = 0
    for tile, width in zip(char_tiles, char_widths):
        clock_img.paste(tile, (x_cursor, 0))
        x_cursor += width

    return clock_img

#-----------------------------
# Used in all games         --
#-----------------------------

class EmptyObjectClass(object):
  def __init__(self,name='EmptyObject'):
    self.name  = name
    self.alive = 0
    self.lives = 0
    self.direction = 0
    self.h          = -1 
    self.v          = -1
    self.r          = 0
    self.g          = 0
    self.b          = 0
    self.rgb        = (0,0,0)
    self.scandirection = 0
    self.speed      = 0
    self.score      = 0
    self.exploding  = 0
    self.dropped    = 0

EmptyObject       = EmptyObjectClass()
OutOfBoundsObject = EmptyObjectClass()
OutOfBoundsObject.name = 'OutOfBounds'




RedR = 0
RedG = 0
RedB = 0



def get_process_id():
    PID = os.getpid()
    #print("Current PID:", PID)
    return PID




def LoadConfigData():
  global DotInvadersHighScore
  global DotInvadersGamesPlayed
  global OutbreakHighScore
  global OutbreakGamesPlayed
  global SpaceDotHighScore
  global SpaceDotGamesPlayed
  global DefenderHighScore
  global DefenderGamesPlayed
  global HatHeight
  global HatWidth
  
  PID = get_process_id()
  print (f"{PID} --Load Config Data--")
  #print ("PacDotHighScore Before Load: ",PacDotHighScore)
    
  if (os.path.exists(ConfigFileName)):
    print (f"{PID}Config file (",ConfigFileName,"): already exists")
    ConfigFile = SafeConfigParser()
    ConfigFile.read(ConfigFileName)

    #Get and set time    
    #TheTime = ConfigFile.get("main","currenttime")
    #print ("Setting time: ",TheTime)
    #CMD = "sudo date --set " + TheTime
    #os.system(CMD)
   
    #Get pacdot data
    #PacDotHighScore   = ConfigFile.get("pacdot","PacdotHighScore")
    #PacDotGamesPlayed = int(ConfigFile.get("pacdot","PacdotGamesPlayed"))
    #print ("PacDotHighScore: ",  PacDotHighScore)
    #print ("PacDotGamesPlayed: ",PacDotGamesPlayed)

    #Get CryptoBalance
    #CryptoBalance = ConfigFile.get("crypto","balance")
    #print ("CryptoBalance:   ",CryptoBalance)

    #Get DotInvadersHighScore
    DotInvadersHighScore   = int(ConfigFile.get("scores","DotInvadersHighScore"))
    DotInvadersGamesPlayed = int(ConfigFile.get("scores","DotInvadersGamesPlayed"))
    print (f"{PID} DotInvadersHighScore:   ",DotInvadersHighScore)
    print (f"{PID} DotInvadersGamesPlayed: ",DotInvadersGamesPlayed)


    try:
      HatHeight   = int(ConfigFile.get("MATRIX","HatHeight"))
      HatWidth    = int(ConfigFile.get("MATRIX","HatWidth"))
    except:
      print(f"{PID} No override for HatHeight/HatWidth.  Going with defaults.")
      
    
    
    print(f"{PID} HatWidth:               ",HatWidth)
    print(f"{PID} HatHeight               ",HatHeight)
      




    #Get Outbreak data
    OutbreakHighScore   = int(ConfigFile.get("scores","OutbreakHighScore"))
    OutbreakGamesPlayed = int(ConfigFile.get("scores","OutbreakGamesPlayed"))
    print (f"{PID} OutbreakHighScore:      ",OutbreakHighScore)
    print (f"{PID} OutbreakGamesPlayed:    ",OutbreakGamesPlayed)


    #Get SpaceDot data
    SpaceDotHighScore   = int(ConfigFile.get("scores","SpaceDotHighScore"))
    SpaceDotGamesPlayed = int(ConfigFile.get("scores","SpaceDotGamesPlayed"))
    print (f"{PID} SpaceDotHighScore:      ",SpaceDotHighScore)
    print (f"{PID} SpaceDotGamesPlayed:    ",SpaceDotGamesPlayed)


    #Get Defender data
    DefenderHighScore   = int(ConfigFile.get("scores","DefenderHighScore"))
    DefenderGamesPlayed = int(ConfigFile.get("scores","DefenderGamesPlayed"))
    print (f"{PID} DefenderHighScore:      ",DefenderHighScore)
    print (f"{PID} DefenderGamesPlayed:    ",DefenderGamesPlayed)


  else:
    print (f"{PID} Config file not found! Running with default values.")

    
  print (f"{PID} --------------------")
  print (" ")
  








 

#------------------------------------------------------------------------------
#                                                                            --
# BIG LED FUNCTIONS                                                          --
#                                                                            --
#------------------------------------------------------------------------------

def ClearBigLED():
  TheMatrix.Clear()


def ClearBuffers():
  #There are TWO buffers.  One is built into the API, and we can write to it but not query it.  That is the Canvas.
  #The second one is ScreenArray, which is our own version, kept up to date when we draw to the Canvas or the Matrix.


  global ScreenArray

  ScreenArray  = [[]]
  ScreenArray  = [[ (0,0,0) for i in range(HatWidth)] for i in range(HatHeight)]
  Canvas.Clear()






#------------------------------------------------------------------------------
#   ____ _                                                                   --
#  / ___| | __ _ ___ ___  ___  ___                                           --
# | |   | |/ _` / __/ __|/ _ \/ __|                                          --
# | |___| | (_| \__ \__ \  __/\__ \                                          --
#  \____|_|\__,_|___/___/\___||___/                                          --
#                                                                            --
#------------------------------------------------------------------------------


#TheMatrix = the LED hardware
#TheMatrix.setpixel() is the library function to set the value of the pixel (immediate display)
#setpixel() is my function that will set the matrix pixel AND our addressable screen copy ScreenArray
# Canvas is a built in buffer that we can write to without affecting TheMatrix
# when we are done writing we do execute SwapOnVSync(Canvas)
#
#   Canvas.SetPixel(H,V,fr,fg,fb)
#   ScreenArray[V][H]=(fr,fg,fb)
#
#   TheMatrix.SwapOnVSync(Canvas)
#


#Update the matrix and the buffer with the contents of a buffer
def setpixels(TheBuffer):
  x = 0
  y = 0

  #Copy our old buffer to the new LED buffer.  This will be replaced.
  #ScreenArray = TheBuffer

  for y in range (HatHeight):
    for x in range (HatWidth):
      r,g,b = TheBuffer[y][x]
      setpixel(x,y,r,g,b)



      
def setpixelsWithClock(TheBuffer,ClockSprite,h,v):
  x = 0
  y = 0

  for y in range (HatHeight):
    for x in range (HatWidth):
      if (x >= h and x <= h+ClockSprite.width) and (y >= v and y <= v+ClockSprite.height):
        r = ClockSprite.r
        g = ClockSprite.g
        b = ClockSprite.b
      else:
        r,g,b = TheBuffer[y][x]
      setpixel(x,y,r,g,b)



      
      

def setpixel(x, y, r, g, b):
  #This writes to the LED physical screen directly, and to the in-memory copy called ScreenArray (which can be qeuried unlike the physical screen)
  #This does NOT make use of buffer swaps (canvas) and should be used with cuation
  global ScreenArray

  if (CheckBoundary(x,y) == 0):
    TheMatrix.SetPixel(x,y,r,g,b)
    ScreenArray[y][x] = (r,g,b)



def setpixelCanvas(x, y, r, g, b):
  global ScreenArray
  global Canvas


  if (CheckBoundary(x,y) == 0):
    Canvas.SetPixel(x,y,r,g,b)
    ScreenArray[y][x] = (r,g,b)




    
def setpixelRGB(x, y, RGB):
  global ScreenArray
  r,g,b = RGB
  if (CheckBoundary(x,y) == 0):
    TheMatrix.SetPixel(x,y,r,g,b)
    ScreenArray[y][x] = (r,g,b)
    

def setpixelsLED(TheBuffer):
  x = 0
  y = 0

  for y in range (HatHeight):
    for x in range (HatWidth):
      
      r,g,b = TheBuffer[y][x]
      TheMatrix.SetPixel(x,y,r,g,b)


def setpixelLEDOnly(x, y, r,g,b):
  global TheMatrix
  TheMatrix.SetPixel(x,y,r,g,b)
  



#Bug fix because my HD is inverted horizontally
def getpixel(h,v):
  #print ("get hv:",h,v)
  r = 0
  g = 0
  b = 0
  #r,g,b = unicorn.get_pixel(abs(15-h),v)
  r,g,b = ScreenArray[v][h]
  #print("Get pixel HV RGB:",h,v,"-",r,g,b)
  return r,g,b      


def ShowScreenArray(InputScreenArray):
  for h in range (0,HatWidth):
    for v in range (0,HatHeight):
      r,g,b = InputScreenArray[v][h]
      #if (r + g + b > 0):
      TheMatrix.SetPixel(h,v,r,g,b)
        
        

def CopyScreenArrayToCanvas(ScreenArray,Canvas):
  for h in range (0,HatWidth):
    for v in range (0,HatHeight):
      TheColor = graphics.Color(ScreenArray[v][h])
      Canvas.SetPixel(h,v,TheColor)
  return Canvas


def CopyScreenArrayToCanvasVSync(ScreenArray):
  global Canvas
  global TheMatrix

  for h in range (0,HatWidth):
    for v in range (0,HatHeight):
      r,g,b = ScreenArray[v][h]
      Canvas.SetPixel(h,v,r,g,b)
  Canvas = TheMatrix.SwapOnVSync(Canvas)


#this one is used by functions that calculate velocity
#and utilize an off screen canvas (buffer) to reduce flickering
def SetBufferPixel(Buffer,x,y,r,g,b):
  h = round(x)
  v = round(y)
  if (CheckBoundary(h,v) == 0):
    Buffer[v][h] = (r,g,b)
  return Buffer
      


  
  
def ClockTimer(seconds):
  global StartTime
  elapsed_time = time.time() - StartTime
  elapsed_hours, rem = divmod(elapsed_time, 3600)
  elapsed_minutes, elapsed_seconds = divmod(rem, 60)
  #print("Elapsed Time: {:0>2}:{:0>2}:{:05.2f}".format(int(elapsed_hours),int(elapsed_minutes),elapsed_seconds),end="\r")

  if (elapsed_seconds >= seconds ):
    StartTime = time.time()
    return 1
  else:
    return 0
  


#def GetElapsedSeconds(starttime, seconds):
#  
#  elapsed_time = time.time() - starttime
#  elapsed_hours, rem = divmod(elapsed_time, 3600)
#  elapsed_minutes, elapsed_seconds = divmod(rem, 60)
#  #print("Elapsed Time: {:0>2}:{:0>2}:{:05.2f}".format(int(elapsed_hours),int(elapsed_minutes),elapsed_seconds),end="\r")
#  return elapsed_seconds


def GetElapsedTime(StartTime,StopTime):
    elapsed_time = StopTime - StartTime
    elapsed_hours, rem = divmod(elapsed_time, 3600)
    elapsed_minutes, elapsed_seconds = divmod(rem, 60)
    return(elapsed_hours,elapsed_minutes,round(elapsed_seconds))

  
  
  
  


# --------------------------
# -- Dot and Ship Sprites --
# --------------------------
      
      
class Dot(object):
  def __init__(self,h,v,r,g,b,direction,speed,alive,name,trail,score,maxtrail,erasespeed,HeadRGB=(100,100,100)):
    self.h          = h 
    self.v          = v
    self.r          = r
    self.g          = g
    self.b          = b
    self.direction  = direction
    self.speed      = speed
    self.alive      = 1
    self.name       = name
    self.trail      = [] # a list of tuples, holding hv coordinates of the dot trail
    self.score      = 0
    self.maxtrail   = 0
    self.erasespeed = erasespeed #sleep time for the erase trail function
    self.HeadRGB    = HeadRGB
    self.score      = 0




  def Display(self):
    #print("hv rgb",self.h,self.v,"-",self.r,self.g,self.b)

    TheMatrix.SetPixel(self.h,self.v,self.r,self.g,self.b)
    ScreenArray[self.v][self.h] = (self.r,self.g,self.b)


    #r,g,b = self.HeadRGB
    #TheMatrix.SetPixel(self.h,self.v,r,g,b)
    
      
  def EraseTrail(self,direction,flash):
    r = self.r
    g = self.g
    b = self.b
    
    
    #Turn trail bright, then gradually fade
    if (flash == 'flash'):
      for x in range(25):
        newr = r + (100) - (2*x-1)
        newg = g + (100) - (2*x-1)
        newb = b + (100) - (2*x-1)
        if (newr > 255):
          newr = 255
        if (newg > 255):
          newg = 255
        if (newb > 255):
          newb = 255
        if (newr < r):
          newr = r 
        if (newg < g):
          newg = g
        if (newb < b):
          newb = b
          
        for i,dot in enumerate(self.trail):
          h = dot[0]
          v = dot[1]
          TheMatrix.SetPixel(h,v,newr,newg,newb)
          ScreenArray[v][h] = (newr,newg,newb)
          

      
    #Erase 
    if (direction == 'forward'):
      #print ("Erasing Trail: forward")
      #for i,dot in enumerate(self.trail):

#--> we need a faster way to go through the trail

      count = len(self.trail)
      for i in range (0,count):
        h = self.trail[i][0]
        v = self.trail[i][1]
                        
        TheMatrix.SetPixel(h,v,255,255,255)
        time.sleep(self.erasespeed)
        TheMatrix.SetPixel(h,v,0,0,0)
        ScreenArray[v][h] = (0,0,0)
        

      
    else:
      print ("Erasing Trail: backward")
      count = len(self.trail)
      for i in range (count-1,0,-1):
        h = self.trail[i][0]
        v = self.trail[i][1]


      #for i,dot in reversed(list(enumerate(self.trail))):
        #h = dot[0]
        #v = dot[1]
        TheMatrix.SetPixel(h,v,255,255,255)
        
        time.sleep(self.erasespeed)
        TheMatrix.SetPixel(h,v,0,0,0)
        ScreenArray[v][h] = (0,0,0)


  def ReverseWorm(self):
    self.h,self.v = self.trail[0]
    self.trail.reverse()
    self.direction = ReverseDirection(self.direction)
    #ShowScreenArray()
      
  def ColorizeTrail(self,r,g,b):
    print ("Colorize Trail: this loop seems wrong.  ")
    for i,dot in enumerate(self.trail):
      h = dot[0]
      v = dot[1]
      TheMatrix.SetPixel(h,v,r,g,b)
      ScreenArray[v][h] = (r,g,b)

    time.sleep(self.erasespeed * 1.5)
    
  def DisplayTrail(self):
      count = len(self.trail)
      print ("Displaying Trail:",count," dots")
      for i in range (0,count):
        h = self.trail[i][0]
        v = self.trail[i][1]
                        
        TheMatrix.SetPixel(h,v,self.r,self.g,self.b)
        ScreenArray[v][h] = (self.r,self.g,self.b)




  def Resurrect(self):
    #This function is used to bring a superworm back from the dead

    #Find and empty spot
    resurrected = 'N'
    count       = 0
    
    while (resurrected == 'N' and count <= ResurrectionTries):
      count = count + 1
      h = random.randint(0,HatWidth-1)
      v = random.randint(0,HatHeight-1)
      r,g,b = getpixel(h,v)
      if (r == 0 and g == 0 and b == 0):
        resurrected = 'Y'
        self.alive     = 1
        self.h         = h
        self.v         = v
        self.direction = (random.randint(1,4))
        self.trail     = []
        self.trail     = [(h,v)]
        self.maxtrail  = ResurrectedMaxTrail
        self.speed     = StartSpeedLow
      
        print ("A holy resurrection!")


    return


  def IncreaseMaxTrailLength(self,length):
    if (self.maxtrail < MaxTrailLength):
      self.maxtrail = self.maxtrail + 1
      

  def SetStartingPoint(self):
    done = 'N'
    while (done == 'N'):
      h = random.randint(SuperWormStartMinH,SuperWormStartMaxH)
      v = random.randint(SuperWormStartMinV,SuperWormStartMaxV)
      r,g,b = getpixel(h,v)

      if (r == 0 and g == 0 and b == 0):
        self.h         = h
        self.v         = v
        done = 'Y'


  def TrimTrail(self):
    if (len(self.trail) >= self.maxtrail):
      h,v = self.trail[0]
      setpixel(h,v,0,0,0)
      del self.trail[0]


  def Kill(self):
    self.alive = 0
    self.EraseTrail('forward','flash')
    setpixel(self.h,self.v,0,0,0)

 






    """
    Represents a dynamic visual entity on the LED matrix, such as a player ship, enemy,
    missile, or interactive sprite. This class encapsulates both display-related attributes
    and game logic metadata for rendering, movement, collisions, and lifecycle tracking.

    Attributes:
    -----------
    H : int
        Current horizontal coordinate on the LED matrix.
    V : int
        Current vertical coordinate on the LED matrix.
    OldH : int
        Previous horizontal position (used for erase/redraw logic).
    OldV : int
        Previous vertical position.
    Dir : int
        Direction of movement (implementation-specific encoding).
    Speed : int
        How frequently the ship moves (e.g., ticks between updates).
    Score : int
        Points awarded when this ship is destroyed.
    Name : str
        Unique or descriptive label for debugging and game logic.
    Type : str
        Category or classification (e.g., "Missile", "Enemy", "Player").
    Group : str
        Used for collision filtering (e.g., avoid self-hit on missiles).
    FiredBy : str
        ID or name of the object that created this ship (for attribution).
    exploding : bool
        Indicates if this ship is currently in its explosion animation state.
    exploded : bool
        Flag marking the ship as destroyed and ready for cleanup.
    alive : bool
        Whether the ship is currently active and should be rendered/processed.
    lives : int
        Health or durability; reaching 0 sets `exploded = True`.
    missiles : int
        Number of missiles fired or attached to this ship.
    sprite : List[List[Tuple[int, int, int]]]
        2D RGB sprite array representing the ship's appearance.
    SpriteHeight : int
        Height in pixels of the current sprite.
    SpriteWidth : int
        Width in pixels of the current sprite.

    Notes:
    ------
    - Ships are rendered via the `setpixel()` function using the internal sprite array.
    - Lifecycle is managed by `alive`, `exploding`, and `exploded` flags.
    - Ships can be cloned and reused for object pooling, especially for missiles/enemies.
    - Sprite data must match SpriteHeight and SpriteWidth dimensions for correct display.

    Example Usage:
    --------------
    >>> ship = Ship()
    >>> ship.H, ship.V = 10, 5
    >>> ship.sprite = CreateSimpleSprite((255, 0, 0))
    >>> DrawShip(ship)

    Designed for compatibility with LEDarcade's buffered rendering system and
    multiprocessing architecture.
    """

class Ship(object):
  def __init__(self,h,v,r,g,b,direction,scandirection,speed,alive,lives,name,score,exploding):
    self.h          = h 
    self.v          = v
    self.r          = r
    self.g          = g
    self.b          = b
    self.direction  = direction
    self.scandirection = scandirection
    self.speed      = speed
    self.alive      = alive
    self.lives      = lives
    self.name       = name
    self.score      = 0
    self.exploding  = 0
    self.dropped    = 0
    self.velocityH   = 0
    self.velocityV   = 0
    

  def Display(self):
    #print("display HV:", self.name, self.h,self.v)

    if (self.alive == 1):
      TheMatrix.SetPixel(self.h,self.v,self.r,self.g,self.b)
      ScreenArray[self.v][self.h] = (self.r,self.g,self.b)
      

      
      
  def Erase(self):
    if (CheckBoundary(self.h,self.v) == 0):
      TheMatrix.SetPixel(self.h,self.v,0,0,0)
      ScreenArray[self.v][self.h] = (0,0,0)
    
      
  def Flash(self):
    sleep = FlashSleep * 0.75
    LowR  = int(self.r * 0.75)
    LowG  = int(self.g * 0.75)
    LowB  = int(self.b * 0.75)
    HighR = int(self.r * 1.5)
    HighG = int(self.g * 1.5)
    HighB = int(self.b * 1.5)
    
    if (LowR < 0 ):
      LowR = 0
    if (LowG < 0 ):
      LowG = 0
    if (LowB < 0 ):
      LowBB = 0
    
    if (HighR > 255):
      HighR = 255
    if (HighG > 255):
      HighG = 255
    if (HighB > 255):
      HighB = 255
      
    TheMatrix.SetPixel(self.h,self.v,HighR,HighG,HighB)
    #unicorn.show()
    #SendBufferPacket(RemoteDisplay,HatHeight,HatWidth)
    time.sleep(sleep)
    TheMatrix.SetPixel(self.h,self.v,self.r,self.g,self.b)
    #unicorn.show()
    TheMatrix.SetPixel(self.h,self.v,LowR,LowG,LowB)
    #unicorn.show()
    time.sleep(sleep)
    #unicorn.show()
    TheMatrix.SetPixel(self.h,self.v,HighR,HighG,HighB)
    #unicorn.show()
    time.sleep(sleep)
    TheMatrix.SetPixel(self.h,self.v,self.r,self.g,self.b)
    #unicorn.show()
    TheMatrix.SetPixel(self.h,self.v,LowR,LowG,LowB)
    #unicorn.show()
    time.sleep(sleep)
    #unicorn.show()
    #SendBufferPacket(RemoteDisplay,HatHeight,HatWidth)
  






  def UpdateLocationWithGravity(self,Gravity):
  #keep all the info inside the sprite object if possible

    GRAVITY  = Gravity
    FRICTION = 0.50
    CEILING  = -5
    FLOOR    = HatHeight
    WESTWALL = 0
    EASTWALL = HatWidth
    


    #initial co-ordinates for ship
    x     = self.h
    y     = self.v
    oldx  = x
    oldy  = y
    nextx = 0
    nexty = 0

    # intiial velocities
    velocityX = self.velocityH
    velocityY = self.velocityV
    

    
    # calculate new position based on velocity  
    next_y = y + velocityY
    next_x = x + velocityX


    # Bounce off floor
    if (next_y >= (FLOOR)):
      #velocityY = -velocityY * FRICTION
      velocityY = -velocityY * FRICTION
      velocityX =  velocityX * FRICTION
      next_y = FLOOR

    # Bounce of ceiling
    #if (next_y <= CEILING):
    #  #velocityY = -velocityY * FRICTION
    #  velocityY = -velocityY * FRICTION
    #  velocityX =  velocityX * FRICTION
    #  next_y = CEILING    

    # Bounce of side walls
    #if (next_x  > (EASTWALL)):
    #  velocityX = -velocityX * FRICTION
    #  next_x = EASTWALL

    # Bounce of side walls
    #if (next_x  < WESTWALL):
    #  velocityX = -velocityX * FRICTION
    #  next_x = WESTWALL

    #Calculate new vertical velocity (based on gravity)
    velocityY = velocityY +GRAVITY

    #Update location info
    self.h = next_x
    self.v = next_y
    self.velocityH = velocityX
    self.velocityV = velocityY





@njit
def compute_scroll_positions(start_h, moves, modifier):
    return np.array([start_h + i * modifier for i in range(moves)])
  
  
class Sprite(object):
  

  def __init__(self,width,height,r,g,b,grid=[]):
    self.width  = width
    self.height = height
    self.r      = r
    self.g      = g
    self.b      = b
    self.grid   = grid
    self.name   = "?"
    self.h      = 0
    self.v      = 0
    self.direction = random.randint(1,8)
    self.directionH  = 0
    self.directionV  = 0
    self.velocityH   = 0
    self.velocityV   = 0
    self.on          = True

  
  
    #Draw the sprite using an affect like in the movie Tron 
  def LaserScan(self,h1,v1,speed=0.005):
    x = 0
    y = 0
    r = self.r
    g = self.g
    b = self.b
    #print ("CAS - LaserScan -")
    for count in range (0,(self.width * self.height)):
      y,x = divmod(count,self.width)
      if(self.grid[count] >= 0):
        if (CheckBoundary((x+h1),y+v1) == 0):
          FlashDot4((x+h1),y+v1,speed)
          Canvas.SetPixel((x+h1),y+v1,r,g,b)
          TheMatrix.SwapOnVSync(Canvas)

  
  def DisplayIncludeBlack(self,h1,v1):
    x = 0,
    y = 0
    for count in range (0,(self.width * self.height)):
      y,x = divmod(count,self.width)
      
      if self.grid[count] == 1:
        if (CheckBoundary(x+h1,y+v1) == 0):
          TheMatrix.SetPixel(x+h1,y+v1,self.r,self.g,self.b)
      elif self.grid[count] == 0:
        if (CheckBoundary(x+h1,y+v1) == 0):
          TheMatrix.SetPixel(x+h1,y+v1,0,0,0)
    #unicorn.show()
    #SendBufferPacket(RemoteDisplay,HatHeight,HatWidth)



  def Display(self,h1,v1):
    x = 0,
    y = 0
    #print ("Display:",self.width, self.height, self.r, self.g, self.b,v1,h1)

    #global Canvas
    #Canvas = TheMatrix.SwapOnVSync(Canvas) 

    for count in range (0,(self.width * self.height)):
      y,x = divmod(count,self.width)
      #print("Count:",count,"xy",x,y)
      if self.grid[count] == 1:
        if (CheckBoundary(x+h1,y+v1) == 0):

          setpixelCanvas(x+h1,y+v1,self.r,self.g,self.b)
    #Canvas = TheMatrix.SwapOnVSync(Canvas) 




  def CopySpriteToScreenArrayZoom(self,h,v,ZoomFactor):

    #ScreenArray  = ([[]])
    #ScreenArray  = [[ (0,0,0) for i in range(HatWidth)] for i in range(HatHeight)]

    x = 0,
    y = 0

    for count in range (0,(self.width * self.height) ):
      y,x = divmod(count,self.width)

      y = y * ZoomFactor
      x = x * ZoomFactor

      if (ZoomFactor >= 1):
        for zv in range (0,ZoomFactor):
          for zh in range (0,ZoomFactor):
            H = x+h+zh
            V = y+v+zv
        
            if(CheckBoundary(H,V) == 0):
            #draw the sprite portion
              if self.grid[count] != 0:
                ScreenArray[V][H]=(self.r,self.g,self.b)
     
    return ScreenArray
    

  def CopySpriteToScreenArrayZoom2(self,h,v,ZoomFactor,InputScreenArray):


    x = 0,
    y = 0

    for count in range (0,(self.width * self.height) ):
      y,x = divmod(count,self.width)

      y = y * ZoomFactor
      x = x * ZoomFactor

      if (ZoomFactor >= 1):
        for zv in range (0,ZoomFactor):
          for zh in range (0,ZoomFactor):
            H = x+h+zh
            V = y+v+zv
        
            if(CheckBoundary(H,V) == 0):
            #draw the sprite portion
              if self.grid[count] != 0:
                InputScreenArray[V][H]=(self.r,self.g,self.b)
     
    return InputScreenArray
    


  





  def EraseNoShow(self,h1,v1):
    #This function draws a black sprite, erasing the sprite.  
    #It does NOT call #unicorn.show(), which would cause a visilble blink
    x = 0
    y = 0
    #print ("Erase:",self.width, self.height, self.r, self.g, self.b,v1,h1)
    for count in range (0,(self.width * self.height)):
      y,x = divmod(count,self.width)
      #print("Count:",count,"xy",x,y)
      if self.grid[count] == 1:
        if (CheckBoundary(x+h1,y+v1) == 0):
          #TheMatrix.SetPixel(x+h1,y+v1,0,0,0)
          TheMatrix.SetPixel(x+h1,y+v1,0,0,0)

    
  def Erase_old(self,h1,v1):
    #This function draws a black sprite, erasing the sprite.  This may be useful for
    #a future "floating over the screen" type of sprite motion
    #It is pretty fast now, seems just as fast as blanking whole screen using off() or clear()
    x = 0
    y = 0

    
    #global ScreenArray
    #global Canvas
    
    #Canvas = TheMatrix.SwapOnVSync(Canvas) 
    
    for count in range (0,(self.width * self.height)):
      y,x = divmod(count,self.width)
      if self.grid[count] == 1:
        if (CheckBoundary(x+h1,y+v1) == 0):
          #TheMatrix.SetPixel(x+h1,y+v1,0,0,0)
          
          #migrating to canvas logic
          #setpixel(x+h1,y+v1,0,0,0)
          setpixelCanvas(x+h1,y+v1,0,0,0)

    #Canvas = TheMatrix.SwapOnVSync(Canvas)              




  def EraseWholeSprite(self,h1,v1):
    #This function draws a black rectangle the size of the sprite

    x = 0
    y = 0
    for count in range (0,(self.width * self.height)):
      y,x = divmod(count,self.width)
      if (CheckBoundary(x+h1,y+v1) == 0):
        setpixel(x+h1,y+v1,0,0,0)



  def HorizontalFlip(self):
    x = 0
    y = 0
    flipgrid = []
    
    #print ("flip:",self.width, self.height)
    for count in range (0,(self.width * self.height)):
      y,x = divmod(count,self.width)
      #print("Count:",count,"xy",x,y)
      #print("Calculations: ",(y*self.height)+ self.height-x-1)  
      flipgrid.append(self.grid[(y*self.height)+ self.height-x-1])  
    #print("Original:", str(self.grid))
    #print("Flipped :", str(flipgrid))
    self.grid = flipgrid      

  



  def Scroll_old(self,h,v,direction,moves,delay):
    global Canvas

    #When we scroll, we want to write to the canvas first, then swap it with
    #the active display.  However, we want to copy the active display first
    #so we can write to the canvas and not lose what was on the screen or get
    #flickering.
    

    #print("Entering Scroll")
    x = 0
    oldh = 0
    
    #modifier is used to increment or decrement the location
    if direction == "right" or direction == "down":
      modifier = 1
    else: 
      modifier = -1
    
    #print("Modifier:",modifier)
    
    
   
    
    
    #Put active display into temp canvas
    #swap main display with canvas
    #copy temp canvas to canvas
    #swap main display with canvas
    #now both main display and canvas have a good background to start scrolling on
    TempCanvas = TheMatrix.SwapOnVSync(Canvas) 
    Canvas = TheMatrix.SwapOnVSync(TempCanvas) 
    Canvas = TempCanvas



    if direction == "left" or direction == "right":
      #print ("Direction: ",direction)  
      for count in range (0,moves):
        h = h + (modifier)



        #erase old sprite
        if count >= 1:
          oldh = h - modifier
          #print ("Scroll:",self.width, self.height, self.r, self.g, self.b,h,v)
          #TheMatrix.Clear()
          self.Erase(oldh,v)  

        #draw new sprite
        self.Display(h,v)
        #SendBufferPacket(RemoteDisplay,HatHeight,HatWidth)
        Canvas = TheMatrix.SwapOnVSync(Canvas) 
        time.sleep(delay)

        #Check for keyboard input
        r = random.randint(0,50)
        if (r == 0):
          Key = PollKeyboard()




    if direction == "up" or direction == "down":
      for count in range (0,moves):
        v = v + (modifier)
        #erase old sprite
        if count >= 1:
          oldv = v - modifier
          #self.Erase(h,oldv)
          setpixels(Buffer)
            
        #draw new sprite
        self.Display(h,v)
        Canvas = TheMatrix.SwapOnVSync(Canvas) 
        #SendBufferPacket(RemoteDisplay,HatHeight,HatWidth)
        time.sleep(delay)
        #Check for keyboard input
        r = random.randint(0,5)
        if (r == 0):
          Key = PollKeyboard()
        
  

  def Scroll(self, start_h=None, start_v=None, direction="right", moves=1, sleep=0.01):
        #AI created this one, but it flickers
        global Canvas, TheMatrix

        if start_h is not None:
            self.h = start_h
        if start_v is not None:
            self.v = start_v

        # Sync display and buffer once before scrolling
        TempCanvas = TheMatrix.SwapOnVSync(Canvas)
        Canvas = TheMatrix.SwapOnVSync(TempCanvas)
        Canvas = TempCanvas

        if direction == "right":
            modifier = 1
            axis = 'h'
        elif direction == "left":
            modifier = -1
            axis = 'h'
        elif direction == "down":
            modifier = 1
            axis = 'v'
        elif direction == "up":
            modifier = -1
            axis = 'v'
        else:
            modifier = 1
            axis = 'h'

        start_pos = self.h if axis == 'h' else self.v
        positions = compute_scroll_positions(start_pos, moves, modifier)

        for pos in positions:
            self.Erase(Canvas)
            if axis == 'h':
                self.h = pos
            else:
                self.v = pos
            self.DisplayToCanvas(Canvas)
            time.sleep(sleep)

        # Swap once at the end of scroll
        Canvas = TheMatrix.SwapOnVSync(Canvas)

  def Erase(self, Canvas):
        for count in range(self.width * self.height):
            y, x = divmod(count, self.width)
            if self.grid[count] == 1:
                Canvas.SetPixel(self.h + x, self.v + y, 0, 0, 0)

  def DisplayToCanvas(self, Canvas):
        for count in range(self.width * self.height):
            y, x = divmod(count, self.width)
            if self.grid[count] == 1:
                setpixelCanvas(self.h + x, self.v + y, self.r, self.g, self.b)





  def ScrollAcrossScreen(self,h,v,direction,ScrollSleep):
    #print ("--ScrollAcrossScreen--")
    #print ("width height",self.width,self.height)
    if (direction == "right"):
      self.Scroll((0- self.width),v,"right",(HatWidth + self.width),ScrollSleep)
    elif (direction == "left"):
      self.Scroll(HatWidth-1,v,"left",(HatWidth + self.width),ScrollSleep)
    elif (direction == "up"):
      self.Scroll(h,HatWidth-1,"left",(HatWidth + self.height),ScrollSleep)


  def DisplayNoBlack(self,h1,v1):
    x = 0
    y = 0

    #print ("Display:",self.width, self.height, self.r, self.g, self.b,v1,h1)
    for count in range (0,(self.width * self.height)):
      y,x = divmod(count,self.width)
      if (CheckBoundary(x+h1,y+v1) == 0):
        if (not(self.r == 0 and self.g == 0 and self.b == 0)):
          TheMatrix.SetPixel(x+h1,y+v1,self.r,self.g,self.b)
    


  def Float(self,h,v,direction,moves,delay):
    #Scroll across the screen, floating over the background
    
    x = 0
    oldh = 0
    #Capture Background
    Buffer = copy.deepcopy(unicorn.get_pixels())
    
    #modifier is used to increment or decrement the location
    if direction == "right" or direction == "down":
      modifier = 1
    else: 
      modifier = -1
    
    #print("Modifier:",modifier)
    
    
    
    if direction == "left" or direction == "right":
      #print ("Direction: ",direction)  
      
      for count in range (0,moves):
        h = h + (modifier)
        #erase old sprite
        #print ("Erasing Frame HV:",oldf," ",h,v)
        setpixels(Buffer)

        if count >= 1:
          oldh = h - modifier
          
        #draw new sprite
        self.Display(h,v)
        #unicorn.show() 
        #SendBufferPacket(RemoteDisplay,HatHeight,HatWidth)
        time.sleep(delay)

      #Check for keyboard input
      r = random.randint(0,5)
      if (r == 0):
        Key = PollKeyboard()

  
  def FloatAcrossScreen(self,h,v,direction,ScrollSleep):
    if (direction == "right"):
      self.Float((0- self.width),v,"right",(HatWidth + self.width),ScrollSleep)
    elif (direction == "left"):
      self.Float(HatWidth-1,v,"left",(HatWidth + self.width),ScrollSleep)
    elif (direction == "up"):
      self.Float(h,HatWidth-1,"left",(HatWidth + self.height),ScrollSleep)


  
  def TrimLeftEmptyColumns(self, leave_columns=1):
    if self.width <= leave_columns:
        return  # Nothing to trim

    def is_column_empty(col):
        for row in range(self.height):
            idx = row * self.width + col
            if self.grid[idx] != (0, 0, 0):
                return False
        return True

    # Count fully empty columns from the left
    empty_count = 0
    for col in range(self.width):
        if is_column_empty(col):
            empty_count += 1
        else:
            break

    # Leave X empty columns
    trim_cols = max(0, empty_count - leave_columns)
    if trim_cols == 0:
        return

    new_grid = []
    for row in range(self.height):
        start = row * self.width + trim_cols
        end = row * self.width + self.width
        new_grid.extend(self.grid[start:end])

    self.grid = new_grid
    self.width -= trim_cols

  
  def LeftTrim(self, pixels_to_trim):
      if pixels_to_trim >= self.width:
          raise ValueError("Cannot trim more pixels than the sprite width.")

      new_grid = []
      for row in range(self.height):
          start = row * self.width + pixels_to_trim
          end = row * self.width + self.width
          new_grid.extend(self.grid[start:end])

      self.grid = new_grid
      self.width -= pixels_to_trim
      self.h = max(0, self.h - pixels_to_trim)




class Wall(object):
  def __init__(self,h,v,r,g,b,alive,lives,name):
    self.h          = h 
    self.v          = v
    self.r          = r
    self.g          = g
    self.b          = b
    self.alive      = 1
    self.lives      = lives
    self.name       = name
    

  def Display(self):
    if (self.alive == 1):
      TheMatrix.SetPixel(self.h,self.v,self.r,self.g,self.b)


      
  def Erase(self):
    TheMatrix.SetPixel(self.h,self.v,0,0,0)

      
  def IncreaseBrightness(self,increment):
      
    self.r = (self.r + increment)
    self.g = (self.g + increment)
    self.b = (self.b + increment)
    
    if (self.r > 255):
      self.r = 255
    if (self.g > 255):
      self.g = 255
    if (self.b > 255):
      self.b = 255
    










# ----------------------
# -- Animated Sprites --
# ----------------------

class AnimatedSprite(object):
  def __init__(self,width,height,r,g,b,frames,grid):
    self.width  = width
    self.height = height
    self.r      = r
    self.g      = g
    self.b      = b
    self.frames = frames
    self.grid   = []

  def Display(self,h1,v1,frame):
    x = 0,
    y = 0

    #print ("Display:",self.width, self.height, self.r, self.g, self.b,v1,h1)
    for count in range (0,(self.width * self.height)):
      y,x = divmod(count,self.width)
      #print("Count:",count,"xy",x,y, " frame: ", frame)
      if self.grid[frame][count] == 1:
        if (CheckBoundary(x+h1,y+v1) == 0):
          TheMatrix.SetPixel(x+h1,y+v1,self.r,self.g,self.b)
    #unicorn.show() 


  def DisplayNoBlack(self,h1,v1,frame):
    x = 0,
    y = 0

    #print ("Display:",self.width, self.height, self.r, self.g, self.b,v1,h1)
    for count in range (0,(self.width * self.height)):
      y,x = divmod(count,self.width)
      #print("Count:",count,"xy",x,y, " frame: ", frame)
      if self.grid[frame][count] == 1:
        if (CheckBoundary(x+h1,y+v1) == 0):
          if (not(self.r == 0 and self.g == 0 and self.b == 0)):
            TheMatrix.SetPixel(x+h1,y+v1,self.r,self.g,self.b)
    #unicorn.show() 



  def Erase(self,h1,v1,frame):
    #This function draws a black sprite, erasing the sprite.  This may be useful for
    #a future "floating over the screen" type of sprite motion
    #It is pretty fast now, seems just as fast as blanking whole screen using off() or clear()
    x = 0
    y = 0
    #print ("Erase:",self.width, self.height, self.r, self.g, self.b,v1,h1)
    for count in range (0,(self.width * self.height)):
      y,x = divmod(count,self.width)
      #print("Count:",count,"xy",x,y)
      if self.grid[frame][count] == 1:
        if (CheckBoundary(x+h1,y+v1) == 0):
          #TheMatrix.SetPixel(x+h1,y+v1,255,255,255)
          #unicorn.show()
          #time.sleep(0.05)
          TheMatrix.SetPixel(x+h1,y+v1,0,0,0)




          
  def EraseSpriteFromPlayfield(self,Playfield):
    #Erase the sprite by writing 'EmptyObject' to every spot on the playfield occupied by the sprite
    x     = 0
    y     = 0
    count = 0



    for count in range (0,(self.width * self.height)):
      y,x = divmod(count,self.width)
      if (CheckBoundary(x+h1,y+v1) == 0):
        #TheMatrix.SetPixel(x+h1,y+v1,0,0,0)
        Playfield[y+v1][x+h1] = EmptyObject
        #FlashDot(x+h1,y+v1,0.002)
    return Playfield



  def HorizontalFlip(self):
    #Attempting to speed things up by disabling garbage collection
    gc.disable()
    for f in range(0,self.frames ):
      x = 0
      y = 0
      flipgrid = []
      #print ("flip:",self.width, self.height)
      for count in range (0,(self.width * self.height )):
        y,x = divmod(count,self.width)
        #print("Count:",count,"xy",x,y)
        #print("Calculations: ",(y*self.height)+ self.height-x-1)  
        flipgrid.append(self.grid[f][(y*self.height)+ self.height-x-1])  
      #print("Original:", str(self.grid[f]))
      #print("Flipped :", str(flipgrid))
      self.grid[f] = flipgrid      
    gc.enable()
          
  def Scroll(self,h,v,direction,moves,delay):
    #print("AnimatedSprite.scroll")
    x = 0
    oldh = 0
    #Capture Background
    Buffer = copy.deepcopy(unicorn.get_pixels())
    
    #modifier is used to increment or decrement the location
    if direction == "right" or direction == "down":
      modifier = 1
    else: 
      modifier = -1
    
    #print("Modifier:",modifier)
    
    #we use f to iterate the animation frames
    f = self.frames
    if direction == "left" or direction == "right":
      #print ("Direction: ",direction)  
      
      for count in range (0,moves):
        oldf = f
        f = f+1
        if (f > self.frames):
          f = 0
        h = h + (modifier)
        #erase old sprite
        #print ("Erasing Frame HV:",oldf," ",h,v)
        if count >= 1:
          oldh = h - modifier
          #print ("Scroll:",self.width, self.height, self.r, self.g, self.b,h,v)
          self.Erase(oldh,v,oldf)
        #draw new sprite
        setpixels(Buffer)
        self.Display(h,v,f)
        #unicorn.show() 
        #SendBufferPacket(RemoteDisplay,HatHeight,HatWidth)
        time.sleep(delay)

        #Check for keyboard input
        r = random.randint(0,5)
        if (r == 0):
          Key = PollKeyboard()



  def ScrollWithFrames(self,h,v,direction,moves,delay):
    #print("Entering Scroll")
    x    = 0
    oldh = 0
    Buffer = copy.deepcopy(unicorn.get_pixels())
    
    #modifier is used to increment or decrement the location
    if direction == "right" or direction == "down":
      modifier = 1
    else: 
      modifier = -1
    
    #print("Modifier:",modifier)
    oldf = self.frames
    #we use f to iterate the animation frames
    f = self.frames
    if direction == "left" or direction == "right":
      for count in range (0,moves):
        #print ("Count:",count)
        if (count >= 1):
          oldh = h
          #print ("Erasing Frame: ", oldf, " hv: ",oldh,v)
          self.Erase(oldh,v,oldf+1)
        h = h + (modifier)
        #print ("incrementing H:",h)

        #Check for keyboard input
        r = random.randint(0,25)
        if (r == 0):
          Key = PollKeyboard()

        #Animate Each Frame
        for f in range (0, self.frames+1):
          #erase old sprite
          oldf = f-1
          if oldf < 0:
            oldf = self.frames
          #print ("Erasing Frame: ", oldf, " hv: ",h,v)
          self.Erase(h,v,oldf)
          setpixels(Buffer)
            
          #draw new sprite
          #print ("Display Frame: ", f, " hv: ",h,v)
          self.Display(h,v,f)
          #unicorn.show()
          #SendBufferPacket(RemoteDisplay,HatHeight,HatWidth)

          time.sleep(delay)
          self.Erase(h,v,f)

       
  
  def ScrollAcrossScreen(self,h,v,direction,ScrollSleep):
    if (direction == "right"):
      self.Scroll((0- self.width),v,"right",(HatWidth + self.width),ScrollSleep)
    elif (direction == "left"):
      self.Scroll(HatWidth-1,v,"left",(HatWidth + self.width),ScrollSleep)
    elif (direction == "up"):
      self.Scroll(h,HatWidth-1,"left",(HatWidth + self.height),ScrollSleep)





  def Float(self,h,v,direction,moves,delay):
    #Scroll across the screen, floating over the background
    
    x = 0
    oldh = 0
    #Capture Background
    Buffer = copy.deepcopy(unicorn.get_pixels())
    
    #modifier is used to increment or decrement the location
    if direction == "right" or direction == "down":
      modifier = 1
    else: 
      modifier = -1
    
    #print("Modifier:",modifier)
    
    #we use f to iterate the animation frames
    f = self.frames
    if direction == "left" or direction == "right":
      #print ("Direction: ",direction)  
      
      for count in range (0,moves):
        oldf = f
        f = f+1
        if (f > self.frames):
          f = 0
        h = h + (modifier)
        #erase old sprite
        #print ("Erasing Frame HV:",oldf," ",h,v)
        setpixels(Buffer)

        if count >= 1:
          oldh = h - modifier
          #print ("Scroll:",self.width, self.height, self.r, self.g, self.b,h,v)
          
        #draw new sprite
        self.DisplayNoBlack(h,v,f)
        #unicorn.show() 
        #SendBufferPacket(RemoteDisplay,HatHeight,HatWidth)
        time.sleep(delay)

        #Check for keyboard input
        r = random.randint(0,5)
        if (r == 0):
          Key = PollKeyboard()

  
  def FloatAcrossScreen(self,h,v,direction,ScrollSleep):
    if (direction == "right"):
      self.Float((0- self.width),v,"right",(HatWidth + self.width),ScrollSleep)
    elif (direction == "left"):
      self.Float(HatWidth-1,v,"left",(HatWidth + self.width),ScrollSleep)
    elif (direction == "up"):
      self.Float(h,HatWidth-1,"left",(HatWidth + self.height),ScrollSleep)





  def Animate(self,h,v,delay,direction):
    x = 0,
    y = 0,
    Buffer = copy.deepcopy(unicorn.get_pixels())
    
    if (direction == 'forward'):
      for f in range (0,self.frames+1):
        self.Display(h,v,f)
        #unicorn.show()
        #SendBufferPacket(RemoteDisplay,HatHeight,HatWidth)
        time.sleep(delay)
        setpixels(Buffer)
    else:  
      for f in range (0,self.frames+1):
        self.Display(h,v,(self.frames-f))
        #unicorn.show()
        #SendBufferPacket(RemoteDisplay,HatHeight,HatWidth)
        time.sleep(delay)
        setpixels(Buffer)
      
      





      


# ----------------------------
# -- Color Animated Sprites --
# ----------------------------

class ColorAnimatedSprite(object):
  def __init__(self,h,v,name,width,height,frames=0,framerate=1,grid=[[]]):
    self.h      = h
    self.v      = v
    self.name   = name
    self.width  = width
    self.height = height
    self.frames = frames
    self.currentframe = 1
    self.framerate    = framerate #how many ticks per frame of animation, higher the number the slower the animation
    self.grid         = [[]]      #holds numbers that indicate color of the pixel
    self.ticks        = 0         #internal calculation of how many times a frame has been displayed.  
    self.ScreenArray = [[ (0,0,0) for i in range(HatWidth)] for i in range(HatHeight)]
    self.direction  = random.randint(1,8) 
    self.directionH  = 0
    self.directionV  = 0
    self.velocityH   = 0
    self.velocityV   = 0
    self.speed       = 0
    self.exploding   = 0
    self.Particles   = []  #holds dot objects for each pixel in a particular frame, used for animating explosions
    self.alive       = True
    self.counter     = 0
    self.afraid      = False  #when afraid, it will flee 
    self.bounces     = 0

  def IncrementFrame(self):
    self.ticks = self.ticks + 1

    #lower rate = faster frames
    m,r = divmod(self.ticks,self.framerate)
    if (r == 0):

      if (self.currentframe == self.frames):
        self.currentframe  = 1
      else:
        self.currentframe = self.currentframe + 1


  def InitializeScreenArray(self):
    self.ScreenArray  = ([[]])
    self.ScreenArray  = [[ (0,0,0) for i in range(HatWidth)] for i in range(HatHeight)]

  def Display(self,h1,v1):
    x = 0
    y = 0
    r = 0
    g = 0
    b = 0
    frame = self.currentframe


    for count in range (0,(self.width * self.height)):
      y,x = divmod(count,self.width)
      #print ("Name:",self.name," Frame:",frame, " Count: ",count, "Width Height",self.width,self.height )
      #print ("self.grid[frame][count]:",self.grid[frame][count] )
      if(self.grid[frame][count] >= 0):
        if (CheckBoundary((x+h1),y+v1) == 0):
          r,g,b =  ColorList[self.grid[frame][count]]
          #print ("CAS - Display - rgb",r,g,b)
          if (r > -1 and g > -1 and b > -1):
            #TheMatrix.SetPixel(x+h1,y+v1,r,g,b)
            setpixel(x+h1,y+v1,r,g,b)



  def DisplayNoBlack(self,h1,v1):
    #Treat black pixels in sprite as transparent
    #to acheive this we need to copy from our own buffer (ScreenArray)
    x = 0
    y = 0
    r = 0
    g = 0
    b = 0
    frame = self.currentframe
    
    for count in range (0,(self.width * self.height)):
      y,x = divmod(count,self.width)
      #print ("Name:",self.name," Frame:",frame, " Count: ",count, "Width Height",self.width,self.height )
      #print ("self.grid[frame][count]:",self.grid[frame][count] )
      
      #check for a color pixel
      if(self.grid[frame][count] >= 0):
        #check for outside boundary
        if (CheckBoundary((x+h1),y+v1) == 0):
          r,g,b =  ColorList[self.grid[frame][count]]
          #print ("CAS - Display - rgb",r,g,b)
          if (r > 0 or g > 0 or b > 0 ):
            #TheMatrix.SetPixel(x+h1,y+v1,r,g,b)
             setpixel(x+h1,y+v1,r,g,b)

          else:
            r,g,b = self.ScreenArray[y+v1][x+h1]
            setpixel(x+h1,y+v1,r,g,b)

            #TheMatrix.SetPixel(x+h1,y+v1,r,g,b)
    #unicorn.show() 



  def DisplayAnimated(self,h1 = -1, v1 = -1):
    #Treat black pixels in sprite as transparent -- maybe? Not yet.  Currently erasing.
    x = 0
    y = 0
    r = 0
    g = 0
    b = 0
    
    if (h1 < 0):
      h1 = self.h
    if (v1 < 0):
      v1 = self.v

    
    #print("name:",self.name," currentframe:",self.currentframe," Frames:",self.frames)

    self.ticks = self.ticks + 1
    #NOTE: This usage of ticks is different than in ScrollWithFrames
    if (self.ticks == self.framerate):
      self.currentframe = self.currentframe + 1
      self.ticks        = 0


    if (self.currentframe > self.frames or self.currentframe == 0):
      self.currentframe = 1

    for count in range (0,(self.width * self.height)):
      y,x = divmod(count,self.width)
      
      
      try:
        if (CheckBoundary((x+h1),y+v1) == 0):
          #print("Count:",count)
          #print("CurrentFrame:",self.currentframe," self.grid[]:",self.grid[self.currentframe][count])
          r,g,b =  ColorList[self.grid[self.currentframe][count]]
          TheMatrix.SetPixel(x+h1,y+v1,r,g,b)
      except:

        print("Something wrong...")
        print("Name:",self.name)
        print("Count:",count)
        print("CurrentFrame:",self.currentframe)
        print("self.grid[]:",self.grid[self.currentframe][count])
       

    
    return
   


  def PaintAnimatedToCanvas(self,h1 = -1, v1 = -1,Canvas=None):
    #Treat black pixels in sprite as transparent
    x = 0
    y = 0
    r = 0
    g = 0
    b = 0
    
    #if (h1 < 0):
    #  h1 = self.h
    #if (v1 < 0):
    #  v1 = self.v

    
    #print("name:",self.name," currentframe:",self.currentframe," Frames:",self.frames)

    self.ticks = self.ticks + 1
    #NOTE: This usage of ticks is different than in ScrollWithFrames
    if (self.ticks >= self.framerate):
      self.currentframe = self.currentframe + 1
      self.ticks        = 0

    if (self.currentframe > self.frames or self.currentframe == 0):
      self.currentframe = 1

    for count in range (0,(self.width * self.height)):
      y,x = divmod(count,self.width)
      
      
      try:
        if (CheckBoundary((x+h1),y+v1) == 0):
          #print("Count:",count)
          #print("CurrentFrame:",self.currentframe," self.grid[]:",self.grid[self.currentframe][count])
          r,g,b =  ColorList[self.grid[self.currentframe][count]]
          if(r > 0 or g > 0 or b > 0):
            Canvas.SetPixel(x+h1,y+v1,r,g,b)
      except:
        print("Error PaintAnimatedToCanvas")
        print("Something wrong...")
        print("Name:",self.name)
        print("Count:",count)
        print("CurrentFrame:",self.currentframe)
        print("self.grid[]:",self.grid[self.currentframe][count])
       

    
    return Canvas
   

  #def ActivateParticles(self):
  #  for j in (0,len(self.Particles)):




  def PaintAnimatedExplosionToCanvas(self,h1 = -1, v1 = -1,Canvas=None):
    #Treat black pixels in sprite as transparent
    x = 0
    y = 0
    r = 0
    g = 0
    b = 0
    
    #if (h1 < 0):
    #  h1 = self.h
    #if (v1 < 0):
    #  v1 = self.v

    
    #print("name:",self.name," currentframe:",self.currentframe," Frames:",self.frames)

    self.ticks = self.ticks + 1
    #NOTE: This usage of ticks is different than in ScrollWithFrames
    if (self.ticks == self.framerate):
      self.currentframe = self.currentframe + 1
      self.ticks        = 0

    if (self.currentframe > self.frames or self.currentframe == 0):
      self.currentframe = 1

    for count in range (0,(self.width * self.height)):
      y,x = divmod(count,self.width)
      
      
      try:
        if (CheckBoundary((x+h1),y+v1) == 0):
          #print("Count:",count)
          #print("CurrentFrame:",self.currentframe," self.grid[]:",self.grid[self.currentframe][count])
          r,g,b =  ColorList[self.grid[self.currentframe][count]]
          if(r > 0 or g > 0 or b > 0):
            Canvas.SetPixel(x+h1,y+v1,255,0,0)
      except:
        print("Error PaintAnimatedExplosionToCanvas")
        print("Something wrong...")
        print("Name:",self.name)
        print("Count:",count)
        print("CurrentFrame:",self.currentframe)
        print("self.grid[]:",self.grid[self.currentframe][count])
       

    
    return Canvas






  def Erase(self):
    #This function draws a black sprite, erasing the sprite.  This may be useful for
    #a future "floating over the screen" type of sprite motion
    #It is pretty fast now, seems just as fast as blanking whole screen using off() or clear()
    x = 0
    y = 0
    h1 = self.h
    v1 = self.v
    frame = self.currentframe
    #print ("CAS - Erase - width hieigh HV currentframe",self.width, self.height, h1,v1,frame)
    for count in range (0,(self.width * self.height)):
      y,x = divmod(count,self.width)
     # print("Count:",count,"xy",x,y)
     # print ("CAS - Erase Frame Count",frame,count)
      if self.grid[frame][count] > 0:

        #Double check this!  I believe this code was only necessary for the Ubercorn hat
        if (CheckBoundary(abs(15-(x+h1)),y+v1) == 0):
         # print ("CAS - Erase HV:",x+h1,y+v1)
          TheMatrix.SetPixel(x+h1,y+v1,0,0,0)


  def EraseZoom(self,h,v,ZoomFactor=1):
    x = 0
    y = 0
   
    # we round because newer animations make use of gravity and acceleration calculations
    h = round(h)
    v = round(v)

    for count in range (0,((self.width * ZoomFactor) * (self.height * ZoomFactor))):
      y,x = divmod(count,self.width * ZoomFactor)
      
      if (CheckBoundary(x+h,y+v) == 0):
        r,g,b = self.ScreenArray[y+v][x+h]
        setpixel(x+h,y+v,r,g,b)



  def EraseFrontBackZoom(self,h,v,Front=False,Back=True,ZoomFactor=1):
    #Just erase the front or back pixels
    #when a sprite is moving across the screen, it should overwrite itself and not
    #need to be erased, but just in case it is leaving artifacts we will erase a bit of it
    #this is way faster than erasing the entire sprite
    x = 0
    y = 0
   
    # we round because newer animations make use of gravity and acceleration calculations
    h = round(h)
    v = round(v)

    for count in range (0,((self.width * ZoomFactor) * (self.height * ZoomFactor))):
      y,x = divmod(count,self.width * ZoomFactor)
      
      if (Back==True):
        #if(x <= (2 * ZoomFactor)):
        if(x <= 1 ):
          if (CheckBoundary(x+h,y+v) == 0):
            r,g,b = self.ScreenArray[y+v][x+h]
            #setpixel(x+h,y+v,r,g,b)
            #setpixel(x+h,y+v,r,g,b)
            setpixelLEDOnly(x+h,y+v,r,g,b)


      if (Front==True):
        #if(x >= self.width + (-2 * ZoomFactor)):
        if(x >= self.width -1):
          if (CheckBoundary(x+h,y+v) == 0):
            r,g,b = self.ScreenArray[y+v][x+h]
            #setpixel(x+h,y+v,r,g,b)
            setpixelLEDOnly(x+h,y+v,r,g,b)







  def EraseFrame(self,h,v,frame=-1):
    x = 0
    y = 0
   
    # we round because newer animations make use of gravity and acceleration calculations
    h = round(h)
    v = round(v)
    
    for count in range (0,(self.width * self.height)):
      y,x = divmod(count,self.width)
      setpixel(x+h,y+v,0,0,0)









#Need Erase Frame Zoom       


          
  def EraseLocation(self,h,v):
    x = 0
    y = 0
    frame = self.currentframe -1

    for count in range (0,(self.width * self.height)):
      y,x = divmod(count,self.width)

 
      if self.grid[frame][count] > 0:
        if (CheckBoundary((x+h),y+v) == 0):
          #print ("CAS - EraseLocation HV:",x+h,y+v)
          TheMatrix.SetPixel(x+h,y+v,0,0,0)
          

  def EraseSpriteFromPlayfield(self,Playfield):
    #Erase the sprite by writing 'EmptyObject' to every spot on the playfield occupied by the sprite
    x     = 0
    y     = 0
    count = 0

    width   = self.width 
    height  = self.height
    h       = self.h
    v       = self.v
    frame   = self.currentframe
    self.alive = False
  

    for count in range (0,(width * height)):
      y,x = divmod(count,width)

      if (CheckBoundary(x+h,y+v) == 0):
        TheMatrix.SetPixel(x+h,y+v,0,0,0)
        Playfield[y+v][x+h] = EmptyObject
    return Playfield



  def EraseSpriteFromPlayfield2(self,Playfield):
    #This version is used by Defender 
    #Erase the sprite by writing 'EmptyObject' to every spot on the playfield occupied by the sprite
    x     = 0
    y     = 0
    count = 0

    width   = self.width 
    height  = self.height
    h       = self.h
    v       = self.v
    frame   = self.currentframe
    

    for count in range (0,(width * height)):
      y,x = divmod(count,width)

      if (CheckBoundary(x+h,y+v) == 0):
        Playfield.map[y+v][x+h] = EmptyObject
    return Playfield



          
  def Scroll(self,h,v,direction,moves,delay):
    #print("CAS - Scroll -   HV Direction moves Delay", h,v,direction,moves,delay)
    x = 0
    oldh = 0
    r = 0
    g = 0
    b = 0
    
        
    #modifier is used to increment or decrement the location
    if direction == "right" or direction == "down":
      modifier = 1
    else: 
      modifier = -1
    
    #print("Modifier:",modifier)
    
    #we use f to iterate the animation frames
    f = self.frames
    if direction == "left" or direction == "right":
      #print ("CAS - Scroll - Direction: ",direction)  
      
      for count in range (0,moves):
        #print ("CAS - Scroll - currentframe: ",self.currentframe)
        if (self.currentframe < (self.frames)):
          self.currentframe = self.currentframe + 1
        else:
          self.currentframe = 1
        h = h + (modifier)
        if count >= 1:
          oldh = h - modifier

        #draw new sprite
        #self.setpixels(Buffer)
          
        self.Display(h,v)
        #unicorn.show()
        #SendBufferPacket(RemoteDisplay,HatHeight,HatWidth)
        time.sleep(delay)


  def ScrollWithFrames(self,h,v,direction,moves,delay):

  #NOTE1: We need a rewrite.  We need to take into account movenet per tick as well as frames per tick
  #NOTE2: We call 

    #print("CAS - ScrollWithFrames - HV direction moves delay", h,v,direction,moves,delay)
    x    = 0
    oldh = 0
    self.currentframe = 1
    self.ticks = 0


    #modifier is used to increment or decrement the location
    if direction == "right" or direction == "down":
      modifier = 1
    else: 
      modifier = -1
    
    #print("Modifier:",modifier)
    oldf = self.frames
    #we use f to iterate the animation frames
    f = self.frames
    

    if direction == "left" or direction == "right":
      for count in range (0,moves):
        #print ("Count:",count)
        self.ticks = self.ticks + 1

#this is where we need to include distance per tick

        if (count >= 1):
          oldh = h
          h = h + (modifier)
          #print ("CAS - SWF - H oldh modifier",h,oldh,modifier)
        

        m,r = divmod(self.ticks, self.framerate)
        if (r== 0):
          self.DisplayNoBlack(h,v)
          #Increment current frame counter (taking into account framerate)
          #print("Ticks:",self.ticks,"Framerate:",self.framerate, "CurrentFrame:",self.currentframe)
          if (self.currentframe <= (self.frames)):
            self.currentframe = self.currentframe + 1
          if (self.currentframe > (self.frames)):
            self.currentframe = 1
        time.sleep(delay)




  def HorizontalFlip(self):
    #print ("CAS - Horizontalflip width heigh frames",self.width, self.height,self.frames)
    for f in range(1,self.frames+1):
      x = 0
      y = 0
      cells = (self.width * self.height)

      flipgrid = []
      #print ("Frame: ",f)
      #print ("cells: ",cells)
      for count in range (0,cells):
        y,x = divmod(count,self.width)
       #print("y,x = divmod(",count,self.width,"): ",y,x)
        #print ("cell to flip: ",((y*self.width)+ self.width-x-1), "value: ",self.grid[f][((y*self.width)+ self.width-x-1)])
        
        flipgrid.append(self.grid[f][((y*self.width)+ self.width-x-1)])  

      #print("Original:", str(self.grid[f]))
      #print("Flipped :", str(flipgrid))
      self.grid[f] = flipgrid      
    #print ("Done Flipping")
    
       
  
  def ScrollAcrossScreen(self,h,v,direction,ScrollSleep):
    #hv seem a little messed up, investigate what their original purpose was and fix

    #Make a copy of screen array so we can scroll over objects without erasing them
    self.ScreenArray = copy.deepcopy(ScreenArray)

    if (direction == "right"):
      self.ScrollWithFrames((0- self.width),v,"right",(HatWidth + self.width),ScrollSleep)
    elif (direction == "left"):
      self.ScrollWithFrames(HatWidth-1,v,"left",(HatWidth + self.width),ScrollSleep)
    elif (direction == "up"):
      self.ScrollWithFrames(h,HatWidth-1,"left",(HatWidth + self.height),ScrollSleep)



  def Float(self,h,v,direction,moves,delay):
    #print("CAS - Scroll -   HV Direction moves Delay", h,v,direction,moves,delay)
    x = 0
    oldh = 0
    r = 0
    g = 0
    b = 0
    
    #Capture Background
    Buffer = copy.deepcopy(unicorn.get_pixels())
    
    #modifier is used to increment or decrement the location
    if direction == "right" or direction == "down":
      modifier = 1
    else: 
      modifier = -1
    
    #print("Modifier:",modifier)
    
    #we use f to iterate the animation frames
    f = self.frames
    if direction == "left" or direction == "right":
      #print ("CAS - Scroll - Direction: ",direction)  
      
      for count in range (0,moves):
        #print ("CAS - Scroll - currentframe: ",self.currentframe)
        if (self.currentframe < (self.frames-1)):
          self.currentframe = self.currentframe + 1
        else:
          self.currentframe = 1
        h = h + (modifier)
        if count >= 1:
          oldh = h - modifier

        #draw new sprite
        setpixels(Buffer)
          
        self.DisplayNoBlack(h,v)
        #unicorn.show()
        #SendBufferPacket(RemoteDisplay,HatHeight,HatWidth)
        time.sleep(delay)



  def FloatAcrossScreen(self,h,v,direction,ScrollSleep):
    if (direction == "right"):
      self.Float((0- self.width),v,"right",(HatWidth + self.width),ScrollSleep)
    elif (direction == "left"):
      self.Float(HatWidth-1,v,"left",(HatWidth + self.width),ScrollSleep)
    elif (direction == "up"):
      self.Float(h,HatWidth-1,"left",(HatWidth + self.height),ScrollSleep)


  def Animate(self,h,v,direction,delay,StartFrame = 0):
   #print("CAS - Animate - HV delay ",h,v,delay,)
    x = 0,
    y = 0,
    
    if(StartFrame >= 1):
      self.currentframe = StartFrame

    if (direction == 'forward'):
      for f in range (0,self.frames):
        #erase old sprite
        #setpixels(Buffer)
        #draw new sprite
        self.Display(h,v)
        #unicorn.show()
        #SendBufferPacket(RemoteDisplay,HatHeight,HatWidth)

        #Increment current frame counter
        if (self.currentframe < (self.frames-1)):
          self.currentframe = self.currentframe + 1
        else:
          self.currentframe = 1
          
        time.sleep(delay)
        

    else:  
      for f in range (0,self.frames+1):
        #erase old sprite
        #setpixels(Buffer)
        #draw new sprite
        #print ("CAS - Animate - currentframe: ",self.currentframe)
        self.Display(h,v)
        #unicorn.show()
        #SendBufferPacket(RemoteDisplay,HatHeight,HatWidth)

        #Increment current frame counter
        if (self.currentframe <= (self.frames-1)):
          self.currentframe = self.currentframe -1
        else:
          self.currentframe = self.frames
          
        #time.sleep(delay)
      

  #Draw the sprite using an affect like in the movie Tron 
  def LaserScan(self,h1,v1,speed=0.005):
    x = 0
    y = 0
    r = 0
    g = 0
    b = 0
    frame = self.currentframe
    #print ("CAS - LaserScan -")
    for count in range (0,(self.width * self.height)):
      y,x = divmod(count,self.width)
      if(self.grid[frame][count] >= 0):
        if (CheckBoundary((x+h1),y+v1) == 0):
          r,g,b =  ColorList[self.grid[frame][count]]
          if (r > 0 or g > 0 or b > 0):
            FlashDot4((x+h1),y+v1,speed)
            TheMatrix.SetPixel((x+h1),y+v1,r,g,b)

          TheMatrix.SwapOnVSync(Canvas)




  def LaserErase(self,h1,v1,speed=0.005):
    x = 0
    y = 0
    r = 0
    g = 0
    b = 0
    frame = self.currentframe
    #print ("CAS - LaserErase -")
    for count in range (0,(self.width * self.height)):
      y,x = divmod(count,self.width)
      if(self.grid[frame][count] >= 0):
        if (CheckBoundary((x+h1),y+v1) == 0):
          r,g,b =  ColorList[self.grid[frame][count]]
          if (r > 0 or g > 0 or b > 0):
            FlashDot4((x+h1),y+v1,speed)
            TheMatrix.SetPixel((x+h1),y+v1,0,0,0)
      #unicorn.show() 
      #SendBufferPacket(RemoteDisplay,HatHeight,HatWidth)



    

  def CopyAnimatedSpriteToPlayfield(self,Playfield, TheObject):
    #Copy an animated sprite to the Playfield. 
    #Animated can have different shapes per frame
    #Each spot on the playfield will contain a reference to the objecttype e.g. a ship

    width   = self.width 
    height  = self.height
    h       = TheObject.h - (width // 2)
    v       = TheObject.v - (height // 2)
    
    if(self.currentframe == 0):
      self.currentframe = 1

    frame   = self.currentframe
      

    #Copy sprite to playfield
    for count in range (0,(width * height)):
      y,x = divmod(count,width)

      if(self.grid[frame][count] >= 0):
        if (CheckBoundary((x+h),y+v) == 0):
          r,g,b =  ColorList[self.grid[frame][count]]
          if (r > -1 and g > -1 and b > -1):
              Playfield[y+v][x+h] = TheObject
              #TheMatrix.SetPixel(x+h1,y+v1,r,g,b)
          else:
              Playfield[y+v][x+h] = EmptyObject('EmptyObject')
              TheMatrix.SetPixel(x+h1,y+v1,r,g,b)

           
    return Playfield;









  def ConvertSpriteToParticles(self):
    #Treat black pixels in sprite as transparent
    x = 0
    y = 0
    r = 0
    g = 0
    b = 0
    #print('Self HV:',self.h,self.v)
    self.currentframe = 1
    
    for count in range (0,(self.width * self.height)):
      y,x = divmod(count,self.width)
      
      
      try:
        r,g,b =  ColorList[self.grid[self.currentframe][count]]
        if(r > 0 or g > 0 or b > 0):
          NewParticle = Ship(x + self.h, y + self.v,r,g,b,2,2,2,1,1,'particle',0,0)
          NewParticle.velocityH = random.random() * (random.randint(0,1) *2 -1)
          NewParticle.velocityV = random.random() * (random.randint(0,1) *2 -1)
          self.Particles.append(NewParticle)
          #print("NewParticle hv:",x + self.h, y + self.v)
       
      except:
        print("Error ConvertSpriteToParticles")
        print("Something wrong...")
        print("Name:",self.name)
        print("Count:",count)
        print("CurrentFrame:",self.currentframe)
        print("self.grid[]:",self.grid[self.currentframe][count])
     
    return 
   


  def UpdateLocationWithGravity(self,Friction=0.):
  #color animated sprite version    
  #keep all the info inside the sprite object if possible

    GRAVITY  = 0.0098
    FRICTION = 0.50
    CEILING  = -5
    FLOOR    = HatHeight
    WESTWALL = 0
    EASTWALL = HatWidth -1
    


    #initial co-ordinates for ship
    x     = self.h
    y     = self.v
    oldx  = x
    oldy  = y
    nextx = 0
    nexty = 0

    # intiial velocities
    velocityX = self.velocityH
    velocityY = self.velocityV
    
    
    # calculate new position based on velocity  
    next_y = y + velocityY
    next_x = x + velocityX


    # Bounce off floor
    if (next_y >= (FLOOR)):
      velocityY = -velocityY * FRICTION
      velocityX =  velocityX * FRICTION
      next_y = FLOOR
      self.bounces = self.bounces + 1


    # Bounce off WestWall
    if (next_x <= WESTWALL):
      velocityY = velocityY * FRICTION
      velocityX = -velocityX * FRICTION
      next_x = WESTWALL
      self.bounces = self.bounces + 1


    if (next_x >= EASTWALL):
      velocityY = velocityY * FRICTION
      velocityX = -velocityX * FRICTION
      next_x = EASTWALL
      self.bounces = self.bounces + 1


    #Calculate new vertical velocity (based on gravity)
    velocityY = velocityY +GRAVITY

    #Update location info
    self.h = next_x
    self.v = next_y
    self.velocityH = velocityX
    self.velocityV = velocityY











class Maze(object):
  def __init__(self, h,v, width, height):
    self.h         = h
    self.v         = v
    self.width     = width
    self.height    = height
    self.ColorList = {}
    self.TypeList  = {}
    self.map       = []
    self.StartHV   = []   #Start positions for creatures (e.g. ghosts, pacdot)
    

                 
  def LoadMap(self):
    mapchar = ""
    RGB     = (0,0,0)
    dottype = ""
    NumDots = 0
    r       = 0
    g       = 0
    b       = 0


    for y in range (0,self.height):
      print ("PacMaze.map[",y,"] =",self.map[y])


    #read the map string and process one character at a time
    #decode the color and type of dot to place
    for y in range (0,self.height):
      for x in range (0,self.width):
        mapchar = self.map[y][x]
        RGB     =  self.ColorList.get(mapchar)
        dottype =  self.TypeList.get(mapchar)
        setpixelRGB(self.h+x,self.v+y,RGB)
        #print ("RGB",RGB)
        r,g,b = RGB
        

        if (dottype == "dot"):
          NumDots = NumDots + 1
          DotMatrix[self.h + x][self.v + y] = 1
          #FlashDot5(self.h + x,self.v + y,0.01)
        elif (dottype == "pill"):
          NumDots = NumDots + 1
          DotMatrix[self.h + x][self.v + y] = 2
          #FlashDot5(self.h + x,self.v + y,0.01)

      
    return DotMatrix, NumDots;  

  def GetStartingPositions(self):
    #Start pacdot in middle of bottom row, ghosts in middle
    PacHV = (0,0)
    Ghost1HV = (0,0)
    Ghost2HV = (0,0)
    Ghost3HV = (0,0)
    Ghost4HV = (0,0)

    PacHV    = self.h + (self.width // 2)   , self.v + (self.height   -2),
    Ghost1HV = self.h + (self.width // 2) -2, self.v + (self.height // 2),
    Ghost2HV = self.h + (self.width // 2) -1, self.v + (self.height // 2),
    Ghost3HV = self.h + (self.width // 2)   , self.v + (self.height // 2),
    Ghost4HV = self.h + (self.width // 2) +1, self.v + (self.height // 2)

    #print (PacHV)

    return (PacHV, Ghost1HV,Ghost2HV,Ghost3HV,Ghost4HV)
           
      
    
class Layer(object):
  def __init__(
      self,
      name,
      width,
      height,
      h,
      v
    ):  

    self.name   = name
    self.width  = width
    self.height = height
    self.h      = h
    self.v      = v
    self.map    = [[(0,0,0) for i in range(self.width)] for i in range(self.height)]
    self.starchance = 20


  def CreateStars(self,r,g,b,starchance):
    for x in range (0,self.width):
      for y in range (0,self.height):
        if(random.randint(0,starchance) == 1):
          
          #make the last screen of stars dim so we don't notice a transition
          if(x >= self.width -HatWidth):
            self.map[y][x] = (random.randint(0,round(r/3)),random.randint(0,round(g/3)),random.randint(0,round(b/3)))
          else:
            self.map[y][x] = (random.randint(0,r),random.randint(0,g),random.randint(0,b))

        else:
          self.map[y][x] = (0,0,0)

  


  def CreateMountains(self,GroundRGB,SurfaceRGB,maxheight=31):
    mh     = HatWidth -1
    mv     = 31

    chance = 10
    Step   = random.randint(1,3)

    GroundR, GroundG, GroundB    = GroundRGB
    SurfaceR, SurfaceG, SurfaceB = SurfaceRGB
    print("GroundRGB:",GroundRGB)


    HalfWidth = round(self.width / 2)

    #draw first half randomly, then copy in reverse for the second half
    for x in range (0,HalfWidth):
      if(random.randint(0,chance) == 1):
        mv = mv - Step
      elif(random.randint(0,chance) == 2):
        mv = mv + Step

      #stay within bounds
      if(mv > HatHeight-1):
        mv = HatHeight-1
      if(mv < HatHeight - maxheight):
        mv = HatHeight - maxheight

      


      #Start with dark, as the mountain grows it gets brighter
      
      #for y in range (mv,HatHeight):
      #  #Ground is brighter near top of screen, darker near bottom
      #  GroundR, GroundG, GroundB = AdjustBrightnessRGB(GroundRGB,-y + 20)
      #  self.map[y][x] = (GroundR,GroundG,GroundB)  
      #  #self.map[y][x] = (0,(abs(y -34  )),0)
      #self.map[mv][x] = (SurfaceR, SurfaceG, SurfaceB)

      
      for y in range (0,HatHeight):
        if(y >= mv):
          #Ground is brighter near top of screen, darker near bottom
          GroundR, GroundG, GroundB = AdjustBrightnessRGB(GroundRGB,-y + 20)
          self.map[y][x] = (GroundR,GroundG,GroundB)  
          #self.map[y][x] = (0,(abs(y -34  )),0)
        else:
          #erase any previous mountain debris
          self.map[y][x] = (0,0,0)  
        #draw surface topsoil
        self.map[mv][x] = (SurfaceR, SurfaceG, SurfaceB)

      


    #copy second half
    for x in range (0,HalfWidth):
      for y in range (0,HatHeight):
        self.map[y][x+HalfWidth] = self.map[y][HalfWidth -1 - x]






  def PaintOnCanvas(self,h,v,Canvas):
    width = self.width
    for x in range (0,HatWidth-1):
      for y in range (0,HatHeight):

        if(x+h >= width):
          PosX = x
        else:
          PosX = x+h

        try:
          r,g,b = rgb = self.map[v+y][PosX]
        except:
          print("PosX x h:",PosX, x, h)
          time.sleep(1)


        #if the pixel is not black, set the canvas
        if (rgb != (0,0,0)):
          Canvas.SetPixel(x,y,r,g,b)
    
    return Canvas
  


def PaintThreeLayerCanvas(bh, mh, fh, Background, Middleground, Foreground, Canvas):
    # Cache map arrays for fast access
    fg_map = Foreground.map
    mg_map = Middleground.map
    bg_map = Background.map

    # Cache widths (assume .width attribute exists)
    fwidth = Foreground.width
    mwidth = Middleground.width
    bwidth = Background.width

    # Cache range objects
    range_w = range(HatWidth)
    range_h = range(HatHeight)


    for x in range_w:
        fx = int((x + fh) % fwidth)
        mx = int((x + mh) % mwidth)
        bx = int((x + bh) % bwidth)

        for y in range_h:
            rgb = fg_map[y][fx]
            if rgb == (0, 0, 0):
                rgb = mg_map[y][mx]
                if rgb == (0, 0, 0):
                    rgb = bg_map[y][bx]

            # Always write something, even if it's black
            Canvas.SetPixel(x, y, *rgb)

    return Canvas
  






def PaintFourLayerCanvas(bh, mh, fh, gh, Background, Middleground, Foreground, Ground, Canvas, DirectionOfTravel=1):
    # Cache map arrays
    bg_map = Background.map
    mg_map = Middleground.map
    fg_map = Foreground.map
    gr_map = Ground.map

    # Cache widths
    bwidth = Background.width
    mwidth = Middleground.width
    fwidth = Foreground.width
    gwidth = Ground.width

    # Cache range objects
    range_w = range(HatWidth)
    range_h = range(HatHeight)

    for x in range_w:
        bx = int((x + bh) % bwidth)
        mx = int((x + mh) % mwidth)
        fx = int((x + fh) % fwidth)
        gx = int((x + gh) % gwidth)

        for y in range_h:
            rgb = gr_map[y][gx]
            if rgb == (0, 0, 0):
                rgb = fg_map[y][fx]
                if rgb == (0, 0, 0):
                    rgb = mg_map[y][mx]
                    if rgb == (0, 0, 0):
                        rgb = bg_map[y][bx]

            # Always write something, even if it's black
            Canvas.SetPixel(x, y, *rgb)

    return Canvas







def PaintFourLayerScreenArray(bh,mh,fh,gh,Background,Middleground,Foreground,Ground,Canvas):
  #we can only write to a canvas, cannot query it
  #so for fancy special effects we create a grid/screen array 

  bh = round(bh)
  mh = round(mh)
  fh = round(fh)
  gh = round(gh)



  ScreenArray  = ([[]])
  ScreenArray  = [[ (0,0,0) for i in range(HatWidth)] for i in range(HatHeight)]
  gwidth = Ground.width

  for x in range (0,HatWidth):
    for y in range (0,HatHeight):
      virtual_x = (x + gh) % gwidth
      rgb = Ground.map[y][virtual_x]

      if(rgb == (0,0,0)):
        rgb = Foreground.map[y][(x+fh) % Foreground.width]
        if(rgb == (0,0,0)):
          rgb = Middleground.map[y][(x+mh) % Middleground.width]
          if(rgb == (0,0,0)):
            rgb = Background.map[y][(x+bh) % Background.width]

      #if the pixel is not black, set the ScreenArray
      if (rgb != (0,0,0)):
        r,g,b = rgb
        ScreenArray[y][x] = (r,g,b)
        Canvas.SetPixel(x,y,r,g,b)
  
  return ScreenArray


def CopyImageToScreenArray(image, h, v, InputScreenArray=None):
  """Copy a PIL.Image onto a ScreenArray buffer without scaling."""
  h = round(h)
  v = round(v)

  image = image.convert('RGB')
  width, height = image.size

  if InputScreenArray is None:
    ScreenArray = [[(0,0,0) for _ in range(HatWidth)] for _ in range(HatHeight)]
  else:
    ScreenArray = InputScreenArray

  for y in range(height):
    for x in range(width):
      H = x + h
      V = y + v
      if CheckBoundary(H, V) == 0:
        r, g, b = image.getpixel((x, y))
        ScreenArray[V][H] = (r, g, b)

  return ScreenArray







def CopySpriteToLayerZoom(TheSprite,h,v, ColorTuple=(-1,-1,-1),FillerTuple=(-1,-1,-1),ZoomFactor = 1,Fill=True,Layer=Layer):
  #Copy a regular sprite to the LED 
  #Apply a ZoomFactor i.e  1 = normal / 2 = double in size / 3 = 3 times the size
  #print ("Copying sprite to playfield:",TheSprite.name, ObjectType, Filler)
  #if Fill = False, don't write anything for filler, that way we can leave existing lights on LED

  width   = TheSprite.width 
  height  = TheSprite.height

  
  if (ColorTuple == (-1,-1,-1)):
    r = TheSprite.r
    g = TheSprite.g
    b = TheSprite.b
  else:
    r,g,b   = ColorTuple
  
  if (FillerTuple == (-1,-1,-1)):
    fr = 0
    fg = 0
    fb = 0
  else:
    fr,fg,fb   = FillerTuple


  #Copy sprite to Canvas
  for count in range (0,(TheSprite.width * TheSprite.height) ):
    y,x = divmod(count,TheSprite.width)

    y = y * ZoomFactor
    x = x * ZoomFactor


    if (ZoomFactor >= 1):
      for zv in range (0,ZoomFactor):
        for zh in range (0,ZoomFactor):
          H = x+h+zh
          V = y+v+zv
         
          if((0 <= H < Layer.width) and (0 <= v < Layer.height)):

            #draw the sprite portion
            if TheSprite.grid[count] != 0:
              Layer.map[V][H] = (r,g,b)
            # if the sprite portion is a 0
            else:
              if (Fill == True):
                Layer.map[V][H] = (fr,fg,fb)

  return Layer;
  

















class PlayField(object):
  def __init__(
      self,
      name,
      width,
      height,
      h,
      v
    ):  

    self.name   = name,
    self.width  = width
    self.height = height
    self.h      = h
    self.v      = v
    self.map    = [[EmptyObject for i in range(self.width)] for i in range(self.height)]
    DisplayH    = 0 #upper left hand corner of the playfield currently being displayed
    DisplayV    = 0 #upper left hand corner of the playfield currently being displayed 


  def CopyPlayfieldToCanvas(self,h,v,canvas):

    for x in range (0,HatWidth):
      for y in range (0,HatHeight):
        if(self.map[y+v][x+h].name != 'EmptyObject'):
          canvas.SetPixel(x,y,50,75,100)
    return canvas



  def CopyAnimatedSpriteToPlayfield(self,h,v, TheObject):
    #Copy an object (e.g. animated sprite) to the Playfield. 
    #To keep things simple, we will copy the shape of the sprite
    #and treat it as a hitbox
    #Each spot on the playfield will contain a reference to the objecttype e.g. a ship

    width   = TheObject.width 
    height  = TheObject.height
    
    #Copy sprite to playfield
    for count in range (0,(width * height)):
      y,x = divmod(count,width)
      #print("Playfield HV:",x+h,y+v)

      if((y+v < self.height-1) and (x+h < self.width-1)):
        self.map[y+v][x+h] = TheObject
           
    return


  def EraseAnimatedSpriteFromPlayfield(self,h,v, TheObject):
    #overwrite the previous sprite info with EmptyObject

    width   = TheObject.width 
    height  = TheObject.height
    
    #Copy sprite to playfield
    for count in range (0,(width * height)):
      y,x = divmod(count,width)
      #print("Playfield HV:",x+h,y+v)

      if((y+v < self.height-1) and (x+h < self.width-1)):
        self.map[y+v][x+h] = EmptyObject
           
    return






#------------------------------------------------------------------------------
# Network Display Classes                                                    --
#------------------------------------------------------------------------------

# class PixelSimDisplay():
  # #Created by Kareem Sultan - Dec 2020
  # def __init__(self, url, display_name, on_attach=None, on_detach=None):
    # self.url = url
    # self.display_name = display_name
    # self.on_attach = on_attach
    # self.on_detach = on_detach
    # #we don't send packet if it is duplicate of previous
    # self.PreviousPacketString = ""
    # self.PacketString = ""

    # #self.on_message = on_message

# #    try:
    # print("Defining connection:",self.display_name)
    # self.hub_connection = HubConnectionBuilder()\
        # .with_url(url, options={"verify_ssl":True, "access_token_factory":lambda: "dummytoken"})\
        # .configure_logging(logging.DEBUG)\
        # .with_automatic_reconnect({
            # "type": "raw",
            # "keep_alive_interval": 10,
            # "reconnect_interval": 5,
            # "max_attempts": 5
        # })\
        # .build()

    # print("--connection on--")
    # self.hub_connection.on("recieveMessage", print)
    # print("--connection on_open--")
    # self.hub_connection.on_open(self.on_connect)
    # print("--connection on_close--")
    # self.hub_connection.on_close(lambda: print("connection closed"))
    # print("---")

    # # except Exception as ErrorMessage:
      # # TheTrace = traceback.format_exc()
      # # print("")
      # # print("")
      # # print("--------------------------------------------------------------")
      # # print("ERROR - Defining hub_connection")
      # # print(ErrorMessage)
      # # print("")
      # # #print("EXCEPTION")
      # # #print(sys.exc_info())
      # # print("")
      # # print ("TRACE")
      # # print (TheTrace)
      # # print("--------------------------------------------------------------")
      # # print("")
      # # print("")
      

  # def on_display_attached(self):
    # print("--Display attached--")
      

  # def on_connect(self):

      # print ("--on_connect start--")
    # #try:
      # print("---------------------------------------------------------------")
      # print("connection opened and handshake received ready to send messages")
      # self.hub_connection.send("AttachDisplay: ", [self.display_name])
      
      # if self.on_attach is not None and callable(self.on_attach):
              # print ("--calling on_attach--")
      # self.on_attach(self)
      # print("---------------------------------------------------------------")
      # print("--on_connect end--")



    # # except Exception as ErrorMessage:
      # # TheTrace = traceback.format_exc()
      # # print("")
      # # print("")
      # # print("--------------------------------------------------------------")
      # # print("ERROR - on_connect")
      # # print(ErrorMessage)
      # # print("")
      # # #print("EXCEPTION")
      # # #print(sys.exc_info())
      # # print("")
      # # print ("TRACE")
      # # print (TheTrace)
      # # print("--------------------------------------------------------------")
      # # print("")
      # # print("")
      # # time.sleep(5)
      
      
  # def connect(self):
    # try:
      # self.hub_connection.start()  
    
    # except Exception as ErrorMessage:
      # TheTrace = traceback.format_exc()
      # print("")
      # print("")
      # print("--------------------------------------------------------------")
      # print("ERROR - Connect")
      # print(ErrorMessage)
      # print("")
      # #print("EXCEPTION")
      # #print(sys.exc_info())
      # print("")
      # print ("TRACE")
      # print (TheTrace)
      # print("--------------------------------------------------------------")
      # print("")
      # print("")
      # time.sleep(5)

  
  # def disconnect(self):
    # try:
      # self.hub_connection.stop()
    # except Exception as ErrorMessage:
      # TheTrace = traceback.format_exc()
      # print("")
      # print("")
      # print("--------------------------------------------------------------")
      # print("ERROR - disconnect")
      # print(ErrorMessage)
      # print("")
      # #print("EXCEPTION")
      # #print(sys.exc_info())
      # print("")
      # print ("TRACE")
      # print (TheTrace)
      # print("--------------------------------------------------------------")
      # print("")
      # print("")
      # time.sleep(5)
  
  # def update(self):
    # #print ("PixelArray:",)
    # try:
      # print ("Sending message")  
      # self.hub_connection.send("sendMessage", [self.PacketString])
    # except Exception as ErrorMessage:
      # TheTrace = traceback.format_exc()
      # print("")
      # print("")
      # print("--------------------------------------------------------------")
      # print("ERROR - update")
      # print(ErrorMessage)
      # print("")
      # #print("EXCEPTION")
      # #print(sys.exc_info())
      # print("")
      # print ("TRACE")
      # print (TheTrace)
      # print("--------------------------------------------------------------")
      # print("")
      # print("")
      # time.sleep(5)


  # #Send the message/packet
  # def SendPacket(self):
    
    # print ("Inputstring:",self.PacketString)
    # #print ("PrevString: ",self.PreviousPacketString[1:16])
    
    
    # try:
      
      # if (self.PreviousPacketString != self.PacketString ):
        # startTime = time.time()
        # #r = requests.post(url = self.URLEndpoint, data = PacketString, timeout=0.3) 
        # #r = self.TheSession.post(url = self.URLEndpoint, data = PacketString, timeout=self.timeout) 
        # self.update()
        # self.PreviousPacketString = self.PacketString
        # endTime = time.time()
        # totalTimeTaken = str(float(round((endTime - startTime ),3)))
        # print ("ElapsedTime:",totalTimeTaken)


      # else:
        # print ("--skip frame--")

        # #print ("PacketString:",self.PacketString[1:16])
        # #print ("PrevString:  ",self.PreviousPacketString[1:16])

    # except Exception as ErrorMessage:
      # TheTrace = traceback.format_exc()
      # print("")
      # print("")
      # print("--------------------------------------------------------------")
      # print("ERROR")
      # print(ErrorMessage)
      # print("")
      # #print("EXCEPTION")
      # #print(sys.exc_info())
      # print("")
      # print ("TRACE")
      # print (TheTrace)
      # print("--------------------------------------------------------------")
      # print("")
      # print("")
      # time.sleep(5)



  # #The HTTPDisplay object can capture the current Unicorn buffer and send that as a packet
  # def SendBufferPacket(self,width,height):
    # self.PacketString = ""
    # x = 0
    # y = 0
    # rgb = (0,0,0)
    # HatWidth  = width
    # HatHeight = height
    # UnicornBuffer = unicorn.get_pixels()
   
    # ints = []
   
    # for x in range(0,HatHeight):
      # for y in range(0,HatWidth):
        # r,g,b = UnicornBuffer[x][y]
        # self.PacketString = self.PacketString + '#%02x%02x%02x' % (r,g,b) + ","
        # #self.PacketString = self.PacketString + str(r) + "," + str(g) + "," + str(b) + ","
        # #ints.append(UnicornBuffer[x][y])
    # #pixel_string = ','.join(map(str, ints))

    
    # self.PacketString = self.PacketString[:-1]
    # #print (pixel_string)
    # #print (string)
    # #self.SendPacket([pixel_string])
    # #print ("PixelString ",self.PacketString[1:8])
    # self.SendPacket()
    # #self.SendPacket([string])
    # return;
  


#------------------------------------------------------------------------------
# Drawing Sprite Classes                                                     --
#------------------------------------------------------------------------------



class TextMap(object):
  #A text map is a series of same length strings that are used to visually layout a map
  def __init__(self, h,v, width, height):
    self.h         = h
    self.v         = v
    self.width     = width
    self.height    = height
    self.ColorList = {}
    self.TypeList  = {}
    self.map       = []


  def CopyMapToColorSprite(self,TheSprite,Frame=0):
    mapchar = ""
    dottype = ""
    NumDots = 0
    SpriteFrame = []

    #read the map string and process one character at a time
    #decode the color and type of dot to place
    #print ("Height:",self.height)
    for y in range (0,self.height):
      #print ("map[",y,"] =",self.map[y])
      for x in range (0,self.width):
        mapchar = self.map[y][x]
        TheColor =  self.ColorList.get(mapchar)
        dottype  =  self.TypeList.get(mapchar)
        SpriteFrame.append(TheColor)
    TheSprite.grid.append(SpriteFrame)
    TheSprite.frames = TheSprite.frames + 1


    

    











#------------------------------------------------------------------------------
# SPRITES                                                                    --
#------------------------------------------------------------------------------




DigitList = []
#0
DigitList.append([1,1,1, 
                  1,0,1,
                  1,0,1,
                  1,0,1,
                  1,1,1])
#1
DigitList.append([0,0,1, 
                  0,0,1,
                  0,0,1,
                  0,0,1,
                  0,0,1])
#2
DigitList.append([1,1,1, 
                  0,0,1,
                  1,1,1,
                  1,0,0,
                  1,1,1])
#3
DigitList.append([1,1,1, 
                  0,0,1,
                  0,1,1,
                  0,0,1,
                  1,1,1])
#4
DigitList.append([1,0,1, 
                  1,0,1,
                  1,1,1,
                  0,0,1,
                  0,0,1])
               
#5  
DigitList.append([1,1,1, 
                  1,0,0,
                  1,1,1,
                  0,0,1,
                  1,1,1])
#6
DigitList.append([1,1,1, 
                  1,0,0,
                  1,1,1,
                  1,0,1,
                  1,1,1])
#7
DigitList.append([1,1,1, 
                  0,0,1,
                  0,1,0,
                  1,0,0,
                  1,0,0])
#8  
DigitList.append([1,1,1, 
                  1,0,1,
                  1,1,1,
                  1,0,1,
                  1,1,1])
#9  
DigitList.append([1,1,1, 
                  1,0,1,
                  1,1,1,
                  0,0,1,
                  0,0,1])
                    

# List of Digit Number Numeric sprites
DigitSpriteList = [Sprite(3,5,RedR,RedG,RedB,DigitList[i]) for i in range(0,10)]


AlphaList = []
#A
AlphaList.append([0,1,1,0,0,
                  1,0,0,1,0,
                  1,1,1,1,0,
                  1,0,0,1,0,
                  1,0,0,1,0])

#B
AlphaList.append([1,1,1,0,0,
                  1,0,0,1,0,
                  1,1,1,0,0,
                  1,0,0,1,0,
                  1,1,1,0,0])
#c
AlphaList.append([0,1,1,1,0,
                  1,0,0,0,0,
                  1,0,0,0,0,
                  1,0,0,0,0,
                  0,1,1,1,0])

#D
AlphaList.append([1,1,1,0,0,
                  1,0,0,1,0,
                  1,0,0,1,0,
                  1,0,0,1,0,
                  1,1,1,0,0])

#E
AlphaList.append([1,1,1,1,0,
                  1,0,0,0,0,
                  1,1,1,0,0,
                  1,0,0,0,0,
                  1,1,1,1,0])
                  
#F
AlphaList.append([1,1,1,1,0,
                  1,0,0,0,0,
                  1,1,1,0,0,
                  1,0,0,0,0,
                  1,0,0,0,0])

#G
AlphaList.append([0,1,1,1,0,
                  1,0,0,0,0,
                  1,0,1,1,0,
                  1,0,0,1,0,
                  0,1,1,1,0])

#H
AlphaList.append([1,0,0,1,0,
                  1,0,0,1,0,
                  1,1,1,1,0,
                  1,0,0,1,0,
                  1,0,0,1,0])
#I
AlphaList.append([0,1,1,1,0,
                  0,0,1,0,0,
                  0,0,1,0,0,
                  0,0,1,0,0,
                  0,1,1,1,0])
#J
AlphaList.append([0,1,1,1,0,
                  0,0,1,0,0,
                  0,0,1,0,0,
                  1,0,1,0,0,
                  0,1,0,0,0])
                  
#K
AlphaList.append([1,0,0,1,0,
                  1,0,1,0,0,
                  1,1,0,0,0,
                  1,0,1,0,0,
                  1,0,0,1,0])
#L
AlphaList.append([0,1,0,0,0,
                  0,1,0,0,0,
                  0,1,0,0,0,
                  0,1,0,0,0,
                  0,1,1,1,0])

#M
AlphaList.append([1,0,0,0,1,
                  1,1,0,1,1,
                  1,0,1,0,1,
                  1,0,0,0,1,
                  1,0,0,0,1])

#N
AlphaList.append([1,0,0,0,1,
                  1,1,0,0,1,
                  1,0,1,0,1,
                  1,0,0,1,1,
                  1,0,0,0,1])
#O
AlphaList.append([0,1,1,0,0,
                  1,0,0,1,0,
                  1,0,0,1,0,
                  1,0,0,1,0,
                  0,1,1,0,0])
#P
AlphaList.append([1,1,1,0,0,
                  1,0,0,1,0,
                  1,1,1,0,0,
                  1,0,0,0,0,
                  1,0,0,0,0])
#Q
AlphaList.append([0,1,1,1,0,
                  1,0,0,0,1,
                  1,0,0,0,1,
                  1,0,0,1,0,
                  0,1,1,0,1])
#R 
AlphaList.append([1,1,1,0,0,
                  1,0,0,1,0,
                  1,1,1,0,0,
                  1,0,1,0,0,
                  1,0,0,1,0])
#S
AlphaList.append([0,1,1,1,0,
                  1,0,0,0,0,
                  0,1,1,0,0,
                  0,0,0,1,0,
                  1,1,1,0,0])
#T
AlphaList.append([0,1,1,1,0,
                  0,0,1,0,0,
                  0,0,1,0,0,
                  0,0,1,0,0,
                  0,0,1,0,0])
#U
AlphaList.append([1,0,0,1,0,
                  1,0,0,1,0,
                  1,0,0,1,0,
                  1,0,0,1,0,
                  0,1,1,0,0])
#V
AlphaList.append([1,0,0,0,1,
                  1,0,0,0,1,
                  0,1,0,1,0,
                  0,1,0,1,0,
                  0,0,1,0,0])
#W
AlphaList.append([1,0,0,0,1,
                  1,0,0,0,1,
                  1,0,1,0,1,
                  0,1,0,1,0,
                  0,1,0,1,0])
#X
AlphaList.append([1,0,0,0,1,
                  0,1,0,1,0,
                  0,0,1,0,0,
                  0,1,0,1,0,
                  1,0,0,0,1])
#Y
AlphaList.append([0,1,0,1,0,
                  0,1,0,1,0,
                  0,0,1,0,0,
                  0,0,1,0,0,
                  0,0,1,0,0])
#Z
AlphaList.append([1,1,1,1,0,
                  0,0,0,1,0,
                  0,0,1,0,0,
                  0,1,0,0,0,
                  1,1,1,1,0])


                  
                  
# List of Alpha sprites
AlphaSpriteList = [Sprite(5,5,RedR,RedG,RedB,AlphaList[i]) for i in range(0,26)]



                  
                  
#space                  
SpaceSprite = Sprite(
  3,
  5,
  0,
  0,
  0,
  [0,0,0,
   0,0,0,
   0,0,0,
   0,0,0,
   0,0,0]
)

#Exclamation
ExclamationSprite = Sprite(
  3,
  5,
  0,
  0,
  0,
  [0,1,0,
   0,1,0,
   0,1,0,
   0,0,0,
   0,1,0]
)

#Period
PeriodSprite = Sprite(
  2,
  5,
  0,
  0,
  0,
  [0,0,
   0,0,
   0,0,
   0,0,
   0,1]
)




#QuestionMark
QuestionMarkSprite = Sprite(
  5,
  5,
  0,
  0,
  0,
  [0,0,1,1,0,
   0,0,0,1,0,
   0,0,1,1,0,
   0,0,0,0,0,
   0,0,1,0,0]
)


#PoundSignSprite
PoundSignSprite = Sprite(
  5,
  5,
  0,
  0,
  0,
  [0,1,0,1,0,
   1,1,1,1,1,
   0,1,0,1,0,
   1,1,1,1,1,
   0,1,0,1,0]
)


#AmpersandSprite
AmpersandSprite = Sprite(
  5,
  5,
  0,
  0,
  0,
  [0,0,0,1,0,
   1,1,1,1,1,
   0,1,0,1,0,
   0,0,1,1,0,
   0,0,0,1,0]
)


 
ColonSprite = Sprite(
  3,
  5,
  RedR,
  RedG,
  RedB,
  [0,0,0,
   0,1,0,
   0,0,0,
   0,1,0,
   0,0,0]
)



DashSprite = Sprite(
  4,
  5,
  RedR,
  RedG,
  RedB,
  [0,0,0,0,
   0,0,0,0,
   0,1,1,0,
   0,0,0,0,
   0,0,0,0]
)


#$
DollarSignSprite = Sprite(
  4,
  5,
  RedR,
  RedG,
  RedB,
  [0,1,1,1,
   1,0,1,0,
   0,1,1,0,
   0,0,1,1,
   1,1,1,0]
)

#,
CommaSprite = Sprite(
  3,
  5,
  RedR,
  RedG,
  RedB,
  [0,0,0,
   0,0,0,
   0,0,0,
   0,0,1,
   0,1,0]
)



# `
BackTickSprite = Sprite(
  3,
  5,
  RedR,
  RedG,
  RedB,
  [1,0,0,
   0,1,0,
   0,0,0,
   0,0,0,
   0,0,0]
)


#+
PlusSignSprite = Sprite(
  5,
  5,
  0,
  0,
  0,
  [0,0,0,0,0,
   0,0,1,0,0,
   0,1,1,1,0,
   0,0,1,0,0,
   0,0,0,0,0]
)



#(
LeftParenthesisSprite = Sprite(
  3,
  5,
  0,
  0,
  0,
  [0,0,1,
   0,1,0,
   0,1,0,
   0,1,0,
   0,0,1,]
)


#(
RightParenthesisSprite = Sprite(
  3,
  5,
  0,
  0,
  0,
  [0,1,0,
   0,0,1,
   0,0,1,
   0,0,1,
   0,1,0,]
)





#>
GreaterThanSprite = Sprite(
  3,
  5,
  0,
  0,
  0,
  [1,0,0,
   0,1,0,
   0,0,1,
   0,1,0,
   1,0,0]
)


#>
LessThanSprite = Sprite(
  3,
  5,
  0,
  0,
  0,
  [0,0,1,
   0,1,0,
   1,0,0,
   0,1,0,
   1,0,1]
)



#@
AtSignSprite = Sprite(
  5,
  5,
  0,
  0,
  0,
  [0,1,1,1,0,
   1,0,1,0,1,
   1,0,1,1,1,
   1,0,0,0,0,
   0,1,1,1,0]
)





#'
SingleQuoteSprite = Sprite(
  3,
  3,
  0,
  0,
  0,
  [0,1,0,
   0,1,0,
   0,0,0,
   0,0,0,
   0,0,0]
)


#"
DoubleQuoteSprite = Sprite(
  5,
  5,
  0,
  0,
  0,
  [0,1,0,1,0,
   0,1,0,1,0,
   0,0,0,0,0,
   0,0,0,0,0,
   0,0,0,0,0]
)



#|
PipeSprite = Sprite(
  3,
  3,
  0,
  0,
  0,
  [0,1,0,
   0,1,0,
   0,1,0,
   0,1,0,
   0,1,0]
)



#_
UnderscoreSprite = Sprite(
  3,
  3,
  0,
  0,
  0,
  [0,0,0,
   0,0,0,
   0,0,0,
   0,0,0,
   1,1,1]
)


# [
LeftSquareBracketSprite = Sprite(
  3,
  3,
  0,
  0,
  0,
  [1,1,1,
   1,0,0,
   1,0,0,
   1,0,0,
   1,1,1]
)

# [
RightSquareBracketSprite = Sprite(
  3,
  3,
  0,
  0,
  0,
  [1,1,1,
   0,0,1,
   0,0,1,
   0,0,1,
   1,1,1]
)


# >
ForwardSlashSprite = Sprite(
  5,
  5,
  0,
  0,
  0,
  [0,0,0,0,1,
   0,0,0,1,0,
   0,0,1,0,0,
   0,1,0,0,0,
   1,0,0,0,0]
)


# >
BackSlashSprite = Sprite(
  5,
  5,
  0,
  0,
  0,
  [1,0,0,0,0,
   0,1,0,0,0,
   0,0,1,0,0,
   0,0,0,1,0,
   0,0,0,0,1]
)



CursorSprite = Sprite(
  4,
  5,
  RedR,
  RedG,
  RedB,
  [1,1,1,1,
   1,1,1,1,
   1,1,1,1,
   1,1,1,1,
   1,1,1,1]
)


# chr(193)
UpArrowSprite = Sprite(
  5,
  5,
  0,
  0,
  0,
  [0,0,1,0,0,
   0,1,1,1,0,
   1,1,1,1,1,
   0,0,1,0,0,
   0,0,1,0,0,]
)


# chr(194)
DownArrowSprite = Sprite(
  5,
  5,
  0,
  0,
  0,
  [0,0,1,0,0,
   0,0,1,0,0,
   1,1,1,1,1,
   0,1,1,1,0,
   0,0,1,0,0,]
)


ClockSpriteBackground = Sprite(
  16,
  7,
  0,
  0,
  0,
  [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
   0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
   0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
   0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
   0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
   0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
   0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
   0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,  
   ]
)



#------------------------------------------------------------------------------
# CUSTOM SPRITES                                                             --
#   These sprites come from various video games in the Arcade Retro Clock.   --
#   They were created for an 8x8 display but work quite well on any size.    --
#   Animated sprites have frames of animations that are displayed as the     --
#   sprite moves.                                                            --
#                                                                            --
#   Note:                                                                    --
#   These sprites are "drawn" with a lot of imagination but are stored as    --
#   a list of integers.  This is a technique I created back in the 80's      --
#   while programming my TRS-80 color computer, and certainly WAY before     --
#   I had a firm grasp on Python arrays/lists/tuples and all that jazz.      --
#------------------------------------------------------------------------------




PacSprite = Sprite(
  6,
  5,
  YellowR,
  YellowG,
  YellowB,
  [0,0,1,1,1,0,
   0,1,1,1,0,0,
   0,1,1,0,0,0,
   0,1,1,1,0,0,
   0,0,1,1,1,0]
)


RedGhostSprite = Sprite(
  5,
  5,
  RedR,
  RedG,
  RedB,
  [0,1,1,1,0,
   1,1,1,1,1,
   1,0,1,0,1,
   1,1,1,1,1,
   1,0,1,0,1]
)
    

OrangeGhostSprite = Sprite(
  5,
  5,
  OrangeR,
  OrangeG,
  OrangeB,
  [0,1,1,1,0,
   1,1,1,1,1,
   1,0,1,0,1,
   1,1,1,1,1,
   1,0,1,0,1]
)
    
BlueGhostSprite = Sprite(
  5,
  5,
  BlueR,
  BlueG,
  BlueB,
  [0,1,1,1,0,
   1,1,1,1,1,
   1,0,1,0,1,
   1,1,1,1,1,
   1,0,1,0,1]
)

PurpleGhostSprite = Sprite(
  5,
  5,
  PurpleR,
  PurpleG,
  PurpleB,
  [0,1,1,1,0,
   1,1,1,1,1,
   1,0,1,0,1,
   1,1,1,1,1,
   1,0,1,0,1]
)



ChickenRunning = ColorAnimatedSprite(h=0, v=0, name="Chicken", width=8, height=8, frames=4,framerate=1,grid=[])
ChickenRunning.grid.append(
  [
    0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 5, 0, 0, 0, 0, 0,
    0,17, 2, 0, 0, 0, 0, 0,
    0, 0, 5, 2, 0, 2, 2, 0,
    0, 0, 0, 2, 2, 2, 0, 0,
    0, 0, 0, 0,22, 0, 0, 0,
    0, 0, 0,22, 0,21, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0

  ]
)

ChickenRunning.grid.append(
  [
    0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 5, 0, 0, 0, 0, 0,
    0,17, 2, 0, 0, 0, 0, 0,
    0, 0, 5, 2, 0, 2, 2, 0,
    0, 0, 0, 2, 2, 2, 0, 0,
    0, 0, 0, 0,22, 0, 0, 0,
    0, 0, 0, 0,22, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0

  ]
)

ChickenRunning.grid.append(
  [
    0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 5, 0, 0, 0, 0, 0,
    0,17, 2, 0, 0, 0, 0, 0,
    0, 0, 5, 2, 0, 2, 2, 0,
    0, 0, 0, 2, 2, 2, 0, 0,
    0, 0, 0, 0,22, 0, 0, 0,
    0, 0, 0,21, 0,22, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0

  ]
)


ChickenRunning.grid.append(
  [
    0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 5, 0, 0, 0, 0, 0,
    0,17, 2, 0, 0, 0, 0, 0,
    0, 0, 5, 2, 0, 2, 2, 0,
    0, 0, 0, 2, 2, 2, 0, 0,
    0, 0, 0, 0,22, 0, 0, 0,
    0, 0, 0, 0,22, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0

  ]
)







WormChasingChicken = ColorAnimatedSprite(h=0, v=0, name="Chicken", width=24, height=8, frames=4,framerate=1,grid=[])
WormChasingChicken.grid.append(
  [
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0,17, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 5, 2, 0, 2, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 2, 2, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0,22, 0, 0, 0, 0, 0, 0, 0,17,17,17,17,17,17,17,17, 0, 0, 0, 0,
    0, 0, 0,22, 0,21, 0, 0, 0, 0, 0, 0,17,17,17,17,17,17,17,17, 0, 0, 0, 0,

  ]
)

WormChasingChicken.grid.append(
  [
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0,17, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 5, 2, 0, 2, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 2, 2, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,17,17, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0,22, 0, 0, 0, 0, 0, 0, 0, 0,17,17,17,17,17,17,17, 0, 0, 0, 0,
    0, 0, 0, 0,22, 0, 0, 0, 0, 0, 0, 0, 0,17,17,17, 0, 0,17,17, 0, 0, 0, 0,

  ]
)

WormChasingChicken.grid.append(
  [
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0,17, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 5, 2, 0, 2, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0,17,17, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 2, 2, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,17,17, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0,22, 0, 0, 0, 0, 0, 0, 0, 0, 0,17,17, 0, 0,17,17, 0, 0, 0, 0,
    0, 0, 0,21, 0,22, 0, 0, 0, 0, 0, 0, 0, 0,17,17, 0, 0,17,17, 0, 0, 0, 0

  ]
)


WormChasingChicken.grid.append(
  [
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0,17, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 5, 2, 0, 2, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 2, 2, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,17,17, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0,22, 0, 0, 0, 0, 0, 0, 0, 0,17,17,17,17,17,17,17, 0, 0, 0, 0,
    0, 0, 0, 0,22, 0, 0, 0, 0, 0, 0, 0, 0,17,17,17, 0, 0,17,17, 0, 0, 0, 0

  ]
)












ChickenChasingWorm = ColorAnimatedSprite(h=0, v=0, name="Chicken", width=16, height=8, frames=4,framerate=1,grid=[])
ChickenChasingWorm.grid.append(
  [
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0,17, 2, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5, 2, 0, 2, 2, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 2, 2, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,22, 0, 0, 0,
    5,17, 5,17,17, 0, 0, 0, 0, 0, 0,22, 0,21, 0, 0

  ]
)

ChickenChasingWorm.grid.append(
  [
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0,17, 2, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5, 2, 0, 2, 2, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 2, 2, 0, 0,
    0, 0, 0, 5, 0, 0, 0, 0, 0, 0, 0, 0,22, 0, 0, 0,
    0, 5,17, 0,17, 0, 0, 0, 0, 0, 0, 0,22, 0, 0, 0

  ]
)

ChickenChasingWorm.grid.append(
  [
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0,17, 2, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5, 2, 0, 2, 2, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 2, 2, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,22, 0, 0, 0,
    5,17, 5,17,17, 0, 0, 0, 0, 0, 0,21, 0,22, 0, 0

  ]
)


ChickenChasingWorm.grid.append(
  [
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0,17, 2, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5, 2, 0, 2, 2, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 2, 2, 0, 0,
    0, 0, 0, 5, 0, 0, 0, 0, 0, 0, 0, 0,22, 0, 0, 0,
    0, 5,17, 0,17, 0, 0, 0, 0, 0, 0, 0,22, 0, 0, 0

  ]
)




ThreeGhostPacSprite = ColorAnimatedSprite(h=0, v=0, name="ThreeGhost", width=27, height=5, frames=5, framerate=1,grid=[])



ThreeGhostPacSprite.grid.append(
  [
   0, 0, 0,33,33,33, 0, 0, 0,18,18,18, 0, 0, 0, 7, 7, 7, 0, 0, 0, 0,23,23,23, 0, 0,
   0, 0,33,33,33,33,33, 0,18,18,18,18,18, 0, 7, 7, 7, 7, 7, 0, 0, 23,23,23, 0,0, 0,
   0, 0,33, 2,33, 2,33, 0,18, 2,18, 2,18, 0, 7, 2, 7, 2, 7, 0, 0, 23,23, 0, 0,0, 0,
   0, 0,33,33,33,33,33, 0,18,18,18,18,18, 0, 7, 7, 7, 7, 7, 0, 0, 23,23,23, 0,0, 0,
   0, 0,33, 0,33, 0,33, 0,18, 0,18, 0,18, 0, 7, 0, 7, 0, 7, 0, 0, 0,23,23,23, 0, 0
  
   ]
)


ThreeGhostPacSprite.grid.append(
  [
    0, 0 ,0,33,33,33, 0, 0, 0,18,18,18, 0, 0, 0, 7, 7, 7, 0, 0, 0, 0,23,23,23, 0, 0,
    0, 0,33,33,33,33,33, 0,18,18,18,18,18, 0, 7, 7, 7, 7, 7, 0, 0,23,23,23,23,23, 0,
    0, 0,33, 2,33, 2,33, 0,18, 2,18, 2,18, 0, 7, 2, 7, 2, 7, 0, 0,23,23,23, 0, 0, 0,
    0, 0,33,33,33,33,33, 0,18,18,18,18,18, 0, 7, 7, 7, 7, 7, 0, 0,23,23,23,23,23, 0,
    0, 0,33, 0,33, 0,33, 0,18, 0,18, 0,18, 0, 7, 0, 7, 0, 7, 0, 0, 0,23,23,23, 0, 0
  
   ]
)



ThreeGhostPacSprite.grid.append(
  [
    0, 0, 0,33,33,33, 0, 0, 0,18,18,18, 0, 0, 0, 7, 7, 7, 0, 0, 0, 0,23,23,23,0, 0,
    0, 0,33,33,33,33,33, 0,18,18,18,18,18, 0, 7, 7, 7, 7, 7, 0, 0, 23,23,23,23,23, 0,
    0, 0,33, 2,33, 2,33, 0,18, 2,18, 2,18, 0, 7, 2, 7, 2, 7, 0, 0, 23,23,23,23,23, 0,
    0, 0,33,33,33,33,33, 0,18,18,18,18,18, 0, 7, 7, 7, 7, 7, 0, 0, 23,23,23,23,23, 0,
    0, 0,33, 0,33, 0,33, 0,18, 0,18, 0,18, 0, 7, 0, 7, 0, 7, 0, 0, 0,23,23,23,0, 0
  
   ]
)



ThreeGhostPacSprite.grid.append(
  [
    0, 0,0,33,33,33, 0, 0, 0,18,18,18, 0, 0, 0, 7, 7, 7, 0, 0, 0,  0,23,23,23,0, 0,
    0, 0,33,33,33,33,33, 0,18,18,18,18,18, 0, 7, 7, 7, 7, 7, 0, 0, 23,23,23,23,0, 0,
    0, 0,33, 2,33, 2,33, 0,18, 2,18, 2,18, 0, 7, 2, 7, 2, 7, 0, 0, 23,23,23,0,0, 0,
    0, 0,33,33,33,33,33, 0,18,18,18,18,18, 0, 7, 7, 7, 7, 7, 0, 0, 23,23,23,23,0,  0,
    0, 0,33, 0,33, 0,33, 0,18, 0,18, 0,18, 0, 7, 0, 7, 0, 7, 0, 0, 0,23,23,23,0, 0
  
   ]
)

 
ThreeGhostPacSprite.grid.append(
  [
    0, 0, 0,33,33,33, 0, 0, 0,18,18,18, 0, 0, 0, 7, 7, 7, 0, 0, 0, 0,23,23,23,0, 0,
    0, 0,33,33,33,33,33, 0,18,18,18,18,18, 0, 7, 7, 7, 7, 7, 0, 0, 23,23,0,0,0, 0,
    0, 0,33, 2,33, 2,33, 0,18, 2,18, 2,18, 0, 7, 2, 7, 2, 7, 0, 0, 23,23,0,0,0, 0,
    0, 0,33,33,33,33,33, 0,18,18,18,18,18, 0, 7, 7, 7, 7, 7, 0, 0, 23,23,0,0,0, 0,
    0, 0,33, 0,33, 0,33, 0,18, 0,18, 0,18, 0, 7, 0, 7, 0, 7, 0, 0, 0,23,23,23,0, 0
  
   ]
)




ThreeBlueGhostPacSprite = ColorAnimatedSprite(h=0, v=0, name="ThreeGhost", width=27, height=5, frames=6, framerate=1,grid=[])

ThreeBlueGhostPacSprite.grid.append(
  [
    0,  0,0,14,14,14, 0, 0, 0,14,14,14, 0, 0, 0,14,14,14, 0, 0, 0, 0,23,23,23,0, 0,
    0, 0,14,14,14,14,14, 0,14,14,14,14,14, 0,14,14,14,14,14, 0, 0, 0,0,23,23,23, 0,
    0, 0,14, 2,14, 2,14, 0,14, 2,14, 2,14, 0,14, 2,14, 2,14, 0, 0, 0,0,0,23,23, 0,
    0, 0,14,14,14,14,14, 0,14,14,14,14,14, 0,14,14,14,14,14, 0, 0, 0,0,23,23,23, 0,
    0, 0,14, 0,14, 0,14, 0,14, 0,14, 0,14, 0,14, 0,14, 0,14, 0, 0, 0,23,23,23,0, 0
  
   ]
)


ThreeBlueGhostPacSprite.grid.append(
  [
    0, 0, 0,14,14,14, 0, 0, 0,14,14,14, 0, 0, 0,14,14,14, 0, 0, 0, 0,23,23,23,0, 0,
    0, 0,14,14,14,14,14, 0,14,14,14,14,14, 0,14,14,14,14,14, 0, 0, 23,23,23,23,23, 0,
    0, 0,14, 2,14, 2,14, 0,14, 2,14, 2,14, 0,14, 2,14, 2,14, 0, 0, 0,0,0,23,23, 0,
    0, 0,14,14,14,14,14, 0,14,14,14,14,14, 0,14,14,14,14,14, 0, 0, 23,23,23,23,23, 0,
    0, 0,14, 0,14, 0,14, 0,14, 0,14, 0,14, 0,14, 0,14, 0,14, 0, 0, 0,23,23,23,0, 0
  
   ]
)



ThreeBlueGhostPacSprite.grid.append(
  [
    0,  0,0,14,14,14, 0, 0, 0,14,14,14, 0, 0, 0,14,14,14, 0, 0, 0, 0,23,23,23,0, 0,
    0, 0,14,14,14,14,14, 0,14,14,14,14,14, 0,14,14,14,14,14, 0, 0, 23,23,23,23,23, 0,
    0, 0,14, 2,14, 2,14, 0,14, 2,14, 2,14, 0,14, 2,14, 2,14, 0, 0, 23,23,23,23,23, 0,
    0, 0,14,14,14,14,14, 0,14,14,14,14,14, 0,14,14,14,14,14, 0, 0, 23,23,23,23,23, 0,
    0, 0,14, 0,14, 0,14, 0,14, 0,14, 0,14, 0,14, 0,14, 0,14, 0, 0, 0,23,23,23,0, 0
  
   ]
)

ThreeBlueGhostPacSprite.grid.append(
  [
    0,  0,0,14,14,14, 0, 0, 0,14,14,14, 0, 0, 0,14,14,14, 0, 0, 0, 0,23,23,23,0, 0,
    0, 0,14,14,14,14,14, 0,14,14,14,14,14, 0,14,14,14,14,14, 0, 0, 0,23,23,23,23, 0,
    0, 0,14, 2,14, 2,14, 0,14, 2,14, 2,14, 0,14, 2,14, 2,14, 0, 0, 0,0,23,23,23, 0,
    0, 0,14,14,14,14,14, 0,14,14,14,14,14, 0,14,14,14,14,14, 0, 0, 0,23,23,23,23, 0,
    0, 0,14, 0,14, 0,14, 0,14, 0,14, 0,14, 0,14, 0,14, 0,14, 0, 0, 0,23,23,23,0, 0
  
   ]
)

 
ThreeBlueGhostPacSprite.grid.append(
  [
    0,  0,0,14,14,14, 0, 0, 0,14,14,14, 0, 0, 0,14,14,14, 0, 0, 0, 0,23,23,23,0, 0,
    0, 0,14,14,14,14,14, 0,14,14,14,14,14, 0,14,14,14,14,14, 0, 0, 0,0,0,23,23, 0,
    0, 0,14, 2,14, 2,14, 0,14, 2,14, 2,14, 0,14, 2,14, 2,14, 0, 0, 0,0,0,0,23, 0,
    0, 0,14,14,14,14,14, 0,14,14,14,14,14, 0,14,14,14,14,14, 0, 0, 0,0,0,23,23, 0,
    0, 0,14, 0,14, 0,14, 0,14, 0,14, 0,14, 0,14, 0,14, 0,14, 0, 0, 0,23,23,23,0, 0
  
   ]
)

ThreeBlueGhostPacSprite.grid.append(
  [
    0,  0,0,14,14,14, 0, 0, 0,14,14,14, 0, 0, 0,14,14,14, 0, 0, 0, 0,23,23,23,0, 0,
    0, 0,14,14,14,14,14, 0,14,14,14,14,14, 0,14,14,14,14,14, 0, 0, 0,0,0,23,23, 0,
    0, 0,14, 2,14, 2,14, 0,14, 2,14, 2,14, 0,14, 2,14, 2,14, 0, 0, 0,0,0,0,23, 0,
    0, 0,14,14,14,14,14, 0,14,14,14,14,14, 0,14,14,14,14,14, 0, 0, 0,0,0,23,23, 0,
    0, 0,14, 0,14, 0,14, 0,14, 0,14, 0,14, 0,14, 0,14, 0,14, 0, 0, 0,23,23,23,0,  0
  
   ]
)






ThreeGhostSprite = ColorAnimatedSprite(h=0, v=0, name="ThreeGhost", width=19, height=5, frames=1, framerate=1,grid=[])
ThreeGhostSprite.grid.append(
  [
   0, 0,33,33,33, 0, 0, 0,18,18,18, 0, 0, 0, 7, 7, 7, 0, 0, 
   0,33,33,33,33,33, 0,18,18,18,18,18, 0, 7, 7, 7, 7, 7, 0, 
   0,33, 2,33, 2,33, 0,18, 2,18, 2,18, 0, 7, 2, 7, 2, 7, 0, 
   0,33,33,33,33,33, 0,18,18,18,18,18, 0, 7, 7, 7, 7, 7, 0, 
   0,33, 0,33, 0,33, 0,18, 0,18, 0,18, 0, 7, 0, 7, 0, 7, 0 
  
   ]
)


ThreeBlueGhostSprite = ColorAnimatedSprite(h=0, v=0, name="ThreeBlueGhost", width=19, height=5, frames=1, framerate=1,grid=[])
ThreeBlueGhostSprite.grid.append(
  [
   0, 0, 0,14,14,14, 0, 0, 0,14,14,14, 0, 0, 0,14,14,14, 0, 0, 
   0, 0,14,14,14,14,14, 0,14,14,14,14,14, 0,14,14,14,14,14, 0, 
   0, 0,14, 2,14, 2,14, 0,14, 2,14, 2,14, 0,14, 2,14, 2,14, 0, 
   0, 0,14,14,14,14,14, 0,14,14,14,14,14, 0,14,14,14,14,14, 0, 
   0, 0,14, 0,14, 0,14, 0,14, 0,14, 0,14, 0,14, 0,14, 0,14, 0 
  
   ]
)


#This one is a color animated object
PacManSprite = ColorAnimatedSprite(h=0, v=0, name="PacDot", width=5, height=5, frames=5, framerate=1,grid=[])
PacManSprite.grid.append(
  [0,23,23,23,0,
   23,23,23,0,0,
   23,23,0,0,0,
   23,23,23,0,0,
   0,23,23,23,0]
)

PacManSprite.grid.append(
  [0,23,23,23,0,
   23,23,23,23,23,
   23,23,0,0,0,
   23,23,23,23,23,
   0,23,23,23,0]
)


PacManSprite.grid.append(
  [0,23,23,23,0,
   23,23,23,23,23,
   23,23,23,23,23,
   23,23,23,23,23,
   0,23,23,23,0]
)
PacManSprite.grid.append(
  [0,23,23,23,0,
   23,23,23,23,0,
   23,23,23,0,0,
   23,23,23,23,0,
   0,23,23,23,0]
)

PacManSprite.grid.append(
  [0,23,23,23,0,
   23,23,0,0,0,
   23,0,0,0,0,
   23,23,0,0,0,
   0,23,23,23,0]
)

# Make left and right facing pacmen
PacManRightSprite  = copy.deepcopy(PacManSprite)
PacManLeftSprite  = copy.deepcopy(PacManSprite)
PacManLeftSprite.HorizontalFlip()





#single color object (very old)
PacDotAnimatedSprite = AnimatedSprite(5,5,YellowR,YellowG,YellowB,4,[])
PacDotAnimatedSprite.grid.append(
  [0,1,1,1,0,
   1,1,1,0,0,
   1,1,0,0,0,
   1,1,1,0,0,
   0,1,1,1,0]
)

PacDotAnimatedSprite.grid.append(
  [0,1,1,1,0,
   1,1,1,1,1,
   1,1,0,0,0,
   1,1,1,1,1,
   0,1,1,1,0]
)


PacDotAnimatedSprite.grid.append(
  [0,1,1,1,0,
   1,1,1,1,1,
   1,1,1,1,1,
   1,1,1,1,1,
   0,1,1,1,0]
)
PacDotAnimatedSprite.grid.append(
  [0,1,1,1,0,
   1,1,1,1,0,
   1,1,1,0,0,
   1,1,1,1,0,
   0,1,1,1,0]
)

PacDotAnimatedSprite.grid.append(
  [0,1,1,1,0,
   1,1,0,0,0,
   1,0,0,0,0,
   1,1,0,0,0,
   0,1,1,1,0]
)


# Make left and right facing pacmen
PacRightAnimatedSprite = copy.deepcopy(PacDotAnimatedSprite)
PacLeftAnimatedSprite  = copy.deepcopy(PacDotAnimatedSprite)
PacLeftAnimatedSprite.HorizontalFlip()




DotZerkRobot = ColorAnimatedSprite(h=0, v=0, name="Robot", width=10, height=8, frames=9, framerate=1,grid=[])
DotZerkRobot.grid.append(
  [
    0, 0, 0, 6, 6, 6, 6, 0, 0, 0,
    0, 0, 6, 8, 1, 6, 6, 6, 0, 0,
    0, 6, 6, 6, 6, 6, 6, 6, 6, 0,
    0, 6, 0, 6, 6, 6, 6, 0, 6, 0,
    0, 6, 0, 6, 6, 6, 6, 0, 6, 0,
    0, 0, 0, 6, 6, 6, 6, 0, 0, 0,
    0, 0, 0, 6, 0, 0, 6, 0, 0, 0,
    0, 0, 6, 6, 0, 0, 6, 6, 0, 0

  ]
)
DotZerkRobot.grid.append(
  [
    0, 0, 0, 6, 6, 6, 6, 0, 0, 0,
    0, 0, 6, 1, 8, 6, 6, 6, 0, 0,
    0, 6, 6, 6, 6, 6, 6, 6, 6, 0,
    0, 6, 0, 6, 6, 6, 6, 0, 6, 0,
    0, 6, 0, 6, 6, 6, 6, 0, 6, 0,
    0, 0, 0, 6, 6, 6, 6, 0, 0, 0,
    0, 0, 0, 6, 0, 0, 6, 0, 0, 0,
    0, 0, 6, 6, 0, 0, 6, 6, 0, 0

  ]
)
DotZerkRobot.grid.append(
  [
    0, 0, 0, 6, 6, 6, 6, 0, 0, 0,
    0, 0, 6, 6, 1, 8, 6, 6, 0, 0,
    0, 6, 6, 6, 6, 6, 6, 6, 6, 0,
    0, 6, 0, 6, 6, 6, 6, 0, 6, 0,
    0, 6, 0, 6, 6, 6, 6, 0, 6, 0,
    0, 0, 0, 6, 6, 6, 6, 0, 0, 0,
    0, 0, 0, 6, 0, 0, 6, 0, 0, 0,
    0, 0, 6, 6, 0, 0, 6, 6, 0, 0

  ]
)
DotZerkRobot.grid.append(
  [
    0, 0, 0, 6, 6, 6, 6, 0, 0, 0,
    0, 0, 6, 6, 6, 1, 8, 6, 0, 0,
    0, 6, 6, 6, 6, 6, 6, 6, 6, 0,
    0, 6, 0, 6, 6, 6, 6, 0, 6, 0,
    0, 6, 0, 6, 6, 6, 6, 0, 6, 0,
    0, 0, 0, 6, 6, 6, 6, 0, 0, 0,
    0, 0, 0, 6, 0, 0, 6, 0, 0, 0,
    0, 0, 6, 6, 0, 0, 6, 6, 0, 0

  ]
)


DotZerkRobot.grid.append(
  [
    0, 0, 0, 6, 6, 6, 6, 0, 0, 0,
    0, 0, 6, 6, 6, 1, 8, 6, 0, 0,
    0, 6, 6, 6, 6, 6, 6, 6, 6, 0,
    0, 6, 0, 6, 6, 6, 6, 0, 6, 0,
    0, 6, 0, 6, 6, 6, 6, 0, 6, 0,
    0, 0, 0, 6, 6, 6, 6, 0, 0, 0,
    0, 0, 0, 6, 0, 0, 6, 0, 0, 0,
    0, 0, 6, 6, 0, 0, 6, 6, 0, 0

  ]
)

DotZerkRobot.grid.append(
  [
    0, 0, 0, 6, 6, 6, 6, 0, 0, 0,
    0, 0, 6, 6, 6, 8, 1, 6, 0, 0,
    0, 6, 6, 6, 6, 6, 6, 6, 6, 0,
    0, 6, 0, 6, 6, 6, 6, 0, 6, 0,
    0, 6, 0, 6, 6, 6, 6, 0, 6, 0,
    0, 0, 0, 6, 6, 6, 6, 0, 0, 0,
    0, 0, 0, 6, 0, 0, 6, 0, 0, 0,
    0, 0, 6, 6, 0, 0, 6, 6, 0, 0

  ]
)


DotZerkRobot.grid.append(
  [
    0, 0, 0, 6, 6, 6, 6, 0, 0, 0,
    0, 0, 6, 6, 8, 1, 6, 6, 0, 0,
    0, 6, 6, 6, 6, 6, 6, 6, 6, 0,
    0, 6, 0, 6, 6, 6, 6, 0, 6, 0,
    0, 6, 0, 6, 6, 6, 6, 0, 6, 0,
    0, 0, 0, 6, 6, 6, 6, 0, 0, 0,
    0, 0, 0, 6, 0, 0, 6, 0, 0, 0,
    0, 0, 6, 6, 0, 0, 6, 6, 0, 0

  ]
)


DotZerkRobot.grid.append(
  [
    0, 0, 0, 6, 6, 6, 6, 0, 0, 0,
    0, 0, 6, 8, 1, 6, 6, 6, 0, 0,
    0, 6, 6, 6, 6, 6, 6, 6, 6, 0,
    0, 6, 0, 6, 6, 6, 6, 0, 6, 0,
    0, 6, 0, 6, 6, 6, 6, 0, 6, 0,
    0, 0, 0, 6, 6, 6, 6, 0, 0, 0,
    0, 0, 0, 6, 0, 0, 6, 0, 0, 0,
    0, 0, 6, 6, 0, 0, 6, 6, 0, 0

  ]
)

DotZerkRobot.grid.append(
  [
    0, 0, 0, 6, 6, 6, 6, 0, 0, 0,
    0, 0, 6, 8, 1, 6, 6, 6, 0, 0,
    0, 6, 6, 6, 6, 6, 6, 6, 6, 0,
    0, 6, 0, 6, 6, 6, 6, 0, 6, 0,
    0, 6, 0, 6, 6, 6, 6, 0, 6, 0,
    0, 0, 0, 6, 6, 6, 6, 0, 0, 0,
    0, 0, 0, 6, 0, 0, 6, 0, 0, 0,
    0, 0, 6, 6, 0, 0, 6, 6, 0, 0,

  ]
)




DotZerkRobotWalking = ColorAnimatedSprite(h=0, v=0, name="Robot", width=10, height=8, frames=2, framerate=1,grid=[])
DotZerkRobotWalking.grid.append(
  [
    0, 0, 0, 6, 6, 6, 6, 0, 0, 0,
    0, 0, 6,14,14, 6, 6, 6, 0, 0,
    0, 6, 6, 6, 6, 6, 6, 6, 6, 0,
    0, 6, 0, 6, 6, 6, 6, 0, 6, 0,
    0, 6, 0, 6, 6, 6, 6, 0, 6, 0,
    0, 0, 0, 6, 6, 6, 6, 0, 0, 0,
    0, 0, 0, 6, 0, 0, 6, 0, 0, 0,
    0, 0, 6, 6, 0, 6, 6, 0, 0, 0,

  ]
)
DotZerkRobotWalking.grid.append(
  [
    0, 0, 0, 6, 6, 6, 6, 0, 0, 0,
    0, 0, 6,14,14, 6, 6, 6, 0, 0,
    0, 6, 6, 6, 6, 6, 6, 6, 6, 0,
    0, 6, 0, 6, 6, 6, 6, 0, 6, 0,
    0, 6, 0, 6, 6, 6, 6, 0, 6, 0,
    0, 0, 0, 0, 6, 6, 0, 0, 0, 0,
    0, 0, 0, 0, 6, 6, 0, 0, 0, 0,
    0, 0, 0, 6, 6, 6, 0, 0, 0, 0

  ]
)


DotZerkRobotWalkingSmall = ColorAnimatedSprite(h=0, v=0, name="Robot", width=9, height=5, frames=4, framerate=1,grid=[])
DotZerkRobotWalkingSmall.grid.append(
  [
   0, 0, 0,10,10,10,10, 0, 0,
   0, 0,10, 7, 7,10,10,10, 0,
   0, 0,10,10,10,10,10,10, 0,
   0, 0,10, 0, 0, 0, 0,10, 0,
   0, 10,10, 0, 0, 0,10,10, 0

  ]
)
DotZerkRobotWalkingSmall.grid.append(
  [
   0, 0, 0,10,10,10,10, 0, 0,
   0, 0,10, 7, 7,10,10,10, 0,
   0, 0,10,10,10,10,10,10, 0,
   0, 0, 0,10, 0, 0,10, 0, 0,
   0, 0,10,10, 0,10,10, 0, 0,

  ]
)

DotZerkRobotWalkingSmall.grid.append(
  [
   0, 0, 0,10,10,10,10, 0, 0,
   0, 0,10, 7, 7,10,10,10, 0,
   0, 0,10,10,10,10,10,10, 0,
   0, 0, 0, 0,10,10, 0, 0, 0,
   0, 0, 0,10,10,10, 0, 0, 0,

  ]
)
DotZerkRobotWalkingSmall.grid.append(
  [
   0, 0, 0,10,10,10,10, 0, 0,
   0, 0,10, 7, 7,10,10,10, 0,
   0, 0,10,10,10,10,10,10, 0,
   0, 0, 0,10, 0, 0,10, 0, 0,
   0, 0,10,10, 0,10,10, 0, 0,

  ]
)





RunningManSprite = ColorAnimatedSprite(
  h=0, 
  v=0, 
  name="RunningMan", 
  width  = 19, 
  height = 18, 
  frames = 0, 
  framerate=2,
  grid=[]  )

                 

RunningManSpriteMap = TextMap(
  h      = 1,
  v      = 1,
  width  = 19, 
  height = 18
  )

RunningManSpriteMap.ColorList = {
  ' ' : 0,
  '-' : 1,
  '.' : 2,
  'o' : 15,  # Med Blue
  'O' : 4,  
  'r' : 5,
  'R' : 8,
  'b' : 12,
  'B' : 13,
  '#' : 27
}

RunningManSpriteMap.TypeList = {
  ' ' : 'Empty',
  '-' : 'wall',
  '.' : 'wall',
  'o' : 'wall',
  'O' : 'wall'
}



RunningManSpriteMap.map= (
  #0.........1.........2.....
  "                   ", 
  "          oooo     ", 
  "          oo       ", 
  "      oooooooo     ", 
  "    oooooooo       ", 
  "    oo  oooo    oo ", 
  "    oo  oooooooo   ", 
  "                   ", 
  "        oooo       ", 
  "        oooo       ", 
  "      oooooooooooo ", 
  "      oo        oo ", 
  "    oooo      oo   ", 
  "    oo        oo   ", 
  "  oooo             ", 
  "  oo               ", 
  "  oo               ", 
  "                   ", 

  )
      
RunningManSpriteMap.CopyMapToColorSprite(TheSprite=RunningManSprite)


RunningManSpriteMap.map= (
  #0.........1.........2.....
  "                   ", 
  "          oooo     ", 
  "          oo       ", 
  "  oooooooooooo     ", 
  "  oo    oooo       ", 
  "  oo    oooooooooo ", 
  "        oooo       ", 
  "                   ", 
  "        oooo       ", 
  "        oooo       ", 
  "      oooooooooooo ", 
  "      oo        oo ", 
  "    oooo        oo ", 
  "    oo          oo ", 
  "  oooo             ", 
  "  oo               ", 
  "                   ", 
  "                   ", 
  )

RunningManSpriteMap.CopyMapToColorSprite(TheSprite=RunningManSprite)


RunningManSpriteMap.map= (
  #0.........1.........2.....
  "                   ", 
  "          oooo     ", 
  "          oo       ", 
  "      oooooooo     ", 
  "    oooooooo       ", 
  "    oo  oooooooooo ", 
  "    oo  oooo       ", 
  "                   ", 
  "        oooo       ", 
  "        oooo       ", 
  "      oooooooo     ", 
  "      oo    oo     ", 
  "    oooo    oooo   ", 
  "  oooo        oo   ", 
  "  oo          oo   ", 
  "              oooo ", 
  "                   ", 
  "                   ", 
  )

RunningManSpriteMap.CopyMapToColorSprite(TheSprite=RunningManSprite)


RunningManSpriteMap.map= (
  #0.........1.........2.....
  "                   ", 
  "          oooo     ", 
  "          oo       ", 
  "        oooooo     ", 
  "    oooooooo       ", 
  "    oo  oooooo     ", 
  "    oo  oooo  oo   ", 
  "                   ", 
  "        oooo       ", 
  "      oooooo       ", 
  "      oooooooo     ", 
  "      oo    oo     ", 
  "  oooooo    oo     ", 
  "  oo        oo     ", 
  "  oo        oo     ", 
  "            oooo   ", 
  "                   ", 
  "                   ", 
  )

RunningManSpriteMap.CopyMapToColorSprite(TheSprite=RunningManSprite)


RunningManSpriteMap.map= (
  #0.........1.........2.....
  "                   ", 
  "          oooo     ", 
  "          oo       ", 
  "        oooooo     ", 
  "      oooooo       ", 
  "      oooooo       ", 
  "      oooooo       ", 
  "      oooooooooo   ", 
  "        oooo       ", 
  "        oooo       ", 
  "        oooo       ", 
  "        oooo       ", 
  "    oooooooo       ", 
  "    oo    oo       ", 
  "    oo    oo       ", 
  "          oooo     ", 
  "                   ", 
  "                   ", 
  )

RunningManSpriteMap.CopyMapToColorSprite(TheSprite=RunningManSprite)


RunningManSpriteMap.map= (
  #0.........1.........2.....
  "                   ", 
  "          oooo     ", 
  "          oo       ", 
  "        oooooo     ", 
  "      oooooo       ", 
  "      oooooo       ", 
  "      oooooo       ", 
  "        oooo       ", 
  "        oooo       ", 
  "        oooo       ", 
  "        oooo       ", 
  "        oooo       ", 
  "    oooooooo       ", 
  "    oo  oo         ", 
  "    oo  oo         ", 
  "        oooo       ", 
  "                   ", 
  "                   ", 
  )

RunningManSpriteMap.CopyMapToColorSprite(TheSprite=RunningManSprite)



RunningManSpriteMap.map= (
  #0.........1.........2.....
  "                   ", 
  "          oooo     ", 
  "          oo       ", 
  "        oooooo     ", 
  "      oooooo       ", 
  "      oooooooo     ", 
  "      oooooooo     ", 
  "      oooooooooo   ", 
  "        oooo       ", 
  "        oooooo     ", 
  "      oooooooooo   ", 
  "      oo      oo   ", 
  "      oo  oooooo   ", 
  "      oo  oo       ", 
  "      oo           ", 
  "        oo         ", 
  "                   ", 
  "                   ", 
  )

RunningManSpriteMap.CopyMapToColorSprite(TheSprite=RunningManSprite)




RunningManSpriteMap.map= (
  #0.........1.........2.....
  "                   ", 
  "          oooo     ", 
  "          oo       ", 
  "        oooooo     ", 
  "      oooooo       ", 
  "    oooooooo       ", 
  "    oo  oooooooo   ", 
  "    oo             ", 
  "        oooo       ", 
  "        oooooo     ", 
  "      oooooooooooo ", 
  "      oo        oo ", 
  "      oo    oooooo ", 
  "    oo      oo     ", 
  "    oo             ", 
  "    oo             ", 
  "                   ", 
  "                   ", 
  )

RunningManSpriteMap.CopyMapToColorSprite(TheSprite=RunningManSprite)






RunningMan2Sprite = ColorAnimatedSprite(
  h=0, 
  v=0, 
  name="RunningMan", 
  width  = 19, 
  height = 18, 
  frames = 0, 
  framerate=2,
  grid=[]  )

                 

RunningMan2SpriteMap = TextMap(
  h      = 1,
  v      = 1,
  width  = 19, 
  height = 18
  )

RunningMan2SpriteMap.ColorList = {
  ' ' : 0,
  '-' : 14, # Dark blue
  '.' : 16, # Med  blue
  'o' : 15, # Low  blue
  'O' : 16, # Med  blue
  'r' : 5,
  'R' : 8,
  'b' : 12,
  'B' : 13,
  '#' : 27
}

RunningMan2SpriteMap.TypeList = {
  ' ' : 'Empty',
  '-' : 'wall',
  '.' : 'wall',
  'o' : 'wall',
  'O' : 'wall'
}



RunningMan2SpriteMap.map= (
  #0.........1.........2.....
  "                   ", 
  "          oooo     ", 
  "          oo       ", 
  "      oooooooo     ", 
  "    oooooooo       ", 
  "    oo  oooo    OO ", 
  "    oo  oooooooo   ", 
  "                   ", 
  "        oooo       ", 
  "        oooo       ", 
  "      oooooooooooo ", 
  "      oo        oo ", 
  "    oooo      oo   ", 
  "    oo        --   ", 
  "  oooo             ", 
  "  .o               ", 
  "  .o               ", 
  "                   ", 

  )
      
RunningMan2SpriteMap.CopyMapToColorSprite(TheSprite=RunningMan2Sprite)


RunningMan2SpriteMap.map= (
  #0.........1.........2.....
  "                   ", 
  "          oooo     ", 
  "          oo       ", 
  "  oooooooooooo     ", 
  "  oo    oooo       ", 
  "  oo    ooooooooOO ", 
  "        oooo       ", 
  "                   ", 
  "        oooo       ", 
  "        oooo       ", 
  "      oooooooooooo ", 
  "      oo        oo ", 
  "    oooo        oo ", 
  "    oo          -- ", 
  "  .ooo             ", 
  "  .o               ", 
  "                   ", 
  "                   ", 
  )

RunningMan2SpriteMap.CopyMapToColorSprite(TheSprite=RunningMan2Sprite)


RunningMan2SpriteMap.map= (
  #0.........1.........2.....
  "                   ", 
  "          oooo     ", 
  "          oo       ", 
  "      oooooooo     ", 
  "    oooooooo       ", 
  "    oo  ooooooOO   ", 
  "    oo  oooo       ", 
  "                   ", 
  "        oooo       ", 
  "        oooo       ", 
  "      oooooooo     ", 
  "      oo    oo     ", 
  "    oooo    oooo   ", 
  "  .ooo        oo   ", 
  "  .o          oo   ", 
  "              ---- ", 
  "                   ", 
  "                   ", 
  )

RunningMan2SpriteMap.CopyMapToColorSprite(TheSprite=RunningMan2Sprite)


RunningMan2SpriteMap.map= (
  #0.........1.........2.....
  "                   ", 
  "          oooo     ", 
  "          oo       ", 
  "        oooooo     ", 
  "    oooooooo       ", 
  "    oo  oooo       ", 
  "    oo  ooooooOO   ", 
  "                   ", 
  "        oooo       ", 
  "      oooooo       ", 
  "      oooooooo     ", 
  "      oo    oo     ", 
  "  .ooooo    oo     ", 
  "  .o        oo     ", 
  "  .o        oo     ", 
  "            ----   ", 
  "                   ", 
  "                   ", 
  )

RunningMan2SpriteMap.CopyMapToColorSprite(TheSprite=RunningMan2Sprite)


RunningMan2SpriteMap.map= (
  #0.........1.........2.....
  "                   ", 
  "          oooo     ", 
  "          oo       ", 
  "        oooooo     ", 
  "      oooooo       ", 
  "      oooooo       ", 
  "      oooooo       ", 
  "      ooooooOO     ", 
  "        oooo       ", 
  "        oooo       ", 
  "        oooo       ", 
  "        oooo       ", 
  "    .ooooooo       ", 
  "    .o    oo       ", 
  "    .o    oo       ", 
  "          ----     ", 
  "                   ", 
  "                   ", 
  )

RunningMan2SpriteMap.CopyMapToColorSprite(TheSprite=RunningMan2Sprite)


RunningMan2SpriteMap.map= (
  #0.........1.........2.....
  "                   ", 
  "          oooo     ", 
  "          oo       ", 
  "        oooooo     ", 
  "      oooooo       ", 
  "      oooooo       ", 
  "      ooooOO       ", 
  "        oooo       ", 
  "        oooo       ", 
  "        oooo       ", 
  "        oooo       ", 
  "        oooo       ", 
  "    .ooooooo       ", 
  "    .o  oo         ", 
  "    .o  oo         ", 
  "        ----       ", 
  "                   ", 
  "                   ", 
  )

RunningMan2SpriteMap.CopyMapToColorSprite(TheSprite=RunningMan2Sprite)



RunningMan2SpriteMap.map= (
  #0.........1.........2.....
  "                   ", 
  "          oooo     ", 
  "          oo       ", 
  "        oooooo     ", 
  "      oooooo       ", 
  "      oooooooo     ", 
  "      oooooooo     ", 
  "      ooOOoooooo   ", 
  "        oooo       ", 
  "        oooooo     ", 
  "      oooooooooo   ", 
  "      oo      oo   ", 
  "      oo  .ooooo   ", 
  "      oo  .o       ", 
  "      -o           ", 
  "        --         ", 
  "                   ", 
  "                   ", 
  )

RunningMan2SpriteMap.CopyMapToColorSprite(TheSprite=RunningMan2Sprite)




RunningMan2SpriteMap.map= (
  #0.........1.........2.....
  "                   ", 
  "          oooo     ", 
  "          oo       ", 
  "        oooooo     ", 
  "      oooooo       ", 
  "    oooooooo       ", 
  "    oo  oooooooo   ", 
  "    OO             ", 
  "        oooo       ", 
  "        oooooo     ", 
  "      oooooooooooo ", 
  "      oo        oo ", 
  "      oo    .ooooo ", 
  "    -o      .o     ", 
  "    -o             ", 
  "    -o             ", 
  "                   ", 
  "                   ", 
  )

RunningMan2SpriteMap.CopyMapToColorSprite(TheSprite=RunningMan2Sprite)



RunningMan2SpriteMap.map= (
  #0.........1.........2.....
  "                   ", 
  "          oooo     ", 
  "          oo       ", 
  "      oooooooo     ", 
  "    oooooooo       ", 
  "    oo  oooo    oo ", 
  "    OO  oooooooo   ", 
  "                   ", 
  "        oooo       ", 
  "        oooo       ", 
  "      oooooooooooo ", 
  "      oo        oo ", 
  "    oooo      .o   ", 
  "    oo        .o   ", 
  "  -ooo             ", 
  "  -o               ", 
  "  -o               ", 
  "                   ", 

  )
      
RunningMan2SpriteMap.CopyMapToColorSprite(TheSprite=RunningMan2Sprite)


RunningMan2SpriteMap.map= (
  #0.........1.........2.....
  "                   ", 
  "          oooo     ", 
  "          oo       ", 
  "  oooooooooooo     ", 
  "  oo    oooo       ", 
  "  OO    oooooooooo ", 
  "        oooo       ", 
  "                   ", 
  "        oooo       ", 
  "        oooo       ", 
  "      oooooooooooo ", 
  "      oo        oo ", 
  "    oooo        oo ", 
  "    oo          .. ", 
  "  -ooo             ", 
  "  -o               ", 
  "                   ", 
  "                   ", 
  )

RunningMan2SpriteMap.CopyMapToColorSprite(TheSprite=RunningMan2Sprite)


RunningMan2SpriteMap.map= (
  #0.........1.........2.....
  "                   ", 
  "          oooo     ", 
  "          oo       ", 
  "      oooooooo     ", 
  "    oooooooo       ", 
  "    oo  oooooooo   ", 
  "    OO  oooo       ", 
  "                   ", 
  "        oooo       ", 
  "        oooo       ", 
  "      oooooooo     ", 
  "      oo    oo     ", 
  "    oooo    oooo   ", 
  "  -ooo        oo   ", 
  "  -o          oo   ", 
  "              .... ", 
  "                   ", 
  "                   ", 
  )

RunningMan2SpriteMap.CopyMapToColorSprite(TheSprite=RunningMan2Sprite)


RunningMan2SpriteMap.map= (
  #0.........1.........2.....
  "                   ", 
  "          oooo     ", 
  "          oo       ", 
  "        oooooo     ", 
  "    oooooooo       ", 
  "    oo  oooooo     ", 
  "    OO  oooo  oo   ", 
  "                   ", 
  "        oooo       ", 
  "      oooooo       ", 
  "      oooooooo     ", 
  "      oo    oo     ", 
  "  -ooooo    oo     ", 
  "  -o        oo     ", 
  "  -o        oo     ", 
  "            ....   ", 
  "                   ", 
  "                   ", 
  )

RunningMan2SpriteMap.CopyMapToColorSprite(TheSprite=RunningMan2Sprite)


RunningMan2SpriteMap.map= (
  #0.........1.........2.....
  "                   ", 
  "          oooo     ", 
  "          oo       ", 
  "        oooooo     ", 
  "      oooooo       ", 
  "      oooooo       ", 
  "      oooooo       ", 
  "      ooOOoooo     ", 
  "        oooo       ", 
  "        oooo       ", 
  "        oooo       ", 
  "        oooo       ", 
  "    -ooooooo       ", 
  "    -o    oo       ", 
  "    -o    oo       ", 
  "          ....     ", 
  "                   ", 
  "                   ", 
  )

RunningMan2SpriteMap.CopyMapToColorSprite(TheSprite=RunningMan2Sprite)


RunningMan2SpriteMap.map= (
  #0.........1.........2.....
  "                   ", 
  "          oooo     ", 
  "          oo       ", 
  "        oooooo     ", 
  "      oooooo       ", 
  "      oooooo       ", 
  "      ooooOO       ", 
  "        oooo       ", 
  "        oooo       ", 
  "        oooo       ", 
  "        oooo       ", 
  "        oooo       ", 
  "    -ooooooo       ", 
  "    -o  oo         ", 
  "    -o  oo         ", 
  "        ....       ", 
  "                   ", 
  "                   ", 
  )

RunningMan2SpriteMap.CopyMapToColorSprite(TheSprite=RunningMan2Sprite)



RunningMan2SpriteMap.map= (
  #0.........1.........2.....
  "                   ", 
  "          oooo     ", 
  "          oo       ", 
  "        oooooo     ", 
  "      oooooo       ", 
  "      oooooooo     ", 
  "      oooooooo     ", 
  "      ooooooooOO   ", 
  "        oooo       ", 
  "        oooooo     ", 
  "      oooooooooo   ", 
  "      oo      oo   ", 
  "      oo  -ooooo   ", 
  "      oo  -o       ", 
  "      .o           ", 
  "        ..         ", 
  "                   ", 
  "                   ", 
  )

RunningMan2SpriteMap.CopyMapToColorSprite(TheSprite=RunningMan2Sprite)




RunningMan2SpriteMap.map= (
  #0.........1.........2.....
  "                   ", 
  "          oooo     ", 
  "          oo       ", 
  "        oooooo     ", 
  "      oooooo       ", 
  "    oooooooo       ", 
  "    oo  ooooooOO   ", 
  "    oo             ", 
  "        oooo       ", 
  "        oooooo     ", 
  "      oooooooooooo ", 
  "      oo        oo ", 
  "      oo    -ooooo ", 
  "    .o      -o     ", 
  "    .o             ", 
  "    .o             ", 
  "                   ", 
  "                   ", 
  )

RunningMan2SpriteMap.CopyMapToColorSprite(TheSprite=RunningMan2Sprite)









RunningMan3Sprite = ColorAnimatedSprite(
  h=0, 
  v=0, 
  name="RunningMan", 
  width  = 33, 
  height = 18, 
  frames = 0, 
  framerate=2,
  grid=[]  )

                 

RunningMan3SpriteMap = TextMap(
  h      = 1,
  v      = 1,
  width  = 33, 
  height = 18
  )

RunningMan3SpriteMap.ColorList = {
  ' ' : 0,
  '-' : 17, # Dark orange
  '.' : 19, # Med  orange
  'o' : 6,  # Low  Red
  'O' : 7,  # Med  Red
  'r' : 5,
  'R' : 8,
  'b' : 12,
  '*' : 45, #bright white
  '#' : 1  # dark grey
}

RunningMan3SpriteMap.TypeList = {
  ' ' : 'Empty'
  
}



RunningMan3SpriteMap.map= (
  #0.........1.........2.........3...
  "                                 ", 
  "               oooo          **  ", 
  "               oo         ##     ", 
  "           oooooooo    ##        ", 
  "         oooooooo   #oo          ", 
  "         oo  oooo##oo            ", 
  "         oo  o##o                ", 
  "         oo##                    ", 
  "        ##   oooo                ", 
  "     ##      oooo                ", 
  "  ##        ooooooooooo          ", 
  "           oo        oo          ", 
  "         oooo      oo            ", 
  "         oo        --            ", 
  "       oooo                      ", 
  "       .o                        ", 
  "       .o                        ", 
  "                                 ", 

  )
      
RunningMan3SpriteMap.CopyMapToColorSprite(TheSprite=RunningMan3Sprite)


RunningMan3SpriteMap.map= (
  #0.........1.........2.....
  "                                 ", 
  "               oooo          **  ", 
  "               oo         ##     ", 
  "           oooooooo    ##        ", 
  "         oooooooo   #oo          ", 
  "         oo  oooo##oo            ", 
  "         oo  o##o                ", 
  "         oo##                    ", 
  "        ##   oooo                ", 
  "     ##      oooo                ", 
  "  ##        ooooooooooo          ", 
  "           oo        oo          ", 
  "         oooo        oo          ", 
  "         oo          --          ", 
  "       .ooo                      ", 
  "       .o                        ", 
  "                                 ", 
  "                                 ", 
  )

RunningMan3SpriteMap.CopyMapToColorSprite(TheSprite=RunningMan3Sprite)


RunningMan3SpriteMap.map= (
  #0.........1.........2.....
  "                                 ", 
  "               oooo          **  ", 
  "               oo         ##     ", 
  "           oooooooo    ##        ", 
  "         oooooooo   #oo          ", 
  "         oo  oooo##oo            ", 
  "         oo  o##o                ", 
  "         oo##                    ", 
  "        ##   oooo                ", 
  "     ##      oooo                ", 
  "  ##        ooooooo              ", 
  "           oo    oo              ", 
  "         oooo    oooo            ", 
  "       .ooo        oo            ", 
  "       .o          oo            ", 
  "                   ----          ", 
  "                                 ", 
  "                                 ", 
  )

RunningMan3SpriteMap.CopyMapToColorSprite(TheSprite=RunningMan3Sprite)


RunningMan3SpriteMap.map= (
  #0.........1.........2.....
  "                                 ", 
  "               oooo          **  ", 
  "               oo         ##     ", 
  "           oooooooo    ##        ", 
  "         oooooooo   #oo          ", 
  "         oo  oooo##oo            ", 
  "         oo  o##o                ", 
  "         oo##                    ", 
  "        ##   oooo                ", 
  "     ##      oooo                ", 
  "  ##        ooooooo              ", 
  "           oo    oo              ", 
  "       .ooooo    oo              ", 
  "       .o        oo              ", 
  "       .o        oo              ", 
  "                 ----            ", 
  "                                 ", 
  "                                 ", 
  )

RunningMan3SpriteMap.CopyMapToColorSprite(TheSprite=RunningMan3Sprite)


RunningMan3SpriteMap.map= (
  #0.........1.........2.....
  "                                 ", 
  "               oooo          **  ", 
  "               oo         ##     ", 
  "           oooooooo    ##        ", 
  "         oooooooo   #oo          ", 
  "         oo  oooo##oo            ", 
  "         oo  o##o                ", 
  "         oo##                    ", 
  "        ##   oooo                ", 
  "     ##      oooo                ", 
  "  ##        oooooo               ", 
  "             oooo                ", 
  "         .ooooooo                ", 
  "         .o    oo                ", 
  "         .o    oo                ", 
  "               ----              ", 
  "                                 ", 
  "                                 ", 
  )

RunningMan3SpriteMap.CopyMapToColorSprite(TheSprite=RunningMan3Sprite)


RunningMan3SpriteMap.map= (
  #0.........1.........2.....
  "                                 ", 
  "               oooo          **  ", 
  "               oo         ##     ", 
  "           oooooooo    ##        ", 
  "         oooooooo   #oo          ", 
  "         oo  oooo##oo            ", 
  "         oo  o##o                ", 
  "         oo##                    ", 
  "        ##   oooo                ", 
  "     ##      oooo                ", 
  "  ##        oooooo               ", 
  "             oooo                ", 
  "         .ooooooo                ", 
  "         .o  oo                  ", 
  "         .o  oo                  ", 
  "             ----                ", 
  "                                 ", 
  "                                 ", 
  )

RunningMan3SpriteMap.CopyMapToColorSprite(TheSprite=RunningMan3Sprite)



RunningMan3SpriteMap.map= (
  #0.........1.........2.....
  "                                 ", 
  "               oooo          **  ", 
  "               oo         ##     ", 
  "           oooooooo    ##        ", 
  "         oooooooo   #oo          ", 
  "         oo  oooo##oo            ", 
  "         oo  o##o                ", 
  "         oo##                    ", 
  "        ##   oooo                ", 
  "     ##      oooo                ", 
  "  ##        ooooooooo            ", 
  "           oo      oo            ", 
  "           oo  .ooooo            ", 
  "           oo  .o                ", 
  "           -o                    ", 
  "             --                  ", 
  "                                 ", 
  "                                 ", 
  )

RunningMan3SpriteMap.CopyMapToColorSprite(TheSprite=RunningMan3Sprite)




RunningMan3SpriteMap.map= (
  #0.........1.........2.....
  "                                 ", 
  "               oooo          **  ", 
  "               oo         ##     ", 
  "           oooooooo    ##        ", 
  "         oooooooo   #oo          ", 
  "         oo  oooo##oo            ", 
  "         oo  o##o                ", 
  "         oo##                    ", 
  "        ##   oooo                ", 
  "     ##      oooo                ", 
  "  ##        ooooooooooo          ", 
  "           oo        oo          ", 
  "           oo    .ooooo          ", 
  "         -o      .o              ", 
  "         -o                      ", 
  "         -o                      ", 
  "                                 ", 
  "                                 ", 
  )

RunningMan3SpriteMap.CopyMapToColorSprite(TheSprite=RunningMan3Sprite)



RunningMan3SpriteMap.map= (
  #0.........1.........2.....
  "                                 ", 
  "               oooo          **  ", 
  "               oo         ##     ", 
  "           oooooooo    ##        ", 
  "         oooooooo   #oo          ", 
  "         oo  oooo##oo            ", 
  "         oo  o##o                ", 
  "         oo##                    ", 
  "        ##   oooo                ", 
  "     ##      oooo                ", 
  "  ##        ooooooooooo          ", 
  "           oo        oo          ", 
  "         oooo      .o            ", 
  "         oo        .o            ", 
  "       -ooo                      ", 
  "       -o                        ", 
  "       -o                        ", 
  "                                 ", 

  )
      
RunningMan3SpriteMap.CopyMapToColorSprite(TheSprite=RunningMan3Sprite)


RunningMan3SpriteMap.map= (
  #0.........1.........2.....
  "                                 ", 
  "               oooo          **  ", 
  "               oo         ##     ", 
  "           oooooooo    ##        ", 
  "         oooooooo   #oo          ", 
  "         oo  oooo##oo            ", 
  "         oo  o##o                ", 
  "         oo##                    ", 
  "        ##   oooo                ", 
  "     ##      oooo                ", 
  "  ##        ooooooooooo          ", 
  "           oo        oo          ", 
  "         oooo        oo          ", 
  "         oo          ..          ", 
  "       -ooo                      ", 
  "       -o                        ", 
  "                                 ", 
  "                                 ", 
  )

RunningMan3SpriteMap.CopyMapToColorSprite(TheSprite=RunningMan3Sprite)


RunningMan3SpriteMap.map= (
  #0.........1.........2.....
  "                                 ", 
  "               oooo          **  ", 
  "               oo         ##     ", 
  "           oooooooo    ##        ", 
  "         oooooooo   #oo          ", 
  "         oo  oooo##oo            ", 
  "         oo  o##o                ", 
  "         oo##                    ", 
  "        ##   oooo                ", 
  "     ##      oooo                ", 
  "  ##        ooooooo              ", 
  "           oo    oo              ", 
  "         oooo    oooo            ", 
  "       -ooo        oo            ", 
  "       -o          oo            ", 
  "                   ....          ", 
  "                                 ", 
  "                                 ", 
  )

RunningMan3SpriteMap.CopyMapToColorSprite(TheSprite=RunningMan3Sprite)


RunningMan3SpriteMap.map= (
  #0.........1.........2.....
  "                                 ", 
  "               oooo          **  ", 
  "               oo         ##     ", 
  "           oooooooo    ##        ", 
  "         oooooooo   #oo          ", 
  "         oo  oooo##oo            ", 
  "         oo  o##o                ", 
  "         oo##                    ", 
  "        ##   oooo                ", 
  "     ##      oooo                ", 
  "  ##        ooooooo              ", 
  "           oo    oo              ", 
  "       -ooooo    oo              ", 
  "       -o        oo              ", 
  "       -o        oo              ", 
  "                 ....            ", 
  "                                 ", 
  "                                 ", 
  )

RunningMan3SpriteMap.CopyMapToColorSprite(TheSprite=RunningMan3Sprite)


RunningMan3SpriteMap.map= (
  #0.........1.........2.....
  "                                 ", 
  "               oooo          **  ", 
  "               oo         ##     ", 
  "           oooooooo    ##        ", 
  "         oooooooo   #oo          ", 
  "         oo  oooo##oo            ", 
  "         oo  o##o                ", 
  "         oo##                    ", 
  "        ##   oooo                ", 
  "     ##      oooo                ", 
  "  ##        oooooo               ", 
  "             oooo                ", 
  "         -ooooooo                ", 
  "         -o    oo                ", 
  "         -o    oo                ", 
  "               ....              ", 
  "                                 ", 
  "                                 ", 
  )

RunningMan3SpriteMap.CopyMapToColorSprite(TheSprite=RunningMan3Sprite)


RunningMan3SpriteMap.map= (
  #0.........1.........2.....
  "                                 ", 
  "               oooo          **  ", 
  "               oo         ##     ", 
  "           oooooooo    ##        ", 
  "         oooooooo   #oo          ", 
  "         oo  oooo##oo            ", 
  "         oo  o##o                ", 
  "         oo##                    ", 
  "        ##   oooo                ", 
  "     ##      oooo                ", 
  "  ##        oooooo               ", 
  "             oooo                ", 
  "         -ooooooo                ", 
  "         -o  oo                  ", 
  "         -o  oo                  ", 
  "             ....                ", 
  "                                 ", 
  "                                 ", 
  )

RunningMan3SpriteMap.CopyMapToColorSprite(TheSprite=RunningMan3Sprite)



RunningMan3SpriteMap.map= (
  #0.........1.........2.....
  "                                 ", 
  "               oooo          **  ", 
  "               oo         ##     ", 
  "           oooooooo    ##        ", 
  "         oooooooo   #oo          ", 
  "         oo  oooo##oo            ", 
  "         oo  o##o                ", 
  "         oo##                    ", 
  "        ##   oooo                ", 
  "     ##      oooo                ", 
  "  ##        ooooooooo            ", 
  "           oo      oo            ", 
  "           oo  -ooooo            ", 
  "           oo  -o                ", 
  "           .o                    ", 
  "             ..                  ", 
  "                                 ", 
  "                                 ", 
  )

RunningMan3SpriteMap.CopyMapToColorSprite(TheSprite=RunningMan3Sprite)




RunningMan3SpriteMap.map= (
  #0.........1.........2.....
  "                                 ", 
  "               oooo          **  ", 
  "               oo         ##     ", 
  "           oooooooo    ##        ", 
  "         oooooooo   #oo          ", 
  "         oo  oooo##oo            ", 
  "         oo  o##o                ", 
  "         oo##                    ", 
  "        ##   oooo                ", 
  "     ##      oooo                ", 
  "  ##        ooooooooooo          ", 
  "           oo        oo          ", 
  "           oo    -ooooo          ", 
  "         .o      -o              ", 
  "         .o                      ", 
  "         .o                      ", 
  "                                 ", 
  "                                 ", 
  )

RunningMan3SpriteMap.CopyMapToColorSprite(TheSprite=RunningMan3Sprite)








BigSpiderLegOutSprite = ColorAnimatedSprite(
  h=0, 
  v=0, 
  name="Spider", 
  width  = 40, 
  height = 11, 
  frames = 0, 
  framerate=2,
  grid=[]  )

                

BigSpiderLegOutSpriteMap = TextMap(
  h      = 1,
  v      = 1,
  width  = 40, 
  height = 11
  )

BigSpiderLegOutSpriteMap.ColorList = {
  ' ' : 0,
  '.' : 1,
  '-' : 2,
  'o' : 3,  
  'O' : 4,  
  '*' : 8,
  '#' : 14,
  'b' : 15,
  'B' : 16

}

BigSpiderLegOutSpriteMap.TypeList = {
  ' ' : 'Empty',
  'O' : 'wall'
}


BigSpiderLegOutSpriteMap.map= (
  #0.........1.........2.........3
  "                                        ",
  "      ..    ......    ..                ", 
  "     .--.  .------.  .--.               ", 
  "    .-  -..-o*oo*o-..-  -.              ", 
  "   .-    -.-oOOOOo-.-    -.             ", 
  "   .-     .-oooooo-.     -.             ", 
  "   .-      .------.      -.             ", 
  "   .-       ......       -.             ", 
  "   .-                    -.             ", 
  "   .-                    -.             ", 
  "                                        ", 
  )

BigSpiderLegOutSpriteMap.CopyMapToColorSprite(TheSprite=BigSpiderLegOutSprite)


BigSpiderLegOutSpriteMap.map= (
  #0.........1.........2.........3
  "                     ..                 ", 
  "      ..    ......  .--.                ", 
  "     .--.  .------. .--.                ", 
  "    .-  -..-o*oo*o-..- -.               ", 
  "   .-    -.-oOOOOo-.-  -.               ", 
  "   .-     .-oooooo-.   -.               ", 
  "   .-      .------.    -.               ", 
  "   .-       ......     -.               ", 
  "   .-                  -.               ", 
  "   .-                                   ", 
  "                                        ",
  )

BigSpiderLegOutSpriteMap.CopyMapToColorSprite(TheSprite=BigSpiderLegOutSprite)


BigSpiderLegOutSpriteMap.map= (
  #0.........1.........2.........3
  "                     ...                ", 
  "      ..    ......  .---.               ", 
  "     .--.  .------. .-  -.              ", 
  "    .-  -..-o*oo*o-..-  -.              ", 
  "   .-    -.-oOOOOo-.-   -.              ", 
  "   .-     .-oooooo-.    -.              ", 
  "   .-      .------.     -.              ", 
  "   .-       ......      -.              ", 
  "   .-                                   ", 
  "   .-                                   ", 
  "                                        ", 
   )


BigSpiderLegOutSpriteMap.CopyMapToColorSprite(TheSprite=BigSpiderLegOutSprite)


BigSpiderLegOutSpriteMap.map= (
  #0.........1.........2.........3
  "                     .....              ", 
  "      ..    ......  .-----.             ", 
  "     .--.  .------. .-    -.            ", 
  "    .-  -..-o*oo*o-..-    -.            ", 
  "   .-    -.-oOOOOo-.-     -.            ", 
  "   .-     .-oooooo-.      -.            ", 
  "   .-      .------.                     ", 
  "   .-       ......                      ", 
  "   .-                                   ", 
  "   .-                                   ", 
  "                                        ", 
   )


BigSpiderLegOutSpriteMap.CopyMapToColorSprite(TheSprite=BigSpiderLegOutSprite)



BigSpiderLegOutSpriteMap.map= (
  #0.........1.........2.........3.........4
  "                                         ",
  "                          .....          ",
  "        ..    ......     .-----.         ",
  "       .--.  .------.   .-     -.        ",
  "      .-  -..-o*oo*o-. .-      -.        ",
  "     .-    -.-oOOOOo-.-        -.        ",
  "    .-      .-oooooo-.         -.        ",
  "   .-        .------.                    ",
  "   .-         ......                     ",
  "   .-                                    ",
  "                                         ",
  "                                         ",
   )
BigSpiderLegOutSpriteMap.CopyMapToColorSprite(TheSprite=BigSpiderLegOutSprite)




BigSpiderLegOutSpriteMap.map= (
  #0.........1.........2.........3.........4
  "                                         ",
  "                                         ",
  "                                         ",
  "                  ......     ........    ",
  "         .....   .------.   .-------.    ",
  "        .-----...-o*oo*o-. .-        -.  ",
  "       .-     --.-oOOOOo-.-           -. ",
  "      .-        .-oooooo-.            -. ",
  "    .-           .------.                ",
  "   .-             ......                 ",
  "                                         ",
   )
BigSpiderLegOutSpriteMap.CopyMapToColorSprite(TheSprite=BigSpiderLegOutSprite)


BigSpiderLegOutSpriteMap.map= (
  #0.........1.........2.........3.........4
  "                                           ",
  "                                           ",
  "                                           ",
  "                   ......                  ",
  "                  .------.                 ",
  "         .........-o*oo*o-..........       ",
  "        .--------.-oOOOOo-.----------.     ",
  "      .-         .-oooooo-.          -.    ",
  "    .-            .------.            -.   ",
  "   .-              ......              -.  ",
  "                                            ",
   )
BigSpiderLegOutSpriteMap.CopyMapToColorSprite(TheSprite=BigSpiderLegOutSprite)


BigSpiderLegOutSpriteMap.map= (
  #0.........1.........2.........3.........4
  "                                         ",
  "                                         ",
  "                                         ",
  "                  ......     ........    ",
  "         .....   .------.   .-------.    ",
  "        .-----...-o*oo*o-. .-        -.  ",
  "       .-     --.-oOOOOo-.-           -. ",
  "      .-        .-oooooo-.            -. ",
  "    .-           .------.                ",
  "   .-             ......                 ",
  "                                         ",
   )
BigSpiderLegOutSpriteMap.CopyMapToColorSprite(TheSprite=BigSpiderLegOutSprite)


BigSpiderLegOutSpriteMap.map= (
  #0.........1.........2.........3.........4
  "                                         ",
  "                          .....          ",
  "        ..    ......     .-----.         ",
  "       .--.  .------.   .-     -.        ",
  "      .-  -..-o*oo*o-. .-      -.        ",
  "     .-    -.-oOOOOo-.-        -.        ",
  "    .-      .-oooooo-.         -.        ",
  "   .-        .------.                    ",
  "   .-         ......                     ",
  "   .-                                    ",
  "                                         ",
  "                                         ",
   )
BigSpiderLegOutSpriteMap.CopyMapToColorSprite(TheSprite=BigSpiderLegOutSprite)


BigSpiderLegOutSpriteMap.map= (
  #0.........1.........2.........3
  "                     .....              ", 
  "      ..    ......  .-----.             ", 
  "     .--.  .------. .-    -.            ", 
  "    .-  -..-o*oo*o-..-    -.            ", 
  "   .-    -.-oOOOOo-.-     -.            ", 
  "   .-     .-oooooo-.      -.            ", 
  "   .-      .------.                     ", 
  "   .-       ......                      ", 
  "   .-                                   ", 
  "   .-                                   ", 
  "                                        ", 
   )


BigSpiderLegOutSpriteMap.CopyMapToColorSprite(TheSprite=BigSpiderLegOutSprite)




BigSpiderLegOutSpriteMap.map= (
  #0.........1.........2.........3.........4
  "                     ...                ", 
  "      ..    ......  .---.               ", 
  "     .--.  .------. .-  -.              ", 
  "    .-  -..-o*oo*o-..-  -.              ", 
  "   .-    -.-oOOOOo-.-   -.              ", 
  "   .-     .-oooooo-.    -.              ", 
  "   .-      .------.     -.              ", 
  "   .-       ......      -.              ", 
  "   .-                                   ", 
  "   .-                                   ", 
  "                                        ", 
   )


BigSpiderLegOutSpriteMap.CopyMapToColorSprite(TheSprite=BigSpiderLegOutSprite)







#----------------------------
# Big Spider Walking       --
#----------------------------


BigSpiderWalkingSprite = ColorAnimatedSprite(
  h=0, 
  v=0, 
  name="Spider", 
  width  = 44, 
  height = 11, 
  frames = 0, 
  framerate=1,
  grid=[]  )

                

BigSpiderWalkingSpriteMap = TextMap(
  h      = 1,
  v      = 1,
  width  = 44, 
  height = 11
  )

BigSpiderWalkingSpriteMap.ColorList = {
  ' ' : 0,
  '.' : 1,
  '-' : 2,
  'o' : 3,  
  'O' : 4,  
  '*' : 8,
  '#' : 14,
  'b' : 15,
  'B' : 16

}

BigSpiderWalkingSpriteMap.TypeList = {
  ' ' : 'Empty',
  'O' : 'wall'
}


BigSpiderWalkingSpriteMap.map= (
  #0.........1.........2.........3.........4....
  "                                            ",
  "      ..    ......    ..                    ", 
  "     .--.  .------.  .--.                   ", 
  "    .-  -..-o*oo*o-..-  -.                  ", 
  "   .-    -.-oOOOOo-.-    -.                 ", 
  "   .-     .-oooooo-.     -.                 ", 
  "   .-      .------.      -.                 ", 
  "   .-       ......       -.                 ", 
  "   .-                    -.                 ", 
  "   .-                    -.                 ", 
  "                                            ", 
  )

BigSpiderWalkingSpriteMap.CopyMapToColorSprite(TheSprite=BigSpiderWalkingSprite)


BigSpiderWalkingSpriteMap.map= (
  #0.........1.........2.........3
  "                     ..                     ", 
  "      ..    ......  .---.                    ", 
  "     .--.  .------. .-  -.                   ", 
  "    .-  -..-o*oo*o-..-   -.                   ", 
  "   .-    -.-oOOOOo-.-    -.                   ", 
  "   .-     .-oooooo-.     -.                   ", 
  "   .-      .------.      -.                   ", 
  "   .-       ......      -.                    ", 
  "   .-                                         ", 
  "   .-                                        ", 
  "                                             ",
  )

BigSpiderWalkingSpriteMap.CopyMapToColorSprite(TheSprite=BigSpiderWalkingSprite)


BigSpiderWalkingSpriteMap.map= (
  #0.........1.........2.........3
  "                      ...                    ", 
  "      ..    ......   .----.                   ", 
  "     .--.  .------. .-    -.                  ", 
  "    .-  -..-o*oo*o-..-    -.                  ", 
  "   .-    -.-oOOOOo-.-     -.                  ", 
  "   .-     .-oooooo-.      -.                  ", 
  "   .-      .------.      -.                   ", 
  "   .-       ......                           ", 
  "   .-                                        ", 
  "   .-                                        ", 
  "                                             ", 
   )


BigSpiderWalkingSpriteMap.CopyMapToColorSprite(TheSprite=BigSpiderWalkingSprite)


BigSpiderWalkingSpriteMap.map= (
  #0.........1.........2.........3
  "                      .....                 ", 
  "      ..    ......   .-----.                ", 
  "     .--.  .------. .-      -.              ", 
  "    .-  -..-o*oo*o-..-      -.              ", 
  "   .-    -.-oOOOOo-.-       -.              ", 
  "   .-     .-oooooo-.       -.               ", 
  "   .-      .------.                         ", 
  "   .-       ......                          ", 
  "   .-                                       ", 
  "   .-                                       ", 
  "                                            ", 
   )


BigSpiderWalkingSpriteMap.CopyMapToColorSprite(TheSprite=BigSpiderWalkingSprite)



BigSpiderWalkingSpriteMap.map= (
  #0.........1.........2.........3.........4
  "                                             ",
  "                          .....              ",
  "        ..    ......     .-----.             ",
  "       .--.  .------.   .-     -.            ",
  "      .-  -..-o*oo*o-. .-      -.            ",
  "     .-    -.-oOOOOo-.-        -.            ",
  "    .-      .-oooooo-.        -.             ",
  "   .-        .------.                        ",
  "   .-         ......                         ",
  "   .-                                        ",
  "                                             ",
  "                                             ",
   )
BigSpiderWalkingSpriteMap.CopyMapToColorSprite(TheSprite=BigSpiderWalkingSprite)




BigSpiderWalkingSpriteMap.map= (
  #0.........1.........2.........3.........4....
  "                                             ",
  "                                             ",
  "                                             ",
  "                  ......     ........        ",
  "         .....   .------.   .-------.        ",
  "        .-----...-o*oo*o-. .-        -.      ",
  "       .-     --.-oOOOOo-.-           -.     ",
  "      .-        .-oooooo-.            -.     ",
  "    .-           .------.                    ",
  "   .-             ......                     ",
  "                                             ",
   )
BigSpiderWalkingSpriteMap.CopyMapToColorSprite(TheSprite=BigSpiderWalkingSprite)


BigSpiderWalkingSpriteMap.map= (
  #0.........1.........2.........3.........4
  "                                            ",
  "                                            ",
  "                                            ",
  "                   ......                   ",
  "                  .------.                  ",
  "         .........-o*oo*o-..........        ",
  "        .--------.-oOOOOo-.----------.      ",
  "      .-         .-oooooo-.          -.     ",
  "    .-            .------.            -.    ",
  "   .-              ......              -.   ",
  "                                            ",
   )
BigSpiderWalkingSpriteMap.CopyMapToColorSprite(TheSprite=BigSpiderWalkingSprite)





BigSpiderWalkingSpriteMap.map= (
  #0.........1.........2.........3.........4
  "                                            ",
  "                                            ",  
  "                                            ",  
  "       ........     ......                  ",  
  "       .-------.   .------.   .....         ",  
  "     .-        -. .-o*oo*o-...-----.        ",  
  "    .-           -.-oOOOOo-.--     -.       ",  
  "    .-            .-oooooo-.        -.      ",  
  "                   .------.           -.    ",  
  "                    ......             -.   ",  
  "                                            ",  
)
BigSpiderWalkingSpriteMap.CopyMapToColorSprite(TheSprite=BigSpiderWalkingSprite)


BigSpiderWalkingSpriteMap.map= (
  #0.........1.........2.........3.........4...
  "                                            ",
  "             .....                          ",  
  "            .-----.     ......    ..        ",  
  "           .-     -.   .------.  .--.       ",  
  "           .-      -. .-o*oo*o-..-  -.      ",  
  "           .-        -.-oOOOOo-.-    -.     ",  
  "           .-         .-oooooo-.      -.    ",  
  "                       .------.        -.   ",  
  "                        ......         -.   ",  
  "                                       -.   ",  
  "                                            ",  
  "                                            ",  
  )
BigSpiderWalkingSpriteMap.CopyMapToColorSprite(TheSprite=BigSpiderWalkingSprite)


BigSpiderWalkingSpriteMap.map= (
  #0.........1.........2.........3
  "                  .....                     ",
  "                 .-----.  ......    ..      ",  
  "                .-    -. .------.  .--.     ",  
  "                .-    -..-o*oo*o-..-  -.    ",  
  "                .-     -.-oOOOOo-.-    -.   ",  
  "                .-      .-oooooo-.     -.   ",  
  "                         .------.      -.   ",  
  "                          ......       -.   ",  
  "                                       -.   ",  
  "                                       -.   ",  
  "                                            ",  
   )


BigSpiderWalkingSpriteMap.CopyMapToColorSprite(TheSprite=BigSpiderWalkingSprite)


BigSpiderWalkingSpriteMap.map= (
  #0.........1.........2.........3
  "                    ...                     ",
  "                  .----.  ......    ..      ",  
  "                 .-   -. .------.  .--.     ",  
  "                 .-   -..-o*oo*o-..-  -.    ",  
  "                 .-    -.-oOOOOo-.-    -.   ",  
  "                 .-     .-oooooo-.     -.   ",  
  "                 .-      .------.      -.   ",  
  "                          ......       -.   ",  
  "                                       -.   ",  
  "                                       -.   ",  
  "                                            ",  
 )

BigSpiderWalkingSpriteMap.CopyMapToColorSprite(TheSprite=BigSpiderWalkingSprite)

BigSpiderWalkingSpriteMap.map= (
  #0.........1.........2.........3
  "                                            ",
  "                   .-.    ......    ..      ",  
  "                 .----.  .------.  .--.     ",  
  "                 .-   -..-o*oo*o-..-  -.    ",  
  "                 .-    -.-oOOOOo-.-    -.   ",  
  "                 .-     .-oooooo-.     -.   ",  
  "                 .-      .------.      -.   ",  
  "                 .-       ......       -.   ",  
  "                                       -.   ",  
  "                                       -.   ",  
  "                                            ",  
 )

BigSpiderWalkingSpriteMap.map= (
  #0.........1.........2.........3.........4....
  "                                             ",
  "                    ..    ......    ..       ", 
  "                   .--.  .------.  .--.      ", 
  "                  .-  -..-o*oo*o-..-  -.     ", 
  "                 .-    -.-oOOOOo-.-    -.    ", 
  "                 .-     .-oooooo-.     -.    ", 
  "                 .-      .------.      -.    ", 
  "                 .-       ......       -.    ", 
  "                 .-                    -.    ", 
  "                 .-                    -.    ", 
  "                                             ", 
  )

BigSpiderWalkingSpriteMap.CopyMapToColorSprite(TheSprite=BigSpiderWalkingSprite)




ElectricZap = ColorAnimatedSprite(
  h=0, 
  v=0, 
  name="ElectricZap", 
  width  = 5, 
  height = 5, 
  framerate=1,
  grid=[]  )

                 

ElectricZapMap = TextMap(
  h      = 1,
  v      = 1,
  width  = ElectricZap.width, 
  height = ElectricZap.height
  )


ElectricZapMap.ColorList = {
  ' ' : 0,
  '-' : 39, #max-white
  '.' : 9, 
  'o' : 4, 
  'O' : 45, 
  'r' : 5,
  'R' : 8,
  'b' : 12,
  '*' : 45, #bright white
  '#' : 1  # dark grey
}


ElectricZapMap.map= (
  #0.........1.........2.........3.........4....
  "     ",
  "     ",
  "  -  ",
  "     ",
  "     ",
  
  )


ElectricZapMap.CopyMapToColorSprite(TheSprite=ElectricZap)


ElectricZapMap.map= (
  #0.........1.........2.........3.........4....
  "     ",
  " --- ",
  " -.- ",
  " --- ",
  "     ",
  
  )


ElectricZapMap.CopyMapToColorSprite(TheSprite=ElectricZap)

ElectricZapMap.map= (
  #0.........1.........2.........3.........4....
  "  -  ",
  " -.- ",
  "-.o.-",
  " -.- ",
  "  -  ",
  
  )


ElectricZapMap.CopyMapToColorSprite(TheSprite=ElectricZap)



ElectricZapMap.map= (
  #0.........1.........2.........3.........4....
  "  .  ",
  " .o. ",
  ".oOo.",
  " .o. ",
  "  .  ",
  
  )


ElectricZapMap.CopyMapToColorSprite(TheSprite=ElectricZap)

ElectricZapMap.map= (
  #0.........1.........2.........3.........4....
  "  o  ",
  "  O  ",
  "oO Oo",
  "  O  ",
  "  o  ",
  
  )


ElectricZapMap.CopyMapToColorSprite(TheSprite=ElectricZap)


ElectricZapMap.map= (
  #0.........1.........2.........3.........4....
  "  O  ",
  "     ",
  "O   O",
  "     ",
  "  O  ",
  
  )


ElectricZapMap.CopyMapToColorSprite(TheSprite=ElectricZap)


             






Rezonator = ColorAnimatedSprite(
  h=0, 
  v=0, 
  name="Rezonator", 
  width  = 20, 
  height = 18, 
  frames = 0, 
  framerate=1,
  grid=[]  )


RezonatorMap = TextMap(
  h      = 1,
  v      = 1,
  width  = Rezonator.width, 
  height = Rezonator.height
  )


RezonatorMap.ColorList = {
  ' ' : 0,
  '-' : 39, #max-white
  '.' : 6,  #dark red 
  'x' : 5,  #med red
  '*' : 45, #bright white
  '#' : 8,  # bright red
  'o' : 15,
  'O' : 41,
  
  }


RezonatorMap.TypeList = {
  ' ' : 'Empty'
}





RezonatorMap.map= (
    #0.........1.........2.........3
    "                    ", #0
    "         xx         ",
    "        xoox        ",
    " xxxxxxxxxxxxxxxxxx ",
    "  x..............x  ",
    "  x..............x  ",
    " xxxxxxxxxxxxxxxxxx ",
    "  x..x        x..x  ", 
    "  x..x        x..x  ",
    "  x..x        x..x  ",
    "  xxxx        xxxx  ", #10
    "  x..x        x..x  ",
    "  x..x        x..x  ",
    "  x..x        x..x  ",
    "  x..x        x..x  ",
    "  x...x      x...x  ",
    "  xxxxxxx   xxxxxx  ",       
    "                    "  #17 (18 total)
    )
  
RezonatorMap.CopyMapToColorSprite(TheSprite=Rezonator)


RezonatorMap.map= (
    #0.........1.........2.........3
    "                    ", #0
    "         xx         ",
    "        xOOx        ",
    " xxxxxxxxxxxxxxxxxx ",
    "  x..............x  ",
    "  x..............x  ",
    " xxxxxxxxxxxxxxxxxx ",
    "  x..x        x..x  ", 
    "  x..x        x..x  ",
    "  x..x        x..x  ",
    "  xxxx        xxxx  ", #10
    "  x..x        x..x  ",
    "  x..x        x..x  ",
    "  x..x        x..x  ",
    "  x..x        x..x  ",
    "  x...x      x...x  ",
    "  xxxxxxx   xxxxxx  ",       
    "                    "  #17 (18 total)
    )
  
RezonatorMap.CopyMapToColorSprite(TheSprite=Rezonator)







BigRezonator = ColorAnimatedSprite(
  h=0, 
  v=0, 
  name="BigRezonator", 
  width  = 26, 
  height = 25, 
  frames = 0, 
  framerate=1,
  grid=[]  )


BigRezonatorMap = TextMap(
  h      = 1,
  v      = 1,
  width  = BigRezonator.width, 
  height = BigRezonator.height
  )


BigRezonatorMap.ColorList = {
  ' ' : 0,
  '-' : 39, #max-white
  '.' : 6,  #med red 
  'x' : 5,  #dark red
  '*' : 45, #bright white
  '#' : 8,  # bright red
  'o' : 15,
  'y' : 22, #low yellow 
  'Y' : 42, #max yellow 
  }


BigRezonatorMap.TypeList = {
  ' ' : 'Empty'
}





BigRezonatorMap.map= (
    #0.........1.........2.........3
    "                          ", #0
    "            xx            ",
    "          x.yy.x          ",
    "         x......x         ",
    " xxxxxxxxxxxxxxxxxxxxxxxx ",
    "  x....................x  ",
    "  x....................x  ",
    "  x....................x  ",
    "  x....................x  ",
    " xxxxxxxxxxxxxxxxxxxxxxxx ",
    "  x....x   xxxx   x....x  ", #10
    "  x....x          x....x  ", 
    "  x....x          x....x  ", 
    "  x....x          x....x  ", 
    "  x....x          x....x  ", 
    "  xxxxxx          xxxxxx  ", 
    "  x....x          x....x  ",
    "  x....x          x....x  ",
    "  x....x          x....x  ",
    "  x....x          x....x  ",
    "  x....x          x....x  ", #20
    "  x....x          x....x  ",
    "  x.....x        x.....x  ",
    "  xxxxxxxxx     xxxxxxxx  ",       
    "                          " #24  (25 total)
    )
BigRezonatorMap.CopyMapToColorSprite(TheSprite=BigRezonator)



BigRezonatorMap.map= (
    #0.........1.........2.........3
    "                          ", #0
    "            xx            ",
    "          x.YY.x          ",
    "         x......x         ",
    " xxxxxxxxxxxxxxxxxxxxxxxx ",
    "  x....................x  ",
    "  x....................x  ",
    "  x....................x  ",
    "  x....................x  ",
    " xxxxxxxxxxxxxxxxxxxxxxxx ",
    "  x....x   xxxx   x....x  ", #10
    "  x....x          x....x  ", 
    "  x....x          x....x  ", 
    "  x....x          x....x  ", 
    "  x....x          x....x  ", 
    "  xxxxxx          xxxxxx  ", 
    "  x....x          x....x  ",
    "  x....x          x....x  ",
    "  x....x          x....x  ",
    "  x....x          x....x  ",
    "  x....x          x....x  ", #20
    "  x....x          x....x  ",
    "  x.....x        x.....x  ",
    "  xxxxxxxxx     xxxxxxxx  ",       
    "                          " #24  (25 total)
    )
BigRezonatorMap.CopyMapToColorSprite(TheSprite=BigRezonator)














BigRezonator2 = ColorAnimatedSprite(
  h=0, 
  v=0, 
  name="BigRezonator", 
  width  = 26, 
  height = 29, 
  frames = 0, 
  framerate=1,
  grid=[]  )


BigRezonator2Map = TextMap(
  h      = 1,
  v      = 1,
  width  = BigRezonator2.width, 
  height = BigRezonator2.height
  )


BigRezonator2Map.ColorList = {
  ' ' : 0,
  '-' : 39, #max-white
  '.' : 6,  #med red 
  'x' : 5,  #dark red
  '*' : 45, #bright white
  '#' : 8,  # bright red
  'o' : 15,
  'y' : 22, #low yellow 
  'Y' : 42, #max yellow 
  }


BigRezonator2Map.TypeList = {
  ' ' : 'Empty'
}





BigRezonator2Map.map= (
    #0.........1.........2.........3
    "                          ", #0
    "            xx            ",
    "          x.yy.x          ",
    "         x......x         ",
    " xxxxxxxxxxxxxxxxxxxxxxxx ",
    "  x....................x  ",
    "  x....................x  ",
    "  x....................x  ",
    "  x....................x  ",
    " xxxxxxxxxxxxxxxxxxxxxxxx ",
    "  x....x   xxxx   x....x  ", #10
    "  x....x          x....x  ", 
    "  x....x          x....x  ", 
    "  x....x          x....x  ", 
    "  x....x          x....x  ", 
    "  xxxxxx          xxxxxx  ", 
    "  x....x          x....x  ",
    "  x....x          x....x  ",
    "  x....x          x....x  ",
    "  x....x          x....x  ",
    "  x....x          x....x  ", #20
    "  x....x          x....x  ",
    "  x.....x        x.....x  ",
    "  xxxxxxxxx     xxxxxxxx  ",       
    "                          ", #24  (25 total)
    "                          ", 
    "                          ", 
    "                          ", 
    "                          "
    )
BigRezonator2Map.CopyMapToColorSprite(TheSprite=BigRezonator2)



BigRezonator2Map.map= (
    #0.........1.........2.........3
    "                          ", #0
    "            xx            ",
    "          x.yy.x          ",
    "         x......x         ",
    " xxxxxxxxxxxxxxxxxxxxxxxx ",
    "  x....................x  ",
    "  x....................x  ",
    "  x....................x  ",
    "  x....................x  ",
    " xxxxxxxxxxxxxxxxxxxxxxxx ",
    "   x....x  xxxx  x....x   ", #10
    "   x....x        x....x   ", 
    "   x....x        x....x   ", 
    "   x....x        x....x   ", 
    "   x....x        x....x   ", 
    "   xxxxxx        xxxxxx   ", 
    "   x....x        x....x   ",
    "   x....x        x....x   ",
    "   x....x        x....x   ",
    "   x....x        x....x   ",
    "   x....x        x....x   ", #20
    "   x....x        x....x   ",
    "   x.....x      x.....x   ",
    "   xxxxxxxxx   xxxxxxxx   ",       
    "                          ", #24  (25 total)
    "                          ", 
    "                          ", 
    "                          ", 
    "                          "
    )
BigRezonator2Map.CopyMapToColorSprite(TheSprite=BigRezonator2)










BigRezonator2Map.map= (
    #0.........1.........2.........3
    "                          ", 
    "                          ", #0
    "            xx            ",
    "          x.yy.x          ",
    "         x......x         ",
    " xxxxxxxxxxxxxxxxxxxxxxxx ",
    "  x....................x  ",
    "  x....................x  ",
    "  x....................x  ",
    "  x....................x  ",
    " xxxxxxxxxxxxxxxxxxxxxxxx ",
    "    x....x xxxx x....x    ", #10
    "    x....x      x....x    ", 
    "    x....x      x....x    ", 
    "    x....x      x....x    ", 
    "    x....x      x....x    ", 
    "    xxxxxx      xxxxxx    ", 
    "    x....x      x....x    ",
    "    x....x      x....x    ",
    "    x....x      x....x    ",
    "    x....x      x....x    ",
    "    x....x      x....x    ", #20
    "    x....x      x....x    ",
    "    x.....x    x.....x    ",
    "    xxxxxxxxx xxxxxxxx    ",       
    "                          ", #24  (25 total)
    "                          ", 
    "                          ", 
    "                          "
    )
BigRezonator2Map.CopyMapToColorSprite(TheSprite=BigRezonator2)





BigRezonator2Map.map= (
    #0.........1.........2.........3
    "                          ", #0
    "                          ", 
    "            xx            ",
    "          x.YY.x          ",
    "         x......x         ",
    " xxxxxxxxxxxxxxxxxxxxxxxx ",
    "  x....................x  ",
    "  x....................x  ",
    "  x....................x  ",
    "  x....................x  ",
    " xxxxxxxxxxxxxxxxxxxxxxxx ",
    "     x....xxxxxx....x     ", #10
    "     x....x    x....x     ", 
    "     x....x    x....x     ", 
    "     x....x    x....x     ", 
    "     x....x    x....x     ", 
    "     xxxxxx    xxxxxx     ", 
    "     x....x    x....x     ",
    "     x....x    x....x     ",
    "     x....x    x....x     ",
    "     x....x    x....x     ",
    "     x....x    x....x     ", #20
    "     x....x    x....x     ",
    "     x.....x  x.....x     ",
    "     xxxxxxxxxxxxxxxx     ",       
    "                          ", #24  (25 total)
    "                          ", 
    "                          ", 
    "                          "


    )
BigRezonator2Map.CopyMapToColorSprite(TheSprite=BigRezonator2)


BigRezonator2Map.map= (
    #0.........1.........2.........3
    "                          ", #0
    "                          ", 
    "                          ", 
    "            xx            ",
    "          x.YY.x          ",
    "         x......x         ",
    " xxxxxxxxxxxxxxxxxxxxxxxx ",
    "  x....................x  ",
    "  x....................x  ",
    "  x....................x  ",
    "  x....................x  ",
    " xxxxxxxxxxxxxxxxxxxxxxxx ",
    "      x....xxxx....x      ", #10
    "      x....x  x....x      ", 
    "      x....x  x....x      ", 
    "      x....x  x....x      ", 
    "      x....x  x....x      ", 
    "      xxxxxx  xxxxxx      ", 
    "      x....x  x....x      ",
    "      x....x  x....x      ",
    "      x....x  x....x      ",
    "      x....x  x....x      ",
    "      x....x  x....x      ", #20
    "      x....x  x....x      ",
    "      x.....xx.....x      ",
    "      xxxxxxxxxxxxxx      ",       
    "                          ", #24  (25 total)
    "                          ", 
    "                          "
    )
  
BigRezonator2Map.CopyMapToColorSprite(TheSprite=BigRezonator2)


BigRezonator2Map.map= (
    #0.........1.........2.........3
    "                          ", #0
    "                          ", 
    "                          ", 
    "            xx            ",
    "          x.YY.x          ",
    "         x......x         ",
    " xxxxxxxxxxxxxxxxxxxxxxxx ",
    "  x....................x  ",
    "  x....................x  ",
    "  x....................x  ",
    "  x....................x  ",
    " xxxxxxxxxxxxxxxxxxxxxxxx ",
    "       x....xx....x       ", #10
    "       x....xx....x       ", 
    "       x....xx....x       ", 
    "       x....xx....x       ", 
    "       x....xx....x       ", 
    "       xxxxxxxxxxxx       ", 
    "       x....xx....x       ",
    "       x....xx....x       ",
    "       x....xx....x       ",
    "       x....xx....x       ",
    "       x....xx....x       ", #20
    "       x....xx....x       ",
    "       x....xx....x       ",
    "       xxxxxxxxxxxx       ",       
    "                          ", #24  (25 total)
    "                          ",
    "                          "
    )
  
BigRezonator2Map.CopyMapToColorSprite(TheSprite=BigRezonator2)


BigRezonator2Map.map= (
    #0.........1.........2.........3
    "                          ", #0
    "                          ",
    "                          ",
    "                          ",
    "            xx            ",
    "          x.YY.x          ",
    "         x......x         ",
    " xxxxxxxxxxxxxxxxxxxxxxxx ",
    "  x....................x  ",
    "  x....................x  ",
    "  x....................x  ",
    "  x....................x  ",
    " xxxxxxxxxxxxxxxxxxxxxxxx ",
    "       x....xx....x       ", #10
    "       x....xx....x       ", 
    "       x....xx....x       ", 
    "       x....xx....x       ", 
    "       x....xx....x       ", 
    "       xxxxxxxxxxxx       ", 
    "       x....xx....x       ",
    "       x....xx....x       ",
    "       x....xx....x       ",
    "       x....xx....x       ",
    "       x....xx....x       ", #20
    "       x....xx....x       ",
    "       x....xx....x       ",
    "      xxxxxxxxxxxxxx      ",       
    "                          ",
    "                          "
    )
  
BigRezonator2Map.CopyMapToColorSprite(TheSprite=BigRezonator2)








BigRezonator2Map.map= (
    #0.........1.........2.........3
    "                          ", #0
    "                          ",
    "                          ",
    "                          ",
    "                          ",
    "                          ",
    "            xx            ",
    "          x.YY.x          ",
    "         x......x         ",
    " xxxxxxxxxxxxxxxxxxxxxxxx ",
    "  x....................x  ",
    "  x....................x  ",
    "  x....................x  ",
    "  x....................x  ",
    " xxxxxxxxxxxxxxxxxxxxxxxx ",
    "       x....xx....x       ", #10
    "       x....xx....x       ", 
    "       x....xx....x       ", 
    "       x....xx....x       ", 
    "       xxxxxxxxxxxx       ", 
    "       x....xx....x       ",
    "       x....xx....x       ",
    "       x....xx....x       ",
    "       x....xx....x       ",
    "       x....xx....x       ", #20
    "       x....xx....x       ",
    "       x....xx....x       ",
    "      xxxxxxxxxxxxxx      ",       
    "                          "
    )
  
BigRezonator2Map.CopyMapToColorSprite(TheSprite=BigRezonator2)












BigRezonator2Map.map= (
    #0.........1.........2.........3
    "                          ", #0
    "                          ",
    "                          ",
    "                          ", 
    "                          ",
    "                          ",
    "            xx            ",
    "          x.YY.x          ",
    "         x......x         ",
    " xxxxxxxxxxxxxxxxxxxxxxxx ",
    "  x....................x  ",
    "  x....................x  ",
    "  x....................x  ",
    "  x....................x  ",
    " xxxxxxxxxxxxxxxxxxxxxxxx ",
    "       x....xx....x       ", #10
    "       x....xx....x       ", 
    "       x....xx....x       ", 
    "       x....xx....x       ", 
    "       xxxxxxxxxxxx       ", 
    "       x....xx....x       ",
    "       x....xx....x       ",
    "       x....xx....x       ",
    "       x....xx....x       ",
    "       x....xx....x       ", #20
    "       x....xx....x       ",
    "      x.....xx.....x      ",
    "     xxxxxxxxxxxxxxxx     ",       
    "                          " 
    )
  
BigRezonator2Map.CopyMapToColorSprite(TheSprite=BigRezonator2)



BigRezonator2Map.map= (
    #0.........1.........2.........3
    "                          ", #0
    "                          ",
    "                          ", 
    "                          ", 
    "                          ", 
    "                          ",
    "                          ",
    "            xx            ",
    "          x.YY.x          ",
    "         x......x         ",
    " xxxxxxxxxxxxxxxxxxxxxxxx ",
    "  x....................x  ",
    "  x....................x  ",
    "  x....................x  ",
    "  x....................x  ",
    " xxxxxxxxxxxxxxxxxxxxxxxx ",
    "       x....xx....x       ", #10
    "       x....xx....x       ", 
    "       x....xx....x       ", 
    "       xxxxxxxxxxxx       ", 
    "       x....xx....x       ",
    "       x....xx....x       ",
    "       x....xx....x       ",
    "       x....xx....x       ",
    "       x....xx....x       ", #20
    "       x....xx....x       ",
    "      x.....xx.....x      ",
    "     xxxxxxxxxxxxxxxx     ",       
    "                          " 
    )
  
BigRezonator2Map.CopyMapToColorSprite(TheSprite=BigRezonator2)






BigRezonator2Map.map= (
    #0.........1.........2.........3
    "                          ", #0
    "                          ",
    "                          ",
    "                          ",
    "            xx            ",
    "          x.YY.x          ",
    "         x......x         ",
    " xxxxxxxxxxxxxxxxxxxxxxxx ",
    "  x....................x  ",
    "  x....................x  ",
    "  x....................x  ",
    "  x....................x  ",
    " xxxxxxxxxxxxxxxxxxxxxxxx ",
    "       x....xx....x       ", #10
    "       x....xx....x       ", 
    "       x....xx....x       ", 
    "       x....xx....x       ", 
    "       x....xx....x       ", 
    "       xxxxxxxxxxxx       ", 
    "       x....xx....x       ",
    "       x....xx....x       ",
    "       x....xx....x       ",
    "       x....xx....x       ",
    "       x....xx....x       ", #20
    "       x....xx....x       ",
    "      x.....xx.....x      ",
    "     xxxxxxxxxxxxxxxx     ",       
    "                          ", 
    "                          " 
    )
  
BigRezonator2Map.CopyMapToColorSprite(TheSprite=BigRezonator2)



BigRezonator2Map.map= (
    #0.........1.........2.........3
    "                          ", #0
    "                          ", 
    "                          ", 
    "            xx            ",
    "          x.YY.x          ",
    "         x......x         ",
    " xxxxxxxxxxxxxxxxxxxxxxxx ",
    "  x....................x  ",
    "  x....................x  ",
    "  x....................x  ",
    "  x....................x  ",
    " xxxxxxxxxxxxxxxxxxxxxxxx ",
    "       x....xx....x       ", #10
    "       x....xx....x       ", 
    "       x....xx....x       ", 
    "       x....xx....x       ", 
    "       x....xx....x       ", 
    "       xxxxxxxxxxxx       ", 
    "       x....xx....x       ",
    "       x....xx....x       ",
    "       x....xx....x       ",
    "       x....xx....x       ",
    "       x....xx....x       ", #20
    "       x....xx....x       ",
    "       x....xx....x       ",
    "       xxxxxxxxxxxx       ",       
    "                          ", #24  (25 total)
    "                          ",
    "                          "
    )
  
BigRezonator2Map.CopyMapToColorSprite(TheSprite=BigRezonator2)


BigRezonator2Map.map= (
    #0.........1.........2.........3
    "                          ", #0
    "                          ", 
    "                          ", 
    "            xx            ",
    "          x.YY.x          ",
    "         x......x         ",
    " xxxxxxxxxxxxxxxxxxxxxxxx ",
    "  x....................x  ",
    "  x....................x  ",
    "  x....................x  ",
    "  x....................x  ",
    " xxxxxxxxxxxxxxxxxxxxxxxx ",
    "      x....xxxx....x      ", #10
    "      x....x  x....x      ", 
    "      x....x  x....x      ", 
    "      x....x  x....x      ", 
    "      x....x  x....x      ", 
    "      xxxxxx  xxxxxx      ", 
    "      x....x  x....x      ",
    "      x....x  x....x      ",
    "      x....x  x....x      ",
    "      x....x  x....x      ",
    "      x....x  x....x      ", #20
    "      x....x  x....x      ",
    "      x.....xx.....x      ",
    "      xxxxxxxxxxxxxx      ",       
    "                          ", #24  (25 total)
    "                          ", 
    "                          "
    )
  
BigRezonator2Map.CopyMapToColorSprite(TheSprite=BigRezonator2)




BigRezonator2Map.map= (
    #0.........1.........2.........3
    "                          ", #0
    "                          ", #0
    "            xx            ",
    "          x.YY.x          ",
    "         x......x         ",
    " xxxxxxxxxxxxxxxxxxxxxxxx ",
    "  x....................x  ",
    "  x....................x  ",
    "  x....................x  ",
    "  x....................x  ",
    " xxxxxxxxxxxxxxxxxxxxxxxx ",
    "     x....xxxxxx....x     ", #10
    "     x....x    x....x     ", 
    "     x....x    x....x     ", 
    "     x....x    x....x     ", 
    "     x....x    x....x     ", 
    "     xxxxxx    xxxxxx     ", 
    "     x....x    x....x     ",
    "     x....x    x....x     ",
    "     x....x    x....x     ",
    "     x....x    x....x     ",
    "     x....x    x....x     ", #20
    "     x....x    x....x     ",
    "     x.....x  x.....x     ",
    "     xxxxxxxxxxxxxxxx     ",       
    "                          ", #24  (25 total)
    "                          ", 
    "                          ", 
    "                          "


    )
BigRezonator2Map.CopyMapToColorSprite(TheSprite=BigRezonator2)








BigRezonator2Map.map= (
    #0.........1.........2.........3
    "                          ", 
    "                          ", #0
    "            xx            ",
    "          x.YY.x          ",
    "         x......x         ",
    " xxxxxxxxxxxxxxxxxxxxxxxx ",
    "  x....................x  ",
    "  x....................x  ",
    "  x....................x  ",
    "  x....................x  ",
    " xxxxxxxxxxxxxxxxxxxxxxxx ",
    "    x....x xxxx x....x    ", #10
    "    x....x      x....x    ", 
    "    x....x      x....x    ", 
    "    x....x      x....x    ", 
    "    x....x      x....x    ", 
    "    xxxxxx      xxxxxx    ", 
    "    x....x      x....x    ",
    "    x....x      x....x    ",
    "    x....x      x....x    ",
    "    x....x      x....x    ",
    "    x....x      x....x    ", #20
    "    x....x      x....x    ",
    "    x.....x    x.....x    ",
    "    xxxxxxxxx xxxxxxxx    ",       
    "                          ", #24  (25 total)
    "                          ", 
    "                          ", 
    "                          "
    )
BigRezonator2Map.CopyMapToColorSprite(TheSprite=BigRezonator2)










BigRezonator2Map.map= (
    #0.........1.........2.........3
    "                          ", #0
    "            xx            ",
    "          x.YY.x          ",
    "         x......x         ",
    " xxxxxxxxxxxxxxxxxxxxxxxx ",
    "  x....................x  ",
    "  x....................x  ",
    "  x....................x  ",
    "  x....................x  ",
    " xxxxxxxxxxxxxxxxxxxxxxxx ",
    "   x....x  xxxx  x....x   ", #10
    "   x....x        x....x   ", 
    "   x....x        x....x   ", 
    "   x....x        x....x   ", 
    "   x....x        x....x   ", 
    "   xxxxxx        xxxxxx   ", 
    "   x....x        x....x   ",
    "   x....x        x....x   ",
    "   x....x        x....x   ",
    "   x....x        x....x   ",
    "   x....x        x....x   ", #20
    "   x....x        x....x   ",
    "   x.....x      x.....x   ",
    "   xxxxxxxxx   xxxxxxxx   ",       
    "                          ", #24  (25 total)
    "                          ", 
    "                          ", 
    "                          ", 
    "                          "
    )
BigRezonator2Map.CopyMapToColorSprite(TheSprite=BigRezonator2)








BigRezonator2Map.map= (
    #0.........1.........2.........3
    "                          ", #0
    "            xx            ",
    "          x.YY.x          ",
    "         x......x         ",
    " xxxxxxxxxxxxxxxxxxxxxxxx ",
    "  x....................x  ",
    "  x....................x  ",
    "  x....................x  ",
    "  x....................x  ",
    " xxxxxxxxxxxxxxxxxxxxxxxx ",
    "  x....x   xxxx   x....x  ", #10
    "  x....x          x....x  ", 
    "  x....x          x....x  ", 
    "  x....x          x....x  ", 
    "  x....x          x....x  ", 
    "  xxxxxx          xxxxxx  ", 
    "  x....x          x....x  ",
    "  x....x          x....x  ",
    "  x....x          x....x  ",
    "  x....x          x....x  ",
    "  x....x          x....x  ", #20
    "  x....x          x....x  ",
    "  x.....x        x.....x  ",
    "  xxxxxxxxx     xxxxxxxx  ",       
    "                          ", #24  (25 total)
    "                          ", 
    "                          ", 
    "                          ", 
    "                          "
    )
BigRezonator2Map.CopyMapToColorSprite(TheSprite=BigRezonator2)








LightBike = ColorAnimatedSprite(
  h=0, 
  v=0, 
  name="LightBike", 
  width  = 23, 
  height = 9, 
  frames = 0, 
  framerate=1,
  grid=[]  )


LightBikeMap = TextMap(
  h      = 1,
  v      = 1,
  width  = LightBike.width, 
  height = LightBike.height
  )


LightBikeMap.ColorList = {
  ' ' : 0,
  '.' : 34, #dark cyan
  '#' : 36, #Med cyan
  '-' : 38, #high cyan
  'o' : 26,
  '*' : 3   #white
  }


LightBikeMap.TypeList = {
  ' ' : 'Empty'
 }



LightBikeMap.map= (
    #0.........1.........2.........3
    "      -oo              ", 
    "     -oooooooo         ", 
    "   ----ooo.ooooo ..    ", 
    "  .--. -....oo- .--.   ", 
    " .-*.-. -..o.- .-*.-.  ", 
    " .-..-.  -..o- .-..-.  ", 
    "  .--.    ...o- .--.   ",  
    "   ..            ..    ", 
    "                       ", 
    )

  
LightBikeMap.CopyMapToColorSprite(TheSprite=LightBike)

LightBikeMap.map= (
    #0.........1.........2.........3
    "      -oo              ", 
    "     -oooooooo         ", 
    "   ----ooo.ooooo ..    ", 
    "  .--. -....oo- .--.   ", 
    " .-..-. -..o.- .-..-.  ", 
    " .-*.-.  -..o- .-*.-.  ", 
    "  .--.    ...o- .--.   ",  
    "   ..            ..    ", 
    "                       ", 
    )

  
LightBikeMap.CopyMapToColorSprite(TheSprite=LightBike)



LightBikeMap.map= (
    #0.........1.........2.........3
    "      -oo              ", 
    "     -oooooooo         ", 
    "   ----ooo.ooooo ..    ", 
    "  .--. -....oo- .--.   ", 
    " .-..-. -..o.- .-..-.  ", 
    " .-.*-.  -..o- .-.*-.  ", 
    "  .--.    ...o- .--.   ",  
    "   ..            ..    ", 
    "                       ", 
    )

  
LightBikeMap.CopyMapToColorSprite(TheSprite=LightBike)


LightBikeMap.map= (
    #0.........1.........2.........3
    "      -oo              ", 
    "     -oooooooo         ", 
    "   ----ooo.ooooo ..    ", 
    "  .--. -....oo- .--.   ", 
    " .-.*-. -..o.- .-.*-.  ", 
    " .-..-.  -..o- .-..-.  ", 
    "  .--.    ...o- .--.   ",  
    "   ..            ..    ", 
    "                       ", 
    )

  
LightBikeMap.CopyMapToColorSprite(TheSprite=LightBike)



HeartSprite = ColorAnimatedSprite(
  h=0, 
  v=0, 
  name="Heart", 
  width  = 32, 
  height = 32, 
  frames = 0, 
  framerate=2,
  grid=[]  )

                 

HeartSpriteMap = TextMap(
  h      = 1,
  v      = 1,
  width  = 32, 
  height = 32
  )

HeartSpriteMap.ColorList = {
  ' ' : 0,
  '*' : 3,  # med  white
  '#' : 4,  # high white
  '-' : 5,  # dark red
  '.' : 6,  # low  red
  'o' : 7,  # med  red
  'O' : 8,  # high red
}

RunningMan3SpriteMap.TypeList = {
  ' ' : 'Empty'
  
}



HeartSpriteMap.map= (
  #0.........1.........2.........3...
  "                                 ", 
  "                                 ", 
  "                                 ", 
  "        ----         ----        ", 
  "      -ooooo--     --ooo---      ", 
  "     -OOOOOOo-     -oooo----     ", 
  "    -OOO***Oo--   --ooooo----    ", 
  "    OOO*##*Oo--   -ooooooo---    ", 
  "   -OO*##*OOoo-- -oooooooo----   ", 
  "   OO*##*OOOoo-- -ooooooooo---   ", 
  "  -O*##*OOOOoo ---oooooooooo---  ", 
  "  -O*##*OOOOoooooooooooooooo---  ", 
  "  -OO***OOOOOooooooooooooooo---  ", 
  "  -OOO*OOOOOOOoooooooooooooo---  ", 
  "  -ooOOOOOOOOOoooooooooooooo---  ", 
  "  --ooOOOOOOOOoooooooooooooo---  ", 
  "  --oooOOOOOOoooooooooooooo----  ", 
  "   --oooOOOOooooooooooooooo---   ", 
  "    --oooOOOoooooooooooooo---    ", 
  "     --oooOoooooooooooooo---     ", 
  "      --ooooooooooooooooo--      ", 
  "       --ooooooooooooooo--       ", 
  "        --ooooooooooooo--        ", 
  "         --ooooooooooo--         ", 
  "          --ooooooooo--          ", 
  "           --ooooooo--           ", 
  "            ---ooooo-            ", 
  "             ---ooo-             ", 
  "              --o--              ", 
  "               ---               ", 
  "                -                ", 
  "                                 " 
)
      
HeartSpriteMap.CopyMapToColorSprite(TheSprite=HeartSprite)






DropShip = ColorAnimatedSprite(h=0, v=0, name="DropShip", width=5, height=8, frames=2, framerate=1,grid=[])
DropShip.grid.append(
  [
    0, 0, 0, 0, 0,
    0, 0,15, 0, 0,
    0, 0,15, 0, 0,
    0,14,15,14, 0,
    0,14, 7,14, 0,
    0, 0, 6, 0, 0,
    0, 0, 5, 0, 0,
    0, 0, 0, 0, 0,
  ]
)

DropShip.grid.append(
  [
    0, 0, 0, 0, 0,
    0, 0,15, 0, 0,
    0, 0,15, 0, 0,
    0,14,15,14, 0,
    0,14, 6,14, 0,
    0, 0, 5, 0, 0,
    0, 0, 5, 0, 0,
    0, 0, 0, 0, 0,
  ]
)




SpaceInvader = ColorAnimatedSprite(h=0, v=0, name="SpaceInvader", width=13, height=8, frames=2, framerate=1,grid=[])
SpaceInvader.grid.append(
  [
    0, 0, 9, 0, 0, 0, 0, 0, 0, 0, 0, 9, 0,
    0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9, 0, 0, 
    0, 0, 9, 9,11, 9, 9, 9,11, 9, 9, 0, 0,
    0, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 0,
    0, 9, 0, 9, 9, 9, 9, 9, 9, 9, 0, 9, 0,
    0, 9, 0, 9, 0, 0, 0, 0, 0, 9, 0, 9, 0,
    0, 0, 0, 0, 9, 0, 0, 0, 9, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
  ]
)
SpaceInvader.grid.append(
  [
    0, 0, 9, 0, 0, 0, 0, 0, 0, 0, 0, 9, 0,
    0, 0, 0, 9, 9, 9, 9, 9, 9, 9, 9, 0, 0,
    0, 0, 9, 9,11, 9, 9, 9,11, 9, 9, 0, 0,
    0, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 0,
    0, 9, 0, 9, 9, 9, 9, 9, 9, 9, 0, 9, 0,
    0, 9, 0, 9, 0, 0, 0, 0, 0, 9, 0, 9, 0,
    0, 0, 0, 9, 0, 0, 0, 0, 0, 9, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
  ]
)



TinyInvader = ColorAnimatedSprite(h=0, v=0, name="TinyInvader", width=7, height=6, frames=4, framerate=1,grid=[])
TinyInvader.grid.append(
  [
   0, 0, 0, 8, 0, 0, 0,
   0, 0, 9, 9, 9, 0, 0,
   0, 9,11, 9,11, 9, 0,
   0, 9, 9, 9, 9, 9, 0,
   0, 0, 9, 0, 9, 0, 0,
   0, 9, 0, 0, 0, 9, 0
  ]
)
TinyInvader.grid.append(
  [
   0, 0, 0, 8, 0, 0, 0, 
   0, 0, 9, 9, 9, 0, 0, 
   0, 9,11, 9,11, 9, 0, 
   0, 9, 9, 9, 9, 9, 0, 
   0, 0, 9, 0, 9, 0, 0, 
   0, 9, 0, 0, 0, 9, 0
  ]
)
TinyInvader.grid.append(
  [
   0, 0, 0,16, 0, 0, 0,
   0, 0, 9, 9, 9, 0, 0,
   0, 9,11, 9,11, 9, 0,
   0, 9, 9, 9, 9, 9, 0,
   0, 0, 9, 0, 9, 0, 0,
   0, 9, 0, 0, 0, 9, 0
  ]
)

TinyInvader.grid.append(
  [
   0, 0, 0,16, 0, 0, 0,
   0, 0, 9, 9, 9, 0, 0,
   0, 9,11, 9,11, 9, 0,
   0, 9, 9, 9, 9, 9, 0,
   0, 0, 9, 0, 9, 0, 0,
   0, 0, 9, 0, 9, 0, 0
  ]
)




SmallInvader = ColorAnimatedSprite(h=0, v=0, name="SmallInvader", width=9, height=6, frames=2, framerate=1,grid=[])
SmallInvader.grid.append(
  [
    0, 0, 0, 9, 9, 9, 0, 0, 0,
    0, 0, 9, 9, 9, 9, 9, 0, 0,
    0, 9,10,11, 9,11,10, 9, 0,
    0, 9, 9, 9, 9, 9, 9, 9, 0,
    0, 9, 0, 9, 0, 9, 0, 9, 0,
    0, 0, 9, 0, 9, 0, 9, 0, 0,
  ]
)
SmallInvader.grid.append(
  [
    0, 0, 0, 9, 9, 9, 0, 0, 0,
    0, 0, 9, 9, 9, 9, 9, 0, 0,
    0, 9,10,11, 9,11,10, 9, 0,
    0, 9, 9, 9, 9, 9, 9, 9, 0,
    0, 9, 0, 9, 0, 9, 0, 9, 0,
    0, 9, 0, 9, 0, 9, 0, 9, 0,
  ]
)



LittleShipFlying = ColorAnimatedSprite(h=0, v=0, name="LittleShips", width=16, height=8, frames=2,framerate=1,grid=[])

LittleShipFlying.grid.append(
  [
    0, 0, 0, 0, 0, 0, 0, 0, 0,15, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 5, 6, 7, 8, 5, 2, 2, 2, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,15, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 5, 6, 7, 8, 5, 2, 2, 2,
    0, 0, 0, 0, 0,15, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 6, 7, 8, 5, 2, 2, 2, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    
   ]
)

LittleShipFlying.grid.append(
  [
    0, 0, 0, 0, 0, 0, 0, 0, 0,15, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 5, 6, 7, 8, 5, 2, 2, 2, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,15, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 5, 6, 7, 8, 5, 2, 2, 2,
    0, 0, 0, 0, 0,15, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 6, 7, 8, 5, 2, 2, 2, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    
   ]
)


                  
BigShipFlying = ColorAnimatedSprite(h=0, v=0, name="BigShipFlying", width=36, height=8, frames=6, framerate=1,grid=[])

BigShipFlying.grid.append(
  [
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 5, 5, 5, 5,14,14,14,14,14,16,14,16,14,14,14,14, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 5, 5, 5, 5, 6, 6, 7, 7, 8, 8,17,14,14, 9,14, 9,14,14,13,13,13,13, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,15, 0, 0,
    0, 5, 5, 5, 5, 6, 6, 7, 7, 8, 8,17,14,14,14, 9,14, 9,13,13, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,17,14,14,14,
    0, 0, 0, 0, 0, 0, 0, 5, 5, 5, 5, 1,14,13,13,13,13,13, 8, 8, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 5,13,13,13,13, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
   ]
)

BigShipFlying.grid.append(
  [
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 5, 5, 5, 5,14,14, 1,14,14,16,14,16,14,14,14,14, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 5, 5, 5, 5, 6, 6, 7, 8, 8, 5,17,14, 1, 9,14, 9,14,14,13,13,13,13, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0,
    0, 5, 5, 5, 5, 6, 6, 7, 8, 8, 5,17,14, 1,14, 9,14, 9,13,13, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5,14,14,14,
    0, 0, 0, 0, 0, 0, 0, 5, 5, 5, 5, 1,14, 1,13,13,13,13, 0, 5, 5, 5, 7, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 5,13,13,13,13, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
   ]
)

BigShipFlying.grid.append(
  [
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 5, 5, 5, 5,14,14, 1,14,14,16,14,16,14,14,14,14, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 5, 5, 5, 5, 6, 6, 7, 8, 8, 5,17,14, 1, 9,14, 9,14,14,13,13,13,13, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0,
    0, 5, 5, 5, 5, 6, 6, 7, 8, 8, 5,17,14, 1,14, 9,14, 9,13,13, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,17,14,14,14,
    0, 0, 0, 0, 0, 0, 0, 5, 5, 5, 5, 1,14, 1,13,13,13,13, 0, 0, 0, 0, 0, 5, 5, 5, 7, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 5,13,13,13,13, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
   ]
)

BigShipFlying.grid.append(
  [
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 5, 5, 5, 5,14,14, 1,14,14,16,14,16,14,14,14,14, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 5, 5, 5, 5, 6, 6, 7, 8, 8, 5,17,14, 1, 9,14, 9,14,14,13,13,13,13, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0,
    0, 5, 5, 5, 5, 6, 6, 7, 8, 8, 5,17,14, 1,14, 9,14, 9,13,13, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5,14,14,14,
    0, 0, 0, 0, 0, 0, 0, 5, 5, 5, 5, 1,14, 1,13,13,13,13, 0, 0, 0, 0, 0, 0, 0, 0, 5, 5, 5, 7, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 5,13,13,13,13, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
   ]
)

BigShipFlying.grid.append(
  [
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 5, 5, 5, 5,14,14, 1,14,14,16,14,16,14,14,14,14, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 5, 5, 5, 5, 6, 6, 7, 8, 8, 5,17,14, 1, 9,14, 9,14,14,13,13,13,13, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0,
    0, 5, 5, 5, 5, 6, 6, 7, 8, 8, 5,17,14, 1,14, 9,14, 9,13,13, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,17,14,14,14,
    0, 0, 0, 0, 0, 0, 0, 5, 5, 5, 5, 1,14, 1,13,13,13,13, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5, 5, 5, 7, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 5,13,13,13,13, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
   ]
)

BigShipFlying.grid.append(
  [
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 5, 5, 5, 5,14,14, 1,14,14,16,14,16,14,14,14,14, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 5, 5, 5, 5, 6, 6, 7, 8, 8, 5,17,14, 1, 9,14, 9,14,14,13,13,13,13, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0,
    0, 5, 5, 5, 5, 6, 6, 7, 8, 8, 5,17,14, 1,14, 9,14, 9,13,13, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5,14,14,14,
    0, 0, 0, 0, 0, 0, 0, 5, 5, 5, 5, 1,14, 1,13,13,13,13, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5, 5, 5,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 5,13,13,13,13, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
   ]
)






BigShipExplosion = ColorAnimatedSprite(
  h = 0, 
  v = 0,
  name         = "Explosion", 
  width        = 8, 
  height       = 5, 
  frames       = 10,
  framerate    = 15, 
  grid         = []
)
BigShipExplosion.grid.append(
   [ 0, 0, 0, 0, 0, 0, 0, 0, 
     0, 0, 0, 5, 5, 0, 0, 0, 
     0, 0, 5, 5, 5, 5, 0, 0, 
     0, 0, 0, 5, 5, 0, 0, 0, 
     0, 0, 0, 0, 0, 0, 0, 0
   ]
)
BigShipExplosion.grid.append(
   [ 0, 0, 0, 0, 0, 0, 0, 0, 
     0, 0, 0, 5, 5, 0, 0, 0, 
     0, 0, 5, 5, 5, 5, 0, 0, 
     0, 0, 0, 5, 5, 0, 0, 0, 
     0, 0, 0, 0, 0, 0, 0, 0
   ]
)

BigShipExplosion.grid.append(
   [ 0, 0, 0, 5, 5, 0, 0, 0, 
     0, 0, 0, 7, 7, 0, 0, 0, 
     0, 5, 7, 7, 7, 7, 5, 0, 
     0, 0, 0, 7, 7, 0, 0, 0, 
     0, 0, 0, 5, 5, 0, 0, 0
   ]
)
BigShipExplosion.grid.append(
   [ 0, 0, 0, 5, 5, 0, 0, 0, 
     0, 0, 0, 7, 7, 0, 0, 0, 
     0, 5, 7, 7, 7, 7, 5, 0, 
     0, 0, 0, 7, 7, 0, 0, 0, 
     0, 0, 0, 5, 5, 0, 0, 0
   ]
)

BigShipExplosion.grid.append(
   [ 0, 0, 0, 8, 8, 0, 0, 0, 
     0, 0, 0,39,39, 0, 0, 0, 
     8, 8,39,39,39,39, 8, 8, 
     0, 0, 0,39,39, 0, 0, 0, 
     0, 0, 0, 8, 8, 0, 0, 0
   ]
)

BigShipExplosion.grid.append(
   [ 0, 0, 0,39,39, 0, 0, 0, 
     0, 0, 0,45,45, 0, 0, 0, 
    39,39,45,45,45,45,39,39, 
     0, 0, 0,45,45, 0, 0, 0, 
     0, 0, 0,39,39, 0, 0, 0
   ]
)


BigShipExplosion.grid.append(
   [ 0, 0, 0,45,45, 0, 0, 0, 
     0, 0,45,45,45,45, 0, 0, 
    45,45,45,45,45,45,45,45, 
     0, 0,45,45,45,45, 0, 0, 
     0, 0, 0,45,45, 0, 0, 0
   ]
)


BigShipExplosion.grid.append(
   [ 0, 0, 0, 8, 8, 0, 0, 0, 
     0, 0, 5, 5, 5, 5, 0, 0, 
     8, 8, 5, 5, 5, 5, 8, 8, 
     0, 0, 5, 5, 5, 5, 0, 0, 
     0, 0, 0, 8, 8, 0, 0, 0
   ]
)

BigShipExplosion.grid.append(
   [ 0, 0, 0, 8, 8, 0, 0, 0, 
     0, 0, 5, 5, 5, 5, 0, 0, 
     8, 8, 5, 5, 5, 5, 8, 8, 
     0, 0, 5, 5, 5, 5, 0, 0, 
     0, 0, 0, 8, 8, 0, 0, 0
   ]
)

BigShipExplosion.grid.append(
   [ 0, 0, 0, 0, 0, 0, 0, 0, 
     0, 0, 0, 0, 0, 0, 0, 0, 
     0, 0, 0, 0, 0, 0, 0, 0, 
     0, 0, 0, 0, 0, 0, 0, 0, 
     0, 0, 0, 0, 0, 0, 0, 0
   ]
)


DropShip = ColorAnimatedSprite(h=0, v=0, name="DropShip", width=5, height=8, frames=2, framerate=1,grid=[])
DropShip.grid.append(
  [
    0, 0, 0, 0, 0,
    0, 0,15, 0, 0,
    0, 0,15, 0, 0,
    0,14,15,14, 0,
    0,14, 7,14, 0,
    0, 0, 6, 0, 0,
    0, 0, 5, 0, 0,
    0, 0, 0, 0, 0,
  ]
)

DropShip.grid.append(
  [
    0, 0, 0, 0, 0,
    0, 0,15, 0, 0,
    0, 0,15, 0, 0,
    0,14,15,14, 0,
    0,14, 6,14, 0,
    0, 0, 5, 0, 0,
    0, 0, 5, 0, 0,
    0, 0, 0, 0, 0,
  ]
)



PlayerShipExplosion = ColorAnimatedSprite(
  h=0, v=0, name="Explosion", width=5, height=5, 
  frames=14,
  framerate=2,grid=[]
)
PlayerShipExplosion.grid.append(
  [0,0,0,0,0,
   0,0,0,0,0,
   0,0,4,0,0,
   0,0,0,0,0,
   0,0,0,0,0
   ]
)

PlayerShipExplosion.grid.append(
   [0,0,0,0,0,
    0, 0, 4, 0,0,
    0, 4,18, 4,0,
    0, 0, 4, 0,0,
    0,0,0,0,0
   ]
)
  
PlayerShipExplosion.grid.append(
   [ 0, 0, 4, 0, 0,
     0,18,18,18, 0,
     4,18,19,18, 4,
     0,18,18,18, 0,
     0, 0, 4, 0,0
   ]
)
PlayerShipExplosion.grid.append(
   [ 0,18,18,18, 0,
    18,19,19,19,18,
    18,18,20,19,18,
    18,19,19,19,18,
     0,18,18,18, 0
   ]
)
PlayerShipExplosion.grid.append(
   [ 0,19,19,19, 0,
    19,20,20,20,19,
    19,20,20,20,19,
    19,20,20,20,19,
     0,19,19,19, 0
   ]
)
PlayerShipExplosion.grid.append(
   [ 0,20,20,20, 0,
    20,20,20,20,20,
    20,20,20,20,20,
    20,20,20,20,20,
     0,20,20,20, 0
   ]


)
PlayerShipExplosion.grid.append(
   [00,20,20,20,00,
    20,20,20,20,20,
    20,20, 8,20,20,
    20,20,20,20,20,
    00,20,20,20,00
   ]
)
PlayerShipExplosion.grid.append(
   [ 0,20,20,20, 0,
    20,20, 8,20,20,
    20, 8, 7, 8,20,
    20,20, 8,20,20,
     0,20,20,20, 0
   ]
)  

PlayerShipExplosion.grid.append(
   [ 0,20, 8,20, 0,
    20, 8, 7, 8,20,
     8, 7, 6, 7, 8,
    20, 8, 7, 8,20,
     0,20, 8,20, 0
   ]
)
PlayerShipExplosion.grid.append(
   [ 0, 8, 7, 8, 0,
     8, 7, 6, 7, 8,
     7, 6, 5, 6, 7,
     8, 7, 6, 7, 8,
     0, 8, 7, 8, 0
   ]
)
PlayerShipExplosion.grid.append(
   [ 0, 7, 6, 7, 0,
     7, 6, 0, 6, 7,
     6, 5, 0, 5, 6,
     7, 6, 0, 6, 7,
     0, 7, 6, 7, 0
   ]
)
PlayerShipExplosion.grid.append(
   [ 0, 6, 5, 6, 0,
     6, 5, 0, 5, 6,
     5, 0, 0, 0, 5,
     6, 5, 0, 5, 6,
     0, 6, 5, 6, 0
   ]
)
PlayerShipExplosion.grid.append(
   [ 0, 5, 0, 5, 0,
     5, 0, 0, 0, 5,
     0, 0, 0, 0, 0,
     5, 0, 0, 0, 5,
     0, 5, 0, 5, 0
   ]
)  

PlayerShipExplosion.grid.append(
   [ 0, 0, 0, 0, 0,
     0, 0, 0, 0, 0,
     0, 0, 0, 0, 0,
     0, 0, 0, 0, 0,
     0, 0, 0, 0, 0
   ]
)  




BomberShipExplosion = ColorAnimatedSprite(
  h = 0, 
  v = 0,
  name         = "Explosion", 
  width        = 5, 
  height       = 5, 
  frames       = 9,
  framerate    = 15, 
  grid         = []
)
BomberShipExplosion.grid.append(
   [ 0, 0, 0, 0, 0,
     0, 0,45, 0, 0,
     0,45,45,45, 0,
     0, 0,45, 0, 0,
     0, 0, 0, 0, 0
   ]
)

BomberShipExplosion.grid.append(
   [ 0, 0,45, 0, 0,
     0,45,45,45, 0,
    45,45,45,45,45,
     0,45,45,45, 0,
     0, 0,45, 0, 0
   ]
)

BomberShipExplosion.grid.append(
   [ 0, 0,42, 0, 0,
     0,45,42,45, 0,
    42,42,42,42,42,
     0,45,42,45, 0,
     0, 0,42, 0, 0
   ]
)


BomberShipExplosion.grid.append(
   [ 0, 0,42, 0, 0,
     0, 2,20, 2, 0,
    42,20,20,20,42,
     0, 2,20, 2, 0,
     0, 0,42, 0, 0
   ]
)


BomberShipExplosion.grid.append(
   [ 0, 0,20, 0, 0,
     0, 1,20, 1, 0,
    20,20,39,20,20,
     0, 1,20, 1, 0,
     0, 0,20, 0, 0
   ]
)

BomberShipExplosion.grid.append(
   [ 0, 0,39, 0, 0,
     0, 1,39, 1, 0,
    39,39,39,39,20,
     0, 1,39, 1, 0,
     0, 0,39, 0, 0
   ]
)

BomberShipExplosion.grid.append(
   [ 0, 0,39, 0, 0,
     0, 1, 8, 1, 0,
    39, 8, 6, 8,39,
     0, 1, 8, 1, 0,
     0, 0,39, 0, 0
   ]
)


BomberShipExplosion.grid.append(
   [ 0, 0, 0, 0, 0,
     0, 0, 5, 0, 0,
     0, 5, 5, 5, 0,
     0, 0, 5, 0, 0,
     0, 0, 0, 0, 0
   ]
)

BomberShipExplosion.grid.append(
   [ 0, 0, 0, 0, 0,
     0, 0, 0, 0, 0,
     0, 0, 0, 0, 0,
     0, 0, 0, 0, 0,
     0, 0, 0, 0, 0
   ]
)





#(self,h,v,name,width,height,frames,currentframe,framerate,grid):
SatelliteSprite = ColorAnimatedSprite(
  h=-1, v=-1, name="HomingMissile", width=3, height=3, 
  frames       = 7,

  framerate    = 1,
  grid         = []
)
SatelliteSprite.grid.append(
  [ 0, 1, 0,
    1, 1, 1,
    0, 1, 0]
)

SatelliteSprite.grid.append(
  [ 0, 1, 0,
    1, 2, 1,
    0, 1, 0]
)
SatelliteSprite.grid.append(
  [ 0, 1, 0,
    1, 3, 1,
    0, 1, 0]
)
SatelliteSprite.grid.append(
  [ 0, 1, 0,
    1, 4, 1,
    0, 1, 0]
)

SatelliteSprite.grid.append(
  [ 0, 1, 0,
    1, 4, 1,
    0, 1, 0]
)

SatelliteSprite.grid.append(
  [ 0, 1, 0,
    1, 3, 1,
    0, 1, 0]
)

SatelliteSprite.grid.append(
  [ 0, 1, 0,
    1, 2, 1,
    0, 1, 0]
)






#(self,h,v,name,width,height,frames,currentframe,framerate,grid):
SatelliteSprite2 = ColorAnimatedSprite(
  h=-1, v=-1, name="HomingMissile", width=3, height=3, 
  frames       = 7,

  framerate    = 1,
  grid         = []
)
SatelliteSprite2.grid.append(
  [ 0, 1, 0,
    1,13, 1,
    0, 1, 0]
)

SatelliteSprite2.grid.append(
  [ 0, 1, 0,
    1,14, 1,
    0, 1, 0]
)
SatelliteSprite2.grid.append(
  [ 0, 1, 0,
    1,15, 1,
    0, 1, 0]
)
SatelliteSprite2.grid.append(
  [ 0, 1, 0,
    1,16, 1,
    0, 1, 0]
)

SatelliteSprite2.grid.append(
  [ 0, 1, 0,
    1,16, 1,
    0, 1, 0]
)

SatelliteSprite2.grid.append(
  [ 0, 1, 0,
    1,15, 1,
    0, 1, 0]
)

SatelliteSprite2.grid.append(
  [ 0, 1, 0,
    1,14, 1,
    0, 1, 0]
)







#(self,h,v,name,width,height,frames,currentframe,framerate,grid):
SatelliteSprite3 = ColorAnimatedSprite(
  h=-1, v=-1, name="HomingMissile", width=3, height=3, 
  frames       = 8,

  framerate    = 1,
  grid         = []
)
SatelliteSprite3.grid.append(
  [39,39, 0,
    0, 0, 0,
    0, 0, 0]
)

SatelliteSprite3.grid.append(
  [ 0,39,39,
    0, 0, 0,
    0, 0, 0]
)
SatelliteSprite3.grid.append(
  [ 0, 0,39,
    0, 0,39,
    0, 0, 0]
)
SatelliteSprite3.grid.append(
  [ 0, 0, 0,
    0, 0,39,
    0, 0,39]
)
SatelliteSprite3.grid.append(
  [ 0, 0, 0,
    0, 0, 0,
    0,39,39]
)
SatelliteSprite3.grid.append(
  [ 0, 0, 0,
    0, 0, 0,
   39,39, 0]
)
SatelliteSprite3.grid.append(
  [ 0, 0, 0,
   39, 0, 0,
   39, 0, 0]
)
SatelliteSprite3.grid.append(
  [39, 0, 0,
   39, 0, 0,
    0, 0, 0]
)



#(self,h,v,name,width,height,frames,currentframe,framerate,grid):
SatelliteSprite4 = ColorAnimatedSprite(
  h=-1, v=-1, name="HomingMissile", width=3, height=3, 
  frames       = 8,

  framerate    = 1,
  grid         = []
)
SatelliteSprite4.grid.append(
  [40,40, 0,
    0, 0, 0,
    0, 0, 0]
)

SatelliteSprite4.grid.append(
  [ 0,40,40,
    0, 0, 0,
    0, 0, 0]
)
SatelliteSprite4.grid.append(
  [ 0, 0,40,
    0, 0,40,
    0, 0, 0]
)
SatelliteSprite4.grid.append(
  [ 0, 0, 0,
    0, 0,40,
    0, 0,40]
)
SatelliteSprite4.grid.append(
  [ 0, 0, 0,
    0, 0, 0,
    0,40,40]
)
SatelliteSprite4.grid.append(
  [ 0, 0, 0,
    0, 0, 0,
   40,40, 0]
)
SatelliteSprite4.grid.append(
  [ 0, 0, 0,
   40, 0, 0,
   40, 0, 0]
)
SatelliteSprite4.grid.append(
  [40, 0, 0,
   40, 0, 0,
    0, 0, 0]
)




#(self,h,v,name,width,height,frames,currentframe,framerate,grid):
SatelliteSprite5 = ColorAnimatedSprite(
  h=-1, v=-1, name="HomingMissile", width=3, height=3, 
  frames       = 8,

  framerate    = 1,
  grid         = []
)
SatelliteSprite5.grid.append(
  [ 0,43,43,
    0, 0, 0,
    0, 0, 0]
)

SatelliteSprite5.grid.append(
  [43,43, 0,
    0, 0, 0,
    0, 0, 0]
)
SatelliteSprite5.grid.append(
  [43, 0, 0,
   43, 0, 0,
    0, 0, 0]
)
SatelliteSprite5.grid.append(
  [ 0, 0, 0,
   43, 0, 0,
   43, 0, 0]
)
SatelliteSprite5.grid.append(
  [ 0, 0, 0,
    0, 0, 0,
   43,43, 0]
)
SatelliteSprite5.grid.append(
  [ 0, 0, 0,
    0, 0, 0,
    0,43,43]
)
SatelliteSprite5.grid.append(
  [ 0, 0, 0,
    0, 0,43,
    0, 0,43]
)
SatelliteSprite5.grid.append(
  [ 0, 0,43,
    0, 0,43,
    0, 0, 0]
)



#(self,h,v,name,width,height,frames,currentframe,framerate,grid):
SatelliteSprite6 = ColorAnimatedSprite(
  h=-1, v=-1, name="HomingMissile", width=3, height=3, 
  frames       = 8,

  framerate    = 1,
  grid         = []
)
SatelliteSprite6.grid.append(
  [42,20,20,
    0, 0,20,
    0, 0, 0]
)


SatelliteSprite6.grid.append(
  [20,20,20,
   42, 0, 0,
    0, 0, 0]
)

SatelliteSprite6.grid.append(
  [20,20, 0,
   20, 0, 0,
   42, 0, 0]
)

SatelliteSprite6.grid.append(
  [20, 0, 0,
   20, 0, 0,
   20,42, 0]
)


SatelliteSprite6.grid.append(
  [ 0, 0, 0,
   20, 0, 0,
   20,20,42]
)

SatelliteSprite6.grid.append(
  [ 0, 0, 0,
    0, 0,42,
   20,20,20]
)


SatelliteSprite6.grid.append(
  [ 0, 0,42,
    0, 0,20,
    0,20,20]
)



SatelliteSprite6.grid.append(
  [ 0,42,20,
    0, 0,20,
    0, 0,20]
)



#(self,h,v,name,width,height,frames,currentframe,framerate,grid):
SatelliteSprite7 = ColorAnimatedSprite(
  h=-1, v=-1, name="HomingMissile", width=3, height=3, 
  frames       = 8,

  framerate    = 1,
  grid         = []
)
SatelliteSprite7.grid.append(
  [41,41,41,
    0, 0, 0,
    0, 0, 0]
)

SatelliteSprite7.grid.append(
  [41, 0,41,
    0,41, 0,
    0, 0, 0]
)

SatelliteSprite7.grid.append(
  [41, 0,41,
    0,41, 0,
    0,41, 0]
)


SatelliteSprite7.grid.append(
  [41, 0,41,
   41, 0,41,
   41,41,41]
)

SatelliteSprite7.grid.append(
  [ 0,41, 0,
    0,41, 0,
   41,41,41]
)

SatelliteSprite7.grid.append(
  [ 0, 0, 0,
    0,41, 0,
   41,41,41]
)

SatelliteSprite7.grid.append(
  [ 0, 0, 0,
    0, 0, 0,
   41,41,41]
)

SatelliteSprite7.grid.append(
  [ 0, 0, 0,
    0, 0, 0,
   41,41,41]
)


#(self,h,v,name,width,height,frames,currentframe,framerate,grid):
SmallUFOSprite = ColorAnimatedSprite(
  h = -1,
  v = -1,
  name   = "HomingMissile", 
  width  = 3, 
  height = 3, 
  frames = 4, 

  framerate    = 1,
  grid = []
)


SmallUFOSprite.grid.append(
  [ 4, 0, 0,
    0, 1, 0,
    0, 0, 4
    
  ]
)


SmallUFOSprite.grid.append(
  [ 0, 4, 0,
    0, 1, 0,
    0, 4, 0
    
  ]
)
SmallUFOSprite.grid.append(
  [ 0, 0, 4,
    0, 1, 0,
    4, 0, 0
    
  ]
)

SmallUFOSprite.grid.append(
  [ 0, 0, 0,
    4, 1, 4,
    0, 0, 0
    
  ]
)






#(self,h,v,name,width,height,frames,currentframe,framerate,grid):
SmallUFOSprite2 = ColorAnimatedSprite(
  h = -1,
  v = -1,
  name   = "HomingMissile", 
  width  = 3, 
  height = 3, 
  frames = 2, 

  framerate    = 1,
  grid = []
)


SmallUFOSprite2.grid.append(
  [14, 0,14,
    0,22, 0,
    0, 5, 0
    
  ]
)

SmallUFOSprite2.grid.append(
  [14, 0,14,
    0,22, 0,
    0, 8, 0
    
  ]
)





#(self,h,v,name,width,height,frames,currentframe,framerate,grid):
SmallUFOSprite3 = ColorAnimatedSprite(
  h = -1,
  v = -1,
  name   = "HomingMissile", 
  width  = 3, 
  height = 3, 
  frames = 2, 

  framerate    = 1,
  grid = []
)


SmallUFOSprite3.grid.append(
  [ 0,25, 0,
   25, 5,25,
    0, 8, 0
    
  ]
)

SmallUFOSprite3.grid.append(
  [ 0,25, 0,
   25, 8,25,
    0, 5, 0
    
  ]
)



#(self,h,v,name,width,height,frames,currentframe,framerate,grid):
SmallUFOSprite4 = ColorAnimatedSprite(
  h = -1,
  v = -1,
  name   = "HomingMissile", 
  width  = 3, 
  height = 3, 
  frames = 4, 

  framerate    = 1,
  grid = []
)


SmallUFOSprite4.grid.append(
  [ 0,25,37,
   25, 0,25,
    0,25, 0
    
  ]
)


SmallUFOSprite4.grid.append(
  [37,25, 0,
   25, 0,25,
    0,25, 0
    
  ]
)
SmallUFOSprite4.grid.append(
  [ 0,25, 0,
   25, 0,25,
   37,25, 0
    
  ]
)
SmallUFOSprite4.grid.append(
  [ 0,25, 0,
   25, 0,25,
    0,25,37
    
  ]
)






#(self,h,v,name,width,height,frames,currentframe,framerate,grid):
SmallUFOSprite5 = ColorAnimatedSprite(
  h = -1,
  v = -1,
  name   = "HomingMissile", 
  width  = 3, 
  height = 3, 
  frames = 2, 

  framerate    = 1,
  grid = []
)


SmallUFOSprite5.grid.append(
  [14, 0,14,
    0,22, 0,
    0,17, 0,
    0,17, 0
    
  ]
)

SmallUFOSprite5.grid.append(
  [14, 0,14,
    0,22, 0,
    0,22, 0,
    0,18, 0
    
  ]
)

SmallUFOSprite5.grid.append(
  [14, 0,14,
    0,17, 0,
    0,19, 0,
    0,20, 0
    
  ]
)





#(self,h,v,name,width,height,frames,currentframe,framerate,grid):
SmallUFOSprite6 = ColorAnimatedSprite(
  h = -1,
  v = -1,
  name   = "HomingMissile", 
  width  = 3, 
  height = 3, 
  frames = 4, 

  framerate    = 1,
  grid = []
)


SmallUFOSprite6.grid.append(
  [ 2, 0, 2,
    2, 5, 2,
    2, 0, 2
    
  ]
)


SmallUFOSprite6.grid.append(
  [ 2, 0, 2,
    2, 5, 2,
    2, 0, 2
    
  ]
)

SmallUFOSprite6.grid.append(
  [ 2, 0, 2,
    2,39, 2,
    2, 0, 2
    
  ]
)

SmallUFOSprite6.grid.append(
  [ 2, 0, 2,
    2,39, 2,
    2, 0, 2
    
  ]
)




#(self,h,v,name,width,height,frames,currentframe,framerate,grid):
SmallUFOSprite7 = ColorAnimatedSprite(
  h = -1,
  v = -1,
  name   = "HomingMissile", 
  width  = 3, 
  height = 3, 
  frames = 4, 

  framerate    = 1,
  grid = []
)


SmallUFOSprite7.grid.append(
  [ 2, 2, 2,
    2,25, 1,
    2, 1, 1
    
  ]
)

SmallUFOSprite7.grid.append(
  [ 2, 2, 2,
    2,25, 1,
    2, 1, 1
    
  ]
)

SmallUFOSprite7.grid.append(
  [ 2, 2, 2,
    2,43, 1,
    2, 1, 1
    
  ]
)

SmallUFOSprite7.grid.append(
  [ 2, 2, 2,
    2,43, 1,
    2, 1, 1
    
  ]
)


#(self,h,v,name,width,height,frames,currentframe,framerate,grid):
MediumUFOSprite = ColorAnimatedSprite(
  h = -1,
  v = -1,
  name   = "HomingMissile", 
  width  = 4, 
  height = 4, 
  frames = 6, 

  framerate    = 1,
  grid = []
)


MediumUFOSprite.grid.append(
  [ 4, 0, 0, 0,
    0, 1, 0, 0,
    0, 0, 1, 0,
    0, 0, 0, 4]
)

MediumUFOSprite.grid.append(
  [ 0, 4, 0, 0,
    0, 1, 0, 0,
    0, 0, 1, 0,
    0, 0, 4, 0]
)


MediumUFOSprite.grid.append(
  [ 0, 0, 4, 0,
    0, 0, 1, 0,
    0, 1, 0, 0,
    0, 4, 0, 0]
)

MediumUFOSprite.grid.append(
  [ 0, 0, 0, 4,
    0, 0, 1, 0,
    0, 1, 0, 0,
    4, 0, 0, 0]
)

MediumUFOSprite.grid.append(
  [ 0, 0, 0, 0,
    0, 0, 1, 4,
    4, 1, 0, 0,
    0, 0, 0, 0]
)

MediumUFOSprite.grid.append(
  [ 0, 0, 0, 0,
    4, 1, 0, 0,
    0, 0, 1, 4,
    0, 0, 0, 0]
)








#(self,h,v,name,width,height,frames,currentframe,framerate,grid):
MediumUFOSprite2 = ColorAnimatedSprite(
  h = -1,
  v = -1,
  name   = "HomingMissile", 
  width  = 4, 
  height = 4, 
  frames = 8, 

  framerate    = 1,
  grid = []
)


MediumUFOSprite2.grid.append(
  [ 0,28,25, 0,
   25, 9, 9,25,
   25, 9, 9,25,
    0,25,25, 0]
)


MediumUFOSprite2.grid.append(
  [ 0,25,28, 0,
   25, 9, 9,25,
   25, 9, 9,25,
    0,25,25, 0]
)

MediumUFOSprite2.grid.append(
  [ 0,25,25, 0,
   25, 9, 9,28,
   25, 9, 9,25,
    0,25,25, 0]
)

MediumUFOSprite2.grid.append(
  [ 0,25,25, 0,
   25, 9, 9,25,
   25, 9, 9,28,
    0,25,25, 0]
)

MediumUFOSprite2.grid.append(
  [ 0,25,25, 0,
   25, 0, 9,25,
   25, 0, 9,25,
    0,25,28, 0]
)

MediumUFOSprite2.grid.append(
  [ 0,25,25, 0,
   25, 9, 9,25,
   25, 9, 9,25,
    0,28,25, 0]
)

MediumUFOSprite2.grid.append(
  [ 0,25,25, 0,
   25, 9, 9,25,
   28, 9, 9,25,
    0,25,25, 0]
)
MediumUFOSprite2.grid.append(
  [ 0,25,25, 0,
   28, 9, 9,25,
   25, 9, 9,25,
    0,25,25, 0]
)









#(self,h,v,name,width,height,frames,currentframe,framerate,grid):
MediumUFOSprite3 = ColorAnimatedSprite(
  h = -1,
  v = -1,
  name   = "HomingMissile", 
  width  = 4, 
  height = 4, 
  frames = 8, 

  framerate    = 1,
  grid = []
)


MediumUFOSprite3.grid.append(
  [ 0, 9, 9, 0,
    9, 9, 9, 9,
    9, 9, 9, 9,
    0,10,10, 0]
)


MediumUFOSprite3.grid.append(
  [ 0, 9, 9, 0,
    9, 9, 9, 9,
    9,10,10, 9,
    0,11,11, 0]
)
MediumUFOSprite3.grid.append(
  [ 0, 9, 9, 0,
    9,10,10, 9,
    9,11,11, 9,
    0,12,12, 0]
)
MediumUFOSprite3.grid.append(
  [ 0,10,10, 0,
    9,11,11, 9,
    9,12,12, 9,
    0,11,11, 0]
)
MediumUFOSprite3.grid.append(
  [ 0,11,11, 0,
    9,12,12, 9,
    9,11,11, 9,
    0,10,10, 0]
)
MediumUFOSprite3.grid.append(
  [ 0,12,12, 0,
    9,11,11, 9,
    9,10,10, 9,
    0, 9, 9, 0]
)
MediumUFOSprite3.grid.append(
  [ 0,11,11, 0,
    9,10,10, 9,
    9, 9, 9, 9,
    0, 9, 9, 0]
)
MediumUFOSprite3.grid.append(
  [ 0,10,10, 0,
    9, 9, 9, 9,
    9, 9, 9, 9,
    0, 9, 9, 0]
)






#(self,h,v,name,width,height,frames,currentframe,framerate,grid):
MediumUFOSprite4 = ColorAnimatedSprite(
  h = -1,
  v = -1,
  name   = "HomingMissile", 
  width  = 4, 
  height = 3, 
  frames = 6, 

  framerate    = 1,
  grid = []
)


MediumUFOSprite4.grid.append(
  [31, 0, 0,31,
    0,32,32, 0,
    0, 0, 0, 0
  ]
)

MediumUFOSprite4.grid.append(
  [31, 0, 0,31,
    0,32,32, 0,
    0, 0, 0, 0
  ]
)
MediumUFOSprite4.grid.append(
  [31, 0, 0,31,
    0,32,32, 0,
    0, 0, 0, 0
  ]
)

MediumUFOSprite4.grid.append(
  [ 0, 0, 0, 0,
   31,32,32,31,
    0, 0, 0, 0
  ]
)

MediumUFOSprite4.grid.append(
  [ 0, 0, 0, 0,
    0,32,32, 0,
   31, 0, 0,31,
   ]
)

MediumUFOSprite4.grid.append(
  [ 0, 0, 0, 0,
    0,32,32, 0,
    0,31,31, 0 
   ]
)






#(self,h,v,name,width,height,frames,currentframe,framerate,grid):
LargeUFOSprite1 = ColorAnimatedSprite(
  h = -1,
  v = -1,
  name   = "HomingMissile", 
  width  = 5, 
  height = 3, 
  frames = 6, 

  framerate    = 1,
  grid = []
)


LargeUFOSprite1.grid.append(
  [ 
    0, 1, 1, 1, 0,
    1,13,39,13, 1,
    0, 1, 1, 1, 0,
  ]
)



LargeUFOSprite1.grid.append(
  [ 
    0, 1, 1, 1, 0,
    1,39,13,13, 1,
    0, 1, 1, 1, 0,
  ]
)
LargeUFOSprite1.grid.append(
  [ 
    0, 1, 1, 1, 0,
    1,39,13,13, 1,
    0, 1, 1, 1, 0,
  ]
)
LargeUFOSprite1.grid.append(
  [ 
    0, 1, 1, 1, 0,
    1,13,39,13, 1,
    0, 1, 1, 1, 0,
  ]
)


LargeUFOSprite1.grid.append(
  [ 
    0, 1, 1, 1, 0,
    1,13,13,39, 1,
    0, 1, 1, 1, 0,
  ]
)

LargeUFOSprite1.grid.append(
  [ 
    0, 1, 1, 1, 0,
    1,13,13,39, 1,
    0, 1, 1, 1, 0,
  ]
)



#(self,h,v,name,width,height,frames,currentframe,framerate,grid):
LargeUFOSprite2 = ColorAnimatedSprite(
  h = -1,
  v = -1,
  name   = "HomingMissile", 
  width  = 5, 
  height = 5, 
  frames = 5, 

  framerate    = 1,
  grid = []
)



LargeUFOSprite2.grid.append(
  [ 
    0, 0, 1, 0, 0,
    0, 1, 1, 1, 0,
   39,13,13,13,13,
    0, 1, 1, 1, 0,
    0, 0, 1, 0, 0 
  ]
)
LargeUFOSprite2.grid.append(
  [ 
    0, 0, 1, 0, 0,
    0, 1, 1, 1, 0,
   13,39,13,13,13,
    0, 1, 1, 1, 0,
    0, 0, 1, 0, 0 
  ]
)
LargeUFOSprite2.grid.append(
  [ 
    0, 0, 1, 0, 0,
    0, 1, 1, 1, 0,
   13,13,39,13,13,
    0, 1, 1, 1, 0,
    0, 0, 1, 0, 0 
  ]
)

LargeUFOSprite2.grid.append(
  [ 
    0, 0, 1, 0, 0,
    0, 1, 1, 1, 0,
   13,13,13,39,13,
    0, 1, 1, 1, 0,
    0, 0, 1, 0, 0 
  ]
)
LargeUFOSprite2.grid.append(
  [ 
    0, 0, 1, 0, 0,
    0, 1, 1, 1, 0,
   13,13,13,13,39,
    0, 1, 1, 1, 0,
    0, 0, 1, 0, 0 
  ]
)






#(self,h,v,name,width,height,frames,currentframe,framerate,grid):
LargeUFOSprite3 = ColorAnimatedSprite(
  h = -1,
  v = -1,
  name   = "HomingMissile", 
  width  = 5, 
  height = 5, 
  frames = 4, 

  framerate    = 1,
  grid = []
)






LargeUFOSprite3.grid.append(
  [ 
    1, 1, 1, 1, 0,
    1, 2, 2, 2, 2,
    1, 2,40,40, 2,
    1, 2, 9, 9, 2,
    0, 2, 2, 2, 2 
  ]
)

LargeUFOSprite3.grid.append(
  [ 
    1, 1, 1, 1, 0,
    1, 2, 2, 2, 2,
    1, 2, 9,40, 2,
    1, 2, 9,40, 2,
    0, 2, 2, 2, 2 
  ]
)
LargeUFOSprite3.grid.append(
  [ 
    1, 1, 1, 1, 0,
    1, 2, 2, 2, 2,
    1, 2, 9, 9, 2,
    1, 2,40,40, 2,
    0, 2, 2, 2, 2 
  ]
)
LargeUFOSprite3.grid.append(
  [ 
    1, 1, 1, 1, 0,
    1, 2, 2, 2, 2,
    1, 2,40, 9, 2,
    1, 2,40, 9, 2,
    0, 2, 2, 2, 2 
  ]
)



#(self,h,v,name,width,height,frames,currentframe,framerate,grid):
LargeUFOSprite4 = ColorAnimatedSprite(
  h = -1,
  v = -1,
  name   = "HomingMissile", 
  width  = 5, 
  height = 5, 
  frames = 10, 

  framerate    = 1,
  grid = []
)


LargeUFOSprite4.grid.append(
  [ 
    0, 1,16, 1, 0,
    1, 1,41, 1, 1,
   16,41,41,41,16,
    1, 1,41, 1, 1,
    0, 1,16, 1, 0 
  ]
)
LargeUFOSprite4.grid.append(
  [ 
    0, 1,41, 1, 0,
    1, 1,41, 1, 1,
   41,41,15,41,41,
    1, 1,41, 1, 1,
    0, 1,41, 1, 0 
  ]
)
LargeUFOSprite4.grid.append(
  [ 
    0, 1,16, 1, 0,
    1, 1,15, 1, 1,
   16,15,13,15,16,
    1, 1,15, 1, 1,
    0, 1,16, 1, 0 
  ]
)
LargeUFOSprite4.grid.append(
  [ 
    0, 1,15, 1, 0,
    1, 1,13, 1, 1,
   15,13,13,13,15,
    1, 1,13, 1, 1,
    0, 1,15, 1, 0 
  ]
)
LargeUFOSprite4.grid.append(
  [ 
    0, 1,13, 1, 0,
    1, 1,13, 1, 1,
   13,13,13,13,13,
    1, 1,13, 1, 1,
    0, 1,13, 1, 0 
  ]
)
LargeUFOSprite4.grid.append(
  [ 
    0, 1,13, 1, 0,
    1, 1,13, 1, 1,
   13,13,13,13,13,
    1, 1,13, 1, 1,
    0, 1,13, 1, 0 
  ]
)
LargeUFOSprite4.grid.append(
  [ 
    0, 1,13, 1, 0,
    1, 1,13, 1, 1,
   13,13,13,13,13,
    1, 1,13, 1, 1,
    0, 1,13, 1, 0 
  ]
)
LargeUFOSprite4.grid.append(
  [ 
    0, 1,13, 1, 0,
    1, 1,13, 1, 1,
   13,13,41,13,13,
    1, 1,13, 1, 1,
    0, 1,13, 1, 0 
  ]
)

LargeUFOSprite4.grid.append(
  [ 
    0, 1,13, 1, 0,
    1, 1,13, 1, 1,
   13,13,41,13,13,
    1, 1,13, 1, 1,
    0, 1,13, 1, 0 
  ]
)

LargeUFOSprite4.grid.append(
  [ 
    0, 1,13, 1, 0,
    1, 1,16, 1, 1,
   13,16,41,16,13,
    1, 1,16, 1, 1,
    0, 1,13, 1, 0 
  ]
)




#(self,h,v,name,width,height,frames,currentframe,framerate,grid):
LargeUFOSprite5 = ColorAnimatedSprite(
  h = -4,
  v = -1,
  name   = "HomingMissile", 
  width  = 8, 
  height = 5, 
  frames = 4, 

  framerate    = 1,
  grid = []
)


LargeUFOSprite5.grid.append(
  [ 
    0, 2, 0, 0, 0, 0, 2, 0,
    2, 0, 0, 2, 2, 0, 0, 2,
    2, 1, 1,39,39, 1, 1, 2,
    2, 0, 0, 2, 2, 0, 0, 2,
    0, 2, 0, 0, 0, 0, 2, 0
  ]
)
LargeUFOSprite5.grid.append(
  [ 
    0, 2, 0, 0, 0, 0, 2, 0,
    2, 0, 0, 2, 2, 0, 0, 2,
    2, 1, 1,39,39, 1, 1, 2,
    2, 0, 0, 2, 2, 0, 0, 2,
    0, 2, 0, 0, 0, 0, 2, 0
  ]
)

LargeUFOSprite5.grid.append(
  [ 
    0, 2, 0, 0, 0, 0, 2, 0,
    2, 0, 0, 2, 2, 0, 0, 2,
    2, 1, 1, 5, 5, 1, 1, 2,
    2, 0, 0, 2, 2, 0, 0, 2,
    0, 2, 0, 0, 0, 0, 2, 0
  ]
)
LargeUFOSprite5.grid.append(
  [ 
    0, 2, 0, 0, 0, 0, 2, 0,
    2, 0, 0, 2, 2, 0, 0, 2,
    2, 1, 1, 5, 5, 1, 1, 2,
    2, 0, 0, 2, 2, 0, 0, 2,
    0, 2, 0, 0, 0, 0, 2, 0
  ]
)




#(self,h,v,name,width,height,frames,currentframe,framerate,grid):
LargeUFOSprite6 = ColorAnimatedSprite(
  h = -4,
  v = -1,
  name   = "HomingMissile", 
  width  = 8, 
  height = 4, 
  frames = 6, 

  framerate    = 1,
  grid = []
)


LargeUFOSprite6.grid.append(
  [ 
    0, 0, 0, 9, 9, 0, 0, 0,
    0, 1, 1, 1, 1, 1, 1, 0,
   39, 5, 5,39, 5, 5,39, 5,
    0, 1, 1, 1, 1, 1, 1, 0

  ]
)

LargeUFOSprite6.grid.append(
  [ 
    0, 0, 0, 9, 9, 0, 0, 0,
    0, 1, 1, 1, 1, 1, 1, 0,
   39, 5, 5,39, 5, 5,39, 5,
    0, 1, 1, 1, 1, 1, 1, 0

  ]
)


LargeUFOSprite6.grid.append(
  [ 
    0, 0, 0,40,40, 0, 0, 0,
    0, 1, 1, 1, 1, 1, 1, 0,
    5,39, 5, 5,39, 5, 5,39,
    0, 1, 1, 1, 1, 1, 1, 0

  ]
)

LargeUFOSprite6.grid.append(
  [ 
    0, 0, 0,40,40, 0, 0, 0,
    0, 1, 1, 1, 1, 1, 1, 0,
    5,39, 5, 5,39, 5, 5,39,
    0, 1, 1, 1, 1, 1, 1, 0

  ]
)

LargeUFOSprite6.grid.append(
  [ 
    0, 0, 0, 9, 9, 0, 0, 0,
    0, 1, 1, 1, 1, 1, 1, 0,
    5, 5,39, 5, 5,39, 5, 5,
    0, 1, 1, 1, 1, 1, 1, 0

  ]
)

LargeUFOSprite6.grid.append(
  [ 
    0, 0, 0, 9, 9, 0, 0, 0,
    0, 1, 1, 1, 1, 1, 1, 0,
    5, 5,39, 5, 5,39, 5, 5,
    0, 1, 1, 1, 1, 1, 1, 0

  ]
)



#(self,h,v,name,width,height,frames,currentframe,framerate,grid):
WideUFOSprite1 = ColorAnimatedSprite(
  h = -1,
  v = -1,
  name   = "HomingMissile", 
  width  = 8, 
  height = 1, 
  frames =18, 

  framerate    = 1,
  grid = []
)

WideUFOSprite1.grid.append(
  [39, 0, 0, 0, 0, 0, 0, 0 ]
)

WideUFOSprite1.grid.append(
  [ 5,39, 0, 0, 0, 0, 0, 0 ]
)

WideUFOSprite1.grid.append(
  [ 5, 5,39, 0, 0, 0, 0, 0 ]
)
WideUFOSprite1.grid.append(
  [ 0, 5, 5,39, 0, 0, 0, 0 ]
)
WideUFOSprite1.grid.append(
  [ 0, 0, 5, 5,39, 0, 0, 0 ]
)
WideUFOSprite1.grid.append(
  [ 0, 0, 0, 5, 5,39, 0, 0 ]
)
WideUFOSprite1.grid.append(
  [ 0, 0, 0, 0, 5, 5,39, 0 ]
)
WideUFOSprite1.grid.append(
  [ 0, 0, 0, 0, 0, 5, 5,39 ]
)
WideUFOSprite1.grid.append(
  [ 0, 0, 0, 0, 0, 0, 5,39 ]
)
WideUFOSprite1.grid.append(
  [ 0, 0, 0, 0, 0, 0, 0,39 ]
)
WideUFOSprite1.grid.append(
  [ 0, 0, 0, 0, 0, 0,39, 5 ]
)
WideUFOSprite1.grid.append(
  [ 0, 0, 0, 0, 0,39, 5, 5 ]
)
WideUFOSprite1.grid.append(
  [ 0, 0, 0, 0,39, 5, 5, 0 ]
)
WideUFOSprite1.grid.append(
  [ 0, 0, 0,39, 5, 5, 0, 0 ]
)
WideUFOSprite1.grid.append(
  [ 0, 0,39, 5, 5, 0, 0, 0 ]
)
WideUFOSprite1.grid.append(
  [ 0,39, 5, 5, 0, 0, 0, 0 ]
)
WideUFOSprite1.grid.append(
  [39, 5, 5, 0, 0, 0, 0, 0 ]
)
WideUFOSprite1.grid.append(
  [39, 5, 0, 0, 0, 0, 0, 0 ]
)



ShipSprites = []
ShipSprites.append(SmallUFOSprite)
ShipSprites.append(SmallUFOSprite2)
ShipSprites.append(SmallUFOSprite3)
ShipSprites.append(SmallUFOSprite4)
ShipSprites.append(SmallUFOSprite5)
ShipSprites.append(SmallUFOSprite6)
ShipSprites.append(SmallUFOSprite7)
ShipSprites.append(SatelliteSprite)
ShipSprites.append(SatelliteSprite2)
ShipSprites.append(SatelliteSprite3)
ShipSprites.append(SatelliteSprite4)
ShipSprites.append(SatelliteSprite5)
ShipSprites.append(SatelliteSprite6)
ShipSprites.append(SatelliteSprite7)
ShipSprites.append(MediumUFOSprite)
ShipSprites.append(MediumUFOSprite2)
ShipSprites.append(MediumUFOSprite3)
ShipSprites.append(MediumUFOSprite4)
ShipSprites.append(LargeUFOSprite1)
ShipSprites.append(LargeUFOSprite2)
ShipSprites.append(LargeUFOSprite3)
ShipSprites.append(LargeUFOSprite4)
ShipSprites.append(LargeUFOSprite5)
ShipSprites.append(LargeUFOSprite6)
ShipSprites.append(WideUFOSprite1)
ShipSprites.append(SpaceInvader)
ShipSprites.append(SmallInvader)
ShipSprites.append(TinyInvader)




PlayerShipExplosion = ColorAnimatedSprite(
  h=0, v=0, name="Explosion", width=5, height=5, 
  frames=14,
  framerate=2,grid=[]
)
PlayerShipExplosion.grid.append(
  [0,0,0,0,0,
   0,0,0,0,0,
   0,0,4,0,0,
   0,0,0,0,0,
   0,0,0,0,0
   ]
)

PlayerShipExplosion.grid.append(
   [0,0,0,0,0,
    0, 0, 4, 0,0,
    0, 4,18, 4,0,
    0, 0, 4, 0,0,
    0,0,0,0,0
   ]
)
  
PlayerShipExplosion.grid.append(
   [ 0, 0, 4, 0, 0,
     0,18,18,18, 0,
     4,18,19,18, 4,
     0,18,18,18, 0,
     0, 0, 4, 0,0
   ]
)
PlayerShipExplosion.grid.append(
   [ 0,18,18,18, 0,
    18,19,19,19,18,
    18,18,20,19,18,
    18,19,19,19,18,
     0,18,18,18, 0
   ]
)
PlayerShipExplosion.grid.append(
   [ 0,19,19,19, 0,
    19,20,20,20,19,
    19,20,20,20,19,
    19,20,20,20,19,
     0,19,19,19, 0
   ]
)
PlayerShipExplosion.grid.append(
   [ 0,20,20,20, 0,
    20,20,20,20,20,
    20,20,20,20,20,
    20,20,20,20,20,
     0,20,20,20, 0
   ]


)
PlayerShipExplosion.grid.append(
   [00,20,20,20,00,
    20,20,20,20,20,
    20,20, 8,20,20,
    20,20,20,20,20,
    00,20,20,20,00
   ]
)
PlayerShipExplosion.grid.append(
   [ 0,20,20,20, 0,
    20,20, 8,20,20,
    20, 8, 7, 8,20,
    20,20, 8,20,20,
     0,20,20,20, 0
   ]
)  

PlayerShipExplosion.grid.append(
   [ 0,20, 8,20, 0,
    20, 8, 7, 8,20,
     8, 7, 6, 7, 8,
    20, 8, 7, 8,20,
     0,20, 8,20, 0
   ]
)
PlayerShipExplosion.grid.append(
   [ 0, 8, 7, 8, 0,
     8, 7, 6, 7, 8,
     7, 6, 5, 6, 7,
     8, 7, 6, 7, 8,
     0, 8, 7, 8, 0
   ]
)
PlayerShipExplosion.grid.append(
   [ 0, 7, 6, 7, 0,
     7, 6, 0, 6, 7,
     6, 5, 0, 5, 6,
     7, 6, 0, 6, 7,
     0, 7, 6, 7, 0
   ]
)
PlayerShipExplosion.grid.append(
   [ 0, 6, 5, 6, 0,
     6, 5, 0, 5, 6,
     5, 0, 0, 0, 5,
     6, 5, 0, 5, 6,
     0, 6, 5, 6, 0
   ]
)
PlayerShipExplosion.grid.append(
   [ 0, 5, 0, 5, 0,
     5, 0, 0, 0, 5,
     0, 0, 0, 0, 0,
     5, 0, 0, 0, 5,
     0, 5, 0, 5, 0
   ]
)  

PlayerShipExplosion.grid.append(
   [ 0, 0, 0, 0, 0,
     0, 0, 0, 0, 0,
     0, 0, 0, 0, 0,
     0, 0, 0, 0, 0,
     0, 0, 0, 0, 0
   ]
)  




BomberShipExplosion = ColorAnimatedSprite(
  h = 0, 
  v = 0,
  name         = "Explosion", 
  width        = 5, 
  height       = 5, 
  frames       = 9,
  framerate    = 15, 
  grid         = []
)
BomberShipExplosion.grid.append(
   [ 0, 0, 0, 0, 0,
     0, 0,45, 0, 0,
     0,45,45,45, 0,
     0, 0,45, 0, 0,
     0, 0, 0, 0, 0
   ]
)

BomberShipExplosion.grid.append(
   [ 0, 0,45, 0, 0,
     0,45,45,45, 0,
    45,45,45,45,45,
     0,45,45,45, 0,
     0, 0,45, 0, 0
   ]
)

BomberShipExplosion.grid.append(
   [ 0, 0,42, 0, 0,
     0,45,42,45, 0,
    42,42,42,42,42,
     0,45,42,45, 0,
     0, 0,42, 0, 0
   ]
)


BomberShipExplosion.grid.append(
   [ 0, 0,42, 0, 0,
     0, 2,20, 2, 0,
    42,20,20,20,42,
     0, 2,20, 2, 0,
     0, 0,42, 0, 0
   ]
)


BomberShipExplosion.grid.append(
   [ 0, 0,20, 0, 0,
     0, 1,20, 1, 0,
    20,20,39,20,20,
     0, 1,20, 1, 0,
     0, 0,20, 0, 0
   ]
)

BomberShipExplosion.grid.append(
   [ 0, 0,39, 0, 0,
     0, 1,39, 1, 0,
    39,39,39,39,20,
     0, 1,39, 1, 0,
     0, 0,39, 0, 0
   ]
)

BomberShipExplosion.grid.append(
   [ 0, 0,39, 0, 0,
     0, 1, 8, 1, 0,
    39, 8, 6, 8,39,
     0, 1, 8, 1, 0,
     0, 0,39, 0, 0
   ]
)


BomberShipExplosion.grid.append(
   [ 0, 0, 0, 0, 0,
     0, 0, 5, 0, 0,
     0, 5, 5, 5, 0,
     0, 0, 5, 0, 0,
     0, 0, 0, 0, 0
   ]
)

BomberShipExplosion.grid.append(
   [ 0, 0, 0, 0, 0,
     0, 0, 0, 0, 0,
     0, 0, 0, 0, 0,
     0, 0, 0, 0, 0,
     0, 0, 0, 0, 0
   ]
)





SmallExplosion = ColorAnimatedSprite(
  h=-1, v=-1, name="Explosion", width=3, height=3,
  frames=7,
  framerate = 10,grid=[])
SmallExplosion.grid.append(
  [
   0, 0, 0,
   0,29, 0,
   0, 0, 0,
   
   ]
)

SmallExplosion.grid.append(
   [ 
     0,29, 0,
    29,30,29,
     0,29, 0, 
   
   ]
)
  
SmallExplosion.grid.append(
   [ 
      0,30, 0,
     30,31,30,
      0,30, 0,
     
   ]
)
SmallExplosion.grid.append(
   [
     0,31, 0,
    31,32,31,
     0,31, 0,
    
   ]
)

SmallExplosion.grid.append(
   [
     0,32, 0,
    32, 8,32,
     0,32, 0
   ]
)
   

SmallExplosion.grid.append(
   [
     0,20, 0,
    20, 0,20,
     0,20, 0,
    
   ]
)

   
SmallExplosion.grid.append(
   [
     0, 0, 0,
     0, 0, 0,
     0, 0, 0,
    
   ]
)


  


AsteroidExplosion = ColorAnimatedSprite(
  h      = 0 , 
  v      = 0, 
  name   = 'Asteroid',
  width  = 3, 
  height = 3,
  frames = 5,
  framerate    = 10,
  grid=[]
)

AsteroidExplosion.grid.append(
  [0, 0, 0,
   0,45, 0,
   0, 0, 0
  ]
)

AsteroidExplosion.grid.append(
  [0,45, 0,
  45,45,45,
   0,45, 0
  ]
)
AsteroidExplosion.grid.append(
  [0,45, 0,
  45, 8,45,
   0,45, 0
  ]
)
AsteroidExplosion.grid.append(
  [0, 8, 0,
   8, 0, 8,
   0, 8, 0
  ]
)
AsteroidExplosion.grid.append(
  [0, 0, 0,
   0, 0, 0,
   0, 0, 0
  ]
)



AsteroidExplosion2 = ColorAnimatedSprite(
  h      = 0 , 
  v      = 0, 
  name   = 'Asteroid',
  width  = 3, 
  height = 1,
  frames = 7,
  framerate    = 50,
  grid=[]
)

AsteroidExplosion2.grid.append(
  [
    0,45, 0
  ]
)

AsteroidExplosion2.grid.append(
  [
   45,20,45
  ]
)

AsteroidExplosion2.grid.append(
  [
   20,20,20
  ]
)

AsteroidExplosion2.grid.append(
  [
    8, 8, 8
  ]
)

AsteroidExplosion2.grid.append(
  [
    8, 6, 8
  ]
)

AsteroidExplosion2.grid.append(
  [
    6, 5, 6
  ]
)

AsteroidExplosion2.grid.append(
  [
    5, 5, 5
  ]
)




BigGroundExplosion = ColorAnimatedSprite(
  h            = -1, #this is important, it is used to indicate if the explosion is brand new.  I think.
  v            = -1,  
  name         = "Explosion", 
  width        = 9, 
  height       = 3, 
  frames       = 6, 
  framerate    = 150,
  grid         = []
)


BigGroundExplosion.grid.append(
  [
   0, 0, 0, 0, 0, 0, 0, 0, 0,
   0, 0, 0, 0, 4, 0, 0, 0, 0,
   0, 0, 0, 0, 0, 0, 0, 0, 0
   ]
)

BigGroundExplosion.grid.append(
  [
   0, 0, 0, 0, 0, 0, 0, 0, 0,
   0, 0, 0, 4, 4, 4, 0, 0, 0,
   0, 0, 0, 0, 0, 0, 0, 0, 0
   ]
)
BigGroundExplosion.grid.append(
  [
   0, 0, 0, 0, 4, 0, 0, 0, 0,
   0, 0, 4, 4, 4, 4, 4, 0, 0,
   0, 0, 0, 0, 4, 0, 0, 0, 0
   ]
)
BigGroundExplosion.grid.append(
  [
   0, 0, 0, 0, 4, 0, 0, 0, 0,
   0, 4, 4, 4, 4, 4, 4, 4, 0,
   0, 0, 0, 0, 4, 0, 0, 0, 0
   ]
)
BigGroundExplosion.grid.append(
  [
   0, 0, 0, 0, 4, 0, 0, 0, 0,
   4, 4, 4, 0, 0, 0, 4, 4, 4,
   0, 0, 0, 0, 4, 0, 0, 0, 0
   ]
)
BigGroundExplosion.grid.append(
  [
   0, 0, 0, 0, 0, 0, 0, 0, 0,
   4, 0, 0, 0, 0, 0, 0, 0, 4,
   0, 0, 0, 0, 0, 0, 0, 0, 0
   ]
)
BigGroundExplosion.grid.append(
  [
   0, 0, 0, 0, 0, 0, 0, 0, 0,
   0, 0, 0, 0, 0, 0, 0, 0, 0,
   0, 0, 0, 0, 0, 0, 0, 0, 0
   ]
)





Defender = ColorAnimatedSprite(
  h=0, 
  v=0, 
  name="Defender", 
  width  = 7, 
  height = 4, 
  framerate=1,
  grid=[]  )

                 

DefenderMap = TextMap(
  h      = 1,
  v      = 1,
  width  = Defender.width, 
  height = Defender.height
  )


DefenderMap.ColorList = {
  ' ' : 0,
  '-' : 29, #dark pink
  '.' : 2, 
  'o' : 1, 
  'O' : 32,
  '#' : 5,
  '@' : 6,
  '6' : 7,
  '7' : 8,
  

}


DefenderMap.map= (
  #0.........1.........2.........3.........4....
  "       ",
  "  -    ",
  " #...o ",
  "       "
  
  
  )


DefenderMap.CopyMapToColorSprite(TheSprite=Defender)



DefenderMap.map= (
  #0.........1.........2.........3.........4....
  "       ",
  "  -    ",
  " @...o ",
  "       "
  
  
  )


DefenderMap.CopyMapToColorSprite(TheSprite=Defender)





DefenderMap.map= (
  #0.........1.........2.........3.........4....
  "       ",
  "  -    ",
  " 6...o ",
  "       "
  
  
  )


DefenderMap.CopyMapToColorSprite(TheSprite=Defender)


DefenderMap.map= (
  #0.........1.........2.........3.........4....
  "       ",
  "  -    ",
  " 7...o ",
  "       "
  
  
  )


DefenderMap.CopyMapToColorSprite(TheSprite=Defender)








DefenderReverse = ColorAnimatedSprite(
  h=0, 
  v=0, 
  name="DefenderReverse", 
  width  = 7, 
  height = 4, 
  framerate=1,
  grid=[]  )

                 

DefenderReverseMap = TextMap(
  h      = 1,
  v      = 1,
  width  = DefenderReverse.width, 
  height = DefenderReverse.height
  )


DefenderReverseMap.ColorList = {
  ' ' : 0,
  '-' : 29, #dark pink
  '.' : 2, 
  'o' : 1, 
  'O' : 32,
  '#' : 5,
  '@' : 6,
  '6' : 7,
  '7' : 8,
  

}


DefenderReverseMap.map= (
  #0.........1.........2.........3.........4....
  "       ",
  "    -  ",
  " o...# ",
  "       "
  
  
  )


DefenderReverseMap.CopyMapToColorSprite(TheSprite=DefenderReverse)



DefenderReverseMap.map= (
  #0.........1.........2.........3.........4....
  "       ",
  "    -  ",
  " o...@ ",
  "       "
  
  
  )


DefenderReverseMap.CopyMapToColorSprite(TheSprite=DefenderReverse)





DefenderReverseMap.map= (
  #0.........1.........2.........3.........4....
  "       ",
  "    -  ",
  " o...6 ",
  "       "
  
  
  )


DefenderReverseMap.CopyMapToColorSprite(TheSprite=DefenderReverse)


DefenderReverseMap.map= (
  #0.........1.........2.........3.........4....
  "       ",
  "    -  ",
  " o...7 ",
  "       "
  
  
  )


DefenderReverseMap.CopyMapToColorSprite(TheSprite=DefenderReverse)







BombSprite = ColorAnimatedSprite(
  h=0, 
  v=0, 
  name="Bomb", 
  width  = 1, 
  height = 1, 
  framerate=5,
  grid=[]  )

                 

BombMap = TextMap(
  h      = 1,
  v      = 1,
  width  = BombSprite.width, 
  height = BombSprite.height
  )


BombMap.ColorList = {
  ' ' : 0,
  '-' : 29, #dark pink
  '.' : 4,  #bright white
  'o' : 1, 
  'O' : 32,
  '#' : 5,
  '@' : 6,
  '6' : 7,
  '7' : 8,  #Bright Red
  

}


BombMap.map= (
  #0.........1.........2.........3.........4....
  "."
  )
BombMap.CopyMapToColorSprite(TheSprite=BombSprite)


BombMap.map= (
  #0.........1.........2.........3.........4....
  "7"
  )
BombMap.CopyMapToColorSprite(TheSprite=BombSprite)










HumanSprite = ColorAnimatedSprite(
  h=0, 
  v=0, 
  name="Human", 
  width  = 2, 
  height = 2, 
  framerate=random.randint(2,12),
  grid=[]  )

                 

HumanMap = TextMap(
  h      = 1,
  v      = 1,
  width  = HumanSprite.width, 
  height = HumanSprite.height
  )


HumanMap.ColorList = {
  ' ' : 0,
  '-' : 30, #pink
  '.' : 17, #orange 
  'o' : 18, 
  'O' : 19,
  '#' : 5,
  '@' : 6,
  '6' : 7,
  '7' : 8,
  

}


HumanMap.map= (
  #0.........1.........2.........3.........4....
  "- ",
  ". ",
  )
HumanMap.CopyMapToColorSprite(TheSprite=HumanSprite)

HumanMap.map= (
  #0.........1.........2.........3.........4....
  "- ",
  " .",
  )
HumanMap.CopyMapToColorSprite(TheSprite=HumanSprite)

HumanMap.map= (
  #0.........1.........2.........3.........4....
  " -",
  " .",
  )
HumanMap.CopyMapToColorSprite(TheSprite=HumanSprite)

HumanMap.map= (
  #0.........1.........2.........3.........4....
  " -",
  ". ",
  )
HumanMap.CopyMapToColorSprite(TheSprite=HumanSprite)















#------------------------------------------------------------------------------
# FUNCTIONS                                                                  --
#                                                                            --
#  These functions were created before classes were introduced.              --
#------------------------------------------------------------------------------



def PointTowardsObject8Way(SourceH,SourceV,TargetH,TargetV):

  #   8 1 2
  #   7 . 3
  #   6 5 4

  #d = GetDistanceBetweenDots(SourceH, SourceV, TargetH, TargetV):
  
  #source is upper left of target
  if (SourceH < TargetH and SourceV < TargetV):
    direction = 4

  #source is directly above target
  elif (SourceH == TargetH and SourceV < TargetV):
    direction = 5

  #source is upper right of target
  elif (SourceH > TargetH and SourceV < TargetV):
    direction = 6

  #source is directly right of target
  elif (SourceH > TargetH and SourceV == TargetV):
    direction = 7

  #source is lower right of target
  elif (SourceH > TargetH and SourceV > TargetV):
    direction = 8

  #source is directly below target
  elif (SourceH == TargetH and SourceV > TargetV):
    direction = 1
    
  #source is lower left of target
  elif (SourceH < TargetH and SourceV > TargetV):
    direction = 2

  #source is directly left of target
  elif (SourceH < TargetH and SourceV == TargetV):
    direction = 3

  else: direction = random.randint(1,8)

  return direction;


def PointAwayFromObject8Way(SourceH,SourceV,TargetH,TargetV):

  #   8 1 2
  #   7 . 3
  #   6 5 4

  #d = GetDistanceBetweenDots(SourceH, SourceV, TargetH, TargetV):
  
  #source is upper left of target
  if (SourceH < TargetH and SourceV < TargetV):
    direction = 8

  #source is directly above target
  elif (SourceH == TargetH and SourceV < TargetV):
    direction = 1

  #source is upper right of target
  elif (SourceH > TargetH and SourceV < TargetV):
    direction = 2

  #source is directly right of target
  elif (SourceH > TargetH and SourceV == TargetV):
    direction = 3

  #source is lower right of target
  elif (SourceH > TargetH and SourceV > TargetV):
    direction = 4

  #source is directly below target
  elif (SourceH == TargetH and SourceV > TargetV):
    direction = 5
    
  #source is lower left of target
  elif (SourceH < TargetH and SourceV > TargetV):
    direction = 6

  #source is directly left of target
  elif (SourceH < TargetH and SourceV == TargetV):
    direction = 7

  else: direction = random.randint(1,8)

  return direction;






  
def ScrollSprite2(Sprite,h,v,direction,moves,r,g,b,delay):
  x = 0
  #modifier is used to increment or decrement the location
  if direction == "right" or direction == "down":
    modifier = 1
  else: 
    modifier = -1
  
  if direction == "left" or direction == "right":
    for count in range (0,moves):
      h = h + (modifier)
      #erase old sprite
      if count >= 1:
        DisplaySprite(Sprite,Sprite.width,Sprite.height,h-(modifier),v,0,0,0)
      #draw new sprite
      DisplaySprite(Sprite,Sprite.width,Sprite.height,h,v,r,g,b)
      #unicorn.show()
      #SendBufferPacket(RemoteDisplay,HatHeight,HatWidth)
      time.sleep(delay)
  
  return;

 
  

def ScrollSprite(Sprite,width,height,Direction,startH,startV,stopH,stopV,r,g,b,delay):
  x = 0
  h = startH
  v = startV
  movesH = abs(startH - stopH)
  movesV = abs(startV - stopV)

  #modifier is used to increment or decrement the location
  if Direction == "right" or Direction == "down":
    modifier = 1
  else: 
    modifier = -1
  
  if Direction == "left" or Direction == "right":
    for count in range (0,movesH):
      #print ("StartH StartV StopH StopV X",startH,startV,stopH,stopV,x)
      h = h + (modifier)
      #erase old sprite
      if count >= 1:
        DisplaySprite(Sprite,width,height,h-(modifier),v,0,0,0)
      #draw new sprite
      DisplaySprite(Sprite,width,height,h,v,r,g,b)
      #unicorn.show()
      #SendBufferPacket(RemoteDisplay,HatHeight,HatWidth)
      time.sleep(delay)
  
  return;
    
def DisplaySprite(Sprite,width,height,h,v,r,g,b):
  x = 0,
  y = 0
  
  for count in range (0,(width * height)):
    y,x = divmod(count,width)
    #print("Count:",count,"xy",x,y)
    if Sprite[count] == 1:
      if (CheckBoundary(x+h,y+v) == 0):
        TheMatrix.SetPixel(x+h,y+v,r,g,b)
  return;    



def TrimSprite(Sprite1):
  height       = Sprite1.height
  width        = Sprite1.width
  newwidth     = 0
  elements     = height * width
  Empty        = 1
  Skipped      = 0
  EmptyColumns = []
  EmptyCount   = 0
  BufferX      = 0
  BufferColumn = [(0) for i in range(height)]
  
  i = 0
  x = 0
  y = 0

  
  for x in range (0,width):
    
    #Find empty columns, add them to a list
    Empty = 1  
    for y in range (0,height):
      i = x + (y * width)
      
      BufferColumn[y] = Sprite1.grid[i]
      if (Sprite1.grid[i] != 0):
        Empty = 0
    
    if (Empty == 0):
      newwidth =  newwidth + 1
    
    elif (Empty == 1):
      #print ("Found empty column: ",x)
      EmptyColumns.append(x)
      EmptyCount = EmptyCount +1

      
  BufferSprite = Sprite(
    newwidth,
    height,
    Sprite1.r,
    Sprite1.g,
    Sprite1.b,
    [0]*(newwidth*height)
    )
      
  #Now that we identified the empty columns, copy data and skip those columns
  for x in range (0,width):
    Skipped = 0
    
    for y in range (0,height):
      i = x + (y * width)
      b = BufferX + (y * newwidth)
      if (x in EmptyColumns):
        Skipped = 1
      else:
        BufferSprite.grid[b] = Sprite1.grid[i]
    
    
    #advance our Buffer column counter only if we skipped a column
    if (Skipped == 0):
      BufferX = BufferX + 1
    
    
  
  BufferSprite.width = newwidth
  
  
  
  #print (BufferSprite.grid)
  return BufferSprite



def LeftTrimSprite(Sprite1,Columns):
  height       = Sprite1.height
  width        = Sprite1.width
  newwidth     = 0
  elements     = height * width
  Empty        = 1
  Skipped      = 0
  EmptyColumns = []
  EmptyCount   = 0
  BufferX      = 0
  BufferColumn = [(0) for i in range(height)]
  
  i = 0
  x = 0
  y = 0

  
  for x in range (0,width):
    
    #Find empty columns, add them to a list
    Empty = 1  
    for y in range (0,height):
      i = x + (y * width)
      
      BufferColumn[y] = Sprite1.grid[i]
      if (Sprite1.grid[i] != 0):
        Empty = 0
    
    if (Empty == 0 or EmptyCount > Columns):
      newwidth =  newwidth + 1
    
    elif (Empty == 1):
      #print ("Found empty column: ",x)
      EmptyColumns.append(x)
      EmptyCount = EmptyCount +1

      
  BufferSprite = Sprite(
    newwidth,
    height,
    Sprite1.r,
    Sprite1.g,
    Sprite1.b,
    [0]*(newwidth*height)
    )
      
  #Now that we identified the empty columns, copy data and skip those columns
  for x in range (0,width):
    Skipped = 0
    
    for y in range (0,height):
      i = x + (y * width)
      b = BufferX + (y * newwidth)
      if (x in EmptyColumns):
        Skipped = 1
      else:
        BufferSprite.grid[b] = Sprite1.grid[i]
    
    
    #advance our Buffer column counter only if we skipped a column
    if (Skipped == 0):
      BufferX = BufferX + 1
    
    
  
  BufferSprite.width = newwidth
  
  
  
  #print (BufferSprite.grid)
  return BufferSprite
    
    
    
    

  
  
def CreateShortWordSprite(ShortWord):   

  ShortWord = ShortWord.upper()
  TheBanner = CreateBannerSprite(ShortWord)
      

  TheBanner.r = SDMedRedR
  TheBanner.g = SDMedRedG
  TheBanner.b = SDMedRedB
  
  
  #add variables to the object (python allows this, very cool!)
  TheBanner.h = (HatWidth - TheBanner.width) / 2
  TheBanner.v = -4
  TheBanner.rgb = (SDMedGreenR,SDMedGreenG,SDMedGreenB)

  #used for displaying clock
  TheBanner.StartTime = time.time()

  #used for scrolling clock
  TheBanner.PauseStartTime = time.time()
  TheBanner.IsScrolling     = 0
  TheBanner.Delay           = 2
  TheBanner.PausePositionV  = 1
  TheBanner.PauseTimerOn    = 0
  
  TheBanner.on = 1
  TheBanner.DirectionIncrement = 1

  
  return TheBanner 



def ShowShortMessage(RaceWorld,PlayerCar,ShortMessage):
  moves = 1
  ShortMessageSprite    = CreateShortMessageSprite(ShortMessage)
  ShortMessageSprite.on = 1
  while (ShortMessageSprite.on == 1):
    RaceWorld.DisplayWindowWithSprite(PlayerCar.h-7,PlayerCar.v-7,ShortMessageSprite)
    MoveMessageSprite(moves,ShortMessageSprite)
    moves = moves + 1
    #print ("Message On")
    
  ShortMessageSprite.on = 0












def DrawDigit(Digit,h,v,r,g,b):
  #print ("Digit:",Digit)
  x = h
  y = v,
  width = 3
  height = 5  

  if Digit == 0:
    Sprite = ([1,1,1, 
               1,0,1,
               1,0,1,
               1,0,1,
               1,1,1])

  elif Digit == 1:
    Sprite = ([0,0,1, 
               0,0,1,
               0,0,1,
               0,0,1,
               0,0,1])

  elif Digit == 2:
    Sprite = ([1,1,1, 
               0,0,1,
               0,1,0,
               1,0,0,
               1,1,1])

  elif Digit == 3:
    Sprite = ([1,1,1, 
               0,0,1,
               0,1,1,
               0,0,1,
               1,1,1])

  elif Digit == 4:
    Sprite = ([1,0,1, 
               1,0,1,
               1,1,1,
               0,0,1,
               0,0,1])
               
  
  elif Digit == 5:
    Sprite = ([1,1,1, 
               1,0,0,
               1,1,1,
               0,0,1,
               1,1,1])

  elif Digit == 6:
    Sprite = ([1,1,1, 
               1,0,0,
               1,1,1,
               1,0,1,
               1,1,1])

  elif Digit == 7:
    Sprite = ([1,1,1, 
               0,0,1,
               0,1,0,
               1,0,0,
               1,0,0])
  
  elif Digit == 8:
    Sprite = ([1,1,1, 
               1,0,1,
               1,1,1,
               1,0,1,
               1,1,1])
  
  elif Digit == 9:
    Sprite = ([1,1,1, 
               1,0,1,
               1,1,1,
               0,0,1,
               0,0,1])
  

  DisplaySprite(Sprite,width,height,h,v,r,g,b)
  #unicorn.show()
  #SendBufferPacket(RemoteDisplay,HatHeight,HatWidth)
  return;  





   

def CheckBoundaries(h,v,Direction):
  if v < 0:
    v = 0
    Direction = TurnRight(Direction)
  elif v > HatHeight-1:
    v = HatHeight-1
    Direction = TurnRight(Direction)
  elif h < 0:
    h = 0
    Direction = TurnRight(Direction)
  elif h > HatWidth-1:
    h = HatWidth-1
    Direction = TurnRight(Direction)
  return h,v,Direction

  
  
def CheckBoundary(h,v):
  BoundaryHit = 0
  if v < 0 or v > HatHeight-1 or h < 0 or h > HatWidth-1:
    BoundaryHit = 1
  return BoundaryHit;





  






def ShowDigitalClock(h,v,duration):
  #Buffer = copy.deepcopy(unicorn.get_pixels())
  ClockSprite = CreateClockSprite(12)
  ClockSprite.r = SDLowRedR
  ClockSprite.g = SDLowRedG
  ClockSprite.b = SDLowRedB
  ClockSpriteBackground.DisplayIncludeBlack(h-2,v-1)
  ClockSprite.Display(h,v)
  
  #unicorn.show()
  #SendBufferPacket(RemoteDisplay,HatHeight,HatWidth)
  time.sleep(duration)
  #setpixels(Buffer)
  return ClockSprite;



def random_message(MessageFile):
  lines = open(MessageFile).read().splitlines()
  return random.choice(lines)

    


def SaveConfigData():  
  
   
  print (" ")
  print ("--Save Config Data--")
  #we save the time to file as 5 minutes in future, which allows us to unplug the device temporarily
  #the time might be off, but it might be good enough
  
  AdjustedTime = (datetime.now() + timedelta(minutes=5)).strftime('%k:%M:%S')

  
  if (os.path.exists(ConfigFileName)):
    print ("Config file (",ConfigFileName,"): already exists")
    ConfigFile = SafeConfigParser()
    ConfigFile.read(ConfigFileName)
  else:
    print ("Config file not found.  Creating new one.")
    ConfigFile = SafeConfigParser()
    ConfigFile.read(ConfigFileName)
    ConfigFile.add_section('scores')
    #ConfigFile.add_section('pacdot')
    #ConfigFile.add_section('crypto')

    
  #print ("Time to save: ",AdjustedTime)
  #print ("DotInvaders high score:   " ,DotInvadersHighScore)
  #print ("DotInvaders games played: " ,DotInvadersGamesPlayed)
  #print ("Outbreak high score:      " ,OutbreakHighScore)
  #print ("Outbreak games played:    " ,OutbreakGamesPlayed)
  #print ("SpaceDot high score:      " ,SpaceDotHighScore)
  #print ("SpaceDot games played:    " ,SpaceDotGamesPlayed)

  #ConfigFile.set('main',   'CurrentTime',       AdjustedTime)
  ConfigFile.set('scores',   'DotInvadersHighScore',   str(DotInvadersHighScore))
  ConfigFile.set('scores',   'DotInvadersGamesPlayed', str(DotInvadersGamesPlayed))
  ConfigFile.set('scores',   'OutbreakHighScore',   str(OutbreakHighScore))
  ConfigFile.set('scores',   'OutbreakGamesPlayed', str(OutbreakGamesPlayed))
  ConfigFile.set('scores',   'SpaceDotHighScore',   str(SpaceDotHighScore))
  ConfigFile.set('scores',   'SpaceDotGamesPlayed', str(SpaceDotGamesPlayed))
  ConfigFile.set('scores',   'DefenderHighScore',   str(DefenderHighScore))
  ConfigFile.set('scores',   'DefenderGamesPlayed', str(DefenderGamesPlayed))


  print ("Writing configuration file")
  with open(ConfigFileName, 'w') as f:
    ConfigFile.write(f)
  print ("--------------------")



    
  
    
  
  
  
  
def SetTimeHHMM():
  DigitsEntered = 0
  H1  = 0
  H2  = 0
  M1  = 0
  M2  = 0
  Key = -1

  CustomH = ([1,0,1,
              1,0,1,
              1,1,1,
              1,0,1,
              1,0,1])

  CustomM = ([1,0,1,
              1,1,1,
              1,1,1,
              1,0,1,
              1,0,1])

  QuestionMarkSprite = Sprite(
  3,
  5,
  0,
  0,
  0,
  [0,1,1,
   0,0,1,
   0,1,1,
   0,0,0,
   0,1,0]
  )

              
              
  CustomHSprite = Sprite(3,5,SDLowRedR,SDLowRedG,SDLowRedB,CustomH)
  CustomMSprite = Sprite(3,5,SDLowRedR,SDLowRedG,SDLowRedB,CustomM)
  AMSprite      = Sprite(5,5,SDLowGreenR,SDLowGreenG,SDLowGreenB,AlphaSpriteList[0].grid)
  PMSprite      = Sprite(5,5,SDLowGreenR,SDLowGreenG,SDLowGreenB,AlphaSpriteList[15].grid)
  AMPMSprite    = JoinSprite(QuestionMarkSprite,CustomMSprite,1)
  




 
  #ScreenCap  = copy.deepcopy(unicorn.get_pixels())
  ScrollScreen('up',ScreenCap,ScrollSleep)
  ShowScrollingBanner("set time: hours minutes",100,100,0,ScrollSleep)
  ScrollScreen('down',ScreenCap,ScrollSleep)

  
  HHSprite = TrimSprite(CustomHSprite)
  HHSprite = JoinSprite (HHSprite,TrimSprite(CustomHSprite),1)
  
  HHSprite.Display(1,1)
  #unicorn.show()
  #SendBufferPacket(RemoteDisplay,HatHeight,HatWidth)
  
  #Get first hour digit
  while (Key != 0 and Key != 1):
    Key = PollKeyboardInt()
    time.sleep(0.15)
  H1 = Key
  
  #Convert user input H1 to a sprite
  #x = ord(H1) -48
  
  UserH1Sprite = Sprite(3,5,SDLowGreenR,SDLowGreenG,SDLowGreenB,DigitSpriteList[H1].grid)
  CustomHSprite.Erase(1,1)
  UserH1Sprite.Display(1,1)
  #unicorn.show()
  #SendBufferPacket(RemoteDisplay,HatHeight,HatWidth)
  
  #Get second hour digit (special conditions to make sure we keep 12 hour time)
  Key = -1
  while ((H1 == 1 and (Key != 0 and Key != 1 and Key != 2))
     or (H1 == 0 and (Key == -1)) ):
    Key = PollKeyboardInt()
    time.sleep(0.15)
  H2 = Key
 
  #Convert user input H2 to a sprite
  UserH2Sprite = Sprite(3,5,SDLowGreenR,SDLowGreenG,SDLowGreenB,DigitSpriteList[H2].grid)
  CustomHSprite.Erase(5,1)
  UserH2Sprite.Display(5,1)
  #unicorn.show()
  #SendBufferPacket(RemoteDisplay,HatHeight,HatWidth)
    
  #print ("HH: ",H1,H2)
  

  
  
  
  #Get minutes
  time.sleep(1)
  TheMatrix.Clear()

  
  MMSprite = TrimSprite(CustomMSprite)
  MMSprite = JoinSprite (MMSprite,TrimSprite(CustomMSprite),1)
  
  MMSprite.Display(1,1)
  #unicorn.show()
  #SendBufferPacket(RemoteDisplay,HatHeight,HatWidth)
  
  #Get first minute digit
  Key = -1
  while (Key < 0 or Key >= 6):
    Key = PollKeyboardInt()
    time.sleep(0.15)
  M1 = Key
  
  #Convert user input M1 to a sprite
  UserM1Sprite = Sprite(3,5,SDLowGreenR,SDLowGreenG,SDLowGreenB,DigitSpriteList[M1].grid)
  CustomMSprite.Erase(1,1)
  UserM1Sprite.Display(1,1)
  #unicorn.show()
  #SendBufferPacket(RemoteDisplay,HatHeight,HatWidth)
  
  #Get second hour digit
  Key = -1
  while (Key == -1):
    Key = PollKeyboardInt()
    time.sleep(0.15)
  M2 = Key
 
  #Convert user input M2 to a sprite
  UserM2Sprite = Sprite(3,5,SDLowGreenR,SDLowGreenG,SDLowGreenB,DigitSpriteList[M2].grid)
  CustomMSprite.Erase(5,1)
  UserM2Sprite.Display(5,1)
  #unicorn.show()
  #SendBufferPacket(RemoteDisplay,HatHeight,HatWidth)
    
  #print ("MM: ",M1,M2)
  
  time.sleep(1)
  TheMatrix.Clear()

  # a.m / p.m.
  ShowScrollingBanner("AM or PM",100,100,0,ScrollSleep * 0.65)
  AMPMSprite.Display(1,1)
  #unicorn.show()
  #SendBufferPacket(RemoteDisplay,HatHeight,HatWidth)
  #Get A or P
  KeyChar = ''
  while (KeyChar == '' or (KeyChar != 'A' and KeyChar != 'a' and KeyChar != 'P' and KeyChar != 'p' )):
    KeyChar = PollKeyboardRegular()
    time.sleep(0.15)

  AMPMSprite.r = SDLowGreenR
  AMPMSprite.g = SDLowGreenG
  AMPMSprite.b = SDLowGreenB
  AMPMSprite.Display(1,1)
  #unicorn.show()
  #SendBufferPacket(RemoteDisplay,HatHeight,HatWidth)
  
  QuestionMarkSprite.Erase(1,1)

  AMPM = ''
  if (KeyChar == 'a' or KeyChar == 'A'):
    AMSprite.Display(0,1)
    #unicorn.show()
    #SendBufferPacket(RemoteDisplay,HatHeight,HatWidth)
    AMPM  = 'am'
    
  elif (KeyChar == 'p' or KeyChar == 'P'):
    PMSprite.Display(0,1)
    #unicorn.show()
    #SendBufferPacket(RemoteDisplay,HatHeight,HatWidth)
    AMPM = 'pm'
    
  
  #print ("KeyChar ampm:",KeyChar, AMPM)    
  time.sleep(1)
 
  
  
  
  #set system time
  NewTime = str(H1) + str(H2) + ":" + str(M1) + str(M2) + AMPM
  CMD = "sudo date --set " + NewTime
  os.system(CMD)
  
  TheMatrix.Clear()
  ScrollScreenShowClock('down',ScrollSleep)         
  








def ShowScrollingBanner(TheMessage,r,g,b,ScrollSpeed):
  TheMessage = TheMessage.upper()
  TheBanner = CreateBannerSprite(TheMessage)
  TheBanner.r = r 
  TheBanner.g = g 
  TheBanner.b = b 
  TheBanner.ScrollAcrossScreen(HatWidth-1,4,"left",ScrollSpeed)


def ShowScrollingBanner2(TheMessage,rgb,ScrollSpeed,v=5):
  r,g,b = rgb
  TheMessage = TheMessage.upper()
  TheBanner = CreateBannerSprite(TheMessage)
  TheBanner.r = r 
  TheBanner.g = g 
  TheBanner.b = b 
  TheBanner.ScrollAcrossScreen(HatWidth-1,v,"left",ScrollSpeed)

def ShowFloatingBanner(TheMessage,rgb,ScrollSpeed,v=5):
  r,g,b = rgb
  TheMessage = TheMessage.upper()
  TheBanner = CreateBannerSprite(TheMessage)
  TheBanner.r = r 
  TheBanner.g = g 
  TheBanner.b = b 
  TheBanner.FloatAcrossScreen(HatWidth-1,v,"left",ScrollSpeed)












  
def FlashDot(h,v,FlashSleep):
  r,g,b = getpixel(h,v)
  TheMatrix.SetPixel(h,v,0,0,255)
  time.sleep(FlashSleep)
  #unicorn.show()
  #SendBufferPacket(RemoteDisplay,HatHeight,HatWidth)
  TheMatrix.SetPixel(h,v,r,g,b)
  time.sleep(FlashSleep)
  #unicorn.show()
  TheMatrix.SetPixel(h,v,0,255,0)
  time.sleep(FlashSleep)
  #unicorn.show()
  TheMatrix.SetPixel(h,v,r,g,b)
  time.sleep(FlashSleep)
  #unicorn.show()
  #SendBufferPacket(RemoteDisplay,HatHeight,HatWidth)
  return;

def FlashDot2(h,v,FlashSleep):
  r,g,b = getpixel(h,v)
  TheMatrix.SetPixel(h,v,100,100,0)
  TheMatrix.SetPixel(h,v,200,200,0)
  TheMatrix.SetPixel(h,v,255,255,255)
  time.sleep(FlashSleep)
  TheMatrix.SetPixel(h,v,r,g,b)

  return;


  
def FlashDot3(h,v,r,g,b,FlashSleep):
 
    
  LowR = int(r * 0.75)
  LowG = int(g * 0.75)
  LowB = int(b * 0.75)
  HighR = int(r * 1.5)
  HighG = int(g * 1.5)
  HighB = int(b * 1.5)
  
  if (LowR < 0 ):
    LowR = 0
  if (LowG < 0 ):
    LowG = 0
  if (LowB < 0 ):
    LowBB = 0
  
  
  if (HighR > 255):
    HighR = 255
  if (HighG > 255):
    HighG = 255
  if (HighB > 255):
    HighB = 255
    
  TheMatrix.SetPixel(h,v,HighR,HighG,HighB)
  #unicorn.show()
  #SendBufferPacket(RemoteDisplay,HatHeight,HatWidth)
  time.sleep(FlashSleep)
  TheMatrix.SetPixel(h,v,r,g,b)
  #unicorn.show()
  TheMatrix.SetPixel(h,v,LowR,LowG,LowB)
  #unicorn.show()
  time.sleep(FlashSleep)
  #unicorn.show()
  TheMatrix.SetPixel(h,v,HighR,HighG,HighB)
  #unicorn.show()
  time.sleep(FlashSleep)
  TheMatrix.SetPixel(h,v,r,g,b)
  #unicorn.show()
  TheMatrix.SetPixel(h,v,LowR,LowG,LowB)
  #unicorn.show()
  time.sleep(FlashSleep)
  #unicorn.show()
  #SendBufferPacket(RemoteDisplay,HatHeight,HatWidth)
  
  
def FlashDot4(h,v,FlashSleep):
  r,g,b = getpixel(h,v)
  #TheMatrix.SetPixel(h,v,0,0,100)
  #unicorn.show()
  #time.sleep(FlashSleep)
  #TheMatrix.SetPixel(h,v,0,0,175)
  #unicorn.show()
  time.sleep(FlashSleep)
  TheMatrix.SetPixel(h,v,0,0,255)
  #unicorn.show()
  time.sleep(FlashSleep)
  TheMatrix.SetPixel(h,v,0,255,255)
  #unicorn.show()
  time.sleep(FlashSleep)
  TheMatrix.SetPixel(h,v,255,255,255)
  #unicorn.show()
  #SendBufferPacket(RemoteDisplay,HatHeight,HatWidth)
  time.sleep(FlashSleep)
  TheMatrix.SetPixel(h,v,r,g,b)
  #unicorn.show()
  time.sleep(FlashSleep)
  return;
  

def FlashDot5(h,v,TimeSleep):
  #r,g,b = getpixel(h,v)
  
  #There is not get pixel function in rpi-rgb-led
  r,g,b = (255,255,255)

  setpixel(h,v,255,255,255)
  #unicorn.show()
  #SendBufferPacket(RemoteDisplay,HatHeight,HatWidth)
  time.sleep(TimeSleep)
  setpixel(h,v,r,g,b)
  
  
  return;


def FlashDot6(h,v):
  r,g,b = getpixel(h,v)
  TheMatrix.SetPixel(h,v,255,255,255)
  #unicorn.show()
  #TheMatrix.SetPixel(h,v,r,g,b)
  return;


def FlashDot7(h,v):
  TheMatrix.SetPixel(h,v,255,150,0)
  #unicorn.show()
  TheMatrix.SetPixel(h,v,0,0,0)
  return;



  
def DebugPlayfield(Playfield,width,height):
  #Show contents of playfield - in text window, for debugging purposes
    
  print ("Map width height:",width,height)

  
  print ("=======================================")

  for V in range(0,height):
    for H in range (0,width):
       
      name = Playfield[V][H].name
      #print ("Display: ",name,V,H)
      if (name == 'EmptyObject'):
        print ('--',end='')

      #draw border walls
      elif (V == 0 or V == height-1):
        print(' _',end='')
      
      #draw border walls
      elif (H == 0 or H == width-1):
        print(' |',end='')
        
      #draw interior
      elif (name == 'Wall'):
        print (' #',end='')

      elif (name == 'Ground'):
        print (' G',end='')

      #draw asteroid
      elif (name == 'Asteroid'):
        if (Playfield[V][H].alive == 1):
          print (' A',end='')
        else:
          print ('*a')
        
        FlashDot(H,V,0.01)


      #draw asteroid
      elif (name == 'UFO'):
        print (' U',end='')

      #draw asteroid
      elif (name == 'BomberShip'):
        print (' B',end='')

      #draw UFOMissile
      elif (name == 'UFOMissile'):
        print (' m',end='')

      #draw UFOMissile
      elif (name == 'PlayerMissile'):
        print (' p',end='')

      #draw UFOMissile
      elif (name == 'Explosion'):
        print (' E',end='')

      #draw HomingMissile
      elif (name == 'HomingMissile'):
        print (' H',end='')



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
  time.sleep(1)

  return



  



def CreateClockSprite(format=24,hhmmss=''):   
  #print ("CreateClockSprite")
  #Create the time as HHMMSS
  
  if(hhmmss == ''):
    if (format == 12 or format == 2):  
      hhmmss = datetime.now().strftime('%I:%M:%S')
    
    if format == 24:  
      hhmmss = datetime.now().strftime('%H:%M:%S')

  hh,mm,ss = hhmmss.split(':')
    
  #print ("hhmmss:",hhmmss,hh,mm,ss)


  
  #get hour digits
  h1 = int(hh[0])
  h2 = int(hh[1])
  #get minute digits
  m1 = int(mm[0])
  m2 = int(mm[1])

  #print ("h1h2 m1m2",h1,h2,m1,m2)

  #For 12 hour format, we don't want to display leading zero 
  #for tiny clock (2) format we only get hours
  if ((format == 12 or format == 2) and h1 == 0):
    ClockSprite = DigitSpriteList[h2]
  else:
    ClockSprite = JoinSprite(DigitSpriteList[h1], DigitSpriteList[h2], 1)
  
  if (format == 12 or format == 24):
    ClockSprite = JoinSprite(ClockSprite, ColonSprite, 0)
    ClockSprite = JoinSprite(ClockSprite, DigitSpriteList[m1], 0)
    ClockSprite = JoinSprite(ClockSprite, DigitSpriteList[m2], 1)
    

  ClockSprite.r = SDMedRedR
  ClockSprite.g = SDMedRedG
  ClockSprite.b = SDMedRedB
  
  
  #add variables to the object (python allows this, very cool!)
  ClockSprite.h = (HatWidth - ClockSprite.width) // 2
  ClockSprite.v = -4
  ClockSprite.rgb = (SDMedGreenR,SDMedGreenG,SDMedGreenB)
  ClockSprite.hhmm = datetime.now().strftime('%H:%M')
  
  
  #used for displaying clock
  ClockSprite.StartTime = time.time()

  #used for scrolling clock
  ClockSprite.PauseStartTime = time.time()
  ClockSprite.IsScrolling     = 0
  ClockSprite.Delay           = 2
  ClockSprite.PausePositionV  = 1
  ClockSprite.PauseTimerOn    = 0

  
  ClockSprite.on = 1
  ClockSprite.DirectionIncrement = 1

  ClockSprite.name = 'Clock'
  
  return ClockSprite 





def CreateTimerSprite(hhmmss='00:00:00',ShowSeconds=False):   
  #HH:MM:SS
  #print("CreateTimerSprite: ",hhmmss)
  hh,mm,ss = hhmmss.split(':')
    
  #get ints
  h1 = int(hh[0])
  h2 = int(hh[1])
  m1 = int(mm[0])
  m2 = int(mm[1])
  s1 = int(ss[0])
  s2 = int(ss[1])

  #JoinSprite also sets the width of the timer sprite
  TimerSprite = JoinSprite(DigitSpriteList[h1], DigitSpriteList[h2], 1)
  TimerSprite = JoinSprite(TimerSprite, ColonSprite, 0)
  TimerSprite = JoinSprite(TimerSprite, DigitSpriteList[m1], 0)
  TimerSprite = JoinSprite(TimerSprite, DigitSpriteList[m2], 1)

  if (ShowSeconds == True):
    TimerSprite = JoinSprite(TimerSprite, ColonSprite, 0)
    TimerSprite = JoinSprite(TimerSprite, DigitSpriteList[s1], 0)
    TimerSprite = JoinSprite(TimerSprite, DigitSpriteList[s2], 1)

  TimerSprite.HHMMSS = hhmmss    
  TimerSprite.HHMM   = hhmmss[0:5]
 
  #print('CreateTimerSprite: ',hhmmss, h1,h2,m1,m2,s1,s2)
  #print("TimerSprite.HHMMSS:",TimerSprite.HHMMSS)
  #print("TimerSprite.HHMM:  ",TimerSprite.HHMM)

  return TimerSprite 













def CreateSecondsSprite():   
  
  hhmmss = datetime.now().strftime('%I:%M:%S')
  hh,mm,ss = hhmmss.split(':')
 
  #get seconds digits
  s1 = int(ss[0])
  s2 = int(ss[1])

  SecondsSprite = JoinSprite(DigitSpriteList[s1], DigitSpriteList[s2], 1)
  
  SecondsSprite.r = SDDarkOrangeR
  SecondsSprite.g = SDDarkOrangeG
  SecondsSprite.b = SDDarkOrangeB
  
  
  #add variables to the object (python allows this, very cool!)
  SecondsSprite.h = (HatWidth - SecondsSprite.width) // 2
  SecondsSprite.v = 5
  SecondsSprite.rgb = (SDMedGreenR,SDMedGreenG,SDMedGreenB)
  
  return SecondsSprite 



def CreateDayOfWeekSprite():   
  
  weekdaynum = datetime.today().weekday()
  dow        = ""
 
  if (weekdaynum   == 0 ):
    dow = "MON"
  elif (weekdaynum == 1 ):
    dow = "TUE"
  elif (weekdaynum == 2 ):
    dow = "WED"
  elif (weekdaynum == 3 ):
    dow = "THU"
  elif (weekdaynum == 4 ):
    dow = "FRI"
  elif (weekdaynum == 5 ):
    dow = "SAT"
  elif (weekdaynum == 6 ):
    dow = "SUN"


  DowSprite = LeftTrimSprite(CreateBannerSprite(dow),1)  
  
  DowSprite.r = SDMedOrangeR
  DowSprite.g = SDMedOrangeG
  DowSprite.b = SDMedOrangeB
  
  
  #add variables to the object (python allows this, very cool!)
  DowSprite.h = ((HatWidth - DowSprite.width) // 2) -1
  DowSprite.v = 5
  DowSprite.rgb = (SDMedGreenR,SDMedGreenG,SDMedGreenB)
  
  return DowSprite



def CreateMonthSprite():   
  
  ShortMonth = (datetime.now()).strftime('%b').upper()
  #print ("Month:",ShortMonth)
  

  MonthSprite = LeftTrimSprite(CreateBannerSprite(ShortMonth),1)
  
  MonthSprite.r = SDMedBlueR
  MonthSprite.g = SDMedBlueG
  MonthSprite.b = SDMedBlueB
  
  
  #add variables to the object (python allows this, very cool!)
  MonthSprite.h = ((HatWidth - MonthSprite.width) // 2) -1
  MonthSprite.v = 5
  MonthSprite.rgb = (SDMedGreenR,SDMedGreenG,SDMedGreenB)
  
  return MonthSprite



def CreateDayOfMonthSprite():   
  
  DayOfMonth = str((datetime.now()).day)
  #print ("Month:",DayOfMonth)
  

  DayOfMonthSprite = LeftTrimSprite(CreateBannerSprite(DayOfMonth),1)
  
  DayOfMonthSprite.r = SDMedBlueR
  DayOfMonthSprite.g = SDMedBlueG
  DayOfMonthSprite.b = SDMedBlueB
  
  
  #add variables to the object (python allows this, very cool!)
  DayOfMonthSprite.h = ((HatWidth - DayOfMonthSprite.width) // 2) -1
  DayOfMonthSprite.v = 5
  DayOfMonthSprite.rgb = (SDMedGreenR,SDMedGreenG,SDMedGreenB)
  
  return DayOfMonthSprite





def CreateShortMessageSprite(ShortMessage):
  if (ShortMessage == "you win"):
    ShortMessageSprite = Sprite(
      16,
      11,
      200,
      0,
      0,
      [0,1,0,1,0,0,1,1,0,0,1,0,0,1,0,0,
       0,1,0,1,0,1,0,0,1,0,1,0,0,1,0,0,
       0,0,1,0,0,1,0,0,1,0,1,0,0,1,0,0,
       0,0,1,0,0,1,0,0,1,0,1,0,0,1,0,0,
       0,0,1,0,0,0,1,1,0,0,0,1,1,0,0,0,
       0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
       0,1,0,0,0,1,0,1,1,1,0,1,0,0,1,0,
       0,1,0,1,0,1,0,0,1,0,0,1,1,0,1,0,  
       0,1,1,0,1,1,0,0,1,0,0,1,0,1,1,0,
       0,0,1,0,1,0,0,1,1,1,0,1,0,0,1,0,
       0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,  
       ]
    )
  elif (ShortMessage == "you die"):
    ShortMessageSprite = Sprite(
      16,
      11,
      200,
      0,
      0,
      [0,1,0,1,0,0,1,1,0,0,1,0,0,1,0,0,
       0,1,0,1,0,1,0,0,1,0,1,0,0,1,0,0,
       0,0,1,0,0,1,0,0,1,0,1,0,0,1,0,0,
       0,0,1,0,0,1,0,0,1,0,1,0,0,1,0,0,
       0,0,1,0,0,0,1,1,0,0,0,1,1,0,0,0,
       0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
       0,1,1,0,0,1,1,1,0,1,1,1,0,0,1,0,
       0,1,0,1,0,0,1,0,0,1,0,0,0,0,1,0,  
       0,1,0,1,0,0,1,0,0,1,1,1,0,0,1,0,
       0,1,0,1,0,0,1,0,0,1,0,0,0,0,0,0,
       0,1,1,0,0,1,1,1,0,1,1,1,0,0,1,0,  
       ]
    )
  elif (ShortMessage == "smile"):
    ShortMessageSprite = Sprite(
      12,
      10,
      200,
      200,
      0,
      [0,0,0,0,1,1,1,1,0,0,0,0,
       0,0,0,1,0,0,0,0,1,0,0,0,
       0,0,1,0,0,0,0,0,0,1,0,0,
       0,1,0,0,1,0,0,1,0,0,1,0,
       0,1,0,0,0,0,0,0,0,0,1,0,
       0,1,0,1,0,0,0,0,1,0,1,0,
       0,1,0,0,1,1,1,1,0,0,1,0,
       0,0,1,0,0,0,0,0,0,1,0,0,  
       0,0,0,1,0,0,0,0,1,0,0,0,
       0,0,0,0,1,1,1,1,0,0,0,0,
       ]
    )
  else: #(ShortMessage == "frown"):
    ShortMessageSprite = Sprite(
      12,
      10,
      200,
      200,
      0,
      [0,0,0,0,1,1,1,1,0,0,0,0,
       0,0,0,1,0,0,0,0,1,0,0,0,
       0,0,1,0,0,0,0,0,0,1,0,0,
       0,1,0,0,1,0,0,1,0,0,1,0,
       0,1,0,0,0,0,0,0,0,0,1,0,
       0,1,0,0,0,1,1,0,0,0,1,0,
       0,1,0,0,1,0,0,1,0,0,1,0,
       0,0,1,0,0,0,0,0,0,1,0,0,  
       0,0,0,1,0,0,0,0,1,0,0,0,
       0,0,0,0,1,1,1,1,0,0,0,0,
       ]
    )
    
  
  #add variables to the object (python allows this, very cool!)
  ShortMessageSprite.h = (HatWidth - ShortMessageSprite.width) // 2
  ShortMessageSprite.v = 0 - ShortMessageSprite.height
  ShortMessageSprite.rgb = (ShortMessageSprite.r,ShortMessageSprite.g,ShortMessageSprite.b)
  ShortMessageSprite.StartTime = time.time()
  
  #used for scrolling clock
  ShortMessageSprite.PauseStartTime = time.time()
  ShortMessageSprite.IsScrolling     = 0
  ShortMessageSprite.Delay           = 1
  ShortMessageSprite.PausePositionV  = 2
  ShortMessageSprite.PauseTimerOn    = 0
  
  ShortMessageSprite.on = 0
  ShortMessageSprite.DirectionIncrement = 1

  
  return ShortMessageSprite


  
  
def CreateShortWordSprite(ShortWord):   

  ShortWord = ShortWord.upper()
  TheBanner = CreateBannerSprite(ShortWord)
      

  TheBanner.r = SDMedRedR
  TheBanner.g = SDMedRedG
  TheBanner.b = SDMedRedB
  
  
  #add variables to the object (python allows this, very cool!)
  TheBanner.h = (HatWidth - TheBanner.width) // 2
  TheBanner.v = -4
  TheBanner.rgb = (SDMedGreenR,SDMedGreenG,SDMedGreenB)

  #used for displaying clock
  TheBanner.StartTime = time.time()

  #used for scrolling clock
  TheBanner.PauseStartTime = time.time()
  TheBanner.IsScrolling     = 0
  TheBanner.Delay           = 2
  TheBanner.PausePositionV  = 1
  TheBanner.PauseTimerOn    = 0
  
  TheBanner.on = 1
  TheBanner.DirectionIncrement = 1

  
  return TheBanner 

  
  


  

  
 
  
def CreateBannerSprite(TheMessage):
  #We need to dissect the message and build our banner sprite one letter at a time
  #We need to initialize the banner sprite object first, so we pick the first letter
  x = -1

  if (TheMessage == None):
        TheMessage = "UNKNOWN"
    

  TheMessage = TheMessage.upper()
  
  if (len(TheMessage) == 1):
    BannerSprite = Sprite(0,5,0,0,0,[0,0,0,0,0])
  else:  
    BannerSprite = Sprite(1,5,0,0,0,[0,0,0,0,0])
  
  #Iterate through the message, decoding each characater
  for i,c, in enumerate(TheMessage):
    x = ord(c) -65
    if (c == '?'):
      BannerSprite = JoinSprite(BannerSprite, QuestionMarkSprite,0)
    elif (c == '-'):
      BannerSprite = JoinSprite(BannerSprite, DashSprite,0)
    elif (c == '#'):
      BannerSprite = JoinSprite(BannerSprite, PoundSignSprite,0)
    elif (c == '$'):
      BannerSprite = JoinSprite(BannerSprite, DollarSignSprite,0)
    elif (c == '.'):
      BannerSprite = JoinSprite(BannerSprite, PeriodSprite,0)
    elif (c == ':'):
      BannerSprite = JoinSprite(BannerSprite, ColonSprite,0)
    elif (c == '@'):
      BannerSprite = JoinSprite(BannerSprite, AtSignSprite,0)

    elif (c == ','):
      BannerSprite = JoinSprite(BannerSprite, CommaSprite,0)


    elif (c == '('):
      BannerSprite = JoinSprite(BannerSprite, LeftParenthesisSprite,0)
    elif (c == ')'):
      BannerSprite = JoinSprite(BannerSprite, RightParenthesisSprite,0)



    elif (c == '>'):
      BannerSprite = JoinSprite(BannerSprite, GreaterThanSprite,0)


    elif (c == '&'):
      BannerSprite = JoinSprite(BannerSprite, AmpersandSprite,0)


    elif (c == '`'):
      BannerSprite = JoinSprite(BannerSprite, BackTickSprite,0)


    elif (c == '|'):
      BannerSprite = JoinSprite(BannerSprite, PipeSprite,0)


    elif (c == '+'):
      BannerSprite = JoinSprite(BannerSprite, PlusSignSprite,0)
    elif (c == '!'):
      BannerSprite = JoinSprite(BannerSprite, ExclamationSprite,0)

    elif (c == "'"):
      BannerSprite = JoinSprite(BannerSprite, SingleQuoteSprite,0)
    elif (c == '"'):
      BannerSprite = JoinSprite(BannerSprite, DoubleQuoteSprite,0)

    elif (c == '_'):
      BannerSprite = JoinSprite(BannerSprite, UnderscoreSprite,0)

    elif (c == '['):
      BannerSprite = JoinSprite(BannerSprite, LeftSquareBracketSprite,0)

    elif (c == ']'):
      BannerSprite = JoinSprite(BannerSprite, RightSquareBracketSprite,0)
    
    elif (c == '/'):
      BannerSprite = JoinSprite(BannerSprite, ForwardSlashSprite,0)

    elif (c == '\\'):
      BannerSprite = JoinSprite(BannerSprite, BackSlashSprite,0)

    elif (c == chr(193)):
      BannerSprite = JoinSprite(BannerSprite, UpArrowSprite,0)
    elif (c == chr(194)):
      BannerSprite = JoinSprite(BannerSprite, DownArrowSprite,0)

    elif (c == ' '):
      BannerSprite = JoinSprite(BannerSprite, SpaceSprite,0)
    elif (ord(c) >= 48 and ord(c)<= 57):
      BannerSprite = JoinSprite(BannerSprite, DigitSpriteList[int(c)],1)
    else:
      
      try:
        BannerSprite = JoinSprite(BannerSprite, TrimSprite(AlphaSpriteList[x]),1)
      except:
        print("Warning!  Character (",c,") not found.")
        BannerSprite = JoinSprite(BannerSprite, QuestionMarkSprite,0)

  return BannerSprite

  
    

  
  

def ShowLevelCount(LevelCount):
  global MainSleep
  TheMatrix.Clear()
      
  SDColor = (random.randint (0,6) *4 + 1) 
  print ("LevelCountColor:",SDColor)
  
  r,g,b =  ColorList[SDColor]  
  max   = 50
  #sleep = 0.06 * MainSleep
  
  #print ("sleep: ",sleep," MainSleep: ",MainSleep)
  
  LevelSprite = Sprite(1,5,r,g,b,[0,0,0,0,0])
  
  if (LevelCount > 9):
    LevelString = str(LevelCount)
    LevelSprite1 = DigitSpriteList[int(LevelString[0])]
    LevelSprite2 = DigitSpriteList[int(LevelString[1])]
   
    
    for x in range(0,max,1):
      LevelSprite1.r = r + x*5
      LevelSprite1.g = g + x*5
      LevelSprite1.b = b + x*5
      LevelSprite2.r = r + x*5
      LevelSprite2.g = g + x*5
      LevelSprite2.b = b + x*5

      if(LevelSprite1.r > 255):
        LevelSprite1.r = 255
      if(LevelSprite1.g > 255):
        LevelSprite1.g = 255
      if(LevelSprite1.b > 255):
        LevelSprite1.b = 255
      if(LevelSprite2.r > 255):
        LevelSprite2.r = 255
      if(LevelSprite2.g > 255):
        LevelSprite2.g = 255
      if(LevelSprite2.b > 255):
        LevelSprite2.b = 255

      LevelSprite.Display((HatWidth-6) // 2 ,(HatHeight -5)//2)
      LevelSprite.Display((HatWidth-10) // 2 ,(HatHeight -5)//2)      
      #unicorn.show()
      #SendBufferPacket(RemoteDisplay,HatHeight,HatWidth)
      #time.sleep(sleep)

    
    for x in range(0,max,1):
      LevelSprite1.r = r + max -x*3
      LevelSprite1.g = g + max -x*3
      LevelSprite1.b = b + max -x*3
      LevelSprite2.r = r + max -x*3
      LevelSprite2.g = g + max -x*3
      LevelSprite2.b = b + max -x*3

      if(LevelSprite1.r < r):
        LevelSprite1.r = r
      if(LevelSprite1.g < g):
        LevelSprite1.g = g
      if(LevelSprite1.b < b):
        LevelSprite1.b = b
      if(LevelSprite2.r < r):
        LevelSprite2.r = r
      if(LevelSprite2.g < g):
        LevelSprite2.g = g
      if(LevelSprite2.b < b):
        LevelSprite2.b = b

      LevelSprite1.Display(6,1)
      LevelSprite2.Display(10,1)
      #unicorn.show()
      #SendBufferPacket(RemoteDisplay,HatHeight,HatWidth)

      #time.sleep(sleep) 
     
      
  else:    
    LevelSprite = DigitSpriteList[LevelCount]

    for x in range(0,max,1):
      LevelSprite.r = r + x*3
      LevelSprite.g = g + x*3
      LevelSprite.b = b + x*3

      if(LevelSprite.r > 255):
        LevelSprite.r = 255
      if(LevelSprite.g > 255):
        LevelSprite.g = 255
      if(LevelSprite.b > 255):
        LevelSprite.b = 255

      LevelSprite.Display((HatWidth-3) // 2 ,(HatHeight -5)//2)
      #unicorn.show()
      #SendBufferPacket(RemoteDisplay,HatHeight,HatWidth)
      #time.sleep(sleep) 
      
    for x in range(0,max,1):
      LevelSprite.r = r + max -x*3
      LevelSprite.g = g + max -x*3
      LevelSprite.b = b + max -x*3

      if(LevelSprite.r < r):
        LevelSprite.r = r
      if(LevelSprite.g < g):
        LevelSprite.g = g
      if(LevelSprite.b < b):
        LevelSprite.b = b
      LevelSprite.Display((HatWidth-3) // 2 ,(HatHeight -5)//2)
      #unicorn.show()
      #SendBufferPacket(RemoteDisplay,HatHeight,HatWidth)
      #time.sleep(sleep)
      

  
  TheMatrix.Clear()
  return
  







  

  


  
def ScreenWipe(Wipe, Speed):
  if Wipe == "RedCurtain":
    for x in range (HatWidth):
      for y in range (HatHeight):
        TheMatrix.SetPixel(x,y,255,0,0)
        #unicorn.show()
        #SendBufferPacket(RemoteDisplay,HatHeight,HatWidth)
        time.sleep(Speed)
    
#Primitive, single color



  



  
  
def MoveBigSprite(sprite,FlashSleep):
  for i in range (0,80):
    
    y,x = divmod(i,16)
    #print ("x,y,i",x,y,i)
    if (x >= 0 and x<= 2):
      BigSprite.grid[i] = DigitSpriteList[2].grid[x-(0*4)+(y*3)]
    if (x >= 4 and x<= 6):
      BigSprite.grid[i] = DigitSpriteList[3].grid[x-(1*4)+(y*3)]
    if (x >=8  and x<= 10):
      BigSprite.grid[i] = DigitSpriteList[0].grid[x-(2*4)+(y*3)]
    if (x >=12  and x<= 14):
      BigSprite.grid[i] = DigitSpriteList[7].grid[x-(3*4)+(y*3)]
    #"looping"
  BigSprite.Scroll(-16,0,"right",24,FlashSleep)
  BigSprite.Scroll(9,0,"left",24,FlashSleep)
    

  
def JoinSprite(Sprite1, Sprite2, Buffer):
  #This function takes two sprites, and joins them together horizontally
  #The color of the second sprite is used for the new sprite
  height = Sprite1.height
  width  = Sprite1.width + Buffer + Sprite2.width
  elements = height * width
  x = 0
  y = 0
  
 
  TempSprite = Sprite(
  width,
  height,
  Sprite2.r,
  Sprite2.g,
  Sprite2.b,
  [0]*elements
  )
  for i in range (0,elements):
    y,x = divmod(i,width)
    
    #copy elements of first sprite
    if (x >= 0 and x< Sprite1.width):
      TempSprite.grid[i] = Sprite1.grid[x + (y * Sprite1.width)]
    
    if (x >= (Sprite1.width + Buffer) and x< (Sprite1.width + Buffer + Sprite2.width)):
      TempSprite.grid[i] = Sprite2.grid[(x - (Sprite1.width + Buffer)) + (y * Sprite2.width)]

  
  return TempSprite    


def TrimSprite(Sprite1):
  height       = Sprite1.height
  width        = Sprite1.width
  newwidth     = 0
  elements     = height * width
  Empty        = 1
  Skipped      = 0
  EmptyColumns = []
  EmptyCount   = 0
  BufferX      = 0
  BufferColumn = [(0) for i in range(height)]
  
  i = 0
  x = 0
  y = 0

  
  for x in range (0,width):
    
    #Find empty columns, add them to a list
    Empty = 1  
    for y in range (0,height):
      i = x + (y * width)
      
      BufferColumn[y] = Sprite1.grid[i]
      if (Sprite1.grid[i] != 0):
        Empty = 0
    
    if (Empty == 0):
      newwidth =  newwidth + 1
    
    elif (Empty == 1):
      #print ("Found empty column: ",x)
      EmptyColumns.append(x)
      EmptyCount = EmptyCount +1

      
  BufferSprite = Sprite(
    newwidth,
    height,
    Sprite1.r,
    Sprite1.g,
    Sprite1.b,
    [0]*(newwidth*height)
    )
      
  #Now that we identified the empty columns, copy data and skip those columns
  for x in range (0,width):
    Skipped = 0
    
    for y in range (0,height):
      i = x + (y * width)
      b = BufferX + (y * newwidth)
      if (x in EmptyColumns):
        Skipped = 1
      else:
        BufferSprite.grid[b] = Sprite1.grid[i]
    
    
    #advance our Buffer column counter only if we skipped a column
    if (Skipped == 0):
      BufferX = BufferX + 1
    
    
  
  BufferSprite.width = newwidth
  
  
  
  #print (BufferSprite.grid)
  return BufferSprite



def LeftTrimSprite(Sprite1,Columns):
  height       = Sprite1.height
  width        = Sprite1.width
  newwidth     = 0
  elements     = height * width
  Empty        = 1
  Skipped      = 0
  EmptyColumns = []
  EmptyCount   = 0
  BufferX      = 0
  BufferColumn = [(0) for i in range(height)]
  
  i = 0
  x = 0
  y = 0

  
  for x in range (0,width):
    
    #Find empty columns, add them to a list
    Empty = 1  
    for y in range (0,height):
      i = x + (y * width)
      
      BufferColumn[y] = Sprite1.grid[i]
      if (Sprite1.grid[i] != 0):
        Empty = 0
    
    if (Empty == 0 or EmptyCount > Columns):
      newwidth =  newwidth + 1
    
    elif (Empty == 1):
      #print ("Found empty column: ",x)
      EmptyColumns.append(x)
      EmptyCount = EmptyCount +1

      
  BufferSprite = Sprite(
    newwidth,
    height,
    Sprite1.r,
    Sprite1.g,
    Sprite1.b,
    [0]*(newwidth*height)
    )
      
  #Now that we identified the empty columns, copy data and skip those columns
  for x in range (0,width):
    Skipped = 0
    
    for y in range (0,height):
      i = x + (y * width)
      b = BufferX + (y * newwidth)
      if (x in EmptyColumns):
        Skipped = 1
      else:
        BufferSprite.grid[b] = Sprite1.grid[i]
    
    
    #advance our Buffer column counter only if we skipped a column
    if (Skipped == 0):
      BufferX = BufferX + 1
    
    
  
  BufferSprite.width = newwidth
  
  
  
  #print (BufferSprite.grid)
  return BufferSprite
    
  



#------------------------------------------------------------------------------
# Keyboard Functions                                                         --
#------------------------------------------------------------------------------
  

def CheckElapsedTime(seconds):
  global StartTime
  elapsed_time = time.time() - StartTime
  elapsed_hours, rem = divmod(elapsed_time, 3600)
  elapsed_minutes, elapsed_seconds = divmod(rem, 60)


  m,r = divmod(round(elapsed_seconds), seconds)
  #print("Elapsed Time: {:0>2}:{:0>2}:{:05.2f}".format(int(elapsed_hours),int(elapsed_minutes),elapsed_seconds)," CheckSeconds:",seconds," remainder:",r,end="\r")

  #if (elapsed_seconds >= seconds ):
    #StartTime = time.time()
  if (r == 0):
    return 1
  else:
    return 0




#------------------------------------------------------------------------------
# Keyboard Functions                                                         --
#------------------------------------------------------------------------------




def ProcessKeypress(Key):

  global MainSleep
  global ScrollSleep
  global NumDots

  # a = animation demo
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
    TheMatrix.Clear()
    ShowScrollingBanner2("Quit!",(MedRed),ScrollSleep)
  elif (Key == "r"):
    TheMatrix.Clear()
    #ShowScrollingBanner("Reboot!",100,0,0,ScrollSleep * 0.55)
    os.execl(sys.executable, sys.executable, *sys.argv)
  elif (Key == "t"):

    ActivateClockMode(60)

  elif (Key == "c"):
    DrawTinyClock(60)
  elif (Key == "h"):
    SetTimeHHMM()
  elif (Key == "i"):
    ShowIPAddress()

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



    
    
    


def GetKey(stdscr):
  ReturnChar = ""
  stdscr.nodelay(1) # doesn't keep waiting for a key press
  c = stdscr.getch()  
  
  #Look for specific characters
  if  (c == ord(" ") 
    or c == ord("+")
    or c == ord("-")
    or c == ord("a")
    or c == ord("b")
    or c == ord("c")
    or c == ord("d")
    or c == ord("h")
    or c == ord("i")
    or c == ord("p")
    or c == ord("q")
    or c == ord("r")
    or c == ord("t")
    or c == ord("n")
    or c == ord("m") ):
    ReturnChar = chr(c)       

  #Look for digits (ascii 48-57 == digits 0-9)
  elif (c >= 48 and c <= 57):
    print ("Digit detected")
    ReturnChar = chr(c)    

  return ReturnChar
 

  
  

def PollKeyboard():
  Key = ""
  curses.filter()
  stdscr = curses.initscr()
  curses.noecho()
  Key = curses.wrapper(GetKey)
  if (Key != ""):
    print ("----------------")
    print ("Key Pressed: ",Key)
    print ("----------------")
    #ProcessKeypress(Key)
    #SaveConfigData()
    
  
  return Key


  
def GetKeyInt(stdscr):
  ReturnInt = -1
  stdscr.nodelay(1) # doesn't keep waiting for a key press
  
  #gets ascii value
  c = stdscr.getch()  

  
  #Look for digits (ascii 48-57 == digits 0-9)
  if (c >= 48 and c <= 57):
    print ("Digit detected")
    ReturnInt = c - 48   

  return ReturnInt

  
  
def PollKeyboardInt():
  Key = -1
  stdscr = curses.initscr()
  curses.noecho()
  Key = curses.wrapper(GetKeyInt)
  if (Key != -1):
    print ("----------------")
    print ("Key Pressed: ",Key)
    print ("----------------")
    ProcessKeypress(Key)
  
  return Key


  

  
  
# This section deals with getting specific input from a question and does not
# trigger events  
  
def GetKeyRegular(stdscr):
  ReturnChar = ""
  stdscr.nodelay(1) # doesn't keep waiting for a key press
  c = stdscr.getch()  

  if (c >= 48 and c <= 150):
    ReturnChar = chr(c)    

  return ReturnChar
  
def PollKeyboardRegular():
  Key = ""
  stdscr = curses.initscr()
  curses.noecho()
  Key = curses.wrapper(GetKeyRegular)
  if (Key != ""):
    print ("----------------")
    print ("Key Pressed: ",Key)
    print ("----------------")
  
  return Key
  


def GetClockDot(time):
  #this is a list of hv coordinates around the outside of the unicorn hat
  #pass in a number from 1-60 to get the correct dot to display
  
  DotList = []
  DotList.append ([4,0]) #0 same as 60
  DotList.append ([4,0])
  DotList.append ([5,0])
  DotList.append ([6,0])
  DotList.append ([7,0])
  DotList.append ([7,1])
  DotList.append ([7,2])
  DotList.append ([7,3])
  DotList.append ([7,4])
  DotList.append ([7,5])
  DotList.append ([7,6])
  DotList.append ([7,7])
  DotList.append ([6,7])
  DotList.append ([5,7])
  DotList.append ([4,7])
  DotList.append ([3,7])
  DotList.append ([2,7])
  DotList.append ([1,7])
  DotList.append ([0,7])
  DotList.append ([0,6])
  DotList.append ([0,5])
  DotList.append ([0,4])
  DotList.append ([0,3])
  DotList.append ([0,2])
  DotList.append ([0,1])
  DotList.append ([0,0])
  DotList.append ([1,0])
  DotList.append ([2,0])
  DotList.append ([3,0])
  
  return DotList[time]







def DrawTinyClock(Minutes):
  print ("--DrawTinyClock--")
  print ("Minutes:",Minutes)
  TheMatrix.Clear()
  MinDate = datetime.now()
  MaxDate = datetime.now() + timedelta(minutes=Minutes)
  now     = datetime.now()
  Quit    = 0
  

  while (now >= MinDate and now <= MaxDate and Quit == 0):
    print ("--DrawTinyClock--")
    TheMatrix.Clear()
    ClockSprite = CreateClockSprite(2)
    ClockSprite.r = SDDarkRedR
    ClockSprite.g = SDDarkRedG
    ClockSprite.b = SDDarkRedB


    #Center the display
    h = 3 - (ClockSprite.width // 2)
    ClockSprite.Display(h,1)

    #break apart the time
    now = datetime.now()

    print ("Now:",now)
    print ("Min:",MinDate)
    print ("Max:",MaxDate)
    DrawClockMinutes()
    Quit = DrawClockSeconds()
    print("Quit:",Quit)
    now = datetime.now()

  TheMatrix.Clear()
    
def DrawClockMinutes():

  #break apart the time
  now = datetime.now()
  mm  = now.minute
  print ("DrawClockMinutes minutes:",mm)  
  
  dots = int(28.0 // 60.0 * mm)

#  #Erase  
  for i in range(1,28):
    h,v = GetClockDot(i)
  TheMatrix.SetPixel(h,v,0,0,0)
  #unicorn.show()
  #SendBufferPacket(RemoteDisplay,HatHeight,HatWidth)

  
  for i in range(1,dots+1):
    print ("Setting minute dot:",i)
    h,v = GetClockDot(i)
    TheMatrix.SetPixel(h,v,SDDarkBlueR,SDDarkBlueG,SDDarkBlueB)
    #unicorn.show()
    #SendBufferPacket(RemoteDisplay,HatHeight,HatWidth)
  
  
  
  
def DrawClockSeconds():
  #break apart the time
  now = datetime.now()
  ss  = now.second
  
  print ("--DrawClockSeconds seconds:",ss,"--")  

  r = 0
  g = 0
  b = 0
  
   
  h = 0
  v = 0
  x = -1
  y = -1
  
  
  TheMatrix.SetPixel(3,0,0,0,0)


  for i in range(ss,61):
    
    #Erase dot 0/60
    DisplayDot =  int(28.0 // 60.0 * i)
    h,v = GetClockDot(DisplayDot)
    
    
    print ("Setting second dot:",i)
    #print ("xy hv:",x,y,h,v)
    if (x >= 0):
      #print ("writing old pixel")
      TheMatrix.SetPixel(x,y,r,g,b)

    
    #capture previous pixel
    x,y = h,v
    
    r,g,b = getpixel(h,v)
    TheMatrix.SetPixel(h,v,SDLowWhiteR,SDLowWhiteG,SDLowWhiteB)
    #unicorn.show()
    #SendBufferPacket(RemoteDisplay,HatHeight,HatWidth)
    time.sleep(0.005)

    TheMatrix.SetPixel(h,v,SDDarkPurpleR,SDDarkPurpleG,SDDarkPurpleB)
    #unicorn.show()
    #SendBufferPacket(RemoteDisplay,HatHeight,HatWidth)
    
    #Check for keyboard input
    Key = PollKeyboard()
    if (Key == 'q'):
      return 1
    

    
    time.sleep(0.995)
    
  print ("--end seconds--")
  return 0
  


#--------------------------------------
#  Transitions and Sequences         --
#--------------------------------------


def ShowDropShip(h,v,action,speed):

  PlayerShipR = SDMedBlueR
  PlayerShipG = SDMedBlueG
  PlayerShipB = SDMedBlueB

  print("ShowDropShip:",action)
  setpixel(h,v,PlayerShipR,PlayerShipG,PlayerShipB)
  #Canvas = unicorn.get_pixels()
  setpixel(h,v,0,0,0)
  #Buffer2 = unicorn.get_pixels()
  setpixel(h,v,PlayerShipR,PlayerShipG,PlayerShipB)
  
  if (action == 'pickup'):
    
    DropShip.Animate(h-2,v+1,'forward',speed)
    DropShip.Animate(h-2,v+1,'forward',speed)
    DropShip.Animate(h-2,v+1,'forward',speed)
    DropShip.Animate(h-2,v+1,'forward',speed)
    DropShip.Animate(h-2,v+1,'forward',speed)
    DropShip.Animate(h-2,v+1,'forward',speed)
    DropShip.Animate(h-2,v+1,'forward',speed)
    DropShip.Animate(h-2,v+1,'forward',speed)
    DropShip.Animate(h-2,v+1,'forward',speed)

    #print("Sleeping")
    for y in range(v-5,-10,-1):
      DropShip.Animate(h-2,y,'forward',speed)
      DropShip.Animate(h-2,y,'forward',speed)
      DropShip.Animate(h-2,y,'forward',speed)
  else:
    for y in range(-14,v-5):
      DropShip.Animate(h-2,y,'forward',speed)
      DropShip.Animate(h-2,y,'forward',speed)
      DropShip.Animate(h-2,y,'forward',speed)

    DropShip.Animate(h-2,v+1,'forward',speed)
    DropShip.Animate(h-2,v+1,'forward',speed)
    DropShip.Animate(h-2,v+1,'forward',speed)
    DropShip.Animate(h-2,v+1,'forward',speed)
    DropShip.Animate(h-2,v+1,'forward',speed)
    DropShip.Animate(h-2,v+1,'forward',speed)
    DropShip.Animate(h-2,v+1,'forward',speed)
    DropShip.Animate(h-2,v+1,'forward',speed)
    DropShip.Animate(h-2,v+1,'forward',speed)
    
    
    for y in range(v-5,-10,-1):
      DropShip.Animate(h-2,y,'forward',speed)
      DropShip.Animate(h-2,y,'forward',speed)
      DropShip.Animate(h-2,y,'forward',speed)




def ScrollBigClock(direction,speed,ZoomFactor):    
  #Screen capture is a copy of the unicorn display Buffer, which in HD is a numby array
  #Capture the screen, then pass that to this function
  #this function will make a copy, chop up that copy and display the slices in the order to make
  #it look like the screen is scrolling up or down, left or right
  
  #For now, we scroll, replacing with empty screen.  Also, reverse.
 
  RGB, ShadowRGB = GetBrightAndShadowRGB()

  #Canvas.Clear()
  
  #ClockScreen
  ClockScreen  = [[]]
  ClockScreen  = [[ (0,0,0) for i in range(HatWidth)] for i in range(HatHeight)]
  

  ScreenCopy = copy.deepcopy(ScreenArray)
  ScreenCopy2 = copy.deepcopy(ScreenArray)

  #ClearBuffers()
  print("about to create clock sprite")
  TheTime = CreateClockSprite(12)
  TheTime.h = (HatWidth  //2) - (TheTime.width  * ZoomFactor // 2) - ZoomFactor
  TheTime.v = (HatHeight //2) - (TheTime.height * ZoomFactor // 2) - ZoomFactor
  

  print ("create clock scren")
  #this will copy the clock sprite to the regular screen buffer ScreenBuffer
  #make drop shadow then draw current time
  ClockScreen = CopySpriteToScreenArrayZoom(TheBuffer=ClockScreen, TheSprite=TheTime,h=TheTime.h-2,v=TheTime.v+2, ColorTuple=ShadowRGB,FillerTuple=(-1,-1,-1),ZoomFactor = ZoomFactor,Fill=False)
  ClockScreen = CopySpriteToScreenArrayZoom(TheBuffer=ClockScreen, TheSprite=TheTime,h=TheTime.h-1,v=TheTime.v+1, ColorTuple=ShadowRGB,FillerTuple=(-1,-1,-1),ZoomFactor = ZoomFactor,Fill=False)
  ClockScreen = CopySpriteToScreenArrayZoom(TheBuffer=ClockScreen, TheSprite=TheTime,h=TheTime.h,v=TheTime.v, ColorTuple=RGB,FillerTuple=(-1,-1,-1),ZoomFactor = ZoomFactor,Fill=False)
  print ("clock screen created")
  
  print ("about to start scrolling")
  
    

  #Scroll up
  #Delete top row, insert blank on bottom, pushing remaining to the top
  if (direction == 'up'):
    
  
    for x in range (0,HatHeight):
      #Take a line from the clock sprite 
      InsertLine = ClockScreen[x]
      ScreenCopy = numpy.delete(ScreenCopy,(0),axis=0)
      ScreenCopy  = numpy.insert(ScreenCopy,HatHeight-1,InsertLine,axis=0)
      setpixelsLED(ScreenCopy)

      #SendBufferPacket(RemoteDisplay,HatHeight,HatWidth)
      time.sleep(speed)

    
    

  Oldmm = 0
  done  = 0
  ShownOnce = 0
  

  print("going into a loop")

  while (1 == 1):
 
    #If the time has changed, draw a new time
    mm = datetime.now().strftime('%M')
    if (mm != Oldmm):
      #Erase old time
      Oldmm = mm
      

      TheTime = CreateClockSprite(12)
      TheTime.h = (HatWidth //2 )  - (TheTime.width * ZoomFactor // 2)  - ZoomFactor
      TheTime.v = (HatHeight //2 ) - (TheTime.height * ZoomFactor // 2) - ZoomFactor

      #Display New Time
      ClockScreen  = [[]]
      ClockScreen  = [[ (0,0,0) for i in range(HatWidth)] for i in range(HatHeight)]
      #make drop shadow then draw current time
      ClockScreen = CopySpriteToScreenArrayZoom(TheBuffer=ClockScreen, TheSprite=TheTime,h=TheTime.h-2,v=TheTime.v+2, ColorTuple=ShadowRGB,FillerTuple=(-1,-1,-1),ZoomFactor = ZoomFactor,Fill=False)
      ClockScreen = CopySpriteToScreenArrayZoom(TheBuffer=ClockScreen, TheSprite=TheTime,h=TheTime.h-1,v=TheTime.v+1, ColorTuple=ShadowRGB,FillerTuple=(-1,-1,-1),ZoomFactor = ZoomFactor,Fill=False)
      ClockScreen = CopySpriteToScreenArrayZoom(TheBuffer=ClockScreen, TheSprite=TheTime,h=TheTime.h,v=TheTime.v, ColorTuple=RGB,FillerTuple=(-1,-1,-1),ZoomFactor = ZoomFactor,Fill=False)
      setpixelsLED(ClockScreen)

      


    Key = PollKeyboard()
    if (Key =='q'):
      for x in range (0,HatHeight):
        InsertLine = ScreenCopy2[x]
        ClockScreen = numpy.delete(ClockScreen,(0),axis=0)
        ClockScreen = numpy.insert(ClockScreen,HatHeight-1,InsertLine,axis=0)
        setpixelsLED(ClockScreen)
        #unicorn.show()
        #SendBufferPacket(RemoteDisplay,HatHeight,HatWidth)
        time.sleep(speed)
      return;

    print("sleeping")
    time.sleep(1)








def ScrollScreen(direction,ScreenCap,speed):    
  #Screen capture is a copy of the unicorn display Buffer, which in HD is a numby array
  #Capture the screen, then pass that to this function
  #this function will make a copy, chop up that copy and display the slices in the order to make
  #it look like the screen is scrolling up or down, left or right
  
  #For now, we scroll, replacing with empty screen.  Also, reverse.
 
 
  EmptyCap   = [[(0,0,0) for i in range (0,HatWidth)]]
  InsertLine = copy.deepcopy(EmptyCap)
  Buffer     = copy.deepcopy(EmptyCap)

  
  #Scroll up
  #Delete top row, insert blank on bottom, pushing remaining to the top
  if (direction == 'up'):
    Buffer = copy.deepcopy(ScreenCap)
    #print ("Buffer",Buffer)

    for x in range (0,HatHeight):
      
      Buffer = numpy.delete(Buffer,(0),axis=1)
      Buffer = numpy.insert(Buffer,HatHeight-1,InsertLine,axis=1)
      setpixelsLED(Buffer)


      #unicorn.show()
      #SendBufferPacket(RemoteDisplay,HatHeight,HatWidth)
      #print(Buffer)
      time.sleep(speed)

  #Scroll down
  #Screen is blank, start adding lines from ScreenCap
  if (direction == 'down'):
    # Make an empty Buffer, axis must be 0 to match the EmptyBuffer layout [(0,0,0),(0,0,0),(0,0,0)...etc.]
    Buffer = [[(0,0,0) for i in range(HatHeight)] for i in range(HatWidth)]

    for x in range (0,HatWidth):
      InsertLine = [()]
      #copy line from the ScreenCap into the Buffer
      #we do this one element at a time because I could not figure out how to slice the array properly
      for y in range (0,HatWidth):
        InsertLine = numpy.append(InsertLine, ScreenCap[y][abs(HatWidth-1 - x)])

      InsertLine = InsertLine.reshape(1,HatWidth,3)
      Buffer = numpy.insert(Buffer,0,InsertLine,axis=1)
      setpixelsLED(Buffer)
      #unicorn.show()
      #SendBufferPacket(RemoteDisplay,HatHeight,HatWidth)
      time.sleep(speed)


      
      

  #Scroll to RIGHT
  #Delete right row, insert blank on left, pushing remaining to the right
  if (direction == 'right'):
    Buffer = copy.deepcopy(ScreenCap)
    for x in range (0,HatWidth):
      
      Buffer = numpy.delete(Buffer,(0),axis=0)
      Buffer = numpy.append(Buffer,EmptyCap,axis=0)
      setpixelsLED(Buffer)
      #unicorn.show()
      #SendBufferPacket(RemoteDisplay,HatHeight,HatWidth)
      #time.sleep(speed)
  
  
  
  
  #Scroll to LEFT
  #Delete left row, insert blank on right, pushing remaining to the left
  if (direction == 'left'):
    # Make an empty Buffer
    for x in range (0,HatWidth-1):
      Buffer = numpy.append(Buffer,EmptyCap,axis=0)

    for x in range (0,HatWidth):
      Buffer = numpy.delete(Buffer,(-1),axis=0)
      
      #Copy each tuple to the line to be inserted (gotta be a better way!)
      for j in range (HatWidth):
        InsertLine[0][j] = ScreenCap[abs(HatWidth-x)][j]
      
      Buffer = numpy.insert(Buffer,0,InsertLine,axis=0)
      
      setpixelsLED(Buffer)
      #unicorn.show()
      #SendBufferPacket(RemoteDisplay,HatHeight,HatWidth)
      time.sleep(speed)


      




def ZoomScreen(ScreenArray, ZoomStart, ZoomStop, ZoomSleep, Fade=False):    
    ZoomFactor = 0
    DimIncrement = max(round(100 / abs(ZoomStart - ZoomStop)), 1)
    OldBrightness = TheMatrix.brightness
    Brightness = OldBrightness

    if ZoomStart <= ZoomStop:
        for ZoomFactor in range(ZoomStart, ZoomStop):
            if Fade:
                Brightness -= DimIncrement
                if Brightness >= 0:
                    TheMatrix.brightness = Brightness
            # TheMatrix.Clear()  ← REMOVE THIS LINE
            DisplayScreenCap(ScreenArray, ZoomFactor)
            if ZoomSleep > 0:
                time.sleep(ZoomSleep)

    else:
        for ZoomFactor in reversed(range(ZoomStop, ZoomStart)):
            if Fade:
                Brightness -= DimIncrement
                if Brightness >= 0:
                    TheMatrix.brightness = Brightness
            # TheMatrix.Clear()  ← REMOVE THIS LINE
            DisplayScreenCap(ScreenArray, ZoomFactor)
            if ZoomSleep > 0:
                time.sleep(ZoomSleep)

    TheMatrix.brightness = OldBrightness




# Try looping the number of zooms, but re-capture the screen at the zoomed in level and pass that back into
# the DisplayScreenCap function


def ZoomScreen_old(ScreenArray,ZoomStart,ZoomStop,ZoomSleep,Fade=False):    
  #Capture the screen, then pass that to this function
  #Loop through the zoom levels specified, calling the DisplayScreenCap function

 
  ZoomFactor    = 0
  DimIncrement  = max(round(100 / abs(ZoomStart - ZoomStop)),1)
  OldBrightness = TheMatrix.brightness
  Brightness    = OldBrightness

  if (ZoomStart <= ZoomStop):
    for ZoomFactor in range (ZoomStart,ZoomStop):
      if (Fade == True):
        Brightness = Brightness - DimIncrement
        if (Brightness >= 0):
          TheMatrix.brightness = Brightness
          #print("Brightness:",Brightness)
      TheMatrix.Clear()        
      DisplayScreenCap(ScreenArray,ZoomFactor)
      if (ZoomSleep > 0):
        time.sleep(ZoomSleep)
        
  else:
    for ZoomFactor in reversed(range(ZoomStop, ZoomStart)):
      #clear the screen as we zoom to remove leftovers
      if (Fade == True):
        Brightness = Brightness - DimIncrement
        if (Brightness >= 0):
          TheMatrix.brightness = Brightness
          #print("Brightness:",Brightness)
      TheMatrix.Clear()        
      DisplayScreenCap(ScreenArray,ZoomFactor)
      if (ZoomSleep > 0):
        time.sleep(ZoomSleep)

  #go back to old brightness
  TheMatrix.brightness = OldBrightness


  # for y in range (HatWidth):
    # for x in range (HatWidth):
      # r,g,b = ScreenCap[abs(15-x)][y]
      # TheMatrix.SetPixel(x,y,r,g,b)





def DisplayScreenCap(ScreenCap, ZoomFactor=0):
    global Canvas

    r = g = b = 0
    H_modifier = V_modifier = 0
    HIndentFactor = VIndentFactor = 0

    # Create new buffer, do not clear existing canvas until after swap
    new_canvas = Canvas
    new_canvas.Clear()

    if ZoomFactor > 1:
        H_modifier = (1 / HatWidth) * ZoomFactor * 2
        V_modifier = (1 / HatHeight) * ZoomFactor

        NewHeight = round(HatHeight * V_modifier)
        NewWidth  = round(HatWidth * H_modifier)

        HIndentFactor = (HatWidth / 2)  - (NewWidth / 2)
        VIndentFactor = (HatHeight / 2) - (NewHeight / 2)

    for V in range(0, HatHeight):
        for H in range(0, HatWidth):
            r, g, b = ScreenCap[V][H]

            if ZoomFactor > 0:
                draw_h = int((H * H_modifier) + HIndentFactor)
                draw_v = int((V * V_modifier) + VIndentFactor)
            else:
                draw_h = H
                draw_v = V

            if 0 <= draw_h < HatWidth and 0 <= draw_v < HatHeight:
                new_canvas.SetPixel(draw_h, draw_v, r, g, b)

    # Only now swap to avoid flashing blank screen
    Canvas = TheMatrix.SwapOnVSync(new_canvas)



def DisplayScreenCap_original(ScreenCap,ZoomFactor = 0):
  #This function writes a Screen capture to the buffer using the specified zoom factor
  #ZoomFactor is based on Vertical height.  
  #  Matrix = 32, Zoom 16 = shrink screen to 1/2 size
  #  Matrix = 32, Zoom 64 = show 1/2 of screen capture, doubled so it fits on whole screen
  r = 0
  g = 0
  b = 0
  count    = 0
  H_modifier = 0
  V_modifier = 0
  H = 0
  V = 0
  HIndentFactor = 0    
  VIndentFactor = 0    
  
 

  #NewScreenCap = deepcopy.copy(ScreenCap)


  if (ZoomFactor > 1):
    H_modifier = (1 / HatWidth ) * ZoomFactor * 2  #BigLED is 2 times wider than tall. Hardcoding now, will fix later. 
    V_modifier = (1 / HatHeight ) * ZoomFactor

    #calculate the newsize of the zoomed screen cap
    NewHeight = round(HatHeight * V_modifier)
    NewWidth  = round(HatWidth * H_modifier)

    HIndentFactor = (HatWidth / 2)  - (NewWidth /2)
    VIndentFactor = (HatHeight / 2) - (NewHeight /2)
  else:
    IndentFactor = 0



#  for V in range(max(math.floor((0 + V_modifier * 2) ),0) ,min(math.floor((HatHeight - V_modifier * 2) ),HatHeight-1)) :
#    for H in range (max(math.floor((0 + H_modifier * 4)),0),min(math.floor((HatWidth - H_modifier * 4) ),HatWidth-1)):
  for V in range(0,HatHeight):
    for H in range (0,HatWidth):
      if (CheckBoundary((H * H_modifier) + HIndentFactor ,(V * V_modifier) + VIndentFactor) == 0):
      
        r,g,b = ScreenCap[V][H]
        if (ZoomFactor > 0):
          Canvas.SetPixel((H * H_modifier) + HIndentFactor ,(V * V_modifier) + VIndentFactor,r,g,b)
        
        else:
          Canvas.SetPixel(H,V,r,g,b)

  TheMatrix.SwapOnVSync(Canvas)
        
  
  #unicorn.show()




  
    
def ScrollScreenScrollBanner(message,r,g,b,direction,speed):

  # this has been converted from an older way of scrolling.  
  # we might need to input multiple directions to give more flexibility
  
  
  ScreenCap  = copy.deepcopy(unicorn.get_pixels())
  ScrollScreen('up',ScreenCap,speed)

  af.ShowScrollingBanner(message,r,g,b,speed)

  TheTime.ScrollAcrossScreen(0,1,"right",speed)
  ScrollScreen('down',ScreenCap,speed)










def PointTowardsObjectH(Source, Target):

#     1 
#   4   2
#     3

  #Source is to the left of target
  if (Source.h < Target.h and Source.direction == 4) or (Source.h > Target.h and Source.direction == 2):
    Source.direction = ReverseDirection(Source.direction)

  return;
  

def GetDistanceBetweenDots(h1,v1,h2,v2):
  a = abs(h1 - h2)
  b = abs(v1 - v2)
  c = math.sqrt(a**2 + b**2)

  return c;  
      


def ShowIPAddress(Wait=5):
  message = str(subprocess.check_output("hostname -I", shell=True)[:-1]);
  
  IPAddress = message[2:17]

  #cut off at trailing space, if it exists
  i = message.find(" ")
  print("Space detected:",i)
  if(i >1):
    IPAddress = IPAddress[0:i-1]

  print ("-->",IPAddress,"<--") 

  CursorH = 0
  CursorV = 0
  
  #not really used here
  ScreenArray  = ([[]])
  ScreenArray  = [[ (0,0,0) for i in range(HatWidth)] for i in range(HatHeight)]

  ScreenArray,CursorH,CursorV = TerminalScroll(ScreenArray,"Your IP Address:" ,CursorH=CursorH,CursorV=CursorV,MessageRGB=(200,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)
  ScreenArray,CursorH,CursorV = TerminalScroll(ScreenArray,IPAddress ,CursorH=CursorH,CursorV=CursorV,MessageRGB=(0,200,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)

  #print dots on the same line
  V = CursorV
  
  #duplicate this underscore WAIT number of times
  #message = '_' * Wait
  #One second between each letter
  #print(message)
  #ScreenArray,CursorH,CursorV = TerminalScroll(ScreenArray,message,CursorH=CursorH,CursorV=V,MessageRGB=(0,200,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=1,ScrollSpeed=ScrollSleep)
  
  BlinkCursor(CursorH= CursorH,CursorV=CursorV,CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),BlinkSpeed=0.5,BlinkCount=Wait)



  return IPAddress















def ShowGlowingText(
    h          = -1,            #horizontal placement of upper left corner of text banner
    v          = -1,            #vertical   placement of upper left corner of text banner
    Text       = 'Test',        #Text messatge to display (make sure it fits!)
    RGB        = (100,100,100), #color value of the text
    ShadowRGB  = (20,20,20),    #color value of the shadow
    ZoomFactor = 2,             #scale the text (1=normal, 2=twice the size, etc.)
    GlowLevels = 200,           #how many brightness increments to show the text
    DropShadow = True,          #show a drop shadow of the text
    CenterHoriz = False,        #center text horizontally, overrides H
    CenterVert  = False,        #center text vertically, overrides V
    FadeLevels  = 0,            #Fade the text in this many brightness decrements
    FadeDelay   = 0.25         #How long to keep text on screen before fading

  ):

  global ScreenArray

  r,g,b = RGB 
  r2 = 0
  g2 = 0
  b2 = 0
  Text      = Text.upper()
  TheBanner = CreateBannerSprite(Text)
  

  #Center if HV not specified
  if (CenterHoriz == True):
    h = (HatWidth // 2)  - ((TheBanner.width * ZoomFactor) // 2) - ZoomFactor
  if (CenterVert  == True):
    v = (HatHeight // 2) - ((TheBanner.height * ZoomFactor) // 2) - ZoomFactor
  #Draw Shadow Text
  if(DropShadow == True):
    CopySpriteToPixelsZoom(TheBanner,h-1,v+1,ShadowRGB,(0,0,0),ZoomFactor,Fill=False)

                                    
  if (GlowLevels > 0):
    for i in range (1,GlowLevels):
      r2 = math.ceil((r / GlowLevels) * i)
      g2 = math.ceil((g / GlowLevels) * i)
      b2 = math.ceil((b / GlowLevels) * i)
      CopySpriteToPixelsZoom(TheBanner,h,v,(r2,g2,b2),(0,0,0),ZoomFactor,Fill=False)

  #Draw text
  CopySpriteToPixelsZoom(TheBanner,h,v,(r,g,b),(0,0,0),ZoomFactor,Fill=False)


  #Fade away!
  if (FadeLevels > 0):
    time.sleep(FadeDelay)
    if(DropShadow == True):
      CopySpriteToPixelsZoom(TheBanner,h-1,v+1,(0,0,0),(0,0,0),ZoomFactor,Fill=False)

    for i in range (FadeLevels,0,-1):
      r2 = math.ceil((r / GlowLevels) * i)
      g2 = math.ceil((g / GlowLevels) * i)
      b2 = math.ceil((b / GlowLevels) * i)
      CopySpriteToPixelsZoom(TheBanner,h,v,(r2,g2,b2),(0,0,0),ZoomFactor,Fill=False)
    #erase remnants
    CopySpriteToPixelsZoom(TheBanner,h,v,(0,0,0),(0,0,0),ZoomFactor,Fill=False)
    CopySpriteToPixelsZoom(TheBanner,h-1,v+1,(0,0,0),(0,0,0),ZoomFactor,Fill=False)


  return   




def ShowGlowingSprite(
    h          = -1,                #horizontal placement of upper left corner of text banner
    v          = -1,                #vertical   placement of upper left corner of text banner
    TheSprite  = ExclamationSprite, #Text message to display (make sure it fits!)
    RGB        = HighRed,
    ShadowRGB  = ShadowRed,         #color value of the shadow
    ZoomFactor = 2,                 #scale the text (1=normal, 2=twice the size, etc.)
    GlowLevels = 200,               #how many brightness increments to show the text
    DropShadow = True,          #show a drop shadow of the text
    CenterHoriz = False,        #center text horizontally, overrides H
    CenterVert  = False,        #center text vertically, overrides V
    FadeLevels  = 0,            #Fade the text in this many brightness decrements
    FadeDelay   = 0.25          #How long to keep text on screen before fading
  ):

  #Note: alphanumeric sprites have RGB = 0, so you need to pass in the desired RGB

  global ScreenArray

  r,g,b = (RGB)
  r2 = 0
  g2 = 0
  b2 = 0
    

  #Center if HV not specified
  if (CenterHoriz == True):
    h = (HatWidth // 2)  - ((TheSprite.width * ZoomFactor) // 2) - ZoomFactor
  if (CenterVert  == True):
    v = (HatHeight // 2) - ((TheSprite.height * ZoomFactor) // 2) - ZoomFactor
  #Draw Shadow Text
  if(DropShadow == True):
    CopySpriteToPixelsZoom(TheSprite,h-1,v+1,ShadowRGB,(0,0,0),ZoomFactor,Fill=False)

                                    
  if (GlowLevels > 0):
    for i in range (1,GlowLevels):
      r2 = math.ceil((r / GlowLevels) * i)
      g2 = math.ceil((g / GlowLevels) * i)
      b2 = math.ceil((b / GlowLevels) * i)
      CopySpriteToPixelsZoom(TheSprite,h,v,(r2,g2,b2),(0,0,0),ZoomFactor,Fill=False)

  #Draw Sprite
  CopySpriteToPixelsZoom(TheSprite,h,v,RGB,(0,0,0),ZoomFactor,Fill=False)


  #Fade away!
  if (FadeLevels > 0):
    time.sleep(FadeDelay)
    if(DropShadow == True):
      CopySpriteToPixelsZoom(TheSprite,h-1,v+1,(0,0,0),(0,0,0),ZoomFactor,Fill=False)

    for i in range (FadeLevels,0,-1):
      r2 = math.ceil((r / GlowLevels) * i)
      g2 = math.ceil((g / GlowLevels) * i)
      b2 = math.ceil((b / GlowLevels) * i)
      CopySpriteToPixelsZoom(TheSprite,h,v,(r2,g2,b2),(0,0,0),ZoomFactor,Fill=False)
    #erase remnants
    CopySpriteToPixelsZoom(TheSprite,h,v,(0,0,0),(0,0,0),ZoomFactor,Fill=False)
    CopySpriteToPixelsZoom(TheSprite,h-1,v+1,(0,0,0),(0,0,0),ZoomFactor,Fill=False)

 
  return   





def CopySpriteToPixelsZoom(TheSprite,h,v, ColorTuple=(-1,-1,-1),FillerTuple=(-1,-1,-1),ZoomFactor = 1,Fill=True):
  #Copy a regular sprite to the LED 
  #Apply a ZoomFactor i.e  1 = normal / 2 = double in size / 3 = 3 times the size
  #print ("Copying sprite to playfield:",TheSprite.name, ObjectType, Filler)
  #if Fill = False, don't write anything for filler, that way we can leave existing lights on LED


 
  

  width   = TheSprite.width 
  height  = TheSprite.height

  #global ScreenArray  
  
  if (ColorTuple == (-1,-1,-1)):
    r = TheSprite.r
    g = TheSprite.g
    b = TheSprite.b
  else:
    r,g,b   = ColorTuple
  
  if (FillerTuple == (-1,-1,-1)):
    fr = 0
    fg = 0
    fb = 0
  else:
    fr,fg,fb   = FillerTuple


  #Copy sprite to LED pixels
  for count in range (0,(TheSprite.width * TheSprite.height) ):
    y,x = divmod(count,TheSprite.width)

    y = y * ZoomFactor
    x = x * ZoomFactor


    if (ZoomFactor >= 1):
      for zv in range (0,ZoomFactor):
        for zh in range (0,ZoomFactor):
          H = x+h+zh
          V = y+v+zv
         
          if(CheckBoundary(H,V) == 0):

            #draw the sprite portion
            if TheSprite.grid[count] != 0:
              #Canvas.SetPixel(H,V,r,g,b)
              #ScreenArray[V][H]=(r,g,b)
              setpixel(H,V,r,g,b)
            # if the sprite portion is a 0
            else:
              if (Fill == True):
                #Canvas.SetPixel(H,V,fr,fg,fb)
                #ScreenArray[V][H]=(fr,fg,fb)
                setpixel(H,V,fr,fg,fb)
              #else:
              #  setpixel(H,V,0,0,0)

  #draw the contents of the buffer to the LED matrix
  #Canvas = TheMatrix.SwapOnVSync(Canvas)
  
 

  return;



def CopySpriteToCanvasZoom(TheSprite,h,v, ColorTuple=(-1,-1,-1),FillerTuple=(-1,-1,-1),ZoomFactor = 1,Fill=True,Canvas=None):
  #Copy a regular sprite to the LED 
  #Apply a ZoomFactor i.e  1 = normal / 2 = double in size / 3 = 3 times the size
  #print ("Copying sprite to playfield:",TheSprite.name, ObjectType, Filler)
  #if Fill = False, don't write anything for filler, that way we can leave existing lights on LED

  width   = TheSprite.width 
  height  = TheSprite.height

  
  if (ColorTuple == (-1,-1,-1)):
    r = TheSprite.r
    g = TheSprite.g
    b = TheSprite.b
  else:
    r,g,b   = ColorTuple
  
  if (FillerTuple == (-1,-1,-1)):
    fr = 0
    fg = 0
    fb = 0
  else:
    fr,fg,fb   = FillerTuple


  #Copy sprite to Canvas
  for count in range (0,(TheSprite.width * TheSprite.height) ):
    y,x = divmod(count,TheSprite.width)

    y = y * ZoomFactor
    x = x * ZoomFactor


    if (ZoomFactor >= 1):
      for zv in range (0,ZoomFactor):
        for zh in range (0,ZoomFactor):
          H = x+h+zh
          V = y+v+zv
         
          if(CheckBoundary(H,V) == 0):

            #draw the sprite portion
            if TheSprite.grid[count] != 0:
              Canvas.SetPixel(H,V,r,g,b)
              #ScreenArray[V][H]=(r,g,b)
              #setpixel(H,V,r,g,b)
            # if the sprite portion is a 0
            else:
              if (Fill == True):
                Canvas.SetPixel(H,V,fr,fg,fb)
                #ScreenArray[V][H]=(fr,fg,fb)
                #setpixel(H,V,fr,fg,fb)
              #else:
              #  setpixel(H,V,0,0,0)

  return Canvas;








#def CopyPlayfieldToCanvas(Playfield,h,v,Canvas=None):
#  #Copy a section of the Playfield to the canvas
#
#  #Copy sprite to Canvas
#  for x in range (0,HatWidth ):
#    for y in range (0,HatHeight):
#      rgb = Playfield[y+v][x+h] 
#    
#  return Canvas;











def CopySpriteToScreenArrayZoom(TheSprite,h,v, ColorTuple=(-1,-1,-1),FillerTuple=(-1,-1,-1),ZoomFactor = 1,Fill=True,InputScreenArray=None):
  #Copy a regular sprite to the ScreenArray buffer
  #Apply a ZoomFactor i.e  1 = normal / 2 = double in size / 3 = 3 times the size
  #print ("Copying sprite to playfield:",TheSprite.name, ObjectType, Filler)
  #if Fill = False, don't write anything for filler, that way we can leave existing lights on LED

  h = round(h)
  v = round(v)

  width   = TheSprite.width 
  height  = TheSprite.height

  if InputScreenArray is None:
    #print("InputScreenArray is None")
    ScreenArray  = ([[]])
    ScreenArray  = [[ (0,0,0) for i in range(HatWidth)] for i in range(HatHeight)]
  else:
    #print("Applying new sprite to existing ScreenArray")
    ScreenArray = InputScreenArray
  
  if (ColorTuple == (-1,-1,-1)):
    r = TheSprite.r
    g = TheSprite.g
    b = TheSprite.b
  else:
    r,g,b   = ColorTuple
  
  if (FillerTuple == (-1,-1,-1)):
    fr = 0
    fg = 0
    fb = 0
  else:
    fr,fg,fb   = FillerTuple


  #Copy sprite to Screen Array
  for count in range (0,(TheSprite.width * TheSprite.height) ):
    y,x = divmod(count,TheSprite.width)

    y = y * ZoomFactor
    x = x * ZoomFactor


    if (ZoomFactor >= 1):
      for zv in range (0,ZoomFactor):
        for zh in range (0,ZoomFactor):
          H = x+h+zh
          V = y+v+zv
          
          if(CheckBoundary(H,V) == 0):

            #draw the sprite portion
            if TheSprite.grid[count] != 0:
              ScreenArray[V][H]=(r,g,b)
            # if the sprite portion is a 0
            #else:
            #  if (Fill == True):
            #    ScreenArray[V][H]=(fr,fg,fb)
            #  else:
            #    setpixel(H,V,0,0,0)

  return ScreenArray
 





def CopyAnimatedSpriteToPixelsZoom(TheSprite,h,v, ZoomFactor = 1):
  #Copy a color animated sprite to the LED and the ScreenArray buffer
  #Apply a ZoomFactor i.e  1 = normal / 2 = double in size / 3 = 3 times the size

  h = round(h)
  v = round(v)


  width   = TheSprite.width 
  height  = TheSprite.height

  #global ScreenArray  
  
  TheFrame = TheSprite.currentframe
  #Copy sprite to LED pixels
  for count in range (0,(TheSprite.width * TheSprite.height)):
    y,x = divmod(count,TheSprite.width)

    y = y * ZoomFactor
    x = x * ZoomFactor


    if (ZoomFactor >= 1):
      for zv in range (0,ZoomFactor):
        for zh in range (0,ZoomFactor):
          H = x+h+zh
          V = y+v+zv


          if(CheckBoundary(H,V) == 0):
            r,g,b =  ColorList[TheSprite.grid[TheFrame][count]]

            #Experimental method to only draw if the sprite is non black, and to fill in the spot with the 
            #the screenArray (our manual copy of the screen) if it is black which prevents the background from getting erased
            if (r >0 or g > 0 or b > 0):
              setpixel(H,V,r,g,b)
              

            else:
              r2,g2,b2 = TheSprite.ScreenArray[V][H]
              setpixel(H,V,r2,g2,b2)
              


  

  # We used to auto-increment but t his causes problems
  #TheFrame = TheFrame + 1
  #if (TheFrame > TheSprite.frames):
  #  TheFrame = 1
  #
  #TheSprite.currentframe = TheFrame

  return;




def CopyAnimatedSpriteToPixelsZoomLEDOnly(TheSprite,h,v, ZoomFactor = 1):
  #Copy a color animated sprite to the LED ONLY
  #Apply a ZoomFactor i.e  1 = normal / 2 = double in size / 3 = 3 times the size

  h = round(h)
  v = round(v)


  width   = TheSprite.width 
  height  = TheSprite.height

  #global ScreenArray  
  
  TheFrame = TheSprite.currentframe
  #Copy sprite to LED pixels
  for count in range (0,(TheSprite.width * TheSprite.height)):
    y,x = divmod(count,TheSprite.width)

    y = y * ZoomFactor
    x = x * ZoomFactor


    if (ZoomFactor >= 1):
      for zv in range (0,ZoomFactor):
        for zh in range (0,ZoomFactor):
          H = x+h+zh
          V = y+v+zv


          if(CheckBoundary(H,V) == 0):
            r,g,b =  ColorList[TheSprite.grid[TheFrame][count]]

            #Experimental method to only draw if the sprite is non black, and to fill in the spot with the 
            #the screenArray (our manual copy of the screen) if it is black which prevents the background from getting erased
            if (r >0 or g > 0 or b > 0):
              setpixelLEDOnly(H,V,r,g,b)

            else:
              r2,g2,b2 = TheSprite.ScreenArray[V][H]
              setpixelLEDOnly(H,V,r2,g2,b2)


  

  # We used to auto-increment but t his causes problems
  #TheFrame = TheFrame + 1
  #if (TheFrame > TheSprite.frames):
  #  TheFrame = 1
  #
  #TheSprite.currentframe = TheFrame

  return;




def CopyAnimatedSpriteToScreenArrayZoom(TheSprite,h,v, ZoomFactor = 1,TheScreenArray = [[]]):
  #Copy a color animated sprite to the a ScreenArray
  #Apply a ZoomFactor i.e  1 = normal / 2 = double in size / 3 = 3 times the size

  h = round(h)
  v = round(v)

  width   = TheSprite.width 
  height  = TheSprite.height

  #global ScreenArray  
  
  TheFrame = TheSprite.currentframe
  #Copy sprite ScreenArray
  for count in range (0,(TheSprite.width * TheSprite.height)):
    y,x = divmod(count,TheSprite.width)

    y = y * ZoomFactor
    x = x * ZoomFactor


    if (ZoomFactor >= 1):
      for zv in range (0,ZoomFactor):
        for zh in range (0,ZoomFactor):
          H = x+h+zh
          V = y+v+zv


          if(CheckBoundary(H,V) == 0):
            r,g,b =  ColorList[TheSprite.grid[TheFrame][count]]

            #Experimental method to only draw if the sprite is non black, and to fill in the spot with the 
            #the screenArray (our manual copy of the screen) if it is black which prevents the background from getting erased
            if (r >0 or g > 0 or b > 0):
              
              TheScreenArray[V][H] = r,g,b

  return TheScreenArray


  

def CopyAnimatedSpriteZoom(TheSprite,ZoomFactor = 2):
  #Copy a color animated sprite with the specified zoom level
  #Apply a ZoomFactor i.e  1 = normal / 2 = double in size / 3 = 3 times the size

  h      = 0
  v      = 0
  NewHeight = TheSprite.height * ZoomFactor
  NewWidth  = TheSprite.width  * ZoomFactor
  frames    = TheSprite.frames
  OldGridCount = TheSprite.height * TheSprite.width
  
  NewSprite = ColorAnimatedSprite(
      h = 0, 
      v = 0, 
      name   = TheSprite.name, 
      width  = NewWidth,
      height = NewHeight, 
      frames = frames,
      framerate = TheSprite.framerate,
      grid = []
    )

  


  #the new grid is messed up




  #initialize new sprite grid
  #NewSprite.grid  = [[ (0) for i in range(NewWidth * NewHeight)] for i in range(frames)]
  #NewSprite.grid  = [[ (0) for i in range()] for i in range(3)]
  NewSprite.grid   = [[]]
  #print(NewSprite.grid)

  '''
  Original
    [1][2]        = [1][2][3][4]
    [3][4]

  New
    [1][1][2][2] = [1][1][2][2][1][1][2][2][3][3][4][4][3][3][4][4]
    [1][1][2][2]
    [3][3][4][4]
    [3][3][4][4]

    

  '''




  #Frame 0 is empty in ColorAnimatedSprites  
  for f in range (1,frames+1):
    # The sprite is stored in 2D array
    print("frame:",f)

    Array1 = []
    Array2 = []    

    #work through array in original sprite
    #and add double the characters to a new array
    for i in range (0,TheSprite.height * TheSprite.width ):

      Array1.append(TheSprite.grid[f][i])   
      Array1.append(TheSprite.grid[f][i])   
      Array2.append(TheSprite.grid[f][i])   
      Array2.append(TheSprite.grid[f][i])   
      #print(i)
      #NewSprite.grid[f][i]                              = TheSprite.grid[f][i] 
      #NewSprite.grid[f][i+1]                            = TheSprite.grid[f][i] 
      #NewSprite.grid[f][i + TheSprite.width * Zoom]     = TheSprite.grid[f][i] 
      #NewSprite.grid[f][i + TheSprite.width * Zoom + 1] = TheSprite.grid[f][i] 

    
    Array2 = Array1 + Array2
    
    print (TheSprite.grid[f])
    print (Array2)

    #NewSprite.grid[f] = Array2
    NewSprite.grid.append(Array2)
    #take the new array and double it
    #for i in range (0,len(Array1)):
    #  Array2.append(Array1[i])
    

  return NewSprite;















def DisplayScore(score,rgb):

  r,g,b = rgb

  ScoreSprite = CreateBannerSprite(str(score))
  ScoreH      = HatWidth  - ScoreSprite.width
  ScoreV      = HatHeight - ScoreSprite.height
  ScoreSprite.r = r
  ScoreSprite.g = g
  ScoreSprite.b = b
  ScoreSprite.DisplayIncludeBlack(ScoreH,ScoreV)



def DisplayScoreMessage(h=0,v=0,Message='TEST',RGB=(100,100,100),FillerRGB=(0,0,0)):

  r,g,b    = RGB
  fr,fg,fb = FillerRGB
  ScoreH   = h
  ScoreV   = v



  #Display a message where the scoreboard is (lower right corner)
  ScoreMessage = CreateBannerSprite(str(Message.upper()))
  
  if (ScoreH == 0):
    ScoreH      = (HatWidth  - ScoreMessage.width) // 2
  if (ScoreV == 0):
    ScoreV      = HatHeight - ScoreMessage.height
  ScoreMessage.r = r
  ScoreMessage.g = g
  ScoreMessage.b = b
  #ScoreMessage.DisplayIncludeBlack(ScoreH,ScoreV)
  CopySpriteToPixelsZoom(ScoreMessage,ScoreH,ScoreV, ColorTuple=(RGB),FillerTuple=(FillerRGB),ZoomFactor = 1,Fill=True)




def DisplayLevel(level,rgb):

  r,g,b = rgb

  ScoreSprite = CreateBannerSprite(str(level))
  ScoreH      = HatWidth  - 33
  ScoreV      = HatHeight - ScoreSprite.height
  ScoreSprite.r = r
  ScoreSprite.g = g
  ScoreSprite.b = b
  ScoreSprite.DisplayIncludeBlack(ScoreH,ScoreV)








  



def GetElapsedSeconds(starttime):
  elapsed_seconds = time.time() - starttime
  return elapsed_seconds





def TronGetRandomMessage(MessageType = 'TAUNT'):
  

  if (MessageType == 'TAUNT'):
    MessageList = ('NICE TRY',
                   'YOU FAIL',
                   'NOOOO!',
                   'HA HA!',
                   'AGAIN ?',
                   'LOSER!',
                   'YOU LOSE',
                   'YOU DIED',
                   'PLAYER!!!',
                   'GOT EM',
                   'THEY ESCAPED!',
                   'AFTER THEM!',
                   'YOU WILL FAIL',
                   'FIX THAT WALL',
                   'WHAT???',
                   'NEVER GIVE UP',
                   'THAT STINKS!',
                   'SYNTAX ERROR',
                   'NOT NICE!',
                   'STOPSTOPSTOP',
                   'ILLEGAL STOP',
                   'FULL STOP',
                   'DO NOT RUN',
                   'BUT WHY?',
                   'THAT WAS FUN',
                   'TRY AGAIN?',
                   'COME BACK!',
                   'NO ESCAPE',
                   'NOT TODAY!',
                   'GET THEM',
                   'ALERT!',
                   'IS IT SAFE?',
                   'MISSED IT BY THAT MUCH!',
                   'YOUR LACK OF SKILL DISTURBS ME'

                   
      )
  elif (MessageType == 'CHALLENGE'):
    MessageList = ('DO YOU FIGHT FOR THE PLAYER?',
                   'DO YOU FIGHT FOR MCP?',
                   'WELCOME TO THE CIRCUITBOARD',
                   'ARE YOU A USER?',
                   'ARE YOU READY FOR THE CHALLENGE?',
                   'WITNESS THE MIGHT OF MCP!',
                   'GET YOUR JETBIKE READY',
                   'RUN HIM INTO THE JETWALLS!',
                   'THIS CLOCK IS FULLY ARMED AND OPERATIONAL',
                   'SIT FACING THE SCREEN LOGAN 5',
                   'GET READY',
                   'DESERVE VICTORY!',
                   'FIGHT FOR THE USER!',
                   'FIGHT FOR MCP!',
                   'THERE IS NO SANCTUARY...',
                   'SOYLENT GREEN IS....TASTY!',
                   'THIS IS NOT AN ALERT',
                   'WELCOME TO THE REAL WORLD NEO',
                   'PREPARE YOURSELF FOR BATTLE!',
                   'GET ON YOUR BIKES AND RIDE!',
                   'ANOTHER WARRIOR FOR MY AMUSEMENT!',
                   'DO YOU DARE TO ENTER THE ARENA?',
                   'YOUR JET BIKE HAS A FLAT TIRE',
                   'DO YOU HAVE TIME FOR A GAME?',
                   'HOW ABOUT A GAME OF THERMONUCLEAR WAR?',
                   'TODAY IS A GOOD DAY TO WATCH A CLOCK',
                   'WELCOME TO THUNDERDOME',
                   'DONT CHANGE THAT DIAL!',
                   'THIS IS A TRANSMISSION FROM THE FUTURE',
                   'IMAGINE IF YOU WILL A CLOCK THAT COULD PLAY GAMES',
                   'IS IT THAT TIME AGAIN?',
                   'PREVIOUSLY ON CLOCK...',
                   'THANKS FOR TUNING IN',
                   'YOU WONT BELIEVE WHAT HAPPENS NEXT',
                   'MISSED IT BY THAT MUCH!',
                   'CAN YOU DIG IT?',
                   'IM BACK BABY'
                   
      )
                   
  elif (MessageType == 'SHORTGAME'):
    #12 characters
    MessageList = ('A DOT GAME',
                   'REIMAGINED',
                   'BY DATAGOD',
                   'AN ODDITY',
                   'A CLOCK GAME',
                   'RGB MATRIX',
                   'A FUN PROJECT',
                   'ON YOUR CLOCK',
                   'FUN TIMES',
                   'PI POWERED',
                   'BLOW YER MIND',
                   'ULTIMATE TIME',
                   'TIME SQUARED',
                   'ITS ABOUT TIME',
                   'TIME TO RUN',
                   'END TIMES',
                   'NO TIME LEFT',
                   'SHOW TIME!',
                   'OUTTA TIME!',
                   'KNOCK KNOCK!',
                   'READY?',
                   'GO!'

      )
  
  
  ListCount = len(MessageList)
  print(ListCount)
  print("ListCount:",ListCount)
  i = 0
  Message = ''
  #Message = MessageList(random.randint(0,ListCount-1))
  Message = random.choice(MessageList)
  print("Message:",Message)
  return Message




def EraseMessageArea(LinesFromBottom = 5):
  for x in range (0,HatWidth):
    for y in range (HatHeight-LinesFromBottom,HatHeight):
      setpixel(x,y,0,0,0)



def IsSpotEmpty(h,v):
  r,g,b = getpixel(h,v)
  if (r > 0 or g > 0 or b > 0):
    return False
  else:
    return True


  
def GetBrightAndShadowRGB():
  #get a bright color and find a shadow that is one 20th the brightness
  i = random.randint(1,7)
  BrightRGB = GlowingTextRGB[i]
  ShadowRGB = GlowingShadowRGB[i]

  return BrightRGB, ShadowRGB






def ShowTitleScreen(
  BigText          = 'BIGTEXT',
  BigTextRGB       = HighBlue,
  BigTextShadowRGB = ShadowBlue,

  LittleText          = 'LITTLE TEXT',
  LittleTextRGB       = HighRed,
  LittleTextShadowRGB = ShadowRed, 
  
  ScrollText     = 'SCROLLING TEXT',
  ScrollTextRGB  = HighYellow,
  ScrollSleep    = 0.05,    #how long to wait between each frame of scrolling
  DisplayTime    = 5,       #how long to wait before exiting
  ExitEffect     = 0,
  BigTextZoom    = 2,
  LittleTextZoom = 1,

  BigText2          = '',
  BigText2RGB       = HighBlue,
  BigText2ShadowRGB = ShadowBlue

  ):


  global ScreenArray  
    
  
  #Draw the Big text
  #Clear only the LED matrix
  #Draw the next size down
  #When at the final zoom level
  #  - clear the LED Matrix
  #  - clear all buffers (canvas and ScreenArray[V][H])
  #  - draw the text at desired last zoom level
  #  - draw the rest of the text, at this point it is all written to ArrayBuffer
  #  - clear the LED Matrix
  #  - clear all buffers (canvas and ScreenArray[V][H])
  #Call the ZoomScreen function to redraw the display using ScreenArray[V][H] which at this point
  #contains the values last written to the screen.

  BigText    = BigText.upper()
  BigText2   = BigText2.upper()
  LittleText = LittleText.upper()
  ScrollText = ScrollText.upper()

  
  #We want to capture what is on the screen before we start drawing, that way we can transition back to it nicely
  ScreenArrayBefore = copy.deepcopy(ScreenArray)

  TheMatrix.Clear()
  ClearBuffers()
  


  #Big Text
  TheMatrix.Clear()
  ShowGlowingText(CenterHoriz=True,CenterVert=False,h=0,v=0,Text=BigText,RGB=BigTextRGB,ShadowRGB=BigTextShadowRGB,ZoomFactor= 8,GlowLevels=0,DropShadow=False)
  TheMatrix.Clear()
  ShowGlowingText(CenterHoriz=True,CenterVert=False,h=0,v=1,Text=BigText,RGB=BigTextRGB,ShadowRGB=BigTextShadowRGB,ZoomFactor= 7,GlowLevels=0,DropShadow=False)
  TheMatrix.Clear()
  ShowGlowingText(CenterHoriz=True,CenterVert=False,h=0,v=1,Text=BigText,RGB=BigTextRGB,ShadowRGB=BigTextShadowRGB,ZoomFactor= 6,GlowLevels=0,DropShadow=False)
  TheMatrix.Clear()
  ShowGlowingText(CenterHoriz=True,CenterVert=False,h=0,v=1,Text=BigText,RGB=BigTextRGB,ShadowRGB=BigTextShadowRGB,ZoomFactor= 5,GlowLevels=0,DropShadow=False)
  TheMatrix.Clear()
  ShowGlowingText(CenterHoriz=True,CenterVert=False,h=0,v=1,Text=BigText,RGB=BigTextRGB,ShadowRGB=BigTextShadowRGB,ZoomFactor= 4,GlowLevels=0,DropShadow=False)
  TheMatrix.Clear()
  ShowGlowingText(CenterHoriz=True,CenterVert=False,h=0,v=1,Text=BigText,RGB=BigTextRGB,ShadowRGB=BigTextShadowRGB,ZoomFactor= 3,GlowLevels=0,DropShadow=False)
  TheMatrix.Clear()
  ClearBuffers() #We do this to erase our ScreenArray (which we draw to manually because we cannot read the matrix as a whole)
  ShowGlowingText(CenterHoriz=True, CenterVert=False, h=0, v=1, Text=BigText, RGB=BigTextRGB, ShadowRGB=BigTextShadowRGB,ZoomFactor= BigTextZoom,GlowLevels=0,DropShadow=True)
  

  time.sleep(0.5)


  #BigText2 or LittleText
  if (BigText2 == ''):
    #Little Text
    v = BigTextZoom * 7 
    ShowGlowingText(CenterHoriz=True,h=0,v=v,Text=LittleText,RGB=LittleTextRGB,ShadowRGB=LittleTextShadowRGB,ZoomFactor= LittleTextZoom,GlowLevels=100,DropShadow=True)
  else:
    #BigText2
    ShowGlowingText(CenterHoriz = True,h = 0 ,v = 12,  Text = BigText2,  RGB = BigText2RGB,     ShadowRGB = BigText2ShadowRGB,    ZoomFactor = 2,GlowLevels=50,DropShadow=True)


  #Scrolling Message
  EraseMessageArea(LinesFromBottom=6)
  BrightRGB, ShadowRGB = GetBrightAndShadowRGB()
  ShowScrollingBanner2(ScrollText,ScrollTextRGB,ScrollSpeed=ScrollSleep,v=26)



  time.sleep(DisplayTime)

  #Pick a random special affect
 
  if(ExitEffect == -1):
    print("No effect")

  elif(ExitEffect == 0):
    r = random.randint(0,5)
    if (r == 0):
      #Zoom out
      #print('Random Zoom out')
      ZoomScreen(ScreenArray,32,256,Fade=True,ZoomSleep=0.01)
    elif (r == 1):
      #Shrink
      #print('Random Shrink')
      ZoomScreen(ScreenArray,32,1,Fade=True,ZoomSleep=0.01)
    elif (r == 2):
      #Bounce1
      #print('Random Bounce1')
      ZoomScreen(ScreenArray,32,5,Fade=False,ZoomSleep=0.005)
      ZoomScreen(ScreenArray,6,128,Fade=True,ZoomSleep=0)
    elif (r == 3):
      #Bounce2
      #print('Random Bounce2')
      ZoomScreen(ScreenArray,32,42,Fade=False,ZoomSleep=0.015)
      ZoomScreen(ScreenArray,42,1,Fade=True,ZoomSleep=0.0)

    elif (r == 4):
      #print('Fade')
      ScreenArray2  = ([[]])
      ScreenArray2  = [[ (0,0,0) for i in range(HatWidth)] for i in range(HatHeight)]
      TransitionBetweenScreenArrays(ScreenArray,ScreenArray2,TransitionType=1)

    elif (r == 5):
      #print('FallingSand')
      ScreenArray2  = ([[]])
      ScreenArray2  = [[ (0,0,0) for i in range(HatWidth)] for i in range(HatHeight)]
      TransitionBetweenScreenArrays(ScreenArray,ScreenArray2,TransitionType=2)



  elif(ExitEffect == 1):
      #Shrink
      print('Shrink')
      ZoomScreen(ScreenArray,32,1,Fade=True,ZoomSleep=0.01)
  elif(ExitEffect == 2):
      #Zoom out
      print('Zoom out')
      ZoomScreen(ScreenArray,32,256,Fade=True,ZoomSleep=0.01)

  elif(ExitEffect == 3):
      #Bounce
      print('Bounce')
      ZoomScreen(ScreenArray,32,10,Fade=False,ZoomSleep=0.005)
      ZoomScreen(ScreenArray,11,128,Fade=True,ZoomSleep=0)

  elif(ExitEffect == 4):
      print("Fade")
      ScreenArray2  = ([[]])
      ScreenArray2  = [[ (0,0,0) for i in range(HatWidth)] for i in range(HatHeight)]
      TransitionBetweenScreenArrays(ScreenArray,ScreenArray2,TransitionType=1)

  elif(ExitEffect == 5):
      print("FallingSand")
      ScreenArray2  = ([[]])
      ScreenArray2  = [[ (0,0,0) for i in range(HatWidth)] for i in range(HatHeight)]
      TransitionBetweenScreenArrays(ScreenArray,ScreenArray2,TransitionType=2)



  
  
  #We want to clean up all our display, but then fade back into whatever what before this function was called
  #fade back into the previous display (likely Uptime)
  TheMatrix.Clear()
  BlankScreenArray  = ([[]])
  BlankScreenArray  = [[ (0,0,0) for i in range(HatWidth)] for i in range(HatHeight)]
  TransitionBetweenScreenArrays(OldArray = BlankScreenArray, NewArray = ScreenArrayBefore,TransitionType=1)
  
  
      
    
  

def MoveSpriteAcrossScreen(sprite,Position='bottom',v=0,direction="right",ZoomFactor=1,sleep=0.1):
  #this function is for moving old single color sprites (such as text)
  #note: untested as of OCt 28, 2021
  h = 0
  r = sprite.r
  g = sprite.g
  b = sprite.b

  if (Position == 'bottom'):
    v =  HatHeight - (TheSprite.height * ZoomFactor)
  elif (Position == 'middle'):
    v = (HatHeight / 2)- ((TheSprite.height * ZoomFactor) / 2)


  if (direction == "right"):
    #start the sprite completely of screen
    h = 0 - (TheSprite.width * ZoomFactor)

    while (h <= HatWidth):
      #TheSprite.Erase()
      CopySpriteToPixelsZoom(TheBanner,h-1,v+1,(r,g,b),(0,0,0),ZoomFactor,Fill=False)
      time.sleep(sleep)
      h = h + 1


  if (direction == "left"):
    #start the sprite completely of screen
    h = HatWidth + 1

    while (h >= (0- TheSprite.width)):
      CopySpriteToPixelsZoom(TheBanner,h-1,v+1,(r,g,b),(0,0,0),ZoomFactor,Fill=False)
      time.sleep(sleep)
      h = h - 1





def MoveAnimatedSpriteAcrossScreen(TheSprite,Position='bottom',v=0,direction="right",steps=1,ZoomFactor=1,sleep=0.1):
  #Currently steps controls how many H to move after going through all the frames.
  #This allows a sprite (such as the spider) to move in its frames of animation, then after
  #all frames have been displayed, start at frame 1 after moving.



  TheSprite.ScreenArray = copy.deepcopy(ScreenArray)


  h = 0
  v = 0
  Y = 0

  if (Position == 'bottom'):
    v =  HatHeight - (TheSprite.height * ZoomFactor)
  elif (Position == 'middle'):
    v = (HatHeight / 2)- ((TheSprite.height * ZoomFactor) / 2)
  elif (Position == 'random'):
    Y =  HatHeight - (TheSprite.height * ZoomFactor)
    v = Y - random.randint(0,Y)


  if (direction == "right"):
    #start the sprite completely of screen
    h = 0 - (TheSprite.width * ZoomFactor)

    while (h <= HatWidth):
      for i in range (1,TheSprite.frames+1):
        #TheSprite.Erase()
        TheSprite.currentframe = i
        CopyAnimatedSpriteToPixelsZoom(TheSprite,h=h,v=v, ZoomFactor=ZoomFactor)
        if(sleep > 0):
          time.sleep(sleep)
      h = h + steps



  if (direction == "left"):
    #start the sprite completely of screen
    h = HatWidth + 1

    while (h >= (0- TheSprite.width * ZoomFactor)):
      for i in range (1,TheSprite.frames+1):
        TheSprite.currentframe = i
        CopyAnimatedSpriteToPixelsZoom(TheSprite,h=h,v=v, ZoomFactor=ZoomFactor)
        if(sleep > 0):
          time.sleep(sleep)
      h = h - steps




def MoveAnimatedSpriteAcrossScreenFramesPerStep(TheSprite,Position='bottom',v=0,direction="right",FramesPerStep=2,ZoomFactor=1,sleep=0.1):
  #Show x frames per horizontal step
  #current frame count is incremented in CopyANimatedSpriteToPixelsZoom

  h          = 0,
  FrameCount = 0
  tick       = 0
  v = 0
  Y = 0

  if (Position == 'bottom'):
    v =  HatHeight - (TheSprite.height * ZoomFactor)
  elif (Position == 'middle'):
    v = (HatHeight / 2)- ((TheSprite.height * ZoomFactor) / 2)
  elif (Position == 'random'):
    Y =  HatHeight - (TheSprite.height * ZoomFactor)
    v = Y - random.randint(0,Y)

  TheSprite.ScreenArray = copy.deepcopy(ScreenArray)


  if (direction == "right"):
    #start the sprite completely of screen
    h = 0 - (TheSprite.width * ZoomFactor)

    while (h <= HatWidth):
      for i in range (1,TheSprite.frames+1):
        TheSprite.IncrementFrame()
        CopyAnimatedSpriteToPixelsZoomLEDOnly(TheSprite,h=h,v=v, ZoomFactor=ZoomFactor)
        if(sleep > 0):
          time.sleep(sleep)
  
        tick = tick + 1
        m,r = divmod(tick,FramesPerStep)
        #print("m,r, FramesPerStep, tick",m,r,FramesPerStep,tick)
        if (r==0):
          TheSprite.EraseFrontBackZoom(h,v,Back=True,ZoomFactor=ZoomFactor)
          h = h + 1


  if (direction == "left"):
    #start the sprite completely of screen
    h = HatWidth  + 1


    while (h >= (0- TheSprite.width * ZoomFactor)):
      for i in range (1,TheSprite.frames+1):
        TheSprite.IncrementFrame()
        CopyAnimatedSpriteToPixelsZoomLEDOnly(TheSprite,h=h,v=v, ZoomFactor=ZoomFactor)
        if(sleep > 0):
          time.sleep(sleep)
  
        tick = tick + 1
        m,r = divmod(tick,FramesPerStep)
        if (r==0):
          TheSprite.EraseFrontBackZoom(h,v,Front=True,ZoomFactor=ZoomFactor)
          h = h - 1



def MoveAnimatedSpriteAcrossScreenStepsPerFrame(TheSprite,Position='bottom',Vadjust=0,direction="right",StepsPerFrame=1,ZoomFactor=1,sleep=0.1):
  #Show x frames per horizontal step
  #current frame count is incremented in CopyANimatedSpriteToPixelsZoom

  h          = 0
  FrameCount = 0
  tick       = 0
  v = 0
  Y = 0

  TheSprite.ScreenArray = copy.deepcopy(ScreenArray)


  if (Position == 'top'):
    v =  Vadjust
  elif (Position == 'bottom'):
    v =  HatHeight - (TheSprite.height * ZoomFactor)
  elif (Position == 'middle'):
    v = (HatHeight / 2)- ((TheSprite.height * ZoomFactor) / 2)
  elif (Position == 'random'):
    Y =  HatHeight - (TheSprite.height * ZoomFactor)
    v = Y - random.randint(0,Y)

  v = round(v + Vadjust)
  h = round(h)
  

  oldH = h
  oldV = v

  if (direction == "right"):
    #start the sprite completely of screen

    h = 0 - (TheSprite.width * ZoomFactor)

    while (h <= HatWidth):
      tick = tick + 1
      m,r = divmod(tick,StepsPerFrame)
      if (r==0):
        TheSprite.IncrementFrame()
      TheSprite.EraseFrontBackZoom(oldH,oldV,Back=True,ZoomFactor=ZoomFactor)
      CopyAnimatedSpriteToPixelsZoomLEDOnly(TheSprite,h=h,v=v, ZoomFactor=ZoomFactor)
      if(sleep > 0):
        time.sleep(sleep)
      oldH = h
      oldV = v
      h = h + 1


  if (direction == "left"):
    #start the sprite completely of screen
    h = HatWidth  + 1

    while (h >= (0- TheSprite.width * ZoomFactor)):
      for i in range (1,TheSprite.frames+1):
        tick = tick + 1
        m,r = divmod(tick,StepsPerFrame)
        if (r==0):
          TheSprite.IncrementFrame()
        TheSprite.EraseFrontBackZoom(oldH,oldV,Front=True,ZoomFactor=ZoomFactor)
        CopyAnimatedSpriteToPixelsZoomLEDOnly(TheSprite,h=h,v=v, ZoomFactor=ZoomFactor)
        if(sleep > 0):
          time.sleep(sleep)
        oldH = h
        oldV = v
        h = h - 1


def TurnLeftOrRight8Way(direction):
  WhichWay = random.randint(1,4)
  #print ("WhichWay:",WhichWay)
  if (WhichWay == 1):
    #print ("turning W")
    direction = TurnLeft8Way(direction)
    direction = TurnLeft8Way(direction)
  elif (WhichWay == 2):
    #print ("turning NW")
    direction = TurnLeft8Way(direction)
  elif (WhichWay == 3):
    #print ("turning NE")
    direction = TurnRight8Way(direction)
  elif (WhichWay == 4):
    #print ("turning E")
    direction = TurnRight8Way(direction)
    direction = TurnRight8Way(direction)
    
  return direction;


      
def TurnLeftOrRightTwice8Way(direction):
  WhichWay = random.randint(1,2)
  #print ("WhichWay:",WhichWay)
  if (WhichWay == 1):
    direction = TurnLeft8Way(direction)
    direction = TurnLeft8Way(direction)
  elif (WhichWay == 2):
    direction = TurnRight8Way(direction)
    direction = TurnRight8Way(direction)
    
  return direction;



def TurnLeft(direction):
  #print "ChangeDirection!"
  #print "  old: ",direction
  if direction == 1:
    direction = 4
  elif direction == 2:
    direction = 1
  elif direction == 3:
    direction = 2
  elif direction == 4:
    direction = 3
  #print "  new: ",direction
  return direction;




def TurnRight(direction):
  if direction == 1:
    direction = 2
  elif direction == 2:
    direction = 3
  elif direction == 3:
    direction = 4
  elif direction == 4:
    direction = 1
  #print "  new: ",direction
  return direction;
    

def TurnLeftOrRight(direction):
  WhichWay = random.randint(1,2)
  #print ("WhichWay:",WhichWay)
  if (WhichWay == 1):
    #print ("turning left")
    direction = TurnLeft(direction)
  else:
    #print ("turning right")
    direction = TurnRight(direction)
    
  return direction;





def CalculateDotMovement(h,v,Direction):
  #1N 2E 3S 4W
  if (Direction == 1):
    v = v -1
  if (Direction == 2):
    h = h + 1
  if (Direction == 3):
    v = v + 1
  if (Direction == 4):
    h = h -1
  return h,v;





def ReverseDirection(direction):
  if direction == 1:
    direction = 3
  elif direction == 2:
    direction = 4
  elif direction == 3:
    direction = 1
  elif direction == 4:
    direction = 2
  return direction;



def CalculateDotMovement8Way(h,v,Direction):
  #1N 2NE 3E 4SE 5S 6SW 7W 8NW
  # 8 1 2
  # 7 x 3
  # 6 5 4
  
  if (Direction == 1):
    v = v -1
  if (Direction == 2):
    h = h + 1
    v = v - 1
  if (Direction == 3):
    h = h + 1
  if (Direction == 4):
    h = h + 1
    v = v + 1
  if (Direction == 5):
    v = v + 1
  if (Direction == 6):
    h = h - 1
    v = v + 1
  if (Direction == 7):
    h = h - 1
  if (Direction == 8):
    h = h - 1
    v = v - 1
  return h,v;



def TurnRight8Way(direction):
  if direction == 1:
    direction = 2
  elif direction == 2:
    direction = 3
  elif direction == 3:
    direction = 4
  elif direction == 4:
    direction = 5
  elif direction == 5:
    direction = 6
  elif direction == 6:
    direction = 7
  elif direction == 7:
    direction = 8
  elif direction == 8:
    direction = 1
  #print "  new: ",direction
  return direction;
    

def TurnLeft8Way(direction):
  #print "ChangeDirection!"
  #print "  old: ",direction
  if direction == 1:
    direction = 8
  elif direction == 8:
    direction = 7
  elif direction == 7:
    direction = 6
  elif direction == 6:
    direction = 5
  elif direction == 5:
    direction = 4
  elif direction == 4:
    direction = 3
  elif direction == 3:
    direction = 2
  elif direction == 2:
    direction = 1
  #print ("  new: ",direction)
  return direction;



def ChanceOfTurning8Way(Direction,Chance):
  #print ("Chance of turning: ",Chance)
  if Chance > randint(1,100):
    if randint(0,1) == 0:
      Direction = TurnLeft8Way(Direction)
    else:
      Direction = TurnRight8Way(Direction)
  return Direction;


def ChanceOfTurning(Direction,Chance):
  #print ("Chance of turning: ",Chance)
  if Chance > randint(1,100):
    if randint(0,1) == 0:
      Direction = TurnLeft(Direction)
    else:
      Direction = TurnRight(Direction)
  return Direction;





GRAVITY  = 0.0098
FRICTION = 0.75
CEILING  = -5
FLOOR    = HatHeight
WESTWALL = 0
EASTWALL = HatWidth
TICKSPERFRAME = 7

def MoveSpriteWithGravity(sprite):
#keep all the info inside the sprite object if possible

  #initial co-ordinates for ball
  x     = sprite.h
  y     = sprite.v
  oldx  = x
  oldy  = y
  nextx = 0
  nexty = 0

  # intiial velocities
  velocityX = sprite.velocityH
  velocityY = sprite.velocityV
  

  
  # calculate new position based on velocity  
  next_y = y + velocityY
  next_x = x + velocityX


  # Bounce off floor
  if (next_y >= (FLOOR - sprite.height)):
    velocityY = -velocityY * FRICTION
    next_y = FLOOR - sprite.height

  # Bounce of ceiling
  if (next_y <= CEILING):
    velocityY = -velocityY * FRICTION
    next_y = CEILING    

  # Bounce of side walls
  if (next_x  > (EASTWALL - sprite.width)):
    velocityX = -velocityX * FRICTION
    next_x = EASTWALL - sprite.width

  # Bounce of side walls
  if (next_x  < WESTWALL):
    velocityX = -velocityX * FRICTION
    next_x = WESTWALL

  #Calculate new vertical velocity (based on gravity)
  velocityY = velocityY +GRAVITY



  #Erase old sprite
  sprite.h = next_x
  sprite.v = next_y
  sprite.velocityH = velocityX
  sprite.velocityV = velocityY

  # only erase if movement detected
  if(round(oldx) != round(next_x)) or (round(oldy) != round(next_y)):
    sprite.EraseFrame(h=oldx,v=oldy,frame=-1)

  CopyAnimatedSpriteToPixelsZoom(sprite,h=round(next_x),v=round(next_y), ZoomFactor=1)




# Experimental functions for bouncing



# drawing functions compute pixel locations based
# on locations in meters





def ReverseDirection8Way(direction):
  if direction == 1:
    direction = 5
  elif direction == 2:
    direction = 6
  elif direction == 3:
    direction = 7
  elif direction == 4:
    direction = 8
  elif direction == 5:
    direction = 1
  elif direction == 6:
    direction = 2
  elif direction == 7:
    direction = 3
  elif direction == 8:
    direction = 4
  return direction;














def ErrorHandler(ErrorMessage,TraceMessage,AdditionalInfo):
  CallingFunction =  inspect.stack()[1][3]
  #FinalCleanup(stdscr)
  print("")
  print("")
  print("--------------------------------------------------------------")
  print("ERROR - Function (",CallingFunction, ") has encountered an error. ")
  print(ErrorMessage)
  print("")
  print("")
  print("TRACE")
  print(TraceMessage)
  print("")
  print("")
  if (AdditionalInfo != ""):
    print("Additonal info:",AdditionalInfo)
    print("")
    print("")
  print("--------------------------------------------------------------")
  print("")
  print("")
  











def MoveWithInertia(sprite):
  

    
  if(sprite.h > HatWidth - sprite.width) or (sprite.h <= 0):
    sprite.directionH = sprite.directionH * -1
    
    #sprite.speed = sprite.speed * 0.95
  if(sprite.v > HatHeight - sprite.height ) or (sprite.v <= 0):
    sprite.directionV = sprite.directionV * -1
    
    #sprite.speed = sprite.speed * 0.95

  sprite.h = sprite.h + (sprite.speed * sprite.directionH)
  sprite.v = sprite.v + (sprite.speed * sprite.directionV)

  



def RandomMove(h,v,sprite):
  sprite.direction = ChanceOfTurning8Way(sprite.direction,30) 
  newh,newv = CalculateDotMovement8Way(h,v,sprite.direction)
  if(CheckBoundary(newh,newv) == 0) and (CheckBoundary((newh + sprite.width),(newv + sprite.height))== 0):
    return newh,newv
  else:
    sprite.direction = ReverseDirection8Way(sprite.direction)
    return h,v





def BounceFromCollision(sprite1,sprite2):

  #Calculate box coordinates for Sprite 1
  h1 = sprite1.h
  v1 = sprite1.v
  h2 = h1 + sprite1.width
  v2 = v1 + sprite1.height

  #Calculate box coordinates for Sprite 2
  x1 = sprite2.h
  y1 = sprite2.v
  x2 = x1 + sprite2.width
  y2 = y1 + sprite2.height
  
  
  if (((h1 >= x1 and h1 <= x2) and (v1 >= y1 and v1 <= y2)) or
     ((h2 >= x1 and h2 <= x2) and (v2 >= y1 and v2 <= y2))):

    if (h1 <= x1) or (h2 >= x2):
      sprite1.velocityH = sprite1.velocityH * -1

    if (v1 <= y1) or (v2 >= y2):
      sprite1.velocityV = sprite1.velocityV * -1
  
    return 1
  else:
    return 0




def RandomBounceFromFloor(sprite):

  if (abs(sprite.velocityV) < 0.001):
    sprite.velocityV = 2 * random.random()

  if (abs(sprite.velocityH) < 0.001):
    sprite.velocityH = 2 * random.random()





def CheckForCollision(Sprite1,Sprite2):

  #Calculate box coordinates for Sprite 1
  h1 = Sprite1.h
  v1 = Sprite1.v
  h2 = h1 + Sprite1.width
  v2 = v1 + Sprite1.height

  #Calculate box coordinates for Sprite 2
  x1 = Sprite2.h
  y1 = Sprite2.v
  x2 = x1 + Sprite2.width
  y2 = y1 + Sprite2.height


  #if the boxes overlap, a collision has occurred
  if (((h1 >= x1 and h1 <= x2) and (v1 >= y1 and v1 <= y2)) or
     ((h2 >= x1 and h2 <= x2) and (v2 >= y1 and v2 <= y2))):
    return 1
  
  return 0







def DisplayExplosionIfExploding(Explosion,h,v):
  if (Explosion.exploding == 1 ):
    if (Explosion.h == -1):
      Explosion.h = round(h)
      Explosion.v = round(v)
    Explosion.DisplayAnimated(Explosion.h,Explosion.v)

    #Kill explosion sprite after explosion animation is complete
    if (Explosion.currentframe >= Explosion.frames):
      Explosion.EraseFrame(Explosion.h,Explosion.v)
      Explosion.currentframe = 1
      Explosion.exploding    = 0
      Explosion.alive        = 0
      Explosion.h = -1
      Explosion.v = -1


def ChangeRGBBrightness(r,g,b,increment):
  r = r + increment
  g = g + increment
  b = b + increment

  if(increment <= 0):
    if(r <= 0):
      r = 0
    if(g <= 0):
      g = 0
    if(b <= 0):
      b = 0

  if (increment > 0):
    if(r >= 255):
      r = 255
    if(g >= 255):
      g = 255
    if(b >= 255):
      b = 255

  return r,g,b




















def TransitionBetweenScreenArrays(OldArray,NewArray,TransitionType=1,FadeSleep=0.01):

  #NewArray NEW pixels need to glow into existence
  #OldArray pixels not in new need to fade

  global ScreenArray
  
  #Buffer will be our custom "off screen canvas"
  Buffer  = ([[]])
  Buffer  = [[ (0,0,0) for i in range(HatWidth)] for i in range(HatHeight)]
  
  

  # 1 = Fade and Glow
  if(TransitionType == 1):
    #Create list of co-ordinates that need to be processed
    PixelsToFade = []
    PixelsToGlow = []


    for y in range (0,HatHeight):
      for x in range (0,HatWidth):
        OldR, OldG, OldB = OldRGB = OldArray[y][x]
        NewR, NewG, NewB = NewRGB = NewArray[y][x]
        
        #OldPixel set NewPixel empty
        #if OldRGB != (0,0,0) and NewRGB == (0,0,0):
        if ((OldR > 0 or OldG > 0 or OldB > 0) and
          (NewR == 0  and NewG == 0  and NewB == 0)):
          PixelsToFade.append((x,y,OldR,OldG,OldB))
          #print("Fade:",x,y,OldR,OldG,OldB)

        #NewPixel set OldPixel empty
        elif ((NewR > 0 or NewG > 0 or NewB > 0) and
          (OldR == 0  and OldG == 0  and OldB == 0)):
          PixelsToGlow.append((x,y,0,0,0))
          #print('Glow:',x,y,NewR,NewG,NewB)

        else:
          TheMatrix.SetPixel(x,y,OldR,OldG,OldB)

    FadeCount = len(PixelsToFade)
    GlowCount = len(PixelsToGlow)

    #print ("FadeCount:",FadeCount," GlowCount:",GlowCount)
    #j is used to control brightness levels.  j +- 10
    for j in range (1,26):
      
      if (FadeCount > 1):
        for f in range (0,FadeCount):
          x,y,r,g,b = PixelsToFade[f]
          r,g,b = ChangeRGBBrightness(r,g,b,-10)
          #print ('Fade:',x,y,r,g,b,f)
          PixelsToFade[f] = (x,y,r,g,b)
          TheMatrix.SetPixel(x,y,r,g,b)

      if (GlowCount > 1):        
        for i in range (0,GlowCount):
          x,y,r,g,b = PixelsToGlow[i]
          r,g,b = ChangeRGBBrightness(r,g,b,10)
          #print ('Glow:',x,y,r,g,b,i)

          #Stop increasing value once we hit the original color
          NewR, NewG, NewB = NewRGB = NewArray[y][x]
          if (r >= NewR):
            r = NewR
          if (g >= NewG):
            g = NewG
          if (b >= NewB):
            b = NewB
          #print ("old:",r,g,b," new:",NewR,NewG,NewB)

          PixelsToGlow[i] = (x,y,r,g,b)
          TheMatrix.SetPixel(x,y,r,g,b)
      time.sleep(FadeSleep)
    setpixels(NewArray)
    

  #----------------------------
  # Falling particles
  #----------------------------
  elif(TransitionType == 2):
    #create an array of sprite objects (particles)
    SpriteArray = CreateSpriteArray(OldArray,NewArray)
    CopyScreenArrayToCanvasVSync(OldArray)
    #Canvas.Clear()
    
    
    #Count particles to process

    ParticleCount = 0
    for y in range (0,HatHeight):
      for x in range (0,HatWidth):
        if(SpriteArray[0][y][x].name == 'fall'):
          ParticleCount = ParticleCount + 1
        if(SpriteArray[1][y][x].name == 'fall'):
          ParticleCount = ParticleCount + 1

    Processed = 0

   
    
    while (Processed < ParticleCount):
      #Draw empty pixels first

      #Erase the particles
      for y in range (0,HatHeight):
        for x in range (0,HatWidth):
          if(SpriteArray[0][y][x].name in('fall')):
            #Canvas.SetPixel(x,y,0,0,0)
            Buffer[y][x]=(0,0,0)
            Buffer = SetBufferPixel(Buffer, x, y, 0,0,0)

          if(SpriteArray[1][y][x].name in ('fall')):
            #Canvas.SetPixel(x,y,0,0,0)
            Buffer = SetBufferPixel(Buffer, x, y, 0,0,0)

          if(SpriteArray[2][y][x].name in ('empty')):
            #Canvas.SetPixel(x,y,0,0,0)
            Buffer = SetBufferPixel(Buffer, x, y, 0,0,0)

      #Canvas = TheMatrix.SwapOnVSync(Canvas)  
      #CopyScreenArrayToCanvasVSync(Buffer)

      #Draw the falling pixels
      for y in range (0,HatHeight):
        for x in range (0,HatWidth):

          OldName = SpriteArray[0][y][x].name
          OldR    = SpriteArray[0][y][x].r
          OldG    = SpriteArray[0][y][x].g
          OldB    = SpriteArray[0][y][x].b
          OldH    = SpriteArray[0][y][x].h
          OldV    = SpriteArray[0][y][x].v
          Old_v_stop    = SpriteArray[0][y][x].v_stop
          Old_velocityV = SpriteArray[0][y][x].velocityV
          Old_next_v    = OldV +Old_velocityV


          NewName = SpriteArray[1][y][x].name
          NewR    = SpriteArray[1][y][x].r
          NewG    = SpriteArray[1][y][x].g
          NewB    = SpriteArray[1][y][x].b
          NewH    = SpriteArray[1][y][x].h
          NewV    = SpriteArray[1][y][x].v
          New_v_stop    = SpriteArray[1][y][x].v_stop
          New_velocityV = SpriteArray[1][y][x].velocityV
          New_next_v    = NewV + New_velocityV


          BothName = SpriteArray[2][y][x].name
          BothR    = SpriteArray[2][y][x].r
          BothG    = SpriteArray[2][y][x].g
          BothB    = SpriteArray[2][y][x].b
          BothH    = SpriteArray[2][y][x].h
          BothV    = SpriteArray[2][y][x].v
          #Both_v_stop    = SpriteArray[2][y][x].v_stop
          Both_velocityV = SpriteArray[2][y][x].velocityV
          Both_next_v    = BothV + Both_velocityV


          if(NewName == 'fall'):
            if (New_next_v > New_v_stop):
              next_v = New_v_stop
              Processed = Processed + 1
              SpriteArray[1][y][x].name = 'empty'
              SpriteArray[2][y][x].name = 'both-different'
              SpriteArray[2][y][x].r    = NewR
              SpriteArray[2][y][x].g    = NewG
              SpriteArray[2][y][x].b    = NewB
              Buffer = SetBufferPixel(Buffer, x, y, NewR, NewG, NewB )          
  
            #Canvas.SetPixel(NewH,New_next_v,NewR,NewG,NewB)
            #Buffer[round(New_next_v)][round(NewH)] = 50,50,0
            Buffer = SetBufferPixel(Buffer, NewH, NewV, NewR, NewG, NewB)

            SpriteArray[1][y][x].velocityV = New_velocityV + random.random() / 2
            SpriteArray[1][y][x].v = New_next_v
            
            
            


          if(OldName == 'fall'):
            if (Old_next_v >= Old_v_stop ):
              Old_next_v = Old_v_stop
              Processed = Processed + 1
              SpriteArray[0][y][x].name = 'empty'

            #Canvas.SetPixel(OldH,Old_next_v,OldR,OldG,OldB)
            Buffer = SetBufferPixel(Buffer, OldH, OldV, OldR, OldG, OldB)

            SpriteArray[0][y][x].velocityV = Old_velocityV + random.random() / 2
            SpriteArray[0][y][x].v = Old_next_v

                        
          #when particles fall, they are overwriting a spot that is marked as both.  This should not happen.
          #falling dots need to be erased.
          
          #once the old particles fall, we want the BOTH color to swich over to the NEW colors
          elif(BothName in ('both-identical','both-different')):
            #Canvas.SetPixel(x,y,BothR,BothG,BothB)            
            Buffer = SetBufferPixel(Buffer, x, y, BothR, BothG, BothB)
            #Buffer = SetBufferPixel(Buffer, x, y, 0, 0, 0)
          

      
      CopyScreenArrayToCanvasVSync(Buffer)
      time.sleep(FadeSleep)
      #time.sleep(0.01)
    CopyScreenArrayToCanvasVSync(NewArray)
    #time.sleep(1)
    
    ScreenArray = copy.deepcopy(NewArray)
  return









def CreateSpriteArray(OldArray,NewArray):
  #This function will create a screen array of color animated sprites, one dot in size
  #this will allow us to perform advanced animations and transitions
  #Adding a third dimension, to allow multiple sprites to occupy the same space

  SpriteArray = ([[[]]])
  SpriteArray = [[[ (Sprite(
      width = 1,
      height = 1,
      r = 0,
      g = 0,
      b = 0
      )
    ) for i in range(HatWidth)] for i in range(HatHeight)]  for j in range(3)]




  for y in range (0,HatHeight):
    for x in range (0,HatWidth):
  
      OldR, OldG, OldB = OldRGB = OldArray[y][x]
      NewR, NewG, NewB = NewRGB = NewArray[y][x]
      
      

      #Give every sprite an empty value
      for j in range (3):
        SpriteArray[j][y][x].name = 'empty'
        SpriteArray[j][y][x].r    = 0
        SpriteArray[j][y][x].g    = 0
        SpriteArray[j][y][x].b    = 0

        SpriteArray[j][y][x].h    = x
        SpriteArray[j][y][x].v    = y
        SpriteArray[j][y][x].velocityV = GRAVITY * 5
        SpriteArray[j][y][x].v_stop = HatHeight 
          


      #OLD = 0 / NEW = 1 / BOTH = 2

      #Old on  New off
      if ((OldR > 0 or OldG > 0 or OldB > 0) and 
         (NewR == 0 and NewG == 0 and NewB == 0)):
        SpriteArray[0][y][x].name = 'fall'
        SpriteArray[0][y][x].r    = OldR
        SpriteArray[0][y][x].g    = OldG
        SpriteArray[0][y][x].b    = OldB

        SpriteArray[0][y][x].h    = x
        SpriteArray[0][y][x].v    = y
        SpriteArray[0][y][x].velocityV = GRAVITY * 5
        SpriteArray[0][y][x].v_stop = HatHeight 

        
      #New on Old off
      elif((NewR > 0 or NewG > 0 or NewB > 0) and 
         (OldR == 0 and OldG == 0 and OldB == 0)):
        SpriteArray[1][y][x].name = 'fall'
        SpriteArray[1][y][x].r    = NewR
        SpriteArray[1][y][x].g    = NewG
        SpriteArray[1][y][x].b    = NewB

        SpriteArray[1][y][x].h    = x
        SpriteArray[1][y][x].v    = 0 - y - 10
        SpriteArray[1][y][x].velocityV = GRAVITY * 5
        SpriteArray[1][y][x].v_stop = y

       
      #Both are populated and identical
      elif ((NewR > 0 or NewG > 0 or NewB > 0) and
        (OldR == NewR and OldG == NewG and OldB == NewB)):

        SpriteArray[2][y][x].name = 'both-identical'
        SpriteArray[2][y][x].r    = OldR
        SpriteArray[2][y][x].g    = OldG
        SpriteArray[2][y][x].b    = OldB

        SpriteArray[2][y][x].h    = x
        SpriteArray[2][y][x].v    = 0 -y -10
        SpriteArray[2][y][x].velocityV = GRAVITY * 5
        SpriteArray[2][y][x].v_stop = y #not needed really 

      #Both are populated but different
      #Fall down old and new
      #this takes care of strange artifacts in the shadows
      elif ((NewR > 0 or NewG > 0 or NewB > 0) and
            (OldR > 0 or OldG > 0 or OldB > 0) and
        (OldR != NewR or OldG != NewG or OldB != NewB)):

        #SpriteArray[2][y][x].name = 'both-different'
        #SpriteArray[2][y][x].r    = NewR
        #SpriteArray[2][y][x].g    = NewG
        #SpriteArray[2][y][x].b    = NewB

        SpriteArray[0][y][x].name = 'fall'
        SpriteArray[0][y][x].r    = OldR
        SpriteArray[0][y][x].g    = OldG
        SpriteArray[0][y][x].b    = OldB
        SpriteArray[0][y][x].h    = x
        SpriteArray[0][y][x].v    = y
        SpriteArray[0][y][x].velocityV = GRAVITY * 5
        SpriteArray[0][y][x].v_stop = HatHeight


        SpriteArray[1][y][x].name = 'fall'
        SpriteArray[1][y][x].r    = NewR
        SpriteArray[1][y][x].g    = NewG
        SpriteArray[1][y][x].b    = NewB
        SpriteArray[1][y][x].h    = x
        SpriteArray[1][y][x].v    = 0 -y -10
        SpriteArray[1][y][x].velocityV = GRAVITY * 5
        SpriteArray[1][y][x].v_stop = y


        SpriteArray[2][y][x].name = 'both-different'
        SpriteArray[2][y][x].r    = NewR
        SpriteArray[2][y][x].g    = NewG
        SpriteArray[2][y][x].b    = NewB
        SpriteArray[2][y][x].h    = x
        SpriteArray[2][y][x].v    = 0 -y -10
        SpriteArray[2][y][x].velocityV = GRAVITY * 5
        SpriteArray[2][y][x].v_stop = y


   
     
     
     

  return SpriteArray






def MakeAndShowClock(hh=24,h=0,v=0,RGB=HighGreen,ShadowRGB=ShadowGreen,ZoomFactor=1,Fill=False):

  ClearBigLED()
  ClearBuffers()      
  ClockSprite = CreateClockSprite(hh)
  CopySpriteToPixelsZoom(ClockSprite,h-1,v+1,ShadowRGB,(0,0,0),ZoomFactor,          Fill=False)
  CopySpriteToPixelsZoom(ClockSprite,h,v,    RGB,      (0,0,0),ZoomFactor=ZoomFactor,Fill=False)

 

def MakeAndShowTimer(hhmmss,h=0,v=0,RGB=HighGreen,ShadowRGB=ShadowGreen,ZoomFactor=1,Fill=False):

  #we want to show a timer for how long the stream has been active
  #this can be triggerred by a command possibly

  ClearBigLED()
  ClearBuffers()      
  StartTime = time.time()
  HHMMSS = '00:00:00'
  TimerSprite = CreateTimerSprite(HHMMSS)
  h = int(((HatWidth - TimerSprite.width * ZoomFactor) / 2))

  CopySpriteToPixelsZoom(TimerSprite,h-1,v+1,ShadowRGB,(0,0,0),ZoomFactor,          Fill=False)
  CopySpriteToPixelsZoom(TimerSprite,h,v,    RGB,      (0,0,0),ZoomFactor=ZoomFactor,Fill=False)







def UpdateClockWithTransition(ClockSprite,hh=24,h=0,v=0,RGB=HighGreen,ShadowRGB=ShadowGreen,ZoomFactor=1,Fill=False,TransitionType=1):

  global ScreenArray
  
  if (ClockSprite.hhmm != datetime.now().strftime('%H:%M')):
  #if (1==1):


    DayOfWeekSprite     = CreateDayOfWeekSprite()
    MonthSprite         = CreateMonthSprite()
    DayOfMonthSprite    = CreateDayOfMonthSprite()

          


    #print("ClockSprite.hhm: ",ClockSprite.hhmm, "Other:",datetime.now().strftime('%H:%M'))

    #copy old time to a buffer


    ScreenArray1 = CopySpriteToScreenArrayZoom(ClockSprite,h-1,v+1,ShadowRGB,(0,0,0),ZoomFactor,          Fill=False)
    ScreenArray1 = CopySpriteToScreenArrayZoom(ClockSprite,h,v,    RGB,      (0,0,0),ZoomFactor=ZoomFactor,Fill=False,InputScreenArray=ScreenArray1)
    ScreenArray1 = CopySpriteToScreenArrayZoom(DayOfWeekSprite,DayOfWeekH,DayOfWeekV,DayOfWeekRGB, (0,0,0),ZoomFactor=1,Fill=False,InputScreenArray=ScreenArray1)
    ScreenArray1 = CopySpriteToScreenArrayZoom(MonthSprite,MonthH,DayOfWeekV,MonthRGB, (0,0,0),ZoomFactor=1,Fill=False,InputScreenArray=ScreenArray1)
    ScreenArray1 = CopySpriteToScreenArrayZoom(DayOfMonthSprite,DayOfMonthH,DayOfMonthV,DayOfMonthRGB, (0,0,0),ZoomFactor=1,Fill=False,InputScreenArray=ScreenArray1)



    #Just in case the day changes!
    DayOfWeekSprite     = CreateDayOfWeekSprite()
    MonthSprite         = CreateMonthSprite()
    DayOfMonthSprite    = CreateDayOfMonthSprite()


    #copy new time to a buffer
    #TheTime = str(random.randint(10,23)) + ":" + str(random.randint(10,59)) + ":00"
    #ClockSprite = CreateClockSprite(hh,hhmmss=TheTime)
    ClockSprite = CreateClockSprite(hh)
    ScreenArray2 = CopySpriteToScreenArrayZoom(ClockSprite,h-1,v+1,ShadowRGB,(0,0,0),ZoomFactor,          Fill=False)
    ScreenArray2 = CopySpriteToScreenArrayZoom(ClockSprite,h,v,    RGB,      (0,0,0),ZoomFactor=ZoomFactor,Fill=False,InputScreenArray=ScreenArray2)
    ScreenArray2 = CopySpriteToScreenArrayZoom(DayOfWeekSprite,DayOfWeekH,DayOfWeekV,DayOfWeekRGB, (0,0,0),ZoomFactor=1,Fill=False,InputScreenArray=ScreenArray2)
    ScreenArray2 = CopySpriteToScreenArrayZoom(MonthSprite,MonthH,DayOfWeekV,MonthRGB, (0,0,0),ZoomFactor=1,Fill=False,InputScreenArray=ScreenArray2)
    ScreenArray2 = CopySpriteToScreenArrayZoom(DayOfMonthSprite,DayOfMonthH,DayOfMonthV,DayOfMonthRGB, (0,0,0),ZoomFactor=1,Fill=False,InputScreenArray=ScreenArray2)


    if(TransitionType == 1):
      TransitionBetweenScreenArrays(ScreenArray2,ScreenArray1,TransitionType)
    elif(TransitionType == 2):
      TransitionBetweenScreenArrays(ScreenArray1,ScreenArray2,TransitionType)


    #CopySpriteToPixelsZoom(ClockSprite,ClockH,0,(150,0,0),(0,0,0),2,Fill=True)

    ScreenArray = copy.deepcopy(ScreenArray2)

  return ClockSprite 


#MakeAndShowClock(hh,h=0,v,RGB,ShadowGreen=,ZoomFactor,Fill):

















def UpdateTimerWithTransition(TimerSprite,BannerSprite,h=0,v=0,RGB=HighGreen,ShadowRGB=ShadowGreen,ZoomFactor=1,Fill=False,TransitionType=1,StartDateTimeUTC='',ForceUpdate=False):
  #take the time as a sprite, and a message to display (the banner sprite)
  #update the LED screen
  #print("Update timer with transition")

  global ScreenArray
  
  hh,mm,ss, HHMMSS = CalculateElapsedTime(StartDateTimeUTC)
  print ('DurationHHMMSS: ',HHMMSS,end="\r")
  #print ('DurationHHMMSS: ',HHMMSS)
  #print('HV:',h,v," ForceUpdate:",ForceUpdate)
  
  if (HHMMSS[0:5] != TimerSprite.HHMM or ForceUpdate == True):
  #if (HHMMSS != TimerSprite.HHMM):
    TimerSprite = CreateTimerSprite(HHMMSS)

    #Write time to a buffer with a nice shadow
    NewScreenArray  = ([[]])
    NewScreenArray  = [[ (0,0,0) for i in range(HatWidth)] for i in range(HatHeight)]
    NewScreenArray = CopySpriteToScreenArrayZoom(TimerSprite,h-1,v+1,ShadowRGB,(0,0,0),ZoomFactor,           Fill=False)
    NewScreenArray = CopySpriteToScreenArrayZoom(TimerSprite,h,v,    RGB,      (0,0,0),ZoomFactor=ZoomFactor,Fill=False,InputScreenArray=NewScreenArray)
    #write the Banner (e.g. UpTime) to the buffer
    NewScreenArray = CopySpriteToScreenArrayZoom(BannerSprite,BannerSprite.h,BannerSprite.v, BannerSprite.RGB, (0,0,0),ZoomFactor=BannerSprite.ZoomFactor,Fill=False,InputScreenArray=NewScreenArray)
   

    #ScreenArray = copy.deepcopy(ScreenArray2)
    #CopyScreenArrayToCanvasVSync(ScreenArray2)
    TransitionBetweenScreenArrays(OldArray=ScreenArray,NewArray=NewScreenArray,TransitionType=2)
    
    
  return TimerSprite

  






#MakeAndShowClock(hh,h=0,v,RGB,ShadowGreen=,ZoomFactor,Fill):










def DisplayDigitalClock(
  ClockStyle  = 1,
  CenterHoriz = False,
  CenterVert  = False,
  h           = 0,
  v           = 0,
  hh          = 24,
  RGB         = MedBlue,
  ShadowRGB   = ShadowBlue,
  ZoomFactor  = 2,
  AnimationDelay = 30,
  ScrollSleep    = 0.01,
  RunMinutes     = 1,
  StartDateTimeUTC  = '',
  HHMMSS            = '00:00:00',
  DisplayNumber1    = 0,
  DisplayNumber2    = 0,
  StopEvent         = None
  ):



    ClearBigLED()
    ClearBuffers()
    global ScreenArray
    global DayOfWeekV
    global MonthV
    global DayOfMonthV


    print(f"[LED.DisplayDigitalClock] PID: {os.getpid()} - Hello from LED processes")
    print(f"RGB:    {RGB}")
    print(f"Shadow: {ShadowRGB}")
    

    print("ClockStyle:",ClockStyle)
    ClockSprite = CreateClockSprite(hh)
    ClockSprite.TrimLeftEmptyColumns(0)
    Done        = False
    StartTime   = time.time()
    print("RunMinutes:",RunMinutes)



    if (CenterHoriz == True):
      h = (HatWidth  // 2)  - ((ClockSprite.width * ZoomFactor) // 2) -1

    if (CenterVert  == True):
      v = (HatHeight // 2) - ((ClockSprite.height * ZoomFactor) // 2) - ZoomFactor


    
    if (ClockStyle in (1,2)):
      DayOfWeekSprite     = CreateDayOfWeekSprite()
      MonthSprite         = CreateMonthSprite()
      DayOfMonthSprite    = CreateDayOfMonthSprite()
   
      DateSprite = JoinSprite(DayOfWeekSprite,MonthSprite,4)
      DateSprite = JoinSprite(DateSprite,DayOfMonthSprite,4)
      DateSprite.h =  (HatWidth  // 2)  - ((DateSprite.width) // 2) + 1
      DateSprite.v =  (v + ClockSprite.height * ZoomFactor) + 4
        

  
    # Clock at top, random scrolling animations
    if (ClockStyle == 1):
    
      #MakeAndShowClock(hh,h,v,RGB,ShadowGreen,ZoomFactor,Fill=False)
      ScreenArray1  = ([[]])
      ScreenArray1  = [[ (0,0,0) for i in range(HatWidth)] for i in range(HatHeight)]
      ScreenArray2  = ([[]])
      ScreenArray2  = [[ (0,0,0) for i in range(HatWidth)] for i in range(HatHeight)]
      ClockSprite = CreateClockSprite(hh)
      ClockSprite.TrimLeftEmptyColumns(0)

      ScreenArray1 = CopySpriteToScreenArrayZoom(ClockSprite,h-1,v+1,ShadowRGB,(0,0,0),ZoomFactor=ZoomFactor,Fill=False,InputScreenArray=ScreenArray)
      ScreenArray1 = CopySpriteToScreenArrayZoom(ClockSprite,h,v,RGB,(0,0,0),ZoomFactor=ZoomFactor,Fill=False,InputScreenArray=ScreenArray1)
      try:
        TransitionBetweenScreenArrays(ScreenArray2,ScreenArray1,TransitionType=2)
      except Exception as e:
            print(f"[ERROR] LED.DisplayTwitchTimer crashed: {e}")

      #CopySpriteToPixelsZoom(ClockSprite,h-1,v+1,ShadowRGB,(0,0,0),ZoomFactor,          Fill=False)
      #CopySpriteToPixelsZoom(ClockSprite,h,v,    RGB,      (0,0,0),ZoomFactor=ZoomFactor,Fill=False)
      
      
      #Show Custom Sprite
      #CopySpriteToPixelsZoom(DayOfWeekSprite,  DayOfWeekH,  DayOfWeekV,  DayOfWeekRGB,   SpriteFillerRGB,1)
      #CopySpriteToPixelsZoom(MonthSprite,      MonthH,      MonthV,      MonthRGB,       SpriteFillerRGB,1)
      #CopySpriteToPixelsZoom(DayOfMonthSprite, DayOfMonthH, DayOfMonthV, DayOfMonthRGB , SpriteFillerRGB,1)
      CopySpriteToPixelsZoom(DateSprite, DateSprite.h , DateSprite.v, DayOfMonthRGB , SpriteFillerRGB,1)

      
      #MakeAndShowClock(hh,h,v,RGB,ShadowGreen,ZoomFactor,Fill=True)
      ClockSprite = UpdateClockWithTransition(ClockSprite,hh,h,v,RGB,ShadowRGB,ZoomFactor,Fill=True)

      LastAnimation = time.time()

      while (Done == False):
        #print(f"StopEvent: {StopEvent}")
        #when called from a multiprocess (LEDcommander) keep an eye on the StopEvent 
        
        if StopEvent and StopEvent.is_set():
            print("[LED] Stop requested — exiting early.")
            Done = True

            #--> Put a transition effect here
           

            break


        #If the time has changed since we started the animation delay loop, update the sprite
        ClockSprite = UpdateClockWithTransition(ClockSprite,hh,h,v,RGB,ShadowRGB,ZoomFactor,Fill=True,TransitionType=2)



        hh1,mmm1,ss1 = GetElapsedTime(LastAnimation,time.time())
        if(ss1 >= AnimationDelay):
          print("[LEDarcade][DisplayDigitalClock] Showing animation ")
          LastAnimation = time.time()


          #Pick a random animation        
          r = random.randint(1,11)
          if (r == 1):
            ClockSprite = UpdateClockWithTransition(ClockSprite,hh,h,v,RGB,ShadowRGB,ZoomFactor,Fill=True)
            #MakeAndShowClock(hh,h,v,RGB,ShadowGreen,ZoomFactor,Fill=True)

            RunningMan2Sprite.ScrollAcrossScreen(20,15,'right', ScrollSleep )
            RunningMan2Sprite.HorizontalFlip()
            Rezonator.ScrollAcrossScreen(20,(HatHeight - Rezonator.height),'right', ScrollSleep )
            RunningMan2Sprite.ScrollAcrossScreen(20,15,'left',0.02 )
            Rezonator.ScrollAcrossScreen(20,(HatHeight - Rezonator.height),'left', ScrollSleep )
            RunningMan2Sprite.HorizontalFlip()

          elif (r == 2):
            ClockSprite = UpdateClockWithTransition(ClockSprite,hh,h,v,RGB,ShadowRGB,ZoomFactor,Fill=True,TransitionType=2)
            #MakeAndShowClock(hh,h,v,RGB,ShadowGreen,ZoomFactor,Fill=True)
            r = random.randint(1,2)
            MoveAnimatedSpriteAcrossScreen(BigSpiderWalkingSprite,Position='bottom',direction="right",steps=14*r,ZoomFactor=r,sleep=0.05)
            BigSpiderWalkingSprite.HorizontalFlip()
            r = random.randint(1,2)
            MoveAnimatedSpriteAcrossScreen(BigSpiderWalkingSprite,Position='bottom',direction="left",steps=14*r,ZoomFactor=r,sleep=0.03)
            BigSpiderWalkingSprite.HorizontalFlip()

          elif (r == 3):
            #MakeAndShowClock(hh,h,v,RGB,ShadowGreen,ZoomFactor,Fill=False)
            ClockSprite = UpdateClockWithTransition(ClockSprite,hh,h,v,RGB,ShadowRGB,ZoomFactor,Fill=True,TransitionType=2)

            MoveAnimatedSpriteAcrossScreenFramesPerStep(
              ThreeGhostPacSprite,
              Position      = 'bottom',
              direction     = "right",
              FramesPerStep = 1,
              ZoomFactor    = random.randint(1,2),
              sleep         = 0.03
              )
            

            MoveAnimatedSpriteAcrossScreenFramesPerStep(
              ThreeBlueGhostPacSprite,
              Position      = 'bottom',
              direction     = "left",
              FramesPerStep = 1,
              ZoomFactor    = random.randint(1,2),
              sleep         = 0.02
              )

            #This one works better for big animations
            #MoveAnimatedSpriteAcrossScreen(
            #      ThreeGhostPacSprite,
            #      v             = 15,
            #      direction     = "right",
            #      steps         = 2,
            #      ZoomFactor    = 3,
            #      sleep         = 0
            #      )
                

          elif (r == 4):
            #MakeAndShowClock(hh,h,v,RGB,ShadowGreen,ZoomFactor,Fill=False)
            ClockSprite = UpdateClockWithTransition(ClockSprite,hh,h,v,RGB,ShadowRGB,ZoomFactor,Fill=True,TransitionType=2)

            SpaceInvader.framerate = 2
            SpaceInvader.InitializeScreenArray()
            SmallInvader.framerate = 2
            SmallInvader.InitializeScreenArray()
            TinyInvader.framerate  = 1
            TinyInvader.InitializeScreenArray()


            MoveAnimatedSpriteAcrossScreenStepsPerFrame(
              SpaceInvader,
              Position      = 'bottom',
              direction     = "right",
              StepsPerFrame = 4,
              ZoomFactor    = random.randint(1,3),
              sleep         = 0.03
              )


            MoveAnimatedSpriteAcrossScreenStepsPerFrame(
              SmallInvader,
              Position      = 'bottom',
              direction     = "right",
              StepsPerFrame = 4,
              ZoomFactor    = random.randint(1,3),
              sleep         = 0.03
              )


            MoveAnimatedSpriteAcrossScreenStepsPerFrame(
              TinyInvader,
              Position      = 'bottom',
              direction     = "right",
              StepsPerFrame = 4,
              ZoomFactor    = random.randint(1,3),
              sleep         = 0.03
              )

          elif (r == 5):
            ClockSprite = UpdateClockWithTransition(ClockSprite,hh,h,v,RGB,ShadowRGB,ZoomFactor,Fill=True,TransitionType=2)
            #MakeAndShowClock(hh,h,v,RGB,ShadowGreen,ZoomFactor,Fill=False)

            r = random.randint(1,3)
            MoveAnimatedSpriteAcrossScreenStepsPerFrame(
              LittleShipFlying,
              Position      = 'bottom',
              direction     = "right",
              StepsPerFrame = 4 * r,
              ZoomFactor    = r,
              sleep         = 0.03 / r
              )
            LittleShipFlying.HorizontalFlip()

            r = random.randint(1,3)
            MoveAnimatedSpriteAcrossScreenStepsPerFrame(
              LittleShipFlying,
              Position      = 'bottom',
              direction     = "left",
              StepsPerFrame = 4 * r,
              ZoomFactor    = r,
              sleep         = 0.03 / r
              )
            LittleShipFlying.HorizontalFlip()


          elif (r == 6):
            ClockSprite = UpdateClockWithTransition(ClockSprite,hh,h,v,RGB,ShadowRGB,ZoomFactor,Fill=True,TransitionType=2)
            #MakeAndShowClock(hh,h,v,RGB,ShadowGreen,ZoomFactor,Fill=False)

            MoveAnimatedSpriteAcrossScreenStepsPerFrame(
              DotZerkRobotWalking,
              Position      = 'bottom',
              direction     = "left",
              StepsPerFrame = 2,
              ZoomFactor    = random.randint(1,2),
              sleep         = 0.03
              )
            DotZerkRobotWalking.HorizontalFlip()



            MoveAnimatedSpriteAcrossScreenStepsPerFrame(
              DotZerkRobotWalking,
              Position      = 'bottom',
              direction     = "right",
              StepsPerFrame = 2,
              ZoomFactor    = random.randint(1,2),
              sleep         = 0.03
              )
            DotZerkRobotWalking.HorizontalFlip()


          elif (r == 7):
            ClockSprite = UpdateClockWithTransition(ClockSprite,hh,h,v,RGB,ShadowRGB,ZoomFactor,Fill=True,TransitionType=2)
            #MakeAndShowClock(hh,h,v,RGB,ShadowGreen,ZoomFactor,Fill=False)

            MoveAnimatedSpriteAcrossScreenStepsPerFrame(
              DotZerkRobotWalkingSmall,
              Position      = 'bottom',
              direction     = "left",
              StepsPerFrame = 2,
              ZoomFactor    = random.randint(1,2),
              sleep         = 0.03
              )
            DotZerkRobotWalkingSmall.HorizontalFlip()

            MoveAnimatedSpriteAcrossScreenStepsPerFrame(
              DotZerkRobotWalkingSmall,
              Position      = 'bottom',
              direction     = "right",
              StepsPerFrame = 2,
              ZoomFactor    = random.randint(1,2),
              sleep         = 0.03
              )
            DotZerkRobotWalkingSmall.HorizontalFlip()



          if (r == 8):
            ClockSprite = UpdateClockWithTransition(ClockSprite,hh,h,v,RGB,ShadowRGB,ZoomFactor,Fill=True,TransitionType=2)
            #MakeAndShowClock(hh,h,v,RGB,ShadowGreen,ZoomFactor,Fill=False)

            RunningMan3Sprite.ScrollAcrossScreen(20,15,'right', ScrollSleep )
            RunningMan3Sprite.HorizontalFlip()
            RunningMan3Sprite.ScrollAcrossScreen(20,15,'left',0.02 )
            RunningMan3Sprite.HorizontalFlip()


          elif (r == 9):
            #MakeAndShowClock(hh,h,v,RGB,ShadowGreen,ZoomFactor,Fill=False)
            ClockSprite = UpdateClockWithTransition(ClockSprite,hh,h,v,RGB,ShadowRGB,ZoomFactor,Fill=True,TransitionType=2)

            i = random.randint(0,27)
            ShipSprites[i].InitializeScreenArray()

            MoveAnimatedSpriteAcrossScreenStepsPerFrame(
              ShipSprites[i],
              Position      = 'bottom',
              direction     = "left",
              StepsPerFrame = 1,
              ZoomFactor    = random.randint(1,2),
              sleep         = 0.03
              )
          

            i = random.randint(0,27)
            MoveAnimatedSpriteAcrossScreenStepsPerFrame(
              ShipSprites[i],
              Position      = 'bottom',
              direction     = "right",
              StepsPerFrame = 1,
              ZoomFactor    = random.randint(1,2),
              sleep         = 0.03
              )




            i = random.randint(0,27)
            ShipSprites[i].InitializeScreenArray()

            MoveAnimatedSpriteAcrossScreenStepsPerFrame(
              ShipSprites[i],
              Position      = 'bottom',
              direction     = "left",
              StepsPerFrame = 1,
              ZoomFactor    = random.randint(2,3),
              sleep         = 0.03
              )
          

            i = random.randint(0,27)
            MoveAnimatedSpriteAcrossScreenStepsPerFrame(
              ShipSprites[i],
              Position      = 'bottom',
              direction     = "right",
              StepsPerFrame = 1,
              ZoomFactor    = random.randint(2,3),
              sleep         = 0.03
              )

          elif (r == 10):
            ClockSprite = UpdateClockWithTransition(ClockSprite,hh,h,v,RGB,ShadowRGB,ZoomFactor,Fill=True,TransitionType=2)
            #MakeAndShowClock(hh,h,v,RGB,ShadowGreen,ZoomFactor,Fill=False)

            MoveAnimatedSpriteAcrossScreenStepsPerFrame(
              ChickenRunning,
              Position      = 'bottom',
              direction     = "left",
              StepsPerFrame = 2,
              ZoomFactor    = 1,
              sleep         = 0.02
              )
            DotZerkRobotWalking.HorizontalFlip()
            
            
            MoveAnimatedSpriteAcrossScreenStepsPerFrame(
              DotZerkRobotWalking,
              Position      = 'bottom',
              direction     = "left",
              StepsPerFrame = 2,
              ZoomFactor    = 2,
              sleep         = 0.03
              )
            DotZerkRobotWalking.HorizontalFlip()
            
            
            MoveAnimatedSpriteAcrossScreenStepsPerFrame(
              DotZerkRobotWalking,
              Position      = 'bottom',
              direction     = "right",
              StepsPerFrame = 2,
              ZoomFactor    = 2,
              sleep         = 0.02
              )
            DotZerkRobotWalking.HorizontalFlip()

            ChickenRunning.HorizontalFlip()

            MoveAnimatedSpriteAcrossScreenStepsPerFrame(
              ChickenRunning,
              Position      = 'bottom',
              direction     = "left",
              StepsPerFrame = 2,
              ZoomFactor    = 3,
              sleep         = 0.02
              )
            DotZerkRobotWalking.HorizontalFlip()



          elif (r == 11):
            ClockSprite = UpdateClockWithTransition(ClockSprite,hh,h,v,RGB,ShadowRGB,ZoomFactor,Fill=True,TransitionType=2)
            #MakeAndShowClock(hh,h,v,RGB,ShadowGreen,ZoomFactor,Fill=False)

            
            MoveAnimatedSpriteAcrossScreenStepsPerFrame(
              LightBike,
              Position      = 'bottom',
              direction     = "left",
              StepsPerFrame = 2,
              ZoomFactor    = 1,
              sleep         = 0.03
              )
            LightBike.HorizontalFlip()

            MoveAnimatedSpriteAcrossScreenStepsPerFrame(
              Rezonator,
              Position      = 'bottom',
              direction     = "left",
              StepsPerFrame = 2,
              ZoomFactor    = 1,
              sleep         = 0.02
              )

            MoveAnimatedSpriteAcrossScreenStepsPerFrame(
              LightBike,
              Position      = 'bottom',
              direction     = "right",
              StepsPerFrame = 2,
              ZoomFactor    = 1,
              sleep         = 0.01
              )
            LightBike.HorizontalFlip()

            if random.randint(1,2) == 1:
              MoveAnimatedSpriteAcrossScreenStepsPerFrame(
                BigRezonator,
                Position      = 'bottom',
                direction     = "right",
                StepsPerFrame = 2,
                ZoomFactor    = 1,
                sleep         = 0
                )

            else:
              MoveAnimatedSpriteAcrossScreenStepsPerFrame(
                BigRezonator2,
                Position      = 'bottom',
                direction     = "right",
                StepsPerFrame = 2,
                ZoomFactor    = 1,
                sleep         = 0.02
                )






          #This will end the while loop
          elapsed_time = time.time() - StartTime
          elapsed_hours, rem = divmod(elapsed_time, 3600)
          elapsed_minutes, elapsed_seconds = divmod(rem, 60)

          print(datetime.now().strftime('%H:%M:%S'))
      


          if (ClockSprite.hhmm != datetime.now().strftime('%H:%M')):
            #MakeAndShowClock(hh,h,v,RGB,ShadowGreen,ZoomFactor,Fill=True)
            ClockSprite = UpdateClockWithTransition(ClockSprite,hh,h,v,RGB,ShadowRGB,ZoomFactor,Fill=True,TransitionType=2)

          if elapsed_minutes >= RunMinutes:
            Done = True

          




    elif (ClockStyle == 2):

      #ClearBigLED()
      #ClearBuffers()      

      ClockH = HatWidth - (ClockSprite.width * 2)
      ClockSprite = CreateClockSprite(hh)
      #we need to make a fake sprite to take the place of the clock which is zoomed)
      ClockAreaSprite = Sprite((ClockSprite.width*2)+3,(ClockSprite.height*2),0,0,0,[])
      ClockAreaSprite.h = ClockH -3
      ClockAreaSprite.v = 1
      CopySpriteToScreenArrayZoom(ClockSprite,h=ClockH,v=0,ColorTuple=(150,0,0),FillerTuple=(0,0,0),ZoomFactor=2,Fill=True)

      while (Done == False):

        if (ClockSprite.hhmm != datetime.now().strftime('%H:%M')):
          print("[LEDarcade][DisplayDigitalClock] Time:", datetime.now().strftime('%H:%M'))

          #ClearBuffers() #clean the internal graphic buffers
          ClockSprite = CreateClockSprite(hh)
          ScreenArray = CopySpriteToScreenArrayZoom(ClockSprite,45,0,(150,0,0),(0,0,0),1,Fill=True)

        
        r = random.randint(1,7)
        
        if StopEvent and StopEvent.is_set():
            print("[LED] Stop requested — exiting early.")
            Done = True
            #--> Put a transition effect here
            break




        #RunningMan / Starrynight
        if (r==1):
         

          RunningMan3Sprite.framerate = 2
          RunningMan3Sprite.h = -4
          RunningMan3Sprite.v = 14

          RunningManSprite.InitializeScreenArray()
          RunningMan2Sprite.InitializeScreenArray()
          RunningMan3Sprite.InitializeScreenArray()


          print("Starting chicken running")
          ClockSprite = CreateClockSprite(hh)
          h = HatWidth - (ClockSprite.width * 2)
          ScreenArray1 = CopySpriteToScreenArrayZoom(ClockSprite,h=h,v=0,ColorTuple=(150,0,0),FillerTuple=(0,0,0),ZoomFactor=2,Fill=True)

          #Start with empty, copy current time to it
          ScreenArray2 = copy.deepcopy(EmptyArray)
          ScreenArray2 = CopySpriteToScreenArrayZoom(ClockSprite,h=h,v=0,ColorTuple=(150,0,0),FillerTuple=(0,0,0),ZoomFactor=2,Fill=True,InputScreenArray=ScreenArray2)
          ScreenArray2 = CopyAnimatedSpriteToScreenArrayZoom(RunningMan3Sprite,h=-4,v=16, ZoomFactor=1,TheScreenArray=ScreenArray2)
          ScreenArray2 = CopyAnimatedSpriteToScreenArrayZoom(RunningMan2Sprite,h=28,v=16, ZoomFactor=1,TheScreenArray=ScreenArray2)
          ScreenArray2 = CopyAnimatedSpriteToScreenArrayZoom(RunningManSprite,h=46,v=16, ZoomFactor=1,TheScreenArray=ScreenArray2)
          TransitionBetweenScreenArrays(ScreenArray1,ScreenArray2,TransitionType=2)



          for x in range (1,5000):
            #RunningMan3Sprite.Erase()
            CopyAnimatedSpriteToPixelsZoom(RunningMan3Sprite,h=-4,v=16, ZoomFactor=1)
            RunningMan3Sprite.IncrementFrame()
  
            #RunningMan2Sprite.EraseFrame(28,14)
            CopyAnimatedSpriteToPixelsZoom(RunningMan2Sprite,h=28,v=16, ZoomFactor=1)
            RunningMan2Sprite.IncrementFrame()

            #RunningManSprite.EraseFrame(46,14)
            CopyAnimatedSpriteToPixelsZoom(RunningManSprite,h=46,v=16, ZoomFactor=1)
            RunningManSprite.IncrementFrame()
            time.sleep(0.05)

          #Check Time
          if (ClockSprite.hhmm != datetime.now().strftime('%H:%M')):
            #ClearBuffers() #clean the internal graphic buffers
            ClockSprite = CreateClockSprite(hh)
            CopySpriteToPixelsZoom(ClockSprite,h=h,v=0,ColorTuple=(150,0,0),FillerTuple=(0,0,0),ZoomFactor=2,Fill=True)


          ClockSprite = CreateClockSprite(hh)
          ScreenArray2 = CopySpriteToScreenArrayZoom(ClockSprite,h=h,v=0,ColorTuple=(150,0,0),FillerTuple=(0,0,0),ZoomFactor=2,Fill=True)
          TransitionBetweenScreenArrays(ScreenArray,ScreenArray2,TransitionType=2)

          



        #robots
        if (r==2):
          #ClearBigLED()
          #ClearBuffers()      


          print("Starting robot walking running")
          ClockSprite = CreateClockSprite(hh)
          h = HatWidth - (ClockSprite.width * 2)
          ScreenArray1 = CopySpriteToScreenArrayZoom(ClockSprite,h=h,v=0,ColorTuple=(150,0,0),FillerTuple=(0,0,0),ZoomFactor=2,Fill=True)

          #Start with empty, copy current time to it
          ScreenArray2 = copy.deepcopy(EmptyArray)
          ScreenArray2 = CopySpriteToScreenArrayZoom(ClockSprite,h=h,v=0,ColorTuple=(150,0,0),FillerTuple=(0,0,0),ZoomFactor=2,Fill=True,InputScreenArray=ScreenArray2)
          ScreenArray2 = CopyAnimatedSpriteToScreenArrayZoom(DotZerkRobotWalking,h=0,v=16,ZoomFactor=2,TheScreenArray=ScreenArray2)
          ScreenArray2 = CopyAnimatedSpriteToScreenArrayZoom(DotZerkRobotWalkingSmall,h=40,v=22,ZoomFactor=2,TheScreenArray=ScreenArray2)
          TransitionBetweenScreenArrays(ScreenArray1,ScreenArray2,TransitionType=2)




          DotZerkRobotWalking.HorizontalFlip()
          for x in range (1,100):
            CopyAnimatedSpriteToPixelsZoom(DotZerkRobotWalking,h=0,v=16, ZoomFactor=2)
            DotZerkRobotWalking.IncrementFrame()
            CopyAnimatedSpriteToPixelsZoom(DotZerkRobotWalkingSmall,h=40,v=22, ZoomFactor=2)
            DotZerkRobotWalkingSmall.IncrementFrame()
            #time.sleep(0.08)
            time.sleep(0.08)
          DotZerkRobotWalking.HorizontalFlip()

          #Check Time
          if (ClockSprite.hhmm != datetime.now().strftime('%H:%M')):
            print("ClockSprite.hhm: ",ClockSprite.hhmm, "Other:",datetime.now().strftime('%H:%M'))
            #ClearBuffers() #clean the internal graphic buffers
            ClockSprite = CreateClockSprite(hh)
            CopySpriteToPixelsZoom(ClockSprite,h,0,(150,0,0),(0,0,0),2,Fill=True)


          ClockSprite = CreateClockSprite(hh)
          ScreenArray2 = CopySpriteToScreenArrayZoom(ClockSprite,h=h,v=0,ColorTuple=(150,0,0),FillerTuple=(0,0,0),ZoomFactor=2,Fill=True)
          TransitionBetweenScreenArrays(ScreenArray1,ScreenArray2,TransitionType=2)



          #DotZerkRobotWalking.EraseZoom(0,16,2)
          #DotZerkRobotWalkingSmall.EraseZoom(40,22,2)

        #space invaders
        if (r==3):


          SpaceInvader.framerate = 4
          SmallInvader.framerate = 2
          TinyInvader.framerate  = 1

          SpaceInvader.InitializeScreenArray()
          SmallInvader.InitializeScreenArray()
          TinyInvader.InitializeScreenArray()



          print("Starting space invaders")
          ClockSprite = CreateClockSprite(hh)
          h = HatWidth - (ClockSprite.width * 2)
          ScreenArray1 = CopySpriteToScreenArrayZoom(ClockSprite,h=h,v=0,ColorTuple=(150,0,0),FillerTuple=(0,0,0),ZoomFactor=2,Fill=True)

          #Start with empty, copy current time to it
          ScreenArray2 = copy.deepcopy(EmptyArray)
          ScreenArray2 = CopySpriteToScreenArrayZoom(ClockSprite,h=h,v=0,ColorTuple=(150,0,0),FillerTuple=(0,0,0),ZoomFactor=2,Fill=True,InputScreenArray=ScreenArray2)
          ScreenArray2 = CopyAnimatedSpriteToScreenArrayZoom(SpaceInvader,h=0,v=8, ZoomFactor=2,TheScreenArray=ScreenArray2)
          ScreenArray2 = CopyAnimatedSpriteToScreenArrayZoom(SmallInvader,h=25,v=16, ZoomFactor=2,TheScreenArray=ScreenArray2)
          ScreenArray2 = CopyAnimatedSpriteToScreenArrayZoom(TinyInvader,h=45,v=17, ZoomFactor=2,TheScreenArray=ScreenArray2)

          TransitionBetweenScreenArrays(ScreenArray1,ScreenArray2,TransitionType=2)


          for x in range (1,100):
            CopyAnimatedSpriteToPixelsZoom(SpaceInvader,h=0,v=8, ZoomFactor=2)
            SpaceInvader.IncrementFrame()
            CopyAnimatedSpriteToPixelsZoom(SmallInvader,h=25,v=16, ZoomFactor=2)
            SmallInvader.IncrementFrame()
            CopyAnimatedSpriteToPixelsZoom(TinyInvader,h=45,v=17, ZoomFactor=2)
            TinyInvader.IncrementFrame()
            time.sleep(0.08)

          #Check Time
          if (ClockSprite.hhmm != datetime.now().strftime('%H:%M')):
            print("ClockSprite.hhm: ",ClockSprite.hhmm, "Other:",datetime.now().strftime('%H:%M'))
            #ClearBuffers() #clean the internal graphic buffers
            ClockSprite = CreateClockSprite(hh)
            CopySpriteToPixelsZoom(ClockSprite,h,0,(150,0,0),(0,0,0),2,Fill=True)


          ClockSprite = CreateClockSprite(hh)
          ScreenArray2 = CopySpriteToScreenArrayZoom(ClockSprite,h=h,v=0,ColorTuple=(150,0,0),FillerTuple=(0,0,0),ZoomFactor=2,Fill=True)
          TransitionBetweenScreenArrays(ScreenArray1,ScreenArray2,TransitionType=2)




        #Chicken
        if (r==4):

          r = random.randint(1,3)


          print("Starting chicken running")
          ClockSprite = CreateClockSprite(hh)
          h = HatWidth - (ClockSprite.width * 2)
          ScreenArray1 = CopySpriteToScreenArrayZoom(ClockSprite,h=h,v=0,ColorTuple=(150,0,0),FillerTuple=(0,0,0),ZoomFactor=2,Fill=True)

          #Start with empty, copy current time to it
          ScreenArray2 = copy.deepcopy(EmptyArray)
          ScreenArray2 = CopySpriteToScreenArrayZoom(ClockSprite,h=h,v=0,ColorTuple=(150,0,0),FillerTuple=(0,0,0),ZoomFactor=2,Fill=True,InputScreenArray=ScreenArray2)
          TransitionBetweenScreenArrays(ScreenArray1,ScreenArray2,TransitionType=2)




          MoveAnimatedSpriteAcrossScreenStepsPerFrame(
            ChickenRunning,
            Position      = 'bottom',
            Vadjust       = 1 * r,
            direction     = "left",
            StepsPerFrame = r,
            ZoomFactor    = r,
            sleep         = 0.03 / r
            )
          

          #Check Time
          #if (ClockSprite.hhmm != datetime.now().strftime('%H:%M')):
          #  print("ClockSprite.hhm: ",ClockSprite.hhmm, "Other:",datetime.now().strftime('%H:%M'))
          #  #ClearBuffers() #clean the internal graphic buffers
          #  ClockSprite = CreateClockSprite(hh)
          #  CopySpriteToPixelsZoom(ClockSprite,h,0,(150,0,0),(0,0,0),2,Fill=True)


          #Check Time
          if (ClockSprite.hhmm != datetime.now().strftime('%H:%M')):
            print("ClockSprite.hhm: ",ClockSprite.hhmm, "Other:",datetime.now().strftime('%H:%M'))
            #ClearBuffers() #clean the internal graphic buffers

            ScreenArray1 = CopySpriteToScreenArrayZoom(ClockSprite,ClockH,0,  (150,0,0),(0,0,0),ZoomFactor=1,Fill=True)
            ClockSprite = CreateClockSprite(hh)

            ScreenArray2 = CopySpriteToScreenArrayZoom(ClockSprite,ClockH,0,  (150,0,0),(0,0,0),ZoomFactor=1,Fill=True)
            TransitionBetweenScreenArrays(ScreenArray1,ScreenArray2)
            #CopySpriteToPixelsZoom(ClockSprite,ClockH,0,(150,0,0),(0,0,0),2,Fill=True)



          ClockSprite = CreateClockSprite(hh)
          ScreenArray2 = CopySpriteToScreenArrayZoom(ClockSprite,h=h,v=0,ColorTuple=(150,0,0),FillerTuple=(0,0,0),ZoomFactor=2,Fill=True)
          TransitionBetweenScreenArrays(ScreenArray1,ScreenArray2,TransitionType=2)



        #animated ships (no gravity, flying around like insects)
        if (r==5):

          print("Starting animated ships no gravity")
          ClockSprite = CreateClockSprite(hh)
          h = HatWidth - (ClockSprite.width * 2)
          ScreenArray1 = CopySpriteToScreenArrayZoom(ClockSprite,h=h,v=0,ColorTuple=(150,0,0),FillerTuple=(0,0,0),ZoomFactor=2,Fill=True)

          #Start with empty, copy current time to it
          ScreenArray2 = copy.deepcopy(EmptyArray)
          ScreenArray2 = CopySpriteToScreenArrayZoom(ClockSprite,h=h,v=0,ColorTuple=(150,0,0),FillerTuple=(0,0,0),ZoomFactor=2,Fill=True,InputScreenArray=ScreenArray2)
          TransitionBetweenScreenArrays(ScreenArray1,ScreenArray2,TransitionType=2)


         



          h = HatWidth - (ClockSprite.width * 2)
          ClockSprite = CreateClockSprite(hh)
          ScreenArray = CopySpriteToScreenArrayZoom(ClockSprite,h=h,v=0,ColorTuple=(150,0,0),FillerTuple=(0,0,0),ZoomFactor=2,Fill=True,InputScreenArray=ScreenArray)

          #Make a screen array (buffer)
          #copy sprite frames
          #fade with falling sand
          ScreenArray1 = copy.deepcopy(ScreenArray)
          ScreenArray2 = copy.deepcopy(EmptyArray)
          TransitionBetweenScreenArrays(ScreenArray2,ScreenArray1,TransitionType=2)





          ship1 = random.randint(0,4)
          ShipSprites[ship1].framerate = 2
          ShipSprites[ship1].InitializeScreenArray()

          ship2 = random.randint(5,9)
          ShipSprites[ship2].framerate = 2
          ShipSprites[ship2].InitializeScreenArray()
                             
          ship3 = random.randint(10,15)
          ShipSprites[ship3].framerate = 2
          ShipSprites[ship3].InitializeScreenArray()

          h1,v1 = 0,0
          h2,v2 = 20,0
          h3,v3 = 50,20

          #ElectricExplosions
          Explosion1 = copy.deepcopy(ElectricZap)
          Explosion1.framerate = 1
          Explosion1.h = -1
          Explosion1.v = -1
          Explosion2 = copy.deepcopy(ElectricZap)
          Explosion2.framerate = 1
          Explosion2.h = -1
          Explosion2.v = -1
          Explosion3 = copy.deepcopy(ElectricZap)
          Explosion3.framerate = 1
          Explosion3.h = -1
          Explosion3.v = -1




          #print ("ElectricZap frames:",ElectricZap.frames)
          #print ("Explosion1  frames:",Explosion1.frames)

          for x in range (1,500):

            h,v = h1,v1
            h1,v1 = RandomMove(h1,v1,ShipSprites[ship1])
            #h1,v1 = RandomMove(h1,v1,ShipSprites[ship1])
            ShipSprites[ship1].h, ShipSprites[ship1].v = h1,v1
            if (CheckForCollision(ShipSprites[ship1], ShipSprites[ship2]) or
                CheckForCollision(ShipSprites[ship1], ShipSprites[ship3])):
              ShipSprites[ship1].direction = ReverseDirection8Way(ShipSprites[ship1].direction)
              h1,v1 = h,v
            if (CheckForCollision(ShipSprites[ship1], ClockAreaSprite)):              
              Explosion1.exploding = 1
              Explosion1.h = round(h)
              Explosion1.v = round(v)

              ShipSprites[ship1].direction = ReverseDirection8Way(ShipSprites[ship1].direction)
              h1,v1 = random.randint(0,HatWidth)-ShipSprites[ship1].width,HatHeight-ShipSprites[ship1].height

            ShipSprites[ship1].IncrementFrame()
            ShipSprites[ship1].EraseFrame(h,v,frame=-1)
            #If this sprite has collided, use old HV instead 
            CopyAnimatedSpriteToPixelsZoom(ShipSprites[ship1],h=h1,v=v1, ZoomFactor=1)

            h,v = h2,v2
            h2,v2 = RandomMove(h2,v2,ShipSprites[ship2])
            ShipSprites[ship2].h, ShipSprites[ship2].v = h2,v2
            if (CheckForCollision(ShipSprites[ship2], ShipSprites[ship1]) or
                CheckForCollision(ShipSprites[ship2], ShipSprites[ship3])):
              ShipSprites[ship2].direction = ReverseDirection8Way(ShipSprites[ship2].direction)
              h2,v2 = h,v
                
            if (CheckForCollision(ShipSprites[ship2], ClockAreaSprite)):              
              Explosion2.exploding = 1
              Explosion2.h = round(h)
              Explosion2.v = round(v)
              ShipSprites[ship2].direction = ReverseDirection8Way(ShipSprites[ship2].direction)
              h2,v2 = random.randint(0,HatWidth)-ShipSprites[ship1].width,HatHeight-ShipSprites[ship2].height
              
            ShipSprites[ship2].IncrementFrame()
            ShipSprites[ship2].EraseFrame(h,v,frame=-1)
            CopyAnimatedSpriteToPixelsZoom(ShipSprites[ship2],h=h2,v=v2, ZoomFactor=1)



            h,v = h3,v3
            h3,v3 = RandomMove(h3,v3,ShipSprites[ship3])
            ShipSprites[ship3].h, ShipSprites[ship3].v = h3,v3
            if (CheckForCollision(ShipSprites[ship3], ShipSprites[ship2]) or
                CheckForCollision(ShipSprites[ship3], ShipSprites[ship1])): 
              ShipSprites[ship3].direction = ReverseDirection8Way(ShipSprites[ship3].direction)
              h3,v3 = h,v

            if (CheckForCollision(ShipSprites[ship3], ClockAreaSprite)):              
              Explosion3.exploding = 1
              Explosion3.h = round(h)
              Explosion3.v = round(v)

              ShipSprites[ship3].direction = ReverseDirection8Way(ShipSprites[ship3].direction)
              h3,v3 = random.randint(0,HatWidth)-ShipSprites[ship1].width,HatHeight-ShipSprites[ship3].height

            ShipSprites[ship3].IncrementFrame()
            ShipSprites[ship3].EraseFrame(h,v,frame=-1)
            CopyAnimatedSpriteToPixelsZoom(ShipSprites[ship3],h=h3,v=v3, ZoomFactor=1)




            if (Explosion1.exploding == 1 ):
              Explosion1.DisplayAnimated(Explosion1.h,Explosion1.v)


              #Kill UFOMissile after explosion animation is complete
              if (Explosion1.currentframe >= Explosion1.frames):
                Explosion1.EraseFrame(Explosion1.h,Explosion1.v)
                Explosion1.currentframe = 1
                Explosion1.exploding    = 0
                Explosion1.alive        = 0
                Explosion1.h = -1
                Explosion1.v = -1

              
            if (Explosion2.exploding == 1 ):
              Explosion2.DisplayAnimated(Explosion2.h,Explosion2.v)


              #Kill UFOMissile after explosion animation is complete
              if (Explosion2.currentframe >= Explosion2.frames):
                Explosion2.EraseFrame(Explosion2.h,Explosion2.v)
                Explosion2.currentframe = 1
                Explosion2.exploding    = 0
                Explosion2.alive        = 0
                Explosion2.h = -1
                Explosion2.v = -1

            if (Explosion3.exploding == 1 ):
              Explosion3.DisplayAnimated(Explosion3.h,Explosion3.v)


              #Kill UFOMissile after explosion animation is complete
              if (Explosion3.currentframe >= Explosion3.frames):
                Explosion3.EraseFrame(Explosion3.h,Explosion3.v)
                Explosion3.currentframe = 1
                Explosion3.exploding    = 0
                Explosion3.alive        = 0
                Explosion3.h = -1
                Explosion3.v = -1



            #Check Time
            #if (ClockSprite.hhmm != datetime.now().strftime('%H:%M')):
            #  print("ClockSprite.hhm: ",ClockSprite.hhmm, "Other:",datetime.now().strftime('%H:%M'))
            #  #ClearBuffers() #clean the internal graphic buffers
            #  ClockSprite = CreateClockSprite(hh)
            #  CopySpriteToPixelsZoom(ClockSprite,ClockH,0,(150,0,0),(0,0,0),2,Fill=True)


            #Check Time
            if (ClockSprite.hhmm != datetime.now().strftime('%H:%M')):
              print("ClockSprite.hhm: ",ClockSprite.hhmm, "Other:",datetime.now().strftime('%H:%M'))
              #ClearBuffers() #clean the internal graphic buffers

              ScreenArray1 = CopySpriteToScreenArrayZoom(ClockSprite,ClockH,0,  (150,0,0),(0,0,0),ZoomFactor=2,Fill=True)
              ClockSprite = CreateClockSprite(hh)

              ScreenArray2 = CopySpriteToScreenArrayZoom(ClockSprite,ClockH,0,  (150,0,0),(0,0,0),ZoomFactor=2,Fill=True)
              TransitionBetweenScreenArrays(ScreenArray1,ScreenArray2)
              #CopySpriteToPixelsZoom(ClockSprite,ClockH,0,(150,0,0),(0,0,0),2,Fill=True)



            time.sleep(0.03)
            
          

          ClockSprite = CreateClockSprite(hh)
          ScreenArray2 = CopySpriteToScreenArrayZoom(ClockSprite,h=h,v=0,ColorTuple=(150,0,0),FillerTuple=(0,0,0),ZoomFactor=2,Fill=True)
          TransitionBetweenScreenArrays(ScreenArray1,ScreenArray2,TransitionType=2)



        #animated ships with gravity
        if (r==6):

          print("Starting Animated ships with gravity")
          ClockSprite = CreateClockSprite(hh)
          h = HatWidth - (ClockSprite.width * 2)
          ScreenArray1 = CopySpriteToScreenArrayZoom(ClockSprite,h=h,v=0,ColorTuple=(150,0,0),FillerTuple=(0,0,0),ZoomFactor=2,Fill=True)

          #Start with empty, copy current time to it
          ScreenArray2 = copy.deepcopy(EmptyArray)
          ScreenArray2 = CopySpriteToScreenArrayZoom(ClockSprite,h=h,v=0,ColorTuple=(150,0,0),FillerTuple=(0,0,0),ZoomFactor=2,Fill=True,InputScreenArray=ScreenArray2)
          TransitionBetweenScreenArrays(ScreenArray1,ScreenArray2,TransitionType=2)



          #Initialize 3 ships
          ship1 = random.randint(0,8)
          ship2 = random.randint(9,17)
          ship3 = random.randint(18,27)
          
          h1,v1 = 0,0
          h2,v2 = 20,0
          h3,v3 = 50,20

          #ElectricExplosions
          Explosion1 = copy.deepcopy(ElectricZap)
          Explosion1.framerate = 1
          Explosion1.h = -1
          Explosion1.v = -1
          Explosion2 = copy.deepcopy(ElectricZap)
          Explosion2.framerate = 1
          Explosion2.h = -1
          Explosion2.v = -1
          Explosion3 = copy.deepcopy(ElectricZap)
          Explosion3.framerate = 1
          Explosion3.h = -1
          Explosion3.v = -1




          ShipSprites[ship1].h = random.randint(0,10)
          ShipSprites[ship1].v = 0
          ShipSprites[ship1].velocityH = 1 * random.random()
          ShipSprites[ship1].velocityV = 1 * random.random()
          ShipSprites[ship1].InitializeScreenArray()

          ShipSprites[ship2].h = random.randint(11,20)
          ShipSprites[ship2].v = 15
          ShipSprites[ship2].velocityH = 2 * random.random()
          ShipSprites[ship2].velocityV = 2 * random.random()
          ShipSprites[ship2].InitializeScreenArray()

          ShipSprites[ship3].h = random.randint(0,10)
          ShipSprites[ship3].v = 25
          ShipSprites[ship3].velocityH = 3 * random.random()
          ShipSprites[ship3].velocityV = 3 * random.random()
          ShipSprites[ship3].InitializeScreenArray()
          
          ShipSprites[ship1].framerate = 1
          ShipSprites[ship2].framerate = 1
          ShipSprites[ship3].framerate = 1
          

          #Bounce(ShipSprites[ship1])

          print("ShipName:",ShipSprites[ship1].name)
          print("ShipName:",ShipSprites[ship2].name)
          print("ShipName:",ShipSprites[ship3].name)

          for x in range (1,2000):
            #maybe only increment the frame ever X seconds (use a timer?)
            MoveSpriteWithGravity(ShipSprites[ship1])
            MoveSpriteWithGravity(ShipSprites[ship2])
            MoveSpriteWithGravity(ShipSprites[ship3])

            #The logic needs to be reworked and simplified
            #we want the critters to bounce off the clock and each other
            #when they hit the lock area an explosion / spark will appear
            #and they are pushed back with a little bit of energy
            #BounceFromCollision and CheckForCollision could be merged
            BounceFromCollision(ShipSprites[ship1],ClockAreaSprite)
            if (CheckForCollision(ShipSprites[ship1],ClockAreaSprite)):              
              Explosion1.exploding = 1
              MoveSpriteWithGravity(ShipSprites[ship1])
              MoveSpriteWithGravity(ShipSprites[ship1])

            DisplayExplosionIfExploding(Explosion1,ShipSprites[ship1].h,ShipSprites[ship1].v)
            BounceFromCollision(ShipSprites[ship1],ShipSprites[ship2])
            BounceFromCollision(ShipSprites[ship1],ShipSprites[ship3])


            BounceFromCollision(ShipSprites[ship2],ClockAreaSprite)
            if (CheckForCollision(ShipSprites[ship2],ClockAreaSprite)):              
              Explosion2.exploding = 1
              MoveSpriteWithGravity(ShipSprites[ship2])
              MoveSpriteWithGravity(ShipSprites[ship2])

            DisplayExplosionIfExploding(Explosion2,ShipSprites[ship2].h,ShipSprites[ship2].v)
            BounceFromCollision(ShipSprites[ship2],ShipSprites[ship1])
            BounceFromCollision(ShipSprites[ship2],ShipSprites[ship3])


            BounceFromCollision(ShipSprites[ship3],ClockAreaSprite)
            if (CheckForCollision(ShipSprites[ship3],ClockAreaSprite)):              
              Explosion3.exploding = 1
              MoveSpriteWithGravity(ShipSprites[ship3])
              MoveSpriteWithGravity(ShipSprites[ship3])
            DisplayExplosionIfExploding(Explosion3,ShipSprites[ship3].h,ShipSprites[ship3].v)
            BounceFromCollision(ShipSprites[ship3],ShipSprites[ship1])
            BounceFromCollision(ShipSprites[ship3],ShipSprites[ship2])


            RandomBounceFromFloor(ShipSprites[ship1])
            if(ShipSprites[ship1].velocityV < 0.001):
              Explosion1.exploding
            RandomBounceFromFloor(ShipSprites[ship2])
            RandomBounceFromFloor(ShipSprites[ship3])

            #advance frame every X ticks
            m,r = divmod(x,TICKSPERFRAME)
            if (r == 0):
              ShipSprites[ship1].IncrementFrame()
              ShipSprites[ship2].IncrementFrame()
              ShipSprites[ship3].IncrementFrame()
            time.sleep(0.007)
            
            

            #Check Time
            if (ClockSprite.hhmm != datetime.now().strftime('%H:%M')):
              print("ClockSprite.hhm: ",ClockSprite.hhmm, "Other:",datetime.now().strftime('%H:%M'))
              #ClearBuffers() #clean the internal graphic buffers

              ScreenArray1 = CopySpriteToScreenArrayZoom(ClockSprite,ClockH,0,  (150,0,0),(0,0,0),ZoomFactor=2,Fill=True)
              ClockSprite = CreateClockSprite(hh)

              ScreenArray2 = CopySpriteToScreenArrayZoom(ClockSprite,ClockH,0,  (150,0,0),(0,0,0),ZoomFactor=2,Fill=True)
              TransitionBetweenScreenArrays(ScreenArray1,ScreenArray2)
              #CopySpriteToPixelsZoom(ClockSprite,ClockH,0,(150,0,0),(0,0,0),2,Fill=True)


          


          ClockSprite = CreateClockSprite(hh)
          ScreenArray2 = CopySpriteToScreenArrayZoom(ClockSprite,h=h,v=0,ColorTuple=(150,0,0),FillerTuple=(0,0,0),ZoomFactor=2,Fill=True)
          TransitionBetweenScreenArrays(ScreenArray,ScreenArray2,TransitionType=2)


          #ShipSprites[ship1].EraseZoom(h1,v1)
          #ShipSprites[ship2].EraseZoom(h2,v2)
          #ShipSprites[ship3].EraseZoom(h3,v3)

        
        
        
        #rSpiderLeg
        if (r==7):
          print("Starting Spider Leg")
          #ScreenArray = copy.deepcopy(EmptyArray)
          ClockSprite = CreateClockSprite(hh)
          h = HatWidth - (ClockSprite.width * 2)
          ScreenArray1 = CopySpriteToScreenArrayZoom(ClockSprite,h=h,v=0,ColorTuple=(150,0,0),FillerTuple=(0,0,0),ZoomFactor=2,Fill=True)

          #Start with empty, copy current time to it
          ScreenArray2 = copy.deepcopy(EmptyArray)
          ScreenArray2 = CopySpriteToScreenArrayZoom(ClockSprite,h=h,v=0,ColorTuple=(150,0,0),FillerTuple=(0,0,0),ZoomFactor=2,Fill=True,InputScreenArray=ScreenArray2)
          ScreenArray2 = CopyAnimatedSpriteToScreenArrayZoom(BigSpiderLegOutSprite,h=0,v=(HatHeight-BigSpiderLegOutSprite.height),ZoomFactor=1,TheScreenArray=ScreenArray2)
         
          TransitionBetweenScreenArrays(ScreenArray1,ScreenArray2,TransitionType=2)


         
          
          
          for x in range (1,200):
            CopyAnimatedSpriteToPixelsZoom(BigSpiderLegOutSprite,h=0,v=HatHeight-BigSpiderLegOutSprite.height, ZoomFactor=1)
            BigSpiderLegOutSprite.IncrementFrame()
            time.sleep(0.05)
            
          

          #Check Time
          if (ClockSprite.hhmm != datetime.now().strftime('%H:%M')):
            print("ClockSprite.hhm: ",ClockSprite.hhmm, "Other:",datetime.now().strftime('%H:%M'))
            #ClearBuffers() #clean the internal graphic buffers
            ClockSprite = CreateClockSprite(hh)
            CopySpriteToPixelsZoom(ClockSprite,h,0,(150,0,0),(0,0,0),2,Fill=True)


          #Fade to Black
          #ScreenArray1 = copy.deepcopy(EmptyArray)
          #ScreenArray2 = copy.deepcopy(ScreenArray)
          #TransitionBetweenScreenArrays(ScreenArray2,ScreenArray1,TransitionType=2)
          #ScreenArray = copy.deepcopy(EmptyArray)


          #DotZerkRobotWalking.EraseZoom(0,16,2)
          #DotZerkRobotWalkingSmall.EraseZoom(40,22,2)

          ClockSprite = CreateClockSprite(hh)
          ScreenArray2 = CopySpriteToScreenArrayZoom(ClockSprite,h=h,v=0,ColorTuple=(150,0,0),FillerTuple=(0,0,0),ZoomFactor=2,Fill=True)
          TransitionBetweenScreenArrays(ScreenArray,ScreenArray2,TransitionType=2)



        #This will end the while loop
        elapsed_time = time.time() - StartTime
        elapsed_hours, rem = divmod(elapsed_time, 3600)
        elapsed_minutes, elapsed_seconds = divmod(rem, 60)

        #print ("StartTime:    ",StartTime, " Now:",time.time())
        print("ElapsedMinutes: ",elapsed_minutes)
        if elapsed_minutes >= RunMinutes:
          Done = True


        #Check EventQueue (webhook data from twitch and patreon)
        #print("Checking the EventQueue for any incoming requests")
        #QueueCount = EventQueue.qsize()
        #print("QueueCount: ",QueueCount)
        #if (QueueCount > 0):
        #  Done = True





    #Starry Night Clock
    elif (ClockStyle == 3):

      #This will end the while loop
      elapsed_time = time.time() - StartTime
      elapsed_hours, rem = divmod(elapsed_time, 3600)
      elapsed_minutes, elapsed_seconds = divmod(rem, 60)

      #print ("StartTime:    ",StartTime, " Now:",time.time())
      print("ElapsedMinutes: ",elapsed_minutes)
      if elapsed_minutes >= RunMinutes:
        Done = True


      #Check EventQueue (webhook data from twitch and patreon)
      #print("Checking the EventQueue for any incoming requests")
      #QueueCount = EventQueue.qsize()
      #print("QueueCount: ",QueueCount)
      #if (QueueCount > 0):
      #  Done = True



      ClockH = HatWidth - (ClockSprite.width * 2)
      ClockSprite = CreateClockSprite(hh)
      #we need to make a fake sprite to take the place of the clock which is zoomed)
      ClockAreaSprite = Sprite((ClockSprite.width*2)+3,(ClockSprite.height*2),0,0,0,[])
      ClockAreaSprite.h = ClockH -3
      ClockAreaSprite.v = 1
      #CopySpriteToScreenArrayZoom(ClockSprite,h=ClockH,v=0,ColorTuple=(150,0,0),FillerTuple=(0,0,0),ZoomFactor=2,Fill=True)

      #--------------------------------
      #-- Create Layers              --
      #--------------------------------

      Background   = Layer(name="backround", width=2024, height=32,h=0,v=0)
      Middleground = Layer(name="backround", width=2024, height=32,h=0,v=0)
      Foreground   = Layer(name="backround", width=2024, height=32,h=0,v=0)

      Background.CreateStars(0,0,50,50)
      Middleground.CreateStars(0,0,100,100)
      Foreground.CreateStars(0,0,200,200)

      Canvas = TheMatrix.CreateFrameCanvas()
      Canvas.Clear()
      Canvas = TheMatrix.SwapOnVSync(Canvas)

     
      count  = 0
      bx     = 0
      mx     = 0
      fx     = 0
      bwidth = Background.width    - HatWidth
      mwidth = Middleground.width  - HatWidth
      fwidth = Foreground.width    - HatWidth
      brate  = 4
      mrate  = 2
      frate  = 1
      h = HatWidth - ClockSprite.width * ZoomFactor - 2
      v = 2
      
      if(HatWidth > 64):
        rmH = 0
        rmV = 13
      else:
        rmH = -2
        rmV = 13


  
      while (Done == False):

        if StopEvent and StopEvent.is_set():
            print("[LED] Stop requested — exiting early.")
            Done = True
            #--> Put a transition effect here
            break



        if (ClockSprite.hhmm != datetime.now().strftime('%H:%M')):
          print("[LEDarcade][DisplayDigitalClock] Time:", datetime.now().strftime('%H:%M'))
          ClockSprite = CreateClockSprite(hh)
          h = HatWidth - ClockSprite.width * ZoomFactor - 2

          #ScreenArray = CopySpriteToScreenArrayZoom(ClockSprite,45,0,(150,0,0),(0,0,0),1,Fill=True)
  
        x = 0

        #main counter
        count = count + 1
        Canvas.Clear()
      
        #Background
        m,r = divmod(count,brate)
        if(r == 0):
          bx = bx + 1
          if(bx > bwidth):
            bx = 0
        Canvas = Background.PaintOnCanvas(bx,0,Canvas)


        #Middleground
        m,r = divmod(count,mrate)
        if(r == 0):
          mx = mx + 1
          if(mx > mwidth):
            mx = 0
        Canvas = Middleground.PaintOnCanvas(mx,0,Canvas)

          
        #foreground
        m,r = divmod(count,frate)
        if(r == 0):
          fx = fx + 1
          if(fx > fwidth):
            fx = 0
        Canvas = Foreground.PaintOnCanvas(fx,0,Canvas)

        #LED.RunningMan3Sprite.DisplayAnimated(10,10)
        Canvas = RunningMan3Sprite.PaintAnimatedToCanvas(rmH,rmV,Canvas)
        Canvas = CopySpriteToCanvasZoom(ClockSprite,h,v,(0,100,0),(0,5,0),ZoomFactor,False,Canvas)
      

        Canvas = TheMatrix.SwapOnVSync(Canvas)
        

        
        if(random.randint(0,1000) == 1):
          #This will end the while loop
          elapsed_time = time.time() - StartTime
          elapsed_hours, rem = divmod(elapsed_time, 3600)
          elapsed_minutes, elapsed_seconds = divmod(rem, 60)

          #print ("StartTime:    ",StartTime, " Now:",time.time())
          print("ElapsedMinutes: ",elapsed_minutes)
          if elapsed_minutes >= RunMinutes:
            Done = True

        #if(random.randint(0,100) == 1):
          #Check EventQueue (webhook data from twitch and patreon)
          #print("Checking the EventQueue for any incoming requests")
          #QueueCount = EventQueue.qsize()
          #print("QueueCount: ",QueueCount)
          #if (QueueCount > 0):
          #  print ("Queue is not empty.  Setting Done = True")
          #  Done = True



        #time.sleep(ScrollSleep)
        time.sleep(ScrollSleep)


    #Retro Font
    elif (ClockStyle == 4):
      DisplayCustomFontClock(StopEvent)
      Done = True

    #Blasteroids
    elif (ClockStyle == 5):
      import Blasteroids as BL
      BL.LaunchBlasteroids(Duration=100000, ShowIntro=False, StopEvent=StopEvent)        
      Done = True







#------------------------------------------------------------------------------
#  TWITCH DISPLAY                                                            --
#------------------------------------------------------------------------------



# This function will be called by an asyncio process
# The calling module will be able to continue to monitor Twitch stream and chat
# This function will check a global variable to determine if it should exit early

def DisplayTwitchTimer(
  CenterHoriz = False,
  CenterVert  = False,
  h           = 0,
  v           = 0,
  hh          = 24,
  RGB         = MedBlue,
  ShadowRGB   = ShadowBlue,
  ZoomFactor  = 2,
  AnimationDelay = 10,
  ScrollSleep    = 0.02,
  RunMinutes     = 1,
  StartDateTimeUTC  = '',
  HHMMSS            = '00:00:00',
  DisplayNumber1    = 0,
  DisplayNumber2    = 0,
  StopEvent         = ''
  
  ):
    

    

    #ClearBigLED()
    #ClearBuffers()
    global ScreenArray
    

    
    TimerSprite = CreateTimerSprite(HHMMSS)
    Done        = False
    StartTime   = time.time()
    #print("RunMinutes:",RunMinutes)

    if (CenterHoriz == True):
      h = round((HatWidth  // 2)  - ((TimerSprite.width * ZoomFactor) // 2) + 1)

    if (CenterVert  == True):
      v = round((HatHeight // 2) - ((TimerSprite.height * ZoomFactor) // 2) - ZoomFactor)
   
    #print("HV",h,v)





    #MakeAndShowClock(hh,h,v,RGB,ShadowGreen,ZoomFactor,Fill=False)
    ScreenArray1  = ([[]])
    ScreenArray1  = [[ (0,0,0) for i in range(HatWidth)] for i in range(HatHeight)]
    ScreenArray2  = ([[]])
    ScreenArray2  = [[ (0,0,0) for i in range(HatWidth)] for i in range(HatHeight)]
    ClockSprite = CreateClockSprite(hh)


    ScreenArray1 = CopySpriteToScreenArrayZoom(TimerSprite,h-1,v+1,ShadowRGB,(0,0,0),ZoomFactor=ZoomFactor,Fill=False)
    ScreenArray1 = CopySpriteToScreenArrayZoom(TimerSprite,h,v,RGB,(0,0,0),ZoomFactor=ZoomFactor,Fill=False,InputScreenArray=ScreenArray1)
    #TransitionBetweenScreenArrays(ScreenArray2,ScreenArray1,TransitionType=2)


    #This will be displayed under the clock
    message = "Uptime"
    BannerSprite = CreateBannerSprite(message)
    BannerSprite.h = round((HatWidth - BannerSprite.width) / 2)
    BannerSprite.v = 19
    BannerSprite.RGB = (50,0,150)
    BannerSprite.ZoomFactor = 1
    ScreenArray = CopySpriteToScreenArrayZoom(BannerSprite,BannerSprite.h,BannerSprite.v,BannerSprite.RGB,(0,0,0),ZoomFactor=1,Fill=False,InputScreenArray=ScreenArray1)


    try:  
      #MakeAndShowClock(hh,h,v,RGB,ShadowGreen,ZoomFactor,Fill=True)
      TimerSprite = UpdateTimerWithTransition(TimerSprite,BannerSprite,h,v,    RGB,          ShadowRGB,            ZoomFactor,  Fill=True, TransitionType=2,StartDateTimeUTC = StartDateTimeUTC,ForceUpdate=True)
    except Exception as e:
            print(f"[ERROR] LED.DisplayTwitchTimer crashed: {e}")

    
    #TransitionBetweenScreenArrays(ScreenArray2,ScreenArray,TransitionType=2)
    #CopyScreenArrayToCanvasVSync(ScreenArray)
    
    


    
    LastAnimation = time.time()

    
    #Show the timer, sleep for X seconds, show animations every Y seconds
    while (Done == False):
    
      if StopEvent and StopEvent.is_set():
        print("[LED] Stop requested — exiting early.")
        Done = True
        #--> Put a transition effect here
        break

    
      #print("while loop")
      TimerSprite = UpdateTimerWithTransition(TimerSprite,BannerSprite,h,v,RGB,ShadowRGB,ZoomFactor,Fill=True,TransitionType=2,StartDateTimeUTC = StartDateTimeUTC)
      #ScreenArray = CopySpriteToScreenArrayZoom(BannerSprite,h1,v1,BannerRGB,(0,0,0),ZoomFactor=1,Fill=False,InputScreenArray=ScreenArray)

      #print("Asyncio sleep")




      #check and exit
      if(Done == True):
        return

      #Check for animation time
      hh1,mmm1,ss1 = GetElapsedTime(LastAnimation,time.time())
      if(ss1 >= AnimationDelay):
        #print("animation delay")
        LastAnimation = time.time()

        TimerSprite = UpdateTimerWithTransition(TimerSprite,BannerSprite,h,v,RGB,ShadowRGB,ZoomFactor,Fill=True,StartDateTimeUTC = StartDateTimeUTC)

        random.seed(time.time())
        r = random.randint(1,13)
        #print("random animation:",r)
        if (r == 1):
          #ShowScreenArray(ScreenArray)
          #MakeAndShowClock(hh,h,v,RGB,ShadowGreen,ZoomFactor,Fill=True)

          RunningMan2Sprite.ScrollAcrossScreen(20,15,'right', ScrollSleep )
          RunningMan2Sprite.HorizontalFlip()
          Rezonator.ScrollAcrossScreen(20,(HatHeight - Rezonator.height),'right', ScrollSleep )
          RunningMan2Sprite.ScrollAcrossScreen(20,15,'left',0.02 )
          Rezonator.ScrollAcrossScreen(20,(HatHeight - Rezonator.height),'left', ScrollSleep )
          RunningMan2Sprite.HorizontalFlip()

        elif (r == 2):
          #ShowScreenArray(ScreenArray)
          #MakeAndShowClock(hh,h,v,RGB,ShadowGreen,ZoomFactor,Fill=True)
          r = random.randint(1,2)
          MoveAnimatedSpriteAcrossScreen(BigSpiderWalkingSprite,Position='bottom',direction="right",steps=14*r,ZoomFactor=r,sleep=0.05)
          BigSpiderWalkingSprite.HorizontalFlip()
          r = random.randint(1,2)
          MoveAnimatedSpriteAcrossScreen(BigSpiderWalkingSprite,Position='bottom',direction="left",steps=14*r,ZoomFactor=r,sleep=0.03)
          BigSpiderWalkingSprite.HorizontalFlip()

        elif (r == 3):
          #MakeAndShowClock(hh,h,v,RGB,ShadowGreen,ZoomFactor,Fill=False)
          #ShowScreenArray(ScreenArray)

          MoveAnimatedSpriteAcrossScreenFramesPerStep(
            ThreeGhostPacSprite,
            Position      = 'bottom',
            direction     = "right",
            FramesPerStep = 1,
            ZoomFactor    = random.randint(1,2),
            sleep         = 0.03
            )
          

          MoveAnimatedSpriteAcrossScreenFramesPerStep(
            ThreeBlueGhostPacSprite,
            Position      = 'bottom',
            direction     = "left",
            FramesPerStep = 1,
            ZoomFactor    = random.randint(1,2),
            sleep         = 0.02
            )

          #This one works better for big animations
          #MoveAnimatedSpriteAcrossScreen(
          #      ThreeGhostPacSprite,
          #      v             = 15,
          #      direction     = "right",
          #      steps         = 2,
          #      ZoomFactor    = 3,
          #      sleep         = 0
          #      )
              

        elif (r == 4):
          #MakeAndShowClock(hh,h,v,RGB,ShadowGreen,ZoomFactor,Fill=False)


          #ShowScreenArray(ScreenArray)

          SpaceInvader.framerate = 2
          SpaceInvader.InitializeScreenArray()
          SmallInvader.framerate = 2
          SmallInvader.InitializeScreenArray()
          TinyInvader.framerate  = 1
          TinyInvader.InitializeScreenArray()


          MoveAnimatedSpriteAcrossScreenStepsPerFrame(
            SpaceInvader,
            Position      = 'bottom',
            direction     = "right",
            StepsPerFrame = 4,
            ZoomFactor    = random.randint(1,3),
            sleep         = 0.03
            )


          MoveAnimatedSpriteAcrossScreenStepsPerFrame(
            SmallInvader,
            Position      = 'bottom',
            direction     = "right",
            StepsPerFrame = 4,
            ZoomFactor    = random.randint(1,3),
            sleep         = 0.03
            )


          MoveAnimatedSpriteAcrossScreenStepsPerFrame(
            TinyInvader,
            Position      = 'bottom',
            direction     = "right",
            StepsPerFrame = 4,
            ZoomFactor    = random.randint(1,3),
            sleep         = 0.03
            )

        elif (r == 5):
          #ShowScreenArray(ScreenArray)

          #MakeAndShowClock(hh,h,v,RGB,ShadowGreen,ZoomFactor,Fill=False)

          r = random.randint(1,3)
          MoveAnimatedSpriteAcrossScreenStepsPerFrame(
            LittleShipFlying,
            Position      = 'bottom',
            direction     = "right",
            StepsPerFrame = 4 * r,
            ZoomFactor    = r,
            sleep         = 0.03 / r
            )
          LittleShipFlying.HorizontalFlip()

          r = random.randint(1,3)
          MoveAnimatedSpriteAcrossScreenStepsPerFrame(
            LittleShipFlying,
            Position      = 'bottom',
            direction     = "left",
            StepsPerFrame = 4 * r,
            ZoomFactor    = r,
            sleep         = 0.03 / r
            )
          LittleShipFlying.HorizontalFlip()


        elif (r == 6):
          #ShowScreenArray(ScreenArray)

          #MakeAndShowClock(hh,h,v,RGB,ShadowGreen,ZoomFactor,Fill=False)

          MoveAnimatedSpriteAcrossScreenStepsPerFrame(
            DotZerkRobotWalking,
            Position      = 'bottom',
            direction     = "left",
            StepsPerFrame = 2,
            ZoomFactor    = random.randint(1,2),
            sleep         = 0.03
            )
          DotZerkRobotWalking.HorizontalFlip()



          MoveAnimatedSpriteAcrossScreenStepsPerFrame(
            DotZerkRobotWalking,
            Position      = 'bottom',
            direction     = "right",
            StepsPerFrame = 2,
            ZoomFactor    = random.randint(1,2),
            sleep         = 0.03
            )
          DotZerkRobotWalking.HorizontalFlip()


        elif (r == 7):
          #ShowScreenArray(ScreenArray)

          #MakeAndShowClock(hh,h,v,RGB,ShadowGreen,ZoomFactor,Fill=False)

          MoveAnimatedSpriteAcrossScreenStepsPerFrame(
            DotZerkRobotWalkingSmall,
            Position      = 'bottom',
            direction     = "left",
            StepsPerFrame = 2,
            ZoomFactor    = random.randint(1,2),
            sleep         = 0.03
            )
          DotZerkRobotWalkingSmall.HorizontalFlip()

          MoveAnimatedSpriteAcrossScreenStepsPerFrame(
            DotZerkRobotWalkingSmall,
            Position      = 'bottom',
            direction     = "right",
            StepsPerFrame = 2,
            ZoomFactor    = random.randint(1,2),
            sleep         = 0.03
            )
          DotZerkRobotWalkingSmall.HorizontalFlip()



        if (r == 8):
          #ShowScreenArray(ScreenArray)

          #MakeAndShowClock(hh,h,v,RGB,ShadowGreen,ZoomFactor,Fill=False)

          RunningMan3Sprite.ScrollAcrossScreen(20,15,'right', ScrollSleep )
          RunningMan3Sprite.HorizontalFlip()
          RunningMan3Sprite.ScrollAcrossScreen(20,15,'left',0.02 )
          RunningMan3Sprite.HorizontalFlip()


        elif (r == 9):
          #MakeAndShowClock(hh,h,v,RGB,ShadowGreen,ZoomFactor,Fill=False)
          #ShowScreenArray(ScreenArray)

          i = random.randint(0,27)
          ShipSprites[i].InitializeScreenArray()

          MoveAnimatedSpriteAcrossScreenStepsPerFrame(
            ShipSprites[i],
            Position      = 'bottom',
            direction     = "left",
            StepsPerFrame = 1,
            ZoomFactor    = random.randint(1,2),
            sleep         = 0.03
            )
        

          i = random.randint(0,27)
          MoveAnimatedSpriteAcrossScreenStepsPerFrame(
            ShipSprites[i],
            Position      = 'bottom',
            direction     = "right",
            StepsPerFrame = 1,
            ZoomFactor    = random.randint(1,2),
            sleep         = 0.03
            )




          i = random.randint(0,27)
          ShipSprites[i].InitializeScreenArray()

          MoveAnimatedSpriteAcrossScreenStepsPerFrame(
            ShipSprites[i],
            Position      = 'bottom',
            direction     = "left",
            StepsPerFrame = 1,
            ZoomFactor    = random.randint(3,4),
            sleep         = 0.03
            )
        

          i = random.randint(0,27)
          MoveAnimatedSpriteAcrossScreenStepsPerFrame(
            ShipSprites[i],
            Position      = 'bottom',
            direction     = "right",
            StepsPerFrame = 1,
            ZoomFactor    = random.randint(3,4),
            sleep         = 0.03
            )

        elif (r == 10):
          #ShowScreenArray(ScreenArray)

          #MakeAndShowClock(hh,h,v,RGB,ShadowGreen,ZoomFactor,Fill=False)

          MoveAnimatedSpriteAcrossScreenStepsPerFrame(
            LightBike,
            Position      = 'bottom',
            direction     = "left",
            StepsPerFrame = 2,
            ZoomFactor    = 1,
            sleep         = 0.01
            )
          LightBike.HorizontalFlip()
          MoveAnimatedSpriteAcrossScreenStepsPerFrame(
            LightBike,
            Position      = 'bottom',
            direction     = "right",
            StepsPerFrame = 2,
            ZoomFactor    = 1,
            sleep         = 0.01
            )
          LightBike.HorizontalFlip()


        elif (r == 11):
          #ShowScreenArray(ScreenArray)

          #MakeAndShowClock(hh,h,v,RGB,ShadowGreen,ZoomFactor,Fill=False)

          
          MoveAnimatedSpriteAcrossScreenStepsPerFrame(
            LightBike,
            Position      = 'bottom',
            direction     = "left",
            StepsPerFrame = 2,
            ZoomFactor    = 1,
            sleep         = 0.009
            )
          LightBike.HorizontalFlip()

          MoveAnimatedSpriteAcrossScreenStepsPerFrame(
            Rezonator,
            Position      = 'bottom',
            direction     = "left",
            StepsPerFrame = 2,
            ZoomFactor    = 1,
            sleep         = 0.009
            )

          MoveAnimatedSpriteAcrossScreenStepsPerFrame(
            LightBike,
            Position      = 'bottom',
            direction     = "right",
            StepsPerFrame = 2,
            ZoomFactor    = 1,
            sleep         = 0.001
            )
          LightBike.HorizontalFlip()

          if random.randint(1,2) == 1:
            MoveAnimatedSpriteAcrossScreenStepsPerFrame(
              BigRezonator,
              Position      = 'bottom',
              direction     = "right",
              StepsPerFrame = 2,
              ZoomFactor    = 1,
              sleep         = 0
              )

          else:
            MoveAnimatedSpriteAcrossScreenStepsPerFrame(
              BigRezonator2,
              Position      = 'bottom',
              direction     = "right",
              StepsPerFrame = 2,
              ZoomFactor    = 1,
              sleep         = 0
              )

          print("end of animation")
        


        elif (r == 12):

          r = random.randint(1,3)
          MoveAnimatedSpriteAcrossScreenStepsPerFrame(
            ChickenRunning,
            Position      = 'bottom',
            Vadjust       = 1 * r,
            direction     = "left",
            StepsPerFrame = r,
            ZoomFactor    = r,
            sleep         = 0.03 / r
            )
          


        elif (r == 13):

          r = random.randint(1,4)
          MoveAnimatedSpriteAcrossScreenStepsPerFrame(
            PacManRightSprite,
            Position      = 'random',
            Vadjust       = 1 * r,
            direction     = "right",
            StepsPerFrame = r,
            ZoomFactor    = r,
            sleep         = 0.03 / r
            )

          r = random.randint(1,3)
          MoveAnimatedSpriteAcrossScreenStepsPerFrame(
            PacManLeftSprite,
            Position      = 'random',
            Vadjust       = 1 * r,
            direction     = "left",
            StepsPerFrame = r,
            ZoomFactor    = r,
            sleep         = 0.03 / r
            )



      #This will end the while loop -- THIS SECTION NEEDS A REWRITE
      elapsed_h,m,s, HHMMSS = CalculateElapsedTime(StartDateTimeUTC)
      #h,m,s = GetElapsedTime(LastAnimation,time.time())
            
      #print("HHMMSS: ",HHMMSS)

      

      if (TimerSprite.HHMM != HHMMSS[0:5]):
        #MakeAndShowClock(hh,h,v,RGB,ShadowGreen,ZoomFactor,Fill=True)
        TimerSprite = UpdateTimerWithTransition(TimerSprite,BannerSprite,h,v,RGB,ShadowRGB,ZoomFactor,Fill=True,TransitionType=2,StartDateTimeUTC = StartDateTimeUTC)
        #ShowScreenArray(ScreenArray)


      #How long has this function been running?
      #h,m,s, HHMMSS = CalculateElapsedTime(StartTime)
      h,m,s = GetElapsedTime(StartTime,time.time())
      

      #print("M:",m," RunMinutes:",RunMinutes)
      if m >= RunMinutes:
        Done = True
        print("Exiting Twitch Timer")











def DisplayRandomAnimation():
        
  r = random.randint(1,13)
  if (r == 1):

    RunningMan2Sprite.ScrollAcrossScreen(20,15,'right', ScrollSleep )
    RunningMan2Sprite.HorizontalFlip()
    Rezonator.ScrollAcrossScreen(20,(HatHeight - Rezonator.height),'right', ScrollSleep )
    RunningMan2Sprite.ScrollAcrossScreen(20,15,'left',0.02 )
    Rezonator.ScrollAcrossScreen(20,(HatHeight - Rezonator.height),'left', ScrollSleep )
    RunningMan2Sprite.HorizontalFlip()

  elif (r == 2):
    r = random.randint(1,2)
    MoveAnimatedSpriteAcrossScreen(BigSpiderWalkingSprite,Position='bottom',direction="right",steps=14*r,ZoomFactor=r,sleep=0.05)
    BigSpiderWalkingSprite.HorizontalFlip()
    r = random.randint(1,2)
    MoveAnimatedSpriteAcrossScreen(BigSpiderWalkingSprite,Position='bottom',direction="left",steps=14*r,ZoomFactor=r,sleep=0.03)
    BigSpiderWalkingSprite.HorizontalFlip()

  elif (r == 3):

    MoveAnimatedSpriteAcrossScreenFramesPerStep(
      ThreeGhostPacSprite,
      Position      = 'bottom',
      direction     = "right",
      FramesPerStep = 1,
      ZoomFactor    = random.randint(1,2),
      sleep         = 0.03
      )
    

    MoveAnimatedSpriteAcrossScreenFramesPerStep(
      ThreeBlueGhostPacSprite,
      Position      = 'bottom',
      direction     = "left",
      FramesPerStep = 1,
      ZoomFactor    = random.randint(1,2),
      sleep         = 0.02
      )

            

  elif (r == 4):

    SpaceInvader.framerate = 2
    SpaceInvader.InitializeScreenArray()
    SmallInvader.framerate = 2
    SmallInvader.InitializeScreenArray()
    TinyInvader.framerate  = 1
    TinyInvader.InitializeScreenArray()


    MoveAnimatedSpriteAcrossScreenStepsPerFrame(
      SpaceInvader,
      Position      = 'bottom',
      direction     = "right",
      StepsPerFrame = 4,
      ZoomFactor    = random.randint(1,3),
      sleep         = 0.03
      )


    MoveAnimatedSpriteAcrossScreenStepsPerFrame(
      SmallInvader,
      Position      = 'bottom',
      direction     = "right",
      StepsPerFrame = 4,
      ZoomFactor    = random.randint(1,3),
      sleep         = 0.03
      )


    MoveAnimatedSpriteAcrossScreenStepsPerFrame(
      TinyInvader,
      Position      = 'bottom',
      direction     = "right",
      StepsPerFrame = 4,
      ZoomFactor    = random.randint(1,3),
      sleep         = 0.03
      )

  elif (r == 5):

    r = random.randint(1,3)
    MoveAnimatedSpriteAcrossScreenStepsPerFrame(
      LittleShipFlying,
      Position      = 'bottom',
      direction     = "right",
      StepsPerFrame = 4 * r,
      ZoomFactor    = r,
      sleep         = 0.03 / r
      )
    LittleShipFlying.HorizontalFlip()

    r = random.randint(1,3)
    MoveAnimatedSpriteAcrossScreenStepsPerFrame(
      LittleShipFlying,
      Position      = 'bottom',
      direction     = "left",
      StepsPerFrame = 4 * r,
      ZoomFactor    = r,
      sleep         = 0.03 / r
      )
    LittleShipFlying.HorizontalFlip()


  elif (r == 6):

    MoveAnimatedSpriteAcrossScreenStepsPerFrame(
      DotZerkRobotWalking,
      Position      = 'bottom',
      direction     = "left",
      StepsPerFrame = 2,
      ZoomFactor    = random.randint(1,2),
      sleep         = 0.03
      )
    DotZerkRobotWalking.HorizontalFlip()



    MoveAnimatedSpriteAcrossScreenStepsPerFrame(
      DotZerkRobotWalking,
      Position      = 'bottom',
      direction     = "right",
      StepsPerFrame = 2,
      ZoomFactor    = random.randint(1,2),
      sleep         = 0.03
      )
    DotZerkRobotWalking.HorizontalFlip()


  elif (r == 7):

    MoveAnimatedSpriteAcrossScreenStepsPerFrame(
      DotZerkRobotWalkingSmall,
      Position      = 'bottom',
      direction     = "left",
      StepsPerFrame = 2,
      ZoomFactor    = random.randint(1,2),
      sleep         = 0.03
      )
    DotZerkRobotWalkingSmall.HorizontalFlip()

    MoveAnimatedSpriteAcrossScreenStepsPerFrame(
      DotZerkRobotWalkingSmall,
      Position      = 'bottom',
      direction     = "right",
      StepsPerFrame = 2,
      ZoomFactor    = random.randint(1,2),
      sleep         = 0.03
      )
    DotZerkRobotWalkingSmall.HorizontalFlip()




  elif (r == 8):

    RunningMan3Sprite.ScrollAcrossScreen(20,15,'right', ScrollSleep )
    RunningMan3Sprite.HorizontalFlip()
    RunningMan3Sprite.ScrollAcrossScreen(20,15,'left',0.02 )
    RunningMan3Sprite.HorizontalFlip()


  elif (r == 9):

    i = random.randint(0,27)
    ShipSprites[i].InitializeScreenArray()

    d = random.randint(1,2)
    if d == 1:
      direction = 'left'
    else:
      direction = 'right'


    MoveAnimatedSpriteAcrossScreenStepsPerFrame(
      ShipSprites[i],
      Position      = 'random',
      direction     = direction,
      StepsPerFrame = 1,
      ZoomFactor    = random.randint(1,3),
      sleep         = 0.03
      )
  

    
  elif (r == 10):

    MoveAnimatedSpriteAcrossScreenStepsPerFrame(
      LightBike,
      Position      = 'bottom',
      direction     = "left",
      StepsPerFrame = 2,
      ZoomFactor    = 1,
      sleep         = 0.005
      )
    LightBike.HorizontalFlip()
    MoveAnimatedSpriteAcrossScreenStepsPerFrame(
      LightBike,
      Position      = 'bottom',
      direction     = "right",
      StepsPerFrame = 2,
      ZoomFactor    = 1,
      sleep         = 0.005
      )
    LightBike.HorizontalFlip()


  elif (r == 11):
    
    MoveAnimatedSpriteAcrossScreenStepsPerFrame(
      LightBike,
      Position      = 'bottom',
      direction     = "left",
      StepsPerFrame = 2,
      ZoomFactor    = 1,
      sleep         = 0.003
      )
    LightBike.HorizontalFlip()

    MoveAnimatedSpriteAcrossScreenStepsPerFrame(
      Rezonator,
      Position      = 'bottom',
      direction     = "left",
      StepsPerFrame = 2,
      ZoomFactor    = 1,
      sleep         = 0.005
      )

    MoveAnimatedSpriteAcrossScreenStepsPerFrame(
      LightBike,
      Position      = 'bottom',
      direction     = "right",
      StepsPerFrame = 2,
      ZoomFactor    = 1,
      sleep         = 0.001
      )
    LightBike.HorizontalFlip()

    if random.randint(1,2) == 1:
      MoveAnimatedSpriteAcrossScreenStepsPerFrame(
        BigRezonator,
        Position      = 'bottom',
        direction     = "right",
        StepsPerFrame = 2,
        ZoomFactor    = 1,
        sleep         = 0
        )

  elif (r == 12):

    r = random.randint(1,3)
    MoveAnimatedSpriteAcrossScreenStepsPerFrame(
      ChickenRunning,
      Position      = 'bottom',
      Vadjust       = 1 * r,
      direction     = "left",
      StepsPerFrame = r,
      ZoomFactor    = r,
      sleep         = 0.03 / r
      )
    


  elif (r == 13):

    r = random.randint(1,4)
    MoveAnimatedSpriteAcrossScreenStepsPerFrame(
      PacManRightSprite,
      Position      = 'random',
      Vadjust       = 1 * r,
      direction     = "right",
      StepsPerFrame = r,
      ZoomFactor    = r,
      sleep         = 0.03 / r
      )

    r = random.randint(1,3)
    MoveAnimatedSpriteAcrossScreenStepsPerFrame(
      PacManLeftSprite,
      Position      = 'random',
      Vadjust       = 1 * r,
      direction     = "left",
      StepsPerFrame = r,
      ZoomFactor    = r,
      sleep         = 0.03 / r
      )





  else:
    MoveAnimatedSpriteAcrossScreenStepsPerFrame(
      BigRezonator2,
      Position      = 'bottom',
      direction     = "right",
      StepsPerFrame = 2,
      ZoomFactor    = 1,
      sleep         = 0
      )









def ScrollScreenArray(ScreenArray,lines,speed):    
  
  EmptyCap   = [[(0,0,0) for i in range (0,HatWidth)]]
  InsertLine = copy.deepcopy(EmptyCap)
  Buffer     = ScreenArray

  
  #Scroll up
  #Delete top row, insert blank on bottom, pushing remaining to the top

  for x in range (0,lines):
    
    Buffer = numpy.delete(Buffer,(0),axis=0)
    Buffer = numpy.insert(Buffer,HatHeight-1,InsertLine,axis=0)
    #setpixelsLED(Buffer)
    CopyScreenArrayToCanvasVSync(Buffer)
    if (speed > 0):
      time.sleep(speed)

  return Buffer
      



def BlinkCursor(CursorH=0,CursorV=0,CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),BlinkSpeed=0.25,BlinkCount=1):


  for i in range (0,BlinkCount*2):
    #If on, draw dark, if off, draw bright
    #print ("BlinkCursor:",CursorSprite.on)
    if(CursorSprite.on == True):
      ColorTuple = CursorDarkRGB
      CursorSprite.on = False
    else:
      ColorTuple = CursorRGB
      CursorSprite.on = True


    CopySpriteToPixelsZoom(
      TheSprite = CursorSprite,
      h = CursorH,
      v = CursorV,
      ColorTuple = ColorTuple,
      FillerTuple=(0,0,0),
      ZoomFactor = 1,
      Fill = False
    )

    if (BlinkSpeed > 0):
      time.sleep(BlinkSpeed)

  return


        
def TerminalScroll(ScreenArray, Message="",CursorH=0,CursorV=0,MessageRGB=(0,150,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0), StartingLineFeed=0,TypeSpeed=0.1,ScrollSpeed=0.1):
  LineSize = 6  #this is the height of the LEDarcade text characters + 1

  #erase the cursor because we are going to type
  CopySpriteToPixelsZoom(
    TheSprite = CursorSprite,
    h = CursorH,
    v = CursorV,
    ColorTuple = (0,0,0),
    FillerTuple=(0,0,0),
    ZoomFactor = 1,
    Fill = False
  )

  #increment a line if not at the very top
  if(StartingLineFeed > 0 and CursorV > 0):
    #print("Starting line feed activated:",CursorH,CursorV)
    CursorV = CursorV + (LineSize * StartingLineFeed)
    CursorH = 0

  #check incoming cursor position to see if we need to scroll right away
  if (CursorV > HatHeight -LineSize):
    #erase the cursor at old location
    #print ("scrolling")
    CopySpriteToPixelsZoom(
      TheSprite = CursorSprite,
      h = CursorH,
      v = CursorV,
      ColorTuple = (0,0,0),
      FillerTuple=(0,0,0),
      ZoomFactor = 1,
      Fill = False
    )

    ScreenArray = ScrollScreenArray(ScreenArray,LineSize,ScrollSpeed)
    #we want to keep printing at the bottom line at this point
    CursorV = CursorV - LineSize



  WordList = Message.split()
  for i in range(0,len(WordList)):
    word = WordList[i] + ' '
    WordSprite = CreateBannerSprite(word)    

    #Make sure we have room to print
    if(CursorH +  WordSprite.width > HatWidth):

      #erase the cursor at old location
      CopySpriteToPixelsZoom(
        TheSprite = CursorSprite,
        h = CursorH,
        v = CursorV ,
        ColorTuple = (0,0,0),
        FillerTuple=(0,0,0),
        ZoomFactor = 1,
        Fill = False
      )

      #carriage return line feed
      CursorH = 0
      CursorV = CursorV + LineSize


    if (CursorV + LineSize > HatHeight):
      #print("scrolling")
      ScreenArray = ScrollScreenArray(ScreenArray,LineSize,ScrollSpeed)
      #we want to keep printing at the bottom line at this point
      CursorV = CursorV - LineSize

   



    for i in range (0,len(word)):

      #convert single character to a sprite
      character = word[i]
      CharacterSprite = CreateBannerSprite(character)    

      
      #Make cursor blink at current location
      CopySpriteToPixelsZoom(
        TheSprite = CursorSprite,
        h = CursorH,
        v = CursorV,
        ColorTuple = CursorRGB,
        FillerTuple=(0,0,0),
        ZoomFactor = 1,
        Fill = False
      )
      
      if(TypeSpeed >0):
        time.sleep(TypeSpeed)



      #Erase cursor
      CopySpriteToPixelsZoom(
        TheSprite = CursorSprite,
        h = CursorH,
        v = CursorV,
        ColorTuple = (0,0,0),
        FillerTuple=(0,0,0),
        ZoomFactor = 1,
        Fill = False
      )
      #CopyScreenArrayToCanvasVSync(ScreenArray)
     


      #copy character to current spot
      CopySpriteToScreenArrayZoom(
        TheSprite = CharacterSprite,
        h = CursorH,
        v = CursorV,
        ColorTuple = MessageRGB,
        FillerTuple=(0,0,0),
        ZoomFactor = 1,
        Fill = False,
        InputScreenArray = ScreenArray
      )
      #CopyScreenArrayToCanvasVSync(ScreenArray)
      setpixels(ScreenArray)
      
      CursorH = CursorH + CharacterSprite.width
      
      #leave cursor on at the end of the word
      CopySpriteToPixelsZoom(
        TheSprite = CursorSprite,
        h = CursorH,
        v = CursorV,
        ColorTuple = CursorDarkRGB,
        FillerTuple=(0,0,0),
        ZoomFactor = 1,
        Fill = False
      )


   
  return ScreenArray,CursorH,CursorV





def TerminalTypeLine(ScreenArray, Message="",CursorH=0,CursorV=0,MessageRGB=(0,150,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0), StartingLineFeed=0,TypeSpeed=0.1,ScrollSpeed=0.1):
  
  #erase the cursor because we are going to type
  CopySpriteToPixelsZoom(
    TheSprite = CursorSprite,
    h = CursorH,
    v = CursorV,
    ColorTuple = (0,0,0),
    FillerTuple=(0,0,0),
    ZoomFactor = 1,
    Fill = False
  )

  for i in range (0,len(Message)):

    #convert single character to a sprite
    character = Message[i]
    CharacterSprite = CreateBannerSprite(character)    

    
    #Make cursor blink at current location
    CopySpriteToPixelsZoom(
      TheSprite = CursorSprite,
      h = CursorH,
      v = CursorV,
      ColorTuple = CursorRGB,
      FillerTuple=(0,0,0),
      ZoomFactor = 1,
      Fill = False
    )
    
    if(TypeSpeed >0):
      time.sleep(TypeSpeed)


    #Erase cursor
    CopySpriteToPixelsZoom(
      TheSprite = CursorSprite,
      h = CursorH,
      v = CursorV,
      ColorTuple = (0,0,0),
      FillerTuple=(0,0,0),
      ZoomFactor = 1,
      Fill = False
    )
    #CopyScreenArrayToCanvasVSync(ScreenArray)
    
    #copy character to current spot
    CopySpriteToScreenArrayZoom(
      TheSprite = CharacterSprite,
      h = CursorH,
      v = CursorV,
      ColorTuple = MessageRGB,
      FillerTuple=(0,0,0),
      ZoomFactor = 1,
      Fill = False,
      InputScreenArray = ScreenArray
    )
    setpixels(ScreenArray)
    
    CursorH = CursorH + CharacterSprite.width
    
    #Erase cursor
    CopySpriteToPixelsZoom(
      TheSprite = CursorSprite,
      h = CursorH,
      v = CursorV,
      ColorTuple = (0,0,0),
      FillerTuple=(0,0,0),
      ZoomFactor = 1,
      Fill = False
    )
  return ScreenArray,CursorH,CursorV








def deEmojify(InputString):
    return InputString.encode('ascii', 'ignore').decode('ascii')





def CalculateElapsedTime(StartDateTimeUTC):
  #get current UTC datetime (timezone naive)
  nowUTC = datetime.utcnow()

  #print("nowUTC:",nowUTC,nowUTC.timestamp())
  
  #This creates a timedelta object
  elapsed_time =  nowUTC - StartDateTimeUTC
  elapsed_hours, rem = divmod(elapsed_time.seconds, 3600)
  elapsed_minutes, elapsed_seconds = divmod(rem, 60)
    
  HHMMSS = "{:0>2}:{:0>2}:{:0>2}".format(int(elapsed_hours),int(elapsed_minutes),elapsed_seconds)
  
  return elapsed_hours, elapsed_minutes, elapsed_seconds, HHMMSS
  





def ZoomImage(ImageName, ZoomStart, ZoomStop, ZoomSleep, Step):
    global Canvas

    image = Image.open(ImageName).convert('RGB')
    orig_width, orig_height = image.size

    zoom_range = range(ZoomStart, ZoomStop, Step) if ZoomStart <= ZoomStop else range(ZoomStart, ZoomStop, -Step)

    for ZoomFactor in zoom_range:
        new_width = int(orig_width * ZoomFactor / 100)
        new_height = int(orig_height * ZoomFactor / 100)

        ResizedImage = image.resize((new_width, new_height), resample=Image.LANCZOS)

        x = int(HatWidth // 2 - new_width // 2)
        y = int(HatHeight // 2 - new_height // 2)

        if new_width < HatWidth or new_height < HatHeight:
            Canvas.Fill(0, 0, 0)

        Canvas.SetImage(ResizedImage, x, y)
        Canvas = TheMatrix.SwapOnVSync(Canvas)

        if ZoomSleep > 0:
            time.sleep(ZoomSleep)


def ZoomImageObject(image, ZoomStart, ZoomStop, ZoomSleep, Step):
    """
    Zooms in or out on an existing PIL Image object and renders it to the canvas.

    Parameters:
        image (PIL.Image): The image to zoom.
        ZoomStart (int): Initial zoom percentage (e.g. 0 for 0%).
        ZoomStop (int): Final zoom percentage (e.g. 100 for 100%).
        ZoomSleep (float): Time to sleep (in seconds) between frames.
        Step (int): Step increment for zooming.
    """
    global Canvas

    image = image.convert('RGB')
    orig_width, orig_height = image.size

    zoom_range = range(ZoomStart, ZoomStop, Step) if ZoomStart <= ZoomStop else range(ZoomStart, ZoomStop, -Step)

    for ZoomFactor in zoom_range:
        new_width = int(orig_width * ZoomFactor / 100)
        new_height = int(orig_height * ZoomFactor / 100)

        if new_width <= 0 or new_height <= 0:
            continue  # Skip invalid sizes

        ResizedImage = image.resize((new_width, new_height), resample=Image.LANCZOS)

        x = int(HatWidth // 2 - new_width // 2)
        y = int(HatHeight // 2 - new_height // 2)

        if new_width < HatWidth or new_height < HatHeight:
            Canvas.Fill(0, 0, 0)

        Canvas.SetImage(ResizedImage, x, y)
        Canvas = TheMatrix.SwapOnVSync(Canvas)

        if ZoomSleep > 0:
            time.sleep(ZoomSleep)




def ZoomImage_old(ImageName,ZoomStart, ZoomStop, ZoomSleep,Step):

  global Canvas

  image = Image.open(ImageName)
  image = image.convert('RGB')
 
  ZoomFactor    = 0
  
  
  draw = ImageDraw.Draw(image)  # Declare Draw instance before prims

  
  if (ZoomStart <= ZoomStop):
    for ZoomFactor in range (ZoomStart,ZoomStop,Step):
      ResizedImage = image.resize(size=(ZoomFactor,ZoomFactor))
      TheMatrix.SetImage(ResizedImage, (HatWidth/2 -(ZoomFactor/2)),(HatHeight/2 -(ZoomFactor/2)))
      #TheMatrix.SetImage(ResizedImage, (HatWidth/2 -(ZoomFactor/2)),(0))
      if (ZoomSleep > 0):
        time.sleep(ZoomSleep)
        
  else:
    #for ZoomFactor in reversed(range(ZoomStop, ZoomStart,-Step)):
    for ZoomFactor in range(ZoomStart, ZoomStop,-Step):
      #clear the screen as we zoom to remove leftovers
      ResizedImage = image.resize(size=(ZoomFactor,ZoomFactor))
      
      #zooming out (shrinking the image) will leave artifacts unless we erase them
      if(ZoomFactor < HatWidth or ZoomFactor < HatHeight):
        Canvas.Fill(0,0,0)
      Canvas.SetImage(ResizedImage, (HatWidth/2 -(ZoomFactor/2)),(HatHeight/2 -(ZoomFactor/2)))
      Canvas = TheMatrix.SwapOnVSync(Canvas)
      
      if (ZoomSleep > 0):
        time.sleep(ZoomSleep)
      
        

      
      
        #if ZoomFactor <= HatWidth:
        #  draw.rectangle((0,0, ZoomFactor, ZoomFactor), fill=(0, 0, 0))

        #TheMatrix.Clear()        





def RotateAndZoomImage(ImageName):
  #image = Image.open("/home/pi/LEDarcade/images/ninja64colors.png")
  #image = Image.open("/home/pi/LEDarcade/images/ninja.png")
  #image = Image.open("/home/pi/LEDarcade/images/BigNinjaLogo256.png")
  image = Image.open(ImageName)
  image = image.convert('RGB')

  for x in range(1,100):    

    for r in range(1,100,2):
      ResizedImage = image.rotate(r).resize(size=(r,r))
      TheMatrix.SetImage(ResizedImage, (HatWidth/2 -(r/2)),(HatHeight/2 -(r/2)))
      time.sleep(0.01)
    TheMatrix.Clear()
 
    for r in range(256,1,-2):
      ResizedImage = image.resize(size=(r,r))
      TheMatrix.SetImage(ResizedImage, (HatWidth/2 -(r/2)),(HatHeight/2 -(r/2)))
      time.sleep(0.01)
      TheMatrix.Clear()



    for r in range(1,256,2):
      ResizedImage = image.rotate(r*6).resize(size=(r,r))
      TheMatrix.SetImage(ResizedImage, (HatWidth/2 -(r/2)),(HatHeight/2 -(r/2)))
      time.sleep(0.01)
    TheMatrix.Clear()


  for i in range (0,359):
    NewImage = ResizedImage.rotate(i)
    TheMatrix.SetImage(NewImage, HatWidth-r/2, -18)
    time.sleep(0.001 )




def GetImageFromURL(URL,SaveName):
  print("")
  print("-- Show GetImageFromURL --")
  print("ImageLocation:",URL)
  print("SaveName:",SaveName)

  with urllib.request.urlopen(URL) as i:
    byteImg = io.BytesIO(i.read())
    image = Image.open(byteImg)
    image.save(SaveName)




def ShowImage(ImageLocation,Fade=False,MaxBright = 100, Duration = 1):
  # Make image fit our screen.
  print("")
  print("-- Show Image --")
  print("ImageLocation:",ImageLocation)
  image = Image.open(ImageLocation)

  image.thumbnail((HatWidth, HatHeight), Image.LANCZOS)

  image = image.convert('RGB')

  if(Fade == True):
    TheMatrix.brightness = 0
    for x in range (0,MaxBright):
      TheMatrix.brightness = x
      TheMatrix.SetImage(image)

  
  time.sleep(Duration)


  if(Fade == True):
    for x in range (0,MaxBright):
      TheMatrix.brightness = MaxBright - x
      TheMatrix.SetImage(image)
      time.sleep(0.01)

  TheMatrix.Clear()
  TheMatrix.brightness = 100
      


  # for n in range(-32, -HatWidth-1):  # Start off top-left, move off bottom-right
  #     TheMatrix.Clear()
  #     TheMatrix.SetImage(image, n, 0)
  #     time.sleep(0.01)

      


def DrawSquare2():

  # RGB example w/graphics prims.
  # Note, only "RGB" mode is supported currently.
  image = Image.new("RGB", (HatWidth, 32))  # Can be larger than matrix if wanted!!
  draw = ImageDraw.Draw(image)  # Declare Draw instance before prims
  # Draw some shapes into image (no immediate effect on matrix)...
  draw.rectangle((0, 0, 31, 31), fill=(0, 0, 0), outline=(0, 0, 255))
  draw.line((0, 0, 31, 31), fill=(255, 0, 0))
  draw.line((0, 31, 31, 0), fill=(0, 255, 0))

  # Then scroll image across matrix...
  for n in range(-32, 63):  # Start off top-left, move off bottom-right
      TheMatrix.Clear()
      TheMatrix.SetImage(image, n, n)
      time.sleep(0.01)


def DrawSquare(h1,v1,h2,v2,FillRGB,BorderRGB):
  image = Image.new("RGB", (HatWidth, 32))  # Can be larger than matrix if wanted!!
  draw = ImageDraw.Draw(image)  # Declare Draw instance before prims
  # Draw some shapes into image (no immediate effect on matrix)...
  draw.rectangle((h1, v1, h2, v2), fill=FillRGB, outline=BorderRGB)
  TheMatrix.SetImage(image, h1, v1)
  time.sleep(1)







def CreateCreditImage(names):
  Buffer          = 32
  GradientSection = 32
  text_y_position = 0
  text_padding    = 12
  image_width     = HatWidth
  ColorB          = 52
  TextRGB         = (235,235,235)




  #Create blank image
  image_height    = (len(names) * text_padding) + (Buffer *2) + (GradientSection *2) + 13
  img = Image.new("RGB", (image_width, image_height), color=(0,0,ColorB))
  draw = ImageDraw.Draw(img)

 

  #Draw buffer
  for v in range (0,Buffer):
    draw.line((0,text_y_position,HatWidth,text_y_position),fill=(0,0,0))
    text_y_position += 1

  #draw gradient
  for v in range (0,GradientSection):
    NewColorB = round(ColorB / GradientSection * v)
    draw.line((0,text_y_position,HatWidth,text_y_position),fill=(0,0,NewColorB))
    text_y_position += 1


  #write header
  Text = "PATRONS"
  fnt = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoMono-Regular.ttf",12)
  

  #header_width, header_height = draw.textsize(Text, font=fnt)

  bbox = draw.textbbox((0, 0), Text, font=fnt)
  header_width = bbox[2] - bbox[0]
  header_height = bbox[3] - bbox[1]

  draw.text(
    ( 
      (image_width - header_width) / 2,  text_y_position ),
      Text,
      font=fnt,
      fill=(250,250,250)
    )
  text_y_position += text_padding


  #write patron names
  for name in names:
     #text_width, text_height = draw.textsize(name, font=fnt)
     bbox = draw.textbbox((0, 0), name, font=fnt)
     text_width = bbox[2] - bbox[0]
     text_height = bbox[3] - bbox[1]

     fnt = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoMono-Regular.ttf",10)
     draw.text(
       ( 
         (image_width - text_width) / 2,  text_y_position ),
         name,
         font=fnt,
         fill=TextRGB

       )
     text_y_position += text_padding
  


  #draw gradient
  for v in range (GradientSection,0,-1):
    NewColorB = round(ColorB / GradientSection * v)
    draw.line((0,text_y_position,HatWidth,text_y_position),fill=(0,0,NewColorB))
    text_y_position += 1


  #Draw buffer
  for v in range (0,Buffer):
    draw.line((0,text_y_position,HatWidth,text_y_position),fill=(0,0,0))
    text_y_position += 1

  

  img.save('credits.png')       









def ScrollCreditImage(CreditImage,ScrollSleep):
  


  image = Image.open(CreditImage)
  image = image.convert('RGB')
  width,height = image.size
  print("ScrollCreditImage: CreditImage")
  print("Image width height:", width,height)

  for x in range (0,height - HatHeight):
    #print("Cropping image x:", x)
    ScreenCrop = image.crop((0,x,HatWidth,x + HatHeight))
    TheMatrix.SetImage(ScreenCrop,0,0)
    time.sleep(ScrollSleep)







def ScrollImage(ImageName,ScrollSleep):


  
  image = Image.open(ImageName)
  image = image.convert('RGB')
  width,height = image.size
  print("ScrollImage:",ImageName)
  print("Image width height:", width,height)

  for x in range (0,height - HatHeight):
    #print("Cropping image x:", x)
    ScreenCrop = image.crop((0,x,HatWidth,x + HatHeight))
    TheMatrix.SetImage(ScreenCrop,0,0)
    time.sleep(ScrollSleep)





def CreateJustJoinedImage(names=[],ImageName='JustJoined.png'):
  Buffer          = 32
  GradientSection = 32
  text_y_position = 0
  text_padding    = 16
  image_width     = HatWidth
  ColorG          = 52
  TextRGB         = (235,235,235)
  NameFontSize    = 11

  print("LEDarcade| ImageName:",ImageName)

  #Create blank image
  image_height    = (len(names) * text_padding) + (Buffer *2) + (GradientSection *2) + 13
  img = Image.new("RGB", (image_width, image_height), color=(0,ColorG,0))
  draw = ImageDraw.Draw(img)

 

  #Draw buffer
  for v in range (0,Buffer):
    draw.line((0,text_y_position,HatWidth,text_y_position),fill=(0,0,0))
    text_y_position += 1

  #draw gradient
  for v in range (0,GradientSection):
    NewColorG = round(ColorG / GradientSection * v)
    draw.line((0,text_y_position,HatWidth,text_y_position),fill=(0,NewColorG,0))
    text_y_position += 1


  #write header
  Text = "WELCOME"
  fnt = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoMono-Regular.ttf",12)
  #header_width, header_height = draw.textsize(Text, font=fnt)
  bbox = draw.textbbox((0, 0), Text, font=fnt)
  header_width = bbox[2] - bbox[0]
  header_height = bbox[3] - bbox[1]

  
  draw.text(
    ( 
      (image_width - header_width) / 2,  text_y_position ),
      Text,
      font=fnt,
      fill=(250,250,250)
    )
  text_y_position += text_padding
  

  #write names
  for name in names:
     NameLen = len(name)
     #? not sure why this line is here
     if(NameLen > 12):
       name = name[0:11]
       NameFontSize = 8
     elif(NameLen >=10):
       NameFontSize = 9
     else:
      NameFontSize = 11

     fnt = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoMono-Regular.ttf",NameFontSize)
     #text_width, text_height = draw.textsize(name, font=fnt)

     bbox = draw.textbbox((0, 0), name, font=fnt)
     text_width = bbox[2] - bbox[0]
     text_height = bbox[3] - bbox[1]


     draw.text(
       ( 
         (image_width - text_width) / 2,  text_y_position ),
         name,
         font=fnt,
         fill=TextRGB

       )
     text_y_position += text_padding
  


  #draw gradient
  for v in range (GradientSection,0,-1):
    NewColorG = round(ColorG / GradientSection * v)
    draw.line((0,text_y_position,HatWidth,text_y_position),fill=(0,NewColorG,0))
    text_y_position += 1


  #Draw buffer
  for v in range (0,Buffer + 8):
    draw.line((0,text_y_position,HatWidth,text_y_position),fill=(0,0,0))
    text_y_position += 1

  
  img.save(ImageName)       



def ScrollJustJoinedUser(Names=[],ImageName='JustJoined.png',ScrollSleep=0.05):
  
  CreateJustJoinedImage(Names,ImageName)
  ScrollImage(ImageName,ScrollSleep)
  





def SweepClean():

    def get_zoom(sprite):
          height = sprite.height
          if height <= 5:
              return 3
          elif height <= 10:
              return 2
          else:
              return 1


    r = random.randint(1,5)
    if r == 1:
      SpriteChoices = [
                      "ThreeGhostPacSprite",
                      "ThreeGhostSprite",
                      "ThreeBlueGhostSprite",
                      "PacManSprite",
                      "ElectricZap",
                      "Rezonator",
                      "BigRezonator",
                      "BigRezonator2",
                      "SpaceInvader",
                      "TinyInvader",
                      "SmallInvader",
                      "LittleShipFlying",
                      "LargeUFOSprite1",
                      "LargeUFOSprite2",
                      "LargeUFOSprite3",
                      "LargeUFOSprite4",
                      "LargeUFOSprite5",
                      "LargeUFOSprite6"
                      ]

      SpriteName    = random.choice(SpriteChoices)
      SpriteZoom    = get_zoom(globals()[SpriteName])
      MoveAnimatedSpriteAcrossScreenStepsPerFrame(
          globals()[SpriteName],
          Position      = 'top',
          Vadjust       = 0,
          direction     = "right",
          StepsPerFrame = 3,
          ZoomFactor    = SpriteZoom,
          sleep         = 0.02
      )

      MoveAnimatedSpriteAcrossScreenStepsPerFrame(
          globals()[SpriteName],
          Position      = 'middle',
          Vadjust       = 0,
          direction     = "left",
          StepsPerFrame = 3,
          ZoomFactor    = SpriteZoom,
          sleep         = 0.01
      )

      MoveAnimatedSpriteAcrossScreenStepsPerFrame(
          globals()[SpriteName],
          Position      = 'bottom',
          Vadjust       = 0,
          direction     = "right",
          StepsPerFrame = 3,
          ZoomFactor    = SpriteZoom,
          sleep         = 0.004
      )
    else:
      MoveAnimatedSpriteAcrossScreenStepsPerFrame(
        PacManRightSprite,
        Position      = 'top',
        Vadjust       = 0 ,
        direction     = "right",
        StepsPerFrame = 3,
        ZoomFactor    = 3,
        sleep         = 0.02 
        )


      MoveAnimatedSpriteAcrossScreenStepsPerFrame(
        PacManLeftSprite,
        Position      = 'middle',
        Vadjust       = 0,
        direction     = "left",
        StepsPerFrame = 3,
        ZoomFactor    = 3,
        sleep         = 0.01
        )

      MoveAnimatedSpriteAcrossScreenStepsPerFrame(
        PacManRightSprite,
        Position      = 'bottom',
        Vadjust       = 0 ,
        direction     = "right",
        StepsPerFrame = 3,
        ZoomFactor    = 3,
        sleep         = 0.004 
        )






def AdjustBrightnessRGB(rgb,step):
  r,g,b = rgb
    
  r = r + step
  if r < 0:
    r = 0
  elif r > 255:
    r = 255
  g = g + step
  if g < 0:
    g = 0
  elif g > 255:
    g = 255
  
  b = b + step
  if b < 0:
    b = 0
  elif b > 255:
    b = 255

  return r,g,b







def StarryNightDisplayText(
  Text1        = "TEXT1",
  Text2        = "TEXT2",
  Text3        = "TEXT3",
  ScrollSleep  = 0.02,
  RunSeconds   = 60
):

  #We want to capture what is on the screen before we start drawing, that way we can transition back to it nicely
  ScreenArrayBefore = copy.deepcopy(ScreenArray)






  H = 0
  V = 0

  print("")
  print("-- Starry Night Display Text")
  print("Text1:",Text1)
  print("Text2:",Text2)
  print("Text3:",Text3)
  StartTime = time.time()

  #Define color list
  TextColorList = ((ShadowPurple,DarkPurple,LowPurple,MedPurple),
                   #(ShadowRed,   DarkRed,   LowRed,   MedRed),
                   (DarkRed,     LowRed,    MedRed,   HighRed),
                   (ShadowOrange,DarkOrange,LowOrange,MedOrange),
                   (ShadowYellow,DarkYellow,LowYellow,MedYellow),
                   #(ShadowGreen, DarkGreen, LowGreen, MedGreen),
                   (DarkGreen,   LowGreen,  MedGreen, HighGreen),
                   (ShadowBlue,  DarkBlue,  LowBlue,  MedBlue),
                   (ShadowPink,  DarkPink,  LowPink,  MedPink),
                   (ShadowCyan,  DarkCyan,  LowCyan,  MedCyan)
  
                    )
  TextColorCount = len(TextColorList)

  #Get a bunch of random colors for each text layer  
  i = random.randint(0,TextColorCount -1)
  A,B,C,D = TextColorList[i]
  Text1RGB = C

  i = random.randint(0,TextColorCount -1)
  A,B,C,D = TextColorList[i]
  Text2RGB = B
  
  i = random.randint(0,TextColorCount -1)
  A,B,C,D = TextColorList[i]
  Text3RGB = B
  



  #--------------------------------
  #-- Create Layers              --
  #--------------------------------

  Background   = Layer(name="backround", width=600,  height=32,h=0,v=0)
  Middleground = Layer(name="backround", width=800,  height=32,h=0,v=0)
  Foreground   = Layer(name="backround", width=1000, height=32,h=0,v=0)

  Background.CreateStars(0,0,50,50)
  Middleground.CreateStars(0,0,100,100)
  Foreground.CreateStars(0,0,200,200)

  Canvas = TheMatrix.CreateFrameCanvas()
  Canvas.Clear()
  Canvas = TheMatrix.SwapOnVSync(Canvas)

  
  count  = 0
  bx     = 0
  mx     = 0
  fx     = 0
  bwidth = Background.width    - HatWidth
  mwidth = Middleground.width  - HatWidth
  fwidth = Foreground.width    - HatWidth
  brate  = 4
  mrate  = 2
  frate  = 1
  Done   = False



  TheBanner1 = CreateBannerSprite(Text1)
  h1         = HatWidth + 20
  v1         = 8
  Foreground = CopySpriteToLayerZoom(TheBanner1,h1,v1,Text1RGB,(0,0,0),ZoomFactor=3,Fill=False,Layer=Foreground)

  TheBanner2 = CreateBannerSprite(Text2)
  h2         = HatWidth + 100
  v2         = 4
  Middleground = CopySpriteToLayerZoom(TheBanner2,h2,v2,Text2RGB,(0,0,0),ZoomFactor=2,Fill=False,Layer=Middleground)

  TheBanner3 = CreateBannerSprite(Text3)
  h3         = HatWidth + 100
  v3         = 0
  Background = CopySpriteToLayerZoom(TheBanner3,h3,v3,Text3RGB,(0,0,0),ZoomFactor=1,Fill=False,Layer=Background)



  #Choose a random sprite
  r = random.randint(0,13)
  if(r == 0):
    TheSprite = copy.deepcopy(RunningMan2Sprite)
    TheSprite.framerate = 4
    H = -2
    V = 15
  elif(r == 1):
    TheSprite = copy.deepcopy(RunningMan3Sprite)
    TheSprite.framerate = 3
    H = -2
    V = 15
  elif(r == 2):
    TheSprite = copy.deepcopy(ChickenRunning)
    TheSprite.framerate = 8
    TheSprite.HorizontalFlip()
    H = 1
    V = HatHeight - TheSprite.height
  elif(r == 3):
    TheSprite = copy.deepcopy(ThreeGhostPacSprite)
    TheSprite.framerate = 4
    #TheSprite.HorizontalFlip()
    H = 1
    V = HatHeight - TheSprite.height
  
  elif(r == 4):
    TheSprite = copy.deepcopy(ThreeBlueGhostPacSprite)
    TheSprite.framerate = 4
    TheSprite.HorizontalFlip()
    H = 1
    V = HatHeight - TheSprite.height

  elif(r == 5):
    TheSprite = copy.deepcopy(ChickenChasingWorm)
    TheSprite.framerate = 8
    TheSprite.HorizontalFlip()
    H = 1
    V = HatHeight - TheSprite.height
  
  elif(r == 6):
    TheSprite = copy.deepcopy(DotZerkRobot)
    TheSprite.framerate = 8
    TheSprite.HorizontalFlip()
    H = 1
    V = HatHeight - TheSprite.height
  
  elif(r == 7):
    TheSprite = copy.deepcopy(DotZerkRobotWalking)
    TheSprite.framerate = 8
    TheSprite.HorizontalFlip()
    H = 1
    V = HatHeight - TheSprite.height

  elif(r == 8):
    TheSprite = copy.deepcopy(DotZerkRobotWalkingSmall)
    TheSprite.framerate = 8
    TheSprite.HorizontalFlip()
    H = 1
    V = HatHeight - TheSprite.height

  elif(r == 9):
    TheSprite = copy.deepcopy(Rezonator)
    TheSprite.framerate = 12
    TheSprite.HorizontalFlip()
    H = 1
    V = HatHeight - TheSprite.height


  elif(r == 10):
    TheSprite = copy.deepcopy(BigRezonator)
    TheSprite.framerate = 12
    TheSprite.HorizontalFlip()
    H = 1
    V = HatHeight - TheSprite.height

  elif(r == 11):
    TheSprite = copy.deepcopy(SpaceInvader)
    TheSprite.framerate = 8
    TheSprite.HorizontalFlip()
    H = 1
    V = HatHeight - TheSprite.height

  elif(r == 12):
    TheSprite = copy.deepcopy(SmallInvader)
    TheSprite.framerate = 8
    TheSprite.HorizontalFlip()
    H = 1
    V = HatHeight - TheSprite.height


  elif(r == 13):
    TheSprite = copy.deepcopy(TinyInvader)
    TheSprite.framerate = 8
    TheSprite.HorizontalFlip()
    H = 1
    V = HatHeight - TheSprite.height


  #TheSprite = copy.deepcopy(TinyInvader)
  #TheSprite = CopyAnimatedSpriteZoom(TheSprite,2)
  #TheSprite.currentframe = 1
  #TheSprite.framerate = 8
  #H = 1
  #V = HatHeight - TheSprite.height  -5

  while (Done == False):

    x = 0

    #main counter
    count = count + 1
    Canvas.Clear()
  
    #Background
    m,r = divmod(count,brate)
    if(r == 0):
      bx = bx + 1
      if(bx > bwidth):
        bx = 0

    #Middleground
    m,r = divmod(count,mrate)
    if(r == 0):
      mx = mx + 1
      if(mx > mwidth):
        mx = 0
      
    #foreground
    m,r = divmod(count,frate)
    if(r == 0):
      fx = fx + 1
      if(fx > fwidth):
        fx = 0

    Canvas = PaintThreeLayerCanvas(bx,mx,fx,Background,Middleground,Foreground,Canvas)


    #LED.RunningMan3Sprite.DisplayAnimated(10,10)
    Canvas = TheSprite.PaintAnimatedToCanvas(H,V,Canvas)
    Canvas = TheMatrix.SwapOnVSync(Canvas)
   
    
    
    #Ever once in a while check to see if the time is up and we should exit
    if(random.randint(0,100) == 1):
      #This will end the while loop
      elapsed_time = time.time() - StartTime
      elapsed_hours, rem = divmod(elapsed_time, 3600)
      elapsed_minutes, r = divmod(rem, 60)
      elapsed_seconds = elapsed_time

      #print ("StartTime:    ",StartTime, " Now:",time.time())
      print("ElapsedSeconds: ",round(elapsed_seconds))
      if elapsed_seconds >= RunSeconds:
        Done = True

    if (ScrollSleep > 0):
      time.sleep(ScrollSleep)
 
  #We want to clean up all our display, but then fade back into whatever what before this function was called
  #fade back into the previous display (likely Uptime)
  TheMatrix.Clear()
  BlankScreenArray  = ([[]])
  BlankScreenArray  = [[ (0,0,0) for i in range(HatWidth)] for i in range(HatHeight)]
  TransitionBetweenScreenArrays(OldArray = BlankScreenArray, NewArray = ScreenArrayBefore,TransitionType=1)





def ShowBeatingHeart(h=0,v=0,beats=10,Sleep=0):
  ScreenArray  = ([[]])
  ScreenArray  = [[ (0,0,0) for i in range(HatWidth)] for i in range(HatHeight)]

  ScreenArray = CopyAnimatedSpriteToScreenArrayZoom(HeartSprite,h,v,1,TheScreenArray=ScreenArray)

  #ZoomScreen(ScreenArray,1,32,Sleep)
  SpinShrinkTransition(ScreenArray, steps=32, delay = 0.01,start_zoom=0, end_zoom=100)
 
  

  for i in range(0,beats):
    time.sleep(0.25)
    ZoomScreen(ScreenArray,32,16,Sleep)
    time.sleep(0.125)
    ZoomScreen(ScreenArray,22,32,Sleep)

  SpinShrinkTransition(ScreenArray, steps=32, delay = 0.01,start_zoom=100, end_zoom=0)


def ShowBeatingImage(ImageLocation, h=0, v=0, beats=10, Sleep=0):
  """Display an image with a beating (zoom) effect."""
  image = Image.open(ImageLocation)
  image = image.convert('RGB')
  
  image.thumbnail((HatWidth, HatHeight), Image.LANCZOS)


  width, height = image.size

  # Center the image if h and v are both 0
  if h == 0 and v == 0:
    h = int((HatWidth  - width)  / 2)
    v = int((HatHeight - height) / 2)

  ScreenArray = [[(0, 0, 0) for _ in range(HatWidth)] for _ in range(HatHeight)]

  for y in range(height):
    for x in range(width):
      r, g, b = image.getpixel((x, y))
      H = x + h
      V = y + v
      if CheckBoundary(H, V) == 0:
        ScreenArray[V][H] = (r, g, b)

  SpinShrinkTransition(ScreenArray, steps=32, delay=0.01, start_zoom=0, end_zoom=100)

  for i in range(0, beats):
    time.sleep(0.25)
    ZoomScreen(ScreenArray, 32, 16, Sleep)
    time.sleep(0.125)
    ZoomScreen(ScreenArray, 22, 32, Sleep)

  SpinShrinkTransition(ScreenArray, steps=32, delay=0.01, start_zoom=100, end_zoom=0)




def ShowBeatingImageObject(image, h=0, v=0, beats=10, Sleep=0):
  """Display a beating effect for a preloaded PIL.Image object."""
  image = image.convert('RGB')
  image.thumbnail((HatWidth, HatHeight), Image.LANCZOS)

  width, height = image.size

  # Center the image if h and v are both 0
  if h == 0 and v == 0:
    h = int((HatWidth  - width)  / 2)
    v = int((HatHeight - height) / 2)

  ScreenArray = [[(0, 0, 0) for _ in range(HatWidth)] for _ in range(HatHeight)]

  for y in range(height):
    for x in range(width):
      r, g, b = image.getpixel((x, y))
      H = x + h
      V = y + v
      if CheckBoundary(H, V) == 0:
        ScreenArray[V][H] = (r, g, b)

  SpinShrinkTransition(ScreenArray, steps=32, delay=0.01, start_zoom=0, end_zoom=100)

  for i in range(0, beats):
    time.sleep(0.25)
    ZoomScreen(ScreenArray, 32, 16, Sleep)
    time.sleep(0.125)
    ZoomScreen(ScreenArray, 22, 32, Sleep)

  SpinShrinkTransition(ScreenArray, steps=32, delay=0.01, start_zoom=100, end_zoom=0)
 
  



def DisplayGIF(GIFName,width,height,Loops=5,sleep=0.03):
  #canvas = Image.new("RGB",(HatWidth,HatHeight),"black")
  global Canvas
  Canvas.Clear()
  gif = Image.open(GIFName, 'r')
  #resized =  gif.resize((32,32),Image.LANCZOS)

  ImageArray = []
  #convert the GIF into an array of resized frames
  index = 1
  for frame in ImageSequence.Iterator(gif):
      frame = frame.convert('RGB')
      resized = frame.resize((width,height),Image.LANCZOS)
      ImageArray.append(resized)
      index += 1

  h = (HatWidth  - width) / 2
  v = (HatHeight - height) / 2

  for loop in range(0,Loops):
    for i in range(0,index-1):
      Canvas.SetImage(ImageArray[i],h,v)
      Canvas = TheMatrix.SwapOnVSync(Canvas)
      time.sleep(sleep)





  


def DisplayStockPrice(Symbol="", Price=""):
    global ScreenArray

    # Step 1 - Save current screen
    OldArray = copy.deepcopy(ScreenArray)

    # Step 2 - Prepare new empty array
    NewArray = [[(0, 0, 0) for i in range(HatWidth)] for i in range(HatHeight)]

    # Step 3 - Create both sprites
    SymbolSprite = CreateBannerSprite(Symbol.upper())
    PriceSprite  = CreateBannerSprite(Price)

    SymbolSprite.r = 150
    SymbolSprite.g = 150
    SymbolSprite.b = 0

    PriceSprite.r = 0
    PriceSprite.g = 175
    PriceSprite.b = 0

    ZoomFactor = 2

    # Estimate sprite heights
    symbol_height = SymbolSprite.height * ZoomFactor
    price_height  = PriceSprite.height * ZoomFactor
    total_height  = symbol_height + price_height

    # Step 4 - Calculate vertical positioning (centered vertically)
    v_offset = max((HatHeight - total_height) // 2, 0)

    # Horizontal centering
    symbol_h = max((HatWidth - SymbolSprite.width * ZoomFactor) // 2, 0)
    price_h  = max((HatWidth - PriceSprite.width  * ZoomFactor) // 2, 0)

    # Step 5 - Draw both sprites onto the same NewArray
    NewArray = SymbolSprite.CopySpriteToScreenArrayZoom2(
        symbol_h, v_offset -1, ZoomFactor=ZoomFactor, InputScreenArray=NewArray
    )

    NewArray = PriceSprite.CopySpriteToScreenArrayZoom2(
        price_h, v_offset + symbol_height + 1, ZoomFactor=ZoomFactor, InputScreenArray=NewArray
    )

    # Step 6 - Transition
    TransitionBetweenScreenArrays(OldArray, NewArray, TransitionType=1)

    # Step 7 - Finalize
    CopyScreenArrayToCanvasVSync(NewArray)
    ScreenArray = copy.deepcopy(NewArray)











def SpinShrinkTransition(ScreenArray, steps=48, delay=0.03, start_zoom=100, end_zoom=100, StopEvent=None):
    """
    Spin and zoom transition for LED matrix screens.

    Parameters:
        ScreenArray : 2D list of RGB tuples (copied from ScreenArray)
        steps       : Number of frames
        delay       : Time per frame (seconds)
        start_zoom  : Starting zoom percentage (0 = invisible, 100 = normal size, 200 = 2x size, etc.)
        end_zoom    : Ending zoom percentage
        StopEvent   : Optional multiprocessing event for early exit
    """
    import time
    from PIL import Image

    global Canvas

    def render_transformed(buffer, zoom, angle):
        h, w = len(buffer), len(buffer[0])
        img = Image.new("RGB", (w, h))
        for y in range(h):
            for x in range(w):
                img.putpixel((x, y), buffer[y][x])

        scale = zoom / 100.0
        size = max(1, int(w * scale)), max(1, int(h * scale))
        img = img.resize(size, Image.BICUBIC).rotate(angle, expand=True)

        ox = (HatWidth - img.width) // 2
        oy = (HatHeight - img.height) // 2

        for y in range(img.height):
            for x in range(img.width):
                px, py = ox + x, oy + y
                if 0 <= px < HatWidth and 0 <= py < HatHeight:
                    r, g, b = img.getpixel((x, y))
                    setpixel(px, py, r, g, b)

    def render_final(buffer, zoom):
        if zoom <= 0:
            Canvas.Clear()
            return

        h, w = len(buffer), len(buffer[0])
        img = Image.new("RGB", (w, h))
        for y in range(h):
            for x in range(w):
                img.putpixel((x, y), buffer[y][x])

        scale = zoom / 100.0
        size = max(1, int(w * scale)), max(1, int(h * scale))
        img = img.resize(size, Image.BICUBIC)  # No rotation

        ox = (HatWidth - img.width) // 2
        oy = (HatHeight - img.height) // 2

        for y in range(img.height):
            for x in range(img.width):
                px, py = ox + x, oy + y
                if 0 <= px < HatWidth and 0 <= py < HatHeight:
                    r, g, b = img.getpixel((x, y))
                    setpixel(px, py, r, g, b)

    total_spin_degrees = 720

    for frame in range(steps):
        if StopEvent and StopEvent.is_set():
            break

        t = frame / (steps - 1)  # Ensures last frame is 1.0
        zoom = start_zoom + (end_zoom - start_zoom) * t
        angle = int(round(total_spin_degrees * t))

        render_transformed(ScreenArray, zoom, angle)
        Canvas = TheMatrix.SwapOnVSync(Canvas)
        time.sleep(delay)

    # Final frame correction
    render_final(ScreenArray, end_zoom)
    Canvas = TheMatrix.SwapOnVSync(Canvas)


def DisplayImage(image):
    """
    Display a PIL.Image using double-buffered swap on LED matrix.
    Ensures proper timing and flicker-free updates.
    """
    global Canvas
    if hasattr(image, "load"):
        Canvas.SetImage(image)
        Canvas = TheMatrix.SwapOnVSync(Canvas)
    else:
        raise TypeError("Input must be a PIL.Image object")




from PIL import Image, ImageDraw, ImageFont
import time
import textwrap

def scroll_sentence_star_wars(sentence, TextRGB=(200,200,0), base_font_size=12, tilt_factor=0.6, scroll_delay=0.06, font_path="/usr/share/fonts/truetype/noto/NotoMono-Regular.ttf"):

    global Canvas
    image_width = HatWidth
    base_spacing =12
    background_color = (0, 0, 0)

    # Word wrap
    font = ImageFont.truetype(font_path, base_font_size)
    max_chars_per_line = max(1, int(image_width / font.getlength("M")))
    lines = textwrap.wrap(sentence, width=max_chars_per_line)

    # Estimate image height
    est_height = len(lines) * base_spacing + 10
    img = Image.new("RGB", (image_width, est_height), color=background_color)
    draw = ImageDraw.Draw(img)

    # Draw each line
    y_cursor = 0
    for line in lines:
        draw.text((0, y_cursor), line, font=font, fill=TextRGB)
        y_cursor += base_spacing

    img_w, img_h = img.size

    # Scroll upwards from below screen
    for scroll_y in range(-HatHeight, img_h):
        Canvas.Clear()
        for screen_y in range(HatHeight):
            source_y = scroll_y + screen_y
            if source_y < 0 or source_y >= img_h:
                continue

            # Correct perspective scale: narrower at top
            scale = (screen_y / HatHeight) * tilt_factor + (1 - tilt_factor)
            scale = max(0.2, scale)

            #relative_pos = screen_y / HatHeight
            #scale = (relative_pos ** 2) * tilt_factor + (1 - tilt_factor)



            src_line = img.crop((0, source_y, image_width, source_y + 1)).resize(
                (int(image_width * scale), 1), resample=Image.BILINEAR
            )

            x_offset = (image_width - src_line.width) // 2
            for x in range(src_line.width):
                r, g, b = src_line.getpixel((x, 0))
                if 0 <= x + x_offset < HatWidth:
                    setpixelCanvas(x + x_offset, screen_y, r, g, b)

        Canvas = TheMatrix.SwapOnVSync(Canvas)
        time.sleep(scroll_delay)

def scroll_sentence_star_wars_old(sentence, tilt_factor=0.6, scroll_delay=0.06, font_path="/usr/share/fonts/truetype/noto/NotoMono-Regular.ttf"):
    global Canvas  # Ensure Canvas is accessible and modifiable
    image_width = HatWidth
    base_font_size = 11
    base_spacing = 14
    TextRGB = (235, 235, 235)
    background_color = (0, 0, 0)

    # Word wrap
    font = ImageFont.truetype(font_path, base_font_size)
    max_chars_per_line = max(1, int(image_width / font.getlength("M")))
    lines = textwrap.wrap(sentence, width=max_chars_per_line)

    # Estimate image height
    est_height = len(lines) * base_spacing + 100
    img = Image.new("RGB", (image_width, est_height), color=background_color)
    draw = ImageDraw.Draw(img)

    # Draw each line with spacing
    y_cursor = 0
    for line in lines:
        draw.text((0, y_cursor), line, font=font, fill=TextRGB)
        y_cursor += base_spacing

    # Scroll with perspective compression
    for scroll_y in range(0, y_cursor - HatHeight):
        Canvas.Clear()
        for screen_y in range(HatHeight):
            source_y = scroll_y + screen_y

            # Perspective scale factor: smaller at top
            scale = (screen_y / HatHeight) * tilt_factor + (1 - tilt_factor)
            scale = max(0.2, scale)

            src_line = img.crop((0, source_y, image_width, source_y + 1)).resize(
                (int(image_width * scale), 1), resample=Image.BILINEAR
            )

            # Center scaled line
            x_offset = (image_width - src_line.width) // 2
            for x in range(src_line.width):
                r, g, b = src_line.getpixel((x, 0))
                if 0 <= x + x_offset < HatWidth:
                    setpixelCanvas(x + x_offset, screen_y, r, g, b)

        Canvas = TheMatrix.SwapOnVSync(Canvas)
        time.sleep(scroll_delay)



def scroll_random_movie_intro(StopEvent=None):
    intros = [
        # Sci-Fi
        "Space... the final snooze button. This clock's mission: to seek out new alarms... - Clock Trek the Motion Clock",
        "I've seen things you people wouldn't believe... a talking clock with several impressive colors... - Blade Runner Director's Clock edition",
        "What if I told you... this clock controls more than just time? - Morpheus",
        "I'm sorry, Dave. I can't let you sleep in. Time to get up! ",
        "In space, no one can hear you hit snooze. But this clock sure tries. ",
        "The clock is out there. It can't be bargained with. It will wake you.",
        "88 miles per hour? This clock barely does 60 seconds a minute. - Clock to the Future",
        "The spice must flow... but not before it's time. ",
        "They came for conquest. They found a digital clock and got bored. - Some SciFi movie",
        "This clock is armed and fully operational - Emperor Whats his face",
        "Your inability to tell time is your weakness - Luke SkyClocker - Your faith in your watch is yours! - Emperor Whats his face",
        

        # Other Genres
        "One clock to rule them all... and in the darkness wake them.",
        "You're a wizard, Harry... now set your alarm.",
        "Fortune and glory, kid... right after this clock strikes seven.",
        "Life finds a way. But this clock finds Monday first.",
        "Is this a dream? No... it's just your 6AM alarm again.",
        "In the wasteland, fuel is scarce... but this clock runs forever.",
        "Good morning! And in case I don't see ya, it's time to get up!",
        "I'm gonna make you an offer you can't understand... - The Clock Father",
        "Why so snoozy?",
        "This is the way... to set your alarm.",
        "You either wake up a hero or snooze long enough to become the villain.",
        "Say hello to my little snooze button!",
        "Keep your friends close, and your alarms closer.",
        "Houston, we have overslept. - Apollo 13 O'Clock",
        "You can't handle the time! - A Few Good Clocks",
        "That'll do, clock. That'll do. - Babe: Pig in the Clock Store",
        "Frankly, my dear, I don't give a tick. - Gone With the Wind up Clock",
        "May the snooze be with you. - Star Wars: Sleepy Planet",
        "I'm not bad, I'm just wound that way. - Who Framed Roger's Clock",
        "To infinity... and five more minutes! - Toy Story Maybe",
        "Here's ticking at you, kid.",
        "Time will get you every ... uh ... time. - No Clock for Old Men",
        "It's not a man, it's a ticking machine!",
        "With great clocks comes great punctuality. - Spiderman: Home Alarm"

        
    ]

    sentence = random.choice(intros)
    scroll_sentence_star_wars(
        sentence,
        base_font_size = 12,
        TextRGB=(255,255,0),
        tilt_factor=0.4,
        scroll_delay=0.06,
        font_path="/usr/share/fonts/truetype/noto/NotoMono-Regular.ttf"
    )


def scroll_random_demotivational_quote(StopEvent=None):
    demotivationals = [
        "The road to success is always under construction.",
        "Dream big. Set goals. Then take a nap.",
        "Believe in yourself. Because no one else does.",
        "Hard work never killed anyone, but why risk it?",
        "If at first you don't succeed, skydiving definitely isn't for you.",
        "It could be that the purpose of your life is only to serve as a warning to others.",
        "You miss 100% of the naps you don't take.",
        "A journey of a thousand miles begins with a single 'meh'.",
        "Mistakes were made. Mostly by you.",
        "Some people graduate with honors, I am just honored to graduate.",
        "Don't be part of the problem, be the WHOLE problem!"
        "Teamwork: when you blame someone else together.",
        "Every corpse on Everest was once a highly motivated person.",
        "Work hard so you can earn the right to be tired.",
        "Try and fail, but don't fail to try... unless it's before coffee.",
        "The early bird gets the worm, but the second mouse gets the cheese.",
        "Your best just wasn't good enough.",
        "Shoot for the moon. If you miss, you'll float in space forever.",
        "Not everyone gets to be extraordinary. That's what makes it special.",
        "You're not being replaced. You're being upgraded… out of existence.",
        "When life closes a door, it locks all the windows too.",
        "The light at the end of the tunnel is a train.",
        "The light at the end of the tunnel has been turned off due to budget cuts.",
        "Failure is not an option — it's standard procedure.",
        "You can do anything... once. Poorly.",
        "Just because you're unique doesn't mean you're useful.",
        "Aim low. You'll never be disappointed.",
        "It's not that you're replaceable. It's just that we already replaced you.",
        "Success is just failure that hasn't happened yet.",
        "Always give 110%. Unless you're donating blood.",
        "Your best just wasn't good enough, but thanks for trying.",
        "There's no 'I' in team, but there's a 'U' in 'useless.'"
        

    ]

    sentence = random.choice(demotivationals)
    scroll_sentence_star_wars(
        sentence,
        base_font_size=12,
        TextRGB=(255, 100, 100),
        tilt_factor=0.4,
        scroll_delay=0.06,
        font_path="/usr/share/fonts/truetype/noto/NotoMono-Regular.ttf"
    )




#------------------------------------------------------------------------------
# MAIN SECTION                                                               --
#                                                                            --
#                                                                            --
#                                                                            --
#                                                                            --
#                                                                            --
#------------------------------------------------------------------------------


def ApplyGamma(value, gamma):
    corrected = int(value * gamma)
    return min(corrected, 255)




def ActivateRGBMatrix():
   
   
    
    global TheMatrix, Canvas, ScreenArray, HatWidth, HatHeight
    LoadConfigData()
   

    # ------------------------------------------------------------------------------
    # RGBMatrixOptions Explanation
    # ------------------------------------------------------------------------------
    # The RGBMatrixOptions class is used to configure how the LED matrix behaves.
    # This object is passed to the RGBMatrix constructor to define display settings.

    # Common options include:
    #
    #   rows              - Number of rows per panel (e.g., 32, 64)
    #   cols              - Number of columns per panel (e.g., 64, 128)
    #   chain_length      - Number of daisy-chained panels horizontally
    #   parallel          - Number of parallel chains (for larger displays)
    #   brightness        - LED brightness (0–100)
    #   gpio_slowdown     - Reduces signal speed for hardware compatibility (0–4)
    #   disable_hardware_pulsing - Set to True to avoid PWM interference
    #   show_refresh_rate - Display refresh rate on console (for debugging)

    # Example:
    # options = RGBMatrixOptions()
    # options.rows = 32
    # options.cols = 64
    # options.chain_length = 2
    # options.parallel = 1
    # options.brightness = 75
    # matrix = RGBMatrix(options=options)
    # ------------------------------------------------------------------------------


    #load config data to see if there is an override value for hatwidth/hatheight

    # -------------------------------
    # RGBMatrix Options
    # -------------------------------
    options = RGBMatrixOptions()
    options.rows = 32
    options.cols = 64
    options.chain_length = 1
    options.parallel = 1
    options.hardware_mapping = 'adafruit-hat'       # Adafruit HAT specific
    options.gpio_slowdown = 3                      # Adjust if you see flicker
    options.brightness = 100                         # Keep this moderate
    options.pwm_bits = 11                           # Lower for better timing
    options.pwm_lsb_nanoseconds = 130               # Tweak this if needed
    options.scan_mode = 0                           # Progressive
    options.disable_hardware_pulsing = False
    options.drop_privileges = False                 # Avoid permission issues

    HatWidth  = options.cols
    HatHeight = options.rows

    #The matrix object is what is used to interact with the LED display
    TheMatrix    = RGBMatrix(options = options)
    Canvas = TheMatrix.CreateFrameCanvas()
    Canvas.Fill(0, 0, 0)
    ScreenArray = [[(0, 0, 0) for _ in range(HatWidth)] for _ in range(HatHeight)]

    print(f"LED Matrix Brightness: {options.brightness}")

    print("LEDarcade initialized.")







_initialized = False
def Initialize():
    global TheMatrix, Canvas, ScreenArray, HatWidth, HatHeight, Gamma, _initialized
    print("\n" + "=" * 65)
    print("🚀 LEDarcade Initialized")
    print("=" * 65)
    print("A retro-inspired LED matrix graphics engine.")
    print("Created by William McEvoy (@datagod) for Raspberry Pi systems.")
    print("Features:")
    print(" - Real-time graphics and animations")
    print(" - Flight tracking, gaming, and Twitch integrations")
    print(" - Supports 32x32, 32x64, 32x128 LED panel arrays")
    print(" - Easily extensible with sprite and animation APIs")
    print("-------------------------------------------------------------")
    print("Explore the pixel universe with LEDarcade!")
    print("=" * 65 + "\n")
    print("")
    print("")
    
    if _initialized:
        print("LEDarcade already initialized.  Skipping")
        return
    _initialized = True




    ActivateRGBMatrix()
    if TheMatrix is None:
        raise RuntimeError("ERROR: TheMatrix failed to initialize. Check RGBMatrixOptions or matrix hardware connection.")




if __name__ == "__main__":
    print("*******************************************")
    print("** LEDarcade                             **")
    print("*******************************************")
    #os.system('clear')
    Gamma = 1.0  # Default gamma, should be overwritten by config if needed
    Initialize()
    

