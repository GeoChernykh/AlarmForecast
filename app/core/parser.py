import requests
from bs4 import BeautifulSoup


BASE_URL = "https://understandingwar.org/research"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                  " AppleWebKit/537.36 (KHTML, like Gecko)"
                  " Chrome/120.0.0.0 Safari/537.36"
}

def get_news_by_date(date):
    """
    Reurns news on a specified date
    """
    url = f"{BASE_URL}/??_date_from={date}%2C{date}&_teams=russia-ukraine"

    responce = requests.get(url, headers=headers)
    html = responce.text

    soup = BeautifulSoup(html, "lxml")
    print(soup.find("div", class_="team-research-listing").prettify())


if __name__ == "__main__":
    get_news_by_date("2026-03-01")