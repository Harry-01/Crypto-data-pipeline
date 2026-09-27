# Airflow 3 image with the pipeline + dbt installed in an isolated virtualenv.
FROM apache/airflow:3.3.2-python3.12

USER root
RUN python -m venv /opt/pipeline-venv && chown -R airflow: /opt/pipeline-venv

USER airflow
COPY requirements.txt /tmp/requirements.txt
RUN /opt/pipeline-venv/bin/pip install --no-cache-dir -r /tmp/requirements.txt

ENV PIPELINE_VENV_BIN=/opt/pipeline-venv/bin \
    PIPELINE_PROJECT_DIR=/opt/airflow/project
