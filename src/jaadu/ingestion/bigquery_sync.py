from __future__ import annotations

import pandas as pd
from jaadu.google import settings
from jaadu.google.clients import bigquery_client


def maybe_export(observations: pd.DataFrame) -> dict:
    """Copy the observation panel to BigQuery when a project is configured.

    Local parquet remains the source of truth for investigate / evaluate.
    Failure never aborts ingest.
    """
    if observations is None or observations.empty:
        return {"exported": False, "reason": "empty"}
    if not settings.project_id():
        return {"exported": False, "reason": "GOOGLE_CLOUD_PROJECT not set"}
    client = bigquery_client()
    if client is None:
        return {"exported": False, "reason": "bigquery client unavailable"}
    dataset_id = settings.bigquery_dataset()
    table_id = f"{settings.project_id()}.{dataset_id}.observations"
    try:
        from google.cloud import bigquery

        dataset = bigquery.Dataset(f"{settings.project_id()}.{dataset_id}")
        dataset.location = settings.location()
        client.create_dataset(dataset, exists_ok=True)
        job = client.load_table_from_dataframe(
            observations,
            table_id,
            job_config=bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE"),
        )
        job.result()
        return {"exported": True, "table": table_id, "n": int(len(observations))}
    except Exception as exc:
        return {"exported": False, "reason": str(exc)}
