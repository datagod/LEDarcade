from multiprocessing import Process, Queue
import LEDcommander
import time
import os

def wait_for_terminalmode_to_start():
    # Simulate waiting for subprocess to initialize
    print("[Test] Waiting for TerminalMode to start...")
    time.sleep(2)



def enqueue_gif_commands(CommandQueue, folder='./images/', loops=2, sleep=0.06):
    print("Folder: ",folder)
    for filename in sorted(os.listdir(folder)):
        if filename.lower().endswith('.gif'):
            gif_path = os.path.join(folder, filename)
            print("File: ",gif_path)
            CommandQueue.put({
                "Action": "showgif",
                "GIF": gif_path,
                "Loops": 5,
                "sleep": sleep
            })





if __name__ == "__main__":
    CommandQueue = Queue()
    LEDProcess = Process(target=LEDcommander.Run, args=(CommandQueue,))
    LEDProcess.start()
    CommandQueue.cancel_join_thread()

    #enqueue_gif_commands(CommandQueue)
    #CommandQueue.put({        "Action": "showheart",    })

    CommandQueue.put({"Action": "showheart" })
    time.sleep(25)



    #Formulate the command.      
    CommandQueue.put({        "Action": "launch_gravitysim",   "Duration": 5})




    CommandQueue.put({        "Action": "launch_defender",     "Duration": 5})
    CommandQueue.put({        "Action": "launch_dotinvaders",  "Duration": 5})
   
    time.sleep(2)



    #Formulate the command.      
    CommandQueue.put({
        "Action": "ShowClock",
        "Style": 1,
        "Zoom": 3 ,
        "Duration": 1,  # minutes
        "Delay": 10
    })
   
    time.sleep(2)

    CommandQueue.put({
        "Action": "terminalmode_on",
        "Message": "Message 0",
        "RGB": (0, 0, 200),
        "ScrollSleep": 0.03
    })

    time.sleep(2)


    CommandQueue.put({
        "Action": "terminalmessage",
        "Message": "Message 1",
        "RGB": (0, 0, 200),
        "ScrollSleep": 0.03
    })


    CommandQueue.put({
        "Action": "terminalmessage",
        "Message": "Message 2",
        "RGB": (0, 0, 200),
        "ScrollSleep": 0.03
    })

    CommandQueue.put({
        "Action": "terminalmessage",
        "Message": "Message 3",
        "RGB": (0, 0, 200),
        "ScrollSleep": 0.03
    })




    time.sleep(300)


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
        "BigTextRGB": (200, 0, 200),
        "BigTextShadowRGB": (40, 0, 40),
        "LittleText": "NO STREAM",
        "LittleTextRGB": (200, 0, 0),
        "LittleTextShadowRGB": (100, 0, 0),
        "ScrollText": "Stream not active. Try again later...",
        "ScrollTextRGB": (200, 200, 0),
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
