import sqlite3


def get_db_connection():
    """Return a connection to the SQLite database."""
    conn = sqlite3.connect("astronomy.db")
    conn.row_factory = sqlite3.Row
    return conn


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
