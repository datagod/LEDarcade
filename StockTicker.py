

"""
================================================================================
 LED Stock Ticker Display - Powered by LEDarcade
================================================================================

 Description:
 ------------
 This program fetches real-time stock prices using the yfinance library and 
 displays them on a connected LED matrix (e.g., 32x64 or 32x128) using the 
 LEDarcade rendering system. Each stock's price is periodically updated, and
 visual cues (up/down arrows) indicate movement direction since the last check.

 Features:
 ---------
 - Pulls live stock prices using Yahoo Finance (via yfinance)
 - Displays stock prices on an LED matrix using the LEDarcade library
 - Visual indicators:
     ▸ chr(193): Price increase (shown as up arrow)
     ▸ chr(194): Price decrease (shown as down arrow)
     ▸ Space character: No price change
 - Automatically checks prices every 15 minutes
 - Displays each stock for a configurable delay (default 2 seconds)
 - Robust error handling and configuration file support

 Configuration:
 --------------
 - The stock symbols and API key are read from a file: `KeyConfig.ini`
     Example content:
        [KEYS]
        ALPHA_API_KEY = YOUR_API_KEY_HERE
        STOCK_SYMBOLS = TSLA,MSFT,AAPL

 - Output to LED handled by:
     ▸ LED.DisplayStockPrice(symbol, formatted_price)
     ▸ Formatting assumes CreateBannerSprite handles directional symbols

 Requirements:
 -------------
 - Python 3.x
 - yfinance (pip install yfinance)
 - rgbmatrix library for controlling the LED display
 - LEDarcade module (https://github.com/datagod/LEDarcade)
 - Raspberry Pi with supported LED matrix hat

 Author:
 -------
 William McEvoy (aka datagod)
 Metropolis Dreamware Inc.
 License: Non-commercial use only. Contact for commercial licensing.

 Revision History:
 -----------------
 v1.0 - Initial stock ticker display with direction indicators
 v1.1 - Added timer logic to control fetch frequency and display loop

"""



import os
os.system('cls||clear')

import yfinance as yf

import sys
import re   # regular expression

import LEDarcade as LED
from rgbmatrix import graphics
from rgbmatrix import RGBMatrix, RGBMatrixOptions

import random
from configparser import ConfigParser
import requests
import traceback


import time
from datetime import datetime, timezone



#---------------------------------------
#Variable declaration section
#---------------------------------------
ScrollSleep         = 0.05
TerminalTypeSpeed   = 0.01  #pause in seconds between characters
TerminalScrollSpeed = 0.01  #pause in seconds between new lines
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
STOCK_SYMBOLS  = []

#Files
KeyConfigFileName = "KeyConfig.ini" 






#----------------------------------------
#-- FILE ACCESS Functions              --
#----------------------------------------

def CheckConfigFiles():
    if os.path.exists(KeyConfigFileName):
        print("File found:", KeyConfigFileName)
    else:
        try:
            print("Warning! File not found:", KeyConfigFileName)
            print("We will attempt to create a file with default values")
            with open(KeyConfigFileName, 'a+') as KeyConfigFile:
                KeyConfigFile.write("[KEYS]\n")
                KeyConfigFile.write("STOCK_SYMBOLS = TSLA,MSFT,AAPL\n")
                KeyConfigFile.write("\n")
            print("File created")
        except Exception as ErrorMessage:
            TraceMessage = traceback.format_exc()
            AdditionalInfo = f"Creating the {KeyConfigFileName} file"
            print(f"[Error] {AdditionalInfo}\n{ErrorMessage}\n{TraceMessage}")

def LoadConfigFiles():
    global STOCK_SYMBOLS

    print("--Load Stock Keys--")
    if os.path.exists(KeyConfigFileName):
        print(f"Config file ({KeyConfigFileName}): found")
        KeyFile = ConfigParser()
        KeyFile.read(KeyConfigFileName)

        STOCK_SYMBOLS = KeyFile.get("KEYS", "STOCK_SYMBOLS").replace(' ', '').split(',')

        print("STOCK_SYMBOLS:              ", ', '.join(STOCK_SYMBOLS))
        print("--------------------\n")
    else:
        print(f"ERROR: Could not locate Key file ({KeyConfigFileName}). Create it and populate it with your own keys.")



#------------------------------------------------------------------------------
# CUSTOM FUNCTIONS                                                           --
#------------------------------------------------------------------------------


def GetStockPrice(symbol):
    try:
        stock = yf.Ticker(symbol)
        if not stock.info:
            raise ValueError(f"No data returned for {symbol}")

        price = stock.info.get('regularMarketPrice')
        if price is None:
            raise KeyError(f"regularMarketPrice not found for {symbol}")

        price_formatted = "{:.2f}".format(price)
        print(f"{symbol}: ${price_formatted}")
        return price

    except KeyError as ke:
        print(f"[Error] Missing data for {symbol}: {ke}")
    except ValueError as ve:
        print(f"[Error] No valid data for {symbol}: {ve}")
    except Exception as e:
        print(f"[Error] Unexpected error fetching {symbol}: {e}")

    return None





#------------------------------------------------------------------------------
# MAIN SECTION                                                               --
#------------------------------------------------------------------------------

def main():


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
  LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"LED Stock Ticker",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalTypeSpeed)
  LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"by datagod and Jacob Jack",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalTypeSpeed)
  LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,".........................",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=ScrollSleep)
  LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"Boot sequence initiated",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)
  LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"ESTABLISHING CONNECTION to NASDAQ",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)
  LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,".........................",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.025,ScrollSpeed=ScrollSleep)
  LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"CONNECTON VERIFIED",CursorH=CursorH,CursorV=CursorV,MessageRGB=(0,200,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)
  LED.BlinkCursor(CursorH= CursorH,CursorV=CursorV,CursorRGB=CursorRGB,CursorDarkRGB=CursorDarkRGB,BlinkSpeed=0.5,BlinkCount=2)
  #IPAddress = LED.ShowIPAddress(Wait=5)

  # Load API Key and Stock Symbol
  CheckConfigFiles()
  LoadConfigFiles()


    
    
  FETCH_INTERVAL = 900  # 15 minutes
  DISPLAY_DELAY = 2     # 2 seconds between displaying each stock

  stock_prices = {}
  previous_prices = {symbol: 0.0 for symbol in STOCK_SYMBOLS}
  last_fetch_time = 0

  while True:
      current_time = time.time()

      # Fetch stock prices if interval has passed or none are available
      if current_time - last_fetch_time >= FETCH_INTERVAL or not stock_prices:
          print("Fetching stock prices...")
          stock_prices.clear()

          for symbol in STOCK_SYMBOLS:
              try:
                  price_value = GetStockPrice(symbol)
                  if price_value is None:
                      raise ValueError("Price returned None")

                  StockPrice = "{:.2f}".format(price_value)

                  # Determine price change symbol using extended ASCII
                  prev_price = previous_prices.get(symbol)
                  if price_value > prev_price:
                      display_price = chr(193) + StockPrice  # Up arrow (example: '┴')
                  elif price_value < prev_price:
                      display_price = chr(194) + StockPrice  # Down arrow (example: '┬')
                  else:
                      display_price = StockPrice       # No change

                  previous_prices[symbol] = price_value
                  stock_prices[symbol] = display_price
                  print(f"Fetched {symbol}: {display_price}")

              except Exception as e:
                  print(f"[Warning] Failed to get stock price for {symbol}. Error: {e}")

          last_fetch_time = current_time
          print("Stock prices updated.\n")

      # Display all current stock prices one at a time
      for symbol, display_price in stock_prices.items():
          try:
              LED.DisplayStockPrice(symbol, display_price)
              time.sleep(DISPLAY_DELAY)
          except Exception as e:
              print(f"[Warning] Display error for {symbol}. Error: {e}")

#Otherwise it is part of a module and we don't execute it 
if __name__ == "__main__":
    main()


