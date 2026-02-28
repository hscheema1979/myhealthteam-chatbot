#!/bin/bash
# VPS2 Setup Script for MyHealthTeam Chatbot
# Run this script ON VPS2 after logging in

set -e

echo "=========================================="
echo "MyHealthTeam Chatbot - VPS2 Setup"
echo "=========================================="

# Configuration
REPO_URL="https://github.com/hscheema1979/myhealthteam-chatbot.git"
DEPLOY_DIR="/var/www/myhealthteam-chatbot"
SERVICE_NAME="myhealthteam-chatbot"
TEST_DB_SOURCE="/home/ubuntu/myhealthteam/dev/production_backup_for_testing.db"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   log_error "This script must be run with sudo"
   exit 1
fi

# Step 1: Clone repository
log_info "Cloning repository from GitHub..."
if [ -d "$DEPLOY_DIR" ]; then
    log_info "Directory exists, updating..."
    cd "$DEPLOY_DIR"
    sudo -u www-data git pull origin master
else
    log_info "Cloning fresh copy..."
    mkdir -p "$DEPLOY_DIR"
    git clone "$REPO_URL" "$DEPLOY_DIR"
    cd "$DEPLOY_DIR"
fi

# Step 2: Create virtual environment
log_info "Setting up Python virtual environment..."
if [ ! -d "$DEPLOY_DIR/venv" ]; then
    python3 -m venv "$DEPLOY_DIR/venv"
fi

# Step 3: Install dependencies
log_info "Installing Python dependencies..."
"$DEPLOY_DIR/venv/bin/pip" install --upgrade pip -q
"$DEPLOY_DIR/venv/bin/pip" install -r "$DEPLOY_DIR/requirements.txt" -q

# Step 4: Copy test database
log_info "Copying test database..."
if [ -f "$TEST_DB_SOURCE" ]; then
    cp "$TEST_DB_SOURCE" "$DEPLOY_DIR/production_backup_for_testing.db"
    chown www-data:www-data "$DEPLOY_DIR/production_backup_for_testing.db"
    chmod 640 "$DEPLOY_DIR/production_backup_for_testing.db"
    log_info "✓ Test database copied"
else
    log_warn "Test database not found at $TEST_DB_SOURCE"
    log_warn "You'll need to copy it manually"
fi

# Step 5: Configure environment
log_info "Setting up environment..."
if [ ! -f "$DEPLOY_DIR/.env" ]; then
    cp "$DEPLOY_DIR/.env.example" "$DEPLOY_DIR/.env"

    # Set default values
    echo "DATABASE_PATH=$DEPLOY_DIR/production_backup_for_testing.db" >> "$DEPLOY_DIR/.env"
    echo "CHATBOT_PORT=8503" >> "$DEPLOY_DIR/.env"
    echo "CHATBOT_HOST=0.0.0.0" >> "$DEPLOY_DIR/.env"

    log_info "Created .env file with defaults"
fi

chown www-data:www-data "$DEPLOY_DIR/.env"
chmod 640 "$DEPLOY_DIR/.env"

# Step 6: Set permissions
log_info "Setting file permissions..."
chown -R www-data:www-data "$DEPLOY_DIR"
chmod -R 755 "$DEPLOY_DIR"

# Step 7: Create log directory
log_info "Creating log directory..."
mkdir -p /var/log/myhealthteam-chatbot
chown www-data:www-data /var/log/myhealthteam-chatbot

# Step 8: Install systemd service
log_info "Installing systemd service..."
cp "$DEPLOY_DIR/deployments/myhealthteam-chatbot.service" "/etc/systemd/system/$SERVICE_NAME.service"
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"

# Step 9: Configure Nginx
log_info "Configuring Nginx..."
if [ -f "$DEPLOY_DIR/deployments/nginx-chatbot.conf" ]; then
    # Check if main nginx config includes sites-enabled
    if grep -q "include.*sites-enabled" /etc/nginx/nginx.conf; then
        cp "$DEPLOY_DIR/deployments/nginx-chatbot.conf" "/etc/nginx/sites-available/chatbot.conf"
        ln -sf /etc/nginx/sites-available/chatbot.conf /etc/nginx/sites-enabled/chatbot.conf

        # Test nginx config
        if nginx -t 2>/dev/null; then
            systemctl reload nginx
            log_info "✓ Nginx configured successfully"
        else
            log_warn "Nginx config test failed, skipping reload"
        fi
    else
        log_warn "Nginx not configured for sites-enabled, skipping"
        log_warn "Add the contents of $DEPLOY_DIR/deployments/nginx-chatbot.conf to your nginx config manually"
    fi
fi

# Step 10: Start service
log_info "Starting chatbot service..."
systemctl restart "$SERVICE_NAME"

# Wait for service to start
sleep 3

# Step 11: Check status
if systemctl is-active --quiet "$SERVICE_NAME"; then
    log_info "✓ Chatbot service is running!"
    echo ""
    echo "=========================================="
    echo "Deployment Complete!"
    echo "=========================================="
    echo ""
    echo "Repository: https://github.com/hscheema1979/myhealthteam-chatbot"
    echo "Deploy Directory: $DEPLOY_DIR"
    echo ""
    echo "Access URLs:"
    echo "  Internal: http://localhost:8503"
    echo "  External: http://care.myhealthteam.org/chat"
    echo ""
    echo "Commands:"
    echo "  Status: sudo systemctl status $SERVICE_NAME"
    echo "  Logs:   sudo journalctl -u $SERVICE_NAME -f"
    echo "  Restart: sudo systemctl restart $SERVICE_NAME"
    echo ""
else
    log_error "Failed to start chatbot service"
    log_error "Check logs: sudo journalctl -u $SERVICE_NAME -n 50"
    exit 1
fi
