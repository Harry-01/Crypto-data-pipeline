"""Write each extraction run as an immutable NDJSON file in the landing zone.

Layout:  <root>/<source>/<YYYY-MM-DD>/<source>_<run_id>.json

Files are never overwritten or edited, so the raw layer is a complete, replayable history.
Deduplication happens downstream in dbt (silver layer).
"""

from __future__ import annotations

import io
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

log = logging.getLogger(__name__)


def new_run_id(now: datetime | None = None) -> str:
    return (now or datetime.now(UTC)).strftime("%Y%m%dT%H%M%SZ")


def to_ndjson(records: list[dict[str, Any]], run_id: str, ingested_at: datetime) -> bytes:
    """Serialise records, stamping each with ingestion metadata for lineage."""
    meta = {"_run_id": run_id, "_ingested_at": ingested_at.isoformat()}
    lines = (json.dumps({**r, **meta}, ensure_ascii=False, default=str) for r in records)
    return ("\n".join(lines) + "\n").encode("utf-8")


def relative_path(source: str, run_id: str, ingested_at: datetime) -> str:
    return f"{source}/{ingested_at:%Y-%m-%d}/{source}_{run_id}.json"


class Lander(Protocol):
    def write(self, source: str, records: list[dict[str, Any]], run_id: str) -> str | None: ...


class LocalLander:
    """Writes to a local directory; handy for development and tests (no Databricks needed)."""

    def __init__(self, root: str | Path):
        self.root = Path(root)

    def write(self, source: str, records: list[dict[str, Any]], run_id: str) -> str | None:
        if not records:
            log.warning("%s: no records, nothing landed", source)
            return None
        now = datetime.now(UTC)
        path = self.root / relative_path(source, run_id, now)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(to_ndjson(records, run_id, now))
        log.info("%s: landed %d records -> %s", source, len(records), path)
        return str(path)


class DatabricksVolumeLander:
    """Uploads to a Unity Catalog volume via the Databricks Files API.

    Authentication comes from DATABRICKS_HOST / DATABRICKS_TOKEN (standard SDK env vars).
    """

    def __init__(self, volume_path: str, client=None):
        if client is None:
            from databricks.sdk import WorkspaceClient

            client = WorkspaceClient()
        self.client = client
        self.volume_path = volume_path.rstrip("/")

    def write(self, source: str, records: list[dict[str, Any]], run_id: str) -> str | None:
        if not records:
            log.warning("%s: no records, nothing landed", source)
            return None
        now = datetime.now(UTC)
        path = f"{self.volume_path}/{relative_path(source, run_id, now)}"
        self.client.files.upload(path, io.BytesIO(to_ndjson(records, run_id, now)), overwrite=False)
        log.info("%s: landed %d records -> %s", source, len(records), path)
        return path
