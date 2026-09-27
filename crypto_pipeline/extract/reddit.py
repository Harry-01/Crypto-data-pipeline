"""Reddit: recent r/CryptoCurrency posts mentioning each tracked coin (OAuth2 script app)."""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from typing import Any

import requests

from crypto_pipeline import sentiment
from crypto_pipeline.extract.coingecko import Coin
from crypto_pipeline.http import DEFAULT_TIMEOUT

log = logging.getLogger(__name__)

TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
API_URL = "https://oauth.reddit.com"
MAX_SELFTEXT = 5000


def get_access_token(
    session: requests.Session, client_id: str, client_secret: str, username: str, password: str
) -> str:
    resp = session.post(
        TOKEN_URL,
        auth=(client_id, client_secret),
        data={"grant_type": "password", "username": username, "password": password},
        timeout=DEFAULT_TIMEOUT,
    )
    resp.raise_for_status()
    token = resp.json().get("access_token")
    if not token:
        raise RuntimeError(f"Reddit did not return an access token: {resp.text[:200]}")
    return token


def build_query(coin: Coin) -> str:
    """Match the coin's full name or ticker, e.g. '"Bitcoin" OR BTC'."""
    return f'"{coin.name}" OR {coin.symbol.upper()}'


def to_record(post: dict[str, Any], coin: Coin, subreddit: str) -> dict[str, Any]:
    created = post.get("created_utc")
    compound = sentiment.score(post.get("title"))
    return {
        "post_id": post.get("id"),
        "coin_id": coin.coin_id,
        "subreddit": subreddit,
        "title": post.get("title"),
        "selftext": (post.get("selftext") or "")[:MAX_SELFTEXT],
        "author": post.get("author"),
        "score": post.get("score"),
        "upvote_ratio": post.get("upvote_ratio"),
        "num_comments": post.get("num_comments"),
        "created_utc": (
            datetime.fromtimestamp(created, tz=UTC).isoformat() if created is not None else None
        ),
        "url": post.get("url"),
        "permalink": f"https://www.reddit.com{post.get('permalink', '')}",
        "sentiment_compound": compound,
        "sentiment_label": sentiment.label(compound),
    }


def search_coin_posts(
    session: requests.Session,
    token: str,
    coin: Coin,
    subreddit: str = "CryptoCurrency",
    limit: int = 100,
    max_pages: int = 3,
    time_filter: str = "week",
    pause_seconds: float = 1.0,
) -> list[dict[str, Any]]:
    """Search one subreddit for a coin, paginating with Reddit's `after` cursor."""
    headers = {"Authorization": f"bearer {token}"}
    params: dict[str, Any] = {
        "q": build_query(coin),
        "restrict_sr": "true",
        "sort": "new",
        "t": time_filter,
        "limit": limit,
        "type": "link",
    }
    seen: set[str] = set()
    records: list[dict[str, Any]] = []
    for _ in range(max_pages):
        resp = session.get(
            f"{API_URL}/r/{subreddit}/search", headers=headers, params=params, timeout=DEFAULT_TIMEOUT
        )
        resp.raise_for_status()
        data = resp.json().get("data", {})
        for child in data.get("children", []):
            post = child.get("data", {})
            if post.get("id") and post["id"] not in seen:
                seen.add(post["id"])
                records.append(to_record(post, coin, subreddit))
        after = data.get("after")
        if not after:
            break
        params["after"] = after
        time.sleep(pause_seconds)  # stay well inside Reddit's free-tier rate limit
    return records


def fetch_posts_for_coins(
    session: requests.Session,
    coins: list[Coin],
    client_id: str | None,
    client_secret: str | None,
    username: str | None,
    password: str | None,
    subreddit: str = "CryptoCurrency",
    max_pages: int = 3,
    pause_seconds: float = 1.0,
) -> list[dict[str, Any]]:
    if not all([client_id, client_secret, username, password]):
        raise ValueError("Reddit credentials are not fully set (REDDIT_CLIENT_ID/SECRET/USERNAME/PASSWORD)")

    token = get_access_token(session, client_id, client_secret, username, password)  # type: ignore[arg-type]
    records: list[dict[str, Any]] = []
    for coin in coins:
        try:
            records.extend(
                search_coin_posts(
                    session, token, coin, subreddit=subreddit, max_pages=max_pages, pause_seconds=pause_seconds
                )
            )
        except requests.RequestException as exc:  # one bad coin should not sink the whole run
            log.warning("Reddit: search failed for %s: %s", coin.coin_id, exc)
        time.sleep(pause_seconds)
    log.info("Reddit: fetched %d post-coin records for %d coins", len(records), len(coins))
    return records
