import argparse
from rgbmatrix import RGBMatrix, RGBMatrixOptions

# Parse command-line arguments
parser = argparse.ArgumentParser(description="LEDarcade Configuration")
parser.add_argument("--led-rows", type=int, default=32, help="Number of rows in the LED matrix")
parser.add_argument("--led-cols", type=int, default=64, help="Number of columns in the LED matrix")
parser.add_argument("--led-chain", type=int, default=1, help="Number of daisy-chained LED panels")
parser.add_argument("--led-parallel", type=int, default=1, help="Number of parallel chains")
parser.add_argument("--led-brightness", type=int, default=100, help="Brightness level (0-100)")
parser.add_argument("--led-gpio-slowdown", type=int, default=1, help="GPIO slowdown value")
parser.add_argument("--led-gpio-mapping", type=str, default="regular", help="GPIO mapping (e.g., 'regular', 'adafruit-hat')")
parser.add_argument("--led-scan-mode", type=int, choices=[0, 1], default=1, help="Scan mode: 0=progressive, 1=interlaced")
parser.add_argument("--led-pwm-bits", type=int, default=11, help="PWM bits")
parser.add_argument("--led-pwm-lsb-nanoseconds", type=int, default=130, help="PWM LSB nanoseconds")
parser.add_argument("--led-show-refresh", action="store_true", help="Show refresh rate")
parser.add_argument("--led-no-hardware-pulse", action="store_true", help="Disable hardware pulse")
parser.add_argument("--led-rgb-sequence", type=str, default="RGB", help="RGB sequence")
parser.add_argument("--led-pixel-mapper", type=str, default="", help="Pixel mapper configuration")
parser.add_argument("--led-row-addr-type", type=int, default=0, help="Row address type")
parser.add_argument("--led-multiplexing", type=int, default=0, help="Multiplexing type")
parser.add_argument("--led-panel-type", type=str, default="", help="Panel type")
parser.add_argument("--led-drop-privileges", dest="drop_privileges", action="store_false", help="Don't drop privileges from 'root' after initializing the hardware.")
parser.set_defaults(drop_privileges=True)

args = parser.parse_args()

# Configure RGBMatrixOptions
options = RGBMatrixOptions()
options.rows = args.led_rows
options.cols = args.led_cols
options.chain_length = args.led_chain
options.parallel = args.led_parallel
options.brightness = args.led_brightness
options.gpio_slowdown = args.led_gpio_slowdown
options.hardware_mapping = args.led_gpio_mapping
options.scan_mode = args.led_scan_mode
options.pwm_bits = args.led_pwm_bits
options.pwm_lsb_nanoseconds = args.led_pwm_lsb_nanoseconds
options.show_refresh_rate = int(args.led_show_refresh)
options.disable_hardware_pulsing = args.led_no_hardware_pulse
options.led_rgb_sequence = args.led_rgb_sequence
options.pixel_mapper_config = args.led_pixel_mapper
options.row_address_type = args.led_row_addr_type
options.multiplexing = args.led_multiplexing
options.panel_type = args.led_panel_type
options.drop_privileges = args.drop_privileges

# Initialize the matrix
matrix = RGBMatrix(options=options)
canvas = matrix.CreateFrameCanvas()


# Draw a test pixel
canvas.Clear()
canvas.SetPixel(10, 10, 255, 0, 0)  # red at (10,10)
canvas.SetPixel(10, 11, 255, 0, 0)  # red at (10,10)
canvas.SetPixel(10, 12, 255, 0, 0)  # red at (10,10)
canvas.SetPixel(10, 13, 255, 0, 0)  # red at (10,10)
canvas.SetPixel(10, 14, 255, 0, 0)  # red at (10,10)
matrix.SwapOnVSync(canvas)

input("✅ Red pixel drawn. Press Enter to exit...")
