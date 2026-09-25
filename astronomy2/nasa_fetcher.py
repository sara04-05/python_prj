import os

import requests
from dotenv import load_dotenv

from database import get_db_connection


NASA_APOD_URL = "https://science.nasa.gov/wp-json/wp/v2/apod-basic"

load_dotenv()


def fetch_apod(date=None):
    """Fetch one APOD entry from NASA."""
    api_key = os.getenv("NASA_API_KEY")
    if not api_key:
        raise RuntimeError("NASA_API_KEY is not set in the environment.")

    params = {"api_key": api_key}
    if date:
        params["date"] = date

    response = requests.get(NASA_APOD_URL, params=params)
    response.raise_for_status()
    data = response.json()

    return {
        "date": data["date"],
        "title": data["title"],
        "explanation": data["explanation"],
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