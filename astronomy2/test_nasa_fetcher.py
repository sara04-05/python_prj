import sqlite3
from datetime import date
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


def test_fetch_single_apod_uses_requested_date(monkeypatch):
    monkeypatch.setenv("NASA_API_KEY", "test-key")
    response = Mock()
    response.json.return_value = _apod("2000-01-01")
    monkeypatch.setattr(nasa_fetcher.requests, "get", Mock(return_value=response))

    result = nasa_fetcher.fetch_apod("2000-01-01")

    assert result["date"] == "2000-01-01"
    nasa_fetcher.requests.get.assert_called_once_with(
        nasa_fetcher.NASA_APOD_URL,
        params={"api_key": "test-key", "date": "2000-01-01"},
        timeout=30,
    )


def test_fetch_apod_range_uses_nasa_date_range(monkeypatch):
    monkeypatch.setenv("NASA_API_KEY", "test-key")
    response = Mock()
    response.json.return_value = [_apod("2000-01-01"), _apod("2000-01-02")]
    monkeypatch.setattr(nasa_fetcher.requests, "get", Mock(return_value=response))

    result = nasa_fetcher.fetch_apod_range("2000-01-01", "2000-01-02")

    assert [entry["date"] for entry in result] == ["2000-01-01", "2000-01-02"]
    nasa_fetcher.requests.get.assert_called_once_with(
        nasa_fetcher.NASA_APOD_URL,
        params={
            "api_key": "test-key",
            "start_date": "2000-01-01",
            "end_date": "2000-01-02",
        },
        timeout=30,
    )


def test_lower_boundary_is_allowed_and_dates_before_it_are_rejected(monkeypatch):
    monkeypatch.setenv("NASA_API_KEY", "test-key")
    response = Mock()
    response.json.return_value = _apod("2000-01-01")
    monkeypatch.setattr(nasa_fetcher.requests, "get", Mock(return_value=response))

    nasa_fetcher.fetch_apod("2000-01-01")

    with pytest.raises(ValueError, match="before 2000-01-01"):
        nasa_fetcher.fetch_apod("1999-12-31")
    nasa_fetcher.requests.get.assert_called_once()


def test_fetch_and_store_does_not_duplicate_existing_apod(database, monkeypatch):
    response = Mock()
    response.json.return_value = _apod("2000-01-01")
    monkeypatch.setattr(nasa_fetcher.requests, "get", Mock(return_value=response))

    nasa_fetcher.fetch_and_store_apod("2000-01-01")
    nasa_fetcher.fetch_and_store_apod("2000-01-01")

    with database() as conn:
        assert conn.execute("SELECT COUNT(*) FROM apod_entries").fetchone()[0] == 1


def test_historical_sync_fetches_back_to_lower_boundary(database, monkeypatch):
    response = Mock()
    response.json.return_value = [_apod("2000-01-01"), _apod("2000-01-02")]
    monkeypatch.setattr(nasa_fetcher.requests, "get", Mock(return_value=response))

    summary = nasa_fetcher.sync_historical_apods(date(2000, 1, 2))

    assert summary == {"stored": 2, "skipped": 0, "failed": 0}
    request = nasa_fetcher.requests.get.call_args.kwargs["params"]
    assert request["start_date"] == "2000-01-01"
    assert request["end_date"] == "2000-01-02"


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

    response = Mock()
    response.json.return_value = [_apod("2000-01-01"), _apod("2000-01-02")]
    monkeypatch.setattr(nasa_fetcher.requests, "get", Mock(return_value=response))

    summary = nasa_fetcher.sync_historical_apods(date(2000, 1, 2))

    assert summary == {"stored": 1, "skipped": 1, "failed": 0}
    with database() as conn:
        assert conn.execute("SELECT COUNT(*) FROM apod_entries").fetchone()[0] == 2


def test_historical_sync_falls_back_to_single_dates_after_batch_failure(
    database, monkeypatch
):
    def get_response(url, params, timeout):
        response = Mock()
        if "start_date" in params:
            response.raise_for_status.side_effect = requests.RequestException("rate limited")
        else:
            response.json.return_value = [_apod(params["date"])][0]
        return response

    monkeypatch.setattr(nasa_fetcher.requests, "get", Mock(side_effect=get_response))

    summary = nasa_fetcher.sync_historical_apods(date(2000, 1, 2))

    assert summary == {"stored": 2, "skipped": 0, "failed": 0}


def test_historical_sync_does_not_retry_each_date_after_rate_limit(
    database, monkeypatch
):
    response = Mock(status_code=429)
    response.raise_for_status.side_effect = requests.HTTPError(
        "rate limited", response=response
    )
    request = Mock(return_value=response)
    monkeypatch.setattr(nasa_fetcher.requests, "get", request)

    summary = nasa_fetcher.sync_historical_apods(date(2000, 1, 2))

    assert summary == {"stored": 0, "skipped": 0, "failed": 2}
    request.assert_called_once()
