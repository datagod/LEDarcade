# LEDweb.py
from multiprocessing import  Queue
import queue

import os
from flask import send_from_directory

IMAGE_DIR = "/home/pi/LEDarcade/images"


def serve_web_control(queue, port=5055):
    """
    Starts a minimal Flask server to receive control commands.
    Expected JSON format: { "Action": "<ActionName>" }
    """
    from flask import Flask, request, jsonify
    import logging

    # Suppress Flask's default logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

    app = Flask(__name__)



    @app.route('/command', methods=['POST'])
    def handle_command():
        if request.is_json:
            raw_data = request.get_json()
        else:
            raw_data = request.form.to_dict()

        print(f"[LEDweb] Received: {raw_data}")

        if not raw_data or 'Action' not in raw_data:
            return jsonify({'status': 'error', 'message': 'Missing action field'}), 400

        data = raw_data

        # Cast numeric fields if needed
        for k in ['Zoom', 'Style', 'Duration', 'Delay', 'loops']:
            if k in data:
                try:
                    data[k] = int(data[k])
                except:
                    pass


        # Auto-prepend full path for GIF field if needed
        if 'GIF' in data:
            if not data['GIF'].startswith('/'):
                data['GIF'] = os.path.join(IMAGE_DIR, os.path.basename(data['GIF']))
        queue.put(data)


        
        return jsonify({'status': 'ok', 'message': f"Queued: {data['Action']}"}), 200

    @app.route('/', methods=['GET'])
    def homepage():
        return '''
        <html>
        <head><title>LED Commander</title></head>
        <body>
        <h1>LED Commander Control Panel</h1>

        <h2>Show Clock</h2>
        <form method="post" action="/command">
            <input type="hidden" name="Action" value="showclock">
            Style: <input type="number" name="Style" value="1"><br>
            Zoom: <input type="number" name="Zoom" value="2"><br>
            Duration (min): <input type="number" name="Duration" value="1"><br>
            Delay (ms): <input type="number" name="Delay" value="30"><br>
            <button type="submit">Start Clock</button>
        </form>

        <h2>Show Title Screen</h2>
        <form method="post" action="/command">
            <input type="hidden" name="Action" value="showtitlescreen">
            BigText: <input type="text" name="BigText" value="Hello"><br>
            LittleText: <input type="text" name="LittleText" value="World"><br>
            ScrollText: <input type="text" name="ScrollText" value="Welcome to LEDCommander"><br>
            <button type="submit">Show Title Screen</button>
        </form>

        <h2>Show GIF</h2>
        <form method="post" action="/command">
            <input type="hidden" name="Action" value="showgif">
            GIF Path: <input type="text" name="GIF" value="./images/minions.gif"><br>
            Loops: <input type="number" name="loops" value="5"><br>
            <button type="submit">Show GIF</button>
        </form>
        </body>
        </html>
        '''

    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)



if __name__ == "__main__":
  CommandQueue = Queue()
  serve_web_control(CommandQueue, port=5055)