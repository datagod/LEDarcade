# LEDpanel.py - Shared CRT-styled control panel for LED Commander
import LEDupdate
from WeatherClock import DEFAULT_LOCATION
from StockReport import LoadStockSymbols

PANEL_VERSION = "1.5"
PANEL_TITLE = f"LED Commander Control Panel {PANEL_VERSION}"

DEFAULT_GAME_DURATION = 10
# Games that default to play-until-game-over (duration 0)
UNTIL_GAME_OVER_LAUNCHERS = {
    "launch_rallydot",
}

GAME_LAUNCHERS = [
    ("launch_dotinvaders", "Dot Invaders"),
    ("launch_defender", "Defender"),
    ("launch_defender2", "Defender 2"),
    ("launch_tron", "Tron"),
    ("launch_outbreak", "Outbreak"),
    ("launch_ledtv", "LED TV"),
    ("launch_spacedot", "Space Dot"),
    ("launch_pacdot", "PacDot"),
    ("launch_dotzerk", "DotZerk"),
    ("launch_blasteroids", "Blasteroids"),
    ("launch_fallingsand", "Falling Sand"),
    ("launch_particles", "Particles"),
    ("launch_gravitysim", "Gravity Sim"),
    ("launch_mazecar", "Maze Car"),
    ("launch_spaceexplorer", "Space Explorer"),
    ("launch_skyfall", "Skyfall"),
    ("launch_rallydot", "Rally Dot"),  # last — also last in idle rotation
]

ACTION_LABELS = {
    "showclock": "Digital Clock",
    "stopclock": "Stop Clock",
    "stop": "Stop Display",
    "showtitlescreen": "Title Screen",
    "analogclock": "Analog Clock",
    "retrodigital": "Retro Digital",
    "starrynightdisplaytext": "Starry Night Text",
    "launch_stockticker": "Stock Ticker",
    "launch_ledtv": "LED TV",
    "launch_pacdot": "PacDot",
    "launch_dotzerk": "DotZerk",
    "launch_rallydot": "Rally Dot",
    "twitchtimer_on": "Twitch Timer On",
    "twitchtimer_off": "Twitch Timer Off",
    "terminalmode_on": "Terminal Mode On",
    "terminalmessage": "Terminal Message",
    "terminalmode_off": "Terminal Mode Off",
    "showheart": "Show Heart",
    "showintro": "Show Intro",
    "showonair": "On Air",
    "showonair_off": "On Air Off",
    "showdemotivate": "Demotivator",
    "showgif": "Show GIF",
    "showviewers": "Show Viewers",
    "showimagezoom": "Image Zoom",
    "quit": "Quit",
}

PANEL_STYLES = """
body {
    font-family: 'Courier New', monospace;
    padding: 20px;
    background-color: #000;
    color: #0f0;
    text-shadow: 0 0 5px rgba(0, 255, 0, 0.5);
    position: relative;
}
body::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: repeating-linear-gradient(
        to bottom,
        transparent 0px,
        transparent 1px,
        rgba(0, 0, 0, 0.3) 1px,
        rgba(0, 0, 0, 0.3) 2px
    );
    pointer-events: none;
    z-index: 1;
    opacity: 0.5;
}
.panel-header {
    position: relative;
    z-index: 2;
    margin-bottom: 20px;
}
.panel-header h1 {
    margin: 0 0 16px 0;
    color: #0f0;
}
.commands-container {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 20px;
    position: relative;
    z-index: 2;
}
.command-section {
    padding: 15px;
    border: 1px solid #0f0;
    border-radius: 5px;
    background-color: #111;
    box-shadow: 0 0 10px rgba(0, 255, 0, 0.2);
}
.command-section h2 {
    margin-top: 0;
    color: #0f0;
    font-size: 1rem;
    word-break: break-word;
}
label {
    color: #0f0;
    display: block;
    margin-bottom: 8px;
}
p {
    color: #0a0;
    font-size: 0.85rem;
    margin: 0 0 8px 0;
}
input[type="text"] {
    width: 100%;
    box-sizing: border-box;
    background-color: #222;
    color: #0f0;
    border: 1px solid #0f0;
    padding: 5px;
    font-family: 'Courier New', monospace;
    margin-top: 4px;
}
input[type="submit"] {
    background-color: #0f0;
    color: #000;
    border: none;
    padding: 8px 12px;
    cursor: pointer;
    font-family: 'Courier New', monospace;
    margin-top: 8px;
}
input[type="submit"]:hover {
    background-color: #00ff00;
}
.unit-choice {
    display: flex;
    gap: 16px;
    margin: 8px 0 12px 0;
}
.unit-choice label {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 0;
    cursor: pointer;
}
.unit-choice input[type="radio"] {
    accent-color: #0f0;
}
#status-message {
    position: fixed;
    top: 10px;
    left: 50%;
    transform: translateX(-50%);
    padding: 10px 16px;
    border-radius: 5px;
    z-index: 1000;
    display: none;
}
.success {
    background-color: #004400;
    color: #0f0;
    border: 1px solid #0f0;
}
.error {
    background-color: #440000;
    color: #ff0000;
    border: 1px solid #ff0000;
}
.games-section {
    grid-column: 1 / -1;
}
.games-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 20px;
    margin-top: 12px;
}
.game-note {
    font-size: 0.85em;
    color: #0a0;
    margin: 0.25em 0 0.5em 0;
    opacity: 0.9;
}
.game-card h3 {
    margin: 0 0 10px 0;
    color: #0f0;
    font-size: 1rem;
}
""" + LEDupdate.UPDATE_STYLES

FORM_SUBMIT_SCRIPT = """
document.addEventListener('DOMContentLoaded', function() {
    const forms = document.querySelectorAll('form.command-form');
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            event.preventDefault();
            const formData = new FormData(form);
            const data = Object.fromEntries(formData.entries());

            fetch('/command', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(result => {
                const statusMsg = document.getElementById('status-message');
                statusMsg.innerText = result.message;
                statusMsg.className = result.status === 'ok' ? 'success' : 'error';
                statusMsg.style.display = 'block';
                setTimeout(() => { statusMsg.style.display = 'none'; }, 3000);
            })
            .catch(error => {
                const statusMsg = document.getElementById('status-message');
                statusMsg.innerText = 'Error: ' + error;
                statusMsg.className = 'error';
                statusMsg.style.display = 'block';
                setTimeout(() => { statusMsg.style.display = 'none'; }, 3000);
            });
        });
    });
});
"""


def render_stock_section(default_symbols=None):
    """Dedicated stock report control."""
    if default_symbols is None:
        default_symbols = ", ".join(LoadStockSymbols())
    return f"""
        <div class="command-section stock-section">
            <h2>Stock Report</h2>
            <form class="command-form" action="/command" method="post">
                <input type="hidden" name="Action" value="stockterminal">
                <label>Symbols
                    <input type="text" name="symbols" value="{default_symbols}" placeholder="TSLA MSFT AAPL">
                </label>
                <p>Comma or space separated. Leave blank to use KeyConfig.ini.</p>
                <input type="submit" value="Stock Report">
            </form>
        </div>
    """


def render_weather_section(default_location=DEFAULT_LOCATION):
    """Dedicated weather report control with location input."""
    return f"""
        <div class="command-section weather-section">
            <h2>Weather Report</h2>
            <form class="command-form" action="/command" method="post">
                <input type="hidden" name="Action" value="weatherterminal">
                <label>Location
                    <input type="text" name="Location" value="{default_location}" placeholder="{default_location}">
                </label>
                <div class="unit-choice">
                    <span>Units:</span>
                    <label><input type="radio" name="Units" value="C" checked> C</label>
                    <label><input type="radio" name="Units" value="F"> F</label>
                </div>
                <input type="submit" value="Weather Report">
            </form>
        </div>
    """


def render_ledtv_section():
    """Dedicated LED TV launch control (same action as Twitch ?tv)."""
    return f"""
        <div class="command-section ledtv-section">
            <h2>LED TV</h2>
            <form class="command-form" action="/command" method="post">
                <input type="hidden" name="Action" value="launch_ledtv">
                <input type="hidden" name="effect" value="channels">
                <label>Duration (minutes)
                    <input type="text" name="duration" value="5" placeholder="5">
                </label>
                <p>Channel surf: static, CHn flashes, videos &amp; specialty channels. Same as Twitch <code>?tv</code>.</p>
                <input type="submit" value="Launch LED TV">
            </form>
        </div>
    """


def _action_label(action):
    return ACTION_LABELS.get(action, action)


def _game_launcher_actions(valid_actions):
    return [
        (action, title)
        for action, title in GAME_LAUNCHERS
        if action in valid_actions
    ]


def render_games_section(valid_actions):
    """Grouped launch controls for arcade games and sims."""
    games = _game_launcher_actions(valid_actions)
    if not games:
        return ""

    cards = []
    for action, title in games:
        # LED TV has its own top-level section; skip duplicate card
        if action == "launch_ledtv":
            continue
        fields = valid_actions[action]
        field_html = ""
        until_go = action in UNTIL_GAME_OVER_LAUNCHERS
        for field in fields:
            if field == "duration":
                # 0 = until game over (Rally Dot default)
                value = 0 if until_go else DEFAULT_GAME_DURATION
            else:
                value = ""
            field_html += (
                f'<label>{field}'
                f'<input type="text" name="{field}" value="{value}"></label>'
            )
        note = ""
        if until_go:
            note = (
                '<p class="game-note">Default duration 0 = play until game over '
                '(3 lives). Set minutes to cap the run.</p>'
            )
        cards.append(f"""
            <div class="command-section game-card">
                <h3>{title}</h3>
                {note}
                <form class="command-form" action="/command" method="post">
                    <input type="hidden" name="Action" value="{action}">
                    {field_html}
                    <input type="submit" value="Launch {title}">
                </form>
            </div>
        """)

    return f"""
        <div class="command-section games-section">
            <h2>Games &amp; Simulations</h2>
            <p>Duration is in minutes (0 = until game over where supported).
               Games here are part of the idle rotation.</p>
            <div class="games-grid">
                {"".join(cards)}
            </div>
        </div>
    """


def render_homepage(valid_actions):
    """Render the CRT-themed LED Commander control panel."""
    html = f"""
    <html>
    <head>
        <title>LED Commander {PANEL_VERSION}</title>
        <style>
            {PANEL_STYLES}
        </style>
        <script>
            {LEDupdate.UPDATE_SCRIPT}
            {FORM_SUBMIT_SCRIPT}
        </script>
    </head>
    <body>
        <div id="status-message"></div>
        <div class="panel-header">
            <h1>{PANEL_TITLE}</h1>
            {LEDupdate.UPDATE_BAR_HTML}
        </div>
        <div class="commands-container">
    """

    html += render_weather_section()
    html += render_stock_section()
    if "launch_ledtv" in valid_actions:
        html += render_ledtv_section()
    html += render_games_section(valid_actions)

    game_actions = {action for action, _ in GAME_LAUNCHERS}
    for action, fields in valid_actions.items():
        if action in ("weatherterminal", "stockterminal", "launch_ledtv") or action in game_actions:
            continue
        label = _action_label(action)
        html += f'<div class="command-section"><h2>{label}</h2>'
        html += '<form class="command-form" action="/command" method="post">'
        html += f'<input type="hidden" name="Action" value="{action}">'
        for field in fields:
            html += f'<label>{field}<input type="text" name="{field}"></label>'
        html += f'<input type="submit" value="{label}"></form></div>'

    html += """
        </div>
    </body>
    </html>
    """
    return html