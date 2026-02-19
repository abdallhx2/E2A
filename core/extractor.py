import os
import sys
import shutil
import asyncio
from pathlib import Path
from config import settings
from core.job_store import update_job
from models import JobStatus


_PYTHON_PACKAGES = {"yt-dlp": "yt_dlp"}


def _resolve_bin(name: str) -> list[str]:
    """Find binary: python -m for Python packages, PATH for system binaries."""
    if name in _PYTHON_PACKAGES:
        return [sys.executable, "-m", _PYTHON_PACKAGES[name]]
    found = shutil.which(name)
    if found:
        return [found]
    raise FileNotFoundError(f"'{name}' not found. Install it or add to PATH.")


async def extract_youtube(job_id: str, url: str, start_sec=None, end_sec=None) -> None:
    """يُشغَّل كـ background task"""
    output_path = Path(settings.TEMP_DIR) / f"{job_id}.%(ext)s"
    os.makedirs(settings.TEMP_DIR, exist_ok=True)
    update_job(job_id, status=JobStatus.processing)

    cmd = [
        *_resolve_bin("yt-dlp"),
        "--extract-audio",
        "--audio-format", settings.AUDIO_FORMAT,
        "--audio-quality", settings.AUDIO_QUALITY,
        "--max-filesize", f"{settings.MAX_FILE_SIZE_MB}m",
        "--match-filter", f"duration <= {settings.MAX_DURATION_SECONDS}",
        "--no-playlist",
        "--output", str(output_path),
        "--print", "title",
        "--no-simulate",          # --print implies --simulate by default; override it
    ]

    if settings.COOKIES_FILE:
        cmd += ["--cookies", settings.COOKIES_FILE]
    if settings.PROXY:
        cmd += ["--proxy", settings.PROXY]

    cmd.append(str(url))

    clip = settings.AUDIO_CLIP_SECONDS
    if start_sec is not None or end_sec is not None:
        s = start_sec or 0
        e = end_sec or "inf"
        if clip and e == "inf":
            e = s + clip
        elif clip and isinstance(e, (int, float)):
            e = min(e, s + clip)
        cmd += ["--download-sections", f"*{s}-{e}"]
    elif clip:
        cmd += ["--download-sections", f"*0-{clip}"]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)

        if proc.returncode != 0:
            raise RuntimeError(stderr.decode("utf-8", errors="replace")[:500])

        final_path = Path(settings.TEMP_DIR) / f"{job_id}.{settings.AUDIO_FORMAT}"
        # yt-dlp prints title first, then may print other lines — take first non-empty line
        title = next(
            (line for line in stdout.decode("utf-8", errors="replace").strip().splitlines() if line.strip()),
            "unknown"
        )

        duration = await _get_duration(final_path)

        update_job(
            job_id,
            status=JobStatus.done,
            file_path=str(final_path),
            title=title,
            duration=duration,
        )
    except Exception as e:
        update_job(job_id, status=JobStatus.failed, error=str(e))


async def extract_video_file(job_id: str, input_path: str) -> None:
    """تحويل ملف فيديو مرفوع إلى صوت"""
    update_job(job_id, status=JobStatus.processing)
    output_path = Path(settings.TEMP_DIR) / f"{job_id}.{settings.AUDIO_FORMAT}"

    clip_args = ["-t", str(settings.AUDIO_CLIP_SECONDS)] if settings.AUDIO_CLIP_SECONDS else []
    cmd = [
        *_resolve_bin("ffmpeg"), "-i", input_path,
        *clip_args,
        "-vn",
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
        "-acodec", "libmp3lame",
        "-ab", settings.AUDIO_QUALITY,
        "-ar", "44100",
        "-y",
        str(output_path),
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)

        if proc.returncode != 0:
            raise RuntimeError(stderr.decode("utf-8", errors="replace")[:500])

        duration = await _get_duration(output_path)
        update_job(
            job_id,
            status=JobStatus.done,
            file_path=str(output_path),
            duration=duration,
        )
    except Exception as e:
        update_job(job_id, status=JobStatus.failed, error=str(e))
    finally:
        if os.path.exists(input_path):
            os.remove(input_path)


async def _get_duration(file_path: Path) -> float | None:
    try:
        proc = await asyncio.create_subprocess_exec(
            *_resolve_bin("ffprobe"), "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(file_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await proc.communicate()
        return float(stdout.decode().strip())
    except Exception:
        return None
