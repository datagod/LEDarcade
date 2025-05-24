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
    #CommandQueue.put({
    #    "Action": "terminalmode_on",
    #    "Message": "CHAT MODE ON",
    #    "RGB": (0, 200, 0),
    #    "ScrollSleep": 0.03
    #})

    #wait_for_terminalmode_to_start()
    #time.sleep(5)


    CommandQueue.put({
        "Action": "terminalmessage",
        "Message": "Hello World!",
        "RGB": (0, 0, 200),
        "ScrollSleep": 0.03
    })

    time.sleep(5)

    CommandQueue.put({
        "Action": "terminalmessage",
        "Message": "Welcome to the jungle. We have plenty of cake.  Take me down to paradise city where girls are fat and the burgers are plenty.",
        "RGB": (0, 200, 0),
        "ScrollSleep": 0.03
    })



    CommandQueue.put({
        "Action": "terminalmessage",
        "Message": "This is so strange why won't it work c'mon man this is joe biden talkin here good buddy lets go ok.",
        "RGB": (0, 200, 0),
        "ScrollSleep": 0.03
    })




    time.sleep(300)


    CommandQueue.put({
        "Action": "terminalmessage",
        "RGB": (0, 200, 0),
        "ScrollSleep": 0.03
    })


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
