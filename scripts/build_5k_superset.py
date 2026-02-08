import requests
import json
import time
from datetime import datetime

api_key = '8265bd1679663a7ea12ac168da84d2e8'

# Load existing horror profile
with open('/home/benunix/temp/horror_profile.json', 'r') as f:
    profile = json.load(f)

print(f"{'='*70}")
print(f"BUILDING ~5K HORROR SUPERSET WITH TIERED APPROACH")
print(f"{'='*70}")
print(f"Started: {datetime.now().strftime('%H:%M:%S')}")

# Tiered keyword strategy based on your collection's preferences
keyword_tiers = {
    'Tier 1 (Core taste - 10 pages)': {
        'slasher': 12339,
        'serial killer': 10714,
        'zombie': 12377,
        'found footage': 163053,
        'folk horror': 209568,
        'supernatural': 6152,
    },
    'Tier 2 (Strong interest - 7 pages)': {
        'occult': 156174,
        'demon': 15001,
        'lovecraftian': 287274,
        'haunted house': 3358,
        'creature': 13031,
        'body horror': 283085,
        'cult': 6158,
        'possession': 9712,
    },
    'Tier 3 (Nice to have - 5 pages)': {
        'ghost': 9823,
        'revenge': 4162,
        'ritual': 4720,
        'witch': 616,
        'monster': 2190,
        'gore': 10292,
    }
}

# Calculate total API calls
total_calls = (6 * 10) + (8 * 7) + (6 * 5)
print(f"\nEstimated API calls: {total_calls}")
print(f"Estimated time: ~{int(total_calls * 0.3 / 60)} minutes (with rate limiting)")
print(f"{'='*70}\n")

# Get keyword IDs (already have them, but let's verify they're correct)
# Using the IDs from previous analysis

discovered_movies = []
seen_ids = set()
api_call_count = 0

for tier_name, keywords in keyword_tiers.items():
    pages_to_fetch = 10 if 'Tier 1' in tier_name else (7 if 'Tier 2' in tier_name else 5)

    print(f"\n{'='*70}")
    print(f"{tier_name}")
    print(f"{'='*70}")

    for kw_name, kw_id in keywords.items():
        print(f"\n[{kw_name}] Fetching {pages_to_fetch} pages...", end='', flush=True)

        movies_found_this_keyword = 0

        for page in range(1, pages_to_fetch + 1):
            discover_url = f'https://api.themoviedb.org/3/discover/movie'
            params = {
                'api_key': api_key,
                'with_genres': 27,  # Horror (AND condition)
                'with_keywords': kw_id,
                'sort_by': 'vote_count.desc',
                'vote_count.gte': 10,  # Filter out ultra-obscure
                'page': page
            }

            try:
                response = requests.get(discover_url, params=params)
                api_call_count += 1
                data = response.json()
                movies = data.get('results', [])

                for movie in movies:
                    if movie['id'] not in seen_ids:
                        seen_ids.add(movie['id'])
                        movies_found_this_keyword += 1
                        discovered_movies.append({
                            'tmdb_id': movie['id'],
                            'title': movie['title'],
                            'year': movie.get('release_date', '')[:4],
                            'vote_average': movie.get('vote_average'),
                            'vote_count': movie.get('vote_count'),
                            'keyword': kw_name,
                            'tier': tier_name.split()[0] + ' ' + tier_name.split()[1]
                        })

                # Rate limiting: TMDB allows ~4 req/sec, we'll do 3.33 req/sec to be safe
                time.sleep(0.3)

                # Progress indicator
                if page % 3 == 0:
                    print('.', end='', flush=True)

            except Exception as e:
                print(f"\n  ❌ Error on page {page}: {e}")
                break

        print(f" ✓ {movies_found_this_keyword} new movies (total: {len(discovered_movies)})")

print(f"\n{'='*70}")
print(f"API CALLS MADE: {api_call_count}")
print(f"{'='*70}")

# Add your original collection
your_collection = profile['movie_data']
total_superset = len(your_collection) + len(discovered_movies)

print(f"\n{'='*70}")
print(f"SUPERSET SUMMARY")
print(f"{'='*70}")
print(f"Your collection:     {len(your_collection)} movies")
print(f"Newly discovered:    {len(discovered_movies)} unique movies")
print(f"TOTAL SUPERSET:      {total_superset} movies")

# Breakdown by tier
tier1_count = len([m for m in discovered_movies if 'Tier 1' in m['tier']])
tier2_count = len([m for m in discovered_movies if 'Tier 2' in m['tier']])
tier3_count = len([m for m in discovered_movies if 'Tier 3' in m['tier']])

print(f"\nBreakdown by tier:")
print(f"  Tier 1 (core):      {tier1_count} movies")
print(f"  Tier 2 (strong):    {tier2_count} movies")
print(f"  Tier 3 (nice):      {tier3_count} movies")

# Top 20 by vote count
print(f"\n{'='*70}")
print(f"TOP 20 DISCOVERED MOVIES (by vote count)")
print(f"{'='*70}")
sorted_by_votes = sorted(discovered_movies, key=lambda x: x['vote_count'], reverse=True)
for i, movie in enumerate(sorted_by_votes[:20], 1):
    print(f"{i:2}. {movie['title']} ({movie['year']}) - {movie['vote_average']}/10 "
          f"[{movie['keyword']}]")

# Save results
output = {
    'your_collection_count': len(your_collection),
    'discovered_count': len(discovered_movies),
    'total_superset_count': total_superset,
    'tier_breakdown': {
        'tier1': tier1_count,
        'tier2': tier2_count,
        'tier3': tier3_count
    },
    'api_calls_made': api_call_count,
    'discovered_movies': discovered_movies,
    'your_collection': your_collection
}

with open('/home/benunix/temp/horror_superset_5k.json', 'w') as f:
    json.dump(output, f, indent=2)

print(f"\n{'='*70}")
print(f"✓ Saved to: /home/benunix/temp/horror_superset_5k.json")
print(f"Completed: {datetime.now().strftime('%H:%M:%S')}")
print(f"{'='*70}")
