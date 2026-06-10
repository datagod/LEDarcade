# LEDupdate.py - Shared update/restart support for LED Commander web panels
import os
import subprocess
import threading

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
UPDATE_SCRIPT = os.path.join(REPO_DIR, "update_ledarcade.sh")
LAUNCHER_FILE = os.path.join(REPO_DIR, "localdata", "launcher.cmd")

UPDATE_BAR_HTML = """
<div class="update-bar">
    <button type="button" id="update-button" class="update-button">Update</button>
    <span id="update-hint">Stop, git pull, auto-restart LED Commander</span>
</div>
"""

UPDATE_STYLES = """
.update-bar {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 24px;
    padding: 16px 20px;
    border: 2px solid #0f0;
    border-radius: 8px;
    background-color: #111;
    box-shadow: 0 0 12px rgba(0, 255, 0, 0.25);
    position: relative;
    z-index: 2;
}
.update-button {
    background-color: #0f0;
    color: #000;
    border: none;
    padding: 10px 24px;
    font-size: 16px;
    font-weight: bold;
    cursor: pointer;
    font-family: 'Courier New', monospace;
    border-radius: 4px;
}
.update-button:hover {
    background-color: #00ff00;
}
.update-button:disabled {
    opacity: 0.6;
    cursor: wait;
}
#update-hint {
    color: #0f0;
    font-size: 14px;
}
"""

UPDATE_STYLES_SIMPLE = """
.update-bar {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 24px;
    padding: 16px 20px;
    border: 1px solid #ccc;
    border-radius: 8px;
    background-color: #f7f7f7;
}
.update-button {
    background-color: #2563eb;
    color: #fff;
    border: none;
    padding: 10px 24px;
    font-size: 16px;
    font-weight: bold;
    cursor: pointer;
    border-radius: 4px;
}
.update-button:hover {
    background-color: #1d4ed8;
}
.update-button:disabled {
    opacity: 0.6;
    cursor: wait;
}
#update-hint {
    color: #444;
    font-size: 14px;
}
"""

UPDATE_SCRIPT = """
document.addEventListener('DOMContentLoaded', function() {
    const updateButton = document.getElementById('update-button');
    if (!updateButton) {
        return;
    }

    function waitForPanel() {
        let attempts = 0;
        const maxAttempts = 30;

        const timer = setInterval(() => {
            attempts += 1;
            fetch('/', { method: 'GET', cache: 'no-store' })
                .then(response => {
                    if (response.ok) {
                        clearInterval(timer);
                        window.location.reload();
                    }
                })
                .catch(() => {});

            if (attempts >= maxAttempts) {
                clearInterval(timer);
            }
        }, 2000);
    }

    updateButton.addEventListener('click', function() {
        if (!confirm('Update LEDarcade now? This will stop the display, run git pull, and restart automatically.')) {
            return;
        }

        updateButton.disabled = true;
        updateButton.innerText = 'Updating...';

        const statusMsg = document.getElementById('status-message');
        if (statusMsg) {
            statusMsg.innerText = 'Update started. Auto-restarting LED Commander...';
            statusMsg.className = 'success';
            statusMsg.style.display = 'block';
        }

        fetch('/update', { method: 'POST' })
            .then(response => response.json())
            .then(result => {
                if (statusMsg) {
                    statusMsg.innerText = result.message || 'Update started. Waiting for restart...';
                    statusMsg.className = result.status === 'ok' ? 'success' : 'error';
                    statusMsg.style.display = 'block';
                }
                if (result.status === 'ok') {
                    waitForPanel();
                }
            })
            .catch(() => {
                if (statusMsg) {
                    statusMsg.innerText = 'Update triggered. Waiting for restart...';
                    statusMsg.className = 'success';
                    statusMsg.style.display = 'block';
                }
                waitForPanel();
            });
    });
});
"""


def save_launcher(script_name):
    """Remember which entry script launched LEDarcade."""
    os.makedirs(os.path.dirname(LAUNCHER_FILE), exist_ok=True)
    with open(LAUNCHER_FILE, "w", encoding="utf-8") as launcher_file:
        launcher_file.write(f'LAUNCH_SCRIPT="{script_name}"\n')


def register_update_routes(app, queue):
    """Register the /update endpoint on a Flask app."""
    from flask import jsonify

    @app.route('/update', methods=['POST'])
    def handle_update():
        print("[LEDupdate] Update requested from control panel")
        queue.put({"Action": "quit"})

        def run_update():
            subprocess.Popen(
                ["bash", UPDATE_SCRIPT],
                cwd=REPO_DIR,
                start_new_session=True,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        threading.Timer(1.0, run_update).start()
        return jsonify({
            'status': 'ok',
            'message': 'Update started. Pulling latest code and auto-restarting LED Commander...'
        }), 200