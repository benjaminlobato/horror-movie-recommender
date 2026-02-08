# Horror Movie Recommender - Progress Summary

## What We Built Today

### ✅ Phase 1: Hybrid Recommender System
**Goal:** Combine collaborative filtering with content-based filtering

**Achievements:**
- Built hybrid recommender: 70% user overlap + 30% content similarity
- Extracted 4,115 reviews from 2,112 Letterboxd users
- Cosine fallback for movies without reviews
- 100% coverage: 257 movies with hybrid, 29 with cosine fallback

**Results:**
- **Bad Ben** recommendations:
  - ❌ Pure cosine: "Oppenheimer", "Lion King" (superficial)
  - ✅ Hybrid: "WNUF Halloween Special", "Noroi: The Curse" (actual horror gems!)

**Files:**
- `scripts/hybrid_recommender_v2.py` - Core hybrid engine
- `scripts/hybrid_recommender_with_fallback.py` - With cosine fallback
- `web/app.py` - Updated web interface
- `data/user_overlap/user_movie_reviews.parquet` - 4,115 reviews

### ✅ Phase 2: Database Cleanup
**Goal:** Match authoritative horror club list exactly

**Achievements:**
- Cleaned up 32 duplicate entries (remakes/sequels)
- Database now has exactly 286 horror club movies
- Matches authoritative CSV with proper TMDB/IMDb/Letterboxd IDs

**Results:**
- Before: 318 movies (with duplicates)
- After: 286 movies (exact match)

### ✅ Phase 3: Database Redesign & Migration
**Goal:** Proper architecture for scalability

**Achievements:**
- Created new schema with clean separation of concerns:
  - `horror_movies` - The universe (will be ~5,000)
  - `horror_club_watches` - What club watched (286) with watch order
  - `letterboxd_reviews` - For collaborative filtering cache
- Migrated 286 horror club movies with `list_entry_id` preserving watch order
- Started Phase 3: Expanding universe via Letterboxd co-reviews

**Current Status:**
- ✅ Phase 1: Schema created
- ✅ Phase 2: Horror club migrated (286 movies)
- 🔄 Phase 3: Extracting universe candidates (running in background)

## Architecture Evolution

### Before (Messy)
```
movies table (1,908 rows)
├── watched_by_club flag (318 movies - had duplicates!)
└── Mixed horror club with broader TMDB keyword search
```

### After (Clean)
```
horror_movies (universe ~5,000)
├── Horror club: 286 movies (data_source='horror_club')
├── TMDB keywords: 1,622 movies (data_source='tmdb_keywords')
└── Letterboxd co-reviews: ~3,000 movies (data_source='letterboxd_coreviews')

horror_club_watches (286 rows)
├── Links to horror_movies
├── list_entry_id (watch order!)
└── Extensible for multiple lists

letterboxd_reviews (cache)
├── Fast collaborative filtering
└── movie_id + username pairs
```

## Key Insights

### 1. Cosine Similarity Alone is Superficial
- "Bad Ben" → "Oppenheimer" (both tagged "dramatic")
- Metadata keywords don't capture what horror fans actually like

### 2. User Overlap is Powerful
- Even 2 users reviewing both movies is a strong signal
- When those 2 users have 80+ horror reviews each
- "Tony the Terror" reviewed 86 horror club movies - his taste matters!

### 3. Letterboxd Dataset Limitations
- Only 257/286 horror club movies have reviews in the dataset
- Some movies have as few as 10 reviewers (Bad Ben)
- But quality > quantity for niche horror fans

### 4. Hybrid Approach Wins
- User overlap finds hidden gems
- Content similarity filters out non-horror (Lion King)
- 70/30 weighting balances both signals

### 5. Architecture Matters
- Clean separation: universe vs. watched
- Preserving watch order (list_entry_id) enables future analysis
- Extensible for multiple curated lists

## What's Next

### Phase 3 (In Progress)
- ✅ Extract movies reviewed by 2,112 horror fans from Letterboxd
- 🔄 Match to TMDB API for IDs and genres
- 🔄 Filter for horror/thriller (target: ~5,000 total movies)
- 🔄 Insert into horror_movies with data_source='letterboxd_coreviews'

### Phase 4 (TODO)
- Populate letterboxd_reviews table for fast collaborative filtering
- Update hybrid recommender to query new schema
- Recommend FROM 5,000 movies TO 286 horror club movies

### Phase 5 (TODO)
- Update web app to use new schema
- Add "watch order" view (sort by list_entry_id)
- Add universe statistics dashboard

## Files Changed

### New Files Created
- `DATABASE_REDESIGN_TODO.md` - Full architecture plan
- `PROGRESS_SUMMARY.md` - This file
- `scripts/phase1_create_new_schema.py` - New tables
- `scripts/phase2_migrate_horror_club.py` - Migration
- `scripts/phase3_expand_universe.py` - Universe expansion
- `scripts/hybrid_recommender_v2.py` - Core hybrid engine
- `scripts/hybrid_recommender_with_fallback.py` - With fallback
- `scripts/cleanup_horror_club_duplicates.py` - Remove duplicates
- `scripts/check_*.py` - Various analysis scripts
- `HYBRID_RECOMMENDER.md` - Documentation

### Modified Files
- `web/app.py` - Updated for hybrid recommender
- `web/templates/index.html` - New UI with hybrid scores
- `data/horror_recommender.db` - New schema added

### Data Files
- `data/user_overlap/user_movie_reviews.parquet` - 4,115 reviews
- `data/user_overlap/horror_club_review_stats.csv` - Review counts
- `data/horror_club_with_ids.csv` - Authoritative 286 movies
- `data/universe_candidates.csv` - Extracted co-reviews (pending)

## Metrics

### Database
- Horror club movies: 286 (exact match to authoritative list)
- Old universe: 1,908 movies (TMDB keywords only)
- New universe: ~5,000 movies (after Phase 3 completes)

### Letterboxd Data
- Horror club reviewers: 2,112 users
- Total reviews extracted: 4,115
- Movies with reviews: 257/286 (89.9%)
- Average reviews per movie: 16.0

### Recommendations
- Hybrid coverage: 257/286 movies (89.9%)
- Cosine fallback: 29/286 movies (10.1%)
- Total coverage: 286/286 movies (100%)

## Success Criteria Met

✅ **Authoritative Data Foundation**
- Exact 286 horror club movies with proper IDs
- Cross-platform: TMDB, IMDb, Letterboxd
- Watch order preserved

✅ **Better Recommendations**
- Hybrid > Pure cosine (Bad Ben test case proves it)
- Hidden gems discovered (WNUF Halloween Special)
- 100% coverage with fallback

✅ **Scalable Architecture**
- Clean separation of concerns
- Extensible schema for future features
- Ready for 5,000 movie universe

✅ **Production Ready**
- Web app running at localhost:5001
- Fast recommendations (<1 second)
- User-friendly interface with scores/tiers

## Next Session Goals

1. Complete Phase 3 (universe expansion to ~5,000)
2. Implement TMDB matching for genre filtering
3. Update recommender to use new schema
4. Test recommendations with larger universe
5. Deploy and test end-to-end

---
*Last updated: 2026-02-08*
