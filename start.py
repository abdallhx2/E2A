"""Startup script: launch bgutil PO token server then uvicorn."""
import os
import subprocess
import sys
import time

# Render sets PORT dynamically - uvicorn must use it
render_port = os.environ.get("PORT", "8000")

# Start bgutil on fixed port 4416, stripping Render's PORT
pot_env = {k: v for k, v in os.environ.items() if k != "PORT"}

print(f"[start] Render PORT={render_port}, launching PO token server on 4416...")
pot_proc = subprocess.Popen(
    ["node", "/app/pot-server/server/build/main.js", "--port", "4416"],
    env=pot_env,
    stdout=open("/app/pot-server-startup.log", "w"),
    stderr=subprocess.STDOUT,
)

time.sleep(3)

if pot_proc.poll() is None:
    print(f"[start] PO token server running (PID {pot_proc.pid})")
else:
    print("[start] WARNING: PO token server crashed!")
    with open("/app/pot-server-startup.log") as f:
        print(f.read()[:500])

print(f"[start] Starting uvicorn on port {render_port}...")
os.execvp(
    sys.executable,
    [sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", render_port],
)
