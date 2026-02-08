"""
Phase 6: Populate letterboxd_reviews table for collaborative filtering
Extract user reviews from Letterboxd dataset for movies in our universe
"""
import json
import sqlite3
from pathlib import Path
from tqdm import tqdm

project_root = Path(__file__).parent.parent

print("=" * 70)
print("PHASE 6: POPULATING LETTERBOXD REVIEWS")
print("=" * 70)

# Connect to database
db_path = project_root / 'data' / 'horror_recommender_v2.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print(f"\n1. Connected to database: {db_path}")

# Get all letterboxd_ids from horror_movies table
cursor.execute("""
    SELECT letterboxd_id, id, title
    FROM horror_movies
    WHERE letterboxd_id IS NOT NULL
""")
movies_in_universe = cursor.fetchall()

# Create lookup: letterboxd_id -> movie_id
lb_to_movie_id = {}
for lb_id, movie_id, title in movies_in_universe:
    lb_to_movie_id[lb_id] = (movie_id, title)

print(f"2. Found {len(lb_to_movie_id):,} movies with Letterboxd IDs in universe")

# Load horror fans (users who reviewed horror club movies)
user_reviews_path = project_root / 'data' / 'user_overlap' / 'user_movie_reviews.parquet'
import pandas as pd
user_reviews_df = pd.read_parquet(user_reviews_path)
horror_fans = set(user_reviews_df['username'].unique())

print(f"3. Found {len(horror_fans):,} horror fans to track")

# Scan Letterboxd dataset for reviews
letterboxd_file = project_root / 'data' / 'letterboxd' / 'letterboxd_full.jsonl'

print(f"\n4. Scanning Letterboxd dataset for reviews...")

# Count lines for progress bar
with open(letterboxd_file, 'r') as f:
    total_lines = sum(1 for _ in f)

reviews_inserted = 0
movies_with_reviews = 0
batch_size = 1000
batch = []

with open(letterboxd_file, 'r') as f:
    for line in tqdm(f, total=total_lines, desc="Processing"):
        try:
            movie = json.loads(line)
            url = movie.get('url', '')
            if not url:
                continue

            # Extract letterboxd ID from URL
            lb_id = url.split('/')[-2] if '/' in url else None

            # Check if this movie is in our universe
            if lb_id not in lb_to_movie_id:
                continue

            movie_id, title = lb_to_movie_id[lb_id]

            # Process reviews
            reviews = movie.get('reviews', [])
            if not isinstance(reviews, list):
                continue

            movie_has_reviews = False
            for review in reviews:
                if not isinstance(review, dict):
                    continue

                username = review.get('username')
                if not username:
                    continue

                # Only track reviews from horror fans
                if username not in horror_fans:
                    continue

                # Add to batch
                batch.append((
                    movie_id,
                    username,
                    review.get('review_text', '')[:500],  # Truncate long reviews
                    review.get('likes', 0)
                ))

                movie_has_reviews = True

            if movie_has_reviews:
                movies_with_reviews += 1

            # Insert batch when it reaches batch_size
            if len(batch) >= batch_size:
                cursor.executemany("""
                    INSERT OR IGNORE INTO letterboxd_reviews (
                        movie_id, username, review_text, likes
                    ) VALUES (?, ?, ?, ?)
                """, batch)
                reviews_inserted += len(batch)
                batch = []
                conn.commit()

        except (json.JSONDecodeError, KeyError) as e:
            continue

# Insert remaining batch
if batch:
    cursor.executemany("""
        INSERT OR IGNORE INTO letterboxd_reviews (
            movie_id, username, review_text, likes
        ) VALUES (?, ?, ?, ?)
    """, batch)
    reviews_inserted += len(batch)
    conn.commit()

print("\n" + "=" * 70)
print("REVIEWS POPULATION COMPLETE")
print("=" * 70)
print(f"Total reviews inserted:     {reviews_inserted:,}")
print(f"Movies with reviews:        {movies_with_reviews:,}")
print(f"Movies in universe:         {len(lb_to_movie_id):,}")
print(f"Coverage:                   {movies_with_reviews/len(lb_to_movie_id)*100:.1f}%")

# Verify database contents
cursor.execute("SELECT COUNT(*) FROM letterboxd_reviews")
total_reviews = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(DISTINCT movie_id) FROM letterboxd_reviews")
distinct_movies = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(DISTINCT username) FROM letterboxd_reviews")
distinct_users = cursor.fetchone()[0]

print(f"\n" + "=" * 70)
print("DATABASE VERIFICATION")
print("=" * 70)
print(f"Total reviews in database:  {total_reviews:,}")
print(f"Distinct movies reviewed:   {distinct_movies:,}")
print(f"Distinct users (fans):      {distinct_users:,}")

# Show top reviewed movies
cursor.execute("""
    SELECT m.title, m.year, COUNT(*) as review_count
    FROM letterboxd_reviews r
    JOIN horror_movies m ON r.movie_id = m.id
    GROUP BY r.movie_id
    ORDER BY review_count DESC
    LIMIT 20
""")

print(f"\n" + "=" * 70)
print("TOP 20 REVIEWED MOVIES (by horror fans)")
print("=" * 70)
for title, year, count in cursor.fetchall():
    year_str = f"({year})" if year else ""
    print(f"  {title:50s} {year_str:6s} - {count:,} reviews")

# Show most active reviewers
cursor.execute("""
    SELECT username, COUNT(*) as review_count
    FROM letterboxd_reviews
    GROUP BY username
    ORDER BY review_count DESC
    LIMIT 10
""")

print(f"\n" + "=" * 70)
print("TOP 10 MOST ACTIVE HORROR FANS")
print("=" * 70)
for username, count in cursor.fetchall():
    print(f"  {username:30s} - {count:,} reviews")

conn.close()

print("\n" + "=" * 70)
print("NEXT STEPS")
print("=" * 70)
print("""
1. Update recommender to query new schema (horror_movies + letterboxd_reviews)
2. Test recommendations with expanded universe
3. Update web app to use new database
4. Verify recommendation quality with test cases
""")
