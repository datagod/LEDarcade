#LEDcommander.py

# ------------------------------------------------------------------------------
# LEDcommander Multiprocessing Architecture and LED Display Initialization
# ------------------------------------------------------------------------------

# This module uses Python's multiprocessing to offload LED display animations
# such as digital clocks and title screens to a dedicated subprocess. It listens
# for command dictionaries via a multiprocessing.Queue and launches a worker
# process per display task.

# ---------------------------
# IMPORTANT: Display + GPIO Access
# ---------------------------

# The LEDarcade module interfaces with LED matrices via GPIO or a framebuffer
# library (such as rpi-rgb-led-matrix). This kind of low-level hardware access
# has constraints in a multiprocessing environment — especially on Linux-based
# systems like Raspberry Pi OS.

# ✅ DO NOT initialize the LED display in the parent process
#    - Importing LEDarcade or calling LED.Initialize() in the main process and
#      then forking (via multiprocessing.Process) can lead to:
#         - corrupted hardware state
#         - no output to the LED panel
#         - silent failures or bus hangs
#
# ✅ Instead, do all display-related setup in the child process:
#    - Import `LEDarcade as LED` INSIDE the worker functions (ShowDigitalClock, ShowTitleScreen).
#    - Call `LED.Initialize()` inside each worker process before any drawing.
#
# Why? On Linux, the default multiprocessing "fork" method copies memory — but
# does NOT safely copy resources like:
#    - GPIO memory mappings
#    - hardware buffers
#    - shared C/C++ resources used by native libraries
#
# Forked children may appear to run, but silently fail to affect the actual LED panel.

# ---------------------------
# Spawn Method (Optional Safety Enhancement)
# ---------------------------
# For stricter isolation, you can switch multiprocessing to "spawn" mode in your
# main application script:
#
#     import multiprocessing
#     multiprocessing.set_start_method("spawn")
#
# This avoids forking entirely and creates new, clean Python interpreter processes.
# It is slightly slower but significantly safer for hardware operations.

# In summary:
#    - Do NOT initialize or use LEDarcade in the main process.
#    - Import and initialize LEDarcade separately inside each display subprocess.
#    - Always test display subprocesses with sudo.


print("")
print("=============================================")
print("== LEDcommander.py                           =")
print("=============================================")
print("")




import time
import traceback


from multiprocessing import Event, Process
import queue

StopEvent = Event()
DisplayProcess = None


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
            print(f"[LEDCommander] Received command: {Command}")

            if not isinstance(Command, dict):
                continue

            Action = Command.get("Action", "").casefold()
            print(f"-->{Action}<--")


            if Action == "showclock":
                print("Starting the clock")
                if DisplayProcess and DisplayProcess.is_alive():
                    print("Clock is already running.  Stopping the clock first then restarting.")
                    StopEvent.set()
                    DisplayProcess.join()

                StopEvent.clear()
                DisplayProcess = Process(target=ShowDigitalClock, args=(Command, StopEvent))
                DisplayProcess.start()


            elif Action == "showtitlescreen":
                print("Showing title screen")
                if DisplayProcess and DisplayProcess.is_alive():
                    print("Clock is already running.  Stopping the clock first then restarting.")
                    StopEvent.set()
                    DisplayProcess.join()

                StopEvent.clear()
                DisplayProcess = Process(target=ShowTitleScreen, args=(Command, StopEvent))
                DisplayProcess.start()


            elif Action == "stopclock":
                print("Stopping the clock")
                StopEvent.set()
                if DisplayProcess and DisplayProcess.is_alive():
                    DisplayProcess.join()


            #----------------------------------
            #-- SCROLL MESSAGES
            #----------------------------------

            elif Action == "scrollmessages":
                while DisplayProcess and DisplayProcess.is_alive():
                    print("[LEDCommander] Display process is still running. Waiting...")
                    time.sleep(0.5)  # Sleep to avoid CPU hogging
                DisplayProcess = Process(target=ScrollMessages, args=(Command, StopEvent))
                DisplayProcess.start()



            #----------------------------------
            #-- TERMINAL MODE
            #----------------------------------
            
            elif Action == "terminalmode_on":
                print("[LEDcommander] RUN: terminalmode_on detected")
                if DisplayProcess and DisplayProcess.is_alive():
                    print("[LEDCommander] Display already active. Waiting...")
                    continue
                StopEvent.clear()
                DisplayProcess = Process(target=RunTerminalMode, args=(Command, CommandQueue, StopEvent))
                DisplayProcess.start()

            elif Action == "terminalmode_off":
                print("[LEDCommander] Exiting TerminalMode.")
                StopEvent.set()
                if DisplayProcess and DisplayProcess.is_alive():
                    DisplayProcess.join()






            elif Action == "quit":
                print("[LEDCommander] Quit received.")
                if DisplayProcess and DisplayProcess.is_alive():
                    StopEvent.set()
                    DisplayProcess.join()
                print("[LEDCommander] Shutdown complete.")
                break  # Exit the loop and end the process



        except queue.Empty:
            print("[LEDCommander] Waiting for command...")
            time.sleep(2)
            continue

        except Exception as Error:
            print(f"[LEDCommander ERROR] {Error}")
            traceback.print_exc()

        


#----------------------------------------------------------
#-- Action functions
#----------------------------------------------------------

def ShowDigitalClock(Command,StopEvent):
    import LEDarcade as LED
    LED.Initialize()

    print("RedR: ",LED.RedR)

    #Sprite display locations ??  maybe not needed
    LED.ClockH,      LED.ClockV,      LED.ClockRGB      = 0,0,  (0,150,0)
    LED.DayOfWeekH,  LED.DayOfWeekV,  LED.DayOfWeekRGB  = 8,20,  (125,20,20)
    LED.MonthH,      LED.MonthV,      LED.MonthRGB      = 28,20, (125,30,0)
    LED.DayOfMonthH, LED.DayOfMonthV, LED.DayOfMonthRGB = 47,20, (115,40,10)

    

    ClockStyle = Command.get("Style", 1)
    ZoomFactor = Command.get("Zoom", 2)
    RunMinutes = Command.get("Duration", 1)
    AnimationDelay = Command.get("Delay", 30)

    print(f"[LEDCommander] Showing clock: Style={ClockStyle}, Zoom={ZoomFactor}, Duration={RunMinutes}")

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
    

    print(f"[LEDCommander] Showing clock: Style={ClockStyle}, Zoom={ZoomFactor}, Duration={RunMinutes}")

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






def ScrollMessages(Command,StopEvent):

    import LEDarcade as LED
    LED.Initialize()

    #LED.ClearBigLED()
    #LED.ClearBuffers()

    ScrollSleep         = 0.025
    TerminalTypeSpeed   = 0.08  #pause in seconds between characters
    TerminalScrollSpeed = 0.08  #pause in seconds between new lines
    CursorRGB           = (0,255,0)
    CursorDarkRGB       = (0,50,0)

    CursorH = 0
    CursorV = 0
    TerminalTypeSpeed 
    

    Messages = Command.get("Messages", [])
    for msg in Messages:
        text        = msg.get("Message", "")
        color       = msg.get("RGB", (255, 255, 255))
        TypeSpeed   = msg.get("ScrollSleep", 0.05)
        ScrollSpeed = msg.get("ScrollSleep", 0.05)
    
        print(f"[LEDCommander] Scrolling terminal text: {msg}")

        LED.ScreenArray,CursorH,CursorV =   LED.TerminalScroll(LED.ScreenArray,
            text,
            CursorH=CursorH,
            CursorV=CursorV,
            MessageRGB=color,
            CursorRGB=(0,255,0),
            CursorDarkRGB=(0,50,0),
            StartingLineFeed=1,
            TypeSpeed=TypeSpeed,
            ScrollSpeed=ScrollSpeed
        )

    LED.ZoomScreen(LED.ScreenArray, 32, 1, Fade=False, ZoomSleep=0.01)



def RunTerminalMode_old(Command, CommandQueue, StopEvent):
    import LEDarcade as LED
    LED.Initialize()
    print("[LEDCommander] TerminalMode activated.")
    CursorH = 0
    CursorV = 0
    CursorRGB     = (0,200,0)
    CursorDarkRGB = (0,50,0)

    TerminalTypeSpeed   = 0.08  #pause in seconds between characters
    TerminalScrollSpeed = 0.08  #pause in seconds between new lines
    CursorRGB           = (0,255,0)
    CursorDarkRGB       = (0,50,0)

    text = Command.get("Message", "NO MESSAGE FOUND")
    rgb  = Command.get("RGB", (255, 255, 255))



    while not StopEvent.is_set():
        try:
                
                print("Message: ",text)


                LED.ScreenArray, CursorH, CursorV = LED.TerminalScroll(
                    LED.ScreenArray,
                    Message=text,
                    CursorH=CursorH,
                    CursorV=CursorV,
                    MessageRGB=rgb,
                    CursorRGB=(0, 255, 0),
                    CursorDarkRGB=(0, 50, 0),
                    StartingLineFeed=1,
                    TypeSpeed=TerminalTypeSpeed,
                    ScrollSpeed=TerminalScrollSpeed
                )

                Command = CommandQueue.get(timeout=0.5)
                #the first command was already pulled from the queue by the calling procedure
                if Command.get("Action", "").lower() == "terminalmessage":
                    text = Command.get("Message", "NO MESSAGE FOUND")
                    rgb = Command.get("RGB", (255, 255, 255))
                    speed = Command.get("ScrollSleep", 0.05)


        except queue.Empty:
            print("[LEDcommander] Queue is empty")
            LED.BlinkCursor(CursorH= CursorH,CursorV=CursorV,CursorRGB=CursorRGB,CursorDarkRGB=CursorDarkRGB,BlinkSpeed=0.25,BlinkCount=1)
            print("[LEDcommander] RunTerminaMode: getting next command")
            continue
\





def RunTerminalMode(CommandQueue, StopEvent, InitialCommand=None):
    import LEDarcade as LED
    LED.Initialize()
    CursorH, CursorV = 0, 0
    print("[LEDCommander] TerminalMode activated.")

    CursorRGB     = (0,200,0)
    CursorDarkRGB = (0,50,0)

    TerminalTypeSpeed   = 0.08  #pause in seconds between characters
    TerminalScrollSpeed = 0.08  #pause in seconds between new lines
    CursorRGB           = (0,255,0)
    CursorDarkRGB       = (0,50,0)


    # Display first message if provided
    if InitialCommand:
        first_msg = InitialCommand.get("Message", None)
        if first_msg:
            color = InitialCommand.get("RGB", (255, 255, 255))
            sleep = InitialCommand.get("ScrollSleep", 0.05)
            LED.ScreenArray, CursorH, CursorV = LED.TerminalScroll(
                LED.ScreenArray,
                Message=first_msg,
                CursorH=CursorH,
                CursorV=CursorV,
                MessageRGB=color,
                CursorRGB=(0, 255, 0),
                CursorDarkRGB=(0, 50, 0),
                StartingLineFeed=1,
                TypeSpeed=TerminalTypeSpeed,
                ScrollSpeed=TerminalScrollSpeed
            )

    # Start listening for future messages
    while not StopEvent.is_set():
        try:
            Command = CommandQueue.get(timeout=0.5)
            if Command.get("Action", "").lower() == "terminalmessage":
                msg = Command.get("Message", "")
                color = Command.get("RGB", (255, 255, 255))
                sleep = Command.get("ScrollSleep", 0.05)

                LED.ScreenArray, CursorH, CursorV = LED.TerminalScroll(
                    LED.ScreenArray,
                    Message=msg,
                    CursorH=CursorH,
                    CursorV=CursorV,
                    MessageRGB=color,
                    CursorRGB=(0, 255, 0),
                    CursorDarkRGB=(0, 50, 0),
                    StartingLineFeed=1,
                    TypeSpeed=TerminalTypeSpeed,
                    ScrollSpeed=TerminalScrollSpeed
                )
        except queue.Empty:
            print("[LEDcommander] Queue is empty")
            LED.BlinkCursor(CursorH= CursorH,CursorV=CursorV,CursorRGB=CursorRGB,CursorDarkRGB=CursorDarkRGB,BlinkSpeed=0.25,BlinkCount=2)
            print("[LEDcommander] RunTerminaMode: getting next command")
            continue





#-------------------------------------------------------------------------------
# Main Processing
#
#-------------------------------------------------------------------------------


if __name__ == "__main__":
    print("Hi there")
