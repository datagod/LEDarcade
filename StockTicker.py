

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
import re
import LEDarcade as LED
LED.Initialize()
from rgbmatrix import graphics
from rgbmatrix import RGBMatrix, RGBMatrixOptions
import random
from configparser import ConfigParser
import requests
import traceback
import time
from datetime import datetime, timezone
import json
import logging

#---------------------------------------
# Variable declaration section
#---------------------------------------
ScrollSleep         = 0.05
TerminalTypeSpeed   = 0.01
TerminalScrollSpeed = 0.01
CursorRGB           = (0,255,0)
CursorDarkRGB       = (0,50,0)
HatHeight = 32
HatWidth  = 64
StreamBrightness = 20
GifBrightness    = 25
MaxBrightness    = 80
LED.ClockH,      LED.ClockV,      LED.ClockRGB      = 0,0,  (0,150,0)
LED.DayOfWeekH,  LED.DayOfWeekV,  LED.DayOfWeekRGB  = 8,20,  (125,20,20)
LED.MonthH,      LED.MonthV,      LED.MonthRGB      = 28,20, (125,30,0)
LED.DayOfMonthH, LED.DayOfMonthV, LED.DayOfMonthRGB = 47,20, (115,40,10)
TerminalRGB = (0,200,0)
CursorRGB = (0,75,0)
STOCK_SYMBOLS  = []
KeyConfigFileName = "KeyConfig.ini"
StockPricesFileName = "stock_prices.json"
StockHistoryFileName = "stock_history.log"

#---------------------------------------
#-- FILE ACCESS Functions              --
#---------------------------------------

def CheckConfigFiles():
    """Check if KeyConfig.ini exists; create with defaults if missing."""
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
    """Load stock symbols from KeyConfig.ini."""
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

def LoadStockPrices():
    """Load stock prices from stock_prices.json, strip arrows, validate, and initialize previous_prices."""
    global stock_prices, previous_prices
    if os.path.exists(StockPricesFileName):
        try:
            with open(StockPricesFileName, 'r') as file:
                loaded_prices = json.load(file)
                # Strip arrows and validate
                cleaned_prices = {}
                for symbol, price in loaded_prices.items():
                    # Remove arrow characters (chr(193) or chr(194)) if present
                    cleaned_price = price.lstrip(chr(193)).lstrip(chr(194))
                    cleaned_prices[symbol] = cleaned_price
                    # Parse numerical price for previous_prices
                    try:
                        numerical_price = float(cleaned_price)
                        previous_prices[symbol] = numerical_price
                    except ValueError:
                        print(f"[Warning] Invalid price format for {symbol}: {cleaned_price}")
                        previous_prices[symbol] = 0.0
                # Validate against STOCK_SYMBOLS
                valid_prices = {k: v for k, v in cleaned_prices.items() if k in STOCK_SYMBOLS}
                stock_prices.update(valid_prices)
                if len(valid_prices) < len(loaded_prices):
                    print(f"[Warning] Some loaded prices were invalid or for unknown symbols: {set(loaded_prices) - set(STOCK_SYMBOLS)}")
                print(f"Loaded stock prices from {StockPricesFileName}:")
                for symbol, price in valid_prices.items():
                    print(f"{symbol}: {price}")
        except Exception as e:
            print(f"[Error] Failed to load stock prices from {StockPricesFileName}: {e}")
            logging.error(f"Failed to load stock prices: {e}")
    else:
        print(f"No stock prices file found at {StockPricesFileName}. Starting with empty prices.")

def SaveStockPrices():
    """Save stock prices to stock_prices.json."""
    try:
        with open(StockPricesFileName, 'w') as file:
            json.dump(stock_prices, file, indent=4)
            print(f"Saved stock prices to {StockPricesFileName}")
            logging.info(f"Saved stock prices to {StockPricesFileName}: {stock_prices}")
    except Exception as e:
        print(f"[Error] Failed to save stock prices to {StockPricesFileName}: {e}")
        logging.error(f"Failed to save stock prices: {e}")

def LogStockPrice(symbol, price_value, display_price):
    """Log stock price with timestamp to stock_history.log."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z")
    logging.info(f"{timestamp} | {symbol} | ${price_value:.2f} | Display: {display_price}")

#---------------------------------------
#-- CUSTOM FUNCTIONS                  --
#---------------------------------------

def GetStockPrice(symbol):
    """Fetch current stock price for the given symbol using yfinance."""
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

#---------------------------------------
#-- MAIN SECTION                      --
#---------------------------------------



def main(Duration=10, StopEvent=None, ShowIntro=False):
    """Main function to run the stock ticker display."""
    global stock_prices, previous_prices
    # Configure logging
    logging.basicConfig(
        filename=StockHistoryFileName,
        level=logging.INFO,
        format='%(message)s'
    )

    DISPLAY_DELAY = 2     # 2 seconds


    print ("---------------------------------------------------------------")
    print ("WELCOME TO THE LED ARCADE - Stock Price Displayorama (Enhanced) ")
    print ("")
    print ("BY DATAGOD and The Blue Friend")
    print ("")
    print ("This program will display stock prices, save them to a file, ")
    print ("and log price history.")
    print ("---------------------------------------------------------------")
    print ("")
    print ("--Start--")
    
    if ShowIntro:
        LED.ClearBigLED()
        LED.ClearBuffers()
        CursorH = 0
        CursorV = 0
        LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"LED Stock Ticker",CursorH=CursorH,CursorV=CursorV,MessageRGB=(150,150,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalTypeSpeed)
        LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"by datagod and Jacob Jack",CursorH=CursorH,CursorV=CursorV,MessageRGB=(150,150,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalTypeSpeed)
        LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,".........................",CursorH=CursorH,CursorV=CursorV,MessageRGB=(150,150,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=ScrollSleep)
        LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"Boot sequence initiated",CursorH=CursorH,CursorV=CursorV,MessageRGB=(150,150,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)
        LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"ESTABLISHING CONNECTION to NASDAQ",CursorH=CursorH,CursorV=CursorV,MessageRGB=(150,150,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)
        LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,".........................",CursorH=CursorH,CursorV=CursorV,MessageRGB=(150,150,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.025,ScrollSpeed=ScrollSleep)
        LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"CONNECTON VERIFIED",CursorH=CursorH,CursorV=CursorV,MessageRGB=(0,200,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)
        LED.BlinkCursor(CursorH=CursorH,CursorV=CursorV,CursorRGB=CursorRGB,CursorDarkRGB=CursorDarkRGB,BlinkSpeed=0.5,BlinkCount=2)

    # Load configuration and stock prices
    CheckConfigFiles()
    LoadConfigFiles()
    stock_prices = {}
    previous_prices = {symbol: 0.0 for symbol in STOCK_SYMBOLS}  # Initialize before loading
    LoadStockPrices()

    # Display loaded (old) stock prices without arrows
    if stock_prices:
        print("Displaying previously saved stock prices (without arrows)...")
        for symbol, display_price in stock_prices.items():
            try:
                LED.DisplayStockPrice(symbol, display_price)
                time.sleep(DISPLAY_DELAY)
            except Exception as e:
                print(f"[Warning] Display error for {symbol} (old price): {e}")
                logging.error(f"Display error for {symbol} (old price): {e}")
    else:
        print("No saved stock prices to display.")

    # Immediately fetch new stock prices
    FETCH_INTERVAL = 900  # 15 minutes
    DISPLAY_DELAY = 2     # 2 seconds
    last_fetch_time = 0

    try:
        while True:
            current_time = time.time()
            if StopEvent and StopEvent.is_set():
                print("\n" + "="*40)
                print("[StockTicker] StopEvent received")
                print("-> Shutting down gracefully...")
                print("="*40 + "\n")
                SaveStockPrices()
                break

            if current_time - last_fetch_time >= FETCH_INTERVAL or not stock_prices:
                print("Fetching stock prices...")
                stock_prices.clear()
                for symbol in STOCK_SYMBOLS:
                    try:
                        price_value = GetStockPrice(symbol)
                        if price_value is None:
                            raise ValueError("Price returned None")
                        StockPrice = "{:.2f}".format(price_value)
                        prev_price = previous_prices.get(symbol, 0.0)
                        if price_value > prev_price:
                            display_price = chr(193) + StockPrice
                        elif price_value < prev_price:
                            display_price = chr(194) + StockPrice
                        else:
                            display_price = StockPrice
                        previous_prices[symbol] = price_value
                        stock_prices[symbol] = display_price
                        print(f"Fetched {symbol}: {display_price}")
                        LogStockPrice(symbol, price_value, display_price)
                    except Exception as e:
                        print(f"[Warning] Failed to get stock price for {symbol}. Error: {e}")
                        logging.error(f"Failed to fetch stock price for {symbol}: {e}")
                last_fetch_time = current_time
                SaveStockPrices()
                print("Stock prices updated.\n")

            for symbol, display_price in stock_prices.items():
                try:
                    LED.DisplayStockPrice(symbol, display_price)
                    time.sleep(DISPLAY_DELAY)
                except Exception as e:
                    print(f"[Warning] Display error for {symbol}: {e}")
                    logging.error(f"Display error for {symbol}: {e}")
    except KeyboardInterrupt:
        print("\n" + "="*40)
        print("[StockTicker] KeyboardInterrupt received")
        print("-> Shutting down gracefully...")
        print("="*40 + "\n")
        SaveStockPrices()
        LED.ClearBigLED()

if __name__ == "__main__":
    main(Duration=10, StopEvent=None, ShowIntro=False)