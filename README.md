# FinScout

An AI agent that researches stocks by actually browsing the web.

Type a ticker. Watch a real browser visit Yahoo Finance, Google News, and other sources. ~60 seconds later you get a structured research brief — current price, recent news with sentiment tags, bull/bear cases grounded in extracted evidence, and an honest confidence note about what couldn't be verified.

Built with Anthropic Claude, Playwright, FastAPI, and Pydantic. Hand-rolled ReAct-style agent loop. No agent framework dependencies.

---

## What It Does

- **Autonomous browsing** — A visible Chromium browser navigates real financial sites, takes screenshots, extracts content
- **Live progress** — Server-Sent Events stream the agent's activity to the browser in real time
- **Structured synthesis** — Multi-source extracted text is fused into a Pydantic-validated research brief via Claude tool use
- **Honest by design** — Each brief includes a `confidence_note` field that explicitly states what the agent could and couldn't verify; refuses to invent numbers or quotes

### Why "honest by design" matters

Most LLM-powered research tools eagerly fabricate plausible-sounding numbers and quotes. FinScout's system prompt and schema were engineered to refuse this:

- Optional financial fields (`current_price`, `market_cap`, `pe_ratio`) — Claude returns `None` rather than invent
- The `confidence_note` field forces the model to articulate gaps ("article bodies were not visited, summaries are inferred from headlines only")
- Ground-truth fields like `sources_visited` are populated by the code, not Claude — the model cannot claim to have visited URLs it didn't

---

## Architecture

```
[Browser UI]  ─►  [FastAPI + SSE]  ─►  [Agent loop]  ─►  Playwright (real browser)
                                            │                    │
                                            │                    ▼
                                            │            visits Yahoo, Google News, etc.
                                            │                    │
                                            ▼                    ▼
                                       Claude API  ◄────  extracted text + screenshots
                                            │
                                            ▼
                                       ResearchBrief (Pydantic)
```

### Components

| Path | Role |
|------|------|
| `src/core/page_extractor.py` | Reusable Playwright session: visits any URL, returns cleaned text + screenshot |
| `src/core/models.py` | Pydantic schemas (`NewsItem`, `ResearchBrief`) |
| `src/core/llm.py` | Reusable `structured_call()` — sends any Pydantic model to Claude via tool use |
| `src/core/agent.py` | The research agent: orchestrates browsing + synthesis. Yields progress events. |
| `src/interfaces/web/api.py` | FastAPI app with streaming research endpoint + UI |
| `src/interfaces/web/static/` | Dark Bloomberg-terminal-styled frontend (HTML/CSS/vanilla JS + SSE) |

---

## Tech Stack

- **Python 3.12**
- **Playwright** — headless or headed Chromium for browsing
- **Anthropic Claude API** (`claude-sonnet-4-6`) — synthesis
- **Pydantic v2** — structured output schemas
- **FastAPI + Uvicorn** — backend with Server-Sent Events
- **Plain HTML/CSS/vanilla JS** — no frontend framework

---

## Setup

### Prerequisites

- Python 3.10+ (3.12 recommended)
- An Anthropic API key (`sk-ant-...`) — small free credit or ~$5 prepaid more than covers this project

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

`BROWSER_MODE=headed` makes the browser window visible (recommended for demos). Use `headless` for invisible/faster runs.

### Run

```bash
uvicorn src.interfaces.web.api:app --reload --port 8002
```

Open **http://localhost:8002/ui/** — type a ticker (NVDA, AAPL, TSLA) and click Research.

---

## How the Agent Works

The agent loop is intentionally simple and hand-rolled — no LangChain, no agent framework:

1. **Browse**: For each source in the configured list, open it in a real browser, wait for content to load, extract visible text, screenshot the page.
2. **Bundle**: Combine all extracted text into a single labeled prompt, with clear `═══ SOURCE N ═══` delimiters and per-source URL labels (plain text — JSON inputs caused "context contamination" in smaller models during exploration).
3. **Synthesize**: Send the bundle to Claude with a strict anti-hallucination system prompt and a Pydantic-defined `ResearchBrief` schema. Claude is forced to call our tool, guaranteeing structured output.
4. **Verify**: After synthesis, overwrite `sources_visited` with the URLs actually visited (ground truth from the code, not the model).

For v1, the source list is hardcoded. Future versions can let the LLM dynamically choose follow-up sources based on what it learns from each visit.

---

## What I Learned

- **Hand-rolled ReAct loops** are surprisingly small (~50 lines) and *much* easier to debug than framework-wrapped equivalents
- **Server-Sent Events** are the right primitive for agent progress streaming — lighter than WebSockets, built into every browser
- **Hallucination resistance is schema design** — Optional fields, `confidence_note`, ground-truth-overwrite patterns
- **Selectors break constantly in real browser automation** — the first NVDA price selector matched 33 elements; the fix was constraining by `data-symbol`
- **Plain-text source delimiters beat JSON** as LLM input when the model needs to differentiate "context" from "output target"

---

## Roadmap

- [ ] Dynamic source selection — let the LLM decide what to visit next based on what it learned
- [ ] Article body fetching — currently we read headline lists; full articles would improve quality
- [ ] Earnings call transcript ingestion
- [ ] Comparison briefs — research multiple tickers and compare them side-by-side
- [ ] Public deployment with rate limiting

---

## License

MIT

---

## Author

Built by Jagrati Bhardwaj. The motivation: I wanted to actually use this for my own stock research, and I wanted to learn real agentic AI engineering — the kind where the AI takes actions in the world, not just generates text.