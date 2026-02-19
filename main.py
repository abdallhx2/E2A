import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from core.cleanup import cleanup_loop
from core.job_store import get_job
from models import JobResponse, JobStatus
from routes import youtube, upload
from config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(settings.TEMP_DIR, exist_ok=True)
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
