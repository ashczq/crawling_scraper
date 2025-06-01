# QuoteScrollScraper – Take-Home Assessment

Scrape the “infinite-scroll” demo at **<https://quotes.toscrape.com/scroll>** and
export at least *N* quotes (default = 100) to CSV **or** JSON.

* **Key data fields** : `text`, `author`, `tags`
* **Pagination** : handled by scrolling a headless Chrome window until enough
  new `<div class="quote">` blocks load
* **Dynamic vs static** :
  * **static** mode (default) collects the first 10 quotes – no Selenium required
  * **dynamic** mode (`--dynamic`) launches headless Chrome via Selenium to gather
    as many quotes as requested

---

## 1  Repository contents

| File | Purpose |
|------|---------|
| `quotes_scroll_scraper.py` | All scraping logic (class + CLI) |
| `README.md` (this file) | How to install, run, and troubleshoot |
| _optional output_ | `quotes.csv` or `quotes.json` produced by running the script |

---

## 2  Quick-start

```bash
# create & activate a clean virtual-env using python 3.11.0
python -m venv venv
# Windows:  venv\Scripts\activate
# macOS/Linux:  source venv/bin/activate

# 2. Install core + dynamic dependencies
pip install --upgrade pip
pip install -r requirements.txt 
