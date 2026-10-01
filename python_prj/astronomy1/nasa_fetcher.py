import os
import logging
import re
import time
from datetime import date as date_type, timedelta
from html.parser import HTMLParser
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv

from database import get_db_connection


NASA_APOD_URL = "https://science.nasa.gov/wp-json/wp/v2/apod-basic"
EARLIEST_APOD_DATE = date_type(2000, 1, 1)
APOD_PAGE_SIZE = 25
MAX_RATE_LIMIT_RETRIES = 3
MAX_CONSECUTIVE_PAGE_FAILURES = 3
MAX_PAGE_LOOKUPS = 10
RATE_LIMIT_BACKOFF_SECONDS = 2
# Seconds to wait for NASA to (connect, send data). Kept short so a slow
# answer becomes a clear error instead of the app timing out.
REQUEST_TIMEOUT = (10, 25)
APOD_FIELDS = "date,title,explanation,url,hdurl,media_type,copyright"
# Some NASA servers answer the default python-requests client slowly or not
# at all, so identify as a regular browser-style client asking for JSON.
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0 Safari/537.36"
    ),
    "Accept": "application/json",
}
logger = logging.getLogger(__name__)

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))


class _ExplanationParser(HTMLParser):
    """Extract readable text while preserving the explanation's content."""

    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

    def text(self):
        return "".join(self.parts)


def _parse_date(value):
    if isinstance(value, date_type):
        return value
    try:
        parsed_date = date_type.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError("Date must be in YYYY-MM-DD format.")
    if parsed_date.isoformat() != value:
        raise ValueError("Date must be in YYYY-MM-DD format.")
    return parsed_date


def _validate_date(date):
    if date is None:
        return None

    parsed_date = _parse_date(date)
    if parsed_date < EARLIEST_APOD_DATE:
        raise ValueError("APOD dates before 2000-01-01 are not available.")
    if parsed_date > date_type.today():
        raise ValueError("Future APOD dates are not available.")
    return parsed_date


def _get_api_key():
    """Return the optional NASA key; science.nasa.gov works without one."""
    return os.getenv("NASA_API_KEY", "").strip() or None


IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".tif", ".tiff")
# NASA appends site notices ("APOD's email ... has changed", "Tomorrow's
# picture") after a double line break; only the text before it is the
# explanation itself.
_NOTICE_BREAK = re.compile(r"<br\s*/?>\s*<br\s*/?>", re.IGNORECASE)


def _html_to_text(html):
    parser = _ExplanationParser()
    parser.feed(html or "")
    parser.close()
    return " ".join(parser.text().split())


def _clean_explanation(explanation):
    main_text = _NOTICE_BREAK.split(explanation or "", maxsplit=1)[0]
    text = _html_to_text(main_text)
    if text.lower().startswith("explanation:"):
        text = text[len("explanation:"):].strip()
    return text


def _looks_like_image(url):
    return urlparse(url or "").path.lower().endswith(IMAGE_EXTENSIONS)


def _image_url(data):
    """Return a direct image link.

    For images the science.nasa.gov endpoint puts the article page in ``url``
    and the picture itself in ``hdurl``.
    """
    url = data["url"]
    if data["media_type"] == "image" and not _looks_like_image(url) and data.get("hdurl"):
        return data["hdurl"]
    return url


def _normalise_apod(data):
    if not isinstance(data, dict):
        raise RuntimeError("NASA APOD returned an invalid response.")
    required_fields = ("date", "title", "explanation", "url", "media_type")
    if any(field not in data for field in required_fields):
        raise RuntimeError("NASA APOD returned an incomplete response.")

    return {
        "date": data["date"],
        "title": data["title"],
        "explanation": _clean_explanation(data["explanation"]),
        "url": _image_url(data),
        "hdurl": data.get("hdurl"),
        "media_type": data["media_type"],
        "copyright": _html_to_text(data.get("copyright")) or None,
    }


def _nasa_get(path="", params=None):
    """GET a NASA APOD endpoint and return the decoded JSON.

    Network problems are turned into short RuntimeErrors so the API can answer
    quickly with a clear message instead of hanging until the client gives up.
    """
    query = dict(params or {})
    api_key = _get_api_key()
    if api_key:
        query = {"api_key": api_key, **query}
    try:
        response = requests.get(
            NASA_APOD_URL + path,
            params=query,
            headers=REQUEST_HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
    except requests.Timeout:
        raise RuntimeError("NASA did not answer in time. Please try again in a moment.")
    except requests.ConnectionError:
        raise RuntimeError("Could not connect to NASA. Check your internet connection.")
    response.raise_for_status()
    try:
        return response.json()
    except ValueError:
        raise RuntimeError("NASA APOD returned a response that is not JSON.")


def _fetch_apod_item(target_date):
    """Fetch one APOD directly by its YYMMDD id (e.g. 260929 for 2026-09-29).

    Returns None when NASA has no item under that id, so callers can fall back
    to paging through the collection.
    """
    try:
        data = _nasa_get(f"/{target_date.strftime('%y%m%d')}", {"_fields": APOD_FIELDS})
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else None
        if status in (400, 404):
            return None
        raise
    if isinstance(data, list):
        data = data[0] if data else None
    try:
        apod = _normalise_apod(data)
    except RuntimeError:
        return None
    return apod if apod["date"] == target_date.isoformat() else None


def fetch_apod(date=None):
    """Fetch one APOD entry from NASA for the requested date.

    Tries NASA's direct item address first (one small request) and only pages
    through the archive when that address does not hold the requested day.
    """
    parsed_date = _validate_date(date)
    if parsed_date is None:
        entries = _fetch_apod_page(1, per_page=1)
        if not entries:
            raise RuntimeError("NASA APOD returned no entries.")
        return entries[0]

    apod = _fetch_apod_item(parsed_date)
    if apod is not None:
        return apod
    return _find_apod_by_page(parsed_date, newest_date=date_type.today())


def _find_apod_by_page(target_date, newest_date):
    """Locate one APOD by paging through the newest-first collection.

    There is roughly one APOD per day, so the page holding ``target_date`` can
    be estimated from its distance to the newest entry and then corrected by
    stepping one page at a time.
    """
    if target_date > newest_date:
        raise RuntimeError(
            f"NASA has not published an APOD for {target_date.isoformat()} yet."
        )
    page = max(1, (newest_date - target_date).days // APOD_PAGE_SIZE + 1)
    visited = set()
    for _ in range(MAX_PAGE_LOOKUPS):
        if page < 1 or page in visited:
            break
        visited.add(page)
        try:
            entries = _fetch_apod_page(page)
        except requests.HTTPError as exc:
            # WordPress answers 400 for a page past the end of the archive.
            if exc.response is not None and exc.response.status_code == 400 and page > 1:
                entries = []
            else:
                raise
        if not entries:
            page -= 1
            continue
        for apod in entries:
            if apod["date"] == target_date.isoformat():
                return apod
        page_dates = [_parse_date(apod["date"]) for apod in entries]
        if min(page_dates) > target_date:
            page += 1
        elif max(page_dates) < target_date:
            page -= 1
        else:
            break
    if target_date == date_type.today():
        raise RuntimeError(
            "NASA has not published today's picture yet. Try yesterday's date."
        )
    raise RuntimeError(f"No NASA APOD was found for {target_date.isoformat()}.")


def fetch_apod_range(start_date, end_date):
    """Fetch APOD entries for an inclusive date range.

    The WordPress endpoint currently ignores the documented date filters and
    returns its newest records. Historical synchronization therefore uses the
    endpoint's page pagination directly; this helper remains useful for the
    single-page API contract and validation.
    """
    parsed_start = _validate_date(start_date)
    parsed_end = _validate_date(end_date)
    if parsed_start > parsed_end:
        raise ValueError("Start date must not be after end date.")

    data = _nasa_get(
        params={
            "start_date": parsed_start.isoformat(),
            "end_date": parsed_end.isoformat(),
            "per_page": APOD_PAGE_SIZE,
            "_fields": APOD_FIELDS,
        }
    )
    if not isinstance(data, list):
        raise RuntimeError("NASA APOD returned an invalid date range response.")
    return [_normalise_apod(item) for item in data]


def _fetch_apod_page(page, per_page=APOD_PAGE_SIZE):
    data = _nasa_get(
        params={"page": page, "per_page": per_page, "_fields": APOD_FIELDS}
    )
    if not isinstance(data, list):
        raise RuntimeError("NASA APOD returned an invalid paginated response.")
    return [_normalise_apod(item) for item in data]


def _store_apod(conn, apod):
    cursor = conn.execute(
        """
        INSERT OR IGNORE INTO apod_entries
            (date, title, explanation, url, hdurl, media_type, copyright)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            apod["date"],
            apod["title"],
            apod["explanation"],
            apod["url"],
            apod["hdurl"],
            apod["media_type"],
            apod["copyright"],
        ),
    )
    return cursor.rowcount == 1


def fetch_and_store_apod(date=None):
    """Fetch an APOD entry and return its saved database row."""
    apod = fetch_apod(date)
    conn = get_db_connection()

    try:
        _store_apod(conn, apod)
        conn.commit()
        row = conn.execute(
            "SELECT * FROM apod_entries WHERE date = ?", (apod["date"],)
        ).fetchone()
        return dict(row)
    finally:
        conn.close()


def sync_historical_apods(start_date=None, end_date=None):
    """Fill missing APOD entries from the newest NASA page back to 2000-01-01.

    NASA's current ``apod-basic`` endpoint is a WordPress collection. Its
    date-filter query parameters are not applied by the live endpoint, so
    pagination is used as the range mechanism. Each request returns up to 25
    APODs, keeping the request count in the hundreds rather than thousands.
    """
    target_date = (
        _validate_date(start_date) if start_date is not None else EARLIEST_APOD_DATE
    )
    today = _validate_date(end_date) if end_date is not None else date_type.today()
    if target_date > today:
        raise ValueError("Start date must not be after end date.")
    conn = get_db_connection()
    summary = {
        "requested_range": {
            "start_date": target_date.isoformat(),
            "end_date": today.isoformat(),
        },
        "records_received": 0,
        "inserted": 0,
        "duplicates": 0,
        "skipped": 0,
        "failed": 0,
        "earliest_successfully_stored": None,
    }

    try:
        existing_dates = {
            date_type.fromisoformat(row["date"])
            for row in conn.execute("SELECT date FROM apod_entries")
        }
        page = 1
        rate_limit_retries = 0
        consecutive_failures = 0
        while consecutive_failures < MAX_CONSECUTIVE_PAGE_FAILURES:
            try:
                entries = _fetch_apod_page(page)
                rate_limit_retries = 0
                consecutive_failures = 0
                if not entries:
                    break
                page_dates = []
                all_page_dates = []
                for apod in entries:
                    apod_date = _parse_date(apod["date"])
                    all_page_dates.append(apod_date)
                    if apod_date < target_date or apod_date > today:
                        summary["skipped"] += 1
                        continue
                    page_dates.append(apod_date)
                    summary["records_received"] += 1
                    if apod_date in existing_dates or not _store_apod(conn, apod):
                        summary["duplicates"] += 1
                    else:
                        existing_dates.add(apod_date)
                        summary["inserted"] += 1
                        if (
                            summary["earliest_successfully_stored"] is None
                            or apod_date
                            < date_type.fromisoformat(
                                summary["earliest_successfully_stored"]
                            )
                        ):
                            summary["earliest_successfully_stored"] = apod_date.isoformat()
                conn.commit()
                logger.info(
                    "Processed NASA APOD page %d: received=%d inserted=%d duplicates=%d",
                    page,
                    len(page_dates),
                    summary["inserted"],
                    summary["duplicates"],
                )
                # Stop once this page reaches back to the requested start date.
                # All entries count here, including ones outside the range, so
                # pages newer than ``end_date`` do not end the sync early.
                if min(all_page_dates) <= target_date:
                    break
                page += 1
            except requests.HTTPError as exc:
                status = exc.response.status_code if exc.response is not None else None
                if status == 429 and rate_limit_retries < MAX_RATE_LIMIT_RETRIES:
                    rate_limit_retries += 1
                    logger.warning(
                        "NASA rate limited page %d; retry %d/%d",
                        page,
                        rate_limit_retries,
                        MAX_RATE_LIMIT_RETRIES,
                    )
                    time.sleep(RATE_LIMIT_BACKOFF_SECONDS * rate_limit_retries)
                    continue
                if status == 400 and page > 1:
                    # WordPress answers 400 when the page is past the last one.
                    break
                rate_limit_retries = 0
                consecutive_failures += 1
                summary["failed"] += 1
                logger.error("NASA APOD page %d failed with HTTP %s: %s", page, status, exc)
                page += 1
            except (requests.RequestException, RuntimeError, ValueError) as exc:
                consecutive_failures += 1
                summary["failed"] += 1
                logger.error("NASA APOD page %d failed: %s", page, exc)
                page += 1
    finally:
        conn.close()

    return summary