"""
Mark which movies the horror club has watched
"""
import pandas as pd
from sqlalchemy import create_engine, text
import os
from pathlib import Path
from dotenv import load_dotenv
from fuzzywuzzy import fuzz

load_dotenv()

project_root = Path(__file__).parent.parent

# Load horror club collection
horror_club_df = pd.read_csv(project_root / 'data' / 'horror_club_collection.csv', encoding='utf-8-sig')
print(f"Horror club collection: {len(horror_club_df)} movies")

# Connect to database
engine = create_engine(os.getenv('DATABASE_URL'))

# Get all movies from database
with engine.connect() as conn:
    result = conn.execute(text('SELECT id, title, year FROM movies')).fetchall()
    db_movies = [(row[0], row[1], row[2]) for row in result]

print(f"Database movies: {len(db_movies)}")

# Match horror club movies to database
matches = []
for _, club_row in horror_club_df.iterrows():
    club_title = club_row['Title'].strip()

    # Try exact match first
    exact_matches = [(id, title, year) for id, title, year in db_movies if title.lower() == club_title.lower()]

    if exact_matches:
        matches.append((exact_matches[0][0], club_title, exact_matches[0][1]))
    else:
        # Try fuzzy match
        best_match = None
        best_score = 0

        for id, db_title, year in db_movies:
            score = fuzz.ratio(club_title.lower(), db_title.lower())
            if score > best_score and score >= 85:  # 85% similarity threshold
                best_score = score
                best_match = (id, club_title, db_title, score)

        if best_match:
            matches.append((best_match[0], best_match[1], best_match[2]))
            if best_match[3] < 100:
                print(f"  Fuzzy match ({best_match[3]}%): '{best_match[1]}' -> '{best_match[2]}'")

print(f"\nMatched {len(matches)} horror club movies to database")

# Update database
with engine.connect() as conn:
    for movie_id, club_title, db_title in matches:
        conn.execute(
            text('UPDATE movies SET watched_by_club = 1 WHERE id = :id'),
            {'id': movie_id}
        )
    conn.commit()

print(f"✓ Updated {len(matches)} movies with watched_by_club flag")

# Verify
with engine.connect() as conn:
    result = conn.execute(text('SELECT COUNT(*) FROM movies WHERE watched_by_club = 1')).fetchone()
    print(f"✓ Total horror club movies in DB: {result[0]}")
