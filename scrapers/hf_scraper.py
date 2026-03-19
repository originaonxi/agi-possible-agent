"""
Scrapes HuggingFace Papers page.
HF aggregates and upvotes the best ML papers daily.
Free. No API key needed.
"""

from __future__ import annotations
import re
import time
import requests
from datetime import date
from scrapers.arxiv_scraper import score_agi_relevance

HF_PAPERS_URL = "https://huggingface.co/papers"

def scrape_hf_papers() -> list[dict]:
    """Scrape HuggingFace Papers daily listing."""
    papers = []
    try:
        r = requests.get(HF_PAPERS_URL, timeout=20, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AGIPossibleBot/1.0"
        })
        r.raise_for_status()
        html = r.text

        # Extract paper links (format: /papers/ARXIV_ID)
        paper_ids = re.findall(r'href="/papers/(\d{4}\.\d+)"', html)
        paper_ids = list(dict.fromkeys(paper_ids))  # deduplicate, preserve order

        # Extract titles near those links
        title_pattern = re.findall(
            r'href="/papers/\d{4}\.\d+"[^>]*>\s*<[^>]*>\s*(.*?)\s*</',
            html, re.DOTALL
        )

        print(f"  HF Papers: found {len(paper_ids)} papers")

        for i, arxiv_id in enumerate(paper_ids[:30]):
            url = f"https://huggingface.co/papers/{arxiv_id}"
            arxiv_url = f"https://arxiv.org/abs/{arxiv_id}"

            # Try to get title
            title = f"Paper {arxiv_id}"
            if i < len(title_pattern):
                t = re.sub(r'<[^>]+>', '', title_pattern[i]).strip()
                if t and len(t) > 5:
                    title = t

            score = score_agi_relevance(title, "")

            papers.append({
                "id": f"hf:{arxiv_id}",
                "title": title,
                "url": arxiv_url,  # link to arXiv for full paper
                "hf_url": url,
                "abstract": "",
                "authors": [],
                "published_date": date.today().isoformat(),
                "source": "HuggingFace Papers",
                "source_type": "hf_papers",
                "agi_score": score + 5,  # HF trending = slight boost
            })

        time.sleep(1)
    except Exception as e:
        print(f"  HF Papers scrape error: {e}")

    return papers
