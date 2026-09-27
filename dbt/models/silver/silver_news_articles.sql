-- One row per article x coin. The same article is re-landed on every run while it
-- stays in the feed, so keep only the first time we saw it.
with typed as (
    select
        article_id,
        coin_id,
        feed,
        title,
        summary,
        link,
        cast(published_at as timestamp)  as published_at,
        sentiment_compound,
        sentiment_label,
        cast(_ingested_at as timestamp)  as ingested_at
    from {{ ref('bronze_news_articles') }}
    where article_id is not null
),

ranked as (
    select
        *,
        row_number() over (
            partition by article_id, coalesce(coin_id, '__market__')
            order by ingested_at asc
        ) as rn
    from typed
)

select
    * except (rn),
    coalesce(published_at, ingested_at) as event_at
from ranked
where rn = 1
