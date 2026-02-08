"""
Phase 3b: Filter Universe Candidates by Genre
Use Letterboxd's genre data to filter for Horror/Thriller
Target: ~5,000 movies most-reviewed by horror fans
"""
import json
import pandas as pd
from pathlib import Path
from tqdm import tqdm

project_root = Path(__file__).parent.parent

print("=" * 70)
print("PHASE 3B: FILTERING BY GENRE")
print("=" * 70)

# Load candidates
candidates_path = project_root / 'data' / 'universe_candidates.csv'
candidates_df = pd.read_csv(candidates_path)

print(f"\n1. Loaded {len(candidates_df):,} candidate movies")

# Create lookup by letterboxd_id for fast matching
candidates_lookup = {
    row['letterboxd_id']: {
        'title': row['title'],
        'year': row['year'],
        'reviewer_count': row['reviewer_count'],
        'rating': row['rating']
    }
    for _, row in candidates_df.iterrows()
}

print(f"   Built lookup table with {len(candidates_lookup):,} entries")

# Scan Letterboxd dataset to get genres
print("\n2. Scanning Letterboxd dataset for genre information...")
letterboxd_file = project_root / 'data' / 'letterboxd' / 'letterboxd_full.jsonl'

# Count lines
print("   Counting lines...")
with open(letterboxd_file, 'r') as f:
    total_lines = sum(1 for _ in f)

# Extract genre information
genre_data = {}  # letterboxd_id -> {genres, directors, cast, synopsis}

print(f"   Processing {total_lines:,} movies...")
with open(letterboxd_file, 'r') as f:
    for line in tqdm(f, total=total_lines, desc="Extracting genres"):
        try:
            movie = json.loads(line)

            # Extract letterboxd_id from URL
            url = movie.get('url', '')
            if not url:
                continue

            letterboxd_id = url.split('/')[-2] if '/' in url else None

            # Check if this is one of our candidates
            if letterboxd_id and letterboxd_id in candidates_lookup:
                genre_data[letterboxd_id] = {
                    'genres': movie.get('genres', []),
                    'directors': movie.get('directors', []),
                    'cast': movie.get('cast', [])[:10],  # First 10 cast members
                    'synopsis': movie.get('synopsis', ''),
                    'poster_url': movie.get('poster_url', '')
                }

        except (json.JSONDecodeError, KeyError):
            continue

print(f"\n✓ Found genre data for {len(genre_data):,} candidates")

# Filter for Horror/Thriller
print("\n3. Filtering for Horror/Thriller genres...")

horror_movies = []

for letterboxd_id, candidate in candidates_lookup.items():
    # Get genre data
    genres_info = genre_data.get(letterboxd_id)

    if not genres_info:
        continue

    genres = genres_info['genres']
    if not isinstance(genres, list):
        continue

    # Check if Horror or Thriller in genres
    is_horror = any(
        genre.lower() in ['horror', 'thriller']
        for genre in genres
    )

    if is_horror:
        horror_movies.append({
            'letterboxd_id': letterboxd_id,
            'title': candidate['title'],
            'year': candidate['year'],
            'reviewer_count': candidate['reviewer_count'],
            'rating': candidate['rating'],
            'genres': ', '.join(genres),
            'directors': ', '.join(genres_info['directors']),
            'cast': ', '.join(genres_info['cast']),
            'synopsis': genres_info['synopsis'][:200] + '...' if len(genres_info['synopsis']) > 200 else genres_info['synopsis'],
            'poster_url': genres_info['poster_url']
        })

print(f"✓ Found {len(horror_movies):,} Horror/Thriller movies")

# Sort by reviewer_count (most-reviewed first)
horror_movies.sort(key=lambda x: x['reviewer_count'], reverse=True)

# Take top 5,000
target_count = 5000
filtered_movies = horror_movies[:target_count]

print(f"\n4. Taking top {target_count:,} most-reviewed by horror fans...")

# Save filtered list
output_path = project_root / 'data' / 'horror_universe_filtered.csv'
filtered_df = pd.DataFrame(filtered_movies)
filtered_df.to_csv(output_path, index=False)

print(f"✓ Saved to: {output_path}")

# Statistics
print("\n" + "=" * 70)
print("FILTERING COMPLETE")
print("=" * 70)
print(f"Original candidates:         {len(candidates_df):,}")
print(f"With genre data:             {len(genre_data):,}")
print(f"Horror/Thriller:             {len(horror_movies):,}")
print(f"Top selected:                {len(filtered_movies):,}")

# Reviewer count distribution
if filtered_movies:
    reviewer_counts = [m['reviewer_count'] for m in filtered_movies]
    print(f"\nReviewer count range:")
    print(f"  Min:  {min(reviewer_counts)} reviewers")
    print(f"  Max:  {max(reviewer_counts)} reviewers")
    print(f"  Median: {sorted(reviewer_counts)[len(reviewer_counts)//2]} reviewers")

# Top 20 most-reviewed
print(f"\nTop 20 most-reviewed horror movies by our fans:")
print(f"{'#':<4} {'Title':<45} {'Year':<6} {'Reviewers':<10} {'Genres':<30}")
print("-" * 100)

for i, movie in enumerate(filtered_movies[:20], 1):
    title = movie['title'][:44]
    year = str(movie['year']) if movie['year'] else 'N/A'
    reviewers = movie['reviewer_count']
    genres = movie['genres'][:29]
    print(f"{i:<4} {title:<45} {year:<6} {reviewers:<10} {genres:<30}")

# Genre breakdown
print("\n5. Genre breakdown (top genres):")
all_genres = []
for movie in filtered_movies:
    genres = movie['genres'].split(', ')
    all_genres.extend(genres)

from collections import Counter
genre_counts = Counter(all_genres)
for genre, count in genre_counts.most_common(10):
    print(f"  {genre:20s}: {count:,} movies")

print("\n" + "=" * 70)
print("NEXT STEPS")
print("=" * 70)
print("""
1. Match filtered movies to TMDB API for:
   - TMDB ID (primary key)
   - IMDb ID (cross-platform linking)
   - Additional metadata if needed

2. Insert into horror_movies table with data_source='letterboxd_coreviews'

3. Update recommender to use new universe (5,000+ movies!)
""")
