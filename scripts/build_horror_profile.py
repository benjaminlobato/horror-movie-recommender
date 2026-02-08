import pandas as pd
import requests
from collections import Counter
import json
import time

# Load your movie list
movies_df = pd.read_csv('/home/benunix/projects/movie-night/scripts/movies.csv', encoding='utf-8-sig')
print(f"Loaded {len(movies_df)} movies from your list")

# TMDB API key
api_key = '8265bd1679663a7ea12ac168da84d2e8'

# Function to search TMDB for movie and get its ID + keywords
def get_movie_keywords(title, release_year=None):
    # Search for movie
    search_url = f'https://api.themoviedb.org/3/search/movie?api_key={api_key}&query={title}'
    if release_year:
        search_url += f'&year={release_year}'

    try:
        response = requests.get(search_url)
        results = response.json().get('results', [])

        if not results:
            print(f"  ❌ Not found: {title}")
            return None

        movie_id = results[0]['id']

        # Get keywords for this movie
        keywords_url = f'https://api.themoviedb.org/3/movie/{movie_id}/keywords?api_key={api_key}'
        kw_response = requests.get(keywords_url)
        keywords = kw_response.json().get('keywords', [])

        keyword_names = [kw['name'] for kw in keywords]

        # Also get genres
        movie_url = f'https://api.themoviedb.org/3/movie/{movie_id}?api_key={api_key}'
        movie_response = requests.get(movie_url)
        movie_data = movie_response.json()
        genres = [g['name'] for g in movie_data.get('genres', [])]

        return {
            'tmdb_id': movie_id,
            'title': movie_data.get('title'),
            'keywords': keyword_names,
            'genres': genres,
            'vote_average': movie_data.get('vote_average'),
            'budget': movie_data.get('budget', 0)
        }
    except Exception as e:
        print(f"  ❌ Error for {title}: {e}")
        return None

# Fetch keywords for all movies
all_keywords = []
movie_data_list = []

print("\nFetching keywords from TMDB...")
for idx, row in movies_df.iterrows():
    title = row['Title']

    # Parse release year from date (format appears to be MM-DD-YY)
    try:
        release_date = str(row['ReleaseDate'])
        # Try to parse year (could be various formats)
        year = None
        if len(release_date.split('-')) == 3:
            year_part = release_date.split('-')[2]
            if len(year_part) == 2:
                year = int('19' + year_part if int(year_part) > 50 else '20' + year_part)
            elif len(year_part) == 4:
                year = int(year_part)
    except:
        year = None

    print(f"[{idx+1}/{len(movies_df)}] {title} ({year if year else 'unknown year'})...", end='')

    movie_data = get_movie_keywords(title, year)

    if movie_data:
        print(f" ✓ Found {len(movie_data['keywords'])} keywords")
        all_keywords.extend(movie_data['keywords'])
        movie_data_list.append(movie_data)
    else:
        print()

    # Rate limiting
    time.sleep(0.3)

# Count keyword frequencies
keyword_counts = Counter(all_keywords)

print(f"\n{'='*60}")
print(f"KEYWORD ANALYSIS")
print(f"{'='*60}")
print(f"Total movies processed: {len(movie_data_list)}")
print(f"Total keyword occurrences: {len(all_keywords)}")
print(f"Unique keywords: {len(keyword_counts)}")

# Calculate 90th percentile
counts_sorted = sorted(keyword_counts.values())
percentile_90_idx = int(len(counts_sorted) * 0.90)
percentile_90_threshold = counts_sorted[percentile_90_idx] if counts_sorted else 0

print(f"\n90th Percentile Threshold: {percentile_90_threshold} occurrences")

# Get keywords at or above 90th percentile
top_keywords = {k: v for k, v in keyword_counts.items() if v >= percentile_90_threshold}

print(f"\nTop {len(top_keywords)} keywords (≥ {percentile_90_threshold} occurrences):")
print(f"{'='*60}")
for keyword, count in sorted(top_keywords.items(), key=lambda x: x[1], reverse=True):
    print(f"  {keyword}: {count}")

# Check for specific keywords
print(f"\n{'='*60}")
print("CHECKING KEY HORROR SUBGENRES:")
print(f"{'='*60}")
check_keywords = ['found footage', 'folk horror', 'slasher', 'haunted house', 'paranormal']
for kw in check_keywords:
    count = keyword_counts.get(kw, 0)
    in_top = '✓ IN 90TH PERCENTILE' if count >= percentile_90_threshold else '✗ Below threshold'
    print(f"  '{kw}': {count} occurrences {in_top}")

# Save results
output = {
    'total_movies': len(movie_data_list),
    'unique_keywords': len(keyword_counts),
    'percentile_90_threshold': percentile_90_threshold,
    'top_keywords': dict(sorted(top_keywords.items(), key=lambda x: x[1], reverse=True)),
    'all_keyword_counts': dict(sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)),
    'movie_data': movie_data_list
}

with open('/home/benunix/temp/horror_profile.json', 'w') as f:
    json.dump(output, f, indent=2)

print(f"\n{'='*60}")
print(f"✓ Saved to: /home/benunix/temp/horror_profile.json")
print(f"{'='*60}")
