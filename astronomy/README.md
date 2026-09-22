# APOD Personal Gallery

A personal archive of NASA's Astronomy Picture of the Day, with your own
ratings, auto-classified categories (Galaxy, Nebula, Planet, etc.), and a
visual gallery dashboard. Same structure as the books project it's based
on: scraper -> SQLite -> FastAPI (CRUD + API-key auth) -> Streamlit.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:
- Get a free NASA API key at https://api.nasa.gov (instant, no approval
  wait) and set `NASA_API_KEY`. The default `DEMO_KEY` works for testing
  but is capped at 30 requests/hour and 50/day.
- Set `API_KEY` to any secret string of your choosing — this is what
  the Streamlit app sends to authorize adding/editing/deleting entries.

## 1. Scrape + populate the database

```bash
python database.py
```

This pulls the last 14 days of APOD entries (edit the date range at the
bottom of `apod_scraper.py` to backfill further — mind the rate limit)
and inserts them into `apod.db`, auto-sorted into categories and topics
based on keywords in each image's title/explanation.

## 2. Run the API

```bash
uvicorn main:app --reload
```

Runs at `http://localhost:8000`. Interactive docs at `/docs`.

## 3. Run the dashboard

In a second terminal:

```bash
streamlit run app.py
```

Enter the `API_KEY` from your `.env` in the sidebar to unlock add/edit/
delete. The **Gallery & Visualizations** tab works without a key — it
shows category/rating charts plus the actual images, sorted by your
rating, with an expandable NASA explanation for each.

## Files

- `apod_scraper.py` — pulls from NASA's APOD API, classifies category + topics
- `database.py` — SQLite schema (`categories`, `images`) and insert helpers
- `main.py` — FastAPI app, wires up the routers
- `routers/categories.py` — CRUD for categories (parent entity)
- `routers/images.py` — CRUD for images (child entity)
- `routers/api_key.py` — validates the `api-key` header
- `app.py` — Streamlit dashboard (Categories, Images, Gallery & Visualizations)

## Extending it

- Backfill further back than 14 days by editing the `start`/`end` dates
  in `apod_scraper.py`'s `__main__` block, or import `scrape_apod_range`
  and call it with any date range from your own script.
- The category classifier is a simple keyword heuristic — tune
  `CATEGORY_KEYWORDS` / `TOPIC_KEYWORDS` in `apod_scraper.py` if you want
  finer-grained or more accurate sorting.
- Add a "re-rate" quick action in the gallery view (a slider per image
  that PUTs straight to `/api/images/{id}`) if you want to rate images
  without leaving the gallery tab.
