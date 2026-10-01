import sqlite3
from datetime import date, timedelta
from unittest.mock import Mock, patch

import pytest
import requests

import nasa_fetcher


def _apod(date_value):
    return {
        "date": date_value,
        "title": f"APOD {date_value}",
        "explanation": "Explanation",
        "url": f"https://example.test/{date_value}.jpg",
        "hdurl": None,
        "media_type": "image",
        "copyright": None,
    }


@pytest.fixture
def database(tmp_path, monkeypatch):
    database_path = tmp_path / "astronomy.db"

    def connection():
        conn = sqlite3.connect(database_path)
        conn.row_factory = sqlite3.Row
        return conn

    monkeypatch.setattr(nasa_fetcher, "get_db_connection", connection)
    monkeypatch.setattr(nasa_fetcher.time, "sleep", lambda seconds: None)
    with connection() as conn:
        conn.execute(
            """
            CREATE TABLE apod_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                explanation TEXT,
                url TEXT,
                hdurl TEXT,
                media_type TEXT,
                copyright TEXT
            )
            """
        )
    monkeypatch.setenv("NASA_API_KEY", "test-key")
    return connection


def _response(payload=None, status_code=200):
    response = Mock(status_code=status_code)
    response.json.return_value = payload
    if status_code >= 400:
        response.raise_for_status.side_effect = requests.HTTPError(
            f"HTTP {status_code}", response=response
        )
    return response


def _newest_first(start, end):
    """Return APODs from ``end`` back to ``start``, like the live endpoint."""
    days = (end - start).days
    return [_apod((end - timedelta(days=offset)).isoformat()) for offset in range(days + 1)]


def _paged(entries, items_by_id=None):
    """Serve ``entries`` in NASA-sized pages, answering 400 past the last page.

    Direct item requests (``/YYMMDD``) answer from ``items_by_id`` or 404.
    """
    items_by_id = items_by_id or {}

    def get(url, params, headers, timeout):
        if url != nasa_fetcher.NASA_APOD_URL:
            item = items_by_id.get(url.rsplit("/", 1)[1])
            return _response(item) if item else _response(status_code=404)
        per_page = params.get("per_page", nasa_fetcher.APOD_PAGE_SIZE)
        start = (params.get("page", 1) - 1) * per_page
        page = entries[start:start + per_page]
        if not page and params.get("page", 1) > 1:
            return _response(status_code=400)
        return _response(page)

    return Mock(side_effect=get)


def _recent(days):
    return _newest_first(date.today() - timedelta(days=days), date.today())


def test_fetch_single_apod_uses_direct_item_address(monkeypatch):
    monkeypatch.setenv("NASA_API_KEY", "test-key")
    get = Mock(return_value=_response(_apod("2026-09-29")))
    monkeypatch.setattr(nasa_fetcher.requests, "get", get)

    result = nasa_fetcher.fetch_apod("2026-09-29")

    assert result["date"] == "2026-09-29"
    get.assert_called_once_with(
        nasa_fetcher.NASA_APOD_URL + "/260929",
        params={"api_key": "test-key", "_fields": nasa_fetcher.APOD_FIELDS},
        headers=nasa_fetcher.REQUEST_HEADERS,
        timeout=nasa_fetcher.REQUEST_TIMEOUT,
    )


def test_fetch_latest_apod_without_date(monkeypatch):
    monkeypatch.setenv("NASA_API_KEY", "test-key")
    get = _paged(_recent(30))
    monkeypatch.setattr(nasa_fetcher.requests, "get", get)

    assert nasa_fetcher.fetch_apod()["date"] == date.today().isoformat()
    assert get.call_args.kwargs["params"]["per_page"] == 1


def test_fetch_single_apod_pages_back_when_item_address_misses(monkeypatch):
    monkeypatch.setenv("NASA_API_KEY", "test-key")
    target = (date.today() - timedelta(days=120)).isoformat()
    get = _paged(_recent(200))
    monkeypatch.setattr(nasa_fetcher.requests, "get", get)

    result = nasa_fetcher.fetch_apod(target)

    assert result["date"] == target
    assert get.call_count <= 4


def test_fetch_single_apod_ignores_item_with_wrong_date(monkeypatch):
    monkeypatch.setenv("NASA_API_KEY", "test-key")
    target = date.today() - timedelta(days=10)
    wrong = _apod((target - timedelta(days=1)).isoformat())
    get = _paged(_recent(30), {target.strftime("%y%m%d"): wrong})
    monkeypatch.setattr(nasa_fetcher.requests, "get", get)

    assert nasa_fetcher.fetch_apod(target.isoformat())["date"] == target.isoformat()


def test_fetch_single_apod_reports_missing_date(monkeypatch):
    monkeypatch.setenv("NASA_API_KEY", "test-key")
    missing = (date.today() - timedelta(days=40)).isoformat()
    entries = [entry for entry in _recent(100) if entry["date"] != missing]
    monkeypatch.setattr(nasa_fetcher.requests, "get", _paged(entries))

    with pytest.raises(RuntimeError, match="No NASA APOD was found"):
        nasa_fetcher.fetch_apod(missing)


def test_fetch_today_before_nasa_publishes(monkeypatch):
    monkeypatch.setenv("NASA_API_KEY", "test-key")
    entries = _newest_first(date.today() - timedelta(days=30), date.today() - timedelta(days=1))
    monkeypatch.setattr(nasa_fetcher.requests, "get", _paged(entries))

    with pytest.raises(RuntimeError, match="not published today's picture"):
        nasa_fetcher.fetch_apod(date.today().isoformat())


def test_slow_nasa_becomes_clear_error(monkeypatch):
    monkeypatch.setenv("NASA_API_KEY", "test-key")
    monkeypatch.setattr(
        nasa_fetcher.requests, "get", Mock(side_effect=requests.Timeout("read timed out"))
    )

    with pytest.raises(RuntimeError, match="did not answer in time"):
        nasa_fetcher.fetch_apod("2026-09-29")


def test_fetch_apod_range_uses_nasa_date_range(monkeypatch):
    monkeypatch.setenv("NASA_API_KEY", "test-key")
    get = Mock(return_value=_response([_apod("2000-01-01"), _apod("2000-01-02")]))
    monkeypatch.setattr(nasa_fetcher.requests, "get", get)

    result = nasa_fetcher.fetch_apod_range("2000-01-01", "2000-01-02")

    assert [entry["date"] for entry in result] == ["2000-01-01", "2000-01-02"]
    get.assert_called_once_with(
        nasa_fetcher.NASA_APOD_URL,
        params={
            "api_key": "test-key",
            "start_date": "2000-01-01",
            "end_date": "2000-01-02",
            "per_page": nasa_fetcher.APOD_PAGE_SIZE,
            "_fields": nasa_fetcher.APOD_FIELDS,
        },
        headers=nasa_fetcher.REQUEST_HEADERS,
        timeout=nasa_fetcher.REQUEST_TIMEOUT,
    )


def test_lower_boundary_is_allowed_and_dates_before_it_are_rejected(monkeypatch):
    monkeypatch.setenv("NASA_API_KEY", "test-key")
    get = Mock(return_value=_response(_apod("2000-01-01")))
    monkeypatch.setattr(nasa_fetcher.requests, "get", get)

    nasa_fetcher.fetch_apod("2000-01-01")

    with pytest.raises(ValueError, match="before 2000-01-01"):
        nasa_fetcher.fetch_apod("1999-12-31")
    get.assert_called_once()


def test_invalid_and_future_dates_are_rejected():
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        nasa_fetcher._validate_date("2000-1-1")
    with pytest.raises(ValueError, match="Future"):
        nasa_fetcher._validate_date(date.today() + timedelta(days=1))


def test_fetch_and_store_does_not_duplicate_existing_apod(database, monkeypatch):
    monkeypatch.setattr(
        nasa_fetcher.requests, "get", Mock(return_value=_response(_apod("2000-01-01")))
    )

    nasa_fetcher.fetch_and_store_apod("2000-01-01")
    nasa_fetcher.fetch_and_store_apod("2000-01-01")

    with database() as conn:
        assert conn.execute("SELECT COUNT(*) FROM apod_entries").fetchone()[0] == 1


def test_historical_sync_stores_range_and_stops_at_start_date(database, monkeypatch):
    entries = _newest_first(date(2000, 1, 1), date(2000, 3, 31))
    get = _paged(entries)
    monkeypatch.setattr(nasa_fetcher.requests, "get", get)

    summary = nasa_fetcher.sync_historical_apods("2000-03-01", "2000-03-31")

    assert summary["inserted"] == 31
    assert summary["failed"] == 0
    assert summary["earliest_successfully_stored"] == "2000-03-01"
    assert get.call_count == 2


def test_historical_sync_does_not_stop_on_pages_newer_than_end_date(
    database, monkeypatch
):
    entries = _newest_first(date(2000, 1, 1), date(2000, 6, 30))
    monkeypatch.setattr(nasa_fetcher.requests, "get", _paged(entries))

    summary = nasa_fetcher.sync_historical_apods("2000-01-01", "2000-01-31")

    assert summary["inserted"] == 31
    assert summary["earliest_successfully_stored"] == "2000-01-01"


def test_historical_sync_skips_already_populated_dates(database, monkeypatch):
    with database() as conn:
        conn.execute(
            """
            INSERT INTO apod_entries
                (date, title, explanation, url, media_type)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("2000-01-02", "Existing", "Explanation", "url", "image"),
        )

    monkeypatch.setattr(
        nasa_fetcher.requests,
        "get",
        _paged(_newest_first(date(2000, 1, 1), date(2000, 1, 2))),
    )

    summary = nasa_fetcher.sync_historical_apods("2000-01-01", "2000-01-02")

    assert summary["inserted"] == 1
    assert summary["duplicates"] == 1
    with database() as conn:
        assert conn.execute("SELECT COUNT(*) FROM apod_entries").fetchone()[0] == 2


def test_historical_sync_gives_up_after_repeated_failures(database, monkeypatch):
    get = Mock(return_value=_response(status_code=500))
    monkeypatch.setattr(nasa_fetcher.requests, "get", get)

    summary = nasa_fetcher.sync_historical_apods("2000-01-01", "2000-01-02")

    assert summary["failed"] == nasa_fetcher.MAX_CONSECUTIVE_PAGE_FAILURES
    assert get.call_count == nasa_fetcher.MAX_CONSECUTIVE_PAGE_FAILURES


def test_historical_sync_retries_rate_limits_before_failing(database, monkeypatch):
    get = Mock(return_value=_response(status_code=429))
    monkeypatch.setattr(nasa_fetcher.requests, "get", get)

    summary = nasa_fetcher.sync_historical_apods("2000-01-01", "2000-01-02")

    retries_per_page = nasa_fetcher.MAX_RATE_LIMIT_RETRIES + 1
    assert summary["failed"] == nasa_fetcher.MAX_CONSECUTIVE_PAGE_FAILURES
    assert get.call_count == retries_per_page * nasa_fetcher.MAX_CONSECUTIVE_PAGE_FAILURES


def test_normalise_real_science_nasa_response():
    # Shape of a real science.nasa.gov apod-basic item (trimmed).
    item = {
        "date": "2026-09-29",
        "title": "Sh2-188: The Shrimp Nebula",
        "media_type": "image",
        "explanation": (
            "<strong>Explanation: </strong>What causes the swirl in the "
            '<a href="https://example.test">Shrimp Nebula</a>? Its high speed.'
            "<br><br><strong>APOD's email for image submissions has changed.</strong>"
            "<br><strong>Tomorrow's picture: </strong><a href=\"x\">open space</a>"
        ),
        "copyright": '<a href="https://www.instagram.com/x/">Pawel Piechnik</a>',
        "url": "https://science.nasa.gov/image-article/apod-2026-september-29-sh2-188/",
        "hdurl": (
            "https://assets.science.nasa.gov/dynamicimage/assets/science/cds/apod/"
            "apod/2026/september/Shrimp_Pawel_2048.jpg?w=2048&h=2560&fit=clip"
        ),
    }

    apod = nasa_fetcher._normalise_apod(item)

    assert apod["explanation"] == "What causes the swirl in the Shrimp Nebula? Its high speed."
    assert apod["copyright"] == "Pawel Piechnik"
    assert apod["url"] == item["hdurl"]


def test_normalise_keeps_direct_image_and_video_urls():
    image = {**_apod("2000-01-01"), "hdurl": "https://example.test/hd.jpg"}
    video = {**_apod("2000-01-01"), "media_type": "video",
             "url": "https://www.youtube.com/embed/abc"}

    assert nasa_fetcher._normalise_apod(image)["url"] == image["url"]
    assert nasa_fetcher._normalise_apod(video)["url"] == video["url"]
