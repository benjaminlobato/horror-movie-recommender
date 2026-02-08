"""
Phase 1: Create New Database Schema
Proper separation: horror_movies (universe) + horror_club_watches (what club watched)
"""
import sqlite3
from pathlib import Path

project_root = Path(__file__).parent.parent
db_path = project_root / 'data' / 'horror_recommender.db'

print("=" * 70)
print("PHASE 1: CREATING NEW DATABASE SCHEMA")
print("=" * 70)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check if new tables already exist
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='horror_movies'")
if cursor.fetchone():
    print("\n⚠️  WARNING: New tables already exist!")
    response = input("Drop and recreate? (yes/no): ")
    if response.lower() != 'yes':
        print("Aborted.")
        exit(0)

    print("\nDropping existing new tables...")
    cursor.execute("DROP TABLE IF EXISTS letterboxd_reviews")
    cursor.execute("DROP TABLE IF EXISTS horror_club_watches")
    cursor.execute("DROP TABLE IF EXISTS horror_movies")
    conn.commit()
    print("✓ Dropped old tables")

print("\n1. Creating horror_movies table (the universe)...")
cursor.execute("""
CREATE TABLE horror_movies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Core identifiers
    tmdb_id INTEGER UNIQUE NOT NULL,
    imdb_id VARCHAR(20),
    letterboxd_id VARCHAR(100),

    -- Basic info
    title VARCHAR(500) NOT NULL,
    year INTEGER,
    director VARCHAR(255),

    -- Metadata for recommendations
    genres TEXT,
    keywords TEXT,
    cast TEXT,
    overview TEXT,

    -- Ratings/popularity
    tmdb_vote_count INTEGER DEFAULT 0,
    tmdb_vote_average REAL,
    tmdb_popularity REAL,
    letterboxd_rating REAL,
    letterboxd_review_count INTEGER DEFAULT 0,

    -- Source tracking
    data_source VARCHAR(50),  -- 'horror_club', 'tmdb_keywords', 'letterboxd_coreviews'

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

cursor.execute("CREATE INDEX idx_horror_movies_tmdb ON horror_movies(tmdb_id)")
cursor.execute("CREATE INDEX idx_horror_movies_title ON horror_movies(title)")
cursor.execute("CREATE INDEX idx_horror_movies_source ON horror_movies(data_source)")

print("✓ Created horror_movies table")

print("\n2. Creating horror_club_watches table (what club watched)...")
cursor.execute("""
CREATE TABLE horror_club_watches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Link to movie
    movie_id INTEGER NOT NULL,

    -- Original list metadata
    list_entry_id INTEGER,  -- From original CSV (watch order!)
    data_object_id VARCHAR(50),  -- From Letterboxd export

    -- Watch info
    watch_date DATE,
    notes TEXT,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (movie_id) REFERENCES horror_movies(id)
)
""")

cursor.execute("CREATE INDEX idx_club_watches_movie ON horror_club_watches(movie_id)")
cursor.execute("CREATE INDEX idx_club_watches_entry ON horror_club_watches(list_entry_id)")

print("✓ Created horror_club_watches table")

print("\n3. Creating letterboxd_reviews table (for collaborative filtering)...")
cursor.execute("""
CREATE TABLE letterboxd_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    movie_id INTEGER NOT NULL,
    username VARCHAR(255) NOT NULL,

    -- Review metadata (optional)
    review_text TEXT,
    likes INTEGER DEFAULT 0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (movie_id) REFERENCES horror_movies(id),
    UNIQUE(movie_id, username)
)
""")

cursor.execute("CREATE INDEX idx_reviews_username ON letterboxd_reviews(username)")
cursor.execute("CREATE INDEX idx_reviews_movie_user ON letterboxd_reviews(movie_id, username)")

print("✓ Created letterboxd_reviews table")

conn.commit()

# Verify tables were created
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [row[0] for row in cursor.fetchall()]

print("\n" + "=" * 70)
print("SCHEMA CREATION COMPLETE")
print("=" * 70)
print(f"\nTables in database:")
for table in tables:
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    count = cursor.fetchone()[0]
    print(f"  - {table}: {count} rows")

print("\n✅ New schema ready for migration!")
print("\nNext step: Run phase2_migrate_horror_club.py")

conn.close()
