#!/bin/bash
# PM2 wrapper script for MyHealthTeam Chatbot
# This script launches the Streamlit app with proper environment

cd /var/www/myhealthteam-chatbot

# Load environment variables if .env exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Activate virtual environment
source venv/bin/activate

# Start Streamlit
exec streamlit run chatbot_app.py \
    --server.port=${CHATBOT_PORT:-8503} \
    --server.address=${CHATBOT_HOST:-0.0.0.0} \
    --server.headless=true \
    --server.enableCORS=false \
    --server.enableXsrfProtection=true
