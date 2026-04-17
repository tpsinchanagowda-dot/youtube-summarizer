# exporter.py — SAFE VERSION (No emoji / no encoding errors)

import os
from pathlib import Path
from datetime import datetime

from utils import (
    sanitize_filename,
    format_duration,
    ensure_output_dir,
)

def _s(text) -> str:
    """Strip emojis and non-ASCII characters from any string."""
    if not text:
        return ""
    return str(text).encode('ascii', 'ignore').decode('ascii').strip()

# ---------------------------
# MARKDOWN
# ---------------------------

def generate_markdown(summary_data, video_info, video_id):
    title = _s(video_info.get("title", "YouTube Video"))
    channel = _s(video_info.get("channel", "Unknown"))
    duration = format_duration(video_info.get("duration_seconds", 0))
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = []

    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"Channel: {channel}")
    lines.append(f"Duration: {duration}")
    lines.append(f"Video: {video_url}")
    lines.append(f"Generated: {generated_at}")
    lines.append("")
    lines.append("---")

    # Executive Summary
    if summary_data.get("executive_summary"):
        lines.append("## Executive Summary")
        lines.append(_s(summary_data["executive_summary"]))

    # Key Themes
    if summary_data.get("key_themes"):
        lines.append("\n## Key Themes")
        for t in summary_data["key_themes"]:
            lines.append(f"- {_s(t)}")

    # Key Points
    if summary_data.get("key_points"):
        lines.append("\n## Key Points")
        for i, kp in enumerate(summary_data["key_points"], 1):
            lines.append(f"\n### {i}. {_s(kp.get('title',''))}")
            lines.append(f"Time: {_s(kp.get('timestamp',''))}")
            lines.append(_s(kp.get("explanation","")))

    # Insights
    if summary_data.get("notable_insights"):
        lines.append("\n## Insights")
        for i in summary_data["notable_insights"]:
            lines.append(f"- {_s(i)}")

    return "\n".join(lines)


def save_markdown(content, title, output_dir="outputs"):
    out_dir = ensure_output_dir(output_dir)
    filename = sanitize_filename(title) + ".md"
    path = out_dir / filename
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------
# PDF
# ---------------------------

def generate_pdf(summary_data, video_info, video_id, output_dir="outputs"):
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet

    out_dir = ensure_output_dir(output_dir)
    filename = sanitize_filename(video_info.get("title", "video")) + ".pdf"
    path = out_dir / filename

    doc = SimpleDocTemplate(str(path))
    styles = getSampleStyleSheet()
    story = []

    title = _s(video_info.get("title", ""))
    story.append(Paragraph(title, styles["Title"]))
    story.append(Spacer(1, 10))

    if summary_data.get("executive_summary"):
        story.append(Paragraph("Executive Summary", styles["Heading2"]))
        story.append(Paragraph(_s(summary_data["executive_summary"]), styles["Normal"]))

    if summary_data.get("key_points"):
        story.append(Paragraph("Key Points", styles["Heading2"]))
        for kp in summary_data["key_points"]:
            story.append(Paragraph(_s(kp.get("title","")), styles["Heading3"]))
            story.append(Paragraph(_s(kp.get("explanation","")), styles["Normal"]))

    doc.build(story)
    return path


# ---------------------------
# BOTH
# ---------------------------

def export_both(summary_data, video_info, video_id, output_dir="outputs"):
    md = generate_markdown(summary_data, video_info, video_id)
    md_path = save_markdown(md, video_info.get("title","video"), output_dir)
    pdf_path = generate_pdf(summary_data, video_info, video_id, output_dir)
    return md_path, pdf_path