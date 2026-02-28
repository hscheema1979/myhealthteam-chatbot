# Quick VPS2 Deployment Instructions

## GitHub Repository
**URL**: https://github.com/hscheema1979/myhealthteam-chatbot

## One-Line VPS2 Deploy

SSH into VPS2 and run:

```bash
curl -sSL https://raw.githubusercontent.com/hscheema1979/myhealthteam-chatbot/master/deployments/vps2-setup.sh | sudo bash
```

Or manually:

```bash
# SSH to VPS2
ssh ubuntu@178.16.140.23

# Clone and setup
sudo bash << 'EOF'
git clone https://github.com/hscheema1979/myhealthteam-chatbot.git /var/www/myhealthteam-chatbot
cd /var/www/myhealthteam-chatbot
bash deployments/vps2-setup.sh
EOF
```

## What Gets Deployed

- Chatbot application on port 8503
- Nginx route at `/chat`
- Systemd service for auto-start
- Test database isolation

## Access After Deploy

- **External**: http://care.myhealthteam.org/chat
- **Internal**: http://178.16.140.23:8503

## Commands

```bash
# Check status
sudo systemctl status myhealthteam-chatbot

# View logs
sudo journalctl -u myhealthteam-chatbot -f

# Restart service
sudo systemctl restart myhealthteam-chatbot

# Stop service
sudo systemctl stop myhealthteam-chatbot
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
