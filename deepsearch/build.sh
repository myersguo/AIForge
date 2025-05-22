#!/bin/bash

# Start both DeepSearch's backend and web UI server.
# If the user presses Ctrl+C, kill them both.

if [ "$1" = "--dev" -o "$1" = "-d" -o "$1" = "dev" -o "$1" = "development" ]; then
  echo -e "Starting DeepSearch in [DEVELOPMENT] mode...\n"
  python main.py & SERVER_PID=$!
  cd web && pnpm dev & WEB_PID=$!
  trap "kill $SERVER_PID $WEB_PID" SIGINT SIGTERM
  wait
else
  echo -e "Starting DeepSearch in [PRODUCTION] mode...\n"
  source .venv/bin/activate
  python main.py
  cd web && pnpm start
fi 
