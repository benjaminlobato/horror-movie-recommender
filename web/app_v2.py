"""
Flask web app V2 for hybrid horror movie recommendations
Uses new database schema with expanded universe (~3,600 movies)
Combines collaborative filtering (user overlap) with content-based filtering
"""
from flask import Flask, render_template, jsonify, request
import sys
from pathlib import Path
import pandas as pd

# Add scripts directory to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root / 'scripts'))

from hybrid_recommender_v3 import (
    recommend,
    get_movie_info,
    search_movies,
    movies_df,
    movie_to_users,
    title_to_movie_id,
    movie_id_to_metadata,
    user_to_movies
)

app = Flask(__name__)

print("=" * 70)
print("LOADING HYBRID HORROR RECOMMENDER WEB APP V2")
print("=" * 70)
print(f"✓ Total movies in universe: {len(movies_df):,}")
print(f"✓ Movies with reviews (hybrid): {len(movie_to_users):,}")
print(f"✓ Movies using cosine fallback: {len(movies_df) - len(movie_to_users):,}")
print(f"✓ Horror club movies: {len(movies_df[movies_df['data_source'] == 'horror_club']):,}")
print(f"✓ Letterboxd coreviews: {len(movies_df[movies_df['data_source'] == 'letterboxd_coreviews']):,}")
print(f"✓ Horror fans tracked: {len(user_to_movies):,}")
print("✓ Ready to serve recommendations!")

def format_movie_result(metadata, review_count=None):
    """Format a movie for display"""
    if review_count is None:
        # Try to get review count from movie_id
        movie_id = None
        # Find movie_id by title
        title_lower = metadata['title'].lower()
        if title_lower in title_to_movie_id:
            movie_id = title_to_movie_id[title_lower]
            review_count = len(movie_to_users.get(movie_id, set()))
        else:
            review_count = 0

    return {
        'title': metadata['title'],
        'tmdb_id': int(metadata['tmdb_id']) if pd.notna(metadata.get('tmdb_id')) else None,
        'imdb_id': metadata.get('imdb_id'),
        'year': int(metadata['year']) if pd.notna(metadata.get('year')) else None,
        'review_count': review_count,
        'genres': metadata.get('genres', ''),
        'director': metadata.get('director', ''),
        'is_horror_club': metadata.get('data_source') == 'horror_club',
        'is_true_horror': bool(metadata.get('is_true_horror')),
        'poster_url': metadata.get('poster_url', ''),
        'rating': metadata.get('rating')
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/search')
def search():
    """Search for movies by partial title match"""
    query = request.args.get('q', '').strip()

    if not query:
        return jsonify({'results': []})

    # Use the search_movies function from recommender
    matches = search_movies(query, limit=20)

    results = []
    for match in matches:
        # Get full metadata
        movie_id = match['movie_id']
        metadata = movie_id_to_metadata[movie_id]
        review_count = len(movie_to_users.get(movie_id, set()))

        results.append(format_movie_result(metadata, review_count))

    return jsonify({'results': results})

@app.route('/api/recommend/<path:movie_title>')
def get_recommendations(movie_title):
    """Get recommendations for a movie (hybrid or cosine fallback)"""
    movie_title_lower = movie_title.lower().strip()

    # Check if movie exists
    if movie_title_lower not in title_to_movie_id:
        return jsonify({'error': f'Movie "{movie_title}" not found'}), 404

    try:
        # Get filter parameter
        filter_true_horror = request.args.get('filter_true_horror', 'false').lower() == 'true'

        # Get recommendations
        results, error, method = recommend(
            movie_title_lower,
            top_n=20,
            filter_true_horror=filter_true_horror
        )

        if error:
            return jsonify({'error': error}), 400

        # Get movie info
        movie_id = title_to_movie_id[movie_title_lower]
        movie_metadata = movie_id_to_metadata[movie_id]
        review_count = len(movie_to_users.get(movie_id, set()))

        movie_info = format_movie_result(movie_metadata, review_count)
        movie_info['user_count'] = review_count
        movie_info['has_reviews'] = movie_id in movie_to_users

        # Format recommendations
        recommendations = []
        for movie_id, title, hybrid_score, user_count, content_sim, metadata in results:
            rec = format_movie_result(metadata, user_count)
            rec['user_overlap'] = user_count
            rec['content_similarity'] = round(content_sim, 3)
            rec['hybrid_score'] = round(hybrid_score, 3)

            # Determine tier based on score
            if method == 'cosine_fallback':
                # For cosine-only, use different thresholds
                if hybrid_score > 0.3:
                    rec['tier'] = 'Excellent Match'
                    rec['tier_emoji'] = '🎯'
                elif hybrid_score > 0.2:
                    rec['tier'] = 'Strong Match'
                    rec['tier_emoji'] = '💎'
                elif hybrid_score > 0.15:
                    rec['tier'] = 'Good Match'
                    rec['tier_emoji'] = '✨'
                else:
                    rec['tier'] = 'Worth Exploring'
                    rec['tier_emoji'] = '🔍'
            else:
                # Hybrid thresholds
                if hybrid_score > 0.2:
                    rec['tier'] = 'Excellent Match'
                    rec['tier_emoji'] = '🎯'
                elif hybrid_score > 0.15:
                    rec['tier'] = 'Strong Match'
                    rec['tier_emoji'] = '💎'
                elif hybrid_score > 0.1:
                    rec['tier'] = 'Good Match'
                    rec['tier_emoji'] = '✨'
                else:
                    rec['tier'] = 'Worth Exploring'
                    rec['tier_emoji'] = '🔍'

            recommendations.append(rec)

        return jsonify({
            'movie': movie_info,
            'recommendations': recommendations,
            'algorithm': method,
            'weights': {
                'user_overlap': 0.7 if method == 'hybrid' else 0.0,
                'content_similarity': 0.3 if method == 'hybrid' else 1.0
            },
            'filter_true_horror': filter_true_horror
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats')
def stats():
    """Get dataset statistics"""
    total_movies = len(movies_df)
    movies_with_reviews = len(movie_to_users)
    total_users = len(user_to_movies)

    # Calculate total reviews
    total_reviews = sum(len(users) for users in movie_to_users.values())

    # Count by data source
    horror_club_count = len(movies_df[movies_df['data_source'] == 'horror_club'])
    letterboxd_count = len(movies_df[movies_df['data_source'] == 'letterboxd_coreviews'])

    # Count by horror classification
    true_horror_count = len(movies_df[movies_df['is_true_horror'] == 1])
    non_horror_count = len(movies_df[movies_df['is_true_horror'] == 0])

    return jsonify({
        'total_movies': total_movies,
        'movies_with_reviews': movies_with_reviews,
        'movies_cosine_fallback': total_movies - movies_with_reviews,
        'total_users': total_users,
        'total_reviews': total_reviews,
        'horror_club_movies': horror_club_count,
        'letterboxd_coreviews': letterboxd_count,
        'true_horror_movies': true_horror_count,
        'non_horror_club_movies': non_horror_count,
        'avg_reviews_per_movie': round(total_reviews / movies_with_reviews, 1) if movies_with_reviews else 0,
        'algorithm': 'Hybrid with cosine fallback (70% user overlap + 30% content similarity when reviews available)',
        'coverage': round(movies_with_reviews / total_movies * 100, 1)
    })

@app.route('/api/movies')
def get_movies():
    """Get all movies for browsing"""
    # Get all movies sorted by review count
    movies_with_counts = []

    for _, row in movies_df.iterrows():
        movie_id = row['movie_id']
        review_count = len(movie_to_users.get(movie_id, set()))

        metadata = {
            'title': row['title'],
            'year': row['year'],
            'genres': row['genres'],
            'director': row['director'],
            'tmdb_id': row['tmdb_id'],
            'imdb_id': row['imdb_id'],
            'data_source': row['data_source'],
            'is_true_horror': row['is_true_horror'],
            'poster_url': row['poster_url'],
            'rating': row['rating']
        }

        movies_with_counts.append((metadata, review_count))

    # Sort by review count desc, then title
    movies_with_counts.sort(key=lambda x: (-x[1], x[0]['title']))

    movies = [format_movie_result(metadata, count) for metadata, count in movies_with_counts]

    return jsonify({'movies': movies})

@app.route('/api/popular')
def popular():
    """Get most reviewed movies"""
    # Get movies sorted by review count
    movie_counts = []
    for movie_id, users in movie_to_users.items():
        if movie_id in movie_id_to_metadata:
            metadata = movie_id_to_metadata[movie_id]
            movie_counts.append((metadata, len(users)))

    movie_counts.sort(key=lambda x: -x[1])

    popular_movies = [
        format_movie_result(metadata, count)
        for metadata, count in movie_counts[:30]
    ]

    return jsonify({'movies': popular_movies})

if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("Starting web server on http://0.0.0.0:5001")
    print("=" * 70)
    app.run(debug=True, host='0.0.0.0', port=5001)
