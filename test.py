from multiprocessing import Process, Queue
import LEDcommander
import time

def wait_for_terminalmode_to_start():
    # Simulate waiting for subprocess to initialize
    print("[Test] Waiting for TerminalMode to start...")
    time.sleep(2)

if __name__ == "__main__":
    CommandQueue = Queue()
    LEDProcess = Process(target=LEDcommander.Run, args=(CommandQueue,))
    LEDProcess.start()
    CommandQueue.cancel_join_thread()

    time.sleep(1)

    # Start TerminalMode
    CommandQueue.put({
        "Action": "terminalmode_on",
        "RGB": (0, 200, 0),
        "ScrollSleep": 0.03
    })

    wait_for_terminalmode_to_start()

    # Send scrollmessages once
    scroll_block = [
        {"Message": "Welcome to the Matrix!", "RGB": (0, 255, 0), "ScrollSleep": 0.03},
        {"Message": "Enjoy the pixel ride.", "RGB": (0, 200, 255), "ScrollSleep": 0.04},
        {"Message": "Datagod says hi.", "RGB": (255, 100, 0), "ScrollSleep": 0.05}
    ]

    CommandQueue.put({
        "Action": "scrollmessages",
        "Messages": scroll_block
    })

    time.sleep(3)

    # Send a few terminal messages
    for msg, rgb in [
        ("Welcome to the Jungle", (0, 100, 0)),
        ("We got plenty of cake", (0, 255, 0)),
        ("What da??", (255, 0, 0))
    ]:
        CommandQueue.put({
            "Action": "terminalmessage",
            "Message": msg,
            "RGB": rgb,
            "ScrollSleep": 0.03
        })
        time.sleep(3)

    # Shutdown TerminalMode
    CommandQueue.put({
        "Action": "terminalmode_off"
    })

    # Let system idle before shutdown
    time.sleep(10)

    # Send TitleScreen (post terminal)
    print("Sending ShowTitleScreen command...")
    CommandQueue.put({
        "Action": "ShowTitleScreen",
        "BigText": "404",
        "BigTextRGB": (255, 0, 255),
        "BigTextShadowRGB": (100, 0, 100),
        "LittleText": "NO STREAM",
        "LittleTextRGB": (255, 0, 0),
        "LittleTextShadowRGB": (100, 0, 0),
        "ScrollText": "Stream not active. Try again later...",
        "ScrollTextRGB": (255, 255, 0),
        "ScrollSleep": 0.05,
        "DisplayTime": 15,
        "ExitEffect": 5,
        "LittleTextZoom": 1
    })

    time.sleep(5)

    # Final shutdown
    CommandQueue.put({"Action": "Quit"})
    LEDProcess.join(timeout=3)

    if LEDProcess.is_alive():
        print("[Main] LEDCommander still alive — terminating.")
        LEDProcess.terminate()
        LEDProcess.join()

    print("[Main] Shutdown complete.")
