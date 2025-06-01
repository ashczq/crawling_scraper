from __future__ import annotations

import argparse
import random
import time
from pathlib import Path
from typing import Dict, List

import pandas as pd
import requests
from bs4 import BeautifulSoup, FeatureNotFound
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager


#helper function
def _make_soup(html: str) -> BeautifulSoup:
    """Return a BeautifulSoup object, preferring ``lxml`` but falling back
    to Python’s built-in ``html.parser`` if *lxml* is not installed.

    Args:
        html: Raw HTML text.

    Returns:
        A BeautifulSoup DOM tree.
    """
    try:
        return BeautifulSoup(html, "lxml")
    except (FeatureNotFound, ImportError):
        return BeautifulSoup(html, "html.parser")


class QuoteScrollScraper:
    """Scraper for the quotes.toscrape.com *infinite-scroll* demo page.

    Parameters
    ----------
    url:
        Page URL.  Defaults to the standard demo.
    dynamic:
        If *True*, use Selenium headless Chrome to render JavaScript and
        follow the scrolling; if *False*, scrape only the first 10 static
        quotes delivered in the initial HTML.
    min_quotes:
        Minimum number of quotes to collect before stopping.  Ignored in
        static mode if set > 10 (a RuntimeError is raised instead).
    headless:
        Run Chrome in headless mode.  Has no effect in static mode.
    scroll_pause:
        Seconds to wait after each ``window.scrollTo`` call so the backend
        can deliver the next batch of quotes.
    max_scrolls:
        Safety cap on the number of scroll attempts; prevents endless loops
        on network errors or unexpected markup changes.
    """

    DEFAULT_URL = "https://quotes.toscrape.com/scroll"

    def __init__(
        self,
        url: str | None = None,
        *,
        dynamic: bool = False,
        min_quotes: int = 100,
        headless: bool = True,
        scroll_pause: float = 0.8,
        max_scrolls: int = 120,
    ) -> None:
        self.url = url or self.DEFAULT_URL
        self.dynamic = dynamic
        self.min_quotes = min_quotes
        self.headless = headless
        self.scroll_pause = scroll_pause
        self.max_scrolls = max_scrolls

    def scrape(self) -> pd.DataFrame:
        """Return a ``pandas.DataFrame`` containing the requested number of
        quotes.

        Returns
        -------
        pandas.DataFrame
            Columns: *text*, *author*, *tags*.
        """
        quotes = (
            self._scrape_dynamic()
            if self.dynamic
            else self._scrape_static(limit=self.min_quotes)
        )
        return pd.DataFrame(quotes)

    def save(self, df: pd.DataFrame, outfile: Path | str) -> None:
        """Write the DataFrame to disk as UTF-8 CSV (with BOM) or JSON.

        Args:
            df: The data returned by :py:meth:`scrape`.
            outfile: Path whose extension determines the format.
                     ``.csv`` → CSV;  ``.json`` → JSON.
        """
        path = Path(outfile).expanduser()
        if path.suffix.lower() == ".json":
            df.to_json(path, orient="records", indent=2, force_ascii=False)
        else:
            df.to_csv(path, index=False, encoding="utf-8-sig") 
        print(f"Saved {len(df):,} rows → {path.resolve()}")

    def _scrape_static(self, limit: int) -> List[dict]:
        """Grab the first *limit* quotes from the server-rendered HTML.

        The site only ships 10 quotes statically; requesting more forces
        callers into dynamic mode.

        Raises
        ------
        RuntimeError
            If *limit* is > 10.
        """
        if limit > 10:
            raise RuntimeError(
                "Static mode can only capture the first 10 quotes. "
                "Run with --dynamic for a full scrape."
            )

        resp = requests.get(self.url, timeout=10)
        resp.encoding = "utf-8"  
        soup = _make_soup(resp.text)

        return [
            self._parse_quote_div(div) for div in soup.select("div.quote")
        ][:limit]

    def _scrape_dynamic(self) -> List[dict]:
        """Open the page in headless Chrome and keep scrolling until at
        least *min_quotes* unique quotes are gathered or *max_scrolls*
        attempts have been made."""
        opts = Options()
        if self.headless:
            opts.add_argument("--headless=new")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--window-size=1920,1080")

        service = Service(ChromeDriverManager().install(), log_level=3)
        driver = webdriver.Chrome(service=service, options=opts)

        quotes: Dict[str, dict] = {}
        try:
            driver.get(self.url)

            WebDriverWait(driver, 6).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.quote"))
            )

            last_height = driver.execute_script("return document.body.scrollHeight")

            for _ in range(self.max_scrolls):
                soup = _make_soup(driver.page_source)
                for div in soup.select("div.quote"):
                    q = self._parse_quote_div(div)
                    quotes[q["text"]] = q  

                if len(quotes) >= self.min_quotes:
                    break

                driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(self.scroll_pause + random.uniform(0.1, 0.3))

                WebDriverWait(driver, 2).until(
                    lambda d: d.execute_script("return document.body.scrollHeight")
                    > last_height
                )
                last_height = driver.execute_script("return document.body.scrollHeight")

        finally:
            driver.quit()

        return list(quotes.values())

    @staticmethod
    def _parse_quote_div(div) -> dict:
        """Convert one ``<div class="quote">`` block to a plain dict."""
        text = div.select_one("span.text").get_text(strip=True)
        author = div.select_one("small.author").get_text(strip=True)
        tags = [a.get_text(strip=True) for a in div.select("div.tags a.tag")]
        return {"text": text, "author": author, "tags": tags}


def _cli() -> None:
    """Parse command-line args and run the scraper."""
    p = argparse.ArgumentParser(
        description="Scrape the infinite-scroll quotes demo into CSV/JSON."
    )
    p.add_argument("-o", "--out", type=Path, default="quotes.csv", help="Output file")
    p.add_argument(
        "--dynamic",
        action="store_true",
        help="Render JavaScript with Selenium (recommended).",
    )
    p.add_argument(
        "--rows",
        type=int,
        default=100,
        help="Minimum number of quotes to collect (default 100).",
    )
    args = p.parse_args()

    scraper = QuoteScrollScraper(dynamic=args.dynamic, min_quotes=args.rows)
    df = scraper.scrape()
    scraper.save(df, args.out)

    with pd.option_context("display.max_colwidth", 120):
        print("\nSample rows")
        print(df.head().to_string(index=False))


if __name__ == "__main__":
    _cli()
