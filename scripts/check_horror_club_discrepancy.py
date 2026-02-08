"""
Check why database has 318 horror club movies but CSV has 286
"""
import pandas as pd
import sqlite3
from pathlib import Path

project_root = Path(__file__).parent.parent

print("=" * 70)
print("HORROR CLUB MOVIE COUNT DISCREPANCY")
print("=" * 70)

# Load authoritative CSV
csv_path = project_root / 'data' / 'horror_club_with_ids.csv'
csv_df = pd.read_csv(csv_path)
print(f"\n1. AUTHORITATIVE CSV: {len(csv_df)} movies")

# Load database
db_path = project_root / 'data' / 'horror_recommender.db'
conn = sqlite3.connect(db_path)

query = "SELECT id, title, tmdb_id, watched_by_club FROM movies WHERE watched_by_club = 1"
db_df = pd.read_sql(query, conn)
print(f"2. DATABASE (watched_by_club=1): {len(db_df)} movies")

print(f"\n3. DISCREPANCY: {len(db_df) - len(csv_df)} extra movies in database")

# Check for duplicates in database
print("\n4. CHECKING FOR DUPLICATES IN DATABASE:")
duplicate_titles = db_df[db_df.duplicated(subset=['title'], keep=False)]
if len(duplicate_titles) > 0:
    print(f"   Found {len(duplicate_titles)} rows with duplicate titles:")
    for title in duplicate_titles['title'].unique():
        matches = db_df[db_df['title'] == title]
        print(f"\n   '{title}':")
        for _, row in matches.iterrows():
            print(f"     ID: {row['id']}, TMDB: {row['tmdb_id']}")
else:
    print("   No duplicate titles found")

duplicate_tmdb = db_df[db_df.duplicated(subset=['tmdb_id'], keep=False)]
if len(duplicate_tmdb) > 0:
    print(f"\n   Found {len(duplicate_tmdb)} rows with duplicate TMDB IDs:")
    for tmdb_id in duplicate_tmdb['tmdb_id'].unique():
        matches = db_df[db_df['tmdb_id'] == tmdb_id]
        print(f"\n   TMDB ID {tmdb_id}:")
        for _, row in matches.iterrows():
            print(f"     ID: {row['id']}, Title: {row['title']}")
else:
    print("   No duplicate TMDB IDs found")

# Find movies in DB but not in CSV
print("\n5. MOVIES IN DATABASE BUT NOT IN AUTHORITATIVE CSV:")
csv_tmdb_ids = set(csv_df['tmdb_id'].dropna().astype(int))
db_tmdb_ids = set(db_df['tmdb_id'].dropna().astype(int))

extra_in_db = db_tmdb_ids - csv_tmdb_ids
if extra_in_db:
    print(f"   {len(extra_in_db)} movies in DB but not in CSV:")
    for tmdb_id in sorted(extra_in_db)[:20]:
        movie = db_df[db_df['tmdb_id'] == tmdb_id].iloc[0]
        print(f"     TMDB {tmdb_id}: {movie['title']}")
    if len(extra_in_db) > 20:
        print(f"     ... and {len(extra_in_db) - 20} more")
else:
    print("   All DB movies are in CSV")

# Find movies in CSV but not in DB
extra_in_csv = csv_tmdb_ids - db_tmdb_ids
if extra_in_csv:
    print(f"\n6. MOVIES IN CSV BUT NOT IN DATABASE:")
    print(f"   {len(extra_in_csv)} movies:")
    for tmdb_id in sorted(extra_in_csv)[:20]:
        movie = csv_df[csv_df['tmdb_id'] == tmdb_id].iloc[0]
        print(f"     TMDB {tmdb_id}: {movie['title']}")
    if len(extra_in_csv) > 20:
        print(f"     ... and {len(extra_in_csv) - 20} more")
else:
    print("   All CSV movies are in DB")

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"CSV (authoritative):     {len(csv_df)} movies")
print(f"Database (marked club):  {len(db_df)} movies")
print(f"Extra in DB:             {len(extra_in_db)}")
print(f"Missing from DB:         {len(extra_in_csv)}")

conn.close()
