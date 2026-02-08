import requests
import json

api_key = '8265bd1679663a7ea12ac168da84d2e8'

# Load the horror profile to get keyword IDs
with open('/home/benunix/temp/horror_profile.json', 'r') as f:
    profile = json.load(f)

# Key keywords we care about
focus_keywords = {
    'found footage': 163053,
    'slasher': 12339,
    'folk horror': 209568,
    'serial killer': 10714,
    'zombie': 12377,
    'gore': 10292,
    'supernatural': 6152,
    'haunted house': 3358,
    'body horror': 283085,
    'occult': 156174,
    'demon': 15001,
    'lovecraftian': 287274,
    'cult': 6158,
    'possession': 9712,
}

print(f"{'='*70}")
print(f"KEYWORD AVAILABILITY ON TMDB (Horror genre only)")
print(f"{'='*70}")
print(f"{'Keyword':<20} {'ID':<10} {'Total Movies':<15} {'We Fetched':<15}")
print(f"{'-'*70}")

total_available = 0
total_fetched = 0

for kw_name, kw_id in focus_keywords.items():
    # Query first page to get total_results
    discover_url = f'https://api.themoviedb.org/3/discover/movie'
    params = {
        'api_key': api_key,
        'with_genres': 27,  # Horror
        'with_keywords': kw_id,
        'sort_by': 'vote_count.desc',
        'vote_count.gte': 10,
        'page': 1
    }

    try:
        response = requests.get(discover_url, params=params)
        data = response.json()
        total_results = data.get('total_results', 0)
        total_pages = data.get('total_pages', 0)

        fetched = min(60, total_results)  # We fetched 3 pages = 60 movies max

        total_available += total_results
        total_fetched += fetched

        print(f"{kw_name:<20} {kw_id:<10} {total_results:<15} {fetched:<15}")

    except Exception as e:
        print(f"{kw_name:<20} {kw_id:<10} ERROR")

print(f"{'-'*70}")
print(f"{'TOTALS':<20} {'':<10} {total_available:<15} {total_fetched:<15}")
print(f"{'='*70}")

print(f"\nNOTE: These totals have overlap (same movie can have multiple keywords)")
print(f"\nTO REACH ~5,000 UNIQUE MOVIES:")
print(f"  Current approach (20 keywords × 3 pages): ~1,071 unique")
print(f"  Suggested: Increase to 5-10 pages per keyword")
print(f"  OR: Add more keywords from 90th percentile")
