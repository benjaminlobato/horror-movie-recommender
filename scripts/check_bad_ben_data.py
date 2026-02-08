"""
Check Bad Ben review data
"""
import pandas as pd
import json
from pathlib import Path

project_root = Path(__file__).parent.parent

# Check extracted reviews
print("=" * 70)
print("BAD BEN IN EXTRACTED DATA")
print("=" * 70)

df = pd.read_parquet(project_root / 'data' / 'user_overlap' / 'user_movie_reviews.parquet')
bad_ben = df[df['movie_title'] == 'bad ben']

print(f'\nTotal reviews extracted: {len(bad_ben)}')
print(f'Unique users: {bad_ben["username"].nunique()}')
print('\nUsers who reviewed Bad Ben:')
for user in bad_ben['username'].unique():
    print(f'  - {user}')

# Check original JSONL
print("\n" + "=" * 70)
print("BAD BEN IN ORIGINAL LETTERBOXD DATASET")
print("=" * 70)

letterboxd_file = project_root / 'data' / 'letterboxd' / 'letterboxd_full.jsonl'

found = False
with open(letterboxd_file, 'r') as f:
    for line in f:
        movie = json.loads(line)
        title = movie.get('title', '').lower()

        if 'bad ben' == title.strip():
            found = True
            print(f"\nFound: {movie['title']} ({movie.get('year')})")
            print(f"  Total reviews in Letterboxd dataset: {len(movie.get('reviews', []))}")
            print(f"  Rating: {movie.get('rating')}")
            print(f"  URL: {movie.get('url')}")

            reviews = movie.get('reviews', [])
            if reviews:
                print(f"\n  Sample of usernames in dataset:")
                for i, review in enumerate(reviews[:10], 1):
                    username = review.get('username', 'N/A')
                    print(f"    {i}. {username}")

                if len(reviews) > 10:
                    print(f"    ... and {len(reviews) - 10} more")
            break

if not found:
    print("\nBad Ben not found in original dataset!")
    print("Searching for similar titles...")
    with open(letterboxd_file, 'r') as f:
        for line in f:
            movie = json.loads(line)
            if 'bad' in movie.get('title', '').lower() and 'ben' in movie.get('title', '').lower():
                print(f"  Found: {movie['title']} ({movie.get('year')})")
