"""
SQLAlchemy connection factory and bulk-load helpers.
Used by extract.py and can be imported by any pipeline step
that needs a database connection.
"""

import os
import logging
from contextlib import contextmanager

import pandas as pd
from sqlalchemy import create_engine, text, Engine
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


# ── Connection factories ──────────────────────────────────────────────────────

def get_pooled_engine() -> Engine:
    """
    Pooled connection via PgBouncer (port 6543).
    Use for ingestion and Python analysis — handles high-throughput
    bulk inserts without exhausting Supabase connection limits.
    """
    url = (
        f"postgresql+psycopg2://"
        f"{os.getenv('DW_USER')}:{os.getenv('DW_PASSWORD')}"
        f"@{os.getenv('DW_HOST')}:{os.getenv('DW_PORT')}"
        f"/{os.getenv('DW_DATABASE')}"
    )
    return create_engine(url, pool_pre_ping=True,
        connect_args={"sslmode": "require"})


def get_direct_engine() -> Engine:
    """
    Direct connection (port 5432).
    Use for dbt and any session that needs prepared statements.
    """
    url = (
        f"postgresql+psycopg2://"
        f"{os.getenv('DBT_USER')}:{os.getenv('DBT_PASSWORD')}"
        f"@{os.getenv('DBT_HOST')}:{os.getenv('DBT_PORT', '5432')}"
        f"/{os.getenv('DBT_DATABASE')}"
    )
    return create_engine(url, pool_pre_ping=True,
        connect_args={"sslmode": "require"})


@contextmanager
def get_connection(engine: Engine | None = None):
    """Context manager that yields a live connection and auto-commits."""
    eng = engine or get_pooled_engine()
    with eng.begin() as conn:
        yield conn


# ── Bulk loader ───────────────────────────────────────────────────────────────

def bulk_load(
    df: pd.DataFrame,
    table: str,
    schema: str = "raw",
    engine: Engine | None = None,
    if_exists: str = "replace",
    chunksize: int = 500,
) -> int:
    """
    Load a DataFrame into PostgreSQL using multi-row INSERT.

    Parameters
    ----------
    df        : DataFrame to load
    table     : destination table name
    schema    : destination schema (default: raw)
    engine    : SQLAlchemy engine — uses pooled engine if None
    if_exists : 'replace' (first chunk) or 'append' (subsequent chunks)
    chunksize : rows per INSERT statement (keep ≤500 for Supabase free tier)

    Returns
    -------
    int : total rows loaded
    """
    eng = engine or get_pooled_engine()

    df.to_sql(
        name=table,
        schema=schema,
        con=eng,
        if_exists=if_exists,
        index=False,
        method="multi",
        chunksize=chunksize,
    )
    logger.debug("Loaded %d rows → %s.%s", len(df), schema, table)
    return len(df)


def query(sql: str, engine: Engine | None = None) -> pd.DataFrame:
    """Execute a SQL query and return results as a DataFrame."""
    eng = engine or get_pooled_engine()
    with eng.connect() as conn:
        return pd.read_sql(text(sql), conn)


def row_count(table: str, schema: str = "raw", engine: Engine | None = None) -> int:
    """Return the current row count for a table."""
    eng = engine or get_pooled_engine()
    with eng.connect() as conn:
        result = conn.execute(
            text(f"SELECT COUNT(*) FROM {schema}.{table}")
        )
        return result.scalar()
