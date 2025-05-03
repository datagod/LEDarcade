from rgbmatrix import RGBMatrix, RGBMatrixOptions

options = RGBMatrixOptions()
options.rows = HatHeight        # From your config
options.cols = HatWidth         # From your config
options.chain_length = 1
options.parallel = 1
options.brightness = 100
options.scan_mode = 1
options.gpio_slowdown = 5

# Only works if your version supports it; if not, skip it or run via CLI
# options.hardware_mapping = "adafruit-hat"

TheMatrix = RGBMatrix(options=options)
Canvas = TheMatrix.CreateFrameCanvas()
