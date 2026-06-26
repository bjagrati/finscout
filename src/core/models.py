"""Pydantic models for FinScout — humanized stock explainer."""
from typing import Literal, Optional
from pydantic import BaseModel, Field


# ──────────────── News (humanized) ────────────────

class NewsItem(BaseModel):
    """A single recent news headline, framed for non-finance readers."""
    
    headline: str = Field(..., description="The article headline, copied verbatim.")
    
    source: str = Field(..., description="Publication name (Reuters, CNBC, etc.). Use 'Unknown' if not stated.")
    
    age: str = Field(..., description="How recent (e.g., '2 hours ago', 'Yesterday').")
    
    mood: Literal["good_news", "bad_news", "mixed", "neutral_info"] = Field(
        ...,
        description=(
            "The mood of this news for the stock. "
            "'good_news' = clearly positive, 'bad_news' = clearly negative, "
            "'mixed' = both positive and negative, 'neutral_info' = informational with no clear direction."
        ),
    )
    
    plain_summary: str = Field(
        ...,
        description=(
            "A 1-sentence summary in plain English that a high-schooler would understand. "
            "No finance jargon. If the headline mentions specific terms (P/E, EBITDA, EPS), "
            "either explain them or rephrase without them."
        ),
    )


# ──────────────── The humanized brief ────────────────

class StockExplainer(BaseModel):
    """A plain-English explanation of what's going on with a stock, designed for non-finance readers."""
    
    # Identity
    ticker: str = Field(..., description="Stock ticker (e.g., 'NVDA').")
    
    company_name: str = Field(..., description="Full company name (e.g., 'NVIDIA Corporation').")
    
    what_they_do: str = Field(
        ...,
        description=(
            "A single sentence explaining what the company actually does, "
            "in language a high-schooler would understand. "
            "Example: 'NVIDIA makes the special computer chips that power most modern AI systems.' "
            "AVOID jargon. AVOID 'industry leader in semiconductor solutions for...' type phrasing."
        ),
    )
    
    # The headline verdict — the most important field
    overall_mood: Literal["very_positive", "positive", "mixed", "negative", "very_negative"] = Field(
        ...,
        description=(
            "The dominant story for this stock right now. "
            "'very_positive' = strong tailwinds, broadly bullish news. "
            "'positive' = generally good but some concerns. "
            "'mixed' = real positives and real negatives, no clear direction. "
            "'negative' = mostly concerning news or weak performance. "
            "'very_negative' = serious problems or crashing stock. "
            "Be HONEST — don't default to 'mixed' to avoid taking a position."
        ),
    )
    
    mood_one_liner: str = Field(
        ...,
        description=(
            "ONE sentence (max 15 words) capturing the current state in plain language. "
            "Examples: 'Strong company, but the stock has cooled off this week.' "
            "'Solid earnings have investors excited about the next year.' "
            "'Real concerns about competition are weighing on the price.'"
        ),
    )
    
    # The story
    the_story: str = Field(
        ...,
        description=(
            "A 3-5 sentence plain-English story explaining what's happening with this stock RIGHT NOW. "
            "Lead with the most important thing. Connect cause to effect. "
            "Mention numbers ONLY when they have clear meaning ('they made $30 billion in profit last quarter' "
            "is fine; 'TTM revenue of $253.49B with 62.97% margins' is NOT). "
            "Tone: thoughtful friend explaining over coffee, not Wall Street analyst."
        ),
    )
    
    # Current snapshot — simplified
    current_price: Optional[float] = Field(
        None,
        description="Current stock price in USD. None if not extracted.",
    )
    
    price_context: str = Field(
        ...,
        description=(
            "1 sentence putting the current price in context. "
            "Examples: 'Down 3% today, but up 45% this year.' "
            "'Near its all-time high after a strong week.' "
            "'Has fallen sharply from $250 earlier this year.' "
            "Use only price/performance facts visible in the sources."
        ),
    )
    
    company_size_context: str = Field(
        ...,
        description=(
            "1 sentence putting the company's size in relatable terms. "
            "Examples: 'NVIDIA is now worth more than the entire economy of France.' "
            "'A mid-sized company, smaller than McDonald's.' "
            "Use the market cap from sources but DO NOT use raw '$4.7T' phrasing — translate it."
        ),
    )
    
    # Good and bad signals — humanized bull/bear
    good_signs: list[str] = Field(
        ...,
        description=(
            "2-4 things going well for this stock, in plain English. "
            "Each one sentence. No jargon. "
            "Good example: 'The company keeps making more money than analysts expected.' "
            "BAD example: 'Strong Q1 EPS beat with positive guidance for FY27.'"
        ),
    )
    
    concerns: list[str] = Field(
        ...,
        description=(
            "2-4 things to watch out for, in plain English. "
            "Each one sentence. Frame as 'why someone might be worried,' not as 'sell signals.' "
            "Good example: 'Some big investors are quietly selling, which suggests they expect a slowdown.' "
            "BAD example: 'Hedge fund positioning shows net short flow with declining institutional ownership.'"
        ),
    )
    
    # The takeaway
    honest_takeaway: str = Field(
        ...,
        description=(
            "2-3 sentences. The 'if I were explaining this to a friend' bottom line. "
            "Honest about uncertainty. Should help a normal person think about the stock without telling them what to do. "
            "Good example: 'NVIDIA is a great company having a normal stock wobble. If you already own it, no need to panic. "
            "If you're thinking about buying, you might want to wait a few weeks and see if the price stabilizes.' "
            "AVOID phrasings that constitute investment advice ('buy', 'sell', 'strong buy'). "
            "DO use human framings ('worth keeping an eye on', 'not a panic moment', 'real questions to ask before buying')."
        ),
    )
    
    recent_news: list[NewsItem] = Field(
        ...,
        description="3-5 most relevant recent headlines, ranked by importance and recency.",
    )
    
    # Provenance & honesty
    sources_visited: list[str] = Field(
        ...,
        description="URLs visited to build this explainer.",
    )
    
    what_we_could_not_check: str = Field(
        ...,
        description=(
            "A plain-English note about limitations. "
            "Example: 'This is based on Yahoo Finance and Google News headlines from the last few hours. "
            "We didn't read the full articles, and we can't see things like analyst reports or detailed earnings data.' "
            "Make it feel honest, not technical."
        ),
    )