"""
Phase 3: Expand Universe via Letterboxd Co-Reviews
Find all movies reviewed by users who reviewed horror club movies
Filter for horror/thriller genres, match to TMDB
Target: ~5,000 horror movies in the universe
"""
import json
import sqlite3
import pandas as pd
from pathlib import Path
from tqdm import tqdm
from collections import Counter

project_root = Path(__file__).parent.parent

print("=" * 70)
print("PHASE 3: EXPANDING UNIVERSE VIA LETTERBOXD")
print("=" * 70)

# Load our horror club reviewers
print("\n1. Loading horror club reviewers...")
user_reviews_df = pd.read_parquet(project_root / 'data' / 'user_overlap' / 'user_movie_reviews.parquet')
horror_reviewers = set(user_reviews_df['username'].unique())
print(f"✓ Found {len(horror_reviewers):,} users who reviewed horror club movies")

# Stream through Letterboxd dataset
letterboxd_file = project_root / 'data' / 'letterboxd' / 'letterboxd_full.jsonl'
print(f"\n2. Streaming through Letterboxd dataset...")
print(f"   Looking for movies reviewed by our {len(horror_reviewers):,} users")

# Count lines for progress
print("   Counting total lines...")
with open(letterboxd_file, 'r') as f:
    total_lines = sum(1 for _ in f)
print(f"   Total movies to scan: {total_lines:,}")

# Collect candidate movies
movie_candidates = {}  # letterboxd_id -> {title, year, url, reviewer_count}
processed = 0

print("\n3. Extracting movies...")
with open(letterboxd_file, 'r') as f:
    for line in tqdm(f, total=total_lines, desc="Processing"):
        processed += 1

        try:
            movie = json.loads(line)

            # Check if any of our horror reviewers reviewed this movie
            reviews = movie.get('reviews', [])
            if not isinstance(reviews, list):
                continue

            reviewer_count = 0
            for review in reviews:
                if isinstance(review, dict):
                    username = review.get('username')
                    if username in horror_reviewers:
                        reviewer_count += 1

            # If at least one horror reviewer reviewed it, it's a candidate
            if reviewer_count > 0:
                letterboxd_id = movie.get('url', '').split('/')[-2] if movie.get('url') else None

                if letterboxd_id:
                    movie_candidates[letterboxd_id] = {
                        'title': movie.get('title', '').strip(),
                        'year': movie.get('year'),
                        'letterboxd_url': movie.get('url'),
                        'reviewer_count': reviewer_count,
                        'rating': movie.get('rating')
                    }

        except (json.JSONDecodeError, KeyError):
            continue

print(f"\n✓ Found {len(movie_candidates):,} movies reviewed by horror fans")

# Sort by reviewer count (most reviewed = most relevant)
sorted_candidates = sorted(
    movie_candidates.items(),
    key=lambda x: x[1]['reviewer_count'],
    reverse=True
)

print("\n4. Top 20 most-reviewed movies by horror fans:")
for i, (lb_id, data) in enumerate(sorted_candidates[:20], 1):
    print(f"   {i:2d}. {data['title']:40s} ({data['year']}) - {data['reviewer_count']} reviewers")

# Now we need to match these to TMDB to get IDs and genres
print("\n5. Matching to TMDB for genre filtering...")
print("   This requires TMDB API calls - will implement in next phase")

# For now, save the candidates for manual review
candidates_df = pd.DataFrame([
    {
        'letterboxd_id': lb_id,
        'title': data['title'],
        'year': data['year'],
        'letterboxd_url': data['letterboxd_url'],
        'reviewer_count': data['reviewer_count'],
        'rating': data['rating']
    }
    for lb_id, data in sorted_candidates
])

output_path = project_root / 'data' / 'universe_candidates.csv'
candidates_df.to_csv(output_path, index=False)

print(f"\n✓ Saved {len(candidates_df):,} candidates to: {output_path}")

# Statistics
print("\n" + "=" * 70)
print("EXTRACTION COMPLETE")
print("=" * 70)
print(f"Total movies scanned: {processed:,}")
print(f"Movies reviewed by horror fans: {len(movie_candidates):,}")
print(f"")
print(f"Breakdown by reviewer count:")
counter = Counter([data['reviewer_count'] for data in movie_candidates.values()])
for count in sorted(counter.keys(), reverse=True)[:10]:
    print(f"  {count:3d} reviewers: {counter[count]:,} movies")

print("\n" + "=" * 70)
print("NEXT STEPS")
print("=" * 70)
print("""
1. Match candidates to TMDB API to get:
   - TMDB IDs
   - IMDb IDs
   - Genres (filter for horror/thriller)
   - Director, cast, keywords

2. Filter for horror/thriller genres (target ~5,000 movies)

3. Insert into horror_movies table with data_source='letterboxd_coreviews'

This will give us a ~5,000 movie universe curated by actual horror fan behavior!
""")
