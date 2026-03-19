"""
Daily AGI Possible — Main Agent
Runs at 8am PST daily via cron.

Pipeline:
1. Scrape all sources
2. Compute deltas (new content only)
3. Score by AGI relevance
4. Claude selects top 5
5. Claude writes 5 deep stories
6. Send beautiful HTML email
7. Log to SQLite
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
from scrapers.university_scraper import scrape_all_universities
from writer import select_top_stories, write_story, write_why_these_five
from emailer import build_email_html, send_email
from config import EMAIL_TO

def run():
    print()
    print("=" * 55)
    print("  DAILY AGI POSSIBLE — Newsletter Agent")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M PST')}")
    print("=" * 55)
    print()

    # Initialize database
    init_db()
    issue_number = get_issue_number()
    print(f"  Issue #{issue_number:03d}")
    print()

    # --- STEP 1: SCRAPE ALL SOURCES ---
    print("  [1/5] Scraping all sources...")
    all_content = []

    print("  -> arXiv (cs.LG, cs.AI, cs.CL, stat.ML)")
    arxiv_content = scrape_arxiv()
    all_content.extend(arxiv_content)

    print("  -> HuggingFace Papers")
    hf_content = scrape_hf_papers()
    all_content.extend(hf_content)

    print("  -> Frontier labs (Anthropic, OpenAI, DeepMind, Meta AI)")
    lab_content = scrape_all_labs()
    all_content.extend(lab_content)

    print("  -> University labs (Stanford, MIT, Berkeley)")
    uni_content = scrape_all_universities()
    all_content.extend(uni_content)

    total_scraped = len(all_content)
    print(f"\n  Total scraped: {total_scraped} items")

    # --- STEP 2: COMPUTE DELTAS ---
    print("\n  [2/5] Computing deltas (new content only)...")
    new_content = save_content(all_content)
    new_today = len(new_content)
    print(f"  New today: {new_today} (of {total_scraped} total)")
    print(f"  All-time database: {get_total_seen()} items")

    if new_today == 0:
        print("\n  No new content today. Skipping email.")
        log_email(issue_number, [], False, "No new content")
        return

    # --- STEP 3: SELECT TOP 5 ---
    print("\n  [3/5] Selecting top 5 with Claude...")
    top_stories = select_top_stories(new_content)
    print(f"  Selected: {len(top_stories)} stories")
    for s in top_stories:
        print(f"    -> [{s.get('source_type','?')}] {s.get('title','')[:60]}")

    # --- STEP 4: WRITE STORIES ---
    print("\n  [4/5] Writing stories with Claude...")
    written_stories = []
    for i, item in enumerate(top_stories, 1):
        print(f"  Writing story {i}/5: {item.get('title','')[:50]}...")
        story = write_story(item, i, new_today)
        written_stories.append(story)

    why_five = write_why_these_five(written_stories, total_scraped)

    # --- STEP 5: SEND EMAIL ---
    print(f"\n  [5/5] Sending newsletter to {EMAIL_TO}...")

    today_str = date.today().strftime("%B %d, %Y")
    subject = f"Daily AGI Possible #{issue_number:03d} — {today_str} | {new_today} new deltas"

    html = build_email_html(
        issue_number=issue_number,
        stories=written_stories,
        why_these_five=why_five,
        total_scraped=total_scraped,
        new_today=new_today,
    )

    try:
        send_email(html, subject)
        story_ids = [s["item"].get("url", "") for s in written_stories]
        mark_included(story_ids, date.today().isoformat())
        log_email(issue_number, story_ids, True)
        print(f"  Issue #{issue_number:03d} sent to {EMAIL_TO}")
    except Exception as e:
        log_email(issue_number, [], False, str(e))
        print(f"  Send failed: {e}")
        raise

    print()
    print("  Done. See you tomorrow at 8am PST.")
    print()

if __name__ == "__main__":
    run()
