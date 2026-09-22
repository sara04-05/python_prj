"""
Scrapes NASA's Astronomy Picture of the Day (APOD) from the official
WordPress API endpoint: https://science.nasa.gov/wp-json/wp/v2/apod-basic/

Auto-classifies each entry into a category (Galaxy, Nebula, Planet, etc.)
based on keywords in the title/explanation, and extracts topic tags
(the "genres" equivalent).

Uses NASA's public WordPress API - no API key required!
"""
import os
import time
import re
from datetime import date, timedelta

import requests
from dotenv import load_dotenv

load_dotenv()

# NASA APOD WordPress API endpoint (no API key needed!)
APOD_URL = "https://science.nasa.gov/wp-json/wp/v2/apod-basic/"
NASA_API_KEY = os.getenv("NASA_API_KEY", "")  # Not needed for this endpoint

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


def fetch_apod_wordpress():
    """Fetch APOD entries from NASA's WordPress API.
    Returns a list of entries."""
    try:
        response = requests.get(APOD_URL, timeout=15)
        if response.status_code != 200:
            return []
        data = response.json()
        return data if isinstance(data, list) else []
    except Exception as e:
        print(f"Error fetching APOD data: {e}")
        return []


def parse_wordpress_apod(post):
    """Parse a single WordPress APOD post into our format.
    Returns dict with title, explanation, url, date, or None if invalid."""
    try:
        title = post.get("title", {}).get("rendered", "Untitled").strip()
        content = post.get("content", {}).get("rendered", "")
        explanation = content
        
        # Find featured image URL
        image_url = None
        if post.get("featured_media_src_url"):
            image_url = post.get("featured_media_src_url")
        elif post.get("better_featured_image", {}).get("source_url"):
            image_url = post.get("better_featured_image", {}).get("source_url")
        
        # Fallback: extract first image from content
        if not image_url and "<img" in content:
            match = re.search(r'src="([^"]+)"', content)
            if match:
                image_url = match.group(1)
        
        if not image_url:
            return None
        
        # Parse date
        date_str = post.get("date_gmt") or post.get("date")
        if date_str:
            try:
                post_date = date.fromisoformat(date_str.split("T")[0])
            except:
                post_date = date.today()
        else:
            post_date = date.today()
        
        return {
            "title": title,
            "explanation": explanation,
            "url": image_url,
            "date": post_date,
            "year": post_date.year
        }
    except Exception as e:
        print(f"Error parsing APOD post: {e}")
        return None


def fetch_apod(day):
    """Fetch a single day's APOD entry. Returns None on failure (e.g. the
    date has no entry, or media_type is 'video' instead of an image)."""
    # Legacy function - kept for compatibility
    posts = fetch_apod_wordpress()
    for post in posts:
        parsed = parse_wordpress_apod(post)
        if parsed and parsed["date"] == day:
            return parsed
    return None


def scrape_apod_range(start_date, end_date):
    """
    Scrapes APOD entries from WordPress API, filters by date range.
    Returns (images_dict, categories) matching the same shape:
    a dict keyed by (title, category) and a list of unique category names.
    """
    images_dict = {}
    categories = []

    # Fetch all available APOD entries from WordPress
    posts = fetch_apod_wordpress()
    print(f"Fetched {len(posts)} posts from NASA APOD API")
    
    for post in posts:
        parsed = parse_wordpress_apod(post)
        if not parsed:
            continue
        
        # Filter by date range
        post_date = parsed["date"]
        if not (start_date <= post_date <= end_date):
            continue
        
        title = parsed["title"]
        explanation = parsed["explanation"]
        category = classify_category(title, explanation)
        topics = extract_topics(title, explanation)

        images_dict[(title, category)] = {
            "date": post_date.isoformat(),
            "image_url": parsed["url"],
            "explanation": explanation,
            "topics": topics,
            "year": post_date.year,
        }
        if category not in categories:
            categories.append(category)
        
        time.sleep(0.05)  # Be polite to the API

    return images_dict, categories


if __name__ == "__main__":
    # Default: last 14 days. Adjust as needed - mind the DEMO_KEY's
    # 30 requests/hour limit if pulling a large range.
    end = date.today()
    start = end - timedelta(days=14)

    print(f"Fetching APOD entries from {start} to {end}...")
    images, cats = scrape_apod_range(start, end)
    print(f"Fetched {len(images)} images across {len(cats)} categories: {cats}")
