# %%

import LEDarcade as LED
from rgbmatrix import graphics
from rgbmatrix import RGBMatrix, RGBMatrixOptions
import time
import random
import requests
from bs4 import BeautifulSoup
import pprint

#Variable declaration section
ScrollSleep   = 0.025
HatHeight     = 32
HatWidth      = 64
url         = "https://www.twingalaxies.com/activity.php?do=viewactivites"


print ("---------------------------------------------------------------")
print ("TWIN GALAXIES - ACTIVITY MONITOR")
print ("")
print ("BY DATAGOD")
print ("")
print ("This program will demonstrate several LED functions that have")
print ("been developed as part of the Arcade Retro Clock RGB project.")
print ("---------------------------------------------------------------")
print ("")
print ("")



# Your HTML content
html_content = '''<div class="cardOne warningBorder dbtech_vbshout_shout alt1" name="dbtech_vbshout_shoutwrapper" data-instanceid="15" data-shoutid="3457826" style="">
    <!-- Other HTML content -->
    <div class="nomouseover popupmenu memberaction">
        <a class="popupctrl" href="javascript://" name="dbtech_vbshout_togglemenu" data-instanceid="15" data-userid="489402" data-shoutid="3458490">Scott Hawkins</a>
    </div>
    <!-- Other HTML content -->
</div>'''

# Parse the HTML content
soup = BeautifulSoup(html_content, 'html.parser')

# Find the div element with the specific class and name attributes
div_element = soup.find('div', {'class': 'cardOne warningBorder dbtech_vbshout_shout alt1', 'name': 'dbtech_vbshout_shoutwrapper'})

# Find the nested div element with class 'nomouseover popupmenu memberaction'
nested_div = div_element.find('div', {'class': 'nomouseover popupmenu memberaction'})

# Find the a element within the nested div
a_element = nested_div.find('a', {'class': 'popupctrl'})

# Extract the user information
user_name = a_element.text
user_id = a_element['data-userid']
shout_id = a_element['data-shoutid']

print(f"User Name: {user_name}")
print(f"User ID: {user_id}")
print(f"Shout ID: {shout_id}")
