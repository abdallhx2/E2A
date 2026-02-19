from pydantic import BaseModel, HttpUrl
from enum import Enum
from typing import Optional


class JobStatus(str, Enum):
    pending    = "pending"
    processing = "processing"
    done       = "done"
    failed     = "failed"


class JobResponse(BaseModel):
    job_id:    str
    status:    JobStatus
    error:     Optional[str] = None
    audio_url: Optional[str] = None   # متاح عند status=done
    duration:  Optional[float] = None # مدة الصوت بالثواني
    title:     Optional[str] = None   # عنوان الفيديو


class YoutubeRequest(BaseModel):
    url:       HttpUrl
    start_sec: Optional[int] = None   # قص: من ثانية كذا
    end_sec:   Optional[int] = None   # قص: إلى ثانية كذا
