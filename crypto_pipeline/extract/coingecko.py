"""CoinGecko: market snapshot for the top-N coins by market cap."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import requests

from crypto_pipeline.http import DEFAULT_TIMEOUT

log = logging.getLogger(__name__)

BASE_URL = "https://api.coingecko.com/api/v3"

# CoinGecko field -> landed column name
MARKET_FIELDS = {
    "id": "coin_id",
    "symbol": "symbol",
    "name": "name",
    "market_cap_rank": "market_cap_rank",
    "current_price": "current_price",
    "market_cap": "market_cap",
    "total_volume": "total_volume",
    "high_24h": "high_24h",
    "low_24h": "low_24h",
    "price_change_percentage_24h": "price_change_percentage_24h",
    "circulating_supply": "circulating_supply",
    "last_updated": "last_updated",
}


@dataclass(frozen=True)
class Coin:
    """Identifiers used to look a coin up in the news and Reddit sources."""

    coin_id: str
    name: str
    symbol: str


def to_record(raw: dict[str, Any]) -> dict[str, Any]:
    return {target: raw.get(source) for source, target in MARKET_FIELDS.items()}


def fetch_markets(session: requests.Session, api_key: str | None, limit: int = 30) -> list[dict[str, Any]]:
    """Fetch one market snapshot for the top `limit` coins (max 250 per CoinGecko page)."""
    headers = {"x-cg-demo-api-key": api_key} if api_key else {}
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": min(limit, 250),
        "page": 1,
    }
    resp = session.get(f"{BASE_URL}/coins/markets", params=params, headers=headers, timeout=DEFAULT_TIMEOUT)
    resp.raise_for_status()
    records = [to_record(c) for c in resp.json()]
    log.info("CoinGecko: fetched %d market records", len(records))
    return records


def coins_from_markets(records: list[dict[str, Any]]) -> list[Coin]:
    return [
        Coin(coin_id=r["coin_id"], name=r["name"], symbol=r["symbol"])
        for r in records
        if r.get("coin_id") and r.get("name") and r.get("symbol")
    ]
