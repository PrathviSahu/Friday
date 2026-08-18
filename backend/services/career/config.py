"""backend/services/career/config.py — Configuration for Career OS Job Pipeline.

Contains safe configuration defaults for job ingestion, deduplication, and matching.
Does NOT store secrets, tokens, or API keys.
"""

# Master toggle for background job search ingestion
JOB_SEARCH_ENABLED: bool = True

# Maximum raw results per provider search execution
MAX_RESULTS: int = 50

# Toggle for SHA-256 job signature deduplication
DEDUP_ENABLED: bool = True

# Minimum match score threshold (0-100) for highlighting top matches
MIN_MATCH_SCORE: float = 0.0

# Safety dry-run toggle (prevents any external side-effects or automated applications)
DRY_RUN: bool = True
