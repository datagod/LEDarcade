# LEDcommander.py - Multiprocessing Command Dispatcher for LEDarcade

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
import random
import itertools  # for generator function


from multiprocessing import Event, Process, Queue
import queue

from flask import Flask, request, jsonify
import logging
import os
import LEDupdate
import LEDpanel

#GLOBAL VARS
RotateClockDelay = 5  # minutes between rotation of different display styles
IsOnAirActive = False
IsStockTickerPinned = False
ON_AIR_DEFAULT_MINUTES = 30
ON_AIR_DEFAULT_SECONDS = ON_AIR_DEFAULT_MINUTES * 60

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_DIR = os.path.join(REPO_DIR, "images")

VALID_WEB_ACTIONS = {
    "showclock": [],
    "stopclock": [],
    "stop": [],
    "showtitlescreen": [
        "BigText", "LittleText", "LittleTextRGB", "ScrollText", "ScrollTextRGB",
        "ScrollSleep", "DisplayTime", "ExitEffect", "LittleTextZoom",
    ],
    "analogclock": [],
    "retrodigital": [],
    "starrynightdisplaytext": ["text1", "text2", "text3"],
    "launch_dotinvaders": ["duration"],
    "launch_defender": ["duration"],
    "launch_defender2": ["duration"],
    "launch_tron": ["duration"],
    "launch_outbreak": ["duration"],
    "launch_outbreak2": ["duration"],
    "launch_outbreak3": ["duration"],
    "launch_outbreak4": ["duration"],
    "launch_ledtv": ["duration", "effect", "youtube_url", "channel"],
    "launch_spacedot": ["duration"],
    "launch_pacdot": ["duration"],
    "launch_dotzerk": ["duration"],
    "launch_blasteroids": ["duration"],
    "launch_stockticker": ["duration", "symbols"],
    "launch_fallingsand": ["duration"],
    "launch_particles": ["duration"],
    "launch_gravitysim": ["duration"],
    "launch_mazecar": ["duration"],
    "launch_spaceexplorer": ["duration"],
    "launch_skyfall": ["duration"],
    "twitchtimer_on": ["StreamStartedDateTime", "StreamDurationHHMMSS"],
    "twitchtimer_off": [],
    "terminalmode_on": ["Message", "RGB", "ScrollSleep"],
    "terminalmessage": ["Message", "RGB", "ScrollSleep"],
    "terminalmode_off": [],
    "weatherterminal": ["Location", "Units", "RGB", "ScrollSleep", "TypeSpeed", "Repeat", "PostScrollWait"],
    "stockterminal": ["symbols", "RGB", "ScrollSleep", "TypeSpeed", "Repeat", "PostScrollWait"],
    "showheart": [],
    "showintro": [],
    "showonair": ["duration"],
    "showonair_off": [],
    "showdemotivate": [],
    "showgif": ["GIF", "loops", "sleep"],
    "showviewers": ["chatusers"],
    "showimagezoom": ["image", "zoommin", "zoommax", "zoomfinal", "sleep", "step"],
    "quit": [],
}


def sanitize_web_command(data, action):
    """Normalize and validate web command fields before queueing."""
    if "Loops" in data and "loops" not in data:
        data["loops"] = data["Loops"]
    if "Image" in data and "image" not in data:
        data["image"] = data["Image"]
    if "Duration" in data and "duration" not in data and action in ["showonair"] + [a for a in VALID_WEB_ACTIONS if a.startswith("launch_")]:
        data["duration"] = data["Duration"]

    for key in data:
        if "RGB" in key and isinstance(data[key], str):
            try:
                data[key] = tuple(map(int, data[key].split(",")))
            except Exception:
                data[key] = (255, 255, 255)

    if action in ["showgif", "showimagezoom", "showtitlescreen", "terminalmode_on", "terminalmessage", "weatherterminal", "showonair", "twitchtimer_on"] or action.startswith("launch_"):
        for key in ["Duration", "loops", "sleep", "ScrollSleep", "DisplayTime", "zoommin", "zoommax", "zoomfinal", "step", "duration"]:
            if key in data:
                try:
                    data[key] = float(data[key]) if '.' in str(data[key]) else int(data[key])
                except ValueError:
                    pass

    if action == "terminalmode_on":
        for key in ["Style", "Speed"]:
            if key in data:
                try:
                    data[key] = int(data[key])
                except ValueError:
                    pass

    if action == "showgif" and "GIF" in data and not str(data["GIF"]).startswith("/"):
        data["GIF"] = os.path.join(IMAGE_DIR, os.path.basename(data["GIF"]))

    if action == "showimagezoom" and "image" in data and not str(data["image"]).startswith("/"):
        data["image"] = os.path.join(IMAGE_DIR, os.path.basename(data["image"]))

    if action == "showviewers" and "chatusers" in data and isinstance(data["chatusers"], str):
        data["chatusers"] = [user.strip() for user in data["chatusers"].split(",") if user.strip()]

    if action == "weatherterminal":
        import WeatherClock as WC
        data["Units"] = WC.NormalizeUnits(data.get("Units", "C"))
        for key in ["TypeSpeed", "ScrollSleep"]:
            if key in data:
                try:
                    data[key] = float(data[key])
                except ValueError:
                    pass
        if "Repeat" in data:
            try:
                data["Repeat"] = max(int(data["Repeat"]), 1)
            except ValueError:
                data["Repeat"] = WC.WEATHER_SCROLL_REPEAT
        if "PostScrollWait" in data:
            try:
                data["PostScrollWait"] = max(float(data["PostScrollWait"]), 0)
            except ValueError:
                data["PostScrollWait"] = WC.WEATHER_POST_SCROLL_WAIT

    if action == "stockterminal":
        import StockReport as SR
        for key in ["TypeSpeed", "ScrollSleep"]:
            if key in data:
                try:
                    data[key] = float(data[key])
                except ValueError:
                    pass
        if "Repeat" in data:
            try:
                data["Repeat"] = max(int(data["Repeat"]), 1)
            except ValueError:
                data["Repeat"] = SR.STOCK_SCROLL_REPEAT
        if "PostScrollWait" in data:
            try:
                data["PostScrollWait"] = max(float(data["PostScrollWait"]), 0)
            except ValueError:
                data["PostScrollWait"] = SR.STOCK_POST_SCROLL_WAIT
        if "symbols" in data:
            parsed = SR.ParseStockSymbols(data["symbols"])
            if parsed:
                data["symbols"] = parsed

    if action == "launch_stockticker" and "symbols" in data:
        if isinstance(data["symbols"], str):
            data["symbols"] = [s.strip().upper() for s in data["symbols"].split(",") if s.strip()]
        elif isinstance(data["symbols"], list):
            data["symbols"] = [str(s).strip().upper() for s in data["symbols"] if str(s).strip()]

    return data



def serve_web_control(queue, port=5055):
    """
    LED Commander web control panel and /command API.
    This is the single source of truth for remote display commands.
    """
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

    app = Flask(__name__)
    LEDupdate.register_update_routes(app, queue)

    @app.route('/command', methods=['POST'])
    def handle_command():
        data = request.get_json() if request.is_json else request.form.to_dict()
        print(f"[LEDcommander][web] Received: {data}")
        action = data.get("Action")
        if isinstance(action, str):
            action = action.lower()
            data["Action"] = action
        print(f"[LEDcommander][web] Action: {action}")
        if not action or action not in VALID_WEB_ACTIONS:
            return jsonify({'status': 'error', 'message': f'Invalid or missing action: {action}'}), 400
        data = sanitize_web_command(data, action)
        allowed_fields = set(VALID_WEB_ACTIONS[action] + ["Action"])
        filtered_data = {k: v for k, v in data.items() if k in allowed_fields}
        queue.put(filtered_data)
        return jsonify({'status': 'ok', 'message': f"Queued: {action}"}), 200

    @app.route('/', methods=['GET'])
    def homepage():
        return LEDpanel.render_homepage(VALID_WEB_ACTIONS)

    app.run(host='0.0.0.0', port=port, threaded=False)

















CursorH   = 0
CursorV   = 0
StopEvent = Event()
DisplayProcess       = None
CurrentDisplayMode   = None
TerminalQueue        = Queue()
ClockFallbackEnabled = True

# Twitch / stream matrix brightness (0–100)
STREAM_GAME_BRIGHTNESS = 70
STREAM_CLOCK_BRIGHTNESS = 80
STREAM_MAX_BRIGHTNESS = 100


def _apply_matrix_brightness(level):
    try:
        import LEDarcade as LED
        LED.TheMatrix.brightness = int(level)
    except Exception:
        pass


def _run_game_dimmed(launch_fn):
    """Run a game at stream game brightness, restore full brightness after."""
    _apply_matrix_brightness(STREAM_GAME_BRIGHTNESS)
    try:
        return launch_fn()
    finally:
        _apply_matrix_brightness(STREAM_MAX_BRIGHTNESS)



def fallback_action_generator():
    # Your sequence from __main__ in the documents; customize durations/styles
    actions = [
        {"Action": "launch_skyfall", "duration": 10},
        {"Action": "retrodigital", "duration": 10},
        {"Action": "showclock", "Style": 5, "Zoom": 1, "duration": 10, "Delay": 10},
        {"Action": "showclock", "Style": 3, "Zoom": 2, "duration": 10, "Delay": 10},
        {"Action": "showclock", "Style": 1, "Zoom": 3, "duration": 10, "Delay": 30},  
        {"Action": "launch_defender", "duration": 10},
        {"Action": "analogclock", "duration": 10 },
        {"Action": "weatherterminal"},
        {"Action": "stockterminal"},

        {"Action": "launch_dotinvaders", "duration": 10},
        {"Action": "retrodigital", "duration": 10},
        {"Action": "launch_gravitysim", "duration": 10},
        {"Action": "retrodigital", "duration": 10},
        {"Action": "launch_tron", "duration": 10},
        {"Action": "retrodigital", "duration": 10},
        {"Action": "launch_outbreak", "duration": 10},
        {"Action": "retrodigital", "duration": 10},
        {"Action": "launch_spacedot", "duration": 10},
        {"Action": "retrodigital", "duration": 10},
        {"Action": "launch_pacdot", "duration": 5},
        {"Action": "retrodigital", "duration": 10},
        {"Action": "launch_dotzerk", "duration": 5},
        {"Action": "retrodigital", "duration": 10},
        {"Action": "launch_spaceexplorer", "duration": 10},
        {"Action": "retrodigital", "duration": 10},
        {"Action": "launch_fallingsand", "duration": 10},
        {"Action": "launch_particles", "duration": 10},
        {"Action": "launch_mazecar", "duration": 10},
    ]
    for action in itertools.cycle(actions):
        yield action

 


def stop_current_display(preempted_by, join_timeout=5):
    """Stop the active display subprocess and log what interrupted it.

    Sets the shared StopEvent so well-behaved games (Skyfall, LEDtv, …) exit
    their loops promptly. Waits up to join_timeout seconds, then terminates
    the process if it is still alive so the next LEDcommander action can run.
    """
    global StopEvent, DisplayProcess, CurrentDisplayMode
    if DisplayProcess and DisplayProcess.is_alive():
        mode = CurrentDisplayMode or "unknown"
        print(f"[LEDcommander] Stopping '{mode}' (preempted by: {preempted_by})")
        try:
            StopEvent.set()
        except Exception:
            pass
        DisplayProcess.join(timeout=join_timeout)
        if DisplayProcess.is_alive():
            print(
                f"[LEDcommander] '{mode}' did not exit after "
                f"{join_timeout}s — terminating process"
            )
            try:
                DisplayProcess.terminate()
            except Exception:
                pass
            DisplayProcess.join(timeout=2)
            if DisplayProcess.is_alive():
                try:
                    DisplayProcess.kill()
                except Exception:
                    pass
                DisplayProcess.join(timeout=1)
        DisplayProcess = None
        if CurrentDisplayMode == mode:
            CurrentDisplayMode = None


def Run(CommandQueue):
    global StopEvent, DisplayProcess, CurrentDisplayMode, TerminalQueue
    global IsOnAirActive, IsStockTickerPinned, FallbackGenerator
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
            # Get command or handle empty
            try:
                Command = CommandQueue.get(timeout=1)
            except queue.Empty:
                # Check for timed-out OnAir
                if IsOnAirActive and DisplayProcess and not DisplayProcess.is_alive():
                    print("[LEDcommander] OnAir timed out, proceeding to next")
                    IsOnAirActive = False
                    CurrentDisplayMode = None
                if IsStockTickerPinned and DisplayProcess and not DisplayProcess.is_alive():
                    print("[LEDcommander] Stock ticker finished, releasing pin")
                    IsStockTickerPinned = False
                    CurrentDisplayMode = None
                # If idle (no OnAir, no pinned stock ticker, no process), pull generator
                if (not IsOnAirActive and not IsStockTickerPinned
                        and (DisplayProcess is None or not DisplayProcess.is_alive())):
                    print("[LEDcommander] Queue empty and idle—using fallback generator")
                    Command = next(FallbackGenerator)
                else:
                    continue  # Wait if something's running

            print(f"[LEDcommander][Run] Received command: {Command}")
            
            if not isinstance(Command, dict):
                continue

            Action = Command.get("Action", "").lower()
            print(f"<-- [LEDcommander] Action: {Action}")

            # Handle off (force stop, proceed)
            if Action == "showonair_off":
                if IsOnAirActive:
                    print("[LEDcommander] Manual stop OnAir, proceeding to next")
                    stop_current_display(Action)
                    IsOnAirActive = False
                continue  # Loop will now pull next queue/generator

            # Handle on (start with duration)
            if Action == "showonair":
                print("[LEDcommander] Starting OnAir")
                stop_current_display(Action)
                StopEvent.clear()
                if "duration" not in Command:
                    Command["duration"] = ON_AIR_DEFAULT_SECONDS
                CurrentDisplayMode = "onair"
                IsOnAirActive = True
                DisplayProcess = Process(target=ShowOnAir, args=(Command, StopEvent))
                DisplayProcess.start()
                continue

            # Explicit stop: clear pin flags and preempt Skyfall / any display
            if Action in ("stop", "stopclock"):
                print(f"[LEDcommander] Stop command ({Action}) — ending '{CurrentDisplayMode}'")
                IsOnAirActive = False
                IsStockTickerPinned = False
                stop_current_display(Action)
                CurrentDisplayMode = "stopped"
                continue

            # While On Air, hold the display until manual off or duration expiry.
            if IsOnAirActive and Action not in ("showonair", "showonair_off", "stop", "stopclock", "quit"):
                print(f"[LEDcommander] OnAir active—ignoring command: {Action}")
                continue

            # While stock ticker is pinned (user set duration), hold until it finishes.
            if (IsStockTickerPinned
                    and Action not in (
                        "launch_stockticker", "showonair", "showonair_off",
                        "quit", "stop", "stopclock",
                    )):
                print(f"[LEDcommander] Stock ticker pinned—ignoring command: {Action}")
                continue



            #----------------------------------
            #-- CLOCK MODE
            #----------------------------------

            if Action == "showclock":
                print("Starting the clock")
                stop_current_display(Action)
                StopEvent.clear()
                CurrentDisplayMode = "clock"
                DisplayProcess = Process(target=ShowDigitalClock, args=(Command, StopEvent))
                DisplayProcess.start()



            #----------------------------------
            #-- TITLE SCREEN
            #----------------------------------

            elif Action == "showtitlescreen":
                print("Showing title screen")
                stop_current_display(Action)

                StopEvent.clear()
                CurrentDisplayMode = "title"
                DisplayProcess = Process(target=ShowTitleScreen, args=(Command, StopEvent))
                DisplayProcess.start()


            #----------------------------------
            #-- ANALOG CLOCK
            #----------------------------------

            elif Action == "analogclock":
                stop_current_display(Action)

                StopEvent.clear()
                CurrentDisplayMode = "clock"
                DisplayProcess = Process(target=ShowAnalogClock, args=(Command, StopEvent))
                DisplayProcess.start()


            elif Action == "retrodigital":
                stop_current_display(Action)

                StopEvent.clear()
                CurrentDisplayMode = "clock"
                DisplayProcess = Process(target=ShowRetroDigital, args=(Command, StopEvent))
                DisplayProcess.start()


            #----------------------------------
            #-- STARRY NIGHT VARIATIONS
            #----------------------------------


            elif Action == "starrynightdisplaytext":
                print("[LEDcommander][Run] Starry Night Display Text")
                stop_current_display(Action)

                StopEvent.clear()
                CurrentDisplayMode = "starrynight"
                DisplayProcess = Process(target=StarryNightDisplayText, args=(Command, StopEvent))
                DisplayProcess.start()



            #----------------------------------
            #-- LAUNCH PROGRAMS
            #----------------------------------


            elif Action == "launch_dotinvaders":
                print("[LEDcommander][Run] Launching DotInvaders")
                stop_current_display(Action)

                StopEvent.clear()
                CurrentDisplayMode = "dotinvaders"
                DisplayProcess = Process(target=LaunchDotInvaders, args=(Command, StopEvent))
                DisplayProcess.start()


            elif Action in ("launch_defender", "launch_defender2"):
                print("[LEDcommander][Run] Launching Defender")
                stop_current_display(Action)

                StopEvent.clear()
                CurrentDisplayMode = "defender"
                DisplayProcess = Process(target=LaunchDefender, args=(Command, StopEvent))
                DisplayProcess.start()


            elif Action == "launch_tron":
                print("[LEDcommander][Run] Launching Tron")
                stop_current_display(Action)

                StopEvent.clear()
                CurrentDisplayMode = "tron"
                DisplayProcess = Process(target=LaunchTron, args=(Command, StopEvent))
                DisplayProcess.start()

            elif Action in ("launch_outbreak", "launch_outbreak2", "launch_outbreak3", "launch_outbreak4"):
                outbreak_labels = {
                    "launch_outbreak": "Outbreak",
                    "launch_outbreak2": "Outbreak2",
                    "launch_outbreak3": "Outbreak3",
                    "launch_outbreak4": "Outbreak4",
                }
                outbreak_modes = {
                    "launch_outbreak": "outbreak",
                    "launch_outbreak2": "outbreak2",
                    "launch_outbreak3": "outbreak3",
                    "launch_outbreak4": "outbreak4",
                }
                outbreak_launchers = {
                    "launch_outbreak": LaunchOutbreak,
                    "launch_outbreak2": LaunchOutbreak2,
                    "launch_outbreak3": LaunchOutbreak3,
                    "launch_outbreak4": LaunchOutbreak4,
                }
                print(f"[LEDcommander][Run] Launching {outbreak_labels[Action]}")
                stop_current_display(Action)

                StopEvent.clear()
                CurrentDisplayMode = outbreak_modes[Action]
                DisplayProcess = Process(target=outbreak_launchers[Action], args=(Command, StopEvent))
                DisplayProcess.start()



            elif Action == "launch_ledtv":
                print("[LEDcommander][Run] Launching LEDtv")
                stop_current_display(Action)

                StopEvent.clear()
                CurrentDisplayMode = "ledtv"
                DisplayProcess = Process(target=LaunchLEDtv, args=(Command, StopEvent))
                DisplayProcess.start()

            elif Action == "launch_spacedot":
                print("[LEDcommander][Run] Launching SpaceDot")
                stop_current_display(Action)

                StopEvent.clear()
                CurrentDisplayMode = "spacedot"
                DisplayProcess = Process(target=LaunchSpaceDot, args=(Command, StopEvent))
                DisplayProcess.start()

            elif Action == "launch_pacdot":
                print("[LEDcommander][Run] Launching PacDot")
                stop_current_display(Action)

                StopEvent.clear()
                CurrentDisplayMode = "pacdot"
                DisplayProcess = Process(target=LaunchPacDot, args=(Command, StopEvent))
                DisplayProcess.start()

            elif Action == "launch_dotzerk":
                print("[LEDcommander][Run] Launching DotZerk")
                stop_current_display(Action)

                StopEvent.clear()
                CurrentDisplayMode = "dotzerk"
                DisplayProcess = Process(target=LaunchDotZerk, args=(Command, StopEvent))
                DisplayProcess.start()


            elif Action == "launch_blasteroids":
                print("[LEDcommander][Run] Launching Blasteroids")
                stop_current_display(Action)

                StopEvent.clear()
                CurrentDisplayMode = "blasteroids"
                DisplayProcess = Process(target=LaunchBlasteroids, args=(Command, StopEvent))
                DisplayProcess.start()



            elif Action == "launch_stockticker":
                duration = Command.get("duration", 10)
                pin = "duration" in Command
                print(f"[LEDcommander][Run] Launching StockTicker (duration={duration} min, pinned={pin})")
                stop_current_display(Action)
                StopEvent.clear()
                CurrentDisplayMode = "stockticker"
                IsStockTickerPinned = pin
                DisplayProcess = Process(target=LaunchStockTicker, args=(Command, StopEvent))
                DisplayProcess.start()



            elif Action == "launch_fallingsand":
                print("[LEDcommander][Run] Launching fallingsand")
                stop_current_display(Action)

                StopEvent.clear()
                CurrentDisplayMode = "tron"
                DisplayProcess = Process(target=LaunchFallingSand, args=(Command, StopEvent))
                DisplayProcess.start()

            elif Action == "launch_particles":
                print("[LEDcommander][Run] Launching Particles")
                stop_current_display(Action)

                StopEvent.clear()
                CurrentDisplayMode = "particles"
                DisplayProcess = Process(target=LaunchParticles, args=(Command, StopEvent))
                DisplayProcess.start()


            elif Action == "launch_gravitysim":
                print("[LEDcommander][Run] Launching GravitySim")
                stop_current_display(Action)

                StopEvent.clear()
                CurrentDisplayMode = "gravitysim"
                DisplayProcess = Process(target=LaunchGravitySim, args=(Command, StopEvent))
                DisplayProcess.start()

            elif Action == "launch_mazecar":
                print("[LEDcommander][Run] Launching MazeCar")
                stop_current_display(Action)

                StopEvent.clear()
                CurrentDisplayMode = "mazecar"
                DisplayProcess = Process(target=LaunchMazeCar, args=(Command, StopEvent))
                DisplayProcess.start()

            elif Action == "launch_spaceexplorer":
                print("[LEDcommander][Run] Launching SpaceExplorer")
                stop_current_display(Action)

                StopEvent.clear()
                CurrentDisplayMode = "spaceexplorer"
                DisplayProcess = Process(target=LaunchSpaceExplorer, args=(Command, StopEvent))
                DisplayProcess.start()

            elif Action == "launch_skyfall":
                print("[LEDcommander][Run] Launching Skyfall")
                stop_current_display(Action)

                StopEvent.clear()
                CurrentDisplayMode = "skyfall"
                DisplayProcess = Process(target=LaunchSkyfall, args=(Command, StopEvent))
                DisplayProcess.start()


            #----------------------------------
            #-- TWITCH TIMER
            #----------------------------------

            elif Action == "twitchtimer_on":
                print("Showing title screen")
                stop_current_display(Action)

                StopEvent.clear()
                CurrentDisplayMode = "twitch"
                DisplayProcess = Process(target=StartTwitchTimer, args=(Command, StopEvent))
                DisplayProcess.start()


            elif Action == "twitchtimer_off":
                print("Showing title screen")
                stop_current_display(Action)

                StopEvent.clear()
                CurrentDisplayMode = "stopped"




            #----------------------------------
            #-- TERMINAL MODE
            #----------------------------------

            elif Action == "terminalmode_on":
                if DisplayProcess and DisplayProcess.is_alive() and CurrentDisplayMode == "terminal":
                    print("[LEDcommander][Run] TerminalMode already active; queueing message.")
                    TerminalQueue.put(Command)
                else:
                    stop_current_display(Action)
                    StopEvent.clear()
                    CurrentDisplayMode = "terminal"
                    TerminalQueue = Queue()
                    DisplayProcess = Process(
                        target=StartTerminalMode,
                        args=(TerminalQueue, StopEvent, Command),
                    )
                    DisplayProcess.start()


            elif Action == "weatherterminal":
                import WeatherClock as WC

                location = WC.LoadWeatherLocation(Command.get("Location", ""))
                units = WC.NormalizeUnits(Command.get("Units", "C"))
                report = WC.FetchWeatherReport(location, units=units)
                terminal_action = "terminalmessage" if (
                    DisplayProcess and DisplayProcess.is_alive() and CurrentDisplayMode == "terminal"
                ) else "terminalmode_on"

                print(f"[LEDcommander] Queueing weather via {terminal_action} for {location}")

                if terminal_action == "terminalmode_on":
                    stop_current_display(Action)

                terminal_cmd = {
                    "Action": terminal_action,
                    "RGB": Command.get("RGB", (0, 200, 0)),
                    "ScrollSleep": Command.get("ScrollSleep", 0.05),
                    "TypeSpeed": Command.get("TypeSpeed", WC.WEATHER_TYPE_SPEED),
                    "Repeat": Command.get("Repeat", WC.WEATHER_SCROLL_REPEAT),
                    "PostScrollWait": Command.get("PostScrollWait", WC.WEATHER_POST_SCROLL_WAIT),
                    "HeaderRGB": WC.WEATHER_HEADER_RGB,
                }
                if isinstance(report, dict):
                    terminal_cmd["MessageHeader"] = report.get("header", "")
                    terminal_cmd["MessageBody"] = report.get("body", "")
                    terminal_cmd["Message"] = " ".join(
                        part for part in [report.get("header", ""), report.get("body", "")] if part
                    )
                else:
                    terminal_cmd["Message"] = report

                CommandQueue.put(terminal_cmd)


            elif Action == "stockterminal":
                import StockReport as SR

                symbols = Command.get("symbols")
                if isinstance(symbols, str) and not symbols.strip():
                    symbols = None
                report = SR.FetchStockReport(symbols)
                terminal_action = "terminalmessage" if (
                    DisplayProcess and DisplayProcess.is_alive() and CurrentDisplayMode == "terminal"
                ) else "terminalmode_on"

                print(f"[LEDcommander] Queueing stock report via {terminal_action}")

                if terminal_action == "terminalmode_on":
                    stop_current_display(Action)

                terminal_cmd = {
                    "Action": terminal_action,
                    "RGB": Command.get("RGB", (0, 200, 0)),
                    "ScrollSleep": Command.get("ScrollSleep", 0.05),
                    "TypeSpeed": Command.get("TypeSpeed", SR.STOCK_TYPE_SPEED),
                    "Repeat": Command.get("Repeat", SR.STOCK_SCROLL_REPEAT),
                    "PostScrollWait": Command.get("PostScrollWait", SR.STOCK_POST_SCROLL_WAIT),
                    "HeaderRGB": SR.STOCK_HEADER_RGB,
                    "SymbolRGB": SR.STOCK_SYMBOL_RGB,
                    "StockLines": report.get("stock_lines", []),
                    "MessageHeader": report.get("header", ""),
                    "MessageBody": report.get("body", ""),
                    "Message": " ".join(
                        part for part in [report.get("header", ""), report.get("body", "")] if part
                    ),
                }
                if report.get("errors"):
                    terminal_cmd["ErrorText"] = f"Unavailable: {', '.join(report['errors'])}."

                CommandQueue.put(terminal_cmd)


            elif Action == "terminalmessage":
                if DisplayProcess and DisplayProcess.is_alive() and CurrentDisplayMode == "terminal":
                    TerminalQueue.put(Command)
                else:
                    print("[LEDcommander] TerminalMode not active. Auto-starting it.")
                    stop_current_display(Action)
                    StopEvent.clear()
                    CurrentDisplayMode = "terminal"
                    TerminalQueue = Queue()  # reset queue to avoid stale messages
                    DisplayProcess = Process(target=StartTerminalMode, args=(TerminalQueue, StopEvent, Command))
                    DisplayProcess.start()

            # In StartTerminalMode(), replace CommandQueue with TerminalQueue


            elif Action == "terminalmode_off":
                print("[LEDcommander] terminalmode_OFF detected")
                stop_current_display(Action)
                StopEvent.clear()
                CurrentDisplayMode = "stopped"
                print("[LEDcommander] TerminalMode stopped.")



            #----------------------------------------
            # ANIMATIONS                           --
            #----------------------------------------

            elif Action == "showheart":
                stop_current_display(Action)

                StopEvent.clear()
                CurrentDisplayMode = "heart"
                DisplayProcess = Process(target=ShowHeart, args=(Command, StopEvent))
                DisplayProcess.start()



            elif Action == "showintro":
                print("[LEDcommander][Run] Launching Intro")
                stop_current_display(Action)

                StopEvent.clear()
                CurrentDisplayMode = "showintro"
                DisplayProcess = Process(target=ShowIntro, args=(Command, StopEvent))
                DisplayProcess.start()





            elif Action == "showdemotivate":
                print("[LEDcommander][Run] Launching Demotivate")
                stop_current_display(Action)

                StopEvent.clear()
                CurrentDisplayMode = "showdemotivate"
                DisplayProcess = Process(target=ShowDemotivate, args=(Command, StopEvent))
                DisplayProcess.start()



            elif Action == "showgif":
                stop_current_display(Action)
                StopEvent.clear()
                CurrentDisplayMode = "gif"
                DisplayProcess = Process(target=ShowGIF, args=(Command, StopEvent))
                DisplayProcess.start()


            elif Action == "showviewers":
                stop_current_display(Action)
                StopEvent.clear()
                CurrentDisplayMode = "gif"
                DisplayProcess = Process(target=ShowViewers, args=(Command, StopEvent))
                DisplayProcess.start()


            elif Action == "showimagezoom":
                stop_current_display(Action)
                StopEvent.clear()
                CurrentDisplayMode = "image"
                DisplayProcess = Process(target=ShowImageZoom, args=(Command, StopEvent))
                
                #After showing Image, we restart the clock
                CommandQueue.put(OldCommand)
                DisplayProcess.start()



            elif Action == "quit":
                print("[LEDcommander] Quit received.")
                stop_current_display(Action)
                print("[LEDcommander][Run] Shutdown complete.")
                break  # Exit the loop and end the process


        except Exception as e:
            print(f"[LEDcommander] Run error: {e}")
            traceback.print_exc()
            if ClockFallbackEnabled:
                CommandQueue.put({"Action": "showclock"})  # Fallback









#----------------------------------------------------------
#-- Action functions
#----------------------------------------------------------

def ShowDigitalClock(Command,StopEvent):
    import LEDarcade as LED
    LED.Initialize()

    print("RedR: ",LED.RedR)

    ClockStyle = Command.get("Style", 1)
    ZoomFactor = Command.get("Zoom", 2)
    RunMinutes = Command.get("duration", 1)
    AnimationDelay = Command.get("Delay", 30)

    print(
        f"[LEDcommander] Showing clock: Style={ClockStyle}, Zoom={ZoomFactor}, "
        f"Duration={RunMinutes}, brightness={STREAM_CLOCK_BRIGHTNESS}"
    )

    try:
        LED.TheMatrix.brightness = STREAM_CLOCK_BRIGHTNESS
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
    finally:
        _apply_matrix_brightness(STREAM_MAX_BRIGHTNESS)



def ShowRetroDigital(Command,StopEvent):
    import LEDarcade as LED
    LED.Initialize()

    ClockStyle = Command.get("Style", 4)
    ZoomFactor = Command.get("Zoom", 1)
    RunMinutes = Command.get("duration", 5)
    AnimationDelay = Command.get("Delay", 30)

    print(
        f"[LEDcommander] Showing retro clock: Style={ClockStyle}, Zoom={ZoomFactor}, "
        f"Duration={RunMinutes}, brightness={STREAM_CLOCK_BRIGHTNESS}"
    )

    try:
        LED.TheMatrix.brightness = STREAM_CLOCK_BRIGHTNESS
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
    finally:
        _apply_matrix_brightness(STREAM_MAX_BRIGHTNESS)












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
        MessageRGB=(100,100,0),
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
        nonlocal CursorH, CursorV
        print("=========================")
        print("== STOP TERMINAL MODE ==")
        print("=========================")
        LED.ScreenArray, CursorH, CursorV = LED.TerminalScroll(
            LED.ScreenArray,
            Message="Stopping terminal...",
            CursorH=CursorH,
            CursorV=CursorV,
            MessageRGB=(0,200, 0),
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
                    type_speed = Command.get("TypeSpeed", TerminalTypeSpeed)
                    repeat = max(int(Command.get("Repeat", 1)), 1)
                    header = Command.get("MessageHeader", "")
                    body = Command.get("MessageBody", "")
                    header_rgb = Command.get("HeaderRGB", (200, 200, 0))
                    stock_lines = Command.get("StockLines", [])
                    symbol_rgb = Command.get("SymbolRGB", (200, 0, 200))
                    error_text = Command.get("ErrorText", "")

                    for repeat_index in range(repeat):
                        if stock_lines:
                            import StockReport as SR
                            if header:
                                LED.ScreenArray, CursorH, CursorV = LED.TerminalScroll(
                                    LED.ScreenArray, header + " ",
                                    CursorH=CursorH, CursorV=CursorV,
                                    MessageRGB=header_rgb,
                                    CursorRGB=CursorRGB, CursorDarkRGB=CursorDarkRGB,
                                    StartingLineFeed=1,
                                    TypeSpeed=type_speed,
                                    ScrollSpeed=scroll_speed
                                )
                            for stock_index, entry in enumerate(stock_lines):
                                blank_line_count = (
                                    SR.STOCK_BLANK_LINES_BEFORE_FIRST
                                    if stock_index == 0
                                    else SR.STOCK_BLANK_LINES_BETWEEN
                                )
                                for _ in range(blank_line_count):
                                    LED.ScreenArray, CursorH, CursorV = LED.TerminalScroll(
                                        LED.ScreenArray, "",
                                        CursorH=CursorH, CursorV=CursorV,
                                        MessageRGB=rgb,
                                        CursorRGB=CursorRGB, CursorDarkRGB=CursorDarkRGB,
                                        StartingLineFeed=1,
                                        TypeSpeed=0,
                                        ScrollSpeed=scroll_speed
                                    )

                                symbol = entry.get("symbol", "")
                                if symbol:
                                    LED.ScreenArray, CursorH, CursorV = LED.TerminalScroll(
                                        LED.ScreenArray, symbol,
                                        CursorH=CursorH, CursorV=CursorV,
                                        MessageRGB=symbol_rgb,
                                        CursorRGB=CursorRGB, CursorDarkRGB=CursorDarkRGB,
                                        StartingLineFeed=0,
                                        TypeSpeed=type_speed,
                                        ScrollSpeed=scroll_speed
                                    )

                                for detail_line in entry.get("detail_lines", []):
                                    LED.ScreenArray, CursorH, CursorV = LED.TerminalScroll(
                                        LED.ScreenArray, detail_line,
                                        CursorH=CursorH, CursorV=CursorV,
                                        MessageRGB=rgb,
                                        CursorRGB=CursorRGB, CursorDarkRGB=CursorDarkRGB,
                                        StartingLineFeed=1,
                                        TypeSpeed=type_speed,
                                        ScrollSpeed=scroll_speed
                                    )
                            if error_text:
                                LED.ScreenArray, CursorH, CursorV = LED.TerminalScroll(
                                    LED.ScreenArray, error_text,
                                    CursorH=CursorH, CursorV=CursorV,
                                    MessageRGB=rgb,
                                    CursorRGB=CursorRGB, CursorDarkRGB=CursorDarkRGB,
                                    StartingLineFeed=1,
                                    TypeSpeed=type_speed,
                                    ScrollSpeed=scroll_speed
                                )
                        elif header and body:
                            LED.ScreenArray, CursorH, CursorV = LED.TerminalScroll(
                                LED.ScreenArray, header,
                                CursorH=CursorH, CursorV=CursorV,
                                MessageRGB=header_rgb,
                                CursorRGB=CursorRGB, CursorDarkRGB=CursorDarkRGB,
                                StartingLineFeed=1,
                                TypeSpeed=type_speed,
                                ScrollSpeed=scroll_speed
                            )
                            LED.ScreenArray, CursorH, CursorV = LED.TerminalScroll(
                                LED.ScreenArray, body,
                                CursorH=CursorH, CursorV=CursorV,
                                MessageRGB=rgb,
                                CursorRGB=CursorRGB, CursorDarkRGB=CursorDarkRGB,
                                StartingLineFeed=0,
                                TypeSpeed=type_speed,
                                ScrollSpeed=scroll_speed
                            )
                        else:
                            LED.ScreenArray, CursorH, CursorV = LED.TerminalScroll(
                                LED.ScreenArray, msg,
                                CursorH=CursorH, CursorV=CursorV,
                                MessageRGB=rgb,
                                CursorRGB=CursorRGB, CursorDarkRGB=CursorDarkRGB,
                                StartingLineFeed=1,
                                TypeSpeed=type_speed,
                                ScrollSpeed=scroll_speed
                            )

                        if repeat_index < repeat - 1:
                            LED.ScreenArray, CursorH, CursorV = LED.TerminalScroll(
                                LED.ScreenArray, "",
                                CursorH=CursorH, CursorV=CursorV,
                                MessageRGB=rgb,
                                CursorRGB=CursorRGB, CursorDarkRGB=CursorDarkRGB,
                                StartingLineFeed=1,
                                TypeSpeed=0,
                                ScrollSpeed=scroll_speed
                            )

                    if "PostScrollWait" in Command:
                        post_scroll_wait = float(Command.get("PostScrollWait", 0))
                        if post_scroll_wait > 0:
                            print(f"[TerminalMode] Post-scroll wait: {post_scroll_wait}s")
                            wait_end = time.time() + post_scroll_wait
                            while time.time() < wait_end and not StopEvent.is_set():
                                LED.BlinkCursor(
                                    CursorH=CursorH,
                                    CursorV=CursorV,
                                    CursorRGB=CursorRGB,
                                    CursorDarkRGB=CursorDarkRGB,
                                    BlinkSpeed=0.50,
                                    BlinkCount=2
                                )
                        if not StopEvent.is_set():
                            _StopTerminalMode()
                            StopEvent.set()
                            break
                else:
                    print("[TerminalMode] Skipped invalid or missing 'Message'.")

        except Exception as e:
            print(f"[TerminalMode] Error: {e}")

        if StopEvent.is_set():
            break

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
    GifBrightness    = 50
    MaxBrightness    = 100
    print("[LEDcommander][ShowHeart] Show beating heart")

    LED.TheMatrix.brightness = GifBrightness
    LED.ShowBeatingHeart(h=16, v=0, beats=5, Sleep=0.01) 
    LED.TheMatrix.brightness = MaxBrightness
    LED.SweepClean()



def ShowOnAir(Command, StopEvent):
    import LEDarcade as LED
    LED.Initialize()

    MaxBrightness = 100

    duration_str = Command.get("duration", ON_AIR_DEFAULT_SECONDS)
    try:
        duration = int(duration_str)
        if duration <= 0:
            duration = ON_AIR_DEFAULT_SECONDS
    except (ValueError, TypeError):
        print(f"[LEDcommander][ShowOnAir] Invalid duration provided, using default {ON_AIR_DEFAULT_SECONDS}s")
        duration = ON_AIR_DEFAULT_SECONDS

    print(f"[LEDcommander][ShowOnAir] Show ON AIR sign for {duration}s ({duration / 60:.0f} minutes)")

    LED.TheMatrix.brightness = MaxBrightness
    LED.ShowOnAir(StopEvent, duration=duration)

    print("[LEDcommander][ShowOnAir] Ending")
    if StopEvent.is_set():
        print("[LEDcommander][ShowOnAir] Stopped by showonair_off")
    else:
        print("[LEDcommander][ShowOnAir] Duration expired")
    LED.ZoomScreen(LED.ScreenArray, 32, 1, Fade=True, ZoomSleep=0.05)



def ShowOnAir_old(Command, StopEvent):
    import LEDarcade as LED
    LED.Initialize()

    StreamBrightness = 80
    GifBrightness    = 50
    MaxBrightness    = 100
    try:
      duration = int(Command.get("duration", 1800))
    except ValueError:
      duration = 1800
    print("[LEDcommander][ShowOnAir] Show ON AIR sign",duration)

    LED.TheMatrix.brightness = MaxBrightness
    LED.ShowOnAir(StopEvent,duration=duration) 
    LED.ZoomScreen(LED.ScreenArray, 32, 1, Fade=True, ZoomSleep=0.05)

    #LED.SweepClean()



def ShowIntro(Command, StopEvent):
    import LEDarcade as LED
    LED.Initialize()

    StreamBrightness = 80
    GifBrightness    = 50
    MaxBrightness    = 100
    print("[LEDcommander][ShowIntro] Now scrolling text, star wars style")


    LED.TheMatrix.brightness = MaxBrightness
    LED.scroll_random_movie_intro(StopEvent=StopEvent)
    LED.SweepClean()


def ShowDemotivate(Command, StopEvent):
    import LEDarcade as LED
    LED.Initialize()

    StreamBrightness = 80
    GifBrightness    = 50
    MaxBrightness    = 100
    print("[LEDcommander][ShowDemotivate] Now scrolling text, star wars style")


    LED.TheMatrix.brightness = MaxBrightness
    LED.scroll_random_demotivational_quote(StopEvent=StopEvent)
    LED.SweepClean()



def ShowGIF(Command, StopEvent):
    import LEDarcade as LED
    LED.Initialize()

    StreamBrightness = 80
    GifBrightness    = 50
    MaxBrightness    = 100

    GIF              = Command.get("GIF",'./images/redalert.gif')
    loops            = Command.get("loops",5)
    sleep            = Command.get("sleep",0.06)

    print("[LEDcommander][ShowGIF] displaying a GIF: ",GIF)

    LED.TheMatrix.brightness = GifBrightness
    LED.DisplayGIF(GIFName=GIF,width=64,height=32,Loops=loops,sleep=sleep)
    LED.TheMatrix.brightness = MaxBrightness
    LED.SweepClean()




def ShowViewers(Command, StopEvent):
    import LEDarcade as LED
    LED.Initialize()

    StreamBrightness = 80
    GifBrightness    = 50
    MaxBrightness    = 100

    print("[LEDcommander][ShowViewers] Showing image" )

    ChatUsers = Command.get("chatusers",["Nobody"])


    LED.TheMatrix.brightness = GifBrightness
    LED.ScrollJustJoinedUser(ChatUsers,'JustJoined.png',0.04)
    LED.TheMatrix.brightness = MaxBrightness
    
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
    zoommax          = Command.get("zoommax",100)
    zoomfinal        = Command.get("zoomfinal",16)
    sleep            = Command.get("sleep",0.001)
    step             = Command.get("step",1)

    print("[LEDcommander][ShowImageZoom] Zoom an image  ZoomMin ZoomMax ZoomFinal",zoommin, zoommax, zoomfinal)
    

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

    Duration         = Command.get("duration",1)

    print("[LEDcommander][LaunchDotInvaders] Launching...")
    try:
        _run_game_dimmed(
            lambda: DI.LaunchDotInvaders(Duration=Duration, ShowIntro=True, StopEvent=StopEvent)
        )
    finally:
        LED.SweepClean()



def LaunchDefender(Command, StopEvent):
    import LEDarcade as LED
    LED.Initialize()
    import Defender2 as DE
    Duration         = Command.get("duration",1)
    print(f"[LEDcommander][LaunchDefender] Launching Defender2 for {Duration} minutes...")
    try:
        _run_game_dimmed(
            lambda: DE.LaunchDefender2(Duration=Duration, ShowIntro=True, StopEvent=StopEvent)
        )
    finally:
        LED.SweepClean()


def LaunchGravitySim(Command, StopEvent):
    import LEDarcade as LED
    LED.Initialize()
    import gravitysim as GR
    Duration         = Command.get("duration",30)
    if Duration=='':
        Duration = 30
    print("[LEDcommander][LaunchGravitySim] Launching...")
    _run_game_dimmed(
        lambda: GR.Launch(Duration=Duration, ShowIntro=True, StopEvent=StopEvent)
    )


def LaunchTron(Command, StopEvent):
    import LEDarcade as LED
    LED.Initialize()
    import Tron as TR
    Duration         = Command.get("duration",10)
    print("[LEDcommander][LaunchTron] Launching...")
    _run_game_dimmed(
        lambda: TR.LaunchTron(Duration=Duration, ShowIntro=True, StopEvent=StopEvent)
    )


def LaunchSpaceDot(Command, StopEvent):
    import LEDarcade as LED
    LED.Initialize()
    import SpaceDot as SD
    Duration         = Command.get("duration",10)
    print("[LEDcommander][LaunchSpaceDot] Launching...")
    _run_game_dimmed(
        lambda: SD.LaunchSpaceDot(Duration=Duration, ShowIntro=True, StopEvent=StopEvent)
    )


def LaunchPacDot(Command, StopEvent):
    import LEDarcade as LED
    LED.Initialize()
    import PacDot as PD
    Duration = Command.get("duration", 5)
    if Duration == "" or Duration is None:
        Duration = 5
    try:
        Duration = int(Duration)
    except (TypeError, ValueError):
        Duration = 5
    print(f"[LEDcommander][LaunchPacDot] Launching PacDot for {Duration} minutes...")
    try:
        _run_game_dimmed(
            lambda: PD.LaunchPacDot(Duration=Duration, ShowIntro=True, StopEvent=StopEvent)
        )
    finally:
        LED.SweepClean()
    print("[LEDcommander][LaunchPacDot] PacDot finished — returning to rotation")


def LaunchDotZerk(Command, StopEvent):
    import LEDarcade as LED
    LED.Initialize()
    import DotZerk as DZ
    Duration = Command.get("duration", 5)
    if Duration == "" or Duration is None:
        Duration = 5
    try:
        Duration = int(Duration)
    except (TypeError, ValueError):
        Duration = 5
    print(f"[LEDcommander][LaunchDotZerk] Launching DotZerk for {Duration} minutes...")
    try:
        _run_game_dimmed(
            lambda: DZ.LaunchDotZerk(Duration=Duration, ShowIntro=True, StopEvent=StopEvent)
        )
    finally:
        LED.SweepClean()
    print("[LEDcommander][LaunchDotZerk] DotZerk finished — returning to rotation")


def LaunchOutbreak(Command, StopEvent):
    import LEDarcade as LED
    LED.Initialize()
    import Outbreak as OB
    Duration         = Command.get("duration",10)
    print("[LEDcommander][LaunchOutbreak] Launching...")
    _run_game_dimmed(
        lambda: OB.LaunchOutbreak(Duration=Duration, ShowIntro=True, StopEvent=StopEvent)
    )


def LaunchOutbreak2(Command, StopEvent):
    import LEDarcade as LED
    LED.Initialize()
    import Outbreak2 as OB2
    Duration         = Command.get("duration",10)
    print("[LEDcommander][LaunchOutbreak2] Launching...")
    _run_game_dimmed(
        lambda: OB2.LaunchOutbreak2(Duration=Duration, ShowIntro=True, StopEvent=StopEvent)
    )


def LaunchOutbreak3(Command, StopEvent):
    import LEDarcade as LED
    LED.Initialize()
    import Outbreak3 as OB3
    Duration         = Command.get("duration",10)
    print("[LEDcommander][LaunchOutbreak3] Launching...")
    _run_game_dimmed(
        lambda: OB3.LaunchOutbreak3(Duration=Duration, ShowIntro=True, StopEvent=StopEvent)
    )


def LaunchOutbreak4(Command, StopEvent):
    import LEDarcade as LED
    LED.Initialize()
    import Outbreak4 as OB4
    Duration = Command.get("duration", 10)
    print("[LEDcommander][LaunchOutbreak4] Launching...")
    _run_game_dimmed(
        lambda: OB4.LaunchOutbreak4(duration=Duration, show_intro=True, stop_event=StopEvent)
    )


def LaunchLEDtv(Command, StopEvent):
    import LEDarcade as LED
    LED.Initialize()
    import LEDtv as TV
    # Default: 5 min channel surf — title drop → static → flashes → video
    # Only switches to YouTube/local play when a non-empty URL is provided.
    Duration = Command.get("duration", 5)
    try:
        Duration = float(Duration) if Duration not in (None, "") else 5.0
    except (TypeError, ValueError):
        Duration = 5.0
    YoutubeUrl = Command.get("youtube_url") or Command.get("url") or ""
    YoutubeUrl = str(YoutubeUrl).strip() or None
    Channel = Command.get("channel")
    if Channel is not None and str(Channel).strip() == "":
        Channel = None
    elif Channel is not None:
        try:
            Channel = int(Channel)
        except (TypeError, ValueError):
            Channel = None
    # Empty/missing URL → always full channel-surf sequence (ignore blank effect)
    if YoutubeUrl:
        Effect = (Command.get("effect") or "youtube")
    else:
        Effect = "channels"
    # show_intro / boot_intro: ?tv full cold open; ?tvN tunes fast (no title/static)
    ShowIntro = Command.get("show_intro", True)
    if isinstance(ShowIntro, str):
        ShowIntro = ShowIntro.strip().lower() not in ("0", "false", "no", "off")
    BootIntro = Command.get("boot_intro", True)
    if isinstance(BootIntro, str):
        BootIntro = BootIntro.strip().lower() not in ("0", "false", "no", "off")
    # Tuning to a channel: skip intros unless explicitly requested
    if Channel is not None and "show_intro" not in Command:
        ShowIntro = False
    if Channel is not None and "boot_intro" not in Command:
        BootIntro = False
    print(
        "[LEDcommander][LaunchLEDtv] duration={} effect={!r} url={!r} "
        "channel={!r} intro={} boot={} brightness={}".format(
            Duration, Effect, YoutubeUrl, Channel, ShowIntro, BootIntro,
            STREAM_GAME_BRIGHTNESS,
        )
    )
    try:
        _run_game_dimmed(
            lambda: TV.LaunchLEDtv(
                duration=Duration,
                show_intro=bool(ShowIntro),
                stop_event=StopEvent,
                effect=Effect,
                youtube_url=YoutubeUrl,
                channel=Channel,
                boot_intro=bool(BootIntro),
            )
        )
    finally:
        try:
            LED.SweepClean()
        except Exception:
            pass


def LaunchBlasteroids(Command, StopEvent):
    import LEDarcade as LED
    #LED.Initialize()
    import Blasteroids as BL
    Duration         = Command.get("duration",10)
    print("[LEDcommander][LaunchBlasteroids] Launching...")
    _run_game_dimmed(
        lambda: BL.LaunchBlasteroids(Duration=Duration, ShowIntro=True, StopEvent=StopEvent)
    )


def LaunchStockTicker(Command, StopEvent):
    import LEDarcade as LED
    #LED.Initialize()
    import StockTicker as ST
    Duration         = Command.get("duration",10)
    Symbols          = Command.get("symbols")
    print("[LEDcommander][LaunchStockTicker] Launching...")
    ST.main(Duration=Duration, StopEvent=StopEvent, Symbols=Symbols)




def LaunchMazeCar(Command, StopEvent):
    import LEDarcade as LED
    LED.Initialize()
    import MazeCar as MC
    Duration = Command.get("duration", 10)
    print(f"[LEDcommander][LaunchMazeCar] Launching for {Duration} minutes...")
    _run_game_dimmed(
        lambda: MC.LaunchMazeCar(Duration=Duration, ShowIntro=True, StopEvent=StopEvent)
    )


def LaunchSpaceExplorer(Command, StopEvent):
    import LEDarcade as LED
    LED.Initialize()
    import SpaceExplorer as SE
    Duration = Command.get("duration", 10)
    print(f"[LEDcommander][LaunchSpaceExplorer] Launching for {Duration} minutes...")
    _run_game_dimmed(
        lambda: SE.LaunchSpaceExplorer(Duration=Duration, ShowIntro=False, StopEvent=StopEvent)
    )


def LaunchSkyfall(Command, StopEvent):
    import LEDarcade as LED
    LED.Initialize()
    import Skyfall as SF
    Duration = Command.get("duration", 10)
    try:
        Duration = float(Duration) if Duration not in (None, "") else 10.0
    except (TypeError, ValueError):
        Duration = 10.0
    print(
        f"[LEDcommander][LaunchSkyfall] Launching for {Duration} minutes "
        f"(StopEvent wired, brightness={STREAM_GAME_BRIGHTNESS})..."
    )
    try:
        _run_game_dimmed(
            lambda: SF.LaunchSkyfall(Duration=Duration, ShowIntro=False, StopEvent=StopEvent)
        )
    finally:
        print("[LEDcommander][LaunchSkyfall] Process exit")
        try:
            LED.ClearBigLED()
            LED.ClearBuffers()
        except Exception:
            pass


def LaunchFallingSand(Command, StopEvent):
    import LEDarcade as LED
    LED.Initialize()
    import FallingSand as FS
    Duration         = Command.get("duration",10)
    print("[LEDcommander][LaunchFallingSand] Launching...")
    _run_game_dimmed(
        lambda: FS.LaunchFallingSand(Duration=Duration, ShowIntro=True, StopEvent=StopEvent)
    )


def LaunchParticles(Command, StopEvent):
    import LEDarcade as LED
    LED.Initialize()
    import particles as PT
    Duration = Command.get("duration", 10)
    print(f"[LEDcommander][LaunchParticles] Launching for {Duration} minutes...")
    _run_game_dimmed(
        lambda: PT.LaunchParticles(Duration=Duration, ShowIntro=False, StopEvent=StopEvent)
    )



def ShowAnalogClock(Command, StopEvent):
    import LEDarcade as LED
    LED.Initialize()
    import AnalogClock as AC
    Duration         = Command.get("duration",10)
    print(f"[LEDcommander][ShowAnalogClock] Launching... brightness={STREAM_CLOCK_BRIGHTNESS}")

    try:
        LED.TheMatrix.brightness = STREAM_CLOCK_BRIGHTNESS
        AC.RunClock(Duration=Duration, StopEvent=StopEvent)
    finally:
        _apply_matrix_brightness(STREAM_MAX_BRIGHTNESS)





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
    ScrollSleep = 0.01,
    RunSeconds  = 30
    )







#-------------------------------------------------------------------------------
# Main Processing
#
#-------------------------------------------------------------------------------
FallbackGenerator = fallback_action_generator()

if __name__ == "__main__":
    LEDupdate.save_launcher("LEDcommander.py")

    CommandQueue = Queue()
    commander_process = Process(target=Run, args=(CommandQueue,))
    commander_process.start()

    webserver_process = Process(target=serve_web_control, args=(CommandQueue,))
    webserver_process.start()

    print("")
    print("[LEDcommander][main] Processes started")
    
    # Remove joins for now
    # commander_process.join()
    # webserver_process.join()

    # Keep main thread alive so child processes aren't killed.
    # Display rotation when idle is handled inside Run(); do not push timed
    # commands here — that loop preempted web-panel launches every RotateClockDelay minutes.
    while True:
        time.sleep(60)


