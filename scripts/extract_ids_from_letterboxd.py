"""
Extract TMDB and IMDb IDs from Letterboxd pages
This script scrapes each Letterboxd URL to find the external IDs
"""
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import json
import re
from pathlib import Path

project_root = Path(__file__).parent.parent

# Load horror club letterboxd data
input_path = project_root / 'data' / 'horror_club_letterboxd.csv'
output_path = project_root / 'data' / 'horror_club_with_ids.csv'

df = pd.read_csv(input_path)
print(f"Loaded {len(df)} movies from horror club")

# Add columns for IDs
df['tmdb_id'] = None
df['imdb_id'] = None
df['title'] = None
df['year'] = None

# Extract IDs from each Letterboxd page
success_count = 0
error_count = 0

for idx, row in df.iterrows():
    url = row['URL']
    film_slug = row['film_slug']

    try:
        # Fetch the page
        print(f"\n[{idx+1}/{len(df)}] Fetching: {film_slug}")
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()

        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract title and year from the page
        # Look for film-poster or headline-1
        title_elem = soup.find('h1', class_='headline-1')
        if title_elem:
            df.at[idx, 'title'] = title_elem.get_text(strip=True)

        # Year is often in the <small> tag near the title
        year_elem = soup.find('small', class_='number')
        if year_elem:
            year_text = year_elem.get_text(strip=True)
            year_match = re.search(r'(\d{4})', year_text)
            if year_match:
                df.at[idx, 'year'] = int(year_match.group(1))

        # Look for TMDb link using the data-track-action attribute
        # Based on https://github.com/Tetrax-10/letterboxd-csv-imdb-tmdb-mapper
        tmdb_link = soup.find('a', attrs={'data-track-action': 'TMDB'})
        if tmdb_link:
            tmdb_href = tmdb_link.get('href', '')
            # Regex: /(movie|tv)\/(\d+)\//
            tmdb_match = re.search(r'/(movie|tv)/(\d+)/', tmdb_href)
            if tmdb_match:
                df.at[idx, 'tmdb_id'] = int(tmdb_match.group(2))
                print(f"  ✓ TMDB ID: {tmdb_match.group(2)} ({tmdb_match.group(1)})")

        # Look for IMDb link using the data-track-action attribute
        imdb_link = soup.find('a', attrs={'data-track-action': 'IMDb'})
        if imdb_link:
            imdb_href = imdb_link.get('href', '')
            # Regex: /\/title\/(tt\d+)\/?/
            imdb_match = re.search(r'/title/(tt\d+)/?', imdb_href)
            if imdb_match:
                df.at[idx, 'imdb_id'] = imdb_match.group(1)
                print(f"  ✓ IMDb ID: {imdb_match.group(1)}")

        if df.at[idx, 'tmdb_id'] or df.at[idx, 'imdb_id']:
            success_count += 1
        else:
            print(f"  ⚠️  No IDs found")
            error_count += 1

        # Be respectful with rate limiting
        time.sleep(1)

        # Save progress every 10 movies
        if (idx + 1) % 10 == 0:
            df.to_csv(output_path, index=False)
            print(f"\n💾 Progress saved ({idx+1}/{len(df)} processed)")

    except Exception as e:
        print(f"  ❌ Error: {e}")
        error_count += 1
        time.sleep(2)  # Wait longer on errors
        continue

# Final save
df.to_csv(output_path, index=False)

print("\n" + "="*70)
print("EXTRACTION COMPLETE")
print("="*70)
print(f"Total movies: {len(df)}")
print(f"Successfully extracted: {success_count}")
print(f"Movies with TMDB ID: {df['tmdb_id'].notna().sum()}")
print(f"Movies with IMDb ID: {df['imdb_id'].notna().sum()}")
print(f"Movies with both IDs: {(df['tmdb_id'].notna() & df['imdb_id'].notna()).sum()}")
print(f"Errors/missing: {error_count}")
print(f"\nSaved to: {output_path}")
