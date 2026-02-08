"""
Hybrid Recommendation System with Cosine Similarity Fallback
- Use hybrid (user overlap + content) when reviews are available
- Fall back to pure cosine similarity when no reviews exist
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
print("HYBRID RECOMMENDER WITH COSINE FALLBACK")
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

print(f"✓ Indexed {len(movie_to_users)} movies WITH reviews")
print(f"✓ Indexed {len(user_to_movies)} users")

# Load ALL horror club movies for fallback
print("\n3. Loading all horror club movies...")
db_path = project_root / 'data' / 'horror_recommender.db'
engine = create_engine(f'sqlite:///{db_path}')

query = text("""
    SELECT tmdb_id, title, genres, keywords, "cast", director
    FROM movies
    WHERE watched_by_club = 1
""")

with engine.connect() as conn:
    all_movies_df = pd.read_sql(query, conn)

print(f"✓ Loaded metadata for {len(all_movies_df)} total horror club movies")

# Build metadata lookup
tmdb_to_metadata = all_movies_df.set_index('tmdb_id').to_dict('index')
title_to_tmdb_all = {row['title'].lower().strip(): row['tmdb_id']
                     for _, row in all_movies_df.iterrows()}

# Movies without reviews (need cosine fallback)
movies_without_reviews = set(title_to_tmdb_all.keys()) - set(movie_to_users.keys())
print(f"✓ {len(movies_without_reviews)} movies need cosine fallback")

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
    """Compute content similarity between target and multiple candidates"""
    target_content = build_content_string(target_tmdb_id)
    candidate_contents = [build_content_string(cid) for cid in candidate_tmdb_ids]

    all_texts = [target_content] + candidate_contents

    vectorizer = TfidfVectorizer(lowercase=True, stop_words='english')
    try:
        tfidf_matrix = vectorizer.fit_transform(all_texts)
    except ValueError:
        return {cid: 0.0 for cid in candidate_tmdb_ids}

    target_vector = tfidf_matrix[0:1]
    candidate_vectors = tfidf_matrix[1:]
    similarities = cosine_similarity(target_vector, candidate_vectors)[0]

    return {cid: sim for cid, sim in zip(candidate_tmdb_ids, similarities)}


def recommend_cosine_only(movie_title, top_n=20):
    """
    Pure cosine similarity fallback for movies without reviews
    """
    movie_title = movie_title.lower().strip()

    if movie_title not in title_to_tmdb_all:
        return None, f"Movie '{movie_title}' not found"

    target_tmdb_id = title_to_tmdb_all[movie_title]

    # Get all other horror club movies
    candidate_tmdb_ids = [tmdb_id for title, tmdb_id in title_to_tmdb_all.items()
                          if title != movie_title]

    # Compute similarities
    similarities = compute_content_similarity(target_tmdb_id, candidate_tmdb_ids)

    # Build recommendations
    recommendations = []
    tmdb_to_title = {v: k for k, v in title_to_tmdb_all.items()}

    for tmdb_id, similarity in similarities.items():
        if similarity > 0.1:  # Minimum threshold
            title = tmdb_to_title.get(tmdb_id)
            if title:
                # Check if it has reviews for display
                review_count = len(movie_to_users.get(title, []))
                recommendations.append((
                    title,
                    0,  # user_overlap (N/A for cosine-only)
                    similarity,  # content_similarity
                    similarity,  # hybrid_score = just similarity
                    tmdb_id
                ))

    # Sort by similarity
    recommendations.sort(key=lambda x: x[3], reverse=True)
    return recommendations[:top_n], None


def recommend_hybrid(movie_title, top_n=20, min_content_similarity=0.1,
                    user_weight=0.7, similarity_weight=0.3):
    """
    Hybrid recommendation with user overlap + content similarity
    """
    movie_title = movie_title.lower().strip()

    if movie_title not in movie_to_users:
        return None, f"No reviews found for '{movie_title}'"

    if movie_title not in movie_title_to_tmdb:
        return None, f"No TMDB mapping for '{movie_title}'"

    target_tmdb_id = movie_title_to_tmdb[movie_title]

    # Find users who reviewed this movie
    users_who_reviewed = set(movie_to_users[movie_title])

    # Get all other movies those users reviewed
    candidate_movies = Counter()
    for user in users_who_reviewed:
        for other_movie in user_to_movies[user]:
            if other_movie != movie_title:
                candidate_movies[other_movie] += 1

    if not candidate_movies:
        return [], None

    # Compute content similarities
    candidate_tmdb_ids = [movie_title_to_tmdb[title] for title in candidate_movies.keys()
                          if title in movie_title_to_tmdb]

    similarities = compute_content_similarity(target_tmdb_id, candidate_tmdb_ids)

    # Calculate hybrid scores
    recommendations = []

    for candidate_title, user_count in candidate_movies.items():
        candidate_tmdb_id = movie_title_to_tmdb.get(candidate_title)
        if not candidate_tmdb_id:
            continue

        content_sim = similarities.get(candidate_tmdb_id, 0.0)

        # Filter by content similarity
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

    # Sort by hybrid score
    recommendations.sort(key=lambda x: x[3], reverse=True)
    return recommendations[:top_n], None


def recommend(movie_title, top_n=20):
    """
    Smart recommender: Use hybrid if reviews available, else fall back to cosine
    """
    movie_title = movie_title.lower().strip()

    # Check if movie has reviews
    if movie_title in movie_to_users:
        # Use hybrid
        results, error = recommend_hybrid(movie_title, top_n=top_n)
        if error:
            return results, error
        return results, None, 'hybrid'
    elif movie_title in title_to_tmdb_all:
        # Fall back to cosine-only
        results, error = recommend_cosine_only(movie_title, top_n=top_n)
        if error:
            return results, error
        return results, None, 'cosine_fallback'
    else:
        return None, f"Movie '{movie_title}' not found in database", None


# Export functions and data for web app
__all__ = [
    'recommend',
    'recommend_hybrid',
    'recommend_cosine_only',
    'movie_to_users',
    'movie_title_to_tmdb',
    'tmdb_to_metadata',
    'title_to_tmdb_all',
    'movies_without_reviews'
]

if __name__ == '__main__':
    # Test both methods
    print("\n" + "=" * 70)
    print("TESTING HYBRID RECOMMENDATIONS")
    print("=" * 70)

    test_movie = "bad ben"
    results, error, method = recommend(test_movie, top_n=10)

    if error:
        print(f"Error: {error}")
    else:
        print(f"\nMovie: {test_movie}")
        print(f"Method: {method}")
        print(f"Results: {len(results)} recommendations\n")

        for i, (title, user_count, content_sim, score, tmdb_id) in enumerate(results, 1):
            print(f"{i:2d}. {title:45s} Users:{user_count:3d} Content:{content_sim:.3f} Score:{score:.3f}")

    # Test cosine fallback
    print("\n" + "=" * 70)
    print("TESTING COSINE FALLBACK")
    print("=" * 70)

    # Pick a movie without reviews
    if movies_without_reviews:
        test_movie = list(movies_without_reviews)[0]
        results, error, method = recommend(test_movie, top_n=10)

        if error:
            print(f"Error: {error}")
        else:
            print(f"\nMovie: {test_movie}")
            print(f"Method: {method}")
            print(f"Results: {len(results)} recommendations\n")

            for i, (title, user_count, content_sim, score, tmdb_id) in enumerate(results, 1):
                print(f"{i:2d}. {title:45s} Content:{content_sim:.3f} Score:{score:.3f}")
