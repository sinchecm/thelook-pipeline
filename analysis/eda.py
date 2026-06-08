"""
Python EDA entry point.

Runs all three analyses in sequence:
  1. Monthly revenue trends
  2. Top-selling products
  3. Customer RFM segmentation

Outputs are saved to analysis/outputs/.

Run:
    python analysis/eda.py
    python analysis/eda.py --only trends     # one analysis
    python analysis/eda.py --only products
    python analysis/eda.py --only segments
"""

import argparse
import logging
import sys
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def print_overview() -> None:
    from analysis.db import query, scalar

    logger.info("── Overview ────────────────────────────────")
    df = query("""
        SELECT
            (SELECT COUNT(*)                                    FROM marts.fact_sales)                              AS total_sales,
            (SELECT COUNT(*)                                    FROM marts.fact_sales WHERE is_returned = false)    AS non_returned_sales,
            (SELECT COUNT(*)                                    FROM marts.dim_customer)                            AS total_customers,
            (SELECT COUNT(*)                                    FROM marts.dim_product)                             AS total_products,
            (SELECT ROUND(SUM(sale_amount)::numeric,2)          FROM marts.fact_sales WHERE is_returned = false)    AS total_revenue,
            (SELECT ROUND(AVG(sale_amount)::numeric,2)          FROM marts.fact_sales WHERE is_returned = false)    AS avg_order_value,
            (SELECT ROUND(AVG(profit_margin_pct)::numeric,1)    FROM marts.fact_sales WHERE is_returned = false)    AS avg_margin_pct
    """)
    row = df.iloc[0]
    print(f"""
  Total sales          : {int(row['total_sales']):>12,}
  Non-returned sales   : {int(row['non_returned_sales']):>12,}
  Total customers      : {int(row['total_customers']):>12,}
  Total products       : {int(row['total_products']):>12,}
  Total revenue        : ${float(row['total_revenue']):>11,.2f}
  Avg order value      : ${float(row['avg_order_value']):>11,.2f}
  Avg profit margin    : {float(row['avg_margin_pct']):>11.1f}%
""")


def main() -> None:
    parser = argparse.ArgumentParser(description="TheLook EDA runner")
    parser.add_argument(
        "--only",
        choices=["trends", "products", "segments"],
        help="Run a single analysis instead of all three",
    )
    args = parser.parse_args()

    logger.info("=" * 50)
    logger.info("TheLook EDA  —  %s", datetime.now().strftime("%Y-%m-%d %H:%M"))
    logger.info("=" * 50)

    try:
        print_overview()
    except Exception as e:
        logger.error("Could not connect to data warehouse: %s", e)
        sys.exit(1)

    failed: list[str] = []

    analyses = {
        "trends":   ("analysis.monthly_trends",   "run"),
        "products": ("analysis.top_products",      "run"),
        "segments": ("analysis.customer_segments", "run"),
    }

    targets = [args.only] if args.only else list(analyses.keys())

    for name in targets:
        module_path, fn = analyses[name]
        try:
            import importlib
            mod = importlib.import_module(module_path)
            getattr(mod, fn)()
        except Exception as exc:
            logger.error("Analysis '%s' failed: %s", name, exc)
            failed.append(name)

    logger.info("\n%s", "=" * 50)
    if failed:
        logger.error("Failed analyses: %s", failed)
        sys.exit(1)

    logger.info("EDA complete. Outputs saved to analysis/outputs/")


if __name__ == "__main__":
    main()
