from multiprocessing import Process, Queue
import LEDcommander
import time

if __name__ == "__main__":


    CommandQueue = Queue()
    LEDProcess = Process(target=LEDcommander.Run, args=(CommandQueue,))
    LEDProcess.start()
    CommandQueue.cancel_join_thread()



    CommandQueue.put({
        "Action": "terminalMode_on",
        "Message": "This is the first terminal message!",
        "RGB": (0, 200, 0),
        "ScrollSleep": 0.03
    })


    CommandQueue.put({
        "Action": "terminalMode_on",
        "Message": "This is the second terminal message!",
        "RGB": (0, 100, 0),
        "ScrollSleep": 0.03
    })


    CommandQueue.put({
        "Action": "terminalMode_on",
        "Message": "This is the third terminal message!",
        "RGB": (0, 200, 255),
        "ScrollSleep": 0.03
    })


    CommandQueue.put({
        "Action": "terminalMode_off",
        "Message": "No message needed",
        "RGB": (0, 200, 0),
        "ScrollSleep": 0.03
    })





    CommandQueue.put({
        "Action": "ScrollMessages",
        "Messages": [
            {"Message": "First message!", "RGB": (255, 0, 0), "ScrollSleep": 0.03},
            {"Message": "Second one here!", "RGB": (0, 255, 0), "ScrollSleep": 0.05},
            {"Message": "Last message in batch.", "RGB": (0, 0, 255), "ScrollSleep": 0.07},
            {"Message": "...................", "RGB": (0, 100, 255), "ScrollSleep": 0.07}]
    })

    CommandQueue.put({
        "Action": "ScrollMessages",
        "Messages": [
            {"Message": "And now we are back from our commercial break.", "RGB": (255, 0, 0), "ScrollSleep": 0.03},
            {"Message": "Did you buy the poopy poopy?", "RGB": (0, 255, 0), "ScrollSleep": 0.05},
            {"Message": "...................", "RGB": (0, 100, 255), "ScrollSleep": 0.07}]
    })




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
