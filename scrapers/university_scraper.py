"""
Scrapes top university AI lab publications:
Stanford HAI, MIT CSAIL, UC Berkeley BAIR, CMU.
"""

from __future__ import annotations
import re
import time
import hashlib
import requests
from datetime import date
from scrapers.arxiv_scraper import score_agi_relevance

UNIVERSITIES = {
    "Stanford HAI": {
        "url": "https://hai.stanford.edu/news",
        "link_pattern": r'href="(/news/[^"]+)"',
        "base": "https://hai.stanford.edu",
    },
    "Berkeley BAIR": {
        "url": "https://bair.berkeley.edu/blog/",
        "link_pattern": r'href="(https://bair\.berkeley\.edu/blog/\d{4}/[^"]+)"',
        "base": "",
    },
    "MIT CSAIL": {
        "url": "https://www.csail.mit.edu/news",
        "link_pattern": r'href="(/news/[^"?#]+)"',
        "base": "https://www.csail.mit.edu",
    },
}

def scrape_university(name: str, config: dict) -> list[dict]:
    """Scrape a university AI lab news/blog page."""
    items = []
    try:
        r = requests.get(config["url"], timeout=20, headers={
            "User-Agent": "Mozilla/5.0 AGIPossibleBot/1.0"
        })
        r.raise_for_status()
        html = r.text

        links = re.findall(config["link_pattern"], html)
        links = list(dict.fromkeys(links))[:15]

        for link in links:
            full_url = config["base"] + link if config["base"] else link

            if not full_url.startswith("http"):
                continue

            slug = full_url.split("/")[-1].replace("-", " ").replace("_", " ").title()
            title_match = re.search(
                re.escape(link) + r'[^>]*>\s*(?:<[^>]+>)?\s*([^<]{10,150})',
                html
            )
            title = title_match.group(1).strip() if title_match else slug
            title = re.sub(r'\s+', ' ', title).strip()

            uid = hashlib.md5(full_url.encode()).hexdigest()[:12]
            score = score_agi_relevance(title, "")

            items.append({
                "id": f"uni:{uid}",
                "title": title,
                "url": full_url,
                "abstract": "",
                "authors": [name],
                "published_date": date.today().isoformat(),
                "source": name,
                "source_type": "university",
                "agi_score": score + 3,
            })

        print(f"  {name}: {len(items)} items found")
        time.sleep(1.5)
    except Exception as e:
        print(f"  {name} scrape error: {e}")

    return items

def scrape_all_universities() -> list[dict]:
    """Scrape all university labs."""
    all_items = []
    for name, config in UNIVERSITIES.items():
        items = scrape_university(name, config)
        all_items.extend(items)
    return all_items
