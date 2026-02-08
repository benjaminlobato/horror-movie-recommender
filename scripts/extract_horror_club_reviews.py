"""
Extract reviews for horror club movies from Letterboxd dataset
STREAMING approach - don't load entire 1.1GB file into memory
"""
import json
from pathlib import Path
import pandas as pd
from tqdm import tqdm
from collections import defaultdict

project_root = Path(__file__).parent.parent

print("=" * 70)
print("EXTRACTING HORROR CLUB REVIEWS (STREAMING)")
print("=" * 70)

# Load horror club movies
horror_club_path = project_root / 'data' / 'horror_club_with_ids.csv'
horror_club_df = pd.read_csv(horror_club_path)

# Create title-to-info mapping for fast lookup
horror_club_titles = {}
for _, row in horror_club_df.iterrows():
    title = row['title'].lower().strip() if pd.notna(row['title']) else None
    if title:
        horror_club_titles[title] = {
            'tmdb_id': row['tmdb_id'],
            'imdb_id': row['imdb_id'],
            'letterboxd_id': row['film_slug'],
            'original_title': row['title']
        }

print(f"Horror club movies: {len(horror_club_titles)}")

# Stream through Letterboxd dataset
letterboxd_file = project_root / 'data' / 'letterboxd' / 'letterboxd_full.jsonl'
print(f"Reading: {letterboxd_file}")
print(f"Size: {letterboxd_file.stat().st_size / (1024**3):.2f} GB\n")

# Store user-movie review data
user_reviews = defaultdict(set)  # user -> set of movie titles they reviewed
movie_reviewers = defaultdict(set)  # movie title -> set of users who reviewed it
movie_data = {}  # movie title -> movie info

found_count = 0
processed_lines = 0

print("Streaming through dataset (this will take a few minutes)...\n")

# Count total lines for progress bar
print("Counting total lines...")
with open(letterboxd_file, 'r', encoding='utf-8') as f:
    total_lines = sum(1 for _ in f)
print(f"Total movies in dataset: {total_lines:,}\n")

# Stream through file
with open(letterboxd_file, 'r', encoding='utf-8') as f:
    for line in tqdm(f, total=total_lines, desc="Processing"):
        processed_lines += 1

        try:
            movie = json.loads(line)

            # Get movie title
            movie_title = movie.get('title', '').lower().strip()

            # Check if this is a horror club movie
            if movie_title in horror_club_titles:
                found_count += 1

                # Store movie data
                movie_data[movie_title] = {
                    'title': movie.get('title'),
                    'year': movie.get('year'),
                    'url': movie.get('url'),
                    'rating': movie.get('rating'),
                    'review_count': len(movie.get('reviews', []))
                }

                # Extract reviewers
                reviews = movie.get('reviews', [])
                if isinstance(reviews, list):
                    for review in reviews:
                        if isinstance(review, dict):
                            username = review.get('username')
                            if username:
                                # Record this user reviewed this movie
                                user_reviews[username].add(movie_title)
                                movie_reviewers[movie_title].add(username)

                if found_count % 10 == 0:
                    print(f"\n  Found {found_count}/286 horror club movies")
                    print(f"  Unique users so far: {len(user_reviews):,}")

        except json.JSONDecodeError:
            continue

print("\n" + "=" * 70)
print("EXTRACTION COMPLETE")
print("=" * 70)
print(f"Processed: {processed_lines:,} movies")
print(f"Found horror club movies: {found_count}/{len(horror_club_titles)}")
print(f"Unique users: {len(user_reviews):,}")
print(f"Total reviews extracted: {sum(len(users) for users in movie_reviewers.values()):,}")

# Save results
output_dir = project_root / 'data' / 'user_overlap'
output_dir.mkdir(exist_ok=True)

# Save user-movie matrix (sparse format)
print("\nSaving user-movie matrix...")
user_movie_data = []
for user, movies in user_reviews.items():
    for movie in movies:
        user_movie_data.append({
            'username': user,
            'movie_title': movie,
            'tmdb_id': horror_club_titles[movie]['tmdb_id']
        })

user_movie_df = pd.DataFrame(user_movie_data)
user_movie_path = output_dir / 'user_movie_reviews.parquet'
user_movie_df.to_parquet(user_movie_path, index=False)
print(f"✓ Saved: {user_movie_path}")
print(f"  Rows: {len(user_movie_df):,}")

# Save movie review counts
movie_stats = []
for movie_title, users in movie_reviewers.items():
    movie_stats.append({
        'movie_title': horror_club_titles[movie_title]['original_title'],
        'tmdb_id': horror_club_titles[movie_title]['tmdb_id'],
        'review_count': len(users),
        'letterboxd_rating': movie_data.get(movie_title, {}).get('rating')
    })

movie_stats_df = pd.DataFrame(movie_stats).sort_values('review_count', ascending=False)
movie_stats_path = output_dir / 'horror_club_review_stats.csv'
movie_stats_df.to_csv(movie_stats_path, index=False)
print(f"✓ Saved: {movie_stats_path}")

# Show top reviewed horror club movies
print("\nTop 10 most reviewed horror club movies:")
for idx, row in movie_stats_df.head(10).iterrows():
    print(f"  {row['movie_title']:40s} - {row['review_count']:,} reviews")

# Show sample users with most horror club reviews
user_horror_counts = [(user, len(movies)) for user, movies in user_reviews.items()]
user_horror_counts.sort(key=lambda x: x[1], reverse=True)

print("\nTop 10 users who reviewed most horror club movies:")
for user, count in user_horror_counts[:10]:
    print(f"  {user:30s} - {count} horror club movies reviewed")

print("\n" + "=" * 70)
print("Ready for collaborative filtering!")
print("=" * 70)
print("\nNext steps:")
print("1. For a movie like 'Bad Ben', find users who reviewed it")
print("2. Get all other horror club movies those users reviewed")
print("3. Filter with cosine similarity (keep only similar horror)")
print("4. Rank by user overlap count + similarity score")
