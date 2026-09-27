{{ config(enabled=reddit_enabled()) }}
-- One row per Reddit post x coin. Scores and comment counts change over time,
-- so keep the most recent observation.
with typed as (
    select
        post_id,
        coin_id,
        subreddit,
        title,
        author,
        cast(score as int)               as score,
        upvote_ratio,
        cast(num_comments as int)        as num_comments,
        cast(created_utc as timestamp)   as created_at,
        permalink,
        sentiment_compound,
        sentiment_label,
        cast(_ingested_at as timestamp)  as ingested_at
    from {{ ref('bronze_reddit_posts') }}
    where post_id is not null
      and coin_id is not null
),

ranked as (
    select
        *,
        row_number() over (
            partition by post_id, coin_id
            order by ingested_at desc
        ) as rn
    from typed
)

select * except (rn)
from ranked
where rn = 1
