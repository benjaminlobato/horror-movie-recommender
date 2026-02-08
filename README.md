# Horror Movie Recommender

A hybrid recommendation system that combines collaborative filtering (user overlap) with content-based filtering to suggest horror movies based on what horror fans actually watch.

**Current Universe**: ~3,600 horror movies
**Recommendation Method**: 70% user overlap + 30% content similarity
**Data Source**: Letterboxd reviews from 2,112+ horror fans

---

## Table of Contents

1. [The Problem](#the-problem)
2. [The Solution](#the-solution)
3. [Architecture Overview](#architecture-overview)
4. [Data Sources](#data-sources)
5. [Data Processing Pipeline](#data-processing-pipeline)
6. [Recommendation Algorithm](#recommendation-algorithm)
7. [Database Schema](#database-schema)
8. [Usage](#usage)
9. [Development History](#development-history)
10. [File Structure](#file-structure)

---

## The Problem

**Challenge**: Recommend horror movies that horror fans will actually enjoy, not just movies with similar keywords.

**Why Traditional Content-Based Filtering Fails**:
- Pure cosine similarity (TF-IDF on genres/keywords) gives superficial matches
- Example: "Bad Ben" (found footage indie horror) → "Oppenheimer" (both tagged "dramatic")
- Keywords like "intense", "atmospheric", "dark" apply to many non-horror films

**What We Need**:
- Recommendations based on what real horror fans watch
- Understanding of horror subgenres (found footage, slasher, supernatural, etc.)
- Quality signal beyond just metadata matching

---

## The Solution

### Hybrid Recommendation System

**70% Collaborative Filtering (User Overlap)**:
- Find users who reviewed the target movie
- See what other movies those users reviewed
- Score by how many users overlap
- **Why it works**: Horror fans have distinct tastes; if they both reviewed "Bad Ben" and "WNUF Halloween Special", there's a real connection

**30% Content-Based Filtering (Metadata Similarity)**:
- Use TF-IDF on genres, director, and cast
- Calculate cosine similarity between movies
- Filter out low-similarity recommendations (min threshold: 0.05)
- **Why we need it**: Prevents recommending completely unrelated movies that happen to share a few reviewers

**Automatic Fallback**:
- Movies with reviews: Hybrid approach (best quality)
- Movies without reviews: Pure content similarity (fallback)
- Ensures 100% coverage of universe

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     DATA SOURCES                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Horror Club List (286 movies)                             │
│  ├─ Authoritative list of what the horror club watched     │
│  └─ With watch order (list_entry_id 1-286)                 │
│                                                             │
│  Letterboxd Dataset (847K movies)                           │
│  ├─ Full movie metadata (genres, cast, directors)          │
│  ├─ User reviews from horror fans                          │
│  └─ Ratings and popularity data                            │
│                                                             │
│  TMDB API                                                   │
│  ├─ Official TMDB IDs                                      │
│  ├─ IMDb IDs for cross-platform linking                    │
│  └─ Additional metadata if needed                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  PROCESSING PIPELINE                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Phase 1: Extract Horror Fans                              │
│  └─ Find 2,112 users who reviewed horror club movies       │
│                                                             │
│  Phase 2: Extract Candidate Movies                         │
│  └─ Find 179,829 movies reviewed by horror fans            │
│                                                             │
│  Phase 3: Filter by Genre                                  │
│  ├─ STRICT: Must have "Horror" in genres                   │
│  ├─ Result: 3,598 Horror movies                            │
│  └─ Plus: 56 horror club movies without Horror tag         │
│                                                             │
│  Phase 4: Match TMDB IDs                                   │
│  └─ Get official IDs for all 3,654 movies                  │
│                                                             │
│  Phase 5: Build Database                                   │
│  └─ Insert into horror_recommender_v2.db                   │
│                                                             │
│  Phase 6: Cache Reviews                                    │
│  └─ Store user-movie review relationships                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  RECOMMENDATION ENGINE                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  hybrid_recommender_v3.py                                   │
│  ├─ Load movie universe (3,654 movies)                     │
│  ├─ Build user-movie mappings (collaborative filtering)    │
│  ├─ Compute TF-IDF similarity matrix (content-based)       │
│  └─ Combine scores: 0.7 × user_overlap + 0.3 × content_sim │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                       WEB APPLICATION                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Flask Web App (app_v2.py)                                 │
│  ├─ Search for movies                                      │
│  ├─ Get recommendations                                    │
│  ├─ Browse popular movies                                  │
│  └─ View statistics                                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Sources

### 1. Horror Club List

**File**: `data/horror_club_with_ids.csv`
**Origin**: Authoritative list of 286 movies watched by a horror film club
**Purpose**: Gold standard for "quality horror movies"

**Contains**:
- Film title and year
- Letterboxd film slug (ID)
- TMDB ID and IMDb ID
- Watch order (list_entry_id: 1-286)

**Why it matters**: These are the movies we KNOW horror fans love. Everything else is measured against this standard.

### 2. Letterboxd Dataset

**File**: `data/letterboxd/letterboxd_full.jsonl`
**Size**: 847,209 movies (~500MB)
**Format**: JSONL (JSON Lines) - one movie per line

**Each movie contains**:
```json
{
  "url": "https://letterboxd.com/film/the-thing-1982/",
  "title": "The Thing",
  "year": "1982",
  "directors": ["John Carpenter"],
  "genres": ["Mystery", "Science Fiction", "Horror"],
  "cast": ["Kurt Russell", "Keith David", ...],
  "synopsis": "...",
  "rating": "4.23 out of 5",
  "reviews": [
    {
      "username": "username",
      "review_text": "...",
      "likes": "123"
    }
  ],
  "poster_url": "https://..."
}
```

**Why it matters**:
- Provides genre classification (source of truth for "is this horror?")
- Contains user reviews for collaborative filtering
- Rich metadata for content-based similarity

### 3. TMDB API

**Purpose**: Get official movie IDs for cross-platform compatibility
**Rate Limit**: 40 requests per 10 seconds

**What we get**:
- TMDB ID (primary key for most movie databases)
- IMDb ID (for linking to IMDb, streaming platforms, etc.)

---

## Data Processing Pipeline

### Phase 1: Identify Horror Fans

**Script**: `scripts/phase1_extract_horror_fans.py`
**Input**: `horror_club_with_ids.csv` + `letterboxd_full.jsonl`
**Output**: `data/user_overlap/user_movie_reviews.parquet` (2,112 users)

**Process**:
1. Load 286 horror club movies (with Letterboxd IDs)
2. Scan 847K Letterboxd movies to find these 286
3. Extract all users who reviewed any horror club movie
4. Build user-movie review matrix

**Result**: 2,112 horror fans who have proven taste in horror

---

### Phase 2: Extract Candidate Movies

**Script**: `scripts/phase3_expand_universe.py`
**Input**: `user_movie_reviews.parquet` + `letterboxd_full.jsonl`
**Output**: `universe_candidates.csv` (179,829 movies)

**Process**:
1. Take the 2,112 horror fans
2. Find ALL movies they reviewed (not just horror club)
3. Count how many fans reviewed each movie
4. Save all candidates

**Why cast a wide net?**: Some great horror movies might not have "Horror" as their primary genre. We let the data decide.

---

### Phase 3: Filter by Genre (STRICT)

**Scripts**:
- `phase3b_filter_by_genre.py` → 34,534 movies
- `phase3c_filter_horror_only.py` → 3,598 movies
- `phase3d_merge_universe.py` → 3,654 movies (final)

**Critical Decision**: **Thriller alone is NOT horror**

**Examples of what we EXCLUDE**:
- Inglourious Basterds (War/Drama/Thriller)
- Die Hard (Action/Thriller)
- Blade Runner (Sci-Fi/Thriller)

**Filter Logic**:
```python
horror_only = df[df['genres'].str.contains('Horror', case=False, na=False)]
```

**Result**: 3,598 movies that have "Horror" in their Letterboxd genres

**Special Case**: 56 horror club movies don't have "Horror" tag (e.g., "They Live", "Little Nemo"). We include them BUT flag them with `is_true_horror = FALSE`

**Final Universe**: 3,654 movies = 3,598 Horror + 56 horror club non-horror

---

### Phase 4: Match TMDB IDs

**Script**: `scripts/phase4_match_tmdb_ids.py`
**Output**: `horror_universe_with_ids.csv`

**Process**:
```python
for each movie:
    # Search TMDB by title + year
    results = tmdb.search(title, year)
    tmdb_id = results[0]['id']

    # Get full details for IMDb ID
    details = tmdb.get_movie(tmdb_id)
    imdb_id = details['imdb_id']
```

**Rate Limiting**: 0.26 seconds per movie (~2.4 movies/sec)
**Time**: ~25 minutes for 3,654 movies
**Success Rate**: ~95-98%

---

### Phase 5: Build Database

**Script**: `scripts/phase5_insert_into_database.py`
**Output**: `data/horror_recommender_v2.db` (SQLite)

**Process**:
1. Insert all 3,654 movies into `horror_movies` table
2. Mark data_source ('horror_club' or 'letterboxd_coreviews')
3. Set is_true_horror flag
4. Insert 286 horror club watches into `horror_club_watches` with list_entry_id

---

### Phase 6: Cache Reviews

**Script**: `scripts/phase6_populate_reviews.py`
**Output**: Populated `letterboxd_reviews` table

**Process**:
1. For each movie in universe (with Letterboxd ID)
2. Scan Letterboxd dataset for its reviews
3. Filter to only horror fans (2,112 users)
4. Cache user-movie relationships

**Why cache?**: Collaborative filtering requires fast lookup: "Who reviewed this movie?"

---

## Recommendation Algorithm

### Step 1: Collaborative Filtering (User Overlap)

```python
# Find users who reviewed target movie
users_who_reviewed = movie_to_users["bad ben"]  # e.g., 10 users

# Find other movies those users reviewed
for user in users_who_reviewed:
    for other_movie in user_to_movies[user]:
        candidate_movies[other_movie] += 1

# Example results:
# "wnuf halloween special" → 8 users (8/10 = 0.8 overlap)
# "noroi: the curse" → 6 users (6/10 = 0.6 overlap)
```

**Normalized User Score** = `user_count / len(users_who_reviewed)`

### Step 2: Content-Based Filtering (TF-IDF Similarity)

```python
# Build feature vector for each movie
features = f"{genres} {director} {cast}"

# Compute TF-IDF
vectorizer = TfidfVectorizer(max_features=1000, ngram_range=(1, 2))
tfidf_matrix = vectorizer.fit_transform(all_movie_features)

# Compute similarity
content_sim = cosine_similarity(target_vector, candidate_vector)
```

### Step 3: Combine Scores

```python
hybrid_score = (normalized_user_count × 0.7) + (content_similarity × 0.3)

# Example for "WNUF Halloween Special" given "Bad Ben":
# User overlap: 0.8 (8/10 users)
# Content sim: 0.45 (both found footage horror)
# Hybrid: (0.8 × 0.7) + (0.45 × 0.3) = 0.695
```

**Filter**: Drop candidates with content_sim < 0.05 (too dissimilar)

### Fallback for Movies Without Reviews

```python
# Use pure content similarity
similarities = cosine_similarity(target_movie, all_movies)
return top_similar[:top_n]
```

**Coverage**: 100% guaranteed (hybrid when possible, cosine fallback otherwise)

---

## Database Schema

### Table: `horror_movies`

Universe of all recommendable movies

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Primary key |
| `tmdb_id` | INTEGER | TMDB ID (unique) |
| `imdb_id` | VARCHAR(20) | IMDb ID |
| `letterboxd_id` | VARCHAR(100) | Letterboxd slug |
| `title` | VARCHAR(500) | Movie title |
| `year` | INTEGER | Release year |
| `director` | VARCHAR(255) | Director name(s) |
| `genres` | TEXT | Comma-separated genres |
| `cast` | TEXT | Comma-separated cast |
| `synopsis` | TEXT | Plot synopsis |
| `rating` | TEXT | Letterboxd rating |
| `poster_url` | TEXT | Poster image URL |
| `data_source` | VARCHAR(50) | 'horror_club' or 'letterboxd_coreviews' |
| `is_true_horror` | BOOLEAN | TRUE if 'Horror' in genres |

### Table: `horror_club_watches`

Track which movies the horror club watched (preserves watch order)

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Primary key |
| `movie_id` | INTEGER | FK to horror_movies.id |
| `list_entry_id` | INTEGER | Watch order (1-286) |

### Table: `letterboxd_reviews`

Cache user-movie review relationships for fast collaborative filtering

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Primary key |
| `movie_id` | INTEGER | FK to horror_movies.id |
| `username` | VARCHAR(255) | Letterboxd username |
| `review_text` | TEXT | Review excerpt |
| `likes` | INTEGER | Number of likes |

---

## Usage

### Running the Recommender (Python)

```python
from hybrid_recommender_v3 import recommend, get_movie_info, search_movies

# Get recommendations
results, error, method = recommend("Bad Ben", top_n=20)

for movie_id, title, hybrid_score, user_count, content_sim, metadata in results:
    print(f"{title}: {hybrid_score:.3f}")

# Search movies
matches = search_movies("nightmare", limit=10)
```

### Running the Web App

```bash
cd web
python3 app_v2.py
# Visit: http://localhost:5001
```

**API Endpoints**:
- `GET /api/search?q=nightmare`
- `GET /api/recommend/bad%20ben`
- `GET /api/recommend/bad%20ben?filter_true_horror=true`
- `GET /api/movies`
- `GET /api/popular`
- `GET /api/stats`

---

## Development History

### Version 1: Pure Content-Based (Failed)
**Problem**: "Bad Ben" → "Oppenheimer" (both tagged "dramatic")

### Version 2: Hybrid with Small Universe (Limited)
**Universe**: 286 movies (horror club only)
**Success**: Great recommendations
**Problem**: Too small

### Version 3: Hybrid with Expanded Universe (Current)
**Universe**: 3,654 movies (12.8x larger)
**Method**: Co-review analysis + strict genre filtering
**Result**: Quality AND variety

---

## Key Metrics

- **Universe Size**: 3,654 movies
- **True Horror**: 3,628 movies (99.3%)
- **Horror Fans**: 2,112 users
- **Coverage**: 100% (hybrid + fallback)
- **Recommendation Speed**: Instant

---

## File Structure

```
horror-movie-recommender/
├── data/
│   ├── horror_club_with_ids.csv          # 286 horror club movies
│   ├── horror_universe_complete.csv      # 3,654 final universe
│   ├── horror_recommender_v2.db          # SQLite database
│   ├── letterboxd/
│   │   └── letterboxd_full.jsonl         # 847K movies
│   └── user_overlap/
│       └── user_movie_reviews.parquet    # 2,112 horror fans
│
├── scripts/
│   ├── hybrid_recommender_v3.py          # Main recommender
│   ├── phase*_*.py                       # Data processing pipeline
│   └── phase8_test_recommendations.py    # Testing
│
├── web/
│   ├── app_v2.py                         # Flask web app
│   └── templates/index.html
│
├── README.md                             # This file
└── DEPLOYMENT_PLAN.md                    # Deployment guide
```

---

## Technology Stack

- **Python**: Data processing and ML
- **scikit-learn**: TF-IDF, cosine similarity
- **pandas**: Data manipulation
- **SQLite**: Database
- **Flask**: Web framework
- **TMDB API**: Movie metadata

---

**Last Updated**: 2026-02-08
**Version**: 3.0 (Expanded Universe)
**Status**: Production Ready

---

*Built with horror fans, for horror fans* 🎃
