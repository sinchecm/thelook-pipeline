"""
Dagster pipeline definition for the TheLook e-commerce data pipeline.
"""

import subprocess
import sys
import time
import logging
import os
import json
import base64
import tempfile
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

# ─────────────────────────────────────────────────────────────────
#  GCP credentials — works both locally and on Dagster Cloud
# ─────────────────────────────────────────────────────────────────
def setup_gcp_credentials():
    """Write GCP key from env var to a temp file if running on Dagster Cloud."""
    gcp_key_json = os.environ.get("GCP_KEY_JSON")
    if gcp_key_json:
        key_data = base64.b64decode(gcp_key_json).decode("utf-8")
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        tmp.write(key_data)
        tmp.flush()
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = tmp.name

setup_gcp_credentials()


def _run(cmd: list[str], cwd: Path | None = None, log=None) -> str:
    logger = log or logging.getLogger(__name__)
    result = subprocess.run(
        cmd,
        cwd=str(cwd or PROJECT_ROOT),
        capture_output=True,
        text=True,
    )
    if result.stdout:
        logger.info(result.stdout[-4000:])
    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed: {' '.join(cmd)}\n{result.stderr[-2000:]}"
        )
    return result.stdout


@asset(group_name="ingestion", description="Extract all theLook tables from BigQuery → raw schema.")
def raw_tables(context: AssetExecutionContext) -> Output[dict]:
    log = get_dagster_logger()
    t0  = time.time()
    log.info("Starting ingestion from BigQuery...")
    _run([PYTHON, "-m", "ingestion.extract"], log=log)
    elapsed = time.time() - t0
    return Output(
        {"status": "ok", "duration_s": round(elapsed, 1)},
        metadata={"duration_seconds": round(elapsed, 1)},
    )


@asset(group_name="transform", deps=[raw_tables])
def dbt_models(context: AssetExecutionContext) -> Output[dict]:
    log = get_dagster_logger()
    t0  = time.time()
    _run([DBT, "deps"], cwd=DBT_DIR, log=log)
    _run([DBT, "run"], cwd=DBT_DIR, log=log)
    elapsed = time.time() - t0
    return Output(
        {"status": "ok", "duration_s": round(elapsed, 1)},
        metadata={"duration_seconds": round(elapsed, 1)},
    )


@asset(group_name="quality", deps=[dbt_models])
def data_quality_checks(context: AssetExecutionContext) -> Output[dict]:
    log = get_dagster_logger()
    t0  = time.time()
    _run([DBT, "test"], cwd=DBT_DIR, log=log)
    _run([PYTHON, "-m", "quality.expectations"], log=log)
    _run([PYTHON, "-m", "quality.custom_sql_checks"], log=log)
    elapsed = time.time() - t0
    return Output(
        {"status": "ok", "duration_s": round(elapsed, 1)},
        metadata={"duration_seconds": round(elapsed, 1)},
    )


@asset(group_name="analysis", deps=[data_quality_checks])
def python_analysis(context: AssetExecutionContext) -> Output[dict]:
    log = get_dagster_logger()
    t0  = time.time()
    _run([PYTHON, "-m", "analysis.eda"], log=log)
    elapsed = time.time() - t0
    return Output(
        {"status": "ok", "duration_s": round(elapsed, 1)},
        metadata={"duration_seconds": round(elapsed, 1)},
    )


pipeline_job = define_asset_job(
    name="thelook_pipeline",
    selection=[raw_tables, dbt_models, data_quality_checks, python_analysis],
)

daily_schedule = ScheduleDefinition(
    job=pipeline_job,
    cron_schedule="0 2 * * *",
    name="daily_pipeline_schedule",
    execution_timezone="UTC",
)

defs = Definitions(
    assets=[raw_tables, dbt_models, data_quality_checks, python_analysis],
    jobs=[pipeline_job],
    schedules=[daily_schedule],
)
