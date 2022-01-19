#------------------------------------------------------------------------------
#      _    ____   ____    _    ____  _____                                  --
#     / \  |  _ \ / ___|  / \  |  _ \| ____|                                 --
#    / _ \ | |_) | |     / _ \ | | | |  _|                                   --
#   / ___ \|  _ <| |___ / ___ \| |_| | |___                                  --
#  /_/   \_\_| \_\\____/_/   \_\____/|_____|                                 --
#                                                                            --
#------------------------------------------------------------------------------



import LEDarcade   as LED
import DotInvaders as DI
import Outbreak    as OB
import time
      

#---------------------------------------
#Variable declaration section
#---------------------------------------

ScrollSleep         = 0.025
TerminalTypeSpeed   = 0.02  #pause in seconds between characters
TerminalScrollSpeed = 0.02  #pause in seconds between new lines
CursorRGB           = (0,255,0)
CursorDarkRGB       = (0,50,0)



#--------------------------------------
# M A I N   P R O C E S S I N G      --
#--------------------------------------

def LaunchArcade(GameMaxMinutes = 10000):
  
    global start_time


    start_time = time.time()
    LED.LoadConfigData()


    LED.ShowTitleScreen(
        BigText             = 'ARCADE',
        BigTextRGB          = LED.HighRed,
        BigTextShadowRGB    = LED.ShadowRed,
        LittleText          = 'RETRO CLOCK',
        LittleTextRGB       = LED.MedGreen,
        LittleTextShadowRGB = (0,10,0), 
        ScrollText          = 'Insert 25 cents to continue',
        ScrollTextRGB       = LED.MedYellow,
        ScrollSleep         = 0.03, # time in seconds to control the scrolling (0.005 is fast, 0.1 is kinda slow)
        DisplayTime         = 1,           # time in seconds to wait before exiting 
        ExitEffect          = 0            # 0=Random / 1=shrink / 2=zoom out / 3=bounce / 4=fade /5=fallingsand
        )


    LED.ClearBigLED()
    LED.ClearBuffers()
    CursorH = 0
    CursorV = 0
    LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"accessing time machine",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalTypeSpeed)
    LED.BlinkCursor(CursorH= CursorH,CursorV=CursorV,CursorRGB=CursorRGB,CursorDarkRGB=CursorDarkRGB,BlinkSpeed=0.5,BlinkCount=2)
    LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"entering 1984",CursorH=CursorH,CursorV=CursorV,MessageRGB=(100,100,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalTypeSpeed)
    LED.BlinkCursor(CursorH= CursorH,CursorV=CursorV,CursorRGB=CursorRGB,CursorDarkRGB=CursorDarkRGB,BlinkSpeed=0.5,BlinkCount=2)
    LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"GOOD LUCK!",CursorH=CursorH,CursorV=CursorV,MessageRGB=(0,0,255),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=0.005,ScrollSpeed=ScrollSleep)
    LED.BlinkCursor(CursorH= CursorH,CursorV=CursorV,CursorRGB=CursorRGB,CursorDarkRGB=CursorDarkRGB,BlinkSpeed=0.5,BlinkCount=2)


    DI.LaunchDotInvaders(GameMaxMinutes)
    OB.LaunchOutbreak(GameMaxMinutes)
        







#execute if this script is called directly
if __name__ == "__main__" :
  while(1==1):
    LaunchArcade(100000)        











