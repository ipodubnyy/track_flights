#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/track_flights"

echo "=== Deploying Flight Price Tracker ==="

# Install system deps
sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-venv python3-pip nginx

# Create app directory
sudo mkdir -p "$APP_DIR"
sudo chown ubuntu:ubuntu "$APP_DIR"

# Sync code
rsync -a --exclude='.git' --exclude='__pycache__' --exclude='.env' --exclude='*.db' \
    /tmp/track_flights_deploy/ "$APP_DIR/"

# Create virtualenv and install deps
if [ ! -d "$APP_DIR/venv" ]; then
    python3 -m venv "$APP_DIR/venv"
fi
"$APP_DIR/venv/bin/pip" install -q --upgrade pip
"$APP_DIR/venv/bin/pip" install -q -r "$APP_DIR/requirements.txt"

# Copy .env if not present
if [ ! -f "$APP_DIR/.env" ]; then
    cp "$APP_DIR/.env.example" "$APP_DIR/.env"
    echo "WARNING: .env copied from example. Edit /opt/track_flights/.env with real credentials."
fi

# Setup nginx
sudo cp "$APP_DIR/deploy/nginx.conf" /etc/nginx/sites-available/track_flights
sudo ln -sf /etc/nginx/sites-available/track_flights /etc/nginx/sites-enabled/track_flights
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx

# Setup systemd service
sudo cp "$APP_DIR/deploy/track_flights.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable track_flights
sudo systemctl restart track_flights

echo "=== Deployment complete ==="
echo "App is running at http://$(curl -s ifconfig.me 2>/dev/null || echo 'YOUR_IP'):80"
echo ""
echo "Next steps:"
echo "  1. Edit /opt/track_flights/.env with your API keys"
echo "  2. sudo systemctl restart track_flights"
