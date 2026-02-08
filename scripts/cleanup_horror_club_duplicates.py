"""
Clean up database to match authoritative horror club list EXACTLY
Remove the 32 duplicate entries, keep only the 286 movies from the CSV
"""
import pandas as pd
import sqlite3
from pathlib import Path

project_root = Path(__file__).parent.parent

print("=" * 70)
print("CLEANING UP HORROR CLUB DATABASE")
print("=" * 70)

# Load authoritative CSV
csv_path = project_root / 'data' / 'horror_club_with_ids.csv'
csv_df = pd.read_csv(csv_path)
authoritative_tmdb_ids = set(csv_df['tmdb_id'].dropna().astype(int))

print(f"\n1. AUTHORITATIVE LIST: {len(authoritative_tmdb_ids)} movies")

# Connect to database
db_path = project_root / 'data' / 'horror_recommender.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check current state
cursor.execute("SELECT COUNT(*) FROM movies WHERE watched_by_club = 1")
current_count = cursor.fetchone()[0]
print(f"2. CURRENT DATABASE: {current_count} movies marked as horror club")

# Get movies that will be unmarked
cursor.execute("""
    SELECT id, title, tmdb_id
    FROM movies
    WHERE watched_by_club = 1 AND tmdb_id NOT IN ({})
""".format(','.join(map(str, authoritative_tmdb_ids))))
to_unmark = cursor.fetchall()

print(f"\n3. MOVIES TO UNMARK: {len(to_unmark)} duplicates/extras")
if to_unmark:
    print("\n   Movies being removed from horror club:")
    for movie_id, title, tmdb_id in to_unmark:
        # Find which version is kept
        kept_version = csv_df[csv_df['title'].str.lower() == title.lower()]
        if len(kept_version) > 0:
            kept_tmdb = kept_version.iloc[0]['tmdb_id']
            print(f"   ✗ {title} (TMDB {tmdb_id}) - keeping TMDB {kept_tmdb} instead")
        else:
            print(f"   ✗ {title} (TMDB {tmdb_id}) - not in authoritative list")

# Step 1: Unmark ALL movies
print("\n4. STEP 1: Unmarking all movies...")
cursor.execute("UPDATE movies SET watched_by_club = 0")
unmarked = cursor.rowcount
print(f"   ✓ Unmarked {unmarked} movies")

# Step 2: Mark ONLY the authoritative 286
print("\n5. STEP 2: Marking authoritative 286 movies...")
marked_count = 0
missing_count = 0
missing_movies = []

for tmdb_id in authoritative_tmdb_ids:
    cursor.execute("""
        UPDATE movies
        SET watched_by_club = 1
        WHERE tmdb_id = ?
    """, (int(tmdb_id),))

    if cursor.rowcount > 0:
        marked_count += 1
    else:
        missing_count += 1
        # Get movie title from CSV
        movie = csv_df[csv_df['tmdb_id'] == tmdb_id].iloc[0]
        missing_movies.append((tmdb_id, movie['title']))

print(f"   ✓ Marked {marked_count} movies")

if missing_count > 0:
    print(f"\n   ⚠ WARNING: {missing_count} movies from CSV not found in database:")
    for tmdb_id, title in missing_movies[:10]:
        print(f"      TMDB {tmdb_id}: {title}")
    if missing_count > 10:
        print(f"      ... and {missing_count - 10} more")

# Commit changes
conn.commit()

# Verify final state
cursor.execute("SELECT COUNT(*) FROM movies WHERE watched_by_club = 1")
final_count = cursor.fetchone()[0]

print("\n" + "=" * 70)
print("CLEANUP COMPLETE")
print("=" * 70)
print(f"Before:  {current_count} movies marked as horror club")
print(f"After:   {final_count} movies marked as horror club")
print(f"Target:  {len(authoritative_tmdb_ids)} movies (authoritative list)")
print()

if final_count == len(authoritative_tmdb_ids):
    print("✅ SUCCESS! Database now matches authoritative list exactly.")
else:
    print(f"⚠️  WARNING: Database has {final_count} movies, expected {len(authoritative_tmdb_ids)}")
    if missing_count > 0:
        print(f"   {missing_count} movies from CSV are not in the database.")
        print("   You may need to fetch them from TMDB.")

conn.close()

print("\n" + "=" * 70)
print("NEXT STEPS")
print("=" * 70)
print("1. Restart the web server to reload the data")
print("2. Verify the movie count shows 286 (not 318)")
