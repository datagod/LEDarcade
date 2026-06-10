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

wait_for_panel() {
    local attempt
    for attempt in $(seq 1 30); do
        if curl -sf "http://127.0.0.1:${PORT}/" >/dev/null 2>&1; then
            log "Control panel is back online on port ${PORT}"
            return 0
        fi
        sleep 2
    done
    log "WARNING: Control panel did not respond on port ${PORT} within 60 seconds"
    return 1
}

log "=== LEDarcade update started ==="

sleep 2

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

log "Auto-restarting LEDarcade"
if bash "$LEDARCADE_DIR/start_ledarcade.sh" >> "$LOG_FILE" 2>&1; then
    wait_for_panel || true
    log "=== LEDarcade update complete ==="
else
    log "ERROR: Auto-restart failed. Check $LOG_FILE or run: sudo python3 twitch.py"
    exit 1
fi