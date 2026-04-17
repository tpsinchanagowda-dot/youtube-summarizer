# YouTube Summarizer

> Paste any YouTube URL → Get instant structured notes, key points with timestamps, and PDF/Markdown export. Powered by OpenAI GPT + Whisper.

---

## Features

- **Smart transcript extraction** — 3-tier fallback (YouTube captions → yt-dlp → Whisper)
- **AI summarization** — Chunk-and-merge strategy for videos of any length
- **Key points with timestamps** — Clickable links back to exact video moments
- **PDF & Markdown export** — Professional formatted documents
- **Comprehension quiz** — Auto-generated from summary
- **Caching** — Reprocess same video instantly at zero cost

---

## Quick Start (5 Minutes)

### Prerequisites
- Python 3.10+
- FFmpeg (for Whisper fallback only)
- OpenAI API key

### 1. Clone / Download
```bash
# If using git:
git clone <your-repo-url>
cd yt_summarizer

# Or just navigate to the project folder in VS Code
```

### 2. Create Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure API Key
```bash
# Copy the example env file
cp .env.example .env

# Open .env and add your OpenAI API key:
# OPENAI_API_KEY=sk-your-actual-key-here
```

Get your API key at: https://platform.openai.com/api-keys

### 5. Run the App
```bash
streamlit run app.py
```

The app opens at http://localhost:8501 

---

##Project Structure

```
yt_summarizer/
├── app.py           # Streamlit UI — all UI logic
├── backend.py       # Pipeline orchestrator (also optional FastAPI server)
├── transcript.py    # YouTube transcript + Whisper fallback
├── summarizer.py    # GPT chunk summarization + key point extraction
├── exporter.py      # Markdown + PDF generation
├── utils.py         # Shared helpers (URL parsing, chunking, caching)
├── .env             # Your API keys (never commit this!)
├── .env.example     # Template for .env
├── requirements.txt
├── cache/           # Auto-created: cached summaries
└── outputs/         # Auto-created: exported PDF + MD files
```

---

## How It Works

```
URL Input
   ↓
extract_video_id()          ← utils.py
   ↓
get_video_info()             ← transcript.py (yt-dlp metadata)
   ↓
get_transcript()             ← transcript.py
   Tier 1: youtube-transcript-api
   Tier 2: yt-dlp subtitles
   Tier 3: yt-dlp + Whisper API
   ↓
chunk_transcript_segments()  ← utils.py (2000 token chunks w/ overlap)
   ↓
summarize_chunks()           ← summarizer.py (GPT per chunk)
   ↓
merge_summaries()            ← summarizer.py (GPT final synthesis)
   ↓
extract_key_points()         ← summarizer.py (JSON output + timestamps)
   ↓
generate_quiz()              ← summarizer.py
   ↓
export_both()                ← exporter.py (MD + PDF)
   ↓
Display in Streamlit UI      ← app.py
```

---

##Configuration (.env)

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | required | Your OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o-mini` | Model for final synthesis |
| `OPENAI_CHUNK_MODEL` | `gpt-4o-mini` | Model for per-chunk summary |
| `OPENAI_TEMPERATURE` | `0.3` | Creativity (0=factual, 1=creative) |
| `CACHE_ENABLED` | `true` | Cache results to SQLite |
| `CACHE_TTL_DAYS` | `7` | How long to keep cached results |

---

##Estimated Costs

| Video Length | Method | Estimated Cost |
|---|---|---|
| Any (cached) | Cache hit | **$0.00** |
| 10 min (has captions) | GPT-4o-mini | **~$0.02** |
| 30 min (has captions) | GPT-4o-mini | **~$0.06** |
| 30 min (no captions) | Whisper + GPT-4o-mini | **~$0.24** |
| 30 min (no captions) | Whisper + GPT-4o | **~$0.60** |

---

##Optional: Run as FastAPI Server

```bash
# In one terminal:
uvicorn backend:app --reload --port 8000

# In another terminal:
streamlit run app.py

# API docs available at:
open http://localhost:8000/docs
```

---

##Troubleshooting

**"No transcript found"**
→ Try a different video with enabled captions, or ensure FFmpeg is installed for Whisper fallback.

**"OPENAI_API_KEY not set"**
→ Make sure you copied `.env.example` to `.env` and added your real key.

**"FFmpeg not found"**
→ Install FFmpeg: https://ffmpeg.org/download.html
→ On Windows: `winget install ffmpeg`
→ On Mac: `brew install ffmpeg`
→ On Ubuntu: `sudo apt install ffmpeg`

**PDF export fails**
→ Run: `pip install reportlab Pillow`

**yt-dlp fails**
→ Update yt-dlp: `pip install --upgrade yt-dlp`

---

## Roadmap (Next Features)

- [ ] Semantic search over saved notes (ChromaDB + embeddings)
- [ ] Multi-language support UI
- [ ] Playlist batch processing
- [ ] Notion / Slack export integration
- [ ] User accounts + history (PostgreSQL migration)
- [ ] Chrome extension

---

## License

MIT — free to use, modify, and distribute.
