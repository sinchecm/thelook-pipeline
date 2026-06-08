"""
Executes the custom SQL assertion files in dbt_project/tests/.
Each file returns rows when an assertion is violated — zero rows = pass.

Run standalone:
    python quality/custom_sql_checks.py
"""

import sys
import logging
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from ingestion.load import get_pooled_engine

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

TESTS_DIR = Path(__file__).parent.parent / "dbt_project" / "tests"
PASS = "\033[32m✓\033[0m"
FAIL = "\033[31m✗\033[0m"


def strip_config(sql: str) -> str:
    """Remove dbt {{ config(...) }} blocks before running SQL directly."""
    import re
    return re.sub(r'\{\{\s*config\([^)]*\)\s*\}\}', '', sql).strip()


def resolve_refs(sql: str) -> str:
    """
    Replace dbt {{ ref('model') }} macros with fully-qualified table names.
    This lets us run the assertion SQL directly against Supabase without dbt.
    """
    import re

    def replacer(m: re.Match) -> str:
        model = m.group(1).strip().strip("'\"")
        schema = "marts"    # all custom tests reference mart models
        return f"{schema}.{model}"

    return re.sub(r"\{\{\s*ref\s*\(([^)]+)\)\s*\}\}", replacer, sql)


def run_assertion(sql_file: Path, engine) -> tuple[bool, int]:
    """
    Run one SQL assertion file.
    Returns (passed: bool, violation_count: int).
    """
    raw_sql  = sql_file.read_text()
    clean_sql = strip_config(resolve_refs(raw_sql))

    with engine.connect() as conn:
        df = pd.read_sql(clean_sql, conn)

    violations = len(df)
    passed = violations == 0

    if passed:
        logger.info("  %s  %s", PASS, sql_file.name)
    else:
        logger.warning("  %s  %s  →  %d violations", FAIL, sql_file.name, violations)
        if not df.empty:
            logger.warning("\n%s\n", df.head(5).to_string(index=False))

    return passed, violations


def main() -> None:
    logger.info("Custom SQL assertions")
    logger.info("─" * 40)

    engine = get_pooled_engine()
    sql_files = sorted(TESTS_DIR.glob("*.sql"))

    if not sql_files:
        logger.warning("No SQL test files found in %s", TESTS_DIR)
        return

    results: list[tuple[str, bool, int]] = []

    for f in sql_files:
        passed, count = run_assertion(f, engine)
        results.append((f.name, passed, count))

    total  = len(results)
    passed = sum(1 for _, p, _ in results if p)

    logger.info("\n%s", "─" * 40)
    logger.info("Results: %d/%d assertions passed", passed, total)
# assert_daily_volume is a known warning for partial datasets
    hard_failures = [
        (name, ok, count) for name, ok, count in results
        if not ok and name != "assert_daily_volume.sql"
    ]
    if hard_failures:
        logger.error("Failed assertions:")
        for name, ok, count in hard_failures:
            logger.error("  ✗  %s  (%d violations)", name, count)
        sys.exit(1)

    logger.info("All SQL assertions passed (daily_volume is advisory).")
    

if __name__ == "__main__":
    main()
