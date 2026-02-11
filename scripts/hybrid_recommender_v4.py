"""
Hybrid Recommender V4 - SVD Collaborative Filtering with Numeric Ratings

Uses the titouann/letterboxd-10m-movies-ratings-2025 dataset (10.4M ratings,
0.5-5.0 stars, 6,519 users, 281K movies) for SVD-based collaborative filtering.
97.5% of our ~10,700 horror movies appear in this dataset with 1.85M ratings.

Combines SVD movie-movie similarity (70%) + TF-IDF content similarity (30%).
Same API contract as v3: recommend(title, top_n) → (recs, error, method).

Movie universe loaded from master-movies.json (exported from Supabase
master_movies table via movie-night/scripts/export-master-movies.py).
Uses tmdb_id as the internal movie ID throughout.
"""
import json
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import svds

project_root = Path(__file__).parent.parent

# Paths
json_path = project_root.parent / 'movie-night' / 'data' / 'master-movies.json'
parquet_path = project_root / 'data' / 'letterboxd-ratings' / 'titouann_10m.parquet'

print("=" * 70)
print("LOADING HYBRID RECOMMENDER V4 (SVD)")
print("=" * 70)

# ============================================================================
# STEP 1: LOAD MOVIE UNIVERSE FROM MASTER-MOVIES.JSON
# ============================================================================
print(f"\n1. Loading movie universe from {json_path.name}...")

if not json_path.exists():
    raise FileNotFoundError(
        f"{json_path} not found. Run: python movie-night/scripts/export-master-movies.py"
    )

with open(json_path) as f:
    movies_raw = json.load(f)

n_movies_total = len(movies_raw)
n_horror = sum(1 for m in movies_raw if m.get('is_horror'))
print(f"   Loaded {n_movies_total:,} movies ({n_horror:,} horror)")

# Create lookups — tmdb_id IS the movie_id now
title_to_movie_id = {}
tmdb_to_movie_id = {}
movie_id_to_metadata = {}
movie_id_to_lb_slug = {}

for m in movies_raw:
    movie_id = m['tmdb_id']
    title = m.get('title', '')

    title_to_movie_id[title.lower()] = movie_id
    tmdb_to_movie_id[movie_id] = movie_id  # identity mapping

    movie_id_to_metadata[movie_id] = {
        'title': title,
        'year': m.get('year'),
        'director': m.get('director') or '',
        'tmdb_genres': m.get('tmdb_genres') or [],
        'keywords': m.get('keywords') or [],
        'is_horror': m.get('is_horror', False),
        'tmdb_id': movie_id,
        'imdb_id': m.get('imdb_id'),
        'letterboxd_id': m.get('letterboxd_id'),
        'poster_path': m.get('poster_path'),
        'vote_average': m.get('vote_average'),
        'vote_count': m.get('vote_count'),
        'origin_country': m.get('origin_country') or [],
        'top_cast': m.get('top_cast') or [],
    }

    if m.get('letterboxd_id'):
        movie_id_to_lb_slug[movie_id] = m['letterboxd_id']

# Reverse lookups: letterboxd slug → movie_id(s)
# Multiple movie_ids can share the same letterboxd slug (duplicates in DB).
lb_slug_to_movie_id = {v: k for k, v in movie_id_to_lb_slug.items()}
lb_slug_to_movie_ids = {}
for mid, slug in movie_id_to_lb_slug.items():
    lb_slug_to_movie_ids.setdefault(slug, []).append(mid)

# ============================================================================
# STEP 2: LOAD TITOUANN RATINGS AND BUILD SVD
# ============================================================================
print("\n2. Loading titouann ratings and building SVD...")

# Load parquet — only the columns we need
ratings_df = pd.read_parquet(parquet_path, columns=['user', 'title', 'rating'])

# Filter to movies in our universe
our_slugs = set(lb_slug_to_movie_id.keys())
ratings_df = ratings_df[ratings_df['title'].isin(our_slugs)]
print(f"   Filtered to {len(ratings_df):,} ratings on {ratings_df['title'].nunique():,} of our movies")
print(f"   {ratings_df['user'].nunique():,} distinct users")

# Build rating count lookup (used by generate-recommendations.py for adaptive scoring)
# Map ALL movie_ids sharing a slug to the same count.
movie_rating_counts = {}
rating_counts_by_slug = ratings_df.groupby('title').size()
for slug, count in rating_counts_by_slug.items():
    for mid in lb_slug_to_movie_ids.get(slug, []):
        movie_rating_counts[mid] = int(count)

# Encode users and movies to integer indices
user_ids = ratings_df['user'].unique()
movie_slugs = ratings_df['title'].unique()

user_encoder = {uid: idx for idx, uid in enumerate(user_ids)}
slug_encoder = {slug: idx for idx, slug in enumerate(movie_slugs)}
slug_decoder = {idx: slug for slug, idx in slug_encoder.items()}

n_users = len(user_ids)
n_movies = len(movie_slugs)
print(f"   Matrix shape: {n_users:,} users × {n_movies:,} movies")

# Build sparse user-rating matrix
user_indices = ratings_df['user'].map(user_encoder).values
movie_indices = ratings_df['title'].map(slug_encoder).values
rating_values = ratings_df['rating'].values.astype(np.float32)

sparse_matrix = csr_matrix((rating_values, (user_indices, movie_indices)),
                           shape=(n_users, n_movies))

# Mean-center each user's ratings (subtract user mean)
print("   Mean-centering user ratings...")
user_means = np.array(sparse_matrix.sum(axis=1)).flatten()
user_nnz = np.diff(sparse_matrix.indptr)
user_nnz[user_nnz == 0] = 1  # avoid division by zero
user_means = user_means / user_nnz

# Subtract means only from nonzero entries
centered = sparse_matrix.copy().astype(np.float64)
for i in range(n_users):
    start, end = centered.indptr[i], centered.indptr[i + 1]
    centered.data[start:end] -= user_means[i]

# Run SVD with k=50 latent factors
k = 50
print(f"   Running SVD with k={k} latent factors...")
U, sigma, Vt = svds(centered, k=k)

# Movie factor matrix weighted by singular values
movie_factors = Vt.T * sigma  # shape: (n_movies, k)

# Compute movie-movie SVD similarity
print(f"   Computing SVD similarity matrix ({n_movies:,} × {n_movies:,})...")
svd_similarity = cosine_similarity(movie_factors).astype(np.float32)

# Create lookup: movie_id → SVD matrix index
# Map ALL movie_ids sharing a slug to the same SVD index.
movie_id_to_svd_idx = {}
for slug_idx in range(n_movies):
    slug = slug_decoder[slug_idx]
    for mid in lb_slug_to_movie_ids.get(slug, []):
        movie_id_to_svd_idx[mid] = slug_idx

print(f"   SVD similarity matrix ready ({len(movie_id_to_svd_idx):,} movies)")

# Free memory
del ratings_df, sparse_matrix, centered, U, Vt, movie_factors

# ============================================================================
# STEP 3: BUILD CONTENT SIMILARITY MATRIX (TF-IDF) — genres + director + keywords
# ============================================================================
print("\n3. Building content similarity matrix...")

movie_features = []
movie_ids_ordered = []

for movie_id in sorted(movie_id_to_metadata.keys()):
    metadata = movie_id_to_metadata[movie_id]
    features = ' '.join([
        ' '.join(metadata.get('tmdb_genres') or []),
        metadata.get('director') or '',
        ' '.join(metadata.get('keywords') or []),
    ])
    movie_features.append(features)
    movie_ids_ordered.append(movie_id)

vectorizer = TfidfVectorizer(
    max_features=1000,
    stop_words='english',
    ngram_range=(1, 2)
)

tfidf_matrix = vectorizer.fit_transform(movie_features)

print(f"   Computing cosine similarity for {len(movie_ids_ordered):,} × {len(movie_ids_ordered):,} matrix...")
content_similarity_matrix = cosine_similarity(tfidf_matrix, tfidf_matrix).astype(np.float32)

movie_id_to_content_idx = {movie_id: idx for idx, movie_id in enumerate(movie_ids_ordered)}

print(f"   Content similarity matrix ready")

# ============================================================================
# RECOMMENDATION FUNCTIONS
# ============================================================================

# SVD confidence ramp: below this many ratings, SVD factors are noisy so we
# lean more on content similarity.  At or above this count, use the full
# 70/30 SVD/content blend.
SVD_CONFIDENCE_THRESHOLD = 200

def recommend_hybrid(movie_title, top_n=20, max_svd_weight=0.7,
                     min_content_similarity=0.05, filter_true_horror=False,
                     tmdb_id=None):
    """
    Hybrid recommendation with rating-count-aware weight blending.

    When both source and candidate have many ratings, uses 70% SVD / 30%
    content.  When either has few ratings, shifts weight toward content
    similarity so that noisy SVD factors don't dominate.

    Args:
        movie_title: Title to search for (used if tmdb_id not provided)
        tmdb_id: TMDB ID for exact lookup (preferred over title for duplicates)

    Returns:
        (recommendations, error)
        Where recommendations is a list of tuples:
        (movie_id, title, hybrid_score, svd_sim_score, content_sim, metadata)
    """
    # Resolve movie_id: prefer tmdb_id (unique) over title (may collide)
    if tmdb_id is not None:
        movie_id = tmdb_to_movie_id.get(int(tmdb_id))
        if movie_id is None:
            return None, f"TMDB ID {tmdb_id} not found in universe"
    else:
        movie_title_lower = movie_title.lower()
        if movie_title_lower not in title_to_movie_id:
            return None, "Movie not found in universe"
        movie_id = title_to_movie_id[movie_title_lower]

    svd_idx = movie_id_to_svd_idx.get(movie_id)

    content_idx = movie_id_to_content_idx.get(movie_id)
    if content_idx is None:
        return None, "Movie not in content matrix"

    source_ratings = movie_rating_counts.get(movie_id, 0)
    has_svd = svd_idx is not None

    # Get similarity rows
    svd_sims = svd_similarity[svd_idx] if has_svd else None
    content_sims = content_similarity_matrix[content_idx]

    recommendations = []

    # Score all movies in content matrix as candidates
    for candidate_id, candidate_content_idx in movie_id_to_content_idx.items():
        if candidate_id == movie_id:
            continue

        if filter_true_horror and not movie_id_to_metadata[candidate_id].get('is_horror'):
            continue

        content_sim = float(content_sims[candidate_content_idx])

        if content_sim < min_content_similarity:
            continue

        # SVD similarity if both source and candidate have SVD data
        candidate_svd_idx = movie_id_to_svd_idx.get(candidate_id)
        if has_svd and candidate_svd_idx is not None:
            svd_sim = float(svd_sims[candidate_svd_idx])

            # Confidence ramp: trust SVD less when either movie has few ratings
            candidate_ratings = movie_rating_counts.get(candidate_id, 0)
            min_ratings = min(source_ratings, candidate_ratings)
            svd_confidence = min(min_ratings / SVD_CONFIDENCE_THRESHOLD, 1.0)
            svd_weight = max_svd_weight * svd_confidence
            content_weight = 1.0 - svd_weight

            hybrid_score = svd_weight * svd_sim + content_weight * content_sim
        else:
            # No SVD data for source or candidate — pure content
            svd_sim = 0.0
            hybrid_score = content_sim

        metadata = movie_id_to_metadata[candidate_id]
        recommendations.append((
            candidate_id,
            metadata['title'],
            hybrid_score,
            svd_sim,
            content_sim,
            metadata
        ))

    recommendations.sort(key=lambda x: x[2], reverse=True)
    return recommendations[:top_n], None


def recommend(movie_title, top_n=20, filter_true_horror=False, tmdb_id=None):
    """
    Main recommendation function.

    Args:
        movie_title: Title to search for
        tmdb_id: TMDB ID for exact lookup (preferred over title for duplicates)

    Returns:
        (recommendations, error, method)
    """
    # Resolve movie_id to determine method
    if tmdb_id is not None:
        movie_id = tmdb_to_movie_id.get(int(tmdb_id))
    else:
        movie_id = title_to_movie_id.get(movie_title.lower())
    has_svd = movie_id is not None and movie_id in movie_id_to_svd_idx

    results, error = recommend_hybrid(
        movie_title,
        top_n=top_n,
        filter_true_horror=filter_true_horror,
        tmdb_id=tmdb_id,
    )

    if results is not None:
        method = 'hybrid' if has_svd else 'content_only'
        return results, None, method

    return None, error, None


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_movie_info(movie_title):
    """Get metadata for a specific movie."""
    movie_title_lower = movie_title.lower()
    if movie_title_lower not in title_to_movie_id:
        return None

    movie_id = title_to_movie_id[movie_title_lower]
    metadata = movie_id_to_metadata[movie_id]
    metadata['rating_count'] = movie_rating_counts.get(movie_id, 0)
    return metadata


def search_movies(query, limit=20):
    """Search for movies by partial title match."""
    query_lower = query.lower()
    matches = []

    for title_lower, movie_id in title_to_movie_id.items():
        if query_lower in title_lower:
            metadata = movie_id_to_metadata[movie_id]
            matches.append({
                'movie_id': movie_id,
                'title': metadata['title'],
                'year': metadata['year'],
                'tmdb_genres': metadata.get('tmdb_genres', []),
                'is_horror': metadata.get('is_horror', False)
            })

    return matches[:limit]


# ============================================================================
# STATS
# ============================================================================

movies_with_svd = len(movie_id_to_svd_idx)
movies_without_svd = n_movies_total - movies_with_svd

print("\n" + "=" * 70)
print("RECOMMENDER V4 (SVD) READY")
print("=" * 70)
print(f"Total movies in universe:        {n_movies_total:,}")
print(f"  - With SVD data (hybrid):      {movies_with_svd:,}")
print(f"  - Without SVD (content only):  {movies_without_svd:,}")
print(f"Coverage:                         {movies_with_svd/n_movies_total*100:.1f}%")
print(f"SVD confidence threshold:        {SVD_CONFIDENCE_THRESHOLD} ratings")
print(f"\nSVD latent factors:              {k}")
print(f"Titouann ratings used:           {sum(movie_rating_counts.values()):,}")
print(f"\nReady to recommend!")

# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("TESTING RECOMMENDATIONS")
    print("=" * 70)

    test_movies = [
        "Halloween",
        "The Thing",
        "Deep Red",
        "Bride of Frankenstein",
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
        print(f"\n{'#':<4} {'Title':<45} {'Year':<6} {'Hybrid':<8} {'SVD':<8} {'Content':<8}")
        print("-" * 82)

        for i, (movie_id, title, hybrid_score, svd_sim, content_sim, metadata) in enumerate(results, 1):
            year = metadata.get('year') or 'N/A'
            print(f"{i:<4} {title[:44]:<45} {str(year):<6} {hybrid_score:.3f}    {svd_sim:.3f}    {content_sim:.3f}")
