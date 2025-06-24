# %%

'''
TO DO:


The EventSub is so complex to keep going...OAUTH, reverse DNS, Packet Riot, LetsEncrypt, custom domain....
I might just read the chat and react there.

Read StreamElements messages
 - X has been a s-ranked ninja for y months in a row
 - X just threw down X bits!
 - X gifted a Tier 1 sub
 - X just smoke-bombed into lurk mode. They're still here, but as silent as a feather in the wind.... and will be back when you least expect it!
 - X is raiding
 
Others 
!lurk

KofiStreamBot
 - visit XtianNinja page
 

 
'''

print("")
print("=============================================")
print("== Twitch.py                                =")
print("=============================================")
print("")



import os
#os.system('cls||clear')

import sys
import re   # regular expression

import LEDarcade as LED


#from rgbmatrix import graphics
#from rgbmatrix import RGBMatrix, RGBMatrixOptions

import random
from configparser import ConfigParser
import requests
import traceback
import socket



#multi processing
import asyncio
import multiprocessing
from multiprocessing import Process, Queue
import LEDcommander
import time




from flask import Flask, request, abort
from multiprocessing.connection import Client
import json



#Twitch
import twitchio
from twitchio.ext import commands, eventsub

#from twitchAPI.eventsub.webhook import EventSubWebhook
#from twitchAPI.object.eventsub import ChannelFollowEvent
from twitchAPI.twitch import Twitch




#Webhooks
#import patreon
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
#import DotInvaders as DI
#import Outbreak    as OB
#import Defender    as DE
#import Tron        as TR
#import SpaceDot    as SD






#---------------------------------------
#Variable declaration section
#---------------------------------------
ScrollSleep         = 0.025
TerminalTypeSpeed   = 0.02  #pause in seconds between characters
TerminalScrollSpeed = 0.02  #pause in seconds between new lines
CursorRGB           = (0,255,0)
CursorDarkRGB       = (0,50,0)
RotateClockDelay    = 5     #minutes between each clock rotation (launch an LEDarcade display every X minutes using LEDcommander)
ClockDuration       = 1

#TWITCH VARIABLES
#LEDARCADE_APP_ACCESS_TOKEN  = ''
#REFRESH_TOKEN           = ''

#LEDARCADE_APP_CLIENT_ID     = ''
#LEDARCADE_APP_CLIENT_SECRET = ''

BROADCASTER_CHANNEL = ''
CHANNEL_BIG_TEXT    = ''
CHANNEL_LITTLE_TEXT = ''

BROADCASTER_USER_ID = ''
BROADCASTER_ID      = ''
PROFILE_IMAGE_URL   = ''
VIEW_COUNT          = ''
THECLOCKBOT_CHANNEL = ''


THECLOCKBOT_ACCESS_TOKEN  = ''
THECLOCKBOT_REFRESH_TOKEN = ''
CLOCKBOT_X_ACCESS_TOKEN   = ''
CLOCKBOT_X_REFRESH_TOKEN  = ''

#BOT_REFRESH_TOKEN = ''
THECLOCKBOT_CLIENT_ID = ''
THECLOCKBOT_USER_ID   = ''
THECLOCKBOT_SECRET    = ''
TWITCH_WEBHOOK_URL    = ''
TWITCH_WEBHOOK_SECRET = ''

#PATREON VARIABLES
PATREON_CLIENT_ID            = ''
PATREON_CLIENT_SECRET        = ''
PATREON_CREATOR_ACCESS_TOKEN = ''
PATREON_WEBHOOK_URL          = ''
PATREON_WEBHOOK_SECRET       = ''




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
ChatUserListCount       = 25
ChatUserListWaitSeconds = 30

#HypeTrain info
HypeTrainStartTime   = ''
HypeTrainExpireTime  = ''
HypeTrainGoal        = ''
HypeTrainLevel       = 0
HypeTrainTotal       = ''



HatHeight = 32
HatWidth  = 64
StreamBrightness = 80
GifBrightness    = 80
MaxBrightness    = 100

  

#Configurations
SHOW_VIEWERS   = True
SHOW_FOLLOWERS = False
SHOW_SUBS      = True
SHOW_VIEWS     = True
SHOW_CHATBOT_MESSAGES = False

#Files
KeyConfigFileName = "KeyConfig.ini" 
MyConfigFileName  = "MyConfig.ini"



#Colors
TerminalRGB = (0,200,0)
CursorRGB = (0,75,0)


#Data structures
#EventQueue = asyncio.Queue()  #used to store and process chat messages


# Global variables for LEDcommander
CommandQueue   = None
CommandProcess = None





#----------------------------------------------------------------------------
# FUNCTIONS
#----------------------------------------------------------------------------


def get_viewer_message(viewer_count):
    templates = [
        "There are currently {} viewers enjoying the show.",
        "You're not alone—{} people are tuned in right now!",
        "{} awesome folks are watching this stream.",
        "Look at that! {} viewers are here with us.",
        "{} viewers, one amazing broadcast.",
        "Shoutout to all {} viewers joining us!",
        "Currently, {} fine folks are watching.",
        "{} legends are watching this epic moment.",
        "{} people are vibing with us live!",
        "Streaming live to {} amazing fans.",
        "We've got {} watchers on deck.",
        "Audience check: {} viewers present!",
        "{} people can’t be wrong—this stream rocks.",
        "{} online and counting!",
        "Roll call: {} people are in the stream.",
        "This just in—{} viewers locked in!",
        "Bringing joy to {} viewers at the moment.",
        "{} people decided to spend their time here. Excellent choice!",
        "Thank you to our {} viewers!",
        "{} streamers strong and going!",
        "Currently captivating {} eyeballs.",
        "Lighting up screens for {} people.",
        "{} people are enjoying the pixel party.",
        "This moment is shared with {} viewers.",
        "Hats off to all {} watching this live.",
        "{} tuned in for this adventure!"
    ]
    
    message = random.choice(templates).format(viewer_count)
    return message



def get_personal_hello_response(user_name):
    responses = [
        f"Hello there, {user_name}!",
        f"Hey hey, {user_name}!",
        f"What's up, {user_name}?",
        f"Howdy partner, {user_name}!",
        f"Greetings, {user_name}.",
        f"Yo, {user_name}!",
        f"Hiya, {user_name}!",
        f"Ahoy, {user_name}!",
        f"Hey you, {user_name}!",
        f"Well well well, look who's here: {user_name}!",
        f"Oh no, it's you again... {user_name}.",
        f"Welcome back, {user_name}!",
        f"Hey, it's nice to see you, {user_name}!",
        f"You're just in time, {user_name}!",
        f"Brace yourself, {user_name} is here!",
        f"Hi {user_name}. Need anything?",
        f"Let's get this party started, {user_name}!",
        f"Oh wow, hello {user_name}!",
        f"What's crackin', {user_name}?",
        f"Hola amigo, {user_name}!",
        f"Bonjour, {user_name}!",
        f"Ciao, {user_name}!",
        f"Kon'nichiwa, {user_name}!",
        f"Why hello there, {user_name}, fancy meeting you here.",
        f"Greeeetingssss... from the void, {user_name}.",
    ]
    return random.choice(responses)





def GetElapsedSeconds(starttime):
  elapsed_seconds = time.time() - starttime
  return elapsed_seconds


#
 
#We are now spawning a separate process to control the LED display

''' 
def SpawnClock(EventQueue, AnimationDelay, StreamActive, SharedState):


    try:
            import LEDarcade as LED
            LED.Initialize()
            LED.ReinitializeMatrix()
            LED.InitializeColors()
            LED.TheMatrix.brightness = 100  # force brightness again
            LED.ClearBigLED()
            LED.ClearBuffers()

            print("SpawnClock: Matrix brightness =", LED.TheMatrix.brightness)

            print("Red:",LED.MedRed," ShadowRed: ",LED.ShadowRed)


            print("SpawnClock - Begin")
            SharedState['DigitalClockSpawned'] = True
            print(f"DigitalClockSpawned set to: {SharedState['DigitalClockSpawned']}")

            r = random.choice([1, 3])
            zoom = 3 if StreamActive else 2

            print(f"ClockStyle: {r}, Zoom: {zoom}")

            LED.DisplayDigitalClock(
                ClockStyle=1,  # change back to r later
                CenterHoriz=True,
                v=1,
                hh=24,
                RGB=(255,0,0),
                ShadowRGB=(255,255,255),
                ZoomFactor=zoom,
                AnimationDelay=AnimationDelay,
                RunMinutes=1,
                EventQueue=EventQueue
            )

    except Exception as e:
            print(f"[ERROR] SpawnClock crashed: {e}")
            traceback.print_exc()
    finally:
        SharedState['DigitalClockSpawned'] = False
        print("SpawnClock - Completed")
        print(f"DigitalClockSpawned set to: {SharedState['DigitalClockSpawned']}")
''' 




class Bot(commands.Bot ):
#This started out as a Twitch Bot but has grown into a more complex program

    CursorH             = 0
    CursorV             = 0
    CursorRGB           = (0,255,0)
    CursorDarkRGB       = (0,50,0)
    AnimationDelay      = 30
    LastMessageReceived = time.time()
    LastUserJoinedChat  = time.time()
    ChatUsers           = []
    SecondsToWaitChat   = 30
    LastStreamCheckTime = time.time()
    LastChatInfoTime    = time.time()
    MinutesToWaitBeforeCheckingStream = 5       #check the stream this often
    MinutesToWaitBeforeChatInfo       = 180     #send info message to viewers about clock commands
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
    ClockRunning        = False  # <== Added flag to show if uptime clock is running


  

  
    def __init__(self,EventQueue=None):

        self.EventQueue   = EventQueue   #old, being replaced

        # Initialise our Bot with our access token, prefix and a list of channels to join on boot...
        # prefix can be a callable, which returns a list of strings or a string...
        # initial_channels can also be a callable which returns a list of strings...
        # Note: the bot client id is from Twitch Dev TheClockBot.
        
        print("Bot Initialization")
        print("THECLOCKBOT_CLIENT_ID:    ",THECLOCKBOT_CLIENT_ID)
        print("THECLOCKBOT_CLIENT_ID:    ",THECLOCKBOT_USER_ID)
        print("THECLOCKBOT_SECRET:       ",THECLOCKBOT_SECRET)
        print("THECLOCKBOT_CHANNEL:      ",THECLOCKBOT_CHANNEL)
        print("THECLOCKBOT_CODE:         ",THECLOCKBOT_CODE)
        print("THECLOCKBOT_ACCESS_TOKEN: ",THECLOCKBOT_ACCESS_TOKEN)
        print("THECLOCKBOT_REFRESH_TOKEN:",THECLOCKBOT_REFRESH_TOKEN)

        print("")
        print("")
        print("")
        print("=====================================================")
        print("Initiating client object to connect to twitch")
        print("Initial_Channels:",BROADCASTER_CHANNEL)

        super().__init__(token=THECLOCKBOT_ACCESS_TOKEN, prefix='?', initial_channels=[BROADCASTER_CHANNEL])
        
        self.BotStartTime   = time.time()
        LastMessageReceived = time.time()
        #time.sleep(3)
        print("=====================================================")
        print("")
        
        
       



    
          


    async def my_custom_startup(self):
        global CommandQueue
        
        await asyncio.sleep(1)
        self.Channel = self.get_channel(BROADCASTER_CHANNEL)
        #channel2 = self.fetch_channel(CHANNEL_ID)

        #Check Twitch advanced info 
        await self.CheckStream()

        if(StreamActive == True and SHOW_CHATBOT_MESSAGES == True):
          self.ChatTerminalOn = True
        elif(StreamActive == False and SHOW_CHATBOT_MESSAGES == True):
          #Explain the main intro is not live

          CommandQueue.put({
              "Action": "ShowTitleScreen",
              "BigText": "404",
              "BigTextRGB": LED.MedPurple,
              "BigTextShadowRGB": LED.ShadowPurple,
              "LittleText": "NO STREAM",
              "LittleTextRGB": LED.MedRed,
              "LittleTextShadowRGB": LED.ShadowRed,
              "ScrollText": BROADCASTER_CHANNEL + " not active. Try again later...",
              "ScrollTextRGB": LED.MedYellow,
              "ScrollSleep": ScrollSleep / 2,
              "DisplayTime": 1,
              "ExitEffect": 5,
              "LittleTextZoom": 1
          })

          
          


        
      

    #---------------------------------------
    #- Check Stream Info                  --
    #---------------------------------------
    # check to see if the stream is live or not
    async def CheckStream(self):
      print("Checking if stream is active")
      GetBasicTwitchInfo()
      self.LastStreamCheckTime = time.time()
      #Show title info if Main stream is active

        
    #---------------------------------------
    #- Send Chat Message                  --
    #---------------------------------------
    async def SendChatMessage(self,Message):
      await self.Channel.send(Message)
    




    #---------------------------------------
    #- Perform Time Based Actions         --
    #---------------------------------------

    async def PerformTimeBasedActions(self):
        global DigitalClockSpawned
        loop = asyncio.get_running_loop()

        if(StreamActive == True):
            await self.DisplayRandomConnectionMessage()

        while True:
            await asyncio.sleep(5)
            print("Stream Status:",StreamActive)

            if(StreamActive == True):
                if (self.ChatTerminalOn == True):
                    h,m,s = LED.GetElapsedTime(self.LastMessageReceived,time.time())
                    if (m >= self.MinutesToWaitBeforeClosing ):
                        CommandQueue.put({"Action": "terminalmessage", "Message": "No chat activity detected.  Did everyone fall asleep?", "RGB": (100, 100, 0), "ScrollSleep": 0.03 })
                        CommandQueue.put({"Action": "terminalmessage", "Message": "Closing Terminal", "RGB": (100, 100, 0), "ScrollSleep": 0.03 })
                        CommandQueue.put({"Action": "terminalmessage", "Message": "................", "RGB": (100, 100, 0), "ScrollSleep": 0.03 })
                        CommandQueue.put({"Action": "terminalmode_off"})
                        self.ChatTerminalOn = False
                        self.ClockRunning   = False  # Reset clock flag when terminal closes

                if(self.ChatTerminalOn == False and self.ClockRunning == False):
                    #print("[Twitch] Creating multiprocess DisplayDigitalClock()")
                    #self.DisplayDigitalClock()
                    self.ClockRunning = True
                    await self.RotateClockDisplays(RotateClockDelay)




            #-------------------------------------------------------------------------
            #-- If stream is not active, run a series of displays for X minutes each
            #-------------------------------------------------------------------------
            
            if (StreamActive == False):
                print("[Twitch] StreamActive == False")
                                
                await self.RotateClockDisplays(RotateClockDelay)
                
                
                

                



            h,m,s = LED.GetElapsedTime(self.LastChatInfoTime,time.time())
            if (m >= self.MinutesToWaitBeforeChatInfo):
                await self.SendChatMessage("Don't forget to interact with the LED display.  Type ?clock for a list of commands.")
                self.LastChatInfoTime = time.time()

            h,m,s = LED.GetElapsedTime(self.LastStreamCheckTime,time.time())
            if (m >= self.MinutesToWaitBeforeCheckingStream):
                await self.CheckStream()
                if(StreamActive == True):
                    self.LastStreamCheckTime = time.time()



    #---------------------------------------
    #- Event Ready                        --
    #---------------------------------------
    async def event_ready(self):
        global CommandQueue
        # Notify us when everything is ready!
        # We are logged in and ready to chat and use commands...
        #UserList = self.fetch_users()
        print("")
        print("=================================================")
        print(f'Logged in as | {self.nick}')
        #print("Channels logged in:', self.connected_channels.__len__())
        #Channel = self.fetch_channel(CHANNEL)
        #print(Channel)
        print("=================================================")
        print("")

        
        #My custom startup code runs here
        await self.my_custom_startup()
        #await self.Sleep()

        
        if(StreamActive == True):

          #skip my own channel for testing purposes
          if(BROADCASTER_CHANNEL != 'datagod' and BROADCASTER_CHANNEL.upper() != 'XTIANNINJA'):

              # INTRO FOR MAIN CHANNEL
              CommandQueue.put({
                  "Action": "ShowTitleScreen",
                  "BigText": CHANNEL_BIG_TEXT,
                  "BigTextRGB": LED.MedPurple,
                  "BigTextShadowRGB": LED.ShadowPurple,
                  "LittleText": CHANNEL_LITTLE_TEXT,
                  "LittleTextRGB": LED.MedRed,
                  "LittleTextShadowRGB": LED.ShadowRed,
                  "ScrollText": Title,
                  "ScrollTextRGB": LED.MedYellow,
                  "ScrollSleep": ScrollSleep,
                  "DisplayTime": 1,
                  "ExitEffect": 5,
                  "LittleTextZoom": 2
              })

              # SHOW FOLLOWERS
              if SHOW_FOLLOWERS:
                  BigTextZoom = 2 if Followers > 9999 else 3
                  CommandQueue.put({
                      "Action": "ShowTitleScreen",
                      "BigText": str(Followers),
                      "BigTextRGB": LED.MedPurple,
                      "BigTextShadowRGB": LED.ShadowPurple,
                      "BigTextZoom": BigTextZoom,
                      "LittleText": "FOLLOWS",
                      "LittleTextRGB": LED.MedRed,
                      "LittleTextShadowRGB": LED.ShadowRed,
                      "ScrollText": "",
                      "ScrollTextRGB": LED.MedYellow,
                      "ScrollSleep": ScrollSleep,
                      "DisplayTime": 1,
                      "ExitEffect": 0
                  })

              # SHOW VIEWERS
              if SHOW_VIEWERS:
                  CommandQueue.put({
                      "Action": "ShowTitleScreen",
                      "BigText": str(ViewerCount),
                      "BigTextRGB": LED.MedPurple,
                      "BigTextShadowRGB": LED.ShadowPurple,
                      "BigTextZoom": 3,
                      "LittleText": "Viewers",
                      "LittleTextRGB": LED.MedRed,
                      "LittleTextShadowRGB": LED.ShadowRed,
                      "ScrollText": f"Now Playing: {GameName}",
                      "ScrollTextRGB": LED.MedYellow,
                      "ScrollSleep": ScrollSleep,
                      "DisplayTime": 1,
                      "ExitEffect": 1
                  })

              # CHAT TERMINAL INTRO
              CommandQueue.put({
                  "Action": "ShowTitleScreen",
                  "BigText": "CHAT",
                  "BigTextRGB": LED.MedRed,
                  "BigTextShadowRGB": LED.ShadowRed,
                  "LittleText": "TERMINAL",
                  "LittleTextRGB": LED.MedBlue,
                  "LittleTextShadowRGB": LED.ShadowBlue,
                  "ScrollText": f"TUNING IN TO {BROADCASTER_CHANNEL}",
                  "ScrollTextRGB": LED.MedOrange,
                  "ScrollSleep": ScrollSleep,
                  "DisplayTime": 1,
                  "ExitEffect": 0,
                  "LittleTextZoom": 1
              })


          await self.SendRandomChatGreeting()
        await self.PerformTimeBasedActions()

    

        
    #---------------------------------------
    # Rotate Clock Displays               --
    #---------------------------------------
    async def RotateClockDisplays(self, RotateClockDelay: int = 5):


        #Blasteroids clock (style=5)
        CommandQueue.put({ "Action": "showclock",   "Style": 5,  "Zoom": 1,   "duration": 10, "Delay": 10  })
        await asyncio.sleep(RotateClockDelay * 60)


        CommandQueue.put({"Action": "retrodigital", "duration": 10 })
        await asyncio.sleep(RotateClockDelay * 60)

        #StarryNight clock display (style=3)
        CommandQueue.put({ "Action": "showclock",   "Style": 3,  "Zoom": 2,   "duration": 10, "Delay": 10  })
        await asyncio.sleep(RotateClockDelay * 60)
        self.DisplayDigitalClock(ClockDuration)


        CommandQueue.put({"Action": "launch_defender", "duration": 10 })
        await asyncio.sleep(RotateClockDelay * 60)
        self.DisplayDigitalClock(ClockDuration)


        CommandQueue.put({"Action": "launch_dotinvaders", "duration": 10 })
        await asyncio.sleep(RotateClockDelay * 60)
        self.DisplayDigitalClock(ClockDuration)


        CommandQueue.put({"Action": "launch_gravitysim", "duration": 10 })
        await asyncio.sleep(RotateClockDelay * 60)
        self.DisplayDigitalClock(ClockDuration)


        CommandQueue.put({"Action": "launch_tron", "duration": 10 })
        await asyncio.sleep(RotateClockDelay * 60)
        self.DisplayDigitalClock(ClockDuration)

        CommandQueue.put({"Action": "launch_outbreak", "duration": 10 })
        await asyncio.sleep(RotateClockDelay * 60)
        self.DisplayDigitalClock(ClockDuration)

        CommandQueue.put({"Action": "launch_spacedot", "duration": 10 })
        await asyncio.sleep(RotateClockDelay * 60)
        self.DisplayDigitalClock(ClockDuration)

        CommandQueue.put({"Action": "launch_fallingsand", "duration": 10 })
        await asyncio.sleep(RotateClockDelay * 60)
        self.DisplayDigitalClock(ClockDuration)





    #---------------------------------------
    # READ CHAT MESSAGES                  --
    #---------------------------------------
    async def event_message(self, message):
        

        print("Reading chat messages")

        # Messages with echo set to True are messages sent by the bot...
        # For now we just want to ignore them...
        if message.echo:
          return
        
        # Since we have commands and are overriding the default `event_message`
        # We must let the bot know we want to handle and invoke our commands...
        await self.handle_commands(message)


        # Check for special key words
        #Remove emoji from message
        message.content = LED.deEmojify(message.content)

        author = message.author.display_name

        #Log Chat
        print('CHAT| ',author,':',message.content)


        #---------------------------------------
        # KOFI                                --
        #---------------------------------------
        if (author.upper() == 'KOFISTREAMBOT'  and "VISIT" in message.content.upper()):
          print("CHAT| KofiBot detected")

          message = "Time for a Kofi"
          await self.Channel.send(message)
          
          Text1       = "KOFI"
          Text2       = "WE APPRECIATE YOUR SUPPORT"
          Text3       = "KOFI IS THE PREFERRED WAY TO SUPPORT THIS CHANNEL"

          CommandQueue.put({"Action": "StarryNightDisplayText",
                            "text1": Text1,
                            "text2": Text2,
                            "text1": Text3}
                            )





        #---------------------------------------
        # Stream Elements                     --
        #---------------------------------------
        
        #TACO
        if (author.upper() == 'STREAMELEMENTS'  and "GROWING" in message.content.upper()):
          print("CHAT| TACO detected")

          Text1       = "TACO"
          Text2       = "The Alliance for creative outreach"
          Text3       = "visit taconetwork.org to learn all about us"

          CommandQueue.put({"Action": "starrynightdisplaytext",
                            "text1": Text1,
                            "text2": Text2,
                            "text3": Text3}
                            )

        #Dragon Coffee
        if (author.upper() == 'STREAMELEMENTS'  and "COFFEE" in message.content.upper()):
          print("CHAT| TACO detected")

          Text1       = "dragon roast coffee"
          Text2       = "Great Nerd Coffee"
          Text3       = "the thing that makes everything better"

          CommandQueue.put({"Action": "starrynightdisplaytext",
                            "text1": Text1,
                            "text2": Text2,
                            "text3": Text3}
                            )




        # Check for S-Ranked Ninja message
        match = re.search(r'^(?P<username>\w+).+?S-Ranked Ninja for (?P<duration>\d+ months)', message.content)
        if match:
            username = match.group('username')
            duration = match.group('duration')
            print(f"CHAT| S-Ranked Ninja detected: {username}, {duration}")

            CommandQueue.put({
                "Action": "starrynightdisplaytext",
                "text1": f"{username}",
                "text2": "S-Ranked Ninja!",
                "text3": f"{duration} strong!"
            })



        #BITS
        #if (author == 'StreamElements'  and message.content.upper() == ""):
        if (author.upper() == 'STREAMELEMENTS'  and "JUST THREW DOWN" in message.content.upper()):
          print("CHAT| BITS detected")

          words  = message.content.split(" ")
          BitGiver = words[0] 
          bits     = words[4]
          print("CHAT|",BitGiver,"just threw down ",bits," bits")

          #LED.ClearBigLED()
          #LED.ClearBuffers()

          Text1       = BitGiver + " just threw down " + bits + " bits"
          Text2       = "Thank you " + BitGiver
          Text3       = "Bits are an important part of the economy.  Your contribution is appreciated!"

          CommandQueue.put({"Action": "StarryNightDisplayText",
                            "text1": Text1,
                            "text2": Text2,
                            "text1": Text3}
                            )





        #FOLLOWING
        #if (author == 'StreamElements'  and message.content.upper() == "is raiding"):
        if (author.upper() == 'STREAMELEMENTS'  and "THANK YOU FOR FOLLOWING" in message.content.upper()):
          print("CHAT| follow detected")

          words  = message.content.split(" ")
          follower = words[4] 
          print("CHAT|",follower,"is now following")

          Text1       = follower + " is now following" 
          Text2       = "Thank you " + follower
          Text3       = "Welcome to our community.  We appreciate you joining us!",
          CommandQueue.put({"Action": "StarryNightDisplayText",
                            "text1": Text1,
                            "text2": Text2,
                            "text3": Text3}
                            )




        #RAIDING
        #if (author == 'StreamElements'  and message.content.upper() == "is raiding"):
        if (author.upper() == 'STREAMELEMENTS'  and "IS RAIDING" in message.content.upper()):
          print("CHAT| Raid detected")

          words  = message.content.split(" ")
          raider = words[0] 
          print("CHAT|",raider,"is raiding")
          
          Text1       = raider + " is raiding"
          Text2       = "Thank you " + raider
          Text3       = "Welcome to our community.  Stick around and have fun!"

          CommandQueue.put({"Action": "StarryNightDisplayText",
                  "text1": Text1,
                  "text2": Text2,
                  "text3": Text3}
                  )





        #Subscriber for X months
        if (author.upper() == 'STREAMELEMENTS'  and "MONTHS IN A ROW" in message.content.upper()):

          print("CHAT| SUBscriber detected")
          words  = message.content.split(" ")
          Subscriber = words[0] 
          Months     = words[6]
          print("CHAT|",Subscriber," has been a subscriber for ",Months, " months")
        
          print("Get user profile info:",Subscriber)
          API_ENDPOINT = "https://api.twitch.tv/helix/users?login=" + Subscriber
          head = {
          #'Client-ID': CLIENT_ID,
          'Client-ID':  THECLOCKBOT_CLIENT_ID,
          'Authorization': 'Bearer ' +  THECLOCKBOT_ACCESS_TOKEN
          }

          #print ("URL: ",API_ENDPOINT, 'data:',head)
          r = requests.get(url = API_ENDPOINT, headers = head)
          results = r.json()
          pprint.pprint(results)
          #print(" ")

          UserProfileURL = ''
          DataDict = results.get('data','NONE')
          if (DataDict != 'NONE'):

            print("Data found.  Processing...")

            try:
              UserProfileURL = results['data'][0]['profile_image_url']

            except Exception as ErrorMessage:
              TraceMessage = traceback.format_exc()
              AdditionalInfo = "Getting CHANNEL info from API call" 
              LED.ErrorHandler(ErrorMessage,TraceMessage,AdditionalInfo)
           
        
          if (UserProfileURL != ""):
            LED.GetImageFromURL(UserProfileURL,"UserProfile.png")

            CommandQueue.put({"Action": "showimagezoom",
                              "image": "UserProfile.png",
                              "zoommin" : 1,
                              "zoommax":256,
                              "zoomfinal" : 32,
                              "sleep" : 0.01,
                              "step"  : 1})



        #LURK
        if (message.content.upper() == "!LURK"):
          print("LURK MODE ACTIVATED: ",author)

          #LED.ClearBigLED()
          #LED.ClearBuffers()

          CommandQueue.put({
                  "Action": "ShowTitleScreen",
                  "BigText": "LURK",
                  "BigTextRGB": LED.MedGreen,
                  "BigTextShadowRGB": LED.ShadowGreen,
                  "BigTextZoom": 3,
                  "LittleText": "",
                  "LittleTextRGB": LED.MedRed,
                  "LittleTextShadowRGB": LED.ShadowRed,
                  "LittleTextZoom": 2,
                  "ScrollText": author + " has gone into lurk mode",
                  "ScrollTextRGB": LED.MedYellow,
                  "ScrollSleep": ScrollSleep,
                  "DisplayTime": 1,
                  "ExitEffect": 1
              })

          ''' 
          LED.ShowTitleScreen(
            BigText             = "LURK",
            BigTextRGB          = LED.MedGreen,
            BigTextShadowRGB    = LED.ShadowGreen,
            BigTextZoom         = 3,
            LittleText          = '',
            LittleTextRGB       = LED.MedRed,
            LittleTextShadowRGB = LED.ShadowRed, 
            ScrollText          = author + " has gone into lurk mode",
            ScrollTextRGB       = LED.MedYellow,
            ScrollSleep         = ScrollSleep, # time in seconds to control the scrolling (0.005 is fast, 0.1 is kinda slow)
            DisplayTime         = 0,           # time in seconds to wait before exiting 
            ExitEffect          = 1            # 0=Random / 1=shrink / 2=zoom out / 3=bounce / 4=fade /5=fallingsand
            )
          ''' 
          print("LURK MODE DEACTIVATED")


        #----------------------------------------
        #-- Trigger Words
        #----------------------------------------


        if author.upper() != 'TheClockBot':
          #HUGS
          if ("HUG" in message.content.upper()):
              CommandQueue.put({"Action": "showheart" })

          #Jesus
          if any(word in message.content.upper() for word in ("JESUS","CHRIST","CHRISTIAN","CHURCH")):
          
            CommandQueue.put({"Action": "showimagezoom",
                      "image": "./images/Jesus1.png",
                      "zoommin" : 1,
                      "zoommax":128,
                      "zoomfinal" : 32,
                      "sleep" : 0.01,
                      "step"  : 1})


        #REDALERT
        if ("STORM" in message.content.upper()):
            CommandQueue.put({"Action": "showgif", "GIF": './images/storm.gif', "Loops" : 5, "sleep":0.06 })

        #Ghosts
        if ("GHOST" in message.content.upper()):
            CommandQueue.put({"Action": "showgif", "GIF": './images/ghosts.gif', "Loops" : 10, "sleep":0.06 })


        #simpsons
        if ("SIMPSONS" in message.content.upper()):
          r = random.randint(1,5)
          if r == 1:
            CommandQueue.put({"Action": "showgif", "GIF": './images/homer_marge2.gif', "Loops" : 4, "sleep":0.06 })
          if r == 2:
            CommandQueue.put({"Action": "showgif", "GIF": './images/policefist.gif', "Loops" : 4, "sleep":0.06 })
          if r == 3:
            CommandQueue.put({"Action": "showgif", "GIF": './images/simpsonspolice.gif', "Loops" : 1, "sleep":0.06 })
          if r == 4:
            CommandQueue.put({"Action": "showgif", "GIF": './images/simpsons1.gif', "Loops" : 10, "sleep":0.2 })
          if r == 5:
            CommandQueue.put({"Action": "showgif", "GIF": './images/simpsons2.gif', "Loops" : 2, "sleep":0.06 })


        #minions
        if ("MINION" in message.content.upper()):
          r = random.randint(1,6)
          if r == 1:
            CommandQueue.put({"Action": "showgif", "GIF": './images/minioncrying.gif', "Loops" : 10, "sleep":0.06 })
          if r == 2:
            CommandQueue.put({"Action": "showgif", "GIF": './images/minioncrying2.gif', "Loops" : 10, "sleep":0.06 })

          if r == 3:
            CommandQueue.put({"Action": "showgif", "GIF": './images/minioneyes.gif', "Loops" : 10, "sleep":0.06 })

          if r == 4:
            CommandQueue.put({"Action": "showgif", "GIF": './images/miniongru.gif', "Loops" : 10, "sleep":0.06 })
          if r == 5:
            CommandQueue.put({"Action": "showgif", "GIF": './images/minionredalert.gif', "Loops" : 10, "sleep":0.06 })
          if r == 6:
            CommandQueue.put({"Action": "showgif", "GIF": './images/minions.gif', "Loops" : 10, "sleep":0.06 })



        #POLICE
        if any(word in message.content.upper() for word in ("POLICE","COPS","FBI","CIA")):
          if random.randint(1,2) == 1:
            CommandQueue.put({"Action": "showgif", "GIF": './images/simpsonspolice.gif', "Loops" : 2, "sleep":0.06 })
          else:
            CommandQueue.put({"Action": "showgif", "GIF": './images/policefist.gif', "Loops" : 2, "sleep":0.06 })
          
        #FOOD
        if any(word in message.content.upper() for word in ("FOOD", "EAT", "CHICKEN","CAKE")):
          if random.randint(1,2) == 1:
            CommandQueue.put({"Action": "showgif", "GIF": './images/food1.gif', "Loops" : 1, "sleep":0.06 })
          else:
            CommandQueue.put({"Action": "showgif", "GIF": './images/food2.gif', "Loops" : 1, "sleep":0.06 })



        #WATCH
        if ("WATCH" in message.content.upper()):
            CommandQueue.put({"Action": "analogclock", "duration": 30 })

        #RETRO
        if any(word in message.content.upper() for word in ("RETRO","BUBBLE","TIME")):
            CommandQueue.put({"Action": "retrodigital", "duration": 30 })


        #SLAP
        if any(word in message.content.upper() for word in ("SLAP","PUNCH","HIT")):
            CommandQueue.put({"Action": "showgif", "GIF": './images/slap.gif', "Loops" : 1, "sleep":0.06 })



        #VIP / Hello
        if (message.content.upper() == "!VIP"):

          CommandQueue.put({
              "Action": "ShowTitleScreen",
              "BigText": "HI",
              "BigTextRGB": LED.MedPurple,
              "BigTextShadowRGB": LED.ShadowPurple,
              "BigTextZoom" : 3,
              "LittleText": "",
              "LittleTextRGB": LED.MedRed,
              "LittleTextShadowRGB": LED.ShadowRed,
              "ScrollText": "Hello there "+ author + "! Thanks for tuning in.",
              "ScrollTextRGB": LED.MedYellow,
              "ScrollSleep": ScrollSleep,
              "DisplayTime": 5,
              "ExitEffect": 0
              
          })



          #Goodbye
        if (message.content.upper() == "!GOODBYE"):
          CommandQueue.put({
              "Action": "ShowTitleScreen",
              "BigText": "BYE",
              "BigTextRGB": LED.MedPurple,
              "BigTextShadowRGB": LED.ShadowPurple,
              "BigTextZoom" : 3,
              "LittleText": "",
              "LittleTextRGB": LED.MedRed,
              "LittleTextShadowRGB": LED.ShadowRed,
              "ScrollText": "See you later" + author,
              "ScrollTextRGB": LED.MedYellow,
              "ScrollSleep": ScrollSleep,
              "DisplayTime": 5,
              "ExitEffect": 0
          })








        #Exit if Chat Terminal is not on
        if (self.ChatTerminalOn == False):
          self.MesageCount = self.MessageCount -1
          return
        

        

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
          # Start TerminalMode
          CommandQueue.put({"Action": "terminalmode_on","Message": "CHAT MODE ON","RGB": (0, 200, 0),"ScrollSleep": 0.03 })
          CommandQueue.put({"Action": "terminalmode_on","Message": message.author.display_name + ":","RGB": (100, 0, 200),"ScrollSleep": self.BotScrollSpeed })
          CommandQueue.put({"Action": "terminalmode_on","Message": ScrollText,"RGB": (0, 150, 0),"ScrollSleep": self.BotScrollSpeed })

        except:
          print('ERROR - Something went wrong writing to the terminal')

        
        self.MesageCount = self.MessageCount -1

      
      

        
   

    #---------------------------------------
    # Event Join                          --
    #---------------------------------------
    async def event_join(self,channel,user):
      #Called when a channel event is detected?
      print("Channel:",channel.name, " User:",user.name)
      

      self.ChatUsers.append(user.name)

      elapsed_seconds = GetElapsedSeconds(self.LastUserJoinedChat)

      
      '''  --> this is broken, keeps scrolling
      if(StreamActive == True and 
        ((elapsed_seconds >= ChatUserListWaitSeconds) or (len(self.ChatUsers) >= ChatUserListCount))):
    
   
        LED.TheMatrix.brightness = StreamBrightness
        LED.ScrollJustJoinedUser(self.ChatUsers,'JustJoined.png',0.04)
        #Empty chat user list
        self.ChatUsers = []
        LED.TheMatrix.brightness = MaxBrightness
        #clean up the screen using animations
        LED.SweepClean()
      '''

      LastUserJoinedChat  = time.time()
      
      

      
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
      
       #CursorH = self.CursorH
      #CursorV = self.CursorV
      #LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,message,CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalScrollSpeed)
      #LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray," ",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalScrollSpeed)
      #LED.BlinkCursor(CursorH= CursorH,CursorV=CursorV,CursorRGB=self.CursorRGB,CursorDarkRGB=self.CursorDarkRGB,BlinkSpeed=0.5,BlinkCount=2)
      #self.CursorH = CursorH
      #self.CursorV = CursorV
      
      CommandQueue.put({
          "Action": "terminalmessage",
          "Message": message,
          "RGB": (100, 100, 0),
          "ScrollSleep": 0.03
      })



 
    #---------------------------------------
    # Display connection message          --
    #---------------------------------------
    async def DisplayConnectingToTerminalMessage(self):
      #Show terminal connection message
      
      
      #LED.ClearBigLED()
      #LED.ClearBuffers()
      #CursorH = 0
      #CursorV = 0
      #LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"INITIATING CONNECTION",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)
      #LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,".....",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.5,ScrollSpeed=ScrollSleep)
      #self.CursorH = CursorH
      #self.CursorV = CursorV
      
      CommandQueue.put({"Action": "terminalmode_on", "RGB": (0, 200, 0),"ScrollSleep": 0.03  })
  
      CommandQueue.put({
        "Action": "terminalmessage",
        "Message": "Initiating connection",
        "RGB": (100, 100, 0),
        "ScrollSleep": ScrollSleep   })



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

        CommandQueue.put({
          "Action": "terminalmessage",
          "Message": message,
          "RGB": RGB,
          "ScrollSleep": LED.ScrollSleep   })


    #---------------------------------------
    # Turn on Timer (UPTIME)              --
    #---------------------------------------

    async def DisplayTwitchTimer(self):
      
      
      print ("Task started: DisplayTwitchTimer")
      
      
      #Only do this if the timer function is actually finished
      if(StreamActive == True):
        CommandQueue.put({"Action": "twitchtimer_on", "StreamStartedDateTime": StreamStartedDateTime,"StreamDurationHHMMSS": StreamDurationHHMMSS})
        print("Returned back from DisplayTwitchTimer")
      else:
        print("Timer is not yet finished")
        



    #---------------------------------------
    # Turn on RegularClock                --
    #---------------------------------------

    def DisplayDigitalClock(self,ClockDuration):
      global CommandQueue
      print("Starting: DisplayDigitalClock")

      try:
        # Stop existing clock (if any), then start new one
        CommandQueue.put({"Action": "stopclock"})
        
        #Formulate the command.      
        CommandQueue.put({
            "Action": "showclock",
            "Style": 1,
            "Zoom": 3 ,
            "duration": ClockDuration,  # minutes
            "Delay": self.AnimationDelay
        })

      except Exception as e:
        print(f"[ERROR] Failed to send clock command: {e}")
        traceback.print_exc()

    
      
    
    
    


    #---------------------------------------
    # WEBHOOK EventQueue                  --
    #---------------------------------------

    async def ReadEventQueue(self):
      global EventQueue
      QueueCount = EventQueue.qsize()
      print("Reading EventQueue: ",QueueCount)

      for i in range (0,QueueCount):
        try:      
          #Read the Queue then mark it as complete

          print("")
          print("")
          print("==ReadEventQueue=======================")

          MessageType, Message = EventQueue.get_nowait()
          EventQueue.task_done()
          #print("Message ",str(QueueCount),":",Message)

          print("Parsing Event Message")
          await self.ProcessEvent(MessageType, Message)
          
          print("=======================================")
          print("")

        except Exception as ErrorMessage:
          TraceMessage = traceback.format_exc()
          AdditionalInfo = "Reading an object from the EventQueue" 
          LED.ErrorHandler(ErrorMessage,TraceMessage,AdditionalInfo)      
 
      
      
      

    async def ProcessEvent(self,MessageType, Message):
      #we need to determine the type of event, source of webhook etc

      print("MessageType:",MessageType)
      pprint.pprint(Message,indent=4)

      BitsThrown = 0


      #--------------------------------------
      #-- Patreon Events                   --
      #--------------------------------------
      if(MessageType == "PATREON"):
        DataDict = Message.get('data','NONE')

        if (DataDict != 'NONE'):
          print("Patreon data")
          AttributesDict = DataDict.get('attributes','NONE')

        if(AttributesDict != 'NONE'):
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
          
          

          LED.StarryNightDisplayText(
            Text1 = "NEW PATRON",
            Text2 = "Thank you " + FirstName,
            Text3 = "You are an awesome supporter!",
            RunSeconds = 60
            )                    



      #--------------------------------------
      #-- Twitch Events                    --
      #--------------------------------------
      
      elif (MessageType == 'EVENTSUB_STREAM_ONLINE'):
          EventDict = Message.get('event','NONE')
          if(EventDict != "NONE"):
            print("Event discovered")
            StartedAt = Message['event']['started_at']

            LED.DisplayGIF('./images/homer_marge2.gif',64,32,5,0.04)
            LED.StarryNightDisplayText(
              Text1 = "STREAM ONLINE",
              Text2 = "STREAM ONLINE",
              Text3 = "PREPARE YOURSELF FOR JOY AND ENTERTAINMENT", 
              RunSeconds = 30
              )                    

      elif (MessageType == 'EVENTSUB_FOLLOW'):
          EventDict = Message.get('event','NONE')
          if(EventDict != "NONE"):
            print("Event discovered")
            FollowedBy = Message['event']['user_name']
          
            LED.TheMatrix.brightness = GifBrightness
            LED.DisplayGIF('./images/minions.gif',64,32,5,0.06)
            LED.TheMatrix.brightness = MaxBrightness
            
            LED.StarryNightDisplayText(
              Text1 = FollowedBy,
              Text2 = "NEW FOLLOWER!!",
              Text3 = "THANK YOU FOR YOUR SUPPORT", 
              RunSeconds = 60
              )                    


      #SUBSCRIPTION GIFT
      elif (MessageType == 'EVENTSUB_SUBSCRIBE'):
        EventDict = Message.get('event','NONE')
        if(EventDict != "NONE"):
          NameDict = EventDict.get('user_name','NONE')
          print ("*****************************************************")
          print(NameDict)
          #BITS
          if(NameDict != "NONE"):
            print("Found: user_name")
            TwitchUser = Message['event']['user_name']
            print("user_name:",TwitchUser)

            LED.DisplayGIF('./images/minions.gif',64,32,15,0.06)

            LED.StarryNightDisplayText(
              Text1 = str(BitsThrown) + "TwitchUser",
              Text2 = "NEW SUBSCRIBER!!",
              Text3 = "THANK YOU FOR YOUR SUPPORT", 
              RunSeconds = 60
              )                    



      #SUBSCRIPTION GIFT
      elif (MessageType == 'EVENTSUB_SUBSCRIPTION_GIFT'):
        EventDict = Message.get('event','NONE')
        if(EventDict != "NONE"):
          NameDict = EventDict.get('user_name','NONE')
          print ("*****************************************************")
          print(NameDict)
          #BITS
          if(NameDict != "NONE"):
            print("Found: user_name")
            TwitchUser = Message['event']['user_name']
            print("user_name:",user_name)

            LED.DisplayGIF('./images/minions.gif',64,32,15,0.06)

            LED.StarryNightDisplayText(
              Text1 = str(BitsThrown) + "TwitchUser",
              Text2 = "GAVE A SUBSCRIPTION!!",
              Text3 = "THANK YOU FOR YOUR SUPPORT", 
              RunSeconds = 60
              )                    


      #BITS / CHEER
      elif (MessageType == 'EVENTSUB_CHEER'):
        EventDict = Message.get('event','NONE')
        if(EventDict != "NONE"):
          BitsDict = EventDict.get('bits','NONE')
          print ("*****************************************************")
          print(EventDict)
          #BITS
          if(BitsDict != "NONE"):
            print("Found: bits")
            BitsThrown = Message['event']['bits']
            TwitchUser = Message['event']['user_name']
            print ("Found: bits")
            print("Bits thrown:",BitsThrown)

            LED.TheMatrix.Clear()
            LED.TheMatrix.brightness = GifBrightness
            LED.DisplayGIF('./images/marioprincesskiss.gif',32,32,1,0.06)
            LED.DisplayGIF('./images/minions.gif',64,32,15,0.06)


            LED.StarryNightDisplayText(
              Text1 = str(BitsThrown) + " BITS",
              Text2 = TwitchUser,
              Text3 = "THANK YOU FOR YOUR SUPPORT", 
              RunSeconds = 40
              )                    
            LED.TheMatrix.brightness = MaxBrightness

      #CHANNEL POINTS REDEMPTION
      elif (MessageType == 'EVENTSUB_POINTS_REDEMPTION'):
        EventDict = Message.get('event','NONE')
        if(EventDict != "NONE"):
          RewardDict = EventDict.get('reward','NONE')
          print ("*****************************************************")
          print(EventDict)
          #REWARDS
          if(RewardDict != "NONE"):
            print("Found: channel points redeemed")
            #Reward     = Message['event']['reward']
            TwitchUser = Message['event']['user_name']
            Cost       = Message['event']['reward']['cost']
            Title      = Message['event']['reward']['title']
            print ("username:     ",TwitchUser)
            print("points redeemed:",Cost)

            LED.TheMatrix.brightness = GifBrightness
            if (Title.upper() in ("D'OH!",'KHAN!','LANGUAGE!','BAZINGA','ANGRY PIGLIN','CREEPER','GHAST SCREAM')):
              r = random.randint(0,6)            
              if (r == 0):
                LED.DisplayGIF('./images/fishburger.gif',64,32,2,0.04)
              elif(r==1):
                LED.DisplayGIF('./images/ghosts.gif',64,32,10,0.04)
              elif(r==2):
                LED.TheMatrix.Clear()
                LED.DisplayGIF('./images/samus.gif',32,32,20,0.06)
              elif(r==3):
                LED.TheMatrix.Clear()
                LED.DisplayGIF('./images/samusbounce.gif',32,32,15,0.09)
              elif(r==4):
                LED.DisplayGIF('./images/minions.gif',64,32,15,0.06)
              elif(r==5):
                LED.DisplayGIF('./images/minioneyes.gif',64,32,4,0.06)
              elif(r==6):
                LED.DisplayGIF('./images/minioncrying2.gif',64,32,4,0.06)



            elif(Title.upper() in ('RIMSHOT','HYDRATE!','POSTURE CHECK!','BREAK IT DOWN NED','CONFETTI','HIGHLIGHT MY MESSAGE','STREEEEEEEEEETCH','HIT THE DAB')):
              r = random.randint(0,6)
              if (r == 0):
                LED.DisplayGIF('./images/homer_marge2.gif',64,32,15,0.04)
              elif (r == 1):
                LED.DisplayGIF('./images/arcade1.gif',64,32,25,0.12)
              elif (r == 2):
                LED.DisplayGIF('./images/arcade2.gif',64,32,25,0.12)
              elif (r == 3):
                LED.TheMatrix.Clear()
                LED.DisplayGIF('./images/mario.gif',32,32,15,0.05)
              elif(r==4):
                LED.TheMatrix.Clear()
                LED.DisplayGIF('./images/samus.gif',32,32,20,0.06)
              elif(r==5):
                LED.DisplayGIF('./images/minions.gif',64,32,15,0.06)
              elif(r==6):
                LED.TheMatrix.Clear()
                LED.DisplayGIF('./images/marioprincesskiss.gif',32,32,1,0.06)

            elif(Title.upper() in ('RED ALERT')):
              LED.DisplayGIF('./images/redalert.gif',64,32,20,0.06)
          
            elif(Title.upper() in ('GET ROMANTIC')):
              LED.DisplayGIF('./images/marioprincesskiss.gif',32,32,5,0.06)


            elif(Title.upper =='POLICE! OPEN UP!'):
              LED.DisplayGIF('./images/policefist.gif',64,32,5,0.06)

            elif(Title.upper() == 'DANCE PARTY'):
              LED.DisplayGIF('./images/storm.gif',64,32,5,0.06)

            elif(Title.upper() == 'THUNDERSTORM'):
              LED.DisplayGIF('./images/storm.gif',64,32,5,0.06)


            LED.TheMatrix.brightness = MaxBrightness
            LED.SweepClean()

            LED.StarryNightDisplayText(
              Text1 = Title,
              Text2 = TwitchUser + " SPENT " + str(Cost) + " POINTS",
              Text3 = "KEEP GOING " + TwitchUser + " YOU GOT MORE TO SPEND!", 
              RunSeconds = 30
              )                    


      #HYPE TRAIN BEGIN
      elif (MessageType == 'EVENTSUB_HYPE_TRAIN_BEGIN'):
          print("HYPE TRAIN BEGIN")
          pprint.pprint(Message)
          LED.StarryNightDisplayText(
            Text1 = "HYPE TRAIN STARTED!",
            Text2 = "HYPE TRAIN STARTED",
            Text3 = "More details soon", 
            RunSeconds = 60
            )                    

      #HYPE TRAIN PROGRESS
      elif (MessageType == 'EVENTSUB_HYPE_TRAIN_PROGRESS'):
          print("HYPE TRAIN PROGRESS")
          EventDict = Message.get('event','NONE')
          if(EventDict != 'NONE'):
            HypeLevel = Message['event']['level']
            HypeTotal = Message['event']['total']
            HypeGoal = Message['event']['goal']
            print("HypeTrainLevel: ",HypeLevel)
            print("HypeTrainTotal: ",HypeTotal)
            print("HypeTrainGoal: ",HypeGoal)
            pprint.pprint(Message)

          LED.ShowTitleScreen(
            BigText             = "LEVEL",
            BigTextRGB          = LED.HighRed,
            BigTextShadowRGB    = LED.ShadowRed,
            BigTextZoom         = 3, 
            BigText2            = '',
            BigText2RGB         = HighBlue,
            BigText2ShadowRGB   = ShadowBlue,

          
            ScrollText          = 'HYPE TRAIN WOO WOO',
            ScrollTextRGB       = LED.MedYellow,
            ScrollSleep         = ScrollSleep, # time in seconds to control the scrolling (0.005 is fast, 0.1 is kinda slow)
            DisplayTime         = 10,           # time in seconds to wait before exiting 
            ExitEffect          = -1           # 0=Random / 1=shrink / 2=zoom out / 3=bounce / 4=fade /5=fallingsand
            )

          LED.StarryNightDisplayText(
            Text1 = "HYPE TRAIN POINTS " + HypeTotal ,
            Text2 = HypeTotal,
            Text3 = HypeGoal + " points needed to reach the next leve", 
            RunSeconds = 60
            )                    


      #HYPE TRAIN END
      elif (MessageType == 'EVENTSUB_HYPE_TRAIN_END'):
          print("HYPE TRAIN END")
          pprint.pprint(Message)
          LED.StarryNightDisplayText(
            Text1 = "HYPE TRAIN ENDED",
            Text2 = "HYPE TRAIN ENDED",
            Text3 = "How sad for us!", 
            RunSeconds = 60
            )                    




  #---------------------------------------
  # CLIENT EVENTS                       --
  #---------------------------------------
  #PubSub to Twitch





  #---------------------------------------
  # B O T   C O M M A N D S             --
  #---------------------------------------
  #the bot will respond to these commands typed in the chat e.g. ?hello


    #----------------------------------------
    # Hello                                --
    #----------------------------------------

    @commands.command()
    async def hello(self, ctx: commands.Context):
        response = get_personal_hello_response(ctx.author.name)
        await ctx.send(response)

    #----------------------------------------
    # clock commands                       --
    #----------------------------------------

    @commands.command()
    async def clock(self, ctx: commands.Context):
        await ctx.send('Available commands: ?demotivate ?hello ?hug ?intro ?profile ?me ?retro ?starrynight ?views ?taco ?time ?uptime ?viewers ?who')
        time.sleep(4)
        await ctx.send('Available games: ?astrosmash ?blasteroids ?defender ?fallingsand ?gravity ?invaders ?outbreak ?tron')
        #time.sleep(4)
        #await ctx.send('Trigger words: hug ghosts minions police storm ')




    #----------------------------------------
    # WHO - Current Viewers                --
    #----------------------------------------
    @commands.command()
    async def who(self, ctx: commands.Context):

      if(SHOW_CHATBOT_MESSAGES == True):
        message = "Now scrolling: Most recent viewers".format(ViewerCount)
        await self.Channel.send(message)

      CommandQueue.put({"Action": "showviewers","chatusers": self.ChatUsers})
    

    #----------------------------------------
    # RetroClock                           --
    #----------------------------------------
    @commands.command()
    async def retro(self, ctx: commands.Context):

      if(SHOW_CHATBOT_MESSAGES == True):
        message = "Time for an old school retro digital display"
        await self.Channel.send(message)
        CommandQueue.put({"Action": "retrodigital", "duration": 30 })

    
    #----------------------------------------
    # Hug                                  --
    #----------------------------------------
    @commands.command()
    async def hug(self, ctx: commands.Context):
      message = "Sending hugs <3 <3 <3"
      await self.Channel.send(message)
      CommandQueue.put({"Action": "showheart"})

    @commands.command()
    async def hugs(self, ctx: commands.Context):
      message = "Sending hugs <3 <3 <3"
      await self.Channel.send(message)
      CommandQueue.put({"Action": "showheart"})



    #----------------------------------------
    # Intro                                --
    #----------------------------------------
    @commands.command()
    async def intro(self, ctx: commands.Context):
      CommandQueue.put({"Action": "showintro"})


    #----------------------------------------
    # Demotivate                           --
    #----------------------------------------
    @commands.command()
    async def demotivate(self, ctx: commands.Context):
      CommandQueue.put({"Action": "showdemotivate"})


    



    #----------------------------------------
    # Viewers                              --
    #----------------------------------------
    @commands.command()
    async def viewers(self, ctx: commands.Context):
      #SHOW VIEWERS
      
      if(SHOW_VIEWERS == True):
        GetTwitchCounts()

        if(SHOW_CHATBOT_MESSAGES == True):
          message = get_viewer_message(ViewerCount)
          await self.Channel.send(message)

        CommandQueue.put({
              "Action": "ShowTitleScreen",
              "BigText": str(ViewerCount),
              "BigTextRGB": LED.MedPurple,
              "BigTextShadowRGB": LED.ShadowPurple,
              "LittleText": "Viewers",
              "LittleTextRGB": LED.MedRed,
              "LittleTextShadowRGB": LED.ShadowRed,
              "ScrollText": 'Now Playing: ' + GameName,
              "ScrollTextRGB": LED.MedYellow,
              "ScrollSleep": ScrollSleep,
              "DisplayTime": 1,
              "ExitEffect": 5,
              "LittleTextZoom": 1
          })



    #----------------------------------------
    # Time                                 --
    #----------------------------------------
    @commands.command()
    async def time(self, ctx: commands.Context):

      try:
        # Stop existing clock (if any), then start new one
        CommandQueue.put({"Action": "stopclock"})
        
        #Formulate the command.      
        CommandQueue.put({
            "Action": "showclock",
            "Style": 1,
            "Zoom": 3 if StreamActive else 2,
            "duration": 10,  # minutes
            "Delay": 10
        })

      except Exception as e:
        print(f"[ERROR] Failed to send clock command: {e}")
        traceback.print_exc()



    '''
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

      if (Followers > 9999):
        BigTextZoom = 2
      else:
        BigTextZoom = 3


      CommandQueue.put({
              "Action": "ShowTitleScreen",
              "BigText": str(Followers),
              "BigTextRGB": LED.MedPurple,
              "BigTextShadowRGB": LED.ShadowPurple,
              "BigTextZoom" : 3,
              "LittleText": "Follows",
              "LittleTextRGB": LED.MedRed,
              "LittleTextShadowRGB": LED.ShadowRed,
              "ScrollText": '',
              "ScrollTextRGB": LED.MedYellow,
              "ScrollSleep": ScrollSleep,
              "DisplayTime": 1,
              "ExitEffect": 5,
              "LittleTextZoom": 1
          })




    @commands.command()
    async def followers(self, ctx: commands.Context):
      
      #SHOW FOLLOWERS
      print("SHOW_FOLLOWERS:",SHOW_FOLLOWERS)
      if(SHOW_FOLLOWERS == True):
        GetTwitchCounts()

        if (Followers > 9999):
          BigTextZoom = 2
        else:
          BigTextZoom = 3


        if(SHOW_CHATBOT_MESSAGES == True):
          message = "{} viewers follow this channel. Gotta get those numbers up!".format(Followers)
          await self.Channel.send(message)


        CommandQueue.put({
              "Action": "ShowTitleScreen",
              "BigText": str(Followers),
              "BigTextRGB": LED.MedPurple,
              "BigTextShadowRGB": LED.ShadowPurple,
              "BigTextZoom" : 3,
              "LittleText": "Follows",
              "LittleTextRGB": LED.MedRed,
              "LittleTextShadowRGB": LED.ShadowRed,
              "ScrollText": '',
              "ScrollTextRGB": LED.MedYellow,
              "ScrollSleep": ScrollSleep,
              "DisplayTime": 5,
              "ExitEffect": 0,
              "LittleTextZoom": 1
          })


      else:
        if(SHOW_CHATBOT_MESSAGES == True):
          message = "{} has decided to not show followers.".format(BROADCASTER_CHANNEL)
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


        if (Subs > 9999):
          BigTextZoom = 2
        else:
          BigTextZoom = 3


        CommandQueue.put({
              "Action": "ShowTitleScreen",
              "BigText": str(Subs),
              "BigTextRGB": LED.MedPurple,
              "BigTextShadowRGB": LED.ShadowPurple,
              "BigTextZoom" : 3,
              "LittleText": "Subscribers",
              "LittleTextRGB": LED.MedRed,
              "LittleTextShadowRGB": LED.ShadowRed,
              "ScrollText": '',
              "ScrollTextRGB": LED.MedYellow,
              "ScrollSleep": ScrollSleep,
              "DisplayTime": 5,
              "ExitEffect": 0,
              "LittleTextZoom": 1
          })



      else:
        if(SHOW_CHATBOT_MESSAGES == True):
          message = "Well, you are viewing.  I am viewing.  {} is viewing.  That's at least three.  The rest is a mystery to me.".format(CHANNEL)
          await self.Channel.send(message)

    '''


    #----------------------------------------
    # Uptime                               --
    #----------------------------------------
      
    @commands.command()
    async def uptime(self, ctx: commands.Context):
      #SHOW UPTIME
      if(SHOW_CHATBOT_MESSAGES == True):
        message = "{} has been streaming for {} HHMMSS".format(BROADCASTER_CHANNEL,StreamDurationHHMMSS)
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
      if(SHOW_CHATBOT_MESSAGES == True):
        message = "The chat will now be displayed on the LEDarcade clock thingy.".format(BROADCASTER_CHANNEL,StreamDurationHHMMSS)
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
      CommandQueue.put({"Action": "showimagezoom",
                              "image": "CurrentProfile.png",
                              "zoommin" : 1,
                              "zoommax":100,
                              "zoomfinal" : 16,
                              "sleep" : 0.010,
                              "step"  : 1})


      #SHOW PROFILE
      if(SHOW_CHATBOT_MESSAGES == True):
        message = "Now displaying the profile pic for this channel."
        await self.Channel.send(message)


    #----------------------------------------
    # Me                                   --
    #----------------------------------------

    #Show the chat user's profile  
    @commands.command()
    async def me(self, ctx: commands.Context):
      
      
      print("THECLOCKBOT_CLIENT_ID:",THECLOCKBOT_CLIENT_ID)

      print("Get user profile info:",ctx.author.name)
      API_ENDPOINT = "https://api.twitch.tv/helix/users?login=" + ctx.author.name
      head = {
      #'Client-ID': CLIENT_ID,
      'Client-ID':  THECLOCKBOT_CLIENT_ID,
      'Authorization': 'Bearer ' +  THECLOCKBOT_ACCESS_TOKEN
      }

      #print ("URL: ",API_ENDPOINT, 'data:',head)
      r = requests.get(url = API_ENDPOINT, headers = head)
      results = r.json()
      pprint.pprint(results)
      #print(" ")

      UserProfileURL = ''
      DataDict = results.get('data','NONE')
      if (DataDict != 'NONE'):

        print("Data found.  Processing...")

        try:
          UserProfileURL = results['data'][0]['profile_image_url']

        except Exception as ErrorMessage:
          TraceMessage = traceback.format_exc()
          AdditionalInfo = "Getting CHANNEL info from API call" 
          LED.ErrorHandler(ErrorMessage,TraceMessage,AdditionalInfo)
        
        
      
      #SHOW PROFILE
      if(SHOW_CHATBOT_MESSAGES == True):
        message = "Lets take a closer look at " + ctx.author.name
        await self.Channel.send(message)

      if (UserProfileURL != ""):
        
        LED.GetImageFromURL(UserProfileURL,"UserProfile.png")
        CommandQueue.put({"Action": "showimagezoom",
                              "image": "UserProfile.png",
                              "zoommin" : 1,
                              "zoommax": 100,
                              "zoomfinal" : 16,
                              "sleep" : 0.01,
                              "step"  : 1})





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

        if (VIEW_COUNT > 9999):
          BigTextZoom = 2
        else:
          BigTextZoom = 3

        CommandQueue.put({
              "Action": "ShowTitleScreen",
              "BigText": str(VIEW_COUNT),
              "BigTextRGB": LED.MedRed,
              "BigTextShadowRGB": LED.ShadowRed,
              "BigTextZoom" : BigTextZoom,
              "LittleText": "Views",
              "LittleTextRGB": LED.MedPurple,
              "LittleTextShadowRGB": LED.ShadowPurple,
              "ScrollText": '',
              "ScrollTextRGB": LED.MedYellow,
              "ScrollSleep": ScrollSleep,
              "DisplayTime": 5,
              "ExitEffect": 0,
              "LittleTextZoom": 1
          })


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
      CommandQueue.put({"Action": "launch_dotinvaders", "duration": 10 })

    #----------------------------------------
    # GRAVITY SIM                          --
    #----------------------------------------

    @commands.command()
    async def gravity(self, ctx: commands.Context):
      #Play game GravitySim
      if(SHOW_CHATBOT_MESSAGES == True):
        message = "Lets watch comets orbiting a star"
        await self.Channel.send(message)
      CommandQueue.put({"Action": "launch_gravitysim", "duration": 10 })




    #----------------------------------------
    # OUTBREAK                             --
    #----------------------------------------

    @commands.command()
    async def outbreak(self, ctx: commands.Context):
      #Play game Outbreak
      if(SHOW_CHATBOT_MESSAGES == True):
        message = "An infection is spreading..."
        await self.Channel.send(message)
      CommandQueue.put({"Action": "launch_outbreak", "duration": 10 })


    #----------------------------------------
    # ASTROSMASH (spacedot)                --
    #----------------------------------------

    @commands.command()
    async def astrosmash(self, ctx: commands.Context):
      if(SHOW_CHATBOT_MESSAGES == True):
        message = "The sky is falling..."
        await self.Channel.send(message)
      CommandQueue.put({"Action": "launch_spacedot", "duration": 10 })



    #----------------------------------------
    # DEFENDER                             --
    #----------------------------------------

    @commands.command()
    async def defender(self, ctx: commands.Context):
      #Play game Defender
      if(SHOW_CHATBOT_MESSAGES == True):
        message = "Time to go blast some mutants"
        await self.Channel.send(message)
      CommandQueue.put({"Action": "launch_defender", "duration": 10 })



    #----------------------------------------
    # BLASTEROIDS                          --
    #----------------------------------------

    @commands.command()
    async def blasteroids(self, ctx: commands.Context):
      #Play game Blasteroids
      #if(SHOW_CHATBOT_MESSAGES == True):
      #  message = "Time to earn your wings, kid.  Blow up them space rocks!"
      #  await self.Channel.send(message)
      CommandQueue.put({"Action": "launch_blasteroids", "duration": 10 })


    #----------------------------------------
    # TRON                                 --
    #----------------------------------------

    @commands.command()
    async def tron(self, ctx: commands.Context):
      #Play game Tron
      if(SHOW_CHATBOT_MESSAGES == True):
        message = "Time for some jetbike races"
        await self.Channel.send(message)
      CommandQueue.put({"Action": "launch_tron", "duration": 10 })


    #----------------------------------------
    # FALLING SAND                         --
    #----------------------------------------

    @commands.command()
    async def fallingsand(self, ctx: commands.Context):
      #Play game FallingSand
      if(SHOW_CHATBOT_MESSAGES == True):
        message = "Watch the pretty sand fall...and explode!"
        await self.Channel.send(message)
      CommandQueue.put({"Action": "launch_fallingsand", "duration": 10 })


    #----------------------------------------
    # STARRY NIGHT CLOCK (clock style 3)   --
    #----------------------------------------

    @commands.command()
    async def starrynight(self, ctx: commands.Context):
      if(SHOW_CHATBOT_MESSAGES == True):
        message = "Enjoy the peaceful starry sky while staring at a clock"
        await self.Channel.send(message)

        CommandQueue.put({
            "Action": "showclock",
            "Style": 3,
            "Zoom": 2,
            "duration": 10,  # minutes
            "Delay": 10
        })


    #----------------------------------------
    # TACO                                 --
    #----------------------------------------

    @commands.command()
    async def taco(self, ctx: commands.Context):
      print("CHAT| TACO detected")

      message = "Is it TACO Tuesday?"
      await self.Channel.send(message)
      
      Text1       = "TACO"
      Text2       = "The Alliance for creative outreach"
      Text3       = "visit taconetwork.org to learn all about us"

      CommandQueue.put({"Action": "StarryNightDisplayText",
                         "text1": Text1,
                         "text2": Text2,
                         "text1": Text3}
                         )




    #----------------------------------------
    # DISPLAY PATREON                      --
    #----------------------------------------



   # @commands.command()
   # async def patreon(self, ctx: commands.Context):
   #   if(SHOW_CHATBOT_MESSAGES == True):
   #     message = "Now displaying the list of patrons"
   #     await self.Channel.send(message)

   #   DisplayPatreon()
   #   LED.SweepClean()


   # @commands.command()
   # async def patrons(self, ctx: commands.Context):
   #   if(SHOW_CHATBOT_MESSAGES == True):
   #     message = "Now displaying the list of patrons"
   #     await self.Channel.send(message)
      
   #   DisplayPatreon()
   #   LED.MoveAnimatedSpriteAcrossScreenStepsPerFrame(
   #     LED.PacManRightSprite,
   #     Position      = 'top',
   #     Vadjust       = 0 ,
   #     direction     = "right",
   #     StepsPerFrame = 3,
   #     ZoomFactor    = 3,
   #     sleep         = 0.02 
   #     )






#------------------------------------------------
# Bot functions
#------------------------------------------------








# bot.run() is blocking and will stop execution of any below code here until stopped or closed.
#twitch = Twitch('nxzwcicyp9ytl6m7b94ek7e9x79cw0', '2p433nc5plbcqnzwy9ivt56fo0tpww')




#curl -X GET 'https://api.twitch.tv/helix/channels?broadcaster_id=141981764' \
#-H 'Authorization: Bearer 2gbdx6oar67tqtcmt49t3wpcgycthx' \
#-H 'Client-Id: wbmytr93xzw8zbg0p1izqyzzc5mbiz'



    
    



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
    global BROADCASTER_ID
    #Follower Info
    global Followers      
    global Subs

    
    #----------------------------------------
    # GET USER INFO - ACTIVE STREAM
    #----------------------------------------
    print ("GetTwitchCounts| Getting USER info")
    API_ENDPOINT = "https://api.twitch.tv/helix/streams?user_login=" + BROADCASTER_CHANNEL
    head = {
    #'Client-ID': CLIENT_ID,
    'Client-ID': CLOCKBOT_X_CLIENT_ID,
    'Authorization': 'Bearer ' +  CLOCKBOT_X_ACCESS_TOKEN
    }
    print ("GetTwitchCounts| URL: ",API_ENDPOINT, 'data:',head)
    r = requests.get(url = API_ENDPOINT, headers = head)
    results = r.json()
    #pprint.pprint(results)
    #print(" ")

    if (r.status_code == 200):
      print("GetTwitchCounts| Data found.  Processing...")

      try:
        StreamStartedAt = results['data'][0]['started_at']
        StreamType      = results['data'][0]['type']
        ViewerCount     = results['data'][0]['viewer_count']
        StreamActive    = True

        if(StreamActive) == False:
          StreamActive = True
          print("** STREAM NOW ACTIVE **")
          #twitch dates are special format, and in UTC
          #Convert to datetime (timezone naive)
          StreamStartedDateTime = datetime.strptime(StreamStartedAt, '%Y-%m-%dT%H:%M:%SZ')
          hh,mm,ss, StreamDurationHHMMSS = LED.CalculateElapsedTime(StreamStartedDateTime)
          print("GetTwitchCounts| Stream Duration:",StreamDurationHHMMSS)

      except Exception as ErrorMessage:
        TraceMessage = traceback.format_exc()
        AdditionalInfo = "Getting USER info from API call" 
        LED.ErrorHandler(ErrorMessage,TraceMessage,AdditionalInfo)
        pprint.pprint(results)
        StreamActive   = False

    else:
      print("GetTwitchCounts| Stream NOT active")
      StreamActive = False  
      StreamDurationHHMMSS = '000000'


    '''
    #----------------------------------------
    # Follower Count
    #----------------------------------------
    print("Get FOLLOWER information")
    API_ENDPOINT = "https://api.twitch.tv/helix/channels/followers?broadcaster_id=" + BROADCASTER_USER_ID
    head = {
    'Client-ID': CLOCKBOT_X_CLIENT_ID,
    'Authorization': 'Bearer ' +  CLOCKBOT_X_ACCESS_TOKEN
    }

    #print ("URL: ",API_ENDPOINT, 'data:',head)
    r = requests.get(url = API_ENDPOINT, headers = head)
    #pp.pprint(r.content)

    try:
      if (r.status_code == 200) and ('total' in results):
        print("Data found.  Processing...")
    
        results = r.json()
        Followers = results['total']
        pprint.pprint(results)
        print("")
      else:
        print("No followers found")


    except Exception as ErrorMessage:
      TraceMessage = traceback.format_exc()
      AdditionalInfo = "Getting FOLLOWER info from API call." + " (BROADCASTER_USER_ID:" + BROADCASTER_USER_ID + ")"
      pprint.pprint(results)
      LED.ErrorHandler(ErrorMessage,TraceMessage,AdditionalInfo)
    '''


    #----------------------------------------
    # Subscriber Count
    #----------------------------------------
    print("Get SUBSCRIBER information")
    API_ENDPOINT = "https://api.twitch.tv/helix/subscriptions?broadcaster_id=" + BROADCASTER_ID
    head = {
    #'Client-ID': CLIENT_ID,
    'Client-ID': CLOCKBOT_X_CLIENT_ID,
    'Authorization': 'Bearer ' +  CLOCKBOT_X_ACCESS_TOKEN
    }

    #print ("URL: ",API_ENDPOINT, 'data:',head)
    r = requests.get(url = API_ENDPOINT, headers = head)

    try:
      if (r.status_code == 200) and ('total' in results):
        print("Data found.  Processing...")
        results = r.json()
        Subs = results['total']
      else:
        print("No subscriber info found")


    except Exception as ErrorMessage:
      TraceMessage = traceback.format_exc()
      AdditionalInfo = "Getting SUBSCRIBER info from API call - This usually means your account does not have permission, or you are not an affiliate/partner." 
      pprint.pprint(r.content)
      LED.ErrorHandler(ErrorMessage,TraceMessage,AdditionalInfo)
      





import requests
import traceback
from datetime import datetime


# Globals assumed to be defined somewhere else
CLOCKBOT_X_CLIENT_ID = ''
CLOCKBOT_X_SECRET = ''
CLOCKBOT_X_ACCESS_TOKEN = ''
BROADCASTER_CHANNEL = ''
BROADCASTER_ID = ''

GameName = ''
Title = ''
PROFILE_IMAGE_URL = ''
VIEW_COUNT = ''
StreamStartedAt = ''
StreamStartedDateTime = ''
StreamDurationHHMMSS = ''
StreamType = ''
ViewerCount = 0
StreamActive = False
Followers = 0
HypeTrainStartTime = ''
HypeTrainExpireTime = ''
HypeTrainGoal = ''
HypeTrainLevel = 0
HypeTrainTotal = ''


def GetBasicTwitchInfo():
    global CLOCKBOT_X_ACCESS_TOKEN, GameName, Title, PROFILE_IMAGE_URL, VIEW_COUNT
    global StreamStartedAt, StreamStartedDateTime, StreamDurationHHMMSS, StreamType, ViewerCount, StreamActive
    global Followers, HypeTrainStartTime, HypeTrainExpireTime, HypeTrainGoal, HypeTrainLevel, HypeTrainTotal

    print("--GetBasicTwitchInfo--")

    # Get OAuth Token
    print("Get OAUTH ACCESS Token")
    token_url = "https://id.twitch.tv/oauth2/token"
    token_data = {
        'client_id': CLOCKBOT_X_CLIENT_ID,
        'client_secret': CLOCKBOT_X_SECRET,
        'grant_type': 'client_credentials'
    }
    token_headers = {'Content-Type': 'application/x-www-form-urlencoded'}

    token_resp = requests.post(url=token_url, data=token_data, headers=token_headers)
    print("Status Code:", token_resp.status_code)
    print("Response Text:", token_resp.text)

    try:
        token_json = token_resp.json()
        CLOCKBOT_X_ACCESS_TOKEN = token_json.get('access_token', '')
        if not CLOCKBOT_X_ACCESS_TOKEN:
            print("ERROR: access_token not found")
            return
    except requests.exceptions.JSONDecodeError:
        print("ERROR: Failed to parse token response")
        return

    # Get Channel Info
    print("Get CHANNEL info")
    user_url = f"https://api.twitch.tv/helix/users?login={BROADCASTER_CHANNEL}"
    headers = {
        'Client-ID': CLOCKBOT_X_CLIENT_ID,
        'Authorization': f'Bearer {CLOCKBOT_X_ACCESS_TOKEN}'
    }

    user_resp = requests.get(url=user_url, headers=headers)
    print("Status Code:", user_resp.status_code)
    print("Response Text:", user_resp.text)

    try:
        user_data = user_resp.json().get('data', [{}])[0]
        PROFILE_IMAGE_URL = user_data.get('profile_image_url', '')
        VIEW_COUNT = user_data.get('view_count', '')
        broadcaster_id = user_data.get('id', '')
        if broadcaster_id:
            global BROADCASTER_ID
            BROADCASTER_ID = broadcaster_id
    except Exception as e:
        LED.ErrorHandler(e, traceback.format_exc(), "Getting CHANNEL info")
        return

    # Get Broadcaster Info
    print("Get BROADCASTER info")
    broadcast_url = f"https://api.twitch.tv/helix/channels?broadcaster_id={BROADCASTER_ID}"
    broadcast_resp = requests.get(url=broadcast_url, headers=headers)
    print("Status Code:", broadcast_resp.status_code)
    print("Response Text:", broadcast_resp.text)

    try:
        broadcast_data = broadcast_resp.json().get('data', [{}])[0]
        GameName = broadcast_data.get('game_name', '')
        Title = broadcast_data.get('title', '')
    except Exception as e:
        LED.ErrorHandler(e, traceback.format_exc(), "Getting BROADCASTER info")


    # Check Stream Status
    print("Check STREAM STATUS")
    stream_url = f"https://api.twitch.tv/helix/streams?user_id={BROADCASTER_ID}"
    stream_resp = requests.get(url=stream_url, headers=headers)
    print("Status Code:", stream_resp.status_code)
    print("Response Text:", stream_resp.text)
    
    try:
        stream_data = stream_resp.json().get('data', [])
        if stream_data:
            StreamActive = True
            stream_info = stream_data[0]
            StreamStartedAt = stream_info.get('started_at', '')
            StreamType = stream_info.get('type', '')
            ViewerCount = stream_info.get('viewer_count', 0)

            if StreamStartedAt:
                StreamStartedDateTime = datetime.strptime(StreamStartedAt, '%Y-%m-%dT%H:%M:%SZ')
                hh, mm, ss, StreamDurationHHMMSS = LED.CalculateElapsedTime(StreamStartedDateTime)
        else:
            StreamActive = False
    except Exception as e:
        LED.ErrorHandler(e, traceback.format_exc(), "Checking STREAM status")
        StreamActive = False



    # Stream Summary Output
    print("---------------------------------------")
    print("Title:", Title)
    print("GameName:", GameName)
    print("StreamStartedAt:", StreamStartedAt)
    print("StreamDurationHHMMSS:", StreamDurationHHMMSS)
    print("StreamType:", StreamType)
    print("ViewerCount:", ViewerCount)
    print("Followers:", Followers)
    print("---------------------------------------")



def GetBasicTwitchInfo_OLD():
    
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
    # GET ACCESS TOKEN
    #----------------------------------------
    print("Get OAUTH ACCESS Token")
    API_ENDPOINT = "https://id.twitch.tv/oauth2/token"
    head = {
    'client_id': CLOCKBOT_X_CLIENT_ID,
    'client_secret' : CLOCKBOT_X_SECRET,
    'grant_type' : 'client_credentials'
    }

    print ("URL: ",API_ENDPOINT, 'data:',head)
    r = requests.get(url = API_ENDPOINT, headers = head)

    print("Status Code:", r.status_code)
    print("Response Headers:", r.headers)
    print("Response Text:", r.text)


    results = r.json()
    pprint.pprint(results)
    print(" ")
    



  

    #----------------------------------------
    # GET CHANNEL INFO
    #----------------------------------------
    print("Get CHANNEL info")
    API_ENDPOINT = "https://api.twitch.tv/helix/users?login=" + BROADCASTER_CHANNEL
    head = {
    #'Client-ID': CLIENT_ID,
    'Client-ID': CLOCKBOT_X_CLIENT_ID,
    'Authorization': 'Bearer ' +  CLOCKBOT_X_ACCESS_TOKEN
    }

    print ("URL: ",API_ENDPOINT, 'data:',head)
    r = requests.get(url = API_ENDPOINT, headers = head)
    results = r.json()

    #check for expired oauth tokens
    if r.status_code == 401:
      print("Unauthorized access. Refreshing Credentials")
      GetAccessTokenUsingRefreshToken_TheClockBot()
    else:
      #pprint.pprint(results)
      DataDict = results.get('data','NONE')
      if(DataDict == "NONE"):
        print("")
        print("")
        print("========================================================")
        print("TWITCH ERROR - Could not extract data from CHANNEL info") 
        print("")
        print(results)
        print(API_ENDPOINT)
        print(head)
        print("========================================================")
        print("")
        print("")
        return
      else:
      #if results['data']:
        print("Data found.  Processing...")

        try:
          BROADCASTER_USER_ID = results['data'][0]['id']
          #BROADCASTER_ID      = BROADCASTER_USER_ID
          PROFILE_IMAGE_URL   = results['data'][0]['profile_image_url']
          VIEW_COUNT          = results['data'][0]['view_count']

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
    #'Client-ID': CLIENT_ID,
    'Client-ID': CLOCKBOT_X_CLIENT_ID,
    'Authorization': 'Bearer ' +  CLOCKBOT_X_ACCESS_TOKEN
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
        Title           = (results['data'][0]['title'].encode('ascii','ignore')).decode()
        

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
    #'Client-ID': CLIENT_ID,
    'Client-ID': CLOCKBOT_X_CLIENT_ID,

    'Authorization': 'Bearer ' +  CLOCKBOT_X_ACCESS_TOKEN
    }

    #print ("URL: ",API_ENDPOINT, 'data:',head)
    r = requests.get(url = API_ENDPOINT, headers = head)
    results = r.json()
    #pprint.pprint(results)

    DataDict = results.get('data','NONE')
    if (DataDict != 'NONE'):
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



    
    



#----------------------------------------
#-- Generic Functions                  --
#----------------------------------------



def ConvertDate(TheDate):
  #take a funky twitch 3339 style date and convert it to a python datetime UTC
  StringDate = TheDate
  NewDate = StringDate[0:10]+ ' ' + StringDate[11:19]
  NewDate = datetime.strptime(NewDate, '%Y-%m-%d %H:%M:%S')
  NewDate.replace(tzinfo=timezone.utc)


  return NewDate



#----------------------------------------
#-- FILE ACCESS Functions              --
#----------------------------------------

def Twitch_LoadConfigFiles():
      
  #global LEDARCADE_APP_ACCESS_TOKEN
  #global LEDARCADE_APP_CLIENT_ID
  #global LEDARCADE_APP_CLIENT_SECRET
  
  global BROADCASTER_CHANNEL
  global CHANNEL_BIG_TEXT
  global CHANNEL_LITTLE_TEXT
  
  global BROADCASTER_USER_ID
  global BROADCASTER_ID
  global THECLOCKBOT_CLIENT_ID
  global THECLOCKBOT_USER_ID
  global THECLOCKBOT_SECRET
  global THECLOCKBOT_CHANNEL
  global THECLOCKBOT_CODE
  global THECLOCKBOT_ACCESS_TOKEN
  global THECLOCKBOT_REFRESH_TOKEN
  global CLOCKBOT_X_CLIENT_ID
  global CLOCKBOT_X_SECRET
  global CLOCKBOT_X_CODE
  global CLOCKBOT_X_ACCESS_TOKEN
  global CLOCKBOT_X_REFRESH_TOKEN

  global PATREON_CLIENT_ID
  global PATREON_CLIENT_SECRET
  global PATREON_CREATOR_ACCESS_TOKEN

  global SHOW_VIEWERS
  global SHOW_FOLLOWERS
  global SHOW_SUBS
  global SHOW_VIEWS
  global SHOW_CHATBOT_MESSAGES
  global TWITCH_WEBHOOK_URL
  global TWITCH_WEBHOOK_SECRET
  global PATREON_WEBHOOK_URL
  global PATREON_WEBHOOK_SECRET

  
  
  print ("--Load Twitch Keys--")
  print("KeyConfig.ini")
  if (os.path.exists(KeyConfigFileName)):

    print ("Config file (",KeyConfigFileName,"): found")
    KeyFile = ConfigParser()
    KeyFile.read(KeyConfigFileName)

    #Get tokens
    BROADCASTER_CHANNEL = KeyFile.get("KEYS","BROADCASTER_CHANNEL")
    CHANNEL_BIG_TEXT    = KeyFile.get("KEYS","CHANNEL_BIG_TEXT")
    CHANNEL_LITTLE_TEXT = KeyFile.get("KEYS","CHANNEL_LITTLE_TEXT")

    BROADCASTER_USER_ID     = KeyFile.get("KEYS","BROADCASTER_USER_ID")        #Same as Broadcaster_ID
    BROADCASTER_ID          = KeyFile.get("KEYS","BROADCASTER_ID") #Same as UserID
    #LEDARCADE_APP_ACCESS_TOKEN  = KeyFile.get("KEYS","LEDARCADE_APP_ACCESS_TOKEN")  
    #REFRESH_TOKEN           = KeyFile.get("KEYS","REFRESH_TOKEN")
    #LEDARCADE_APP_CLIENT_ID     = KeyFile.get("KEYS","LEDARCADE_APP_CLIENT_ID")      #CLIENT_ID     of the twitch connected app (ad defined at Twitch Developer site)
    #LEDARCADE_APP_CLIENT_SECRET = KeyFile.get("KEYS","LEDARCADE_APP_CLIENT_SECRET")  #CLIENT_SECRET of the twitch connected app (ad defined at Twitch Developer site)
    

    #Webhook URL
    TWITCH_WEBHOOK_URL     = KeyFile.get("KEYS","TWITCH_WEBHOOK_URL")
    TWITCH_WEBHOOK_SECRET  = KeyFile.get("KEYS","TWITCH_WEBHOOK_SECRET")
    

    #Patreon
    PATREON_CLIENT_ID            = KeyFile.get("KEYS","PATREON_CLIENT_ID")      
    PATREON_CLIENT_SECRET        = KeyFile.get("KEYS","PATREON_CLIENT_SECRET")      
    PATREON_CREATOR_ACCESS_TOKEN = KeyFile.get("KEYS","PATREON_CREATOR_ACCESS_TOKEN")      
    PATREON_WEBHOOK_URL          = KeyFile.get("KEYS","PATREON_WEBHOOK_URL")
    PATREON_WEBHOOK_SECRET       = KeyFile.get("KEYS","PATREON_WEBHOOK_URL")


    #Bot specific connection info
    #in case we want a bot to connect separately, or to other channels
    THECLOCKBOT_CLIENT_ID          = KeyFile.get("KEYS","THECLOCKBOT_CLIENT_ID")  
    THECLOCKBOT_USER_ID            = KeyFile.get("KEYS","THECLOCKBOT_USER_ID")  
    THECLOCKBOT_SECRET             = KeyFile.get("KEYS","THECLOCKBOT_SECRET")  
    THECLOCKBOT_CHANNEL            = KeyFile.get("KEYS","THECLOCKBOT_CHANNEL")  
    THECLOCKBOT_CODE               = KeyFile.get("KEYS","THECLOCKBOT_CODE")  
    THECLOCKBOT_ACCESS_TOKEN       = KeyFile.get("KEYS","THECLOCKBOT_ACCESS_TOKEN")  
    THECLOCKBOT_REFRESH_TOKEN      = KeyFile.get("KEYS","THECLOCKBOT_REFRESH_TOKEN")  
    CLOCKBOT_X_ACCESS_TOKEN        = KeyFile.get("KEYS","CLOCKBOT_X_ACCESS_TOKEN")  
    CLOCKBOT_X_REFRESH_TOKEN       = KeyFile.get("KEYS","CLOCKBOT_X_REFRESH_TOKEN")  
    CLOCKBOT_X_CLIENT_ID           = KeyFile.get("KEYS","CLOCKBOT_X_CLIENT_ID")     
    CLOCKBOT_X_SECRET              = KeyFile.get("KEYS","CLOCKBOT_X_SECRET")     
    CLOCKBOT_X_CODE                = KeyFile.get("KEYS","CLOCKBOT_X_CODE")     


    print("BROADCASTER_CHANNEL: ",BROADCASTER_CHANNEL)   
    print("CHANNEL_BIG_TEXT:    ",CHANNEL_BIG_TEXT)   
    print("CHANNEL_LITTLE_TEXT: ",CHANNEL_LITTLE_TEXT)   
    print("BROADCASTER_USER_ID: ",BROADCASTER_USER_ID)
    print("BROADCASTER_ID:      ",BROADCASTER_ID)
    #print("LEDARCADE_APP_CLIENT_ID: ",LEDARCADE_APP_CLIENT_ID)
    #print("LEDARCADE_APP_CLIENT_SECRET: ",LEDARCADE_APP_CLIENT_SECRET)
    #print("LEDARCADE_APP_ACCESS_TOKEN: ",LEDARCADE_APP_ACCESS_TOKEN)
    
    print("")
    #print("PATREON_CLIENT_ID:            ",PATREON_CLIENT_ID)
    #print("PATREON_CLIENT_SECRET:        ",PATREON_CLIENT_SECRET)
    #print("PATREON_CREATOR_ACCESS_TOKEN: ",PATREON_CREATOR_ACCESS_TOKEN)
    print("")
    
    print("THECLOCKBOT_CODE:           ",THECLOCKBOT_CODE)
    print("THECLOCKBOT_ACCESS_TOKEN:   ",THECLOCKBOT_ACCESS_TOKEN)
    print("THECLOCKBOT_REFRESH_TOKEN:  ",THECLOCKBOT_REFRESH_TOKEN)

    print("THECLOCKBOT_CLIENT_ID:      ",THECLOCKBOT_CLIENT_ID)   
    print("THECLOCKBOT_USER_ID:        ",THECLOCKBOT_USER_ID)   
    print("THECLOCKBOT_SECRET:         ",THECLOCKBOT_SECRET)   
    print("THECLOCKBOT_CHANNEL:        ",THECLOCKBOT_CHANNEL)   
    print("CLOCKBOT_X_CLIENT_ID:       ",CLOCKBOT_X_CLIENT_ID)
    print("CLOCKBOT_X_SECRET:          ",CLOCKBOT_X_SECRET)
    print("CLOCKBOT_X_CODE:            ",CLOCKBOT_X_CODE)

    print("TWITCH_WEBHOOK_URL:    ",TWITCH_WEBHOOK_URL)
    print("TWITCH_WEBHOOK_SECRET: ",TWITCH_WEBHOOK_SECRET)
    print("PATREON_WEBHOOK_URL:   ",PATREON_WEBHOOK_URL)
    print("PATREON_WEBHOOK_SECRET:",PATREON_WEBHOOK_SECRET)

    print ("--------------------")
    print (" ")

  else:
    #To be finished later
    print ("ERROR: Could not locate Key file (",KeyConfigFileName,"). Create a file and make sure to pupulate it with your own keys.")



  print ("--Load Personal Configurations--")
  print("MyConfig.ini")

  if (os.path.exists(MyConfigFileName)):

    print ("Config file (",MyConfigFileName,"): found")
    MyConfigFile = ConfigParser()
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
      KeyConfigFile.write("  BROADCASTER_USER_ID = 12345\n")
      KeyConfigFile.write("  BROADCASTER_ID      = 12345 (same as BROADCASTER_UserID)\n")
      
      #KeyConfigFile.write("  LEDARCADE_APP_REDIRECT_URL    = http://localhost\n")
      KeyConfigFile.write("  TWITCH_WEBHOOK_URL    = https://eventsub.something.packetriot.net\n")
      KeyConfigFile.write("  TWITCH_WEBHOOK_SECRET = SomeSecretYouMakeUp\n")
      KeyConfigFile.write("\n")
      KeyConfigFile.write("  THECLOCKBOT_CODE         = abcde\n")
      KeyConfigFile.write("  THECLOCKBOT_ACCESS_TOKEN = abcde\n")
      KeyConfigFile.write("  THECLOCKBOT_REFRESH_TOKEN = abcde\n")
      KeyConfigFile.write("  CLOCKBOT_X_ACCESS_TOKEN  = abcde\n")
      KeyConfigFile.write("  CLOCKBOT_X_CLIENT_ID     = 123456\n")
      KeyConfigFile.write("  CLOCKBOT_X_SECRET        = abcdefg\n")
      KeyConfigFile.write("  CLOCKBOT_X_CODE          = abcdefg\n")
      KeyConfigFile.write("\n")
      KeyConfigFile.write("  PATREON_CLIENT_ID             = ABCDE\n")
      KeyConfigFile.write("  PATREON_CLIENT_SECRET         = EFJHI\n")
      KeyConfigFile.write("  PATREON_CREATOR_ACCESS_TOKEN  = EFJHI\n")
      KeyConfigFile.write("  PATREON_WEBHOOK_URL    = https://patreon.something.packetriot.net\n")
      KeyConfigFile.write("  PATREON_WEBHOOK_SECRET = SomeSecretYouMakeUp\n")
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
  LED.TheMatrix.brightness = StreamBrightness
  LED.ScrollCreditImage("credits.png",ScrollSleep=0.04)
  LED.TheMatrix.brightness = MaxBrightness




'''
These are part of EventSub and will be removed.


#----------------------------------------
#-- ASYNCIO Functions                  --
#----------------------------------------




#this allows us to collect data from asynchronous generators
#Generated by CHATGPT
async def collect_data_from_async_gen(async_gen):
    data = []
    async for item in async_gen:
        data.append(item)
    return data



# this will be called whenever someone follows the target channel
async def on_stream_online(data: dict):
    print("**** STREAM ONLINE ****")
    EventQueue.put(('EVENTSUB_STREAM_ONLINE',data))


#v3
async def on_follow(data: dict):
    print("**** follow detected ****")
    EventQueue.put(('EVENTSUB_FOLLOW',data))

async def on_subscribe(data: dict):
    await EventQueue.put(('EVENTSUB_SUBSCRIBE',data))

async def on_channel_cheer(data:dict):
    await EventQueue.put(('EVENTSUB_CHEER',data))

async def on_channel_points_redemption(data:dict):
    EventQueue.put(('EVENTSUB_POINTS_REDEMPTION',data))

async def on_hype_train_begin(data:dict):
    EventQueue.put(('EVENTSUB_HYPE_TRAIN_BEGIN',data))

async def on_hype_train_progress(data:dict):
    EventQueue.put(('EVENTSUB_HYPE_TRAIN_PROGRESS',data))


async def on_hype_train_end(data:dict):
    EventQueue.put(('EVENTSUB_HYPE_TRAIN_END',data))

async def on_channel_subscription_gift(data:dict):
    EventQueue.put(('EVENTSUB_SUBSCRIPTION_GIFT',data))

'''

#----------------------------------------
#-- MULTIPROCESSING Functions          --
#----------------------------------------

async def TwitchEventSub(EventQueue):

  print("ASYNC| ")
  print("ASYNC| ")
  print("ASYNC| Starting TwitchEventSub")
  print("ASYNC| ")
  
  print("ASYNC| Authenticating with Twitch using ClockbotX ID and Secret")
  twitch = await Twitch(CLOCKBOT_X_CLIENT_ID, CLOCKBOT_X_SECRET)
  await twitch.authenticate_app([])



  #twitch.get_users returns an async_generator
  #and must be handled differently than in TwitchAPI3
  print("ASYNC| Get list of users")
  async_results = twitch.get_users(logins=[BROADCASTER_CHANNEL])
  
  #This will create a list of twitch objects
  #we have to go into the object to get the ID that we want (the first one)
  print("ASYNC| Processing list of users to get BroadCasterUserID")
  uid_data = await collect_data_from_async_gen(async_results)
  BroadCasterUserID = uid_data[0].id
  print("ASYNC| BroadCasterUserID:",BroadCasterUserID)
  






  # basic setup, will run on port 8080 and a reverse proxy takes care of the https and certificate
  #EventSub comes from TWITCHAPI
  #TwitchAPI v3
  #hook = EventSubWebhook(TWITCH_WEBHOOK_URL, CLOCKBOT_X_CLIENT_ID, 5051, twitch)
  
  #TwitchAPI v4
  print("ASYNC| Creating webhooks")
  hook = EventSubWebhook(TWITCH_WEBHOOK_URL, 5051, twitch)
  
  # unsubscribe from all to get a clean slate
  print("ASYNC| unscubscribing to all previous webhooks")
  await hook.unsubscribe_all()
  
  # start client
  hook.start()
  print("ASYNC| ")
  print('ASYNC| --Subscribing to EVENTSUB hooks--')
  print("ASYNC| BroadCasterUserID:   ",BroadCasterUserID)
  print("ASYNC| TWITCH_WEBHOOK_URL:  ",TWITCH_WEBHOOK_URL)
  print("ASYNC| CLOCKBOT_X_CLIENT_ID:",CLOCKBOT_X_CLIENT_ID)
  print("ASYNC| ")


  # 2023-09-26 TwitchAPI 4 requires an actual twitch user id (we can use BroadcasterID)
  # in order to get new follower notifications
  print("ASYNC| Channel follows")
  await hook.listen_channel_follow_v2(BroadCasterUserID, BroadCasterUserID, on_follow)
  
  
  
  #print("EVENTSUB: Stream goes live")
  #await hook.listen_stream_online(BroadCasterUserID, on_stream_online)


  #print("ASYNC| Channel subscriptions")
  #try:
  #  await hook.listen_channel_subscribe(BroadCasterUserID, on_subscribe)

  #except Exception as ErrorMessage:
  #  TraceMessage = traceback.format_exc()
  #  AdditionalInfo = "ERROR subscribing to listen_channel_subscribe" 
  #  LED.ErrorHandler(ErrorMessage,TraceMessage,AdditionalInfo)


  print("EVENTSUB: Bits thrown")
  await hook.listen_channel_cheer(BroadCasterUserID,on_channel_cheer)
 
  
  #print("EVENTSUB: Channel points redeemed")
  #hook.listen_channel_points_custom_reward_redemption_add(BroadCasterUserID,on_channel_points_redemption)

  #print("EVENTSUB: Hype Train begin")
  #hook.listen_hype_train_begin(BroadCasterUserID, on_hype_train_begin)

  #print("EVENTSUB: Hype Train progress")
  #hook.listen_hype_train_progress(BroadCasterUserID, on_hype_train_progress)

  #print("EVENTSUB: Hype Train end")
  #hook.listen_hype_train_end(BroadCasterUserID, on_hype_train_end)

  #print("EVENTSUB: subscription gifted")
  #hook.listen_channel_subscription_gift(BroadCasterUserID,on_channel_subscription_gift)

 
  print("ASYNC| ")
  print("ASYNC| ")
  print("ASYNC| ")
  print("ASYNC| ")
  



def PatreonWebHook(EventQueue):

  #we create a Flask app, assign a default function (Receiver) and use it to write to the 
  #multiprocessing Queue.  This allows the Twitch Bot to pop the queue.

  app = Flask(__name__)
  @app.route('/', methods=['POST'])
  def Receiver():
    
    MyData = request.json
    #MyData = request.get_json(silent=True)
    #pprint.pprint(MyData)     
    #print("DATA: ", request.json)
    EventQueue.put(('PATREON',MyData))
    
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
  app.run(port=5050)
  





def GetAccessTokenUsingOAUTHCode_TheClockBot():
  global THECLOCKBOT_CLIENT_ID
  global THECLOCKBOT_USER_ID
  global THECLOCKBOT_SECRET
  global THECLOCKBOT_CODE
  global THECLOCKBOT_ACCESS_TOKEN
  global THECLOCKBOT_REFRESH_TOKEN
 
 
  print ("-- GET OAUTH TOKEN --")
  API_ENDPOINT = "https://id.twitch.tv/oauth2/token"

  headers = {
      'Content-Type': 'application/x-www-form-urlencoded',
  }

  payload = {
      'grant_type': 'authorization_code',
      'client_id': THECLOCKBOT_CLIENT_ID,
      'client_secret': THECLOCKBOT_SECRET,
      'code': THECLOCKBOT_CODE,
      'redirect_uri': 'http://localhost'
  }

  try:
    print ("URL: ",API_ENDPOINT, 'data:',headers, 'Payload:',payload)
    r = requests.post(url = API_ENDPOINT, headers = headers,params=payload)
    results = r.json()
    pprint.pprint(results)
    #print(" ")
  except Exception as ErrorMessage:
      TraceMessage = traceback.format_exc()
      AdditionalInfo = "ERROR ACCESSING TWITCH OAUTH2 API" 
      LED.ErrorHandler(ErrorMessage,TraceMessage,AdditionalInfo)


  DataDict = results.get('access_token','NONE')
  if(DataDict == "NONE"):
    print("")
    print("")
    print("=================================================================================")
    print("TWITCH ERROR - Could not extract ACCESS TOKEN from OAUTH results") 
    print("")
    print(results)
    print("=================================================================================")
    print("")
    print("")
  else:
    print("")
    print("ACCESS GRANTED...processing data results")
    print("")

    try:
      THECLOCKBOT_ACCESS_TOKEN   = results['access_token']
      THECLOCKBOT_REFRESH_TOKEN  = results['refresh_token']

    except Exception as ErrorMessage:
      TraceMessage = traceback.format_exc()
      AdditionalInfo = "Getting ACCESS_TOKEN" 
      LED.ErrorHandler(ErrorMessage,TraceMessage,AdditionalInfo)


    print("THECLOCKBOT_CODE:         ",THECLOCKBOT_CODE)
    print("THECLOCKBOT_ACCESS_TOKEN: ",THECLOCKBOT_ACCESS_TOKEN)
    print("THECLOCKBOT_REFRESH_TOKEN:",THECLOCKBOT_REFRESH_TOKEN)

    
    #Write results to config file
    try:
        KeyFile = ConfigParser()
        KeyFile.read(KeyConfigFileName)
        KeyFile.set('KEYS','THECLOCKBOT_CODE',THECLOCKBOT_CODE)
        KeyFile.set('KEYS','THECLOCKBOT_ACCESS_TOKEN',THECLOCKBOT_ACCESS_TOKEN)
        KeyFile.set('KEYS','THECLOCKBOT_REFRESH_TOKEN',THECLOCKBOT_REFRESH_TOKEN)

        print("File:",KeyConfigFileName)

        with open(KeyConfigFileName,'w+') as UpdatedFile:
          KeyFile.write(UpdatedFile)

    except Exception as ErrorMessage:
        TraceMessage = traceback.format_exc()
        AdditionalInfo = "ACCESS_TOKEN not found in result set" 
        LED.ErrorHandler(ErrorMessage,TraceMessage,AdditionalInfo)


  print("----------------------------------------")
  print("")




def GetAccessTokenUsingRefreshToken_TheClockBot():
  global THECLOCKBOT_CLIENT_ID
  global THECLOCKBOT_USER_ID
  global THECLOCKBOT_SECRET
  global THECLOCKBOT_CODE
  global THECLOCKBOT_ACCESS_TOKEN
  global THECLOCKBOT_REFRESH_TOKEN
 
 
  print ("-- GET OAUTH TOKEN USING REFRESH TOKEN--")
  API_ENDPOINT = "https://id.twitch.tv/oauth2/token"

  headers = {
      'Content-Type': 'application/x-www-form-urlencoded',
  }

  payload = {
      'grant_type': 'refresh_token',
      'client_id': THECLOCKBOT_CLIENT_ID,
      'client_secret': THECLOCKBOT_SECRET,
      'refresh_token': THECLOCKBOT_REFRESH_TOKEN,
      'redirect_uri': 'http://localhost'
  }

  try:
    print ("URL: ",API_ENDPOINT, 'data:',headers, 'Payload:',payload)
    r = requests.post(url = API_ENDPOINT, headers = headers,params=payload)
    results = r.json()
    pprint.pprint(results)
    #print(" ")
  except Exception as ErrorMessage:
      TraceMessage = traceback.format_exc()
      AdditionalInfo = "ERROR ACCESSING TWITCH OAUTH2 API" 
      LED.ErrorHandler(ErrorMessage,TraceMessage,AdditionalInfo)


  DataDict = results.get('access_token','NONE')
  if(DataDict == "NONE"):
    print("")
    print("")
    print("=================================================================================")
    print("TWITCH ERROR - Could not extract access TOKEN from OAUTH results") 
    print("")
    print(results)
    print("=================================================================================")
    print("")
    print("")
  else:
    print("")
    print("ACCESS GRANTED...processing data results")
    print("")

    try:
      THECLOCKBOT_ACCESS_TOKEN   = results['access_token']
      THECLOCKBOT_REFRESH_TOKEN = results['refresh_token']

    except Exception as ErrorMessage:
      TraceMessage = traceback.format_exc()
      AdditionalInfo = "Getting ACCESS_TOKEN" 
      THECLOCKBOT_ACCESS_TOKEN = 'REFRESH_FAILED'
      LED.ErrorHandler(ErrorMessage,TraceMessage,AdditionalInfo)



    print("THECLOCKBOT_CODE:         ",THECLOCKBOT_CODE)
    print("THECLOCKBOT_ACCESS_TOKEN: ",THECLOCKBOT_ACCESS_TOKEN)
    print("THECLOCKBOT_REFRESH_TOKEN:",THECLOCKBOT_REFRESH_TOKEN)

    
    #Write results to config file
    try:
        KeyFile = ConfigParser()
        KeyFile.read(KeyConfigFileName)
        KeyFile.set('KEYS','THECLOCKBOT_CODE',THECLOCKBOT_CODE)
        KeyFile.set('KEYS','THECLOCKBOT_ACCESS_TOKEN',THECLOCKBOT_ACCESS_TOKEN)
        KeyFile.set('KEYS','THECLOCKBOT_REFRESH_TOKEN',THECLOCKBOT_REFRESH_TOKEN)

        print("File:",KeyConfigFileName)

        with open(KeyConfigFileName,'w+') as UpdatedFile:
          KeyFile.write(UpdatedFile)

    except Exception as ErrorMessage:
        TraceMessage = traceback.format_exc()
        AdditionalInfo = "ACCESS_TOKEN not found in result set" 
        LED.ErrorHandler(ErrorMessage,TraceMessage,AdditionalInfo)


  print("----------------------------------------")
  print("")




      
def GetAccessTokenUsingOAUTHCode_ClockBotX():
  global CLOCKBOT_X_CLIENT_ID
  global CLOCKBOT_X_SECRET
  global CLOCKBOT_X_CODE
  global CLOCKBOT_X_ACCESS_TOKEN
  global CLOCKBOT_X_REFRESH_TOKEN
 
 
  print ("-- GET OAUTH TOKEN --")
  API_ENDPOINT = "https://id.twitch.tv/oauth2/token"

  headers = {
      'Content-Type': 'application/x-www-form-urlencoded',
  }

  payload = {
      'grant_type': 'authorization_code',
      'client_id': CLOCKBOT_X_CLIENT_ID,
      'client_secret': CLOCKBOT_X_SECRET,
      'code': CLOCKBOT_X_CODE,
      'redirect_uri': 'http://localhost'
  }

  try:
    print ("URL: ",API_ENDPOINT, 'data:',headers, 'Payload:',payload)
    r = requests.post(url = API_ENDPOINT, headers = headers,params=payload)
    results = r.json()
    pprint.pprint(results)
    #print(" ")
  except Exception as ErrorMessage:
      TraceMessage = traceback.format_exc()
      AdditionalInfo = "ERROR ACCESSING TWITCH OAUTH2 API" 
      LED.ErrorHandler(ErrorMessage,TraceMessage,AdditionalInfo)


  DataDict = results.get('access_token','NONE')
  if(DataDict == "NONE"):
    print("")
    print("")
    print("=================================================================================")
    print("TWITCH ERROR - Could not extract ACCESS TOKEN from OAUTH results") 
    print("")
    print(results)
    print("=================================================================================")
    print("")
    print("")
  else:
    print("")
    print("ACCESS GRANTED...processing data results")
    print("")

    try:
      CLOCKBOT_X_ACCESS_TOKEN   = results['access_token']
      CLOCKBOT_X_REFRESH_TOKEN  = results['refresh_token']

    except Exception as ErrorMessage:
      TraceMessage = traceback.format_exc()
      AdditionalInfo = "Getting ACCESS_TOKEN" 
      LED.ErrorHandler(ErrorMessage,TraceMessage,AdditionalInfo)


    print("CLOCKBOT_X_CODE:         ",CLOCKBOT_X_CODE)
    print("CLOCKBOT_X_ACCESS_TOKEN: ",CLOCKBOT_X_ACCESS_TOKEN)
    print("CLOCKBOT_X_REFRESH_TOKEN:",CLOCKBOT_X_REFRESH_TOKEN)

    
    #Write results to config file
    try:
        KeyFile = ConfigParser()
        KeyFile.read(KeyConfigFileName)
        KeyFile.set('KEYS','CLOCKBOT_X_CODE',CLOCKBOT_X_CODE)
        KeyFile.set('KEYS','CLOCKBOT_X_ACCESS_TOKEN',CLOCKBOT_X_ACCESS_TOKEN)
        KeyFile.set('KEYS','CLOCKBOT_X_REFRESH_TOKEN',CLOCKBOT_X_REFRESH_TOKEN)

        print("File:",KeyConfigFileName)

        with open(KeyConfigFileName,'w+') as UpdatedFile:
          KeyFile.write(UpdatedFile)

    except Exception as ErrorMessage:
        TraceMessage = traceback.format_exc()
        AdditionalInfo = "ACCESS_TOKEN not found in result set" 
        LED.ErrorHandler(ErrorMessage,TraceMessage,AdditionalInfo)


  print("----------------------------------------")
  print("")





def GetAccessTokenUsingRefreshToken_ClockBotX():
  global CLOCKBOT_X_CLIENT_ID
  global CLOCKBOT_X_SECRET
  global CLOCKBOT_X_CODE
  global CLOCKBOT_X_ACCESS_TOKEN
  global CLOCKBOT_X_REFRESH_TOKEN
 
 
  print ("-- GET OAUTH TOKEN USING REFRESH TOKEN--")
  API_ENDPOINT = "https://id.twitch.tv/oauth2/token"

  headers = {
      'Content-Type': 'application/x-www-form-urlencoded',
  }

  payload = {
      'grant_type': 'refresh_token',
      'client_id': CLOCKBOT_X_CLIENT_ID,
      'client_secret': CLOCKBOT_X_SECRET,
      'refresh_token': CLOCKBOT_X_REFRESH_TOKEN,
      'redirect_uri': 'http://localhost'
  }

  try:
    print ("URL: ",API_ENDPOINT, 'data:',headers, 'Payload:',payload)
    r = requests.post(url = API_ENDPOINT, headers = headers,params=payload)
    results = r.json()
    pprint.pprint(results)
    #print(" ")
  except Exception as ErrorMessage:
      TraceMessage = traceback.format_exc()
      AdditionalInfo = "ERROR ACCESSING TWITCH OAUTH2 API" 
      LED.ErrorHandler(ErrorMessage,TraceMessage,AdditionalInfo)


  DataDict = results.get('access_token','NONE')
  if(DataDict == "NONE"):
    print("")
    print("")
    print("=================================================================================")
    print("TWITCH ERROR - Could not extract access TOKEN from OAUTH results") 
    print("")
    print(results)
    print("=================================================================================")
    print("")
    print("")
  else:
    print("")
    print("ACCESS GRANTED...processing data results")
    print("")

    try:
      CLOCKBOT_X_ACCESS_TOKEN  = results['access_token']
      CLOCKBOT_X_REFRESH_TOKEN = results['refresh_token']

    except Exception as ErrorMessage:
      TraceMessage = traceback.format_exc()
      AdditionalInfo = "Getting ACCESS_TOKEN" 
      CLOCKBOT_X_ACCESS_TOKEN = 'REFRESH_FAILED'
      LED.ErrorHandler(ErrorMessage,TraceMessage,AdditionalInfo)



    print("CLOCKBOT_X_CODE:         ",CLOCKBOT_X_CODE)
    print("CLOCKBOT_X_ACCESS_TOKEN: ",CLOCKBOT_X_ACCESS_TOKEN)
    print("CLOCKBOT_X_REFRESH_TOKEN:",CLOCKBOT_X_REFRESH_TOKEN)

    
    #Write results to config file
    try:
        KeyFile = ConfigParser()
        KeyFile.read(KeyConfigFileName)
        KeyFile.set('KEYS','CLOCKBOT_X_CODE',CLOCKBOT_X_CODE)
        KeyFile.set('KEYS','CLOCKBOT_X_ACCESS_TOKEN',CLOCKBOT_X_ACCESS_TOKEN)
        KeyFile.set('KEYS','CLOCKBOT_X_REFRESH_TOKEN',CLOCKBOT_X_REFRESH_TOKEN)

        print("File:",KeyConfigFileName)

        with open(KeyConfigFileName,'w+') as UpdatedFile:
          KeyFile.write(UpdatedFile)

    except Exception as ErrorMessage:
        TraceMessage = traceback.format_exc()
        AdditionalInfo = "ACCESS_TOKEN not found in result set" 
        LED.ErrorHandler(ErrorMessage,TraceMessage,AdditionalInfo)


  print("----------------------------------------")
  print("")






def run_coroutine_in_new_loop(EventQueue):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(TwitchEventSub(EventQueue))



def start_led_commander():
    global CommandQueue, CommandProcess, WebProcess

    from multiprocessing import Queue, Process
    import LEDcommander
    import LEDweb  # <== import here

    print("Initializing LEDcommander")

    command_queue = Queue()
    commander = Process(target=LEDcommander.Run, args=(command_queue,))
    webserver = Process(target=LEDweb.serve_web_control, args=(command_queue,))

    commander.start()
    webserver.start()

    command_queue.cancel_join_thread()

    print("LEDcommander and LEDweb launched.")
    return command_queue, commander, webserver






#------------------------------------------------------------------------------
# MAIN SECTION                                                               --
#------------------------------------------------------------------------------


def main():
    
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

  #LED.LEDInitialize()
  #LED.main()

  #load keys and settings
  CheckConfigFiles()
  Twitch_LoadConfigFiles()

  #Spawn a process to run the clock
  #clock_proc = multiprocessing.Process(target=Bot.DisplayDigitalClock())
    


  #----------------------------------------
  # USE OAUTH CODE TO GET NEW TOKEN
  #----------------------------------------

  #This assumes the user has already granted us access via URL and we were given a CODE
  # https://id.twitch.tv/oauth2/authorize?response_type=code&client_id=xxxxxx&scope=chat%3Aread+chat%3Aedit&redirect_uri=http://localhost

  print("  ___    _   _   _ _____ _   _ ")
  print(" / _ \  / \ | | | |_   _| | | |")
  print("| | | |/ _ \| | | | | | | |_| |")
  print("| |_| / ___ \ |_| | | | |  _  |")
  print(" \___/_/   \_\___/  |_| |_| |_|")
  print("")

  # TheClockBot Tokens
  # 1.  Do we have an authentication token yet?
  #       No  - get one using CODE
  #       Yes - refresh before use
  # 2.  Did the refresh work?
  #       No  - Maybe it was too old.  get new tokens using CODE

  if(THECLOCKBOT_ACCESS_TOKEN == 'NONE'):
    print("Access token not found")
    GetAccessTokenUsingOAUTHCode_TheClockBot()
  else:
    print("Access token found.  Refreshing...")
    GetAccessTokenUsingRefreshToken_TheClockBot()
    
    if(THECLOCKBOT_ACCESS_TOKEN == 'NONE'):
      print("Refresh failed.  Attempting to generate new ACCESS_TOKEN and REFRESH_TOKEN using CODE")
      GetAccessTokenUsingOAUTHCode_TheClockBot()
    



  print("")
  print("")
  print("")

  # ClockBot_X Tokens
  # 1.  Do we have an authentication token yet?
  #       No  - get one using CODE
  #       Yes - refresh before use
  # 1.  Did the refresh work?
  #       No  - Maybe it was too old.  get new tokens using CODE

  if(CLOCKBOT_X_ACCESS_TOKEN == 'NONE'):
    print("Access token not found")
    GetAccessTokenUsingOAUTHCode_ClockBotX()
  else:
    print("Access token found.  Refreshing...")
    GetAccessTokenUsingRefreshToken_ClockBotX()
    
    if(CLOCKBOT_X_ACCESS_TOKEN == 'NONE'):
      print("Refresh failed.  Attempting to generate new ACCESS_TOKEN and REFRESH_TOKEN using CODE")
      GetAccessTokenUsingOAUTHCode_ClockBotX()


  #print("")
  #print("--Spawning WebHook process--------------")
  #Spawn the webhook process
  #PatreonWebHookProcess = multiprocessing.Process(target = PatreonWebHook, args=(EventQueue,))
  #PatreonWebHookProcess.start()

  # 2023-09-28
  #Temporarily removing webhooks this because it is crazy complex to keep it running
  #TwitchEventSubProcess = multiprocessing.Process(target = run_coroutine_in_new_loop, args=(EventQueue,))
  #TwitchEventSubProcess.start()


  #print("----------------------------------------")


    

  
  print ("--StartBot--")
  #skip all this if running datagod
  if (BROADCASTER_CHANNEL != 'datagod' and BROADCASTER_CHANNEL != 'XtianNinja'):
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
  





  '''
  LED.DisplayDigitalClock(
      ClockStyle=3,
      CenterHoriz=True,
      v=1, 
      hh=24,
      RGB=LED.LowGreen,
      ShadowRGB=LED.ShadowGreen,
      ZoomFactor=2,
      AnimationDelay=0.05,
      RunMinutes=1,
      EventQueue=EventQueue
  )
  '''
  
  


  mybot = Bot()
  #mybot.DisplayDigitalClock()
  mybot.run()




#If we are running this program directly, it's own name is "__main__"
#This section is where we put things that we only want run once
if __name__ == "__main__":
    try:
        CommandQueue, CommandProcess, WebProcess = start_led_commander()
        main()
    finally:
        CommandQueue.put({"Action": "Quit"})
        time.sleep(0.1)

        CommandProcess.join(timeout=3)
        if CommandProcess.is_alive():
            print("[LEDcommander][Main] LEDCommander still alive — terminating.")
            CommandProcess.terminate()
            CommandProcess.join()

        if WebProcess.is_alive():
            print("[LEDcommander][Main] Web server still alive — terminating.")
            WebProcess.terminate()
            WebProcess.join()

        print("[LEDcommander][Main] Shutdown complete.")


# %%

 