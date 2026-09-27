"""Command-line entry point.

    python -m crypto_pipeline setup                          # create schema + volume in Databricks
    python -m crypto_pipeline extract --target local         # land raw files under ./data/landing
    python -m crypto_pipeline extract --target databricks    # land raw files in the UC volume
    python -m crypto_pipeline extract --sources news         # run a single source
"""

from __future__ import annotations

import argparse
import logging
import sys

from crypto_pipeline.config import Settings
from crypto_pipeline.extract import coingecko, news, reddit
from crypto_pipeline.http import build_session
from crypto_pipeline.load.landing import DatabricksVolumeLander, Lander, LocalLander, new_run_id

SOURCES = ("coingecko", "news", "reddit")
log = logging.getLogger("crypto_pipeline")


def make_lander(target: str, settings: Settings) -> Lander:
    if target == "databricks":
        return DatabricksVolumeLander(settings.volume_path)
    return LocalLander(settings.local_landing_dir)


def run_extract(sources: list[str], lander: Lander, settings: Settings) -> int:
    """Extract the requested sources and land them. Returns the number of failed sources."""
    run_id = new_run_id()
    session = build_session(user_agent=settings.reddit_user_agent)

    # CoinGecko defines the coin universe that news and Reddit are matched against,
    # so it is always fetched; it is only *landed* when requested.
    try:
        markets = coingecko.fetch_markets(session, settings.coingecko_api_key, settings.coin_limit)
    except Exception:  # noqa: BLE001 - without the coin list no source can run
        log.exception("coingecko: could not fetch the coin universe; aborting run")
        return len(sources)
    coins = coingecko.coins_from_markets(markets)

    failures = 0
    for source in sources:
        try:
            if source == "coingecko":
                records = markets
            elif source == "news":
                records = news.fetch_articles(session, coins, settings.news_feeds)
            elif source == "reddit":
                if not settings.reddit_enabled:
                    log.warning("reddit: credentials not configured, skipping")
                    continue
                records = reddit.fetch_posts_for_coins(
                    session,
                    coins,
                    settings.reddit_client_id,
                    settings.reddit_client_secret,
                    settings.reddit_username,
                    settings.reddit_password,
                    subreddit=settings.reddit_subreddit,
                    max_pages=settings.max_pages,
                )
            else:
                raise ValueError(f"unknown source {source!r}")
            lander.write(source, records, run_id)
        except Exception:  # noqa: BLE001 - report every source, then fail the run
            failures += 1
            log.exception("%s: extraction failed", source)
    return failures


def run_setup(settings: Settings) -> None:
    """Idempotently create the raw schema and managed landing volume in Unity Catalog."""
    from databricks.sdk import WorkspaceClient
    from databricks.sdk.errors import ResourceAlreadyExists
    from databricks.sdk.service.catalog import VolumeType

    w = WorkspaceClient()
    try:
        w.schemas.create(name=settings.raw_schema, catalog_name=settings.databricks_catalog)
        log.info("created schema %s.%s", settings.databricks_catalog, settings.raw_schema)
    except ResourceAlreadyExists:
        log.info("schema %s.%s already exists", settings.databricks_catalog, settings.raw_schema)
    try:
        w.volumes.create(
            catalog_name=settings.databricks_catalog,
            schema_name=settings.raw_schema,
            name=settings.landing_volume,
            volume_type=VolumeType.MANAGED,
        )
        log.info("created volume %s", settings.volume_path)
    except ResourceAlreadyExists:
        log.info("volume %s already exists", settings.volume_path)


def parse_sources(value: str) -> list[str]:
    sources = list(SOURCES) if value == "all" else [s.strip() for s in value.split(",") if s.strip()]
    unknown = set(sources) - set(SOURCES)
    if unknown:
        raise argparse.ArgumentTypeError(f"unknown source(s): {', '.join(sorted(unknown))}")
    return sources


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="crypto_pipeline", description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)

    ext = sub.add_parser("extract", help="extract sources and land raw files")
    ext.add_argument("--sources", type=parse_sources, default=list(SOURCES), help="all, or comma-separated list")
    ext.add_argument("--target", choices=("local", "databricks"), default="local")

    sub.add_parser("setup", help="create the raw schema and landing volume in Databricks")

    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = Settings.from_env()

    if args.command == "setup":
        run_setup(settings)
        return 0

    failures = run_extract(args.sources, make_lander(args.target, settings), settings)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
