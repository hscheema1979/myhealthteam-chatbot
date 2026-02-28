#!/bin/bash
# VPS2 Setup Script for MyHealthTeam Chatbot (PM2 Managed)
# Run this script ON VPS2 after logging in

set -e

echo "=========================================="
echo "MyHealthTeam Chatbot - VPS2 Setup (PM2)"
echo "=========================================="

# Configuration
REPO_URL="https://github.com/hscheema1979/myhealthteam-chatbot.git"
DEPLOY_DIR="/var/www/myhealthteam-chatbot"
APP_NAME="myhealthteam-chatbot"
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

# Step 1: Install Node.js and PM2 if not present
log_info "Checking for Node.js and PM2..."
if ! command -v node &> /dev/null; then
    log_info "Installing Node.js..."
    curl -fsSL https://deb.nodesource.com/setup_lts.x | bash -
    apt-get install -y nodejs
fi

if ! command -v pm2 &> /dev/null; then
    log_info "Installing PM2..."
    npm install -g pm2
    pm2 install pm2-logrotate
fi

# Step 2: Clone repository
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

# Step 3: Create virtual environment
log_info "Setting up Python virtual environment..."
if [ ! -d "$DEPLOY_DIR/venv" ]; then
    python3 -m venv "$DEPLOY_DIR/venv"
fi

# Step 4: Install dependencies
log_info "Installing Python dependencies..."
"$DEPLOY_DIR/venv/bin/pip" install --upgrade pip -q
"$DEPLOY_DIR/venv/bin/pip" install -r "$DEPLOY_DIR/requirements.txt" -q

# Step 5: Copy test database
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

# Step 6: Configure environment
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

# Step 7: Set permissions
log_info "Setting file permissions..."
chown -R www-data:www-data "$DEPLOY_DIR"
chmod -R 755 "$DEPLOY_DIR"
chmod +x "$DEPLOY_DIR/start-chatbot.sh"

# Step 8: Create log directory
log_info "Creating log directory..."
mkdir -p /var/log/myhealthteam-chatbot
chown www-data:www-data /var/log/myhealthteam-chatbot

# Step 9: Configure Nginx
log_info "Configuring Nginx..."
if [ -f "$DEPLOY_DIR/deployments/nginx-chatbot.conf" ]; then
    if grep -q "include.*sites-enabled" /etc/nginx/nginx.conf; then
        cp "$DEPLOY_DIR/deployments/nginx-chatbot.conf" "/etc/nginx/sites-available/chatbot.conf"
        ln -sf /etc/nginx/sites-available/chatbot.conf /etc/nginx/sites-enabled/chatbot.conf

        if nginx -t 2>/dev/null; then
            systemctl reload nginx
            log_info "✓ Nginx configured successfully"
        else
            log_warn "Nginx config test failed, skipping reload"
        fi
    else
        log_warn "Nginx not configured for sites-enabled, skipping"
    fi
fi

# Step 10: Stop existing PM2 process if running
log_info "Checking for existing PM2 processes..."
if pm2 describe "$APP_NAME" &> /dev/null; then
    log_info "Stopping existing $APP_NAME..."
    pm2 stop "$APP_NAME"
    pm2 delete "$APP_NAME"
fi

# Step 11: Start with PM2
log_info "Starting chatbot with PM2..."
cd "$DEPLOY_DIR"
pm2 start ecosystem.config.cjs

# Step 12: Save PM2 process list
log_info "Saving PM2 process list..."
pm2 save
pm2 startup | tail -n 1 > /tmp/pm2-startup.sh
if [ -s /tmp/pm2-startup.sh ]; then
    log_info "To enable PM2 auto-start on boot, run:"
    cat /tmp/pm2-startup.sh
fi

# Wait for app to start
sleep 5

# Step 13: Check status
if pm2 describe "$APP_NAME" &> /dev/null; then
    STATUS=$(pm2 jlist | node -e "console.log(JSON.parse(require('fs').readFileSync(0)).find(p=>p.name==='$APP_NAME').pm2_env.status)")
    if [ "$STATUS" = "online" ]; then
        log_info "✓ Chatbot is running with PM2!"
        echo ""
        echo "=========================================="
        echo "Deployment Complete!"
        echo "=========================================="
        echo ""
        echo "Repository: https://github.com/hscheema1979/myhealthteam-chatbot"
        echo "Deploy Directory: $DEPLOY_DIR"
        echo "Process Manager: PM2"
        echo ""
        echo "Access URLs:"
        echo "  Internal: http://localhost:8503"
        echo "  External: http://care.myhealthteam.org/chat"
        echo ""
        echo "PM2 Commands:"
        echo "  Status:  pm2 status"
        echo "  Logs:    pm2 logs $APP_NAME"
        echo "  Restart: pm2 restart $APP_NAME"
        echo "  Stop:    pm2 stop $APP_NAME"
        echo "  Monitor: pm2 monit"
        echo ""
    else
        log_error "Chatbot process not online (status: $STATUS)"
        pm2 logs "$APP_NAME" --lines 20 --nostream
        exit 1
    fi
else
    log_error "Failed to start chatbot with PM2"
    pm2 logs "$APP_NAME" --lines 20 --nostream
    exit 1
fi
