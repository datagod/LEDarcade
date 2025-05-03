from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
import time

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
font = graphics.Font()
font.LoadFont("rpi-rgb-led-matrix/fonts/6x10.bdf")

# -------------------------------
# Colors
# -------------------------------
red   = graphics.Color(255, 0, 0)
green = graphics.Color(0, 255, 0)
blue  = graphics.Color(0, 0, 255)
white = graphics.Color(255, 255, 255)

# -------------------------------
# Main loop
# -------------------------------
while True:
    canvas.Clear()

    # Draw some lines
    graphics.DrawLine(canvas, 0, 0, 63, 31, red)
    graphics.DrawLine(canvas, 0, 31, 63, 0, green)
    graphics.DrawLine(canvas, 0, 16, 63, 16, blue)

    # Draw some text
    graphics.DrawText(canvas, font, 2, 10, white, "Hello")
    graphics.DrawText(canvas, font, 2, 22, red,   "Datagod")

    canvas = matrix.SwapOnVSync(canvas)
    time.sleep(0.05)
