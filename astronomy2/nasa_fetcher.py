import os
from datetime import date as date_type
from html.parser import HTMLParser

import requests
from dotenv import load_dotenv

from database import get_db_connection


NASA_APOD_URL = "https://api.nasa.gov/planetary/apod"

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


def _validate_date(date):
    if date is None:
        return

    try:
        parsed_date = date_type.fromisoformat(date)
    except (TypeError, ValueError):
        raise ValueError("Date must be in YYYY-MM-DD format.")

    if parsed_date.isoformat() != date:
        raise ValueError("Date must be in YYYY-MM-DD format.")
    if parsed_date > date_type.today():
        raise ValueError("Future APOD dates are not available.")


def _clean_explanation(explanation):
    parser = _ExplanationParser()
    parser.feed(explanation)
    parser.close()
    return parser.text()


def fetch_apod(date=None):
    """Fetch one APOD entry from NASA for the requested date."""
    _validate_date(date)

    api_key = os.getenv("NASA_API_KEY")
    if not api_key:
        raise RuntimeError("NASA_API_KEY is missing from .env")

    params = {"api_key": api_key}
    if date:
        params["date"] = date

    response = requests.get(NASA_APOD_URL, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    if not isinstance(data, dict):
        raise RuntimeError("NASA APOD returned an invalid response.")
    if date and data.get("date") != date:
        raise RuntimeError(f"NASA APOD returned the wrong date for {date}.")

    return {
        "date": data["date"],
        "title": data["title"],
        "explanation": _clean_explanation(data["explanation"]),
        "url": data["url"],
        "hdurl": data.get("hdurl"),
        "media_type": data["media_type"],
        "copyright": data.get("copyright"),
    }


def fetch_and_store_apod(date=None):
    """Fetch an APOD entry and return its saved database row."""
    apod = fetch_apod(date)
    conn = get_db_connection()

    try:
        conn.execute(
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
        conn.commit()

        row = conn.execute(
            "SELECT * FROM apod_entries WHERE date = ?", (apod["date"],)
        ).fetchone()
        return dict(row)
    finally:
        conn.close()