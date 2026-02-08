"""
Phase 3c: Re-filter for HORROR ONLY (strict)
Thriller alone is not horror - must have "Horror" in genres
"""
import pandas as pd
from pathlib import Path

project_root = Path(__file__).parent.parent

print("=" * 70)
print("PHASE 3C: STRICT HORROR-ONLY FILTERING")
print("=" * 70)

# Load previously filtered data
filtered_path = project_root / 'data' / 'horror_universe_filtered.csv'
df = pd.read_csv(filtered_path)

print(f"\n1. Loaded {len(df):,} movies (Horror OR Thriller)")

# Filter for movies that MUST have "Horror" in genres
horror_only = df[df['genres'].str.contains('Horror', case=False, na=False)]

print(f"2. Filtered to {len(horror_only):,} movies (must contain 'Horror')")

# Show what we're excluding
excluded = df[~df['genres'].str.contains('Horror', case=False, na=False)]
print(f"\n3. Excluding {len(excluded):,} movies without 'Horror':")

# Sample of excluded movies
print("\n   Sample excluded movies (Thriller but not Horror):")
for i in range(min(20, len(excluded))):
    row = excluded.iloc[i]
    print(f"   ❌ {row['title']:45s} ({row['year']}) - {row['genres']}")

# Take top 5,000 by reviewer count
horror_only = horror_only.sort_values('reviewer_count', ascending=False).head(5000)

# Save
output_path = project_root / 'data' / 'horror_universe_final.csv'
horror_only.to_csv(output_path, index=False)

print(f"\n4. Saved top {len(horror_only):,} horror movies to: {output_path}")

# Statistics
print("\n" + "=" * 70)
print("FILTERING COMPLETE")
print("=" * 70)
print(f"Original (Horror OR Thriller):     5,000 movies")
print(f"Final (must include Horror):       {len(horror_only):,} movies")
print(f"Excluded (Thriller without Horror): {5000 - len(horror_only):,} movies")

# Reviewer count stats
print(f"\nReviewer count range:")
print(f"  Min:  {horror_only['reviewer_count'].min()} reviewers")
print(f"  Max:  {horror_only['reviewer_count'].max()} reviewers")
print(f"  Mean: {horror_only['reviewer_count'].mean():.1f} reviewers")

# Genre breakdown
print("\n5. Genre combinations (top 20):")
genre_counts = horror_only['genres'].value_counts()
for genres, count in genre_counts.head(20).items():
    print(f"  {genres:50s}: {count:,} movies")

# Show top movies
print(f"\nTop 20 HORROR movies by reviewer count:")
print(f"{'#':<4} {'Title':<45} {'Year':<6} {'Reviewers':<10} {'Genres':<40}")
print("-" * 110)

for i, (_, row) in enumerate(horror_only.head(20).iterrows(), 1):
    title = row['title'][:44]
    year = str(row['year']) if pd.notna(row['year']) else 'N/A'
    reviewers = row['reviewer_count']
    genres = row['genres'][:39]
    print(f"{i:<4} {title:<45} {year:<6} {reviewers:<10} {genres:<40}")

print("\n" + "=" * 70)
print("✅ STRICT HORROR-ONLY FILTER APPLIED")
print("=" * 70)
print("\nResult: Universe contains ONLY movies with 'Horror' in genres")
print("Thriller-only movies have been excluded")
