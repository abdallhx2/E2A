#!/bin/bash

# Start bgutil PO token server in background (port 4416)
echo "[entrypoint] Starting PO token server..."
cd /app/pot-server/server
deno run --allow-env --allow-net \
  --allow-ffi=/app/pot-server/server/node_modules \
  --allow-read=/app/pot-server/server/node_modules \
  /app/pot-server/server/src/main.ts > /app/pot-server-startup.log 2>&1 &
POT_PID=$!

sleep 5

if kill -0 $POT_PID 2>/dev/null; then
  echo "[entrypoint] PO token server started (PID $POT_PID)"
else
  echo "[entrypoint] WARNING: PO token server failed. Log:"
  cat /app/pot-server-startup.log
fi

cd /app
exec uvicorn main:app --host 0.0.0.0 --port 8000
