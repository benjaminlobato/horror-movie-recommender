"""
Import existing data into database:
1. Horror club collection (258 movies) - mark as watched_by_club=TRUE
2. TMDB superset (1,871 movies) - with all metadata
"""
import json
import pandas as pd
import pickle
from pathlib import Path
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()

project_root = Path(__file__).parent.parent

# Get database URL from environment
db_url = os.getenv('DATABASE_URL')
if not db_url:
    print("❌ DATABASE_URL not found in .env")
    print("Run: python scripts/setup_database.py first")
    exit(1)

print("=" * 70)
print("IMPORTING EXISTING DATA")
print("=" * 70)

# Create database connection
engine = create_engine(db_url)

print("\n1. Loading existing data...")

# Load horror club collection
horror_club_path = project_root / 'data' / 'horror_club_collection.csv'
horror_club_df = pd.read_csv(horror_club_path, encoding='utf-8-sig')
print(f"   ✓ Horror club: {len(horror_club_df)} movies")

# Load TMDB metadata
metadata_path = project_root / 'data' / 'movies_metadata_raw.json'
with open(metadata_path, 'r') as f:
    tmdb_metadata = json.load(f)
print(f"   ✓ TMDB metadata: {len(tmdb_metadata)} movies")

print("\n2. Importing to database...")

imported_count = 0
club_count = 0

with engine.connect() as conn:
    for movie in tmdb_metadata:
        # Check if horror club watched this movie
        watched_by_club = horror_club_df['Title'].str.lower().str.contains(
            movie['title'].lower(), na=False, regex=False
        ).any()

        if watched_by_club:
            club_count += 1

        # Insert movie
        insert_sql = text("""
            INSERT INTO movies (
                title, year, overview,
                tmdb_id, genres, keywords,
                director, cast,
                tmdb_vote_count, tmdb_vote_average,
                budget, watched_by_club,
                data_source
            ) VALUES (
                :title, :year, :overview,
                :tmdb_id, :genres, :keywords,
                :director, :cast,
                :vote_count, :vote_average,
                :budget, :watched_by_club,
                'tmdb'
            )
            ON CONFLICT (tmdb_id) DO UPDATE SET
                title = EXCLUDED.title,
                year = EXCLUDED.year,
                overview = EXCLUDED.overview,
                genres = EXCLUDED.genres,
                keywords = EXCLUDED.keywords,
                director = EXCLUDED.director,
                cast = EXCLUDED.cast,
                tmdb_vote_count = EXCLUDED.tmdb_vote_count,
                tmdb_vote_average = EXCLUDED.tmdb_vote_average,
                budget = EXCLUDED.budget,
                watched_by_club = EXCLUDED.watched_by_club,
                updated_at = NOW()
        """)

        try:
            conn.execute(insert_sql, {
                'title': movie['title'],
                'year': int(movie['year']) if movie['year'] else None,
                'overview': movie['overview'],
                'tmdb_id': movie['tmdb_id'],
                'genres': json.dumps(movie['genres']),
                'keywords': json.dumps(movie['keywords']),
                'director': movie['director'][0] if movie['director'] else None,
                'cast': json.dumps(movie['cast']),
                'vote_count': movie['vote_count'],
                'vote_average': movie['vote_average'],
                'budget': movie['budget'],
                'watched_by_club': watched_by_club
            })
            imported_count += 1

            if imported_count % 100 == 0:
                print(f"   Imported {imported_count} movies...")

        except Exception as e:
            print(f"   ⚠️  Error importing {movie['title']}: {e}")
            continue

    conn.commit()

print(f"\n✓ Import complete!")
print(f"   Total movies: {imported_count}")
print(f"   Horror club movies: {club_count}")

# Verify
with engine.connect() as conn:
    result = conn.execute(text("SELECT COUNT(*) FROM movies")).fetchone()
    total = result[0]

    result = conn.execute(text("SELECT COUNT(*) FROM movies WHERE watched_by_club = TRUE")).fetchone()
    club_total = result[0]

    print(f"\nDatabase statistics:")
    print(f"   Total movies in DB: {total}")
    print(f"   Horror club movies: {club_total}")

print("\n" + "=" * 70)
print("✓ DATA IMPORT COMPLETE")
print("=" * 70)
