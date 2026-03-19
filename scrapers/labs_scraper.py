"""
Scrapes frontier lab research blogs:
Anthropic, OpenAI, DeepMind, Meta AI.
"""

from __future__ import annotations
import re
import time
import hashlib
import requests
from datetime import date
from scrapers.arxiv_scraper import score_agi_relevance

LABS = {
    "Anthropic": {
        "url": "https://www.anthropic.com/research",
        "link_pattern": r'href="(/research/[^"]+)"',
        "base": "https://www.anthropic.com",
    },
    "OpenAI": {
        "url": "https://openai.com/research",
        "link_pattern": r'href="(/research/[^"]+)"',
        "base": "https://openai.com",
    },
    "DeepMind": {
        "url": "https://deepmind.google/research/publications/",
        "link_pattern": r'href="(https://deepmind\.google/research/publications/[^"]+)"',
        "base": "",
    },
    "Meta AI": {
        "url": "https://ai.meta.com/research/publications/",
        "link_pattern": r'href="(https://ai\.meta\.com/research/publications/[^"]+)"',
        "base": "",
    },
}

def scrape_lab(lab_name: str, config: dict) -> list[dict]:
    """Scrape a single lab's research page."""
    items = []
    try:
        r = requests.get(config["url"], timeout=20, headers={
            "User-Agent": "Mozilla/5.0 AGIPossibleBot/1.0"
        })
        r.raise_for_status()
        html = r.text

        links = re.findall(config["link_pattern"], html)
        links = list(dict.fromkeys(links))[:20]  # dedup, first 20

        # Extract titles near links
        for link in links:
            full_url = config["base"] + link if config["base"] else link

            # Skip non-content pages
            skip_patterns = ["/research/overview", "/research/index", "#"]
            if any(p in full_url for p in skip_patterns):
                continue

            # Try to get title from surrounding text
            escaped = re.escape(link)
            title_match = re.search(
                escaped + r'[^>]*>([^<]{10,100})<',
                html
            )
            title = title_match.group(1).strip() if title_match else full_url.split("/")[-1].replace("-", " ").title()
            title = re.sub(r'\s+', ' ', title).strip()

            uid = hashlib.md5(full_url.encode()).hexdigest()[:12]
            score = score_agi_relevance(title, "")

            items.append({
                "id": f"lab:{uid}",
                "title": title,
                "url": full_url,
                "abstract": "",
                "authors": [lab_name],
                "published_date": date.today().isoformat(),
                "source": lab_name,
                "source_type": "lab_blog",
                "agi_score": score + 8,  # Lab publications get boost
            })

        print(f"  {lab_name}: {len(items)} items found")
        time.sleep(2)
    except Exception as e:
        print(f"  {lab_name} scrape error: {e}")

    return items

def scrape_all_labs() -> list[dict]:
    """Scrape all frontier labs."""
    all_items = []
    for lab_name, config in LABS.items():
        items = scrape_lab(lab_name, config)
        all_items.extend(items)
    return all_items
