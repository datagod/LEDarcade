# LEDupdate.py - Shared update/restart support for LED Commander web panels
import os
import subprocess
import sys
import threading
import time
from datetime import datetime

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
UPDATE_SCRIPT = os.path.join(REPO_DIR, "update_ledarcade.sh")
LAUNCHER_FILE = os.path.join(REPO_DIR, "localdata", "launcher.cmd")
LOG_DIR = os.path.join(REPO_DIR, "localdata")
LOG_FILE = os.path.join(LOG_DIR, "update.log")

# Exit code from the boot-update display worker when a pull succeeded and
# a restart has been scheduled.
BOOT_UPDATE_RESTART_EXIT = 42

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


def _log(message):
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {message}"
    print(f"[LEDupdate] {message}")
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as log_file:
            log_file.write(line + "\n")
    except OSError:
        pass


def _git(args, timeout=90):
    """Run a git command in the LEDarcade repo. Returns CompletedProcess."""
    return subprocess.run(
        ["git", *args],
        cwd=REPO_DIR,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _show_status(LED, message, hold=1.5):
    """Show a short status message on the LED matrix (clock panel)."""
    LED.ClearBigLED()
    LED.ClearBuffers()
    screen = [[(0, 0, 0) for _ in range(LED.HatWidth)] for _ in range(LED.HatHeight)]
    cursor_h = 0
    cursor_v = 0
    screen, cursor_h, cursor_v = LED.TerminalScroll(
        screen,
        message,
        CursorH=cursor_h,
        CursorV=cursor_v,
        MessageRGB=(0, 200, 0),
        CursorRGB=(0, 255, 0),
        CursorDarkRGB=(0, 50, 0),
        StartingLineFeed=1,
        TypeSpeed=0.01,
        ScrollSpeed=0.01,
    )
    blinks = max(1, int(hold / 0.6))
    LED.BlinkCursor(
        CursorH=cursor_h,
        CursorV=cursor_v,
        CursorRGB=(0, 255, 0),
        CursorDarkRGB=(0, 50, 0),
        BlinkSpeed=0.3,
        BlinkCount=blinks,
    )


def _upstream_ref():
    """Return origin/<branch> for the current branch, or None if unavailable."""
    branch = _git(["rev-parse", "--abbrev-ref", "HEAD"], timeout=15)
    if branch.returncode != 0:
        return None
    name = (branch.stdout or "").strip()
    if not name or name == "HEAD":
        return None
    return f"origin/{name}"


def _is_behind_origin():
    """
    Fetch from origin and return True if local HEAD is behind the remote branch.
    Returns (behind: bool, detail: str).
    """
    upstream = _upstream_ref()
    if not upstream:
        return False, "no upstream branch"

    fetch = _git(["fetch", "origin"], timeout=90)
    if fetch.returncode != 0:
        err = (fetch.stderr or fetch.stdout or "fetch failed").strip()
        return False, f"git fetch failed: {err[:200]}"

    local = _git(["rev-parse", "HEAD"], timeout=15)
    remote = _git(["rev-parse", upstream], timeout=15)
    if local.returncode != 0 or remote.returncode != 0:
        return False, "could not resolve HEAD or upstream"

    local_sha = (local.stdout or "").strip()
    remote_sha = (remote.stdout or "").strip()
    if not local_sha or not remote_sha:
        return False, "empty revision"

    if local_sha == remote_sha:
        return False, "up to date"

    # Only treat as update-needed when remote has commits we don't.
    counts = _git(
        ["rev-list", "--left-right", "--count", f"HEAD...{upstream}"],
        timeout=15,
    )
    if counts.returncode != 0:
        # Fall back to SHA inequality (includes diverged / ahead cases).
        return True, f"local {local_sha[:7]} != remote {remote_sha[:7]}"

    parts = (counts.stdout or "").strip().split()
    try:
        ahead = int(parts[0])
        behind = int(parts[1])
    except (IndexError, ValueError):
        return True, f"local {local_sha[:7]} != remote {remote_sha[:7]}"

    if behind > 0:
        return True, f"behind by {behind} commit(s) (ahead {ahead})"
    return False, f"up to date (ahead {ahead})"


def _schedule_restart_only():
    """Detach a restart that stops LEDarcade and relaunches without another pull."""
    _log("Scheduling restart after boot update")
    subprocess.Popen(
        ["bash", UPDATE_SCRIPT, "--restart-only"],
        cwd=REPO_DIR,
        start_new_session=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _boot_update_process():
    """
    Display-subprocess entry: show status on the matrix, pull if needed.
    Exit 0 = continue, 42 = update applied + restart scheduled, 1 = error continue.
    """
    # GPIO/matrix must only be touched inside a child process (LEDcommander rule).
    import LEDarcade as LED

    LED.Initialize()
    try:
        LED.TheMatrix.brightness = 80
    except Exception:
        pass

    try:
        _show_status(LED, "Checking for Updates", hold=1.0)
        _log("Boot check: looking for updates on GitHub")

        try:
            behind, detail = _is_behind_origin()
        except subprocess.TimeoutExpired:
            _log("Boot check: git timed out")
            _show_status(LED, "Update check timeout", hold=2.0)
            sys.exit(1)
        except Exception as exc:
            _log(f"Boot check: error during fetch: {exc}")
            _show_status(LED, "Update check failed", hold=2.0)
            sys.exit(1)

        _log(f"Boot check: {detail}")
        if not behind:
            # Brief confirmation then hand off to normal clock rotation.
            _show_status(LED, "Up to date", hold=1.2)
            sys.exit(0)

        _show_status(LED, "Downloading", hold=1.0)
        _log("Boot update: git pull --ff-only")
        try:
            pull = _git(["pull", "--ff-only"], timeout=120)
        except subprocess.TimeoutExpired:
            _log("Boot update: git pull timed out")
            _show_status(LED, "Download timeout", hold=2.0)
            sys.exit(1)

        if pull.returncode != 0:
            err = (pull.stderr or pull.stdout or "pull failed").strip()
            _log(f"Boot update: git pull failed: {err[:300]}")
            _show_status(LED, "Download failed", hold=2.5)
            sys.exit(1)

        _log("Boot update: pull succeeded")
        _show_status(LED, "Installing", hold=2.0)
        _schedule_restart_only()
        # Keep matrix message visible until the restart script stops us.
        time.sleep(1.0)
        sys.exit(BOOT_UPDATE_RESTART_EXIT)
    except SystemExit:
        raise
    except Exception as exc:
        _log(f"Boot update worker crashed: {exc}")
        try:
            _show_status(LED, "Update error", hold=2.0)
        except Exception:
            pass
        sys.exit(1)


def run_boot_update_check():
    """
    Called once when LEDcommander starts. Shows status on the panel, pulls from
    GitHub if behind origin, then restarts LEDarcade so the new code loads.

    Set LEDARCADE_SKIP_BOOT_UPDATE=1 to skip (useful while developing).
    """
    skip = os.environ.get("LEDARCADE_SKIP_BOOT_UPDATE", "").strip().lower()
    if skip in ("1", "true", "yes", "on"):
        _log("Boot update check skipped (LEDARCADE_SKIP_BOOT_UPDATE)")
        return

    _log("=== Boot update check starting ===")
    from multiprocessing import Process

    worker = Process(target=_boot_update_process, name="LEDbootUpdate")
    worker.start()
    worker.join(timeout=180)

    if worker.is_alive():
        _log("Boot update check timed out — terminating worker")
        worker.terminate()
        worker.join(timeout=5)
        return

    code = worker.exitcode
    if code == BOOT_UPDATE_RESTART_EXIT:
        _log("Update installed — waiting for restart script to relaunch LEDarcade")
        # Restart script will pkill this process tree. Stay idle until then.
        time.sleep(90)
        _log("Restart did not kill us — exiting so stale code is not used")
        os._exit(0)

    if code not in (0, None):
        _log(f"Boot update finished with code {code} — continuing without restart")
    else:
        _log("Boot update check complete — no restart needed")


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