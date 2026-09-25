import os
import logging
from datetime import date as date_type, timedelta
from html.parser import HTMLParser

import requests
from dotenv import load_dotenv

from database import get_db_connection


NASA_APOD_URL = "https://science.nasa.gov/wp-json/wp/v2/apod-basic"
EARLIEST_APOD_DATE = date_type(2000, 1, 1)
APOD_PAGE_SIZE = 25
MAX_RATE_LIMIT_RETRIES = 3
logger = logging.getLogger(__name__)

load_dotenv()


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
    api_key = os.getenv("NASA_API_KEY")
    if not api_key:
        raise RuntimeError("NASA_API_KEY is missing from .env")
    return api_key


def _clean_explanation(explanation):
    parser = _ExplanationParser()
    parser.feed(explanation)
    parser.close()
    return parser.text()


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
        "url": data["url"],
        "hdurl": data.get("hdurl"),
        "media_type": data["media_type"],
        "copyright": data.get("copyright"),
    }


def fetch_apod(date=None):
    """Fetch one APOD entry from NASA for the requested date."""
    parsed_date = _validate_date(date)
    params = {"api_key": _get_api_key(), "per_page": 1}
    if parsed_date:
        params["date"] = parsed_date.isoformat()

    response = requests.get(NASA_APOD_URL, params=params, timeout=30)
    response.raise_for_status()
    data = _normalise_apod(response.json())
    if parsed_date and data["date"] != parsed_date.isoformat():
        raise RuntimeError(
            f"NASA APOD returned the wrong date for {parsed_date.isoformat()}."
        )
    return data


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

    response = requests.get(
        NASA_APOD_URL,
        params={
            "api_key": _get_api_key(),
            "start_date": parsed_start.isoformat(),
            "end_date": parsed_end.isoformat(),
            "per_page": APOD_PAGE_SIZE,
        },
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, list):
        raise RuntimeError("NASA APOD returned an invalid date range response.")
    return [_normalise_apod(item) for item in data]


def _fetch_apod_page(page):
    response = requests.get(
        NASA_APOD_URL,
        params={
            "api_key": _get_api_key(),
            "page": page,
            "per_page": APOD_PAGE_SIZE,
            "_fields": "date,title,explanation,url,hdurl,media_type,copyright",
        },
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
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
    _get_api_key()
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
        while True:
            try:
                entries = _fetch_apod_page(page)
                rate_limit_retries = 0
                if not entries:
                    break
                page_dates = []
                for apod in entries:
                    apod_date = _parse_date(apod["date"])
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
                if min(page_dates, default=target_date) <= target_date:
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
                    continue
                rate_limit_retries = 0
                summary["failed"] += 1
                logger.error("NASA APOD page %d failed with HTTP %s: %s", page, status, exc)
                page += 1
            except (requests.RequestException, RuntimeError, ValueError) as exc:
                summary["failed"] += 1
                logger.error("NASA APOD page %d failed: %s", page, exc)
                page += 1
    finally:
        conn.close()

    return summary