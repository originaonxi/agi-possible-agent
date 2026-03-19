"""
SQLite database for tracking all seen content.
Enables delta computation — never send duplicates.
"""

import sqlite3
import json
from datetime import datetime, date
from typing import List, Optional

DB_PATH = "agi_possible.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # All content ever seen
    c.execute("""
        CREATE TABLE IF NOT EXISTS content (
            content_id TEXT PRIMARY KEY,
            title TEXT,
            url TEXT UNIQUE,
            source TEXT,
            source_type TEXT,
            abstract TEXT,
            authors TEXT,
            published_date TEXT,
            agi_score INTEGER DEFAULT 0,
            first_seen_date TEXT,
            included_in_email INTEGER DEFAULT 0,
            email_date TEXT
        )
    """)

    # Daily email log
    c.execute("""
        CREATE TABLE IF NOT EXISTS email_log (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            send_date TEXT,
            issue_number INTEGER,
            story_ids TEXT,
            sent_successfully INTEGER DEFAULT 0,
            error_message TEXT
        )
    """)

    conn.commit()
    conn.close()

def is_seen(url: str) -> bool:
    """Check if URL already in database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT 1 FROM content WHERE url=?", (url,))
    result = c.fetchone() is not None
    conn.close()
    return result

def save_content(items: List[dict]) -> List[dict]:
    """
    Save new content items. Returns only the NEW ones (delta).
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    new_items = []
    today = date.today().isoformat()

    for item in items:
        url = item.get("url", "")
        if not url:
            continue
        try:
            c.execute("""
                INSERT INTO content
                (content_id, title, url, source, source_type, abstract,
                 authors, published_date, agi_score, first_seen_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item.get("id", url),
                item.get("title", ""),
                url,
                item.get("source", ""),
                item.get("source_type", ""),
                item.get("abstract", ""),
                json.dumps(item.get("authors", [])),
                item.get("published_date", today),
                item.get("agi_score", 0),
                today,
            ))
            new_items.append(item)
        except sqlite3.IntegrityError:
            pass  # Already seen

    conn.commit()
    conn.close()
    return new_items

def mark_included(story_ids: List[str], email_date: str):
    """Mark stories as included in email."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for sid in story_ids:
        c.execute(
            "UPDATE content SET included_in_email=1, email_date=? WHERE content_id=? OR url=?",
            (email_date, sid, sid)
        )
    conn.commit()
    conn.close()

def get_issue_number() -> int:
    """Get next issue number."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM email_log WHERE sent_successfully=1")
    count = c.fetchone()[0]
    conn.close()
    return count + 1

def log_email(issue_number: int, story_ids: List[str], success: bool, error: str = ""):
    """Log email send attempt."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO email_log (send_date, issue_number, story_ids, sent_successfully, error_message)
        VALUES (?, ?, ?, ?, ?)
    """, (
        date.today().isoformat(),
        issue_number,
        json.dumps(story_ids),
        1 if success else 0,
        error,
    ))
    conn.commit()
    conn.close()

def get_total_seen() -> int:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM content")
    count = c.fetchone()[0]
    conn.close()
    return count
