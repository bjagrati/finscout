"""Smoke test: open a browser, visit Yahoo Finance, screenshot, extract price."""
import os
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

# Load .env
ENV_PATH = Path(__file__).parent.parent / ".env"
load_dotenv(ENV_PATH)

BROWSER_MODE = os.environ.get("BROWSER_MODE", "headed")
HEADLESS = BROWSER_MODE == "headless"

# Where to save screenshots
SCREENSHOTS_DIR = Path(__file__).parent.parent / "screenshots"
SCREENSHOTS_DIR.mkdir(exist_ok=True)


def main():
    ticker = "NVDA"
    url = f"https://finance.yahoo.com/quote/{ticker}"
    
    print(f"Browser mode: {BROWSER_MODE}")
    print(f"Visiting: {url}\n")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )
        page = context.new_page()
        
        print("Navigating...")
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        
        # Yahoo Finance sometimes shows a consent banner. Try to dismiss it.
        try:
            page.click("button:has-text('Accept all')", timeout=3000)
            print("Dismissed consent banner.")
        except Exception:
            pass
        
        # SPECIFIC selector: match BOTH the ticker symbol AND the field type
        # This avoids matching sidebar widgets for other stocks.
        selector = f"fin-streamer[data-symbol='{ticker}'][data-field='regularMarketPrice']"
        
        print("Looking for price...")
        page.wait_for_selector(selector, timeout=10000)
        price_element = page.query_selector(selector)
        price = price_element.inner_text() if price_element else "??"
        
        print(f"\n💰 {ticker} current price: ${price}")
        
        # Take a screenshot
        screenshot_path = SCREENSHOTS_DIR / f"{ticker}_yahoo.png"
        page.screenshot(path=str(screenshot_path), full_page=False)
        print(f"📸 Screenshot saved: {screenshot_path}")
        
        print(f"📄 Page title: {page.title()}")
        
        if not HEADLESS:
            print("\nKeeping browser open for 3 seconds so you can see it...")
            page.wait_for_timeout(3000)
        
        browser.close()
        print("\n✓ Done!")


if __name__ == "__main__":
    main()