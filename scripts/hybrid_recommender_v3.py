"""
Hybrid Recommender V3 - Uses new database schema
Combines user overlap (70%) + content similarity (30%)
Works with expanded universe (~3,600 movies)
"""
import sqlite3
import pandas as pd
from pathlib import Path
from collections import defaultdict, Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

project_root = Path(__file__).parent.parent

# Connect to new database
db_path = project_root / 'data' / 'horror_recommender_v2.db'
conn = sqlite3.connect(db_path)

print("=" * 70)
print("LOADING HYBRID RECOMMENDER V3")
print("=" * 70)

# ============================================================================
# LOAD MOVIE UNIVERSE
# ============================================================================
print("\n1. Loading movie universe from horror_movies table...")

query = """
    SELECT
        id as movie_id,
        title,
        year,
        director,
        genres,
        "cast",
        data_source,
        is_true_horror,
        tmdb_id,
        imdb_id,
        letterboxd_id,
        poster_url,
        rating
    FROM horror_movies
    ORDER BY title
"""

movies_df = pd.read_sql_query(query, conn)
print(f"   Loaded {len(movies_df):,} movies")
print(f"   - {len(movies_df[movies_df['data_source'] == 'horror_club']):,} horror club")
print(f"   - {len(movies_df[movies_df['data_source'] == 'letterboxd_coreviews']):,} letterboxd coreviews")
print(f"   - {len(movies_df[movies_df['is_true_horror'] == 1]):,} with Horror genre")

# Create lookups
title_to_movie_id = {}
movie_id_to_metadata = {}

for _, row in movies_df.iterrows():
    movie_id = row['movie_id']
    title = row['title']
    title_lower = title.lower()

    title_to_movie_id[title_lower] = movie_id

    movie_id_to_metadata[movie_id] = {
        'title': title,
        'year': row['year'],
        'director': row['director'] if pd.notna(row['director']) else '',
        'genres': row['genres'] if pd.notna(row['genres']) else '',
        'cast': row['cast'] if pd.notna(row['cast']) else '',
        'data_source': row['data_source'],
        'is_true_horror': row['is_true_horror'],
        'tmdb_id': row['tmdb_id'],
        'imdb_id': row['imdb_id'],
        'letterboxd_id': row['letterboxd_id'],
        'poster_url': row['poster_url'],
        'rating': row['rating']
    }

# ============================================================================
# LOAD USER REVIEWS FOR COLLABORATIVE FILTERING
# ============================================================================
print("\n2. Loading user reviews from letterboxd_reviews table...")

reviews_query = """
    SELECT
        movie_id,
        username
    FROM letterboxd_reviews
    ORDER BY movie_id, username
"""

reviews_df = pd.read_sql_query(reviews_query, conn)
print(f"   Loaded {len(reviews_df):,} reviews")
print(f"   - {reviews_df['movie_id'].nunique():,} distinct movies reviewed")
print(f"   - {reviews_df['username'].nunique():,} distinct users (horror fans)")

# Build collaborative filtering lookups
user_to_movies = defaultdict(set)
movie_to_users = defaultdict(set)

for _, row in reviews_df.iterrows():
    movie_id = row['movie_id']
    username = row['username']

    user_to_movies[username].add(movie_id)
    movie_to_users[movie_id].add(username)

print(f"   Built user-movie mappings for {len(movie_to_users):,} movies")

# ============================================================================
# BUILD CONTENT SIMILARITY MATRIX (TF-IDF)
# ============================================================================
print("\n3. Building content similarity matrix...")

# Create feature vectors for each movie
movie_features = []
movie_ids_ordered = []

for movie_id in sorted(movie_id_to_metadata.keys()):
    metadata = movie_id_to_metadata[movie_id]

    # Combine text features
    features = ' '.join([
        metadata['genres'],
        metadata['director'],
        metadata['cast']
    ])

    movie_features.append(features)
    movie_ids_ordered.append(movie_id)

# Compute TF-IDF
vectorizer = TfidfVectorizer(
    max_features=1000,
    stop_words='english',
    ngram_range=(1, 2)
)

tfidf_matrix = vectorizer.fit_transform(movie_features)

# Precompute similarity matrix (this is memory intensive but makes lookups fast)
print(f"   Computing cosine similarity for {len(movie_ids_ordered):,} x {len(movie_ids_ordered):,} matrix...")
similarity_matrix = cosine_similarity(tfidf_matrix, tfidf_matrix)

# Create lookup: movie_id -> index in matrix
movie_id_to_idx = {movie_id: idx for idx, movie_id in enumerate(movie_ids_ordered)}

print(f"   ✓ Content similarity matrix ready")

# ============================================================================
# RECOMMENDATION FUNCTIONS
# ============================================================================

def recommend_hybrid(movie_title, top_n=20, user_weight=0.7, similarity_weight=0.3,
                    min_content_similarity=0.05, filter_true_horror=False):
    """
    Hybrid recommendation: user overlap (70%) + content similarity (30%)

    Args:
        movie_title: Title of the movie to get recommendations for
        top_n: Number of recommendations to return
        user_weight: Weight for user overlap score (default 0.7)
        similarity_weight: Weight for content similarity score (default 0.3)
        min_content_similarity: Minimum content similarity threshold (default 0.05)
        filter_true_horror: If True, only recommend movies with is_true_horror=True

    Returns:
        List of tuples: (movie_id, title, hybrid_score, user_overlap, content_sim, metadata)
    """
    movie_title_lower = movie_title.lower()

    if movie_title_lower not in title_to_movie_id:
        return None, "Movie not found in universe"

    movie_id = title_to_movie_id[movie_title_lower]

    # Check if movie has reviews
    if movie_id not in movie_to_users:
        return None, "Movie has no reviews - falling back to cosine similarity"

    # Get users who reviewed this movie
    users_who_reviewed = movie_to_users[movie_id]

    # Find candidate movies reviewed by same users
    candidate_movies = Counter()
    for user in users_who_reviewed:
        for other_movie_id in user_to_movies[user]:
            if other_movie_id != movie_id:
                candidate_movies[other_movie_id] += 1

    if not candidate_movies:
        return None, "No overlapping reviews found"

    # Get content similarity index for target movie
    target_idx = movie_id_to_idx.get(movie_id)
    if target_idx is None:
        return None, "Movie not in similarity matrix"

    # Score candidates
    recommendations = []

    for candidate_id, user_count in candidate_movies.items():
        # Skip if filtering for true horror and this isn't true horror
        if filter_true_horror and not movie_id_to_metadata[candidate_id]['is_true_horror']:
            continue

        # Get content similarity
        candidate_idx = movie_id_to_idx.get(candidate_id)
        if candidate_idx is None:
            continue

        content_sim = similarity_matrix[target_idx][candidate_idx]

        # Skip if below minimum content similarity
        if content_sim < min_content_similarity:
            continue

        # Calculate hybrid score
        normalized_user_count = user_count / len(users_who_reviewed)
        hybrid_score = (normalized_user_count * user_weight) + (content_sim * similarity_weight)

        metadata = movie_id_to_metadata[candidate_id]

        recommendations.append((
            candidate_id,
            metadata['title'],
            hybrid_score,
            user_count,
            content_sim,
            metadata
        ))

    # Sort by hybrid score
    recommendations.sort(key=lambda x: x[2], reverse=True)

    return recommendations[:top_n], None


def recommend_cosine_fallback(movie_title, top_n=20, filter_true_horror=False):
    """
    Fallback to pure content-based filtering for movies with no reviews
    """
    movie_title_lower = movie_title.lower()

    if movie_title_lower not in title_to_movie_id:
        return None, "Movie not found in universe"

    movie_id = title_to_movie_id[movie_title_lower]
    target_idx = movie_id_to_idx.get(movie_id)

    if target_idx is None:
        return None, "Movie not in similarity matrix"

    # Get all similarities for this movie
    similarities = similarity_matrix[target_idx]

    # Get top similar movies
    similar_indices = np.argsort(similarities)[::-1]

    recommendations = []
    for idx in similar_indices[1:top_n+1]:  # Skip first (itself)
        candidate_id = movie_ids_ordered[idx]

        # Skip if filtering for true horror and this isn't true horror
        if filter_true_horror and not movie_id_to_metadata[candidate_id]['is_true_horror']:
            continue

        metadata = movie_id_to_metadata[candidate_id]

        recommendations.append((
            candidate_id,
            metadata['title'],
            similarities[idx],
            0,  # No user overlap
            similarities[idx],
            metadata
        ))

    return recommendations[:top_n], None


def recommend(movie_title, top_n=20, filter_true_horror=False):
    """
    Main recommendation function with automatic fallback

    Returns:
        (recommendations, error, method)
    """
    # Try hybrid first
    results, error = recommend_hybrid(
        movie_title,
        top_n=top_n,
        filter_true_horror=filter_true_horror
    )

    if results is not None:
        return results, None, 'hybrid'

    # Fallback to cosine similarity
    if "no reviews" in error.lower():
        results, error = recommend_cosine_fallback(
            movie_title,
            top_n=top_n,
            filter_true_horror=filter_true_horror
        )

        if results is not None:
            return results, None, 'cosine_fallback'

    return None, error, None


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_movie_info(movie_title):
    """Get metadata for a specific movie"""
    movie_title_lower = movie_title.lower()

    if movie_title_lower not in title_to_movie_id:
        return None

    movie_id = title_to_movie_id[movie_title_lower]
    metadata = movie_id_to_metadata[movie_id]

    # Add review count
    review_count = len(movie_to_users.get(movie_id, set()))
    metadata['review_count'] = review_count

    return metadata


def search_movies(query, limit=20):
    """Search for movies by partial title match"""
    query_lower = query.lower()
    matches = []

    for title_lower, movie_id in title_to_movie_id.items():
        if query_lower in title_lower:
            metadata = movie_id_to_metadata[movie_id]
            matches.append({
                'movie_id': movie_id,
                'title': metadata['title'],
                'year': metadata['year'],
                'genres': metadata['genres'],
                'is_true_horror': metadata['is_true_horror']
            })

    return matches[:limit]


# ============================================================================
# STATS
# ============================================================================

movies_with_reviews = len(movie_to_users)
movies_without_reviews = len(movies_df) - movies_with_reviews

print("\n" + "=" * 70)
print("RECOMMENDER V3 READY")
print("=" * 70)
print(f"Total movies in universe:        {len(movies_df):,}")
print(f"  - With reviews (hybrid):       {movies_with_reviews:,}")
print(f"  - Without reviews (fallback):  {movies_without_reviews:,}")
print(f"Coverage:                         {movies_with_reviews/len(movies_df)*100:.1f}%")
print(f"\nHorror fans tracked:             {len(user_to_movies):,}")
print(f"Total reviews:                   {len(reviews_df):,}")
print(f"\nReady to recommend!")

conn.close()

# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("TESTING RECOMMENDATIONS")
    print("=" * 70)

    test_movies = [
        "Bad Ben",
        "The Thing",
        "Scream"
    ]

    for movie in test_movies:
        print(f"\n{'='*70}")
        print(f"Recommendations for: {movie}")
        print('='*70)

        results, error, method = recommend(movie, top_n=10)

        if error:
            print(f"Error: {error}")
            continue

        print(f"Method: {method.upper()}")
        print(f"\n{'#':<4} {'Title':<45} {'Year':<6} {'Hybrid':<8} {'Users':<7} {'Content':<8}")
        print("-" * 80)

        for i, (movie_id, title, hybrid_score, user_count, content_sim, metadata) in enumerate(results, 1):
            year = metadata['year'] if pd.notna(metadata['year']) else 'N/A'
            print(f"{i:<4} {title[:44]:<45} {str(year):<6} {hybrid_score:.3f}    {user_count:<7} {content_sim:.3f}")
