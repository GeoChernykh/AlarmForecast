import json
from flask import Flask
from pathlib import Path
from datetime import datetime, timedelta
from app.api.forecast_route import forecast_bp
from app.api.alarm_api import alarm_bp
from app.errors import register_error_handlers
from app.core.scraper_isw import scrape_isw

def create_app():
    app = Flask(__name__)

    

    register_error_handlers(app)

    return app


app = create_app()

def _parse_date(raw: str) -> datetime | None:
    """Convert an ISW date string into a :class:`datetime`.

    The format may be like ``March 4, 2026`` or ``2026-03-04``.  If parsing
    fails we return ``None``.
    """
    for fmt in ("%B %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt)
        except Exception:
            continue
    return None

def _get_last_date_from_json(file_path: Path) -> datetime | None:
    """Return the latest date recorded in the JSON file.

    If the file is missing, empty, or contains invalid JSON we return ``None``
    and the caller will treat the dataset as empty.  Any errors during load are
    caught so the script does not crash.
    """
    if not file_path.exists():
        return None

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:  # including JSONDecodeError
        print(f"warning: could not read JSON from {file_path}: {e}")
        return None

    if not isinstance(data, list):
        return None

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
    data_file = Path("data/isw/isw_data.json")
    last_dt = _get_last_date_from_json(data_file)
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
            print("scraper returned no new articles")
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

        merged = existing + to_add
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=4)

        print(f"added {len(to_add)} articles (total {len(merged)})")
    else:
        default_start = datetime(2022, 2, 24)
        start_str = default_start.strftime("%Y-%m-%d")
        end_str = today.strftime("%Y-%m-%d")
        print(f"no existing ISW data; scraping full range {start_str} to {end_str}")
        scrape_isw(start_date=start_str, end_date=end_str, save_result=True, max_pages=100)

if __name__ == "__main__":
    _run_scraper_range()
    app.run(debug=True)