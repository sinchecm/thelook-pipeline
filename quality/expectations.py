"""
Great Expectations data quality suite for the TheLook pipeline.
Compatible with great-expectations >= 0.18.x
"""

import sys
import logging
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv

from ingestion.load import get_pooled_engine

load_dotenv(dotenv_path='.env')

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

PASS = "\033[32m✓\033[0m"
FAIL = "\033[31m✗\033[0m"


def query(sql: str) -> pd.DataFrame:
    engine = get_pooled_engine()
    with engine.connect() as conn:
        return pd.read_sql(sql, conn)


def check_not_null(df: pd.DataFrame, col: str) -> tuple[bool, str]:
    n = df[col].isna().sum()
    ok = n == 0
    return ok, f"not_null({col}): {n} nulls found"


def check_unique(df: pd.DataFrame, col: str) -> tuple[bool, str]:
    n = df[col].duplicated().sum()
    ok = n == 0
    return ok, f"unique({col}): {n} duplicates found"


def check_range(df: pd.DataFrame, col: str, min_val=None, max_val=None) -> tuple[bool, str]:
    s = df[col].dropna()
    violations = 0
    if min_val is not None:
        violations += (s < min_val).sum()
    if max_val is not None:
        violations += (s > max_val).sum()
    ok = violations == 0
    return ok, f"range({col}): {violations} out-of-range values"


def check_values(df: pd.DataFrame, col: str, values: list) -> tuple[bool, str]:
    bad = ~df[col].isin(values)
    n = bad.sum()
    ok = n == 0
    return ok, f"accepted_values({col}): {n} unexpected values"


def run_checks(df: pd.DataFrame, checks: list, suite_name: str) -> tuple[int, int]:
    passed = 0
    for fn, args, kwargs in checks:
        ok, msg = fn(df, *args, **kwargs)
        if ok:
            passed += 1
            logger.info("  %s  %s", PASS, msg)
        else:
            logger.warning("  %s  %s", FAIL, msg)
    logger.info("  %s: %d/%d passed", suite_name, passed, len(checks))
    return passed, len(checks)


def check_fact_sales() -> tuple[int, int]:
    logger.info("\n── fact_sales ──────────────────────────────")
    df = query("SELECT * FROM marts.fact_sales LIMIT 500000")

    checks = [
        (check_not_null,  ["sale_id"],          {}),
        (check_not_null,  ["order_id"],         {}),
        (check_not_null,  ["customer_id"],      {}),
        (check_not_null,  ["product_id"],       {}),
        (check_not_null,  ["date_id"],          {}),
        (check_not_null,  ["sale_amount"],      {}),
        (check_unique,    ["sale_id"],          {}),
        (check_range,     ["sale_amount"],      {"min_val": 0, "max_val": 10000}),
        (check_range,     ["profit_margin_pct"],{"min_val": -100, "max_val": 100}),
        (check_values,    ["is_returned"],      {"values": [True, False]}),
    ]
    return run_checks(df, checks, "fact_sales")


def check_dim_customer() -> tuple[int, int]:
    logger.info("\n── dim_customer ────────────────────────────")
    df = query("SELECT * FROM marts.dim_customer")

    checks = [
        (check_not_null,  ["customer_id"],  {}),
        (check_not_null,  ["email"],        {}),
        (check_unique,    ["customer_id"],  {}),
        (check_values,    ["clv_segment"],  {"values": ["High", "Medium", "Low"]}),
        (check_range,     ["lifetime_value"], {"min_val": 0}),
        (check_range,     ["total_orders"],   {"min_val": 0}),
    ]
    return run_checks(df, checks, "dim_customer")


def check_revenue_sanity() -> bool:
    logger.info("\n── Revenue sanity check ────────────────────")
    result = query(
        "SELECT ROUND(SUM(sale_amount)::numeric, 2) AS total "
        "FROM marts.fact_sales WHERE is_returned = false"
    )
    total = float(result["total"].iloc[0])
    ok = total >= 100_000
    symbol = PASS if ok else FAIL
    logger.info("  %s  Total non-returned revenue: $%s", symbol, f"{total:,.0f}")
    return ok


def main() -> None:
    logger.info("=" * 50)
    logger.info("Great Expectations suite  —  %s", datetime.now().strftime("%Y-%m-%d %H:%M"))
    logger.info("=" * 50)

    p1, t1 = check_fact_sales()
    p2, t2 = check_dim_customer()
    ok      = check_revenue_sanity()

    total_passed = p1 + p2 + (1 if ok else 0)
    total_checks = t1 + t2 + 1

    logger.info("\n%s", "=" * 50)
    logger.info("Summary: %d/%d expectations passed", total_passed, total_checks)

    if total_passed < total_checks:
        failed = total_checks - total_passed
        logger.error("%d expectation(s) FAILED — halting pipeline.", failed)
        sys.exit(1)

    logger.info("All quality checks passed.")


if __name__ == "__main__":
    main()
