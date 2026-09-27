{#-
  Helpers for reading the raw landing zone with Databricks' read_files().
  An explicit schema is used for every source so that type inference can never
  drift between runs; casting and cleaning happen in the silver layer.
-#}

{% macro landing_schema(source_name) %}
  {%- set common = "_run_id STRING, _ingested_at STRING" -%}
  {%- set schemas = {
    "coingecko": "coin_id STRING, symbol STRING, name STRING, market_cap_rank BIGINT, current_price DOUBLE, market_cap DOUBLE, total_volume DOUBLE, high_24h DOUBLE, low_24h DOUBLE, price_change_percentage_24h DOUBLE, circulating_supply DOUBLE, last_updated STRING",
    "news": "article_id STRING, feed STRING, title STRING, summary STRING, link STRING, published_at STRING, sentiment_compound DOUBLE, sentiment_label STRING, coin_id STRING",
    "reddit": "post_id STRING, coin_id STRING, subreddit STRING, title STRING, selftext STRING, author STRING, score BIGINT, upvote_ratio DOUBLE, num_comments BIGINT, created_utc STRING, url STRING, permalink STRING, sentiment_compound DOUBLE, sentiment_label STRING",
  } -%}
  {{- return(schemas[source_name] ~ ", " ~ common) -}}
{% endmacro %}


{% macro read_landing(source_name) %}
  read_files(
    '{{ var("landing_path") }}/{{ source_name }}/*/*.json',
    format => 'json',
    schema => '{{ landing_schema(source_name) }}'
  )
{% endmacro %}


{#- Bronze body shared by every source: raw columns + file lineage, append-only. -#}
{% macro bronze_from_landing(source_name) %}
select
  *,
  _metadata.file_path              as _source_file,
  _metadata.file_modification_time as _file_modified_at,
  current_timestamp()              as _loaded_at
from {{ read_landing(source_name) }}
{% if is_incremental() %}
-- only pick up files that have not been loaded before
where _metadata.file_path not in (select distinct _source_file from {{ this }})
{% endif %}
{% endmacro %}


{#- Reddit API access is optional (new apps need Reddit approval); ENABLE_REDDIT=false switches it off. -#}
{% macro reddit_enabled() %}
  {{ return(env_var('ENABLE_REDDIT', 'true') | lower == 'true') }}
{% endmacro %}
