import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from core.cleanup import cleanup_loop
from core.job_store import get_job
from models import JobResponse, JobStatus
from routes import youtube, upload, admin
from config import settings


def _write_cookies_file() -> None:
    """Decode COOKIES_BASE64 env var to a file if no COOKIES_FILE is set."""
    if settings.COOKIES_FILE or not settings.COOKIES_BASE64:
        return
    import base64
    path = os.path.join(settings.TEMP_DIR, "cookies.txt")
    with open(path, "wb") as f:
        f.write(base64.b64decode(settings.COOKIES_BASE64))
    settings.COOKIES_FILE = path


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(settings.TEMP_DIR, exist_ok=True)
    _write_cookies_file()
    task = asyncio.create_task(cleanup_loop())
    yield
    task.cancel()


app = FastAPI(
    title="Audio Extraction Service",
    description="خدمة استخراج الصوت من يوتيوب وملفات الفيديو",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(youtube.router)
app.include_router(upload.router)
app.include_router(admin.router)


@app.get("/jobs/{job_id}", response_model=JobResponse)
async def job_status(job_id: str) -> JobResponse:
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="الوظيفة غير موجودة أو انتهت صلاحيتها")
    return JobResponse(
        job_id=job_id,
        status=job["status"],
        error=job.get("error"),
        title=job.get("title"),
        duration=job.get("duration"),
        audio_url=f"/jobs/{job_id}/download" if job["status"] == JobStatus.done else None,
    )


@app.get("/jobs/{job_id}/download")
async def download_audio(job_id: str) -> FileResponse:
    job = get_job(job_id)
    if not job or job["status"] != JobStatus.done:
        raise HTTPException(status_code=404, detail="الملف غير متاح")
    file_path = job["file_path"]
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="الملف غير موجود على القرص")
    return FileResponse(
        file_path,
        media_type="audio/mpeg",
        filename=f"{job_id}.mp3",
    )


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/debug/pot")
async def debug_pot() -> dict:
    """Diagnostic: check PO token server and yt-dlp plugins."""
    import subprocess, httpx
    info = {}

    # Check yt-dlp version
    try:
        r = subprocess.run(["python", "-m", "yt_dlp", "--version"], capture_output=True, text=True)
        info["ytdlp_version"] = r.stdout.strip()
    except Exception as e:
        info["ytdlp_version"] = str(e)

    # List yt-dlp plugins
    try:
        r = subprocess.run(
            ["python", "-c", "import yt_dlp; yd = yt_dlp.YoutubeDL({'quiet': True}); print([p.name for p in yd._plugin_dirs.get('extractors', [])])"],
            capture_output=True, text=True, timeout=10,
        )
        info["ytdlp_plugins_stdout"] = r.stdout.strip()
        info["ytdlp_plugins_stderr"] = r.stderr.strip()[:500] if r.stderr else ""
    except Exception as e:
        info["ytdlp_plugins"] = str(e)

    # Check PO token server on port 4416
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("http://127.0.0.1:4416/", timeout=5)
            info["pot_server"] = {"status": resp.status_code, "body": resp.text[:200]}
    except Exception as e:
        info["pot_server"] = {"error": str(e)}

    # Check if bgutil plugin is importable
    try:
        import importlib
        mod = importlib.import_module("bgutil_ytdlp_pot_provider")
        info["bgutil_plugin"] = {"installed": True, "path": str(mod.__file__) if hasattr(mod, '__file__') else "unknown"}
    except ImportError as e:
        info["bgutil_plugin"] = {"installed": False, "error": str(e)}

    # Check deno availability
    try:
        r = subprocess.run(["deno", "--version"], capture_output=True, text=True, timeout=5)
        info["deno_version"] = r.stdout.strip().split("\n")[0] if r.stdout else r.stderr.strip()[:200]
    except Exception as e:
        info["deno_version"] = str(e)

    # Check pot-server files exist
    info["pot_server_files"] = {
        "main_ts": os.path.exists("/app/pot-server/server/src/main.ts"),
        "node_modules": os.path.exists("/app/pot-server/server/node_modules"),
    }

    # Check running processes
    try:
        r = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=5)
        info["processes"] = [l for l in r.stdout.split("\n") if "deno" in l.lower() or "pot" in l.lower() or "main.ts" in l.lower()]
    except Exception as e:
        info["processes"] = str(e)

    # Try starting PO token server and capture error
    try:
        r = subprocess.run(
            ["deno", "run", "--allow-env", "--allow-net",
             "--allow-ffi=/app/pot-server/server/node_modules",
             "--allow-read=/app/pot-server/server/node_modules",
             "--unstable-bare-node-builtins",
             "/app/pot-server/server/src/main.ts"],
            capture_output=True, text=True, timeout=15,
            cwd="/app/pot-server/server",
        )
        info["pot_start_attempt"] = {
            "returncode": r.returncode,
            "stdout": r.stdout[:500],
            "stderr": r.stderr[:500],
        }
    except subprocess.TimeoutExpired:
        info["pot_start_attempt"] = "Server started (still running after 15s = good)"
    except Exception as e:
        info["pot_start_attempt"] = str(e)

    # Check entrypoint log
    try:
        r = subprocess.run(["cat", "/app/pot-server-startup.log"], capture_output=True, text=True, timeout=5)
        info["startup_log"] = r.stdout[:500] if r.stdout else r.stderr[:200]
    except Exception as e:
        info["startup_log"] = str(e)

    return info
