
'''
Requirements: geopy
> sudo pip3 install geopy
> sudo pip3 install FlightRadar24API
'''


import os
os.system('cls||clear')
import sys
import requests
import json
import time
import geopy.distance
import LEDarcade as LED
from configparser import SafeConfigParser


from opensky_api import OpenSkyApi
api = OpenSkyApi()
s = api.get_states()
print(s)



#---------------------------------------
#Variable declaration section
#---------------------------------------

ConfigFileName = "FlightConfig.ini"
ScrollSleep = 0.015
TerminalTypeSpeed = 0
TerminalScrollSpeed = 0
CursorRGB = (0, 0, 0)
CursorDarkRGB = (0, 0, 0)
LastGetFlightsTime = time.time()
GetFlightsWaitMinutes = 5

URL = ''
BaseLat = 0.0
BaseLon = 0.0
Bounds = ''
Dump1090URL = ''



OriginAirport         = ''
DestinationAirport    = ''
AircraftType          = ''
AirlineName           = ''
AirlineShortName      = ''
AirportList           = []


#Files
ConfigFileName = "FlightConfig.ini" 








#----------------------------------------
#-- FILE ACCESS Functions              --
#----------------------------------------


ConfigFileName = "FlightConfig.ini"
ScrollSleep = 0.015
TerminalTypeSpeed = 0
TerminalScrollSpeed = 0
CursorRGB = (0, 0, 0)
CursorDarkRGB = (0, 0, 0)
LastGetFlightsTime = time.time()
GetFlightsWaitMinutes = 5

URL = ''
BaseLat = 0.0
BaseLon = 0.0
Bounds = ''
Dump1090URL = ''

def LoadConfigFile():
    global URL, BaseLat, BaseLon, Bounds, Dump1090URL

    print("--Load Config values--")
    
    if os.path.exists(ConfigFileName):
        print(f"Config file ({ConfigFileName}): found")
        KeyFile = SafeConfigParser()
        KeyFile.read(ConfigFileName)

        URL = KeyFile.get("FLIGHT", "URL", fallback="")
        BaseLat = float(KeyFile.get("FLIGHT", "BaseLat"))
        BaseLon = float(KeyFile.get("FLIGHT", "BaseLon"))
        Bounds = KeyFile.get("FLIGHT", "Bounds")
        Dump1090URL = KeyFile.get("FLIGHT", "Dump1090URL", fallback="http://localhost:8080/data/aircraft.json")

        print("---------------------------------------------")
        print(f"URL:            {URL}")
        print(f"BaseLat:        {BaseLat}")
        print(f"BaseLon:        {BaseLon}")
        print(f"Bounds:         {Bounds}")
        print(f"Dump1090URL:    {Dump1090URL}")
        print("---------------------------------------------")
    else:
        print(f"ERROR: Could not locate Key file ({ConfigFileName}).")
        sys.exit(1)









def LoadConfigFile_old():

  global URL
  global BaseLat
  global BaseLon
  global Bounds


  print ("--Load Config values--")
  if (os.path.exists(ConfigFileName)):

    print ("Config file (",ConfigFileName,"): found")
    KeyFile = SafeConfigParser()
    KeyFile.read(ConfigFileName)

    #Get tokens
    URL             = KeyFile.get("FLIGHT","URL")
    BaseLat         = KeyFile.get("FLIGHT","BaseLat")
    BaseLon         = KeyFile.get("FLIGHT","BaseLon")
    Bounds          = KeyFile.get("FLIGHT","Bounds")

    print (" ")

    print ("---------------------------------------------")
    print("Dump1090URL:    ",URL)   
    print("BaseLat:        ",BaseLat)   
    print("BaseLon:        ",BaseLon)   
    print ("---------------------------------------------")
    print (" ")

  else:
    #To be finished later
    print ("ERROR: Could not locate Key file (",ConfigFileName,"). Create a file and make sure to pupulate it with your own keys.")







def GetFlightsInBounds(Bounds):
    print("\n--GetFlightsInBounds--")
    print(f"Bounds: {Bounds}")
    
    try:
        print(f"Fetching data from: {Dump1090URL}")
        response = requests.get(Dump1090URL, timeout=5)
        print(f"HTTP Status Code: {response.status_code}")
        print(f"Raw Response: {response.text}")
        response.raise_for_status()
        aircraft_list = response.json()
        print(f"Aircraft List: {aircraft_list}")
        
        # Log detailed aircraft data
        print("\n--Aircraft Details--")
        aircraft_data = aircraft_list.get('aircraft', [])
        print(f"Total Aircraft: {len(aircraft_data)}")
        for i, ac in enumerate(aircraft_data):
            print(f"Aircraft {i}:")
            print(f"  Hex: {ac.get('hex', 'N/A')}")
            print(f"  Lat: {ac.get('lat', 'N/A')}")
            print(f"  Lon: {ac.get('lon', 'N/A')}")
            print(f"  Altitude: {ac.get('altitude', 'N/A')}")
            print(f"  Speed: {ac.get('speed', 'N/A')}")
            print(f"  Squawk: {ac.get('squawk', 'N/A')}")
            print(f"  Flight: {ac.get('flight', 'N/A')}")
            print(f"  Track: {ac.get('track', 'N/A')}")
            print(f"  All Keys: {list(ac.keys())}")
        
        lat1, lat2, lon1, lon2 = map(float, Bounds.split(','))
        lat_min, lat_max = min(lat1, lat2), max(lat1, lat2)
        lon_min, lon_max = min(lon1, lon2), max(lon1, lon2)
        print(f"\nBounds Filter: Lat [{lat_min}, {lat_max}], Lon [{lon_min}, {lon_max}]")
        
        filtered_aircraft = [
            {
                'hex': ac.get('hex', ''),
                'latitude': ac.get('lat', 0),
                'longitude': ac.get('lon', 0),
                'altitude': ac.get('altitude', 0),
                'ground_speed': ac.get('speed', 0),
                'squawk': ac.get('squawk', '0000'),
                'callsign': ac.get('flight', 'UNKNOWN').strip(),
                'track': ac.get('track', 0),
                'id': ac.get('hex', '')
            }
            for ac in aircraft_data
            if 'lat' in ac and 'lon' in ac
            and isinstance(ac['lat'], (int, float)) and isinstance(ac['lon'], (int, float))
            and lat_min <= ac['lat'] <= lat_max
            and lon_min <= ac['lon'] <= lon_max
        ]
        
        print(f"\nFiltered Aircraft: {filtered_aircraft}")
        print(f"Flights: {len(filtered_aircraft)}")
        if not filtered_aircraft and aircraft_data:
            print("Warning: No aircraft within bounds. Check Bounds or aircraft coordinates.")
        
        return filtered_aircraft
    except Exception as e:
        print(f"Error fetching Dump1090 data: {e}")
        return []


def GetNearbyFlights(DetailedFlightList):
    print("\n--GetNearbyFlights--")

    if not DetailedFlightList:
        print("**No flight data available**")
        LED.Canvas.Clear()
        no_data_sprite = LED.CreateBannerSprite("NO DATA")
        LED.Canvas = LED.CopySpriteToCanvasZoom(no_data_sprite, 0, 0, (255, 0, 0), (0, 0, 0), 1, False, LED.Canvas)
        LED.Canvas = LED.TheMatrix.SwapOnVSync(LED.Canvas)
        return None

    i = 0
    ShortestDistance = 10000000
    ClosestFlight = -1

    for flight in DetailedFlightList:
        try:
            lat = flight['latitude']
            lon = flight['longitude']
            distance = geopy.distance.geodesic((lat, lon), (BaseLat, BaseLon)).m / 1000
            if distance <= ShortestDistance:
                ShortestDistance = distance
                ClosestFlight = i
        except Exception as e:
            print(f"Record: {i}, error: {e}")
        i += 1

    if ClosestFlight >= 0:
        flight = DetailedFlightList[ClosestFlight]

        Flight = flight['callsign'] or "UNKNOWN"
        Category = "N/A"
        Distance = ShortestDistance
        Speed = flight['ground_speed'] * 1.852 if flight['ground_speed'] else 0
        Squawk = flight['squawk'] or "0000"
        AircraftCount = i
        Hex = flight['hex'].upper()

        print("\n** Closest Aircraft **")
        print(f'Record:   {ClosestFlight}')
        print(f'Hex:      {Hex}')
        print(f'Flight:   {Flight}')
        print(f'Category: {Category}')
        print(f'Distance: {Distance:.2f} km')
        print(f'Speed:    {Speed:.2f} km/h')
        print(f'Squawk:   {Squawk}')
        print(f'Aircraft: {AircraftCount}')

        TitleRGB = (0, 150, 0)
        ValueRGB = (150, 75, 0)

        TitleFlight = LED.CreateBannerSprite("Flight")
        TitleDistance = LED.CreateBannerSprite("Dist")
        TitleSpeed = LED.CreateBannerSprite("kph")
        TitleSquawk = LED.CreateBannerSprite("Sqwk")
        TitleAircraftCount = LED.CreateBannerSprite("UP")
        TitleCategory = LED.CreateBannerSprite("CAT")

        ValueFlight = LED.CreateBannerSprite(Flight)
        ValueDistance = LED.CreateBannerSprite(f"{Distance:.2f}")
        ValueSpeed = LED.CreateBannerSprite(f"{Speed:.1f}")
        ValueSquawk = LED.CreateBannerSprite(Squawk)
        ValueAircraftCount = LED.CreateBannerSprite(str(AircraftCount))
        ValueCategory = LED.CreateBannerSprite(Category)

        LED.Canvas.Clear()
        LED.Canvas = LED.CopySpriteToCanvasZoom(TitleFlight, 0, 0, TitleRGB, (0, 5, 0), 1, False, LED.Canvas)
        LED.Canvas = LED.CopySpriteToCanvasZoom(ValueFlight, 28, 0, ValueRGB, (0, 5, 0), 1, False, LED.Canvas)

        LED.Canvas = LED.CopySpriteToCanvasZoom(TitleDistance, 0, 6, TitleRGB, (0, 5, 0), 1, False, LED.Canvas)
        LED.Canvas = LED.CopySpriteToCanvasZoom(ValueDistance, 28, 6, ValueRGB, (0, 5, 0), 1, False, LED.Canvas)

        LED.Canvas = LED.CopySpriteToCanvasZoom(TitleCategory, 63, 0, TitleRGB, (0, 5, 0), 1, False, LED.Canvas)
        LED.Canvas = LED.CopySpriteToCanvasZoom(ValueCategory, 81, 0, ValueRGB, (0, 5, 0), 1, False, LED.Canvas)

        LED.Canvas = LED.CopySpriteToCanvasZoom(TitleSpeed, 63, 6, TitleRGB, (0, 5, 0), 1, False, LED.Canvas)
        LED.Canvas = LED.CopySpriteToCanvasZoom(ValueSpeed, 81, 6, ValueRGB, (0, 5, 0), 1, False, LED.Canvas)

        LED.Canvas = LED.TheMatrix.SwapOnVSync(LED.Canvas)
    else:
        print("**No flight data found**")
        LED.Canvas.Clear()
        no_data_sprite = LED.CreateBannerSprite("NO DATA")
        LED.Canvas = LED.CopySpriteToCanvasZoom(no_data_sprite, 0, 0, (255, 0, 0), (0, 0, 0), 1, False, LED.Canvas)
        LED.Canvas = LED.TheMatrix.SwapOnVSync(LED.Canvas)
        return None

    return Hex
  


def GetFlightDetails(FlightList):
    print("\n--GetFlightDetails--")
    print(f"FlightList length: {len(FlightList)}")
    return FlightList



def LookupFlightDetails(Hex,DetailedFlightList):
  global OriginAirport
  global DestinationAirport
  global AircraftType 
  global AirlineName
  global AirlineShortName

  print("")
  print("--LookupFlightDetails--")
    
  try:
    print("Hex: ",Hex)
    for flight in DetailedFlightList:
      print("Examining:",flight.icao_24bit)
    
      if flight.icao_24bit and flight.icao_24bit.upper() == Hex.upper():

        #print("Flying to", flight.destination_airport_name)
        pp.pprint(flight.id)
        pp.pprint(flight.icao_24bit)   #Hex
        pp.pprint(flight.callsign)
        pp.pprint(flight.aircraft_code)
        pp.pprint(flight.squawk)
        pp.pprint(flight.registration)
        pp.pprint(flight.origin_airport_iata)
        pp.pprint(flight.destination_airport_iata)
        pp.pprint(flight.number)
        pp.pprint(flight.airline_iata)
        pp.pprint(flight.aircraft_model)
        AircraftType       = flight.aircraft_model
        OriginAirport      = flight.origin_airport_iata
        DestinationAirport = flight.destination_airport_iata
        AirlineName        = flight.airline_name
        AirlineShortName   = flight.airline_short_name
        break


  except:
    print("Data problem")

  return


def GetAirportList():
  global AirportList
  
  print("")
  print("--GetAirportList--")
  AirportList = fr_api.get_airports()
  print("Airports:",len(AirportList))
  print ("-----------------")
  print("")



  #for Airport in AirportList:
  #  print("===============================")
  #  pp.pprint(Airport)


def GetAirport(AirportIata):
  print("")
  print("--GetAirport--")  
  print("Searching for:",AirportIata)
  

  AirportName = ""

  try:
    #Search a list of dictionairies 
    Index = (next((i for i, x in enumerate(AirportList) if x['iata'] == AirportIata), None))
    print("Index:",Index)
    if(Index != None):
      pp.pprint(AirportList[Index])
      AirportName = AirportList[Index]["name"]
  except:
    print("Airport not found")
  return AirportName
  

#------------------------------------------------------------------------------
#  __  __    _    ___ _   _     ____  _____ ____ _____ ___ ___  _   _
# |  \/  |  / \  |_ _| \ | |   / ___|| ____/ ___|_   _|_ _/ _ \| \ | |
# | |\/| | / _ \  | ||  \| |   \___ \|  _|| |     | |  | | | | |  \| |
# | |  | |/ ___ \ | || |\  |    ___) | |__| |___  | |  | | |_| | |\  |
# |_|  |_/_/   \_\___|_| \_|   |____/|_____\____| |_| |___\___/|_| \_|
#
#------------------------------------------------------------------------------




print ("")
print ("")
print ("---------------------------------------------------------------")
print ("Flight - Display nearby aircraft                               ")
print ("")
print ("BY DATAGOD")
print ("")
print ("This program access a local dump1090 installation to get a     ")
print ("list of local aircraft.  It also gets a list of aircraft from  ")
print ("flightradar24 which has more details.                          ")
print ("There are some local flights which may not appear in           ")
print ("the online data (i.e. flightradar24 doesn't track military)    ")
print ("---------------------------------------------------------------")
print ("")
print ("")

LED.ClearBigLED()
LED.ClearBuffers()
CursorH = 0
CursorV = 0

LED.ScreenArray, CursorH, CursorV = LED.TerminalScroll(
    LED.ScreenArray, "LOADING CONFIG FILES", CursorH=CursorH, CursorV=CursorV,
    MessageRGB=(0, 150, 0), CursorRGB=(0, 255, 0), CursorDarkRGB=(0, 50, 0),
    StartingLineFeed=1, TypeSpeed=TerminalTypeSpeed, ScrollSpeed=TerminalScrollSpeed
)
LoadConfigFile()

LED.ScreenArray, CursorH, CursorV = LED.TerminalScroll(
    LED.ScreenArray, "GETTING LIST OF FLIGHTS FROM DUMP1090", CursorH=CursorH, CursorV=CursorV,
    MessageRGB=(0, 150, 0), CursorRGB=(0, 255, 0), CursorDarkRGB=(0, 50, 0),
    StartingLineFeed=1, TypeSpeed=TerminalTypeSpeed, ScrollSpeed=TerminalScrollSpeed
)

LED.ClearBigLED()
LED.ClearBuffers()



# Initialize DetailedFlightList
DetailedFlightList = []

while True:
    h, m, s = LED.GetElapsedTime(LastGetFlightsTime, time.time())
    if m >= GetFlightsWaitMinutes:
        FlightList = GetFlightsInBounds(Bounds)
        LastGetFlightsTime = time.time()
        DetailedFlightList = GetFlightDetails(FlightList)
    
    NearestFlightHex = GetNearbyFlights(DetailedFlightList)
    
    time.sleep(5)  

  

