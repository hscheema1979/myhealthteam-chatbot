# Quick VPS2 Deployment Instructions

## GitHub Repository
**URL**: https://github.com/hscheema1979/myhealthteam-chatbot

## One-Line VPS2 Deploy

SSH into VPS2 and run:

```bash
curl -sSL https://raw.githubusercontent.com/hscheema1979/myhealthteam-chatbot/master/deployments/vps2-setup.sh | sudo bash
```

## What Gets Deployed

- Chatbot application on port 8503
- PM2 process manager (auto-restart on failure)
- Nginx route at `/chat`
- PM2 auto-start on boot
- Test database isolation

## Access After Deploy

- **External**: http://care.myhealthteam.org/chat
- **Internal**: http://178.16.140.23:8503

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

## Test the Chatbot

Once deployed, try these queries:

```
/stats
/patients
/tasks
"How many patients do I have?"
"Show active patients"
```
