"""Crypto news from public RSS feeds, tagged to tracked coins and scored for sentiment."""

from __future__ import annotations

import hashlib
import html
import logging
import re
from datetime import UTC, datetime
from typing import Any

import feedparser
import requests

from crypto_pipeline import sentiment
from crypto_pipeline.extract.coingecko import Coin
from crypto_pipeline.http import DEFAULT_TIMEOUT

log = logging.getLogger(__name__)

DEFAULT_FEEDS = {
    "coindesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "cointelegraph": "https://cointelegraph.com/rss",
    "decrypt": "https://decrypt.co/feed",
}
MAX_SUMMARY = 2000
MIN_TICKER_LEN = 3  # short tickers (e.g. "S", "OP") match too much ordinary text

_TAG_RE = re.compile(r"<[^>]+>")


def clean_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", html.unescape(_TAG_RE.sub(" ", value or ""))).strip()


def article_id(link: str, title: str) -> str:
    return hashlib.sha1(f"{link}|{title}".encode()).hexdigest()


def _published_iso(entry: Any) -> str | None:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not parsed:
        return None
    return datetime(*parsed[:6], tzinfo=UTC).isoformat()


def build_matchers(coins: list[Coin]) -> list[tuple[Coin, re.Pattern[str], re.Pattern[str] | None]]:
    """Name matches case-insensitively; ticker must appear in upper case as a whole word."""
    matchers = []
    for coin in coins:
        name_re = re.compile(rf"\b{re.escape(coin.name)}\b", re.IGNORECASE)
        ticker = coin.symbol.upper()
        ticker_re = re.compile(rf"\b{re.escape(ticker)}\b") if len(ticker) >= MIN_TICKER_LEN else None
        matchers.append((coin, name_re, ticker_re))
    return matchers


def match_coins(text: str, matchers) -> list[str]:
    return [
        coin.coin_id
        for coin, name_re, ticker_re in matchers
        if name_re.search(text) or (ticker_re is not None and ticker_re.search(text))
    ]


def parse_feed(feed_name: str, content: bytes, matchers) -> list[dict[str, Any]]:
    """One row per (article, matched coin); untagged articles are kept with coin_id = None."""
    parsed = feedparser.parse(content)
    rows: list[dict[str, Any]] = []
    for entry in parsed.entries:
        title = clean_text(entry.get("title"))
        link = entry.get("link") or ""
        if not title or not link:
            continue
        summary = clean_text(entry.get("summary"))[:MAX_SUMMARY]
        compound = sentiment.score(f"{title}. {summary}" if summary else title)
        base = {
            "article_id": article_id(link, title),
            "feed": feed_name,
            "title": title,
            "summary": summary,
            "link": link,
            "published_at": _published_iso(entry),
            "sentiment_compound": compound,
            "sentiment_label": sentiment.label(compound),
        }
        coin_ids = match_coins(f"{title} {summary}", matchers) or [None]
        rows.extend({**base, "coin_id": cid} for cid in coin_ids)
    return rows


def fetch_articles(
    session: requests.Session, coins: list[Coin], feeds: dict[str, str] | None = None
) -> list[dict[str, Any]]:
    feeds = feeds or DEFAULT_FEEDS
    matchers = build_matchers(coins)
    rows: list[dict[str, Any]] = []
    for name, url in feeds.items():
        try:
            resp = session.get(url, timeout=DEFAULT_TIMEOUT)
            resp.raise_for_status()
            feed_rows = parse_feed(name, resp.content, matchers)
            log.info("News: %s -> %d article-coin rows", name, len(feed_rows))
            rows.extend(feed_rows)
        except requests.RequestException as exc:  # one dead feed should not sink the run
            log.warning("News: feed %s failed: %s", name, exc)
    if not rows:
        raise RuntimeError("News: no articles fetched from any feed")
    return rows
