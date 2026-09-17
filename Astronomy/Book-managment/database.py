import sqlite3


# Function to establish a connection to the SQLite database
def get_db_connection():
    conn = sqlite3.connect('books.db')
    conn.row_factory = sqlite3.Row  # This allows the rows returned to behave like dictionaries
    return conn


def create_database():
    # Set up the SQLite database
    conn = sqlite3.connect('books.db')
    cursor = conn.cursor()

    # Create a table to store book information
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            author_id INTEGER,
            book_link TEXT,
            genres TEXT,
            average_rating REAL,
            published_year INTEGER,
            FOREIGN KEY (author_id) REFERENCES authors(id)
        )
    ''')
    cursor.execute('''
            CREATE TABLE IF NOT EXISTS authors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE
            )
        ''')
    conn.commit()
    return conn, cursor


def insert_authors(authors, cursor):
    author_ids = {}

    for author in authors:
        cursor.execute('''
            INSERT OR IGNORE INTO authors (name)
            VALUES (?)
        ''', (author,))
        cursor.execute('SELECT id FROM authors WHERE name = ?', (author,))
        author_ids[author] = cursor.fetchone()[0]

    return author_ids


def insert_books(books_dict, author_ids, cursor):
    for (title, author), info in books_dict.items():
        cursor.execute('''
            INSERT INTO books (title, author_id, book_link, genres, average_rating, published_year)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            title,
            author_ids[author],
            info['link'],
            ', '.join(info['genres']),
            float(info['avg_rating'].split()[0]) if info['avg_rating'] else None,
            int(info['published'].split()[0]) if info['published'] else None
        ))


def insert_data(books_dict, authors):
    conn, cursor = create_database()

    # Insert authors and get their IDs
    author_ids = insert_authors(authors, cursor)

    # Insert books using the author IDs
    insert_books(books_dict, author_ids, cursor)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    from books_scraper import scrape_books

    # Get the scraped data
    books_dict, authors = scrape_books()

    # Insert the data into the database
    insert_data(books_dict, authors)



