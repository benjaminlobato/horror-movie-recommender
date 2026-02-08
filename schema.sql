-- Horror Movie Recommender Database Schema
-- Unified data foundation for TMDB, Letterboxd, Trakt, and Horror Club data

-- ============================================================================
-- MOVIES TABLE (Core entity)
-- ============================================================================
CREATE TABLE movies (
    id SERIAL PRIMARY KEY,

    -- Basic Info
    title VARCHAR(500) NOT NULL,
    year INTEGER,
    overview TEXT,

    -- External IDs (for joining across platforms)
    tmdb_id INTEGER UNIQUE,
    imdb_id VARCHAR(20) UNIQUE,
    letterboxd_id VARCHAR(100) UNIQUE,
    trakt_id INTEGER UNIQUE,

    -- Metadata
    genres JSONB,              -- ['Horror', 'Thriller']
    keywords JSONB,            -- ['found footage', 'haunted house']
    director VARCHAR(255),
    cast JSONB,                -- ['Actor 1', 'Actor 2', 'Actor 3']

    -- Stats from TMDB
    tmdb_vote_count INTEGER DEFAULT 0,
    tmdb_vote_average NUMERIC(3,1),
    tmdb_popularity NUMERIC(10,3),
    budget BIGINT,
    revenue BIGINT,

    -- Stats from Letterboxd
    letterboxd_rating NUMERIC(2,1),
    letterboxd_review_count INTEGER DEFAULT 0,

    -- Horror Club tracking
    watched_by_club BOOLEAN DEFAULT FALSE,
    club_watch_date DATE,
    club_notes TEXT,

    -- Source tracking
    data_source VARCHAR(50),   -- 'tmdb', 'letterboxd', 'manual'

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- REVIEWS TABLE (Letterboxd reviews)
-- ============================================================================
CREATE TABLE reviews (
    id SERIAL PRIMARY KEY,
    movie_id INTEGER REFERENCES movies(id) ON DELETE CASCADE,

    -- Review data
    username VARCHAR(100) NOT NULL,
    review_text TEXT,
    rating NUMERIC(2,1),       -- Letterboxd uses 0.5 to 5.0
    likes INTEGER DEFAULT 0,
    review_date DATE,

    -- Source
    source VARCHAR(20) DEFAULT 'letterboxd',

    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- USER_MOVIES TABLE (User interactions for collaborative filtering)
-- ============================================================================
CREATE TABLE user_movies (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,     -- username or hashed ID
    movie_id INTEGER REFERENCES movies(id) ON DELETE CASCADE,

    -- Interaction details
    interaction_type VARCHAR(20) NOT NULL,  -- 'reviewed', 'watched', 'rated', 'listed'
    rating NUMERIC(2,1),

    -- Source platform
    platform VARCHAR(20),      -- 'letterboxd', 'trakt', 'horror_club'

    -- Timestamps
    interaction_date DATE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- ID_MAPPINGS TABLE (Cross-platform ID resolution)
-- ============================================================================
CREATE TABLE id_mappings (
    id SERIAL PRIMARY KEY,
    movie_id INTEGER REFERENCES movies(id) ON DELETE CASCADE,

    -- All possible IDs
    tmdb_id INTEGER,
    imdb_id VARCHAR(20),
    letterboxd_id VARCHAR(100),
    trakt_id INTEGER,

    -- Confidence score
    confidence NUMERIC(3,2) DEFAULT 1.0,  -- 0.0 to 1.0

    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- SIMILARITY_CACHE TABLE (Pre-computed similarities)
-- ============================================================================
CREATE TABLE similarity_cache (
    id SERIAL PRIMARY KEY,
    movie_id_1 INTEGER REFERENCES movies(id) ON DELETE CASCADE,
    movie_id_2 INTEGER REFERENCES movies(id) ON DELETE CASCADE,

    -- Similarity scores
    content_similarity NUMERIC(5,4),      -- Cosine similarity (0 to 1)
    collaborative_similarity NUMERIC(5,4), -- User overlap similarity
    combined_similarity NUMERIC(5,4),      -- Hybrid score

    -- Metadata
    algorithm_version VARCHAR(20),
    computed_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(movie_id_1, movie_id_2)
);

-- ============================================================================
-- INDEXES for performance
-- ============================================================================

-- Movies table indexes
CREATE INDEX idx_movies_tmdb ON movies(tmdb_id);
CREATE INDEX idx_movies_imdb ON movies(imdb_id);
CREATE INDEX idx_movies_letterboxd ON movies(letterboxd_id);
CREATE INDEX idx_movies_trakt ON movies(trakt_id);
CREATE INDEX idx_movies_watched ON movies(watched_by_club);
CREATE INDEX idx_movies_year ON movies(year);
CREATE INDEX idx_movies_title ON movies(title);
CREATE INDEX idx_movies_genres ON movies USING GIN (genres);
CREATE INDEX idx_movies_keywords ON movies USING GIN (keywords);

-- Reviews table indexes
CREATE INDEX idx_reviews_movie ON reviews(movie_id);
CREATE INDEX idx_reviews_user ON reviews(username);
CREATE INDEX idx_reviews_rating ON reviews(rating);

-- User_movies table indexes
CREATE INDEX idx_user_movies_user ON user_movies(user_id);
CREATE INDEX idx_user_movies_movie ON user_movies(movie_id);
CREATE INDEX idx_user_movies_type ON user_movies(interaction_type);
CREATE UNIQUE INDEX idx_user_movies_unique ON user_movies(user_id, movie_id, interaction_type, platform);

-- Similarity cache indexes
CREATE INDEX idx_similarity_movie1 ON similarity_cache(movie_id_1);
CREATE INDEX idx_similarity_movie2 ON similarity_cache(movie_id_2);
CREATE INDEX idx_similarity_combined ON similarity_cache(combined_similarity DESC);

-- ============================================================================
-- VIEWS for common queries
-- ============================================================================

-- Horror club movies view
CREATE VIEW horror_club_movies AS
SELECT
    m.*,
    COUNT(r.id) as review_count
FROM movies m
LEFT JOIN reviews r ON m.id = r.movie_id
WHERE m.watched_by_club = TRUE
GROUP BY m.id;

-- User review stats view
CREATE VIEW user_review_stats AS
SELECT
    username,
    COUNT(*) as total_reviews,
    AVG(rating) as avg_rating,
    COUNT(DISTINCT m.id) FILTER (WHERE m.tmdb_vote_count < 500) as obscure_movie_count
FROM reviews r
JOIN movies m ON r.movie_id = m.id
GROUP BY username;

-- Movie recommendation view (most similar to horror club movies)
CREATE VIEW recommended_movies AS
SELECT
    m2.id,
    m2.title,
    m2.year,
    m2.tmdb_vote_average,
    m2.tmdb_vote_count,
    AVG(sc.combined_similarity) as avg_similarity_to_club
FROM movies m1
JOIN similarity_cache sc ON m1.id = sc.movie_id_1
JOIN movies m2 ON sc.movie_id_2 = m2.id
WHERE m1.watched_by_club = TRUE
  AND m2.watched_by_club = FALSE
GROUP BY m2.id, m2.title, m2.year, m2.tmdb_vote_average, m2.tmdb_vote_count
ORDER BY avg_similarity_to_club DESC;

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Update timestamp function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for movies table
CREATE TRIGGER update_movies_updated_at BEFORE UPDATE ON movies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
