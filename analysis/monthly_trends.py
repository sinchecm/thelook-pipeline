"""
Monthly revenue trend analysis.

Reads from marts.rpt_monthly_revenue (pre-aggregated) and produces:
  - analysis/outputs/monthly_trend.png  (revenue line + MoM % bar)
  - Console summary table
"""

import logging
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

from analysis.db import query

logger = logging.getLogger(__name__)
OUTPUT_DIR = Path(__file__).parent / "outputs"


def fetch_monthly_revenue() -> pd.DataFrame:
    return query("""
        SELECT
            year,
            month,
            month_abbr,
            fiscal_quarter_label,
            num_orders,
            num_customers,
            total_revenue,
            total_profit,
            avg_order_value,
            avg_margin_pct,
            revenue_mom_pct
        FROM marts.rpt_monthly_revenue
        ORDER BY year, month
    """)


def plot_trends(df: pd.DataFrame) -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    out_path = OUTPUT_DIR / "monthly_trend.png"

    labels = df["month_abbr"] + "\n" + df["year"].astype(str)
    x = range(len(df))

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 9), sharex=True)
    fig.patch.set_facecolor("#FAFAFA")

    # ── Top: revenue line ──────────────────────────────────────────
    ax1.set_facecolor("#FAFAFA")
    ax1.plot(x, df["total_revenue"], color="#0D9488", linewidth=2.5,
             marker="o", markersize=4, zorder=3)
    ax1.fill_between(x, df["total_revenue"], alpha=0.08, color="#0D9488")

    # Annotate Q4 spikes
    for i, row in df.iterrows():
        if row["month"] == 12:
            ax1.annotate(
                f"${row['total_revenue']/1000:.0f}K",
                xy=(i, row["total_revenue"]),
                xytext=(0, 10), textcoords="offset points",
                ha="center", fontsize=8, color="#0D9488",
            )

    ax1.yaxis.set_major_formatter(
        mtick.FuncFormatter(lambda v, _: f"${v/1000:.0f}K")
    )
    ax1.set_title("Monthly Revenue", fontsize=13, fontweight="bold",
                  loc="left", pad=8)
    ax1.set_ylabel("Revenue", fontsize=10)
    ax1.grid(axis="y", linewidth=0.4, alpha=0.5)
    ax1.spines[["top", "right"]].set_visible(False)

    # ── Bottom: MoM % bar ─────────────────────────────────────────
    ax2.set_facecolor("#FAFAFA")
    mom = df["revenue_mom_pct"].fillna(0)
    bar_colors = ["#10B981" if v >= 0 else "#EF4444" for v in mom]
    ax2.bar(x, mom, color=bar_colors, alpha=0.75, width=0.7)
    ax2.axhline(0, color="#94A3B8", linewidth=0.8)

    ax2.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=1))
    ax2.set_title("Month-over-month growth %", fontsize=13, fontweight="bold",
                  loc="left", pad=8)
    ax2.set_ylabel("MoM %", fontsize=10)
    ax2.set_xticks(list(x))
    ax2.set_xticklabels(labels, fontsize=8)
    ax2.grid(axis="y", linewidth=0.4, alpha=0.5)
    ax2.spines[["top", "right"]].set_visible(False)

    plt.tight_layout(h_pad=1.5)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Chart saved → %s", out_path)
    return out_path


def run() -> pd.DataFrame:
    logger.info("── Monthly revenue trends ──────────────────")
    df = fetch_monthly_revenue()

    # Console summary
    summary = df[["year","month_abbr","num_orders","total_revenue",
                  "avg_order_value","revenue_mom_pct"]].copy()
    summary["total_revenue"]   = summary["total_revenue"].map("${:,.0f}".format)
    summary["avg_order_value"] = summary["avg_order_value"].map("${:,.2f}".format)
    summary["revenue_mom_pct"] = summary["revenue_mom_pct"].map(
        lambda v: f"{v:+.1f}%" if pd.notna(v) else "—"
    )
    print("\n" + summary.to_string(index=False))

    plot_trends(df)
    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    run()
