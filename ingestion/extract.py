"""
Extract all theLook eCommerce tables from BigQuery and load them
into the raw schema in Supabase (PostgreSQL).

Run:
    python ingestion/extract.py
    python ingestion/extract.py --tables orders users   # specific tables
    python ingestion/extract.py --date-filter 2023-01-01  # limit by date
"""

import os
import sys
import argparse
import logging
import time
from datetime import datetime

import pandas as pd
from google.cloud import bigquery
from dotenv import load_dotenv

from ingestion.load import get_pooled_engine, bulk_load, row_count

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

BQ_PROJECT = os.getenv("GCP_PROJECT_ID")
BQ_DATASET = os.getenv("BQ_DATASET", "bigquery-public-data.thelook_ecommerce")

# Tables ordered small → large to fail fast on auth/connection issues
# and so storage usage grows gradually on the free tier
SOURCE_TABLES = [
    "distribution_centers",   #      ~10 rows
    "products",               #   ~29 000 rows
    "users",                  #  ~100 000 rows
    "orders",                 #  ~100 000 rows
    "inventory_items",        #  ~490 000 rows
    "events",                 # ~2 500 000 rows
    "order_items",            # ~5 000 000 rows  ← largest, load last
]

# Columns that contain timestamps — cast to datetime after read_gbq
TIMESTAMP_COLS: dict[str, list[str]] = {
    "orders":           ["created_at", "returned_at", "shipped_at", "delivered_at"],
    "order_items":      ["created_at", "shipped_at", "delivered_at", "returned_at"],
    "users":            ["created_at"],
    "inventory_items":  ["created_at", "sold_at"],
    "events":           ["created_at"],
}

CHUNK_SIZE = 50_000   # rows per BigQuery page
LOAD_CHUNK = 500      # rows per INSERT (Supabase free tier limit)


def build_query(table: str, date_filter: str | None = None) -> str:
    """Build the BigQuery SELECT query, optionally filtering by created_at."""
    base = f"SELECT * FROM `{BQ_DATASET}.{table}`"
    if date_filter and table in TIMESTAMP_COLS:
        base += f" WHERE created_at >= '{date_filter}'"
    return base


def coerce_timestamps(df: pd.DataFrame, table: str) -> pd.DataFrame:
    """Convert timestamp columns to timezone-naive datetime for psycopg2."""
    for col in TIMESTAMP_COLS.get(table, []):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], utc=True, errors="coerce")
            # Strip tz info — psycopg2 stores as TIMESTAMPTZ, Supabase handles it
            df[col] = df[col].dt.tz_localize(None)
    return df


def extract_table(
    table: str,
    date_filter: str | None = None,
    dry_run: bool = False,
) -> int:
    """
    Extract one BigQuery table and load it into raw.<table>.

    Returns
    -------
    int : total rows loaded
    """
    client = bigquery.Client(project=BQ_PROJECT)
    engine = get_pooled_engine()
    query  = build_query(table, date_filter)

    logger.info("%-22s  querying BigQuery...", table)
    t0 = time.time()

    if dry_run:
        count_q = f"SELECT COUNT(*) as n FROM `{BQ_DATASET}.{table}`"
        n = list(client.query(count_q).result())[0].n
        logger.info("%-22s  [DRY RUN] would load %d rows", table, n)
        return n

    rows_loaded = 0
    first_chunk = True

    job = client.query(query)
    rows = job.result()
    
    all_rows = []
    batch = []
    for row in rows:
        batch.append(dict(row))
        if len(batch) >= CHUNK_SIZE:
            all_rows.append(pd.DataFrame(batch))
            batch = []
    if batch:
        all_rows.append(pd.DataFrame(batch))
    
    chunk_iter = iter(all_rows)
    for chunk in chunk_iter:
        
        chunk = coerce_timestamps(chunk, table)

        if first_chunk:
            with engine.begin() as conn:
                conn.execute(__import__('sqlalchemy').text(
                    f"DROP TABLE IF EXISTS raw.{table} CASCADE"
                ))

        loaded = bulk_load(
            df=chunk,
            table=table,
            schema="raw",
            engine=engine,
            if_exists="replace" if first_chunk else "append",
            chunksize=LOAD_CHUNK,
        )
        rows_loaded += loaded
        first_chunk = False
        elapsed = time.time() - t0
        print(
            f"  {table:<22}  {rows_loaded:>10,} rows  ({elapsed:.1f}s)",
            end="\r",
            flush=True,
        )

    elapsed = time.time() - t0
    logger.info(
        "%-22s  %10d rows loaded  (%.1fs)",
        table, rows_loaded, elapsed,
    )
    return rows_loaded


def verify_counts(tables: list[str]) -> None:
    """Print row counts from the raw schema as a quick sanity check."""
    logger.info("\nVerification — row counts in raw schema:")
    logger.info("  %-22s  %s", "table", "rows")
    logger.info("  %s", "-" * 36)
    for t in tables:
        try:
            n = row_count(t, schema="raw")
            logger.info("  %-22s  %10d", t, n)
        except Exception as e:
            logger.warning("  %-22s  ERROR: %s", t, e)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Extract theLook tables from BigQuery")
    p.add_argument(
        "--tables", nargs="+", metavar="TABLE",
        help="Specific tables to load (default: all)",
    )
    p.add_argument(
        "--date-filter", metavar="YYYY-MM-DD",
        help="Only load rows where created_at >= this date",
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help="Count rows in BigQuery without loading",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    tables = args.tables or SOURCE_TABLES

    logger.info("=" * 50)
    logger.info("TheLook ingestion  —  %s", datetime.now().strftime("%Y-%m-%d %H:%M"))
    logger.info("Dataset : %s", BQ_DATASET)
    logger.info("Tables  : %s", ", ".join(tables))
    if args.date_filter:
        logger.info("Filter  : created_at >= %s", args.date_filter)
    logger.info("=" * 50)

    total_rows = 0
    failed: list[str] = []

    for table in tables:
        try:
            n = extract_table(table, args.date_filter, args.dry_run)
            total_rows += n
        except Exception as exc:
            logger.error("FAILED  %-22s  %s", table, exc)
            failed.append(table)

    verify_counts([t for t in tables if t not in failed])

    logger.info("\nSummary: %d rows loaded across %d tables", total_rows, len(tables) - len(failed))
    if failed:
        logger.error("Failed tables: %s", failed)
        sys.exit(1)
    logger.info("Ingestion complete.")


if __name__ == "__main__":
    main()
