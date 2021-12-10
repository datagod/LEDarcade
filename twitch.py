
# %%

import os
os.system('cls||clear')

import LEDarcade as LED
from rgbmatrix import graphics
from rgbmatrix import RGBMatrix, RGBMatrixOptions

import random
from configparser import SafeConfigParser
import requests
import traceback
import socket
import twitchio
import asyncio
from twitchio.ext import pubsub
from twitchio.ext import commands
import pprint
import copy

import irc.bot
import select

#list of connection messages
from CustomMessages import ConnectionMessages
from CustomMessages import ChatStartMessages


import time
from datetime import datetime








#---------------------------------------
#Variable declaration section
#---------------------------------------
ScrollSleep         = 0.025
TerminalTypeSpeed   = 0.02  #pause in seconds between characters
TerminalScrollSpeed = 0.02  #pause in seconds between new lines


#TWITCH VARIABLES
ACCESS_TOKEN      = ''
REFRESH_TOKEN     = ''
CLIENT_ID         = ''

CHANNEL             = ''
CHANNEL_BIG_TEXT    = ''
CHANNEL_LITTLE_TEXT = ''

USER_ID           = ''
BROADCASTER_ID    = ''
BOT_CHANNEL       = ''
BOT_CHANNEL1      = ''
BOT_CHANNEL2      = ''
BOT_ACCESS_TOKEN  = ''
BOT_REFRESH_TOKEN = ''
BOT_CLIENT_ID     = ''





#User / Channel Info
GameName        = ''
Title           = ''

# Stream Info
StreamStartedAt = ''
StreamType      = ''
ViewerCount     = 0
StreamActive    = False



#Follower Info
Followers      = 0

#HypeTrain info
HypeTrainStartTime  = ''
HypeTrainExpireTime = ''
HypeTrainGoal       = ''
HypeTrainLevel      = 0
HypeTrainTotal      = ''



HatHeight = 32
HatWidth  = 64






class Bot(commands.Bot):

    CursorH             = 0
    CursorV             = 0
    AnimationDelay      = 60
    LastMessageReceived = time.time()
    MinutesToWaitBeforeClosing = 5
    MinutesMaxTime      = 10
    BotStartTime        = time.time()
    SendStartupMessage  = False
    BotTypeSpeed        = TerminalTypeSpeed
    BotScrollSpeed      = TerminalScrollSpeed
    MessageCount        = 0
    SpeedupMessageCount = 5
    ChatTerminalOn      = False



    def __init__(self):
        # Initialise our Bot with our access token, prefix and a list of channels to join on boot...
        # prefix can be a callable, which returns a list of strings or a string...
        # initial_channels can also be a callable which returns a list of strings...
        print("Bot Initialization")
        print("BOT_CHANNEL:     ",BOT_CHANNEL)
        print("BOT_ACCESS_TOKEN:",BOT_ACCESS_TOKEN)
        super().__init__(token=BOT_ACCESS_TOKEN, prefix='?', initial_channels=[BOT_CHANNEL])
        self.BotStartTime        = time.time()




    async def my_custom_startup(self):
        await asyncio.sleep(1)
        channel = self.get_channel(BOT_CHANNEL)
        #channel2 = self.fetch_channel(CHANNEL_ID)


        x = len(ChatStartMessages)
        #print("ChatStartMessages: ",x)
        i = random.randint(0,x-1)
        message = ChatStartMessages[i]         
        print("Message:",message)

        if (self.SendStartupMessage == True):
          await channel.send(message)

      


    async def PerformTimeBasedActions(self):
        loop = asyncio.get_running_loop()
        #end_time = loop.time() + self.AnimationDelay
        

        while True:
          #print('Now: ',datetime.now())
          await asyncio.sleep(1)
         
          
          #elapsed_time = time.time() - starttime
          #elapsed_hours, rem = divmod(elapsed_time, 3600)
          #elapsed_minutes, elapsed_seconds = divmod(rem, 60)

          
          #Close Bot after X minutes of inactivity
          h,m,s    = LED.GetElapsedTime(self.LastMessageReceived,time.time())
          h2,m2,s2 = LED.GetElapsedTime(self.BotStartTime,time.time())
          print("Seconds since last message:",s," MaxMinutes: ",self.MinutesMaxTime, " Minutes Run:","{:5.2f}".format((m2 + s2 / 60))," Messages Queued:",self.MessageCount,end="\r")

          #if (m >= self.MinutesToWaitBeforeClosing or m2 >= self.MinutesMaxTime):
          if (m >= self.MinutesToWaitBeforeClosing or m2 >= 1):
            print("No chat activity for the past {} minutes OR max {} minutes reached.  Closing bot...".format(self.MinutesToWaitBeforeClosing,self.MinutesMaxTime))
            print("")       
            print("*****************")       
            print("** EXITING BOT **")
            print("*****************")       
            print("")       
            LED.ClearBigLED()
            LED.ClearBuffers()
            CursorH = 0
            CursorV = 0
            LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"No chat activity detected.  Did everyone fall asleep?",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalScrollSpeed)
            LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"Closing terminal",CursorH=CursorH,CursorV=CursorV,MessageRGB=(200,0,0),CursorRGB=(200,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalScrollSpeed)
            LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"............",CursorH=CursorH,CursorV=CursorV,MessageRGB=(200,0,0),CursorRGB=(200,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalScrollSpeed)
            self.CursorH = CursorH
            self.CursorV = CursorV
                                  
            await self.close()
            

            BOT_CHANNEL = 'hungrygoriya'
            self.__init__()

          

          #Display animations after X seconds
          h,m,s = LED.GetElapsedTime(self.LastMessageReceived,self.BotStartTime)
          if (s >= self.AnimationDelay):
            LED.DisplayRandomAnimation()
            self.BotStartTime = time.time()





    
    async def event_ready(self):
        # Notify us when everything is ready!
        # We are logged in and ready to chat and use commands...
        #UserList = self.fetch_users()
        print(f'Logged in as | {self.nick}')
    
        
        
        #Display connection message
        x = len(ConnectionMessages)
        print("ConnectionMessages: ",x)
        i = random.randint(0,x-1)
        message = ConnectionMessages[i]         
        print("ConnectionMessage:",message)
        CursorH = self.CursorH
        CursorV = self.CursorH
        LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,message,CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalScrollSpeed)
        LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray," ",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalScrollSpeed)
        self.CursorH = CursorH
        self.CursorV = CursorV


        print(self.connected_channels.__len__())
        #Channel = self.fetch_channel(CHANNEL)
        #print(Channel)

        await self.my_custom_startup()
        #await self.Sleep()

        await self.PerformTimeBasedActions()

    

        '''
        LED.DisplayDigitalClock(
          ClockStyle = 3,
          CenterHoriz = True,
          v   = 1, 
          hh  = 24,
          RGB = LED.LowGreen,
          ShadowRGB     = LED.ShadowGreen,
          ZoomFactor    = 3,
          AnimationDelay= 10,
          RunMinutes = 1)
        ''' 


    #async def event_raw_data(self, raw_message):
    #    print(raw_message)
        

    
      

    async def event_message(self, message):
        
        #Exit if Chat Terminal is not on
        if (self.ChatTerminalOn = False):
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

        # Messages with echo set to True are messages sent by the bot...
        # For now we just want to ignore them...
        if message.echo:
            return

        ScrollText = message.content
        print(message.author.display_name + ": " + ScrollText)

        #print(message.raw_data)
        print(" ")





        try:
          LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,message.author.display_name + ":",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,0,200),CursorRGB=(0,255,0),CursorDarkRGB=(0,200,0),StartingLineFeed=1,TypeSpeed=self.BotTypeSpeed,ScrollSpeed=self.BotScrollSpeed)
          LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray, ScrollText,CursorH=CursorH,CursorV=CursorV,MessageRGB=(0,150,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,200,0),StartingLineFeed=0,TypeSpeed=self.BotTypeSpeed,ScrollSpeed=self.BotScrollSpeed)
        
          #Store running values in the bot object
          self.CursorH = CursorH
          self.CursorV = CursorV
        except:
          LED.ShowScrollingBanner2('ERROR! INVALID CHARACTER',(200,0,0),ScrollSleep=0.005,v=25)

        self.MesageCount = self.MessageCount -1


        #Close Bot if we went past the max time. This is necessary here because the messages queue up 
        #and PerformTimeBaseFunctions has lower priority
        h2,m2,s2 = LED.GetElapsedTime(self.BotStartTime,time.time())
        print("MaxMinutes: ",self.MinutesMaxTime, " Minutes Run:","{:5.2f}".format((m2 + s2 / 60))," Messages Queued:",self.MessageCount,end="\r")

        if (m2 >= self.MinutesMaxTime):
          print("Max {} minutes reached.  Closing bot...".format(self.MinutesToWaitBeforeClosing))       
          print("")       
          print("*****************")       
          print("** EXITING BOT **")
          print("*****************")       
          print("")       
          LED.ClearBigLED()
          LED.ClearBuffers()
          CursorH = 0
          CursorV = 0
          LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"maximum time reached",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalScrollSpeed)
          LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"Closing terminal",CursorH=CursorH,CursorV=CursorV,MessageRGB=(200,0,0),CursorRGB=(200,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalScrollSpeed)
          LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"............",CursorH=CursorH,CursorV=CursorV,MessageRGB=(200,0,0),CursorRGB=(200,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalScrollSpeed)
          self.CursorH = CursorH
          self.CursorV = CursorV
          await self.close()
      

        # Since we have commands and are overriding the default `event_message`
        # We must let the bot know we want to handle and invoke our commands...
        await self.handle_commands(message)

   
    async def event_join(self,channel,user):
      
      print ("Event: event_join")
        
    

    @commands.command()
    async def hello(self, ctx: commands.Context):
        # Here we have a command hello, we can invoke our command with our prefix and command name
        # e.g ?hello
        # We can also give our commands aliases (different names) to invoke with.

        # Send a hello back!
        # Sending a reply back to the channel is easy... Below is an example.
        await ctx.send(f'Greetings from dataBot! {ctx.author.name}!')


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


    
    time.sleep(1)



  

















#------------------------------------------------------------------------------
# Functions                                                                  --
#------------------------------------------------------------------------------



def LoadTwitchKeys():
  
  global ACCESS_TOKEN
  global REFRESH_TOKEN
  global CLIENT_ID
  global CHANNEL
  global CHANNEL_BIG_TEXT
  global CHANNEL_LITTLE_TEXT
  
  global USER_ID
  global BROADCASTER_ID
  global BOT_CHANNEL1
  global BOT_CHANNEL2
  global BOT_ACCESS_TOKEN
  global BOT_REFRESH_TOKEN
  global BOT_CLIENT_ID



  #XtianNinja
  #ACCESS_TOKEN  = '5ndbsyu94bm2qeebw1rgnapw82n2ez'
  #REFRESH_TOKEN = 'spqotm9ujy4ef23u5w36ra1dcr6fs70i71f00jdqvatnckjg3y'
  #CLIENT_ID     = 'gp762nuuoqcoxypju8c569th9wz7q5'
  #CHANNEL       = 'XtianNinja'


  KeyFileName = "KeyConfig.ini" 
  print ("--Load Twitch Keys--")


  if (os.path.exists(KeyFileName)):

    print ("Config file (",KeyFileName,"): already exists")
    KeyFile = SafeConfigParser()
    KeyFile.read(KeyFileName)

    #Get tokens
    CHANNEL             = KeyFile.get("KEYS","CHANNEL")
    CHANNEL_BIG_TEXT    = KeyFile.get("KEYS","CHANNEL_BIG_TEXT")
    CHANNEL_LITTLE_TEXT = KeyFile.get("KEYS","CHANNEL_LITTLE_TEXT")

    USER_ID        = KeyFile.get("KEYS","USER_ID")        #Same as Broadcaster_ID
    BROADCASTER_ID = KeyFile.get("KEYS","BROADCASTER_ID") #Same as UserID
    ACCESS_TOKEN   = KeyFile.get("KEYS","ACCESS_TOKEN")  
    REFRESH_TOKEN  = KeyFile.get("KEYS","REFRESH_TOKEN")
    CLIENT_ID      = KeyFile.get("KEYS","CLIENT_ID")      #ID of the twitch connected app (this program)


    #Bot specific connection info
    BOT_CHANNEL1       = KeyFile.get("KEYS","BOT_CHANNEL1")
    BOT_CHANNEL2       = KeyFile.get("KEYS","BOT_CHANNEL2")
    BOT_ACCESS_TOKEN   = KeyFile.get("KEYS","BOT_ACCESS_TOKEN")  
    BOT_REFRESH_TOKEN  = KeyFile.get("KEYS","BOT_REFRESH_TOKEN")
    BOT_CLIENT_ID      = KeyFile.get("KEYS","BOT_CLIENT_ID")     


    print("CHANNEL:             ",CHANNEL)   
    print("CHANNEL_BIG_TEXT:    ",CHANNEL_BIG_TEXT)   
    print("CHANNEL_LITTLE_TEXT: ",CHANNEL_LITTLE_TEXT)   
    print("USER_ID:             ",USER_ID)
    print("BROADCASTER_ID:      ",BROADCASTER_ID)
    print("CLIENT_ID:           ",CLIENT_ID)
    #print("ACCESS_TOKEN:   ",ACCESS_TOKEN)
    #print("REFRESH_TOKEN:  ",REFRESH_TOKEN)

    print("BOT_CHANNEL1:        ",BOT_CHANNEL1)   
    print("BOT_CHANNEL2:        ",BOT_CHANNEL2)   
    print("BOT_CLIENT_ID:       ",BOT_CLIENT_ID)
    #print("ACCESS_TOKEN:   ",ACCESS_TOKEN)
    #print("REFRESH_TOKEN:  ",REFRESH_TOKEN)


  else:
    
    #To be finished later
    print ("ERROR: Could not locate Key file (",KeyFileName,"). Create a file and make sure to pupulate it with your own keys.")
    #NewKeyFile = SafeConfigParser()
    #NewKeyFile.read(ConfigFileName)
    #NewKeyFile.add_section('KEYS')
    



    #open(KeyFileName "w+")
    #KeyFile.add_section('KEYS')
    #KeyFile.set('KEYS','CHANNEL','YourChannelHere')
    

    #KeyFile = SafeConfigParser()
    #KeyFile.read(KeyFileName)
    

    
  print ("--------------------")
  print (" ")
  








def GetBasicTwitchInfo():
    
    #User / Channel Info
    global GameName        
    global Title           

    #Stream Info
    global StreamStartedAt 
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

   

    print ("--GetBasicTwitchINfo--")

    #----------------------------------------
    # GET CHANNEL INFO
    #----------------------------------------
    print("Get CHANNEL info")
    API_ENDPOINT = "https://api.twitch.tv/helix/channels?broadcaster_id=657401641"
    head = {
    'Client-ID': CLIENT_ID,
    'Authorization': 'Bearer ' +  ACCESS_TOKEN
    }

    #print ("URL: ",API_ENDPOINT, 'data:',head)
    r = requests.get(url = API_ENDPOINT, headers = head)
    results = r.json()
    pprint.pprint(results)
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
    API_ENDPOINT = "https://api.twitch.tv/helix/users/follows?to_id=657401641"
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
    #Hype Train
    #----------------------------------------
    print("Get HYPETRAIN info")
    API_ENDPOINT = "https://api.twitch.tv/helix/hypetrain/events?broadcaster_id=657401641"
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








    print ("---------------------------------------")
    print("Title:",Title)
    print("GameName:",GameName)

    if(StreamActive):
      print("StreamStartedAt:",StreamStartedAt)
      print("StreamType:",StreamType)
      print("ViewerCount:",ViewerCount)

    print("Followers:",Followers)
    print("HypeTrainStartTime:",HypeTrainStartTime)
    print("HypeTrainExpireTime:",HypeTrainExpireTime)
    print("HypeTrainGoal:",HypeTrainGoal)
    print("HypeTrainLevel:",HypeTrainLevel)
    print("HypeTrainTotal:",HypeTrainTotal)
    print ("---------------------------------------")



    
    if(StreamActive):
      StreamStartedDateTime =  ConvertDate(StreamStartedAt)
      
      elapsed_time = time.time() - StreamStartedDateTime
      elapsed_hours, rem = divmod(elapsed_time, 3600)
      elapsed_minutes, elapsed_seconds = divmod(rem, 60)
      print("Elapsed Time: {:0>2}:{:0>2}:{:05.2f}".format(int(elapsed_hours),int(elapsed_minutes),elapsed_seconds),end="\r")


def ConvertDate(TheDate):
  StringDate = TheDate
  NewDate = StringDate[0:10]+ ' ' + StringDate[11:19]
  NewDate = datetime.strptime(NewDate, '%Y-%m-%d %H:%M:%S')

  return NewDate

































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



#connects, but does not retrieve chat messages
#IRCStuff()





#we want to show a timer for how long the stream has been active
#this can be triggerred by a command possibly
#StartTime = time.time()
#HHMMSS = '00:00:00'
#TimerSprite = LED.CreateTimerSprite(HHMMSS)

#while(1==1):
  #elapsed_time = time.time() - StartTime
  #elapsed_hours, rem = divmod(elapsed_time, 3600)
  #elapsed_minutes, elapsed_seconds = divmod(rem, 60)
  #HHMMSS = "{:0>2}:{:0>2}:{:05.2f}".format(int(elapsed_hours),int(elapsed_minutes),elapsed_seconds)
  #print ('ElapsedTime: ',HHMMSS,end="\r")
  #print(TimerSprite.width,HatWidth)
  #h = int(((HatWidth - TimerSprite.width * 3) / 2))
  #print(h)
  #TimerSprite = LED.UpdateTimerWithTransition(TimerSprite, h ,0,(150,0,0),(15,0,0),3,Fill=True,TransitionType=1)  
  #time.sleep(1)






#--------------------------------------
#  SHOW TITLE SCREEN                 --
#--------------------------------------


#examples
# Show Follows
#TheBanner = LED.CreateBannerSprite(str(Followers))
#LED.ClearBuffers() #clean the internal graphic buffers
#LED.ShowGlowingSprite(CenterHoriz=True,CenterVert=False,h=0,v=0,TheSprite=TheBanner,RGB=LED.MedRed,ShadowRGB=LED.ShadowRed,ZoomFactor= 3,GlowLevels=100,FadeLevels=0,DropShadow=True,FadeDelay=0)
#LED.ShowGlowingText(CenterHoriz=True,CenterVert=False,h=0,v=17,Text='FOLLOWS',RGB=LED.MedPurple,ShadowRGB=LED.ShadowPurple,ZoomFactor= 2,GlowLevels=25,DropShadow=True)
#time.sleep(2) 

# Show Follows
#LED.ClearBigLED()
#TheBanner = LED.CreateBannerSprite('XTIAN')
#LED.ShowGlowingSprite(CenterHoriz=True,CenterVert=False,h=0,v=0,TheSprite=TheBanner,RGB=LED.MedBlue,ShadowRGB=LED.ShadowBlue,ZoomFactor= 2,GlowLevels=100,FadeLevels=0,DropShadow=True,FadeDelay=0)
#TheBanner = LED.CreateBannerSprite('NINJA')
#LED.ShowGlowingSprite(CenterHoriz=True,CenterVert=False,h=0,v=13,TheSprite=TheBanner,RGB=LED.MedBlue,ShadowRGB=LED.ShadowBlue,ZoomFactor= 2,GlowLevels=100,FadeLevels=0,DropShadow=True,FadeDelay=0)
#time.sleep(2) 


      

#--------------------------------------
#  Begin Twitch                      --
#--------------------------------------

#Fake boot sequence
LED.ClearBigLED()
LED.ClearBuffers()
CursorH = 0
CursorV = 0
LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"Arcade Retro Clock",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalTypeSpeed)
LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"by datagod",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalTypeSpeed)
LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,".....................",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.025,ScrollSpeed=ScrollSleep)
LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"Boot sequence initiated",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)
LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"RAM CHECK",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)
LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"OK",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)
LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"STORAGE",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)
LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"OK",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)
time.sleep(1)
IPAddress = LED.ShowIPAddress(Wait=5)





LoadTwitchKeys()
BOT_CHANNEL = BOT_CHANNEL1
mybot = Bot()


while (1==1):

  GetBasicTwitchInfo()

  #Decide which stream to monitor the chats
  if(StreamActive == True):
    print ("** Main Stream Active**")
    BOT_CHANNEL = CHANNEL
  else:
    print ("** Main Stream NOT Active**")
    ("Alternate channel selected")
    BOT_CHANNEL = BOT_CHANNEL1

  
  #Show title info if Main stream is active
  if(StreamActive == True):

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


    LED.ShowTitleScreen(
      BigText             = str(Followers),
      BigTextRGB          = LED.MedPurple,
      BigTextShadowRGB    = LED.ShadowPurple,
      LittleText          = 'FOLLOWS',
      LittleTextRGB       = LED.MedRed,
      LittleTextShadowRGB = LED.ShadowRed, 
      ScrollText          = 'CURRENT GAME: ' + GameName,
      ScrollTextRGB       = LED.MedYellow,
      ScrollSleep         = ScrollSleep, # time in seconds to control the scrolling (0.005 is fast, 0.1 is kinda slow)
      DisplayTime         = 1,           # time in seconds to wait before exiting 
      ExitEffect          = 0            # 0=Random / 1=shrink / 2=zoom out / 3=bounce / 4=fade /5=fallingsand
      )


    LED.DisplayDigitalClock(
      ClockStyle = 3,
      CenterHoriz = True,
      v   = 1, 
      hh  = 24,
      RGB = LED.LowGreen,
      ShadowRGB     = LED.ShadowGreen,
      ZoomFactor    = 3,
      AnimationDelay= 30,
      RunMinutes = 1)

    mybot.MinutesMaxTime = 15

  else:
    #Explain the main intro is not live
    LED.ShowTitleScreen(
      BigText             = "404",
      BigTextRGB          = LED.MedPurple,
      BigTextShadowRGB    = LED.ShadowPurple,
      LittleText          = "NO STREAM",
      LittleTextRGB       = LED.MedRed,
      LittleTextShadowRGB = LED.ShadowRed, 
      ScrollText          = CHANNEL + " not active. Lets try " + BOT_CHANNEL,
      ScrollTextRGB       = LED.MedYellow,
      ScrollSleep         = ScrollSleep /2, # time in seconds to control the scrolling (0.005 is fast, 0.1 is kinda slow)
      DisplayTime         = 1,           # time in seconds to wait before exiting 
      ExitEffect          = 5,           # 0=Random / 1=shrink / 2=zoom out / 3=bounce / 4=fade /5=fallingsand
      LittleTextZoom      = 1
      )
  
    mybot.MinutesMaxTime = 1

  
  LED.ClearBigLED()
  LED.ClearBuffers()

  #Show this one reading chats
  LED.ShowTitleScreen(
    BigText             = 'CHAT',
    BigTextRGB          = LED.MedRed,
    BigTextShadowRGB    = LED.ShadowRed,
    LittleText          = 'TERMINAL',
    LittleTextRGB       = LED.MedBlue,
    LittleTextShadowRGB = LED.ShadowBlue, 
    ScrollText          = 'TUNING IN TO ' +  BOT_CHANNEL,
    ScrollTextRGB       = LED.MedOrange,
    ScrollSleep         = ScrollSleep, # time in seconds to control the scrolling (0.005 is fast, 0.1 is kinda slow)
    DisplayTime         = 1,           # time in seconds to wait before exiting 
    ExitEffect          = 0,           # 0=Random / 1=shrink / 2=zoom out / 3=bounce / 4=fade /5=fallingsand
    LittleTextZoom      = 1
    )

  #Show terminal connection message
  LED.ClearBigLED()
  LED.ClearBuffers()
  CursorH = 0
  CursorV = 0
  LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"INITIATING CONNECTION",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)
  LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,".....",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.5,ScrollSpeed=ScrollSleep)
  mybot.CursorH = CursorH
  mybot.CursorV = CursorV




  try:
    print("Loading chat bot for: ",BOT_CHANNEL)
    mybot.run()
  except:
    LED.ClearBigLED()
    LED.ClearBuffers()
    CursorH = 0
    CursorV = 0
    LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"The chat bot has experienced a terminal error",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)
    LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"Connection closed",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)
    




  LED.DisplayDigitalClock(
    ClockStyle = 1,
    CenterHoriz = True,
    v   = 1, 
    hh  = 24,
    RGB = LED.LowGreen,
    ShadowRGB     = LED.ShadowGreen,
    ZoomFactor    = 2,
    AnimationDelay= 60,
    RunMinutes = 5)

  LED.DisplayDigitalClock(ClockStyle=2,CenterHoriz=True,v=1, hh=24, ZoomFactor = 1, AnimationDelay=30, RunMinutes = 5 )







# %%

