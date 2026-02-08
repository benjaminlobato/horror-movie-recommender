"""
Check what universe of movies can be recommended
"""
import pandas as pd
import sqlite3
from pathlib import Path

project_root = Path(__file__).parent.parent

print("=" * 70)
print("RECOMMENDATION UNIVERSE ANALYSIS")
print("=" * 70)

# Check database
db_path = project_root / 'data' / 'horror_recommender.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute('SELECT COUNT(*) FROM movies')
total_db = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(*) FROM movies WHERE watched_by_club = 1')
horror_club_db = cursor.fetchone()[0]

print("\n1. DATABASE (from TMDB keyword search):")
print(f"   Total movies: {total_db:,}")
print(f"   Horror club: {horror_club_db}")
print(f"   Other horror: {total_db - horror_club_db:,}")

# Check Letterboxd reviews
reviews_df = pd.read_parquet(project_root / 'data' / 'user_overlap' / 'user_movie_reviews.parquet')
movies_with_reviews = reviews_df['movie_title'].nunique()

print("\n2. LETTERBOXD REVIEWS:")
print(f"   Movies with reviews: {movies_with_reviews}")
print(f"   Unique users: {reviews_df['username'].nunique():,}")
print(f"   Total reviews: {len(reviews_df):,}")

# Current system
print("\n3. CURRENT SYSTEM:")
print(f"   Can GET recommendations for: 286 horror club movies")
print(f"   Can RECOMMEND from: 286 horror club movies ONLY")

# Check if any non-horror-club movies have reviews
cursor.execute('''
    SELECT title, tmdb_id
    FROM movies
    WHERE watched_by_club = 0
    LIMIT 20
''')
other_movies = cursor.fetchall()

print("\n4. POTENTIAL EXPANSION:")
print(f"   Could recommend from: {total_db:,} movies")
print(f"   Would add: {total_db - 286:,} more horror movies")
print()
print("   Sample of non-horror-club movies in database:")
for i, (title, tmdb_id) in enumerate(other_movies[:10], 1):
    print(f"     {i:2d}. {title}")

# Check if any of these have Letterboxd reviews
print("\n5. DO NON-HORROR-CLUB MOVIES HAVE REVIEWS?")
print("   Checking if broader dataset movies have Letterboxd reviews...")

# Get all movie titles from reviews (lowercase)
review_titles = set(reviews_df['movie_title'].str.lower().str.strip())

# Get non-horror-club movies
cursor.execute('SELECT title FROM movies WHERE watched_by_club = 0')
non_club_movies = [title.lower().strip() for title, in cursor.fetchall()]

# Check overlap
overlap = [title for title in non_club_movies if title in review_titles]

print(f"   Non-horror-club movies with reviews: {len(overlap)}")
if overlap:
    print("   Examples:")
    for title in overlap[:10]:
        print(f"     - {title}")

print("\n" + "=" * 70)
print("RECOMMENDATION")
print("=" * 70)
print("""
Current: Recommend FROM horror club movies (286) TO horror club movies (286)

Option 1 (Keep current):
  ✓ Curated quality
  ✓ All movies vetted by horror club
  ✗ Limited variety

Option 2 (Expand to 1,908 movies):
  ✓ Much more variety
  ✓ Can discover more obscure horror
  ✗ Quality not curated
  ✗ May recommend mainstream/non-horror

Hybrid approach:
  - Get recommendations FOR horror club movies (286)
  - Recommend FROM full database (1,908) using user overlap + cosine
  - User overlap ensures quality (users who like horror club movies)
""")

conn.close()
