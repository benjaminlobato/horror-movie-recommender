"""
Flask web app for hybrid horror movie recommendations
Combines collaborative filtering (user overlap) with content-based filtering
"""
from flask import Flask, render_template, jsonify, request
import sys
from pathlib import Path

# Add scripts directory to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root / 'scripts'))

from hybrid_recommender_with_fallback import (
    recommend, movie_to_users, movie_title_to_tmdb,
    tmdb_to_metadata, title_to_tmdb_all, movies_without_reviews
)
import pandas as pd

app = Flask(__name__)

print("=" * 70)
print("LOADING HYBRID HORROR RECOMMENDER WEB APP")
print("=" * 70)
print(f"✓ Total horror club movies: {len(title_to_tmdb_all)}")
print(f"✓ Movies with reviews: {len(movie_to_users)}")
print(f"✓ Movies using cosine fallback: {len(movies_without_reviews)}")
print(f"✓ Total users: {len(set().union(*[set(users) for users in movie_to_users.values()]))}")
print("✓ Ready to serve recommendations!")

# Create reverse mapping for search
tmdb_to_title = {v: k for k, v in movie_title_to_tmdb.items()}

# Load horror club data for display
horror_club_df = pd.read_csv(project_root / 'data' / 'horror_club_with_ids.csv')
horror_club_titles = set(horror_club_df['title'].str.lower().str.strip())

def format_movie_result(title, tmdb_id=None):
    """Format a movie for display"""
    if tmdb_id is None:
        tmdb_id = movie_title_to_tmdb.get(title)

    metadata = tmdb_to_metadata.get(tmdb_id, {}) if tmdb_id else {}
    review_count = len(movie_to_users.get(title, []))

    return {
        'title': title.title(),  # Capitalize for display
        'tmdb_id': int(tmdb_id) if tmdb_id else None,
        'review_count': review_count,
        'genres': metadata.get('genres', ''),
        'director': metadata.get('director', ''),
        'is_horror_club': title in horror_club_titles
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/search')
def search():
    """Search for movies in the review dataset"""
    query = request.args.get('q', '').strip().lower()

    if not query:
        return jsonify({'results': []})

    # Search in movie titles
    matches = [title for title in movie_to_users.keys() if query in title.lower()]
    matches = sorted(matches)[:20]  # Top 20 matches

    results = [format_movie_result(title) for title in matches]

    return jsonify({'results': results})

@app.route('/api/recommend/<path:movie_title>')
def get_recommendations(movie_title):
    """Get recommendations for a movie (hybrid or cosine fallback)"""
    movie_title_lower = movie_title.lower().strip()

    # Check if movie exists anywhere
    if movie_title_lower not in movie_to_users and movie_title_lower not in title_to_tmdb_all:
        return jsonify({'error': f'Movie "{movie_title}" not found'}), 404

    try:
        # Get recommendations (auto-detects hybrid vs cosine fallback)
        results, error, method = recommend(movie_title_lower, top_n=20)

        if error:
            return jsonify({'error': error}), 400

        # Format movie info
        movie_info = format_movie_result(movie_title_lower)
        movie_info['user_count'] = len(movie_to_users.get(movie_title_lower, []))
        movie_info['has_reviews'] = movie_title_lower in movie_to_users

        # Format recommendations
        recommendations = []
        for title, user_count, content_sim, hybrid_score, tmdb_id in results:
            rec = format_movie_result(title, tmdb_id)
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
            }
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats')
def stats():
    """Get dataset statistics"""
    user_set = set()
    total_reviews = 0

    for users in movie_to_users.values():
        user_set.update(users)
        total_reviews += len(users)

    return jsonify({
        'total_movies': len(title_to_tmdb_all),
        'movies_with_reviews': len(movie_to_users),
        'movies_cosine_fallback': len(movies_without_reviews),
        'total_users': len(user_set),
        'total_reviews': total_reviews,
        'horror_club_movies': len(horror_club_titles),
        'avg_reviews_per_movie': round(total_reviews / len(movie_to_users), 1) if movie_to_users else 0,
        'algorithm': 'Hybrid with cosine fallback (70% user overlap + 30% content similarity when reviews available)'
    })

@app.route('/api/movies')
def get_movies():
    """Get all movies for browsing (includes movies with and without reviews)"""
    # Combine movies with reviews and without
    all_movie_titles = set(title_to_tmdb_all.keys())

    movies_with_counts = []
    for title in all_movie_titles:
        review_count = len(movie_to_users.get(title, []))
        movies_with_counts.append((title, review_count))

    # Sort by review count desc, then title
    movies_with_counts.sort(key=lambda x: (-x[1], x[0]))

    movies = []
    for title, review_count in movies_with_counts:
        movie = format_movie_result(title)
        movies.append(movie)

    return jsonify({'movies': movies})

@app.route('/api/popular')
def popular():
    """Get most reviewed movies"""
    movies_with_counts = [(title, len(users)) for title, users in movie_to_users.items()]
    movies_with_counts.sort(key=lambda x: -x[1])

    popular_movies = []
    for title, review_count in movies_with_counts[:30]:
        movie = format_movie_result(title)
        popular_movies.append(movie)

    return jsonify({'movies': popular_movies})

if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("Starting web server on http://0.0.0.0:5001")
    print("=" * 70)
    app.run(debug=True, host='0.0.0.0', port=5001)
