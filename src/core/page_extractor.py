"""Generic page content extraction.

Given a URL, returns the visible text content + a screenshot.
Used by the agent to read any web page consistently.
"""
import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, Page, Browser


# Load .env
_ENV_PATH = Path(__file__).parent.parent.parent / ".env"
load_dotenv(_ENV_PATH)

_HEADLESS = os.environ.get("BROWSER_MODE", "headed") == "headless"
_SCREENSHOTS_DIR = Path(__file__).parent.parent.parent / "screenshots"
_SCREENSHOTS_DIR.mkdir(exist_ok=True)

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


@dataclass
class PageContent:
    """The extracted content of a single page visit."""
    url: str
    title: str
    text: str                 # main visible text content, cleaned
    screenshot_path: str      # relative path to screenshot file
    text_length: int          # for quick "is this empty?" checks
    
    def short_preview(self, n: int = 200) -> str:
        """A brief preview of the text, useful for logging."""
        return self.text[:n] + ("..." if len(self.text) > n else "")


class PageExtractor:
    """A browser session that can extract content from multiple pages.
    
    Designed to be used as a context manager:
        with PageExtractor() as extractor:
            content = extractor.extract("https://...")
    """
    
    def __init__(self, headless: bool = None):
        self.headless = _HEADLESS if headless is None else headless
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context = None
    
    def __enter__(self):
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=self.headless)
        self._context = self._browser.new_context(
            user_agent=_USER_AGENT,
            viewport={"width": 1280, "height": 800},
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()
    
    def extract(self, url: str, wait_for: Optional[str] = None, dismiss_banners: bool = True) -> PageContent:
        """Visit a URL, extract its text content, and screenshot it.
        
        Args:
            url: The URL to visit.
            wait_for: Optional CSS selector to wait for (useful for slow JS pages).
            dismiss_banners: Try to click common cookie/consent banners.
        
        Returns:
            PageContent with text, screenshot path, and metadata.
        """
        page = self._context.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            if dismiss_banners:
                self._try_dismiss_banners(page)
            
            if wait_for:
                try:
                    page.wait_for_selector(wait_for, timeout=10000)
                except Exception:
                    pass  # Continue even if specific selector doesn't appear
            else:
                # Default: give JS a moment to populate the page
                page.wait_for_timeout(2000)
            
            title = page.title()
            text = self._extract_visible_text(page)
            screenshot_path = self._save_screenshot(page, url)
            
            return PageContent(
                url=url,
                title=title,
                text=text,
                screenshot_path=str(screenshot_path),
                text_length=len(text),
            )
        finally:
            page.close()
    
    def _try_dismiss_banners(self, page: Page):
        """Try to dismiss common cookie/consent banners. Best-effort."""
        common_buttons = [
            "button:has-text('Accept all')",
            "button:has-text('Accept All')",
            "button:has-text('I agree')",
            "button:has-text('Got it')",
            "button:has-text('Accept')",
            "button[aria-label='Close']",
            "[id*='cookie'] button",
        ]
        for selector in common_buttons:
            try:
                page.click(selector, timeout=1000)
                return  # Successfully clicked something, stop trying
            except Exception:
                continue
    
    def _extract_visible_text(self, page: Page) -> str:
        """Extract the visible body text of the page, stripping noise.
        
        Strategy: get the body's inner_text (which is what a user would see),
        then collapse whitespace.
        """
        # inner_text returns ONLY visible text, respecting CSS display rules.
        # This is the magic — Playwright already filters out hidden/styled-out content.
        raw = page.inner_text("body")
        return self._clean_text(raw)
    
    @staticmethod
    def _clean_text(text: str) -> str:
        """Collapse excessive whitespace and clean up."""
        # Collapse multiple newlines into double-newline (paragraph breaks)
        text = re.sub(r"\n{3,}", "\n\n", text)
        # Collapse multiple spaces/tabs
        text = re.sub(r"[ \t]+", " ", text)
        # Strip leading/trailing whitespace on each line
        text = "\n".join(line.strip() for line in text.split("\n"))
        return text.strip()
    
    def _save_screenshot(self, page: Page, url: str) -> Path:
        """Save a screenshot with a unique filename based on the URL + a UUID."""
        # Build a safe filename slug from the URL
        slug = re.sub(r"[^a-z0-9]+", "-", url.lower())[:60].strip("-")
        unique = uuid.uuid4().hex[:6]
        filename = f"{slug}_{unique}.png"
        path = _SCREENSHOTS_DIR / filename
        page.screenshot(path=str(path), full_page=False)
        return path