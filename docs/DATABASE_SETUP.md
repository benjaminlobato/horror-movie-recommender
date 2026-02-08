# Database Setup Guide

## Overview

The horror movie recommender now uses a proper database to manage:
- **Movies** from multiple sources (TMDB, Letterboxd, Trakt)
- **Reviews** from Letterboxd (user overlap data!)
- **Horror club tracking** (which movies we've watched)
- **ID mappings** across platforms
- **Similarity caching** for performance

## Schema Highlights

### Core Tables:
- `movies` - Primary movie data with external IDs (tmdb_id, imdb_id, letterboxd_id, trakt_id)
- `reviews` - Letterboxd reviews (THE KEY for collaborative filtering!)
- `user_movies` - User interactions (watched, rated, reviewed)
- `similarity_cache` - Pre-computed similarity scores

### Key Features:
- ✅ **Cross-platform ID mapping** - Join TMDB ↔ Letterboxd ↔ Trakt
- ✅ **Horror club tracking** - `watched_by_club` boolean flag
- ✅ **Review-based collaborative filtering** - Find users who reviewed obscure movies
- ✅ **Efficient queries** - Indexed for common operations

## Setup Instructions

### Option 1: SQLite (Recommended for Development)

**Pros:** No server setup, portable, easy
**Cons:** Less features than Postgres

```bash
cd ~/projects/horror-movie-recommender

# Install dependencies
pip3 install sqlalchemy psycopg2-binary

# Run setup
python3 scripts/setup_database.py
# Choose option 2 (SQLite)

# Import existing data
python3 scripts/import_existing_data.py
```

Database will be created at: `data/horror_recommender.db`

### Option 2: PostgreSQL (Recommended for Production)

**Pros:** Full features, better for large datasets
**Cons:** Requires server setup

```bash
# 1. Install PostgreSQL (if not already)
sudo apt-get install postgresql postgresql-contrib

# 2. Create user (if needed)
sudo -u postgres createuser --interactive

# 3. Set environment variables in .env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password

# 4. Run setup
python3 scripts/setup_database.py
# Choose option 1 (PostgreSQL)

# 5. Import existing data
python3 scripts/import_existing_data.py
```

## What Gets Imported

### Initial Import (from existing data):
1. **1,871 movies** from TMDB superset
2. **258 horror club movies** (marked with `watched_by_club = TRUE`)
3. **Full metadata**: keywords, genres, cast, director, ratings

### Next Steps (after Letterboxd download):
4. **847K movies** from Letterboxd dataset
5. **~millions of reviews** (user overlap data!)
6. **ID mappings** between TMDB ↔ Letterboxd

## Database Usage Examples

### Query horror club movies:
```sql
SELECT title, year, tmdb_vote_average, tmdb_vote_count
FROM movies
WHERE watched_by_club = TRUE
ORDER BY title;
```

### Find users who reviewed Bad Ben:
```sql
SELECT DISTINCT username
FROM reviews r
JOIN movies m ON r.movie_id = m.id
WHERE m.title LIKE '%Bad Ben%';
```

### See what else those users reviewed:
```sql
WITH bad_ben_reviewers AS (
    SELECT DISTINCT username
    FROM reviews r
    JOIN movies m ON r.movie_id = m.id
    WHERE m.title LIKE '%Bad Ben%'
)
SELECT m.title, m.year, COUNT(*) as review_count
FROM reviews r
JOIN movies m ON r.movie_id = m.id
WHERE r.username IN (SELECT username FROM bad_ben_reviewers)
  AND m.title NOT LIKE '%Bad Ben%'
GROUP BY m.id, m.title, m.year
ORDER BY review_count DESC
LIMIT 20;
```

### Find obscure gems:
```sql
SELECT title, year, tmdb_vote_average, tmdb_vote_count
FROM movies
WHERE tmdb_vote_count < 500
  AND tmdb_vote_average > 6.5
  AND watched_by_club = FALSE
ORDER BY tmdb_vote_average DESC
LIMIT 20;
```

## Connection Strings

After setup, connection string is saved to `.env`:

**SQLite:**
```
DATABASE_URL=sqlite:////home/benunix/projects/horror-movie-recommender/data/horror_recommender.db
```

**PostgreSQL:**
```
DATABASE_URL=postgresql://user:password@localhost:5432/horror_recommender
```

## Next Steps

1. ✅ **Setup database** (you are here)
2. **Download Letterboxd dataset** (847K movies + reviews)
   ```bash
   python3 scripts/download_letterboxd.py
   ```
3. **Build review-based recommender** (collaborative filtering)
4. **Integrate with web app** (use DB instead of pickle files)

## Troubleshooting

### SQLite: Database locked
- Close any open connections
- Check if another process is using the DB

### PostgreSQL: Connection refused
- Ensure PostgreSQL is running: `sudo systemctl status postgresql`
- Check connection parameters in `.env`

### Import errors
- Ensure TMDB metadata file exists: `data/movies_metadata_raw.json`
- Check file encoding: should be UTF-8
