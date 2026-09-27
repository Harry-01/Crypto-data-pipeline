-- Current attributes for every coin ever tracked (latest snapshot wins).
select
    coin_id,
    symbol,
    name,
    market_cap_rank,
    price_usd        as latest_price_usd,
    market_cap_usd   as latest_market_cap_usd,
    last_updated_at,
    first_seen_at
from (
    select
        *,
        min(last_updated_at) over (partition by coin_id) as first_seen_at,
        row_number() over (partition by coin_id order by last_updated_at desc) as rn
    from {{ ref('silver_coin_market_snapshots') }}
)
where rn = 1
