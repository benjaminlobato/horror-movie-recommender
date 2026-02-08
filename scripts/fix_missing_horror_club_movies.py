#!/usr/bin/env python3
"""
Fix the 4 missing horror club movies that were matched to wrong versions (remakes).

Problem:
- A Nightmare on Elm Street: Got 2010 remake instead of 1984 original
- Carrie: Got 2013 remake instead of 1976 original
- Haunt: Got 2013 version instead of 2019 version
- Nightmare at Shadow Woods: Got wrong metadata

Solution:
1. Get correct movie data from Letterboxd dataset
2. Delete wrong versions from database
3. Insert correct versions with proper metadata
4. Add to horror_club_watches table
"""

import json
import sqlite3
import pandas as pd

# The 4 problematic movies with their correct Letterboxd IDs and data
CORRECT_MOVIES = {
    'a-nightmare-on-elm-street': {
        'horror_club_list_entry_id': None,  # Will lookup
        'correct_tmdb': 377,
        'correct_imdb': 'tt0087800',
    },
    'carrie-1976': {
        'horror_club_list_entry_id': None,
        'correct_tmdb': 7340,
        'correct_imdb': 'tt0074285',
    },
    'haunt-2019': {
        'horror_club_list_entry_id': None,
        'correct_tmdb': 517116,  # NOT 146243!
        'correct_imdb': 'tt6535880',
    },
    'nightmare-at-shadow-woods': {
        'horror_club_list_entry_id': None,
        'correct_tmdb': 28264,
        'correct_imdb': 'tt0085253',
    }
}

print("=" * 70)
print("FIXING 4 MISSING HORROR CLUB MOVIES")
print("=" * 70)

# Step 1: Get list_entry_ids from horror club
print("\n1. Loading horror club list_entry_ids...")
club_df = pd.read_csv('data/horror_club_with_ids.csv')

for film_slug in CORRECT_MOVIES:
    match = club_df[club_df['film_slug'] == film_slug]
    if len(match) > 0:
        list_entry_id = match.iloc[0]['list_entry_id']
        CORRECT_MOVIES[film_slug]['horror_club_list_entry_id'] = list_entry_id
        print(f"  ✓ {film_slug}: list_entry_id = {list_entry_id}")

# Step 2: Extract metadata from Letterboxd dataset
print("\n2. Extracting metadata from Letterboxd dataset...")
letterboxd_data = {}

with open('data/letterboxd/letterboxd_full.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        movie = json.loads(line)
        # Extract letterboxd ID from URL
        url = movie.get('url', '')
        if '/film/' in url:
            film_id = url.split('/film/')[-1].rstrip('/')

            if film_id in CORRECT_MOVIES:
                letterboxd_data[film_id] = {
                    'title': movie.get('title', ''),
                    'year': movie.get('year', ''),
                    'directors': ', '.join(movie.get('directors', [])),
                    'genres': ', '.join(movie.get('genres', [])),
                    'cast': ', '.join(movie.get('cast', [])[:10]),
                    'synopsis': movie.get('synopsis', ''),
                    'rating': movie.get('rating', ''),
                    'poster_url': movie.get('poster_url', ''),
                }
                print(f"  ✓ Found: {film_id} - {letterboxd_data[film_id]['title']} ({letterboxd_data[film_id]['year']})")

# Step 3: Connect to database
print("\n3. Connecting to database...")
conn = sqlite3.connect('data/horror_recommender_v2.db')
cursor = conn.cursor()

# Step 4: Delete wrong versions
print("\n4. Deleting wrong versions...")
wrong_tmdb_ids = [377, 7340, 146243, 28264]

for tmdb_id in wrong_tmdb_ids:
    # Check what's there
    cursor.execute("SELECT title, year, letterboxd_id, data_source FROM horror_movies WHERE tmdb_id = ?", (tmdb_id,))
    existing = cursor.fetchone()
    if existing:
        print(f"  ✗ Deleting: {existing[0]} ({existing[1]}) - {existing[2]} [{existing[3]}]")
        cursor.execute("DELETE FROM horror_movies WHERE tmdb_id = ?", (tmdb_id,))

# Step 5: Insert correct versions
print("\n5. Inserting correct versions...")

for film_slug, data in CORRECT_MOVIES.items():
    tmdb_id = data['correct_tmdb']
    imdb_id = data['correct_imdb']
    list_entry_id = data['horror_club_list_entry_id']

    # Get metadata
    metadata = letterboxd_data.get(film_slug, {})

    if not metadata:
        print(f"  ⚠ WARNING: No Letterboxd data for {film_slug}, using minimal data")
        metadata = {
            'title': film_slug.replace('-', ' ').title(),
            'year': '',
            'directors': '',
            'genres': 'Horror',
            'cast': '',
            'synopsis': '',
            'rating': '',
            'poster_url': '',
        }

    # Convert year
    year_int = None
    if metadata['year']:
        try:
            year_int = int(metadata['year'])
        except:
            pass

    # Determine is_true_horror
    is_true_horror = 'Horror' in metadata.get('genres', '')

    # Insert into horror_movies
    cursor.execute("""
        INSERT INTO horror_movies (
            tmdb_id, imdb_id, letterboxd_id, title, year,
            director, genres, "cast", synopsis, rating, poster_url,
            data_source, is_true_horror
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        tmdb_id, imdb_id, film_slug, metadata['title'], year_int,
        metadata['directors'], metadata['genres'], metadata['cast'],
        metadata['synopsis'], metadata['rating'], metadata['poster_url'],
        'horror_club', is_true_horror
    ))

    movie_id = cursor.lastrowid
    print(f"  ✓ Inserted: {metadata['title']} ({year_int}) - movie_id: {movie_id}")

    # Insert into horror_club_watches
    if list_entry_id:
        cursor.execute("""
            INSERT INTO horror_club_watches (movie_id, list_entry_id)
            VALUES (?, ?)
        """, (movie_id, list_entry_id))
        print(f"    ✓ Added to horror_club_watches (list_entry_id: {list_entry_id})")

# Commit changes
conn.commit()

# Step 6: Verify
print("\n" + "=" * 70)
print("VERIFICATION")
print("=" * 70)

cursor.execute("SELECT COUNT(*) FROM horror_club_watches")
club_watch_count = cursor.fetchone()[0]
print(f"Horror club watches: {club_watch_count} (should be 286)")

cursor.execute("SELECT COUNT(*) FROM horror_movies WHERE data_source = 'horror_club'")
club_movie_count = cursor.fetchone()[0]
print(f"Horror club movies: {club_movie_count}")

# Check the 4 movies
print("\nThe 4 fixed movies:")
for film_slug in CORRECT_MOVIES:
    cursor.execute("""
        SELECT hm.title, hm.year, hm.tmdb_id, hm.data_source, hcw.list_entry_id
        FROM horror_movies hm
        LEFT JOIN horror_club_watches hcw ON hm.id = hcw.movie_id
        WHERE hm.letterboxd_id = ?
    """, (film_slug,))
    result = cursor.fetchone()
    if result:
        status = "✓" if result[4] is not None else "✗"
        print(f"  {status} {result[0]} ({result[1]}) - TMDB {result[2]} - {result[3]} - list_entry: {result[4]}")

conn.close()

print("\n" + "=" * 70)
print("DONE!")
print("=" * 70)
