#!/usr/bin/env bash
set -euo pipefail

# Rebuild all microservice Docker images and recreate containers
# - Images: adlprocess, assetprocess, discord_shared_image
# - Containers: adlcontrol_container, assetcontrol_container, discord_shared_container
# - Code root (host): /home/ubuntu/fr_bot/code
# - Mounts shared logs volume and _settings into containers

# -------- Config --------
APP_ROOT="${APP_ROOT:-/home/ubuntu/fr_bot}"
CODE_DIR="${CODE_DIR:-$APP_ROOT/code}"
HOST_SETTINGS_DIR="${HOST_SETTINGS_DIR:-$CODE_DIR/_settings}"

IMAGE_ADL="${IMAGE_ADL:-adlprocess}"
IMAGE_ASSET="${IMAGE_ASSET:-assetprocess}"
IMAGE_DISCORD="${IMAGE_DISCORD:-discord_shared_image}"

CONTAINER_ADL="${CONTAINER_ADL:-adlcontrol_container}"
CONTAINER_ASSET="${CONTAINER_ASSET:-assetcontrol_container}"
CONTAINER_DISCORD="${CONTAINER_DISCORD:-discord_shared_container}"

# Shared logs volume (same as install.sh)
LOGS_VOLUME="${LOGS_VOLUME:-frbot_logs}"
# ------------------------

require_ubuntu() {
  if [[ -f /etc/os-release ]]; then
    . /etc/os-release
    if [[ "${ID:-}" != "ubuntu" ]]; then
      echo "[ERROR] Detected: ${NAME:-unknown}. Please run on Ubuntu." >&2
      exit 1
    fi
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

ensure_logs_volume() {
  echo "[INFO] Ensuring shared logs volume: $LOGS_VOLUME"
  sudo docker volume create "$LOGS_VOLUME" >/dev/null
}

validate_paths() {
  [[ -d "$CODE_DIR" ]] || { echo "[ERROR] CODE_DIR not found: $CODE_DIR" >&2; exit 1; }
  [[ -d "$HOST_SETTINGS_DIR" ]] || { echo "[ERROR] HOST_SETTINGS_DIR not found: $HOST_SETTINGS_DIR" >&2; exit 1; }
}

build_images() {
  echo "[INFO] Rebuilding images from $CODE_DIR"
  sudo docker build -f "$CODE_DIR/MainProcess/ADLControl/Dockerfile" -t "$IMAGE_ADL" "$CODE_DIR"
  sudo docker build -f "$CODE_DIR/MainProcess/AssetControl/Dockerfile" -t "$IMAGE_ASSET" "$CODE_DIR"
  sudo docker build -f "$CODE_DIR/Notification/Dockerfile" -t "$IMAGE_DISCORD" "$CODE_DIR"
}

recreate_containers() {
  echo "[INFO] Removing old containers (ignore errors if not exist)"
  sudo docker rm -f "$CONTAINER_ADL" "$CONTAINER_ASSET" "$CONTAINER_DISCORD" 2>/dev/null || true

  echo "[INFO] Recreating containers"
  sudo docker create --name "$CONTAINER_ADL" \
    -v "$LOGS_VOLUME":/home/ubuntu/fr_bot/logs \
    -v "$LOGS_VOLUME":/app/logs \
    -v "$HOST_SETTINGS_DIR":/home/ubuntu/fr_bot/code/_settings \
    "$IMAGE_ADL"

  sudo docker create --name "$CONTAINER_ASSET" \
    -v "$LOGS_VOLUME":/home/ubuntu/fr_bot/logs \
    -v "$LOGS_VOLUME":/app/logs \
    -v "$HOST_SETTINGS_DIR":/home/ubuntu/fr_bot/code/_settings \
    "$IMAGE_ASSET"

  sudo docker run -d --name "$CONTAINER_DISCORD" \
    --restart unless-stopped \
    -v "$LOGS_VOLUME":/home/ubuntu/fr_bot/logs \
    -v "$LOGS_VOLUME":/app/logs \
    -v "$HOST_SETTINGS_DIR":/home/ubuntu/fr_bot/code/_settings \
    "$IMAGE_DISCORD"
}

post_checks() {
  echo "[INFO] Container status:"
  sudo docker ps -a --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"
  echo "[INFO] Docker volumes:"
  sudo docker volume ls | grep -E "(VOLUME|$LOGS_VOLUME)" || true
}

main() {
  echo "[INFO] Rebuild all microservice docker images & containers"
  require_ubuntu
  install_docker
  ensure_logs_volume
  validate_paths
  build_images
  recreate_containers
  post_checks
  echo "[DONE] Rebuild completed. Containers are using shared logs volume: $LOGS_VOLUME"
}

main "$@"
