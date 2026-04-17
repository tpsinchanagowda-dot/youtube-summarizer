"""
transcript.py — Transcript extraction with tiered fallback.
"""

import os
import re
import json
import tempfile
from pathlib import Path

from utils import clean_transcript_text


def _sanitize(text: str) -> str:
    """Remove emojis and non-ASCII characters to prevent charmap errors on Windows."""
    if not text:
        return ""
    return text.encode('ascii', 'ignore').decode('ascii')


def _safe_print(msg):
    try:
        print(_sanitize(str(msg)))
    except Exception:
        pass


def get_transcript(video_id: str, language: str = "en") -> dict:
    errors = []

    _safe_print(f"[Transcript] Tier 1: Trying youtube-transcript-api for {video_id}...")
    try:
        result = _get_via_youtube_transcript_api(video_id, language)
        _safe_print(f"[Transcript] Tier 1 success ({len(result['segments'])} segments)")
        return result
    except Exception as e:
        errors.append(f"Tier1 (youtube-transcript-api): {e}")
        _safe_print(f"[Transcript] Tier 1 failed: {e}")

    _safe_print(f"[Transcript] Tier 2: Trying yt-dlp subtitle download...")
    try:
        result = _get_via_ytdlp_subs(video_id, language)
        _safe_print(f"[Transcript] Tier 2 success ({len(result['segments'])} segments)")
        return result
    except Exception as e:
        errors.append(f"Tier2 (yt-dlp subs): {e}")
        _safe_print(f"[Transcript] Tier 2 failed: {e}")

    raise RuntimeError(
        "All transcript extraction methods failed.\n"
        + "\n".join(errors)
        + "\n\nSolutions:\n"
        + "1. Make sure the video is public and has captions/subtitles enabled\n"
        + "2. Try a different video\n"
        + "3. Run: pip install --upgrade youtube-transcript-api yt-dlp"
    )


def _get_via_youtube_transcript_api(video_id: str, language: str = "en") -> dict:
    """Works with youtube-transcript-api version 1.x"""
    from youtube_transcript_api import YouTubeTranscriptApi

    try:
        ytt_api = YouTubeTranscriptApi()
        transcript_list = ytt_api.list(video_id)

        transcript = None
        try:
            transcript = transcript_list.find_manually_created_transcript([language])
        except Exception:
            try:
                transcript = transcript_list.find_generated_transcript([language])
            except Exception:
                try:
                    transcript = transcript_list.find_generated_transcript(['en'])
                except Exception:
                    for t in transcript_list:
                        transcript = t
                        break

        if transcript is None:
            raise RuntimeError("No transcript found")

        fetched = transcript.fetch()

        segments = []
        for seg in fetched:
            if hasattr(seg, 'text'):
                segments.append({
                    "text": _sanitize(seg.text.strip()),
                    "start": float(seg.start),
                    "duration": float(getattr(seg, 'duration', 0)),
                })
            elif isinstance(seg, dict):
                segments.append({
                    "text": _sanitize(seg.get("text", "").strip()),
                    "start": float(seg.get("start", 0)),
                    "duration": float(seg.get("duration", 0)),
                })

        segments = [s for s in segments if s["text"]]
        full_text = _sanitize(clean_transcript_text(" ".join(s["text"] for s in segments)))
        duration = segments[-1]["start"] + segments[-1]["duration"] if segments else 0

        return {
            "segments": segments,
            "full_text": full_text,
            "language": language,
            "method": "youtube_transcript_api",
            "duration_seconds": int(duration),
        }

    except Exception as e:
        raise RuntimeError(f"youtube-transcript-api error: {e}")


def _get_via_ytdlp_subs(video_id: str, language: str = "en") -> dict:
    import yt_dlp

    url = f"https://www.youtube.com/watch?v={video_id}"

    with tempfile.TemporaryDirectory() as tmpdir:
        ydl_opts = {
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": [language, "en", "en-US", "a.en"],
            "subtitlesformat": "json3",
            "outtmpl": os.path.join(tmpdir, "%(id)s.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "sleep_interval": 2,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_title = info.get("title", video_id) if info else video_id
            video_duration = info.get("duration", 0) if info else 0

        sub_files = list(Path(tmpdir).glob(f"*.{language}.json3"))
        if not sub_files:
            sub_files = list(Path(tmpdir).glob("*.json3"))
        if not sub_files:
            raise RuntimeError("No subtitle files downloaded by yt-dlp")

        sub_data = json.loads(sub_files[0].read_text(encoding="utf-8"))

    segments = _parse_json3_subs(sub_data)
    full_text = _sanitize(clean_transcript_text(" ".join(s["text"] for s in segments)))
    video_title = _sanitize(video_title)
    if not video_title:
        video_title = f"Video {video_id}"

    return {
        "segments": segments,
        "full_text": full_text,
        "language": language,
        "method": "ytdlp_subs",
        "duration_seconds": int(video_duration),
        "title": video_title,
    }


def _parse_json3_subs(sub_data: dict) -> list:
    segments = []
    for event in sub_data.get("events", []):
        if "segs" not in event:
            continue
        text = "".join(seg.get("utf8", "") for seg in event["segs"]).strip()
        text = re.sub(r'<[^>]+>', '', text)
        text = _sanitize(text)
        if not text or text == "\n":
            continue
        start_ms = event.get("tStartMs", 0)
        dur_ms = event.get("dDurationMs", 0)
        segments.append({
            "text": text,
            "start": start_ms / 1000.0,
            "duration": dur_ms / 1000.0,
        })
    return segments


def get_video_info(video_id: str) -> dict:
    import yt_dlp
    url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "no_warnings": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        title = info.get("title", "Unknown Title")
        title = _sanitize(title).strip()
        if not title:
            title = f"Video {video_id}"

        return {
            "title": title,
            "channel": _sanitize(info.get("uploader", "Unknown Channel")),
            "duration_seconds": info.get("duration", 0),
            "view_count": info.get("view_count", 0),
            "upload_date": info.get("upload_date", ""),
            "thumbnail": info.get("thumbnail", ""),
            "description": _sanitize((info.get("description", "") or "")[:500]),
        }
    except Exception as e:
        return {"title": f"Video {video_id}", "error": str(e)}