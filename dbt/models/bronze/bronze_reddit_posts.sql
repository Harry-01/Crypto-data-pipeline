{{ config(enabled=reddit_enabled()) }}
-- Raw Reddit posts (one row per post x coin searched), appended exactly as landed.
{{ bronze_from_landing('reddit') }}
