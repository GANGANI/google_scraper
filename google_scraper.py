import os
import gzip
import json
import time
import logging
import random
import argparse
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
from playwright_stealth.stealth import stealth_sync
from fake_useragent import UserAgent

ua = UserAgent()

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.DEBUG)

def fetch_links_using_playwright(url, sleep_range=(2, 5), max_scrolls=3):
    """Fetches search result links from Google using Playwright with stealth and random delays."""
    links = []
    user_agent = ua.random
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Change to False to debug in browser
        context = browser.new_context(viewport={'width': 1280, 'height': 800},  
                                      user_agent=user_agent,
                                      accept_downloads=True)
        context.set_extra_http_headers({
            "Referer": "https://www.google.com/",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
        })
        page = context.new_page()

        stealth_sync(page)  # Apply stealth mode to bypass bot detection

        try:
            logging.info(f"Opening URL: {url}")
            page.goto(url, timeout=90000)  # Increased timeout to 90 seconds
            page.wait_for_load_state("networkidle")  # Wait until no network activity

            # Scroll multiple times to ensure all results load
            for _ in range(max_scrolls):
                page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
                time.sleep(random.uniform(*sleep_range))  # Random delay between scrolls

            # Wait for search result links to appear using a broader selector
            page.wait_for_selector('div.tF2Cxc a', timeout=90000)  # Wait for result container with links

            # Extract links from search results
            search_results = page.query_selector_all('div.tF2Cxc a')
            links = [result.get_attribute("href") for result in search_results if result.get_attribute("href")]

            logging.info(f"Extracted {len(links)} links.")

        except Exception as e:
            logging.error(f"Error during Playwright fetching: {e}")

        finally:
            browser.close()

    return links

def create_directory(directory_path):
    """Creates directory if it does not exist."""
    os.makedirs(directory_path, exist_ok=True)

def get_google_date_range_directive(start_yyyy_mm_dd, end_yyyy_mm_dd):
    """Generates Google search date range directive."""
    try:
        start_date = datetime.strptime(start_yyyy_mm_dd, '%Y-%m-%d').strftime('%-m/%-d/%Y').replace('/', '%2F')
        end_date = datetime.strptime(end_yyyy_mm_dd, '%Y-%m-%d').strftime('%-m/%-d/%Y').replace('/', '%2F')
        return f'tbs=cdr%3A1%2Ccd_min%3A{start_date}%2Ccd_max%3A{end_date}'
    except Exception as e:
        logging.error(f"Error generating date range directive: {e}")
        return ''
    
def google_scrape(query, extraParams=None):
    """Scrapes Google search results and returns structured JSON output."""
    if extraParams is None:
        extraParams = {}

    base_url = extraParams.get("directives", "").replace("site:", "") if "directives" in extraParams else None
    date_range_directive = extraParams.get("search_query_params", "")
    sleep_sec = extraParams.get("sleep_sec", 2)
    max_pages = extraParams.get("max_pages", 1)  # Default to 1 page if not provided

    # Build the Google search URL dynamically
    google_search_url = f"https://www.google.com/search?q="
    if "directives" in extraParams and extraParams["directives"]:
        google_search_url += f"+{base_url}+{query}"
    else:
        google_search_url += f"{query}"
    if date_range_directive:
        google_search_url += f"&{date_range_directive}"

    logging.info(f"Fetching search results from: {google_search_url}")

    scraped_links = []
    
    # Loop through the specified number of pages
    for page_number in range(max_pages):
        page_url = google_search_url + f"&start={page_number * 10}"
        logging.info(f"Fetching page {page_number + 1}: {page_url}")

        links = fetch_links_using_playwright(page_url, sleep_range=(2, 5))
        
        if links:
            logging.info(f"Found {len(links)} links on page {page_number + 1} of Google search")
            scraped_links.extend(links)
        else:
            logging.warning(f"No links found on page {page_number + 1}.")

        time.sleep(sleep_sec)  # Apply delay between requests

    # Construct structured JSON response
    serp_result = {
        "query": query,
        "source": "Google",
        "extra_params": extraParams,
        "links": scraped_links,
        "gen_timestamp": datetime.now(timezone.utc).isoformat()
    }

    return serp_result

def main():
    """Main function to execute the scraping process via command-line."""
    parser = argparse.ArgumentParser(description="Generalized Google Web Scraper using Playwright.")
    parser.add_argument('query', type=str, help="Search query for scraping")
    parser.add_argument('-p', '--pages', type=int, default=1, help="Number of pages to scrape (default: 1)")
    parser.add_argument('-s', '--sleep', type=int, default=2, help="Time to sleep between requests (default: 2 seconds)")
    parser.add_argument('-o', '--output', type=str, default='scraped_data/links.jsonl.gz', help="Output file path")
    parser.add_argument('--site', type=str, default=None, help="Base site for site-specific scraping (optional)")
    parser.add_argument('--start-date', type=str, default='', help="Start date for Google search (format: YYYY-MM-DD)")
    parser.add_argument('--end-date', type=str, default='', help="End date for Google search (format: YYYY-MM-DD)")

    args = parser.parse_args()

    # Construct extraParams dictionary
    extraParams = {
        "directives": f"site:{args.site}" if args.site else "",
        "search_query_params": get_google_date_range_directive(args.start_date, args.end_date),
        "sleep_sec": args.sleep,
        "max_pages": args.pages
    }

    create_directory(os.path.dirname(args.output))

    # Call the function with dynamic parameters
    serp_result = google_scrape(args.query, extraParams)

    # Save the structured JSON response
    with gzip.open(args.output, 'wt', encoding='utf-8') as f:
        f.write(json.dumps(serp_result, indent=4))

    logging.info(f"Scraped data saved to {args.output}")

if __name__ == "__main__":
    main()
