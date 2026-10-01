import pytest
from fastapi.testclient import TestClient

import database
from main import app


HEADERS = {"api-key": "test-key"}
ENTRY = {
    "date": "2020-01-01",
    "title": "Orion Nebula",
    "explanation": "A stellar nursery.",
    "url": "https://example.test/orion.jpg",
    "hdurl": None,
    "media_type": "image",
    "copyright": None,
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", str(tmp_path / "astronomy.db"))
    monkeypatch.setenv("API_KEYS", "test-key,second-key")
    with TestClient(app) as test_client:
        yield test_client


def test_api_key_validation(client):
    assert client.get("/api/validate_key/", headers=HEADERS).status_code == 200
    assert client.get("/api/validate_key/", headers={"api-key": "second-key"}).status_code == 200
    assert client.get("/api/validate_key/", headers={"api-key": "wrong"}).status_code == 401
    assert client.get("/api/validate_key/").status_code == 401


def test_create_read_update_delete(client):
    created = client.post("/api/apod/", json=ENTRY, headers=HEADERS)
    assert created.status_code == 200
    entry_id = created.json()["id"]

    assert client.get("/api/apod/2020-01-01").json()["title"] == "Orion Nebula"
    assert client.post("/api/apod/", json=ENTRY, headers=HEADERS).status_code == 409

    updated = client.put(
        f"/api/apod/{entry_id}", json={**ENTRY, "title": "Orion"}, headers=HEADERS
    )
    assert updated.json()["title"] == "Orion"

    assert client.delete(f"/api/apod/{entry_id}", headers=HEADERS).status_code == 200
    assert client.delete(f"/api/apod/{entry_id}", headers=HEADERS).status_code == 404


def test_writes_require_api_key(client):
    assert client.post("/api/apod/", json=ENTRY).status_code == 401


def test_invalid_entries_are_rejected(client):
    for bad in ({"date": "2020-13-01"}, {"title": ""}, {"media_type": "gif"}):
        response = client.post("/api/apod/", json={**ENTRY, **bad}, headers=HEADERS)
        assert response.status_code == 422


def test_album_entries_endpoint(client):
    for day in ("2020-01-01", "2020-01-02", "2021-05-05"):
        client.post("/api/apod/", json={**ENTRY, "date": day}, headers=HEADERS)

    response = client.get("/api/apod/entries", params={"year": 2020, "sort": "asc"})
    assert [entry["date"] for entry in response.json()] == ["2020-01-01", "2020-01-02"]
    assert client.get("/api/apod/2020-1-1").status_code == 400
