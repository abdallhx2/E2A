#!/bin/bash

# Start bgutil PO token server in background (generates YouTube bot-bypass tokens)
cd /app/pot-server/server/node_modules && \
  deno run --allow-env --allow-net --allow-ffi=. --allow-read=. ../src/main.ts &

# Wait a moment for the token server to initialize
sleep 3

# Start the main application
cd /app
exec uvicorn main:app --host 0.0.0.0 --port 8000
