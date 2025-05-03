from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
import time
import random


# -------------------------------
# Matrix Options
# -------------------------------
options = RGBMatrixOptions()
options.rows = 32
options.cols = 64
options.chain_length = 1
options.parallel = 1
options.hardware_mapping = 'adafruit-hat'       # Adafruit HAT specific
options.gpio_slowdown = 3                       # Adjust if you see flicker
options.brightness = 60                         # Keep this moderate
options.pwm_bits = 7                            # Lower for better timing
options.pwm_lsb_nanoseconds = 250               # Tweak this if needed
options.scan_mode = 0                           # Progressive
options.disable_hardware_pulsing = False
options.drop_privileges = False                 # Avoid permission issues

# -------------------------------
# Create Matrix and Canvas
# -------------------------------
matrix = RGBMatrix(options=options)
canvas = matrix.CreateFrameCanvas()

# -------------------------------
# Load font
# -------------------------------

# -------------------------------
# Colors
# -------------------------------
red   = graphics.Color(255, 0, 0)
green = graphics.Color(0, 255, 0)
blue  = graphics.Color(0, 0, 255)
white = graphics.Color(255, 255, 255)



# -------------------------------
# Color generator
# -------------------------------
def random_color():
    return graphics.Color(random.randint(50, 255), random.randint(50, 255), random.randint(50, 255))


# -------------------------------
# Main loop
# -------------------------------
while True:

    for _ in range(10):  # draw 10 random lines
        x1 = random.randint(0, 63)
        y1 = random.randint(0, 31)
        x2 = random.randint(0, 63)
        y2 = random.randint(0, 31)
        color = random_color()
        graphics.DrawLine(canvas, x1, y1, x2, y2, color)    


    canvas = matrix.SwapOnVSync(canvas)
    
