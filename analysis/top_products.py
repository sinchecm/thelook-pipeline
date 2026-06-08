"""
Top-selling products analysis.

Reads from marts.fact_sales + marts.dim_product and produces:
  - analysis/outputs/top_products.png  (horizontal bar chart)
  - Console table of top 20 category/brand combinations
"""

import logging
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

from analysis.db import query

logger    = logging.getLogger(__name__)
OUTPUT_DIR = Path(__file__).parent / "outputs"


def fetch_top_products(n: int = 20) -> pd.DataFrame:
    return query(f"""
        SELECT
            p.category,
            p.brand,
            p.department,
            COUNT(f.sale_id)                        AS units_sold,
            COUNT(DISTINCT f.order_id)              AS orders,
            ROUND(SUM(f.sale_amount)::numeric, 2)   AS revenue,
            ROUND(AVG(f.profit_margin_pct)::numeric, 1) AS avg_margin_pct,
            ROUND(SUM(f.profit_amount)::numeric, 2) AS total_profit

        FROM marts.fact_sales f
        JOIN marts.dim_product p ON f.product_id = p.product_id
        WHERE f.is_returned = false
        GROUP BY p.category, p.brand, p.department
        ORDER BY revenue DESC
        LIMIT {n}
    """)


def fetch_category_summary() -> pd.DataFrame:
    return query("""
        SELECT
            p.category,
            COUNT(f.sale_id)                        AS units_sold,
            ROUND(SUM(f.sale_amount)::numeric, 2)   AS revenue,
            ROUND(AVG(f.profit_margin_pct)::numeric, 1) AS avg_margin_pct
        FROM marts.fact_sales f
        JOIN marts.dim_product p ON f.product_id = p.product_id
        WHERE f.is_returned = false
        GROUP BY p.category
        ORDER BY revenue DESC
        LIMIT 10
    """)


def plot_top_categories(df: pd.DataFrame) -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    out_path = OUTPUT_DIR / "top_products.png"

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
    fig.patch.set_facecolor("#FAFAFA")

    teal_ramp = [
        "#0D9488","#0F766E","#115E59","#134E4A","#0891B2",
        "#0E7490","#155E75","#164E63","#1D4ED8","#1E40AF",
    ]

    # ── Left: revenue by category ─────────────────────────────────
    cats = fetch_category_summary()
    ax1.set_facecolor("#FAFAFA")
    bars = ax1.barh(
        cats["category"],
        cats["revenue"],
        color=teal_ramp[:len(cats)],
        height=0.65,
    )
    ax1.bar_label(bars, fmt=lambda v: f"${v/1000:.0f}K",
                  padding=4, fontsize=9)
    ax1.invert_yaxis()
    ax1.xaxis.set_major_formatter(mtick.FuncFormatter(lambda v, _: f"${v/1000:.0f}K"))
    ax1.set_title("Revenue by category", fontsize=13, fontweight="bold", loc="left", pad=8)
    ax1.set_xlabel("Revenue", fontsize=10)
    ax1.grid(axis="x", linewidth=0.4, alpha=0.5)
    ax1.spines[["top", "right"]].set_visible(False)

    # ── Right: avg margin % by category ──────────────────────────
    ax2.set_facecolor("#FAFAFA")
    margin_colors = ["#10B981" if v >= 40 else "#F59E0B" if v >= 25 else "#EF4444"
                     for v in cats["avg_margin_pct"]]
    ax2.barh(cats["category"], cats["avg_margin_pct"],
             color=margin_colors, height=0.65, alpha=0.8)
    ax2.axvline(cats["avg_margin_pct"].mean(), color="#64748B",
                linewidth=1, linestyle="--", label="Average")
    ax2.invert_yaxis()
    ax2.xaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
    ax2.set_title("Avg profit margin % by category", fontsize=13,
                  fontweight="bold", loc="left", pad=8)
    ax2.set_xlabel("Margin %", fontsize=10)
    ax2.grid(axis="x", linewidth=0.4, alpha=0.5)
    ax2.spines[["top", "right"]].set_visible(False)
    ax2.legend(fontsize=9)

    plt.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Chart saved → %s", out_path)
    return out_path


def run() -> pd.DataFrame:
    logger.info("── Top products ────────────────────────────")
    df = fetch_top_products(20)

    summary = df.copy()
    summary["revenue"]    = summary["revenue"].map("${:,.0f}".format)
    summary["total_profit"] = summary["total_profit"].map("${:,.0f}".format)
    summary["avg_margin_pct"] = summary["avg_margin_pct"].map(lambda v: f"{v:.1f}%")
    print("\n" + summary.to_string(index=False))

    plot_top_categories(df)
    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    run()
