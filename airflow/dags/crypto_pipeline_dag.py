"""Airflow DAG: extract each source into the Databricks landing volume, then run dbt build.

    extract_coingecko ─┐
    extract_news ──────┼──> dbt_build (bronze -> silver -> gold, with tests)
    extract_reddit ────┘
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import dag

PROJECT_DIR = os.getenv("PIPELINE_PROJECT_DIR", "/opt/airflow/project")
# The pipeline and dbt live in their own virtualenv so their dependencies never clash with Airflow's.
VENV_BIN = os.getenv("PIPELINE_VENV_BIN", "/opt/pipeline-venv/bin")

SOURCES = ["coingecko", "news"]
if os.getenv("ENABLE_REDDIT", "true").lower() == "true":
    SOURCES.append("reddit")


@dag(
    dag_id="crypto_pipeline",
    description="Crypto prices + news/Reddit sentiment into a Databricks lakehouse",
    schedule="0 */6 * * *",  # every 6 hours
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=5)},
    tags=["crypto", "databricks", "dbt"],
)
def crypto_pipeline():
    extract_tasks = [
        BashOperator(
            task_id=f"extract_{source}",
            cwd=PROJECT_DIR,
            bash_command=f"{VENV_BIN}/python -m crypto_pipeline extract --sources {source} --target databricks",
        )
        for source in SOURCES
    ]

    dbt_build = BashOperator(
        task_id="dbt_build",
        cwd=f"{PROJECT_DIR}/dbt",
        bash_command=f"{VENV_BIN}/dbt build --profiles-dir . --target dev",
        # still transform whatever landed if one source failed; the DAG run is marked failed anyway
        trigger_rule="all_done",
    )

    extract_tasks >> dbt_build


crypto_pipeline()
