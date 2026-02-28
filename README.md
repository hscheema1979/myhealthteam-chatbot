# MyHealthTeam Chatbot - Standalone Health Assistant

A standalone intelligent chatbot interface for MyHealthTeam coordinators and providers. This application provides natural language access to patient information, task management, and health metrics.

**Isolation Notice**: This chatbot is configured to work with the TEST DATABASE ONLY (`production_backup_for_testing.db`). It will never access production data.

## Features

- **Natural Language Interface**: Ask questions in plain English
- **Quick Stats**: Get personal and team performance metrics
- **Patient Information**: Query patient status and details
- **Task Management**: Log visits, add tasks, update patient status
- **Secure Data Entry**: All changes require confirmation before execution
- **Transaction Safety**: All database operations are atomic and audited

## Tech Stack

- **Frontend**: Streamlit (port 8502)
- **NLP Engine**: Gemini CLI (BAA compliant for healthcare)
- **Database**: SQLite (test database only)
- **Safety Layer**: Surgical action harness with schema validation

## Installation

### Prerequisites

```bash
# Python 3.10+
sudo apt update
sudo apt install python3-pip python3-venv

# Gemini CLI (BAA with Google)
npm install -g @google/gemini-cli
```

### Setup

```bash
# Clone this repository
git clone <repository-url> myhealthteam-chatbot
cd myhealthteam-chatbot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your test database path
```

## Configuration

### Environment Variables (.env)

```bash
# Database Path (TEST DATABASE ONLY)
DATABASE_PATH=/path/to/production_backup_for_testing.db

# Gemini CLI Configuration
GEMINI_MODEL=gemini-pro
GEMINI_TIMEOUT=30000

# Application Settings
CHATBOT_PORT=8502
CHATBOT_HOST=0.0.0.0

# Security
SECRET_KEY=<your-secret-key>
SESSION_TIMEOUT=3600
```

## Running

### Development

```bash
# Activate virtual environment
source venv/bin/activate

# Run chatbot
streamlit run chatbot_app.py --server.port=8502
```

### Production (systemd)

```bash
# Install service
sudo cp deployments/myhealthteam-chatbot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable myhealthteam-chatbot
sudo systemctl start myhealthteam-chatbot

# Check status
sudo systemctl status myhealthteam-chatbot
```

## Usage Examples

### Queries (No confirmation required)
```
/stats or "How many patients do I have?"
/patients or "Show active patients"
/tasks or "What are my pending tasks?"
/workflows or "Any pending workflows?"
```

### Actions (Require confirmation)
```
"Add 30min PCP visit for John Smith"
"Update Mary Johnson status to discharged"
"Log 15min follow-up call for patient 123"
```

## Architecture

```
chatbot_app.py (Streamlit UI)
    ↓
GeminiClient (NLP via Gemini CLI)
    ↓
IntentParser → ActionBuilder
    ↓
TransactionExecutor (Safe DB operations)
    ↓
Test Database (production_backup_for_testing.db)
```

## Safety Features

1. **Schema Validation**: All operations validated against actual database structure
2. **Transaction Atomicity**: All-or-nothing changes with automatic rollback
3. **Confirmation Required**: No database changes without user approval
4. **Audit Logging**: Complete trail of all database operations
5. **Test Isolation**: Configured for test database only

## Deployment

### VPS2 Test Instance

```bash
# SSH to VPS2
ssh ubuntu@178.16.140.23

# Navigate to chatbot directory
cd /var/www/myhealthteam-chatbot

# Pull latest changes
git pull origin main

# Restart service
sudo systemctl restart myhealthteam-chatbot
```

### Nginx Configuration

```nginx
location /chat {
    proxy_pass http://localhost:8502;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
}
```

## Monitoring

```bash
# View logs
sudo journalctl -u myhealthteam-chatbot -f

# Check service status
sudo systemctl status myhealthteam-chatbot

# View database operations
sqlite3 production_backup_for_testing.db "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT 20;"
```

## Testing

```bash
# Run unit tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test
pytest tests/chatbot/test_intent_parser.py -v
```

## License

Proprietary - MyHealthTeam Internal Use Only

## Support

For issues or questions, contact the development team.
