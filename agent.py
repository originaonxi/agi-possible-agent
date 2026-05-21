"""
Daily AGI Possible — Main Agent v2
Runs at 8am PST daily via cron.

Pipeline:
1. Scrape all sources (arXiv, HF, Labs, OpenReview)
2. Compute deltas (new content only, SQLite)
3. Fetch Reddit r/MachineLearning social buzz
4. Enrich with Semantic Scholar + Papers With Code signals
5. Composite score (keyword + citations + code + reddit + lab prestige)
6. Claude selects top 1-5 (quality threshold, not always 5)
7. Claude writes deep stories
8. Send beautiful HTML email
"""

from __future__ import annotations
import sys
from datetime import date, datetime

from storage.database import (
    init_db, save_content, mark_included,
    get_issue_number, log_email, get_total_seen
)
from scrapers.arxiv_scraper import scrape_all as scrape_arxiv
from scrapers.hf_scraper import scrape_hf_papers
from scrapers.labs_scraper import scrape_all_labs
from scrapers.openreview_scraper import scrape_all_conferences
from scrapers.reddit_scraper import scrape_reddit_papers, build_reddit_index
from scrapers.semantic_scholar import enrich_batch
from scrapers.papers_with_code import get_paper_signals, compute_pwc_score
from scoring import rank_and_filter, QUALITY_THRESHOLD, MAX_STORIES, MIN_STORIES
from writer import select_top_stories, write_story, write_why_these_five
from emailer import build_email_html, send_email
from config import EMAIL_TO

def run():
    print()
    print("=" * 60)
    print("  DAILY AGI POSSIBLE v2 — Newsletter Agent")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M PST')}")
    print("=" * 60)
    print()

    init_db()
    issue_number = get_issue_number()
    print(f"  Issue #{issue_number:03d}")
    print()

    # ─── STEP 1: SCRAPE ALL SOURCES ──────────────────────────────
    print("  [1/7] Scraping all sources...")
    all_content = []

    print("  -> arXiv (cs.LG, cs.AI, cs.CL, stat.ML)")
    arxiv_content = scrape_arxiv()
    all_content.extend(arxiv_content)

    print("  -> HuggingFace Papers (community-upvoted)")
    hf_content = scrape_hf_papers()
    all_content.extend(hf_content)

    print("  -> Frontier labs (Anthropic, OpenAI, DeepMind, Meta AI)")
    lab_content = scrape_all_labs()
    all_content.extend(lab_content)

    print("  -> OpenReview (ICLR, NeurIPS, ICML conference papers)")
    conf_content = scrape_all_conferences()
    all_content.extend(conf_content)

    total_scraped = len(all_content)
    print(f"\n  Total scraped: {total_scraped} items")

    # ─── STEP 2: DELTA FILTER ────────────────────────────────────
    print("\n  [2/7] Computing deltas (deduplication)...")
    new_content = save_content(all_content)
    new_today = len(new_content)
    print(f"  New today: {new_today} (of {total_scraped} total)")
    print(f"  All-time database: {get_total_seen()} items")

    if new_today == 0:
        print("\n  No new content today. Skipping email.")
        log_email(issue_number, [], False, "No new content")
        return

    # ─── STEP 3: REDDIT BUZZ ─────────────────────────────────────
    print("\n  [3/7] Fetching Reddit r/MachineLearning buzz...")
    reddit_papers = scrape_reddit_papers()
    reddit_index = build_reddit_index(reddit_papers)
    print(f"  Reddit signals: {len(reddit_index)} papers with community scores")

    # ─── STEP 4: SEMANTIC SCHOLAR ENRICHMENT ─────────────────────
    print("\n  [4/7] Enriching with Semantic Scholar (citation velocity, author h-index)...")
    arxiv_papers = [p for p in new_content if p.get("id", "").startswith("arxiv:")]
    arxiv_papers.sort(key=lambda x: x.get("agi_score", 0), reverse=True)
    to_enrich = arxiv_papers[:40]
    enriched = enrich_batch(to_enrich, delay=0.4)
    enriched_by_id = {p["id"]: p for p in enriched}
    for p in new_content:
        if p["id"] in enriched_by_id:
            p.update(enriched_by_id[p["id"]])
    print(f"  S2 enriched: {len(enriched)} papers")

    # ─── STEP 5: PAPERS WITH CODE ────────────────────────────────
    print("\n  [5/7] Checking Papers With Code (GitHub stars, implementations)...")
    for p in new_content:
        if p.get("id", "").startswith("arxiv:") and p.get("agi_score", 0) >= 10:
            pid = p["id"].replace("arxiv:", "")
            signals = get_paper_signals(pid)
            p["pwc"] = signals
            p["pwc_score"] = compute_pwc_score(signals)
        else:
            p["pwc"] = {}
            p["pwc_score"] = 0

    # ─── STEP 6: COMPOSITE SCORE + RANK ──────────────────────────
    print("\n  [6/7] Composite scoring (keyword + citations + code + reddit + lab prestige)...")
    qualified = rank_and_filter(new_content, reddit_index)
    print(f"  Papers above quality threshold ({QUALITY_THRESHOLD}): {len(qualified)}")

    if not qualified:
        print(f"\n  No papers cleared quality bar today. Skipping email.")
        log_email(issue_number, [], False, f"No papers above threshold {QUALITY_THRESHOLD}")
        return

    # ─── STEP 7: CLAUDE SELECTS + WRITES ─────────────────────────
    print(f"\n  [7/7] Claude selects best {MIN_STORIES}-{MAX_STORIES}, then writes stories...")
    top_candidates = qualified[:20]
    top_stories = select_top_stories(top_candidates, qualified_count=len(qualified))
    actual_count = len(top_stories)
    print(f"  Selected: {actual_count} stories")
    for s in top_stories:
        score = s.get("composite_score", 0)
        bd = s.get("score_breakdown", {})
        print(f"    [{score}] {s.get('title','')[:55]}")
        print(f"           kw={bd.get('keyword',0)} s2={bd.get('s2',0)} "
              f"pwc={bd.get('pwc',0)} lab={bd.get('lab',0)} reddit={bd.get('reddit',0)}")

    written_stories = []
    for i, item in enumerate(top_stories, 1):
        print(f"  Writing story {i}/{actual_count}: {item.get('title','')[:50]}...")
        story = write_story(item, i, new_today)
        written_stories.append(story)

    why_these = write_why_these_five(written_stories, total_scraped)

    # ─── SEND ─────────────────────────────────────────────────────
    print(f"\n  Sending to {EMAIL_TO}...")
    today_str = date.today().strftime("%B %d, %Y")
    subject = (
        f"Daily AGI Possible #{issue_number:03d} — {today_str} | "
        f"{actual_count} must-reads from {new_today} new papers"
    )

    html = build_email_html(
        issue_number=issue_number,
        stories=written_stories,
        why_these_five=why_these,
        total_scraped=total_scraped,
        new_today=new_today,
    )

    try:
        send_email(html, subject)
        story_ids = [s["item"].get("url", "") for s in written_stories]
        mark_included(story_ids, date.today().isoformat())
        log_email(issue_number, story_ids, True)
        print(f"\n  Issue #{issue_number:03d} sent. {actual_count} stories.")
    except Exception as e:
        log_email(issue_number, [], False, str(e))
        print(f"  Send failed: {e}")
        raise

    print()
    print("  Done. See you tomorrow at 8am PST.")
    print()

if __name__ == "__main__":
    run()
