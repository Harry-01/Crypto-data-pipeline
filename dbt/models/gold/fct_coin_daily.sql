-- Daily grain: one row per coin per UTC day, combining market data with
-- news and Reddit activity and sentiment.
with prices as (
    select
        coin_id,
        to_date(last_updated_at)                       as market_date,
        max_by(price_usd, last_updated_at)             as close_price_usd,
        min(price_usd)                                 as min_observed_price_usd,
        max(price_usd)                                 as max_observed_price_usd,
        max_by(market_cap_usd, last_updated_at)        as market_cap_usd,
        max_by(volume_24h_usd, last_updated_at)        as volume_24h_usd,
        count(*)                                       as price_snapshots
    from {{ ref('silver_coin_market_snapshots') }}
    group by 1, 2
),

news as (
    select
        coin_id,
        to_date(event_at)                              as market_date,
        count(distinct article_id)                     as news_articles,
        avg(sentiment_compound)                        as news_sentiment_avg,
        count_if(sentiment_label = 'positive')         as news_positive,
        count_if(sentiment_label = 'negative')         as news_negative
    from {{ ref('silver_news_articles') }}
    where coin_id is not null
    group by 1, 2
),

{% if reddit_enabled() %}
reddit as (
    select
        coin_id,
        to_date(created_at)                            as market_date,
        count(distinct post_id)                        as reddit_posts,
        sum(score)                                     as reddit_score,
        sum(num_comments)                              as reddit_comments,
        avg(sentiment_compound)                        as reddit_sentiment_avg
    from {{ ref('silver_reddit_posts') }}
    group by 1, 2
),
{% else %}
reddit as (
    select
        cast(null as string) as coin_id,
        cast(null as date)   as market_date,
        cast(null as bigint) as reddit_posts,
        cast(null as bigint) as reddit_score,
        cast(null as bigint) as reddit_comments,
        cast(null as double) as reddit_sentiment_avg
    where false
),
{% endif %}

spine as (
    select coin_id, market_date from prices
    union
    select coin_id, market_date from news
    union
    select coin_id, market_date from reddit
)

select
    s.coin_id,
    s.market_date,
    c.symbol,
    c.name,
    p.close_price_usd,
    p.close_price_usd
        / nullif(lag(p.close_price_usd) over (partition by s.coin_id order by s.market_date), 0)
        - 1                                           as price_change_pct_1d,
    p.min_observed_price_usd,
    p.max_observed_price_usd,
    p.market_cap_usd,
    p.volume_24h_usd,
    coalesce(p.price_snapshots, 0)                    as price_snapshots,
    coalesce(n.news_articles, 0)                      as news_articles,
    n.news_sentiment_avg,
    coalesce(n.news_positive, 0)                      as news_positive,
    coalesce(n.news_negative, 0)                      as news_negative,
    coalesce(r.reddit_posts, 0)                       as reddit_posts,
    coalesce(r.reddit_score, 0)                       as reddit_score,
    coalesce(r.reddit_comments, 0)                    as reddit_comments,
    r.reddit_sentiment_avg,
    current_timestamp()                               as _built_at
from spine s
left join {{ ref('dim_coins') }} c on c.coin_id = s.coin_id
left join prices p on p.coin_id = s.coin_id and p.market_date = s.market_date
left join news   n on n.coin_id = s.coin_id and n.market_date = s.market_date
left join reddit r on r.coin_id = s.coin_id and r.market_date = s.market_date
