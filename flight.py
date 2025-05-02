
'''
Requirements: geopy
> sudo pip3 install geopy
> sudo pip3 install FlightRadar24API
'''


import os
os.system('cls||clear')

import requests
import json
import time
import pprint as pp
import geopy.distance
import LEDarcade as LED
from configparser import SafeConfigParser

from FlightRadar24.api import FlightRadar24API 


fr_api = FlightRadar24API()




#---------------------------------------
#Variable declaration section
#---------------------------------------
ScrollSleep         = 0.015
TerminalTypeSpeed   = 0  #pause in seconds between characters
TerminalScrollSpeed = 0  #pause in seconds between new lines
CursorRGB           = (0,0,0)
CursorDarkRGB       = (0,0,0)
LastGetFlightsTime    = time.time()
GetFlightsWaitMinutes = 5

OriginAirport         = ''
DestinationAirport    = ''
AircraftType          = ''
AirlineName           = ''
AirlineShortName      = ''
AirportList           = []


#Files
ConfigFileName = "FlightConfig.ini" 



URL             = ''
BaseLat         = ''
BaseLon         = ''
BoundUpperLeft  = ''
BoundLowerRight = ''
Bounds          = ''



#----------------------------------------
#-- FILE ACCESS Functions              --
#----------------------------------------

def LoadConfigFile():

  global URL
  global BaseLat
  global BaseLon
  global BoundUpperLeft
  global BoundLowerRight
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
    BoundUpperLeft  = KeyFile.get("FLIGHT","BoundUpperLeft")
    BoundLowerRight = KeyFile.get("FLIGHT","BoundLowerRight")
    Bounds          = KeyFile.get("FLIGHT","Bounds")

    print (" ")

    print ("---------------------------------------------")
    print("URL:            ",URL)   
    print("BaseLat:        ",BaseLat)   
    print("BaseLon:        ",BaseLon)   
    print("BoundUpperLeft: ",BoundUpperLeft)
    print("BoundLowerRight:",BoundLowerRight)
    print ("---------------------------------------------")
    print (" ")

  else:
    #To be finished later
    print ("ERROR: Could not locate Key file (",ConfigFileName,"). Create a file and make sure to pupulate it with your own keys.")







#Get a list of flights in a lat/lon box
def GetFlightsInBounds(Bounds):
  print("")
  print("--GetFlightsInBounds--")
  print("Bounds:",Bounds)
  FlightList = fr_api.get_flights(airline= None, bounds=Bounds)
  print("Flights:"+str(len(FlightList)))
  time.sleep(2)
  #pp.pprint(FlightList)
  
  return FlightList
  




def GetNearbyFlights():
  
  global OriginAirport
  global DestinationAirport

  print("")
  print("--GetNearbyFlights--")
  r = requests.get(URL, headers={'Content-Type': 'application/json'})

  response = requests.get(url)
  print(f"Status Code: {response.status_code}")
  print(f"Response Content: {response.text}")

  #pp.pprint(r)
  message = r.json()
  #pp.pprint(message)
  
  i = 0
  ShortestDistance = 10000000
  ClosestFlight = -1

  AircraftDict = message.get('aircraft','NONE')
  if(AircraftDict != "NONE"):
    for flight in AircraftDict:
      try:
        #print("")
        #print("Analyzing flight data: ",i)
        #print(flight['flight'])
        #print(flight['alt_baro'])
        #print(flight['lat'])
        #print(flight['lon'])

        lat = flight['lat']
        lon = flight['lon']

        distance = geopy.distance.geodesic((lat,lon), (BaseLat, BaseLon)).m / 1000
        #print("Distance:",distance)
        if (distance <= ShortestDistance):
          ShortestDistance = distance
          ClosestFlight = i

    
      except:
        print("Record:",i,"no flight info found")

      i = i + 1
    

  if(ClosestFlight >= 0) :
    Flight   = AircraftDict[ClosestFlight].get('flight','none')
    Category = AircraftDict[ClosestFlight].get('category','none')
    Distance = ShortestDistance
    #Mach     = AircraftDict[ClosestFlight]['mach']  
    Speed    = AircraftDict[ClosestFlight].get('gs',0) * 1.8520
    Messages = AircraftDict[ClosestFlight].get('messages',0) 
    Squawk   = AircraftDict[ClosestFlight].get('squawk','none')
    AircraftCount = i
    Hex      = AircraftDict[ClosestFlight].get('hex','none').upper()

    #print("****************************************")
    #pp.pprint(AircraftDict[ClosestFlight])
    #print("****************************************")

    print("")
    print("")
    print("")
    print("** Closest Aircraft **")
    print('Record:   ',ClosestFlight)
    print('Hex:      ',Hex)
    print('Flight:   ',Flight)
    print('Category: ',Category)
    print('Distance: ',Distance)
    #print('Mach:     ',Mach)
    print('Speed:    ',Speed,'km/h')
    print('Messages: ',Messages)
    print('Sqauwk:   ',Squawk)
    print('Aircraft: ',AircraftCount)

    TitleRGB = (0,150,0)
    ValueRGB = (150,75,0)


    TitleFlight        = LED.CreateBannerSprite("Flight")
    TitleDistance      = LED.CreateBannerSprite("Dist")
    TitleSpeed         = LED.CreateBannerSprite("kph")
    TitleSquawk        = LED.CreateBannerSprite("Sqwk")
    TitleAircraftCount = LED.CreateBannerSprite("UP")
    TitleAircraftType  = LED.CreateBannerSprite("Type")
    TitleCategory      = LED.CreateBannerSprite("CAT")
    
    ValueFlight        = LED.CreateBannerSprite(Flight)
    ValueDistance      = LED.CreateBannerSprite(str(Distance)[0:5])
    ValueSpeed         = LED.CreateBannerSprite(str(Speed)[0:6])
    ValueSquawk        = LED.CreateBannerSprite(Squawk)
    ValueAircraftCount = LED.CreateBannerSprite(str(AircraftCount))
    ValueAircraftType  = LED.CreateBannerSprite(AircraftType)
    ValueAirlineShort  = LED.CreateBannerSprite(AirlineShortName)
    ValueCategory      = LED.CreateBannerSprite(Category)
    
    OriginDestination  = LED.CreateBannerSprite("  " + OriginAirport + " " + DestinationAirport)

    LED.Canvas.Clear()    
    LED.Canvas = LED.CopySpriteToCanvasZoom(TitleFlight,0,0,TitleRGB,(0,5,0),1,False,LED.Canvas)
    LED.Canvas = LED.CopySpriteToCanvasZoom(ValueFlight,28,0,ValueRGB,(0,5,0),1,False,LED.Canvas)

    LED.Canvas = LED.CopySpriteToCanvasZoom(TitleDistance,0,6,TitleRGB,(0,5,0),1,False,LED.Canvas)
    LED.Canvas = LED.CopySpriteToCanvasZoom(ValueDistance,28,6,ValueRGB,(0,5,0),1,False,LED.Canvas)
   
    H = LED.HatWidth - (ValueAircraftCount.width + TitleAircraftCount.width + 1)
    V = 0
    LED.Canvas = LED.CopySpriteToCanvasZoom(TitleAircraftCount,H,V,TitleRGB,(0,5,0),1,False,LED.Canvas)
    H = LED.HatWidth - ValueAircraftCount.width
    V = 0
    LED.Canvas = LED.CopySpriteToCanvasZoom(ValueAircraftCount,H,V,ValueRGB,(0,5,0),1,False,LED.Canvas)


    LED.Canvas = LED.CopySpriteToCanvasZoom(TitleCategory,63,0,TitleRGB,(0,5,0),1,False,LED.Canvas)
    LED.Canvas = LED.CopySpriteToCanvasZoom(ValueCategory,81,0,ValueRGB,(0,5,0),1,False,LED.Canvas)

    LED.Canvas = LED.CopySpriteToCanvasZoom(TitleSpeed,63,6,TitleRGB,(0,5,0),1,False,LED.Canvas)
    LED.Canvas = LED.CopySpriteToCanvasZoom(ValueSpeed,81,6,ValueRGB,(0,5,0),1,False,LED.Canvas)

    
    
    #LED.Canvas = LED.CopySpriteToCanvasZoom(TitleSquawk,56,0,TitleRGB,(0,5,0),1,False,LED.Canvas)
    #LED.Canvas = LED.CopySpriteToCanvasZoom(ValueSquawk,80,0,ValueRGB,(0,5,0),1,False,LED.Canvas)

    #LED.Canvas = LED.CopySpriteToCanvasZoom(TitleAircraftType,0,24,TitleRGB,(0,5,0),1,False,LED.Canvas)
    LED.Canvas = LED.CopySpriteToCanvasZoom(ValueAircraftType,0,12,(75,0,200),(0,5,0),1,False,LED.Canvas)
    LED.Canvas = LED.CopySpriteToCanvasZoom(ValueAirlineShort,0,18,(75,0,200),(0,5,0),1,False,LED.Canvas)

    



    #ScrollText = ScrollText + " - " + AircraftType
    #ScrollText = ScrollText + " - " + AirlineName
    #ScrollText = ScrollText + " - " + AirlineShortName



    #LED.Canvas = LED.CopySpriteToCanvasZoom(OriginDestination,0,24,(100,150,0),(0,5,0),1,False,LED.Canvas)


    LED.Canvas = LED.TheMatrix.SwapOnVSync(LED.Canvas)


  else:
    print("**No flight data found**")
    return None


  return Hex

  


def GetFlightDetails(FlightList):
  print("")
  print("--GetFlightDetails-")
  print("FlightList length: ",len(FlightList))
  
  DetailedFlightList = []
  
  for flight in FlightList:
    print(flight)
    details = fr_api.get_flight_details(flight.id)
    
    try:
      flight.set_flight_details(details)
    except:
      print("not a valid flight object")
   
    try:
      DetailedFlightList.append(flight)
      print("Appending flight")
    except:
      print("Processing",end='\r')


  return DetailedFlightList





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
    
      if((flight.icao_24bit).upper() == NearestFlightHex.upper()):
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

LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"LOADING CONFIG FILES",CursorH=CursorH,CursorV=CursorV,MessageRGB=(0,150,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalScrollSpeed)
LoadConfigFile()
LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"RETREIVING LIST OF AIRPORTS",CursorH=CursorH,CursorV=CursorV,MessageRGB=(0,150,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalScrollSpeed)
GetAirportList()

#pp.pprint(AirportList)

LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"GETTING LIST OF FLIGHTS WITHIN SPECIFIED BOUNDARY",CursorH=CursorH,CursorV=CursorV,MessageRGB=(0,150,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalScrollSpeed)
FlightList = GetFlightsInBounds(Bounds)
LastGetFlightsTime = time.time()
LED.ScreenArray,CursorH,CursorV = LED.TerminalScroll(LED.ScreenArray,"RETRIEVING FLIGHT DETAILS",CursorH=CursorH,CursorV=CursorV,MessageRGB=(0,150,0),CursorRGB=(0,255,0),CursorDarkRGB=(0,50,0),StartingLineFeed=1,TypeSpeed=TerminalTypeSpeed,ScrollSpeed=TerminalScrollSpeed)
DetailedFlightList = GetFlightDetails(FlightList)



# an example "flight"
# [<(B350) C-GSYC - Altitude: 4375 - Ground Speed: 206 - Heading: 129>
#details = fr_api.get_flight_details('B350')
#pp.pprint(details)
#time.sleep(2)

LED.ClearBigLED()
LED.ClearBuffers()

while(1==1):
  h,m,s = LED.GetElapsedTime(LastGetFlightsTime,time.time())
  
  #update master list of flights every X minutes
  print("HMS",h,m,s)
  print("LastGetFlightsTime",LastGetFlightsTime)
  if (m >= GetFlightsWaitMinutes):
    FlightList = GetFlightsInBounds(Bounds)
    LastGetFlightsTime = time.time()
    DetailedFlightList = GetFlightDetails(FlightList)
 

  NearestFlightHex = GetNearbyFlights()
  LookupFlightDetails(NearestFlightHex,DetailedFlightList)

  print((OriginAirport + " " + DestinationAirport))  
  
  
  
  OriginText      = GetAirport(OriginAirport)
  DestinationText = GetAirport(DestinationAirport)
  
  #--------------------------------------------------
  #Create scrolling text with additional information
  #--------------------------------------------------
  

  try:
    ScrollText = OriginAirport + "-" + DestinationAirport + " " + OriginText.split()[0] + " " + OriginText.split()[1] + " --> " + DestinationText.split()[0] + " " + DestinationText.split()[1]
    #ScrollText = ScrollText + " - " + AircraftType
    #ScrollText = ScrollText + " - " + AirlineName
    #ScrollText = ScrollText + " - " + AirlineShortName
    print(ScrollText)

    LED.ShowScrollingBanner2(ScrollText,(100,150,0),ScrollSpeed=ScrollSleep,v=26)
  except:
    print("ScrollText not found")
    
    
    



    time.sleep(5)
  

  




'''
[{'alt': 326,
  'country': 'Spain',
  'iata': 'LCG',
  'icao': 'LECO',
  'lat': 43.302059,
  'lon': -8.37725,
1  'name': 'A Coruna Airport'},
'''