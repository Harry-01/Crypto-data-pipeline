import pytest

from crypto_pipeline.extract import reddit
from crypto_pipeline.extract.coingecko import Coin
from tests.conftest import FakeResponse, FakeSession

BTC = Coin("bitcoin", "Bitcoin", "btc")


def _page(ids, after=None):
    return FakeResponse({"data": {"after": after, "children": [
        {"data": {"id": i, "title": f"Bitcoin is amazing {i}", "score": 10, "num_comments": 2,
                  "created_utc": 1790000000, "permalink": f"/r/CryptoCurrency/{i}"}} for i in ids
    ]}})


def test_build_query():
    assert reddit.build_query(BTC) == '"Bitcoin" OR BTC'


def test_search_paginates_and_dedupes():
    session = FakeSession([_page(["a", "b"], after="t3_b"), _page(["b", "c"])])
    records = reddit.search_coin_posts(session, "tok", BTC, max_pages=5, pause_seconds=0)

    assert [r["post_id"] for r in records] == ["a", "b", "c"]
    assert session.calls[1]["params"]["after"] == "t3_b"
    assert records[0]["coin_id"] == "bitcoin"
    assert records[0]["created_utc"].endswith("+00:00")
    assert records[0]["permalink"] == "https://www.reddit.com/r/CryptoCurrency/a"
    assert records[0]["sentiment_label"] == "positive"


def test_fetch_requires_credentials():
    with pytest.raises(ValueError):
        reddit.fetch_posts_for_coins(FakeSession([]), [BTC], None, None, None, None)


def test_fetch_continues_after_one_coin_fails():
    eth = Coin("ethereum", "Ethereum", "eth")
    session = FakeSession([
        FakeResponse({"access_token": "tok"}),
        FakeResponse(status=500),       # bitcoin search fails
        _page(["x"]),                   # ethereum search succeeds
    ])
    records = reddit.fetch_posts_for_coins(session, [BTC, eth], "id", "secret", "u", "p", pause_seconds=0)
    assert [(r["post_id"], r["coin_id"]) for r in records] == [("x", "ethereum")]
