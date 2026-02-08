"""
Hybrid Recommendation System
Combines collaborative filtering (user overlap) with content-based filtering (cosine similarity)

Strategy:
1. Find users who reviewed the target movie
2. Get all other horror club movies those users reviewed
3. Filter candidates using cosine similarity (remove non-horror like Lion King)
4. Rank by hybrid score: user_overlap_count * 0.7 + cosine_similarity * 0.3
"""
from pathlib import Path
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from collections import Counter

project_root = Path(__file__).parent.parent

print("=" * 70)
print("HYBRID HORROR RECOMMENDER")
print("=" * 70)

# Load user-movie review matrix
print("\n1. Loading user review data...")
user_reviews_path = project_root / 'data' / 'user_overlap' / 'user_movie_reviews.parquet'
user_reviews_df = pd.read_parquet(user_reviews_path)
print(f"✓ Loaded {len(user_reviews_df):,} reviews from {user_reviews_df['username'].nunique():,} users")

# Build lookup dictionaries for fast access
print("\n2. Building lookup structures...")
# user -> list of movie titles
user_to_movies = user_reviews_df.groupby('username')['movie_title'].apply(list).to_dict()

# movie -> list of users
movie_to_users = user_reviews_df.groupby('movie_title')['username'].apply(list).to_dict()

# movie title -> tmdb_id
movie_title_to_tmdb = user_reviews_df.drop_duplicates('movie_title').set_index('movie_title')['tmdb_id'].to_dict()
tmdb_to_title = {v: k for k, v in movie_title_to_tmdb.items()}

print(f"✓ Indexed {len(movie_to_users)} movies")
print(f"✓ Indexed {len(user_to_movies)} users")

# Load pre-computed similarity matrix from database
print("\n3. Loading pre-computed similarity matrix...")
db_path = project_root / 'data' / 'horror_recommender.db'
engine = create_engine(f'sqlite:///{db_path}')

# Load similarity cache for horror club movies
query = text("""
    SELECT
        s.movie_id_1,
        s.movie_id_2,
        s.content_similarity,
        m1.tmdb_id as tmdb_id_1,
        m2.tmdb_id as tmdb_id_2
    FROM similarity_cache s
    JOIN movies m1 ON s.movie_id_1 = m1.id
    JOIN movies m2 ON s.movie_id_2 = m2.id
    WHERE m1.watched_by_club = 1 AND m2.watched_by_club = 1
""")

with engine.connect() as conn:
    similarity_df = pd.read_sql(query, conn)

print(f"✓ Loaded {len(similarity_df):,} similarity pairs")

# Build similarity lookup: (tmdb_id_1, tmdb_id_2) -> similarity
similarity_cache = {}
for _, row in similarity_df.iterrows():
    key1 = (row['tmdb_id_1'], row['tmdb_id_2'])
    key2 = (row['tmdb_id_2'], row['tmdb_id_1'])  # Symmetric
    similarity_cache[key1] = row['content_similarity']
    similarity_cache[key2] = row['content_similarity']

print(f"✓ Built similarity lookup with {len(similarity_cache):,} entries")

def get_similarity(tmdb_id_1, tmdb_id_2):
    """Get pre-computed similarity between two movies"""
    if tmdb_id_1 == tmdb_id_2:
        return 1.0
    return similarity_cache.get((tmdb_id_1, tmdb_id_2), 0.0)


def recommend_hybrid(movie_title, top_n=10, min_content_similarity=0.2, user_weight=0.7, similarity_weight=0.3):
    """
    Hybrid recommendation combining user overlap and content similarity

    Args:
        movie_title: Target movie title (lowercase)
        top_n: Number of recommendations to return
        min_content_similarity: Minimum content similarity threshold (filter)
        user_weight: Weight for user overlap score
        similarity_weight: Weight for content similarity score

    Returns:
        List of (movie_title, user_count, content_sim, hybrid_score, tmdb_id)
    """

    # Normalize input
    movie_title = movie_title.lower().strip()

    # Check if movie exists in our data
    if movie_title not in movie_to_users:
        return None, f"Movie '{movie_title}' not found in review data"

    if movie_title not in movie_title_to_tmdb:
        return None, f"Movie '{movie_title}' not found in TMDB mapping"

    # Get TMDB ID for target movie
    target_tmdb_id = movie_title_to_tmdb[movie_title]

    # Step 1: Find users who reviewed this movie
    users_who_reviewed = set(movie_to_users[movie_title])

    # Step 2: Get all other movies those users reviewed
    candidate_movies = Counter()
    for user in users_who_reviewed:
        for other_movie in user_to_movies[user]:
            if other_movie != movie_title:  # Don't recommend the same movie
                candidate_movies[other_movie] += 1

    # Step 3: Calculate hybrid scores
    recommendations = []

    for candidate_title, user_count in candidate_movies.items():
        # Get candidate's TMDB ID
        candidate_tmdb_id = movie_title_to_tmdb.get(candidate_title)
        if not candidate_tmdb_id:
            continue

        # Get pre-computed content similarity
        content_sim = get_similarity(target_tmdb_id, candidate_tmdb_id)

        # Filter: only keep candidates with sufficient similarity (horror-like)
        if content_sim < min_content_similarity:
            continue

        # Normalize user count (scale to 0-1 range for fair weighting)
        # Max possible is number of users who reviewed target movie
        normalized_user_count = user_count / len(users_who_reviewed)

        # Hybrid score
        hybrid_score = (normalized_user_count * user_weight) + (content_sim * similarity_weight)

        recommendations.append((
            candidate_title,
            user_count,
            content_sim,
            hybrid_score,
            candidate_tmdb_id
        ))

    # Sort by hybrid score (descending)
    recommendations.sort(key=lambda x: x[3], reverse=True)

    return recommendations[:top_n], None


# Test with Bad Ben
print("\n" + "=" * 70)
print("TESTING WITH 'BAD BEN'")
print("=" * 70)

test_movie = "bad ben"
print(f"\nGetting recommendations for: {test_movie}")

# Check if movie exists in lowercase
if test_movie not in movie_to_users:
    # Try to find it case-insensitive
    for title in movie_to_users.keys():
        if test_movie in title.lower():
            print(f"Found as: '{title}'")
            test_movie = title
            break

results, error = recommend_hybrid(test_movie, top_n=15)

if error:
    print(f"\n❌ Error: {error}")
else:
    print(f"\n✓ Found {len(results)} recommendations\n")
    print(f"{'Rank':<5} {'Movie Title':<45} {'Users':<7} {'Content':<8} {'Hybrid':<8} {'TMDB ID':<10}")
    print("-" * 95)

    for i, (title, user_count, content_sim, hybrid_score, tmdb_id) in enumerate(results, 1):
        print(f"{i:<5} {title[:44]:<45} {user_count:<7} {content_sim:<8.3f} {hybrid_score:<8.3f} {tmdb_id:<10}")

print("\n" + "=" * 70)
print("READY FOR PRODUCTION")
print("=" * 70)
print("\nUsage:")
print("  from hybrid_recommender import recommend_hybrid")
print("  results, error = recommend_hybrid('bad ben', top_n=10)")
