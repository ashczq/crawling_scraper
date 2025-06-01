from pathlib import Path

import pandas as pd
import pytest

from src.quotes_scroll_scraper import QuoteScrollScraper


def test_static_mode_tmp_path(tmp_path: Path) -> None:
    """Static path should always produce exactly 10 rows from the homepage."""
    scraper = QuoteScrollScraper(dynamic=False, min_quotes=10)
    df = scraper.scrape()

    assert isinstance(df, pd.DataFrame)
    assert df.shape[0] == 10
    assert set(df.columns) == {"text", "author", "tags"}

    out = tmp_path / "first10.csv"
    scraper.save(df, out)

    df2 = pd.read_csv(out, encoding="utf-8-sig")

    # same number of rows & cols
    assert df2.shape == df.shape
    assert df2["text"].equals(df["text"])
    assert df2["author"].equals(df["author"])

@pytest.mark.skipif(
    pytest.importorskip("selenium", reason="Selenium not installed") is None,
    reason="Selenium not available",
)
def test_dynamic_mode() -> None:
    """Dynamic path should gather at least 30 unique quotes."""
    scraper = QuoteScrollScraper(dynamic=True, min_quotes=30, headless=True)
    df = scraper.scrape()

    assert df.shape[0] >= 30
    assert df["text"].is_unique
