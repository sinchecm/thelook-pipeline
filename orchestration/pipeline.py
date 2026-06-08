"""
Dagster pipeline definition for the TheLook e-commerce data pipeline.

Assets (in dependency order):
  raw_tables → dbt_models → data_quality_checks → python_analysis

Schedule: daily at 02:00 UTC.

Run:
    dagster dev -f orchestration/pipeline.py
    # then open http://localhost:3000
"""

import subprocess
import sys
import time
import logging
from pathlib import Path

from dagster import (
    AssetExecutionContext,
    Definitions,
    Output,
    ScheduleDefinition,
    asset,
    define_asset_job,
    get_dagster_logger,
)
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent
DBT_DIR      = PROJECT_ROOT / "dbt_project"
PYTHON       = sys.executable
DBT          = str(PROJECT_ROOT / ".venv/bin/dbt")


def _run(cmd: list[str], cwd: Path | None = None, log=None) -> str:
    """Run a subprocess, stream output to the Dagster logger, raise on failure."""
    logger = log or logging.getLogger(__name__)
    result = subprocess.run(
        cmd,
        cwd=str(cwd or PROJECT_ROOT),
        capture_output=True,
        text=True,
    )
    if result.stdout:
        logger.info(result.stdout[-4000:])   # last 4K chars to avoid log flood
    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed: {' '.join(cmd)}\n{result.stderr[-2000:]}"
        )
    return result.stdout


# ─────────────────────────────────────────────────────────────────
#  Assets
# ─────────────────────────────────────────────────────────────────

@asset(group_name="ingestion", description="Extract all theLook tables from BigQuery → raw schema.")
def raw_tables(context: AssetExecutionContext) -> Output[dict]:
    log = get_dagster_logger()
    t0  = time.time()

    log.info("Starting ingestion from BigQuery...")
    _run([PYTHON, "-m", "ingestion.extract"], log=log)

    elapsed = time.time() - t0
    log.info("Ingestion complete in %.1fs", elapsed)

    return Output(
        {"status": "ok", "duration_s": round(elapsed, 1)},
        metadata={"duration_seconds": round(elapsed, 1)},
    )


@asset(
    group_name="transform",
    deps=[raw_tables],
    description="Run all dbt models: staging views → intermediate → mart tables.",
)
def dbt_models(context: AssetExecutionContext) -> Output[dict]:
    log = get_dagster_logger()
    t0  = time.time()

    log.info("Installing dbt packages...")
    _run([DBT, "deps"], cwd=DBT_DIR, log=log)

    log.info("Running dbt models...")
    _run([DBT, "run"], cwd=DBT_DIR, log=log)

    elapsed = time.time() - t0
    log.info("dbt run complete in %.1fs", elapsed)

    return Output(
        {"status": "ok", "duration_s": round(elapsed, 1)},
        metadata={"duration_seconds": round(elapsed, 1)},
    )


@asset(
    group_name="quality",
    deps=[dbt_models],
    description="Run dbt schema tests + Great Expectations + custom SQL assertions.",
)
def data_quality_checks(context: AssetExecutionContext) -> Output[dict]:
    log = get_dagster_logger()
    t0  = time.time()

    log.info("Running dbt tests...")
    _run([DBT, "test"], cwd=DBT_DIR, log=log)

    log.info("Running Great Expectations suite...")
    _run([PYTHON, "-m", "quality.expectations"], log=log)

    log.info("Running custom SQL assertions...")
    _run([PYTHON, "-m", "quality.custom_sql_checks"], log=log)

    elapsed = time.time() - t0
    log.info("All quality checks passed in %.1fs", elapsed)

    return Output(
        {"status": "ok", "duration_s": round(elapsed, 1)},
        metadata={"duration_seconds": round(elapsed, 1)},
    )


@asset(
    group_name="analysis",
    deps=[data_quality_checks],
    description="Run Python EDA: monthly trends, top products, RFM segmentation.",
)
def python_analysis(context: AssetExecutionContext) -> Output[dict]:
    log = get_dagster_logger()
    t0  = time.time()

    log.info("Running EDA...")
    _run([PYTHON, "-m", "analysis.eda"], log=log)

    elapsed = time.time() - t0
    log.info("Analysis complete in %.1fs", elapsed)

    return Output(
        {"status": "ok", "duration_s": round(elapsed, 1)},
        metadata={"duration_seconds": round(elapsed, 1)},
    )


# ─────────────────────────────────────────────────────────────────
#  Job & schedule
# ─────────────────────────────────────────────────────────────────

pipeline_job = define_asset_job(
    name="thelook_pipeline",
    selection=[raw_tables, dbt_models, data_quality_checks, python_analysis],
    description="Full TheLook pipeline: ingest → transform → quality → analyse.",
)

daily_schedule = ScheduleDefinition(
    job=pipeline_job,
    cron_schedule="0 2 * * *",      # 02:00 UTC daily
    name="daily_pipeline_schedule",
    execution_timezone="UTC",
)

defs = Definitions(
    assets=[raw_tables, dbt_models, data_quality_checks, python_analysis],
    jobs=[pipeline_job],
    schedules=[daily_schedule],
)
