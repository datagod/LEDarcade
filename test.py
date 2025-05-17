# %%
import LEDarcade as LED

# test_clock.py
import multiprocessing
import time

def SpawnClock(EventQueue, AnimationDelay, StreamActive, SharedState):
    print("SpawnClock - Running")
    SharedState["DigitalClockSpawned"] = True

    LED.DisplayDigitalClock(
                ClockStyle=1,  # change back to r later
                CenterHoriz=True,
                v=1,
                hh=24,
                RGB=LED.LowGreen,
                ShadowRGB=LED.ShadowGreen,
                ZoomFactor=2,
                AnimationDelay=5,
                RunMinutes=1,
                EventQueue=EventQueue
            )



    SharedState["DigitalClockSpawned"] = False
    print("SpawnClock - Done")

def main():
    multiprocessing.set_start_method("spawn", force=True)
    
    manager = multiprocessing.Manager()
    queue = manager.Queue()
    shared = manager.dict()
    shared["DigitalClockSpawned"] = False

    proc = multiprocessing.Process(
        target=SpawnClock,
        args=(queue, 0.01, False, shared)
    )
    proc.start()
    proc.join()
    print("Final state:", shared["DigitalClockSpawned"])

if __name__ == "__main__":
    main()
