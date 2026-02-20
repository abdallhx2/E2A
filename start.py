"""Startup script: launch bgutil PO token server then uvicorn."""
import os
import subprocess
import sys
import time

# Force PORT=4416 for bgutil, removing Render's PORT=8000
pot_env = {k: v for k, v in os.environ.items() if k != "PORT"}
pot_env["PORT"] = "4416"

print("[start] Launching PO token server on port 4416...")
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

print("[start] Starting uvicorn...")
os.execvp(
    sys.executable,
    [sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"],
)
