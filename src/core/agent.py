"""The FinScout research agent.

Given a ticker, orchestrates browser visits across multiple sources,
then synthesizes a structured research brief using Claude.

This is a 'tool-using agent' in the simple sense: the agent doesn't
decide what to visit dynamically (yet). Instead, it follows a
hardcoded sequence of high-value sources, then synthesizes the
extracted content. Future versions can add dynamic source selection.
"""
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from core.page_extractor import PageExtractor, PageContent
from core.llm import structured_call
from core.models import ResearchBrief


_ENV_PATH = Path(__file__).parent.parent.parent / ".env"
load_dotenv(_ENV_PATH)


# ──────────────── Source definitions ────────────────

# Each source is a function from ticker → URL. Keeps the URL construction
# explicit and easy to extend.

def yahoo_quote_url(ticker: str) -> str:
    return f"https://finance.yahoo.com/quote/{ticker}"


def google_news_url(ticker: str) -> str:
    # Search for the ticker AND the word 'stock' to filter out unrelated noise
    query = f"{ticker} stock"
    return f"https://news.google.com/search?q={query.replace(' ', '+')}"


def yahoo_news_url(ticker: str) -> str:
    return f"https://finance.yahoo.com/quote/{ticker}/news"


# The ordered list of sources our agent visits.
# Tuple format: (source_name_for_logs, url_builder_function)
DEFAULT_SOURCES = [
    ("Yahoo Finance quote page", yahoo_quote_url),
    ("Yahoo Finance news tab", yahoo_news_url),
    ("Google News", google_news_url),
]


# ──────────────── The agent ────────────────

_SYSTEM_PROMPT = """You are a careful equity research analyst.

Your job: read the raw content from multiple web sources about a stock, then produce a structured research brief.

CRITICAL RULES:
1. NEVER invent numbers. If a price, market cap, or P/E isn't shown in the sources, return None for that field.
2. NEVER invent news. If the sources don't contain enough headlines, return fewer items.
3. NEVER invent quotes or claim a specific analyst said something unless their name appears in the source.
4. Be HONEST in confidence_note about what you could and couldn't verify.
5. Bull and bear cases must be grounded in evidence visible in the sources. If sources only show price action and headlines, the cases should reflect that — don't pretend to know things like "growing revenue in segment X" unless that's actually stated.

The sources you're given are raw extracted text from real web pages. They will contain noise: navigation menus, ads, "sign in" prompts, sidebar widgets for other stocks. Filter that out mentally and focus on the substance about the requested ticker."""


def research(ticker: str, sources=None) -> ResearchBrief:
    """Run the full research pipeline for a ticker and return a structured brief."""
    ticker = ticker.upper().strip()
    if not ticker:
        raise ValueError("Ticker cannot be empty.")
    
    sources = sources or DEFAULT_SOURCES
    
    print(f"\n🔍 Researching {ticker}...\n")
    
    # Step 1: Browse all sources, collect content
    extracted: list[PageContent] = []
    with PageExtractor() as extractor:
        for source_name, url_builder in sources:
            url = url_builder(ticker)
            print(f"  📄 Visiting {source_name}: {url}")
            try:
                content = extractor.extract(url)
                print(f"     ✓ Got {content.text_length} chars")
                extracted.append(content)
            except Exception as e:
                print(f"     ⚠️  Failed: {e}")
                # Continue — we'd rather have a partial brief than no brief
    
    if not extracted:
        raise RuntimeError(f"Could not extract content from any source for {ticker}.")
    
    print(f"\n🧠 Synthesizing brief from {len(extracted)} source(s)...\n")
    
    # Step 2: Build the analysis prompt
    prompt = _build_synthesis_prompt(ticker, extracted)
    
    # Step 3: Get structured output from Claude
    brief = structured_call(
        prompt=prompt,
        response_model=ResearchBrief,
        system=_SYSTEM_PROMPT,
        max_tokens=6000,
    )
    
    # Step 4: Ensure sources_visited reflects reality, not what Claude claims
    brief.sources_visited = [c.url for c in extracted]
    
    return brief


def _build_synthesis_prompt(ticker: str, extracted: list[PageContent]) -> str:
    """Assemble the synthesis prompt with all extracted content."""
    
    # We label each source clearly so Claude knows what came from where.
    # Plain-text framing (not JSON) avoids context contamination — the
    # same lesson learned in resume-tailor.
    
    parts = [
        f"You are researching stock ticker: {ticker}",
        "",
        "Below are extracted text dumps from web pages. Each is REFERENCE MATERIAL — "
        "use it to inform your research brief, but do NOT echo it back. Your output "
        "must be a structured ResearchBrief.",
        "",
    ]
    
    for i, content in enumerate(extracted, 1):
        parts.append(f"═══ SOURCE {i}: {content.url} ═══")
        parts.append(f"PAGE TITLE: {content.title}")
        parts.append("")
        # Cap each source at ~6000 chars to keep prompt size manageable
        text = content.text[:6000]
        if len(content.text) > 6000:
            text += "\n... [truncated, page continues]"
        parts.append(text)
        parts.append("")
    
    parts.append("═══ YOUR TASK ═══")
    parts.append(
        f"Produce a structured ResearchBrief for {ticker}. "
        "Focus on substance, not noise. "
        "Be honest in confidence_note about what was and wasn't extractable from these sources."
    )
    
    return "\n".join(parts)