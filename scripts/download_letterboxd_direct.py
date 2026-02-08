"""
Download Letterboxd dataset directly from Hugging Face
Workaround for datasets library compatibility issues
"""
from pathlib import Path
import requests
from tqdm import tqdm
import pandas as pd

project_root = Path(__file__).parent.parent

print("=" * 70)
print("DOWNLOADING LETTERBOXD DATASET (DIRECT)")
print("=" * 70)
print("\nDataset: pkchwy/letterboxd-all-movie-data")
print("Size: ~1.12 GB (847K movies)")
print("Method: Direct download from Hugging Face\n")

# Create data directory
data_dir = project_root / 'data' / 'letterboxd'
data_dir.mkdir(exist_ok=True, parents=True)

# Direct URL to the JSONL file
url = "https://huggingface.co/datasets/pkchwy/letterboxd-all-movie-data/resolve/main/full_dump.jsonl"
output_path = data_dir / 'letterboxd_full.jsonl'

print(f"Downloading from: {url}")
print(f"Saving to: {output_path}\n")

# Download with progress bar
response = requests.get(url, stream=True)
total_size = int(response.headers.get('content-length', 0))

with open(output_path, 'wb') as f, tqdm(
    desc="Downloading",
    total=total_size,
    unit='B',
    unit_scale=True,
    unit_divisor=1024,
) as pbar:
    for chunk in response.iter_content(chunk_size=8192):
        if chunk:
            f.write(chunk)
            pbar.update(len(chunk))

print(f"\n✓ Download complete!")
print(f"File size: {output_path.stat().st_size / (1024**3):.2f} GB\n")

# Analyze dataset
print("=" * 70)
print("DATASET ANALYSIS")
print("=" * 70)

print("Loading JSONL file (this may take a minute)...")
df = pd.read_json(output_path, lines=True)

print(f"\nTotal movies: {len(df):,}")

# Count movies with reviews
movies_with_reviews = df[df['reviews'].apply(lambda x: isinstance(x, list) and len(x) > 0)]
print(f"Movies with reviews: {len(movies_with_reviews):,}")

# Count total reviews
total_reviews = 0
for reviews in df['reviews']:
    if isinstance(reviews, list):
        total_reviews += len(reviews)

print(f"Total reviews: {total_reviews:,}")
print(f"Average reviews per movie: {total_reviews / len(df):.1f}")

# Extract unique usernames
print("\nExtracting unique users...")
all_usernames = set()
for reviews in tqdm(df['reviews'], desc="Processing"):
    if isinstance(reviews, list):
        for review in reviews:
            if isinstance(review, dict) and 'username' in review:
                all_usernames.add(review['username'])

print(f"Unique users: {len(all_usernames):,}")

# Sample movie with reviews
if len(movies_with_reviews) > 0:
    sample = movies_with_reviews.iloc[0]
    print(f"\nSample movie: {sample['title']} ({sample['year']})")
    print(f"  Rating: {sample['rating']}")
    print(f"  Reviews: {len(sample['reviews'])}")
    if sample['reviews']:
        print(f"  Sample usernames: {[r.get('username', 'N/A') for r in sample['reviews'][:5]]}")

print("\n" + "=" * 70)
print("DOWNLOAD COMPLETE")
print("=" * 70)
print(f"\nDataset saved to: {output_path}")
print(f"Size: {output_path.stat().st_size / (1024**3):.2f} GB")
print(f"Movies: {len(df):,}")
print(f"Reviews: {total_reviews:,}")
print(f"Users: {len(all_usernames):,}")

print("\nNext steps:")
print("1. Build user-movie review matrix for horror club movies")
print("2. Find users who reviewed obscure horror")
print("3. Recommend based on user overlap")
