from multiprocessing import Process
from rgbmatrix import RGBMatrix, RGBMatrixOptions
import time

def show_color(brightness):
    options = RGBMatrixOptions()
    options.rows = 32
    options.cols = 64
    options.chain_length = 1
    options.parallel = 1
    options.hardware_mapping = 'adafruit-hat'
    options.brightness = brightness
    options.gpio_slowdown = 3

    print(f"[Child] Creating matrix with brightness: {brightness}")
    matrix = RGBMatrix(options=options)
    matrix.brightness = brightness  # enforce

    canvas = matrix.CreateFrameCanvas()
    canvas.Fill(255, 0, 0)
    canvas = matrix.SwapOnVSync(canvas)

    print(f"[Child] Actual brightness: {matrix.brightness}")
    time.sleep(1)

if __name__ == "__main__":
    print("[Main] Starting child process...")
    proc = Process(target=show_color, args=(10,))
    proc.start()
    proc.join()

    proc = Process(target=show_color, args=(25,))
    proc.start()
    proc.join()

    proc = Process(target=show_color, args=(50,))
    proc.start()
    proc.join()


    proc = Process(target=show_color, args=(100,))
    proc.start()
    proc.join()

    print("[Main] Done.")
