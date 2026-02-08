"""
Demo: Hybrid Recommender in Action
Shows recommendations for various types of horror movies
"""
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent))

from hybrid_recommender_v2 import recommend_hybrid

# Test movies representing different horror subgenres
test_movies = [
    ("bad ben", "Obscure found footage"),
    ("the thing", "Classic sci-fi horror"),
    ("blair witch", "Found footage classic"),
    ("midsommar", "Folk horror"),
    ("us", "Modern psychological horror"),
]

print("=" * 80)
print(" " * 20 + "HYBRID HORROR RECOMMENDER DEMO")
print("=" * 80)
print("\nCombining collaborative filtering (user overlap) with content similarity")
print("Weights: 70% user overlap + 30% content similarity\n")

for movie_title, subgenre in test_movies:
    print("\n" + "=" * 80)
    print(f"INPUT: '{movie_title.upper()}' ({subgenre})")
    print("=" * 80)

    results, error = recommend_hybrid(movie_title, top_n=10, min_content_similarity=0.1)

    if error:
        print(f"\n❌ {error}")
        continue

    if not results:
        print("\n⚠️  No recommendations found (try lowering min_content_similarity)")
        continue

    print(f"\nTOP {len(results)} RECOMMENDATIONS:\n")
    print(f"{'#':<3} {'Title':<50} {'Users':<6} {'Content':<8} {'Score':<6}")
    print("-" * 80)

    for i, (title, user_count, content_sim, hybrid_score, tmdb_id) in enumerate(results, 1):
        print(f"{i:<3} {title[:49]:<50} {user_count:<6} {content_sim:<8.3f} {hybrid_score:<6.3f}")

print("\n" + "=" * 80)
print("ANALYSIS")
print("=" * 80)
print("""
Key Insights:
1. User overlap finds movies that actual horror fans loved
2. Content similarity filters out non-horror (e.g., prevents Lion King recommendations)
3. Hybrid scoring balances popularity (user count) with relevance (content match)
4. Results include hidden gems and indie horror that pure content-based would miss

Why this works better than pure cosine similarity:
- Cosine similarity: "Bad Ben" → "Oppenheimer" (both have "dramatic" keywords)
- Hybrid recommender: "Bad Ben" → "WNUF Halloween Special" (horror fans who loved one loved the other)
""")
