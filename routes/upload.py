import os
import aiofiles
from pathlib import Path
from fastapi import APIRouter, BackgroundTasks, Security, UploadFile, File, HTTPException
from models import JobResponse
from core.job_store import create_job
from core.extractor import extract_video_file
from config import settings
from routes.youtube import verify_key

router = APIRouter(prefix="/extract", tags=["extract"])

ALLOWED_TYPES = {
    "video/mp4",
    "video/webm",
    "video/quicktime",
    "video/x-matroska",
}


@router.post("/upload", response_model=JobResponse, status_code=202)
async def submit_upload(
    bg: BackgroundTasks,
    file: UploadFile = File(...),
    _=Security(verify_key),
) -> JobResponse:
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="نوع الملف غير مدعوم")

    job_id = create_job()
    suffix = Path(file.filename or "video.mp4").suffix or ".mp4"
    input_path = Path(settings.TEMP_DIR) / f"{job_id}_input{suffix}"
    os.makedirs(settings.TEMP_DIR, exist_ok=True)

    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"حجم الملف يتجاوز {settings.MAX_FILE_SIZE_MB}MB",
        )

    async with aiofiles.open(input_path, "wb") as f:
        await f.write(content)

    bg.add_task(extract_video_file, job_id, str(input_path))
    return JobResponse(job_id=job_id, status="pending")
