"""
Builds and sends the Daily AGI Possible newsletter email.
Beautiful dark HTML. Reads like a real newsletter.
"""

from __future__ import annotations
import re
import smtplib
from datetime import date, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, EMAIL_TO

def markdown_to_html(text: str) -> str:
    """Convert simple markdown to HTML for email."""
    # Headers
    text = re.sub(r'^### (.+)', r'<h3 style="color:#a78bfa;font-size:17px;margin:24px 0 8px;font-family:\'Inter\',sans-serif;">\1</h3>', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.+)', r'<h2 style="color:#c4b5fd;font-size:19px;margin:24px 0 8px;">\1</h2>', text, flags=re.MULTILINE)

    # Bold
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong style="color:#e2e8f0;">\1</strong>', text)

    # Italic
    text = re.sub(r'\*(.+?)\*', r'<em style="color:#94a3b8;">\1</em>', text)

    # Inline code
    text = re.sub(r'`([^`]+)`', r'<code style="background:#1e1b4b;color:#a78bfa;padding:1px 5px;border-radius:3px;font-size:13px;">\1</code>', text)

    # Links
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" style="color:#818cf8;text-decoration:none;">\1</a>', text)

    # Arrows
    text = text.replace('\u2192', '<span style="color:#818cf8;">\u2192</span>')

    # Paragraphs
    paragraphs = text.split('\n\n')
    html_parts = []
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        if p.startswith('<h'):
            html_parts.append(p)
        else:
            p = p.replace('\n', '<br>')
            html_parts.append(f'<p style="color:#cbd5e1;font-size:15px;line-height:1.8;margin:12px 0;">{p}</p>')

    return '\n'.join(html_parts)

def _signal_badges(item: dict) -> str:
    """Build social signal badges for a paper (citations, stars, Reddit, lab)."""
    badges = []

    # S2 citation velocity
    s2 = item.get("s2") or {}
    velocity = s2.get("citationVelocity") or 0
    influential = s2.get("influentialCitationCount") or 0
    if velocity >= 20:
        badges.append(f'<span style="background:#14532d;color:#4ade80;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:600;">\u26a1 {velocity} cit/yr</span>')
    elif influential >= 5:
        badges.append(f'<span style="background:#14532d;color:#4ade80;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:600;">\ud83d\udcda {influential} influential cit</span>')

    # Papers With Code stars
    pwc = item.get("pwc") or {}
    stars = pwc.get("stars") or 0
    if stars >= 100:
        k = f"{stars//1000}k" if stars >= 1000 else str(stars)
        badges.append(f'<span style="background:#1c1917;color:#fb923c;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:600;">\u2b50 {k} stars</span>')
    elif pwc.get("has_official"):
        badges.append('<span style="background:#1c1917;color:#fb923c;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:600;">\u2705 official code</span>')

    # Reddit buzz
    reddit = item.get("reddit") or {}
    reddit_score = reddit.get("reddit_score") or 0
    if reddit_score >= 100:
        badges.append(f'<span style="background:#1a0a00;color:#f97316;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:600;">\ud83d\udd25 r/ML {reddit_score}</span>')

    # Conference badge
    if item.get("source_type") == "conference":
        venue = item.get("conference_venue", "Conference")
        badges.append(f'<span style="background:#0c0a1e;color:#a78bfa;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:600;">\ud83c\udf93 {venue}</span>')

    if not badges:
        return ""
    return f'<div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px;">{" ".join(badges)}</div>'

def build_story_html(story: dict) -> str:
    """Build HTML for one story."""
    content_html = markdown_to_html(story["content"])
    source = story.get("source", "")
    url = story.get("url", "#")
    item = story.get("item", {})
    badges_html = _signal_badges(item)

    # Composite score display
    score = item.get("composite_score", 0)
    score_color = "#4ade80" if score >= 60 else "#a78bfa" if score >= 40 else "#818cf8"

    return f"""
<div style="background:#0f0f2a;border-radius:12px;padding:24px;margin-bottom:24px;border:1px solid #1e1b4b;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;flex-wrap:wrap;gap:8px;">
    <span style="background:#1e1b4b;color:#818cf8;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600;letter-spacing:1px;text-transform:uppercase;">{source}</span>
    <span style="color:{score_color};font-size:11px;font-weight:600;">signal: {score}</span>
  </div>
  {badges_html}
  {content_html}
  <div style="margin-top:16px;padding-top:12px;border-top:1px solid #1e1b4b;">
    <a href="{url}" style="color:#818cf8;font-size:12px;text-decoration:none;">Read full paper \u2192</a>
  </div>
</div>"""

def build_email_html(
    issue_number: int,
    stories: list[dict],
    why_these_five: str,
    total_scraped: int,
    new_today: int,
) -> str:
    date_str = date.today().strftime("%B %d, %Y")
    day_name = date.today().strftime("%A")

    stories_html = "\n".join(build_story_html(s) for s in stories)

    # Source breakdown
    sources = {}
    for s in stories:
        src = s.get("source", "Unknown")
        sources[src] = sources.get(src, 0) + 1
    source_tags = " \u00b7 ".join(f'<span style="color:#818cf8;">{k}</span>' for k in sources.keys())

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
</head>
<body style="margin:0;padding:16px 0;background:#050510;font-family:'Inter',sans-serif;">
<div style="max-width:680px;margin:0 auto;">

<!-- Header -->
<div style="background:linear-gradient(135deg,#1e1b4b 0%,#0f0f2a 100%);padding:32px 32px 24px;border-radius:12px 12px 0 0;border-bottom:1px solid #2d2b5e;">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px;">
    <div>
      <p style="margin:0 0 6px;color:#818cf8;font-size:11px;letter-spacing:3px;text-transform:uppercase;font-weight:600;">Issue #{issue_number:03d}</p>
      <h1 style="margin:0;color:#ffffff;font-size:26px;font-weight:700;letter-spacing:-0.5px;">Daily AGI Possible</h1>
      <p style="margin:8px 0 0;color:#64748b;font-size:13px;">{day_name}, {date_str} \u00b7 8:00 AM PST</p>
    </div>
    <div style="text-align:right;">
      <p style="margin:0;color:#a78bfa;font-size:24px;font-weight:700;">{new_today}</p>
      <p style="margin:2px 0 0;color:#64748b;font-size:11px;">new deltas today</p>
      <p style="margin:4px 0 0;color:#475569;font-size:10px;">of ~{total_scraped} scraped</p>
    </div>
  </div>
</div>

<!-- Intro -->
<div style="background:#0a0a1e;padding:20px 32px;border-bottom:1px solid #1e1b4b;">
  <p style="margin:0 0 8px;color:#94a3b8;font-size:14px;line-height:1.7;">
    Every day at 8am PST, this agent scrapes the entire ML frontier \u2014 arXiv (4 categories), HuggingFace Papers, frontier lab blogs (Anthropic/OpenAI/DeepMind/Meta), and ICLR/NeurIPS/ICML via OpenReview. Then it cross-references Semantic Scholar citation velocity, Papers With Code GitHub stars, and Reddit r/MachineLearning buzz to find the papers every researcher is actually talking about. Only the ones that clear the quality bar reach your inbox.
  </p>
  <p style="margin:0;color:#64748b;font-size:12px;">Sources today: {source_tags}</p>
</div>

<!-- Stories -->
<div style="background:#070718;padding:24px 28px;">
  <p style="margin:0 0 20px;color:#818cf8;font-size:10px;letter-spacing:3px;text-transform:uppercase;font-weight:600;">Today's 5 AGI Deltas</p>
  {stories_html}
</div>

<!-- Why These Five -->
<div style="background:#0a0a1e;padding:20px 32px;border-top:1px solid #1e1b4b;border-bottom:1px solid #1e1b4b;">
  <p style="margin:0 0 10px;color:#818cf8;font-size:10px;letter-spacing:3px;text-transform:uppercase;font-weight:600;">Why These Five</p>
  <p style="margin:0;color:#94a3b8;font-size:14px;line-height:1.7;font-style:italic;">{why_these_five}</p>
</div>

<!-- Footer -->
<div style="background:#050510;padding:20px 32px;border-radius:0 0 12px 12px;">
  <p style="margin:0;color:#334155;font-size:12px;line-height:1.7;">
    Daily AGI Possible \u00b7 Issue #{issue_number:03d} \u00b7 {date_str}<br>
    Agent built by <a href="https://linkedin.com/in/samisanmol" style="color:#818cf8;text-decoration:none;">Anmol Chaudhary</a> \u2014 CTO @ Aonxi, Ex-Meta, Ex-Apple<br>
    github.com/originaonxi \u00b7 iamsamios@icloud.com
  </p>
</div>

</div>
</body>
</html>"""

def send_email(html: str, subject: str) -> bool:
    """Send the newsletter email."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = EMAIL_TO
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.starttls()
        s.login(SMTP_USER, SMTP_PASS)
        s.sendmail(SMTP_USER, EMAIL_TO, msg.as_string())
    return True
