# 🚀 Ready to Deploy - Workspace Isolated

## Status: READY ✓

The MyHealthTeam Chatbot is ready for deployment to VPS2 with **PM2 process management** and **workspace isolation**.

## Workspace Isolation

The chatbot is configured to ONLY operate within `/opt/test_myhealthteam/` workspace:

```
/opt/test_myhealthteam/
├── chatbot/                    # Chatbot application
│   ├── production_backup_for_testing.db  # Test database only
│   ├── venv/                    # Python environment
│   ├── chatbot_app.py
│   └── src/
└── (no production access)
```

## Security Layers

1. ✅ **Workspace Isolation**: Only operates in `/opt/test_myhealthteam/`
2. ✅ **Test Database Only**: `production_backup_for_testing.db`
3. ✅ **Path Validation**: Enforced in `src/database.py`
4. ✅ **No Production Access**: Cannot access production database

## One-Command Deploy

SSH into VPS2 and run this single command:

```bash
ssh ubuntu@178.16.140.23

curl -sSL https://raw.githubusercontent.com/hscheema1979/myhealthteam-chatbot/master/deployments/vps2-setup.sh | sudo bash
```

## What This Does

- ✓ Creates `/opt/test_myhealthteam/` workspace
- ✓ Installs Node.js and PM2 (if not present)
- ✓ Clones chatbot from GitHub
- ✓ Sets up Python virtual environment
- ✓ Installs dependencies
- ✓ Copies test database to workspace
- ✓ Enforces workspace isolation
- ✓ Starts chatbot with PM2 (auto-restart on failure)
- ✓ Configures Nginx route at `/chat`
- ✓ Enables PM2 auto-start on boot

## Access After Deploy

| URL | Description |
|-----|-------------|
| http://care.myhealthteam.org/chat | Public access |
| http://178.16.140.23:8503 | Direct access |

## Ports Used

- **8501**: Main app (unchanged)
- **8502**: Monitoring dashboard (unchanged)
- **8503**: Chatbot (new, isolated)

## PM2 Management Commands

```bash
# Check status
pm2 status

# View logs (real-time)
pm2 logs myhealthteam-chatbot

# Restart app
pm2 restart myhealthteam-chatbot

# Stop app
pm2 stop myhealthteam-chatbot

# Monitor (interactive dashboard)
pm2 monit

# View detailed info
pm2 describe myhealthteam-chatbot
```

## Verification Commands

```bash
# Verify workspace isolation
grep DATABASE_PATH /opt/test_myhealthteam/chatbot/.env
# Should show: DATABASE_PATH=/opt/test_myhealthteam/chatbot/production_backup_for_testing.db

# Test locally
curl http://localhost:8503

# Check PM2 process list
pm2 list

# View resource usage
pm2 monit
```

## Test Queries

Once deployed, try these:
- `/stats` - View your statistics
- `/patients` - List your patients
- `/tasks` - Show pending tasks
- "How many patients do I have?"
- "Show active patients"

## Security Checklist

- ✅ Workspace isolation: `/opt/test_myhealthteam/` only
- ✅ Test database only: `production_backup_for_testing.db`
- ✅ Path validation enforced in code
- ✅ No access to production data
- ✅ All changes require confirmation
- ✅ Complete audit logging
- ✅ PM2 auto-restart on failure
- ✅ PM2 log rotation

---

**Repository**: https://github.com/hscheema1979/myhealthteam-chatbot
**Process Manager**: PM2 with auto-restart and log rotation
**Workspace**: `/opt/test_myhealthteam/` (isolated)
