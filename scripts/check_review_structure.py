"""
Check what data is available in Letterboxd reviews
"""
import json
from pathlib import Path

project_root = Path(__file__).parent.parent
letterboxd_file = project_root / 'data' / 'letterboxd' / 'letterboxd_full.jsonl'

print("=" * 70)
print("LETTERBOXD REVIEW DATA STRUCTURE")
print("=" * 70)

# Find Bad Ben and examine its reviews
with open(letterboxd_file, 'r') as f:
    for line in f:
        movie = json.loads(line)
        if movie.get('title', '').lower().strip() == 'bad ben':
            print(f"\nMovie: {movie['title']} ({movie.get('year')})")
            print(f"Movie-level rating: {movie.get('rating')}")
            print(f"Total reviews: {len(movie.get('reviews', []))}")

            reviews = movie.get('reviews', [])
            if reviews:
                print(f"\n{'-' * 70}")
                print("SAMPLE REVIEWS:")
                print('-' * 70)

                for i, review in enumerate(reviews[:3], 1):
                    print(f"\nReview #{i}:")
                    print(f"  Keys available: {list(review.keys())}")
                    for key, value in review.items():
                        if isinstance(value, str) and len(value) > 100:
                            print(f"  {key}: {value[:100]}...")
                        else:
                            print(f"  {key}: {value}")

                print(f"\n{'-' * 70}")
                print("ALL REVIEWS WITH RATINGS:")
                print('-' * 70)
                for i, review in enumerate(reviews, 1):
                    username = review.get('username', 'Unknown')
                    rating = review.get('rating')
                    has_text = bool(review.get('text'))
                    print(f"{i}. {username:40s} Rating: {rating if rating else 'No rating':>10s}  Has text: {has_text}")

            break
