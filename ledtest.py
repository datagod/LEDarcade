import time
from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics

# ----- CONFIGURE MATRIX OPTIONS -----
options = RGBMatrixOptions()
options.rows = 32
options.cols = 64
options.chain_length = 1
options.parallel = 1
options.hardware_mapping = 'adafruit-hat'       # Adafruit HAT specific
options.gpio_slowdown = 3                       # Adjust if you see flicker
options.brightness = 100                         # Keep this moderate
options.pwm_bits = 11                           # Lower for better timing
options.pwm_lsb_nanoseconds = 500               # Tweak this if needed
options.scan_mode = 0                           # Progressive
options.disable_hardware_pulsing = False
options.drop_privileges = False                 # Avoid permission issues


matrix = RGBMatrix(options=options)
canvas = matrix.CreateFrameCanvas()

# ----- DRAW GRADIENT -----
def draw_color_gradient(color_channel):
    canvas.Clear()
    width = canvas.width
    height = canvas.height

    for x in range(width):
        # Avoid too-dark start: start at 64, end at 255
        level = int(64 + (x / (width - 1)) * (255 - 64))

        if color_channel == "red":
            color = graphics.Color(level, 0, 0)
        elif color_channel == "green":
            color = graphics.Color(0, level, 0)
        elif color_channel == "blue":
            color = graphics.Color(0, 0, level)
        else:
            color = graphics.Color(level, level, level)  # fallback to grayscale

        for y in range(height):
            canvas.SetPixel(x, y, color.red, color.green, color.blue)

    matrix.SwapOnVSync(canvas)

# ----- MAIN -----
colors = ["red", "green", "blue"]
try:
    while True:
        for color in colors:
            draw_color_gradient(color)
            print(f"Displaying {color} gradient...")
            time.sleep(0.2)

except KeyboardInterrupt:
    print("Exiting LED color test.")
