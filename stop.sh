#!/bin/bash
# Stop all LEDarcade running processes.

set -u

LEDARCADE_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$LEDARCADE_DIR/localdata"
LOG_FILE="$LOG_DIR/update.log"

mkdir -p "$LOG_DIR"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [stop] $*" | tee -a "$LOG_FILE"
}

is_stop_script() {
    local cmd="$1"
    case "$cmd" in
        *stop.sh*|*update_ledarcade.sh*)
            return 0
            ;;
    esac
    return 1
}

matching_pids() {
    local pattern="$1"
    local pid cmd

    for pid in $(pgrep -f "$pattern" 2>/dev/null || true); do
        cmd=$(ps -p "$pid" -o args= 2>/dev/null || true)
        if [ -z "$cmd" ] || is_stop_script "$cmd"; then
            continue
        fi
        echo "$pid"
    done
}

kill_pattern() {
    local pattern="$1"
    local label="$2"
    local pid

    if [ -z "$(matching_pids "$pattern")" ]; then
        return 0
    fi

    log "Stopping $label"
    pkill -f "$pattern" 2>/dev/null || true
    if command -v sudo >/dev/null 2>&1; then
        sudo pkill -f "$pattern" 2>/dev/null || true
    fi
}

force_kill_pattern() {
    local pattern="$1"
    local label="$2"

    if [ -z "$(matching_pids "$pattern")" ]; then
        return 0
    fi

    log "Force stopping $label"
    pkill -9 -f "$pattern" 2>/dev/null || true
    if command -v sudo >/dev/null 2>&1; then
        sudo pkill -9 -f "$pattern" 2>/dev/null || true
    fi
}

still_running() {
    local patterns=(
        "python3.*$LEDARCADE_DIR"
        "sudo -n python3.*$LEDARCADE_DIR"
        "sudo python3.*$LEDARCADE_DIR"
        "$LEDARCADE_DIR/start_ledarcade.sh"
        "python3 (twitch|LEDcommander|arcade)\\.py"
        "sudo(-n)? python3 (twitch|LEDcommander|arcade)\\.py"
    )
    local pattern

    for pattern in "${patterns[@]}"; do
        if [ -n "$(matching_pids "$pattern")" ]; then
            return 0
        fi
    done
    return 1
}

log "=== Stopping LEDarcade ==="

if screen -ls ledarcade 2>/dev/null | grep -q "[0-9]*\\.ledarcade"; then
    log "Closing screen session 'ledarcade'"
    screen -S ledarcade -X quit 2>/dev/null || true
fi

kill_pattern "$LEDARCADE_DIR/start_ledarcade.sh" "start_ledarcade.sh"
kill_pattern "start_ledarcade.sh --foreground" "start_ledarcade foreground wrapper"
kill_pattern "python3.*$LEDARCADE_DIR" "python3 (LEDarcade directory)"
kill_pattern "sudo -n python3.*$LEDARCADE_DIR" "sudo -n python3 (LEDarcade directory)"
kill_pattern "sudo python3.*$LEDARCADE_DIR" "sudo python3 (LEDarcade directory)"

LAUNCHERS=(
    twitch.py
    LEDcommander.py
    arcade.py
    particles.py
    Defender.py
    Defender2.py
    Outbreak.py
    Blasteroids.py
    DotInvaders.py
    FallingSand.py
    gravitysim.py
    Tron.py
    SpaceDot.py
    MazeCar.py
    StockTicker.py
    AnalogClock.py
    WeatherClock.py
    LEDweb.py
    LEDpanel.py
    OnAir.py
    RunningTest.py
    demo.py
    clock.py
)

for script in "${LAUNCHERS[@]}"; do
    kill_pattern "python3 ${script}" "$script"
    kill_pattern "python3 .*${LEDARCADE_DIR}/${script}" "$script (full path)"
    kill_pattern "sudo python3 ${script}" "$script (sudo)"
    kill_pattern "sudo -n python3 ${script}" "$script (sudo -n)"
done

sleep 2

if still_running; then
    log "Some processes did not exit cleanly; sending SIGKILL"
    force_kill_pattern "$LEDARCADE_DIR/start_ledarcade.sh" "start_ledarcade.sh"
    force_kill_pattern "python3.*$LEDARCADE_DIR" "python3 (LEDarcade directory)"
    force_kill_pattern "sudo -n python3.*$LEDARCADE_DIR" "sudo -n python3 (LEDarcade directory)"
    force_kill_pattern "sudo python3.*$LEDARCADE_DIR" "sudo python3 (LEDarcade directory)"
    force_kill_pattern "python3 (twitch|LEDcommander|arcade)\\.py" "launcher scripts"
    force_kill_pattern "sudo(-n)? python3 (twitch|LEDcommander|arcade)\\.py" "sudo launcher scripts"
    sleep 1
fi

if still_running; then
    log "ERROR: Could not stop all LEDarcade processes. Try: sudo bash $LEDARCADE_DIR/stop.sh"
    for pid in $(matching_pids "python3.*$LEDARCADE_DIR"); do
        ps -p "$pid" -o pid=,args= 2>/dev/null | tee -a "$LOG_FILE" || true
    done
    exit 1
fi

log "All LEDarcade processes stopped"