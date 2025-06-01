# Written Report
**Scraper:** `quotes_scroll_scraper.py`  
**Target site:** <https://quotes.toscrape.com/scroll>  
**Author:** *<Ashley Chan>* &nbsp;|&nbsp; *Date:* 1 Jun 2025

---

## 1  Why this site?

| Requirements           | How the site fulfils it |
|------------------------|-------------------------|
| Public & login-free    | Open demo built for scraping practice. |
| Tabular / list data    | Each quote lives in a `<div class="quote">` with predictable sub-tags. |
| Pagination / load-more | Uses **infinite scroll**: new quotes load only after a scroll event. |
| ≥ 100 rows             | 1 000 + unique quotes are available. |
| Demonstrate JS handling| Forces a real browser renderer (Selenium) to capture > 10 rows. |

---

## 2  Architecture & Design

| Layer | Implementation | Rationale |
|-------|----------------|-----------|
| **Browser / HTTP** | `selenium` + headless Chrome (dynamic mode) or plain `requests` (static fallback). | Shows both a fast path *and* a JS-rendered path. |
| **HTML parsing** | `BeautifulSoup` preferring **lxml** but falling back to the std-lib parser. | Keeps the script portable on hosts without a C compiler. |
| **Data model** | Simple `dict(text, author, tags)` objects deduped by *text*, then concatenated into a `pandas.DataFrame`. | Zero external state, deterministic deduplication. |
| **Output** | CSV or JSON chosen by filename; CSV is written UTF-8-BOM for Excel compatibility. |
---

### 3.1 JavaScript / Dynamic Loading  
* **Problem** – Quotes appear only after an AJAX call triggered by scrolling.  
* **Solution** – In dynamic mode the scraper:  
  1. Launches headless Chrome.  
  2. Waits for the first quote (`WebDriverWait`).  
  3. Scrolls to bottom → pauses (`scroll_pause`) until `body.scrollHeight` grows.  
  4. Re-parses DOM; loop stops when ≥ *min_quotes* rows or *max_scrolls* cap reached.

### 3.2 Anti-scraping Measures  
Although the demo site has no defences, the code is hardened for real-world targets:

| Concern | Mitigation already in code |
|---------|----------------------------|
| **Rate limiting** | Human-like delay (`scroll_pause` + random jitter) between scrolls. |
| **Runaway loops** | `max_scrolls` safety cap. |
| **Encoding errors** | `resp.encoding = "utf-8"` on static path; CSV written with BOM. |
| **Parser availability** | Graceful fallback to `html.parser` if *lxml* wheel missing. |
| **Verbose driver logs** | `Service(..., log_level=3)` keeps console clean. |

Proxies and CAPTCHA-solvers can be added by passing proxy flags into ChromeOptions or `requests`.

---

## 4  Results Snapshot

```text
$ python quotes_scroll_scraper.py --dynamic --rows 120 -o data/quotes.csv
Saved 120 rows → …/data/quotes.csv

Sample rows
 “The world as we have created it is a process of our thinking…”, Albert Einstein, [change, deep-thoughts, thinking, world]
 “It is our choices, Harry, that show what we truly are…”,        J.K. Rowling,  [abilities, choices]
 ...
