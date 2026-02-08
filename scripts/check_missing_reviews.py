"""
Check which horror club movies don't have reviews in the Letterboxd dataset
"""
import pandas as pd
from pathlib import Path

project_root = Path(__file__).parent.parent

print("=" * 70)
print("HORROR CLUB MOVIES VS LETTERBOXD REVIEWS")
print("=" * 70)

# Load authoritative horror club list
horror_club_df = pd.read_csv(project_root / 'data' / 'horror_club_with_ids.csv')
print(f"\nTotal horror club movies: {len(horror_club_df)}")

# Load extracted reviews
reviews_df = pd.read_parquet(project_root / 'data' / 'user_overlap' / 'user_movie_reviews.parquet')
movies_with_reviews = set(reviews_df['movie_title'].unique())
print(f"Movies with reviews in Letterboxd dataset: {len(movies_with_reviews)}")

# Find movies without reviews
horror_club_titles_normalized = set(horror_club_df['title'].str.lower().str.strip())
missing_reviews = horror_club_titles_normalized - movies_with_reviews

print(f"\nMovies WITHOUT reviews: {len(missing_reviews)}")

if missing_reviews:
    print("\n" + "=" * 70)
    print("HORROR CLUB MOVIES WITH NO REVIEWS IN DATASET")
    print("=" * 70)

    # Get full info for missing movies
    missing_info = []
    for title in missing_reviews:
        movie_info = horror_club_df[horror_club_df['title'].str.lower().str.strip() == title]
        if not movie_info.empty:
            row = movie_info.iloc[0]
            missing_info.append({
                'title': row['title'],
                'year': row.get('year', 'N/A'),
                'tmdb_id': row.get('tmdb_id', 'N/A'),
                'imdb_id': row.get('imdb_id', 'N/A')
            })

    # Sort by title
    missing_info.sort(key=lambda x: x['title'])

    for i, movie in enumerate(missing_info, 1):
        print(f"{i:3d}. {movie['title']:50s} ({movie['year']})")

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"Authoritative list:     {len(horror_club_df)} movies")
print(f"With reviews:           {len(movies_with_reviews)} movies ({len(movies_with_reviews)/len(horror_club_df)*100:.1f}%)")
print(f"Without reviews:        {len(missing_reviews)} movies ({len(missing_reviews)/len(horror_club_df)*100:.1f}%)")
