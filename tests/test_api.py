"""
Tests for the Audio Extraction Service.
Run with: pytest tests/ -v
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
import sys
import os

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import app
from core.job_store import create_job, update_job, get_job, delete_job, get_all_jobs
from models import JobStatus

API_KEY = "dev-secret-key-change-in-production"
HEADERS = {"X-API-Key": API_KEY}

client = TestClient(app)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Job store unit tests
# ---------------------------------------------------------------------------

def test_create_and_get_job():
    job_id = create_job()
    job = get_job(job_id)
    assert job is not None
    assert job["status"] == JobStatus.pending
    assert job["file_path"] is None
    delete_job(job_id)


def test_update_job():
    job_id = create_job()
    update_job(job_id, status=JobStatus.done, title="Test Title")
    job = get_job(job_id)
    assert job["status"] == JobStatus.done
    assert job["title"] == "Test Title"
    delete_job(job_id)


def test_delete_job():
    job_id = create_job()
    delete_job(job_id)
    assert get_job(job_id) is None


def test_get_all_jobs():
    job_id = create_job()
    all_jobs = get_all_jobs()
    assert job_id in all_jobs
    delete_job(job_id)


# ---------------------------------------------------------------------------
# Authentication tests
# ---------------------------------------------------------------------------

def test_youtube_missing_api_key():
    res = client.post("/extract/youtube", json={"url": "https://www.youtube.com/watch?v=test"})
    assert res.status_code == 403


def test_youtube_wrong_api_key():
    res = client.post(
        "/extract/youtube",
        json={"url": "https://www.youtube.com/watch?v=test"},
        headers={"X-API-Key": "wrong-key"},
    )
    assert res.status_code == 403


# ---------------------------------------------------------------------------
# YouTube submission (background task mocked)
# ---------------------------------------------------------------------------

def test_submit_youtube_returns_pending():
    with patch("routes.youtube.extract_youtube", new_callable=AsyncMock) as mock_extract:
        res = client.post(
            "/extract/youtube",
            json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
            headers=HEADERS,
        )
    assert res.status_code == 202
    data = res.json()
    assert data["status"] == "pending"
    assert "job_id" in data
    # cleanup
    delete_job(data["job_id"])


def test_submit_youtube_with_time_range():
    with patch("routes.youtube.extract_youtube", new_callable=AsyncMock):
        res = client.post(
            "/extract/youtube",
            json={
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "start_sec": 10,
                "end_sec": 60,
            },
            headers=HEADERS,
        )
    assert res.status_code == 202
    data = res.json()
    assert data["status"] == "pending"
    delete_job(data["job_id"])


# ---------------------------------------------------------------------------
# Job status endpoint
# ---------------------------------------------------------------------------

def test_job_status_not_found():
    res = client.get("/jobs/nonexistent-job-id")
    assert res.status_code == 404


def test_job_status_pending():
    job_id = create_job()
    res = client.get(f"/jobs/{job_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "pending"
    assert data["audio_url"] is None
    delete_job(job_id)


def test_job_status_done_has_audio_url():
    job_id = create_job()
    update_job(job_id, status=JobStatus.done, file_path="/tmp/fake.mp3", duration=120.0, title="Test")
    res = client.get(f"/jobs/{job_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "done"
    assert data["audio_url"] == f"/jobs/{job_id}/download"
    assert data["duration"] == 120.0
    assert data["title"] == "Test"
    delete_job(job_id)


def test_job_status_failed():
    job_id = create_job()
    update_job(job_id, status=JobStatus.failed, error="something went wrong")
    res = client.get(f"/jobs/{job_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "failed"
    assert data["error"] == "something went wrong"
    delete_job(job_id)


# ---------------------------------------------------------------------------
# Download endpoint
# ---------------------------------------------------------------------------

def test_download_not_found():
    res = client.get("/jobs/nonexistent/download")
    assert res.status_code == 404


def test_download_job_not_done():
    job_id = create_job()
    res = client.get(f"/jobs/{job_id}/download")
    assert res.status_code == 404
    delete_job(job_id)


def test_download_file_missing_from_disk():
    job_id = create_job()
    update_job(job_id, status=JobStatus.done, file_path="/tmp/nonexistent_audio.mp3")
    res = client.get(f"/jobs/{job_id}/download")
    assert res.status_code == 404
    delete_job(job_id)


def test_download_success(tmp_path):
    fake_mp3 = tmp_path / "test.mp3"
    fake_mp3.write_bytes(b"\xff\xfb\x90\x00" * 100)  # fake MP3 header bytes

    job_id = create_job()
    update_job(job_id, status=JobStatus.done, file_path=str(fake_mp3))
    res = client.get(f"/jobs/{job_id}/download")
    assert res.status_code == 200
    assert res.headers["content-type"] == "audio/mpeg"
    delete_job(job_id)


# ---------------------------------------------------------------------------
# Upload endpoint
# ---------------------------------------------------------------------------

def test_upload_wrong_content_type():
    with patch("routes.upload.extract_video_file", new_callable=AsyncMock):
        res = client.post(
            "/extract/upload",
            files={"file": ("test.txt", b"hello", "text/plain")},
            headers=HEADERS,
        )
    assert res.status_code == 400


def test_upload_valid_file():
    with patch("routes.upload.extract_video_file", new_callable=AsyncMock):
        res = client.post(
            "/extract/upload",
            files={"file": ("video.mp4", b"\x00" * 100, "video/mp4")},
            headers=HEADERS,
        )
    assert res.status_code == 202
    data = res.json()
    assert data["status"] == "pending"
    delete_job(data["job_id"])
