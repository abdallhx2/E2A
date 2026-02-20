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
