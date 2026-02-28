#!/bin/bash
# MyHealthTeam Chatbot Deployment Script
# Run this script to deploy or update the chatbot on VPS2

set -e

echo "=========================================="
echo "MyHealthTeam Chatbot Deployment Script"
echo "=========================================="

# Configuration
REPO_URL="git@github.com:myhealthteam/chatbot.git"  # Update with actual repo
DEPLOY_DIR="/var/www/myhealthteam-chatbot"
SERVICE_NAME="myhealthteam-chatbot"
TEST_DB_SOURCE="/home/ubuntu/myhealthteam/dev/production_backup_for_testing.db"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   log_error "This script should not be run as root. Use sudo instead."
   exit 1
fi

# Step 1: Clone or update repository
log_info "Setting up deployment directory..."
if [ -d "$DEPLOY_DIR" ]; then
    log_info "Updating existing repository..."
    cd "$DEPLOY_DIR"
    sudo git pull origin main
else
    log_info "Cloning repository..."
    sudo mkdir -p "$DEPLOY_DIR"
    sudo git clone "$REPO_URL" "$DEPLOY_DIR"
    cd "$DEPLOY_DIR"
fi

# Step 2: Create virtual environment
log_info "Setting up Python virtual environment..."
if [ ! -d "$DEPLOY_DIR/venv" ]; then
    sudo python3 -m venv "$DEPLOY_DIR/venv"
fi

# Step 3: Install dependencies
log_info "Installing Python dependencies..."
sudo "$DEPLOY_DIR/venv/bin/pip" install -r requirements.txt

# Step 4: Copy test database
log_info "Copying test database..."
if [ -f "$TEST_DB_SOURCE" ]; then
    sudo cp "$TEST_DB_SOURCE" "$DEPLOY_DIR/production_backup_for_testing.db"
    sudo chown www-data:www-data "$DEPLOY_DIR/production_backup_for_testing.db"
    log_info "Test database copied successfully"
else
    log_warn "Test database not found at $TEST_DB_SOURCE"
    log_warn "You'll need to copy it manually"
fi

# Step 5: Configure environment
log_info "Setting up environment configuration..."
if [ ! -f "$DEPLOY_DIR/.env" ]; then
    sudo cp "$DEPLOY_DIR/.env.example" "$DEPLOY_DIR/.env"
    log_warn "Environment file created from .env.example"
    log_warn "Please edit .env with your configuration"
fi

# Step 6: Set permissions
log_info "Setting file permissions..."
sudo chown -R www-data:www-data "$DEPLOY_DIR"
sudo chmod -R 755 "$DEPLOY_DIR"
sudo chmod 640 "$DEPLOY_DIR/.env"

# Step 7: Create log directory
log_info "Creating log directory..."
sudo mkdir -p /var/log/myhealthteam-chatbot
sudo chown www-data:www-data /var/log/myhealthteam-chatbot

# Step 8: Install systemd service
log_info "Installing systemd service..."
sudo cp "$DEPLOY_DIR/deployments/myhealthteam-chatbot.service" "/etc/systemd/system/$SERVICE_NAME.service"
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"

# Step 9: Configure Nginx
log_info "Configuring Nginx..."
if [ -f "$DEPLOY_DIR/deployments/nginx-chatbot.conf" ]; then
    sudo cp "$DEPLOY_DIR/deployments/nginx-chatbot.conf" "/etc/nginx/sites-available/chatbot.conf"
    sudo ln -sf /etc/nginx/sites-available/chatbot.conf /etc/nginx/sites-enabled/chatbot.conf
    sudo nginx -t && sudo systemctl reload nginx
    log_info "Nginx configured successfully"
else
    log_warn "Nginx config not found, skipping Nginx configuration"
fi

# Step 10: Start service
log_info "Starting chatbot service..."
sudo systemctl restart "$SERVICE_NAME"

# Step 11: Check status
sleep 3
if sudo systemctl is-active --quiet "$SERVICE_NAME"; then
    log_info "✓ Chatbot service is running!"
    echo ""
    echo "=========================================="
    echo "Deployment Complete!"
    echo "=========================================="
    echo ""
    echo "Chatbot URL: http://care.myhealthteam.org/chat"
    echo "Service Status: sudo systemctl status $SERVICE_NAME"
    echo "View Logs: sudo journalctl -u $SERVICE_NAME -f"
    echo ""
else
    log_error "Failed to start chatbot service"
    log_error "Check logs: sudo journalctl -u $SERVICE_NAME -n 50"
    exit 1
fi
