
'''
TO DO:
 
'''



import os
os.system('cls||clear')

import sys
import re   # regular expression

import LEDarcade as LED
from rgbmatrix import graphics
from rgbmatrix import RGBMatrix, RGBMatrixOptions

import random
from configparser import ConfigParser
import requests
import traceback
import socket



import json




import pprint


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



#Configurations
STOCK_SYMBOL   = True

#Files
KeyConfigFileName = "KeyConfig.ini" 






#----------------------------------------
#-- FILE ACCESS Functions              --
#----------------------------------------

def LoadConfigFiles():
     
  
  global ALPHA_API_KEY
  global STOCK_SYMBOL

  
  print ("--Load Stock Keys--")
  print("KeyConfig.ini")
  if (os.path.exists(KeyConfigFileName)):

    print ("Config file (",KeyConfigFileName,"): found")
    KeyFile = ConfigParser()
    KeyFile.read(KeyConfigFileName)

    #Get key
    ALPHA_API_KEY = KeyFile.get("KEYS","ALPhA_API_KEY")
    STOCK_SYMBOL = KeyFile.get("KEYS","STOCK_SYMBOL")
   
    
    print("ALPHA_API_KEY:              ",ALPHA_API_KEY)
    print("STOCK_SYMBOL:               ",STOCK_SYMBOL)
    print ("--------------------")
    print (" ")

  else:
    #To be finished later
    print ("ERROR: Could not locate Key file (",KeyConfigFileName,"). Create a file and make sure to pupulate it with your own keys.")



def CheckConfigFiles():
  #This function will create the config files if they do not exist and populate them 
  #with examples

  #KeyConfig.ini


  if (os.path.exists(KeyConfigFileName)):
    print("File found:",KeyConfigFileName)
  else:
    try:
      print("Warning! File not found:",KeyConfigFileName)
      print("We will attempt to create a file with default values")
  
      #CREATE A CONFIG FILE
      KeyConfigFile = open(KeyConfigFileName,'a+')
      KeyConfigFile.write("[KEYS]\n")
      KeyConfigFile.write("  ALPHA_API_KEY            = YOUR API KEY HERE\n")
      KeyConfigFile.write("  STOCK_SYMBOL             = TSLA\n")
      KeyConfigFile.write("\n")
      
      print("File created")
    except Exception as ErrorMessage:
      TraceMessage = traceback.format_exc()
      AdditionalInfo = "Creating the {}file".format(KeyConfigFileName)
      LED.ErrorHandler(ErrorMessage,TraceMessage,AdditionalInfo)
    




#------------------------------------------------------------------------------
# CUSTOM FUNCTIONS                                                           --
#------------------------------------------------------------------------------


def GetStockPrice(symbol):
    
    global ALPHA_API_KEY

    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={symbol}&interval=60min&apikey={ALPHA_API_KEY}"
    url = f'https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={ALPHA_API_KEY}'
    response = requests.get(url)
    data = response.json()

    print(data)

    if 'Global Quote' in data:
        current_price = data['Global Quote']['05. price']
        print(f"Current stock price of {symbol}: ${current_price}")


    return current_price









#------------------------------------------------------------------------------
# MAIN SECTION                                                               --
#------------------------------------------------------------------------------



print ("---------------------------------------------------------------")
print ("WELCOME TO THE LED ARCADE - Stock Price Displayorama            ")
print ("")
print ("BY DATAGOD and The Blue Friend")
print ("")
print ("This program will display the stock prices for various ")
print ("stock symbols.")
print ("---------------------------------------------------------------")
print ("")
print ("")







print ("--Start--")
#Fake boot sequence
LED.ClearBigLED()
LED.ClearBuffers()
CursorH = 0
CursorV = 0
LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"LED Stock Tracker",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalTypeSpeed)
LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"by datagod and The Blue Friend",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalTypeSpeed)
LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,".........................",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.025,ScrollSpeed=ScrollSleep)
LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"Boot sequence initiated",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)
LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"ESTABLISHING CONNECTION to NASDAQ",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)
LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,".........................",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.025,ScrollSpeed=ScrollSleep)
LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"CONNECTON VERIFIED",CursorH=CursorH,CursorV=CursorV,MessageRGB=(0,200,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)
LED.BlinkCursor(CursorH= CursorH,CursorV=CursorV,CursorRGB=CursorRGB,CursorDarkRGB=CursorDarkRGB,BlinkSpeed=0.5,BlinkCount=2)
#IPAddress = LED.ShowIPAddress(Wait=5)

# Load API Key and Stock Symbol
CheckConfigFiles()
LoadConfigFiles()


while 1==1:

  StockPrice = GetStockPrice(STOCK_SYMBOL)
  LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"TESLA CURRENT PRICE",CursorH=CursorH,CursorV=CursorV,MessageRGB=(200,0,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalTypeSpeed)
  LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,StockPrice,CursorH=CursorH,CursorV=CursorV,MessageRGB=(0,200,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalTypeSpeed)
  LED.BlinkCursor(CursorH= CursorH,CursorV=CursorV,CursorRGB=CursorRGB,CursorDarkRGB=CursorDarkRGB,BlinkSpeed=0.5,BlinkCount=20)
  LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,".........................",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=1,ScrollSpeed=ScrollSleep)









 