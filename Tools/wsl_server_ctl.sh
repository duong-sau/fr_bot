#!/usr/bin/env bash
set -euo pipefail

# Start/stop the FR Bot FastAPI server on WSL setups that don't have systemd
# as PID 1 (so install.sh's `install_systemd_server` can't be used). Runs
# uvicorn under a restart-on-crash loop, backgrounded with setsid so it
# survives the shell that launched it, and tracks it via a PID file.
#
# Meant to be invoked from the [boot] `command` in /etc/wsl.conf so the
# server comes back up automatically whenever the WSL instance (re)starts:
#
#   [boot]
#   command = "su - <user> -c '/home/ubuntu/fr_bot/code/Tools/wsl_server_ctl.sh start'"
#
# Windows itself does not launch WSL at boot on its own; pair this with a
# Windows Task Scheduler entry that runs `wsl.exe -d <Distro> true` at user
# logon (or "At startup") to trigger that boot command automatically.

APP_ROOT="${APP_ROOT:-/home/ubuntu/fr_bot}"
CODE_DIR="${CODE_DIR:-$APP_ROOT/code}"
VENV_DIR="${VENV_DIR:-$APP_ROOT/venv}"
LOG_DIR="${LOG_DIR:-$APP_ROOT/logs}"
APP_MODULE="${APP_MODULE:-Server.App:app}"
APP_PORT="${APP_PORT:-8000}"
PID_FILE="${PID_FILE:-$APP_ROOT/frbot-server.pid}"
LOG_FILE="$LOG_DIR/server.log"

is_running() {
  [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null
}

__supervise() {
  cd "$CODE_DIR"
  while true; do
    "$VENV_DIR/bin/uvicorn" "$APP_MODULE" --host 127.0.0.1 --port "$APP_PORT" --log-level info
    echo "[WARN] $(date -Iseconds) server exited, restarting in 3s"
    sleep 3
  done
}

start() {
  if is_running; then
    echo "[INFO] Already running (pid $(cat "$PID_FILE"))."
    return 0
  fi
  mkdir -p "$LOG_DIR"
  echo "[INFO] Starting FR Bot server (restart-on-crash loop) -> $LOG_FILE"
  setsid "$0" __supervise >>"$LOG_FILE" 2>&1 </dev/null &
  disown
  echo $! > "$PID_FILE"
  sleep 1
  echo "[INFO] Started, supervisor pid $(cat "$PID_FILE"). Tail logs: tail -f $LOG_FILE"
}

stop() {
  if ! is_running; then
    echo "[INFO] Not running."
    rm -f "$PID_FILE"
    return 0
  fi
  local pid
  pid="$(cat "$PID_FILE")"
  echo "[INFO] Stopping supervisor pid $pid and its children..."
  pkill -TERM -P "$pid" 2>/dev/null || true
  kill -TERM "$pid" 2>/dev/null || true
  sleep 1
  pkill -KILL -P "$pid" 2>/dev/null || true
  kill -KILL "$pid" 2>/dev/null || true
  rm -f "$PID_FILE"
  echo "[INFO] Stopped."
}

status() {
  if is_running; then
    echo "[INFO] Running, supervisor pid $(cat "$PID_FILE")."
  else
    echo "[INFO] Not running."
  fi
}

case "${1:-}" in
  start) start ;;
  stop) stop ;;
  restart) stop; start ;;
  status) status ;;
  __supervise) __supervise ;;
  *) echo "Usage: $0 {start|stop|restart|status}" >&2; exit 1 ;;
esac
