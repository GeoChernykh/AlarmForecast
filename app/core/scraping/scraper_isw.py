import requests
from bs4 import BeautifulSoup
import json
import time
from urllib.parse import urljoin
from tqdm import tqdm
from pathlib import Path
from datetime import datetime, timedelta, date
import re


def scrape_isw(start_date: date | str = date(2022, 2, 24), end_date: date | str = date.today(),
               save_result=False, file_name="isw_data_v2.json", max_pages=3):
    # Convert string dates to date objects
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
    elif isinstance(start_date, datetime):
        start_date = start_date.date()

    if start_date is None:
        start_date = date(2022, 2, 24)
    
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
    elif isinstance(end_date, datetime):
        end_date = end_date.date()
    
    base_url = "https://understandingwar.org"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    all_articles_links = []

    for page in tqdm(range(1, max_pages + 1), desc="Scraping pages:"):
        url = f"{base_url}/research/?_date_from={start_date.strftime('%Y-%m-%d')}%2C{end_date.strftime('%Y-%m-%d')}&_teams=russia-ukraine"
        if page != 1:
            url += f"&_paged={page}"

        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'lxml')

        page_links = []
        for a in soup.select('h3.research-card-title a'):
            href = a.get('href')
            if href:
                full_url = urljoin(base_url, href)
                if full_url not in page_links:
                    page_links.append(full_url)

        if not page_links:
            print(f"no news in {page}")
            break

        all_articles_links.extend(page_links)

        time.sleep(1)


    if not all_articles_links:
        print("no news")
        return

    news_data = []

    for link in tqdm(all_articles_links, desc="Scraping links:"):
        try:
            page_resp = requests.get(link, headers=headers)
            page_soup = BeautifulSoup(page_resp.text, 'lxml')

            title_tag = page_soup.select_one('h1.gb-headline, h1#page-title, h1')
            title = title_tag.text.strip() if title_tag else "no title"

            date_ = "no data"
            date_tag = page_soup.select_one('h6.gb-text')
            if date_tag and "202" in date_tag.text:
                date_ = date_tag.text.strip()
            else:
                meta_date = page_soup.find('meta', property='article:published_time')
                if meta_date:
                    date_ = meta_date.get('content', '').split('T')[0]

            text_div = page_soup.find("div", id="printable-area").find("div", class_="dynamic-entry-content")
            
            endnotes = text_div.find("div", title="Endnotes")
            if endnotes:
                endnotes.decompose()

            text = text_div.get_text(separator=" ", strip=False)
            
            # Clean the text: remove URLs, newlines, and bracketed numbers
            text = re.sub(r'https?://\S+', '', text)
            text = re.sub(r'www\.\S+', '', text)
            text = re.sub(r'Endnotes \S+', '', text)
            text = re.sub(r'\n+', ' ', text)
            text = re.sub(r'\[\d+\]', '', text)
            text = re.sub(r'\s+', ' ', text).strip()
        
            # Parse date with multiple format options
            if date_ == "no data":
                continue
            
            parsed_date = None
            for fmt in ("%B %d, %Y", "%Y-%m-%d"):
                try:
                    parsed_date = datetime.strptime(date_, fmt).date()
                    break
                except ValueError:
                    continue
            
            if parsed_date is None:
                continue

            if start_date <= parsed_date <= end_date:
                news_data.append({
                    "date": parsed_date.strftime("%Y-%m-%d"),
                    "title": title,
                    "url": link,
                    "text": text
                })
                out_of_range = 0  # reset on a valid article
            else:
                out_of_range += 1
                if out_of_range >= 3:  # stop only after 3 consecutive misses
                    break

            time.sleep(0.5)

        except Exception as e:
            print(f"error {link}: {e}")

    if save_result:
        data_dir = Path("data/isw/")

        if not data_dir.exists():
            data_dir.mkdir(parents=True)

        if not file_name.endswith(".json"):
            file_name += ".json"

        file_path = data_dir / file_name

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(news_data, f, ensure_ascii=False, indent=4)

        
    return news_data


def _parse_date(raw: str) -> datetime | None:
    for fmt in ("%B %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None

def _get_last_date_from_json(file_path: Path) -> datetime | None:
    if not file_path.exists():
        return None

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    dates: list[datetime] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        raw = item.get("date")
        if not raw:
            continue
        dt = _parse_date(raw)
        if dt:
            dates.append(dt)
    return max(dates) if dates else None

def _run_scraper_range():
    data_file = Path("data/isw/isw_data_v2.json")

    last_dt = _get_last_date_from_json(data_file) if data_file.exists() else None
    today = datetime.today()

    today_str = today.strftime("%Y-%m-%d")
    end_str = last_dt.strftime("%Y-%m-%d") if last_dt else today_str

    if last_dt:
        start_dt = last_dt + timedelta(days=1)
        if start_dt.date() > today.date():
            print("nothing to scrape")
            return
        start_str = start_dt.strftime("%Y-%m-%d")
        end_str = today.strftime("%Y-%m-%d")
        print(f"scraping from {start_str} to {end_str} (last stored date {last_dt.date()})")

        new_items = scrape_isw(start_date=start_str, end_date=end_str,
                               save_result=False, max_pages=100) or []
        if not new_items:
            print("no new articles")
            return

        filtered: list[dict] = []
        seen_urls: set[str] = set()
        for item in new_items:
            url = item.get("url")
            if url in seen_urls:
                continue
            seen_urls.add(url)
            raw_date = item.get("date", "")
            dt = _parse_date(raw_date)
            if not dt or dt.date() < start_dt.date() or dt.date() > today.date():
                continue
            filtered.append(item)

        if not filtered:
            print("no new articles")
            return

        with open(data_file, "r", encoding="utf-8") as f:
            existing = json.load(f)

        existing_urls = {itm.get("url") for itm in existing if isinstance(itm, dict)}
        to_add = [itm for itm in filtered if itm.get("url") not in existing_urls]

        merged = to_add + existing
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=4)

        print(f"added {len(to_add)} articles (total {len(merged)})")
    else:
        default_start = datetime(2022, 2, 24)
        start_str = default_start.strftime("%Y-%m-%d")
        end_str = today.strftime("%Y-%m-%d")
        print(f"no existing ISW data => scraping full range {start_str} to {end_str}")
        scrape_isw(start_date=start_str, end_date=end_str, # TODO: add result to database
                   save_result=True, file_name="isw_data_v2", 
                   max_pages=100)

if __name__ == "__main__":
    _run_scraper_range()
    # scrape_isw(start_date=date.today() - timedelta(days=60), save_result=True, file_name="temp", max_pages=100)