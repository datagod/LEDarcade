from multiprocessing import Process, Queue
import LEDcommander as LED
import time

if __name__ == "__main__":
    CommandQueue = Queue()
    LEDProcess = Process(target=LED.Run, args=(CommandQueue,))
    LEDProcess.start()
    CommandQueue.cancel_join_thread()

    CommandQueue.put({
        "Action": "ShowClock",
        "Style": 1,
        "Zoom": 2,
        "Duration": 1,
        "Delay": 5
    })

    # Let it run for a bit
    time.sleep(1)

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
