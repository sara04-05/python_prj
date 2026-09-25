import sqlite3
from typing import Optional


def get_db_connection():
    """Return a connection to the SQLite database."""
    conn = sqlite3.connect("astronomy.db")
    conn.row_factory = sqlite3.Row
    return conn


def get_apod_entries(
    *,
    year: Optional[int] = None,
    month: Optional[int] = None,
    search: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
    descending: bool = False,
):
    """Return saved APOD entries with optional album-oriented filters."""
    query = "SELECT * FROM apod_entries"
    conditions = []
    parameters = []

    if year is not None:
        conditions.append("strftime('%Y', date) = ?")
        parameters.append(f"{year:04d}")
    if month is not None:
        conditions.append("strftime('%m', date) = ?")
        parameters.append(f"{month:02d}")
    if search:
        conditions.append("(title LIKE ? OR explanation LIKE ?)")
        search_pattern = f"%{search}%"
        parameters.extend([search_pattern, search_pattern])

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY date " + ("DESC" if descending else "ASC")

    if limit is not None:
        query += " LIMIT ? OFFSET ?"
        parameters.extend([limit, offset])

    conn = get_db_connection()
    try:
        rows = conn.execute(query, parameters).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def create_database():
    """Create the APOD table if it does not already exist."""
    conn = get_db_connection()

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS apod_entries (
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

    conn.commit()
    conn.close()


if __name__ == "__main__":
    create_database()
    print("Database created successfully.")
