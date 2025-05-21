from multiprocessing import Process, Queue
import LEDcommander
import time

if __name__ == "__main__":




    CommandQueue = Queue()
    LEDProcess = Process(target=LEDcommander.Run, args=(CommandQueue,))
    LEDProcess.start()
    CommandQueue.cancel_join_thread()




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






    # Let it run for a bit
    time.sleep(500)

    # Turn off the clock
    CommandQueue.put({"Action": "StopClock"})
    time.sleep(5)
   
    print("QUIT NOW!")
    
    # Ask LEDCommander to shut down fully
    CommandQueue.put({"Action": "Quit"})

    # Give the subprocess a moment to receive the message
    time.sleep(0.1)

    # Now join with a timeout
    LEDProcess.join(timeout=3)


    if LEDProcess.is_alive():
        print("[Main] LEDCommander still alive — terminating.")
        LEDProcess.terminate()
        LEDProcess.join()

    print("[Main] Shutdown complete.")
