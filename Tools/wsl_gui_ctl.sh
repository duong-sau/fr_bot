#!/usr/bin/env bash
set -euo pipefail

# Start/stop the FR Bot web GUI (web-ui/, a React dev server) alongside the
# server, for setups without systemd as PID 1 (mirrors Tools/wsl_server_ctl.sh).
# Runs `npm start` under a restart-on-crash loop, backgrounded with setsid so
# it survives the shell that launched it, and tracks it via a PID file.
#
# install.sh only wires this up when is_wsl() is true -- the GUI is a Node/
# React dev server meant for a WSL dev machine sharing the host with the
# server, not something to run unattended on a bare Linux box.

APP_ROOT="${APP_ROOT:-/home/ubuntu/fr_bot}"
CODE_DIR="${CODE_DIR:-$APP_ROOT/code}"
GUI_DIR="${GUI_DIR:-$CODE_DIR/web-ui}"
LOG_DIR="${LOG_DIR:-$APP_ROOT/logs}"
GUI_PORT="${GUI_PORT:-3000}"
PID_FILE="${PID_FILE:-$APP_ROOT/frbot-gui.pid}"
LOG_FILE="$LOG_DIR/gui.log"

is_running() {
  [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null
}

__supervise() {
  cd "$GUI_DIR"
  while true; do
    # BROWSER=none: don't try to open a tab on a headless WSL host.
    # CI=true: fail fast instead of hanging on the "port already in use,
    # run on another port? (Y/n)" prompt, since stdin is /dev/null here.
    PORT="$GUI_PORT" BROWSER=none CI=true npm start
    echo "[WARN] $(date -Iseconds) GUI exited, restarting in 3s"
    sleep 3
  done
}

start() {
  if is_running; then
    echo "[INFO] Already running (pid $(cat "$PID_FILE"))."
    return 0
  fi
  mkdir -p "$LOG_DIR"
  echo "[INFO] Starting FR Bot web GUI (restart-on-crash loop) -> $LOG_FILE"
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
