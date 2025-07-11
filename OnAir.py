from multiprocessing import Process, Queue
import LEDcommander
import time
import os

def wait_for_terminalmode_to_start():
    # Simulate waiting for subprocess to initialize
    print("[Test] Waiting for TerminalMode to start...")
    time.sleep(2)


if __name__ == "__main__":
    CommandQueue = Queue()
    LEDProcess = Process(target=LEDcommander.Run, args=(CommandQueue,))
    LEDProcess.start()
    CommandQueue.cancel_join_thread()

    CommandQueue.put({"Action": "showonair"})
  
