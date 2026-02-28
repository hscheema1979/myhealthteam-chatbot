# 🚀 Ready to Deploy

## Status: READY ✓

The MyHealthTeam Chatbot is ready for deployment to VPS2 with **PM2 process management**.

## One-Command Deploy

SSH into VPS2 and run this single command:

```bash
curl -sSL https://raw.githubusercontent.com/hscheema1979/myhealthteam-chatbot/master/deployments/vps2-setup.sh | sudo bash
```

## What This Does

- ✓ Installs Node.js and PM2 (if not present)
- ✓ Clones chatbot from GitHub
- ✓ Sets up Python virtual environment
- ✓ Installs dependencies
- ✓ Copies test database (isolated from production)
- ✓ Configures environment for port 8503
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
- **8503**: Chatbot (new)

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

## Security

- ✓ Test database only (production_backup_for_testing.db)
- ✓ No access to production data
- ✓ All changes require confirmation
- ✓ Complete audit logging
- ✓ PM2 auto-restart on failure
- ✓ PM2 log rotation

---

**Repository**: https://github.com/hscheema1979/myhealthteam-chatbot
**Process Manager**: PM2 with auto-restart and log rotation
