import os
import gzip
import json
import time
import logging
import random
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
from playwright_stealth.stealth import stealth_sync
from fake_useragent import UserAgent

ua = UserAgent()


# List of user agents to avoid detection
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36",
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
]

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.DEBUG)

def extract_domain(site_url):
    """Extracts domain name from a given URL."""
    parsed_url = urlparse(site_url)
    domain = parsed_url.netloc or parsed_url.path
    return domain.replace("www.", "").rstrip("/")

def extract_links_from_wikipedia(media_website, wikipedia_links):
    """Extracts relevant links from Wikipedia articles."""
    site_domain = extract_domain(media_website)
    extracted_site_links = []
    try:
        for wikipedia_link in wikipedia_links:
            logging.info(f"Fetching Wikipedia URL: {wikipedia_link}")
            response = requests.get(wikipedia_link, headers={"User-Agent": "Mozilla/5.0"})
            if response.status_code != 200:
                logging.error(f"Failed to fetch {wikipedia_link}, status code: {response.status_code}")
                continue
            
            soup = BeautifulSoup(response.text, 'html.parser')
            extracted_links = set()
            for anchor in soup.find_all("a", href=True):
                link = anchor["href"]
                if link.startswith("/"):
                    link = wikipedia_link.rstrip("/") + link  # Convert relative links to absolute
                article_domain = extract_domain(link)
                if link and site_domain in article_domain:
                    logging.info(f"Extracted URL: {link} from: {wikipedia_link}")
                    extracted_links.add(link)
            extracted_site_links.append({wikipedia_link: list(extracted_links)})
        return extracted_site_links
    except Exception as e:
        logging.error(f"Error extracting links from {media_website}: {e}")

def fetch_google_results(site, max_pages, start_date, end_date):
    """Fetches Wikipedia links from Google search results."""
    wikipedia_links = []
    domain = extract_domain(site)
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

        date_range_directive = get_google_date_range_directive(start_date, end_date)

        try:
            for page_number in range(max_pages):
                url = f"https://www.google.com/search?q=site:wikipedia.org+{domain}&{date_range_directive}&start={page_number * 10}"
                logging.info(f"Fetching Google Search URL: {url}")

                page.goto(url, timeout=60000)

                # Scroll down to load results
                page.evaluate("window.scrollBy(0, scrollBy(0, window.innerHeight))")
                time.sleep(random.uniform(2, 5))

                # Wait for Wikipedia links instead of h3
                page.wait_for_selector('a[href^="https://en.wikipedia.org/wiki/"]', timeout=45000)

                search_results = page.query_selector_all('a[href^="https://en.wikipedia.org/wiki/"]')

                for result in search_results:
                    link = result.get_attribute("href")
                    if link and "wikipedia.org" in link:
                        wikipedia_links.append(link)
                        logging.info(f"Wikipedia link found: {link}")

        except Exception as e:
            logging.error(f"Error during Google search: {e}")
        finally:
            browser.close()
    
    return wikipedia_links

def create_directory(directory_path):
    logging.info(f"Create Directory: {directory_path}")
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

def main():
    """Main function to execute the scraping process."""
    with open("news.json", "r") as file:
        data = json.load(file)
    
    start_year, end_year = 2022, 2023
    overall_start_time = time.time()

    for state, media_types in data.items():
        for media_type, media_list in media_types.items():
            execution_times_file = f'{media_type}_execution_times.txt'
            create_directory(f'{media_type}/{state}')
            state_start_time = time.time()

            for year in range(start_year, end_year + 1):
                start_date, end_date = f'{year}-01-01', f'{year}-12-31'
                year_start_time = time.time()
                serp_data = []

                for media in media_list:
                    media_website = media.get("website")
                    if not media_website:
                        continue
                    logging.info(f"Processing {media_website} for {state} in {year}")

                    wikipedia_links = fetch_google_results(media_website, 1, start_date, end_date)
                    results = extract_links_from_wikipedia(media_website, wikipedia_links)

                    serp_data.append({
                        'website': media_website,
                        'date': datetime.now(timezone.utc).isoformat(),
                        'results': results,
                        'media_metadata': media
                    })

                if serp_data:
                    json_file_path = f'{media_type}/{state}/{media_type}_articles_{state}_{year}.jsonl.gz'
                    try:
                        with gzip.open(json_file_path, 'wt', encoding='utf-8') as jsonl_gzip_file:
                            for entry in serp_data:
                                jsonl_gzip_file.write(json.dumps(entry) + '\n')
                        logging.info(f"Saved SERP data for {state} in {year} to {json_file_path}")
                    except OSError as e:
                        logging.error(f"Error saving data to {json_file_path}: {e}")

                year_end_time = time.time()
                with open(execution_times_file, 'a') as execution_times_file_handle:
                    execution_times_file_handle.write(f'{state} {year}: {year_end_time - year_start_time:.2f} seconds\n')

            state_end_time = time.time()
            with open(execution_times_file, 'a') as execution_times_file_handle:
                execution_times_file_handle.write(f'State {state}: {state_end_time - state_start_time:.2f} seconds\n')

    overall_end_time = time.time()
    logging.info(f"Total execution time: {overall_end_time - overall_start_time:.2f} seconds.")

if __name__ == "__main__":
    main()
