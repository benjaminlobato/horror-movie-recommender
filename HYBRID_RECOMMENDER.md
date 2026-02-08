# Hybrid Horror Movie Recommender

## Overview

A recommendation system that combines **collaborative filtering** (user overlap) with **content-based filtering** (metadata similarity) to find hidden gem horror movies that actual fans loved.

## Why Hybrid?

**Problem with pure cosine similarity:**
- Recommends superficially similar movies based on keywords/genres
- Example: "Bad Ben" → "Oppenheimer" (both tagged as "dramatic")
- Misses the nuance of what horror fans actually enjoy

**Solution: Hybrid approach**
- Primary signal: User overlap (people who loved X also loved Y)
- Filter: Content similarity (ensure recommendations are actually horror)
- Result: Hidden gems that horror enthusiasts genuinely appreciate

## Architecture

### Data Sources

1. **Letterboxd Dataset** (1.1GB, 847K movies)
   - User reviews with usernames
   - Extracted 4,115 reviews from 2,112 users
   - Focused on 286 horror club movies

2. **TMDB Metadata**
   - Genres, keywords, cast, director
   - Used for content similarity calculation

### Algorithm

```
For target movie M:
  1. Find users U who reviewed M
  2. Get all other movies {C} those users reviewed
  3. For each candidate movie C:
     a. Count user overlap (how many users reviewed both M and C)
     b. Compute content similarity (TF-IDF cosine similarity on metadata)
     c. Filter: Keep only if content_similarity > threshold (default 0.1)
     d. Score: (normalized_user_count × 0.7) + (content_similarity × 0.3)
  4. Return top N by hybrid score
```

### Weights

- **User overlap: 70%** - Primary signal of actual fan taste
- **Content similarity: 30%** - Filter to keep recommendations horror-relevant

## Results

### Bad Ben (Obscure Found Footage)
- **Input:** 10 users reviewed it
- **Top recommendations:**
  1. WNUF Halloween Special (found footage mockumentary)
  2. Noroi: The Curse (Japanese found footage)
  3. Horror in the High Desert (found footage)
  4. Hell House LLC (found footage)

✅ All niche found footage horror - exactly the right vibe!

### The Thing (Classic Sci-Fi Horror)
- **Input:** 24 users reviewed it
- **Top recommendations:**
  1. The Faculty (sci-fi horror)
  2. Nope (alien horror)
  3. Critters (creature feature)
  4. Predator 2 (sci-fi action horror)
  5. They Live (sci-fi horror)

✅ All sci-fi/creature horror - spot on!

### Us (Modern Psychological Horror)
- **Input:** 59 users reviewed it (most popular)
- **Top recommendations:**
  1. You're Next (home invasion thriller)
  2. Haunt (psychological horror)

✅ Modern indie horror with psychological elements!

## Implementation

### Core Script
`scripts/hybrid_recommender_v2.py`

### Usage

```python
from hybrid_recommender_v2 import recommend_hybrid

results, error = recommend_hybrid(
    movie_title="bad ben",
    top_n=10,
    min_content_similarity=0.1,  # Filter threshold
    user_weight=0.7,             # User overlap weight
    similarity_weight=0.3        # Content similarity weight
)

if error:
    print(error)
else:
    for title, user_count, content_sim, hybrid_score, tmdb_id in results:
        print(f"{title}: {hybrid_score:.3f}")
```

### Demo
`scripts/demo_hybrid.py`

Run: `python3 scripts/demo_hybrid.py`

## Data Files

- `data/user_overlap/user_movie_reviews.parquet` - Sparse user-movie matrix (4,115 reviews)
- `data/user_overlap/horror_club_review_stats.csv` - Review counts per movie
- `data/horror_recommender.db` - SQLite database with movie metadata

## Key Differences from Pure Content-Based

| Approach | Bad Ben → ? | Pros | Cons |
|----------|-------------|------|------|
| **Pure Cosine Similarity** | Oppenheimer, Lion King | Fast, simple | Superficial matches |
| **Pure Collaborative** | WNUF Halloween Special | True fan taste | Cold start problem |
| **Hybrid (Ours)** | WNUF Halloween Special (filtered) | Best of both | Needs review data |

## Performance

- **Load time:** ~2 seconds (user matrix + metadata)
- **Recommendation time:** ~0.5 seconds per movie
  - Streaming approach: Only computes similarity for candidates
  - No need to pre-compute full similarity matrix

## Future Enhancements

1. **Implicit feedback**: Use star ratings, not just binary reviewed/not-reviewed
2. **Time decay**: Weight recent reviews more heavily
3. **User clustering**: Find similar users first, then aggregate their tastes
4. **Diversity boost**: Penalize recommendations that are too similar to each other

## Conclusion

The hybrid recommender successfully finds **hidden gem horror movies** by:
1. Leveraging what actual horror fans loved (collaborative filtering)
2. Filtering out non-horror noise (content-based filtering)
3. Balancing popularity with relevance (weighted hybrid scoring)

It's particularly effective for **obscure indie horror** where pure metadata-based approaches fail.
