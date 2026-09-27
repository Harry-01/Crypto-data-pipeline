import pytest

from crypto_pipeline.extract import news
from crypto_pipeline.extract.coingecko import Coin
from tests.conftest import FakeResponse, FakeSession

COINS = [Coin("bitcoin", "Bitcoin", "btc"), Coin("ethereum", "Ethereum", "eth"), Coin("sonic", "Sonic", "s")]

RSS = b"""<?xml version="1.0"?>
<rss version="2.0"><channel><title>Test</title>
<item><title>Bitcoin and ETH rally to record highs</title><link>https://ex.com/a</link>
  <description>&lt;p&gt;Great gains for investors.&lt;/p&gt;</description>
  <pubDate>Sat, 27 Sep 2026 10:00:00 GMT</pubDate></item>
<item><title>Regulators warn of crash risk</title><link>https://ex.com/b</link>
  <description>Markets fear heavy losses</description>
  <pubDate>Sat, 27 Sep 2026 11:00:00 GMT</pubDate></item>
<item><title></title><link>https://ex.com/empty</link></item>
</channel></rss>"""


def test_parse_feed_tags_coins_and_scores_sentiment():
    rows = news.parse_feed("test", RSS, news.build_matchers(COINS))

    rally = [r for r in rows if r["link"] == "https://ex.com/a"]
    assert sorted(r["coin_id"] for r in rally) == ["bitcoin", "ethereum"]  # name + ticker match
    assert rally[0]["sentiment_label"] == "positive"
    assert rally[0]["summary"] == "Great gains for investors."  # HTML stripped
    assert rally[0]["published_at"] == "2026-09-27T10:00:00+00:00"
    assert rally[0]["article_id"] == rally[1]["article_id"]

    crash = [r for r in rows if r["link"] == "https://ex.com/b"]
    assert [r["coin_id"] for r in crash] == [None]  # untagged article kept for market-wide sentiment
    assert crash[0]["sentiment_label"] == "negative"

    assert not any(r["link"] == "https://ex.com/empty" for r in rows)


def test_short_tickers_are_not_matched_as_words():
    matchers = news.build_matchers(COINS)
    assert news.match_coins("It's a sonic boom", matchers) == ["sonic"]  # name still matches
    assert news.match_coins("S and P 500 futures", matchers) == []  # ticker 'S' ignored


def test_fetch_articles_survives_one_dead_feed():
    session = FakeSession([FakeResponse(status=503), FakeResponse(content=RSS)])
    rows = news.fetch_articles(session, COINS, {"dead": "https://dead", "ok": "https://ok"})
    assert {r["feed"] for r in rows} == {"ok"}


def test_fetch_articles_fails_when_every_feed_fails():
    session = FakeSession([FakeResponse(status=500)])
    with pytest.raises(RuntimeError):
        news.fetch_articles(session, COINS, {"dead": "https://dead"})
