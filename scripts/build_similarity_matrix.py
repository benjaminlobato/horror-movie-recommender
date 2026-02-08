"""
Build similarity matrix for horror movie recommendations
Fetches full metadata from TMDB and calculates cosine similarity
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
print(f"BUILDING SIMILARITY MATRIX FOR HORROR RECOMMENDER")
print(f"{'='*70}")
print(f"Started: {datetime.now().strftime('%H:%M:%S')}")

# Load the 2,000-movie superset
superset_path = project_root / 'data' / 'horror_superset_5k.json'
with open(superset_path, 'r') as f:
    superset = json.load(f)

# Combine your collection + discovered movies
your_movies = superset['your_collection']
discovered_movies = superset['discovered_movies']

# Create list of all TMDB IDs to fetch
all_movies = []
seen_ids = set()

# Add your collection
for movie in your_movies:
    if movie['tmdb_id'] not in seen_ids:
        all_movies.append(movie['tmdb_id'])
        seen_ids.add(movie['tmdb_id'])

# Add discovered movies
for movie in discovered_movies:
    if movie['tmdb_id'] not in seen_ids:
        all_movies.append(movie['tmdb_id'])
        seen_ids.add(movie['tmdb_id'])

print(f"\nTotal unique movies to process: {len(all_movies)}")
print(f"Estimated time: ~{int(len(all_movies) * 0.3 / 60)} minutes")
print(f"{'='*70}\n")

# Fetch full metadata for each movie
movie_data = []
api_calls = 0
errors = 0

print("Fetching metadata from TMDB...")
for idx, tmdb_id in enumerate(all_movies, 1):
    try:
        # Use append_to_response to get everything in one call
        url = f'https://api.themoviedb.org/3/movie/{tmdb_id}'
        params = {
            'api_key': api_key,
            'append_to_response': 'keywords,credits'
        }

        response = requests.get(url, params=params)
        api_calls += 1
        data = response.json()

        # Extract keywords
        keywords = [kw['name'] for kw in data.get('keywords', {}).get('keywords', [])]

        # Extract genres
        genres = [g['name'] for g in data.get('genres', [])]

        # Extract cast (top 3)
        cast = [c['name'] for c in data.get('credits', {}).get('cast', [])[:3]]

        # Extract director
        crew = data.get('credits', {}).get('crew', [])
        director = [c['name'] for c in crew if c.get('job') == 'Director']

        # Store movie data
        movie_data.append({
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
        })

        # Progress indicator
        if idx % 50 == 0:
            print(f"  [{idx}/{len(all_movies)}] Processed {idx} movies... "
                  f"(API calls: {api_calls}, errors: {errors})")

        # Rate limiting
        time.sleep(0.3)

    except Exception as e:
        errors += 1
        print(f"  ❌ Error fetching {tmdb_id}: {e}")
        continue

print(f"\n✓ Fetched metadata for {len(movie_data)} movies")
print(f"  API calls: {api_calls}, Errors: {errors}")

# Process data following FedunAnton's approach
print(f"\n{'='*70}")
print("PROCESSING DATA...")
print(f"{'='*70}")

df = pd.DataFrame(movie_data)

# Remove spaces from keywords, genres, cast, director (for better matching)
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

# Create new dataframe with just essentials
movies_df = df[['tmdb_id', 'title', 'year', 'vote_count', 'vote_average', 'budget']].copy()
movies_df['tags'] = df['tags'].apply(lambda x: ' '.join(x))

print(f"✓ Processed {len(movies_df)} movies")
print(f"  Sample tags for '{movies_df.iloc[0]['title']}':")
print(f"  {movies_df.iloc[0]['tags'][:200]}...")

# Build similarity matrix
print(f"\n{'='*70}")
print("CALCULATING SIMILARITY MATRIX...")
print(f"{'='*70}")

# Use CountVectorizer (5000 features, remove English stop words)
cv = CountVectorizer(max_features=5000, stop_words='english')
vectors = cv.fit_transform(movies_df['tags']).toarray()

print(f"✓ Created feature vectors: {vectors.shape}")

# Calculate cosine similarity
similarity = cosine_similarity(vectors)

print(f"✓ Calculated similarity matrix: {similarity.shape}")
print(f"  Matrix size: {similarity.nbytes / (1024*1024):.1f} MB")

# Save results
print(f"\n{'='*70}")
print("SAVING RESULTS...")
print(f"{'='*70}")

output_dir = project_root / 'data'

# Save processed movies
movies_path = output_dir / 'movies_processed.pkl'
with open(movies_path, 'wb') as f:
    pickle.dump(movies_df, f)
print(f"✓ Saved: {movies_path}")

# Save similarity matrix
similarity_path = output_dir / 'similarity_matrix.pkl'
with open(similarity_path, 'wb') as f:
    pickle.dump(similarity, f)
print(f"✓ Saved: {similarity_path}")

# Test the system with Bad Ben
print(f"\n{'='*70}")
print("TESTING WITH BAD BEN...")
print(f"{'='*70}")

bad_ben_matches = movies_df[movies_df['title'].str.contains('Bad Ben', case=False, na=False)]

if len(bad_ben_matches) > 0:
    bad_ben_idx = bad_ben_matches.index[0]
    bad_ben_title = movies_df.iloc[bad_ben_idx]['title']

    print(f"Found: {bad_ben_title} (index: {bad_ben_idx})")

    # Get similarity scores for Bad Ben
    distances = sorted(list(enumerate(similarity[bad_ben_idx])),
                      reverse=True, key=lambda x: x[1])

    print(f"\nTop 10 recommendations for '{bad_ben_title}':")
    print(f"{'-'*70}")
    for i, (idx, score) in enumerate(distances[1:11], 1):
        movie = movies_df.iloc[idx]
        print(f"{i:2}. {movie['title']} ({movie['year']}) - "
              f"Score: {score:.3f}, Votes: {movie['vote_count']}")
else:
    print("Bad Ben not found in dataset")

print(f"\n{'='*70}")
print(f"✓ COMPLETE!")
print(f"Finished: {datetime.now().strftime('%H:%M:%S')}")
print(f"{'='*70}")
