"""Pydantic models for FinScout research outputs."""
from typing import Literal, Optional
from pydantic import BaseModel, Field


# ──────────────── News items ────────────────

class NewsItem(BaseModel):
    """A single recent news headline about the company."""
    
    headline: str = Field(..., description="The article headline, copied verbatim from the source.")
    
    source: str = Field(
        ...,
        description="Publication name (e.g., 'Reuters', 'CNBC', 'Bloomberg'). If unknown, use 'Unknown'.",
    )
    
    age: str = Field(
        ...,
        description="How recent, as shown on the page (e.g., '2 hours ago', '3 days ago', 'June 25').",
    )
    
    sentiment: Literal["positive", "negative", "neutral"] = Field(
        ...,
        description=(
            "Sentiment of the headline toward the stock. 'Positive' = bullish/good news. "
            "'Negative' = bearish/bad news. 'Neutral' = informational or mixed."
        ),
    )
    
    summary: str = Field(
        ...,
        description="One-sentence summary of what this headline means for the stock.",
    )


# ──────────────── The full brief ────────────────

class ResearchBrief(BaseModel):
    """A complete equity research brief synthesizing multiple web sources."""
    
    # Identity
    ticker: str = Field(..., description="The stock ticker symbol (e.g., 'NVDA').")
    
    company_name: str = Field(
        ...,
        description="The full company name (e.g., 'NVIDIA Corporation').",
    )
    
    # Numbers — all optional because not every source has them
    current_price: Optional[float] = Field(
        None,
        description="Current share price in USD if found, else None. Do not invent.",
    )
    
    market_cap: Optional[str] = Field(
        None,
        description=(
            "Market capitalization as shown on the page, including units (e.g., '$3.5T', '$847B'). "
            "Copy exactly as shown. None if not found."
        ),
    )
    
    pe_ratio: Optional[float] = Field(
        None,
        description="Price-to-Earnings ratio if shown. None if not found or 'N/A'.",
    )
    
    # The narrative
    one_line_summary: str = Field(
        ...,
        description=(
            "A single sentence capturing the current state of the stock and the dominant narrative. "
            "Example: 'AI infrastructure leader showing first signs of cooling after a record-breaking run.'"
        ),
    )
    
    recent_news: list[NewsItem] = Field(
        ...,
        description=(
            "The 3-6 most relevant recent headlines. Prioritize by recency AND relevance. "
            "Don't include unrelated sponsored content or irrelevant trending news."
        ),
    )
    
    bull_case: list[str] = Field(
        ...,
        description=(
            "3-5 specific reasons to be optimistic about this stock, based ONLY on evidence from the visited sources. "
            "Each bullet should be 1-2 sentences and reference specific facts when possible. "
            "If the sources don't support a bull case, return fewer bullets — don't invent."
        ),
    )
    
    bear_case: list[str] = Field(
        ...,
        description=(
            "3-5 specific reasons to be concerned about this stock, based ONLY on evidence from the visited sources. "
            "Each bullet should be 1-2 sentences. "
            "Look for concerns mentioned in news headlines, analyst views, or competitive dynamics."
        ),
    )
    
    key_risks: list[str] = Field(
        ...,
        description=(
            "2-4 concrete risks to monitor (e.g., regulatory, competitive, macroeconomic). "
            "Different from bear_case: these are forward-looking watch items, not current negatives."
        ),
    )
    
    # Provenance
    sources_visited: list[str] = Field(
        ...,
        description="URLs of all pages visited to produce this brief.",
    )
    
    confidence_note: str = Field(
        ...,
        description=(
            "An honest 2-3 sentence note about the brief's limitations. "
            "Mention what we COULDN'T access (paywalled sources, missing earnings data, etc.). "
            "Mention any data points that were inferred rather than directly read. "
            "This builds trust by being upfront about what the agent does and doesn't know."
        ),
    )