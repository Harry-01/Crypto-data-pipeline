"""Runtime configuration, read from environment variables (optionally via a .env file)."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value else default


def _feeds(value: str | None) -> dict[str, str]:
    """Parse NEWS_FEEDS="name=url,name=url"; fall back to the built-in feed list."""
    from crypto_pipeline.extract.news import DEFAULT_FEEDS

    if not value:
        return dict(DEFAULT_FEEDS)
    pairs = (item.split("=", 1) for item in value.split(",") if "=" in item)
    return {name.strip(): url.strip() for name, url in pairs}


@dataclass(frozen=True)
class Settings:
    # Source APIs
    coingecko_api_key: str | None
    news_feeds: dict[str, str]
    reddit_client_id: str | None
    reddit_client_secret: str | None
    reddit_username: str | None
    reddit_password: str | None
    reddit_user_agent: str
    reddit_subreddit: str

    # Extraction behaviour
    coin_limit: int
    max_pages: int

    # Landing zone
    databricks_catalog: str
    raw_schema: str
    landing_volume: str
    local_landing_dir: str

    @property
    def reddit_enabled(self) -> bool:
        return all(
            [self.reddit_client_id, self.reddit_client_secret, self.reddit_username, self.reddit_password]
        )

    @property
    def volume_path(self) -> str:
        return f"/Volumes/{self.databricks_catalog}/{self.raw_schema}/{self.landing_volume}"

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            coingecko_api_key=os.getenv("COINGECKO_API_KEY"),
            news_feeds=_feeds(os.getenv("NEWS_FEEDS")),
            reddit_client_id=os.getenv("REDDIT_CLIENT_ID"),
            reddit_client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            reddit_username=os.getenv("REDDIT_USERNAME"),
            reddit_password=os.getenv("REDDIT_PASSWORD"),
            reddit_user_agent=os.getenv(
                "REDDIT_USER_AGENT", "crypto-data-pipeline/1.0 (portfolio project)"
            ),
            reddit_subreddit=os.getenv("REDDIT_SUBREDDIT", "CryptoCurrency"),
            coin_limit=_int("COIN_LIMIT", 30),
            max_pages=_int("MAX_PAGES", 3),
            databricks_catalog=os.getenv("DATABRICKS_CATALOG", "workspace"),
            raw_schema=os.getenv("RAW_SCHEMA", "crypto_raw"),
            landing_volume=os.getenv("LANDING_VOLUME", "landing"),
            local_landing_dir=os.getenv("LOCAL_LANDING_DIR", "data/landing"),
        )
