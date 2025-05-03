from rgbmatrix import RGBMatrix, graphics

options = graphics.ParseOptions()
matrix = RGBMatrix(options=options)

canvas = matrix.CreateFrameCanvas()
canvas.Clear()
canvas.SetPixel(10, 10, 255, 0, 0)  # Red pixel
matrix.SwapOnVSync(canvas)
