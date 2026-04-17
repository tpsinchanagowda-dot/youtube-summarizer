"""
utils.py — Shared helper functions used across all modules.
"""

import re
import os
import hashlib
import json
from datetime import datetime
from pathlib import Path


# ─────────────────────────────────────────
# URL / Video ID Helpers
# ─────────────────────────────────────────

def extract_video_id(url: str) -> str | None:
    """
    Extract YouTube video ID from any valid YouTube URL format.
    
    Supports:
      - https://www.youtube.com/watch?v=VIDEO_ID
      - https://youtu.be/VIDEO_ID
      - https://youtube.com/shorts/VIDEO_ID
      - https://www.youtube.com/embed/VIDEO_ID
    
    Returns None if no valid ID found.
    """
    patterns = [
        r'(?:v=)([a-zA-Z0-9_-]{11})',           # ?v=ID
        r'youtu\.be/([a-zA-Z0-9_-]{11})',         # youtu.be/ID
        r'shorts/([a-zA-Z0-9_-]{11})',             # shorts/ID
        r'embed/([a-zA-Z0-9_-]{11})',              # embed/ID
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def is_valid_youtube_url(url: str) -> bool:
    """Return True if the URL looks like a valid YouTube video URL."""
    return extract_video_id(url) is not None


def build_youtube_url(video_id: str) -> str:
    """Build a standard YouTube watch URL from a video ID."""
    return f"https://www.youtube.com/watch?v={video_id}"


def build_timestamp_url(video_id: str, seconds: float) -> str:
    """Build a YouTube URL that jumps to a specific timestamp."""
    t = int(seconds)
    return f"https://www.youtube.com/watch?v={video_id}&t={t}s"


def format_timestamp(seconds: float) -> str:
    """
    Convert seconds to MM:SS or HH:MM:SS string.
    
    Examples:
      65    → "1:05"
      3665  → "1:01:05"
    """
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


# ─────────────────────────────────────────
# Token Counting
# ─────────────────────────────────────────

def estimate_tokens(text: str) -> int:
    """
    Quick token count estimate without importing tiktoken.
    Rule of thumb: ~1 token per 4 characters for English text.
    For accuracy, use tiktoken (imported conditionally below).
    """
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        # Fallback: rough estimate
        return len(text) // 4


# ─────────────────────────────────────────
# Cache Helpers
# ─────────────────────────────────────────

def get_cache_dir() -> Path:
    """Return the cache directory path, creating it if needed."""
    cache_dir = Path("cache")
    cache_dir.mkdir(exist_ok=True)
    return cache_dir


def make_cache_key(video_id: str, suffix: str = "") -> str:
    """
    Create a cache filename from a video_id.
    suffix can be 'transcript', 'summary', etc.
    """
    key = f"{video_id}_{suffix}" if suffix else video_id
    return hashlib.md5(key.encode()).hexdigest()


def save_to_cache(video_id: str, data: dict, suffix: str = "") -> Path:
    """Save a dict to a JSON cache file. Returns the file path."""
    cache_dir = get_cache_dir()
    key = make_cache_key(video_id, suffix)
    cache_file = cache_dir / f"{key}.json"
    
    payload = {
        "video_id": video_id,
        "cached_at": datetime.now().isoformat(),
        "data": data
    }
    cache_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    return cache_file


def load_from_cache(video_id: str, suffix: str = "", ttl_days: int = 7) -> dict | None:
    """
    Load data from cache if it exists and is not expired.
    Returns the 'data' dict or None if cache miss / expired.
    """
    cache_dir = get_cache_dir()
    key = make_cache_key(video_id, suffix)
    cache_file = cache_dir / f"{key}.json"

    if not cache_file.exists():
        return None

    try:
        payload = json.loads(cache_file.read_text())
        cached_at = datetime.fromisoformat(payload["cached_at"])
        age_days = (datetime.now() - cached_at).days
        if age_days > ttl_days:
            cache_file.unlink()  # Delete expired cache
            return None
        return payload["data"]
    except Exception:
        return None


# ─────────────────────────────────────────
# Text Utilities
# ─────────────────────────────────────────

def sanitize_text(text: str) -> str:
    """
    Remove emojis and non-ASCII characters that cause charmap encoding errors on Windows.
    Keeps standard Latin characters, punctuation, and common symbols.
    """
    if not text:
        return text
    # Encode to ASCII ignoring unencodable chars (emojis, special unicode), then decode back
    return text.encode('ascii', 'ignore').decode('ascii')


def clean_transcript_text(text: str) -> str:
    """
    Light cleanup of raw transcript text:
    - Remove repeated spaces
    - Remove common filler transcription artifacts
    - Normalize line breaks
    """
    # Remove multiple spaces
    text = re.sub(r' +', ' ', text)
    # Remove [Music], [Applause] etc.
    text = re.sub(r'\[[\w\s]+\]', '', text)
    # Normalize newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def chunk_text(text: str, max_tokens: int = 2000, overlap_tokens: int = 150) -> list[dict]:
    """
    Split text into chunks suitable for LLM processing.
    
    Args:
        text: Full text to split
        max_tokens: Maximum tokens per chunk
        overlap_tokens: Token overlap between chunks (preserves context)
    
    Returns:
        List of dicts: [{"text": "...", "chunk_index": 0, "total_chunks": N}]
    """
    # Split into sentences (simple split on ". ")
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    chunks = []
    current_sentences = []
    current_tokens = 0

    for sentence in sentences:
        s_tokens = estimate_tokens(sentence)

        if current_tokens + s_tokens > max_tokens and current_sentences:
            # Save current chunk
            chunks.append(" ".join(current_sentences))

            # Keep last few sentences for overlap
            overlap_text = ""
            overlap_count = 0
            for s in reversed(current_sentences):
                if estimate_tokens(overlap_text + s) < overlap_tokens:
                    overlap_text = s + " " + overlap_text
                    overlap_count += 1
                else:
                    break
            current_sentences = current_sentences[-overlap_count:] if overlap_count else []
            current_tokens = estimate_tokens(" ".join(current_sentences))

        current_sentences.append(sentence)
        current_tokens += s_tokens

    if current_sentences:
        chunks.append(" ".join(current_sentences))

    total = len(chunks)
    return [
        {"text": chunk, "chunk_index": i, "total_chunks": total}
        for i, chunk in enumerate(chunks)
    ]


def chunk_transcript_segments(segments: list[dict], max_tokens: int = 2000, overlap_tokens: int = 150) -> list[dict]:
    """
    Split transcript segments (with timestamps) into token-limited chunks.
    Preserves timestamp information for each chunk.
    
    Args:
        segments: List of {"text": "...", "start": 12.5, "duration": 3.0}
    
    Returns:
        List of chunks with start/end timestamps preserved.
    """
    chunks = []
    current_segments = []
    current_tokens = 0

    for seg in segments:
        seg_tokens = estimate_tokens(seg.get("text", ""))

        if current_tokens + seg_tokens > max_tokens and current_segments:
            # Build chunk
            chunk_text_joined = " ".join(s["text"] for s in current_segments)
            chunks.append({
                "text": clean_transcript_text(chunk_text_joined),
                "start_time": current_segments[0]["start"],
                "end_time": current_segments[-1]["start"] + current_segments[-1].get("duration", 0),
                "chunk_index": len(chunks),
            })

            # Overlap: keep last N segments
            overlap_segs = []
            overlap_tok = 0
            for s in reversed(current_segments):
                t = estimate_tokens(s["text"])
                if overlap_tok + t < overlap_tokens:
                    overlap_segs.insert(0, s)
                    overlap_tok += t
                else:
                    break
            current_segments = overlap_segs
            current_tokens = overlap_tok

        current_segments.append(seg)
        current_tokens += seg_tokens

    # Last chunk
    if current_segments:
        chunk_text_joined = " ".join(s["text"] for s in current_segments)
        chunks.append({
            "text": clean_transcript_text(chunk_text_joined),
            "start_time": current_segments[0]["start"],
            "end_time": current_segments[-1]["start"] + current_segments[-1].get("duration", 0),
            "chunk_index": len(chunks),
        })

    # Add total_chunks to each
    total = len(chunks)
    for chunk in chunks:
        chunk["total_chunks"] = total

    return chunks


def find_best_timestamp(key_point: str, segments: list[dict]) -> float:
    """
    Find the most relevant timestamp for a key point by
    counting word overlap with transcript segments.
    
    Returns: best matching start time in seconds (0.0 if not found)
    """
    if not segments:
        return 0.0

    kp_words = set(re.findall(r'\w+', key_point.lower()))
    if not kp_words:
        return 0.0

    best_score = 0.0
    best_time = segments[0]["start"]

    for seg in segments:
        seg_words = set(re.findall(r'\w+', seg.get("text", "").lower()))
        overlap = len(kp_words & seg_words)
        score = overlap / max(len(kp_words), 1)
        if score > best_score:
            best_score = score
            best_time = seg["start"]

    return best_time


# ─────────────────────────────────────────
# Misc
# ─────────────────────────────────────────

def ensure_output_dir(dirname: str = "outputs") -> Path:
    """Create and return an output directory."""
    out = Path(dirname)
    out.mkdir(exist_ok=True)
    return out


def sanitize_filename(name: str, max_length: int = 60) -> str:
    """
    Convert a string to a safe filename.
    Removes special chars, replaces spaces with underscores.
    """
    name = re.sub(r'[^\w\s-]', '', name)
    name = re.sub(r'\s+', '_', name.strip())
    return name[:max_length]


def format_duration(total_seconds: int) -> str:
    """Format seconds into human-readable duration string."""
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    if h:
        return f"{h}h {m}m {s}s"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"