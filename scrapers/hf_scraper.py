"""
Scrapes HuggingFace Papers.
Uses HF's daily papers API — returns upvote counts (our Twitter/X velocity proxy).
Also checks HF hub for model existence (open weights signal).
"""

from __future__ import annotations
import re
import time
import requests
from datetime import date
from scrapers.arxiv_scraper import score_agi_relevance

HF_PAPERS_API = "https://huggingface.co/api/papers"
HF_MODELS_API = "https://huggingface.co/api/models"


def scrape_hf_papers() -> list[dict]:
    """Fetch today's HF Papers with upvote counts via API."""
    papers = []
    today = date.today().isoformat()

    try:
        r = requests.get(
            f"{HF_PAPERS_API}?date={today}",
            timeout=20,
            headers={"User-Agent": "AGIPossibleBot/1.0"},
        )
        r.raise_for_status()
        items = r.json()
        if not isinstance(items, list):
            items = items.get("papers", [])

        print(f"  HF Papers API: found {len(items)} papers for {today}")

        for item in items[:30]:
            paper    = item.get("paper", item)
            arxiv_id = paper.get("id", "")
            if not arxiv_id:
                continue

            title    = paper.get("title", f"Paper {arxiv_id}")
            abstract = paper.get("summary", "") or paper.get("abstract", "")
            authors  = [a.get("name", "") for a in (paper.get("authors") or [])[:6]]
            upvotes  = item.get("upvotes", 0) or paper.get("upvotes", 0) or 0
            score    = score_agi_relevance(title, abstract)

            papers.append({
                "id": f"arxiv:{arxiv_id}",
                "title": title,
                "url": f"https://arxiv.org/abs/{arxiv_id}",
                "hf_url": f"https://huggingface.co/papers/{arxiv_id}",
                "abstract": abstract,
                "authors": authors,
                "published_date": today,
                "source": "HuggingFace Papers",
                "source_type": "hf_papers",
                "agi_score": score + 5,
                "hf_likes": upvotes,  # community upvotes = Twitter/X velocity proxy
            })

        time.sleep(1)

    except Exception as e:
        print(f"  HF Papers API error: {e}, falling back to HTML scrape")
        papers = _scrape_hf_html()

    return papers


def _scrape_hf_html() -> list[dict]:
    """Fallback: scrape HF Papers HTML page (no upvote counts)."""
    papers = []
    today = date.today().isoformat()
    try:
        r = requests.get(
            "https://huggingface.co/papers",
            timeout=20,
            headers={"User-Agent": "Mozilla/5.0 AGIPossibleBot/1.0"},
        )
        r.raise_for_status()
        html = r.text
        paper_ids = list(dict.fromkeys(re.findall(r'href="/papers/(\d{4}\.\d+)"', html)))
        print(f"  HF Papers HTML fallback: {len(paper_ids)} papers")
        for arxiv_id in paper_ids[:30]:
            papers.append({
                "id": f"arxiv:{arxiv_id}",
                "title": f"Paper {arxiv_id}",
                "url": f"https://arxiv.org/abs/{arxiv_id}",
                "hf_url": f"https://huggingface.co/papers/{arxiv_id}",
                "abstract": "",
                "authors": [],
                "published_date": today,
                "source": "HuggingFace Papers",
                "source_type": "hf_papers",
                "agi_score": 5,
                "hf_likes": 0,
            })
        time.sleep(1)
    except Exception as e:
        print(f"  HF HTML fallback error: {e}")
    return papers


def check_hf_model_exists(arxiv_id: str) -> bool:
    """
    Check if a paper has released model weights on HuggingFace.
    Papers with open weights are cited 5x more (Gemini: 30% weight signal).
    """
    clean_id = arxiv_id.replace("arxiv:", "").split("v")[0]
    try:
        r = requests.get(
            HF_MODELS_API,
            params={"search": clean_id, "limit": 1},
            timeout=8,
            headers={"User-Agent": "AGIPossibleBot/1.0"},
        )
        if r.status_code == 200:
            return len(r.json()) > 0
    except Exception:
        pass
    return False
