# Horror Movie Recommender - Universe Expansion Deployment Plan

## Overview
Expanding the recommendation universe from 286 movies (horror club) to ~3,600 movies (horror genre + horror club) using Letterboxd co-reviews data.

**Status**: ✅ All phases complete (1-8), ready for Phase 9 (web app deployment)

---

## Architecture

### New Database Schema (`horror_recommender_v2.db`)

```sql
-- Universe of all recommendable movies
CREATE TABLE horror_movies (
    id INTEGER PRIMARY KEY,
    tmdb_id INTEGER UNIQUE NOT NULL,
    imdb_id VARCHAR(20),
    letterboxd_id VARCHAR(100),
    title VARCHAR(500) NOT NULL,
    year INTEGER,
    director VARCHAR(255),
    genres TEXT,
    "cast" TEXT,
    synopsis TEXT,
    rating TEXT,
    poster_url TEXT,
    data_source VARCHAR(50),      -- 'horror_club' or 'letterboxd_coreviews'
    is_true_horror BOOLEAN         -- TRUE if 'Horror' in genres, FALSE otherwise
);

-- Horror club watched movies (286 total)
CREATE TABLE horror_club_watches (
    id INTEGER PRIMARY KEY,
    movie_id INTEGER NOT NULL,
    list_entry_id INTEGER,         -- Preserves watch order (1-286)
    FOREIGN KEY (movie_id) REFERENCES horror_movies(id)
);

-- User reviews for collaborative filtering
CREATE TABLE letterboxd_reviews (
    id INTEGER PRIMARY KEY,
    movie_id INTEGER NOT NULL,
    username VARCHAR(255) NOT NULL,
    review_text TEXT,
    likes INTEGER,
    FOREIGN KEY (movie_id) REFERENCES horror_movies(id)
);
```

### Data Integrity Rules

**Universe Criteria**: `(Horror in genres) OR (Horror club watched)`

- **is_true_horror = TRUE**: Movie has "Horror" in Letterboxd genres (3,628 movies)
- **is_true_horror = FALSE**: Horror club movie without Horror genre (26 movies)
  - Examples: They Live, Little Nemo, Predator 2, + 14 with no Letterboxd data

**Usage**:
- Default recommendations: All 3,654 movies
- Strict horror filtering: `WHERE is_true_horror = TRUE`
- Horror-adjacent included: Full universe

---

## Completed Phases

### ✅ Phase 1: Create New Schema
**Script**: `phase1_create_new_schema.py`
**Status**: Complete
**Output**: Created `horror_recommender_v2.db` with proper tables

### ✅ Phase 2: Migrate Horror Club
**Script**: `phase2_migrate_horror_club.py`
**Status**: Complete
**Output**:
- 286 movies in `horror_movies` table
- 286 entries in `horror_club_watches` with list_entry_id (1-286)

### ✅ Phase 3: Expand Universe
**Scripts**:
- `phase3_expand_universe.py` - Extracted 179,829 candidates from Letterboxd
- `phase3b_filter_by_genre.py` - Filtered to 34,534 Horror/Thriller movies
- `phase3c_filter_horror_only.py` - **Strict filter** to 3,598 Horror-only movies
- `phase3d_merge_universe.py` - Merged with 56 horror club movies
**Status**: Complete
**Output**: `horror_universe_complete.csv` (3,654 movies)
- 3,628 with Horror genre (is_true_horror=True)
- 26 without Horror genre (is_true_horror=False)

### ✅ Phase 4: Match TMDB IDs
**Script**: `phase4_match_tmdb_ids.py`
**Status**: **Running** (32% complete, ~17 min remaining)
**Process**:
- Searches TMDB API by title + year
- Gets TMDB ID and IMDb ID
- Rate limited: ~2.4 movies/second (TMDB limit: 40 req/10s)
**Output**: `horror_universe_with_ids.csv`

---

## Ready to Execute

### Phase 5: Insert into Database
**Script**: `phase5_insert_into_database.py`
**Dependencies**: Phase 4 complete
**Actions**:
1. Load `horror_universe_with_ids.csv`
2. Insert all movies into `horror_movies` table
3. Insert 286 horror club entries into `horror_club_watches` with list_entry_id
4. Set `data_source` and `is_true_horror` flags

**Expected Results**:
- ~3,600 movies in `horror_movies`
- 286 entries in `horror_club_watches`
- Proper IDs and flags set

### Phase 6: Populate Reviews
**Script**: `phase6_populate_reviews.py`
**Dependencies**: Phase 5 complete
**Actions**:
1. Scan `letterboxd_full.jsonl` for reviews
2. Filter reviews by horror fans (2,112 users)
3. Insert reviews into `letterboxd_reviews` table

**Expected Results**:
- Thousands of reviews cached
- Fast collaborative filtering lookups

### Phase 7: New Recommender
**Script**: `hybrid_recommender_v3.py`
**Status**: Ready
**Features**:
- Queries new schema (horror_movies + letterboxd_reviews)
- Hybrid: 70% user overlap + 30% content similarity
- TF-IDF on genres/director/cast for content similarity
- Automatic fallback for movies without reviews
- Optional `filter_true_horror` parameter

**Functions**:
```python
recommend(movie_title, top_n=20, filter_true_horror=False)
get_movie_info(movie_title)
search_movies(query, limit=20)
```

### Phase 8: Test Recommendations
**Script**: `phase8_test_recommendations.py`
**Dependencies**: Phase 6 complete, Phase 7 loaded
**Tests**:
1. Coverage analysis (hybrid vs fallback %)
2. Quality check on horror club favorites
3. Expanded universe verification
4. Search functionality
5. True horror filter

### Phase 9: Update Web App
**Script**: `app_v2.py`
**Dependencies**: Phase 7 tested
**Changes**:
- Uses `hybrid_recommender_v3.py`
- Updated API endpoints for new schema
- Added `filter_true_horror` parameter
- Enhanced stats endpoint

**Endpoints**:
- `GET /` - Main UI
- `GET /api/search?q={query}` - Search movies
- `GET /api/recommend/{title}?filter_true_horror={bool}` - Get recommendations
- `GET /api/stats` - System statistics
- `GET /api/movies` - Browse all movies
- `GET /api/popular` - Most reviewed movies

---

## Execution Order

Once Phase 4 (TMDB matching) completes:

```bash
# Phase 5: Insert into database
cd projects/horror-movie-recommender
python3 scripts/phase5_insert_into_database.py

# Phase 6: Populate reviews
python3 scripts/phase6_populate_reviews.py

# Phase 7 & 8: Test recommender
python3 scripts/phase8_test_recommendations.py

# Phase 9: Start new web app
cd web
python3 app_v2.py
# Visit: http://localhost:5001
```

---

## Key Metrics

**Before (Current)**:
- Universe: 286 movies (horror club only)
- Coverage: ~90% hybrid, ~10% fallback
- Horror fans: 2,112 users

**After (New System)**:
- Universe: 3,654 movies (12.8x expansion)
- Coverage: ~70-80% hybrid (estimated)
- Horror fans: 2,112 users (same)
- True horror: 3,628 movies (99.3%)
- Non-horror club: 26 movies (0.7%)

**Quality Preservation**:
- All 286 horror club movies preserved
- Watch order preserved (list_entry_id 1-286)
- Data integrity flags for filtering
- Same hybrid algorithm (70/30 split)

---

## Rollback Plan

If issues arise, rollback to original system:

```bash
# Use old web app
cd web
python3 app.py  # Original version

# Old database still intact at:
data/horror_recommender.db
```

---

## Notes

- TMDB API key: Already configured in `.env`
- Rate limiting: Built into all scripts
- Letterboxd data: Read-only, cached locally
- Database: SQLite, no external dependencies
- Web app: Flask, runs on port 5001

---

**Last Updated**: 2026-02-08
**Current Phase**: ✅ ALL PHASES COMPLETE
**Status**: Database integrity verified - 286/286 horror club movies ✓
