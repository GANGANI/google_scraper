# Google Search Scraper

This repository provides a Google Search scraper using Playwright and Stealth mode to bypass bot detection. The script fetches search result links and saves them in a structured JSON format.

## Features
- Uses Playwright with Stealth to avoid bot detection.
- Implements random User-Agent rotation for anonymity.
- Supports Google search queries with date range filtering.
- Can scrape multiple pages with delays to mimic human behavior.
- Saves output in JSON format for easy processing.

## Installation

Before running the script, install the required dependencies:

```bash
pip install playwright beautifulsoup4 playwright-stealth fake_useragent
playwright install
```

## Usage

### Running the Scraper from Command Line

You can run the scraper using the following command:

```bash
python scraper.py "search query" -p 2 -s 3 -o output.jsonl.gz --site bbc.com --start-date 2022-01-01 --end-date 2022-12-31
```

#### Command Line Arguments:
- `query` - The search query.
- `-p, --pages` - Number of pages to scrape (default: 1).
- `-s, --sleep` - Sleep time (default: 2 seconds).
- `-o, --output` - Output file path (default: `scraped_data/links.jsonl.gz`).
- `--site` - Restrict search to a specific site (optional).
- `--start-date` - Start date for filtering results (format: YYYY-MM-DD, optional).
- `--end-date` - End date for filtering results (format: YYYY-MM-DD, optional).

### Running the Scraper in a Python Script

You can also use the scraper within a Python script:

```python
from scraper import google_scrape, get_google_date_range_directive

query = "news"
extraParams = {
    "directives": "site:bbc.com",
    "search_query_params": get_google_date_range_directive("2022-01-01", "2022-12-31"),
    "sleep_sec": 3,
    "max_pages": 1
}

scraped_links = google_scrape(query, extraParams)
print(scraped_links)
```

## Output Format

The scraper returns a JSON object containing the search results:

```json
{
    "query": "news",
    "source": "Google",
    "extra_params": {
        "directives": "site:bbc.com",
        "search_query_params": "tbs=cdr%3A1%2Ccd_min%3A1%2F1%2F2022%2Ccd_max%3A12%2F31%2F2022",
        "sleep_sec": 3,
        "max_pages": 1
    },
    "links": [
        "https://www.bbc.com/news/article-1",
        "https://www.bbc.com/news/article-2"
    ],
    "gen_timestamp": "2024-03-09T12:34:56Z"
}
```

