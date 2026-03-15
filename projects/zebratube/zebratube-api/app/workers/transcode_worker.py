"""
workers/transcode_worker.py — media validation, thumbnail, and transcode

Called as a background task after a submission upload.
Produces:
    - Normalised MP4 preview (720p, libx264, fast preset)
    - Thumbnail (first frame or waveform image for audio)
    - media_metadata dict stored back to submission row

Usage (standalone):
    python3 -m app.workers.transcode_worker \\
        --submission-id <uuid> \\
        --input-path    /path/to/upload.mp4

Usage (from FastAPI background task):
    from app.workers.transcode_worker import transcode_submission
    background_tasks.add_task(transcode_submission, submission_id, input_path)
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.db import get_db_session
from app.models.schema import Submission, SubmissionStatus

MEDIA_ROOT  = Path(os.environ.get("MEDIA_ROOT", "/tmp/zebratube/media"))
PREVIEW_DIR = MEDIA_ROOT / "previews"
THUMB_DIR   = MEDIA_ROOT / "thumbnails"

VIDEO_EXTS  = {".mp4", ".webm", ".mov", ".avi", ".mkv"}
AUDIO_EXTS  = {".mp3", ".wav", ".ogg", ".flac", ".m4a"}
IMAGE_EXTS  = {".png", ".jpg", ".jpeg", ".svg", ".gif"}


# ── ffprobe ───────────────────────────────────────────────────────────────────

def probe(path: Path) -> dict:
    """Run ffprobe and return stream metadata."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_streams", "-show_format", str(path)],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return {}
        return json.loads(result.stdout)
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return {}


def extract_metadata(path: Path, probe_data: dict) -> dict:
    fmt     = probe_data.get("format", {})
    streams = probe_data.get("streams", [])
    video   = next((s for s in streams if s.get("codec_type") == "video"), {})
    audio   = next((s for s in streams if s.get("codec_type") == "audio"), {})

    return {
        "file_size":   path.stat().st_size,
        "duration_s":  float(fmt.get("duration", 0)),
        "format":      fmt.get("format_name", ""),
        "width":       video.get("width"),
        "height":      video.get("height"),
        "video_codec": video.get("codec_name"),
        "audio_codec": audio.get("codec_name"),
        "fps":         video.get("r_frame_rate", ""),
    }


# ── transcode ─────────────────────────────────────────────────────────────────

def transcode_video(input_path: Path, output_path: Path) -> bool:
    """Transcode to H.264 720p preview. Returns True on success."""
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(
            [
                "ffmpeg", "-y", "-i", str(input_path),
                "-vf", "scale=-2:720",
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "aac", "-b:a", "128k",
                "-movflags", "+faststart",
                str(output_path),
            ],
            capture_output=True, timeout=300,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def extract_thumbnail(input_path: Path, thumb_path: Path, ext: str) -> bool:
    """Extract first frame (video) or generate waveform image (audio)."""
    THUMB_DIR.mkdir(parents=True, exist_ok=True)
    try:
        if ext in VIDEO_EXTS:
            result = subprocess.run(
                ["ffmpeg", "-y", "-i", str(input_path),
                 "-vframes", "1", "-vf", "scale=320:-2", str(thumb_path)],
                capture_output=True, timeout=30,
            )
            return result.returncode == 0
        elif ext in AUDIO_EXTS:
            # Simple waveform via ffmpeg showwavespic
            result = subprocess.run(
                ["ffmpeg", "-y", "-i", str(input_path),
                 "-filter_complex", "showwavespic=s=320x80:colors=#6688ff",
                 "-frames:v", "1", str(thumb_path)],
                capture_output=True, timeout=30,
            )
            return result.returncode == 0
        return False
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


# ── main transcode task ───────────────────────────────────────────────────────

def transcode_submission(submission_id: str, input_path: str) -> None:
    """
    Full processing pipeline for one submission.
    Updates the Submission row with paths and metadata when complete.
    """
    input_path = Path(input_path)
    ext        = input_path.suffix.lower()

    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    THUMB_DIR.mkdir(parents=True, exist_ok=True)

    preview_path = None
    thumb_path   = None
    metadata     = {}
    success      = True

    # Probe
    probe_data = probe(input_path)
    if probe_data:
        metadata = extract_metadata(input_path, probe_data)

    # Transcode video → preview
    if ext in VIDEO_EXTS:
        p = PREVIEW_DIR / f"{submission_id}_preview.mp4"
        if transcode_video(input_path, p):
            preview_path = str(p)
        else:
            # Fall back to original
            preview_path = str(input_path)
            success = False

    elif ext in AUDIO_EXTS:
        # Audio: no transcode needed, just copy reference
        preview_path = str(input_path)

    elif ext in IMAGE_EXTS:
        preview_path = str(input_path)

    # Thumbnail
    if ext in VIDEO_EXTS | AUDIO_EXTS:
        t = THUMB_DIR / f"{submission_id}_thumb.png"
        if extract_thumbnail(input_path, t, ext):
            thumb_path = str(t)

    # Update submission row
    db = get_db_session()
    try:
        sub = db.query(Submission).filter_by(id=submission_id).first()
        if sub:
            sub.preview_path  = preview_path
            sub.thumbnail_path= thumb_path
            sub.media_metadata= metadata
            sub.status        = SubmissionStatus.pending  # ready for review
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    status = "ok" if success else "partial (transcode failed, original preserved)"
    print(f"transcode_submission {submission_id}: {status}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--submission-id", required=True)
    ap.add_argument("--input-path",    required=True)
    args = ap.parse_args()
    transcode_submission(args.submission_id, args.input_path)


if __name__ == "__main__":
    main()
