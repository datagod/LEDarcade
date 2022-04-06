# %%

'''
TO DO:
 - Read the EventQueue even when displaying the digital clock
   Exit the clock mode and react to the event 

- maybe spawn the clock modes with multiprocessing and allow the twitch bot to process via ASYNC processes

'''


import os
os.system('cls||clear')

import sys

import LEDarcade as LED
from rgbmatrix import graphics
from rgbmatrix import RGBMatrix, RGBMatrixOptions

import random
from configparser import SafeConfigParser
import requests
import traceback
import socket
import twitchio


#multi processing
import asyncio
import multiprocessing

from flask import Flask, request, abort
from multiprocessing.connection import Client
import json



#Twitch
from twitchio.ext import pubsub
from twitchio.ext import commands

#Webhooks
import patreon
#import flask
#from flask import Flask, request, abort


import pprint
import copy

import irc.bot
import select




#list of connection messages
from CustomMessages import ConnectionMessages
from CustomMessages import ChatStartMessages


import time
from datetime import datetime, timezone


#games
import DotInvaders as DI
import Outbreak    as OB
import Defender    as DE
import Tron        as TR







#---------------------------------------
#Variable declaration section
#---------------------------------------
ScrollSleep         = 0.025
TerminalTypeSpeed   = 0.02  #pause in seconds between characters
TerminalScrollSpeed = 0.02  #pause in seconds between new lines
CursorRGB           = (0,255,0)
CursorDarkRGB       = (0,50,0)


#TWITCH VARIABLES
ACCESS_TOKEN      = ''
REFRESH_TOKEN     = ''
CLIENT_ID         = ''

CHANNEL             = ''
CHANNEL_BIG_TEXT    = ''
CHANNEL_LITTLE_TEXT = ''

USER_ID           = ''
BROADCASTER_ID    = ''
PROFILE_IMAGE_URL = ''
VIEW_COUNT        = ''
BOT_CHANNEL       = ''
BOT_ACCESS_TOKEN  = ''
BOT_REFRESH_TOKEN = ''
BOT_CLIENT_ID     = ''

#PATREON VARIABLES
PATREON_CLIENT_ID            = ''
PATREON_CLIENT_SECRET        = ''
PATREON_CREATOR_ACCESS_TOKEN = ''


#User / Channel Info
GameName        = ''
Title           = ''

# Stream Info
StreamStartedAt       = ''
StreamStartedTime     = ''
StreamStartedDateTime = ''
StreamDurationHHMMSS  = ''
StreamType            = ''
ViewerCount           = 0
StreamActive          = False

#Follower Info
Followers            = 0
Subs                 = 0

#HypeTrain info
HypeTrainStartTime   = ''
HypeTrainExpireTime  = ''
HypeTrainGoal        = ''
HypeTrainLevel       = 0
HypeTrainTotal       = ''



HatHeight = 32
HatWidth  = 64


  

#Configurations
SHOW_VIEWERS   = True
SHOW_FOLLOWERS = True
SHOW_SUBS      = True
SHOW_VIEWS     = True
SHOW_CHATBOT_MESSAGES = False

#Files
KeyConfigFileName = "KeyConfig.ini" 
MyConfigFileName  = "MyConfig.ini"



#Sprite display locations
LED.ClockH,      LED.ClockV,      LED.ClockRGB      = 0,0,  (0,150,0)
LED.DayOfWeekH,  LED.DayOfWeekV,  LED.DayOfWeekRGB  = 8,20,  (125,20,20)
LED.MonthH,      LED.MonthV,      LED.MonthRGB      = 28,20, (125,30,0)
LED.DayOfMonthH, LED.DayOfMonthV, LED.DayOfMonthRGB = 47,20, (115,40,10)

#Colors
TerminalRGB = (0,200,0)
CursorRGB = (0,75,0)


#Data structures
#EventQueue = asyncio.Queue()  #used to store and process webhook messages
MPM = multiprocessing.Manager()
EventQueue = MPM.Queue()       #used to store and process webhook messages




class Bot(commands.Bot):
#This started out as a Twitch Bot but has grown into a more complex program

    CursorH             = 0
    CursorV             = 0
    CursorRGB           = (0,255,0)
    CursorDarkRGB       = (0,50,0)
    AnimationDelay      = 30
    LastMessageReceived = time.time()
    LastStreamCheckTime = time.time()
    MinutesToWaitBeforeCheckingStream = 1       #check the stream this often
    MinutesToWaitBeforeClosing        = 0       #close chat after X minutes of inactivity
    #MinutesMaxTime                   = 10      #exit chat terminal after X minutes and display clock
    BotStartTime        = time.time()
    SendStartupMessage  = True
    BotTypeSpeed        = TerminalTypeSpeed
    BotScrollSpeed      = TerminalScrollSpeed
    MessageCount        = 0
    SpeedupMessageCount = 5
    ChatTerminalOn      = False
    Channel             = ''



    def __init__(self):
        # Initialise our Bot with our access token, prefix and a list of channels to join on boot...
        # prefix can be a callable, which returns a list of strings or a string...
        # initial_channels can also be a callable which returns a list of strings...

        
        print("Bot Initialization")
        print("BOT_CHANNEL:     ",BOT_CHANNEL)
        print("BOT_ACCESS_TOKEN:",BOT_ACCESS_TOKEN)
      
       
        print("=====================================================")
        print("Initiating client object to connect to twitch")
        print("Initial_Channels:",BOT_CHANNEL)
        super().__init__(token=BOT_ACCESS_TOKEN, prefix='?', initial_channels=[BOT_CHANNEL])
        self.BotStartTime   = time.time()
        LastMessageReceived = time.time()
        print("=====================================================")
        
        



    async def my_custom_startup(self):

        
        await asyncio.sleep(1)
        self.Channel = self.get_channel(BOT_CHANNEL)
        #channel2 = self.fetch_channel(CHANNEL_ID)

        #Check Twitch advanced info 
        await self.CheckStream()

        if(StreamActive == True and SHOW_CHATBOT_MESSAGES == True):
          self.ChatTerminalOn = True
        else:
          #Explain the main intro is not live
          LED.ShowTitleScreen(
            BigText             = "404",
            BigTextRGB          = LED.MedPurple,
            BigTextShadowRGB    = LED.ShadowPurple,
            LittleText          = "NO STREAM",
            LittleTextRGB       = LED.MedRed,
            LittleTextShadowRGB = LED.ShadowRed, 
            ScrollText          = CHANNEL + " not active. Try again later...",
            ScrollTextRGB       = LED.MedYellow,
            ScrollSleep         = ScrollSleep /2, # time in seconds to control the scrolling (0.005 is fast, 0.1 is kinda slow)
            DisplayTime         = 1,           # time in seconds to wait before exiting 
            ExitEffect          = 5,           # 0=Random / 1=shrink / 2=zoom out / 3=bounce / 4=fade /5=fallingsand
            LittleTextZoom      = 1
            )
          self.ChatTerminalOn = False
        
        
        


        
      

    #---------------------------------------
    #- Check Stream Info                  --
    #---------------------------------------
    # check to see if the stream is live or not
    async def CheckStream(self):
      print("Checking if stream is active")
      GetBasicTwitchInfo()
      self.LastStreamCheckTime = time.time()
      #Show title info if Main stream is active
      #if(StreamActive == True):
      #  await self.DisplayConnectingToTerminalMessage()
      #  await self.DisplayRandomConnectionMessage()

        


    #---------------------------------------
    #- Perform Time Based Actions         --
    #---------------------------------------

    async def PerformTimeBasedActions(self):
        loop = asyncio.get_running_loop()
        #end_time = loop.time() + self.AnimationDelay
        
        if(StreamActive == True):
          #await self.DisplayConnectingToTerminalMessage()
          await self.DisplayRandomConnectionMessage()

        while True:
          
          #asyncio.sleep suspends the current task, allowing other processes to run
          await asyncio.sleep(1)


          #Check the event queue for incoming data
          await self.ReadEventQueue()
          #print("Stream Status:",StreamActive, 'TwithTimerOn:',LED.TwitchTimerOn)


          if(StreamActive == True):
            if (self.ChatTerminalOn == True):
              
              #Don't blink cursor if displaying the uptime
              #maybe have a blinkcursor switch instead
              if(LED.TwitchTimerOn == False):
                LED.BlinkCursor(CursorH= self.CursorH,CursorV=self.CursorV,CursorRGB=self.CursorRGB,CursorDarkRGB=self.CursorDarkRGB,BlinkSpeed=0.25,BlinkCount=1)
            
              #Close Chat Terminal after X minutes of inactivity
              h,m,s    = LED.GetElapsedTime(self.LastMessageReceived,time.time())
                        
              print("Seconds since last message:",s," MinutesToWaitBeforeClosing: ",self.MinutesToWaitBeforeClosing," Messages Queued:",self.MessageCount,end="\r")

              if (m >= self.MinutesToWaitBeforeClosing ):
                print("No chat activity for the past {} minutes.  Closing terminal...".format(self.MinutesToWaitBeforeClosing))
                print("")       
                print("*****************************************")       
                print("** EXITING CHAT TERMINAL - NO ACTIVITY **")
                print("*****************************************")       
                print("")       
                LED.ClearBigLED()
                LED.ClearBuffers()
                CursorH = 0
                CursorV = 0
                LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"No chat activity detected.  Did everyone fall asleep?",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalScrollSpeed)
                LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"Closing terminal",CursorH=CursorH,CursorV=CursorV,MessageRGB=(200,0,0),CursorRGB=(200,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalScrollSpeed)
                LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"............",CursorH=CursorH,CursorV=CursorV,MessageRGB=(200,0,0),CursorRGB=(200,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalScrollSpeed)
                LED.ClearBigLED()
                LED.ClearBuffers()
                self.CursorH = CursorH
                self.CursorV = CursorV

                self.ChatTerminalOn = False                        
                #await self.close()

            
            #I don't remember why I created a tas for this.  That's life I guess.
            if(self.ChatTerminalOn == False and LED.TwitchTimerOn == False):
              self.TwitchTimerTask = asyncio.create_task(self.DisplayTwitchTimer())
              


          #If the stream is not live, display a regular clock 
          if (StreamActive == False):
            await self.DisplayDigitalClock()

                 

          
          
          #Check to see if stream is live yet (only check every X minutes)
          h,m,s = LED.GetElapsedTime(self.LastStreamCheckTime,time.time())
          if (m >= self.MinutesToWaitBeforeCheckingStream):
            await self.CheckStream()
            if(StreamActive == True):
              self.LastStreamCheckTime = time.time()

            #self.__init__()
            #super().__init__(token=BOT_ACCESS_TOKEN, prefix='?', initial_channels=[BOT_CHANNEL])

          




    #---------------------------------------
    #- Event Ready                        --
    #---------------------------------------
    async def event_ready(self):
        # Notify us when everything is ready!
        # We are logged in and ready to chat and use commands...
        #UserList = self.fetch_users()
        print(f'Logged in as | {self.nick}')
          
        print(self.connected_channels.__len__())
        #Channel = self.fetch_channel(CHANNEL)
        #print(Channel)

        
        #My custom startup code runs here
        await self.my_custom_startup()
        #await self.Sleep()

        
        if(StreamActive == True):

          #skip my own channel for testing purposes
          if(CHANNEL != 'datagod'):

            #SHOW INTRO FOR MAIN CHANNEL
            LED.ShowTitleScreen(
              BigText             = CHANNEL_BIG_TEXT,
              BigTextRGB          = LED.MedPurple,
              BigTextShadowRGB    = LED.ShadowPurple,
              LittleText          = CHANNEL_LITTLE_TEXT,
              LittleTextRGB       = LED.MedRed,
              LittleTextShadowRGB = LED.ShadowRed, 
              ScrollText          = Title,
              ScrollTextRGB       = LED.MedYellow,
              ScrollSleep         = ScrollSleep, # time in seconds to control the scrolling (0.005 is fast, 0.1 is kinda slow)
              DisplayTime         = 1,           # time in seconds to wait before exiting 
              ExitEffect          = 5,           # 0=Random / 1=shrink / 2=zoom out / 3=bounce / 4=fade /5=fallingsand
              LittleTextZoom      = 2
              )

            #SHOW FOLLOWERS
            if (SHOW_FOLLOWERS == True):
              LED.ShowTitleScreen(
                BigText             = str(Followers),
                BigTextRGB          = LED.MedPurple,
                BigTextShadowRGB    = LED.ShadowPurple,
                LittleText          = 'FOLLOWS',
                LittleTextRGB       = LED.MedRed,
                LittleTextShadowRGB = LED.ShadowRed, 
                ScrollText          = '',
                ScrollTextRGB       = LED.MedYellow,
                ScrollSleep         = ScrollSleep, # time in seconds to control the scrolling (0.005 is fast, 0.1 is kinda slow)
                DisplayTime         = 1,           # time in seconds to wait before exiting 
                ExitEffect          = 0            # 0=Random / 1=shrink / 2=zoom out / 3=bounce / 4=fade /5=fallingsand
                )


            #SHOW VIEWERS
            if (SHOW_VIEWERS == True):
              LED.ShowTitleScreen(
                BigText             = str(ViewerCount),
                BigTextRGB          = LED.MedPurple,
                BigTextShadowRGB    = LED.ShadowPurple,
                LittleText          = 'Viewers',
                LittleTextRGB       = LED.MedRed,
                LittleTextShadowRGB = LED.ShadowRed, 
                ScrollText          = 'Now Playing: ' + GameName,
                ScrollTextRGB       = LED.MedYellow,
                ScrollSleep         = ScrollSleep, # time in seconds to control the scrolling (0.005 is fast, 0.1 is kinda slow)
                DisplayTime         = 1,           # time in seconds to wait before exiting 
                ExitEffect          = 1            # 0=Random / 1=shrink / 2=zoom out / 3=bounce / 4=fade /5=fallingsand
                )




            #Show this one reading chats
            LED.ShowTitleScreen(
              BigText             = 'CHAT',
              BigTextRGB          = LED.MedRed,
              BigTextShadowRGB    = LED.ShadowRed,
              LittleText          = 'TERMINAL',
              LittleTextRGB       = LED.MedBlue,
              LittleTextShadowRGB = LED.ShadowBlue, 
              ScrollText          = 'TUNING IN TO ' +  CHANNEL,
              ScrollTextRGB       = LED.MedOrange,
              ScrollSleep         = ScrollSleep, # time in seconds to control the scrolling (0.005 is fast, 0.1 is kinda slow)
              DisplayTime         = 1,           # time in seconds to wait before exiting 
              ExitEffect          = 0,           # 0=Random / 1=shrink / 2=zoom out / 3=bounce / 4=fade /5=fallingsand
              LittleTextZoom      = 1
              )

          await self.SendRandomChatGreeting()
        await self.PerformTimeBasedActions()

    

    #async def event_raw_data(self, raw_message):
    #    print(raw_message)
        

    
      
    #---------------------------------------
    # Event Message                       --
    #---------------------------------------
    async def event_message(self, message):
        
        # Messages with echo set to True are messages sent by the bot...
        # For now we just want to ignore them...
        if message.echo:
          return

        # Since we have commands and are overriding the default `event_message`
        # We must let the bot know we want to handle and invoke our commands...
        await self.handle_commands(message)


        #Exit if Chat Terminal is not on
        if (self.ChatTerminalOn == False):
          self.MesageCount = self.MessageCount -1
          return
        
        #Remove emoji from message
        message.content = LED.deEmojify(message.content)

        

        #If we have too many messages in the queue, speed up the terminal
        self.MessageCount = self.MessageCount + 1
        if(self.MessageCount > self.SpeedupMessageCount):
          print("MessagesCount:  ",self.MessageCount," is higher than ",self.SpeedupMessageCount,". Speeding up terminal.")
          print("BotTypeSpeed:   ",self.BotTypeSpeed)
          print("BotScrollSpeed: ",self.BotScrollSpeed)
          self.BotTypeSpeed   = 0
          self.BotScrollSpeed = 0
        else:
          self.BotTypeSpeed   = TerminalTypeSpeed
          self.BotScrollSpeed = TerminalScrollSpeed

        #retrieve running values from the bot object
        CursorH = self.CursorH
        CursorV = self.CursorV

        self.LastMessageReceived = time.time()

        
        ScrollText = message.content
        print(message.author.display_name + ": " + ScrollText)

        #print(message.raw_data)
        print(" ")





        try:
          LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,message.author.display_name + ":",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,0,200),CursorRGB=(0,255,0),CursorDarkRGB=(0,200,0),StartingLineFeed=1,TypeSpeed=self.BotTypeSpeed,ScrollSpeed=self.BotScrollSpeed)
          LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray, ScrollText,CursorH=CursorH,CursorV=CursorV,MessageRGB=(0,150,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,200,0),StartingLineFeed=0,TypeSpeed=self.BotTypeSpeed,ScrollSpeed=self.BotScrollSpeed)
          LED.BlinkCursor(CursorH= CursorH,CursorV=CursorV,CursorRGB=self.CursorRGB,CursorDarkRGB=self.CursorDarkRGB,BlinkSpeed=0.5,BlinkCount=2)


          #Store running values in the bot object
          self.CursorH = CursorH
          self.CursorV = CursorV
        except:
          LED.ShowScrollingBanner2('ERROR! INVALID CHARACTER',(200,0,0),ScrollSleep=0.005,v=25)

        
        self.MesageCount = self.MessageCount -1


          
          #await self.close()
      

        
   

    #---------------------------------------
    # Event Join                          --
    #---------------------------------------
    async def event_join(self,channel,user):
      #Called when a channel event is detected?
      print("")
      print ("Event:  event_join")
      print("Channel:",channel.name)
      print("User:   ",user.name)
      
      

      
    #---------------------------------------
    # Display Random Connection Message   --
    #---------------------------------------
    async def DisplayRandomConnectionMessage(self):
      #LED.ClearBigLED()
      #LED.ClearBuffers()
      x = len(ConnectionMessages)
      i = random.randint(0,x-1)
      message = ConnectionMessages[i]         
      print("Connection message:",message)
      CursorH = self.CursorH
      CursorV = self.CursorV
      LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,message,CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalScrollSpeed)
      LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray," ",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalScrollSpeed)
      LED.BlinkCursor(CursorH= CursorH,CursorV=CursorV,CursorRGB=self.CursorRGB,CursorDarkRGB=self.CursorDarkRGB,BlinkSpeed=0.5,BlinkCount=2)
      self.CursorH = CursorH
      self.CursorV = CursorV

 
    #---------------------------------------
    # Display connection message          --
    #---------------------------------------
    async def DisplayConnectingToTerminalMessage(self):
      #Show terminal connection message
      LED.ClearBigLED()
      LED.ClearBuffers()
      CursorH = 0
      CursorV = 0
      LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"INITIATING CONNECTION",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)
      LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,".....",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.5,ScrollSpeed=ScrollSleep)
      self.CursorH = CursorH
      self.CursorV = CursorV
      
    

    #---------------------------------------
    # Send random chat greeting           --
    #---------------------------------------
    async def SendRandomChatGreeting(self):
      x = len(ChatStartMessages)
      i = random.randint(0,x-1)
      message = ChatStartMessages[i]         
      print("Message:",message)
      

      #send startup message if stream is active
      if (self.SendStartupMessage == True and StreamActive == True):
        await self.Channel.send(message)
    


    #---------------------------------------
    # DisplayTerminalMessage              --
    #---------------------------------------

    async def DisplayTerminalMessage(self,message,RGB):
      if(self.ChatTerminalOn == True):
        print("DisplayTerminalMessage:",message)
        #Show terminal connection message
        #LED.ClearBigLED()
        #LED.ClearBuffers()
        CursorH = self.CursorH
        CursorV = self.CursorV 
        LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,message,CursorH=CursorH,CursorV=CursorV,MessageRGB=RGB,CursorRGB=CursorRGB,CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)
        self.CursorH = CursorH
        self.CursorV = CursorV


    #---------------------------------------
    # Turn on Timer (UPTIME)              --
    #---------------------------------------

    async def DisplayTwitchTimer(self):
      
      
      print ("Task started: DisplayTwitchTimer")
      
      #Only do this if the timer function is actually finished
      if(LED.TwitchTimerOn == False):
        LED.TwitchTimerOn = True
            
        LED.ClearBigLED()

        await LED.DisplayTwitchTimer(
          CenterHoriz = True,
          CenterVert  = False,
          h   = 0,
          v   = 1, 
          hh  = 24,
          RGB              = LED.LowGreen,
          ShadowRGB        = LED.ShadowGreen,
          ZoomFactor       = 3,
          AnimationDelay   = self.AnimationDelay,
          RunMinutes       = 1,
          StartDateTimeUTC = StreamStartedDateTime,
          HHMMSS           = StreamDurationHHMMSS,
          EventQueue       = EventQueue
          )
        print("Returned back from DisplayTwitchTimer")
      else:
        print("Timer is not yet finished")
        



    #---------------------------------------
    # Turn on RegularClock                --
    #---------------------------------------

    async def DisplayDigitalClock(self):
      print ("Starting: DisplayDigitalClock")

      
      #Skip the buggy clockstyle 2
      r = random.randint(1,2)
      if (r == 2):
        r = 3


      LED.DisplayDigitalClock(
        ClockStyle = r,
        CenterHoriz = True,
        v   = 1, 
        hh  = 24,
        RGB = LED.LowGreen,
        ShadowRGB        = LED.ShadowGreen,
        ZoomFactor       = 3,
        AnimationDelay   = self.AnimationDelay,
        RunMinutes       = 1,
        EventQueue       = EventQueue
        )
      print("Clock function completed")





    #---------------------------------------
    # WEBHOOK EventQueue                  --
    #---------------------------------------

    async def ReadEventQueue(self):
      global EventQueue
      QueueCount = EventQueue.qsize()
      #print("QueueCount: ",QueueCount)

      for i in range (0,QueueCount):
        try:      
          #Read the Queue then mark it as complete

          print("")
          print("")
          print("==ReadEventQueue=======================")

          Message = EventQueue.get_nowait()
          EventQueue.task_done()
          #print("Message ",str(QueueCount),":",Message)

          print("Parsing Event Message")
          await self.ProcessEvent(Message)
          
          print("=======================================")
          print("")

        except Exception as ErrorMessage:
          TraceMessage = traceback.format_exc()
          AdditionalInfo = "Reading an object from the EventQueue" 
          LED.ErrorHandler(ErrorMessage,TraceMessage,AdditionalInfo)      
 
      
      
      

    async def ProcessEvent(self,Message):
      #we need to determine the type of event, source of webhook etc
   
     
      #Patreon Events
      if Message['data']['attributes']['patron_status']:
        print ("Data type: PATREON")

        try:
          PledgeStart = Message['data']['attributes']['pledge_relationship_start']
          FullName    = Message['data']['attributes']['full_name']
          City        = Message['included'][0]['attributes']['city']
          State       = Message['included'][0]['attributes']['state']
          Country     = Message['included'][0]['attributes']['country']


          NameList  = FullName.split()
          FirstName = NameList[0]
          LastName  = NameList[-1]

          if(Country == 'CA'):
            Country = 'Canada'

          if(Country == 'US'):
            Country = 'U.S.A.'

          print("")
          print("--Patron Info--")
          print("PledgeStart:",PledgeStart)
          print("FullName:   ",FullName)
          print("City:       ",City)
          print("State:      ",State)
          print("Country:    ",Country)
          print("---------------")
          
          
          LED.ShowTitleScreen(
            BigText             = "NEW",
            BigTextRGB          = LED.MedGreen,
            BigTextShadowRGB    = LED.ShadowGreen,
            BigText2            = 'PLEDGE',
            BigText2RGB         = LED.MedGreen,
            BigText2ShadowRGB   = LED.ShadowGreen,
            LittleText          = 'PATREON',
            LittleTextRGB       = LED.MedRed,
            LittleTextShadowRGB = LED.ShadowRed, 
            ScrollText          = "THANK YOU " + FirstName + " FROM " + State + ", " + Country,
            ScrollTextRGB       = LED.MedYellow,
            ScrollSleep         = ScrollSleep, # time in seconds to control the scrolling (0.005 is fast, 0.1 is kinda slow)
            DisplayTime         = 1,           # time in seconds to wait before exiting 
            ExitEffect          = 0           # 0=Random / 1=shrink / 2=zoom out / 3=bounce / 4=fade /5=fallingsand
            )

          LED.ClearBuffers()

        except Exception as ErrorMessage:
          TraceMessage = traceback.format_exc()
          AdditionalInfo = "Decoding JSON for WebHook" 
          LED.ErrorHandler(ErrorMessage,TraceMessage,AdditionalInfo)



      else:
        print("Unkown data type")
        




  #---------------------------------------
  # B O T   C O M M A N D S             --
  #---------------------------------------
  #the bot will respond to these commands typed in the chat e.g. ?hello


    #----------------------------------------
    # Hello                                --
    #----------------------------------------

    @commands.command()
    async def hello(self, ctx: commands.Context):
        # Here we have a command hello, we can invoke our command with our prefix and command name
        # e.g ?hello
        # We can also give our commands aliases (different names) to invoke with.

        # Send a hello back!
        # Sending a reply back to the channel is easy... Below is an example.
        await ctx.send(f'Greetings! {ctx.author.name}!')



    #----------------------------------------
    # commands                             --
    #----------------------------------------

    @commands.command()
    async def clock(self, ctx: commands.Context):
        await ctx.send('Available commands: ?hello ?viewers ?follows ?subs ?uptime ?chat ?profile ?robot ?invaders ?outbreak ?defender ?tron ?starrynight ?patreon ?patrons')


    #----------------------------------------
    # Viewers                              --
    #----------------------------------------
    @commands.command()
    async def viewers(self, ctx: commands.Context):
      #SHOW VIEWERS
      
      if(SHOW_VIEWERS == True):
        GetTwitchCounts()

        if(SHOW_CHATBOT_MESSAGES == True):
          message = "There are {} viewers watching this great broadcast. Thanks for asking.".format(ViewerCount)
          await self.Channel.send(message)

        LED.ShowTitleScreen(
          BigText             = str(ViewerCount),
          BigTextRGB          = LED.MedPurple,
          BigTextShadowRGB    = LED.ShadowPurple,
          LittleText          = 'Viewers',
          LittleTextRGB       = LED.MedRed,
          LittleTextShadowRGB = LED.ShadowRed, 
          ScrollText          = 'Now Playing: ' + GameName,
          ScrollTextRGB       = LED.MedYellow,
          ScrollSleep         = ScrollSleep, # time in seconds to control the scrolling (0.005 is fast, 0.1 is kinda slow)
          DisplayTime         = 1,           # time in seconds to wait before exiting 
          ExitEffect          = -1           # 0=Random / 1=shrink / 2=zoom out / 3=bounce / 4=fade /5=fallingsand
          )

        self.CursorH = 0
      

    #----------------------------------------
    # Follows / Followers                  --
    #----------------------------------------

    @commands.command()
    async def follows(self, ctx: commands.Context):
      #SHOW FOLLOWS
      GetTwitchCounts()

      print("SHOW_CHATBOT_MESSAGES:",SHOW_CHATBOT_MESSAGES)
      if(SHOW_CHATBOT_MESSAGES == True):
        message = "{} viewers follow this channel. Thanks for asking.".format(Followers)
        await self.Channel.send(message)

      LED.ShowTitleScreen(
        BigText             = str(Followers),
        BigTextRGB          = LED.MedPurple,
        BigTextShadowRGB    = LED.ShadowPurple,
        LittleText          = 'Follows',
        LittleTextRGB       = LED.MedRed,
        LittleTextShadowRGB = LED.ShadowRed, 
        ScrollText          = '',
        ScrollTextRGB       = LED.MedYellow,
        ScrollSleep         = ScrollSleep, # time in seconds to control the scrolling (0.005 is fast, 0.1 is kinda slow)
        DisplayTime         = 1,           # time in seconds to wait before exiting 
        ExitEffect          = -1           # 0=Random / 1=shrink / 2=zoom out / 3=bounce / 4=fade /5=fallingsand
        )

      self.CursorH = 0



    @commands.command()
    async def followers(self, ctx: commands.Context):
      
      #SHOW FOLLOWERS
      print("SHOW_FOLLOWERS:",SHOW_FOLLOWERS)
      if(SHOW_FOLLOWERS == True):
        GetTwitchCounts()

        if(SHOW_CHATBOT_MESSAGES == True):
          message = "{} viewers follow this channel. Gotta get those numbers up!".format(Followers)
          await self.Channel.send(message)

        LED.ShowTitleScreen(
          BigText             = str(Followers),
          BigTextRGB          = LED.MedPurple,
          BigTextShadowRGB    = LED.ShadowPurple,
          LittleText          = 'Follows',
          LittleTextRGB       = LED.MedRed,
          LittleTextShadowRGB = LED.ShadowRed, 
          ScrollText          = '',
          ScrollTextRGB       = LED.MedYellow,
          ScrollSleep         = ScrollSleep, # time in seconds to control the scrolling (0.005 is fast, 0.1 is kinda slow)
          DisplayTime         = 1,           # time in seconds to wait before exiting 
          ExitEffect          = -1           # 0=Random / 1=shrink / 2=zoom out / 3=bounce / 4=fade /5=fallingsand
          )

        self.CursorH = 0



      else:
        if(SHOW_CHATBOT_MESSAGES == True):
          message = "{} has decided to not show followers.".format(CHANNEL)
          await self.Channel.send(message)



    #----------------------------------------
    # Subs                                 --
    #----------------------------------------


    @commands.command()
    async def subs(self, ctx: commands.Context):
      #SHOW SUBS
      if(SHOW_SUBS == True):
        GetTwitchCounts()
        if(SHOW_CHATBOT_MESSAGES == True):
          message = "This channel has {} subscribers. We can always use more.".format(Subs)
          await self.Channel.send(message)

        LED.ShowTitleScreen(
          BigText             = str(Subs),
          BigTextRGB          = LED.MedPurple,
          BigTextShadowRGB    = LED.ShadowPurple,
          LittleText          = 'Subscribers',
          LittleTextRGB       = LED.MedRed,
          LittleTextShadowRGB = LED.ShadowRed, 
          ScrollText          = '',
          ScrollTextRGB       = LED.MedYellow,
          ScrollSleep         = ScrollSleep, # time in seconds to control the scrolling (0.005 is fast, 0.1 is kinda slow)
          DisplayTime         = 5,           # time in seconds to wait before exiting 
          ExitEffect          = -1           # 0=Random / 1=shrink / 2=zoom out / 3=bounce / 4=fade /5=fallingsand
          )
        self.CursorH = 0

      else:
        if(SHOW_CHATBOT_MESSAGES == True):
          message = "Well, you are viewing.  I am viewing.  {} is viewing.  That's at least three.  The rest is a mystery to me.".format(CHANNEL)
          await self.Channel.send(message)



    #----------------------------------------
    # Uptime                               --
    #----------------------------------------
      
    @commands.command()
    async def uptime(self, ctx: commands.Context):
      #SHOW UPTIME
      if(SHOW_CHATBOT_MESSAGES == True):
        message = "{} has been streaming for {} HHMMSS".format(CHANNEL,StreamDurationHHMMSS)
        await self.Channel.send(message)

      self.ChatTerminalOn = False
      self.TwitchTimerTask = asyncio.create_task(self.DisplayTwitchTimer())


    #----------------------------------------
    # CHAT                                 --
    #----------------------------------------

    @commands.command()
    async def chat(self, ctx: commands.Context):
      #SHOW CHAT
      self.ChatTerminalOn = True
      LED.TwitchTimerOn   = False
      if(SHOW_CHATBOT_MESSAGES == True):
        message = "The chat will now be displayed on the LEDarcade clock thingy.".format(CHANNEL,StreamDurationHHMMSS)
        await self.Channel.send(message)
      

    #----------------------------------------
    # Profile                              --
    #----------------------------------------
      
    @commands.command()
    async def profile(self, ctx: commands.Context):
      #SHOW PROFILE
      if(SHOW_CHATBOT_MESSAGES == True):
        message = "Now displaying the profile pic for this channel."
        await self.Channel.send(message)

      LED.GetImageFromURL(PROFILE_IMAGE_URL,"CurrentProfile.png")
      LED.ZoomImage(ImageName="CurrentProfile.png",ZoomStart=1,ZoomStop=256,ZoomSleep=0.025,Step=4)
      LED.ZoomImage(ImageName="CurrentProfile.png",ZoomStart=256,ZoomStop=64,ZoomSleep=0.025,Step=4)
      time.sleep(3)
      LED.ClearBigLED()


    #----------------------------------------
    # VIEWS                                --
    #----------------------------------------


    @commands.command()
    async def views(self, ctx: commands.Context):
      #SHOW VIEWS
      if(SHOW_VIEWS == True):
        GetTwitchCounts()
        if(SHOW_CHATBOT_MESSAGES == True):
          message = "This channel has been viewed {} times.". format(VIEW_COUNT)
          await self.Channel.send(message)

        LED.ShowTitleScreen(
          BigText             = str(VIEW_COUNT),
          BigTextRGB          = LED.MedRed,
          BigTextShadowRGB    = LED.ShadowRed,
          LittleText          = 'Views',
          LittleTextRGB       = LED.MedPurple,
          LittleTextShadowRGB = LED.ShadowPurple, 
          ScrollText          = '',
          ScrollTextRGB       = LED.MedYellow,
          ScrollSleep         = ScrollSleep, # time in seconds to control the scrolling (0.005 is fast, 0.1 is kinda slow)
          DisplayTime         = 5,           # time in seconds to wait before exiting 
          ExitEffect          = -1           # 0=Random / 1=shrink / 2=zoom out / 3=bounce / 4=fade /5=fallingsand
          )
        self.CursorH = 0

      else:
        if(SHOW_CHATBOT_MESSAGES == True):
          message = "Well, I viewed once or twice.  {} is viewing right now. That has to count for something.".format(CHANNEL)
          await self.Channel.send(message)





    #----------------------------------------
    # ROBOT                                --
    #----------------------------------------


    @commands.command()
    async def robot(self, ctx: commands.Context):
      #SHOW ROBOT
      if(SHOW_CHATBOT_MESSAGES == True):
        message = "Here is a big red robot for your amusement"
        await self.Channel.send(message)

      LED.MoveAnimatedSpriteAcrossScreenStepsPerFrame(
        LED.BigRezonator2,
        Position      = 'bottom',
        direction     = "right",
        StepsPerFrame = 2,
        ZoomFactor    = 1,
        sleep         = 0
        )

      self.CursorH = 0



    #----------------------------------------
    # DOT INVADERS                         --
    #----------------------------------------


    @commands.command()
    async def invaders(self, ctx: commands.Context):
      #Play game DotInvaders
      if(SHOW_CHATBOT_MESSAGES == True):
        message = "Lets play a game of DotInvaders"
        await self.Channel.send(message)
      DI.LaunchDotInvaders(GameMaxMinutes = 2,ShowIntro=False) 
      LED.ClearBigLED()
      LED.ClearBuffers()
      CursorH = 0
      CursorV = 0



    #----------------------------------------
    # OUTBREAK                             --
    #----------------------------------------

    @commands.command()
    async def outbreak(self, ctx: commands.Context):
      #Play game Outbreak
      if(SHOW_CHATBOT_MESSAGES == True):
        message = "Looks like you want to play some Outbreak..."
        await self.Channel.send(message)
      OB.LaunchOutbreak(GameMaxMinutes = 2,ShowIntro = False)
      LED.ClearBigLED()
      LED.ClearBuffers()
      CursorH = 0
      CursorV = 0

    #----------------------------------------
    # DEFENDER                             --
    #----------------------------------------


    @commands.command()
    async def defender(self, ctx: commands.Context):
      #Play game Defender
      if(SHOW_CHATBOT_MESSAGES == True):
        message = "Time to shoot some mutants"
        await self.Channel.send(message)
      DE.LaunchDefender(GameMaxMinutes = 2,ShowIntro=False)
      LED.ClearBigLED()
      LED.ClearBuffers()
      CursorH = 0
      CursorV = 0


    #----------------------------------------
    # TRON                                 --
    #----------------------------------------


    @commands.command()
    async def tron(self, ctx: commands.Context):
      #Play game Tron
      if(SHOW_CHATBOT_MESSAGES == True):
        message = "Time for some jetbike races"
        await self.Channel.send(message)
      TR.LaunchTron(GameMaxMinutes = 2,ShowIntro=False)
      LED.ClearBigLED()
      LED.ClearBuffers()
      CursorH = 0
      CursorV = 0


    #----------------------------------------
    # STARRY NIGHT CLOCK                   --
    #----------------------------------------

    @commands.command()
    async def starrynight(self, ctx: commands.Context):
      if(SHOW_CHATBOT_MESSAGES == True):
        message = "Enjoy the peaceful starry sky while staring at a clock"
        await self.Channel.send(message)
      LED.DisplayDigitalClock(ClockStyle=3,CenterHoriz=True,v=1, hh=24, ZoomFactor = 1, AnimationDelay=30, RunMinutes = 1, EventQueue=EventQueue )
      LED.ClearBigLED()
      LED.ClearBuffers()
      CursorH = 0
      CursorV = 0



    #----------------------------------------
    # DISPLAY PATREON                      --
    #----------------------------------------

    @commands.command()
    async def patreon(self, ctx: commands.Context):
      if(SHOW_CHATBOT_MESSAGES == True):
        message = "Now displaying the list of patrons"
        await self.Channel.send(message)

      DisplayPatreon()
      LED.RunningMan2Sprite.ScrollAcrossScreen(20,0,'right', ScrollSleep )
      LED.RunningMan2Sprite.HorizontalFlip()      
      LED.RunningMan2Sprite.ScrollAcrossScreen(20,15,'left', ScrollSleep )
      LED.RunningMan2Sprite.HorizontalFlip()

    @commands.command()
    async def patrons(self, ctx: commands.Context):
      if(SHOW_CHATBOT_MESSAGES == True):
        message = "Now displaying the list of patrons"
        await self.Channel.send(message)
      
      DisplayPatreon()
      LED.MoveAnimatedSpriteAcrossScreenStepsPerFrame(
        LED.PacManRightSprite,
        Position      = 'top',
        Vadjust       = 0 ,
        direction     = "right",
        StepsPerFrame = 3,
        ZoomFactor    = 3,
        sleep         = 0.02 
        )


      LED.MoveAnimatedSpriteAcrossScreenStepsPerFrame(
        LED.PacManLeftSprite,
        Position      = 'middle',
        Vadjust       = 0,
        direction     = "left",
        StepsPerFrame = 3,
        ZoomFactor    = 3,
        sleep         = 0.01
        )

      LED.MoveAnimatedSpriteAcrossScreenStepsPerFrame(
        LED.PacManRightSprite,
        Position      = 'bottom',
        Vadjust       = 0 ,
        direction     = "right",
        StepsPerFrame = 3,
        ZoomFactor    = 3,
        sleep         = 0.0 
        )


LED.ClearBigLED()
LED.ClearBuffers()




#------------------------------------------------
# Bot functions
#------------------------------------------------








# bot.run() is blocking and will stop execution of any below code here until stopped or closed.
#twitch = Twitch('nxzwcicyp9ytl6m7b94ek7e9x79cw0', '2p433nc5plbcqnzwy9ivt56fo0tpww')




#curl -X GET 'https://api.twitch.tv/helix/channels?broadcaster_id=141981764' \
#-H 'Authorization: Bearer 2gbdx6oar67tqtcmt49t3wpcgycthx' \
#-H 'Client-Id: wbmytr93xzw8zbg0p1izqyzzc5mbiz'



def IRCStuff():
  connection_data = ("irc.chat.twitch.tv",6667)
  token      = 'oauth:' + MY_ACCESS_TOKEN
  user       = 'dataBot'
  channel    = 'retrowithmarco'
  readbuffer = ''

  server = socket.socket()
  server.connect(connection_data)
  server.send(bytes('PASS ' + token   + '\r\n', 'utf-8'))
  server.send(bytes('NICK ' + user    + '\r\n', 'utf-8'))
  server.send(bytes('JOIN ' + channel + '\r\n', 'utf-8'))
 
  print (server)

  timeout_in_seconds = 10

  pprint.pprint(server)  
  while True:
    print('Waiting')
    #ready = select.select([server], [], [], timeout_in_seconds)
    
    results = server.recv(512)
    print(results)
    
    
    #if ready[0]:
    #  print(ready)
    #  print('We are ready to recieve')
    #  results = server.recv(1024)
    #  print(results)
      
    if results.find(str.encode("PING")):
      print('Ping detected.  Responding with PONG')
      server.send(bytes("PONG tmi.twitch.tv\r\n", 'utf-8'))


    
    



#------------------------------------------------------------------------------
# File Functions                                                             --
#------------------------------------------------------------------------------








def GetTwitchCounts():
    
    #User / Channel Info
    global GameName        
    global Title           

    #Stream Info
    global StreamStartedAt 
    global StreamStartedTime
    global StreamStartedDateTime
    global StreamDurationHHMMSS
    global StreamType      
    global ViewerCount     
    global StreamActive 

    #Follower Info
    global Followers      
    global Subs

    
    #----------------------------------------
    # GET USER INFO - ACTIVE STREAM
    #----------------------------------------
    print ("Getting USER info")
    API_ENDPOINT = "https://api.twitch.tv/helix/streams?user_login=" + CHANNEL
    head = {
    'Client-ID': CLIENT_ID,
    'Authorization': 'Bearer ' +  ACCESS_TOKEN
    }
    print ("URL: ",API_ENDPOINT, 'data:',head)
    r = requests.get(url = API_ENDPOINT, headers = head)
    results = r.json()
    pprint.pprint(results)
    #print(" ")

    if results['data']:
      print("Data found.  Processing...")

      try:
        StreamStartedAt = results['data'][0]['started_at']
        StreamType      = results['data'][0]['type']
        ViewerCount     = results['data'][0]['viewer_count']
        StreamActive    = True

      except Exception as ErrorMessage:
        TraceMessage = traceback.format_exc()
        AdditionalInfo = "Getting USER info from API call" 
        LED.ErrorHandler(ErrorMessage,TraceMessage,AdditionalInfo)
    else:
      print("Stream NOT active")
      StreamActive = False  


    #----------------------------------------
    # Follower Count
    #----------------------------------------
    print("Get FOLLOWER information")
    API_ENDPOINT = "https://api.twitch.tv/helix/users/follows?to_id=" + USER_ID
    head = {
    'Client-ID': CLIENT_ID,
    'Authorization': 'Bearer ' +  ACCESS_TOKEN
    }

    #print ("URL: ",API_ENDPOINT, 'data:',head)
    r = requests.get(url = API_ENDPOINT, headers = head)
    #pp.pprint(r.content)

    try:
      results = r.json()
      Followers = results['total']
      #pprint.pprint(results)
      #print("")

    except Exception as ErrorMessage:
      TraceMessage = traceback.format_exc()
      AdditionalInfo = "Getting FOLLOWER info from API call" 
      LED.ErrorHandler(ErrorMessage,TraceMessage,AdditionalInfo)


    #----------------------------------------
    # Subscriber Count
    #----------------------------------------
    print("Get SUBSCRIBER information")
    API_ENDPOINT = "https://api.twitch.tv/helix/subscriptions?broadcaster_id=" + BROADCASTER_ID
    head = {
    'Client-ID': CLIENT_ID,
    'Authorization': 'Bearer ' +  ACCESS_TOKEN
    }

    #print ("URL: ",API_ENDPOINT, 'data:',head)
    r = requests.get(url = API_ENDPOINT, headers = head)

    try:
      results = r.json()
      Subs = results['total']
      pprint.pprint(results)
      #print("")

    except Exception as ErrorMessage:
      TraceMessage = traceback.format_exc()
      AdditionalInfo = "Getting SUBSCRIBER info from API call - This usually means your account does not have permission, or you are not an affiliate/partner." 
      pprint.pprint(r.content)
      LED.ErrorHandler(ErrorMessage,TraceMessage,AdditionalInfo)
      








def GetBasicTwitchInfo():
    
    #User / Channel Info
    global GameName        
    global Title           
    global PROFILE_IMAGE_URL
    global VIEW_COUNT
    

    #Stream Info
    global StreamStartedAt 
    global StreamStartedTime
    global StreamStartedDateTime
    global StreamDurationHHMMSS
    global StreamType      
    global ViewerCount     
    global StreamActive 

    #Follower Info
    global Followers      

    #HypeTrain info
    global HypeTrainStartTime  
    global HypeTrainExpireTime 
    global HypeTrainGoal       
    global HypeTrainLevel      
    global HypeTrainTotal      

   

    print ("--GetBasicTwitchInfo--")

    #----------------------------------------
    # GET CHANNEL INFO
    #----------------------------------------
    print("Get CHANNEL info")
    API_ENDPOINT = "https://api.twitch.tv/helix/users?login=" + CHANNEL
    head = {
    'Client-ID': CLIENT_ID,
    'Authorization': 'Bearer ' +  ACCESS_TOKEN
    }

    #print ("URL: ",API_ENDPOINT, 'data:',head)
    r = requests.get(url = API_ENDPOINT, headers = head)
    results = r.json()
    #pprint.pprint(results)
    #print(" ")

    if results['data']:
      print("Data found.  Processing...")

      try:
        USER_ID           = results['data'][0]['id']
        BROADCASTER_ID    = USER_ID
        PROFILE_IMAGE_URL = results['data'][0]['profile_image_url']
        VIEW_COUNT        = results['data'][0]['view_count']

      except Exception as ErrorMessage:
        TraceMessage = traceback.format_exc()
        AdditionalInfo = "Getting CHANNEL info from API call" 
        LED.ErrorHandler(ErrorMessage,TraceMessage,AdditionalInfo)
     


    #----------------------------------------
    # GET BROADCASTER INFO
    #----------------------------------------
    print("Get BROADCASTER info")
    API_ENDPOINT = "https://api.twitch.tv/helix/channels?broadcaster_id=" + BROADCASTER_ID
    head = {
    'Client-ID': CLIENT_ID,
    'Authorization': 'Bearer ' +  ACCESS_TOKEN
    }

    #print ("URL: ",API_ENDPOINT, 'data:',head)
    r = requests.get(url = API_ENDPOINT, headers = head)
    results = r.json()
    #pprint.pprint(results)
    #print(" ")

    if results['data']:
      print("Data found.  Processing...")

      try:
        GameName        = results['data'][0]['game_name']
        Title           = results['data'][0]['title']

      except Exception as ErrorMessage:
        TraceMessage = traceback.format_exc()
        AdditionalInfo = "Getting CHANNEL info from API call" 
        LED.ErrorHandler(ErrorMessage,TraceMessage,AdditionalInfo)
     
    
    
    GetTwitchCounts()
    

    #----------------------------------------
    #Hype Train
    #----------------------------------------
    print("Get HYPETRAIN info")
    API_ENDPOINT = "https://api.twitch.tv/helix/hypetrain/events?broadcaster_id=" + BROADCASTER_ID
    head = {
    'Client-ID': CLIENT_ID,
    'Authorization': 'Bearer ' +  ACCESS_TOKEN
    }

    #print ("URL: ",API_ENDPOINT, 'data:',head)
    r = requests.get(url = API_ENDPOINT, headers = head)
    results = r.json()
    pprint.pprint(results)


    if results['data']:
      print("Hypetrain data found.  Processing...")

      try:
        HypeTrainStartTime  = results['data'][0]['event_timestamp']
        HypeTrainExpireTime = results['data'][0]['event_data']['expires_at']
        HypeTrainGoal  = results['data'][0]['event_data']['goal']
        HypeTrainLevel = results['data'][0]['event_data']['level']
        HypeTrainTotal = results['data'][0]['event_data']['total']

        #convert to non annoying format
        HypeTrainStartTime  = ConvertDate(HypeTrainStartTime)
        HypeTrainExpireTime = ConvertDate(HypeTrainExpireTime)


      except Exception as ErrorMessage:
        TraceMessage = traceback.format_exc()
        AdditionalInfo = "Getting HypeTrain info from API call" 
        LED.ErrorHandler(ErrorMessage,TraceMessage,AdditionalInfo)

    else:
      print("HypeTrain NOT active")
      HypeTrainActive = False  





    if(StreamActive):
      print("** STREAM ACTIVE **")
      #twitch dates are special format, and in UTC
      #Convert to datetime (timezone naive)
      StreamStartedDateTime = datetime.strptime(StreamStartedAt, '%Y-%m-%dT%H:%M:%SZ')
      
      hh,mm,ss, StreamDurationHHMMSS = LED.CalculateElapsedTime(StreamStartedDateTime)
      print("Stream Duration:",StreamDurationHHMMSS)
    else:
      print("** STREAM NOT ACTIVE **")



    print ("---------------------------------------")
    print("Title:",Title)
    print("GameName:",GameName)

    if(StreamActive):
      print("StreamStartedAt: ",StreamStartedAt)
      print("StreamDurationHHMMSS:",StreamDurationHHMMSS)
      print("StreamType:",StreamType)
      print("ViewerCount:",ViewerCount)

    print("Followers:",Followers)
    print("HypeTrainStartTime:",HypeTrainStartTime)
    print("HypeTrainExpireTime:",HypeTrainExpireTime)
    print("HypeTrainGoal:",HypeTrainGoal)
    print("HypeTrainLevel:",HypeTrainLevel)
    print("HypeTrainTotal:",HypeTrainTotal)
    print ("---------------------------------------")



    
    






def ConvertDate(TheDate):
  #take a funky twitch 3339 style date and convert it to a python datetime UTC
  StringDate = TheDate
  NewDate = StringDate[0:10]+ ' ' + StringDate[11:19]
  NewDate = datetime.strptime(NewDate, '%Y-%m-%d %H:%M:%S')
  NewDate.replace(tzinfo=timezone.utc)


  return NewDate







def LoadConfigFiles():
  
  global ACCESS_TOKEN
  global REFRESH_TOKEN
  global CLIENT_ID
  global CHANNEL
  global CHANNEL_BIG_TEXT
  global CHANNEL_LITTLE_TEXT
  
  global USER_ID
  global BROADCASTER_ID
  global BOT_CHANNEL
  global BOT_ACCESS_TOKEN
  global BOT_REFRESH_TOKEN
  global BOT_CLIENT_ID

  global PATREON_CLIENT_ID
  global PATREON_CLIENT_SECRET
  global PATREON_CREATOR_ACCESS_TOKEN

  global SHOW_VIEWERS
  global SHOW_FOLLOWERS
  global SHOW_SUBS
  global SHOW_VIEWS
  global SHOW_CHATBOT_MESSAGES
  

  
  
  print ("--Load Twitch Keys--")
  print("KeyConfig.ini")
  if (os.path.exists(KeyConfigFileName)):

    print ("Config file (",KeyConfigFileName,"): found")
    KeyFile = SafeConfigParser()
    KeyFile.read(KeyConfigFileName)

    #Get tokens
    CHANNEL             = KeyFile.get("KEYS","CHANNEL")
    CHANNEL_BIG_TEXT    = KeyFile.get("KEYS","CHANNEL_BIG_TEXT")
    CHANNEL_LITTLE_TEXT = KeyFile.get("KEYS","CHANNEL_LITTLE_TEXT")

    USER_ID        = KeyFile.get("KEYS","USER_ID")        #Same as Broadcaster_ID
    BROADCASTER_ID = KeyFile.get("KEYS","BROADCASTER_ID") #Same as UserID
    ACCESS_TOKEN   = KeyFile.get("KEYS","ACCESS_TOKEN")  
    REFRESH_TOKEN  = KeyFile.get("KEYS","REFRESH_TOKEN")
    CLIENT_ID      = KeyFile.get("KEYS","CLIENT_ID")      #ID of the twitch connected app (this program)

    #Patreon
    PATREON_CLIENT_ID            = KeyFile.get("KEYS","PATREON_CLIENT_ID")      
    PATREON_CLIENT_SECRET        = KeyFile.get("KEYS","PATREON_CLIENT_SECRET")      
    PATREON_CREATOR_ACCESS_TOKEN = KeyFile.get("KEYS","PATREON_CREATOR_ACCESS_TOKEN")      


    #Bot specific connection info
    #in case we want a bot to connect separately, or to other channels
    BOT_CHANNEL = CHANNEL
    BOT_ACCESS_TOKEN   = KeyFile.get("KEYS","BOT_ACCESS_TOKEN")  
    BOT_REFRESH_TOKEN  = KeyFile.get("KEYS","BOT_REFRESH_TOKEN")
    BOT_CLIENT_ID      = KeyFile.get("KEYS","BOT_CLIENT_ID")     


    print("CHANNEL:             ",CHANNEL)   
    print("CHANNEL_BIG_TEXT:    ",CHANNEL_BIG_TEXT)   
    print("CHANNEL_LITTLE_TEXT: ",CHANNEL_LITTLE_TEXT)   
    print("USER_ID:             ",USER_ID)
    print("BROADCASTER_ID:      ",BROADCASTER_ID)
    print("CLIENT_ID:           ",CLIENT_ID)
    print("")
    #print("PATREON_CLIENT_ID:            ",PATREON_CLIENT_ID)
    #print("PATREON_CLIENT_SECRET:        ",PATREON_CLIENT_SECRET)
    #print("PATREON_CREATOR_ACCESS_TOKEN: ",PATREON_CREATOR_ACCESS_TOKEN)
    print("")
    
    #print("ACCESS_TOKEN:   ",ACCESS_TOKEN)
    #print("REFRESH_TOKEN:  ",REFRESH_TOKEN)

    print("BOT_CHANNEL:         ",BOT_CHANNEL)   
    print("BOT_CLIENT_ID:       ",BOT_CLIENT_ID)
    #print("ACCESS_TOKEN:   ",ACCESS_TOKEN)
    #print("REFRESH_TOKEN:  ",REFRESH_TOKEN)

    print ("--------------------")
    print (" ")

  else:
    #To be finished later
    print ("ERROR: Could not locate Key file (",KeyConfigFileName,"). Create a file and make sure to pupulate it with your own keys.")



  print ("--Load Personal Configurations--")
  print("MyConfig.ini")

  if (os.path.exists(MyConfigFileName)):

    print ("Config file (",MyConfigFileName,"): found")
    MyConfigFile = SafeConfigParser()
    MyConfigFile.read(MyConfigFileName)

    #Get settings
    SHOW_VIEWERS   = MyConfigFile.get("SHOW","SHOW_VIEWERS")
    SHOW_FOLLOWERS = MyConfigFile.get("SHOW","SHOW_FOLLOWERS")
    SHOW_SUBS      = MyConfigFile.get("SHOW","SHOW_SUBS")
   
    SHOW_CHATBOT_MESSAGES = MyConfigFile.get("SHOW","SHOW_CHATBOT_MESSAGES")


    #This one was created prior to initial release so we try to add the missing config items
    try:
      SHOW_VIEWS     = MyConfigFile.get("SHOW","SHOW_VIEWS")
    except:
      MyConfigFile = open(MyConfigFileName,'a+')
      print("Adding entry to config file for SHOW_VIEWS")
      MyConfigFile.write("  SHOW_VIEWS     = True\n")


    #The config file reads in True as 'True' (string)
    #we need to convert to True/False boolean
    if(SHOW_VIEWERS == 'True'):
      SHOW_VIEWERS = True
    else:
      SHOW_VIEWERS = False

    if(SHOW_FOLLOWERS == 'True'):
      SHOW_FOLLOWERS = True
    else:
      SHOW_FOLLOWERS = False

    if(SHOW_SUBS == 'True'):
      SHOW_SUBS = True
    else:
      SHOW_SUBS = False 


    if(SHOW_VIEWS == 'True'):
      SHOW_VIEWS = True
    else:
      SHOW_VIEWS = False 

    if(SHOW_CHATBOT_MESSAGES == 'True'):
      SHOW_CHATBOT_MESSAGES = True
    else:
      SHOW_CHATBOT_MESSAGES = False
    



    print("SHOW_VIEWERS:          ",SHOW_VIEWERS)   
    print("SHOW_FOLLOWERS:        ",SHOW_FOLLOWERS)   
    print("SHOW_SUBS:             ",SHOW_SUBS)   
    print("SHOW_VIEWS:            ",SHOW_VIEWS)   
    print("SHOW_CHATBOT_MESSAGES: ",SHOW_CHATBOT_MESSAGES)   


  else:
    print ("ERROR: Could not locate config file (",MyConfigFileName,").")
  
  print ("--------------------")
  print (" ")
  






def CheckConfigFiles():
  #This function will create the config files if they do not exist and populate them 
  #with examples

  #KeyConfig.ini


  if (os.path.exists(MyConfigFileName)):
    print("File found:",MyConfigFileName)

  else:

    try:
      print("Warning! File not found:",MyConfigFileName)
      print("We will attempt to create a file with default values")
    
      #CREATE A CONFIG FILE
      MyConfigFile = open(MyConfigFileName,'a+')
      MyConfigFile.write("[SHOW]\n")
      MyConfigFile.write("  SHOW_VIEWERS   = True\n")
      MyConfigFile.write("  SHOW_FOLLOWERS = True\n")
      MyConfigFile.write("  SHOW_SUBS      = True\n")
      MyConfigFile.write("  SHOW_VIEWS     = True\n")
      MyConfigFile.write("  SHOW_CHATBOT_MESSAGES = True\n")

    except Exception as ErrorMessage:
      TraceMessage = traceback.format_exc()
      AdditionalInfo = "Creating the {}file".format(MyConfigFileName)
      LED.ErrorHandler(ErrorMessage,TraceMessage,AdditionalInfo)



  if (os.path.exists(KeyConfigFileName)):
    print("File found:",KeyConfigFileName)
  else:
    try:
      print("Warning! File not found:",KeyConfigFileName)
      print("We will attempt to create a file with default values")
  
      #CREATE A CONFIG FILE
      KeyConfigFile = open(KeyConfigFileName,'a+')
      KeyConfigFile.write("[KEYS]\n")
      KeyConfigFile.write("  CHANNEL             = YourChannelName\n")
      KeyConfigFile.write("  CHANNEL_BIG_TEXT    = LED\n")
      KeyConfigFile.write("  CHANNEL_LITTLE_TEXT = ARCADE\n")
      KeyConfigFile.write("\n")
      KeyConfigFile.write("  USER_ID        = 12345\n")
      KeyConfigFile.write("  BROADCASTER_ID = 12345 (same as UserID)\n")
      KeyConfigFile.write("  ACCESS_TOKEN   = abcdefg\n")
      KeyConfigFile.write("  REFRESH_TOKEN  = hijklmn\n")
      KeyConfigFile.write("  CLIENT_ID      = gp762nuuoqcoxypju8c569th9wz7q5\n")
      KeyConfigFile.write("\n")
      KeyConfigFile.write("  BOT_ACCESS_TOKEN  = abcde\n")
      KeyConfigFile.write("  BOT_REFRESH_TOKEN = fghij\n")
      KeyConfigFile.write("  BOT_CLIENT_ID     = gp762nuuoqcoxypju8c569th9wz7q5\n")
      KeyConfigFile.write("\n")
      KeyConfigFile.write("  PATREON_CLIENT_ID             = ABCDE\n")
      KeyConfigFile.write("  PATREON_CLIENT_SECRET         = EFJHI\n")
      KeyConfigFile.write("  PATREON_CREATOR_ACCESS_TOKEN  = EFJHI\n")
      KeyConfigFile.write("\n")
      
      print("File created")
    except Exception as ErrorMessage:
      TraceMessage = traceback.format_exc()
      AdditionalInfo = "Creating the {}file".format(KeyConfigFileName)
      LED.ErrorHandler(ErrorMessage,TraceMessage,AdditionalInfo)
    





def DisplayPatreon():

#Patreon Stuff

  try:
    print("--Accessing Patreon--")
    api_client = patreon.API(PATREON_CREATOR_ACCESS_TOKEN)

    #get the campaign ID
    campaign_response = api_client.fetch_campaign()
    campaign_id       = campaign_response.data()[0].id()

    all_pledges = []
    cursor = None

    while(True):
      print('Fetching patron data (25 at a time)')
      pledges_response = api_client.fetch_page_of_pledges(
        campaign_id, 
        25,
        cursor=cursor,
        fields = {'pledge': ['total_historical_amount_cents']},
        
        )
      cursor = api_client.extract_cursor(pledges_response)
      all_pledges += pledges_response.data()
      if(not cursor):
        print('done patreon data fetch')
        break

    CreditNames = []
    for pledge in all_pledges:
      print('Listing pledges')
      print(pledge.relationship('patron').attribute('first_name'))
      print(pledge.relationship('patron').attribute('full_name'))
      print(pledge.relationship('patron').attribute('created'))

      CreditNames.append(pledge.relationship('patron').attribute('first_name'))

  except:

    print("Error while gathering patron list.  Make sure your Application Token is valid.")
    CreditNames = []
    CreditNames.append('Mathew')
    CreditNames.append('Mark')
    CreditNames.append('Luke')
    CreditNames.append('James')
    CreditNames.append('Jesus')
    


  LED.CreateCreditImage(CreditNames)
  LED.ScrollCreditImage("credits.png",ScrollSleep=0.04)













def WebHook(EventQueue):
  
 
  #we create a Flask app, assign a default function (Receiver) and use it to write to the 
  #multiprocessing Queue.  This allows the Twitch Bot to pop the queue.

  app = Flask(__name__)
  @app.route('/', methods=['POST'])
  def Receiver():
    
    MyData = request.json
    
    #MyData = request.get_json(silent=True)
    #pprint.pprint(MyData)     
    #print("DATA: ", request.json)
    EventQueue.put(MyData)
    
    #pprint.pprint(MyData, indent=2)        


    print("")
    if request.method == 'POST':
      print("==WEBHOOK===============================================")
      print("Status:      DATA RECEIVED")
      print("Method:     ",request.method)
      print("QueueCount: ",EventQueue.qsize())
      print("========================================================")
      print("")
      return 'success', 200

    elif request.method == 'GET':
      print("GET Requested.  received data: ", request.json)
      return 'success', 200

    else:
      abort(400)

    


    




  print("Running the webhook app")
  app.run()






def StartBot():

  CheckConfigFiles()
  LoadConfigFiles()


  print ("--StartBot--")
  #skip all this if running datagod
  if (CHANNEL != 'datagod'):
    #Fake boot sequence
    LED.ClearBigLED()
    LED.ClearBuffers()
    CursorH = 0
    CursorV = 0
    LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"Arcade Retro Clock",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalTypeSpeed)
    LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"by datagod",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalTypeSpeed)
    LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,".........................",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.025,ScrollSpeed=ScrollSleep)
    LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"Boot sequence initiated",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)
    LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"RAM CHECK",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)
    LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"OK",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)
    LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"STORAGE",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)
    LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"OK",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)
    LED.BlinkCursor(CursorH= CursorH,CursorV=CursorV,CursorRGB=CursorRGB,CursorDarkRGB=CursorDarkRGB,BlinkSpeed=0.5,BlinkCount=2)

    IPAddress = LED.ShowIPAddress(Wait=5)
  else:
    print("Skipping boot up sequence")

   

  mybot = Bot()
  mybot.run()



  try:
    print("Loading chat bot for: ",BOT_CHANNEL)
    #mybot.run()
  except:
    LED.ClearBigLED()
    LED.ClearBuffers()
    CursorH = 0
    CursorV = 0
    LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"The chat bot has experienced a terminal error",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)
    LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"Connection closed",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)
    








#------------------------------------------------------------------------------
# MAIN SECTION                                                               --
#------------------------------------------------------------------------------



print ("---------------------------------------------------------------")
print ("WELCOME TO THE LED ARCADE - Twitch Version                     ")
print ("")
print ("BY DATAGOD")
print ("")
print ("This program will display Twitch activity using the LEDArcade ")
print ("library.")
print ("---------------------------------------------------------------")
print ("")
print ("")


print("--Spawning WebHook process--------------")
#Spawn the webhook process
WebHookProcess = multiprocessing.Process(target = WebHook, args=(EventQueue,))
WebHookProcess.start()
#BotProcess = multiprocessing.Process(target = StartBot,args=(EventQueue,))
#BotProcess.start()
print("----------------------------------------")




StartBot()


#LED.DisplayDigitalClock(ClockStyle=2,CenterHoriz=True,v=1, hh=24, ZoomFactor = 1, AnimationDelay=30, RunMinutes = 5 )




# %%

 