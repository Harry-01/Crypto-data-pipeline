import json
from datetime import UTC, datetime

from crypto_pipeline import __main__ as cli
from crypto_pipeline.config import Settings
from crypto_pipeline.load import landing


def test_to_ndjson_adds_lineage_columns():
    ts = datetime(2026, 9, 27, 10, 0, tzinfo=UTC)
    lines = landing.to_ndjson([{"a": 1}, {"a": 2}], "run1", ts).decode().splitlines()
    assert [json.loads(line) for line in lines] == [
        {"a": 1, "_run_id": "run1", "_ingested_at": "2026-09-27T10:00:00+00:00"},
        {"a": 2, "_run_id": "run1", "_ingested_at": "2026-09-27T10:00:00+00:00"},
    ]


def test_local_lander_writes_partitioned_file(tmp_path):
    path = landing.LocalLander(tmp_path).write("news", [{"x": 1}], "20260927T100000Z")
    assert path.endswith("news_20260927T100000Z.json")
    assert "/news/" in path
    assert landing.LocalLander(tmp_path).write("news", [], "r") is None


class FakeFiles:
    def __init__(self):
        self.uploads = []

    def upload(self, path, contents, overwrite=None):
        self.uploads.append((path, contents.read(), overwrite))


class FakeWorkspace:
    def __init__(self):
        self.files = FakeFiles()


def test_databricks_lander_uploads_to_volume():
    ws = FakeWorkspace()
    lander = landing.DatabricksVolumeLander("/Volumes/workspace/crypto_raw/landing/", client=ws)
    path = lander.write("coingecko", [{"coin_id": "bitcoin"}], "run1")

    uploaded_path, body, overwrite = ws.files.uploads[0]
    assert path == uploaded_path
    assert uploaded_path.startswith("/Volumes/workspace/crypto_raw/landing/coingecko/")
    assert json.loads(body)["coin_id"] == "bitcoin"
    assert overwrite is False  # landed files are immutable


def test_run_extract_lands_sources_and_counts_failures(monkeypatch, tmp_path):
    markets = [{"coin_id": "bitcoin", "name": "Bitcoin", "symbol": "btc"}]
    monkeypatch.setattr(cli.coingecko, "fetch_markets", lambda *a, **k: markets)
    monkeypatch.setattr(cli.news, "fetch_articles", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("down")))
    monkeypatch.delenv("REDDIT_CLIENT_ID", raising=False)
    settings = Settings.from_env()

    lander = landing.LocalLander(tmp_path)
    failures = cli.run_extract(["coingecko", "news", "reddit"], lander, settings)

    assert failures == 1  # news failed; reddit skipped (no credentials) is not a failure
    assert len(list((tmp_path / "coingecko").rglob("*.json"))) == 1
    assert not (tmp_path / "news").exists()


def test_parse_sources():
    assert cli.parse_sources("all") == list(cli.SOURCES)
    assert cli.parse_sources("news, coingecko") == ["news", "coingecko"]
