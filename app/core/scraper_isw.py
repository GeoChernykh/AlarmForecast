import requests
from bs4 import BeautifulSoup
import json
import time
from urllib.parse import urljoin


def scrape_isw(max_pages=3):
    base_url = "https://understandingwar.org"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    all_articles_links = []

    for page in range(1, max_pages + 1):
        print(f"page: {page}")

        if page == 1:
            url = f"{base_url}/research/?_teams=russia-ukraine"
        else:
            url = f"{base_url}/research/?_teams=russia-ukraine&_paged={page}"

        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')

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

    for count, link in enumerate(all_articles_links, 1):
        print(f"parser {count}/{len(all_articles_links)}")
        try:
            page_resp = requests.get(link, headers=headers)
            page_soup = BeautifulSoup(page_resp.text, 'html.parser')

            title_tag = page_soup.select_one('h1.gb-headline, h1#page-title, h1')
            title = title_tag.text.strip() if title_tag else "no title"

            date = "no data"
            date_tag = page_soup.select_one('h6.gb-text')
            if date_tag and "202" in date_tag.text:
                date = date_tag.text.strip()
            else:
                meta_date = page_soup.find('meta', property='article:published_time')
                if meta_date:
                    date = meta_date.get('content', '').split('T')[0]

            takeaways = []

            kt_container = page_soup.find(attrs={"data-id": "key-takeaways"})
            if kt_container:
                list_elem = kt_container.find(['ul', 'ol'])
                if list_elem:
                    for li in list_elem.find_all('li'):
                        takeaways.append(li.text.strip())

            if not takeaways:
                headers_tags = page_soup.find_all(['h2', 'h3', 'strong'])
                for header in headers_tags:
                    if "Key Takeaways" in header.text or "Toplines" in header.text:
                        parent = header.parent if header.name == 'strong' else header
                        curr = parent.find_next_sibling()
                        while curr:
                            if curr.name in ['ul', 'ol']:
                                for li in curr.find_all('li'):
                                    takeaways.append(li.text.strip())
                                break

                            nested_list = curr.find(['ul', 'ol'])
                            if nested_list:
                                for li in nested_list.find_all('li'):
                                    takeaways.append(li.text.strip())
                                break

                            if curr.name in ['h2', 'h3']:
                                break
                            curr = curr.find_next_sibling()
                        if takeaways:
                            break

            if not takeaways:
                takeaways.append("no key takeways")

            news_data.append({
                "date": date,
                "title": title,
                "url": link,
                "key_takeaways": takeaways
            })

            time.sleep(0.5)

        except Exception as e:
            print(f"error {link}: {e}")

    with open('isw_news.json', 'w', encoding='utf-8') as f:
        json.dump(news_data, f, ensure_ascii=False, indent=4)

    print(f"\ncomplete")


if __name__ == "__main__":
    scrape_isw(max_pages=71)