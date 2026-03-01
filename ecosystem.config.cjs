module.exports = {
  apps: [{
    name: 'myhealthteam-chatbot',
    script: './start-chatbot.sh',
    cwd: '/opt/test_myhealthteam/chatbot',
    interpreter: '/bin/bash',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
    restart_delay: 4000,
    min_uptime: '10s',
    max_restarts: 10,
    env: {
      NODE_ENV: 'production',
      CHATBOT_PORT: 8504,
      CHATBOT_HOST: '0.0.0.0',
      WORKSPACE: '/opt/test_myhealthteam'
    },
    error_file: '/var/log/myhealthteam-chatbot/error.log',
    out_file: '/var/log/myhealthteam-chatbot/out.log',
    log_file: '/var/log/myhealthteam-chatbot/combined.log',
    time: true,
    merge_logs: true,
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
    kill_timeout: 5000,
    wait_ready: true,
    listen_timeout: 10000
  }]
};
