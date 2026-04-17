"""
summarizer.py - AI summarization using Google Gemini API.
"""

import os
import re
import json


def _call_gemini(prompt: str) -> str:
    """Call Google Gemini API."""
    try:
        import google.generativeai as genai
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not set in .env file")
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        raise RuntimeError(f"Gemini API error: {e}")


def generate_summary(transcript_data: dict, video_id: str, progress_callback=None) -> dict:
    """
    Generate a full summary from transcript data using Google Gemini.
    """
    def _progress(step, pct):
        if progress_callback:
            progress_callback(step, pct)

    full_text = transcript_data.get("full_text", "")
    if not full_text:
        return {"error": "No transcript available"}

    # Trim transcript if too long
    if len(full_text) > 12000:
        full_text = full_text[:12000] + "..."

    _progress("Generating summary with Gemini...", 20)

    prompt = f"""You are an expert note-taker. Analyze this YouTube video transcript and return a JSON object.

Transcript:
{full_text}

Return ONLY a valid JSON object with exactly these fields:
{{
  "executive_summary": "2-3 paragraph summary of the entire video",
  "key_themes": ["theme 1", "theme 2", "theme 3"],
  "key_points": [
    {{
      "title": "Short title",
      "explanation": "1-2 sentence explanation",
      "type": "concept",
      "timestamp": "0:00",
      "quote": ""
    }}
  ],
  "notable_insights": ["insight 1", "insight 2"],
  "action_items": ["action 1", "action 2"],
  "detailed_notes": "Detailed markdown notes about the video content",
  "quiz": [
    {{
      "question": "A question about the video",
      "type": "mcq",
      "options": ["A) option1", "B) option2", "C) option3", "D) option4"],
      "correct_index": 0,
      "explanation": "Why this is correct"
    }}
  ]
}}

Return ONLY the JSON. No extra text."""

    _progress("Waiting for Gemini response...", 50)

    try:
        raw = _call_gemini(prompt)

        # Clean up response - remove markdown code blocks if present
        raw = raw.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```[a-z]*\n?", "", raw)
            raw = re.sub(r"```$", "", raw)
            raw = raw.strip()

        _progress("Parsing summary...", 80)

        data = json.loads(raw)
        data["model_used"] = "Gemini 1.5 Flash"
        data["chunk_count"] = 1

        # Sanitize all string fields to remove emojis
        def clean(obj):
            if isinstance(obj, str):
                return obj.encode('ascii', 'ignore').decode('ascii')
            elif isinstance(obj, list):
                return [clean(i) for i in obj]
            elif isinstance(obj, dict):
                return {k: clean(v) for k, v in obj.items()}
            return obj

        data = clean(data)
        return data

    except json.JSONDecodeError:
        _progress("Using plain text summary...", 80)
        return {
            "executive_summary": raw,
            "key_themes": [],
            "key_points": [],
            "notable_insights": [],
            "action_items": [],
            "detailed_notes": raw,
            "quiz": [],
            "model_used": "Gemini 1.5 Flash",
            "chunk_count": 1,
        }
    except Exception as e:
        return {
            "executive_summary": f"Summary generation failed: {e}",
            "key_themes": [],
            "key_points": [],
            "notable_insights": [],
            "action_items": [],
            "detailed_notes": "",
            "quiz": [],
            "model_used": "Gemini 1.5 Flash",
            "chunk_count": 1,
        }