"""
Phase 4: Match horror universe movies to TMDB API
Get TMDB ID and IMDb ID for all 3,654 movies
"""
import pandas as pd
import requests
import time
from pathlib import Path
from dotenv import load_dotenv
import os
from tqdm import tqdm

load_dotenv()

project_root = Path(__file__).parent.parent

TMDB_API_KEY = os.getenv('TMDB_API_KEY')
TMDB_BASE_URL = os.getenv('TMDB_API_BASE_URL', 'https://api.themoviedb.org/3')

print("=" * 70)
print("PHASE 4: MATCHING TO TMDB API")
print("=" * 70)

# Load complete universe
universe_path = project_root / 'data' / 'horror_universe_complete.csv'
df = pd.read_csv(universe_path)

print(f"\n1. Loaded {len(df):,} movies from complete universe")
print(f"   - {len(df[df['is_true_horror'] == True]):,} with Horror genre")
print(f"   - {len(df[df['is_true_horror'] == False]):,} without Horror genre")

# Add columns for IDs
df['tmdb_id'] = None
df['imdb_id'] = None
df['tmdb_match_score'] = None  # For debugging fuzzy matches

# Statistics
matched_count = 0
no_match_count = 0
api_error_count = 0

print(f"\n2. Matching movies to TMDB API...")

for idx, row in tqdm(df.iterrows(), total=len(df), desc="Matching"):
    title = row['title']
    year = row.get('year')

    if pd.isna(title):
        print(f"\n  ⚠️  No title for row {idx}, skipping")
        no_match_count += 1
        continue

    try:
        # Search TMDB API
        params = {
            'api_key': TMDB_API_KEY,
            'query': title,
            'include_adult': 'true'  # Horror movies might be flagged as adult
        }

        # Add year if available for better matching
        if pd.notna(year) and year != '':
            try:
                params['year'] = int(year)
            except (ValueError, TypeError):
                pass

        response = requests.get(
            f"{TMDB_BASE_URL}/search/movie",
            params=params,
            timeout=10
        )
        response.raise_for_status()

        data = response.json()
        results = data.get('results', [])

        if results:
            # Take first result (best match)
            best_match = results[0]
            tmdb_id = best_match.get('id')

            # Now get full movie details to get IMDb ID
            detail_response = requests.get(
                f"{TMDB_BASE_URL}/movie/{tmdb_id}",
                params={'api_key': TMDB_API_KEY},
                timeout=10
            )
            detail_response.raise_for_status()

            detail_data = detail_response.json()
            imdb_id = detail_data.get('imdb_id')

            df.at[idx, 'tmdb_id'] = tmdb_id
            df.at[idx, 'imdb_id'] = imdb_id
            df.at[idx, 'tmdb_match_score'] = best_match.get('vote_count', 0)  # Use vote count as quality indicator

            matched_count += 1

            # Rate limiting - TMDB allows 40 requests per 10 seconds
            time.sleep(0.26)  # ~3.8 requests/sec = safe

        else:
            no_match_count += 1
            tqdm.write(f"  ⚠️  No TMDB match for: {title} ({year})")

        # Save progress every 100 movies
        if (idx + 1) % 100 == 0:
            output_path = project_root / 'data' / 'horror_universe_with_ids.csv'
            df.to_csv(output_path, index=False)

    except requests.exceptions.RequestException as e:
        api_error_count += 1
        tqdm.write(f"  ❌ API error for {title}: {e}")
        time.sleep(2)  # Wait longer on errors
        continue
    except Exception as e:
        api_error_count += 1
        tqdm.write(f"  ❌ Error for {title}: {e}")
        continue

# Final save
output_path = project_root / 'data' / 'horror_universe_with_ids.csv'
df.to_csv(output_path, index=False)

print("\n" + "=" * 70)
print("TMDB MATCHING COMPLETE")
print("=" * 70)
print(f"Total movies:           {len(df):,}")
print(f"Successfully matched:   {matched_count:,} ({matched_count/len(df)*100:.1f}%)")
print(f"No match found:         {no_match_count:,}")
print(f"API errors:             {api_error_count:,}")
print(f"\nMovies with TMDB ID:    {df['tmdb_id'].notna().sum():,}")
print(f"Movies with IMDb ID:    {df['imdb_id'].notna().sum():,}")
print(f"Movies with both IDs:   {(df['tmdb_id'].notna() & df['imdb_id'].notna()).sum():,}")

# Show sample of unmatched movies
unmatched = df[df['tmdb_id'].isna()]
if len(unmatched) > 0:
    print(f"\nSample of unmatched movies ({len(unmatched)} total):")
    for _, row in unmatched.head(10).iterrows():
        year_str = f"({row['year']})" if pd.notna(row['year']) else ""
        print(f"  • {row['title']:50s} {year_str}")

print(f"\nSaved to: {output_path}")

# Breakdown by is_true_horror
print("\n" + "=" * 70)
print("BREAKDOWN BY HORROR CLASSIFICATION")
print("=" * 70)
true_horror = df[df['is_true_horror'] == True]
false_horror = df[df['is_true_horror'] == False]

print(f"\nTrue Horror (is_true_horror=True): {len(true_horror):,} movies")
print(f"  - Matched to TMDB: {true_horror['tmdb_id'].notna().sum():,} ({true_horror['tmdb_id'].notna().sum()/len(true_horror)*100:.1f}%)")

print(f"\nNon-Horror Club Movies (is_true_horror=False): {len(false_horror):,} movies")
print(f"  - Matched to TMDB: {false_horror['tmdb_id'].notna().sum():,} ({false_horror['tmdb_id'].notna().sum()/len(false_horror)*100:.1f}%)")
