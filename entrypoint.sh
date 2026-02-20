#!/bin/bash

# Start bgutil PO token server in background (port 4416)
echo "[entrypoint] Starting PO token server..."
cd /app/pot-server/server
deno run --allow-env --allow-net \
  --allow-ffi=/app/pot-server/server/node_modules \
  --allow-read=/app/pot-server/server/node_modules \
  /app/pot-server/server/src/main.ts &
POT_PID=$!

# Wait for server to initialize
sleep 5

# Check if PO token server is alive
if kill -0 $POT_PID 2>/dev/null; then
  echo "[entrypoint] PO token server started (PID $POT_PID)"
else
  echo "[entrypoint] WARNING: PO token server failed to start"
fi

# Start the main application
cd /app
exec uvicorn main:app --host 0.0.0.0 --port 8000
