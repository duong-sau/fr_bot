#!/usr/bin/env bash
# Acquire a Let's Encrypt certificate (trusted CA) and wire it to the FR Bot service.
# - Ubuntu with sudo privileges required
# - Uses certbot (snap) with standalone HTTP-01 challenge (needs port 80)
#
# Usage:
#   sudo bash setup_letsencrypt.sh -d your.domain.com -m you@email.com [-p 8000]
#
# Steps performed:
# 1) Install certbot if missing
# 2) Stop frbot-server.service temporarily (to free port 80 if needed)
# 3) Obtain/renew certificate for the domain (standalone)
# 4) Symlink /etc/ssl/frbot/cert.pem and key.pem to the issued certs
# 5) Set SSL_CERTFILE/SSL_KEYFILE env and reinstall/restart the systemd service (HTTPS)
# 6) Install a deploy hook to restart the service automatically on renewal

set -euo pipefail

DOMAIN=""
EMAIL=""
APP_PORT="8000" # can be overridden with -p
SYSTEMD_UNIT="frbot-server.service"
SSL_DIR="/etc/ssl/frbot"

usage() {
  echo "Usage: sudo bash $0 -d <domain> -m <email> [-p 8000]" 1>&2
  exit 1
}

while getopts ":d:m:p:" opt; do
  case "$opt" in
    d) DOMAIN="$OPTARG" ;;
    m) EMAIL="$OPTARG" ;;
    p) APP_PORT="$OPTARG" ;;
    *) usage ;;
  esac
done

[[ -z "$DOMAIN" || -z "$EMAIL" ]] && usage

if [[ $EUID -ne 0 ]]; then
  echo "[INFO] Re-running with sudo..."
  exec sudo -E bash "$0" -d "$DOMAIN" -m "$EMAIL" -p "$APP_PORT"
fi

install_certbot() {
  if command -v certbot >/dev/null 2>&1; then
    echo "[INFO] certbot found."
    return
  fi
  echo "[INFO] Installing certbot via snap..."
  if ! command -v snap >/dev/null 2>&1; then
    apt-get update -y
    apt-get install -y snapd
  fi
  snap install core || true
  snap refresh core || true
  snap install --classic certbot
  ln -sf /snap/bin/certbot /usr/bin/certbot
}

# 1) Install certbot
install_certbot

# 2) Stop service to free ports (especially 80)
if systemctl is-active --quiet "$SYSTEMD_UNIT"; then
  echo "[INFO] Stopping $SYSTEMD_UNIT to free port 80 for validation..."
  systemctl stop "$SYSTEMD_UNIT" || true
fi

# 3) Obtain/renew certificate via standalone HTTP-01
# Make sure your domain DNS A/AAAA records point to this server
echo "[INFO] Requesting/renewing Let's Encrypt certificate for $DOMAIN"
certbot certonly \
  --standalone \
  --preferred-challenges http \
  -d "$DOMAIN" \
  -m "$EMAIL" \
  --agree-tos \
  --non-interactive \
  --keep-until-expiring

LIVE_DIR="/etc/letsencrypt/live/$DOMAIN"
CERT_SRC="$LIVE_DIR/fullchain.pem"
KEY_SRC="$LIVE_DIR/privkey.pem"

if [[ ! -f "$CERT_SRC" || ! -f "$KEY_SRC" ]]; then
  echo "[ERROR] Missing certificate files from certbot: $CERT_SRC / $KEY_SRC" 1>&2
  exit 1
fi

# 4) Symlink to /etc/ssl/frbot
mkdir -p "$SSL_DIR"
ln -sf "$CERT_SRC" "$SSL_DIR/cert.pem"
ln -sf "$KEY_SRC" "$SSL_DIR/key.pem"
chmod 644 "$SSL_DIR/cert.pem"
chmod 600 "$SSL_DIR/key.pem"

echo "[INFO] Symlinked certs to $SSL_DIR (cert.pem, key.pem)"

# 5) Ensure the systemd service uses these files and HTTPS port
export SSL_CERTFILE="$SSL_DIR/cert.pem"
export SSL_KEYFILE="$SSL_DIR/key.pem"
export APP_PORT="$APP_PORT"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [[ -f "$SCRIPT_DIR/install.sh" ]]; then
  echo "[INFO] Reinstalling systemd service with HTTPS using install.sh"
  bash "$SCRIPT_DIR/install.sh"
else
  echo "[WARN] install.sh not found at $SCRIPT_DIR. Attempting to restart service only."
  systemctl daemon-reload || true
fi

# 6) Create deploy hook to restart service on renewal
HOOK_PATH="/etc/letsencrypt/renewal-hooks/deploy/restart-frbot.sh"
mkdir -p "$(dirname "$HOOK_PATH")"
cat > "$HOOK_PATH" <<EOF
#!/usr/bin/env bash
systemctl restart $SYSTEMD_UNIT || true
EOF
chmod +x "$HOOK_PATH"

echo "[INFO] Installed deploy hook: $HOOK_PATH"

echo "[DONE] Let's Encrypt certificate installed for $DOMAIN and service restarted over HTTPS on port $APP_PORT."

