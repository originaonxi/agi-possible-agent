"""
Composite scoring for AGI research papers.

Scoring philosophy (from Codex + Gemini CLI consensus):
- Code/open-weights release: papers with code are cited 5x more (Gemini: 30% weight)
- Twitter/X velocity in first 72h: strongest early signal (proxy: HF likes + Reddit)
- Problem primitiveness: solves a bottleneck vs iterates a benchmark
- Author/lab pedigree: high h-index authors from elite labs
- Artifacts: runnable code, model weights, datasets, demos
- Empirical strength: benchmark lift, ablations, generality
"""

from __future__ import annotations
from config import AGI_SIGNALS

LAB_PRESTIGE = {
    "anthropic": 30, "openai": 30, "deepmind": 30, "google deepmind": 30,
    "google brain": 30, "meta ai": 28, "meta fair": 28,
    "microsoft research": 20, "apple ml": 20, "nvidia research": 20,
    "amazon science": 18, "allen ai": 18, "hugging face": 15,
    "stanford": 15, "mit": 15, "berkeley": 15, "carnegie mellon": 15,
    "cmu": 15, "university of toronto": 12, "oxford": 12, "cambridge": 12,
    "eth zurich": 12, "princeton": 12, "yale": 10, "columbia": 10,
    "mistral": 12, "cohere": 10, "eleutherai": 12, "ai2": 15,
}

CORE_AGI_KEYWORDS = {
    "critical": [
        "reasoning", "chain of thought", "test-time compute", "inference scaling",
        "world model", "self-improvement", "self-play", "autonomous agent",
        "alignment", "constitutional ai", "rlhf", "rlaif", "reward model",
        "general intelligence", "agi", "cognitive architecture", "metacognition",
        "in-context learning", "few-shot", "zero-shot", "emergent",
        "o1", "o3", "system 2", "slow thinking", "deliberation",
        "agentic", "tool use", "computer use", "planning",
    ],
    "strong": [
        "scaling law", "foundation model", "large language model", "llm",
        "transformer", "attention mechanism", "mixture of experts", "moe",
        "multimodal", "vision language", "instruction tuning", "sft",
        "evaluation", "benchmark", "capability", "interpretability",
        "mechanistic interpretability", "circuits", "representation",
        "synthetic data", "distillation", "quantization", "speculative decoding",
        "context window", "long context", "retrieval", "rag",
    ],
    "penalize": [
        "protein folding", "drug discovery", "climate", "medical imaging",
        "autonomous driving", "speech recognition", "music generation",
        "video generation", "image synthesis", "text-to-image",
    ],
}

QUALITY_THRESHOLD = 20
MAX_STORIES = 5
MIN_STORIES = 1


def compute_keyword_score(title: str, abstract: str) -> int:
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
    source   = (paper.get("source") or "").lower()
    authors  = " ".join(paper.get("authors") or []).lower()
    abstract = (paper.get("abstract") or "").lower()
    combined = f"{source} {authors} {abstract}"
    best = 0
    for lab, pts in LAB_PRESTIGE.items():
        if lab in combined:
            best = max(best, pts)
    return best


def compute_artifact_score(paper: dict) -> int:
    """
    Gemini: 'Papers with code/open weights are cited 5x more — 30% weight.'
    Codex: 'Artifact availability = 14% of score.'
    This is the single biggest predictor of real-world impact.
    """
    score = 0

    # Papers With Code: has implementation
    pwc = paper.get("pwc_score", 0) or 0
    score += pwc  # already encodes has_code, impl_count, stars, has_official

    # Extra boost for official implementation (not just community re-implementations)
    if paper.get("has_official_code"):
        score += 20

    # Hugging Face model/dataset exists = open weights = massive adoption signal
    if paper.get("has_hf_model"):
        score += 25

    # Paper is on HF Papers trending = community has already validated it
    if paper.get("source_type") == "hf_papers":
        score += 15

    return score


def compute_velocity_score(paper: dict) -> int:
    """
    Gemini: 'Twitter/X velocity in first 72h = strongest early signal (25% weight).'
    Proxy: HF paper likes + Reddit engagement + Semantic Scholar citation velocity.
    """
    score = 0

    # Semantic Scholar citation/influence velocity
    s2 = paper.get("s2_score", 0) or 0
    score += s2

    # Reddit engagement (r/MachineLearning buzz = community filter)
    from scrapers.reddit_scraper import compute_reddit_score
    reddit_data = paper.get("reddit")
    if reddit_data:
        score += compute_reddit_score(reddit_data)

    # HF paper likes = curated community upvotes (proxy for Twitter velocity)
    hf_likes = paper.get("hf_likes", 0) or 0
    if hf_likes >= 100: score += 20
    elif hf_likes >= 50: score += 14
    elif hf_likes >= 20: score += 8
    elif hf_likes >= 5:  score += 4

    return score


def compute_hf_boost(paper: dict) -> int:
    if paper.get("source_type") == "hf_papers":
        return 12
    return 0


def compute_composite_score(paper: dict, reddit_index: dict | None = None) -> int:
    """
    Final composite score. Higher = more must-read.

    Signal weights (approximate, informed by Codex + Gemini):
    - keyword relevance:    ~25% (AGI topic match)
    - artifact availability: ~25% (code + weights + HF = 5x citation predictor)
    - velocity:             ~20% (S2 + Reddit + HF likes = early community signal)
    - lab prestige:         ~20% (frontier labs + top universities)
    - conference boost:     ~10% (peer review stamp)
    """
    from scrapers.reddit_scraper import compute_reddit_score

    title    = paper.get("title", "")
    abstract = paper.get("abstract", "")
    arxiv_id = paper.get("id", "").replace("arxiv:", "")

    # Attach reddit data for display + scoring
    if reddit_index:
        reddit_data = reddit_index.get(arxiv_id)
        if reddit_data:
            paper["reddit"] = reddit_data

    keyword  = compute_keyword_score(title, abstract)
    artifact = compute_artifact_score(paper)
    velocity = compute_velocity_score(paper)
    lab      = compute_lab_prestige(paper)
    conf     = 10 if paper.get("source_type") == "conference" else 0

    total = keyword + artifact + velocity + lab + conf
    paper["composite_score"] = total
    paper["score_breakdown"] = {
        "keyword": keyword, "artifact": artifact,
        "velocity": velocity, "lab": lab, "conf": conf,
    }
    return total


def rank_and_filter(papers: list[dict], reddit_index: dict | None = None) -> list[dict]:
    for p in papers:
        compute_composite_score(p, reddit_index)
    scored    = sorted(papers, key=lambda x: x.get("composite_score", 0), reverse=True)
    qualified = [p for p in scored if p.get("composite_score", 0) >= QUALITY_THRESHOLD]
    return qualified
