#!/bin/bash
# Safely stop LEDarcade, pull latest code, and relaunch.

set -u

LEDARCADE_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$LEDARCADE_DIR/localdata"
LOG_FILE="$LOG_DIR/update.log"
PORT=5055

mkdir -p "$LOG_DIR"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG_FILE"
}

log "=== LEDarcade update started ==="

sleep 2

if pgrep -f "python3 twitch.py" >/dev/null 2>&1; then
    LAUNCH_CMD="sudo python3 twitch.py"
    log "Detected twitch.py launcher"
elif pgrep -f "python3 LEDcommander.py" >/dev/null 2>&1; then
    LAUNCH_CMD="sudo python3 LEDcommander.py"
    log "Detected LEDcommander.py launcher"
else
    LAUNCH_CMD="sudo python3 twitch.py"
    log "No launcher detected; defaulting to twitch.py"
fi

log "Stopping LEDarcade processes"
pkill -f "python3 twitch.py" 2>/dev/null || true
pkill -f "python3 LEDcommander.py" 2>/dev/null || true
pkill -f "LEDweb.py" 2>/dev/null || true
sleep 2

cd "$LEDARCADE_DIR" || exit 1

log "Running git pull"
if git pull >> "$LOG_FILE" 2>&1; then
    log "git pull succeeded"
else
    log "git pull failed"
    exit 1
fi

log "Relaunching: $LAUNCH_CMD"
if command -v screen >/dev/null 2>&1; then
    screen -S ledarcade -X quit 2>/dev/null || true
    screen -S ledarcade -d -m bash -c "cd '$LEDARCADE_DIR' && $LAUNCH_CMD >> '$LOG_FILE' 2>&1"
    log "Relaunched in screen session 'ledarcade'"
else
    nohup bash -c "cd '$LEDARCADE_DIR' && $LAUNCH_CMD" >> "$LOG_FILE" 2>&1 &
    log "Relaunched with nohup (pid $!)"
fi

log "=== LEDarcade update complete ==="