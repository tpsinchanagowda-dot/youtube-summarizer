"""
backend.py — Core pipeline logic that wires together all modules.

This can be used in two ways:
  1. Direct import: from backend import process_video
  2. As a FastAPI server: uvicorn backend:app --reload

The process_video() function is the single entry point for the app.py UI.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

from utils import (
    extract_video_id,
    is_valid_youtube_url,
    load_from_cache,
    save_to_cache,
)
from transcript import get_transcript, get_video_info
from summarizer import generate_summary
from exporter import export_both, generate_markdown

load_dotenv()


# ─────────────────────────────────────────
# Core Pipeline Function
# ─────────────────────────────────────────

def process_video(youtube_url: str, progress_callback=None) -> dict:
    """
    Full processing pipeline for a YouTube URL.
    
    Args:
        youtube_url: Any valid YouTube URL
        progress_callback: Optional callable(step: str, pct: int)
    
    Returns dict with keys:
        - video_id, video_info, transcript_data
        - summary_data (executive_summary, key_points, etc.)
        - md_path, pdf_path (file paths of exported docs)
        - from_cache (bool)
        - error (str, only if something failed)
    
    Raises:
        ValueError: If URL is invalid
        RuntimeError: If transcript extraction fails
    """
    def _progress(step, pct):
        if progress_callback:
            progress_callback(step, pct)
        else:
            safe_step = step.encode('ascii', 'ignore').decode('ascii')
            print(f"  [{pct:3d}%] {safe_step}")

    # ── Validate URL ────────────────────
    _progress("Validating URL...", 2)
    if not is_valid_youtube_url(youtube_url):
        raise ValueError(
            f"'{youtube_url}' is not a valid YouTube URL.\n"
            "Supported formats:\n"
            "  https://www.youtube.com/watch?v=VIDEO_ID\n"
            "  https://youtu.be/VIDEO_ID\n"
            "  https://youtube.com/shorts/VIDEO_ID"
        )

    video_id = extract_video_id(youtube_url)
    _progress(f"Processing video ID: {video_id}", 5)

    # ── Check cache ─────────────────────
    cache_enabled = os.getenv("CACHE_ENABLED", "true").lower() == "true"
    cache_ttl = int(os.getenv("CACHE_TTL_DAYS", "7"))

    if cache_enabled:
        cached = load_from_cache(video_id, "full_result", ttl_days=cache_ttl)
        if cached:
            _progress("OK Loaded from cache (instant!)", 100)
            cached["from_cache"] = True
            return cached

    # ── Get video metadata ──────────────
    _progress("Fetching video metadata...", 8)
    video_info = get_video_info(video_id)
    if "error" in video_info:
        print(f"[Backend] Warning: metadata fetch failed: {video_info['error']}")
        video_info = {"title": f"Video {video_id}", "channel": "Unknown", "duration_seconds": 0}

    # ── Extract transcript ──────────────
    _progress("Extracting transcript...", 10)
    transcript_data = get_transcript(video_id)
    
    segments_count = len(transcript_data.get("segments", []))
    method = transcript_data.get("method", "unknown")
    _progress(f"OK Transcript: {segments_count} segments via {method}", 30)

    # ── Generate summary ─────────────────
    _progress("Starting AI summarization...", 32)
    summary_data = generate_summary(
        transcript_data,
        video_id,
        progress_callback=lambda step, pct: _progress(step, 32 + int(pct * 0.55))
    )
    _progress("OK Summary generated", 88)

    # ── Export documents ─────────────────
    _progress("Exporting Markdown & PDF...", 90)
    try:
        md_path, pdf_path = export_both(summary_data, video_info, video_id)
        _progress(f"OK Files saved: {md_path.name}, {pdf_path.name}", 97)
    except Exception as e:
        print(f"[Backend] Export warning: {e}")
        md_path = None
        pdf_path = None

    # ── Build result ─────────────────────
    result = {
        "video_id": video_id,
        "video_info": video_info,
        "transcript_data": {
            "method": transcript_data.get("method"),
            "duration_seconds": transcript_data.get("duration_seconds", 0),
            "segment_count": segments_count,
            "language": transcript_data.get("language", "en"),
            "full_text": transcript_data.get("full_text", ""),
        },
        "summary_data": summary_data,
        "md_path": str(md_path) if md_path else None,
        "pdf_path": str(pdf_path) if pdf_path else None,
        "from_cache": False,
    }

    # ── Save to cache ────────────────────
    if cache_enabled:
        save_to_cache(video_id, result, "full_result")
        _progress("OK Result cached for future requests", 99)

    _progress("Done! Complete!", 100)
    return result


def get_markdown_content(result: dict) -> str:
    """
    Return the Markdown content from a result dict.
    Re-generates if md_path is not available.
    """
    md_path = result.get("md_path")
    if md_path and Path(md_path).exists():
        return Path(md_path).read_text(encoding="utf-8")

    # Re-generate from data
    from exporter import generate_markdown
    return generate_markdown(
        result["summary_data"],
        result["video_info"],
        result["video_id"],
    )


# ─────────────────────────────────────────
# Optional FastAPI Server
# ─────────────────────────────────────────
# Run with: uvicorn backend:app --reload --port 8000
# Then use: http://localhost:8000/docs for interactive API docs
# ─────────────────────────────────────────

try:
    from fastapi import FastAPI, HTTPException, BackgroundTasks
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    import uuid

    app = FastAPI(
        title="YouTube Summarizer API",
        description="Transcribe, summarize, and export YouTube videos",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # In-memory job store (for async processing)
    _jobs: dict = {}

    class SummarizeRequest(BaseModel):
        url: str
        language: str = "en"

    class SummarizeResponse(BaseModel):
        job_id: str
        status: str
        message: str

    @app.get("/")
    def root():
        return {"status": "ok", "message": "YouTube Summarizer API is running"}

    @app.post("/summarize", response_model=SummarizeResponse)
    def summarize(request: SummarizeRequest, bg: BackgroundTasks):
        """Start async summarization job. Poll /status/{job_id} for updates."""
        if not is_valid_youtube_url(request.url):
            raise HTTPException(status_code=400, detail="Invalid YouTube URL")

        job_id = str(uuid.uuid4())[:8]
        _jobs[job_id] = {"status": "processing", "progress": 0, "step": "Starting..."}

        def run_job(job_id, url):
            try:
                def on_progress(step, pct):
                    _jobs[job_id]["step"] = step
                    _jobs[job_id]["progress"] = pct

                result = process_video(url, progress_callback=on_progress)
                _jobs[job_id].update({
                    "status": "done",
                    "result": result,
                    "progress": 100,
                })
            except Exception as e:
                _jobs[job_id].update({"status": "error", "error": str(e)})

        bg.add_task(run_job, job_id, request.url)
        return {"job_id": job_id, "status": "processing", "message": f"Job {job_id} started"}

    @app.get("/status/{job_id}")
    def status(job_id: str):
        """Poll this endpoint to get job progress."""
        if job_id not in _jobs:
            raise HTTPException(status_code=404, detail="Job not found")
        return _jobs[job_id]

    @app.get("/health")
    def health():
        return {"status": "healthy"}

except ImportError: 
    passvenv