# LEDpanel.py - Shared CRT-styled control panel for LED Commander
import LEDupdate
from WeatherClock import DEFAULT_LOCATION
from StockReport import LoadStockSymbols

PANEL_VERSION = "1.1"
PANEL_TITLE = f"LED Commander Control Panel {PANEL_VERSION}"

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
                    <label><input type="radio" name="Units" value="F" checked> F</label>
                    <label><input type="radio" name="Units" value="C"> C</label>
                </div>
                <input type="submit" value="Weather Report">
            </form>
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

    for action, fields in valid_actions.items():
        if action in ("weatherterminal", "stockterminal"):
            continue
        html += f'<div class="command-section"><h2>{action}</h2>'
        html += '<form class="command-form" action="/command" method="post">'
        html += f'<input type="hidden" name="Action" value="{action}">'
        for field in fields:
            html += f'<label>{field}<input type="text" name="{field}"></label>'
        html += '<input type="submit" value="Submit"></form></div>'

    html += """
        </div>
    </body>
    </html>
    """
    return html