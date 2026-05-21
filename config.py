import os
from dotenv import load_dotenv
load_dotenv()

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# Requesty — unified LLM router (Claude/GPT/Gemini via one key)
# Primary LLM backend when Anthropic direct credits are low
REQUESTY_API_KEY = os.environ.get(
    "REQUESTY_API_KEY",
    "rqsty-sk-/JTViZRyS62Hdxsq1s2DGukrmTe4GTgjfmoT5ejWJ5ecV8UZuHFr14ZrEbXgCpt61QmZ6B+B/PFM4gx4o48A89xkEXANC+XfEllnEXUy7QA=",
)
REQUESTY_BASE_URL = "https://router.requesty.ai/v1"

# Codex + Gemini CLI both independently recommend Claude Opus 4.7 for writing.
# GPT-4o writes "newsletter-ese" (filler). Opus 4.7 is technically sharp + concise.
# gpt-4o for selector: reliable JSON, precise reasoning.
SELECTOR_MODEL = "openai/gpt-4o"
WRITER_MODEL   = "anthropic/claude-opus-4-7"

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = os.environ.get("SMTP_USER", "lifeislovesam@gmail.com")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
EMAIL_TO = os.environ.get("EMAIL_TO", "iamsamios@icloud.com")

# How many stories to select for the email
TOP_N_STORIES = 5

# AGI relevance scoring keywords (higher = more relevant)
AGI_SIGNALS = {
    "high": [
        "self-improvement", "recursive", "AGI", "general intelligence",
        "reasoning", "agents", "planning", "world model", "emergent",
        "scaling law", "multimodal", "alignment", "RLHF", "RLAIF",
        "chain of thought", "tool use", "autonomous", "benchmark",
        "self-play", "reinforcement learning from human feedback",
        "test-time compute", "inference scaling", "agentic",
    ],
    "medium": [
        "transformer", "attention", "LLM", "foundation model",
        "fine-tuning", "instruction following", "hallucination",
        "evaluation", "safety", "interpretability", "mechanistic",
        "sparse", "mixture of experts", "MoE", "quantization",
        "distillation", "synthetic data", "reward model",
    ],
    "low": [
        "image generation", "video", "speech", "protein", "drug",
        "climate", "robotics", "diffusion", "GAN",
    ],
}

# Sources to scrape
SOURCES = {
    "arxiv": [
        "https://arxiv.org/list/cs.LG/recent",
        "https://arxiv.org/list/cs.AI/recent",
        "https://arxiv.org/list/cs.CL/recent",
        "https://arxiv.org/list/stat.ML/recent",
    ],
    "hf_papers": "https://huggingface.co/papers",
    "labs": {
        "anthropic": "https://www.anthropic.com/research",
        "openai": "https://openai.com/research",
        "deepmind": "https://deepmind.google/research/publications/",
        "meta_ai": "https://ai.meta.com/research/publications/",
    },
    "universities": {
        "stanford_hai": "https://hai.stanford.edu/news",
        "mit_csail": "https://www.csail.mit.edu/news",
        "berkeley_bair": "https://bair.berkeley.edu/blog/",
    },
}
