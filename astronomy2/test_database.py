import sqlite3

from database import create_database


create_database()

conn = sqlite3.connect("astronomy.db")
table = conn.execute(
    """
    SELECT name
    FROM sqlite_master
    WHERE type = 'table' AND name = 'apod_entries'
    """
).fetchone()
conn.close()

if table:
    print("astronomy.db and apod_entries were created.")
else:
    raise RuntimeError("The apod_entries table was not created.")
