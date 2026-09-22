# 🌌 APOD Personal Gallery

**Astronomy Picture of the Day Archive — Categories/Topics → Daily Images, with Personal Ratings & Year**

A personal archive of NASA's Astronomy Picture of the Day. Dead simple: one image per day + explanation. Rate, categorize, and build a personal favorites gallery over time.

**Source:** NASA Science WordPress APOD API (`https://science.nasa.gov/wp-json/wp/v2/apod-basic/`) — No API key required!

## 🎯 Vision

Build your own curated collection of the cosmos. Every day, NASA releases a stunning image of the universe. This app lets you:
- **Archive** daily images automatically
- **Rate** images (0-5 stars) to build favorites
- **Categorize** by topic (Galaxy, Nebula, Planet, Aurora, Comet, etc.)
- **Browse** your personal collection by year, category, or rating
- **Discover** patterns in what captures your imagination

## ⭐ Features

- **⭐ Personal Favorites Gallery**: Browse high-rated images with rich filtering
- **📚 Archive Browser**: Explore all images organized by category, year, and rating
- **📊 Statistics & Timeline**: See collection growth and distribution over time
- **🏷️ Auto-Categorization**: Images are auto-classified (Galaxy, Nebula, Planet, Eclipse, etc.)
- **📅 Year-Based Organization**: Track captures by year, from 1995 to present
- **🎨 Rich UI**: Streamlit-based gallery with visual cards and detailed statistics
- **🔐 API-Key Authentication**: Secure CRUD operations

## Project Structure

```
astronomy/
├── main.py                      # FastAPI backend
├── app.py                       # Streamlit frontend (main interface)
├── database.py                  # SQLite database setup
├── apod_scraper.py             # NASA APOD API fetcher & auto-classifier
├── requirements.txt            # Dependencies
├── README.md                   # This file
│
├── models/                     # Pydantic data models
│   ├── __init__.py
│   ├── category.py             # Category: id, name
│   └── image.py                # Image: title, rating, year, category, topics, etc.
│
├── routers/                    # FastAPI endpoints
│   ├── __init__.py
│   ├── categories.py           # Category CRUD
│   ├── images.py               # Image CRUD
│   └── api_key.py              # API key validation
│
└── auth/                       # Security & authentication
    ├── __init__.py
    ├── security.py             # API key validation logic
    └── generate_key.py         # Key generation utility
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd astronomy
pip install -r requirements.txt
```

### 2. Set Up Environment

```bash
# Create .env file (API key not needed for public APOD endpoint)
echo "" > .env
```

### 3. Initialize Database

```bash
python -c "from database import create_database; create_database(); print('✅ Database initialized')"
```

### 4. Fetch Initial APOD Data

```bash
# Fetch last 30 days of APOD images
python -c "
from apod_scraper import scrape_apod_range
from datetime import date, timedelta

start = date.today() - timedelta(days=30)
end = date.today()
scrape_apod_range(start, end)
print(f'✅ Fetched APOD from {start} to {end}')
"
```

### 5. Generate API Key (for editing)

```bash
python auth/generate_key.py
# Copy the generated key, add to .env as:
# API_KEY=your_generated_key_here
```

### 6. Start the Backend (Terminal 1)

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### 7. Start the Streamlit Frontend (Terminal 2)

```bash
streamlit run app.py
```

Your browser will open to http://localhost:8501 with the **APOD Personal Gallery**.

## 📖 Usage

### ⭐ Favorites Tab
- See all images rated 4+ stars
- Filter by category, year range, or minimum rating
- Sort by rating or date
- Quick stats on your top favorites

### 📚 Archive Tab
- **Statistics**: See rating distribution and year-by-year growth
- **By Category**: Browse images organized by type (Galaxy, Nebula, etc.)
- **Timeline**: View all images chronologically with explanations

### 🛠️ Manage Tab
- **Add Image**: Manually add APOD images with ratings and details
- **Edit Image**: Quick rating updates
- **View All**: See entire collection in table format

### 📚 Categories Tab
- View, add, or customize image categories
- Reorganize your classification system

## 🏷️ Auto-Classification Categories

Images are automatically classified into:

- **Galaxy** - Milky Way, Andromeda, etc.
- **Nebula** - Star-forming clouds
- **Planet** - Mars, Jupiter, Saturn, etc.
- **Moon** - Lunar features, craters
- **Sun** - Solar flares, sunspots, corona
- **Star Cluster** - Globular and open clusters
- **Aurora** - Northern/Southern lights
- **Comet** - Nearby comets
- **Meteor** - Meteor showers
- **Eclipse** - Solar and lunar eclipses
- **Spacecraft** - Rovers, telescopes, ISS
- **Other** - Everything else

## 🔧 API & Endpoints

### Core Endpoints
- **GET /api/images/** — Fetch all images (public)
- **POST /api/images/** — Add new image (requires API key)
- **PUT /api/images/{id}** — Update image (requires API key)
- **DELETE /api/images/{id}** — Delete image (requires API key)

- **GET /api/categories/** — List all categories (public)
- **POST /api/categories/** — Create category (requires API key)
- **PUT /api/categories/{id}** — Update category (requires API key)
- **DELETE /api/categories/{id}** — Delete category (requires API key)

### Authentication
Include `api-key: your_key` in request headers for write operations.

## 💾 Database Schema

**images**
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER | Primary key |
| title | TEXT | Image title |
| category_id | INTEGER | Foreign key to categories |
| image_url | TEXT | Direct image URL |
| explanation | TEXT | NASA explanation |
| topics | TEXT | Comma-separated tags |
| capture_date | TEXT | YYYY-MM-DD |
| year | INTEGER | Year captured |
| rating | REAL | 0.0 to 5.0 (your rating) |

**categories**
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER | Primary key |
| name | TEXT | Category name (unique) |

## 🎨 Customization

**Modify auto-classification:** Edit `apod_scraper.py`
- `CATEGORY_KEYWORDS` — Add/remove category keywords
- `TOPIC_KEYWORDS` — Customize topic detection

**Backfill archive:** Fetch historical images
```python
from apod_scraper import scrape_apod_range
from datetime import date

start = date(1995, 6, 16)  # APOD inception
end = date(2024, 12, 31)

scrape_apod_range(start, end)
```

## 📚 Files Overview

| File | Purpose |
|------|---------|
| `main.py` | FastAPI backend server |
| `app.py` | Streamlit gallery frontend |
| `database.py` | SQLite database & migrations |
| `apod_scraper.py` | NASA API fetcher & classifier |
| `models/` | Pydantic request/response models |
| `routers/` | API endpoint handlers |
| `auth/` | API key generation & validation |

## 🌍 Data Source

**NASA Astronomy Picture of the Day**
- Public WordPress API: https://science.nasa.gov/wp-json/wp/v2/apod-basic/
- Available: 1995-present (18 most recent in API)
- No API key required
- No rate limits documented

## 🚀 Extending the Project

- **Export**: Generate CSV/JSON of rated images
- **Share**: Create public read-only gallery links
- **Timeline**: Add animated timeline view
- **Search**: Full-text search in titles & explanations  
- **Tags**: User-defined custom tags
- **Collections**: Group favorites into themed collections
- **APIs**: Expose public REST API for your collection
- **Email**: Weekly digest of top-rated images

## 📝 License

This project uses **public NASA data** and the **public WordPress APOD API** — no NASA API key required!
| `auth/generate_key.py` | Generate secure API keys |

## Troubleshooting

### "Invalid API Key" errors
- Ensure `API_KEY` is set in `.env` (for Streamlit, not NASA API)
- Check Streamlit is sending header: `{"api-key": your_key}`
- Verify no whitespace in key

### "Cannot reach API" errors (Streamlit)
- Make sure FastAPI is running: `uvicorn main:app --reload`
- Check `BASE_URL` in `.env` matches your API location
- Default: `http://localhost:8000/api`

### "No images showing" errors
- Check database populated: `python database.py`
- Verify database has data: Check `apod.db` file exists
- Try "Gallery & Visualizations" tab (works without auth)

### NASA APOD WordPress API errors
- Test API directly: `curl "https://science.nasa.gov/wp-json/wp/v2/apod-basic/"`
- Check internet connection
- WordPress endpoint may have occasional maintenance

### NASA API rate limited (old api.nasa.gov)
- This only applies if you were using the old NASA API
- New WordPress API has no rate limits!

### Database locked errors
- Ensure only one process accesses `apod.db` at a time
- Close and restart API/Streamlit if processes hang

### Images not showing in gallery
- Check category_id exists in database
- Verify image_url is accessible
- Inspect browser console for CORS issues (allow if needed)

## License

Open source — use freely for personal repositories.

---

**Status:** Running on localhost by default. For production:
- Use PostgreSQL instead of SQLite
- Add CORS middleware
- Use environment-based settings
- Enable HTTPS
- Set up CI/CD pipeline

