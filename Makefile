.PHONY: install test lint setup extract-local extract dbt-build airflow

install:
	pip install -r requirements-dev.txt

test:
	pytest -q

lint:
	ruff check .

setup:            ## create the raw schema + landing volume in Databricks
	python -m crypto_pipeline setup

extract-local:    ## land raw files under ./data/landing (no Databricks needed)
	python -m crypto_pipeline extract --target local

extract:          ## land raw files in the Databricks volume
	python -m crypto_pipeline extract --target databricks

dbt-build:        ## bronze -> silver -> gold, then run all data tests
	cd dbt && dbt build --profiles-dir .

airflow:          ## run Airflow locally on http://localhost:8080
	docker compose up --build
