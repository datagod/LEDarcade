import time
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import LEDarcade as LED

# Initialize matrix and LEDarcade
LED.Initialize()
width = LED.HatWidth
height = LED.HatHeight

# Load a system TrueType font
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)




def MakeTimeImage():
    now = datetime.now()
    current_minute = now.strftime("%H:%M")

    # Create blank image and drawing context
    image = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(image)

    # Measure text size and center it using textbbox
    bbox = draw.textbbox((0, 0), current_minute, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (width - text_width) // 2
    y = (height - text_height) // 4
    draw.text((x, y), current_minute, font=font, fill=(0, 200, 0))  # Red
    return image
    

# Display image using LEDarcade canvas
image = MakeTimeImage()
ScreenArray = LED.CopyImageToScreenArray(image, 0, 0)
LED.SpinShrinkTransition(ScreenArray, steps=32, delay=0.01, start_zoom=0, end_zoom=100)


# Clock loop
last_minute = None
try:
    while True:
        now = datetime.now()
        current_minute = now.strftime("%H:%M")

        if current_minute != last_minute:
            image = MakeTimeImage()
            LED.DisplayImage(image)
            last_minute = current_minute

        time.sleep(1)

except KeyboardInterrupt:
    LED.TheMatrix.Clear()

