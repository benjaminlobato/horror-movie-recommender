"""
Update database with proper IDs from authoritative Letterboxd dataset
NO FUZZY MATCHING - only exact ID mapping
"""
import pandas as pd
from sqlalchemy import create_engine, text
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

project_root = Path(__file__).parent.parent

# Load authoritative horror club data with proper IDs
horror_club_path = project_root / 'data' / 'horror_club_with_ids.csv'
horror_club_df = pd.read_csv(horror_club_path)

print("=" * 70)
print("UPDATING DATABASE WITH AUTHORITATIVE IDS")
print("=" * 70)
print(f"\nLoaded {len(horror_club_df)} horror club movies with proper IDs")

# Connect to database
engine = create_engine(os.getenv('DATABASE_URL'))

# Statistics
updated_count = 0
new_count = 0
already_exists_count = 0

with engine.connect() as conn:
    for idx, row in horror_club_df.iterrows():
        tmdb_id = int(row['tmdb_id']) if pd.notna(row['tmdb_id']) else None
        imdb_id = row['imdb_id'] if pd.notna(row['imdb_id']) else None
        letterboxd_url = row['URL'] if pd.notna(row['URL']) else None
        film_slug = row['film_slug'] if pd.notna(row['film_slug']) else None
        title = row['title'] if pd.notna(row['title']) else row['data-original-title']

        # Extract year from data-original-title if year column is empty
        year = None
        if pd.notna(row.get('year')) and row['year'] != '':
            try:
                year = int(row['year'])
            except (ValueError, TypeError):
                pass

        if year is None:
            # Try to extract from data-original-title (e.g., "Bad Ben (2016) ")
            import re
            title_with_year = row['data-original-title']
            year_match = re.search(r'\((\d{4})\)', title_with_year)
            if year_match:
                year = int(year_match.group(1))

        if not tmdb_id:
            print(f"  ⚠️  Skipping {title} - no TMDB ID")
            continue

        # Check if movie already exists in database
        result = conn.execute(
            text('SELECT id, title, watched_by_club FROM movies WHERE tmdb_id = :tmdb_id'),
            {'tmdb_id': tmdb_id}
        ).fetchone()

        if result:
            # Movie exists - update it
            movie_id, db_title, watched_by_club = result

            update_sql = text("""
                UPDATE movies SET
                    imdb_id = :imdb_id,
                    letterboxd_id = :letterboxd_id,
                    watched_by_club = 1,
                    updated_at = datetime('now')
                WHERE tmdb_id = :tmdb_id
            """)

            conn.execute(update_sql, {
                'tmdb_id': tmdb_id,
                'imdb_id': imdb_id,
                'letterboxd_id': film_slug
            })

            if watched_by_club:
                already_exists_count += 1
                print(f"  ✓ Already marked: {title} (TMDB: {tmdb_id})")
            else:
                updated_count += 1
                print(f"  ✓ Updated: {title} (TMDB: {tmdb_id}, IMDb: {imdb_id})")
        else:
            # Movie doesn't exist - we'll need to fetch it from TMDB API later
            new_count += 1
            print(f"  ⚠️  Not in DB: {title} (TMDB: {tmdb_id}) - needs TMDB fetch")

    conn.commit()

print("\n" + "=" * 70)
print("UPDATE COMPLETE")
print("=" * 70)
print(f"Movies already marked as watched: {already_exists_count}")
print(f"Movies updated with IDs: {updated_count}")
print(f"Movies not in DB (need TMDB fetch): {new_count}")
print(f"Total horror club movies: {len(horror_club_df)}")

# Verify
with engine.connect() as conn:
    result = conn.execute(text("SELECT COUNT(*) FROM movies WHERE watched_by_club = 1")).fetchone()
    total_watched = result[0]

    result = conn.execute(text("SELECT COUNT(*) FROM movies WHERE imdb_id IS NOT NULL")).fetchone()
    total_with_imdb = result[0]

    result = conn.execute(text("SELECT COUNT(*) FROM movies WHERE letterboxd_id IS NOT NULL")).fetchone()
    total_with_letterboxd = result[0]

    print(f"\nDatabase statistics:")
    print(f"  Horror club movies marked: {total_watched}")
    print(f"  Movies with IMDb ID: {total_with_imdb}")
    print(f"  Movies with Letterboxd ID: {total_with_letterboxd}")

if new_count > 0:
    print(f"\n⚠️  Next step: Fetch {new_count} missing movies from TMDB API")
