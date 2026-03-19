# Daily AGI Possible

**Every morning at 8am PST — the 5 ML papers and posts that actually matter for AGI, written like a brilliant friend explaining them over coffee.**

An autonomous agent that scrapes the entire ML frontier, computes deltas vs yesterday, picks the 5 most AGI-relevant stories, has Claude write deep explanations, and sends a beautiful dark-mode HTML email. Every day. No duplicates. No noise.

## What it does

```
8:00 AM PST daily:

  Scrape 6 sources              Compute deltas           Claude selects top 5
  ┌─────────────┐              ┌──────────────┐         ┌──────────────────┐
  │ arXiv (4)   │──┐           │              │         │                  │
  │ HuggingFace │  │  ~200     │  SQLite DB   │  new    │  Claude ranks    │
  │ Anthropic   │──┼─ items ──>│  seen before?│──only──>│  by AGI signal   │
  │ OpenAI      │  │  /day     │  deduplicate │  ~50    │  picks 5 best    │
  │ DeepMind    │  │           │              │         │                  │
  │ Meta AI     │──┘           └──────────────┘         └────────┬─────────┘
  │ Stanford    │                                                │
  │ MIT CSAIL   │                                                v
  │ Berkeley    │                                       ┌──────────────────┐
  └─────────────┘                                       │ Claude writes 5  │
                                                        │ deep stories     │
                                                        │ Story/Logic/     │
                                                        │ Maths/Impact/AGI │
                                                        └────────┬─────────┘
                                                                 │
                                                                 v
                                                        ┌──────────────────┐
                                                        │ Beautiful HTML   │
                                                        │ email via Gmail  │
                                                        │ SMTP             │
                                                        └──────────────────┘
```

## Why delta-only matters

Every URL ever seen is stored in SQLite. Run it 100 days in a row — you'll never see the same paper twice. The agent only writes about what's genuinely new since yesterday.

## Sources scraped

| Source | What | Count |
|--------|------|-------|
| arXiv cs.LG | Machine Learning | ~30/day |
| arXiv cs.AI | Artificial Intelligence | ~30/day |
| arXiv cs.CL | Computation & Language | ~30/day |
| arXiv stat.ML | Statistics ML | ~30/day |
| HuggingFace Papers | Community-upvoted papers | ~20/day |
| Anthropic Research | Frontier lab blog | ~5 |
| OpenAI Research | Frontier lab blog | ~5 |
| DeepMind Publications | Frontier lab blog | ~10 |
| Meta AI Research | Frontier lab blog | ~10 |
| Stanford HAI | University AI news | ~10 |
| MIT CSAIL | University AI news | ~10 |
| Berkeley BAIR | University AI blog | ~5 |

## Email format

Each of the 5 stories follows this structure:

- **Story** — Hook with a vivid analogy or surprising fact
- **The Logic** — What problem does this solve? How does it work?
- **The Maths** — Key equation or mechanism, simplified but accurate
- **Impact** — What changes because this exists? Be specific.
- **Why this gets us closer to AGI** — What capability gap does this close?

## AGI relevance scoring

Content is scored by keyword signals:

- **High (+10)**: self-improvement, reasoning, agents, planning, world model, scaling law, alignment, chain of thought, test-time compute, agentic
- **Medium (+5)**: transformer, LLM, fine-tuning, evaluation, safety, interpretability, MoE, distillation
- **Low (-2)**: image generation, video, protein, drug, climate (penalized — not AGI-relevant)

Claude then selects the final 5 from the top 20 scored candidates.

## Quick start

```bash
# 1. Clone
git clone https://github.com/originaonxi/agi-possible-agent.git
cd agi-possible-agent

# 2. Install
pip3 install -r requirements.txt

# 3. Set environment variables
export ANTHROPIC_API_KEY="your_key"
export SMTP_USER="your_gmail@gmail.com"
export SMTP_PASS="your_gmail_app_password"
export EMAIL_TO="recipient@email.com"

# 4. Run
python3 agent.py

# 5. Schedule daily at 8am PST
bash scheduler.sh
```

## Cost

~$0.10/day in Claude API calls (7 calls to claude-sonnet-4-20250514: 1 selector + 5 stories + 1 closing).

## Author

**Anmol Chaudhary** — CTO @ Aonxi, Ex-Meta, Ex-Apple
