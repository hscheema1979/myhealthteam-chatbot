# VPS2 Test Instance Deployment Guide

This guide covers deploying the MyHealthTeam Chatbot to VPS2 test instance.

## Prerequisites

- SSH access to VPS2 (178.16.140.23)
- Test database available at `/home/ubuntu/myhealthteam/dev/production_backup_for_testing.db`
- Gemini CLI installed on VPS2

## Quick Deploy

```bash
# SSH into VPS2
ssh ubuntu@178.16.140.23

# Create deployment directory
sudo mkdir -p /var/www/myhealthteam-chatbot
sudo chown ubuntu:www-data /var/www/myhealthteam-chatbot

# Copy files from local
exit
scp -r /home/ubuntu/myhealthteam-chatbot ubuntu@178.16.140.23:/var/www/

# SSH back and run setup
ssh ubuntu@178.16.140.23
cd /var/www/myhealthteam-chatbot
./setup.sh
```

## Manual Setup Steps

### 1. Copy Repository to VPS2

```bash
# On local machine
rsync -avz --exclude='venv' --exclude='__pycache__' \
    /home/ubuntu/myhealthteam-chatbot/ \
    ubuntu@178.16.140.23:/var/www/myhealthteam-chatbot/
```

### 2. Copy Test Database

```bash
# On VPS2
sudo cp /home/ubuntu/myhealthteam/dev/production_backup_for_testing.db \
    /var/www/myhealthteam-chatbot/
sudo chown www-data:www-data /var/www/myhealthteam-chatbot/production_backup_for_testing.db
```

### 3. Setup Virtual Environment

```bash
cd /var/www/myhealthteam-chatbot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
cp .env.example .env
nano .env  # Edit with your configuration
```

Required .env settings:
```bash
DATABASE_PATH=/var/www/myhealthteam-chatbot/production_backup_for_testing.db
CHATBOT_PORT=8503
CHATBOT_HOST=0.0.0.0
```

### 5. Setup systemd Service

```bash
sudo cp deployments/myhealthteam-chatbot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable myhealthteam-chatbot
sudo systemctl start myhealthteam-chatbot
```

### 6. Configure Nginx

```bash
sudo cp deployments/nginx-chatbot.conf /etc/nginx/sites-available/chatbot.conf
sudo ln -s /etc/nginx/sites-available/chatbot.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 7. Verify Deployment

```bash
# Check service status
sudo systemctl status myhealthteam-chatbot

# View logs
sudo journalctl -u myhealthteam-chatbot -f

# Test locally
curl http://localhost:8503

# Test from external
curl http://care.myhealthteam.org/chat
```

## Test Database Isolation

The chatbot is configured to ONLY use the test database:

**Key Security Features:**

1. **Database Path Validation**: `src/database.py` validates the database path contains "test" or "production_backup_for_testing"

2. **Environment Variable**: `DATABASE_PATH` explicitly set to test database

3. **No Production Access**: Chatbot has no configuration for production database

**Verification:**
```bash
# Check database path
cat /var/www/myhealthteam-chatbot/.env | grep DATABASE_PATH

# Should output:
# DATABASE_PATH=/var/www/myhealthteam-chatbot/production_backup_for_testing.db
```

## Accessing the Chatbot

After deployment, access the chatbot at:

**Internal (VPS2):** http://localhost:8503
**External:** http://care.myhealthteam.org/chat

## Testing Natural Language Queries

Once deployed, test with these queries:

```
/stats
/patients
/tasks
/workflows
"How many patients do I have?"
"Show active patients"
"What are my pending tasks?"
```

## Monitoring and Logs

### Service Status
```bash
sudo systemctl status myhealthteam-chatbot
```

### Real-time Logs
```bash
sudo journalctl -u myhealthteam-chatbot -f
```

### Application Logs
```bash
tail -f /var/log/myhealthteam-chatbot/chatbot.log
```

### Database Audit Log
```bash
sqlite3 /var/www/myhealthteam-chatbot/production_backup_for_testing.db \
    "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT 20;"
```

## Troubleshooting

### Service Won't Start
```bash
# Check status
sudo systemctl status myhealthteam-chatbot

# View error logs
sudo journalctl -u myhealthteam-chatbot -n 50

# Common issues:
# - Port 8503 already in use
# - Virtual environment not set up
# - Database not found
```

### Database Connection Error
```bash
# Verify database exists
ls -la /var/www/myhealthteam-chatbot/*.db

# Check permissions
sudo chown www-data:www-data /var/www/myhealthteam-chatbot/*.db
sudo chmod 640 /var/www/myhealthteam-chatbot/*.db
```

### Nginx 502 Bad Gateway
```bash
# Check if chatbot is running
sudo systemctl status myhealthteam-chatbot

# Check if port is listening
sudo netstat -tlnp | grep 8503

# Test direct connection
curl http://localhost:8503
```

## Rollback

If you need to rollback:

```bash
# Stop service
sudo systemctl stop myhealthteam-chatbot

# Revert code
cd /var/www/myhealthteam-chatbot
git reset --hard HEAD~1

# Restart service
sudo systemctl start myhealthteam-chatbot
```

## Next Steps

After successful deployment:

1. **Test Authentication**: Ensure shared session auth works with main app
2. **Test Natural Language**: Try various NL queries
3. **Test Data Entry**: Test "Add task" flow with confirmation
4. **Monitor Logs**: Check for any errors in production logs
5. **Gather Feedback**: Collect feedback from test users

## Security Reminders

⚠️ **IMPORTANT**: This chatbot is configured for TEST DATABASE ONLY

- Never modify `DATABASE_PATH` to point to production
- Always verify isolation before deploying
- Monitor audit logs for any unexpected database changes
- Keep Gemini CLI updated for security patches
