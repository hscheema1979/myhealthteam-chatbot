# 🚀 Ready to Deploy

## Status: READY ✓

The MyHealthTeam Chatbot is ready for deployment to VPS2.

## One-Command Deploy

SSH into VPS2 and run this single command:

```bash
curl -sSL https://raw.githubusercontent.com/hscheema1979/myhealthteam-chatbot/master/deployments/vps2-setup.sh | sudo bash
```

## What This Does

- ✓ Clones chatbot from GitHub
- ✓ Sets up Python virtual environment
- ✓ Installs dependencies
- ✓ Copies test database (isolated from production)
- ✓ Configures environment for port 8503
- ✓ Creates systemd service (auto-start)
- ✓ Configures Nginx route at `/chat`
- ✓ Starts the chatbot service

## Access After Deploy

| URL | Description |
|-----|-------------|
| http://care.myhealthteam.org/chat | Public access |
| http://178.16.140.23:8503 | Direct access |

## Ports Used

- **8501**: Main app (unchanged)
- **8502**: Monitoring dashboard (unchanged)
- **8503**: Chatbot (new)

## Verification Commands

```bash
# Check service status
sudo systemctl status myhealthteam-chatbot

# View logs
sudo journalctl -u myhealthteam-chatbot -f

# Test locally
curl http://localhost:8503

# Restart if needed
sudo systemctl restart myhealthteam-chatbot
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

---

**Repository**: https://github.com/hscheema1979/myhealthteam-chatbot
