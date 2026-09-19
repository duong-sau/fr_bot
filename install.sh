#!/usr/bin/env bash
set -euo pipefail

# FR Bot install script (FastAPI server)
# - Server: uvicorn via systemd (APP_MODULE=Server.App:app) on a real systemd host,
#   or via Tools/wsl_server_ctl.sh's restart-on-crash loop when systemd isn't PID 1
#   (e.g. WSL without `systemd=true` in /etc/wsl.conf) -- auto-detected, see has_systemd().
# - HTTP only, bound to 127.0.0.1 (front it with a reverse proxy for external/HTTPS access)
# - Web GUI (web-ui/, a React dev server on :3000): only installed/started when the host is
#   detected as WSL (see is_wsl()); left disabled on a non-WSL Ubuntu host. Uses the same
#   systemd-vs-nohup mechanism as the server (Tools/wsl_gui_ctl.sh mirrors wsl_server_ctl.sh).

# ---------------- Config ----------------
APP_ROOT="${APP_ROOT:-/home/ubuntu/fr_bot}"
CODE_DIR="${CODE_DIR:-$APP_ROOT/code}"
LOG_DIR="${LOG_DIR:-$APP_ROOT/logs}"
DATA_DIR="${DATA_DIR:-$APP_ROOT/data}"
VENV_DIR="${VENV_DIR:-$APP_ROOT/venv}"
HOST_SETTINGS_DIR="$CODE_DIR/_settings"
APP_MODULE="${APP_MODULE:-Server.App:app}"
APP_PORT="${APP_PORT:-8000}"
SYSTEMD_UNIT="${SYSTEMD_UNIT:-frbot-server.service}"

# Web GUI (web-ui/, a React dev server). Only installed/started when the
# host is detected as WSL (see is_wsl()) -- on a non-WSL Ubuntu host it's
# left disabled, matching how this repo actually gets used (GUI shares the
# WSL dev machine with the server; a bare Linux host just runs the server).
GUI_DIR="${GUI_DIR:-$CODE_DIR/web-ui}"
GUI_PORT="${GUI_PORT:-3000}"
GUI_SYSTEMD_UNIT="${GUI_SYSTEMD_UNIT:-frbot-gui.service}"


# Microservices (optional; skip by default to keep this script focused on the server)
SKIP_MICROSERVICES="${SKIP_MICROSERVICES:-1}"
LOGS_VOLUME="${LOGS_VOLUME:-frbot_logs}"
IMAGE_ADL="${IMAGE_ADL:-adlprocess}"
IMAGE_ASSET="${IMAGE_ASSET:-assetprocess}"
IMAGE_DISCORD="${IMAGE_DISCORD:-discord_shared_image}"
CONTAINER_ADL="${CONTAINER_ADL:-adlcontrol_container}"
CONTAINER_ASSET="${CONTAINER_ASSET:-assetcontrol_container}"
CONTAINER_DISCORD="${CONTAINER_DISCORD:-discord_shared_container}"
GIT_REPO="${GIT_REPO:-https://github.com/duong-sau/fr_bot.git}"
GIT_REF="${GIT_REF:-master}"
# ---------------------------------------

require_ubuntu() {
  if [[ -f /etc/os-release ]]; then
    . /etc/os-release
    if [[ "${ID:-}" != "ubuntu" ]]; then
      echo "[ERROR] Detected: ${NAME:-unknown}. Please run on Ubuntu." >&2
      exit 1
    fi
  fi
}

# True when systemd is actually running as PID 1 (real Ubuntu host, or a WSL
# distro with `[boot] systemd=true` set in /etc/wsl.conf -- "kieu moi"). False
# for a WSL distro without that setting ("kieu cu"), where `systemctl`/D-Bus
# calls fail with "System has not been booted with systemd as init system".
has_systemd() {
  [[ -d /run/systemd/system ]] && command -v systemctl >/dev/null 2>&1
}

is_wsl() {
  [[ -n "${WSL_DISTRO_NAME:-}" ]] || grep -qiE 'microsoft|wsl' /proc/version 2>/dev/null
}

install_git() {
  if ! command -v git >/dev/null 2>&1; then
    echo "[INFO] Installing git..."
    sudo apt-get update -y
    sudo apt-get install -y git
  fi
}

install_rsync() {
  if ! command -v rsync >/dev/null 2>&1; then
    echo "[INFO] Installing rsync..."
    sudo apt-get update -y
    sudo apt-get install -y rsync
  fi
}

install_python() {
  if ! command -v python3 >/dev/null 2>&1; then
    echo "[INFO] Installing Python 3..."
    sudo apt-get update -y
    sudo apt-get install -y python3 python3-venv python3-pip build-essential
  else
    # ensure venv and pip exist
    sudo apt-get update -y
    sudo apt-get install -y python3-venv python3-pip build-essential
  fi
}

install_node() {
  if ! command -v npm >/dev/null 2>&1; then
    echo "[INFO] Installing Node.js/npm (for the web GUI)..."
    sudo apt-get update -y
    sudo apt-get install -y nodejs npm
  fi
}

install_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "[INFO] Installing Docker..."
    sudo apt-get update -y
    sudo apt-get install -y docker.io
    sudo systemctl enable docker
    sudo systemctl start docker
    sudo usermod -aG docker "$USER" || true
  fi
}

ensure_logs_volume() {
  echo "[INFO] Ensuring shared logs volume: $LOGS_VOLUME"
  sudo docker volume create "$LOGS_VOLUME" >/dev/null
}

ensure_dirs() {
  echo "[INFO] Ensuring app dirs at '$APP_ROOT'..."
  sudo mkdir -p "$CODE_DIR" "$LOG_DIR" "$DATA_DIR"
  sudo chown -R "$USER":"$USER" "$APP_ROOT"
}

fetch_code() {
  if [[ -n "$GIT_REPO" ]]; then
    install_git
    echo "[INFO] Fetching code from Git: $GIT_REPO (ref: $GIT_REF) -> $CODE_DIR"
    if [[ -d "$CODE_DIR/.git" ]]; then
      pushd "$CODE_DIR" >/dev/null
      git fetch --all --tags --prune
      git checkout "$GIT_REF"
      # Hard-sync to the remote ref rather than `pull --rebase`: any local diff in
      # CODE_DIR (e.g. a stray `chmod +x` on a script) makes rebase refuse to run,
      # and the previous `|| true` silently left the host on stale code. _settings/
      # and venv/ are untracked (gitignored) so a hard reset never touches them.
      git reset --hard "origin/$GIT_REF"
      popd >/dev/null
    else
      rm -rf "$CODE_DIR" && mkdir -p "$CODE_DIR"
      git clone --depth 1 --branch "$GIT_REF" "$GIT_REPO" "$CODE_DIR"
    fi
  else
    echo "[INFO] GIT_REPO not set. Copying local code (from script's directory) -> $CODE_DIR"
    install_rsync
    local SRC_DIR
    SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
    rsync -a --delete --exclude ".git" --exclude "venv" --exclude "__pycache__" "$SRC_DIR"/ "$CODE_DIR"/
  fi
}

setup_venv_and_deps() {
  install_python
  if [[ ! -d "$VENV_DIR" ]]; then
    echo "[INFO] Creating venv at $VENV_DIR"
    python3 -m venv "$VENV_DIR"
  fi
  source "$VENV_DIR/bin/activate"
  if [[ -f "$CODE_DIR/Server/requirements.txt" ]]; then
    pip install --upgrade pip
    pip install -r "$CODE_DIR/Server/requirements.txt"
  elif [[ -f "$CODE_DIR/requirements.txt" ]]; then
    pip install --upgrade pip
    pip install -r "$CODE_DIR/requirements.txt"
  else
    echo "[WARN] No requirements.txt found; skipping Python deps installation."
  fi
  deactivate || true
}

setup_gui_deps() {
  install_node
  if [[ -d "$GUI_DIR" ]]; then
    echo "[INFO] Installing web GUI dependencies in $GUI_DIR..."
    npm install --prefix "$GUI_DIR"
  else
    echo "[WARN] GUI dir '$GUI_DIR' not found; skipping GUI dependency install."
    return 1
  fi
}

install_systemd_server() {
  echo "[INFO] Installing systemd unit: $SYSTEMD_UNIT"
  UNIT_PATH="/etc/systemd/system/$SYSTEMD_UNIT"

  sudo bash -c "cat > '$UNIT_PATH'" <<EOF
[Unit]
Description=FR Bot FastAPI Server (uvicorn, HTTP, loopback)
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$CODE_DIR
Environment=APP_MODULE=$APP_MODULE
Environment=HOST_SETTINGS_DIR=$HOST_SETTINGS_DIR
Environment=LOG_DIR=$LOG_DIR
Environment=DATA_DIR=$DATA_DIR
ExecStart=$VENV_DIR/bin/uvicorn ${APP_MODULE} --host 127.0.0.1 --port $APP_PORT --log-level info
Restart=always
RestartSec=3
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full

[Install]
WantedBy=multi-user.target
EOF

  sudo systemctl daemon-reload
  sudo systemctl enable "$SYSTEMD_UNIT"
  sudo systemctl restart "$SYSTEMD_UNIT"
  sleep 2
  sudo systemctl --no-pager --full status "$SYSTEMD_UNIT" || true
}

install_systemd_gui() {
  echo "[INFO] Installing systemd unit: $GUI_SYSTEMD_UNIT"
  UNIT_PATH="/etc/systemd/system/$GUI_SYSTEMD_UNIT"
  NPM_BIN="$(command -v npm)"

  sudo bash -c "cat > '$UNIT_PATH'" <<EOF
[Unit]
Description=FR Bot Web GUI (React dev server)
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$GUI_DIR
Environment=PORT=$GUI_PORT
Environment=BROWSER=none
Environment=CI=true
ExecStart=$NPM_BIN start
Restart=always
RestartSec=3
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full

[Install]
WantedBy=multi-user.target
EOF

  sudo systemctl daemon-reload
  sudo systemctl enable "$GUI_SYSTEMD_UNIT"
  sudo systemctl restart "$GUI_SYSTEMD_UNIT"
  sleep 2
  sudo systemctl --no-pager --full status "$GUI_SYSTEMD_UNIT" || true
}

# $@: absolute paths (no "start" suffix) of the wsl_*_ctl.sh scripts that
# need to survive a WSL restart. Chains them into a single /etc/wsl.conf
# [boot] command since wsl.conf only supports one.
configure_wsl_boot_command() {
  local scripts=("$@")
  local inner=""
  local script
  for script in "${scripts[@]}"; do
    if [[ -n "$inner" ]]; then
      inner+=" && "
    fi
    inner+="$script start"
  done
  local boot_cmd="su - $USER -c '$inner'"

  if [[ -f /etc/wsl.conf ]] && grep -qE "wsl_(server|gui)_ctl\.sh" /etc/wsl.conf; then
    echo "[INFO] /etc/wsl.conf already wires up wsl_*_ctl.sh; leaving it as-is."
  elif [[ -f /etc/wsl.conf ]] && grep -q '^\[boot\]' /etc/wsl.conf; then
    echo "[WARN] /etc/wsl.conf already has a [boot] section; add this line to it manually:"
    echo "         command = \"$boot_cmd\""
  else
    echo "[INFO] Adding [boot] command to /etc/wsl.conf so processes restart when WSL boots..."
    sudo bash -c "cat >> /etc/wsl.conf" <<EOF

[boot]
command = "$boot_cmd"
EOF
  fi

  echo "[WARN] WSL2 does not launch automatically when Windows starts. To fully auto-start"
  echo "       on boot, add a Windows Task Scheduler entry (trigger: 'At log on') running:"
  echo "         wsl.exe -d <YourDistroName> true"
  echo "       (list distro names with 'wsl -l -v' from PowerShell)."
}

install_nohup_server() {
  echo "[INFO] No systemd detected -- running the server via Tools/wsl_server_ctl.sh (nohup + restart-on-crash loop) instead."
  chmod +x "$CODE_DIR/Tools/wsl_server_ctl.sh"
  APP_ROOT="$APP_ROOT" CODE_DIR="$CODE_DIR" VENV_DIR="$VENV_DIR" LOG_DIR="$LOG_DIR" \
    APP_MODULE="$APP_MODULE" APP_PORT="$APP_PORT" \
    "$CODE_DIR/Tools/wsl_server_ctl.sh" restart

  if ! is_wsl; then
    echo "[WARN] No systemd and not detected as WSL -- the server is running now but won't"
    echo "       restart on reboot. Wire '$CODE_DIR/Tools/wsl_server_ctl.sh start' into your"
    echo "       init system (cron @reboot, rc.local, etc.) to persist it."
  fi
}

install_nohup_gui() {
  echo "[INFO] No systemd detected -- running the GUI via Tools/wsl_gui_ctl.sh (nohup + restart-on-crash loop) instead."
  chmod +x "$CODE_DIR/Tools/wsl_gui_ctl.sh"
  APP_ROOT="$APP_ROOT" CODE_DIR="$CODE_DIR" GUI_DIR="$GUI_DIR" LOG_DIR="$LOG_DIR" GUI_PORT="$GUI_PORT" \
    "$CODE_DIR/Tools/wsl_gui_ctl.sh" restart
}

build_images_microservices() {
  install_docker
  ensure_logs_volume
  echo "[INFO] Building microservice images..."
  sudo docker build -f "$CODE_DIR/MainProcess/ADLControl/Dockerfile" -t "$IMAGE_ADL" "$CODE_DIR"
  sudo docker build -f "$CODE_DIR/MainProcess/AssetControl/Dockerfile" -t "$IMAGE_ASSET" "$CODE_DIR"
  sudo docker build -f "$CODE_DIR/Notification/Dockerfile" -t "$IMAGE_DISCORD" "$CODE_DIR"
}

recreate_containers_microservices() {
  echo "[INFO] Removing old microservice containers (if exist)"
  sudo docker rm -f "$CONTAINER_ADL" "$CONTAINER_ASSET" "$CONTAINER_DISCORD" 2>/dev/null || true

  echo "[INFO] Creating microservice containers (ADL/Asset stopped by default, Discord started)"
  sudo docker create --name "$CONTAINER_ADL" \
    -v "$LOGS_VOLUME":/home/ubuntu/fr_bot/logs \
    -v "$LOGS_VOLUME":/app/logs \
    "$IMAGE_ADL"

  sudo docker create --name "$CONTAINER_ASSET" \
    -v "$LOGS_VOLUME":/home/ubuntu/fr_bot/logs \
    -v "$LOGS_VOLUME":/app/logs \
    "$IMAGE_ASSET"

  sudo docker run -d --name "$CONTAINER_DISCORD" \
    -v "$LOGS_VOLUME":/home/ubuntu/fr_bot/logs \
    -v "$LOGS_VOLUME":/app/logs \
    -v "$HOST_SETTINGS_DIR":/home/ubuntu/fr_bot/code/_settings \
    "$IMAGE_DISCORD"
}

post_checks() {
  echo "[INFO] Server listening on :$APP_PORT"
  if command -v curl >/dev/null 2>&1; then
    sleep 2
    echo "[INFO] Health check (HTTP):"
    curl -sf "http://127.0.0.1:${APP_PORT}/bot1api/microservices" || true
  fi
}

main() {
  echo "[INFO] One-click install (systemd server, HTTP only)"
  require_ubuntu
  ensure_dirs
  fetch_code
  setup_venv_and_deps

  if [[ ! -f "$HOST_SETTINGS_DIR/config.txt" ]]; then
    echo "[INFO] No settings found at '$HOST_SETTINGS_DIR' -- scaffolding defaults (bitget/gate) via manage_config.py"
    "$VENV_DIR/bin/python" "$CODE_DIR/Tools/manage_config.py" init
    echo "[WARN] exchange_key.json was created empty. Set real API keys before starting ADL/Asset control: '$CODE_DIR/config_menu.sh' or 'python Tools/manage_keys.py set <exchange> --local'."
  fi

  local gui_enabled=0
  if is_wsl; then
    echo "[INFO] WSL detected -- installing/starting the web GUI (web-ui/) alongside the server..."
    if setup_gui_deps; then
      gui_enabled=1
    fi
  else
    echo "[INFO] Not running under WSL -- leaving the web GUI (web-ui/) disabled."
  fi

  if has_systemd; then
    install_systemd_server
    if [[ "$gui_enabled" -eq 1 ]]; then
      install_systemd_gui
    fi
  else
    install_nohup_server
    if [[ "$gui_enabled" -eq 1 ]]; then
      install_nohup_gui
    fi
    if is_wsl; then
      if [[ "$gui_enabled" -eq 1 ]]; then
        configure_wsl_boot_command "$CODE_DIR/Tools/wsl_server_ctl.sh" "$CODE_DIR/Tools/wsl_gui_ctl.sh"
      else
        configure_wsl_boot_command "$CODE_DIR/Tools/wsl_server_ctl.sh"
      fi
    else
      echo "[WARN] No systemd and not detected as WSL -- the server is running now but won't"
      echo "       restart on reboot. Wire '$CODE_DIR/Tools/wsl_server_ctl.sh start' into your"
      echo "       init system (cron @reboot, rc.local, etc.) to persist it."
    fi
  fi

  if [[ "$SKIP_MICROSERVICES" -eq 0 ]]; then
    build_images_microservices
    recreate_containers_microservices
  else
    echo "[INFO] Skipping microservices build/run (SKIP_MICROSERVICES=$SKIP_MICROSERVICES)"
  fi

  post_checks
  echo "[DONE] Server: http://127.0.0.1:$APP_PORT (loopback only)  Code: '$CODE_DIR'  Logs Volume: '$LOGS_VOLUME'  Data: '$DATA_DIR'"
  if [[ "$gui_enabled" -eq 1 ]]; then
    echo "[DONE] GUI: http://127.0.0.1:$GUI_PORT (WSL detected)"
  fi
}

main "$@"
