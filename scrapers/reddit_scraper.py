"""
Reddit r/MachineLearning scraper.
Community upvotes + comment counts = real researcher excitement.
Uses public JSON API — no auth needed.
"""

from __future__ import annotations
import requests
import re
from datetime import date

SUBREDDITS = ["MachineLearning", "artificial", "singularity"]
REDDIT_BASE = "https://www.reddit.com"
HEADERS = {"User-Agent": "AGIPossibleBot/2.0 (research newsletter; contact: sam@aonxi.ai)"}

def fetch_top_posts(subreddit: str = "MachineLearning", limit: int = 50) -> list[dict]:
    """Fetch today's hot posts from a subreddit."""
    try:
        url = f"{REDDIT_BASE}/r/{subreddit}/hot.json"
        r = requests.get(url, params={"limit": limit}, headers=HEADERS, timeout=15)
        r.raise_for_status()
        posts = r.json()["data"]["children"]
        return [p["data"] for p in posts]
    except Exception as e:
        print(f"  Reddit {subreddit} error: {e}")
        return []

def scrape_reddit_papers() -> list[dict]:
    """Return papers found on Reddit with their social scores."""
    papers = []
    seen = set()

    for sub in SUBREDDITS:
        posts = fetch_top_posts(sub)
        for post in posts:
            title = post.get("title", "")
            url = post.get("url", "")
            score = post.get("score", 0)
            comments = post.get("num_comments", 0)

            # Only care about arXiv links or paper discussions
            arxiv_match = re.search(r'arxiv\.org/abs/(\d{4}\.\d+)', url + " " + title)
            if not arxiv_match:
                # Try to find arXiv ID in selftext
                selftext = post.get("selftext", "")
                arxiv_match = re.search(r'arxiv\.org/abs/(\d{4}\.\d+)', selftext)

            if not arxiv_match:
                continue

            arxiv_id = arxiv_match.group(1)
            if arxiv_id in seen:
                continue
            seen.add(arxiv_id)

            papers.append({
                "arxiv_id": arxiv_id,
                "reddit_score": score,
                "reddit_comments": comments,
                "reddit_url": f"https://www.reddit.com{post.get('permalink', '')}",
                "subreddit": sub,
            })

    return papers

def build_reddit_index(papers: list[dict]) -> dict[str, dict]:
    """Index Reddit signals by arXiv ID for fast lookup."""
    index = {}
    for p in papers:
        aid = p["arxiv_id"]
        if aid not in index or p["reddit_score"] > index[aid]["reddit_score"]:
            index[aid] = p
    return index

def compute_reddit_score(reddit_data: dict | None) -> int:
    """Convert Reddit signals to a score boost."""
    if not reddit_data:
        return 0
    score = 0
    upvotes = reddit_data.get("reddit_score", 0) or 0
    comments = reddit_data.get("reddit_comments", 0) or 0

    if upvotes >= 2000:
        score += 25
    elif upvotes >= 1000:
        score += 18
    elif upvotes >= 500:
        score += 12
    elif upvotes >= 200:
        score += 8
    elif upvotes >= 50:
        score += 4

    if comments >= 200:
        score += 8
    elif comments >= 100:
        score += 5
    elif comments >= 50:
        score += 3
    elif comments >= 20:
        score += 1

    return min(score, 30)
