"""
Download Letterboxd dataset from Hugging Face
847K movies with user reviews - the key for collaborative filtering
"""
from datasets import load_dataset
from pathlib import Path
import json
import pandas as pd
from tqdm import tqdm

project_root = Path(__file__).parent.parent

print("=" * 70)
print("DOWNLOADING LETTERBOXD DATASET")
print("=" * 70)
print("\nDataset: pkchwy/letterboxd-all-movie-data")
print("Size: ~1.12 GB (847K movies)")
print("Content: Movie metadata + user reviews with usernames\n")

# Create data directory
data_dir = project_root / 'data' / 'letterboxd'
data_dir.mkdir(exist_ok=True, parents=True)

print("Loading dataset from Hugging Face...")
print("(This may take a few minutes on first download)\n")

# Download dataset
dataset = load_dataset("pkchwy/letterboxd-all-movie-data")

print(f"✓ Dataset loaded: {len(dataset['train'])} movies\n")

# Save to local parquet for faster access
parquet_path = data_dir / 'letterboxd_full.parquet'
print(f"Saving to: {parquet_path}")

dataset['train'].to_parquet(parquet_path)

print(f"✓ Saved to parquet\n")

# Sample analysis
print("=" * 70)
print("DATASET ANALYSIS")
print("=" * 70)

# Load as DataFrame for analysis
df = pd.read_parquet(parquet_path)

print(f"\nTotal movies: {len(df):,}")
print(f"Movies with reviews: {df['reviews'].apply(lambda x: len(x) if isinstance(x, list) else 0).sum():,}")

# Count total reviews
total_reviews = 0
for reviews in df['reviews']:
    if isinstance(reviews, list):
        total_reviews += len(reviews)

print(f"Total reviews: {total_reviews:,}")
print(f"Average reviews per movie: {total_reviews / len(df):.1f}")

# Sample movie with reviews
movies_with_reviews = df[df['reviews'].apply(lambda x: isinstance(x, list) and len(x) > 0)]
sample = movies_with_reviews.iloc[0]

print(f"\nSample movie: {sample['title']} ({sample['year']})")
print(f"  Rating: {sample['rating']}")
print(f"  Reviews: {len(sample['reviews'])}")
if sample['reviews']:
    print(f"  Sample review usernames: {[r.get('username', 'N/A') for r in sample['reviews'][:5]]}")

print("\n" + "=" * 70)
print("DOWNLOAD COMPLETE")
print("=" * 70)
print(f"\nDataset saved to: {parquet_path}")
print(f"Size: {parquet_path.stat().st_size / (1024**3):.2f} GB")

print("\nNext steps:")
print("1. Extract user-movie review matrix")
print("2. Build collaborative filtering recommendations")
print("3. Combine with cosine similarity for hybrid approach")
