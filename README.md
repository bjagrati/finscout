# FinScout

**Stocks, explained in plain English.**

Type a ticker or company name. ~60 seconds later, FinScout gives you the honest story behind that stock — what the company actually does, what's happening with the stock right now, what's working, what to watch out for, and an honest takeaway. No jargon. No "buy/sell" advice. Just the kind of explanation a thoughtful friend would give you.

Built with Anthropic Claude, Playwright, FastAPI, and Pydantic. Hand-rolled ReAct-style agent loop. No agent framework dependencies.

---

## Why This Exists

Most stock research tools were built for people who already understand finance. They throw around terms like P/E ratio, EBITDA, EPS guidance, and forward multiples — useful for analysts, completely opaque to anyone who just wants to understand what's going on with NVIDIA or Tesla.

FinScout flips the audience. Instead of a Bloomberg-terminal-style dashboard, it produces an editorial-style explainer written for actual humans:

- "NVIDIA makes the specialized computer chips that power most of the world's AI systems" — not "NVDA: semiconductor manufacturer with leading data center accelerator position"
- "Worth roughly as much as the entire annual economic output of Germany" — not "Market cap: $4.7T"
- "If you already own it, this doesn't look like a crisis moment" — not "HOLD recommendation"

---

## What It Does

You enter a ticker or company name. FinScout autonomously:

1. Opens a real Chromium browser
2. Visits Yahoo Finance (quote + news tab) and Google News for the ticker
3. Extracts visible text + screenshots from each source
4. Synthesizes everything into a structured `StockExplainer` using Claude
5. Streams progress to your browser via Server-Sent Events
6. Renders the explainer in a clean, editorial layout

The output has these fields, all written in plain English:

- **What they do** — one sentence on the actual business
- **Overall mood** — `very_positive` / `positive` / `mixed` / `negative` / `very_negative`
- **The story** — 3-5 sentence narrative explaining what's happening right now
- **Price + size context** — including a relatable comparison ("worth more than the GDP of Germany")
- **What's working** / **What to watch** — 2-4 plain-English bullets each
- **The honest takeaway** — a thoughtful-friend-over-coffee verdict, never "buy" or "sell"
- **Recent news** — 3-5 headlines with plain-English summaries and mood tags
- **What we couldn't check** — an honest note about the explainer's limitations

### Honest by design

FinScout is engineered to refuse fabrication:

- **Optional financial fields** (`current_price`) return `None` when sources don't show them — Claude is not allowed to invent prices.
- **The `what_we_could_not_check` field** forces the model to articulate gaps explicitly ("we didn't read the full articles behind most headlines, so some nuances may be missing").
- **Ground-truth fields like `sources_visited`** are populated by the code, not the model — the agent cannot claim to have visited URLs it didn't.
- **The system prompt enforces non-advice language**: "worth keeping an eye on" instead of "buy", "real questions to ask" instead of "sell".

---

## Architecture

```
[Browser UI]  ─►  [FastAPI + SSE]  ─►  [Agent loop]  ─►  Playwright (real Chromium)
                                            │                    │
                                            │                    ▼
                                            │            visits Yahoo Finance + Google News
                                            │                    │
                                            ▼                    ▼
                                       Claude API  ◄────  extracted text + screenshots
                                            │
                                            ▼
                                       StockExplainer (Pydantic)
```

### Components

| Path | Role |
|------|------|
| `src/core/page_extractor.py` | Reusable Playwright session: visits any URL, returns cleaned text + screenshot |
| `src/core/models.py` | Pydantic schemas (`NewsItem`, `StockExplainer`) defining the plain-English output |
| `src/core/llm.py` | Reusable `structured_call()` — sends any Pydantic model to Claude via tool use |
| `src/core/agent.py` | The research agent: orchestrates browsing + synthesis. Yields progress events. |
| `src/interfaces/web/api.py` | FastAPI app with streaming research endpoint + static UI |
| `src/interfaces/web/static/` | Editorial-style frontend (HTML/CSS/vanilla JS + SSE, ticker autocomplete) |

---

## Tech Stack

- **Python 3.12**
- **Playwright** — headless or headed Chromium for browsing
- **Anthropic Claude API** (`claude-sonnet-4-6`) — synthesis
- **Pydantic v2** — structured output schemas
- **FastAPI + Uvicorn** — backend with Server-Sent Events streaming
- **Inter + Newsreader + JetBrains Mono** — typography
- **Plain HTML/CSS/vanilla JS** — no frontend framework

---

## Setup

### Prerequisites

- Python 3.10+ (3.12 recommended)
- An Anthropic API key (`sk-ant-...`) — small free credit or ~$5 prepaid is plenty for testing

### Install

```bash
git clone https://github.com/bjagrati/finscout.git
cd finscout

python3.12 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
playwright install chromium
```

### Configure

Create a `.env` file in the project root:

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
BROWSER_MODE=headed
```

`BROWSER_MODE=headed` makes the Chromium window visible (recommended for first run — it's part of the demo). Use `headless` for invisible/faster runs or production.

### Run

```bash
uvicorn src.interfaces.web.api:app --reload --port 8002
```

Open **http://localhost:8002/ui/** — type a ticker or company name (NVDA, Tesla, "apple") and click Explain.

---

## How the Agent Works

The agent loop is intentionally simple — no LangChain, no agent framework:

1. **Browse** — For each source in the configured list (Yahoo Finance quote, Yahoo Finance news, Google News), open it in a real browser, dismiss cookie banners, wait for content to load, extract visible text, screenshot the page.
2. **Bundle** — Combine extracted text into a labeled prompt with clear `═══ SOURCE N ═══` delimiters and per-source URLs (plain text — embedding JSON inputs causes smaller models to echo the JSON back instead of producing output).
3. **Synthesize** — Send the bundle to Claude with a "thoughtful friend explaining a stock" system prompt and the `StockExplainer` Pydantic schema. Claude is forced to call our tool, guaranteeing structured output.
4. **Verify** — Overwrite `sources_visited` with the URLs actually visited (ground truth from the code, not the model).

For v1, the source list is hardcoded. Future versions can let the LLM dynamically choose follow-up sources based on what it learns.

---

## What I Learned Building This

- **Audience reframes everything.** Started as a Bloomberg-style technical research tool. Realized mid-build that "for normal people" was a more interesting product. The pivot required no engine changes — only the schema, prompts, and UI.
- **Hand-rolled ReAct loops are tiny.** ~50 lines of Python. Much easier to debug than framework-wrapped equivalents.
- **Server-Sent Events** are the right primitive for streaming agent progress — built into every browser, lighter than WebSockets, perfect for one-way progress updates.
- **Hallucination resistance is schema design.** Optional fields, explicit "don't invent" rules in field descriptions, `confidence_note` / `what_we_could_not_check` fields, ground-truth-overwrite patterns.
- **Selectors break constantly in real browser automation.** The first NVDA price selector matched 33 elements (Yahoo's page has price widgets for many sidebar tickers); the fix was constraining by `data-symbol` to match only the requested ticker.
- **Plain-text source delimiters beat JSON** as LLM input when the model needs to differentiate "context" from "output target."

---

## Roadmap

- [ ] Dynamic source selection — let the LLM decide what to visit next based on what it learned
- [ ] Article body fetching — currently we read headline lists; full articles would improve quality
- [ ] Earnings call transcript ingestion
- [ ] Compare mode — research two tickers side-by-side
- [ ] Public deployment with rate limiting

---

## License

MIT

---

## Author

Built by Jagrati Bhardwaj. The goal: a stock research tool that anyone can actually use — not just people who already understand finance. The technical motivation: learn real agentic AI engineering, the kind where the AI takes actions in the world (not just generates text).