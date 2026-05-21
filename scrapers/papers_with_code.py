"""
Papers With Code API.
Detects if a paper has GitHub implementations and how many stars they have.
"Code exists with 1000 stars" is a strong signal researchers are using it.
Free, no auth.
"""

from __future__ import annotations
import requests

PWC_BASE = "https://paperswithcode.com/api/v1"

def get_paper_signals(arxiv_id: str) -> dict:
    """Get implementation signals for an arXiv paper."""
    clean_id = arxiv_id.replace("arxiv:", "").split("v")[0]
    try:
        r = requests.get(f"{PWC_BASE}/papers/", params={"arxiv_id": clean_id}, timeout=10)
        r.raise_for_status()
        results = r.json().get("results", [])
        if not results:
            return {"has_code": False, "stars": 0, "impl_count": 0}

        paper_id = results[0]["id"]
        repos_r = requests.get(f"{PWC_BASE}/papers/{paper_id}/repositories/", timeout=10)
        repos_r.raise_for_status()
        repos = repos_r.json().get("results", [])

        if not repos:
            return {"has_code": False, "stars": 0, "impl_count": 0}

        return {
            "has_code": True,
            "impl_count": len(repos),
            "stars": max((r.get("stars", 0) or 0 for r in repos), default=0),
            "has_official": any(r.get("is_official") for r in repos),
        }
    except Exception:
        return {"has_code": False, "stars": 0, "impl_count": 0}

def compute_pwc_score(signals: dict) -> int:
    """Papers with popular code = researchers are using it = important."""
    if not signals.get("has_code"):
        return 0
    score = 5  # has any code
    stars = signals.get("stars", 0) or 0
    if stars >= 5000:
        score += 20
    elif stars >= 1000:
        score += 14
    elif stars >= 500:
        score += 9
    elif stars >= 100:
        score += 5
    if signals.get("has_official"):
        score += 5
    if (signals.get("impl_count", 0) or 0) >= 5:
        score += 4
    return min(score, 30)
