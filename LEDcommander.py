#LEDcommander.py


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


CursorH   = 0
CursorV   = 0
StopEvent = Event()
DisplayProcess     = None
CurrentDisplayMode = None
TerminalQueue      = Queue()





def Run(CommandQueue):


    global StopEvent
    global DisplayProcess

    
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

            if not isinstance(Command, dict):
                continue

            Action = Command.get("Action", "").lower()
            print(f"[LEDcommander][Run]-->{Action}<--")

            #----------------------------------
            #-- CLOCK MODE
            #----------------------------------

            if Action == "showclock":
                print("Starting the clock")
                if DisplayProcess and DisplayProcess.is_alive():
                    print("LED display already in use.  Stopping process then restarting")
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
                    print("LED display already in use.  Stopping process then restarting")
                    StopEvent.set()
                    DisplayProcess.join()

                StopEvent.clear()
                CurrentDisplayMode = "stopped"
                DisplayProcess = Process(target=StopTwitchTimer, args=(Command, StopEvent))
                DisplayProcess.start()




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



            # Final version using a dedicated TerminalQueue

            # At the top-level of Run(), outside the loop (not shown here):

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
            # Animations                           --
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


            elif Action == "showimagezoom":
                if DisplayProcess and DisplayProcess.is_alive():
                    StopEvent.set()
                    DisplayProcess.join()
                StopEvent.clear()
                CurrentDisplayMode = "gif"
                DisplayProcess = Process(target=ShowImageZoom, args=(Command, StopEvent))
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
            time.sleep(2)
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
    LED.ShowBeatingHeart(h=16, v=0, beats=10, Sleep=0.01) 
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

    print("[LEDcommander][ShowGIF] displaying a GIF")

    LED.TheMatrix.brightness = StreamBrightness
    LED.DisplayGIF(GIFName=GIF,width=64,height=32,Loops=loops,sleep=sleep)
    LED.TheMatrix.brightness = MaxBrightness
    LED.SweepClean()



def ShowImageZoom(Command, StopEvent):
    import LEDarcade as LED
    LED.Initialize()

    StreamBrightness = 80
    GifBrightness    = 80
    MaxBrightness    = 100

    image            = Command.get("image",'./images/UserProfile.png')
    zoommin          = Command.get("zoommin",1)
    zoommax          = Command.get("zoommax",256)
    zoomfinal        = Command.get("zoomfinal",32)
    sleep            = Command.get("sleep",0.025)
    step             = Command.get("step",4)

    print("[LEDcommander][ShowImageZoom] Zoom an image")


    LED.TheMatrix.brightness = StreamBrightness
    LED.ZoomImage(ImageName=image,ZoomStart=zoommin,ZoomStop=zoommax,ZoomSleep=sleep,Step=step)
    LED.ZoomImage(ImageName="UserProfile.png",ZoomStart=zoommax,ZoomStop=zoommin,ZoomSleep=sleep,Step=step)
    LED.ZoomImage(ImageName="UserProfile.png",ZoomStart=zoommin,ZoomStop=zoomfinal,ZoomSleep=sleep,Step=step)
    time.sleep(3)
    LED.TheMatrix.brightness = MaxBrightness
    LED.SweepClean()


    

#-------------------------------------------------------------------------------
# Main Processing
#
#-------------------------------------------------------------------------------


if __name__ == "__main__":
    print("Hi there")
