-- Market-wide daily news sentiment by feed, including articles not tied to a tracked coin.
with articles as (
    -- an article can be matched to several coins; count it once
    select distinct article_id, feed, to_date(event_at) as news_date, sentiment_compound, sentiment_label
    from {{ ref('silver_news_articles') }}
)

select
    news_date,
    feed,
    count(*)                                   as articles,
    avg(sentiment_compound)                    as sentiment_avg,
    count_if(sentiment_label = 'positive')     as positive_articles,
    count_if(sentiment_label = 'neutral')      as neutral_articles,
    count_if(sentiment_label = 'negative')     as negative_articles
from articles
group by 1, 2
