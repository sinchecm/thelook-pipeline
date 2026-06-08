"""
Database connection helpers for the analysis layer.
Uses the pooled Supabase connection (port 6543).
"""

import os
import pandas as pd
from sqlalchemy import create_engine, text, Engine
from dotenv import load_dotenv

load_dotenv()

_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        url = (
            f"postgresql+psycopg2://"
            f"{os.getenv('DW_USER')}:{os.getenv('DW_PASSWORD')}"
            f"@{os.getenv('DW_HOST')}:{os.getenv('DW_PORT')}"
            f"/{os.getenv('DW_DATABASE')}"
        )
        _engine = create_engine(url, pool_pre_ping=True)
    return _engine


def query(sql: str, params: dict | None = None) -> pd.DataFrame:
    """Execute SQL and return a DataFrame."""
    with get_engine().connect() as conn:
        return pd.read_sql(text(sql), conn, params=params)


def scalar(sql: str) -> any:
    """Execute SQL and return a single scalar value."""
    with get_engine().connect() as conn:
        return conn.execute(text(sql)).scalar()
