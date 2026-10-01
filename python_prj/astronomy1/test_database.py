import sqlite3

import database


def test_create_database_creates_apod_table(tmp_path, monkeypatch):
    database_path = tmp_path / "astronomy.db"
    monkeypatch.setenv("DATABASE_URL", str(database_path))

    database.create_database()

    conn = sqlite3.connect(database_path)
    table = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name = 'apod_entries'
        """
    ).fetchone()
    conn.close()
    assert table is not None


def test_relative_database_path_is_resolved_next_to_the_code(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "astronomy.db")

    assert database.get_database_path() == str(
        database.os.path.join(database.BASE_DIR, "astronomy.db")
    )


def test_album_filters(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", str(tmp_path / "astronomy.db"))
    database.create_database()
    conn = database.get_db_connection()
    for entry_date, title in [
        ("2020-01-05", "Orion Nebula"),
        ("2020-02-10", "Andromeda"),
        ("2021-01-15", "Orion again"),
    ]:
        conn.execute(
            "INSERT INTO apod_entries (date, title, explanation, url, media_type)"
            " VALUES (?, ?, '', 'url', 'image')",
            (entry_date, title),
        )
    conn.commit()
    conn.close()

    assert [e["title"] for e in database.get_apod_entries(year=2020)] == [
        "Orion Nebula",
        "Andromeda",
    ]
    assert len(database.get_apod_entries(search="orion")) == 2
    assert [
        e["date"] for e in database.get_apod_entries(descending=True, limit=1)
    ] == ["2021-01-15"]
