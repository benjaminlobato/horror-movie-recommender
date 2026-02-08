# Horror Movie Recommender

A content-based movie recommendation system designed for horror enthusiasts, with a focus on discovering obscure gems rather than mainstream blockbusters.

## The Problem

Generic recommendation systems (like TMDB's built-in recommender) fail for niche horror movies. An ultra-low-budget found footage film like "Bad Ben" ($300 budget) gets recommended mainstream blockbusters like "Oppenheimer" instead of similar obscure horror films.

## Our Approach

### Phase 1: Content-Based Filtering with Obscurity Bias ✅
1. **Analyze horror club collection** (258 movies) to extract taste profile
2. **Extract keywords** from watched movies (murder, slasher, found footage, folk horror, etc.)
3. **Build horror superset** (~2,000 movies) by querying TMDB with top keywords
4. **Calculate similarity** using keywords, genres, cast, and director
5. **Weight by obscurity** - prioritize low vote_count movies to find hidden gems

### Phase 2: Collaborative Filtering (Future)
- Integrate Trakt.tv user overlap data or horror club watch histories
- Find "horror weirdos" who watched the same obscure movies
- Recommend based on what those users also watched

## Project Structure

```
horror-movie-recommender/
├── data/
│   ├── horror_club_collection.csv    # Original 258-movie horror club list
│   ├── horror_profile.json           # Keyword analysis and taste profile
│   └── horror_superset_5k.json       # 2,000-movie curated horror dataset
├── scripts/
│   └── (analysis and building scripts)
├── notebooks/
│   └── (Jupyter notebooks for exploration)
├── docs/
│   └── (documentation and findings)
├── .env                               # API keys (not committed)
└── README.md
```

## Current Status

**Completed:**
- ✅ Analyzed 255 horror movies from club collection
- ✅ Extracted 1,554 unique keywords
- ✅ Identified top keywords: slasher (32), serial killer (26), zombie (21), found footage (19), folk horror (15)
- ✅ Built 2,000-movie horror superset using tiered keyword approach
  - Tier 1 (core): 909 movies - slasher, zombie, found footage, folk horror
  - Tier 2 (strong): 691 movies - occult, demon, creature, haunted house
  - Tier 3 (nice): 145 movies - witch, ritual, gore

**Next Steps:**
- [ ] Build similarity matrix on 2,000-movie superset
- [ ] Implement obscurity weighting algorithm
- [ ] Test with Bad Ben → should recommend Hell House LLC, [REC], Paranormal Activity
- [ ] Explore Trakt.tv API for collaborative filtering

## Key Insights

1. **90th percentile keywords** (≥3 occurrences) = 236 keywords - these represent the group's taste
2. **Found footage** and **folk horror** are well-represented in the collection (both in 90th percentile)
3. **Obscurity matters** - someone who watched Bad Ben is a stronger signal than someone who watched The Exorcist
4. **TMDB 5000 dataset is insufficient** - 90% of horror club movies aren't in the top 5000 movies dataset

## Technology Stack

- **Python** - Data processing and ML
- **TMDB API** - Movie metadata, keywords, cast, crew
- **scikit-learn** - Similarity calculations (cosine similarity, TF-IDF)
- **pandas** - Data manipulation
- **Trakt.tv API** (future) - User overlap data for collaborative filtering

## Setup

1. Clone the repository
2. Copy `.env.example` to `.env` and add your TMDB API key
3. Install dependencies: `pip install -r requirements.txt`
4. Run analysis scripts in `scripts/`

## Contributing

This is a personal project for a horror movie club, but ideas and suggestions are welcome!

## License

MIT

---

*Built with Claude Code by horror enthusiasts, for horror enthusiasts* 🎃
