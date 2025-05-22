print("")
print("==========================================")
print("== LEDcolors.py                         ==")
print("==========================================")
print("")


def ApplyGamma(value, gamma):
    corrected = int(value * gamma)
    return min(corrected, 255)


def InitializeColors():

    print("")
    print("-------------------------------")
    print("-- LEDcolors: initialization --")
    print("-------------------------------")
    print("")
    

    global Gamma
    global ColorList, BrightColorList, TextColorList

    global RedR, RedG, RedB, HighRed, MedRed, LowRed, DarkRed, ShadowRed
    global GreenR, GreenG, GreenB, HighGreen, MedGreen, LowGreen, DarkGreen, ShadowGreen
    global BlueR, BlueG, BlueB, HighBlue, MedBlue, LowBlue, DarkBlue, ShadowBlue
    global OrangeR, OrangeG, OrangeB, HighOrange, MedOrange, LowOrange, DarkOrange, ShadowOrange
    global YellowR, YellowG, YellowB, HighYellow, MedYellow, LowYellow, DarkYellow, ShadowYellow
    global PurpleR, PurpleG, PurpleB, HighPurple, MedPurple, LowPurple, DarkPurple, ShadowPurple
    global PinkR, PinkG, PinkB, MaxPink, HighPink, MedPink, LowPink, DarkPink, ShadowPink
    global CyanR, CyanG, CyanB, MaxCyan, HighCyan, MedCyan, LowCyan, DarkCyan, ShadowCyan


    global MaxWhite, MaxRed, MaxGreen, MaxBlue

    def rgb(r, g, b):
        return (ApplyGamma(r, Gamma), ApplyGamma(g, Gamma), ApplyGamma(b, Gamma))



    #HighRed
    SDHighRedR = 255
    SDHighRedG = 0
    SDHighRedB = 0


    #MedRed
    SDMedRedR = 175
    SDMedRedG = 0
    SDMedRedB = 0


    #LowRed
    SDLowRedR = 100
    SDLowRedG = 0
    SDLowRedB = 0

    #DarkRed
    SDDarkRedR = 45
    SDDarkRedG = 0
    SDDarkRedB = 0

    # Red RGB Tuples
    HighRed = (SDHighRedR,SDHighRedG,SDHighRedB)
    MedRed  = (SDMedRedR ,SDMedRedG ,SDMedRedB)
    LowRed  = (SDLowRedR ,SDLowRedG ,SDLowRedB)
    DarkRed = (SDDarkRedR,SDDarkRedG,SDDarkRedB)
    ShadowRed = (25,0,0)


    #HighOrange
    SDHighOrangeR = 255
    SDHighOrangeG = 128
    SDHighOrangeB = 0

    #MedOrange
    SDMedOrangeR = 200
    SDMedOrangeG = 100
    SDMedOrangeB = 0

    #LowOrange
    SDLowOrangeR = 155
    SDLowOrangeG = 75
    SDLowOrangeB = 0

    #DarkOrange
    SDDarkOrangeR = 100
    SDDarkOrangeG = 45
    SDDarkOrangeB = 0

    HighOrange = (SDHighOrangeR,SDHighOrangeG,SDHighOrangeB)
    MedOrange  = (SDMedOrangeR, SDMedOrangeG, SDMedOrangeB)
    LowOrange  = (SDLowOrangeR, SDLowOrangeG, SDLowOrangeB)
    DarkOrange = (SDDarkOrangeR,SDDarkOrangeG,SDDarkOrangeB)
    ShadowOrange = (50,20,0)

    # High = (R,G,B)
    # Med  = (R,G,B)
    # Low  = (R,G,B)
    # Dark = (R,G,B)


    #SDHighPurple
    SDHighPurpleR = 230
    SDHighPurpleG = 0
    SDHighPurpleB = 255

    #MedPurple
    SDMedPurpleR = 105
    SDMedPurpleG = 0
    SDMedPurpleB = 155

    #SDLowPurple
    SDLowPurpleR = 75
    SDLowPurpleG = 0
    SDLowPurpleB = 120


    #SDDarkPurple
    SDDarkPurpleR = 45
    SDDarkPurpleG = 0
    SDDarkPurpleB = 45

    # Purple RGB Tuples
    HighPurple = (SDHighPurpleR,SDHighPurpleG,SDHighPurpleB)
    MedPurple  = (SDMedPurpleR ,SDMedPurpleG ,SDMedPurpleB)
    LowPurple  = (SDLowPurpleR ,SDLowPurpleG ,SDLowPurpleB)
    DarkPurple = (SDDarkPurpleR,SDDarkPurpleG,SDDarkPurpleB)
    ShadowPurple = (25,0,25)





    #HighGreen
    SDHighGreenR = 0
    SDHighGreenG = 255
    SDHighGreenB = 0

    #MedGreen
    SDMedGreenR = 0
    SDMedGreenG = 200
    SDMedGreenB = 0

    #LowGreen
    SDLowGreenR = 0
    SDLowGreenG = 100
    SDLowGreenB = 0

    #DarkGreen
    SDDarkGreenR = 0
    SDDarkGreenG = 45
    SDDarkGreenB = 0

    #Green tuples
    HighGreen = (SDHighGreenR,SDHighGreenG,SDHighGreenB)
    MedGreen  = (SDMedGreenR,SDMedGreenG,SDMedGreenB)
    LowGreen  = (SDLowGreenR,SDLowGreenG,SDLowGreenB)
    DarkGreen = (SDDarkGreenR,SDDarkGreenG,SDDarkGreenB)
    ShadowGreen = (0,35,0)




    #HighBlue
    SDHighBlueR = 0
    SDHighBlueG = 0
    SDHighBlueB = 255


    #MedBlue
    SDMedBlueR = 0
    SDMedBlueG = 0
    SDMedBlueB = 175

    #LowBlue
    SDLowBlueR = 0
    SDLowBlueG = 0
    SDLowBlueB = 100
    
    

    #DarkBlue
    SDDarkBlueR = 0
    SDDarkBlueG = 0
    SDDarkBlueB = 45


    # Blue RGB Tuples
    HighBlue = (SDHighBlueR,SDHighBlueG,SDHighBlueB)
    MedBlue  = (SDHighBlueR,SDHighBlueG,SDHighBlueB)
    LowBlue  = (SDHighBlueR,SDHighBlueG,SDHighBlueB)
    DarkBlue = (SDHighBlueR,SDHighBlueG,SDHighBlueB)
    ShadowBlue = (0,0,25)


    #WhiteMax
    SDMaxWhiteR = 255
    SDMaxWhiteG = 255
    SDMaxWhiteB = 255

    #WhiteHigh
    SDHighWhiteR = 255
    SDHighWhiteG = 255
    SDHighWhiteB = 255

    #WhiteMed
    SDMedWhiteR = 150
    SDMedWhiteG = 150
    SDMedWhiteB = 150

    #WhiteLow
    SDLowWhiteR = 100
    SDLowWhiteG = 100
    SDLowWhiteB = 100

    #WhiteDark
    SDDarkWhiteR = 35
    SDDarkWhiteG = 35
    SDDarkWhiteB = 35


    # White RGB Tuples
    MaxWhite  = (SDMaxWhiteR,SDMaxWhiteG,SDMaxWhiteB)
    HighWhite = (SDHighWhiteR,SDHighWhiteG,SDHighWhiteB)
    MedWhite  = (SDHighWhiteR,SDHighWhiteG,SDHighWhiteB)
    LowWhite  = (SDHighWhiteR,SDHighWhiteG,SDHighWhiteB)
    DarkWhite = (SDHighWhiteR,SDHighWhiteG,SDHighWhiteB)
    ShadowWhite = (15,15,15)


    #YellowMax
    SDMaxYellowR = 255
    SDMaxYellowG = 255
    SDMaxYellowB = 0


    #YellowHigh
    SDHighYellowR = 215
    SDHighYellowG = 215
    SDHighYellowB = 0

    #YellowMed
    SDMedYellowR = 175
    SDMedYellowG = 175
    SDMedYellowB = 0

    #YellowLow
    SDLowYellowR = 100
    SDLowYellowG = 100
    SDLowYellowB = 0


    #YellowDark
    SDDarkYellowR = 55
    SDDarkYellowG = 55
    SDDarkYellowB = 0


    # Yellow RGB Tuples
    MaxYellow  = (SDMaxYellowR,SDMaxYellowG,SDMaxYellowB)
    HighYellow = (SDHighYellowR,SDHighYellowG,SDHighYellowB)
    MedYellow  = (SDMedYellowR,SDMedYellowG,SDMedYellowB)
    LowYellow  = (SDLowYellowR,SDLowYellowG,SDLowYellowB)
    DarkYellow = (SDDarkYellowR,SDDarkYellowG,SDDarkYellowB)
    ShadowYellow = (30,30,0)


    #Pink
    SDMaxPinkR = 155
    SDMaxPinkG = 0
    SDMaxPinkB = 130

    SDHighPinkR = 130
    SDHighPinkG = 0
    SDHighPinkB = 105

    SDMedPinkR = 100
    SDMedPinkG = 0
    SDMedPinkB = 75

    SDLowPinkR = 75
    SDLowPinkG = 0
    SDLowPinkB = 50

    SDDarkPinkR = 45
    SDDarkPinkG = 0
    SDDarkPinkB = 50


    # Pink RGB Tuples
    MaxPink  = (SDMaxPinkR,SDMaxPinkG,SDMaxPinkB)
    HighPink = (SDHighPinkR,SDHighPinkG,SDHighPinkB)
    MedPink  = (SDHighPinkR,SDHighPinkG,SDHighPinkB)
    LowPink  = (SDHighPinkR,SDHighPinkG,SDHighPinkB)
    DarkPink = (SDHighPinkR,SDHighPinkG,SDHighPinkB)
    ShadowPink = (22,0,25)


    #Cyan
    SDMaxCyanR = 0
    SDMaxCyanG = 255
    SDMaxCyanB = 255

    SDHighCyanR = 0
    SDHighCyanG = 150
    SDHighCyanB = 150

    SDMedCyanR = 0
    SDMedCyanG = 100
    SDMedCyanB = 100

    SDLowCyanR = 0
    SDLowCyanG = 75
    SDLowCyanB = 75

    SDDarkCyanR = 0
    SDDarkCyanG = 50
    SDDarkCyanB = 50

    # Cyan RGB Tuples
    MaxCyan  = (SDMaxCyanR,SDMaxCyanG,SDMaxCyanB)
    HighCyan = (SDHighCyanR,SDHighCyanG,SDHighCyanB)
    MedCyan  = (SDHighCyanR,SDHighCyanG,SDHighCyanB)
    LowCyan  = (SDHighCyanR,SDHighCyanG,SDHighCyanB)
    DarkCyan = (SDHighCyanR,SDHighCyanG,SDHighCyanB)
    ShadowCyan = (0,20,20)

    Gamma = Gamma if 'Gamma' in globals() else 1.0





    MaxRed = rgb(255, 0, 0)
    MaxGreen = rgb(0, 255, 0)
    MaxBlue = rgb(0, 0, 255)
    MaxWhite = rgb(255, 255, 255)

    HighRed = MaxRed
    MedRed = rgb(175, 0, 0)
    LowRed = rgb(100, 0, 0)
    DarkRed = rgb(45, 0, 0)
    ShadowRed = rgb(25, 0, 0)

    HighGreen = rgb(0, 255, 0)
    MedGreen = rgb(0, 200, 0)
    LowGreen = rgb(0, 100, 0)
    DarkGreen = rgb(0, 45, 0)
    ShadowGreen = rgb(0, 25, 0)

    HighBlue = rgb(0, 0, 255)
    MedBlue = rgb(0, 0, 175)
    LowBlue = rgb(0, 0, 100)
    DarkBlue = rgb(0, 0, 45)
    ShadowBlue = rgb(0, 0, 25)

    HighOrange = rgb(255, 128, 0)
    MedOrange = rgb(200, 100, 0)
    LowOrange = rgb(155, 75, 0)
    DarkOrange = rgb(100, 45, 0)
    ShadowOrange = rgb(50, 25, 0)

    MaxYellow  = (255,255,0)
    HighYellow = rgb(215, 215, 0)
    MedYellow = rgb(175, 175, 0)
    LowYellow = rgb(100, 100, 0)
    DarkYellow = rgb(55, 55, 0)
    ShadowYellow = rgb(25, 25, 0)

    MaxPurple    = rgb(255,0,255)
    HighPurple   = rgb(230, 0, 255)
    MedPurple    = rgb(105, 0, 155)
    LowPurple    = rgb(75, 0, 120)
    DarkPurple   = rgb(45, 0, 45)
    ShadowPurple = rgb(25,0,25)

    MaxPink = rgb(155, 0, 130)
    HighPink = rgb(130, 0, 105)
    MedPink = rgb(100, 0, 75)
    LowPink = rgb(75, 0, 50)
    DarkPink = rgb(45, 0, 50)
    ShadowPink = rgb(25, 0, 25)

    MaxCyan = rgb(0, 255, 255)
    HighCyan = rgb(0, 150, 150)
    MedCyan = rgb(0, 100, 100)
    LowCyan = rgb(0, 75, 75)
    DarkCyan = rgb(0, 50, 50)
    ShadowCyan = rgb(0, 25, 25)

    ColorList = []
    ColorList.append((0, 0, 0))  # 0 Black

    # 1–4 White shades
    ColorList.append((SDDarkWhiteR, SDDarkWhiteG, SDDarkWhiteB))
    ColorList.append((SDLowWhiteR, SDLowWhiteG, SDLowWhiteB))
    ColorList.append((SDMedWhiteR, SDMedWhiteG, SDMedWhiteB))
    ColorList.append((SDHighWhiteR, SDHighWhiteG, SDHighWhiteB))

    # 5–8 Reds
    ColorList.append((SDDarkRedR, SDDarkRedG, SDDarkRedB))
    ColorList.append((SDLowRedR, SDLowRedG, SDLowRedB))
    ColorList.append((SDMedRedR, SDMedRedG, SDMedRedB))
    ColorList.append((SDHighRedR, SDHighRedG, SDHighRedB))

    # 9–12 Greens
    ColorList.append((SDDarkGreenR, SDDarkGreenG, SDDarkGreenB))
    ColorList.append((SDLowGreenR, SDLowGreenG, SDLowGreenB))
    ColorList.append((SDMedGreenR, SDMedGreenG, SDMedGreenB))
    ColorList.append((SDHighGreenR, SDHighGreenG, SDHighGreenB))

    # 13–16 Blues
    ColorList.append((SDDarkBlueR, SDDarkBlueG, SDDarkBlueB))
    ColorList.append((SDLowBlueR, SDLowBlueG, SDLowBlueB))
    ColorList.append((SDMedBlueR, SDMedBlueG, SDMedBlueB))
    ColorList.append((SDHighBlueR, SDHighBlueG, SDHighBlueB))

    # 17–20 Oranges
    ColorList.append((SDDarkOrangeR, SDDarkOrangeG, SDDarkOrangeB))
    ColorList.append((SDLowOrangeR, SDLowOrangeG, SDLowOrangeB))
    ColorList.append((SDMedOrangeR, SDMedOrangeG, SDMedOrangeB))
    ColorList.append((SDHighOrangeR, SDHighOrangeG, SDHighOrangeB))

    # 21–24 Yellows
    ColorList.append((SDDarkYellowR, SDDarkYellowG, SDDarkYellowB))
    ColorList.append((SDLowYellowR, SDLowYellowG, SDLowYellowB))
    ColorList.append((SDMedYellowR, SDMedYellowG, SDMedYellowB))
    ColorList.append((SDHighYellowR, SDHighYellowG, SDHighYellowB))

    # 25–28 Purples
    ColorList.append((SDDarkPurpleR, SDDarkPurpleG, SDDarkPurpleB))
    ColorList.append((SDLowPurpleR, SDLowPurpleG, SDLowPurpleB))
    ColorList.append((SDMedPurpleR, SDMedPurpleG, SDMedPurpleB))
    ColorList.append((SDHighPurpleR, SDHighPurpleG, SDHighPurpleB))

    # 29–33 Pinks
    ColorList.append((SDDarkPinkR, SDDarkPinkG, SDDarkPinkB))
    ColorList.append((SDLowPinkR, SDLowPinkG, SDLowPinkB))
    ColorList.append((SDMedPinkR, SDMedPinkG, SDMedPinkB))
    ColorList.append((SDHighPinkR, SDHighPinkG, SDHighPinkB))
    ColorList.append((SDMaxPinkR, SDMaxPinkG, SDMaxPinkB))

    # 34–38 Cyans
    ColorList.append((SDDarkCyanR, SDDarkCyanG, SDDarkCyanB))
    ColorList.append((SDLowCyanR, SDLowCyanG, SDLowCyanB))
    ColorList.append((SDMedCyanR, SDMedCyanG, SDMedCyanB))
    ColorList.append((SDHighCyanR, SDHighCyanG, SDHighCyanB))
    ColorList.append((SDMaxCyanR, SDMaxCyanG, SDMaxCyanB))

    # 39–45 MAX colors
    ColorList.append((255,   0,   0))  # Red
    ColorList.append((0,   255,   0))  # Green
    ColorList.append((0,     0, 255))  # Blue
    ColorList.append((255, 255,   0))  # Yellow
    ColorList.append((255,   0, 255))  # Purple
    ColorList.append((0,   255, 255))  # Cyan
    ColorList.append((255, 255, 255))  # White

    # 46 Additional MAX Cyan
    ColorList.append((SDMaxCyanR, SDMaxCyanG, SDMaxCyanB))




    BrightColorList = (
        (0, 0, 0),                     # 0: Black / Transparent
        rgb(100, 100, 100),            # 1: Low White
        rgb(150, 150, 150),            # 2: Medium White
        rgb(225, 225, 225),            # 3: High White

        LowRed, MedRed, HighRed,       # 4–6: Red shades
        LowGreen, MedGreen, HighGreen, # 7–9: Green shades
        LowBlue, MedBlue, HighBlue,    # 10–12: Blue shades
        LowOrange, MedOrange, HighOrange, # 13–15: Orange shades
        LowYellow, MedYellow, HighYellow, # 16–18: Yellow shades
        LowPurple, MedPurple, HighPurple, # 19–21: Purple shades
        MedPink, HighPink, MaxPink,       # 22–24: Pink shades
        MedCyan, HighCyan, MaxCyan        # 25–27: Cyan shades
    )



    TextColorList = (
    (DarkPurple, LowPurple, MedPurple, HighPurple),  # 0: Purple family
    (DarkRed,    LowRed,    MedRed,    HighRed),     # 1: Red family
    (DarkOrange, LowOrange, MedOrange, HighOrange),  # 2: Orange family
    (DarkYellow, LowYellow, MedYellow, HighYellow),  # 3: Yellow family
    (DarkGreen,  LowGreen,  MedGreen,  HighGreen),   # 4: Green family
    (DarkBlue,   LowBlue,   MedBlue,   HighBlue),    # 5: Blue family
    (DarkPink,   LowPink,   MedPink,   HighPink),    # 6: Pink family
    (DarkCyan,   LowCyan,   MedCyan,   HighCyan)     # 7: Cyan family
    )

    print("Colors initialized with gamma:", Gamma)



    # ------------------------------------------------------------------------------
    # Generate legacy-style R, G, B channel variables for all key named colors
    # ------------------------------------------------------------------------------

    def make_rgb_channels(name, color):
        globals()[f"{name}R"] = color[0]
        globals()[f"{name}G"] = color[1]
        globals()[f"{name}B"] = color[2]

    for name in [
        "HighRed", "MedRed", "LowRed", "DarkRed", "ShadowRed",
        "HighGreen", "MedGreen", "LowGreen", "DarkGreen", "ShadowGreen",
        "HighBlue", "MedBlue", "LowBlue", "DarkBlue", "ShadowBlue",
        "HighOrange", "MedOrange", "LowOrange", "DarkOrange", "ShadowOrange",
        "HighYellow", "MedYellow", "LowYellow", "DarkYellow", "ShadowYellow",
        "HighPurple", "MedPurple", "LowPurple", "DarkPurple", "ShadowPurple",
        "HighPink", "MedPink", "LowPink", "DarkPink", "ShadowPink",
        "HighCyan", "MedCyan", "LowCyan", "DarkCyan", "ShadowCyan",
        "MaxWhite", "MaxRed", "MaxGreen", "MaxBlue", "MaxCyan"
    ]:
        make_rgb_channels(name, globals()[name])

    # ------------------------------------------------------------------------------
    # Game-specific color constants (compatibility with old Pac-Man style games)
    # ------------------------------------------------------------------------------

    global RedR, RedG, RedB
    RedR, RedG, RedB = HighRed

    global GreenR, GreenG, GreenB
    GreenR, GreenG, GreenB = HighGreen
    
    global OrangeR, OrangeG, OrangeB
    OrangeR, OrangeG, OrangeB = HighOrange

    global YellowR, YellowG, YellowB
    YellowR, YellowG, YellowB = HighYellow

    global PurpleR, PurpleG, PurpleB
    PurpleR, PurpleG, PurpleB = HighPurple

    global BlueR, BlueG, BlueB
    BlueR, BlueG, BlueB = HighBlue

    global PinkR, PinkG, PinkB
    PinkR, PinkG, PinkB = MaxPink

    global CyanR, CyanG, CyanB
    CyanR, CyanG, CyanB = MaxCyan





    DotRGB  = rgb(95, 95, 95)
    WallRGB = rgb(10, 10, 100)

    DotR, DotG, DotB     = DotRGB
    WallR, WallG, WallB  = WallRGB

    # Pac-Man Character Colors
    YellowRGB = rgb(220, 220, 0)
    PacR, PacG, PacB = YellowRGB

    Ghost1RGB = rgb(150, 0, 0)
    Ghost2RGB = rgb(130, 75, 0)
    Ghost3RGB = rgb(125, 0, 125)
    Ghost4RGB = rgb(0, 150, 150)

    Ghost1R, Ghost1G, Ghost1B = Ghost1RGB
    Ghost2R, Ghost2G, Ghost2B = Ghost2RGB
    Ghost3R, Ghost3G, Ghost3B = Ghost3RGB
    Ghost4R, Ghost4G, Ghost4B = Ghost4RGB

    # PowerPills and Scared Ghosts
    PillRGB = rgb(0, 200, 0)
    BlueGhostRGB = rgb(0, 0, 200)
    PillR, PillG, PillB = PillRGB
    BlueGhostR, BlueGhostG, BlueGhostB = BlueGhostRGB


InitializeColors()

