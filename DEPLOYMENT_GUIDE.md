# Complete Deployment Guide - VPS2 Test Instance

## Quick Deploy (Port 8503)

```bash
ssh ubuntu@178.16.140.23

# Deploy chatbot
curl -sSL https://raw.githubusercontent.com/hscheema1979/myhealthteam-chatbot/master/deployments/vps2-setup.sh | sudo bash

# Test access
curl http://localhost:8503
```

Access: http://178.16.140.23:8503

---

## Subdomain Deploy (test.myhealthteam.org)

### Step 1: Deploy Chatbot

```bash
ssh ubuntu@178.16.140.23

# Deploy with PM2
curl -sSL https://raw.githubusercontent.com/hscheema1979/myhealthteam-chatbot/master/deployments/vps2-setup.sh | sudo bash
```

### Step 2: Configure Nginx for Subdomain

```bash
# On VPS2, copy the subdomain config
sudo cp /opt/test_myhealthteam/chatbot/deployments/nginx-test-subdomain.conf \
        /etc/nginx/sites-available/test-myhealthteam

# Enable the site
sudo ln -s /etc/nginx/sites-available/test-myhealthteam \
            /etc/nginx/sites-enabled/test-myhealthteam

# Test nginx config
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

### Step 3: Configure DNS

Add an A record for test.myhealthteam.org:

```
Type: A
Name: test
Value: 178.16.140.23
TTL: 300
```

### Step 4: Access

**Main site**: http://test.myhealthteam.org
**Chat path**: http://test.myhealthteam.org/chat
**Direct**: http://test.myhealthteam.org/ (redirects to /chat)

---

## Workspace Verification

```bash
# Verify workspace isolation
grep DATABASE_PATH /opt/test_myhealthteam/chatbot/.env

# Should output:
# DATABASE_PATH=/opt/test_myhealthteam/chatbot/production_backup_for_testing.db

# Verify PM2 is running
pm2 status

# View logs
pm2 logs myhealthteam-chatbot
```

---

## Access Options

| URL | Description |
|-----|-------------|
| http://178.16.140.23:8503 | Direct IP access |
| http://care.myhealthteam.org/chat | Via main site |
| http://test.myhealthteam.org/chat | Via subdomain (after DNS + Nginx config) |

---

## PM2 Management

```bash
pm2 status                          # Check status
pm2 logs myhealthteam-chatbot      # View logs
pm2 restart myhealthteam-chatbot   # Restart
pm2 stop myhealthteam-chatbot      # Stop
pm2 monit                           # Monitor
```

---

## Security Checklist

- ✅ Workspace: `/opt/test_myhealthteam/`
- ✅ Database: `production_backup_for_testing.db` only
- ✅ Port: 8503 (isolated)
- ✅ PM2: Auto-restart enabled
- ✅ Gemini CLI: Test data only
- ✅ No production access possible
