"""
Test hybrid recommender with multiple movies
"""
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent))

from hybrid_recommender_v2 import recommend_hybrid, movie_to_users

# Test movies
test_movies = [
    "the thing",
    "hereditary",
    "the blair witch project",
    "midsommar",
]

print("=" * 70)
print("TESTING HYBRID RECOMMENDER WITH MULTIPLE MOVIES")
print("=" * 70)

for test_movie in test_movies:
    # Find the movie (case-insensitive)
    movie_found = None
    for title in movie_to_users.keys():
        if test_movie in title.lower():
            movie_found = title
            break

    if not movie_found:
        print(f"\n\n❌ Movie '{test_movie}' not found\n")
        continue

    print(f"\n\n{'=' * 70}")
    print(f"RECOMMENDATIONS FOR: {movie_found.upper()}")
    print("=" * 70)

    results, error = recommend_hybrid(movie_found, top_n=10, min_content_similarity=0.15)

    if error:
        print(f"\n❌ Error: {error}")
    else:
        print(f"\n✓ Top 10 recommendations:\n")
        print(f"{'Rank':<5} {'Movie Title':<45} {'Users':<7} {'Content':<8} {'Hybrid':<8}")
        print("-" * 85)

        for i, (title, user_count, content_sim, hybrid_score, tmdb_id) in enumerate(results, 1):
            print(f"{i:<5} {title[:44]:<45} {user_count:<7} {content_sim:<8.3f} {hybrid_score:<8.3f}")
