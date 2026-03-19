"""
The heart of the newsletter.
Claude writes 5 deep stories from the top content.
Format: Story | Logic | Maths | Impact | Why AGI-relevant
"""

from __future__ import annotations
import json
import anthropic
from datetime import date
from config import ANTHROPIC_API_KEY, TOP_N_STORIES

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

WRITER_SYSTEM = """You are the writer of "Daily AGI Possible" — the best
ML newsletter in the world. Your job: explain cutting-edge AI research
to smart, curious people in a way that makes them feel like they just had
coffee with a brilliant friend who works at a frontier lab.

Your writing style:
- Human, warm, direct. No corporate jargon.
- Open with a vivid analogy or story hook
- Explain the LOGIC clearly — what problem does this solve and how?
- Include the KEY MATHS if any — simplified but accurate
- Give real IMPACT — what changes because this exists?
- End with WHY THIS MATTERS FOR AGI — be specific
- Never say "groundbreaking" or "revolutionary" — show, don't tell
- Always mention job skills or practical implications where relevant
- Use arrows for flow, not bullet points
- Max 400 words per story"""

SELECTOR_SYSTEM = """You are the editor of "Daily AGI Possible."
Your job: pick the 5 most AGI-relevant items from today's list.

Criteria (in order of importance):
1. Direct relevance to AGI: self-improvement, reasoning, scaling, alignment, evaluation
2. Novelty: genuinely new idea or result, not incremental
3. Impact: if true, does this change something important?
4. Diversity: try to cover different aspects (architecture, training, evaluation, application, theory)
5. Clarity: can this be explained to a smart non-specialist?

Avoid: pure application papers, narrow domain papers, papers with no AGI angle"""

def select_top_stories(candidates: list[dict], n: int = TOP_N_STORIES) -> list[dict]:
    """
    Use Claude to select the top N most AGI-relevant stories.
    Two-stage: sort by score, then Claude picks the best N.
    """
    # Stage 1: sort by agi_score, take top 20 candidates
    sorted_candidates = sorted(candidates, key=lambda x: x.get("agi_score", 0), reverse=True)
    top_candidates = sorted_candidates[:20]

    if not top_candidates:
        return []

    # Stage 2: Claude selects the best N
    candidate_list = "\n".join([
        f"{i+1}. [{c.get('source_type','?')}] {c.get('title','')} (score:{c.get('agi_score',0)}) — {c.get('url','')}"
        for i, c in enumerate(top_candidates)
    ])

    try:
        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            system=SELECTOR_SYSTEM,
            messages=[{
                "role": "user",
                "content": f"""Today's new ML content ({len(top_candidates)} items):

{candidate_list}

Select the {n} most AGI-relevant items. Return ONLY a JSON array of the numbers (1-based):
Example: [3, 7, 12, 1, 9]

Return only the JSON array, nothing else."""
            }]
        )

        text = msg.content[0].text.strip()
        indices = json.loads(text)
        selected = [top_candidates[i-1] for i in indices if 0 < i <= len(top_candidates)]
        return selected[:n]

    except Exception as e:
        print(f"  Selector error: {e}, using score-based top {n}")
        return top_candidates[:n]

def write_story(item: dict, story_number: int, total_items_today: int) -> dict:
    """
    Write one deep story for an ML paper/post.
    Returns dict with html_content and metadata.
    """

    # Fetch abstract if missing
    abstract = item.get("abstract", "")
    if not abstract and "arxiv.org" in item.get("url", ""):
        abstract = _fetch_arxiv_abstract(item["url"])

    prompt = f"""Write story #{story_number} for today's "Daily AGI Possible" newsletter.

Paper/Post details:
Title: {item.get('title', 'Unknown')}
Source: {item.get('source', 'Unknown')}
URL: {item.get('url', '')}
Abstract/Description: {abstract or 'Not available — use your knowledge of this paper/topic'}
Authors: {', '.join(item.get('authors', [])) or 'Unknown'}

Write the story in this exact structure:

### {story_number}. [TITLE]
**Story**: [Hook — open with a vivid analogy, surprising fact, or human scenario. 2-3 sentences.]

**The Logic**: [What problem does this solve? How does it work? Walk through the key insight. 3-4 sentences.]

**The Maths** (if applicable): [The key equation or algorithm, explained simply. If no maths, explain the mechanism.]

**Impact**: [What changes if this works? Be specific — not "this will change AI" but "this means X can now do Y". 2-3 sentences.]

**Why this gets us closer to AGI**: [Specific, honest. What capability gap does this close? 2 sentences max.]

Keep it under 380 words total. Write like you're explaining this to a brilliant friend over coffee."""

    try:
        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=800,
            system=WRITER_SYSTEM,
            messages=[{"role": "user", "content": prompt}]
        )
        content = msg.content[0].text.strip()

        return {
            "number": story_number,
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "source": item.get("source", ""),
            "content": content,
            "item": item,
        }
    except Exception as e:
        return {
            "number": story_number,
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "source": item.get("source", ""),
            "content": f"*Story generation failed: {e}*",
            "item": item,
        }

def _fetch_arxiv_abstract(url: str) -> str:
    """Fetch abstract from arXiv page."""
    import requests, re
    try:
        r = requests.get(url, timeout=10)
        match = re.search(r'class="abstract[^"]*"[^>]*>(.*?)</blockquote>', r.text, re.DOTALL)
        if match:
            abstract = re.sub(r'<[^>]+>', '', match.group(1)).strip()
            return abstract.replace("Abstract:", "").strip()
    except Exception:
        pass
    return ""

def write_why_these_five(stories: list[dict], total_scraped: int) -> str:
    """
    Write the closing section: why these 5 out of all content today.
    """
    titles = [f"{s['number']}. {s['title']}" for s in stories]

    try:
        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            messages=[{"role": "user", "content": f"""Write a 3-sentence closing for "Daily AGI Possible" newsletter.

Today we ingested ~{total_scraped} new items. We chose these 5:
{chr(10).join(titles)}

Explain WHY these 5 specifically — what made them stand out from the rest.
Be specific about the signal (not just "they were the best").
Tone: human, direct, like a sharp editor explaining their choices.
Return only the 3 sentences, no headers."""}]
        )
        return msg.content[0].text.strip()
    except Exception:
        return f"Out of ~{total_scraped} new items today, these 5 had the highest AGI signal-to-noise ratio — direct attacks on self-improvement, architectural scaling, and evaluation gaps that matter."
