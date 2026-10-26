"""Load the raw simulator tables into BigQuery (optional hosted warehouse).

    pip install google-cloud-bigquery
    gcloud auth application-default login
    BQ_PROJECT=my-project python scripts/load_bigquery.py --raw data/raw
    dbt build --project-dir dbt --profiles-dir dbt --target bigquery

Creates dataset `raw` (BQ_RAW_DATASET) and loads each data/raw/raw_*.csv.gz with schema
autodetect. The dbt models are the same as on DuckDB: engine-specific SQL lives in
dbt/macros/cross_db.sql. Timestamps load as DATETIME (IST wall-clock), matching DuckDB.
Sandbox note: free-tier tables expire after 60 days unless billing is enabled.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default="data/raw")
    ap.add_argument("--project", default=os.environ.get("BQ_PROJECT"))
    ap.add_argument("--dataset", default=os.environ.get("BQ_RAW_DATASET", "raw"))
    ap.add_argument("--location", default=os.environ.get("BQ_LOCATION", "asia-south1"))
    a = ap.parse_args()
    if not a.project:
        raise SystemExit("set BQ_PROJECT or pass --project")

    from google.cloud import bigquery
    client = bigquery.Client(project=a.project, location=a.location)
    ds = bigquery.Dataset(f"{a.project}.{a.dataset}")
    ds.location = a.location
    client.create_dataset(ds, exists_ok=True)

    for path in sorted(Path(a.raw).glob("raw_*.csv.gz")):
        table = f"{a.project}.{a.dataset}.{path.name.split('.')[0]}"
        cfg = bigquery.LoadJobConfig(source_format=bigquery.SourceFormat.CSV, skip_leading_rows=1, autodetect=True,
                                     write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE)
        with open(path, "rb") as f:
            job = client.load_table_from_file(f, table, job_config=cfg)
        job.result()
        print(f"  loaded {table:<60} {client.get_table(table).num_rows:>12,} rows")


if __name__ == "__main__":
    main()
