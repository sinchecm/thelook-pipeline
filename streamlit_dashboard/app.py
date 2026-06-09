"""
TheLook E-Commerce Analytics Dashboard
Connects live to PostgreSQL warehouse — always shows latest data after pipeline runs.
"""

import os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sqlalchemy import create_engine
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

st.set_page_config(
    page_title="TheLook Analytics",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stApp { background-color: #FFFFFF; color: #1F2937; }
    [data-testid="stSidebar"] { background-color: #F8F9FA; border-right: 1px solid #E5E7EB; }
    .kpi-card { background: linear-gradient(135deg, #1E293B 0%, #162032 100%); border: 1px solid #334155; border-radius: 12px; padding: 1.25rem 1.5rem; position: relative; overflow: hidden; }
    .kpi-card::before { content: ''; position: absolute; top: 0; left: 0; width: 3px; height: 100%; border-radius: 2px 0 0 2px; }
    .kpi-card.teal::before  { background: #0D9488; }
    .kpi-card.blue::before  { background: #3B82F6; }
    .kpi-card.purple::before{ background: #8B5CF6; }
    .kpi-card.amber::before { background: #F59E0B; }
    .kpi-card.green::before { background: #10B981; }
    .kpi-card.red::before   { background: #EF4444; }
    .kpi-label { font-size: 11px; font-weight: 500; letter-spacing: 0.08em; text-transform: uppercase; color: #64748B; margin-bottom: 6px; }
    .kpi-value { font-size: 28px; font-weight: 600; color: #F1F5F9; line-height: 1.1; font-family: 'DM Mono', monospace; }
    .section-header { font-size: 13px; font-weight: 500; letter-spacing: 0.1em; text-transform: uppercase; color: #475569; margin: 2rem 0 1rem; padding-bottom: 0.5rem; border-bottom: 1px solid #1E293B; }
</style>
""", unsafe_allow_html=True)

# ── Database ──────────────────────────────────────────────────────────────────
@st.cache_resource
def get_engine():
    def _get(key, default):
        try:
            return st.secrets[key]
        except Exception:
            return os.getenv(key, default)
    url = (
        f"postgresql+psycopg2://"
        f"{_get('DW_USER', 'pipeline_user')}:"
        f"{_get('DW_PASSWORD', 'pipeline_pass')}"
        f"@{_get('DW_HOST', 'localhost')}:"
        f"{_get('DW_PORT', '5432')}"
        f"/{_get('DW_DATABASE', 'neondb')}"
        f"?sslmode=require"
    )
    return create_engine(url, pool_pre_ping=True)

@st.cache_data(ttl=3600)
def query(sql: str) -> pd.DataFrame:
    with get_engine().connect() as conn:
        return pd.read_sql(sql, conn)

PLOT_BG = "#FFFFFF"; PAPER_BG = "#FFFFFF"; GRID_COLOR = "#E5E7EB"
TEXT_COLOR = "#1F2937"; TEAL = "#0D9488"; BLUE = "#3B82F6"
PURPLE = "#8B5CF6"; AMBER = "#F59E0B"; GREEN = "#10B981"; RED = "#EF4444"

def base_layout(title="", height=360):
    return dict(
        title=dict(text=title, font=dict(size=13, color="#CBD5E1"), x=0.01),
        paper_bgcolor=PAPER_BG, plot_bgcolor=PLOT_BG,
        font=dict(family="DM Sans", color=TEXT_COLOR, size=11),
        height=height, margin=dict(l=16, r=16, t=40, b=16),
        xaxis=dict(gridcolor=GRID_COLOR, linecolor="#334155"),
        yaxis=dict(gridcolor=GRID_COLOR, linecolor="#334155"),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:.5rem 0 1.5rem">
        <div style="font-size:22px;font-weight:600;color:#F1F5F9;">🛍️ TheLook</div>
        <div style="font-size:11px;color:#475569;text-transform:uppercase;letter-spacing:.05em">Analytics Dashboard</div>
    </div>""", unsafe_allow_html=True)

    st.markdown("**Filters**")

    years_df = query("SELECT DISTINCT year FROM marts.rpt_monthly_revenue ORDER BY year")
    year_opts = ["All"] + [str(y) for y in years_df["year"].tolist()]
    selected_year = st.selectbox("Year", year_opts, index=0)

    cats_df = query("SELECT DISTINCT category FROM marts.dim_product ORDER BY category")
    cat_opts = ["All"] + cats_df["category"].tolist()
    selected_cat = st.selectbox("Category", cat_opts, index=0)

    countries_df = query("SELECT DISTINCT country FROM marts.dim_customer WHERE country IS NOT NULL ORDER BY country LIMIT 20")
    country_opts = ["All"] + countries_df["country"].tolist()
    selected_country = st.selectbox("Country", country_opts, index=0)

    st.divider()
    last_run = query("SELECT MAX(ordered_at) as last_order FROM marts.fact_sales")
    last_ts = last_run["last_order"].iloc[0]
    st.markdown(f'<div style="font-size:11px;color:#475569">🟢 Live · Last order: {pd.Timestamp(last_ts).strftime("%d %b %Y") if last_ts else "N/A"}</div>', unsafe_allow_html=True)

# ── Build filters ─────────────────────────────────────────────────────────────
def year_f(alias="d"):
    return f"AND {alias}.year = {selected_year}" if selected_year != "All" else ""

def cat_f():
    return f"AND p.category = '{selected_cat}'" if selected_cat != "All" else ""

def country_f():
    return f"AND c.country = '{selected_country}'" if selected_country != "All" else ""

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="margin-bottom:1.5rem">
    <h1 style="font-size:24px;font-weight:600;color:#F1F5F9;margin:0">Revenue & Performance</h1>
    <p style="font-size:13px;color:#475569;margin:4px 0 0">End-to-end analytics · Updated daily at 02:00 UTC</p>
</div>""", unsafe_allow_html=True)

# ── KPIs ──────────────────────────────────────────────────────────────────────
kpis = query(f"""
    SELECT
        COUNT(DISTINCT f.sale_id)                           AS total_orders,
        COUNT(DISTINCT f.customer_id)                       AS total_customers,
        ROUND(SUM(f.sale_amount)::numeric, 2)               AS total_revenue,
        ROUND(AVG(f.sale_amount)::numeric, 2)               AS avg_order_value,
        ROUND(AVG(f.profit_margin_pct)::numeric, 1)         AS avg_margin_pct,
        ROUND(SUM(CASE WHEN f.is_returned THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS return_rate
    FROM marts.fact_sales f
    LEFT JOIN marts.dim_date d     ON f.date_id    = d.date_id
    LEFT JOIN marts.dim_product p  ON f.product_id = p.product_id
    LEFT JOIN marts.dim_customer c ON f.customer_id = c.customer_id
    WHERE f.is_returned = false {year_f()} {cat_f()} {country_f()}
""")
k = kpis.iloc[0]

def kpi_card(col, label, value, color="teal"):
    col.markdown(f"""<div class="kpi-card {color}">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
    </div>""", unsafe_allow_html=True)

c1,c2,c3,c4,c5,c6 = st.columns(6)
kpi_card(c1, "Total Revenue", "${:.1f}M".format(float(k['total_revenue'])/1_000_000), "teal")
kpi_card(c2, "Total Orders",    f"{int(k['total_orders']):,}",         "blue")
kpi_card(c3, "Customers",       f"{int(k['total_customers']):,}",      "purple")
kpi_card(c4, "Avg Order Value", f"${float(k['avg_order_value']):.2f}", "amber")
kpi_card(c5, "Avg Margin",      f"{float(k['avg_margin_pct']):.1f}%",  "green")
kpi_card(c6, "Return Rate",     f"{float(k['return_rate']):.1f}%",     "red")

st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)

# ── Monthly trend ─────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">Revenue Trend</div>', unsafe_allow_html=True)

monthly_where = f"WHERE 1=1 {year_f('r')}"
monthly = query(f"""
    SELECT r.year, r.month, r.month_abbr, r.month_name,
           r.total_revenue, r.total_profit, r.num_orders,
           r.avg_order_value, r.revenue_mom_pct
    FROM marts.rpt_monthly_revenue r
    {monthly_where}
    ORDER BY r.year, r.month
""")

if not monthly.empty:
    monthly["label"] = monthly["month_abbr"] + " " + monthly["year"].astype(str)
    monthly["mom_color"] = monthly["revenue_mom_pct"].apply(lambda x: GREEN if (x or 0) >= 0 else RED)

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.05)
    fig.add_trace(go.Scatter(x=monthly["label"], y=monthly["total_revenue"],
        mode="lines+markers", name="Revenue",
        line=dict(color=TEAL, width=2.5), marker=dict(size=5),
        fill="tozeroy", fillcolor="rgba(13,148,136,0.08)"), row=1, col=1)
    fig.add_trace(go.Scatter(x=monthly["label"], y=monthly["total_profit"],
        mode="lines", name="Profit", line=dict(color=BLUE, width=1.5, dash="dot")), row=1, col=1)
    fig.add_trace(go.Bar(x=monthly["label"], y=monthly["revenue_mom_pct"].fillna(0),
        name="MoM %", marker_color=monthly["mom_color"]), row=2, col=1)

    layout = base_layout(height=420)
    layout.update(showlegend=True, hovermode="x unified",
        yaxis=dict(tickprefix="$", tickformat=",.0f", gridcolor=GRID_COLOR),
        yaxis2=dict(ticksuffix="%", gridcolor=GRID_COLOR))
    fig.update_layout(**layout)
    st.plotly_chart(fig, use_container_width=True)

# ── Top categories ────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">Products & Categories</div>', unsafe_allow_html=True)
col_l, col_r = st.columns(2)

top_cats = query(f"""
    SELECT p.category,
           ROUND(SUM(f.sale_amount)::numeric, 0)       AS revenue,
           ROUND(AVG(f.profit_margin_pct)::numeric, 1) AS margin_pct
    FROM marts.fact_sales f
    JOIN marts.dim_product p  ON f.product_id = p.product_id
    LEFT JOIN marts.dim_date d     ON f.date_id    = d.date_id
    LEFT JOIN marts.dim_customer c ON f.customer_id = c.customer_id
    WHERE f.is_returned = false {year_f()} {cat_f()} {country_f()}
    GROUP BY p.category ORDER BY revenue DESC LIMIT 10
""")

with col_l:
    if not top_cats.empty:
        fig2 = go.Figure(go.Bar(
            y=top_cats["category"], x=top_cats["revenue"], orientation="h",
            marker=dict(color=top_cats["revenue"], colorscale=[[0,"#0F4C75"],[1,TEAL]]),
            text=top_cats["revenue"].apply(lambda x: f"${x:,.0f}"),
            textposition="outside", textfont=dict(size=10, color=TEXT_COLOR)))
        l2 = base_layout("Revenue by category", 360)
        l2["yaxis"] = dict(autorange="reversed", gridcolor=GRID_COLOR)
        l2["xaxis"] = dict(tickprefix="$", tickformat=",.0f", gridcolor=GRID_COLOR)
        l2["margin"] = dict(l=16, r=80, t=40, b=16)
        fig2.update_layout(**l2)
        st.plotly_chart(fig2, use_container_width=True)

with col_r:
    if not top_cats.empty:
        colors = [GREEN if m >= 50 else AMBER if m >= 35 else RED for m in top_cats["margin_pct"]]
        fig3 = go.Figure(go.Bar(
            y=top_cats["category"], x=top_cats["margin_pct"], orientation="h",
            marker_color=colors,
            text=top_cats["margin_pct"].apply(lambda x: f"{x:.1f}%"),
            textposition="outside", textfont=dict(size=10, color=TEXT_COLOR)))
        l3 = base_layout("Profit margin % by category", 360)
        l3["yaxis"] = dict(autorange="reversed", gridcolor=GRID_COLOR)
        l3["xaxis"] = dict(ticksuffix="%", gridcolor=GRID_COLOR)
        l3["margin"] = dict(l=16, r=60, t=40, b=16)
        fig3.update_layout(**l3)
        st.plotly_chart(fig3, use_container_width=True)

# ── Customer segments ─────────────────────────────────────────────────────────
st.markdown('<div class="section-header">Customer Segments</div>', unsafe_allow_html=True)
cs1, cs2, cs3 = st.columns([1,1,1])

country_where = f"AND c.country = '{selected_country}'" if selected_country != "All" else ""
segments = query(f"""
    SELECT c.rfm_segment,
           COUNT(*)                                 AS customers,
           ROUND(AVG(c.lifetime_value)::numeric, 2) AS avg_ltv,
           ROUND(SUM(c.lifetime_value)::numeric, 0) AS total_revenue
    FROM marts.dim_customer c
    WHERE c.total_orders > 0 {country_where}
    GROUP BY c.rfm_segment ORDER BY total_revenue DESC
""")

SEG_COLORS = {"Champions":TEAL,"Loyal":BLUE,"Potential Loyalists":PURPLE,"At Risk":AMBER,"Lost / Churned":RED}

with cs1:
    if not segments.empty:
        colors = [SEG_COLORS.get(s, "#64748B") for s in segments["rfm_segment"]]
        fig4 = go.Figure(go.Pie(
            labels=segments["rfm_segment"], values=segments["customers"],
            hole=0.55, marker=dict(colors=colors, line=dict(color=PLOT_BG, width=2)),
            textinfo="percent", textfont=dict(size=11)))
        fig4.add_annotation(text=f"<b>{int(segments['customers'].sum()):,}</b><br>customers",
            x=0.5, y=0.5, showarrow=False, font=dict(size=13, color="#F1F5F9"))
        l4 = base_layout("Customer distribution", 320)
        l4["showlegend"] = True
        fig4.update_layout(**l4)
        st.plotly_chart(fig4, use_container_width=True)

with cs2:
    if not segments.empty:
        fig5 = go.Figure(go.Bar(
            x=segments["rfm_segment"], y=segments["avg_ltv"],
            marker_color=[SEG_COLORS.get(s, "#64748B") for s in segments["rfm_segment"]],
            text=segments["avg_ltv"].apply(lambda x: f"${x:,.0f}"),
            textposition="outside", textfont=dict(size=10, color=TEXT_COLOR)))
        l5 = base_layout("Avg lifetime value", 320)
        l5["yaxis"]["tickprefix"] = "$"
        l5["xaxis"]["tickangle"] = -20
        fig5.update_layout(**l5)
        st.plotly_chart(fig5, use_container_width=True)

with cs3:
    if not segments.empty:
        for _, row in segments.iterrows():
            color = SEG_COLORS.get(row["rfm_segment"], "#64748B")
            pct = row["customers"] / segments["customers"].sum() * 100
            st.markdown(f"""<div style="margin-bottom:.75rem;padding:.75rem 1rem;
                background:#1E293B;border-radius:8px;border-left:3px solid {color}">
                <div style="display:flex;justify-content:space-between">
                    <span style="font-size:12px;font-weight:500;color:#CBD5E1">{row['rfm_segment']}</span>
                    <span style="font-size:11px;color:#64748B">{pct:.1f}%</span>
                </div>
                <div style="display:flex;justify-content:space-between;margin-top:4px">
                    <span style="font-size:11px;color:#64748B">{int(row['customers']):,} customers</span>
                    <span style="font-size:11px;color:{color}">${float(row['avg_ltv']):,.0f} avg LTV</span>
                </div></div>""", unsafe_allow_html=True)

# ── Top products table ────────────────────────────────────────────────────────
st.markdown('<div class="section-header">Top Products</div>', unsafe_allow_html=True)

top_prods = query(f"""
    SELECT p.product_name, p.brand, p.category, p.price_tier,
           COUNT(f.sale_id)                             AS units_sold,
           ROUND(SUM(f.sale_amount)::numeric, 0)        AS revenue,
           ROUND(AVG(f.profit_margin_pct)::numeric, 1)  AS margin_pct
    FROM marts.fact_sales f
    JOIN marts.dim_product p  ON f.product_id = p.product_id
    LEFT JOIN marts.dim_date d     ON f.date_id    = d.date_id
    LEFT JOIN marts.dim_customer c ON f.customer_id = c.customer_id
    WHERE f.is_returned = false {year_f()} {cat_f()} {country_f()}
    GROUP BY p.product_name, p.brand, p.category, p.price_tier
    ORDER BY revenue DESC LIMIT 15
""")

if not top_prods.empty:
    top_prods["Revenue"] = top_prods["revenue"].apply(lambda x: f"${x:,.0f}")
    top_prods["Margin"]  = top_prods["margin_pct"].apply(lambda x: f"{x:.1f}%")
    st.dataframe(
        top_prods[["product_name","brand","category","price_tier","units_sold","Revenue","Margin"]]
        .rename(columns={"product_name":"Product","brand":"Brand","category":"Category",
                         "price_tier":"Tier","units_sold":"Units"}),
        use_container_width=True, hide_index=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(f"""<div style="margin-top:2rem;padding-top:1rem;border-top:1px solid #1E293B;
    display:flex;justify-content:space-between">
    <span style="font-size:11px;color:#334155">TheLook Analytics · Streamlit + dbt + Dagster</span>
    <span style="font-size:11px;color:#334155">Last refresh: {datetime.now().strftime('%d %b %Y %H:%M')}</span>
</div>""", unsafe_allow_html=True)
