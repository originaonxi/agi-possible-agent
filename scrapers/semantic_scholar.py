"""
Semantic Scholar API enrichment.
Adds citation velocity, influential citations, author h-index, TLDR to any paper.
Free, no auth for basic use. 100 req/5min unauthenticated.
"""

from __future__ import annotations
import time
import requests

S2_BASE = "https://api.semanticscholar.org/graph/v1"

FIELDS = ",".join([
    "citationCount",
    "influentialCitationCount",
    "citationVelocity",
    "tldr",
    "authors.authorId",
    "authors.name",
    "authors.hIndex",
    "venue",
    "publicationDate",
    "externalIds",
])

def enrich_paper(arxiv_id: str) -> dict:
    """Fetch S2 signals for one arXiv paper. Returns {} on failure."""
    clean_id = arxiv_id.replace("arxiv:", "").split("v")[0]
    url = f"{S2_BASE}/paper/ARXIV:{clean_id}"
    try:
        r = requests.get(url, params={"fields": FIELDS}, timeout=15)
        if r.status_code == 404:
            return {}
        r.raise_for_status()
        return r.json()
    except Exception:
        return {}

def compute_s2_score(s2: dict) -> int:
    """Convert S2 signals into a score boost (0-50)."""
    if not s2:
        return 0

    score = 0

    citations = s2.get("citationCount", 0) or 0
    influential = s2.get("influentialCitationCount", 0) or 0
    velocity = s2.get("citationVelocity", 0) or 0

    # Citation velocity (citations per year) — best predictor of impact
    if velocity >= 100:
        score += 25
    elif velocity >= 50:
        score += 18
    elif velocity >= 20:
        score += 12
    elif velocity >= 10:
        score += 7
    elif velocity >= 5:
        score += 3

    # Influential citations (papers that actually USE this work)
    if influential >= 20:
        score += 15
    elif influential >= 10:
        score += 10
    elif influential >= 5:
        score += 6
    elif influential >= 2:
        score += 3

    # Top author h-index (credibility signal)
    authors = s2.get("authors", []) or []
    max_h = max((a.get("hIndex", 0) or 0 for a in authors), default=0)
    if max_h >= 80:
        score += 10
    elif max_h >= 50:
        score += 7
    elif max_h >= 30:
        score += 4
    elif max_h >= 15:
        score += 2

    # Top venue (conference quality)
    venue = (s2.get("venue") or "").lower()
    top_venues = ["neurips", "iclr", "icml", "acl", "nature", "science", "arxiv"]
    if any(v in venue for v in top_venues):
        score += 5

    return min(score, 50)

def enrich_batch(papers: list[dict], delay: float = 0.5) -> list[dict]:
    """Enrich a list of papers with S2 signals. Rate-limited."""
    enriched = []
    for paper in papers:
        pid = paper.get("id", "")
        if pid.startswith("arxiv:"):
            s2 = enrich_paper(pid)
            paper["s2"] = s2
            paper["s2_score"] = compute_s2_score(s2)
            # Use S2 TLDR if no abstract
            if not paper.get("abstract") and s2.get("tldr"):
                paper["abstract"] = s2["tldr"].get("text", "")
        else:
            paper["s2"] = {}
            paper["s2_score"] = 0
        enriched.append(paper)
        time.sleep(delay)
    return enriched
