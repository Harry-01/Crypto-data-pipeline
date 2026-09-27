from crypto_pipeline.extract import coingecko
from tests.conftest import FakeResponse, FakeSession

RAW = [
    {"id": "bitcoin", "symbol": "btc", "name": "Bitcoin", "current_price": 65000.5, "market_cap_rank": 1,
     "last_updated": "2026-09-27T10:00:00.000Z", "image": "ignored"},
    {"id": "ethereum", "symbol": "eth", "name": "Ethereum", "current_price": 3200.0, "market_cap_rank": 2,
     "last_updated": "2026-09-27T10:00:00.000Z"},
]


def test_fetch_markets_maps_fields_and_sends_key():
    session = FakeSession([FakeResponse(RAW)])
    records = coingecko.fetch_markets(session, api_key="demo", limit=2)

    assert [r["coin_id"] for r in records] == ["bitcoin", "ethereum"]
    assert "image" not in records[0]
    assert set(records[0]) == set(coingecko.MARKET_FIELDS.values())
    call = session.calls[0]
    assert call["headers"] == {"x-cg-demo-api-key": "demo"}
    assert call["params"]["per_page"] == 2


def test_coins_from_markets_skips_incomplete_rows():
    records = [coingecko.to_record(r) for r in RAW] + [{"coin_id": None, "name": "x", "symbol": "x"}]
    coins = coingecko.coins_from_markets(records)
    assert [c.coin_id for c in coins] == ["bitcoin", "ethereum"]
