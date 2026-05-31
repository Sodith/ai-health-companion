#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  scripts/deploy.sh
#  One-shot EC2 deployment script for AI Health Companion
#
#  Run this script on a FRESH Ubuntu 22.04 / 24.04 EC2 instance as the
#  default user (ubuntu).  It will:
#    1. Update the system
#    2. Install Docker Engine + Docker Compose plugin
#    3. Clone the repository  (or pull latest if already cloned)
#    4. Prompt for / verify the .env file
#    5. Build images and start all services in detached mode
#
#  Usage (from your local machine via SSH):
#    scp -i your-key.pem scripts/deploy.sh ubuntu@<EC2_PUBLIC_IP>:~/
#    ssh -i your-key.pem ubuntu@<EC2_PUBLIC_IP> "bash ~/deploy.sh"
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/<YOUR_GITHUB_USERNAME>/ai-health-companion.git}"
APP_DIR="${APP_DIR:-/home/ubuntu/ai-health-companion}"
COMPOSE_CMD="docker compose"

# ── 1. System update ──────────────────────────────────────────────────────────
echo "==> [1/5] Updating system packages..."
sudo apt-get update -y
sudo apt-get upgrade -y
sudo apt-get install -y curl git ca-certificates gnupg lsb-release

# ── 2. Install Docker ─────────────────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
  echo "==> [2/5] Installing Docker Engine..."
  # Official Docker install script
  curl -fsSL https://get.docker.com | sudo bash
  sudo usermod -aG docker "$USER"
  newgrp docker <<INNEREOF
  echo "Docker group applied."
INNEREOF
else
  echo "==> [2/5] Docker already installed: $(docker --version)"
fi

# Ensure Docker Compose plugin is available
if ! docker compose version &>/dev/null; then
  echo "     Installing Docker Compose plugin..."
  sudo apt-get install -y docker-compose-plugin
fi

# ── 3. Clone or pull repo ─────────────────────────────────────────────────────
echo "==> [3/5] Fetching repository..."
if [[ -d "$APP_DIR/.git" ]]; then
  cd "$APP_DIR"
  git pull origin main
else
  git clone "$REPO_URL" "$APP_DIR"
  cd "$APP_DIR"
fi

# ── 4. Environment file ───────────────────────────────────────────────────────
echo "==> [4/5] Checking .env file..."
if [[ ! -f "${APP_DIR}/.env" ]]; then
  echo ""
  echo "  ┌─────────────────────────────────────────────────────────────────┐"
  echo "  │  .env file not found!                                           │"
  echo "  │                                                                 │"
  echo "  │  Copy .env.production.example to .env and fill in all values:  │"
  echo "  │    cp .env.production.example .env                              │"
  echo "  │    nano .env                                                    │"
  echo "  │                                                                 │"
  echo "  │  Then re-run this script.                                       │"
  echo "  └─────────────────────────────────────────────────────────────────┘"
  echo ""
  exit 1
fi

# Validate critical secrets are not placeholder values
for VAR in MYSQL_ROOT_PASSWORD MYSQL_PASSWORD JWT_SECRET_KEY GEMINI_API_KEY; do
  VAL=$(grep "^${VAR}=" "${APP_DIR}/.env" | cut -d'=' -f2-)
  if [[ -z "$VAL" || "$VAL" == *"CHANGE_ME"* ]]; then
    echo "[ERROR] ${VAR} is not set or still contains the placeholder value."
    echo "        Edit ${APP_DIR}/.env and set a real value before deploying."
    exit 1
  fi
done

# ── 5. Build & start ──────────────────────────────────────────────────────────
echo "==> [5/5] Building images and starting services..."
cd "$APP_DIR"
$COMPOSE_CMD -f docker-compose.yml -f docker-compose.prod.yml pull --ignore-pull-failures || true
$COMPOSE_CMD -f docker-compose.yml -f docker-compose.prod.yml build --no-cache
$COMPOSE_CMD -f docker-compose.yml -f docker-compose.prod.yml up -d

echo ""
echo "  ✅  Deployment complete!"
echo "  App is available at:  http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo '<EC2_PUBLIC_IP>')"
echo ""
echo "  Useful commands:"
echo "    docker compose ps                      # service status"
echo "    docker compose logs -f backend         # backend logs"
echo "    docker compose logs -f frontend        # nginx logs"
echo "    ./scripts/backup.sh                    # manual DB backup"

