"""
Fetch missing horror club movies from TMDB API
Add them to the database with proper IDs
"""
import pandas as pd
from sqlalchemy import create_engine, text
import os
import requests
import json
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

project_root = Path(__file__).parent.parent

# TMDB API configuration
TMDB_API_KEY = os.getenv('TMDB_API_KEY')
TMDB_BASE_URL = os.getenv('TMDB_API_BASE_URL', 'https://api.themoviedb.org/3')

if not TMDB_API_KEY:
    print("❌ TMDB_API_KEY not found in .env")
    exit(1)

# Load authoritative horror club data
horror_club_path = project_root / 'data' / 'horror_club_with_ids.csv'
horror_club_df = pd.read_csv(horror_club_path)

print("=" * 70)
print("FETCHING MISSING MOVIES FROM TMDB API")
print("=" * 70)
print(f"\nLoaded {len(horror_club_df)} horror club movies")

# Connect to database
engine = create_engine(os.getenv('DATABASE_URL'))

# Find missing movies
missing_movies = []

with engine.connect() as conn:
    for idx, row in horror_club_df.iterrows():
        tmdb_id = int(row['tmdb_id']) if pd.notna(row['tmdb_id']) else None

        if not tmdb_id:
            continue

        # Check if movie exists
        result = conn.execute(
            text('SELECT id FROM movies WHERE tmdb_id = :tmdb_id'),
            {'tmdb_id': tmdb_id}
        ).fetchone()

        if not result:
            missing_movies.append(row)

print(f"Found {len(missing_movies)} movies to fetch from TMDB\n")

# Fetch and insert missing movies
fetched_count = 0
error_count = 0

with engine.connect() as conn:
    for idx, row in enumerate(missing_movies, 1):
        tmdb_id = int(row['tmdb_id'])
        imdb_id = row['imdb_id'] if pd.notna(row['imdb_id']) else None
        letterboxd_id = row['film_slug'] if pd.notna(row['film_slug']) else None

        print(f"[{idx}/{len(missing_movies)}] Fetching TMDB ID {tmdb_id}...")

        try:
            # Fetch movie details from TMDB
            url = f"{TMDB_BASE_URL}/movie/{tmdb_id}"
            params = {'api_key': TMDB_API_KEY}
            response = requests.get(url, params=params)
            response.raise_for_status()

            movie_data = response.json()

            # Extract data
            title = movie_data.get('title', row.get('title', 'Unknown'))
            year = None
            if movie_data.get('release_date'):
                year = int(movie_data['release_date'].split('-')[0])

            overview = movie_data.get('overview', '')

            # Get IMDb ID from TMDB if not in our dataset
            if not imdb_id and movie_data.get('imdb_id'):
                imdb_id = movie_data['imdb_id']

            # Extract genres
            genres = [g['name'] for g in movie_data.get('genres', [])]

            # Fetch keywords
            keywords = []
            try:
                keywords_url = f"{TMDB_BASE_URL}/movie/{tmdb_id}/keywords"
                keywords_response = requests.get(keywords_url, params=params)
                keywords_response.raise_for_status()
                keywords_data = keywords_response.json()
                keywords = [k['name'] for k in keywords_data.get('keywords', [])]
            except Exception as e:
                print(f"  ⚠️  Could not fetch keywords: {e}")

            # Fetch credits (cast and crew)
            director = None
            cast = []
            try:
                credits_url = f"{TMDB_BASE_URL}/movie/{tmdb_id}/credits"
                credits_response = requests.get(credits_url, params=params)
                credits_response.raise_for_status()
                credits_data = credits_response.json()

                # Get director
                crew = credits_data.get('crew', [])
                directors = [c['name'] for c in crew if c.get('job') == 'Director']
                if directors:
                    director = directors[0]

                # Get top 5 cast members
                cast_list = credits_data.get('cast', [])
                cast = [c['name'] for c in cast_list[:5]]
            except Exception as e:
                print(f"  ⚠️  Could not fetch credits: {e}")

            vote_count = movie_data.get('vote_count', 0)
            vote_average = movie_data.get('vote_average', 0.0)
            budget = movie_data.get('budget', 0)

            # Insert into database
            insert_sql = text("""
                INSERT INTO movies (
                    title, year, overview,
                    tmdb_id, imdb_id, letterboxd_id,
                    genres, keywords,
                    director, cast,
                    tmdb_vote_count, tmdb_vote_average,
                    budget, watched_by_club,
                    data_source
                ) VALUES (
                    :title, :year, :overview,
                    :tmdb_id, :imdb_id, :letterboxd_id,
                    :genres, :keywords,
                    :director, :cast,
                    :vote_count, :vote_average,
                    :budget, 1,
                    'tmdb'
                )
            """)

            conn.execute(insert_sql, {
                'title': title,
                'year': year,
                'overview': overview,
                'tmdb_id': tmdb_id,
                'imdb_id': imdb_id,
                'letterboxd_id': letterboxd_id,
                'genres': json.dumps(genres),
                'keywords': json.dumps(keywords),
                'director': director,
                'cast': json.dumps(cast),
                'vote_count': vote_count,
                'vote_average': vote_average,
                'budget': budget
            })

            conn.commit()

            print(f"  ✓ Added: {title} ({year})")
            print(f"    TMDB: {tmdb_id}, IMDb: {imdb_id}, Letterboxd: {letterboxd_id}")
            print(f"    Genres: {', '.join(genres[:3])}")
            print(f"    Keywords: {len(keywords)}, Vote: {vote_average}/10 ({vote_count} votes)")

            fetched_count += 1

            # Rate limiting - be nice to TMDB API
            time.sleep(0.3)

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                print(f"  ❌ Movie not found in TMDB: {tmdb_id}")
            else:
                print(f"  ❌ HTTP Error: {e}")
            error_count += 1
            time.sleep(1)
        except Exception as e:
            print(f"  ❌ Error: {e}")
            error_count += 1
            time.sleep(1)

print("\n" + "=" * 70)
print("FETCH COMPLETE")
print("=" * 70)
print(f"Successfully fetched and added: {fetched_count}")
print(f"Errors: {error_count}")
print(f"Total processed: {len(missing_movies)}")

# Final verification
with engine.connect() as conn:
    result = conn.execute(text("SELECT COUNT(*) FROM movies WHERE watched_by_club = 1")).fetchone()
    total_watched = result[0]

    result = conn.execute(text("SELECT COUNT(*) FROM movies WHERE imdb_id IS NOT NULL")).fetchone()
    total_with_imdb = result[0]

    result = conn.execute(text("SELECT COUNT(*) FROM movies WHERE letterboxd_id IS NOT NULL")).fetchone()
    total_with_letterboxd = result[0]

    print(f"\nFinal database statistics:")
    print(f"  Horror club movies marked: {total_watched}")
    print(f"  Movies with IMDb ID: {total_with_imdb}")
    print(f"  Movies with Letterboxd ID: {total_with_letterboxd}")

if total_watched == len(horror_club_df):
    print(f"\n✅ All {len(horror_club_df)} horror club movies are now in the database!")
else:
    missing = len(horror_club_df) - total_watched
    print(f"\n⚠️  Still missing {missing} movies in database")
