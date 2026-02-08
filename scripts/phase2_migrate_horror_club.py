"""
Phase 2: Migrate Horror Club Movies to New Schema
1. Copy 286 horror club movies to horror_movies table
2. Create watch records in horror_club_watches with list_entry_id
"""
import sqlite3
import pandas as pd
from pathlib import Path

project_root = Path(__file__).parent.parent
db_path = project_root / 'data' / 'horror_recommender.db'

print("=" * 70)
print("PHASE 2: MIGRATING HORROR CLUB MOVIES")
print("=" * 70)

# Load authoritative horror club list
csv_path = project_root / 'data' / 'horror_club_with_ids.csv'
horror_club_df = pd.read_csv(csv_path)

print(f"\n1. Loaded {len(horror_club_df)} horror club movies from CSV")

# Connect to database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Verify new tables exist
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='horror_movies'")
if not cursor.fetchone():
    print("\n❌ ERROR: New tables don't exist!")
    print("Run phase1_create_new_schema.py first")
    exit(1)

print("\n2. Migrating movies to horror_movies table...")

migrated = 0
skipped = 0
errors = []

for idx, row in horror_club_df.iterrows():
    tmdb_id = int(row['tmdb_id']) if pd.notna(row['tmdb_id']) else None

    if not tmdb_id:
        errors.append(f"Row {idx}: Missing TMDB ID for {row.get('title', 'Unknown')}")
        continue

    # Get additional metadata from old movies table
    cursor.execute("""
        SELECT title, year, director, genres, keywords, "cast", overview,
               tmdb_vote_count, tmdb_vote_average, tmdb_popularity,
               letterboxd_rating, letterboxd_review_count
        FROM movies
        WHERE tmdb_id = ?
    """, (tmdb_id,))

    movie_data = cursor.fetchone()

    if movie_data:
        # Use data from database
        title, year, director, genres, keywords, cast, overview, \
        vote_count, vote_avg, popularity, lb_rating, lb_reviews = movie_data
    else:
        # Use data from CSV (minimal)
        title = row.get('title', row.get('data-original-title', 'Unknown'))
        year = row.get('year')
        director = None
        genres = None
        keywords = None
        cast = None
        overview = None
        vote_count = 0
        vote_avg = None
        popularity = None
        lb_rating = None
        lb_reviews = 0

    try:
        cursor.execute("""
            INSERT INTO horror_movies (
                tmdb_id, imdb_id, letterboxd_id,
                title, year, director,
                genres, keywords, cast, overview,
                tmdb_vote_count, tmdb_vote_average, tmdb_popularity,
                letterboxd_rating, letterboxd_review_count,
                data_source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            tmdb_id,
            row.get('imdb_id'),
            row.get('film_slug'),
            title,
            year,
            director,
            genres,
            keywords,
            cast,
            overview,
            vote_count,
            vote_avg,
            popularity,
            lb_rating,
            lb_reviews,
            'horror_club'  # Source
        ))

        movie_id = cursor.lastrowid

        # Create watch record in horror_club_watches
        cursor.execute("""
            INSERT INTO horror_club_watches (
                movie_id,
                list_entry_id,
                data_object_id
            ) VALUES (?, ?, ?)
        """, (
            movie_id,
            idx + 1,  # list_entry_id = row number (watch order)
            row.get('data-object-id')
        ))

        migrated += 1

        if migrated % 50 == 0:
            print(f"  Migrated {migrated}/{len(horror_club_df)} movies...")

    except sqlite3.IntegrityError as e:
        skipped += 1
        errors.append(f"Row {idx}: {row.get('title', 'Unknown')} - {str(e)}")

conn.commit()

print(f"\n✓ Migration complete!")
print(f"  Migrated: {migrated}")
print(f"  Skipped: {skipped}")

if errors:
    print(f"\n⚠️  Errors ({len(errors)}):")
    for error in errors[:10]:
        print(f"    {error}")
    if len(errors) > 10:
        print(f"    ... and {len(errors) - 10} more")

# Verify migration
print("\n3. Verifying migration...")
cursor.execute("SELECT COUNT(*) FROM horror_movies WHERE data_source = 'horror_club'")
horror_count = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM horror_club_watches")
watch_count = cursor.fetchone()[0]

print(f"  horror_movies (horror_club): {horror_count}")
print(f"  horror_club_watches: {watch_count}")

# Show sample with watch order
print("\n4. Sample movies with watch order:")
cursor.execute("""
    SELECT
        hcw.list_entry_id,
        hm.title,
        hm.year,
        hm.tmdb_id
    FROM horror_club_watches hcw
    JOIN horror_movies hm ON hcw.movie_id = hm.id
    ORDER BY hcw.list_entry_id
    LIMIT 10
""")

print(f"\n  {'Order':<6} {'Title':<45} {'Year':<6} {'TMDB ID':<10}")
print("  " + "-" * 70)
for row in cursor.fetchall():
    order, title, year, tmdb = row
    year_str = str(year) if year else 'N/A'
    print(f"  {order:<6} {title[:44]:<45} {year_str:<6} {tmdb:<10}")

print("\n" + "=" * 70)
print("MIGRATION COMPLETE")
print("=" * 70)
print(f"\n✅ {migrated} horror club movies migrated")
print(f"✅ Watch order preserved (list_entry_id)")
print("\nNext step: Run phase3_expand_universe.py to add ~5,000 movies")

conn.close()
