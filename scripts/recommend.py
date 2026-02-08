"""
Horror Movie Recommender with Tiered Approach
Balances similarity with diversity across popularity levels
"""
import pandas as pd
import pickle
from pathlib import Path

project_root = Path(__file__).parent.parent

# Load data
print("Loading data...")
movies_df = pickle.load(open(project_root / 'data' / 'movies_processed.pkl', 'rb'))
similarity = pickle.load(open(project_root / 'data' / 'similarity_matrix.pkl', 'rb'))
print(f"✓ Loaded {len(movies_df)} movies\n")

def recommend_tiered(movie_title, n_recommendations=10, verbose=True):
    """
    Tiered recommendation approach:
    - 40% Best matches (any vote_count)
    - 30% Obscure (< 500 votes)
    - 20% Niche (500-2K votes)
    - 10% Established (> 2K votes)
    """

    # Find the movie
    matches = movies_df[movies_df['title'].str.contains(movie_title, case=False, na=False)]

    if len(matches) == 0:
        print(f"❌ Movie '{movie_title}' not found in dataset")
        return None

    if len(matches) > 1:
        print(f"Found {len(matches)} matches:")
        for idx, row in matches.iterrows():
            print(f"  [{idx}] {row['title']} ({row['year']}) - {row['vote_count']} votes")
        movie_idx = matches.index[0]
        print(f"\nUsing: {movies_df.iloc[movie_idx]['title']}")
    else:
        movie_idx = matches.index[0]

    movie_info = movies_df.iloc[movie_idx]

    if verbose:
        print(f"\n{'='*70}")
        print(f"RECOMMENDATIONS FOR: {movie_info['title']} ({movie_info['year']})")
        print(f"Vote count: {movie_info['vote_count']}, Rating: {movie_info['vote_average']}/10")
        print(f"{'='*70}\n")

    # Get all similar movies (sorted by similarity)
    similarities = list(enumerate(similarity[movie_idx]))
    similarities = sorted(similarities, reverse=True, key=lambda x: x[1])

    # Exclude the movie itself
    similarities = [(idx, score) for idx, score in similarities if idx != movie_idx]

    # Calculate tier sizes
    n_tier1 = int(n_recommendations * 0.4)  # 40% best matches
    n_tier2 = int(n_recommendations * 0.3)  # 30% obscure
    n_tier3 = int(n_recommendations * 0.2)  # 20% niche
    n_tier4 = n_recommendations - n_tier1 - n_tier2 - n_tier3  # 10% established

    recommendations = []

    # TIER 1: Best matches (any vote_count)
    tier1 = []
    for idx, score in similarities[:50]:  # Top 50 candidates
        movie = movies_df.iloc[idx]
        tier1.append({
            'idx': idx,
            'title': movie['title'],
            'year': movie['year'],
            'vote_count': movie['vote_count'],
            'vote_average': movie['vote_average'],
            'similarity': score,
            'tier': 'Best Match'
        })
    tier1 = sorted(tier1, key=lambda x: x['similarity'], reverse=True)[:n_tier1]
    recommendations.extend(tier1)

    # Get IDs already used
    used_ids = {r['idx'] for r in recommendations}

    # TIER 2: Obscure (< 500 votes)
    tier2 = []
    for idx, score in similarities:
        if idx in used_ids:
            continue
        movie = movies_df.iloc[idx]
        if movie['vote_count'] < 500:
            tier2.append({
                'idx': idx,
                'title': movie['title'],
                'year': movie['year'],
                'vote_count': movie['vote_count'],
                'vote_average': movie['vote_average'],
                'similarity': score,
                'tier': 'Hidden Gem'
            })
        if len(tier2) >= n_tier2:
            break
    recommendations.extend(tier2)
    used_ids.update(r['idx'] for r in tier2)

    # TIER 3: Niche (500-2K votes)
    tier3 = []
    for idx, score in similarities:
        if idx in used_ids:
            continue
        movie = movies_df.iloc[idx]
        if 500 <= movie['vote_count'] < 2000:
            tier3.append({
                'idx': idx,
                'title': movie['title'],
                'year': movie['year'],
                'vote_count': movie['vote_count'],
                'vote_average': movie['vote_average'],
                'similarity': score,
                'tier': 'Cult Classic'
            })
        if len(tier3) >= n_tier3:
            break
    recommendations.extend(tier3)
    used_ids.update(r['idx'] for r in tier3)

    # TIER 4: Established (> 2K votes)
    tier4 = []
    for idx, score in similarities:
        if idx in used_ids:
            continue
        movie = movies_df.iloc[idx]
        if movie['vote_count'] >= 2000:
            tier4.append({
                'idx': idx,
                'title': movie['title'],
                'year': movie['year'],
                'vote_count': movie['vote_count'],
                'vote_average': movie['vote_average'],
                'similarity': score,
                'tier': 'Established'
            })
        if len(tier4) >= n_tier4:
            break
    recommendations.extend(tier4)

    # Display recommendations
    if verbose:
        for i, rec in enumerate(recommendations, 1):
            tier_emoji = {
                'Best Match': '🎯',
                'Hidden Gem': '💎',
                'Cult Classic': '🔥',
                'Established': '⭐'
            }[rec['tier']]

            print(f"{i:2}. {tier_emoji} {rec['title']} ({rec['year']})")
            print(f"    Similarity: {rec['similarity']:.3f} | "
                  f"Votes: {rec['vote_count']:,} | "
                  f"Rating: {rec['vote_average']}/10 | "
                  f"[{rec['tier']}]")
            print()

    return recommendations

# Test with different movies
if __name__ == "__main__":
    test_movies = [
        "Bad Ben",
        "The Wicker Man",
        "Hell House LLC"
    ]

    for movie in test_movies:
        results = recommend_tiered(movie, n_recommendations=10)
        if results:
            print(f"\n{'='*70}\n")
