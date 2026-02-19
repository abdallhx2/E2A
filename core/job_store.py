import uuid
import time
from typing import Dict, Optional
from models import JobStatus

_store: Dict[str, dict] = {}


def create_job() -> str:
    job_id = str(uuid.uuid4())
    _store[job_id] = {
        "status":     JobStatus.pending,
        "created_at": time.time(),
        "file_path":  None,
        "error":      None,
        "title":      None,
        "duration":   None,
    }
    return job_id


def update_job(job_id: str, **kwargs) -> None:
    if job_id in _store:
        _store[job_id].update(kwargs)


def get_job(job_id: str) -> Optional[dict]:
    return _store.get(job_id)


def delete_job(job_id: str) -> None:
    _store.pop(job_id, None)


def get_all_jobs() -> Dict[str, dict]:
    return _store
