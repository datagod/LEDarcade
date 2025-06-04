# LEDweb.py - Control for LEDarcade actions
from multiprocessing import Queue
import os
from flask import Flask, request, jsonify
import logging

IMAGE_DIR = "/home/pi/LEDarcade/images"


def serve_web_control(queue, port=5055):
    """
    Starts a minimal Flask server to receive control commands.
    Supports all LEDarcade actions with field customization.
    """
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

    app = Flask(__name__)

    VALID_ACTIONS = {
        "showclock": [],
        "stopclock": [],
        "showtitlescreen": ["Text", "RGB", "Duration"],
        "analogclock": [],
        "starrynightdisplaytext": ["Text"],
        "launch_dotinvaders": [],
        "launch_defender": [],
        "launch_tron": [],
        "launch_outbreak": [],
        "launch_spacedot": [],
        "launch_fallingsand": [],
        "launch_gravitysim": [],
        "twitchtimer_on": [],
        "twitchtimer_off": [],
        "terminalmode_on": ["Message", "RGB", "Style", "Speed"],
        "terminalmessage": ["Message"],
        "terminalmode_off": [],
        "showheart": [],
        "showgif": ["GIF", "Duration"],
        "showviewers": [],
        "showimagezoom": ["Image"],
        "quit": []
    }

    def sanitize_data(data, action):
        if action in ["showtitlescreen", "terminalmode_on"]:
            if "RGB" in data and isinstance(data["RGB"], str):
                try:
                    data["RGB"] = tuple(map(int, data["RGB"].split(",")))
                except Exception:
                    data["RGB"] = (255, 255, 255)
        if action == "terminalmode_on":
            for key in ["Style", "Speed"]:
                if key in data:
                    try:
                        data[key] = int(data[key])
                    except ValueError:
                        pass
        if action in ["showtitlescreen", "showgif"]:
            if "Duration" in data:
                try:
                    data["Duration"] = int(data["Duration"])
                except ValueError:
                    pass
        if action == "showgif":
            if "GIF" in data and not data["GIF"].startswith("/"):
                data["GIF"] = os.path.join(IMAGE_DIR, os.path.basename(data["GIF"]))
        return data

    @app.route('/command', methods=['POST'])
    def handle_command():
        data = request.get_json() if request.is_json else request.form.to_dict()
        print(f"[LEDweb] Received: {data}")
        action = data.get("Action")
        if not action or action not in VALID_ACTIONS:
            return jsonify({'status': 'error', 'message': f'Invalid or missing action: {action}'}), 400
        data = sanitize_data(data, action)
        allowed_fields = set(VALID_ACTIONS[action] + ["Action"])
        filtered_data = {k: v for k, v in data.items() if k in allowed_fields}
        queue.put(filtered_data)
        return jsonify({'status': 'ok', 'message': f"Queued: {action}"}), 200

    @app.route('/', methods=['GET'])
    def homepage():
        html = """
        <html>
        <head>
            <title>LED Commander</title>
            <style>
                body { font-family: Arial, sans-serif; padding: 20px; }
                .command-section { margin-bottom: 40px; padding: 20px; border: 1px solid #ccc; border-radius: 8px; }
                .command-section h2 { margin-top: 0; }
                input[type="text"] { width: 300px; }
            </style>
        </head>
        <body>
        <h1>LED Commander Control Panel</h1>
        """
        for action, fields in VALID_ACTIONS.items():
            html += f'<div class="command-section">'
            html += f'<h2>{action} Command</h2>'
            html += '<form action="/command" method="post">'
            html += f'<input type="hidden" name="Action" value="{action}"/>'
            for field in fields:
                html += f'<label for="{field}">{field}:</label><br>'
                html += f'<input type="text" name="{field}" id="{field}"/><br><br>'
            html += '<input type="submit" value="Send Command"/>'
            html += '</form>'
            html += '</div>'
        html += """
        </body>
        </html>
        """
        return html

    app.run(host="0.0.0.0", port=port)
