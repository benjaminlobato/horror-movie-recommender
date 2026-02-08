"""
Build similarity matrix with metadata caching
Saves raw TMDB metadata so we don't need to re-fetch on subsequent runs
"""
import pandas as pd
import pickle
import requests
import json
import time
from datetime import datetime
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import os
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv('TMDB_API_KEY')
project_root = Path(__file__).parent.parent

print(f"{'='*70}")
print(f"BUILDING SIMILARITY MATRIX (WITH CACHING)")
print(f"{'='*70}")
print(f"Started: {datetime.now().strftime('%H:%M:%S')}")

# Load the 2,000-movie superset
superset_path = project_root / 'data' / 'horror_superset_5k.json'
with open(superset_path, 'r') as f:
    superset = json.load(f)

# Get list of all TMDB IDs
your_movies = superset['your_collection']
discovered_movies = superset['discovered_movies']

all_movie_ids = set()
for movie in your_movies:
    all_movie_ids.add(movie['tmdb_id'])
for movie in discovered_movies:
    all_movie_ids.add(movie['tmdb_id'])

all_movie_ids = sorted(list(all_movie_ids))
print(f"\nTotal unique movie IDs: {len(all_movie_ids)}")

# Check if cached metadata exists
cache_path = project_root / 'data' / 'movies_metadata_raw.json'
cached_metadata = {}

if cache_path.exists():
    print(f"\n✓ Found cached metadata: {cache_path}")
    with open(cache_path, 'r') as f:
        cached_data = json.load(f)
        cached_metadata = {m['tmdb_id']: m for m in cached_data}
    print(f"  Cached movies: {len(cached_metadata)}")

# Find movies we still need to fetch
movies_to_fetch = [mid for mid in all_movie_ids if mid not in cached_metadata]
print(f"  Movies to fetch: {len(movies_to_fetch)}")

# Fetch missing metadata
movie_data = list(cached_metadata.values())
api_calls = 0
errors = 0

if movies_to_fetch:
    print(f"\nFetching metadata from TMDB...")
    print(f"Estimated time: ~{int(len(movies_to_fetch) * 0.3 / 60)} minutes")

    for idx, tmdb_id in enumerate(movies_to_fetch, 1):
        try:
            url = f'https://api.themoviedb.org/3/movie/{tmdb_id}'
            params = {
                'api_key': api_key,
                'append_to_response': 'keywords,credits'
            }

            response = requests.get(url, params=params)
            api_calls += 1
            data = response.json()

            # Extract and store raw metadata
            keywords = [kw['name'] for kw in data.get('keywords', {}).get('keywords', [])]
            genres = [g['name'] for g in data.get('genres', [])]
            cast = [c['name'] for c in data.get('credits', {}).get('cast', [])[:3]]
            crew = data.get('credits', {}).get('crew', [])
            director = [c['name'] for c in crew if c.get('job') == 'Director']

            movie_info = {
                'tmdb_id': tmdb_id,
                'title': data.get('title'),
                'year': data.get('release_date', '')[:4],
                'overview': data.get('overview', ''),
                'keywords': keywords,
                'genres': genres,
                'cast': cast,
                'director': director,
                'vote_count': data.get('vote_count', 0),
                'vote_average': data.get('vote_average', 0),
                'budget': data.get('budget', 0)
            }

            movie_data.append(movie_info)

            # Progress indicator
            if idx % 50 == 0:
                print(f"  [{idx}/{len(movies_to_fetch)}] Fetched {idx} movies...")

            # Rate limiting
            time.sleep(0.3)

        except Exception as e:
            errors += 1
            print(f"  ❌ Error fetching {tmdb_id}: {e}")
            continue

    print(f"\n✓ Fetched {len(movies_to_fetch)} new movies")
    print(f"  API calls: {api_calls}, Errors: {errors}")

    # Save updated cache
    print(f"\n💾 Saving metadata cache...")
    with open(cache_path, 'w') as f:
        json.dump(movie_data, f, indent=2)
    print(f"✓ Cached {len(movie_data)} movies to: {cache_path}")
else:
    print(f"\n✓ All movies already cached! No API calls needed.")

# Process data
print(f"\n{'='*70}")
print("PROCESSING DATA...")
print(f"{'='*70}")

df = pd.DataFrame(movie_data)

# Remove spaces from keywords, genres, cast, director
def remove_spaces(items):
    return [item.replace(' ', '') for item in items]

df['keywords'] = df['keywords'].apply(remove_spaces)
df['genres'] = df['genres'].apply(remove_spaces)
df['cast'] = df['cast'].apply(remove_spaces)
df['director'] = df['director'].apply(remove_spaces)

# Tokenize overview
df['overview'] = df['overview'].fillna('')
df['overview'] = df['overview'].apply(lambda x: x.split())

# Combine all features into 'tags'
df['tags'] = df['overview'] + df['genres'] + df['keywords'] + df['cast'] + df['director']

# Create processed dataframe
movies_df = df[['tmdb_id', 'title', 'year', 'vote_count', 'vote_average', 'budget']].copy()
movies_df['tags'] = df['tags'].apply(lambda x: ' '.join(x))

print(f"✓ Processed {len(movies_df)} movies")

# Build similarity matrix
print(f"\n{'='*70}")
print("CALCULATING SIMILARITY MATRIX...")
print(f"{'='*70}")

cv = CountVectorizer(max_features=5000, stop_words='english')
vectors = cv.fit_transform(movies_df['tags']).toarray()

print(f"✓ Created feature vectors: {vectors.shape}")

similarity = cosine_similarity(vectors)

print(f"✓ Calculated similarity matrix: {similarity.shape}")
print(f"  Matrix size: {similarity.nbytes / (1024*1024):.1f} MB")

# Save results
print(f"\n{'='*70}")
print("SAVING RESULTS...")
print(f"{'='*70}")

output_dir = project_root / 'data'

movies_path = output_dir / 'movies_processed.pkl'
with open(movies_path, 'wb') as f:
    pickle.dump(movies_df, f)
print(f"✓ Saved: {movies_path}")

similarity_path = output_dir / 'similarity_matrix.pkl'
with open(similarity_path, 'wb') as f:
    pickle.dump(similarity, f)
print(f"✓ Saved: {similarity_path}")

# Test with Bad Ben
print(f"\n{'='*70}")
print("TESTING...")
print(f"{'='*70}")

# Search for Bad Ben (any variant)
bad_ben_matches = movies_df[movies_df['title'].str.contains('Bad Ben', case=False, na=False)]

if len(bad_ben_matches) > 0:
    print(f"\nFound {len(bad_ben_matches)} Bad Ben movies:")
    for idx, row in bad_ben_matches.iterrows():
        print(f"  - {row['title']} ({row['year']}) - votes: {row['vote_count']}")

    # Test with first one
    bad_ben_idx = bad_ben_matches.index[0]
    bad_ben_title = movies_df.iloc[bad_ben_idx]['title']

    distances = sorted(list(enumerate(similarity[bad_ben_idx])),
                      reverse=True, key=lambda x: x[1])

    print(f"\nTop 10 recommendations for '{bad_ben_title}':")
    print(f"{'-'*70}")
    for i, (idx, score) in enumerate(distances[1:11], 1):
        movie = movies_df.iloc[idx]
        print(f"{i:2}. {movie['title']} ({movie['year']}) - "
              f"Score: {score:.3f}, Votes: {movie['vote_count']}")

print(f"\n{'='*70}")
print(f"✓ COMPLETE!")
print(f"Finished: {datetime.now().strftime('%H:%M:%S')}")
print(f"{'='*70}")
print(f"\nNext run will use cached metadata - no API calls needed!")
