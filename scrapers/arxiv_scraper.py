"""
Scrapes arXiv recent listings for cs.LG, cs.AI, cs.CL, stat.ML.
Returns structured paper data with title, abstract, authors, URL.
Free. No API key needed.
"""

from __future__ import annotations
import re
import time
import hashlib
import requests
from datetime import date
from config import AGI_SIGNALS

BASE = "https://arxiv.org"

def score_agi_relevance(title: str, abstract: str) -> int:
    """Score content by AGI relevance using keyword signals."""
    text = (title + " " + abstract).lower()
    score = 0
    for keyword in AGI_SIGNALS["high"]:
        if keyword.lower() in text:
            score += 10
    for keyword in AGI_SIGNALS["medium"]:
        if keyword.lower() in text:
            score += 5
    for keyword in AGI_SIGNALS["low"]:
        if keyword.lower() in text:
            score -= 2
    return max(0, score)

def scrape_arxiv_category(category_url: str) -> list[dict]:
    """Scrape one arXiv category recent page."""
    papers = []
    try:
        r = requests.get(category_url, timeout=20, headers={
            "User-Agent": "AGIPossibleBot/1.0 (research newsletter)"
        })
        r.raise_for_status()
        html = r.text

        # Extract paper entries
        # arXiv recent page has dt/dd pairs
        entries = re.findall(
            r'<dt>.*?</dt>\s*<dd>(.*?)</dd>',
            html, re.DOTALL
        )

        # Also try arXiv API for better data
        category = category_url.split("/list/")[1].split("/")[0]
        papers = _scrape_via_api(category)

        if not papers:
            # Fallback: parse HTML
            papers = _parse_html_listing(html, category)

        time.sleep(1)
    except Exception as e:
        print(f"  arXiv scrape error for {category_url}: {e}")

    return papers

def _scrape_via_api(category: str, max_results: int = 50) -> list[dict]:
    """Use arXiv API for structured data."""
    try:
        api_url = f"http://export.arxiv.org/api/query"
        params = {
            "search_query": f"cat:{category}",
            "start": 0,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        r = requests.get(api_url, params=params, timeout=30)
        r.raise_for_status()

        papers = []
        # Parse Atom XML
        entries = re.findall(r'<entry>(.*?)</entry>', r.text, re.DOTALL)

        for entry in entries:
            arxiv_id = re.search(r'<id>.*?/abs/([^<]+)</id>', entry)
            title = re.search(r'<title>(.*?)</title>', entry, re.DOTALL)
            summary = re.search(r'<summary>(.*?)</summary>', entry, re.DOTALL)
            authors = re.findall(r'<name>(.*?)</name>', entry)
            published = re.search(r'<published>(.*?)</published>', entry)

            if not (arxiv_id and title and summary):
                continue

            arxiv_id = arxiv_id.group(1).strip()
            title_text = re.sub(r'\s+', ' ', title.group(1)).strip()
            abstract = re.sub(r'\s+', ' ', summary.group(1)).strip()
            pub_date = published.group(1)[:10] if published else date.today().isoformat()

            url = f"https://arxiv.org/abs/{arxiv_id}"
            score = score_agi_relevance(title_text, abstract)

            papers.append({
                "id": f"arxiv:{arxiv_id}",
                "title": title_text,
                "url": url,
                "abstract": abstract,
                "authors": authors[:5],
                "published_date": pub_date,
                "source": f"arXiv {category}",
                "source_type": "arxiv",
                "agi_score": score,
            })

        return papers
    except Exception as e:
        print(f"  arXiv API error for {category}: {e}")
        return []

def _parse_html_listing(html: str, category: str) -> list[dict]:
    """Fallback HTML parser for arXiv listing page."""
    papers = []
    try:
        # Find paper IDs
        ids = re.findall(r'href="/abs/(\d+\.\d+)"', html)
        titles = re.findall(r'class="title[^"]*"[^>]*>(.*?)</span>', html, re.DOTALL)

        for i, arxiv_id in enumerate(ids[:30]):
            title = re.sub(r'\s+', ' ', titles[i]).strip() if i < len(titles) else f"Paper {arxiv_id}"
            title = re.sub(r'<[^>]+>', '', title).strip()
            url = f"https://arxiv.org/abs/{arxiv_id}"

            papers.append({
                "id": f"arxiv:{arxiv_id}",
                "title": title,
                "url": url,
                "abstract": "",
                "authors": [],
                "published_date": date.today().isoformat(),
                "source": f"arXiv {category}",
                "source_type": "arxiv",
                "agi_score": score_agi_relevance(title, ""),
            })
    except Exception:
        pass
    return papers

def scrape_all() -> list[dict]:
    """Scrape all arXiv categories."""
    from config import SOURCES
    all_papers = []
    seen_ids = set()

    categories = ["cs.LG", "cs.AI", "cs.CL", "stat.ML"]
    for category in categories:
        print(f"  Scraping arXiv {category}...")
        papers = _scrape_via_api(category, max_results=30)
        for p in papers:
            if p["id"] not in seen_ids:
                seen_ids.add(p["id"])
                all_papers.append(p)
        time.sleep(2)

    print(f"  arXiv: {len(all_papers)} papers found")
    return all_papers
