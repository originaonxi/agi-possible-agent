"""
The heart of the newsletter.
Claude writes 5 deep stories from the top content.
Format: Story | Logic | Maths | Impact | Why AGI-relevant
"""

from __future__ import annotations
import json
from openai import OpenAI
from config import TOP_N_STORIES, REQUESTY_API_KEY, REQUESTY_BASE_URL, SELECTOR_MODEL, WRITER_MODEL

_client = OpenAI(api_key=REQUESTY_API_KEY, base_url=REQUESTY_BASE_URL)


def _chat(system: str, user: str, max_tokens: int = 800, model: str = WRITER_MODEL) -> str:
    """Call LLM via Requesty. Falls back to gpt-4o if primary model fails."""
    try:
        resp = _client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        if model != "openai/gpt-4o":
            resp = _client.chat.completions.create(
                model="openai/gpt-4o",
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user},
                ],
            )
            return resp.choices[0].message.content.strip()
        raise RuntimeError(f"LLM call failed: {e}")

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

SELECTOR_SYSTEM = """You are the editor of "Daily AGI Possible" — the most signal-dense AI research newsletter.
Your job: pick 1 to 5 papers every AGI researcher MUST read today.

These candidates are pre-scored by: citation velocity, lab prestige, Reddit buzz, GitHub stars, keyword signals.
Your job is final editorial judgment.

Strict priority:
1. Papers that could change how the world thinks about intelligence or AGI — not incremental
2. Papers from Anthropic, OpenAI, DeepMind, Meta FAIR, Google, or top universities (Stanford/MIT/Berkeley/CMU)
3. Papers the research community is visibly excited about (high s2/reddit/pwc scores)
4. Surprising results or genuinely new approaches
5. At most 1 paper per area (reasoning, alignment, architecture, evaluation, training)

CRITICAL: If nothing is truly remarkable today, pick 1-2 papers. Do NOT pad to 5 with mediocre work.
A researcher's time is precious. Quality over quantity."""

def select_top_stories(candidates: list[dict], n: int = TOP_N_STORIES, qualified_count: int = 0) -> list[dict]:
    """
    Claude picks 1-5 best stories from pre-scored candidates.
    Dynamic count: don't force 5 if nothing is remarkable.
    """
    import re as _re
    if not candidates:
        return []

    candidate_list = "\n".join([
        f"{i+1}. [score:{c.get('composite_score', c.get('agi_score',0))}] [{c.get('source_type','?')}] {c.get('title','')} — {c.get('source','')}\n"
        f"   s2={c.get('score_breakdown',{}).get('s2',0)} lab={c.get('score_breakdown',{}).get('lab',0)} "
        f"reddit={c.get('score_breakdown',{}).get('reddit',0)} pwc={c.get('score_breakdown',{}).get('pwc',0)}\n"
        f"   {c.get('url','')}"
        for i, c in enumerate(candidates)
    ])

    max_pick = min(n, len(candidates))

    try:
        text = _chat(
            SELECTOR_SYSTEM,
            f"""Today's pre-scored candidates ({len(candidates)} from {qualified_count} qualified):

{candidate_list}

Pick 1 to {max_pick} that every AGI researcher MUST read today.
Return ONLY a JSON array: [3, 1, 7]""",
            max_tokens=300,
            model=SELECTOR_MODEL,
        )
        # Extract JSON array — handle empty or malformed responses
        if not text:
            raise ValueError("Empty response from LLM")
        match = _re.search(r'\[[\d,\s]+\]', text)
        indices = json.loads(match.group() if match else text)
        selected = [candidates[i-1] for i in indices if 0 < i <= len(candidates)]
        return selected[:max_pick]

    except Exception as e:
        print(f"  Selector error: {e}, using score-based top 3")
        return candidates[:min(3, max_pick)]

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
        content = _chat(WRITER_SYSTEM, prompt, max_tokens=800)
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

    n = len(stories)
    try:
        return _chat(
            "You are the editor of a top AI research newsletter. Be direct, human, no filler.",
            f"""Write a 3-sentence closing for "Daily AGI Possible" newsletter.

Today we ingested ~{total_scraped} new items. We chose {n}:
{chr(10).join(titles)}

Explain WHY these specifically — what signal made them stand out.
Tone: sharp editor explaining choices. Return only 3 sentences, no headers.""",
            max_tokens=300,
        )
    except Exception:
        return f"Out of ~{total_scraped} new items today, these {n} had the highest composite signal — citation velocity, lab prestige, community buzz, and direct AGI relevance."
