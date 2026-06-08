"""
Customer segmentation analysis using RFM (Recency, Frequency, Monetary).

Reads pre-computed rfm_segment from marts.dim_customer and produces:
  - analysis/outputs/rfm_segments.csv
  - analysis/outputs/customer_segments.png  (donut + bar charts)
  - Console segment summary table
"""

import logging
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from analysis.db import query

logger    = logging.getLogger(__name__)
OUTPUT_DIR = Path(__file__).parent / "outputs"

SEGMENT_COLORS = {
    "Champions":           "#0D9488",
    "Loyal":               "#0891B2",
    "Potential Loyalists": "#7C3AED",
    "At Risk":             "#F59E0B",
    "Lost / Churned":      "#EF4444",
}


def fetch_segments() -> pd.DataFrame:
    return query("""
        SELECT
            customer_id,
            full_name,
            country,
            clv_segment,
            rfm_segment,
            total_orders,
            ROUND(lifetime_value::numeric, 2)    AS lifetime_value,
            ROUND(avg_order_value::numeric, 2)   AS avg_order_value,
            ROUND(recency_days::numeric, 0)      AS recency_days,
            is_repeat_customer,
            acquisition_date
        FROM marts.dim_customer
        WHERE total_orders > 0
        ORDER BY lifetime_value DESC
    """)


def summarise_segments(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate per-segment KPIs."""
    return (
        df.groupby("rfm_segment")
        .agg(
            customers       = ("customer_id",    "count"),
            total_revenue   = ("lifetime_value", "sum"),
            avg_ltv         = ("lifetime_value", "mean"),
            avg_orders      = ("total_orders",   "mean"),
            avg_recency_days= ("recency_days",   "mean"),
        )
        .round(2)
        .reset_index()
        .sort_values("total_revenue", ascending=False)
    )


def plot_segments(df: pd.DataFrame, summary: pd.DataFrame) -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    out_path = OUTPUT_DIR / "customer_segments.png"

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
    fig.patch.set_facecolor("#FAFAFA")

    seg_order  = list(SEGMENT_COLORS.keys())
    seg_counts = summary.set_index("rfm_segment").reindex(seg_order)["customers"].fillna(0)
    colors     = [SEGMENT_COLORS[s] for s in seg_order if s in summary["rfm_segment"].values]
    labels_pie = [
        f"{s}\n{int(seg_counts[s]):,} ({seg_counts[s]/seg_counts.sum()*100:.1f}%)"
        for s in seg_order if s in summary["rfm_segment"].values
    ]

    # ── Left: donut chart ────────────────────────────────────────
    ax1.set_facecolor("#FAFAFA")
    wedges, _ = ax1.pie(
        [seg_counts[s] for s in seg_order if s in summary["rfm_segment"].values],
        colors=colors,
        startangle=90,
        wedgeprops={"width": 0.5, "edgecolor": "#FAFAFA", "linewidth": 2},
    )
    ax1.legend(wedges, labels_pie, loc="lower center",
               ncol=2, fontsize=9, frameon=False,
               bbox_to_anchor=(0.5, -0.15))
    total = int(seg_counts.sum())
    ax1.text(0, 0, f"{total:,}\ncustomers", ha="center", va="center",
             fontsize=13, fontweight="bold", color="#334155")
    ax1.set_title("Customer segments", fontsize=13, fontweight="bold",
                  loc="left", pad=8)

    # ── Right: avg LTV per segment ───────────────────────────────
    ax2.set_facecolor("#FAFAFA")
    plot_summary = summary[summary["rfm_segment"].isin(seg_order)].copy()
    plot_summary = plot_summary.set_index("rfm_segment").reindex(
        [s for s in seg_order if s in plot_summary.index]
    ).reset_index()

    bar_colors = [SEGMENT_COLORS[s] for s in plot_summary["rfm_segment"]]
    bars = ax2.barh(
        plot_summary["rfm_segment"],
        plot_summary["avg_ltv"],
        color=bar_colors,
        height=0.6,
        alpha=0.85,
    )
    ax2.bar_label(bars, fmt=lambda v: f"${v:,.0f}", padding=4, fontsize=9)
    ax2.invert_yaxis()
    ax2.set_title("Average lifetime value per segment",
                  fontsize=13, fontweight="bold", loc="left", pad=8)
    ax2.set_xlabel("Avg LTV ($)", fontsize=10)
    ax2.xaxis.set_major_formatter(
        plt.FuncFormatter(lambda v, _: f"${v:,.0f}")
    )
    ax2.grid(axis="x", linewidth=0.4, alpha=0.5)
    ax2.spines[["top", "right"]].set_visible(False)

    plt.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Chart saved → %s", out_path)
    return out_path


def run() -> tuple[pd.DataFrame, pd.DataFrame]:
    logger.info("── Customer segmentation ───────────────────")
    df      = fetch_segments()
    summary = summarise_segments(df)

    # Console output
    display = summary.copy()
    display["total_revenue"] = display["total_revenue"].map("${:,.0f}".format)
    display["avg_ltv"]       = display["avg_ltv"].map("${:,.2f}".format)
    display["avg_orders"]    = display["avg_orders"].map("{:.1f}".format)
    display["avg_recency_days"] = display["avg_recency_days"].map("{:.0f}d".format)
    print("\n" + display.to_string(index=False))

    # Save CSV
    csv_path = OUTPUT_DIR / "rfm_segments.csv"
    OUTPUT_DIR.mkdir(exist_ok=True)
    df.to_csv(csv_path, index=False)
    logger.info("CSV saved → %s", csv_path)

    plot_segments(df, summary)
    return df, summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    run()
