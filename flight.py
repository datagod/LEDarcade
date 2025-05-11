
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
from urllib.parse import urlparse
import csv


import requests
from bs4 import BeautifulSoup



#from opensky_api import OpenSkyApi
#api = OpenSkyApi()
#s = api.get_states()
#print(s)



#---------------------------------------
#Variable declaration section
#---------------------------------------

ConfigFileName        = "FlightConfig.ini"
ScrollSleep           = 0.02
TerminalTypeSpeed     = 0
TerminalScrollSpeed   = 0
CursorRGB             = (0, 0, 0)
CursorDarkRGB         = (0, 0, 0)
LastGetFlightsTime    = time.time()
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
AirportDict           = {}



#Files
ConfigFileName = "FlightConfig.ini" 



DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/113.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.google.com/",
    "Connection": "keep-alive",
}






#-------------------------------------------------------------------------------
#-- FUNCTIONS                                                                 --
#-------------------------------------------------------------------------------

def GenerateRouteString(Hex, CallSign):

    RouteString      = ''
    DepartureAirport = '?'
    ArrivalAirport   = '?'
    DepartureCountry = '?'

    try:

        print("--Route------------------------")
        Route, Departure, Arrival = get_flight_origin_destination(Hex, CallSign)
        print("Route: ",Route)

        DepartureDetails = GetAirport(Departure)
        DepartureAirport = DepartureDetails['city']
        DepartureCountry = DepartureDetails['country']
        
        print(f"DepartureDetails:{DepartureDetails}")
        print(f"DepartureAirport: {DepartureAirport}")
    except Exception as e:
        print  (f"Error retrieving Departure information: {e}")

    try:    
        ArrivalDetails = GetAirport(Arrival)
        ArrivalAirport = ArrivalDetails['city']
        print(f"ArrivalDetails:{ArrivalDetails}")
        print(f"ArrivalAirport: {ArrivalAirport}")
        
        RouteString = f"{DepartureAirport} --> {ArrivalAirport} "
        if (DepartureCountry != 'Canada' and DepartureCountry != '?'):
          RouteString = RouteString + f' {DepartureCountry}'
        print(f"RouteString: {RouteString}")
        print(f"[Route Lookup] Hex: {Hex}, CallSign: {CallSign} → {RouteString}")
        print("--Route------------------------")
        
  
    except Exception as e:
        print  (f"Error retrieving Arrival information: {e}")


    return RouteString

    


def LoadAirportDict():
    """
    Load airport data from airports.dat and return a dictionary keyed by IATA and ICAO codes.
    
    Returns:
        dict: {
            'CYYZ': {...},  # ICAO
            'YYZ': {...}    # IATA
        }
    """
    filepath="./localdata/airports.dat"
    airport_dict = {}

    with open(filepath, encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 8:
                continue

            airport_data = {
                "id": row[0],
                "name": row[1],
                "city": row[2],
                "country": row[3],
                "iata": row[4],
                "icao": row[5],
                "lat": float(row[6]) if row[6] else None,
                "lon": float(row[7]) if row[7] else None,
            }

            # Index by IATA
            if row[4] and row[4] != r"\N":
                airport_dict[row[4].strip()] = airport_data

            # Also index by ICAO
            if row[5] and row[5] != r"\N":
                airport_dict[row[5].strip()] = airport_data

    return airport_dict


def GetAirport(code):
    """
    Query airport data by IATA or ICAO code.

    Args:
        code (str): IATA or ICAO code
        airport_dict (dict): the loaded airport dictionary

    Returns:
        dict or None: Airport info dict or None if not found
    """
    return AirportDict.get(code.upper())









def extract_airports_from_url(url):
    """
    Extracts departure and arrival airport codes from a FlightAware flight history URL.
    
    Args:
        url (str): FlightAware URL in the format
                   https://www.flightaware.com/live/flight/XXX/history/YYYYMMDD/ZZZZZ/DEP/ARR

    Returns:
        tuple: (departure_airport_code, arrival_airport_code)
    """
    print("Extracting airports from url")
    print(f"URL: {url}")
    parsed_url = urlparse(url)
    path_parts = parsed_url.path.strip('/').split('/')
    print(f"Path Parts: {path_parts}")
    if len(path_parts) < 2:
        raise ValueError("Invalid URL format: Not enough path segments.")

    departure_airport = path_parts[-2]
    arrival_airport = path_parts[-1]

    return departure_airport, arrival_airport



def get_flight_origin_destination(hex_code, CallSign):
    try:
        dep = ''
        arr = ''

        # Step 1: Construct URL
        url = f"https://flightaware.com/live/modes/{hex_code.lower()}/ident/{CallSign}/redirect"


        
        headers = {"User-Agent": "Mozilla/5.0"}
        print(f"[DEBUG] Requesting URL: {url}")

        # Step 2: Follow redirect

        session = requests.Session()
        session.headers.update(DEFAULT_HEADERS)
        response = session.get(url, timeout=10, allow_redirects=True)
        print(f"[DEBUG] Final URL after redirects: {response.url}")
        print(f"[DEBUG] Status Code: {response.status_code}")

        if response.status_code != 200:
            print(f"[DEBUG] Non-OK status: {response.status_code}")
            return f"HTTP {response.status_code}", dep, arr

        # Step 3: Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        route_summary = soup.find("div", class_="flightPageSummaryRoute")



        #print("[DEBUG] Dumping first 1000 chars of HTML:")
        #print(response.text[:10000])

        

        dep, arr = extract_airports_from_url(response.url)
        print(f"Departure: {dep}, Arrival: {arr}")


        if route_summary:
            print(f"[DEBUG] Found route element: {route_summary}")
            text = route_summary.get_text(" ", strip=True)
            print(f"[DEBUG] Extracted text: {text}")
            return text, dep, arr
        else:
            print("[DEBUG] Route summary div not found.")
            return "Route info not found", dep, arr









    except Exception as e:
        print(f"[DEBUG] Exception: {e}")
        return f"Error: {e}"




def get_enroute_info(flightaware_url):



    try:

        session = requests.Session()
        session.headers.update(DEFAULT_HEADERS)
        response = session.get(flightaware_url, timeout=10)

        soup = BeautifulSoup(response.text, 'html.parser')

        # Search for structured enroute info in the summary section
        summary_table = soup.find("table", class_="flightPageSummaryAirports")
        if not summary_table:
            return "Enroute info not found (summary table missing)"

        cells = summary_table.find_all("td")
        if len(cells) >= 2:
            origin = cells[0].get_text(" ", strip=True)
            destination = cells[1].get_text(" ", strip=True)
            return f"{origin} → {destination}"
        else:
            return "Enroute info not found (table format issue)"

    except Exception as e:
        return f"Error retrieving enroute information: {e}"




def decode_aircraft_category(raw_category):
    numeric_map = {
        0: "No Info",
        1: "Light (< 15.5k lbs)",
        2: "Small (15.5k–75k lbs)",
        3: "Large (75k–300k lbs)",
        4: "High Vortex",
        5: "Heavy (> 300k lbs)",
        6: "High Performance",
        7: "Rotorcraft",
        8: "Glider",
        9: "Lighter-than-air",
        10: "Parachutist",
        11: "Ultralight",
        12: "Reserved",
        13: "UAV",
        14: "Spacecraft"
    }
    
    letter_map = {
        "A0": "No Info",
        "A1": "Light",
        "A2": "Small",
        "A3": "Large",
        "A4": "High Vortex",
        "A5": "Heavy",
        "A6": "High Perf",
        "A7": "Rotorcraft"
    }

    if isinstance(raw_category, int):
        return numeric_map.get(raw_category, "Unknown")
    elif isinstance(raw_category, str):
        return letter_map.get(raw_category.upper(), f"Unknown ({raw_category})")
    return "Unknown"





#----------------------------------------
#-- FILE ACCESS Functions              --
#----------------------------------------


ConfigFileName = "FlightConfig.ini"
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










def GetFlightsInBounds(Bounds):
    print("\n--GetFlightsInBounds--")
    print(f"Bounds: {Bounds}")
    
    try:
        print(f"Fetching data from: {Dump1090URL}")
        response = requests.get(Dump1090URL, timeout=5)
        #print(f"HTTP Status Code: {response.status_code}")
        #print(f"Raw Response: {response.text}")
        response.raise_for_status()
        aircraft_list = response.json()
        #print(f"Aircraft List: {aircraft_list}")
        
        # Log detailed aircraft data
        #print("\n--Aircraft Details--")
        aircraft_data = aircraft_list.get('aircraft', [])
        print(f"Total Aircraft: {len(aircraft_data)}")
        #for i, ac in enumerate(aircraft_data):
            #print(f"Aircraft {i}:")
            #print(f"  Hex: {ac.get('hex', 'N/A')}")
            #print(f"  Lat: {ac.get('lat', 'N/A')}")
            #print(f"  Lon: {ac.get('lon', 'N/A')}")
            #print(f"  Altitude: {ac.get('altitude', 'N/A')}")
            #print(f"  Speed: {ac.get('speed', 'N/A')}")
            #print(f"  Squawk: {ac.get('squawk', 'N/A')}")
            #print(f"  Flight: {ac.get('flight', 'N/A')}")
            #print(f"  Track: {ac.get('track', 'N/A')}")
            #print(f"  Category: {ac.get('category', 'N/A')}")
            
            #print(f"  All Keys: {list(ac.keys())}")
        
        lat1, lat2, lon1, lon2 = map(float, Bounds.split(','))
        lat_min, lat_max = min(lat1, lat2), max(lat1, lat2)
        lon_min, lon_max = min(lon1, lon2), max(lon1, lon2)
        print(f"\nBounds Filter: Lat [{lat_min}, {lat_max}], Lon [{lon_min}, {lon_max}]")
        
        filtered_aircraft = [
            {
                'hex': ac.get('hex', ''),
                'latitude': ac.get('lat', 0),
                'longitude': ac.get('lon', 0),
                'altitude': ac.get('alt_baro', ac.get('alt_geom', 0)),
                'ground_speed': ac.get('gs', 0),
                'squawk': ac.get('squawk', '0000'),
                'CallSign': ac.get('flight', 'UNKNOWN').strip(),
                'track': ac.get('track', 0),
                'id': ac.get('hex', ''),
                'category': decode_aircraft_category(ac.get('category')),

            }
            for ac in aircraft_data
            if 'lat' in ac and 'lon' in ac
            and isinstance(ac['lat'], (int, float)) and isinstance(ac['lon'], (int, float))
            and lat_min <= ac['lat'] <= lat_max
            and lon_min <= ac['lon'] <= lon_max
        ]        
        # Log aircraft excluded by bounds
        excluded_aircraft = [
            ac for ac in aircraft_data
            if 'lat' in ac and 'lon' in ac
            and isinstance(ac['lat'], (int, float)) and isinstance(ac['lon'], (int, float))
            and not (lat_min <= ac['lat'] <= lat_max and lon_min <= ac['lon'] <= lon_max)
        ]
        if excluded_aircraft:
            print("\n--Excluded Aircraft (Outside Bounds)--")
            for i, ac in enumerate(excluded_aircraft):
                print(f"Excluded Aircraft {i}:")
                print(f"  Hex: {ac.get('hex', 'N/A')}")
                print(f"  Lat: {ac.get('lat', 'N/A')}")
                print(f"  Lon: {ac.get('lon', 'N/A')}")
        
        
        
        
        # Collect and print all raw category codes
        raw_categories = set()
        for ac in aircraft_data:
            if 'category' in ac:
                raw_categories.add(ac['category'])

        print("\n--Unique Raw Category Codes Detected--")
        for cat in sorted(raw_categories):
            print(f"  Category: {cat}")

        
        
        
        
        #print(f"\nFiltered Aircraft: {filtered_aircraft}")
        print(f"Flights: {len(filtered_aircraft)}")
        if not filtered_aircraft and aircraft_data:
            print("Warning: No aircraft within bounds. Check Bounds or aircraft coordinates.")
        elif not aircraft_data:
            print("Warning: No aircraft data in JSON response. Check Dump1090 feed.")
        



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
        return None, None

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
        Flight   = flight['CallSign'] or "UNKNOWN"
        CallSign = flight['CallSign'] or "UNKNOWN"
        Category  = flight.get('category', 'Unknown')
        Distance  = ShortestDistance
        Speed     = flight['ground_speed'] * 1.852 if flight['ground_speed'] else 0
        Squawk    = flight['squawk'] or "0000"
        Hex       = flight['hex'] or "UNKNOWN"
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

        LED.Canvas = LED.CopySpriteToCanvasZoom(TitleCategory, 0, 12, TitleRGB, (0, 5, 0), 1, False, LED.Canvas)
        LED.Canvas = LED.CopySpriteToCanvasZoom(ValueCategory, 28,12, ValueRGB, (0, 5, 0), 1, False, LED.Canvas)

        LED.Canvas = LED.CopySpriteToCanvasZoom(TitleSpeed, 0, 18, TitleRGB, (0, 5, 0), 1, False, LED.Canvas)
        LED.Canvas = LED.CopySpriteToCanvasZoom(ValueSpeed, 28,18, ValueRGB, (0, 5, 0), 1, False, LED.Canvas)

        LED.Canvas = LED.TheMatrix.SwapOnVSync(LED.Canvas)

        



        # You can also call get_enroute_info if you prefer full URL scraping:
        # full_url = f"https://www.flightaware.com/live/flight/{CallSign}"
        # route = get_enroute_info(full_url)




    else:
        print("**No flight data found**")
        LED.Canvas.Clear()
        no_data_sprite = LED.CreateBannerSprite("NO DATA")
        LED.Canvas = LED.CopySpriteToCanvasZoom(no_data_sprite, 0, 0, (255, 0, 0), (0, 0, 0), 1, False, LED.Canvas)
        LED.Canvas = LED.TheMatrix.SwapOnVSync(LED.Canvas)
        return None,None

    return Hex, CallSign
  


def GetFlightDetails(FlightList):
    print("\n--GetFlightDetails--")
    print(f"FlightList length: {len(FlightList)}")
    return FlightList




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

print ("Loading airports")
AirportDict = LoadAirportDict()

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
  FlightList    = GetFlightsInBounds(Bounds)
  Hex, CallSign = GetNearbyFlights(FlightList)
  RouteString   = GenerateRouteString(Hex,CallSign)
    
  #--------------------------------------------------
  #Create scrolling text with additional information
  #--------------------------------------------------
  LED.ShowScrollingBanner2(RouteString,(100,150,0),ScrollSpeed=ScrollSleep,v=26)
  time.sleep(1) 

    
  

