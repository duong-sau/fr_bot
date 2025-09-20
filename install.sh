#!/usr/bin/env bash
set -euo pipefail

# FR Bot install script (server via systemd, microservices via Docker)
# - Code location (host): /home/ubuntu/fr_bot/code
# - Data/logs (host):     /home/ubuntu/fr_bot/{data,logs}
# - Server: uvicorn via systemd (APP_MODULE=Server.App:app)
# - ADL/Asset/Discord: Docker containers

# -------- Config --------
APP_ROOT="/home/ubuntu/fr_bot"
CODE_DIR="$APP_ROOT/code"
LOG_DIR="$APP_ROOT/logs"
DATA_DIR="$APP_ROOT/data"
VENV_DIR="$APP_ROOT/venv"
GIT_REPO="${GIT_REPO:-}"
GIT_REF="${GIT_REF:-main}"
IMAGE_ADL="${IMAGE_ADL:-adlprocess}"
IMAGE_ASSET="${IMAGE_ASSET:-assetprocess}"
IMAGE_DISCORD="${IMAGE_DISCORD:-discord_shared_image}"
CONTAINER_ADL="${CONTAINER_ADL:-adlcontrol_container}"
CONTAINER_ASSET="${CONTAINER_ASSET:-assetcontrol_container}"
CONTAINER_DISCORD="${CONTAINER_DISCORD:-discord_shared_container}"
HOST_SETTINGS_DIR="$CODE_DIR/_settings"
APP_MODULE="${APP_MODULE:-Server.App:app}"
APP_PORT="${APP_PORT:-8000}"
SYSTEMD_UNIT="frbot-server.service"
# ------------------------

require_ubuntu() {
  if [[ -f /etc/os-release ]]; then
    . /etc/os-release
    if [[ "${ID:-}" != "ubuntu" ]]; then
      echo "[ERROR] Detected: ${NAME:-unknown}. Please run on Ubuntu-based AWS AMI." >&2
      exit 1
    fi
  fi
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

install_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "[INFO] Installing Docker..."
    sudo apt-get update -y
    sudo apt-get install -y ca-certificates curl gnupg lsb-release
    sudo apt-get install -y docker.io docker-compose-plugin
    sudo systemctl enable docker
    sudo systemctl start docker
    sudo usermod -aG docker "$USER" || true
  fi
}

install_python() {
  echo "[INFO] Ensuring Python toolchain..."
  sudo apt-get update -y
  sudo apt-get install -y python3 python3-venv python3-pip build-essential
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
      git pull --rebase origin "$GIT_REF" || true
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

install_systemd_server() {
  echo "[INFO] Installing systemd unit: $SYSTEMD_UNIT"
  UNIT_PATH="/etc/systemd/system/$SYSTEMD_UNIT"
  sudo bash -c "cat > '$UNIT_PATH'" <<EOF
[Unit]
Description=FR Bot FastAPI Server (uvicorn)
Wants=network-online.target
After=network-online.target docker.service

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$CODE_DIR
Environment=APP_MODULE=$APP_MODULE
Environment=HOST_SETTINGS_DIR=$HOST_SETTINGS_DIR
Environment=LOG_DIR=$LOG_DIR
Environment=DATA_DIR=$DATA_DIR
ExecStart=$VENV_DIR/bin/uvicorn \
  \${APP_MODULE} --host 0.0.0.0 --port $APP_PORT --log-level info
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

build_images_microservices() {
  install_docker
  echo "[INFO] Building microservice images (server image disabled)..."
  sudo docker build -f "$CODE_DIR/MainProcess/ADLControl/Dockerfile" -t "$IMAGE_ADL" "$CODE_DIR"
  sudo docker build -f "$CODE_DIR/MainProcess/AssetControl/Dockerfile" -t "$IMAGE_ASSET" "$CODE_DIR"
  sudo docker build -f "$CODE_DIR/Notification/Dockerfile" -t "$IMAGE_DISCORD" "$CODE_DIR"
}

recreate_containers_microservices() {
  echo "[INFO] Removing old microservice containers (if exist)"
  sudo docker rm -f "$CONTAINER_ADL" "$CONTAINER_ASSET" "$CONTAINER_DISCORD" 2>/dev/null || true

  echo "[INFO] Creating microservice containers (ADL/Asset stopped by default, Discord started)"
  sudo docker create --name "$CONTAINER_ADL" \
    -v "$LOG_DIR":/home/ubuntu/fr_bot/logs \
    -v "$HOST_SETTINGS_DIR":/home/ubuntu/fr_bot/code/_settings \
    "$IMAGE_ADL"

  sudo docker create --name "$CONTAINER_ASSET" \
    -v "$LOG_DIR":/home/ubuntu/fr_bot/logs \
    -v "$HOST_SETTINGS_DIR":/home/ubuntu/fr_bot/code/_settings \
    "$IMAGE_ASSET"

  sudo docker run -d --name "$CONTAINER_DISCORD" \
    --restart unless-stopped \
    -v "$LOG_DIR":/home/ubuntu/fr_bot/logs \
    -v "$HOST_SETTINGS_DIR":/home/ubuntu/fr_bot/code/_settings \
    "$IMAGE_DISCORD"
}

post_checks() {
  echo "[INFO] systemd service listening on :$APP_PORT"
  if command -v curl >/dev/null 2>&1; then
    sleep 2
    echo "[INFO] Health check (if implemented):"
    curl -sf "http://127.0.0.1:${APP_PORT}/bot1api/microservices" || true
    echo
  fi
  echo "[INFO] Docker containers:"
  sudo docker ps -a --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"
}

main() {
  echo "[INFO] One-click install (systemd server, docker microservices)"
  require_ubuntu
  ensure_dirs
  fetch_code
  if [[ ! -f "$HOST_SETTINGS_DIR/config.txt" ]]; then
    echo "[ERROR] Missing settings file: '$HOST_SETTINGS_DIR/config.txt'" >&2
    exit 1
  fi
  setup_venv_and_deps
  install_systemd_server
  build_images_microservices
  recreate_containers_microservices
  post_checks
  echo "[DONE] Server: http://<server-ip>:$APP_PORT  Code: '$CODE_DIR'  Logs: '$LOG_DIR'  Data: '$DATA_DIR'"
}

main "$@"

