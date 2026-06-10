#!/bin/bash
# Start LEDarcade using the last known launcher, with sudo fallback.

set -u

LEDARCADE_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$LEDARCADE_DIR/localdata"
LOG_FILE="$LOG_DIR/update.log"
LAUNCHER_FILE="$LOG_DIR/launcher.cmd"

mkdir -p "$LOG_DIR"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG_FILE"
}

if [ -f "$LAUNCHER_FILE" ]; then
    # shellcheck disable=SC1090
    source "$LAUNCHER_FILE"
fi

LAUNCH_SCRIPT="${LAUNCH_SCRIPT:-twitch.py}"

cd "$LEDARCADE_DIR" || exit 1

run_launcher() {
    local use_sudo="$1"
    if [ "$use_sudo" = "1" ]; then
        sudo -n python3 "$LAUNCH_SCRIPT"
    else
        python3 "$LAUNCH_SCRIPT"
    fi
}

log "Starting LEDarcade with $LAUNCH_SCRIPT"

if command -v screen >/dev/null 2>&1; then
    screen -S ledarcade -X quit 2>/dev/null || true
    if screen -S ledarcade -d -m bash -c "cd '$LEDARCADE_DIR' && '$LEDARCADE_DIR/start_ledarcade.sh' --foreground >> '$LOG_FILE' 2>&1"; then
        log "Started in screen session 'ledarcade'"
        exit 0
    fi
fi

if [ "${1:-}" = "--foreground" ]; then
    if run_launcher 0; then
        exit 0
    fi
    log "Direct launch failed; retrying with sudo -n"
    if run_launcher 1; then
        exit 0
    fi
    log "ERROR: Could not start $LAUNCH_SCRIPT. Configure passwordless sudo for python3 or run manually."
    exit 1
fi

nohup bash -c "cd '$LEDARCADE_DIR' && '$LEDARCADE_DIR/start_ledarcade.sh' --foreground" >> "$LOG_FILE" 2>&1 &
log "Started with nohup (pid $!)"