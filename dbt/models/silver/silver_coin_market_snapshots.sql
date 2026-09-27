-- One row per coin per CoinGecko update, typed and de-duplicated.
with typed as (
    select
        coin_id,
        lower(symbol)                                  as symbol,
        name,
        cast(market_cap_rank as int)                   as market_cap_rank,
        current_price                                  as price_usd,
        market_cap                                     as market_cap_usd,
        total_volume                                   as volume_24h_usd,
        high_24h                                       as high_24h_usd,
        low_24h                                        as low_24h_usd,
        price_change_percentage_24h                    as price_change_pct_24h,
        circulating_supply,
        cast(last_updated as timestamp)                as last_updated_at,
        cast(_ingested_at as timestamp)                as ingested_at,
        _run_id                                        as run_id
    from {{ ref('bronze_coin_markets') }}
    where coin_id is not null
      and current_price is not null
),

ranked as (
    select
        *,
        row_number() over (
            partition by coin_id, last_updated_at
            order by ingested_at desc
        ) as rn
    from typed
)

select * except (rn)
from ranked
where rn = 1
