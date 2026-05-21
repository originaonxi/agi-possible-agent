"""
Composite scoring engine.
Replaces pure keyword scoring with a weighted multi-signal system.

Final score = keyword + s2 + pwc + reddit + lab_prestige + hf_boost
Papers must score >= QUALITY_THRESHOLD to be included.
Dynamically selects 1-5 papers based on quality, not always exactly 5.
"""

from __future__ import annotations
from config import AGI_SIGNALS

# Tier-1 labs — papers from these always get a prestige boost
LAB_PRESTIGE = {
    # Score 30 — world-class frontier labs
    "anthropic": 30, "openai": 30, "deepmind": 30, "google deepmind": 30,
    "google brain": 30, "meta ai": 28, "meta fair": 28,
    # Score 20 — top research labs
    "microsoft research": 20, "apple ml": 20, "nvidia research": 20,
    "amazon science": 18, "allen ai": 18, "hugging face": 15,
    # Score 15 — top universities
    "stanford": 15, "mit": 15, "berkeley": 15, "carnegie mellon": 15,
    "cmu": 15, "university of toronto": 12, "oxford": 12, "cambridge": 12,
    "eth zurich": 12, "princeton": 12, "yale": 10, "columbia": 10,
    # Emerging (worth tracking)
    "mistral": 12, "cohere": 10, "eleutherai": 12, "ai2": 15,
}

# Papers touching these topics directly advance AGI — strongest signal
CORE_AGI_KEYWORDS = {
    "critical": [
        "reasoning", "chain of thought", "test-time compute", "inference scaling",
        "world model", "self-improvement", "self-play", "autonomous agent",
        "alignment", "constitutional ai", "rlhf", "rlaif", "reward model",
        "general intelligence", "agi", "cognitive architecture", "metacognition",
        "in-context learning", "few-shot", "zero-shot", "emergent",
        "o1", "o3", "system 2", "slow thinking", "deliberation",
    ],
    "strong": [
        "scaling law", "foundation model", "large language model", "llm",
        "transformer", "attention mechanism", "mixture of experts", "moe",
        "multimodal", "vision language", "instruction tuning", "sft",
        "evaluation", "benchmark", "capability", "interpretability",
        "mechanistic interpretability", "circuits", "representation",
        "synthetic data", "distillation", "quantization",
    ],
    "penalize": [
        "protein folding", "drug discovery", "climate", "medical imaging",
        "autonomous driving", "speech recognition", "music generation",
        "video generation", "image synthesis", "text-to-image",
    ],
}

# Minimum composite score to be worth including
QUALITY_THRESHOLD = 20

# Max papers per day — only send truly remarkable ones
MAX_STORIES = 5
MIN_STORIES = 1


def compute_keyword_score(title: str, abstract: str) -> int:
    """Keyword-based AGI relevance score."""
    text = (title + " " + (abstract or "")).lower()
    score = 0
    for kw in CORE_AGI_KEYWORDS["critical"]:
        if kw in text:
            score += 10
    for kw in CORE_AGI_KEYWORDS["strong"]:
        if kw in text:
            score += 5
    for kw in CORE_AGI_KEYWORDS["penalize"]:
        if kw in text:
            score -= 4
    # Legacy signals from config
    for kw in AGI_SIGNALS.get("high", []):
        if kw.lower() in text:
            score += 6
    for kw in AGI_SIGNALS.get("medium", []):
        if kw.lower() in text:
            score += 3
    for kw in AGI_SIGNALS.get("low", []):
        if kw.lower() in text:
            score -= 2
    return max(0, score)


def compute_lab_prestige(paper: dict) -> int:
    """Score boost for tier-1 labs and universities."""
    source = (paper.get("source") or "").lower()
    authors = " ".join(paper.get("authors") or []).lower()
    abstract = (paper.get("abstract") or "").lower()
    combined = f"{source} {authors} {abstract}"

    best = 0
    for lab, pts in LAB_PRESTIGE.items():
        if lab in combined:
            best = max(best, pts)
    return best


def compute_hf_boost(paper: dict) -> int:
    """HuggingFace trending papers = community validated."""
    if paper.get("source_type") == "hf_papers":
        return 12
    return 0


def compute_composite_score(paper: dict, reddit_index: dict | None = None) -> int:
    """
    Final composite score for a paper.
    Higher = more must-read. Threshold = QUALITY_THRESHOLD.
    """
    from scrapers.reddit_scraper import compute_reddit_score

    title = paper.get("title", "")
    abstract = paper.get("abstract", "")
    arxiv_id = paper.get("id", "").replace("arxiv:", "")

    keyword = compute_keyword_score(title, abstract)
    s2 = paper.get("s2_score", 0) or 0
    pwc = paper.get("pwc_score", 0) or 0
    lab = compute_lab_prestige(paper)
    hf = compute_hf_boost(paper)

    # Reddit signal
    reddit_data = (reddit_index or {}).get(arxiv_id)
    reddit = compute_reddit_score(reddit_data)
    if reddit_data:
        paper["reddit"] = reddit_data  # attach for email display

    # Conference papers get a hard boost (peer-reviewed)
    conf_boost = 10 if paper.get("source_type") == "conference" else 0

    total = keyword + s2 + pwc + lab + hf + reddit + conf_boost
    paper["composite_score"] = total
    paper["score_breakdown"] = {
        "keyword": keyword, "s2": s2, "pwc": pwc,
        "lab": lab, "hf": hf, "reddit": reddit, "conf": conf_boost,
    }
    return total


def rank_and_filter(papers: list[dict], reddit_index: dict | None = None) -> list[dict]:
    """
    Score all papers, sort by composite score.
    Returns only papers above QUALITY_THRESHOLD.
    """
    for p in papers:
        compute_composite_score(p, reddit_index)

    scored = sorted(papers, key=lambda x: x.get("composite_score", 0), reverse=True)

    # Keep only papers above threshold
    qualified = [p for p in scored if p.get("composite_score", 0) >= QUALITY_THRESHOLD]

    return qualified
