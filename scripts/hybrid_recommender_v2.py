"""
Hybrid Recommendation System (On-the-fly similarity computation)
Combines collaborative filtering (user overlap) with content-based filtering

Strategy:
1. Find users who reviewed the target movie
2. Get all other horror club movies those users reviewed
3. Compute content similarity on-the-fly for candidate movies
4. Filter candidates using content similarity threshold
5. Rank by hybrid score: user_overlap_count * 0.7 + content_similarity * 0.3
"""
from pathlib import Path
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

project_root = Path(__file__).parent.parent

print("=" * 70)
print("HYBRID HORROR RECOMMENDER (v2)")
print("=" * 70)

# Load user-movie review matrix
print("\n1. Loading user review data...")
user_reviews_path = project_root / 'data' / 'user_overlap' / 'user_movie_reviews.parquet'
user_reviews_df = pd.read_parquet(user_reviews_path)
print(f"✓ Loaded {len(user_reviews_df):,} reviews from {user_reviews_df['username'].nunique():,} users")

# Build lookup dictionaries
print("\n2. Building lookup structures...")
user_to_movies = user_reviews_df.groupby('username')['movie_title'].apply(list).to_dict()
movie_to_users = user_reviews_df.groupby('movie_title')['username'].apply(list).to_dict()
movie_title_to_tmdb = user_reviews_df.drop_duplicates('movie_title').set_index('movie_title')['tmdb_id'].to_dict()

print(f"✓ Indexed {len(movie_to_users)} movies")
print(f"✓ Indexed {len(user_to_movies)} users")

# Load movie metadata from database
print("\n3. Loading movie metadata...")
db_path = project_root / 'data' / 'horror_recommender.db'
engine = create_engine(f'sqlite:///{db_path}')

query = text("""
    SELECT tmdb_id, title, genres, keywords, "cast", director
    FROM movies
    WHERE watched_by_club = 1
""")

with engine.connect() as conn:
    movies_metadata = pd.read_sql(query, conn)

print(f"✓ Loaded metadata for {len(movies_metadata)} horror club movies")

# Build metadata lookup
tmdb_to_metadata = movies_metadata.set_index('tmdb_id').to_dict('index')

def build_content_string(tmdb_id):
    """Build a text string from movie metadata for TF-IDF"""
    metadata = tmdb_to_metadata.get(tmdb_id, {})

    parts = []

    # Genres (high weight - repeat 3x)
    genres = metadata.get('genres', '')
    if genres:
        parts.extend([genres] * 3)

    # Keywords (medium weight - repeat 2x)
    keywords = metadata.get('keywords', '')
    if keywords:
        parts.extend([keywords] * 2)

    # Director (medium weight - repeat 2x)
    director = metadata.get('director', '')
    if director:
        parts.extend([director] * 2)

    # Cast (low weight - once)
    cast = metadata.get('cast', '')
    if cast:
        parts.append(cast)

    return ' '.join(parts)


def compute_content_similarity(target_tmdb_id, candidate_tmdb_ids):
    """
    Compute content similarity between target and multiple candidates
    Returns dict: candidate_tmdb_id -> similarity_score
    """
    # Build content strings
    target_content = build_content_string(target_tmdb_id)
    candidate_contents = [build_content_string(cid) for cid in candidate_tmdb_ids]

    # Combine all texts
    all_texts = [target_content] + candidate_contents

    # TF-IDF vectorization
    vectorizer = TfidfVectorizer(lowercase=True, stop_words='english')
    try:
        tfidf_matrix = vectorizer.fit_transform(all_texts)
    except ValueError:
        # No valid text
        return {cid: 0.0 for cid in candidate_tmdb_ids}

    # Compute cosine similarity
    target_vector = tfidf_matrix[0:1]
    candidate_vectors = tfidf_matrix[1:]
    similarities = cosine_similarity(target_vector, candidate_vectors)[0]

    # Map back to TMDB IDs
    return {cid: sim for cid, sim in zip(candidate_tmdb_ids, similarities)}


def recommend_hybrid(movie_title, top_n=10, min_content_similarity=0.1, user_weight=0.7, similarity_weight=0.3):
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

    # Check if movie exists
    if movie_title not in movie_to_users:
        return None, f"Movie '{movie_title}' not found in review data"

    if movie_title not in movie_title_to_tmdb:
        return None, f"Movie '{movie_title}' not found in TMDB mapping"

    target_tmdb_id = movie_title_to_tmdb[movie_title]

    # Step 1: Find users who reviewed this movie
    users_who_reviewed = set(movie_to_users[movie_title])
    print(f"\n  → {len(users_who_reviewed)} users reviewed '{movie_title}'")

    # Step 2: Get all other movies those users reviewed
    candidate_movies = Counter()
    for user in users_who_reviewed:
        for other_movie in user_to_movies[user]:
            if other_movie != movie_title:
                candidate_movies[other_movie] += 1

    print(f"  → {len(candidate_movies)} candidate movies from user overlap")

    # Step 3: Compute content similarities for all candidates
    candidate_tmdb_ids = [movie_title_to_tmdb[title] for title in candidate_movies.keys()
                          if title in movie_title_to_tmdb]

    similarities = compute_content_similarity(target_tmdb_id, candidate_tmdb_ids)

    # Step 4: Calculate hybrid scores
    recommendations = []

    for candidate_title, user_count in candidate_movies.items():
        candidate_tmdb_id = movie_title_to_tmdb.get(candidate_title)
        if not candidate_tmdb_id:
            continue

        content_sim = similarities.get(candidate_tmdb_id, 0.0)

        # Filter: only keep candidates with sufficient similarity
        if content_sim < min_content_similarity:
            continue

        # Normalize user count
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

    print(f"  → {len(recommendations)} movies passed content similarity filter (>{min_content_similarity})")

    # Sort by hybrid score
    recommendations.sort(key=lambda x: x[3], reverse=True)

    return recommendations[:top_n], None


# Test with Bad Ben
print("\n" + "=" * 70)
print("TESTING WITH 'BAD BEN'")
print("=" * 70)

test_movie = "bad ben"

# Try to find the movie (case-insensitive)
movie_found = None
for title in movie_to_users.keys():
    if test_movie in title.lower():
        movie_found = title
        print(f"\nFound movie: '{title}'")
        break

if not movie_found:
    print(f"\n❌ Movie '{test_movie}' not found in review data")
    print(f"\nAvailable movies containing 'bad': {[m for m in movie_to_users.keys() if 'bad' in m.lower()]}")
else:
    results, error = recommend_hybrid(movie_found, top_n=15)

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
print("  from hybrid_recommender_v2 import recommend_hybrid")
print("  results, error = recommend_hybrid('bad ben', top_n=10)")
