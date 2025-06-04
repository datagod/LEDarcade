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

# Clock loop
try:
    while True:
        now = datetime.now().strftime("%H:%M")

        # Create blank image and drawing context
        image = Image.new("RGB", (width, height))
        draw = ImageDraw.Draw(image)

        # Measure text size and center it using textbbox
        bbox = draw.textbbox((0, 0), now, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (width - text_width) // 2
        y = (height - text_height) // 4
        draw.text((x, y), now, font=font, fill=(255, 0, 0))  # Red

        # Display image using LEDarcade canvas
        # Force image directly to matrix
        
        LED.ShowBeatingImageObject(image, h=0, v=0, beats=10, Sleep=0)
        
        LED.DisplayImage(image)
        time.sleep(1)

except KeyboardInterrupt:
    LED.TheMatrix.Clear()
