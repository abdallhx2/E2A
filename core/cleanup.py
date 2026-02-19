import asyncio
import os
import time
from config import settings
from core.job_store import get_all_jobs, delete_job


async def cleanup_loop() -> None:
    """يعمل كل 10 دقائق، يحذف الوظائف المنتهية الصلاحية"""
    while True:
        await asyncio.sleep(600)
        now = time.time()
        for job_id, job in list(get_all_jobs().items()):
            if now - job["created_at"] > settings.JOB_TTL_SECONDS:
                file_path = job.get("file_path")
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
                delete_job(job_id)
