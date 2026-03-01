# Complete Deployment Guide - VPS2 Test Instance

## ⚠️ IMPORTANT: TEST INSTANCE ONLY

This chatbot is for **TESTING ONLY** and should:
- ❌ NEVER be deployed to production (care.myhealthteam.org)
- ❌ NEVER be accessible on the main site
- ✅ ONLY run on test subdomain (test.myhealthteam.org)
- ✅ ONLY use test database (production_backup_for_testing.db)

---

## Quick Deploy (Subdomain)

### Step 1: Deploy Chatbot

```bash
ssh ubuntu@178.16.140.23

# Deploy with PM2 to isolated workspace
curl -sSL https://raw.githubusercontent.com/hscheema1979/myhealthteam-chatbot/master/deployments/vps2-setup.sh | sudo bash
```

### Step 2: Configure Nginx for Test Subdomain

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

**Test site**: http://test.myhealthteam.org/chat
**Direct**: http://test.myhealthteam.org/ (redirects to /chat)

---

## Direct Port Access (For Testing)

```bash
ssh ubuntu@178.16.140.23

# Deploy chatbot
curl -sSL https://raw.githubusercontent.com/hscheema1979/myhealthteam-chatbot/master/deployments/vps2-setup.sh | sudo bash

# Test access
curl http://localhost:8503
```

**Access**: http://178.16.140.23:8503

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

## Access Options (TEST ONLY)

| URL | Description |
|-----|-------------|
| http://178.16.140.23:8503 | Direct IP access (for testing) |
| http://test.myhealthteam.org/chat | Test subdomain (primary access) |

❌ **NOT AVAILABLE**: http://care.myhealthteam.org/chat (production - do not use)

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

- ✅ Workspace: `/opt/test_myhealthteam/` (isolated)
- ✅ Database: `production_backup_for_testing.db` only
- ✅ Port: 8503 (isolated)
- ✅ Subdomain: test.myhealthteam.org (test only)
- ✅ PM2: Auto-restart enabled
- ✅ Gemini CLI: Test data only
- ✅ No production access: Enforced in code
- ❌ Production site: NOT configured
