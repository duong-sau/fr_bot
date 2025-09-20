#!/usr/bin/env bash
set -euo pipefail

# One-click deploy FR Bot on an AWS Ubuntu instance
# - Optionally fetch code from Git (set GIT_REPO and GIT_REF)
# - Installs Docker & dependencies
# - Builds all images (Server, ADL, Asset, Discord)
# - Creates required volumes
# - Creates containers with proper mounts
# - Starts FastAPI server + Discord relay (ADL/Asset left for control via API/UI)

# -------- Config (can be overridden via ENV) --------
DETECTED_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT_ROOT="${PROJECT_ROOT:-$DETECTED_ROOT}"

# Git options (optional). If GIT_REPO is set, code will be cloned/updated into APP_DIR
GIT_REPO="${GIT_REPO:-}"
GIT_REF="${GIT_REF:-main}"
APP_DIR="${APP_DIR:-/opt/frbot}"

IMAGE_SERVER="${IMAGE_SERVER:-frbot_server_image}"
IMAGE_ADL="${IMAGE_ADL:-adlprocess}"
IMAGE_ASSET="${IMAGE_ASSET:-assetprocess}"
IMAGE_DISCORD="${IMAGE_DISCORD:-discord_shared_image}"

CONTAINER_SERVER="${CONTAINER_SERVER:-frbot_server}"
CONTAINER_ADL="${CONTAINER_ADL:-adlcontrol_container}"
CONTAINER_ASSET="${CONTAINER_ASSET:-assetcontrol_container}"
CONTAINER_DISCORD="${CONTAINER_DISCORD:-discord_shared_container}"

LOG_VOLUME="${LOG_VOLUME:-frbot_logs}"
HOST_SETTINGS_DIR="${HOST_SETTINGS_DIR:-$PROJECT_ROOT/_settings}"
# ---------------------------------------------------

require_ubuntu() {
  # Detect via /etc/os-release to avoid dependency on lsb_release
  if [[ -f /etc/os-release ]]; then
    . /etc/os-release
    if [[ "${ID:-}" != "ubuntu" ]]; then
      echo "[ERROR] Detected: ${NAME:-unknown}. Please run on Ubuntu-based AWS AMI." >&2
      exit 1
    fi
  else
    echo "[WARN] /etc/os-release not found; proceeding, but this script expects Ubuntu." >&2
  fi
}

install_git() {
  if ! command -v git >/dev/null 2>&1; then
    echo "[INFO] Installing git..."
    sudo apt-get update -y
    sudo apt-get install -y git
  fi
}

install_docker() {
  echo "[INFO] Installing Docker..."
  sudo apt-get update -y
  sudo apt-get install -y ca-certificates curl gnupg lsb-release
  # Install Docker engine (from Ubuntu repo for simplicity)
  sudo apt-get install -y docker.io docker-compose-plugin
  sudo systemctl enable docker
  sudo systemctl start docker
  # Allow current user to use docker (may require re-login to take effect)
  sudo usermod -aG docker "$USER" || true
  echo "[INFO] Docker installed. Version:"
  sudo docker --version || true
}

ensure_prereqs() {
  require_ubuntu
  if ! command -v docker >/dev/null 2>&1; then
    install_docker
  else
    echo "[INFO] Docker already installed."
  fi
}

fetch_code() {
  if [[ -n "$GIT_REPO" ]]; then
    install_git
    echo "[INFO] Fetching code from Git: $GIT_REPO (ref: $GIT_REF)"
    sudo mkdir -p "$APP_DIR"
    sudo chown -R "$USER":"$USER" "$APP_DIR"
    if [[ -d "$APP_DIR/.git" ]]; then
      echo "[INFO] Existing repo found. Updating..."
      pushd "$APP_DIR" >/dev/null
      git fetch --all --tags --prune
      git checkout "$GIT_REF"
      git pull --rebase origin "$GIT_REF" || true
      popd >/dev/null
    else
      git clone --depth 1 --branch "$GIT_REF" "$GIT_REPO" "$APP_DIR"
    fi
    PROJECT_ROOT="$APP_DIR"
    HOST_SETTINGS_DIR="$PROJECT_ROOT/_settings"
  else
    echo "[INFO] GIT_REPO not set. Using existing code at PROJECT_ROOT=$PROJECT_ROOT"
  fi
}

build_images() {
  echo "[INFO] Creating log volume (if missing): $LOG_VOLUME"
  sudo docker volume create "$LOG_VOLUME" >/dev/null 2>&1 || true

  echo "[INFO] Building images..."
  # Build server image
  sudo docker build -f "$PROJECT_ROOT/Server/Dockerfile" -t "$IMAGE_SERVER" "$PROJECT_ROOT"
  # Build microservices
  sudo docker build -f "$PROJECT_ROOT/MainProcess/ADLControl/Dockerfile" -t "$IMAGE_ADL" "$PROJECT_ROOT"
  sudo docker build -f "$PROJECT_ROOT/MainProcess/AssetControl/Dockerfile" -t "$IMAGE_ASSET" "$PROJECT_ROOT"
  sudo docker build -f "$PROJECT_ROOT/Notification/DiscordDockerfile" -t "$IMAGE_DISCORD" "$PROJECT_ROOT"
}

recreate_containers() {
  echo "[INFO] Removing old containers (if exist)"
  sudo docker rm -f "$CONTAINER_SERVER" "$CONTAINER_ADL" "$CONTAINER_ASSET" "$CONTAINER_DISCORD" 2>/dev/null || true

  echo "[INFO] Creating containers with proper mounts"
  # Server: needs docker.sock to manage other containers; mount logs + settings
  sudo docker run -d --name "$CONTAINER_SERVER" \
    --restart unless-stopped \
    -p 8000:8000 \
    -v "$LOG_VOLUME":/app/logs \
    -v "$HOST_SETTINGS_DIR":/app/code/_settings \
    -v /var/run/docker.sock:/var/run/docker.sock \
    "$IMAGE_SERVER"

  # ADL & Asset: pre-create (do not start), so Server can manage start/stop without recreating
  sudo docker create --name "$CONTAINER_ADL" \
    -v "$LOG_VOLUME":/app/logs \
    -v "$HOST_SETTINGS_DIR":/app/code/_settings \
    "$IMAGE_ADL"

  sudo docker create --name "$CONTAINER_ASSET" \
    -v "$LOG_VOLUME":/app/logs \
    -v "$HOST_SETTINGS_DIR":/app/code/_settings \
    "$IMAGE_ASSET"

  # Discord: start immediately so it can forward logs
  sudo docker run -d --name "$CONTAINER_DISCORD" \
    --restart unless-stopped \
    -v "$LOG_VOLUME":/app/logs \
    -v "$HOST_SETTINGS_DIR":/app/code/_settings \
    "$IMAGE_DISCORD"
}

post_checks() {
  echo "[INFO] Listing containers:"
  sudo docker ps -a --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"

  echo "[INFO] Hitting FastAPI health (microservices list):"
  sleep 2
  if command -v curl >/dev/null 2>&1; then
    curl -sf http://127.0.0.1:8000/bot1api/microservices || true
    echo
  else
    echo "[WARN] curl not found; skip health check"
  fi

  echo "[INFO] Tail shared log (if exists):"
  sudo docker run --rm -v "$LOG_VOLUME":/data alpine sh -c "tail -n 50 /data/shared.log || true" || true
}

main() {
  echo "[INFO] Starting FR Bot one-click deploy"
  ensure_prereqs
  fetch_code
  echo "[INFO] Using PROJECT_ROOT: $PROJECT_ROOT"
  if [[ ! -f "$HOST_SETTINGS_DIR/config.txt" ]]; then
    echo "[ERROR] Missing settings file: $HOST_SETTINGS_DIR/config.txt" >&2
    echo "[HINT] Ensure your repo has _settings/config.txt or set HOST_SETTINGS_DIR to a valid path." >&2
    exit 1
  fi
  build_images
  recreate_containers
  post_checks
  echo "[DONE] Deployment completed. FastAPI: http://<server-ip>:8000"
}

main "$@"
