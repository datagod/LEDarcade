#LEDcommander.py

import time
import traceback
import LEDarcade as LED
from multiprocessing import Event, Process
import queue

StopEvent = Event()
DisplayProcess = None


def Run(CommandQueue):
    global StopEvent
    global DisplayProcess

    while True:
        print("While true print this")
        try:
            Command = CommandQueue.get(timeout=1)
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


            elif Action == "stopclock":
                print("Stopping the clock")
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
            continue

        except Exception as Error:
            print(f"[LEDCommander ERROR] {Error}")
            traceback.print_exc()


def ShowDigitalClock(Command,StopEvent):
    LED.Initialize()

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



#-------------------------------------------------------------------------------
# Main Processing
#
#-------------------------------------------------------------------------------

print("")
print("-----------------")
print("--LED COMMANDER--")
print("-----------------")
print("")

