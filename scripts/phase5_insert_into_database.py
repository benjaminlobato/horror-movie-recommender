"""
Phase 5: Insert matched movies into new database schema
Populates horror_movies and horror_club_watches tables
"""
import pandas as pd
import sqlite3
from pathlib import Path
from tqdm import tqdm

project_root = Path(__file__).parent.parent

print("=" * 70)
print("PHASE 5: INSERTING INTO DATABASE")
print("=" * 70)

# Load matched universe
universe_path = project_root / 'data' / 'horror_universe_with_ids.csv'
df = pd.read_csv(universe_path)

print(f"\n1. Loaded {len(df):,} movies from matched universe")
print(f"   - {df['tmdb_id'].notna().sum():,} with TMDB ID")
print(f"   - {df['imdb_id'].notna().sum():,} with IMDb ID")

# Load horror club list to get watch order
horror_club_path = project_root / 'data' / 'horror_club_with_ids.csv'
horror_club_df = pd.read_csv(horror_club_path)

# Create lookup: letterboxd_id -> list_entry_id (watch order)
club_lookup = {}
for idx, row in horror_club_df.iterrows():
    lb_id = row.get('film_slug')
    if pd.notna(lb_id):
        club_lookup[lb_id] = idx + 1  # list_entry_id is 1-indexed

print(f"2. Loaded {len(horror_club_df)} horror club movies for watch order")

# Connect to new database
db_path = project_root / 'data' / 'horror_recommender_v2.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print(f"3. Connected to database: {db_path}")

# Statistics
inserted_count = 0
club_watch_count = 0
skipped_no_tmdb = 0
error_count = 0

print(f"\n4. Inserting movies into horror_movies table...")

for idx, row in tqdm(df.iterrows(), total=len(df), desc="Inserting"):
    tmdb_id = row.get('tmdb_id')
    imdb_id = row.get('imdb_id')
    letterboxd_id = row.get('letterboxd_id')
    title = row.get('title')
    year = row.get('year')
    is_true_horror = row.get('is_true_horror')

    # Skip movies without TMDB ID (can't insert without primary key)
    if pd.isna(tmdb_id):
        skipped_no_tmdb += 1
        continue

    # Convert year to int if possible
    year_int = None
    if pd.notna(year):
        try:
            year_int = int(year)
        except (ValueError, TypeError):
            pass

    # Determine data_source
    # If this movie is in horror club lookup, mark as horror_club
    # Otherwise, it's from letterboxd_coreviews
    is_club_movie = letterboxd_id in club_lookup if pd.notna(letterboxd_id) else False
    data_source = 'horror_club' if is_club_movie else 'letterboxd_coreviews'

    # Get metadata fields
    director = row.get('directors', '')
    genres = row.get('genres', '')
    cast = row.get('cast', '')
    synopsis = row.get('synopsis', '')
    rating = row.get('rating')
    poster_url = row.get('poster_url', '')

    try:
        # Insert into horror_movies
        cursor.execute("""
            INSERT OR IGNORE INTO horror_movies (
                tmdb_id, imdb_id, letterboxd_id, title, year,
                director, genres, "cast", synopsis, rating, poster_url,
                data_source, is_true_horror
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            int(tmdb_id), imdb_id, letterboxd_id, title, year_int,
            director, genres, cast, synopsis, rating, poster_url,
            data_source, is_true_horror
        ))

        if cursor.rowcount > 0:
            inserted_count += 1
            movie_id = cursor.lastrowid

            # If this is a horror club movie, also insert into horror_club_watches
            if is_club_movie:
                list_entry_id = club_lookup[letterboxd_id]
                cursor.execute("""
                    INSERT OR IGNORE INTO horror_club_watches (
                        movie_id, list_entry_id
                    ) VALUES (?, ?)
                """, (movie_id, list_entry_id))

                if cursor.rowcount > 0:
                    club_watch_count += 1

    except Exception as e:
        error_count += 1
        tqdm.write(f"  ❌ Error inserting {title}: {e}")
        continue

# Commit all changes
conn.commit()

print("\n" + "=" * 70)
print("DATABASE INSERTION COMPLETE")
print("=" * 70)
print(f"Movies inserted:        {inserted_count:,}")
print(f"Skipped (no TMDB ID):   {skipped_no_tmdb:,}")
print(f"Errors:                 {error_count:,}")
print(f"Horror club watches:    {club_watch_count:,}")

# Verify database contents
cursor.execute("SELECT COUNT(*) FROM horror_movies")
total_movies = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM horror_movies WHERE data_source = 'horror_club'")
club_movies = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM horror_movies WHERE data_source = 'letterboxd_coreviews'")
letterboxd_movies = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM horror_movies WHERE is_true_horror = 1")
true_horror = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM horror_movies WHERE is_true_horror = 0")
false_horror = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM horror_club_watches")
total_watches = cursor.fetchone()[0]

print(f"\n" + "=" * 70)
print("DATABASE VERIFICATION")
print("=" * 70)
print(f"Total movies in database:       {total_movies:,}")
print(f"  - Horror club source:         {club_movies:,}")
print(f"  - Letterboxd coreviews:       {letterboxd_movies:,}")
print(f"\nBy horror classification:")
print(f"  - True horror (Horror genre): {true_horror:,}")
print(f"  - Non-horror club movies:     {false_horror:,}")
print(f"\nHorror club watches recorded:   {total_watches:,}")

# Show sample of inserted movies
print(f"\n" + "=" * 70)
print("SAMPLE OF INSERTED MOVIES")
print("=" * 70)

cursor.execute("""
    SELECT title, year, data_source, is_true_horror, tmdb_id
    FROM horror_movies
    WHERE data_source = 'horror_club'
    LIMIT 10
""")
print("\nHorror club movies (sample):")
for row in cursor.fetchall():
    title, year, source, is_horror, tmdb = row
    horror_flag = "✓" if is_horror else "✗"
    print(f"  {horror_flag} {title:45s} ({year}) - TMDB: {tmdb}")

cursor.execute("""
    SELECT title, year, data_source, is_true_horror, tmdb_id
    FROM horror_movies
    WHERE data_source = 'letterboxd_coreviews'
    LIMIT 10
""")
print("\nLetterboxd coreviews (sample):")
for row in cursor.fetchall():
    title, year, source, is_horror, tmdb = row
    horror_flag = "✓" if is_horror else "✗"
    print(f"  {horror_flag} {title:45s} ({year}) - TMDB: {tmdb}")

conn.close()

print("\n" + "=" * 70)
print("NEXT STEPS")
print("=" * 70)
print("""
1. Populate letterboxd_reviews table for collaborative filtering
2. Update recommender to query new schema
3. Test recommendations with expanded universe
4. Update web app to use new database
""")
