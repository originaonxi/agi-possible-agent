"""
OpenReview scraper for top conference papers.
ICLR, NeurIPS, ICML — where the best AGI research gets formally published.
Papers with high review scores = peer-validated quality.
"""

from __future__ import annotations
import requests
import re
from datetime import date

OPENREVIEW_BASE = "https://api2.openreview.net"
HEADERS = {"User-Agent": "AGIPossibleBot/2.0"}

# Current conferences — update venue IDs each cycle
VENUES = {
    "ICLR.cc/2025/Conference": "ICLR 2025",
    "NeurIPS.cc/2024/Conference": "NeurIPS 2024",
    "ICML.cc/2025/Conference": "ICML 2025",
    "ICLR.cc/2025/Workshop": "ICLR 2025 Workshop",
}

def fetch_accepted_papers(venue_id: str, limit: int = 100) -> list[dict]:
    """Fetch accepted papers from a venue."""
    try:
        r = requests.get(
            f"{OPENREVIEW_BASE}/notes",
            params={
                "invitation": f"{venue_id}/-/Camera_Ready_Submission",
                "details": "replyCount,originalReplyCount",
                "limit": limit,
                "offset": 0,
                "sort": "cdate:desc",
            },
            headers=HEADERS,
            timeout=20,
        )
        r.raise_for_status()
        notes = r.json().get("notes", [])
        return notes
    except Exception:
        # Fallback: try Oral/Spotlight track (highest quality)
        try:
            r = requests.get(
                f"{OPENREVIEW_BASE}/notes",
                params={
                    "invitation": f"{venue_id}/-/Oral_Submission",
                    "limit": limit,
                },
                headers=HEADERS,
                timeout=20,
            )
            r.raise_for_status()
            return r.json().get("notes", [])
        except Exception:
            return []

def scrape_all_conferences() -> list[dict]:
    """Scrape recent papers from top conferences."""
    papers = []
    seen_ids = set()

    for venue_id, venue_name in VENUES.items():
        try:
            notes = fetch_accepted_papers(venue_id, limit=50)
            for note in notes:
                content = note.get("content", {})
                title = _extract_field(content, "title")
                abstract = _extract_field(content, "abstract")
                authors = _extract_list(content, "authors")
                arxiv_link = _extract_field(content, "code") or _extract_field(content, "pdf") or ""

                if not title:
                    continue

                # Build unique ID
                uid = note.get("id", title[:20].replace(" ", "_"))
                if uid in seen_ids:
                    continue
                seen_ids.add(uid)

                # Try to find arXiv ID in PDF link
                arxiv_id = None
                pdf_link = _extract_field(content, "pdf") or note.get("id", "")
                arxiv_match = re.search(r'(\d{4}\.\d{4,5})', pdf_link)
                if arxiv_match:
                    arxiv_id = arxiv_match.group(1)

                papers.append({
                    "id": f"openreview:{uid}",
                    "title": title,
                    "url": f"https://openreview.net/forum?id={note.get('id', '')}",
                    "abstract": abstract,
                    "authors": authors[:5],
                    "published_date": date.today().isoformat(),
                    "source": venue_name,
                    "source_type": "conference",
                    "agi_score": 0,  # Will be scored by composite scorer
                    "conference_venue": venue_name,
                    "arxiv_id_hint": arxiv_id,
                })
        except Exception as e:
            print(f"  OpenReview {venue_name} error: {e}")

    print(f"  OpenReview: {len(papers)} conference papers found")
    return papers

def _extract_field(content: dict, field: str) -> str:
    v = content.get(field, "")
    if isinstance(v, dict):
        return v.get("value", "")
    return str(v) if v else ""

def _extract_list(content: dict, field: str) -> list[str]:
    v = content.get(field, [])
    if isinstance(v, dict):
        v = v.get("value", [])
    if isinstance(v, list):
        return [str(x) for x in v]
    return []
