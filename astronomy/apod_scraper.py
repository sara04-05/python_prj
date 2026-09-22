"""
Scrapes NASA's Astronomy Picture of the Day (APOD) API for a date range,
auto-classifies each entry into a category (Galaxy, Nebula, Planet, etc.)
based on keywords in the title/explanation, and extracts topic tags
(the "genres" equivalent).

Get a free API key at https://api.nasa.gov (instant, no approval wait).
Without one, NASA's shared DEMO_KEY works but is rate-limited to
30 requests/hour and 50/day - fine for testing, not for bulk backfills.
"""
import os
import time
from datetime import date, timedelta

import requests
from dotenv import load_dotenv

load_dotenv()

APOD_URL = "https://api.nasa.gov/planetary/apod"
NASA_API_KEY = os.getenv("NASA_API_KEY", "DEMO_KEY")

# Keyword -> category classification. Checked in order against the
# lowercased title + explanation; first match wins. This is a simple
# heuristic, not an official NASA taxonomy - APOD doesn't provide one.
CATEGORY_KEYWORDS = [
    # More specific categories are checked first so a phrase like "solar
    # eclipse" (which contains "sun"-adjacent and "moon"-adjacent ideas)
    # lands under Eclipse rather than being caught by a broader keyword.
    ("Eclipse", ["eclipse"]),
    ("Meteor", ["meteor", "meteor shower", "meteorite"]),
    ("Galaxy", ["galaxy", "galaxies", "milky way", "andromeda"]),
    ("Nebula", ["nebula", "nebulae"]),
    ("Planet", ["mars", "jupiter", "saturn", "venus", "mercury", "neptune",
                "uranus", "exoplanet", "planet"]),
    ("Moon", ["moon", "lunar", "crater"]),
    ("Comet", ["comet"]),
    ("Star Cluster", ["star cluster", "globular cluster", "open cluster"]),
    ("Star", ["star ", "supernova", "nova", "stellar"]),
    ("Aurora", ["aurora"]),
    ("Sun", ["sun ", "solar flare", "sunspot", "corona"]),
    ("Spacecraft", ["rover", "satellite", "spacecraft", "iss",
                     "space station", "telescope", "launch"]),
    ("Deep Sky", ["deep sky", "cosmos", "universe", "black hole"]),
]

# Topic tags (the many-valued "genres" equivalent) - broader net than
# categories, an image can match several.
TOPIC_KEYWORDS = {
    "Astrophotography": ["photograph", "image captures", "captured"],
    "Infrared": ["infrared"],
    "X-ray": ["x-ray"],
    "Hubble": ["hubble"],
    "James Webb": ["webb", "jwst"],
    "Deep Space": ["light-years", "million light", "billion light", "distant"],
    "Solar System": ["solar system"],
    "Time-lapse": ["time-lapse", "time lapse"],
    "Meteor": ["meteor", "meteor shower"],
    "Eclipse": ["eclipse"],
}


def classify_category(title, explanation):
    text = f"{title} {explanation}".lower()
    for category, keywords in CATEGORY_KEYWORDS:
        if any(kw in text for kw in keywords):
            return category
    return "Other"


def extract_topics(title, explanation):
    text = f"{title} {explanation}".lower()
    topics = [topic for topic, keywords in TOPIC_KEYWORDS.items()
              if any(kw in text for kw in keywords)]
    return topics or ["Uncategorized"]


def fetch_apod(day):
    """Fetch a single day's APOD entry. Returns None on failure (e.g. the
    date has no entry, or media_type is 'video' instead of an image)."""
    params = {"api_key": NASA_API_KEY, "date": day.isoformat()}
    response = requests.get(APOD_URL, params=params, timeout=15)
    if response.status_code != 200:
        return None
    data = response.json()
    if data.get("media_type") != "image":
        return None
    return data


def scrape_apod_range(start_date, end_date):
    """
    Scrapes APOD entries for every day between start_date and end_date
    (inclusive). Returns (images_dict, categories) matching the same
    shape books_scraper.py produces: a dict keyed by (title, category)
    and a list of unique category names.
    """
    images_dict = {}
    categories = []

    current = start_date
    while current <= end_date:
        entry = fetch_apod(current)
        if entry:
            title = entry.get("title", "Untitled").strip()
            explanation = entry.get("explanation", "")
            category = classify_category(title, explanation)
            topics = extract_topics(title, explanation)

            images_dict[(title, category)] = {
                "date": current.isoformat(),
                "image_url": entry.get("hdurl") or entry.get("url", ""),
                "explanation": explanation,
                "topics": topics,
                "year": current.year,
            }
            if category not in categories:
                categories.append(category)

        # NASA's rate limit is generous but be a polite citizen
        time.sleep(0.2)
        current += timedelta(days=1)

    return images_dict, categories


if __name__ == "__main__":
    # Default: last 14 days. Adjust as needed - mind the DEMO_KEY's
    # 30 requests/hour limit if pulling a large range.
    end = date.today()
    start = end - timedelta(days=14)

    print(f"Fetching APOD entries from {start} to {end}...")
    images, cats = scrape_apod_range(start, end)
    print(f"Fetched {len(images)} images across {len(cats)} categories: {cats}")
