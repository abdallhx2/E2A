from fastapi import APIRouter, BackgroundTasks, Security, HTTPException
from fastapi.security.api_key import APIKeyHeader
from models import YoutubeRequest, JobResponse
from core.job_store import create_job, get_job
from core.extractor import extract_youtube
from config import settings

router = APIRouter(prefix="/extract", tags=["extract"])
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


def verify_key(key: str = Security(api_key_header)) -> None:
    if key != settings.API_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.post("/youtube", response_model=JobResponse, status_code=202)
async def submit_youtube(
    req: YoutubeRequest,
    bg: BackgroundTasks,
    _=Security(verify_key),
) -> JobResponse:
    job_id = create_job()
    bg.add_task(extract_youtube, job_id, str(req.url), req.start_sec, req.end_sec)
    return JobResponse(job_id=job_id, status="pending")
