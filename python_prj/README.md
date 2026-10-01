# 🔭 Astronomy Picture of the Day

A FastAPI backend and Streamlit app for browsing NASA's Astronomy Picture of the Day (APOD).
Pictures are fetched from NASA on demand and saved in a local SQLite database.

## Features

- **Picture of the day**: pick any date since 2000, step to the previous or next day, or jump to a random one.
- **Gallery**: browse saved pictures in a grid, filter by year and month, and search titles and explanations.
- **Admin** (needs an API key): add, edit and delete entries, fetch a single day from NASA, or sync a whole date range.

## Project structure

```
astronomy1/
├── main.py              FastAPI app
├── app.py               Streamlit front end
├── nasa_fetcher.py      Fetching and syncing pictures from NASA
├── database.py          SQLite access
├── generate_key.py      Creates an admin API key in .env
├── auth/security.py     API key check for admin endpoints
├── models/apod.py       Pydantic models
├── routers/             API routes
├── .streamlit/          Streamlit theme
└── test_*.py            Tests
```

## Setup

```bash
cd astronomy1
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # Windows: copy .env.example .env
python generate_key.py             # writes an admin key into .env
```

Then put your NASA key (free at https://api.nasa.gov) in `.env`.

## Run

Start the API and the app in two terminals, both from the `astronomy1` folder:

```bash
uvicorn main:app --reload
streamlit run app.py
```

The API docs are at http://127.0.0.1:8000/docs and the app opens at http://localhost:8501.

## API

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| GET | `/api/apod/` | | All saved entries, or one with `?date=YYYY-MM-DD` |
| GET | `/api/apod/entries` | | Paginated entries with `year`, `month`, `search`, `page`, `page_size`, `sort` |
| GET | `/api/apod/{date}` | | One day's picture, fetched from NASA if not saved yet |
| POST | `/api/apod/` | ✓ | Add an entry |
| PUT | `/api/apod/{id}` | ✓ | Update an entry |
| DELETE | `/api/apod/{id}` | ✓ | Delete an entry |
| POST | `/api/apod/fetch?date=` | ✓ | Fetch and save one day from NASA |
| POST | `/api/apod/sync?start_date=` | ✓ | Save every missing day from today back to `start_date` |
| GET | `/api/validate_key/` | ✓ | Check an API key |

Admin requests send the key in an `api-key` header.

## If pictures load slowly

Run `python check_nasa.py` in the `astronomy1` folder. It shows how long NASA takes to answer from your computer.

## Tests

```bash
cd astronomy1
pytest
```
