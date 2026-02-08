# Database Redesign & Architecture TODO

## Current Problems
- ❌ Single `movies` table with `watched_by_club` flag is messy
- ❌ Mixes universe of horror movies with club-specific data
- ❌ Universe limited to 1,908 movies (should be ~5,000)
- ❌ Built from TMDB keywords instead of actual user behavior

## Proposed Architecture

### Table 1: `horror_movies` (The Universe)
**Purpose:** ALL horror movies that could be recommended

**Schema:**
```sql
CREATE TABLE horror_movies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Core identifiers
    tmdb_id INTEGER UNIQUE NOT NULL,
    imdb_id VARCHAR(20),
    letterboxd_id VARCHAR(100),

    -- Basic info
    title VARCHAR(500) NOT NULL,
    year INTEGER,
    director VARCHAR(255),

    -- Metadata for recommendations
    genres TEXT,
    keywords TEXT,
    cast TEXT,
    overview TEXT,

    -- Ratings/popularity
    tmdb_vote_count INTEGER DEFAULT 0,
    tmdb_vote_average REAL,
    tmdb_popularity REAL,
    letterboxd_rating REAL,
    letterboxd_review_count INTEGER DEFAULT 0,

    -- Source tracking
    data_source VARCHAR(50),  -- 'tmdb_keywords', 'letterboxd_coreviews', 'manual'

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_tmdb_id ON horror_movies(tmdb_id);
CREATE INDEX idx_title ON horror_movies(title);
```

### Table 2: `horror_club_watches` (What Club Watched)
**Purpose:** Track which movies the horror club watched and when

**Schema:**
```sql
CREATE TABLE horror_club_watches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Link to movie
    movie_id INTEGER NOT NULL,

    -- Original list metadata
    list_entry_id INTEGER,  -- From original CSV (watch order!)
    data_object_id VARCHAR(50),  -- From Letterboxd export

    -- Watch info
    watch_date DATE,
    notes TEXT,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (movie_id) REFERENCES horror_movies(id)
);

CREATE INDEX idx_movie_id ON horror_club_watches(movie_id);
CREATE INDEX idx_list_entry_id ON horror_club_watches(list_entry_id);
```

### Table 3: `letterboxd_reviews` (Optional - for user overlap)
**Purpose:** Cache reviews for collaborative filtering

**Schema:**
```sql
CREATE TABLE letterboxd_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    movie_id INTEGER NOT NULL,
    username VARCHAR(255) NOT NULL,

    -- Review metadata (if we want it)
    review_text TEXT,
    likes INTEGER DEFAULT 0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (movie_id) REFERENCES horror_movies(id),
    UNIQUE(movie_id, username)
);

CREATE INDEX idx_username ON letterboxd_reviews(username);
CREATE INDEX idx_movie_username ON letterboxd_reviews(movie_id, username);
```

## Migration Plan

### Phase 1: Build New Schema ✅
- [ ] Create new tables with proper schema
- [ ] Keep old `movies` table for reference during migration

### Phase 2: Migrate Horror Club Movies ✅
- [ ] Insert 286 authoritative horror club movies into `horror_movies`
- [ ] Insert watch records into `horror_club_watches` with `list_entry_id`
- [ ] Preserve original watch order from CSV

### Phase 3: Expand Universe via Letterboxd Co-Reviews 🎯
- [ ] Query Letterboxd dataset: Find all movies reviewed by our 2,112 users
- [ ] Extract movie titles, years, letterboxd_ids
- [ ] Match to TMDB to get tmdb_id, imdb_id, metadata
- [ ] Filter for horror/thriller genres
- [ ] Insert into `horror_movies` with `data_source='letterboxd_coreviews'`
- [ ] **Target: ~5,000 horror movies**

### Phase 4: Cache Letterboxd Reviews
- [ ] Extract reviews for all horror_movies from Letterboxd dataset
- [ ] Insert into `letterboxd_reviews` table
- [ ] This powers collaborative filtering

### Phase 5: Update Recommender Code
- [ ] Update hybrid recommender to query new schema
- [ ] Recommend FROM `horror_movies` (universe)
- [ ] Recommend FOR `horror_club_watches` (what club watched)
- [ ] Update web app to use new schema

### Phase 6: Cleanup
- [ ] Verify everything works
- [ ] Drop old `movies` table
- [ ] Archive old scripts

## Benefits of New Architecture

✅ **Separation of Concerns**
- Universe of horror movies (5,000+)
- Specific lists (horror club, future curated lists)

✅ **Preserve Metadata**
- `list_entry_id` preserves watch order
- Can analyze: "What patterns in watch order?"
- Can query: "Show me movies watched in chronological order"

✅ **Scalability**
- Easy to add new lists/collections
- Easy to add new data sources
- Easy to add more metadata

✅ **Better Recommendations**
- Recommend from 5,000 movies (not 286)
- Still curated by actual horror fan behavior
- Maintains quality through user overlap

## Open Questions

1. **Do we want to keep budget/revenue data?**
   - Probably not critical for recommendations
   - Can add later if needed

2. **How far back in Letterboxd reviews?**
   - All 4,115 reviews we have
   - Or expand to ALL movies in Letterboxd dataset?

3. **Multiple watch tracking?**
   - Horror club might watch same movie multiple times
   - Current schema allows this (one row per watch)

4. **User tables?**
   - Do we want to track the 2,112 Letterboxd users?
   - Could enable "find similar users" feature

## Next Steps

1. ✅ Review this architecture proposal
2. ✅ Get approval on schema design
3. 🎯 Create migration scripts
4. 🎯 Expand universe via Letterboxd
5. 🎯 Update recommender & web app
