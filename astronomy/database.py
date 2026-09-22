import sqlite3


# Function to establish a connection to the SQLite database
def get_db_connection():
    conn = sqlite3.connect('apod.db')
    conn.row_factory = sqlite3.Row  # This allows the rows returned to behave like dictionaries
    return conn


def create_database():
    # Set up the SQLite database
    conn = sqlite3.connect('apod.db')
    cursor = conn.cursor()

    # Create a table to store category information
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        )
    ''')
    
    # Create a table to store image information
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            category_id INTEGER,
            image_url TEXT,
            explanation TEXT,
            topics TEXT,
            capture_date TEXT,
            year INTEGER,
            rating REAL DEFAULT 0,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        )
    ''')
    conn.commit()
    return conn, cursor


def insert_categories(categories, cursor):
    category_ids = {}

    for category in categories:
        cursor.execute('''
            INSERT OR IGNORE INTO categories (name)
            VALUES (?)
        ''', (category,))
        cursor.execute('SELECT id FROM categories WHERE name = ?', (category,))
        category_ids[category] = cursor.fetchone()[0]

    return category_ids


def insert_images(images_dict, category_ids, cursor):
    for (title, category), info in images_dict.items():
        cursor.execute('''
            INSERT INTO images
                (title, category_id, image_url, explanation, topics, capture_date, year, rating)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            title,
            category_ids[category],
            info['image_url'],
            info['explanation'],
            ', '.join(info['topics']),
            info['date'],
            info['year'],
            0.0  # default rating; the person rates it later via the API/dashboard
        ))


def insert_data(images_dict, categories):
    conn, cursor = create_database()
    category_ids = insert_categories(categories, cursor)
    insert_images(images_dict, category_ids, cursor)
    conn.commit()
    conn.close()


if __name__ == "__main__":
    from datetime import date, timedelta
    from apod_scraper import scrape_apod_range

    end = date.today()
    start = end - timedelta(days=14)

    images_dict, categories = scrape_apod_range(start, end)
    insert_data(images_dict, categories)
    print(f"Inserted {len(images_dict)} images across {len(categories)} categories.")
