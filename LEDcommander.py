#LEDcommander.py

# To do
# =====
#
# - work on transitions between displays
#   - this is tough because each different display type is spawned as a process
#   - perhaps the calling function can take a screen shot (deep copy ScreenArray)
#     and put that in the CommandQueue so we can fade back to it later
 
 
"""
===============================================================================
LEDcommander.py - Multiprocessing Command Dispatcher for LEDarcade
===============================================================================
Author: William McEvoy (@datagod)

DESCRIPTION:
This module coordinates all LED display tasks by acting as a command-and-control
process. It uses Python's `multiprocessing` library to delegate screen updates
(such as digital clocks, terminal messages, or titles) to subprocesses.

KEY ARCHITECTURE:
- The main `Run()` function monitors a shared `CommandQueue`.
- Based on the command type (`Action`), it starts/stops worker processes.
- Each subprocess initializes and controls the hardware via `LEDarcade` safely.

IMPORTANT: Display + GPIO Access
- The `LEDarcade` module interfaces directly with LED matrices via GPIO or
  framebuffer libraries (like `rpi-rgb-led-matrix`).
- Due to hardware constraints, **display initialization must be done inside child processes** only.
- Initializing the display in the main process can lead to:
    - corrupted hardware state
    - silent failures
    - GPIO conflicts and undefined behavior

✅ Always import `LEDarcade` and call `LED.Initialize()` inside the subprocess
✅ Never use GPIO display functions from the parent process

MULTIPROCESS DESIGN:
- Subprocesses are spawned using `multiprocessing.Process` (fork model).
- Only one active `DisplayProcess` is allowed at any time to avoid buffer collisions.
- A shared `StopEvent` is used to gracefully shut down current subprocesses.

COMMANDQUEUE:
- A shared `multiprocessing.Queue` used to deliver structured command dictionaries.
- `Run()` consumes commands in order (FIFO) and dispatches the corresponding worker.
- For TerminalMode, `Run()` forwards terminal messages back into the same queue
  (this avoids direct queue collisions between parent and subprocess).

TERMINAL MODE:
- A persistent terminal subprocess that waits for new text messages.
- Displays each message sequentially with typing and scrolling effects.
- Maintains a local FIFO queue (`message_queue`) to handle rapid incoming messages.
- When idle, shows a blinking cursor until the next message arrives.

SPAWN METHOD (OPTIONAL SAFETY):
For more isolation (especially with native libraries), consider:
    import multiprocessing
    multiprocessing.set_start_method("spawn")

This ensures new interpreter processes are used instead of forks. It's slightly
slower but more reliable when working with C/C++ extensions like GPIO.

EXAMPLES:
To start TerminalMode and send a message:
    CommandQueue.put({"Action": "terminalmode_on", "Message": "Hello", ...})
To send more messages:
    CommandQueue.put({"Action": "terminalmessage", "Message": "Next line!", ...})
To stop TerminalMode:
    CommandQueue.put({"Action": "terminalmode_off"})

"""


print("")
print("=============================================")
print("== LEDcommander.py                           =")
print("=============================================")
print("")




import time
import traceback


from multiprocessing import Event, Process, Queue
import queue

from flask import app, jsonify, request


CursorH   = 0
CursorV   = 0
StopEvent = Event()
DisplayProcess       = None
CurrentDisplayMode   = None
TerminalQueue        = Queue()
ClockFallbackEnabled = True




def Run(CommandQueue):

    global StopEvent
    global DisplayProcess
    global CurrentDisplayMode
    global TerminalQueue

    OldCommand = {
            "Action": "showclock",
            "Style": 1,
            "Zoom": 3 ,
            "Duration": 5,  # minutes
            "Delay": 30
             }


    
    print("\n" + "=" * 65)
    print("🧠 LEDcommander Launched")
    print("=" * 65)
    print("Multiprocessing control engine for LEDarcade.")
    print("Handles dynamic screen updates, effects, and real-time commands.")
    print("Developed by William McEvoy (@datagod) for Raspberry Pi environments.")
    print("Core Features:")
    print(" - Isolated subprocess rendering (clock, titles, etc.)")
    print(" - Clean LED shutdown via command queue")
    print(" - Expandable message-based architecture")
    print(" - Safe multiprocessing for GPIO hardware")
    print("-------------------------------------------------------------")
    print("Command your pixels like a pro — with LEDcommander.")
    print("=" * 65 + "\n")
    print("")
    print("")


    while True:

        try:
            Command = CommandQueue.get(timeout=1)
            print(f"[LEDcommander][Run] Received command: {Command}")
            
            #We want to restart a previous process if it was interrupted
            #OldCommand = Command


            if not isinstance(Command, dict):
                continue

            Action = Command.get("Action", "").lower()
            print("")
            print("<--------------------------------------------->")
            print(f"<-- [LEDcommander] Action: {Action}")
            print("<--------------------------------------------->")
            print("")



            #----------------------------------
            #-- CLOCK MODE
            #----------------------------------

            if Action == "showclock":
                print("Starting the clock")
                if DisplayProcess and DisplayProcess.is_alive():
                    print("LED display already in use.  Restarting")
                    #time.sleep(10)
                    StopEvent.set()
                    DisplayProcess.join()
                StopEvent.clear()
                CurrentDisplayMode = "clock"
                DisplayProcess = Process(target=ShowDigitalClock, args=(Command, StopEvent))
                DisplayProcess.start()


            elif Action == "stopclock":
                print("Stopping the clock")
                StopEvent.set()
                if DisplayProcess and DisplayProcess.is_alive():
                    DisplayProcess.join()



            #----------------------------------
            #-- TITLE SCREEN
            #----------------------------------

            elif Action == "showtitlescreen":
                print("Showing title screen")
                if DisplayProcess and DisplayProcess.is_alive():
                    print("LED display already in use.  Stopping process then restarting")
                    StopEvent.set()
                    DisplayProcess.join()

                StopEvent.clear()
                CurrentDisplayMode = "title"
                DisplayProcess = Process(target=ShowTitleScreen, args=(Command, StopEvent))
                DisplayProcess.start()


            #----------------------------------
            #-- ANALOG CLOCK
            #----------------------------------

            elif Action == "analogclock":
                if DisplayProcess and DisplayProcess.is_alive():
                    StopEvent.set()
                    DisplayProcess.join()

                StopEvent.clear()
                CurrentDisplayMode = "clock"
                DisplayProcess = Process(target=ShowAnalogClock, args=(Command, StopEvent))
                DisplayProcess.start()


            elif Action == "retrodigital":
                if DisplayProcess and DisplayProcess.is_alive():
                    StopEvent.set()
                    DisplayProcess.join()

                StopEvent.clear()
                CurrentDisplayMode = "clock"
                DisplayProcess = Process(target=ShowRetroDigital, args=(Command, StopEvent))
                DisplayProcess.start()


            #----------------------------------
            #-- STARRY NIGHT VARIATIONS
            #----------------------------------


            elif Action == "starrynightdisplaytext":
                print("[LEDcommander][Run] Starry Night Display Text")
                if DisplayProcess and DisplayProcess.is_alive():
                    print("LED display already in use.  Stopping process then restarting")
                    StopEvent.set()
                    DisplayProcess.join()

                StopEvent.clear()
                CurrentDisplayMode = "starrynight"
                DisplayProcess = Process(target=StarryNightDisplayText, args=(Command, StopEvent))
                DisplayProcess.start()



            #----------------------------------
            #-- LAUNCH PROGRAMS
            #----------------------------------


            elif Action == "launch_dotinvaders":
                print("[LEDcommander][Run] Launching DotInvaders")
                if DisplayProcess and DisplayProcess.is_alive():
                    print("LED display already in use.  Stopping process then restarting")
                    StopEvent.set()
                    DisplayProcess.join()

                StopEvent.clear()
                CurrentDisplayMode = "dotinvaders"
                DisplayProcess = Process(target=LaunchDotInvaders, args=(Command, StopEvent))
                DisplayProcess.start()


            elif Action == "launch_defender":
                print("[LEDcommander][Run] Launching Defender")
                if DisplayProcess and DisplayProcess.is_alive():
                    print("LED display already in use.  Stopping process then restarting")
                    StopEvent.set()
                    DisplayProcess.join()

                StopEvent.clear()
                CurrentDisplayMode = "defender"
                DisplayProcess = Process(target=LaunchDefender, args=(Command, StopEvent))
                DisplayProcess.start()




            elif Action == "launch_tron":
                print("[LEDcommander][Run] Launching Tron")
                if DisplayProcess and DisplayProcess.is_alive():
                    print("LED display already in use.  Stopping process then restarting")
                    StopEvent.set()
                    DisplayProcess.join()

                StopEvent.clear()
                CurrentDisplayMode = "tron"
                DisplayProcess = Process(target=LaunchTron, args=(Command, StopEvent))
                DisplayProcess.start()

            elif Action == "launch_outbreak":
                print("[LEDcommander][Run] Launching Outbreak")
                if DisplayProcess and DisplayProcess.is_alive():
                    print("LED display already in use.  Stopping process then restarting")
                    StopEvent.set()
                    DisplayProcess.join()

                StopEvent.clear()
                CurrentDisplayMode = "outbreak"
                DisplayProcess = Process(target=LaunchOutbreak, args=(Command, StopEvent))
                DisplayProcess.start()



            elif Action == "launch_spacedot":
                print("[LEDcommander][Run] Launching SpaceDot")
                if DisplayProcess and DisplayProcess.is_alive():
                    print("LED display already in use.  Stopping process then restarting")
                    StopEvent.set()
                    DisplayProcess.join()

                StopEvent.clear()
                CurrentDisplayMode = "spacedot"
                DisplayProcess = Process(target=LaunchSpaceDot, args=(Command, StopEvent))
                DisplayProcess.start()


            elif Action == "launch_fallingsand":
                print("[LEDcommander][Run] Launching fallingsand")
                if DisplayProcess and DisplayProcess.is_alive():
                    print("LED display already in use.  Stopping process then restarting")
                    StopEvent.set()
                    DisplayProcess.join()

                StopEvent.clear()
                CurrentDisplayMode = "tron"
                DisplayProcess = Process(target=LaunchFallingSand, args=(Command, StopEvent))
                DisplayProcess.start()


            elif Action == "launch_gravitysim":
                print("[LEDcommander][Run] Launching GravitySim")
                if DisplayProcess and DisplayProcess.is_alive():
                    print("LED display already in use.  Stopping process then restarting")
                    StopEvent.set()
                    DisplayProcess.join()

                StopEvent.clear()
                CurrentDisplayMode = "gravitysim"
                DisplayProcess = Process(target=LaunchGravitySim, args=(Command, StopEvent))
                DisplayProcess.start()


            #----------------------------------
            #-- TWITCH TIMER
            #----------------------------------

            elif Action == "twitchtimer_on":
                print("Showing title screen")
                if DisplayProcess and DisplayProcess.is_alive():
                    print("LED display already in use.  Stopping process then restarting")
                    StopEvent.set()
                    DisplayProcess.join()

                StopEvent.clear()
                CurrentDisplayMode = "twitch"
                DisplayProcess = Process(target=StartTwitchTimer, args=(Command, StopEvent))
                DisplayProcess.start()


            elif Action == "twitchtimer_off":
                print("Showing title screen")
                if DisplayProcess and DisplayProcess.is_alive():
                    print("LED display in use.  Stopping process.")
                    StopEvent.set()
                    DisplayProcess.join()

                StopEvent.clear()
                CurrentDisplayMode = "stopped"




            #----------------------------------
            #-- TERMINAL MODE
            #----------------------------------

            elif Action == "terminalmode_on":
                if DisplayProcess and DisplayProcess.is_alive():
                    print("[LEDcommander][Run] TerminalMode already active.")
                else:
                    StopEvent.clear()
                    CurrentDisplayMode = "terminal"
                    DisplayProcess = Process(target=StartTerminalMode, args=(CommandQueue, StopEvent, Command))
                    DisplayProcess.start()


            elif Action == "terminalmessage":
                if DisplayProcess and DisplayProcess.is_alive() and CurrentDisplayMode == "terminal":
                    TerminalQueue.put(Command)
                else:
                    print("[LEDcommander] TerminalMode not active. Auto-starting it.")
                    StopEvent.set()
                    if DisplayProcess and DisplayProcess.is_alive():
                        DisplayProcess.join()
                    StopEvent.clear()
                    CurrentDisplayMode = "terminal"
                    TerminalQueue = Queue()  # reset queue to avoid stale messages
                    DisplayProcess = Process(target=StartTerminalMode, args=(TerminalQueue, StopEvent, Command))
                    DisplayProcess.start()

            # In StartTerminalMode(), replace CommandQueue with TerminalQueue


            elif Action == "terminalmode_off":
                print("[LEDcommander] terminalmode_OFF detected")
                CurrentDisplayMode = "stopped"
                DisplayProcess = Process(target=StopTerminalMode, args=())
                DisplayProcess.start()
                StopEvent.set()
                if DisplayProcess and DisplayProcess.is_alive():
                    DisplayProcess.join()
                    print("[LEDcommander] TerminalMode stopped.")



            #----------------------------------------
            # ANIMATIONS                           --
            #----------------------------------------

            elif Action == "showheart":
                if DisplayProcess and DisplayProcess.is_alive():
                    StopEvent.set()
                    DisplayProcess.join()

                StopEvent.clear()
                CurrentDisplayMode = "heart"
                DisplayProcess = Process(target=ShowHeart, args=(Command, StopEvent))
                DisplayProcess.start()


            elif Action == "showgif":
                if DisplayProcess and DisplayProcess.is_alive():
                    StopEvent.set()
                    DisplayProcess.join()
                StopEvent.clear()
                CurrentDisplayMode = "gif"
                DisplayProcess = Process(target=ShowGIF, args=(Command, StopEvent))
                DisplayProcess.start()


            elif Action == "showviewers":
                if DisplayProcess and DisplayProcess.is_alive():
                    StopEvent.set()
                    DisplayProcess.join()
                StopEvent.clear()
                CurrentDisplayMode = "gif"
                DisplayProcess = Process(target=ShowViewers, args=(Command, StopEvent))
                DisplayProcess.start()


            elif Action == "showimagezoom":
                if DisplayProcess and DisplayProcess.is_alive():
                    StopEvent.set()
                    DisplayProcess.join()
                StopEvent.clear()
                CurrentDisplayMode = "image"
                DisplayProcess = Process(target=ShowImageZoom, args=(Command, StopEvent))
                
                #After showing Image, we restart the clock
                CommandQueue.put(OldCommand)
                DisplayProcess.start()



            elif Action == "quit":
                print("[LEDcommander] Quit received.")
                if DisplayProcess and DisplayProcess.is_alive():
                    StopEvent.set()
                    DisplayProcess.join()
                print("[LEDcommander][Run] Shutdown complete.")
                break  # Exit the loop and end the process



        except queue.Empty:
            print("[LEDcommander][Run] Queue empty.  Waiting for command...")
            time.sleep(5)

            #If nothing is being displayed, tell it to restart the digital clock
            if CommandQueue.empty():
                if not (DisplayProcess and DisplayProcess.is_alive()):
                    print("[LEDcommander] No display active and queue is empty. Restarting fallback clock.")
                    CommandQueue.put(OldCommand)

            continue


        except Exception as Error:
            print(f"[LEDcommander ERROR][Run] {Error}")
            traceback.print_exc()

        





#----------------------------------------------------------
#-- Action functions
#----------------------------------------------------------

def ShowDigitalClock(Command,StopEvent):
    import LEDarcade as LED
    LED.Initialize()

    print("RedR: ",LED.RedR)

    #Sprite display locations ??  maybe not needed
    #LED.ClockH,      LED.ClockV,      LED.ClockRGB      = 0,0,  (0,150,0)
    #LED.DayOfWeekH,  LED.DayOfWeekV,  LED.DayOfWeekRGB  = 8,20,  (125,20,20)
    #LED.MonthH,      LED.MonthV,      LED.MonthRGB      = 28,20, (125,30,0)
    #LED.DayOfMonthH, LED.DayOfMonthV, LED.DayOfMonthRGB = 47,20, (115,40,10)

   

    ClockStyle = Command.get("Style", 1)
    ZoomFactor = Command.get("Zoom", 2)
    RunMinutes = Command.get("Duration", 1)
    AnimationDelay = Command.get("Delay", 30)

    print(f"[LEDcommander] Showing clock: Style={ClockStyle}, Zoom={ZoomFactor}, Duration={RunMinutes}")

    LED.DisplayDigitalClock(
        ClockStyle=ClockStyle,
        CenterHoriz=True,
        v=1,
        hh=24,
        RGB=LED.LowGreen,
        ShadowRGB      = LED.ShadowGreen,
        ZoomFactor     = ZoomFactor,
        AnimationDelay = AnimationDelay,
        RunMinutes     = RunMinutes,
        StopEvent      = StopEvent
    )
    #LED.SweepClean()



def ShowRetroDigital(Command,StopEvent):
    import LEDarcade as LED
    LED.Initialize()
   

    ClockStyle = Command.get("Style", 4)
    ZoomFactor = Command.get("Zoom", 1)
    RunMinutes = Command.get("Duration", 5)
    AnimationDelay = Command.get("Delay", 30)

    print(f"[LEDcommander] Showing clock: Style={ClockStyle}, Zoom={ZoomFactor}, Duration={RunMinutes}")

    LED.DisplayDigitalClock(
        ClockStyle=ClockStyle,
        CenterHoriz=True,
        v=1,
        hh=24,
        RGB=LED.LowGreen,
        ShadowRGB      = LED.ShadowGreen,
        ZoomFactor     = ZoomFactor,
        AnimationDelay = AnimationDelay,
        RunMinutes     = RunMinutes,
        StopEvent      = StopEvent
    )
    #LED.SweepClean()













def StartTwitchTimer(Command,StopEvent):
    import LEDarcade as LED
    LED.Initialize()

    
    StreamStartedDateTime     = Command.get("StreamStartedDateTime", 1)
    StreamDurationHHMMSS      = Command.get("StreamDurationHHMMSS", 1)
    print(f"[LEDcommander][StartTwitchTimer] StreamDurationHHMMSS: ",StreamDurationHHMMSS)

    LED.DisplayTwitchTimer(
        CenterHoriz = True,
        CenterVert  = False,
        h   = 0,
        v   = 1, 
        hh  = 24,
        RGB              = LED.LowGreen,
        ShadowRGB        = LED.ShadowGreen,
        ZoomFactor       = 3,
        AnimationDelay   = 30,
        RunMinutes       = 10,
        StartDateTimeUTC = StreamStartedDateTime,
        HHMMSS           = StreamDurationHHMMSS,
        StopEvent        = StopEvent
    )
    LED.SweepClean()
          




def ShowTitleScreen(Command,StopEvent):
    import LEDarcade as LED
    LED.Initialize()

    #Extract values from the Command dictionary
    #Populate input variables
    BigText             = Command.get("BigText","?")
    BigTextRGB          = Command.get("BigTextRGB",(255,0,0))
    BigTextShadowRGB    = Command.get("BigTextShadowRGB",(255,0,0))
    LittleText          = Command.get("LittleText","??")
    LittleTextRGB       = Command.get("LittleTextRGB",(255,0,0))
    LittleTextShadowRGB = Command.get("LittleTextShadowRGB",(255,0,0))
    ScrollText          = Command.get("ScrollText","??")
    ScrollTextRGB       = Command.get("ScrollTextRGB",(255,0,0))
    ScrollSleep         = Command.get("ScrollSleep",0.05)
    DisplayTime         = Command.get("DisplayTime",1)
    ExitEffect          = Command.get("ExitEffect",0)
    LittleTextZoom      = Command.get("LittleTextZoom",1)
    
    
    print(f"[LEDcommander] Showing title screen: BigText={BigText}, LittleText={LittleText}, ScrollText={ScrollText}")


    LED.ShowTitleScreen(
      BigText             = BigText,
      BigTextRGB          = BigTextRGB,
      BigTextShadowRGB    = BigTextShadowRGB,
      LittleText          = LittleText,
      LittleTextRGB       = LittleTextRGB,
      LittleTextShadowRGB = LittleTextShadowRGB,
      ScrollText          = ScrollText,
      ScrollTextRGB       = ScrollTextRGB,
      ScrollSleep         = ScrollSleep,
      DisplayTime         = DisplayTime,
      ExitEffect          = ExitEffect,
      LittleTextZoom      = LittleTextZoom
      )
    LED.SweepClean()









def StopTerminalMode():
    import LEDarcade as LED
    LED.Initialize()
    global CursorH, CursorV

    message_queue = []
    TerminalTypeSpeed = 0.08
    TerminalScrollSpeed = 0.08
    CursorRGB = (0, 255, 0)
    CursorDarkRGB = (0, 50, 0)
    
    print("=========================")
    print("== STOP TERMINAL MODE ==")
    print("=========================")
    LED.ScreenArray, CursorH, CursorV = LED.TerminalScroll(
        LED.ScreenArray,
        Message="Stopping terminal...",
        CursorH=CursorH,
        CursorV=CursorV,
        MessageRGB=(0,0,0),
        CursorRGB=(0, 255, 0),
        CursorDarkRGB=(0, 50, 0),
        StartingLineFeed=1,
        TypeSpeed=TerminalTypeSpeed,
        ScrollSpeed=TerminalScrollSpeed
    )
    LED.ZoomScreen(LED.ScreenArray, 32, 1, Fade=True, ZoomSleep=0.05)
    LED.SweepClean()




def StartTerminalMode(TerminalQueue, StopEvent, InitialCommand=None):
    import LEDarcade as LED
    LED.Initialize()
    CursorH, CursorV = 0, 0
    message_queue = []
    TerminalTypeSpeed = 0.08
    TerminalScrollSpeed = 0.08
    CursorRGB = (0, 255, 0)
    CursorDarkRGB = (0, 50, 0)

    def _StopTerminalMode():
        print("=========================")
        print("== STOP TERMINAL MODE ==")
        print("=========================")
        LED.ScreenArray, CursorH, CursorV = LED.TerminalScroll(
            LED.ScreenArray,
            Message="Stopping terminal...",
            CursorH=CursorH,
            CursorV=CursorV,
            MessageRGB=(0, 0, 0),
            CursorRGB=CursorRGB,
            CursorDarkRGB=CursorDarkRGB,
            StartingLineFeed=1,
            TypeSpeed=TerminalTypeSpeed,
            ScrollSpeed=TerminalScrollSpeed
        )
        LED.ZoomScreen(LED.ScreenArray, 32, 1, Fade=True, ZoomSleep=0.03)

    print("=========================")
    print("== START TERMINAL MODE ==")
    print("=========================")

    if InitialCommand:
        message_queue.append(InitialCommand)

    while not StopEvent.is_set():
        try:
            try:
                Command = TerminalQueue.get(timeout=0.1)
                Action = Command.get("Action", "").lower()

                if Action == "terminalmessage":
                    message_queue.append(Command)
                    print(f"[TerminalMode] Queued: {Command.get('Message')[:40]}...")

                elif Action == "terminalmode_off":
                    print("[LEDcommander] RUN: terminalmode_OFF detected")
                    _StopTerminalMode()
                    StopEvent.set()

            except queue.Empty:
                pass

            if message_queue:
                Command = message_queue.pop(0)
                msg = Command.get("Message", None)
                if isinstance(msg, str):
                    rgb = Command.get("RGB", (255, 255, 255))
                    scroll_speed = Command.get("ScrollSleep", 0.05)
                    LED.ScreenArray, CursorH, CursorV = LED.TerminalScroll(
                        LED.ScreenArray, msg,
                        CursorH=CursorH, CursorV=CursorV,
                        MessageRGB=rgb,
                        CursorRGB=CursorRGB, CursorDarkRGB=CursorDarkRGB,
                        StartingLineFeed=1,
                        TypeSpeed=TerminalTypeSpeed,
                        ScrollSpeed=scroll_speed
                    )
                else:
                    print("[TerminalMode] Skipped invalid or missing 'Message'.")

        except Exception as e:
            print(f"[TerminalMode] Error: {e}")

        LED.BlinkCursor(
            CursorH=CursorH,
            CursorV=CursorV,
            CursorRGB=CursorRGB,
            CursorDarkRGB=CursorDarkRGB,
            BlinkSpeed=0.50,
            BlinkCount=2
        )





def ShowHeart(Command, StopEvent):
    import LEDarcade as LED
    LED.Initialize()

    StreamBrightness = 80
    GifBrightness    = 80
    MaxBrightness    = 100
    print("[LEDcommander][ShowHeart] Show beating heart")

    LED.TheMatrix.brightness = StreamBrightness
    LED.ShowBeatingHeart(h=16, v=0, beats=5, Sleep=0.01) 
    LED.TheMatrix.brightness = MaxBrightness
    LED.SweepClean()



def ShowGIF(Command, StopEvent):
    import LEDarcade as LED
    LED.Initialize()

    StreamBrightness = 80
    GifBrightness    = 80
    MaxBrightness    = 100

    GIF              = Command.get("GIF",'./images/redalert.gif')
    loops            = Command.get("loops",5)
    sleep            = Command.get("sleep",0.06)

    print("[LEDcommander][ShowGIF] displaying a GIF: ",GIF)

    LED.TheMatrix.brightness = StreamBrightness
    LED.DisplayGIF(GIFName=GIF,width=64,height=32,Loops=loops,sleep=sleep)
    LED.TheMatrix.brightness = MaxBrightness
    LED.SweepClean()




def ShowViewers(Command, StopEvent):
    import LEDarcade as LED
    LED.Initialize()

    StreamBrightness = 80
    GifBrightness    = 80
    MaxBrightness    = 100

    print("[LEDcommander][ShowViewers] Showing image" )

    ChatUsers = Command.get("chatusers",["Nobody"])


    LED.TheMatrix.brightness = MaxBrightness
    LED.ScrollJustJoinedUser(ChatUsers,'JustJoined.png',0.04)
    LED.TheMatrix.brightness = StreamBrightness
    
    #clean up the screen using animations
    LED.SweepClean()




def ShowImageZoom(Command, StopEvent):
    import LEDarcade as LED
    LED.Initialize()

    StreamBrightness = 80
    GifBrightness    = 25
    MaxBrightness    = 100

    image            = Command.get("image",'./images/UserProfile.png')
    zoommin          = Command.get("zoommin",1)
    zoommax          = Command.get("zoommax",256)
    zoomfinal        = Command.get("zoomfinal",32)
    sleep            = Command.get("sleep",0.001)
    step             = Command.get("step",1)

    print("[LEDcommander][ShowImageZoom] Zoom an image")


    LED.TheMatrix.brightness = GifBrightness
    LED.ZoomImage(ImageName=image,ZoomStart=zoommin,ZoomStop=zoommax,ZoomSleep=sleep,Step=step)
    LED.ZoomImage(ImageName=image,ZoomStart=zoommax,ZoomStop=zoomfinal,ZoomSleep=sleep,Step=step)
    time.sleep(3)
    LED.TheMatrix.brightness = MaxBrightness
    LED.SweepClean()


def LaunchDotInvaders(Command, StopEvent):
    import LEDarcade as LED
    LED.Initialize()
    import DotInvaders as DI

    StreamBrightness = 80
    GifBrightness    = 80
    MaxBrightness    = 100

    Duration         = Command.get("duration",1)

    print("[LEDcommander][LaunchDotInvaders] Launching...")

    DI.LaunchDotInvaders(Duration=Duration, ShowIntro=True, StopEvent=StopEvent)
    LED.SweepClean()
    


def LaunchDefender(Command, StopEvent):
    import LEDarcade as LED
    LED.Initialize()
    import Defender as DE
    Duration         = Command.get("duration",1)
    print("[LEDcommander][LaunchDefender] Launching...")

    DE.LaunchDefender(Duration=Duration, ShowIntro=True, StopEvent=StopEvent)
    LED.SweepClean()


def LaunchGravitySim(Command, StopEvent):
    import LEDarcade as LED
    LED.Initialize()
    import gravitysim as GR
    Duration         = Command.get("duration",10)
    print("[LEDcommander][LaunchGravitySim] Launching...")

    GR.Launch(Duration=Duration, ShowIntro=True, StopEvent=StopEvent)


def LaunchTron(Command, StopEvent):
    import LEDarcade as LED
    LED.Initialize()
    import Tron as TR
    Duration         = Command.get("duration",10)
    print("[LEDcommander][LaunchTron] Launching...")

    TR.LaunchTron(Duration=Duration, ShowIntro=True, StopEvent=StopEvent)


def LaunchSpaceDot(Command, StopEvent):
    import LEDarcade as LED
    LED.Initialize()
    import SpaceDot as SD
    Duration         = Command.get("duration",10)
    print("[LEDcommander][LaunchSpaceDot] Launching...")

    SD.LaunchSpaceDot(Duration=Duration, ShowIntro=True, StopEvent=StopEvent)




def LaunchOutbreak(Command, StopEvent):
    import LEDarcade as LED
    LED.Initialize()
    import Outbreak as OB
    Duration         = Command.get("duration",10)
    print("[LEDcommander][LaunchOutbreak] Launching...")

    OB.LaunchOutbreak(Duration=Duration, ShowIntro=True, StopEvent=StopEvent)





def LaunchFallingSand(Command, StopEvent):
    import LEDarcade as LED
    LED.Initialize()
    import FallingSand as FS
    Duration         = Command.get("duration",10)
    print("[LEDcommander][LaunchFallingSand] Launching...")

    FS.LaunchFallingSand(Duration=Duration, ShowIntro=True, StopEvent=StopEvent)



def ShowAnalogClock(Command, StopEvent):
    import LEDarcade as LED
    LED.Initialize()
    import AnalogClock as AC
    Duration         = Command.get("duration",10)
    print("[LEDcommander][ShowAnalogClock] Launching...")

    AC.RunClock(Duration=Duration, StopEvent=StopEvent)





def StarryNightDisplayText(Command, StopEvent):
    import LEDarcade as LED
    LED.Initialize()
    print("[LEDcommander][StarryNightDisplay] Launching...")
    Text1  = Command.get("text1",'')
    Text2  = Command.get("text2",'')
    Text3  = Command.get("text3",'')

    LED.StarryNightDisplayText(
    Text1       = Text1,
    Text2       = Text2,
    Text3       = Text3, 
    ScrollSleep = 0.015,
    RunSeconds  = 30
    )




#-------------------------------------------------------------------------------
# Main Processing
#
#-------------------------------------------------------------------------------

if __name__ == "__main__":
    CommandQueue = Queue()

    commander_process = Process(target=Run, args=(CommandQueue,))
    commander_process.start()

    webserver_process = Process(target=launch_web_control_server, args=(CommandQueue,))
    webserver_process.start()

    print("")
    print("[LEDcommander][main] Processes started")
    
    # Remove joins for now
    # commander_process.join()
    # webserver_process.join()

    # Keep main thread alive so child processes aren’t killed
    while True:
        time.sleep(1)
