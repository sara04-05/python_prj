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


def _paged(entries):
    """Serve ``entries`` in NASA-sized pages, answering 400 past the last page."""

    def get(url, params, timeout):
        if "page" not in params:
            return _response(entries[:1])
        start = (params["page"] - 1) * nasa_fetcher.APOD_PAGE_SIZE
        page = entries[start:start + nasa_fetcher.APOD_PAGE_SIZE]
        if not page and params["page"] > 1:
            return _response(status_code=400)
        return _response(page)

    return Mock(side_effect=get)


def test_fetch_single_apod_uses_requested_date(monkeypatch):
    monkeypatch.setenv("NASA_API_KEY", "test-key")
    get = Mock(return_value=_response(_apod("2000-01-01")))
    monkeypatch.setattr(nasa_fetcher.requests, "get", get)

    result = nasa_fetcher.fetch_apod("2000-01-01")

    assert result["date"] == "2000-01-01"
    get.assert_called_once_with(
        nasa_fetcher.NASA_APOD_URL,
        params={"api_key": "test-key", "per_page": 1, "date": "2000-01-01"},
        timeout=30,
    )


def test_fetch_single_apod_accepts_list_response(monkeypatch):
    monkeypatch.setenv("NASA_API_KEY", "test-key")
    monkeypatch.setattr(
        nasa_fetcher.requests, "get", Mock(return_value=_response([_apod("2000-01-01")]))
    )

    assert nasa_fetcher.fetch_apod("2000-01-01")["date"] == "2000-01-01"


def test_fetch_single_apod_pages_back_when_date_filter_is_ignored(monkeypatch):
    monkeypatch.setenv("NASA_API_KEY", "test-key")
    entries = _newest_first(date(2000, 1, 1), date(2000, 6, 30))
    get = _paged(entries)
    monkeypatch.setattr(nasa_fetcher.requests, "get", get)

    result = nasa_fetcher.fetch_apod("2000-02-14")

    assert result["date"] == "2000-02-14"
    assert get.call_count <= 4


def test_fetch_single_apod_reports_missing_date(monkeypatch):
    monkeypatch.setenv("NASA_API_KEY", "test-key")
    entries = [
        entry for entry in _newest_first(date(2000, 1, 1), date(2000, 3, 1))
        if entry["date"] != "2000-02-14"
    ]
    monkeypatch.setattr(nasa_fetcher.requests, "get", _paged(entries))

    with pytest.raises(RuntimeError, match="No NASA APOD was found"):
        nasa_fetcher.fetch_apod("2000-02-14")


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
        },
        timeout=30,
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
