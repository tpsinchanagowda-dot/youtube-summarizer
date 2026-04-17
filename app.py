"""
app.py — Streamlit UI for the YouTube Summarizer.

Run with: streamlit run app.py

This file contains ALL the UI logic. It calls backend.process_video()
which internally uses transcript.py, summarizer.py, and exporter.py.
"""
import sys
import io
import os

os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONUTF8"] = "1"

import time
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
import sys
import io
# Force UTF-8 output to prevent emoji/charmap errors on Windows
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONUTF8"] = "1"
import os
os.environ["PYTHONIOENCODING"] = "utf-8"

import time
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# Add current directory to path so imports work
sys.path.insert(0, str(Path(__file__).parent))

from backend import process_video, get_markdown_content
from utils import (
    is_valid_youtube_url,
    extract_video_id,
    format_duration,
    build_youtube_url,
)


# ─────────────────────────────────────────
# Page Config (MUST be first Streamlit call)
# ─────────────────────────────────────────

st.set_page_config(
    page_title="YouTube Summarizer",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ─────────────────────────────────────────
# Custom CSS
# ─────────────────────────────────────────

st.markdown("""
<style>
/* ── Main app background ── */
.stApp {
    background-color: #0f0f13;
    color: #e8e8e0;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background-color: #16161e;
    border-right: 1px solid #2a2a38;
}

/* ── Input box ── */
.stTextInput input {
    background-color: #1e1e2e !important;
    color: #e8e8e0 !important;
    border: 1px solid #3a3a4e !important;
    border-radius: 6px !important;
    font-size: 15px !important;
    padding: 10px 14px !important;
}

.stTextInput input:focus {
    border-color: #c8f060 !important;
    box-shadow: 0 0 0 2px rgba(200,240,96,0.15) !important;
}

/* ── Primary button ── */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #c8f060, #a0d040) !important;
    color: #0f0f13 !important;
    font-weight: 700 !important;
    border: none !important;
    border-radius: 6px !important;
    padding: 10px 28px !important;
    font-size: 15px !important;
    transition: all 0.2s !important;
}

.stButton > button[kind="primary"]:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 16px rgba(200,240,96,0.3) !important;
}

/* ── Cards / metric boxes ── */
[data-testid="metric-container"] {
    background: #1e1e2e;
    border: 1px solid #2a2a38;
    border-radius: 8px;
    padding: 16px;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: #16161e;
    border-bottom: 1px solid #2a2a38;
    gap: 4px;
}

.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: #7a7a8a !important;
    border: none !important;
    padding: 10px 20px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
}

.stTabs [aria-selected="true"] {
    color: #c8f060 !important;
    border-bottom: 2px solid #c8f060 !important;
    background: transparent !important;
}

/* ── Expander ── */
.streamlit-expanderHeader {
    background: #1e1e2e !important;
    border: 1px solid #2a2a38 !important;
    border-radius: 6px !important;
}

/* ── Code / markdown blocks ── */
.stMarkdown pre {
    background: #1e1e2e !important;
    border: 1px solid #2a2a38 !important;
    border-radius: 6px !important;
}

/* ── Progress bar ── */
.stProgress > div > div {
    background-color: #c8f060 !important;
}

/* ── Download buttons ── */
.stDownloadButton > button {
    background: #1e1e2e !important;
    border: 1px solid #3a3a4e !important;
    color: #c8f060 !important;
    border-radius: 6px !important;
}

.stDownloadButton > button:hover {
    border-color: #c8f060 !important;
    background: #2a2a3e !important;
}

/* ── Info / warning / error boxes ── */
.stAlert {
    border-radius: 6px !important;
}

/* ── Key point card ── */
.kp-card {
    background: #1e1e2e;
    border: 1px solid #2a2a38;
    border-left: 3px solid #c8f060;
    border-radius: 6px;
    padding: 16px 20px;
    margin: 8px 0;
}

.kp-type-badge {
    display: inline-block;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    padding: 2px 8px;
    border-radius: 3px;
    background: rgba(200,240,96,0.12);
    color: #c8f060;
    margin-bottom: 6px;
}

.ts-badge {
    display: inline-block;
    font-size: 11px;
    font-family: monospace;
    padding: 2px 8px;
    border-radius: 3px;
    background: rgba(240,96,96,0.15);
    color: #f06060;
    margin-left: 8px;
}

/* ── Quiz card ── */
.quiz-card {
    background: #1e1e2e;
    border: 1px solid #2a2a38;
    border-radius: 6px;
    padding: 16px 20px;
    margin: 10px 0;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────
# Session State Initialization
# ─────────────────────────────────────────

if "result" not in st.session_state:
    st.session_state.result = None
if "processing" not in st.session_state:
    st.session_state.processing = False
if "history" not in st.session_state:
    st.session_state.history = []  # list of {url, title, timestamp}


# ─────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────

with st.sidebar:
    st.markdown("##  YT Summarizer")
    st.markdown("---")

    # ── Gemini API Key check (replaces OpenAI check) ──
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    if gemini_key:
        st.success("✓ Gemini API key loaded")
    else:
        st.error("✗ GEMINI_API_KEY not set")
        st.caption("Add it to your .env file:\nGEMINI_API_KEY=your_key_here")

    st.markdown("---")

    # ── History ──
    if st.session_state.history:
        st.markdown("####  Recent Videos")
        for item in reversed(st.session_state.history[-5:]):
            short_title = item["title"][:35] + "…" if len(item["title"]) > 35 else item["title"]
            if st.button(short_title, key=f"hist_{item['url']}", use_container_width=True):
                st.session_state["prefill_url"] = item["url"]
        if st.button("Clear History", use_container_width=True):
            st.session_state.history = []
            st.rerun()

    st.markdown("---")
    st.caption("Built with Streamlit + Google Gemini")


# ─────────────────────────────────────────
# Main Content
# ─────────────────────────────────────────

st.markdown("#  YouTube Video Summarizer")
st.markdown("Paste any YouTube URL to get an AI-powered summary, key points, and quiz.")

# ── URL Input ───────────────────────────
prefill = st.session_state.pop("prefill_url", "")
url_input = st.text_input(
    "YouTube URL",
    value=prefill,
    placeholder="https://www.youtube.com/watch?v=...",
    label_visibility="collapsed",
)

col1, col2 = st.columns([1, 5])
with col1:
    summarize_btn = st.button("Summarize →", type="primary", use_container_width=True)
with col2:
    if st.session_state.result:
        if st.button("Clear Results", use_container_width=False):
            st.session_state.result = None
            st.rerun()

# ── Processing ───────────────────────────
if summarize_btn and url_input:
    st.session_state.processing = True
    progress_bar = st.progress(0)
    status_text = st.empty()

    try:
        def on_progress(step, pct):
            progress_bar.progress(pct / 100)
            status_text.markdown(
                f"<p style='color: #a0a0b0; font-size: 13px;'> {step}</p>",
                unsafe_allow_html=True
            )

        result = process_video(url_input, progress_callback=on_progress)
        st.session_state.result = result
        st.session_state.processing = False

        # Add to history
        title = result.get("video_info", {}).get("title", url_input)
        st.session_state.history.append({
            "url": url_input,
            "title": title,
            "timestamp": time.time(),
        })

        progress_bar.progress(1.0)
        status_text.markdown(
            "<p style='color: #60f0a0; font-size: 13px;'>✓ Done!</p>",
            unsafe_allow_html=True
        )
        time.sleep(0.5)
        progress_bar.empty()
        status_text.empty()

    except ValueError as e:
        progress_bar.empty()
        status_text.empty()
        st.error(f"**Invalid input:** {e}")
    except RuntimeError as e:
        progress_bar.empty()
        status_text.empty()
        st.error(f"**Processing failed:** {e}")
    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        st.error(f"**Unexpected error:** {e}")
        st.caption("Check the terminal for full error details.")
        raise


# ─────────────────────────────────────────
# Results Display
# ─────────────────────────────────────────

if st.session_state.result:
    result = st.session_state.result
    summary = result.get("summary_data", {})
    video_info = result.get("video_info", {})
    transcript_info = result.get("transcript_data", {})
    video_id = result.get("video_id", "")

    st.markdown("---")

    # ── Video Info Banner ────────────────
    title = video_info.get("title", "Unknown Video")
    title = title.encode('ascii', 'ignore').decode('ascii').strip() or "Unknown Video"
    channel = video_info.get("channel", "")
    duration = video_info.get("duration_seconds", 0)
    from_cache = result.get("from_cache", False)

    info_col1, info_col2 = st.columns([3, 1])
    with info_col1:
        st.markdown(f"### 🎬 {title}")
        st.caption(f" {channel}  ·  ⏱ {format_duration(duration)}  ·  "
                   f" {transcript_info.get('segment_count', 0)} segments via "
                   f"`{transcript_info.get('method', 'unknown')}`"
                   + ("  ·   From cache" if from_cache else ""))
    with info_col2:
        yt_url = f"https://www.youtube.com/watch?v={video_id}"
        st.markdown(f"[▶ Watch on YouTube]({yt_url})")

    # ── Download Buttons ─────────────────
    st.markdown("#####  Export")
    dl_col1, dl_col2, dl_col3 = st.columns([1, 1, 3])

    md_path = result.get("md_path")
    pdf_path = result.get("pdf_path")

    if md_path and Path(md_path).exists():
        with dl_col1:
            st.download_button(
                "⬇ Download Markdown",
                data=Path(md_path).read_bytes(),
                file_name=Path(md_path).name,
                mime="text/markdown",
            )

    if pdf_path and Path(pdf_path).exists():
        with dl_col2:
            st.download_button(
                "⬇ Download PDF",
                data=Path(pdf_path).read_bytes(),
                file_name=Path(pdf_path).name,
                mime="application/pdf",
            )

    # ── Main Tabs ───────────────────────
    st.markdown("---")
    tabs = st.tabs([" Summary", " Key Points", " Detailed Notes",
                    "Quiz", "Raw Markdown", "Transcript"])

    # ── Tab 1: Summary ──────────────────
    with tabs[0]:
        exec_summary = summary.get("executive_summary", "")
        if exec_summary:
            st.markdown("#### Executive Summary")
            st.info(exec_summary)

        col_left, col_right = st.columns(2)

        with col_left:
            themes = summary.get("key_themes", [])
            if themes:
                st.markdown("#### Key Themes")
                for theme in themes:
                    st.markdown(f"• {theme}")

            actions = summary.get("action_items", [])
            if actions:
                st.markdown("#### Action Items")
                for action in actions:
                    st.checkbox(action, key=f"action_{action[:20]}")

        with col_right:
            insights = summary.get("notable_insights", [])
            if insights:
                st.markdown("#### Notable Insights")
                for insight in insights:
                    st.markdown(f"• {insight}")

            # Stats
            st.markdown("#### Processing Stats")
            st.metric("Transcript Segments", transcript_info.get("segment_count", 0))
            st.metric("Chunks Processed", summary.get("chunk_count", 1))
            st.metric("Model Used", summary.get("model_used", "Gemini"))

    # ── Tab 2: Key Points ───────────────
    with tabs[1]:
        key_points = summary.get("key_points", [])
        if key_points:
            st.markdown(f"**{len(key_points)} key points extracted with timestamps:**")
            st.markdown("")

            TYPE_COLORS = {
                "concept": "#c8f060",
                "statistic": "#60c8f0",
                "action-item": "#f0a030",
                "example": "#a060f0",
                "warning": "#f06060",
                "insight": "#60f0a0",
            }

            for kp in key_points:
                kp_type = kp.get("type", "concept")
                color = TYPE_COLORS.get(kp_type, "#c8f060")
                ts = kp.get("timestamp", "0:00")
                ts_url = kp.get("timestamp_url", f"https://youtube.com/watch?v={video_id}")
                title_kp = kp.get("title", "")
                explanation = kp.get("explanation", "")
                quote = kp.get("quote", "")

                st.markdown(f"""
<div class='kp-card' style='border-left-color: {color};'>
    <span class='kp-type-badge' style='background: {color}22; color: {color};'>{kp_type.upper()}</span>
    <a href='{ts_url}' target='_blank' class='ts-badge'>▶ {ts}</a>
    <div style='font-weight: 600; font-size: 15px; margin: 8px 0 6px; color: #e8e8e0;'>{title_kp}</div>
    <div style='font-size: 14px; color: #a0a0b0; line-height: 1.6;'>{explanation}</div>
    {"<div style='font-size: 12px; color: #606080; font-style: italic; margin-top: 8px; padding-left: 12px; border-left: 2px solid #3a3a4e;'>&ldquo;" + quote + "&rdquo;</div>" if quote else ""}
</div>
""", unsafe_allow_html=True)
        else:
            st.info("No key points extracted. Try reprocessing with a different model.")

    # ── Tab 3: Detailed Notes ────────────
    with tabs[2]:
        detailed = summary.get("detailed_notes", "")
        if detailed:
            st.markdown(detailed)
        else:
            exec_s = summary.get("executive_summary", "")
            st.markdown(exec_s if exec_s else "No detailed notes available.")

    # ── Tab 4: Quiz ─────────────────────
    with tabs[3]:
        quiz = summary.get("quiz", [])
        if quiz:
            st.markdown(f"### Comprehension Quiz ({len(quiz)} Questions)")
            st.caption("Test your understanding of the video content.")

            for i, q in enumerate(quiz, 1):
                with st.expander(f"Q{i}: {q.get('question', '')[:80]}..."):
                    q_type = q.get("type", "short_answer")
                    st.markdown(f"**{q.get('question', '')}**")
                    st.markdown("")

                    if q_type == "mcq":
                        opts = q.get("options", [])
                        correct_idx = q.get("correct_index", 0)
                        user_answer = st.radio(
                            "Choose your answer:",
                            opts,
                            key=f"quiz_{i}",
                            label_visibility="collapsed",
                        )
                        if st.button("Check Answer", key=f"check_{i}"):
                            if user_answer == opts[correct_idx]:
                                st.success(f"✓ Correct! {q.get('explanation', '')}")
                            else:
                                st.error(
                                    f"✗ Incorrect. Correct answer: **{opts[correct_idx]}**\n\n"
                                    f"{q.get('explanation', '')}"
                                )
                    else:
                        user_text = st.text_area("Your answer:", key=f"quiz_sa_{i}", height=80)
                        with st.expander("See sample answer"):
                            st.markdown(q.get("sample_answer", ""))
        else:
            st.info("Quiz generation was disabled or failed. Enable it in the sidebar and reprocess.")

    # ── Tab 5: Raw Markdown ─────────────
    with tabs[4]:
        md_content = get_markdown_content(result)
        if md_content:
            st.markdown("##### Preview (raw Markdown source):")
            st.code(md_content, language="markdown")
        else:
            st.info("Markdown not available.")

    # ── Tab 6: Transcript ───────────────
    with tabs[5]:
        full_text = transcript_info.get("full_text", "")
        if full_text:
            st.markdown(f"**Full transcript** ({len(full_text.split())} words):")
            st.markdown(
                f"<div style='background: #1e1e2e; padding: 20px; border-radius: 6px; "
                f"font-size: 13px; line-height: 1.8; color: #a0a0b0; "
                f"max-height: 400px; overflow-y: auto;'>{full_text}</div>",
                unsafe_allow_html=True
            )
        else:
            st.info("Transcript text not stored. Reprocess to view.")

else:
    # ── Empty State ──────────────────────
    st.markdown("---")
    st.markdown("""
<div style='text-align: center; padding: 60px 20px; color: #4a4a5a;'>
    <div style='font-size: 64px; margin-bottom: 16px;'></div>
    <div style='font-size: 18px; font-weight: 500; color: #6a6a7a;'>
        Paste a YouTube URL above and click <strong style='color: #c8f060'>Summarize →</strong>
    </div>
    <div style='font-size: 14px; margin-top: 12px;'>
        Supports lectures, podcasts, tutorials, talks, documentaries
    </div>
    <div style='font-size: 13px; margin-top: 8px; color: #4a7a20;'>
         Free · Powered by Google Gemini
    </div>
</div>
""", unsafe_allow_html=True)