from multiprocessing import Process, Queue
import LEDcommander
import time

if __name__ == "__main__":


    CommandQueue = Queue()
    LEDProcess = Process(target=LEDcommander.Run, args=(CommandQueue,))
    LEDProcess.start()
    CommandQueue.cancel_join_thread()

    time.sleep(1)

    CommandQueue.put({
    "Action": "scrollmessages",
    "Messages": [
        {"Message": "Welcome to the Matrix!", "RGB": (0, 255, 0), "ScrollSleep": 0.03},
        {"Message": "Enjoy the pixel ride.", "RGB": (0, 200, 255), "ScrollSleep": 0.04},
        {"Message": "Datagod says hi.", "RGB": (255, 100, 0), "ScrollSleep": 0.05}
    ]
    })

    time.sleep(3)

    CommandQueue.put({
        "Action": "terminalmode_on",
        "RGB": (0, 200, 0),
        "ScrollSleep": 0.03
    })

    time.sleep(3)

    CommandQueue.put({
        "Action": "terminalmessage",
        "Message": "Welcome to the Jungle",
        "RGB": (0, 100, 0),
        "ScrollSleep": 0.03
    })

    time.sleep(3)

    CommandQueue.put({
        "Action": "terminalmessage",
        "Message": "We got plenty of cake",
        "RGB": (0, 255, 0),
        "ScrollSleep": 0.03
    })
    time.sleep(3)
    CommandQueue.put({
        "Action": "terminalmessage",
        "Message": "What da??",
        "RGB": (255, 0, 0),
        "ScrollSleep": 0.03
    })
    time.sleep(3)

    CommandQueue.put({
        "Action": "terminalmode_off",
        "Message": "No message needed",
        "RGB": (0, 200, 0),
        "ScrollSleep": 0.03
    })


    time.sleep(20)
    CommandQueue.put({
        "Action": "Quit",
        "Messages": "quit"
    })



    # Let it run for a bit
    #time.sleep(500)

    # Turn off the clock
    CommandQueue.put({"Action": "StopClock"})
    time.sleep(500)
   
    print("QUIT NOW!")
    
    # Ask LEDCommander to shut down fully
    CommandQueue.put({"Action": "Quit"})

    # Give the subprocess a moment to receive the message
    time.sleep(0.1)

    # Now join with a timeout
    LEDProcess.join(timeout=3)


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





    if LEDProcess.is_alive():
        print("[Main] LEDCommander still alive — terminating.")
        LEDProcess.terminate()
        LEDProcess.join()

    print("[Main] Shutdown complete.")
