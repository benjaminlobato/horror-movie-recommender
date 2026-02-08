"""
Simple Flask web app for horror movie recommendations
"""
from flask import Flask, render_template, jsonify, request
import pandas as pd
import pickle
import os
from pathlib import Path

app = Flask(__name__)

# Load data
project_root = Path(__file__).parent.parent
movies_df = pickle.load(open(project_root / 'data' / 'movies_processed.pkl', 'rb'))
similarity = pickle.load(open(project_root / 'data' / 'similarity_matrix.pkl', 'rb'))

TMDB_API_KEY = os.getenv('TMDB_API_KEY', '8265bd1679663a7ea12ac168da84d2e8')

print(f"✓ Loaded {len(movies_df)} movies")

def get_poster_url(tmdb_id):
    """Get TMDB poster URL for a movie"""
    return f"https://image.tmdb.org/t/p/w342/{tmdb_id}"  # We'll fetch this from API if needed

def recommend_tiered(movie_idx, n_recommendations=10):
    """
    Tiered recommendation approach
    """
    # Get all similar movies
    similarities = list(enumerate(similarity[movie_idx]))
    similarities = sorted(similarities, reverse=True, key=lambda x: x[1])

    # Exclude the movie itself
    similarities = [(idx, score) for idx, score in similarities if idx != movie_idx]

    # Calculate tier sizes
    n_tier1 = int(n_recommendations * 0.4)
    n_tier2 = int(n_recommendations * 0.3)
    n_tier3 = int(n_recommendations * 0.2)
    n_tier4 = n_recommendations - n_tier1 - n_tier2 - n_tier3

    recommendations = []

    # TIER 1: Best matches
    tier1 = []
    for idx, score in similarities[:50]:
        movie = movies_df.iloc[idx]
        tier1.append({
            'idx': int(idx),
            'tmdb_id': int(movie['tmdb_id']),
            'title': movie['title'],
            'year': str(movie['year']),
            'vote_count': int(movie['vote_count']),
            'vote_average': float(movie['vote_average']),
            'similarity': float(score),
            'tier': 'Best Match',
            'tier_emoji': '🎯'
        })
    tier1 = sorted(tier1, key=lambda x: x['similarity'], reverse=True)[:n_tier1]
    recommendations.extend(tier1)

    used_ids = {r['idx'] for r in recommendations}

    # TIER 2: Obscure
    tier2 = []
    for idx, score in similarities:
        if idx in used_ids:
            continue
        movie = movies_df.iloc[idx]
        if movie['vote_count'] < 500:
            tier2.append({
                'idx': int(idx),
                'tmdb_id': int(movie['tmdb_id']),
                'title': movie['title'],
                'year': str(movie['year']),
                'vote_count': int(movie['vote_count']),
                'vote_average': float(movie['vote_average']),
                'similarity': float(score),
                'tier': 'Hidden Gem',
                'tier_emoji': '💎'
            })
        if len(tier2) >= n_tier2:
            break
    recommendations.extend(tier2)
    used_ids.update(r['idx'] for r in tier2)

    # TIER 3: Niche
    tier3 = []
    for idx, score in similarities:
        if idx in used_ids:
            continue
        movie = movies_df.iloc[idx]
        if 500 <= movie['vote_count'] < 2000:
            tier3.append({
                'idx': int(idx),
                'tmdb_id': int(movie['tmdb_id']),
                'title': movie['title'],
                'year': str(movie['year']),
                'vote_count': int(movie['vote_count']),
                'vote_average': float(movie['vote_average']),
                'similarity': float(score),
                'tier': 'Cult Classic',
                'tier_emoji': '🔥'
            })
        if len(tier3) >= n_tier3:
            break
    recommendations.extend(tier3)
    used_ids.update(r['idx'] for r in tier3)

    # TIER 4: Established
    tier4 = []
    for idx, score in similarities:
        if idx in used_ids:
            continue
        movie = movies_df.iloc[idx]
        if movie['vote_count'] >= 2000:
            tier4.append({
                'idx': int(idx),
                'tmdb_id': int(movie['tmdb_id']),
                'title': movie['title'],
                'year': str(movie['year']),
                'vote_count': int(movie['vote_count']),
                'vote_average': float(movie['vote_average']),
                'similarity': float(score),
                'tier': 'Established',
                'tier_emoji': '⭐'
            })
        if len(tier4) >= n_tier4:
            break
    recommendations.extend(tier4)

    return recommendations

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/search')
def search():
    """Search for movies"""
    query = request.args.get('q', '').strip()

    if not query:
        return jsonify({'results': []})

    # Search in titles
    matches = movies_df[movies_df['title'].str.contains(query, case=False, na=False)]

    results = []
    for idx, row in matches.head(10).iterrows():
        results.append({
            'idx': int(idx),
            'tmdb_id': int(row['tmdb_id']),
            'title': row['title'],
            'year': str(row['year']),
            'vote_count': int(row['vote_count']),
            'vote_average': float(row['vote_average'])
        })

    return jsonify({'results': results})

@app.route('/api/recommend/<int:movie_idx>')
def recommend(movie_idx):
    """Get recommendations for a movie"""
    try:
        movie = movies_df.iloc[movie_idx]

        movie_info = {
            'tmdb_id': int(movie['tmdb_id']),
            'title': movie['title'],
            'year': str(movie['year']),
            'vote_count': int(movie['vote_count']),
            'vote_average': float(movie['vote_average'])
        }

        recommendations = recommend_tiered(movie_idx, n_recommendations=10)

        return jsonify({
            'movie': movie_info,
            'recommendations': recommendations
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/stats')
def stats():
    """Get dataset statistics"""
    return jsonify({
        'total_movies': len(movies_df),
        'avg_vote_count': float(movies_df['vote_count'].mean()),
        'avg_rating': float(movies_df['vote_average'].mean())
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
